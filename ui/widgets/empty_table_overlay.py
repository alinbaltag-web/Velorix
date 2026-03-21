from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt


class EmptyTableOverlay(QLabel):
    """
    Label centrat peste viewport-ul unui QTableWidget.
    Apare automat cand tabelul nu are randuri, dispare cand are.
    Folosire:
        overlay = EmptyTableOverlay(table, "Niciun client inregistrat.")
    """

    def __init__(self, table, text="Nicio inregistrare gasita."):
        super().__init__(table.viewport())
        self._table = table
        self.setText(text)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            color: #94a3b8;
            font-size: 14px;
            font-style: italic;
            background: transparent;
        """)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

        # Suprascrie resizeEvent pe viewport ca sa ne repozitionam
        _orig_resize = table.viewport().resizeEvent

        def _on_resize(event):
            self._reposition()
            if _orig_resize:
                _orig_resize(event)

        table.viewport().resizeEvent = _on_resize

    def update_visibility(self):
        visible = self._table.rowCount() == 0
        self.setVisible(visible)
        if visible:
            self._reposition()

    def _reposition(self):
        vp = self._table.viewport()
        self.setGeometry(0, 0, vp.width(), vp.height())
