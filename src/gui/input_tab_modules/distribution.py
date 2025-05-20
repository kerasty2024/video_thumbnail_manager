# src/gui/input_tab_modules/distribution.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                             QSlider, QLineEdit, QComboBox, QFrame, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygonF, QFont, QFontMetrics
import numpy as np
from src.distribution_enum import Distribution
from loguru import logger

class DistributionGraphWidget(QWidget):
    def __init__(self, gui_ref, parent=None):
        super().__init__(parent)
        self.gui = gui_ref
        self.setMinimumSize(200, 100)
        self.setAutoFillBackground(True)
        self._font = QFont() # Default system font for any text if needed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().window().color()) # Clear background

        # Essential GUI elements check
        required_attrs = ['use_peak_concentration_var', 'distribution_var', 'peak_pos_var',
                          'concentration_var', 'thumbs_var']
        for attr in required_attrs:
            if not hasattr(self.gui, attr) or getattr(self.gui, attr) is None:
                # logger.debug(f"DistributionGraphWidget: GUI element '{attr}' not ready for painting.")
                return # Silently return if not ready, as this can be called often during init

        if not self.gui.use_peak_concentration_var.isChecked():
            # logger.debug("DistributionGraphWidget: Use Peak-Concentration is not checked.")
            return

        try:
            distribution_str = self.gui.distribution_var.currentText()
            if not distribution_str: # Can be empty during init
                return
            distribution = Distribution(distribution_str)
            peak_pos = self.gui.peak_pos_var.value()
            concentration = self.gui.concentration_var.value()
            num_thumbs = self.gui.thumbs_var.value()
        except ValueError as e: # Invalid enum string
            # logger.warning(f"DistributionGraphWidget: Invalid distribution string '{distribution_str}': {e}")
            return
        except Exception as e: # Catch any other attribute errors
            logger.error(f"DistributionGraphWidget: Error accessing GUI control values: {e}", exc_info=True)
            return

        width_px = self.width()
        height_px = self.height()
        padding = 10

        if num_thumbs <= 0:
            # logger.debug("DistributionGraphWidget: num_thumbs is <= 0.")
            return

        x_axis = np.linspace(0, 1, 100)
        y_values = np.zeros_like(x_axis)

        try:
            if distribution == Distribution.NORMAL:
                sigma = max(float(concentration), 1e-6)
                y_values = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(- (x_axis - float(peak_pos)) ** 2 / (2 * sigma ** 2))
            elif distribution == Distribution.TRIANGULAR:
                peak_pos_f = float(peak_pos)
                concentration_f = float(concentration)
                left = max(0, peak_pos_f - concentration_f)
                right = min(1, peak_pos_f + concentration_f)
                c = peak_pos_f
                if abs(right - left) < 1e-6:
                    y_values = np.zeros_like(x_axis)
                    center_idx = np.abs(x_axis - c).argmin()
                    if center_idx < len(y_values): y_values[center_idx] = 1.0
                else:
                    for i, x_val in enumerate(x_axis):
                        if left <= x_val <= c:
                            denominator = (right - left) * (c - left)
                            y_values[i] = 2 * (x_val - left) / denominator if abs(denominator) > 1e-6 else 0
                        elif c < x_val <= right:
                            denominator = (right - left) * (right - c)
                            y_values[i] = 2 * (right - x_val) / denominator if abs(denominator) > 1e-6 else 0
            elif distribution == Distribution.UNIFORM: # Should only be drawn if peak concentration is on
                y_values = np.ones_like(x_axis)
        except Exception as e:
            logger.error(f"Error during distribution calculation in paintEvent: {e}", exc_info=True)
            painter.setPen(QColor("red"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Graph Calc Error")
            return

        max_y_val = np.max(y_values) if len(y_values) > 0 else 0
        if max_y_val > 1e-9: # Slightly larger epsilon for float comparison
            y_values_normalized = y_values / max_y_val * (height_px - 2 * padding)
        else:
            y_values_normalized = np.zeros_like(y_values)

        poly = QPolygonF()
        for i in range(len(x_axis)):
            px = padding + x_axis[i] * (width_px - 2 * padding)
            py = height_px - padding - y_values_normalized[i] # Y is inverted in screen coords
            poly.append(QPointF(px, py))

        pen = QPen(QColor("blue"), 2)
        painter.setPen(pen)
        painter.drawPolyline(poly)

        # --- Sample points drawing (Re-enable this section) ---
        if num_thumbs > 0:
            try:
                # logger.debug(f"Drawing samples: dist={distribution}, peak={peak_pos}, conc={concentration}, num={num_thumbs}")
                if distribution == Distribution.NORMAL:
                    sigma = max(float(concentration), 1e-6)
                    samples = np.random.normal(float(peak_pos), sigma, num_thumbs)
                elif distribution == Distribution.TRIANGULAR:
                    peak_pos_f = float(peak_pos)
                    concentration_f = float(concentration)
                    left_s = max(0, peak_pos_f - concentration_f)
                    right_s = min(1, peak_pos_f + concentration_f)
                    c_s = peak_pos_f
                    if abs(right_s - left_s) < 1e-6: # Degenerate case for sampling
                        samples = np.full(num_thumbs, c_s)
                    else:
                        # Ensure mode is within [left, right] for triangular
                        mode_s = np.clip(c_s, left_s, right_s)
                        samples = np.random.triangular(left_s, mode_s, right_s, num_thumbs)
                else: # Uniform
                    samples = np.random.uniform(0, 1, num_thumbs)

                samples = np.clip(samples, 0, 1) # Clip all samples to [0,1]

                pen.setColor(QColor("red"))
                pen.setWidth(1)
                painter.setPen(pen)
                for sample in samples:
                    x_pos_screen = padding + sample * (width_px - 2 * padding)
                    painter.drawLine(int(x_pos_screen), height_px - padding,
                                     int(x_pos_screen), height_px - padding - 10) # Draw small vertical lines
            except Exception as e:
                logger.error(f"Error drawing sample points: {e}", exc_info=True)
        # --- End of sample points drawing ---

# --- setup_distribution_controls_pyqt (変更なし) ---
# ... (前回提示のままでOK) ...
def setup_distribution_controls_pyqt(gui, right_layout):
    gui.use_peak_concentration_var = QCheckBox("Use Peak-Concentration")
    # gui.use_peak_concentration_var.setChecked(gui.config.get('use_peak_concentration')) # 初期値はtoggle_peak_concentrationで設定
    gui.use_peak_concentration_var.setToolTip("Enable peak-concentration based thumbnail distribution.")
    gui.use_peak_concentration_var.stateChanged.connect(gui.toggle_peak_concentration)
    right_layout.addWidget(gui.use_peak_concentration_var)

    peak_pos_group = QWidget()
    peak_pos_layout = QHBoxLayout(peak_pos_group)
    gui.peak_pos_label = QLabel("Peak Position (0-1):")
    gui.peak_pos_label.setToolTip("Position of the peak concentration (0 to 1).")
    peak_pos_layout.addWidget(gui.peak_pos_label)
    gui.peak_pos_var = QDoubleSpinBox()
    gui.peak_pos_var.setRange(0.0, 1.0)
    gui.peak_pos_var.setSingleStep(0.01)
    # gui.peak_pos_var.setValue(gui.config.get('thumbnail_peak_pos')) # 初期値はtoggle_peak_concentrationで設定
    gui.peak_pos_var.valueChanged.connect(gui.update_distribution_graph)
    gui.peak_pos_var.setToolTip("Adjust or enter the peak position value (0 to 1).")
    peak_pos_layout.addWidget(gui.peak_pos_var)
    right_layout.addWidget(peak_pos_group)
    gui.peak_pos_entry = gui.peak_pos_var
    gui.peak_pos_scale = None

    concentration_group = QWidget()
    concentration_layout = QHBoxLayout(concentration_group)
    gui.concentration_label = QLabel("Concentration (0-1):")
    gui.concentration_label.setToolTip("Concentration level around the peak (0 to 1).")
    concentration_layout.addWidget(gui.concentration_label)
    gui.concentration_var = QDoubleSpinBox()
    gui.concentration_var.setRange(0.01, 1.0)
    gui.concentration_var.setSingleStep(0.01)
    # gui.concentration_var.setValue(gui.config.get('thumbnail_concentration')) # 初期値はtoggle_peak_concentrationで設定
    gui.concentration_var.valueChanged.connect(gui.update_distribution_graph)
    gui.concentration_var.setToolTip("Adjust or enter the concentration level (0 to 1).")
    concentration_layout.addWidget(gui.concentration_var)
    right_layout.addWidget(concentration_group)
    gui.concentration_entry = gui.concentration_var
    gui.concentration_scale = None

    dist_model_group = QWidget()
    dist_model_layout = QHBoxLayout(dist_model_group)
    gui.distribution_label = QLabel("Distribution Model:")
    gui.distribution_label.setToolTip("Model for distributing thumbnails.")
    dist_model_layout.addWidget(gui.distribution_label)
    gui.distribution_var = QComboBox()
    distribution_options = [d.value for d in Distribution]
    gui.distribution_var.addItems(distribution_options)
    # gui.distribution_var.setCurrentText(gui.config.get('thumbnail_distribution').value) # 初期値はtoggle_peak_concentrationで設定
    gui.distribution_var.currentTextChanged.connect(gui.update_distribution_graph)
    gui.distribution_var.setToolTip("Select the distribution model for thumbnail placement.")
    dist_model_layout.addWidget(gui.distribution_var)
    dist_model_layout.addStretch(1)
    right_layout.addWidget(dist_model_group)
    gui.distribution_menu = gui.distribution_var

    gui.distribution_canvas_widget = DistributionGraphWidget(gui)
    gui.distribution_canvas_widget.setToolTip("Graphical representation of the thumbnail distribution.")
    right_layout.addWidget(gui.distribution_canvas_widget)
    right_layout.addStretch(1)

# --- toggle_peak_concentration_pyqt (変更なし) ---
# ... (前回提示のままでOK) ...
def toggle_peak_concentration_pyqt(gui):
    required_attrs_checkbox = ['use_peak_concentration_var']
    required_attrs_controls = ['peak_pos_label', 'peak_pos_var',
                               'concentration_label', 'concentration_var', 'distribution_label',
                               'distribution_var', 'distribution_canvas_widget']

    if not all(hasattr(gui, attr) and getattr(gui, attr) is not None for attr in required_attrs_checkbox):
        logger.warning("toggle_peak_concentration_pyqt: Checkbox 'use_peak_concentration_var' not initialized.")
        return

    is_checked = gui.use_peak_concentration_var.isChecked()

    if is_checked:
        if hasattr(gui, 'peak_pos_var') and gui.peak_pos_var:
            gui.peak_pos_var.setValue(gui.config.get('thumbnail_peak_pos'))
        if hasattr(gui, 'concentration_var') and gui.concentration_var:
            gui.concentration_var.setValue(gui.config.get('thumbnail_concentration'))
        if hasattr(gui, 'distribution_var') and gui.distribution_var:
            gui.distribution_var.setCurrentText(gui.config.get('thumbnail_distribution').value)
    else:
        pass

    for attr in required_attrs_controls:
        if hasattr(gui, attr) and getattr(gui, attr) is not None:
            getattr(gui, attr).setVisible(is_checked)
        else:
            logger.warning(f"toggle_peak_concentration_pyqt: Control widget '{attr}' not initialized. Cannot set visibility.")

    gui.update_distribution_graph()

# --- update_distribution_graph_pyqt (変更なし) ---
# ... (前回提示のままでOK) ...
def update_distribution_graph_pyqt(gui):
    if hasattr(gui, 'distribution_canvas_widget') and gui.distribution_canvas_widget:
        gui.distribution_canvas_widget.update()