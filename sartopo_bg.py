from sartopo_python import SartopoSession
import logging
import re
import time
import os
import sys
import json
from os import path

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debrief_ui import Ui_DebriefDialog
from debriefMapDialog_ui import Ui_DebriefMapDialog

LINK_LIGHT_STYLES={
    -1:"background-color:#bb0000", # red - no link / link error
    0:"background-color:#aaaaaa", # gray - no link attempted
    1:"background-color:#009900", # medium green - good link
    10:"background-color:#00ff00", # light green - good link, sync in progress
    100:"background-color:#00ffff" # cyan - data change in progress
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
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))
    QMessageBox(QMessageBox.Critical,'Ungaught exception.\n\nSee transcript or log file.')
sys.excepthook = handle_exception

# sourceMap and targetMap arguments can be one of:
#  SartopoSession instance
#  map ID (end of URL)
#  complete URL

# in the last two cases, a new instance of SartopoSession will be created


# To redefine basicConfig, per stackoverflow.com/questions/12158048
# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
if os.path.isfile('dmg.log'):
    os.remove('dmg.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        # setting the filehandeler to write mode here causes the file
        #  to get deleted and overwritten when the threads end; so
        #  instead set it to append here, and take care of deleting it
        #  or rotating it at the top level
        logging.FileHandler('dmg.log','a'),
        # logging.FileHandler(self.fileNameBase+'_bg.log','w'),
        logging.StreamHandler(sys.stdout)
    ]
)

def inform_user_about_issue(message: str, icon: QMessageBox.Icon = QMessageBox.Critical, parent: QObject = None, title="", timeout=0):
	opts = Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowStaysOnTopHint
	if title == "":
		title = "Warning" if (icon == QMessageBox.Warning) else "Error"
	buttons = QMessageBox.StandardButton(QMessageBox.Ok)
	box = QMessageBox(icon, title, message, buttons, parent, opts)
	box.show()
	QCoreApplication.processEvents()
	box.raise_()
	if timeout:
		QTimer.singleShot(timeout,box.close)
	box.exec_()


