from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QDoubleSpinBox,
    QSpinBox, QPushButton, QTextEdit, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from database import get_connection, get_tva
from ui.session_manager import SessionManager


class DialogPiesa(QDialog):
    def __init__(self, parent=None, piesa_id=None):
        super().__init__(parent)
        self.piesa_id = piesa_id
        self.setWindowTitle("Adauga Piesa" if not piesa_id else "Editeaza Piesa")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.init_ui()
        if piesa_id:
            self.load_piesa()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Titlu
        titlu = QLabel("Adauga Piesa in Stoc" if not self.piesa_id else "Editeaza Piesa")
        titlu.setObjectName("dialogTitle")
        titlu.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(titlu)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #334155;")
        layout.addWidget(sep)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.input_cod = QLineEdit()
        self.input_cod.setPlaceholderText("ex: FLT-001")
        form.addRow("Cod Piesa:", self.input_cod)

        self.input_nume = QLineEdit()
        self.input_nume.setPlaceholderText("ex: Filtru ulei Honda")
        form.addRow("Nume Piesa *:", self.input_nume)

        self.combo_categorie = QComboBox()
        self.load_categorii()
        form.addRow("Categorie:", self.combo_categorie)

        self.combo_unitate = QComboBox()
        self.combo_unitate.addItems(["buc", "litru", "ml", "kg", "g", "m", "set"])
        form.addRow("Unitate Masura:", self.combo_unitate)

        self.spin_stoc = QDoubleSpinBox()
        self.spin_stoc.setRange(0, 99999)
        self.spin_stoc.setDecimals(2)
        self.spin_stoc.setSuffix("  buc")
        form.addRow("Stoc Curent:", self.spin_stoc)

        self.spin_stoc_minim = QDoubleSpinBox()
        self.spin_stoc_minim.setRange(0, 99999)
        self.spin_stoc_minim.setDecimals(2)
        self.spin_stoc_minim.setValue(1)
        self.spin_stoc_minim.setSuffix("  buc")
        form.addRow("Stoc Minim:", self.spin_stoc_minim)

        self.spin_pret_ach = QDoubleSpinBox()
        self.spin_pret_ach.setRange(0, 999999)
        self.spin_pret_ach.setDecimals(2)
        self.spin_pret_ach.setSuffix("  RON")
        self.spin_pret_ach.valueChanged.connect(self.calculeaza_vanzare)
        form.addRow("Pret Achizitie:", self.spin_pret_ach)

        self.spin_pret_van = QDoubleSpinBox()
        self.spin_pret_van.setRange(0, 999999)
        self.spin_pret_van.setDecimals(2)
        self.spin_pret_van.setSuffix("  RON")
        form.addRow("Pret Vanzare:", self.spin_pret_van)

        self.combo_tva = QComboBox()
        self.combo_tva.addItems(["21", "19", "9", "5", "0"])
        # Setare automata TVA din setari
        tva_curent = str(int(get_tva()))
        idx = self.combo_tva.findText(tva_curent)
        if idx >= 0:
            self.combo_tva.setCurrentIndex(idx)        
        form.addRow("TVA %:", self.combo_tva)

        self.input_furnizor = QLineEdit()
        self.input_furnizor.setPlaceholderText("Numele furnizorului")
        form.addRow("Furnizor:", self.input_furnizor)

        self.input_obs = QTextEdit()
        self.input_obs.setMaximumHeight(70)
        self.input_obs.setPlaceholderText("Observatii optionale...")
        form.addRow("Observatii:", self.input_obs)

        layout.addLayout(form)

        # Butoane
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_anuleaza = QPushButton("Anuleaza")
        self.btn_anuleaza.setObjectName("secondaryButton")
        self.btn_anuleaza.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_anuleaza)

        self.btn_salveaza = QPushButton("💾 Salveaza")
        self.btn_salveaza.setObjectName("primaryButton")
        self.btn_salveaza.clicked.connect(self.salveaza)
        btn_layout.addWidget(self.btn_salveaza)

        layout.addLayout(btn_layout)

    def load_categorii(self):
        self.combo_categorie.clear()
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT id, nume FROM categorii_piese ORDER BY nume")
        for row in cur.fetchall():
            self.combo_categorie.addItem(row[1], row[0])
        con.close()

    def calculeaza_vanzare(self, val):
        # Sugestie automata pret vanzare = achizitie + 30%
        if self.spin_pret_van.value() == 0:
            self.spin_pret_van.setValue(round(val * 1.30, 2))

    def load_piesa(self):
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT * FROM stoc_piese WHERE id=?", (self.piesa_id,))
        row = cur.fetchone()
        con.close()
        if not row:
            return
        # id, cod, nume, id_categorie, stoc_curent, stoc_minim,
        # unitate, pret_achizitie, pret_vanzare, tva, furnizor, observatii
        self.input_cod.setText(row[1] or "")
        self.input_nume.setText(row[2] or "")

        # Setare categorie
        idx = self.combo_categorie.findData(row[3])
        if idx >= 0:
            self.combo_categorie.setCurrentIndex(idx)

        self.spin_stoc.setValue(float(row[4]) if row[4] else 0)
        self.spin_stoc_minim.setValue(float(row[5]) if row[5] else 1)

        idx_um = self.combo_unitate.findText(row[6] or "buc")
        if idx_um >= 0:
            self.combo_unitate.setCurrentIndex(idx_um)

        self.spin_pret_ach.setValue(float(row[7]) if row[7] else 0)
        self.spin_pret_van.setValue(float(row[8]) if row[8] else 0)

        idx_tva = self.combo_tva.findText(str(row[9] or 19))
        if idx_tva >= 0:
            self.combo_tva.setCurrentIndex(idx_tva)

        self.input_furnizor.setText(row[10] or "")
        self.input_obs.setPlainText(row[11] or "")

    def salveaza(self):
        nume = self.input_nume.text().strip()
        if not nume:
            QMessageBox.warning(self, "Eroare", "Numele piesei este obligatoriu!")
            self.input_nume.setFocus()
            return

        cod = self.input_cod.text().strip()
        cat_id = self.combo_categorie.currentData()
        stoc = self.spin_stoc.value()
        stoc_minim = self.spin_stoc_minim.value()
        unitate = self.combo_unitate.currentText()
        pret_ach = self.spin_pret_ach.value()
        pret_van = self.spin_pret_van.value()
        tva = int(self.combo_tva.currentText())
        furnizor = self.input_furnizor.text().strip()
        obs = self.input_obs.toPlainText().strip()
        user = SessionManager.get_user()        
        con = get_connection()
        cur = con.cursor()

        if self.piesa_id:
            cur.execute("""
                UPDATE stoc_piese SET cod=?, nume=?, id_categorie=?, stoc_curent=?,
                stoc_minim=?, unitate=?, pret_achizitie=?, pret_vanzare=?,
                tva=?, furnizor=?, observatii=?
                WHERE id=?
            """, (cod, nume, cat_id, stoc, stoc_minim, unitate,
                  pret_ach, pret_van, tva, furnizor, obs, self.piesa_id))
        else:
            cur.execute("""
                INSERT INTO stoc_piese
                (cod, nume, id_categorie, stoc_curent, stoc_minim, unitate,
                 pret_achizitie, pret_vanzare, tva, furnizor, observatii)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cod, nume, cat_id, stoc, stoc_minim, unitate,
                  pret_ach, pret_van, tva, furnizor, obs))
            piesa_id_nou = cur.lastrowid

            # Inregistreaza miscare initiala daca stoc > 0
            if stoc > 0:
                cur.execute("""
                    INSERT INTO miscari_stoc (id_piesa, tip, cantitate, stoc_dupa, motiv, username)
                    VALUES (?, 'intrare', ?, ?, 'Stoc initial', ?)
                """, (piesa_id_nou, stoc, stoc, user))

        con.commit()
        con.close()
        self.accept()