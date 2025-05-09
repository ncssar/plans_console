# #############################################################################
#
#  Plans_console.py - watch a radiolog.csv file that is being written by
#    the full radiolog program, presumably running on a different computer
#    writing to a shared drive that this program can see.  Also, enable the
#    placement of Markers for Teams when at an assignment, edit shapes and 
#    assignments and create debrief maps for faster access.
#
#   developed for Nevada County Sheriff's Search and Rescue
#   requires caltopo_python and several other python libs
#
#   Attribution, feedback, bug reports and feature requests are appreciated
#
#  REVISION HISTORY
#-----------------------------------------------------------------------------
#   DATE     |  AUTHOR  |  NOTES
#-----------------------------------------------------------------------------
#  8/7/2020   SDL         Initial released
#  6/16/2021  SDL         added cut/expand/crop interface
#  2022       TMG         upgraded the UI and added the debrief map
#  7/8/2023   SDL         changed Med icon to not display team# on the map
#  8/27/2023  SDL         fixed issue with case and not finding an edited object (part of fix is in caltopo_python)
#  10/6/2023  SDL         added clue log listing and print button for clue log and assignments
#  12/17/2023 SDL         added try block around getFeatures for med/assignment getObjects
#  3/10/2024  SDL         fixed reload of medical icon into TmAs table
#  3/17/2024  SDL         redefined check for LE callsign & trying to remove duplicate radiolog entries
#  8/17/2024  SDL         bug  assignment number with embedded extra spaces
# 10/20/2024  SDL         add check for empty assignment letter (saving color for main/ckue table rows)
#  3/14/2025  SDL 1.24    allow IC/TR to create a table entry, implemented color restore upon rescan
#  4/26/2025  SDL 1.25    put try around editfeature due to connection error to Caltopo   
#  4/28/2025  SDL 1.26    fixed issue with new radiolog entries, added IC and TR assignments, using caltopo_python
#  5/03/2025  SDL 1.27    strip spaces from team entry. change IC assign to ICX (conflict with IC marker)
#
# #############################################################################
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  See included file LICENSE.txt for full license terms, also
#  available at http://opensource.org/licenses/gpl-3.0.html
#
# ############################################################################
#



from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from pygtail import Pygtail
import math
import os
import shutil
import glob
import regex
import time
import io
import traceback
import json
import random
import configparser
import argparse
from shapely.geometry import Polygon
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import subprocess
VERSION = "1.27"

caltopo_python_min_version="1.1.2"
#import pkg_resources
#caltopo_python_installed_version=pkg_resources.get_distribution("caltopo-python").version
#print("caltopo_python version:"+str(caltopo_python_installed_version))
##if pkg_resources.parse_version(caltopo_python_installed_version)<pkg_resources.parse_version(caltopo_python_min_version):
#    print("ABORTING: installed caltopo_python version "+str(caltopo_python_installed_version)+ \
#          " is less than minimum required version "+caltopo_python_min_version)
#    exit()
import sys
caltopo_python_dir='../caltopo_python/caltopo_python'
if os.path.isdir(caltopo_python_dir):
    sys.path.insert(1,caltopo_python_dir)
from caltopo_python import CaltopoSession # import before logging to avoid useless numpy-not-installed message

# start logging early, to catch any messages during import of modules

import logging

import common # variables shared across multiple modules

# log filename should be <top-level-module-name>.log
# logfile=os.path.splitext(os.path.basename(sys.path[0]))[0]+'.log'
common.pcDir='C:\\PlansConsole'
common.pcLogDir=os.path.join(common.pcDir,'Logs')
common.logfile=os.path.join(common.pcLogDir,'plans_console.log')

if not os.path.isdir(common.pcLogDir):
    os.makedirs(common.pcLogDir)

cleanShutdownText='Plans Console shutdown requested'
# cleanShutdownText should appear in the last five lines of the previous
#  log file if it was a clean shutdown; if not, copy the file
#  with a unique filename before starting the new log; use seek instead
#  of readlines to reduce time and memory consumption for large log files
if os.path.exists(common.logfile):
    save=False
    if os.path.getsize(common.logfile)>1024:
        with open(common.logfile,'rb') as f:
            f.seek(-1025,2) # 1kB before the file's end
            tail=f.read(1024).decode()
        if cleanShutdownText not in tail:
            save=True
    else: # tiny file; read the whole file to see if clean shutdown line exists
        with open(common.logfile,'r') as f:
            if cleanShutdownText not in f.read():
                save=True
    if save:
        shutil.copyfile(common.logfile,os.path.splitext(common.logfile)[0]+'.aborted.'+datetime.fromtimestamp(os.path.getmtime(common.logfile)).strftime('%Y-%m-%d-%H-%M-%S')+'.log')

# print by default; let the caller change this if needed
# (note, caller would need to clear all handlers first,
#   per stackoverflow.com/questions/12158048)
# To redefine basicConfig, per stackoverflow.com/questions/12158048
# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    datefmt='%H:%M:%S',
    format='%(asctime)s [%(module)s:%(lineno)d:%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(common.logfile,'w'),
        logging.StreamHandler(sys.stdout)
    ]
)

from specifyMap import SpecifyMapDialog

BG_GREEN = "background-color:#00bb00;"
BG_RED = "background-color:#bb0000;"
BG_GRAY = "background-color:#aaaaaa;"

# rebuild all _ui.py files from .ui files in the same directory as this script as needed
#   NOTE - this will overwrite any edits in _ui.py files
for ui in glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'*.ui')):
    uipy=ui.replace('.ui','_ui.py')
    if not (os.path.isfile(uipy) and os.path.getmtime(uipy) > os.path.getmtime(ui)):
        cmd='pyuic5 -o '+uipy+' '+ui
        logging.info('Building GUI file from '+os.path.basename(ui)+':')
        logging.info('  '+cmd)
        os.system(cmd)

# rebuild all _rc.py files from .qrc files in the same directory as this script as needed
#   NOTE - this will overwrite any edits in _rc.py files
for qrc in glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)),'*.qrc')):
    rcpy=qrc.replace('.qrc','_rc.py')
    if not (os.path.isfile(rcpy) and os.path.getmtime(rcpy) > os.path.getmtime(qrc)):
        cmd='pyrcc5 -o '+rcpy+' '+qrc
        logging.info('Building Qt Resource file from '+os.path.basename(qrc)+':')
        logging.info('  '+cmd)
        os.system(cmd)

from plans_console_ui import Ui_PlansConsole
from caltopo_bg import *
logging.info('PID:'+str(os.getpid()))

def genLpix(ldpi):
    if ldpi<10:
        ldpi=96
    lpix={}
    for ptSize in [1,2,3,4,6,8,9,10,11,12,14,16,18,22,24,36,48]:
        lpix[ptSize]=math.floor((ldpi*ptSize)/72)
    return lpix


def ask_user_to_confirm(question: str, icon: QMessageBox.Icon = QMessageBox.Question, parent: QObject = None, title = "Please Confirm") -> bool:
    # don't bother taking the steps to handle moving from one screen to another of different ldpi
    opts = Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowStaysOnTopHint
    buttons = QMessageBox.StandardButton(QMessageBox.Yes | QMessageBox.No)
    # determine logical pixel equivalents: take from parent if possible, so that the messagebox uses the same DPI as the spawning window
    if parent and hasattr(parent,'ldpi') and parent.ldpi>1:
        ldpi=parent.ldpi
        # logging.info('using parent ldpi = '+str(ldpi))
    else:
        try:
            ldpi=parent.window().screen().logicalDotsPerInch()
            # logging.info('using lpdi of parent\'s screen = '+str(ldpi))
        except:
            testDialog=QDialog()
            testDialog.show()
            ldpi=testDialog.window().screen().logicalDotsPerInch()
            testDialog.close()
            del testDialog
            # logging.info('using lpdi of current screen = '+str(ldpi))
    lpix=genLpix(ldpi)
    box = QMessageBox(icon, title, question, buttons, parent, opts)
    box.setDefaultButton(QMessageBox.No)
    spacer=QSpacerItem(int(300*(ldpi/96)),0,QSizePolicy.Minimum,QSizePolicy.Expanding)
    layout=box.layout()
    layout.addItem(spacer,layout.rowCount(),0,1,layout.columnCount())
    box.setStyleSheet('''
    *{
        font-size:'''+str(lpix[12])+'''px;
        icon-size:'''+str(lpix[36])+'''px '''+str(lpix[36])+'''px;
    }''')
    QCoreApplication.processEvents()
    box.show()
    box.raise_()
    return box.exec_() == QMessageBox.Yes

##  set timeout to 4 sec
def inform_user_about_issue(message: str, icon: QMessageBox.Icon = QMessageBox.Critical, parent: QObject = None, title="", timeout=4000):
    # don't bother taking the steps to handle moving from one screen to another of different ldpi
    opts = Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowStaysOnTopHint
    if title == "":
        title = "Warning" if (icon == QMessageBox.Warning) else "Error"
    buttons = QMessageBox.StandardButton(QMessageBox.Ok)
    # determine logical pixel equivalents: take from parent if possible, so that the messagebox uses the same DPI as the spawning window
    if parent and hasattr(parent,'ldpi') and parent.ldpi>1:
        ldpi=parent.ldpi
        # logging.info('using parent ldpi = '+str(ldpi))
    else:
        try:
            ldpi=parent.window().screen().logicalDotsPerInch()
            # logging.info('using lpdi of parent\'s screen = '+str(ldpi))
        except:
            testDialog=QDialog()
            testDialog.show()
            ldpi=testDialog.window().screen().logicalDotsPerInch()
            testDialog.close()
            del testDialog
            # logging.info('using lpdi of current screen = '+str(ldpi))
    lpix=genLpix(ldpi)
    box = QMessageBox(icon, title, message, buttons, parent, opts)
    spacer=QSpacerItem(int(800*(ldpi/96)),0,QSizePolicy.Minimum,QSizePolicy.Expanding)
    layout=box.layout()
    layout.addItem(spacer,layout.rowCount(),0,1,layout.columnCount())
    box.setStyleSheet('''
    *{
        font-size:'''+str(lpix[12])+'''px;
        icon-size:'''+str(lpix[36])+'''px '''+str(lpix[36])+'''px;
    }''')
    QCoreApplication.processEvents()
    box.show()
    box.raise_()
    if timeout:
        if timeout<100:
            timeout=timeout*1000 # user probably specified integer seconds
        QTimer.singleShot(timeout,box.close)
    box.exec_()

statusColorDict={}
statusColorDict["At IC"]=["22ff22","000000"]
statusColorDict["Available"]=["00ffff","000000"]
statusColorDict["In Transit"]=["2222ff","eeeeee"]
statusColorDict["Waiting for Transport"]=["2222ff","eeeeee"]

stateColorDict={}    # used to toggle color
stateColorDict["#ff4444"]="#eeeeee"
stateColorDict["#eeeeee"]="#ff4444"
sys.tracebacklimit = 1000


# log uncaught exceptions - https://stackoverflow.com/a/16993115/3577105
# don't try to print from inside this function, since stdout is in binary mode
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))
    inform_user_about_issue('Uncaught exception:\n\n'+str(exc_type.__name__)+': '+str(exc_value)+'\n\nCheck log file for details including traceback.  The program will continue if possible when you close this message box.', timeout=4000)
sys.excepthook = handle_exception

def sortByTitle(item):
    return item["properties"]["title"]

