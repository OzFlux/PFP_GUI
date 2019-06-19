# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'split_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(476, 205)
        self.label_FileEndDate = QtWidgets.QLabel(Dialog)
        self.label_FileEndDate.setGeometry(QtCore.QRect(310, 3, 81, 17))
        self.label_FileEndDate.setObjectName("label_FileEndDate")
        self.label_StartDate = QtWidgets.QLabel(Dialog)
        self.label_StartDate.setGeometry(QtCore.QRect(10, 130, 58, 17))
        self.label_StartDate.setObjectName("label_StartDate")
        self.label_FileStartDate = QtWidgets.QLabel(Dialog)
        self.label_FileStartDate.setGeometry(QtCore.QRect(110, 4, 91, 17))
        self.label_FileStartDate.setObjectName("label_FileStartDate")
        self.label_InputFileName = QtWidgets.QLabel(Dialog)
        self.label_InputFileName.setGeometry(QtCore.QRect(10, 50, 101, 17))
        self.label_InputFileName.setObjectName("label_InputFileName")
        self.label_OutputFileName = QtWidgets.QLabel(Dialog)
        self.label_OutputFileName.setGeometry(QtCore.QRect(10, 90, 111, 17))
        self.label_OutputFileName.setObjectName("label_OutputFileName")
        self.label_FileStartDate_value = QtWidgets.QLabel(Dialog)
        self.label_FileStartDate_value.setGeometry(QtCore.QRect(90, 23, 131, 17))
        self.label_FileStartDate_value.setObjectName("label_FileStartDate_value")
        self.lineEdit_EndDate = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_EndDate.setGeometry(QtCore.QRect(310, 130, 151, 25))
        self.lineEdit_EndDate.setObjectName("lineEdit_EndDate")
        self.lineEdit_InputFileName = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_InputFileName.setGeometry(QtCore.QRect(130, 50, 241, 25))
        self.lineEdit_InputFileName.setObjectName("lineEdit_InputFileName")
        self.pushButton_Run = QtWidgets.QPushButton(Dialog)
        self.pushButton_Run.setGeometry(QtCore.QRect(100, 170, 87, 27))
        self.pushButton_Run.setObjectName("pushButton_Run")
        self.pushButton_Quit = QtWidgets.QPushButton(Dialog)
        self.pushButton_Quit.setGeometry(QtCore.QRect(270, 170, 87, 27))
        self.pushButton_Quit.setObjectName("pushButton_Quit")
        self.label_FileEndDate_value = QtWidgets.QLabel(Dialog)
        self.label_FileEndDate_value.setGeometry(QtCore.QRect(277, 22, 131, 20))
        self.label_FileEndDate_value.setObjectName("label_FileEndDate_value")
        self.pushButton_OutputFileName = QtWidgets.QPushButton(Dialog)
        self.pushButton_OutputFileName.setGeometry(QtCore.QRect(380, 90, 87, 27))
        self.pushButton_OutputFileName.setObjectName("pushButton_OutputFileName")
        self.label_EndDate = QtWidgets.QLabel(Dialog)
        self.label_EndDate.setGeometry(QtCore.QRect(240, 132, 58, 17))
        self.label_EndDate.setObjectName("label_EndDate")
        self.lineEdit_StartDate = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_StartDate.setGeometry(QtCore.QRect(80, 130, 141, 25))
        self.lineEdit_StartDate.setObjectName("lineEdit_StartDate")
        self.lineEdit_OutputFileName = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_OutputFileName.setGeometry(QtCore.QRect(130, 90, 241, 25))
        self.lineEdit_OutputFileName.setObjectName("lineEdit_OutputFileName")
        self.pushButton_InputFileName = QtWidgets.QPushButton(Dialog)
        self.pushButton_InputFileName.setGeometry(QtCore.QRect(380, 50, 87, 27))
        self.pushButton_InputFileName.setObjectName("pushButton_InputFileName")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label_FileEndDate.setText(_translate("Dialog", "File end date"))
        self.label_StartDate.setText(_translate("Dialog", "Start date"))
        self.label_FileStartDate.setText(_translate("Dialog", "File start date"))
        self.label_InputFileName.setText(_translate("Dialog", "Input file name"))
        self.label_OutputFileName.setText(_translate("Dialog", "Output file name"))
        self.label_FileStartDate_value.setText(_translate("Dialog", "YYYY-MM-DD HH:MM"))
        self.lineEdit_EndDate.setText(_translate("Dialog", "YYYY-MM-DD HH:MM"))
        self.pushButton_Run.setText(_translate("Dialog", "Run"))
        self.pushButton_Quit.setText(_translate("Dialog", "Quit"))
        self.label_FileEndDate_value.setText(_translate("Dialog", "YYYY-MM-DD HH:MM"))
        self.pushButton_OutputFileName.setText(_translate("Dialog", "Browse"))
        self.label_EndDate.setText(_translate("Dialog", "End date"))
        self.lineEdit_StartDate.setText(_translate("Dialog", "YYYY-MM-DD HH:MM"))
        self.pushButton_InputFileName.setText(_translate("Dialog", "Browse"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
