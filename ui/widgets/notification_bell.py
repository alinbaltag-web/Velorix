from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QApplication
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont
from notification_manager import NotificationManager


class NotificationPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedWidth(360)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: #1e3a5f;
                border-radius: 10px;
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)

        lbl = QLabel("🔔 Notificari")
        lbl.setStyleSheet("color: white; font-size: 13px; font-weight: 600;")
        header_layout.addWidget(lbl)
        header_layout.addStretch()

        self.btn_citeste_toate = QPushButton("Marcheaza toate citite")
        self.btn_citeste_toate.setStyleSheet("""
            QPushButton {
                color: #93c5fd;
                font-size: 11px;
                border: none;
                background: transparent;
            }
            QPushButton:hover { color: white; }
        """)
        self.btn_citeste_toate.clicked.connect(self.marcheaza_toate)
        header_layout.addWidget(self.btn_citeste_toate)
        layout.addWidget(header)

        # Scroll area pentru notificari
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setMaximumHeight(350)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.refresh()

    def refresh(self):
        # Curatam
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        notificari = NotificationManager.get_notificari_necitite()

        if not notificari:
            lbl = QLabel("✅  Nicio notificare noua")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #6b7280; font-size: 12px; padding: 20px;"
            )
            self.container_layout.addWidget(lbl)
        else:
            for notif_id, tip, mesaj, data_creare in notificari:
                row = self._make_row(notif_id, mesaj, data_creare)
                self.container_layout.addWidget(row)

        self.container_layout.addStretch()

    def _make_row(self, notif_id, mesaj, data_creare):
        row = QFrame()
        row.setStyleSheet("""
            QFrame {
                border-bottom: 1px solid #f1f5f9;
                background: #fffbeb;
            }
            QFrame:hover { background: #fef3c7; }
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 10, 10, 10)
        rl.setSpacing(8)

        icon = QLabel("⚠️")
        icon.setFixedWidth(22)
        rl.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        lbl_mesaj = QLabel(mesaj)
        lbl_mesaj.setWordWrap(True)
        lbl_mesaj.setStyleSheet("font-size: 11px; color: #1f2937;")
        text_layout.addWidget(lbl_mesaj)

        lbl_data = QLabel(data_creare[:16])
        lbl_data.setStyleSheet("font-size: 10px; color: #9ca3af;")
        text_layout.addWidget(lbl_data)

        rl.addLayout(text_layout)

        btn_ok = QPushButton("✓")
        btn_ok.setFixedSize(26, 26)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #d1fae5;
                color: #065f46;
                border-radius: 13px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background: #6ee7b7; }
        """)
        btn_ok.clicked.connect(lambda _, nid=notif_id: self.citeste_una(nid))
        rl.addWidget(btn_ok)

        return row

    def citeste_una(self, notif_id):
        NotificationManager.marcheaza_citita(notif_id)
        self.refresh()
        # Actualizam clopotul
        if self.parent():
            self.parent().refresh_count()

    def marcheaza_toate(self):
        NotificationManager.marcheaza_toate_citite()
        self.refresh()
        if self.parent():
            self.parent().refresh_count()


class NotificationBell(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 46)
        self.popup = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn = QPushButton("🔔")
        self.btn.setFixedSize(40, 40)
        self.btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                background: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover { background: #f1f5f9; }
        """)
        self.btn.clicked.connect(self.toggle_popup)
        layout.addWidget(self.btn)

        # Badge numar
        self.badge = QLabel("0")
        self.badge.setFixedSize(18, 18)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet("""
            QLabel {
                background: #ef4444;
                color: white;
                border-radius: 9px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.badge.setParent(self)
        self.badge.move(24, 2)
        self.badge.hide()

        self.refresh_count()

    def refresh_count(self):
        count = NotificationManager.count_necitite()
        if count > 0:
            self.badge.setText(str(count) if count < 100 else "99+")
            self.badge.show()
        else:
            self.badge.hide()

    def toggle_popup(self):
        if self.popup and self.popup.isVisible():
            self.popup.hide()
            return

        self.popup = NotificationPopup(self)
        # Pozitionam popup-ul sub clopot
        pos = self.mapToGlobal(QPoint(0, self.height()))
        # Ajustare sa nu iasa din ecran
        screen = QApplication.desktop().screenGeometry()
        if pos.x() + 360 > screen.width():
            pos.setX(screen.width() - 370)
        self.popup.move(pos)
        self.popup.show()