# Working directory structure 4-8-22:
#  C:\PlansConsole
#     |
#     |-- Logs
#     |     |-- plans_console.log
#     |     |-- [plans_console.log.err[.1-5]]
#     |     |-- [plans_console_aborted.<date><time>.log]
#     |
#     |-- Config
#     |     |-- plans_console.cfg
#     |     |-- plans_console.rc
#     |     |-- cts.ini
#     |
#     |-- save_plans_console.txt
#     |
#     |-- Debrief
#           |-- JSON
#           |    |-- <incidentMapID>_<debriefMapID>.json
#           |
#           |-- Maps
#                |-- <outingName>_<time>_<pdfID>.pdf
#                       (files also written to optional second PDF directory
#                        such as Z:\DebriefMaps, specified in plans_console.cfg)

class PlansConsole(QDialog,Ui_PlansConsole):
    def __init__(self,parent):
        QDialog.__init__(self)
        logging.info('Plans Console Vers '+str(VERSION)+' startup at '+datetime.now().strftime("%a %b %d %Y %H:%M:%S"))

        self.ldpi=1 # font size calculations (see moveEvent)
        self.parent=parent
        self.pcConfigDir=os.path.join(common.pcDir,'Config')
        self.ctsconfigpath=os.path.join(self.pcConfigDir,'cts.ini')
        self.rcFileName=os.path.join(self.pcConfigDir,'plans_console.rc')
        self.configFileName=os.path.join(self.pcConfigDir,'plans_console.cfg')
        self.pcDataFileName=os.path.join(common.pcDir,'save_plans_console.txt')

        self.ui=Ui_PlansConsole()
        self.ui.setupUi(self)

        # default window geometry; overridden by previous rc file
        
        self.xd=100
        self.yd=100
        self.wd=1600
        self.hd=1000
        # self.fontSize=12
        self.grid=[[0]]
        self.curTeam = ""
        self.curAssign = ""
        self.curType = ""
        self.totalRows = 0
        self.totalRows2 = 0
        self.x = self.xd
        self.y = self.yd
        self.w = self.wd
        self.h = self.hd
        self.debriefX=None
        self.debriefY=None
        self.debriefW=None
        self.debriefH=None
        self.fidMed = None
        self.fidLE = None
        self.sentMsg = []
        self.savedData = []      # data saved prior to a rescan
        self.FIRST_PASS = True   # unset after first time thru so that warning above is only given once
        self.color = ["#ffff00", "#cccccc"]  # yellow, gray80
                     
        self.loadRcFile()

		# main window:
        # make sure x/y/w/h from resource file will fit on the available display
        d=QApplication.desktop()
        if self.x+self.w > d.width():
            self.x=50
        if self.y+self.h > d.height():
            self.y=50
        # try to use specified w and h; shrink if needed
        if self.x+self.w > d.width():
            self.w=d.availableGeometry(self).width()-100
        if self.y+self.h > d.height():
            self.h=d.availableGeometry(self).height()-100
        
		# debrief dialog (in case it is opened):
        # make sure x/y/w/h from resource file will fit on the available display
        if self.debriefX and self.debriefY and self.debriefW and self.debriefH:
            if self.debriefX+self.debriefW > d.width():
                self.debriefX=50
            if self.debriefY+self.debriefH > d.height():
                self.debriefY=50
            # try to use specified w and h; shrink if needed
            if self.debriefX+self.debriefW > d.width():
                self.debriefW=d.availableGeometry(self).width()-100
            if self.debriefY+self.debriefH > d.height():
                self.debriefH=d.availableGeometry(self).height()-100

        self.setGeometry(int(self.x),int(self.y),int(self.w),int(self.h))

        parser=argparse.ArgumentParser()
        parser.add_argument('mapID',nargs='?',default=None)        # optional incident map ID (#abcd or $abcd for now)
        parser.add_argument('debriefMapID',nargs='?',default=None) # optional debrief map ID (#abcd or $abcd for now)
        parser.add_argument('-sd','--syncdump',action='store_true',
                help='write a sync dump file containing every "since" response; for debug only; results in a LOT of files'),
        parser.add_argument('-cd','--cachedump',action='store_true',
                help='write a cache dump file after every "since" response; for debug only; results in a LOT of potentially HUGE files'),
        parser.add_argument('-nr','--norestore',action='store_true',
                help='do not try to restore the previous session, and do not ask the user')
        parser.add_argument('-nu','--nourl',action='store_true',
                help='disable all interactions with SARTopo/Caltopo')
        self.args=parser.parse_args()
        logging.info('args:'+str(self.args))

        self.readConfigFile()

        self.ui.incidentLinkLight.setStyleSheet(BG_GRAY)
        self.ui.debriefLinkLight.setStyleSheet(BG_GRAY)

        self.setAttribute(Qt.WA_DeleteOnClose) 
        self.medval = ""
        self.save_mod_date = 0
        self.assignments = []
        self.forceRescan = 0
        self.feature = {}
        self.feature2 = {}
        # self.setStyleSheet("background-color:#d6d6d6")
        self.ui.tableWidget.cellClicked.connect(self.tableCellClicked)        
        self.ui.OKbut.clicked.connect(self.assignTab_OK_clicked)
        self.ui.doOper.clicked.connect(self.doOperClicked)
        self.ui.incidentButton.clicked.connect(self.incidentButtonClicked)
        self.ui.debriefButton.clicked.connect(self.debriefButtonClicked)
        # self.screen().logicalDotsPerInchChanged.connect(self.lldpiChanged)
        self.reloaded = False
        self.incidentURL=None
        self.debriefURL=None
        
    # hardcode workarounds to avoid uncaught exceptions during save_data TMG 1-18-21
        self.watchedFile='watched.csv'
        self.watchedFile2='watched2.csv'
        self.offsetFileName='offset.csv'
        self.offsetFileName2='offset2.csv'
        self.csvFiles=[]
        self.csvFiles2=[]

        if os.path.exists(self.pcDataFileName):
            [i,d,n]=self.preview_saved_data()
            if not self.args.norestore:
                if not (i and n): # i and n are necessary; d is not
                    logging.info('Saved session file contained no useful data; not offering to restore')
                else:
                    iTxt='Incident map = '+str(i)
                    dTxt='No debrief map specified\n   (DMG failed or was not used)'
                    if d:
                        dTxt='Debrief map = '+str(d)+'\n   (DMG sync will resume if restored)'
                    nSuffix=''
                    if n!=1:
                        nSuffix='s'
                    nTxt=str(n)+' radiolog record'+nSuffix
                    if ask_user_to_confirm('Should the session be restored?\n\n'+iTxt+'\n'+dTxt+'\n'+nTxt,parent=self):
                    # name1, done1 = QtWidgets.QInputDialog.getText(self, 'Input Dialog','Should the session be restored?')
                    # if "y" in name1.lower():
                        self.load_data()
                        self.reloaded = True
        if not self.args.nourl and not self.reloaded:
            name1=self.args.mapID
            if name1:
                if "#" in name1:
                    self.incidentURL="https://caltopo.com/m/"+name1[1:]        # remove the #
                elif "$" in name1:
                    self.incidentURL="http://localhost:8080/m/"+name1[1:]     # remove the $
                else:    
                    self.incidentURL="http://192.168.1.20:8080/m/"+name1
            else:
                if not ask_user_to_confirm('If the map is at caltopo.com it must be in the NCSSAR account.\n  Continue?',parent=self):
                    pass   # abort
                    print("Exiting")
                    exit()
                self.incidentMapDialog=SpecifyMapDialog(self,'Incident',None,self.defaultDomainAndPort)
                self.incidentMapDialog.exec() # force modal
                self.incidentURL=self.incidentMapDialog.url
                self.incidentDomainAndPort=self.incidentMapDialog.domainAndPort
        self.cts=None
        self.dmg=None # DebriefMapGenerator instance
        self.link=-1
        self.latField = "0.0"
        self.lonField = "0.0"
        self.NCSO = [39.27, -121.026]
        self.sinceFolder=0 # caltopo wants integer milliseconds
        self.sinceMarker=0 # caltopo wants integer milliseconds
        self.markerList=[] # list of all caltopo markers and their ids
        

        # self.scl = min(self.w/self.wd, self.h/self.hd)
        # self.fontSize = int(self.fontSize*self.scl)
        # logging.info("Scale:"+str(self.scl))

        self.updateClock()

        
        if self.watchedDir:
            logging.info('watched dir:'+str(self.watchedDir))
            self.ui.notYet=QMessageBox(QMessageBox.Information,"Waiting...","No valid radiolog file was found.\nRe-scanning every few seconds...",
                        QMessageBox.Abort,self,Qt.WindowTitleHint|Qt.WindowCloseButtonHint|Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint|Qt.WindowStaysOnTopHint)
            self.ui.notYet.setStyleSheet("background-color: lightgray")
            self.ui.notYet.setModal(False)
            self.ui.notYet.show()
            self.ui.notYet.buttonClicked.connect(self.notYetButtonClicked)
            self.ui.rescanButton.clicked.connect(self.rescanButtonClicked)
            self.ui.printButton.clicked.connect(self.printButtonClicked)

            self.rescanTimer=QTimer(self)
            self.rescanTimer.timeout.connect(self.rescan)
            if not self.reloaded:
                self.rescanTimer.start(2000)     # do not start rescan timer if this is a reload
            else:
                self.ui.notYet.close()           # we have csv file in reload
        else:
            logging.info('No watched dir specified.')
        
                  
        self.refreshTimer=QTimer(self)
        self.refreshTimer.timeout.connect(self.refresh)
        self.refreshTimer.timeout.connect(self.updateClock)
        self.refreshTimer.start(3000)
        self.print_refresh = 0
        self.update_TmAs = 0
        self.update_Tm = 0
        self.flag_TmAs_getobj = False
        self.flag_TmAs_Ok = False

        self.since={}
        self.since["Folder"]=0
        self.since["Marker"]=0
        
        self.featureListDict={}
        self.featureListDict["Folder"]=[]
        self.featureListDict["Marker"]=[]

        self.ui.incidentMapField.setText('<None>')
        self.ui.debriefMapField.setText('<None>')

        if self.incidentURL:
            self.ui.incidentMapField.setText(self.incidentURL)
            self.tryAgain=True
            while self.tryAgain:
                self.createCTS()
        # check and create if not existing, line assignments for IC and TR to use as placeHolders for teams at IC or in transit
        try:
            assigns = self.cts.getFeatures('Assignment') 
            print("getting assignments for IC and TR, if they exist")
        except:
            pass   # if timeout then just return
        self.ICid = None
        self.TRid = None
        for x in assigns:
            if 'ICX' in x['properties']['title']:
                self.ICid = x['id']
                print('Found IC')
            if 'TR' in x['properties']['title']:
                self.TRid = x['id']
                print('Found TR')

        if self.ICid is None:
           self.ICid = self.cts.addLineAssignment(points=[[-120,39],[-120.01,39.01]], letter='ICX')
           print('created IC')   # named ICX to remove conflict with IC marker
        if self.TRid is None:
           self.TRid = self.cts.addLineAssignment(points=[[-120,39],[-120.01,39.01]], letter='TR')
           print('created TR')
        self.save_data()

        # if debrief map was specified both on command line and in restored file,
        #  then ignore so that the user will have to specify the debrief map in the GUI
        if self.debriefURL and self.args.debriefMapID:
            self.debriefMapID=None
            self.debriefURL=None

        if self.args.debriefMapID and self.link>-1:
            name2=self.args.debriefMapID
            if name2:
                if "#" in name2:
                    self.debriefURL="https://caltopo.com/m/"+name2[1:]        # remove the #
                elif "$" in name2:
                    self.debriefURL="http://localhost:8080/m/"+name2[1:]     # remove the $
                else:    
                    self.debriefURL="http://192.168.1.20:8080/m/"+name2


