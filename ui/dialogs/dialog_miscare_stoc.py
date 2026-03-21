from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QDoubleSpinBox, QComboBox, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from database import get_connection
from ui.session_manager import SessionManager

class DialogMiscareStoc(QDialog):
    def __init__(self, parent=None, piesa_id=None):
        super().__init__(parent)
        self.piesa_id = piesa_id
        self.setWindowTitle("Miscare Stoc")
        self.setMinimumWidth(520)
        self.setMinimumHeight(520)
        self.setModal(True)
        self.init_ui()
        self.load_info_piesa()
        self.load_istoric()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Titlu
        self.lbl_titlu = QLabel("Miscare Stoc")
        self.lbl_titlu.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(self.lbl_titlu)

        # Info piesa
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.lbl_info)

        # Stoc curent card
        self.lbl_stoc_curent = QLabel("Stoc curent: —")
        self.lbl_stoc_curent.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #10b981; "
            "background: #0f2d1f; padding: 8px 16px; border-radius: 6px;"
        )
        layout.addWidget(self.lbl_stoc_curent)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #334155;")
        layout.addWidget(sep)

        # Form miscare
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.combo_tip = QComboBox()
        self.combo_tip.addItem("📥  Intrare (adauga stoc)", "intrare")
        self.combo_tip.addItem("📤  Iesire (scade stoc)", "iesire")
        self.combo_tip.addItem("🔧  Corectie inventar", "corectie")
        self.combo_tip.currentIndexChanged.connect(self.update_preview)
        form.addRow("Tip Miscare:", self.combo_tip)

        self.spin_cantitate = QDoubleSpinBox()
        self.spin_cantitate.setRange(0.01, 99999)
        self.spin_cantitate.setDecimals(2)
        self.spin_cantitate.setValue(1)
        self.spin_cantitate.valueChanged.connect(self.update_preview)
        form.addRow("Cantitate:", self.spin_cantitate)

        self.input_motiv = QLineEdit()
        self.input_motiv.setPlaceholderText("ex: Achizitie furnizor, Inventar...")
        form.addRow("Motiv:", self.input_motiv)

        layout.addLayout(form)

        # Preview stoc dupa
        self.lbl_preview = QLabel("Stoc dupa operatie: —")
        self.lbl_preview.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 6px 12px; "
            "border-radius: 4px; background: #1e293b;"
        )
        layout.addWidget(self.lbl_preview)

        # Butoane
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_anuleaza = QPushButton("Anuleaza")
        self.btn_anuleaza.setObjectName("secondaryButton")
        self.btn_anuleaza.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_anuleaza)

        self.btn_salveaza = QPushButton("✅ Confirma")
        self.btn_salveaza.setObjectName("primaryButton")
        self.btn_salveaza.clicked.connect(self.salveaza)
        btn_layout.addWidget(self.btn_salveaza)

        layout.addLayout(btn_layout)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #334155;")
        layout.addWidget(sep2)

        # Istoric miscari
        lbl_istoric = QLabel("Istoric Miscari")
        lbl_istoric.setStyleSheet("font-weight: bold; color: #94a3b8;")
        layout.addWidget(lbl_istoric)

        self.tabel_istoric = QTableWidget()
        self.tabel_istoric.setColumnCount(5)
        self.tabel_istoric.setHorizontalHeaderLabels(
            ["Tip", "Cantitate", "Stoc Dupa", "Motiv", "Data"]
        )
        self.tabel_istoric.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabel_istoric.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel_istoric.verticalHeader().setVisible(False)
        self.tabel_istoric.setAlternatingRowColors(True)
        self.tabel_istoric.setMaximumHeight(160)
        header = self.tabel_istoric.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.tabel_istoric)

    def load_info_piesa(self):
        if not self.piesa_id:
            return
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT s.nume, s.cod, s.stoc_curent, s.unitate, c.nume
            FROM stoc_piese s
            LEFT JOIN categorii_piese c ON s.id_categorie = c.id
            WHERE s.id = ?
        """, (self.piesa_id,))
        row = cur.fetchone()
        con.close()
        if not row:
            return
        self.stoc_curent = float(row[2]) if row[2] else 0
        self.unitate = row[3] or "buc"
        self.lbl_titlu.setText(f"Miscare Stoc — {row[0]}")
        self.lbl_info.setText(f"Cod: {row[1] or '—'}  |  Categorie: {row[4] or '—'}")
        self.lbl_stoc_curent.setText(
            f"Stoc curent: {self.stoc_curent} {self.unitate}"
        )
        self.spin_cantitate.setSuffix(f"  {self.unitate}")
        self.update_preview()

    def update_preview(self):
        if not hasattr(self, 'stoc_curent'):
            return
        tip = self.combo_tip.currentData()
        cant = self.spin_cantitate.value()

        if tip == "intrare":
            stoc_nou = self.stoc_curent + cant
            culoare = "#10b981"
            semn = "+"
        elif tip == "iesire":
            stoc_nou = self.stoc_curent - cant
            culoare = "#ef4444" if stoc_nou < 0 else "#f59e0b"
            semn = "-"
        else:  # corectie
            stoc_nou = cant
            culoare = "#3b82f6"
            semn = "="

        self.lbl_preview.setText(
            f"Stoc dupa operatie: <span style='color:{culoare}'>"
            f"{semn if tip != 'corectie' else ''}{stoc_nou:.2f} {getattr(self, 'unitate', 'buc')}"
            f"</span>"
        )
        self.lbl_preview.setTextFormat(Qt.RichText)

        if tip == "iesire" and stoc_nou < 0:
            self.lbl_preview.setStyleSheet(
                "font-size: 14px; font-weight: bold; padding: 6px 12px; "
                "border-radius: 4px; background: #3d1515;"
            )
        else:
            self.lbl_preview.setStyleSheet(
                "font-size: 14px; font-weight: bold; padding: 6px 12px; "
                "border-radius: 4px; background: #1e293b;"
            )

    def load_istoric(self):
        if not self.piesa_id:
            return
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT tip, cantitate, stoc_dupa, motiv, data
            FROM miscari_stoc
            WHERE id_piesa = ?
            ORDER BY data DESC
            LIMIT 20
        """, (self.piesa_id,))
        rows = cur.fetchall()
        con.close()

        self.tabel_istoric.setRowCount(0)
        for row in rows:
            r = self.tabel_istoric.rowCount()
            self.tabel_istoric.insertRow(r)
            tip = row[0]
            
            # Emoji si culoare dupa tip
            if tip == "intrare":
                tip_text = "📥 Intrare"
                culoare = QColor("#0f2d1f")
            elif tip == "iesire":
                tip_text = "📤 Iesire"
                culoare = QColor("#3d1515")
            else:
                tip_text = "🔧 Corectie"
                culoare = QColor("#1e293b")

            valori = [tip_text, str(row[1]), str(row[2] or "—"), row[3] or "—", row[4] or "—"]
            for col, val in enumerate(valori):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(culoare)
                self.tabel_istoric.setItem(r, col, item)

    def salveaza(self):
        tip = self.combo_tip.currentData()
        cant = self.spin_cantitate.value()
        motiv = self.input_motiv.text().strip()
        user = SessionManager.get_user()        
        if tip == "intrare":
            stoc_nou = self.stoc_curent + cant
        elif tip == "iesire":
            stoc_nou = self.stoc_curent - cant
        else:
            stoc_nou = cant

        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE stoc_piese SET stoc_curent=? WHERE id=?",
            (stoc_nou, self.piesa_id)
        )
        cur.execute("""
            INSERT INTO miscari_stoc (id_piesa, tip, cantitate, stoc_dupa, motiv, username)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.piesa_id, tip, cant, stoc_nou, motiv, user))
        con.commit()
        con.close()
        self.accept()