class DebriefMapGenerator():
    def __init__(self,parent,sourceMap,targetMap):
        self.parent=parent
        # is this being spawned from Plans Console?
        self.pc=self.parent.__class__.__name__=='PlansConsole'
        self.debriefURL=''
        # do not register the callbacks until after the initial processing; that way we
        #  can be sure to process existing assignments first

        # assignments - dictionary of dictionaries of assignment data; each assignment sub-dictionary
        #   is created upon processing of the first feature that appears to be related to the assigment,
        #   based on title ('AA101' for assignment features, or 'AA101a' for lines, possibly including space(s))
        # NOTE - we really want to be able to recreate the ID associations at runtime (what target map
        #   feature corresponds to what source map feature) rather than relying on a correspondence file,
        #   but that would require a place for metadata on the target map features.  Maybe the target map
        #   details / description field could be used for this?  Any new field added here just gets deleted
        #   by sartopo.  How important is it to keep this ID correspondence?  IS title sufficient?
        #  key = assignment title (name and number; i.e. we want one dict entry per pairing/'outing')
        #  val = dictionary
        #     bid - id of boundary feature (in the target map)
        #     fid - id of folder feature (in the target map)
        #     sid - id of the assignment feature (in the SOURCE map)
        #     cids - list of ids of associated clues (in the target map)
        #     tids - list of ids of associated tracks (in the target map)
        #     utids - list of uncropped track ids (since the track may be processed before the boundary)

        # sourceMapID='V80'
        # targetMapID='0SD' # must already be a saved map

        self.dd=DebriefDialog()

        # determine / create SartopoSession objects
        #  process the target session first, since nocb definition checks for it

        # determine / create sts2 (target map SartopoSession instance)
        self.sts2=None
        tcn=targetMap.__class__.__name__           
        if tcn=='SartopoSession':
            logging.info('Target map argument = SartopoSession instance')
            self.sts2=targetMap
            self.targetDomainAndPort=self.sts2.domainAndPort
            self.targetMapID=self.sts2.mapID
        elif tcn=='str':
            logging.info('Target map argument = string')
            self.targetDomainAndPort='localhost:8080'
            targetParse=targetMap.split('/')
            self.targetMapID=targetParse[-1]
            self.debriefURL=self.targetDomainAndPort+'/m/'+self.targetMapID
            if targetMap.lower().startswith('http'):
                self.debriefURL=targetMap
                self.targetDomainAndPort=targetParse[2]
        else:
            logging.info('No debrief map; raising DebriefMapDialog')
            self.debriefMapDialog=DebriefMapDialog(self)
            self.debriefMapDialog.exec() # force modal
            # logging.info('No target map; using default')
            # self.targetDomainAndPort='localhost:8080'
            # self.targetMapID='81M'
        
        if not self.sts2:
            box=QMessageBox(
                QMessageBox.NoIcon, # other vaues cause the chime sound to play
                'Connecting...',
                'Debrief Map:\n\nConnecting to '+self.debriefURL+'\n\nPlease wait...')
            box.setStandardButtons(QMessageBox.NoButton)
            box.show()
            QCoreApplication.processEvents()
            box.raise_()
            self.sts2=SartopoSession(self.targetDomainAndPort,self.targetMapID,
                sync=False,
                syncTimeout=10,
                syncDumpFile='../../'+self.targetMapID+'.txt')
            box.close()

        if self.sts2 and self.sts2.apiVersion<0:
            inform_user_about_issue('Link to specified debrief map '+self.debriefURL+' could not be established.  Please try again.')
            return

        # determine / create sts1 (source map SartopoSession instance)
        self.sts1=None
        scn=sourceMap.__class__.__name__
        if scn=='SartopoSession':
            logging.info('Source map argument = SartopoSession instance: '+sourceMap.domainAndPort+'/m/'+sourceMap.mapID)
            self.sts1=sourceMap
            self.sourceMapID=self.sts1.mapID
            self.sourceDomainAndPort=self.sts1.domainAndPort
        elif scn=='str':
            logging.info('Source map argument = string')
            self.sourceDomainAndPort='localhost:8080'        
            sourceParse=sourceMap.split('/')
            self.sourceMapID=sourceParse[-1]
            if sourceMap.lower().startswith('http'):
                self.sourceDomainAndPort=sourceParse[2]
            try:
                self.sts1=SartopoSession(self.sourceDomainAndPort,self.sourceMapID,
                    syncDumpFile='../../'+self.sourceMapID+'.txt',
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

        if self.pc:
            self.dd.ui.incidentMapField.setText(self.parent.incidentURL)

        # self.sourceMapID=sourceMapID
        # self.targetMapID=targetMapID # must already be a saved map
        self.fileNameBase=self.sourceMapID+'_'+self.targetMapID
        self.dmdFileName=self.fileNameBase+'.json'
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
            
        self.dmd={} # master map data and correspondence dictionary - short for 'Debrief Map Data'
        self.dmd['outings']={}
        self.dmd['corr']={}

        self.outingSuffixDict={} # index numbers for duplicate-named assignments
        # def writeAssignmentsFile():
        #     # write the correspondence file
        #     with open(assignmentsFileName,'w') as assignmentsFile:
        #         assignmentsFile.write(json.dumps(assignments,indent=3))

        # # open a session on the target map first, since nocb definition checks for it
        # if not self.sts2:
        #     try:
        #         self.sts2=SartopoSession(self.targetDomainAndPort,self.targetMapID,
        #             sync=False,
        #             syncTimeout=10,
        #             syncDumpFile='../../'+self.targetMapID+'.txt')
        #     except:
        #         sys.exit()

        # if not self.sts1:  
        #     try:
        #         self.sts1=SartopoSession(self.sourceDomainAndPort,self.sourceMapID,
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
            #  to prevent duplicate feature creation in the target map on restart
            self.sts1.newFeatureCallback=self.newFeatureCallback
            self.sts1.propertyUpdateCallback=self.propertyUpdateCallback
            self.sts1.geometryUpdateCallback=self.geometryUpdateCallback
            self.sts1.deletedFeatureCallback=self.deletedFeatureCallback
        
            if not self.sts1.sync:
                self.sts1.start()

        self.updateLinkLights()

        # need to run this program in a loop - it's not a background/daemon process
        # while True:
        #     time.sleep(5)
        #     logging.info('dmd:\n'+str(json.dumps(self.dmd,indent=3)))
        # return # why would it need to run in a loop?  Maybe that was tru before it was QtIzed

    def updateLinkLights(self,incidentLink=None,debriefLink=None):
        incidentLink=incidentLink or self.sts1.apiVersion
        self.dd.ui.incidentLinkLight.setStyleSheet(LINK_LIGHT_STYLES[incidentLink])
        if self.pc:
            self.parent.ui.incidentLinkLight.setStyleSheet(LINK_LIGHT_STYLES[incidentLink])
        if self.sts2:
            debriefLink=debriefLink or self.sts2.apiVersion
            self.dd.ui.debriefLinkLight.setStyleSheet(LINK_LIGHT_STYLES[debriefLink])
            if self.pc:
                self.parent.ui.debriefLinkLight.setStyleSheet(LINK_LIGHT_STYLES[debriefLink])

    def writeDmdFile(self):
        with open(self.dmdFileName,'w') as dmdFile:
            dmdFile.write(json.dumps(self.dmd,indent=3))
        # populate the table
        row=0
        self.dd.ui.tableWidget.setSortingEnabled(False)
        outings=self.dmd.get('outings',None)
        self.dd.ui.tableWidget.setRowCount(len(outings))
        for outingName in outings:
            self.dd.ui.tableWidget.setItem(row,0,QTableWidgetItem(outingName))
            self.dd.ui.tableWidget.setItem(row,1,QTableWidgetItem(str(len(self.dmd['outings'][outingName]['tids']))))
            self.dd.ui.tableWidget.setItem(row,2,QTableWidgetItem(str(len(self.dmd['outings'][outingName]['cids']))))
            row+=1
        self.dd.ui.tableWidget.viewport().update()

    # assignments={} # assignments dictionary
    # assignments_init={} # pre-filtered assignments dictionary (read from file on startup)



    # fids={} # folder IDs

    # correspondence dictionary (and json file) - serves two purposes:
    # 1. crash/restart recovery - on startup, the task is to import features from the source map
    #      which don't have any correspondence in the target map; this avoids the need
    #      to delete all features from the target map before startup
    # 2. applying source map edits to the target map - when a source map feature is
    #      edited or deleted, the correspondence dictionary will determine what target map
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
        if path.exists(self.dmdFileName):
            with open(self.dmdFileName,'r') as dmdFile:
                logging.info('reading correlation file')
                dmd_init=json.load(dmdFile)
                logging.info(json.dumps(dmd_init,indent=3))

            # build the real dmd dict, by only using the parts of dmd_init that still exist
            # (do not edit an object while iterating over it - that always gives bizarre results)
            sids=sum(self.sts1.mapData['ids'].values(),[])
            logging.info('list of all sts1 ids:'+str(sids))
            tids=sum(self.sts2.mapData['ids'].values(),[])
            logging.info('list of all sts2 ids:'+str(tids))
        # # sidsToRemove=[]
        # # for sid in corr.keys():
        # #     logging.info('checking sid '+sid+':'+str(corr[sid]))
        # #     for tid in corr[sid]:
        # #         logging.info(' checking tid '+tid)
        # #         if tid in tids:
        # #             logging.info('  not in target map; removing')
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
                    logging.info('initial outing preserved: '+ot)
                    self.dmd['outings'][ot]=o
                else:
                    logging.info('initial outing discarded: '+ot)
            # for sidToRemove in sidsToRemove:
            #     del corr[sidToRemove]
        # write the correspondence file
        self.writeDmdFile()
        logging.info('dmd after filtering:')
        logging.info(json.dumps(self.dmd,indent=3))

    # restart handling: read the assignments file (if any)
    # if path.exists(assignmentsFileName):
    #     with open(assignmentsFileName,'r') as assignmentsFile:
    #         logging.info('reading assignments file')
    #         assignments_init=json.load(assignmentsFile)
    #         logging.info(json.dumps(assignments_init,indent=3))

    # then get rid of id's that don't exist in the target map
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



    # efids=sts2.mapData['ids']['Folder'] # existing (target map) folder IDs
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

    # addOuting - arg ft = feature(dict) or title(string)
    def addOuting(self,ft):
        if isinstance(ft,dict):
            p=ft['properties']
            t=p.get('title','').upper()
            id=ft['id']
        else: # string was specified: source map assignment feature doesn't exist yet
            t=ft
            id=None

        # restart handling: only add a new outing if there is not already an outing
        #  that matches sid and title

        logging.info('checking to see if this outing (title='+t+' id='+str(id)+') already exists...')
        alreadyExists=False
        for ot in self.dmd['outings'].keys():
            o=self.dmd['outings'][ot]
            logging.info('  checking: outing title = '+ot+', sid='+o['sid']+', id='+id)
            if o['sid']==id:
                logging.info('  an outing with the same sid was found...')
                if t==ot or 'NOTITLE' in ot:
                    logging.info('    and the title is a match or contains NOTITLE')
                    alreadyExists=True
                    break
                else:
                    logging.info('    but the title is not a match, so it must be an old outing')
        if alreadyExists:
            logging.info('yes, a correpsonding outing already exists on the target map; skipping')
            return False
        else:
            logging.info('no, the outing does not already exist; adding it now')

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
            'utids':[]}
        fid=self.sts2.addFolder(t)
        # fids[t]=fid
        self.dmd['outings'][t]['fid']=fid
        # fid=dmd['outings'][t]['fid']
        self.dmd['outings'][t]['sid']=id # assignment feature id in source map
        # logging.info('fids.keys='+str(fids.keys()))

        if id:
            g=ft['geometry']
            gc=g['coordinates']
            gt=g['type']
            logging.info('drawing boundary polygon for assignment '+t)
            if gt=='Polygon':
                bid=self.sts2.addPolygon(gc[0],title=t,folderId=fid,strokeWidth=8,strokeOpacity=0.4,fillOpacity=0.0)
            elif gt=='LineString':
                bid=self.sts2.addLine(gc,title=t,folderId=fid,width=8,opacity=0.4)
            else:
                logging.error('newly detected assignment '+t+' has an unhandled geometry type '+gt)
                return
            self.dmd['outings'][t]['bid']=bid
            # addCorrespondence(id,bid)
            logging.info('boundary created for assingment '+t+': '+self.dmd['outings'][t]['bid'])
        # since addLine adds the new feature to .mapData immediately, no new 'since' request is needed
        if self.dmd['outings'][t]['utids']!=[]:
            self.cropUncroppedTracks()
        self.writeDmdFile()

    def addShape(self,f):
        p=f['properties']
        g=f['geometry']
        gt=g['type']
        gc=g['coordinates']
        t=p['title']
        sid=f['id']
        if gt=='LineString':
            tparse=self.parseTrackName(t)
            # if len(tparse)<3 or tparse[2]=='': # it's not a track
            if not tparse:
                logging.info('newly detected line '+t+': name does not appear to indicate association with an assignment')
                logging.info('creating line \''+t+'\' in default folder')
                lineID=self.sts2.addLine(gc,title=t,
                        color=p['stroke'],
                        description=p['description'],
                        opacity=p['stroke-opacity'],
                        width=p['stroke-width'],
                        pattern=p['pattern'])
                self.addCorrespondence(sid,lineID)
            else: # it's a track; crop it now if needed, since newFeatureCallback is called once per feature, not once per sync interval
                at=tparse[0]+' '+tparse[1] # 'AA 101' - should match a folder name
                # logging.info('entire assignments dict:')
                # logging.info(json.dumps(self.dmd['outings'],indent=3))
                a=self.dmd['outings'].get(at,None)
                if a==None: # assignment entry hasn't been created yet
                    logging.info('processing line \''+t+'\' which appears to belong to assignment \''+at+'\' which has not been processed yet.  Creating the assignment dictionary and adding this track to the uncropped tracks list.')
                    self.addOuting(at)
                    a=self.dmd['outings'][at]
                # add the line in the assignment folder, and crop to the assignment shape
                logging.info('creating line \''+t+'\' in folder \''+at+'\'')
                logging.info('  assignment fid='+a['fid'])
                bid=a['bid']
                # color=trackColorList[(len(a['tids'])+len(a['utids']))%len(trackColorList)]
                color=self.trackColorDict.get(tparse[2].lower(),'#444444')
                uncroppedTrack=self.sts2.addLine(gc,title=tparse[0].upper()+tparse[1]+tparse[2].lower(),color=color,folderId=a['fid'])
                logging.info(' generated uncropped track '+uncroppedTrack)
                if bid==None:
                    logging.info('   assignment boundary has not been processed yet; saving the uncropped track in utids')
                    self.dmd['outings'][at]['utids'].append(uncroppedTrack)
                    self.addCorrespondence(sid,uncroppedTrack)
                    # logging.info('  utids:'+str(assignments[at]['utids']))
                else:
                    logging.info('  assignment bid='+bid)
                    croppedTrackList=self.sts2.crop(uncroppedTrack,a['bid'],beyond=0.001) # about 100 meters
                    self.dmd['outings'][at]['tids'].append(croppedTrackList)
                    self.addCorrespondence(sid,croppedTrackList)
                    # sts2.doSync(once=True)
                    # sts2.crop(track,a['bid'],beyond=0.001) # about 100 meters
                self.writeDmdFile()
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
        outingName=[name for name in self.dmd['outings'] if self.dmd['outings'][name]['sid']==aid][0]
        self.dmd['outings'][outingName]['cids'].append(clueID)
        self.addCorrespondence(f['id'],clueID)

    def cropUncroppedTracks(self):
        # logging.info('inside cropUncroppedTracks:')
        for a in self.dmd['outings']:
            if len(self.dmd['outings'][a]['utids'])>0:
                bid=self.dmd['outings'][a]['bid']
                if bid is not None:
                    logging.info('  Assignment '+a+': cropping '+str(len(self.dmd['outings'][a]['utids']))+' uncropped tracks:'+str(self.dmd['outings'][a]['utids']))
                    for utid in self.dmd['outings'][a]['utids']:
                        # since newly created features are immediately added to the local cache,
                        #  the boundary feature should be available by this time
                        croppedTrackLines=self.sts2.crop(utid,bid,beyond=0.001) # about 100 meters
                        logging.info('crop return value:'+str(croppedTrackLines))
                        self.dmd['outings'][a]['tids'].append(croppedTrackLines)
                        # cropped track line(s) should correspond to the source map line, 
                        #  not the source map assignment; source map line id will be
                        #  the corr key whose val is the utid; also remove the utid
                        #  from that corr val list
                        # logging.info('    corr items:'+str(corr.items()))
                        slidList=[list(i)[0] for i in self.dmd.items() if list(i)[1]==[utid]]
                        if len(slidList)==1:
                            slid=slidList[0]
                            logging.info('    corresponding source line id:'+str(slid))
                            self.dmd[slid]=[]
                            self.addCorrespondence(slid,croppedTrackLines)
                        else:
                            logging.error('    corresponding source map line id could not be determined')
                            logging.error('    corresponding source line id list:'+str(slidList))
                        # assignments[a]['utids'].remove(utid)
                    self.dmd['outings'][a]['utids']=[] # don't modify the list during iteration over the list!
                    self.writeDmdFile()
                else:
                    logging.info('  Assignment '+a+' has '+str(len(self.dmd['outings'][a]['utids']))+' uncropped tracks, but the boundary has not been imported yet; skipping.')


    # initialNewFeatureCallback: since dmd must be generated before the add<Type> functions
    #  are called (since those functions check to see if the feature already exists on the
    #  target map, to prevent duplicates), the actual new feature actions must not be called
    #  until after dmd is generated (by initDmd).  But, the list of actions to take must be
    #  generated 
    # def initialNewFeatureCallback(self,f):

    # criteria for a 'match': if a feature exists on the target map meeting these criteria,
    #   then it corresponds to the newly read source map feature: don't create a new feature
    #   on the target map; instead, make an entry in corr{} and update the target map feature
    #   if needed; we should be pretty strict here, since any non-matching target map features
    #   can be deleted, and the newly imported feature can be used instead
    #  folder: target title is identical to source title
    #  marker: 
    def newFeatureCallback(self,f):
        self.updateLinkLights(debriefLink=10)
        p=f['properties']
        c=p['class']
        t=p.get('title','')
        sid=f['id']

        logging.info('newFeatureCallback: class='+c+'  title='+t+'  id='+sid)

        # source id might have a corresponding target id; if all corresponding target ids still exist, skip    
        tids=sum(self.sts2.mapData['ids'].values(),[])    
        if sid in self.dmd['corr'].keys():
            logging.info(' source feature exists in correspondence dictionary')
            if all(i in tids for i in self.dmd['corr'][sid]):
                logging.info('  all corresponding features exist in the target map; skipping')
                # crop uncropped tracks even if the assignment already exists in the target;
                #  this will crop any tracks that were imported anew on restart
                if c=='Assignment':
                    self.cropUncroppedTracks()
                self.updateLinkLights()
                return
            else:
                logging.info('  but target map does not contain all of the specified features; adding the feature to the target map')
        else:
            logging.info(' no correspondence entry found; adding the feature to the target map')

        if c=='Assignment':
            a=self.addOuting(f)

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

        if c=='Shape':
            self.addShape(f)
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

        if c=='Marker':
            self.addMarker(f)

        if c=='Clue':
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
    #        the target map is actually thought of as a past-or-present 'pairing' or 'outing', it
    #        makes more sense: once an assignment feature is imported with a 'full' title
    #        (letter and number), don't change it on the target map even when that assignment's
    #        number changes on the source map.  If the number changes to blank on the source map,
    #        make no change on the target map.  If the number changes to another number on the source
    #        map, re-import and create a new pairing (folder and boundary) on the target map. 
    def propertyUpdateCallback(self,f):
        self.updateLinkLights(debriefLink=10)
        sid=f['id']
        sp=f['properties']
        sg=f['geometry']
        sc=sp['class']
        st=sp['title']
        sgt=sg['type']
        logging.info('propertyUpdateCallback called for '+sc+':'+st)
        # determine which target-map feature, if any, corresponds to the edited source-map feature
        if sid in self.dmd.keys(): # this means there's a match but it's not an outing
            corrList=self.dmd[sid]
            if sc=='Shape' and sgt=='LineString':
                for ttid in corrList:
                    self.sts2.delObject('Shape',ttid)
                # also delete from the assignments dict and correspondence dict, so that it will be added anew;
                # we can't be sure here what assignment if any the line was previously a part of,
                #  so scan all assignments for id(s)
                # tparse=parseTrackName(st)
                # if tparse:
                for at in self.dmd['outings']:
                    # at=tparse[0]+' '+tparse[1]
                    # don't modify list while iterating!
                    newTidList=[]
                    for tidList in self.dmd['outings'][at]['tids']:
                        if not all(elem in tidList for elem in corrList):
                            newTidList.append(tidList)
                    self.dmd['outings'][at]['tids']=newTidList
                del self.dmd[sid]
                self.newFeatureCallback(f) # this will crop the track automatically
            elif len(corrList)==1: # exactly one correlating feature exists
                logging.info('  exactly one target map feature corresponds to the source map feature; updating the target map feature properties')
                tf=self.sts2.getFeature(id=corrList[0])
                tp=tf['properties']
                # map properties from source to target, based on source class; start with the existing target
                #  map feature properties, and only copy the appropriate properties from the source feature
                c=sp['class']
                if c=='Clue':
                    logging.info('  mapping properties from Clue to Marker')
                    tp['title']=sp['title']
                    tp['description']=sp['description']
                elif c=='Assignment': # this may be dead code - if assignment, it should have two corr entries
                    tp['title']=sp['title']
                else:
                    tp=sp # for other feature types, copy all properties from source
                self.sts2.editFeature(id=corrList[0],properties=tp)
            else:
                logging.error('  property change: more than one target map feature correspond to the source map feature, which is not a line; no changes made to target map')
        elif sp['class']=='Assignment': # assignment with folder and boundary already created
            olist=[o for o in self.dmd['outings'] if self.dmd['outings'][o]['sid']==sid]
            if len(olist)==0:
                logging.error('  source map assignment feature edited, but it has no corresponding target map feature')
                self.updateLinkLights() # set back to previous colors
                return
            elif len(olist)==1:
                # handle these title change cases:
                #   (use longhand logic - don't try logic reductions - then do a catch-all at the end)
                # 1. blank --> letter only
                #    blank --> letter and number
                #    letter only --> letter and number
                #     --> change title of corresponding target map features (folder and boundary);
                #           change key name for assigments dict entry and fids dict entry
                # 2. letter and number --> same letter, different number
                #     --> do NOT change existing target map assignment; create a new target map
                #          assignment (folder, boundary, assignments dict, fids dict) with new title
                # 3. letter and number --> same letter, no number
                #    all other cases
                #     --> no change to target map or assignments/fids dicts

                # oldf=sts2.getFeature(id=corrList[0])
                # oldTitle=oldf['properties']['title']
                oldTitle=olist[0]
                oldTitleHasNumber=any(char.isdigit() for char in oldTitle)
                newTitleHasNumber=any(char.isdigit() for char in st)
                logging.info('assignment name change: "'+oldTitle+'" --> "'+st+'"')
                logging.info(json.dumps(self.dmd['outings'],indent=3))

                # case 1:
                if (oldTitle=='' or 'NOTITLE' in oldTitle) or (not oldTitleHasNumber and newTitleHasNumber):
                # if newTitleHasNumber: # cases 1 and 2 (case 3 needs to action)
                #     if oldTitleHasNumber: # case 2
                #         newFeatureCallback(f)
                #     else: # case 1
                    logging.info('  existing target map assignment title will be updated...')
                    o=self.dmd['outings'][oldTitle]
                    for tid in [o['bid'],o['fid']]:
                        tf=self.sts2.getFeature(id=tid)
                        tp=tf['properties']
                        tp['title']=sp['title'].upper()
                        self.sts2.editFeature(id=tid,properties=tp)
                    self.dmd['outings'][tp['title']]=self.dmd['outings'][oldTitle]
                    # fids[tp['title']]=fids[oldTitle]
                    del self.dmd['outings'][oldTitle]
                    # del fids[oldTitle]

                # case 2:
                elif (oldTitleHasNumber and newTitleHasNumber):
                    logging.info('  existing target map assignment will not be changed; importing the new assignment from scratch...')
                    self.newFeatureCallback(f)

                # case 3 / all other cases:
                else:
                    logging.info('  no change needed to existing target map assignments')

                # logging.info('new assignments dict:')
                # logging.info(json.dumps(dmd['outings'],indent=3))
                self.writeDmdFile()
            else:
                logging.info('  more than one existing target map outing corresponds to the source map assignment; nothing edited due to ambuguity')
        else:
            logging.info('  source map feature does not have any corresponding feature in target map; nothing edited')
        self.updateLinkLights() # set back to previous colors

    # parseTrackName: return False if not a track, or [assignment,team,suffix] if a track
    def parseTrackName(self,t):
        tparse=re.split('(\d+)',t.upper().replace(' ',''))
        if len(tparse)==3:
            return tparse
        else:
            return False

    def geometryUpdateCallback(self,f):
        self.updateLinkLights(debriefLink=10)
        sid=f['id']
        sp=f['properties']
        st=sp['title']
        sg=f['geometry']
        osids=[self.dmd['outings'][x]['sid'] for x in self.dmd['outings'].keys()] # list of sid of all outings
        logging.info('osids:'+str(osids))
        # if the edited source feature is a track (a linestring with appropriate name format),
        #  delete all corresponding target map features (the crop operation could have resulted in
        #  multiple lines) then re-import the feature from scratch, which will also re-crop it;
        # otherwise, edit the geometry of all corresponding features that have a geometry entry
        #  (i.e. when an assigment boundary is edited, the assignment folder has no geometry)
        # if assignment geometry is edited, consider the following:
        #  - don't edit the geometry for any previous outing boundaries (i.e. if it currently has a
        #     number, and there are additional outing(s) with numbers, edit the current one
        #     but not the previous ones)

        logging.info('geometryUpdateCallback called for '+sp['class']+':'+sp['title'])
        if sid in self.dmd.keys():
            tparse=self.parseTrackName(sp['title'])
            if sg['type']=='LineString' and sp['class']=='Shape' and tparse:
                logging.info('  edited feature '+sp['title']+' appears to be a track; correspoding previous imported and cropped tracks will be deleted, and the new track will be re-imported (and re-cropped)')
                corrList=self.dmd[sid]
                for ttid in self.dmd[sid]:
                    self.sts2.delObject('Shape',ttid)
                # also delete from the assignments dict and correspondence dict, so that it will be added anew
                at=tparse[0]+' '+tparse[1]
                # don't modify list while iterating!
                newTidList=[]
                for tidList in self.dmd['outings'][at]['tids']:
                    if not all(elem in tidList for elem in corrList):
                        newTidList.append(tidList)
                self.dmd['outings'][at]['tids']=newTidList
                del self.dmd[sid]
                self.newFeatureCallback(f) # this will crop the track automatically
            else:
                for tid in self.dmd[sid]:
                    if 'geometry' in self.sts2.getFeature(id=tid).keys():
                        logging.info('  corresponding target map feature '+tid+' has geometry; setting it equal to the edited source feature geometry')
                        self.sts2.editFeature(id=tid,geometry=sg)
                    else:
                        logging.info('  corresponding target map feature '+tid+' has no geometry; no edit performed')
        elif sid in osids:
            for ot in self.dmd['outings'].keys():
                o=self.dmd['outings'][ot]
                if o['sid']==sid and ot==st: # the title is current
                    logging.info('  assignment geometry was edited: applying the same edit to corresponding target map boundary that has the same title "'+st+'" as the edited feature (to preserve previous outing boundaries)')
                    self.sts2.editFeature(id=o['bid'],geometry=sg)
        # # 1. determine which target-map feature, if any, corresponds to the edited source-map feature
        # if sid in corr.keys():
        #     cval=corr[sid]
        #     logging.info('cval:'+str(cval))
        #     if len(cval)==1: # exactly one corresponding feature exists
        #         logging.info('exactly one target map feature corresponds to the source map feature; updating the target map feature geometry')
        #         sts2.editFeature(id=cval[0],geometry=sg)
        #         # if it was a track, delete all corresponding target map features, then re-import (which will re-crop it)
        #         if sg['type']=='LineString':
        #             for a in assignments:
        #                 logging.info('  checking assignment: tids='+str(assignments[a]['tids']))
        #                 if cval[0] in assignments[a]['tids']:
        #                     logging.info('  the updated geometry is a track belonging to '+assignments[a]['title']+': will re-crop using the new geometry')
        #                     sts2.crop(cval[0],assignments[a]['bid'],beyond=0.001)
        #     else:
        #         logging.info('more than one existing target map feature corresponds to the source map feature; nothing edited due to ambuguity')
        else:
            logging.info('source map feature does not have any corresponding feature in target map; nothing edited')
        self.updateLinkLights() # set back to previous colors

    def deletedFeatureCallback(self,f):
        self.updateLinkLights(debriefLink=10)
        sid=f['id']
        logging.info('deletedFeatureCallback called for feature '+str(sid)+' :')
        logging.info(json.dumps(f,indent=3))
        # 1. determine which target-map feature, if any, corresponds to the edited source-map feature
        # logging.info('corr keys:')
        # logging.info(str(dmd['corr'].keys()))
        logging.info('dmd:\n'+str(json.dumps(self.dmd,indent=3)))
        if sid in self.dmd['corr'].keys():
            cval=self.dmd['corr'][sid]
            for tid in cval:
                logging.info('deleting corresponding target map feature '+tid)
                self.sts2.delObject(f['properties']['class'],existingId=tid)
            del self.dmd['corr'][sid] # not currently iterating, so, del should be fine
            self.writeDmdFile()
        else:
            logging.info('source map feature does not have any corresponding feature in target map; nothing deleted')
        self.updateLinkLights() # set back to previous colors



    # initial sync is different than callback handling because:
    #    ...
    #
    # on the initial sync, pay attention to the sequence:
    # 1. read assignments from source map: create folders and boundary shapes in target map
    # 2. read shapes from source map: for completed search tracks (based on name),
    #      draw the line in the target map assignment folder
    # 3. perform a fresh since request on target map, so that newly
    #      drawn lines will appear in .mapData as needed by crop()
    # 4. in target map, color the tracks in alphabetical order
    # 5. in target map, crop tracks to assigment boundaries

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

    # # 3. do a new since request in the target map
    # sts2.doSync(once=True)

    # 4. color the tracks in alphabetical order



    # initial processing complete; now register the callback
    # sts1.newFeatureCallback=newFeatureCallback



