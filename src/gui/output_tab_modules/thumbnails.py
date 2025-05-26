from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                             QSizePolicy, QGridLayout, QFrame, QMenu, QApplication)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QCursor, QDesktopServices, QFontMetrics
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl, QPoint, QRectF

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont as PILImageFont, ImageQt
from loguru import logger
import subprocess

from ..utils import resize_image_pil # Assuming this exists and is correct
from .video_actions import play_video_pyqt, copy_filename_pyqt, copy_filepath_pyqt, open_in_explorer_pyqt

class ThumbnailLabel(QLabel):
    doubleClicked = pyqtSignal()
    rightClicked = pyqtSignal(QPoint)

    TIMESTAMP_AREA_HEIGHT = 20

    def __init__(self, gui, video_path, pil_image, timestamp_str, original_dims, parent=None):
        super().__init__(parent)
        self.gui = gui
        self.video_path = video_path
        self.pil_image_original = pil_image
        self.timestamp_str = timestamp_str
        self.original_image_width, self.original_image_height = original_dims
        self.is_zoomed = False
        self.current_pixmap = None

        self._pil_font = None
        try:
            self._pil_font = PILImageFont.truetype("arial.ttf", 10)
        except IOError:
            logger.warning("Arial font not found, using Pillow's default font for timestamps.")
            self._pil_font = PILImageFont.load_default()

        self._update_image_pixmap(self.pil_image_original, self.original_image_width, self.original_image_height)

        self.setScaledContents(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)
        self.setFixedSize(self.original_image_width, self.original_image_height + self.TIMESTAMP_AREA_HEIGHT)

    def _update_image_pixmap(self, pil_img_source, target_w, target_h_img):
        try:
            pil_img_resized = pil_img_source.resize((target_w, target_h_img), Image.Resampling.LANCZOS)
            qimage = ImageQt.ImageQt(pil_img_resized.convert("RGBA"))
            self.current_pixmap = QPixmap.fromImage(qimage)
        except Exception as e:
            logger.error(f"Error in _update_image_pixmap for {self.video_path}: {e}", exc_info=True)
            self.current_pixmap = QPixmap(target_w, target_h_img)
            self.current_pixmap.fill(Qt.GlobalColor.lightGray)
            p = QPainter(self.current_pixmap)
            p.setPen(Qt.GlobalColor.red)
            p.drawText(self.current_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Img Err")
            p.end()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        img_rect_w = self.width()
        img_rect_h = self.height() - self.TIMESTAMP_AREA_HEIGHT

        if self.current_pixmap:
            painter.drawPixmap(0, 0, self.current_pixmap)
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

            zoomed_image_w = int(self.original_image_width * zoom_factor)
            zoomed_image_h = int(self.original_image_height * zoom_factor)

            self._update_image_pixmap(self.pil_image_original, zoomed_image_w, zoomed_image_h)
            self.setFixedSize(zoomed_image_w, zoomed_image_h + self.TIMESTAMP_AREA_HEIGHT)
            self.is_zoomed = True
            if self.parentWidget() and hasattr(self.parentWidget(), 'updateGeometry'):
                self.parentWidget().updateGeometry()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.is_zoomed:
            self._update_image_pixmap(self.pil_image_original, self.original_image_width, self.original_image_height)
            self.setFixedSize(self.original_image_width, self.original_image_height + self.TIMESTAMP_AREA_HEIGHT)
            self.is_zoomed = False
            if self.parentWidget() and hasattr(self.parentWidget(), 'updateGeometry'):
                self.parentWidget().updateGeometry()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
            play_video_pyqt(self.gui, self.video_path)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if self.parentWidget() and hasattr(self.parentWidget(), 'toggle_entry_selection_from_child'):
            self.parentWidget().toggle_entry_selection_from_child()

        if event.button() == Qt.MouseButton.MiddleButton:
            play_video_pyqt(self.gui, self.video_path)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.rightClicked.emit(event.globalPos())


class VideoEntryWidgetPyQt(QFrame):
    _pil_error_font = None

    def __init__(self, gui, video_path: Path, thumbnails_data: list, timestamps: list, duration: float, video_specific_cache_dir: Path, parent=None):
        super().__init__(parent)
        self.gui = gui
        self.video_path = video_path
        self.thumbnails_data = thumbnails_data # List of thumbnail filenames
        self.timestamps = timestamps
        self.duration = duration
        self.video_specific_cache_dir = video_specific_cache_dir # Store this

        if VideoEntryWidgetPyQt._pil_error_font is None:
            try: VideoEntryWidgetPyQt._pil_error_font = PILImageFont.truetype("arial.ttf", 10)
            except IOError: VideoEntryWidgetPyQt._pil_error_font = PILImageFont.load_default()

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(3)

        top_part_layout = QHBoxLayout()
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(video_path in self.gui.selected_videos)
        self.checkbox.stateChanged.connect(self.on_selection_changed)
        top_part_layout.addWidget(self.checkbox)

        duration_str = self.format_duration(duration)
        video_label_text = f"{video_path.name} (Duration: {duration_str})"
        if hasattr(gui, 'video_counter'): video_label_text = f"{gui.video_counter}. {video_label_text}"

        self.video_label = QLabel(video_label_text)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.video_label.setWordWrap(True)
        top_part_layout.addWidget(self.video_label)
        self.main_layout.addLayout(top_part_layout)

        self.thumbnails_widget = QWidget()
        self.thumbnails_layout = QGridLayout(self.thumbnails_widget)
        self.thumbnails_layout.setSpacing(2)
        self.main_layout.addWidget(self.thumbnails_widget)

        self.thumbnail_labels = []
        self.load_thumbnails()
        self.update_selection_appearance(self.checkbox.isChecked())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.setChecked(not self.checkbox.isChecked())
        super().mousePressEvent(event)


    def load_thumbnails(self):
        if not all(hasattr(self.gui, attr) and getattr(self.gui, attr) is not None for attr in
                   ['thumbs_per_column_var', 'width_var']):
            logger.error(f"Cannot load thumbnails for {self.video_path}, GUI elements for dimensions not ready.")
            return

        thumbs_per_column = self.gui.thumbs_per_column_var.value()
        if thumbs_per_column <= 0: thumbs_per_column = 1

        original_image_width = self.gui.width_var.value()
        if original_image_width <=0: original_image_width = 160
        original_image_height = int(original_image_width * 9 / 16)

        # Use the video_specific_cache_dir passed during construction
        cache_base_for_this_video = self.video_specific_cache_dir

        for idx, thumb_filename in enumerate(self.thumbnails_data): # thumbnails_data is a list of filenames
            thumb_path = cache_base_for_this_video / thumb_filename # Construct full path
            pil_image = None
            if thumb_path.exists():
                try: pil_image = Image.open(thumb_path)
                except Exception as e: logger.error(f"Failed to open thumbnail {thumb_path}: {e}")

            if pil_image is None:
                pil_image = Image.new('RGB', (original_image_width, original_image_height), color='gray')
                draw = ImageDraw.Draw(pil_image)
                draw.text((5,5), "Error", fill="red", font=VideoEntryWidgetPyQt._pil_error_font)

            timestamp_val = self.timestamps[idx] if idx < len(self.timestamps) else 0.0
            timestamp_str = self.format_duration(timestamp_val)

            try:
                thumb_label = ThumbnailLabel(self.gui, self.video_path, pil_image, timestamp_str,
                                             (original_image_width, original_image_height),
                                             parent=self.thumbnails_widget)
                thumb_label.rightClicked.connect(self.show_context_menu_from_child)

                row = idx % thumbs_per_column
                col = idx // thumbs_per_column
                self.thumbnails_layout.addWidget(thumb_label, row, col)
                self.thumbnail_labels.append(thumb_label)
            except Exception as e:
                logger.error(f"Error creating ThumbnailLabel for {self.video_path} idx {idx} from {thumb_path}: {e}", exc_info=True)
        self.updateGeometry()

    def format_duration(self, secs):
        try: secs_float = float(secs)
        except (ValueError, TypeError):
            logger.warning(f"Invalid duration value for formatting: {secs}, using 0.0")
            secs_float = 0.0
        hours = int(secs_float // 3600)
        minutes = int((secs_float % 3600) // 60)
        seconds = int(secs_float % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def on_selection_changed(self, state_value): # state_value is int for Qt.CheckState
        is_selected = (Qt.CheckState(state_value) == Qt.CheckState.Checked)
        if is_selected: self.gui.selected_videos.add(self.video_path)
        else: self.gui.selected_videos.discard(self.video_path)
        self.update_selection_appearance(is_selected)
        self.gui.update_selection_count()


    def toggle_entry_selection_from_child(self):
        self.checkbox.setChecked(not self.checkbox.isChecked())

    def update_selection_appearance(self, is_selected):
        if is_selected:
            self.setStyleSheet("QFrame { background-color: lightblue; border: 1px solid black; }"
                               "QLabel { background-color: lightblue; }"
                               "QCheckBox { background-color: lightblue; }")
        else:
            self.setStyleSheet("QFrame { background-color: white; border: 1px solid black; }"
                               "QLabel { background-color: white; }"
                               "QCheckBox { background-color: white; }")
        for thumb_label in self.thumbnail_labels:
            thumb_label.setStyleSheet("QLabel { background-color: transparent; }")

    def contextMenuEvent(self, event): self.show_context_menu(event.globalPos())
    def show_context_menu_from_child(self, global_pos: QPoint): self.show_context_menu(global_pos)

    def show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        play_action = menu.addAction("Play Video")
        select_action = menu.addAction("Select/Deselect")
        copy_name_action = menu.addAction("Copy Filename")
        copy_path_action = menu.addAction("Copy Filepath")
        open_explorer_action = menu.addAction("Open in Explorer")

        action = menu.exec(global_pos)

        if action == play_action: play_video_pyqt(self.gui, self.video_path)
        elif action == select_action: self.checkbox.setChecked(not self.checkbox.isChecked())
        elif action == copy_name_action: copy_filename_pyqt(self.gui, self.video_path)
        elif action == copy_path_action: copy_filepath_pyqt(self.gui, self.video_path)
        elif action == open_explorer_action: open_in_explorer_pyqt(self.video_path)

# update_output_tab_pyqt now takes video_specific_cache_dir
def update_output_tab_pyqt(gui, video_path: Path, thumbnail_files: list, timestamps: list, duration: float, video_specific_cache_dir: Path):
    logger.debug(f"Updating Output tab for {video_path} using cache {video_specific_cache_dir} with {len(thumbnail_files)} thumbnails, duration: {duration}")

    if not hasattr(gui, 'output_scrollable_layout') or gui.output_scrollable_layout is None:
        logger.error("output_scrollable_layout not initialized in GUI. Cannot update output tab.")
        return

    gui.videos[video_path] = thumbnail_files # Store filenames
    gui.video_counter += 1

    existing_widget = None
    for i in range(gui.output_scrollable_layout.count()):
        item = gui.output_scrollable_layout.itemAt(i)
        if item and item.widget():
            widget = item.widget()
            if isinstance(widget, VideoEntryWidgetPyQt) and widget.video_path == video_path:
                existing_widget = widget
                break

    if existing_widget:
        gui.output_scrollable_layout.removeWidget(existing_widget)
        existing_widget.deleteLater()
        logger.debug(f"Removed existing widget for {video_path} to update.")

    try:
        video_entry = VideoEntryWidgetPyQt(gui, video_path, thumbnail_files, timestamps, duration, video_specific_cache_dir) # Pass it here
        gui.output_scrollable_layout.addWidget(video_entry)
    except Exception as e:
        logger.error(f"Error creating or adding VideoEntryWidgetPyQt for {video_path}: {e}", exc_info=True)
        return

    if hasattr(gui, 'output_scrollable_widget') and gui.output_scrollable_widget:
        gui.output_scrollable_widget.adjustSize()
    gui.update_selection_count()
    logger.debug(f"Added/Updated VideoEntryWidget for {video_path}")