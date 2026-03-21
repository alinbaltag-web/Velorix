"""
PATCH pentru page_rapoarte.py
==============================
Adauga tab-ul "💼 Export Contabil" in PageRapoarte.

INSTRUCTIUNI DE INTEGRARE:
  1. Copiaza fisierul export_contabil.py in folderul principal al proiectului
     (langa database.py si main.py)

  2. In page_rapoarte.py, la inceputul fisierului, dupa ultimul import adauga:
     ──────────────────────────────────────────────────────
     from ui.widgets.tab_export_contabil import TabExportContabil
     ──────────────────────────────────────────────────────

  3. In __init__ din PageRapoarte, dupa linia:
         self.tab_rvehicul  = QWidget()
     adauga:
     ──────────────────────────────────────────────────────
         self.tab_export = TabExportContabil(self)
     ──────────────────────────────────────────────────────

  4. In __init__, dupa linia:
         self.tabs.addTab(self.tab_rvehicul,  "🏍️ Raport vehicul")
     adauga:
     ──────────────────────────────────────────────────────
         self.tabs.addTab(self.tab_export, "💼 Export Contabil")
     ──────────────────────────────────────────────────────

  5. Pune acest fisier (tab_export_contabil.py) in:
         ui/widgets/tab_export_contabil.py
"""

import os
import subprocess
import platform
from datetime import datetime, date

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDateEdit, QComboBox, QGroupBox,
    QCheckBox, QFileDialog, QProgressBar, QFrame,
    QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from ui.utils_toast import show_toast


# ─── Thread export (nu blocheaza UI-ul) ──────────────────────
class ExportThread(QThread):
    finished  = pyqtSignal(list)   # lista fisiere generate
    error     = pyqtSignal(str)

    def __init__(self, data_start, data_end, formate, output_dir):
        super().__init__()
        self.data_start  = data_start
        self.data_end    = data_end
        self.formate     = formate
        self.output_dir  = output_dir

    def run(self):
        try:
            from ui.export_contabil import export_csv, export_excel, export_pdf
            ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
            gen = []

            if "CSV" in self.formate:
                fisiere = export_csv(
                    self.data_start, self.data_end,
                    self.output_dir
                )
                gen.extend(fisiere)

            if "Excel" in self.formate:
                path = os.path.join(
                    self.output_dir,
                    f"export_contabil_{ts}.xlsx"
                )
                export_excel(self.data_start, self.data_end, path)
                gen.append(path)

            if "PDF" in self.formate:
                path = os.path.join(
                    self.output_dir,
                    f"export_contabil_{ts}.pdf"
                )
                export_pdf(self.data_start, self.data_end, path)
                gen.append(path)

            self.finished.emit(gen)
        except Exception as e:
            import traceback
            self.error.emit(traceback.format_exc())


