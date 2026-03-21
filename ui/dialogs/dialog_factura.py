from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QDateEdit, QDoubleSpinBox, QMessageBox,
    QAbstractItemView, QWidget, QCheckBox
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor, QFont
from database import get_connection, log_action, get_tva

STYLE = """
QDialog { background: #f0f4f8; }
QLabel#sec { font-size:10px; font-weight:700; color:#94a3b8; letter-spacing:1px; }
QLineEdit, QDateEdit {
    background:white; border:1.5px solid #e2e8f0; border-radius:6px;
    padding:5px 10px; font-size:13px; color:#1e3a5f; min-height:34px;
}
QLineEdit:focus, QDateEdit:focus { border-color:#1A73E8; }
QComboBox {
    background:white; border:1.5px solid #e2e8f0; border-radius:6px;
    padding:5px 10px; font-size:13px; color:#1e3a5f; min-height:34px;
}
QComboBox:focus { border-color:#1A73E8; }
QComboBox::drop-down { border:none; width:26px; }
QComboBox QAbstractItemView {
    background:white; color:#1e3a5f;
    selection-background-color:#eff6ff; selection-color:#1A73E8;
    border:1px solid #e2e8f0; outline:none; font-size:13px;
}
QFrame#card { background:white; border:1px solid #e8edf2; border-radius:10px; }
QTableWidget {
    background:white; border:none; gridline-color:#f1f5f9;
    font-size:12px; color:#1e3a5f;
}
QTableWidget::item { padding:5px 8px; color:#1e3a5f; }
QTableWidget::item:selected { background:#eff6ff; color:#1e3a5f; }
QHeaderView::section {
    background:#f8fafc; color:#64748b; font-weight:700; font-size:10px;
    padding:7px 8px; border:none; border-bottom:2px solid #e2e8f0;
}
QDateEdit:disabled { background:#f1f5f9; color:#9ca3af; border-color:#e2e8f0; }
"""


def _card():
    f = QFrame()
    f.setObjectName("card")
    return f


def _sec(text):
    l = QLabel(text.upper())
    l.setObjectName("sec")
    return l


