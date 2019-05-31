# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'split_dialog.ui'
#
# Created: Thu May 30 13:35:08 2019
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(476, 205)
        self.label_FileEndDate = QtGui.QLabel(Dialog)
        self.label_FileEndDate.setGeometry(QtCore.QRect(310, 3, 81, 17))
        self.label_FileEndDate.setObjectName(_fromUtf8("label_FileEndDate"))
        self.label_StartDate = QtGui.QLabel(Dialog)
        self.label_StartDate.setGeometry(QtCore.QRect(10, 130, 58, 17))
        self.label_StartDate.setObjectName(_fromUtf8("label_StartDate"))
        self.label_FileStartDate = QtGui.QLabel(Dialog)
        self.label_FileStartDate.setGeometry(QtCore.QRect(110, 4, 91, 17))
        self.label_FileStartDate.setObjectName(_fromUtf8("label_FileStartDate"))
        self.label_InputFileName = QtGui.QLabel(Dialog)
        self.label_InputFileName.setGeometry(QtCore.QRect(10, 50, 101, 17))
        self.label_InputFileName.setObjectName(_fromUtf8("label_InputFileName"))
        self.label_OutputFileName = QtGui.QLabel(Dialog)
        self.label_OutputFileName.setGeometry(QtCore.QRect(10, 90, 111, 17))
        self.label_OutputFileName.setObjectName(_fromUtf8("label_OutputFileName"))
        self.label_FileStartDate_value = QtGui.QLabel(Dialog)
        self.label_FileStartDate_value.setGeometry(QtCore.QRect(90, 23, 131, 17))
        self.label_FileStartDate_value.setObjectName(_fromUtf8("label_FileStartDate_value"))
        self.lineEdit_EndDate = QtGui.QLineEdit(Dialog)
        self.lineEdit_EndDate.setGeometry(QtCore.QRect(310, 130, 151, 25))
        self.lineEdit_EndDate.setObjectName(_fromUtf8("lineEdit_EndDate"))
        self.lineEdit_InputFileName = QtGui.QLineEdit(Dialog)
        self.lineEdit_InputFileName.setGeometry(QtCore.QRect(130, 50, 241, 25))
        self.lineEdit_InputFileName.setObjectName(_fromUtf8("lineEdit_InputFileName"))
        self.pushButton_Run = QtGui.QPushButton(Dialog)
        self.pushButton_Run.setGeometry(QtCore.QRect(100, 170, 87, 27))
        self.pushButton_Run.setObjectName(_fromUtf8("pushButton_Run"))
        self.pushButton_Quit = QtGui.QPushButton(Dialog)
        self.pushButton_Quit.setGeometry(QtCore.QRect(270, 170, 87, 27))
        self.pushButton_Quit.setObjectName(_fromUtf8("pushButton_Quit"))
        self.label_FileEndDate_value = QtGui.QLabel(Dialog)
        self.label_FileEndDate_value.setGeometry(QtCore.QRect(277, 22, 131, 20))
        self.label_FileEndDate_value.setObjectName(_fromUtf8("label_FileEndDate_value"))
        self.pushButton_OutputFileName = QtGui.QPushButton(Dialog)
        self.pushButton_OutputFileName.setGeometry(QtCore.QRect(380, 90, 87, 27))
        self.pushButton_OutputFileName.setObjectName(_fromUtf8("pushButton_OutputFileName"))
        self.label_EndDate = QtGui.QLabel(Dialog)
        self.label_EndDate.setGeometry(QtCore.QRect(240, 132, 58, 17))
        self.label_EndDate.setObjectName(_fromUtf8("label_EndDate"))
        self.lineEdit_StartDate = QtGui.QLineEdit(Dialog)
        self.lineEdit_StartDate.setGeometry(QtCore.QRect(80, 130, 141, 25))
        self.lineEdit_StartDate.setObjectName(_fromUtf8("lineEdit_StartDate"))
        self.lineEdit_OutputFileName = QtGui.QLineEdit(Dialog)
        self.lineEdit_OutputFileName.setGeometry(QtCore.QRect(130, 90, 241, 25))
        self.lineEdit_OutputFileName.setObjectName(_fromUtf8("lineEdit_OutputFileName"))
        self.pushButton_InputFileName = QtGui.QPushButton(Dialog)
        self.pushButton_InputFileName.setGeometry(QtCore.QRect(380, 50, 87, 27))
        self.pushButton_InputFileName.setObjectName(_fromUtf8("pushButton_InputFileName"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Dialog", None))
        self.label_FileEndDate.setText(_translate("Dialog", "File end date", None))
        self.label_StartDate.setText(_translate("Dialog", "Start date", None))
        self.label_FileStartDate.setText(_translate("Dialog", "File start date", None))
        self.label_InputFileName.setText(_translate("Dialog", "Input file name", None))
        self.label_OutputFileName.setText(_translate("Dialog", "Output file name", None))
        self.label_FileStartDate_value.setText(_translate("Dialog", "YYYY-MM-DD HH:MM", None))
        self.lineEdit_EndDate.setText(_translate("Dialog", "YYYY-MM-DD HH:MM", None))
        self.pushButton_Run.setText(_translate("Dialog", "Run", None))
        self.pushButton_Quit.setText(_translate("Dialog", "Quit", None))
        self.label_FileEndDate_value.setText(_translate("Dialog", "YYYY-MM-DD HH:MM", None))
        self.pushButton_OutputFileName.setText(_translate("Dialog", "Browse", None))
        self.label_EndDate.setText(_translate("Dialog", "End date", None))
        self.lineEdit_StartDate.setText(_translate("Dialog", "YYYY-MM-DD HH:MM", None))
        self.pushButton_InputFileName.setText(_translate("Dialog", "Browse", None))


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    Dialog = QtGui.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())

