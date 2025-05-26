from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QPushButton
from PyQt6.QtCore import Qt, QThread
from loguru import logger
import json
from pathlib import Path
from src.distribution_enum import Distribution
import time
from src.gui.worker import VideoProcessingWorker

def setup_progress_controls_pyqt(gui, parent_layout):
    bottom_frame_widget = QWidget()
    bottom_layout = QVBoxLayout(bottom_frame_widget)

    gui.progress_bar = QProgressBar()
    gui.progress_bar.setRange(0, 100)
    gui.progress_bar.setValue(0)
    gui.progress_bar.setToolTip("Progress bar showing the thumbnail generation status.")
    bottom_layout.addWidget(gui.progress_bar)

    gui.eta_label = QLabel("ETA: --:--")
    gui.eta_label.setToolTip("Estimated time remaining for processing.")
    bottom_layout.addWidget(gui.eta_label)

    gui.completion_label = QLabel("")
    gui.completion_label.setToolTip("Message display area.")
    bottom_layout.addWidget(gui.completion_label)

    start_button = QPushButton("Start")
    start_button.setToolTip("Begin processing videos with the current settings.")
    start_button.clicked.connect(gui.start_processing_wrapper)
    bottom_layout.addWidget(start_button, 0, Qt.AlignmentFlag.AlignCenter)

    parent_layout.addWidget(bottom_frame_widget)


def start_processing_pyqt(gui):
    logger.info("start_processing_pyqt called.")
    required_attrs = ['folder_var', 'cache_folder_var', # Added cache_folder_var
                      'thumbs_var', 'thumbs_per_column_var', 'width_var', 'quality_var',
                      'concurrent_var', 'zoom_var', 'min_size_var', 'min_size_unit_var',
                      'min_duration_var', 'min_duration_unit_var', 'use_peak_concentration_var',
                      'peak_pos_var', 'concentration_var', 'distribution_var', 'completion_label',
                      'output_scrollable_layout', 'progress_bar', 'eta_label']
    for attr in required_attrs:
        if not hasattr(gui, attr) or getattr(gui, attr) is None:
            logger.error(f"GUI element '{attr}' for processing not initialized.")
            if hasattr(gui, 'completion_label') and gui.completion_label:
                gui.completion_label.setText(f"Error: GUI element '{attr}' not ready.")
            return

    folder = gui.folder_var.text()
    cache_dir = gui.cache_folder_var.text() # Get cache_dir from GUI
    thumbs = gui.thumbs_var.value()
    thumbs_per_column = gui.thumbs_per_column_var.value()
    width = gui.width_var.value()
    quality = gui.quality_var.value()
    concurrent = gui.concurrent_var.value()
    zoom = gui.zoom_var.value()
    min_size_mb = gui.get_min_size_mb()
    min_duration_seconds = gui.get_min_duration_seconds()
    use_peak_concentration = gui.use_peak_concentration_var.isChecked()
    peak_pos = gui.peak_pos_var.value()
    concentration = gui.concentration_var.value()
    distribution_text = gui.distribution_var.currentText()

    try:
        distribution = Distribution.UNIFORM if not use_peak_concentration else Distribution(distribution_text)
    except ValueError:
        logger.warning(f"Invalid distribution string '{distribution_text}', defaulting to UNIFORM.")
        distribution = Distribution.UNIFORM

    if quality < 1: quality = 1
    elif quality > 31: quality = 31

    gui.config.set('default_folder', folder)
    gui.config.set('cache_dir', cache_dir) # Save cache_dir to config
    gui.config.set('thumbnails_per_video', thumbs)
    gui.config.set('thumbnails_per_column', thumbs_per_column)
    gui.config.set('thumbnail_width', width)
    gui.config.set('thumbnail_quality', quality)
    gui.config.set('concurrent_videos', concurrent)
    gui.config.set('zoom_factor', zoom)
    gui.config.set('min_size_mb', min_size_mb)
    gui.config.set('min_duration_seconds', min_duration_seconds)
    gui.config.set('use_peak_concentration', use_peak_concentration)
    gui.config.set('thumbnail_peak_pos', peak_pos)
    gui.config.set('thumbnail_concentration', concentration)
    gui.config.set('thumbnail_distribution', distribution)
    gui.config.save()

    config_file = Path('config.json')
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_content = json.load(f)
        logger.info(f"Configuration saved to config.json: {json.dumps(config_content, indent=4)}")

    gui.reinit_processor() # This will now use the updated cache_dir from config

    if not gui.processor:
        logger.error("Cannot start processing: VideoProcessor failed to initialize.")
        gui.completion_label.setText("Error: VideoProcessor initialization failed.")
        return

    if gui.output_scrollable_layout:
        while gui.output_scrollable_layout.count():
            child = gui.output_scrollable_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    gui.videos.clear()
    gui.selected_videos.clear()

    if gui.worker_thread and gui.worker_thread.isRunning():
        logger.warning("Processing is already in progress. Please wait.")
        gui.completion_label.setText("Processing already in progress. Please wait.")
        return

    try:
        logger.info(f"Scanning videos in folder: {gui.folder_var.text()}")
        gui.folder_to_scan_for_worker = gui.folder_var.text()

        gui.total_videos = 0
        gui.total_thumbnails = 0
        gui.completion_label.setText("Scanning videos...")
        logger.info("Video scan will be performed by the worker thread.")

    except Exception as e:
        logger.error(f"Error preparing for video scanning: {e}", exc_info=True)
        gui.completion_label.setText(f"Error preparing scan: {e}")
        gui.setWindowTitle(gui.base_window_title)
        output_tab_idx = gui.get_tab_index_by_text_prefix("Output") # Changed to prefix match
        if output_tab_idx != -1 and hasattr(gui.notebook, 'setTabText'):
            gui.notebook.setTabText(output_tab_idx, "Output")
        return

    gui.processed_thumbnails_count = 0
    if gui.progress_bar: gui.progress_bar.setValue(0)
    if gui.eta_label: gui.eta_label.setText("ETA: --:--")
    gui.start_time = time.time()
    gui.video_counter = 0
    gui.update_selection_count()

    gui.worker_thread = QThread()
    gui.processing_worker = VideoProcessingWorker(gui)
    gui.processing_worker.moveToThread(gui.worker_thread)

    if hasattr(gui, 'connect_worker_signals') and callable(gui.connect_worker_signals):
        gui.connect_worker_signals(gui.processing_worker)
    else:
        logger.error("gui object does not have connect_worker_signals method!")
        try:
            gui.processing_worker.signals.progress.connect(gui.update_progress_bar_slot)
            gui.processing_worker.signals.thumbnail_progress.connect(gui.update_process_tab_thumbnail_progress_slot)
            gui.processing_worker.signals.eta_update.connect(gui.update_eta_label_slot)
            gui.processing_worker.signals.completion_message.connect(gui.update_completion_label_slot)
            gui.processing_worker.signals.error.connect(gui.report_error_slot_detailed)
            gui.processing_worker.signals.command.connect(gui.update_command_slot)
            gui.processing_worker.signals.processing_complete.connect(gui.on_processing_complete_slot)
            logger.info("Fallback: Connected worker signals directly in progress.py.")
        except Exception as e_connect:
            logger.error(f"Fallback connection failed: {e_connect}")
            gui.completion_label.setText("Error: Failed to set up processing signals.")
            return


    gui.worker_thread.started.connect(gui.processing_worker.process_videos_thread)

    logger.info("Starting worker thread for video processing (including scan).")
    gui.worker_thread.start()