# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\caver\Documents\GitHub\plans_console\debriefOptionsDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DebriefOptionsDialog(object):
    def setupUi(self, DebriefOptionsDialog):
        DebriefOptionsDialog.setObjectName("DebriefOptionsDialog")
        DebriefOptionsDialog.resize(333, 156)
        self.layoutWidget = QtWidgets.QWidget(DebriefOptionsDialog)
        self.layoutWidget.setGeometry(QtCore.QRect(20, 10, 296, 138))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.layoutWidget)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.comboBox = QtWidgets.QComboBox(self.layoutWidget)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.horizontalLayout.addWidget(self.comboBox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.checkBox = QtWidgets.QCheckBox(self.layoutWidget)
        self.checkBox.setChecked(True)
        self.checkBox.setObjectName("checkBox")
        self.verticalLayout.addWidget(self.checkBox)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.rebuildAllButton = QtWidgets.QPushButton(self.layoutWidget)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/plans_console/reload-icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.rebuildAllButton.setIcon(icon)
        self.rebuildAllButton.setObjectName("rebuildAllButton")
        self.verticalLayout.addWidget(self.rebuildAllButton)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.buttonBox = QtWidgets.QDialogButtonBox(self.layoutWidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(DebriefOptionsDialog)
        self.buttonBox.accepted.connect(DebriefOptionsDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(DebriefOptionsDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(DebriefOptionsDialog)

    def retranslateUi(self, DebriefOptionsDialog):
        _translate = QtCore.QCoreApplication.translate
        DebriefOptionsDialog.setWindowTitle(_translate("DebriefOptionsDialog", "Debrief Options"))
        self.label.setText(_translate("DebriefOptionsDialog", "Basemap Layer"))
        self.comboBox.setItemText(0, _translate("DebriefOptionsDialog", "Scanned Topo (USGS 7.5\')"))
        self.comboBox.setItemText(1, _translate("DebriefOptionsDialog", "Forest Service (FSTopo 2016 - Green)"))
        self.comboBox.setItemText(2, _translate("DebriefOptionsDialog", "MapBuilder Topo"))
        self.comboBox.setItemText(3, _translate("DebriefOptionsDialog", "MapBuilder Hybrid"))
        self.comboBox.setItemText(4, _translate("DebriefOptionsDialog", "Imagery"))
        self.checkBox.setText(_translate("DebriefOptionsDialog", "Show UTM Grid (at auto-interval)"))
        self.rebuildAllButton.setText(_translate("DebriefOptionsDialog", "Rebuild Entire Debrief Map"))
import plans_console2_rc
