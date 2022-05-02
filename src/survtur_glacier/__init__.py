from typing import Optional

__version__ = "2022.4a12"


def start(workdir: Optional[str] = None):
    print("Starting Survtur Glacier " + __version__)
    import os
    import sys
    from pathlib import Path
    from PyQt5 import QtWidgets

    from .qts.start_gui import SurvturGlacierGui
    if workdir is None:
        home = str(Path.home())
        workdir = os.path.join(home, ".survtur-glacier")
        try:
            os.mkdir(workdir)
        except FileExistsError:
            pass

    app = QtWidgets.QApplication(sys.argv)
    window = SurvturGlacierGui(workdir=workdir)
    window.setWindowTitle("Survtur Glacier " + __version__)
    window.show()
    app.exec_()
