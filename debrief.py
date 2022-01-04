import sartopo_bg

from PyQt5.QtWidgets import *
from debrief_ui import Ui_DebriefDialog

# This class defines the dialog structure.
# How should the content be updated?  Options:
# - pushed from code that imports and instantiates this dialog:
#        this code does not need any smarts to populate the dialog fields
#     this makes sense if the DMG is running on the same computer,
#     but what if it's running on a different computer?
# - pulled from an associated debrief map generator object:
#        this code needs the smarts to populate the dialog fields
# - pulled from the debrief map, when the DMG process is not running locally:
#        this code needs the smarts to parse the debrief map AND
#        the smarts to populate the dialog fields

#  Maybe this code should be the parent of the DMG object, i.e. the DMG
#   object / process should be spawned from a button on this dialog.

class DebriefDialog(QDialog,Ui_DebriefDialog):
    def __init__(self,parent):
        QDialog.__init__(self)
        self.parent=parent
        
        # is this dialog being called from Plans Console?
        self.pc=self.parent.__class__.__name__=='PlansConsole'

        # is this computer running the debrief map generator?
        # self.localDMG=False

        self.ui=Ui_DebriefDialog()
        self.ui.setupUi(self)

    def showEvent(self,*args,**kwargs):
        if self.pc:
            self.ui.incidentMapField.setText(self.parent.incidentURL)
            self.ui.incidentLinkLight.setStyleSheet(self.parent.ui.incidentLinkLight.styleSheet())

    # refresh the display
    # provide for two modes of operation:
    # 1. this computer is running the debrief map generator
    #   the debrief map data file is available, so all data can be shown in the dialog
    # 2. a different computer is running the debrief map generator
    #   the debrief map data file is not available, so not all data can be shown

    # def refresh(self):
