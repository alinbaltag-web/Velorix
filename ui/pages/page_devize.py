from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QHeaderView, QTableWidgetItem, QAbstractItemView,
    QMessageBox, QTableWidgetSelectionRange, QLineEdit, QComboBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor

import os
import platform
import subprocess
import webbrowser
from datetime import datetime

from ui.utils_toast import show_toast
from ui.widgets.checkbox_header import CheckBoxHeader
from ui.widgets.empty_table_overlay import EmptyTableOverlay
from ui.pdf.deviz_pdf import genereaza_deviz_pdf
from ui.pdf.rar_pdf import genereaza_rar_pdf
from database import log_action, get_connection
from ui.widgets.search_bar import SearchBar


class PageDevize(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.selected_client_id = None
        self.selected_vehicul_id = None
        self.selected_deviz_id = None
        self.selected_lucrare_id = None

        layout = QVBoxLayout(self)

        # ── LABEL INFO ──
        self.lbl_info = QLabel("Selecteaza client si vehicul pentru a vedea devizele")
        layout.addWidget(self.lbl_info)

        # ── BARA FILTRE: search + combo RAR ──
        filtru_row = QHBoxLayout()

        self.search_client = SearchBar(placeholder="Cauta dupa client...")
        self.search_client.search_triggered.connect(lambda _: self._apply_filters())
        filtru_row.addWidget(self.search_client, stretch=3)

        self.combo_rar = QComboBox()
        self.combo_rar.addItems(["Toate", "Raportat RAR", "Neraportat RAR"])
        self.combo_rar.setFixedWidth(175)
        self.combo_rar.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                background: white;
            }
            QComboBox::drop-down { border: none; }
        """)
        self.combo_rar.currentIndexChanged.connect(self._apply_filters)
        filtru_row.addWidget(self.combo_rar)

        layout.addLayout(filtru_row)

        # ── TABEL DEVIZE ──
        self.table_devize = QTableWidget()
        self.table_devize.setFocusPolicy(Qt.NoFocus)
        self.table_devize.setColumnCount(8)
        self.table_devize.setHorizontalHeaderLabels(
            ["", "Numar", "Client", "Vehicul", "Pret fara TVA", "TVA", "Total general", "RAR"]
        )

        header = CheckBoxHeader(Qt.Horizontal, self.table_devize)
        self.table_devize.setHorizontalHeader(header)
        header.clicked.connect(self.toggle_all_rows)

        self.table_devize.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_devize.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        header.setStretchLastSection(False)

        self.table_devize.verticalHeader().setDefaultSectionSize(28)
        self.table_devize.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_devize.setSelectionMode(QAbstractItemView.MultiSelection)
        self.table_devize.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table_devize.cellClicked.connect(self._on_cell_clicked)
        self.table_devize.cellDoubleClicked.connect(self.generate_pdf_selected)
        self.table_devize.viewport().installEventFilter(self)

        self.table_devize.setStyleSheet("""
            QTableWidget::item { padding-left: 4px; background-color: transparent; }
            QTableWidget::indicator { margin-left: 0px; }
        """)

        layout.addWidget(self.table_devize)
        layout.addSpacing(10)

        self._empty_overlay = EmptyTableOverlay(self.table_devize, "Niciun deviz inregistrat.\nGenereaza un deviz din pagina Lucrari.")

        # ── INCARCARE + RESTAURARE ──
        self.load_devize()
        self.restore_table_state()
        self.table_devize.horizontalHeader().sectionResized.connect(self.save_table_state)

        # ── BUTOANE ──
        btns = QHBoxLayout()

        self.btn_delete = QPushButton("Sterge deviz")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self.delete_deviz)

        self.btn_rar_pdf = QPushButton("PDF RAR")
        self.btn_rar_pdf.setToolTip(
            "Genereaza formular PDF pre-completat pentru raportarea la RAR Auto-Pass"
        )
        self.btn_rar_pdf.setStyleSheet("""
            QPushButton {
                background: #7c3aed; color: white; border: none;
                border-radius: 7px; font-size: 12px;
                font-weight: 600; padding: 0 16px; min-height: 32px;
            }
            QPushButton:hover { background: #6d28d9; }
        """)
        self.btn_rar_pdf.clicked.connect(self.genereaza_pdf_rar)

        self.btn_rar = QPushButton("Raporteaza la RAR")
        self.btn_rar.setStyleSheet("""
            QPushButton {
                background: #1A73E8; color: white; border: none;
                border-radius: 7px; font-size: 12px;
                font-weight: 600; padding: 0 16px; min-height: 32px;
            }
            QPushButton:hover { background: #1557b0; }
        """)
        self.btn_rar.clicked.connect(self.raporteaza_rar)

        self.btn_rar_manual = QPushButton("Marcheaza ca raportat")
        self.btn_rar_manual.setStyleSheet("""
            QPushButton {
                background: #059669; color: white; border: none;
                border-radius: 7px; font-size: 12px;
                font-weight: 600; padding: 0 16px; min-height: 32px;
            }
            QPushButton:hover { background: #047857; }
        """)
        self.btn_rar_manual.clicked.connect(self.marcheaza_raportat_rar)

        self.btn_emite_factura = QPushButton("🧾 Emite Factura")
        self.btn_emite_factura.setStyleSheet("""
            QPushButton {
                background: #0f766e; color: white; border: none;
                border-radius: 7px; font-size: 12px;
                font-weight: 600; padding: 0 16px; min-height: 32px;
            }
            QPushButton:hover { background: #0d9488; }
        """)
        self.btn_emite_factura.setToolTip("Emite factura din devizul selectat")
        self.btn_emite_factura.clicked.connect(self.emite_factura_din_deviz)

        btns.addWidget(self.btn_delete)
        btns.addStretch()
        btns.addWidget(self.btn_emite_factura)
        btns.addSpacing(6)
        btns.addWidget(self.btn_rar_pdf)
        btns.addSpacing(6)
        btns.addWidget(self.btn_rar)
        btns.addSpacing(6)
        btns.addWidget(self.btn_rar_manual)

        layout.addLayout(btns)
        layout.addSpacing(10)

        self.apply_language()

    # ─────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────

    def _get_pdf_path(self, numar_deviz: str) -> str:
        base  = os.path.dirname(os.path.abspath(__file__))
        ui_dir = os.path.dirname(base)
        root   = os.path.dirname(ui_dir)
        return os.path.join(root, "Devize_pdf", f"{numar_deviz}.pdf")

    # ─────────────────────────────────────────────────────
    # LIMBA
    # ─────────────────────────────────────────────────────

    def apply_language(self):
        lang = self.parent.app_language

        if lang == "RO":
            self.lbl_info.setText("Selecteaza client si vehicul pentru a vedea devizele")
            self.search_client.setPlaceholderText("Cauta dupa client...")
            self.table_devize.setHorizontalHeaderLabels(
                ["", "Numar", "Client", "Vehicul", "Pret fara TVA", "TVA", "Total general", "RAR"]
            )
            self.btn_delete.setText("🗑️ Sterge deviz")
            self.btn_rar_pdf.setText("📄 PDF RAR")
            self.btn_rar.setText("📋 Raporteaza la RAR")
            self.btn_rar_manual.setText("✅ Marcheaza ca raportat")
            self.combo_rar.setItemText(0, "Toate")
            self.combo_rar.setItemText(1, "✅ Raportat RAR")
            self.combo_rar.setItemText(2, "⬜ Neraportat RAR")
        else:
            self.lbl_info.setText("Select a client and vehicle to view estimates")
            self.search_client.setPlaceholderText("Search by client...")
            self.table_devize.setHorizontalHeaderLabels(
                ["", "Number", "Client", "Vehicle", "Price excl. VAT", "VAT", "Grand total", "RAR"]
            )
            self.btn_delete.setText("🗑️ Delete estimate")
            self.btn_rar_pdf.setText("📄 RAR PDF")
            self.btn_rar.setText("📋 Report to RAR")
            self.btn_rar_manual.setText("✅ Mark as reported")
            self.combo_rar.setItemText(0, "All")
            self.combo_rar.setItemText(1, "✅ Reported RAR")
            self.combo_rar.setItemText(2, "⬜ Not reported RAR")

        self.load_devize()

    # ─────────────────────────────────────────────────────
    # CHECKBOX HEADER
    # ─────────────────────────────────────────────────────

    def toggle_all_rows(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        self.table_devize.blockSignals(True)
        if checked:
            self.table_devize.selectAll()
        else:
            self.table_devize.clearSelection()
        for row in range(self.table_devize.rowCount()):
            item = self.table_devize.item(row, 0)
            if item:
                item.setCheckState(state)
        self.table_devize.blockSignals(False)

    # ─────────────────────────────────────────────────────
    # INCARCARE DEVIZE
    # ─────────────────────────────────────────────────────

    def load_devize(self):
        self.table_devize.setRowCount(0)

        # Sursa de adevar: starea din MainWindow (evita out-of-sync cu atributele locale)
        client_id  = getattr(self.parent, "selected_client_id",  self.selected_client_id)
        vehicul_id = getattr(self.parent, "selected_vehicul_id", self.selected_vehicul_id)

        con = get_connection()
        cur = con.cursor()

        base_query = """
            SELECT d.id, d.numar, d.total_manopera, d.total_tva, d.total_general,
                   c.nume, v.marca, v.model, d.raportat_rar
            FROM devize d
            LEFT JOIN clienti c ON d.id_client = c.id
            LEFT JOIN vehicule v ON d.id_vehicul = v.id
        """

        if not client_id and not vehicul_id:
            cur.execute(base_query + " ORDER BY d.id DESC")
        elif client_id and not vehicul_id:
            cur.execute(base_query + " WHERE d.id_client=? ORDER BY d.id DESC",
                        (client_id,))
        elif vehicul_id and not client_id:
            cur.execute(base_query + " WHERE d.id_vehicul=? ORDER BY d.id DESC",
                        (vehicul_id,))
        else:
            cur.execute(base_query + " WHERE d.id_client=? AND d.id_vehicul=? ORDER BY d.id DESC",
                        (client_id, vehicul_id))

        rows = cur.fetchall()
        con.close()

        row_index = 0
        for d in rows:
            numar_deviz = d[1]
            pdf_path    = self._get_pdf_path(numar_deviz)

            self.table_devize.insertRow(row_index)

            chk = QTableWidgetItem("")
            chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            chk.setCheckState(Qt.Unchecked)
            chk.setTextAlignment(Qt.AlignCenter)
            self.table_devize.setItem(row_index, 0, chk)

            self.table_devize.setItem(row_index, 1, QTableWidgetItem(str(d[1])))
            self.table_devize.setItem(row_index, 2, QTableWidgetItem(d[5] or ""))
            vehicul_text = f"{d[6] or ''} {d[7] or ''}".strip()
            self.table_devize.setItem(row_index, 3, QTableWidgetItem(vehicul_text))

            pret_fara_tva = d[2] if d[2] is not None else 0
            tva           = d[3] if d[3] is not None else 0
            total         = d[4] if d[4] is not None else 0
            self.table_devize.setItem(row_index, 4, QTableWidgetItem(f"{pret_fara_tva:.2f}"))
            self.table_devize.setItem(row_index, 5, QTableWidgetItem(f"{tva:.2f}"))
            self.table_devize.setItem(row_index, 6, QTableWidgetItem(f"{total:.2f}"))

            # Coloana RAR
            raportat = d[8] if len(d) > 8 and d[8] else 0
            if raportat:
                rar_item = QTableWidgetItem("Raportat")
                rar_item.setForeground(QColor("#059669"))
            else:
                rar_item = QTableWidgetItem("Neraportat")
                rar_item.setForeground(QColor("#9ca3af"))
            rar_item.setTextAlignment(Qt.AlignCenter)
            self.table_devize.setItem(row_index, 7, rar_item)

            # Evidentiere randuri fara PDF local
            pdf_missing = not os.path.exists(pdf_path)
            for col in range(self.table_devize.columnCount()):
                item = self.table_devize.item(row_index, col)
                if item:
                    if pdf_missing:
                        item.setBackground(QColor("#ffe4cc"))
                        item.setData(Qt.UserRole, "no_pdf")
                    else:
                        item.setData(Qt.UserRole, "ok")

            row_index += 1

        self._apply_filters()
        self._empty_overlay.update_visibility()

    # ─────────────────────────────────────────────────────
    # FILTRARE COMBINATA
    # ─────────────────────────────────────────────────────

    def _apply_filters(self):
        text    = self.search_client.text().strip().lower()
        rar_idx = self.combo_rar.currentIndex()  # 0=Toate 1=Raportat 2=Neraportat

        for row in range(self.table_devize.rowCount()):
            nr_text     = (self.table_devize.item(row, 1).text().lower()
                           if self.table_devize.item(row, 1) else "")
            client_name = (self.table_devize.item(row, 2).text().lower()
                           if self.table_devize.item(row, 2) else "")
            vehicul_text = (self.table_devize.item(row, 3).text().lower()
                            if self.table_devize.item(row, 3) else "")
            match_text  = (text == "") or (text in nr_text or text in client_name
                                           or text in vehicul_text)

            item_rar = self.table_devize.item(row, 7)
            rar_text = item_rar.text() if item_rar else ""
            if rar_idx == 0:
                match_rar = True
            elif rar_idx == 1:
                match_rar = rar_text == "Raportat"
            else:
                match_rar = rar_text == "Neraportat"

            self.table_devize.setRowHidden(row, not (match_text and match_rar))

    def filter_devize(self, text=None):
        """Compatibilitate cu codul extern care apeleaza filter_devize."""
        self._apply_filters()

    # ─────────────────────────────────────────────────────
    # DUBLU-CLICK → PDF DEVIZ
    # ─────────────────────────────────────────────────────

    def generate_pdf_selected(self, row=None, col=None):
        row = self.table_devize.currentRow()
        if row < 0:
            return

        numar_item = self.table_devize.item(row, 1)
        if not numar_item:
            return
        numar_deviz = numar_item.text()

        # Verificam daca PDF-ul exista local
        path = self._get_pdf_path(numar_deviz)
        if not os.path.exists(path):
            QMessageBox.warning(
                self,
                "PDF indisponibil",
                f"PDF-ul pentru devizul {numar_deviz} nu exista pe acest calculator.\n"
                "Poti sterge inregistrarea sau regenera devizul."
            )
            return

        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT id FROM devize WHERE numar = ?", (numar_deviz,))
        result = cur.fetchone()
        con.close()

        if not result:
            return

        log_action(self.parent.logged_email, "Deschidere deviz PDF", f"Deviz nr {numar_deviz}")

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    # ─────────────────────────────────────────────────────
    # GENERARE PDF DEVIZ
    # ─────────────────────────────────────────────────────

    def generate_pdf(self, id_deviz, lucrari_selectate):
        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT numar, id_client, id_vehicul, total_general
            FROM devize WHERE id = ?
        """, (id_deviz,))
        deviz_row = cur.fetchone()
        if not deviz_row:
            con.close()
            return

        numar_deviz   = deviz_row[0]
        id_client     = deviz_row[1]
        id_vehicul    = deviz_row[2]
        total_general = deviz_row[3] or 0

        cur.execute("SELECT nume, telefon, email FROM clienti WHERE id = ?", (id_client,))
        c_row = cur.fetchone()
        client = {
            "nume":    c_row[0] if c_row else "",
            "telefon": c_row[1] if c_row else "",
            "email":   c_row[2] if c_row else ""
        }

        cur.execute("SELECT marca, model, an, vin, nr, km FROM vehicule WHERE id = ?", (id_vehicul,))
        v_row = cur.fetchone()
        vehicul = {
            "marca": v_row[0] if v_row else "", "model": v_row[1] if v_row else "",
            "an":    v_row[2] if v_row else "", "vin":   v_row[3] if v_row else "",
            "nr":    v_row[4] if v_row else "", "km":    v_row[5] if v_row else ""
        }

        cur.execute("SELECT descriere, cost, ore_rar FROM deviz_lucrari WHERE id_deviz = ?", (id_deviz,))
        rows_l = cur.fetchall()

        cur.execute("""
            SELECT piesa, cantitate, pret_fara_tva, pret_cu_tva, tva, total
            FROM deviz_piese WHERE id_deviz = ?
        """, (id_deviz,))
        rows_p = cur.fetchall()

        piese   = [{"piesa": r[0], "cant": float(r[1]), "pret_fara_tva": float(r[2]),
                    "pret_cu_tva": float(r[3]), "tva": float(r[4]), "total": float(r[5])}
                   for r in rows_p]
        lucrari = [{"descriere": r[0] or "", "cost": float(r[1]) if r[1] is not None else 0,
                    "ore_rar": r[2] if len(r) > 2 else None}
                   for r in rows_l]
        con.close()

        verificari = getattr(self.parent, "verificari_finale", None)
        path = genereaza_deviz_pdf(numar_deviz, client, vehicul, lucrari, piese,
                                   float(total_general), verificari)
        log_action(self.parent.logged_email, "Generare PDF deviz", f"Deviz nr {numar_deviz}")
        if path:
            msg = "PDF generat" if self.parent.app_language == "RO" else "PDF generated"
            show_toast(self.parent, msg)

    # ─────────────────────────────────────────────────────
    # STERGERE DEVIZ
    # ─────────────────────────────────────────────────────

    def delete_deviz(self):
        rows_to_delete = [
            row for row in range(self.table_devize.rowCount())
            if (self.table_devize.item(row, 0) and
                self.table_devize.item(row, 0).checkState() == Qt.Checked)
        ]
        if not rows_to_delete:
            return

        if self.parent.app_language == "RO":
            confirm = QMessageBox.question(self, "Confirmare stergere",
                "Esti sigur ca vrei sa stergi devizul selectat?",
                QMessageBox.Yes | QMessageBox.No)
        else:
            confirm = QMessageBox.question(self, "Delete confirmation",
                "Are you sure you want to delete the selected estimate?",
                QMessageBox.Yes | QMessageBox.No)

        if confirm != QMessageBox.Yes:
            return

        con = get_connection()
        cur = con.cursor()
        from ui.session_manager import SessionManager
        user = SessionManager.get_user() or "system"
        for row in rows_to_delete:
            numar    = self.table_devize.item(row, 1).text()
            pdf_path = self._get_pdf_path(numar)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            # Restaureaza stocul pieselor din deviz inainte de stergere
            cur.execute("""
                SELECT id_piesa_stoc, cantitate FROM deviz_piese
                WHERE id_deviz = (SELECT id FROM devize WHERE numar = ?)
                  AND id_piesa_stoc IS NOT NULL
            """, (numar,))
            for piesa_id, cant in cur.fetchall():
                cant = float(cant) if cant else 0.0
                cur.execute("SELECT stoc_curent FROM stoc_piese WHERE id=?", (piesa_id,))
                r_stoc = cur.fetchone()
                if r_stoc:
                    stoc_nou = float(r_stoc[0]) + cant
                    cur.execute("UPDATE stoc_piese SET stoc_curent=? WHERE id=?",
                                (stoc_nou, piesa_id))
                    cur.execute("""
                        INSERT INTO miscari_stoc
                            (id_piesa, tip, cantitate, stoc_dupa, motiv, username)
                        VALUES (?, 'intrare', ?, ?, ?, ?)
                    """, (piesa_id, cant, stoc_nou, f"Anulare deviz {numar}", user))

            cur.execute("DELETE FROM devize WHERE numar = ?", (numar,))
            log_action(self.parent.logged_email, "Stergere deviz", f"Deviz nr {numar}")

        con.commit()
        con.close()
        self.load_devize()
        msg = "Deviz sters" if self.parent.app_language == "RO" else "Estimate deleted"
        show_toast(self.parent, msg)
        self.parent.page_dashboard.refresh_dashboard()

    # ─────────────────────────────────────────────────────
    # EMITE FACTURA DIN DEVIZ
    # ─────────────────────────────────────────────────────

    def emite_factura_din_deviz(self):
        """Deschide DialogFactura pre-populat cu devizul selectat (primul bifat sau randul curent)."""
        # Gasim devizul — prioritar primul bifat, altfel randul curent selectat
        id_deviz = None
        for row in range(self.table_devize.rowCount()):
            chk = self.table_devize.item(row, 0)
            if chk and chk.checkState() == Qt.Checked:
                numar_item = self.table_devize.item(row, 1)
                if numar_item:
                    # id-ul devizului din DB (coloana ascunsa) sau prin numar
                    con = get_connection()
                    cur = con.cursor()
                    cur.execute("SELECT id FROM devize WHERE numar=?", (numar_item.text(),))
                    r = cur.fetchone()
                    con.close()
                    if r:
                        id_deviz = r[0]
                break

        if not id_deviz:
            row = self.table_devize.currentRow()
            if row >= 0:
                numar_item = self.table_devize.item(row, 1)
                if numar_item:
                    con = get_connection()
                    cur = con.cursor()
                    cur.execute("SELECT id FROM devize WHERE numar=?", (numar_item.text(),))
                    r = cur.fetchone()
                    con.close()
                    if r:
                        id_deviz = r[0]

        if not id_deviz:
            show_toast(self.parent, "Selecteaza un deviz mai intai.")
            return

        from ui.dialogs.dialog_factura import DialogFactura
        dlg = DialogFactura(self.parent, id_deviz=id_deviz)
        dlg.exec_()
        # Reincarca facturare daca pagina e vizibila
        if hasattr(self.parent, "page_facturare"):
            self.parent.page_facturare.load_data()

    # ─────────────────────────────────────────────────────
    # SELECTARE DEVIZ
    # ─────────────────────────────────────────────────────

    def _on_cell_clicked(self, row, col):
        if col == 0:
            item = self.table_devize.item(row, 0)
            if item:
                selected_rows = [i.row() for i in self.table_devize.selectedItems()]
                is_selected = row in selected_rows
                self.table_devize.blockSignals(True)
                item.setCheckState(Qt.Checked if is_selected else Qt.Unchecked)
                self.table_devize.blockSignals(False)
        id_item = self.table_devize.item(row, 1)
        if id_item:
            self.selected_deviz_id = id_item.text()

    def select_deviz(self, row, col):
        id_item = self.table_devize.item(row, 1)
        if not id_item:
            return
        self.selected_deviz_id = id_item.text()

    # ─────────────────────────────────────────────────────
    # EVENT FILTER
    # ─────────────────────────────────────────────────────

    def eventFilter(self, source, event):
        if source is self.table_devize.viewport():
            if event.type() == event.MouseButtonPress:
                index = self.table_devize.indexAt(event.pos())
                if not index.isValid():
                    self.table_devize.blockSignals(True)
                    self.table_devize.clearSelection()
                    for r in range(self.table_devize.rowCount()):
                        chk = self.table_devize.item(r, 0)
                        if chk:
                            chk.setCheckState(Qt.Unchecked)
                    self.table_devize.blockSignals(False)
                    self.selected_deviz_id = None
                    return True
                if index.column() != 0:
                    row = index.row()
                    self.table_devize.blockSignals(True)
                    self.table_devize.clearSelection()
                    self.table_devize.selectRow(row)
                    for r in range(self.table_devize.rowCount()):
                        chk = self.table_devize.item(r, 0)
                        if chk and chk.checkState() == Qt.Checked:
                            self.table_devize.selectRow(r)
                    self.table_devize.blockSignals(False)
                    id_item = self.table_devize.item(row, 1)
                    if id_item:
                        self.selected_deviz_id = id_item.text()
                    return True
        return super().eventFilter(source, event)

    # ─────────────────────────────────────────────────────
    # SALVARE / RESTAURARE STARE TABEL
    # ─────────────────────────────────────────────────────

    def save_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        settings.setValue("header", self.table_devize.horizontalHeader().saveState())
        settings.endGroup()

    def restore_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        header = settings.value("header")
        settings.endGroup()
        if header:
            self.table_devize.horizontalHeader().restoreState(header)

    # ─────────────────────────────────────────────────────
    # RAR AUTO-PASS
    # ─────────────────────────────────────────────────────

    def raporteaza_rar(self):
        """Deschide site-ul RAR cu informatiile devizului selectat."""
        row = self.table_devize.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selectie",
                "Selecteaza un deviz din lista pentru a raporta la RAR.")
            return

        numar_item = self.table_devize.item(row, 1)
        if not numar_item:
            return
        numar = numar_item.text()

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT v.vin, c.nume, v.marca, v.model
            FROM devize d
            LEFT JOIN vehicule v ON v.id = d.id_vehicul
            LEFT JOIN clienti c ON c.id = d.id_client
            WHERE d.numar = ?
        """, (numar,))
        result = cur.fetchone()
        con.close()

        vin     = result[0] if result and result[0] else ""
        client  = result[1] if result and result[1] else ""
        vehicul = f"{result[2] or ''} {result[3] or ''}".strip() if result else ""

        msg = (
            f"Deviz: {numar}\n"
            f"Client: {client}\n"
            f"Vehicul: {vehicul}\n"
            f"VIN: {vin or 'Necompletat'}\n\n"
            f"Se va deschide site-ul RAR Auto-Pass.\n"
            f"Introduci manual VIN-ul si raportezi lucrarile.\n\n"
            f"Sfat: genereaza mai intai '📄 PDF RAR' pentru a avea datele pregatite."
        )
        QMessageBox.information(self, "Raportare RAR Auto-Pass", msg)
        webbrowser.open("https://www.rarom.ro")

    def marcheaza_raportat_rar(self):
        """Marcheaza / demarcheaza devizul ca raportat la RAR."""
        row = self.table_devize.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selectie", "Selecteaza un deviz din lista.")
            return

        numar_item = self.table_devize.item(row, 1)
        if not numar_item:
            return
        numar = numar_item.text()

        rar_item      = self.table_devize.item(row, 7)
        deja_raportat = rar_item and rar_item.text() == "Raportat"

        if deja_raportat:
            confirm = QMessageBox.question(
                self, "Anulare raportare",
                f"Devizul {numar} este deja marcat ca raportat.\nVrei sa anulezi marcarea?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
            nou_status = 0
        else:
            nou_status = 1

        data_now = datetime.now().strftime("%Y-%m-%d %H:%M") if nou_status else ""

        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE devize SET raportat_rar=?, data_raportare_rar=? WHERE numar=?",
            (nou_status, data_now, numar)
        )
        con.commit()
        con.close()

        log_action(
            self.parent.logged_email,
            "RAR Auto-Pass raportare" if nou_status else "RAR Auto-Pass anulare",
            f"Deviz {numar}"
        )
        self.load_devize()

        if nou_status:
            show_toast(self.parent, f"Deviz {numar} marcat ca raportat la RAR")
        else:
            show_toast(self.parent, f"Marcare RAR anulata pentru {numar}")

    def genereaza_pdf_rar(self):
        """Genereaza PDF pre-completat RAR pentru devizul selectat si il deschide."""
        row = self.table_devize.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selectie",
                "Selecteaza un deviz din lista pentru a genera PDF-ul RAR.")
            return

        numar_item = self.table_devize.item(row, 1)
        if not numar_item:
            return
        numar = numar_item.text()

        try:
            path = genereaza_rar_pdf(numar)
        except Exception as e:
            QMessageBox.critical(self, "Eroare PDF RAR",
                f"Nu s-a putut genera PDF-ul RAR:\n{e}")
            return

        if not path:
            QMessageBox.warning(self, "Eroare",
                f"Devizul {numar} nu a fost gasit in baza de date.")
            return

        log_action(
            self.parent.logged_email,
            "Generare PDF RAR Auto-Pass",
            f"Deviz {numar} -> {path}"
        )
        show_toast(self.parent, f"PDF RAR generat: RAR_{numar}.pdf")

        if os.path.exists(path):
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])