from sartopo_python import SartopoSession
import logging
import re
import time
import os
import sys
import json
import shutil
from datetime import datetime
import webbrowser
from math import floor,cos,radians

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from specifyMap import SpecifyMapDialog

from debrief_ui import Ui_DebriefDialog
from debriefOptionsDialog_ui import Ui_DebriefOptionsDialog

LINK_LIGHT_STYLES={
    -1:"background-color:#bb0000;", # red - no link / link error
    0:"background-color:#aaaaaa;", # gray - no link attempted
    1:"background-color:#009900;", # medium green - good link
    5:"background-color:#00dd00;", # med-light green - sync heartbeat
    10:"background-color:#00ff00;", # light green - good link, sync in progress
    100:"background-color:#00ffff;" # cyan - data change in progress
}

BASEMAP_REGEX={
    'mapbuilder topo':'mbt',
    'mapbuilder hybrid':'mbh',
    'scanned topo':'t',
    'forest service.*2016.*green':'f16a',
    'forest service.*2016.*white':'f16',
    'forest service.*2013':'f',
    'naip':'n'
}

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

# log uncaught exceptions - https://stackoverflow.com/a/16993115/3577105
# don't try to print from inside this function, since stdout is in binary mode
# note - this function will be overwritten by the same function in plans console
#  (if called from plans console)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))
    inform_user_about_issue('Uncaught Exception:')
sys.excepthook = handle_exception

# sourceMap and targetMap arguments can be one of:
#  SartopoSession instance
#  map ID (end of URL)
#  complete URL

# in the last two cases, a new instance of SartopoSession will be created


# log filename should be <top-level-module-name>.log
# so if this is being called from plans console, use the already-opened
#  logfile plans-console.log
# but if this is being run directly, use dmg.log
logfile=os.path.splitext(os.path.basename(sys.path[0]))[0]+'.log'

# To redefine basicConfig, per stackoverflow.com/questions/12158048
# Remove all handlers associated with the root logger object.

errlogdepth=5
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
if os.path.isfile(logfile):
    os.remove(logfile)
logging.basicConfig(
    level=logging.INFO,
    datefmt='%H:%M:%S',
    format='%(asctime)s [%(module)s:%(lineno)d:%(levelname)s] %(message)s',
    handlers=[
        # setting the filehandeler to write mode here causes the file
        #  to get deleted and overwritten when the threads end; so
        #  instead set it to append here, and take care of deleting it
        #  or rotating it at the top level
        logging.FileHandler(logfile,'a'),
        # logging.FileHandler(self.fileNameBase+'_bg.log','w'),
        logging.StreamHandler(sys.stdout)
    ]
)

# add a custom handler that doesn't print anything, but instead copies the file
#  to a backup if level is ERROR or CRITICAL.  It's important to make sure this
#  happens >after< the first default handler that actually does the printing.
# Only keep [logdepth] error log files (default 5).
errlog=False
class CustomHandler(logging.StreamHandler):
    def emit(self,record):
        if record.levelname in ['ERROR','CRITICAL']:
            global errlog
            # if this is the first error/critical record for this session,
            #  rotate the error log files in preparation for copying of the current log
            if not errlog:                    
                for n in range(errlogdepth-1,0,-1):
                    src=logfile+'.err.'+str(n)
                    dst=logfile+'.err.'+str(n+1)
                    if os.path.isfile(src):
                        os.replace(src,dst)
                src=logfile+'.err'
                dst=logfile+'.err.1'
                if os.path.isfile(src):
                    os.replace(src,dst)
                errlog=True
            # if this session has had any error/critical records, copy to error log file
            #  (regardless of the current record's level)
            if errlog:
                shutil.copyfile(logfile,logfile+'.err')

logging.root.addHandler(CustomHandler())

def genLpix(ldpi):
    lpix={}
    for ptSize in [1,2,3,4,6,8,9,10,11,12,14,16,18,22,24,36,48]:
        lpix[ptSize]=floor((ldpi*ptSize)/72)
    return lpix

def ask_user_to_confirm(question: str, icon: QMessageBox.Icon = QMessageBox.Question, parent: QObject = None, title = "Please Confirm") -> bool:
    opts = Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowStaysOnTopHint
    buttons = QMessageBox.StandardButton(QMessageBox.Yes | QMessageBox.No)
    box = QMessageBox(icon, title, question, buttons, parent, opts)
    # determine logical pixel equivalents: take prom parent if possible, so that the messagebox uses the same DPI as the spawning window
    if hasattr(parent,'lpix'):
        lpix=parent.lpix
        # logging.info('using parent lpix: '+str(lpix))
    else:
        lpix=genLpix(96) # use 96dpi as a default when the parent doesn't have any lpix attribute
        # logging.info('using default 96dpi lpix: '+str(lpix))
    box.setDefaultButton(QMessageBox.No)
    box.setStyleSheet('''
    *{
        font-size:'''+str(lpix[12])+'''px;
        icon-size:'''+str(lpix[36])+'''px '''+str(lpix[36])+'''px;
    }''')
    box.show()
    QCoreApplication.processEvents()
    box.raise_()
    return box.exec_() == QMessageBox.Yes

def inform_user_about_issue(message: str, icon: QMessageBox.Icon = QMessageBox.Critical, parent: QObject = None, title="", timeout=0):
    opts = Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowStaysOnTopHint
    if title == "":
        title = "Warning" if (icon == QMessageBox.Warning) else "Error"
    buttons = QMessageBox.StandardButton(QMessageBox.Ok)
    box = QMessageBox(icon, title, message, buttons, parent, opts)
    # determine logical pixel equivalents: take prom parent if possible, so that the messagebox uses the same DPI as the spawning window
    if hasattr(parent,'lpix'):
        lpix=parent.lpix
        # logging.info('using parent lpix: '+str(lpix))
    else:
        lpix=genLpix(96) # use 96dpi as a default when the parent doesn't have any lpix attribute
        # logging.info('using default 96dpi lpix: '+str(lpix))
    # attempt to set larger min width on hi res - none of these seem to work
    # from https://www.qtcentre.org/threads/22298-QMessageBox-Controlling-the-width
    # spacer=QSpacerItem(int(8000*(LDPI/96)),0,QSizePolicy.Minimum,QSizePolicy.Expanding)
    # layout=box.layout()
    # layout.addItem(spacer,layout.rowCount(),0,1,layout.columnCount())
    # box.setMaximumWidth(int(800*(LDPI/96)))
    # box.setFixedWidth(int(800*(LDPI/96)))
    box.setStyleSheet('''
    *{
        font-size:'''+str(lpix[12])+'''px;
        icon-size:'''+str(lpix[36])+'''px '''+str(lpix[36])+'''px;
    }''')
    box.show()
    QCoreApplication.processEvents()
    box.raise_()
    if timeout:
        QTimer.singleShot(timeout,box.close)
    box.exec_()

# from https://stackoverflow.com/a/10995203/3577105
def dictHasAllKeys(d,klist):
    if not isinstance(d,dict) or not isinstance(klist,list):
        logging.error('dictHasKeys: first arg must be dict; second arg must be list')
        return False
    return all(key in d for key in klist)

