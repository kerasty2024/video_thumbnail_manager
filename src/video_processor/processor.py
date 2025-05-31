from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from loguru import logger

from .cache import get_cache_path, is_cache_valid, clear_cache
from .scanner import scan_videos # scan_videos now takes exclusion parameters
from .thumbnail import generate_thumbnails
from src.distribution_enum import Distribution

class VideoProcessor:
    def __init__(self, cache_dir_str, thumbnails_per_video, thumbnail_width, thumbnail_quality,
                 concurrent_videos, min_size_mb, min_duration_seconds, update_callback=None,
                 peak_pos=0.5, concentration=0.2, distribution='normal',
                 excluded_words_str="", excluded_words_regex=False, excluded_words_match_full_path=False): # New args

        if cache_dir_str and cache_dir_str.strip():
            self.cache_dir = Path(cache_dir_str).resolve()
            logger.info(f"VideoProcessor using specified cache directory: {self.cache_dir}")
        else:
            self.cache_dir = Path.cwd() / "vtm_cache_default"
            logger.info(f"VideoProcessor using default cache directory: {self.cache_dir}")

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create or access cache directory {self.cache_dir}: {e}. Caching might fail.")

        self.thumbnails_per_video = thumbnails_per_video
        self.thumbnail_width = thumbnail_width
        self.thumbnail_quality = max(1, min(31, thumbnail_quality))
        self.concurrent_videos = concurrent_videos
        self.min_size_mb = min_size_mb
        self.min_duration_seconds = min_duration_seconds
        self.update_callback = update_callback
        self.peak_pos = peak_pos
        self.concentration = concentration
        try:
            self.distribution = Distribution(distribution)
        except ValueError:
            logger.warning(f"Invalid distribution '{distribution}', defaulting to 'normal'")
            self.distribution = Distribution.NORMAL

        self.excluded_words_str = excluded_words_str
        self.excluded_words_regex = excluded_words_regex
        self.excluded_words_match_full_path = excluded_words_match_full_path
        logger.debug(f"Processor initialized with excluded words: '{self.excluded_words_str}', "
                     f"regex: {self.excluded_words_regex}, "
                     f"match_full_path: {self.excluded_words_match_full_path}")

        self._stop_requested = False

    def request_stop(self):
        logger.info("VideoProcessor: Stop requested.")
        self._stop_requested = True

    def scan_videos(self, folder):
        """Scan videos applying exclusion rules."""
        logger.debug(f"Processor.scan_videos called with folder: {folder}, "
                     f"exclusions: '{self.excluded_words_str}', regex: {self.excluded_words_regex}, "
                     f"match_full: {self.excluded_words_match_full_path}")
        return scan_videos(folder, self.min_size_mb, self.min_duration_seconds,
                           self.excluded_words_str, self.excluded_words_regex, self.excluded_words_match_full_path)

    def process_videos(self, videos, progress_callback=None, error_callback=None, command_callback=None, completion_callback=None, stop_flag_check=None):
        logger.info(f"VideoProcessor: Starting processing for {len(videos)} videos. Cache root: {self.cache_dir}")
        self._stop_requested = False

        processed_count = 0
        total_videos = len(videos)

        with ThreadPoolExecutor(max_workers=self.concurrent_videos) as executor:
            futures = {
                executor.submit(
                    generate_thumbnails,
                    self,
                    video,
                    progress_callback,
                    command_callback,
                    lambda: self._stop_requested or (stop_flag_check and stop_flag_check())
                ): video
                for video in videos
            }

            for future in as_completed(futures):
                if self._stop_requested or (stop_flag_check and stop_flag_check()):
                    logger.info("VideoProcessor: Stop flag triggered, cancelling remaining tasks.")
                    for f_cancel in futures:
                        if not f_cancel.done():
                            f_cancel.cancel()
                    break

                video = futures[future]
                try:
                    future.result()
                    logger.debug(f"VideoProcessor: Successfully processed {video}")
                except Exception as e:
                    if not isinstance(e,futures.CancelledError): # type: ignore
                        logger.error(f"VideoProcessor: Error processing {video}: {e}", exc_info=True)
                        if error_callback:
                            error_callback(video, str(e))
                finally:
                    processed_count +=1

        logger.info(f"VideoProcessor: Finished processing batch. Processed {processed_count} futures.")
        if completion_callback:
            logger.debug("VideoProcessor: Calling completion_callback.")
            completion_callback()