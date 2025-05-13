import subprocess
import os
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time
import shutil

import numpy as np
from loguru import logger
from PIL import Image

from .distribution_enum import Distribution

class VideoProcessor:
    """Handles video processing, including thumbnail generation and caching."""

    def __init__(self, cache_dir, thumbnails_per_video, thumbnail_width, thumbnail_quality, concurrent_videos, min_size_mb, min_duration_seconds, update_callback=None, peak_pos=0.5, concentration=0.2, distribution='normal'):
        """Initialize the VideoProcessor with configuration settings.

        Args:
            cache_dir (str): Directory for caching thumbnails.
            thumbnails_per_video (int): Number of thumbnails to generate per video.
            thumbnail_width (int): Width of generated thumbnails in pixels.
            thumbnail_quality (int): Quality setting for thumbnails (1-31).
            concurrent_videos (int): Number of videos to process concurrently.
            min_size_mb (float): Minimum video size in MB to process.
            min_duration_seconds (float): Minimum video duration in seconds to process.
            update_callback (callable, optional): Callback for updating the UI with new thumbnails.
            peak_pos (float): Position of peak concentration (0 to 1).
            concentration (float): Spread of concentration (e.g., standard deviation for normal).
            distribution (str): Distribution model ('normal', 'uniform', 'triangular').
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.cwd() / "cache"
        self.thumbnails_per_video = thumbnails_per_video
        self.thumbnail_width = thumbnail_width
        self.thumbnail_quality = max(1, min(31, thumbnail_quality))
        self.concurrent_videos = concurrent_videos
        self.min_size_mb = min_size_mb
        self.min_duration_seconds = min_duration_seconds
        self.lock = Lock()
        self.update_callback = update_callback
        self.peak_pos = peak_pos
        self.concentration = concentration
        # Convert string to Distribution enum, default to NORMAL if invalid
        try:
            self.distribution = Distribution(distribution)
        except ValueError:
            logger.warning(f"Invalid distribution '{distribution}', defaulting to 'normal'")
            self.distribution = Distribution.NORMAL
        logger.debug(f"Initialized VideoProcessor with min_size_mb={self.min_size_mb}, min_duration_seconds={self.min_duration_seconds}, peak_pos={self.peak_pos}, concentration={self.concentration}, distribution={self.distribution.value}")

    def get_file_hash(self, file_path):
        """Generate a SHA-256 hash of the file content.

        Args:
            file_path (Path): Path to the file to hash.

        Returns:
            str: Hexadecimal hash of the file.
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def is_video_file(self, file_path):
        """Determine if a file is a video by checking FFmpeg duration metadata and applying filters.

        Args:
            file_path (Path): Path to the file to check.

        Returns:
            bool: True if the file is a video meeting criteria, False otherwise.
        """
        try:
            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
            if file_size_mb < self.min_size_mb:
                logger.debug(f"File {file_path} filtered out: size {file_size_mb:.2f} MB < {self.min_size_mb} MB")
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
            if duration < self.min_duration_seconds:
                logger.debug(f"File {file_path} filtered out: duration {duration:.2f} s < {self.min_duration_seconds} s")
                return False

            logger.debug(f"File {file_path} passed filters: size {file_size_mb:.2f} MB, duration {duration:.2f} s")
            return True
        except Exception as e:
            logger.debug(f"File {file_path} filtered out: FFmpeg failed: {str(e)}")
            return False

    def scan_videos(self, folder):
        """Scan a directory for video files, excluding 'cache' directories.

        Args:
            folder (str): Directory path to scan.

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
                if self.is_video_file(file_path):
                    videos.append(file_path)
                    logger.info(f"Detected video: {file_path}")
        logger.info(f"Total videos detected: {len(videos)}")
        return videos

    def get_cache_path(self, video_path):
        """Generate the cache path for a video's thumbnails.

        Args:
            video_path (Path): Path to the video file.

        Returns:
            Path: Path to the cache JSON file.
        """
        cache_base = video_path.parent / "cache" / video_path.name
        cache_base.parent.mkdir(exist_ok=True)
        cache_base.mkdir(exist_ok=True)
        return cache_base / f"{video_path.name}.json"

    def clear_cache(self, video_path):
        """Clear the cache directory for a specific video.

        Args:
            video_path (Path): Path to the video file.
        """
        cache_base = video_path.parent / "cache" / video_path.name
        if cache_base.exists():
            try:
                shutil.rmtree(cache_base)
                logger.debug(f"Cleared cache directory: {cache_base}")
                cache_base.mkdir(exist_ok=True)
            except OSError as e:
                logger.warning(f"Failed to clear cache directory {cache_base}: {e}")

    def is_cache_valid(self, video_path):
        """Check if the cache for a video is valid based on current settings.

        Args:
            video_path (Path): Path to the video file.

        Returns:
            bool: True if the cache is valid, False otherwise.
        """
        cache_path = self.get_cache_path(video_path)
        if not cache_path.exists():
            return False
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            cache_base = video_path.parent / "cache" / video_path.name
            thumbnail_paths = [cache_base / thumb for thumb in cache['thumbnails']]
            is_valid = (
                    cache['thumbnails_per_video'] == self.thumbnails_per_video and
                    cache['thumbnail_width'] == self.thumbnail_width and
                    cache['thumbnail_quality'] == self.thumbnail_quality and
                    cache['peak_pos'] == self.peak_pos and
                    cache['concentration'] == self.concentration and
                    cache['distribution'] == self.distribution.value and
                    all(path.exists() for path in thumbnail_paths)
            )
            logger.debug(f"Cache for {video_path} is {'valid' if is_valid else 'invalid'}")
            return is_valid
        except Exception as e:
            logger.warning(f"Cache for {video_path} is corrupted: {e}. Clearing cache.")
            self.clear_cache(video_path)
            return False

    def generate_placeholder_thumbnail(self):
        """Generate a gray placeholder thumbnail image.

        Returns:
            Image: Placeholder image with dimensions based on thumbnail_width.
        """
        return Image.new('RGB', (self.thumbnail_width, int(self.thumbnail_width * 9 / 16)), color='gray')

    def generate_distributed_timestamps(self, duration):
        """Generate thumbnail timestamps based on the selected distribution.

        Args:
            duration (float): Total duration of the video in seconds.

        Returns:
            list: List of timestamps in seconds.
        """
        match self.distribution:
            case Distribution.UNIFORM:
                normalized_timestamps = np.linspace(0, 1, self.thumbnails_per_video + 2)[1:-1]  # Exclude endpoints
            case Distribution.TRIANGULAR:
                normalized_timestamps = np.random.triangular(0, self.peak_pos, 1, self.thumbnails_per_video + 1)
                normalized_timestamps = sorted(normalized_timestamps)[:-1]  # Remove the last one if duplicated
            case Distribution.NORMAL:
                # Generate a larger pool of samples to capture the full distribution
                samples = np.random.normal(self.peak_pos, self.concentration, self.thumbnails_per_video * 10)
                normalized_timestamps = np.clip(samples, 0, 1)
                # Sort and select evenly spaced percentiles to ensure both tails are represented
                percentiles = np.linspace(0, 100, self.thumbnails_per_video)
                normalized_timestamps = np.percentile(normalized_timestamps, percentiles)
                normalized_timestamps = sorted(normalized_timestamps)
            case _:
                raise ValueError(f"Unknown distribution: {self.distribution}")

        # Ensure timestamps are strictly less than duration by clipping to [0, 0.99)
        normalized_timestamps = np.clip(normalized_timestamps, 0, 0.99)

        # Convert normalized timestamps to seconds
        timestamps = [timestamp * duration for timestamp in normalized_timestamps]
        logger.debug(f"normalized_timestamps={normalized_timestamps}")
        return sorted(timestamps)

    def get_video_duration(self, video_path):
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

    def generate_thumbnails(self, video_path, progress_callback=None, command_callback=None):
        """Generate thumbnails for a video and manage cache.

        Args:
            video_path (Path): Path to the video file.
            progress_callback (callable, optional): Callback to report thumbnail generation progress.
            command_callback (callable, optional): Callback to report FFmpeg commands.

        Returns:
            tuple: (list of thumbnail file names, list of corresponding timestamps in seconds, video duration in seconds)
        """
        logger.debug(f"Processing thumbnails for {video_path}")
        cache_path = self.get_cache_path(video_path)
        if not cache_path.exists():
            logger.debug(f"No cache found for {video_path}. Generating new thumbnails.")
        elif not self.is_cache_valid(video_path):
            logger.debug(f"Cache invalid for {video_path} due to config mismatch. Clearing cache.")
            self.clear_cache(video_path)
        else:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            logger.debug(f"Using valid cache for {video_path}")
            if self.update_callback:
                logger.debug(f"Calling update_callback for {video_path} with cached {len(cache['thumbnails'])} thumbnails")
                self.update_callback(video_path, cache['thumbnails'], cache['timestamps'], cache['duration'])
            return cache['thumbnails'], cache['timestamps'], cache['duration']

        try:
            # Get video duration
            duration = self.get_video_duration(video_path)
            if duration == 0:
                raise ValueError("Could not determine video duration")

            # Generate timestamps
            timestamps = self.generate_distributed_timestamps(duration)
            thumbnails = []
            start_time = time.time()
            cache_base = video_path.parent / "cache" / video_path.name
            cache_base.parent.mkdir(exist_ok=True)
            cache_base.mkdir(exist_ok=True)

            for i, timestamp in enumerate(timestamps):
                thumb_path = cache_base / f"{i}.jpg"
                cmd = [
                    'ffmpeg', '-hwaccel', 'cuda', '-ss', str(timestamp), '-i', str(video_path),
                    '-vf', f'scale={self.thumbnail_width}:-1', '-vframes', '1', '-qscale:v', str(self.thumbnail_quality),
                    '-c:v', 'mjpeg', '-y', str(thumb_path)
                ]
                if command_callback:
                    command_callback(' '.join(cmd), str(thumb_path), str(video_path))
                try:
                    result = subprocess.run(cmd, capture_output=True, text=False)
                    if result.returncode != 0:
                        error_msg = result.stderr.decode('utf-8', errors='ignore')
                        raise subprocess.CalledProcessError(result.returncode, cmd, stderr=error_msg)
                    thumbnails.append(f"{i}.jpg")
                    logger.debug(f"Generated thumbnail {thumb_path} at {timestamp}s")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to generate thumbnail for {video_path} at {timestamp}s: {e.stderr}")
                    placeholder = self.generate_placeholder_thumbnail()
                    placeholder.save(thumb_path, quality=self.thumbnail_quality)
                    thumbnails.append(f"{i}.jpg")
                    logger.debug(f"Generated placeholder thumbnail {thumb_path}")

                if progress_callback:
                    progress_callback((i + 1) / self.thumbnails_per_video * 100)

            # Save to cache
            cache_data = {
                'thumbnails': thumbnails,
                'timestamps': timestamps,  # Store timestamps in cache
                'duration': duration,  # Store duration in cache
                'thumbnails_per_video': self.thumbnails_per_video,
                'thumbnail_width': self.thumbnail_width,
                'thumbnail_quality': self.thumbnail_quality,
                'peak_pos': self.peak_pos,
                'concentration': self.concentration,
                'distribution': self.distribution.value
            }
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)

            logger.debug(f"Generated thumbnails for {video_path} in {time.time() - start_time:.2f}s")

            if self.update_callback:
                logger.debug(f"Calling update_callback for {video_path} with {len(thumbnails)} thumbnails")
                self.update_callback(video_path, thumbnails, timestamps, duration)

            return thumbnails, timestamps, duration

        except Exception as e:
            logger.error(f"Error processing {video_path}: {str(e)}")
            thumbnails = []
            timestamps = [0] * self.thumbnails_per_video  # Placeholder timestamps
            duration = 0  # Placeholder duration
            cache_base = video_path.parent / "cache" / video_path.name
            cache_base.parent.mkdir(exist_ok=True)
            cache_base.mkdir(exist_ok=True)
            for i in range(self.thumbnails_per_video):
                thumb_path = cache_base / f"{i}.jpg"
                placeholder = self.generate_placeholder_thumbnail()
                placeholder.save(thumb_path, quality=self.thumbnail_quality)
                thumbnails.append(f"{i}.jpg")
            cache_data = {
                'thumbnails': thumbnails,
                'timestamps': timestamps,
                'duration': duration,
                'thumbnails_per_video': self.thumbnails_per_video,
                'thumbnail_width': self.thumbnail_width,
                'thumbnail_quality': self.thumbnail_quality,
                'peak_pos': self.peak_pos,
                'concentration': self.concentration,
                'distribution': self.distribution.value
            }
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)

            if self.update_callback:
                logger.debug(f"Calling update_callback for {video_path} with {len(thumbnails)} thumbnails (error case)")
                self.update_callback(video_path, thumbnails, timestamps, duration)

            return thumbnails, timestamps, duration

    def process_videos(self, videos, progress_callback=None, error_callback=None, command_callback=None, completion_callback=None):
        """Process a list of videos concurrently.

        Args:
            videos (list): List of Path objects for video files.
            progress_callback (callable, optional): Callback to report progress.
            error_callback (callable, optional): Callback to report errors.
            command_callback (callable, optional): Callback to report FFmpeg commands.
            completion_callback (callable, optional): Callback to notify when processing is complete.
        """
        logger.info(f"Starting processing for {len(videos)} videos")
        with ThreadPoolExecutor(max_workers=self.concurrent_videos) as executor:
            future_to_video = {
                executor.submit(self.generate_thumbnails, video, progress_callback, command_callback): video
                for video in videos
            }
            for future in future_to_video:
                video = future_to_video[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing {video}: {e}")
                    if error_callback:
                        error_callback(video, str(e))
            if completion_callback:
                logger.debug("Calling completion_callback")
                completion_callback()
        logger.info("Finished processing all videos")