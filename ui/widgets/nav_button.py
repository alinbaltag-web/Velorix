"""
VELORIX — ui/widgets/nav_button.py
====================================
_NavButton si _NavGroup — widget-uri reutilizabile pentru panoul de navigare
lateral (folosit in PageSetari si PageRapoarte).
"""

from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt

# Paleta Velorix
C_DARK   = "#0f2137"
C_BLUE   = "#1a4fa0"
C_ACCENT = "#2196F3"
C_LIGHT  = "#e8f0fe"
C_GREY   = "#64748b"
C_GREYBG = "#f7f9fc"


class NavButton(QPushButton):
    """Buton de navigare lateral cu highlight activ (border-left accent)."""

    def __init__(self, icon_char, text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_char}  {text}")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._apply_style(False)

    def _apply_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C_LIGHT};
                    color: {C_BLUE};
                    border: none;
                    border-left: 3px solid {C_ACCENT};
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 14px;
                    font-size: 13px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {C_GREY};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 14px;
                    font-size: 13px;
                    font-weight: 400;
                }}
                QPushButton:hover {{
                    background: {C_GREYBG};
                    color: {C_DARK};
                }}
            """)

    def setChecked(self, checked):
        super().setChecked(checked)
        self._apply_style(checked)


class NavGroup(QWidget):
    """Grup de butoane de navigare cu titlu de sectiune."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 4)
        lay.setSpacing(0)
        lbl = QLabel(f"  {title}")
        lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {C_GREY};"
            f"text-transform: uppercase; letter-spacing: 1px;"
            f"padding: 6px 0 4px 14px; background: transparent;"
        )
        lay.addWidget(lbl)
        self.layout = lay

    def add_button(self, btn):
        self.layout.addWidget(btn)


# Alias backward-compat pentru codul existent care foloseste _NavButton/_NavGroup
_NavButton = NavButton
_NavGroup  = NavGroup
