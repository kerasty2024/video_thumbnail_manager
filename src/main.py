import tkinter as tk
import argparse

from loguru import logger

from src.gui.thumbnail_gui import VideoThumbnailGUI
from src.version import __version__


def main():
    print(f"Video Thumbnail Manager v{__version__}")
    """Entry point to launch the Video Thumbnail Manager GUI."""
    parser = argparse.ArgumentParser(description="Video Thumbnail Manager")
    parser.add_argument("-l", "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level (default: INFO)")
    args = parser.parse_args()

    logger.add("../debug.log", level=args.log_level)
    root = tk.Tk()
    app = VideoThumbnailGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
