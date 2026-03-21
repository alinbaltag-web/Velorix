from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit,
    QPushButton, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from ui.data_marci_modele import MARCI_MODELE
from PyQt5.QtWidgets import QCompleter
from PyQt5.QtCore import QStringListModel
from ui.vin_decoder import decode_vin


class DialogVehicul(QDialog):
    def __init__(self, parent=None, vehicul_data=None):
        super().__init__(parent)
        self.vehicul_data = vehicul_data
        self.setWindowTitle("Vehicul nou" if not vehicul_data else "Editare vehicul")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # ---------------------------------------------------------
        # Formular
        # ---------------------------------------------------------
        form = QFormLayout()
        form.setSpacing(10)

        self.marca = QLineEdit()
        self.marca.setPlaceholderText("Ex: Honda, Yamaha, BMW...")

        self.model = QLineEdit()
        self.model.setPlaceholderText("Ex: CBR600RR, MT-07...")

        self.an = QLineEdit()
        self.an.setPlaceholderText("Ex: 2020")

        self.vin = QLineEdit()
        self.vin.setPlaceholderText("17 caractere")
        self.vin.setMaxLength(17)

        self.nr = QLineEdit()
        self.nr.setPlaceholderText("Ex: B 123 ABC")

        self.cc = QLineEdit()
        self.cc.setPlaceholderText("Ex: 600")

        self.km = QLineEdit()
        self.km.setPlaceholderText("Ex: 15000")

        self.culoare = QLineEdit()
        self.culoare.setPlaceholderText("Ex: Rosu, Negru...")

        self.combustibil = QComboBox()
        self.combustibil.addItems([
            "Benzina",
            "Diesel",
            "Electric",
            "Hibrid"
        ])

        self.serie_motor = QLineEdit()
        self.serie_motor.setPlaceholderText("Serie motor")

        form.addRow("Marca *:", self.marca)
        form.addRow("Model:", self.model)
        form.addRow("An fabricatie:", self.an)
        form.addRow("VIN:", self.vin)

        self.lbl_vin_status = QLabel("")
        self.lbl_vin_status.setStyleSheet("font-size: 11px; color: #6b7280;")
        form.addRow("", self.lbl_vin_status)
        form.addRow("Nr. inmatriculare:", self.nr)
        form.addRow("Cilindree (CC):", self.cc)
        form.addRow("Kilometraj:", self.km)
        form.addRow("Culoare:", self.culoare)
        form.addRow("Combustibil:", self.combustibil)
        form.addRow("Serie motor:", self.serie_motor)

        layout.addLayout(form)

        # ---------------------------------------------------------
        # Butoane
        # ---------------------------------------------------------
        btns = QHBoxLayout()

        self.btn_salveaza = QPushButton("💾 Salveaza")
        self.btn_salveaza.setObjectName("primary")
        self.btn_salveaza.clicked.connect(self.salveaza)

        self.btn_anuleaza = QPushButton("✖ Anuleaza")
        self.btn_anuleaza.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(self.btn_anuleaza)
        btns.addWidget(self.btn_salveaza)

        layout.addLayout(btns)

        # ---------------------------------------------------------
        # Tab order
        # ---------------------------------------------------------
        self.setTabOrder(self.marca, self.model)
        self.setTabOrder(self.model, self.an)
        self.setTabOrder(self.an, self.vin)
        self.setTabOrder(self.vin, self.nr)
        self.setTabOrder(self.nr, self.cc)
        self.setTabOrder(self.cc, self.km)
        self.setTabOrder(self.km, self.culoare)
        self.setTabOrder(self.culoare, self.serie_motor)
        self.setTabOrder(self.serie_motor, self.btn_salveaza)

        # Reset highlight la editare
        self.marca.textChanged.connect(lambda: self.marca.setStyleSheet(""))
        self.an.textChanged.connect(lambda: self.an.setStyleSheet(""))
        self.km.textChanged.connect(lambda: self.km.setStyleSheet(""))
        self.cc.textChanged.connect(lambda: self.cc.setStyleSheet(""))

        # ---------------------------------------------------------
        # Autocomplete marca
        # ---------------------------------------------------------
        completer_marca = QCompleter(list(MARCI_MODELE.keys()), self)
        completer_marca.setCaseSensitivity(Qt.CaseInsensitive)
        completer_marca.setFilterMode(Qt.MatchContains)
        self.marca.setCompleter(completer_marca)

        # ---------------------------------------------------------
        # Autocomplete model dinamic
        # ---------------------------------------------------------
        self.model_list = QStringListModel([], self)
        completer_model = QCompleter(self.model_list, self)
        completer_model.setCaseSensitivity(Qt.CaseInsensitive)
        completer_model.setFilterMode(Qt.MatchContains)
        self.model.setCompleter(completer_model)

        self.marca.textChanged.connect(self.on_marca_changed)
        self.vin.textChanged.connect(self.on_vin_changed)

        # ---------------------------------------------------------
        # Daca editam, populam campurile
        # ---------------------------------------------------------
        if self.vehicul_data:
            self.populeaza_date()

    # ---------------------------------------------------------
    # AUTOCOMPLETE MODEL
    # ---------------------------------------------------------
    def on_marca_changed(self, text):
        modele = MARCI_MODELE.get(text.strip(), [])
        self.model_list.setStringList(modele)

    # ---------------------------------------------------------
    # COMPLETARE AUTOMATA DIN VIN
    # ---------------------------------------------------------
    def on_vin_changed(self, text):
        vin = text.strip().upper()
        if len(vin) < 17:
            return

        result = decode_vin(vin)
        if not result.get("valid"):
            self.lbl_vin_status.setText("⚠️ VIN nerecunoscut")
            self.lbl_vin_status.setStyleSheet("font-size: 11px; color: #f59e0b;")
            return

        self.lbl_vin_status.setText("✅ VIN recunoscut")
        self.lbl_vin_status.setStyleSheet("font-size: 11px; color: #10b981;")

        if result.get("marca") and not self.marca.text().strip():
            self.marca.setText(result["marca"])

        if result.get("model") and not self.model.text().strip():
            self.model.setText(result["model"])

        if result.get("year") and not self.an.text().strip():
            self.an.setText(str(result["year"]))

        if result.get("cc") and not self.cc.text().strip():
            self.cc.setText(str(result["cc"]))

    # ---------------------------------------------------------
    # POPULARE DATE LA EDITARE
    # ---------------------------------------------------------
    def populeaza_date(self):
        d = self.vehicul_data
        self.marca.setText(d.get("marca", ""))
        self.model.setText(d.get("model", ""))
        self.an.setText(str(d.get("an", "") or ""))        
        self.vin.setText(d.get("vin", ""))
        self.nr.setText(d.get("nr", ""))
        self.cc.setText(str(d.get("cc", "") or ""))        
        self.km.setText(str(d.get("km", "") or ""))        
        self.culoare.setText(d.get("culoare", ""))
        self.serie_motor.setText(d.get("serie_motor", ""))

        idx = self.combustibil.findText(d.get("combustibil", "Benzina"))
        if idx >= 0:
            self.combustibil.setCurrentIndex(idx)

    # ---------------------------------------------------------
    # VALIDARE SI SALVARE
    # ---------------------------------------------------------
    def salveaza(self):
        _err = "border: 2px solid #ef4444; border-radius: 7px;"

        if not self.marca.text().strip():
            self.marca.setStyleSheet(_err)
            self.marca.setFocus()
            QMessageBox.warning(self, "Camp obligatoriu", "Campul Marca este obligatoriu.")
            return

        an = self.an.text().strip()
        if an:
            if not an.isdigit() or not (1900 <= int(an) <= 2030):
                self.an.setStyleSheet(_err)
                self.an.setFocus()
                QMessageBox.warning(self, "Valoare invalida",
                                    "Anul trebuie sa fie intre 1900 si 2030 (ex: 2020).")
                return

        vin = self.vin.text().strip().upper()
        if vin:
            if len(vin) != 17:
                self.vin.setFocus()
                QMessageBox.warning(self, "VIN invalid",
                                    f"VIN-ul trebuie sa aiba exact 17 caractere (acum are {len(vin)}).")
                return
            if any(c in vin for c in "IOQ"):
                self.vin.setFocus()
                QMessageBox.warning(self, "VIN invalid",
                                    "VIN-ul nu poate contine literele I, O sau Q.")
                return

        km = self.km.text().strip()
        if km and not km.isdigit():
            self.km.setStyleSheet(_err)
            self.km.setFocus()
            QMessageBox.warning(self, "Valoare invalida", "Kilometrajul trebuie sa fie un numar valid.")
            return

        cc = self.cc.text().strip()
        if cc and not cc.isdigit():
            self.cc.setStyleSheet(_err)
            self.cc.setFocus()
            QMessageBox.warning(self, "Valoare invalida", "CC trebuie sa fie un numar valid.")
            return

        self.accept()

    # ---------------------------------------------------------
    # GETTER DATE
    # ---------------------------------------------------------
    def get_data(self):
        return {
            "marca": self.marca.text().strip(),
            "model": self.model.text().strip(),
            "an": self.an.text().strip() or None,
            "vin": self.vin.text().strip().upper() or None,
            "nr": self.nr.text().strip() or None,
            "cc": self.cc.text().strip() or None,
            "km": self.km.text().strip() or None,
            "culoare": self.culoare.text().strip() or None,
            "combustibil": self.combustibil.currentText(),
            "serie_motor": self.serie_motor.text().strip() or None
        }