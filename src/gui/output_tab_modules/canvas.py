from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent

class CustomScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_speed_multiplier = 3 # スクロール速度の倍率

    def keyPressEvent(self, event: QKeyEvent):
        scroll_bar = self.verticalScrollBar()
        if not scroll_bar:
            super().keyPressEvent(event)
            return

        current_value = scroll_bar.value()
        step = scroll_bar.singleStep() * self.scroll_speed_multiplier # 通常のステップに倍率をかける

        if event.key() == Qt.Key.Key_Down:
            scroll_bar.setValue(current_value + step)
            event.accept()
        elif event.key() == Qt.Key.Key_Up:
            scroll_bar.setValue(current_value - step)
            event.accept()
        elif event.key() == Qt.Key.Key_PageDown:
            scroll_bar.setValue(current_value + scroll_bar.pageStep())
            event.accept()
        elif event.key() == Qt.Key.Key_PageUp:
            scroll_bar.setValue(current_value - scroll_bar.pageStep())
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            scroll_bar.setValue(scroll_bar.minimum())
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            scroll_bar.setValue(scroll_bar.maximum())
            event.accept()
        else:
            super().keyPressEvent(event) # 他のキーはデフォルト処理


def setup_output_canvas_pyqt(gui):
    """Setup the QScrollArea for the Output tab in PyQt6."""
    gui.output_scroll_area = CustomScrollArea() # カスタムスクロールエリアを使用
    gui.output_scroll_area.setWidgetResizable(True)
    gui.output_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    gui.output_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # スクロールエリアがキーイベントを受け取れるようにフォーカスを設定
    gui.output_scroll_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


    gui.output_scrollable_widget = QWidget()
    gui.output_scrollable_layout = QVBoxLayout(gui.output_scrollable_widget)
    gui.output_scrollable_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    gui.output_scroll_area.setWidget(gui.output_scrollable_widget)
    gui.output_frame_layout.addWidget(gui.output_scroll_area) # QVBoxLayoutに追加

    # Ctrl+Wheelでの横スクロールが必要な場合は、CustomScrollAreaのwheelEventをオーバーライド
    # gui.output_scroll_area.wheelEvent = lambda event: on_mouse_wheel_pyqt(gui, event) # on_mouse_wheel_pyqtは別途定義が必要