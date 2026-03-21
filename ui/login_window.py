import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QColor, QPainter, QLinearGradient, QFont, QPen, QBrush, QPainterPath
from PyQt5.QtSvg import QSvgRenderer
from database import get_connection, log_action, verify_password, hash_password, _is_bcrypt_hash
from ui.main_window import MainWindow
from ui.session_manager import SessionManager


# ─────────────────────────────────────────────
#  Rate Limiting — blocare dupa 5 incercari
# ─────────────────────────────────────────────
MAX_INCERCARI   = 5
BLOCARE_MINUTE  = 15

# Dictionar in memorie: { username: {"incercari": int, "blocat_pana": datetime | None} }
_login_attempts = {}


def _verifica_blocat(username: str) -> tuple[bool, int]:
    """
    Returneaza (blocat: bool, minute_ramase: int).
    Daca nu e blocat → (False, 0).
    """
    info = _login_attempts.get(username)
    if not info:
        return False, 0
    if info["blocat_pana"] and datetime.now() < info["blocat_pana"]:
        ramase = int((info["blocat_pana"] - datetime.now()).total_seconds() / 60) + 1
        return True, ramase
    return False, 0


def _inregistreaza_esec(username: str):
    """Incrementeaza contorul de esecuri. Blocheaza daca s-a atins limita."""
    if username not in _login_attempts:
        _login_attempts[username] = {"incercari": 0, "blocat_pana": None}

    _login_attempts[username]["incercari"] += 1

    if _login_attempts[username]["incercari"] >= MAX_INCERCARI:
        _login_attempts[username]["blocat_pana"] = datetime.now() + timedelta(minutes=BLOCARE_MINUTE)
        _login_attempts[username]["incercari"] = 0  # reset pentru urmatoarea perioada


def _reseteaza_incercari(username: str):
    """Reseteaza contorul dupa login reusit."""
    if username in _login_attempts:
        del _login_attempts[username]


# ─────────────────────────────────────────────
#  Widget stanga — branding VELORIX
# ─────────────────────────────────────────────
class BrandPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(580)
        import os
        svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "logo_velorix_dark.svg")

        if os.path.exists(svg_path):
            self._svg = QSvgRenderer(svg_path)
        else:
            self._svg = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Gradient fundal albastru inchis
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#0d1f3c"))
        grad.setColorAt(0.6, QColor("#112244"))
        grad.setColorAt(1.0, QColor("#0a1728"))
        painter.fillRect(self.rect(), QBrush(grad))

        # Linii diagonale decorative subtile
        painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
        step = 44
        for i in range(-self.height(), self.width() + self.height(), step):
            painter.drawLine(i, 0, i + self.height(), self.height())

        # Cerc decorativ mare (colt dreapta-jos)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(Qt.NoBrush)
        cx, cy, r = self.width() + 60, self.height() + 60, 280
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        painter.drawEllipse(cx - r + 40, cy - r + 40, (r - 40) * 2, (r - 40) * 2)

        # Logo SVG centrat
        from PyQt5.QtCore import QRectF
        if self._svg and self._svg.isValid():
            logo_w, logo_h = 460, 115
            logo_x = (self.width() - logo_w) // 2
            logo_y = (self.height() - logo_h) // 2
            self._svg.render(painter, QRectF(logo_x, logo_y, logo_w, logo_h))
        else:
            # Fallback text daca SVG nu e gasit
            font_title = QFont("Arial", 42, QFont.Black)
            font_title.setLetterSpacing(QFont.AbsoluteSpacing, 6)
            painter.setFont(font_title)
            painter.setPen(QColor(255, 255, 255, 240))
            painter.drawText(0, 370, self.width(), 60, Qt.AlignCenter, "VELORIX")


