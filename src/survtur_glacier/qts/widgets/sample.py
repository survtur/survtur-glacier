from PyQt5 import QtGui
from PyQt5.QtWidgets import QPushButton


class Sample(QPushButton):

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        print("PRESSED")
        super().mousePressEvent(e)
