from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QHeaderView, QTableWidgetItem,
    QAbstractItemView, QMessageBox, QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QBrush
from ui.widgets.search_bar import SearchBar


class _HighlightDelegate(QStyledItemDelegate):
    """Coloreaza fundalul randurilor cu lucrari nefinalizate."""
    def paint(self, painter, option, index):
        if index.data(Qt.UserRole) and not (option.state & 0x0002):  # State_Selected
            painter.save()
            painter.fillRect(option.rect, QColor("#fff3cd"))
            painter.restore()
        super().paint(painter, option, index)
from database import log_action
from ui.crypto_utils import encrypt, decrypt
from ui.dialogs.dialog_client import DialogClient
from ui.widgets.empty_table_overlay import EmptyTableOverlay

class PageClienti(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.lbl_title = QLabel("Clienti")
        self.lbl_title.setObjectName("pageTitle")
        layout.addWidget(self.lbl_title)

        # ---------------------------------------------------------
        # Cautare clienti (cu debounce — nu face query la fiecare tasta)
        # ---------------------------------------------------------
        self.search_client = SearchBar(placeholder="Cauta dupa nume, telefon sau email...")
        self.search_client.search_triggered.connect(self.filter_clienti)
        layout.addWidget(self.search_client)

        # ---------------------------------------------------------
        # Tabel clienti
        # ---------------------------------------------------------
        self.table_clienti = QTableWidget()

        # Header cu checkbox
        from ui.widgets.checkbox_header import CheckBoxHeader
        header = CheckBoxHeader(Qt.Horizontal, self.table_clienti)
        header.clicked.connect(self._select_all_rows)
        self.table_clienti.setHorizontalHeader(header)

        self.table_clienti.setFocusPolicy(Qt.NoFocus)
        self.table_clienti.setColumnCount(7)
        self.table_clienti.setHorizontalHeaderLabels(["", "ID", "Tip", "Nume", "Telefon", "Email", "Adresa"])
        # Prima coloana (checkbox) manuala
        self.table_clienti.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)

        self.table_clienti.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_clienti.setSelectionMode(QAbstractItemView.MultiSelection)
        self.table_clienti.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table_clienti.setItemDelegate(_HighlightDelegate(self.table_clienti))

        # Evenimente
        self.table_clienti.cellClicked.connect(self._on_cell_clicked)
        self.table_clienti.cellDoubleClicked.connect(lambda row, col: self.edit_client())
        self.table_clienti.viewport().installEventFilter(self)

        layout.addWidget(self.table_clienti)

        # ---------------------------------------------------------
        # Incarcam datele
        # ---------------------------------------------------------
        self._empty_overlay = EmptyTableOverlay(self.table_clienti, "Niciun client inregistrat.\nApasa '➕ Adauga client' pentru a incepe.")
        self.load_clienti()

        # Coloane redimensionabile
        self.table_clienti.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # Restauram latimile salvate
        self.restore_table_state()

        # Salvam automat la redimensionare
        self.table_clienti.horizontalHeader().sectionResized.connect(self.save_table_state)

        # ---------------------------------------------------------
        # Butoane
        # ---------------------------------------------------------
        btns = QHBoxLayout()

        self.btn_add = QPushButton("➕ Adauga client")
        self.btn_add.setObjectName("primary")

        self.btn_edit = QPushButton("✏️ Editeaza")
        self.btn_edit.setObjectName("primary")

        self.btn_delete = QPushButton("🗑️ Sterge")
        self.btn_delete.setObjectName("danger")

        self.btn_add.clicked.connect(self.add_client)
        self.btn_edit.clicked.connect(self.edit_client)
        self.btn_delete.clicked.connect(self.delete_client)

        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_delete)
        btns.addStretch()

        layout.addLayout(btns)

        # Ascunde butoanele de modificare daca rolul nu are permisiune
        if not self.parent.permisiuni.get("clienti_modificare", False):
            self.btn_add.hide()
            self.btn_edit.hide()
            self.btn_delete.hide()

        # ---------------------------------------------------------
        # Aplica limba
        # ---------------------------------------------------------
        self.apply_language()

    # ---------------------------------------------------------
    # APLICARE LIMBA
    # ---------------------------------------------------------
    def apply_language(self):
        lang = self.parent.app_language

        if lang == "RO":
            self.search_client.setPlaceholderText("Cauta dupa nume, telefon sau email...")
            self.table_clienti.setHorizontalHeaderLabels(["", "ID", "Tip", "Nume", "Telefon", "Email", "Adresa"])            

            self.btn_add.setText("➕ Adauga client")
            self.btn_edit.setText("✏️ Editeaza")
            self.btn_delete.setText("🗑️ Sterge")


        else:
            self.search_client.setPlaceholderText("Search by name, phone or email...")
            self.table_clienti.setHorizontalHeaderLabels(["", "ID", "Type", "Name", "Phone", "Email", "Address"])            
            
            self.btn_add.setText("➕ Add client")
            self.btn_edit.setText("✏️ Edit")
            self.btn_delete.setText("🗑️ Delete")

        if lang == "RO":
            self.lbl_title.setText("Clienti")
        else:
            self.lbl_title.setText("Clients")            
    # ---------------------------------------------------------
    # EVENT FILTER — click in zona alba
    # ---------------------------------------------------------
    def _select_all_rows(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        self.table_clienti.blockSignals(True)
        if checked:
            self.table_clienti.selectAll()
        else:
            self.table_clienti.clearSelection()
        for row in range(self.table_clienti.rowCount()):
            item = self.table_clienti.item(row, 0)
            if item:
                item.setCheckState(state)
        self.table_clienti.blockSignals(False)

    def _on_cell_clicked(self, row, col):
        # Aceasta metoda este apelata DOAR pentru col==0 (checkbox) deoarece
        # eventFilter consuma clickurile pe col!=0 si apeleaza select_client acolo.
        item = self.table_clienti.item(row, 0)
        if item:
            selected_rows = [i.row() for i in self.table_clienti.selectedItems()]
            is_selected = row in selected_rows
            self.table_clienti.blockSignals(True)
            item.setCheckState(Qt.Checked if is_selected else Qt.Unchecked)
            self.table_clienti.blockSignals(False)

    def eventFilter(self, source, event):
        if source is self.table_clienti.viewport():
            if event.type() == event.MouseButtonPress:
                index = self.table_clienti.indexAt(event.pos())
                if not index.isValid():
                    self.table_clienti.blockSignals(True)
                    self.table_clienti.clearSelection()
                    for r in range(self.table_clienti.rowCount()):
                        chk = self.table_clienti.item(r, 0)
                        if chk:
                            chk.setCheckState(Qt.Unchecked)
                    self.table_clienti.blockSignals(False)
                    self.parent.deselect_client()
                    return True
                if index.column() != 0:
                    row = index.row()
                    id_item = self.table_clienti.item(row, 1)
                    id_client = int(id_item.text()) if id_item else None
                    is_deselect = (id_client is not None and id_client == self.parent.selected_client_id)
                    self.table_clienti.blockSignals(True)
                    self.table_clienti.clearSelection()
                    if not is_deselect:
                        self.table_clienti.selectRow(row)
                    for r in range(self.table_clienti.rowCount()):
                        chk = self.table_clienti.item(r, 0)
                        if chk and chk.checkState() == Qt.Checked:
                            self.table_clienti.selectRow(r)
                    self.table_clienti.blockSignals(False)
                    self.parent.select_client(row, index.column())
                    return True
        return super().eventFilter(source, event)

    # ---------------------------------------------------------
    # INCARCARE CLIENTI
    # ---------------------------------------------------------
    def load_clienti(self):
        from database import get_connection

        self.table_clienti.blockSignals(True)
        try:
            self.table_clienti.setRowCount(0)

            con = get_connection()
            cur = con.cursor()

            cur.execute("""
                SELECT c.id, c.tip, c.nume, c.telefon, c.email, c.adresa,
                       CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                FROM clienti c
                LEFT JOIN vehicule v ON v.id_client = c.id
                LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                GROUP BY c.id
                ORDER BY c.id DESC
            """)
            rows = cur.fetchall()
            con.close()

            for r, c in enumerate(rows):
                self.table_clienti.insertRow(r)

                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                chk.setCheckState(Qt.Unchecked)
                chk.setTextAlignment(Qt.AlignCenter)
                self.table_clienti.setItem(r, 0, chk)

                self.table_clienti.setItem(r, 1, QTableWidgetItem(str(c[0])))
                self.table_clienti.setItem(r, 2, QTableWidgetItem(c[1] if c[1] else ""))
                self.table_clienti.setItem(r, 3, QTableWidgetItem(c[2]))
                self.table_clienti.setItem(r, 4, QTableWidgetItem(c[3] if c[3] else ""))
                self.table_clienti.setItem(r, 5, QTableWidgetItem(c[4] if c[4] else ""))
                self.table_clienti.setItem(r, 6, QTableWidgetItem(c[5] if c[5] else ""))

                if c[6]:  # are lucrari nefinalizate
                    for col in range(self.table_clienti.columnCount()):
                        item = self.table_clienti.item(r, col)
                        if item:
                            item.setData(Qt.UserRole, True)
        finally:
            self.table_clienti.blockSignals(False)

        if self.search_client.text().strip():
            self.filter_clienti(self.search_client.text())
        self._empty_overlay.update_visibility()
    # ---------------------------------------------------------
    # CRUD — ADAUGA
    # ---------------------------------------------------------
    def _check_duplicate_client(self, nume, telefon, email, exclude_id=None):
        """
        Verifica daca exista deja un client cu acelasi nume sau acelasi telefon/email.
        Returneaza lista de duplicate gasite (poate fi goala).
        """
        from database import get_connection
        con = get_connection()
        cur = con.cursor()
        conditions = []
        params = []
        if nume:
            conditions.append("LOWER(TRIM(nume)) = LOWER(TRIM(?))")
            params.append(nume)
        if telefon:
            conditions.append("REPLACE(REPLACE(telefon,' ',''),'-','') = REPLACE(REPLACE(?,' ',''),'-','')")
            params.append(telefon)
        if email:
            conditions.append("LOWER(TRIM(email)) = LOWER(TRIM(?))")
            params.append(email)

        if not conditions:
            con.close()
            return []

        sql = f"SELECT id, nume, telefon, email FROM clienti WHERE ({' OR '.join(conditions)})"
        if exclude_id:
            sql += " AND id != ?"
            params.append(exclude_id)

        cur.execute(sql, params)
        duplicates = cur.fetchall()
        con.close()
        return duplicates

    def add_client(self):
        dialog = DialogClient(self)
        if dialog.exec_() == DialogClient.Accepted:
            d = dialog.get_data()

            # Verificare duplicate
            duplicates = self._check_duplicate_client(d["nume"], d["telefon"], d["email"])
            if duplicates:
                dup_info = "\n".join([f"• ID {r[0]}: {r[1]} | {r[2] or '-'} | {r[3] or '-'}" for r in duplicates])
                reply = QMessageBox.question(
                    self, "Client posibil duplicat",
                    f"Exista deja un client similar:\n{dup_info}\n\nDoresti sa adaugi oricum?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            from database import get_connection
            con = get_connection()
            try:
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO clienti (tip, nume, telefon, email, adresa, cui_cnp, observatii)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (d["tip"], d["nume"], d["telefon"], d["email"], d["adresa"], encrypt(d["cui_cnp"]), d["observatii"]))
                con.commit()
            finally:
                con.close()

            log_action(self.parent.logged_email, "Adaugare client", f"{d['nume']} | {d['telefon']}")
            self.load_clienti()

    def edit_client(self):
        row = self.table_clienti.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Atentie", "Selecteaza un client din tabel pentru editare.")
            return

        id_client = int(self.table_clienti.item(row, 1).text())

        from database import get_connection
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT tip, nume, telefon, email, adresa, cui_cnp, observatii FROM clienti WHERE id=?", (id_client,))
        row_data = cur.fetchone()
        con.close()

        if not row_data:
            return

        client_data = {
            "tip": row_data[0] or "Persoana Fizica",
            "nume": row_data[1] or "",
            "telefon": row_data[2] or "",
            "email": row_data[3] or "",
            "adresa": row_data[4] or "",
            "cui_cnp": decrypt(row_data[5] or ""),
            "observatii": row_data[6] or ""
        }

        dialog = DialogClient(self, client_data)
        if dialog.exec_() == DialogClient.Accepted:
            d = dialog.get_data()

            # Verificare duplicate (excludem clientul curent)
            duplicates = self._check_duplicate_client(d["nume"], d["telefon"], d["email"], exclude_id=id_client)
            if duplicates:
                dup_info = "\n".join([f"• ID {r[0]}: {r[1]} | {r[2] or '-'} | {r[3] or '-'}" for r in duplicates])
                reply = QMessageBox.question(
                    self, "Client posibil duplicat",
                    f"Exista deja un client similar:\n{dup_info}\n\nDoresti sa salvezi oricum?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            con = get_connection()
            try:
                cur = con.cursor()
                cur.execute("""
                    UPDATE clienti SET tip=?, nume=?, telefon=?, email=?, adresa=?, cui_cnp=?, observatii=?
                    WHERE id=?
                """, (d["tip"], d["nume"], d["telefon"], d["email"], d["adresa"], encrypt(d["cui_cnp"]), d["observatii"], id_client))
                con.commit()
            finally:
                con.close()

            log_action(self.parent.logged_email, "Editare client", f"ID={id_client} | {d['nume']}")
            self.load_clienti()
    # ---------------------------------------------------------
    # STERGERE CLIENT
    # ---------------------------------------------------------
    def delete_client(self):
        rows = []
        for r in range(self.table_clienti.rowCount()):
            chk = self.table_clienti.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                rows.append(r)

        if not rows:
            return

        from database import get_connection
        con = get_connection()
        cur = con.cursor()

        # Colecteaza statistici pentru avertizare
        ids = [self.table_clienti.item(r, 1).text() for r in rows]
        total_vehicule = 0
        total_devize = 0
        for id_c in ids:
            cur.execute("SELECT COUNT(*) FROM vehicule WHERE id_client=?", (id_c,))
            total_vehicule += cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM devize WHERE id_client=?", (id_c,))
            total_devize += cur.fetchone()[0]

        if self.parent.app_language == "RO":
            detalii = ""
            if total_vehicule or total_devize:
                detalii = (f"\n\n⚠️ Vor fi sterse si:\n"
                           f"  • {total_vehicule} vehicul(e) asociat(e)\n"
                           f"  • {total_devize} deviz(e) asociat(e)\n\n"
                           f"Aceasta actiune este permanenta si nu poate fi anulata!")
            msg = QMessageBox.question(self, "Confirmare stergere",
                                       f"Stergi {len(rows)} client(i) selectat(i)?{detalii}",
                                       QMessageBox.Yes | QMessageBox.No)
        else:
            detalii = ""
            if total_vehicule or total_devize:
                detalii = (f"\n\n⚠️ This will also delete:\n"
                           f"  • {total_vehicule} associated vehicle(s)\n"
                           f"  • {total_devize} associated estimate(s)\n\n"
                           f"This action is permanent and cannot be undone!")
            msg = QMessageBox.question(self, "Delete confirmation",
                                       f"Delete {len(rows)} selected client(s)?{detalii}",
                                       QMessageBox.Yes | QMessageBox.No)

        if msg != QMessageBox.Yes:
            con.close()
            return

        for id_c in ids:
            cur.execute("DELETE FROM clienti WHERE id=?", (id_c,))
            log_action(self.parent.logged_email, "Stergere client", f"ID={id_c}")

        con.commit()
        con.close()
        self.load_clienti()

    # ---------------------------------------------------------
    # FILTRARE CLIENTI
    # ---------------------------------------------------------
    def filter_clienti(self, text):
        from database import get_connection

        text = text.strip().lower()
        self.table_clienti.blockSignals(True)
        self.table_clienti.setRowCount(0)

        con = get_connection()
        cur = con.cursor()

        if text == "":
            cur.execute("""
                SELECT c.id, c.tip, c.nume, c.telefon, c.email, c.adresa,
                       CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                FROM clienti c
                LEFT JOIN vehicule v ON v.id_client = c.id
                LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                GROUP BY c.id
                ORDER BY c.id DESC
            """)
        else:
            cur.execute("""
                SELECT c.id, c.tip, c.nume, c.telefon, c.email, c.adresa,
                       CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                FROM clienti c
                LEFT JOIN vehicule v ON v.id_client = c.id
                LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                WHERE LOWER(c.nume) LIKE ? OR c.telefon LIKE ? OR LOWER(c.email) LIKE ?
                GROUP BY c.id
                ORDER BY c.id DESC
            """, (f"%{text}%", f"%{text}%", f"%{text}%"))
        rows = cur.fetchall()
        con.close()

        for r, c in enumerate(rows):
            self.table_clienti.insertRow(r)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            chk.setCheckState(Qt.Unchecked)
            chk.setTextAlignment(Qt.AlignCenter)
            self.table_clienti.setItem(r, 0, chk)

            self.table_clienti.setItem(r, 1, QTableWidgetItem(str(c[0])))
            self.table_clienti.setItem(r, 2, QTableWidgetItem(c[1] if c[1] else ""))
            self.table_clienti.setItem(r, 3, QTableWidgetItem(c[2]))
            self.table_clienti.setItem(r, 4, QTableWidgetItem(c[3] if c[3] else ""))
            self.table_clienti.setItem(r, 5, QTableWidgetItem(c[4] if c[4] else ""))
            self.table_clienti.setItem(r, 6, QTableWidgetItem(c[5] if c[5] else ""))

            if c[6]:  # are lucrari nefinalizate
                for col in range(self.table_clienti.columnCount()):
                    item = self.table_clienti.item(r, col)
                    if item:
                        item.setData(Qt.UserRole, True)

        self.table_clienti.blockSignals(False)
        self._empty_overlay.update_visibility()
    # ---------------------------------------------------------
    # SALVARE STARE TABEL
    # ---------------------------------------------------------
    def save_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        settings.setValue("header", self.table_clienti.horizontalHeader().saveState())
        settings.endGroup()

    # ---------------------------------------------------------
    # RESTAURARE STARE TABEL
    # ---------------------------------------------------------
    def restore_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        header = settings.value("header")
        settings.endGroup()

        if header:
            self.table_clienti.horizontalHeader().restoreState(header)
