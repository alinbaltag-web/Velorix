from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QPushButton, QStackedWidget, QTableWidgetSelectionRange, QLabel
)
from PyQt5.QtCore import Qt, QSize, QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QShortcut

from database import init_db, backup_database, get_permisiuni
from assets.translations import translations

from ui.pages.page_dashboard import PageDashboard
from ui.pages.page_clienti import PageClienti
from ui.pages.page_vehicule import PageVehicule
from ui.pages.page_lucrari import PageLucrari
from ui.pages.page_devize import PageDevize
from ui.pages.page_setari import PageSetari
from ui.pages.page_fisa_service import PageFisaService
from ui.pages.page_istoric_lucrari import PageIstoricLucrari
from ui.pages.page_rapoarte import PageRapoarte
from ui.pages.page_stocuri import PageStocuri
from ui.pages.page_facturare import PageFacturare
from ui.utils_toast import show_toast
from ui.widgets.checkbox_header import CheckBoxHeader
from ui.session_manager import SessionManager
from notification_manager import NotificationManager
from ui.widgets.notification_bell import NotificationBell
from sync_manager import SyncManager, init_sync_queue
from ui.widgets.sync_indicator import SyncIndicator


class MainWindow(QMainWindow):
    def __init__(self, role, email):
        super().__init__()
        self.role = role
        self.logged_email = email
        self.permisiuni = get_permisiuni(role)

        if not SessionManager.is_logged_in():
            from ui.login_window import LoginWindow
            self.login = LoginWindow()
            self.login.show()
            self.close()
            return

        with open("styles/style.qss", "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

        from PyQt5.QtWidgets import QApplication
        QApplication.setStyle("Fusion")

        import ctypes
        try:
            ctypes.windll.uxtheme.SetPreferredAppMode(1)
        except:
            pass

        self.setWindowTitle("VELORIX – Management Service")
        import os, sys
        _base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _ico = os.path.join(_base, "assets", "velorix.ico")
        if not os.path.exists(_ico):
            _ico = os.path.join(_base, "assets", "logo_velorix.png")
        self.setWindowIcon(QIcon(_ico))
        self.setMinimumSize(1024, 600)
        self.showMaximized()

        backup_database()
        init_sync_queue()
        self.sync_manager = SyncManager(interval_secunde=30)

        # Helper thread-safe pentru refresh UI dupa sync cu date noi din cloud
        class _SyncRefreshHelper(QObject):
            refresh_needed = pyqtSignal(int)
        self._sync_refresh_signal = _SyncRefreshHelper(self)
        self._sync_refresh_signal.refresh_needed.connect(self._on_sync_data_changed)

        from database import get_connection
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT limba FROM setari LIMIT 1")
        row = cur.fetchone()
        con.close()

        self.app_language = "RO" if not row or row[0] == "RO" else "EN"
        self.translations = translations

        self.selected_client_id = None
        self.selected_vehicul_id = None

        central = QWidget()
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        self.sidebar = self._create_sidebar()
        layout.addWidget(self.sidebar)

        self.notif_bell = NotificationBell(self.sidebar)
        self.notif_bell.move(194, 10)
        self.notif_bell.raise_()

        # Ascunde butoane fara permisiuni
        if not self.permisiuni.get("fisa_service", False):
            self.btn_fisa_service.hide()
        if not self.permisiuni.get("lucrari", False):
            self.btn_lucrari.hide()
        if not self.permisiuni.get("devize", False):
            self.btn_devize.hide()
        if not self.permisiuni.get("istoric", False):
            self.btn_istoric.hide()
        if not self.permisiuni.get("rapoarte", False):
            self.btn_rapoarte.hide()
        if not self.permisiuni.get("stocuri_vizualizare", False):
            self.btn_stocuri.hide()
        if not self.permisiuni.get("setari", False):
            self.btn_setari.hide()
        if self.role not in ("administrator", "receptie"):
            self.btn_facturare.hide()

        self.pages = QStackedWidget()
        layout.addWidget(self.pages, stretch=1)

        # ── Instantiere pagini ──
        self.page_dashboard = PageDashboard(self)
        self.page_clienti = PageClienti(self)
        self.page_vehicule = PageVehicule(self)
        self.page_fisa_service = PageFisaService(self)

        try:
            self.page_lucrari = PageLucrari(self)
        except Exception as e:
            import traceback
            with open("eroare_lucrari.txt", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            print("EROARE PageLucrari:")
            traceback.print_exc()
            raise

        self.page_istoric   = PageIstoricLucrari(self)
        self.page_devize    = PageDevize(self)
        self.page_rapoarte  = PageRapoarte(self)
        self.page_stocuri   = PageStocuri()
        self.page_setari    = PageSetari(self)
        self.page_facturare = PageFacturare(self)

        # ── Adaugare in stack ──
        self.pages.addWidget(self.page_dashboard)
        self.pages.addWidget(self.page_clienti)
        self.pages.addWidget(self.page_vehicule)
        self.pages.addWidget(self.page_fisa_service)
        self.pages.addWidget(self.page_lucrari)
        self.pages.addWidget(self.page_devize)
        self.pages.addWidget(self.page_istoric)
        self.pages.addWidget(self.page_rapoarte)
        self.pages.addWidget(self.page_stocuri)
        self.pages.addWidget(self.page_setari)
        self.pages.addWidget(self.page_facturare)

        # Referinte tabele
        self.table_clienti  = self.page_clienti.table_clienti
        self.table_vehicule = self.page_vehicule.table_vehicule
        self.table_lucrari  = self.page_lucrari.table_lucrari
        self.table_devize   = self.page_devize.table_devize

        self.page_devize.table_devize.horizontalHeader().clicked.connect(
            self.toggle_all_devize
        )

        self.pages.setCurrentWidget(self.page_dashboard)
        self.apply_language()
        self._setup_shortcuts()

    # ---------------------------------------------------------
    # SCURTATURI TASTATURA
    # ---------------------------------------------------------
    def _setup_shortcuts(self):
        # Navigare intre pagini
        QShortcut(QKeySequence("Alt+1"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_dashboard, self.page_dashboard))
        QShortcut(QKeySequence("Alt+2"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_clienti, self.page_clienti))
        QShortcut(QKeySequence("Alt+3"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_vehicule, self.page_vehicule))
        QShortcut(QKeySequence("Alt+4"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_lucrari, self.page_lucrari))
        QShortcut(QKeySequence("Alt+5"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_devize, self.page_devize))
        QShortcut(QKeySequence("Alt+6"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_stocuri, self.page_stocuri))
        QShortcut(QKeySequence("Alt+7"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_rapoarte, self.page_rapoarte))
        QShortcut(QKeySequence("Alt+8"), self).activated.connect(
            lambda: self._activate_sidebar(self.btn_facturare, self.page_facturare))

        # Adaugare rapida (Ctrl+N) — actioneaza butonul "Adauga" din pagina curenta
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._shortcut_add)

        # Refresh (F5)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._shortcut_refresh)

        # Focus pe cautare (Ctrl+F)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._shortcut_focus_search)

    def _shortcut_add(self):
        page = self.pages.currentWidget()
        if page is self.page_clienti and hasattr(page, "btn_add"):
            page.btn_add.click()
        elif page is self.page_vehicule and hasattr(page, "btn_add"):
            page.btn_add.click()
        elif page is self.page_lucrari and hasattr(page, "btn_add_lucrare"):
            page.btn_add_lucrare.click()
        elif page is self.page_stocuri and hasattr(page, "btn_adauga"):
            page.btn_adauga.click()
        elif page is self.page_devize and hasattr(page, "btn_deviz_nou"):
            page.btn_deviz_nou.click()

    def _shortcut_refresh(self):
        page = self.pages.currentWidget()
        if page is self.page_dashboard:
            self.page_dashboard.refresh_dashboard()
        elif page is self.page_clienti:
            self.page_clienti.load_clienti()
        elif page is self.page_vehicule:
            self.page_vehicule.load_vehicule()
        elif page is self.page_lucrari:
            self.page_lucrari.load_lucrari()
        elif page is self.page_devize:
            self.page_devize.load_devize()
        elif page is self.page_stocuri:
            self.page_stocuri.load_data()
        elif page is self.page_facturare:
            self.page_facturare.load_data()

    def _shortcut_focus_search(self):
        page = self.pages.currentWidget()
        for attr in ("search_client", "search_vehicul", "input_search", "txt_search"):
            widget = getattr(page, attr, None)
            if widget:
                widget.setFocus()
                widget.selectAll()
                break

    # ---------------------------------------------------------
    # LIMBA
    # ---------------------------------------------------------
    def apply_language(self):
        t = self.translations[self.app_language]

        self.btn_dashboard.setText(t["dashboard"])
        self.btn_clienti.setText(t["clienti"])
        self.btn_vehicule.setText(t["vehicule"])
        self.btn_fisa_service.setText("Fisa Service" if self.app_language == "RO" else "Service Sheet")
        self.btn_lucrari.setText(t["lucrari"])
        self.btn_devize.setText(t["devize"])
        self.btn_istoric.setText("Istoric lucrari" if self.app_language == "RO" else "Work History")
        self.btn_rapoarte.setText("Rapoarte" if self.app_language == "RO" else "Reports")
        self.btn_setari.setText(t["setari"])
        self.btn_stocuri.setText("Stocuri" if self.app_language == "RO" else "Stock")
        self.btn_facturare.setText("Facturare" if self.app_language == "RO" else "Invoicing")

        self.page_dashboard.apply_language()
        self.page_clienti.apply_language()
        self.page_vehicule.apply_language()
        self.page_lucrari.apply_language()
        self.page_devize.apply_language()
        self.page_istoric.apply_language()
        self.page_setari.apply_language()
        self.page_fisa_service.apply_language()
        self.page_rapoarte.apply_language()
        self.page_stocuri.apply_language(self.app_language)
        self.page_facturare.apply_language()

    # ---------------------------------------------------------
    # TVA
    # ---------------------------------------------------------
    def get_tva(self):
        from PyQt5.QtCore import QSettings
        settings = QSettings("ServiceMoto", "UI")
        return settings.value("cota_tva", 0.21, type=float)

    # ---------------------------------------------------------
    # SIDEBAR
    # ---------------------------------------------------------
    def _create_sidebar(self):
        frame = QFrame()
        frame.setFixedWidth(240)
        frame.setObjectName("sidebar")

        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 20, 0, 0)

        def btn(text, icon_path):
            b = QPushButton(text)
            b.setFixedHeight(50)
            b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True)
            b.setIcon(QIcon(icon_path))
            b.setIconSize(QSize(20, 20))
            return b

        self.btn_dashboard    = btn("Dashboard",       "assets/icons/home.svg")
        self.btn_clienti      = btn("Clienti",          "assets/icons/users.svg")
        self.btn_vehicule     = btn("Vehicule",          "assets/icons/bike.svg")
        self.btn_fisa_service = btn("Fisa Service",     "assets/icons/document.svg")
        self.btn_lucrari      = btn("Lucrari",           "assets/icons/tools.svg")
        self.btn_devize       = btn("Devize",             "assets/icons/document.svg")
        self.btn_facturare    = btn("Facturare",          "assets/icons/check.svg")
        self.btn_istoric      = btn("Istoric lucrari",   "assets/icons/history.svg")
        self.btn_rapoarte     = btn("Rapoarte",           "assets/icons/progress.svg")
        self.btn_stocuri      = btn("Stocuri",            "assets/icons/tools.svg")
        self.btn_setari       = btn("Setari",             "assets/icons/settings.svg")

        self.sidebar_buttons = [
            self.btn_dashboard, self.btn_clienti, self.btn_vehicule,
            self.btn_lucrari, self.btn_fisa_service, self.btn_devize,
            self.btn_facturare, self.btn_istoric, self.btn_rapoarte,
            self.btn_stocuri, self.btn_setari,
        ]

        self.btn_dashboard.clicked.connect(
            lambda: self._activate_sidebar(self.btn_dashboard, self.page_dashboard))
        self.btn_clienti.clicked.connect(
            lambda: self._activate_sidebar(self.btn_clienti, self.page_clienti))
        self.btn_vehicule.clicked.connect(
            lambda: self._activate_sidebar(self.btn_vehicule, self.page_vehicule))
        self.btn_fisa_service.clicked.connect(
            lambda: self._activate_sidebar(self.btn_fisa_service, self.page_fisa_service))
        self.btn_lucrari.clicked.connect(
            lambda: self._activate_sidebar(self.btn_lucrari, self.page_lucrari))
        self.btn_devize.clicked.connect(
            lambda: self._activate_sidebar(self.btn_devize, self.page_devize))
        self.btn_facturare.clicked.connect(
            lambda: self._activate_sidebar(self.btn_facturare, self.page_facturare))
        self.btn_istoric.clicked.connect(
            lambda: self._activate_sidebar(self.btn_istoric, self.page_istoric))
        self.btn_rapoarte.clicked.connect(
            lambda: self._activate_sidebar(self.btn_rapoarte, self.page_rapoarte))
        self.btn_stocuri.clicked.connect(
            lambda: self._activate_sidebar(self.btn_stocuri, self.page_stocuri))
        self.btn_setari.clicked.connect(
            lambda: self._activate_sidebar(self.btn_setari, self.page_setari))

        for b in self.sidebar_buttons:
            layout.addWidget(b)

        layout.addStretch()

        # ── Separator subtire deasupra indicatorului ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.07); border: none;")
        layout.addWidget(sep)

        # ── Sync indicator ──
        self.sync_indicator = SyncIndicator(frame, self.sync_manager)
        self.sync_manager.on_status_change = (
            lambda s, e=None: self.sync_indicator.update_status(s, e)
        )
        # Callback date noi din cloud — thread-safe prin signal Qt
        self.sync_manager.on_data_changed = (
            lambda count: self._sync_refresh_signal.refresh_needed.emit(count)
        )
        layout.addWidget(self.sync_indicator)

        self.sync_manager.start()
        return frame

    # ---------------------------------------------------------
    # ACTIVARE PAGINI
    # ---------------------------------------------------------
    def _activate_sidebar(self, button, page):
        blocaje = {
            self.btn_fisa_service: "fisa_service",
            self.btn_lucrari:      "lucrari",
            self.btn_devize:       "devize",
            self.btn_istoric:      "istoric",
            self.btn_rapoarte:     "rapoarte",
            self.btn_stocuri:      "stocuri_vizualizare",
            self.btn_setari:       "setari",
        }
        if button in blocaje:
            sectiune = blocaje[button]
            if not self.permisiuni.get(sectiune, False):
                show_toast(self, "Nu ai acces la aceasta sectiune.")
                return

        for btn in self.sidebar_buttons:
            btn.setChecked(btn is button)

        self.pages.setCurrentWidget(page)

        if page is self.page_dashboard:
            NotificationManager.genereaza_notificari()
            self.page_dashboard.refresh_dashboard()
            self.notif_bell.refresh_count()

        if page is self.page_clienti:
            self.page_clienti.load_clienti()

        if page is self.page_vehicule:
            self.page_vehicule.load_vehicule()

        if page is self.page_devize:
            self.page_devize.selected_client_id = None
            self.page_devize.selected_vehicul_id = None
            self.page_devize.load_devize()

        if page is self.page_fisa_service:
            self.page_fisa_service.reincarca_lucrari_din_db()

        if page is self.page_istoric:
            if self.selected_vehicul_id:
                self.page_istoric.load_istoric(self.selected_vehicul_id)
            else:
                show_toast(self, "Selecteaza un vehicul.")

        if page is self.page_vehicule:
            if self.app_language == "RO":
                self.page_vehicule.lbl_client.setText(
                    "Client selectat: -" if not self.selected_client_id
                    else f"Client selectat: ID {self.selected_client_id}")
            else:
                self.page_vehicule.lbl_client.setText(
                    "Selected client: -" if not self.selected_client_id
                    else f"Selected client: ID {self.selected_client_id}")
            self.page_vehicule.load_vehicule()

        if page is self.page_facturare:
            self.page_facturare.load_data()

    # ---------------------------------------------------------
    # SELECTARE CLIENT
    # ---------------------------------------------------------
    def select_client(self, row, col):
        t = self.page_clienti.table_clienti
        id_item = t.item(row, 1)
        if not id_item:
            return

        id_client = int(id_item.text())

        if self.selected_client_id == id_client:
            self.selected_client_id = None
            if self.app_language == "RO":
                self.page_vehicule.lbl_client.setText("Client selectat: -")
            else:
                self.page_vehicule.lbl_client.setText("Selected client: -")
            self.page_vehicule.load_vehicule()
            self.page_devize.selected_client_id = None
            self.page_devize.selected_vehicul_id = None
            self.page_devize.load_devize()
            self.page_fisa_service.txt_solicitari.clear()
            self.page_fisa_service.txt_defecte.clear()
            self.page_fisa_service.txt_observatii.clear()
            self.page_fisa_service.txt_km.clear()
            self.page_lucrari.table_lucrari.clearContents()
            self.page_lucrari.table_lucrari.setRowCount(0)
            return

        self.selected_client_id = id_client

        nume = t.item(row, 3).text()
        if self.app_language == "RO":
            self.page_vehicule.lbl_client.setText(f"Client selectat: {nume} (ID {id_client})")
        else:
            self.page_vehicule.lbl_client.setText(f"Selected client: {nume} (ID {id_client})")

        self.page_vehicule.load_vehicule()
        self.page_devize.selected_client_id = id_client
        self.page_devize.selected_vehicul_id = self.selected_vehicul_id
        self.page_devize.load_devize()

    # ---------------------------------------------------------
    # SELECTARE VEHICUL
    # ---------------------------------------------------------
    def select_vehicul(self, row, col):
        table = self.page_vehicule.table_vehicule
        id_item = table.item(row, 1)
        if not id_item:
            return

        id_vehicul = int(id_item.text())

        if self.selected_vehicul_id == id_vehicul:
            self.selected_vehicul_id = None
            if self.app_language == "RO":
                self.page_lucrari.lbl_vehicul.setText("Vehicul selectat: -")
            else:
                self.page_lucrari.lbl_vehicul.setText("Selected vehicle: -")
            self.page_lucrari.selected_vehicul_id = None
            self.page_lucrari.load_lucrari()
            self.page_devize.selected_vehicul_id = None
            self.page_devize.load_devize()
            self.page_fisa_service.txt_solicitari.clear()
            self.page_fisa_service.txt_defecte.clear()
            self.page_fisa_service.txt_observatii.clear()
            self.page_fisa_service.txt_km.clear()
            self.page_lucrari.table_lucrari.clearContents()
            self.page_lucrari.table_lucrari.setRowCount(0)
            return

        self.selected_vehicul_id = id_vehicul

        # Citim marca/model si clientul vehiculului din DB
        from database import get_connection
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT v.id_client, v.marca, v.model, c.nume
            FROM vehicule v
            LEFT JOIN clienti c ON c.id = v.id_client
            WHERE v.id = ?
        """, (id_vehicul,))
        vrow = cur.fetchone()
        con.close()

        marca_model = f"{vrow[1] or ''} {vrow[2] or ''}".strip() if vrow else f"ID {id_vehicul}"

        # Auto-selectare client daca nu este deja selectat
        if vrow and vrow[0] and not self.selected_client_id:
            self.selected_client_id = vrow[0]
            client_name = vrow[3] or f"ID {vrow[0]}"
            if self.app_language == "RO":
                self.page_vehicule.lbl_client.setText(f"Client selectat: {client_name} (ID {vrow[0]})")
            else:
                self.page_vehicule.lbl_client.setText(f"Selected client: {client_name} (ID {vrow[0]})")

        self.page_lucrari.selected_vehicul_id = id_vehicul
        self.page_lucrari.set_vehicul(id_vehicul, marca_model)

        if self.app_language == "RO":
            self.page_lucrari.lbl_vehicul.setText(f"Vehicul selectat: {marca_model}")
        else:
            self.page_lucrari.lbl_vehicul.setText(f"Selected vehicle: {marca_model}")

        self.page_lucrari.load_lucrari()
        self.page_devize.selected_vehicul_id = id_vehicul
        self.page_devize.selected_client_id = self.selected_client_id
        self.page_devize.load_devize()

    # ---------------------------------------------------------
    # DESELECTARE CLIENT
    # ---------------------------------------------------------
    def deselect_client(self):
        self.selected_client_id = None
        if self.app_language == "RO":
            self.page_vehicule.lbl_client.setText("Client selectat: -")
        else:
            self.page_vehicule.lbl_client.setText("Selected client: -")
        self.page_vehicule.load_vehicule()
        self.page_devize.selected_client_id = None
        self.page_devize.selected_vehicul_id = None
        self.page_devize.load_devize()
        self.page_fisa_service.txt_solicitari.clear()
        self.page_fisa_service.txt_defecte.clear()
        self.page_fisa_service.txt_observatii.clear()
        self.page_fisa_service.txt_km.clear()
        self.page_lucrari.table_lucrari.clearContents()
        self.page_lucrari.table_lucrari.setRowCount(0)

    # ---------------------------------------------------------
    # REFRESH DUPA SYNC CU DATE NOI DIN CLOUD
    # ---------------------------------------------------------
    def _on_sync_data_changed(self, pulled_count):
        """
        Apelat pe main thread dupa un sync care a adus date noi din cloud.
        Reincarca paginile vizibile pentru a afisa datele actualizate.
        """
        try:
            self.page_dashboard.refresh_dashboard()
        except Exception:
            pass
        try:
            self.page_clienti.load_clienti()
        except Exception:
            pass
        try:
            self.page_vehicule.load_vehicule()
        except Exception:
            pass
        try:
            self.page_devize.load_devize()
        except Exception:
            pass
        try:
            self.page_stocuri.load_stoc()
        except Exception:
            pass
        if self.selected_vehicul_id:
            try:
                self.page_lucrari.load_lucrari()
            except Exception:
                pass
        show_toast(self, f"Sync: {pulled_count} inregistrari noi preluate din cloud")

    # ---------------------------------------------------------
    # TOGGLE SELECT ALL
    # ---------------------------------------------------------
    def toggle_all_clienti(self, checked):
        t = self.page_clienti.table_clienti
        for r in range(t.rowCount()):
            i = t.item(r, 0)
            if i:
                i.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                if checked:
                    t.selectRow(r)
                else:
                    t.setRangeSelected(
                        QTableWidgetSelectionRange(r, 0, r, t.columnCount() - 1), False)
        t.viewport().update()

    def toggle_all_vehicule(self, checked):
        t = self.page_vehicule.table_vehicule
        for r in range(t.rowCount()):
            i = t.item(r, 0)
            if i:
                i.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                if checked:
                    t.selectRow(r)
                else:
                    t.setRangeSelected(
                        QTableWidgetSelectionRange(r, 0, r, t.columnCount() - 1), False)
        t.viewport().update()

    def toggle_all_lucrari(self, checked):
        t = self.page_lucrari.table_lucrari
        for r in range(t.rowCount()):
            i = t.item(r, 0)
            if i:
                i.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                if checked:
                    t.selectRow(r)
                else:
                    t.setRangeSelected(
                        QTableWidgetSelectionRange(r, 0, r, t.columnCount() - 1), False)
        t.viewport().update()

    def toggle_all_devize(self, checked):
        t = self.page_devize.table_devize
        for r in range(t.rowCount()):
            i = t.item(r, 0)
            if i:
                i.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                if checked:
                    t.selectRow(r)
                else:
                    t.setRangeSelected(
                        QTableWidgetSelectionRange(r, 0, r, t.columnCount() - 1), False)
        t.viewport().update()

    # ---------------------------------------------------------
    # DESCHIDERE DEVIZ PDF
    # ---------------------------------------------------------
    def open_deviz_pdf(self, row, col):
        if col == 0:
            return

        t = self.page_devize.table_devize
        numar = t.item(row, 1).text()

        import os, subprocess, platform
        base = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(base)
        path = os.path.join(root, "Devize_pdf", f"{numar}.pdf")

        if not os.path.exists(path):
            return

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    # ---------------------------------------------------------
    # INCHIDERE
    # ---------------------------------------------------------
    def closeEvent(self, event):
        try:
            self.page_clienti.save_table_state()
            self.page_vehicule.save_table_state()
            self.page_lucrari.save_table_state()
            self.page_devize.save_table_state()
        except Exception as e:
            print("Eroare la salvarea starii tabelelor:", e)

        try:
            self.sync_manager.stop()
        except Exception:
            pass

        event.accept()