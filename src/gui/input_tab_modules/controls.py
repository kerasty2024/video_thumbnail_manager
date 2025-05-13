import tkinter as tk
from tkinter import ttk
from .tooltip import Tooltip

def setup_input_controls(gui, left_frame, right_frame):
    """Setup input controls for the Input tab."""
    row_left = row_right = 0

    # Folder (Left column)
    folder_label = ttk.Label(left_frame, text="Folder:")
    folder_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(folder_label, "The directory containing the video files to process.")
    folder_entry = ttk.Entry(left_frame, textvariable=gui.folder_var, width=30)
    folder_entry.grid(row=row_left, column=1, padx=5, pady=5)
    Tooltip(folder_entry, "Enter or browse to the folder with video files.")
    ttk.Button(left_frame, text="Browse", command=gui.browse_folder).grid(row=row_left, column=2, padx=5, pady=5)
    Tooltip(left_frame.winfo_children()[-1], "Open a dialog to select the video folder.")
    row_left += 1

    # Thumbnails per Video (Left column)
    thumbs_label = ttk.Label(left_frame, text="Thumbnails per Video:")
    thumbs_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(thumbs_label, "Number of thumbnails to generate per video (default: 8).")
    gui.thumbs_var = tk.IntVar(value=gui.config.get('thumbnails_per_video'))
    thumbs_entry = ttk.Entry(left_frame, textvariable=gui.thumbs_var, width=10)
    thumbs_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(thumbs_entry, "Set the number of thumbnails to extract from each video.")
    row_left += 1

    # Thumbnails per Column (Left column)
    thumbs_per_column_label = ttk.Label(left_frame, text="Thumbnails per Column:")
    thumbs_per_column_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(thumbs_per_column_label, "Number of thumbnails displayed per column in the output (default: 2).")
    gui.thumbs_per_column_var = tk.IntVar(value=gui.config.get('thumbnails_per_column'))
    thumbs_per_column_entry = ttk.Entry(left_frame, textvariable=gui.thumbs_per_column_var, width=10)
    thumbs_per_column_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(thumbs_per_column_entry, "Set the number of thumbnails per column in the output layout.")
    row_left += 1

    # Thumbnail Width (Left column)
    width_label = ttk.Label(left_frame, text="Thumbnail Width:")
    width_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(width_label, "Width of each thumbnail in pixels (default: 320).")
    gui.width_var = tk.IntVar(value=gui.config.get('thumbnail_width'))
    width_entry = ttk.Entry(left_frame, textvariable=gui.width_var, width=10)
    width_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(width_entry, "Set the width of the generated thumbnails.")
    row_left += 1

    # Thumbnail Quality (Left column)
    quality_label = ttk.Label(left_frame, text="Thumbnail Quality (1-31):")
    quality_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(quality_label, "FFmpeg quality setting for thumbnails (1 = best, 31 = worst, default: 4).")
    gui.quality_var = tk.IntVar(value=gui.config.get('thumbnail_quality'))
    quality_entry = ttk.Entry(left_frame, textvariable=gui.quality_var, width=10)
    quality_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(quality_entry, "Set the FFmpeg quality parameter for thumbnails (1-31).")
    row_left += 1

    # Min Duration (Left column)
    min_duration_label = ttk.Label(left_frame, text="Min Duration:")
    min_duration_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(min_duration_label, "Minimum video duration to process (default: 0.0 seconds).")
    gui.min_duration_var = tk.DoubleVar(value=gui.config.get('min_duration_seconds'))
    min_duration_entry = ttk.Entry(left_frame, textvariable=gui.min_duration_var, width=10)
    min_duration_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(min_duration_entry, "Set the minimum video duration to include.")
    gui.min_duration_unit_var = tk.StringVar(value='seconds')
    min_duration_unit_menu = ttk.OptionMenu(left_frame, gui.min_duration_unit_var, 'seconds', 'seconds', 'minutes', 'hours')
    min_duration_unit_menu.grid(row=row_left, column=2, padx=5, pady=5)
    Tooltip(min_duration_unit_menu, "Select the unit for the minimum video duration.")
    row_left += 1

    # Min Video Size (Left column)
    min_size_label = ttk.Label(left_frame, text="Min Video Size:")
    min_size_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(min_size_label, "Minimum video file size to process (default: 0.0 MB).")
    gui.min_size_var = tk.DoubleVar(value=gui.config.get('min_size_mb'))
    min_size_entry = ttk.Entry(left_frame, textvariable=gui.min_size_var, width=10)
    min_size_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(min_size_entry, "Set the minimum video size to include (in MB).")
    gui.min_size_unit_var = tk.StringVar(value='MB')
    min_size_unit_menu = ttk.OptionMenu(left_frame, gui.min_size_unit_var, 'MB', 'KB', 'MB', 'GB', 'TB')
    min_size_unit_menu.grid(row=row_left, column=2, padx=5, pady=5)
    Tooltip(min_size_unit_menu, "Select the unit for the minimum video size.")
    row_left += 1

    # Concurrent Videos (Left column)
    concurrent_label = ttk.Label(left_frame, text="Concurrent Videos:")
    concurrent_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(concurrent_label, "Number of videos to process simultaneously (default: 4).")
    gui.concurrent_var = tk.IntVar(value=gui.config.get('concurrent_videos'))
    concurrent_entry = ttk.Entry(left_frame, textvariable=gui.concurrent_var, width=10)
    concurrent_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(concurrent_entry, "Set the number of videos processed concurrently.")
    row_left += 1

    # Zoom Factor (Left column)
    zoom_label = ttk.Label(left_frame, text="Zoom Factor:")
    zoom_label.grid(row=row_left, column=0, padx=5, pady=5, sticky='w')
    Tooltip(zoom_label, "Zoom level when hovering over thumbnails with Ctrl (default: 2.0).")
    gui.zoom_var = tk.DoubleVar(value=gui.config.get('zoom_factor'))
    zoom_entry = ttk.Entry(left_frame, textvariable=gui.zoom_var, width=10)
    zoom_entry.grid(row=row_left, column=1, padx=5, pady=5, sticky='w')
    Tooltip(zoom_entry, "Set the zoom factor for thumbnail hover previews.")
    row_left += 1

    return row_left, row_right