# standard modules
import copy
import inspect
import logging
import os
import pdb
# 3rd party modules
from configobj import ConfigObj
from PyQt5 import QtCore, QtGui, QtWidgets
# PFP modules
import pfp_func
import pfp_utils
import pfp_gfALT
import pfp_gfSOLO

logger = logging.getLogger("pfp_log")

class myMessageBox(QtWidgets.QMessageBox):
    def __init__(self, msg, title="Information", parent=None):
        super(myMessageBox, self).__init__(parent)
        if title == "Critical":
            self.setIcon(QtWidgets.QMessageBox.Critical)
        elif title == "Warning":
            self.setIcon(QtWidgets.QMessageBox.Warning)
        else:
            self.setIcon(QtWidgets.QMessageBox.Information)
        self.setText(msg)
        self.setWindowTitle(title)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.exec_()

class MsgBox_ContinueOrQuit(QtWidgets.QMessageBox):
    def __init__(self, msg, title="Information", parent=None):
        super(MsgBox_ContinueOrQuit, self).__init__(parent)
        if title == "Critical":
            self.setIcon(QtWidgets.QMessageBox.Critical)
        elif title == "Warning":
            self.setIcon(QtWidgets.QMessageBox.Warning)
        else:
            self.setIcon(QtWidgets.QMessageBox.Information)
        self.setText(msg)
        self.setWindowTitle(title)
        self.setStandardButtons(QtWidgets.QMessageBox.Yes |
                                QtWidgets.QMessageBox.No)
        self.button(QtWidgets.QMessageBox.Yes).setText("Continue")
        self.button(QtWidgets.QMessageBox.No).setText("Quit")
        self.exec_()

class MsgBox_Quit(QtWidgets.QMessageBox):
    def __init__(self, msg, title="Information", parent=None):
        super(MsgBox_Quit, self).__init__(parent)
        if title == "Critical":
            self.setIcon(QtWidgets.QMessageBox.Critical)
        elif title == "Warning":
            self.setIcon(QtWidgets.QMessageBox.Warning)
        else:
            self.setIcon(QtWidgets.QMessageBox.Information)
        self.setText(msg)
        self.setWindowTitle(title)
        self.setStandardButtons(QtWidgets.QMessageBox.No)
        self.button(QtWidgets.QMessageBox.No).setText("Quit")
        self.exec_()

class myTxtBox(QtWidgets.QInputDialog):
    def __init__(self, title="", prompt="", parent=None):
        super(myTxtBox, self).__init__(parent)
        self.getText(None, title, prompt, QtWidgets.QLineEdit.Normal,"")