##### Temporarily removing debrief - using for printing
        ''' 
        if self.debriefURL:
            self.debriefButtonClicked()
            self.dmg.dd.ui.debriefMapField.setText(self.debriefURL)
            self.ui.debriefMapField.setText(self.debriefURL)
            QTimer.singleShot(1000,self.debriefButtonClicked) # raise again
        else:
            QTimer.singleShot(1000,self.debriefButtonClicked) # no reason not to start dmg anyway - TMG/SDL 4-9-22
       '''


    def printx(self):    #  printing clue table
        ###  needs a rescan to be sure up to date
        ##       presently rescan does not restore the radiolog and clue displays are correct
        from reportlab.lib.units import inch

        c = canvas.Canvas("report.pdf", pagesize=letter)
        # move the origin up and to the left
        c.translate(0.5*inch,inch)
        # define a font
        c.setFont("Helvetica", 8)
        # choose some colors
        c.setStrokeColorRGB(0,0,0)           ## color for lines
        c.setFillColorRGB(0.15,0.15,0.15)    ## color for text
        self.csvFiles2 = []        
        f2=glob.glob(self.watchedDir+"\\*.csv")
        f2x=[x for x in f2 if regex.match('.*_clueLog.csv$',x)]  # get cluelog files
        f2s=sorted(f2x,key=os.path.getmtime,reverse=True)
        for file in f2s:
            l=[file,os.path.getsize(file),os.path.getmtime(file)]
            self.csvFiles2.append(l)
        self.watchedFile2=self.csvFiles2[0][0]
        ioff = 0.1
        Entries = []
        if (self.watchedDir and self.csvFiles2!=[]):
          with open(self.watchedFile2, 'r') as fid:  
                lines = fid.readlines()
          newl = False   # set to not working a newline within a string
          for line in lines:      
              line, newl = self.fixStrg(line, newl)  # fix ' and newline in  string
              if newl:
                  continue     # in the middle of a multi-line description
              Entries.append(line.split(','))
          for entry in Entries:
            if len(entry)>8:
                entry=entry[:8]                 
            if len(entry)==8:
               ioff = ioff + 0.3
               clueNum,msg,callsign,time,d1,d2,radioLoc,status=entry
               c.drawString(0.05*inch, (8.5-ioff)*inch, clueNum)
               c.drawString(0.6*inch, (8.5-ioff)*inch, time)
               c.drawString(1.1*inch, (8.5-ioff)*inch, radioLoc)
               c.drawString(2.0*inch, (8.5-ioff)*inch, msg)
          c.drawString(0.05*inch, 8.8*inch, datetime.now().strftime("%a %b %d %Y %H:%M:%S"))     
          c.drawString(0.05*inch, (8.5)*inch, 'Cluenum   Time           Location              Message')
          c.showPage()
          # 2nd page
        if True:    # indent  
          # define a font
          c.translate(0.5*inch,inch)
          # define a font
          c.setFont("Helvetica", 8)
          # choose some colors
          c.setStrokeColorRGB(0,0,0)           ## color for lines
          c.setFillColorRGB(0.15,0.15,0.15)    ## color for text
          ioff = 0
          for itm2 in range(self.ui.tableWidget_TmAs.rowCount()): # data for team assignment table 
             ioff = ioff + 0.3
             team = self.ui.tableWidget_TmAs.item(itm2, 0).text()
             c.drawString(0.5*inch, (8.5-ioff)*inch, team)
             assign = self.ui.tableWidget_TmAs.item(itm2, 1).text()
             c.drawString(1.5*inch, (8.5-ioff)*inch, assign)
             type = self.ui.tableWidget_TmAs.item(itm2, 2).text()
             c.drawString(2.5*inch, (8.5-ioff)*inch, type)
             med = self.ui.tableWidget_TmAs.item(itm2, 3).text()
             if med != ' ':
                 med = 'Yes'
             c.drawString(3.5*inch, (8.5-ioff)*inch, med)
          c.drawString(0.05*inch, 8.8*inch, datetime.now().strftime("%a %b %d %Y %H:%M:%S"))     
          c.drawString(0.05*inch, (8.5)*inch, '          Team#               Assignment                         Type                     Medical')
          c.showPage()
 
        c.save()
        pdfx = subprocess.Popen(["C:/Program Files/Adobe/Acrobat DC/Acrobat/Acrobat.exe", "report.pdf"])

    def fixStrg(self, line, newl):
        lineX = line
        if newl:
            pass # reading next line as part of prior line; replace
                 # newline with /
            lineX = self.savel+lineX    # concatenate lines
            offset = len(self.savel)  # want to continue scan after nl replacement
            #newl = False         # reset newl mode until a possible next nl
            #print("LINE:"+str(self.savel)+":"+str(lineX)+"::")
        else:
            self.inStrg = False
            offset= 0
        #print("INTER:"+str(lineX)+":"+str(self.inStrg)+":"+str(newl)+":"+str(len(lineX)))    
        #
        #
        #  CHECK -1 removal............
        #
        for i in range(offset,len(lineX)): # -1):  # stop b4 last char  REMOVE comma in a string
                                              # also account for newline in a text string
            ##QQ print("ERROR:"+str(line)+":"+str(i))
            if lineX[i] == '"' or self.inStrg :
                #print("A:"+str(lineX[i])+":"+str(i))
                if lineX[i] == ',':
                    lineX = lineX[:i]+';'+lineX[i+1:]       # replace ',' in a string
                if lineX[i] == '\n' or (newl and i == len(lineX)-2):  # do not want to keep newline character
                    if lineX[i] == '\n':   # some lines appear to have the nl (get rid of)
                                           # others do not, so keep the character
                        j = 0
                    else:
                        j = 1
                    lineX = lineX[:i+j]+'/'       # replace 'nl' in a string OR last char w/o finding nl
                    #print("MOD:"+str(lineX)+":"+str(i))
                    self.savel = lineX
                    newl= True
                    self.inStrg = True
                    break     # at end of this line, get some more on next call
                elif lineX[i] == '"' and self.inStrg:
                    #print("END:"+str(i))
                    self.inStrg = False      # end of string
                    newl = False
                    continue 
                self.inStrg = True   # only done inside a string  getting

        return(lineX, newl)

    def createCTS(self):
        parse=self.incidentURL.replace("http://","").replace("https://","").split("/")
        domainAndPort=parse[0]
        mapID=parse[-1]
        syncDumpFile=None
        if self.args.syncdump:
            syncDumpFile='syncdump.'+mapID
            logging.info('Sync dump file will be written with the response to each "since" request; each filename will begin with '+syncDumpFile)
            syncDumpFile+='.txt'
        cacheDumpFile=None
        if self.args.cachedump:
            cacheDumpFile='cachedump.'+mapID
            logging.info('Cache dump file will be written after each "since" request; each filename will begin with '+cacheDumpFile)
            cacheDumpFile+='.txt'
        self.cts=None
        box=QMessageBox(
            QMessageBox.NoIcon, # other values cause the chime sound to play
            'Connecting...',
            'Incident Map:\n\nConnecting to '+self.incidentURL+'\n\nPlease wait...')
        box.setStandardButtons(QMessageBox.NoButton)
        box.show()
        QCoreApplication.processEvents()
        box.raise_()
        logging.info("Creating CaltopoSession with domainAndPort="+domainAndPort+" mapID="+mapID)
        try:
            if 'caltopo.com' in domainAndPort.lower():
                print("Account:"+str(self.accountName))
                self.cts=CaltopoSession(domainAndPort=domainAndPort,mapID=mapID,
                                        configpath=self.ctsconfigpath,
                                        account=self.accountName,
                                        sync=False,
                                        syncDumpFile=syncDumpFile,
                                        cacheDumpFile=cacheDumpFile,
                                        useFiddlerProxy=True)
            else:
                self.cts=CaltopoSession(domainAndPort=domainAndPort,mapID=mapID,sync=False,syncDumpFile=syncDumpFile,cacheDumpFile=cacheDumpFile,useFiddlerProxy=True, syncTimeout=30)
            self.link=self.cts.apiVersion
        except Exception as e:
            logging.warning('Exception during createCTS:\n'+str(e))
            self.link=-1
        finally:
            box.done(0)
        if self.link>-1:
            logging.info('Successfully connected.')
            self.ui.incidentLinkLight.setStyleSheet(BG_GREEN)
            if not self.reloaded:  
                self.getObjects()
            '''
            #Z1
            else:
                pass
                ####self.rescan()   #QQ   ## Do a rescan here to get info updated after a reload
            '''    
            self.tryAgain=False
        else:
            logging.info('Connection failed.')
            self.ui.incidentLinkLight.setStyleSheet(BG_RED)
            inform_user_about_issue('Link could not be established with specified incident map\n\n'+self.incidentURL+'\n\nPlease specify a valid map, or hit Cancel from the map dialog to run Plans Console with no incident map.',parent=self)
            self.incidentMapDialog=SpecifyMapDialog(self,'Incident',None,domainAndPort)
            if self.incidentMapDialog.exec(): # force modal
                self.ui.incidentMapField.setText(self.incidentMapDialog.url)
                self.ui.incidentLinkLight.setStyleSheet(BG_GRAY)
                self.incidentURL=self.incidentMapDialog.url
                self.incidentDomainAndPort=self.incidentMapDialog.domainAndPort
                if not self.incidentURL:
                    self.tryAgain=False
            else:
                self.tryAgain=False                 

    def getObjects(self):   # run when the map has NOT been reloaded OR needs to be updated
        pass                # look at map to get features to load into the assignment table
        print("Loading assignment table from map")
        #  get Medical marker information
        try:
            medMarkers=[f for f in self.cts.getFeatures('Marker') if f['properties'].get('marker-symbol','') == 'medevac-site']
            print("updating markers")
        except:
            return   # if timeout then just return
        #  get assignments with teams(s) assigned
        try:
            assignmentsWithNumber=[f for f in self.cts.getFeatures('Assignment') if f['properties'].get('number','') != '']
            print("updating assignments with teams")
        except:
            return   # if timeout then just return
        #   Need to parse title to get assignemnt and each team #
        l = []   # init list of entries
        for a in assignmentsWithNumber:
            s = re.sub(' +', ' ',a['properties']['title'].strip())   # split at space or comma or slash (get assignment & teams)
            s = re.split(r'[ ,/]', s)   # split at space or comma or slash (get assignment & teams)
            #s = re.split(r'[ ,/]', a['properties']['title'].strip())   # split at space or comma or slash (get assignment & teams)
            print("####### "+str(s)+"::"+str(a['properties']['title'].strip())+"::")
            # pop warning message that Assignment does not exist - skipping
            if s[0] == '' and self.FIRST_PASS:    # no assignment or assignment is in number (team) field
                inform_user_about_issue("Mostlikely Assignment name, "+str(s[1])+", is in the number field, skipping")
                continue
            scnt = len(s)
            #$#if self.flag == 1:
            #$#    scnt = min(scnt,2)
            for k in range(0, scnt-1):   # run thru team numbers (or LE callsign)
                if len(s[k+1]) >= 3 and (s[k+1][0].isdigit() and s[k+1][1].isalpha() and s[k+1][2].isdigit()):  # 2nd char is a digit, not LE
                    x = 'LE'
                else:
                    x = a['properties']['resourceType']
                Med = False    
                for m in medMarkers:
                    #print("Med Info Chk:"+str(m)+":"+str(s[k+1]+s[0]))
                    #if m['properties']['title'] == s[k+1] and m['properties']['description'] == s[0]:   #OLD team# was displayed on the map
                    if m['properties']['title'] == s[k+1] and m['properties']['description'] == s[k+1]+s[0]:
                       #print("Found") 
                       Med = True          #  will get Medical info from the Marker
                if Med: self.medval = " X"
                else: self.medval = " "    #  need at least a space so that it is not empty
 
                l.append([s[k+1], s[0], x, self.medval])
                l.sort(key = lambda g: g[0], reverse = True)   # sort by 1st element, team #
        self.FIRST_PASS = False   # set after first time thru so that warning above is only given once
        for el in l:
                   self.ui.tableWidget_TmAs.insertRow(0)
                   self.ui.tableWidget_TmAs.setItem(0, 0, QtWidgets.QTableWidgetItem(el[0]))
                   self.ui.tableWidget_TmAs.setItem(0, 1, QtWidgets.QTableWidgetItem(el[1]))    
                   self.ui.tableWidget_TmAs.setItem(0, 2, QtWidgets.QTableWidgetItem(el[2]))
                   self.ui.tableWidget_TmAs.setItem(0, 3, QtWidgets.QTableWidgetItem(el[3]))

        #     set type to Unk if not type is unknown from map info

    def addMarker(self):
        folders=self.cts.getFeatures("Folder")
        self.fidX = True    # set to something other than None for following test
        if not folders:
            self.fidX = self.cts.addFolder("X")   # add unused folder for following test
            print("StatusAddFolder"+str(self.fidX))
        if self.fidX == None:   # could not add    
            inform_user_about_issue("Mostlikely this session is not connected to the map for write access. Check that the proper account is being used.")
            return
        logging.info('addMarker folders:'+str(folders))
        fid=False   # used to help get display of first marker of type Med or LE, see below
        for folder in folders:
            if folder["properties"]["title"]=="Medical":
                self.fidMed=folder["id"]
                fid = True     # use here or below?
            if folder["properties"]["title"]=="LE":
                self.fidLE=folder["id"]
                fid = True     # use here or below?
        #if not self.fidMed:
        #    self.fidMed = self.cts.addFolder("Medical")
        #if not self.fidLE:
        #    self.fidLE = self.cts.addFolder("LE")
        ## icons
        if self.medval == " X":
            if not self.fidMed:
                self.fidMed = self.cts.addFolder("Medical")
                fid = True
            markr = "medevac-site"     # medical +
            clr = "FF0000"
            #rval=self.cts.addMarker(self.latField,self.lonField,self.curTeam,self.curAssign, \  # OLD: team# was displayed on the map
            rval=self.cts.addMarker(self.latField,self.lonField,self.curTeam,self.curTeam+self.curAssign, \
                                            clr,markr,None,self.fidMed)
            if fid:                  # temporary fix   NOW (10/25/2023) does not seem to help
              print("At reADD marker")
              time.sleep(4)          # the delay, delete and redo seems to get display of marker
              self.delMarker()       # removes most recent
              rval=self.cts.addMarker(self.latField,self.lonField,self.curTeam,self.curTeam+self.curAssign, \
                                            clr,markr,None,self.fidMed)
        elif self.curType == "LE":     # law enforcement
            if not self.fidLE:
                self.fidLE = self.cts.addFolder("LE")
                fid = True
            markr = "icon-ERJ4011P-24-0.5-0.5-ff"     # red dot with blue circle
            clr = "FF0000"           
            rval=self.cts.addMarker(self.latField,self.lonField,self.curTeam, \
                                    self.curAssign,clr,markr,None,self.fidLE)
            if fid:                  # temporary fix   NOW (10/25/2023) does not seem to help
              print("At reADD marker")
              time.sleep(4)          # the delay, delete and redo seems to get display of marker
              self.delMarker()
              rval=self.cts.addMarker(self.latField,self.lonField,self.curTeam, \
                                     self.curAssign,clr,markr,None,self.fidLE)
        else:
            pass #X# don't place marker for searcher
            #X# markr = "hiking"       # default 
            #X# clr = "FFFF00"
            rval = "X"   # place holder
        logging.info("In addMarker:"+self.curTeam)    
        ## also add team number to assignment
        rval2 = self.cts.mapData['state']['features']
        numbr = ""
        for props in rval2:
            lettr = props['properties'].get('letter')
            if lettr is None:  continue
            print("PROPS:"+str(self.curAssign)+":"+str(lettr))
            if lettr == self.curAssign:
                numbr = props['properties'].get('number')
                break
        if numbr == '' or numbr is None:
            numbr = self.curTeam
        else:
            print("NUMBER:"+str(numbr)+":"+str(self.curTeam))
            numbr += " "+self.curTeam  #  set the team# and resource from table entry  
        assign = self.curAssign.upper()    
        if assign == 'IC':
            assign = 'ICX'  # using ICX to avoid conflict with IC marker
        rval2=self.cts.editFeature(className='Assignment', letter=assign, properties={'number':numbr, \
                                   'resourceType':self.curType})
        if rval2 == False:
            inform_user_about_issue('Could not edit map object, probably do not have access to EDIT this map.',parent=self)
        logging.info("RVAL rtn:"+str(rval)+' : '+str(rval2))


    
    def delMarker(self):
        rval = self.cts.getFeatures("Folder")     # get Folders
        rval2 = self.cts.getFeatures("Marker")
        ##print("Folders:"+json.dumps(rval))
        fidLE = None
        fidMed = None
        for self.feature2 in rval:
            if self.feature2['properties'].get("title") == 'LE':   # find LE folder Match                
                fidLE=self.feature2.get("id")
            if self.feature2['properties'].get("title") == 'Medical':   # find Medical folder Match                
                fidMed=self.feature2.get("id")
            if fidLE != None or fidMed != None:    
                logging.info("id:"+str(fidLE))
                ##print("Marker:"+json.dumps(rval2))                  
                # get Markers
                for self.feature2 in rval2:
                    if (self.feature2['properties'].get('folderId') == fidLE or self.feature2['properties'].get('folderId') == fidMed) and \
                        self.feature2['properties'].get('title').upper() == self.curTeam.upper(): # both folder and Team match
                            logging.info("Marker ID:"+self.feature2['id']+" of team: "+self.curTeam)
                            rval3 = self.cts.delMarker(self.feature2['id'])

        # remove the team number from any assignments that contain it
        assignmentsWithThisNumber=[f for f in self.cts.getFeatures('Assignment') if self.curTeam.upper() in f['properties'].get('number','').upper()]
        for a in assignmentsWithThisNumber:
            n=a['properties']['number']
            pe=a['properties']['previousEfforts']
            logging.info('changing assignment "'+a['properties']['title']+'": old number = "'+n+'"')
            nList=n.upper().split()
            if self.curTeam.upper() in nList:
                nList.remove(self.curTeam.upper())
            else:
                return
            n=' '.join(nList)
            logging.info('  new number = "'+n+'"')
            pe += ' T'+self.curTeam+datetime.now().strftime("-%d%b%y_%H%M")                # append info to previousEfforts field
            try:
                self.cts.editFeature(id=a['id'],properties={'number':n,'previousEfforts':pe})  # removes team# from assignment
            except:
                time.sleep(2)  # wait 2 seconds and retry
                try:
                    self.cts.editFeature(id=a['id'],properties={'number':n,'previousEfforts':pe})  # removes team# from assignment
                except:
                    logging.error("Could not connect to Caltopo, please retry request")
                    return
