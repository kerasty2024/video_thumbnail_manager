import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from loguru import logger

import typing
if typing.TYPE_CHECKING:
    from .thumbnails import VideoEntryWidgetPyQt # Assuming this is the type
    from src.gui.thumbnail_gui import VideoThumbnailGUI


def delete_selected_pyqt(gui: 'VideoThumbnailGUI'):
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
    last_deleted_processing_order = None # Store the processing order of the last successfully deleted video

    selected_video_paths_copy = list(gui.selected_videos)

    for video_path in selected_video_paths_copy:
        try:
            current_processing_order = -1
            # Find the widget to get its processing_order
            from .thumbnails import VideoEntryWidgetPyQt # Local import for type check
            for i in range(gui.output_scrollable_layout.count()): # Iterate normally to find
                widget = gui.output_scrollable_layout.itemAt(i).widget()
                if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path == video_path:
                    if hasattr(widget, 'processing_order'):
                        current_processing_order = widget.processing_order
                    break

            if video_path.exists():
                os.remove(video_path)
                logger.info(f"Deleted video file: {video_path}")

            if gui.processor and gui.processor.cache_dir:
                cache_dir_for_video = gui.processor.cache_dir / video_path.name
                if cache_dir_for_video.exists():
                    shutil.rmtree(cache_dir_for_video)
                    logger.info(f"Deleted cache directory: {cache_dir_for_video}")
            else:
                logger.warning(f"Processor or cache_dir not available, cannot delete cache for {video_path}")

            if video_path in gui.videos:
                del gui.videos[video_path]

            gui.selected_videos.discard(video_path)

            videos_to_remove_ui.append(video_path)

            if current_processing_order != -1:
                last_deleted_processing_order = current_processing_order


        except Exception as e:
            QMessageBox.critical(gui, "Deletion Error", f"Failed to delete {video_path}: {e}")
            logger.error(f"Error deleting {video_path}: {e}")

    from .thumbnails import VideoEntryWidgetPyQt
    if videos_to_remove_ui:
        for i in reversed(range(gui.output_scrollable_layout.count())):
            widget = gui.output_scrollable_layout.itemAt(i).widget()
            if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path in videos_to_remove_ui:
                gui.output_scrollable_layout.removeWidget(widget)
                widget.deleteLater()
                logger.debug(f"Removed widget for {widget.video_path} from UI.")

    gui.update_selection_count() # Updates count and jump widget max
    if last_deleted_processing_order is not None:
        gui.update_last_deleted_label(last_deleted_processing_order)

    if gui.output_scrollable_widget: gui.output_scrollable_widget.adjustSize()
    # Removed automatic scrolling to deleted item area


def delete_unselected_pyqt(gui: 'VideoThumbnailGUI'):
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
    last_deleted_processing_order = None

    unselected_video_paths_copy = list(unselected_video_paths)

    for video_path in unselected_video_paths_copy:
        try:
            current_processing_order = -1
            from .thumbnails import VideoEntryWidgetPyQt
            for i in range(gui.output_scrollable_layout.count()):
                widget = gui.output_scrollable_layout.itemAt(i).widget()
                if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path == video_path:
                    if hasattr(widget, 'processing_order'):
                        current_processing_order = widget.processing_order
                    break

            if video_path.exists():
                os.remove(video_path)
                logger.info(f"Deleted video file: {video_path}")

            if gui.processor and gui.processor.cache_dir:
                cache_dir_for_video = gui.processor.cache_dir / video_path.name
                if cache_dir_for_video.exists():
                    shutil.rmtree(cache_dir_for_video)
                    logger.info(f"Deleted cache directory: {cache_dir_for_video}")
            else:
                logger.warning(f"Processor or cache_dir not available, cannot delete cache for {video_path}")

            if video_path in gui.videos:
                del gui.videos[video_path]

            videos_to_remove_ui.append(video_path)
            if current_processing_order != -1:
                last_deleted_processing_order = current_processing_order

        except Exception as e:
            QMessageBox.critical(gui, "Deletion Error", f"Failed to delete {video_path}: {e}")
            logger.error(f"Error deleting {video_path}: {e}")

    from .thumbnails import VideoEntryWidgetPyQt
    if videos_to_remove_ui:
        for i in reversed(range(gui.output_scrollable_layout.count())):
            widget = gui.output_scrollable_layout.itemAt(i).widget()
            if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path in videos_to_remove_ui:
                gui.output_scrollable_layout.removeWidget(widget)
                widget.deleteLater()
                logger.debug(f"Removed widget for {widget.video_path} from UI.")

    gui.update_selection_count()
    if last_deleted_processing_order is not None:
        gui.update_last_deleted_label(last_deleted_processing_order)

    if gui.output_scrollable_widget: gui.output_scrollable_widget.adjustSize()
    # Removed automatic scrolling


def clear_all_selection_pyqt(gui: 'VideoThumbnailGUI'):
    logger.debug(f"Clearing all selections. Currently selected: {len(gui.selected_videos)}")
    gui.selected_videos.clear()
    from .thumbnails import VideoEntryWidgetPyQt
    for i in range(gui.output_scrollable_layout.count()):
        widget = gui.output_scrollable_layout.itemAt(i).widget()
        if isinstance(widget, VideoEntryWidgetPyQt):
            widget.checkbox.setChecked(False)
    gui.update_selection_count()
    gui.update_last_deleted_label(None)
    logger.debug("All selections cleared.")