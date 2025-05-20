import sys
import argparse
from PyQt6.QtWidgets import QApplication
from loguru import logger
from pathlib import Path

from src.gui.thumbnail_gui import VideoThumbnailGUI
from src.version import __version__ # src/version.py からインポート

def main():
    print(f"Video Thumbnail Manager v{__version__}")
    parser = argparse.ArgumentParser(description="Video Thumbnail Manager")
    parser.add_argument("-l", "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level (default: INFO)")
    args = parser.parse_args()

    # ../debug.log へのパスは main.py の場所からの相対パス
    # プロジェクトルートからのパスで指定する場合は適宜調整
    log_file_path = Path(__file__).resolve().parent.parent / "debug.log"
    logger.add(log_file_path, level=args.log_level)

    app = QApplication(sys.argv)
    window = VideoThumbnailGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    from pathlib import Path # main() 内の logger.add のために追加
    main()