class DebriefMapDialog(QDialog,Ui_DebriefMapDialog):
    def __init__(self,parent):
        QDialog.__init__(self)
        self.parent=parent
        self.ui=Ui_DebriefMapDialog()
        self.ui.setupUi(self)
        self.ui.domainAndPortButtonGroup.buttonClicked.connect(self.domainAndPortClicked)
        self.urlChanged()
        self.ui.mapIDField.setFocus()

    def domainAndPortClicked(self,*args,**kwargs):
        val=self.ui.domainAndPortButtonGroup.checkedButton().text()
        self.ui.domainAndPortOtherField.setEnabled(val=='Other')
        self.urlChanged()

    def urlChanged(self):
        dap=self.ui.domainAndPortButtonGroup.checkedButton().text()
        if dap=='Other':
            dap=self.ui.domainAndPortOtherField.text()
        prefix='http://'
        if '.com' in dap:
            prefix='https://'
        mapID=self.ui.mapIDField.text()
        url=prefix+dap+'/m/'+mapID
        self.ui.urlField.setText(url)
    
    def accept(self):
        self.parent.targetDomainAndPort=self.ui.domainAndPortButtonGroup.checkedButton().text()
        self.parent.targetMapID=self.ui.mapIDField.text()
        self.parent.debriefURL=self.ui.urlField.text()
        self.parent.dd.ui.debriefMapField.setText(self.ui.urlField.text())
        if self.parent.pc:
            self.parent.parent.ui.debriefMapField.setText(self.ui.urlField.text())
        super(DebriefMapDialog,self).accept()


class DebriefDialog(QDialog,Ui_DebriefDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui=Ui_DebriefDialog()
        self.ui.setupUi(self)
        
        self.ui.tableWidget.setColumnWidth(0,125)
        self.ui.tableWidget.setColumnWidth(1,75)
        self.ui.tableWidget.setColumnWidth(2,75)
        self.ui.tableWidget.horizontalHeader().setSectionResizeMode(3,1)
        self.ui.tableWidget.setColumnWidth(4,50)
        self.ui.tableWidget.setColumnWidth(5,50)

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