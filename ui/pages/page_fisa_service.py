from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QComboBox, QPushButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from datetime import datetime

import os
import platform
import subprocess

from ui.utils_toast import show_toast
from ui.widgets.checkbox_header import CheckBoxHeader
from ui.pdf.fisa_service_pdf import genereaza_fisa_service
from database import get_connection


# ============================================================
# LISTE LUCRARI PRESETATE RO / EN
# ============================================================

LUCRARI_RO = [
    ("--- MOTOR: ULEI & FILTRE ---", False),
    ("Schimb ulei motor", True),
    ("Schimb filtru ulei", True),
    ("Schimb filtru aer", True),
    ("Curatare filtru aer (spuma)", True),
    ("Schimb filtru combustibil", True),
    ("Verificare nivel ulei", True),
    ("Verificare scurgeri motor", True),

    ("--- TRANSMISIE & AMBREIAJ ---", False),
    ("Schimb ulei transmisie / cutie", True),
    ("Reglare ambreiaj", True),
    ("Verificare cablu ambreiaj", True),
    ("Verificare discuri ambreiaj", True),
    ("Verificare lant distributie", True),

    ("--- TRANSMISIE CVT (SCUTERE) ---", False),
    ("Revizie transmisie CVT (scutere)", True),
    ("Verificare role variator", True),
    ("Verificare cureaua CVT", True),
    ("Curatare variator", True),
    ("Curatare ambreiaj centrifugal", True),
    ("Verificare arcuri ambreiaj", True),

    ("--- TRANSMISIE SECUNDARA ---", False),
    ("Curatare lant", True),
    ("Ungere lant", True),
    ("Reglare lant", True),
    ("Verificare pinion fata", True),
    ("Verificare pinion spate", True),
    ("Verificare curea transmisie", True),
    ("Verificare cardan (nivel ulei + joc)", True),

    ("--- ROTI & ANVELOPE ---", False),
    ("Verificare presiune anvelope", True),
    ("Verificare uzura anvelope", True),
    ("Schimb anvelope", True),
    ("Echilibrare roti", True),
    ("Verificare rulmenti roata fata", True),
    ("Verificare rulmenti roata spate", True),

    ("--- SISTEM DE FRANARE ---", False),
    ("Verificare placute frana", True),
    ("Schimb placute frana", True),
    ("Verificare discuri frana", True),
    ("Schimb lichid frana", True),
    ("Aerisire sistem franare", True),
    ("Verificare etrieri", True),
    ("Curatare etrieri", True),
    ("Verificare ABS", True),

    ("--- SUSPENSII ---", False),
    ("Verificare furca fata", True),
    ("Schimb ulei furca", True),
    ("Schimb simeringuri furca", True),
    ("Verificare amortizor spate", True),
    ("Reglaje suspensie (preload, rebound, compresie)", True),

    ("--- ELECTRIC & ELECTRONICA ---", False),
    ("Verificare baterie", True),
    ("Testare incarcare alternator", True),
    ("Verificare regulator redresor", True),
    ("Verificare lumini", True),
    ("Verificare claxon", True),
    ("Verificare senzori (ABS, temperatura, pozitie)", True),

    ("--- SISTEM ALIMENTARE ---", False),
    ("Curatare carburator(e)", True),
    ("Sincronizare carburatoare", True),
    ("Curatare clapete injectie", True),
    ("Verificare pompa combustibil", True),
    ("Verificare injectoare", True),

    ("--- EVACUARE ---", False),
    ("Verificare scurgeri evacuare", True),
    ("Verificare prinderi evacuare", True),
    ("Curatare catalizator", True),

    ("--- SURUBURI, PRINDERI, CADRU ---", False),
    ("Verificare strangeri suruburi", True),
    ("Verificare prinderi cadru", True),
    ("Verificare suport motor", True),
    ("Verificare suport evacuare", True),

    ("--- DIRECTIE ---", False),
    ("Verificare joc ghidon", True),
    ("Verificare rulmenti jug", True),
    ("Reglare jug", True),

    ("--- INTRETINERE GENERALA ---", False),
    ("Verificare generala motocicleta", True),
    ("Test ride", True),
    ("Curatare motocicleta", True),
    ("Lubrifiere articulatii", True),

    ("--- OPERATIUNI ADMINISTRATIVE ---", False),
    ("Resetare service", True),
    ("Actualizare kilometraj", True),
    ("Notare observatii mecanic", True),
]


