from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                             QSizePolicy, QGridLayout, QFrame, QMenu, QApplication)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QCursor, QDesktopServices, QFontMetrics
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl, QPoint, QRectF

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont as PILImageFont, ImageQt
from loguru import logger
import subprocess
import os

from ..utils import resize_image_pil
from .video_actions import play_video_pyqt, copy_filename_pyqt, copy_filepath_pyqt, open_in_explorer_pyqt

class ThumbnailLabel(QLabel):
    doubleClicked = pyqtSignal()
    rightClicked = pyqtSignal(QPoint)

    TIMESTAMP_AREA_HEIGHT = 20

    def __init__(self, gui, video_path, pil_image_original, timestamp_str, parent=None):
        super().__init__(parent)
        self.gui = gui
        self.video_path = video_path
        self.pil_image_original = pil_image_original

        self.original_ffmpeg_width = self.pil_image_original.width
        self.original_ffmpeg_height = self.pil_image_original.height

        self.timestamp_str = timestamp_str
        self.is_zoomed = False
        self.current_pixmap = None

        self._pil_font = None
        try:
            self._pil_font = PILImageFont.truetype("arial.ttf", 10)
        except IOError:
            logger.warning("Arial font not found, using Pillow's default font for timestamps (if drawn by PIL).")
            self._pil_font = PILImageFont.load_default()

        self._update_display_pixmap_and_size()

        self.setScaledContents(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)

    def _calculate_display_dimensions(self, zoom_factor=1.0):
        base_display_width = self.gui.width_var.value()
        target_display_width = int(base_display_width * zoom_factor)

        if self.original_ffmpeg_width > 0:
            aspect_ratio = self.original_ffmpeg_height / self.original_ffmpeg_width
            target_display_height = int(target_display_width * aspect_ratio)
        else:
            target_display_height = int(self.gui.width_var.value() * 9/16 * zoom_factor)

        return target_display_width, target_display_height

    def _update_display_pixmap_and_size(self, zoom_factor=1.0):
        target_w, target_h_img = self._calculate_display_dimensions(zoom_factor)

        try:
            pil_img_resized = self.pil_image_original.resize((target_w, target_h_img), Image.Resampling.LANCZOS)
            qimage = ImageQt.ImageQt(pil_img_resized.convert("RGBA"))
            self.current_pixmap = QPixmap.fromImage(qimage)
        except Exception as e:
            logger.error(f"Error resizing/converting PIL image for {self.video_path}: {e}", exc_info=True)
            self.current_pixmap = QPixmap(target_w, target_h_img)
            self.current_pixmap.fill(Qt.GlobalColor.lightGray)
            p = QPainter(self.current_pixmap)
            p.setPen(Qt.GlobalColor.red)
            p.drawText(self.current_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Img Err")
            p.end()

        self.setFixedSize(target_w, target_h_img + self.TIMESTAMP_AREA_HEIGHT)
        self.update()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        img_rect_w = self.width()
        img_rect_h = self.height() - self.TIMESTAMP_AREA_HEIGHT

        if self.current_pixmap:
            px = (img_rect_w - self.current_pixmap.width()) // 2
            py = (img_rect_h - self.current_pixmap.height()) // 2
            painter.drawPixmap(px, py, self.current_pixmap)
        else:
            painter.fillRect(0, 0, img_rect_w, img_rect_h, Qt.GlobalColor.darkGray)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(QRectF(0,0, img_rect_w, img_rect_h), Qt.AlignmentFlag.AlignCenter, "No Img")

        timestamp_bg_rect = QRectF(0, img_rect_h, img_rect_w, self.TIMESTAMP_AREA_HEIGHT)
        painter.fillRect(timestamp_bg_rect, QColor(0,0,0,180))

        painter.setPen(Qt.GlobalColor.white)
        qfont = QFont("Arial", 8)
        painter.setFont(qfont)

        fm = QFontMetrics(qfont)
        elided_timestamp = fm.elidedText(self.timestamp_str, Qt.TextElideMode.ElideRight, img_rect_w - 4)

        text_rect = QRectF(2, img_rect_h, img_rect_w - 4, self.TIMESTAMP_AREA_HEIGHT)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, elided_timestamp)

    def enterEvent(self, event):
        if QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier and not self.is_zoomed:
            if not hasattr(self.gui, 'zoom_var') or self.gui.zoom_var is None: return
            zoom_factor = self.gui.zoom_var.value()

            self._update_display_pixmap_and_size(zoom_factor)
            self.is_zoomed = True
            if self.parentWidget() and hasattr(self.parentWidget(), 'updateGeometry'):
                if self.parentWidget().parentWidget() and hasattr(self.parentWidget().parentWidget(), 'updateGeometry'):
                    self.parentWidget().parentWidget().updateGeometry()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.is_zoomed:
            self._update_display_pixmap_and_size(zoom_factor=1.0)
            self.is_zoomed = False
            if self.parentWidget() and hasattr(self.parentWidget(), 'updateGeometry'):
                if self.parentWidget().parentWidget() and hasattr(self.parentWidget().parentWidget(), 'updateGeometry'):
                    self.parentWidget().parentWidget().updateGeometry()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
            play_video_pyqt(self.gui, self.video_path)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        video_entry_widget = self.parentWidget()
        if video_entry_widget:
            grand_parent_widget = video_entry_widget.parentWidget()
            if grand_parent_widget and hasattr(grand_parent_widget, 'toggle_entry_selection_from_child'):
                grand_parent_widget.toggle_entry_selection_from_child()

        if event.button() == Qt.MouseButton.MiddleButton:
            play_video_pyqt(self.gui, self.video_path)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.rightClicked.emit(event.globalPos())