# ─── Widget principal ─────────────────────────────────────────
class TabExportContabil(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_page = parent
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Titlu ──
        lbl = QLabel("💼 Export Contabil")
        lbl.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #0d1f3c;"
        )
        root.addWidget(lbl)

        sub = QLabel(
            "Genereaza exporturi pentru contabil in formatele selectate. "
            "Fisierele contin: devize emise, centralizator TVA, "
            "venituri manopera vs piese, situatie clienti si rezumat lunar."
        )
        sub.setStyleSheet("font-size: 12px; color: #7a8ba0;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        # ── Separator ──
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #dce4ef;")
        root.addWidget(line)

        # ── Rand filtre ──
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Perioada rapida
        grp_rapid = QGroupBox("Perioada rapida")
        grp_rapid.setStyleSheet(self._grp_style())
        lay_rap = QHBoxLayout(grp_rapid)
        self.cmb_rapid = QComboBox()
        self.cmb_rapid.addItems([
            "Luna curenta", "Luna trecuta",
            "Trimestrul curent", "Ultimele 6 luni",
            "Anul curent", "Personalizat"
        ])
        self.cmb_rapid.currentIndexChanged.connect(self._on_rapid_changed)
        lay_rap.addWidget(self.cmb_rapid)
        row1.addWidget(grp_rapid)

        # Interval personalizat
        grp_date = QGroupBox("Interval personalizat")
        grp_date.setStyleSheet(self._grp_style())
        lay_dat = QHBoxLayout(grp_date)

        lay_dat.addWidget(QLabel("De la:"))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_start.setFixedWidth(110)
        lay_dat.addWidget(self.date_start)

        lay_dat.addWidget(QLabel("Pana la:"))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("dd.MM.yyyy")
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setFixedWidth(110)
        lay_dat.addWidget(self.date_end)

        row1.addWidget(grp_date)
        row1.addStretch()
        root.addLayout(row1)

        # ── Formate ──
        grp_fmt = QGroupBox("Formate export")
        grp_fmt.setStyleSheet(self._grp_style())
        lay_fmt = QHBoxLayout(grp_fmt)
        lay_fmt.setSpacing(24)

        self.chk_csv   = QCheckBox("📄 CSV  (Saga / WinMentor)")
        self.chk_xlsx  = QCheckBox("📊 Excel (.xlsx)")
        self.chk_pdf   = QCheckBox("🖨️ PDF")

        self.chk_csv.setChecked(True)
        self.chk_xlsx.setChecked(True)
        self.chk_pdf.setChecked(True)

        for chk in [self.chk_csv, self.chk_xlsx, self.chk_pdf]:
            chk.setStyleSheet("font-size: 13px; font-weight: 500;")
            lay_fmt.addWidget(chk)
        lay_fmt.addStretch()
        root.addWidget(grp_fmt)

        # ── Director output ──
        grp_dir = QGroupBox("Director salvare")
        grp_dir.setStyleSheet(self._grp_style())
        lay_dir = QHBoxLayout(grp_dir)

        self.lbl_dir = QLabel(os.path.expanduser("~/Desktop"))
        self.lbl_dir.setStyleSheet(
            "font-size: 11px; color: #1a2535; "
            "background: #f0f4f8; border-radius: 6px; padding: 4px 10px;"
        )
        self.lbl_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay_dir.addWidget(self.lbl_dir)

        btn_dir = QPushButton("📁 Alege...")
        btn_dir.setFixedWidth(100)
        btn_dir.clicked.connect(self._choose_dir)
        btn_dir.setStyleSheet("""
            QPushButton {
                background: #f0f4f8; border: 1.5px solid #dce4ef;
                border-radius: 6px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background: #dce4ef; }
        """)
        lay_dir.addWidget(btn_dir)
        root.addWidget(grp_dir)

        # ── Progres ──
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # indeterminate
        self.progress.setVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none; border-radius: 3px;
                background: #f0f4f8;
            }
            QProgressBar::chunk {
                background: #1a73e8; border-radius: 3px;
            }
        """)
        root.addWidget(self.progress)

        # ── Butoane actiune ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_export = QPushButton("⬇️  Genereaza Export")
        self.btn_export.setMinimumHeight(44)
        self.btn_export.setMinimumWidth(200)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1a73e8, stop:1 #0d5abf);
                color: white; border: none; border-radius: 10px;
                font-size: 14px; font-weight: 700;
            }
            QPushButton:hover { background: #2b82f5; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        self.btn_export.clicked.connect(self._do_export)
        btn_row.addWidget(self.btn_export)

        self.btn_open_dir = QPushButton("📂 Deschide folder")
        self.btn_open_dir.setMinimumHeight(44)
        self.btn_open_dir.setStyleSheet("""
            QPushButton {
                background: #f0f4f8; color: #1a2535;
                border: 1.5px solid #dce4ef; border-radius: 10px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #dce4ef; }
        """)
        self.btn_open_dir.clicked.connect(self._open_dir)
        btn_row.addWidget(self.btn_open_dir)
        btn_row.addStretch()

        root.addLayout(btn_row)

        # ── Card info ──
        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        lay_info = QVBoxLayout(info)
        lay_info.setContentsMargins(14, 10, 14, 10)
        lay_info.setSpacing(4)

        lay_info.addWidget(QLabel(
            "<b>📋 Ce contine exportul:</b>"
        ))
        for item in [
            "① Devize emise — numar, data, client, vehicul, baza impozabila, TVA, total",
            "② Centralizator TVA lunar — baza manopera, baza piese, TVA colectat",
            "③ Venituri manopera vs piese — detaliat per deviz",
            "④ Situatie incasari pe client — total per client in perioada",
            "⑤ Raport lunar rezumat — numar devize si totale per luna",
        ]:
            lbl_item = QLabel(f"  {item}")
            lbl_item.setStyleSheet("font-size: 11px; color: #1e3a5f;")
            lay_info.addWidget(lbl_item)

        root.addWidget(info)
        root.addStretch()

        # Init interval
        self._on_rapid_changed(0)

    # ─── Helpers ──────────────────────────────────────────────
    def _grp_style(self):
        return """
            QGroupBox {
                font-size: 11px; font-weight: 600;
                color: #7a8ba0; border: 1.5px solid #dce4ef;
                border-radius: 8px; margin-top: 8px; padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 4px;
            }
        """

    def _on_rapid_changed(self, idx):
        azi = date.today()
        custom = (self.cmb_rapid.currentText() == "Personalizat")
        self.date_start.setEnabled(custom)
        self.date_end.setEnabled(custom)

        if self.cmb_rapid.currentText() == "Luna curenta":
            start = azi.replace(day=1)
            end   = azi
        elif self.cmb_rapid.currentText() == "Luna trecuta":
            if azi.month == 1:
                start = date(azi.year-1, 12, 1)
                end   = date(azi.year-1, 12, 31)
            else:
                import calendar
                start = date(azi.year, azi.month-1, 1)
                last  = calendar.monthrange(azi.year, azi.month-1)[1]
                end   = date(azi.year, azi.month-1, last)
        elif self.cmb_rapid.currentText() == "Trimestrul curent":
            q = (azi.month - 1) // 3
            start = date(azi.year, q*3+1, 1)
            end   = azi
        elif self.cmb_rapid.currentText() == "Ultimele 6 luni":
            m = azi.month - 6
            y = azi.year
            if m <= 0:
                m += 12; y -= 1
            start = date(y, m, 1)
            end   = azi
        elif self.cmb_rapid.currentText() == "Anul curent":
            start = date(azi.year, 1, 1)
            end   = azi
        else:
            return

        self.date_start.setDate(QDate(start.year, start.month, start.day))
        self.date_end.setDate(QDate(end.year, end.month, end.day))

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Alege directorul de salvare",
            self.lbl_dir.text()
        )
        if d:
            self.lbl_dir.setText(d)

    def _open_dir(self):
        path = self.lbl_dir.text()
        if not os.path.exists(path):
            show_toast(self.parent_page.parent, "Directorul nu exista.")
            return
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    def _get_formate(self):
        formate = []
        if self.chk_csv.isChecked():   formate.append("CSV")
        if self.chk_xlsx.isChecked():  formate.append("Excel")
        if self.chk_pdf.isChecked():   formate.append("PDF")
        return formate

    # ─── Export ───────────────────────────────────────────────
    def _do_export(self):
        formate = self._get_formate()
        if not formate:
            show_toast(self.parent_page.parent,
                       "Selecteaza cel putin un format de export!")
            return

        output_dir = self.lbl_dir.text()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.warning(self, "Eroare",
                                    f"Nu pot crea directorul:\n{e}")
                return

        data_start = self.date_start.date().toString("yyyy-MM-dd")
        data_end   = self.date_end.date().toString("yyyy-MM-dd")

        if data_start > data_end:
            show_toast(self.parent_page.parent,
                       "Data de start trebuie sa fie inainte de data de sfarsit!")
            return

        # Pornire thread
        self.btn_export.setEnabled(False)
        self.progress.setVisible(True)

        self._thread = ExportThread(
            data_start, data_end, formate, output_dir
        )
        self._thread.finished.connect(self._on_export_done)
        self._thread.error.connect(self._on_export_error)
        self._thread.start()

    def _on_export_done(self, fisiere):
        self.progress.setVisible(False)
        self.btn_export.setEnabled(True)

        if not fisiere:
            show_toast(self.parent_page.parent,
                       "⚠️ Nu exista date in perioada selectata.")
            return

        msg = f"✅ Export generat! {len(fisiere)} fisier(e) salvate in:\n{self.lbl_dir.text()}"
        show_toast(self.parent_page.parent, msg)

        # Deschide automat folderul
        self._open_dir()

    def _on_export_error(self, traceback_str):
        self.progress.setVisible(False)
        self.btn_export.setEnabled(True)
        QMessageBox.critical(
            self, "Eroare la export",
            f"A aparut o eroare:\n\n{traceback_str[:800]}"
        )