LUCRARI_EN = [
    ("--- ENGINE: OIL & FILTERS ---", False),
    ("Engine oil change", True),
    ("Oil filter replacement", True),
    ("Air filter replacement", True),
    ("Air filter cleaning (foam)", True),
    ("Fuel filter replacement", True),
    ("Oil level check", True),
    ("Engine leak inspection", True),

    ("--- TRANSMISSION & CLUTCH ---", False),
    ("Transmission / gearbox oil change", True),
    ("Clutch adjustment", True),
    ("Clutch cable inspection", True),
    ("Clutch discs inspection", True),
    ("Timing chain inspection", True),

    ("--- CVT TRANSMISSION (SCOOTERS) ---", False),
    ("CVT transmission service (scooters)", True),
    ("Variator rollers inspection", True),
    ("CVT belt inspection", True),
    ("Variator cleaning", True),
    ("Centrifugal clutch cleaning", True),
    ("Clutch springs inspection", True),

    ("--- FINAL DRIVE ---", False),
    ("Chain cleaning", True),
    ("Chain lubrication", True),
    ("Chain adjustment", True),
    ("Front sprocket inspection", True),
    ("Rear sprocket inspection", True),
    ("Drive belt inspection", True),
    ("Cardan inspection (oil level + play)", True),

    ("--- WHEELS & TIRES ---", False),
    ("Tire pressure check", True),
    ("Tire wear inspection", True),
    ("Tire replacement", True),
    ("Wheel balancing", True),
    ("Front wheel bearings inspection", True),
    ("Rear wheel bearings inspection", True),

    ("--- BRAKING SYSTEM ---", False),
    ("Brake pads inspection", True),
    ("Brake pads replacement", True),
    ("Brake discs inspection", True),
    ("Brake fluid replacement", True),
    ("Brake system bleeding", True),
    ("Brake calipers inspection", True),
    ("Brake calipers cleaning", True),
    ("ABS inspection", True),

    ("--- SUSPENSION ---", False),
    ("Front fork inspection", True),
    ("Fork oil replacement", True),
    ("Fork seals replacement", True),
    ("Rear shock absorber inspection", True),
    ("Suspension adjustments (preload, rebound, compression)", True),

    ("--- ELECTRICAL & ELECTRONICS ---", False),
    ("Battery inspection", True),
    ("Alternator charging test", True),
    ("Regulator rectifier inspection", True),
    ("Lights inspection", True),
    ("Horn inspection", True),
    ("Sensors inspection (ABS, temperature, position)", True),

    ("--- FUEL SYSTEM ---", False),
    ("Carburetor cleaning", True),
    ("Carburetor synchronization", True),
    ("Throttle body cleaning", True),
    ("Fuel pump inspection", True),
    ("Injector inspection", True),

    ("--- EXHAUST ---", False),
    ("Exhaust leak inspection", True),
    ("Exhaust mounts inspection", True),
    ("Catalyst cleaning", True),

    ("--- BOLTS, MOUNTS, FRAME ---", False),
    ("Bolts tightening inspection", True),
    ("Frame mounts inspection", True),
    ("Engine mount inspection", True),
    ("Exhaust mount inspection", True),

    ("--- STEERING ---", False),
    ("Handlebar play inspection", True),
    ("Steering bearings inspection", True),
    ("Steering adjustment", True),

    ("--- GENERAL MAINTENANCE ---", False),
    ("General motorcycle inspection", True),
    ("Test ride", True),
    ("Motorcycle cleaning", True),
    ("Joint lubrication", True),

    ("--- ADMINISTRATIVE OPERATIONS ---", False),
    ("Service reset", True),
    ("Mileage update", True),
    ("Mechanic notes entry", True),
]


