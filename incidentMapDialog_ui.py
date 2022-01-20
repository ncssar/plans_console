# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\caver\Documents\GitHub\plans_console\incidentMapDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_IncidentMapDialog(object):
    def setupUi(self, IncidentMapDialog):
        IncidentMapDialog.setObjectName("IncidentMapDialog")
        IncidentMapDialog.resize(420, 293)
        self.buttonBox = QtWidgets.QDialogButtonBox(IncidentMapDialog)
        self.buttonBox.setGeometry(QtCore.QRect(10, 250, 401, 32))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.buttonBox.setFont(font)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.label = QtWidgets.QLabel(IncidentMapDialog)
        self.label.setGeometry(QtCore.QRect(20, 10, 381, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(IncidentMapDialog)
        self.label_2.setGeometry(QtCore.QRect(10, 210, 141, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.urlField = QtWidgets.QLineEdit(IncidentMapDialog)
        self.urlField.setEnabled(False)
        self.urlField.setGeometry(QtCore.QRect(160, 210, 251, 22))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.urlField.setFont(font)
        self.urlField.setObjectName("urlField")
        self.mapIDField = QtWidgets.QLineEdit(IncidentMapDialog)
        self.mapIDField.setGeometry(QtCore.QRect(270, 100, 111, 31))
        font = QtGui.QFont()
        font.setFamily("Liberation Mono")
        font.setPointSize(18)
        font.setBold(False)
        font.setWeight(50)
        self.mapIDField.setFont(font)
        self.mapIDField.setText("")
        self.mapIDField.setObjectName("mapIDField")
        self.label_3 = QtWidgets.QLabel(IncidentMapDialog)
        self.label_3.setGeometry(QtCore.QRect(270, 70, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.groupBox = QtWidgets.QGroupBox(IncidentMapDialog)
        self.groupBox.setGeometry(QtCore.QRect(20, 50, 221, 141))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.groupBox.setFont(font)
        self.groupBox.setObjectName("groupBox")
        self.domainAndPortOtherField = QtWidgets.QLineEdit(self.groupBox)
        self.domainAndPortOtherField.setEnabled(False)
        self.domainAndPortOtherField.setGeometry(QtCore.QRect(40, 110, 171, 21))
        self.domainAndPortOtherField.setObjectName("domainAndPortOtherField")
        self.radioButton_2 = QtWidgets.QRadioButton(self.groupBox)
        self.radioButton_2.setGeometry(QtCore.QRect(20, 50, 141, 20))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.radioButton_2.setFont(font)
        self.radioButton_2.setObjectName("radioButton_2")
        self.domainAndPortButtonGroup = QtWidgets.QButtonGroup(IncidentMapDialog)
        self.domainAndPortButtonGroup.setObjectName("domainAndPortButtonGroup")
        self.domainAndPortButtonGroup.addButton(self.radioButton_2)
        self.radioButton = QtWidgets.QRadioButton(self.groupBox)
        self.radioButton.setGeometry(QtCore.QRect(20, 20, 141, 20))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.radioButton.setFont(font)
        self.radioButton.setChecked(True)
        self.radioButton.setObjectName("radioButton")
        self.domainAndPortButtonGroup.addButton(self.radioButton)
        self.otherButton = QtWidgets.QRadioButton(self.groupBox)
        self.otherButton.setGeometry(QtCore.QRect(20, 80, 141, 20))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.otherButton.setFont(font)
        self.otherButton.setObjectName("otherButton")
        self.domainAndPortButtonGroup.addButton(self.otherButton)
        self.label_4 = QtWidgets.QLabel(IncidentMapDialog)
        self.label_4.setGeometry(QtCore.QRect(270, 130, 131, 16))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label_4.setFont(font)
        self.label_4.setObjectName("label_4")

        self.retranslateUi(IncidentMapDialog)
        self.buttonBox.accepted.connect(IncidentMapDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(IncidentMapDialog.reject) # type: ignore
        self.mapIDField.textChanged['QString'].connect(IncidentMapDialog.urlChanged) # type: ignore
        self.domainAndPortOtherField.textChanged['QString'].connect(IncidentMapDialog.urlChanged) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(IncidentMapDialog)

    def retranslateUi(self, IncidentMapDialog):
        _translate = QtCore.QCoreApplication.translate
        IncidentMapDialog.setWindowTitle(_translate("IncidentMapDialog", "Incident Map"))
        self.label.setText(_translate("IncidentMapDialog", "Specify the Incident Map."))
        self.label_2.setText(_translate("IncidentMapDialog", "Incident Map URL:"))
        self.mapIDField.setPlaceholderText(_translate("IncidentMapDialog", "A1B2C"))
        self.label_3.setText(_translate("IncidentMapDialog", "Incident Map ID"))
        self.groupBox.setTitle(_translate("IncidentMapDialog", "Domain and Port"))
        self.domainAndPortOtherField.setPlaceholderText(_translate("IncidentMapDialog", "myServer:8080"))
        self.radioButton_2.setText(_translate("IncidentMapDialog", "sartopo.com"))
        self.radioButton.setText(_translate("IncidentMapDialog", "localhost:8080"))
        self.otherButton.setText(_translate("IncidentMapDialog", "Other"))
        self.label_4.setText(_translate("IncidentMapDialog", "3-5 characters"))
