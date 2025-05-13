import tkinter as tk
from tkinter import ttk

def setup_output_canvas(gui):
    """Setup the canvas and scrollbars for the Output tab."""
    gui.output_canvas = tk.Canvas(gui.output_frame)
    gui.output_scrollbar = ttk.Scrollbar(gui.output_frame, orient='vertical', command=gui.output_canvas.yview)
    gui.output_scrollbar_x = ttk.Scrollbar(gui.output_frame, orient='horizontal', command=gui.output_canvas.xview)
    gui.output_scrollable_frame = tk.Frame(gui.output_canvas)

    gui.output_scrollable_frame.bind("<Configure>", lambda e: gui.output_canvas.configure(scrollregion=gui.output_canvas.bbox("all")))
    gui.output_canvas.create_window((0, 0), window=gui.output_scrollable_frame, anchor="nw")
    gui.output_canvas.configure(yscrollcommand=gui.output_scrollbar.set, xscrollcommand=gui.output_scrollbar_x.set)

    gui.output_canvas.pack(side="top", fill="both", expand=True)
    gui.output_scrollbar.pack(side="right", fill="y")
    gui.output_scrollbar_x.pack(side="bottom", fill="x")

    gui.output_canvas.bind_all("<MouseWheel>", gui.on_mouse_wheel)