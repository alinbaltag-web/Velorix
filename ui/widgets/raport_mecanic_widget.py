"""
RaportMecanicWidget — widget standalone care poate fi adaugat
in orice QTabWidget din page_rapoarte.py.

Utilizare in page_rapoarte.py:
    from ui.widgets.raport_mecanic_widget import RaportMecanicWidget
    self.tab_mecanic = RaportMecanicWidget(self)
    self.tabs.addTab(self.tab_mecanic, "📊 Raport mecanic")
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont
from database import get_connection


class RaportMecanicWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Titlu ──
        lbl = QLabel("📊 Raport activitate mecanici")
        lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #1e3a5f;")
        layout.addWidget(lbl)

        # ── Filtre ──
        filtru_frame = QFrame()
        filtru_frame.setStyleSheet(
            "QFrame { background: #f8fafc; border: 1px solid #e2e8f0; "
            "border-radius: 8px; }"
        )
        filtru_layout = QHBoxLayout(filtru_frame)
        filtru_layout.setContentsMargins(12, 8, 12, 8)
        filtru_layout.setSpacing(12)

        filtru_layout.addWidget(QLabel("Perioada:"))

        self.date_de_la = QDateEdit()
        self.date_de_la.setCalendarPopup(True)
        self.date_de_la.setDisplayFormat("dd.MM.yyyy")
        self.date_de_la.setDate(QDate.currentDate().addMonths(-1))
        self.date_de_la.setMinimumWidth(110)
        filtru_layout.addWidget(self.date_de_la)

        filtru_layout.addWidget(QLabel("—"))

        self.date_pana_la = QDateEdit()
        self.date_pana_la.setCalendarPopup(True)
        self.date_pana_la.setDisplayFormat("dd.MM.yyyy")
        self.date_pana_la.setDate(QDate.currentDate())
        self.date_pana_la.setMinimumWidth(110)
        filtru_layout.addWidget(self.date_pana_la)

        filtru_layout.addSpacing(16)
        filtru_layout.addWidget(QLabel("Mecanic:"))

        self.cmb_mecanic = QComboBox()
        self.cmb_mecanic.setMinimumWidth(180)
        self.cmb_mecanic.addItem("Toti mecanicii", "")
        self._load_mecanici()
        filtru_layout.addWidget(self.cmb_mecanic)

        filtru_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Actualizeaza")
        self.btn_refresh.setObjectName("primary")
        self.btn_refresh.setMinimumHeight(32)
        self.btn_refresh.clicked.connect(self.refresh)
        filtru_layout.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("📥 Export CSV")
        self.btn_export.setMinimumHeight(32)
        self.btn_export.clicked.connect(self._export_csv)
        filtru_layout.addWidget(self.btn_export)

        layout.addWidget(filtru_frame)

        # ── Tabel sumar ──
        lbl_sumar = QLabel("Sumar pe mecanic")
        lbl_sumar.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        layout.addWidget(lbl_sumar)

        self.table_sumar = QTableWidget()
        self.table_sumar.setFocusPolicy(Qt.NoFocus)
        self.table_sumar.setColumnCount(6)
        self.table_sumar.setHorizontalHeaderLabels([
            "Mecanic", "Nr. lucrari", "Vehicule unice",
            "Ore RAR total", "Valoare manopera (RON)", "Medie ore/lucrare"
        ])
        h = self.table_sumar.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 6):
            h.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table_sumar.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sumar.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_sumar.setAlternatingRowColors(True)
        self.table_sumar.setMaximumHeight(200)
        self.table_sumar.itemSelectionChanged.connect(self._on_sumar_selection)
        layout.addWidget(self.table_sumar)

        # ── Detaliu pe categorii ──
        lbl_det = QLabel("Detaliu lucrari pe categorii")
        lbl_det.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        layout.addWidget(lbl_det)

        self.tree_detaliu = QTreeWidget()
        self.tree_detaliu.setFocusPolicy(Qt.NoFocus)
        self.tree_detaliu.setColumnCount(4)
        self.tree_detaliu.setHeaderLabels([
            "Categorie / Lucrare", "Nr. lucrari", "Ore RAR", "Valoare (RON)"
        ])
        self.tree_detaliu.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_detaliu.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree_detaliu.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree_detaliu.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree_detaliu.setAlternatingRowColors(True)
        layout.addWidget(self.tree_detaliu, stretch=1)

        # ── Footer total ──
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #1e3a5f; "
            "padding: 6px 10px; background: #eff6ff; border-radius: 6px;"
        )
        self.lbl_total.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_total)

    # =========================================================
    # LOAD MECANICI
    # =========================================================
    def _load_mecanici(self):
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute(
                "SELECT username FROM users WHERE role='mecanic' ORDER BY username"
            )
            for (username,) in cur.fetchall():
                self.cmb_mecanic.addItem(username, username)
            con.close()
        except Exception:
            pass

    # =========================================================
    # REFRESH
    # =========================================================
    def refresh(self):
        de_la = self.date_de_la.date().toString("yyyy-MM-dd")
        pana_la = self.date_pana_la.date().toString("yyyy-MM-dd")
        mecanic_filtru = self.cmb_mecanic.currentData()

        con = get_connection()
        cur = con.cursor()

        # ── Migrare coloana mecanic (safe) ──
        try:
            cur.execute("ALTER TABLE lucrari ADD COLUMN mecanic TEXT DEFAULT ''")
            con.commit()
        except Exception:
            pass

        # ── Query sumar ──
        where_mec = "AND l.mecanic = ?" if mecanic_filtru else ""
        params_mec = [de_la, pana_la]
        if mecanic_filtru:
            params_mec.append(mecanic_filtru)

        # Query simplu direct pe lucrari - fara join cu fise_service
        params_simple = []
        where_mec_simple = ""
        if mecanic_filtru:
            where_mec_simple = "AND l.mecanic = ?"
            params_simple.append(mecanic_filtru)

        cur.execute(f"""
            SELECT
                COALESCE(NULLIF(l.mecanic,''), '— Nealocat —') as mecanic,
                COUNT(*) as nr_lucrari,
                COUNT(DISTINCT l.id_vehicul) as vehicule_unice,
                COALESCE(SUM(l.ore_rar), 0) as ore_total,
                COALESCE(SUM(l.cost), 0) as valoare_total
            FROM lucrari l
            WHERE 1=1
            {where_mec_simple}
            GROUP BY mecanic
            ORDER BY valoare_total DESC
        """, params_simple)
        rows_sumar = cur.fetchall()

        con.close()

        # ── Populam tabel sumar ──
        self.table_sumar.setRowCount(0)
        total_ore = 0.0
        total_valoare = 0.0
        total_lucrari = 0

        for row_idx, (mecanic, nr, veh, ore, val) in enumerate(rows_sumar):
            ore = float(ore)
            val = float(val)
            total_ore += ore
            total_valoare += val
            total_lucrari += nr

            self.table_sumar.insertRow(row_idx)

            item_mec = QTableWidgetItem(mecanic)
            font = item_mec.font()
            font.setBold(True)
            item_mec.setFont(font)
            if mecanic != "— Nealocat —":
                item_mec.setForeground(QColor("#1e3a5f"))
            else:
                item_mec.setForeground(QColor("#9ca3af"))
            self.table_sumar.setItem(row_idx, 0, item_mec)

            self.table_sumar.setItem(row_idx, 1, self._item_center(str(nr)))
            self.table_sumar.setItem(row_idx, 2, self._item_center(str(veh)))

            item_ore = QTableWidgetItem(f"{ore:.1f}")
            item_ore.setTextAlignment(Qt.AlignCenter)
            item_ore.setForeground(QColor("#1A73E8"))
            self.table_sumar.setItem(row_idx, 3, item_ore)

            item_val = QTableWidgetItem(f"{val:,.2f}")
            item_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_val.setForeground(QColor("#10b981"))
            font2 = item_val.font()
            font2.setBold(True)
            item_val.setFont(font2)
            self.table_sumar.setItem(row_idx, 4, item_val)

            medie = round(ore / nr, 2) if nr > 0 else 0.0
            self.table_sumar.setItem(row_idx, 5, self._item_center(f"{medie:.2f}"))

            self.table_sumar.setRowHeight(row_idx, 30)

        # Footer
        self.lbl_total.setText(
            f"Total: {total_lucrari} lucrari  |  "
            f"{total_ore:.1f} ore RAR  |  "
            f"Valoare manopera: {total_valoare:,.2f} RON"
        )

        # Daca e selectat un mecanic din filtru, aratam detaliul direct
        if mecanic_filtru:
            self._load_detaliu(mecanic_filtru, de_la, pana_la)
        else:
            self.tree_detaliu.clear()

    # =========================================================
    # CLICK PE RAND DIN SUMAR → DETALIU
    # =========================================================
    def _on_sumar_selection(self):
        rows = self.table_sumar.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        mecanic_item = self.table_sumar.item(row, 0)
        if not mecanic_item:
            return
        mecanic = mecanic_item.text()
        if mecanic == "— Nealocat —":
            mecanic = ""
        de_la = self.date_de_la.date().toString("yyyy-MM-dd")
        pana_la = self.date_pana_la.date().toString("yyyy-MM-dd")
        self._load_detaliu(mecanic, de_la, pana_la)

    # =========================================================
    # DETALIU PE CATEGORII
    # =========================================================
    def _load_detaliu(self, mecanic, de_la, pana_la):
        self.tree_detaliu.clear()

        con = get_connection()
        cur = con.cursor()

        where_mec = "AND l.mecanic = ?" if mecanic else "AND (l.mecanic IS NULL OR l.mecanic = '')"
        params = [mecanic] if mecanic else []

        # Grupam dupa descriere (categoriile nu sunt stocate in lucrari,
        # le deducem din LUCRARI_PREDEFINITE sau le grupam alfabetic)
        cur.execute(f"""
            SELECT
                l.descriere,
                COUNT(*) as nr,
                COALESCE(SUM(l.ore_rar), 0) as ore,
                COALESCE(SUM(l.cost), 0) as val
            FROM lucrari l
            WHERE 1=1
            {where_mec}
            GROUP BY l.descriere
            ORDER BY val DESC
        """, params)
        rows = cur.fetchall()
        con.close()

        # Importam categoriile din dialog_lucrare
        try:
            from ui.dialogs.dialog_lucrare import LUCRARI_PREDEFINITE
            cat_map = {k: v["categorie"] for k, v in LUCRARI_PREDEFINITE.items()}
        except ImportError:
            cat_map = {}

        # Grupam pe categorii
        from collections import defaultdict
        categorii = defaultdict(list)
        for descriere, nr, ore, val in rows:
            cat = cat_map.get(descriere, "Altele")
            categorii[cat].append((descriere, int(nr), float(ore), float(val)))

        # Populam tree
        for cat_name in sorted(categorii.keys()):
            lucrari = categorii[cat_name]
            cat_nr = sum(l[1] for l in lucrari)
            cat_ore = sum(l[2] for l in lucrari)
            cat_val = sum(l[3] for l in lucrari)

            parent = QTreeWidgetItem([
                cat_name,
                str(cat_nr),
                f"{cat_ore:.1f}",
                f"{cat_val:,.2f}"
            ])
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            parent.setForeground(0, QColor("#1e3a5f"))
            parent.setForeground(1, QColor("#374151"))
            parent.setForeground(2, QColor("#1A73E8"))
            parent.setForeground(3, QColor("#10b981"))
            for col in range(4):
                parent.setTextAlignment(col, Qt.AlignLeft if col == 0 else Qt.AlignCenter)

            for descriere, nr, ore, val in sorted(lucrari, key=lambda x: -x[3]):
                child = QTreeWidgetItem([
                    f"  {descriere}",
                    str(nr),
                    f"{ore:.1f}",
                    f"{val:,.2f}"
                ])
                child.setForeground(0, QColor("#4b5563"))
                child.setForeground(2, QColor("#1A73E8"))
                child.setForeground(3, QColor("#10b981"))
                for col in range(4):
                    child.setTextAlignment(col, Qt.AlignLeft if col == 0 else Qt.AlignCenter)
                parent.addChild(child)

            self.tree_detaliu.addTopLevelItem(parent)
            parent.setExpanded(True)

    # =========================================================
    # EXPORT CSV
    # =========================================================
    def _export_csv(self):
        import csv, os
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime

        mecanic = self.cmb_mecanic.currentData() or "toti"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"raport_mecanic_{mecanic}_{timestamp}.csv"

        path, _ = QFileDialog.getSaveFileName(
            self, "Salveaza raport CSV", default_name, "CSV Files (*.csv)"
        )
        if not path:
            return

        def fix_nr(val):
            """Inlocuieste punctul zecimal cu virgula pentru Excel RO."""
            try:
                # Daca e numar, convertim separatorul
                float(val.replace(",", "."))
                return val.replace(".", ",")
            except (ValueError, AttributeError):
                return val

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)

                # ── Sumar ──
                writer.writerow(["=== SUMAR PE MECANIC ==="])
                headers_sumar = []
                for col in range(self.table_sumar.columnCount()):
                    h = self.table_sumar.horizontalHeaderItem(col)
                    headers_sumar.append(h.text() if h else "")
                writer.writerow(headers_sumar)

                for row in range(self.table_sumar.rowCount()):
                    row_data = []
                    for col in range(self.table_sumar.columnCount()):
                        item = self.table_sumar.item(row, col)
                        val = item.text() if item else ""
                        row_data.append(fix_nr(val))
                    writer.writerow(row_data)

                writer.writerow([])

                # ── Detaliu pe categorii ──
                writer.writerow(["=== DETALIU PE CATEGORII ==="])
                writer.writerow(["Categorie / Lucrare", "Nr. lucrari", "Ore RAR", "Valoare (RON)"])

                root = self.tree_detaliu.invisibleRootItem()
                for i in range(root.childCount()):
                    cat_item = root.child(i)
                    writer.writerow([
                        cat_item.text(0),
                        fix_nr(cat_item.text(1)),
                        fix_nr(cat_item.text(2)),
                        fix_nr(cat_item.text(3))
                    ])
                    for j in range(cat_item.childCount()):
                        child = cat_item.child(j)
                        writer.writerow([
                            child.text(0).strip(),
                            fix_nr(child.text(1)),
                            fix_nr(child.text(2)),
                            fix_nr(child.text(3))
                        ])

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Export", f"Salvat: {os.path.basename(path)}")

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Eroare", f"Nu s-a putut salva:\n{e}")

    # =========================================================
    # UTILE
    # =========================================================
    @staticmethod
    def _item_center(text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item
