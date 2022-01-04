# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\caver\Documents\GitHub\plans_console\debrief.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DebriefDialog(object):
    def setupUi(self, DebriefDialog):
        DebriefDialog.setObjectName("DebriefDialog")
        DebriefDialog.resize(653, 297)
        self.horizontalLayout = QtWidgets.QHBoxLayout(DebriefDialog)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.incidentMapLabel = QtWidgets.QLabel(DebriefDialog)
        self.incidentMapLabel.setObjectName("incidentMapLabel")
        self.gridLayout.addWidget(self.incidentMapLabel, 0, 0, 1, 1)
        self.incidentMapField = QtWidgets.QLineEdit(DebriefDialog)
        self.incidentMapField.setEnabled(False)
        self.incidentMapField.setObjectName("incidentMapField")
        self.gridLayout.addWidget(self.incidentMapField, 0, 1, 1, 1)
        self.incidentLinkLight = QtWidgets.QLineEdit(DebriefDialog)
        self.incidentLinkLight.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.incidentLinkLight.sizePolicy().hasHeightForWidth())
        self.incidentLinkLight.setSizePolicy(sizePolicy)
        self.incidentLinkLight.setMaximumSize(QtCore.QSize(20, 16777215))
        self.incidentLinkLight.setObjectName("incidentLinkLight")
        self.gridLayout.addWidget(self.incidentLinkLight, 0, 2, 1, 1)
        self.debriefMapLabel = QtWidgets.QLabel(DebriefDialog)
        self.debriefMapLabel.setObjectName("debriefMapLabel")
        self.gridLayout.addWidget(self.debriefMapLabel, 1, 0, 1, 1)
        self.debriefMapField = QtWidgets.QLineEdit(DebriefDialog)
        self.debriefMapField.setEnabled(False)
        self.debriefMapField.setObjectName("debriefMapField")
        self.gridLayout.addWidget(self.debriefMapField, 1, 1, 1, 1)
        self.debriefLinkLight = QtWidgets.QLineEdit(DebriefDialog)
        self.debriefLinkLight.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.debriefLinkLight.sizePolicy().hasHeightForWidth())
        self.debriefLinkLight.setSizePolicy(sizePolicy)
        self.debriefLinkLight.setMaximumSize(QtCore.QSize(20, 16777215))
        self.debriefLinkLight.setObjectName("debriefLinkLight")
        self.gridLayout.addWidget(self.debriefLinkLight, 1, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.tableWidget = QtWidgets.QTableWidget(DebriefDialog)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(5, item)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setHighlightSections(False)
        self.verticalLayout.addWidget(self.tableWidget)
        self.horizontalLayout.addLayout(self.verticalLayout)

        self.retranslateUi(DebriefDialog)
        QtCore.QMetaObject.connectSlotsByName(DebriefDialog)

    def retranslateUi(self, DebriefDialog):
        _translate = QtCore.QCoreApplication.translate
        DebriefDialog.setWindowTitle(_translate("DebriefDialog", "Dialog"))
        self.incidentMapLabel.setText(_translate("DebriefDialog", "Incident Map"))
        self.incidentMapField.setPlaceholderText(_translate("DebriefDialog", "http(s)://incidentMapURL"))
        self.debriefMapLabel.setText(_translate("DebriefDialog", "Debrief Map"))
        self.debriefMapField.setPlaceholderText(_translate("DebriefDialog", "http(s)://debriefMapURL"))
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText(_translate("DebriefDialog", "Outing"))
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText(_translate("DebriefDialog", "Tracks"))
        item = self.tableWidget.horizontalHeaderItem(2)
        item.setText(_translate("DebriefDialog", "Clues"))
        item = self.tableWidget.horizontalHeaderItem(3)
        item.setText(_translate("DebriefDialog", "Latest"))
        item = self.tableWidget.horizontalHeaderItem(4)
        item.setText(_translate("DebriefDialog", "Print"))
        item = self.tableWidget.horizontalHeaderItem(5)
        item.setText(_translate("DebriefDialog", "Rebuild"))
