from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit,
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
import re

_EMAIL_RE   = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE   = re.compile(r"^(\+4)?07[0-9]{8}$")


class DialogClient(QDialog):
    def __init__(self, parent=None, client_data=None):
        super().__init__(parent)
        self.client_data = client_data  # None = adaugare, dict = editare
        self.setWindowTitle("Client nou" if not client_data else "Editare client")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # ---------------------------------------------------------
        # Formular
        # ---------------------------------------------------------
        form = QFormLayout()
        form.setSpacing(10)

        self.tip = QComboBox()
        self.tip.addItems(["Persoana Fizica", "Persoana Juridica"])

        self.nume = QLineEdit()
        self.nume.setPlaceholderText("Nume complet / Denumire firma")

        self.telefon = QLineEdit()
        self.telefon.setPlaceholderText("07xx xxx xxx")

        self.email = QLineEdit()
        self.email.setPlaceholderText("email@exemplu.ro")

        self.adresa = QLineEdit()
        self.adresa.setPlaceholderText("Strada, nr, oras, judet")

        self.cui_cnp = QLineEdit()
        self.cui_cnp.setPlaceholderText("CNP / CUI")

        self.observatii = QTextEdit()
        self.observatii.setPlaceholderText("Observatii despre client...")
        self.observatii.setMaximumHeight(80)

        form.addRow("Tip:", self.tip)
        form.addRow("Nume *:", self.nume)
        form.addRow("Telefon:", self.telefon)
        form.addRow("Email:", self.email)
        form.addRow("Adresa:", self.adresa)
        form.addRow("CNP / CUI:", self.cui_cnp)
        form.addRow("Observatii:", self.observatii)

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
        self.setTabOrder(self.tip, self.nume)
        self.setTabOrder(self.nume, self.telefon)
        self.setTabOrder(self.telefon, self.email)
        self.setTabOrder(self.email, self.adresa)
        self.setTabOrder(self.adresa, self.cui_cnp)
        self.setTabOrder(self.cui_cnp, self.observatii)
        self.setTabOrder(self.observatii, self.btn_salveaza)

        # Reset highlight la editare
        self.nume.textChanged.connect(lambda: self.nume.setStyleSheet(""))
        self.email.textChanged.connect(lambda: self.email.setStyleSheet(""))
        self.telefon.textChanged.connect(lambda: self.telefon.setStyleSheet(""))

        # ---------------------------------------------------------
        # Daca editam, populam campurile
        # ---------------------------------------------------------
        if self.client_data:
            self.populeaza_date()

        # Schimbam label CNP/CUI in functie de tip
        self.tip.currentTextChanged.connect(self.update_label_cui_cnp)
        self.update_label_cui_cnp(self.tip.currentText())

    # ---------------------------------------------------------
    # UPDATE LABEL CNP / CUI
    # ---------------------------------------------------------
    def update_label_cui_cnp(self, text):
        form = self.layout().itemAt(0).layout()
        for i in range(form.rowCount()):
            label_item = form.itemAt(i, QFormLayout.LabelRole)
            if label_item:
                label = label_item.widget()
                if label and "CNP" in label.text():
                    if text == "Persoana Juridica":
                        label.setText("CUI:")
                        self.cui_cnp.setPlaceholderText("RO12345678")
                    else:
                        label.setText("CNP / CUI:")
                        self.cui_cnp.setPlaceholderText("CNP / CUI")

    # ---------------------------------------------------------
    # POPULARE DATE LA EDITARE
    # ---------------------------------------------------------
    def populeaza_date(self):
        d = self.client_data
        idx = self.tip.findText(d.get("tip", "Persoana Fizica"))
        if idx >= 0:
            self.tip.setCurrentIndex(idx)
        self.nume.setText(d.get("nume", ""))
        self.telefon.setText(d.get("telefon", ""))
        self.email.setText(d.get("email", ""))
        self.adresa.setText(d.get("adresa", ""))
        self.cui_cnp.setText(d.get("cui_cnp", ""))
        self.observatii.setPlainText(d.get("observatii", ""))

    # ---------------------------------------------------------
    # SALVARE — returneaza datele completate
    # ---------------------------------------------------------
    def salveaza(self):
        _err_style = "border: 2px solid #ef4444; border-radius: 7px;"
        ok = True

        if not self.nume.text().strip():
            self.nume.setStyleSheet(_err_style)
            self.nume.setFocus()
            QMessageBox.warning(self, "Camp obligatoriu", "Numele clientului este obligatoriu.")
            ok = False

        email = self.email.text().strip()
        if ok and email and not _EMAIL_RE.match(email):
            self.email.setStyleSheet(_err_style)
            self.email.setFocus()
            QMessageBox.warning(self, "Email invalid", "Adresa de email nu este valida.")
            ok = False

        telefon = self.telefon.text().strip().replace(" ", "").replace("-", "")
        if ok and telefon and not _PHONE_RE.match(telefon):
            self.telefon.setStyleSheet(_err_style)
            self.telefon.setFocus()
            QMessageBox.warning(self, "Telefon invalid",
                                "Numarul de telefon trebuie sa fie in formatul 07xxxxxxxx sau +407xxxxxxxx.")
            ok = False

        if ok:
            self.accept()

    # ---------------------------------------------------------
    # GETTER DATE
    # ---------------------------------------------------------
    def get_data(self):
        return {
            "tip": self.tip.currentText(),
            "nume": self.nume.text().strip(),
            "telefon": self.telefon.text().strip(),
            "email": self.email.text().strip(),
            "adresa": self.adresa.text().strip(),
            "cui_cnp": self.cui_cnp.text().strip(),
            "observatii": self.observatii.toPlainText().strip()
        }