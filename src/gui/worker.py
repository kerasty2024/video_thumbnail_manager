from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
from loguru import logger
import time
# VideoProcessor や Distribution などのインポートは、
# VideoProcessingWorker が実際にそれらを使用する場合にここに追加します。

class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    thumbnail_progress = pyqtSignal(float, int, int)
    eta_update = pyqtSignal(str)
    completion_message = pyqtSignal(str)
    error = pyqtSignal(str, str)
    command = pyqtSignal(str, str, str)
    # scan_complete: total_videos_found, total_thumbnails_to_generate, scan_duration_seconds
    scan_complete = pyqtSignal(int, int, float)
    # processing_complete: thumbnail_generation_duration_seconds
    processing_complete = pyqtSignal(float)


class VideoProcessingWorker(QObject):
    def __init__(self, gui_ref):
        super().__init__()
        self.gui = gui_ref
        self.signals = WorkerSignals()
        self._is_running = True
        self.thumbnail_gen_start_time_for_duration_calc = 0.0
        self.ffmpeg_batch_duration = 0.0 # Stores the duration of the ffmpeg processing part

    def stop(self):
        logger.debug("VideoProcessingWorker stop method called.")
        self._is_running = False
        if hasattr(self.gui, 'processor') and self.gui.processor and hasattr(self.gui.processor, 'request_stop'):
            self.gui.processor.request_stop()

    def _handle_ffmpeg_batch_completed(self):
        """Called when the processor's batch of FFmpeg tasks completes."""
        if self._is_running:
            if self.thumbnail_gen_start_time_for_duration_calc > 0:
                duration = time.time() - self.thumbnail_gen_start_time_for_duration_calc
                logger.info(f"VideoProcessingWorker: FFmpeg batch completed. Effective thumbnail generation time: {duration:.2f}s.")
                self.ffmpeg_batch_duration = duration
            else:
                logger.warning("VideoProcessingWorker: FFmpeg batch completed, but start time was not recorded.")
                self.ffmpeg_batch_duration = 0.0
        else:
            logger.info("VideoProcessingWorker: FFmpeg batch noted completion, but worker was stopped.")
            self.ffmpeg_batch_duration = 0.0


    def process_videos_thread(self):
        logger.debug("VideoProcessingWorker: process_videos_thread started.")
        scan_duration_sec = 0.0
        # Initialize ffmpeg_batch_duration at the start of processing attempt
        self.ffmpeg_batch_duration = 0.0
        self.thumbnail_gen_start_time_for_duration_calc = 0.0

        try:
            if not self.gui.processor:
                logger.error("VideoProcessingWorker: VideoProcessor not initialized in GUI.")
                self.signals.error.emit("Setup Error", "VideoProcessor not available.")
                # No processing_complete signal here, finally block will handle it.
                return

            # --- Step 1: Scan for videos ---
            if not hasattr(self.gui, 'folder_to_scan_for_worker') or not self.gui.folder_to_scan_for_worker:
                logger.error("VideoProcessingWorker: Folder to scan not provided.")
                self.signals.error.emit("Setup Error", "Folder to scan not specified.")
                return

            folder_to_scan = self.gui.folder_to_scan_for_worker
            logger.info(f"VideoProcessingWorker: Starting scan in folder: {folder_to_scan}")

            scan_start_time = time.time()
            videos_to_process = self.gui.processor.scan_videos(folder_to_scan)
            scan_end_time = time.time()
            scan_duration_sec = scan_end_time - scan_start_time

            total_videos_found = len(videos_to_process)

            thumbs_per_video_actual = self.gui.processor.thumbnails_per_video if self.gui.processor else self.gui.config.get('thumbnails_per_video')
            if thumbs_per_video_actual <= 0: thumbs_per_video_actual = 1
            total_thumbnails_to_generate = total_videos_found * thumbs_per_video_actual

            logger.info(f"VideoProcessingWorker: Scan complete. Found {total_videos_found} videos ({scan_duration_sec:.2f}s), {total_thumbnails_to_generate} total thumbnails.")
            self.signals.scan_complete.emit(total_videos_found, total_thumbnails_to_generate, scan_duration_sec)

            if not self._is_running:
                logger.info("VideoProcessingWorker: Stop requested during/after scan.")
                return # Finally block will emit processing_complete

            if not videos_to_process:
                logger.warning("VideoProcessingWorker: No videos found after scan.")
                # scan_complete with 0 videos handles messaging in GUI.
                # processing_complete with 0.0 duration will be emitted by finally.
                return

            # --- Step 2: Generate thumbnails ---
            logger.info(f"VideoProcessingWorker: Starting thumbnail generation for {total_videos_found} videos.")
            self.thumbnail_gen_start_time_for_duration_calc = time.time()

            self.gui.processor.process_videos(
                videos_to_process,
                progress_callback=lambda p: self.handle_thumbnail_progress_signal(p),
                error_callback=lambda v, e: self.signals.error.emit(str(v), e),
                command_callback=lambda cmd, thumb, vid: self.signals.command.emit(cmd, str(thumb), str(vid)),
                completion_callback=self._handle_ffmpeg_batch_completed, # Use internal handler
                stop_flag_check=lambda: not self._is_running
            )
            # Note: process_videos is blocking. If it completes (or is interrupted and finishes),
            # _handle_ffmpeg_batch_completed will set self.ffmpeg_batch_duration.

        except Exception as e:
            logger.error(f"Error in VideoProcessingWorker.process_videos_thread: {e}", exc_info=True)
            self.signals.error.emit("Processing Thread Error", str(e))
        finally:
            # ffmpeg_batch_duration would have been set by _handle_ffmpeg_batch_completed if thumbnailing ran.
            # If scan failed or no videos, it remains 0.0.
            # If stopped during thumbnailing, _handle_ffmpeg_batch_completed might set it to partial or 0.0.
            logger.debug(f"VideoProcessingWorker: process_videos_thread reached finally. Emitting processing_complete with duration: {self.ffmpeg_batch_duration:.2f}s.")
            self.signals.processing_complete.emit(self.ffmpeg_batch_duration)
            self._is_running = False # Ensure worker state is reset

    def handle_thumbnail_progress_signal(self, progress_percentage_for_video):
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