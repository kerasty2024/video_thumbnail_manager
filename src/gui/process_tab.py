from PyQt6.QtWidgets import QTextEdit, QLabel, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
from pathlib import Path
from PIL import Image, ImageQt
from loguru import logger

from .utils import resize_qimage # Assuming utils.py has this now

def setup_process_tab(gui):
    """Configure the Process tab with command log and thumbnail preview for PyQt6."""
    # gui.process_frame_layout is the QVBoxLayout for the process_tab QWidget

    gui.process_text_edit = QTextEdit()
    gui.process_text_edit.setReadOnly(True)
    gui.process_frame_layout.addWidget(gui.process_text_edit, 1) # Stretch factor 1

    gui.thumbnail_preview_label = QLabel("Thumbnail Preview")
    gui.thumbnail_preview_label.setFixedSize(320, 180) # Fixed size for preview
    gui.thumbnail_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    gui.thumbnail_preview_label.setStyleSheet("QLabel { background-color: gray; border: 1px solid black; }")
    gui.process_frame_layout.addWidget(gui.thumbnail_preview_label, 0, Qt.AlignmentFlag.AlignCenter) # No stretch, centered

def update_process_text_pyqt(gui, message):
    """Update the process tab text with a new message for PyQt6."""
    if gui.process_text_edit:
        gui.process_text_edit.append(message)
        # Auto scroll to bottom could be done with:
        # gui.process_text_edit.verticalScrollBar().setValue(gui.process_text_edit.verticalScrollBar().maximum())

def update_thumbnail_preview_pyqt(gui, thumbnail_path: Path):
    """Update the thumbnail preview in the process tab for PyQt6."""
    if gui.thumbnail_preview_label and thumbnail_path.exists():
        try:
            # Load with Pillow for robust format handling, then convert
            pil_img = Image.open(thumbnail_path)

            # Resize with Pillow while maintaining aspect ratio (fit into 320x180)
            pil_img.thumbnail((320,180), Image.Resampling.LANCZOS)

            # Convert Pillow Image to QImage then QPixmap
            qimage = ImageQt.ImageQt(pil_img.convert("RGBA"))
            pixmap = QPixmap.fromImage(qimage)

            gui.thumbnail_preview_label.setPixmap(pixmap)
            gui.current_thumbnail_pixmap = pixmap # Store reference if needed elsewhere
        except Exception as e:
            logger.error(f"Error displaying thumbnail {thumbnail_path} in preview: {e}")
            gui.thumbnail_preview_label.setText("Preview Error")
            update_process_text_pyqt(gui, f"Error displaying thumbnail {thumbnail_path}: {e}\n")
    elif gui.thumbnail_preview_label:
        gui.thumbnail_preview_label.setText("Preview N/A")