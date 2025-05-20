from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QFrame
from PyQt6.QtCore import Qt

from .output_tab_modules.canvas import setup_output_canvas_pyqt

def setup_output_tab(gui):
    """Configure the Output tab for thumbnail display using PyQt6."""
    # gui.output_frame_layout is the QVBoxLayout for the output_tab QWidget

    # --- Canvas/Scroll Area (Main content) ---
    # setup_output_canvas_pyqt will add the scroll area to gui.output_frame_layout
    # selection_count_label は thumbnail_gui.py の setup_gui_layout で output_frame_layout に追加済み
    # なので、scroll_area はその下に追加される
    setup_output_canvas_pyqt(gui)

    # --- Separator Line (Optional) ---
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    gui.output_frame_layout.addWidget(line)

    # --- Action Buttons at the bottom (Horizontal Layout) ---
    action_buttons_widget = QWidget() # Container for horizontal button layout
    action_buttons_layout = QHBoxLayout(action_buttons_widget) # Horizontal layout for buttons
    action_buttons_layout.setContentsMargins(0, 5, 0, 5) # Add some vertical margin

    delete_selected_button = QPushButton("Delete Selected")
    delete_selected_button.clicked.connect(gui.delete_selected)
    delete_selected_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    action_buttons_layout.addWidget(delete_selected_button)

    delete_unselected_button = QPushButton("Delete Unselected")
    delete_unselected_button.clicked.connect(gui.delete_unselected)
    delete_unselected_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    action_buttons_layout.addWidget(delete_unselected_button)

    clear_selection_button = QPushButton("Clear All Selection")
    clear_selection_button.clicked.connect(gui.clear_all_selection)
    clear_selection_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    action_buttons_layout.addWidget(clear_selection_button)

    # Add stretch to push buttons to the center or left, or distribute them
    # action_buttons_layout.addStretch(1) # Pushes buttons to the left if not enough space

    # Add the widget containing the horizontal button layout to the main output tab layout
    gui.output_frame_layout.addWidget(action_buttons_widget)