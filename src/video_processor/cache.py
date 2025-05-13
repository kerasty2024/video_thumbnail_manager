import json
import shutil
from pathlib import Path

from loguru import logger

def get_cache_path(video_path):
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

def clear_cache(video_path):
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

def is_cache_valid(processor, video_path):
    """Check if the cache for a video is valid based on current settings.

    Args:
        processor: The VideoProcessor instance.
        video_path (Path): Path to the video file.

    Returns:
        bool: True if the cache is valid, False otherwise.
    """
    cache_path = get_cache_path(video_path)
    if not cache_path.exists():
        return False
    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        cache_base = video_path.parent / "cache" / video_path.name
        thumbnail_paths = [cache_base / thumb for thumb in cache['thumbnails']]
        is_valid = (
                cache['thumbnails_per_video'] == processor.thumbnails_per_video and
                cache['thumbnail_width'] == processor.thumbnail_width and
                cache['thumbnail_quality'] == processor.thumbnail_quality and
                cache['peak_pos'] == processor.peak_pos and
                cache['concentration'] == processor.concentration and
                cache['distribution'] == processor.distribution.value and
                all(path.exists() for path in thumbnail_paths)
        )
        logger.debug(f"Cache for {video_path} is {'valid' if is_valid else 'invalid'}")
        return is_valid
    except Exception as e:
        logger.warning(f"Cache for {video_path} is corrupted: {e}. Clearing cache.")
        clear_cache(video_path)
        return False