from tkinter import ttk
from .output_tab_modules.canvas import setup_output_canvas
from .output_tab_modules.selection import delete_selected, delete_unselected, clear_all_selection
from .output_tab_modules.thumbnails import update_output_tab
from .output_tab_modules.video_actions import on_mouse_wheel

def setup_output_tab(gui):
    """Configure the Output tab for thumbnail display."""
    setup_output_canvas(gui)

    ttk.Button(gui.output_frame, text="Delete Selected", command=gui.delete_selected).pack(side='top')
    ttk.Button(gui.output_frame, text="Delete Unselected", command=gui.delete_unselected).pack(side='top')
    ttk.Button(gui.output_frame, text="Clear All Selection", command=gui.clear_all_selection).pack(side='top')