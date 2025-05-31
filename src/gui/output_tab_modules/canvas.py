from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent

class CustomScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scroll_speed_multiplier = 3 # Default scroll speed multiplier

    def set_scroll_speed_multiplier(self, multiplier: int):
        self._scroll_speed_multiplier = max(1, multiplier) # Ensure multiplier is at least 1

    def get_scroll_speed_multiplier(self) -> int:
        return self._scroll_speed_multiplier

    def keyPressEvent(self, event: QKeyEvent):
        scroll_bar = self.verticalScrollBar()
        if not scroll_bar:
            super().keyPressEvent(event)
            return

        # For Up/Down arrow keys, use the singleStep adjusted by multiplier
        # For PageUp/PageDown, use pageStep (multiplier usually not applied here by default, but could be)

        single_step_val = scroll_bar.singleStep()
        page_step_val = scroll_bar.pageStep()

        # Effective step for arrow keys
        arrow_key_step = single_step_val * self._scroll_speed_multiplier

        current_value = scroll_bar.value()

        if event.key() == Qt.Key.Key_Down:
            scroll_bar.setValue(current_value + arrow_key_step)
            event.accept()
        elif event.key() == Qt.Key.Key_Up:
            scroll_bar.setValue(current_value - arrow_key_step)
            event.accept()
        elif event.key() == Qt.Key.Key_PageDown:
            scroll_bar.setValue(current_value + page_step_val) # Standard PageDown
            event.accept()
        elif event.key() == Qt.Key.Key_PageUp:
            scroll_bar.setValue(current_value - page_step_val) # Standard PageUp
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            scroll_bar.setValue(scroll_bar.minimum())
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            scroll_bar.setValue(scroll_bar.maximum())
            event.accept()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        # Apply multiplier to wheel events as well
        if not (event.modifiers() == Qt.KeyboardModifier.ControlModifier or \
                event.modifiers() == Qt.KeyboardModifier.ShiftModifier) : # No Ctrl/Shift for vertical scroll

            # Default wheel delta is usually 120. A single step is often around 15-20.
            # We want our multiplier to affect the "number of lines" scrolled.
            # QScrollBar.singleStep() is roughly one line.

            num_degrees = event.angleDelta().y() / 8
            num_steps = num_degrees / 15 # Standard steps per wheel notch

            scroll_amount = int(num_steps * self.verticalScrollBar().singleStep() * self._scroll_speed_multiplier)

            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - scroll_amount)
            event.accept()
        else:
            # Let parent handle Ctrl+Wheel (often horizontal scroll) or Shift+Wheel
            super().wheelEvent(event)


def setup_output_canvas_pyqt(gui):
    """Setup the QScrollArea for the Output tab in PyQt6."""
    gui.output_scroll_area = CustomScrollArea()
    gui.output_scroll_area.setWidgetResizable(True)
    gui.output_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    gui.output_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    gui.output_scroll_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


    gui.output_scrollable_widget = QWidget()
    gui.output_scrollable_layout = QVBoxLayout(gui.output_scrollable_widget)
    gui.output_scrollable_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    gui.output_scroll_area.setWidget(gui.output_scrollable_widget)
    gui.output_frame_layout.addWidget(gui.output_scroll_area)