class edit_cfg_L1(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L1, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_L1_gui()

    def edit_L1_gui(self):
        """ Edit L1 control file GUI."""
        # get a QTreeView and a standard model
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        #self.tree = custom_treeview()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        # do the QTreeView layout
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # set some features of the QTreeView
        self.view.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        # set the QTreeView model
        self.view.setModel(self.model)
        # enable drag and drop
        self.view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 200)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # there must be some way to do this recursively
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Files", "Global", "Output"]:
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    val = self.cfg[key1][key2]
                    val = self.parse_cfg_values(key2, val, ['"', "'"])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Variables"]:
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for key4 in self.cfg[key1][key2][key3]:
                            val = self.cfg[key1][key2][key3][key4]
                            val = self.parse_cfg_values(key4, val, ['"', "'"])
                            child0 = QtGui.QStandardItem(key4)
                            child1 = QtGui.QStandardItem(val)
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = ConfigObj(indent_type="    ", list_values=False)
        cfg["level"] = "L1"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["Variables"]:
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        subsubsection = subsection.child(k)
                        key3 = str(subsubsection.text())
                        cfg[key1][key2][key3] = {}
                        for l in range(subsubsection.rowCount()):
                            key4 = str(subsubsection.child(l, 0).text())
                            val4 = str(subsubsection.child(l, 1).text())
                            cfg[key1][key2][key3][key4] = val4
        return cfg

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_level_selected_item(self):
        """ Get the level of the selected item in the model."""
        indexes = self.view.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            idx = indexes[0]
            while idx.parent().isValid():
                idx = idx.parent()
                level += 1
        return level

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # update the control file contents
        self.cfg = self.get_data_from_model()
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the level of the selected item
        level = self.get_level_selected_item()
        if level == 0:
            selected_text = str(idx.data())
            if selected_text == "Global":
                self.context_menu.actionAddGlobal = QtWidgets.QAction(self)
                self.context_menu.actionAddGlobal.setText("Add attribute")
                self.context_menu.addAction(self.context_menu.actionAddGlobal)
                self.context_menu.actionAddGlobal.triggered.connect(self.add_global)
            elif selected_text == "Variables":
                self.context_menu.actionAddVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
        elif level == 1:
            selected_item = idx.model().itemFromIndex(idx)
            parent = selected_item.parent()
            if (str(parent.text()) == "Files") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                # check to see if we have the selected subsection
                if key == "file_path":
                    self.context_menu.actionBrowseFilePath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key == "in_filename":
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key == "out_filename":
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                else:
                    pass
            elif str(parent.text()) == "Global":
                self.context_menu.actionRemoveGlobal = QtWidgets.QAction(self)
                self.context_menu.actionRemoveGlobal.setText("Remove attribute")
                self.context_menu.addAction(self.context_menu.actionRemoveGlobal)
                self.context_menu.actionRemoveGlobal.triggered.connect(self.remove_item)
            elif str(parent.text()) == "Variables":
                self.context_menu.actionAddFunction = QtWidgets.QAction(self)
                self.context_menu.actionAddFunction.setText("Add Function")
                self.context_menu.addAction(self.context_menu.actionAddFunction)
                self.context_menu.actionAddFunction.triggered.connect(self.add_function)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveVariable)
                self.context_menu.actionRemoveVariable.triggered.connect(self.remove_item)
        elif level == 2:
            section_text = str(idx.parent().parent().data())
            subsection_text = str(idx.parent().data())
            subsubsection_text = str(idx.data())
            if section_text == "Variables":
                if subsubsection_text == "Attr":
                    self.context_menu.actionAddAttribute = QtWidgets.QAction(self)
                    self.context_menu.actionAddAttribute.setText("Add attribute")
                    self.context_menu.addAction(self.context_menu.actionAddAttribute)
                    self.context_menu.actionAddAttribute.triggered.connect(self.add_attribute)
                elif subsubsection_text in ["Function", "xl", "csv"]:
                    self.context_menu.actionRemoveSubSubSection = QtWidgets.QAction(self)
                    self.context_menu.actionRemoveSubSubSection.setText("Remove item")
                    self.context_menu.addAction(self.context_menu.actionRemoveSubSubSection)
                    self.context_menu.actionRemoveSubSubSection.triggered.connect(self.remove_item)
        elif level == 3:
            if str(idx.parent().data()) == "Attr":
                self.context_menu.actionRemoveAttribute = QtWidgets.QAction(self)
                self.context_menu.actionRemoveAttribute.setText("Remove attribute")
                self.context_menu.addAction(self.context_menu.actionRemoveAttribute)
                self.context_menu.actionRemoveAttribute.triggered.connect(self.remove_item)
            elif (str(idx.parent().data()) == "Function" and
                  str(idx.data()) == "Right click to browse"):
                implemented_functions_name = [name for name,data in inspect.getmembers(pfp_func,inspect.isfunction)]
                self.context_menu.actionAddFunction = {}
                for item in implemented_functions_name:
                    self.context_menu.actionAddFunction[item] = QtWidgets.QAction(self)
                    self.context_menu.actionAddFunction[item].setText(str(item))
                    self.context_menu.addAction(self.context_menu.actionAddFunction[item])
                    self.context_menu.actionAddFunction[item].triggered.connect(self.add_function_entry)

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def add_attribute(self):
        """ Add a variable attribute to a variable in the [Variables] section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the new children
        child0 = QtGui.QStandardItem("New attribute")
        child1 = QtGui.QStandardItem("")
        # add them to the parent
        selected_item.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_function(self):
        """ Add a function to a variable."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        dict_to_add = {"Function":{"func": "Right click to browse"}}
        # add the subsubsection
        self.add_subsubsection(selected_item, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_function_entry(self):
        """ Add the selected function to the variables [Function] subsection."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get a list of function names in pfp_func
        implemented_functions_name = [name for name,data in inspect.getmembers(pfp_func,inspect.isfunction)]
        # get the arguments for the functions in pfp_func
        implemented_functions_data = [data for name,data in inspect.getmembers(pfp_func,inspect.isfunction)]
        # get the context menu entry that has been selected
        sender = str(self.context_menu.sender().text())
        # get the arguments for the selected function
        args = inspect.getargspec(implemented_functions_data[implemented_functions_name.index(sender)])
        # construct the function string
        function_string = sender+"("
        for item in args[0][2:]:
            function_string = function_string + str(item) + ","
        function_string = function_string[:-1] + ")"
        # get the selected item from the index
        item = idx.model().itemFromIndex(idx)
        # change the text of the selected item
        item.setText(function_string)

    def add_global(self):
        """ Add a new entry to the [Global] section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the new children
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        selected_item.appendRow([child0, child1])
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_subsection(self, section, dict_to_add):
        for key in dict_to_add:
            val = str(dict_to_add[key])
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            section.appendRow([child0, child1])

    def add_subsubsection(self, subsection, dict_to_add):
        """ Add a subsubsection to the model."""
        for key in dict_to_add:
            subsubsection = QtGui.QStandardItem(key)
            self.add_subsection(subsubsection, dict_to_add[key])
            subsection.appendRow(subsubsection)

    def add_variable(self):
        """ Add a new variable."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        new_var = {"xl":{"sheet":"", "name":""},
                   "Attr":{"height":"<height>m", "instrument":"", "long_name":"",
                           "serial_number":"", "standard_name":"", "units":""}}
        subsection = QtGui.QStandardItem("New variable")
        self.add_subsubsection(subsection, new_var)
        parent.appendRow(subsection)
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def browse_file_path(self):
        """ Browse for the data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder ...", file_path)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)
            self.update_tab_text()

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                              directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])
            self.update_tab_text()

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                              directory=file_path, filter="*.nc")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])
            self.update_tab_text()

    def parse_cfg_values(self, k, v, strip_list):
        """ Parse key values to remove unnecessary characters."""
        for c in strip_list:
            if (c in v):
                if (v != '""') and (v != "''"):
                    self.cfg_changed = True
                v = v.replace(c, "")
        return v

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        self.update_tab_text()

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L2(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L2, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_L2_gui()

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        new_qc = {"DependencyCheck":{"source":""}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        new_qc = {"DiurnalCheck":{"NumSd":"5"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        new_qc = {"ExcludeDates":{"0":"YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_excludedaterange(self):
        """ Add another date range to the ExcludeDates QC check."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_excludehours(self):
        """ Add an exclude hours check to a variable."""
        print " add ExcludeHours here"

    def add_file_path(self):
        """ Add file_path to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("file_path")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_in_filename(self):
        """ Add in_filename to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("in_filename")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_irga_check(self):
        """ Add IRGA check to Options section."""
        new_options = {"IRGA_Check": "Yes"}
        for key in new_options:
            value = new_options[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(value)
            self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_linear(self):
        """ Add a linear correction to a variable."""
        new_qc = {"Linear": {"0": "YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM, 1.0, 0.0"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_linearrange(self):
        """ Add another date range to the Linear QC check."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM, 1.0, 0.0")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_lowercheck(self):
        """ Add a lower range check to a variable."""
        new_qc = {"LowerCheck":{"0":"YYYY-mm-dd HH:MM,<start_value>,YYYY-mm-dd HH:MM,<end_value>"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_lowercheckrange(self):
        """ Add another date range to the LowerCheck QC check."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM,<start_value>,YYYY-mm-dd HH:MM,<end_value>")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_options_section(self):
        """ Add an Options section."""
        self.sections["Options"] = QtGui.QStandardItem("Options")
        new_options = {"irga_type": "Li-7500A"}
        for key in new_options:
            value = new_options[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(value)
            self.sections["Options"].appendRow([child0, child1])
        self.model.insertRow(self.section_headings.index("Variables"), self.sections["Options"])
        self.update_tab_text()

    def add_out_filename(self):
        """ Add out_filename to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("out_filename")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_plot_path(self):
        """ Add plot_path to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("plot_path")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_qc_check(self, selected_item, new_qc):
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key in new_qc[key1]:
                val = str(new_qc[key1][key])
                child0 = QtGui.QStandardItem(key)
                child1 = QtGui.QStandardItem(val)
                parent.appendRow([child0, child1])
            selected_item.appendRow(parent)
        self.update_tab_text()

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        new_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_scatterplot(self):
        """ Add a new scatter plot to the 'Plots' section."""
        new_plot = {"Type":"xy", "XSeries":"", "YSeries":""}
        parent = QtGui.QStandardItem("New scatter plot")
        for key in new_plot:
            val = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(val))
            parent.appendRow([child0, child1])
        self.sections["Plots"].appendRow(parent)
        self.update_tab_text()

    def add_sonic_check(self):
        """ Add sonic check to Options section."""
        new_options = {"SONIC_Check": "Yes"}
        for key in new_options:
            value = new_options[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(value)
            self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_subsection(self, section, dict_to_add):
        for key in dict_to_add:
            val = str(dict_to_add[key])
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            section.appendRow([child0, child1])

    def add_subsubsection(self, subsection, dict_to_add):
        """ Add a subsubsection to the model."""
        for key in dict_to_add:
            subsubsection = QtGui.QStandardItem(key)
            self.add_subsection(subsubsection, dict_to_add[key])
            subsection.appendRow(subsubsection)

    def add_timeseries(self):
        """ Add a new time series to the 'Plots' section."""
        new_plot = {"Variables":""}
        parent = QtGui.QStandardItem("New time series")
        for key in new_plot:
            value = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(value))
            parent.appendRow([child0, child1])
        self.sections["Plots"].appendRow(parent)
        self.update_tab_text()

    def add_uppercheck(self):
        """ Add a upper range check to a variable."""
        new_qc = {"UpperCheck":{"0":"YYYY-mm-dd HH:MM,<start_value>,YYYY-mm-dd HH:MM,<end_value>"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_uppercheckrange(self):
        """ Add another date range to the UpperCheck QC check."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM,<start_value>,YYYY-mm-dd HH:MM,<end_value>")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_variable(self):
        """ Add a new variable to the 'Variables' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        new_var_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        subsection = QtGui.QStandardItem("New variable")
        self.add_subsubsection(subsection, new_var_qc)
        parent.appendRow(subsection)
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_winddirectioncorrection(self):
        """ Add the wind direction correction check to a variable."""
        new_qc = {"CorrectWindDirection":{"0":"YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM, <correction>"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_winddirectioncorrectionrange(self):
        """ Add another date range to the wind direction correction."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM, <correction>")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def browse_file_path(self):
        """ Browse for the data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder ...",
                                                         file_path, QtWidgets.QFileDialog.ShowDirsOnly)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                          directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                          directory=file_path, filter="*.nc")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_plot_path(self):
        """ Browse for the plot path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder ...",
                                                         file_path, QtWidgets.QFileDialog.ShowDirsOnly)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the level of the selected item
        level = self.get_level_selected_item()
        if level == 0:
            add_separator = False
            selected_text = str(idx.data())
            self.section_headings = []
            root = self.model.invisibleRootItem()
            for i in range(root.rowCount()):
                self.section_headings.append(str(root.child(i).text()))
            if "Options" not in self.section_headings and selected_text == "Files":
                self.context_menu.actionAddOptionsSection = QtWidgets.QAction(self)
                self.context_menu.actionAddOptionsSection.setText("Add Options section")
                self.context_menu.addAction(self.context_menu.actionAddOptionsSection)
                self.context_menu.actionAddOptionsSection.triggered.connect(self.add_options_section)
                add_separator = True
            if selected_text == "Files":
                if add_separator:
                    self.context_menu.addSeparator()
                    add_separator = False
                existing_entries = self.get_existing_entries()
                if "file_path" not in existing_entries:
                    self.context_menu.actionAddfile_path = QtWidgets.QAction(self)
                    self.context_menu.actionAddfile_path.setText("Add file_path")
                    self.context_menu.addAction(self.context_menu.actionAddfile_path)
                    self.context_menu.actionAddfile_path.triggered.connect(self.add_file_path)
                if "in_filename" not in existing_entries:
                    self.context_menu.actionAddin_filename = QtWidgets.QAction(self)
                    self.context_menu.actionAddin_filename.setText("Add in_filename")
                    self.context_menu.addAction(self.context_menu.actionAddin_filename)
                    self.context_menu.actionAddin_filename.triggered.connect(self.add_in_filename)
                if "out_filename" not in existing_entries:
                    self.context_menu.actionAddout_filename = QtWidgets.QAction(self)
                    self.context_menu.actionAddout_filename.setText("Add out_filename")
                    self.context_menu.addAction(self.context_menu.actionAddout_filename)
                    self.context_menu.actionAddout_filename.triggered.connect(self.add_out_filename)
                if "plot_path" not in existing_entries:
                    self.context_menu.actionAddplot_path = QtWidgets.QAction(self)
                    self.context_menu.actionAddplot_path.setText("Add plot_path")
                    self.context_menu.addAction(self.context_menu.actionAddplot_path)
                    self.context_menu.actionAddplot_path.triggered.connect(self.add_plot_path)
            elif selected_text == "Options":
                existing_entries = self.get_existing_entries()
                if "SONIC_Check" not in existing_entries:
                    self.context_menu.actionSonicCheck = QtWidgets.QAction(self)
                    self.context_menu.actionSonicCheck.setText("SONIC_Check")
                    self.context_menu.addAction(self.context_menu.actionSonicCheck)
                    self.context_menu.actionSonicCheck.triggered.connect(self.add_sonic_check)
                    add_separator = True
                if "IRGA_Check" not in existing_entries:
                    self.context_menu.actionIRGACheck = QtWidgets.QAction(self)
                    self.context_menu.actionIRGACheck.setText("IRGA_Check")
                    self.context_menu.addAction(self.context_menu.actionIRGACheck)
                    self.context_menu.actionIRGACheck.triggered.connect(self.add_irga_check)
                    add_separator = True
                if add_separator:
                    self.context_menu.addSeparator()
                    add_separator = False
                self.context_menu.actionRemoveOptionsSection = QtWidgets.QAction(self)
                self.context_menu.actionRemoveOptionsSection.setText("Remove section")
                self.context_menu.addAction(self.context_menu.actionRemoveOptionsSection)
                self.context_menu.actionRemoveOptionsSection.triggered.connect(self.remove_section)
            elif selected_text == "Variables":
                self.context_menu.actionAddVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
            elif selected_text == "Plots":
                self.context_menu.actionAddTimeSeries = QtWidgets.QAction(self)
                self.context_menu.actionAddTimeSeries.setText("Add time series")
                self.context_menu.addAction(self.context_menu.actionAddTimeSeries)
                self.context_menu.actionAddTimeSeries.triggered.connect(self.add_timeseries)
                self.context_menu.actionAddScatterPlot = QtWidgets.QAction(self)
                self.context_menu.actionAddScatterPlot.setText("Add scatter plot")
                self.context_menu.addAction(self.context_menu.actionAddScatterPlot)
                self.context_menu.actionAddScatterPlot.triggered.connect(self.add_scatterplot)
        elif level == 1:
            selected_item = idx.model().itemFromIndex(idx)
            parent = selected_item.parent()
            if (str(parent.text()) == "Files") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                # check to see if we have the selected subsection
                if key == "file_path":
                    self.context_menu.actionBrowseFilePath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key == "in_filename":
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key == "out_filename":
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                elif key == "plot_path":
                    self.context_menu.actionBrowsePlotPath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowsePlotPath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowsePlotPath)
                    self.context_menu.actionBrowsePlotPath.triggered.connect(self.browse_plot_path)
                else:
                    pass
            elif (str(parent.text()) == "Options") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                if key == "irga_type":
                    existing_entry = str(parent.child(selected_item.row(),1).text())
                    if existing_entry != "Li-7500":
                        self.context_menu.actionSetIRGATypeLi7500 = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeLi7500.setText("Li-7500")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeLi7500)
                        self.context_menu.actionSetIRGATypeLi7500.triggered.connect(self.set_irga_li7500)
                    if existing_entry != "Li-7500A (<V6.5)":
                        self.context_menu.actionSetIRGATypeLi7500APre6_5 = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeLi7500APre6_5.setText("Li-7500A (<V6.5)")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeLi7500APre6_5)
                        self.context_menu.actionSetIRGATypeLi7500APre6_5.triggered.connect(self.set_irga_li7500a_pre6_5)
                    if existing_entry != "Li-7500A (>=V6.5)":
                        self.context_menu.actionSetIRGATypeLi7500APost6_5 = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeLi7500APost6_5.setText("Li-7500A (>=V6.5)")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeLi7500APost6_5)
                        self.context_menu.actionSetIRGATypeLi7500APost6_5.triggered.connect(self.set_irga_li7500a_post6_5)
                    if existing_entry != "Li-7500RS":
                        self.context_menu.actionSetIRGATypeLi7500RS = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeLi7500RS.setText("Li-7500RS")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeLi7500RS)
                        self.context_menu.actionSetIRGATypeLi7500RS.triggered.connect(self.set_irga_li7500rs)
                    if existing_entry != "Li-7200":
                        self.context_menu.actionSetIRGATypeLi7200 = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeLi7200.setText("Li-7200")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeLi7200)
                        self.context_menu.actionSetIRGATypeLi7200.triggered.connect(self.set_irga_li7200)
                    if existing_entry != "EC150":
                        self.context_menu.actionSetIRGATypeEC150 = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeEC150.setText("EC150")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeEC150)
                        self.context_menu.actionSetIRGATypeEC150.triggered.connect(self.set_irga_ec150)
                    if existing_entry != "EC155":
                        self.context_menu.actionSetIRGATypeEC155 = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeEC155.setText("EC155")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeEC155)
                        self.context_menu.actionSetIRGATypeEC155.triggered.connect(self.set_irga_ec155)
                    if existing_entry != "IRGASON":
                        self.context_menu.actionSetIRGATypeIRGASON = QtWidgets.QAction(self)
                        self.context_menu.actionSetIRGATypeIRGASON.setText("IRGASON")
                        self.context_menu.addAction(self.context_menu.actionSetIRGATypeIRGASON)
                        self.context_menu.actionSetIRGATypeIRGASON.triggered.connect(self.set_irga_irgason)
                elif key in ["SONIC_Check", "IRGA_Check"]:
                    existing_entry = str(parent.child(selected_item.row(),1).text())
                    if existing_entry != "Yes":
                        self.context_menu.actionSetCheckYes = QtWidgets.QAction(self)
                        self.context_menu.actionSetCheckYes.setText("Yes")
                        self.context_menu.addAction(self.context_menu.actionSetCheckYes)
                        self.context_menu.actionSetCheckYes.triggered.connect(self.set_check_yes)
                    if existing_entry != "No":
                        self.context_menu.actionSetCheckNo = QtWidgets.QAction(self)
                        self.context_menu.actionSetCheckNo.setText("No")
                        self.context_menu.addAction(self.context_menu.actionSetCheckNo)
                        self.context_menu.actionSetCheckNo.triggered.connect(self.set_check_no)
            elif (str(parent.text()) == "Options") and (selected_item.column() == 0):
                if selected_item.text() in ["SONIC_Check", "IRGA_Check"]:
                    self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                    self.context_menu.actionRemoveOption.setText("Remove option")
                    self.context_menu.addAction(self.context_menu.actionRemoveOption)
                    self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
            elif str(parent.text()) == "Variables":
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                # only put a QC check in the context menu if it is not already present
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtWidgets.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                if "LowerCheck" not in existing_entries:
                    self.context_menu.actionAddLowerCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddLowerCheck.setText("Add LowerCheck")
                    self.context_menu.addAction(self.context_menu.actionAddLowerCheck)
                    self.context_menu.actionAddLowerCheck.triggered.connect(self.add_lowercheck)
                if "UpperCheck" not in existing_entries:
                    self.context_menu.actionAddUpperCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddUpperCheck.setText("Add UpperCheck")
                    self.context_menu.addAction(self.context_menu.actionAddUpperCheck)
                    self.context_menu.actionAddUpperCheck.triggered.connect(self.add_uppercheck)
                if "CorrectWindDirection" not in existing_entries:
                    self.context_menu.actionAddWindDirectionCorrection = QtWidgets.QAction(self)
                    self.context_menu.actionAddWindDirectionCorrection.setText("Add CorrectWindDirection")
                    self.context_menu.addAction(self.context_menu.actionAddWindDirectionCorrection)
                    self.context_menu.actionAddWindDirectionCorrection.triggered.connect(self.add_winddirectioncorrection)
                if "Linear" not in existing_entries:
                    self.context_menu.actionAddLinear = QtWidgets.QAction(self)
                    self.context_menu.actionAddLinear.setText("Add Linear")
                    self.context_menu.addAction(self.context_menu.actionAddLinear)
                    self.context_menu.actionAddLinear.triggered.connect(self.add_linear)
                #self.context_menu.actionAddExcludeHours = QtWidgets.QAction(self)
                #self.context_menu.actionAddExcludeHours.setText("Add ExcludeHours")
                #self.context_menu.addAction(self.context_menu.actionAddExcludeHours)
                #self.context_menu.actionAddExcludeHours.triggered.connect(self.add_excludehours)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveVariable)
                self.context_menu.actionRemoveVariable.triggered.connect(self.remove_item)
            elif str(parent.text()) == "Plots":
                self.context_menu.actionRemovePlot = QtWidgets.QAction(self)
                self.context_menu.actionRemovePlot.setText("Remove plot")
                self.context_menu.addAction(self.context_menu.actionRemovePlot)
                self.context_menu.actionRemovePlot.triggered.connect(self.remove_item)
        elif level == 2:
            add_separator = False
            if str(idx.data()) in ["ExcludeDates"]:
                self.context_menu.actionAddExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                add_separator = True
            if str(idx.data()) in ["LowerCheck"]:
                self.context_menu.actionAddLowerCheckRange = QtWidgets.QAction(self)
                self.context_menu.actionAddLowerCheckRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddLowerCheckRange)
                self.context_menu.actionAddLowerCheckRange.triggered.connect(self.add_lowercheckrange)
                add_separator = True
            if str(idx.data()) in ["UpperCheck"]:
                self.context_menu.actionAddUpperCheckRange = QtWidgets.QAction(self)
                self.context_menu.actionAddUpperCheckRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddUpperCheckRange)
                self.context_menu.actionAddUpperCheckRange.triggered.connect(self.add_uppercheckrange)
                add_separator = True
            if str(idx.data()) in ["CorrectWindDirection"]:
                self.context_menu.actionAddWindDirectionCorrectionRange = QtWidgets.QAction(self)
                self.context_menu.actionAddWindDirectionCorrectionRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddWindDirectionCorrectionRange)
                self.context_menu.actionAddWindDirectionCorrectionRange.triggered.connect(self.add_winddirectioncorrectionrange)
                add_separator = True
            if str(idx.data()) in ["Linear"]:
                self.context_menu.actionAddLinearRange = QtWidgets.QAction(self)
                self.context_menu.actionAddLinearRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddLinearRange)
                self.context_menu.actionAddLinearRange.triggered.connect(self.add_linearrange)
                add_separator = True
            if add_separator:
                self.context_menu.addSeparator()
                add_separator = False
            self.context_menu.actionRemoveQCCheck = QtWidgets.QAction(self)
            self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
            self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
            self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_item)
        elif level == 3:
            if (str(idx.parent().data()) in ["ExcludeDates", "LowerCheck", "UpperCheck", "Linear"] and
                str(idx.data()) != "0"):
                self.context_menu.actionRemoveExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionRemoveExcludeDateRange.setText("Remove date range")
                self.context_menu.addAction(self.context_menu.actionRemoveExcludeDateRange)
                self.context_menu.actionRemoveExcludeDateRange.triggered.connect(self.remove_daterange)

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def edit_L2_gui(self):
        """ Edit L2 control file GUI."""
        # get a QTreeView and a standard model
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.view.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        # set the QTreeView model
        self.view.setModel(self.model)
        # enable drag and drop
        self.view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 200)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = ConfigObj(indent_type="    ", list_values=False)
        cfg["level"] = "L2"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files", "Options"]:
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["Plots"]:
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3
            elif key1 in ["Variables"]:
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        subsubsection = subsection.child(k)
                        key3 = str(subsubsection.text())
                        cfg[key1][key2][key3] = {}
                        for l in range(subsubsection.rowCount()):
                            key4 = str(subsubsection.child(l, 0).text())
                            val4 = str(subsubsection.child(l, 1).text())
                            cfg[key1][key2][key3][key4] = val4
        return cfg

    def get_existing_entries(self):
        """ Get a list of existing entries in the current section."""
        # index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from its index
        selected_item = idx.model().itemFromIndex(idx)
        # build a list of existing QC checks
        existing_entries = []
        if selected_item.hasChildren():
            for i in range(selected_item.rowCount()):
                existing_entries.append(str(selected_item.child(i, 0).text()))
        return existing_entries

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_level_selected_item(self):
        """ Get the level of the selected item in the model."""
        indexes = self.view.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            idx = indexes[0]
            while idx.parent().isValid():
                idx = idx.parent()
                level += 1
        return level

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # there must be some way to do this recursively
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Files", "Options"]:
                # sections with only 1 level
                self.sections[key1] = QtGui.QStandardItem(key1)
                for val in self.cfg[key1]:
                    value = self.cfg[key1][val]
                    value = self.parse_cfg_files_value(val, value)
                    child0 = QtGui.QStandardItem(val)
                    child1 = QtGui.QStandardItem(value)
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif  key1 in ["Plots"]:
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    # handle old-style control files with separate Title key
                    title = self.parse_cfg_plots_title(key1, key2)
                    parent2 = QtGui.QStandardItem(title)
                    for val in self.cfg[key1][key2]:
                        value = self.cfg[key1][key2][val]
                        value = self.parse_cfg_plots_value(val, value)
                        child0 = QtGui.QStandardItem(val)
                        child1 = QtGui.QStandardItem(value)
                        parent2.appendRow([child0, child1])
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Variables"]:
                # sections with 3 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for val in self.cfg[key1][key2][key3]:
                            value = self.cfg[key1][key2][key3][val]
                            value = self.parse_cfg_variables_value(key3, value)
                            child0 = QtGui.QStandardItem(val)
                            child1 = QtGui.QStandardItem(value)
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()
        # update the control file contents
        self.cfg = self.get_data_from_model()

    def parse_cfg_files_value(self, k, v):
        """ Parse the [Files] section keys to remove unnecessary characters."""
        strip_list = ['"', "'"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def parse_cfg_plots_title(self, key1, key2):
        """ Parse the [Plots] section for a title."""
        if "Title" in self.cfg[key1][key2]:
            title = self.cfg[key1][key2]["Title"]
            del self.cfg[key1][key2]["Title"]
            self.cfg_changed = True
        else:
            title = key2
        strip_list = ['"', "'"]
        for c in strip_list:
            if c in title:
                title = title.replace(c, "")
                self.cfg_changed = True
        return title

    def parse_cfg_plots_value(self, k, v):
        """ Parse the [Plots] section keys to remove unnecessary characters."""
        if k in ["Variables", "Type", "XSeries", "YSeries"]:
            if ("[" in v) and ("]" in v):
                v = v.replace("[", "").replace("]", "")
                self.cfg_changed = True
        strip_list = [" ", '"', "'"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def parse_cfg_variables_value(self, k, v):
        """ Parse value from control file to remove unnecessary characters."""
        try:
            # check to see if it is a number
            r = float(v)
        except ValueError as e:
            if ("[" in v) and ("]" in v) and ("*" in v):
                # old style of [value]*12
                v = v[v.index("[")+1:v.index("]")]
                self.cfg_changed = True
            elif ("[" in v) and ("]" in v) and ("*" not in v):
                # old style of [1,2,3,4,5,6,7,8,9,10,11,12]
                v = v.replace("[", "").replace("]", "")
                self.cfg_changed = True
        # remove white space and quotes
        if k in ["RangeCheck", "DiurnalCheck", "DependencyCheck"]:
            strip_list = [" ", '"', "'"]
        elif k in ["ExcludeDates", "ExcludeHours", "LowerCheck", "UpperCheck", "Linear"]:
            # don't remove white space between date and time
            strip_list = ['"', "'"]
        else:
            msg = " QC check " + k + " not recognised"
            logger.warning(msg)
            return v
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def remove_daterange(self):
        """ Remove a date range from the ustar_threshold section."""
        # remove the date range
        self.remove_item()
        # index of selected item
        idx = self.view.selectedIndexes()[0]
        # item from index
        selected_item = idx.model().itemFromIndex(idx)
        # parent of selected item
        parent = selected_item.parent()
        # renumber the subsections
        for i in range(parent.rowCount()):
            parent.child(i, 0).setText(str(i))

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        self.update_tab_text()

    def remove_section(self):
        """ Remove a section from the view."""
        # loop over selected items in the tree
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the root
        root = self.model.invisibleRootItem()
        # remove the row
        root.removeRow(selected_item.row())
        self.update_tab_text()

    def set_irga_li7500(self):
        """ Set the IRGA type to Li-7500."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("Li-7500")

    def set_irga_li7500a_pre6_5(self):
        """ Set the IRGA type to Li-7500A pre V6.5."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("Li-7500A (<V6.5)")

    def set_irga_li7500a_post6_5(self):
        """ Set the IRGA type to Li-7500A post V6.5."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("Li-7500A (>=V6.5)")

    def set_irga_li7500rs(self):
        """ Set the IRGA type to Li-7500RS."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("Li-7500RS")

    def set_irga_li7200(self):
        """ Set the IRGA type to Li-7200."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("Li-7200")

    def set_irga_ec150(self):
        """ Set the IRGA type to EC150."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("EC150")

    def set_irga_ec155(self):
        """ Set the IRGA type to EC155."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("EC155")

    def set_irga_irgason(self):
        """ Set the IRGA type to IRGASON."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("IRGASON")

    def set_check_no(self):
        """ Set the Sonic check to No."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("No")

    def set_check_yes(self):
        """ Set the Sonic check to Yes."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        parent = selected_item.parent()
        parent.child(selected_item.row(), 1).setText("Yes")

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L3(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L3, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_L3_gui()

    def add_2dcoordrotation(self):
        """ Add 2DCoordRotation to the [Options] section."""
        child0 = QtGui.QStandardItem("2DCoordRotation")
        child1 = QtGui.QStandardItem("Yes")
        self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_applyfcstorage_to_options(self):
        """ Add storage term to Fc to the [Options] section."""
        child0 = QtGui.QStandardItem("ApplyFcStorage")
        child1 = QtGui.QStandardItem("Yes")
        self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_applyfcstorage_to_variable(self):
        """ Add apply Fc storage instruction to a variable."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        parent = QtGui.QStandardItem("ApplyFcStorage")
        child0 = QtGui.QStandardItem("source")
        child1 = QtGui.QStandardItem("")
        parent.appendRow([child0, child1])
        selected_item.appendRow(parent)
        self.update_tab_text()

    def add_averageseries(self):
        """ Add an average series instruction to a variable."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        parent = QtGui.QStandardItem("AverageSeries")
        child0 = QtGui.QStandardItem("source")
        child1 = QtGui.QStandardItem("")
        parent.appendRow([child0, child1])
        selected_item.appendRow(parent)
        self.update_tab_text()

    def add_correctindividualfg(self):
        """ Add correct individual Fg to the [Options] section."""
        child0 = QtGui.QStandardItem("CorrectIndividualFg")
        child1 = QtGui.QStandardItem("Yes")
        self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_correctfgforstorage(self):
        """ Add correct Fg for storage to the [Options] section."""
        child0 = QtGui.QStandardItem("CorrectFgForStorage")
        child1 = QtGui.QStandardItem("Yes")
        self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        new_qc = {"DependencyCheck":{"source":""}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        new_qc = {"DiurnalCheck":{"NumSd":"5"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        new_qc = {"ExcludeDates":{"0":"YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM"}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_excludedaterange(self):
        """ Add another date range to the ExcludeDates QC check."""
        # loop over selected items in the tree
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_file_path(self):
        """ Add file_path to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("file_path")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_imports_section(self):
        """ Add an Imports section."""
        self.sections["Imports"] = QtGui.QStandardItem("Imports")
        self.add_imports_variable()
        self.model.insertRow(self.section_headings.index("Files")+1, self.sections["Imports"])
        self.update_tab_text()

    def add_imports_variable(self):
        """ Add a variable to the Imports section."""
        new_import = {"file_name": "Right click to browse", "var_name": "<variable_name>"}
        new_variable = QtGui.QStandardItem("New variable")
        for key in new_import:
            val = new_import[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            new_variable.appendRow([child0, child1])
        self.sections["Imports"].appendRow(new_variable)
        self.update_tab_text()

    def add_in_filename(self):
        """ Add in_filename to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("in_filename")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_massmancorrection(self):
        """ Add Massman correction to the [Options] section."""
        child0 = QtGui.QStandardItem("MassmanCorrection")
        child1 = QtGui.QStandardItem("Yes")
        self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_massman_section(self):
        """ Add a Massman section."""
        self.sections["Massman"] = QtGui.QStandardItem("Massman")
        new_massman = {"zmd": "<height_above_displacement_plane>",
                       "z0": "<roughness_length>",
                       "north_separation": "<north_separation>",
                       "east_separation": "<east_separation>"}
        for key in new_massman:
            value = new_massman[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(value)
            self.sections["Massman"].appendRow([child0, child1])
        self.model.insertRow(self.section_headings.index("Variables"), self.sections["Massman"])
        self.update_tab_text()

    def add_mergeseries(self):
        """ Add a merge series instruction to a variable."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        parent = QtGui.QStandardItem("MergeSeries")
        child0 = QtGui.QStandardItem("source")
        child1 = QtGui.QStandardItem("")
        parent.appendRow([child0, child1])
        selected_item.appendRow(parent)
        self.update_tab_text()

    def add_out_filename(self):
        """ Add out_filename to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("out_filename")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_plot_path(self):
        """ Add plot_path to the 'Files' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        child0 = QtGui.QStandardItem("plot_path")
        child1 = QtGui.QStandardItem("Right click to browse")
        parent.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_qc_check(self, selected_item, new_qc):
        """ Add a QC check to a variable."""
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key in new_qc[key1]:
                val = str(new_qc[key1][key])
                child0 = QtGui.QStandardItem(key)
                child1 = QtGui.QStandardItem(val)
                parent.appendRow([child0, child1])
            selected_item.appendRow(parent)
        self.update_tab_text()

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        new_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        self.add_qc_check(selected_item, new_qc)
        self.update_tab_text()

    def add_scatterplot(self):
        """ Add a new scatter plot to the 'Plots' section."""
        new_plot = {"Type":"xy","Title":"", "XSeries":"[]", "YSeries":"[]"}
        parent = QtGui.QStandardItem("New scatter plot")
        for key in new_plot:
            val = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(val))
            parent.appendRow([child0, child1])
        self.sections["Plots"].appendRow(parent)
        self.update_tab_text()

    def add_timeseries(self):
        """ Add a new time series to the 'Plots' section."""
        new_plot = {"Variables":""}
        parent = QtGui.QStandardItem("New time series")
        for key in new_plot:
            val = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(val))
            parent.appendRow([child0, child1])
        self.sections["Plots"].appendRow(parent)
        self.update_tab_text()

    def add_usel2fluxes(self):
        """ Add UseL2Fluxes to the [Options] section."""
        child0 = QtGui.QStandardItem("UseL2Fluxes")
        child1 = QtGui.QStandardItem("Yes")
        self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_variable(self):
        new_var_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        parent2 = QtGui.QStandardItem("New variable")
        for key3 in new_var_qc:
            parent3 = QtGui.QStandardItem(key3)
            for key in new_var_qc[key3]:
                val = new_var_qc[key3][key]
                child0 = QtGui.QStandardItem(key)
                child1 = QtGui.QStandardItem(str(val))
                parent3.appendRow([child0, child1])
            parent2.appendRow(parent3)
        self.sections["Variables"].appendRow(parent2)
        self.update_tab_text()

    def add_zms(self):
        """ Add zms to the [Options] section."""
        child0 = QtGui.QStandardItem("zms")
        child1 = QtGui.QStandardItem("")
        self.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def browse_alternate_file(self):
        """ Browse for the alternate data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # set the file filter
        file_filter = "*.nc"
        # get the file path from the selected item
        file_path = os.path.split(str(idx.data()))[0]
        file_path = os.path.join(file_path, "")
        # dialog for open file
        new_file = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an alternate data file ...",
                                                     directory=file_path, filter=file_filter)[0]
        # quit if cancel button pressed
        if len(str(new_file)) > 0:
            # update the model
            parent.child(selected_item.row(), 1).setText(new_file)

    def browse_file_path(self):
        """ Browse for the data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder ...",
                                                         file_path, QtWidgets.QFileDialog.ShowDirsOnly)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                          directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                          directory=file_path, filter="*.nc")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the level of the selected item
        level = self.get_level_selected_item()
        if level == 0:
            add_separator = False
            selected_text = str(idx.data())
            self.section_headings = []
            root = self.model.invisibleRootItem()
            for i in range(root.rowCount()):
                self.section_headings.append(str(root.child(i).text()))
            if "Imports" not in self.section_headings and selected_text == "Files":
                self.context_menu.actionAddImportsSection = QtWidgets.QAction(self)
                self.context_menu.actionAddImportsSection.setText("Add Imports section")
                self.context_menu.addAction(self.context_menu.actionAddImportsSection)
                self.context_menu.actionAddImportsSection.triggered.connect(self.add_imports_section)
                add_separator = True
            if "Massman" not in self.section_headings and selected_text == "Files":
                self.context_menu.actionAddMassmanSection = QtWidgets.QAction(self)
                self.context_menu.actionAddMassmanSection.setText("Add Massman section")
                self.context_menu.addAction(self.context_menu.actionAddMassmanSection)
                self.context_menu.actionAddMassmanSection.triggered.connect(self.add_massman_section)
                add_separator = True
            if selected_text == "Files":
                if add_separator:
                    self.context_menu.addSeparator()
                    add_separator = False
                existing_entries = self.get_existing_entries()
                if "file_path" not in existing_entries:
                    self.context_menu.actionAddfile_path = QtWidgets.QAction(self)
                    self.context_menu.actionAddfile_path.setText("Add file_path")
                    self.context_menu.addAction(self.context_menu.actionAddfile_path)
                    self.context_menu.actionAddfile_path.triggered.connect(self.add_file_path)
                if "in_filename" not in existing_entries:
                    self.context_menu.actionAddin_filename = QtWidgets.QAction(self)
                    self.context_menu.actionAddin_filename.setText("Add in_filename")
                    self.context_menu.addAction(self.context_menu.actionAddin_filename)
                    self.context_menu.actionAddin_filename.triggered.connect(self.add_in_filename)
                if "out_filename" not in existing_entries:
                    self.context_menu.actionAddout_filename = QtWidgets.QAction(self)
                    self.context_menu.actionAddout_filename.setText("Add out_filename")
                    self.context_menu.addAction(self.context_menu.actionAddout_filename)
                    self.context_menu.actionAddout_filename.triggered.connect(self.add_out_filename)
                if "plot_path" not in existing_entries:
                    self.context_menu.actionAddplot_path = QtWidgets.QAction(self)
                    self.context_menu.actionAddplot_path.setText("Add plot_path")
                    self.context_menu.addAction(self.context_menu.actionAddplot_path)
                    self.context_menu.actionAddplot_path.triggered.connect(self.add_plot_path)
            elif selected_text == "Imports":
                self.context_menu.actionAddImportsVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddImportsVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddImportsVariable)
                self.context_menu.actionAddImportsVariable.triggered.connect(self.add_imports_variable)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveImportsSection = QtWidgets.QAction(self)
                self.context_menu.actionRemoveImportsSection.setText("Remove section")
                self.context_menu.addAction(self.context_menu.actionRemoveImportsSection)
                self.context_menu.actionRemoveImportsSection.triggered.connect(self.remove_section)
            elif selected_text == "Options":
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                if "zms" not in existing_entries:
                    self.context_menu.actionAddzms = QtWidgets.QAction(self)
                    self.context_menu.actionAddzms.setText("Add zms")
                    self.context_menu.addAction(self.context_menu.actionAddzms)
                    self.context_menu.actionAddzms.triggered.connect(self.add_zms)
                if "UseL2Fluxes" not in existing_entries:
                    self.context_menu.actionAddUseL2Fluxes = QtWidgets.QAction(self)
                    self.context_menu.actionAddUseL2Fluxes.setText("UseL2Fluxes")
                    self.context_menu.addAction(self.context_menu.actionAddUseL2Fluxes)
                    self.context_menu.actionAddUseL2Fluxes.triggered.connect(self.add_usel2fluxes)
                if "2DCoordRotation" not in existing_entries:
                    self.context_menu.actionAdd2DCoordRotation = QtWidgets.QAction(self)
                    self.context_menu.actionAdd2DCoordRotation.setText("2DCoordRotation")
                    self.context_menu.addAction(self.context_menu.actionAdd2DCoordRotation)
                    self.context_menu.actionAdd2DCoordRotation.triggered.connect(self.add_2dcoordrotation)
                if "MassmanCorrection" not in existing_entries:
                    self.context_menu.actionAddMassmanCorrection = QtWidgets.QAction(self)
                    self.context_menu.actionAddMassmanCorrection.setText("MassmanCorrection")
                    self.context_menu.addAction(self.context_menu.actionAddMassmanCorrection)
                    self.context_menu.actionAddMassmanCorrection.triggered.connect(self.add_massmancorrection)
                if "ApplyFcStorage" not in existing_entries:
                    self.context_menu.actionAddApplyFcStorage = QtWidgets.QAction(self)
                    self.context_menu.actionAddApplyFcStorage.setText("ApplyFcStorage")
                    self.context_menu.addAction(self.context_menu.actionAddApplyFcStorage)
                    self.context_menu.actionAddApplyFcStorage.triggered.connect(self.add_applyfcstorage_to_options)
                if "CorrectIndividualFg" not in existing_entries:
                    self.context_menu.actionAddCorrectIndividualFg = QtWidgets.QAction(self)
                    self.context_menu.actionAddCorrectIndividualFg.setText("CorrectIndividualFg")
                    self.context_menu.addAction(self.context_menu.actionAddCorrectIndividualFg)
                    self.context_menu.actionAddCorrectIndividualFg.triggered.connect(self.add_correctindividualfg)
                if "CorrectFgForStorage" not in existing_entries:
                    self.context_menu.actionAddCorrectFgForStorage = QtWidgets.QAction(self)
                    self.context_menu.actionAddCorrectFgForStorage.setText("CorrectFgForStorage")
                    self.context_menu.addAction(self.context_menu.actionAddCorrectFgForStorage)
                    self.context_menu.actionAddCorrectFgForStorage.triggered.connect(self.add_correctfgforstorage)
                #self.context_menu.actionCoordinateFluxGaps = QtWidgets.QAction(self)
                #self.context_menu.actionCoordinateFluxGaps.setText("CoordinateFluxGaps")
                #self.context_menu.addAction(self.context_menu.actionAddCoordinateFluxGaps)
                #self.context_menu.actionAddCoordinateFluxGaps.triggered.connect(self.add_coordinatefluxgaps)
                #self.context_menu.actionCoordinateAhFcGaps = QtWidgets.QAction(self)
                #self.context_menu.actionCoordinateAhFcGaps.setText("CoordinateAhFcGaps")
                #self.context_menu.addAction(self.context_menu.actionAddCoordinateAhFcGaps)
                #self.context_menu.actionAddCoordinateAhFcGaps.triggered.connect(self.add_coordinateahfcgaps)
            elif selected_text == "Massman":
                self.context_menu.actionRemoveMassmanSection = QtWidgets.QAction(self)
                self.context_menu.actionRemoveMassmanSection.setText("Remove section")
                self.context_menu.addAction(self.context_menu.actionRemoveMassmanSection)
                self.context_menu.actionRemoveMassmanSection.triggered.connect(self.remove_section)
            elif selected_text == "Variables":
                self.context_menu.actionAddVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
            elif selected_text == "Plots":
                self.context_menu.actionAddTimeSeries = QtWidgets.QAction(self)
                self.context_menu.actionAddTimeSeries.setText("Add time series")
                self.context_menu.addAction(self.context_menu.actionAddTimeSeries)
                self.context_menu.actionAddTimeSeries.triggered.connect(self.add_timeseries)
                self.context_menu.actionAddScatterPlot = QtWidgets.QAction(self)
                self.context_menu.actionAddScatterPlot.setText("Add scatter plot")
                self.context_menu.addAction(self.context_menu.actionAddScatterPlot)
                self.context_menu.actionAddScatterPlot.triggered.connect(self.add_scatterplot)
        elif level == 1:
            selected_item = idx.model().itemFromIndex(idx)
            parent = selected_item.parent()
            if (str(parent.text()) == "Files") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                # check to see if we have the selected subsection
                if key in ["file_path", "plot_path"]:
                    self.context_menu.actionBrowseFilePath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key == "in_filename":
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key == "out_filename":
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                else:
                    pass
            elif (str(parent.text()) == "Imports"):
                self.context_menu.actionRemoveImportsVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveImportsVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveImportsVariable)
                self.context_menu.actionRemoveImportsVariable.triggered.connect(self.remove_item)
            elif str(parent.text()) == "Options":
                self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove option")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
            elif str(parent.text()) == "Variables":
                selected_text = str(idx.data())
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                # only put a QC check in the context menu if it is not already present
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtWidgets.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                if "ApplyFcStorage" not in existing_entries and selected_text[0:2] == "Fc":
                    self.context_menu.actionAddApplyFcStorage = QtWidgets.QAction(self)
                    self.context_menu.actionAddApplyFcStorage.setText("Add ApplyFcStorage")
                    self.context_menu.addAction(self.context_menu.actionAddApplyFcStorage)
                    self.context_menu.actionAddApplyFcStorage.triggered.connect(self.add_applyfcstorage_to_variable)
                self.context_menu.addSeparator()
                if "MergeSeries" not in existing_entries:
                    self.context_menu.actionAddMergeSeries = QtWidgets.QAction(self)
                    self.context_menu.actionAddMergeSeries.setText("Add MergeSeries")
                    self.context_menu.addAction(self.context_menu.actionAddMergeSeries)
                    self.context_menu.actionAddMergeSeries.triggered.connect(self.add_mergeseries)
                if "AverageSeries" not in existing_entries:
                    self.context_menu.actionAddAverageSeries = QtWidgets.QAction(self)
                    self.context_menu.actionAddAverageSeries.setText("Add AverageSeries")
                    self.context_menu.addAction(self.context_menu.actionAddAverageSeries)
                    self.context_menu.actionAddAverageSeries.triggered.connect(self.add_averageseries)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveVariable)
                self.context_menu.actionRemoveVariable.triggered.connect(self.remove_item)
            elif str(parent.text()) == "Plots":
                #self.context_menu.actionDisablePlot = QtWidgets.QAction(self)
                #self.context_menu.actionDisablePlot.setText("Disable plot")
                #self.context_menu.addAction(self.context_menu.actionDisablePlot)
                #self.context_menu.actionDisablePlot.triggered.connect(self.disable_plot)
                self.context_menu.actionRemovePlot = QtWidgets.QAction(self)
                self.context_menu.actionRemovePlot.setText("Remove plot")
                self.context_menu.addAction(self.context_menu.actionRemovePlot)
                self.context_menu.actionRemovePlot.triggered.connect(self.remove_item)
        elif level == 2:
            add_separator = False
            # we are in a subsection
            selected_item = idx.model().itemFromIndex(idx)
            # get the subsection
            subsection = selected_item.parent()
            # get the section
            section = subsection.parent()
            # check to see what the user whats us to do based on what was selected when the right click happened
            if str(idx.data()) in ["ExcludeDates"]:
                # we are adding a date range to an ExcludeDates QC check
                self.context_menu.actionAddExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                add_separator = True
            if (str(section.text()) == "Imports") and (selected_item.column() == 1):
                # we are browsing for a file name in an Imports section
                key = str(subsection.child(selected_item.row(),0).text())
                if key in ["file_name"]:
                    self.context_menu.actionBrowseAlternateFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseAlternateFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseAlternateFile)
                    self.context_menu.actionBrowseAlternateFile.triggered.connect(self.browse_alternate_file)
                    add_separator = True
            if add_separator:
                self.context_menu.addSeparator()
                add_separator = False
            self.context_menu.actionRemoveQCCheck = QtWidgets.QAction(self)
            self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
            self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
            self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_item)
        elif level == 3:
            if (str(idx.parent().data()) in ["ExcludeDates"] and
                str(idx.data()) != "0"):
                self.context_menu.actionRemoveExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionRemoveExcludeDateRange.setText("Remove date range")
                self.context_menu.addAction(self.context_menu.actionRemoveExcludeDateRange)
                self.context_menu.actionRemoveExcludeDateRange.triggered.connect(self.remove_daterange)

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def correct_legacy_variable_names(self):
        """ Correct some legacy variable names."""
        # change Fn_KZ to Fn_4cmpt
        opt = pfp_utils.get_keyvaluefromcf(self.cfg, ["Variables", "Fn", "MergeSeries"],
                                           "source", default="", mode="quiet")
        if len(opt) != 0:
            if "Fn_KZ" in opt:
                opt = opt.replace("Fn_KZ", "Fn_4cmpt")
                self.cfg["Variables"]["Fn"]["MergeSeries"]["source"] = opt
                self.cfg_changed = True
        return

    def disable_plot(self):
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        selected_item.setForeground(QtGui.QBrush(QtGui.QColor("red")))

    def edit_L3_gui(self):
        """ Edit L3 control file GUI."""
        # get a QTreeView and a standard model
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.view.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.view.setModel(self.model)
        # enable drag and drop
        self.view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 200)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        # create a new control file object
        cfg = ConfigObj(indent_type="    ", list_values=False)
        # set the control file level
        cfg["level"] = "L3"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                # sections with only 1 level
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["Plots", "Imports"]:
                # sections with 2 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3
            elif key1 in ["Variables"]:
                # sections with 3 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        subsubsection = subsection.child(k)
                        key3 = str(subsubsection.text())
                        cfg[key1][key2][key3] = {}
                        for l in range(subsubsection.rowCount()):
                            key4 = str(subsubsection.child(l, 0).text())
                            val4 = str(subsubsection.child(l, 1).text())
                            cfg[key1][key2][key3][key4] = val4
        return cfg

    def get_existing_entries(self):
        """ Get a list of existing entries in the current section."""
        # index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from its index
        selected_item = idx.model().itemFromIndex(idx)
        # build a list of existing QC checks
        existing_entries = []
        if selected_item.hasChildren():
            for i in range(selected_item.rowCount()):
                existing_entries.append(str(selected_item.child(i, 0).text()))
        return existing_entries

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_level_selected_item(self):
        """ Get the level of the selected item in the model."""
        indexes = self.view.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            idx = indexes[0]
            while idx.parent().isValid():
                idx = idx.parent()
                level += 1
        return level

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # correct legacy variable names in the control file
        self.correct_legacy_variable_names()
        # transfer anything in the [General] section to [Options]
        self.transfer_general_to_options()
        # there must be some way to do this recursively
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Files", "Global", "Output", "Options", "Soil", "Massman"]:
                # sections with only 1 level
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    val = self.cfg[key1][key2]
                    val = self.parse_cfg_values(key2, val, ['"', "'", "[", "]"])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Plots", "Imports"]:
                # sections with 2 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    if key1 == "Plots":
                        # handle old-style control files with separate Title key
                        title = self.parse_cfg_plots_title(key1, key2)
                        parent2 = QtGui.QStandardItem(title)
                    else:
                        parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg[key1][key2]:
                        if key3 in ["source"]:
                            continue
                        val = self.cfg[key1][key2][key3]
                        val = self.parse_cfg_plots_value(key3, val)
                        child0 = QtGui.QStandardItem(key3)
                        child1 = QtGui.QStandardItem(val)
                        parent2.appendRow([child0, child1])
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Variables"]:
                # sections with 3 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    if key2 in ["ustar_filtered"]:
                        continue
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg[key1][key2]:
                        if key3 in ["RangeCheck", "DependencyCheck", "DiurnalCheck", "ExcludeDates",
                                    "ApplyFcStorage", "MergeSeries", "AverageSeries"]:
                            parent3 = QtGui.QStandardItem(key3)
                            for key4 in self.cfg[key1][key2][key3]:
                                val = self.cfg[key1][key2][key3][key4]
                                val = self.parse_cfg_variables_value(key3, val)
                                child0 = QtGui.QStandardItem(key4)
                                child1 = QtGui.QStandardItem(val)
                                parent3.appendRow([child0, child1])
                            parent2.appendRow(parent3)
                    if parent2.hasChildren():
                        self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # update the control file contents
        self.cfg = self.get_data_from_model()
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def parse_cfg_plots_title(self, key1, key2):
        """ Parse the [Plots] section for a title."""
        if "Title" in self.cfg[key1][key2]:
            title = self.cfg[key1][key2]["Title"]
            del self.cfg[key1][key2]["Title"]
            self.cfg_changed = True
        else:
            title = key2
        strip_list = ['"', "'"]
        for c in strip_list:
            if c in title:
                self.cfg_changed = True
                title = title.replace(c, "")
        return title

    def parse_cfg_plots_value(self, k, v):
        """ Parse the [Plots] section keys to remove unnecessary characters."""
        if k in ["Variables", "Type", "XSeries", "YSeries"]:
            if ("[" in v) and ("]" in v):
                v = v.replace("[", "").replace("]", "")
                self.cfg_changed = True
        strip_list = [" ", '"', "'"]
        for c in strip_list:
            if c in v:
                if (v != '""') and (v != "''"):
                    self.cfg_changed = True
                v = v.replace(c, "")
        return v

    def parse_cfg_values(self, k, v, strip_list):
        """ Parse key values to remove unnecessary characters."""
        for c in strip_list:
            if c in v:
                if (v != '""') and (v != "''"):
                    self.cfg_changed = True
                v = v.replace(c, "")
        if k in ["file_path", "plot_path"] and "browse" not in v:
            if os.path.join(str(v), "") != v:
                v = os.path.join(str(v), "")
                self.cfg_changed = True
        return v

    def parse_cfg_variables_value(self, k, v):
        """ Parse value from control file to remove unnecessary characters."""
        strip_list = []
        try:
            # check to see if it is a number
            r = float(v)
        except ValueError as e:
            if ("[" in v) and ("]" in v) and ("*" in v):
                # old style of [value]*12
                v = v[v.index("[")+1:v.index("]")]
                self.cfg_changed = True
            elif ("[" in v) and ("]" in v) and ("*" not in v):
                # old style of [1,2,3,4,5,6,7,8,9,10,11,12]
                v = v.replace("[", "").replace("]", "")
                self.cfg_changed = True
        # remove white space and quotes
        if k in ["RangeCheck", "DiurnalCheck", "DependencyCheck",
                 "MergeSeries", "AverageSeries", "ApplyFcStorage"]:
            strip_list = [" ", '"', "'"]
        elif k in ["ExcludeDates", "ExcludeHours", "LowerCheck", "UpperCheck"]:
            # don't remove white space between date and time
            strip_list = ['"', "'"]
        else:
            msg = " QC check " + k + " not recognised"
            logger.warning(msg)
            return v
        for c in strip_list:
            if c in v:
                if (v != '""') and (v != "''"):
                    self.cfg_changed = True
                v = v.replace(c, "")
        return v

    def remove_daterange(self):
        """ Remove a date range from the ustar_threshold section."""
        # remove the date range
        self.remove_item()
        # index of selected item
        idx = self.view.selectedIndexes()[0]
        # item from index
        selected_item = idx.model().itemFromIndex(idx)
        # parent of selected item
        parent = selected_item.parent()
        # renumber the subsections
        for i in range(parent.rowCount()):
            parent.child(i, 0).setText(str(i))

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        self.update_tab_text()

    def remove_section(self):
        """ Remove a section from the view."""
        # loop over selected items in the tree
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the root
        root = self.model.invisibleRootItem()
        # remove the row
        root.removeRow(selected_item.row())
        self.update_tab_text()

    def transfer_general_to_options(self):
        """ Copy any entries in [General] to [Options] then delete [General]."""
        if "General" in self.cfg:
            if "Options" not in self.cfg:
                self.cfg["Options"] = {}
            for item in self.cfg["General"]:
                self.cfg["Options"][item] = self.cfg["General"][item]
            del self.cfg["General"]
        return

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_concatenate(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_concatenate, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)

        self.cfg_changed = False
        self.tabs = main_gui.tabs

        self.edit_concatenate_gui()

    def edit_concatenate_gui(self):
        """ Edit a concatenate control file GUI."""
        # get a QTreeView
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.view.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.view.setModel(self.model)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 200)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Options"]:
                # sections with only 1 level
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    val = self.cfg[key1][key2]
                    val = self.parse_cfg_values(key2, val, ["[","]",'"', "'"])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(str(val))
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Files"]:
                # sections with 2 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for val in self.cfg[key1][key2]:
                        value = self.cfg[key1][key2][val]
                        child0 = QtGui.QStandardItem(val)
                        child1 = QtGui.QStandardItem(str(value))
                        parent2.appendRow([child0, child1])
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = ConfigObj(indent_type="    ", list_values=False)
        cfg["level"] = "concatenate"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Options"]:
                # sections with only 1 level
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["Files"]:
                # sections with 2 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3

        return cfg

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # update the control file contents
        self.cfg = self.get_data_from_model()
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item text
        selected_text = str(idx.data())
        # get the selected item
        selected_item = idx.model().itemFromIndex(idx)
        # get the level of the selected item
        level = self.get_level_selected_item()
        if level == 0:
            # sections with only 1 level
            if selected_text == "Options":
                existing_entries = self.get_existing_entries()
                if "NumberOfDimensions" not in existing_entries:
                    self.context_menu.actionAddNumberOfDimensions = QtWidgets.QAction(self)
                    self.context_menu.actionAddNumberOfDimensions.setText("NumberOfDimensions")
                    self.context_menu.addAction(self.context_menu.actionAddNumberOfDimensions)
                    self.context_menu.actionAddNumberOfDimensions.triggered.connect(self.add_numberofdimensions)
                if "MaxGapInterpolate" not in existing_entries:
                    self.context_menu.actionAddMaxGapInterpolate = QtWidgets.QAction(self)
                    self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                    self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                    self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
                if "FixTimeStepMethod" not in existing_entries:
                    self.context_menu.actionAddFixTimeStepMethod = QtWidgets.QAction(self)
                    self.context_menu.actionAddFixTimeStepMethod.setText("FixTimeStepMethod")
                    self.context_menu.addAction(self.context_menu.actionAddFixTimeStepMethod)
                    self.context_menu.actionAddFixTimeStepMethod.triggered.connect(self.add_fixtimestepmethod)
                if "Truncate" not in existing_entries:
                    self.context_menu.actionAddTruncate = QtWidgets.QAction(self)
                    self.context_menu.actionAddTruncate.setText("Truncate")
                    self.context_menu.addAction(self.context_menu.actionAddTruncate)
                    self.context_menu.actionAddTruncate.triggered.connect(self.add_truncate)
                if "TruncateThreshold" not in existing_entries:
                    self.context_menu.actionAddTruncateThreshold = QtWidgets.QAction(self)
                    self.context_menu.actionAddTruncateThreshold.setText("TruncateThreshold")
                    self.context_menu.addAction(self.context_menu.actionAddTruncateThreshold)
                    self.context_menu.actionAddTruncateThreshold.triggered.connect(self.add_truncatethreshold)
                if "SeriesToCheck" not in existing_entries:
                    self.context_menu.actionAddSeriesToCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddSeriesToCheck.setText("SeriesToCheck")
                    self.context_menu.addAction(self.context_menu.actionAddSeriesToCheck)
                    self.context_menu.actionAddSeriesToCheck.triggered.connect(self.add_seriestocheck)
        elif level == 1:
            parent = selected_item.parent()
            if (str(parent.text()) == "Options") and (selected_item.column() == 0):
                self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove option")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
            elif str(parent.text()) == "Files":
                if selected_text == "In":
                    self.context_menu.actionAddInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionAddInputFile.setText("Add input file")
                    self.context_menu.addAction(self.context_menu.actionAddInputFile)
                    self.context_menu.actionAddInputFile.triggered.connect(self.add_inputfile)
        elif level == 2:
            parent = selected_item.parent()
            section = selected_item.parent().parent()
            if ((str(section.text()) == "Files") and (str(parent.text()) == "In")):
                if (selected_item.column() == 0):
                    self.context_menu.actionRemoveInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionRemoveInputFile.setText("Remove file")
                    self.context_menu.addAction(self.context_menu.actionRemoveInputFile)
                    self.context_menu.actionRemoveInputFile.triggered.connect(self.remove_item)
                elif (selected_item.column() == 1):
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
            elif ((str(section.text()) == "Files") and (str(parent.text()) == "Out")):
                if str(parent.child(selected_item.row(), 0).text()) == "ncFileName":
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
        elif level == 3:
            pass

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def get_section(self, section_name):
        """ Gets a section from a model by matching the section name."""
        model = self.tree.model()
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == str(section_name):
                break
        return section, i

    def get_subsection(self, section, idx):
        """ Gets a subsection from a model by matching the subsection name."""
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(idx.data()):
                break
        return subsection, i

    def get_existing_entries(self):
        """ Get a list of existing entries in the current section."""
        # index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from its index
        selected_item = idx.model().itemFromIndex(idx)
        # build a list of existing QC checks
        existing_entries = []
        if selected_item.hasChildren():
            for i in range(selected_item.rowCount()):
                existing_entries.append(str(selected_item.child(i, 0).text()))
        return existing_entries

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_keyval_by_val_name(self, section, val):
        """ Get the value from a section based on the value name."""
        found = False
        key_child = ""
        val_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 1).text()) == str(val):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found

    def get_level_selected_item(self):
        """ Get the level of the selected item."""
        level = 0
        idx = self.view.selectedIndexes()[0]
        while idx.parent().isValid():
            idx = idx.parent()
            level += 1
        return level

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_inputfile(self):
        """ Add an entry for a new input file."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        subsection = idx.model().itemFromIndex(idx)
        dict_to_add = {str(subsection.rowCount()): "Right click to browse"}
        # add the subsubsection
        self.add_subsection(dict_to_add)

        ## loop over selected items in the tree
        #for idx in self.tree.selectedIndexes():
            ## get the parent section
            #section, i = self.get_section("Files")
            #subsection, j = self.get_subsection(section, idx)
            #child0 = QtGui.QStandardItem(str(subsection.rowCount()))
            #child1 = QtGui.QStandardItem("")
            #subsection.appendRow([child0, child1])

    #def add_option(self, key, val):
        #""" Add an option to the context menu."""
        ## add the option to the [Options] section
        #child0 = QtGui.QStandardItem(key)
        #child1 = QtGui.QStandardItem(val)
        #self.tree.sections["Options"].appendRow([child0, child1])
        #self.update_tab_text()

    def add_numberofdimensions(self):
        """ Add the NumberOfDimensions option to the context menu."""
        dict_to_add = {"NumberOfDimensions": "3"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_maxgapinterpolate(self):
        """ Add the MaxGapInterpolate option to the context menu."""
        # add the option to the [Options] section
        dict_to_add = {"MaxGapInterpolate": "3"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_fixtimestepmethod(self):
        """ Add the FixTimeStepMethod option to the context menu."""
        # add the option to the [Options] section
        dict_to_add = {"FixTimeStepMethod": "round"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_subsection(self, dict_to_add):
        """ Add a subsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        section = idx.model().itemFromIndex(idx)
        for key in dict_to_add:
            val = str(dict_to_add[key])
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            section.appendRow([child0, child1])
        self.update_tab_text()

    def add_truncate(self):
        """ Add the Truncate option to the context menu."""
        # add the option to the [Options] section
        dict_to_add = {"Truncate": "Yes"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_truncatethreshold(self):
        """ Add the TruncateThreshold option to the context menu."""
        # add the option to the [Options] section
        dict_to_add = {"TruncateThreshold": "50"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_seriestocheck(self):
        """ Add the SeriesToCheck option to the context menu."""
        # add the option to the [Options] section
        series = "Ah,CO2,Fa,Fg,Fld,Flu,Fn,Fsd,Fsu,ps,Sws,Ta,Ts,Ws,Wd,Precip"
        dict_to_add = {"SeriesToCheck": series}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                              directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_path = QtCore.QDir.toNativeSeparators(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_path)

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                          directory=file_path, filter="*.nc")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_path = QtCore.QDir.toNativeSeparators(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_path)

    def parse_cfg_values(self, k, v, strip_list):
        """ Parse key values to remove unnecessary characters."""
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def remove_option(self):
        """ Remove an option."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the "Options" section
            section, i = self.get_section("Options")
            # loop over all children in the "Options" section
            subsection, i = self.get_subsection(section, idx)
            # remove the option
            section.removeRow(i)
            self.update_tab_text()

    def remove_inputfile(self):
        """ Remove an input file."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the "Files" section
            section, i = self.get_section("Files")
            subsection, i = self.get_subsection(section, idx)
            subsubsection, i = self.get_subsection(subsection, idx)
            subsection.removeRow(i)
            self.renumber_subsection_keys(subsection)
            self.update_tab_text()

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        self.update_tab_text()

    def renumber_subsection_keys(self, subsection):
        """ Renumber the subsection keys when an item is removed."""
        for i in range(subsection.rowCount()):
            child = subsection.child(i)
            child.setText(str(i))
        return

class edit_cfg_L4(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L4, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)

        self.cfg_changed = False
        self.tabs = main_gui.tabs

        self.edit_l4_gui()

    def edit_l4_gui(self):
        """ Edit an L4 control file GUI."""
        # get a QTreeView
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.view.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.view.setModel(self.model)
        # enable drag and drop
        #self.view.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 210)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Files", "Global", "Options"]:
                # sections with only 1 level
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    val = self.cfg[key1][key2]
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Drivers"]:
                # sections with 4 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                # key2 is the variable name
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    # key3 is the gap filling method
                    for key3 in self.cfg[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        if key3 in ["GapFillFromAlternate", "GapFillFromClimatology"]:
                            # key4 is the alternate variable name
                            for key4 in self.cfg[key1][key2][key3]:
                                parent4 = QtGui.QStandardItem(key4)
                                # key5 is the source of the alternate data
                                for key5 in self.cfg[key1][key2][key3][key4]:
                                    val = self.cfg[key1][key2][key3][key4][key5]
                                    child0 = QtGui.QStandardItem(key5)
                                    child1 = QtGui.QStandardItem(val)
                                    parent4.appendRow([child0, child1])
                                parent3.appendRow(parent4)
                        elif key3 in ["MergeSeries", "RangeCheck", "ExcludeDates"]:
                            for key4 in self.cfg[key1][key2][key3]:
                                val = self.cfg[key1][key2][key3][key4]
                                child0 = QtGui.QStandardItem(key4)
                                child1 = QtGui.QStandardItem(val)
                                parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = ConfigObj(indent_type="    ", list_values=False)
        cfg["level"] = "L4"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files", "Global", "Output", "Options"]:
                # sections with only 1 level
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["Plots"]:
                # sections with 2 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3
            elif key1 in []:
                # sections with 3 levels
                pass
            elif key1 in ["Drivers"]:
                # sections with 4 levels
                for j in range(section.rowCount()):
                    # subsections are variables
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        # subsubsections are GapFillFromAlternate, GapFillFromClimatology and MergeSeries
                        subsubsection = subsection.child(k)
                        key3 = str(subsubsection.text())
                        cfg[key1][key2][key3] = {}
                        if key3 in ["GapFillFromAlternate", "GapFillFromClimatology", "GapFillUsingMDS"]:
                            for l in range(subsubsection.rowCount()):
                                subsubsubsection = subsubsection.child(l)
                                key4 = str(subsubsubsection.text())
                                cfg[key1][key2][key3][key4] = {}
                                for m in range(subsubsubsection.rowCount()):
                                    key5 = str(subsubsubsection.child(m, 0).text())
                                    val5 = str(subsubsubsection.child(m, 1).text())
                                    cfg[key1][key2][key3][key4][key5] = val5
                        elif key3 in ["MergeSeries", "RangeCheck", "DiurnalCheck", "DependencyCheck", "ExcludeDates"]:
                            for l in range(subsubsection.rowCount()):
                                key4 = str(subsubsection.child(l, 0).text())
                                val4 = str(subsubsection.child(l, 1).text())
                                cfg[key1][key2][key3][key4] = val4

        return cfg

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # update the control file contents
        self.cfg = self.get_data_from_model()
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item text
        selected_text = str(idx.data())
        # get the selected item
        selected_item = idx.model().itemFromIndex(idx)
        # get the level of the selected item
        level = self.get_level_selected_item()
        # initialise logical for inserting a separator
        add_separator = False
        if level == 0:
            # sections with only 1 level
            if selected_text == "Files":
                self.context_menu.actionAddFileEntry = QtWidgets.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif selected_text == "Output":
                pass
            elif selected_text == "Options":
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                # only put an option in the context menu if it is not already present
                if "MaxGapInterpolate" not in existing_entries:
                    self.context_menu.actionAddMaxGapInterpolate = QtWidgets.QAction(self)
                    self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                    self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                    self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
                if "InterpolateType" not in existing_entries:
                    self.context_menu.actionAddInterpolateType = QtWidgets.QAction(self)
                    self.context_menu.actionAddInterpolateType.setText("InterpolateType")
                    self.context_menu.addAction(self.context_menu.actionAddInterpolateType)
                    self.context_menu.actionAddInterpolateType.triggered.connect(self.add_interpolatetype)
            elif selected_text in ["Drivers"]:
                self.context_menu.actionAddVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_new_variable)
        elif level == 1:
            # sections with 2 levels
            # get the parent of the selected item
            parent = selected_item.parent()
            if (str(parent.text()) == "Files") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                if key in ["file_path", "plot_path"]:
                    self.context_menu.actionBrowseFilePath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key in ["in_filename"]:
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key in ["out_filename"]:
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                else:
                    self.context_menu.actionBrowseAlternateFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseAlternateFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseAlternateFile)
                    self.context_menu.actionBrowseAlternateFile.triggered.connect(self.browse_alternate_file)
            elif (str(parent.text()) == "Files") and (selected_item.column() == 0):
                key = str(parent.child(selected_item.row(),0).text())
                if key not in ["file_path", "plot_path", "in_filename", "out_filename"]:
                    self.context_menu.actionRemoveItem = QtWidgets.QAction(self)
                    self.context_menu.actionRemoveItem.setText("Remove item")
                    self.context_menu.addAction(self.context_menu.actionRemoveItem)
                    self.context_menu.actionRemoveItem.triggered.connect(self.remove_item)
                else:
                    pass
            elif (str(parent.text()) == "Options"):
                key = str(parent.child(selected_item.row(),0).text())
                if (selected_item.column() == 0):
                    self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                    self.context_menu.actionRemoveOption.setText("Remove option")
                    self.context_menu.addAction(self.context_menu.actionRemoveOption)
                    self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
                elif (selected_item.column() == 1) and (key == "InterpolateType"):
                    if selected_text != "linear":
                        self.context_menu.actionChangeInterpolateType = QtWidgets.QAction(self)
                        self.context_menu.actionChangeInterpolateType.setText("linear")
                        self.context_menu.addAction(self.context_menu.actionChangeInterpolateType)
                        self.context_menu.actionChangeInterpolateType.triggered.connect(lambda:self.change_selected_text("linear"))
                    if selected_text != "Akima":
                        self.context_menu.actionChangeInterpolateType = QtWidgets.QAction(self)
                        self.context_menu.actionChangeInterpolateType.setText("Akima")
                        self.context_menu.addAction(self.context_menu.actionChangeInterpolateType)
                        self.context_menu.actionChangeInterpolateType.triggered.connect(lambda:self.change_selected_text("Akima"))
            elif (str(parent.text()) in ["Drivers"]):
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                # only put a QC check in the context menu if it is not already present
                if "GapFillFromAlternate" not in existing_entries:
                    self.context_menu.actionAddAlternate = QtWidgets.QAction(self)
                    self.context_menu.actionAddAlternate.setText("Add Alternate")
                    self.context_menu.addAction(self.context_menu.actionAddAlternate)
                    self.context_menu.actionAddAlternate.triggered.connect(self.add_alternate)
                    add_separator = True
                if "GapFillUsingMDS" not in existing_entries:
                    self.context_menu.actionAddMDS = QtWidgets.QAction(self)
                    self.context_menu.actionAddMDS.setText("Add MDS")
                    self.context_menu.addAction(self.context_menu.actionAddMDS)
                    self.context_menu.actionAddMDS.triggered.connect(self.add_MDS)
                    add_separator = True
                if "GapFillFromClimatology" not in existing_entries:
                    self.context_menu.actionAddClimatology = QtWidgets.QAction(self)
                    self.context_menu.actionAddClimatology.setText("Add Climatology")
                    self.context_menu.addAction(self.context_menu.actionAddClimatology)
                    self.context_menu.actionAddClimatology.triggered.connect(self.add_climatology)
                    add_separator = True
                if add_separator:
                    add_separator = False
                    self.context_menu.addSeparator()
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                    add_separator = True
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                    add_separator = True
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                    add_separator = True
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtWidgets.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                    add_separator = True
                if add_separator:
                    add_separator = False
                    self.context_menu.addSeparator()
                self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
        elif level == 2:
            # sections with 3 levels
            subsubsection_name = str(idx.data())
            if subsubsection_name in ["RangeCheck", "DependencyCheck", "DiurnalCheck"]:
                self.context_menu.actionRemoveQCCheck = QtWidgets.QAction(self)
                self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
                self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
                self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_item)
            elif subsubsection_name in ["ExcludeDates"]:
                self.context_menu.actionAddExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveQCCheck = QtWidgets.QAction(self)
                self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
                self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
                self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_item)
            elif subsubsection_name in ["GapFillFromAlternate", "GapFillUsingMDS", "GapFillFromClimatology"]:
                if subsubsection_name == "GapFillFromAlternate":
                    self.context_menu.actionAddMoreAlternate = QtWidgets.QAction(self)
                    self.context_menu.actionAddMoreAlternate.setText("Add Alternate")
                    self.context_menu.addAction(self.context_menu.actionAddMoreAlternate)
                    self.context_menu.actionAddMoreAlternate.triggered.connect(self.add_more_alternate)
                self.context_menu.actionRemoveGFMethod = QtWidgets.QAction(self)
                self.context_menu.actionRemoveGFMethod.setText("Remove method")
                self.context_menu.addAction(self.context_menu.actionRemoveGFMethod)
                self.context_menu.actionRemoveGFMethod.triggered.connect(self.remove_item)
        elif level == 3:
            # sections with 4 levels
            # get the parent text
            parent = idx.parent()
            parent_text = str(parent.data())
            if parent_text == "ExcludeDates":
                self.context_menu.actionRemoveExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionRemoveExcludeDateRange.setText("Remove date range")
                self.context_menu.addAction(self.context_menu.actionRemoveExcludeDateRange)
                self.context_menu.actionRemoveExcludeDateRange.triggered.connect(self.remove_daterange)
            elif parent_text == "GapFillFromAlternate":
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                if "fit" not in existing_entries:
                    self.context_menu.actionAddAltFit = QtWidgets.QAction(self)
                    self.context_menu.actionAddAltFit.setText("Add fit")
                    self.context_menu.addAction(self.context_menu.actionAddAltFit)
                    self.context_menu.actionAddAltFit.triggered.connect(self.add_alternate_fit)
                    add_separator = True
                if "lag" not in existing_entries:
                    self.context_menu.actionAddAltLag = QtWidgets.QAction(self)
                    self.context_menu.actionAddAltLag.setText("Add lag")
                    self.context_menu.addAction(self.context_menu.actionAddAltLag)
                    self.context_menu.actionAddAltLag.triggered.connect(self.add_alternate_lag)
                    add_separator = True
                if add_separator:
                    add_separator = False
                    self.context_menu.addSeparator()
                self.context_menu.actionRemoveGFMethodVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveGFMethodVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveGFMethodVariable)
                self.context_menu.actionRemoveGFMethodVariable.triggered.connect(self.remove_item)
        elif level == 4:
            selected_item = idx.model().itemFromIndex(idx)
            selected_text = str(idx.data())
            parent = idx.parent()
            key = parent.child(selected_item.row(), 0)
            key_text = str(key.data())
            if selected_text in ["fit", "lag"]:
                self.context_menu.actionRemoveItem = QtWidgets.QAction(self)
                self.context_menu.actionRemoveItem.setText("Remove item")
                self.context_menu.addAction(self.context_menu.actionRemoveItem)
                self.context_menu.actionRemoveItem.triggered.connect(self.remove_item)
            elif key_text == "fit":
                if selected_text != "ols":
                    self.context_menu.actionOLS = QtWidgets.QAction(self)
                    self.context_menu.actionOLS.setText("OLS")
                    self.context_menu.addAction(self.context_menu.actionOLS)
                    self.context_menu.actionOLS.triggered.connect(lambda:self.change_selected_text("ols"))
                if selected_text != "ols_thru0":
                    self.context_menu.actionOLSThroughOrigin = QtWidgets.QAction(self)
                    self.context_menu.actionOLSThroughOrigin.setText("OLS through origin")
                    self.context_menu.addAction(self.context_menu.actionOLSThroughOrigin)
                    self.context_menu.actionOLSThroughOrigin.triggered.connect(lambda:self.change_selected_text("ols_thru0"))
                if selected_text != "replace":
                    self.context_menu.actionReplace = QtWidgets.QAction(self)
                    self.context_menu.actionReplace.setText("replace")
                    self.context_menu.addAction(self.context_menu.actionReplace)
                    self.context_menu.actionReplace.triggered.connect(lambda:self.change_selected_text("replace"))
                if selected_text != "mrev":
                    self.context_menu.actionMREV = QtWidgets.QAction(self)
                    self.context_menu.actionMREV.setText("mrev")
                    self.context_menu.addAction(self.context_menu.actionMREV)
                    self.context_menu.actionMREV.triggered.connect(lambda:self.change_selected_text("mrev"))
                if selected_text != "rma":
                    self.context_menu.actionRMA = QtWidgets.QAction(self)
                    self.context_menu.actionRMA.setText("rma")
                    self.context_menu.addAction(self.context_menu.actionRMA)
                    self.context_menu.actionRMA.triggered.connect(lambda:self.change_selected_text("rma"))
                if selected_text != "odr":
                    self.context_menu.actionODR = QtWidgets.QAction(self)
                    self.context_menu.actionODR.setText("odr")
                    self.context_menu.addAction(self.context_menu.actionODR)
                    self.context_menu.actionODR.triggered.connect(lambda:self.change_selected_text("odr"))
            elif key_text == "lag":
                if selected_text != "yes":
                    self.context_menu.actionYes = QtWidgets.QAction(self)
                    self.context_menu.actionYes.setText("Yes")
                    self.context_menu.addAction(self.context_menu.actionYes)
                    self.context_menu.actionYes.triggered.connect(lambda:self.change_selected_text("yes"))
                if selected_text != "no":
                    self.context_menu.actionNo = QtWidgets.QAction(self)
                    self.context_menu.actionNo.setText("No")
                    self.context_menu.addAction(self.context_menu.actionNo)
                    self.context_menu.actionNo.triggered.connect(lambda:self.change_selected_text("no"))

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def add_alternate(self):
        """ Add GapFillFromAlternate to a variable."""
        dict_to_add = {"GapFillFromAlternate":{"<var_alt>": {"source": "<alt>"}}}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsubsection(dict_to_add)

    def add_alternate_fit(self):
        """ Add fit to alternate variable."""
        dict_to_add = {"fit":"ols"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_alternate_lag(self):
        """ Add lag to alternate variable."""
        dict_to_add = {"lag":"yes"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_climatology(self):
        """ Add GapFillFromClimatology to a variable."""
        idx = self.view.selectedIndexes()[0]
        var_name = str(idx.data()) + "_cli"
        dict_to_add = {"GapFillFromClimatology": {var_name: {"method":"interpolated daily"}}}
        # add the subsubsection (GapFillFromClimatology)
        self.add_subsubsubsection(dict_to_add)

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        dict_to_add = {"DependencyCheck":{"source":""}}
        # add the subsubsection (DependencyCheck)
        self.add_subsubsection(dict_to_add)

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        dict_to_add = {"DiurnalCheck":{"NumSd":"5"}}
        # add the subsubsection (DiurnalCheck)
        self.add_subsubsection(dict_to_add)

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        dict_to_add = {"ExcludeDates":{"0":"YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM"}}
        # add the subsubsection (ExcludeDates)
        self.add_subsubsection(dict_to_add)

    def add_excludedaterange(self):
        """ Add another date range to the ExcludeDates QC check."""
        # loop over selected items in the tree
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_fileentry(self):
        """ Add a new entry to the [Files] section."""
        dict_to_add = {"New item":""}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_interpolatetype(self):
        """ Add InterpolateType to the [Options] section."""
        dict_to_add = {"InterpolateType": "Akima"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_maxgapinterpolate(self):
        """ Add MaxGapInterpolate to the [Options] section."""
        dict_to_add = {"MaxGapInterpolate": "3"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_MDS(self):
        """ Add GapFillUsingMDS to a variable."""
        idx = self.view.selectedIndexes()[0]
        var_name = str(idx.data()) + "_MDS"
        dict_to_add = {"GapFillUsingMDS":{var_name: {"drivers": "['Fsd','Ta','VPD']",
                                                     "tolerances":"[(20, 50), 2.5, 0.5]"}}}
        # add the subsubsection (GapFillUsingMDS)
        self.add_subsubsubsection(dict_to_add)

    def add_more_alternate(self):
        """ Add another alternate source to a variable."""
        idx = self.view.selectedIndexes()[0]
        var_name = str(idx.parent().data()) + "_<alt>"
        dict_to_add = {var_name: {"source": "<alt>"}}
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(dict_to_add)

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        dict_to_add = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(dict_to_add)

    def add_subsection(self, dict_to_add):
        """ Add a subsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        section = idx.model().itemFromIndex(idx)
        for key in dict_to_add:
            val = str(dict_to_add[key])
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            section.appendRow([child0, child1])
        self.update_tab_text()

    def add_subsubsection(self, dict_to_add):
        """ Add a subsubsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        subsection = idx.model().itemFromIndex(idx)
        for key1 in dict_to_add:
            subsubsection = QtGui.QStandardItem(key1)
            for key2 in dict_to_add[key1]:
                val = str(dict_to_add[key1][key2])
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(val)
                subsubsection.appendRow([child0, child1])
            subsection.appendRow(subsubsection)
        self.update_tab_text()

    def add_subsubsubsection(self, dict_to_add):
        """ Add a subsubsubsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        subsection = idx.model().itemFromIndex(idx)
        for key3 in dict_to_add:
            subsubsection = QtGui.QStandardItem(key3)
            for key4 in dict_to_add[key3]:
                subsubsubsection = QtGui.QStandardItem(key4)
                for val in dict_to_add[key3][key4]:
                    value = dict_to_add[key3][key4][val]
                    child0 = QtGui.QStandardItem(val)
                    child1 = QtGui.QStandardItem(str(value))
                    subsubsubsection.appendRow([child0, child1])
                subsubsection.appendRow(subsubsubsection)
            subsection.appendRow(subsubsection)
        self.update_tab_text()

    def add_new_variable(self):
        """ Add a new variable."""
        gfALT = {"<var>_<alt>": {"source": "<alt>"}}
        gfCLIM = {"<var>_cli": {"method": "interpolated daily"}}
        gfMS = {"source": "<var>,<var>_<alt>,<var>_cli"}
        d2a = {"New variable": {"GapFillFromAlternate": gfALT,
                                "GapFillFromClimatology": gfCLIM,
                                "MergeSeries": gfMS}}
        self.add_variable(d2a)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_variable(self, d2a):
        """ Add a variable."""
        for key2 in d2a:
            parent2 = QtGui.QStandardItem(key2)
            # key3 is the gap filling method
            for key3 in d2a[key2]:
                parent3 = QtGui.QStandardItem(key3)
                if key3 in ["GapFillFromAlternate", "GapFillFromClimatology"]:
                    # key4 is the gap fill variable name
                    for key4 in d2a[key2][key3]:
                        parent4 = QtGui.QStandardItem(key4)
                        # key5 is the source of the alternate data
                        for key5 in d2a[key2][key3][key4]:
                            val = d2a[key2][key3][key4][key5]
                            child0 = QtGui.QStandardItem(key5)
                            child1 = QtGui.QStandardItem(val)
                            parent4.appendRow([child0, child1])
                        parent3.appendRow(parent4)
                elif key3 in ["MergeSeries", "RangeCheck", "ExcludeDates"]:
                    for key4 in d2a[key2][key3]:
                        val = d2a[key2][key3][key4]
                        child0 = QtGui.QStandardItem(key4)
                        child1 = QtGui.QStandardItem(val)
                        parent3.appendRow([child0, child1])
                parent2.appendRow(parent3)
            self.sections["Drivers"].appendRow(parent2)

    def browse_alternate_file(self):
        """ Browse for the alternate data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # set the file filter
        file_filter = "*.nc"
        if str(parent.child(selected_item.row(), 0).text()) in ["climatology"]:
            file_filter = "*.xls"
        # get the file path from the selected item
        file_path = os.path.split(str(idx.data()))[0]
        file_path = os.path.join(file_path, "")
        # dialog for open file
        new_file = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an alternate data file ...",
                                                     directory=file_path, filter=file_filter)[0]
        # quit if cancel button pressed
        if len(str(new_file)) > 0:
            # update the model
            new_file = QtCore.QDir.toNativeSeparators(str(new_file))
            parent.child(selected_item.row(), 1).setText(new_file)

    def browse_file_path(self):
        """ Browse for the data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder",
                                                         file_path, QtWidgets.QFileDialog.ShowDirsOnly)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                          directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                          directory=file_path, filter="*.nc")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def change_selected_text(self, new_text):
        """ Change the selected text."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        selected_item.setText(new_text)

    def get_existing_entries(self):
        """ Get a list of existing entries in the current section."""
        # index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from its index
        selected_item = idx.model().itemFromIndex(idx)
        # build a list of existing QC checks
        existing_entries = []
        if selected_item.hasChildren():
            for i in range(selected_item.rowCount()):
                existing_entries.append(str(selected_item.child(i, 0).text()))
        return existing_entries

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_keyval_by_val_name(self, section, val):
        """ Get the value from a section based on the value name."""
        found = False
        key_child = ""
        val_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 1).text()) == str(val):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_level_selected_item(self):
        """ Get the level of the selected item."""
        level = 0
        idx = self.view.selectedIndexes()[0]
        while idx.parent().isValid():
            idx = idx.parent()
            level += 1
        return level

    def get_subsection_from_index(self, section, idx):
        """ Gets a subsection from a model by matching the subsection name."""
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(idx.data()):
                break
        return subsection, i

    def get_subsection_from_text(self, section, text):
        """ Gets a subsection from a model by matching the subsection name"""
        for i in range(section.rowCount()):
            subsection = section.child(i)
            if str(subsection.text()) == text:
                break
        return subsection, i

    def remove_daterange(self):
        """ Remove a date range from the ustar_threshold section."""
        # remove the date range
        self.remove_item()
        # index of selected item
        idx = self.view.selectedIndexes()[0]
        # item from index
        selected_item = idx.model().itemFromIndex(idx)
        # parent of selected item
        parent = selected_item.parent()
        # renumber the subsections
        for i in range(parent.rowCount()):
            parent.child(i, 0).setText(str(i))

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        self.update_tab_text()

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L5(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L5, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)

        self.cfg_changed = False
        self.altered = []
        self.tabs = main_gui.tabs

        self.edit_l5_gui()

    def edit_l5_gui(self):
        """ Edit an L5 control file GUI."""
        # get a QTreeView
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.view.setAlternatingRowColors(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.view.setModel(self.model)
        # enable drag and drop
        #self.view.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 200)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Files", "Global", "Options", "ustar_threshold"]:
                # sections with only 1 level
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    val = self.cfg[key1][key2]
                    if ((key1 in ["Files"]) and ("browse" not in val)):
                        val = self.parse_cfg_values(key2, val, ["[", "]", "'", '"', " "])
                    elif key1 in ["Global", "Options"]:
                        val = self.parse_cfg_values(key2, val, ["[", "]", "'", '"', " "])
                    elif key1 in ["ustar_threshold"]:
                        val = self.parse_cfg_values(key2, val, ["[", "]", "'", '"'])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif  key1 in ["Imports", "SummaryPlots"]:
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg[key1][key2]:
                        val = self.cfg[key1][key2][key3]
                        val = self.parse_cfg_values(key3, val, ["[", "]", "'", '"', " "])
                        child0 = QtGui.QStandardItem(key3)
                        child1 = QtGui.QStandardItem(val)
                        parent2.appendRow([child0, child1])
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Fluxes", "Variables"]:
                # sections with 4 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                # key2 is the variable name
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    # key3 is the gap filling method
                    for key3 in self.cfg[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        if key3 in ["GapFillUsingSOLO", "GapFillLongSOLO", "GapFillUsingMDS"]:
                            # key4 is the gap fill variable name
                            for key4 in self.cfg[key1][key2][key3]:
                                parent4 = QtGui.QStandardItem(key4)
                                # key5 is the source of the alternate data
                                for key5 in self.cfg[key1][key2][key3][key4]:
                                    val = self.cfg[key1][key2][key3][key4][key5]
                                    val = self.parse_cfg_values(key5, val, ["[", "]", "'", '"', " "])
                                    child0 = QtGui.QStandardItem(key5)
                                    child1 = QtGui.QStandardItem(val)
                                    parent4.appendRow([child0, child1])
                                parent3.appendRow(parent4)
                        elif key3 in ["MergeSeries", "RangeCheck", "ExcludeDates", "DiurnalCheck", "DependencyCheck"]:
                            for key4 in self.cfg[key1][key2][key3]:
                                val = self.cfg[key1][key2][key3][key4]
                                val = self.parse_cfg_variables_value(key3, val)
                                child0 = QtGui.QStandardItem(key4)
                                child1 = QtGui.QStandardItem(val)
                                parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = ConfigObj(indent_type="    ", list_values=False)
        cfg["level"] = "L5"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files", "Global", "Output", "Options", "ustar_threshold"]:
                # sections with only 1 level
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["Imports", "SummaryPlots"]:
                # sections with 2 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3
            elif key1 in []:
                # sections with 3 levels
                pass
            elif key1 in ["Fluxes", "Variables"]:
                # sections with 4 levels
                for j in range(section.rowCount()):
                    # subsections are variables
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        # subsubsections are GapFillUsingSOLO, GapFillUsingMDS and MergeSeries
                        subsubsection = subsection.child(k)
                        key3 = str(subsubsection.text())
                        cfg[key1][key2][key3] = {}
                        if key3 in ["GapFillUsingSOLO", "GapFillLongSOLO", "GapFillUsingMDS"]:
                            for l in range(subsubsection.rowCount()):
                                subsubsubsection = subsubsection.child(l)
                                key4 = str(subsubsubsection.text())
                                cfg[key1][key2][key3][key4] = {}
                                for m in range(subsubsubsection.rowCount()):
                                    key5 = str(subsubsubsection.child(m, 0).text())
                                    val5 = str(subsubsubsection.child(m, 1).text())
                                    cfg[key1][key2][key3][key4][key5] = val5
                        elif key3 in ["MergeSeries", "RangeCheck", "DiurnalCheck", "DependencyCheck", "ExcludeDates"]:
                            for l in range(subsubsection.rowCount()):
                                key4 = str(subsubsection.child(l, 0).text())
                                val4 = str(subsubsection.child(l, 1).text())
                                cfg[key1][key2][key3][key4] = val4

        return cfg

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # update the control file contents
        self.cfg = self.get_data_from_model()
        # update the list of altered series
        self.update_altered_list()
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item text
        selected_text = str(idx.data())
        # get the selected item
        selected_item = idx.model().itemFromIndex(idx)
        # get the level of the selected item
        level = self.get_level_selected_item()
        # initialise logical for inserting a separator
        add_separator = False
        if level == 0:
            # sections with only 1 level
            # get a list of the section headings at the root level
            section_headings = []
            root = self.model.invisibleRootItem()
            for i in range(root.rowCount()):
                section_headings.append(str(root.child(i).text()))
            if "SummaryPlots" not in section_headings:
                self.context_menu.actionAddSummaryPlots = QtWidgets.QAction(self)
                self.context_menu.actionAddSummaryPlots.setText("Add summary plots section")
                self.context_menu.addAction(self.context_menu.actionAddSummaryPlots)
                self.context_menu.actionAddSummaryPlots.triggered.connect(self.add_summary_plots_section)
                add_separator = True
            if "ustar_threshold" not in section_headings:
                self.context_menu.actionAddUstarThreshold = QtWidgets.QAction(self)
                self.context_menu.actionAddUstarThreshold.setText("Add u* threshold section")
                self.context_menu.addAction(self.context_menu.actionAddUstarThreshold)
                self.context_menu.actionAddUstarThreshold.triggered.connect(self.add_ustar_threshold_section)
                add_separator = True
            if "Imports" not in section_headings:
                self.context_menu.actionAddImports = QtWidgets.QAction(self)
                self.context_menu.actionAddImports.setText("Add Imports section")
                self.context_menu.addAction(self.context_menu.actionAddImports)
                self.context_menu.actionAddImports.triggered.connect(self.add_imports_section)
                add_separator = True
            if selected_text == "Files":
                self.context_menu.actionAddFileEntry = QtWidgets.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif selected_text == "Output":
                pass
            elif selected_text == "Options":
                if add_separator:
                    self.context_menu.addSeparator()
                    add_separator = False
                # get a list of existing entries in this section
                existing_entries = self.get_existing_entries()
                # only put an option in the context menu if it is not already present
                if "MaxGapInterpolate" not in existing_entries:
                    self.context_menu.actionAddMaxGapInterpolate = QtWidgets.QAction(self)
                    self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                    self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                    self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
                if "MaxShortGapDays" not in existing_entries:
                    self.context_menu.actionAddMaxShortGapDays = QtWidgets.QAction(self)
                    self.context_menu.actionAddMaxShortGapDays.setText("MaxShortGapDays")
                    self.context_menu.addAction(self.context_menu.actionAddMaxShortGapDays)
                    self.context_menu.actionAddMaxShortGapDays.triggered.connect(self.add_maxshortgapdays)
                if "FilterList" not in existing_entries:
                    self.context_menu.actionAddFilterList = QtWidgets.QAction(self)
                    self.context_menu.actionAddFilterList.setText("FilterList")
                    self.context_menu.addAction(self.context_menu.actionAddFilterList)
                    self.context_menu.actionAddFilterList.triggered.connect(self.add_filterlist)
                if "TurbulenceFilter" not in existing_entries:
                    self.context_menu.actionAddTurbulenceFilter = QtWidgets.QAction(self)
                    self.context_menu.actionAddTurbulenceFilter.setText("TurbulenceFilter")
                    self.context_menu.addAction(self.context_menu.actionAddTurbulenceFilter)
                    self.context_menu.actionAddTurbulenceFilter.triggered.connect(self.add_turbulencefilter)
                if "DayNightFilter" not in existing_entries:
                    self.context_menu.actionAddDayNightFilter = QtWidgets.QAction(self)
                    self.context_menu.actionAddDayNightFilter.setText("DayNightFilter")
                    self.context_menu.addAction(self.context_menu.actionAddDayNightFilter)
                    self.context_menu.actionAddDayNightFilter.triggered.connect(self.add_daynightfilter)
                if "UseFsdsyn_threshold" not in existing_entries:
                    self.context_menu.actionAddUseFsdsyn_threshold = QtWidgets.QAction(self)
                    self.context_menu.actionAddUseFsdsyn_threshold.setText("UseFsdsyn_threshold")
                    self.context_menu.addAction(self.context_menu.actionAddUseFsdsyn_threshold)
                    self.context_menu.actionAddUseFsdsyn_threshold.triggered.connect(self.add_usefsdsynthreshold)
                if "AcceptDayTimes" not in existing_entries:
                    self.context_menu.actionAddAcceptDayTimes = QtWidgets.QAction(self)
                    self.context_menu.actionAddAcceptDayTimes.setText("AcceptDayTimes")
                    self.context_menu.addAction(self.context_menu.actionAddAcceptDayTimes)
                    self.context_menu.actionAddAcceptDayTimes.triggered.connect(self.add_acceptdaytimes)
                if "UseEveningFilter" not in existing_entries:
                    self.context_menu.actionAddUseEveningFilter = QtWidgets.QAction(self)
                    self.context_menu.actionAddUseEveningFilter.setText("UseEveningFilter")
                    self.context_menu.addAction(self.context_menu.actionAddUseEveningFilter)
                    self.context_menu.actionAddUseEveningFilter.triggered.connect(self.add_useeveningfilter)
                if "EveningFilterLength" not in existing_entries:
                    self.context_menu.actionAddEveningFilterLength = QtWidgets.QAction(self)
                    self.context_menu.actionAddEveningFilterLength.setText("EveningFilterLength")
                    self.context_menu.addAction(self.context_menu.actionAddEveningFilterLength)
                    self.context_menu.actionAddEveningFilterLength.triggered.connect(self.add_eveningfilterlength)
                if "Fsd_threshold" not in existing_entries:
                    self.context_menu.actionAddFsd_threshold = QtWidgets.QAction(self)
                    self.context_menu.actionAddFsd_threshold.setText("Fsd_threshold")
                    self.context_menu.addAction(self.context_menu.actionAddFsd_threshold)
                    self.context_menu.actionAddFsd_threshold.triggered.connect(self.add_fsdthreshold)
                if "sa_threshold" not in existing_entries:
                    self.context_menu.actionAddsa_threshold = QtWidgets.QAction(self)
                    self.context_menu.actionAddsa_threshold.setText("sa_threshold")
                    self.context_menu.addAction(self.context_menu.actionAddsa_threshold)
                    self.context_menu.actionAddsa_threshold.triggered.connect(self.add_sathreshold)
                if "TruncateToImports" not in existing_entries:
                    self.context_menu.actionAddTruncateToImports = QtWidgets.QAction(self)
                    self.context_menu.actionAddTruncateToImports.setText("TruncateToImports")
                    self.context_menu.addAction(self.context_menu.actionAddTruncateToImports)
                    self.context_menu.actionAddTruncateToImports.triggered.connect(self.add_truncatetoimports)
            elif selected_text in ["Fluxes", "Variables"]:
                self.context_menu.actionAddVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_new_variable)
            elif selected_text in ["ustar_threshold"]:
                self.context_menu.actionAddUstarThreshold = QtWidgets.QAction(self)
                self.context_menu.actionAddUstarThreshold.setText("Add year")
                self.context_menu.addAction(self.context_menu.actionAddUstarThreshold)
                self.context_menu.actionAddUstarThreshold.triggered.connect(self.add_ustar_threshold_daterange)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveUstarThreshold = QtWidgets.QAction(self)
                self.context_menu.actionRemoveUstarThreshold.setText("Remove section")
                self.context_menu.addAction(self.context_menu.actionRemoveUstarThreshold)
                self.context_menu.actionRemoveUstarThreshold.triggered.connect(self.remove_section)
            elif selected_text in ["Imports"]:
                self.context_menu.actionAddImportsVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddImportsVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddImportsVariable)
                self.context_menu.actionAddImportsVariable.triggered.connect(self.add_imports_variable)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveImportsSection = QtWidgets.QAction(self)
                self.context_menu.actionRemoveImportsSection.setText("Remove section")
                self.context_menu.addAction(self.context_menu.actionRemoveImportsSection)
                self.context_menu.actionRemoveImportsSection.triggered.connect(self.remove_section)
            elif selected_text in ["SummaryPlots"]:
                self.context_menu.actionAddSummaryPlot = QtWidgets.QAction(self)
                self.context_menu.actionAddSummaryPlot.setText("Add summary plot")
                self.context_menu.addAction(self.context_menu.actionAddSummaryPlot)
                self.context_menu.actionAddSummaryPlot.triggered.connect(self.add_summary_plot)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveSummaryPlotSection = QtWidgets.QAction(self)
                self.context_menu.actionRemoveSummaryPlotSection.setText("Remove section")
                self.context_menu.addAction(self.context_menu.actionRemoveSummaryPlotSection)
                self.context_menu.actionRemoveSummaryPlotSection.triggered.connect(self.remove_section)
        elif level == 1:
            # sections with 2 levels
            # get the parent of the selected item
            parent = selected_item.parent()
            if (str(parent.text()) == "Files") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                if key in ["file_path", "plot_path"]:
                    self.context_menu.actionBrowseFilePath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key in ["in_filename"]:
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key in ["out_filename"]:
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                elif key in ["cpd_filename"]:
                    self.context_menu.actionBrowseCPDFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseCPDFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseCPDFile)
                    self.context_menu.actionBrowseCPDFile.triggered.connect(self.browse_cpd_file)
                else:
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
            elif (str(parent.text()) == "Files") and (selected_item.column() == 0):
                key = str(parent.child(selected_item.row(),0).text())
                if key not in ["file_path", "plot_path", "in_filename", "out_filename"]:
                    self.context_menu.actionRemoveItem = QtWidgets.QAction(self)
                    self.context_menu.actionRemoveItem.setText("Remove item")
                    self.context_menu.addAction(self.context_menu.actionRemoveItem)
                    self.context_menu.actionRemoveItem.triggered.connect(self.remove_item)
                else:
                    pass
            elif (str(parent.text()) == "Options"):
                key = str(parent.child(selected_item.row(),0).text())
                if (selected_item.column() == 0):
                    self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                    self.context_menu.actionRemoveOption.setText("Remove option")
                    self.context_menu.addAction(self.context_menu.actionRemoveOption)
                    self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
                elif (selected_item.column() == 1) and (key == "InterpolateType"):
                    if selected_text != "linear":
                        self.context_menu.actionChangeInterpolateType = QtWidgets.QAction(self)
                        self.context_menu.actionChangeInterpolateType.setText("linear")
                        self.context_menu.addAction(self.context_menu.actionChangeInterpolateType)
                        self.context_menu.actionChangeInterpolateType.triggered.connect(lambda:self.change_selected_text("linear"))
                    if selected_text != "Akima":
                        self.context_menu.actionChangeInterpolateType = QtWidgets.QAction(self)
                        self.context_menu.actionChangeInterpolateType.setText("Akima")
                        self.context_menu.addAction(self.context_menu.actionChangeInterpolateType)
                        self.context_menu.actionChangeInterpolateType.triggered.connect(lambda:self.change_selected_text("Akima"))
            elif (str(parent.text()) in ["Fluxes", "Variables"]):
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                # only put a QC check in the context menu if it is not already present
                if "GapFillUsingSOLO" not in existing_entries:
                    self.context_menu.actionAddSOLO = QtWidgets.QAction(self)
                    self.context_menu.actionAddSOLO.setText("Add SOLO")
                    self.context_menu.addAction(self.context_menu.actionAddSOLO)
                    self.context_menu.actionAddSOLO.triggered.connect(self.add_solo)
                    add_separator = True
                if "GapFillLongSOLO" not in existing_entries:
                    self.context_menu.actionAddLongSOLO = QtWidgets.QAction(self)
                    self.context_menu.actionAddLongSOLO.setText("Add SOLO (long gaps)")
                    self.context_menu.addAction(self.context_menu.actionAddLongSOLO)
                    self.context_menu.actionAddLongSOLO.triggered.connect(self.add_solo_long)
                    add_separator = True
                if "GapFillUsingMDS" not in existing_entries:
                    self.context_menu.actionAddMDS = QtWidgets.QAction(self)
                    self.context_menu.actionAddMDS.setText("Add MDS")
                    self.context_menu.addAction(self.context_menu.actionAddMDS)
                    self.context_menu.actionAddMDS.triggered.connect(self.add_MDS)
                    add_separator = True
                if "GapFillFromClimatology" not in existing_entries:
                    self.context_menu.actionAddClimatology = QtWidgets.QAction(self)
                    self.context_menu.actionAddClimatology.setText("Add Climatology")
                    self.context_menu.addAction(self.context_menu.actionAddClimatology)
                    self.context_menu.actionAddClimatology.triggered.connect(self.add_climatology)
                    add_separator = True
                if add_separator:
                    add_separator = False
                    self.context_menu.addSeparator()
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                    add_separator = True
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                    add_separator = True
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtWidgets.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                    add_separator = True
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtWidgets.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                    add_separator = True
                if add_separator:
                    add_separator = False
                    self.context_menu.addSeparator()
                self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
            elif (str(parent.text()) == "ustar_threshold"):
                self.context_menu.actionRemoveDateRange = QtWidgets.QAction(self)
                self.context_menu.actionRemoveDateRange.setText("Remove date range")
                self.context_menu.addAction(self.context_menu.actionRemoveDateRange)
                self.context_menu.actionRemoveDateRange.triggered.connect(self.remove_daterange)
            elif (str(parent.text()) == "Imports"):
                self.context_menu.actionRemoveImportsVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveImportsVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveImportsVariable)
                self.context_menu.actionRemoveImportsVariable.triggered.connect(self.remove_item)
            elif str(parent.text()) == "SummaryPlots":
                self.context_menu.actionRemoveSummaryPlot = QtWidgets.QAction(self)
                self.context_menu.actionRemoveSummaryPlot.setText("Remove summary plot")
                self.context_menu.addAction(self.context_menu.actionRemoveSummaryPlot)
                self.context_menu.actionRemoveSummaryPlot.triggered.connect(self.remove_item)
        elif level == 2:
            # sections with 3 levels
            parent = selected_item.parent()
            grand_parent = selected_item.parent().parent()
            subsubsection_name = str(idx.data())
            if subsubsection_name in ["RangeCheck", "DependencyCheck", "DiurnalCheck"]:
                self.context_menu.actionRemoveQCCheck = QtWidgets.QAction(self)
                self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
                self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
                self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_item)
            elif subsubsection_name in ["ExcludeDates"]:
                self.context_menu.actionAddExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveQCCheck = QtWidgets.QAction(self)
                self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
                self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
                self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_item)
            elif subsubsection_name in ["GapFillUsingSOLO", "GapFillLongSOLO", "GapFillUsingMDS", "GapFillFromClimatology"]:
                self.context_menu.actionRemoveGFMethod = QtWidgets.QAction(self)
                self.context_menu.actionRemoveGFMethod.setText("Remove method")
                self.context_menu.addAction(self.context_menu.actionRemoveGFMethod)
                self.context_menu.actionRemoveGFMethod.triggered.connect(self.remove_GFMethod)
            if str(grand_parent.text() == "Imports"):
                key = str(parent.child(selected_item.row(),0).text())
                if (key == "file_name") and (selected_item.column() == 1):
                    self.context_menu.actionBrowseImportsFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseImportsFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseImportsFile)
                    self.context_menu.actionBrowseImportsFile.triggered.connect(self.browse_imports_file)
        elif level == 3:
            existing_entries = self.get_existing_entries()
            # sections with 4 levels
            # get the parent text
            parent_text = str(idx.parent().data())
            if parent_text == "ExcludeDates":
                self.context_menu.actionRemoveExcludeDateRange = QtWidgets.QAction(self)
                self.context_menu.actionRemoveExcludeDateRange.setText("Remove date range")
                self.context_menu.addAction(self.context_menu.actionRemoveExcludeDateRange)
                self.context_menu.actionRemoveExcludeDateRange.triggered.connect(self.remove_daterange)
            elif parent_text == "GapFillUsingSOLO":
                # get a list of existing entries
                existing_entries = self.get_existing_entries()
                if "solo_settings" not in existing_entries:
                    self.context_menu.actionAddSOLOSettings = QtWidgets.QAction(self)
                    self.context_menu.actionAddSOLOSettings.setText("Add SOLO settings")
                    self.context_menu.addAction(self.context_menu.actionAddSOLOSettings)
                    self.context_menu.actionAddSOLOSettings.triggered.connect(self.add_solo_settings)
                    add_separator = True
                if add_separator:
                    add_separator = False
                    self.context_menu.addSeparator()
                self.context_menu.actionRemoveGFMethodVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveGFMethodVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveGFMethodVariable)
                self.context_menu.actionRemoveGFMethodVariable.triggered.connect(self.remove_item)
        elif level == 4:
            selected_text = str(idx.data())
            if selected_text in ["solo_settings"]:
                self.context_menu.actionRemoveSOLOSettings = QtWidgets.QAction(self)
                self.context_menu.actionRemoveSOLOSettings.setText("Remove item")
                self.context_menu.addAction(self.context_menu.actionRemoveSOLOSettings)
                self.context_menu.actionRemoveSOLOSettings.triggered.connect(self.remove_item)

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def add_solo(self):
        """ Add GapFillUsingSOLO to a variable."""
        idx = self.view.selectedIndexes()[0]
        var_name = str(idx.data()) + "_SOLO"
        dict_to_add = {"GapFillUsingSOLO":{var_name: {"drivers": "Fn,Fg,q,VPD,Ta,Ts"}}}
        # add the subsubsection (GapFillUsingSOLO)
        self.add_subsubsubsection(dict_to_add)
        # update the Merge section
        selected_item =idx.model().itemFromIndex(idx)
        for i in range(selected_item.rowCount()):
            if str(selected_item.child(i, 0).text()) == "MergeSeries":
                sources = str(selected_item.child(i).child(0, 1).text())
                sources = sources + "," + var_name
                selected_item.child(i).child(0,1).setText(sources)

    def add_solo_long(self):
        """ Add GapFillLongSOLO to a variable."""
        idx = self.view.selectedIndexes()[0]
        var_name = str(idx.data()) + "_LONG"
        dict_to_add = {"GapFillLongSOLO":{var_name: {"drivers": "Fn,Fg,q,VPD,Ta,Ts,EVI"}}}
        # add the subsubsection (GapFillUsingSOLO)
        self.add_subsubsubsection(dict_to_add)
        # update the Merge section
        selected_item =idx.model().itemFromIndex(idx)
        for i in range(selected_item.rowCount()):
            if str(selected_item.child(i, 0).text()) == "MergeSeries":
                sources = str(selected_item.child(i).child(0, 1).text())
                sources = sources + "," + var_name
                selected_item.child(i).child(0,1).setText(sources)

    def add_solo_settings(self):
        """ Add solo_settings to a variable."""
        dict_to_add = {"solo_settings":"5,500,5,0.001,500"}
        # add the subsubsection (GapFillFromAlternate)
        self.add_subsection(dict_to_add)

    def add_climatology(self):
        """ Add GapFillFromClimatology to a variable."""
        idx = self.view.selectedIndexes()[0]
        var_name = str(idx.data()) + "_cli"
        dict_to_add = {"GapFillFromClimatology": {var_name: {"method":"interpolated daily"}}}
        # add the subsubsection (GapFillFromClimatology)
        self.add_subsubsubsection(dict_to_add)
        # update the Merge section
        selected_item =idx.model().itemFromIndex(idx)
        for i in range(selected_item.rowCount()):
            if str(selected_item.child(i, 0).text()) == "MergeSeries":
                sources = str(selected_item.child(i).child(0, 1).text())
                sources = sources + "," + var_name
                selected_item.child(i).child(0,1).setText(sources)

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        dict_to_add = {"DependencyCheck":{"source":""}}
        # add the subsubsection (DependencyCheck)
        self.add_subsubsection(dict_to_add)
        # update the list of altered series
        self.update_altered_list()

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        dict_to_add = {"DiurnalCheck":{"NumSd":"5"}}
        # add the subsubsection (DiurnalCheck)
        self.add_subsubsection(dict_to_add)
        # update the list of altered series
        self.update_altered_list()

    def add_excludedaterange(self):
        """ Add another date range to the ExcludeDates QC check."""
        # loop over selected items in the tree
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        dict_to_add = {"ExcludeDates":{"0":"YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM"}}
        # add the subsubsection (ExcludeDates)
        self.add_subsubsection(dict_to_add)
        # update the list of altered series
        self.update_altered_list()

    def add_fileentry(self):
        """ Add a new entry to the [Files] section."""
        dict_to_add = {"New item":""}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_imports_section(self):
        """ Add an Imports section."""
        self.sections["Imports"] = QtGui.QStandardItem("Imports")
        self.add_imports_variable()
        self.model.appendRow(self.sections["Imports"])
        self.update_tab_text()

    def add_imports_variable(self):
        """ Add a new variable to the 'Imports' section."""
        new_import = {"source": "", "file_name": "Right click to browse",
                      "var_name": ""}
        parent = QtGui.QStandardItem("New variable")
        for key in new_import:
            value = new_import[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(value))
            parent.appendRow([child0, child1])
        self.sections["Imports"].appendRow(parent)
        self.update_tab_text()

    def add_interpolatetype(self):
        """ Add InterpolateType to the [Options] section."""
        dict_to_add = {"InterpolateType": "Akima"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_include_qc(self):
        """ Add include_qc to a variable."""
        idx = self.tree.selectedIndexes()[0]
        # get the parent and sub section text
        subsubsubsection_text = str(idx.data())
        subsubsection_text = str(idx.parent().data())
        subsection_text = str(idx.parent().parent().data())
        section_text = str(idx.parent().parent().parent().data())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
        subsubsubsection, l = self.get_subsection_from_text(subsubsection, subsubsubsection_text)
        # add the subsubsection
        child0 = QtGui.QStandardItem("include_qc")
        child1 = QtGui.QStandardItem("Yes")
        subsubsubsection.appendRow([child0, child1])
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_maxgapinterpolate(self):
        """ Add MaxGapInterpolate to the [Options] section."""
        dict_to_add = {"MaxGapInterpolate": "3"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_maxshortgapdays(self):
        """ Add MaxShortGapDays to the [Options] section."""
        dict_to_add = {"MaxShortGapDays": "30"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_filterlist(self):
        """ Add FilterList to the [Options] section."""
        dict_to_add = {"FilterList": "Fc"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_turbulencefilter(self):
        """ Add TurbulenceFilter to the [Options] section."""
        dict_to_add = {"TurbulenceFilter": "ustar"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_daynightfilter(self):
        """ Add DayNightFilter to the [Options] section."""
        dict_to_add = {"DayNightFilter": "Fsd"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_usefsdsynthreshold(self):
        """ Add UseFsdsyn_threshold to the [Options] section."""
        dict_to_add = {"UseFsdsyn_threshold": "No"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_acceptdaytimes(self):
        """ Add AcceptDayTimes to the [Options] section."""
        dict_to_add = {"AcceptDayTimes": "Yes"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_useeveningfilter(self):
        """ Add UseEveningFilter to the [Options] section."""
        dict_to_add = {"UseEveningFilter": "No"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_eveningfilterlength(self):
        """ Add EveningFilterLength to the [Options] section."""
        dict_to_add = {"EveningFilterLength": "0"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_fsdthreshold(self):
        """ Add Fsd_threshold to the [Options] section."""
        dict_to_add = {"Fsd_threshold": "10"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_sathreshold(self):
        """ Add sa_threshold to the [Options] section."""
        dict_to_add = {"sa_threshold": "-5"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_summary_plot(self):
        """ Add a summary plot to the summary plots section."""
        new_plot = {"Variables":""}
        parent = QtGui.QStandardItem("New summary plot")
        for key in new_plot:
            val = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(val))
            parent.appendRow([child0, child1])
        self.sections["SummaryPlots"].appendRow(parent)
        self.update_tab_text()

    def add_summary_plots_section(self):
        """ Add a summary plots section."""
        dict_to_add = {"SOLO": {"Variables": "ustar_SOLO,Fh_SOLO,Fe_SOLO,Fc_SOLO"}}
        self.sections["SummaryPlots"] = QtGui.QStandardItem("SummaryPlots")
        for key2 in dict_to_add:
            subsection = QtGui.QStandardItem(key2)
            for key3 in dict_to_add[key2]:
                child0 = QtGui.QStandardItem(key3)
                child1 = QtGui.QStandardItem(dict_to_add[key2][key3])
                subsection.appendRow([child0, child1])
            self.sections["SummaryPlots"].appendRow(subsection)
        self.model.appendRow(self.sections["SummaryPlots"])
        self.update_tab_text()

    def add_truncatetoimports(self):
        """ Add TruncateToImports to the [Options] section."""
        dict_to_add = {"TruncateToImports": "Yes"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_ustar_threshold_section(self):
        """ Add a ustar threshold section."""
        self.sections["ustar_threshold"] = QtGui.QStandardItem("ustar_threshold")
        child0 = QtGui.QStandardItem("0")
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM, <ustar_threshold>")
        self.sections["ustar_threshold"].appendRow([child0, child1])
        self.model.appendRow(self.sections["ustar_threshold"])
        self.update_tab_text()

    def add_ustar_threshold_daterange(self):
        """ Add a year to the [ustar_threshold] section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the children
        child0 = QtGui.QStandardItem(str(selected_item.rowCount()))
        child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM, <ustar_threshold>")
        # add them
        selected_item.appendRow([child0, child1])
        self.update_tab_text()

    def add_MDS(self):
        """ Add GapFillUsingMDS to a variable."""
        idx = self.view.selectedIndexes()[0]
        var_name = str(idx.data()) + "_MDS"
        dict_to_add = {"GapFillUsingMDS":{var_name: {"drivers": "Fsd,Ta,VPD",
                                                     "tolerances":"(20, 50),2.5,0.5"}}}
        # add the subsubsection (GapFillUsingMDS)
        self.add_subsubsubsection(dict_to_add)
        # update the Merge section
        selected_item =idx.model().itemFromIndex(idx)
        for i in range(selected_item.rowCount()):
            if str(selected_item.child(i, 0).text()) == "MergeSeries":
                sources = str(selected_item.child(i).child(0, 1).text())
                sources = sources + "," + var_name
                selected_item.child(i).child(0,1).setText(sources)

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        dict_to_add = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(dict_to_add)
        # update the list of altered series
        self.update_altered_list()

    def add_subsection(self, dict_to_add):
        """ Add a subsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        section = idx.model().itemFromIndex(idx)
        for key in dict_to_add:
            val = str(dict_to_add[key])
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            section.appendRow([child0, child1])
        self.update_tab_text()

    def add_subsubsection(self, dict_to_add):
        """ Add a subsubsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        subsection = idx.model().itemFromIndex(idx)
        for key1 in dict_to_add:
            subsubsection = QtGui.QStandardItem(key1)
            for key2 in dict_to_add[key1]:
                val = str(dict_to_add[key1][key2])
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(val)
                subsubsection.appendRow([child0, child1])
            subsection.appendRow(subsubsection)
        self.update_tab_text()

    def add_subsubsubsection(self, dict_to_add):
        """ Add a subsubsubsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        subsection = idx.model().itemFromIndex(idx)
        for key3 in dict_to_add:
            subsubsection = QtGui.QStandardItem(key3)
            for key4 in dict_to_add[key3]:
                subsubsubsection = QtGui.QStandardItem(key4)
                for val in dict_to_add[key3][key4]:
                    value = dict_to_add[key3][key4][val]
                    child0 = QtGui.QStandardItem(val)
                    child1 = QtGui.QStandardItem(str(value))
                    subsubsubsection.appendRow([child0, child1])
                subsubsection.appendRow(subsubsubsection)
            subsection.appendRow(subsubsection)
        self.update_tab_text()

    def add_new_variable(self):
        """ Add a new variable."""
        gfSOLO = {"<var>_SOLO": {"drivers": ""}}
        gfMDS = {"<var>_MDS": {"drivers": "Fsd,Ta,VPD", "tolerances": "(20, 50), 2.5, 0.5"}}
        gfCLIM = {"<var>_cli": {"method": "interpolated daily"}}
        gfMS = {"source": "<var>,<var>_SOLO,<var>_MDS,<var>_cli"}
        d2a = {"New variable": {"GapFillUsingSOLO": gfSOLO,
                                "GapFillUsingMDS": gfMDS,
                                "GapFillFromClimatology": gfCLIM,
                                "MergeSeries": gfMS}}
        self.add_variable(d2a)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_variable(self, d2a):
        """ Add a variable."""
        for key2 in d2a:
            parent2 = QtGui.QStandardItem(key2)
            # key3 is the gap filling method
            for key3 in d2a[key2]:
                parent3 = QtGui.QStandardItem(key3)
                if key3 in ["GapFillUsingSOLO", "GapFillUsingMDS", "GapFillFromClimatology"]:
                    # key4 is the gap fill variable name
                    for key4 in d2a[key2][key3]:
                        parent4 = QtGui.QStandardItem(key4)
                        # key5 is the source of the alternate data
                        for key5 in d2a[key2][key3][key4]:
                            val = d2a[key2][key3][key4][key5]
                            child0 = QtGui.QStandardItem(key5)
                            child1 = QtGui.QStandardItem(val)
                            parent4.appendRow([child0, child1])
                        parent3.appendRow(parent4)
                elif key3 in ["MergeSeries", "RangeCheck", "ExcludeDates"]:
                    for key4 in d2a[key2][key3]:
                        val = d2a[key2][key3][key4]
                        child0 = QtGui.QStandardItem(key4)
                        child1 = QtGui.QStandardItem(val)
                        parent3.appendRow([child0, child1])
                parent2.appendRow(parent3)
            self.sections["Fluxes"].appendRow(parent2)

    def browse_cpd_file(self):
        """ Browse for the CPD results file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # set the file filter
        file_filter = "*.xls"
        # get the file path from the selected item
        file_path = os.path.split(str(idx.data()))[0]
        file_path = os.path.join(file_path,"")
        # dialog for open file
        file_path = os.path.join(file_path, "")
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose a CPD results file ...",
                                                          directory=file_path, filter=file_filter)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_path = QtCore.QDir.toNativeSeparators(str(new_file_path))
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_file_path(self):
        """ Browse for the data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder",
                                                             file_path, QtWidgets.QFileDialog.ShowDirsOnly)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)

    def browse_imports_file(self):
        """ Browse for the imports file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # set the file filter
        file_filter = "*.nc"
        # get the file path from the selected item
        file_path = os.path.split(str(idx.data()))[0]
        file_path = os.path.join(file_path,"")
        # dialog for open file
        new_file = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an Imports file ...",
                                                     directory=file_path, filter=file_filter)[0]
        # update the model
        if len(str(new_file)) > 0:
            new_file = QtCore.QDir.toNativeSeparators(str(new_file))
            parent.child(selected_item.row(), 1).setText(new_file)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                              directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                              directory=file_path, filter="*.nc")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def change_selected_text(self, new_text):
        """ Change the selected text."""
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        selected_item.setText(new_text)

    def get_existing_entries(self):
        """ Get a list of existing entries in the current section."""
        # index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from its index
        selected_item = idx.model().itemFromIndex(idx)
        # build a list of existing QC checks
        existing_entries = []
        if selected_item.hasChildren():
            for i in range(selected_item.rowCount()):
                existing_entries.append(str(selected_item.child(i, 0).text()))
        return existing_entries

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_level_selected_item(self):
        """ Get the level of the selected item."""
        model = self.model
        indexes = self.view.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        return level

    def parse_cfg_values(self, k, v, strip_list):
        """ Parse key values to remove unnecessary characters."""
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def parse_cfg_variables_value(self, k, v):
        """ Parse value from control file to remove unnecessary characters."""
        try:
            # check to see if it is a number
            r = float(v)
        except ValueError as e:
            if ("[" in v) and ("]" in v) and ("*" in v):
                # old style of [value]*12
                v = v[v.index("[")+1:v.index("]")]
                self.cfg_changed = True
            elif ("[" in v) and ("]" in v) and ("*" not in v):
                # old style of [1,2,3,4,5,6,7,8,9,10,11,12]
                v = v.replace("[", "").replace("]", "")
                self.cfg_changed = True
        # remove white space and quotes
        if k in ["RangeCheck", "DiurnalCheck", "DependencyCheck",
                 "MergeSeries", "AverageSeries"]:
            strip_list = [" ", '"', "'"]
        elif k in ["ExcludeDates", "ExcludeHours"]:
            # don't remove white space between date and time
            strip_list = ['"', "'"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def remove_daterange(self):
        """ Remove a date range from the ustar_threshold section."""
        # remove the date range
        self.remove_item()
        # index of selected item
        idx = self.view.selectedIndexes()[0]
        # item from index
        selected_item = idx.model().itemFromIndex(idx)
        # parent of selected item
        parent = selected_item.parent()
        # renumber the subsections
        for i in range(parent.rowCount()):
            parent.child(i, 0).setText(str(i))

    def remove_GFMethod(self):
        """ Remove a gap filling method from a variable."""
        # get the currently selected item
        idx = self.view.selectedIndexes()[0]
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent
        parent = selected_item.parent()
        # get the variable name
        var_name = str(selected_item.child(0).text())
        # find the MergeSeries entry
        for i in range(parent.rowCount()):
            if str(parent.child(i, 0).text()) == "MergeSeries":
                # get the "Sources" value
                sources = str(parent.child(i).child(0, 1).text())
                # remove the variable name from the Sources value
                if var_name in sources:
                    sources = sources.replace(var_name, "")
                    # remove double commas
                    sources = sources.replace(",,",",")
                    # remove leading or trailing commas
                    if sources[0] == ",":
                        sources = sources[1:]
                    if sources[-1] == ",":
                        sources = sources[:-1]
                    # update the MergeSeries Sources value
                    parent.child(i).child(0, 1).setText(sources)
        self.remove_item()

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        # update the list of altered series
        self.update_altered_list()
        # update the tab text
        self.update_tab_text()

    def remove_section(self):
        """ Remove a section from the view."""
        # loop over selected items in the tree
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the root
        root = self.model.invisibleRootItem()
        # remove the row
        root.removeRow(selected_item.row())
        self.update_tab_text()

    def update_altered_list(self):
        """ Update the list of entries in the control file that have been altered."""
        idx = self.view.selectedIndexes()[0]
        level = self.get_level_selected_item()
        if level == 1 and str(idx.parent().data()) == "Fluxes":
            parent_text = str(idx.data())
            if parent_text not in self.altered:
                self.altered.append(parent_text)
        elif level == 2 and str(idx.parent().parent().data()) == "Fluxes":
            parent_text = str(idx.parent().data())
            if parent_text not in self.altered:
                self.altered.append(parent_text)
        elif level == 3 and str(idx.parent().parent().parent().data()) == "Fluxes":
            parent_text = str(idx.parent().parent().data())
            if parent_text not in self.altered:
                self.altered.append(parent_text)
        elif level == 4 and str(idx.parent().parent().parent().parent().data()) == "Fluxes":
            parent_text = str(idx.parent().parent().parent().data())
            if parent_text not in self.altered:
                self.altered.append(parent_text)
        return

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L6(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L6, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)

        self.cfg_changed = False
        self.tabs = main_gui.tabs

        self.edit_l6_gui()

    def edit_l6_gui(self):
        """ Edit an L6 control file GUI."""
        # get a QTreeView
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.view.setAlternatingRowColors(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.view.setModel(self.model)
        # enable drag and drop
        #self.view.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 200)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Files", "Global"]:
                # sections with only 1 level
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    val = self.cfg[key1][key2]
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif key1 in ["NetEcosystemExchange", "GrossPrimaryProductivity"]:
                # sections with 2 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg[key1][key2]:
                        val = self.cfg[key1][key2][key3]
                        child0 = QtGui.QStandardItem(key3)
                        child1 = QtGui.QStandardItem(val)
                        parent2.appendRow([child0, child1])
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])
            elif key1 in ["EcosystemRespiration"]:
                # sections with 4 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        if key3 in ["ERUsingSOLO", "ERUsingFFNET", "ERUsingLloydTaylor", "ERUsingLasslop"]:
                            for key4 in self.cfg[key1][key2][key3]:
                                parent4 = QtGui.QStandardItem(key4)
                                for key5 in self.cfg[key1][key2][key3][key4]:
                                    val = self.cfg[key1][key2][key3][key4][key5]
                                    child0 = QtGui.QStandardItem(key5)
                                    child1 = QtGui.QStandardItem(val)
                                    parent4.appendRow([child0, child1])
                                parent3.appendRow(parent4)
                        elif key3 in ["MergeSeries"]:
                            for key4 in self.cfg[key1][key2][key3]:
                                val = self.cfg[key1][key2][key3][key4]
                                child0 = QtGui.QStandardItem(key4)
                                child1 = QtGui.QStandardItem(val)
                                parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = ConfigObj(indent_type="    ", list_values=False)
        cfg["level"] = "L6"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files", "Global", "Output", "Options"]:
                # sections with only 1 level
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["NetEcosystemExchange", "GrossPrimaryProductivity"]:
                # sections with 2 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3
            elif key1 in ["EcosystemRespiration"]:
                # sections with 4 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        subsubsection = subsection.child(k)
                        key3 = str(subsubsection.text())
                        cfg[key1][key2][key3] = {}
                        if key3 in ["ERUsingSOLO", "ERUsingFFNET", "ERUsingLloydTaylor", "ERUsingLasslop"]:
                            for l in range(subsubsection.rowCount()):
                                subsubsubsection = subsubsection.child(l)
                                key4 = str(subsubsubsection.text())
                                cfg[key1][key2][key3][key4] = {}
                                for m in range(subsubsubsection.rowCount()):
                                    key5 = str(subsubsubsection.child(m, 0).text())
                                    val5 = str(subsubsubsection.child(m, 1).text())
                                    cfg[key1][key2][key3][key4][key5] = val5
                        elif key3 in ["MergeSeries"]:
                            for l in range(subsubsection.rowCount()):
                                key4 = str(subsubsection.child(l, 0).text())
                                val4 = str(subsubsection.child(l, 1).text())
                                cfg[key1][key2][key3][key4] = val4

        return cfg

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item text
        selected_text = str(idx.data())
        # get the selected item
        selected_item = idx.model().itemFromIndex(idx)
        # get the level of the selected item
        level = self.get_level_selected_item()
        # initialise logical for inserting a separator
        add_separator = False
        if level == 0:
            # sections with only 1 level
            if selected_text == "Files":
                self.context_menu.actionAddFileEntry = QtWidgets.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif selected_text == "Output":
                pass
            elif selected_text == "Options":
                # get a list of existing entries in this section
                existing_entries = self.get_existing_entries()
                # only put a QC check in the context menu if it is not already present
                if "MaxGapInterpolate" not in existing_entries:
                    self.context_menu.actionAddMaxGapInterpolate = QtWidgets.QAction(self)
                    self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                    self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                    self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
            elif selected_text == "Global":
                self.context_menu.actionAddGlobalAttribute = QtWidgets.QAction(self)
                self.context_menu.actionAddGlobalAttribute.setText("Add global attribute")
                self.context_menu.addAction(self.context_menu.actionAddGlobalAttribute)
                self.context_menu.actionAddGlobalAttribute.triggered.connect(self.add_global_attribute)
            elif selected_text in ["EcosystemRespiration"]:
                pass
                #self.context_menu.actionAddVariable = QtWidgets.QAction(self)
                #self.context_menu.actionAddVariable.setText("Add variable")
                #self.context_menu.addAction(self.context_menu.actionAddVariable)
                #self.context_menu.actionAddVariable.triggered.connect(self.add_er_variable)
            elif selected_text in ["NetEcosystemExchange"]:
                pass
            elif selected_text in ["GrossPrimaryProductivity"]:
                pass
        elif level == 1:
            # sections with 2 levels
            # get the parent of the selected item
            parent = selected_item.parent()
            if (str(parent.text()) == "Files") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                if key in ["file_path", "plot_path"]:
                    self.context_menu.actionBrowseFilePath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key in ["in_filename"]:
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key in ["out_filename"]:
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
            elif (str(parent.text()) == "Global") and (selected_item.column() == 0):
                self.context_menu.actionRemoveGlobalAttribute = QtWidgets.QAction(self)
                self.context_menu.actionRemoveGlobalAttribute.setText("Remove attribute")
                self.context_menu.addAction(self.context_menu.actionRemoveGlobalAttribute)
                self.context_menu.actionRemoveGlobalAttribute.triggered.connect(self.remove_item)
            elif (str(parent.text()) == "NetEcosystemExchange") and (selected_item.column() == 0):
                self.context_menu.actionRemoveNEEVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveNEEVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveNEEVariable)
                self.context_menu.actionRemoveNEEVariable.triggered.connect(self.remove_item)
            elif (str(parent.text()) == "GrossPrimaryProductivity") and (selected_item.column() == 0):
                self.context_menu.actionRemoveGPPVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveGPPVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveGPPVariable)
                self.context_menu.actionRemoveGPPVariable.triggered.connect(self.remove_item)
            elif (str(parent.text()) == "EcosystemRespiration") and (selected_item.column() == 0):
                self.context_menu.actionRemoveERVariable = QtWidgets.QAction(self)
                self.context_menu.actionRemoveERVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveERVariable)
                self.context_menu.actionRemoveERVariable.triggered.connect(self.remove_item)
        elif level == 2:
            pass

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # update the control file contents
        self.cfg = self.get_data_from_model()
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_er_variable(self):
        """ Add a variable to the [ER] section."""
        dict_to_add = {"ERUsingSOLO":{"ER_SOLO_all": {"drivers": "Ta,Ts,Sws",
                                                      "target": "ER",
                                                      "output": "ER_SOLO_all"}}}
        subsection = QtGui.QStandardItem("ER_SOLO")
        self.add_subsubsubsection(subsection, dict_to_add)
        dict_to_add = {"MergeSeries": {"source": "ER,ER_SOLO_all"}}
        self.add_subsubsection(subsection, dict_to_add)
        self.tree.sections["EcosystemRespiration"].appendRow(subsection)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_fileentry(self):
        """ Add a new entry to the [Files] section."""
        dict_to_add = {"New item":""}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_global_attribute(self):
        """ Add a new global attribute to the [Global] section."""
        dict_to_add = {"New attribute":""}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_maxgapinterpolate(self):
        """ Add MaxGapInterpolate to the [Options] section."""
        dict_to_add = {"MaxGapInterpolate":"3"}
        # add the subsection
        self.add_subsection(dict_to_add)

    def add_subsection(self, dict_to_add):
        """ Add a subsection to the model."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        section = idx.model().itemFromIndex(idx)
        for key in dict_to_add:
            val = str(dict_to_add[key])
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            section.appendRow([child0, child1])
        self.update_tab_text()

    def browse_file_path(self):
        """ Browse for the data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder",
                                                             file_path, QtWidgets.QFileDialog.ShowDirsOnly)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                              directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                              directory=file_path, filter="*.nc")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def get_existing_entries(self):
        """ Get a list of existing entries in the current section."""
        # index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from its index
        selected_item = idx.model().itemFromIndex(idx)
        # build a list of existing QC checks
        existing_entries = []
        if selected_item.hasChildren():
            for i in range(selected_item.rowCount()):
                existing_entries.append(str(selected_item.child(i, 0).text()))
        return existing_entries

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_level_selected_item(self):
        """ Get the level of the selected item."""
        model = self.model
        indexes = self.view.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        return level

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        self.update_tab_text()

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_nc2csv_ecostress(QtWidgets.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_nc2csv_ecostress, self).__init__()

        self.cfg = copy.deepcopy(main_gui.cfg)

        self.cfg_changed = False
        self.tabs = main_gui.tabs

        self.edit_nc2csv_ecostress_gui()

    def edit_nc2csv_ecostress_gui(self):
        """ Edit an nc2csv_ecostress control file GUI."""
        # get a QTreeView
        self.view = QtWidgets.QTreeView()
        self.model = QtGui.QStandardItemModel()
        # set the context menu policy
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.view.customContextMenuRequested.connect(self.context_menu)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.view)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.view.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.view.setHeaderHidden(False)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.view.setModel(self.model)
        #self.tree.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()
        # set the default width for the first column
        self.view.setColumnWidth(0, 210)
        # expand the top level of the sections
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 0)
            self.view.expand(idx)

    def get_model_from_data(self):
        """ Build the data model."""
        self.model.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.model.itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.sections = {}
        for key1 in self.cfg:
            if not self.cfg[key1]:
                continue
            if key1 in ["Files", "General"]:
                # sections with only 1 level
                self.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg[key1]:
                    val = self.cfg[key1][key2]
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.sections[key1].appendRow([child0, child1])
                self.model.appendRow(self.sections[key1])
            elif key1 in ["Variables"]:
                # sections with 2 levels
                self.sections[key1] = QtGui.QStandardItem(key1)
                # key2 is the variable name
                for key2 in self.cfg[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    # key3 is the variable options
                    for key3 in self.cfg[key1][key2]:
                        val = self.cfg[key1][key2][key3]
                        child0 = QtGui.QStandardItem(key3)
                        child1 = QtGui.QStandardItem(val)
                        parent2.appendRow([child0, child1])
                    self.sections[key1].appendRow(parent2)
                self.model.appendRow(self.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = ConfigObj(indent_type="    ", list_values=False)
        cfg["level"] = "nc2csv_ecostress"
        model = self.model
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files", "General"]:
                # sections with only 1 level
                for j in range(section.rowCount()):
                    key2 = str(section.child(j, 0).text())
                    val2 = str(section.child(j, 1).text())
                    cfg[key1][key2] = val2
            elif key1 in ["Variables"]:
                # sections with 2 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3

        return cfg

    def context_menu(self, position):
        """ Right click context menu."""
        # get a menu
        self.context_menu = QtWidgets.QMenu()
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item text
        selected_text = str(idx.data())
        # get the selected item
        selected_item = idx.model().itemFromIndex(idx)
        # get the level of the selected item
        level = self.get_level_selected_item()
        # initialise logical for inserting a separator
        add_separator = False
        if level == 0:
            if selected_text in ["Variables"]:
                self.context_menu.actionAddVariable = QtWidgets.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_new_variable)
            elif selected_text in ["General"]:
                self.context_menu.actionAddItem = QtWidgets.QAction(self)
                self.context_menu.actionAddItem.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddItem)
                self.context_menu.actionAddItem.triggered.connect(self.add_general_item)
        elif level == 1:
            # sections with 2 levels
            # get the parent of the selected item
            parent = selected_item.parent()
            if (str(parent.text()) == "Files") and (selected_item.column() == 1):
                key = str(parent.child(selected_item.row(),0).text())
                if key in ["file_path"]:
                    self.context_menu.actionBrowseFilePath = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key in ["in_filename"]:
                    self.context_menu.actionBrowseInputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key in ["out_filename"]:
                    self.context_menu.actionBrowseOutputFile = QtWidgets.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
            elif (str(parent.text()) == "Variables") and (selected_item.column() == 0):
                self.context_menu.actionRemoveOption = QtWidgets.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_item)
            elif (str(parent.text()) == "General") and (selected_item.column() == 0):
                self.context_menu.actionRemoveItem = QtWidgets.QAction(self)
                self.context_menu.actionRemoveItem.setText("Remove item")
                self.context_menu.addAction(self.context_menu.actionRemoveItem)
                self.context_menu.actionRemoveItem.triggered.connect(self.remove_item)
        elif level == 2:
            # sections with 3 levels
            pass

        self.context_menu.exec_(self.view.viewport().mapToGlobal(position))

    def add_general_item(self):
        """ Add a new entry to the [Files] section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        section = idx.model().itemFromIndex(idx)
        dict_to_add = {"New item":""}
        # add the subsection
        self.add_subsection(section, dict_to_add)

    def add_new_variable(self):
        """ Add a new variable to the 'Variables' section."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        parent = idx.model().itemFromIndex(idx)
        dict_to_add = {"ncname": "", "units": "", "format": ""}
        subsection = QtGui.QStandardItem("New variable")
        self.add_subsection(subsection, dict_to_add)
        parent.appendRow(subsection)
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def add_subsection(self, section, dict_to_add):
        """ Add a subsection to the model."""
        for key in dict_to_add:
            val = str(dict_to_add[key])
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(val)
            section.appendRow([child0, child1])

    def browse_file_path(self):
        """ Browse for the data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the selected entry text
        file_path = str(idx.data())
        # dialog for new directory
        new_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose a folder",
                                                             file_path, QtWidgets.QFileDialog.ShowDirsOnly)
        # quit if cancel button pressed
        if len(str(new_dir)) > 0:
            # make sure the string ends with a path delimiter
            tmp_dir = QtCore.QDir.toNativeSeparators(str(new_dir))
            new_dir = os.path.join(tmp_dir, "")
            # update the model
            parent.child(selected_item.row(), 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                              directory=file_path)[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        # get the index of the selected item
        idx = self.view.selectedIndexes()[0]
        # get the selected item from the index
        selected_item = idx.model().itemFromIndex(idx)
        # get the parent of the selected item
        parent = selected_item.parent()
        # get the top level and sub sections
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(parent, "file_path")
        # dialog for open file
        new_file_path = QtWidgets.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                              directory=file_path, filter="*.csv")[0]
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            parent.child(selected_item.row(), 1).setText(new_file_parts[1])

    def get_keyval_by_key_name(self, section, key):
        """ Get the value from a section based on the key name."""
        found = False
        val_child = ""
        key_child = ""
        for i in range(section.rowCount()):
            if str(section.child(i, 0).text()) == str(key):
                found = True
                key_child = str(section.child(i, 0).text())
                val_child = str(section.child(i, 1).text())
                break
        return key_child, val_child, found, i

    def get_level_selected_item(self):
        """ Get the level of the selected item."""
        indexes = self.view.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        return level

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # update the control file contents
        self.cfg = self.get_data_from_model()
        # add an asterisk to the tab text to indicate the tab contents have changed
        self.update_tab_text()

    def remove_item(self):
        """ Remove an item from the view."""
        # loop over selected items in the tree
        for idx in self.view.selectedIndexes():
            # get the selected item from the index
            selected_item = idx.model().itemFromIndex(idx)
            # get the parent of the selected item
            parent = selected_item.parent()
            # remove the row
            parent.removeRow(selected_item.row())
        self.update_tab_text()

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class pfp_l4_ui(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(pfp_l4_ui, self).__init__(parent)
        self.resize(400, 236)
        self.setWindowTitle("Gap fill (alternate)")
        self.RunButton = QtWidgets.QPushButton(self)
        self.RunButton.setGeometry(QtCore.QRect(20, 200, 93, 27))
        self.RunButton.setText("Run")
        self.DoneButton = QtWidgets.QPushButton(self)
        self.DoneButton.setGeometry(QtCore.QRect(150, 200, 93, 27))
        self.DoneButton.setText("Done")
        self.QuitButton = QtWidgets.QPushButton(self)
        self.QuitButton.setGeometry(QtCore.QRect(270, 200, 93, 27))
        self.QuitButton.setText("Quit")
        self.checkBox_ShowPlots = QtWidgets.QCheckBox(self)
        self.checkBox_ShowPlots.setGeometry(QtCore.QRect(20, 170, 94, 22))
        self.checkBox_ShowPlots.setText("Show plots")
        self.checkBox_ShowPlots.setChecked(True)
        self.checkBox_PlotAll = QtWidgets.QCheckBox(self)
        self.checkBox_PlotAll.setGeometry(QtCore.QRect(150, 170, 94, 22))
        self.checkBox_PlotAll.setText("Plot all")
        self.checkBox_Overwrite = QtWidgets.QCheckBox(self)
        self.checkBox_Overwrite.setGeometry(QtCore.QRect(270, 170, 94, 22))
        self.checkBox_Overwrite.setText("Overwrite")

        self.radioButton_NumberMonths = QtWidgets.QRadioButton(self)
        self.radioButton_NumberMonths.setGeometry(QtCore.QRect(20, 140, 110, 22))
        self.radioButton_NumberMonths.setText("Months")
        self.radioButton_NumberMonths.setChecked(True)
        self.radioButton_NumberDays = QtWidgets.QRadioButton(self)
        self.radioButton_NumberDays.setGeometry(QtCore.QRect(130, 140, 110, 22))
        self.radioButton_NumberDays.setText("Days")
        self.radioButton_Manual = QtWidgets.QRadioButton(self)
        self.radioButton_Manual.setGeometry(QtCore.QRect(20, 110, 110, 25))
        self.radioButton_Manual.setText("Manual")
        self.radioButtons = QtWidgets.QButtonGroup(self)
        self.radioButtons.addButton(self.radioButton_NumberMonths)
        self.radioButtons.addButton(self.radioButton_NumberDays)
        self.radioButtons.addButton(self.radioButton_Manual)

        self.lineEdit_NumberMonths = QtWidgets.QLineEdit(self)
        self.lineEdit_NumberMonths.setGeometry(QtCore.QRect(90, 140, 30, 25))
        self.lineEdit_NumberMonths.setText("3")
        self.lineEdit_NumberDays = QtWidgets.QLineEdit(self)
        self.lineEdit_NumberDays.setGeometry(QtCore.QRect(220, 140, 30, 25))
        self.lineEdit_NumberDays.setText("90")
        self.checkBox_AutoComplete = QtWidgets.QCheckBox(self)
        self.checkBox_AutoComplete.setGeometry(QtCore.QRect(270, 140, 120, 25))
        self.checkBox_AutoComplete.setChecked(True)
        self.checkBox_AutoComplete.setText("Auto complete")
        self.lineEdit_MinPercent = QtWidgets.QLineEdit(self)
        self.lineEdit_MinPercent.setGeometry(QtCore.QRect(220, 110, 30, 25))
        self.lineEdit_MinPercent.setText("50")
        self.label_MinPercent = QtWidgets.QLabel(self)
        self.label_MinPercent.setGeometry(QtCore.QRect(140, 110, 80, 25))
        self.label_MinPercent.setText("Min pts (%)")
        self.lineEdit_EndDate = QtWidgets.QLineEdit(self)
        self.lineEdit_EndDate.setGeometry(QtCore.QRect(220, 77, 161, 25))
        self.label_EndDate = QtWidgets.QLabel(self)
        self.label_EndDate.setGeometry(QtCore.QRect(30, 80, 171, 20))
        self.label_EndDate.setText("End date (YYYY-MM-DD)")
        self.lineEdit_StartDate = QtWidgets.QLineEdit(self)
        self.lineEdit_StartDate.setGeometry(QtCore.QRect(220, 47, 161, 25))
        self.label_StartDate = QtWidgets.QLabel(self)
        self.label_StartDate.setGeometry(QtCore.QRect(30, 47, 171, 20))
        self.label_StartDate.setText("Start date (YYYY-MM-DD)")
        self.label_DataStartDate = QtWidgets.QLabel(self)
        self.label_DataStartDate.setGeometry(QtCore.QRect(48, 6, 111, 17))
        self.label_DataEndDate = QtWidgets.QLabel(self)
        self.label_DataEndDate.setGeometry(QtCore.QRect(244, 6, 101, 17))
        self.label_DataStartDate_value = QtWidgets.QLabel(self)
        self.label_DataStartDate_value.setGeometry(QtCore.QRect(33, 26, 151, 20))
        self.label_DataEndDate_value = QtWidgets.QLabel(self)
        self.label_DataEndDate_value.setGeometry(QtCore.QRect(220, 26, 141, 17))
        self.label_DataStartDate.setText("Data start date")
        self.label_DataEndDate.setText("Data end date")
        self.label_DataStartDate_value.setText("YYYY-MM-DD HH:mm")
        self.label_DataEndDate_value.setText("YYYY-MM-DD HH:mm")
        # connect signals to slots
        self.RunButton.clicked.connect(lambda:pfp_gfALT.gfalternate_run_interactive(self))
        self.DoneButton.clicked.connect(lambda:pfp_gfALT.gfalternate_done(self))
        self.QuitButton.clicked.connect(lambda:pfp_gfALT.gfalternate_quit(self))

class solo_gui(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(solo_gui, self).__init__(parent)
        self.resize(400, 265)
        # component sizes and positions
        row_height = 25
        label_width = 145
        label_height = 20
        lineedit_long_width = 160
        lineedit_short_width = 30
        lineedit_height = 20
        radiobutton_width = 110
        radiobutton_height = 20
        checkbox_width = 95
        checkbox_height = 20
        button_width = 90
        button_height = 25
        # first row; Date start and end headings
        row1_y = 5
        self.label_DataStartDate = QtWidgets.QLabel(self)
        self.label_DataStartDate.setGeometry(QtCore.QRect(48, row1_y, label_width, label_height))
        self.label_DataEndDate = QtWidgets.QLabel(self)
        self.label_DataEndDate.setGeometry(QtCore.QRect(244, row1_y, label_width, label_height))
        # second row; Date start and end values
        row2_y = row1_y + row_height
        self.label_DataStartDate_value = QtWidgets.QLabel(self)
        self.label_DataStartDate_value.setGeometry(QtCore.QRect(33, row2_y, label_width, label_height))
        self.label_DataEndDate_value = QtWidgets.QLabel(self)
        self.label_DataEndDate_value.setGeometry(QtCore.QRect(220, row2_y, label_width, label_height))
        self.label_DataStartDate.setText("Data start date")
        self.label_DataEndDate.setText("Data end date")
        self.label_DataStartDate_value.setText("YYYY-MM-DD HH:mm")
        self.label_DataEndDate_value.setText("YYYY-MM-DD HH:mm")
        # third row; Nodes etc
        row3_y = row2_y + row_height
        self.label_Nodes = QtWidgets.QLabel(self)
        self.label_Nodes.setGeometry(QtCore.QRect(20, row3_y, 60, label_height))
        self.label_Nodes.setText("Nodes")
        self.lineEdit_Nodes = QtWidgets.QLineEdit(self)
        self.lineEdit_Nodes.setGeometry(QtCore.QRect(80, row3_y, 50, lineedit_height))
        self.lineEdit_Nodes.setText("10")
        self.label_Training = QtWidgets.QLabel(self)
        self.label_Training.setGeometry(QtCore.QRect(150, row3_y, 50, label_height))
        self.label_Training.setText("Training")
        self.lineEdit_Training = QtWidgets.QLineEdit(self)
        self.lineEdit_Training.setGeometry(QtCore.QRect(210, row3_y, 50, lineedit_height))
        self.lineEdit_Training.setText("500")
        self.label_NdaFactor = QtWidgets.QLabel(self)
        self.label_NdaFactor.setGeometry(QtCore.QRect(270, row3_y, 70, label_height))
        self.label_NdaFactor.setText("Nda factor")
        self.lineEdit_NdaFactor = QtWidgets.QLineEdit(self)
        self.lineEdit_NdaFactor.setGeometry(QtCore.QRect(340, row3_y, 50, lineedit_height))
        self.lineEdit_NdaFactor.setText("5")
        # fourth row; Learning, Iterations
        row4_y = row3_y + row_height
        self.label_Learning = QtWidgets.QLabel(self)
        self.label_Learning.setGeometry(QtCore.QRect(140, row4_y, 60, label_height))
        self.label_Learning.setText("Learning")
        self.lineEdit_Learning = QtWidgets.QLineEdit(self)
        self.lineEdit_Learning.setGeometry(QtCore.QRect(210, row4_y, 50, lineedit_height))
        self.lineEdit_Learning.setText("0.001")
        self.label_Iterations = QtWidgets.QLabel(self)
        self.label_Iterations.setGeometry(QtCore.QRect(270, row4_y, 70, label_height))
        self.label_Iterations.setText("Iterations")
        self.lineEdit_Iterations = QtWidgets.QLineEdit(self)
        self.lineEdit_Iterations.setGeometry(QtCore.QRect(340, row4_y, 50, lineedit_height))
        self.lineEdit_Iterations.setText("500")
        # fifth row; start date line edit box
        row5_y = row4_y + row_height
        self.label_StartDate = QtWidgets.QLabel(self)
        self.label_StartDate.setGeometry(QtCore.QRect(30, row5_y, lineedit_long_width, lineedit_height))
        self.label_StartDate.setText("Start date (YYYY-MM-DD)")
        self.lineEdit_StartDate = QtWidgets.QLineEdit(self)
        self.lineEdit_StartDate.setGeometry(QtCore.QRect(220, row5_y, lineedit_long_width, lineedit_height))
        # sixth row; end date line edit box
        row6_y = row5_y + row_height
        self.label_EndDate = QtWidgets.QLabel(self)
        self.label_EndDate.setGeometry(QtCore.QRect(30, row6_y, lineedit_long_width, lineedit_height))
        self.label_EndDate.setText("End date (YYYY-MM-DD)")
        self.lineEdit_EndDate = QtWidgets.QLineEdit(self)
        self.lineEdit_EndDate.setGeometry(QtCore.QRect(220, row6_y, lineedit_long_width, lineedit_height))
        # seventh row
        row7_y = row6_y + row_height
        self.radioButton_Manual = QtWidgets.QRadioButton(self)
        self.radioButton_Manual.setGeometry(QtCore.QRect(20, row7_y, radiobutton_width, radiobutton_height))
        self.radioButton_Manual.setText("Manual")
        self.lineEdit_MinPercent = QtWidgets.QLineEdit(self)
        self.lineEdit_MinPercent.setGeometry(QtCore.QRect(220, row7_y, 30, lineedit_height))
        self.lineEdit_MinPercent.setText("25")
        self.label_MinPercent = QtWidgets.QLabel(self)
        self.label_MinPercent.setGeometry(QtCore.QRect(140, row7_y, 80, label_height))
        self.label_MinPercent.setText("Min pts (%)")
        # eighth row; Months, Days, Auto-complete
        row8_y = row7_y + row_height
        self.radioButton_NumberMonths = QtWidgets.QRadioButton(self)
        self.radioButton_NumberMonths.setGeometry(QtCore.QRect(20, row8_y, radiobutton_width, radiobutton_height))
        self.radioButton_NumberMonths.setText("Months")
        self.lineEdit_NumberMonths = QtWidgets.QLineEdit(self)
        self.lineEdit_NumberMonths.setGeometry(QtCore.QRect(90, row8_y, lineedit_short_width, lineedit_height))
        self.radioButton_NumberDays = QtWidgets.QRadioButton(self)
        self.radioButton_NumberDays.setGeometry(QtCore.QRect(150, row8_y, radiobutton_width, radiobutton_height))
        self.radioButton_NumberDays.setText("Days")
        self.lineEdit_NumberDays = QtWidgets.QLineEdit(self)
        self.lineEdit_NumberDays.setGeometry(QtCore.QRect(220, row8_y, lineedit_short_width, lineedit_height))
        self.lineEdit_NumberDays.setText("60")
        self.checkBox_AutoComplete = QtWidgets.QCheckBox(self)
        self.checkBox_AutoComplete.setGeometry(QtCore.QRect(270, row8_y, radiobutton_width+10, radiobutton_height))
        self.checkBox_AutoComplete.setText("Auto complete")
        # define the radio button group
        self.radioButtons = QtWidgets.QButtonGroup(self)
        self.radioButtons.addButton(self.radioButton_NumberMonths)
        self.radioButtons.addButton(self.radioButton_NumberDays)
        self.radioButtons.addButton(self.radioButton_Manual)
        # ninth row; Show plots, Plot all and Overwrite checkboxes
        row9_y = row8_y + row_height
        self.checkBox_ShowPlots = QtWidgets.QCheckBox(self)
        self.checkBox_ShowPlots.setGeometry(QtCore.QRect(20, row9_y, checkbox_width, checkbox_height))
        self.checkBox_ShowPlots.setText("Show plots")
        self.checkBox_ShowPlots.setChecked(True)
        self.checkBox_PlotAll = QtWidgets.QCheckBox(self)
        self.checkBox_PlotAll.setGeometry(QtCore.QRect(150, row9_y, checkbox_width, checkbox_height))
        self.checkBox_PlotAll.setText("Plot all")
        self.checkBox_Overwrite = QtWidgets.QCheckBox(self)
        self.checkBox_Overwrite.setGeometry(QtCore.QRect(270, row9_y, checkbox_width, checkbox_height))
        self.checkBox_Overwrite.setText("Overwrite")
        # tenth (bottom) row; Run, Done and Quit buttons
        row10_y = row9_y + row_height
        self.RunButton = QtWidgets.QPushButton(self)
        self.RunButton.setGeometry(QtCore.QRect(20, row10_y, button_width, button_height))
        self.RunButton.setText("Run")
        self.DoneButton = QtWidgets.QPushButton(self)
        self.DoneButton.setGeometry(QtCore.QRect(150, row10_y, button_width, button_height))
        self.DoneButton.setText("Done")
        self.QuitButton = QtWidgets.QPushButton(self)
        self.QuitButton.setGeometry(QtCore.QRect(270, row10_y, button_width, button_height))
        self.QuitButton.setText("Quit")
        # connect the "Run", "Done" and "Quit" buttons to their slots
        self.RunButton.clicked.connect(self.call_gui_run)
        self.DoneButton.clicked.connect(self.call_gui_done)
        self.QuitButton.clicked.connect(self.call_gui_quit)

    def call_gui_run(self):
        pfp_gfSOLO.gfSOLO_run_interactive(self)

    def call_gui_quit(self):
        pfp_gfSOLO.gfSOLO_quit(self)

    def call_gui_done(self):
        pfp_gfSOLO.gfSOLO_done(self)
