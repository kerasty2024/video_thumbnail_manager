import subprocess
import os
from pathlib import Path

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
        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
        if file_size_mb < min_size_mb:
            logger.debug(f"File {file_path} filtered out: size {file_size_mb:.2f} MB < {min_size_mb} MB")
            return False

        # Check duration
        cmd = ['ffmpeg', '-i', str(file_path), '-hide_banner']
        result = subprocess.run(cmd, capture_output=True, text=False)
        output = result.stderr.decode('utf-8', errors='ignore')
        if 'Duration' not in output or 'No such file or directory' in output:
            logger.debug(f"File {file_path} filtered out: not a video or file not found")
            return False

        duration = 0
        for line in output.split('\n'):
            if 'Duration' in line:
                time_str = line.split('Duration: ')[1].split(',')[0]
                try:
                    h, m, s = map(float, time_str.split(':'))
                    duration = h * 3600 + m * 60 + s
                except ValueError as e:
                    logger.debug(f"File {file_path} filtered out: invalid duration format ({time_str})")
                    return False
                break
        if duration < min_duration_seconds:
            logger.debug(f"File {file_path} filtered out: duration {duration:.2f} s < {min_duration_seconds} s")
            return False

        logger.debug(f"File {file_path} passed filters: size {file_size_mb:.2f} MB, duration {duration:.2f} s")
        return True
    except Exception as e:
        logger.debug(f"File {file_path} filtered out: FFmpeg failed: {str(e)}")
        return False

def scan_videos(folder, min_size_mb, min_duration_seconds):
    """Scan a directory for video files, excluding 'cache' directories.

    Args:
        folder (str): Directory path to scan.
        min_size_mb (float): Minimum video size in MB.
        min_duration_seconds (float): Minimum video duration in seconds.

    Returns:
        list: List of Path objects for detected video files.
    """
    videos = []
    logger.debug(f"Scanning folder: {folder}")
    for root, dirs, files in os.walk(folder):
        # Skip directories named 'cache'
        if 'cache' in dirs:
            dirs.remove('cache')
        for file in files:
            file_path = Path(root) / file
            logger.debug(f"Checking file: {file_path}")
            if is_video_file(file_path, min_size_mb, min_duration_seconds):
                videos.append(file_path)
                logger.info(f"Detected video: {file_path}")
    logger.info(f"Total videos detected: {len(videos)}")
    return videos