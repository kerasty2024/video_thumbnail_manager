from PyQt6.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
                             QSizePolicy, QFrame, QLabel, QLineEdit, QSpinBox, QComboBox, QCheckBox, QSlider)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator

# GUIクラスの型ヒントのため (循環インポートを避けるためにTYPE_CHECKINGブロック内で使用)
import typing
if typing.TYPE_CHECKING:
    from .thumbnail_gui import VideoThumbnailGUI


class JumpWidget(QWidget):
    """Widget for jumping to a specific video by its display order or keyword."""
    jump_to_display_order_signal = pyqtSignal(int) # Signal emits display_order
    jump_to_keyword_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(5)

        # Jump to Display Order
        self.jump_label = QLabel("Jump (#):") # Corrected label
        main_layout.addWidget(self.jump_label)

        self.jump_input = QSpinBox()
        self.jump_input.setRange(1, 999999) # Increased max range to 999999
        self.jump_input.setToolTip("Enter the video's current display number to jump to.")
        self.jump_input.setFixedWidth(70) # Adjusted width for larger numbers
        main_layout.addWidget(self.jump_input)

        self.jump_button = QPushButton("Go")
        self.jump_button.setToolTip("Jump to the specified video display number.")
        self.jump_button.clicked.connect(self._emit_jump_display_order_signal)
        self.jump_button.setFixedWidth(40)
        main_layout.addWidget(self.jump_button)

        main_layout.addWidget(QLabel("|"))

        # Find by Keyword
        self.keyword_label = QLabel("Find:")
        main_layout.addWidget(self.keyword_label)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Keyword...")
        self.keyword_input.setToolTip("Enter a keyword to find in video names.")
        self.keyword_input.returnPressed.connect(self._emit_jump_keyword_signal)
        main_layout.addWidget(self.keyword_input)

        self.search_button = QPushButton("Find")
        self.search_button.setToolTip("Find the next video matching the keyword.")
        self.search_button.clicked.connect(self._emit_jump_keyword_signal)
        self.search_button.setFixedWidth(50)
        main_layout.addWidget(self.search_button)

    def _emit_jump_display_order_signal(self):
        try:
            video_number = self.jump_input.value()
            if video_number >= 1:
                self.jump_to_display_order_signal.emit(video_number) # Emits display_order
        except ValueError:
            pass

    def _emit_jump_keyword_signal(self):
        keyword = self.keyword_input.text().strip()
        if keyword:
            self.jump_to_keyword_signal.emit(keyword)

    def set_max_jump_value(self, max_val):
        # The range should accommodate the maximum possible display order.
        # If max_val can be very large, ensure QSpinBox range is sufficient.
        self.jump_input.setRange(1, max(1, max_val if max_val > 0 else 999999) )


    def set_enabled_controls(self, enabled: bool):
        self.jump_input.setEnabled(enabled)
        self.jump_button.setEnabled(enabled)
        self.keyword_input.setEnabled(enabled)
        self.search_button.setEnabled(enabled)


class SortWidget(QWidget):
    """Widget for sorting the video list."""
    sort_changed_signal = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)

        self.sort_label = QLabel("Sort by:")
        layout.addWidget(self.sort_label)

        self.sort_key_combo = QComboBox()
        self.sort_key_combo.addItems([
            "Original Order", "Name", "Size", "Duration", "Date Modified"
        ])
        self.sort_key_combo.setToolTip("Select sorting criteria.")
        self.sort_key_combo.currentTextChanged.connect(self._emit_sort_changed)
        layout.addWidget(self.sort_key_combo)

        self.sort_order_button = QPushButton("Asc")
        self.sort_order_button.setCheckable(True)
        self.sort_order_button.setChecked(True)
        self.sort_order_button.toggled.connect(self._toggle_sort_order_text)
        self.sort_order_button.setToolTip("Toggle sort order (Ascending/Descending).")
        self.sort_order_button.setFixedWidth(50)
        layout.addWidget(self.sort_order_button)

    def _toggle_sort_order_text(self, checked):
        if checked:
            self.sort_order_button.setText("Asc")
        else:
            self.sort_order_button.setText("Desc")
        self._emit_sort_changed()

    def _emit_sort_changed(self):
        sort_key = self.sort_key_combo.currentText()
        ascending = self.sort_order_button.isChecked()
        self.sort_changed_signal.emit(sort_key, ascending)

    def get_current_sort_options(self):
        sort_key = self.sort_key_combo.currentText()
        ascending = self.sort_order_button.isChecked()
        return sort_key, ascending

    def set_enabled_controls(self, enabled: bool):
        self.sort_key_combo.setEnabled(enabled)
        self.sort_order_button.setEnabled(enabled)

    def set_enabled(self, enabled: bool):
        self.set_enabled_controls(enabled)


