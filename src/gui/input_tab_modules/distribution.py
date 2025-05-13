import tkinter as tk
from tkinter import ttk
import numpy as np
from src.distribution_enum import Distribution
from .tooltip import Tooltip

def setup_distribution_controls(gui, right_frame, row_right):
    """Setup distribution-related controls for the Input tab."""
    # Use Peak Concentration (Right column)
    gui.use_peak_concentration_var = tk.BooleanVar(value=gui.config.get('use_peak_concentration'))
    use_peak_concentration_check = ttk.Checkbutton(right_frame, text="Use Peak-Concentration", variable=gui.use_peak_concentration_var, command=gui.toggle_peak_concentration)
    use_peak_concentration_check.grid(row=row_right, column=0, columnspan=3, padx=5, pady=5, sticky='w')
    Tooltip(use_peak_concentration_check, "Enable peak-concentration based thumbnail distribution.")
    row_right += 1

    # Thumbnail Peak Position (Right column)
    gui.peak_pos_label = ttk.Label(right_frame, text="Thumbnail Peak Position (0-1):")
    gui.peak_pos_label.grid(row=row_right, column=0, padx=5, pady=5, sticky='w')
    Tooltip(gui.peak_pos_label, "Position of the peak concentration within the video (0 to 1, default: 0.7).")
    gui.peak_pos_var = tk.DoubleVar(value=gui.config.get('thumbnail_peak_pos'))
    gui.peak_pos_scale = ttk.Scale(right_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, variable=gui.peak_pos_var, length=150, command=gui.update_distribution_graph)
    gui.peak_pos_scale.grid(row=row_right, column=1, padx=5, pady=5)
    Tooltip(gui.peak_pos_scale, "Adjust the peak position slider (0 to 1).")
    gui.peak_pos_entry = ttk.Entry(right_frame, textvariable=gui.peak_pos_var, width=10)
    gui.peak_pos_entry.grid(row=row_right, column=2, padx=5, pady=5)
    Tooltip(gui.peak_pos_entry, "Enter the peak position value (0 to 1).")
    gui.peak_pos_var.trace('w', lambda *args: validate_peak_pos(gui))
    row_right += 1

    # Thumbnail Concentration (Right column)
    gui.concentration_label = ttk.Label(right_frame, text="Thumbnail Concentration (0-1):")
    gui.concentration_label.grid(row=row_right, column=0, padx=5, pady=5, sticky='w')
    Tooltip(gui.concentration_label, "Concentration level around the peak (0 to 1, default: 0.2).")
    gui.concentration_var = tk.DoubleVar(value=gui.config.get('thumbnail_concentration'))
    gui.concentration_scale = ttk.Scale(right_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, variable=gui.concentration_var, length=150, command=gui.update_distribution_graph)
    gui.concentration_scale.grid(row=row_right, column=1, padx=5, pady=5)
    Tooltip(gui.concentration_scale, "Adjust the concentration level slider (0 to 1).")
    gui.concentration_entry = ttk.Entry(right_frame, textvariable=gui.concentration_var, width=10)
    gui.concentration_entry.grid(row=row_right, column=2, padx=5, pady=5)
    Tooltip(gui.concentration_entry, "Enter the concentration level value (0 to 1).")
    gui.concentration_var.trace('w', lambda *args: validate_concentration(gui))
    row_right += 1

    # Distribution Model (Right column)
    gui.distribution_label = ttk.Label(right_frame, text="Distribution Model:")
    gui.distribution_label.grid(row=row_right, column=0, padx=5, pady=5, sticky='w')
    Tooltip(gui.distribution_label, "Model for distributing thumbnails.")
    gui.distribution_var = tk.StringVar(value=gui.config.get('thumbnail_distribution').value)
    distribution_options = [d.value for d in Distribution]
    gui.distribution_menu = ttk.OptionMenu(right_frame, gui.distribution_var, gui.config.get('thumbnail_distribution').value, *distribution_options, command=gui.update_distribution_graph)
    gui.distribution_menu.grid(row=row_right, column=1, columnspan=2, padx=5, pady=5, sticky='w')
    Tooltip(gui.distribution_menu, "Select the distribution model for thumbnail placement.")
    row_right += 1

    # Canvas for distribution graph (Right column)
    gui.distribution_canvas = tk.Canvas(right_frame, width=200, height=100, bg='white')
    gui.distribution_canvas.grid(row=row_right, column=0, columnspan=3, padx=5, pady=5)
    Tooltip(gui.distribution_canvas, "Graphical representation of the thumbnail distribution.")
    row_right += 1

    return row_right

