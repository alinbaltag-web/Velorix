from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDoubleSpinBox,
    QPushButton, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from database import get_connection

# ============================================================
# LUCRARI PREDEFINITE CU NORMATIV RAR
# ============================================================
LUCRARI_PREDEFINITE = {
    "Schimb ulei motor + filtru":               {"ore_rar": 0.3, "categorie": "Motor"},
    "Schimb bujii":                             {"ore_rar": 0.5, "categorie": "Motor"},
    "Schimb filtru aer":                        {"ore_rar": 0.3, "categorie": "Motor"},
    "Reglaj supape":                            {"ore_rar": 2.0, "categorie": "Motor"},
    "Schimb lant distributie + role":           {"ore_rar": 4.0, "categorie": "Motor"},
    "Schimb garnitura chiulasa":                {"ore_rar": 5.0, "categorie": "Motor"},
    "Rectificare chiulasa":                     {"ore_rar": 3.0, "categorie": "Motor"},
    "Schimb piston + segmenti":                 {"ore_rar": 6.0, "categorie": "Motor"},
    "Schimb pompa ulei":                        {"ore_rar": 3.5, "categorie": "Motor"},
    "Schimb simeringuri arbore cotit":          {"ore_rar": 5.0, "categorie": "Motor"},
    "Diagnosticare motor":                      {"ore_rar": 1.0, "categorie": "Motor"},
    "Curatare carburator":                      {"ore_rar": 1.5, "categorie": "Motor"},
    "Reglaj carburator":                        {"ore_rar": 0.5, "categorie": "Motor"},
    "Schimb carburator":                        {"ore_rar": 1.5, "categorie": "Motor"},
    "Curatare injector":                        {"ore_rar": 1.0, "categorie": "Motor"},
    "Schimb injector":                          {"ore_rar": 1.5, "categorie": "Motor"},
    "Schimb filtru combustibil":                {"ore_rar": 0.5, "categorie": "Motor"},
    "Schimb pompa combustibil":                 {"ore_rar": 1.5, "categorie": "Motor"},
    "Schimb lant transmisie + pinioane":        {"ore_rar": 1.0, "categorie": "Transmisie"},
    "Schimb curea transmisie CVT":              {"ore_rar": 1.5, "categorie": "Transmisie"},
    "Schimb role variator CVT":                 {"ore_rar": 1.0, "categorie": "Transmisie"},
    "Schimb ambreiaj":                          {"ore_rar": 2.5, "categorie": "Transmisie"},
    "Reglaj ambreiaj":                          {"ore_rar": 0.5, "categorie": "Transmisie"},
    "Schimb ulei cutie viteze":                 {"ore_rar": 0.5, "categorie": "Transmisie"},
    "Schimb pinion fata":                       {"ore_rar": 0.5, "categorie": "Transmisie"},
    "Schimb coroana spate":                     {"ore_rar": 1.0, "categorie": "Transmisie"},
    "Schimb placute frana fata":               {"ore_rar": 0.5, "categorie": "Frane"},
    "Schimb placute frana spate":              {"ore_rar": 0.5, "categorie": "Frane"},
    "Schimb disc frana fata":                  {"ore_rar": 1.0, "categorie": "Frane"},
    "Schimb disc frana spate":                 {"ore_rar": 1.0, "categorie": "Frane"},
    "Purjare lichid de frana fata":            {"ore_rar": 0.5, "categorie": "Frane"},
    "Purjare lichid de frana spate":           {"ore_rar": 0.5, "categorie": "Frane"},
    "Schimb pompa frana fata":                 {"ore_rar": 1.5, "categorie": "Frane"},
    "Schimb pompa frana spate":                {"ore_rar": 1.5, "categorie": "Frane"},
    "Schimb furtun frana":                     {"ore_rar": 1.0, "categorie": "Frane"},
    "Reglaj frana tambur spate":               {"ore_rar": 0.3, "categorie": "Frane"},
    "Schimb sabot frana tambur":               {"ore_rar": 0.5, "categorie": "Frane"},
    "Schimb ulei furca fata":                  {"ore_rar": 1.5, "categorie": "Suspensie"},
    "Schimb simeringuri furca fata":           {"ore_rar": 2.0, "categorie": "Suspensie"},
    "Schimb amortizor spate":                  {"ore_rar": 1.0, "categorie": "Suspensie"},
    "Schimb rulmenti roata fata":              {"ore_rar": 1.0, "categorie": "Suspensie"},
    "Schimb rulmenti roata spate":             {"ore_rar": 1.0, "categorie": "Suspensie"},
    "Schimb cap de punte fata":                {"ore_rar": 1.5, "categorie": "Suspensie"},
    "Reglaj geometrie furca":                  {"ore_rar": 1.0, "categorie": "Suspensie"},
    "Schimb anvelopa fata":                    {"ore_rar": 0.5, "categorie": "Roti"},
    "Schimb anvelopa spate":                   {"ore_rar": 0.7, "categorie": "Roti"},
    "Echilibrare roata fata":                  {"ore_rar": 0.3, "categorie": "Roti"},
    "Echilibrare roata spate":                 {"ore_rar": 0.3, "categorie": "Roti"},
    "Schimb camera fata":                      {"ore_rar": 0.5, "categorie": "Roti"},
    "Schimb camera spate":                     {"ore_rar": 0.5, "categorie": "Roti"},
    "Verificare si reglaj presiune anvelope":  {"ore_rar": 0.2, "categorie": "Roti"},
    "Schimb baterie acumulator":               {"ore_rar": 0.3, "categorie": "Electrica"},
    "Schimb alternator":                       {"ore_rar": 2.0, "categorie": "Electrica"},
    "Schimb regulator tensiune":               {"ore_rar": 0.5, "categorie": "Electrica"},
    "Schimb demaror":                          {"ore_rar": 1.5, "categorie": "Electrica"},
    "Schimb bobina aprindere":                 {"ore_rar": 0.5, "categorie": "Electrica"},
    "Schimb senzor pozitie ax came":           {"ore_rar": 1.0, "categorie": "Electrica"},
    "Schimb senzor temperatura motor":         {"ore_rar": 0.5, "categorie": "Electrica"},
    "Diagnosticare sistem electric":           {"ore_rar": 1.0, "categorie": "Electrica"},
    "Schimb far fata":                         {"ore_rar": 0.5, "categorie": "Electrica"},
    "Schimb bec far":                          {"ore_rar": 0.3, "categorie": "Electrica"},
    "Schimb contacte / sigurante":             {"ore_rar": 0.5, "categorie": "Electrica"},
    "Reparatie instalatie electrica":          {"ore_rar": 2.0, "categorie": "Electrica"},
    "Demontare / montare carenaj complet":     {"ore_rar": 2.0, "categorie": "Carenaj"},
    "Demontare / montare carenaj partial":     {"ore_rar": 1.0, "categorie": "Carenaj"},
    "Schimb oglinzi":                          {"ore_rar": 0.3, "categorie": "Carenaj"},
    "Schimb parbriz / deflector":              {"ore_rar": 0.5, "categorie": "Carenaj"},
    "Schimb sa":                               {"ore_rar": 0.3, "categorie": "Carenaj"},
    "Revizie 1 an / 5.000 km":                {"ore_rar": 1.5, "categorie": "Revizie"},
    "Revizie 2 ani / 10.000 km":              {"ore_rar": 3.0, "categorie": "Revizie"},
    "Revizie completa sezon":                  {"ore_rar": 4.0, "categorie": "Revizie"},
    "Inspectie tehnica pre-ITP":               {"ore_rar": 1.0, "categorie": "Revizie"},
    "Pregatire depozitare iarna":              {"ore_rar": 1.5, "categorie": "Revizie"},
    "Repunere in functiune dupa iarna":        {"ore_rar": 1.5, "categorie": "Revizie"},
}

