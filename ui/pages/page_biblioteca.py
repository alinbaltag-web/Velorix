from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QScrollArea, QFrame, QLineEdit
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal
from ui.data_specificatii import SPECIFICATII


# Etichete mai lizibile pentru cheile din dictionar
ETICHETE = {
    "descriere":                       "Descriere",
    "ulei_motor_tip":                  "Tip ulei motor",
    "ulei_motor_cantitate":            "Cantitate ulei motor",
    "ulei_transmisie_tip":             "Tip ulei transmisie",
    "ulei_transmisie_cantitate":       "Cantitate ulei transmisie",
    "ulei_furca_tip":                  "Tip ulei furca",
    "ulei_furca_cantitate":            "Cantitate ulei furca",
    "lichid_racire_cantitate":         "Lichid racire (cantitate)",
    "lichid_frana_tip":                "Tip lichid frana",
    "lichid_frana_interval":           "Schimb lichid frana",
    "bujie_tip":                       "Bujie",
    "presiune_roti_fata":              "Presiune roata fata",
    "presiune_roti_spate":             "Presiune roata spate",
    "presiune_roti_spate_cu_pasant":   "Presiune roata spate (cu pasant)",
    "interval_service":                "Interval service",
    "interval_curea":                  "Interval curea",
    "interval_role":                   "Interval role",
    "filtru_ulei_tip":                 "Filtru ulei (numar piesa)",
    "filtru_ulei_hiflofiltro":         "Filtru ulei Hiflofiltro",
    "filtru_ulei_champion":            "Filtru ulei Champion",
    # cupluri
    "buson_ulei":    "Buson ulei",
    "filtru_ulei":   "Filtru ulei",
    "roata_fata":    "Roata fata",
    "roata_spate":   "Roata spate",
    "etrier_fata":   "Etrier fata",
    "etrier_spate":  "Etrier spate",
}

def _label(cheie):
    return ETICHETE.get(cheie, cheie.replace("_", " ").title())


# ============================================================
# WIDGET PENTRU AFISAREA FISEI TEHNICE
# ============================================================
class FisaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(12)

    def clear(self):
        for i in reversed(range(self.layout.count())):
            item = self.layout.takeAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_title(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        lbl.setStyleSheet("color: #1A73E8; margin-bottom: 10px;")
        lbl.setWordWrap(True)
        self.layout.addWidget(lbl)

    def add_section(self, title, content_dict, icon="📘", color="#333333"):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)

        lbl_title = QLabel(f"{icon} {title}")
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {color};")
        card_layout.addWidget(lbl_title)

        for key, value in content_dict.items():
            lbl = QLabel(f"<b>{_label(key)}:</b> {value}")
            lbl.setFont(QFont("Segoe UI", 11))
            lbl.setWordWrap(True)
            card_layout.addWidget(lbl)

        self.layout.addWidget(card)

    def add_text(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 12))
        lbl.setWordWrap(True)
        self.layout.addWidget(lbl)


