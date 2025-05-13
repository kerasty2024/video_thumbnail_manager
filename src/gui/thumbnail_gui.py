import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from loguru import logger

from src.config import Config
from src.video_processor.processor import VideoProcessor
from src.gui.input_tab import setup_input_tab
from src.gui.output_tab import setup_output_tab
from src.gui.process_tab import setup_process_tab
from src.gui.input_tab_modules.distribution import toggle_peak_concentration, update_distribution_graph
from src.gui.output_tab_modules.selection import delete_selected, delete_unselected, clear_all_selection
from src.gui.output_tab_modules.video_actions import on_mouse_wheel
from src.version import __version__

class VideoThumbnailGUI:
    def __init__(self, root):
        self.root = root
        self.config = Config()
        self.processor = VideoProcessor(
            self.config.get('cache_dir'),
            self.config.get('thumbnails_per_video'),
            self.config.get('thumbnail_width'),
            self.config.get('thumbnail_quality'),
            self.config.get('concurrent_videos'),
            self.config.get('min_size_mb'),
            self.config.get('min_duration_seconds'),
            self.update_output_tab
        )
        self.videos = {}
        self.selected_videos = set()
        self.current_thumbnail = None
        self.photo_references = []
        self.zoom_labels = {}
        self.total_videos = 0
        self.processed_thumbnails = 0
        self.total_thumbnails = 0
        self.start_time = None
        self.video_counter = 0
        self.current_crypto = "BTC"
        self.folder_var = tk.StringVar(value=self.config.get('default_folder'))
        self.setup_gui()

    def setup_gui(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.75)
        window_height = int(screen_height * 0.75)
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.title(f"Video Thumbnail Manager by Kerasty ver. {__version__}")

        # ノートブックの初期化（重複がないように1回だけ）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # 既存のタブをクリア（念のため）
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)

        # Inputタブのフレームを初期化（重複を防ぐ）
        self.input_frame = ttk.Frame(self.notebook)
        self.output_frame = ttk.Frame(self.notebook)
        self.process_frame = ttk.Frame(self.notebook)

        # タブを追加（1回だけ）
        self.notebook.add(self.input_frame, text='Input')
        self.notebook.add(self.output_frame, text='Output')
        self.notebook.add(self.process_frame, text='Process')

        # 選択カウントラベルの設定
        self.selection_count_label = ttk.Label(self.output_frame, text="0 of 0 selected")
        self.selection_count_label.pack(side='top')

        # 各タブのセットアップ（1回だけ呼び出し）
        setup_input_tab(self)
        setup_output_tab(self)
        setup_process_tab(self)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)
            logger.debug(f"Selected folder: {folder}")

    def report_error(self, video, error_message):
        messagebox.showerror("Error", f"Error processing {video}:\n{error_message}")
        logger.error(f"Reported error for {video}: {error_message}")

    def update_selection_count(self):
        count = len(self.selected_videos)
        total = len(self.videos)
        self.selection_count_label.config(text=f"{count} of {total} selected")
        logger.debug(f"Updated selection count: {count} of {total}")

    def update_output_tab(self, video, thumbnails, timestamps, duration):
        from src.gui.output_tab import update_output_tab
        update_output_tab(self, video, thumbnails, timestamps, duration)

    def toggle_peak_concentration(self, *args):
        toggle_peak_concentration(self, *args)

    def on_mouse_wheel(self, event):
        on_mouse_wheel(self, event)

    def delete_selected(self):
        delete_selected(self)

    def delete_unselected(self):
        delete_unselected(self)

    def clear_all_selection(self):
        clear_all_selection(self)

    def update_distribution_graph(self, *args):
        update_distribution_graph(self, *args)