from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer

_STYLES = {
    "success": "background-color: #10b981; color: white;",
    "warning": "background-color: #f59e0b; color: white;",
    "error":   "background-color: #ef4444; color: white;",
    "info":    "background-color: rgba(50, 50, 50, 200); color: white;",
}

def show_toast(parent, text, kind="info"):
    bg = _STYLES.get(kind, _STYLES["info"])
    toast = QLabel(text, parent)
    toast.setStyleSheet(f"""
        {bg}
        padding: 10px 20px;
        border-radius: 6px;
        font-size: 12pt;
    """)
    toast.setWindowFlags(Qt.ToolTip)
    toast.adjustSize()

    x = parent.width() // 2 - toast.width() // 2
    y = parent.height() - 80
    toast.move(x, y)

    toast.show()
    QTimer.singleShot(2500, toast.close)
