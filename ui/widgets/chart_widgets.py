"""
VELORIX — Grafice native PyQt5 (fara pyqtgraph/numpy)
Inlocuieste graficele pyqtgraph din page_dashboard.py
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient


class BarChartWidget(QWidget):
    """Grafic bare venituri - nativ PyQt5"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.valori = []
        self.etichete = []
        self.setMinimumHeight(150)
        self.setMaximumHeight(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, valori, etichete):
        self.valori = valori
        self.etichete = etichete
        self.update()

    def paintEvent(self, event):
        if not self.valori:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding_left = 45
        padding_right = 10
        padding_top = 20
        padding_bottom = 30

        max_val = max(self.valori) if max(self.valori) > 0 else 1
        n = len(self.valori)
        available_w = w - padding_left - padding_right
        bar_w = int(available_w / n * 0.6)
        gap = int(available_w / n)

        culori = ["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1A73E8"]

        for i, (val, label) in enumerate(zip(self.valori, self.etichete)):
            x = padding_left + i * gap + (gap - bar_w) // 2
            bar_h = int((val / max_val) * (h - padding_top - padding_bottom))
            y = h - padding_bottom - bar_h

            culoare = QColor(culori[i % len(culori)])
            painter.setBrush(QBrush(culoare))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

            # Valoare deasupra barei
            if val > 0:
                painter.setPen(QPen(QColor("#1e3a5f")))
                painter.setFont(QFont("Segoe UI", 7))
                val_text = f"{val:,.0f}" if val < 100000 else f"{val/1000:.0f}k"
                painter.drawText(x - 5, y - 3, bar_w + 10, 14,
                                 Qt.AlignCenter, val_text)

            # Eticheta jos
            painter.setPen(QPen(QColor("#6b7280")))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(x - 5, h - padding_bottom + 4, bar_w + 10, 20,
                             Qt.AlignCenter, label)

        # Linie baza
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        painter.drawLine(padding_left - 5, h - padding_bottom,
                         w - padding_right, h - padding_bottom)

        # Gridlines orizontale (3 linii)
        painter.setFont(QFont("Segoe UI", 7))
        for step in [0.25, 0.5, 0.75, 1.0]:
            y_grid = h - padding_bottom - int(step * (h - padding_top - padding_bottom))
            painter.setPen(QPen(QColor("#f3f4f6"), 1, Qt.DashLine))
            painter.drawLine(padding_left, y_grid, w - padding_right, y_grid)
            val_grid = max_val * step
            painter.setPen(QPen(QColor("#9ca3af")))
            label_grid = f"{val_grid:,.0f}" if val_grid < 10000 else f"{val_grid/1000:.0f}k"
            painter.drawText(0, y_grid - 6, padding_left - 3, 14,
                             Qt.AlignRight | Qt.AlignVCenter, label_grid)

        painter.end()


class DonutChartWidget(QWidget):
    """Grafic donut status lucrari - nativ PyQt5"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.segmente = []  # [(valoare, culoare, label), ...]
        self.total = 0
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, segmente):
        """segmente = [(valoare, culoare, label), ...]"""
        self.segmente = segmente
        self.total = sum(v for v, _, _ in segmente)
        self.update()

    def paintEvent(self, event):
        import math

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        if self.total == 0:
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, "Fara date")
            painter.end()
            return

        size = min(w, h) - 10
        x = (w - size) // 2
        y = (h - size) // 2
        rect = QRect(x, y, size, size)
        inner_size = int(size * 0.55)
        inner_x = x + (size - inner_size) // 2
        inner_y = y + (size - inner_size) // 2
        inner_rect = QRect(inner_x, inner_y, inner_size, inner_size)

        unghi_start = -90 * 16  # Qt foloseste 1/16 grade

        for valoare, culoare, label in self.segmente:
            if valoare == 0:
                continue
            unghi_span = int(360 * 16 * valoare / self.total)
            painter.setBrush(QBrush(QColor(culoare)))
            painter.setPen(QPen(QColor("white"), 2))
            painter.drawPie(rect, unghi_start, unghi_span)
            unghi_start += unghi_span

        # Cerc interior alb (donut)
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(inner_rect)

        # Total in centru
        painter.setPen(QPen(QColor("#1e3a5f")))
        painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
        painter.drawText(inner_rect, Qt.AlignCenter, str(self.total))

        painter.end()