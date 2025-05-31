import subprocess
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image

from loguru import logger

from src.distribution_enum import Distribution
from .cache import get_cache_path, is_cache_valid, clear_cache

def generate_placeholder_thumbnail(processor):
    height = int(processor.thumbnail_width * 9 / 16)
    return Image.new('RGB', (processor.thumbnail_width, height), color='gray')

def get_video_duration(video_path):
    cmd = ['ffmpeg', '-i', str(video_path), '-hide_banner']
    try:
        result = subprocess.run(cmd, capture_output=True, text=False, timeout=30)
        output = result.stderr.decode('utf-8', errors='ignore')
        duration = 0
        for line in output.split('\n'):
            if 'Duration' in line:
                time_str = line.split('Duration: ')[1].split(',')[0]
                h, m, s = map(float, time_str.split(':'))
                duration = h * 3600 + m * 60 + s
                break
        if duration == 0:
            logger.warning(f"Could not parse duration for {video_path} from FFmpeg output. Output: {output[:500]}")
        return duration
    except subprocess.TimeoutExpired:
        logger.warning(f"ffmpeg timeout while getting duration for {video_path}")
        return 0
    except Exception as e:
        logger.error(f"Error getting video duration for {video_path}: {e}")
        return 0


def generate_distributed_timestamps(processor, duration):
    if not isinstance(processor.distribution, Distribution):
        logger.warning(f"Invalid distribution type: {type(processor.distribution)}. Defaulting to UNIFORM.")
        current_distribution = Distribution.UNIFORM
    else:
        current_distribution = processor.distribution

    num_thumbnails = processor.thumbnails_per_video
    if num_thumbnails <= 0:
        logger.warning(f"Thumbnails per video is {num_thumbnails}, must be > 0. Returning empty timestamps.")
        return []

    match current_distribution:
        case Distribution.UNIFORM:
            if num_thumbnails == 0: return []
            if num_thumbnails == 1: normalized_timestamps = np.array([0.5])
            else: normalized_timestamps = np.linspace(0, 1, num_thumbnails + 2)[1:-1]
        case Distribution.TRIANGULAR:
            if num_thumbnails == 0: return []
            peak_pos_f = float(processor.peak_pos)
            concentration_f = float(processor.concentration)

            left_bound = max(0, peak_pos_f - concentration_f)
            right_bound = min(1, peak_pos_f + concentration_f)
            mode = np.clip(peak_pos_f, left_bound, right_bound)

            if abs(right_bound - left_bound) < 1e-6 or concentration_f < 1e-3:
                spread_epsilon = 0.05
                left_fallback = max(0, peak_pos_f - spread_epsilon)
                right_fallback = min(1, peak_pos_f + spread_epsilon)
                if left_fallback >= right_fallback:
                    normalized_timestamps = np.full(num_thumbnails, peak_pos_f)
                else:
                    normalized_timestamps = np.random.triangular(left_fallback, peak_pos_f, right_fallback, num_thumbnails)

            else:
                normalized_timestamps = np.random.triangular(left_bound, mode, right_bound, num_thumbnails)

        case Distribution.NORMAL:
            if num_thumbnails == 0: return []
            sigma = max(float(processor.concentration), 1e-6)

            initial_sample_size = num_thumbnails * 10 if num_thumbnails > 1 else 20
            samples = np.random.normal(float(processor.peak_pos), sigma, initial_sample_size)
            samples_clipped = np.clip(samples, 0, 1)

            if num_thumbnails == 1:
                normalized_timestamps = np.array([np.median(samples_clipped)])
            else:
                percentiles_to_sample = np.linspace(0, 100, num_thumbnails)
                normalized_timestamps = np.percentile(samples_clipped, percentiles_to_sample)
        case _:
            logger.error(f"Unknown distribution: {current_distribution}. Defaulting to UNIFORM.")
            if num_thumbnails == 0: return []
            if num_thumbnails == 1: normalized_timestamps = np.array([0.5])
            else: normalized_timestamps = np.linspace(0, 1, num_thumbnails + 2)[1:-1]

    normalized_timestamps = np.unique(np.clip(normalized_timestamps, 0.01, 0.99))

    if len(normalized_timestamps) < num_thumbnails and num_thumbnails > 0:
        logger.trace(f"Distribution generated {len(normalized_timestamps)} unique timestamps, need {num_thumbnails}. Augmenting.")
        if len(normalized_timestamps) > 0 :
            uniform_fill = np.linspace(0.01, 0.99, num_thumbnails)
            combined = np.concatenate((normalized_timestamps, uniform_fill))
            normalized_timestamps = np.unique(combined)
            if len(normalized_timestamps) > num_thumbnails:
                indices = np.round(np.linspace(0, len(normalized_timestamps) - 1, num_thumbnails)).astype(int)
                normalized_timestamps = normalized_timestamps[indices]
        else:
            normalized_timestamps = np.linspace(0.01, 0.99, num_thumbnails)


    timestamps_in_seconds = [ts * duration for ts in normalized_timestamps]

    if len(timestamps_in_seconds) > num_thumbnails:
        indices = np.round(np.linspace(0, len(timestamps_in_seconds) - 1, num_thumbnails)).astype(int)
        timestamps_in_seconds = [timestamps_in_seconds[i] for i in indices]
    elif len(timestamps_in_seconds) < num_thumbnails and num_thumbnails > 0:
        if timestamps_in_seconds:
            timestamps_in_seconds.extend([timestamps_in_seconds[-1]] * (num_thumbnails - len(timestamps_in_seconds)))
        else:
            timestamps_in_seconds = [(duration * 0.5)] * num_thumbnails

    return sorted(list(set(timestamps_in_seconds)))


