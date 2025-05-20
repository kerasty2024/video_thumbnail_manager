from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QHBoxLayout, QWidget
from PyQt6.QtGui import QIntValidator, QDoubleValidator

def setup_input_controls_pyqt(gui, left_layout, right_layout):
    """Setup input controls for the Input tab using PyQt6."""

    # Folder (Left column)
    folder_group = QWidget()
    folder_layout = QHBoxLayout(folder_group)
    folder_label = QLabel("Folder:")
    folder_label.setToolTip("The directory containing the video files to process.")
    folder_layout.addWidget(folder_label)
    gui.folder_var = QLineEdit(gui.config.get('default_folder'))
    gui.folder_var.setToolTip("Enter or browse to the folder with video files.")
    folder_layout.addWidget(gui.folder_var)
    browse_button = QPushButton("Browse")
    browse_button.setToolTip("Open a dialog to select the video folder.")
    browse_button.clicked.connect(gui.browse_folder)
    folder_layout.addWidget(browse_button)
    left_layout.addWidget(folder_group)

    # Thumbnails per Video (Left column)
    thumbs_group = QWidget()
    thumbs_layout = QHBoxLayout(thumbs_group)
    thumbs_label = QLabel("Thumbnails per Video:")
    thumbs_label.setToolTip("Number of thumbnails to generate per video (default: 18).")
    thumbs_layout.addWidget(thumbs_label)
    gui.thumbs_var = QSpinBox()
    gui.thumbs_var.setRange(1, 100) # Example range
    gui.thumbs_var.setValue(gui.config.get('thumbnails_per_video'))
    gui.thumbs_var.setToolTip("Set the number of thumbnails to extract from each video.")
    thumbs_layout.addWidget(gui.thumbs_var)
    thumbs_layout.addStretch(1)
    left_layout.addWidget(thumbs_group)


    # Thumbnails per Column (Left column)
    thumbs_per_col_group = QWidget()
    thumbs_per_col_layout = QHBoxLayout(thumbs_per_col_group)
    thumbs_per_column_label = QLabel("Thumbnails per Column:")
    thumbs_per_column_label.setToolTip("Number of thumbnails displayed per column in the output (default: 3).")
    thumbs_per_col_layout.addWidget(thumbs_per_column_label)
    gui.thumbs_per_column_var = QSpinBox()
    gui.thumbs_per_column_var.setRange(1, 20) # Example range
    gui.thumbs_per_column_var.setValue(gui.config.get('thumbnails_per_column'))
    gui.thumbs_per_column_var.setToolTip("Set the number of thumbnails per column in the output layout.")
    thumbs_per_col_layout.addWidget(gui.thumbs_per_column_var)
    thumbs_per_col_layout.addStretch(1)
    left_layout.addWidget(thumbs_per_col_group)

    # Thumbnail Width (Left column)
    width_group = QWidget()
    width_layout = QHBoxLayout(width_group)
    width_label = QLabel("Thumbnail Width:")
    width_label.setToolTip("Width of each thumbnail in pixels (default: 320).")
    width_layout.addWidget(width_label)
    gui.width_var = QSpinBox()
    gui.width_var.setRange(50, 1920) # Example range
    gui.width_var.setValue(gui.config.get('thumbnail_width'))
    gui.width_var.setToolTip("Set the width of the generated thumbnails.")
    width_layout.addWidget(gui.width_var)
    width_layout.addStretch(1)
    left_layout.addWidget(width_group)

    # Thumbnail Quality (Left column)
    quality_group = QWidget()
    quality_layout = QHBoxLayout(quality_group)
    quality_label = QLabel("Thumbnail Quality (1-31):")
    quality_label.setToolTip("FFmpeg quality setting for thumbnails (1 = best, 31 = worst, default: 4).")
    quality_layout.addWidget(quality_label)
    gui.quality_var = QSpinBox()
    gui.quality_var.setRange(1, 31)
    gui.quality_var.setValue(gui.config.get('thumbnail_quality'))
    gui.quality_var.setToolTip("Set the FFmpeg quality parameter for thumbnails (1-31).")
    quality_layout.addWidget(gui.quality_var)
    quality_layout.addStretch(1)
    left_layout.addWidget(quality_group)

    # Min Duration (Left column)
    min_duration_group = QWidget()
    min_duration_layout = QHBoxLayout(min_duration_group)
    min_duration_label = QLabel("Min Duration:")
    min_duration_label.setToolTip("Minimum video duration to process (default: 0.0 seconds).")
    min_duration_layout.addWidget(min_duration_label)
    gui.min_duration_var = QDoubleSpinBox()
    gui.min_duration_var.setRange(0.0, 10000.0) # Example range
    gui.min_duration_var.setValue(gui.config.get('min_duration_seconds')) # Default to seconds from config
    gui.min_duration_var.setToolTip("Set the minimum video duration to include.")
    min_duration_layout.addWidget(gui.min_duration_var)
    gui.min_duration_unit_var = QComboBox()
    gui.min_duration_unit_var.addItems(['seconds', 'minutes', 'hours'])
    # Find and set current unit based on config (if it was stored as seconds)
    # For simplicity, assume 'seconds' is the base unit. Let user choose if they want to input in min/hr
    gui.min_duration_unit_var.setToolTip("Select the unit for the minimum video duration.")
    min_duration_layout.addWidget(gui.min_duration_unit_var)
    left_layout.addWidget(min_duration_group)


    # Min Video Size (Left column)
    min_size_group = QWidget()
    min_size_layout = QHBoxLayout(min_size_group)
    min_size_label = QLabel("Min Video Size:")
    min_size_label.setToolTip("Minimum video file size to process (default: 0.0 MB).")
    min_size_layout.addWidget(min_size_label)
    gui.min_size_var = QDoubleSpinBox()
    gui.min_size_var.setRange(0.0, 100000.0) # Example range
    gui.min_size_var.setValue(gui.config.get('min_size_mb')) # Default to MB from config
    gui.min_size_var.setToolTip("Set the minimum video size to include (in MB).")
    min_size_layout.addWidget(gui.min_size_var)
    gui.min_size_unit_var = QComboBox()
    gui.min_size_unit_var.addItems(['MB', 'KB', 'GB', 'TB'])
    # Find and set current unit
    gui.min_size_unit_var.setCurrentText('MB') # Default display unit
    gui.min_size_unit_var.setToolTip("Select the unit for the minimum video size.")
    min_size_layout.addWidget(gui.min_size_unit_var)
    left_layout.addWidget(min_size_group)

    # Concurrent Videos (Left column)
    concurrent_group = QWidget()
    concurrent_layout = QHBoxLayout(concurrent_group)
    concurrent_label = QLabel("Concurrent Videos:")
    concurrent_label.setToolTip("Number of videos to process simultaneously (default: 4).")
    concurrent_layout.addWidget(concurrent_label)
    gui.concurrent_var = QSpinBox()
    gui.concurrent_var.setRange(1, 16) # Example range
    gui.concurrent_var.setValue(gui.config.get('concurrent_videos'))
    gui.concurrent_var.setToolTip("Set the number of videos processed concurrently.")
    concurrent_layout.addWidget(gui.concurrent_var)
    concurrent_layout.addStretch(1)
    left_layout.addWidget(concurrent_group)

    # Zoom Factor (Left column)
    zoom_group = QWidget()
    zoom_layout = QHBoxLayout(zoom_group)
    zoom_label = QLabel("Zoom Factor:")
    zoom_label.setToolTip("Zoom level when hovering over thumbnails with Ctrl (default: 2.0).")
    zoom_layout.addWidget(zoom_label)
    gui.zoom_var = QDoubleSpinBox()
    gui.zoom_var.setRange(1.0, 10.0) # Example range
    gui.zoom_var.setSingleStep(0.1)
    gui.zoom_var.setValue(gui.config.get('zoom_factor'))
    gui.zoom_var.setToolTip("Set the zoom factor for thumbnail hover previews.")
    zoom_layout.addWidget(gui.zoom_var)
    zoom_layout.addStretch(1)
    left_layout.addWidget(zoom_group)

    left_layout.addStretch(1) # Pushes all controls to the top of left_layout

    # Right layout will be populated by distribution controls