from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QCursor
from PyQt6.QtWidgets import QApplication, QMenu
from pathlib import Path
import subprocess
from loguru import logger

def on_mouse_wheel_pyqt(gui, event):
    """Handle mouse wheel scrolling for the output QScrollArea (PyQt6)."""
    # Standard QScrollArea handles vertical scroll.
    # For Ctrl+Wheel for horizontal scroll:
    scroll_area = gui.output_scroll_area
    if not scroll_area:
        return

    if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
        delta = event.angleDelta().y()  # Typically y for wheel, but might be x for some mice
        if delta == 0: delta = event.angleDelta().x() # If y is 0, try x (for horizontal scroll wheels)

        current_val = scroll_area.horizontalScrollBar().value()
        # Adjust sensitivity; angleDelta is usually +/- 120
        scroll_amount = -delta // 15 # Negative to match typical scroll direction
        scroll_area.horizontalScrollBar().setValue(current_val + scroll_amount)
        event.accept()
    else:
        # Let QScrollArea handle vertical scroll by not accepting the event here
        # or by explicitly calling its default handler if overridden.
        # If this function is an event filter, then returning False passes it on.
        # If it's a direct override of wheelEvent, call super().wheelEvent(event).
        event.ignore() # Allow parent/default handling

def play_video_pyqt(gui, video_path: Path):
    """Play the selected video using the default system video player (PyQt6)."""
    try:
        video_url = QUrl.fromLocalFile(str(video_path.resolve()))
        if video_path.exists():
            if not QDesktopServices.openUrl(video_url):
                logger.error(f"QDesktopServices could not open video: {video_path}")
                # Fallback to subprocess for platforms where QDesktopServices might fail for local files
                try:
                    if sys.platform == "win32":
                        os.startfile(str(video_path.resolve()))
                    elif sys.platform == "darwin":
                        subprocess.run(['open', str(video_path.resolve())], check=True)
                    else: # linux variants
                        subprocess.run(['xdg-open', str(video_path.resolve())], check=True)
                except Exception as e_sub:
                    logger.error(f"Fallback subprocess failed to play video {video_path}: {e_sub}")
                    gui.report_error_slot(str(video_path), f"Could not play video (QDesktopServices and subprocess failed). Error: {e_sub}")

        else:
            logger.error(f"Video file does not exist: {video_path}")
            gui.report_error_slot(str(video_path), "Video file does not exist")
    except Exception as e:
        logger.error(f"Failed to play video {video_path}: {e}")
        gui.report_error_slot(str(video_path), str(e))


# Context menu creation is now part of VideoEntryWidgetPyQt
# These are helper functions for menu actions:

def open_in_explorer_pyqt(video_path: Path):
    """Open the video's parent directory in the system's file explorer."""
    try:
        if not video_path.exists():
            logger.error(f"Cannot open in explorer, file does not exist: {video_path}")
            # Optionally show a message to user via gui signal if gui ref was passed
            return

        # QDesktopServices.openUrl(QUrl.fromLocalFile(str(video_path.parent))) # Opens directory
        # For selecting the file:
        if sys.platform == "win32":
            subprocess.run(['explorer', '/select,', str(video_path.resolve())], shell=False, check=True)
        elif sys.platform == "darwin": # macOS
            subprocess.run(['open', '-R', str(video_path.resolve())], check=True)
        else: # Linux
            # Fallback to just opening the directory as 'select' isn't standard for xdg-open
            # Some file managers might support it with specific URIs (e.g. KIO for Dolphin)
            # but QDesktopServices.openUrl is more general for just opening the dir.
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(video_path.parent)))
            # Alternatively, try to use a common file manager if known
            # subprocess.run(['xdg-open', str(video_path.parent)], check=True)

        logger.debug(f"Opened/selected in Explorer: {video_path}")

    except Exception as e:
        logger.warning(f"Failed to open Explorer for {video_path}: {e}")
        # Optionally show error to user

import sys, os # for play_video_pyqt and open_in_explorer_pyqt platform checks

def copy_filename_pyqt(gui, video_path: Path):
    filename = video_path.name
    QApplication.clipboard().setText(filename)
    logger.debug(f"Copied filename to clipboard: {filename}")
    gui.update_completion_label_slot("Filename copied to clipboard!")

def copy_filepath_pyqt(gui, video_path: Path):
    filepath = str(video_path.resolve())
    QApplication.clipboard().setText(filepath)
    logger.debug(f"Copied filepath to clipboard: {filepath}")
    gui.update_completion_label_slot("Filepath copied to clipboard!")