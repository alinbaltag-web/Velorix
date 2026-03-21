from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QCheckBox, QPushButton, QMessageBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt

VERIFICARI = {
    "Motor & Transmisie": [
        "Nivel ulei motor verificat",
        "Etanseitate motor (fara scurgeri)",
        "Lant/curea transmisie reglat si lubrifiat",
        "Ambreiaj functional",
    ],
    "Frane": [
        "Frana fata functionala",
        "Frana spate functionala",
        "Nivel lichid de frana verificat",
        "Grosime placute/saboti verificata",
    ],
    "Suspensie & Directie": [
        "Furca fata fara joc si fara scurgeri",
        "Amortizor spate functional",
        "Directie fara joc excesiv",
    ],
    "Roti & Anvelope": [
        "Presiune anvelope verificata",
        "Uzura anvelope in limite normale",
        "Rulmenti roti fara joc",
    ],
    "Electrica & Lumini": [
        "Far fata functional",
        "Stop spate functional",
        "Semnalizatoare functionale",
        "Nivel incarcare acumulator OK",
    ],
    "Test Final": [
        "Test de drum efectuat",
        "Nu exista zgomote sau vibratii anormale",
        "Clientul a fost informat despre lucrarile efectuate",
    ],
}


class DialogVerificari(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fisa verificari finale")
        self.setMinimumWidth(420)
        self.setMinimumHeight(500)
        self.setModal(True)

        self.checkboxes = {}

        main_layout = QVBoxLayout(self)

        # Titlu
        lbl = QLabel("✔ Verificari obligatorii inainte de predare")
        lbl.setStyleSheet("font-size: 15px; font-weight: 600; margin-bottom: 8px;")
        main_layout.addWidget(lbl)

        # Scroll area pentru verificari
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(8)

        for categorie, iteme in VERIFICARI.items():
            # Header categorie
            lbl_cat = QLabel(f"📋 {categorie}")
            lbl_cat.setStyleSheet(
                "font-weight: bold; font-size: 13px; "
                "color: #1A73E8; margin-top: 8px;"
            )
            container_layout.addWidget(lbl_cat)

            self.checkboxes[categorie] = []
            for item in iteme:
                chk = QCheckBox(item)
                chk.setStyleSheet("margin-left: 12px;")
                container_layout.addWidget(chk)
                self.checkboxes[categorie].append(chk)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Buton selectare rapida
        btn_row = QHBoxLayout()
        self.btn_all = QPushButton("✔ Selecteaza toate")
        self.btn_all.clicked.connect(self.selecteaza_toate)

        self.btn_none = QPushButton("✖ Deselecteaza toate")
        self.btn_none.clicked.connect(self.deselecteaza_toate)

        btn_row.addWidget(self.btn_all)
        btn_row.addWidget(self.btn_none)
        main_layout.addLayout(btn_row)

        # Buton confirmare
        self.btn_ok = QPushButton("💾 Confirma si continua")
        self.btn_ok.setObjectName("primary")
        self.btn_ok.clicked.connect(self.confirm)
        main_layout.addWidget(self.btn_ok)

    def selecteaza_toate(self):
        for chk_list in self.checkboxes.values():
            for chk in chk_list:
                chk.setChecked(True)

    def deselecteaza_toate(self):
        for chk_list in self.checkboxes.values():
            for chk in chk_list:
                chk.setChecked(False)

    def confirm(self):
        nebifate = []
        for categorie, chk_list in self.checkboxes.items():
            for chk in chk_list:
                if not chk.isChecked():
                    nebifate.append(f"• {chk.text()}")

        if nebifate:
            lista = "\n".join(nebifate[:5])
            if len(nebifate) > 5:
                lista += f"\n... si inca {len(nebifate) - 5} verificari"
            QMessageBox.warning(
                self,
                "Verificari incomplete",
                f"Urmatoarele verificari nu sunt bifate:\n\n{lista}"
            )
            return

        self.accept()

    def get_results(self):
        rezultate = {}
        for categorie, chk_list in self.checkboxes.items():
            rezultate[categorie] = {
                chk.text(): chk.isChecked()
                for chk in chk_list
            }
        return rezultate