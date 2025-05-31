import subprocess
import os
from pathlib import Path
import re # Import regex module

from loguru import logger

def is_video_file(file_path, min_size_mb, min_duration_seconds):
    """Determine if a file is a video by checking FFmpeg duration metadata and applying filters.

    Args:
        file_path (Path): Path to the file to check.
        min_size_mb (float): Minimum video size in MB.
        min_duration_seconds (float): Minimum video duration in seconds.

    Returns:
        bool: True if the file is a video meeting criteria, False otherwise.
    """
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb < min_size_mb:
            logger.trace(f"File {file_path} filtered out (size): {file_size_mb:.2f} MB < {min_size_mb} MB")
            return False

        cmd = ['ffmpeg', '-i', str(file_path), '-hide_banner']
        result = subprocess.run(cmd, capture_output=True, text=False, timeout=10) # Added timeout
        output = result.stderr.decode('utf-8', errors='ignore')

        if result.returncode != 0 and 'Invalid data found when processing input' not in output and 'HTTP error' not in output : # Allow some ffmpeg errors if duration is found
            # Check if it's just a warning but duration is still parseable
            duration_found_despite_error = False
            if 'Duration' in output:
                for line_check_duration in output.split('\n'):
                    if 'Duration' in line_check_duration:
                        duration_found_despite_error = True
                        break
            if not duration_found_despite_error:
                logger.trace(f"File {file_path} filtered out (ffmpeg error): code {result.returncode}, {output[:200]}")
                return False


        if 'Duration' not in output :
            logger.trace(f"File {file_path} filtered out (no duration): not a video or unreadable.")
            return False

        duration = 0
        for line in output.split('\n'):
            if 'Duration' in line:
                time_str = line.split('Duration: ')[1].split(',')[0]
                try:
                    h, m, s = map(float, time_str.split(':'))
                    duration = h * 3600 + m * 60 + s
                except ValueError:
                    logger.trace(f"File {file_path} filtered out (invalid duration format): {time_str}")
                    return False
                break
        if duration < min_duration_seconds:
            logger.trace(f"File {file_path} filtered out (duration): {duration:.2f} s < {min_duration_seconds} s")
            return False

        logger.trace(f"File {file_path} passed filters: size {file_size_mb:.2f} MB, duration {duration:.2f} s")
        return True
    except subprocess.TimeoutExpired:
        logger.trace(f"File {file_path} filtered out (ffmpeg timeout).")
        return False
    except Exception as e:
        logger.trace(f"File {file_path} filtered out (ffmpeg check failed): {str(e)}")
        return False

def scan_videos(folder, min_size_mb, min_duration_seconds, excluded_words_str, use_regex, match_full_path):
    """Scan a directory for video files, excluding based on specified words/patterns.

    Args:
        folder (str): Directory path to scan.
        min_size_mb (float): Minimum video size in MB.
        min_duration_seconds (float): Minimum video duration in seconds.
        excluded_words_str (str): Comma-separated string of words/patterns to exclude.
        use_regex (bool): Whether to treat excluded_words as regex.
        match_full_path (bool): Whether to match against the full path or just filename/dirname.

    Returns:
        list: List of Path objects for detected video files.
    """
    videos = []
    logger.debug(f"Scanning folder: {folder} with exclusions: '{excluded_words_str}', regex: {use_regex}, match_full: {match_full_path}")

    excluded_patterns = []
    if excluded_words_str:
        excluded_patterns = [word.strip() for word in excluded_words_str.split(',') if word.strip()]

    if not excluded_patterns:
        logger.debug("No excluded words/patterns provided for scan.")

    for root, dirs, files in os.walk(folder, topdown=True):
        # Filter directories
        dirs_to_remove = set()
        for d in dirs:
            if d.lower() == 'cache' or d.lower() == 'vtm_cache_default': # Always exclude common cache dirs by name
                dirs_to_remove.add(d)
                logger.trace(f"Excluding standard cache directory: {Path(root) / d}")
                continue

            if excluded_patterns:
                target_text_for_dir = str(Path(root) / d) if match_full_path else d
                for pattern_str in excluded_patterns:
                    try:
                        excluded = False
                        if use_regex:
                            if re.search(pattern_str, target_text_for_dir):
                                excluded = True
                        else:
                            if pattern_str in target_text_for_dir:
                                excluded = True

                        if excluded:
                            dirs_to_remove.add(d)
                            logger.debug(f"Excluding directory: {Path(root) / d} due to pattern '{pattern_str}' on text '{target_text_for_dir}'")
                            break
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern '{pattern_str}' for directory check: {e}. Skipping this pattern.")

        # Modify dirs in-place for os.walk
        original_dirs_len = len(dirs)
        dirs[:] = [d for d in dirs if d not in dirs_to_remove]
        if len(dirs) < original_dirs_len:
            logger.trace(f"Pruned dirs in {root}: removed {original_dirs_len - len(dirs)}")


        # Filter files
        for file in files:
            file_path = Path(root) / file
            logger.trace(f"Checking file: {file_path}")

            if excluded_patterns:
                target_text_for_file = str(file_path) if match_full_path else file_path.name
                is_excluded_file = False
                for pattern_str in excluded_patterns:
                    try:
                        excluded = False
                        if use_regex:
                            if re.search(pattern_str, target_text_for_file):
                                excluded = True
                        else:
                            if pattern_str in target_text_for_file:
                                excluded = True

                        if excluded:
                            is_excluded_file = True
                            logger.debug(f"Excluding file: {file_path} due to pattern '{pattern_str}' on text '{target_text_for_file}'")
                            break
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern '{pattern_str}' for file check: {e}. Skipping this pattern.")

                if is_excluded_file:
                    continue

            if is_video_file(file_path, min_size_mb, min_duration_seconds):
                videos.append(file_path)
                logger.info(f"Detected video: {file_path}")
            else:
                logger.trace(f"File {file_path} did not pass video filters or was excluded.")

    logger.info(f"Total videos detected after filtering and exclusions: {len(videos)}")
    return videos