# ─────────────────────────────────────────────
#  Fereastra principala de login
# ─────────────────────────────────────────────
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VELORIX — Autentificare")
        self.setFixedSize(1500, 900)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # ── Shadow exterior ──
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        self._drag_pos = None
        self._build_ui()

        # Animatie de aparitie
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        screen_geo = self.screen().availableGeometry()
        cx = screen_geo.center().x() - self.width() // 2
        cy = screen_geo.center().y() - self.height() // 2

        self.setGeometry(cx, max(cy, 0), self.width(), self.height())
        self.anim.setStartValue(QRect(cx, max(cy + 20, 0), self.width(), self.height()))
        self.anim.setEndValue(QRect(cx, max(cy, 0), self.width(), self.height()))
        self.anim.start()

        self.logged_user = None
        self.logged_role = None

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel stanga ──
        self.brand = BrandPanel()
        root.addWidget(self.brand)

        # ── Panel dreapta ──
        right = QWidget()
        right.setObjectName("rightPanel")
        right.setStyleSheet("""
            QWidget#rightPanel {
                background: #ffffff;
                border-top-right-radius: 16px;
                border-bottom-right-radius: 16px;
            }
        """)
        root.addWidget(right)

        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(80, 0, 80, 0)
        rlay.setSpacing(0)

        # Buton inchidere (X)
        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #b0bec5;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { color: #ef4444; }
        """)
        btn_close.clicked.connect(self.close)
        close_row.addWidget(btn_close)
        rlay.addLayout(close_row)

        rlay.addStretch()

        # Titlu
        lbl_title = QLabel("Buna ziua! 👋")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1a2535;")
        rlay.addWidget(lbl_title)

        lbl_sub = QLabel("Autentifica-te pentru a continua")
        lbl_sub.setStyleSheet("font-size: 12px; color: #7a8ba0; margin-bottom: 28px;")
        rlay.addWidget(lbl_sub)

        rlay.addSpacing(24)

        # ── Label status blocare (ascuns initial) ──
        self.lbl_blocat = QLabel("")
        self.lbl_blocat.setAlignment(Qt.AlignCenter)
        self.lbl_blocat.setStyleSheet("""
            QLabel {
                background: #fef2f2;
                border: 1px solid #fca5a5;
                border-radius: 8px;
                color: #b91c1c;
                font-size: 11px;
                font-weight: 600;
                padding: 8px 12px;
            }
        """)
        self.lbl_blocat.setVisible(False)
        rlay.addWidget(self.lbl_blocat)
        rlay.addSpacing(8)

        # ── Username ──
        lbl_email = QLabel("UTILIZATOR")
        lbl_email.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: #7a8ba0;")
        rlay.addWidget(lbl_email)
        rlay.addSpacing(6)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("ex: admin")
        self.email_input.setFixedHeight(44)
        self.email_input.setStyleSheet(self._input_style())
        rlay.addWidget(self.email_input)

        rlay.addSpacing(16)

        # ── Parola ──
        lbl_pass = QLabel("PAROLA")
        lbl_pass.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: #7a8ba0;")
        rlay.addWidget(lbl_pass)
        rlay.addSpacing(6)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(8)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Introduceti parola")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(44)
        self.password_input.setStyleSheet(self._input_style())
        self.password_input.returnPressed.connect(self.handle_login)

        self.toggle_password_btn = QPushButton("👁")
        self.toggle_password_btn.setCheckable(True)
        self.toggle_password_btn.setFixedSize(44, 44)
        self.toggle_password_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_password_btn.setStyleSheet("""
            QPushButton {
                background: #f0f4f8;
                border: 1.5px solid #dce4ef;
                border-radius: 10px;
                font-size: 16px;
                color: #7a8ba0;
            }
            QPushButton:hover { background: #e2eaf4; }
            QPushButton:checked { background: #dbeafe; border-color: #1a73e8; }
        """)
        self.toggle_password_btn.clicked.connect(self.toggle_password)
        pass_row.addWidget(self.password_input)
        pass_row.addWidget(self.toggle_password_btn)
        rlay.addLayout(pass_row)

        # ── Label incercari ramase (ascuns initial) ──
        self.lbl_incercari = QLabel("")
        self.lbl_incercari.setStyleSheet(
            "font-size: 10px; color: #e67e22; font-weight: 600; margin-top: 4px;")
        self.lbl_incercari.setVisible(False)
        rlay.addWidget(self.lbl_incercari)

        rlay.addSpacing(28)

        # ── Buton login ──
        self.login_btn = QPushButton("Autentificare")
        self.login_btn.setFixedHeight(46)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1a73e8, stop:1 #0d5abf);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #2b82f5, stop:1 #1a6ad4);
            }
            QPushButton:pressed { background: #0d5abf; }
            QPushButton:disabled {
                background: #cbd5e1;
                color: #94a3b8;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        rlay.addWidget(self.login_btn)

        rlay.addStretch()

        # Footer
        footer = QLabel("VELORIX © 2026  ·  Toate drepturile rezervate")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("font-size: 10px; color: #c5cdd8; letter-spacing: 0.5px;")
        rlay.addWidget(footer)

    def _input_style(self):
        return """
            QLineEdit {
                background: #f0f4f8;
                border: 1.5px solid #dce4ef;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
                color: #1a2535;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
                background: #ffffff;
            }
            QLineEdit::placeholder { color: #b0bec5; }
        """

    # ── Drag fereastra (frameless) ──
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        """Rotunjim colturile ferestrei principale."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        painter.fillPath(path, QBrush(QColor("#0d1f3c")))

    # ── Toggle parola ──
    def toggle_password(self):
        if self.toggle_password_btn.isChecked():
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)

    # ── Autentificare ──
    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Eroare", "Completeaza toate campurile.")
            return

        # ── Verificare blocare ──
        blocat, minute_ramase = _verifica_blocat(email)
        if blocat:
            self.lbl_blocat.setText(
                f"🔒  Contul este blocat temporar din cauza mai multor incercari esuate.\n"
                f"Incearca din nou peste {minute_ramase} minut(e)."
            )
            self.lbl_blocat.setVisible(True)
            self.login_btn.setEnabled(False)
            self.lbl_incercari.setVisible(False)
            log_action(email, "Login blocat", f"Tentativa in perioada de blocare — {minute_ramase} min ramase")
            return

        # Deblocare daca perioada a expirat
        self.lbl_blocat.setVisible(False)
        self.login_btn.setEnabled(True)

        con = get_connection()
        cur = con.cursor()

        cur.execute(
            "SELECT username, role, password FROM users WHERE username=?",
            (email,)
        )
        row = cur.fetchone()
        result = (row[0], row[1]) if row and verify_password(password, row[2]) else None

        if result:
            # ── Login reusit ──
            _reseteaza_incercari(email)
            self.lbl_incercari.setVisible(False)
            self.lbl_blocat.setVisible(False)

            # Auto-migrare parola plain-text → bcrypt la primul login
            if row and not _is_bcrypt_hash(row[2]):
                cur.execute(
                    "UPDATE users SET password=? WHERE username=?",
                    (hash_password(password), email)
                )

            cur.execute(
                "UPDATE users SET last_login=datetime('now') WHERE username=?", (email,)
            )
            con.commit()
            con.close()

            log_action(email, "Autentificare", "Login reusit")

            self.logged_user = result[0]
            self.logged_role = result[1]

            SessionManager.login(self.logged_user, self.logged_role)

            from notification_manager import NotificationManager
            NotificationManager.genereaza_notificari()

            try:
                self.main = MainWindow(role=self.logged_role, email=self.logged_user)
                self.main.show()
                self.hide()
            except Exception as e:
                import traceback
                eroare = traceback.format_exc()
                with open("eroare_log.txt", "w", encoding="utf-8") as f:
                    f.write(eroare)
                QMessageBox.critical(
                    self, "Eroare",
                    f"Eroare la pornire:\n{e}\n\nDetalii in eroare_log.txt"
                )
        else:
            # ── Login esuat ──
            con.close()
            _inregistreaza_esec(email)

            # Log in audit
            info = _login_attempts.get(email, {})
            incercari = info.get("incercari", 0)
            blocat_acum = info.get("blocat_pana") is not None and datetime.now() < info.get("blocat_pana", datetime.min)

            if blocat_acum:
                log_action(email, "Login esuat — CONT BLOCAT",
                           f"5 incercari esuate consecutive — blocat {BLOCARE_MINUTE} minute")
                self.lbl_blocat.setText(
                    f"🔒  Prea multe incercari esuate. Contul este blocat {BLOCARE_MINUTE} minute."
                )
                self.lbl_blocat.setVisible(True)
                self.login_btn.setEnabled(False)
                self.lbl_incercari.setVisible(False)
            else:
                ramase = MAX_INCERCARI - incercari
                log_action(email, "Login esuat",
                           f"Tentativa {incercari}/{MAX_INCERCARI} — {ramase} incercari ramase")
                self.lbl_incercari.setText(
                    f"⚠  Parola incorecta. Mai ai {ramase} incercare(i) inainte de blocare."
                )
                self.lbl_incercari.setVisible(True)

            # Shake animation la eroare
            self._shake()

    def _shake(self):
        """Mica animatie de shake la login gresit."""
        geo = self.geometry()
        self.shake = QPropertyAnimation(self, b"geometry")
        self.shake.setDuration(300)
        self.shake.setLoopCount(1)
        self.shake.setKeyValueAt(0,    QRect(geo.x(),      geo.y(), geo.width(), geo.height()))
        self.shake.setKeyValueAt(0.15, QRect(geo.x() - 10, geo.y(), geo.width(), geo.height()))
        self.shake.setKeyValueAt(0.30, QRect(geo.x() + 10, geo.y(), geo.width(), geo.height()))
        self.shake.setKeyValueAt(0.50, QRect(geo.x() - 6,  geo.y(), geo.width(), geo.height()))
        self.shake.setKeyValueAt(0.70, QRect(geo.x() + 6,  geo.y(), geo.width(), geo.height()))
        self.shake.setKeyValueAt(1.0,  QRect(geo.x(),      geo.y(), geo.width(), geo.height()))
        self.shake.start()