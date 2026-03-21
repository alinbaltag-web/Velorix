from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QHeaderView, QTableWidgetItem,
    QAbstractItemView, QMessageBox, QComboBox, QTabWidget, QFrame,
    QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QColor

from ui.utils_toast import show_toast
from ui.dialogs.dialog_verificari import DialogVerificari
from ui.pdf.deviz_pdf import genereaza_deviz_pdf
from ui.widgets.checkbox_header import CheckBoxHeader
from ui.widgets.empty_table_overlay import EmptyTableOverlay
from database import get_connection, log_action, get_tva
from ui.dialogs.dialog_lucrare import DialogLucrare


class PageLucrari(QWidget):
    lucrare_modificata = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.selected_vehicul_id = None
        self.selected_lucrare_id = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(6)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.tab_manopere = QWidget()
        self.tab_piese = QWidget()
        self.tabs.addTab(self.tab_manopere, "Manopere")
        self.tabs.addTab(self.tab_piese, "Piese")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self._init_tab_piese()
        self._init_tab_manopere()

        self.load_lucrari()
        self.restore_table_state()

        self.table_lucrari.horizontalHeader().sectionResized.connect(
            lambda *_: self.save_table_state()
        )

        self.apply_language()

    # =========================================================
    # TAB MANOPERE — UI
    # =========================================================
    def _init_tab_manopere(self):
        layout = QVBoxLayout(self.tab_manopere)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self.lbl_vehicul = QLabel("Vehicul selectat: -")
        self.lbl_vehicul.setStyleSheet("font-size: 13px; font-weight: 600; color: #1e3a5f;")
        layout.addWidget(self.lbl_vehicul)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtru status:"))
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["Toate", "In lucru", "Finalizate"])
        self.cmb_filter.currentIndexChanged.connect(self.load_lucrari)
        filter_row.addWidget(self.cmb_filter)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.table_lucrari = QTableWidget()
        header = CheckBoxHeader(Qt.Horizontal, self.table_lucrari)
        header.clicked.connect(self._select_all_rows)
        self.table_lucrari.setHorizontalHeader(header)
        self.table_lucrari.setFocusPolicy(Qt.NoFocus)
        self.table_lucrari.setColumnCount(10)
        self.table_lucrari.setHorizontalHeaderLabels([
            "", "ID", "Descriere", "Ore RAR", "Tarif/ora",
            "Pret fara TVA", "TVA", "Total", "Status", "Mecanic"
        ])
        h = self.table_lucrari.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_lucrari.setColumnWidth(0, 32)
        h.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table_lucrari.setColumnWidth(1, 40)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(9, QHeaderView.ResizeToContents)

        self.table_lucrari.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_lucrari.setSelectionMode(QAbstractItemView.MultiSelection)
        self.table_lucrari.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_lucrari.setAlternatingRowColors(True)

        # ── Conexiuni semnale ──
        self.table_lucrari.cellClicked.connect(self._on_cell_clicked)
        self.table_lucrari.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table_lucrari.viewport().installEventFilter(self)

        layout.addWidget(self.table_lucrari)

        self._empty_overlay = EmptyTableOverlay(self.table_lucrari, "Nicio lucrare inregistrata.\nSelecteaza un vehicul sau apasa '➕ Adauga lucrare'.")

        self.lbl_sumar = QLabel("")
        self.lbl_sumar.setStyleSheet(
            "font-size: 12px; color: #1e3a5f; font-weight: 600; "
            "padding: 4px 8px; background: #eff6ff; border-radius: 6px;"
        )
        self.lbl_sumar.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_sumar)

        btns = QHBoxLayout()
        btns.setSpacing(8)

        self.btn_add = QPushButton("➕ Adauga lucrare")
        self.btn_add.setObjectName("primary")
        self.btn_add.setMinimumHeight(32)
        self.btn_add.clicked.connect(self.add_lucrare)

        self.btn_edit = QPushButton("✏️ Editeaza")
        self.btn_edit.setMinimumHeight(32)
        self.btn_edit.setStyleSheet("""
            QPushButton {
                background: #f59e0b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: #d97706; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        self.btn_edit.clicked.connect(self.edit_lucrare)
        self.btn_edit.setEnabled(False)

        self.btn_delete = QPushButton("🗑️ Sterge")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.setMinimumHeight(32)
        self.btn_delete.clicked.connect(self.delete_lucrare)

        self.btn_finalizare = QPushButton("✔ Finalizare lucrari")
        self.btn_finalizare.setObjectName("primary")
        self.btn_finalizare.setMinimumHeight(32)
        self.btn_finalizare.clicked.connect(self.finalizare_lucrari)

        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_delete)
        btns.addStretch()
        btns.addWidget(self.btn_finalizare)
        layout.addLayout(btns)

    # =========================================================
    # HANDLER CLICK / DUBLU-CLICK — inlocuiesc cele vechi
    # =========================================================
    def _select_all_rows(self, checked: bool):
        """Bifeaza / debifeaza toate randurile si sincronizeaza selectia vizuala."""
        state = Qt.Checked if checked else Qt.Unchecked
        self.table_lucrari.blockSignals(True)
        if checked:
            self.table_lucrari.selectAll()
        else:
            self.table_lucrari.clearSelection()
        for row in range(self.table_lucrari.rowCount()):
            item = self.table_lucrari.item(row, 0)
            if item:
                item.setCheckState(state)
        self.table_lucrari.blockSignals(False)

    def _highlight_row(self, row, checked: bool):
        """Coloreaza randul daca e bifat, reseteaza la culoarea normala daca nu."""
        from PyQt5.QtGui import QColor, QBrush
        bg = QBrush(QColor("#dbeafe")) if checked else QBrush()
        for c in range(self.table_lucrari.columnCount()):
            it = self.table_lucrari.item(row, c)
            if it:
                it.setBackground(bg)

    def _on_cell_clicked(self, row, col):
        # Col 0: sincronizam checkbox cu starea de selectie din MultiSelection
        if col == 0:
            item = self.table_lucrari.item(row, 0)
            if item:
                selected_rows = [i.row() for i in self.table_lucrari.selectedItems()]
                is_selected = row in selected_rows
                self.table_lucrari.blockSignals(True)
                item.setCheckState(Qt.Checked if is_selected else Qt.Unchecked)
                self.table_lucrari.blockSignals(False)

        # Activam butonul Editeaza si stocam randul activ
        self.btn_edit.setEnabled(True)
        id_item = self.table_lucrari.item(row, 1)
        if id_item:
            id_lucrare = int(id_item.text())
            self.selected_lucrare_id = id_lucrare
            if hasattr(self.parent, "page_devize"):
                self.parent.page_devize.selected_lucrare_id = id_lucrare
                self.parent.page_devize.selected_vehicul_id = self.selected_vehicul_id
                self.parent.page_devize.selected_client_id = self.parent.selected_client_id

    def _on_cell_double_clicked(self, row, col):
        if col != 8:
            self.edit_lucrare_row(row)

    # =========================================================
    # INCARCARE TARIF DIN SETARI
    # =========================================================
    def _get_tarif_ora(self):
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("SELECT tarif_ora FROM firma LIMIT 1")
            row = cur.fetchone()
            con.close()
            return float(row[0]) if row and row[0] else 150.0
        except Exception:
            return 150.0

    # =========================================================
    # INCARCARE LUCRARI
    # =========================================================
    def load_lucrari(self):
        self.table_lucrari.blockSignals(True)
        try:
            self._load_lucrari_inner()
        finally:
            self.table_lucrari.blockSignals(False)
        self._empty_overlay.update_visibility()

    def _load_lucrari_inner(self):
        self.table_lucrari.setRowCount(0)
        self.lbl_sumar.setText("")
        self.btn_edit.setEnabled(False)

        if not self.selected_vehicul_id:
            return

        con = get_connection()
        cur = con.cursor()
        status_filter = self.cmb_filter.currentText()

        if status_filter in ("In lucru", "In progress"):
            cur.execute("""
                SELECT id, descriere, ore_rar, tarif_ora, cost, status,
                       COALESCE(mecanic,'') as mecanic
                FROM lucrari WHERE id_vehicul=? AND status='in_lucru'
            """, (self.selected_vehicul_id,))
        elif status_filter in ("Finalizate", "Completed"):
            cur.execute("""
                SELECT id, descriere, ore_rar, tarif_ora, cost, status,
                       COALESCE(mecanic,'') as mecanic
                FROM lucrari WHERE id_vehicul=? AND status='finalizat'
            """, (self.selected_vehicul_id,))
        else:
            cur.execute("""
                SELECT id, descriere, ore_rar, tarif_ora, cost, status,
                       COALESCE(mecanic,'') as mecanic
                FROM lucrari WHERE id_vehicul=?
                ORDER BY CASE status WHEN 'in_lucru' THEN 0 ELSE 1 END, id
            """, (self.selected_vehicul_id,))

        lucrari = cur.fetchall()
        con.close()

        tva_pct = get_tva() / 100
        total_general_all = 0.0

        for row, l in enumerate(lucrari):
            lid, descriere, ore_rar, tarif_ora, cost, status, mecanic = l

            ore_rar = float(ore_rar) if ore_rar else 0.0
            tarif_ora = float(tarif_ora) if tarif_ora else self._get_tarif_ora()
            cost = float(cost) if cost else round(ore_rar * tarif_ora, 2)
            tva = round(cost * tva_pct, 2)
            total = round(cost + tva, 2)
            total_general_all += total

            self.table_lucrari.insertRow(row)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            chk.setCheckState(Qt.Unchecked)
            chk.setTextAlignment(Qt.AlignCenter)
            self.table_lucrari.setItem(row, 0, chk)

            self.table_lucrari.setItem(row, 1, QTableWidgetItem(str(lid)))
            self.table_lucrari.setItem(row, 2, QTableWidgetItem(descriere or ""))

            item_ore = QTableWidgetItem(f"{ore_rar:.1f}")
            item_ore.setTextAlignment(Qt.AlignCenter)
            if ore_rar > 0:
                item_ore.setForeground(QColor("#1A73E8"))
            self.table_lucrari.setItem(row, 3, item_ore)

            item_tarif = QTableWidgetItem(f"{tarif_ora:.2f}")
            item_tarif.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_lucrari.setItem(row, 4, item_tarif)

            item_pret = QTableWidgetItem(f"{cost:.2f}")
            item_pret.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_lucrari.setItem(row, 5, item_pret)

            item_tva = QTableWidgetItem(f"{tva:.2f}")
            item_tva.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_tva.setForeground(QColor("#6b7280"))
            self.table_lucrari.setItem(row, 6, item_tva)

            item_total = QTableWidgetItem(f"{total:.2f}")
            item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_total.setForeground(QColor("#10b981"))
            font = item_total.font()
            font.setBold(True)
            item_total.setFont(font)
            self.table_lucrari.setItem(row, 7, item_total)

            btn_status = QPushButton("Finalizat" if status == "finalizat" else "In lucru")
            btn_status.setFixedHeight(26)
            if status == "finalizat":
                btn_status.setStyleSheet(
                    "background:#10b981;color:white;border:none;border-radius:4px;font-size:11px;")
            else:
                btn_status.setStyleSheet(
                    "background:#f59e0b;color:white;border:none;border-radius:4px;font-size:11px;")
            btn_status.clicked.connect(self._make_status_toggle(lid, btn_status))
            self.table_lucrari.setCellWidget(row, 8, btn_status)

            # Col 9: Mecanic
            item_mec = QTableWidgetItem(mecanic or "—")
            item_mec.setTextAlignment(Qt.AlignCenter)
            if mecanic:
                item_mec.setForeground(QColor("#1e3a5f"))
            else:
                item_mec.setForeground(QColor("#9ca3af"))
            self.table_lucrari.setItem(row, 9, item_mec)

            self.table_lucrari.setRowHeight(row, 32)

        if lucrari:
            tva_total = round(total_general_all - total_general_all / (1 + tva_pct), 2)
            fara_tva = round(total_general_all - tva_total, 2)
            self.lbl_sumar.setText(
                f"Subtotal fara TVA: {fara_tva:.2f} RON  |  "
                f"TVA ({int(tva_pct*100)}%): {tva_total:.2f} RON  |  "
                f"TOTAL: {total_general_all:.2f} RON"
            )

    # =========================================================
    # ADAUGA LUCRARE
    # =========================================================
    def add_lucrare(self):
        if not self.selected_vehicul_id:
            show_toast(self.parent, "Selecteaza un vehicul inainte de a adauga o lucrare.")
            return

        tarif = self._get_tarif_ora()
        tva = get_tva()
        dialog = DialogLucrare(self, tarif_ora=tarif, tva=tva)
        if dialog.exec_() != DialogLucrare.Accepted:
            return

        d = dialog.get_data()

        con = get_connection()
        cur = con.cursor()
        # Migrare coloana mecanic (safe)
        try:
            cur.execute("ALTER TABLE lucrari ADD COLUMN mecanic TEXT DEFAULT ''")
            con.commit()
        except Exception:
            pass

        cur.execute("""
            INSERT INTO lucrari (id_vehicul, descriere, ore_rar, tarif_ora, cost, status, mecanic)
            VALUES (?, ?, ?, ?, ?, 'in_lucru', ?)
        """, (
            self.selected_vehicul_id,
            d["descriere"], d["ore_rar"], d["tarif_ora"], d["cost"],
            d.get("mecanic", "")
        ))
        con.commit()
        con.close()

        log_action(
            self.parent.logged_email, "Adaugare lucrare",
            f"{d['descriere']} | {d['ore_rar']} ore RAR | {d['cost']:.2f} RON | Vehicul ID={self.selected_vehicul_id}"
        )
        show_toast(self.parent, f"✅ Lucrare adaugata: {d['descriere']}")
        self.load_lucrari()

    # =========================================================
    # EDITEAZA LUCRARE — buton
    # =========================================================
    def edit_lucrare(self):
        row = self.table_lucrari.currentRow()
        if row < 0:
            show_toast(self.parent, "Selecteaza o lucrare pentru editare.")
            return
        self.edit_lucrare_row(row)

    # =========================================================
    # EDITEAZA LUCRARE — functie principala
    # =========================================================
    def edit_lucrare_row(self, row):
        if row < 0 or row >= self.table_lucrari.rowCount():
            return

        id_item = self.table_lucrari.item(row, 1)
        if not id_item:
            return
        id_lucrare = int(id_item.text())

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT descriere, ore_rar, tarif_ora, cost, COALESCE(mecanic,'')
            FROM lucrari WHERE id=?
        """, (id_lucrare,))
        row_db = cur.fetchone()
        con.close()

        if not row_db:
            return

        descriere_db, ore_rar_db, tarif_ora_db, cost_db, mecanic_db = row_db
        tarif = float(tarif_ora_db) if tarif_ora_db else self._get_tarif_ora()
        tva = get_tva()

        dialog = DialogLucrare(self, tarif_ora=tarif, tva=tva, titlu="Editeaza lucrare")
        dialog.descriere.setText(descriere_db or "")
        dialog.ore_rar.setValue(float(ore_rar_db) if ore_rar_db else 0.0)
        dialog.tarif.setValue(tarif)
        # cost_db este fara TVA — convertim la cu TVA pentru afisare in dialog
        cost_fara_tva_db = float(cost_db) if cost_db else 0.0
        cost_cu_tva_db = round(cost_fara_tva_db * (1 + tva / 100), 2)
        dialog.cost.setValue(cost_cu_tva_db)
        if float(ore_rar_db or 0) > 0:
            dialog.recalculeaza_cost()
        # Setam mecanicul
        dialog.set_mecanic(mecanic_db)

        if dialog.exec_() != DialogLucrare.Accepted:
            return

        d = dialog.get_data()

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            UPDATE lucrari SET descriere=?, ore_rar=?, tarif_ora=?, cost=?, mecanic=?
            WHERE id=?
        """, (d["descriere"], d["ore_rar"], d["tarif_ora"], d["cost"],
              d.get("mecanic", ""), id_lucrare))
        con.commit()
        con.close()

        log_action(
            self.parent.logged_email, "Editare lucrare",
            f"ID={id_lucrare} | {d['descriere']} | {d['ore_rar']} ore | {d['cost']:.2f} RON"
        )
        show_toast(self.parent, f"✅ Lucrare actualizata: {d['descriere']}")
        self.load_lucrari()

    # =========================================================
    # STERGERE LUCRARE
    # =========================================================
    def delete_lucrare(self):
        rows = [r for r in range(self.table_lucrari.rowCount())
                if self.table_lucrari.item(r, 0) and
                self.table_lucrari.item(r, 0).checkState() == Qt.Checked]
        if not rows:
            show_toast(self.parent, "Bifeaza lucrarile pe care vrei sa le stergi.")
            return

        if self.parent.app_language == "RO":
            confirm = QMessageBox.question(
                self, "Confirmare stergere",
                f"Stergi {len(rows)} lucrare(i) selectata(e)?",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            confirm = QMessageBox.question(
                self, "Delete confirmation",
                f"Delete {len(rows)} selected work order(s)?",
                QMessageBox.Yes | QMessageBox.No
            )
        if confirm != QMessageBox.Yes:
            return

        con = get_connection()
        cur = con.cursor()
        for r in rows:
            id_l = self.table_lucrari.item(r, 1).text()
            cur.execute("DELETE FROM lucrari WHERE id=?", (id_l,))
            log_action(self.parent.logged_email, "Stergere lucrare", f"ID={id_l}")
        con.commit()
        con.close()

        self.load_lucrari()
        show_toast(self.parent, "Lucrari sterse")
        self.selected_lucrare_id = None
        self.lucrare_modificata.emit()

        if hasattr(self.parent, "page_devize"):
            self.parent.page_devize.load_devize()
        if hasattr(self.parent, "page_dashboard"):
            self.parent.page_dashboard.refresh_dashboard()

    # =========================================================
    # TOGGLE STATUS
    # =========================================================
    def _make_status_toggle(self, id_lucrare, btn):
        return lambda: self.toggle_status(id_lucrare, btn)

    def toggle_status(self, id_lucrare, btn):
        new_status = "finalizat" if btn.text() == "In lucru" else "in_lucru"
        con = get_connection()
        cur = con.cursor()
        cur.execute("UPDATE lucrari SET status=? WHERE id=?", (new_status, id_lucrare))
        con.commit()
        con.close()
        self.load_lucrari()
        if hasattr(self.parent, "page_clienti"):
            self.parent.page_clienti.load_clienti()
        if hasattr(self.parent, "page_vehicule"):
            self.parent.page_vehicule.load_vehicule()

    # =========================================================
    # CHECKBOX + SELECTARE LUCRARE
    # =========================================================
    def checkbox_changed(self, row, col):
        # Togglam starea checkbox-ului fara sa blocam semnalele
        item = self.table_lucrari.item(row, 0)
        if item:
            new_state = Qt.Checked if item.checkState() == Qt.Unchecked else Qt.Unchecked
            self.table_lucrari.blockSignals(True)
            item.setCheckState(new_state)
            self.table_lucrari.blockSignals(False)

    def select_lucrare(self, row, col):
        # Pastrat pentru compatibilitate — logica mutata in _on_cell_clicked
        pass

    # =========================================================
    # EVENT FILTER
    # =========================================================
    def eventFilter(self, source, event):
        if source is self.table_lucrari.viewport():
            if event.type() == event.MouseButtonPress:
                index = self.table_lucrari.indexAt(event.pos())
                if not index.isValid():
                    # Click pe zona goala — deselectam tot
                    self.table_lucrari.blockSignals(True)
                    self.table_lucrari.clearSelection()
                    for r in range(self.table_lucrari.rowCount()):
                        chk = self.table_lucrari.item(r, 0)
                        if chk:
                            chk.setCheckState(Qt.Unchecked)
                    self.table_lucrari.blockSignals(False)
                    self.selected_lucrare_id = None
                    self.btn_edit.setEnabled(False)
                    if hasattr(self.parent, "page_devize"):
                        self.parent.page_devize.selected_lucrare_id = None
                    return True

                if index.column() != 0:
                    # Click pe col != 0: selectam doar randul curent
                    # + pastram toate randurile cu checkbox bifat selectate
                    row = index.row()
                    self.table_lucrari.blockSignals(True)
                    self.table_lucrari.clearSelection()
                    self.table_lucrari.selectRow(row)
                    for r in range(self.table_lucrari.rowCount()):
                        chk = self.table_lucrari.item(r, 0)
                        if chk and chk.checkState() == Qt.Checked:
                            self.table_lucrari.selectRow(r)
                    self.table_lucrari.blockSignals(False)
                    # Actualizam randul activ manual (cellClicked nu va mai fi emis)
                    self.btn_edit.setEnabled(True)
                    id_item = self.table_lucrari.item(row, 1)
                    if id_item:
                        lid = int(id_item.text())
                        self.selected_lucrare_id = lid
                        if hasattr(self.parent, "page_devize"):
                            self.parent.page_devize.selected_lucrare_id = lid
                            self.parent.page_devize.selected_vehicul_id = self.selected_vehicul_id
                            self.parent.page_devize.selected_client_id = self.parent.selected_client_id
                    return True  # Consumam evenimentul — nu mai lasam MultiSelection sa toggle

        return super().eventFilter(source, event)

    # =========================================================
    # SETARE VEHICUL
    # =========================================================
    def set_vehicul(self, vehicul_id, descriere_text):
        self.selected_vehicul_id = int(vehicul_id)
        self.lbl_vehicul.setText(f"Vehicul selectat: {descriere_text}")
        self.selected_lucrare_id = None
        self.load_lucrari()
        self.load_piese()

    # =========================================================
    # SAVE / RESTORE STATE TABEL
    # =========================================================
    def save_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        settings.setValue("header", self.table_lucrari.horizontalHeader().saveState())
        settings.endGroup()

    def restore_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        header = settings.value("header")
        settings.endGroup()
        if header:
            self.table_lucrari.horizontalHeader().restoreState(header)

    # =========================================================
    # FINALIZARE + GENERARE DEVIZ
    # =========================================================
    def finalizare_lucrari(self):
        if self.table_lucrari.rowCount() == 0:
            show_toast(self.parent, "Nu exista lucrari pentru acest vehicul.")
            return

        dlg = DialogVerificari(self)
        if not dlg.exec_():
            return
        self.parent.verificari_finale = dlg.get_results()

        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM lucrari WHERE id_vehicul=? AND status='in_lucru'",
            (self.selected_vehicul_id,)
        )
        if cur.fetchone()[0] > 0:
            show_toast(self.parent, "Atentie: exista lucrari nefinalizate!")
        con.close()

        if self.parent.app_language == "RO":
            rasp = QMessageBox.question(
                self, "Genereaza deviz",
                "Doresti sa generezi devizul?",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            rasp = QMessageBox.question(
                self, "Generate estimate",
                "Do you want to generate the estimate?",
                QMessageBox.Yes | QMessageBox.No
            )
        if rasp != QMessageBox.Yes:
            return

        self.genereaza_deviz()
        self.parent._activate_sidebar(self.parent.btn_devize, self.parent.page_devize)
        log_action(self.parent.logged_email, "Finalizare lucrari",
                   f"Vehicul ID={self.selected_vehicul_id}")

        # ── Trimitere email notificare finalizare ──
        self._trimite_email_finalizare()

        con = get_connection()
        cur = con.cursor()
        cur.execute("DELETE FROM lucrari WHERE id_vehicul=?", (self.selected_vehicul_id,))
        cur.execute("DELETE FROM piese_lucrari WHERE id_vehicul=?", (self.selected_vehicul_id,))
        con.commit()
        con.close()

        self.load_piese()
        self.load_lucrari()
        if hasattr(self.parent, "page_devize"):
            self.parent.page_devize.load_devize()
        if hasattr(self.parent, "page_clienti"):
            self.parent.page_clienti.load_clienti()
        if hasattr(self.parent, "page_vehicule"):
            self.parent.page_vehicule.load_vehicule()

    # =========================================================
    # EMAIL NOTIFICARE FINALIZARE
    # =========================================================
    def _trimite_email_finalizare(self):
        """Trimite email simplu clientului la finalizarea tuturor lucrarilor."""
        try:
            from ui.services.notification_service import send_email, _get_email_settings
            settings = _get_email_settings()
            if not settings or not settings.get("notificari_active"):
                return

            id_vehicul = self.selected_vehicul_id
            if not id_vehicul:
                return

            con = get_connection()
            cur = con.cursor()
            cur.execute("""
                SELECT v.marca, v.model, v.nr,
                       c.email, c.nume
                FROM vehicule v
                JOIN clienti c ON c.id = v.id_client
                WHERE v.id = ?
            """, (id_vehicul,))
            row_v = cur.fetchone()
            con.close()

            if not row_v:
                return
            marca, model, nr, email_client, client_nume = row_v
            if not email_client:
                return

            vehicul_label = f"{marca or ''} {model or ''}".strip()
            if nr:
                vehicul_label += f" ({nr})"

            subject = f"Lucrarile privind vehiculul {vehicul_label} au fost finalizate"
            body = f"""
            <html>
            <body style="font-family:Arial,sans-serif;color:#333;max-width:520px;margin:auto;">
              <div style="background:#1e3a5f;padding:20px 24px;border-radius:8px 8px 0 0;">
                <h2 style="color:white;margin:0;font-size:17px;">Service Moto</h2>
              </div>
              <div style="padding:24px;border:1px solid #e2e8f0;
                          border-top:none;border-radius:0 0 8px 8px;">
                <p style="font-size:15px;">Buna ziua, <b>{client_nume}</b>,</p>
                <p style="font-size:15px;line-height:1.6;">
                  Lucrarile privind vehiculul <b>{vehicul_label}</b>
                  au fost finalizate. Va asteptam sa ridicati vehiculul.
                </p>
                <p>Pentru informatii suplimentare nu ezitati sa ne contactati.</p>
                <p style="margin-top:24px;padding-top:16px;
                          border-top:1px solid #e2e8f0;
                          font-size:11px;color:#9ca3af;">
                  Email trimis automat de sistemul Service Moto.
                </p>
              </div>
            </body>
            </html>
            """

            ok, err = send_email(email_client, subject, body, settings)
            if ok:
                show_toast(self.parent, f"📧 Email trimis catre {email_client}")
            else:
                show_toast(self.parent, f"⚠️ Email netrimit: {err}")

        except Exception as e:
            show_toast(self.parent, f"⚠️ Email: {e}")

    def genereaza_deviz(self):
        id_client = self.parent.selected_client_id
        id_vehicul = self.parent.selected_vehicul_id
        if not id_client or not id_vehicul:
            show_toast(self.parent, "Selecteaza client si vehicul.")
            return

        tva_pct = get_tva() / 100

        con = get_connection()
        cur = con.cursor()

        cur.execute("SELECT nume, telefon FROM clienti WHERE id=?", (id_client,))
        r = cur.fetchone()
        client_data = {"nume": r[0], "telefon": r[1]}

        cur.execute("SELECT marca, model, an, vin, nr, km FROM vehicule WHERE id=?", (id_vehicul,))
        r = cur.fetchone()
        vehicul_data = {"marca": r[0], "model": r[1], "an": r[2],
                        "vin": r[3], "nr": r[4], "km": r[5]}

        lucrari_list = []
        total_manopera = 0.0
        seen = set()

        for row in range(self.table_lucrari.rowCount()):
            status_widget = self.table_lucrari.cellWidget(row, 8)
            if not status_widget or "finalizat" not in status_widget.text().lower():
                continue
            descr_item = self.table_lucrari.item(row, 2)
            ore_item = self.table_lucrari.item(row, 3)
            tarif_item = self.table_lucrari.item(row, 4)
            cost_item = self.table_lucrari.item(row, 5)
            if not descr_item:
                continue
            descriere = descr_item.text().strip()
            ore_rar = self._safe_float(ore_item.text() if ore_item else "0")
            tarif_ora = self._safe_float(tarif_item.text() if tarif_item else "0")
            cost = self._safe_float(cost_item.text() if cost_item else "0")
            key = (descriere, cost)
            if key in seen:
                continue
            seen.add(key)
            lucrari_list.append({
                "descriere": descriere,
                "ore_rar": ore_rar,
                "tarif_ora": tarif_ora,
                "cost": cost
            })
            total_manopera += cost

        piese_list = self.get_piese_for_deviz()
        total_piese_fara_tva = sum(p["pret_fara_tva"] * p["cant"] for p in piese_list)
        total_piese_tva = sum(p["tva"] for p in piese_list)
        total_fara_tva = total_manopera + total_piese_fara_tva
        total_tva = (total_manopera * tva_pct) + total_piese_tva
        total_general = total_fara_tva + total_tva

        from datetime import datetime
        numar_deviz = f"DEV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        path_pdf = genereaza_deviz_pdf(
            numar_deviz, client_data, vehicul_data,
            lucrari_list, piese_list, total_general
        )

        cur.execute("""
            INSERT INTO devize
                (id_client, id_vehicul, numar, data,
                 total_manopera, total_piese, total_tva, total_general, path_pdf)
            VALUES (?, ?, ?, DATE('now'), ?, ?, ?, ?, ?)
        """, (id_client, id_vehicul, numar_deviz,
              total_manopera, total_piese_fara_tva, total_tva, total_general, path_pdf))
        id_deviz = cur.lastrowid

        for p in piese_list:
            cur.execute("""
                INSERT INTO deviz_piese
                    (id_deviz, piesa, cantitate, pret_fara_tva, pret_cu_tva, tva, total, id_piesa_stoc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (id_deviz, p["piesa"], p["cant"], p["pret_fara_tva"],
                  p["pret_fara_tva"] + p["tva"], p["tva"], p["total"], p.get("id_piesa_stoc")))

        for l in lucrari_list:
            cur.execute("""
                INSERT INTO deviz_lucrari (id_deviz, descriere, cost, ore_rar)
                VALUES (?, ?, ?, ?)
            """, (id_deviz, l["descriere"], l["cost"], l.get("ore_rar", 0.0)))

        con.commit()
        con.close()
        show_toast(self.parent, "Deviz generat si salvat.")

    # =========================================================
    # TAB PIESE — UI
    # =========================================================
    def _init_tab_piese(self):
        layout = QVBoxLayout(self.tab_piese)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("🔍 Cauta:"))
        self.txt_filter_piese = QLineEdit()
        self.txt_filter_piese.setPlaceholderText("Cauta dupa cod sau nume piesa...")
        self.txt_filter_piese.textChanged.connect(self._filter_tabel_stoc)
        filter_row.addWidget(self.txt_filter_piese)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.table_stoc_piese = QTableWidget()
        self.table_stoc_piese.setFocusPolicy(Qt.NoFocus)
        self.table_stoc_piese.setColumnCount(7)
        self.table_stoc_piese.setHorizontalHeaderLabels(
            ["Categorie", "Cod", "Nume Piesa", "Stoc", "UM", "Pret", "Actiuni"]
        )
        h = self.table_stoc_piese.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.Fixed)          # ← Fixed pentru coloana Actiuni
        self.table_stoc_piese.setColumnWidth(6, 110)          # ← latime fixa suficienta
        self.table_stoc_piese.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_stoc_piese.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_stoc_piese.setAlternatingRowColors(True)
        layout.addWidget(self.table_stoc_piese, stretch=2)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(line)

        # ── Formular piesa externa (adusa de client / nu din stoc) ──
        ext_row = QHBoxLayout()
        ext_row.setSpacing(6)
        lbl_ext = QLabel("🔧 Piesa externa:")
        lbl_ext.setStyleSheet("font-weight: bold; color: #1e3a5f;")
        ext_row.addWidget(lbl_ext)

        self.txt_ext_nume = QLineEdit()
        self.txt_ext_nume.setPlaceholderText("Denumire piesa...")
        self.txt_ext_nume.setMinimumWidth(160)
        ext_row.addWidget(self.txt_ext_nume)

        self.txt_ext_cant = QLineEdit()
        self.txt_ext_cant.setPlaceholderText("Cant.")
        self.txt_ext_cant.setText("1")
        self.txt_ext_cant.setFixedWidth(55)
        ext_row.addWidget(self.txt_ext_cant)

        self.txt_ext_pret = QLineEdit()
        self.txt_ext_pret.setPlaceholderText("Pret cu TVA")
        self.txt_ext_pret.setFixedWidth(100)
        ext_row.addWidget(self.txt_ext_pret)

        btn_add_ext = QPushButton("➕ Adauga externa")
        btn_add_ext.setObjectName("primary")
        btn_add_ext.setFixedHeight(28)
        btn_add_ext.clicked.connect(self._adauga_piesa_externa)
        ext_row.addWidget(btn_add_ext)
        ext_row.addStretch()
        layout.addLayout(ext_row)

        lbl_adaugate = QLabel("📋 Piese adaugate la lucrare:")
        lbl_adaugate.setStyleSheet("font-weight: bold; color: #1e3a5f;")
        layout.addWidget(lbl_adaugate)

        self.table_piese = QTableWidget()
        self.table_piese.setFocusPolicy(Qt.NoFocus)
        self.table_piese.setColumnCount(6)
        self.table_piese.setHorizontalHeaderLabels(
            ["ID Stoc", "Piesa", "Cantitate", "Pret fara TVA", "TVA", "Total"]
        )
        self.table_piese.setColumnHidden(0, True)
        h2 = self.table_piese.horizontalHeader()
        h2.setSectionResizeMode(1, QHeaderView.Stretch)
        h2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h2.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h2.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h2.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_piese.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_piese.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_piese.setAlternatingRowColors(True)
        layout.addWidget(self.table_piese, stretch=1)

        btns_row = QHBoxLayout()
        self.btn_delete_piesa = QPushButton("🗑️ Sterge piesa selectata")
        self.btn_delete_piesa.setObjectName("danger")
        self.btn_delete_piesa.clicked.connect(self.delete_piese)
        self.btn_finalizare_piese = QPushButton("✔ Finalizare lucrari")
        self.btn_finalizare_piese.setObjectName("primary")
        self.btn_finalizare_piese.clicked.connect(self.finalizare_lucrari)
        btns_row.addWidget(self.btn_delete_piesa)
        btns_row.addStretch()
        btns_row.addWidget(self.btn_finalizare_piese)
        layout.addLayout(btns_row)

        self._piese_stoc_toate = []
        self._load_tabel_stoc()

    # =========================================================
    # TABEL STOC
    # =========================================================
    def _load_tabel_stoc(self):
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("""
                SELECT sp.id, sp.cod, sp.nume, sp.stoc_curent, sp.unitate,
                       sp.pret_vanzare, cp.nume as categorie
                FROM stoc_piese sp
                LEFT JOIN categorii_piese cp ON cp.id = sp.id_categorie
                ORDER BY cp.nume, sp.nume
            """)
            self._piese_stoc_toate = cur.fetchall()
            con.close()
            self._populate_tabel_stoc(self._piese_stoc_toate)
        except Exception:
            pass

    def _populate_tabel_stoc(self, piese):
        self.table_stoc_piese.setRowCount(0)
        for p in piese:
            piesa_id, cod, nume, stoc, um, pret, categorie = p
            r = self.table_stoc_piese.rowCount()
            self.table_stoc_piese.insertRow(r)
            self.table_stoc_piese.setItem(r, 0, QTableWidgetItem(categorie or "—"))
            self.table_stoc_piese.setItem(r, 1, QTableWidgetItem(cod or "—"))
            self.table_stoc_piese.setItem(r, 2, QTableWidgetItem(nume or ""))
            stoc_val = float(stoc) if stoc else 0
            item_stoc = QTableWidgetItem(f"{stoc_val}")
            if stoc_val <= 0:
                item_stoc.setForeground(QColor("#ef4444"))
            elif stoc_val <= 2:
                item_stoc.setForeground(QColor("#f59e0b"))
            else:
                item_stoc.setForeground(QColor("#10b981"))
            self.table_stoc_piese.setItem(r, 3, item_stoc)
            self.table_stoc_piese.setItem(r, 4, QTableWidgetItem(um or "buc"))
            self.table_stoc_piese.setItem(r, 5, QTableWidgetItem(
                f"{float(pret):.2f}" if pret else "0.00"))

            btn_add = QPushButton("➕ Adauga")
            btn_add.setObjectName("primary")
            btn_add.setFixedHeight(26)
            btn_add.setMinimumWidth(95)   # ← FIX: latime minima ca textul sa nu fie trunchiat
            btn_add.clicked.connect(
                lambda checked, pid=piesa_id, pnume=nume, pstoc=stoc_val, pum=um, ppret=pret:
                self._adauga_piesa_din_stoc(pid, pnume, pstoc, pum, ppret)
            )
            self.table_stoc_piese.setCellWidget(r, 6, btn_add)
            self.table_stoc_piese.setRowHeight(r, 30)

    def _filter_tabel_stoc(self, text):
        text = text.lower().strip()
        if not text:
            self._populate_tabel_stoc(self._piese_stoc_toate)
            return
        filtrate = [p for p in self._piese_stoc_toate
                    if text in (p[1] or "").lower() or text in (p[2] or "").lower()]
        self._populate_tabel_stoc(filtrate)

    def _on_tab_changed(self, index):
        if index == 1:
            self._load_tabel_stoc()
            self.load_piese()

    # =========================================================
    # ADAUGA PIESA DIN STOC
    # =========================================================
    def _adauga_piesa_din_stoc(self, piesa_id, nume, stoc_curent, um, pret_vanzare):
        if not self.selected_vehicul_id:
            show_toast(self.parent, "Selecteaza mai intai un vehicul!")
            return
        if stoc_curent <= 0:
            show_toast(self.parent, f"Stoc insuficient pentru {nume}!")
            return

        cant, ok = QInputDialog.getDouble(
            self, "Cantitate", f"Cantitate pentru {nume} (stoc: {stoc_curent} {um}):",
            1.0, 0.01, float(stoc_curent), 2
        )
        if not ok or cant <= 0:
            return
        if cant > stoc_curent:
            show_toast(self.parent, f"Stoc insuficient! Disponibil: {stoc_curent} {um}")
            return

        pret = float(pret_vanzare) if pret_vanzare else 0.0
        tva_pct = get_tva() / 100
        tva = round(pret * cant * tva_pct, 2)
        total = round(pret * cant + tva, 2)
        stoc_nou = stoc_curent - cant

        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("""
                INSERT INTO piese_lucrari (id_vehicul, nume, cantitate, pret_fara_tva, tva, total, id_piesa_stoc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.selected_vehicul_id, nume, cant, pret, tva, total, piesa_id))
            cur.execute("UPDATE stoc_piese SET stoc_curent=? WHERE id=?", (stoc_nou, piesa_id))

            from ui.session_manager import SessionManager
            user = SessionManager.get_user() or "system"
            cur.execute("""
                INSERT INTO miscari_stoc (id_piesa, tip, cantitate, stoc_dupa, motiv, username)
                VALUES (?, 'iesire', ?, ?, ?, ?)
            """, (piesa_id, cant, stoc_nou,
                  f"Lucrare vehicul ID={self.selected_vehicul_id}", user))

            con.commit()
            con.close()

            log_action(self.parent.logged_email, "Adaugare piesa lucrare",
                       f"{nume} x{cant} | Vehicul ID={self.selected_vehicul_id}")

            row = self.table_piese.rowCount()
            self.table_piese.insertRow(row)
            self.table_piese.setItem(row, 0, QTableWidgetItem(str(piesa_id)))
            self.table_piese.setItem(row, 1, QTableWidgetItem(nume))
            self.table_piese.setItem(row, 2, QTableWidgetItem(f"{cant}"))
            self.table_piese.setItem(row, 3, QTableWidgetItem(f"{pret:.2f}"))
            self.table_piese.setItem(row, 4, QTableWidgetItem(f"{tva:.2f}"))
            self.table_piese.setItem(row, 5, QTableWidgetItem(f"{total:.2f}"))

            self._load_tabel_stoc()
            show_toast(self.parent, f"✅ {nume} adaugat. Stoc ramas: {stoc_nou} {um}")

        except Exception as e:
            show_toast(self.parent, f"Eroare: {e}")

    # =========================================================
    # ADAUGA PIESA EXTERNA (adusa de client, nu din stoc)
    # =========================================================
    def _adauga_piesa_externa(self):
        if not self.selected_vehicul_id:
            show_toast(self.parent, "Selecteaza mai intai un vehicul!")
            return

        nume = self.txt_ext_nume.text().strip()
        if not nume:
            show_toast(self.parent, "Introduceti denumirea piesei.")
            return

        try:
            cant = float(self.txt_ext_cant.text().replace(",", ".") or "1")
        except ValueError:
            show_toast(self.parent, "Cantitate invalida.")
            return

        try:
            pret = float(self.txt_ext_pret.text().replace(",", ".") or "0")
        except ValueError:
            show_toast(self.parent, "Pret invalid.")
            return

        tva_pct = get_tva() / 100
        pret_fara_tva = round(pret / (1 + tva_pct), 4)
        total = round(pret * cant, 2)
        tva = round(total - pret_fara_tva * cant, 2)
        pret = pret_fara_tva

        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("""
                INSERT INTO piese_lucrari (id_vehicul, nume, cantitate, pret_fara_tva, tva, total)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.selected_vehicul_id, nume, cant, pret, tva, total))
            con.commit()
            con.close()

            log_action(self.parent.logged_email, "Adaugare piesa externa",
                       f"{nume} x{cant} | Vehicul ID={self.selected_vehicul_id}")

            row = self.table_piese.rowCount()
            self.table_piese.insertRow(row)
            self.table_piese.setItem(row, 0, QTableWidgetItem(""))  # fara ID stoc
            self.table_piese.setItem(row, 1, QTableWidgetItem(nume))
            self.table_piese.setItem(row, 2, QTableWidgetItem(f"{cant}"))
            self.table_piese.setItem(row, 3, QTableWidgetItem(f"{pret:.2f}"))
            self.table_piese.setItem(row, 4, QTableWidgetItem(f"{tva:.2f}"))
            self.table_piese.setItem(row, 5, QTableWidgetItem(f"{total:.2f}"))

            self.txt_ext_nume.clear()
            self.txt_ext_cant.setText("1")
            self.txt_ext_pret.clear()
            show_toast(self.parent, f"✅ Piesa externa '{nume}' adaugata.")

        except Exception as e:
            show_toast(self.parent, f"Eroare: {e}")

    # =========================================================
    # PIESE LUCRARE
    # =========================================================
    def load_piese(self):
        if not self.selected_vehicul_id:
            self.table_piese.setRowCount(0)
            return
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("""
                SELECT pl.nume, pl.cantitate, pl.pret_fara_tva, pl.tva, pl.total,
                       pl.id_piesa_stoc
                FROM piese_lucrari pl
                WHERE pl.id_vehicul = ?
            """, (self.selected_vehicul_id,))
            rows = cur.fetchall()
            con.close()
            self.table_piese.setRowCount(0)
            for r, row in enumerate(rows):
                self.table_piese.insertRow(r)
                self.table_piese.setItem(r, 0, QTableWidgetItem(str(row[5]) if row[5] else ""))
                self.table_piese.setItem(r, 1, QTableWidgetItem(str(row[0])))
                self.table_piese.setItem(r, 2, QTableWidgetItem(str(row[1])))
                self.table_piese.setItem(r, 3, QTableWidgetItem(f"{float(row[2]):.2f}"))
                self.table_piese.setItem(r, 4, QTableWidgetItem(f"{float(row[3]):.2f}"))
                self.table_piese.setItem(r, 5, QTableWidgetItem(f"{float(row[4]):.2f}"))
        except Exception:
            pass

    def delete_piese(self):
        if not self.selected_vehicul_id:
            show_toast(self.parent, "Selecteaza un vehicul inainte de a sterge piese.")
            return
        rows = sorted({idx.row() for idx in self.table_piese.selectedIndexes()}, reverse=True)
        if not rows:
            show_toast(self.parent, "Selecteaza o piesa din tabelul de jos.")
            return

        try:
            con = get_connection()
            cur = con.cursor()
            for r in rows:
                piesa_id_item = self.table_piese.item(r, 0)
                nume_item = self.table_piese.item(r, 1)
                cant_item = self.table_piese.item(r, 2)
                if not nume_item:
                    continue
                nume = nume_item.text().strip()
                cant = self._safe_float(cant_item.text() if cant_item else "0")
                piesa_id = int(piesa_id_item.text()) if (
                    piesa_id_item and piesa_id_item.text().isdigit()) else None

                self.table_piese.removeRow(r)
                cur.execute("DELETE FROM piese_lucrari WHERE id_vehicul=? AND nume=?",
                            (self.selected_vehicul_id, nume))

                if piesa_id:
                    cur.execute("SELECT stoc_curent FROM stoc_piese WHERE id=?", (piesa_id,))
                    row_stoc = cur.fetchone()
                    if row_stoc:
                        stoc_nou = float(row_stoc[0]) + cant
                        cur.execute("UPDATE stoc_piese SET stoc_curent=? WHERE id=?",
                                    (stoc_nou, piesa_id))
                        from ui.session_manager import SessionManager
                        user = SessionManager.get_user() or "system"
                        cur.execute("""
                            INSERT INTO miscari_stoc
                                (id_piesa, tip, cantitate, stoc_dupa, motiv, username)
                            VALUES (?, 'intrare', ?, ?, 'Anulare piesa lucrare', ?)
                        """, (piesa_id, cant, stoc_nou, user))

                log_action(self.parent.logged_email, "Stergere piesa lucrare",
                           f"{nume} | Vehicul ID={self.selected_vehicul_id}")

            con.commit()
            con.close()
            self._load_tabel_stoc()
            show_toast(self.parent, "Piesele selectate au fost sterse.")
        except Exception as e:
            show_toast(self.parent, f"Eroare: {e}")

    # =========================================================
    # UTILE
    # =========================================================
    @staticmethod
    def _safe_float(text, default=0.0):
        try:
            return float(str(text).replace(",", "."))
        except Exception:
            return default

    def _item_text(self, row, col):
        item = self.table_piese.item(row, col)
        return item.text() if item else ""

    def get_piese_for_deviz(self):
        piese = []
        for row in range(self.table_piese.rowCount()):
            id_stoc_text = self._item_text(row, 0)
            id_stoc = int(id_stoc_text) if id_stoc_text.isdigit() else None
            piese.append({
                "piesa":          self._item_text(row, 1),
                "cant":           self._safe_float(self._item_text(row, 2)),
                "pret_fara_tva":  self._safe_float(self._item_text(row, 3)),
                "tva":            self._safe_float(self._item_text(row, 4)),
                "total":          self._safe_float(self._item_text(row, 5)),
                "id_piesa_stoc":  id_stoc,
            })
        return piese

    # =========================================================
    # APPLY LANGUAGE
    # =========================================================
    def apply_language(self):
        lang = self.parent.app_language
        if lang == "RO":
            self.tabs.setTabText(0, "Manopere")
            self.tabs.setTabText(1, "Piese")
            self.cmb_filter.blockSignals(True)
            self.cmb_filter.clear()
            self.cmb_filter.addItems(["Toate", "In lucru", "Finalizate"])
            self.cmb_filter.blockSignals(False)
            self.table_lucrari.setHorizontalHeaderLabels([
                "", "ID", "Descriere", "Ore RAR", "Tarif/ora",
                "Pret fara TVA", "TVA", "Total", "Status", "Mecanic"
            ])
            self.btn_add.setText("➕ Adauga lucrare")
            self.btn_edit.setText("✏️ Editeaza")
            self.btn_delete.setText("🗑️ Sterge")
            self.btn_finalizare.setText("✔ Finalizare lucrari")
            self.table_piese.setHorizontalHeaderLabels(
                ["ID Stoc", "Piesa", "Cantitate", "Pret fara TVA", "TVA", "Total"])
            self.btn_delete_piesa.setText("🗑️ Sterge piesa selectata")
            self.btn_finalizare_piese.setText("✔ Finalizare lucrari")
        else:
            self.tabs.setTabText(0, "Labor")
            self.tabs.setTabText(1, "Parts")
            self.cmb_filter.blockSignals(True)
            self.cmb_filter.clear()
            self.cmb_filter.addItems(["All", "In progress", "Completed"])
            self.cmb_filter.blockSignals(False)
            self.table_lucrari.setHorizontalHeaderLabels([
                "", "ID", "Description", "RAR hours", "Rate/hour",
                "Price excl. VAT", "VAT", "Total", "Status", "Mechanic"
            ])
            self.btn_add.setText("➕ Add work")
            self.btn_edit.setText("✏️ Edit")
            self.btn_delete.setText("🗑️ Delete")
            self.btn_finalizare.setText("✔ Finalize works")
            self.table_piese.setHorizontalHeaderLabels(
                ["ID Stock", "Part", "Quantity", "Price excl. VAT", "VAT", "Total"])
            self.btn_delete_piesa.setText("🗑️ Remove selected part")
            self.btn_finalizare_piese.setText("✔ Finalize works")