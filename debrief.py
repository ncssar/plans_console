import sartopo_bg

from PyQt5.QtWidgets import *
from debrief_ui import Ui_DebriefDialog

class debriefDialog(QDialog,Ui_DebriefDialog):
    def __init__(self,parent):
        QDialog.__init__(self)
        self.parent=parent
        # is this dialog being called from Plans Console?
        self.pc=self.parent.__class__.__name__=='PlansConsole'
        self.ui=Ui_DebriefDialog()
        self.ui.setupUi(self)

    def showEvent(self,*args,**kwargs):
        if self.pc:
            self.ui.incidentMapField.setText(self.parent.incidentURL)
            self.ui.incidentLinkLight.setStyleSheet(self.parent.ui.incidentLinkLight.styleSheet())
