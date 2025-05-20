from PyQt6.QtWidgets import QWidget, QFrame, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from pathlib import Path

from .input_tab_modules.controls import setup_input_controls_pyqt
from .input_tab_modules.crypto_manager import CryptoManager, setup_crypto_links_pyqt
from .input_tab_modules.distribution import setup_distribution_controls_pyqt
from .input_tab_modules.progress import setup_progress_controls_pyqt

def setup_input_tab(gui):
    """Configure the Input tab with controls and progress indicators for PyQt6."""
    # Clear existing widgets if any (though usually not needed if setup once)
    # for i in reversed(range(gui.input_frame.count())):
    #     gui.input_frame.itemAt(i).widget().setParent(None)

    # Main layout for the input tab (already a QVBoxLayout from thumbnail_gui.py)
    # input_tab_layout = gui.input_frame

    # Top part for controls (left and right frames)
    controls_area = QWidget()
    controls_layout = QHBoxLayout(controls_area)
    gui.input_frame.addWidget(controls_area) # Add to the main QVBoxLayout of the tab

    left_frame_widget = QWidget()
    gui.left_frame_layout = QVBoxLayout(left_frame_widget) # Store layout for access
    gui.left_frame_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    controls_layout.addWidget(left_frame_widget, 1) # Weight 1

    right_frame_widget = QWidget()
    gui.right_frame_layout = QVBoxLayout(right_frame_widget) # Store layout for access
    gui.right_frame_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    controls_layout.addWidget(right_frame_widget, 1) # Weight 1

    # Setup controls
    setup_input_controls_pyqt(gui, gui.left_frame_layout, gui.right_frame_layout)

    # Setup distribution controls (in right_frame_layout)
    setup_distribution_controls_pyqt(gui, gui.right_frame_layout)

    # Separator or spacer (optional)
    # line = QFrame()
    # line.setFrameShape(QFrame.Shape.HLine)
    # line.setFrameShadow(QFrame.Shadow.Sunken)
    # gui.input_frame.addWidget(line)

    # Bottom part for progress and crypto links
    progress_crypto_area = QWidget()
    progress_crypto_layout = QVBoxLayout(progress_crypto_area)
    gui.input_frame.addWidget(progress_crypto_area)

    # Progress controls
    setup_progress_controls_pyqt(gui, progress_crypto_layout)

    # Crypto links
    gui.crypto_manager = CryptoManager(find_contents_path())
    setup_crypto_links_pyqt(gui, progress_crypto_layout)

    # Make sure peak concentration UI reflects current state
    gui.toggle_peak_concentration()


def find_contents_path():
    """Find the 'contents' directory by traversing parent directories."""
    current_path = Path(__file__).parent
    # Assuming this script is in src/gui/, contents is at src/../contents/
    # So, project_root/contents/
    project_root = current_path.parent.parent
    contents_dir = project_root / "contents"
    if contents_dir.exists():
        return contents_dir

    # Fallback to original search if needed, though less likely with known structure
    current_path = Path(__file__).parent
    max_depth = 5
    for _ in range(max_depth):
        if (current_path / "contents").exists():
            return current_path / "contents"
        if current_path.parent == current_path: # Reached root
            break
        current_path = current_path.parent
    raise FileNotFoundError("Could not find 'contents' directory relative to project structure.")