from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
from loguru import logger
# VideoProcessor や Distribution などのインポートは、
# VideoProcessingWorker が実際にそれらを使用する場合にここに追加します。

class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    thumbnail_progress = pyqtSignal(float, int, int)
    eta_update = pyqtSignal(str)
    completion_message = pyqtSignal(str)
    error = pyqtSignal(str, str)
    command = pyqtSignal(str, str, str)
    processing_complete = pyqtSignal()
    scan_complete = pyqtSignal(int, int) # スキャン完了シグナル (total_videos, total_thumbnails)


class VideoProcessingWorker(QObject):
    def __init__(self, gui_ref):
        super().__init__()
        self.gui = gui_ref
        self.signals = WorkerSignals()
        self._is_running = True

    def stop(self):
        logger.debug("VideoProcessingWorker stop method called.")
        self._is_running = False
        if hasattr(self.gui, 'processor') and self.gui.processor and hasattr(self.gui.processor, 'request_stop'):
            self.gui.processor.request_stop()

    def process_videos_thread(self):
        logger.debug("VideoProcessingWorker: process_videos_thread started.")
        try:
            if not self.gui.processor:
                logger.error("VideoProcessingWorker: VideoProcessor not initialized in GUI.")
                self.signals.error.emit("Setup Error", "VideoProcessor not available.")
                self.signals.processing_complete.emit()
                return

            # --- スキャン処理をワーカースレッドの冒頭に移動 ---
            if not hasattr(self.gui, 'folder_to_scan_for_worker') or not self.gui.folder_to_scan_for_worker:
                logger.error("VideoProcessingWorker: Folder to scan not provided.")
                self.signals.error.emit("Setup Error", "Folder to scan not specified.")
                self.signals.processing_complete.emit()
                return

            folder_to_scan = self.gui.folder_to_scan_for_worker
            logger.info(f"VideoProcessingWorker: Starting scan in folder: {folder_to_scan}")

            # スキャン実行
            videos_to_process = self.gui.processor.scan_videos(folder_to_scan)
            total_videos_found = len(videos_to_process)

            thumbs_per_video_actual = self.gui.processor.thumbnails_per_video if self.gui.processor else self.gui.config.get('thumbnails_per_video')
            if thumbs_per_video_actual <= 0: thumbs_per_video_actual = 1
            total_thumbnails_to_generate = total_videos_found * thumbs_per_video_actual

            logger.info(f"VideoProcessingWorker: Scan complete. Found {total_videos_found} videos, {total_thumbnails_to_generate} total thumbnails.")
            self.signals.scan_complete.emit(total_videos_found, total_thumbnails_to_generate) # GUIに結果を通知

            if not self._is_running: # スキャン中に停止要求があった場合
                logger.info("VideoProcessingWorker: Stop requested during/after scan.")
                self.signals.processing_complete.emit()
                return

            if not videos_to_process:
                logger.warning("VideoProcessingWorker: No videos found after scan.")
                self.signals.completion_message.emit("No videos found to process.") # GUIにメッセージ表示
                self.signals.processing_complete.emit()
                return

            # --- サムネイル生成処理 ---
            self.signals.completion_message.emit(f"Processing {total_videos_found} videos...") # スキャン完了後のメッセージ
            logger.info(f"VideoProcessingWorker: Starting thumbnail generation for {total_videos_found} videos.")

            self.gui.processor.process_videos(
                videos_to_process,
                progress_callback=lambda p: self.handle_thumbnail_progress_signal(p),
                error_callback=lambda v, e: self.signals.error.emit(str(v), e),
                command_callback=lambda cmd, thumb, vid: self.signals.command.emit(cmd, str(thumb), str(vid)),
                completion_callback=self.signals.processing_complete.emit,
                stop_flag_check=lambda: not self._is_running
            )

        except Exception as e:
            logger.error(f"Error in VideoProcessingWorker.process_videos_thread: {e}", exc_info=True)
            self.signals.error.emit("Processing Thread Error", str(e))
        finally:
            if self._is_running:
                logger.debug("VideoProcessingWorker: process_videos_thread reached finally, emitting processing_complete.")
                # completion_callback が呼ばれていれば二重になるが、QSignalなら問題ないはず
                self.signals.processing_complete.emit()
            else:
                logger.debug("VideoProcessingWorker: process_videos_thread reached finally, but was stopped.")

    def handle_thumbnail_progress_signal(self, progress_percentage_for_video):
        # ... (変更なし) ...
        if not self._is_running: return

        if not self.gui or not hasattr(self.gui, 'processor') or not self.gui.processor:
            return

        try:
            thumbs_per_video = self.gui.processor.thumbnails_per_video
            if thumbs_per_video <= 0:
                return
            current_thumb_num = int((progress_percentage_for_video / 100.0) * thumbs_per_video)
            self.signals.thumbnail_progress.emit(progress_percentage_for_video, current_thumb_num, thumbs_per_video)
        except Exception as e:
            logger.error(f"Error in handle_thumbnail_progress_signal: {e}", exc_info=True)