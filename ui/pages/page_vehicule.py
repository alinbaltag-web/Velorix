from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QHeaderView, QTableWidgetItem,
    QAbstractItemView, QMessageBox, QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QBrush


class _HighlightDelegate(QStyledItemDelegate):
    """Coloreaza fundalul randurilor cu lucrari nefinalizate."""
    def paint(self, painter, option, index):
        if index.data(Qt.UserRole) and not (option.state & 0x0002):  # State_Selected
            painter.save()
            painter.fillRect(option.rect, QColor("#fff3cd"))
            painter.restore()
        super().paint(painter, option, index)
from ui.data_marci_modele import MARCI_MODELE
from database import get_connection, log_action
from ui.widgets.empty_table_overlay import EmptyTableOverlay
from ui.utils_toast import show_toast
from ui.vin_decoder import decode_vin
from ui.dialogs.dialog_vehicul import DialogVehicul
from ui.widgets.search_bar import SearchBar

class PageVehicule(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.selected_vehicul_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # ---------------------------------------------------------
        # LABEL CLIENT SELECTAT
        # ---------------------------------------------------------
        self.lbl_client = QLabel("Client selectat: -")
        layout.addWidget(self.lbl_client)

        # ---------------------------------------------------------
        # CAUTARE VEHICULE
        # ---------------------------------------------------------
        self.search_vehicul = SearchBar(placeholder="Cauta dupa marca, model, VIN sau numar...")
        self.search_vehicul.search_triggered.connect(self.filter_vehicule)
        layout.addWidget(self.search_vehicul)

        # ---------------------------------------------------------
        # TABEL VEHICULE
        # ---------------------------------------------------------
        self.table_vehicule = QTableWidget()

        from ui.widgets.checkbox_header import CheckBoxHeader
        header = CheckBoxHeader(Qt.Horizontal, self.table_vehicule)
        header.clicked.connect(self._select_all_rows)
        self.table_vehicule.setHorizontalHeader(header)

        self.table_vehicule.setFocusPolicy(Qt.NoFocus)
        self.table_vehicule.setColumnCount(9)
        self.table_vehicule.setHorizontalHeaderLabels([
            "", "ID", "Marca", "Model", "An", "VIN",
            "Nr. inmatriculare", "CC", "KM"
        ])

        h = self.table_vehicule.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        h.setSectionResizeMode(0, QHeaderView.Interactive)

        self.table_vehicule.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_vehicule.setSelectionMode(QAbstractItemView.MultiSelection)
        self.table_vehicule.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table_vehicule.setItemDelegate(_HighlightDelegate(self.table_vehicule))

        self.table_vehicule.cellClicked.connect(self._on_cell_clicked)
        self.table_vehicule.cellDoubleClicked.connect(lambda row, col: self.edit_vehicul())
        self.table_vehicule.viewport().installEventFilter(self)

        layout.addWidget(self.table_vehicule)

        # ---------------------------------------------------------
        # BUTOANE
        # ---------------------------------------------------------
        btns = QHBoxLayout()

        self.btn_add = QPushButton("➕ Adauga vehicul")
        self.btn_add.setObjectName("primary")

        self.btn_edit = QPushButton("✏️ Editeaza")
        self.btn_edit.setObjectName("primary")

        self.btn_delete = QPushButton("🗑️ Sterge")
        self.btn_delete.setObjectName("danger")

        self.btn_add.clicked.connect(self.adauga_vehicul)
        self.btn_edit.clicked.connect(self.edit_vehicul)
        self.btn_delete.clicked.connect(self.delete_vehicul)

        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_delete)
        btns.addStretch()

        layout.addLayout(btns)

        # Ascunde butoanele de modificare daca rolul nu are permisiune
        if not self.parent.permisiuni.get("vehicule_modificare", False):
            self.btn_add.hide()
            self.btn_edit.hide()
            self.btn_delete.hide()

        # ---------------------------------------------------------
        # APLICA LIMBA (ACUM EXISTA TOATE ELEMENTELE)
        # ---------------------------------------------------------
        self.apply_language()

        # ---------------------------------------------------------
        # INCARCARE + RESTAURARE LATIMI (ACUM FORMULARUL EXISTA)
        # ---------------------------------------------------------
        self._empty_overlay = EmptyTableOverlay(self.table_vehicule, "Niciun vehicul inregistrat.\nApasa '➕ Adauga vehicul' pentru a incepe.")
        self.load_vehicule()
        self.restore_table_state()

        h.sectionResized.connect(lambda *_: self.save_table_state())

    # =========================================================
    # HELPER: VALIDARE NUMERICA
    # =========================================================
    def _safe_int(self, text):
        try:
            return int(text)
        except:
            return None

    # =========================================================
    # HELPER: GENERARE RAND IN TABEL
    # =========================================================
    def _add_vehicle_row(self, row_index, vehicul, has_active=False):
        self.table_vehicule.insertRow(row_index)

        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        chk.setCheckState(Qt.Unchecked)
        chk.setTextAlignment(Qt.AlignCenter)
        self.table_vehicule.setItem(row_index, 0, chk)

        for col, val in enumerate(vehicul):
            self.table_vehicule.setItem(row_index, col + 1, QTableWidgetItem(str(val)))

        if has_active:
            for col in range(self.table_vehicule.columnCount()):
                item = self.table_vehicule.item(row_index, col)
                if item:
                    item.setData(Qt.UserRole, True)

        self.table_vehicule.setRowHeight(row_index, 28)

    # =========================================================
    # INCARCARE VEHICULE
    # =========================================================
    def load_vehicule(self):
        self.table_vehicule.blockSignals(True)
        try:
            self.table_vehicule.setRowCount(0)

            con = get_connection()
            cur = con.cursor()

            if self.parent.selected_client_id:
                cur.execute("""
                    SELECT v.id, v.marca, v.model, v.an, v.vin, v.nr, v.cc, v.km,
                           CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                    FROM vehicule v
                    LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                    WHERE v.id_client = ?
                    GROUP BY v.id
                    ORDER BY v.id DESC
                """, (self.parent.selected_client_id,))
            else:
                cur.execute("""
                    SELECT v.id, v.marca, v.model, v.an, v.vin, v.nr, v.cc, v.km,
                           CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                    FROM vehicule v
                    LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                    GROUP BY v.id
                    ORDER BY v.id DESC
                """)
            rows = cur.fetchall()
            con.close()

            for i, vehicul in enumerate(rows):
                self._add_vehicle_row(i, vehicul[:8], has_active=bool(vehicul[8]))
        finally:
            self.table_vehicule.blockSignals(False)

        if self.search_vehicul.text().strip():
            self.filter_vehicule(self.search_vehicul.text())

        self._empty_overlay.update_visibility()

    # =========================================================
    # EVENT FILTER
    # =========================================================
    def _select_all_rows(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        self.table_vehicule.blockSignals(True)
        if checked:
            self.table_vehicule.selectAll()
        else:
            self.table_vehicule.clearSelection()
        for row in range(self.table_vehicule.rowCount()):
            item = self.table_vehicule.item(row, 0)
            if item:
                item.setCheckState(state)
        self.table_vehicule.blockSignals(False)

    def _on_cell_clicked(self, row, col):
        # Aceasta metoda este apelata DOAR pentru col==0 (checkbox).
        # eventFilter consuma clickurile pe col!=0 si apeleaza select_vehicul acolo.
        item = self.table_vehicule.item(row, 0)
        if item:
            selected_rows = [i.row() for i in self.table_vehicule.selectedItems()]
            is_selected = row in selected_rows
            self.table_vehicule.blockSignals(True)
            item.setCheckState(Qt.Checked if is_selected else Qt.Unchecked)
            self.table_vehicule.blockSignals(False)

    def eventFilter(self, source, event):
        if source is self.table_vehicule.viewport():
            if event.type() == event.MouseButtonPress:
                index = self.table_vehicule.indexAt(event.pos())

                if not index.isValid():
                    self.table_vehicule.blockSignals(True)
                    self.table_vehicule.clearSelection()
                    for r in range(self.table_vehicule.rowCount()):
                        chk = self.table_vehicule.item(r, 0)
                        if chk:
                            chk.setCheckState(Qt.Unchecked)
                    self.table_vehicule.blockSignals(False)
                    self.selected_vehicul_id = None
                    self.parent.selected_vehicul_id = None
                    if hasattr(self.parent, "page_lucrari"):
                        self.parent.page_lucrari.selected_vehicul_id = None
                        self.parent.page_lucrari.lbl_vehicul.setText(
                            "Vehicul selectat: -" if self.parent.app_language == "RO" else "Selected vehicle: -"
                        )
                        self.parent.page_lucrari.load_lucrari()
                    if hasattr(self.parent, "page_devize"):
                        self.parent.page_devize.selected_vehicul_id = None
                        self.parent.page_devize.load_devize()
                    return True

                if index.column() != 0:
                    row = index.row()
                    id_item = self.table_vehicule.item(row, 1)
                    id_vehicul = int(id_item.text()) if id_item else None
                    is_deselect = (id_vehicul is not None and id_vehicul == self.parent.selected_vehicul_id)
                    self.table_vehicule.blockSignals(True)
                    self.table_vehicule.clearSelection()
                    if not is_deselect:
                        self.table_vehicule.selectRow(row)
                    for r in range(self.table_vehicule.rowCount()):
                        chk = self.table_vehicule.item(r, 0)
                        if chk and chk.checkState() == Qt.Checked:
                            self.table_vehicule.selectRow(r)
                    self.table_vehicule.blockSignals(False)
                    self.parent.select_vehicul(row, index.column())
                    return True

        return super().eventFilter(source, event)

    # =========================================================
    # FILTRARE VEHICULE
    # =========================================================
    def filter_vehicule(self, text):
        text = text.strip().lower()
        self.table_vehicule.setRowCount(0)

        con = get_connection()
        cur = con.cursor()

        if text == "":
            if self.parent.selected_client_id:
                cur.execute("""
                    SELECT v.id, v.marca, v.model, v.an, v.vin, v.nr, v.cc, v.km,
                           CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                    FROM vehicule v
                    LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                    WHERE v.id_client=?
                    GROUP BY v.id
                    ORDER BY v.id DESC
                """, (self.parent.selected_client_id,))
            else:
                cur.execute("""
                    SELECT v.id, v.marca, v.model, v.an, v.vin, v.nr, v.cc, v.km,
                           CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                    FROM vehicule v
                    LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                    GROUP BY v.id
                    ORDER BY v.id DESC
                """)
        else:
            like = f"%{text}%"

            if self.parent.selected_client_id:
                cur.execute("""
                    SELECT v.id, v.marca, v.model, v.an, v.vin, v.nr, v.cc, v.km,
                           CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                    FROM vehicule v
                    LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                    WHERE v.id_client=? AND (
                        LOWER(v.marca) LIKE ? OR LOWER(v.model) LIKE ? OR
                        LOWER(v.an) LIKE ? OR LOWER(v.vin) LIKE ? OR
                        LOWER(v.nr) LIKE ? OR LOWER(v.cc) LIKE ? OR LOWER(v.km) LIKE ?
                    )
                    GROUP BY v.id
                    ORDER BY v.id DESC
                """, (self.parent.selected_client_id, like, like, like, like, like, like, like))
            else:
                cur.execute("""
                    SELECT v.id, v.marca, v.model, v.an, v.vin, v.nr, v.cc, v.km,
                           CASE WHEN COUNT(l.id) > 0 THEN 1 ELSE 0 END
                    FROM vehicule v
                    LEFT JOIN lucrari l ON l.id_vehicul = v.id AND l.status != 'finalizat'
                    WHERE
                        LOWER(v.marca) LIKE ? OR LOWER(v.model) LIKE ? OR
                        LOWER(v.an) LIKE ? OR LOWER(v.vin) LIKE ? OR
                        LOWER(v.nr) LIKE ? OR LOWER(v.cc) LIKE ? OR LOWER(v.km) LIKE ?
                    GROUP BY v.id
                    ORDER BY v.id DESC
                """, (like, like, like, like, like, like, like))

        rows = cur.fetchall()
        con.close()

        for i, vehicul in enumerate(rows):
            self._add_vehicle_row(i, vehicul[:8], has_active=bool(vehicul[8]))

        self._empty_overlay.update_visibility()

    # =========================================================
    # SELECTARE VEHICUL
    # =========================================================
    def select_vehicul(self, row, col):
        id_item = self.table_vehicule.item(row, 1)
        if not id_item:
            return

        vehicul_id = int(id_item.text())
        self.selected_vehicul_id = vehicul_id

        if hasattr(self.parent, "page_lucrari"):
            self.parent.page_lucrari.set_vehicul(
                vehicul_id,
                f"{self.table_vehicule.item(row, 2).text()} "
                f"{self.table_vehicule.item(row, 3).text()}"
            )

        if hasattr(self.parent, "page_devize"):
            self.parent.page_devize.selected_vehicul_id = vehicul_id
            self.parent.page_devize.load_devize()

    # =========================================================
    # ADAUGA VEHICUL
    # =========================================================
    def adauga_vehicul(self):
        if not self.parent.selected_client_id:
            QMessageBox.warning(self, "Eroare", "Selecteaza un client inainte de a adauga un vehicul.")
            return

        dialog = DialogVehicul(self)
        if dialog.exec_() == DialogVehicul.Accepted:
            d = dialog.get_data()

            # Verificare VIN duplicat
            if d["vin"]:
                con = get_connection()
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM vehicule WHERE vin=?", (d["vin"],))
                if cur.fetchone()[0] > 0:
                    con.close()
                    show_toast(self.parent, "VIN deja existent")
                    return
                con.close()

            con = get_connection()
            cur = con.cursor()
            cur.execute("""
                INSERT INTO vehicule (marca, model, an, vin, nr, cc, km, culoare, combustibil, serie_motor, id_client)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d["marca"], d["model"], d["an"], d["vin"], d["nr"],
                d["cc"], d["km"], d["culoare"], d["combustibil"], d["serie_motor"],
                self.parent.selected_client_id
            ))
            con.commit()
            con.close()

            # Invatare VIN
            if d["vin"] and len(d["vin"]) >= 5 and d["marca"] and d["model"]:
                prefix = d["vin"][:5].upper()
                con = get_connection()
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM vin_family WHERE prefix=?", (prefix,))
                if cur.fetchone()[0] == 0:
                    cur.execute("""
                        INSERT INTO vin_family (prefix, marca, model, descriere, cc, year)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (prefix, d["marca"], d["model"], None, d["cc"], d["an"]))
                    con.commit()
                con.close()

            log_action(
                self.parent.logged_email,
                "Adaugare vehicul",
                f"{d['marca']} {d['model']} | Client ID={self.parent.selected_client_id}"
            )

            self.load_vehicule()
            self.table_vehicule.clearSelection()

            if hasattr(self.parent, "page_dashboard"):
                self.parent.page_dashboard.refresh_dashboard()

    def edit_vehicul(self):
        row = self.table_vehicule.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Atentie", "Selecteaza un vehicul din tabel pentru editare.")
            return

        id_vehicul = int(self.table_vehicule.item(row, 1).text())

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT marca, model, an, vin, nr, cc, km, culoare, combustibil, serie_motor
            FROM vehicule WHERE id=?
        """, (id_vehicul,))
        row_data = cur.fetchone()
        con.close()

        if not row_data:
            return

        vehicul_data = {
            "marca": row_data[0] or "",
            "model": row_data[1] or "",
            "an": row_data[2] or "",
            "vin": row_data[3] or "",
            "nr": row_data[4] or "",
            "cc": row_data[5] or "",
            "km": row_data[6] or "",
            "culoare": row_data[7] or "",
            "combustibil": row_data[8] or "Benzina",
            "serie_motor": row_data[9] or ""
        }

        dialog = DialogVehicul(self, vehicul_data)
        if dialog.exec_() == DialogVehicul.Accepted:
            d = dialog.get_data()

            con = get_connection()
            cur = con.cursor()
            cur.execute("""
                UPDATE vehicule SET marca=?, model=?, an=?, vin=?, nr=?, cc=?, km=?,
                culoare=?, combustibil=?, serie_motor=?
                WHERE id=?
            """, (
                d["marca"], d["model"], d["an"], d["vin"], d["nr"],
                d["cc"], d["km"], d["culoare"], d["combustibil"], d["serie_motor"],
                id_vehicul
            ))
            con.commit()
            con.close()

            log_action(self.parent.logged_email, "Editare vehicul", f"ID={id_vehicul} | {d['marca']} {d['model']}")
            self.load_vehicule()

            if hasattr(self.parent, "page_dashboard"):
                self.parent.page_dashboard.refresh_dashboard()    
    
    # =========================================================
    # STERGERE VEHICULE
    # =========================================================
    def delete_vehicul(self):
        rows = [
            r for r in range(self.table_vehicule.rowCount())
            if self.table_vehicule.item(r, 0)
            and self.table_vehicule.item(r, 0).checkState() == Qt.Checked
        ]

        if not rows:
            return

        if self.parent.app_language == "RO":
            msg = QMessageBox.question(
                self, "Confirmare stergere",
                "Esti sigur ca vrei sa stergi vehiculul/vehiculele selectate?",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            msg = QMessageBox.question(
                self, "Delete confirmation",
                "Are you sure you want to delete the selected vehicle(s)?",
                QMessageBox.Yes | QMessageBox.No
            )

        if msg != QMessageBox.Yes:
            return

        con = get_connection()
        cur = con.cursor()

        for r in rows:
            id_v = self.table_vehicule.item(r, 1).text()

            cur.execute("DELETE FROM vehicule WHERE id=?", (id_v,))
            log_action(self.parent.logged_email, "Stergere vehicul", f"ID={id_v}")

            cur.execute("DELETE FROM lucrari WHERE id_vehicul=?", (id_v,))
            cur.execute("DELETE FROM piese_lucrari WHERE id_vehicul=?", (id_v,))

        con.commit()
        con.close()

        self.load_vehicule()

        if hasattr(self.parent, "page_dashboard"):
            self.parent.page_dashboard.refresh_dashboard()

        if hasattr(self.parent, "page_lucrari"):
            self.parent.page_lucrari.load_lucrari()

        if hasattr(self.parent, "page_devize"):
            self.parent.page_devize.load_devize()


    # =========================================================
    # SALVARE STARE TABEL
    # =========================================================
    def save_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        settings.setValue("header", self.table_vehicule.horizontalHeader().saveState())
        settings.endGroup()

    # =========================================================
    # RESTAURARE STARE TABEL
    # =========================================================
    def restore_table_state(self):
        settings = QSettings("ServiceMoto", "UI")
        settings.beginGroup(self.__class__.__name__)
        header = settings.value("header")
        settings.endGroup()

        if header:
            self.table_vehicule.horizontalHeader().restoreState(header)



    def apply_language(self):
        lang = self.parent.app_language

        if lang == "RO":
            # Label client
            self.lbl_client.setText("Client selectat: -")

            # Cautare
            self.search_vehicul.setPlaceholderText("Cauta dupa marca, model, VIN sau numar...")

            # Header tabel
            self.table_vehicule.setHorizontalHeaderLabels([
                "", "ID", "Marca", "Model", "An", "VIN",
                "Nr. inmatriculare", "CC", "KM"
            ])

            # Butoane
            self.btn_add.setText("➕ Adauga vehicul")
            self.btn_edit.setText("✏️ Editeaza")
            self.btn_delete.setText("🗑️ Sterge")
        else:
            # Label client
            self.lbl_client.setText("Selected client: -")

            # Search
            self.search_vehicul.setPlaceholderText("Search by make, model, VIN or plate...")

            # Table header
            self.table_vehicule.setHorizontalHeaderLabels([
                "", "ID", "Make", "Model", "Year", "VIN",
                "License plate", "CC", "Mileage"
            ])

            # Buttons
            self.btn_add.setText("➕ Add vehicle")
            self.btn_edit.setText("✏️ Edit")
            self.btn_delete.setText("🗑️ Delete")