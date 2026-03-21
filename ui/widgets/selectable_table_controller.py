from PyQt5.QtCore import QObject, pyqtSignal

class SelectableTableController(QObject):
    row_selected = pyqtSignal(int)
    row_deselected = pyqtSignal()

    def __init__(self, table, id_column=0, mode="single"):
        super().__init__()
        self.table = table
        self.id_column = id_column
        self.mode = mode

        if mode == "single":
            self.table.setSelectionMode(self.table.SingleSelection)
        else:
            self.table.setSelectionMode(self.table.MultiSelection)

        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()

        if not selected:
            self.row_deselected.emit()
            return

        row = selected[0].row()
        item = self.table.item(row, self.id_column)

        if item is None:
            self.row_deselected.emit()
            return

        try:
            selected_id = int(item.text())
        except ValueError:
            selected_id = item.text()

        self.row_selected.emit(selected_id)
