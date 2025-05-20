import subprocess
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image

from loguru import logger

from src.distribution_enum import Distribution
from .cache import get_cache_path, is_cache_valid, clear_cache # 相対インポートに変更

def generate_placeholder_thumbnail(processor):
    return Image.new('RGB', (processor.thumbnail_width, int(processor.thumbnail_width * 9 / 16)), color='gray')

def get_video_duration(video_path):
    cmd = ['ffmpeg', '-i', str(video_path), '-hide_banner']
    try:
        result = subprocess.run(cmd, capture_output=True, text=False, timeout=30) # タイムアウト追加
        output = result.stderr.decode('utf-8', errors='ignore')
        duration = 0
        for line in output.split('\n'):
            if 'Duration' in line:
                time_str = line.split('Duration: ')[1].split(',')[0]
                h, m, s = map(float, time_str.split(':'))
                duration = h * 3600 + m * 60 + s
                break
        return duration
    except subprocess.TimeoutExpired:
        logger.warning(f"ffmpeg timeout while getting duration for {video_path}")
        return 0
    except Exception as e:
        logger.error(f"Error getting video duration for {video_path}: {e}")
        return 0


def generate_distributed_timestamps(processor, duration):
    # processor.distribution が Distribution enum インスタンスであることを確認
    if not isinstance(processor.distribution, Distribution):
        logger.warning(f"Invalid distribution type: {type(processor.distribution)}. Defaulting to UNIFORM.")
        current_distribution = Distribution.UNIFORM
    else:
        current_distribution = processor.distribution

    # Ensure thumbnails_per_video is positive
    num_thumbnails = processor.thumbnails_per_video
    if num_thumbnails <= 0:
        logger.warning(f"Thumbnails per video is {num_thumbnails}, must be > 0. Returning empty timestamps.")
        return []


    match current_distribution:
        case Distribution.UNIFORM:
            # Avoid division by zero if num_thumbnails is 0 or 1 for linspace
            if num_thumbnails == 0: return []
            if num_thumbnails == 1: normalized_timestamps = np.array([0.5]) # Single thumbnail in the middle
            else: normalized_timestamps = np.linspace(0, 1, num_thumbnails + 2)[1:-1]
        case Distribution.TRIANGULAR:
            if num_thumbnails == 0: return []
            # np.random.triangular(left, mode, right, size)
            # Ensure concentration makes sense for mode and bounds
            mode = np.clip(processor.peak_pos, 0.01, 0.99) # mode cannot be 0 or 1 for standard triangular
            # For simplicity, let's assume peak_pos is the mode, and concentration defines width
            # This might need more robust handling of left/right bounds relative to mode
            left_bound = max(0, mode - processor.concentration)
            right_bound = min(1, mode + processor.concentration)
            if left_bound >= mode: left_bound = max(0, mode - 0.01) # ensure left < mode
            if right_bound <= mode: right_bound = min(1, mode + 0.01) # ensure right > mode
            if left_bound >= right_bound: # Fallback if bounds are problematic
                normalized_timestamps = np.full(num_thumbnails, mode)
            else:
                normalized_timestamps = np.random.triangular(left_bound, mode, right_bound, num_thumbnails)

        case Distribution.NORMAL:
            if num_thumbnails == 0: return []
            # Ensure concentration (sigma) is positive
            sigma = max(processor.concentration, 1e-6)
            samples = np.random.normal(processor.peak_pos, sigma, num_thumbnails * 5) # Generate more samples
            samples_clipped = np.clip(samples, 0, 1)
            # Select percentiles to get a good spread, even if many samples are outside [0,1] before clipping
            if len(samples_clipped) < num_thumbnails : # Should not happen with *5
                normalized_timestamps = np.linspace(0.1, 0.9, num_thumbnails) # Fallback
            else:
                percentiles = np.linspace(0, 100, num_thumbnails)
                normalized_timestamps = np.percentile(samples_clipped, percentiles)
        case _:
            logger.error(f"Unknown distribution: {current_distribution}. Defaulting to UNIFORM.")
            if num_thumbnails == 0: return []
            if num_thumbnails == 1: normalized_timestamps = np.array([0.5])
            else: normalized_timestamps = np.linspace(0, 1, num_thumbnails + 2)[1:-1]


    normalized_timestamps = np.clip(np.sort(normalized_timestamps), 0.01, 0.99) # Ensure timestamps are within video and sorted
    timestamps = [timestamp * duration for timestamp in normalized_timestamps]
    return sorted(list(set(timestamps))) # Ensure unique and sorted timestamps, remove duplicates