CATEGORII = sorted(set(v["categorie"] for v in LUCRARI_PREDEFINITE.values()))


def _load_mecanici():
    """Returneaza lista de mecanici din tabela users."""
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT username FROM users
            WHERE role = 'mecanic'
            ORDER BY username
        """)
        rows = [r[0] for r in cur.fetchall()]
        con.close()
        return rows
    except Exception:
        return []


class DialogLucrare(QDialog):
    def __init__(self, parent=None, tarif_ora=150.0, tva=21.0, titlu="Adauga lucrare"):
        super().__init__(parent)
        self.tarif_ora = tarif_ora
        self.tva = tva
        self.setWindowTitle(titlu)
        self.setMinimumWidth(520)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # ── Selector categorie + lucrare predefinita ──
        pre_layout = QHBoxLayout()

        self.cmb_categorie = QComboBox()
        self.cmb_categorie.addItem("Toate categoriile")
        for cat in CATEGORII:
            self.cmb_categorie.addItem(cat)
        self.cmb_categorie.currentTextChanged.connect(self.filtreaza_lucrari)

        self.cmb_lucrare = QComboBox()
        self.cmb_lucrare.setEditable(False)
        self.cmb_lucrare.currentTextChanged.connect(self.on_lucrare_predefinita_changed)

        pre_layout.addWidget(QLabel("Categorie:"))
        pre_layout.addWidget(self.cmb_categorie, 1)
        pre_layout.addWidget(QLabel("Lucrare:"))
        pre_layout.addWidget(self.cmb_lucrare, 2)
        layout.addLayout(pre_layout)

        # ── Formular ──
        form = QFormLayout()
        form.setSpacing(10)

        self.descriere = QLineEdit()
        self.descriere.setPlaceholderText("Descriere lucrare")

        self.ore_rar = QDoubleSpinBox()
        self.ore_rar.setRange(0.0, 50.0)
        self.ore_rar.setSingleStep(0.5)
        self.ore_rar.setDecimals(1)
        self.ore_rar.setSuffix(" ore RAR")
        self.ore_rar.valueChanged.connect(self.recalculeaza_cost)

        self.tarif = QDoubleSpinBox()
        self.tarif.setRange(0.0, 9999.0)
        self.tarif.setSingleStep(10.0)
        self.tarif.setDecimals(2)
        self.tarif.setSuffix(" RON/ora")
        self.tarif.setValue(self.tarif_ora)
        self.tarif.valueChanged.connect(self.recalculeaza_cost)

        self.cost = QDoubleSpinBox()
        self.cost.setRange(0.0, 99999.0)
        self.cost.setSingleStep(10.0)
        self.cost.setDecimals(2)
        self.cost.setSuffix(" RON")

        self.lbl_calcul = QLabel("")
        self.lbl_calcul.setStyleSheet("color: #1A73E8; font-size: 11px;")
        self.lbl_calcul.setWordWrap(True)

        self.cost.valueChanged.connect(self._update_label_from_cost)

        # ── Mecanic ──
        self.cmb_mecanic = QComboBox()
        self.cmb_mecanic.setMinimumHeight(28)
        self.cmb_mecanic.addItem("— Nealocat —", "")
        for mec in _load_mecanici():
            self.cmb_mecanic.addItem(mec, mec)
        self.cmb_mecanic.setStyleSheet("""
            QComboBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
            }
            QComboBox:focus { border-color: #3b82f6; }
        """)

        form.addRow("Descriere *:", self.descriere)
        form.addRow("Ore normativ RAR:", self.ore_rar)
        form.addRow("Tarif ora manopera:", self.tarif)
        form.addRow("Cost manopera cu TVA (RON):", self.cost)
        form.addRow("", self.lbl_calcul)
        form.addRow("Mecanic:", self.cmb_mecanic)

        layout.addLayout(form)

        # ── Butoane ──
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

        self.filtreaza_lucrari("Toate categoriile")

    def filtreaza_lucrari(self, categorie):
        self.cmb_lucrare.blockSignals(True)
        self.cmb_lucrare.clear()
        self.cmb_lucrare.addItem("-- Selecteaza lucrare predefinita --")
        for nume, date in sorted(LUCRARI_PREDEFINITE.items()):
            if categorie == "Toate categoriile" or date["categorie"] == categorie:
                self.cmb_lucrare.addItem(nume)
        self.cmb_lucrare.blockSignals(False)

    def on_lucrare_predefinita_changed(self, text):
        if text in LUCRARI_PREDEFINITE:
            date = LUCRARI_PREDEFINITE[text]
            self.descriere.setText(text)
            self.ore_rar.setValue(date["ore_rar"])
            self.recalculeaza_cost()

    def recalculeaza_cost(self):
        ore = self.ore_rar.value()
        tarif = self.tarif.value()
        cost_fara_tva = round(ore * tarif, 2)
        tva_suma = round(cost_fara_tva * self.tva / 100, 2)
        cost_cu_tva = round(cost_fara_tva + tva_suma, 2)
        # Campul afiseaza si accepta pretul CU TVA
        self.cost.setValue(cost_cu_tva)
        if ore > 0:
            self.lbl_calcul.setText(
                f"{ore} ore × {tarif:.2f} RON/ora = {cost_fara_tva:.2f} RON fara TVA"
                f"  +  TVA {self.tva:.0f}% ({tva_suma:.2f} RON)"
            )
        else:
            self._update_label_from_cost(self.cost.value())

    def _update_label_from_cost(self, cost_cu_tva):
        """Actualizeaza label-ul informativ cand utilizatorul modifica manual campul cost."""
        cost_fara_tva = round(cost_cu_tva / (1 + self.tva / 100), 2)
        tva_suma = round(cost_cu_tva - cost_fara_tva, 2)
        self.lbl_calcul.setText(
            f"Fara TVA: {cost_fara_tva:.2f} RON  +  TVA {self.tva:.0f}%: {tva_suma:.2f} RON"
        )

    def set_mecanic(self, mecanic_username):
        """Seteaza mecanicul in dropdown la editare."""
        if not mecanic_username:
            self.cmb_mecanic.setCurrentIndex(0)
            return
        for i in range(self.cmb_mecanic.count()):
            if self.cmb_mecanic.itemData(i) == mecanic_username:
                self.cmb_mecanic.setCurrentIndex(i)
                return
        # Daca nu e in lista (mecanic sters), il adaugam temporar
        self.cmb_mecanic.addItem(f"{mecanic_username} (inactiv)", mecanic_username)
        self.cmb_mecanic.setCurrentIndex(self.cmb_mecanic.count() - 1)

    def salveaza(self):
        if not self.descriere.text().strip():
            QMessageBox.warning(self, "Eroare", "Descrierea lucrarii este obligatorie.")
            return
        self.accept()

    def get_data(self):
        cost_cu_tva = self.cost.value()
        # Convertim la fara TVA — tabelul adauga TVA la afisare si calcul total
        cost_fara_tva = round(cost_cu_tva / (1 + self.tva / 100), 2)
        return {
            "descriere": self.descriere.text().strip(),
            "ore_rar":   self.ore_rar.value(),
            "tarif_ora": self.tarif.value(),
            "cost":      cost_fara_tva,
            "mecanic":   self.cmb_mecanic.currentData() or "",
        }
