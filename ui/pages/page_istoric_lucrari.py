from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton
)
from PyQt5.QtCore import Qt
import os
import subprocess
import platform
from database import get_connection
from ui.utils_toast import show_toast


class PageIstoricLucrari(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        layout = QVBoxLayout(self)

        # ---------------------------------------------------------
        # TITLU
        # ---------------------------------------------------------
        self.lbl_title = QLabel("Istoric lucrari")
        self.lbl_title.setObjectName("pageTitle")
        layout.addWidget(self.lbl_title)

        # ---------------------------------------------------------
        # TABEL DEVIZE
        # ---------------------------------------------------------
        self.table_devize = QTableWidget()
        self.table_devize.setFocusPolicy(Qt.NoFocus)
        self.table_devize.setEditTriggers(QTableWidget.NoEditTriggers)

        self.table_devize.setColumnCount(4)
        self.table_devize.setHorizontalHeaderLabels(["Numar", "Data", "Total", "Deschide PDF"])
        self.table_devize.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_devize.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_devize.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_devize.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        layout.addWidget(self.table_devize)

        # ---------------------------------------------------------
        # TABEL LUCRARI
        # ---------------------------------------------------------
        self.lbl_lucrari = QLabel("Lucrari efectuate")
        self.lbl_lucrari.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(self.lbl_lucrari)

        self.table_lucrari = QTableWidget()
        self.table_lucrari.setFocusPolicy(Qt.NoFocus)
        self.table_lucrari.setEditTriggers(QTableWidget.NoEditTriggers)

        self.table_lucrari.setColumnCount(3)
        self.table_lucrari.setHorizontalHeaderLabels(["Descriere", "Ore RAR", "Total"])
        self.table_lucrari.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_lucrari.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_lucrari.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        layout.addWidget(self.table_lucrari)

        # ---------------------------------------------------------
        # SELECT DEVIZ
        # ---------------------------------------------------------
        self.table_devize.cellClicked.connect(self.on_deviz_selectat)

    # ---------------------------------------------------------
    # HELPER: CREARE FUNCTIE PENTRU DESCHIDERE PDF
    # ---------------------------------------------------------
    def _make_pdf_opener(self, path):
        return lambda: self.deschide_pdf(path)

    # ---------------------------------------------------------
    # INCARCARE DEVIZE PENTRU VEHICUL
    # ---------------------------------------------------------
    def load_istoric(self, id_vehicul):
        self.id_vehicul = id_vehicul

        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT id, numar, data, total_general, path_pdf
            FROM devize
            WHERE id_vehicul = ?
            ORDER BY id DESC
        """, (id_vehicul,))

        devize = cur.fetchall()
        con.close()

        self.devize_data = devize
        self.table_devize.setRowCount(len(devize))

        for i, (id_deviz, numar, data, total, path_pdf) in enumerate(devize):

            # Daca nu exista path_pdf in DB, sarim peste
            if not path_pdf:
                continue

            self.table_devize.setItem(i, 0, QTableWidgetItem(numar))
            self.table_devize.setItem(i, 1, QTableWidgetItem(data))
            self.table_devize.setItem(i, 2, QTableWidgetItem(f"{total:.2f} lei"))

            btn = QPushButton("Deschide")
            btn.clicked.connect(self._make_pdf_opener(path_pdf))
            self.table_devize.setCellWidget(i, 3, btn)

        # Curatam tabelul de lucrari
        self.table_lucrari.clearContents()
        self.table_lucrari.setRowCount(0)

    # ---------------------------------------------------------
    # SELECT DEVIZ → ARATA LUCRARILE
    # ---------------------------------------------------------
    def on_deviz_selectat(self, row, col):
        id_deviz = self.devize_data[row][0]

        con = get_connection()
        cur = con.cursor()

        # Lucrari
        cur.execute("""
            SELECT descriere, cost, ore_rar
            FROM deviz_lucrari
            WHERE id_deviz = ?
        """, (id_deviz,))
        lucrari = cur.fetchall()

        # Piese
        cur.execute("""
            SELECT piesa, cantitate, total
            FROM deviz_piese
            WHERE id_deviz = ?
        """, (id_deviz,))
        piese = cur.fetchall()

        con.close()

        # Calcul randuri
        total_randuri = len(lucrari) + len(piese)
        if piese:
            total_randuri += 1  # separator

        self.table_lucrari.clearContents()
        self.table_lucrari.setRowCount(total_randuri)

        # Afisam lucrarile
        row_index = 0
        for row_data in lucrari:
            descriere = row_data[0] or ""
            cost = float(row_data[1]) if row_data[1] is not None else 0.0
            ore_rar = row_data[2] if len(row_data) > 2 and row_data[2] is not None else None
            ore_txt = f"{float(ore_rar):.1f}" if ore_rar else "-"

            self.table_lucrari.setItem(row_index, 0, QTableWidgetItem(descriere))
            self.table_lucrari.setItem(row_index, 1, QTableWidgetItem(ore_txt))
            self.table_lucrari.setItem(row_index, 2, QTableWidgetItem(f"{cost:.2f} lei"))
            row_index += 1

        # Separator
        if piese:
            self.table_lucrari.setItem(row_index, 0, QTableWidgetItem("— Piese utilizate —"))
            self.table_lucrari.setItem(row_index, 1, QTableWidgetItem(""))
            row_index += 1

        # Afisam piesele
        for nume, cant, total in piese:
            text = f"{nume} (x{cant})"
            self.table_lucrari.setItem(row_index, 0, QTableWidgetItem(text))
            self.table_lucrari.setItem(row_index, 1, QTableWidgetItem(f"{total:.2f} lei"))
            row_index += 1

    # ---------------------------------------------------------
    # DESCHIDERE PDF
    # ---------------------------------------------------------
    def deschide_pdf(self, path):
        if not path or not os.path.exists(path):
            show_toast(self.parent, "PDF-ul nu exista.")
            return

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    def apply_language(self):
        lang = self.parent.app_language

        if lang == "RO":
            # Titluri
            self.lbl_title.setText("Istoric lucrari")
            self.lbl_lucrari.setText("Lucrari efectuate")

            # Header tabel devize
            self.table_devize.setHorizontalHeaderLabels(
                ["Numar", "Data", "Total", "Deschide PDF"]
            )

            # Header tabel lucrari
            self.table_lucrari.setHorizontalHeaderLabels(
                ["Descriere", "Ore RAR", "Total"]
            )

            # Butoane PDF
            for row in range(self.table_devize.rowCount()):
                widget = self.table_devize.cellWidget(row, 3)
                if isinstance(widget, QPushButton):
                    widget.setText("Deschide")

        else:
            # Titles
            self.lbl_title.setText("Work history")
            self.lbl_lucrari.setText("Performed works")

            # Table headers
            self.table_devize.setHorizontalHeaderLabels(
                ["Number", "Date", "Total", "Open PDF"]
            )

            self.table_lucrari.setHorizontalHeaderLabels(
                ["Description", "RAR hours", "Total"]
            )

            # PDF buttons
            for row in range(self.table_devize.rowCount()):
                widget = self.table_devize.cellWidget(row, 3)
                if isinstance(widget, QPushButton):
                    widget.setText("Open")