def generate_thumbnails(processor, video_path: Path, progress_callback=None, command_callback=None, stop_flag_check=None):
    logger.debug(f"Starting thumbnail generation for {video_path}")
    if stop_flag_check and stop_flag_check():
        logger.info(f"Thumbnail generation for {video_path} cancelled before start.")
        return [], [], 0 # Return empty if stopped

    cache_path = get_cache_path(video_path)
    if not cache_path.exists():
        logger.debug(f"No cache found for {video_path}. Generating new thumbnails.")
    elif not is_cache_valid(processor, video_path): # is_cache_valid now takes processor
        logger.debug(f"Cache invalid for {video_path}. Clearing cache.")
        clear_cache(video_path)
    else:
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            # Basic check for essential keys
            if all(k in cache for k in ['thumbnails', 'timestamps', 'duration']):
                logger.debug(f"Using valid cache for {video_path}")
                if processor.update_callback:
                    processor.update_callback(video_path, cache['thumbnails'], cache['timestamps'], cache['duration'])
                return cache['thumbnails'], cache['timestamps'], cache['duration']
            else:
                logger.warning(f"Cache for {video_path} missing essential keys. Regenerating.")
                clear_cache(video_path)
        except json.JSONDecodeError:
            logger.warning(f"Cache for {video_path} is corrupted (JSONDecodeError). Regenerating.")
            clear_cache(video_path)
        except Exception as e:
            logger.warning(f"Error loading cache for {video_path}: {e}. Regenerating.")
            clear_cache(video_path)


    thumbnails = []
    generated_timestamps = []
    video_duration = 0

    try:
        video_duration = get_video_duration(video_path)
        if video_duration <= 0:
            logger.warning(f"Could not determine valid duration for {video_path} ({video_duration}s). Skipping.")
            # update_callback with placeholder/error indication if needed
            if processor.update_callback:
                placeholder_thumbs = [f"placeholder_{i}.jpg" for i in range(processor.thumbnails_per_video)]
                # Create actual placeholder files or handle in UI
                processor.update_callback(video_path, placeholder_thumbs, [0]*processor.thumbnails_per_video, 0)
            return [], [], 0

        target_timestamps = generate_distributed_timestamps(processor, video_duration)
        if not target_timestamps:
            logger.warning(f"No target timestamps generated for {video_path}. Skipping.")
            if processor.update_callback: # Similar placeholder update
                processor.update_callback(video_path, [], [], video_duration)
            return [], [], video_duration


        # Ensure cache_base directory exists
        cache_base = video_path.parent / "cache" / video_path.name
        cache_base.mkdir(parents=True, exist_ok=True) # Ensure full path exists

        for i, timestamp in enumerate(target_timestamps):
            if stop_flag_check and stop_flag_check():
                logger.info(f"Thumbnail generation for {video_path} cancelled during loop at timestamp {timestamp}.")
                break # Exit the loop

            thumb_filename = f"thumb_{i:03d}.jpg" # More robust naming
            thumb_path = cache_base / thumb_filename

            ffmpeg_cmd_successful = False
            # FFmpeg command attempts (simplified for brevity, use your existing multi-attempt logic)
            # Attempt 1: CUDA with format filter
            cmd_list = [
                ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-hwaccel', 'cuda', '-ss', str(timestamp), '-i', str(video_path),
                 '-vf', f'format=yuv420p,scale={processor.thumbnail_width}:-1', '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                 '-c:v', 'mjpeg', '-y', str(thumb_path)],
                # Attempt 2: CPU-based as fallback
                ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', str(timestamp), '-i', str(video_path),
                 '-vf', f'scale={processor.thumbnail_width}:-1,format=yuv420p',
                 '-vframes', '1', '-c:v', 'mjpeg', '-q:v', str(processor.thumbnail_quality), '-y', str(thumb_path)]
            ]

            for cmd_idx, cmd in enumerate(cmd_list):
                if command_callback:
                    command_callback(' '.join(cmd), str(thumb_path), str(video_path))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=False, timeout=30) # Added timeout
                    if result.returncode == 0 and thumb_path.exists() and thumb_path.stat().st_size > 0:
                        thumbnails.append(thumb_filename)
                        generated_timestamps.append(timestamp)
                        ffmpeg_cmd_successful = True
                        logger.debug(f"Generated thumbnail {thumb_path} at {timestamp}s (Attempt {cmd_idx+1})")
                        break # Success, move to next timestamp
                    else:
                        error_output = result.stderr.decode('utf-8', errors='ignore')
                        logger.warning(f"FFmpeg attempt {cmd_idx+1} failed for {video_path} at {timestamp}s. Code: {result.returncode}. Error: {error_output[:200]}")
                except subprocess.TimeoutExpired:
                    logger.warning(f"FFmpeg attempt {cmd_idx+1} timed out for {video_path} at {timestamp}s.")
                except Exception as e_ffmpeg:
                    logger.error(f"Exception during FFmpeg attempt {cmd_idx+1} for {video_path} at {timestamp}s: {e_ffmpeg}", exc_info=True)

            if not ffmpeg_cmd_successful:
                logger.warning(f"All FFmpeg attempts failed for {video_path} at {timestamp}s. Generating placeholder.")
                placeholder_img = generate_placeholder_thumbnail(processor)
                try:
                    placeholder_img.save(thumb_path) # Default quality should be fine for placeholder
                    thumbnails.append(thumb_filename)
                    generated_timestamps.append(timestamp) # Still associate with the target timestamp
                except Exception as e_placeholder:
                    logger.error(f"Failed to save placeholder thumbnail for {video_path} at {timestamp}s: {e_placeholder}")

            if progress_callback:
                # Progress for current video (0-100%)
                progress_val = ((i + 1) / len(target_timestamps)) * 100
                progress_callback(progress_val)

        # After loop, if some thumbnails were generated (or placeholders)
        if thumbnails:
            cache_data = {
                'thumbnails': thumbnails,
                'timestamps': generated_timestamps,
                'duration': video_duration,
                'thumbnails_per_video': processor.thumbnails_per_video,
                'thumbnail_width': processor.thumbnail_width,
                'thumbnail_quality': processor.thumbnail_quality,
                'peak_pos': processor.peak_pos,
                'concentration': processor.concentration,
                'distribution': processor.distribution.value if isinstance(processor.distribution, Distribution) else str(processor.distribution)
            }
            try:
                with open(cache_path, 'w') as f:
                    json.dump(cache_data, f, indent=4)
                logger.debug(f"Saved cache for {video_path}")
            except Exception as e:
                logger.error(f"Failed to write cache for {video_path}: {e}")

        if processor.update_callback:
            processor.update_callback(video_path, thumbnails, generated_timestamps, video_duration)

        return thumbnails, generated_timestamps, video_duration

    except Exception as e:
        logger.error(f"General error processing thumbnails for {video_path}: {e}", exc_info=True)
        # Fallback: update UI with placeholders if a catastrophic error occurs
        if processor.update_callback:
            num_thumbs_fallback = processor.thumbnails_per_video if hasattr(processor, 'thumbnails_per_video') and processor.thumbnails_per_video > 0 else 1
            placeholder_thumbs = [f"error_placeholder_{i}.jpg" for i in range(num_thumbs_fallback)]
            # Potentially create these placeholder files
            processor.update_callback(video_path, placeholder_thumbs, [0.0]*num_thumbs_fallback, 0.0)
        return [], [], 0