# ============================================================
# PAGINA BIBLIOTECA
# ============================================================
class PageBiblioteca(QWidget):
    specificatii_pentru_fisa = pyqtSignal(dict)
    specificatii_pentru_deviz = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Titlu pagina
        self.lbl_title = QLabel("Biblioteca – Fise Tehnice")
        self.lbl_title.setObjectName("pageTitle")
        layout.addWidget(self.lbl_title)

        # Cautare rapida
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cauta model...")
        self.search.textChanged.connect(self.cauta_model)
        layout.addWidget(self.search)

        # Filtre
        filtre_layout = QHBoxLayout()

        self.combo_marca = QComboBox()
        self.combo_model = QComboBox()
        self.combo_euro = QComboBox()
        self.combo_varianta = QComboBox()

        self.combo_marca.addItem("Selecteaza marca")
        self.combo_model.addItem("Selecteaza modelul")
        self.combo_euro.addItem("Selecteaza Euro")
        self.combo_varianta.addItem("Selecteaza varianta")

        filtre_layout.addWidget(self.combo_marca)
        filtre_layout.addWidget(self.combo_model)
        filtre_layout.addWidget(self.combo_euro)
        filtre_layout.addWidget(self.combo_varianta)

        layout.addLayout(filtre_layout)

        # Populare marca
        for marca in SPECIFICATII.keys():
            self.combo_marca.addItem(marca)

        # Conectare filtre
        self.combo_marca.currentIndexChanged.connect(self.on_marca_changed)
        self.combo_model.currentIndexChanged.connect(self.on_model_changed)
        self.combo_euro.currentIndexChanged.connect(self.on_euro_changed)

        # Butoane pe un rand
        btn_row = QHBoxLayout()

        self.btn_cauta = QPushButton("Cauta fisa tehnica")
        self.btn_cauta.setStyleSheet("""
            QPushButton {
                background-color: #1A73E8;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1664c4;
            }
        """)
        self.btn_cauta.clicked.connect(self.afiseaza_fisa)
        btn_row.addWidget(self.btn_cauta)

        self.btn_trimite_fisa = QPushButton("Trimite in Fisa Service")
        self.btn_trimite_fisa.setStyleSheet("""
            QPushButton {
                background-color: #34A853;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2c8e46;
            }
        """)
        self.btn_trimite_fisa.clicked.connect(self.trimite_in_fisa_service)
        btn_row.addWidget(self.btn_trimite_fisa)

        # Buton resetare
        self.btn_reset = QPushButton("Resetare")
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        self.btn_reset.clicked.connect(self.reset_biblioteca)
        btn_row.addWidget(self.btn_reset)

        layout.addLayout(btn_row)

        # Zona de afisare fisa tehnica
        self.fisa_widget = FisaWidget()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.fisa_widget)

        layout.addWidget(scroll)

    # ================================
    # Helper reset combo
    # ================================
    def _reset_combo(self, combo, placeholder):
        combo.clear()
        combo.addItem(placeholder)

    # ================================
    # Cautare rapida
    # ================================
    def cauta_model(self, text):
        text = text.lower().strip()
        if not text:
            return

        for marca, modele in SPECIFICATII.items():
            for model in modele.keys():
                if text in model.lower():
                    self.combo_marca.setCurrentText(marca)
                    self.combo_model.setCurrentText(model)
                    return

    # ================================
    # Marca → Modele
    # ================================
    def on_marca_changed(self):
        marca = self.combo_marca.currentText()

        self._reset_combo(self.combo_model, "Selecteaza modelul")
        self._reset_combo(self.combo_euro, "Selecteaza Euro")
        self._reset_combo(self.combo_varianta, "Selecteaza varianta")

        if marca in SPECIFICATII:
            for model in SPECIFICATII[marca].keys():
                self.combo_model.addItem(model)

    # ================================
    # Model → Euro
    # ================================
    def on_model_changed(self):
        marca = self.combo_marca.currentText()
        model = self.combo_model.currentText()

        self._reset_combo(self.combo_euro, "Selecteaza Euro")
        self._reset_combo(self.combo_varianta, "Selecteaza varianta")

        if marca in SPECIFICATII and model in SPECIFICATII[marca]:
            for euro in SPECIFICATII[marca][model].keys():
                self.combo_euro.addItem(euro)

    # ================================
    # Euro → Variante
    # ================================
    def on_euro_changed(self):
        marca = self.combo_marca.currentText()
        model = self.combo_model.currentText()
        euro = self.combo_euro.currentText()

        self._reset_combo(self.combo_varianta, "Selecteaza varianta")

        if (marca in SPECIFICATII and
            model in SPECIFICATII[marca] and
            euro in SPECIFICATII[marca][model]):

            for varianta in SPECIFICATII[marca][model][euro].keys():
                self.combo_varianta.addItem(varianta)

    # ================================
    # Afisare fisa tehnica
    # ================================
    def afiseaza_fisa(self):
        fisa = self._get_fisa_curenta()

        if fisa is None:
            self.fisa_widget.clear()
            self.fisa_widget.add_text("Selecteaza toate campurile corect.")
            return

        marca = self.combo_marca.currentText()
        model = self.combo_model.currentText()
        euro = self.combo_euro.currentText()
        varianta = self.combo_varianta.currentText()

        self.fisa_widget.clear()
        self.fisa_widget.add_title(f"{marca} {model} – {euro} – {varianta}")

        # ── Grupam campurile plate pe categorii ──────────────────────
        # Chei speciale pentru filtre ulei
        CHEIE_FILTRU = {"filtru_ulei_hiflofiltro", "filtru_ulei_champion", "filtru_ulei_tip"}

        # Categorii de campuri plate
        cat_general    = {}   # descriere, bujie, presiuni
        cat_ulei       = {}   # ulei_motor_*, ulei_transmisie_*, ulei_furca_*
        cat_lichide    = {}   # lichid_racire, lichid_frana_*
        cat_intervale  = {}   # interval_*
        cat_filtre     = {}   # filtru_ulei_*
        cat_subdicts   = {}   # cupluri_strangere etc. (sub-dictionare)

        for cheie, valoare in fisa.items():
            if isinstance(valoare, dict):
                cat_subdicts[cheie] = valoare
            elif cheie in CHEIE_FILTRU:
                cat_filtre[cheie] = valoare
            elif cheie.startswith("ulei_"):
                cat_ulei[cheie] = valoare
            elif cheie.startswith("lichid_"):
                cat_lichide[cheie] = valoare
            elif cheie.startswith("interval_"):
                cat_intervale[cheie] = valoare
            else:
                cat_general[cheie] = valoare

        # ── Afisam sectiunile in ordine logica ───────────────────────
        if cat_general:
            self.fisa_widget.add_section("General", cat_general, "📋")

        if cat_ulei:
            self.fisa_widget.add_section("Uleiuri", cat_ulei, "🛢️")

        if cat_lichide:
            self.fisa_widget.add_section("Lichide", cat_lichide, "💧")

        if cat_intervale:
            self.fisa_widget.add_section("Intervale service", cat_intervale, "🔄")

        # ── Sectiune dedicata filtre ulei ─────────────────────────────
        if cat_filtre:
            self.fisa_widget.add_section(
                "Filtre ulei motor",
                cat_filtre,
                icon="🔧",
                color="#E67E22"
            )

        # ── Sub-dictionare (cupluri de strangere etc.) ────────────────
        for cheie, subdict in cat_subdicts.items():
            self.fisa_widget.add_section(cheie, subdict, "⚙️")

    # ================================
    # Trimite in Fisa Service
    # ================================
    def trimite_in_fisa_service(self):
        fisa = self._get_fisa_curenta()
        if fisa is not None:
            self.specificatii_pentru_fisa.emit(fisa)

    # ================================
    # Resetare completa
    # ================================
    def reset_biblioteca(self):
        self.search.clear()
        self.combo_marca.setCurrentIndex(0)
        self.combo_model.clear()
        self.combo_model.addItem("Selecteaza modelul")
        self.combo_euro.clear()
        self.combo_euro.addItem("Selecteaza Euro")
        self.combo_varianta.clear()
        self.combo_varianta.addItem("Selecteaza varianta")

        self.fisa_widget.clear()

        if hasattr(self.parent, "page_fisa_service"):
            self.parent.page_fisa_service.txt_observatii.clear()

        from ui.utils_toast import show_toast
        show_toast(self.parent, "Biblioteca si Observatiile au fost resetate.")

    # ================================
    # Helper: fisa curenta
    # ================================
    def _get_fisa_curenta(self):
        marca = self.combo_marca.currentText()
        model = self.combo_model.currentText()
        euro = self.combo_euro.currentText()
        varianta = self.combo_varianta.currentText()

        marca_data = SPECIFICATII.get(marca)
        if not marca_data:
            return None

        model_data = marca_data.get(model)
        if not model_data:
            return None

        euro_data = model_data.get(euro)
        if not euro_data:
            return None

        varianta_data = euro_data.get(varianta)
        if not varianta_data:
            return None

        return varianta_data

    # ================================
    # Limba
    # ================================
    def apply_language(self):
        if self.parent.app_language == "RO":
            self.lbl_title.setText("Biblioteca – Fise Tehnice")
            self.search.setPlaceholderText("Cauta model...")
            self.combo_marca.setItemText(0, "Selecteaza marca")
            self.combo_model.setItemText(0, "Selecteaza modelul")
            self.combo_euro.setItemText(0, "Selecteaza Euro")
            self.combo_varianta.setItemText(0, "Selecteaza varianta")
            self.btn_cauta.setText("Cauta fisa tehnica")
            self.btn_trimite_fisa.setText("Trimite in Fisa Service")
            self.btn_reset.setText("Resetare")
        else:
            self.lbl_title.setText("Library – Technical Sheets")
            self.search.setPlaceholderText("Search model...")
            self.combo_marca.setItemText(0, "Select brand")
            self.combo_model.setItemText(0, "Select model")
            self.combo_euro.setItemText(0, "Select Euro")
            self.combo_varianta.setItemText(0, "Select variant")
            self.btn_cauta.setText("Search technical sheet")
            self.btn_trimite_fisa.setText("Send to Service Sheet")
            self.btn_reset.setText("Reset")
