# standard modules
import copy
# 3rd party modules
from PyQt4 import QtCore, QtGui

class edit_cfg_L1L2L3(QtGui.QWidget):
    def __init__(self, cfg):

        super(edit_cfg_L1L2L3, self).__init__()

        self.cfg_mod = copy.deepcopy(cfg)
        # Layout
        self.tree = QtGui.QTreeView()
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setModel(QtGui.QStandardItemModel())
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)

        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])

        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                parent = QtGui.QStandardItem(key1)
                parent.setFlags(QtCore.Qt.NoItemFlags)
                for val in self.cfg_mod[key1]:
                    value = self.cfg_mod[key1][val]
                    child0 = QtGui.QStandardItem(val)
                    child0.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
                    child1 = QtGui.QStandardItem(str(value))
                    child1.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | ~ QtCore.Qt.ItemIsSelectable)
                    parent.appendRow([child0, child1])
                self.tree.model().appendRow(parent)
            elif key1 in ["Variables"]:
                parent1 = QtGui.QStandardItem(key1)
                parent1.setFlags(QtCore.Qt.NoItemFlags)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    parent2.setFlags(QtCore.Qt.NoItemFlags)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        parent3.setFlags(QtCore.Qt.NoItemFlags)
                        for val in self.cfg_mod[key1][key2][key3]:
                            value = self.cfg_mod[key1][key2][key3][val]
                            child0 = QtGui.QStandardItem(val)
                            child0.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
                            child1 = QtGui.QStandardItem(str(value))
                            child1.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | ~ QtCore.Qt.ItemIsSelectable)
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    parent1.appendRow(parent2)
                self.tree.model().appendRow(parent1)

        self.tree.expandAll()

    def get_data(self):
        return self.cfg_mod

class edit_cfg_concatenate(QtGui.QWidget):
    def __init__(self, cfg):

        super(edit_cfg_concatenate, self).__init__()

        self.cfg_mod = copy.deepcopy(cfg)
        # Layout
        self.tree = QtGui.QTreeView()
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setModel(QtGui.QStandardItemModel())
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)

        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])

        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Options"]:
                parent1 = QtGui.QStandardItem(key1)
                parent1.setFlags(QtCore.Qt.NoItemFlags)
                for val in self.cfg_mod[key1]:
                    value = self.cfg_mod[key1][val]
                    child0 = QtGui.QStandardItem(val)
                    child0.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
                    child1 = QtGui.QStandardItem(str(value))
                    child1.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | ~ QtCore.Qt.ItemIsSelectable)
                    parent1.appendRow([child0, child1])
                self.tree.model().appendRow(parent1)
            elif key1 in ["Files"]:
                parent1 = QtGui.QStandardItem(key1)
                parent1.setFlags(QtCore.Qt.NoItemFlags)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    parent2.setFlags(QtCore.Qt.NoItemFlags)
                    for val in self.cfg_mod[key1][key2]:
                        value = self.cfg_mod[key1][key2][val]
                        child0 = QtGui.QStandardItem(val)
                        child0.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
                        child1 = QtGui.QStandardItem(str(value))
                        child1.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | ~ QtCore.Qt.ItemIsSelectable)
                        parent2.appendRow([child0, child1])
                    parent1.appendRow(parent2)
                self.tree.model().appendRow(parent1)

        self.tree.expandAll()

    def get_data(self):
        return self.cfg_mod

class edit_cfg_L4(QtGui.QWidget):
    def __init__(self, cfg):

        super(edit_cfg_L4, self).__init__()

        self.cfg_mod = copy.deepcopy(cfg)
        # Layout
        self.tree = QtGui.QTreeView()
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setModel(QtGui.QStandardItemModel())
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)

        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])

        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                parent1 = QtGui.QStandardItem(key1)
                parent1.setFlags(QtCore.Qt.NoItemFlags)
                for val in self.cfg_mod[key1]:
                    value = self.cfg_mod[key1][val]
                    child0 = QtGui.QStandardItem(val)
                    child0.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
                    child1 = QtGui.QStandardItem(str(value))
                    child1.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | ~ QtCore.Qt.ItemIsSelectable)
                    parent1.appendRow([child0, child1])
                self.tree.model().appendRow(parent1)
            elif key1 in ["Variables", "Drivers"]:
                parent1 = QtGui.QStandardItem(key1)
                parent1.setFlags(QtCore.Qt.NoItemFlags)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    parent2.setFlags(QtCore.Qt.NoItemFlags)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        parent3.setFlags(QtCore.Qt.NoItemFlags)
                        if key3 in ["GapFillFromAlternate", "GapFillFromClimatology"]:
                            for key4 in self.cfg_mod[key1][key2][key3]:
                                parent4 = QtGui.QStandardItem(key4)
                                parent4.setFlags(QtCore.Qt.NoItemFlags)
                                for val in self.cfg_mod[key1][key2][key3][key4]:
                                    value = self.cfg_mod[key1][key2][key3][key4][val]
                                    child0 = QtGui.QStandardItem(val)
                                    child0.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
                                    child1 = QtGui.QStandardItem(str(value))
                                    child1.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | ~ QtCore.Qt.ItemIsSelectable)
                                    parent4.appendRow([child0, child1])
                                parent3.appendRow(parent4)
                        elif key3 in ["MergeSeries", "RangeCheck", "ExcludeDates"]:
                            for val in self.cfg_mod[key1][key2][key3]:
                                value = self.cfg_mod[key1][key2][key3][val]
                                child0 = QtGui.QStandardItem(val)
                                child0.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
                                child1 = QtGui.QStandardItem(str(value))
                                child1.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | ~ QtCore.Qt.ItemIsSelectable)
                                parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    parent1.appendRow(parent2)
                self.tree.model().appendRow(parent1)

        self.tree.expandAll()

    def get_data(self):
        return self.cfg_mod

