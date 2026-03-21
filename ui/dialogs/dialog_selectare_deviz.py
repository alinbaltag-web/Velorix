"""
VELORIX — dialog_selectare_deviz.py
=====================================
Dialog simplu pentru selectarea unui deviz existent
din care se genereaza o factura.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from database import get_connection


class DialogSelectareDeviz(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._id_deviz = None

        self.setWindowTitle("Selecteaza deviz")
        self.setMinimumSize(680, 420)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #f8fafc; }
            QLabel { font-size: 12px; color: #374151; }
            QLineEdit {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                min-height: 32px;
            }
            QLineEdit:focus { border-color: #1A73E8; }
        """)

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 14, 16, 14)
        main.setSpacing(10)

        lbl = QLabel("Selecteaza devizul din care generezi factura")
        lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #1e3a5f;")
        main.addWidget(lbl)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Cauta dupa client, vehicul, nr. deviz...")
        self.txt_search.textChanged.connect(self.load_data)
        main.addWidget(self.txt_search)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Nr.", "Data", "Client", "Vehicul", "Total", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: 12px;
            }
            QHeaderView::section {
                background: #f8fafc;
                font-weight: 600;
                font-size: 11px;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
            QTableWidget::item:alternate { background: #fafafa; }
        """)
        main.addWidget(self.table)

        lbl_hint = QLabel("💡 Dublu-click pe un deviz pentru a-l selecta.")
        lbl_hint.setStyleSheet("font-size: 11px; color: #9ca3af;")
        main.addWidget(lbl_hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Anuleaza")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #374151;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_select = QPushButton("✔ Selecteaza")
        btn_select.setFixedHeight(34)
        btn_select.setStyleSheet("""
            QPushButton {
                background: #1A73E8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: #1557b0; }
        """)
        btn_select.clicked.connect(self._on_select)

        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_select)
        main.addLayout(btn_row)

    def load_data(self):
        search = self.txt_search.text().strip()
        con = get_connection()
        cur = con.cursor()

        query = """
            SELECT d.id, d.data,
                   COALESCE(c.nume, '—') as client,
                   COALESCE(v.marca || ' ' || v.model || ' ' || COALESCE(v.nr,''), '—') as vehicul,
                   COALESCE(d.total_general, 0),
                   COALESCE(d.tip, 'deviz'),
                   CASE WHEN EXISTS (
                       SELECT 1 FROM facturi f
                       WHERE f.id_deviz = d.id
                       AND f.tip IN ('FACTURA', 'PROFORMA')
                       AND f.status NOT IN ('stornata', 'anulata')
                   ) THEN 1 ELSE 0 END as facturat
            FROM devize d
            LEFT JOIN clienti c  ON c.id = d.id_client
            LEFT JOIN vehicule v ON v.id = d.id_vehicul
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (c.nume LIKE ? OR d.id LIKE ? OR v.nr LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        query += " ORDER BY d.data DESC LIMIT 100"
        cur.execute(query, params)
        rows = cur.fetchall()
        con.close()

        self.table.setRowCount(0)
        self.table.setRowCount(len(rows))

        for i, (id_d, data, client, vehicul, total, status, facturat) in enumerate(rows):
            item_id = QTableWidgetItem(f"#{id_d}")
            item_id.setData(Qt.UserRole, id_d)
            self.table.setItem(i, 0, item_id)
            self.table.setItem(i, 1, QTableWidgetItem(data or ""))
            self.table.setItem(i, 2, QTableWidgetItem(client))
            self.table.setItem(i, 3, QTableWidgetItem(vehicul))
            self.table.setItem(i, 4, QTableWidgetItem(f"{total:,.2f} RON"))

            if facturat:
                status_item = QTableWidgetItem("✅ Facturat")
                status_item.setForeground(QColor("#059669"))
                status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            else:
                status_item = QTableWidgetItem(status.capitalize())

            self.table.setItem(i, 5, status_item)
            self.table.setRowHeight(i, 38)

    def _on_double_click(self, index):
        self._on_select()

    def _on_select(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item:
            self._id_deviz = item.data(Qt.UserRole)
            self.accept()

    def get_id_deviz(self):
        return self._id_deviz