from PyQt5 import QtWidgets


class CustomSortableTableWidget(QtWidgets.QTableWidgetItem):
    ALWAYS_MAX = object()
    ALWAYS_MIN = object()

    def __init__(self, sort_value, display: str) -> None:
        self.sort_value = sort_value
        super().__init__(display)

    # This is the only function you need to implement to perform sorting
    def __lt__(self, other: "CustomSortableTableWidget") -> bool:
        if self.sort_value == self.ALWAYS_MAX:
            return False
        if self.sort_value == self.ALWAYS_MIN:
            return True
        if other.sort_value == self.ALWAYS_MIN:
            return True
        if other.sort_value == self.ALWAYS_MAX:
            return False
        return self.sort_value.__lt__(other.sort_value)
