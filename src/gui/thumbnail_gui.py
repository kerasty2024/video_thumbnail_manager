from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget,
                             QFileDialog, QMessageBox, QLabel, QProgressBar, QTextEdit, QApplication,
                             QSizePolicy, QComboBox)
from PyQt6.QtCore import pyqtSignal, QThread, QObject, Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from pathlib import Path
import time
import datetime
import json
from PIL import Image, ImageQt
import re
import os
from collections import deque

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
import typing
if typing.TYPE_CHECKING:
    from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
    from src.gui.output_tab_modules.canvas import CustomScrollArea
    from src.gui.input_tab_modules.controls import ClickableComboBox


class VideoThumbnailGUI(QMainWindow):
    _processor_update_signal = pyqtSignal(Path, list, list, float)
    MAX_UPDATES_PER_CYCLE = 3
    UPDATE_TIMER_INTERVAL = 50

    def __init__(self):
        super().__init__()
        logger.info("VideoThumbnailGUI initializing...")
        self.config = Config()
        self.base_window_title = f"Video Thumbnail Manager by Kerasty ver. {__version__}"

        self.videos = {}
        self.selected_videos = set()
        self.current_thumbnail_pixmap = None
        self.total_videos_scanned = 0
        self.processed_thumbnails_count = 0
        self.total_thumbnails_to_generate = 0
        self.start_time = None
        self.video_widget_processing_order_counter = 0
        self.current_crypto = "BTC"
        self.folder_to_scan_for_worker = ""
        self.last_keyword_search_index = -1
        self.current_sort_key = "Original Order"
        self.current_sort_ascending = True
        self.show_full_path_in_output = True
        self.is_processing = False
        self.max_display_order_ever_assigned = 0

        self.logs_dir = Path.cwd() / "logs"

        self.processor = None
        self._processor_update_signal.connect(self.enqueue_output_tab_update)

        self.worker_thread = None
        self.processing_worker = None

        app_instance = QApplication.instance()
        if app_instance:
            app_instance.aboutToQuit.connect(self.cleanup_on_quit)
        else:
            logger.warning("QApplication.instance() is None, cannot connect aboutToQuit signal.")

        self.setup_gui_elements()
        self.setup_gui_layout()

        self._output_update_queue = deque()
        self._output_update_timer = QTimer(self)
        self._output_update_timer.setSingleShot(True)
        self._output_update_timer.setInterval(self.UPDATE_TIMER_INTERVAL)
        self._output_update_timer.timeout.connect(self._process_queued_output_updates)

        if hasattr(self, 'excluded_words_var') and self.excluded_words_var:
            self.excluded_words_var.setText(self.config.get('excluded_words'))
        if hasattr(self, 'excluded_words_regex_var') and self.excluded_words_regex_var:
            self.excluded_words_regex_var.setChecked(self.config.get('excluded_words_regex'))
        if hasattr(self, 'excluded_words_match_full_path_var') and self.excluded_words_match_full_path_var:
            self.excluded_words_match_full_path_var.setChecked(self.config.get('excluded_words_match_full_path'))

        self.reinit_processor()

        if hasattr(self, 'use_peak_concentration_var') and self.use_peak_concentration_var:
            logger.debug("Setting initial state for use_peak_concentration checkbox and controls.")
            self.use_peak_concentration_var.setChecked(self.config.get('use_peak_concentration'))
            self.toggle_peak_concentration()
        else:
            logger.warning("use_peak_concentration_var not ready for initial toggle_peak_concentration call after setup.")

        if hasattr(self, 'show_full_path_checkbox') and self.show_full_path_checkbox:
            self.show_full_path_checkbox.setChecked(self.show_full_path_in_output)

        self.set_output_controls_enabled_state(True)
        self.load_folder_history()

        logger.info("VideoThumbnailGUI initialized.")


    def setup_gui_elements(self):
        logger.debug("Initializing GUI element member variables to None.")
        self.folder_combo_var: typing.Optional['ClickableComboBox'] = None
        self.cache_folder_var = None;
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

        self.selection_count_label = None
        self.last_deleted_label = None
        self.jump_widget = None
        self.sort_widget = None
        self.show_full_path_checkbox = None
        self.scroll_speed_widget = None

        self.output_scroll_area: typing.Optional['CustomScrollArea'] = None
        self.output_scrollable_widget = None; self.output_scrollable_layout = None;
        self.process_text_edit = None; self.thumbnail_preview_label = None;

        self.excluded_words_var = None;
        self.excluded_words_regex_var = None;
        self.excluded_words_match_full_path_var = None;

        self.delete_selected_button = None
        self.delete_unselected_button = None
        self.clear_selection_button = None

        self.log_output_checkbox = None


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
        setup_input_tab(self)
        if self.folder_combo_var:
            self.folder_combo_var.activated.connect(self.on_folder_combo_activated)


        self.output_tab_widget_ref = QWidget()
        self.output_frame_layout = QVBoxLayout(self.output_tab_widget_ref)
        self.notebook.addTab(self.output_tab_widget_ref, "Output")

        self.selection_count_label = QLabel("0 of 0 selected")
        setup_output_tab(self)

        self.process_tab = QWidget()
        self.process_frame_layout = QVBoxLayout(self.process_tab)
        self.notebook.addTab(self.process_tab, "Process")
        setup_process_tab(self)

        self.update_selection_count()
        self.update_last_deleted_label(None)
        logger.info("GUI setup_gui_layout method complete.")

    def on_folder_combo_activated(self, index: int):
        if not hasattr(self, 'folder_combo_var') or self.folder_combo_var is None:
            return

        selected_path = self.folder_combo_var.itemData(index)
        if selected_path and self.folder_combo_var.lineEdit():
            self.folder_combo_var.lineEdit().setText(str(selected_path))
            logger.debug(f"Folder history item activated: Set lineEdit to '{selected_path}'")


    def load_folder_history(self):
        if not hasattr(self, 'folder_combo_var') or self.folder_combo_var is None:
            logger.warning("Folder combo box not initialized. Cannot load history.")
            return

        current_text_in_editor = ""
        if self.folder_combo_var.lineEdit():
            current_text_in_editor = self.folder_combo_var.lineEdit().text()

        self.folder_combo_var.blockSignals(True)
        self.folder_combo_var.clear()

        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create logs directory {self.logs_dir}: {e}")
            if self.folder_combo_var.lineEdit():
                self.folder_combo_var.lineEdit().setPlaceholderText("Error loading history")
            self.folder_combo_var.setEnabled(False)
            self.folder_combo_var.blockSignals(False)
            return

        log_files = sorted(self.logs_dir.glob("*.json"), reverse=True)

        added_paths = set()

        if not log_files:
            if self.folder_combo_var.lineEdit():
                self.folder_combo_var.lineEdit().setPlaceholderText("No history available, enter path")
            self.folder_combo_var.setEnabled(True)
        else:
            self.folder_combo_var.setEnabled(True)
            if self.folder_combo_var.lineEdit():
                self.folder_combo_var.lineEdit().setPlaceholderText("Enter or select folder path")

            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    folder_path = config_data.get('default_folder')
                    if folder_path and folder_path not in added_paths:
                        added_paths.add(folder_path)

                        item_display_text = str(folder_path)
                        max_len = 80
                        if len(item_display_text) > max_len:
                            prefix = "..."
                            item_display_text = prefix + item_display_text[-(max_len - len(prefix)):]

                        self.folder_combo_var.addItem(item_display_text, userData=folder_path)
                except Exception as e:
                    logger.warning(f"Failed to load or parse log file {log_file}: {e}")

        self.folder_combo_var.blockSignals(False)

        final_text_to_restore = current_text_in_editor if current_text_in_editor else self.config.get('default_folder')

        found_idx = -1
        if final_text_to_restore:
            for i in range(self.folder_combo_var.count()):
                if self.folder_combo_var.itemData(i) == final_text_to_restore:
                    found_idx = i
                    break

        if found_idx != -1:
            self.folder_combo_var.setCurrentIndex(found_idx)
            if self.folder_combo_var.lineEdit():
                self.folder_combo_var.lineEdit().setText(final_text_to_restore)
        elif self.folder_combo_var.lineEdit():
            self.folder_combo_var.lineEdit().setText(final_text_to_restore)

        logger.debug(f"Folder history loaded. {self.folder_combo_var.count()} unique items in dropdown.")


    def browse_folder(self):
        current_path_in_combo = ""
        if hasattr(self, 'folder_combo_var') and self.folder_combo_var and self.folder_combo_var.lineEdit():
            current_path_in_combo = self.folder_combo_var.lineEdit().text()

        initial_dir_for_dialog = self.config.get('default_folder')
        if current_path_in_combo and os.path.isdir(current_path_in_combo):
            initial_dir_for_dialog = current_path_in_combo
        elif not initial_dir_for_dialog or not os.path.isdir(initial_dir_for_dialog):
            initial_dir_for_dialog = str(Path.cwd())

        folder_path_selected = QFileDialog.getExistingDirectory(self, "Select Folder", initial_dir_for_dialog)

        if folder_path_selected:
            self.folder_combo_var.blockSignals(True)

            existing_idx = -1
            for i in range(self.folder_combo_var.count()):
                if self.folder_combo_var.itemData(i) == folder_path_selected:
                    existing_idx = i
                    break

            if existing_idx != -1:
                self.folder_combo_var.setCurrentIndex(existing_idx)
            else:
                item_display_text = str(folder_path_selected)
                max_len = 80
                if len(item_display_text) > max_len:
                    prefix = "..."
                    item_display_text = prefix + item_display_text[-(max_len - len(prefix)):]

                self.folder_combo_var.insertItem(0, item_display_text, userData=folder_path_selected)
                self.folder_combo_var.setCurrentIndex(0)

            self.folder_combo_var.blockSignals(False)
            if self.folder_combo_var.lineEdit():
                self.folder_combo_var.lineEdit().setText(folder_path_selected)
            logger.debug(f"Folder browsed and selected: {folder_path_selected}")

    def browse_cache_folder(self):
        current_cache_folder = ""
        if hasattr(self, 'cache_folder_var') and self.cache_folder_var:
            current_cache_folder = self.cache_folder_var.text()

        initial_dir_for_dialog = self.config.get('cache_dir')
        if current_cache_folder and os.path.isdir(current_cache_folder):
            initial_dir_for_dialog = current_cache_folder
        elif not initial_dir_for_dialog or not os.path.isdir(initial_dir_for_dialog):
            initial_dir_for_dialog = str(Path.cwd())

        folder_path_selected = QFileDialog.getExistingDirectory(self, "Select Cache Folder", initial_dir_for_dialog)

        if folder_path_selected and hasattr(self, 'cache_folder_var') and self.cache_folder_var:
            self.cache_folder_var.setText(folder_path_selected)
            logger.debug(f"Selected cache folder: {folder_path_selected}")


    def set_output_controls_enabled_state(self, enabled: bool):
        if hasattr(self, 'sort_widget') and self.sort_widget:
            self.sort_widget.set_enabled_controls(enabled)
        if hasattr(self, 'delete_selected_button') and self.delete_selected_button:
            self.delete_selected_button.setEnabled(True)
        if hasattr(self, 'delete_unselected_button') and self.delete_unselected_button:
            self.delete_unselected_button.setEnabled(True)


    def connect_worker_signals(self, worker_object_with_signals):
        if not worker_object_with_signals or not hasattr(worker_object_with_signals, 'signals'):
            logger.error("Cannot connect signals: worker_object_with_signals or its 'signals' attribute is None.")
            return
        actual_signals = worker_object_with_signals.signals
        # ... (signal connections remain the same) ...
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
        try: actual_signals.scan_complete.disconnect()
        except TypeError: pass
        try: actual_signals.processing_complete.disconnect()
        except TypeError: pass

        actual_signals.progress.connect(self.update_progress_bar_slot)
        actual_signals.thumbnail_progress.connect(self.update_process_tab_thumbnail_progress_slot)
        actual_signals.eta_update.connect(self.update_eta_label_slot)
        actual_signals.completion_message.connect(self.update_completion_label_slot)
        actual_signals.error.connect(self.report_error_slot_detailed)
        actual_signals.command.connect(self.update_command_slot)
        actual_signals.scan_complete.connect(self.on_scan_complete_slot)
        actual_signals.processing_complete.connect(self.on_processing_complete_slot)
        logger.debug("Connected signals from processing_worker.")


    def reinit_processor(self):
        logger.debug("Reinitializing VideoProcessor...")
        try:
            thumbs_per_video_cfg = self.config.get('thumbnails_per_video')
            if not isinstance(thumbs_per_video_cfg, int) or thumbs_per_video_cfg <= 0:
                logger.warning(f"Invalid thumbnails_per_video from config: {thumbs_per_video_cfg}. Defaulting to 1.")
                thumbs_per_video_cfg = 1
            cache_dir_val = self.config.get('cache_dir')
            logger.info(f"Reinitializing processor with cache_dir string from config: '{cache_dir_val}'")
            excluded_words_str = self.config.get('excluded_words')
            excluded_words_regex = self.config.get('excluded_words_regex')
            excluded_words_match_full_path = self.config.get('excluded_words_match_full_path')
            self.processor = VideoProcessor(
                cache_dir_val, thumbs_per_video_cfg,
                self.config.get('thumbnail_width'), self.config.get('thumbnail_quality'),
                self.config.get('concurrent_videos'), self.config.get('min_size_mb'),
                self.config.get('min_duration_seconds'), update_callback=self.schedule_processor_update,
                peak_pos=self.config.get('thumbnail_peak_pos'),
                concentration=self.config.get('thumbnail_concentration'),
                distribution=self.config.get('thumbnail_distribution').value,
                excluded_words_str=excluded_words_str,
                excluded_words_regex=excluded_words_regex,
                excluded_words_match_full_path=excluded_words_match_full_path)
            logger.debug(f"VideoProcessor reinitialized. Effective cache_dir: {self.processor.cache_dir if self.processor else 'N/A'}")
        except Exception as e:
            logger.error(f"Failed to reinitialize VideoProcessor: {e}", exc_info=True)
            self.processor = None
            self.report_error_slot_detailed("Processor Error", f"Failed to initialize video processor:\n{e}")

    def schedule_processor_update(self, video_path, thumbnails, timestamps, duration):
        self._processor_update_signal.emit(Path(video_path), list(thumbnails), list(timestamps), float(duration))

    def report_error_slot_detailed(self, title_prefix, error_message):
        # ... (method remains the same) ...
        logger.error(f"Reported error: {title_prefix} - {error_message}")
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(f"Error: {title_prefix}")
        main_message_summary = str(error_message).splitlines()[0] if str(error_message) else "An unknown error occurred."
        if len(main_message_summary) > 150: main_message_summary = main_message_summary[:150] + "..."
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
        # ... (method remains the same) ...
        count = len(self.selected_videos)
        total_items_in_layout = self.output_scrollable_layout.count() if self.output_scrollable_layout else 0
        if hasattr(self, 'selection_count_label') and self.selection_count_label:
            self.selection_count_label.setText(f"{count} of {total_items_in_layout} selected")
        if hasattr(self, 'jump_widget') and self.jump_widget:
            self.jump_widget.set_max_jump_value(max(1, total_items_in_layout))

    def update_last_deleted_label(self, deleted_video_display_order: typing.Optional[int]):
        # ... (method remains the same) ...
        if hasattr(self, 'last_deleted_label') and self.last_deleted_label:
            if deleted_video_display_order is not None and deleted_video_display_order > 0:
                self.last_deleted_label.setText(f"(Last Del #: {deleted_video_display_order})")
            else: self.last_deleted_label.setText("")

    def enqueue_output_tab_update(self, video_path: Path, thumbnails: list, timestamps: list, duration: float):
        # ... (method remains the same) ...
        self._output_update_queue.append((video_path, thumbnails, timestamps, duration))
        if not self._output_update_timer.isActive(): self._output_update_timer.start()

    def _process_queued_output_updates(self):
        # ... (method remains the same) ...
        from src.gui.output_tab_modules.thumbnails import update_output_tab_pyqt
        items_processed_this_cycle = 0
        while self._output_update_queue and items_processed_this_cycle < self.MAX_UPDATES_PER_CYCLE:
            video_path, thumbnails, timestamps, duration = self._output_update_queue.popleft()
            if not self.processor:
                logger.error(f"Processor unavailable for {video_path}"); continue
            video_specific_cache_dir = self.processor.cache_dir / video_path.name
            self.video_widget_processing_order_counter += 1
            current_processing_order = self.video_widget_processing_order_counter
            update_output_tab_pyqt(self, video_path, thumbnails, timestamps, duration, video_specific_cache_dir, current_processing_order)
            items_processed_this_cycle += 1
            actual_thumbs_per_video = self.processor.thumbnails_per_video if self.processor else self.config.get('thumbnails_per_video')
            if actual_thumbs_per_video <= 0: actual_thumbs_per_video = 1
            self.processed_thumbnails_count += actual_thumbs_per_video
            if self.total_thumbnails_to_generate > 0:
                overall_progress = min(100.0, (self.processed_thumbnails_count / self.total_thumbnails_to_generate) * 100.0)
                self.update_progress_bar_slot(int(round(overall_progress)))
        if items_processed_this_cycle > 0:
            if self.total_thumbnails_to_generate > 0 and self.start_time is not None: self.update_eta_on_progress()
            if self.current_sort_key == "Original Order": self._update_all_video_entry_display_orders()
            self.update_selection_count()
            if hasattr(self, 'output_scrollable_widget') and self.output_scrollable_widget: self.output_scrollable_widget.adjustSize()
        if self._output_update_queue: self._output_update_timer.start()
        else:
            if items_processed_this_cycle > 0 and hasattr(self, 'output_scrollable_widget') and self.output_scrollable_widget: self.output_scrollable_widget.adjustSize()
        QApplication.processEvents()

    def _process_one_queued_output_update(self):
        # ... (method remains the same) ...
        if not self._output_update_queue: return
        from src.gui.output_tab_modules.thumbnails import update_output_tab_pyqt
        video_path, thumbnails, timestamps, duration = self._output_update_queue.popleft()
        if not self.processor:
            logger.error(f"Processor unavailable for {video_path}"); return
        video_specific_cache_dir = self.processor.cache_dir / video_path.name
        self.video_widget_processing_order_counter += 1
        current_processing_order = self.video_widget_processing_order_counter
        update_output_tab_pyqt(self, video_path, thumbnails, timestamps, duration, video_specific_cache_dir, current_processing_order)
        actual_thumbs_per_video = self.processor.thumbnails_per_video if self.processor else self.config.get('thumbnails_per_video')
        if actual_thumbs_per_video <= 0: actual_thumbs_per_video = 1
        self.processed_thumbnails_count += actual_thumbs_per_video
        if self.total_thumbnails_to_generate > 0:
            overall_progress = min(100.0, (self.processed_thumbnails_count / self.total_thumbnails_to_generate) * 100.0)
            self.update_progress_bar_slot(int(round(overall_progress)))


    def toggle_peak_concentration(self, *args):
        if hasattr(self, 'use_peak_concentration_var') and self.use_peak_concentration_var:
            toggle_peak_concentration_pyqt(self)

    def delete_selected(self):
        if self.is_processing:
            reply = QMessageBox.warning(self, "Confirm Deletion During Processing",
                                        "Processing is ongoing. Are you sure you want to proceed?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return

        max_display_order_of_deleted_items = 0
        items_to_be_deleted_paths = list(self.selected_videos) # Copy for iteration

        if items_to_be_deleted_paths and self.output_scrollable_layout:
            from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
            for i in range(self.output_scrollable_layout.count()):
                widget = self.output_scrollable_layout.itemAt(i).widget()
                if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path in items_to_be_deleted_paths:
                    if hasattr(widget, 'display_order') and widget.display_order > max_display_order_of_deleted_items:
                        max_display_order_of_deleted_items = widget.display_order

        delete_selected_pyqt(self) # This function handles actual file and UI removal

        self.update_selection_count()
        self.update_last_deleted_label(max_display_order_of_deleted_items) # Update label with max order of deleted

        if max_display_order_of_deleted_items > 0:
            # Attempt to jump to the position where the highest display order item was
            # jump_to_video_in_output_by_display_order will handle cases where that exact order no longer exists
            logger.debug(f"Attempting to scroll to position of (former) display order: {max_display_order_of_deleted_items}")
            self.jump_to_video_in_output_by_display_order(max_display_order_of_deleted_items)


    def delete_unselected(self):
        if self.is_processing:
            reply = QMessageBox.warning(self, "Confirm Deletion During Processing",
                                        "Processing is ongoing. Are you sure you want to proceed?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return

        max_display_order_of_deleted_items = 0
        unselected_video_paths = set(self.videos.keys()) - self.selected_videos

        if unselected_video_paths and self.output_scrollable_layout:
            from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
            for i in range(self.output_scrollable_layout.count()):
                widget = self.output_scrollable_layout.itemAt(i).widget()
                if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path in unselected_video_paths:
                    if hasattr(widget, 'display_order') and widget.display_order > max_display_order_of_deleted_items:
                        max_display_order_of_deleted_items = widget.display_order

        delete_unselected_pyqt(self)

        self.update_selection_count()
        self.update_last_deleted_label(max_display_order_of_deleted_items)

        if max_display_order_of_deleted_items > 0:
            logger.debug(f"Attempting to scroll to position of (former) display order: {max_display_order_of_deleted_items}")
            self.jump_to_video_in_output_by_display_order(max_display_order_of_deleted_items)


    def clear_all_selection(self): clear_all_selection_pyqt(self)

    def update_distribution_graph(self, *args):
        if hasattr(self, 'distribution_canvas_widget') and self.distribution_canvas_widget:
            update_distribution_graph_pyqt(self)

    def update_progress_bar_slot(self, value):
        if hasattr(self, 'progress_bar') and self.progress_bar: self.progress_bar.setValue(value)

    def update_process_tab_thumbnail_progress_slot(self, progress_percentage, current_thumb_num, total_thumbs_for_video): pass

    def update_eta_on_progress(self):
        # ... (method remains the same) ...
        if self.start_time is None or self.processed_thumbnails_count == 0 or self.total_thumbnails_to_generate == 0:
            self.update_eta_label_slot("ETA: --:--"); return
        elapsed_time = time.time() - self.start_time
        if elapsed_time <= 1e-6: self.update_eta_label_slot("ETA: Calculating..."); return
        current_processed_for_eta = min(self.processed_thumbnails_count, self.total_thumbnails_to_generate)
        thumbnails_per_second = current_processed_for_eta / elapsed_time
        remaining_thumbnails = max(0, self.total_thumbnails_to_generate - current_processed_for_eta)
        if thumbnails_per_second > 1e-6:
            eta_seconds = remaining_thumbnails / thumbnails_per_second
            eta_minutes, eta_secs = int(eta_seconds // 60), int(eta_seconds % 60)
            self.update_eta_label_slot(f"ETA: {eta_minutes:02d}:{eta_secs:02d}")
        else: self.update_eta_label_slot("ETA: --:--" if remaining_thumbnails > 0 else "ETA: 00:00")

    def update_eta_label_slot(self, text):
        # ... (method remains the same) ...
        if hasattr(self, 'eta_label') and self.eta_label: self.eta_label.setText(text)

    def update_completion_label_slot(self, text):
        # ... (method remains the same) ...
        if hasattr(self, 'completion_label') and self.completion_label:
            self.completion_label.setText(text)
            if text and text != "Processing Complete!":
                QTimer.singleShot(5000, lambda: self.completion_label.setText("") if hasattr(self, 'completion_label') and self.completion_label and self.completion_label.text() == text else None)

    def update_command_slot(self, command, thumb_path_str, video_path_str):
        # ... (method remains the same) ...
        from src.gui.process_tab import update_process_text_pyqt, update_thumbnail_preview_pyqt
        if hasattr(self, 'process_text_edit') and self.process_text_edit:
            quoted_command = command.replace(str(video_path_str), f'"{video_path_str}"').replace(str(thumb_path_str), f'"{thumb_path_str}"')
            update_process_text_pyqt(self, f"Executing: {quoted_command}\n")
        if hasattr(self, 'thumbnail_preview_label') and self.thumbnail_preview_label:
            update_thumbnail_preview_pyqt(self, Path(thumb_path_str))

    def on_scan_complete_slot(self, total_videos_found_by_scanner: int, total_thumbnails_to_be_generated: int, scan_duration_seconds: float):
        # ... (method remains the same) ...
        logger.info(f"GUI: Scan complete. Found: {total_videos_found_by_scanner} videos, To generate: {total_thumbnails_to_be_generated} thumbs. Scan time: {scan_duration_seconds:.2f}s")
        self.total_videos_scanned = total_videos_found_by_scanner
        self.total_thumbnails_to_generate = total_thumbnails_to_be_generated
        self.video_widget_processing_order_counter = 0
        self.processed_thumbnails_count = 0
        self.max_display_order_ever_assigned = 0
        if hasattr(self, 'process_text_edit') and self.process_text_edit:
            self.process_text_edit.append(f"動画スキャン完了: {self.total_videos_scanned} 件の動画を検出 (スキャン時間: {scan_duration_seconds:.2f}秒)\n")
        output_tab_title = f"Output ({self.total_videos_scanned} video{'s' if self.total_videos_scanned != 1 else ''} scanned)"
        if self.total_videos_scanned == 0:
            if hasattr(self, 'completion_label') and self.completion_label:
                self.completion_label.setText("No videos found in the selected folder or all were excluded.")
            self.setWindowTitle(self.base_window_title); output_tab_title = "Output"
            self.is_processing = False; self.set_output_controls_enabled_state(True)
            if hasattr(self, 'progress_bar'): self.progress_bar.setValue(0)
            if hasattr(self, 'eta_label'): self.eta_label.setText("ETA: --:--")
        else:
            if hasattr(self, 'completion_label') and self.completion_label:
                self.completion_label.setText(f"Scan complete. Processing {self.total_videos_scanned} videos...")
            self.setWindowTitle(f"{self.base_window_title} (Found {self.total_videos_scanned} videos)")
            self.start_time = time.time()
        output_tab_index = self.get_tab_index_by_text_prefix("Output")
        if output_tab_index != -1 and hasattr(self.notebook, 'setTabText'):
            self.notebook.setTabText(output_tab_index, output_tab_title)
        if hasattr(self, 'sort_widget') and self.sort_widget:
            self.sort_widget.sort_key_combo.setCurrentText("Original Order")
            self.sort_widget.sort_order_button.setChecked(True)
        self.current_sort_key = "Original Order"; self.current_sort_ascending = True
        self.update_selection_count()

    def on_processing_complete_slot(self, thumbnail_generation_duration_seconds: float):
        # ... (method remains the same) ...
        if self._output_update_timer.isActive(): self._output_update_timer.stop()
        logger.info("Processing any final queued UI updates before official completion...")
        while self._output_update_queue: self._process_one_queued_output_update()
        logger.info(f"GUI: Processing complete. Duration: {thumbnail_generation_duration_seconds:.2f}s.")
        self.is_processing = False; self.set_output_controls_enabled_state(True)
        self.setWindowTitle(self.base_window_title); self.last_keyword_search_index = -1
        if hasattr(self, 'process_text_edit') and self.process_text_edit:
            self.process_text_edit.append(f"全サムネイル生成完了 (総処理時間: {thumbnail_generation_duration_seconds:.2f}秒)\n" if self.total_videos_scanned > 0 else "処理完了 (対象ビデオなし)\n")
        self.sort_output_videos(self.current_sort_key, self.current_sort_ascending)
        output_tab_index = self.get_tab_index_by_text_prefix("Output")
        final_output_tab_text = "Output"
        current_display_count = self.output_scrollable_layout.count() if self.output_scrollable_layout else 0
        if current_display_count > 0: final_output_tab_text = f"Output ({current_display_count} video{'s' if current_display_count != 1 else ''})"
        if output_tab_index != -1 and hasattr(self.notebook, 'setTabText'):
            self.notebook.setTabText(output_tab_index, final_output_tab_text)
        if hasattr(self, 'completion_label') and self.completion_label:
            if self.total_videos_scanned > 0 or current_display_count > 0: self.completion_label.setText("Processing Complete!")
        if hasattr(self, 'progress_bar') and self.progress_bar: self.progress_bar.setValue(100 if (self.total_videos_scanned > 0 or current_display_count > 0) else 0)
        if hasattr(self, 'eta_label') and self.eta_label: self.eta_label.setText("ETA: 00:00" if (self.total_videos_scanned > 0 or current_display_count > 0) else "ETA: --:--")
        if hasattr(self, 'output_scrollable_widget') and self.output_scrollable_widget: self.output_scrollable_widget.adjustSize()
        if hasattr(self, 'output_scroll_area') and self.output_scroll_area: self.output_scroll_area.updateGeometry()
        self.update_selection_count(); self._cleanup_worker_thread()
        logger.info("GUI: Processing complete actions finished.")

    def _cleanup_worker_thread(self):
        # ... (method remains the same) ...
        logger.debug("_cleanup_worker_thread called.")
        worker, thread = self.processing_worker, self.worker_thread
        self.processing_worker, self.worker_thread = None, None
        if thread:
            if thread.isRunning():
                logger.debug("Requesting worker thread to quit...")
                if worker and hasattr(worker, 'stop'): worker.stop()
                thread.quit()
                if not thread.wait(7000):
                    logger.warning("Worker thread did not finish. Terminating."); thread.terminate()
                    if not thread.wait(3000): logger.error("Worker thread failed to terminate.")
                logger.debug("Worker thread finished or terminated.")
            else: logger.debug("Worker thread not running or already finished.")
        else: logger.debug("No worker_thread instance to clean up.")
        logger.debug("Worker objects set to None.")


    def start_processing_wrapper(self):
        # ... (method remains the same) ...
        from src.gui.input_tab_modules.progress import start_processing_pyqt
        logger.info("Start button clicked, calling start_processing_pyqt.")
        try:
            self.video_widget_processing_order_counter = 0; self.processed_thumbnails_count = 0
            self.total_thumbnails_to_generate = 0; self.total_videos_scanned = 0
            self.start_time = None; self.max_display_order_ever_assigned = 0
            self.update_last_deleted_label(None); self.last_keyword_search_index = -1
            if hasattr(self, 'sort_widget') and self.sort_widget:
                self.sort_widget.sort_key_combo.setCurrentText("Original Order")
                self.sort_widget.sort_order_button.setChecked(True)
            self.current_sort_key = "Original Order"; self.current_sort_ascending = True
            self.is_processing = True; self.set_output_controls_enabled_state(False)
            if hasattr(self, 'process_text_edit') and self.process_text_edit:
                self.process_text_edit.clear(); self.process_text_edit.append("Starting new processing job...\n")
            self.setWindowTitle(f"{self.base_window_title} (Scanning...)")
            output_tab_index = self.get_tab_index_by_text_prefix("Output")
            if output_tab_index != -1 and hasattr(self.notebook, 'setTabText'):
                self.notebook.setTabText(output_tab_index, "Output (Scanning...)")
            start_processing_pyqt(self)
        except Exception as e:
            logger.error(f"Error during start_processing_wrapper: {e}", exc_info=True)
            self.report_error_slot_detailed("Processing Start", f"Failed to start processing:\n{e}")
            self.setWindowTitle(self.base_window_title); self.is_processing = False
            self.set_output_controls_enabled_state(True)
            output_tab_idx_err = self.get_tab_index_by_text_prefix("Output")
            if output_tab_idx_err != -1 and hasattr(self.notebook, 'setTabText'):
                self.notebook.setTabText(output_tab_idx_err, "Output")

    def get_tab_index_by_text_prefix(self, text_prefix_to_find):
        # ... (method remains the same) ...
        if hasattr(self, 'notebook') and self.notebook:
            for i in range(self.notebook.count()):
                if self.notebook.tabText(i).startswith(text_prefix_to_find): return i
        return -1

    def get_min_duration_seconds(self):
        # ... (method remains the same) ...
        if not (hasattr(self, 'min_duration_var') and self.min_duration_var and hasattr(self, 'min_duration_unit_var') and self.min_duration_unit_var): return 0.0
        min_duration = self.min_duration_var.value()
        unit = self.min_duration_unit_var.currentText()
        return min_duration * {'seconds': 1, 'minutes': 60, 'hours': 3600}.get(unit, 1)

    def get_min_size_mb(self):
        # ... (method remains the same) ...
        if not (hasattr(self, 'min_size_var') and self.min_size_var and hasattr(self, 'min_size_unit_var') and self.min_size_unit_var): return 0.0
        min_size = self.min_size_var.value()
        unit = self.min_size_unit_var.currentText()
        return min_size * {'KB': 1/1024, 'MB': 1, 'GB': 1024, 'TB': 1024*1024}.get(unit, 1)

    def cleanup_on_quit(self):
        # ... (method remains the same) ...
        logger.info("Application quitting. Final cleanup.")
        if hasattr(self, '_output_update_timer') and self._output_update_timer.isActive(): self._output_update_timer.stop()
        self._cleanup_worker_thread()

    def closeEvent(self, event):
        # ... (method remains the same) ...
        logger.info("Close event. Saving config...")
        if self.is_processing:
            reply = QMessageBox.question(self, "Confirm Exit", "Processing ongoing. Exit anyway?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: event.ignore(); return
            else:
                logger.warning("Exiting during active processing.")
                if hasattr(self, '_output_update_timer') and self._output_update_timer.isActive(): self._output_update_timer.stop()
                self._cleanup_worker_thread()
        if hasattr(self, 'folder_combo_var') and self.folder_combo_var:
            current_folder_text = self.folder_combo_var.currentText()
            self.config.set('default_folder', current_folder_text)
        if hasattr(self, 'cache_folder_var') and self.cache_folder_var:
            self.config.set('cache_dir', self.cache_folder_var.text())
        if hasattr(self, 'excluded_words_var') and self.excluded_words_var:
            self.config.set('excluded_words', self.excluded_words_var.text())
        if hasattr(self, 'excluded_words_regex_var') and self.excluded_words_regex_var:
            self.config.set('excluded_words_regex', self.excluded_words_regex_var.isChecked())
        if hasattr(self, 'excluded_words_match_full_path_var') and self.excluded_words_match_full_path_var:
            self.config.set('excluded_words_match_full_path', self.excluded_words_match_full_path_var.isChecked())
        self.config.save()
        logger.info("Config saved. Closing.")
        super().closeEvent(event)

    def jump_to_video_in_output_by_display_order(self, target_display_order: int):
        # ... (method remains the same) ...
        logger.debug(f"Jump to display order: {target_display_order}")
        self.last_keyword_search_index = -1
        if not self.output_scrollable_layout or not self.output_scroll_area: return
        target_widget: typing.Optional['VideoEntryWidgetPyQt'] = None
        from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
        for i in range(self.output_scrollable_layout.count()):
            widget = self.output_scrollable_layout.itemAt(i).widget()
            if isinstance(widget, VideoEntryWidgetPyQt) and hasattr(widget, 'display_order') and widget.display_order == target_display_order:
                target_widget = widget; break
        if target_widget:
            self.output_scroll_area.ensureWidgetVisible(target_widget, 50, 50)
            logger.info(f"Jumped to display #{target_display_order} ({target_widget.video_path.name})")
            original_style = target_widget.styleSheet()
            target_widget.setStyleSheet(original_style + "QFrame { border: 2px solid orange; }")
            QTimer.singleShot(1000, lambda w=target_widget, s=original_style: w.setStyleSheet(s) if w else None)
        else:
            logger.warning(f"Display order {target_display_order} not found.")
            nearest_greater_widget: typing.Optional['VideoEntryWidgetPyQt'] = None
            min_greater_display_order = float('inf')
            for i in range(self.output_scrollable_layout.count()):
                widget = self.output_scrollable_layout.itemAt(i).widget()
                if isinstance(widget, VideoEntryWidgetPyQt) and hasattr(widget, 'display_order'):
                    if widget.display_order > target_display_order and widget.display_order < min_greater_display_order:
                        min_greater_display_order = widget.display_order; nearest_greater_widget = widget
            if nearest_greater_widget:
                self.output_scroll_area.ensureWidgetVisible(nearest_greater_widget, 50, 50)
                logger.info(f"Jumped to nearest greater: display #{nearest_greater_widget.display_order}")
                original_style = nearest_greater_widget.styleSheet()
                nearest_greater_widget.setStyleSheet(original_style + "QFrame { border: 2px solid orange; }")
                QTimer.singleShot(1000, lambda w=nearest_greater_widget, s=original_style: w.setStyleSheet(s) if w else None)
            else: self.update_completion_label_slot(f"Display order #{target_display_order} (or greater) not found.")


    def jump_to_video_in_output_by_keyword(self, keyword: str):
        # ... (method remains the same) ...
        logger.debug(f"Find keyword: '{keyword}'")
        if not self.output_scrollable_layout or not self.output_scroll_area: return
        if not keyword: self.update_completion_label_slot("Enter keyword."); return
        from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
        start_search_layout_index = self.last_keyword_search_index + 1
        found_widget: typing.Optional['VideoEntryWidgetPyQt'] = None
        for i in range(start_search_layout_index, self.output_scrollable_layout.count()):
            widget = self.output_scrollable_layout.itemAt(i).widget()
            if isinstance(widget, VideoEntryWidgetPyQt):
                search_text = str(widget.video_path.resolve()) if self.show_full_path_in_output else widget.video_path.name
                if keyword.lower() in search_text.lower(): found_widget = widget; self.last_keyword_search_index = i; break
        if not found_widget and start_search_layout_index > 0:
            logger.debug(f"Keyword '{keyword}' not found from {start_search_layout_index}. Wrapping.")
            self.last_keyword_search_index = -1
            for i in range(start_search_layout_index):
                widget = self.output_scrollable_layout.itemAt(i).widget()
                if isinstance(widget, VideoEntryWidgetPyQt):
                    search_text = str(widget.video_path.resolve()) if self.show_full_path_in_output else widget.video_path.name
                    if keyword.lower() in search_text.lower(): found_widget = widget; self.last_keyword_search_index = i; break
        if found_widget:
            self.output_scroll_area.ensureWidgetVisible(found_widget, 50, 50)
            display_order_str = f"Display # {getattr(found_widget, 'display_order', 'N/A')}"
            logger.info(f"Found '{keyword}' in ({display_order_str}, {found_widget.video_path.name}) at layout index {self.last_keyword_search_index}")
            self.update_completion_label_slot(f"Found '{keyword}' in: {display_order_str}")
            original_style = found_widget.styleSheet()
            found_widget.setStyleSheet(original_style + "QFrame { border: 2px solid deepskyblue; }")
            QTimer.singleShot(1000, lambda w=found_widget, s=original_style: w.setStyleSheet(s) if w else None)
        else:
            logger.info(f"Keyword '{keyword}' not found."); self.update_completion_label_slot(f"'{keyword}' not found.")
            self.last_keyword_search_index = -1

    def _update_all_video_entry_display_orders(self):
        # ... (method remains the same) ...
        if not self.output_scrollable_layout: return
        from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
        current_display_num = 1; temp_max_display_order = 0
        for i in range(self.output_scrollable_layout.count()):
            widget = self.output_scrollable_layout.itemAt(i).widget()
            if isinstance(widget, VideoEntryWidgetPyQt):
                widget.set_display_order(current_display_num)
                temp_max_display_order = max(temp_max_display_order, current_display_num); current_display_num += 1
        self.max_display_order_ever_assigned = temp_max_display_order
        self.update_selection_count()

    def sort_output_videos(self, sort_key: str, ascending: bool, new_item_added: bool = False):
        # ... (method remains the same) ...
        if self.is_processing and sort_key != "Original Order":
            logger.info(f"Sorting by '{sort_key}' deferred: processing ongoing.")
            self.current_sort_key, self.current_sort_ascending = sort_key, ascending; return
        logger.info(f"Sorting by: {sort_key}, Asc: {ascending}")
        self.current_sort_key, self.current_sort_ascending = sort_key, ascending
        self.last_keyword_search_index = -1
        if not self.output_scrollable_layout: return
        widgets_to_sort = [self.output_scrollable_layout.itemAt(i).widget() for i in range(self.output_scrollable_layout.count()) if self.output_scrollable_layout.itemAt(i).widget()]
        for widget in widgets_to_sort: self.output_scrollable_layout.removeWidget(widget)
        from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
        def get_sort_val(w: VideoEntryWidgetPyQt, k: str):
            if k == "Name": return str(w.video_path.resolve()).lower() if self.show_full_path_in_output else w.video_path.name.lower()
            elif k == "Size": return w.file_size if hasattr(w, 'file_size') else 0
            elif k == "Duration": return w.duration if hasattr(w, 'duration') else 0
            elif k == "Date Modified": return w.date_modified if hasattr(w, 'date_modified') else 0
            return w.processing_order if hasattr(w, 'processing_order') else float('inf')
        try: widgets_to_sort.sort(key=lambda w: get_sort_val(w, sort_key), reverse=not ascending)
        except Exception as e:
            logger.error(f"Sorting error: {e}", exc_info=True)
            for wf in widgets_to_sort: self.output_scrollable_layout.addWidget(wf)
        self.max_display_order_ever_assigned = 0
        for i, widget in enumerate(widgets_to_sort):
            self.output_scrollable_layout.addWidget(widget)
            if isinstance(widget, VideoEntryWidgetPyQt):
                new_display_order = i + 1; widget.set_display_order(new_display_order)
                self.max_display_order_ever_assigned = max(self.max_display_order_ever_assigned, new_display_order)
        if self.output_scrollable_widget: self.output_scrollable_widget.adjustSize()
        self.update_selection_count(); logger.debug("Sorting complete.")
        if new_item_added and widgets_to_sort and not self.is_processing and sort_key == "Original Order":
            target_proc_order = self.video_widget_processing_order_counter
            for ws in widgets_to_sort:
                if isinstance(ws, VideoEntryWidgetPyQt) and hasattr(ws, 'processing_order') and ws.processing_order == target_proc_order:
                    if hasattr(ws, 'display_order'): self.jump_to_video_in_output_by_display_order(ws.display_order); break

    def toggle_video_path_display_mode(self, state_int: int):
        # ... (method remains the same) ...
        self.show_full_path_in_output = (state_int == Qt.CheckState.Checked.value)
        logger.debug(f"Toggle path display. Full path: {self.show_full_path_in_output}")
        if not self.output_scrollable_layout: return
        from src.gui.output_tab_modules.thumbnails import VideoEntryWidgetPyQt
        for i in range(self.output_scrollable_layout.count()):
            widget = self.output_scrollable_layout.itemAt(i).widget()
            if isinstance(widget, VideoEntryWidgetPyQt): widget.update_video_label_text()
        if self.current_sort_key == "Name" and not self.is_processing:
            self.sort_output_videos(self.current_sort_key, self.current_sort_ascending)
        if self.output_scrollable_widget: self.output_scrollable_widget.adjustSize()

    def update_scroll_speed(self, speed_multiplier: int):
        # ... (method remains the same) ...
        if hasattr(self, 'output_scroll_area') and self.output_scroll_area and hasattr(self.output_scroll_area, 'set_scroll_speed_multiplier'):
            self.output_scroll_area.set_scroll_speed_multiplier(speed_multiplier)
            logger.debug(f"Scroll speed multiplier: {speed_multiplier}x")