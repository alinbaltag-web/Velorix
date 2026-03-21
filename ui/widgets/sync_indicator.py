"""
VELORIX — Sync Indicator Widget
================================
Indicator vizual la baza sidebar-ului — status sincronizare cloud.
Design: complet transparent, integrat in sidebar-ul dark.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QMetaObject, Q_ARG


class SyncIndicator(QWidget):
    sync_requested = pyqtSignal()
    # Signal intern folosit pentru update thread-safe din background threads
    _status_changed = pyqtSignal(str, object)

    def __init__(self, parent=None, sync_manager=None):
        super().__init__(parent)
        self.sync_manager = sync_manager
        self._setup_ui()
        self._set_status("idle")

        # Conectam signal-ul intern la slot — dispatch automat pe main thread
        self._status_changed.connect(self._set_status)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(10_000)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(7)

        # Punct colorat de status
        self.lbl_dot = QLabel("●")
        self.lbl_dot.setFixedWidth(12)
        self.lbl_dot.setStyleSheet("font-size: 8px; color: #64748b; background: transparent;")

        # Text status
        self.lbl_text = QLabel("Local")
        self.lbl_text.setStyleSheet(
            "font-size: 10px; color: #64748b; background: transparent;"
            "font-family: 'Segoe UI';"
        )

        # Buton sync discret
        self.btn_sync = QPushButton("↻")
        self.btn_sync.setFixedSize(16, 16)
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.setToolTip("Sincronizeaza acum")
        self.btn_sync.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 12px;
                color: #4b5563;
                padding: 0;
            }
            QPushButton:hover { color: #60a5fa; }
        """)
        self.btn_sync.clicked.connect(self._on_sync_clicked)

        layout.addWidget(self.lbl_dot)
        layout.addWidget(self.lbl_text, stretch=1)
        layout.addWidget(self.btn_sync)

        # Complet transparent — preia culoarea sidebar-ului
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("SyncIndicator { background: transparent; border: none; }")
        self.setFixedHeight(28)

    def update_status(self, status, extra=None):
        # Aceasta metoda poate fi apelata din orice thread.
        # Emiterea unui signal cu Qt.AutoConnection este thread-safe
        # si dispatchez automat pe main thread (QueuedConnection cross-thread).
        self._status_changed.emit(status, extra)

    def _set_status(self, status, extra=None):
        configs = {
            "synced":  ("●", "Sincronizat",              "#34d399"),
            "syncing": ("●", "Se sincronizeaza...",       "#60a5fa"),
            "pending": ("●", f"{extra or '?'} asteptare", "#fbbf24"),
            "offline": ("●", "Offline",                   "#f87171"),
            "error":   ("●", "Eroare sync",               "#f87171"),
            "idle":    ("●", "Local",                     "#4b5563"),
        }
        dot, text, color = configs.get(status, ("●", "Local", "#4b5563"))
        self.lbl_dot.setText(dot)
        self.lbl_dot.setStyleSheet(
            f"font-size: 8px; color: {color}; background: transparent;"
        )
        self.lbl_text.setText(text)
        self.lbl_text.setStyleSheet(
            f"font-size: 10px; color: {color}; background: transparent;"
            f"font-family: 'Segoe UI';"
        )

    def _refresh(self):
        if not self.sync_manager:
            return
        try:
            from sync_manager import get_pending_count, _is_cloud_enabled
            if not _is_cloud_enabled():
                self._set_status("idle")
                return
            pending = get_pending_count()
            if self.sync_manager.status == "offline":
                self._set_status("offline")
            elif self.sync_manager.status == "syncing":
                self._set_status("syncing")
            elif pending > 0:
                self._set_status("pending", pending)
            else:
                self._set_status("synced")
        except Exception:
            pass

    def _on_sync_clicked(self):
        if self.sync_manager:
            self._set_status("syncing")
            self.sync_manager.sync_now()