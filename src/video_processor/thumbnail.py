import subprocess
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image

from loguru import logger

from src.distribution_enum import Distribution
from src.video_processor.cache import get_cache_path, is_cache_valid, clear_cache

def generate_placeholder_thumbnail(processor):
    """Generate a gray placeholder thumbnail image.

    Args:
        processor: The VideoProcessor instance.

    Returns:
        Image: Placeholder image with dimensions based on thumbnail_width.
    """
    return Image.new('RGB', (processor.thumbnail_width, int(processor.thumbnail_width * 9 / 16)), color='gray')

def get_video_duration(video_path):
    """Get the duration of a video file in seconds.

    Args:
        video_path (Path): Path to the video file.

    Returns:
        float: Duration in seconds.
    """
    cmd = ['ffmpeg', '-i', str(video_path), '-hide_banner']
    result = subprocess.run(cmd, capture_output=True, text=False)
    output = result.stderr.decode('utf-8', errors='ignore')
    duration = 0
    for line in output.split('\n'):
        if 'Duration' in line:
            time_str = line.split('Duration: ')[1].split(',')[0]
            h, m, s = map(float, time_str.split(':'))
            duration = h * 3600 + m * 60 + s
            break
    return duration

def generate_distributed_timestamps(processor, duration):
    """Generate thumbnail timestamps based on the selected distribution.

    Args:
        processor: The VideoProcessor instance.
        duration (float): Total duration of the video in seconds.

    Returns:
        list: List of timestamps in seconds.
    """
    match processor.distribution:
        case Distribution.UNIFORM:
            normalized_timestamps = np.linspace(0, 1, processor.thumbnails_per_video + 2)[1:-1]  # Exclude endpoints
        case Distribution.TRIANGULAR:
            normalized_timestamps = np.random.triangular(0, processor.peak_pos, 1, processor.thumbnails_per_video + 1)
            normalized_timestamps = sorted(normalized_timestamps)[:-1]  # Remove the last one if duplicated
        case Distribution.NORMAL:
            samples = np.random.normal(processor.peak_pos, processor.concentration, processor.thumbnails_per_video * 10)
            normalized_timestamps = np.clip(samples, 0, 1)
            percentiles = np.linspace(0, 100, processor.thumbnails_per_video)
            normalized_timestamps = np.percentile(normalized_timestamps, percentiles)
            normalized_timestamps = sorted(normalized_timestamps)
        case _:
            raise ValueError(f"Unknown distribution: {processor.distribution}")

    normalized_timestamps = np.clip(normalized_timestamps, 0, 0.99)
    timestamps = [timestamp * duration for timestamp in normalized_timestamps]
    return sorted(timestamps)