# ============================================================
# PAGINA FISA SERVICE
# ============================================================

class PageFisaService(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        t = self.parent.translations[self.parent.app_language]
        main_layout = QVBoxLayout(self)

        # ---------------------------------------------------------
        # TITLU
        # ---------------------------------------------------------
        self.lbl_title = QLabel(t["fisa_service"])
        self.lbl_title.setObjectName("pageTitle")
        main_layout.addWidget(self.lbl_title)

        # ---------------------------------------------------------
        # SOLICITARI
        # ---------------------------------------------------------
        self.lbl_solicitari = QLabel(t["customer_requests"])
        self.lbl_solicitari.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.txt_solicitari = QTextEdit()

        # ---------------------------------------------------------
        # DEFECTE
        # ---------------------------------------------------------
        self.lbl_defecte = QLabel(t["reported_issues"])
        self.lbl_defecte.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.txt_defecte = QTextEdit()

        # ---------------------------------------------------------
        # OBSERVATII
        # ---------------------------------------------------------
        self.lbl_observatii = QLabel(t["mechanic_notes"])
        self.lbl_observatii.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.txt_observatii = QTextEdit()
        # Variabila pentru specificatiile tehnice (pagina 2 PDF)
        self.spec_tech = None

        # ---------------------------------------------------------
        # ZONA SPLIT: LUCRARI RECOMANDATE (STANGA) + BIBLIOTECA (DREAPTA)
        # ---------------------------------------------------------
        split_layout = QHBoxLayout()
        main_layout.addLayout(split_layout)

        # ---------------- STANGA: LUCRARI RECOMANDATE ----------------
        left_layout = QVBoxLayout()
        # Solicitari
        left_layout.addWidget(self.lbl_solicitari)
        left_layout.addWidget(self.txt_solicitari)

        # Defecte
        left_layout.addWidget(self.lbl_defecte)
        left_layout.addWidget(self.txt_defecte)

        # Observatii
        left_layout.addWidget(self.lbl_observatii)
        left_layout.addWidget(self.txt_observatii)


        self.lbl_lucrari = QLabel("Lucrari recomandate")
        self.lbl_lucrari.setStyleSheet("font-size: 14px; font-weight: bold;")
        left_layout.addWidget(self.lbl_lucrari)

        self.search_lucrari = QLineEdit()
        self.search_lucrari.setPlaceholderText("Cauta lucrare...")
        self.search_lucrari.textChanged.connect(self.filter_lucrari)
        left_layout.addWidget(self.search_lucrari)

        self.table_lucrari = QTableWidget()
        header = CheckBoxHeader(Qt.Horizontal, self.table_lucrari)
        self.table_lucrari.setHorizontalHeader(header)
        header.setSectionResizeMode(QHeaderView.Fixed)

        self.table_lucrari.setColumnCount(2)
        self.table_lucrari.setColumnWidth(0, 32)
        self.table_lucrari.setHorizontalHeaderLabels(["", "Lucrare"])
        self.table_lucrari.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_lucrari.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_lucrari.setFocusPolicy(Qt.NoFocus)

        scroll_lucrari = QScrollArea()
        scroll_lucrari.setWidgetResizable(True)
        scroll_lucrari.setFixedHeight(350)
        scroll_lucrari.setFrameShape(QFrame.NoFrame)
        scroll_lucrari.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_lucrari.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_lucrari.setWidget(self.table_lucrari)

        left_layout.addWidget(scroll_lucrari)

        split_layout.addLayout(left_layout, 1)

        # ---------------- DREAPTA: BIBLIOTECA ----------------
        right_layout = QVBoxLayout()

        self.lbl_biblio = QLabel("Biblioteca – Fise Tehnice")
        self.lbl_biblio.setStyleSheet("font-size: 14px; font-weight: bold;")
        right_layout.addWidget(self.lbl_biblio)

        # folosim exact PageBiblioteca, dar o integram aici
        from ui.pages.page_biblioteca import PageBiblioteca  # lazy import — evita circular import
        self.page_biblioteca = PageBiblioteca(self.parent)
        # conectam semnalul pentru Observatii mecanic
        self.page_biblioteca.specificatii_pentru_fisa.connect(self.incarca_specificatii)

        # daca vrei sa trimita si in Deviz direct:
        # self.page_biblioteca.specificatii_pentru_deviz.connect(
        #     self.parent.page_devize.incarca_specificatii
        # )

        right_layout.addWidget(self.page_biblioteca)

        split_layout.addLayout(right_layout, 1)

        # ---------------------------------------------------------
        # COMBUSTIBIL + STARE GENERALA
        # ---------------------------------------------------------
        row = QHBoxLayout()

        self.lbl_comb = QLabel(t["fuel_level"])
        self.lbl_comb.setStyleSheet("font-size: 14px; font-weight: bold;")
        row.addWidget(self.lbl_comb)

        self.cmb_combustibil = QComboBox()
        self.cmb_combustibil.addItems(
            ["Plin", "3/4", "Jumatate", "1/4", "Gol"]
            if self.parent.app_language == "RO"
            else ["Full", "3/4", "Half", "1/4", "Empty"]
        )
        row.addWidget(self.cmb_combustibil)

        self.lbl_stare = QLabel(t["general_condition"])
        self.lbl_stare.setStyleSheet("font-size: 14px; font-weight: bold;")
        row.addWidget(self.lbl_stare)

        self.cmb_stare = QComboBox()
        self.cmb_stare.addItems(
            ["Buna", "Mediocra", "Slaba"]
            if self.parent.app_language == "RO"
            else ["Good", "Average", "Poor"]
        )
        row.addWidget(self.cmb_stare)

        main_layout.addLayout(row)

        # ---------------------------------------------------------
        # KILOMETRAJ
        # ---------------------------------------------------------
        self.lbl_km = QLabel(t["mileage_intake"])
        self.lbl_km.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(self.lbl_km)

        self.txt_km = QLineEdit()
        main_layout.addWidget(self.txt_km)

        # ---------------------------------------------------------
        # BUTOANE
        # ---------------------------------------------------------
        btns = QHBoxLayout()

        self.btn_save = QPushButton(
            "💾 Salveaza Fisa" if self.parent.app_language == "RO" else "💾 Save Sheet"
        )
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save_fisa)

        self.btn_pdf = QPushButton(
            "📄 Genereaza PDF" if self.parent.app_language == "RO" else "📄 Generate PDF"
        )
        self.btn_pdf.setObjectName("primary")
        self.btn_pdf.clicked.connect(self.generate_pdf)

        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_pdf)
        btns.addStretch()

        main_layout.addLayout(btns)

        # ---------------------------------------------------------
        # CONEXIUNI TABEL LUCRARI
        # ---------------------------------------------------------
        self._internal_change = False
        self.table_lucrari.itemChanged.connect(self.on_item_changed)

        # Incarcam presetatele
        self.load_lucrari_presetate()

    # ---------------------------------------------------------
    # INCARCARE LUCRARI PRESETATE (BILINGV)
    # ---------------------------------------------------------
    def load_lucrari_presetate(self):
        self.table_lucrari.blockSignals(True)

        if self.parent.app_language == "RO":
            lucrari = LUCRARI_RO
        else:
            lucrari = LUCRARI_EN

        self.lucrari_master = lucrari
        self.table_lucrari.setRowCount(len(lucrari))

        for i, (nume, este_lucrare) in enumerate(lucrari):
            if este_lucrare:
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk.setCheckState(Qt.Unchecked)
                self.table_lucrari.setItem(i, 0, chk)
                self.table_lucrari.setItem(i, 1, QTableWidgetItem(nume))
            else:
                sep = QTableWidgetItem(nume)
                sep.setFlags(Qt.ItemIsEnabled)
                sep.setForeground(Qt.gray)
                self.table_lucrari.setItem(i, 0, QTableWidgetItem(""))
                self.table_lucrari.setItem(i, 1, sep)

        self.table_lucrari.blockSignals(False)

    # ---------------------------------------------------------
    # FILTRARE LUCRARI
    # ---------------------------------------------------------
    def filter_lucrari(self, text):
        self._internal_change = True
        self.table_lucrari.blockSignals(True)

        text = text.lower().strip()
        filtered = []

        for nume, este_lucrare in self.lucrari_master:
            if not este_lucrare:
                filtered.append((nume, False))
            else:
                if text in nume.lower():
                    filtered.append((nume, True))

        self.table_lucrari.setRowCount(len(filtered))

        for i, (nume, este_lucrare) in enumerate(filtered):
            if este_lucrare:
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk.setCheckState(Qt.Unchecked)
                self.table_lucrari.setItem(i, 0, chk)
                self.table_lucrari.setItem(i, 1, QTableWidgetItem(nume))
            else:
                sep = QTableWidgetItem(nume)
                sep.setFlags(Qt.ItemIsEnabled)
                sep.setForeground(Qt.gray)
                self.table_lucrari.setItem(i, 0, QTableWidgetItem(""))
                self.table_lucrari.setItem(i, 1, sep)

        self.table_lucrari.blockSignals(False)
        self._internal_change = False

    # ---------------------------------------------------------
    # HANDLER BIFARE / DEBIFARE
    # ---------------------------------------------------------
    def on_item_changed(self, item):
        if self._internal_change:
            return

        row = item.row()
        col = item.column()
        if col != 0:
            return

        chk = self.table_lucrari.item(row, 0)
        nume_item = self.table_lucrari.item(row, 1)

        if not chk or not nume_item:
            return

        descriere = nume_item.text()

        if descriere.startswith("---"):
            return

        if chk.checkState() == Qt.Checked:
            self.add_lucrare_instant(descriere)
        else:
            self.remove_lucrare_instant(descriere)

    # ---------------------------------------------------------
    # ADAUGA LUCRARE INSTANT
    # ---------------------------------------------------------
    def add_lucrare_instant(self, descriere):
        if not self.parent.selected_vehicul_id:
            return

        con = get_connection()
        cur = con.cursor()

        # Citim tariful implicit din firma
        tarif_implicit = 150.0
        try:
            cur.execute("SELECT tarif_ora FROM firma WHERE id=1")
            row = cur.fetchone()
            if row and row[0]:
                tarif_implicit = float(row[0])
        except:
            pass

        cur.execute("""
            INSERT INTO lucrari (id_vehicul, descriere, cost, ore_rar, tarif_ora, status)
            VALUES (?, ?, NULL, NULL, ?, 'in_lucru')
        """, (self.parent.selected_vehicul_id, descriere, tarif_implicit))

        con.commit()
        con.close()

        self.parent.page_lucrari.load_lucrari()

    # ---------------------------------------------------------
    # STERGE LUCRARE INSTANT
    # ---------------------------------------------------------
    def remove_lucrare_instant(self, descriere):
        if not self.parent.selected_vehicul_id:
            return

        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            DELETE FROM lucrari
            WHERE id_vehicul = ? AND descriere = ?
        """, (self.parent.selected_vehicul_id, descriere))

        con.commit()
        con.close()

        self.parent.page_lucrari.load_lucrari()

    # ---------------------------------------------------------
    # SALVARE + GENERARE PDF FINAL
    # ---------------------------------------------------------
    def save_fisa(self):
        if not self.parent.selected_client_id or not self.parent.selected_vehicul_id:
            show_toast(self.parent,
                       "Selecteaza client si vehicul."
                       if self.parent.app_language == "RO"
                       else "Select a client and vehicle.")
            return

        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO fise_service (
                id_client, id_vehicul, solicitari, defecte,
                observatii, nivel_combustibil, stare_generala, data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.parent.selected_client_id,
            self.parent.selected_vehicul_id,
            self.txt_solicitari.toPlainText(),
            self.txt_defecte.toPlainText(),
            self.txt_observatii.toPlainText(),
            self.cmb_combustibil.currentText(),
            self.cmb_stare.currentText(),
            datetime.now().strftime("%Y-%m-%d")
        ))

        con.commit()
        con.close()

        self.parent.page_lucrari.set_vehicul(
            self.parent.selected_vehicul_id,
            self.parent.selected_vehicul_id
        )

        show_toast(self.parent,
                   "Fisa a fost salvata cu succes."
                   if self.parent.app_language == "RO"
                   else "Sheet saved successfully.")

        # GENERARE PDF FINAL
        con = get_connection()
        cur = con.cursor()

        cur.execute("SELECT nume, telefon, email FROM clienti WHERE id=?",
                    (self.parent.selected_client_id,))
        client = cur.fetchone()

        cur.execute("""
            SELECT marca, model, an, vin, nr, km
            FROM vehicule WHERE id=?
        """, (self.parent.selected_vehicul_id,))
        vehicul = cur.fetchone()

        con.close()

        lucrari_bifate = []
        for r in range(self.table_lucrari.rowCount()):
            chk = self.table_lucrari.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                lucrari_bifate.append(self.table_lucrari.item(r, 1).text())

        piese = self.parent.page_lucrari.get_piese_for_deviz()

        path = genereaza_fisa_service(
            client,
            vehicul,
            self.txt_solicitari.toPlainText().replace("\t", "    "),
            self.txt_defecte.toPlainText().replace("\t", "    "),
            self.txt_observatii.toPlainText().replace("\t", "    "),
            self.cmb_combustibil.currentText(),
            self.cmb_stare.currentText(),
            self.txt_km.text().strip(),
            lucrari_bifate,
            piese,
            specificatii_tehnice=self.spec_tech,
            preview=False
        )
        # Deschidem PDF-ul salvat
        import os, platform, subprocess

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

        self.parent.page_lucrari.set_vehicul(
            self.parent.selected_vehicul_id,
            self.parent.selected_vehicul_id
        )


    # ---------------------------------------------------------
    # GENERARE PDF (PREVIEW)
    # ---------------------------------------------------------
    def generate_pdf(self):
        if not self.parent.selected_client_id or not self.parent.selected_vehicul_id:
            show_toast(self.parent,
                       "Selecteaza client si vehicul."
                       if self.parent.app_language == "RO"
                       else "Select a client and vehicle.")
            return

        con = get_connection()
        cur = con.cursor()

        cur.execute("SELECT nume, telefon, email FROM clienti WHERE id=?",
                    (self.parent.selected_client_id,))
        client = cur.fetchone()

        cur.execute("""
            SELECT marca, model, an, vin, nr, km
            FROM vehicule WHERE id=?
        """, (self.parent.selected_vehicul_id,))
        vehicul = cur.fetchone()

        con.close()

        lucrari_bifate = []
        for r in range(self.table_lucrari.rowCount()):
            chk = self.table_lucrari.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                lucrari_bifate.append(self.table_lucrari.item(r, 1).text())

        piese = self.parent.page_lucrari.get_piese_for_deviz()

        path = genereaza_fisa_service(
            client,
            vehicul,
            self.txt_solicitari.toPlainText().replace("\t", "    "),
            self.txt_defecte.toPlainText().replace("\t", "    "),
            self.txt_observatii.toPlainText().replace("\t", "    "),
            self.cmb_combustibil.currentText(),
            self.cmb_stare.currentText(),
            self.txt_km.text().strip(),
            lucrari_bifate,
            piese,
            specificatii_tehnice=self.spec_tech,
            preview=True
        )

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

        show_toast(self.parent,
                   "Preview PDF generat (nesalvat)."
                   if self.parent.app_language == "RO"
                   else "Preview PDF generated (unsaved).")

    # ---------------------------------------------------------
    # INCARCARE SPECIFICATII TEHNICE (din Biblioteca)
    # ---------------------------------------------------------
    def incarca_specificatii(self, data):
        text = "=== SPECIFICATII TEHNICE ===\n" if self.parent.app_language == "RO" else "=== TECHNICAL SPECIFICATIONS ===\n"

        for cheie, valoare in data.items():
            if isinstance(valoare, dict):
                text += f"\n[{cheie}]\n"
                for sub_cheie, sub_valoare in valoare.items():
                    text += f" - {sub_cheie}: {sub_valoare}\n"
            else:
                text += f"- {cheie}: {valoare}\n"

        self.spec_tech = text
        show_toast(self.parent,
                   "Specificatiile au fost incarcate pe verso."
                   if self.parent.app_language == "RO"
                   else "Specifications loaded into Notes.")

    # ---------------------------------------------------------
    # APLICARE LIMBA
    # ---------------------------------------------------------
    def apply_language(self):
        t = self.parent.translations[self.parent.app_language]

        self.lbl_title.setText(t["fisa_service"])
        self.lbl_solicitari.setText(t["customer_requests"])
        self.lbl_defecte.setText(t["reported_issues"])
        self.lbl_observatii.setText(t["mechanic_notes"])
        self.lbl_comb.setText(t["fuel_level"])
        self.lbl_stare.setText(t["general_condition"])
        self.lbl_km.setText(t["mileage_intake"])

        if self.parent.app_language == "RO":
            self.lbl_lucrari.setText("Lucrari recomandate")
            self.search_lucrari.setPlaceholderText("Cauta lucrare...")
            self.table_lucrari.setHorizontalHeaderLabels(["", "Lucrare"])
            self.lbl_biblio.setText("Biblioteca – Fise Tehnice")
        else:
            self.lbl_lucrari.setText("Recommended works")
            self.search_lucrari.setPlaceholderText("Search work...")
            self.table_lucrari.setHorizontalHeaderLabels(["", "Work"])
            self.lbl_biblio.setText("Library – Technical Sheets")

        self.cmb_combustibil.clear()
        self.cmb_combustibil.addItems(
            ["Plin", "3/4", "Jumatate", "1/4", "Gol"]
            if self.parent.app_language == "RO"
            else ["Full", "3/4", "Half", "1/4", "Empty"]
        )

        self.cmb_stare.clear()
        self.cmb_stare.addItems(
            ["Buna", "Mediocra", "Slaba"]
            if self.parent.app_language == "RO"
            else ["Good", "Average", "Poor"]
        )

        self.btn_save.setText(
            "💾 Salveaza Fisa" if self.parent.app_language == "RO" else "💾 Save Sheet"
        )
        self.btn_pdf.setText(
            "📄 Genereaza PDF" if self.parent.app_language == "RO" else "📄 Generate PDF"
        )

        # Reincarca lista de lucrari in limba corecta
        self.load_lucrari_presetate()

        # Propagam limba si in Biblioteca integrata
        if hasattr(self, "page_biblioteca") and hasattr(self.page_biblioteca, "apply_language"):
            self.page_biblioteca.apply_language()

    # ---------------------------------------------------------
    # REINCARCARE LUCRARI DIN DB
    # ---------------------------------------------------------
    def reincarca_lucrari_din_db(self):
        if not self.parent.selected_vehicul_id:
            return

        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT descriere FROM lucrari
            WHERE id_vehicul = ?
        """, (self.parent.selected_vehicul_id,))

        lucrari_db = [row[0] for row in cur.fetchall()]
        con.close()

        # Debifam totul daca nu exista lucrari in DB
        self._internal_change = True
        self.table_lucrari.blockSignals(True)

        for row in range(self.table_lucrari.rowCount()):
            chk = self.table_lucrari.item(row, 0)
            nume = self.table_lucrari.item(row, 1)

            if chk and nume:
                if nume.text() in lucrari_db:
                    chk.setCheckState(Qt.Checked)
                else:
                    chk.setCheckState(Qt.Unchecked)

        self.table_lucrari.blockSignals(False)
        self._internal_change = False
