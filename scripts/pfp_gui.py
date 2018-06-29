# standard modules
import copy
# 3rd party modules
from PyQt4 import QtCore, QtGui

class edit_cfg_L1(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L1, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.tabs = main_gui.tabs
        
        self.edit_L1_gui()
        
    def edit_L1_gui(self):
        """ Edit L1 control file GUI."""
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
        # there must be some way to do this recursively
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                parent = QtGui.QStandardItem(key1)
                for val in self.cfg_mod[key1]:
                    value = self.cfg_mod[key1][val]
                    child0 = QtGui.QStandardItem(val)
                    child1 = QtGui.QStandardItem(str(value))
                    parent.appendRow([child0, child1])
                self.tree.model().appendRow(parent)
            elif key1 in ["Variables"]:
                self.tree.variables = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for val in self.cfg_mod[key1][key2][key3]:
                            value = self.cfg_mod[key1][key2][key3][val]
                            child0 = QtGui.QStandardItem(val)
                            child1 = QtGui.QStandardItem(str(value))
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.variables.appendRow(parent2)
                self.tree.model().appendRow(self.tree.variables)

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
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        self.context_menu = QtGui.QMenu()
        if level == 0:
            self.context_menu.actionAddVariable = QtGui.QAction(self)
            self.context_menu.actionAddVariable.setText("Add variable")
            self.context_menu.addAction(self.context_menu.actionAddVariable)
            self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
        elif level == 1:
            pass
        elif level == 2:
            self.context_menu.addAction(self.tr("Add ..."))

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

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
        self.tree.variables.appendRow(parent2)

class edit_cfg_L2(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L2, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
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
        # there must be some way to do this recursively
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                parent = QtGui.QStandardItem(key1)
                for val in self.cfg_mod[key1]:
                    value = self.cfg_mod[key1][val]
                    child0 = QtGui.QStandardItem(val)
                    child1 = QtGui.QStandardItem(str(value))
                    parent.appendRow([child0, child1])
                self.tree.model().appendRow(parent)
            elif key1 in ["Variables"]:
                self.tree.variables = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for val in self.cfg_mod[key1][key2][key3]:
                            value = self.cfg_mod[key1][key2][key3][val]
                            child0 = QtGui.QStandardItem(val)
                            child1 = QtGui.QStandardItem(str(value))
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.variables.appendRow(parent2)
                self.tree.model().appendRow(self.tree.variables)

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
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        self.context_menu = QtGui.QMenu()
        if level == 0:
            self.context_menu.actionAddVariable = QtGui.QAction(self)
            self.context_menu.actionAddVariable.setText("Add variable")
            self.context_menu.addAction(self.context_menu.actionAddVariable)
            self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
        elif level == 1:
            self.context_menu.actionAddRangeCheck = QtGui.QAction(self)
            self.context_menu.actionAddRangeCheck.setText("Add RangeCheck")
            self.context_menu.addAction(self.context_menu.actionAddRangeCheck)
            self.context_menu.actionAddRangeCheck.triggered.connect(self.add_rangecheck)

            self.context_menu.actionAddDependencyCheck = QtGui.QAction(self)
            self.context_menu.actionAddDependencyCheck.setText("Add DependencyCheck")
            self.context_menu.addAction(self.context_menu.actionAddDependencyCheck)
            self.context_menu.actionAddDependencyCheck.triggered.connect(self.add_dependencycheck)

            self.context_menu.actionAddDiurnalCheck = QtGui.QAction(self)
            self.context_menu.actionAddDiurnalCheck.setText("Add DiurnalCheck")
            self.context_menu.addAction(self.context_menu.actionAddDiurnalCheck)
            self.context_menu.actionAddDiurnalCheck.triggered.connect(self.add_diurnalcheck)

            self.context_menu.actionAddExcludeDates = QtGui.QAction(self)
            self.context_menu.actionAddExcludeDates.setText("Add ExcludeDates")
            self.context_menu.addAction(self.context_menu.actionAddExcludeDates)
            self.context_menu.actionAddExcludeDates.triggered.connect(self.add_excludedates)

            self.context_menu.actionAddExcludeHours = QtGui.QAction(self)
            self.context_menu.actionAddExcludeHours.setText("Add ExcludeHours")
            self.context_menu.addAction(self.context_menu.actionAddExcludeHours)
            self.context_menu.actionAddExcludeHours.triggered.connect(self.add_excludehours)

            self.context_menu.actionAddLinear = QtGui.QAction(self)
            self.context_menu.actionAddLinear.setText("Add Linear")
            self.context_menu.addAction(self.context_menu.actionAddLinear)
            self.context_menu.actionAddLinear.triggered.connect(self.add_linear)

            self.context_menu.addSeparator()

            self.context_menu.actionRemoveVariable = QtGui.QAction(self)
            self.context_menu.actionRemoveVariable.setText("Remove variable")
            self.context_menu.addAction(self.context_menu.actionRemoveVariable)
            self.context_menu.actionRemoveVariable.triggered.connect(self.remove_variable)
        #elif level == 2:
            #menu.addAction(self.tr("Edit object"))

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

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
        self.tree.variables.appendRow(parent2)

    def add_rangecheck(self):
        """ Add a range check to a variable."""
        print " add RangeCheck here"

    def add_dependencycheck(self):
        """ Add a dependency check to a variable."""
        print " add DependencyCheck here"

    def add_diurnalcheck(self):
        """ Add a diurnal check to a variable."""
        print " add DiurnalCheck here"

    def add_excludedates(self):
        """ Add an exclude dates check to a variable."""
        print " add ExcludeDates here"

    def add_excludehours(self):
        """ Add an exclude hours check to a variable."""
        print " add ExcludeHours here"

    def add_linear(self):
        """ Add a linear correction to a variable."""
        print " add Linear here"

    def remove_variable(self):
        """ Remove a variable."""
        print " add RemoveVariable here"

class edit_cfg_L3(QtGui.QWidget):
    def __init__(self, main_gui):

        super(edit_cfg_L3, self).__init__()

        self.cfg_mod = copy.deepcopy(main_gui.cfg)
        self.tabs = main_gui.tabs
        
        self.edit_L3_gui()
        
    def edit_L3_gui(self):
        """ Edit L3 control file GUI."""
        # get a QTreeView
        self.tree = QtGui.QTreeView()
        # set the context menu policy
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # connect the context menu requested signal to appropriate slot
        self.tree.customContextMenuRequested.connect(self.openMenu)
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
        # there must be some way to do this recursively
        for key1 in self.cfg_mod:
            if not self.cfg_mod[key1]:
                continue
            if key1 in ["Files", "Global", "Output", "General", "Options", "Soil", "Massman"]:
                parent = QtGui.QStandardItem(key1)
                for val in self.cfg_mod[key1]:
                    value = self.cfg_mod[key1][val]
                    child0 = QtGui.QStandardItem(val)
                    child1 = QtGui.QStandardItem(str(value))
                    parent.appendRow([child0, child1])
                self.tree.model().appendRow(parent)
            elif key1 in ["Variables"]:
                self.tree.variables = QtGui.QStandardItem(key1)
                for key2 in self.cfg_mod[key1]:
                    parent2 = QtGui.QStandardItem(key2)
                    for key3 in self.cfg_mod[key1][key2]:
                        parent3 = QtGui.QStandardItem(key3)
                        for val in self.cfg_mod[key1][key2][key3]:
                            value = self.cfg_mod[key1][key2][key3][val]
                            child0 = QtGui.QStandardItem(val)
                            child1 = QtGui.QStandardItem(str(value))
                            parent3.appendRow([child0, child1])
                        parent2.appendRow(parent3)
                    self.tree.variables.appendRow(parent2)
                self.tree.model().appendRow(self.tree.variables)

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

    def handleItemChanged(self, item):
        """ Handler for when view items are edited."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")
        # update the control file contents
        self.cfg_mod = self.get_data_from_model()

    def openMenu(self, position):
        """ Right click context menu."""
        indexes = self.tree.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1
        self.context_menu = QtGui.QMenu()
        if level == 0:
            self.context_menu.actionAddVariable = QtGui.QAction(self)
            self.context_menu.actionAddVariable.setText("Add variable")
            self.context_menu.addAction(self.context_menu.actionAddVariable)
            self.context_menu.actionAddVariable.triggered.connect(self.add_variable)
        elif level == 1:
            self.context_menu.addAction(self.tr("Add QC check"))
        #elif level == 2:
            #menu.addAction(self.tr("Edit object"))

        self.context_menu.exec_(self.tree.viewport().mapToGlobal(position))

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
        self.tree.variables.appendRow(parent2)

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
