from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from loguru import logger

from src.video_processor.cache import get_cache_path, is_cache_valid, clear_cache
from src.video_processor.scanner import scan_videos, is_video_file
from src.video_processor.thumbnail import generate_thumbnails, generate_placeholder_thumbnail, get_video_duration
from src.distribution_enum import Distribution

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
        try:
            self.distribution = Distribution(distribution)
        except ValueError:
            logger.warning(f"Invalid distribution '{distribution}', defaulting to 'normal'")
            self.distribution = Distribution.NORMAL

    def scan_videos(self, folder):
        """Scan a directory for video files, excluding 'cache' directories."""
        return scan_videos(folder, self.min_size_mb, self.min_duration_seconds)

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
                executor.submit(
                    generate_thumbnails,
                    self,
                    video,
                    progress_callback,
                    command_callback
                ): video
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