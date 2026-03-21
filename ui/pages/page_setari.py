from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QDialogButtonBox, QCheckBox, QSpinBox,
    QFrame, QGroupBox, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt
import re
_CUI_RE = re.compile(r"^(RO)?[0-9]{2,10}$", re.IGNORECASE)
from database import get_connection, log_action, get_permisiuni, hash_password, verify_password
from ui.crypto_utils import encrypt, decrypt
from ui.utils_toast import show_toast
from ui.session_manager import SessionManager
from backup_manager import BackupManager


# ── Paleta Velorix ──────────────────────────────────────────
C_DARK    = "#0f2137"
C_BLUE    = "#1a4fa0"
C_ACCENT  = "#2196F3"
C_LIGHT   = "#e8f0fe"
C_BORDER  = "#c5d5ea"
C_GREY    = "#64748b"
C_GREYBG  = "#f7f9fc"
C_SECBG   = "#eef3fb"
C_WHITE   = "#ffffff"


def _separator():
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet(f"color: {C_BORDER}; background: {C_BORDER}; border: none; max-height: 1px;")
    return sep


def _section_title(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: 13px; font-weight: 700; color: {C_BLUE};"
        f"padding: 6px 0 2px 0; background: transparent;"
    )
    return lbl


from ui.widgets.nav_button import NavButton as _NavButton, NavGroup as _NavGroup


