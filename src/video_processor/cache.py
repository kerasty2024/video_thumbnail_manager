import json
import shutil
from pathlib import Path

from loguru import logger

def get_cache_path(processor, video_path: Path) -> Path:
    """Generate the cache path for a video's thumbnails using the processor's cache_dir.

    Args:
        processor: The VideoProcessor instance (contains the base cache_dir).
        video_path (Path): Path to the video file.

    Returns:
        Path: Path to the cache JSON file.
    """
    # Use processor.cache_dir as the root for all caches
    # Create a subdirectory for each video within the main cache_dir
    cache_base_for_video = processor.cache_dir / video_path.name
    cache_base_for_video.mkdir(parents=True, exist_ok=True) # Ensure processor.cache_dir and video-specific subdir exist
    return cache_base_for_video / f"{video_path.name}.json"

def clear_cache(processor, video_path: Path):
    """Clear the cache directory for a specific video within the processor's cache_dir.

    Args:
        processor: The VideoProcessor instance.
        video_path (Path): Path to the video file.
    """
    cache_base_for_video = processor.cache_dir / video_path.name
    if cache_base_for_video.exists():
        try:
            shutil.rmtree(cache_base_for_video)
            logger.debug(f"Cleared cache directory: {cache_base_for_video}")
            # Recreate the directory if needed for subsequent operations,
            # or let get_cache_path handle it. For consistency:
            cache_base_for_video.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to clear cache directory {cache_base_for_video}: {e}")

def is_cache_valid(processor, video_path: Path) -> bool:
    """Check if the cache for a video is valid based on current settings.

    Args:
        processor: The VideoProcessor instance.
        video_path (Path): Path to the video file.

    Returns:
        bool: True if the cache is valid, False otherwise.
    """
    cache_file_path = get_cache_path(processor, video_path) # Use the updated get_cache_path
    if not cache_file_path.exists():
        return False
    try:
        with open(cache_file_path, 'r') as f:
            cache = json.load(f)

        # The base directory for this video's thumbnails is processor.cache_dir / video_path.name
        thumbnails_base_dir = processor.cache_dir / video_path.name
        thumbnail_paths = [thumbnails_base_dir / thumb for thumb in cache.get('thumbnails', [])]

        is_valid = (
                cache.get('thumbnails_per_video') == processor.thumbnails_per_video and
                cache.get('thumbnail_width') == processor.thumbnail_width and
                cache.get('thumbnail_quality') == processor.thumbnail_quality and
                cache.get('peak_pos') == processor.peak_pos and
                cache.get('concentration') == processor.concentration and
                cache.get('distribution') == processor.distribution.value and
                all(path.exists() for path in thumbnail_paths)
        )
        logger.debug(f"Cache for {video_path} (in {thumbnails_base_dir}) is {'valid' if is_valid else 'invalid'}")
        return is_valid
    except Exception as e:
        logger.warning(f"Cache for {video_path} (in {processor.cache_dir / video_path.name}) is corrupted or invalid: {e}. Clearing cache.")
        clear_cache(processor, video_path)
        return False