class ScrollSpeedWidget(QWidget):
    """Widget for adjusting scroll speed."""
    speed_changed_signal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(3)

        self.label = QLabel("Scroll:")
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 20)
        self.slider.setValue(7)
        self.slider.setTickInterval(1)
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider.setFixedWidth(100)
        self.slider.valueChanged.connect(self.on_speed_changed)
        layout.addWidget(self.slider)

        self.speed_value_label = QLabel(f"{self.slider.value()}x")
        self.speed_value_label.setFixedWidth(30)
        layout.addWidget(self.speed_value_label)

    def on_speed_changed(self, value):
        self.speed_value_label.setText(f"{value}x")
        self.speed_changed_signal.emit(value)

    def get_current_speed(self):
        return self.slider.value()


def setup_output_tab(gui: 'VideoThumbnailGUI'):
    """Configure the Output tab for thumbnail display using PyQt6."""
    top_controls_container = QWidget()
    top_controls_container_layout = QVBoxLayout(top_controls_container)
    top_controls_container_layout.setContentsMargins(5, 2, 5, 2)
    top_controls_container_layout.setSpacing(3)

    controls_row_widget = QWidget()
    controls_row_layout = QHBoxLayout(controls_row_widget)
    controls_row_layout.setContentsMargins(0, 0, 0, 0)
    controls_row_layout.setSpacing(8)

    if not hasattr(gui, 'selection_count_label') or gui.selection_count_label is None:
        gui.selection_count_label = QLabel("0 of 0 selected")
    gui.selection_count_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    controls_row_layout.addWidget(gui.selection_count_label)

    gui.last_deleted_label = QLabel("")
    gui.last_deleted_label.setToolTip("Shows the display number of the last deleted video.") # Updated tooltip
    gui.last_deleted_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    controls_row_layout.addWidget(gui.last_deleted_label)

    controls_row_layout.addWidget(QLabel("|"))

    gui.sort_widget = SortWidget()
    gui.sort_widget.sort_changed_signal.connect(gui.sort_output_videos)
    controls_row_layout.addWidget(gui.sort_widget)

    controls_row_layout.addWidget(QLabel("|"))

    gui.jump_widget = JumpWidget()
    gui.jump_widget.jump_to_display_order_signal.connect(gui.jump_to_video_in_output_by_display_order)
    gui.jump_widget.jump_to_keyword_signal.connect(gui.jump_to_video_in_output_by_keyword)
    controls_row_layout.addWidget(gui.jump_widget)

    controls_row_layout.addStretch(1)

    gui.show_full_path_checkbox = QCheckBox("Full Path")
    gui.show_full_path_checkbox.setToolTip("Toggle between showing filename only or full path for videos.")
    gui.show_full_path_checkbox.setChecked(True)
    gui.show_full_path_checkbox.stateChanged.connect(gui.toggle_video_path_display_mode)
    controls_row_layout.addWidget(gui.show_full_path_checkbox)

    controls_row_layout.addWidget(QLabel("|"))

    gui.scroll_speed_widget = ScrollSpeedWidget()
    gui.scroll_speed_widget.speed_changed_signal.connect(gui.update_scroll_speed)
    controls_row_layout.addWidget(gui.scroll_speed_widget)

    top_controls_container_layout.addWidget(controls_row_widget)
    gui.output_frame_layout.addWidget(top_controls_container)

    from .output_tab_modules.canvas import setup_output_canvas_pyqt
    setup_output_canvas_pyqt(gui)

    if hasattr(gui, 'output_scroll_area') and gui.output_scroll_area and hasattr(gui.output_scroll_area, 'set_scroll_speed_multiplier'):
        gui.output_scroll_area.set_scroll_speed_multiplier(gui.scroll_speed_widget.get_current_speed())

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    gui.output_frame_layout.addWidget(line)

    action_buttons_widget = QWidget()
    action_buttons_layout = QHBoxLayout(action_buttons_widget)
    action_buttons_layout.setContentsMargins(0, 5, 0, 5)

    gui.delete_selected_button = QPushButton("Delete Selected")
    gui.delete_selected_button.clicked.connect(gui.delete_selected)
    gui.delete_selected_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    action_buttons_layout.addWidget(gui.delete_selected_button)

    gui.delete_unselected_button = QPushButton("Delete Unselected")
    gui.delete_unselected_button.clicked.connect(gui.delete_unselected)
    gui.delete_unselected_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    action_buttons_layout.addWidget(gui.delete_unselected_button)

    gui.clear_selection_button = QPushButton("Clear All Selection")
    gui.clear_selection_button.clicked.connect(gui.clear_all_selection)
    gui.clear_selection_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    action_buttons_layout.addWidget(gui.clear_selection_button)

    action_buttons_layout.addStretch(1)

    gui.output_frame_layout.addWidget(action_buttons_widget)