class pfp_l4_ui(QtGui.QDialog):
    def __init__(self, parent=None):
        super(pfp_l4_ui, self).__init__(parent)
        self.resize(400, 236)
        self.setWindowTitle("Gap fill (alternate)")
        self.RunButton = QtGui.QPushButton(self)
        self.RunButton.setGeometry(QtCore.QRect(20, 200, 93, 27))
        self.RunButton.setText("Run")
        self.DoneButton = QtGui.QPushButton(self)
        self.DoneButton.setGeometry(QtCore.QRect(150, 200, 93, 27))
        self.DoneButton.setText("Done")
        self.QuitButton = QtGui.QPushButton(self)
        self.QuitButton.setGeometry(QtCore.QRect(270, 200, 93, 27))
        self.QuitButton.setText("Quit")
        self.checkBox_ShowPlots = QtGui.QCheckBox(self)
        self.checkBox_ShowPlots.setGeometry(QtCore.QRect(20, 170, 94, 22))
        self.checkBox_ShowPlots.setText("Show plots")
        self.checkBox_ShowPlots.setChecked(True)
        self.checkBox_PlotAll = QtGui.QCheckBox(self)
        self.checkBox_PlotAll.setGeometry(QtCore.QRect(150, 170, 94, 22))
        self.checkBox_PlotAll.setText("Plot all")
        self.checkBox_Overwrite = QtGui.QCheckBox(self)
        self.checkBox_Overwrite.setGeometry(QtCore.QRect(270, 170, 94, 22))
        self.checkBox_Overwrite.setText("Overwrite")

        self.radioButton_Monthly = QtGui.QRadioButton(self)
        self.radioButton_Monthly.setGeometry(QtCore.QRect(20, 140, 110, 22))
        self.radioButton_Monthly.setText("Monthly")
        self.radioButton_NumberDays = QtGui.QRadioButton(self)
        self.radioButton_NumberDays.setGeometry(QtCore.QRect(130, 140, 110, 22))
        self.radioButton_NumberDays.setChecked(True)
        self.radioButton_NumberDays.setText("No. Days")
        self.radioButton_Manual = QtGui.QRadioButton(self)
        self.radioButton_Manual.setGeometry(QtCore.QRect(20, 110, 110, 25))
        self.radioButton_Manual.setText("Manual")
        self.radioButtons = QtGui.QButtonGroup(self)
        self.radioButtons.addButton(self.radioButton_Monthly)
        self.radioButtons.addButton(self.radioButton_NumberDays)
        self.radioButtons.addButton(self.radioButton_Manual)

        self.lineEdit_NumberDays = QtGui.QLineEdit(self)
        self.lineEdit_NumberDays.setGeometry(QtCore.QRect(220, 140, 30, 25))
        self.lineEdit_NumberDays.setText("90")
        self.checkBox_AutoComplete = QtGui.QCheckBox(self)
        self.checkBox_AutoComplete.setGeometry(QtCore.QRect(270, 140, 120, 25))
        self.checkBox_AutoComplete.setChecked(True)
        self.checkBox_AutoComplete.setText("Auto complete")
        self.lineEdit_MinPercent = QtGui.QLineEdit(self)
        self.lineEdit_MinPercent.setGeometry(QtCore.QRect(220, 110, 30, 25))
        self.lineEdit_MinPercent.setText("50")
        self.label_MinPercent = QtGui.QLabel(self)
        self.label_MinPercent.setGeometry(QtCore.QRect(140, 110, 80, 25))
        self.label_MinPercent.setText("Min pts (%)")
        self.lineEdit_EndDate = QtGui.QLineEdit(self)
        self.lineEdit_EndDate.setGeometry(QtCore.QRect(220, 77, 161, 25))
        self.label_EndDate = QtGui.QLabel(self)
        self.label_EndDate.setGeometry(QtCore.QRect(30, 80, 171, 20))
        self.label_EndDate.setText("End date (YYYY-MM-DD)")
        self.lineEdit_StartDate = QtGui.QLineEdit(self)
        self.lineEdit_StartDate.setGeometry(QtCore.QRect(220, 47, 161, 25))
        self.label_StartDate = QtGui.QLabel(self)
        self.label_StartDate.setGeometry(QtCore.QRect(30, 47, 171, 20))
        self.label_StartDate.setText("Start date (YYYY-MM-DD)")
        self.label_DataStartDate = QtGui.QLabel(self)
        self.label_DataStartDate.setGeometry(QtCore.QRect(48, 6, 111, 17))
        self.label_DataEndDate = QtGui.QLabel(self)
        self.label_DataEndDate.setGeometry(QtCore.QRect(244, 6, 101, 17))
        self.label_DataStartDate_value = QtGui.QLabel(self)
        self.label_DataStartDate_value.setGeometry(QtCore.QRect(33, 26, 151, 20))
        self.label_DataEndDate_value = QtGui.QLabel(self)
        self.label_DataEndDate_value.setGeometry(QtCore.QRect(220, 26, 141, 17))
        self.label_DataStartDate.setText("Data start date")
        self.label_DataEndDate.setText("Data end date")
        self.label_DataStartDate_value.setText("YYYY-MM-DD HH:mm")
        self.label_DataEndDate_value.setText("YYYY-MM-DD HH:mm")
