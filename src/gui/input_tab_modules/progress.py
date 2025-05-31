from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QPushButton
from PyQt6.QtCore import Qt, QThread
from loguru import logger
import json
from pathlib import Path
from src.distribution_enum import Distribution
import time
from src.gui.worker import VideoProcessingWorker # Assuming VideoProcessingWorker is correctly imported for type hinting or other uses if any

def setup_progress_controls_pyqt(gui, parent_layout):
    """Sets up the progress bar, ETA label, completion label, and start button."""
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
    # Connect to the wrapper in thumbnail_gui.py, which handles state and calls this function
    start_button.clicked.connect(gui.start_processing_wrapper)
    bottom_layout.addWidget(start_button, 0, Qt.AlignmentFlag.AlignCenter)

    parent_layout.addWidget(bottom_frame_widget)


def start_processing_pyqt(gui):
    """
    Prepares and initiates the video processing task in a worker thread.
    This function is called by gui.start_processing_wrapper.
    """
    logger.info("start_processing_pyqt called to initiate worker.")

    # Ensure all necessary GUI elements are initialized
    required_attrs = ['folder_var', 'cache_folder_var',
                      'thumbs_var', 'thumbs_per_column_var', 'width_var', 'quality_var',
                      'concurrent_var', 'zoom_var', 'min_size_var', 'min_size_unit_var',
                      'min_duration_var', 'min_duration_unit_var', 'use_peak_concentration_var',
                      'peak_pos_var', 'concentration_var', 'distribution_var',
                      'excluded_words_var', 'excluded_words_regex_var', 'excluded_words_match_full_path_var',
                      'completion_label', 'output_scrollable_layout', 'progress_bar', 'eta_label']
    for attr in required_attrs:
        if not hasattr(gui, attr) or getattr(gui, attr) is None:
            logger.error(f"GUI element '{attr}' for processing not initialized.")
            if hasattr(gui, 'completion_label') and gui.completion_label:
                gui.completion_label.setText(f"Error: GUI element '{attr}' not ready.")
            gui.is_processing = False # Reset flag if setup fails
            gui.set_output_controls_enabled_state(True)
            return

    # Get all settings from GUI controls
    folder = gui.folder_var.text()
    cache_dir = gui.cache_folder_var.text()
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
    excluded_words_val = gui.excluded_words_var.text()
    excluded_words_regex_val = gui.excluded_words_regex_var.isChecked()
    excluded_words_match_full_path_val = gui.excluded_words_match_full_path_var.isChecked()

    try:
        distribution = Distribution.UNIFORM if not use_peak_concentration else Distribution(distribution_text)
    except ValueError:
        logger.warning(f"Invalid distribution string '{distribution_text}', defaulting to UNIFORM.")
        distribution = Distribution.UNIFORM

    if quality < 1: quality = 1
    elif quality > 31: quality = 31

    # Save current settings to config
    gui.config.set('default_folder', folder)
    gui.config.set('cache_dir', cache_dir)
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
    gui.config.set('excluded_words', excluded_words_val)
    gui.config.set('excluded_words_regex', excluded_words_regex_val)
    gui.config.set('excluded_words_match_full_path', excluded_words_match_full_path_val)
    gui.config.save()

    config_file_path = Path('config.json')
    if config_file_path.exists():
        with open(config_file_path, 'r') as f:
            config_content = json.load(f)
        logger.info(f"Configuration saved to config.json: {json.dumps(config_content, indent=4)}")

    # Reinitialize the processor with the new/current settings
    gui.reinit_processor()
    if not gui.processor:
        logger.error("Cannot start processing: VideoProcessor failed to initialize.")
        gui.completion_label.setText("Error: VideoProcessor initialization failed.")
        gui.is_processing = False
        gui.set_output_controls_enabled_state(True)
        return

    # Clear previous output before starting a new job
    if gui.output_scrollable_layout:
        while gui.output_scrollable_layout.count():
            child = gui.output_scrollable_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    gui.videos.clear()
    gui.selected_videos.clear()
    gui.update_selection_count() # Reflect cleared state

    # Check if another worker is already running (should be handled by gui.is_processing too)
    if gui.worker_thread and gui.worker_thread.isRunning():
        logger.warning("Processing is already in progress. Please wait.")
        gui.completion_label.setText("Processing already in progress. Please wait.")
        # gui.is_processing should already be true. Controls should already be disabled.
        return

    # Set the folder for the worker to scan
    gui.folder_to_scan_for_worker = folder
    # Reset progress-related counters in GUI (worker will send actuals via scan_complete)
    gui.processed_thumbnails_count = 0
    if gui.progress_bar: gui.progress_bar.setValue(0)
    if gui.eta_label: gui.eta_label.setText("ETA: --:--")
    gui.start_time = None # ETA calculation will start after scan_complete provides total_thumbnails

    # Setup worker thread and move worker object to it
    gui.worker_thread = QThread()
    gui.processing_worker = VideoProcessingWorker(gui) # Pass GUI reference
    gui.processing_worker.moveToThread(gui.worker_thread)

    # Connect signals from worker to GUI slots
    if hasattr(gui, 'connect_worker_signals') and callable(gui.connect_worker_signals):
        gui.connect_worker_signals(gui.processing_worker)
    else:
        # Fallback or direct connections if `connect_worker_signals` is missing (should not happen)
        logger.error("VideoThumbnailGUI object does not have connect_worker_signals method! Critical setup error.")
        gui.completion_label.setText("Error: Failed to set up processing signals.")
        gui.is_processing = False
        gui.set_output_controls_enabled_state(True)
        return

    # Connect thread's started signal to worker's main processing method
    gui.worker_thread.started.connect(gui.processing_worker.process_videos_thread)

    # The worker will emit processing_complete when done or on error,
    # which will call gui.on_processing_complete_slot to clean up the thread.

    logger.info("Starting worker thread for video scanning and processing.")
    gui.worker_thread.start()
    # GUI is now in `is_processing = True` state, controls disabled via `set_output_controls_enabled_state(False)`.
    # Worker will perform scan, emit `scan_complete`, then process videos, emitting various progress signals.