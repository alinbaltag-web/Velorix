"""
VELORIX — Dashboard Principal
Calendar saptamanal + KPI-uri + Activitate recenta + Programari azi
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QPushButton, QScrollArea, QMenu, QAction,
    QMessageBox, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QPoint, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QCursor, QLinearGradient
from database import get_connection, log_action
from datetime import datetime, timedelta
from ui.widgets.chart_widgets import BarChartWidget, DonutChartWidget




# ============================================================
# KPI CARD
# ============================================================
class KPICard(QFrame):
    def __init__(self, title, value="0", subtitle="", color="#1A73E8",
                 icon="", parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setMinimumHeight(96)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._color = color
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background: white;
                border-radius: 14px;
                border-left: 5px solid {color};
                border-top: 1px solid #e8edf2;
                border-right: 1px solid #e8edf2;
                border-bottom: 1px solid #e8edf2;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Iconita
        if icon:
            lbl_icon = QLabel(icon)
            lbl_icon.setStyleSheet(f"""
                font-size: 26px;
                background: {color}18;
                border-radius: 10px;
                padding: 6px 8px;
            """)
            lbl_icon.setFixedSize(48, 48)
            lbl_icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_icon)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 11px; color: #6b7280; font-weight: 500;")

        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {color};"
        )

        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setStyleSheet("font-size: 10px; color: #9ca3af;")

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_value)
        text_layout.addWidget(self.lbl_subtitle)
        layout.addLayout(text_layout)

    def set_value(self, value):
        self.lbl_value.setText(str(value))

    def set_title(self, text):
        self.lbl_title.setText(text)

    def set_subtitle(self, text):
        self.lbl_subtitle.setText(text)


# ============================================================
# CHART PANEL
# ============================================================
class ChartPanel(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 14px;
                border: 1px solid #e8edf2;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(6)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #1e3a5f;"
        )
        self.layout.addWidget(self.lbl_title)

    def set_title(self, text):
        self.lbl_title.setText(text)


# ============================================================
# CELULA ZI DIN CALENDAR
# ============================================================
class CalendarDayCell(QFrame):
    clicked = pyqtSignal(str)

    STATUS_COLORS = {
        "programat": "#3b82f6",
        "confirmat": "#10b981",
        "anulat":    "#ef4444",
        "finalizat": "#6b7280",
    }

    def __init__(self, date_str, is_today=False, parent=None):
        super().__init__(parent)
        self.date_str = date_str
        self.programari = []
        self.is_today = is_today

        self.setMinimumHeight(88)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

    def _update_style(self):
        if self.is_today:
            self.setStyleSheet("""
                QFrame {
                    background: #eff6ff;
                    border-radius: 10px;
                    border: 2px solid #3b82f6;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: white;
                    border-radius: 10px;
                    border: 1px solid #e8edf2;
                }
                QFrame:hover {
                    background: #f8fafc;
                    border: 1px solid #93c5fd;
                }
            """)

    def set_programari(self, programari):
        self.programari = programari
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        padding = 6

        date = QDate.fromString(self.date_str, "yyyy-MM-dd")
        ziua = str(date.day()) if date.isValid() else ""

        font_zi = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font_zi)

        if self.is_today:
            painter.setBrush(QBrush(QColor("#3b82f6")))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(padding, padding, 24, 24)
            painter.setPen(QPen(QColor("white")))
        else:
            painter.setPen(QPen(QColor("#374151")))

        painter.drawText(padding, padding, 24, 24, Qt.AlignCenter, ziua)

        y_offset = padding + 28
        font_prog = QFont("Segoe UI", 8)
        painter.setFont(font_prog)

        for prog in self.programari[:3]:
            if y_offset + 17 > rect.height() - padding:
                break
            status = prog.get("status", "programat")
            culoare = self.STATUS_COLORS.get(status, "#3b82f6")

            bx = padding
            bw = rect.width() - 2 * padding

            painter.setBrush(QBrush(QColor(culoare + "22")))
            painter.setPen(QPen(QColor(culoare)))
            painter.drawRoundedRect(bx, y_offset, bw, 15, 3, 3)

            painter.setPen(QPen(QColor(culoare)))
            ora = prog.get("ora_start", "")
            client = prog.get("client_nume", "")
            text = f"{ora} {client}"
            fm = painter.fontMetrics()
            text_e = fm.elidedText(text, Qt.ElideRight, bw - 6)
            painter.drawText(bx + 3, y_offset, bw - 6, 15,
                             Qt.AlignVCenter | Qt.AlignLeft, text_e)
            y_offset += 17

        if len(self.programari) > 3:
            extra = len(self.programari) - 3
            painter.setPen(QPen(QColor("#6b7280")))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(padding, y_offset, rect.width() - 2 * padding, 13,
                             Qt.AlignLeft | Qt.AlignVCenter, f"+{extra} mai multe")

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.date_str)
        super().mousePressEvent(event)


# ============================================================
# WIDGET CALENDAR SAPTAMANAL
# ============================================================
class CalendarWidget(QFrame):
    programare_added = pyqtSignal()

    ZILE_RO  = ["Lun", "Mar", "Mie", "Joi", "Vin", "Sam", "Dum"]
    LUNI_RO  = ["", "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai",
                "Iunie", "Iulie", "August", "Septembrie", "Octombrie",
                "Noiembrie", "Decembrie"]

    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window

        today = QDate.currentDate()
        self.saptamana_start = today.addDays(-(today.dayOfWeek() - 1))

        self.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 14px;
                border: 1px solid #e8edf2;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)

        # ── Header navigare ──
        header = QHBoxLayout()

        self.btn_prev = QPushButton("‹")
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background: #f1f5f9; border: none;
                border-radius: 14px; font-size: 16px; color: #374151;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        self.btn_prev.clicked.connect(self._prev_week)

        self.lbl_saptamana = QLabel()
        self.lbl_saptamana.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #1e3a5f;"
        )
        self.lbl_saptamana.setAlignment(Qt.AlignCenter)

        self.btn_next = QPushButton("›")
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: #f1f5f9; border: none;
                border-radius: 14px; font-size: 16px; color: #374151;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        self.btn_next.clicked.connect(self._next_week)

        self.btn_azi = QPushButton("Azi")
        self.btn_azi.setFixedHeight(28)
        self.btn_azi.setStyleSheet("""
            QPushButton {
                background: #3b82f6; color: white; border: none;
                border-radius: 6px; padding: 0 10px;
                font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        self.btn_azi.clicked.connect(self._go_to_today)

        self.btn_add = QPushButton("＋ Programare")
        self.btn_add.setFixedHeight(28)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background: #10b981; color: white; border: none;
                border-radius: 6px; padding: 0 10px;
                font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #059669; }
        """)
        self.btn_add.clicked.connect(lambda: self._add_programare(None))

        header.addWidget(self.btn_prev)
        header.addWidget(self.lbl_saptamana, 1)
        header.addWidget(self.btn_next)
        header.addSpacing(8)
        header.addWidget(self.btn_azi)
        header.addSpacing(4)
        header.addWidget(self.btn_add)
        main_layout.addLayout(header)

        # ── Header zile ──
        self.header_labels = []
        header_zile = QHBoxLayout()
        header_zile.setSpacing(6)
        for zi in self.ZILE_RO:
            lbl = QLabel(zi)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #6b7280; padding: 2px 0;"
            )
            header_zile.addWidget(lbl)
            self.header_labels.append(lbl)
        main_layout.addLayout(header_zile)

        # ── Grid 7 zile ──
        self.grid_layout = QHBoxLayout()
        self.grid_layout.setSpacing(6)
        self.day_cells = []
        for i in range(7):
            cell = CalendarDayCell("", parent=self)
            cell.clicked.connect(self._on_day_clicked)
            self.grid_layout.addWidget(cell)
            self.day_cells.append(cell)
        main_layout.addLayout(self.grid_layout)

        # ── Legenda ──
        legenda = QHBoxLayout()
        legenda.addStretch()
        for status, culoare in CalendarDayCell.STATUS_COLORS.items():
            dot = QLabel(f"● {status.capitalize()}")
            dot.setStyleSheet(f"font-size: 10px; color: {culoare};")
            legenda.addWidget(dot)
            legenda.addSpacing(8)
        main_layout.addLayout(legenda)

        self._refresh()

    # ─────────────────────────────────────────
    def _prev_week(self):
        self.saptamana_start = self.saptamana_start.addDays(-7)
        self._refresh()

    def _next_week(self):
        self.saptamana_start = self.saptamana_start.addDays(7)
        self._refresh()

    def _go_to_today(self):
        today = QDate.currentDate()
        self.saptamana_start = today.addDays(-(today.dayOfWeek() - 1))
        self._refresh()

    # ─────────────────────────────────────────
    def _refresh(self):
        today = QDate.currentDate().toString("yyyy-MM-dd")
        sfarsit = self.saptamana_start.addDays(6)

        luna_start = self.LUNI_RO[self.saptamana_start.month()]
        luna_sf    = self.LUNI_RO[sfarsit.month()]
        an         = self.saptamana_start.year()

        if self.saptamana_start.month() == sfarsit.month():
            titlu = f"{self.saptamana_start.day()} – {sfarsit.day()} {luna_start} {an}"
        else:
            titlu = (f"{self.saptamana_start.day()} {luna_start} – "
                     f"{sfarsit.day()} {luna_sf} {an}")
        self.lbl_saptamana.setText(titlu)

        start_str   = self.saptamana_start.toString("yyyy-MM-dd")
        sfarsit_str = sfarsit.toString("yyyy-MM-dd")

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT p.id, p.id_client, p.id_vehicul, p.data_programare,
                   p.ora_start, p.ora_sfarsit, p.descriere, p.status,
                   p.observatii,
                   COALESCE(c.nume, p.nume_ocazional, '?') as client_nume,
                   COALESCE(v.marca, '') as marca,
                   COALESCE(v.model, '') as model,
                   COALESCE(v.nr, p.vehicul_ocazional, '') as nr
            FROM programari p
            LEFT JOIN clienti c ON p.id_client = c.id
            LEFT JOIN vehicule v ON p.id_vehicul = v.id
            WHERE p.data_programare BETWEEN ? AND ?
            ORDER BY p.ora_start
        """, (start_str, sfarsit_str))
        rows = con.cursor().fetchall() if False else cur.fetchall()
        con.close()

        prog_per_zi = {}
        for row in rows:
            data = row[3]
            if data not in prog_per_zi:
                prog_per_zi[data] = []
            prog_per_zi[data].append({
                "id":              row[0],
                "id_client":       row[1],
                "id_vehicul":      row[2],
                "data_programare": row[3],
                "ora_start":       row[4],
                "ora_sfarsit":     row[5],
                "descriere":       row[6],
                "status":          row[7],
                "observatii":      row[8],
                "client_nume":     row[9] or "",
                "marca":           row[10] or "",
                "model":           row[11] or "",
                "nr":              row[12] or "",
            })

        today_qdate = QDate.currentDate()
        for i, cell in enumerate(self.day_cells):
            data_zi  = self.saptamana_start.addDays(i)
            data_str = data_zi.toString("yyyy-MM-dd")

            cell.date_str = data_str
            cell.is_today = (data_str == today)
            cell._update_style()
            cell.set_programari(prog_per_zi.get(data_str, []))

            # Actualizam header-ul zilei cu data
            if i < len(self.header_labels):
                zi_name = self.ZILE_RO[i]
                if data_zi == today_qdate:
                    self.header_labels[i].setStyleSheet(
                        "font-size: 11px; font-weight: 700; color: #3b82f6; padding: 2px 0;"
                    )
                else:
                    self.header_labels[i].setStyleSheet(
                        "font-size: 11px; font-weight: 600; color: #6b7280; padding: 2px 0;"
                    )
                self.header_labels[i].setText(f"{zi_name}\n{data_zi.day()}")

    # ─────────────────────────────────────────
    def _on_day_clicked(self, date_str):
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT p.id, p.ora_start, p.ora_sfarsit, p.descriere, p.status,
                   COALESCE(c.nume, p.nume_ocazional, '?') as client_nume,
                   COALESCE(v.marca, '') as marca,
                   COALESCE(v.model, '') as model,
                   COALESCE(v.nr, p.vehicul_ocazional, '') as nr
            FROM programari p
            LEFT JOIN clienti c ON p.id_client = c.id
            LEFT JOIN vehicule v ON p.id_vehicul = v.id
            WHERE p.data_programare = ?
            ORDER BY p.ora_start
        """, (date_str,))
        rows = cur.fetchall()
        con.close()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white; border: 1px solid #e2e8f0;
                border-radius: 8px; padding: 4px;
            }
            QMenu::item { padding: 6px 16px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background: #eff6ff; color: #1e3a5f; }
            QMenu::separator { height: 1px; background: #e2e8f0; margin: 4px 8px; }
        """)

        data_qdate = QDate.fromString(date_str, "yyyy-MM-dd")
        luni = self.LUNI_RO
        zile = ["Luni", "Marti", "Miercuri", "Joi", "Vineri", "Sambata", "Duminica"]
        titlu_data = f"{zile[data_qdate.dayOfWeek()-1]}, {data_qdate.day()} {luni[data_qdate.month()]}"

        act_titlu = QAction(titlu_data, self)
        act_titlu.setEnabled(False)
        f = act_titlu.font(); f.setBold(True); act_titlu.setFont(f)
        menu.addAction(act_titlu)
        menu.addSeparator()

        act_add = QAction("＋ Adauga programare", self)
        act_add.triggered.connect(lambda: self._add_programare(date_str))
        menu.addAction(act_add)

        if rows:
            menu.addSeparator()
            for row in rows:
                id_p, ora_s, ora_sf, descr, status, client, marca, model, nr = row
                vehicul = f"{marca or ''} {model or ''}".strip()
                if nr: vehicul += f" ({nr})"
                label = f"{ora_s}–{ora_sf}  {client or '?'}  {vehicul}"

                act_prog = QAction(f"● {label}", self)
                submenu = QMenu(self)
                submenu.setStyleSheet(menu.styleSheet())

                act_edit = QAction("✏️ Editeaza", self)
                act_edit.triggered.connect(lambda checked, pid=id_p: self._edit_programare(pid))
                submenu.addAction(act_edit)

                act_del = QAction("🗑️ Sterge", self)
                act_del.triggered.connect(lambda checked, pid=id_p: self._delete_programare(pid))
                submenu.addAction(act_del)

                act_prog.setMenu(submenu)
                menu.addAction(act_prog)

        menu.exec_(QCursor.pos())

    # ─────────────────────────────────────────
    def _add_programare(self, date_str):
        from ui.dialogs.dialog_programare import DialogProgramare
        dialog = DialogProgramare(self, data_initiala=date_str)
        if dialog.exec_() != DialogProgramare.Accepted:
            return

        d = dialog.get_data()
        con = get_connection()
        cur = con.cursor()

        for sql_col in [
            "ALTER TABLE programari ADD COLUMN nume_ocazional TEXT DEFAULT ''",
            "ALTER TABLE programari ADD COLUMN tel_ocazional TEXT DEFAULT ''",
            "ALTER TABLE programari ADD COLUMN vehicul_ocazional TEXT DEFAULT ''",
        ]:
            try: cur.execute(sql_col)
            except Exception: pass

        try:
            cur.execute("""
                INSERT INTO programari
                    (id_client, id_vehicul, data_programare, ora_start,
                     ora_sfarsit, descriere, status, observatii, created_by,
                     nume_ocazional, tel_ocazional, vehicul_ocazional)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d["id_client"], d["id_vehicul"], d["data_programare"],
                d["ora_start"], d["ora_sfarsit"], d["descriere"],
                d["status"], d["observatii"],
                self.parent_window.logged_email,
                d.get("nume_ocazional", ""),
                d.get("tel_ocazional", ""),
                d.get("vehicul_ocazional", ""),
            ))
            con.commit()
        except Exception as e:
            con.rollback()
            from ui.utils_toast import show_toast
            show_toast(self.parent_window, f"Eroare salvare: {e}")
            con.close()
            return
        con.close()

        log_action(self.parent_window.logged_email, "Adaugare programare",
                   f"{d['data_programare']} {d['ora_start']}")
        self._refresh()
        self.programare_added.emit()

    # ─────────────────────────────────────────
    def _edit_programare(self, programare_id):
        from ui.dialogs.dialog_programare import DialogProgramare
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT id_client, id_vehicul, data_programare, ora_start,
                   ora_sfarsit, descriere, status, observatii,
                   COALESCE(nume_ocazional,''), COALESCE(tel_ocazional,''),
                   COALESCE(vehicul_ocazional,'')
            FROM programari WHERE id=?
        """, (programare_id,))
        row = cur.fetchone()
        con.close()
        if not row: return

        programare_data = {
            "id_client": row[0], "id_vehicul": row[1],
            "data_programare": row[2], "ora_start": row[3],
            "ora_sfarsit": row[4], "descriere": row[5],
            "status": row[6], "observatii": row[7],
            "nume_ocazional": row[8], "tel_ocazional": row[9],
            "vehicul_ocazional": row[10],
        }

        dialog = DialogProgramare(self, programare_data=programare_data)
        if dialog.exec_() != DialogProgramare.Accepted:
            return

        d = dialog.get_data()
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            UPDATE programari SET
                id_client=?, id_vehicul=?, data_programare=?,
                ora_start=?, ora_sfarsit=?, descriere=?, status=?,
                observatii=?, nume_ocazional=?, tel_ocazional=?,
                vehicul_ocazional=?
            WHERE id=?
        """, (
            d["id_client"], d["id_vehicul"], d["data_programare"],
            d["ora_start"], d["ora_sfarsit"], d["descriere"],
            d["status"], d["observatii"],
            d.get("nume_ocazional", ""), d.get("tel_ocazional", ""),
            d.get("vehicul_ocazional", ""), programare_id
        ))
        con.commit()
        con.close()
        log_action(self.parent_window.logged_email, "Editare programare", f"ID={programare_id}")
        self._refresh()
        self.programare_added.emit()

    # ─────────────────────────────────────────
    def _delete_programare(self, programare_id):
        rasp = QMessageBox.question(self, "Confirmare",
                                    "Stergi aceasta programare?",
                                    QMessageBox.Yes | QMessageBox.No)
        if rasp != QMessageBox.Yes: return
        con = get_connection()
        cur = con.cursor()
        cur.execute("DELETE FROM programari WHERE id=?", (programare_id,))
        con.commit()
        con.close()
        log_action(self.parent_window.logged_email, "Stergere programare", f"ID={programare_id}")
        self._refresh()
        self.programare_added.emit()

    def refresh(self):
        self._refresh()


# ============================================================
# PANEL PROGRAMARI AZI
# ============================================================
class ProgramariAziPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 14px;
                border: 1px solid #e8edf2;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.lbl_title = QLabel("📅 Programari azi")
        self.lbl_title.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #1e3a5f;"
        )
        self.lbl_count = QLabel("0")
        self.lbl_count.setStyleSheet("""
            font-size: 10px; font-weight: 700; color: white;
            background: #3b82f6; border-radius: 8px;
            padding: 1px 7px;
        """)
        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_count)
        layout.addLayout(header)

        # Scroll area pentru lista programarilor
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(4)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def refresh(self):
        # Curata
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = datetime.now().strftime("%Y-%m-%d")
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT p.ora_start, p.ora_sfarsit,
                   COALESCE(c.nume, p.nume_ocazional, '—') as client,
                   COALESCE(v.marca||' '||v.model, p.vehicul_ocazional, '—') as vehicul,
                   p.descriere, p.status
            FROM programari p
            LEFT JOIN clienti c ON p.id_client = c.id
            LEFT JOIN vehicule v ON p.id_vehicul = v.id
            WHERE p.data_programare = ?
            ORDER BY p.ora_start
        """, (today,))
        rows = cur.fetchall()
        con.close()

        self.lbl_count.setText(str(len(rows)))

        STATUS_BG = {
            "programat": "#eff6ff", "confirmat": "#f0fdf4",
            "anulat":    "#fef2f2", "finalizat": "#f9fafb",
        }
        STATUS_COLOR = {
            "programat": "#3b82f6", "confirmat": "#10b981",
            "anulat":    "#ef4444", "finalizat": "#6b7280",
        }

        if not rows:
            lbl = QLabel("Nicio programare pentru azi")
            lbl.setStyleSheet(
                "font-size: 11px; color: #9ca3af; padding: 8px 4px;"
            )
            lbl.setAlignment(Qt.AlignCenter)
            self.container_layout.insertWidget(0, lbl)
            return

        for i, (ora_s, ora_sf, client, vehicul, descr, status) in enumerate(rows):
            card = QFrame()
            status = status or "programat"
            bg    = STATUS_BG.get(status, "#eff6ff")
            color = STATUS_COLOR.get(status, "#3b82f6")
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg};
                    border-radius: 8px;
                    border-left: 3px solid {color};
                }}
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.setSpacing(8)

            lbl_ora = QLabel(f"{ora_s}")
            lbl_ora.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {color};")
            lbl_ora.setFixedWidth(36)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(0)
            lbl_client = QLabel(client.strip())
            lbl_client.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #1e3a5f;"
            )
            vehicul_clean = vehicul.strip().replace("None", "").replace("  ", " ")
            lbl_vehicul = QLabel(vehicul_clean or "—")
            lbl_vehicul.setStyleSheet("font-size: 10px; color: #6b7280;")
            info_layout.addWidget(lbl_client)
            info_layout.addWidget(lbl_vehicul)

            if descr:
                lbl_descr = QLabel(descr)
                lbl_descr.setStyleSheet("font-size: 10px; color: #9ca3af;")
                info_layout.addWidget(lbl_descr)

            card_layout.addWidget(lbl_ora)
            card_layout.addLayout(info_layout)
            card_layout.addStretch()

            self.container_layout.insertWidget(i, card)