###@@@@###            
        ##print("RestDel:"+json.dumps(rval3,indent=2))
        # check for Medical marker and also remove
        if self.ui.Med.isChecked(): 
            pass # remove marker from map and from Medical folder
            for md in rval:
                if md['properties'].get("title") == 'Medical': # find Medical folder match
                    fid = md.get('id')
                    for md in rval2:      # match both folder and Team
                        if md['properties'].get('folderId') == fid and md['properties'].get('title').upper() == self.curTeam.upper():
                            rval4 = self.cts.delMarker(md['id'])
             
##   APPEARS to not be used
    def updateFeatureList(self,featureClass,filterFolderId=None):
        # unfiltered feature list should be kept as an object;
        #  filtered feature list (i.e. combobox items) should be recalculated here on each call 
        logging.info("updateFeatureList called: "+featureClass+"  filterFolderId="+str(filterFolderId))
        if self.cts and self.link>0:
            rval=self.cts.getFeatures(featureClass,self.since[featureClass])
            self.since[featureClass]=int(time.time()*1000) # caltopo wants integer milliseconds
            logging.info("At cts check")
            if rval:
                logging.info("rval:"+str(rval))
                for feature in rval:
                    for oldFeature in self.featureListDict[featureClass]:
                        if feature["id"]==oldFeature["id"]:
                            self.featureListDict[featureClass].remove(oldFeature)
                    self.featureListDict[featureClass].append(feature)
                self.featureListDict[featureClass].sort(key=sortByTitle)
                
            # recreate the filtered list regardless of whether there were new features in rval    
            items=[]
            for feature in self.featureListDict[featureClass]:
                id=feature.get("id",0)
                prop=feature.get("properties",{})
                name=prop.get("title","UNNAMED")
                add=True
                if filterFolderId:
                    fid=prop.get("folderId",0)
                    if fid!=filterFolderId:
                        add=False
                        logging.info("      filtering out feature:"+str(id))
                if add:
                    logging.info("    adding feature:"+str(id))
                    if featureClass=="Folder":
                        items.append([name,id])
                    else:
                        items.append([name,[id,prop]])
            else:
                logging.info("no return data, i.e. no new features of this class since the last check")
        else:
            logging.info("No map link has been established yet.  Could not get Folder features.")
            self.featureListDict[featureClass]=[]
            self.since[featureClass]=0
            items=[]
        logging.info("  unfiltered list:"+str(self.featureListDict[featureClass]))
        logging.info("  filtered list:"+str(items))
        
    def readConfigFile(self):
        # create the file (and its directory) if it doesn't already exist
        dir=os.path.dirname(self.configFileName)
        if not os.path.exists(self.configFileName):
            logging.info("Config file "+self.configFileName+" not found.")
            if not os.path.isdir(dir):
                try:
                    logging.info("Creating config dir "+dir)
                    os.makedirs(dir)
                except:
                    logging.error("ERROR creating directory "+dir+" for config file.")
            try:
                defaultConfigFileName=os.path.join(os.path.dirname(os.path.realpath(__file__)),"default.cfg")
                logging.info("Copying default config file "+defaultConfigFileName+" to "+self.configFileName)
                shutil.copyfile(defaultConfigFileName,self.configFileName)
            except:
                logging.error("ERROR copying the default config file to the local config path.")
                
        # specify defaults here
        # self.watchedDir="Z:\\"
        
        logging.info(' Reading config file '+self.configFileName)
        # configFile=QFile(self.configFileName)
        self.config=configparser.ConfigParser()
        self.config.read(self.configFileName)
        if 'Plans_console' not in self.config.sections():

        # if not configFile.open(QFile.ReadOnly|QFile.Text):
        #     warn=QMessageBox(QMessageBox.Warning,"Error","Cannot read configuration file " + self.configFileName + "; using default settings. "+configFile.errorString(),
        #                     QMessageBox.Ok,self,Qt.WindowTitleHint|Qt.WindowCloseButtonHint|Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint|Qt.WindowStaysOnTopHint)
        #     warn.show()
        #     warn.raise_()
        #     warn.exec_()
        #     return
        # inStr=QTextStream(configFile)
        # line=inStr.readLine()
        # if line!="[Plans_console]":
            warn=QMessageBox(QMessageBox.Warning,"Error","Specified configuration file " + self.configFileName + " is not a valid configuration file; using default settings.",
                            QMessageBox.Ok,self,Qt.WindowTitleHint|Qt.WindowCloseButtonHint|Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint|Qt.WindowStaysOnTopHint)
            warn.show()
            warn.raise_()
            warn.exec_()
        #     configFile.close()
            return

        # read individual settings, with defaults
        cpc=self.config['Plans_console']
        self.watchedDir=cpc.get('watchedDir','"Z:\\"')
        self.accountName=cpc.get('accountName',None)
        self.defaultDomainAndPort=cpc.get('defaultDomainAndPort',None)

        # while not inStr.atEnd():
        #     line=inStr.readLine()
        #     tokens=line.split("=")
        #     if tokens[0]=="watchedDir":
        #         self.watchedDir=tokens[1]
        #         print("watchedDir specification "+self.watchedDir+" parsed from config file.")
        # configFile.close()
        
        # validation and post-processing of each item
        configErr=""

        # validate watchedDir
        if self.watchedDir=='None':
            self.watchedDir=None
        else:
            # process any ~ characters
            self.watchedDir=os.path.expanduser(self.watchedDir)
            if not os.path.isdir(self.watchedDir):
                configErr+="WARNING: specified watchedDir '"+self.watchedDir+"' does not exist.\n"
                configErr+="  Radiolog traffic will not be monitored.\n\n"

        if configErr:
            self.configErrMsgBox=QMessageBox(QMessageBox.Warning,"Non-fatal Configuration Error(s)","Error(s) encountered in config file "+self.configFileName+":\n\n"+configErr,
                             QMessageBox.Ok,self,Qt.WindowTitleHint|Qt.WindowCloseButtonHint|Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint|Qt.WindowStaysOnTopHint)
            self.configErrMsgBox.exec_()

    def notYetButtonClicked(self):
        # exit()
        self.rescanTimer.stop()

    
    def doOperClicked(self):  # map editor functions
        # eventually, we can use CTSFeatureComboBox to allow autocomplete on each feature name;
        #  that will also do an immediate cache refresh when the fields are opened; until then,
        #  we can force an immediate refresh now, when the button is clicked.
        self.cts._refresh(forceImmediate=True)
        op=self.ui.geomOpButtonGroup.checkedButton().text()
        selFeatureTitle=self.ui.selFeature.text()
        ## check that the shapes exist
        selFeatures=self.cts.getFeatures(title=selFeatureTitle,featureClassExcludeList=['Folder','OperationalPeriod'], allowMultiTitleMatch=True)
        selFeature=self.cts.getFeature(title=selFeatureTitle,featureClassExcludeList=['Folder','OperationalPeriod'])
        ##if selFeature == -1:
        if len(selFeatures) > 1:    
            logging.warning(op+' operation failed: Selected feature "'+selFeatureTitle+'" has an issue.')
            inform_user_about_issue(op+' operation failed:\n\nThere are more than one feature with the name "'+selFeatureTitle+'"')
            return
        if not selFeature:
            logging.warning(op+' operation failed: Selected feature "'+selFeatureTitle+'" has an issue.')
            inform_user_about_issue(op+' operation failed:\n\nSelected feature "'+selFeatureTitle+'" not found.')
            return
        editorFeatureTitle=self.ui.editorFeature.text()
        editorFeatures=self.cts.getFeatures(title=editorFeatureTitle,featureClassExcludeList=['Folder','OperationalPeriod'], allowMultiTitleMatch=True)
        editorFeature=self.cts.getFeature(title=editorFeatureTitle,featureClassExcludeList=['Folder','OperationalPeriod'])
        ##if editorFeature == -1:
        if len(editorFeatures) > 1:    
            logging.warning(op+' operation failed: Editor feature "'+selFeatureTitle+'" has an issue.')
            inform_user_about_issue(op+' operation failed:\n\nThere are more than one feature with the name "'+editorFeatureTitle+'"')
            return
        if not editorFeature:
            logging.warning(op+' operation failed: Editor feature "'+editorFeatureTitle+'" not found.')
            inform_user_about_issue(op+' operation failed:\n\nEditor feature "'+editorFeatureTitle+'" not found.')
            return
        logging.info("%s shape %s with feature %s"%(op,selFeature,editorFeature))
        if op=='Cut':
            #print("AT CUT")
            if not self.cts.cut(selFeature,editorFeature):
               print("F A I L E D")   # #A#
               logging.warning(op+' operation failed.')
               inform_user_about_issue(op+' operation failed.\n\nSee log file for details.')
               return
        elif op=='Expand':
            if not self.cts.expand(selFeature,editorFeature):
               logging.warning(op+' operation failed.')
               inform_user_about_issue(op+' operation failed.\n\nSee log file for details.')
               return
        elif op=='Crop':    
            if not self.cts.crop(selFeature,editorFeature,deleteBoundary=True):
               logging.warning(op+' operation failed.')
               inform_user_about_issue(op+' operation failed.\n\nSee log file for details.')
               return
        else:
            logging.error('Unknown geometry operation "'+str(op)+'" specified.  No geometry operation performed.')

    # def BEEP(self):
    #     for n in range(2):
    #         winsound.Beep(2500, 100)  ## BEEP, 2500Hz for 1 second
    #         #time.sleep(0.25)

    def incidentButtonClicked(self):
        # if a map was already open, ask for confirmation first
        if self.cts and self.cts.apiVersion>-1:
            really=ask_user_to_confirm('An incident map is already open.  Do you really want to specify a different incident map?')
            if not really:
                return
        self.tryAgain=True
        self.incidentMapDialog=SpecifyMapDialog(self,'Incident',None,self.defaultDomainAndPort)
        if self.incidentMapDialog.exec(): # force modal
            self.ui.incidentMapField.setText(self.incidentMapDialog.url)
            self.ui.incidentLinkLight.setStyleSheet(BG_GRAY)
            self.incidentURL=self.incidentMapDialog.url
            self.incidentDomainAndPort=self.incidentMapDialog.domainAndPort
            self.createCTS()
        else: # don't change the incident map if dialog is canceled
            self.tryAgain=False


    def printButtonClicked(self):
        print("Printing.....")
        self.printx()


    def debriefButtonClicked(self):
        if not self.cts or self.cts.apiVersion<0:
            inform_user_about_issue('You must establish a link with the Incident Map first.',parent=self)
        else:
            if not self.dmg:
                self.dmg=DebriefMapGenerator(self,self.cts,self.debriefURL)
            self.save_data()
            if self.dmg and self.dmg.cts2 and self.dmg.cts2.apiVersion>=0:
                if self.debriefX and self.debriefY and self.debriefW and self.debriefH:
                    self.dmg.dd.setGeometry(int(self.debriefX),int(self.debriefY),int(self.debriefW),int(self.debriefH))
                self.dmg.dd.show()
                self.dmg.dd.raise_()
            else:
                self.ui.debriefMapField.setText('<None>')
                del self.dmg
                self.dmg=None # so that the next debrief button click will try again

    def rescanButtonClicked(self):
        self.forceRescan = 1
        self.rescan()    #force a rescan/refresh
            
    def rescan(self):      # appears to RELOAD all radiolog data in the .csv file (not just the added entries as done in refresh)
        logging.info("scanning "+self.watchedDir+" for latest valid csv file...")
        self.csvFiles=[]      # csvFiles is the main radiolog table
        self.csvFiles2=[]     # csvFiles2 is the clue table
        self.readDir()
        #
        #  added section for self.csvFiles2
        #
        if self.csvFiles!=[]:
            self.rescanTimer.stop()
            self.ui.notYet.close()
            self.watchedFile=self.csvFiles[0][0]
            self.setWindowTitle("Plans_console - "+os.path.basename(self.watchedFile)+"  Version "+VERSION)
            # remove the pygtail offset file, if any, so pygtail will
            #  read from the beginning even if this file has already
            #  been read by pygtail
            self.offsetFileName=self.watchedFile+".offset"+str(os.getpid())
            if os.path.isfile(self.offsetFileName):
                os.remove(self.offsetFileName)
            logging.info("  found "+self.watchedFile)
            self.get_data()   # get saved data to set color
            #self.refresh()
        if self.csvFiles2!=[]:
            self.rescanTimer.stop()
            self.ui.notYet.close()
            self.watchedFile2=self.csvFiles2[0][0]
            # remove the pygtail offset file, if any, so pygtail will
            #  read from the beginning even if this file has already
            #  been read by pygtail
            self.offsetFileName2=self.watchedFile2+".offset"+str(os.getpid())
            if os.path.isfile(self.offsetFileName2):
                os.remove(self.offsetFileName2)
            logging.info("  found "+self.watchedFile2)
            #self.refresh()
        if (self.csvFiles!=[] or self.csvFiles2!=[]) and self.link > -1:  # chk that csvfiles exist and that map is connected
            self.forceRescan = 1   #QQ      ### clear rows by setting to no rows
            self.refresh()
        else:
            inform_user_about_issue("Mostlikely the Radiolog data or the Caltopo map cannot be accessed")


    # refresh - this is the main radiolog and caltopo map viewing loop
    #  - read any new lines from the log file
    #  - process each new line
    #    - add a row to the appropriate panel's table    
    def refresh(self):
        if self.update_Tm == 200:    # 10 minutes    ## why is there a rescan timeout???
               # maybe do this, but reset timeout if activity (refresh w/new data) has occurred??
            logging.info("Calling rescan timeout...")
            self.update_Tm = 0
            self.rescan()
        self.update_Tm += 1
        if self.print_refresh == 20:    # does this do anything??
            logging.info("Refreshing print...")
            self.print_refresh = 0
        self.print_refresh += 1
        ##
        # updating the team/assignment table
        ##
        if self.update_TmAs == 4:
            while self.flag_TmAs_Ok:    # wait until Ok button operation is complete
                pass
            self.flag_TmAs_getobj = True
            logging.info("Refreshing...")
            self.update_TmAs = 0
            rC = self.ui.tableWidget_TmAs.rowCount()
            for i in range(rC-1,-1,-1):  # appears to clear table when run in reverse
                self.curAssign = self.ui.tableWidget_TmAs.item(i,1).text().upper()
                #S#if self.curAssign not in ["TR", "IC"]:   # keep these entries; they do not have assignments on map
                #S#    self.ui.tableWidget_TmAs.removeRow(i)
                self.ui.tableWidget_TmAs.removeRow(i)
            self.getObjects()       # read objects on the map and update the table
            self.flag_TmAs_getobj = False
            ## look for multiple entries for a given team. If so, pop up a warning
            fnd = []
            resend = []
            for itm in range(self.ui.tableWidget_TmAs.rowCount()):    # look for team in multiple assignments
                d = self.ui.tableWidget_TmAs.item(itm, 0).text()
                if d.upper() not in fnd:              # add team# to queue on first appearance
                    fnd.append(d.upper())
                else:
                    resend.append(d.upper())
                    if d.upper() not in self.sentMsg:   # only put up message once
                       self.sentMsg.append(d.upper())
                       msg = 'Team '+str(d)+' is in multiple assignments'
                       inform_user_about_issue(msg, title="Warning")
            for itm in self.sentMsg:
                if itm not in resend:
                    self.sentMsg.remove(itm)         # if team# count has been corrected, elim from sentMsg
        self.update_TmAs += 1
        ##
        #    updating the radiolog listing table
        ##
        if (self.watchedDir and (self.csvFiles!=[] or self.csvFiles2!=[])):
            newEntries, newEntries2=self.readWatchedFile()
            #
            #  add newEntries section
            #
            if newEntries:   ## Only adding new entries, not overridding previous entries
                self.update_Tm = 0   # reset timeout since we got new data
                #Z1ix = 0
                #Zirow = 0     #QQ top row
                #Z1self.totalRows = 0 #QQ
                if self.forceRescan == 1:   #QQ      ### clear rows by setting to no rows
                    self.ui.tableWidget.setRowCount(0) #QQ
                    #  if forced, previous rows will be reloaded.  So, we need to get their prior color
                    #  therefore, need to correlate the saved file info with lines in watchedFile (oldest lines)
                    #  Should be able to compare the first line in saved data with lines from watchedFile.  When it
                    #     matches pickup at least the color (maybe all data) from the saved file
                    #  Can do match on watchedFile[0, 2 and 3] and savedFile[0, 1 and 2]
                logging.info("Num entries:"+str(len(newEntries))) 
                prev_entry = ''    
                fndMatch = False   # looking for savedData match to entry in watchedFile
                savedRow = 0       # initialize
                for entry in newEntries:
                    irow = 0       # forcing to 0 keeps the most recent at the top #QQ
                    logging.info("In loop: %s"% entry)
                    #14: get rid of any elements after 10 (e.g. 11 = operator ID - not needed here)
                    if len(entry)>10:
                        entry=entry[:10]                 
                    if len(entry)==10:
                        '''
                        #Z1
                        if self.forceRescan == 1:
                            logging.info("AT force rescan")   # question if this actually gets used
                            if ix < self.totalRows:
                                ix = ix + 1
                                continue    # skip rows until get to new rows
                        '''
                        timex,tf,callsign,msg,radioLoc,status,epoch,d1,d2,d3=entry  # values in watchedFile
                        logging.info("ENTRY:"+str(timex)+":"+str(callsign))
                        ##  'time' 'callsign' 'msg' 'radioLoc' 'status' 'color'       values in save file

                        if msg.find('Radio Log Begins') > -1:    
                            logging.info('Entry with RADIO LOG BEGINS skipped.')
                        else:
                            if prev_entry == entry:
                                continue       # skip as must have been a hiccup
                            self.ui.tableWidget.insertRow(irow)
                            self.ui.tableWidget.setItem(irow, 0, QtWidgets.QTableWidgetItem(timex))
                            self.ui.tableWidget.setItem(irow, 1, QtWidgets.QTableWidgetItem(callsign))    
                            self.ui.tableWidget.setItem(irow, 2, QtWidgets.QTableWidgetItem(msg))    
                            self.ui.tableWidget.setItem(irow, 3, QtWidgets.QTableWidgetItem(radioLoc))    
                            self.ui.tableWidget.setItem(irow, 4, QtWidgets.QTableWidgetItem(status))    
                            if self.savedData and self.forceRescan:    # implies there was prior stored data to use
                                logging.info("DATA:"+str(self.savedData[savedRow][0])+":"+str(timex)+":"+str(self.savedData[savedRow][1]) \
                                            +":"+str(callsign)+":"+str(self.savedData[savedRow][2])+":"+str(msg))
                                if (self.savedData[0][0] == timex and self.savedData[0][1] == callsign and self.savedData[0][2] == msg) \
                                    or fndMatch:
                                    logging.info("In match check")    
                                    self.setRowColor(self.ui.tableWidget,irow,self.savedData[savedRow][3])
                                    if self.savedData[savedRow][0] != timex or self.savedData[savedRow][1] != callsign or  \
                                        self.savedData[savedRow][2] != msg:
                                            logging.error("Row "+str(savedRow)+" does not match corresponding row in watchedFile")
                                    savedRow += 1      # get ready for next row
                                    fndMatch = True    # found first matched row
                                    # may want to get data from the savedData as well as the color (but not doing it now)
                            else:
                                prevColor=self.ui.tableWidget.item(irow,1).background().color().name()
                                newColor=stateColorDict.get(prevColor,self.color[0])
                                self.setRowColor(self.ui.tableWidget,irow,newColor)
                            logging.info("status:"+status+"  color:"+statusColorDict.get(status,["eeeeee",""])[0])
                            ##irow = irow + 1   #QQ
                            prev_entry = entry
                    else:
                        logging.info('Entry with '+str(len(entry))+' element(s) skipped.')
                self.totalRows = self.ui.tableWidget.rowCount()
                if self.savedData and self.forceRescan and not fndMatch:
                    logging.error("Did not find match in savedData and watchedFile information")
            if newEntries2:
                self.update_Tm = 0   # reset timeout since we got new data
                #Z1ix = 0
                #Zirow = 0    #QQ
                #Z1self.totalRows2 = 0 #QQ
                if self.forceRescan == 1:   #QQ   ### clear rows by setting to no rows
                    # for clue log could do this for normal rescan in that we do not have marking of already 
                    #    reviewed rows as for radiolog lines
                    self.ui.tableWidget_2.setRowCount(0) #QQ
                for entry in newEntries2:
                    irow = 0       # forcing to 0 keeps the most recent at the top #QQ
                    #logging.info("In loop2: %s"% entry)
                    #14: get rid of any elements after 8 (e.g. 11 = operator ID - not needed here)
                    if len(entry)>8:
                        entry=entry[:8]                 
                    if len(entry)==8:
                        '''
                        #Z1
                        if self.forceRescan == 1:
                            logging.info("AT force rescan2")   # question if this actually gets used)
                            if ix < self.totalRows2:
                                ix = ix + 1
                                continue    # skip rows until get to new rows
                        '''        
                        clueNum,msg,callsign,timex,d1,d2,radioLoc,status=entry
                        if msg.find('Radio Log Begins') > -1:    
                            logging.info('Entry with Radio Log Begins skipped.')
                        else:
                            self.ui.tableWidget_2.insertRow(irow)
                            self.ui.tableWidget_2.setItem(irow, 0, QtWidgets.QTableWidgetItem(clueNum))
                            self.ui.tableWidget_2.setItem(irow, 1, QtWidgets.QTableWidgetItem(timex))    
                            self.ui.tableWidget_2.setItem(irow, 2, QtWidgets.QTableWidgetItem(radioLoc))    
                            self.ui.tableWidget_2.setItem(irow, 3, QtWidgets.QTableWidgetItem(msg))    
                            prevColor=self.ui.tableWidget_2.item(irow,1).background().color().name()
                            newColor=stateColorDict.get(prevColor,self.color[0])  # clue rows do not change color if clicked
                            self.setRowColor(self.ui.tableWidget_2,irow,newColor)
                            #logging.info("status2:"+status+"  color:"+statusColorDict.get(status,["eeeeee",""])[0])
                            #Zirow = irow + 1 #QQ
                    else:
                        logging.info('Entry with '+str(len(entry))+' element(s) skipped.')
                self.totalRows2 = self.ui.tableWidget_2.rowCount()
                        