class DialogFactura(QDialog):
    def __init__(self, parent, user="", id_deviz=None):
        super().__init__(parent)
        self.user      = user
        self._tva      = get_tva()
        self._id_deviz = id_deviz
        self._tip      = "FACTURA"
        self.setWindowTitle("Document nou")
        self.setMinimumSize(860, 700)
        self.setModal(True)
        self.setStyleSheet(STYLE)
        self._load_clienti()
        self._build_ui()
        if id_deviz:
            self._importa_deviz(id_deviz)

    def _load_clienti(self):
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT id, nume, telefon FROM clienti ORDER BY nume")
        self._clienti = cur.fetchall()
        con.close()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        lbl = QLabel("Document nou")
        lbl.setStyleSheet("font-size:20px; font-weight:700; color:#1e3a5f;")
        root.addWidget(lbl)

        # Card 1: Tip + Date
        c1 = _card()
        l1 = QVBoxLayout(c1)
        l1.setContentsMargins(14, 10, 14, 10)
        l1.setSpacing(8)
        l1.addWidget(_sec("Tip document si date"))
        r1 = QHBoxLayout()
        r1.setSpacing(14)

        tip_col = QVBoxLayout()
        tip_col.setSpacing(4)
        tip_col.addWidget(_sec("Tip"))
        tip_r = QHBoxLayout()
        tip_r.setSpacing(6)
        self.btn_factura  = self._mk_tip_btn("Factura fiscala", "FACTURA")
        self.btn_proforma = self._mk_tip_btn("Proforma",        "PROFORMA")
        self._refresh_tip_btns()
        tip_r.addWidget(self.btn_factura)
        tip_r.addWidget(self.btn_proforma)
        tip_r.addStretch()
        tip_col.addLayout(tip_r)
        r1.addLayout(tip_col)

        dc = QVBoxLayout()
        dc.setSpacing(4)
        dc.addWidget(_sec("Data emitere"))
        self.date_em = QDateEdit(QDate.currentDate())
        self.date_em.setCalendarPopup(True)
        self.date_em.setFixedWidth(130)
        dc.addWidget(self.date_em)
        r1.addLayout(dc)

        # Scadenta cu checkbox
        sc_col = QVBoxLayout()
        sc_col.setSpacing(4)
        self.chk_scadenta = QCheckBox("Scadenta")
        self.chk_scadenta.setChecked(True)
        self.chk_scadenta.setStyleSheet("""
            QCheckBox {
                font-size:10px; font-weight:700; color:#94a3b8;
                letter-spacing:1px; background:transparent;
            }
            QCheckBox::indicator {
                width:15px; height:15px;
                border:1.5px solid #e2e8f0;
                border-radius:3px; background:white;
            }
            QCheckBox::indicator:checked {
                background:#1A73E8; border-color:#1A73E8;
            }
        """)
        self.chk_scadenta.toggled.connect(lambda checked: self.date_sc.setEnabled(checked))
        sc_col.addWidget(self.chk_scadenta)
        self.date_sc = QDateEdit(QDate.currentDate().addDays(30))
        self.date_sc.setCalendarPopup(True)
        self.date_sc.setFixedWidth(130)
        self.date_sc.setEnabled(True)
        sc_col.addWidget(self.date_sc)
        r1.addLayout(sc_col)

        r1.addStretch()
        l1.addLayout(r1)
        root.addWidget(c1)

        # Card 2: Client
        c2 = _card()
        l2 = QVBoxLayout(c2)
        l2.setContentsMargins(14, 10, 14, 10)
        l2.setSpacing(8)
        l2.addWidget(_sec("Client si deviz"))
        cr = QHBoxLayout()
        cr.setSpacing(10)

        # Client - dropdown simplu, fara editare
        cc = QVBoxLayout()
        cc.setSpacing(4)
        lbl_c = QLabel("Client *")
        lbl_c.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        cc.addWidget(lbl_c)
        self.cmb_client = QComboBox()
        self.cmb_client.addItem("-- Selecteaza client --", None)
        self.cmb_client.addItem("👤 Client ocazional / Persoana fizica", -1)
        for (id_c, nume, tel) in self._clienti:
            label = "{0}  ({1})".format(nume, tel) if tel else nume
            self.cmb_client.addItem(label, id_c)
        self.cmb_client.currentIndexChanged.connect(self._on_client_changed)
        self.cmb_client.setMinimumWidth(280)
        self.cmb_client.setMaxVisibleItems(12)
        self.cmb_client.setFixedHeight(40)
        self.cmb_client.view().setMinimumWidth(400)
        self.cmb_client.view().setSpacing(2)
        cc.addWidget(self.cmb_client)

        self.lbl_client_ocazional = QLabel("Nume client ocazional *")
        self.lbl_client_ocazional.setStyleSheet("font-size:12px; color:#374151;")
        self.lbl_client_ocazional.setVisible(False)
        cc.addWidget(self.lbl_client_ocazional)

        self.txt_client_ocazional = QLineEdit()
        self.txt_client_ocazional.setPlaceholderText("ex: Ion Popescu / Persoana fizica")
        self.txt_client_ocazional.setVisible(False)
        cc.addWidget(self.txt_client_ocazional)
        cr.addLayout(cc)

        bc = QVBoxLayout()
        bc.setSpacing(4)
        bc.addWidget(QLabel(""))
        self.btn_deviz = QPushButton("Importa din deviz")
        self.btn_deviz.setFixedHeight(36)
        self.btn_deviz.setStyleSheet("""
            QPushButton {
                background:#f0f9ff; color:#0369a1;
                border:1.5px solid #7dd3fc; border-radius:7px;
                font-size:12px; font-weight:600; padding:0 14px;
            }
            QPushButton:hover { background:#e0f2fe; }
        """)
        self.btn_deviz.clicked.connect(self._selecteaza_deviz)
        bc.addWidget(self.btn_deviz)
        cr.addLayout(bc)

        self.lbl_deviz = QLabel("")
        self.lbl_deviz.setStyleSheet(
            "font-size:11px; font-weight:600; color:#059669;"
            "background:#f0fdf4; border-radius:5px; padding:4px 10px;")
        self.lbl_deviz.setVisible(False)
        cr.addWidget(self.lbl_deviz)
        cr.addStretch()
        l2.addLayout(cr)

        oc = QVBoxLayout()
        oc.setSpacing(4)
        lo = QLabel("Observatii (optional)")
        lo.setStyleSheet("font-size:12px; color:#374151;")
        oc.addWidget(lo)
        self.txt_obs = QLineEdit()
        self.txt_obs.setPlaceholderText("ex: Garantie, nr. contract, mentiuni speciale...")
        oc.addWidget(self.txt_obs)
        l2.addLayout(oc)
        root.addWidget(c2)

        # Card 3: Linii
        c3 = _card()
        l3 = QVBoxLayout(c3)
        l3.setContentsMargins(14, 10, 14, 10)
        l3.setSpacing(8)
        lh = QHBoxLayout()
        lh.addWidget(_sec("Linii document"))
        lh.addStretch()

        for txt, fn in [
            ("+ Manopera / Serviciu", lambda: self._add_row("serviciu")),
            ("+ Piesa din stoc",      self._dialog_piesa),
            ("+ Linie libera",        lambda: self._add_row("altele")),
        ]:
            b = QPushButton(txt)
            b.setFixedHeight(30)
            b.setStyleSheet("""
                QPushButton {
                    background:#f0f9ff; color:#0369a1;
                    border:1.5px dashed #7dd3fc; border-radius:6px;
                    font-size:12px; font-weight:600; padding:0 12px;
                }
                QPushButton:hover { background:#e0f2fe; }
            """)
            b.clicked.connect(fn)
            lh.addWidget(b)
            lh.addSpacing(4)
        l3.addLayout(lh)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(8)
        self.tbl.setHorizontalHeaderLabels([
            "Tip", "Descriere", "Cant.", "U.M.",
            "Pret unitar", "TVA %", "Fara TVA", "Cu TVA"
        ])
        self.tbl.setColumnWidth(0, 105)
        self.tbl.setColumnWidth(2, 65)
        self.tbl.setColumnWidth(3, 55)
        self.tbl.setColumnWidth(4, 105)
        self.tbl.setColumnWidth(5, 60)
        self.tbl.setColumnWidth(6, 100)
        self.tbl.setColumnWidth(7, 105)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(True)
        self.tbl.setMinimumHeight(175)
        self.tbl.setMaximumHeight(250)
        self.tbl.itemChanged.connect(self._on_change)
        l3.addWidget(self.tbl)

        hint = QLabel("Dublu-click pe Cant., Pret sau TVA% pentru editare.   x = sterge linia.")
        hint.setStyleSheet("font-size:11px; color:#94a3b8;")
        l3.addWidget(hint)
        root.addWidget(c3)

        # Totaluri
        tc = _card()
        tl = QHBoxLayout(tc)
        tl.setContentsMargins(16, 10, 16, 10)
        tl.addStretch()
        self.lbl_sub   = QLabel("Subtotal: 0,00 RON")
        self.lbl_tva_v = QLabel("TVA: 0,00 RON")
        self.lbl_tot   = QLabel("TOTAL: 0,00 RON")
        self.lbl_sub.setStyleSheet("font-size:13px; color:#64748b;")
        self.lbl_tva_v.setStyleSheet("font-size:13px; color:#64748b;")
        self.lbl_tot.setStyleSheet("font-size:16px; font-weight:700; color:#1e3a5f;")

        def vsep():
            s = QFrame()
            s.setFrameShape(QFrame.VLine)
            s.setStyleSheet("color:#e2e8f0;")
            return s

        tl.addWidget(self.lbl_sub)
        tl.addSpacing(16); tl.addWidget(vsep()); tl.addSpacing(16)
        tl.addWidget(self.lbl_tva_v)
        tl.addSpacing(16); tl.addWidget(vsep()); tl.addSpacing(16)
        tl.addWidget(self.lbl_tot)
        root.addWidget(tc)

        # Butoane dialog
        br = QHBoxLayout()
        br.addStretch()
        btn_x = QPushButton("Anuleaza")
        btn_x.setFixedHeight(38)
        btn_x.setStyleSheet("""
            QPushButton { background:white; color:#374151;
                border:1.5px solid #e2e8f0; border-radius:8px;
                font-size:12px; padding:0 18px; }
            QPushButton:hover { background:#f8fafc; }
        """)
        btn_x.clicked.connect(self.reject)
        btn_ok = QPushButton("Salveaza documentul")
        btn_ok.setFixedHeight(38)
        btn_ok.setStyleSheet("""
            QPushButton { background:#1A73E8; color:white; border:none;
                border-radius:8px; font-size:13px;
                font-weight:600; padding:0 22px; }
            QPushButton:hover { background:#1557b0; }
        """)
        btn_ok.clicked.connect(self._salveaza)
        br.addWidget(btn_x)
        br.addSpacing(8)
        br.addWidget(btn_ok)
        root.addLayout(br)

    def _mk_tip_btn(self, text, val):
        b = QPushButton(text)
        b.setFixedHeight(36)
        b.clicked.connect(lambda: self._set_tip(val))
        return b

    def _set_tip(self, val):
        self._tip = val
        self._refresh_tip_btns()

    def _refresh_tip_btns(self):
        ACTIVE = ("QPushButton { background:#1A73E8; color:white; border:none;"
                  "border-radius:8px; font-size:13px; font-weight:600; padding:0 16px; }")
        INACTIVE = ("QPushButton { background:white; color:#374151;"
                    "border:1.5px solid #e2e8f0; border-radius:8px;"
                    "font-size:13px; padding:0 16px; }"
                    "QPushButton:hover { background:#f8fafc; }")
        self.btn_factura.setStyleSheet( ACTIVE if self._tip == "FACTURA"  else INACTIVE)
        self.btn_proforma.setStyleSheet(ACTIVE if self._tip == "PROFORMA" else INACTIVE)
    def _on_client_changed(self):
            """Afiseaza camp nume daca e client ocazional."""
            is_ocazional = (self.cmb_client.currentData() == -1)
            self.lbl_client_ocazional.setVisible(is_ocazional)
            self.txt_client_ocazional.setVisible(is_ocazional)
    def _selecteaza_deviz(self):
        from ui.dialogs.dialog_selectare_deviz import DialogSelectareDeviz
        dlg = DialogSelectareDeviz(self)
        if dlg.exec_():
            id_d = dlg.get_id_deviz()
            if id_d:
                self._importa_deviz(id_d)

    def _importa_deviz(self, id_deviz):
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT d.id_client, c.nume, d.numar
            FROM devize d
            LEFT JOIN clienti c ON c.id = d.id_client
            WHERE d.id = ?
        """, (id_deviz,))
        deviz = cur.fetchone()
        if not deviz:
            con.close()
            return
        self._id_deviz = id_deviz
        id_client, nume_client, nr_deviz = deviz

        for i in range(self.cmb_client.count()):
            if self.cmb_client.itemData(i) == id_client:
                self.cmb_client.setCurrentIndex(i)
                break

        cur.execute(
            "SELECT descriere, cost, ore_rar FROM deviz_lucrari WHERE id_deviz=?",
            (id_deviz,))
        lucrari = cur.fetchall()
        cur.execute(
            "SELECT piesa, cantitate, pret_fara_tva, tva FROM deviz_piese WHERE id_deviz=?",
            (id_deviz,))
        piese = cur.fetchall()
        con.close()

        self.tbl.blockSignals(True)
        self.tbl.setRowCount(0)
        for desc, cost, ore in lucrari:
            if cost and cost > 0:
                ore_v = ore or 1
                pret  = round(cost / ore_v, 2)
                self._insert_row("serviciu", desc or "Manopera",
                                 ore_v, "ore", pret, self._tva)
        for piesa, cant, pret, tva in piese:
            self._insert_row("piesa", piesa or "Piesa",
                             cant or 1, "buc", pret or 0, tva or self._tva)
        self.tbl.blockSignals(False)
        self._recalc_all()
        self.lbl_deviz.setText("Importat din deviz #{}".format(nr_deviz or id_deviz))
        self.lbl_deviz.setVisible(True)

    def _add_row(self, tip):
        self.tbl.blockSignals(True)
        um = "ore" if tip == "serviciu" else "buc"
        self._insert_row(tip, "", 1, um, 0, self._tva)
        self.tbl.blockSignals(False)
        self._recalc_all()
        r = self.tbl.rowCount() - 1
        self.tbl.scrollToBottom()
        self.tbl.setCurrentCell(r, 1)
        self.tbl.editItem(self.tbl.item(r, 1))

    def _dialog_piesa(self):
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT id, cod, nume, stoc_curent, unitate, pret_vanzare, tva
            FROM stoc_piese WHERE stoc_curent > 0 ORDER BY nume
        """)
        piese = cur.fetchall()
        con.close()
        if not piese:
            QMessageBox.information(self, "Stoc gol",
                                    "Nu exista piese cu stoc disponibil.")
            return
        dlg = _DialogPiesa(self, piese)
        if dlg.exec_():
            p = dlg.piesa
            if p:
                self.tbl.blockSignals(True)
                self._insert_row("piesa", p["nume"], p["cant"],
                                 p["um"], p["pret"], p["tva"],
                                 id_piesa=p["id"])
                self.tbl.blockSignals(False)
                self._recalc_all()

    def _insert_row(self, tip, desc, cant, um, pret, tva_p, id_piesa=None):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)
        tf = round(cant * pret, 2)
        tv = round(tf * tva_p / 100, 2)
        tc = round(tf + tv, 2)
        C  = QColor("#1e3a5f")

        def it(txt, ro=False, right=False):
            i = QTableWidgetItem(str(txt))
            i.setForeground(C)
            if ro:
                i.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                i.setBackground(QColor("#f8fafc"))
            if right:
                i.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return i

        wrap = QWidget()
        wl = QHBoxLayout(wrap)
        wl.setContentsMargins(4, 0, 2, 0)
        wl.setSpacing(2)
        lbl_tip = QLabel(tip)
        lbl_tip.setStyleSheet("font-size:11px; font-weight:600; color:#64748b;")
        btn_del = QPushButton("x")
        btn_del.setFixedSize(22, 22)
        btn_del.setStyleSheet("""
            QPushButton { background:#fee2e2; color:#dc2626; border:none;
                border-radius:4px; font-size:14px; font-weight:700; }
            QPushButton:hover { background:#fecaca; }
        """)
        btn_del.clicked.connect(lambda: self._del_row(btn_del))
        wl.addWidget(lbl_tip)
        wl.addStretch()
        wl.addWidget(btn_del)
        self.tbl.setCellWidget(r, 0, wrap)

        ph = QTableWidgetItem(tip)
        ph.setData(Qt.UserRole, tip)
        ph.setFlags(Qt.ItemIsEnabled)
        self.tbl.setItem(r, 0, ph)

        desc_it = it(desc)
        desc_it.setData(Qt.UserRole, id_piesa)
        self.tbl.setItem(r, 1, desc_it)
        self.tbl.setItem(r, 2, it("{:.2f}".format(cant), right=True))
        self.tbl.setItem(r, 3, it(um))
        self.tbl.setItem(r, 4, it("{:.2f}".format(pret), right=True))
        self.tbl.setItem(r, 5, it("{:.0f}%".format(tva_p)))
        self.tbl.setItem(r, 6, it("{:.2f}".format(tf), ro=True, right=True))
        tc_it = it("{:.2f}".format(tc), ro=True, right=True)
        tc_it.setFont(QFont("Segoe UI", 10, QFont.Bold))
        tc_it.setForeground(QColor("#1A73E8"))
        self.tbl.setItem(r, 7, tc_it)
        self.tbl.setRowHeight(r, 38)

    def _del_row(self, btn):
        for r in range(self.tbl.rowCount()):
            w = self.tbl.cellWidget(r, 0)
            if w and btn in w.findChildren(QPushButton):
                self.tbl.removeRow(r)
                self._recalc_all()
                return

    def _on_change(self, item):
        if item.column() in (2, 4, 5):
            QTimer.singleShot(0, lambda: self._recalc_row(item.row()))

    def _recalc_row(self, r):
        try:
            cant_t = self.tbl.item(r, 2)
            pret_t = self.tbl.item(r, 4)
            tva_t  = self.tbl.item(r, 5)
            if not cant_t or not pret_t or not tva_t:
                return
            cant = float(cant_t.text().replace(",", "."))
            pret = float(pret_t.text().replace(",", "."))
            tva  = float(tva_t.text().replace("%", "").strip())
            tf   = round(cant * pret, 2)
            tv   = round(tf * tva / 100, 2)
            tc   = round(tf + tv, 2)
            self.tbl.blockSignals(True)
            if self.tbl.item(r, 6): self.tbl.item(r, 6).setText("{:.2f}".format(tf))
            if self.tbl.item(r, 7): self.tbl.item(r, 7).setText("{:.2f}".format(tc))
            self.tbl.blockSignals(False)
            self._recalc_all()
        except Exception:
            pass

    def _recalc_all(self):
        sub = tva = 0
        for r in range(self.tbl.rowCount()):
            try:
                tf = float(self.tbl.item(r, 6).text())
                tc = float(self.tbl.item(r, 7).text())
                sub += tf
                tva += tc - tf
            except Exception:
                pass
        tot = sub + tva
        self.lbl_sub.setText("Subtotal: {:,.2f} RON".format(sub))
        self.lbl_tva_v.setText("TVA: {:,.2f} RON".format(tva))
        self.lbl_tot.setText("TOTAL: {:,.2f} RON".format(tot))

    def _salveaza(self):
        id_client = self.cmb_client.currentData()
        nume_ocazional = None

        if id_client == -1:
            # Client ocazional — verificam sa aiba nume
            nume_ocazional = self.txt_client_ocazional.text().strip()
            if not nume_ocazional:
                QMessageBox.warning(self, "Nume lipsa",
                    "Introduceti numele clientului ocazional.")
                self.txt_client_ocazional.setFocus()
                return
            id_client = None  # nu avem id real
        elif not id_client:
            QMessageBox.warning(self, "Client lipsa",
                "Selecteaza un client din lista derulanta.")
            self.cmb_client.setFocus()
            return
        if self.tbl.rowCount() == 0:
            QMessageBox.warning(self, "Fara linii",
                "Adauga cel putin o linie in document.")
            return

        sub = tva = 0
        for r in range(self.tbl.rowCount()):
            try:
                sub += float(self.tbl.item(r, 6).text())
                tva += float(self.tbl.item(r, 7).text()) - float(self.tbl.item(r, 6).text())
            except Exception:
                pass
        total = round(sub + tva, 2)

        try:
            from migrations_facturare import get_next_numar_factura
            numar, serie = get_next_numar_factura(self._tip)
        except Exception as e:
            QMessageBox.critical(self, "Eroare numar", str(e))
            return

        data_sc = (self.date_sc.date().toString("yyyy-MM-dd")
                   if self.chk_scadenta.isChecked() else None)

        con = get_connection()
        cur = con.cursor()
        try:
            cur.execute("""
                INSERT INTO facturi
                    (numar, serie, tip, data_emitere, data_scadenta,
                     id_client, id_deviz, total_fara_tva, total_tva,
                     total_cu_tva, status, observatii, creat_de)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'emisa', ?, ?)
            """, (
                numar, serie, self._tip,
                self.date_em.date().toString("yyyy-MM-dd"),
                data_sc,
                id_client, getattr(self, "_id_deviz", None),
                round(sub, 2), round(tva, 2), total,
                ("Client ocazional: " + nume_ocazional + " | " + self.txt_obs.text().strip()
                 if nume_ocazional else self.txt_obs.text().strip()),
                self.user
            ))
            id_f = cur.lastrowid

            for r in range(self.tbl.rowCount()):
                try:
                    ph      = self.tbl.item(r, 0)
                    tip_l   = ph.data(Qt.UserRole) if ph else "altele"
                    desc_it = self.tbl.item(r, 1)
                    desc    = desc_it.text() if desc_it else ""
                    id_p    = desc_it.data(Qt.UserRole) if desc_it else None
                    cant = float(self.tbl.item(r, 2).text().replace(",", "."))
                    um   = self.tbl.item(r, 3).text()
                    pret = float(self.tbl.item(r, 4).text().replace(",", "."))
                    tva_p= float(self.tbl.item(r, 5).text().replace("%", "").strip())
                    tf   = float(self.tbl.item(r, 6).text())
                    tc   = float(self.tbl.item(r, 7).text())
                    cur.execute("""
                        INSERT INTO factura_linii
                            (id_factura, tip_linie, descriere, cantitate, um,
                             pret_unitar, tva_procent, tva_valoare,
                             total_fara_tva, total_cu_tva, id_piesa_stoc, ordine)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id_f, tip_l, desc, cant, um, pret, tva_p,
                          round(tc - tf, 2), tf, tc, id_p, r))
                except Exception as ex:
                    print("[FACTURA linie {}]: {}".format(r, ex))

            con.commit()
            log_action(self.user, "Creare {}".format(self._tip), numar)
            self.accept()

        except Exception as e:
            con.rollback()
            QMessageBox.critical(self, "Eroare salvare", str(e))
        finally:
            con.close()


class _DialogPiesa(QDialog):
    def __init__(self, parent, piese):
        super().__init__(parent)
        self._piese = piese
        self.piesa  = None
        self.setWindowTitle("Selecteaza piesa din stoc")
        self.setFixedSize(520, 420)
        self.setModal(True)
        self.setStyleSheet(STYLE)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        lbl = QLabel("Selecteaza piesa din stoc")
        lbl.setStyleSheet("font-size:15px; font-weight:700; color:#1e3a5f;")
        lay.addWidget(lbl)
        self.txt = QLineEdit()
        self.txt.setPlaceholderText("Cauta dupa denumire sau cod...")
        self.txt.textChanged.connect(self._filter)
        lay.addWidget(self.txt)
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(5)
        self.tbl.setHorizontalHeaderLabels(["Cod", "Denumire", "Stoc", "U.M.", "Pret"])
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.doubleClicked.connect(self._ok)
        lay.addWidget(self.tbl)
        cant_row = QHBoxLayout()
        lbl_c = QLabel("Cantitate:")
        lbl_c.setStyleSheet("font-size:13px; font-weight:600; color:#374151;")
        cant_row.addWidget(lbl_c)
        self.spin = QDoubleSpinBox()
        self.spin.setMinimum(0.01); self.spin.setMaximum(9999)
        self.spin.setValue(1); self.spin.setDecimals(2)
        self.spin.setFixedWidth(100)
        self.spin.setStyleSheet("""
            QDoubleSpinBox { background:white; border:1.5px solid #e2e8f0;
                border-radius:6px; padding:4px 8px;
                font-size:13px; color:#1e3a5f; min-height:32px; }
        """)
        cant_row.addWidget(self.spin)
        cant_row.addStretch()
        lay.addLayout(cant_row)
        br = QHBoxLayout(); br.addStretch()
        btn_x = QPushButton("Anuleaza")
        btn_x.setFixedHeight(34)
        btn_x.setStyleSheet("""
            QPushButton { background:white; color:#374151;
                border:1.5px solid #e2e8f0; border-radius:7px;
                font-size:12px; padding:0 16px; }
            QPushButton:hover { background:#f8fafc; }
        """)
        btn_x.clicked.connect(self.reject)
        btn_ok = QPushButton("Adauga")
        btn_ok.setFixedHeight(34)
        btn_ok.setStyleSheet("""
            QPushButton { background:#1A73E8; color:white; border:none;
                border-radius:7px; font-size:13px;
                font-weight:600; padding:0 18px; }
            QPushButton:hover { background:#1557b0; }
        """)
        btn_ok.clicked.connect(self._ok)
        br.addWidget(btn_x); br.addSpacing(8); br.addWidget(btn_ok)
        lay.addLayout(br)
        self._fill(self._piese)

    def _fill(self, piese):
        self.tbl.setRowCount(0)
        self.tbl.setRowCount(len(piese))
        for i, (id_p, cod, nume, stoc, um, pret, tva) in enumerate(piese):
            row_data = (id_p, cod, nume, stoc, um, pret, tva)
            for c, v in enumerate([cod or "", nume or "",
                                    "{:.2f}".format(stoc), um or "buc",
                                    "{:.2f} RON".format(pret)]):
                item = QTableWidgetItem(v)
                item.setForeground(QColor("#1e3a5f"))
                item.setData(Qt.UserRole, row_data)
                self.tbl.setItem(i, c, item)
            stoc_it = self.tbl.item(i, 2)
            if stoc_it:
                stoc_it.setForeground(
                    QColor("#059669") if stoc > 3 else QColor("#d97706"))
            self.tbl.setRowHeight(i, 34)

    def _filter(self, text):
        t = text.lower()
        self._fill([p for p in self._piese
                    if t in (p[2] or "").lower() or t in (p[1] or "").lower()])

    def _ok(self):
        r = self.tbl.currentRow()
        if r < 0:
            return
        it = self.tbl.item(r, 0)
        if it:
            id_p, cod, nume, stoc, um, pret, tva = it.data(Qt.UserRole)
            self.piesa = {
                "id": id_p, "cod": cod, "nume": nume,
                "um": um or "buc", "pret": pret or 0,
                "tva": tva or 19, "cant": self.spin.value()
            }
            self.accept()