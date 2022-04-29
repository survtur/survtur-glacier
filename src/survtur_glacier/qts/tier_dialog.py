from typing import Optional

from PyQt5.QtWidgets import QDialog, QStyle, QFileDialog

from ..common.human_readable import human_readable_bytes
from ..glacier.survtur_glacier import GlacierTier
from ..qts.tierdialog_qt5 import Ui_TierDialog


class TierDialog(QDialog):
    selected_tier: Optional[GlacierTier] = None
    selected_path: Optional[str] = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_TierDialog()
        self.ui.setupUi(self)

        self.ui.btnOk.setIcon(self.style().standardIcon(QStyle.SP_DialogOkButton))
        self.ui.btnCancel.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))

        self.ui.standardRadio.clicked.connect(lambda: self.set_tier(GlacierTier.STANDARD))
        self.ui.expeditedRadiio.clicked.connect(lambda: self.set_tier(GlacierTier.EXPEDITED))
        self.ui.bultRadio.clicked.connect(lambda: self.set_tier(GlacierTier.BULK))
        self.ui.btnPickFolder.clicked.connect(self.show_pick_folder_dialog)

    def update_label(self, size: int, files_count: int, dirs_count: int):
        bts = human_readable_bytes(size, letters=("&nbsp;bytes", "&nbsp;Kb", "&nbsp;Mb", "&nbsp;Gb", "&nbsp;Tb", "&nbsp;Eb"))
        text = (f"You are going to download <b>{bts}</b> of data. Archives count:&nbsp;{files_count}.")

        self.ui.label.setText(f"<html>{text}</html>")

    def set_tier(self, t: GlacierTier):
        self.selected_tier = t
        self._try_enable_button()

    def _try_enable_button(self):
        if self.selected_tier and self.selected_path:
            self.ui.btnOk.setEnabled(True)

    def show_pick_folder_dialog(self):
        d = QFileDialog(self, caption="Choose folder to save to")
        d.setFileMode(QFileDialog.DirectoryOnly)
        d.fileSelected.connect(self.on_folder_selected)
        d.finished.connect(d.deleteLater)
        d.show()

    def on_folder_selected(self, selection: str):
        show = selection if len(selection) < 40 else f"…{selection[-30:]}"
        self.ui.btnPickFolder.setText(show)
        self.ui.btnPickFolder.setToolTip(selection)
        self.selected_path = selection
        self._try_enable_button()