## save data
            if newEntries2 or newEntries:
                self.save_data()            
            self.forceRescan = 0

    def save_data(self):  
        # logging.info("In savedata")
        data1 = {}
        rowx = {}
        rowy = {}
        rowz = {}
        for itm in range(self.ui.tableWidget.rowCount()): # data for radiolog table
            data1['time'] = self.ui.tableWidget.item(itm, 0).text()
            data1['callsign'] = self.ui.tableWidget.item(itm, 1).text()
            data1['msg'] = self.ui.tableWidget.item(itm, 2).text()
            data1['radioLoc'] = self.ui.tableWidget.item(itm, 3).text()
            data1['status'] = self.ui.tableWidget.item(itm, 4).text()
            data1['color'] = self.ui.tableWidget.item(itm,1).background().color().name()
            rowx['rowA'+str(itm)] = data1.copy()
        for itm2 in range(self.ui.tableWidget_TmAs.rowCount()): # data for team assignment table 
            data1.update({'team': self.ui.tableWidget_TmAs.item(itm2, 0).text()})
            data1.update({'assign': self.ui.tableWidget_TmAs.item(itm2, 1).text()})
            data1.update({'type': self.ui.tableWidget_TmAs.item(itm2, 2).text()})
            data1.update({'med': self.ui.tableWidget_TmAs.item(itm2, 3).text()})
            rowy['rowB'+str(itm2)] = data1.copy()
        for itm3 in range(self.ui.tableWidget_2.rowCount()): # data for cluelog table
            data1.update({'clueNum': self.ui.tableWidget_2.item(itm3, 0).text()})
            data1.update({'time': self.ui.tableWidget_2.item(itm3, 1).text()})
            data1.update({'radioLoc': self.ui.tableWidget_2.item(itm3, 2).text()})
            data1.update({'msg': self.ui.tableWidget_2.item(itm3, 3).text()})
            data1.update({'color': self.ui.tableWidget_2.item(itm3,1).background().color().name()}) # doesn't matter - not clickable
            rowz['rowC'+str(itm3)] = data1.copy()
        
        maps={}
        maps['incidentURL']=self.incidentURL
        if self.dmg and self.dmg.cts2 and self.dmg.cts2.apiVersion>=0:
            maps['debriefURL']=self.debriefURL
        alld = json.dumps([maps,{'csv':self.watchedFile+'%'+self.offsetFileName+'%'+str(self.csvFiles)+\
                '%'+self.watchedFile2+'%'+self.offsetFileName2+'%'+str(self.csvFiles2)},\
                rowx, rowy, rowz])     
        fid = open(self.pcDataFileName,'w')
        fid.write(alld)
        fid.close()

    def preview_saved_data(self):
        with open(self.pcDataFileName,'r') as fid:
            alld=fid.read()
            l=json.loads(alld)
            incidentURL = l[0]['incidentURL']
            debriefURL=l[0].get('debriefURL',None)
            n=len(l[2])
        return [incidentURL,debriefURL,n]

    def load_data(self):  # loading radiolog data table and assignments table from save file
        # logging.info("In load data")
        fid = open(self.pcDataFileName,'r')
        alld = fid.read()
        l = json.loads(alld)
        logging.info("Get:"+str(l))
        self.incidentURL = l[0]['incidentURL']
        self.debriefURL=l[0].get('debriefURL',None)
        self.watchedFile,self.offsetFileName,self.csvFiles,self.watchedFile2,self.offsetFileName2,self.csvFiles2 = l[1]['csv'].split('%')
        irow = 0
        for key in l[2]:
            self.ui.tableWidget.insertRow(irow)            
            self.ui.tableWidget.setItem(irow, 0, QtWidgets.QTableWidgetItem(l[2][key]['time']))
            self.ui.tableWidget.setItem(irow, 1, QtWidgets.QTableWidgetItem(l[2][key]['callsign']))
            self.ui.tableWidget.setItem(irow, 2, QtWidgets.QTableWidgetItem(l[2][key]['msg']))
            self.ui.tableWidget.setItem(irow, 3, QtWidgets.QTableWidgetItem(l[2][key]['radioLoc']))
            self.ui.tableWidget.setItem(irow, 4, QtWidgets.QTableWidgetItem(l[2][key]['status']))
            self.setRowColor(self.ui.tableWidget,irow,l[2][key]['color'])
            irow = irow + 1
        irow = 0    
        for key in l[3]:
            self.ui.tableWidget_TmAs.insertRow(irow)            
            self.ui.tableWidget_TmAs.setItem(irow, 0, QtWidgets.QTableWidgetItem(l[3][key]['team']))
            self.ui.tableWidget_TmAs.setItem(irow, 1, QtWidgets.QTableWidgetItem(l[3][key]['assign']))    
            self.ui.tableWidget_TmAs.setItem(irow, 2, QtWidgets.QTableWidgetItem(l[3][key]['type']))
            self.ui.tableWidget_TmAs.setItem(irow, 3, QtWidgets.QTableWidgetItem(l[3][key]['med']))
            irow = irow + 1
        irow = 0
        for key in l[4]:
            self.ui.tableWidget_2.insertRow(irow)            
            self.ui.tableWidget_2.setItem(irow, 0, QtWidgets.QTableWidgetItem(l[4][key]['clueNum']))
            self.ui.tableWidget_2.setItem(irow, 1, QtWidgets.QTableWidgetItem(l[4][key]['time']))
            self.ui.tableWidget_2.setItem(irow, 2, QtWidgets.QTableWidgetItem(l[4][key]['radioLoc']))
            self.ui.tableWidget_2.setItem(irow, 3, QtWidgets.QTableWidgetItem(l[4][key]['msg']))
            self.setRowColor(self.ui.tableWidget_2,irow,l[4][key]['color'])
            irow = irow + 1
        fid.close()
        
        
    def get_data(self):  # getting Full radiolog data table and putting in a list (rescan)
        # logging.info("In get data")
        with open(self.pcDataFileName,'r')  as fid:
            alld = fid.read()
            l = json.loads(alld)
            #logging.info("Get:"+str(l))
            self.savedData = []
            for key in reversed(l[2]):    # skip the first 2 row entries as header info
                self.savedData.append([l[2][key]['time'], l[2][key]['callsign'], l[2][key]['msg'], l[2][key]['color']])


    def setRowColor(self,table,row,color):     # sets each column to the desired color
        for col in range(table.columnCount()):
            table.item(row,col).setBackground(QColor(color))

    def tableCellClicked(self,row,col):
        table=self.sender()
        i=table.item(row,col)
        if i:
            prevColor=i.background().color().name()
            if prevColor == self.color[1]:
                newColor=stateColorDict.get(prevColor,self.color[0])
            else:
                newColor=stateColorDict.get(prevColor,self.color[1])
            self.setRowColor(self.ui.tableWidget,row,newColor)
