from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import logging
import os
import glob
import math

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

def genLpix(ldpi):
    lpix={}
    for ptSize in [1,2,3,4,6,8,9,10,11,12,14,16,18,22,24,36,48]:
        lpix[ptSize]=math.floor((ldpi*ptSize)/72)
    return lpix

class SpecifyMapDialog(QDialog,Ui_SpecifyMapDialog):
    def __init__(self,parent,name=None,headerText=None,defaultDomainAndPort=None,enableNewMap=False,newDefault=False):
        QDialog.__init__(self)
        self.parent=parent
        self.enableNewMap=enableNewMap
        self.newMap=newDefault
        self.ldpi=0
        self.tmp='small'
        
        # properties that can be queried as effective return values (None if dialog is rejected)
        self.domainAndPort=None
        self.url=None

        self.moveTimer=QTimer(self)
        self.moveTimer.timeout.connect(self.moveTimeout)
        self.ui=Ui_SpecifyMapDialog()
        self.ui.setupUi(self)
        self.ui.newMapRadioButton.setVisible(enableNewMap)
        self.ui.existingMapRadioButton.setVisible(enableNewMap)
        self.ui.newOrExistingLine1.setVisible(enableNewMap)
        self.ui.newOrExistingLine2.setVisible(enableNewMap)
        self.ui.mapSourceButtonGroup.buttonClicked.connect(self.mapSourceClicked)
        self.ui.domainAndPortButtonGroup.buttonClicked.connect(self.domainAndPortClicked)
        if self.newMap:
            self.ui.newMapRadioButton.setChecked(True)
        else:
            self.ui.existingMapRadioButton.setChecked(True)
        self.mapSourceClicked()
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
            # self.ui.mapIDGroupBox.setTitle(str(name)+' Map ID')
            self.ui.mapURLLabel.setText(str(name)+' Map URL:')
            self.setWindowTitle('Specify '+name+' Map')
        if headerText:
            self.ui.headerLabel.setText(str(headerText))
        elif name:
            self.ui.headerLabel.setText('Specify the '+str(name)+' map:')
        self.adjustSize()
        self.setMinimumSize(self.size())
        self.setMaximumSize(self.size())

    def moveEvent(self,event):
        self.setMinimumSize(0,0)
        self.setMaximumSize(10000,10000)
        self.moveTimer.start(100)
        super(SpecifyMapDialog,self).moveEvent(event)

    def moveTimeout(self,*args):
        # logging.info('move ended')
        self.moveTimer.stop()
        [x,y,w,h]=self.geometry().getRect()
        ldpi=self.screen().logicalDotsPerInch()
        if ldpi!=self.ldpi:
            self.ldpi=ldpi
            # logging.info('ldpi changed')
            pix=genLpix(ldpi)
            self.setStyleSheet('''
                *{
                    font-size:'''+str(pix[12])+'''px;
                }
                QDialog{
                    padding:'''+str(pix[6])+'''px;
                }
                QLineEdit{
                    height:'''+str(pix[16])+'''px;
                }
                QLineEdit#mapIDField{
                    height:'''+str(pix[24])+'''px;
                    font-size:'''+str(pix[22])+'''px;
                }
                QGroupBox{
                    border:'''+str(pix[1])+'''px solid #888;
                    border-radius:'''+str(pix[4])+'''px;
                    margin-top:'''+str(pix[10])+'''px;
                    padding:'''+str(pix[3])+'''px;
                    padding-top:'''+str(pix[6])+'''px;
                    font-size:'''+str(pix[10])+'''px;
                }
                QGroupBox::title{
                    padding-top:-'''+str(pix[14])+'''px;
                    left:'''+str(pix[8])+'''px;
                }
                QCheckBox::indicator,QRadioButton::indicator{
                    width:'''+str(pix[10])+'''px;
                    height:'''+str(pix[10])+'''px;
                }
                QRadioButton{
                    spacing:'''+str(pix[8])+'''px;
                }
                #newMapRadioButton,#existingMapRadioButton{
                    font-size:'''+str(pix[16])+'''px;
                }
                #newMapRadioButton::indicator,#existingMapRadioButton::indicator{
                    width:'''+str(pix[12])+'''px;
                    height:'''+str(pix[12])+'''px;
                }
            ''')
            # this results in 'ratcheting': the resize happens by moving the right and bottom sides,
            #  and leaving the top left where it is, relative to the mouse; so each size reduction
            #  means the mouse is farther to the right within the banner, and eventually the mouse
            #  is outisde (to the right of) the banner
            self.ui.dapGroupBox.setMinimumWidth(int(250*(self.ldpi/96)))
            self.adjustSize()
            self.setMinimumSize(self.size())
            self.setMaximumSize(self.size())
            # it would be good to resolve the ratchetings at some point, but this is good enough for now

    def mapSourceClicked(self,*args,**kwargs):
        val=self.ui.mapSourceButtonGroup.checkedButton().text()
        if val=='New Map':
            self.ui.mapIDGroupBox.setEnabled(False)
            self.ui.mapIDGroupBox.setStyleSheet('QGroupBox:title {color: gray;} QGroupBox {border-color: #CCC;}')
            self.newMap=True
        else:
            self.ui.mapIDGroupBox.setEnabled(True)
            self.ui.mapIDGroupBox.setStyleSheet('QGroupBox:title {color: black;} QGroupBox {border-color: #888;}')
            self.newMap=False
            self.ui.mapIDField.setFocus()
        self.urlChanged()

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
        if self.enableNewMap and self.ui.mapSourceButtonGroup.checkedButton().text()=='New Map':
            mapID='<Pending>'
        else:
            mapID=self.ui.mapIDField.text()
        # form validation: disable Ok button when mapID is blank
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(mapID!='')
        url=prefix+self.dap+'/m/'+mapID
        self.ui.urlField.setText(url)

    def accept(self):
        self.url=self.ui.urlField.text()
        self.domainAndPort=self.dap
        super(SpecifyMapDialog,self).accept()