def generate_thumbnails(processor, video_path, progress_callback=None, command_callback=None):
    """Generate thumbnails for a video and manage cache.

    Args:
        processor: The VideoProcessor instance.
        video_path (Path): Path to the video file.
        progress_callback (callable, optional): Callback to report thumbnail generation progress.
        command_callback (callable, optional): Callback to report FFmpeg commands.

    Returns:
        tuple: (list of thumbnail file names, list of corresponding timestamps in seconds, video duration in seconds)
    """
    logger.debug(f"Processing thumbnails for {video_path}")
    cache_path = get_cache_path(video_path)
    if not cache_path.exists():
        logger.debug(f"No cache found for {video_path}. Generating new thumbnails.")
    elif not is_cache_valid(processor, video_path):
        logger.debug(f"Cache invalid for {video_path} due to config mismatch. Clearing cache.")
        clear_cache(video_path)
    else:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        logger.debug(f"Using valid cache for {video_path}")
        if processor.update_callback:
            logger.debug(f"Calling update_callback for {video_path} with cached {len(cache['thumbnails'])} thumbnails")
            processor.update_callback(video_path, cache['thumbnails'], cache['timestamps'], cache['duration'])
        return cache['thumbnails'], cache['timestamps'], cache['duration']

    try:
        duration = get_video_duration(video_path)
        if duration == 0:
            raise ValueError("Could not determine video duration")

        timestamps = generate_distributed_timestamps(processor, duration)
        thumbnails = []
        start_time = time.time()
        cache_base = video_path.parent / "cache" / video_path.name
        cache_base.parent.mkdir(exist_ok=True)
        cache_base.mkdir(exist_ok=True)

        for i, timestamp in enumerate(timestamps):
            thumb_path = cache_base / f"{i}.jpg"
            success = False

            # Attempt 1: CUDA with format filter
            cmd = [
                'ffmpeg', '-hwaccel', 'cuda', '-ss', str(timestamp), '-i', str(video_path),
                '-vf', f'format=yuv420p,scale={processor.thumbnail_width}:-1', '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                '-c:v', 'mjpeg', '-y', str(thumb_path)
            ]
            if command_callback:
                command_callback(' '.join(cmd), str(thumb_path), str(video_path))
            try:
                result = subprocess.run(cmd, capture_output=True, text=False)
                if result.returncode == 0:
                    thumbnails.append(f"{i}.jpg")
                    logger.debug(f"Generated thumbnail {thumb_path} at {timestamp}s (Attempt 1: format filter)")
                    success = True
                else:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                    logger.warning(f"Attempt 1 failed for {video_path} at {timestamp}s: {error_msg}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Attempt 1 failed for {video_path} at {timestamp}s: {e.stderr.decode('utf-8', errors='ignore')}")

            # Attempt 2: CUDA with h264_cuvid and scale_cuda
            if not success:
                cmd = [
                    'ffmpeg', '-ss', str(timestamp), '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda', '-c:v', 'h264_cuvid',
                    '-i', str(video_path),
                    '-vf', f'scale_cuda={processor.thumbnail_width}:-1:force_original_aspect_ratio=decrease,hwdownload,format=nv12,format=yuv420p,colorspace=all=bt709:iall=bt709',
                    '-vframes', '1', '-c:v', 'mjpeg', '-q:v', str(processor.thumbnail_quality), '-y', str(thumb_path)
                ]
                if command_callback:
                    command_callback(' '.join(cmd), str(thumb_path), str(video_path))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=False)
                    if result.returncode == 0:
                        thumbnails.append(f"{i}.jpg")
                        logger.debug(f"Generated thumbnail {thumb_path} at {timestamp}s (Attempt 2: h264_cuvid with scale_cuda)")
                        success = True
                    else:
                        error_msg = result.stderr.decode('utf-8', errors='ignore')
                        logger.warning(f"Attempt 2 failed for {video_path} at {timestamp}s: {error_msg}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Attempt 2 failed for {video_path} at {timestamp}s: {e.stderr.decode('utf-8', errors='ignore')}")

            # Attempt 3: CUDA with scale_cuda filter
            if not success:
                cmd = [
                    'ffmpeg', '-hwaccel', 'cuda', '-ss', str(timestamp), '-i', str(video_path),
                    '-vf', f'scale_cuda={processor.thumbnail_width}:-1', '-pix_fmt', 'yuv420p', '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                    '-c:v', 'mjpeg', '-y', str(thumb_path)
                ]
                if command_callback:
                    command_callback(' '.join(cmd), str(thumb_path), str(video_path))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=False)
                    if result.returncode == 0:
                        thumbnails.append(f"{i}.jpg")
                        logger.debug(f"Generated thumbnail {thumb_path} at {timestamp}s (Attempt 3: scale_cuda)")
                        success = True
                    else:
                        error_msg = result.stderr.decode('utf-8', errors='ignore')
                        logger.warning(f"Attempt 3 failed for {video_path} at {timestamp}s: {error_msg}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Attempt 3 failed for {video_path} at {timestamp}s: {e.stderr.decode('utf-8', errors='ignore')}")

            # Attempt 4: CPU-based with colorspace filter
            if not success:
                cmd = [
                    'ffmpeg', '-ss', str(timestamp), '-i', str(video_path),
                    '-vf', f'colorspace=all=bt709:iall=bt709,scale={processor.thumbnail_width}:-1,format=yuv420p',
                    '-vframes', '1', '-c:v', 'mjpeg', '-q:v', str(processor.thumbnail_quality), '-y', str(thumb_path)
                ]
                if command_callback:
                    command_callback(' '.join(cmd), str(thumb_path), str(video_path))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=False)
                    if result.returncode == 0:
                        thumbnails.append(f"{i}.jpg")
                        logger.debug(f"Generated thumbnail {thumb_path} at {timestamp}s (Attempt 4: CPU with colorspace)")
                        success = True
                    else:
                        error_msg = result.stderr.decode('utf-8', errors='ignore')
                        logger.warning(f"Attempt 4 (CPU with colorspace) failed for {video_path} at {timestamp}s: {error_msg}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Attempt 4 (CPU with colorspace) failed for {video_path} at {timestamp}s: {e.stderr.decode('utf-8', errors='ignore')}")

            # Fallback: Generate placeholder if all attempts fail
            if not success:
                logger.warning(f"All attempts failed for {video_path} at {timestamp}s. Generating placeholder.")
                placeholder = generate_placeholder_thumbnail(processor)
                placeholder.save(thumb_path, quality=processor.thumbnail_quality)
                thumbnails.append(f"{i}.jpg")
                logger.debug(f"Generated placeholder thumbnail {thumb_path}")

            if progress_callback:
                progress_callback((i + 1) / processor.thumbnails_per_video * 100)

        cache_data = {
            'thumbnails': thumbnails,
            'timestamps': timestamps,
            'duration': duration,
            'thumbnails_per_video': processor.thumbnails_per_video,
            'thumbnail_width': processor.thumbnail_width,
            'thumbnail_quality': processor.thumbnail_quality,
            'peak_pos': processor.peak_pos,
            'concentration': processor.concentration,
            'distribution': processor.distribution.value
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        logger.debug(f"Generated thumbnails for {video_path} in {time.time() - start_time:.2f}s")

        if processor.update_callback:
            logger.debug(f"Calling update_callback for {video_path} with {len(thumbnails)} thumbnails")
            processor.update_callback(video_path, thumbnails, timestamps, duration)

        return thumbnails, timestamps, duration

    except Exception as e:
        logger.error(f"Error processing {video_path}: {str(e)}")
        thumbnails = []
        timestamps = [0] * processor.thumbnails_per_video
        duration = 0
        cache_base = video_path.parent / "cache" / video_path.name
        cache_base.parent.mkdir(exist_ok=True)
        cache_base.mkdir(exist_ok=True)
        for i in range(processor.thumbnails_per_video):
            thumb_path = cache_base / f"{i}.jpg"
            placeholder = generate_placeholder_thumbnail(processor)
            placeholder.save(thumb_path, quality=processor.thumbnail_quality)
            thumbnails.append(f"{i}.jpg")
        cache_data = {
            'thumbnails': thumbnails,
            'timestamps': timestamps,
            'duration': duration,
            'thumbnails_per_video': processor.thumbnails_per_video,
            'thumbnail_width': processor.thumbnail_width,
            'thumbnail_quality': processor.thumbnail_quality,
            'peak_pos': processor.peak_pos,
            'concentration': processor.concentration,
            'distribution': processor.distribution.value
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        if processor.update_callback:
            logger.debug(f"Calling update_callback for {video_path} with {len(thumbnails)} thumbnails (error case)")
            processor.update_callback(video_path, thumbnails, timestamps, duration)

        return thumbnails, timestamps, duration