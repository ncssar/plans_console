from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import logging
import os
import glob

# rebuild all _ui.py files from .ui files in the same directory as this script as needed
#   NOTE - this will overwrite any edits in _ui.py files
for ui in glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'*.ui')):
    uipy=ui.replace('.ui','_ui.py')
    if not (os.path.isfile(uipy) and os.path.getmtime(uipy) > os.path.getmtime(ui)):
        cmd='pyuic5 -o '+uipy+' '+ui
        logging.info('Building GUI file from  '+os.path.basename(ui)+':')
        logging.info('  '+cmd)
        os.system(cmd)

# rebuild all _rc.py files from .qrc files in the same directory as this script as needed
#   NOTE - this will overwrite any edits in _rc.py files
for qrc in glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'*.qrc')):
    rcpy=qrc.replace('.qrc','_rc.py')
    if not (os.path.isfile(rcpy) and os.path.getmtime(rcpy) > os.path.getmtime(qrc)):
        cmd='pyrcc5 -o '+rcpy+' '+qrc
        logging.info('Building Qt Resource file from  '+os.path.basename(qrc)+':')
        logging.info('  '+cmd)
        os.system(cmd)

from specifyMapDialog_ui import Ui_SpecifyMapDialog

class SpecifyMapDialog(QDialog,Ui_SpecifyMapDialog):
    def __init__(self,parent,name=None,headerText=None,defaultDomainAndPort=None):
        QDialog.__init__(self)
        self.parent=parent
        
        # properties that can be queried as effective return values (None if dialog is rejected)
        self.domainAndPort=None
        self.url=None

        self.ui=Ui_SpecifyMapDialog()
        self.ui.setupUi(self)
        self.ui.domainAndPortButtonGroup.buttonClicked.connect(self.domainAndPortClicked)
        self.urlChanged()
        self.ui.mapIDField.setFocus()
        if defaultDomainAndPort:
            found=False
            for button in self.ui.domainAndPortButtonGroup.buttons():
                if defaultDomainAndPort==button.text():
                    found=True
                    button.click()
            if not found:
                self.ui.otherButton.click()
                self.ui.domainAndPortOtherField.setText(defaultDomainAndPort)
        if name:
            self.ui.mapIdLabel.setText(str(name)+' Map ID:')
            self.ui.mapURLLabel.setText(str(name)+' Map URL:')
            self.setWindowTitle('Specify '+name+' Map')
        if headerText:
            self.ui.headerLabel.setText(str(headerText))
        elif name:
            self.ui.headerLabel.setText('Specify the '+str(name)+' map:')

    def domainAndPortClicked(self,*args,**kwargs):
        val=self.ui.domainAndPortButtonGroup.checkedButton().text()
        self.ui.domainAndPortOtherField.setEnabled(val=='Other')
        self.urlChanged()

    def urlChanged(self):
        self.dap=self.ui.domainAndPortButtonGroup.checkedButton().text()
        if self.dap=='Other':
            self.dap=self.ui.domainAndPortOtherField.text()
        prefix='http://'
        if '.com' in self.dap:
            prefix='https://'
        mapID=self.ui.mapIDField.text()
        url=prefix+self.dap+'/m/'+mapID
        self.ui.urlField.setText(url)

    def accept(self):
        self.url=self.ui.urlField.text()
        self.domainAndPort=self.dap
        super(SpecifyMapDialog,self).accept()