class DebriefMapGenerator(QObject):
    updateLinkLightsSignal=pyqtSignal()
    def __init__(self,parent,sourceMap,targetMap):
        logging.info('Debrief Map Generator startup at '+datetime.now().strftime("%a %b %d %Y %H:%M:%S"))
        self.parent=parent
        super(DebriefMapGenerator,self).__init__()
        # is this being spawned from Plans Console?
        self.pc=self.parent.__class__.__name__=='PlansConsole'
        self.debriefURL=''
        self.startupBox=None

        # do not register the callbacks until after the initial processing; that way we
        #  can be sure to process existing assignments first

        # assignments - dictionary of dictionaries of assignment data; each assignment sub-dictionary
        #   is created upon processing of the first feature that appears to be related to the assigment,
        #   based on title ('AA101' for assignment features, or 'AA101a' for lines, possibly including space(s))
        # NOTE - we really want to be able to recreate the ID associations at runtime (what debrief map
        #   feature corresponds to what source map feature) rather than relying on a correspondence file,
        #   but that would require a place for metadata on the debrief map features.  Maybe the debrief map
        #   details / description field could be used for this?  Any new field added here just gets deleted
        #   by sartopo.  How important is it to keep this ID correspondence?  IS title sufficient?
        #  key = assignment title (name and number; i.e. we want one dict entry per pairing/'outing')
        #  val = dictionary
        #     bid - id of boundary feature (in the debrief map)
        #     fid - id of folder feature (in the debrief map)
        #     sid - id of the assignment feature (in the SOURCE map)
        #     cids - list of ids of associated clues (in the debrief map)
        #     tids - list of ids of associated tracks (in the debrief map)
        #     utids - list of uncropped track ids (since the track may be processed before the boundary)

        self.dd=DebriefDialog(self)

        if self.parent.debriefX and self.parent.debriefY and self.parent.debriefW and self.parent.debriefH:
            self.dd.setGeometry(int(self.parent.debriefX),int(self.parent.debriefY),int(self.parent.debriefW),int(self.parent.debriefH))

        self.debriefOptionsDialog=DebriefOptionsDialog(self)
        self.dd.ui.debriefOptionsButton.clicked.connect(self.debriefOptionsButtonClicked)

        # determine / create SartopoSession objects
        #  process the target session first, since nocb definition checks for it

        # determine / create sts2 (debrief map SartopoSession instance)
        self.sts2=None
        self.debriefDomainAndPort=None
        tcn=targetMap.__class__.__name__
        if tcn=='SartopoSession':
            # logging.info('debrief map argument = SartopoSession instance')
            self.sts2=targetMap
            self.debriefDomainAndPort=self.sts2.domainAndPort
            self.debriefMapID=self.sts2.mapID
        elif tcn=='str':
            # logging.info('debrief map argument = string')
            self.debriefDomainAndPort='localhost:8080'
            targetParse=targetMap.split('/')
            self.debriefMapID=targetParse[-1]
            self.debriefURL=self.debriefDomainAndPort+'/m/'+self.debriefMapID
            if targetMap.lower().startswith('http'):
                self.debriefURL=targetMap
                self.debriefDomainAndPort=targetParse[2]
        else:
            logging.info('No debrief map; raising SpecifyMapDialog')
            self.defaultDomainAndPort=None
            if hasattr(self.parent,'defaultDomainAndPort'):
                self.defaultDomainAndPort=self.parent.defaultDomainAndPort
            self.debriefMapDialog=SpecifyMapDialog(self,'Debrief','Create New Map, or Use Existing Map?',self.defaultDomainAndPort,enableNewMap=True)
            if self.debriefMapDialog.exec(): # force modal
                if self.debriefMapDialog.newMap:
                    logging.info('new map requested')
                    configpath='../sts.ini'
                    account=None
                    self.debriefDomainAndPort=self.debriefMapDialog.dap
                    if self.pc:
                        configpath=self.parent.stsconfigpath
                        account=self.parent.accountName
                    self.startupBox=QMessageBox(
                        QMessageBox.NoIcon, # other vaues cause the chime sound to play
                        'New debrief map...',
                        'Debrief Map:\n\nCreating new map...')
                    self.startupBox.setStandardButtons(QMessageBox.NoButton)
                    self.startupBox.show()
                    QCoreApplication.processEvents()
                    self.sts2=SartopoSession(self.debriefDomainAndPort,'[NEW]',
                        sync=False,
                        account=account,
                        configpath=configpath,
                        syncTimeout=10)
                    self.debriefMapID=self.sts2.mapID
                    self.debriefURL=self.debriefMapDialog.url.replace('<Pending>',self.sts2.mapID)
                    self.startupBox.setText('New map created:\n\n'+self.debriefURL+'\n\nPopulating new map...')
                    QCoreApplication.processEvents()
                else:
                    self.debriefURL=self.debriefMapDialog.url
                    parse=self.debriefURL.replace("http://","").replace("https://","").split("/")
                    self.debriefDomainAndPort=parse[0]
                    self.debriefMapID=parse[-1]
                self.dd.ui.debriefMapField.setText(self.debriefURL)
                if self.pc:
                    self.parent.ui.debriefMapField.setText(self.debriefURL)
            else:
                return # debrief map selection dialog was canceled

        if not self.sts2:
            box=QMessageBox(
                QMessageBox.NoIcon, # other vaues cause the chime sound to play
                'Connecting...',
                'Debrief Map:\n\nConnecting to '+self.debriefURL+'\n\nPlease wait...')
            box.setStandardButtons(QMessageBox.NoButton)
            box.show()
            configpath='../sts.ini'
            account=None
            if self.pc:
                configpath=self.parent.stsconfigpath
                account=self.parent.accountName
            QCoreApplication.processEvents()
            box.raise_()
            parse=self.debriefURL.replace("http://","").replace("https://","").split("/")
            domainAndPort=parse[0]
            mapID=parse[-1]
            self.sts2=SartopoSession(self.debriefDomainAndPort,self.debriefMapID,
                sync=False,
                account=account,
                configpath=configpath,
                syncTimeout=10)
                # syncTimeout=10,
                # syncDumpFile='../../'+self.debriefMapID+'.txt')
            box.done(0)

        if self.sts2 and self.sts2.apiVersion<0:
            p=self.dd
            if self.pc:
                p=self.parent
            inform_user_about_issue('Link could not be established with specified debrief map\n\n'+self.debriefURL+'\n\nPlease specify a valid map.',parent=p)
            return

        if self.pc:
            self.dd.ui.debriefDialogLabel.setText('Debrief Map Generator is running in the background.  You can safely close and reopen this dialog as needed.\n\nDebrief data (tracks from returning searchers) should be imported to the INCIDENT map.  The DEBRIEF map is automatically updated and should not need to be directly edited.')
            self.parent.debriefURL=self.debriefURL

        # determine / create sts1 (source map SartopoSession instance)
        self.sts1=None
        scn=sourceMap.__class__.__name__
        if scn=='SartopoSession':
            logging.info('Source map argument = SartopoSession instance: '+sourceMap.domainAndPort+'/m/'+sourceMap.mapID)
            self.sts1=sourceMap
            self.sourceMapID=self.sts1.mapID
            self.incidentDomainAndPort=self.sts1.domainAndPort
        elif scn=='str':
            logging.info('Source map argument = string')
            self.incidentDomainAndPort='localhost:8080'        
            sourceParse=sourceMap.split('/')
            self.sourceMapID=sourceParse[-1]
            if sourceMap.lower().startswith('http'):
                self.incidentDomainAndPort=sourceParse[2]
            try:
                self.sts1=SartopoSession(self.incidentDomainAndPort,self.sourceMapID,
                    # syncDumpFile='../../'+self.sourceMapID+'.txt',
                    # newFeatureCallback=self.initialNewFeatureCallback,
                    # propertyUpdateCallback=self.propertyUpdateCallback,
                    # geometryUpdateCallback=self.geometryUpdateCallback,
                    # deletedFeatureCallback=self.deletedFeatureCallback,
                    syncTimeout=10)
            except:
                logging.critical('Error during source map session creation; aborting.')
                sys.exit()
        else:
            logging.critical('No source map.')
            return

        if self.sts1:
            self.sts1.syncCallback=self.syncCallback
            
        if self.pc:
            self.dd.ui.incidentMapField.setText(self.parent.incidentURL)

        # self.sourceMapID=sourceMapID
        # self.debriefMapID=debriefMapID # must already be a saved map
        self.fileNameBase=self.sourceMapID+'_'+self.debriefMapID
        self.dmdFileName='dmg_'+self.fileNameBase+'.json'
        # assignmentsFileName=fileNameBase+'_assignments.json'

        # different logging level for different modules:
        # https://stackoverflow.com/a/7243225/3577105
        logging.getLogger('sartopo_python').setLevel(logging.DEBUG)

        # rotate track colors: red, green, blue, orange, cyan, purple, then darker versions of each
        self.trackColorDict={
            'a':'#FF0000',
            'b':'#00CD00',
            'c':'#0000FF',
            'd':'#FFAA00',
            'e':'#009AFF',
            'f':'#A200FF',
            'g':'#C00000',
            'h':'#006900',
            'i':'#0000C0',
            'j':'#BC7D00',
            'k':'#0084DC',
            'l':'#8600D4'} # default specified in .get function
        
        self.roamingThresholdMeters=50
        self.cropDegrees=0.001  # about 100 meters - varies with latitude but this is not important for cropping
        self.roamingCropDegrees=0.1 # about 10km - varies with latitude but this is not important for cropping

        self.dmd={} # master map data and correspondence dictionary - short for 'Debrief Map Dictionary'
        self.dmd['outings']={}
        self.dmd['corr']={}
        self.writeDmdPause=False
        # self.pdfStatus={}

        self.orphanTracksDict={}
        self.outingSuffixDict={} # index numbers for duplicate-named assignments
        # def writeAssignmentsFile():
        #     # write the correspondence file
        #     with open(assignmentsFileName,'w') as assignmentsFile:
        #         assignmentsFile.write(json.dumps(assignments,indent=3))

        # # open a session on the debrief map first, since nocb definition checks for it
        # if not self.sts2:
        #     try:
        #         self.sts2=SartopoSession(self.debriefDomainAndPort,self.debriefMapID,
        #             sync=False,
        #             syncTimeout=10,
        #             syncDumpFile='../../'+self.debriefMapID+'.txt')
        #     except:
        #         sys.exit()

        # if not self.sts1:  
        #     try:
        #         self.sts1=SartopoSession(self.incidentDomainAndPort,self.sourceMapID,
        #             syncDumpFile='../../'+self.sourceMapID+'.txt',
        #             # newFeatureCallback=self.initialNewFeatureCallback,
        #             # propertyUpdateCallback=self.propertyUpdateCallback,
        #             # geometryUpdateCallback=self.geometryUpdateCallback,
        #             # deletedFeatureCallback=self.deletedFeatureCallback,
        #             syncTimeout=10)
        #     except:
        #         sys.exit()

        # wait for the source map sync to complete before trying to read an existing dmd file,
        #  otherwise all correspondences will be invalid because the sid's are not yet in
        #  the source cache
        logging.info('sts1.apiVersion:'+str(self.sts1.apiVersion))
        logging.info('sts2.apiVersion:'+str(self.sts2.apiVersion))
        if self.sts1.apiVersion>=0 and self.sts2.apiVersion>=0:
            self.sts1.refresh() # this should do a blocking refresh
            self.initDmd()

            # now that dmd is generated, all source map features should be passed to newFeatureCallback,
            #  which is what would happen if the callback were registered when sts1 was created - but
            #  that would be too early, since the feature creation functions rely on dmd
            for f in self.sts1.mapData['state']['features']:
                self.newFeatureCallback(f)

            # don't register the callbacks until after the initial refresh dmd file processing,
            #  to prevent duplicate feature creation in the debrief map on restart
            self.sts1.newFeatureCallback=self.newFeatureCallback
            self.sts1.propertyUpdateCallback=self.propertyUpdateCallback
            self.sts1.geometryUpdateCallback=self.geometryUpdateCallback
            self.sts1.deletedFeatureCallback=self.deletedFeatureCallback
        
            if not self.sts1.sync:
                self.sts1.start()

        if self.startupBox:
            self.startupBox.done(0)

        # updateLinnkLightsSignal, emitted from thread-safe updateLinkLights function,
        #  calls _updateLinkLights slot which always runs in the main thread
        #  therefore will not cause crashes
        self.updateLinkLightsSignal.connect(self._updateLinkLights)
        self.updateLinkLights()
  
        self.redrawFlag=True
        self.syncBlinkFlag=False

        self.mainTimer=QTimer()
        self.mainTimer.timeout.connect(self.tick)
        self.mainTimer.start(1000)

        # need to run this program in a loop - it's not a background/daemon process
        # while True:
        #     time.sleep(5)
        #     logging.info('dmd:\n'+str(json.dumps(self.dmd,indent=3)))
        # return # why would it need to run in a loop?  Maybe that was tru before it was QtIzed

    # updateLinkLights - can safely be called from within the background thread:
    #  sets instance variables, and sends the signal to update the link lights
    def updateLinkLights(self,incidentLink=None,debriefLink=None):
        self.incidentLightColor=incidentLink or self.sts1.apiVersion
        self.debriefLightColor=debriefLink or self.sts2.apiVersion
        self.updateLinkLightsSignal.emit()

    # _udpateLinkLights - calling this from a background thread can cause hard-to-debug crashes!
    #  so, it should only be called from the signal emitted by a call to updateLinkLights (no underscore)
    def _updateLinkLights(self):
        if self.incidentLightColor: # leave it unchanged if the variable is None
            self.dd.ui.incidentLinkLight.setStyleSheet(LINK_LIGHT_STYLES[self.incidentLightColor])
            if self.pc:
                self.parent.ui.incidentLinkLight.setStyleSheet(LINK_LIGHT_STYLES[self.incidentLightColor])
        if self.sts2 and self.debriefLightColor: # leave it unchanged if the variable is None
            self.dd.ui.debriefLinkLight.setStyleSheet(LINK_LIGHT_STYLES[self.debriefLightColor])
            if self.pc:
                self.parent.ui.debriefLinkLight.setStyleSheet(LINK_LIGHT_STYLES[self.debriefLightColor])

    def writeDmdFile(self):
        if not self.writeDmdPause:
            with open(self.dmdFileName,'w') as dmdFile:
                dmdFile.write(json.dumps(self.dmd,indent=3))
            self.redrawFlag=True

    def tick(self):
        if self.redrawFlag:
            logging.debug('Debrief redraw was requested; redrawing the debrief table...')
            row=0
            self.dd.ui.tableWidget.setSortingEnabled(False)
            outings=self.dmd.get('outings',None)
            self.dd.ui.tableWidget.setRowCount(len(outings))
            for outingName in outings:
                o=self.dmd['outings'][outingName]
                self.dd.ui.tableWidget.setItem(row,0,QTableWidgetItem(outingName))
                self.dd.ui.tableWidget.setItem(row,1,QTableWidgetItem(str(len(o['tids']))))
                self.dd.ui.tableWidget.setItem(row,2,QTableWidgetItem(str(len(o['cids']))))
                editNoteButton=QPushButton(self.dd.ui.editNoteIcon,'')
                editNoteButton.setIconSize(QSize(self.lpix[16],self.lpix[16]))
                editNoteButton.clicked.connect(self.editNoteClicked)
                self.dd.ui.tableWidget.setCellWidget(row,3,editNoteButton)
                notes=o.get('notes',None)
                if notes:
                    s='\n'.join(list(reversed(notes)))
                    i=QTableWidgetItem(s)
                    tt='<table border="1" cellpadding="3">'
                    for note in [x for x in notes if x!='']:
                        tt+='<tr><td>'+note+'</td></tr>'
                    tt+='</table>'
                    i.setToolTip(tt)
                    self.dd.ui.tableWidget.setItem(row,4,i)
                pdf=o.get('PDF',None)
                if pdf:
                    pdfts=o['PDF'][1]
                    latestts=o['log'][-1][0]
                    if pdfts>latestts:
                        # pdf was generated more recently than the latest modification of this outing's data
                        self.setPDFButton(row,'done')
                    else:
                        self.setPDFButton(row,'old')
                else:
                    self.setPDFButton(row,'gen')
                rebuildButton=QPushButton(self.dd.ui.rebuildIcon,'')
                rebuildButton.setIconSize(QSize(self.lpix[16],self.lpix[16]))
                rebuildButton.clicked.connect(self.rebuildClicked)
                self.dd.ui.tableWidget.setCellWidget(row,6,rebuildButton)
                row+=1
            vh=self.dd.ui.tableWidget.verticalHeader()
            for n in range(self.dd.ui.tableWidget.columnCount()):
                vh.resizeSection(n,self.dd.lpix[16])
            self.dd.ui.tableWidget.viewport().update()
            self.dd.moveEvent(None) # initialize sizes
            self.dd.ui.tableWidget.setSortingEnabled(True)
            self.redrawFlag=False
        if self.syncBlinkFlag: # set by syncCallback after each sync
            self.updateLinkLights(incidentLink=5)
            QTimer.singleShot(500,self.updateLinkLights)
            self.syncBlinkFlag=False


    def setPDFButton(self,outingNameOrRow,state):
        if isinstance(outingNameOrRow,int):
            row=outingNameOrRow
            outingName=self.dd.ui.tableWidget.item(row,0).text()
        elif isinstance(outingNameOrRow,str):
            outingName=outingNameOrRow
            row=-1
            if not outingName in self.dmd['outings'].keys():
                return False
            for n in range(self.dd.ui.tableWidget.rowCount()):
                v=self.dd.ui.tableWidget.item(n,0).text()
                logging.info('checking '+str(n)+': "'+str(v)+'"')
                if v==outingName:
                    logging.info('  match!')
                    row=n
                    break
            if row<0:
                logging.error('Call to setPDFButton but outing name "'+outingNameOrRow+'" was not found in the debrief outings table.')
                return False

        # state=changed: specified during callbacks, which aren't aware if a pdf has already been generated
        if state=='changed':
            [lastPDFCode,lastPDFTime]=self.dmd['outings'][outingName].get('PDF',[None,None])
            if lastPDFCode: # a PDF has previously been generated; set the icon to 'regen'
                state='old'
            else:
                state='gen'

        # state=gen: no pdf has been generated; show the initial black-arrow icon
        if state=='gen':
            icon=self.dd.ui.generatePDFIcon
            slot=self.PDFGenClicked
        # state=done: pdf successfully generated and (apparently) up-to-date; show the checked icon
        elif state=='done':
            icon=self.dd.ui.generatePDFDoneIcon
            slot=self.PDFDoneClicked
        # state=old: pdf previously generated but now out-of-date; show the refresh circle icon
        elif state=='old':
            icon=self.dd.ui.generatePDFRegenIcon
            slot=self.PDFRegenClicked
            
        button=QPushButton(icon,'')
        button.setIconSize(QSize(self.lpix[36],self.lpix[14]))
        # genPDFButton.icon().setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        button.clicked.connect(slot)
        self.dd.ui.tableWidget.setCellWidget(row,5,button)

    def syncCallback(self):
        # this function is probably called from a sync thread:
        #  can't create a timer or do some GUI operations from here, etc.
        self.syncBlinkFlag=True

    def debriefOptionsButtonClicked(self,*args,**kwargs):
        self.debriefOptionsDialog.show()
        self.debriefOptionsDialog.raise_()
    
    def editNoteClicked(self,*args,**kwargs):
        row=self.dd.ui.tableWidget.currentRow()
        outingName=self.dd.ui.tableWidget.item(row,0).text()
        logging.info('edit note clicked for outing '+outingName)
        rval=QInputDialog.getMultiLineText(self.dd,'Add Note','Add note for '+outingName+':')
        if rval[1]:
            text=rval[0]
            notes=self.dmd['outings'][outingName].get('notes',[])
            notes.append(text)
            self.dmd['outings'][outingName]['notes']=notes
            self.redrawFlag=True
            self.writeDmdFile()
        # logging.info('entered: '+str(text))

    def PDFGenClicked(self,*args,**kwargs):
        if not self.sts2.id:
            inform_user_about_issue("'id' is not defined for the debrief map session; cannot generarte PDF.'",parent=self.dd)
            return
        if not self.sts2.key:
            inform_user_about_issue("'key' is not defined for the debrief map session; cannot generarte PDF.'",parent=self.dd)
            return
        if not self.sts2.accountId:
            inform_user_about_issue("'accountId' is not defined for the debrief map session; cannot generarte PDF.'",parent=self.dd)
            return
        row=self.dd.ui.tableWidget.currentRow()
        outingName=self.dd.ui.tableWidget.item(row,0).text()
        logging.info('Generate PDF button clicked for outing '+outingName)
        outing=self.dmd['outings'][outingName]
        ids=[outing['bid']]
        ids.extend(outing['cids'])
        for tidList in outing['tids']:
            ids.extend(tidList)
        logging.info('ids for this outing:'+str(ids))
        bounds=self.sts2.getBounds(ids,padPct=15)

        # also print non-outing-related features
        # while there could be folders of non-outing-related features in the incident map,
        #  the debrief map should have no folders other than outings, so just checking
        #  for fetures that are not in folders should be sufficient
        nonOutingFeatureIds=[f['id'] for f in self.sts2.mapData['state']['features']
                if 'folderId' not in f['properties'].keys()
                and f['properties']['class'].lower() in ['marker','shape']]
        logging.info('non-outing ids:'+str(nonOutingFeatureIds))

        ids=ids+nonOutingFeatureIds

        lonMult=cos(radians((bounds[3]+bounds[1])/2.0))
        # logging.info('longitude multiplier = '+str(lonMult))

        # determine orientation from initial aspect ratio, then snap the bounds to
        #  letter-size aspect ratio (map tiles will only be rendered for this area)

        # calculate width, height, and aspect ratio in rectangular units, as they
        #   would appear on paper or on screen.  1' x 1' rectange will appear
        #   taller than it is wide, so w should be <1:
        w=(bounds[2]-bounds[0])*lonMult
        h=bounds[3]-bounds[1]
        ar=w/h
        # logging.info('bounds before adjust (ar='+str(round(ar,4))+') : '+str(bounds))

        if ar>1: # landscape
            size=[11,8.5]
            tar=1.4955 # target aspect ratio
        else: # portrait
            size=[8.5,11]
            tar=0.8027 # target aspect ratio

        # bounds adjustmets:
        # 1) initially, bounds are lat/lon extents; the aspect ratio on paper needs
        #     to account for the length of a unit of longitude at the given latitude
        # 2) after the bounds are unitized / rectangular units, extend on opposite
        #     sides/ends to fill the printable map area, to ensure the map layer
        #     is rendered for that entire area; if initial a.r. (w/h) is too low, pad
        #     left and right; if initial a.r. is too high, pad top and bottom            
        if ar<tar: # too narrow: pad left and right
            targetW=h*tar
            dw=targetW-w
            dlon=dw/lonMult
            # logging.info('landscape: need to grow longitude by '+str(dlon))
            bounds[0]=bounds[0]-(dlon/2)
            bounds[2]=bounds[2]+(dlon/2)
        elif ar>tar: # too wide: pad top and bottom
            targetH=w/tar
            dh=targetH-h
            # logging.info('need to grow latitude by '+str(dh))
            bounds[1]=bounds[1]-(dh/2)
            bounds[3]=bounds[3]+(dh/2)

        w=(bounds[2]-bounds[0])*lonMult
        h=bounds[3]-bounds[1]
        ar=w/h
        # logging.info('bounds after adjust (ar='+str(round(ar,4))+') : '+str(bounds))

        features=[f for f in self.sts2.mapData['state']['features'] if f['id'] in ids]

        # 'expires' should be 7 days from now; if it does expire
        #   before the search is done, that's not really a problem
        #   since the incident map remains
        tsNow=int(datetime.now().timestamp()*1000)
        timeText=time.strftime("%H:%M %m/%d/%Y")
        expires=tsNow+(7*24*60*60*1000)

        # process PDF options
        layerString='t' # default
        layerSelection=self.debriefOptionsDialog.ui.layerComboBox.currentText()
        logging.info('layerSelection='+str(layerSelection))
        for key in BASEMAP_REGEX.keys():
            logging.info('checking '+str(key))
            if re.match('.*'+key+'.*',layerSelection,re.IGNORECASE):
                layerString=BASEMAP_REGEX[key]
                logging.info('found!')
                break
        if self.debriefOptionsDialog.ui.contoursCheckbox.isChecked():
            layerString+=',c'
        if self.debriefOptionsDialog.ui.slopeShadingCheckbox.isChecked():
            layerString+=',sf'
        if self.debriefOptionsDialog.ui.mapBuilderOverlayCheckbox.isChecked():
            layerString+=',mba'
        logging.info('printing with layerstring='+str(layerString))
        grids=[]
        if self.debriefOptionsDialog.ui.utmGridCheckbox.isChecked():
            grids=['utm']
        payload={
            'properties':{
                'mapState':{
                    'type':'FeatureCollection',
                    'features':features
                },
                'layer':layerString,
                'grids':grids,
                'showOverview':False,
                'markupSize':1,
                'datum':'WGS84',
                'dpi':200,
                'title':outingName+'   '+timeText,
                'qrcode':None,
                'expires':expires,
                'pages':[{
                    'bbox':bounds,
                    'size':size
                }],
                'corners':{}
            }
        }

        # if the request is CTD, offer to retry to internet if CTD request fails
        attempt=1
        tryAgain=True
        if 'topo.com' in self.sts2.domainAndPort.lower():
            attempt=2
        printDomainAndPort=self.sts2.domainAndPort
        while tryAgain:
            tryAgain=False
            r=self.sts2.sendRequest('post','api/v1/acct/'+self.sts2.accountId+'/PDFLink',payload,returnJson='ID',domainAndPort=printDomainAndPort)
            if r:
                if isinstance(r,str):
                    logging.info(outingName+' : PDF generated : '+r+' - opening in new browser tab...')
                    webbrowser.open_new_tab(printDomainAndPort+'/p/'+r)
                    self.dmd['outings'][outingName]['PDF']=[r,tsNow]
                    self.setPDFButton(row,'done')
                    self.writeDmdFile()
                elif isinstance(r,dict) and dictHasAllKeys(r,['status','code','message']):
                    suffix=''
                    if 'account' in r['message'].lower():
                        suffix='\n\nMake sure your accountId in '+str(self.sts2.configpath)+' is valid and up to date.'
                    if attempt==1:
                        if ask_user_to_confirm('Print request failed.  Response from server:\n\n'+str(r['code'])+':'+r['status']+'\n'+r['message']+suffix+'\nWould you like to try sending the request to sartopo.com?',parent=self.dd):
                            attempt=2
                            printDomainAndPort='sartopo.com'
                            tryAgain=True
                else:
                    if attempt==1:
                        if ask_user_to_confirm('Print request failed.  See the log file for details.\nWould you like to try sending the request to sartopo.com?',parent=self.dd):
                            attempt=2
                            printDomainAndPort='sartopo.com'
                            tryAgain=True
            else:
                if attempt==1:
                    if ask_user_to_confirm('No response received from print request.  See the log file for details.\nWould you like to try sending the request to sartopo.com?',parent=self.dd):
                        attempt=2
                        printDomainAndPort='sartopo.com'
                        tryAgain=True

    def PDFDoneClicked(self,*args,**kwargs):
        self.PDFGenClicked(*args,**kwargs)

    def PDFRegenClicked(self,*args,**kwargs):
        self.PDFGenClicked(*args,**kwargs)



    # assignments={} # assignments dictionary
    # assignments_init={} # pre-filtered assignments dictionary (read from file on startup)

    # slot (handler) including confirmation dialog for rebuild-all happens inside the options dialog class
    def rebuildClicked(self,*args,**kwargs):
        row=self.dd.ui.tableWidget.currentRow()
        outingName=self.dd.ui.tableWidget.item(row,0).text()
        confirm=QMessageBox(QMessageBox.Warning,'Rebuild '+outingName+' ?',
                'Are you sure you want to rebuild outing "'+outingName+'" in the debrief map?\n\nAll related features on the debrief map will be deleted, causing those features to be recreated on the following sync cycle.',
                QMessageBox.Yes|QMessageBox.Cancel)
        r=confirm.exec()
        if r==QMessageBox.Yes:
            logging.info(outingName+' rebuild requested...')
            self.rebuild(outingName)

    def rebuild(self,outingNameOrAll):
        progressBox=QProgressDialog("Rebuilding, please wait...","Abort",0,100)
        # progressBox.setWindowModality(Qt.WindowModal)
        progressBox.setWindowTitle("Rebuilding")
        progressBox.show()
        progressBox.raise_()
        QCoreApplication.processEvents()
        # progressBox maximum = total number of ids to delete plus total number of incident map features
        self.sts1.syncPause=True
        self.writeDmdPause=True
        if outingNameOrAll==':ALL:':
            logging.info('inside rebuild: about to rebuild the entire debrief map')
            outingsToDelete=list(self.dmd['outings'].keys()) # wrapped in list() so it doesn't change as dmd changes
            tidCount=0
            for sid in self.dmd['corr']:
                tidCount+=len(self.dmd['corr'][sid])
            progressBox.setMaximum(tidCount+len(self.sts1.mapData['state']['features']))
        else:
            outingsToDelete=[outingNameOrAll]
            tidCount=2 # bid, fid; other item counts must be calculated
            o=self.dmd['outings'][outingNameOrAll]
            for tidlist in o['tids']:
                tidCount+=len(tidlist)
            tidCount+=len(o['utids'])
            tidCount+=len(o['cids'])
            progressBox.setMaximum(tidCount+len(self.sts1.mapData['state']['features']))
        progress=0
        for outingName in outingsToDelete:
            # steps needed to rebuild one outing:
            # 1. delete related features from the debrief map
            # 2. delete related entries from dmd['corr']
            # 3. delete entire outing sub-dictionary, dmd['outings'][<outingName>]
            # pause sync until the entire rebuild is done
            logging.info('inside rebuild: about to rebuild outing "'+outingName+'"')
            o=self.dmd['outings'][outingName]
            # logging.info(json.dumps(o,indent=3))
            shapes=[o['bid']] # boundary / begin the delete list
            for tidlist in o['tids']:
                if isinstance(tidlist,list):
                    shapes+=tidlist
            shapes+=o['utids'] # uncropped tracks
            markers=o['cids'] # clues
            folders=[o['fid']] # folders - should never be more than one; this is to provide one flat feature list
            deleteIds=shapes+markers+folders
            # logging.info('features that would be deleted:'+str(shapes+markers+folders))
            for shape in shapes:
                self.sts2.delFeature(id=shape,fClass='Shape')
                progress+=1
                progressBox.setValue(progress)
            for marker in markers: # clues
                self.sts2.delFeature(id=marker,fClass='Marker')
                progress+=1
                progressBox.setValue(progress)
            for folder in folders: # folder
                self.sts2.delFeature(id=folder,fClass='Folder')
                progress+=1
                progressBox.setValue(progress)
            # 2. remove entries for self.dmd['corr']
            keysToDelete=[]
            for sid in self.dmd['corr'].keys():
                newTids=[id for id in self.dmd['corr'][sid] if id not in deleteIds]
                self.dmd['corr'][sid]=newTids
                if len(newTids)==0:
                    keysToDelete.append(sid)
            for key in keysToDelete:
                del self.dmd['corr'][key]
            # inform_user_about_issue('pause...')
            # self.sts2.doSync()
            # 3. delete entire outing sub-dictionary
            del self.dmd['outings'][outingName]
            self.writeDmdFile()
            # inform_user_about_issue('pause...')
            # self.sts2.doSync()
            # inform_user_about_issue('pause...')
        #3b. for entire map rebuild, also delete any remaining features and their corr entries
        if outingNameOrAll==':ALL:':
            for sid in self.dmd['corr'].keys():
                for tid in self.dmd['corr'][sid]:
                    f=self.sts2.getFeature(id=tid)
                    if f: # if f is False, the feature was probably deleted by hand from the debrief map
                        tc=f['properties']['class']
                        self.sts2.delFeature(id=tid,fClass=tc)
                    progress+=1
                    progressBox.setValue(progress)
            self.dmd['corr']={}
        # 4. call newFeatureCallback on all features in the source map
        for f in self.sts1.mapData['state']['features']:
            self.newFeatureCallback(f)
            progress+=1
            progressBox.setValue(progress)
                # inform_user_about_issue('pause...')
        self.sts1.syncPause=False
        self.writeDmdPause=False
        self.writeDmdFile()
        progressBox.close()
        logging.info('rebuild complete')
        inform_user_about_issue('Rebuild complete.',QMessageBox.Information,title='Success',timeout=2500,parent=self.dd)
        if outingNameOrAll==':ALL:':
            for n in range(self.dd.ui.tableWidget.rowCount()):                
                self.setPDFButton(n,'gen')
        else:
            self.setPDFButton(self.dd.ui.tableWidget.currentRow(),'gen')

    # fids={} # folder IDs

    # correspondence dictionary (and json file) - serves two purposes:
    # 1. crash/restart recovery - on startup, the task is to import features from the source map
    #      which don't have any correspondence in the debrief map; this avoids the need
    #      to delete all features from the debrief map before startup
    # 2. applying source map edits to the debrief map - when a source map feature is
    #      edited or deleted, the correspondence dictionary will determine what debrief map
    #      feature(s) will receive the same edit/deletion

    # correspondence dict entries whose keys are source map assignment feature ids will
    #   be lists of lists: one list per pairing, where each list has folder id and boundary id
    #   (since the same source map assignment may have multiple pairings over time)

    # record pre-cropped and also post-cropped tracks in the correspondence dictionary;
    #  the dictionary consumers will need to check to see if each entry exists before applying
    #  any action.

    # corr={} # correspondence dictionary: key=source-map-ID, val=list-of-target-map-IDs
    # corr_init={} # pre-fitlered correspondence dictionary (read from file on startup)

    def initDmd(self):
        logging.info('initDmd called')
        if os.path.exists(self.dmdFileName):
            with open(self.dmdFileName,'r') as dmdFile:
                logging.info('reading correlation file '+self.dmdFileName)
                dmd_init=json.load(dmdFile)
                logging.info(json.dumps(dmd_init,indent=3))

            # build the real dmd dict, by only using the parts of dmd_init that still exist
            # (do not edit an object while iterating over it - that always gives bizarre results)
            sids=sum(self.sts1.mapData['ids'].values(),[])
            # logging.info('list of all sts1 ids:'+str(sids))
            tids=sum(self.sts2.mapData['ids'].values(),[])
            # logging.info('list of all sts2 ids:'+str(tids))
        # # sidsToRemove=[]
        # # for sid in corr.keys():
        # #     logging.info('checking sid '+sid+':'+str(corr[sid]))
        # #     for tid in corr[sid]:
        # #         logging.info(' checking tid '+tid)
        # #         if tid in tids:
        # #             logging.info('  not in debrief map; removing')
        # #             corr[sid].remove(tid)
        # #     if corr[sid]==[]:
        # #         logging.info(' sid '+sid+' no longer has any correspondence; will be removed from correlation dictionary')
        # #         sidsToRemove.append(sid)
            corr_init=dmd_init['corr']
            for sid in corr_init.keys():
                if sid in sids:
                    idListToAdd=[id for id in corr_init[sid] if id in tids]
                    if idListToAdd!=[]:
                        self.dmd['corr'][sid]=idListToAdd
            outings_init=dmd_init['outings']
            for ot in outings_init.keys():
                # preserve the outing if the sid, tid, and fid all exist
                o=outings_init[ot]
                logging.info(' checking for sid='+str(o['sid'])+'  bid='+str(o['bid'])+'  fid='+str(o['fid']))
                if o['sid'] in sids and (o['bid'] and o['bid'] in tids) and (o['fid'] and o['fid'] in tids):
                    logging.info('  initial outing preserved: '+ot)
                    self.dmd['outings'][ot]=o
                else:
                    logging.info('  outing discarded for now since not all of its required components currently exist in the debrief map: '+ot)
            # for sidToRemove in sidsToRemove:
            #     del corr[sidToRemove]
        # write the correspondence file
        self.writeDmdFile()
        # logging.info('dmd after filtering:')
        # logging.info(json.dumps(self.dmd,indent=3))

    # restart handling: read the assignments file (if any)
    # if path.exists(assignmentsFileName):
    #     with open(assignmentsFileName,'r') as assignmentsFile:
    #         logging.info('reading assignments file')
    #         assignments_init=json.load(assignmentsFile)
    #         logging.info(json.dumps(assignments_init,indent=3))

    # then get rid of id's that don't exist in the debrief map
    # for a in assignments_init:
    #     # create the assigmment entry even if the corresponding source id
    #     #  does not exist; that can't be checked until much later when 
    #     #  the first source map happens anyway
    #     ai=assignments_init[a]
    #     k=ai.keys()
    #     a_sid=ai['sid'] or None
    #     a_fid=None
    #     if 'fid' in k and ai['fid'] in tids:
    #         a_fid=ai['fid']
    #     a_bid=None
    #     if 'bid' in k and ai['bid'] in tids:
    #         a_bid=ai['bid']
    #     # remember a['tids'] is a list of lists: each list is a list of crop result ids,
    #     #   which is normally one line but could be several if the track wandered outside
    #     #   the crop boundary and back in again
    #     a_tids=[]
    #     for aitid_list in ai['tids']:
    #         atl=[x for x in aitid_list if x in tids]
    #         if atl:
    #             a_tids.append(atl) # to avoid appending an empty list
    #     # a_tids=[x for x in ai['tids'] if x in tids]
    #     a_cids=[x for x in ai['cids'] if x in tids]
    #     a_utids=[x for x in ai['utids'] if x in tids]
    #     if a_tids or a_cids or a_utids or a_fid or a_bid or a_sid:
    #         assignments[a]={
    #             'sid':a_sid,
    #             'bid':a_bid,
    #             'fid':a_fid,
    #             'tids':a_tids,
    #             'cids':a_cids,
    #             'utids':a_utids}

    #     # assignments[a]={}
    #     # assignments[a]['sid']=assignments_init[a]['sid'] # must assume the source assignment still exists
    #     # if assignments_init[a]['fid'] in tids:
    #     #     assignments[a]['fid']=assignments_init[a]['fid']
    #     # if assignments_init[a]['bid'] in tids:
    #     #     assignments[a]['bid']=assignments_init[a]['bid']
    #     # assignments[a]['tids']=[x for x in assignments_init[a]['tids'] if x in tids]
    #     # assignments[a]['cids']=[x for x in assignments_init[a]['cids'] if x in tids]
    #     # assignments[a]['utids']=[x for x in assignments_init[a]['utids'] if x in tids]
    #     # if assignments[a]['tids']==[] and assignments[a]['cids']==[] and assignments[a]['utids']==[] and 'bid' not in assignments[a].keys() and 'fid' not in assignments[a].keys()
    # # finally, prune any empty assignments; don't edit while iterating
    # assignmentsToDelete=[]
    # for at in assignments:
    #     a=assignments[at]
    #     if not a['bid'] and not a['fid'] and not a['tids'] and not a['cids'] and not a['utids']:
    #         assignmentsToDelete.append(at)
    # for atd in assignmentsToDelete:
    #     logging.info(' deleting empty assignment dict entry "'+atd+'"')
    #     del assignments[atd]
    # writeAssignmentsFile()
    # logging.info('assignments dict after pruning:'+json.dumps(assignments,indent=3))



    # efids=sts2.mapData['ids']['Folder'] # existing (debrief map) folder IDs
    # logging.info('Existing folder ids:'+str(efids))
    # for fid in efids:
    #     f=sts2.getFeatures(id=fid)[0]
    #     logging.info('  Folder:'+str(f))
    #     t=f['properties']['title']
    #     if t:
    #         logging.info('Detected existing folder '+t+' with id '+fid)
    #         fids[t]=fid

    # addCorrespondence - don't call this for assignments
    def addCorrespondence(self,sid,tidOrList):
        sf=self.sts1.getFeature(id=sid)
        if sf:
            if sf['properties']['class']=='Assignment':
                logging.error('addCorrespondence was called on an assignment feature; this should not happen')
                return
        else:
            logging.error('addCorrespondence: source feature not found using id '+str(sid))
        
        # turn the argument into a list if needed
        if not isinstance(tidOrList,list):
            tidOrList=[tidOrList]

        # create or add the correspondence entry
        for tid in tidOrList:
            self.dmd['corr'].setdefault(sid,[]).append(tid)

        # write the correspondence file
        self.writeDmdFile()

    def addOutingLogEntry(self,outingName,entryText):
        tsnow=int(datetime.now().timestamp()*1000)
        self.dmd['outings'][outingName]['log'].append([tsnow,entryText])
        self.redrawFlag=True
        self.writeDmdFile()

    def getOutingSuffixIndex(self,t):
        n=self.outingSuffixDict.get(t,2)
        self.outingSuffixDict[t]=n+1
        return n

    # def createOuting(t,sid):
    #     logging.info('creating outing '+t)
    #     # create the assignment folder if needed
    #     # if t in fids.keys():
    #     #     logging.info('   assignment folder already exists')
    #     #     fid=fids[t]
    #     # else:
    #     logging.info('   creating outing folder '+t)
    #     # if sid: # this function could be called before sid is known, but eventually it would be called again when sid is known
    #     #     addCorrespondence(sid,fid)

    # addOuting - arg fi = feature(dict) or id(36-char string)
    def addOuting(self,fi):
        id=None # source assignment id
        a=None # source assignmet object
        if isinstance(fi,dict):
            a=fi
            p=a['properties']
            t=p.get('title','').upper().rstrip() # assignments with letter but not number could end in space
            id=a['id']
        else: #string
            if len(fi)==36: # id
                id=fi
                a=self.sts1.getFeature(id=id)
                p=a['properties']
                t=p.get('title','').upper().rstrip() # assignments with letter but not number could end in space
            else: # non-id string was specified
                logging.error('addOuting was called with a non-ID string; skipping')
                return False
        
        # an assignment should not become an outing until it has both letter and number
        # if not (p.get('letter',None) and p.get('number',None)):
        # logging.info('properties:\n'+json.dumps(p,indent=3))
        if not (p['letter'] and p['number']):
            logging.info('addOuting called for assigment "'+t+'" that does not have both letter and number; skipping')
            return False

        # restart handling: only add a new outing if there is not already an outing
        #  that matches sid and title

        logging.info(' checking to see if this outing (title="'+t+'" id='+str(id)+') already exists...')
        alreadyExists=False
        for ot in self.dmd['outings'].keys():
            o=self.dmd['outings'][ot]
            osid=o.get('sid',None)
            # logging.info('  checking: outing title = '+str(ot)+', sid='+str(osid)+', id='+str(id))
            # if the outing was created in passing, i.e. during track or marker creation before assignment was processed,
            #  then sid will be null.  So how do we determine whether we should make a new outing?  For now, if sid is
            #  null, go ahead and make a new outing.  If there are actually multiple outings with the same name, then
            #  we have other issues to solve, i.e. which 'AA 101' outing does 'AA101a' belong to?  May be best to just
            #  prohibit identically named outings.
            if osid==id:
                logging.info('  outing "'+ot+'" with the same sid was found...')
                if t==ot or 'NOTITLE' in ot:
                    logging.info('   and the title is a match or contains NOTITLE')
                    alreadyExists=True
                    # on restart:
                    #  - if existing assignment title was changed before restart, it will be added as a new outing
                    #  - if existing assignment geometry was changed before restart, update the geometry of
                    #      only the CURRENT outing's boundary (with matching title): previous outing boundaries
                    #      are part of the record and should not be changed; future outing boundaries will be imported anew
                    #      using the new geometry anyway
                    bid=o.get('bid',None)
                    if bid:
                        ag=a['geometry']
                        b=self.sts2.getFeature(id=bid)
                        bg=b['geometry']
                        if ag!=bg:
                            logging.info('    boundary geometry has changed; updating it now')
                            self.sts2.editFeature(id=bid,geometry=ag)
                    break
                else:
                    logging.info('   but the title is not a match, so it must be a previous outing')
            elif ot==t and not osid:
                logging.info('  an outing with the same name but null sid was found; assuming it is a match and setting its sid')
                alreadyExists=True
                self.dmd['outings'][ot]['sid']=id
                break
        if alreadyExists:
            logging.info('  yes, a correpsonding outing already exists on the debrief map')
            obid=o.get('bid',None)
            fid=o['fid']
            if obid:
                logging.info('  and the existing outing has a boundary; skipping')
                return False
            else:
                logging.info('  but the existing outing has no boundary; adding boundary now')
        else:
            logging.info('  no, the outing does not already exist; adding it now')

            # if t is currently blank, set it to 'NOTITLE' for clarity;
            # dict key must be unique; if an entry by the same name already exists,
            #  append an incrementing suffix
            if t=='':
                t='NOTITLE'
            if t in self.dmd['outings'].keys():
                t=t+':'+str(self.getOutingSuffixIndex(t))
                logging.info('   assignment entry with the same name already exists; setting this assignment title to '+t)

            # createOuting(t,id)
            self.dmd['outings'][t]={
                'bid':None,
                'fid':None,
                'sid':id,
                'cids':[],
                'tids':[],
                'utids':[],
                'log':[]}
            if not a: # boundary not defined; add a log entry now
                self.addOutingLogEntry(t,'Outing entry created')
            fid=self.sts2.addFolder(t)
            # fids[t]=fid
            self.dmd['outings'][t]['fid']=fid
            # fid=dmd['outings'][t]['fid']
            self.dmd['outings'][t]['sid']=id # assignment feature id in source map
            # logging.info('fids.keys='+str(fids.keys()))
            self.checkForOrphans(t)
        if a:
            g=a['geometry']
            gc=g['coordinates']
            gt=g['type']
            if gt=='Polygon':
                logging.info('drawing boundary for area assignment '+t)
                bid=self.sts2.addPolygon(gc[0],title=t,folderId=fid,strokeWidth=8,strokeOpacity=0.4,fillOpacity=0.0)
            elif gt=='LineString':
                logging.info('drawing boundary for line assignment '+t)
                bid=self.sts2.addLine(gc,title=t,folderId=fid,width=8,opacity=0.4)
            else:
                logging.error('newly detected assignment '+t+' has an unhandled geometry type '+gt)
                return
            self.dmd['outings'][t]['bid']=bid
            self.addOutingLogEntry(t,'Added assignment boundary')
            # addCorrespondence(id,bid)
            logging.info('boundary created for assignment '+t+': '+self.dmd['outings'][t]['bid'])
            # if the assignment is tiny, it's probably a roaming assignment
            [lon1,lat1,lon2,lat2]=self.sts2.getBounds([bid])
            # logging.info('bounds:'+str([lon1,lat1,lon2,lat2]))
            if abs(lon2-lon1)*111111*cos(radians(lat1))<self.roamingThresholdMeters or abs(lat2-lat1)*111111<self.roamingThresholdMeters:
                logging.info('  assignment '+t+' is tiny; it looks like an assignment for a roaming team')
                self.dmd['outings'][t]['crop']=self.roamingCropDegrees

        # since addLine adds the new feature to .mapData immediately, no new 'since' request is needed
        # if self.dmd['outings'][t]['utids']!=[]:
        self.cropUncroppedTracks()
        self.writeDmdFile()

    # check for orphan tracks (properly-named tracks that were processed before this outing was created)
    #  and bring them into the specified outing as uncropped tracks
    def checkForOrphans(self,outingTitle):
        cleanedIDs=[]
        for otid in self.orphanTracksDict.keys():
            ott=self.orphanTracksDict[otid]
            tparse=self.parseTrackName(ott)
            if tparse:
                if tparse[0]+' '+tparse[1]==outingTitle:
                    logging.info('Previously imported track "'+ott+'" appears to belong to newly imported outing "'+outingTitle+'".  Importing the uncropped track to the outing.')
                    self.sts2.editFeature(id=otid,className='Shape',properties={'folderId':self.dmd['outings'][outingTitle]['fid']})
                    self.dmd['outings'][outingTitle]['utids'].append(otid)
                    self.addOutingLogEntry(outingTitle,'Imported existing track: '+ott)
                    # don't delete while iterating
                    cleanedIDs.append(otid)
        for cleanedID in cleanedIDs:
            del self.orphanTracksDict[cleanedID]

    def addShape(self,f,outingLogMessageOverride=None):
        p=f['properties']
        g=f['geometry']
        gt=g['type']
        gc=g['coordinates']
        t=p['title'].rstrip() # assignments with letter but not number could end in space
        sid=f['id']
        if gt=='LineString':
            # how should a new line be processed?
            # Q1 - does it have a properly formatted track name (outing name followed by a letter suffix)?
            #   Q1=YES:
            #     Q2 - does the specified outing already exist?
            #       Q2=YES: import it to the outing (folder, color, crop)
            #       Q2=NO: import it as a non-owned line (to the default folder) and add to 'orphan track' list
            #           (if the outing name was accurate and the outing has just not been imported yet,
            #            this track should be brought into the outing folder, and cropped, when the
            #            outing is created; if the outing name was not accurate, and the outing by that
            #            name is never imported, the line will be left in the default folder, which is fine)
            #   Q1=NO: import it as a non-owned line (to the default folder)
            color=p['stroke']
            saveAsOrphan=False
            tparse=self.parseTrackName(t)
            if tparse: # Q1=YES
                ot=tparse[0]+' '+tparse[1] # 'AA 101' - should match a folder name
                o=self.dmd['outings'].get(ot,None)
                color=self.trackColorDict.get(tparse[2].lower(),'#444444')
                t=tparse[0].upper()+tparse[1]+tparse[2].lower()
                if o: # Q2=YES
            # if len(tparse)<3 or tparse[2]=='': # it's not a track
            # else: # it's a track; crop it now if needed, since newFeatureCallback is called once per feature, not once per sync interval
            #     ot=tparse[0]+' '+tparse[1] # 'AA 101' - should match a folder name
            #     # logging.info('entire assignments dict:')
            #     # logging.info(json.dumps(self.dmd['outings'],indent=3))
            #     o=self.dmd['outings'].get(ot,None)
            #     # if o==None: # assignment entry hasn't been created yet
            #     #     logging.info('Processing line \''+t+'\' which appears to belong to outing \''+ot+'\' which has not been processed yet.  Creating the outing dictionary and adding this track to the uncropped tracks list.')
            #     #     self.addOuting(ot)
            #     #     o=self.dmd['outings'][ot]
            #     if o: # add the line in the assignment folder, and crop to the assignment shape
                    logging.info('creating line \''+t+'\' in folder \''+ot+'\'')
                    logging.info('  outing fid='+o['fid'])
                    bid=o['bid']
                    uncroppedTrack=self.sts2.addLine(gc,title=t,color=color,folderId=o['fid'])
                    logging.info(' generated uncropped track '+uncroppedTrack)
                    # if bid==None:
                        # logging.info('  assignment boundary has not been processed yet; saving the uncropped track in utids')
                        # self.dmd['outings'][ot]['utids'].append(uncroppedTrack)
                        # self.addCorrespondence(sid,uncroppedTrack)
                        # # logging.info('  utids:'+str(assignments[ot]['utids']))
                    if bid:
                        # logging.info('  outing bid='+bid)
                        # if cropDegrees is specified in dmd, use that value; otherwise use the default
                        cropDegrees=self.dmd['outings'][ot].get('crop',self.cropDegrees)
                        croppedTrackList=self.sts2.crop(uncroppedTrack,o['bid'],beyond=cropDegrees)
                        if croppedTrackList: # the crop worked
                            self.dmd['outings'][ot]['tids'].append(croppedTrackList)
                            self.addCorrespondence(sid,croppedTrackList)
                        else: # the crop did not work
                            self.dmd['outings'][ot]['utids'].append(uncroppedTrack)
                            self.addCorrespondence(sid,uncroppedTrack)
                        # sts2.doSync(once=True)
                        # sts2.crop(track,o['bid'],beyond=0.001) # about 100 meters
                    else:
                        logging.error('  assignment boundary has not been processed yet!  How did we get here?')
                    msg='Added track '+t
                    if outingLogMessageOverride:
                        msg=outingLogMessageOverride+' '+t
                    self.addOutingLogEntry(ot,msg)
                    self.writeDmdFile()
                    return
                else: # Q2=NO
                    # orphanTrack=self.sts2.addLine(gc,title=title,color=color)
                    logging.info('Newly detected line '+t+': name does appear to indicate association with outing '+ot+', but, that outing has not yet been processed.  Importing the line as an un-owned feature, which will automatically be processed for the outing later if/when an outing with matching name is imported.')
                    saveAsOrphan=True
            else: # Q1=NO
                logging.info('Newly detected line '+t+': name does not appear to indicate association with an assignment')
            # Q1=NO or Q2=NO
            logging.info('creating line \''+t+'\' in default folder')
            lineID=self.sts2.addLine(gc,title=t,
                    color=color,
                    description=p['description'],
                    opacity=p['stroke-opacity'],
                    width=p['stroke-width'],
                    pattern=p['pattern'])
            self.addCorrespondence(sid,lineID)
            if saveAsOrphan:
                self.orphanTracksDict[lineID]=t
        elif gt=='Polygon':
            logging.info('creating polygon \''+t+'\' in default folder')
            polygonID=self.sts2.addPolygon(gc[0],
                title=t,
                stroke=p['stroke'],
                strokeWidth=p['stroke-width'],
                strokeOpacity=p['stroke-opacity'],
                fillOpacity=p['fill-opacity'],
                description=p['description'])
            self.addCorrespondence(sid,polygonID)
        # logging.info('dmd:\n'+str(json.dumps(self.dmd,indent=3)))

    def addMarker(self,f):
        p=f['properties']
        g=f['geometry']
        gt=g['type']
        if gt!='Point':
            logging.info('attempting to add a marker whose geometry type is '+gt+'; skipping')
            return(-1)
        t=p['title']
        gc=g['coordinates']
        logging.info('creating marker \''+t+'\' in default folder')
        markerID=self.sts2.addMarker(gc[1],gc[0],title=t,
                        color=p.get('marker-color',None),
                        rotation=p.get('marker-rotation',None),
                        size=p.get('marker-size',1),
                        description=p['description'],
                        symbol=p['marker-symbol'])
        # logging.info('sts2.mapData after addMarker:'+json.dumps(self.sts2.mapData,indent=3))
        self.addCorrespondence(f['id'],markerID)

    def addClue(self,f):
        p=f['properties']
        g=f['geometry']
        gt=g['type']
        if gt!='Point':
            logging.info('attempting to add a clue whose geometry type is '+gt+'; skipping')
            return(-1)
        t=p['title']
        gc=g['coordinates']
        logging.info('creating clue \''+t+'\' in default folder')
        clueID=self.sts2.addMarker(gc[1],gc[0],title=t,symbol='clue',description=p['description'])
        aid=p['assignmentId']
        # add outing now if not already done
        outingNames=[name for name in self.dmd['outings'] if self.dmd['outings'][name]['sid']==aid]
        if not outingNames:
            logging.info('  The assignment that owns the clue does not yet have an outings dictionary.  Adding the outing now.')
            self.addOuting(aid)
        outingName=[name for name in self.dmd['outings'] if self.dmd['outings'][name]['sid']==aid][0]
        self.dmd['outings'][outingName]['cids'].append(clueID)
        self.addOutingLogEntry(outingName,'Added clue '+t)
        self.addCorrespondence(f['id'],clueID)

    def cropUncroppedTracks(self):
        # logging.info('inside cropUncroppedTracks:')
        for outingName in self.dmd['outings']:
            utids=self.dmd['outings'][outingName]['utids']
            if len(utids)>0:
                bid=self.dmd['outings'][outingName]['bid']
                if bid is not None:
                    logging.info('  Outing '+outingName+': cropping '+str(len(utids))+' uncropped track(s):'+str(utids))
                    for utid in utids:
                        # since newly created features are immediately added to the local cache,
                        #  the boundary feature should be available by this time
                        # if crop is specified in dmd, use that value; otherwise use the default
                        # TODO: allow selection of an existing shape to use as the crop boundary, rather than distance
                        cropDegrees=self.dmd['outings'][outingName].get('crop',self.cropDegrees)
                        croppedTrackLines=self.sts2.crop(utid,bid,beyond=cropDegrees)
                        # logging.info('crop return value:'+str(croppedTrackLines))
                        self.dmd['outings'][outingName]['tids'].append(croppedTrackLines)
                        # cropped track line(s) should correspond to the source map line, 
                        #  not the source map assignment; source map line id will be
                        #  the corr key whose val is the utid; also remove the utid
                        #  from that corr val list
                        # logging.info('    corr items:'+str(corr.items()))
                        slidList=[list(i)[0] for i in self.dmd['corr'].items() if list(i)[1]==[utid]]
                        if len(slidList)==1:
                            slid=slidList[0]
                            # logging.info('    corresponding source line id:'+str(slid))
                            self.dmd['corr'][slid]=[]
                            self.addCorrespondence(slid,croppedTrackLines)
                        else:
                            logging.error('    corresponding source map line id could not be determined')
                            logging.error('    corresponding source line id list:'+str(slidList))
                        # assignments[a]['utids'].remove(utid)
                    self.dmd['outings'][outingName]['utids']=[] # don't modify the list during iteration over the list!
                    # self.writeDmdFile()
                else:
                    logging.info('  Outing '+outingName+' has '+str(len(self.dmd['outings'][outingName]['utids']))+' uncropped tracks, but the boundary has not been imported yet; skipping.')


    # initialNewFeatureCallback: since dmd must be generated before the add<Type> functions
    #  are called (since those functions check to see if the feature already exists on the
    #  debrief map, to prevent duplicates), the actual new feature actions must not be called
    #  until after dmd is generated (by initDmd).  But, the list of actions to take must be
    #  generated 
    # def initialNewFeatureCallback(self,f):

    # criteria for a 'match': if a feature exists on the debrief map meeting these criteria,
    #   then it corresponds to the newly read source map feature: don't create a new feature
    #   on the debrief map; instead, make an entry in corr{} and update the debrief map feature
    #   if needed; we should be pretty strict here, since any non-matching debrief map features
    #   can be deleted, and the newly imported feature can be used instead
    #  folder: target title is identical to source title
    #  marker: 
    def newFeatureCallback(self,f,outingLogMessageOverride=None):
        # this function could be called from multiple places:
        # - startup (__init__ just after initDmd)
        # - doSync
        # - propertyUpdateCallback
        # - geometryUpdateCallback
        # this function is probably called from a sync thread:
        #  can't create a timer or do some GUI operations from here, etc.
        self.updateLinkLights(debriefLink=10)
        p=f['properties']
        c=p['class']
        t=p.get('title','').rstrip() # assignments with letter but not number could end in space
        sid=f['id']

        logging.info('newFeatureCallback: class='+c+'  title='+t+'  id='+sid+'  syncing='+str(self.sts1.syncing))

        # source id might have a corresponding target id; if all corresponding target ids still exist, skip    
        tids=sum(self.sts2.mapData['ids'].values(),[])    
        if sid in self.dmd['corr'].keys():
            logging.info(' source feature exists in correspondence dictionary')
            tparse=self.parseTrackName(t)
            if tparse:
                ot=tparse[0]+' '+tparse[1]
                if ot not in self.dmd['outings'].keys():
                    logging.info('  debrief map does not yet have an outing named "'+ot+'" - adding this line to the orphan list, hopefully to be picked up later')
                    for tid in self.dmd['corr'][sid]:
                        self.orphanTracksDict[tid]=t
            if all(i in tids for i in self.dmd['corr'][sid]):
                logging.info('  all corresponding features exist in the debrief map')
                if len(self.dmd['corr'][sid])==1:
                    tid=self.dmd['corr'][sid][0]
                    tf=self.sts2.getFeature(id=tid)
                    tfp=tf['properties']
                    g=f.get('geometry',None)
                    tfg=tf.get('geometry',None)
                    if tfp==p and tfg==g:
                        logging.info('   properties and geometry are unchanged; moving on...')
                    else:
                        # update un-owned features, but leave owned features alone since they have already been colored and cropped
                        allTidLists=[self.dmd['outings'][ot]['tids'] for ot in self.dmd['outings'].keys()]
                        # flatten a two-level nested list with possible empty members
                        #  https://stackoverflow.com/a/952952
                        allTids=[a for b in [a for b in allTidLists for a in b] for a in b]
                        if tid not in allTids: # only check the first corresponding feature; should be sufficient
                            logging.info('   properties and/or geometry have changed; updating debrief map feature')
                            self.sts2.editFeature(id=tid,properties=p,geometry=g)
                        # assignment boundary geometry change before restart is handled inside addOuting
                # dead code since assignments don't exist in corr:
                # crop uncropped tracks even if the assignment already exists in the target;
                #  this will crop any tracks that were imported anew on restart
                # if c=='Assignment':
                #     self.cropUncroppedTracks()
                #     self.writeDmdFile()
                self.updateLinkLights()
                return
            else:
                logging.info('  but debrief map does not contain all of the specified features; adding the feature to the debrief map')
        elif c!='Assignment': # don't show a message for assignments, since addOuting will determine if it needs to be added
            logging.info(' no correspondence entry found; adding the feature to the debrief map')

        if c=='Assignment':
            self.addOuting(f)

        # new assignment:
        # 1. add a folder with name = assignment title (include the team# - we want one folder per pairing)
        # 2. add a shape (line or polygon) in that folder, with same geometry as the assignment
        # if c=='Assignment':
        #     t=t.upper()

        #     # create the assignment folder if needed
        #     if t in fids.keys():
        #         fid=fids[t]
        #     else:
        #         fid=sts2.addFolder(t)
        #         fids[t]=fid
            
        #     # logging.info('fids.keys='+str(fids.keys()))
        #     g=f['geometry']
        #     gc=g['coordinates']
        #     gt=g['type']
        #     if gt=='Polygon':
        #         existingAssignment=sts2.getFeatures(featureClass=c,title=t)[0]
        #         if existingAssignment:
        #             sts2.editFeature(id=existingAssignment['id'],geometry=g)
        #         else:
        #             sts2.addPolygon(gc[0],title=t,folderId=fid)
        #     elif gt=='LineString':
        #         sts2.addLine(gc,title=t,folderId=fid)
        #     else:
        #         logging.error('newly detected assignment '+t+' has an unhandled geometry type '+gt)
        #         return False

    #     # new shape:
    #     # 1. if line:
    #     #   a. if title indicates it's a track:
    #     #     i. create a new line with same geometry in the assignment folder
    #     #     - creaete the assignment folder if it doesn't already exist; the assignment feature
    #     #        may not have been processed yet
    #     #   b. otherwise:
    #     #     i. create a new line with same geometry in the default folder
    #     # 2. if polygon:
    #     #   a. create a new polygon with the same geometry in the default folder

        elif c=='Shape':
            self.addShape(f,outingLogMessageOverride)
            # g=f['geometry']
            # gc=g['coordinates']
            # gt=g['type']
    # #         # if gt=='Polygon':
    # #         #     sts2.addPolygon(gc[0],title=t,folderId=fid)
            # if gt=='LineString':
            #     tparse=re.split('(\d+)',t.upper().replace(' ',''))
            #     if len(tparse)==3 and tparse[2]=='':
            #         logging.info()
    #                 logging.error('new line '+t+' detected, but name does not appear to indicate a track')
    #                 return False
    #             at=tparse[0]+' '+tparse[1] # 'AA 101' - should match a folder name
    #             # logging.info('at='+at)
    #             # logging.info('fids.keys='+str(fids.keys()))
    #             a=assignments[at]
                
    #             # create the assignment folder if needed
    #             if at in fids.keys():
    #                 fid=fids[at]
    #             else:
    #                 fid=sts2.addFolder(t)
    #                 fids[t]=fid

    #             # add the line in the assignment folder, and crop to the assignment shape
    #             color=trackColorList[len(a['utids'])+len(a['tids'])]
    #             track=sts2.addLine(gc,title=tparse[0].upper()+tparse[1]+tparse[2].lower(),color=color,folderId=fid)
    #             sts2.doSync(once=True) # since crop needs updated .mapData
    #             sts2.crop(track,at,beyond=0.001) # about 100 meters
    #             a['tids'].append(track)
    #             logging.info(' generated track '+track)

    #         else:
    #             logging.error('new feature '+t+' has an unhandled geometry type '+gt)
    #             return False

            # new marker:
            #  add the new marker in the default markers folder

        elif c=='Marker':
            self.addMarker(f)

        elif c=='Clue':
            self.addClue(f)
        
            # new clue:
            #  add a new marker in the assignment folder, using the clue symbol

            # for folder in sts2.getFeatures('Folder',timeout=10):
            #     if folder['properties']['title']==t:
            #         sts2.addLine(f['geometry']['coordinates'],title=t,folderId=folder['id'],timeout=10)
            #         # sts2.editFeature(id=id,properties={'folderId':folder['id']})
        self.updateLinkLights() # set back to previous colors

    # handle these cases:
    #  1 - name change from a non-track to a track ('CURRRENT TRACK' --> 'AA101a')
    #  2 - name change from a track to a non-track ('AA101a' --> 'junk')
    #  3 - name change from a track to a track in a different assignment/pairing ('AA101a' --> 'AA102a')
    #  4 - name change from a track to a track with different suffix only ('AA101a' --> 'AA101b')
    # in each of these cases it's easier to delete the old feature(s) and re-import the new feature;
    # basically, if it's a Shape/LineString, delete and re-import; additional logic could make this
    #  more specific and less destructive, but there's probably no need
    #  5 - assignment name change rules: by the time tracks are obtained, the assignment feature on the
    #        source map will likely have had the number removed from its title (since the team is
    #        no longer working in that assignment).  How to deal with this?  If each 'assignment' on
    #        the debrief map is actually thought of as a past-or-present 'pairing' or 'outing', it
    #        makes more sense: once an assignment feature is imported with a 'full' title
    #        (letter and number), don't change it on the debrief map even when that assignment's
    #        number changes on the source map.  If the number changes to blank on the source map,
    #        make no change on the debrief map.  If the number changes to another number on the source
    #        map, re-import and create a new pairing (folder and boundary) on the debrief map. 
    def propertyUpdateCallback(self,f):
        # this function is probably called from a sync thread:
        #  can't create a timer or do some GUI operations from here, etc.
        self.updateLinkLights(debriefLink=10)
        # logging.info('propertyUpdateCallback:'+str(json.dumps(f,indent=3)))
        sid=f['id']
        sp=f['properties']
        sc=sp['class']
        st=sp['title'].rstrip() # assignments with letter but not number could end in space
        sgt=self.sts1.getFeature(id=sid)['geometry']['type']
        logging.info('propertyUpdateCallback called for '+sc+':'+st)
        # determine which target-map feature, if any, corresponds to the edited source-map feature
        if sid in self.dmd['corr'].keys(): # this means there's a match but it's not an outing
            corrList=self.dmd['corr'][sid]
            if sc=='Shape' and sgt=='LineString':
                for ttid in corrList:
                    self.sts2.delFeature(id=ttid,fClass='Shape')
                # also delete from the assignments dict and correspondence dict, so that it will be added anew;
                # we can't be sure here what assignment if any the line was previously a part of,
                #  so scan all assignments for id(s)
                # tparse=parseTrackName(st)
                # if tparse:
                for ot in self.dmd['outings']:
                    # at=tparse[0]+' '+tparse[1]
                    # don't modify list while iterating!
                    newTidList=[]
                    for tidList in self.dmd['outings'][ot]['tids']:
                        if not all(elem in tidList for elem in corrList):
                            newTidList.append(tidList)
                    self.dmd['outings'][ot]['tids']=newTidList
                del self.dmd['corr'][sid]
                self.newFeatureCallback(f,outingLogMessageOverride='Reimported track "'+st+'" due to property changes') # this will crop the track automatically
            elif len(corrList)==1: # exactly one correlating feature exists
                logging.info(' exactly one debrief map feature corresponds to the source map feature; updating the debrief map feature properties')
                tf=self.sts2.getFeature(id=corrList[0])
                tp=tf['properties']
                # map properties from source to target, based on source class; start with the existing target
                #  map feature properties, and only copy the appropriate properties from the source feature
                if sc=='Clue':
                    logging.info('  mapping properties from Clue to Marker')
                    taid=tp['assignmentId']
                    said=tp['assignmentId']
                    outingNames=self.dmd['outings'].keys()
                    targetOutingName=[x for x in outingNames if self.dmd['outings'][x]['sid']==taid][0]
                    sourceOutingName=[x for x in outingNames if self.dmd['outings'][x]['sid']==said][0]
                    if taid!=said:
                        self.dmd['outings'][targetOutingName].remove(sid)
                        self.addOutingLogEntry(targetOutingName,'Moved clue '+st+' from this outing to '+sourceOutingName)
                        self.addClue(f)
                    if tp['title']!=st:
                        self.addOutingLogEntry(targetOutingName,'Clue title changed: '+tp['title']+' --> '+st)
                    tp['title']=st
                    tp['description']=sp['description']
                elif sc=='Assignment': # this may be dead code - if assignment, it should have two corr entries
                    tp['title']=st
                else:
                    tp=sp # for other feature types, copy all properties from source
                self.sts2.editFeature(id=corrList[0],properties=tp)
            else:
                logging.error(' property change: more than one debrief map feature correspond to the source map feature, which is not a line; no changes made to debrief map')
        elif sc=='Assignment':
            self.addOuting(f)
            # # handle these cases:
            # #   (use longhand logic - don't try logic reductions - then do a catch-all at the end)
            # # 1. no outing exists with matching sid
            # #     blank --> letter only
            # #     letter only --> different letter only
            # #     letter only --> blank
            # #     blank --> letter and number
            # #     letter only --> letter and number
            # #      --> it wasn't an outing before: call addOuting, which will only import it as an outing
            # #           if it has letter and number
            # # 2. letter and number --> same letter, different number
            # #      --> do NOT change existing debrief map outing; create a new debrief map
            # #          outing (folder, boundary, assignments dict, fids dict) with new title;
            # #          check for orphans
            # # 3. letter and number --> same letter, no number
            # #    all other cases
            # #      --> no change to debrief map or assignments/fids dicts
            # olist=[o for o in self.dmd['outings'] if self.dmd['outings'][o]['sid']==sid]
            # st=st.upper()
            # if len(olist)==0: # case 1
            #     # was previously an assignment without both letter and number, which is not an outing; add outing now if needed
            #     logging.error(' source map assignment feature edited, but it has no corresponding debrief map feature')
            #     self.addOuting(f)
            #     self.updateLinkLights() # set back to previous colors
            #     return
            # elif len(olist)==1: # cases 2 and 3
            #     # oldf=sts2.getFeature(id=corrList[0])
            #     # oldTitle=oldf['properties']['title']
            #     oldTitle=olist[0]
            #     oldTitleHasNumber=any(char.isdigit() for char in oldTitle)
            #     newTitleHasNumber=any(char.isdigit() for char in st)
            #     logging.info(' assignment name change: "'+oldTitle+'" --> "'+st+'"')
            #     # logging.info(json.dumps(self.dmd['outings'],indent=3))

            #     # case 1:
            #     if (oldTitle=='' or 'NOTITLE' in oldTitle) or (not oldTitleHasNumber and newTitleHasNumber):
            #     # if newTitleHasNumber: # cases 1 and 2 (case 3 needs to action)
            #     #     if oldTitleHasNumber: # case 2
            #     #         newFeatureCallback(f)
            #     #     else: # case 1
            #         logging.info('  existing debrief map assignment title will be updated...')
            #         o=self.dmd['outings'][oldTitle]
            #         for tid in [o['bid'],o['fid']]:
            #             tf=self.sts2.getFeature(id=tid)
            #             tp=tf['properties']
            #             tp['title']=st
            #             self.sts2.editFeature(id=tid,properties=tp)
            #         self.dmd['outings'][st]=self.dmd['outings'][oldTitle]
            #         self.addOutingLogEntry(tp['title'],'Outing name changed: '+oldTitle+' --> '+st)
            #         # fids[tp['title']]=fids[oldTitle]
            #         del self.dmd['outings'][oldTitle]
            #         self.checkForOrphans(st)
            #         # del fids[oldTitle]

            #     # case 2:
            #     elif (oldTitleHasNumber and newTitleHasNumber):
            #         logging.info('  existing debrief map assignment will not be changed; importing to a new assignment...')
            #         self.newFeatureCallback(f)
            #         self.checkForOrphans(st)

            #     # case 3 / all other cases:
            #     else:
            #         logging.info('  no change needed to existing debrief map assignments')

            #     # logging.info('new assignments dict:')
            #     # logging.info(json.dumps(dmd['outings'],indent=3))
            #     self.cropUncroppedTracks()
            #     self.writeDmdFile()
            # else:
            #     logging.info('  more than one existing debrief map outing corresponds to the source map assignment; nothing edited due to ambuguity')
        else:
            logging.info('  source map feature does not have any corresponding feature in debrief map; nothing edited')
        self.updateLinkLights() # set back to previous colors

    # parseTrackName: return False if not a track, or [assignment,team,suffix] if a track
    def parseTrackName(self,t):
        tparse=re.split('(\d+)',t.upper().replace(' ','')) # can result in empty string element(s)
        if '' in tparse:
            tparse.remove('')
        if len(tparse)==3:
            return tparse
        else:
            return False

    def geometryUpdateCallback(self,f):
        # this function is probably called from a sync thread:
        #  can't create a timer or do some GUI operations from here, etc.
        self.updateLinkLights(debriefLink=10)
        sid=f['id']
        sp=f['properties']
        st=sp['title'].rstrip() # assignment with letter but no number could end with space
        sc=sp['class']
        sg=f['geometry']
        osids=[self.dmd['outings'][x]['sid'] for x in self.dmd['outings'].keys()] # list of sid of all outings
        logging.info('osids:'+str(osids))
        # if the edited source feature is a track (a linestring with appropriate name format),
        #  delete all corresponding debrief map features (the crop operation could have resulted in
        #  multiple lines) then re-import the feature from scratch, which will also re-crop it;
        # otherwise, edit the geometry of all corresponding features that have a geometry entry
        #  (i.e. when an assigment boundary is edited, the assignment folder has no geometry)
        # if assignment geometry is edited, consider the following:
        #  - don't edit the geometry for any previous outing boundaries (i.e. if it currently has a
        #     number, and there are additional outing(s) with numbers, edit the current one
        #     but not the previous ones)

        logging.info('geometryUpdateCallback called for '+sc+':'+st)
        if sid in self.dmd['corr'].keys():
            tparse=self.parseTrackName(st)
            if sg['type']=='LineString' and sp['class']=='Shape' and tparse:
                logging.info('  edited feature '+st+' appears to be a track; correspoding previous imported and cropped tracks will be deleted, and the new track will be re-imported (and re-cropped)')
                corrList=self.dmd['corr'][sid]
                for ttid in corrList:
                    self.sts2.delFeature(id=ttid,fClass='Shape')
                # also delete from the assignments dict and correspondence dict, so that it will be added anew
                at=tparse[0]+' '+tparse[1]
                # don't modify list while iterating!
                newTidList=[]
                for tidList in self.dmd['outings'][at]['tids']:
                    if not all(elem in tidList for elem in corrList):
                        newTidList.append(tidList)
                self.dmd['outings'][at]['tids']=newTidList
                del self.dmd['corr'][sid]
                self.newFeatureCallback(f,outingLogMessageOverride='Reimported track due to geometry change:') # this will crop the track automatically
            else:
                for tid in self.dmd['corr'][sid]:
                    if 'geometry' in self.sts2.getFeature(id=tid).keys():
                        logging.info('  corresponding debrief map feature '+tid+' has geometry; setting it equal to the edited source feature geometry')
                        self.sts2.editFeature(id=tid,geometry=sg)
                        # Is it a clue?  If so, add an outing log entry
                        outingNames=[x for x in self.dmd['outings'].keys() if tid in self.dmd['outings'][x]['cids']]
                        if outingNames:
                            self.addOutingLogEntry(outingNames[0],'Geometry edited for '+st)
                    else:
                        logging.info('  corresponding debrief map feature '+tid+' has no geometry; no edit performed')
        elif sid in osids:
            for ot in self.dmd['outings'].keys():
                o=self.dmd['outings'][ot]
                if o['sid']==sid and ot==st: # the title is current
                    logging.info('  assignment geometry was edited: applying the same edit to corresponding debrief map boundary that has the same title "'+st+'" as the edited feature (to preserve previous outing boundaries)')
                    self.sts2.editFeature(id=o['bid'],geometry=sg)
                    self.addOutingLogEntry(ot,'Geometry edited for assignment boundary')
        # # 1. determine which target-map feature, if any, corresponds to the edited source-map feature
        # if sid in corr.keys():
        #     cval=corr[sid]
        #     logging.info('cval:'+str(cval))
        #     if len(cval)==1: # exactly one corresponding feature exists
        #         logging.info('exactly one debrief map feature corresponds to the source map feature; updating the debrief map feature geometry')
        #         sts2.editFeature(id=cval[0],geometry=sg)
        #         # if it was a track, delete all corresponding debrief map features, then re-import (which will re-crop it)
        #         if sg['type']=='LineString':
        #             for a in assignments:
        #                 logging.info('  checking assignment: tids='+str(assignments[a]['tids']))
        #                 if cval[0] in assignments[a]['tids']:
        #                     logging.info('  the updated geometry is a track belonging to '+assignments[a]['title']+': will re-crop using the new geometry')
        #                     sts2.crop(cval[0],assignments[a]['bid'],beyond=0.001)
        #     else:
        #         logging.info('more than one existing debrief map feature corresponds to the source map feature; nothing edited due to ambuguity')
        else:
            logging.info('source map feature does not have any corresponding feature in debrief map; nothing edited')
        self.updateLinkLights() # set back to previous colors

    # note that the argument to deletedFeatureCallback is just the source map id
    def deletedFeatureCallback(self,sid):
        # this function is probably called from a sync thread:
        #  can't create a timer or do some GUI operations from here, etc.
        self.updateLinkLights(debriefLink=10)
        # sid=f['id']
        logging.info('deletedFeatureCallback called for source map feature with id '+str(sid)+' :')
        # logging.info(json.dumps(f,indent=3))
        # 1. determine which target-map feature, if any, corresponds to the edited source-map feature
        # logging.info('corr keys:')
        # logging.info(str(dmd['corr'].keys()))
        # logging.info('dmd:\n'+str(json.dumps(self.dmd,indent=3)))
        found=False
        if sid in self.dmd['corr'].keys():
            cval=self.dmd['corr'][sid]
            for tid in cval:
                logging.info('deleting corresponding debrief map feature with id '+tid)
                tidTitle=self.sts2.getFeature(id=tid)['properties']['title']
                self.sts2.delFeature(id=tid)
                # remove owned features from outings dict as needed
                for outingName in self.dmd['outings'].keys():
                    o=self.dmd['outings'][outingName]
                    # owned clues
                    if tid in o['cids']:
                        o['cids'].remove(tid)
                        self.addOutingLogEntry(outingName,'Clue deleted: '+tidTitle)
                        found=True
                    # owned uncropped tracks
                    elif tid in o['utids']:
                        o['utids'].remove(tid)
                        self.addOutingLogEntry(outingName,'Track deleted: '+tidTitle)
                        found=True
                    # owned tracks (nested list of segments)
                    else:
                        for trackList in o['tids']:
                            if tid in trackList:
                                trackList.remove(tid)
                                found=True
                            # also remove any zero-length track lists
                            if len(trackList)==0:
                                o['tids'].remove(trackList)
                                self.addOutingLogEntry(outingName,'Track deleted: '+tidTitle)
                    # outing sid are not currently listed in corr
                # remove from orphanTracksDict if needed
                if tid in self.orphanTracksDict.keys():
                    del self.orphanTracksDict[tid]
            del self.dmd['corr'][sid] # not currently iterating, so, del should be fine
        if not found:
            deleteOutingName=None
            # delete the entire outing only if it has no clues or tracks
            for outingName in self.dmd['outings'].keys():
                o=self.dmd['outings'][outingName]
                if o['sid']==sid:
                    if o['tids']==[] and o['cids']==[] and o['utids']==[]:
                        # don't delete while iterating
                        deleteOutingName=outingName
                    else:
                        logging.info('debrief map outing "'+outingName+'" exists, but it has clues and/or tracks, so will not be deleted')
                    found=True
                    break
            if deleteOutingName:
                logging.info('debrief map outing "'+deleteOutingName+'" exists and has no clues or tracks; deleting boundary, folder, and outing database entry now')
                bid=self.dmd['outings'][deleteOutingName]['bid']
                self.sts2.delFeature(id=bid)
                fid=self.dmd['outings'][deleteOutingName]['fid']
                self.sts2.delFeature(id=fid,fClass='Folder')
                del self.dmd['outings'][deleteOutingName]
        self.writeDmdFile()
        self.redrawFlag=True
        self.updateLinkLights() # set back to previous colors




    # initial sync is different than callback handling because:
    #    ...
    #
    # on the initial sync, pay attention to the sequence:
    # 1. read assignments from source map: create folders and boundary shapes in debrief map
    # 2. read shapes from source map: for completed search tracks (based on name),
    #      draw the line in the debrief map assignment folder
    # 3. perform a fresh since request on debrief map, so that newly
    #      drawn lines will appear in .mapData as needed by crop()
    # 4. in debrief map, color the tracks in alphabetical order
    # 5. in debrief map, crop tracks to assigment boundaries

    # # 1. read assignments
    # for f in sts1.getFeatures(featureClass='Assignment'):
    #     addAssignment(f)
        
    # # 2. read shapes
    # for f in sts1.getFeatures('Shape'):
    #     addShape(f)

    # for f in sts1.getFeatures('Marker'):
    #     addMarker(f)

    # for f in sts1.getFeatures('Clue'):
    #     addClue(f)

    # # 3. do a new since request in the debrief map
    # sts2.doSync(once=True)

    # 4. color the tracks in alphabetical order



    # initial processing complete; now register the callback
    # sts1.newFeatureCallback=newFeatureCallback


