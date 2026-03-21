import csv
from ui.widgets.tab_export_contabil import TabExportContabil
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QFileDialog,
    QMessageBox, QStackedWidget, QDateEdit, QFrame,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from database import get_connection
from ui.utils_toast import show_toast
from ui.widgets.raport_mecanic_widget import RaportMecanicWidget


# ── Paleta Velorix ───────────────────────────────────────────
C_DARK   = "#0f2137"
C_BLUE   = "#1a4fa0"
C_ACCENT = "#2196F3"
C_LIGHT  = "#e8f0fe"
C_BORDER = "#c5d5ea"
C_GREY   = "#64748b"
C_GREYBG = "#f7f9fc"
C_WHITE  = "#ffffff"


# ── Identice cu PageSetari ───────────────────────────────────
from ui.widgets.nav_button import NavButton as _NavButton, NavGroup as _NavGroup


class PageRapoarte(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ════════════════════════════════════════════
        # PANOU STANG — navigare verticala
        # ════════════════════════════════════════════
        self._nav_panel = QFrame()
        self._nav_panel.setFixedWidth(210)
        self._nav_panel.setObjectName("rapoarteNav")
        self._nav_panel.setStyleSheet(f"""
            QFrame#rapoarteNav {{
                background: {C_WHITE};
                border-right: 1px solid {C_BORDER};
            }}
        """)

        nav_layout = QVBoxLayout(self._nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        nav_header = QLabel("  Rapoarte")
        nav_header.setFixedHeight(56)
        nav_header.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {C_DARK};"
            f"background: {C_WHITE}; padding-left: 16px;"
            f"border-bottom: 1px solid {C_BORDER};"
        )
        nav_layout.addWidget(nav_header)

        # ── Grup: Financiar ──
        grp_fin = _NavGroup("Financiar")
        self.nav_venituri = _NavButton("💰", "Venituri")
        grp_fin.add_button(self.nav_venituri)
        nav_layout.addWidget(grp_fin)

        # ── Grup: Activitate ──
        grp_act = _NavGroup("Activitate")
        self.nav_lucrari  = _NavButton("🔧", "Lucrari")
        self.nav_clienti  = _NavButton("👥", "Clienti activi")
        self.nav_mecanic  = _NavButton("📊", "Raport mecanic")
        grp_act.add_button(self.nav_lucrari)
        grp_act.add_button(self.nav_clienti)
        grp_act.add_button(self.nav_mecanic)
        nav_layout.addWidget(grp_act)

        # ── Grup: Rapoarte ──
        grp_rap = _NavGroup("Rapoarte")
        self.nav_rclient  = _NavButton("👤", "Raport client")
        self.nav_rvehicul = _NavButton("🏍️", "Raport vehicul")
        grp_rap.add_button(self.nav_rclient)
        grp_rap.add_button(self.nav_rvehicul)
        nav_layout.addWidget(grp_rap)

        # ── Grup: Export ──
        grp_exp = _NavGroup("Export")
        self.nav_export = _NavButton("💼", "Export Contabil")
        grp_exp.add_button(self.nav_export)
        nav_layout.addWidget(grp_exp)

        nav_layout.addStretch()
        root.addWidget(self._nav_panel)

        # ════════════════════════════════════════════
        # PANOU DREPT — continut
        # ════════════════════════════════════════════
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {C_GREYBG};")
        root.addWidget(self._stack, 1)

        self.tab_venituri = QWidget(); self.tab_venituri.setStyleSheet("background: transparent;")
        self.tab_lucrari  = QWidget(); self.tab_lucrari.setStyleSheet("background: transparent;")
        self.tab_clienti  = QWidget(); self.tab_clienti.setStyleSheet("background: transparent;")
        self.tab_mecanic  = RaportMecanicWidget(self)
        self.tab_rclient  = QWidget(); self.tab_rclient.setStyleSheet("background: transparent;")
        self.tab_rvehicul = QWidget(); self.tab_rvehicul.setStyleSheet("background: transparent;")
        self.tab_export   = TabExportContabil(self)

        for page in [self.tab_venituri, self.tab_lucrari, self.tab_clienti,
                     self.tab_mecanic, self.tab_rclient, self.tab_rvehicul,
                     self.tab_export]:
            self._stack.addWidget(page)

        self._nav_btns = [
            self.nav_venituri, self.nav_lucrari, self.nav_clienti,
            self.nav_mecanic,  self.nav_rclient, self.nav_rvehicul,
            self.nav_export,
        ]
        for i, btn in enumerate(self._nav_btns):
            btn.clicked.connect(self._make_handler(i))

        self._activate_nav(0)

        self._init_tab_venituri()
        self._init_tab_lucrari()
        self._init_tab_clienti()
        self._init_tab_raport_client()
        self._init_tab_raport_vehicul()

    # ── Nav helpers ───────────────────────────────────────────
    def _make_handler(self, idx):
        return lambda: self._activate_nav(idx)

    def _activate_nav(self, idx):
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)

    # ── Stiluri butoane filtre ────────────────────────────────
    def _sp(self, btn):  # primary
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_BLUE}; color: white; border: none;
                border-radius: 6px; font-size: 12px; font-weight: 600;
                padding: 4px 14px; min-height: 30px;
            }}
            QPushButton:hover {{ background: {C_ACCENT}; }}
            QPushButton:pressed {{ background: {C_DARK}; }}
        """)

    def _ss(self, btn):  # secondary
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_LIGHT}; color: {C_BLUE};
                border: 1px solid {C_BORDER}; border-radius: 6px;
                font-size: 12px; padding: 4px 14px; min-height: 30px;
            }}
            QPushButton:hover {{ background: {C_BORDER}; }}
        """)

    def _container(self, parent_widget):
        lay = QVBoxLayout(parent_widget)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        return lay

    def _page_header(self, text, subtitle=""):
        w = QWidget()
        w.setStyleSheet(
            f"background: {C_WHITE}; border-bottom: 1px solid {C_BORDER};"
        )
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(2)
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {C_DARK};"
            f"background: transparent; border: none;"
        )
        lay.addWidget(lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(
                f"font-size: 12px; color: {C_GREY}; background: transparent; border: none;"
            )
            lay.addWidget(sub)
        return w

    # =========================================================
    # TAB VENITURI
    # =========================================================
    def _init_tab_venituri(self):
        layout = self._container(self.tab_venituri)
        layout.addWidget(self._page_header("💰  Venituri", "Situatia financiara pe perioade"))

        filtre = QHBoxLayout()
        self.cmb_perioada_v = QComboBox()
        self.cmb_perioada_v.addItems([
            "Luna curenta", "Luna trecuta", "Ultimele 3 luni",
            "Ultimele 6 luni", "Anul curent", "Toate"
        ])
        self.btn_refresh_v = QPushButton("🔄 Actualizeaza")
        self.btn_refresh_v.clicked.connect(self.load_venituri)
        self._sp(self.btn_refresh_v)
        self.btn_export_v = QPushButton("📥 Export CSV")
        self.btn_export_v.clicked.connect(lambda: self.export_csv(self.table_venituri, "venituri"))
        self._ss(self.btn_export_v)
        filtre.addWidget(QLabel("Perioada:"))
        filtre.addWidget(self.cmb_perioada_v)
        filtre.addWidget(self.btn_refresh_v)
        filtre.addWidget(self.btn_export_v)
        filtre.addStretch()
        layout.addLayout(filtre)

        self.lbl_total_venituri = QLabel("Total: 0.00 RON")
        self.lbl_total_venituri.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {C_BLUE};")
        layout.addWidget(self.lbl_total_venituri)

        self.table_venituri = QTableWidget()
        self.table_venituri.setColumnCount(6)
        self.table_venituri.setHorizontalHeaderLabels([
            "Nr. Deviz", "Data", "Client", "Vehicul", "Total fara TVA", "Total cu TVA"
        ])
        h = self.table_venituri.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_venituri.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_venituri.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_venituri.setAlternatingRowColors(True)
        layout.addWidget(self.table_venituri)
        self.load_venituri()

    def load_venituri(self):
        perioada = self.cmb_perioada_v.currentText()
        filtru_data = self._get_date_filter(perioada)
        con = get_connection(); cur = con.cursor()
        query = """
            SELECT d.numar, d.data, c.nume,
                   v.marca || ' ' || v.model,
                   d.total_manopera, d.total_general
            FROM devize d
            JOIN clienti c ON c.id = d.id_client
            JOIN vehicule v ON v.id = d.id_vehicul
        """
        params = []
        if filtru_data:
            query += " WHERE d.data >= ?"; params.append(filtru_data)
        query += " ORDER BY d.data DESC"
        cur.execute(query, params)
        rows = cur.fetchall(); con.close()
        self.table_venituri.setRowCount(0)
        total = 0.0
        for i, row in enumerate(rows):
            self.table_venituri.insertRow(i)
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val else "-")
                item.setTextAlignment(Qt.AlignCenter)
                self.table_venituri.setItem(i, j, item)
            try:
                total += float(row[5]) if row[5] else 0
            except:
                pass
        self.lbl_total_venituri.setText(f"Total perioada: {total:.2f} RON")

    # =========================================================
    # TAB LUCRARI
    # =========================================================
    def _init_tab_lucrari(self):
        layout = self._container(self.tab_lucrari)
        layout.addWidget(self._page_header("🔧  Lucrari", "Toate lucrarile din service"))

        filtre = QHBoxLayout()
        self.cmb_perioada_l = QComboBox()
        self.cmb_perioada_l.addItems([
            "Luna curenta", "Luna trecuta", "Ultimele 3 luni",
            "Ultimele 6 luni", "Anul curent", "Toate"
        ])
        self.cmb_status_l = QComboBox()
        self.cmb_status_l.addItems(["Toate", "In lucru", "Finalizate"])
        self.btn_refresh_l = QPushButton("🔄 Actualizeaza")
        self.btn_refresh_l.clicked.connect(self.load_lucrari_raport)
        self._sp(self.btn_refresh_l)
        self.btn_export_l = QPushButton("📥 Export CSV")
        self.btn_export_l.clicked.connect(lambda: self.export_csv(self.table_lucrari_r, "lucrari"))
        self._ss(self.btn_export_l)
        filtre.addWidget(QLabel("Perioada:"))
        filtre.addWidget(self.cmb_perioada_l)
        filtre.addWidget(QLabel("Status:"))
        filtre.addWidget(self.cmb_status_l)
        filtre.addWidget(self.btn_refresh_l)
        filtre.addWidget(self.btn_export_l)
        filtre.addStretch()
        layout.addLayout(filtre)

        self.lbl_total_lucrari = QLabel("Total lucrari: 0")
        self.lbl_total_lucrari.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {C_BLUE};")
        layout.addWidget(self.lbl_total_lucrari)

        self.table_lucrari_r = QTableWidget()
        self.table_lucrari_r.setColumnCount(7)
        self.table_lucrari_r.setHorizontalHeaderLabels([
            "ID", "Descriere", "Ore RAR", "Cost", "Status", "Vehicul", "Data"
        ])
        h = self.table_lucrari_r.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_lucrari_r.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_lucrari_r.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_lucrari_r.setAlternatingRowColors(True)
        layout.addWidget(self.table_lucrari_r)
        self.load_lucrari_raport()

    def load_lucrari_raport(self):
        perioada = self.cmb_perioada_l.currentText()
        filtru_data = self._get_date_filter(perioada)
        status = self.cmb_status_l.currentText()
        con = get_connection(); cur = con.cursor()
        query = """
            SELECT l.id, l.descriere, l.ore_rar, l.cost, l.status,
                   v.marca || ' ' || v.model, l.data
            FROM lucrari l JOIN vehicule v ON v.id = l.id_vehicul WHERE 1=1
        """
        params = []
        if filtru_data:
            query += " AND l.data >= ?"; params.append(filtru_data)
        if status == "In lucru":
            query += " AND l.status = 'in_lucru'"
        elif status == "Finalizate":
            query += " AND l.status = 'finalizat'"
        query += " ORDER BY l.id DESC"
        cur.execute(query, params)
        rows = cur.fetchall(); con.close()
        self.table_lucrari_r.setRowCount(0)
        for i, row in enumerate(rows):
            self.table_lucrari_r.insertRow(i)
            for j, val in enumerate(row):
                text = str(val) if val is not None else "-"
                if j == 4:
                    text = "In lucru" if val == "in_lucru" else "Finalizat"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.table_lucrari_r.setItem(i, j, item)
        self.lbl_total_lucrari.setText(f"Total lucrari: {len(rows)}")

    # =========================================================
    # TAB CLIENTI ACTIVI
    # =========================================================
    def _init_tab_clienti(self):
        layout = self._container(self.tab_clienti)
        layout.addWidget(self._page_header("👥  Clienti activi", "Lista clientilor cu activitate inregistrata"))

        filtre = QHBoxLayout()
        self.search_client_r = QLineEdit()
        self.search_client_r.setPlaceholderText("Cauta client...")
        self.search_client_r.textChanged.connect(self.load_clienti_raport)
        self.btn_export_c = QPushButton("📥 Export CSV")
        self.btn_export_c.clicked.connect(lambda: self.export_csv(self.table_clienti_r, "clienti"))
        self._ss(self.btn_export_c)
        filtre.addWidget(QLabel("Cauta:"))
        filtre.addWidget(self.search_client_r)
        filtre.addWidget(self.btn_export_c)
        filtre.addStretch()
        layout.addLayout(filtre)

        self.lbl_total_clienti = QLabel("Total clienti: 0")
        self.lbl_total_clienti.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {C_BLUE};")
        layout.addWidget(self.lbl_total_clienti)

        self.table_clienti_r = QTableWidget()
        self.table_clienti_r.setColumnCount(5)
        self.table_clienti_r.setHorizontalHeaderLabels([
            "Nume", "Telefon", "Email", "Nr. vehicule", "Nr. devize"
        ])
        h = self.table_clienti_r.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_clienti_r.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_clienti_r.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_clienti_r.setAlternatingRowColors(True)
        layout.addWidget(self.table_clienti_r)
        self.load_clienti_raport()

    def load_clienti_raport(self):
        search = self.search_client_r.text().strip().lower()
        con = get_connection(); cur = con.cursor()
        cur.execute("""
            SELECT c.nume, c.telefon, c.email,
                   COUNT(DISTINCT v.id), COUNT(DISTINCT d.id)
            FROM clienti c
            LEFT JOIN vehicule v ON v.id_client = c.id
            LEFT JOIN devize d ON d.id_client = c.id
            WHERE 1=1
        """ + (" AND (LOWER(c.nume) LIKE ? OR c.telefon LIKE ?)" if search else "") + """
            GROUP BY c.id ORDER BY COUNT(DISTINCT d.id) DESC
        """, (f"%{search}%", f"%{search}%") if search else ())
        rows = cur.fetchall(); con.close()
        self.table_clienti_r.setRowCount(0)
        for i, row in enumerate(rows):
            self.table_clienti_r.insertRow(i)
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "-")
                item.setTextAlignment(Qt.AlignCenter)
                self.table_clienti_r.setItem(i, j, item)
        self.lbl_total_clienti.setText(f"Total clienti: {len(rows)}")

    # =========================================================
    # TAB RAPORT CLIENT
    # =========================================================
    def _init_tab_raport_client(self):
        layout = self._container(self.tab_rclient)
        layout.addWidget(self._page_header("👤  Raport client", "Istoricul complet al unui client"))

        filtre = QHBoxLayout()
        filtre.addWidget(QLabel("Client:"))
        self.cmb_client_rc = QComboBox()
        self.cmb_client_rc.setMinimumWidth(220)
        self.cmb_client_rc.currentIndexChanged.connect(self._on_client_rc_changed)
        filtre.addWidget(self.cmb_client_rc)
        filtre.addSpacing(12)
        filtre.addWidget(QLabel("De la:"))
        self.date_de_la_rc = QDateEdit()
        self.date_de_la_rc.setCalendarPopup(True)
        self.date_de_la_rc.setDisplayFormat("dd.MM.yyyy")
        self.date_de_la_rc.setDate(QDate.currentDate().addMonths(-3))
        filtre.addWidget(self.date_de_la_rc)
        filtre.addWidget(QLabel("Pana la:"))
        self.date_pana_rc = QDateEdit()
        self.date_pana_rc.setCalendarPopup(True)
        self.date_pana_rc.setDisplayFormat("dd.MM.yyyy")
        self.date_pana_rc.setDate(QDate.currentDate())
        filtre.addWidget(self.date_pana_rc)
        self.btn_refresh_rc = QPushButton("🔄 Actualizeaza")
        self.btn_refresh_rc.clicked.connect(self.load_raport_client)
        self._sp(self.btn_refresh_rc)
        filtre.addWidget(self.btn_refresh_rc)
        self.btn_export_rc = QPushButton("📥 Export CSV")
        self.btn_export_rc.clicked.connect(lambda: self.export_csv(self.table_rc, "raport_client"))
        self._ss(self.btn_export_rc)
        filtre.addWidget(self.btn_export_rc)
        filtre.addStretch()
        layout.addLayout(filtre)

        self.frame_sumar_rc = QFrame()
        self.frame_sumar_rc.setStyleSheet(
            f"QFrame {{ background: {C_LIGHT}; border: 1px solid {C_BORDER}; border-radius: 8px; }}"
        )
        sl = QHBoxLayout(self.frame_sumar_rc)
        sl.setContentsMargins(12, 8, 12, 8)
        self.lbl_rc_nume     = QLabel("—"); self.lbl_rc_tel = QLabel("—")
        self.lbl_rc_vehicule = QLabel("—"); self.lbl_rc_total = QLabel("—")
        for lbl in [self.lbl_rc_nume, self.lbl_rc_tel, self.lbl_rc_vehicule, self.lbl_rc_total]:
            lbl.setStyleSheet(f"font-size: 12px; color: {C_DARK}; background: transparent;")
        sl.addWidget(QLabel("👤")); sl.addWidget(self.lbl_rc_nume); sl.addSpacing(20)
        sl.addWidget(QLabel("📞")); sl.addWidget(self.lbl_rc_tel); sl.addSpacing(20)
        sl.addWidget(QLabel("🏍️")); sl.addWidget(self.lbl_rc_vehicule); sl.addSpacing(20)
        sl.addWidget(QLabel("💰")); sl.addWidget(self.lbl_rc_total); sl.addStretch()
        layout.addWidget(self.frame_sumar_rc)

        self.table_rc = QTableWidget()
        self.table_rc.setColumnCount(7)
        self.table_rc.setHorizontalHeaderLabels([
            "Vehicul", "Descriere lucrare", "Ore RAR", "Cost (RON)", "Status", "Mecanic", "Data"
        ])
        h = self.table_rc.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in [2, 3, 4, 5, 6]:
            h.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table_rc.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_rc.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_rc.setAlternatingRowColors(True)
        layout.addWidget(self.table_rc)

        self.lbl_footer_rc = QLabel("")
        self.lbl_footer_rc.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {C_DARK}; "
            f"padding: 4px 8px; background: #f0fdf4; border-radius: 6px;"
        )
        self.lbl_footer_rc.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_footer_rc)
        self._load_clienti_cmb_rc()

    def _load_clienti_cmb_rc(self):
        self.cmb_client_rc.blockSignals(True)
        self.cmb_client_rc.clear()
        self.cmb_client_rc.addItem("— Selecteaza client —", None)
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT id, nume, telefon FROM clienti ORDER BY nume")
        for cid, nume, tel in cur.fetchall():
            self.cmb_client_rc.addItem(f"{nume}" + (f" ({tel})" if tel else ""), cid)
        con.close()
        self.cmb_client_rc.blockSignals(False)

    def _on_client_rc_changed(self):
        self.load_raport_client()

    def load_raport_client(self):
        id_client = self.cmb_client_rc.currentData()
        if not id_client:
            self.table_rc.setRowCount(0); self.lbl_footer_rc.setText("")
            for lbl in [self.lbl_rc_nume, self.lbl_rc_tel, self.lbl_rc_vehicule, self.lbl_rc_total]:
                lbl.setText("—")
            return
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT nume, telefon FROM clienti WHERE id=?", (id_client,))
        row_c = cur.fetchone()
        if row_c:
            self.lbl_rc_nume.setText(row_c[0] or "—")
            self.lbl_rc_tel.setText(row_c[1] or "—")
        cur.execute("SELECT COUNT(*) FROM vehicule WHERE id_client=?", (id_client,))
        self.lbl_rc_vehicule.setText(f"{cur.fetchone()[0]} vehicule")
        cur.execute("""
            SELECT v.marca || ' ' || COALESCE(v.model,'') || ' ' || COALESCE(v.nr,''),
                   l.descriere, COALESCE(l.ore_rar,0), COALESCE(l.cost,0),
                   l.status, COALESCE(l.mecanic,'—'), COALESCE(l.data,'—')
            FROM lucrari l JOIN vehicule v ON v.id = l.id_vehicul
            WHERE v.id_client = ? ORDER BY v.id, l.id DESC
        """, (id_client,))
        rows = cur.fetchall(); con.close()
        self.table_rc.setRowCount(0)
        total_ore = 0.0; total_cost = 0.0
        for i, row in enumerate(rows):
            vehicul, descriere, ore, cost, status, mecanic, data = row
            ore = float(ore); cost = float(cost)
            total_ore += ore; total_cost += cost
            self.table_rc.insertRow(i)
            item_v = QTableWidgetItem(vehicul.strip())
            item_v.setForeground(QColor(C_DARK)); f = item_v.font(); f.setBold(True); item_v.setFont(f)
            self.table_rc.setItem(i, 0, item_v)
            self.table_rc.setItem(i, 1, QTableWidgetItem(descriere or "—"))
            item_ore = QTableWidgetItem(f"{ore:.1f}")
            item_ore.setTextAlignment(Qt.AlignCenter); item_ore.setForeground(QColor(C_ACCENT))
            self.table_rc.setItem(i, 2, item_ore)
            item_cost = QTableWidgetItem(f"{cost:.2f}")
            item_cost.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_cost.setForeground(QColor("#10b981"))
            self.table_rc.setItem(i, 3, item_cost)
            st_text = "In lucru" if status == "in_lucru" else "Finalizat"
            item_st = QTableWidgetItem(st_text)
            item_st.setTextAlignment(Qt.AlignCenter)
            item_st.setForeground(QColor("#f59e0b") if status == "in_lucru" else QColor("#10b981"))
            self.table_rc.setItem(i, 4, item_st)
            item_mec = QTableWidgetItem(mecanic); item_mec.setTextAlignment(Qt.AlignCenter)
            self.table_rc.setItem(i, 5, item_mec)
            item_data = QTableWidgetItem(data); item_data.setTextAlignment(Qt.AlignCenter)
            self.table_rc.setItem(i, 6, item_data)
            self.table_rc.setRowHeight(i, 28)
        tva = total_cost * 0.19; total_cu_tva = total_cost + tva
        self.lbl_rc_total.setText(f"{total_cu_tva:.2f} RON (cu TVA)")
        self.lbl_footer_rc.setText(
            f"Total lucrari: {len(rows)}  |  Ore RAR: {total_ore:.1f}  |  "
            f"Manopera fara TVA: {total_cost:.2f} RON  |  "
            f"TVA (19%): {tva:.2f} RON  |  TOTAL: {total_cu_tva:.2f} RON"
        )

    # =========================================================
    # TAB RAPORT VEHICUL
    # =========================================================
    def _init_tab_raport_vehicul(self):
        layout = self._container(self.tab_rvehicul)
        layout.addWidget(self._page_header("🏍️  Raport vehicul", "Istoricul complet al unui vehicul"))

        filtre = QHBoxLayout()
        filtre.addWidget(QLabel("Client:"))
        self.cmb_client_rv = QComboBox()
        self.cmb_client_rv.setMinimumWidth(200)
        self.cmb_client_rv.currentIndexChanged.connect(self._on_client_rv_changed)
        filtre.addWidget(self.cmb_client_rv)
        filtre.addWidget(QLabel("Vehicul:"))
        self.cmb_vehicul_rv = QComboBox()
        self.cmb_vehicul_rv.setMinimumWidth(200)
        filtre.addWidget(self.cmb_vehicul_rv)
        filtre.addSpacing(12)
        filtre.addWidget(QLabel("De la:"))
        self.date_de_la_rv = QDateEdit()
        self.date_de_la_rv.setCalendarPopup(True)
        self.date_de_la_rv.setDisplayFormat("dd.MM.yyyy")
        self.date_de_la_rv.setDate(QDate.currentDate().addMonths(-3))
        filtre.addWidget(self.date_de_la_rv)
        filtre.addWidget(QLabel("Pana la:"))
        self.date_pana_rv = QDateEdit()
        self.date_pana_rv.setCalendarPopup(True)
        self.date_pana_rv.setDisplayFormat("dd.MM.yyyy")
        self.date_pana_rv.setDate(QDate.currentDate())
        filtre.addWidget(self.date_pana_rv)
        self.btn_refresh_rv = QPushButton("🔄 Actualizeaza")
        self.btn_refresh_rv.clicked.connect(self.load_raport_vehicul)
        self._sp(self.btn_refresh_rv)
        filtre.addWidget(self.btn_refresh_rv)
        self.btn_export_rv = QPushButton("📥 Export CSV")
        self.btn_export_rv.clicked.connect(lambda: self.export_csv(self.table_rv, "raport_vehicul"))
        self._ss(self.btn_export_rv)
        filtre.addWidget(self.btn_export_rv)
        filtre.addStretch()
        layout.addLayout(filtre)

        self.frame_sumar_rv = QFrame()
        self.frame_sumar_rv.setStyleSheet(
            "QFrame { background: #fefce8; border: 1px solid #fde68a; border-radius: 8px; }"
        )
        sl = QHBoxLayout(self.frame_sumar_rv); sl.setContentsMargins(12, 8, 12, 8)
        self.lbl_rv_vehicul = QLabel("—"); self.lbl_rv_client = QLabel("—")
        self.lbl_rv_nr = QLabel("—");      self.lbl_rv_total = QLabel("—")
        for lbl in [self.lbl_rv_vehicul, self.lbl_rv_client, self.lbl_rv_nr, self.lbl_rv_total]:
            lbl.setStyleSheet(f"font-size: 12px; color: {C_DARK}; background: transparent;")
        sl.addWidget(QLabel("🏍️")); sl.addWidget(self.lbl_rv_vehicul); sl.addSpacing(20)
        sl.addWidget(QLabel("👤"));  sl.addWidget(self.lbl_rv_client);  sl.addSpacing(20)
        sl.addWidget(QLabel("🔢")); sl.addWidget(self.lbl_rv_nr);       sl.addSpacing(20)
        sl.addWidget(QLabel("💰")); sl.addWidget(self.lbl_rv_total);    sl.addStretch()
        layout.addWidget(self.frame_sumar_rv)

        self.table_rv = QTableWidget()
        self.table_rv.setColumnCount(6)
        self.table_rv.setHorizontalHeaderLabels([
            "Descriere lucrare", "Ore RAR", "Cost (RON)", "Status", "Mecanic", "Data"
        ])
        h = self.table_rv.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in [1, 2, 3, 4, 5]:
            h.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table_rv.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_rv.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_rv.setAlternatingRowColors(True)
        layout.addWidget(self.table_rv)

        self.lbl_footer_rv = QLabel("")
        self.lbl_footer_rv.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {C_DARK}; "
            f"padding: 4px 8px; background: #fefce8; border-radius: 6px;"
        )
        self.lbl_footer_rv.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_footer_rv)
        self._load_clienti_cmb_rv()

    def _load_clienti_cmb_rv(self):
        self.cmb_client_rv.blockSignals(True)
        self.cmb_client_rv.clear()
        self.cmb_client_rv.addItem("— Selecteaza client —", None)
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT id, nume FROM clienti ORDER BY nume")
        for cid, nume in cur.fetchall():
            self.cmb_client_rv.addItem(nume, cid)
        con.close()
        self.cmb_client_rv.blockSignals(False)

    def _on_client_rv_changed(self):
        id_client = self.cmb_client_rv.currentData()
        self.cmb_vehicul_rv.clear()
        self.cmb_vehicul_rv.addItem("— Selecteaza vehicul —", None)
        if not id_client: return
        con = get_connection(); cur = con.cursor()
        cur.execute("SELECT id, marca, model, nr FROM vehicule WHERE id_client=? ORDER BY marca", (id_client,))
        for vid, marca, model, nr in cur.fetchall():
            label = f"{marca or ''} {model or ''}".strip()
            if nr: label += f" | {nr}"
            self.cmb_vehicul_rv.addItem(label, vid)
        con.close()

    def load_raport_vehicul(self):
        id_vehicul = self.cmb_vehicul_rv.currentData()
        if not id_vehicul:
            self.table_rv.setRowCount(0); self.lbl_footer_rv.setText("")
            for lbl in [self.lbl_rv_vehicul, self.lbl_rv_client, self.lbl_rv_nr, self.lbl_rv_total]:
                lbl.setText("—")
            return
        con = get_connection(); cur = con.cursor()
        cur.execute("""
            SELECT v.marca, v.model, v.nr, v.an, c.nume
            FROM vehicule v JOIN clienti c ON c.id = v.id_client WHERE v.id=?
        """, (id_vehicul,))
        row_v = cur.fetchone()
        if row_v:
            marca, model, nr, an, client_nume = row_v
            vl = f"{marca or ''} {model or ''}".strip()
            if nr: vl += f" | {nr}"
            if an: vl += f" ({an})"
            self.lbl_rv_vehicul.setText(vl)
            self.lbl_rv_client.setText(client_nume or "—")
            self.lbl_rv_nr.setText(nr or "—")
        cur.execute("""
            SELECT l.descriere, COALESCE(l.ore_rar,0), COALESCE(l.cost,0),
                   l.status, COALESCE(l.mecanic,'—'), COALESCE(l.data,'—')
            FROM lucrari l WHERE l.id_vehicul = ? ORDER BY l.id DESC
        """, (id_vehicul,))
        rows = cur.fetchall(); con.close()
        self.table_rv.setRowCount(0)
        total_ore = 0.0; total_cost = 0.0
        for i, row in enumerate(rows):
            descriere, ore, cost, status, mecanic, data = row
            ore = float(ore); cost = float(cost)
            total_ore += ore; total_cost += cost
            self.table_rv.insertRow(i)
            self.table_rv.setItem(i, 0, QTableWidgetItem(descriere or "—"))
            item_ore = QTableWidgetItem(f"{ore:.1f}")
            item_ore.setTextAlignment(Qt.AlignCenter); item_ore.setForeground(QColor(C_ACCENT))
            self.table_rv.setItem(i, 1, item_ore)
            item_cost = QTableWidgetItem(f"{cost:.2f}")
            item_cost.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_cost.setForeground(QColor("#10b981"))
            self.table_rv.setItem(i, 2, item_cost)
            st_text = "In lucru" if status == "in_lucru" else "Finalizat"
            item_st = QTableWidgetItem(st_text)
            item_st.setTextAlignment(Qt.AlignCenter)
            item_st.setForeground(QColor("#f59e0b") if status == "in_lucru" else QColor("#10b981"))
            self.table_rv.setItem(i, 3, item_st)
            item_mec = QTableWidgetItem(mecanic); item_mec.setTextAlignment(Qt.AlignCenter)
            self.table_rv.setItem(i, 4, item_mec)
            item_data = QTableWidgetItem(data); item_data.setTextAlignment(Qt.AlignCenter)
            self.table_rv.setItem(i, 5, item_data)
            self.table_rv.setRowHeight(i, 28)
        tva = total_cost * 0.19; total_cu_tva = total_cost + tva
        self.lbl_rv_total.setText(f"{total_cu_tva:.2f} RON")
        self.lbl_footer_rv.setText(
            f"Total lucrari: {len(rows)}  |  Ore RAR: {total_ore:.1f}  |  "
            f"Manopera fara TVA: {total_cost:.2f} RON  |  "
            f"TVA (19%): {tva:.2f} RON  |  TOTAL: {total_cu_tva:.2f} RON"
        )

    # =========================================================
    # EXPORT CSV
    # =========================================================
    def export_csv(self, table, prefix):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"raport_{prefix}_{timestamp}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salveaza raport CSV", default_name, "CSV Files (*.csv)"
        )
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
                headers = [table.horizontalHeaderItem(c).text()
                           if table.horizontalHeaderItem(c) else ""
                           for c in range(table.columnCount())]
                writer.writerow(headers)
                for row in range(table.rowCount()):
                    writer.writerow([
                        (table.item(row, col).text() if table.item(row, col) else "")
                        for col in range(table.columnCount())
                    ])
            show_toast(self.parent, f"Export salvat: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.warning(self, "Eroare", f"Nu s-a putut salva fisierul:\n{e}")

    # =========================================================
    # HELPER: FILTRU DATA
    # =========================================================
    def _get_date_filter(self, perioada):
        azi = datetime.now()
        if perioada == "Luna curenta":
            return azi.strftime("%Y-%m-01")
        elif perioada == "Luna trecuta":
            if azi.month == 1: return f"{azi.year - 1}-12-01"
            return f"{azi.year}-{azi.month - 1:02d}-01"
        elif perioada == "Ultimele 3 luni":
            luna = azi.month - 3; an = azi.year
            if luna <= 0: luna += 12; an -= 1
            return f"{an}-{luna:02d}-01"
        elif perioada == "Ultimele 6 luni":
            luna = azi.month - 6; an = azi.year
            if luna <= 0: luna += 12; an -= 1
            return f"{an}-{luna:02d}-01"
        elif perioada == "Anul curent":
            return f"{azi.year}-01-01"
        return None

    # =========================================================
    # LIMBA
    # =========================================================
    def apply_language(self):
        lang = self.parent.app_language
        if lang == "RO":
            self.nav_venituri.setText("  💰  Venituri")
            self.nav_lucrari.setText("  🔧  Lucrari")
            self.nav_clienti.setText("  👥  Clienti activi")
            self.nav_mecanic.setText("  📊  Raport mecanic")
            self.nav_rclient.setText("  👤  Raport client")
            self.nav_rvehicul.setText("  🏍️  Raport vehicul")
            self.nav_export.setText("  💼  Export Contabil")
            self.btn_refresh_v.setText("🔄 Actualizeaza")
            self.btn_refresh_l.setText("🔄 Actualizeaza")
            self.btn_refresh_rc.setText("🔄 Actualizeaza")
            self.btn_refresh_rv.setText("🔄 Actualizeaza")
            self.search_client_r.setPlaceholderText("Cauta client...")
        else:
            self.nav_venituri.setText("  💰  Revenue")
            self.nav_lucrari.setText("  🔧  Works")
            self.nav_clienti.setText("  👥  Active clients")
            self.nav_mecanic.setText("  📊  Mechanic report")
            self.nav_rclient.setText("  👤  Client report")
            self.nav_rvehicul.setText("  🏍️  Vehicle report")
            self.nav_export.setText("  💼  Accounting Export")
            self.btn_refresh_v.setText("🔄 Refresh")
            self.btn_refresh_l.setText("🔄 Refresh")
            self.btn_refresh_rc.setText("🔄 Refresh")
            self.btn_refresh_rv.setText("🔄 Refresh")
            self.search_client_r.setPlaceholderText("Search client...")
        self._activate_nav(self._stack.currentIndex())