from pathlib import Path
from tkinter import ttk
from .input_tab_modules.controls import setup_input_controls
from .input_tab_modules.crypto_manager import CryptoManager, setup_crypto_links
from .input_tab_modules.distribution import setup_distribution_controls, toggle_peak_concentration
from .input_tab_modules.progress import setup_progress_controls, start_processing

def setup_input_tab(gui):
    """Configure the Input tab with controls and progress indicators."""
    # 既存のウィジェットをクリア（重複を防ぐ）
    for widget in gui.input_frame.winfo_children():
        widget.destroy()

    # フレームの初期化
    left_frame = ttk.Frame(gui.input_frame)
    left_frame.grid(row=0, column=0, padx=10, pady=5, sticky='n')
    right_frame = ttk.Frame(gui.input_frame)
    right_frame.grid(row=0, column=1, padx=10, pady=5, sticky='n')

    # コントロールのセットアップ
    row_left, row_right = setup_input_controls(gui, left_frame, right_frame)

    # 分布コントロールのセットアップ
    setup_distribution_controls(gui, right_frame, row_right)

    # 進捗コントロールのセットアップ
    setup_progress_controls(gui, gui.input_frame)

    # クリプトリンクのセットアップ
    gui.crypto_manager = CryptoManager(find_contents_path())
    setup_crypto_links(gui, gui.input_frame)

    gui.input_frame.columnconfigure(0, weight=1)
    gui.input_frame.columnconfigure(1, weight=1)

    gui.toggle_peak_concentration()

def find_contents_path():
    """Find the 'contents' directory by traversing parent directories."""
    current_path = Path(__file__).parent
    max_depth = 10  # Prevent infinite traversal
    for _ in range(max_depth):
        if (current_path / "contents").exists():
            return current_path / "contents"
        current_path = current_path.parent
    raise FileNotFoundError("Could not find 'contents' directory")