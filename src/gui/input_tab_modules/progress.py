import tkinter as tk
from tkinter import ttk
import time
import threading
from loguru import logger
from src.distribution_enum import Distribution
from .tooltip import Tooltip
import json
from pathlib import Path

def setup_progress_controls(gui, input_frame):
    """Setup progress bar, ETA, completion label, and start button."""
    bottom_frame = ttk.Frame(input_frame)
    bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='ew')

    gui.progress_var = tk.DoubleVar()
    gui.progress_bar = ttk.Progressbar(bottom_frame, variable=gui.progress_var, maximum=100)
    gui.progress_bar.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
    Tooltip(gui.progress_bar, "Progress bar showing the thumbnail generation status.")

    gui.eta_label = ttk.Label(bottom_frame, text="ETA: --:--")
    gui.eta_label.grid(row=1, column=0, padx=5, pady=5)
    Tooltip(gui.eta_label, "Estimated time remaining for processing.")

    gui.completion_label = ttk.Label(bottom_frame, text="")
    gui.completion_label.grid(row=2, column=0, padx=5, pady=5)
    Tooltip(gui.completion_label, "Message displayed when processing is complete.")

    start_button = ttk.Button(bottom_frame, text="Start", command=lambda: start_processing(gui))
    start_button.grid(row=3, column=0, pady=10)
    Tooltip(start_button, "Begin processing videos with the current settings.")

    bottom_frame.columnconfigure(0, weight=1)

def start_processing(gui):
    """Start the video processing thread with current settings."""
    from src.gui.thumbnail_gui import VideoThumbnailGUI
    folder = gui.folder_var.get()
    thumbs = gui.thumbs_var.get()
    thumbs_per_column = gui.thumbs_per_column_var.get()
    width = gui.width_var.get()
    quality = gui.quality_var.get()
    concurrent = gui.concurrent_var.get()
    zoom = gui.zoom_var.get()
    min_size = gui.min_size_var.get()
    min_size_unit = gui.min_size_unit_var.get()
    min_duration = gui.min_duration_var.get()
    min_duration_unit = gui.min_duration_unit_var.get()
    use_peak_concentration = gui.use_peak_concentration_var.get()
    peak_pos = gui.peak_pos_var.get()
    concentration = gui.concentration_var.get()
    distribution = Distribution.UNIFORM if not use_peak_concentration else Distribution(gui.distribution_var.get())

    if quality < 1:
        quality = 1
    elif quality > 31:
        quality = 31

    size_conversion = {'KB': 1/1024, 'MB': 1, 'GB': 1024, 'TB': 1024*1024}
    min_size_mb = min_size * size_conversion[min_size_unit]

    duration_conversion = {'seconds': 1, 'minutes': 60, 'hours': 3600}
    min_duration_seconds = min_duration * duration_conversion[min_duration_unit]

    gui.config.set('default_folder', folder)
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

    # Save config and print to console
    gui.config.save()
    config_file = Path('config.json')
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_content = json.load(f)
        print("Configuration saved to config.json:")
        print(json.dumps(config_content, indent=4))

    gui.processor = gui.processor.__class__(
        gui.config.get('cache_dir'),
        thumbs, width, quality, concurrent,
        min_size_mb, min_duration_seconds,
        gui.update_output_tab,
        peak_pos=peak_pos,
        concentration=concentration,
        distribution=distribution
    )

    for widget in gui.output_scrollable_frame.winfo_children():
        widget.destroy()
    gui.videos.clear()
    gui.photo_references.clear()

    gui.total_videos = 0
    gui.processed_thumbnails = 0
    gui.total_thumbnails = 0
    gui.progress_var.set(0)
    gui.eta_label.config(text="ETA: --:--")
    gui.completion_label.config(text="")
    gui.start_time = None
    gui.video_counter = 0
    gui.update_selection_count()

    threading.Thread(target=lambda: process_videos(gui), daemon=True).start()

def process_videos(gui):
    """Process all videos in the selected folder."""
    videos = gui.processor.scan_videos(gui.folder_var.get())
    gui.total_videos = len(videos)
    gui.total_thumbnails = gui.total_videos * gui.processor.thumbnails_per_video
    logger.debug(f"Total videos to process: {gui.total_videos}, Total thumbnails to generate: {gui.total_thumbnails}")
    if gui.total_videos == 0:
        logger.warning("No videos found to process")
        on_processing_complete(gui)
        return
    gui.start_time = time.time()

    gui.processor.process_videos(
        videos,
        progress_callback=lambda progress: update_progress(gui, progress),
        error_callback=gui.report_error,
        command_callback=lambda cmd, thumb, vid: update_command(gui, cmd, thumb, vid),
        completion_callback=lambda: on_processing_complete(gui)
    )

def update_progress(gui, progress):
    """Update the progress bar and ETA during thumbnail generation."""
    thumbnails_for_video = gui.processor.thumbnails_per_video
    thumbnails_processed_for_video = int((progress / 100) * thumbnails_for_video)
    gui.processed_thumbnails += 1
    logger.debug(f"Processed thumbnails: {gui.processed_thumbnails}/{gui.total_thumbnails}")

    from src.gui.process_tab import update_process_text
    update_process_text(gui, f"Thumbnail Progress: {progress:.2f}% (Thumbnail {thumbnails_processed_for_video}/{thumbnails_for_video})\n")

    if gui.total_thumbnails > 0:
        overall_progress = (gui.processed_thumbnails / gui.total_thumbnails) * 100
        gui.progress_var.set(overall_progress)

        elapsed_time = time.time() - gui.start_time
        if gui.processed_thumbnails > 0:
            thumbnails_per_second = gui.processed_thumbnails / elapsed_time
            remaining_thumbnails = max(0, gui.total_thumbnails - gui.processed_thumbnails)
            eta_seconds = remaining_thumbnails / thumbnails_per_second if thumbnails_per_second > 0 else 0
            eta_minutes = int(eta_seconds // 60)
            eta_secs = int(eta_seconds % 60)
            gui.eta_label.config(text=f"ETA: {eta_minutes:02d}:{eta_secs:02d}")
        else:
            gui.eta_label.config(text="ETA: --:--")

def update_command(gui, command, thumbnail_path, video_path):
    """Update the process tab with FFmpeg commands and preview thumbnails."""
    from src.gui.process_tab import update_process_text, update_thumbnail_preview
    quoted_command = command.replace(str(video_path), f'"{video_path}"').replace(str(thumbnail_path), f'"{thumbnail_path}"')
    update_process_text(gui, f"Executing: {quoted_command}\n")
    update_thumbnail_preview(gui, thumbnail_path)

def on_processing_complete(gui):
    """Display completion message when all videos are processed."""
    gui.completion_label.config(text="Processing Complete!")
    gui.progress_var.set(100)
    gui.eta_label.config(text="ETA: 00:00")
    logger.debug("Processing complete, ensuring UI update")
    gui.output_scrollable_frame.update_idletasks()
    gui.output_canvas.configure(scrollregion=gui.output_canvas.bbox("all"))
    gui.update_selection_count()