## save data
        self.save_data()

    def assignTab_OK_clicked(self):   # add, delete, modify entry
        if self.cts == None:
            msg = "Not connected to a map"
            inform_user_about_issue(msg)
            return                    # skip as not connected
        while self.flag_TmAs_getobj:  # wait until getObject operation is complete
            pass
        self.flag_TmAs_Ok = True
        self.curAssign = self.ui.Assign.text().upper().strip()
        if self.curAssign == 'IC':
            self.curAssign = 'ICX'    # using ICX to avoid conflict with marker IC
        if self.curAssign == '':      # may be due to double click as things were slow
            self.flag_TmAs_Ok = False
            return                    # No entry, so ignore
        a=self.cts.getFeatures(featureClass='Assignment',title=self.curAssign,letterOnly=True,allowMultiTitleMatch=True)
        #logging.info('getFeatures:'+str(a))
        if self.curAssign not in ['RM'] and len(a)!=1:
            if len(a)==0:
                msg='No assignments with the specified letters "'+self.curAssign+'" were found - no operation performed.'
            else:
                msg='Multiple assignments have the letters "'+self.curAssign+'" - no operation performed.  Remedy that situation and try again.'
            inform_user_about_issue(msg)
            logging.warning(msg)
            self.flag_TmAs_Ok = False
            return
        #print("Ok button clicked, team is:"+self.ui.Team.text())
        rval = self.cts.getFeatures("Assignment")     # get assignments
        ifnd = 1                                      # flag for found valid Assignment
        ## location codes are IC for command post (for type LE, leave marker on map, but at (lon-0.5deg) )
        ##                    TR for in transit
        ##                    RM to remove a team from the table
        ##                    Assignment name 
        if self.curAssign not in ['RM']: ## chk to see if assignment exists (ignore RM)
          ifnd = 0
          print("Assign:"+str(rval))
          for self.feature in rval:
            ##
            ##   number and title appear synomyous (unless there is a letter)
            ##
            #print("ZZZZ:"+str(self.feature["properties"].get("letter")))  # search for new assignment
            if str(self.feature["properties"].get("letter",'').upper()) == self.curAssign:   # find assignment on map
                print("Geo:"+str(self.feature.get("geometry")))
                ifnd = 1     # found the desired assignment on the map, so continue
                break
        if self.ui.Team.text() == "" or ifnd == 0:  # error - checking select below when entry does not exist
            pass  # beepX1
            logging.error("Issue with Assign inputs: "+str(self.ui.Team.text())+" : "+str(ifnd))
            self.flag_TmAs_Ok = False
            return
        ifnd = 0                                    # flag for found existing Team assignment
        irow = 0
        #print("count:"+str(self.ui.tableWidget_TmAs.rowCount()))
        for ix in range(self.ui.tableWidget_TmAs.rowCount()):      # Look for existing Team entry in table
            if self.ui.Team.text().upper().strip() == self.ui.tableWidget_TmAs.item(ix,0).text().upper():  # update
                ifnd = 1             # set found in table, may be on the map, too
                irow = ix            # why do I need this equivalence??
                #S#if (self.ui.tableWidget_TmAs.item(ix,1).text().upper() == "IC" and \
                #S#        self.ui.tableWidget_TmAs.item(ix,2).text().upper() != "LE"):
                    #S#self.ui.tableWidget_TmAs.item(ix,2).text().upper() != "LE") or \
                    #S#self.ui.tableWidget_TmAs.item(ix,1).text().upper() == "TR":  # in transit
                #S#     ifnd = 2        # means came from IC (except type LE) or TR, so s/b no marker/assignment on map now
                #get old marker location to remove 
                #rm marker (NOTE, if was at IC (except type LE) or TR there will not be a marker)
                #if to-assignment is IC or TR do not add marker
                #new marker
                break
        if self.ui.comboBox.currentText() == "Select": 
            if ifnd == 0:               # does not exist in table
                pass  # beepX1
                logging.info("Issue with Assign inputs2")
                self.flag_TmAs_Ok = False
                return
            else:
                indx = self.ui.comboBox.findText(self.ui.tableWidget_TmAs.item(ix,2).text())
                logging.info("INDEX is:"+str(indx))
                self.ui.comboBox.setCurrentIndex(indx)
                if self.ui.tableWidget_TmAs.item(ix,3).text() == ' X':  # also check Med setting
                    self.ui.Med.setChecked(True)
        if self.curAssign == "RM":      # want to completely remove team
            if ifnd == 1:               # want to remove; presently in table AND on map
                self.curTeam = self.ui.Team.text().strip()
                ## if team has medical, need to remove that entry, also
                self.delMarker()        # uses curTeam to find
            if ifnd == 1 or ifnd == 2:  # want to remove; presently only in table
                self.ui.tableWidget_TmAs.removeRow(irow)
            # clear fields
            if ifnd == 0:    # entry not found in table
                pass         #  beep
            else:
                self.ui.Team.setText("")
                self.ui.Assign.setText("")
                self.ui.comboBox.setCurrentIndex(0)
                self.ui.Med.setChecked(False)
