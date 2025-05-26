from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget,
                             QFileDialog, QMessageBox, QLabel, QProgressBar, QTextEdit, QApplication,
                             QSizePolicy)
from PyQt6.QtCore import pyqtSignal, QThread, QObject, Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from pathlib import Path
import time
from PIL import Image, ImageQt

from loguru import logger

from src.config import Config
from src.video_processor.processor import VideoProcessor
from src.gui.input_tab import setup_input_tab
from src.gui.output_tab import setup_output_tab
from src.gui.process_tab import setup_process_tab
from src.gui.input_tab_modules.distribution import toggle_peak_concentration_pyqt, update_distribution_graph_pyqt
from src.gui.output_tab_modules.selection import delete_selected_pyqt, delete_unselected_pyqt, clear_all_selection_pyqt
from src.version import __version__
from src.distribution_enum import Distribution
from .worker import WorkerSignals, VideoProcessingWorker

class VideoThumbnailGUI(QMainWindow):
    _processor_update_signal = pyqtSignal(Path, list, list, float)

    def __init__(self):
        super().__init__()
        logger.info("VideoThumbnailGUI initializing...")
        self.config = Config()
        self.base_window_title = f"Video Thumbnail Manager by Kerasty ver. {__version__}"

        self.videos = {}
        self.selected_videos = set()
        self.current_thumbnail_pixmap = None
        self.total_videos = 0
        self.processed_thumbnails_count = 0
        self.total_thumbnails = 0
        self.start_time = None
        self.video_counter = 0
        self.current_crypto = "BTC"
        self.folder_to_scan_for_worker = ""

        self.processor = None
        self._processor_update_signal.connect(self.update_output_tab_slot)

        self.worker_thread = None
        self.processing_worker = None

        app_instance = QApplication.instance()
        if app_instance:
            app_instance.aboutToQuit.connect(self.cleanup_on_quit)
        else:
            logger.warning("QApplication.instance() is None, cannot connect aboutToQuit signal.")

        self.setup_gui_elements()
        self.setup_gui_layout()

        self.reinit_processor()

        if hasattr(self, 'use_peak_concentration_var') and self.use_peak_concentration_var:
            logger.debug("Setting initial state for use_peak_concentration checkbox and controls.")
            # Set checkbox state from config BEFORE calling toggle_peak_concentration
            # This ensures that toggle_peak_concentration uses the correct initial state
            # to set the visibility and values of related controls.
            self.use_peak_concentration_var.setChecked(self.config.get('use_peak_concentration'))
            self.toggle_peak_concentration() # Call to set initial state of related widgets
        else:
            logger.warning("use_peak_concentration_var not ready for initial toggle_peak_concentration call after setup.")

        logger.info("VideoThumbnailGUI initialized.")


    def setup_gui_elements(self):
        logger.debug("Initializing GUI element member variables to None.")
        self.folder_var = None; self.cache_folder_var = None; # Added cache_folder_var
        self.thumbs_var = None; self.thumbs_per_column_var = None;
        self.width_var = None; self.quality_var = None; self.concurrent_var = None;
        self.zoom_var = None; self.min_size_var = None; self.min_size_unit_var = None;
        self.min_duration_var = None; self.min_duration_unit_var = None;
        self.use_peak_concentration_var = None; self.peak_pos_var = None; self.peak_pos_label = None;
        self.concentration_var = None; self.concentration_label = None;
        self.distribution_var = None; self.distribution_label = None;
        self.distribution_canvas_widget = None;
        self.progress_bar = None; self.eta_label = None; self.completion_label = None;
        self.qr_label = None; self.qr_pixmap = None;
        self.selection_count_label = None; self.output_scroll_area = None;
        self.output_scrollable_widget = None; self.output_scrollable_layout = None;
        self.process_text_edit = None; self.thumbnail_preview_label = None;

    def setup_gui_layout(self):
        logger.debug("Setting up GUI layout.")
        self.setWindowTitle(self.base_window_title)
        primary_screen = QApplication.primaryScreen()
        screen_geometry = primary_screen.geometry() if primary_screen else QWidget().screen().geometry()

        default_width = int(screen_geometry.width() * 0.7) if screen_geometry else 1024
        default_height = int(screen_geometry.height() * 0.7) if screen_geometry else 768
        self.setGeometry(screen_geometry.x() + screen_geometry.width() // 8 if screen_geometry else 100,
                         screen_geometry.y() + screen_geometry.height() // 8 if screen_geometry else 100,
                         default_width, default_height)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.notebook = QTabWidget()
        self.layout.addWidget(self.notebook)

        self.input_tab = QWidget()
        self.input_frame = QVBoxLayout(self.input_tab)
        self.notebook.addTab(self.input_tab, "Input")

        self.output_tab_widget_ref = QWidget()
        self.output_frame_layout = QVBoxLayout(self.output_tab_widget_ref)
        self.notebook.addTab(self.output_tab_widget_ref, "Output")

        self.process_tab = QWidget()
        self.process_frame_layout = QVBoxLayout(self.process_tab)
        self.notebook.addTab(self.process_tab, "Process")

        setup_input_tab(self)

        self.selection_count_label = QLabel("0 of 0 selected")
        self.output_frame_layout.addWidget(self.selection_count_label, alignment=Qt.AlignmentFlag.AlignTop)
        setup_output_tab(self)

        setup_process_tab(self)

        self.update_selection_count()
        logger.info("GUI setup_gui_layout method complete.")


    def connect_worker_signals(self, worker_object_with_signals):
        if not worker_object_with_signals or not hasattr(worker_object_with_signals, 'signals'):
            logger.error("Cannot connect signals: worker_object_with_signals or its 'signals' attribute is None.")
            return

        actual_signals = worker_object_with_signals.signals

        try: actual_signals.progress.disconnect()
        except TypeError: pass
        try: actual_signals.thumbnail_progress.disconnect()
        except TypeError: pass
        try: actual_signals.eta_update.disconnect()
        except TypeError: pass
        try: actual_signals.completion_message.disconnect()
        except TypeError: pass
        try: actual_signals.error.disconnect()
        except TypeError: pass
        try: actual_signals.command.disconnect()
        except TypeError: pass
        try: actual_signals.processing_complete.disconnect()
        except TypeError: pass
        if hasattr(actual_signals, 'scan_complete'):
            try: actual_signals.scan_complete.disconnect()
            except TypeError: pass

        actual_signals.progress.connect(self.update_progress_bar_slot)
        actual_signals.thumbnail_progress.connect(self.update_process_tab_thumbnail_progress_slot)
        actual_signals.eta_update.connect(self.update_eta_label_slot)
        actual_signals.completion_message.connect(self.update_completion_label_slot)
        actual_signals.error.connect(self.report_error_slot_detailed)
        actual_signals.command.connect(self.update_command_slot)
        actual_signals.processing_complete.connect(self.on_processing_complete_slot)
        if hasattr(actual_signals, 'scan_complete'):
            actual_signals.scan_complete.connect(self.on_scan_complete_slot)
        logger.debug("Connected signals from processing_worker.")


    def reinit_processor(self):
        logger.debug("Reinitializing VideoProcessor...")
        try:
            thumbs_per_video_cfg = self.config.get('thumbnails_per_video')
            if not isinstance(thumbs_per_video_cfg, int) or thumbs_per_video_cfg <= 0:
                logger.warning(f"Invalid thumbnails_per_video from config: {thumbs_per_video_cfg}. Defaulting to 1.")
                thumbs_per_video_cfg = 1

            cache_dir_val = self.config.get('cache_dir')
            logger.info(f"Reinitializing processor with cache_dir: '{cache_dir_val}'")

            self.processor = VideoProcessor(
                cache_dir_val, # Use the value from config
                thumbs_per_video_cfg,
                self.config.get('thumbnail_width'),
                self.config.get('thumbnail_quality'),
                self.config.get('concurrent_videos'),
                self.config.get('min_size_mb'),
                self.config.get('min_duration_seconds'),
                update_callback=self.schedule_processor_update,
                peak_pos=self.config.get('thumbnail_peak_pos'),
                concentration=self.config.get('thumbnail_concentration'),
                distribution=self.config.get('thumbnail_distribution').value
            )
            logger.debug(f"VideoProcessor reinitialized with thumbs_per_video: {self.processor.thumbnails_per_video if self.processor else 'N/A'}")
        except Exception as e:
            logger.error(f"Failed to reinitialize VideoProcessor: {e}", exc_info=True)
            self.processor = None
            self.report_error_slot_detailed("Processor Error", f"Failed to initialize video processor:\n{e}")


    def schedule_processor_update(self, video_path, thumbnails, timestamps, duration):
        self._processor_update_signal.emit(Path(video_path), list(thumbnails), list(timestamps), float(duration))


    def browse_folder(self):
        current_folder = ""
        if hasattr(self, 'folder_var') and self.folder_var: current_folder = self.folder_var.text()
        if not current_folder: current_folder = self.config.get('default_folder')

        folder = QFileDialog.getExistingDirectory(self, "Select Folder", current_folder)
        if folder and hasattr(self, 'folder_var') and self.folder_var:
            self.folder_var.setText(folder)
            logger.debug(f"Selected folder: {folder}")

    def browse_cache_folder(self):
        """Opens a dialog to select the cache folder."""
        current_cache_folder = ""
        if hasattr(self, 'cache_folder_var') and self.cache_folder_var:
            current_cache_folder = self.cache_folder_var.text()

        if not current_cache_folder:
            # Default to config value or current working directory
            current_cache_folder = self.config.get('cache_dir') or str(Path.cwd())

        folder = QFileDialog.getExistingDirectory(self, "Select Cache Folder", current_cache_folder)
        if folder and hasattr(self, 'cache_folder_var') and self.cache_folder_var:
            self.cache_folder_var.setText(folder)
            logger.debug(f"Selected cache folder: {folder}")


    def report_error_slot_detailed(self, title_prefix, error_message):
        logger.error(f"Reported error: {title_prefix} - {error_message}")
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(f"Error: {title_prefix}")

        main_message_summary = str(error_message).splitlines()[0] if str(error_message) else "An unknown error occurred."
        if len(main_message_summary) > 150:
            main_message_summary = main_message_summary[:150] + "..."

        msg_box.setText(f"An error occurred with '{title_prefix}':\n{main_message_summary}")
        msg_box.setDetailedText(str(error_message))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        for child in msg_box.findChildren(QTextEdit):
            child.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
            child.setMinimumHeight(150)
            child.setMinimumWidth(450)

        msg_box.exec()

        if hasattr(self, 'process_text_edit') and self.process_text_edit:
            self.process_text_edit.append(f"ERROR: {title_prefix} - {error_message}\n")


    def update_selection_count(self):
        count = len(self.selected_videos)
        total = len(self.videos)
        if hasattr(self, 'selection_count_label') and self.selection_count_label:
            self.selection_count_label.setText(f"{count} of {total} selected")

    def update_output_tab_slot(self, video_path: Path, thumbnails: list, timestamps: list, duration: float):
        from src.gui.output_tab_modules.thumbnails import update_output_tab_pyqt
        logger.debug(f"GUI: Received _processor_update_signal for {video_path}")

        if not self.processor:
            logger.error("Processor not available in update_output_tab_slot. Reinitializing.")
            self.reinit_processor()
            if not self.processor:
                self.report_error_slot_detailed(f"Processor Error for {video_path.name}", "Video processor is not initialized. Cannot update output.")
                return

        update_output_tab_pyqt(self, video_path, thumbnails, timestamps, duration)

        actual_thumbs_per_video = self.processor.thumbnails_per_video if self.processor else self.config.get('thumbnails_per_video')
        if actual_thumbs_per_video <=0: actual_thumbs_per_video = 1

        self.processed_thumbnails_count += actual_thumbs_per_video
        if self.total_thumbnails > 0:
            overall_progress = min(100.0, (self.processed_thumbnails_count / self.total_thumbnails) * 100.0)
            self.update_progress_bar_slot(int(round(overall_progress)))
            self.update_eta_on_progress()

    def toggle_peak_concentration(self, *args):
        if hasattr(self, 'use_peak_concentration_var') and self.use_peak_concentration_var:
            toggle_peak_concentration_pyqt(self)

    def delete_selected(self): delete_selected_pyqt(self)
    def delete_unselected(self): delete_unselected_pyqt(self)
    def clear_all_selection(self): clear_all_selection_pyqt(self)

    def update_distribution_graph(self, *args):
        if hasattr(self, 'distribution_canvas_widget') and self.distribution_canvas_widget:
            update_distribution_graph_pyqt(self)

    def update_progress_bar_slot(self, value):
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.setValue(value)

    def update_process_tab_thumbnail_progress_slot(self, progress_percentage, current_thumb_num, total_thumbs_for_video):
        if hasattr(self, 'process_text_edit') and self.process_text_edit:
            self.process_text_edit.append(
                f"Thumbnail Progress: {progress_percentage:.2f}% "
                f"(Thumbnail {current_thumb_num}/{total_thumbs_for_video})\n"
            )
            self.process_text_edit.verticalScrollBar().setValue(self.process_text_edit.verticalScrollBar().maximum())

    def update_eta_on_progress(self):
        if self.start_time is None or self.processed_thumbnails_count == 0 or self.total_thumbnails == 0:
            self.update_eta_label_slot("ETA: --:--")
            return
        elapsed_time = time.time() - self.start_time
        if elapsed_time <= 1e-6:
            self.update_eta_label_slot("ETA: Calculating...")
            return
        thumbnails_per_second = self.processed_thumbnails_count / elapsed_time
        remaining_thumbnails = max(0, self.total_thumbnails - self.processed_thumbnails_count)
        if thumbnails_per_second > 1e-6:
            eta_seconds = remaining_thumbnails / thumbnails_per_second
            eta_minutes = int(eta_seconds // 60)
            eta_secs = int(eta_seconds % 60)
            self.update_eta_label_slot(f"ETA: {eta_minutes:02d}:{eta_secs:02d}")
        else:
            self.update_eta_label_slot("ETA: --:-- (slow)")

    def update_eta_label_slot(self, text):
        if hasattr(self, 'eta_label') and self.eta_label:
            self.eta_label.setText(text)

    def update_completion_label_slot(self, text):
        if hasattr(self, 'completion_label') and self.completion_label:
            self.completion_label.setText(text)
            if text and text != "Processing Complete!":
                QTimer.singleShot(5000, lambda: self.completion_label.setText("") if hasattr(self, 'completion_label') and self.completion_label and self.completion_label.text() == text else None)

    def update_command_slot(self, command, thumb_path_str, video_path_str):
        from src.gui.process_tab import update_process_text_pyqt, update_thumbnail_preview_pyqt
        if hasattr(self, 'process_text_edit') and self.process_text_edit:
            quoted_command = command.replace(str(video_path_str), f'"{video_path_str}"').replace(str(thumb_path_str), f'"{thumb_path_str}"')
            update_process_text_pyqt(self, f"Executing: {quoted_command}\n")
        if hasattr(self, 'thumbnail_preview_label') and self.thumbnail_preview_label:
            update_thumbnail_preview_pyqt(self, Path(thumb_path_str))

    def on_scan_complete_slot(self, total_videos, total_thumbnails):
        logger.info(f"GUI: Scan complete. Total videos: {total_videos}, Total thumbnails: {total_thumbnails}")
        self.total_videos = total_videos
        self.total_thumbnails = total_thumbnails

        output_tab_title = f"Output ({total_videos} video{'s' if total_videos != 1 else ''} scanned)"
        if self.total_videos == 0:
            if hasattr(self, 'completion_label') and self.completion_label:
                self.completion_label.setText("No videos found in the selected folder.")
            self.setWindowTitle(self.base_window_title)
            output_tab_title = "Output"
        else:
            if hasattr(self, 'completion_label') and self.completion_label:
                self.completion_label.setText(f"Scan complete. Processing {total_videos} videos...")
            self.setWindowTitle(f"{self.base_window_title} (Found {total_videos} videos)")


        output_tab_index = self.get_tab_index_by_text_prefix("Output")
        if output_tab_index != -1 and hasattr(self.notebook, 'setTabText'):
            self.notebook.setTabText(output_tab_index, output_tab_title)

        self.update_selection_count()


    def on_processing_complete_slot(self):
        logger.info("GUI: Processing complete signal received.")
        self.setWindowTitle(self.base_window_title)

        output_tab_index = self.get_tab_index_by_text_prefix("Output")
        if output_tab_index != -1 and hasattr(self.notebook, 'setTabText'):
            self.notebook.setTabText(output_tab_index, "Output")

        if hasattr(self, 'completion_label') and self.completion_label:
            self.completion_label.setText("Processing Complete!")
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.setValue(100)
        if hasattr(self, 'eta_label') and self.eta_label:
            self.eta_label.setText("ETA: 00:00")

        if hasattr(self, 'output_scrollable_widget') and self.output_scrollable_widget:
            self.output_scrollable_widget.adjustSize()
        if hasattr(self, 'output_scroll_area') and self.output_scroll_area:
            self.output_scroll_area.updateGeometry()

        self.update_selection_count()
        self._cleanup_worker_thread()
        logger.info("GUI: Processing complete actions finished.")

    def _cleanup_worker_thread(self):
        logger.debug("_cleanup_worker_thread called.")
        worker = self.processing_worker
        thread = self.worker_thread

        self.processing_worker = None
        self.worker_thread = None

        if thread:
            if thread.isRunning():
                logger.debug("Requesting worker thread to quit...")
                if worker and hasattr(worker, 'stop'): worker.stop()
                thread.quit()
                if not thread.wait(7000):
                    logger.warning("Worker thread did not finish in time. Terminating.")
                    thread.terminate()
                    if not thread.wait(2000):
                        logger.error("Worker thread failed to terminate even after forced termination.")
                logger.debug("Worker thread finished or was terminated.")
            else: logger.debug("Worker thread was not running or already finished.")
        else: logger.debug("No worker_thread instance to clean up.")
        logger.debug("Worker objects set to None for cleanup.")


    def start_processing_wrapper(self):
        from src.gui.input_tab_modules.progress import start_processing_pyqt
        logger.info("Start button clicked, calling start_processing_pyqt.")
        try:
            self.setWindowTitle(f"{self.base_window_title} (Scanning...)")
            output_tab_index = self.get_tab_index_by_text_prefix("Output")
            if output_tab_index != -1 and hasattr(self.notebook, 'setTabText'):
                self.notebook.setTabText(output_tab_index, "Output (Scanning...)")
            start_processing_pyqt(self)
        except Exception as e:
            logger.error(f"Error during start_processing_wrapper: {e}", exc_info=True)
            self.report_error_slot_detailed("Processing Start", f"Failed to start processing:\n{e}")
            self.setWindowTitle(self.base_window_title)
            output_tab_idx_err = self.get_tab_index_by_text_prefix("Output")
            if output_tab_idx_err != -1 and hasattr(self.notebook, 'setTabText'):
                self.notebook.setTabText(output_tab_idx_err, "Output")


    def get_tab_index_by_text_prefix(self, text_prefix_to_find):
        """Finds a tab by its text prefix (e.g., "Output" matches "Output (Scanning...)")."""
        if hasattr(self, 'notebook') and self.notebook:
            for i in range(self.notebook.count()):
                if self.notebook.tabText(i).startswith(text_prefix_to_find):
                    return i
        return -1


    def get_min_duration_seconds(self):
        if not (hasattr(self, 'min_duration_var') and self.min_duration_var and
                hasattr(self, 'min_duration_unit_var') and self.min_duration_unit_var): return 0.0
        min_duration = self.min_duration_var.value()
        unit = self.min_duration_unit_var.currentText()
        conversion = {'seconds': 1, 'minutes': 60, 'hours': 3600}
        return min_duration * conversion.get(unit, 1)


    def get_min_size_mb(self):
        if not (hasattr(self, 'min_size_var') and self.min_size_var and
                hasattr(self, 'min_size_unit_var') and self.min_size_unit_var): return 0.0
        min_size = self.min_size_var.value()
        unit = self.min_size_unit_var.currentText()
        conversion = {'KB': 1/1024, 'MB': 1, 'GB': 1024, 'TB': 1024*1024}
        return min_size * conversion.get(unit, 1)

    def cleanup_on_quit(self):
        logger.info("Application is about to quit. Performing final cleanup.")
        self._cleanup_worker_thread()

    def closeEvent(self, event):
        logger.info("Close event received. Saving config...")
        self.config.save()
        logger.info("Configuration saved.")
        logger.info("Proceeding with closing.")
        super().closeEvent(event)