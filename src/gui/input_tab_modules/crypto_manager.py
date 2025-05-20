# src/gui/input_tab_modules/crypto_manager.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PyQt6.QtGui import QPixmap, QCursor, QDesktopServices, QImage
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer # QTimer をインポート
from pathlib import Path
from PIL import Image, ImageQt
from loguru import logger
from ..utils import resize_image_pil

class CryptoManager:
    # ... (変更なし) ...
    def __init__(self, contents_path):
        self.contents_path = Path(contents_path)
        self.crypto_data = {
            "BTC": {
                "address": "bc1qn72yvftnuh7jgjnn9x848pzhhywasxmqt5c7wp",
                "qr_file": "BTC_QR.jpg"
            },
            "ETH": {
                "address": "0x2175Ed9c75C14F113ab9cEaDc1890b2f87f40e78",
                "qr_file": "ETH_QR.jpg"
            },
            "SOL": {
                "address": "6Hc7erZqgreTVwCsTtNvsyzigN2oHJ4EgNGaLWtRWJ69",
                "qr_file": "Solana_QR.jpg"
            }
        }

    def get_address(self, crypto):
        return self.crypto_data.get(crypto, {}).get("address", "")

    def get_qr_path(self, crypto):
        qr_file = self.crypto_data.get(crypto, {}).get("qr_file", "")
        return self.contents_path / "crypto" / qr_file if qr_file else None

class ClickableLabel(QLabel):
    # ... (変更なし) ...
    clicked = pyqtSignal()
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("QLabel { color: blue; text-decoration: underline; }")
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


def setup_crypto_links_pyqt(gui, parent_layout):
    links_group_widget = QWidget()
    links_frame_layout = QHBoxLayout(links_group_widget)

    left_crypto_layout = QVBoxLayout()
    left_crypto_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    github_label = QLabel("<a href='https://github.com/kerasty2024/'>Github: kerasty2024</a>")
    github_label.setOpenExternalLinks(True)
    github_label.setToolTip("Visit the author's GitHub profile.")
    left_crypto_layout.addWidget(github_label)

    coffee_label = QLabel("<a href='https://www.buymeacoffee.com/kerasty'>Buy Me a Coffee: kerasty</a>")
    coffee_label.setOpenExternalLinks(True)
    coffee_label.setToolTip("Support the author with a coffee via Buy Me a Coffee.")
    left_crypto_layout.addWidget(coffee_label)

    for crypto, data in gui.crypto_manager.crypto_data.items():
        address = data["address"]
        label = ClickableLabel(f"{crypto} Address: {address}")
        label.setToolTip(f"Click to copy {crypto} address for donations.")
        label.clicked.connect(lambda c=crypto, a=address: copy_crypto_address_pyqt(gui, c, a))
        left_crypto_layout.addWidget(label)

    left_crypto_layout.addStretch(1)
    links_frame_layout.addLayout(left_crypto_layout, 1)

    gui.qr_label = QLabel()
    gui.qr_label.setFixedSize(100, 100)
    gui.qr_label.setToolTip("QR code for the selected cryptocurrency address.")
    gui.qr_label.setStyleSheet("QLabel { border: 1px solid lightgray; background-color: white; }") # 背景と境界線
    links_frame_layout.addWidget(gui.qr_label, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

    # QTimer.singleShotを使用して、イベントループが少し進んでからQRコードを更新
    QTimer.singleShot(0, lambda: update_qr_code_display(gui, "BTC"))

    parent_layout.addWidget(links_group_widget)


def copy_crypto_address_pyqt(gui, crypto, address):
    clipboard = QApplication.clipboard()
    clipboard.setText(address)
    logger.debug(f"Copied {crypto} address to clipboard: {address}")
    if hasattr(gui, 'update_completion_label_slot'):
        gui.update_completion_label_slot(f"{crypto} address copied to clipboard!")
    update_qr_code_display(gui, crypto)

def update_qr_code_display(gui, crypto):
    gui.current_crypto = crypto
    qr_path = gui.crypto_manager.get_qr_path(crypto)

    if not hasattr(gui, 'qr_label') or gui.qr_label is None:
        logger.warning("gui.qr_label not initialized in update_qr_code_display")
        return

    if qr_path and qr_path.exists():
        try:
            pil_image = Image.open(qr_path)
            # リサイズは固定サイズ(100x100)に合わせる
            pil_image_resized = pil_image.resize((100, 100), Image.Resampling.LANCZOS)

            qimage = ImageQt.ImageQt(pil_image_resized.convert("RGBA"))
            gui.qr_pixmap = QPixmap.fromImage(qimage)
            gui.qr_label.setPixmap(gui.qr_pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            gui.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # 中央揃え
        except Exception as e:
            logger.error(f"Failed to load or display QR code for {crypto}: {e}", exc_info=True)
            gui.qr_label.setText("QR\nError")
            gui.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if hasattr(gui, 'update_completion_label_slot'):
                gui.update_completion_label_slot(f"Failed to load {crypto} QR code")
    else:
        logger.warning(f"QR code path not found for {crypto}: {qr_path}")
        gui.qr_label.setText("QR\nN/A")
        gui.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if hasattr(gui, 'update_completion_label_slot'):
            gui.update_completion_label_slot(f"QR code for {crypto} not found")