# ============================================================
# PANEL ACTIVITATE RECENTA
# ============================================================
class ActivitateRecentaPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 14px;
                border: 1px solid #e8edf2;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.lbl_title = QLabel("🕐 Activitate recenta")
        self.lbl_title.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #1e3a5f;"
        )
        layout.addWidget(self.lbl_title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(3)
        self.container_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def refresh(self):
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT d.numar, d.data, c.nume,
                   v.marca || ' ' || COALESCE(v.model, '') as vehicul,
                   d.total_general
            FROM devize d
            LEFT JOIN clienti c ON c.id = d.id_client
            LEFT JOIN vehicule v ON v.id = d.id_vehicul
            ORDER BY d.id DESC LIMIT 6
        """)
        rows = cur.fetchall()
        con.close()

        if not rows:
            lbl = QLabel("Niciun deviz inca")
            lbl.setStyleSheet("font-size: 11px; color: #9ca3af; padding: 8px 4px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.container_layout.insertWidget(0, lbl)
            return

        for i, (numar, data, client, vehicul, total) in enumerate(rows):
            row_widget = QFrame()
            row_widget.setStyleSheet("""
                QFrame {
                    background: #f8fafc;
                    border-radius: 6px;
                }
                QFrame:hover { background: #eff6ff; }
            """)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 5, 8, 5)
            row_layout.setSpacing(6)

            lbl_nr = QLabel(numar or "—")
            lbl_nr.setStyleSheet(
                "font-size: 10px; font-weight: 700; color: #1A73E8; min-width: 80px;"
            )

            lbl_client = QLabel(f"{client or '—'} · {(vehicul or '').strip()}")
            lbl_client.setStyleSheet("font-size: 10px; color: #374151;")
            lbl_client.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            lbl_total = QLabel(f"{float(total or 0):,.0f} RON")
            lbl_total.setStyleSheet(
                "font-size: 10px; font-weight: 600; color: #10b981; min-width: 70px;"
            )
            lbl_total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            lbl_data = QLabel(data or "")
            lbl_data.setStyleSheet("font-size: 10px; color: #9ca3af; min-width: 55px;")
            lbl_data.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row_layout.addWidget(lbl_nr)
            row_layout.addWidget(lbl_client)
            row_layout.addWidget(lbl_total)
            row_layout.addWidget(lbl_data)

            self.container_layout.insertWidget(i, row_widget)


# ============================================================
# PAGINA DASHBOARD
# ============================================================
class PageDashboard(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # ── Header cu titlu si data ──
        header_row = QHBoxLayout()
        self.title = QLabel("Panou principal")
        self.title.setObjectName("pageTitle")

        self.lbl_data_ora = QLabel()
        self.lbl_data_ora.setStyleSheet("font-size: 12px; color: #9ca3af;")
        self.lbl_data_ora.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._update_clock()

        self.timer_ceas = QTimer(self)
        self.timer_ceas.timeout.connect(self._update_clock)
        self.timer_ceas.start(60000)  # actualizare la fiecare minut

        header_row.addWidget(self.title)
        header_row.addStretch()
        header_row.addWidget(self.lbl_data_ora)
        main_layout.addLayout(header_row)

        # ── Randul KPI (6 carduri) ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        self.card_venituri    = KPICard("Venituri luna",    "0 RON",  "", "#1A73E8",  "💰")
        self.card_in_lucru    = KPICard("Lucrari in curs",  "0",      "", "#f59e0b",  "🔧")
        self.card_devize_luna = KPICard("Devize luna",      "0",      "", "#10b981",  "📄")
        self.card_clienti     = KPICard("Clienti totali",   "0",      "", "#8b5cf6",  "👥")
        self.card_programari  = KPICard("Programari azi",   "0",      "", "#3b82f6",  "📅")
        self.card_stoc_critic = KPICard("Stoc critic",      "0",      "", "#ef4444",  "⚠️")

        for card in [self.card_venituri, self.card_in_lucru, self.card_devize_luna,
                     self.card_clienti, self.card_programari, self.card_stoc_critic]:
            kpi_row.addWidget(card)

        main_layout.addLayout(kpi_row)

        # ── Randul principal: Calendar + Programari azi ──
        calendar_row = QHBoxLayout()
        calendar_row.setSpacing(12)

        self.calendar = CalendarWidget(parent_window=self.parent)
        self.calendar.setMinimumHeight(230)
        self.calendar.setMaximumHeight(270)
        self.calendar.programare_added.connect(self.refresh_dashboard)

        self.panel_programari_azi = ProgramariAziPanel()
        self.panel_programari_azi.setFixedWidth(240)
        self.panel_programari_azi.setMinimumHeight(230)
        self.panel_programari_azi.setMaximumHeight(270)

        calendar_row.addWidget(self.calendar, 1)
        calendar_row.addWidget(self.panel_programari_azi)
        main_layout.addLayout(calendar_row)

        # ── Randul de jos: Grafice + Activitate recenta ──
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        # Grafic bare venituri
        self.panel_venituri = ChartPanel("Venituri – ultimele 6 luni")
        self.panel_venituri.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.bar_chart = BarChartWidget()
        self.panel_venituri.layout.addWidget(self.bar_chart)

        bottom_row.addWidget(self.panel_venituri, 5)

        # Coloana dreapta: Pie + Activitate
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        self.panel_status = ChartPanel("Status lucrari")
        self.panel_status.setFixedWidth(220)

        self.pie_widget = DonutChartWidget()
        self.panel_status.layout.addWidget(self.pie_widget)
        self.lbl_legend = QLabel()
        self.lbl_legend.setAlignment(Qt.AlignCenter)
        self.lbl_legend.setStyleSheet("font-size: 10px; color: #374151;")
        self.panel_status.layout.addWidget(self.lbl_legend)


        right_col.addWidget(self.panel_status)

        self.panel_activitate = ActivitateRecentaPanel()
        self.panel_activitate.setFixedWidth(220)
        right_col.addWidget(self.panel_activitate, 1)

        bottom_row.addLayout(right_col)
        main_layout.addLayout(bottom_row)

        self.refresh_dashboard()
        self.apply_language()

    # ──────────────────────────────────────────────────────────
    def _update_clock(self):
        now = datetime.now()
        ZILE = ["Luni", "Marti", "Miercuri", "Joi", "Vineri", "Sambata", "Duminica"]
        LUNI = ["", "ian", "feb", "mar", "apr", "mai", "iun",
                "iul", "aug", "sep", "oct", "nov", "dec"]
        zi_saptamana = ZILE[now.weekday()]
        text = f"{zi_saptamana}, {now.day} {LUNI[now.month]} {now.year} · {now.strftime('%H:%M')}"
        self.lbl_data_ora.setText(text)

    # ============================================================
    # REFRESH
    # ============================================================
    def refresh_dashboard(self):
        con = get_connection()
        cur = con.cursor()

        luna = datetime.now().strftime("%Y-%m")
        today = datetime.now().strftime("%Y-%m-%d")

        # Venituri luna (total + defalcat)
        cur.execute("""
            SELECT COALESCE(SUM(total_general), 0),
                   COALESCE(SUM(total_manopera), 0),
                   COALESCE(SUM(total_piese), 0),
                   COALESCE(SUM(total_tva), 0)
            FROM devize WHERE strftime('%Y-%m', data) = ?
        """, (luna,))
        row_v = cur.fetchone()
        venituri       = float(row_v[0] or 0)
        venituri_man   = float(row_v[1] or 0)
        venituri_piese = float(row_v[2] or 0)
        venituri_tva   = float(row_v[3] or 0)
        # Distribuim TVA proportional pe manopera si piese
        total_fara_tva = venituri_man + venituri_piese
        if total_fara_tva > 0:
            man_cu_tva   = venituri_man   * venituri / total_fara_tva
            piese_cu_tva = venituri_piese * venituri / total_fara_tva
        else:
            man_cu_tva   = 0.0
            piese_cu_tva = 0.0
        self.card_venituri.set_value(f"{venituri:,.0f} RON")
        self.card_venituri.set_subtitle(
            f"Man: {man_cu_tva:,.0f}  Piese: {piese_cu_tva:,.0f} RON"
        )

        # Lucrari in curs
        cur.execute("SELECT COUNT(*) FROM lucrari WHERE status='in_lucru'")
        in_lucru = cur.fetchone()[0] or 0
        self.card_in_lucru.set_value(str(in_lucru))

        cur.execute("SELECT COUNT(*) FROM lucrari WHERE status='finalizat'")
        finalizate = cur.fetchone()[0] or 0
        self.card_in_lucru.set_subtitle(f"{finalizate} finalizate total")

        # Devize luna
        cur.execute("""
            SELECT COUNT(*) FROM devize WHERE strftime('%Y-%m', data) = ?
        """, (luna,))
        devize_luna = cur.fetchone()[0] or 0
        self.card_devize_luna.set_value(str(devize_luna))
        self.card_devize_luna.set_subtitle(f"luna {luna}")

        # Clienti
        cur.execute("SELECT COUNT(*) FROM clienti")
        clienti = cur.fetchone()[0] or 0
        self.card_clienti.set_value(str(clienti))
        cur.execute("SELECT COUNT(*) FROM vehicule")
        vehicule = cur.fetchone()[0] or 0
        self.card_clienti.set_subtitle(f"{vehicule} vehicule")

        # Programari azi
        cur.execute("""
            SELECT COUNT(*) FROM programari WHERE data_programare = ?
        """, (today,))
        prog_azi = cur.fetchone()[0] or 0
        self.card_programari.set_value(str(prog_azi))
        cur.execute("""
            SELECT COUNT(*) FROM programari
            WHERE data_programare = ? AND status != 'anulat'
        """, (today,))
        prog_active = cur.fetchone()[0] or 0
        self.card_programari.set_subtitle(f"{prog_active} active azi")

        # Stoc critic
        try:
            cur.execute("""
                SELECT COUNT(*) FROM stoc_piese
                WHERE stoc_curent <= stoc_minim AND stoc_curent >= 0
            """)
            stoc_critic = cur.fetchone()[0] or 0
        except Exception:
            stoc_critic = 0
        self.card_stoc_critic.set_value(str(stoc_critic))
        self.card_stoc_critic.set_subtitle(
            "piese sub stoc minim" if stoc_critic > 0 else "stoc OK"
        )

        self._draw_bar_chart(cur)
        self._draw_pie_chart(cur, in_lucru, finalizate)        
        con.close()

        # Refresh panouri
        self.panel_programari_azi.refresh()
        self.panel_activitate.refresh()
        self.calendar.refresh()

    # ──────────────────────────────────────────────────────────
    # GRAFIC BARE
    # ──────────────────────────────────────────────────────────
    def _draw_bar_chart(self, cur):
            valori = []
            etichete = []
            azi = datetime.now()

            for i in range(5, -1, -1):
                luna_dt = (azi.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
                luna_str   = luna_dt.strftime("%Y-%m")
                luna_label = luna_dt.strftime("%b '%y")

                cur.execute("""
                    SELECT COALESCE(SUM(total_general), 0) FROM devize
                    WHERE strftime('%Y-%m', data) = ?
                """, (luna_str,))
                val = float(cur.fetchone()[0] or 0)
                valori.append(val)
                etichete.append(luna_label)

            self.bar_chart.set_data(valori, etichete)
    # ──────────────────────────────────────────────────────────
    # GRAFIC PIE
    # ──────────────────────────────────────────────────────────
    def _draw_pie_chart(self, cur, in_lucru, finalizate):
            segmente = [
                (in_lucru,   "#f59e0b", "In lucru"),
                (finalizate, "#10b981", "Finalizate"),
            ]
            self.pie_widget.set_data(segmente)
            self.lbl_legend.setText(
                f"🟡 In lucru: {in_lucru}   🟢 Finalizate: {finalizate}"
            )
    # ============================================================
    # LIMBA
    # ============================================================
    def apply_language(self):
        lang = self.parent.app_language
        if lang == "RO":
            self.title.setText("Panou principal")
            self.card_venituri.set_title("Venituri luna")
            self.card_in_lucru.set_title("Lucrari in curs")
            self.card_devize_luna.set_title("Devize luna")
            self.card_clienti.set_title("Clienti totali")
            self.card_programari.set_title("Programari azi")
            self.card_stoc_critic.set_title("Stoc critic")
            self.panel_venituri.set_title("Venituri – ultimele 6 luni")
            self.panel_status.set_title("Status lucrari")
            self.panel_programari_azi.lbl_title.setText("📅 Programari azi")
            self.panel_activitate.lbl_title.setText("🕐 Activitate recenta")
        else:
            self.title.setText("Dashboard")
            self.card_venituri.set_title("Monthly revenue")
            self.card_in_lucru.set_title("Active works")
            self.card_devize_luna.set_title("Monthly estimates")
            self.card_clienti.set_title("Total clients")
            self.card_programari.set_title("Appointments today")
            self.card_stoc_critic.set_title("Critical stock")
            self.panel_venituri.set_title("Revenue – last 6 months")
            self.panel_status.set_title("Work status")
            self.panel_programari_azi.lbl_title.setText("📅 Today's appointments")
            self.panel_activitate.lbl_title.setText("🕐 Recent activity")