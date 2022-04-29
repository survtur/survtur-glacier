import os
import sys
from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets

from .qts.start_gui import SurvturGlacierGui


def start(workdir: Optional[str] = None):
    if workdir is None:
        home = str(Path.home())
        workdir = os.path.join(home, ".survtur-glacier")
        try:
            os.mkdir(workdir)
        except FileExistsError:
            pass

    app = QtWidgets.QApplication(sys.argv)
    window = SurvturGlacierGui(workdir=workdir)
    window.show()
    app.exec_()
