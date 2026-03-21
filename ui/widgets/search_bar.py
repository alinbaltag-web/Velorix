"""
VELORIX — SearchBar widget cu debounce
========================================
Inlocuieste conectarea directa la textChanged care face query la fiecare tasta.
Emite semnalul `search_triggered` dupa DEBOUNCE_MS milisecunde de la ultima tasta.

Utilizare:
    self.search = SearchBar(placeholder="Cauta...")
    self.search.search_triggered.connect(self.filter_data)
    layout.addWidget(self.search)
"""

from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import pyqtSignal, QTimer
from constants import SEARCH_DEBOUNCE_MS


class SearchBar(QLineEdit):
    search_triggered = pyqtSignal(str)

    def __init__(self, placeholder="Cauta...", debounce_ms=SEARCH_DEBOUNCE_MS, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._emit_search)

        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text):
        self._timer.stop()
        self._timer.start()

    def _emit_search(self):
        self.search_triggered.emit(self.text())