def toggle_peak_concentration(gui, *args):
    """Show or hide peak-concentration related options based on checkbox state."""
    if gui.use_peak_concentration_var.get():
        gui.peak_pos_label.grid()
        gui.peak_pos_scale.grid()
        gui.peak_pos_entry.grid()
        gui.concentration_label.grid()
        gui.concentration_scale.grid()
        gui.concentration_entry.grid()
        gui.distribution_label.grid()
        gui.distribution_menu.grid()
        gui.distribution_canvas.grid()
        # Reset to config values or defaults
        gui.peak_pos_var.set(gui.config.get('thumbnail_peak_pos'))
        gui.concentration_var.set(gui.config.get('thumbnail_concentration'))
        gui.distribution_var.set(gui.config.get('thumbnail_distribution').value)
    else:
        gui.peak_pos_label.grid_remove()
        gui.peak_pos_scale.grid_remove()
        gui.peak_pos_entry.grid_remove()
        gui.concentration_label.grid_remove()
        gui.concentration_scale.grid_remove()
        gui.concentration_entry.grid_remove()
        gui.distribution_label.grid_remove()
        gui.distribution_menu.grid_remove()
        gui.distribution_canvas.grid_remove()
    gui.update_distribution_graph()

def update_distribution_graph(gui, *args):
    """Update the distribution graph based on current settings."""
    gui.distribution_canvas.delete("all")
    if not gui.use_peak_concentration_var.get():
        return

    distribution = Distribution(gui.distribution_var.get())
    peak_pos = gui.peak_pos_var.get()
    concentration = gui.concentration_var.get()
    num_thumbs = gui.thumbs_var.get()

    width = gui.distribution_canvas.winfo_width()
    height = gui.distribution_canvas.winfo_height()

    if num_thumbs <= 0:
        return

    x = np.linspace(0, 1, 1000)
    if distribution == Distribution.NORMAL:
        sigma = concentration  # Adjust sigma to make the distribution wider
        y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(- (x - peak_pos) ** 2 / (2 * sigma ** 2))
    elif distribution == Distribution.TRIANGULAR:
        left = max(0, peak_pos - concentration)
        right = min(1, peak_pos + concentration)
        y = np.zeros_like(x)
        mask_left = (x >= left) & (x <= peak_pos)
        y[mask_left] = (x[mask_left] - left) / (peak_pos - left)
        mask_right = (x > peak_pos) & (x <= right)
        y[mask_right] = (right - x[mask_right]) / (right - peak_pos)
        y *= 2 / (right - left)  # Normalize to make area under curve = 1
    else:  # Uniform
        y = np.ones_like(x)

    y = np.maximum(y, 1e-10)
    y = y / np.max(y) * (height - 10)

    points = []
    for i in range(len(x)):
        canvas_x = int(x[i] * (width - 10)) + 5
        canvas_y = height - 5 - int(y[i])
        points.append(canvas_x)
        points.append(canvas_y)

    gui.distribution_canvas.create_line(points, fill="blue")

    if distribution == Distribution.NORMAL:
        sigma = concentration
        samples = np.random.normal(peak_pos, sigma, num_thumbs)
        samples = np.clip(samples, 0, 1)
    elif distribution == Distribution.TRIANGULAR:
        left = max(0, peak_pos - concentration)
        right = min(1, peak_pos + concentration)
        samples = np.random.triangular(left, peak_pos, right, num_thumbs)
    else:  # Uniform
        samples = np.random.uniform(0, 1, num_thumbs)

    for sample in samples:
        x_pos = int(sample * (width - 10)) + 5
        gui.distribution_canvas.create_line(x_pos, height - 5, x_pos, height - 15, fill="red")

def validate_peak_pos(gui, *args):
    """Validate and adjust peak_pos to stay within [0, 1]."""
    value = gui.peak_pos_var.get()
    if value < 0:
        gui.peak_pos_var.set(0.0)
    elif value > 1:
        gui.peak_pos_var.set(1.0)
    update_distribution_graph(gui)

def validate_concentration(gui, *args):
    """Validate and adjust concentration to stay within [0, 1]."""
    value = gui.concentration_var.get()
    if value < 0:
        gui.concentration_var.set(0.0)
    elif value > 1:
        gui.concentration_var.set(1.0)
    update_distribution_graph(gui)