## save data
            self.save_data()    
            self.flag_TmAs_Ok = False
            return
        ##  ifnd=0  not in table and not on map  - add team and marker
        ##  ifnd=1  in table and on map          - update/moving
        ##  ifnd=2  in table but not on map      - add to map (except IC or TR)
        # usually won't be assignment IC nor TR
        '''
        ###############   REMOVE this section to allow entry for IC or TR
        if ifnd == 0 and (self.curAssign in ['IC','TR']) and \
                          self.ui.comboBox.currentText() != "LE":
            self.ui.tableWidget_TmAs.insertRow(0)   # changed to create a new entry even for TR or IC (no marker)
            self.curTeam = self.ui.Team.text()
            self.ui.tableWidget_TmAs.setItem(irow, 0, QtWidgets.QTableWidgetItem(self.curTeam))
            self.ui.tableWidget_TmAs.setItem(irow, 1, QtWidgets.QTableWidgetItem(self.curAssign))    
            self.ui.tableWidget_TmAs.setItem(irow, 2, QtWidgets.QTableWidgetItem(self.ui.comboBox.currentText()))
            self.curType = self.ui.comboBox.currentText()
            if self.ui.Med.isChecked(): self.medval = " X"
            else: self.medval = " "    #  need at least a space so that it is not empty
            self.ui.tableWidget_TmAs.setItem(irow, 3, QtWidgets.QTableWidgetItem(self.medval))  # we don't want marker
            self.flag_TmAs_Ok = True
            self.save_data()    
            return
        '''    
        ###if ifnd == 0: self.ui.tableWidget_TmAs.insertRow(0)
        if ifnd == 1:                                 # moving so remove present loc on map
            self.curTeam = self.ui.tableWidget_TmAs.item(irow,0).text()
            print("del marker?")
            self.delMarker()                          # uses curTeam to find
        cntComma = self.ui.Team.text().count(',')+1   # add 1 for first element
        tok = self.ui.Team.text().split(',')
        for ix in range(cntComma):     # go thru list of teams in the assignment, add a row for each
            if ifnd == 0: self.ui.tableWidget_TmAs.insertRow(0)
            print("ifnd is "+str(ifnd)+":"+str(tok)+":"+str(irow)+":"+str(self.curAssign))
            self.ui.tableWidget_TmAs.setItem(irow, 0, QtWidgets.QTableWidgetItem(tok[ix]))
            self.ui.tableWidget_TmAs.setItem(irow, 1, QtWidgets.QTableWidgetItem(self.curAssign))    
            self.ui.tableWidget_TmAs.setItem(irow, 2, QtWidgets.QTableWidgetItem(self.ui.comboBox.currentText()))
            self.curTeam = tok[ix]
            self.curType = self.ui.comboBox.currentText()
            if self.ui.Med.isChecked(): self.medval = " X"
            else: self.medval = " "    #  need at least a space so that it is not empty
            self.ui.tableWidget_TmAs.setItem(irow, 3, QtWidgets.QTableWidgetItem(self.medval))
            #S#if self.curAssign.upper() in ["IC", "TR"]: # there is no map location for teams at IC or in transit
            #S#    self.ui.tableWidget_TmAs.setItem(irow, 3, QtWidgets.QTableWidgetItem(" "))
            #S#    break
        # find center of shape in latField and lonField float
            if self.curType == "LE" and self.curAssign.upper() == "IC":         # moving LE to 'IC' (away)
                self.lonField = self.NCSO[1]+random.uniform(-1.0, 1.0)*0.001    # temp location; randomly adjust
                self.latField = self.NCSO[0]+random.uniform(-1.0, 1.0)*0.001    # +/-0.001 deg lat and long
            else:   
                self.calcLatLon_center()              # use self.ui.Assign.text() to find shape
        # set marker type (in addMarker) based on Med or if type=LE
            print("B4 addMark:"+str(self.curAssign))
            ##if (self.curAssign != "IC" and self.curAssign != "TR") or self.curType == "LE":
            self.addMarker()       # uses self.ui.Team, medval

        # clear fields
        self.ui.Team.setText("")
        self.ui.Assign.setText("")
        self.ui.comboBox.setCurrentIndex(0)
        self.ui.Med.setChecked(False)
