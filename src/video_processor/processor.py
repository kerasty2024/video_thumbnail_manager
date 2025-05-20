from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed # as_completed をインポート
from threading import Lock

from loguru import logger

# cache と scanner のインポートは __init__.py 経由ではなく直接指定も可能
from .cache import get_cache_path, is_cache_valid, clear_cache
from .scanner import scan_videos # is_video_file は scanner 内で使用
from .thumbnail import generate_thumbnails # generate_placeholder_thumbnail, get_video_duration は thumbnail 内で使用
from src.distribution_enum import Distribution

class VideoProcessor:
    def __init__(self, cache_dir, thumbnails_per_video, thumbnail_width, thumbnail_quality, concurrent_videos, min_size_mb, min_duration_seconds, update_callback=None, peak_pos=0.5, concentration=0.2, distribution='normal'):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.cwd() / "cache"
        self.thumbnails_per_video = thumbnails_per_video
        self.thumbnail_width = thumbnail_width
        self.thumbnail_quality = max(1, min(31, thumbnail_quality))
        self.concurrent_videos = concurrent_videos
        self.min_size_mb = min_size_mb
        self.min_duration_seconds = min_duration_seconds
        # self.lock = Lock() # ThreadPoolExecutorが内部でロックを管理するため、通常は不要
        self.update_callback = update_callback
        self.peak_pos = peak_pos
        self.concentration = concentration
        try:
            self.distribution = Distribution(distribution)
        except ValueError:
            logger.warning(f"Invalid distribution '{distribution}', defaulting to 'normal'")
            self.distribution = Distribution.NORMAL

        self._stop_requested = False # 停止フラグを追加

    def request_stop(self):
        """Requests the processing to stop."""
        logger.info("VideoProcessor: Stop requested.")
        self._stop_requested = True

    def scan_videos(self, folder):
        # スキャン開始時に停止フラグをリセット（スキャン自体は止められないが、後続処理のため）
        # self._stop_requested = False # スキャンは別操作なので、ここではリセットしない方が良いかも
        return scan_videos(folder, self.min_size_mb, self.min_duration_seconds)

    def process_videos(self, videos, progress_callback=None, error_callback=None, command_callback=None, completion_callback=None, stop_flag_check=None):
        """Process a list of videos concurrently.

        Args:
            videos (list): List of Path objects for video files.
            progress_callback (callable, optional): Callback to report progress.
            error_callback (callable, optional): Callback to report errors.
            command_callback (callable, optional): Callback to report FFmpeg commands.
            completion_callback (callable, optional): Callback to notify when processing is complete.
            stop_flag_check (callable, optional): Callback to check if processing should stop.
                                                  Returns True if stop is requested.
        """
        logger.info(f"VideoProcessor: Starting processing for {len(videos)} videos")
        self._stop_requested = False # 新しい処理バッチの開始時にリセット

        processed_count = 0
        total_videos = len(videos)

        with ThreadPoolExecutor(max_workers=self.concurrent_videos) as executor:
            futures = {
                executor.submit(
                    generate_thumbnails, # この関数も stop_flag_check を受け取る必要がある
                    self, # VideoProcessorインスタンス (self) を渡す
                    video,
                    progress_callback, # 個々のビデオのサムネイル生成進捗
                    command_callback,
                    lambda: self._stop_requested or (stop_flag_check and stop_flag_check()) # generate_thumbnails に渡す停止チェック
                ): video
                for video in videos
            }

            for future in as_completed(futures): # 完了順に処理
                if self._stop_requested or (stop_flag_check and stop_flag_check()):
                    logger.info("VideoProcessor: Stop flag triggered, cancelling remaining tasks.")
                    # 残りのfutureをキャンセル (ただし実行中のものは止まらない場合がある)
                    for f_cancel in futures:
                        if not f_cancel.done():
                            f_cancel.cancel()
                    break # ループを抜ける

                video = futures[future]
                try:
                    # result = future.result() # generate_thumbnails の戻り値 (thumbnails, timestamps, duration)
                    # result は update_callback で処理されるので、ここでは例外チェックが主
                    future.result() # 例外が発生していればここで re-raise される
                    logger.debug(f"VideoProcessor: Successfully processed {video}")
                except Exception as e:
                    # future.cancel() でキャンセルされた場合、CancelledError が発生するかもしれない
                    if not isinstance(e,futures.CancelledError): # type: ignore
                        logger.error(f"VideoProcessor: Error processing {video}: {e}", exc_info=True)
                        if error_callback:
                            error_callback(video, str(e))
                finally:
                    processed_count +=1
                    # logger.debug(f"Video {processed_count}/{total_videos} future completed or cancelled.")


        logger.info(f"VideoProcessor: Finished processing batch. Processed {processed_count} futures.")
        if completion_callback:
            logger.debug("VideoProcessor: Calling completion_callback.")
            completion_callback()