class DebriefOptionsDialog(QDialog,Ui_DebriefOptionsDialog):
    def __init__(self,parent):
        QDialog.__init__(self)
        self.parent=parent
        self.ui=Ui_DebriefOptionsDialog()
        self.ui.setupUi(self)
        self.ui.rebuildAllButton.clicked.connect(self.rebuildAllButtonClicked)
        self.onLayerComboChange()
        self.ldpi=0
        self.moveTimer=QTimer(self)
        self.moveTimer.timeout.connect(self.moveTimeout)

    def onLayerComboChange(self,*args,**kwargs):
        text=self.ui.layerComboBox.currentText()
        # only allow contours checkbox when NAIP imagery is selected; if so,
        #  check contours by default but let the user uncheck
        if 'naip' in text.lower():
            self.ui.contoursCheckbox.setChecked(True)
            self.ui.contoursCheckbox.setEnabled(True)
        else:
            self.ui.contoursCheckbox.setChecked(False)
            self.ui.contoursCheckbox.setEnabled(False)
        # only allow MapBuilder Overlay if MapBuilder topo or hybrid is not selected;
        #  check by default but let the user uncheck
        if 'mapbuilder' in text.lower():
            self.ui.mapBuilderOverlayCheckbox.setChecked(False)
            self.ui.mapBuilderOverlayCheckbox.setEnabled(False)
        else:
            self.ui.mapBuilderOverlayCheckbox.setChecked(True)
            self.ui.mapBuilderOverlayCheckbox.setEnabled(True)

    def rebuildAllButtonClicked(self,*args,**kwargs):
        confirm=QMessageBox(QMessageBox.Warning,'Rebuild All?',
                'Are you sure you want to rebuild the entire debrief map?\n\nAny work you did by hand on the debrief map will be lost.\n\nAll features on the debrief map will be deleted, causing the entire debrief map to be rebuilt on the following sync cycle.\n\nFor large maps, this will cause a lot of network traffic and may slow everything else down while the rebuild is in progress.',
                QMessageBox.Yes|QMessageBox.Cancel)
        r=confirm.exec()
        if r==QMessageBox.Yes:
            logging.info('Full debrief map rebuild requested...')
            self.close()
            self.parent.rebuild(':ALL:')

    def moveEvent(self,event):
        self.setMinimumSize(0,0)
        self.setMaximumSize(10000,10000)
        self.moveTimer.start(100)
        super(DebriefOptionsDialog,self).moveEvent(event)

    def moveTimeout(self,*args):
        # logging.info('move ended')
        self.moveTimer.stop()
        [x,y,w,h]=self.geometry().getRect()
        # logicalDotsPerInch seems to give a bit better match across differently scaled extended screen
        #  than physicalDotsPerInch - though not exactly perfect, probably due to testing on monitors
        #  with different physical sizes; but logicalDotsPerInch incorporates Windows display zoom,
        #  while physicalDotsPerInch does not
        ldpi=self.screen().logicalDotsPerInch()
        if ldpi!=self.ldpi:
            pix=genLpix(ldpi)
            # logging.info(self.__class__.__name__+' window moved: new logical dpi='+str(ldpi)+'  new 12pt equivalent='+str(pix[12])+'px')
            self.ldpi=ldpi
            # self.parent.lpix=pix
            # self.lpix=pix

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
                QDialog{
                    padding:'''+str(pix[6])+'''px;
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
                QHeaderView::section{
                    border-style:none;
                }
                QHeaderView::section:horizontal{
                    border-bottom:'''+str(pix[2])+'''px solid gray;
                }
                QMessageBox,QDialogButtonBox{
                    icon-size:'''+str(pix[36])+'''px '''+str(pix[36])+'''px;
                }''')
            # now set the sizes that don't respond to stylesheets for whatever reason
            initialSize=QSize(int(500*(self.ldpi/96)),int(395*(self.ldpi/96)))
            self.setMinimumSize(initialSize)
            self.setMaximumSize(initialSize)


class DebriefDialog(QDialog,Ui_DebriefDialog):
    def __init__(self,parent):
        self.parent=parent
        QDialog.__init__(self)
        self.ui=Ui_DebriefDialog()
        self.ui.setupUi(self)
        self.ldpi=0
        
        self.ui.editNoteIcon=QtGui.QIcon()
        self.ui.editNoteIcon.addPixmap(QtGui.QPixmap(":/plans_console/edit_icon.png"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.ui.generatePDFIcon=QtGui.QIcon()
        self.ui.generatePDFIcon.addPixmap(QtGui.QPixmap(":/plans_console/generate_pdf_gen.png"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.ui.generatePDFDoneIcon=QtGui.QIcon()
        self.ui.generatePDFDoneIcon.addPixmap(QtGui.QPixmap(":/plans_console/generate_pdf_done.png"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.ui.generatePDFRegenIcon=QtGui.QIcon()
        self.ui.generatePDFRegenIcon.addPixmap(QtGui.QPixmap(":/plans_console/generate_pdf_regen.png"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.ui.rebuildIcon=QtGui.QIcon()
        self.ui.rebuildIcon.addPixmap(QtGui.QPixmap(":/plans_console/reload-icon.png"),QtGui.QIcon.Normal,QtGui.QIcon.Off)

        self.ui.tableWidget.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.moveEvent(None) # initialize sizes
    
    def resizeTableColumns(self):
        self.ui.tableWidget.setColumnWidth(0,int(80*(self.ldpi/96)))
        self.ui.tableWidget.setColumnWidth(1,int(60*(self.ldpi/96)))
        self.ui.tableWidget.setColumnWidth(2,int(60*(self.ldpi/96)))
        self.ui.tableWidget.setColumnWidth(3,int(20*(self.ldpi/96)))
        self.ui.tableWidget.horizontalHeader().setSectionResizeMode(4,1)
        self.ui.tableWidget.setColumnWidth(5,int(70*(self.ldpi/96)))
        self.ui.tableWidget.setColumnWidth(6,int(70*(self.ldpi/96)))

    def moveEvent(self,event):
        screen=self.screen()
        # logicalDotsPerInch seems to give a bit better match across differently scaled extended screen
        #  than physicalDotsPerInch - though not exactly perfect, probably due to testing on monitors
        #  with different physical sizes; but logicalDotsPerInch incorporates Windows display zoom,
        #  while physicalDotsPerInch does not
        ldpi=screen.logicalDotsPerInch()
        if ldpi!=self.ldpi:
            pix=genLpix(ldpi)
            logging.debug(self.__class__.__name__+' window moved: new logical dpi='+str(ldpi)+'  new 12pt equivalent='+str(pix[12])+'px')
            self.ldpi=ldpi
            self.parent.lpix=pix
            self.lpix=pix

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
                QDialog{
                    padding:'''+str(pix[6])+'''px;
                }
                QLineEdit{
                    height:'''+str(pix[16])+'''px;
                }
                QMessageBox,QDialogButtonBox{
                    icon-size:'''+str(pix[36])+'''px '''+str(pix[36])+'''px;
                }''')
            # # now set the sizes that don't respond to stylesheets for whatever reason
            self.ui.incidentLinkLight.setFixedWidth(pix[18])
            self.ui.debriefLinkLight.setFixedWidth(pix[18])
            for n in range(self.ui.tableWidget.rowCount()):
                self.ui.tableWidget.cellWidget(n,3).setIconSize(QtCore.QSize(pix[14],pix[14]))
                self.ui.tableWidget.cellWidget(n,5).setIconSize(QtCore.QSize(pix[36],pix[14]))
                self.ui.tableWidget.cellWidget(n,6).setIconSize(QtCore.QSize(pix[14],pix[14]))
            vh=self.ui.tableWidget.verticalHeader()
            for n in range(self.ui.tableWidget.columnCount()):
                vh.resizeSection(n,pix[16])
            self.ui.topLayout.setContentsMargins(pix[6],pix[6],pix[6],pix[6])
            self.ui.debriefOptionsButton.setIconSize(QtCore.QSize(pix[24],pix[24]))
            self.setMinimumSize(QtCore.QSize(int(500*(ldpi/96)),int(500*(ldpi/96))))
            self.setMaximumSize(QtCore.QSize(int(800*(ldpi/96)),screen.size().height()-50))
            self.ui.verticalLayout.setSpacing(pix[6])
            self.resizeTableColumns()
        if event:
            event.accept()

    def closeEvent(self,event):
        (self.parent.debriefX,self.parent.debriefY,self.parent.debriefW,self.parent.debriefH)=self.geometry().getRect()
        if self.parent.pc:
            self.parent.parent.debriefX=self.parent.debriefX
            self.parent.parent.debriefY=self.parent.debriefY
            self.parent.parent.debriefW=self.parent.debriefW
            self.parent.parent.debriefH=self.parent.debriefH
        super(DebriefDialog,self).closeEvent(event)


    # def showEvent(self,*args,**kwargs):
    #     if self.pc:
    #         self.ui.incidentMapField.setText(self.parent.incidentURL)
    #         self.ui.incidentLinkLight.setStyleSheet(self.parent.ui.incidentLinkLight.styleSheet())

    # refresh the display
    # provide for two modes of operation:
    # 1. this computer is running the debrief map generator
    #   the debrief map data file is available, so all data can be shown in the dialog
    # 2. a different computer is running the debrief map generator
    #   the debrief map data file is not available, so not all data can be shown

    # def refresh(self):


if __name__ == '__main__':
	dmg=DebriefMapGenerator(None,'9B1','UG1')