# -*- coding: utf-8 -*-
# Form implementation generated from reading ui file 'plans_console.ui'
#
# Created by: PyQt5 UI code generator 5.12
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QRadioButton, QApplication
import winsound

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 1200)          # does not do anything 
        self.sts = None   ##  used to get sts reference from main routine
        ###self.sclr = MainWindow.scl             # gets scl from MainWindow
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.tableWidget = QtWidgets.QTableWidget(self.centralwidget)
        self.tableWidget.setGeometry(QtCore.QRect(10, 40, 1115, 900))
        self.tableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setObjectName("tableWidget")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        self.tableWidget.setColumnWidth(0, 100)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        self.tableWidget.setColumnWidth(1, 100)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        self.tableWidget.setColumnWidth(2, 700)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(3, item)
        self.tableWidget.setColumnWidth(3, 150)
        item = QtWidgets.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        self.tableWidget.setItem(0, 0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setItem(0, 2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setItem(2, 2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setItem(6, 2, item)
        self.tableWidget.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget.horizontalHeader().setStretchLastSection(False)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setCascadingSectionResizes(False)
        self.tableWidget.verticalHeader().setDefaultSectionSize(20)


        self.groupBox = QtWidgets.QGroupBox(MainWindow)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setGeometry(QtCore.QRect(1300, 725, 200, 70))
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox)
 

        self.clock = QtWidgets.QLCDNumber(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.clock.sizePolicy().hasHeightForWidth())
        self.clock.setSizePolicy(sizePolicy)
        self.clock.setMinimumSize(QtCore.QSize(115, 36))
        self.clock.setMaximumSize(QtCore.QSize(16777215, 36))
        self.clock.setObjectName("clock")
        self.horizontalLayout_2.addWidget(self.clock)

        self.rescanButton = QtWidgets.QPushButton(self.groupBox)
        #sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        #sizePolicy.setHorizontalStretch(0)
        #sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rescanButton.sizePolicy().hasHeightForWidth())
        self.rescanButton.setSizePolicy(sizePolicy)
        self.rescanButton.setMaximumSize(QtCore.QSize(36, 36))
        self.rescanButton.setBaseSize(QtCore.QSize(36, 36))
        self.rescanButton.setText("")

        icon1 = QtGui.QIcon()  # set picture on reset button
        icon1.addPixmap(QtGui.QPixmap("./reload-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.rescanButton.setIcon(icon1)
        self.rescanButton.setIconSize(QtCore.QSize(30, 30))
        self.rescanButton.setObjectName("rescanButton")
        self.horizontalLayout_2.addWidget(self.rescanButton)        


        self.groupBox2 = QtWidgets.QGroupBox(MainWindow)
        self.groupBox2.setTitle("")
        self.groupBox2.setObjectName("groupBox")
        self.groupBox2.setGeometry(QtCore.QRect(1200, 800, 375, 70))
        self.groupBox2.setStyleSheet("QGroupBox { border: 2px solid blue;}")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.groupBox2)

        self.cutExpCrp = QtWidgets.QRadioButton("Cut")
        self.cutExpCrp.type = "Cut"
        self.cutExpCrp.setChecked(True)
        self.result = "Cut"   # initial value
        self.cutExpCrp.toggled.connect(self.onClicked)
        self.horizontalLayout_3.addWidget(self.cutExpCrp)
        sizePolicy.setHeightForWidth(self.cutExpCrp.sizePolicy().hasHeightForWidth())
        self.cutExpCrp.setSizePolicy(sizePolicy)
        self.cutExpCrp.setMinimumSize(QtCore.QSize(115, 36))
        self.cutExpCrp.setMaximumSize(QtCore.QSize(16777215, 36))
        self.cutExpCrp.setObjectName("cut")
        self.cutExpCrp = QtWidgets.QRadioButton("Expand")
        self.cutExpCrp.type = "Expand"
        self.cutExpCrp.toggled.connect(self.onClicked2)
        self.horizontalLayout_3.addWidget(self.cutExpCrp)
        self.cutExpCrp = QtWidgets.QRadioButton("Crop")
        self.cutExpCrp.type = "Crop"
        self.cutExpCrp.toggled.connect(self.onClicked4)
        self.horizontalLayout_3.addWidget(self.cutExpCrp)
        
        self.groupBox3 = QtWidgets.QGroupBox(MainWindow)
        self.groupBox3.setTitle("")
        self.groupBox3.setObjectName("groupBox")
        self.groupBox3.setGeometry(QtCore.QRect(1200, 870, 375, 70))
        self.groupBox3.setStyleSheet("QGroupBox { border: 2px solid blue;}")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.groupBox3)

        self.selObj = QtWidgets.QLineEdit("selObj")
        self.editObj = QtWidgets.QLineEdit("editor")
        self.horizontalLayout_4.addWidget(self.selObj)
        self.horizontalLayout_4.addWidget(self.editObj)
 
        self.doOper = QtWidgets.QPushButton("Go")
        self.doOper.clicked.connect(self.onClicked3)
        self.horizontalLayout_4.addWidget(self.doOper)

        self.tableWidget_TmAs = QtWidgets.QTableWidget(self.centralwidget)
        self.tableWidget_TmAs.setGeometry(QtCore.QRect(1200, 40, 380, 600))
        self.tableWidget_TmAs.setRowCount(0)
        self.tableWidget_TmAs.setColumnCount(4)
        self.tableWidget_TmAs.setObjectName("tableWidget_TmAs")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_TmAs.setHorizontalHeaderItem(0, item)
        self.tableWidget_TmAs.setColumnWidth(0, 50)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_TmAs.setHorizontalHeaderItem(1, item)
        self.tableWidget_TmAs.setColumnWidth(1, 100)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_TmAs.setHorizontalHeaderItem(2, item)
        self.tableWidget_TmAs.setColumnWidth(2, 75)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_TmAs.setHorizontalHeaderItem(3, item)
        self.tableWidget_TmAs.setColumnWidth(3, 60)
        self.tableWidget_TmAs.horizontalHeader().setHighlightSections(False)
        self.tableWidget_TmAs.verticalHeader().setVisible(False)
        self.tableWidget_TmAs.verticalHeader().setDefaultSectionSize(20)
        self.OKbut = QtWidgets.QPushButton(self.centralwidget)
        self.OKbut.setGeometry(QtCore.QRect(1550, 700, 30, 30))
        self.OKbut.setObjectName("OKbut")
        self.Assign = QtWidgets.QLineEdit(self.centralwidget)
        self.Assign.setGeometry(QtCore.QRect(1300,700, 50, 20))
        self.Assign.setObjectName("Assign")
        self.Team = QtWidgets.QLineEdit(self.centralwidget)
        self.Team.setGeometry(QtCore.QRect(1200, 700, 50, 20))
        self.Team.setObjectName("Team")
        self.Med = QtWidgets.QCheckBox(self.centralwidget)
        self.Med.setGeometry(QtCore.QRect(1500, 700, 20, 20))
        self.Med.setObjectName("Med")
        self.comboBox = QtWidgets.QComboBox(self.centralwidget)
        self.comboBox.setGeometry(QtCore.QRect(1380, 700, 100, 30))
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(1200, 670, 50, 30))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(1300, 670, 60, 30))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(1400, 670, 50, 30))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(1500, 670, 40, 30))
        self.label_4.setObjectName("label_4")


        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def onClicked(self):
        self.result = "Cut"

    def onClicked2(self):
        self.result = "Expand"

    def onClicked4(self):
        self.result = "Crop"
    
    def onClicked3(self):
        print("%s shape %s with object %s"%(self.result,self.selObj.text(),self.editObj.text()))
        ## check that the shapes exist; otherwise BEEP
        if self.result == "Cut":
            if not self.sts.cut(self.selObj.text(), self.editObj.text()):
               self.BEEP()
               return
        elif self.result == "Expand":
            if not self.sts.expand(self.selObj.text(), self.editObj.text()):
               self.BEEP()
               return
        else:    
            if not self.sts.crop(self.selObj.text(), self.editObj.text()):
               self.BEEP()
               return

    def BEEP(self):
        winsound.Beep(2500, 1200)  ## BEEP, 2500Hz for 1 second 

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Plans_console Display"))
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Time"))
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Team"))
        item = self.tableWidget.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Description"))
        item = self.tableWidget.horizontalHeaderItem(3)
        item.setText(_translate("MainWindow", "Status"))
        __sortingEnabled = self.tableWidget.isSortingEnabled()
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setSortingEnabled(__sortingEnabled)
        item = self.tableWidget_TmAs.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Team"))
        item = self.tableWidget_TmAs.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Assign"))
        item = self.tableWidget_TmAs.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Type"))
        item = self.tableWidget_TmAs.horizontalHeaderItem(3)
        item.setText(_translate("MainWindow", "Med"))
        self.OKbut.setText(_translate("MainWindow", "Ok"))
        self.comboBox.setItemText(0, _translate("MainWindow", "Select"))
        self.comboBox.setItemText(1, _translate("MainWindow", "K9A"))
        self.comboBox.setItemText(2, _translate("MainWindow", "Gnd"))
        self.comboBox.setItemText(3, _translate("MainWindow", "UTV"))
        self.comboBox.setItemText(4, _translate("MainWindow", "K9T"))
        self.comboBox.setItemText(5, _translate("MainWindow", "LE"))
        self.label.setText(_translate("MainWindow", "Team#"))
        self.label_2.setText(_translate("MainWindow", "Assignment"))
        self.label_3.setText(_translate("MainWindow", "Type"))
        self.label_4.setText(_translate("MainWindow", "Med"))


