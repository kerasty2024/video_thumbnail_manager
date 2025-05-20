from pathlib import Path
from PIL import Image, ImageQt # ImageQt for Pillow to QImage
from PyQt6.QtGui import QImage, QPixmap, QPainter # QPainter を追加
from PyQt6.QtCore import QSize, Qt # Qt をインポート

def resize_image_pil(pil_image: Image.Image, size: tuple) -> Image.Image:
    """Resize a PIL Image to the specified size using LANCZOS filter."""
    return pil_image.resize(size, Image.Resampling.LANCZOS)

def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    """Converts a PIL Image to a QPixmap."""
    # Ensure image is in a mode Qt can handle well, e.g. RGBA for transparency
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")

    qimage = ImageQt.ImageQt(pil_image)
    return QPixmap.fromImage(qimage)

def resize_qimage(q_image: QImage, target_width: int, target_height: int,
                  keep_aspect_ratio: bool = True,
                  bg_color: Qt.GlobalColor = Qt.GlobalColor.transparent) -> QImage: # Qt.GlobalColor が使えるように
    """
    Resize a QImage to target_width and target_height.
    If keep_aspect_ratio is True, the image is scaled to fit and padded if necessary.
    """
    if keep_aspect_ratio:
        scaled_image = q_image.scaled(target_width, target_height,
                                      Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
        # Create a new image with the target size and fill with bg_color
        final_image = QImage(target_width, target_height, QImage.Format.Format_ARGB32_Premultiplied)
        final_image.fill(bg_color) # bg_color は Qt.GlobalColor 型の値

        painter = QPainter(final_image)
        # Calculate top-left position to center the scaled image
        x = (target_width - scaled_image.width()) // 2
        y = (target_height - scaled_image.height()) // 2
        painter.drawImage(x, y, scaled_image)
        painter.end()
        return final_image
    else:
        return q_image.scaled(target_width, target_height,
                              Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)

def resize_qpixmap(pixmap: QPixmap, width: int, height: int,
                   keep_aspect_ratio: bool = True,
                   bg_color: Qt.GlobalColor = Qt.GlobalColor.transparent) -> QPixmap: # Qt.GlobalColor が使えるように
    """Resizes a QPixmap, optionally keeping aspect ratio and padding."""
    qimage = pixmap.toImage()
    resized_qimage = resize_qimage(qimage, width, height, keep_aspect_ratio, bg_color) # keep_aspect_ratio のタイポ修正
    return QPixmap.fromImage(resized_qimage)