def generate_thumbnails(processor, video_path: Path, progress_callback=None, command_callback=None, stop_flag_check=None):
    logger.debug(f"Starting thumbnail generation for {video_path} using cache_dir: {processor.cache_dir}")
    if stop_flag_check and stop_flag_check():
        logger.info(f"Thumbnail generation for {video_path} cancelled before start.")
        return [], [], 0

    cache_json_file_path = get_cache_path(processor, video_path)
    video_specific_cache_dir = processor.cache_dir / video_path.name
    video_specific_cache_dir.mkdir(parents=True, exist_ok=True)

    if not cache_json_file_path.exists():
        logger.debug(f"No cache JSON found at {cache_json_file_path} for {video_path}. Generating new thumbnails.")
    elif not is_cache_valid(processor, video_path):
        logger.debug(f"Cache invalid for {video_path} at {cache_json_file_path}. Clearing cache.")
        clear_cache(processor, video_path)
    else:
        try:
            with open(cache_json_file_path, 'r') as f:
                cache = json.load(f)
            if all(k in cache for k in ['thumbnails', 'timestamps', 'duration']):
                logger.debug(f"Using valid cache from {cache_json_file_path} for {video_path}")
                if processor.update_callback:
                    processor.update_callback(video_path, cache['thumbnails'], cache['timestamps'], cache['duration'])
                return cache['thumbnails'], cache['timestamps'], cache['duration']
            else:
                logger.warning(f"Cache at {cache_json_file_path} for {video_path} missing essential keys. Regenerating.")
                clear_cache(processor, video_path)
        except json.JSONDecodeError:
            logger.warning(f"Cache at {cache_json_file_path} for {video_path} is corrupted. Regenerating.")
            clear_cache(processor, video_path)
        except Exception as e:
            logger.warning(f"Error loading cache from {cache_json_file_path} for {video_path}: {e}. Regenerating.")
            clear_cache(processor, video_path)

    thumbnails = []
    generated_timestamps = []
    video_duration = 0

    try:
        video_duration = get_video_duration(video_path)
        if video_duration <= 0:
            logger.warning(f"Could not determine valid duration for {video_path} ({video_duration}s). Skipping.")
            if processor.update_callback:
                placeholder_filenames = []
                for i in range(processor.thumbnails_per_video):
                    ph_name = f"placeholder_error_{i}.jpg"
                    ph_path = video_specific_cache_dir / ph_name
                    try:
                        generate_placeholder_thumbnail(processor).save(ph_path)
                        placeholder_filenames.append(ph_name)
                    except Exception as e_ph:
                        logger.error(f"Failed to save placeholder {ph_path}: {e_ph}")
                processor.update_callback(video_path, placeholder_filenames, [0.0]*len(placeholder_filenames), 0.0)
            return [], [], 0

        target_timestamps = generate_distributed_timestamps(processor, video_duration)
        if not target_timestamps:
            logger.warning(f"No target timestamps generated for {video_path}. Skipping.")
            if processor.update_callback:
                processor.update_callback(video_path, [], [], video_duration)
            return [], [], video_duration

        actual_num_thumbnails = min(len(target_timestamps), processor.thumbnails_per_video)

        for i, timestamp in enumerate(target_timestamps[:actual_num_thumbnails]):
            if stop_flag_check and stop_flag_check():
                logger.info(f"Thumbnail generation for {video_path} cancelled during loop at timestamp {timestamp}.")
                break

            thumb_filename = f"thumb_{i:03d}.jpg"
            thumb_path = video_specific_cache_dir / thumb_filename

            ffmpeg_cmd_successful = False

            # Base scale filter: preserve aspect ratio by specifying width and -1 for height.
            scale_vf = f'scale={processor.thumbnail_width}:-1'
            # Common output format for good compatibility.
            format_vf = 'format=yuv420p'
            # Combine scale and format, can be extended with other filters.
            vf_complex = f'{scale_vf},{format_vf}'


            cmd_attempts = [
                # Attempt 1: Standard HW accel (if available), precise seek before -i.
                ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-hwaccel', 'cuda',
                 '-ss', str(timestamp), '-i', str(video_path),
                 '-vf', vf_complex,
                 '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                 '-c:v', 'mjpeg', '-y', str(thumb_path)],

                # Attempt 2: Standard SW decoding, precise seek before -i.
                ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                 '-ss', str(timestamp), '-i', str(video_path),
                 '-vf', vf_complex,
                 '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                 '-c:v', 'mjpeg', '-y', str(thumb_path)],

                # Attempt 3: SW decoding, seek after -i (slower, but can be more robust for some files).
                ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                 '-i', str(video_path), '-ss', str(timestamp),
                 '-vf', vf_complex,
                 '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                 '-c:v', 'mjpeg', '-y', str(thumb_path)],

                # Attempt 4: SW, copyts for timestamp accuracy, output as image2.
                # `-an` (no audio), `-f image2` (force image output).
                ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                 '-copyts', '-ss', str(timestamp), '-i', str(video_path),
                 '-vf', vf_complex,
                 '-vframes', '1', '-an', '-f', 'image2', '-qscale:v', str(processor.thumbnail_quality),
                 '-y', str(thumb_path)],

                # Attempt 5: SW, precise seek, but try seeking to a slightly earlier keyframe using -seek_timestamp
                # This requires ffprobe or similar to find the nearest keyframe, which is complex here.
                # A simpler approximation: seek slightly *before* the target timestamp.
                # The -skip_frame option with -copyinkf might be better but also complex.
                # Let's try a small negative offset with -ss.
                ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                 '-ss', str(max(0, timestamp - 0.5)), '-i', str(video_path), # Seek 0.5s earlier
                 '-ss', '0.5', # Then seek forward 0.5s from that point (relative seek if -ss is after -i)
                 # This effectively means -i ... -ss timestamp
                 '-vf', vf_complex,
                 '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                 '-c:v', 'mjpeg', '-y', str(thumb_path)],

                # Attempt 6: Force keyframe seeking only using -skip_frame nokey.
                # This is typically for -ss before -i. If a keyframe is not at `timestamp`, it will take the one *before* it.
                # Then we need to seek *within* that segment. This is getting too complex without ffprobe.
                # Simpler: Use `-ss` before `-i` and hope it lands on a keyframe near `timestamp`.
                # If it's not accurate, the previous attempts might handle it better.
                # Add a variation with `-force_key_frames` for output (though less relevant for single image).
                # What might be more useful is to explicitly ask for a keyframe *near* the timestamp.
                # One way is to use a select filter: vf select='eq(pict_type\,I)'
                # This selects only I-frames. Combine with -ss for a window.

                # Attempt 6: -ss before -i, specify output pix_fmt explicitly for mjpeg
                ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                 '-ss', str(timestamp), '-i', str(video_path),
                 '-vf', vf_complex, '-pix_fmt', 'yuvj420p', # Common for JPEG
                 '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                 '-c:v', 'mjpeg', '-y', str(thumb_path)],

                # Attempt 7: No HW accel, seek after -i, use a slightly different timestamp again
                ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                 '-i', str(video_path), '-ss', str(timestamp + 0.05), # Tiny positive offset
                 '-vf', vf_complex,
                 '-vframes', '1', '-qscale:v', str(processor.thumbnail_quality),
                 '-c:v', 'mjpeg', '-y', str(thumb_path)],

                # Attempt 8: Similar to 7, but try to output a PNG instead of MJPEG, sometimes helps with decoders/encoders.
                # PNG is lossless but larger; for a single frame, it's an alternative.
                # We'd need to change thumb_filename extension or convert later if sticking to JPG.
                # For now, let's stick to JPG output for consistency in cache.
                # This attempt will be a repeat of a previous one with a slight variation if needed.
                # Let's try a very basic command as a last resort.
                ['ffmpeg', '-hide_banner', '-loglevel', 'warning', # More verbose log for this one
                 '-i', str(video_path), '-ss', str(timestamp),
                 '-vframes', '1', '-s', f'{processor.thumbnail_width}x-1', # Simpler scale
                 '-f', 'image2', '-q:v', str(processor.thumbnail_quality), # alias for qscale:v
                 '-y', str(thumb_path)],
            ]


            for cmd_idx, cmd in enumerate(cmd_attempts):
                if stop_flag_check and stop_flag_check(): break

                logger.trace(f"Attempt {cmd_idx+1} for {video_path.name} @{timestamp:.2f}s: {' '.join(cmd)}")
                if command_callback:
                    command_callback(' '.join(cmd), str(thumb_path), str(video_path))

                try:
                    result = subprocess.run(cmd, capture_output=True, text=False, timeout=45)
                    if result.returncode == 0 and thumb_path.exists() and thumb_path.stat().st_size > 100:
                        try:
                            img = Image.open(thumb_path)
                            img.verify()
                            img.close()

                            thumbnails.append(thumb_filename)
                            generated_timestamps.append(timestamp)
                            ffmpeg_cmd_successful = True
                            logger.debug(f"Successfully generated thumbnail {thumb_path.name} (Attempt {cmd_idx+1})")
                            break
                        except Exception as e_pil:
                            logger.warning(f"Pillow verification failed for {thumb_path.name} (Attempt {cmd_idx+1}): {e_pil}. Retrying FFmpeg.")
                            if thumb_path.exists(): thumb_path.unlink(missing_ok=True)
                    else:
                        error_output = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "No stderr"
                        logger.warning(f"FFmpeg attempt {cmd_idx+1} failed for {video_path.name} at {timestamp:.2f}s. Code: {result.returncode}. Error: {error_output[:300]}")
                        if thumb_path.exists() and thumb_path.stat().st_size <= 100 :
                            thumb_path.unlink(missing_ok=True)
                except subprocess.TimeoutExpired:
                    logger.warning(f"FFmpeg attempt {cmd_idx+1} timed out for {video_path.name} at {timestamp:.2f}s.")
                except Exception as e_ffmpeg:
                    logger.error(f"Exception during FFmpeg attempt {cmd_idx+1} for {video_path.name} at {timestamp:.2f}s: {e_ffmpeg}", exc_info=False) # exc_info=False for less noise

            if not ffmpeg_cmd_successful:
                logger.warning(f"All FFmpeg attempts failed for {video_path.name} at {timestamp:.2f}s. Generating placeholder.")
                placeholder_img = generate_placeholder_thumbnail(processor)
                try:
                    placeholder_img.save(thumb_path)
                    thumbnails.append(thumb_filename)
                    generated_timestamps.append(timestamp)
                except Exception as e_placeholder:
                    logger.error(f"Failed to save placeholder thumbnail for {video_path.name} at {timestamp:.2f}s: {e_placeholder}")

            if progress_callback:
                progress_val = ((i + 1) / actual_num_thumbnails) * 100
                progress_callback(progress_val)

        if stop_flag_check and stop_flag_check():
            logger.info(f"Thumbnail generation for {video_path.name} was stopped. Processed {len(thumbnails)} thumbnails.")

        if len(generated_timestamps) < len(thumbnails):
            if generated_timestamps:
                last_ts = generated_timestamps[-1]
            else:
                last_ts = 0.0 if not target_timestamps else target_timestamps[len(generated_timestamps)]

            generated_timestamps.extend([last_ts] * (len(thumbnails) - len(generated_timestamps)))


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
                with open(cache_json_file_path, 'w') as f:
                    json.dump(cache_data, f, indent=4)
                logger.debug(f"Saved cache JSON to {cache_json_file_path} for {video_path.name}")
            except Exception as e:
                logger.error(f"Failed to write cache JSON to {cache_json_file_path} for {video_path.name}: {e}")

        if processor.update_callback:
            processor.update_callback(video_path, thumbnails, generated_timestamps, video_duration)

        return thumbnails, generated_timestamps, video_duration

    except Exception as e:
        logger.error(f"General error processing thumbnails for {video_path.name}: {e}", exc_info=True)
        if processor.update_callback:
            num_thumbs_fallback = processor.thumbnails_per_video if hasattr(processor, 'thumbnails_per_video') and processor.thumbnails_per_video > 0 else 1

            placeholder_filenames = []
            for i_ph in range(num_thumbs_fallback):
                ph_name_err = f"error_placeholder_{i_ph}.jpg"
                ph_path_err = video_specific_cache_dir / ph_name_err
                try:
                    generate_placeholder_thumbnail(processor).save(ph_path_err)
                    placeholder_filenames.append(ph_name_err)
                except Exception as e_ph_save:
                    logger.error(f"Failed to save error placeholder {ph_path_err}: {e_ph_save}")

            processor.update_callback(video_path, placeholder_filenames, [0.0]*len(placeholder_filenames), 0.0)
        return [], [], 0