## save data            
        self.save_data()
        self.flag_TmAs_Ok = False
        
    def calcLatLon_center(self):
        logging.info("in LATLOG")
        loc = self.feature['geometry'].get("coordinates")   # of an assignment
        loc_lat = 0
        loc_long = 0
        ipt = 0
        lenloc = len(loc)
        if type(loc[0][0]) is list:     # polygon is list of list
            p = Polygon(loc[0])                # make shapely Polygon
            mid = p.representative_point()     # get point in shape (shapely)
            avg_lat = list(mid.coords)[0][1]   # convert shapely object back to tuple in list
            avg_lon = list(mid.coords)[0][0]
        else:    # line
            loca = loc[int(lenloc/2)]          # use its mid point
            avg_lat = loca[1]
            avg_lon = loca[0]
        logging.info("Loc-lat:"+str(avg_lat)+" loc-long:"+str(avg_lon))
        self.latField = avg_lat
        self.lonField = avg_lon
        
    # get a list of non-clueLog filenames, modification times, and sizes
    #  in the watchedDir, sorted by modification time (so that the most recent
    #  file is the first item in the list)
    def readDir(self):
        logging.info("in readDir")
        f=glob.glob(self.watchedDir+"\\*.csv")
        f2 = f
        # logging.info("Files: %s"%f)
        f=[x for x in f if not regex.match('.*_clueLog.csv$',x)]
        f=[x for x in f if not regex.match('.*_fleetsync.csv$',x)]
        f=[x for x in f if not regex.match('.*_bak[123456789].csv$',x)]
        f2=[x for x in f2 if regex.match('.*_clueLog.csv$',x)]  # get cluelog files
        f=sorted(f,key=os.path.getmtime,reverse=True)
        f2=sorted(f2,key=os.path.getmtime,reverse=True)
        for file in f:
            l=[file,os.path.getsize(file),os.path.getmtime(file)]
            self.csvFiles.append(l)
        for file in f2:
            l=[file,os.path.getsize(file),os.path.getmtime(file)]
            self.csvFiles2.append(l)
        print("LIST:"+str(self.csvFiles))    

    def readWatchedFile(self):
        newEntries=[]       # these are supposed to be NEW entries as using Pygtail to analyze watchedFile
        newEntries2=[]      #   How does forced reload work if only passing NEW lines to rescan/refresh?
        #print("Watched:"+str(self.watchedFile))
        if self.csvFiles !=[]:
          newl = False  
          try:    # Note if offset file does not exist, whole file is returned
                  #   rescan removes the offset file, hence upon rescan the whole file is read
              lines = Pygtail(self.watchedFile, offset_file=self.offsetFileName, copytruncate=False)
          except:   # retry if first connection fails
              lines = Pygtail(self.watchedFile, offset_file=self.offsetFileName, copytruncate=False)
              print("At 2nd attempt to read...")
          ## for line in Pygtail(self.watchedFile, offset_file=self.offsetFileName, copytruncate=False):
          for line in lines:
            #print("LINEZZ:"+str(line))  
            line, newl = self.fixStrg(line, newl)  # fix ' and newline in  string
            if newl:
                #print("In middle")
                continue     # in the middle of a multi-line description
            #print("FIXED:"+str(line)+":"+str(newl))
            newEntries.append(line.split(','))
        if self.csvFiles2 !=[]:
          newl = False  
          try:
              lines = Pygtail(self.watchedFile2, offset_file=self.offsetFileName2, copytruncate=False)
          except:   # retry if first connection fails
              lines = Pygtail(self.watchedFile2, offset_file=self.offsetFileName2, copytruncate=False)
          ## for line in Pygtail(self.watchedFile2, offset_file=self.offsetFileName2, copytruncate=False):
          for line in lines:
            line, newl = self.fixStrg(line, newl)  # fix ' and newline in  string
            if newl:
                continue     # in the middle of a multi-line description
            newEntries2.append(line.split(','))
        return newEntries,newEntries2
                
    def updateClock(self):
        self.ui.clock.display(time.strftime("%H:%M"))
        
    def saveRcFile(self):
        logging.info("saving...")
        (self.x,self.y,self.w,self.h)=self.geometry().getRect()
        rcFile=QFile(self.rcFileName)
        if not rcFile.open(QFile.WriteOnly|QFile.Text):
            warn=QMessageBox(QMessageBox.Warning,"Error","Cannot write resource file " + self.rcFileName + "; proceeding, but, current settings will be lost. "+rcFile.errorString(),
                            QMessageBox.Ok,self,Qt.WindowTitleHint|Qt.WindowCloseButtonHint|Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint|Qt.WindowStaysOnTopHint)
            warn.show()
            warn.raise_()
            warn.exec_()
            return
        out=QTextStream(rcFile)
        out << "[Plans_console]\n"
        # out << "font-size=" << self.fontSize << "pt\n"
        out << "x=" << self.x << "\n"
        out << "y=" << self.y << "\n"
        out << "w=" << self.w << "\n"
        out << "h=" << self.h << "\n"
        # debrief geometry values are set during resizeEvent of that dialog
        if self.dmg:
            (self.debriefX,self.debriefY,self.debriefW,self.debriefH)=self.dmg.dd.geometry().getRect()
        # if values currently exist, write them to the file for future use - even if dmg was not opened during this session
        if self.debriefX and self.debriefY and self.debriefW and self.debriefH:        
            out << "[Debrief]\n"
            out << "debriefX=" << self.debriefX << "\n"
            out << "debriefY=" << self.debriefY << "\n"
            out << "debriefW=" << self.debriefW << "\n"
            out << "debriefH=" << self.debriefH << "\n"
        rcFile.close()
        
    def loadRcFile(self):
        logging.info("loading...")
        rcFile=QFile(self.rcFileName)
        if not rcFile.open(QFile.ReadOnly|QFile.Text):
            warn=QMessageBox(QMessageBox.Warning,"Error","Cannot read resource file " + self.rcFileName + "; using default settings. "+rcFile.errorString(),
                            QMessageBox.Ok,self,Qt.WindowTitleHint|Qt.WindowCloseButtonHint|Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint|Qt.WindowStaysOnTopHint)
            warn.show()
            warn.raise_()
            warn.exec_()
            return
        inStr=QTextStream(rcFile)
        line=inStr.readLine()
        if line!="[Plans_console]":
            warn=QMessageBox(QMessageBox.Warning,"Error","Specified resource file " + self.rcFileName + " is not a valid resource file; using default settings.",
                            QMessageBox.Ok,self,Qt.WindowTitleHint|Qt.WindowCloseButtonHint|Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint|Qt.WindowStaysOnTopHint)
            warn.show()
            warn.raise_()
            warn.exec_()
            rcFile.close()
            return
        while not inStr.atEnd():
            line=inStr.readLine()
            tokens=line.split("=")
            if tokens[0]=="x":
                self.x=int(tokens[1])
            elif tokens[0]=="y":
                self.y=int(tokens[1])
            elif tokens[0]=="w":
                self.w=int(tokens[1])
            elif tokens[0]=="h":
                self.h=int(tokens[1])
            # elif tokens[0]=="font-size":
            #     self.fontSize=int(tokens[1].replace('pt',''))
            elif tokens[0]=="debriefX":
                self.debriefX=int(tokens[1])
            elif tokens[0]=="debriefY":
                self.debriefY=int(tokens[1])
            elif tokens[0]=="debriefW":
                self.debriefW=int(tokens[1])
            elif tokens[0]=="debriefH":
                self.debriefH=int(tokens[1])
        rcFile.close()

    def moveEvent(self,event):
        screen=self.screen()
        # logging.info(self.__class__.__name__+' moveEvent called')
        # logicalDotsPerInch seems to give a bit better match across differently scaled extended screen
        #  than physicalDotsPerInch - though not exactly perfect, probably due to testing on monitors
        #  with different physical sizes; but logicalDotsPerInch incorporates Windows display zoom,
        #  while physicalDotsPerInch does not
        ldpi=screen.logicalDotsPerInch()
        if ldpi!=self.ldpi:
            pix=genLpix(ldpi)
            logging.debug(self.__class__.__name__+' window moved: new logical dpi='+str(ldpi)+'  new 12pt equivalent='+str(pix[12])+'px')
            self.ldpi=ldpi

            # # from https://doc.qt.io/qt-5/qmetaobject.html#propertyCount
            # metaobject=screen.metaObject()
            # d={}
            # for i in range(metaobject.propertyOffset(),metaobject.propertyCount()):
            #     metaproperty=metaobject.property(i)
            #     name=metaproperty.name()
            #     d[name]=str(screen.property(name))
            # logging.info('dict:\n'+json.dumps(d,indent=3))


            self.setStyleSheet('''
                *{
                    font-size:'''+str(pix[12])+'''px;
                }
                self.ui.setupUi.label_5{
                    font-size:'''+str(pix[6])+'''px;
                }    
                QDialog{
                    padding:'''+str(pix[6])+'''px;
                }
                QLineEdit{
                    height:'''+str(pix[16])+'''px;
                }
                QLineEdit#incidentLinkLight,QLineEdit#debriefLinkLight{
                    width:'''+str(pix[16])+'''px;
                }
                QGroupBox{
                    border:'''+str(pix[1])+'''px solid darkgray;
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
                QComboBox{
                    padding-top:'''+str(pix[4])+'''px;
                }
                QMessageBox,QDialogButtonBox{
                    icon-size:'''+str(pix[36])+'''px '''+str(pix[36])+'''px;
                }
                QCheckBox::indicator,QRadioButton::indicator{
                    width:'''+str(pix[10])+'''px;
                    height:'''+str(pix[10])+'''px;
                }
                QRadioButton{
                    spacing:'''+str(pix[8])+'''px;
                }
                ''')
            self.ui.label.setStyleSheet("padding-top: 0px; padding-bottom: 0px;")
            self.ui.label_5.setStyleSheet("font-size: "+str(pix[8])+"px; padding-top: 0px; padding-bottom: 0px;")
            self.ui.incidentButton.setStyleSheet("font-size: "+str(pix[9])+"px;")
            self.ui.debriefButton.setStyleSheet("font-size: "+str(pix[9])+"px;")
            # now set the sizes that don't respond to stylesheets for whatever reason
            self.ui.incidentLinkLight.setFixedWidth(pix[18])
            self.ui.debriefLinkLight.setFixedWidth(pix[18])
            # logging.info('style:'+self.styleSheet())
            self.ui.topLayout.setContentsMargins(pix[6],pix[6],pix[6],pix[6])
            self.ui.rescanButton.setIconSize(QtCore.QSize(pix[18],pix[18]))
            self.setMinimumSize(QtCore.QSize(int(900*(ldpi/96)),int(600*(ldpi/96))))
            self.ui.tableWidget_TmAs.setMinimumSize(QtCore.QSize(int(300*(ldpi/96)),int(200*(ldpi/96))))
            self.ui.rightVertLayout.setSpacing(pix[6])
            self.ui.mapsGroupVerticalLayout.setSpacing(pix[8])
            self.ui.geomGroupVerticalLayout.setSpacing(pix[8])
            self.resizeTableColumns()
        if event:
            event.accept()

    def resizeTableColumns(self):
        ldpi=self.ldpi
        # set fixed width for first, second, fourth, fifth columns;
        #  set the third column to expand as the layout is resized
        self.ui.tableWidget.setColumnWidth(0, int(50*(ldpi/96)))
        self.ui.tableWidget.setColumnWidth(1, int(100*(ldpi/96)))
        self.ui.tableWidget.horizontalHeader().setSectionResizeMode(2,1)
        self.ui.tableWidget.setColumnWidth(3, int(110*(ldpi/96)))
        self.ui.tableWidget.setColumnWidth(4, int(150*(ldpi/96)))

        self.ui.tableWidget_TmAs.setColumnWidth(0, int(50*(ldpi/96)))
        self.ui.tableWidget_TmAs.setColumnWidth(1, int(60*(ldpi/96)))
        self.ui.tableWidget_TmAs.setColumnWidth(2, int(100*(ldpi/96)))
        self.ui.tableWidget_TmAs.setColumnWidth(3, int(50*(ldpi/96)))

        self.ui.tableWidget_2.setColumnWidth(0, int(100*(ldpi/96)))
        self.ui.tableWidget_2.setColumnWidth(1, int(50*(ldpi/96)))
        self.ui.tableWidget_2.setColumnWidth(2, int(120*(ldpi/96)))
        self.ui.tableWidget_2.horizontalHeader().setSectionResizeMode(3,1)  

    def closeEvent(self,event):  # to save RC file
        if not ask_user_to_confirm("Exit Plans Console?", icon=QMessageBox.Warning, parent = self):
            event.ignore()
            self.exitClicked=False
            return
        logging.info(cleanShutdownText)
        self.saveRcFile()
        event.accept()
        self.parent.quit()

    # prevent esc key from closing the program
    def reject(self,*args):
        pass
       
def main():
    app = QApplication(sys.argv)
    w = PlansConsole(app)
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
