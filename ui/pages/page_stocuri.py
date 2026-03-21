from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox,
    QHeaderView, QFrame, QSizePolicy, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QFont
from database import get_connection, get_tva
from ui.utils_toast import show_toast
from ui.session_manager import SessionManager
from ui.widgets.empty_table_overlay import EmptyTableOverlay
from ui.widgets.search_bar import SearchBar


class PageStocuri(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("ServiceMoto", "Stocuri")
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # === HEADER ===
        header = QHBoxLayout()
        self.lbl_titlu = QLabel("Stocuri & Piese")
        self.lbl_titlu.setObjectName("pageTitle")
        header.addWidget(self.lbl_titlu)
        header.addStretch()

        self.btn_adauga = QPushButton("+ Adauga Piesa")
        self.btn_adauga.setObjectName("primaryButton")
        self.btn_adauga.clicked.connect(self.adauga_piesa)
        header.addWidget(self.btn_adauga)

        self.btn_export = QPushButton("Export CSV")
        self.btn_export.setObjectName("secondaryButton")
        self.btn_export.clicked.connect(self.export_csv)
        header.addWidget(self.btn_export)

        main_layout.addLayout(header)

        # === KPI CARDS ===
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_total = self._make_card("Total Piese", "0", "#3b82f6")
        self.card_valoare = self._make_card("Valoare Stoc", "0 RON", "#10b981")
        self.card_critic = self._make_card("Stoc Critic", "0", "#ef4444")
        self.card_categorii = self._make_card("Categorii", "0", "#f59e0b")

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_valoare)
        cards_layout.addWidget(self.card_critic)
        cards_layout.addWidget(self.card_categorii)
        main_layout.addLayout(cards_layout)

        # === FILTRE ===
        filtre_frame = QFrame()
        filtre_frame.setObjectName("filterFrame")
        filtre_layout = QHBoxLayout(filtre_frame)
        filtre_layout.setContentsMargins(12, 8, 12, 8)
        filtre_layout.setSpacing(10)

        self.lbl_cauta = QLabel("Cauta:")
        filtre_layout.addWidget(self.lbl_cauta)

        self.input_search = SearchBar(placeholder="Nume, cod, furnizor...")
        self.input_search.setMinimumWidth(220)
        self.input_search.search_triggered.connect(lambda _: self.load_data())
        filtre_layout.addWidget(self.input_search)

        self.lbl_cat = QLabel("Categorie:")
        filtre_layout.addWidget(self.lbl_cat)

        self.combo_categorie = QComboBox()
        self.combo_categorie.setMinimumWidth(150)
        self.combo_categorie.currentIndexChanged.connect(self.load_data)
        filtre_layout.addWidget(self.combo_categorie)

        self.lbl_stoc = QLabel("Stoc:")
        filtre_layout.addWidget(self.lbl_stoc)

        self.combo_stoc = QComboBox()
        self.combo_stoc.addItems(["Toate", "Stoc OK", "Stoc Critic", "Stoc Zero"])
        self.combo_stoc.currentIndexChanged.connect(self.load_data)
        filtre_layout.addWidget(self.combo_stoc)

        self.btn_reset = QPushButton("Reseteaza")
        self.btn_reset.setObjectName("secondaryButton")
        self.btn_reset.clicked.connect(self.reset_filtre)
        filtre_layout.addWidget(self.btn_reset)

        filtre_layout.addStretch()
        main_layout.addWidget(filtre_frame)

        # === TABEL ===
        self.tabel = QTableWidget()
        self.tabel.setObjectName("dataTable")
        self.tabel.setColumnCount(11)
        self.tabel.setHorizontalHeaderLabels([
            "ID", "Cod", "Nume Piesa", "Categorie",
            "Stoc Curent", "Stoc Minim", "UM",
            "Pret Achizitie", "Pret Vanzare", "Furnizor", "Actiuni"
        ])
        self.tabel.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabel.setAlternatingRowColors(True)
        self.tabel.verticalHeader().setVisible(False)
        self.tabel.setColumnHidden(0, True)

        header_tabel = self.tabel.horizontalHeader()
        header_tabel.setSectionResizeMode(2, QHeaderView.Stretch)
        header_tabel.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_tabel.setSectionResizeMode(9, QHeaderView.ResizeToContents)

        main_layout.addWidget(self.tabel)

        self._empty_overlay = EmptyTableOverlay(self.tabel, "Nicio piesa in stoc.\nApasa '+ Adauga Piesa' pentru a incepe.")

        # === STATUS BAR ===
        self.lbl_status = QLabel("Se incarca...")
        self.lbl_status.setObjectName("statusLabel")
        main_layout.addWidget(self.lbl_status)

        self.load_categorii()

    def _make_card(self, titlu, valoare, culoare):
        frame = QFrame()
        frame.setObjectName("kpiCard")
        frame.setMinimumHeight(80)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)

        lbl_val = QLabel(valoare)
        lbl_val.setObjectName("kpiValue")
        lbl_val.setStyleSheet(f"color: {culoare}; font-size: 22px; font-weight: bold;")

        lbl_tit = QLabel(titlu)
        lbl_tit.setObjectName("kpiTitle")
        lbl_tit.setStyleSheet("color: #94a3b8; font-size: 12px;")

        layout.addWidget(lbl_val)
        layout.addWidget(lbl_tit)

        frame._value_label = lbl_val
        return frame

    def load_categorii(self):
        self.combo_categorie.blockSignals(True)
        self.combo_categorie.clear()
        self.combo_categorie.addItem("Toate categoriile", None)
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT id, nume FROM categorii_piese ORDER BY nume")
        for row in cur.fetchall():
            self.combo_categorie.addItem(row[1], row[0])
        con.close()
        self.combo_categorie.blockSignals(False)

    def load_data(self):
        search = self.input_search.text().strip()
        cat_id = self.combo_categorie.currentData()
        filtru_stoc = self.combo_stoc.currentText()

        query = """
            SELECT s.id, s.cod, s.nume, c.nume, s.stoc_curent, s.stoc_minim,
                   s.unitate, s.pret_achizitie, s.pret_vanzare, s.furnizor
            FROM stoc_piese s
            LEFT JOIN categorii_piese c ON s.id_categorie = c.id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (s.nume LIKE ? OR s.cod LIKE ? OR s.furnizor LIKE ?)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]

        if cat_id:
            query += " AND s.id_categorie = ?"
            params.append(cat_id)

        if filtru_stoc == "Stoc Critic":
            query += " AND s.stoc_curent > 0 AND s.stoc_curent <= s.stoc_minim"
        elif filtru_stoc == "Stoc Zero":
            query += " AND s.stoc_curent <= 0"
        elif filtru_stoc == "Stoc OK":
            query += " AND s.stoc_curent > s.stoc_minim"

        query += " ORDER BY s.nume"

        con = get_connection()
        cur = con.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        con.close()

        self.tabel.setRowCount(0)
        total_valoare = 0
        stoc_critic = 0

        for row in rows:
            r = self.tabel.rowCount()
            self.tabel.insertRow(r)

            for col, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.tabel.setItem(r, col, item)

            # Colorare stoc critic
            stoc_curent = float(row[4]) if row[4] else 0
            stoc_minim = float(row[5]) if row[5] else 0
            pret_ach = float(row[7]) if row[7] else 0
            total_valoare += stoc_curent * pret_ach

            if stoc_curent <= 0:
                for col in range(10):
                    if self.tabel.item(r, col):
                        self.tabel.item(r, col).setBackground(QColor("#3d1515"))
                stoc_critic += 1
            elif stoc_curent <= stoc_minim:
                for col in range(10):
                    if self.tabel.item(r, col):
                        self.tabel.item(r, col).setBackground(QColor("#3d2e00"))
                stoc_critic += 1

            # Butoane actiuni
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            btn_edit = QPushButton("✏️")
            btn_edit.setFixedSize(30, 26)
            btn_edit.setToolTip("Editeaza")
            btn_edit.clicked.connect(lambda _, rid=row[0]: self.editeaza_piesa(rid))

            btn_miscare = QPushButton("📦")
            btn_miscare.setFixedSize(30, 26)
            btn_miscare.setToolTip("Adauga/Scade stoc")
            btn_miscare.clicked.connect(lambda _, rid=row[0]: self.miscare_stoc(rid))

            btn_del = QPushButton("🗑️")
            btn_del.setFixedSize(30, 26)
            btn_del.setToolTip("Sterge")
            btn_del.clicked.connect(lambda _, rid=row[0]: self.sterge_piesa(rid))

            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_miscare)
            btn_layout.addWidget(btn_del)
            self.tabel.setCellWidget(r, 10, btn_widget)

        # Update KPI cards
        self.card_total._value_label.setText(str(len(rows)))
        self.card_valoare._value_label.setText(f"{total_valoare:,.2f} RON")
        self.card_critic._value_label.setText(str(stoc_critic))

        con2 = get_connection()
        cur2 = con2.cursor()
        cur2.execute("SELECT COUNT(*) FROM categorii_piese")
        nr_cat = cur2.fetchone()[0]
        con2.close()
        self.card_categorii._value_label.setText(str(nr_cat))

        self.lbl_status.setText(f"{len(rows)} piese gasite")
        self._empty_overlay.update_visibility()

    def reset_filtre(self):
        self.input_search.clear()
        self.combo_categorie.setCurrentIndex(0)
        self.combo_stoc.setCurrentIndex(0)

    def adauga_piesa(self):
        from ui.dialogs.dialog_piesa import DialogPiesa
        dlg = DialogPiesa(self)
        if dlg.exec_():
            self.load_data()
            show_toast(self, "Piesa adaugata cu succes!", "success")

    def editeaza_piesa(self, piesa_id):
        from ui.dialogs.dialog_piesa import DialogPiesa
        dlg = DialogPiesa(self, piesa_id=piesa_id)
        if dlg.exec_():
            self.load_data()
            show_toast(self, "Piesa actualizata!", "success")

    def miscare_stoc(self, piesa_id):
        from ui.dialogs.dialog_miscare_stoc import DialogMiscareStoc
        dlg = DialogMiscareStoc(self, piesa_id=piesa_id)
        if dlg.exec_():
            self.load_data()
            show_toast(self, "Stoc actualizat!")

    def sterge_piesa(self, piesa_id):
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT nume FROM stoc_piese WHERE id=?", (piesa_id,))
        row = cur.fetchone()
        con.close()
        if not row:
            return
        lang = getattr(self.parent, "app_language", "RO") if hasattr(self, "parent") else "RO"
        if lang == "RO":
            raspuns = QMessageBox.question(
                self, "Confirmare stergere",
                f"Stergi piesa '{row[0]}'?",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            raspuns = QMessageBox.question(
                self, "Delete confirmation",
                f"Delete part '{row[0]}'?",
                QMessageBox.Yes | QMessageBox.No
            )
        if raspuns == QMessageBox.Yes:
            con = get_connection()
            cur = con.cursor()
            cur.execute("DELETE FROM miscari_stoc WHERE id_piesa=?", (piesa_id,))
            cur.execute("DELETE FROM stoc_piese WHERE id=?", (piesa_id,))
            con.commit()
            con.close()
            self.load_data()
            show_toast(self, "Piesa stearsa!")

    def export_csv(self):
        import csv
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"stoc_{datetime.now().strftime('%Y%m%d')}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT s.cod, s.nume, c.nume, s.stoc_curent, s.stoc_minim,
                   s.unitate, s.pret_achizitie, s.pret_vanzare, s.furnizor
            FROM stoc_piese s
            LEFT JOIN categorii_piese c ON s.id_categorie = c.id
            ORDER BY s.nume
        """)
        rows = cur.fetchall()
        con.close()
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Cod", "Nume", "Categorie", "Stoc Curent",
                             "Stoc Minim", "UM", "Pret Achizitie", "Pret Vanzare", "Furnizor"])
            writer.writerows(rows)
        show_toast(self, f"Export salvat!", "success")

    def apply_language(self, lang="RO"):
        if lang == "EN":
            self.lbl_titlu.setText("Stock & Parts")
            self.btn_adauga.setText("+ Add Part")
            self.btn_export.setText("Export CSV")
            self.lbl_cauta.setText("Search:")
            self.lbl_cat.setText("Category:")
            self.lbl_stoc.setText("Stock:")
            self.btn_reset.setText("Reset")
        else:
            self.lbl_titlu.setText("Stocuri & Piese")
            self.btn_adauga.setText("+ Adauga Piesa")
            self.btn_export.setText("Export CSV")
            self.lbl_cauta.setText("Cauta:")
            self.lbl_cat.setText("Categorie:")
            self.lbl_stoc.setText("Stoc:")
            self.btn_reset.setText("Reseteaza")