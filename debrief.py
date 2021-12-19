import sartopo_bg

from PyQt5.QtWidgets import *
from debrief_ui import Ui_DebriefDialog

class debriefDialog(QDialog,Ui_DebriefDialog):
    def __init__(self,parent):
        QDialog.__init__(self)
        self.ui=Ui_DebriefDialog()
        self.ui.setupUi(self)
