# standard modules
import copy
import inspect
import logging
import os
import pdb
# 3rd party modules
from PyQt4 import QtCore, QtGui
# PFP modules
import pfp_func
import pfp_utils
import pfp_gfALT
import pfp_gfSOLO
import pfp_rpNN

logger = logging.getLogger("pfp_log")

#class custom_treeview(QtGui.QTreeView):
    #def __init__(self, parent=None):
        #super(custom_treeview, self).__init__()
        ##QtGui.QTreeView.__init__(self, parent)
        #self.setItemsExpandable(True)
        #self.setAnimated(True)
        #self.setDragEnabled(True)
        #self.setDropIndicatorShown(True)
        #self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)

    #def dragMoveEvent(self, event):
        #print "moving"
        #super(custom_treeview, self).dragMoveEvent(event)

    #def dropEvent(self, event):
        #print "dropping"
        ##super(custom_treeview, self).dropEvent(event)

    #def dragEnterEvent(self, event):
        #print "entering"
        #event.accept()

class edit_cfg_L1(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L1, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_L1_gui()

    def edit_L1_gui(self):
        """ Edit L1 control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        #self.tree = custom_treeview()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.context_menu)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.tree.setModel(QtGui.QStandardItemModel())
        #self.tree.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()

    def get_model_from_data(self):
        """ Build the data model."""
        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.tree.model().itemChanged.connect(self.handleItemChanged)
        # there must be some way to do this recursively
        self.tree.sections = {}
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Output"]:
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    val = self.cfg_mod[key1][key2]
                    val = self.parse_cfg_values(key2, val, ['"', "'"])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.tree.sections[key1].appendRow([child0, child1])
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["Variables"]:
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for key4 in self.cfg_mod[key1][key2][key3]:
                            val = self.cfg_mod[key1][key2][key3][key4]
                            val = self.parse_cfg_values(key4, val, ['"', "'"])
                            child0 = QtGui.QStandardItem(key4)
                            child1 = QtGui.QStandardItem(val)
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = self.cfg_mod
        model = self.tree.model()
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

    def get_section_from_text(self, model, section_name):
        """ Gets a section from a model by matching the section name."""
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == str(section_name):
                break
        return section, i

    def get_subsection_from_text(self, section, text):
        """ Gets a subsection from a model by matching the subsection name"""
        for i in range(section.rowCount()):
            subsection = section.child(i)
            if str(subsection.text()) == text:
                break
        return subsection, i

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def context_menu(self, position):
        """ Right click context menu."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        self.context_menu = QtGui.QMenu()
        if level == 0:
            if str(indexes[0].data().toString()) == "Files":
                self.context_menu.actionAddFileEntry = QtGui.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif str(indexes[0].data().toString()) == "Global":
                self.context_menu.actionAddGlobal = QtGui.QAction(self)
                self.context_menu.actionAddGlobal.setText("Add attribute")
                self.context_menu.addAction(self.context_menu.actionAddGlobal)
                self.context_menu.actionAddGlobal.triggered.connect(self.add_global)
            elif str(indexes[0].data().toString()) == "Variables":
                self.context_menu.actionAddVariable = QtGui.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
        elif level == 1:
            if str(indexes[0].parent().data().toString()) == "Files":
                # get the parent section
                for i in range(model.rowCount()):
                    section = model.item(i)
                    if str(section.text()) == str(indexes[0].parent().data().toString()):
                        break
                # get the key and value for the selected item
                for i in range(section.rowCount()):
                    key = str(section.child(i, 0).text())
                    val = str(section.child(i, 1).text())
                    if key == str(indexes[0].data().toString()):
                        return
                    if str(indexes[0].data().toString()) == val:
                        break
                # check to see if we have the selected subsection
                if key == "file_path" and key != str(indexes[0].data().toString()):
                    self.context_menu.actionBrowseFilePath = QtGui.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key == "in_filename" and key != str(indexes[0].data().toString()):
                    self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key == "out_filename" and key != str(indexes[0].data().toString()):
                    self.context_menu.actionBrowseOutputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                else:
                    pass
            elif str(indexes[0].parent().data().toString()) == "Global":
                self.context_menu.actionRemoveGlobal = QtGui.QAction(self)
                self.context_menu.actionRemoveGlobal.setText("Remove attribute")
                self.context_menu.addAction(self.context_menu.actionRemoveGlobal)
                self.context_menu.actionRemoveGlobal.triggered.connect(self.remove_global)
            elif str(indexes[0].parent().data().toString()) == "Variables":
                self.context_menu.actionAddFunction = QtGui.QAction(self)
                self.context_menu.actionAddFunction.setText("Add Function")
                self.context_menu.addAction(self.context_menu.actionAddFunction)
                self.context_menu.actionAddFunction.triggered.connect(self.add_function)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveVariable = QtGui.QAction(self)
                self.context_menu.actionRemoveVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveVariable)
                self.context_menu.actionRemoveVariable.triggered.connect(self.remove_variable)
        elif level == 2:
            section_text = str(indexes[0].parent().parent().data().toString())
            subsection_text = str(indexes[0].parent().data().toString())
            subsubsection_text = str(indexes[0].data().toString())
            if section_text == "Variables":
                if subsubsection_text == "Attr":
                    self.context_menu.actionAddAttribute = QtGui.QAction(self)
                    self.context_menu.actionAddAttribute.setText("Add attribute")
                    self.context_menu.addAction(self.context_menu.actionAddAttribute)
                    self.context_menu.actionAddAttribute.triggered.connect(self.add_attribute)
                elif subsubsection_text in ["xl", "Function"]:
                    self.context_menu.actionRemoveSubSubSection = QtGui.QAction(self)
                    self.context_menu.actionRemoveSubSubSection.setText("Remove item")
                    self.context_menu.addAction(self.context_menu.actionRemoveSubSubSection)
                    self.context_menu.actionRemoveSubSubSection.triggered.connect(self.remove_subsubsection)
        elif level == 3:
            if str(indexes[0].parent().data().toString()) == "Attr":
                self.context_menu.actionRemoveAttribute = QtGui.QAction(self)
                self.context_menu.actionRemoveAttribute.setText("Remove attribute")
                self.context_menu.addAction(self.context_menu.actionRemoveAttribute)
                self.context_menu.actionRemoveAttribute.triggered.connect(self.remove_attribute)
            elif (str(indexes[0].parent().data().toString()) == "Function" and
                  str(indexes[0].data().toString()) == "Right click to browse"):
                implemented_functions_name = [name for name,data in inspect.getmembers(pfp_func,inspect.isfunction)]
                self.context_menu.actionAddFunction = {}
                for item in implemented_functions_name:
                    self.context_menu.actionAddFunction[item] = QtGui.QAction(self)
                    self.context_menu.actionAddFunction[item].setText(str(item))
                    self.context_menu.addAction(self.context_menu.actionAddFunction[item])
                    self.context_menu.actionAddFunction[item].triggered.connect(self.add_function_entry)

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_attribute(self):
        """ Add a variable attribute to a variable in the [Variables] section."""
        model = self.tree.model()
        # loop over selected items in the tree
        indexes = self.tree.selectedIndexes()
        # get the name of the parent of the selected item
        parent = str(indexes[0].parent().data().toString())
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        for i in range(section.rowCount()):
            subsection = section.child(i)
            if str(subsection.text()) == str(indexes[0].parent().data().toString()):
                break
        for i in range(subsection.rowCount()):
            subsubsection = subsection.child(i)
            if str(subsubsection.text()) == str(indexes[0].data().toString()):
                break
        child0 = QtGui.QStandardItem("New attribute")
        child1 = QtGui.QStandardItem("")
        subsubsection.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_function(self):
        """ Add a function to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"Function":{"func": "Right click to browse"}}
        # get the parent and sub section text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_function_entry(self):
        """ Add the selected function to the variables [Function] subsection."""
        # get the index of the selected item
        idx = self.tree.selectedIndexes()[0]
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
        for item in args[0][1:]:
            function_string = function_string + str(item) + ","
        function_string = function_string[:-1] + ")"
        # get the selected item from the index
        item = idx.model().itemFromIndex(idx)
        # change the text of the selected item
        item.setText(function_string)

    def add_fileentry(self):
        """ Add a new entry to the 'Files' section."""
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        self.tree.sections["Files"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_global(self):
        """ Add a new entry to the 'Global' section."""
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        self.tree.sections["Global"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_subsubsection(self, subsection, dict_to_add):
        """ Add a subsubsection to the model."""
        for key1 in dict_to_add:
            subsubsection = QtGui.QStandardItem(key1)
            for key2 in dict_to_add[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(dict_to_add[key1][key2]))
                subsubsection.appendRow([child0, child1])
            subsection.appendRow(subsubsection)

    def add_subsubsubsection(self, subsection, dict_to_add):
        """ Add a subsubsubsection to the model."""
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

    def add_variable(self):
        """ Add a new variable."""
        new_var = {"xl":{"sheet":"", "name":""},
                   "Attr":{"height":"<height>m", "instrument":"", "long_name":"",
                           "serial_number":"", "standard_name":"", "units":""}}
        parent2 = QtGui.QStandardItem("New variable")
        for key3 in new_var:
            parent3 = QtGui.QStandardItem(key3)
            for key4 in new_var[key3]:
                value = new_var[key3][key4]
                child0 = QtGui.QStandardItem(key4)
                child1 = QtGui.QStandardItem(str(value))
                parent3.appendRow([child0, child1])
            parent2.appendRow(parent3)
        self.tree.sections["Variables"].appendRow(parent2)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def browse_file_path(self):
        """ Browse for the data file path."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the section containing the selected item
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Files":
                break
        # get the key and value of the selected item
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(indexes[0].data().toString()) == val:
                break
        # dialog for new directory
        new_dir = QtGui.QFileDialog.getExistingDirectory(self, "Open a folder", val, QtGui.QFileDialog.ShowDirsOnly)
        new_dir = os.path.join(str(new_dir), "")
        # update the model
        if len(str(new_dir)) > 0:
            section.child(i,1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        """ Browse for the input data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                              directory=file_path)
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                              directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

    def parse_cfg_values(self, k, v, strip_list):
        """ Parse key values to remove unnecessary characters."""
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def remove_attribute(self):
        """ Remove a variable attribute from a variable."""
        model = self.tree.model()
        # loop over selected items in the tree
        indexes = self.tree.selectedIndexes()
        # get the top level section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].parent().parent().data().toString()):
                break
        # loop over all QC checks in this variable
        for i in range(subsection.rowCount()):
            subsubsection = subsection.child(i)
            if str(subsubsection.text()) == str(indexes[0].parent().data().toString()):
                break
        # loop over all date ranges in the ExcludeDates QC check
        for i in range(subsubsection.rowCount()):
            subsubsubsection = subsubsection.child(i)
            if str(subsubsubsection.text()) == str(indexes[0].data().toString()):
                subsubsection.removeRow(i)
                # add an asterisk to the tab text to indicate the tab contents have changed
                tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                if "*" not in tab_text:
                    self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                break

    #def remove_fileentry(self):
        #""" Remove an entry from the [Files] section."""
        #model = self.tree.model()
        ## loop over selected items in the tree
        #for idx in self.tree.selectedIndexes():
            ## get the name of the parent of the selected item
            #parent = str(idx.parent().data().toString())
            ## get the parent section
            #for i in range(model.rowCount()):
                #section = model.item(i)
                #if str(section.text()) == "Files":
                    #break
            ## loop over all children in the [Files] section
            #for i in range(section.rowCount()):
                ## get the child subsection
                #subsection = section.child(i)
                ## check to see if we have the selected subsection
                #if str(subsection.text()) == str(idx.data().toString()):
                    ## if so, remove the row
                    #section.removeRow(i)
                    ## add an asterisk to the tab text to indicate the tab contents have changed
                    #tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    #if "*" not in tab_text:
                        #self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    #break

    def remove_global(self):
        """ Remove an entry from the [Global] section."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Global":
                    break
            # loop over all children in the [Global] section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.data().toString()):
                    # if so, remove the row
                    section.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def remove_subsubsection(self):
        """ Remove a subsubsection."""
        idx = self.tree.selectedIndexes()[0]
        subsubsection_text = str(idx.data().toString())
        subsection_text = str(idx.parent().data().toString())
        section_text = str(idx.parent().parent().data().toString())
        # get the [Variables] section
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the variable section
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # get the gap filling method section
        subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
        subsection.removeRow(k)
        self.update_tab_text()

    def remove_variable(self):
        """ Remove a variable."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            # loop over all children in the "Variables" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.data().toString()):
                    # if so, remove the row
                    section.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L2(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L2, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_L2_gui()

    def edit_L2_gui(self):
        """ Edit L2 control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.context_menu)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.tree.setModel(QtGui.QStandardItemModel())
        #self.tree.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()

    def get_model_from_data(self):
        """ Build the data model."""
        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.tree.model().itemChanged.connect(self.handleItemChanged)
        # there must be some way to do this recursively
        self.tree.sections = {}
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files"]:
                # sections with only 1 level
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for val in self.cfg_mod[key1]:
                    value = self.cfg_mod[key1][val]
                    value = self.parse_cfg_files_value(val, value)
                    child0 = QtGui.QStandardItem(val)
                    child1 = QtGui.QStandardItem(value)
                    self.tree.sections[key1].appendRow([child0, child1])
                self.tree.model().appendRow(self.tree.sections[key1])
            elif  key1 in ["Plots"]:
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    # handle old-style control files with separate Title key
                    title = self.parse_cfg_plots_title(key1, key2)
                    parent2 = QtGui.QStandardItem(title)
                    for val in self.cfg_mod[key1][key2]:
                        value = self.cfg_mod[key1][key2][val]
                        value = self.parse_cfg_plots_value(val, value)
                        child0 = QtGui.QStandardItem(val)
                        child1 = QtGui.QStandardItem(value)
                        parent2.appendRow([child0, child1])
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["Variables"]:
                # sections with 3 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for val in self.cfg_mod[key1][key2][key3]:
                            value = self.cfg_mod[key1][key2][key3][val]
                            value = self.parse_cfg_variables_value(key3, value)
                            child0 = QtGui.QStandardItem(val)
                            child1 = QtGui.QStandardItem(value)
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = self.cfg_mod
        model = self.tree.model()
        # there must be a way to do this recursively
        for i in range(model.rowCount()):
            section = model.item(i)
            key1 = str(section.text())
            cfg[key1] = {}
            if key1 in ["Files"]:
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

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def context_menu(self, position):
        """ Right click context menu."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        self.context_menu = QtGui.QMenu()
        if level == 0:
            if str(indexes[0].data().toString()) == "Files":
                self.context_menu.actionAddFileEntry = QtGui.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif str(indexes[0].data().toString()) == "Variables":
                self.context_menu.actionAddVariable = QtGui.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
            elif str(indexes[0].data().toString()) == "Plots":
                self.context_menu.actionAddTimeSeries = QtGui.QAction(self)
                self.context_menu.actionAddTimeSeries.setText("Add time series")
                self.context_menu.addAction(self.context_menu.actionAddTimeSeries)
                self.context_menu.actionAddTimeSeries.triggered.connect(self.add_timeseries)
                self.context_menu.actionAddScatterPlot = QtGui.QAction(self)
                self.context_menu.actionAddScatterPlot.setText("Add scatter plot")
                self.context_menu.addAction(self.context_menu.actionAddScatterPlot)
                self.context_menu.actionAddScatterPlot.triggered.connect(self.add_scatterplot)
        elif level == 1:
            parent = str(indexes[0].parent().data().toString())
            if parent == "Variables":
                idx = indexes[0]
                # get the selected item from its index
                selected_item = idx.model().itemFromIndex(idx)
                # build a list of existing QC checks
                if selected_item.hasChildren():
                    existing_entries = []
                    for i in range(selected_item.rowCount()):
                        existing_entries.append(str(selected_item.child(i, 0).text()))
                # only put a QC check in the context menu if it is not already present
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtGui.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtGui.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                #self.context_menu.actionAddExcludeHours = QtGui.QAction(self)
                #self.context_menu.actionAddExcludeHours.setText("Add ExcludeHours")
                #self.context_menu.addAction(self.context_menu.actionAddExcludeHours)
                #self.context_menu.actionAddExcludeHours.triggered.connect(self.add_excludehours)
                #self.context_menu.actionAddLinear = QtGui.QAction(self)
                #self.context_menu.actionAddLinear.setText("Add Linear")
                #self.context_menu.addAction(self.context_menu.actionAddLinear)
                #self.context_menu.actionAddLinear.triggered.connect(self.add_linear)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveVariable = QtGui.QAction(self)
                self.context_menu.actionRemoveVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveVariable)
                self.context_menu.actionRemoveVariable.triggered.connect(self.remove_variable)
            elif parent == "Files":
                # get the parent section
                for i in range(model.rowCount()):
                    section = model.item(i)
                    if str(section.text()) == parent:
                        break
                # get the key and value for the selected item
                for i in range(section.rowCount()):
                    key = str(section.child(i, 0).text())
                    val = str(section.child(i, 1).text())
                    if key == str(indexes[0].data().toString()):
                        return
                    if str(indexes[0].data().toString()) == val:
                        break
                # check to see if we have the selected subsection
                if key in ["file_path", "plot_path"]:
                    self.context_menu.actionBrowseFilePath = QtGui.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key == "in_filename":
                    self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key == "out_filename":
                    self.context_menu.actionBrowseOutputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                else:
                    pass
            elif parent == "Plots":
                self.context_menu.actionRemovePlot = QtGui.QAction(self)
                self.context_menu.actionRemovePlot.setText("Remove plot")
                self.context_menu.addAction(self.context_menu.actionRemovePlot)
                self.context_menu.actionRemovePlot.triggered.connect(self.remove_plot)
        elif level == 2:
            parent = str(indexes[0].parent().data().toString())
            if str(indexes[0].data().toString()) in ["ExcludeDates"]:
                self.context_menu.actionAddExcludeDateRange = QtGui.QAction(self)
                self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                self.context_menu.addSeparator()
            self.context_menu.actionRemoveQCCheck = QtGui.QAction(self)
            self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
            self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
            self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_qccheck)
        elif level == 3:
            parent = str(indexes[0].parent().data().toString())
            if parent in ["ExcludeDates"]:
                self.context_menu.actionRemoveExcludeDateRange = QtGui.QAction(self)
                self.context_menu.actionRemoveExcludeDateRange.setText("Remove date range")
                self.context_menu.addAction(self.context_menu.actionRemoveExcludeDateRange)
                self.context_menu.actionRemoveExcludeDateRange.triggered.connect(self.remove_excludedaterange)

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_fileentry(self):
        """ Add a new entry to the 'Files' section."""
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        self.tree.files.appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_variable(self):
        """ Add a new variable to the 'Variables' section."""
        new_var_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        parent2 = QtGui.QStandardItem("New variable")
        for key3 in new_var_qc:
            parent3 = QtGui.QStandardItem(key3)
            for val in new_var_qc[key3]:
                value = new_var_qc[key3][val]
                child0 = QtGui.QStandardItem(val)
                child1 = QtGui.QStandardItem(str(value))
                parent3.appendRow([child0, child1])
            parent2.appendRow(parent3)
        self.tree.sections["Variables"].appendRow(parent2)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_timeseries(self):
        """ Add a new time series to the 'Plots' section."""
        new_plot = {"Variables":""}
        parent = QtGui.QStandardItem("New time series")
        for key in new_plot:
            value = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(value))
            parent.appendRow([child0, child1])
        self.tree.sections["Plots"].appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_scatterplot(self):
        """ Add a new scatter plot to the 'Plots' section."""
        new_plot = {"Type":"xy", "XSeries":"", "YSeries":""}
        parent = QtGui.QStandardItem("New scatter plot")
        for key in new_plot:
            value = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(value))
            parent.appendRow([child0, child1])
        self.tree.sections["Plots"].appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"DependencyCheck":{"Source":""}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"DiurnalCheck":{"NumSd":"5"}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"ExcludeDates":{"0":"YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM"}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_excludedaterange(self):
        """ Add another date range to the ExcludeDates QC check."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            for i in range(section.rowCount()):
                subsection = section.child(i)
                if str(subsection.text()) == str(idx.parent().data().toString()):
                    break
            for i in range(subsection.rowCount()):
                subsubsection = subsection.child(i)
                if str(subsubsection.text()) == str(idx.data().toString()):
                    break
            child0 = QtGui.QStandardItem(str(subsubsection.rowCount()))
            child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM")
            subsubsection.appendRow([child0, child1])

    def add_excludehours(self):
        """ Add an exclude hours check to a variable."""
        print " add ExcludeHours here"

    def add_linear(self):
        """ Add a linear correction to a variable."""
        print " add Linear here"

    def browse_file_path(self):
        """ Browse for the data file path."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the section containing the selected item
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Files":
                break
        # get the key and value of the selected item
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(indexes[0].data().toString()) == val:
                break
        # dialog for new directory
        new_dir = QtGui.QFileDialog.getExistingDirectory(self, "Open a folder", val, QtGui.QFileDialog.ShowDirsOnly)
        new_dir = os.path.join(str(new_dir), "")
        # update the model
        if len(str(new_dir)) > 0:
            section.child(i,1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the section containing the selected item
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Files":
                break
        # get the key and value of the file path
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if key == "file_path":
                file_path = val
                break
        # get the key and value of the selected item
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(indexes[0].data().toString()) == val:
                break
        # dialog for open file
        new_file = QtGui.QFileDialog.getOpenFileName(caption="Choose an input file ...", directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file)) > 0:
            section.child(i,1).setText(new_file)

    def browse_output_file(self):
        """ Browse for the output data file path."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the section containing the selected item
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Files":
                break
        # get the key and value of the file path
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if key == "file_path":
                file_path = val
                break
        # get the key and value of the selected item
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(indexes[0].data().toString()) == val:
                break
        # dialog for open file
        new_file = QtGui.QFileDialog.getOpenFileName(caption="Choose an output file ...", directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file)) > 0:
            section.child(i,1).setText(new_file)

    def remove_variable(self):
        """ Remove a variable."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            # loop over all children in the "Variables" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.data().toString()):
                    # if so, remove the row
                    section.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def remove_plot(self):
        """ Remove a plot."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Plots":
                    break
            # loop over all children in the "Plots" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.data().toString()):
                    # if so, remove the row
                    section.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def remove_qccheck(self):
        """ Remove a QC check."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            # loop over all children in the "Variables" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == parent:
                    for j in range(subsection.rowCount()):
                        subsubsection = subsection.child(j)
                        if str(subsubsection.text()) == str(idx.data().toString()):
                            # if so, remove the row
                            subsection.removeRow(j)
                            # add an asterisk to the tab text to indicate the tab contents have changed
                            tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                            if "*" not in tab_text:
                                self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                            break

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
        if "Title" in self.cfg_mod[key1][key2]:
            title = self.cfg_mod[key1][key2]["Title"]
            del self.cfg_mod[key1][key2]["Title"]
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
        if k == "Variables":
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
        elif k in ["ExcludeDates", "ExcludeHours"]:
            # don't remove white space between date and time
            strip_list = ['"', "'"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def remove_excludedaterange(self):
        """ Remove an ExcludeDates date range."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the top level section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            # loop over all children in the "Variables" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.parent().parent().data().toString()):
                    break
            # loop over all QC checks in this variable
            for i in range(subsection.rowCount()):
                subsubsection = subsection.child(i)
                if str(subsubsection.text()) == str(idx.parent().data().toString()):
                    break
            # loop over all date ranges in the ExcludeDates QC check
            for i in range(subsubsection.rowCount()):
                subsubsubsection = subsubsection.child(i)
                if str(subsubsubsection.text()) == str(idx.data().toString()):
                    subsubsection.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L3(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L3, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_L3_gui()

    def edit_L3_gui(self):
        """ Edit L3 control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.context_menu)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.tree.setModel(QtGui.QStandardItemModel())
        #self.tree.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()

    def get_model_from_data(self):
        """ Build the data model."""
        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.tree.model().itemChanged.connect(self.handleItemChanged)
        # correct legacy variable names in the control file
        self.correct_legacy_variable_names()
        # there must be some way to do this recursively
        self.tree.sections = {}
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                # sections with only 1 level
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    val = self.cfg_mod[key1][key2]
                    val = self.parse_cfg_values(key2, val, ['"', "'"])
                    if key2 in ["file_path", "plot_path"]:
                        val = os.path.join(str(val), "")
                        self.cfg_changed = True
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.tree.sections[key1].appendRow([child0, child1])
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["Plots"]:
                # sections with 2 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    # handle old-style control files with separate Title key
                    title = self.parse_cfg_plots_title(key1, key2)
                    parent2 = QtGui.QStandardItem(title)
                    for key3 in self.cfg_mod[key1][key2]:
                        val = self.cfg_mod[key1][key2][key3]
                        val = self.parse_cfg_plots_value(key3, val)
                        child0 = QtGui.QStandardItem(key3)
                        child1 = QtGui.QStandardItem(val)
                        parent2.appendRow([child0, child1])
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["Variables"]:
                # sections with 3 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        if key3 in ["ustar_threshold"]:
                            continue
                        parent3 = QtGui.QStandardItem(key3)
                        for key4 in self.cfg_mod[key1][key2][key3]:
                            val = self.cfg_mod[key1][key2][key3][key4]
                            val = self.parse_cfg_variables_value(key3, val)
                            child0 = QtGui.QStandardItem(key4)
                            child1 = QtGui.QStandardItem(val)
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = self.cfg_mod
        model = self.tree.model()
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

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def context_menu(self, position):
        """ Right click context menu."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        self.context_menu = QtGui.QMenu()
        if level == 0:
            if str(indexes[0].data().toString()) == "Files":
                self.context_menu.actionAddFileEntry = QtGui.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif str(indexes[0].data().toString()) == "Options":
                self.context_menu.actionAddUseL2Fluxes = QtGui.QAction(self)
                self.context_menu.actionAddUseL2Fluxes.setText("UseL2Fluxes")
                self.context_menu.addAction(self.context_menu.actionAddUseL2Fluxes)
                self.context_menu.actionAddUseL2Fluxes.triggered.connect(self.add_usel2fluxes)
                self.context_menu.actionAdd2DCoordRotation = QtGui.QAction(self)
                self.context_menu.actionAdd2DCoordRotation.setText("2DCoordRotation")
                self.context_menu.addAction(self.context_menu.actionAdd2DCoordRotation)
                self.context_menu.actionAdd2DCoordRotation.triggered.connect(self.add_2dcoordrotation)
                self.context_menu.actionAddMassmanCorrection = QtGui.QAction(self)
                self.context_menu.actionAddMassmanCorrection.setText("MassmanCorrection")
                self.context_menu.addAction(self.context_menu.actionAddMassmanCorrection)
                self.context_menu.actionAddMassmanCorrection.triggered.connect(self.add_massmancorrection)
                self.context_menu.actionAddApplyFcStorage = QtGui.QAction(self)
                self.context_menu.actionAddApplyFcStorage.setText("ApplyFcStorage")
                self.context_menu.addAction(self.context_menu.actionAddApplyFcStorage)
                self.context_menu.actionAddApplyFcStorage.triggered.connect(self.add_applyfcstorage)
                self.context_menu.actionAddCorrectIndividualFg = QtGui.QAction(self)
                self.context_menu.actionAddCorrectIndividualFg.setText("CorrectIndividualFg")
                self.context_menu.addAction(self.context_menu.actionAddCorrectIndividualFg)
                self.context_menu.actionAddCorrectIndividualFg.triggered.connect(self.add_correctindividualfg)
                self.context_menu.actionAddCorrectFgForStorage = QtGui.QAction(self)
                self.context_menu.actionAddCorrectFgForStorage.setText("CorrectFgForStorage")
                self.context_menu.addAction(self.context_menu.actionAddCorrectFgForStorage)
                self.context_menu.actionAddCorrectFgForStorage.triggered.connect(self.add_correctfgforstorage)
                #self.context_menu.actionCoordinateFluxGaps = QtGui.QAction(self)
                #self.context_menu.actionCoordinateFluxGaps.setText("CoordinateFluxGaps")
                #self.context_menu.addAction(self.context_menu.actionAddCoordinateFluxGaps)
                #self.context_menu.actionAddCoordinateFluxGaps.triggered.connect(self.add_coordinatefluxgaps)
                #self.context_menu.actionCoordinateAhFcGaps = QtGui.QAction(self)
                #self.context_menu.actionCoordinateAhFcGaps.setText("CoordinateAhFcGaps")
                #self.context_menu.addAction(self.context_menu.actionAddCoordinateAhFcGaps)
                #self.context_menu.actionAddCoordinateAhFcGaps.triggered.connect(self.add_coordinateahfcgaps)
            elif str(indexes[0].data().toString()) == "Variables":
                self.context_menu.actionAddVariable = QtGui.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
            elif str(indexes[0].data().toString()) == "Plots":
                self.context_menu.actionAddTimeSeries = QtGui.QAction(self)
                self.context_menu.actionAddTimeSeries.setText("Add time series")
                self.context_menu.addAction(self.context_menu.actionAddTimeSeries)
                self.context_menu.actionAddTimeSeries.triggered.connect(self.add_timeseries)
                self.context_menu.actionAddScatterPlot = QtGui.QAction(self)
                self.context_menu.actionAddScatterPlot.setText("Add scatter plot")
                self.context_menu.addAction(self.context_menu.actionAddScatterPlot)
                self.context_menu.actionAddScatterPlot.triggered.connect(self.add_scatterplot)
        elif level == 1:
            parent = str(indexes[0].parent().data().toString())
            if parent == "Files":
                # get the parent section
                for i in range(model.rowCount()):
                    section = model.item(i)
                    if str(section.text()) == parent:
                        break
                # get the key and value for the selected item
                for i in range(section.rowCount()):
                    key = str(section.child(i, 0).text())
                    val = str(section.child(i, 1).text())
                    if key == str(indexes[0].data().toString()):
                        return
                    if str(indexes[0].data().toString()) == val:
                        break
                # check to see if we have the selected subsection
                if key in ["file_path", "plot_path"]:
                    self.context_menu.actionBrowseFilePath = QtGui.QAction(self)
                    self.context_menu.actionBrowseFilePath.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                    self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                elif key == "in_filename":
                    self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                elif key == "out_filename":
                    self.context_menu.actionBrowseOutputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                else:
                    pass
            elif parent == "Options":
                self.context_menu.actionRemoveOption = QtGui.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove option")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_option)
            elif parent == "Variables":
                idx = indexes[0]
                # get the selected item from its index
                selected_item = idx.model().itemFromIndex(idx)
                # build a list of existing QC checks
                if selected_item.hasChildren():
                    existing_entries = []
                    for i in range(selected_item.rowCount()):
                        existing_entries.append(str(selected_item.child(i, 0).text()))
                # only put a QC check in the context menu if it is not already present
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtGui.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtGui.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                self.context_menu.addSeparator()
                if "MergeSeries" not in existing_entries:
                    self.context_menu.actionAddMergeSeries = QtGui.QAction(self)
                    self.context_menu.actionAddMergeSeries.setText("Add MergeSeries")
                    self.context_menu.addAction(self.context_menu.actionAddMergeSeries)
                    self.context_menu.actionAddMergeSeries.triggered.connect(self.add_mergeseries)
                if "AverageSeries" not in existing_entries:
                    self.context_menu.actionAddAverageSeries = QtGui.QAction(self)
                    self.context_menu.actionAddAverageSeries.setText("Add AverageSeries")
                    self.context_menu.addAction(self.context_menu.actionAddAverageSeries)
                    self.context_menu.actionAddAverageSeries.triggered.connect(self.add_averageseries)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveVariable = QtGui.QAction(self)
                self.context_menu.actionRemoveVariable.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveVariable)
                self.context_menu.actionRemoveVariable.triggered.connect(self.remove_variable)
            elif parent == "Plots":
                self.context_menu.actionRemovePlot = QtGui.QAction(self)
                self.context_menu.actionRemovePlot.setText("Remove plot")
                self.context_menu.addAction(self.context_menu.actionRemovePlot)
                self.context_menu.actionRemovePlot.triggered.connect(self.remove_plot)
        elif level == 2:
            parent = str(indexes[0].parent().data().toString())
            if str(indexes[0].data().toString()) in ["ExcludeDates"]:
                self.context_menu.actionAddExcludeDateRange = QtGui.QAction(self)
                self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                self.context_menu.addSeparator()
            self.context_menu.actionRemoveQCCheck = QtGui.QAction(self)
            self.context_menu.actionRemoveQCCheck.setText("Remove item")
            self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
            self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_qccheck)
        elif level == 3:
            parent = str(indexes[0].parent().data().toString())
            if parent in ["ExcludeDates"]:
                self.context_menu.actionRemoveExcludeDateRange = QtGui.QAction(self)
                self.context_menu.actionRemoveExcludeDateRange.setText("Remove date range")
                self.context_menu.addAction(self.context_menu.actionRemoveExcludeDateRange)
                self.context_menu.actionRemoveExcludeDateRange.triggered.connect(self.remove_excludedaterange)

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_usel2fluxes(self):
        """ Add UseL2Fluxes to the [Options] section."""
        child0 = QtGui.QStandardItem("UseL2Fluxes")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_2dcoordrotation(self):
        """ Add 2DCoordRotation to the [Options] section."""
        child0 = QtGui.QStandardItem("2DCoordRotation")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_massmancorrection(self):
        """ Add Massman correction to the [Options] section."""
        child0 = QtGui.QStandardItem("MassmanCorrection")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_applyfcstorage(self):
        """ Add storage term to Fc to the [Options] section."""
        child0 = QtGui.QStandardItem("ApplyFcStorage")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_correctindividualfg(self):
        """ Add correct individual Fg to the [Options] section."""
        child0 = QtGui.QStandardItem("CorrectIndividualFg")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_correctfgforstorage(self):
        """ Add correct Fg for storage to the [Options] section."""
        child0 = QtGui.QStandardItem("CorrectFgForStorage")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_fileentry(self):
        """ Add a new entry to the 'Files' section."""
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        self.tree.sections["Files"].appendRow([child0, child1])
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_variable(self):
        new_var_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        parent2 = QtGui.QStandardItem("New variable")
        for key3 in new_var_qc:
            parent3 = QtGui.QStandardItem(key3)
            for val in new_var_qc[key3]:
                value = new_var_qc[key3][val]
                child0 = QtGui.QStandardItem(val)
                child1 = QtGui.QStandardItem(str(value))
                parent3.appendRow([child0, child1])
            parent2.appendRow(parent3)
        self.tree.sections["Variables"].appendRow(parent2)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_timeseries(self):
        """ Add a new time series to the 'Plots' section."""
        new_plot = {"Variables":""}
        parent = QtGui.QStandardItem("New time series")
        for key in new_plot:
            value = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(value))
            parent.appendRow([child0, child1])
        self.tree.sections["Plots"].appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_scatterplot(self):
        """ Add a new scatter plot to the 'Plots' section."""
        new_plot = {"Type":"xy","Title":"", "XSeries":"[]", "YSeries":"[]"}
        parent = QtGui.QStandardItem("New scatter plot")
        for key in new_plot:
            value = new_plot[key]
            child0 = QtGui.QStandardItem(key)
            child1 = QtGui.QStandardItem(str(value))
            parent.appendRow([child0, child1])
        self.tree.sections["Plots"].appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_averageseries(self):
        """ Add an average series instruction to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        parent = QtGui.QStandardItem("AverageSeries")
        child0 = QtGui.QStandardItem("Source")
        child1 = QtGui.QStandardItem("[]")
        parent.appendRow([child0, child1])
        subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_mergeseries(self):
        """ Add a merge series instruction to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        parent = QtGui.QStandardItem("MergeSeries")
        child0 = QtGui.QStandardItem("Source")
        child1 = QtGui.QStandardItem("[]")
        parent.appendRow([child0, child1])
        subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"DependencyCheck":{"Source":"[]"}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"DiurnalCheck":{"NumSd":"5"}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        new_qc = {"ExcludeDates":{"0":"[YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM]"}}
        # get the parent section
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Variables":
                break
        # loop over all children in the "Variables" section
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(indexes[0].data().toString()):
                break
        for key1 in new_qc:
            parent = QtGui.QStandardItem(key1)
            for key2 in new_qc[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(new_qc[key1][key2]))
                parent.appendRow([child0, child1])
            subsection.appendRow(parent)
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_excludedaterange(self):
        """ Add another date range to the ExcludeDates QC check."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            for i in range(section.rowCount()):
                subsection = section.child(i)
                if str(subsection.text()) == str(idx.parent().data().toString()):
                    break
            for i in range(subsection.rowCount()):
                subsubsection = subsection.child(i)
                if str(subsubsection.text()) == str(idx.data().toString()):
                    break
            child0 = QtGui.QStandardItem(str(subsubsection.rowCount()))
            child1 = QtGui.QStandardItem("[YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM]")
            subsubsection.appendRow([child0, child1])

    def browse_file_path(self):
        """ Browse for the data file path."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the section containing the selected item
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Files":
                break
        # get the key and value of the selected item
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(indexes[0].data().toString()) == val:
                break
        # dialog for new directory
        new_dir = QtGui.QFileDialog.getExistingDirectory(self, "Open a folder", val, QtGui.QFileDialog.ShowDirsOnly)
        new_dir = os.path.join(str(new_dir), "")
        # update the model
        if len(str(new_dir)) > 0:
            section.child(i,1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                          directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the section containing the selected item
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == "Files":
                break
        # get the key and value of the file path
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if key == "file_path":
                file_path = val
                break
        # get the key and value of the selected item
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(indexes[0].data().toString()) == val:
                break
        # dialog for open file
        new_file = QtGui.QFileDialog.getOpenFileName(caption="Choose an output file ...", directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file)) > 0:
            section.child(i,1).setText(new_file)

    def correct_legacy_variable_names(self):
        """ Correct some legacy variable names."""
        # change Fn_KZ to Fn_4cmpt
        opt = pfp_utils.get_keyvaluefromcf(self.cfg_mod, ["Variables", "Fn", "MergeSeries"],
                                           "Source", default="", mode="quiet")
        if len(opt) != 0:
            if "Fn_KZ" in opt:
                opt = opt.replace("Fn_KZ", "Fn_4cmpt")
                self.cfg_mod["Variables"]["Fn"]["MergeSeries"]["Source"] = opt
                self.cfg_changed = True
        return

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

    def get_section_from_text(self, model, section_name):
        """ Gets a section from a model by matching the section name."""
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == str(section_name):
                break
        return section, i

    def parse_cfg_plots_title(self, key1, key2):
        """ Parse the [Plots] section for a title."""
        if "Title" in self.cfg_mod[key1][key2]:
            title = self.cfg_mod[key1][key2]["Title"]
            del self.cfg_mod[key1][key2]["Title"]
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
        if k == "Variables":
            if ("[" in v) and ("]" in v):
                v = v.replace("[", "").replace("]", "")
                self.cfg_changed = True
        strip_list = [" ", '"', "'"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def parse_cfg_values(self, k, v, strip_list):
        """ Parse key values to remove unnecessary characters."""
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
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
                 "MergeSeries", "AverageSeries"]:
            strip_list = [" ", '"', "'"]
        elif k in ["ExcludeDates", "ExcludeHours", "Linear"]:
            # don't remove white space between date and time
            strip_list = ['"', "'"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def remove_variable(self):
        """ Remove a variable."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            # loop over all children in the "Variables" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.data().toString()):
                    # if so, remove the row
                    section.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def remove_option(self):
        """ Remove an option."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Options":
                    break
            # loop over all children in the "Plots" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.data().toString()):
                    # if so, remove the row
                    section.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def remove_plot(self):
        """ Remove a plot."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Plots":
                    break
            # loop over all children in the "Plots" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.data().toString()):
                    # if so, remove the row
                    section.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

    def remove_qccheck(self):
        """ Remove a QC check."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            # loop over all children in the "Variables" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == parent:
                    for j in range(subsection.rowCount()):
                        subsubsection = subsection.child(j)
                        if str(subsubsection.text()) == str(idx.data().toString()):
                            # if so, remove the row
                            subsection.removeRow(j)
                            # add an asterisk to the tab text to indicate the tab contents have changed
                            tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                            if "*" not in tab_text:
                                self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                            break

    def remove_excludedaterange(self):
        """ Remove an ExcludeDates date range."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the top level section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "Variables":
                    break
            # loop over all children in the "Variables" section
            for i in range(section.rowCount()):
                # get the child subsection
                subsection = section.child(i)
                # check to see if we have the selected subsection
                if str(subsection.text()) == str(idx.parent().parent().data().toString()):
                    break
            # loop over all QC checks in this variable
            for i in range(subsection.rowCount()):
                subsubsection = subsection.child(i)
                if str(subsubsection.text()) == str(idx.parent().data().toString()):
                    break
            # loop over all date ranges in the ExcludeDates QC check
            for i in range(subsubsection.rowCount()):
                subsubsubsection = subsubsection.child(i)
                if str(subsubsubsection.text()) == str(idx.data().toString()):
                    subsubsection.removeRow(i)
                    # add an asterisk to the tab text to indicate the tab contents have changed
                    tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
                    if "*" not in tab_text:
                        self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
                    break

class edit_cfg_concatenate(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_concatenate, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False
        self.tabs = main_gui.tabs

        self.edit_concatenate_gui()

    def edit_concatenate_gui(self):
        """ Edit a concatenate control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.context_menu)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        # build the model
        self.get_model_from_data()

    def get_model_from_data(self):
        """ Build the data model."""
        self.tree.setModel(QtGui.QStandardItemModel())
        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.tree.model().itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.tree.sections = {}
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Options"]:
                # sections with only 1 level
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    val = self.cfg_mod[key1][key2]
                    val = self.parse_cfg_values(key2, val, ["[","]",'"', "'"])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(str(val))
                    self.tree.sections[key1].appendRow([child0, child1])
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["Files"]:
                # sections with 2 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for val in self.cfg_mod[key1][key2]:
                        value = self.cfg_mod[key1][key2][val]
                        child0 = QtGui.QStandardItem(val)
                        child1 = QtGui.QStandardItem(str(value))
                        parent2.appendRow([child0, child1])
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = self.cfg_mod
        model = self.tree.model()
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
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def context_menu(self, position):
        """ Right click context menu."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        self.context_menu = QtGui.QMenu()
        if level == 0:
            # sections with only 1 level
            if str(indexes[0].data().toString()) == "Options":
                options = {"NumberOfDimensions":3, "MaxGapInterpolate": 3, "FixTimeStepMethod": "round",
                           "Truncate": "Yes", "TruncateThreshold": 50,
                           "SeriesToCheck":['Ah','Cc','Fa','Fg','Fld','Flu','Fn','Fsd','Fsu','ps','Sws',
                                            'Ta','Ts','Ws','Wd','Precip']}
                self.context_menu.actionAddNumberOfDimensions = QtGui.QAction(self)
                self.context_menu.actionAddNumberOfDimensions.setText("NumberOfDimensions")
                self.context_menu.addAction(self.context_menu.actionAddNumberOfDimensions)
                self.context_menu.actionAddNumberOfDimensions.triggered.connect(self.add_numberofdimensions)
                self.context_menu.actionAddMaxGapInterpolate = QtGui.QAction(self)
                self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
                self.context_menu.actionAddFixTimeStepMethod = QtGui.QAction(self)
                self.context_menu.actionAddFixTimeStepMethod.setText("FixTimeStepMethod")
                self.context_menu.addAction(self.context_menu.actionAddFixTimeStepMethod)
                self.context_menu.actionAddFixTimeStepMethod.triggered.connect(self.add_fixtimestepmethod)
                self.context_menu.actionAddTruncate = QtGui.QAction(self)
                self.context_menu.actionAddTruncate.setText("Truncate")
                self.context_menu.addAction(self.context_menu.actionAddTruncate)
                self.context_menu.actionAddTruncate.triggered.connect(self.add_truncate)
                self.context_menu.actionAddTruncateThreshold = QtGui.QAction(self)
                self.context_menu.actionAddTruncateThreshold.setText("TruncateThreshold")
                self.context_menu.addAction(self.context_menu.actionAddTruncateThreshold)
                self.context_menu.actionAddTruncateThreshold.triggered.connect(self.add_truncatethreshold)
                self.context_menu.actionAddSeriesToCheck = QtGui.QAction(self)
                self.context_menu.actionAddSeriesToCheck.setText("SeriesToCheck")
                self.context_menu.addAction(self.context_menu.actionAddSeriesToCheck)
                self.context_menu.actionAddSeriesToCheck.triggered.connect(self.add_seriestocheck)
        elif level == 1:
            parent = str(indexes[0].parent().data().toString())
            if parent == "Options":
                self.context_menu.actionRemoveOption = QtGui.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove option")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_option)
            elif parent == "Files":
                if str(indexes[0].data().toString()) == "In":
                    self.context_menu.actionAddInputFile = QtGui.QAction(self)
                    self.context_menu.actionAddInputFile.setText("Add input file")
                    self.context_menu.addAction(self.context_menu.actionAddInputFile)
                    self.context_menu.actionAddInputFile.triggered.connect(self.add_inputfile)
        elif level == 2:
            section_name = str(indexes[0].parent().parent().data().toString())
            subsection_name = str(indexes[0].parent().data().toString())
            section, i = self.get_section(section_name)
            subsection, j = self.get_subsection(section, indexes[0])
            if ((section_name == "Files") and (subsection_name == "In")):
                if (self.selection_is_key(subsection, indexes[0])):
                    self.context_menu.actionRemoveInputFile = QtGui.QAction(self)
                    self.context_menu.actionRemoveInputFile.setText("Remove file")
                    self.context_menu.addAction(self.context_menu.actionRemoveInputFile)
                    self.context_menu.actionRemoveInputFile.triggered.connect(self.remove_inputfile)
                elif (self.selection_is_value(subsection, indexes[0])):
                    self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseInputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                    self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
            elif section_name == "Files" and subsection_name == "Out":
                # get the section named "Files"
                section, i = self.get_section(section_name)
                # get the subsection named "Out"
                subsection, i = self.get_subsection(section, indexes[0].parent())
                # get the key, value and found logical for the selected item
                key, val, found = self.get_keyval_by_key_name(subsection, "ncFileName")
                # check to see if we have the selected subsection
                if found:
                    self.context_menu.actionBrowseOutputFile = QtGui.QAction(self)
                    self.context_menu.actionBrowseOutputFile.setText("Browse...")
                    self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                    self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
        elif level == 3:
            pass

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

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
            if str(subsection.text()) == str(idx.data().toString()):
                break
        return subsection, i

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
        return key_child, val_child, found

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

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

    def add_inputfile(self):
        """ Add an entry for a new input file."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the parent section
            section, i = self.get_section("Files")
            subsection, j = self.get_subsection(section, idx)
            child0 = QtGui.QStandardItem(str(subsection.rowCount()))
            child1 = QtGui.QStandardItem("")
            subsection.appendRow([child0, child1])

    def add_option(self, key, val):
        """ Add an option to the context menu."""
        # add the option to the [Options] section
        child0 = QtGui.QStandardItem(key)
        child1 = QtGui.QStandardItem(val)
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_numberofdimensions(self):
        """ Add the NumberOfDimensions option to the context menu."""
        # add the option to the [Options] section
        child0 = QtGui.QStandardItem("NumberOfDimensions")
        child1 = QtGui.QStandardItem("3")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_maxgapinterpolate(self):
        """ Add the MaxGapInterpolate option to the context menu."""
        # add the option to the [Options] section
        child0 = QtGui.QStandardItem("MaxGapInterpolate")
        child1 = QtGui.QStandardItem("3")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_fixtimestepmethod(self):
        """ Add the FixTimeStepMethod option to the context menu."""
        # add the option to the [Options] section
        child0 = QtGui.QStandardItem("FixTimeStepMethod")
        child1 = QtGui.QStandardItem("round")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_truncate(self):
        """ Add the Truncate option to the context menu."""
        # add the option to the [Options] section
        child0 = QtGui.QStandardItem("Truncate")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_truncatethreshold(self):
        """ Add the TruncateThreshold option to the context menu."""
        # add the option to the [Options] section
        child0 = QtGui.QStandardItem("TruncateThreshold")
        child1 = QtGui.QStandardItem("50")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_seriestocheck(self):
        """ Add the SeriesToCheck option to the context menu."""
        # add the option to the [Options] section
        child0 = QtGui.QStandardItem("SeriesToCheck")
        child1 = QtGui.QStandardItem("['Ah','Cc','Fa','Fg','Fld','Flu','Fn','Fsd','Fsu','ps','Sws','Ta','Ts','Ws','Wd','Precip']")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def browse_input_file(self):
        """ Browse for the input data file path."""
        #model = self.tree.model()
        #indexes = self.tree.selectedIndexes()
        ## get the section containing the selected item
        #section, i = self.get_section("Files")
        #subsection, j = self.get_subsection(section, indexes[0].parent())
        #subsubsection, k = self.get_subsection(subsection, indexes[0])
        #file_path = os.path.expanduser("~")
        #if subsection.rowCount() > 1:
            ## get the existing value of the ncFileName key
            #key, val, found = self.get_keyval_by_key_name(subsection, str(subsection.rowCount()-2))
            #if found:
                #file_path = os.path.split(val)[0]

        idx = self.tree.selectedIndexes()[0]
        item = idx.model().itemFromIndex(idx)
        parent = item.parent()
        val = str(parent.child(item.row(), 1).text())
        file_path = os.path.split(val)[0]
        # dialog for open file
        file_path = os.path.join(file_path, "")
        new_file = QtGui.QFileDialog.getOpenFileName(caption="Choose an input file ...", directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file)) > 0:
            parent.child(item.row(), 1).setText(new_file)

    def browse_output_file(self):
        """ Browse for the output data file path."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        # get the section containing the selected item
        section, i = self.get_section("Files")
        subsection, i = self.get_subsection(section, indexes[0].parent())
        # get the existing value of the ncFileName key
        key, val, found = self.get_keyval_by_key_name(subsection, "ncFileName")
        if not found: return
        # get the path
        file_path = os.path.split(val)
        # dialog for open file
        new_file = QtGui.QFileDialog.getOpenFileName(caption="Choose an output file ...", directory=file_path[0], filter="*.nc")
        # update the model
        if len(str(new_file)) > 0:
            subsection.child(i, 1).setText(new_file)

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

    def selection_is_key(self, section, idx):
        """ Return True if the selected item is a key."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == key:
                result = True
                break
        return result

    def selection_is_value(self, section, idx):
        """ Return True if the selected item is a value."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == val:
                result = True
                break
        return result

    def renumber_subsection_keys(self, subsection):
        """ Renumber the subsection keys when an item is removed."""
        for i in range(subsection.rowCount()):
            child = subsection.child(i)
            child.setText(str(i))
        return

class edit_cfg_L4(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L4, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_l4_gui()

    def edit_l4_gui(self):
        """ Edit an L4 control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.context_menu)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.tree.setModel(QtGui.QStandardItemModel())
        #self.tree.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # build the model
        self.get_model_from_data()

    def get_model_from_data(self):
        """ Build the data model."""
        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.tree.model().itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.tree.sections = {}
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Options"]:
                # sections with only 1 level
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    val = self.cfg_mod[key1][key2]
                    val = self.parse_cfg_values(key2, val, ['"', "'"])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(str(val))
                    self.tree.sections[key1].appendRow([child0, child1])
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["Drivers"]:
                # sections with 4 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                # key2 is the variable name
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    # key3 is the gap filling method
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        if key3 in ["GapFillFromAlternate", "GapFillFromClimatology"]:
                            # key4 is the altyernate variable name
                            for key4 in self.cfg_mod[key1][key2][key3]:
                                parent4 = QtGui.QStandardItem(key4)
                                # key5 is the source of the alternate data
                                for key5 in self.cfg_mod[key1][key2][key3][key4]:
                                    val = self.cfg_mod[key1][key2][key3][key4][key5]
                                    val = self.parse_cfg_values(key5, val, ['"', "'"])
                                    child0 = QtGui.QStandardItem(key5)
                                    child1 = QtGui.QStandardItem(val)
                                    parent4.appendRow([child0, child1])
                                parent3.appendRow(parent4)
                        elif key3 in ["MergeSeries", "RangeCheck", "ExcludeDates"]:
                            for key4 in self.cfg_mod[key1][key2][key3]:
                                val = self.cfg_mod[key1][key2][key3][key4]
                                val = self.parse_cfg_variables_value(key3, val)
                                child0 = QtGui.QStandardItem(key4)
                                child1 = QtGui.QStandardItem(val)
                                parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = self.cfg_mod
        model = self.tree.model()
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
                        # subsubsections are GapFillFromAlternate, GapFillFromClimatology
                        # MergeSeries
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
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def context_menu(self, position):
        """ Right click context menu."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        self.context_menu = QtGui.QMenu()
        level = self.get_level_selected_item()
        if level == 0:
            # sections with only 1 level
            if str(indexes[0].data().toString()) == "Files":
                self.context_menu.actionAddFileEntry = QtGui.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif str(indexes[0].data().toString()) == "Output":
                pass
            elif str(indexes[0].data().toString()) == "Options":
                self.context_menu.actionAddMaxGapInterpolate = QtGui.QAction(self)
                self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
            elif str(indexes[0].data().toString()) in ["Drivers"]:
                self.context_menu.actionAddVariable = QtGui.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
        elif level == 1:
            # sections with 2 levels
            section_name = str(indexes[0].parent().data().toString())
            section, i = self.get_section_from_text(model, section_name)
            if (section_name == "Files"):
                if (self.selection_is_key(section, indexes[0])):
                    self.context_menu.actionRemoveInputFile = QtGui.QAction(self)
                    self.context_menu.actionRemoveInputFile.setText("Remove item")
                    self.context_menu.addAction(self.context_menu.actionRemoveInputFile)
                    self.context_menu.actionRemoveInputFile.triggered.connect(self.remove_item_files)
                elif (self.selection_is_value(section, indexes[0])):
                    key, val, found, i = self.get_keyval_by_val_name(section, indexes[0].data().toString())
                    if key in ["file_path", "plot_path"]:
                        self.context_menu.actionBrowseFilePath = QtGui.QAction(self)
                        self.context_menu.actionBrowseFilePath.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                        self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                    elif key in ["in_filename"]:
                        self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseInputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                        self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                    elif key in ["out_filename"]:
                        self.context_menu.actionBrowseOutputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseOutputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                        self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                    elif key in ["aws", "access", "climatology", "erai"]:
                        self.context_menu.actionBrowseAlternateFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseAlternateFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseAlternateFile)
                        self.context_menu.actionBrowseAlternateFile.triggered.connect(self.browse_alternate_file)
                    else:
                        self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseInputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                        self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
            elif (section_name == "Options"):
                if (self.selection_is_key(section, indexes[0])):
                    self.context_menu.actionRemoveOption = QtGui.QAction(self)
                    self.context_menu.actionRemoveOption.setText("Remove option")
                    self.context_menu.addAction(self.context_menu.actionRemoveOption)
                    self.context_menu.actionRemoveOption.triggered.connect(self.remove_item_options)
            elif (section_name in ["Drivers"]):
                idx = indexes[0]
                # get the selected item from its index
                selected_item = idx.model().itemFromIndex(idx)
                # build a list of existing QC checks
                if selected_item.hasChildren():
                    existing_entries = []
                    for i in range(selected_item.rowCount()):
                        existing_entries.append(str(selected_item.child(i, 0).text()))
                # only put a QC check in the context menu if it is not already present
                if "GapFillFromAlternate" not in existing_entries:
                    self.context_menu.actionAddAlternate = QtGui.QAction(self)
                    self.context_menu.actionAddAlternate.setText("Add Alternate")
                    self.context_menu.addAction(self.context_menu.actionAddAlternate)
                    self.context_menu.actionAddAlternate.triggered.connect(self.add_alternate)
                if "GapFillUsingMDS" not in existing_entries:
                    self.context_menu.actionAddMDS = QtGui.QAction(self)
                    self.context_menu.actionAddMDS.setText("Add MDS")
                    self.context_menu.addAction(self.context_menu.actionAddMDS)
                    self.context_menu.actionAddMDS.triggered.connect(self.add_MDS)
                if "GapFillFromClimatology" not in existing_entries:
                    self.context_menu.actionAddClimatology = QtGui.QAction(self)
                    self.context_menu.actionAddClimatology.setText("Add Climatology")
                    self.context_menu.addAction(self.context_menu.actionAddClimatology)
                    self.context_menu.actionAddClimatology.triggered.connect(self.add_climatology)
                self.context_menu.addSeparator()
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtGui.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtGui.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveOption = QtGui.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_variable)
        elif level == 2:
            # sections with 3 levels
            section_name = str(indexes[0].parent().parent().data().toString())
            subsection_name = str(indexes[0].parent().data().toString())
            subsubsection_name = str(indexes[0].data().toString())
            #if str(indexes[0].data().toString()) in ["ExcludeDates"]:
                #self.context_menu.actionAddExcludeDateRange = QtGui.QAction(self)
                #self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                #self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                #self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                #self.context_menu.addSeparator()
            if subsubsection_name in ["RangeCheck", "DependencyCheck", "DiurnalCheck", "ExcludeDates"]:
                self.context_menu.actionRemoveQCCheck = QtGui.QAction(self)
                self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
                self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
                self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_qc_check)
            elif subsubsection_name in ["GapFillFromAlternate", "GapFillUsingMDS", "GapFillFromClimatology"]:
                if subsubsection_name == "GapFillFromAlternate":
                    self.context_menu.actionAddMoreAlternate = QtGui.QAction(self)
                    self.context_menu.actionAddMoreAlternate.setText("Add Alternate")
                    self.context_menu.addAction(self.context_menu.actionAddMoreAlternate)
                    self.context_menu.actionAddMoreAlternate.triggered.connect(self.add_more_alternate)
                self.context_menu.actionRemoveGFMethod = QtGui.QAction(self)
                self.context_menu.actionRemoveGFMethod.setText("Remove method")
                self.context_menu.addAction(self.context_menu.actionRemoveGFMethod)
                self.context_menu.actionRemoveGFMethod.triggered.connect(self.remove_gf_method)
        elif level == 3:
            # sections with 4 levels
            section_name = str(indexes[0].parent().parent().parent().data().toString())
            subsection_name = str(indexes[0].parent().parent().data().toString())
            subsubsection_name = str(indexes[0].parent().data().toString())
            subsubsubsection_name = str(indexes[0].data().toString())
            self.context_menu.actionRemoveGFMethodVariable = QtGui.QAction(self)
            self.context_menu.actionRemoveGFMethodVariable.setText("Remove variable")
            self.context_menu.addAction(self.context_menu.actionRemoveGFMethodVariable)
            self.context_menu.actionRemoveGFMethodVariable.triggered.connect(self.remove_gf_method_variable)

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_alternate(self):
        """ Add GapFillFromAlternate to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"GapFillFromAlternate":{"<var_alt>": {"source": "<alt>"}}}
        # get the parent and sub section text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_climatology(self):
        """ Add GapFillFromClimatology to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"GapFillFromClimatology":{"<var>_cli": {"method": "interpolated daily"}}}
        # get the parent and sub section text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"DependencyCheck":{"Source":"[]"}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"DiurnalCheck":{"NumSd":"5"}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"ExcludeDates":{"0":"[YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM]"}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_fileentry(self):
        """ Add a new entry to the [Files] section."""
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        self.tree.sections["Files"].appendRow([child0, child1])
        self.update_tab_text()

    def add_maxgapinterpolate(self):
        """ Add MaxGapInterpolate to the [Options] section."""
        child0 = QtGui.QStandardItem("MaxGapInterpolate")
        child1 = QtGui.QStandardItem("3")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_MDS(self):
        """ Add GapFillUsingMDS to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"GapFillUsingMDS":{"<var>_MDS": {"source": "MDS"}}}
        # get the parent and sub section text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (MDS)
        self.add_subsubsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_more_alternate(self):
        """ Add another alternate source to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"<var_alt>": {"source": "<alt>"}}
        # get the parents text
        subsubsection_text = str(idx.data().toString())
        subsection_text = str(idx.parent().data().toString())
        section_text = str(idx.parent().parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsubsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_subsubsection(self, subsection, dict_to_add):
        """ Add a subsubsection to the model."""
        for key1 in dict_to_add:
            subsubsection = QtGui.QStandardItem(key1)
            for key2 in dict_to_add[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(dict_to_add[key1][key2]))
                subsubsection.appendRow([child0, child1])
            subsection.appendRow(subsubsection)

    def add_subsubsubsection(self, subsection, dict_to_add):
        """ Add a subsubsubsection to the model."""
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

    def add_variable(self):
        """ Add a variable."""
        dict_to_add = {"GapFillFromAlternate":{"<var_alt>": {"source": "<alt>"}},
                       "GapFillUsingMDS":{"<var>_MDS":{"source":"MDS"}},
                       "GapFillFromClimatology":{"<var>_cli":{"method":"interpolated daily"}}}
        subsection = QtGui.QStandardItem("New variable")
        self.add_subsubsubsection(subsection, dict_to_add)
        dict_to_add = {"MergeSeries":{"Source":"[]"}}
        self.add_subsubsection(subsection, dict_to_add)
        self.tree.sections["Drivers"].appendRow(subsection)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def browse_alternate_file(self):
        """ Browse for the alternate data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the key and value of the selected item
        key, val, found, i = self.get_keyval_by_val_name(section, str(idx.data().toString()))
        # set the file filter
        file_filter = "*.nc"
        if str(key) in ["climatology"]:
            file_filter = "*.xls"
        # get the file path from the selected item
        file_path = os.path.split(str(idx.data().toString()))[0]
        file_path = os.path.join(file_path,"")
        # dialog for open file
        file_path = os.path.join(file_path, "")
        new_file = QtGui.QFileDialog.getOpenFileName(caption="Choose an alternate data file ...", directory=file_path, filter=file_filter)
        # update the model
        if len(str(new_file)) > 0:
            section.child(i, 1).setText(new_file)

    def browse_file_path(self):
        """ Browse for the data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the key and value of the selected item
        key, val, found, j = self.get_keyval_by_val_name(section, str(idx.data().toString()))
        # dialog for new directory
        new_dir = QtGui.QFileDialog.getExistingDirectory(self, "Open a folder", val, QtGui.QFileDialog.ShowDirsOnly)
        new_dir = os.path.join(str(new_dir), "")
        # update the model
        if len(str(new_dir)) > 0:
            section.child(j, 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                          directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                          directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

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
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        return level

    def get_section_from_text(self, model, section_name):
        """ Gets a section from a model by matching the section name."""
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == str(section_name):
                break
        return section, i

    def get_subsection_from_index(self, section, idx):
        """ Gets a subsection from a model by matching the subsection name."""
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(idx.data().toString()):
                break
        return subsection, i

    def get_subsection_from_text(self, section, text):
        """ Gets a subsection from a model by matching the subsection name"""
        for i in range(section.rowCount()):
            subsection = section.child(i)
            if str(subsection.text()) == text:
                break
        return subsection, i

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

    def remove_item_files(self):
        """ Remove an item from the Files section."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            section_text = str(idx.parent().data().toString())
            subsection_text = str(idx.data().toString())
            # get the top level section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the subsection within the top level section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # remove it
            section.removeRow(j)
            self.update_tab_text()

    def remove_qc_check(self):
        """ Remove a QC check."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            subsubsection_text = str(idx.data().toString())
            subsection_text = str(idx.parent().data().toString())
            section_text = str(idx.parent().parent().data().toString())
            # get the [Variables] section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the variable section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # get the gap filling method section
            subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
            subsection.removeRow(k)
            self.update_tab_text()

    def remove_gf_method(self):
        """ Remove a gap filling method."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            subsubsection_text = str(idx.data().toString())
            subsection_text = str(idx.parent().data().toString())
            section_text = str(idx.parent().parent().data().toString())
            # get the [Variables] section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the variable section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # get the gap filling method section
            subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
            subsection.removeRow(k)
            self.update_tab_text()

    def remove_gf_method_variable(self):
        """ Remove a gap filling method variable."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the parents text
            subsubsubsection_text = str(idx.data().toString())
            subsubsection_text = str(idx.parent().data().toString())
            subsection_text = str(idx.parent().parent().data().toString())
            section_text = str(idx.parent().parent().parent().data().toString())
            # get the [Variables] section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the variable section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # get the gap filling method section
            subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
            # get the variable gap fill method section
            subsubsubsection, l = self.get_subsection_from_text(subsubsection, subsubsubsection_text)
            subsubsection.removeRow(l)
            self.update_tab_text()

    def remove_item_options(self):
        """ Remove an item from the Options section."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            section_text = str(idx.parent().data().toString())
            subsection_text = str(idx.data().toString())
            # get the "Options" section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            section.removeRow(j)
            self.update_tab_text()

    def remove_variable(self):
        """ Remove a variable."""
        for idx in self.tree.selectedIndexes():
            # get the parents text
            subsection_text = str(idx.data().toString())
            section_text = str(idx.parent().data().toString())
            # get the "Drivers" section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            section.removeRow(j)
            self.update_tab_text()

    def selection_is_key(self, section, idx):
        """ Return True if the selected item is a key."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == key:
                result = True
                break
        return result

    def selection_is_value(self, section, idx):
        """ Return True if the selected item is a value."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == val:
                result = True
                break
        return result

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L5(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L5, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_l5_gui()

    def edit_l5_gui(self):
        """ Edit an L5 control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.context_menu)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        # build the model
        self.get_model_from_data()

    def get_model_from_data(self):
        """ Build the data model."""
        self.tree.setModel(QtGui.QStandardItemModel())
        #self.tree.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.tree.model().itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.tree.sections = {}
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Options", "ustar_threshold"]:
                # sections with only 1 level
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    val = self.cfg_mod[key1][key2]
                    val = self.parse_cfg_values(key2, val, ["[", "]", "'", '"'])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.tree.sections[key1].appendRow([child0, child1])
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["Fluxes", "Variables"]:
                # sections with 4 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        if key3 in ["GapFillUsingSOLO", "GapFillUsingMDS"]:
                            for key4 in self.cfg_mod[key1][key2][key3]:
                                parent4 = QtGui.QStandardItem(key4)
                                for key5 in self.cfg_mod[key1][key2][key3][key4]:
                                    val = self.cfg_mod[key1][key2][key3][key4][key5]
                                    val = self.parse_cfg_values(key5, val, ["[", "]", "'", '"'])
                                    child0 = QtGui.QStandardItem(key5)
                                    child1 = QtGui.QStandardItem(val)
                                    parent4.appendRow([child0, child1])
                                parent3.appendRow(parent4)
                        elif key3 in ["MergeSeries", "RangeCheck", "ExcludeDates"]:
                            for key4 in self.cfg_mod[key1][key2][key3]:
                                val = self.cfg_mod[key1][key2][key3][key4]
                                val = self.parse_cfg_variables_value(key3, val)
                                child0 = QtGui.QStandardItem(key4)
                                child1 = QtGui.QStandardItem(val)
                                parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = self.cfg_mod
        model = self.tree.model()
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
                        if key3 in ["GapFillUsingSOLO", "GapFillUsingMDS"]:
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
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def context_menu(self, position):
        """ Right click context menu."""
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        self.context_menu = QtGui.QMenu()
        level = self.get_level_selected_item()
        if level == 0:
            # sections with only 1 level
            if str(indexes[0].data().toString()) == "Files":
                self.context_menu.actionAddFileEntry = QtGui.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif str(indexes[0].data().toString()) == "Output":
                pass
            elif str(indexes[0].data().toString()) == "Options":
                idx = indexes[0]
                # get the selected item from its index
                selected_item = idx.model().itemFromIndex(idx)
                # build a list of existing QC checks
                if selected_item.hasChildren():
                    existing_entries = []
                    for i in range(selected_item.rowCount()):
                        existing_entries.append(str(selected_item.child(i, 0).text()))
                # only put a QC check in the context menu if it is not already present
                if "MaxGapInterpolate" not in existing_entries:
                    self.context_menu.actionAddMaxGapInterpolate = QtGui.QAction(self)
                    self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                    self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                    self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
                if "FilterList" not in existing_entries:
                    self.context_menu.actionAddFilterList = QtGui.QAction(self)
                    self.context_menu.actionAddFilterList.setText("FilterList")
                    self.context_menu.addAction(self.context_menu.actionAddFilterList)
                    self.context_menu.actionAddFilterList.triggered.connect(self.add_filterlist)
                if "TurbulenceFilter" not in existing_entries:
                    self.context_menu.actionAddTurbulenceFilter = QtGui.QAction(self)
                    self.context_menu.actionAddTurbulenceFilter.setText("TurbulenceFilter")
                    self.context_menu.addAction(self.context_menu.actionAddTurbulenceFilter)
                    self.context_menu.actionAddTurbulenceFilter.triggered.connect(self.add_turbulencefilter)
                if "DayNightFilter" not in existing_entries:
                    self.context_menu.actionAddDayNightFilter = QtGui.QAction(self)
                    self.context_menu.actionAddDayNightFilter.setText("DayNightFilter")
                    self.context_menu.addAction(self.context_menu.actionAddDayNightFilter)
                    self.context_menu.actionAddDayNightFilter.triggered.connect(self.add_daynightfilter)
                if "UseFsdsyn_threshold" not in existing_entries:
                    self.context_menu.actionAddUseFsdsyn_threshold = QtGui.QAction(self)
                    self.context_menu.actionAddUseFsdsyn_threshold.setText("UseFsdsyn_threshold")
                    self.context_menu.addAction(self.context_menu.actionAddUseFsdsyn_threshold)
                    self.context_menu.actionAddUseFsdsyn_threshold.triggered.connect(self.add_usefsdsynthreshold)
                if "AcceptDayTimes" not in existing_entries:
                    self.context_menu.actionAddAcceptDayTimes = QtGui.QAction(self)
                    self.context_menu.actionAddAcceptDayTimes.setText("AcceptDayTimes")
                    self.context_menu.addAction(self.context_menu.actionAddAcceptDayTimes)
                    self.context_menu.actionAddAcceptDayTimes.triggered.connect(self.add_acceptdaytimes)
                if "UseEveningFilter" not in existing_entries:
                    self.context_menu.actionAddUseEveningFilter = QtGui.QAction(self)
                    self.context_menu.actionAddUseEveningFilter.setText("UseEveningFilter")
                    self.context_menu.addAction(self.context_menu.actionAddUseEveningFilter)
                    self.context_menu.actionAddUseEveningFilter.triggered.connect(self.add_useeveningfilter)
                if "EveningFilterLength" not in existing_entries:
                    self.context_menu.actionAddEveningFilterLength = QtGui.QAction(self)
                    self.context_menu.actionAddEveningFilterLength.setText("EveningFilterLength")
                    self.context_menu.addAction(self.context_menu.actionAddEveningFilterLength)
                    self.context_menu.actionAddEveningFilterLength.triggered.connect(self.add_eveningfilterlength)
                if "Fsd_threshold" not in existing_entries:
                    self.context_menu.actionAddFsd_threshold = QtGui.QAction(self)
                    self.context_menu.actionAddFsd_threshold.setText("Fsd_threshold")
                    self.context_menu.addAction(self.context_menu.actionAddFsd_threshold)
                    self.context_menu.actionAddFsd_threshold.triggered.connect(self.add_fsdthreshold)
                if "sa_threshold" not in existing_entries:
                    self.context_menu.actionAddsa_threshold = QtGui.QAction(self)
                    self.context_menu.actionAddsa_threshold.setText("sa_threshold")
                    self.context_menu.addAction(self.context_menu.actionAddsa_threshold)
                    self.context_menu.actionAddsa_threshold.triggered.connect(self.add_sathreshold)
            elif str(indexes[0].data().toString()) in ["Fluxes", "Variables"]:
                self.context_menu.actionAddVariable = QtGui.QAction(self)
                self.context_menu.actionAddVariable.setText("Add variable")
                self.context_menu.addAction(self.context_menu.actionAddVariable)
                self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
            elif str(indexes[0].data().toString()) in ["ustar_threshold"]:
                self.context_menu.actionAddUstarThreshold = QtGui.QAction(self)
                self.context_menu.actionAddUstarThreshold.setText("Add year")
                self.context_menu.addAction(self.context_menu.actionAddUstarThreshold)
                self.context_menu.actionAddUstarThreshold.triggered.connect(self.add_ustar_threshold)
        elif level == 1:
            # sections with 2 levels
            section_name = str(indexes[0].parent().data().toString())
            section, i = self.get_section_from_text(model, section_name)
            if (section_name == "Files"):
                if (self.selection_is_key(section, indexes[0])):
                    self.context_menu.actionRemoveInputFile = QtGui.QAction(self)
                    self.context_menu.actionRemoveInputFile.setText("Remove item")
                    self.context_menu.addAction(self.context_menu.actionRemoveInputFile)
                    self.context_menu.actionRemoveInputFile.triggered.connect(self.remove_item_files)
                elif (self.selection_is_value(section, indexes[0])):
                    key, val, found, i = self.get_keyval_by_val_name(section, indexes[0].data().toString())
                    if key in ["file_path", "plot_path"]:
                        self.context_menu.actionBrowseFilePath = QtGui.QAction(self)
                        self.context_menu.actionBrowseFilePath.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                        self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                    elif key in ["in_filename"]:
                        self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseInputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                        self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                    elif key in ["out_filename"]:
                        self.context_menu.actionBrowseOutputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseOutputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                        self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
                    elif key in ["cpd_filename"]:
                        self.context_menu.actionBrowseCPDFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseCPDFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseCPDFile)
                        self.context_menu.actionBrowseCPDFile.triggered.connect(self.browse_cpd_file)
                    else:
                        self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseInputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                        self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
            elif (section_name == "Options"):
                if (self.selection_is_key(section, indexes[0])):
                    self.context_menu.actionRemoveOption = QtGui.QAction(self)
                    self.context_menu.actionRemoveOption.setText("Remove option")
                    self.context_menu.addAction(self.context_menu.actionRemoveOption)
                    self.context_menu.actionRemoveOption.triggered.connect(self.remove_item_options)
            elif (section_name in ["Fluxes", "Variables"]):
                idx = indexes[0]
                # get the selected item from its index
                selected_item = idx.model().itemFromIndex(idx)
                # build a list of existing QC checks
                if selected_item.hasChildren():
                    existing_entries = []
                    for i in range(selected_item.rowCount()):
                        existing_entries.append(str(selected_item.child(i, 0).text()))
                # only put a QC check in the context menu if it is not already present
                if "GapFillUsingSOLO" not in existing_entries:
                    self.context_menu.actionAddSOLO = QtGui.QAction(self)
                    self.context_menu.actionAddSOLO.setText("Add SOLO")
                    self.context_menu.addAction(self.context_menu.actionAddSOLO)
                    self.context_menu.actionAddSOLO.triggered.connect(self.add_solo)
                if "GapFillUsingMDS" not in existing_entries:
                    self.context_menu.actionAddMDS = QtGui.QAction(self)
                    self.context_menu.actionAddMDS.setText("Add MDS")
                    self.context_menu.addAction(self.context_menu.actionAddMDS)
                    self.context_menu.actionAddMDS.triggered.connect(self.add_MDS)
                if "GapFillUsingClimatology" not in existing_entries:
                    self.context_menu.actionAddClimatology = QtGui.QAction(self)
                    self.context_menu.actionAddClimatology.setText("Add Climatology")
                    self.context_menu.addAction(self.context_menu.actionAddClimatology)
                    self.context_menu.actionAddClimatology.triggered.connect(self.add_climatology)
                self.context_menu.addSeparator()
                if "RangeCheck" not in existing_entries:
                    self.context_menu.actionAddRangeCheck = QtGui.QAction(self)
                    self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
                    self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
                    self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)
                if "DependencyCheck" not in existing_entries:
                    self.context_menu.actionAddDependencyCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
                    self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)
                if "DiurnalCheck" not in existing_entries:
                    self.context_menu.actionAddDiurnalCheck = QtGui.QAction(self)
                    self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
                    self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
                    self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)
                if "ExcludeDates" not in existing_entries:
                    self.context_menu.actionAddExcludeDates = QtGui.QAction(self)
                    self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
                    self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
                    self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)
                self.context_menu.addSeparator()
                self.context_menu.actionRemoveOption = QtGui.QAction(self)
                self.context_menu.actionRemoveOption.setText("Remove variable")
                self.context_menu.addAction(self.context_menu.actionRemoveOption)
                self.context_menu.actionRemoveOption.triggered.connect(self.remove_variable)
        elif level == 2:
            # sections with 3 levels
            section_name = str(indexes[0].parent().parent().data().toString())
            subsection_name = str(indexes[0].parent().data().toString())
            subsubsection_name = str(indexes[0].data().toString())
            #if str(indexes[0].data().toString()) in ["ExcludeDates"]:
                #self.context_menu.actionAddExcludeDateRange = QtGui.QAction(self)
                #self.context_menu.actionAddExcludeDateRange.setText("Add date range")
                #self.context_menu.addAction(self.context_menu.actionAddExcludeDateRange)
                #self.context_menu.actionAddExcludeDateRange.triggered.connect(self.add_excludedaterange)
                #self.context_menu.addSeparator()
            if subsubsection_name in ["RangeCheck", "DependencyCheck", "DiurnalCheck", "ExcludeDates"]:
                self.context_menu.actionRemoveQCCheck = QtGui.QAction(self)
                self.context_menu.actionRemoveQCCheck.setText("Remove QC check")
                self.context_menu.addAction(self.context_menu.actionRemoveQCCheck)
                self.context_menu.actionRemoveQCCheck.triggered.connect(self.remove_qc_check)
            elif subsubsection_name in ["GapFillUsingSOLO", "GapFillUsingMDS", "GapFillFromClimatology"]:
                self.context_menu.actionRemoveGFMethod = QtGui.QAction(self)
                self.context_menu.actionRemoveGFMethod.setText("Remove method")
                self.context_menu.addAction(self.context_menu.actionRemoveGFMethod)
                self.context_menu.actionRemoveGFMethod.triggered.connect(self.remove_gf_method)
        elif level == 3:
            # sections with 4 levels
            section_name = str(indexes[0].parent().parent().parent().data().toString())
            subsection_name = str(indexes[0].parent().parent().data().toString())
            subsubsection_name = str(indexes[0].parent().data().toString())
            subsubsubsection_name = str(indexes[0].data().toString())
            if subsubsection_name == "GapFillUsingSOLO":
                self.context_menu.actionAddSOLOSettings = QtGui.QAction(self)
                self.context_menu.actionAddSOLOSettings.setText("Add SOLO settings")
                self.context_menu.addAction(self.context_menu.actionAddSOLOSettings)
                self.context_menu.actionAddSOLOSettings.triggered.connect(self.add_solo_settings)
                self.context_menu.addSeparator()
            self.context_menu.actionRemoveGFMethodVariable = QtGui.QAction(self)
            self.context_menu.actionRemoveGFMethodVariable.setText("Remove variable")
            self.context_menu.addAction(self.context_menu.actionRemoveGFMethodVariable)
            self.context_menu.actionRemoveGFMethodVariable.triggered.connect(self.remove_gf_method_variable)
        elif level == 4:
            subsubsubsubsection_name = str(indexes[0].data().toString())
            if subsubsubsubsection_name in ["solo_settings"]:
                self.context_menu.actionRemoveSOLOSettings = QtGui.QAction(self)
                self.context_menu.actionRemoveSOLOSettings.setText("Remove item")
                self.context_menu.addAction(self.context_menu.actionRemoveSOLOSettings)
                self.context_menu.actionRemoveSOLOSettings.triggered.connect(self.remove_gf_method_variable_setting)

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_solo(self):
        """ Add GapFillUsingSOLO to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"GapFillUsingSOLO":{"<var>_SOLO": {"drivers": "['Fn','Fg','q','VPD','Ta','Ts']"}}}
        # get the parent and sub section text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # change to the variable name
        var_name = subsection_text+"_SOLO"
        dict_to_add["GapFillUsingSOLO"][var_name] = dict_to_add["GapFillUsingSOLO"].pop("<var>_SOLO")
        # add the subsubsection (RangeCheck)
        self.add_subsubsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_solo_settings(self):
        """ Add solo_settings to a variable."""
        idx = self.tree.selectedIndexes()[0]
        # get the parent and sub section text
        subsubsubsection_text = str(idx.data().toString())
        subsubsection_text = str(idx.parent().data().toString())
        subsection_text = str(idx.parent().parent().data().toString())
        section_text = str(idx.parent().parent().parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
        subsubsubsection, l = self.get_subsection_from_text(subsubsection, subsubsubsection_text)
        # add the subsubsection
        child0 = QtGui.QStandardItem("solo_settings")
        child1 = QtGui.QStandardItem("[5,500,5,0.001,500]")
        subsubsubsection.appendRow([child0, child1])
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_climatology(self):
        """ Add GapFillFromClimatology to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"GapFillFromClimatology":{"<var>_cli": {"method": "interpolated daily"}}}
        # get the parent and sub section text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"DependencyCheck":{"Source":"[]"}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"DiurnalCheck":{"NumSd":"5"}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"ExcludeDates":{"0":"[YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM]"}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_fileentry(self):
        """ Add a new entry to the [Files] section."""
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        self.tree.sections["Files"].appendRow([child0, child1])
        self.update_tab_text()

    def add_maxgapinterpolate(self):
        """ Add MaxGapInterpolate to the [Options] section."""
        child0 = QtGui.QStandardItem("MaxGapInterpolate")
        child1 = QtGui.QStandardItem("3")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_filterlist(self):
        """ Add FilterList to the [Options] section."""
        child0 = QtGui.QStandardItem("FilterList")
        child1 = QtGui.QStandardItem("Fc")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_turbulencefilter(self):
        """ Add TurbulenceFilter to the [Options] section."""
        child0 = QtGui.QStandardItem("TurbulenceFilter")
        child1 = QtGui.QStandardItem("ustar")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_daynightfilter(self):
        """ Add DayNightFilter to the [Options] section."""
        child0 = QtGui.QStandardItem("DayNightFilter")
        child1 = QtGui.QStandardItem("Fsd")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_usefsdsynthreshold(self):
        """ Add UseFsdsyn_threshold to the [Options] section."""
        child0 = QtGui.QStandardItem("UseFsdsyn_threshold")
        child1 = QtGui.QStandardItem("No")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_acceptdaytimes(self):
        """ Add AcceptDayTimes to the [Options] section."""
        child0 = QtGui.QStandardItem("AcceptDayTimes")
        child1 = QtGui.QStandardItem("Yes")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_useeveningfilter(self):
        """ Add UseEveningFilter to the [Options] section."""
        child0 = QtGui.QStandardItem("UseEveningFilter")
        child1 = QtGui.QStandardItem("No")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_eveningfilterlength(self):
        """ Add EveningFilterLength to the [Options] section."""
        child0 = QtGui.QStandardItem("EveningFilterLength")
        child1 = QtGui.QStandardItem("3")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_fsdthreshold(self):
        """ Add Fsd_threshold to the [Options] section."""
        child0 = QtGui.QStandardItem("Fsd_threshold")
        child1 = QtGui.QStandardItem("10")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_sathreshold(self):
        """ Add sa_threshold to the [Options] section."""
        child0 = QtGui.QStandardItem("sa_threshold")
        child1 = QtGui.QStandardItem("-5")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def add_ustar_threshold(self):
        """ Add a year to the [ustar_threshold] section."""
        model = self.tree.model()
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the name of the parent of the selected item
            parent = str(idx.parent().data().toString())
            # get the parent section
            for i in range(model.rowCount()):
                section = model.item(i)
                if str(section.text()) == "ustar_threshold":
                    break
            child0 = QtGui.QStandardItem(str(section.rowCount()))
            child1 = QtGui.QStandardItem("YYYY-mm-dd HH:MM, YYYY-mm-dd HH:MM, <ustar_threshold>")
            section.appendRow([child0, child1])

    def add_MDS(self):
        """ Add GapFillUsingMDS to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"GapFillUsingMDS":{"<var>_MDS": {"drivers": "['Fsd','Ta','VPD']",
                                                        "tolerances":"[(20, 50), 2.5, 0.5]"}}}
        # get the parent and sub section text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # change to the variable name
        var_name = subsection_text+"_MDS"
        dict_to_add["GapFillUsingMDS"][var_name] = dict_to_add["GapFillUsingMDS"].pop("<var>_MDS")
        # add the subsubsection (MDS)
        self.add_subsubsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        idx = self.tree.selectedIndexes()[0]
        dict_to_add = {"RangeCheck":{"Lower":0, "Upper": 1}}
        # get the parents text
        subsection_text = str(idx.data().toString())
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        subsection, j = self.get_subsection_from_text(section, subsection_text)
        # add the subsubsection (RangeCheck)
        self.add_subsubsection(subsection, dict_to_add)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_subsubsection(self, subsection, dict_to_add):
        """ Add a subsubsection to the model."""
        for key1 in dict_to_add:
            subsubsection = QtGui.QStandardItem(key1)
            for key2 in dict_to_add[key1]:
                child0 = QtGui.QStandardItem(key2)
                child1 = QtGui.QStandardItem(str(dict_to_add[key1][key2]))
                subsubsection.appendRow([child0, child1])
            subsection.appendRow(subsubsection)

    def add_subsubsubsection(self, subsection, dict_to_add):
        """ Add a subsubsubsection to the model."""
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

    def add_variable(self):
        """ Add a variable."""
        dict_to_add = {"GapFillUsingSOLO":{"<var>_SOLO": {"drivers": "[]"}},
                       "GapFillUsingMDS":{"<var>_MDS":{"drivers":"['Fsd','Ta','VPD']",
                                                       "tolerances":"[(20, 50), 2.5, 0.5]"}},
                       "GapFillFromClimatology":{"<var>_cli":{"method":"interpolated daily"}}}
        subsection = QtGui.QStandardItem("New variable")
        self.add_subsubsubsection(subsection, dict_to_add)
        dict_to_add = {"MergeSeries":{"Source":"['<var>','<var>_SOLO', '<var>_MDS', '<var>_cli']"}}
        self.add_subsubsection(subsection, dict_to_add)
        self.tree.sections["Fluxes"].appendRow(subsection)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def browse_cpd_file(self):
        """ Browse for the CPD results file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the key and value of the selected item
        key, val, found, i = self.get_keyval_by_val_name(section, str(idx.data().toString()))
        # set the file filter
        file_filter = "*.xls"
        # get the file path from the selected item
        file_path = os.path.split(str(idx.data().toString()))[0]
        file_path = os.path.join(file_path,"")
        # dialog for open file
        file_path = os.path.join(file_path, "")
        new_file_path = QtGui.QFileDialog.getOpenFileName(caption="Choose a CPD results file ...",
                                                          directory=file_path, filter=file_filter)
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(i, 1).setText(new_file_parts[1])

    def browse_file_path(self):
        """ Browse for the data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the key and value of the selected item
        key, val, found, j = self.get_keyval_by_val_name(section, str(idx.data().toString()))
        # dialog for new directory
        new_dir = QtGui.QFileDialog.getExistingDirectory(self, "Open a folder", val, QtGui.QFileDialog.ShowDirsOnly)
        new_dir = os.path.join(str(new_dir), "")
        # update the model
        if len(str(new_dir)) > 0:
            section.child(j, 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                          directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                          directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

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
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        return level

    def get_section_from_text(self, model, section_name):
        """ Gets a section from a model by matching the section name."""
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == str(section_name):
                break
        return section, i

    def get_subsection_from_index(self, section, idx):
        """ Gets a subsection from a model by matching the subsection name."""
        for i in range(section.rowCount()):
            # get the child subsection
            subsection = section.child(i)
            # check to see if we have the selected subsection
            if str(subsection.text()) == str(idx.data().toString()):
                break
        return subsection, i

    def get_subsection_from_text(self, section, text):
        """ Gets a subsection from a model by matching the subsection name"""
        for i in range(section.rowCount()):
            subsection = section.child(i)
            if str(subsection.text()) == text:
                break
        return subsection, i

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

    def remove_item_files(self):
        """ Remove an item from the Files section."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            section_text = str(idx.parent().data().toString())
            subsection_text = str(idx.data().toString())
            # get the top level section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the subsection within the top level section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # remove it
            section.removeRow(j)
            self.update_tab_text()

    def remove_qc_check(self):
        """ Remove a QC check."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            subsubsection_text = str(idx.data().toString())
            subsection_text = str(idx.parent().data().toString())
            section_text = str(idx.parent().parent().data().toString())
            # get the [Variables] section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the variable section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # get the gap filling method section
            subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
            subsection.removeRow(k)
            self.update_tab_text()

    def remove_gf_method(self):
        """ Remove a gap filling method."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            subsubsection_text = str(idx.data().toString())
            subsection_text = str(idx.parent().data().toString())
            section_text = str(idx.parent().parent().data().toString())
            # get the [Variables] section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the variable section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # get the gap filling method section
            subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
            subsection.removeRow(k)
            self.update_tab_text()

    def remove_gf_method_variable(self):
        """ Remove a gap filling method variable."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the parents text
            subsubsubsection_text = str(idx.data().toString())
            subsubsection_text = str(idx.parent().data().toString())
            subsection_text = str(idx.parent().parent().data().toString())
            section_text = str(idx.parent().parent().parent().data().toString())
            # get the [Variables] section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the variable section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # get the gap filling method section
            subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
            # get the variable gap fill method section
            subsubsubsection, l = self.get_subsection_from_text(subsubsection, subsubsubsection_text)
            subsubsection.removeRow(l)
            self.update_tab_text()

    def remove_gf_method_variable_setting(self):
        """ Remove a setting for a gap filling method variable."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            # get the parents text
            subsubsubsubsection_text = str(idx.data().toString())
            subsubsubsection_text = str(idx.parent().data().toString())
            subsubsection_text = str(idx.parent().parent().data().toString())
            subsection_text = str(idx.parent().parent().parent().data().toString())
            section_text = str(idx.parent().parent().parent().parent().data().toString())
            # get the [Variables] section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the variable section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # get the gap filling method section
            subsubsection, k = self.get_subsection_from_text(subsection, subsubsection_text)
            # get the variable gap fill method section
            subsubsubsection, l = self.get_subsection_from_text(subsubsection, subsubsubsection_text)
            # get the setting for the variable in gap fill method section
            subsubsubsubsection, m = self.get_subsection_from_text(subsubsubsection, subsubsubsubsection_text)
            subsubsubsection.removeRow(m)
            self.update_tab_text()

    def remove_item_options(self):
        """ Remove an item from the Options section."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            section_text = str(idx.parent().data().toString())
            subsection_text = str(idx.data().toString())
            # get the "Options" section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            section.removeRow(j)
            self.update_tab_text()

    def remove_variable(self):
        """ Remove a variable."""
        for idx in self.tree.selectedIndexes():
            # get the parents text
            subsection_text = str(idx.data().toString())
            section_text = str(idx.parent().data().toString())
            # get the "Drivers" section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            section.removeRow(j)
            self.update_tab_text()

    def selection_is_key(self, section, idx):
        """ Return True if the selected item is a key."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == key:
                result = True
                break
        return result

    def selection_is_value(self, section, idx):
        """ Return True if the selected item is a value."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == val:
                result = True
                break
        return result

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

class edit_cfg_L6(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L6, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.cfg_changed = False

        self.tabs = main_gui.tabs

        self.edit_l6_gui()

    def edit_l6_gui(self):
        """ Edit an L6 control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.context_menu)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 600, 400)
        # Tree view
        self.tree.setAlternatingRowColors(True)
        #self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(False)
        self.tree.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        # build the model
        self.get_model_from_data()

    def get_model_from_data(self):
        """ Build the data model."""
        self.tree.setModel(QtGui.QStandardItemModel())
        #self.tree.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.tree.model().setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.tree.model().itemChanged.connect(self.handleItemChanged)
        # there must be someway outa here, said the Joker to the Thief ...
        self.tree.sections = {}
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global"]:
                # sections with only 1 level
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    val = self.cfg_mod[key1][key2]
                    val = self.parse_cfg_values(key2, val, ["[", "]", "'", '"'])
                    child0 = QtGui.QStandardItem(key2)
                    child1 = QtGui.QStandardItem(val)
                    self.tree.sections[key1].appendRow([child0, child1])
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["NEE", "GPP"]:
                # sections with 2 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        val = self.cfg_mod[key1][key2][key3]
                        val = self.parse_cfg_nee_gpp_value(key3, val)
                        child0 = QtGui.QStandardItem(key3)
                        child1 = QtGui.QStandardItem(val)
                        parent2.appendRow([child0, child1])
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])
            elif key1 in ["ER"]:
                # sections with 3 levels
                self.tree.sections[key1] = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for key4 in self.cfg_mod[key1][key2][key3]:
                            val = self.cfg_mod[key1][key2][key3][key4]
                            val = self.parse_cfg_er_value(key3, val)
                            child0 = QtGui.QStandardItem(key4)
                            child1 = QtGui.QStandardItem(val)
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.sections[key1].appendRow(parent2)
                self.tree.model().appendRow(self.tree.sections[key1])

    def get_data_from_model(self):
        """ Iterate over the model and get the data."""
        cfg = self.cfg_mod
        model = self.tree.model()
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
            elif key1 in ["NEE", "GPP"]:
                # sections with 2 levels
                for j in range(section.rowCount()):
                    subsection = section.child(j)
                    key2 = str(subsection.text())
                    cfg[key1][key2] = {}
                    for k in range(subsection.rowCount()):
                        key3 = str(subsection.child(k, 0).text())
                        val3 = str(subsection.child(k, 1).text())
                        cfg[key1][key2][key3] = val3
            elif key1 in ["ER"]:
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

    def context_menu(self, position):
        """ Right click context menu."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        self.context_menu = QtGui.QMenu()
        level = self.get_level_selected_item()
        if level == 0:
            # sections with only 1 level
            if str(idx.data().toString()) == "Files":
                self.context_menu.actionAddFileEntry = QtGui.QAction(self)
                self.context_menu.actionAddFileEntry.setText("Add item")
                self.context_menu.addAction(self.context_menu.actionAddFileEntry)
                self.context_menu.actionAddFileEntry.triggered.connect(self.add_fileentry)
            elif str(idx.data().toString()) == "Output":
                pass
            elif str(idx.data().toString()) == "Options":
                # get the selected item from its index
                selected_item = idx.model().itemFromIndex(idx)
                # build a list of existing QC checks
                if selected_item.hasChildren():
                    existing_entries = []
                    for i in range(selected_item.rowCount()):
                        existing_entries.append(str(selected_item.child(i, 0).text()))
                # only put a QC check in the context menu if it is not already present
                if "MaxGapInterpolate" not in existing_entries:
                    self.context_menu.actionAddMaxGapInterpolate = QtGui.QAction(self)
                    self.context_menu.actionAddMaxGapInterpolate.setText("MaxGapInterpolate")
                    self.context_menu.addAction(self.context_menu.actionAddMaxGapInterpolate)
                    self.context_menu.actionAddMaxGapInterpolate.triggered.connect(self.add_maxgapinterpolate)
            elif str(idx.data().toString()) == "Global":
                self.context_menu.actionAddGlobalAttribute = QtGui.QAction(self)
                self.context_menu.actionAddGlobalAttribute.setText("Add global attribute")
                self.context_menu.addAction(self.context_menu.actionAddGlobalAttribute)
                self.context_menu.actionAddGlobalAttribute.triggered.connect(self.add_global_attribute)
            elif str(idx.data().toString()) in ["ER"]:
                pass
                #self.context_menu.actionAddVariable = QtGui.QAction(self)
                #self.context_menu.actionAddVariable.setText("Add variable")
                #self.context_menu.addAction(self.context_menu.actionAddVariable)
                #self.context_menu.actionAddVariable.triggered.connect(self.add_er_variable)
        elif level == 1:
            # sections with 2 levels
            section_name = str(idx.parent().data().toString())
            section, i = self.get_section_from_text(model, section_name)
            if (section_name == "Files"):
                if (self.selection_is_key(section, idx)):
                    self.context_menu.actionRemoveInputFile = QtGui.QAction(self)
                    self.context_menu.actionRemoveInputFile.setText("Remove item")
                    self.context_menu.addAction(self.context_menu.actionRemoveInputFile)
                    self.context_menu.actionRemoveInputFile.triggered.connect(self.remove_item_files)
                elif (self.selection_is_value(section, idx)):
                    key, val, found, i = self.get_keyval_by_val_name(section, idx.data().toString())
                    if key in ["file_path", "plot_path"]:
                        self.context_menu.actionBrowseFilePath = QtGui.QAction(self)
                        self.context_menu.actionBrowseFilePath.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseFilePath)
                        self.context_menu.actionBrowseFilePath.triggered.connect(self.browse_file_path)
                    elif key in ["in_filename"]:
                        self.context_menu.actionBrowseInputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseInputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseInputFile)
                        self.context_menu.actionBrowseInputFile.triggered.connect(self.browse_input_file)
                    elif key in ["out_filename"]:
                        self.context_menu.actionBrowseOutputFile = QtGui.QAction(self)
                        self.context_menu.actionBrowseOutputFile.setText("Browse...")
                        self.context_menu.addAction(self.context_menu.actionBrowseOutputFile)
                        self.context_menu.actionBrowseOutputFile.triggered.connect(self.browse_output_file)
            elif (section_name == "Global"):
                if (self.selection_is_key(section, idx)):
                    self.context_menu.actionRemoveGlobalAttribute = QtGui.QAction(self)
                    self.context_menu.actionRemoveGlobalAttribute.setText("Remove attribute")
                    self.context_menu.addAction(self.context_menu.actionRemoveGlobalAttribute)
                    self.context_menu.actionRemoveGlobalAttribute.triggered.connect(self.remove_global_attribute)

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def add_er_variable(self):
        """ Add a variable to the [ER] section."""
        dict_to_add = {"ERUsingSOLO":{"ER_SOLO_all": {"drivers": "[]",
                                                      "target": "ER",
                                                      "output": "ER_SOLO_all"}}}
        subsection = QtGui.QStandardItem("ER_SOLO")
        self.add_subsubsubsection(subsection, dict_to_add)
        dict_to_add = {"MergeSeries":{"Source":"ER,ER_SOLO_all"}}
        self.add_subsubsection(subsection, dict_to_add)
        self.tree.sections["ER"].appendRow(subsection)
        # update the tab text with an asterix if required
        self.update_tab_text()

    def add_fileentry(self):
        """ Add a new entry to the [Files] section."""
        child0 = QtGui.QStandardItem("New item")
        child1 = QtGui.QStandardItem("")
        self.tree.sections["Files"].appendRow([child0, child1])
        self.update_tab_text()

    def add_global_attribute(self):
        """ Add a new global attribute to the [Global] section."""
        child0 = QtGui.QStandardItem("New attribute")
        child1 = QtGui.QStandardItem("")
        self.tree.sections["Global"].appendRow([child0, child1])
        self.update_tab_text()

    def add_maxgapinterpolate(self):
        """ Add MaxGapInterpolate to the [Options] section."""
        child0 = QtGui.QStandardItem("MaxGapInterpolate")
        child1 = QtGui.QStandardItem("3")
        self.tree.sections["Options"].appendRow([child0, child1])
        self.update_tab_text()

    def browse_file_path(self):
        """ Browse for the data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the key and value of the selected item
        key, val, found, j = self.get_keyval_by_val_name(section, str(idx.data().toString()))
        # dialog for new directory
        new_dir = QtGui.QFileDialog.getExistingDirectory(self, "Open a folder", val, QtGui.QFileDialog.ShowDirsOnly)
        new_dir = os.path.join(str(new_dir), "")
        # update the model
        if len(str(new_dir)) > 0:
            section.child(j, 1).setText(new_dir)

    def browse_input_file(self):
        """ Browse for the input data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getOpenFileName(caption="Choose an input file ...",
                                                          directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

    def browse_output_file(self):
        """ Browse for the output data file path."""
        model = self.tree.model()
        idx = self.tree.selectedIndexes()[0]
        # get the section containing the selected item
        section_text = str(idx.parent().data().toString())
        subsection_text = str(idx.data().toString())
        # get the top level and sub sections
        model = self.tree.model()
        section, i = self.get_section_from_text(model, section_text)
        # get the file_path so it can be used as a default directory
        key, file_path, found, j = self.get_keyval_by_key_name(section, "file_path")
        # get the row number for the selected item
        key, val, found, k = self.get_keyval_by_val_name(section, subsection_text)
        # dialog for open file
        new_file_path = QtGui.QFileDialog.getSaveFileName(caption="Choose an output file ...",
                                                          directory=file_path, filter="*.nc")
        # update the model
        if len(str(new_file_path)) > 0:
            new_file_parts = os.path.split(str(new_file_path))
            section.child(k, 1).setText(new_file_parts[1])

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
        model = self.tree.model()
        indexes = self.tree.selectedIndexes()
        level = -1
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        return level

    def get_section_from_text(self, model, section_name):
        """ Gets a section from a model by matching the section name."""
        for i in range(model.rowCount()):
            section = model.item(i)
            if str(section.text()) == str(section_name):
                break
        return section, i

    def get_subsection_from_text(self, section, text):
        """ Gets a subsection from a model by matching the subsection name"""
        for i in range(section.rowCount()):
            subsection = section.child(i)
            if str(subsection.text()) == text:
                break
        return subsection, i

    def parse_cfg_er_value(self, k, v):
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
        if k in ["ERUsingSOLO", "ERUsingFFNET", "ERUsingLloydTaylor",
                 "ERUsingLasslop", "MergeSeries", "AverageSeries"]:
            strip_list = [" ", '"', "'"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def parse_cfg_nee_gpp_value(self, k, v):
        """ Parse the [NEE] and [GPP] section keys to remove unnecessary characters."""
        strip_list = [" ", '"', "'", "[", "]"]
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def parse_cfg_values(self, k, v, strip_list):
        """ Parse key values to remove unnecessary characters."""
        for c in strip_list:
            if c in v:
                v = v.replace(c, "")
                self.cfg_changed = True
        return v

    def remove_item_files(self):
        """ Remove an item from the Files section."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            section_text = str(idx.parent().data().toString())
            subsection_text = str(idx.data().toString())
            # get the top level section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the subsection within the top level section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # remove it
            section.removeRow(j)
            self.update_tab_text()

    def remove_global_attribute(self):
        """ Remove an attribute from the Global section."""
        # loop over selected items in the tree
        for idx in self.tree.selectedIndexes():
            section_text = str(idx.parent().data().toString())
            subsection_text = str(idx.data().toString())
            # get the top level section
            model = self.tree.model()
            section, i = self.get_section_from_text(model, section_text)
            # get the subsection within the top level section
            subsection, j = self.get_subsection_from_text(section, subsection_text)
            # remove it
            section.removeRow(j)
            self.update_tab_text()

    def selection_is_key(self, section, idx):
        """ Return True if the selected item is a key."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == key:
                result = True
                break
        return result

    def selection_is_value(self, section, idx):
        """ Return True if the selected item is a value."""
        result = False
        for i in range(section.rowCount()):
            key = str(section.child(i, 0).text())
            val = str(section.child(i, 1).text())
            if str(idx.data().toString()) == val:
                result = True
                break
        return result

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

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

        self.radioButton_NumberMonths = QtGui.QRadioButton(self)
        self.radioButton_NumberMonths.setGeometry(QtCore.QRect(20, 140, 110, 22))
        self.radioButton_NumberMonths.setText("Months")
        self.radioButton_NumberMonths.setChecked(True)
        self.radioButton_NumberDays = QtGui.QRadioButton(self)
        self.radioButton_NumberDays.setGeometry(QtCore.QRect(130, 140, 110, 22))
        self.radioButton_NumberDays.setText("Days")
        self.radioButton_Manual = QtGui.QRadioButton(self)
        self.radioButton_Manual.setGeometry(QtCore.QRect(20, 110, 110, 25))
        self.radioButton_Manual.setText("Manual")
        self.radioButtons = QtGui.QButtonGroup(self)
        self.radioButtons.addButton(self.radioButton_NumberMonths)
        self.radioButtons.addButton(self.radioButton_NumberDays)
        self.radioButtons.addButton(self.radioButton_Manual)

        self.lineEdit_NumberMonths = QtGui.QLineEdit(self)
        self.lineEdit_NumberMonths.setGeometry(QtCore.QRect(90, 140, 30, 25))
        self.lineEdit_NumberMonths.setText("3")
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
        # connect signals to slots
        self.RunButton.clicked.connect(lambda:pfp_gfALT.gfalternate_run_gui(self))
        self.DoneButton.clicked.connect(lambda:pfp_gfALT.gfalternate_done(self))
        self.QuitButton.clicked.connect(lambda:pfp_gfALT.gfalternate_quit(self))

class pfp_l5_ui(QtGui.QDialog):
    def __init__(self, parent=None):
        super(pfp_l5_ui, self).__init__(parent)
        self.resize(400, 265)
        self.setWindowTitle("Gap fill (SOLO)")
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
        # first row; Nodes, Training, Nda factor
        row1_y = 5
        self.label_Nodes = QtGui.QLabel(self)
        self.label_Nodes.setGeometry(QtCore.QRect(20, row1_y, 50, label_height))
        self.label_Nodes.setText("Nodes")
        self.lineEdit_Nodes = QtGui.QLineEdit(self)
        self.lineEdit_Nodes.setGeometry(QtCore.QRect(70, row1_y, 50, lineedit_height))
        self.lineEdit_Nodes.setText("Auto")
        self.label_Training = QtGui.QLabel(self)
        self.label_Training.setGeometry(QtCore.QRect(150, row1_y, 50, label_height))
        self.label_Training.setText("Training")
        self.lineEdit_Training = QtGui.QLineEdit(self)
        self.lineEdit_Training.setGeometry(QtCore.QRect(210, row1_y, 50, lineedit_height))
        self.lineEdit_Training.setText("500")
        self.label_NdaFactor = QtGui.QLabel(self)
        self.label_NdaFactor.setGeometry(QtCore.QRect(270, row1_y, 70, label_height))
        self.label_NdaFactor.setText("Nda factor")
        self.lineEdit_NdaFactor = QtGui.QLineEdit(self)
        self.lineEdit_NdaFactor.setGeometry(QtCore.QRect(340, row1_y, 50, lineedit_height))
        self.lineEdit_NdaFactor.setText("5")
        # second row; Learning, Iterations
        row2_y = row1_y + row_height
        self.label_Learning = QtGui.QLabel(self)
        self.label_Learning.setGeometry(QtCore.QRect(140, row2_y, 60, label_height))
        self.label_Learning.setText("Learning")
        self.lineEdit_Learning = QtGui.QLineEdit(self)
        self.lineEdit_Learning.setGeometry(QtCore.QRect(210, row2_y, 50, lineedit_height))
        self.lineEdit_Learning.setText("0.001")
        self.label_Iterations = QtGui.QLabel(self)
        self.label_Iterations.setGeometry(QtCore.QRect(270, row2_y, 70, label_height))
        self.label_Iterations.setText("Iterations")
        self.lineEdit_Iterations = QtGui.QLineEdit(self)
        self.lineEdit_Iterations.setGeometry(QtCore.QRect(340, row2_y, 50, lineedit_height))
        self.lineEdit_Iterations.setText("500")
        # third row; data start and end date labels
        row3_y = row2_y + row_height
        self.label_DataStartDate = QtGui.QLabel(self)
        self.label_DataStartDate.setGeometry(QtCore.QRect(48, row3_y, label_width, label_height))
        self.label_DataEndDate = QtGui.QLabel(self)
        self.label_DataEndDate.setGeometry(QtCore.QRect(244, row3_y, label_width, label_height))
        # fourth row; data start and end date values
        row4_y = row3_y + row_height
        self.label_DataStartDate_value = QtGui.QLabel(self)
        self.label_DataStartDate_value.setGeometry(QtCore.QRect(33, row4_y, label_width, label_height))
        self.label_DataEndDate_value = QtGui.QLabel(self)
        self.label_DataEndDate_value.setGeometry(QtCore.QRect(220, row4_y, label_width, label_height))
        self.label_DataStartDate.setText("Data start date")
        self.label_DataEndDate.setText("Data end date")
        self.label_DataStartDate_value.setText("YYYY-MM-DD HH:mm")
        self.label_DataEndDate_value.setText("YYYY-MM-DD HH:mm")
        # fifth row; start date line edit box
        row5_y = row4_y + row_height
        self.label_StartDate = QtGui.QLabel(self)
        self.label_StartDate.setGeometry(QtCore.QRect(30, row5_y, lineedit_long_width, lineedit_height))
        self.label_StartDate.setText("Start date (YYYY-MM-DD)")
        self.lineEdit_StartDate = QtGui.QLineEdit(self)
        self.lineEdit_StartDate.setGeometry(QtCore.QRect(220, row5_y, lineedit_long_width, lineedit_height))
        # sixth row; end date line edit box
        row6_y = row5_y + row_height
        self.label_EndDate = QtGui.QLabel(self)
        self.label_EndDate.setGeometry(QtCore.QRect(30, row6_y, lineedit_long_width, lineedit_height))
        self.label_EndDate.setText("End date (YYYY-MM-DD)")
        self.lineEdit_EndDate = QtGui.QLineEdit(self)
        self.lineEdit_EndDate.setGeometry(QtCore.QRect(220, row6_y, lineedit_long_width, lineedit_height))
        # seventh row
        row7_y = row6_y + row_height
        self.radioButton_Manual = QtGui.QRadioButton(self)
        self.radioButton_Manual.setGeometry(QtCore.QRect(20, row7_y, radiobutton_width, radiobutton_height))
        self.radioButton_Manual.setText("Manual")
        self.lineEdit_MinPercent = QtGui.QLineEdit(self)
        self.lineEdit_MinPercent.setGeometry(QtCore.QRect(220, row7_y, 30, lineedit_height))
        self.lineEdit_MinPercent.setText("25")
        self.label_MinPercent = QtGui.QLabel(self)
        self.label_MinPercent.setGeometry(QtCore.QRect(140, row7_y, 80, label_height))
        self.label_MinPercent.setText("Min pts (%)")
        # eighth row; Months, Days, Auto-complete
        row8_y = row7_y + row_height
        self.radioButton_NumberMonths = QtGui.QRadioButton(self)
        self.radioButton_NumberMonths.setGeometry(QtCore.QRect(20, row8_y, radiobutton_width, radiobutton_height))
        self.radioButton_NumberMonths.setText("Months")
        self.radioButton_NumberMonths.setChecked(True)
        self.lineEdit_NumberMonths = QtGui.QLineEdit(self)
        self.lineEdit_NumberMonths.setGeometry(QtCore.QRect(90, row8_y, lineedit_short_width, lineedit_height))
        self.lineEdit_NumberMonths.setText("2")
        self.radioButton_NumberDays = QtGui.QRadioButton(self)
        self.radioButton_NumberDays.setGeometry(QtCore.QRect(150, row8_y, radiobutton_width, radiobutton_height))
        self.radioButton_NumberDays.setText("Days")
        self.lineEdit_NumberDays = QtGui.QLineEdit(self)
        self.lineEdit_NumberDays.setGeometry(QtCore.QRect(220, row8_y, lineedit_short_width, lineedit_height))
        self.lineEdit_NumberDays.setText("60")
        self.checkBox_AutoComplete = QtGui.QCheckBox(self)
        self.checkBox_AutoComplete.setGeometry(QtCore.QRect(270, row8_y, radiobutton_width+10, radiobutton_height))
        self.checkBox_AutoComplete.setChecked(True)
        self.checkBox_AutoComplete.setText("Auto complete")
        # define the radio button group
        self.radioButtons = QtGui.QButtonGroup(self)
        self.radioButtons.addButton(self.radioButton_NumberMonths)
        self.radioButtons.addButton(self.radioButton_NumberDays)
        self.radioButtons.addButton(self.radioButton_Manual)
        # ninth row; Show plots, Plot all and Overwrite checkboxes
        row9_y = row8_y + row_height
        self.checkBox_ShowPlots = QtGui.QCheckBox(self)
        self.checkBox_ShowPlots.setGeometry(QtCore.QRect(20, row9_y, checkbox_width, checkbox_height))
        self.checkBox_ShowPlots.setText("Show plots")
        self.checkBox_ShowPlots.setChecked(True)
        self.checkBox_PlotAll = QtGui.QCheckBox(self)
        self.checkBox_PlotAll.setGeometry(QtCore.QRect(150, row9_y, checkbox_width, checkbox_height))
        self.checkBox_PlotAll.setText("Plot all")
        self.checkBox_Overwrite = QtGui.QCheckBox(self)
        self.checkBox_Overwrite.setGeometry(QtCore.QRect(270, row9_y, checkbox_width, checkbox_height))
        self.checkBox_Overwrite.setText("Overwrite")
        # tenth (bottom) row; Run, Done and Quit buttons
        row10_y = row9_y + row_height
        self.RunButton = QtGui.QPushButton(self)
        self.RunButton.setGeometry(QtCore.QRect(20, row10_y, button_width, button_height))
        self.RunButton.setText("Run")
        self.DoneButton = QtGui.QPushButton(self)
        self.DoneButton.setGeometry(QtCore.QRect(150, row10_y, button_width, button_height))
        self.DoneButton.setText("Done")
        self.QuitButton = QtGui.QPushButton(self)
        self.QuitButton.setGeometry(QtCore.QRect(270, row10_y, button_width, button_height))
        self.QuitButton.setText("Quit")
        # connect the "Run", "Done" and "Quit" buttons to their slots
        self.RunButton.clicked.connect(self.call_gui_run)
        self.DoneButton.clicked.connect(self.call_gui_done)
        self.QuitButton.clicked.connect(self.call_gui_quit)

    def call_gui_run(self):
        if self.solo_info["called_by"] == "GapFillingUsingSOLO":
            pfp_gfSOLO.gfSOLO_run_gui(self)
        elif self.solo_info["called_by"] == "ERUsingSOLO":
            pfp_rpNN.rpSOLO_run_gui(self)

    def call_gui_quit(self):
        if self.solo_info["called_by"] == "GapFillingUsingSOLO":
            pfp_gfSOLO.gfSOLO_quit(self)
        elif self.solo_info["called_by"] == "ERUsingSOLO":
            pfp_rpNN.rpSOLO_quit(self)

    def call_gui_done(self):
        if self.solo_info["called_by"] == "GapFillingUsingSOLO":
            pfp_gfSOLO.gfSOLO_done(self)
        elif self.solo_info["called_by"] == "ERUsingSOLO":
            pfp_rpNN.rpSOLO_done(self)
