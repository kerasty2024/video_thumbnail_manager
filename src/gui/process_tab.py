import tkinter as tk
from PIL import Image, ImageTk
import os

from loguru import logger

def setup_process_tab(gui):
    """Configure the Process tab with command log and thumbnail preview."""
    gui.process_text = tk.Text(gui.process_frame, height=15, width=80)
    gui.process_text.pack(padx=5, pady=5, fill='both', expand=True)

    gui.thumbnail_canvas = tk.Canvas(gui.process_frame, width=320, height=180, bg='gray')
    gui.thumbnail_canvas.pack(padx=5, pady=5)

def update_process_text(gui, message):
    """Update the process tab text with a new message."""
    gui.process_text.insert(tk.END, message)
    gui.process_text.see(tk.END)

def update_thumbnail_preview(gui, thumbnail_path):
    """Update the thumbnail preview in the process tab."""
    if os.path.exists(thumbnail_path):
        try:
            img = Image.open(thumbnail_path).resize((320, 180), Image.Resampling.LANCZOS)
            gui.current_thumbnail = ImageTk.PhotoImage(img)
            gui.thumbnail_canvas.delete("all")
            gui.thumbnail_canvas.create_image(0, 0, anchor='nw', image=gui.current_thumbnail)
        except Exception as e:
            update_process_text(gui, f"Error displaying thumbnail {thumbnail_path}: {e}\n")