class VideoEntryWidgetPyQt(QFrame):
    _pil_error_font = None

    def __init__(self, gui, video_path: Path, thumbnails_data: list, timestamps: list,
                 duration: float, video_specific_cache_dir: Path, processing_order: int, parent=None):
        super().__init__(parent)
        self.gui = gui
        self.video_path = video_path
        self.processing_order = processing_order
        self.display_order = -1 # Will be set by sorting logic or when added initially
        self.thumbnails_data = thumbnails_data
        self.duration = duration
        self.video_specific_cache_dir = video_specific_cache_dir

        try:
            self.file_size = os.path.getsize(self.video_path) if self.video_path.exists() else 0
            self.date_modified = os.path.getmtime(self.video_path) if self.video_path.exists() else 0
        except OSError:
            self.file_size = 0
            self.date_modified = 0

        self.timestamps = timestamps

        if VideoEntryWidgetPyQt._pil_error_font is None:
            try: VideoEntryWidgetPyQt._pil_error_font = PILImageFont.truetype("arial.ttf", 10)
            except IOError: VideoEntryWidgetPyQt._pil_error_font = PILImageFont.load_default()

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(3)

        self.top_info_widget = QWidget()
        self.top_info_layout = QHBoxLayout(self.top_info_widget)
        self.top_info_layout.setContentsMargins(0,0,0,0)
        self.top_info_layout.setSpacing(5)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(video_path in self.gui.selected_videos)
        self.checkbox.stateChanged.connect(self.on_selection_changed)
        self.top_info_layout.addWidget(self.checkbox)

        self.video_label = QLabel()
        self.video_label.setObjectName("VideoLabel")
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.video_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.top_info_layout.addWidget(self.video_label)
        self.main_layout.addWidget(self.top_info_widget)

        # update_video_label_text will be called after display_order is set
        # self.update_video_label_text() # Call this after display_order is assigned

        self.thumbnails_widget = QWidget()
        self.thumbnails_layout = QGridLayout(self.thumbnails_widget)
        self.thumbnails_layout.setSpacing(2)
        self.main_layout.addWidget(self.thumbnails_widget)

        self.thumbnail_labels = []
        self.load_thumbnails()
        self.update_selection_appearance(self.checkbox.isChecked())

    def set_display_order(self, order: int):
        """Sets the display order and updates the label."""
        if self.display_order != order: # Only update if it changes
            self.display_order = order
            self.update_video_label_text()

    def update_video_label_text(self):
        """Updates the video label text using the current display_order."""
        if self.display_order < 0: # display_order not yet set
            return

        display_name_full = str(self.video_path.resolve())
        display_name_short = self.video_path.name

        chosen_display_name = display_name_full if self.gui.show_full_path_in_output else display_name_short

        duration_str = self.format_duration(self.duration)
        size_str = self.format_size(self.file_size)

        base_text = f"#{self.display_order}. {chosen_display_name} (Dur: {duration_str}, Size: {size_str})"

        self.video_label.setText(base_text)
        self.video_label.setWordWrap(True)

        tooltip_text = (f"Display Order: #{self.display_order}\n"
                        f"Original Processing Order: #{self.processing_order}\n"
                        f"Full Path: {display_name_full}\n"
                        f"Duration: {duration_str}, Size: {size_str}")
        self.video_label.setToolTip(tooltip_text)


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            is_interactive_child = False
            if child:
                if isinstance(child, QCheckBox) or \
                        (child.parentWidget() and isinstance(child.parentWidget(), QCheckBox)):
                    is_interactive_child = True
                elif isinstance(child, ThumbnailLabel):
                    is_interactive_child = True
                elif child.parentWidget() and isinstance(child.parentWidget(), ThumbnailLabel):
                    is_interactive_child = True
                elif child == self.video_label or (child.parentWidget() and child.parentWidget() == self.video_label):
                    pass

            if not is_interactive_child:
                self.checkbox.setChecked(not self.checkbox.isChecked())
        super().mousePressEvent(event)


    def load_thumbnails(self):
        if not all(hasattr(self.gui, attr) and getattr(self.gui, attr) is not None for attr in
                   ['thumbs_per_column_var', 'width_var']):
            logger.error(f"Cannot load thumbnails for {self.video_path}, GUI elements for dimensions not ready.")
            return

        thumbs_per_column = self.gui.thumbs_per_column_var.value()
        if thumbs_per_column <= 0: thumbs_per_column = 1

        target_thumb_display_width = self.gui.width_var.value()
        if target_thumb_display_width <=0: target_thumb_display_width = 160

        for idx, thumb_filename in enumerate(self.thumbnails_data):
            thumb_path_abs = self.video_specific_cache_dir / thumb_filename
            pil_image = None
            if thumb_path_abs.exists():
                try:
                    pil_image = Image.open(thumb_path_abs)
                    pil_image.load()
                except Exception as e:
                    logger.error(f"Failed to open thumbnail {thumb_path_abs}: {e}")

            if pil_image is None:
                placeholder_height = int(target_thumb_display_width * 9 / 16)
                pil_image = Image.new('RGB', (target_thumb_display_width, placeholder_height), color='lightgray')
                draw = ImageDraw.Draw(pil_image)
                try:
                    draw.text((5,5), "Load Err", fill="red", font=VideoEntryWidgetPyQt._pil_error_font)
                except Exception as font_e:
                    logger.warning(f"Failed to draw text on error placeholder: {font_e}")


            timestamp_val = self.timestamps[idx] if idx < len(self.timestamps) else 0.0
            timestamp_str = self.format_duration(timestamp_val)

            try:
                thumb_label = ThumbnailLabel(self.gui, self.video_path, pil_image, timestamp_str,
                                             parent=self.thumbnails_widget)
                thumb_label.rightClicked.connect(self.show_context_menu_from_child)

                row = idx % thumbs_per_column
                col = idx // thumbs_per_column
                self.thumbnails_layout.addWidget(thumb_label, row, col)
                self.thumbnail_labels.append(thumb_label)
            except Exception as e:
                logger.error(f"Error creating ThumbnailLabel for {self.video_path} idx {idx} from {thumb_path_abs}: {e}", exc_info=True)

        self.thumbnails_widget.adjustSize()
        self.updateGeometry()


    def format_duration(self, secs: float) -> str:
        try:
            secs_float = float(secs)
            if secs_float < 0: secs_float = 0.0
        except (ValueError, TypeError):
            logger.warning(f"Invalid duration value for formatting: {secs}, using 0.0")
            secs_float = 0.0

        hours = int(secs_float // 3600)
        minutes = int((secs_float % 3600) // 60)
        seconds = int(secs_float % 60)
        if hours > 0:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        elif minutes == 0 and seconds == 0 and hours == 0:
            return "00:00"
        else:
            return f"{minutes:02d}:{seconds:02d}"


    def format_size(self, size_bytes: int) -> str:
        if size_bytes < 0: size_bytes = 0
        if size_bytes == 0: return "0 B"

        size_names = ("B", "KB", "MB", "GB", "TB")
        i = 0
        size_f = float(size_bytes)

        while size_f >= 1024 and i < len(size_names) - 1:
            size_f /= 1024.0
            i += 1

        if i == 0:
            return f"{int(size_f)} {size_names[i]}"
        else:
            return f"{size_f:.1f} {size_names[i]}"


    def on_selection_changed(self, state_value):
        is_selected = (Qt.CheckState(state_value) == Qt.CheckState.Checked)
        if is_selected: self.gui.selected_videos.add(self.video_path)
        else: self.gui.selected_videos.discard(self.video_path)
        self.update_selection_appearance(is_selected)
        self.gui.update_selection_count()


    def toggle_entry_selection_from_child(self):
        self.checkbox.setChecked(not self.checkbox.isChecked())

    def update_selection_appearance(self, is_selected):
        if is_selected:
            self.setStyleSheet("QFrame { background-color: #ADD8E6; border: 1px solid #0078D7; }"
                               "QLabel#VideoLabel { background-color: transparent; }"
                               "QCheckBox { background-color: transparent; }")
        else:
            self.setStyleSheet("QFrame { background-color: white; border: 1px solid lightgray; }"
                               "QLabel#VideoLabel { background-color: transparent; }"
                               "QCheckBox { background-color: transparent; }")

        if hasattr(self, 'video_label'):
            self.video_label.setStyleSheet("background-color: transparent;")


    def contextMenuEvent(self, event): self.show_context_menu(event.globalPos())
    def show_context_menu_from_child(self, global_pos: QPoint): self.show_context_menu(global_pos)

    def show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        play_action = menu.addAction("Play Video")
        select_action = menu.addAction("Select/Deselect")
        menu.addSeparator()
        copy_name_action = menu.addAction("Copy Filename")
        copy_path_action = menu.addAction("Copy Filepath")
        menu.addSeparator()
        open_explorer_action = menu.addAction("Open in Explorer")

        action = menu.exec(global_pos)

        if action == play_action: play_video_pyqt(self.gui, self.video_path)
        elif action == select_action: self.checkbox.setChecked(not self.checkbox.isChecked())
        elif action == copy_name_action: copy_filename_pyqt(self.gui, self.video_path)
        elif action == copy_path_action: copy_filepath_pyqt(self.gui, self.video_path)
        elif action == open_explorer_action: open_in_explorer_pyqt(self.video_path)

def update_output_tab_pyqt(gui, video_path: Path, thumbnail_files: list, timestamps: list,
                           duration: float, video_specific_cache_dir: Path, processing_order: int):
    logger.debug(f"Adding to Output tab: Processing Order #{processing_order} {video_path.name}")

    if not hasattr(gui, 'output_scrollable_layout') or gui.output_scrollable_layout is None:
        logger.error("output_scrollable_layout not initialized in GUI. Cannot update output tab.")
        return

    gui.videos[video_path] = thumbnail_files

    try:
        video_entry = VideoEntryWidgetPyQt(gui, video_path, thumbnail_files, timestamps, duration,
                                           video_specific_cache_dir, processing_order)
        # Set initial display_order based on current layout count (will be updated by sort)
        # This assumes items are added sequentially to the end when "Original Order" is active
        initial_display_order = gui.output_scrollable_layout.count() + 1
        video_entry.set_display_order(initial_display_order)

        gui.output_scrollable_layout.addWidget(video_entry)
    except Exception as e:
        logger.error(f"Error creating or adding VideoEntryWidgetPyQt for {video_path}: {e}", exc_info=True)
        return

    logger.trace(f"Added VideoEntryWidget for Processing Order #{processing_order} ({video_path.name}) with initial display_order #{initial_display_order}.")