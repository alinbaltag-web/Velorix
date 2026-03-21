"""
VELORIX — page_facturare.py
============================
Pagina principala Facturare + Incasari
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QComboBox, QLineEdit, QMessageBox, QMenu, QAction,
    QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QCursor
from database import get_connection, log_action
from ui.utils_toast import show_toast
from datetime import datetime
import os


# ─────────────────────────────────────────────────────────────
#  BADGE STATUS
# ─────────────────────────────────────────────────────────────

STATUS_CONFIG = {
    "emisa":            {"label": "Emisa",            "bg": "#dbeafe", "fg": "#1d4ed8"},
    "partial_incasata": {"label": "Partial incasata", "bg": "#fef9c3", "fg": "#854d0e"},
    "incasata":         {"label": "Incasata",          "bg": "#dcfce7", "fg": "#166534"},
    "stornata":         {"label": "Stornata",          "bg": "#fee2e2", "fg": "#991b1b"},
    "anulata":          {"label": "Anulata",           "bg": "#f3f4f6", "fg": "#6b7280"},
}

TIP_CONFIG = {
    "FACTURA":  {"label": "Factura",  "bg": "#eff6ff", "fg": "#1d4ed8"},
    "PROFORMA": {"label": "Proforma", "bg": "#f0fdf4", "fg": "#166534"},
    "STORNO":   {"label": "Stornare", "bg": "#fff1f2", "fg": "#be123c"},
}


def _badge(text, bg, fg):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(f"""
        QLabel {{
            background: {bg};
            color: {fg};
            border-radius: 10px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: 600;
        }}
    """)
    return lbl


# ─────────────────────────────────────────────────────────────
#  KPI CARD
# ─────────────────────────────────────────────────────────────

class KpiCard(QFrame):
    def __init__(self, title, value="0", color="#1A73E8", parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 10px;
                border-left: 4px solid {color};
                border-top: 1px solid #e8edf2;
                border-right: 1px solid #e8edf2;
                border-bottom: 1px solid #e8edf2;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 11px; color: #6b7280; font-weight: 500;")

        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {color};")

        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_value)

    def set_value(self, v):
        self.lbl_value.setText(str(v))


# ─────────────────────────────────────────────────────────────
#  PAGINA PRINCIPALA
# ─────────────────────────────────────────────────────────────

class PageFacturare(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(14)

        # ── Titlu + buton ──────────────────────────────────
        header = QHBoxLayout()
        lbl = QLabel("Facturare & Incasari")
        lbl.setObjectName("pageTitle")
        header.addWidget(lbl)
        header.addStretch()

        self.btn_nou = QPushButton("＋ Factura / Proforma noua")
        self.btn_nou.setFixedHeight(38)
        self.btn_nou.setStyleSheet("""
            QPushButton {
                background: #1A73E8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background: #1557b0; }
        """)
        self.btn_nou.clicked.connect(self._deschide_dialog_nou)
        header.addWidget(self.btn_nou)
        main.addLayout(header)

        # ── KPI Cards ──────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self.kpi_total    = KpiCard("Total emise luna",   "0 RON", "#1A73E8")
        self.kpi_incasat  = KpiCard("Incasat luna",       "0 RON", "#10b981")
        self.kpi_restant  = KpiCard("Restant de incasat", "0 RON", "#ef4444")
        self.kpi_proforme = KpiCard("Proforme active",    "0",     "#f59e0b")
        for k in [self.kpi_total, self.kpi_incasat, self.kpi_restant, self.kpi_proforme]:
            kpi_row.addWidget(k)
        main.addLayout(kpi_row)

        # ── Filtre ─────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.cmb_tip = QComboBox()
        self.cmb_tip.addItems(["Toate tipurile", "Factura", "Proforma", "Stornare"])
        self.cmb_tip.setFixedHeight(34)
        self.cmb_tip.setFixedWidth(150)
        self.cmb_tip.currentIndexChanged.connect(self.load_data)

        self.cmb_status = QComboBox()
        self.cmb_status.addItems([
            "Toate statusurile", "Emisa", "Partial incasata",
            "Incasata", "Stornata", "Anulata"
        ])
        self.cmb_status.setFixedHeight(34)
        self.cmb_status.setFixedWidth(160)
        self.cmb_status.currentIndexChanged.connect(self.load_data)

        self.cmb_perioada = QComboBox()
        self.cmb_perioada.addItems([
            "Luna curenta", "Luna trecuta", "Ultimele 3 luni",
            "Anul curent", "Toate"
        ])
        self.cmb_perioada.setFixedHeight(34)
        self.cmb_perioada.setFixedWidth(150)
        self.cmb_perioada.currentIndexChanged.connect(self.load_data)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Cauta numar, client...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self.load_data)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setFixedSize(34, 34)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 16px;
                color: #374151;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        self.btn_refresh.clicked.connect(self.load_data)

        for w in [self.cmb_tip, self.cmb_status, self.cmb_perioada]:
            w.setStyleSheet("""
                QComboBox {
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 0 8px;
                    font-size: 12px;
                    color: #374151;
                }
                QComboBox:hover { border-color: #1A73E8; }
                QComboBox::drop-down { border: none; width: 24px; }
            """)

        self.txt_search.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 12px;
                color: #374151;
            }
            QLineEdit:focus { border-color: #1A73E8; }
        """)

        filter_row.addWidget(self.cmb_tip)
        filter_row.addWidget(self.cmb_status)
        filter_row.addWidget(self.cmb_perioada)
        filter_row.addWidget(self.txt_search, 1)
        filter_row.addWidget(self.btn_refresh)
        main.addLayout(filter_row)

        # ── Tabel facturi ──────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Nr. Document", "Tip", "Data", "Client",
            "Total", "Incasat", "Rest", "Status", "E-Factura", "Actiuni"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)

        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #e8edf2;
                border-radius: 10px;
                gridline-color: transparent;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background: #eff6ff;
                color: #1e3a5f;
            }
            QHeaderView::section {
                background: #f8fafc;
                color: #374151;
                font-weight: 600;
                font-size: 11px;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
            }
            QTableWidget::item:alternate { background: #fafafa; }
        """)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

        main.addWidget(self.table)

    # ─────────────────────────────────────────────────────────
    # INCARCARE DATE
    # ─────────────────────────────────────────────────────────

    def load_data(self):
        con = get_connection()
        cur = con.cursor()

        perioada = self.cmb_perioada.currentText()
        azi = QDate.currentDate()
        data_start = None

        if perioada == "Luna curenta":
            data_start = azi.toString("yyyy-MM-01")
        elif perioada == "Luna trecuta":
            luna_trec = azi.addMonths(-1)
            data_start = luna_trec.toString("yyyy-MM-01")
            azi = QDate(azi.year(), azi.month(), 1).addDays(-1)
        elif perioada == "Ultimele 3 luni":
            data_start = azi.addMonths(-3).toString("yyyy-MM-dd")
        elif perioada == "Anul curent":
            data_start = f"{azi.year()}-01-01"

        tip_map = {
            "Factura": "FACTURA", "Proforma": "PROFORMA", "Stornare": "STORNO"
        }
        tip_sel = tip_map.get(self.cmb_tip.currentText())

        status_map = {
            "Emisa": "emisa", "Partial incasata": "partial_incasata",
            "Incasata": "incasata", "Stornata": "stornata", "Anulata": "anulata"
        }
        status_sel = status_map.get(self.cmb_status.currentText())

        search = self.txt_search.text().strip()

        query = """
            SELECT f.id, f.numar, f.tip, f.data_emitere,
                   COALESCE(c.nume, '—') as client,
                   f.total_cu_tva, f.suma_incasata,
                   f.total_cu_tva - f.suma_incasata as rest,
                   f.status
            FROM facturi f
            LEFT JOIN clienti c ON f.id_client = c.id
            WHERE 1=1
        """
        params = []

        if data_start:
            query += " AND f.data_emitere >= ?"; params.append(data_start)
        if tip_sel:
            query += " AND f.tip = ?"; params.append(tip_sel)
        if status_sel:
            query += " AND f.status = ?"; params.append(status_sel)
        if search:
            query += " AND (f.numar LIKE ? OR c.nume LIKE ?)"; params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY f.data_emitere DESC, f.id DESC"
        cur.execute(query, params)
        rows = cur.fetchall()

        # E-Factura statuses
        ef_statuses = {}
        if rows:
            ids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(ids))
            cur.execute(
                f"SELECT id, efactura_status FROM facturi WHERE id IN ({placeholders})", ids
            )
            for eid, est in cur.fetchall():
                ef_statuses[eid] = est or "netrimisa"

        # Chitante existente — verificam care facturi au cel putin o chitanta
        chitante_ids = set()
        if rows:
            ids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(ids))
            try:
                cur.execute(
                    f"SELECT DISTINCT id_factura FROM chitante WHERE id_factura IN ({placeholders})",
                    ids
                )
                chitante_ids = {row[0] for row in cur.fetchall()}
            except Exception:
                # Tabelul chitante poate sa nu existe daca e legat de incasari
                # Fallback: verificam incasari cu metoda chitanta sau suma > 0
                try:
                    cur.execute(
                        f"SELECT DISTINCT id_factura FROM incasari WHERE id_factura IN ({placeholders})",
                        ids
                    )
                    chitante_ids = {row[0] for row in cur.fetchall()}
                except Exception:
                    pass

        con.close()

        self.table.setRowCount(0)
        self.table.setRowCount(len(rows))

        total_emis = 0
        total_incasat = 0
        total_restant = 0
        nr_proforme = 0

        for i, (id_f, numar, tip, data, client,
                total, incasat, rest, status) in enumerate(rows):

            self.table.setItem(i, 0, QTableWidgetItem(numar or ""))
            self.table.setItem(i, 2, QTableWidgetItem(data or ""))
            self.table.setItem(i, 3, QTableWidgetItem(client or ""))
            self.table.setItem(i, 4, QTableWidgetItem(f"{total:,.2f} RON"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{incasat:,.2f} RON"))

            item_rest = QTableWidgetItem(f"{rest:,.2f} RON")
            if rest > 0.01:
                item_rest.setForeground(QColor("#ef4444"))
                item_rest.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(i, 6, item_rest)

            tip_cfg = TIP_CONFIG.get(tip, {"label": tip, "bg": "#f3f4f6", "fg": "#374151"})
            self.table.setCellWidget(i, 1, _badge(tip_cfg["label"], tip_cfg["bg"], tip_cfg["fg"]))

            st_cfg = STATUS_CONFIG.get(status, {"label": status, "bg": "#f3f4f6", "fg": "#374151"})
            self.table.setCellWidget(i, 7, _badge(st_cfg["label"], st_cfg["bg"], st_cfg["fg"]))

            ef_status = ef_statuses.get(id_f, "netrimisa")
            ef_cfg = {
                "netrimisa": ("—",         "#f3f4f6", "#6b7280"),
                "trimisa":   ("✅ Trimisa", "#dcfce7", "#166534"),
                "eroare":    ("❌ Eroare",  "#fee2e2", "#991b1b"),
            }.get(ef_status, ("—", "#f3f4f6", "#6b7280"))
            self.table.setCellWidget(i, 8, _badge(ef_cfg[0], ef_cfg[1], ef_cfg[2]))

            # Butoane actiuni — transmitem si daca exista chitanta
            are_chitanta = id_f in chitante_ids
            self.table.setCellWidget(
                i, 9,
                self._make_action_buttons(id_f, tip, status, ef_status, are_chitanta)
            )
            self.table.setRowHeight(i, 46)

            item0 = self.table.item(i, 0)
            if item0:
                item0.setData(Qt.UserRole, id_f)

            if tip == "FACTURA":
                total_emis += total
                total_incasat += incasat
                total_restant += rest
            elif tip == "PROFORMA" and status == "emisa":
                nr_proforme += 1

        self.kpi_total.set_value(f"{total_emis:,.0f} RON")
        self.kpi_incasat.set_value(f"{total_incasat:,.0f} RON")
        self.kpi_restant.set_value(f"{total_restant:,.0f} RON")
        self.kpi_proforme.set_value(str(nr_proforme))

    # ─────────────────────────────────────────────────────────
    # BUTOANE ACTIUNI  ← MODIFICAT
    # ─────────────────────────────────────────────────────────

    def _make_action_buttons(self, id_factura, tip, status,
                             ef_status="netrimisa", are_chitanta=False):
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        def _btn(text, bg, fg, handler, tooltip=""):
            b = QPushButton(text)
            b.setFixedHeight(28)
            b.setToolTip(tooltip)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: {fg};
                    border: none;
                    border-radius: 5px;
                    padding: 0 8px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {bg};
                    border: 1px solid rgba(0,0,0,0.15);
                }}
            """)
            b.clicked.connect(handler)
            return b

        # ── 📄 PDF Factura ──────────────────────────────────
        # Albastru inchis — document fiscal oficial
        lay.addWidget(_btn(
            "📄 Factura", "#1a4fa0", "#ffffff",
            lambda: self._genereaza_pdf(id_factura),
            tooltip="Genereaza PDF factura / proforma / storno"
        ))

        # ── 🧾 PDF Chitanta ─────────────────────────────────
        # Verde — document de confirmare plata
        # Vizibil DOAR daca exista cel putin o incasare inregistrata
        if are_chitanta:
            lay.addWidget(_btn(
                "🧾 Chitanta", "#059669", "#ffffff",
                lambda: self._genereaza_pdf_chitanta(id_factura),
                tooltip="Deschide/genereaza PDF chitanta de plata"
            ))
        else:
            # Placeholder gri dezactivat — arata ca nu exista chitanta
            placeholder = QPushButton("🧾 Chitanta")
            placeholder.setFixedHeight(28)
            placeholder.setEnabled(False)
            placeholder.setToolTip("Nu exista incasari inregistrate pentru aceasta factura")
            placeholder.setStyleSheet("""
                QPushButton {
                    background: #f1f5f9;
                    color: #9ca3af;
                    border: 1px dashed #d1d5db;
                    border-radius: 5px;
                    padding: 0 8px;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
            lay.addWidget(placeholder)

        # ── 💰 Inregistreaza incasare ───────────────────────
        if tip == "FACTURA" and status in ("emisa", "partial_incasata"):
            lay.addWidget(_btn(
                "💰 Incasare", "#10b981", "#ffffff",
                lambda: self._inregistreaza_incasare(id_factura),
                tooltip="Inregistreaza o noua incasare"
            ))

        # ── → Converteste proforma ──────────────────────────
        if tip == "PROFORMA" and status == "emisa":
            lay.addWidget(_btn(
                "→ Factura", "#1A73E8", "#ffffff",
                lambda: self._converteste_proforma(id_factura),
                tooltip="Converteste proforma in factura fiscala"
            ))

        # ── ↩ Storno ───────────────────────────────────────
        if tip == "FACTURA" and status in ("emisa", "incasata", "partial_incasata"):
            lay.addWidget(_btn(
                "↩ Storno", "#ef4444", "#ffffff",
                lambda: self._storneaza(id_factura),
                tooltip="Creeaza factura de stornare"
            ))

        # ── 📤 E-Factura ────────────────────────────────────
        if tip in ("FACTURA", "PROFORMA") and status not in ("stornata", "anulata"):
            if ef_status == "netrimisa":
                lay.addWidget(_btn(
                    "📤 E-Factura", "#7c3aed", "#ffffff",
                    lambda: self._trimite_efactura(id_factura),
                    tooltip="Trimite la ANAF prin E-Factura"
                ))
            elif ef_status == "eroare":
                lay.addWidget(_btn(
                    "🔁 Retry E-Fct", "#f59e0b", "#ffffff",
                    lambda: self._trimite_efactura(id_factura),
                    tooltip="Retrimite E-Factura (eroare anterioara)"
                ))

        lay.addStretch()
        return widget

    # ─────────────────────────────────────────────────────────
    # DIALOG FACTURA NOUA
    # ─────────────────────────────────────────────────────────

    def _deschide_dialog_nou(self):
        from ui.dialogs.dialog_factura import DialogFactura
        dialog = DialogFactura(self, user=self.parent.logged_email)
        if dialog.exec_():
            self.load_data()
            show_toast(self.parent, "Document creat cu succes!")

    # ─────────────────────────────────────────────────────────
    # GENERARE PDF FACTURA
    # ─────────────────────────────────────────────────────────

    def _genereaza_pdf(self, id_factura):
        try:
            from ui.pdf.pdf_factura import genereaza_pdf_factura
            path = genereaza_pdf_factura(id_factura)
            if path:
                import subprocess, sys
                if sys.platform == "win32":
                    os.startfile(path)
                show_toast(self.parent, f"PDF factura generat: {path}")
        except Exception as e:
            show_toast(self.parent, f"Eroare PDF factura: {e}")

    # ─────────────────────────────────────────────────────────
    # GENERARE PDF CHITANTA  ← NOU
    # ─────────────────────────────────────────────────────────

    def _genereaza_pdf_chitanta(self, id_factura):
        try:
            con = get_connection()
            cur = con.cursor()

            # Luam ultima incasare pentru factura asta
            cur.execute("""
                SELECT i.suma, i.data_incasare, i.metoda, i.referinta,
                    c.nume, f.numar
                FROM incasari i
                JOIN facturi f ON f.id = i.id_factura
                LEFT JOIN clienti c ON c.id = f.id_client
                WHERE i.id_factura = ?
                ORDER BY i.data_incasare DESC
                LIMIT 1
            """, (id_factura,))
            row = cur.fetchone()
            con.close()

            if not row:
                show_toast(self.parent, "Nu exista incasari pentru aceasta factura.")
                return

            suma, data_inc, metoda, referinta, client_nume, numar_factura = row

            from ui.pdf.chitanta_pdf import genereaza_chitanta
            path = genereaza_chitanta(
                id_factura=id_factura,
                suma=suma,
                data_inc=data_inc,
                metoda=metoda,
                referinta=referinta or "",
                client_nume=client_nume or "—",
                numar_factura=numar_factura or "",
                user=self.parent.logged_email,
                deschide_automat=True
            )

            if path:
                show_toast(self.parent, f"PDF chitanta generat!")

        except Exception as e:
            show_toast(self.parent, f"Eroare PDF chitanta: {e}")



    # ─────────────────────────────────────────────────────────
    # INREGISTRARE INCASARE
    # ─────────────────────────────────────────────────────────

    def _inregistreaza_incasare(self, id_factura):
        from ui.dialogs.dialog_incasare import DialogIncasare
        dialog = DialogIncasare(self, id_factura=id_factura,
                                user=self.parent.logged_email)
        if dialog.exec_():
            self.load_data()
            show_toast(self.parent, "Incasare inregistrata!")

    # ─────────────────────────────────────────────────────────
    # CONVERTIRE PROFORMA → FACTURA
    # ─────────────────────────────────────────────────────────

    def _converteste_proforma(self, id_proforma):
        if self.parent.app_language == "RO":
            rasp = QMessageBox.question(
                self, "Confirmare",
                "Convertesti proforma in factura fiscala?\n"
                "Proforma va fi marcata ca anulata.",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            rasp = QMessageBox.question(
                self, "Confirmation",
                "Convert proforma to fiscal invoice?\n"
                "The proforma will be marked as cancelled.",
                QMessageBox.Yes | QMessageBox.No
            )
        if rasp != QMessageBox.Yes:
            return

        try:
            from migrations_facturare import get_next_numar_factura
            numar, serie = get_next_numar_factura("FACTURA")
            data_azi = datetime.now().strftime("%Y-%m-%d")

            con = get_connection()
            cur = con.cursor()

            cur.execute("""
                SELECT id_client, id_deviz, total_fara_tva,
                       total_tva, total_cu_tva, observatii
                FROM facturi WHERE id = ?
            """, (id_proforma,))
            pro = cur.fetchone()

            if not pro:
                con.close()
                show_toast(self.parent, "Proforma nu a fost gasita.")
                return

            cur.execute("""
                INSERT INTO facturi
                    (numar, serie, tip, data_emitere, id_client, id_deviz,
                     total_fara_tva, total_tva, total_cu_tva,
                     status, observatii, creat_de)
                VALUES (?, ?, 'FACTURA', ?, ?, ?, ?, ?, ?, 'emisa', ?, ?)
            """, (numar, serie, data_azi,
                  pro[0], pro[1], pro[2], pro[3], pro[4],
                  f"Convertit din proforma | {pro[5] or ''}",
                  self.parent.logged_email))

            id_factura_nou = cur.lastrowid

            cur.execute("""
                INSERT INTO factura_linii
                    (id_factura, tip_linie, descriere, cantitate, um,
                     pret_unitar, tva_procent, tva_valoare,
                     total_fara_tva, total_cu_tva, ordine)
                SELECT ?, tip_linie, descriere, cantitate, um,
                       pret_unitar, tva_procent, tva_valoare,
                       total_fara_tva, total_cu_tva, ordine
                FROM factura_linii WHERE id_factura = ?
            """, (id_factura_nou, id_proforma))

            cur.execute("UPDATE facturi SET status = 'anulata' WHERE id = ?", (id_proforma,))
            con.commit()
            con.close()

            log_action(self.parent.logged_email, "Conversie proforma", f"PRO → {numar}")
            self.load_data()
            show_toast(self.parent, f"Factura {numar} creata din proforma!")

        except Exception as e:
            show_toast(self.parent, f"Eroare conversie: {e}")

    # ─────────────────────────────────────────────────────────
    # STORNARE
    # ─────────────────────────────────────────────────────────

    def _storneaza(self, id_factura):
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT numar, total_cu_tva FROM facturi WHERE id=?", (id_factura,))
        row = cur.fetchone()
        con.close()

        if not row:
            return

        numar_orig, total = row

        if self.parent.app_language == "RO":
            rasp = QMessageBox.question(
                self, "Confirmare stornare",
                f"Stornezi factura {numar_orig} ({total:,.2f} RON)?\n\n"
                "Se va crea o factura de stornare cu valoare negativa.",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            rasp = QMessageBox.question(
                self, "Reverse invoice",
                f"Reverse invoice {numar_orig} ({total:,.2f} RON)?\n\n"
                "A credit note with negative value will be created.",
                QMessageBox.Yes | QMessageBox.No
            )
        if rasp != QMessageBox.Yes:
            return

        try:
            from migrations_facturare import get_next_numar_factura
            numar_stor, serie = get_next_numar_factura("STORNO")
            data_azi = datetime.now().strftime("%Y-%m-%d")

            con = get_connection()
            cur = con.cursor()

            cur.execute("""
                SELECT id_client, id_deviz, total_fara_tva, total_tva, total_cu_tva
                FROM facturi WHERE id = ?
            """, (id_factura,))
            orig = cur.fetchone()

            cur.execute("""
                INSERT INTO facturi
                    (numar, serie, tip, data_emitere, id_client, id_deviz,
                     id_storno_ref, total_fara_tva, total_tva, total_cu_tva,
                     status, observatii, creat_de)
                VALUES (?, ?, 'STORNO', ?, ?, ?, ?, ?, ?, ?, 'emisa', ?, ?)
            """, (numar_stor, serie, data_azi,
                  orig[0], orig[1], id_factura,
                  -orig[2], -orig[3], -orig[4],
                  f"Stornare {numar_orig}",
                  self.parent.logged_email))

            id_stor = cur.lastrowid

            cur.execute("""
                INSERT INTO factura_linii
                    (id_factura, tip_linie, descriere, cantitate, um,
                     pret_unitar, tva_procent, tva_valoare,
                     total_fara_tva, total_cu_tva, ordine)
                SELECT ?, tip_linie, descriere, -cantitate, um,
                       pret_unitar, tva_procent, -tva_valoare,
                       -total_fara_tva, -total_cu_tva, ordine
                FROM factura_linii WHERE id_factura = ?
            """, (id_stor, id_factura))

            cur.execute("UPDATE facturi SET status = 'stornata' WHERE id = ?", (id_factura,))
            con.commit()
            con.close()

            log_action(self.parent.logged_email, "Stornare factura",
                       f"{numar_orig} → {numar_stor}")
            self.load_data()
            show_toast(self.parent, f"Stornare {numar_stor} creata!")

        except Exception as e:
            show_toast(self.parent, f"Eroare stornare: {e}")

    # ─────────────────────────────────────────────────────────
    # CONTEXT MENU
    # ─────────────────────────────────────────────────────────

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        item = self.table.item(row, 0)
        if not item:
            return
        id_f = item.data(Qt.UserRole)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 16px; font-size: 12px; border-radius: 4px; }
            QMenu::item:selected { background: #eff6ff; color: #1e3a5f; }
        """)

        act_pdf = QAction("📄 PDF Factura", self)
        act_pdf.triggered.connect(lambda: self._genereaza_pdf(id_f))
        menu.addAction(act_pdf)

        act_chit = QAction("🧾 PDF Chitanta", self)
        act_chit.triggered.connect(lambda: self._genereaza_pdf_chitanta(id_f))
        menu.addAction(act_chit)

        menu.addSeparator()

        act_inc = QAction("💰 Inregistreaza incasare", self)
        act_inc.triggered.connect(lambda: self._inregistreaza_incasare(id_f))
        menu.addAction(act_inc)

        act_inc_list = QAction("📋 Vezi incasari", self)
        act_inc_list.triggered.connect(lambda: self._vezi_incasari(id_f))
        menu.addAction(act_inc_list)

        menu.exec_(QCursor.pos())

    def _vezi_incasari(self, id_factura):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT i.id, i.data_incasare, i.suma, i.metoda, i.referinta,
                   c.nume, f.numar
            FROM incasari i
            JOIN facturi f ON f.id = i.id_factura
            LEFT JOIN clienti c ON c.id = f.id_client
            WHERE i.id_factura = ?
            ORDER BY i.data_incasare DESC
        """, (id_factura,))
        rows = cur.fetchall()
        con.close()

        if not rows:
            show_toast(self.parent, "Nu exista incasari pentru aceasta factura.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Incasari factura")
        dlg.setMinimumWidth(600)
        layout = QVBoxLayout(dlg)

        tbl = QTableWidget(len(rows), 5, dlg)
        tbl.setHorizontalHeaderLabels(["Data", "Suma (RON)", "Metoda", "Referinta", "Chitanta"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)

        for r, (inc_id, data, suma, metoda, ref, client_nume, numar_factura) in enumerate(rows):
            tbl.setItem(r, 0, QTableWidgetItem(str(data or "")))
            tbl.setItem(r, 1, QTableWidgetItem(f"{float(suma or 0):,.2f}"))
            tbl.setItem(r, 2, QTableWidgetItem(str(metoda or "").upper()))
            tbl.setItem(r, 3, QTableWidgetItem(str(ref or "")))

            btn_chit = QPushButton("🧾 PDF")
            btn_chit.setStyleSheet(
                "QPushButton { background:#0f766e; color:white; border-radius:5px;"
                "font-size:11px; font-weight:600; padding:2px 8px; }"
                "QPushButton:hover { background:#0d9488; }"
            )

            def _make_handler(s, d, m, rf, cn, nf):
                def handler():
                    from ui.pdf.chitanta_pdf import genereaza_chitanta
                    path = genereaza_chitanta(
                        id_factura=id_factura, suma=s, data_inc=d, metoda=m,
                        referinta=rf or "", client_nume=cn or "—",
                        numar_factura=nf or "", user=self.parent.logged_email,
                        deschide_automat=True
                    )
                    if path:
                        show_toast(self.parent, "PDF chitanta generat!")
                return handler

            btn_chit.clicked.connect(_make_handler(suma, data, metoda, ref, client_nume, numar_factura))
            tbl.setCellWidget(r, 4, btn_chit)

        layout.addWidget(tbl)
        btn_close = QPushButton("Inchide")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)
        dlg.exec_()

    # ─────────────────────────────────────────────────────────
    # E-FACTURA
    # ─────────────────────────────────────────────────────────

    def _trimite_efactura(self, id_factura):
        from efactura_service import get_provider_activ, trimite_factura_din_db

        provider, err = get_provider_activ()
        if not provider:
            QMessageBox.warning(
                self, "E-Factura neconfigurata",
                f"{err}\n\nMergeti la Setari → E-Factura pentru configurare."
            )
            return

        if self.parent.app_language == "RO":
            rasp = QMessageBox.question(
                self, "Trimite E-Factura",
                "Trimiti aceasta factura la ANAF prin E-Factura?\n\n"
                "Asigurati-va ca datele sunt corecte inainte de trimitere.",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            rasp = QMessageBox.question(
                self, "Send E-Invoice",
                "Send this invoice to ANAF via E-Factura?\n\n"
                "Make sure the data is correct before sending.",
                QMessageBox.Yes | QMessageBox.No
            )
        if rasp != QMessageBox.Yes:
            return

        show_toast(self.parent, "⏳ Se trimite E-Factura...")

        import threading
        def do_trimite():
            ok, mesaj = trimite_factura_din_db(id_factura)
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, "_ef_callback",
                Qt.QueuedConnection,
                Q_ARG(bool, ok),
                Q_ARG(str, mesaj)
            )

        threading.Thread(target=do_trimite, daemon=True).start()

    @pyqtSlot(bool, str)
    def _ef_callback(self, ok: bool, mesaj: str):
        if ok:
            show_toast(self.parent, f"✅ {mesaj}")
            log_action(self.parent.logged_email, "E-Factura trimisa", mesaj)
        else:
            QMessageBox.critical(self, "Eroare E-Factura", f"❌ {mesaj}")
        self.load_data()

    # ─────────────────────────────────────────────────────────
    # LIMBA
    # ─────────────────────────────────────────────────────────

    def apply_language(self):
        pass  # extins ulterior daca e nevoie