class PageSetari(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ════════════════════════════════════════════
        # PANOU STANG — navigare verticala
        # ════════════════════════════════════════════
        self._nav_panel = QFrame()
        self._nav_panel.setFixedWidth(210)
        self._nav_panel.setObjectName("settingsNav")
        self._nav_panel.setStyleSheet(f"""
            QFrame#settingsNav {{
                background: {C_WHITE};
                border-right: 1px solid {C_BORDER};
            }}
        """)

        nav_layout = QVBoxLayout(self._nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        nav_header = QLabel("  Setari")
        nav_header.setFixedHeight(56)
        nav_header.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {C_DARK};"
            f"background: {C_WHITE}; padding-left: 16px;"
            f"border-bottom: 1px solid {C_BORDER};"
        )
        nav_layout.addWidget(nav_header)

        # ── Grup: Aplicatie ──
        self._grp_app = _NavGroup("Aplicatie")
        self.nav_firma   = _NavButton("🏢", "Date firma")
        self.nav_lang    = _NavButton("🌐", "Limba")
        self.nav_prefs   = _NavButton("⚙️", "Preferinte")
        self._grp_app.add_button(self.nav_firma)
        self._grp_app.add_button(self.nav_lang)
        self._grp_app.add_button(self.nav_prefs)
        nav_layout.addWidget(self._grp_app)
        nav_layout.addWidget(_separator())

        # ── Grup: Comunicare ──
        self._grp_comm = _NavGroup("Comunicare")
        self.nav_email    = _NavButton("📧", "Notificari")
        self.nav_efactura = _NavButton("🧾", "E-Factura")
        self._grp_comm.add_button(self.nav_email)
        self._grp_comm.add_button(self.nav_efactura)
        nav_layout.addWidget(self._grp_comm)
        nav_layout.addWidget(_separator())

        # ── Grup: Cont & Acces ──
        self._grp_access = _NavGroup("Cont & Acces")
        self.nav_cont    = _NavButton("👤", "Contul meu")
        self.nav_users   = _NavButton("👥", "Utilizatori")
        self._grp_access.add_button(self.nav_cont)
        self._grp_access.add_button(self.nav_users)
        nav_layout.addWidget(self._grp_access)
        nav_layout.addWidget(_separator())

        # ── Grup: Sistem ──
        self._grp_sys = _NavGroup("Sistem")
        self.nav_audit  = _NavButton("📋", "Jurnal activitate")
        self.nav_backup = _NavButton("💾", "Backup")
        self.nav_cloud  = _NavButton("☁️", "Cloud Sync")
        self._grp_sys.add_button(self.nav_audit)
        self._grp_sys.add_button(self.nav_backup)
        self._grp_sys.add_button(self.nav_cloud)
        nav_layout.addWidget(self._grp_sys)

        nav_layout.addStretch()
        root.addWidget(self._nav_panel)

        # ════════════════════════════════════════════
        # PANOU DREPT — continut pagini (stacked)
        # ════════════════════════════════════════════
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {C_GREYBG};")
        root.addWidget(self._stack, stretch=1)

        self._nav_buttons = [
            self.nav_firma, self.nav_lang, self.nav_prefs,
            self.nav_email, self.nav_efactura,
            self.nav_cont, self.nav_users,
            self.nav_audit, self.nav_backup, self.nav_cloud,
        ]

        # ── Construire pagini ──
        self._page_firma    = self._build_firma()
        self._page_lang     = self._build_lang()
        self._page_prefs    = self._build_prefs()
        self._page_email    = self._build_email()
        self._page_efactura = self._build_efactura()
        self._page_cont     = self._build_cont()
        self._page_users    = self._build_users()
        self._page_audit    = self._build_audit()
        self._page_backup   = self._build_backup()
        self._page_cloud    = self._build_cloud()

        for page in [
            self._page_firma, self._page_lang, self._page_prefs,
            self._page_email, self._page_efactura,
            self._page_cont, self._page_users,
            self._page_audit, self._page_backup, self._page_cloud,
        ]:
            self._stack.addWidget(page)

        pairs = zip(self._nav_buttons, [
            self._page_firma, self._page_lang, self._page_prefs,
            self._page_email, self._page_efactura,
            self._page_cont, self._page_users,
            self._page_audit, self._page_backup, self._page_cloud,
        ])
        for btn, page in pairs:
            btn.clicked.connect(self._make_nav_handler(btn, page))

        # ── Ascunde sectiuni pentru non-admin ──
        if self.parent.role != "administrator":
            for w in [self._grp_app, self._grp_comm, self._grp_sys, self.nav_users]:
                w.hide()
            for i in range(nav_layout.count()):
                item = nav_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QFrame):
                    item.widget().hide()

        # ── Activare implicita ──
        if self.parent.role == "administrator":
            self._activate_nav(self.nav_firma, self._page_firma)
        else:
            self._activate_nav(self.nav_cont, self._page_cont)

        # ── Incarcare date ──
        self.load_data()
        self.load_language()
        self.load_tva()
        self.load_tarif()
        self.load_email_settings()
        self.load_wa_settings()
        self.load_sms_settings()
        self.load_users()
        self.load_permisiuni()
        self.load_backup_list()
        self.load_efactura_settings()
        self.apply_language()
        self._apply_button_styles()

    # ─────────────────────────────────────────────────────────
    # STILURI BUTOANE
    # ─────────────────────────────────────────────────────────
    def _apply_button_styles(self):
        _primary = f"""
            QPushButton {{
                background: {C_BLUE}; color: white; border: none;
                border-radius: 6px; font-size: 13px; font-weight: 600;
                padding: 6px 20px; min-height: 34px;
            }}
            QPushButton:hover {{ background: {C_ACCENT}; }}
            QPushButton:pressed {{ background: {C_DARK}; }}
            QPushButton:disabled {{ background: {C_BORDER}; color: {C_GREY}; }}
        """
        _danger = f"""
            QPushButton {{
                background: #dc2626; color: white; border: none;
                border-radius: 6px; font-size: 13px; font-weight: 600;
                padding: 6px 20px; min-height: 34px;
            }}
            QPushButton:hover {{ background: #ef4444; }}
            QPushButton:pressed {{ background: #991b1b; }}
        """
        _secondary = f"""
            QPushButton {{
                background: {C_LIGHT}; color: {C_BLUE};
                border: 1px solid {C_BORDER}; border-radius: 6px;
                font-size: 13px; padding: 6px 16px; min-height: 34px;
            }}
            QPushButton:hover {{ background: {C_BORDER}; }}
        """
        primary_btns = [
            self.btn_save, self.btn_save_lang, self.btn_save_tva,
            self.btn_save_tarif, self.btn_save_email, self.btn_change_pass,
            self.btn_add_user, self.btn_save_permisiuni, self.filter_btn,
            self.btn_backup_manual, self.btn_sync_now, self.btn_ef_save,
            self.btn_save_wa, self.btn_save_sms,
        ]
        danger_btns  = [self.btn_logout, self.btn_restaureaza, self.btn_restore_cloud]
        secondary_btns = [self.btn_test_email, self.btn_ef_test]

        for b in primary_btns:   b.setStyleSheet(_primary)
        for b in danger_btns:    b.setStyleSheet(_danger)
        for b in secondary_btns: b.setStyleSheet(_secondary)

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────
    def _scrolled(self, inner: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setWidget(inner)
        return scroll

    def _content_widget(self):
        w = QWidget()
        w.setStyleSheet(f"background: {C_GREYBG};")
        return w

    def _page_header(self, icon, title, subtitle):
        w = QWidget(); w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 4); lay.setSpacing(2)
        t = QLabel(f"{icon}  {title}")
        t.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C_DARK}; background: transparent;")
        s = QLabel(subtitle)
        s.setStyleSheet(f"font-size: 12px; color: {C_GREY}; background: transparent;")
        lay.addWidget(t); lay.addWidget(s)
        return w

    # ─────────────────────────────────────────────────────────
    # NAVIGARE
    # ─────────────────────────────────────────────────────────
    def _make_nav_handler(self, btn, page):
        return lambda: self._activate_nav(btn, page)

    def _activate_nav(self, active_btn, page):
        for b in self._nav_buttons:
            b.setChecked(b is active_btn)
        self._stack.setCurrentWidget(page)
        if page is self._page_audit:
            self.load_audit()

    # ─────────────────────────────────────────────────────────
    # PAGINA: DATE FIRMA
    # ─────────────────────────────────────────────────────────
    def _build_firma(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)

        lay.addWidget(self._page_header("🏢", "Date firma",
            "Informatii despre service — apar pe documente si PDF-uri."))
        lay.addWidget(_separator())

        self.f_nume    = QLineEdit(); self.f_nume.setPlaceholderText("Nume firma");         self.f_nume.setFixedWidth(320)
        self.f_cui     = QLineEdit(); self.f_cui.setPlaceholderText("CUI");                  self.f_cui.setFixedWidth(200)
        self.f_reg_com = QLineEdit(); self.f_reg_com.setPlaceholderText("ex: J40/1234/2020"); self.f_reg_com.setFixedWidth(200)
        self.f_adresa  = QLineEdit(); self.f_adresa.setPlaceholderText("Sediul social")
        self.f_cont    = QLineEdit(); self.f_cont.setPlaceholderText("ex: RO49AAAA1B31007593840000"); self.f_cont.setFixedWidth(360)
        self.f_tel     = QLineEdit(); self.f_tel.setPlaceholderText("Telefon");              self.f_tel.setFixedWidth(200)

        # Randul CUI + Nr. Reg. Comertului — side by side
        cui_row = QHBoxLayout(); cui_row.setSpacing(16)
        cui_row.addWidget(self.f_cui)
        cui_row.addWidget(QLabel("Nr. Reg. Comertului:"))
        cui_row.addWidget(self.f_reg_com)
        cui_row.addStretch()

        form = QFormLayout(); form.setSpacing(12); form.setLabelAlignment(Qt.AlignRight)
        form.addRow("Nume firma:", self.f_nume)
        form.addRow("CUI:", cui_row)
        form.addRow("Sediul social:", self.f_adresa)
        form.addRow("Cont bancar:", self.f_cont)
        form.addRow("Telefon:", self.f_tel)
        lay.addLayout(form)



        self.btn_save = QPushButton("Salveaza datele")
        self.btn_save.setFixedHeight(38); self.btn_save.setFixedWidth(180)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_data)
        lay.addWidget(self.btn_save)
        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: LIMBA
    # ─────────────────────────────────────────────────────────
    def _build_lang(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)

        lay.addWidget(self._page_header("🌐", "Limba aplicatie",
            "Schimba limba interfetei pentru toti utilizatorii."))
        lay.addWidget(_separator())

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["Romana", "Engleza"])
        self.cmb_lang.setFixedWidth(220)

        form = QFormLayout(); form.setSpacing(12); form.setLabelAlignment(Qt.AlignRight)
        form.addRow("Limba interfata:", self.cmb_lang)
        lay.addLayout(form)

        self.btn_save_lang = QPushButton("💾 Salveaza limba")
        self.btn_save_lang.setFixedWidth(200)
        self.btn_save_lang.clicked.connect(self.save_language)
        lay.addWidget(self.btn_save_lang)
        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: PREFERINTE
    # ─────────────────────────────────────────────────────────
    def _build_prefs(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)

        lay.addWidget(self._page_header("⚙️", "Preferinte",
            "TVA implicit si tarif ora manopera pentru devize si facturi."))
        lay.addWidget(_separator())

        lay.addWidget(_section_title("Taxe"))
        self.lbl_tva = QLabel("TVA (%)")
        self.txt_tva = QLineEdit(); self.txt_tva.setPlaceholderText("ex: 21"); self.txt_tva.setFixedWidth(120)
        self.btn_save_tva = QPushButton("💾 Salveaza TVA")
        self.btn_save_tva.setFixedWidth(160)
        self.btn_save_tva.clicked.connect(self.save_tva)

        form1 = QFormLayout(); form1.setSpacing(12); form1.setLabelAlignment(Qt.AlignRight)
        form1.addRow("TVA (%):", self.txt_tva)
        lay.addLayout(form1)
        lay.addWidget(self.btn_save_tva)

        lay.addSpacing(12)
        lay.addWidget(_separator())
        lay.addWidget(_section_title("Tarif manopera"))

        self.lbl_tarif = QLabel("Tarif ora manopera (RON)")
        self.txt_tarif = QLineEdit(); self.txt_tarif.setPlaceholderText("ex: 150"); self.txt_tarif.setFixedWidth(120)
        self.btn_save_tarif = QPushButton("💾 Salveaza tarif")
        self.btn_save_tarif.setFixedWidth(160)
        self.btn_save_tarif.clicked.connect(self.save_tarif)

        form2 = QFormLayout(); form2.setSpacing(12); form2.setLabelAlignment(Qt.AlignRight)
        form2.addRow("Tarif (RON/h):", self.txt_tarif)
        lay.addLayout(form2)
        lay.addWidget(self.btn_save_tarif)
        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: EMAIL & NOTIFICARI
    # ─────────────────────────────────────────────────────────
    def _build_email(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(14)

        lay.addWidget(self._page_header("📧", "Email & Notificari",
            "Configurare SMTP, WhatsApp si SMS pentru notificari automate."))
        lay.addWidget(_separator())

        # ── Notificari ON/OFF ──────────────────────────────
        lay.addWidget(_section_title("Notificari automate"))
        notif_row = QHBoxLayout()
        self.lbl_notif = QLabel("Activeaza notificarile:")
        self.chk_notificari = QCheckBox("Activat")
        self.chk_notificari.setStyleSheet("QCheckBox { font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; }")
        notif_row.addWidget(self.lbl_notif); notif_row.addWidget(self.chk_notificari); notif_row.addStretch()
        lay.addLayout(notif_row)

        reminder_row = QHBoxLayout()
        lbl_rem = QLabel("Reminder programare (ore inainte):")
        self.cmb_reminder = QComboBox(); self.cmb_reminder.addItems(["12", "24", "48"]); self.cmb_reminder.setFixedWidth(80)
        reminder_row.addWidget(lbl_rem); reminder_row.addWidget(self.cmb_reminder); reminder_row.addStretch()
        lay.addLayout(reminder_row)

        # ── SMTP ───────────────────────────────────────────
        lay.addWidget(_separator())
        lay.addWidget(_section_title("Configurare SMTP"))

        form_email = QFormLayout(); form_email.setSpacing(10); form_email.setLabelAlignment(Qt.AlignRight)
        self.txt_smtp_host = QLineEdit(); self.txt_smtp_host.setPlaceholderText("ex: mail.velorix.ro");      self.txt_smtp_host.setFixedWidth(280)
        self.txt_smtp_port = QLineEdit(); self.txt_smtp_port.setPlaceholderText("587 (TLS) sau 465 (SSL)"); self.txt_smtp_port.setFixedWidth(160)
        self.txt_smtp_user = QLineEdit(); self.txt_smtp_user.setPlaceholderText("ex: notificari@velorix.ro"); self.txt_smtp_user.setFixedWidth(320)
        self.txt_smtp_pass = QLineEdit(); self.txt_smtp_pass.setEchoMode(QLineEdit.Password)
        self.txt_smtp_pass.setPlaceholderText("Parola contului email"); self.txt_smtp_pass.setFixedWidth(320)
        self.chk_smtp_ssl  = QCheckBox("Foloseste SSL (port 465)")

        form_email.addRow("Server SMTP:",    self.txt_smtp_host)
        form_email.addRow("Port:",           self.txt_smtp_port)
        form_email.addRow("Email expeditor:",self.txt_smtp_user)
        form_email.addRow("Parola:",         self.txt_smtp_pass)
        form_email.addRow("",                self.chk_smtp_ssl)
        lay.addLayout(form_email)

        btns_email = QHBoxLayout()
        self.btn_test_email = QPushButton("🔌 Testeaza conexiunea"); self.btn_test_email.setFixedHeight(34)
        self.btn_test_email.clicked.connect(self.test_email_connection)
        self.btn_save_email = QPushButton("💾 Salveaza setarile email"); self.btn_save_email.setFixedHeight(34)
        self.btn_save_email.clicked.connect(self.save_email_settings)
        btns_email.addWidget(self.btn_test_email); btns_email.addWidget(self.btn_save_email); btns_email.addStretch()
        lay.addLayout(btns_email)

        self.lbl_test_result = QLabel(""); self.lbl_test_result.setStyleSheet("font-size: 12px;")
        lay.addWidget(self.lbl_test_result)

        # ── WhatsApp Business API ──────────────────────────
        lay.addWidget(_separator())
        lay.addWidget(_section_title("📱 WhatsApp Business API"))

        wa_activ_row = QHBoxLayout()
        self.chk_wa_activ = QCheckBox("Activat")
        self.chk_wa_activ.setStyleSheet("QCheckBox { font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; }")
        wa_activ_row.addWidget(QLabel("Activeaza WhatsApp:"))
        wa_activ_row.addWidget(self.chk_wa_activ)
        wa_activ_row.addStretch()
        lay.addLayout(wa_activ_row)

        form_wa = QFormLayout(); form_wa.setSpacing(10); form_wa.setLabelAlignment(Qt.AlignRight)
        self.txt_wa_phone_id = QLineEdit()
        self.txt_wa_phone_id.setPlaceholderText("Phone Number ID din Meta Business"); self.txt_wa_phone_id.setFixedWidth(360)
        self.txt_wa_token = QLineEdit()
        self.txt_wa_token.setPlaceholderText("Access Token permanent"); self.txt_wa_token.setEchoMode(QLineEdit.Password); self.txt_wa_token.setFixedWidth(360)
        self.txt_wa_tmpl_finalizat = QLineEdit()
        self.txt_wa_tmpl_finalizat.setPlaceholderText("ex: lucrare_finalizata"); self.txt_wa_tmpl_finalizat.setFixedWidth(280)
        self.txt_wa_tmpl_reminder = QLineEdit()
        self.txt_wa_tmpl_reminder.setPlaceholderText("ex: reminder_programare"); self.txt_wa_tmpl_reminder.setFixedWidth(280)

        form_wa.addRow("Phone Number ID:",              self.txt_wa_phone_id)
        form_wa.addRow("Access Token:",                 self.txt_wa_token)
        form_wa.addRow("Template lucrare finalizata:",  self.txt_wa_tmpl_finalizat)
        form_wa.addRow("Template reminder programare:", self.txt_wa_tmpl_reminder)
        lay.addLayout(form_wa)

        lbl_wa_help = QLabel(
            "Obtii credentialele din: <a href='https://developers.facebook.com/'>Meta for Developers</a>"
            " → My Apps → WhatsApp → API Setup"
        )
        lbl_wa_help.setOpenExternalLinks(True)
        lbl_wa_help.setStyleSheet(f"font-size: 11px; color: {C_GREY};")
        lay.addWidget(lbl_wa_help)

        self.btn_save_wa = QPushButton("💾 Salveaza setarile WhatsApp")
        self.btn_save_wa.setFixedHeight(34); self.btn_save_wa.setFixedWidth(280)
        self.btn_save_wa.clicked.connect(self.save_wa_settings)
        lay.addWidget(self.btn_save_wa)

        # ── SMS ────────────────────────────────────────────
        lay.addWidget(_separator())
        lay.addWidget(_section_title("💬 SMS"))

        sms_activ_row = QHBoxLayout()
        self.chk_sms_activ = QCheckBox("Activat")
        self.chk_sms_activ.setStyleSheet("QCheckBox { font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; }")
        sms_activ_row.addWidget(QLabel("Activeaza SMS:"))
        sms_activ_row.addWidget(self.chk_sms_activ)
        sms_activ_row.addStretch()
        lay.addLayout(sms_activ_row)

        form_sms = QFormLayout(); form_sms.setSpacing(10); form_sms.setLabelAlignment(Qt.AlignRight)
        self.cmb_sms_provider = QComboBox()
        self.cmb_sms_provider.addItems(["SMSAPI.ro", "Twilio", "TextMagic"]); self.cmb_sms_provider.setFixedWidth(180)
        self.cmb_sms_provider.currentIndexChanged.connect(self._update_sms_help)
        self.txt_sms_key = QLineEdit()
        self.txt_sms_key.setPlaceholderText("API Key / Account SID"); self.txt_sms_key.setEchoMode(QLineEdit.Password); self.txt_sms_key.setFixedWidth(360)
        self.txt_sms_secret = QLineEdit()
        self.txt_sms_secret.setPlaceholderText("Auth Token / Password (doar Twilio/TextMagic)"); self.txt_sms_secret.setEchoMode(QLineEdit.Password); self.txt_sms_secret.setFixedWidth(360)
        self.txt_sms_sender = QLineEdit()
        self.txt_sms_sender.setPlaceholderText("Numar expeditor sau nume alfanumeric"); self.txt_sms_sender.setFixedWidth(280)
        self.txt_sms_tmpl_finalizat = QLineEdit()
        self.txt_sms_tmpl_finalizat.setPlaceholderText("ex: Lucrarea la {vehicul} este finalizata. Va asteptam!"); self.txt_sms_tmpl_finalizat.setFixedWidth(400)
        self.txt_sms_tmpl_reminder = QLineEdit()
        self.txt_sms_tmpl_reminder.setPlaceholderText("ex: Reminder: programare maine la {ora}. {firma}"); self.txt_sms_tmpl_reminder.setFixedWidth(400)

        form_sms.addRow("Provider:",                   self.cmb_sms_provider)
        form_sms.addRow("API Key:",                    self.txt_sms_key)
        form_sms.addRow("Auth Token / Secret:",        self.txt_sms_secret)
        form_sms.addRow("Expeditor:",                  self.txt_sms_sender)
        form_sms.addRow("Template lucrare finalizata:",self.txt_sms_tmpl_finalizat)
        form_sms.addRow("Template reminder:",          self.txt_sms_tmpl_reminder)
        lay.addLayout(form_sms)

        self.lbl_sms_help = QLabel("")
        self.lbl_sms_help.setOpenExternalLinks(True)
        self.lbl_sms_help.setStyleSheet(f"font-size: 11px; color: {C_GREY};")
        lay.addWidget(self.lbl_sms_help)
        self._update_sms_help()

        self.btn_save_sms = QPushButton("💾 Salveaza setarile SMS")
        self.btn_save_sms.setFixedHeight(34); self.btn_save_sms.setFixedWidth(240)
        self.btn_save_sms.clicked.connect(self.save_sms_settings)
        lay.addWidget(self.btn_save_sms)

        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: CONTUL MEU
    # ─────────────────────────────────────────────────────────
    def _build_cont(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)

        lay.addWidget(self._page_header("👤", "Contul meu",
            "Gestioneaza datele contului tau de acces."))
        lay.addWidget(_separator())

        self.lbl_email = QLabel(f"Email: {self.parent.logged_email}")
        self.lbl_email.setStyleSheet(f"font-size: 14px; color: {C_DARK};")
        self.lbl_role = QLabel(f"Rol: {self.parent.role}")
        self.lbl_role.setStyleSheet(f"font-size: 14px; color: {C_GREY};")
        lay.addWidget(self.lbl_email)
        lay.addWidget(self.lbl_role)
        lay.addSpacing(8)

        self.btn_change_pass = QPushButton("🔐 Schimba parola")
        self.btn_change_pass.setFixedWidth(200)
        self.btn_change_pass.clicked.connect(self.change_password)
        lay.addWidget(self.btn_change_pass)

        lay.addStretch()
        lay.addWidget(_separator())

        self.btn_logout = QPushButton("🔄 Schimba utilizator")
        self.btn_logout.setFixedWidth(200)
        self.btn_logout.clicked.connect(self.logout_user)
        lay.addWidget(self.btn_logout)
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: UTILIZATORI
    # ─────────────────────────────────────────────────────────
    def _build_users(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(14)

        lay.addWidget(self._page_header("👥", "Utilizatori",
            "Gestioneaza conturile si permisiunile utilizatorilor."))
        lay.addWidget(_separator())

        pill_row = QHBoxLayout(); pill_row.setSpacing(8)
        self._u_btn_lista = self._pill_btn("Lista utilizatori", True)
        self._u_btn_perm  = self._pill_btn("Permisiuni roluri", False)
        pill_row.addWidget(self._u_btn_lista); pill_row.addWidget(self._u_btn_perm); pill_row.addStretch()
        lay.addLayout(pill_row)

        self._u_stack = QStackedWidget()
        self._u_stack.setStyleSheet("background: transparent;")

        # ---- Lista utilizatori ----
        p_lista = QWidget(); p_lista.setStyleSheet("background: transparent;")
        p_lista_lay = QVBoxLayout(p_lista); p_lista_lay.setContentsMargins(0, 8, 0, 0); p_lista_lay.setSpacing(10)
        self.table_users = QTableWidget()
        self.table_users.setColumnCount(4)
        self.table_users.setHorizontalHeaderLabels(["Email", "Rol", "Ultima logare", "Actiuni"])
        self.table_users.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_users.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_users.setSelectionMode(QTableWidget.NoSelection)
        self.table_users.setMinimumHeight(300)
        p_lista_lay.addWidget(self.table_users)
        self.btn_add_user = QPushButton("➕ Adauga utilizator")
        self.btn_add_user.setFixedWidth(200)
        self.btn_add_user.clicked.connect(self.add_user_dialog)
        p_lista_lay.addWidget(self.btn_add_user)

        # ---- Permisiuni ----
        p_perm = QWidget(); p_perm.setStyleSheet("background: transparent;")
        p_perm_lay = QVBoxLayout(p_perm); p_perm_lay.setContentsMargins(0, 8, 0, 0); p_perm_lay.setSpacing(10)
        self.lbl_perm_info = QLabel("Bifati sectiunile la care fiecare rol are acces. Administrator are intotdeauna acces total.")
        self.lbl_perm_info.setStyleSheet(f"font-size: 12px; color: {C_GREY};"); self.lbl_perm_info.setWordWrap(True)
        p_perm_lay.addWidget(self.lbl_perm_info)
        self.table_permisiuni = QTableWidget()
        self.table_permisiuni.setColumnCount(4)
        self.table_permisiuni.setHorizontalHeaderLabels(["Sectiune", "Administrator", "Mecanic", "Receptie"])
        self.table_permisiuni.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in [1, 2, 3]: self.table_permisiuni.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
        self.table_permisiuni.setColumnWidth(1, 130); self.table_permisiuni.setColumnWidth(2, 100); self.table_permisiuni.setColumnWidth(3, 100)
        self.table_permisiuni.setShowGrid(True); self.table_permisiuni.verticalHeader().setVisible(False)
        self.table_permisiuni.setSelectionMode(QTableWidget.NoSelection)
        self.table_permisiuni.setMinimumHeight(300)
        p_perm_lay.addWidget(self.table_permisiuni)
        self.btn_save_permisiuni = QPushButton("💾 Salveaza permisiuni")
        self.btn_save_permisiuni.setFixedWidth(220)
        self.btn_save_permisiuni.clicked.connect(self.save_permisiuni)
        p_perm_lay.addWidget(self.btn_save_permisiuni)

        self._u_stack.addWidget(p_lista)
        self._u_stack.addWidget(p_perm)
        lay.addWidget(self._u_stack)

        self._u_btn_lista.clicked.connect(lambda: self._switch_user_tab(0))
        self._u_btn_perm.clicked.connect(lambda: self._switch_user_tab(1))
        lay.addStretch()
        return self._scrolled(inner)

    def _pill_btn(self, text, active):
        btn = QPushButton(text)
        btn.setCheckable(True); btn.setChecked(active)
        btn.setFixedHeight(30); btn.setCursor(Qt.PointingHandCursor)
        self._update_pill(btn, active)
        return btn

    def _update_pill(self, btn, active):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C_BLUE}; color: white; border: none;
                border-radius: 15px; font-size: 12px; font-weight: 600; padding: 0 16px; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C_LIGHT}; color: {C_BLUE}; border: none;
                border-radius: 15px; font-size: 12px; padding: 0 16px; }}
                QPushButton:hover {{ background: {C_BORDER}; }}
            """)

    def _switch_user_tab(self, idx):
        self._u_stack.setCurrentIndex(idx)
        self._update_pill(self._u_btn_lista, idx == 0)
        self._update_pill(self._u_btn_perm,  idx == 1)
        self._u_btn_lista.setChecked(idx == 0)
        self._u_btn_perm.setChecked(idx == 1)

    # ─────────────────────────────────────────────────────────
    # PAGINA: JURNAL ACTIVITATE
    # ─────────────────────────────────────────────────────────
    def _build_audit(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(14)

        lay.addWidget(self._page_header("📋", "Jurnal activitate",
            "Istoricul tuturor actiunilor efectuate in aplicatie."))
        lay.addWidget(_separator())

        filter_row = QHBoxLayout(); filter_row.setSpacing(8)
        self.filter_user = QLineEdit(); self.filter_user.setPlaceholderText("Filtru utilizator"); self.filter_user.setFixedWidth(200)
        self.filter_date = QLineEdit(); self.filter_date.setPlaceholderText("YYYY-MM-DD");        self.filter_date.setFixedWidth(140)
        self.filter_btn  = QPushButton("Filtreaza"); self.filter_btn.setFixedWidth(100)
        self.filter_btn.clicked.connect(self.load_audit)
        filter_row.addWidget(self.filter_user); filter_row.addWidget(self.filter_date)
        filter_row.addWidget(self.filter_btn);  filter_row.addStretch()
        lay.addLayout(filter_row)

        self.table_audit = QTableWidget()
        self.table_audit.setColumnCount(4)
        self.table_audit.setHorizontalHeaderLabels(["Utilizator", "Actiune", "Detalii", "Data"])
        self.table_audit.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_audit.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_audit.setMinimumHeight(400)
        lay.addWidget(self.table_audit)
        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: BACKUP
    # ─────────────────────────────────────────────────────────
    def _build_backup(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(14)

        lay.addWidget(self._page_header("💾", "Backup",
            "Backup-uri automate si manuale ale bazei de date."))
        lay.addWidget(_separator())

        self.lbl_backup_info = QLabel("Backup-uri disponibile:")
        self.lbl_backup_info.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C_DARK};")
        lay.addWidget(self.lbl_backup_info)

        self.table_backup = QTableWidget()
        self.table_backup.setColumnCount(3)
        self.table_backup.setHorizontalHeaderLabels(["Nume fisier", "Data", "Marime (KB)"])
        self.table_backup.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_backup.setSelectionBehavior(self.table_backup.SelectRows)
        self.table_backup.setEditTriggers(self.table_backup.NoEditTriggers)
        self.table_backup.setMinimumHeight(300)
        lay.addWidget(self.table_backup)

        btns = QHBoxLayout(); btns.setSpacing(10)
        self.btn_backup_manual = QPushButton("💾 Backup manual acum")
        self.btn_backup_manual.clicked.connect(self.face_backup_manual)
        self.btn_restaureaza = QPushButton("♻️ Restaureaza selectat")
        self.btn_restaureaza.clicked.connect(self.restaureaza_backup)
        btns.addWidget(self.btn_backup_manual); btns.addWidget(self.btn_restaureaza); btns.addStretch()
        lay.addLayout(btns)
        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: CLOUD SYNC
    # ─────────────────────────────────────────────────────────
    def _build_cloud(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(16)

        lay.addWidget(self._page_header("☁️", "Cloud Sync",
            "Sincronizare automata cu Supabase la fiecare 30 secunde."))
        lay.addWidget(_separator())

        self.lbl_cloud_status = QLabel("☁️ Sincronizare Supabase")
        self.lbl_cloud_status.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {C_DARK};")
        lay.addWidget(self.lbl_cloud_status)

        self.lbl_cloud_info = QLabel("Datele sunt sincronizate automat cu Supabase.\nFoloseste butoanele de mai jos pentru operatii manuale.")
        self.lbl_cloud_info.setStyleSheet(f"font-size: 12px; color: {C_GREY};"); self.lbl_cloud_info.setWordWrap(True)
        lay.addWidget(self.lbl_cloud_info)

        self.btn_sync_now = QPushButton("🔄 Sincronizeaza acum")
        self.btn_sync_now.setFixedHeight(40); self.btn_sync_now.setFixedWidth(200)
        self.btn_sync_now.clicked.connect(self._sync_now)
        lay.addWidget(self.btn_sync_now)
        self.lbl_sync_result = QLabel(""); self.lbl_sync_result.setStyleSheet("font-size: 12px;")
        lay.addWidget(self.lbl_sync_result)

        lay.addWidget(_separator())
        lbl_restore = QLabel("🔁 Restaurare din Cloud")
        lbl_restore.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {C_DARK};")
        lay.addWidget(lbl_restore)

        lbl_ri = QLabel("Descarca toate datele din Supabase si le restaureaza local.\nFoloseste dupa o reinstalare a aplicatiei.")
        lbl_ri.setStyleSheet(f"font-size: 12px; color: {C_GREY};"); lbl_ri.setWordWrap(True)
        lay.addWidget(lbl_ri)

        self.btn_restore_cloud = QPushButton("⬇️ Restaureaza din Cloud")
        self.btn_restore_cloud.setFixedHeight(40); self.btn_restore_cloud.setFixedWidth(220)
        self.btn_restore_cloud.clicked.connect(self._restore_from_cloud)
        lay.addWidget(self.btn_restore_cloud)
        self.lbl_restore_result = QLabel(""); self.lbl_restore_result.setStyleSheet("font-size: 12px;")
        lay.addWidget(self.lbl_restore_result)
        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # PAGINA: E-FACTURA
    # ─────────────────────────────────────────────────────────
    def _build_efactura(self):
        inner = self._content_widget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(14)

        lay.addWidget(self._page_header("🧾", "E-Factura ANAF",
            "Trimite facturile la ANAF prin SmartBill sau Oblio."))
        lay.addWidget(_separator())

        activ_row = QHBoxLayout()
        lbl_activ = QLabel("Activeaza E-Factura:")
        lbl_activ.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {C_DARK};")
        self.chk_ef_activ = QCheckBox("Activat")
        self.chk_ef_activ.setStyleSheet("QCheckBox { font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; }")
        self.chk_ef_activ.stateChanged.connect(self._ef_toggle_activ)
        activ_row.addWidget(lbl_activ); activ_row.addWidget(self.chk_ef_activ); activ_row.addStretch()
        lay.addLayout(activ_row)

        test_row = QHBoxLayout()
        lbl_test_mode = QLabel("Mod test (sandbox):")
        lbl_test_mode.setStyleSheet(f"font-size: 12px; color: {C_GREY};")
        self.chk_ef_test = QCheckBox("Activat — nu trimite real la ANAF")
        self.chk_ef_test.setStyleSheet(f"font-size: 12px; color: {C_GREY};"); self.chk_ef_test.setChecked(True)
        test_row.addWidget(lbl_test_mode); test_row.addWidget(self.chk_ef_test); test_row.addStretch()
        lay.addLayout(test_row)

        lay.addWidget(_separator())
        lay.addWidget(_section_title("Credentiale provider"))

        form_ef = QFormLayout(); form_ef.setSpacing(10); form_ef.setLabelAlignment(Qt.AlignRight)
        self.cmb_ef_provider = QComboBox(); self.cmb_ef_provider.addItems(["SmartBill", "Oblio"]); self.cmb_ef_provider.setFixedWidth(160)
        self.cmb_ef_provider.currentIndexChanged.connect(self._ef_update_help)
        self.txt_ef_cif    = QLineEdit(); self.txt_ef_cif.setPlaceholderText("ex: RO12345678");                     self.txt_ef_cif.setFixedWidth(320)
        self.txt_ef_email  = QLineEdit(); self.txt_ef_email.setPlaceholderText("Email-ul contului SmartBill / Oblio"); self.txt_ef_email.setFixedWidth(400)
        self.txt_ef_apikey = QLineEdit(); self.txt_ef_apikey.setPlaceholderText("API Key din contul tau")
        self.txt_ef_apikey.setEchoMode(QLineEdit.Password); self.txt_ef_apikey.setFixedWidth(356)

        self.btn_ef_show = QPushButton("👁")
        self.btn_ef_show.setFixedSize(42, 34); self.btn_ef_show.setCheckable(True)
        self.btn_ef_show.setCursor(Qt.PointingHandCursor); self.btn_ef_show.setToolTip("Arata / Ascunde API Key")
        self.btn_ef_show.setStyleSheet(f"""
            QPushButton {{ border: 1px solid {C_BORDER}; border-radius: 6px; background: {C_GREYBG}; font-size: 16px; color: {C_GREY}; }}
            QPushButton:hover {{ background: {C_LIGHT}; border-color: {C_ACCENT}; color: {C_BLUE}; }}
            QPushButton:checked {{ background: {C_LIGHT}; border-color: {C_ACCENT}; color: {C_BLUE}; }}
        """)

        apikey_row = QHBoxLayout(); apikey_row.setContentsMargins(0, 0, 0, 0); apikey_row.setSpacing(6)
        apikey_row.addWidget(self.txt_ef_apikey); apikey_row.addWidget(self.btn_ef_show); apikey_row.addStretch()
        apikey_w = QWidget(); apikey_w.setLayout(apikey_row)

        form_ef.addRow("Provider:",   self.cmb_ef_provider)
        form_ef.addRow("CIF firma:",  self.txt_ef_cif)
        form_ef.addRow("Email cont:", self.txt_ef_email)
        form_ef.addRow("API Key:",    apikey_w)
        lay.addLayout(form_ef)

        self.lbl_ef_help = QLabel(); self.lbl_ef_help.setOpenExternalLinks(True)
        self.lbl_ef_help.setStyleSheet(f"font-size: 11px; color: {C_GREY};"); self.lbl_ef_help.setWordWrap(True)
        lay.addWidget(self.lbl_ef_help)
        self._ef_update_help()

        btns_ef = QHBoxLayout(); btns_ef.setSpacing(10)
        self.btn_ef_test = QPushButton("🔌 Testeaza conexiunea"); self.btn_ef_test.setFixedHeight(36)
        self.btn_ef_test.clicked.connect(self._ef_test_conexiune)
        self.btn_ef_save = QPushButton("💾 Salveaza setarile"); self.btn_ef_save.setFixedHeight(36)
        self.btn_ef_save.clicked.connect(self._ef_save)
        btns_ef.addWidget(self.btn_ef_test); btns_ef.addWidget(self.btn_ef_save); btns_ef.addStretch()
        lay.addLayout(btns_ef)

        self.lbl_ef_result = QLabel(""); self.lbl_ef_result.setStyleSheet("font-size: 12px;"); self.lbl_ef_result.setWordWrap(True)
        lay.addWidget(self.lbl_ef_result)

        self.lbl_ef_status_box = QLabel("")
        self.lbl_ef_status_box.setWordWrap(True); self.lbl_ef_status_box.setMinimumHeight(40)
        self.lbl_ef_status_box.setStyleSheet("QLabel { border-radius: 8px; padding: 10px 14px; font-size: 12px; }")
        lay.addWidget(self.lbl_ef_status_box)
        lay.addStretch()
        return self._scrolled(inner)

    # ─────────────────────────────────────────────────────────
    # Compatibilitate cu codul existent
    # ─────────────────────────────────────────────────────────
    @property
    def tabs(self):
        return None

    def on_tab_changed(self, index):
        pass

    # =========================================================
    # PERMISIUNI ROLURI
    # =========================================================
    SECTIUNI = [
        ("clienti_vizualizare",  "Clienti — vizualizare"),
        ("clienti_modificare",   "Clienti — adaugare / editare / stergere"),
        ("vehicule_vizualizare", "Vehicule — vizualizare"),
        ("vehicule_modificare",  "Vehicule — adaugare / editare / stergere"),
        ("fisa_service",         "Fisa Service"),
        ("lucrari",              "Lucrari"),
        ("devize",               "Devize"),
        ("istoric",              "Istoric lucrari"),
        ("rapoarte",             "Rapoarte"),
        ("stocuri_vizualizare",  "Stocuri — vizualizare"),
        ("stocuri_modificare",   "Stocuri — adaugare / editare / stergere"),
        ("setari",               "Setari"),
    ]
    ROLURI_COLOANE = [("administrator", 1), ("mecanic", 2), ("receptie", 3)]

    def load_permisiuni(self):
        perm = {rol: get_permisiuni(rol) for rol, _ in self.ROLURI_COLOANE}
        self.table_permisiuni.setRowCount(len(self.SECTIUNI))
        for row_idx, (sectiune_key, sectiune_label) in enumerate(self.SECTIUNI):
            item_label = QTableWidgetItem(sectiune_label)
            item_label.setFlags(Qt.ItemIsEnabled); item_label.setBackground(Qt.white)
            self.table_permisiuni.setItem(row_idx, 0, item_label)
            for rol, col_idx in self.ROLURI_COLOANE:
                chk = QTableWidgetItem()
                if rol == "administrator":
                    chk.setFlags(Qt.ItemIsEnabled); chk.setCheckState(Qt.Checked); chk.setBackground(Qt.lightGray)
                else:
                    chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                    chk.setCheckState(Qt.Checked if perm[rol].get(sectiune_key, False) else Qt.Unchecked)
                self.table_permisiuni.setItem(row_idx, col_idx, chk)
            self.table_permisiuni.setRowHeight(row_idx, 36)

    def save_permisiuni(self):
        con = get_connection(); cur = con.cursor()
        for row_idx, (sectiune_key, _) in enumerate(self.SECTIUNI):
            for rol, col_idx in self.ROLURI_COLOANE:
                if rol == "administrator": continue
                item = self.table_permisiuni.item(row_idx, col_idx)
                if item is None: continue
                acces = 1 if item.checkState() == Qt.Checked else 0
                cur.execute(
                    "INSERT INTO permisiuni (rol, sectiune, acces) VALUES (?, ?, ?) "
                    "ON CONFLICT(rol, sectiune) DO UPDATE SET acces=excluded.acces",
                    (rol, sectiune_key, acces)
                )
        con.commit(); con.close()
        log_action(self.parent.logged_email, "Modificare permisiuni", "Permisiuni roluri actualizate")
        show_toast(self.parent, "Permisiunile au fost salvate. Vor fi active la urmatorul login.")

    # =========================================================
    # UTILIZATORI
    # =========================================================
    def load_users(self):
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT id, username, role, last_login FROM users ORDER BY username")
        rows = cur.fetchall(); con.close()
        self.table_users.setRowCount(len(rows))
        for row_idx, (user_id, email, role, last_login) in enumerate(rows):
            self.table_users.setItem(row_idx, 0, QTableWidgetItem(email))
            self.table_users.setItem(row_idx, 1, QTableWidgetItem(role))
            self.table_users.setItem(row_idx, 2, QTableWidgetItem(last_login or "-"))
            self.table_users.setRowHeight(row_idx, 55)
            btn_reset  = QPushButton("Resetare");    btn_reset.setFixedHeight(32)
            btn_role   = QPushButton("Schimba rol"); btn_role.setFixedHeight(32)
            btn_delete = QPushButton("Sterge");      btn_delete.setFixedHeight(32)
            btn_reset.clicked.connect(self._make_reset_handler(user_id))
            btn_role.clicked.connect(self._make_role_handler(user_id))
            btn_delete.clicked.connect(self._make_delete_handler(user_id))
            aw = QWidget(); al = QHBoxLayout(aw)
            al.addWidget(btn_reset); al.addWidget(btn_role); al.addWidget(btn_delete)
            al.setContentsMargins(4, 4, 4, 4)
            self.table_users.setCellWidget(row_idx, 3, aw)

    def _make_reset_handler(self, uid):  return lambda: self.reset_password(uid)
    def _make_role_handler(self, uid):   return lambda: self.change_role(uid)
    def _make_delete_handler(self, uid): return lambda: self.delete_user(uid)

    def reset_password(self, user_id):
        con = get_connection(); cur = con.cursor()
        cur.execute("UPDATE users SET password=? WHERE id=?", (hash_password("parola123"), user_id))
        con.commit(); con.close()
        log_action(self.parent.logged_email, "Resetare parola", f"user_id={user_id}")
        show_toast(self.parent, "Parola a fost resetata la: parola123")

    def change_role(self, user_id):
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT role FROM users WHERE id=?", (user_id,)); row = cur.fetchone()
        if not row: con.close(); return
        role = row[0]
        from PyQt5.QtWidgets import QInputDialog
        roluri_disponibile = [r for r in ["administrator", "mecanic", "receptie"] if r != role]
        new_role, ok = QInputDialog.getItem(self, "Schimba rol", f"Rol curent: {role}\nAlege noul rol:", roluri_disponibile, 0, False)
        if not ok: con.close(); return
        if role == "administrator":
            cur.execute("SELECT COUNT(*) FROM users WHERE role='administrator'")
            if cur.fetchone()[0] <= 1:
                show_toast(self.parent, "Nu poti schimba rolul singurului administrator!"); con.close(); return
        cur.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id)); con.commit(); con.close()
        log_action(self.parent.logged_email, "Schimbare rol", f"user_id={user_id} -> {new_role}")
        show_toast(self.parent, "Rolul a fost schimbat"); self.load_users()

    def delete_user(self, user_id):
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT role FROM users WHERE id=?", (user_id,)); row = cur.fetchone()
        if not row: con.close(); return
        if row[0] == "administrator":
            cur.execute("SELECT COUNT(*) FROM users WHERE role='administrator'")
            if cur.fetchone()[0] <= 1:
                show_toast(self.parent, "Nu poti sterge singurul administrator!"); con.close(); return
        cur.execute("DELETE FROM users WHERE id=?", (user_id,)); con.commit(); con.close()
        log_action(self.parent.logged_email, "Stergere utilizator", f"user_id={user_id}")
        show_toast(self.parent, "Utilizator sters"); self.load_users()

    def add_user_dialog(self):
        dialog = QDialog(self); dialog.setWindowTitle("Adauga utilizator")
        form = QFormLayout(dialog)
        email    = QLineEdit()
        password = QLineEdit(); password.setEchoMode(QLineEdit.Password)
        role     = QComboBox(); role.addItems(["administrator", "mecanic", "receptie"])
        form.addRow("Email:", email); form.addRow("Parola:", password); form.addRow("Rol:", role)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(buttons); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        if dialog.exec_() == QDialog.Accepted:
            if not email.text().strip():    show_toast(self.parent, "Email invalid"); return
            if not password.text().strip(): show_toast(self.parent, "Parola nu poate fi goala"); return
            con = get_connection(); cur = con.cursor()
            try:
                cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                            (email.text().strip(), hash_password(password.text()), role.currentText()))
                con.commit()
                log_action(self.parent.logged_email, "Adaugare utilizator", email.text())
                show_toast(self.parent, "Utilizator adaugat")
            except Exception:
                show_toast(self.parent, "Eroare: email deja existent")
            finally:
                con.close()
            self.load_users()

    # =========================================================
    # AUDIT
    # =========================================================
    def load_audit(self):
        user_filter = self.filter_user.text().strip()
        date_filter = self.filter_date.text().strip()
        con = get_connection(); cur = con.cursor()
        query = "SELECT username, actiune, detalii, timestamp FROM audit_log WHERE 1=1"; params = []
        if user_filter: query += " AND username LIKE ?"; params.append(f"%{user_filter}%")
        if date_filter:
            if len(date_filter) != 10 or date_filter.count("-") != 2:
                show_toast(self.parent, "Format data invalid (YYYY-MM-DD)"); con.close(); return
            query += " AND DATE(timestamp) = ?"; params.append(date_filter)
        query += " ORDER BY timestamp DESC"
        cur.execute(query, params); rows = cur.fetchall(); con.close()
        self.table_audit.setRowCount(0); self.table_audit.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.table_audit.setItem(i, j, QTableWidgetItem(str(value)))

    # =========================================================
    # LOGOUT / PAROLA
    # =========================================================
    def logout_user(self):
        from ui.login_window import LoginWindow
        SessionManager.logout(); self.parent.hide()
        self.login = LoginWindow(); self.login.show()

    def change_password(self):
        dialog = QDialog(self); dialog.setWindowTitle("Schimbare parola")
        form = QFormLayout(dialog)
        old_pass     = QLineEdit(); old_pass.setEchoMode(QLineEdit.Password)
        new_pass     = QLineEdit(); new_pass.setEchoMode(QLineEdit.Password)
        confirm_pass = QLineEdit(); confirm_pass.setEchoMode(QLineEdit.Password)
        form.addRow("Parola veche:", old_pass)
        form.addRow("Parola noua:",  new_pass)
        form.addRow("Confirmare:",   confirm_pass)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(buttons)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        if dialog.exec_() != QDialog.Accepted: return
        if not old_pass.text().strip():
            show_toast(self.parent, "Introduceti parola veche."); return
        if not new_pass.text().strip():
            show_toast(self.parent, "Parola noua nu poate fi goala."); return
        if new_pass.text() != confirm_pass.text():
            show_toast(self.parent, "Parolele nu coincid."); return
        con = get_connection(); cur = con.cursor()
        try:
            cur.execute("SELECT password FROM users WHERE username=?", (self.parent.logged_email,))
            row = cur.fetchone()
            # ── FIX: folosim verify_password cu suport bcrypt ──
            if not row or not verify_password(old_pass.text(), row[0]):
                show_toast(self.parent, "Parola veche este incorecta."); return
            cur.execute("UPDATE users SET password=? WHERE username=?",
                        (hash_password(new_pass.text()), self.parent.logged_email))
            con.commit()
            log_action(self.parent.logged_email, "Schimbare parola", "Parola proprie schimbata")
            show_toast(self.parent, "Parola a fost schimbata.")
        finally:
            con.close()

    # =========================================================
    # TARIF / TVA
    # =========================================================
    def load_tarif(self):
        con = get_connection(); cur = con.cursor()
        try:
            cur.execute("SELECT tarif_ora FROM firma LIMIT 1"); row = cur.fetchone()
            self.txt_tarif.setText(str(row[0]) if row and row[0] else "150")
        except:
            self.txt_tarif.setText("150")
        finally:
            con.close()

    def save_tarif(self):
        try: tarif = float(self.txt_tarif.text().strip())
        except ValueError: show_toast(self.parent, "Valoare tarif invalida"); return
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT id FROM firma LIMIT 1"); row = cur.fetchone()
        if row: cur.execute("UPDATE firma SET tarif_ora=? WHERE id=?", (tarif, row[0]))
        else:   cur.execute("INSERT INTO firma (nume, cui, adresa, telefon, tva, tarif_ora) VALUES ('','','','',21,?)", (tarif,))
        con.commit(); con.close(); show_toast(self.parent, "Tarif salvat")

    def load_tva(self):
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT tva FROM firma LIMIT 1"); row = cur.fetchone(); con.close()
        self.txt_tva.setText(str(row[0]) if row and row[0] else "21")

    def save_tva(self):
        try: tva = float(self.txt_tva.text().strip())
        except ValueError: show_toast(self.parent, "Valoare TVA invalida"); return
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT id FROM firma LIMIT 1"); row = cur.fetchone()
        if row: cur.execute("UPDATE firma SET tva=? WHERE id=?", (tva, row[0]))
        else:   cur.execute("INSERT INTO firma (nume, cui, adresa, telefon, tva) VALUES ('','','','',?)", (tva,))
        con.commit(); con.close(); show_toast(self.parent, "TVA salvat")
        if hasattr(self.parent, "page_stocuri"): self.parent.page_stocuri.load_data()

    # =========================================================
    # EMAIL
    # =========================================================
    def _ensure_email_table(self, cur):
        cur.execute("""CREATE TABLE IF NOT EXISTS email_settings (
            id INTEGER PRIMARY KEY, smtp_host TEXT DEFAULT '', smtp_port INTEGER DEFAULT 587,
            smtp_user TEXT DEFAULT '', smtp_password TEXT DEFAULT '',
            smtp_ssl INTEGER DEFAULT 0, notificari_active INTEGER DEFAULT 0,
            reminder_ore INTEGER DEFAULT 24
        )""")
        for sql in [
            "ALTER TABLE programari ADD COLUMN reminder_trimis INTEGER DEFAULT 0",
            "ALTER TABLE lucrari ADD COLUMN notificare_trimisa INTEGER DEFAULT 0",
        ]:
            try: cur.execute(sql)
            except: pass

    def load_email_settings(self):
        con = get_connection(); cur = con.cursor()
        self._ensure_email_table(cur); con.commit()
        cur.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_password, smtp_ssl, notificari_active, reminder_ore FROM email_settings LIMIT 1")
        row = cur.fetchone(); con.close()
        if row:
            self.txt_smtp_host.setText(row[0] or ""); self.txt_smtp_port.setText(str(row[1]) if row[1] else "587")
            self.txt_smtp_user.setText(row[2] or ""); self.txt_smtp_pass.setText(decrypt(row[3] or ""))
            self.chk_smtp_ssl.setChecked(bool(row[4])); self.chk_notificari.setChecked(bool(row[5]))
            idx = self.cmb_reminder.findText(str(row[6]))
            if idx >= 0: self.cmb_reminder.setCurrentIndex(idx)

    def save_email_settings(self):
        try: port = int(self.txt_smtp_port.text().strip() or "587")
        except ValueError: port = 587
        con = get_connection(); cur = con.cursor(); self._ensure_email_table(cur)
        cur.execute("SELECT id FROM email_settings LIMIT 1"); row = cur.fetchone()
        reminder_ore = int(self.cmb_reminder.currentText())
        data = (
            self.txt_smtp_host.text().strip(), port,
            self.txt_smtp_user.text().strip(), encrypt(self.txt_smtp_pass.text()),
            1 if self.chk_smtp_ssl.isChecked() else 0,
            1 if self.chk_notificari.isChecked() else 0,
            reminder_ore,
        )
        if row:
            cur.execute("UPDATE email_settings SET smtp_host=?,smtp_port=?,smtp_user=?,smtp_password=?,smtp_ssl=?,notificari_active=?,reminder_ore=? WHERE id=?", (*data, row[0]))
        else:
            cur.execute("INSERT INTO email_settings (smtp_host,smtp_port,smtp_user,smtp_password,smtp_ssl,notificari_active,reminder_ore) VALUES (?,?,?,?,?,?,?)", data)
        con.commit(); con.close()
        log_action(self.parent.logged_email, "Salvare setari email", "")
        show_toast(self.parent, "Setarile email au fost salvate")

    def test_email_connection(self):
        from ui.services.notification_service import test_connection
        self.lbl_test_result.setText("Se testeaza conexiunea...")
        try: port = int(self.txt_smtp_port.text().strip() or "587")
        except ValueError: port = 587
        settings = {
            "host": self.txt_smtp_host.text().strip(), "port": port,
            "user": self.txt_smtp_user.text().strip(), "password": self.txt_smtp_pass.text(),
            "ssl": self.chk_smtp_ssl.isChecked(),
        }
        ok, err = test_connection(settings)
        if ok:
            self.lbl_test_result.setText("✅ Conexiune reusita!")
            self.lbl_test_result.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        else:
            self.lbl_test_result.setText(f"❌ Eroare: {err}")
            self.lbl_test_result.setStyleSheet("color: #ef4444; font-size: 12px;")

    # =========================================================
    # WHATSAPP & SMS — tabele comune
    # =========================================================
    def _ensure_notif_tables(self, cur):
        cur.execute("""CREATE TABLE IF NOT EXISTS whatsapp_settings (
            id INTEGER PRIMARY KEY, activ INTEGER DEFAULT 0,
            phone_id TEXT DEFAULT '', token TEXT DEFAULT '',
            tmpl_finalizat TEXT DEFAULT 'lucrare_finalizata',
            tmpl_reminder  TEXT DEFAULT 'reminder_programare'
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sms_settings (
            id INTEGER PRIMARY KEY, activ INTEGER DEFAULT 0,
            provider TEXT DEFAULT 'SMSAPI.ro',
            api_key TEXT DEFAULT '', api_secret TEXT DEFAULT '',
            sender TEXT DEFAULT '',
            tmpl_finalizat TEXT DEFAULT 'Lucrarea la {vehicul} este finalizata. Va asteptam!',
            tmpl_reminder  TEXT DEFAULT 'Reminder: programare maine la {ora}. {firma}'
        )""")

    # ── WhatsApp ──────────────────────────────────────────────
    def load_wa_settings(self):
        con = get_connection(); cur = con.cursor()
        self._ensure_notif_tables(cur); con.commit()
        cur.execute("SELECT activ, phone_id, token, tmpl_finalizat, tmpl_reminder FROM whatsapp_settings LIMIT 1")
        row = cur.fetchone(); con.close()
        if row:
            self.chk_wa_activ.setChecked(bool(row[0]))
            self.txt_wa_phone_id.setText(row[1] or "")
            self.txt_wa_token.setText(decrypt(row[2] or ""))
            self.txt_wa_tmpl_finalizat.setText(row[3] or "")
            self.txt_wa_tmpl_reminder.setText(row[4] or "")

    def save_wa_settings(self):
        con = get_connection(); cur = con.cursor(); self._ensure_notif_tables(cur)
        cur.execute("SELECT id FROM whatsapp_settings LIMIT 1"); row = cur.fetchone()
        data = (
            1 if self.chk_wa_activ.isChecked() else 0,
            self.txt_wa_phone_id.text().strip(),
            encrypt(self.txt_wa_token.text().strip()),
            self.txt_wa_tmpl_finalizat.text().strip(),
            self.txt_wa_tmpl_reminder.text().strip(),
        )
        if row:
            cur.execute("UPDATE whatsapp_settings SET activ=?,phone_id=?,token=?,tmpl_finalizat=?,tmpl_reminder=? WHERE id=?", (*data, row[0]))
        else:
            cur.execute("INSERT INTO whatsapp_settings (activ,phone_id,token,tmpl_finalizat,tmpl_reminder) VALUES (?,?,?,?,?)", data)
        con.commit(); con.close()
        log_action(self.parent.logged_email, "Salvare setari WhatsApp", "")
        show_toast(self.parent, "Setarile WhatsApp au fost salvate")

    # ── SMS ───────────────────────────────────────────────────
    def _update_sms_help(self):
        p = self.cmb_sms_provider.currentText()
        links = {
            "SMSAPI.ro": "Obtii API Token din: <a href='https://smsapi.ro'>smsapi.ro</a> → Setari cont → API. Campul 'Auth Token' nu este necesar.",
            "Twilio":    "Obtii credentialele din: <a href='https://console.twilio.com'>console.twilio.com</a> → Account SID + Auth Token.",
            "TextMagic": "Obtii credentialele din: <a href='https://my.textmagic.com'>my.textmagic.com</a> → API → Username + API Key.",
        }
        self.lbl_sms_help.setText(links.get(p, ""))

    def load_sms_settings(self):
        con = get_connection(); cur = con.cursor()
        self._ensure_notif_tables(cur); con.commit()
        cur.execute("SELECT activ, provider, api_key, api_secret, sender, tmpl_finalizat, tmpl_reminder FROM sms_settings LIMIT 1")
        row = cur.fetchone(); con.close()
        if row:
            self.chk_sms_activ.setChecked(bool(row[0]))
            idx = self.cmb_sms_provider.findText(row[1] or "SMSAPI.ro")
            if idx >= 0: self.cmb_sms_provider.setCurrentIndex(idx)
            self.txt_sms_key.setText(decrypt(row[2] or ""))
            self.txt_sms_secret.setText(decrypt(row[3] or ""))
            self.txt_sms_sender.setText(row[4] or "")
            self.txt_sms_tmpl_finalizat.setText(row[5] or "")
            self.txt_sms_tmpl_reminder.setText(row[6] or "")

    def save_sms_settings(self):
        con = get_connection(); cur = con.cursor(); self._ensure_notif_tables(cur)
        cur.execute("SELECT id FROM sms_settings LIMIT 1"); row = cur.fetchone()
        data = (
            1 if self.chk_sms_activ.isChecked() else 0,
            self.cmb_sms_provider.currentText(),
            encrypt(self.txt_sms_key.text().strip()),
            encrypt(self.txt_sms_secret.text().strip()),
            self.txt_sms_sender.text().strip(),
            self.txt_sms_tmpl_finalizat.text().strip(),
            self.txt_sms_tmpl_reminder.text().strip(),
        )
        if row:
            cur.execute("UPDATE sms_settings SET activ=?,provider=?,api_key=?,api_secret=?,sender=?,tmpl_finalizat=?,tmpl_reminder=? WHERE id=?", (*data, row[0]))
        else:
            cur.execute("INSERT INTO sms_settings (activ,provider,api_key,api_secret,sender,tmpl_finalizat,tmpl_reminder) VALUES (?,?,?,?,?,?,?)", data)
        con.commit(); con.close()
        log_action(self.parent.logged_email, "Salvare setari SMS", f"provider={self.cmb_sms_provider.currentText()}")
        show_toast(self.parent, "Setarile SMS au fost salvate")

    # =========================================================
    # BACKUP
    # =========================================================
    def load_backup_list(self):
        bm = BackupManager(); lista = bm.lista_backup_uri(); self.table_backup.setRowCount(0)
        for i, b in enumerate(lista):
            self.table_backup.insertRow(i)
            self.table_backup.setItem(i, 0, QTableWidgetItem(b["nume"]))
            self.table_backup.setItem(i, 1, QTableWidgetItem(b["data"]))
            self.table_backup.setItem(i, 2, QTableWidgetItem(str(b["size_kb"])))

    def face_backup_manual(self):
        bm = BackupManager(); ok, rezultat = bm.backup_manual()
        if ok: show_toast(self.parent, "Backup creat cu succes!"); self.load_backup_list()
        else:  show_toast(self.parent, f"Eroare backup: {rezultat}")

    def restaureaza_backup(self):
        row = self.table_backup.currentRow()
        if row < 0: show_toast(self.parent, "Selecteaza un backup din lista."); return
        nume = self.table_backup.item(row, 0).text(); path = f"backup/{nume}"
        from PyQt5.QtWidgets import QMessageBox
        rasp = QMessageBox.question(
            self, "Confirmare restaurare",
            f"Esti sigur ca vrei sa restaurezi:\n{nume}\n\nAplicatia se va reporni dupa restaurare.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if rasp != QMessageBox.Yes: return
        bm = BackupManager(); ok, mesaj = bm.restaureaza(path)
        if ok: show_toast(self.parent, "Restaurare reusita! Reporneste aplicatia.")
        else:  show_toast(self.parent, f"Eroare: {mesaj}")

    # =========================================================
    # CLOUD SYNC
    # =========================================================
    def _sync_now(self):
        self.lbl_sync_result.setText("⏳ Se sincronizeaza..."); self.btn_sync_now.setEnabled(False)
        import threading
        def do_sync():
            from sync_manager import sync_to_cloud; ok, mesaj = sync_to_cloud()
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            txt   = f"✅ {mesaj}" if ok else f"❌ {mesaj}"
            style = "color: #10b981; font-size: 12px;" if ok else "color: #ef4444; font-size: 12px;"
            QMetaObject.invokeMethod(self.lbl_sync_result, "setText",        Qt.QueuedConnection, Q_ARG(str, txt))
            QMetaObject.invokeMethod(self.lbl_sync_result, "setStyleSheet",  Qt.QueuedConnection, Q_ARG(str, style))
            self.btn_sync_now.setEnabled(True)
        threading.Thread(target=do_sync, daemon=True).start()

    def _restore_from_cloud(self):
        from PyQt5.QtWidgets import QMessageBox
        rasp = QMessageBox.question(
            self, "Confirmare restaurare",
            "Esti sigur ca vrei sa restaurezi datele din Cloud?\n\n"
            "Datele locale vor fi INLOCUITE cu cele din Supabase.\nAceasta actiune nu poate fi anulata!",
            QMessageBox.Yes | QMessageBox.No,
        )
        if rasp != QMessageBox.Yes: return
        self.lbl_restore_result.setText("⏳ Se descarca datele din Cloud..."); self.btn_restore_cloud.setEnabled(False)
        import threading
        def do_restore():
            from sync_manager import restore_from_cloud; ok, mesaj = restore_from_cloud()
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            txt   = f"✅ {mesaj}\nReporneste aplicatia!" if ok else f"❌ {mesaj}"
            style = "color: #10b981; font-size: 12px;" if ok else "color: #ef4444; font-size: 12px;"
            QMetaObject.invokeMethod(self.lbl_restore_result, "setText",       Qt.QueuedConnection, Q_ARG(str, txt))
            QMetaObject.invokeMethod(self.lbl_restore_result, "setStyleSheet", Qt.QueuedConnection, Q_ARG(str, style))
            self.btn_restore_cloud.setEnabled(True)
        threading.Thread(target=do_restore, daemon=True).start()

    # =========================================================
    # E-FACTURA
    # =========================================================
    def _ef_update_help(self):
        provider = self.cmb_ef_provider.currentText().lower()
        if provider == "smartbill":
            self.lbl_ef_help.setText("SmartBill: ws.smartbill.ro → Contul meu → Integrari API → copiaza API Token.")
        else:
            self.lbl_ef_help.setText("Oblio: app.oblio.eu → Setari → API → creeaza client OAuth2 si copiaza Client ID + Secret.")

    def _ef_toggle_activ(self, state):
        enabled = (state == Qt.Checked)
        for w in [self.txt_ef_cif, self.txt_ef_email, self.txt_ef_apikey,
                  self.cmb_ef_provider, self.chk_ef_test, self.btn_ef_test]:
            w.setEnabled(enabled)

    def load_efactura_settings(self):
        try:
            from efactura_service import get_efactura_setari; s = get_efactura_setari()
            idx = self.cmb_ef_provider.findText(s["provider"].capitalize(), Qt.MatchFixedString)
            self.cmb_ef_provider.setCurrentIndex(max(idx, 0))
            self.txt_ef_cif.setText(s["cif_firma"]); self.txt_ef_email.setText(s["email"])
            self.txt_ef_apikey.setText(s["api_key"])
            self.chk_ef_activ.setChecked(s["activ"]); self.chk_ef_test.setChecked(s["test_mode"])
            self._ef_toggle_activ(Qt.Checked if s["activ"] else Qt.Unchecked)
            self._ef_refresh_status(s)
        except Exception as e:
            self.lbl_ef_status_box.setText(f"Eroare incarcare setari E-Factura: {e}")

    def _ef_refresh_status(self, setari=None):
        if setari is None:
            from efactura_service import get_efactura_setari; setari = get_efactura_setari()
        if not setari["activ"]:
            self.lbl_ef_status_box.setStyleSheet("QLabel { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #6b7280; }")
            self.lbl_ef_status_box.setText("⬜  E-Factura dezactivata — facturile nu se trimit la ANAF.")
        elif not setari["email"] or not setari["api_key"]:
            self.lbl_ef_status_box.setStyleSheet("QLabel { background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #92400e; }")
            self.lbl_ef_status_box.setText("⚠️  E-Factura activata dar credentialele sunt incomplete.")
        else:
            mode = "MOD TEST" if setari["test_mode"] else "MOD PRODUCTIE"
            self.lbl_ef_status_box.setStyleSheet("QLabel { background: #f0fdf4; border: 1px solid #10b981; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #065f46; }")
            self.lbl_ef_status_box.setText(
                f"✅  E-Factura activata  ·  Provider: {setari['provider'].capitalize()}  ·  {mode}\n"
                f"CIF: {setari['cif_firma']}  ·  Cont: {setari['email']}"
            )

    def _ef_save(self):
        provider  = self.cmb_ef_provider.currentText().lower()
        email     = self.txt_ef_email.text().strip()
        api_key   = self.txt_ef_apikey.text().strip()
        cif_firma = self.txt_ef_cif.text().strip()
        activ     = self.chk_ef_activ.isChecked()
        test_mode = self.chk_ef_test.isChecked()
        if activ and (not email or not api_key or not cif_firma):
            self.lbl_ef_result.setText("⚠️  Completati toate campurile inainte de a activa E-Factura.")
            self.lbl_ef_result.setStyleSheet("color: #f59e0b; font-size: 12px;"); return
        try:
            from efactura_service import salveaza_efactura_setari
            salveaza_efactura_setari(provider, email, api_key, cif_firma, activ, test_mode)
        except Exception as e:
            self.lbl_ef_result.setText(f"❌  Eroare salvare: {e}")
            self.lbl_ef_result.setStyleSheet("color: #ef4444; font-size: 12px;"); return
        log_action(self.parent.logged_email, "Salvare setari E-Factura", f"provider={provider}, activ={activ}, test={test_mode}")
        self.lbl_ef_result.setText("✅  Setarile E-Factura au fost salvate.")
        self.lbl_ef_result.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        self._ef_refresh_status(); show_toast(self.parent, "Setari E-Factura salvate")

    def _ef_test_conexiune(self):
        provider_name = self.cmb_ef_provider.currentText().lower()
        email     = self.txt_ef_email.text().strip()
        api_key   = self.txt_ef_apikey.text().strip()
        cif       = self.txt_ef_cif.text().strip()
        test_mode = self.chk_ef_test.isChecked()
        if not email or not api_key:
            self.lbl_ef_result.setText("⚠️  Introduceti Email si API Key inainte de test.")
            self.lbl_ef_result.setStyleSheet("color: #f59e0b; font-size: 12px;"); return
        self.lbl_ef_result.setText("⏳  Se testeaza conexiunea...")
        self.lbl_ef_result.setStyleSheet("color: #6b7280; font-size: 12px;")
        self.btn_ef_test.setEnabled(False)
        import threading
        def do_test():
            try:
                from efactura_service import SmartBillProvider, OblioProvider
                prov = (SmartBillProvider if provider_name == "smartbill" else OblioProvider)(email, api_key, cif, test_mode)
                ok, mesaj = prov.test_conexiune()
            except Exception as e:
                ok, mesaj = False, str(e)
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            txt   = f"✅  {mesaj}" if ok else f"❌  {mesaj}"
            style = "color: #10b981; font-size: 12px; font-weight: bold;" if ok else "color: #ef4444; font-size: 12px;"
            QMetaObject.invokeMethod(self.lbl_ef_result, "setText",       Qt.QueuedConnection, Q_ARG(str, txt))
            QMetaObject.invokeMethod(self.lbl_ef_result, "setStyleSheet", Qt.QueuedConnection, Q_ARG(str, style))
            self.btn_ef_test.setEnabled(True)
        threading.Thread(target=do_test, daemon=True).start()

    # =========================================================
    # DATE FIRMA
    # =========================================================
    def load_data(self):
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT nume, cui, adresa, telefon, tva, reg_com, cont_bancar FROM firma LIMIT 1")
        row = cur.fetchone(); con.close()
        if row:
            self.f_nume.setText(row[0] or ""); self.f_cui.setText(row[1] or "")
            self.f_adresa.setText(row[2] or ""); self.f_tel.setText(row[3] or "")
            self.f_reg_com.setText(row[5] or "") if len(row) > 5 else None
            self.f_cont.setText(row[6] or "")   if len(row) > 6 else None
            self.txt_tva.setText(str(row[4]) if row[4] else "21")

    def save_data(self):
        from PyQt5.QtWidgets import QMessageBox
        nume  = self.f_nume.text().strip();   cui    = self.f_cui.text().strip()
        adresa   = self.f_adresa.text().strip();  tel     = self.f_tel.text().strip()
        reg_com  = self.f_reg_com.text().strip();  cont    = self.f_cont.text().strip()

        if cui and not _CUI_RE.match(cui):
            QMessageBox.warning(self.parent, "CUI invalid",
                                "CUI-ul firmei trebuie sa aiba formatul: RO12345678 sau 12345678 (2-10 cifre).")
            self.f_cui.setFocus()
            return

        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT id FROM firma LIMIT 1"); row = cur.fetchone()
        if row: cur.execute("UPDATE firma SET nume=?,cui=?,adresa=?,telefon=?,reg_com=?,cont_bancar=? WHERE id=?", (nume, cui, adresa, tel, reg_com, cont, row[0]))
        else:   cur.execute("INSERT INTO firma (nume, cui, adresa, telefon, tva, reg_com, cont_bancar) VALUES (?,?,?,?,?,?,?)", (nume, cui, adresa, tel, self.txt_tva.text(), reg_com, cont))
        con.commit(); con.close()
        show_toast(self.parent, "Datele firmei au fost salvate")

    # =========================================================
    # LIMBA
    # =========================================================
    def load_language(self):
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT limba FROM setari LIMIT 1"); row = cur.fetchone(); con.close()
        if row: self.cmb_lang.setCurrentIndex(1 if row[0] == "EN" else 0)

    def save_language(self):
        lang = "RO" if self.cmb_lang.currentIndex() == 0 else "EN"
        con = get_connection(); cur = con.cursor()
        cur.execute("DELETE FROM setari"); cur.execute("INSERT INTO setari (limba) VALUES (?)", (lang,))
        con.commit(); con.close()
        self.parent.app_language = lang; self.parent.apply_language()
        for page in [
            self.parent,
            getattr(self.parent, "page_dashboard",    None),
            getattr(self.parent, "page_clienti",      None),
            getattr(self.parent, "page_vehicule",     None),
            getattr(self.parent, "page_lucrari",      None),
            getattr(self.parent, "page_devize",       None),
            getattr(self.parent, "page_fisa_service", None),
        ]:
            if page and hasattr(page, "apply_language"): page.apply_language()
        self.apply_language(); show_toast(self.parent, "Limba a fost salvata")

    # =========================================================
    # APPLY LANGUAGE
    # =========================================================
    def apply_language(self):
        lang = self.parent.app_language
        if lang == "RO":
            self.f_nume.setPlaceholderText("Nume firma");  self.f_cui.setPlaceholderText("CUI")
            self.f_adresa.setPlaceholderText("Adresa");    self.f_tel.setPlaceholderText("Telefon")
            self.btn_save.setText("💾 Salveaza datele")
            self.cmb_lang.clear(); self.cmb_lang.addItems(["Romana", "Engleza"])
            self.btn_save_lang.setText("💾 Salveaza limba")
            self.lbl_tva.setText("TVA (%)");               self.txt_tva.setPlaceholderText("Introduceti TVA (%)")
            self.btn_save_tva.setText("💾 Salveaza TVA")
            self.lbl_tarif.setText("Tarif ora manopera (RON)"); self.txt_tarif.setPlaceholderText("Ex: 150")
            self.btn_save_tarif.setText("💾 Salveaza tarif")
            self.btn_change_pass.setText("🔐 Schimba parola"); self.btn_logout.setText("🔄 Schimba utilizator")
            self.table_users.setHorizontalHeaderLabels(["Email", "Rol", "Ultima logare", "Actiuni"])
            self.btn_add_user.setText("➕ Adauga utilizator")
            self.filter_user.setPlaceholderText("Filtru utilizator"); self.filter_date.setPlaceholderText("YYYY-MM-DD"); self.filter_btn.setText("Filtreaza")
            self.table_audit.setHorizontalHeaderLabels(["Utilizator", "Actiune", "Detalii", "Data"])
            self.lbl_backup_info.setText("Backup-uri disponibile:")
            self.btn_backup_manual.setText("💾 Backup manual acum"); self.btn_restaureaza.setText("♻️ Restaureaza selectat")
            self.table_backup.setHorizontalHeaderLabels(["Nume fisier", "Data", "Marime (KB)"])
        else:
            self.f_nume.setPlaceholderText("Company name"); self.f_cui.setPlaceholderText("VAT ID")
            self.f_adresa.setPlaceholderText("Address");    self.f_tel.setPlaceholderText("Phone")
            self.btn_save.setText("💾 Save data")
            self.cmb_lang.clear(); self.cmb_lang.addItems(["Romanian", "English"])
            self.btn_save_lang.setText("💾 Save language")
            self.lbl_tva.setText("VAT (%)");               self.txt_tva.setPlaceholderText("Enter VAT (%)")
            self.btn_save_tva.setText("💾 Save VAT")
            self.lbl_tarif.setText("Labor rate (RON/hour)"); self.txt_tarif.setPlaceholderText("Ex: 150")
            self.btn_save_tarif.setText("💾 Save rate")
            self.btn_change_pass.setText("🔐 Change password"); self.btn_logout.setText("🔄 Switch user")
            self.table_users.setHorizontalHeaderLabels(["Email", "Role", "Last login", "Actions"])
            self.btn_add_user.setText("➕ Add user")
            self.filter_user.setPlaceholderText("User filter"); self.filter_date.setPlaceholderText("YYYY-MM-DD"); self.filter_btn.setText("Filter")
            self.table_audit.setHorizontalHeaderLabels(["User", "Action", "Details", "Date"])
            self.lbl_backup_info.setText("Available backups:")
            self.btn_backup_manual.setText("💾 Manual backup now"); self.btn_restaureaza.setText("♻️ Restore selected")
            self.table_backup.setHorizontalHeaderLabels(["File name", "Date", "Size (KB)"])