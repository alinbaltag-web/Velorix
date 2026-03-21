"""
VELORIX — dialog_incasare.py
==============================
Dialog pentru inregistrarea unei incasari pe o factura.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit,
    QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QDate
from database import get_connection, log_action
from datetime import datetime


class DialogIncasare(QDialog):
    def __init__(self, parent, id_factura, user=""):
        super().__init__(parent)
        self.id_factura = id_factura
        self.user       = user

        self.setWindowTitle("Inregistrare incasare")
        self.setFixedSize(420, 380)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #f8fafc; }
            QLabel { font-size: 12px; color: #374151; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                min-height: 32px;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #1A73E8; }
        """)

        self._load_factura()
        self._build_ui()

    def _load_factura(self):
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT f.numar, f.total_cu_tva, f.suma_incasata,
                   COALESCE(c.nume, '—')
            FROM facturi f
            LEFT JOIN clienti c ON c.id = f.id_client
            WHERE f.id = ?
        """, (self.id_factura,))
        row = cur.fetchone()
        con.close()

        if row:
            self._numar    = row[0]
            self._total    = row[1]
            self._incasat  = row[2]
            self._rest     = round(row[1] - row[2], 2)
            self._client   = row[3]
        else:
            self._numar   = "—"
            self._total   = 0
            self._incasat = 0
            self._rest    = 0
            self._client  = "—"

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(12)

        # ── Titlu ──
        lbl = QLabel("Inregistrare incasare")
        lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #1e3a5f;")
        main.addWidget(lbl)

        # ── Info factura ──
        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
            }
        """)
        info_lay = QVBoxLayout(info)
        info_lay.setContentsMargins(12, 8, 12, 8)
        info_lay.setSpacing(3)

        def info_row(label, value, bold=False):
            h = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("font-size: 11px; color: #6b7280;")
            v = QLabel(value)
            v.setStyleSheet(
                f"font-size: 12px; color: #1e3a5f; "
                f"font-weight: {'700' if bold else '400'};"
            )
            h.addWidget(l)
            h.addStretch()
            h.addWidget(v)
            return h

        info_lay.addLayout(info_row("Factura:", self._numar))
        info_lay.addLayout(info_row("Client:", self._client))
        info_lay.addLayout(info_row("Total factura:", f"{self._total:,.2f} RON"))
        info_lay.addLayout(info_row("Deja incasat:", f"{self._incasat:,.2f} RON"))
        info_lay.addLayout(info_row("Rest de incasat:", f"{self._rest:,.2f} RON", bold=True))
        main.addWidget(info)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #e2e8f0;")
        main.addWidget(sep)

        # ── Suma ──
        main.addWidget(QLabel("Suma incasata (RON) *"))
        self.spin_suma = QDoubleSpinBox()
        self.spin_suma.setMinimum(0.01)
        self.spin_suma.setMaximum(self._rest if self._rest > 0 else 999999)
        self.spin_suma.setValue(self._rest)
        self.spin_suma.setDecimals(2)
        self.spin_suma.setSuffix(" RON")
        self.spin_suma.setStyleSheet("""
            QDoubleSpinBox {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
            }
        """)
        main.addWidget(self.spin_suma)

        # ── Metoda plata ──
        main.addWidget(QLabel("Metoda de plata *"))
        self.cmb_metoda = QComboBox()
        self.cmb_metoda.addItems(["💵 Numerar (Cash)", "💳 Card bancar", "🏦 Transfer bancar (OP)"])
        self.cmb_metoda.currentIndexChanged.connect(self._on_metoda_changed)
        main.addWidget(self.cmb_metoda)

        # ── Referinta (OP / card) ──
        self.lbl_ref = QLabel("Nr. referinta (OP / tranzactie)")
        self.lbl_ref.setVisible(False)
        main.addWidget(self.lbl_ref)

        self.txt_ref = QLineEdit()
        self.txt_ref.setPlaceholderText("ex: OP-123456 sau nr. tranzactie")
        self.txt_ref.setVisible(False)
        main.addWidget(self.txt_ref)

        # ── Data incasare ──
        main.addWidget(QLabel("Data incasarii"))
        self.date_inc = QDateEdit()
        self.date_inc.setDate(QDate.currentDate())
        self.date_inc.setCalendarPopup(True)
        main.addWidget(self.date_inc)

        # ── Butoane ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Anuleaza")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #374151;
                border: 1px solid #e2e8f0;
                border-radius: 7px;
                padding: 0 16px;
                font-size: 12px;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("✅ Inregistreaza incasarea")
        btn_save.setFixedHeight(36)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background: #059669; }
        """)
        btn_save.clicked.connect(self._salveaza)

        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_save)
        main.addLayout(btn_row)

    def _on_metoda_changed(self, idx):
        visible = idx > 0
        self.lbl_ref.setVisible(visible)
        self.txt_ref.setVisible(visible)
        if idx == 1:
            self.lbl_ref.setText("Nr. tranzactie POS *  (obligatoriu)")
            self.lbl_ref.setStyleSheet("font-size: 12px; color: #dc2626; font-weight: 600;")
            self.txt_ref.setPlaceholderText("ex: TRZ-123456")
        elif idx == 2:
            self.lbl_ref.setText("Nr. ordin de plata (OP)")
            self.lbl_ref.setStyleSheet("font-size: 12px; color: #374151;")
            self.txt_ref.setPlaceholderText("ex: OP-123456")

    def _salveaza(self):
        suma = self.spin_suma.value()
        if suma <= 0:
            QMessageBox.warning(self, "Eroare", "Suma trebuie sa fie mai mare ca 0!")
            return

        metoda_map = {0: "cash", 1: "card", 2: "op"}
        metoda    = metoda_map.get(self.cmb_metoda.currentIndex(), "cash")
        referinta = self.txt_ref.text().strip() if self.txt_ref.isVisible() else None
        data_inc  = self.date_inc.date().toString("yyyy-MM-dd")

        # Validare nr. tranzactie obligatoriu pentru card
        if metoda == "card" and not referinta:
            QMessageBox.warning(self, "Camp obligatoriu",
                "Introduceti numarul tranzactiei POS.\n"
                "Acesta se gaseste pe bonul de la terminalul card.")
            self.txt_ref.setFocus()
            return

        con = get_connection()
        cur = con.cursor()

        try:
            # Inseram incasarea
            cur.execute("""
                INSERT INTO incasari
                    (id_factura, data_incasare, suma, metoda,
                     referinta, inregistrat_de)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.id_factura, data_inc, suma, metoda,
                  referinta, self.user))

            # Actualizam suma_incasata pe factura
            cur.execute("""
                UPDATE facturi
                SET suma_incasata = suma_incasata + ?
                WHERE id = ?
            """, (suma, self.id_factura))

            # Actualizam status-ul
            cur.execute("""
                SELECT total_cu_tva, suma_incasata
                FROM facturi WHERE id = ?
            """, (self.id_factura,))
            row = cur.fetchone()

            if row:
                total, incasat = row
                if incasat >= total - 0.01:
                    status = "incasata"
                elif incasat > 0:
                    status = "partial_incasata"
                else:
                    status = "emisa"
                cur.execute(
                    "UPDATE facturi SET status = ? WHERE id = ?",
                    (status, self.id_factura)
                )

            con.commit()
            log_action(self.user, "Incasare factura",
                       f"{self._numar} | {suma:.2f} RON | {metoda}")

            # ── Post-salvare per metoda ──────────────────────
            if metoda == "cash":
                rasp = QMessageBox.question(
                    self, "Chitanta",
                    f"Incasare de {suma:,.2f} RON inregistrata!\n\n"
                    "Doriti sa generati chitanta PDF?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if rasp == QMessageBox.Yes:
                    try:
                        from ui.pdf.chitanta_pdf import genereaza_chitanta
                        genereaza_chitanta(
                            id_factura     = self.id_factura,
                            suma           = suma,
                            data_inc       = data_inc,
                            metoda         = metoda,
                            referinta      = referinta,
                            client_nume    = self._client,
                            numar_factura  = self._numar,
                            user           = self.user,
                            deschide_automat = True,
                        )
                    except Exception as e:
                        QMessageBox.warning(self, "Eroare chitanta", str(e))

            elif metoda == "card":
                QMessageBox.information(
                    self, "Plata card inregistrata",
                    f"Incasare de {suma:,.2f} RON inregistrata!\n\n"
                    f"Nr. tranzactie POS: {referinta}\n\n"
                    "⚠️  Nu uitati sa tipariti bonul de la terminalul POS!"
                )

            elif metoda == "op":
                QMessageBox.information(
                    self, "Transfer bancar inregistrat",
                    f"Incasare de {suma:,.2f} RON inregistrata!\n"
                    f"Referinta OP: {referinta or '—'}"
                )

            self.accept()

        except Exception as e:
            con.rollback()
            QMessageBox.critical(self, "Eroare", f"Nu am putut salva: {e}")
        finally:
            con.close()