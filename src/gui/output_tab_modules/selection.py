# src/gui/output_tab_modules/selection.py
import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from loguru import logger
# from .thumbnails import VideoEntryWidgetPyQt # <--- VideoEntryWidgetPyQt の直接インポートは避ける
# 型ヒントのためには import typing と if typing.TYPE_CHECKING: を使う

import typing
if typing.TYPE_CHECKING:
    from .thumbnails import VideoEntryWidgetPyQt


# def toggle_selection_pyqt(gui, video_path: Path, is_selected: bool, video_entry_widget: 'VideoEntryWidgetPyQt'):
#     """
#     This function's core logic is now moved into VideoEntryWidgetPyQt.on_selection_changed
#     or handled by the checkbox state change directly.
#     If it's needed as a utility by other parts of the GUI, it would need to find the widget.
#     For now, assuming direct checkbox interaction is primary.
#     """
#     logger.debug(f"Toggle selection (utility) for {video_path}: new state={is_selected}")
#     if is_selected:
#         gui.selected_videos.add(video_path)
#     else:
#         gui.selected_videos.discard(video_path)

#     # Find the widget and update its appearance
#     # This is complex if not called from the widget itself.
#     # For now, this function is considered deprecated in favor of widget's own handling.
#     # video_entry_widget.update_selection_appearance(is_selected)
#     gui.update_selection_count()

def select_video_pyqt(gui, video_path: Path, video_entry_widget: 'VideoEntryWidgetPyQt'):
    """Toggle video selection, typically by manipulating its checkbox state."""
    # This might be called from a context menu, for example.
    # It should toggle the checkbox, which in turn handles the selection logic.
    if video_entry_widget:
        current_state = video_entry_widget.checkbox.isChecked()
        video_entry_widget.checkbox.setChecked(not current_state)
    else:
        logger.warning(f"select_video_pyqt called for {video_path} but no widget provided or found.")


def delete_selected_pyqt(gui):
    if not gui.selected_videos:
        QMessageBox.information(gui, "Info", "No videos selected for deletion.")
        return

    reply = QMessageBox.question(gui, "Confirm Deletion",
                                 f"Are you sure you want to delete {len(gui.selected_videos)} selected video(s) and their caches?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    if reply == QMessageBox.StandardButton.No:
        return

    videos_to_remove_ui = []
    for video_path in list(gui.selected_videos):
        try:
            if video_path.exists():
                os.remove(video_path)
                logger.info(f"Deleted video file: {video_path}")

            cache_dir = video_path.parent / "cache" / video_path.name
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logger.info(f"Deleted cache directory: {cache_dir}")

            if video_path in gui.videos:
                del gui.videos[video_path]

            videos_to_remove_ui.append(video_path)

        except Exception as e:
            # gui.report_error_slot(str(video_path), f"Failed to delete: {e}") # gui doesn't have report_error_slot directly here
            QMessageBox.critical(gui, "Deletion Error", f"Failed to delete {video_path}: {e}")
            logger.error(f"Error deleting {video_path}: {e}")

    from .thumbnails import VideoEntryWidgetPyQt # Import locally for type check in loop
    for i in reversed(range(gui.output_scrollable_layout.count())):
        widget = gui.output_scrollable_layout.itemAt(i).widget()
        if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path in videos_to_remove_ui:
            gui.output_scrollable_layout.removeWidget(widget)
            widget.deleteLater()
            logger.debug(f"Removed widget for {widget.video_path} from UI.")

    gui.selected_videos.clear()
    gui.update_selection_count()
    if gui.output_scrollable_widget: gui.output_scrollable_widget.adjustSize()


def delete_unselected_pyqt(gui):
    if not gui.videos:
        QMessageBox.information(gui, "Info", "No videos loaded to delete unselected from.")
        return

    unselected_video_paths = set(gui.videos.keys()) - gui.selected_videos
    if not unselected_video_paths:
        QMessageBox.information(gui, "Info", "No unselected videos to delete (or all are selected).")
        return

    reply = QMessageBox.question(gui, "Confirm Deletion",
                                 f"Are you sure you want to delete {len(unselected_video_paths)} unselected video(s) and their caches?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    if reply == QMessageBox.StandardButton.No:
        return

    videos_to_remove_ui = []
    for video_path in list(unselected_video_paths):
        try:
            if video_path.exists():
                os.remove(video_path)
                logger.info(f"Deleted video file: {video_path}")

            cache_dir = video_path.parent / "cache" / video_path.name
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logger.info(f"Deleted cache directory: {cache_dir}")

            if video_path in gui.videos:
                del gui.videos[video_path]

            videos_to_remove_ui.append(video_path)

        except Exception as e:
            # gui.report_error_slot(str(video_path), f"Failed to delete: {e}")
            QMessageBox.critical(gui, "Deletion Error", f"Failed to delete {video_path}: {e}")
            logger.error(f"Error deleting {video_path}: {e}")

    from .thumbnails import VideoEntryWidgetPyQt # Import locally for type check in loop
    for i in reversed(range(gui.output_scrollable_layout.count())):
        widget = gui.output_scrollable_layout.itemAt(i).widget()
        if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path in videos_to_remove_ui:
            gui.output_scrollable_layout.removeWidget(widget)
            widget.deleteLater()
            logger.debug(f"Removed widget for {widget.video_path} from UI.")

    gui.update_selection_count()
    if gui.output_scrollable_widget: gui.output_scrollable_widget.adjustSize()


def clear_all_selection_pyqt(gui):
    logger.debug(f"Clearing all selections. Currently selected: {len(gui.selected_videos)}")
    gui.selected_videos.clear()
    from .thumbnails import VideoEntryWidgetPyQt # Import locally for type check in loop
    for i in range(gui.output_scrollable_layout.count()):
        widget = gui.output_scrollable_layout.itemAt(i).widget()
        if isinstance(widget, VideoEntryWidgetPyQt):
            widget.checkbox.setChecked(False)
    gui.update_selection_count()
    logger.debug("All selections cleared.")