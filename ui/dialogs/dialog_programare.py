from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QFormLayout,
    QDialogButtonBox, QTimeEdit, QDateEdit, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QTime, QDate
from database import get_connection

CLIENT_OCAZIONAL_ID = -1  # sentinel pentru client nou/ocazional


class DialogProgramare(QDialog):
    def __init__(self, parent=None, data_initiala=None, programare_data=None):
        super().__init__(parent)
        self.setWindowTitle("Programare noua" if not programare_data else "Editeaza programare")
        self.setFixedWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)

        # ── CLIENT ──
        self.cmb_client = QComboBox()
        self.cmb_client.setMinimumHeight(32)
        self.cmb_client.currentIndexChanged.connect(self._on_client_changed)
        form.addRow("Client:", self.cmb_client)

        # ── BLOC CLIENT OCAZIONAL (ascuns implicit) ──
        self.frame_ocazional = QFrame()
        self.frame_ocazional.setStyleSheet(
            "QFrame { background: #fffbeb; border: 1px solid #fcd34d; border-radius: 6px; }"
        )
        ocaz_layout = QFormLayout(self.frame_ocazional)
        ocaz_layout.setContentsMargins(10, 8, 10, 8)
        ocaz_layout.setSpacing(8)

        lbl_info = QLabel("Client ocazional — nu va fi adaugat in baza de date")
        lbl_info.setStyleSheet("font-size: 11px; color: #92400e; font-style: italic;")
        ocaz_layout.addRow(lbl_info)

        self.txt_nume_ocazional = QLineEdit()
        self.txt_nume_ocazional.setPlaceholderText("Nume client *")
        self.txt_nume_ocazional.setMinimumHeight(30)
        ocaz_layout.addRow("Nume:", self.txt_nume_ocazional)

        self.txt_tel_ocazional = QLineEdit()
        self.txt_tel_ocazional.setPlaceholderText("Telefon (optional)")
        self.txt_tel_ocazional.setMinimumHeight(30)
        ocaz_layout.addRow("Telefon:", self.txt_tel_ocazional)

        self.txt_vehicul_ocazional = QLineEdit()
        self.txt_vehicul_ocazional.setPlaceholderText("Ex: Honda CBR 600 | B-123-ABC")
        self.txt_vehicul_ocazional.setMinimumHeight(30)
        ocaz_layout.addRow("Vehicul:", self.txt_vehicul_ocazional)

        self.frame_ocazional.setVisible(False)
        form.addRow(self.frame_ocazional)

        # ── VEHICUL (client existent) ──
        self.cmb_vehicul = QComboBox()
        self.cmb_vehicul.setMinimumHeight(32)
        form.addRow("Vehicul:", self.cmb_vehicul)

        # ── DATA ──
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(32)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        if data_initiala:
            self.date_edit.setDate(QDate.fromString(data_initiala, "yyyy-MM-dd"))
        else:
            self.date_edit.setDate(QDate.currentDate())
        form.addRow("Data:", self.date_edit)

        # ── ORA START / SFARSIT ──
        ora_layout = QHBoxLayout()
        self.time_start = QTimeEdit()
        self.time_start.setDisplayFormat("HH:mm")
        self.time_start.setMinimumHeight(32)
        self.time_start.setTime(QTime(9, 0))
        self.time_start.timeChanged.connect(self._on_time_start_changed)

        self.time_sfarsit = QTimeEdit()
        self.time_sfarsit.setDisplayFormat("HH:mm")
        self.time_sfarsit.setMinimumHeight(32)
        self.time_sfarsit.setTime(QTime(10, 0))

        ora_layout.addWidget(QLabel("De la:"))
        ora_layout.addWidget(self.time_start)
        ora_layout.addSpacing(12)
        ora_layout.addWidget(QLabel("Pana la:"))
        ora_layout.addWidget(self.time_sfarsit)
        form.addRow("Interval:", ora_layout)

        # ── DESCRIERE ──
        self.txt_descriere = QLineEdit()
        self.txt_descriere.setPlaceholderText("Ex: Schimb ulei, revizie, diagnosticare...")
        self.txt_descriere.setMinimumHeight(32)
        form.addRow("Descriere:", self.txt_descriere)

        # ── STATUS ──
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["programat", "confirmat", "anulat", "finalizat"])
        self.cmb_status.setMinimumHeight(32)
        form.addRow("Status:", self.cmb_status)

        # ── OBSERVATII ──
        self.txt_observatii = QTextEdit()
        self.txt_observatii.setPlaceholderText("Observatii suplimentare...")
        self.txt_observatii.setFixedHeight(60)
        form.addRow("Observatii:", self.txt_observatii)

        layout.addLayout(form)

        # ── BUTOANE ──
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("💾 Salveaza")
        buttons.button(QDialogButtonBox.Cancel).setText("Anuleaza")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_clienti()

        if programare_data:
            self._populate(programare_data)

    # =========================================================
    # INCARCARE CLIENTI
    # =========================================================
    def _load_clienti(self):
        self.cmb_client.blockSignals(True)
        self.cmb_client.clear()
        self.cmb_client.addItem("— Selecteaza client —", None)
        self.cmb_client.addItem("➕ Client nou / ocazional", CLIENT_OCAZIONAL_ID)

        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT id, nume, telefon FROM clienti ORDER BY nume")
        rows = cur.fetchall()
        con.close()

        for id_c, nume, tel in rows:
            label = nume
            if tel:
                label += f" ({tel})"
            self.cmb_client.addItem(label, id_c)

        self.cmb_client.blockSignals(False)

    # =========================================================
    # LA SCHIMBARE CLIENT
    # =========================================================
    def _on_client_changed(self, index):
        id_client = self.cmb_client.currentData()

        # Client ocazional
        if id_client == CLIENT_OCAZIONAL_ID:
            self.frame_ocazional.setVisible(True)
            self.cmb_vehicul.setVisible(False)
            # Gasim label-ul "Vehicul:" din form si il ascundem
            self._set_vehicul_row_visible(False)
            return

        # Client normal sau niciunul
        self.frame_ocazional.setVisible(False)
        self.cmb_vehicul.setVisible(True)
        self._set_vehicul_row_visible(True)
        self.cmb_vehicul.clear()

        if not id_client:
            self.cmb_vehicul.addItem("— Selecteaza mai intai un client —", None)
            return

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT id, marca, model, nr FROM vehicule
            WHERE id_client = ? ORDER BY marca
        """, (id_client,))
        rows = cur.fetchall()
        con.close()

        if not rows:
            self.cmb_vehicul.addItem("— Niciun vehicul inregistrat —", None)
            return

        for id_v, marca, model, nr in rows:
            label = f"{marca or ''} {model or ''}".strip()
            if nr:
                label += f" | {nr}"
            self.cmb_vehicul.addItem(label, id_v)

    def _set_vehicul_row_visible(self, visible):
        """Ascunde/arata randul Vehicul din QFormLayout."""
        self.cmb_vehicul.setVisible(visible)

    # =========================================================
    # ORA START — ajustare automata ora sfarsit
    # =========================================================
    def _on_time_start_changed(self, time):
        sfarsit = time.addSecs(3600)
        if sfarsit > self.time_sfarsit.time():
            self.time_sfarsit.setTime(sfarsit)

    # =========================================================
    # POPULARE LA EDITARE
    # =========================================================
    def _populate(self, d):
        # Client ocazional salvat cu id_client=None si nume_ocazional prezent
        if d.get("nume_ocazional"):
            # Selectam "Client nou / ocazional"
            for i in range(self.cmb_client.count()):
                if self.cmb_client.itemData(i) == CLIENT_OCAZIONAL_ID:
                    self.cmb_client.setCurrentIndex(i)
                    break
            self.txt_nume_ocazional.setText(d.get("nume_ocazional", ""))
            self.txt_tel_ocazional.setText(d.get("tel_ocazional", ""))
            self.txt_vehicul_ocazional.setText(d.get("vehicul_ocazional", ""))
        else:
            for i in range(self.cmb_client.count()):
                if self.cmb_client.itemData(i) == d.get("id_client"):
                    self.cmb_client.setCurrentIndex(i)
                    break
            for i in range(self.cmb_vehicul.count()):
                if self.cmb_vehicul.itemData(i) == d.get("id_vehicul"):
                    self.cmb_vehicul.setCurrentIndex(i)
                    break

        data_str = d.get("data_programare", "")
        if data_str:
            self.date_edit.setDate(QDate.fromString(data_str, "yyyy-MM-dd"))

        self.time_start.setTime(QTime.fromString(d.get("ora_start", "09:00"), "HH:mm"))
        self.time_sfarsit.setTime(QTime.fromString(d.get("ora_sfarsit", "10:00"), "HH:mm"))
        self.txt_descriere.setText(d.get("descriere", ""))

        idx = self.cmb_status.findText(d.get("status", "programat"))
        if idx >= 0:
            self.cmb_status.setCurrentIndex(idx)

        self.txt_observatii.setPlainText(d.get("observatii", ""))

    # =========================================================
    # VALIDARE + ACCEPT
    # =========================================================
    def _validate_and_accept(self):
        id_client = self.cmb_client.currentData()

        if id_client is None:
            QMessageBox.warning(self, "Eroare", "Selecteaza un client sau alege 'Client nou / ocazional'.")
            return

        if id_client == CLIENT_OCAZIONAL_ID:
            if not self.txt_nume_ocazional.text().strip():
                QMessageBox.warning(self, "Eroare", "Introdu numele clientului ocazional.")
                return
        else:
            if not self.cmb_vehicul.currentData():
                QMessageBox.warning(self, "Eroare", "Selecteaza un vehicul.")
                return

        if self.time_sfarsit.time() <= self.time_start.time():
            QMessageBox.warning(self, "Eroare", "Ora de sfarsit trebuie sa fie dupa ora de start.")
            return

        self.accept()

    # =========================================================
    # GET DATA
    # =========================================================
    def get_data(self):
        id_client = self.cmb_client.currentData()
        ocazional = (id_client == CLIENT_OCAZIONAL_ID)

        return {
            # Pentru client existent
            "id_client":          None if ocazional else id_client,
            "id_vehicul":         None if ocazional else self.cmb_vehicul.currentData(),
            # Pentru client ocazional
            "ocazional":          ocazional,
            "nume_ocazional":     self.txt_nume_ocazional.text().strip() if ocazional else "",
            "tel_ocazional":      self.txt_tel_ocazional.text().strip() if ocazional else "",
            "vehicul_ocazional":  self.txt_vehicul_ocazional.text().strip() if ocazional else "",
            # Comune
            "data_programare":    self.date_edit.date().toString("yyyy-MM-dd"),
            "ora_start":          self.time_start.time().toString("HH:mm"),
            "ora_sfarsit":        self.time_sfarsit.time().toString("HH:mm"),
            "descriere":          self.txt_descriere.text().strip(),
            "status":             self.cmb_status.currentText(),
            "observatii":         self.txt_observatii.toPlainText().strip(),
        }
