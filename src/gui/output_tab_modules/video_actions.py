import tkinter as tk
import subprocess
from pathlib import Path
from loguru import logger
from .selection import select_video, toggle_selection

def on_mouse_wheel(gui, event):
    """Handle mouse wheel scrolling for the output canvas."""
    if not event.state & 0x0001:  # Check if Ctrl key is not pressed
        gui.output_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    else:
        gui.output_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

def play_video(gui, video):
    """Play the selected video using the default system video player."""
    try:
        video_path = str(video)
        logger.debug(f"Attempting to play video: {video_path}")
        if Path(video_path).exists():
            subprocess.run(['start', '', video_path], shell=True, check=True)
        else:
            logger.error(f"Video file does not exist: {video_path}")
            gui.report_error(video, "Video file does not exist")
    except Exception as e:
        logger.error(f"Failed to play video {video}: {e}")
        gui.report_error(video, str(e))

def show_context_menu(gui, event, video):
    """Show a context menu for the video with various actions."""
    menu = tk.Menu(gui.root, tearoff=0)
    var = tk.BooleanVar(value=video in gui.selected_videos)
    menu.add_command(label="Play Video", command=lambda: play_video(gui, video))
    menu.add_command(label="Select/Deselect", command=lambda: select_video(gui, video, var))
    menu.add_command(label="Copy Filename", command=lambda: copy_filename(gui, video))
    menu.add_command(label="Copy Filepath", command=lambda: copy_filepath(gui, video))
    menu.add_command(label="Open in Explorer", command=lambda: open_in_explorer(video))
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

def open_in_explorer(video):
    """Open the video's parent directory in Windows Explorer."""
    try:
        video_path = Path(video)
        if video_path.exists():
            subprocess.run(['explorer', '/select,', str(video_path)], shell=True, check=True)
            logger.debug(f"Opened Explorer for: {video_path}")
        else:
            logger.error(f"Video file does not exist: {video_path}")
    except subprocess.CalledProcessError as e:
        pass
    except Exception as e:
        logger.error(f"Failed to open Explorer for {video}: {e}, {type(e)=}")

def copy_filename(gui, video):
    """Copy the video filename to the clipboard."""
    filename = Path(video).name
    gui.root.clipboard_clear()
    gui.root.clipboard_append(filename)
    gui.root.update()
    logger.debug(f"Copied filename to clipboard: {filename}")
    gui.completion_label.config(text="Filename copied to clipboard!")

def copy_filepath(gui, video):
    """Copy the full video filepath to the clipboard."""
    filepath = str(video)
    gui.root.clipboard_clear()
    gui.root.clipboard_append(filepath)
    gui.root.update()
    logger.debug(f"Copied filepath to clipboard: {filepath}")
    gui.completion_label.config(text="Filepath copied to clipboard!")