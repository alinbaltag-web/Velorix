"""
VELORIX — Update Checker
Verifica daca exista o versiune noua disponibila pe Supabase
"""

import os
import threading
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont
import webbrowser

# ── Versiunea curenta a aplicatiei ──
VERSIUNE_CURENTA = "1.0"


class UpdateSignal(QObject):
    update_disponibil = pyqtSignal(str, str, str)  # versiune, url, note


class UpdateChecker:
    """Verifica update-uri in background la pornirea aplicatiei"""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.signal = UpdateSignal()
        self.signal.update_disponibil.connect(self._show_dialog)

    def check_async(self):
        """Porneste verificarea in background - nu blocheaza UI"""
        thread = threading.Thread(target=self._check, daemon=True)
        thread.start()

    def _check(self):
        try:
            from dotenv import load_dotenv
            load_dotenv()

            import psycopg2

            host     = os.getenv("DB_HOST", "")
            port     = os.getenv("DB_PORT", "5432")
            dbname   = os.getenv("DB_NAME", "postgres")
            user     = os.getenv("DB_USER", "")
            password = os.getenv("DB_PASSWORD", "")

            if not host or not user or not password:
                return  # Nu avem credentiale cloud

            conn = psycopg2.connect(
                host=host, port=port, dbname=dbname,
                user=user, password=password,
                connect_timeout=5,
                sslmode="require"
            )
            cur = conn.cursor()
            cur.execute("""
                SELECT versiune, url_download, note
                FROM app_version
                WHERE activ = TRUE
                ORDER BY id DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            conn.close()

            if not row:
                return

            versiune_server, url_download, note = row
            versiune_server = versiune_server.strip()

            if self._is_newer(versiune_server, VERSIUNE_CURENTA):
                self.signal.update_disponibil.emit(
                    versiune_server,
                    url_download or "",
                    note or ""
                )

        except Exception:
            pass  # Eroare silentioasa - nu deranjeaza utilizatorul

    def _is_newer(self, server, local):
        """Compara versiuni ex: '1.2' > '1.0'"""
        try:
            s = [int(x) for x in server.split(".")]
            l = [int(x) for x in local.split(".")]
            return s > l
        except Exception:
            return False

    def _show_dialog(self, versiune, url, note):
        dialog = UpdateDialog(versiune, url, note, self.parent)
        dialog.exec_()


class UpdateDialog(QDialog):
    """Dialog frumos pentru notificarea update-ului"""

    def __init__(self, versiune, url, note, parent=None):
        super().__init__(parent)
        self.url = url
        self.setWindowTitle("Versiune noua disponibila")
        self.setFixedWidth(420)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a4fa0, stop:1 #2196F3
                );
                border-radius: 0px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        lbl_icon = QLabel("🚀 Versiune noua disponibila!")
        lbl_icon.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: white;"
        )
        lbl_versiune = QLabel(f"Velorix {versiune}")
        lbl_versiune.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.85);"
        )
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(lbl_versiune)
        layout.addWidget(header)

        # ── Continut ──
        content = QFrame()
        content.setStyleSheet("QFrame { background: white; }")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(12)

        lbl_curent = QLabel(f"Versiunea instalata: {VERSIUNE_CURENTA}")
        lbl_curent.setStyleSheet("font-size: 11px; color: #6b7280;")
        content_layout.addWidget(lbl_curent)

        if note:
            lbl_note_title = QLabel("Noutati:")
            lbl_note_title.setStyleSheet(
                "font-size: 12px; font-weight: 600; color: #1e3a5f;"
            )
            content_layout.addWidget(lbl_note_title)

            lbl_note = QLabel(note)
            lbl_note.setStyleSheet("""
                font-size: 11px; color: #374151;
                background: #f8fafc;
                border-radius: 8px;
                padding: 10px;
                border: 1px solid #e5e7eb;
            """)
            lbl_note.setWordWrap(True)
            content_layout.addWidget(lbl_note)

        # ── Butoane ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_mai_tarziu = QPushButton("Mai tarziu")
        btn_mai_tarziu.setFixedHeight(36)
        btn_mai_tarziu.setStyleSheet("""
            QPushButton {
                background: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                font-size: 12px;
                color: #374151;
                padding: 0 16px;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        btn_mai_tarziu.clicked.connect(self.reject)

        btn_descarca = QPushButton("⬇️  Descarca acum")
        btn_descarca.setFixedHeight(36)
        btn_descarca.setStyleSheet("""
            QPushButton {
                background: #1a4fa0;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                color: white;
                padding: 0 20px;
            }
            QPushButton:hover { background: #2196F3; }
        """)
        btn_descarca.clicked.connect(self._descarca)

        btn_layout.addWidget(btn_mai_tarziu)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_descarca)
        content_layout.addLayout(btn_layout)

        layout.addWidget(content)

    def _descarca(self):
        if self.url:
            webbrowser.open(self.url)
        self.accept()