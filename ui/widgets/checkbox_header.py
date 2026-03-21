from PyQt5.QtWidgets import QHeaderView, QStyleOptionButton, QStyle
from PyQt5.QtCore import Qt, pyqtSignal, QRect


class CheckBoxHeader(QHeaderView):
    clicked = pyqtSignal(bool)

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.isChecked = False

    def paintSection(self, painter, rect, logicalIndex):
        super().paintSection(painter, rect, logicalIndex)

        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(rect.left() + 10, rect.top() + 5, 20, 20)
            option.state = (
                QStyle.State_Enabled |
                (QStyle.State_On if self.isChecked else QStyle.State_Off)
            )
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)

    def mousePressEvent(self, event):
        if self.logicalIndexAt(event.pos()) == 0:
            self.isChecked = not self.isChecked
            self.clicked.emit(self.isChecked)
            self.updateSection(0)

        super().mousePressEvent(event)
