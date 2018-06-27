# standard modules
import copy
import logging
import os
import sys
import time
# 3rd party modules
from configobj import ConfigObj
import matplotlib
matplotlib.use("QT4Agg")
import matplotlib.pyplot as plt
from PyQt4 import QtCore, QtGui
# PFP modules
sys.path.append('scripts')
import pfp_top_level
import pfp_gui

logger = logging.getLogger("pfp_log")
logfmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s','%H:%M:%S')
logger.setLevel(logging.DEBUG)

class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super(QPlainTextEditLogger, self).__init__()
        self.textBox = QtGui.QPlainTextEdit(parent)
        self.textBox.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.textBox.appendPlainText(msg)
        QtGui.QApplication.processEvents()

class pfp_main_ui(QtGui.QWidget, QPlainTextEditLogger):
    def __init__(self, parent=None):
        super(pfp_main_ui, self).__init__(parent)

        logTextBox = QPlainTextEditLogger(self)
        logTextBox.setFormatter(logfmt)
        logger.addHandler(logTextBox)

        # menu bar
        self.menubar = QtGui.QMenuBar(self)
        # File menu
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setTitle("File")
        # File/Convert submenu
        self.menuFileConvert = QtGui.QMenu(self.menuFile)
        self.menuFileConvert.setTitle("Convert")
        # Edit menu
        self.menuEdit = QtGui.QMenu(self.menubar)
        self.menuEdit.setTitle("Edit")
        # Run menu
        self.menuRun = QtGui.QMenu(self.menubar)
        self.menuRun.setTitle("Run")
        # Plot menu
        self.menuPlot = QtGui.QMenu(self.menubar)
        self.menuPlot.setTitle("Plot")
        # Utilities menu
        self.menuUtilities = QtGui.QMenu(self.menubar)
        self.menuUtilities.setTitle("Utilities")
        # Help menu
        self.menuHelp = QtGui.QMenu(self.menubar)
        self.menuHelp.setTitle("Help")
        # File menu items
        self.actionFileOpen = QtGui.QAction(self)
        self.actionFileOpen.setText("Open")
        self.actionFileOpen.setShortcut('Ctrl+O')
        self.actionFileSave = QtGui.QAction(self)
        self.actionFileSave.setText("Save")
        self.actionFileSave.setShortcut('Ctrl+S')
        self.actionFileSaveAs = QtGui.QAction(self)
        self.actionFileSaveAs.setText("Save As...")
        self.actionFileSaveAs.setShortcut('Ctrl+A')
        self.actionFileConcatenate = QtGui.QAction(self)
        self.actionFileConcatenate.setText("Concatenate")
        self.actionFileSplit = QtGui.QAction(self)
        self.actionFileSplit.setText("Split")
        self.actionFileQuit = QtGui.QAction(self)
        self.actionFileQuit.setText("Quit")
        self.actionFileQuit.setShortcut('Ctrl+Z')
        # File/Convert submenu
        self.actionFileConvertnc2biomet = QtGui.QAction(self)
        self.actionFileConvertnc2biomet.setText("nc to Biomet")
        self.actionFileConvertnc2xls = QtGui.QAction(self)
        self.actionFileConvertnc2xls.setText("nc to Excel")
        self.actionFileConvertnc2fluxnet = QtGui.QAction(self)
        self.actionFileConvertnc2fluxnet.setText("nc to FluxNet")
        self.actionFileConvertnc2reddyproc = QtGui.QAction(self)
        self.actionFileConvertnc2reddyproc.setText("nc to REddyProc")
        # Edit menu items
        self.actionEditPreferences = QtGui.QAction(self)
        self.actionEditPreferences.setText("Preferences...")
        # Run menu items
        self.actionRunCurrent = QtGui.QAction(self)
        self.actionRunCurrent.setText("Current...")
        self.actionRunL1 = QtGui.QAction(self)
        self.actionRunL1.setText("L1 (import)")
        self.actionRunL2 = QtGui.QAction(self)
        self.actionRunL2.setText("L2 (QC)")
        self.actionRunL3 = QtGui.QAction(self)
        self.actionRunL3.setText("L3 (process)")
        self.actionRunL4 = QtGui.QAction(self)
        self.actionRunL4.setText("L4 (gap fill drivers)")
        self.actionRunL5 = QtGui.QAction(self)
        self.actionRunL5.setText("L5 (gap fill fluxes)")
        self.actionRunL6 = QtGui.QAction(self)
        self.actionRunL6.setText("L6 (partition)")
        # Plot menu items
        self.actionPlotL1 = QtGui.QAction(self)
        self.actionPlotL1.setText("L1 (import)")
        self.actionPlotL2 = QtGui.QAction(self)
        self.actionPlotL2.setText("L2 (QC)")
        self.actionPlotL3 = QtGui.QAction(self)
        self.actionPlotL3.setText("L3 (process)")
        self.actionPlotL4 = QtGui.QAction(self)
        self.actionPlotL4.setText("L4 (gap fill driver)")
        self.actionPlotL5 = QtGui.QAction(self)
        self.actionPlotL5.setText("L5 (gap fill fluxes)")
        self.actionPlotL6 = QtGui.QAction(self)
        self.actionPlotL6.setText("L6 (summary)")
        self.actionPlotFingerprints = QtGui.QAction(self)
        self.actionPlotFingerprints.setText("Fingerprints")
        self.actionPlotQuickCheck = QtGui.QAction(self)
        self.actionPlotQuickCheck.setText("Quick check")
        self.actionPlotTimeSeries = QtGui.QAction(self)
        self.actionPlotTimeSeries.setText("Time series")
        self.actionPlotClosePlots = QtGui.QAction(self)
        self.actionPlotClosePlots.setText("Close plots")
        # Utilities menu
        self.actionUtilitiesClimatology = QtGui.QAction(self)
        self.actionUtilitiesClimatology.setText("Climatology")
        self.actionUtilitiesUstarCPD = QtGui.QAction(self)
        self.actionUtilitiesUstarCPD.setText("u* thtreshold (CPD)")
        # add the actions to the menus
        # File/Convert submenu
        self.menuFileConvert.addAction(self.actionFileConvertnc2biomet)
        self.menuFileConvert.addAction(self.actionFileConvertnc2xls)
        self.menuFileConvert.addAction(self.actionFileConvertnc2fluxnet)
        self.menuFileConvert.addAction(self.actionFileConvertnc2reddyproc)
        # File menu
        self.menuFile.addAction(self.actionFileOpen)
        self.menuFile.addAction(self.actionFileSave)
        self.menuFile.addAction(self.actionFileSaveAs)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionFileConcatenate)
        self.menuFile.addAction(self.menuFileConvert.menuAction())
        self.menuFile.addAction(self.actionFileSplit)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionFileQuit)
        # Edit menu
        self.menuEdit.addAction(self.actionEditPreferences)
        # Run menu
        self.menuRun.addAction(self.actionRunCurrent)
        self.menuRun.addSeparator()
        self.menuRun.addAction(self.actionRunL1)
        self.menuRun.addAction(self.actionRunL2)
        self.menuRun.addAction(self.actionRunL3)
        self.menuRun.addAction(self.actionRunL4)
        self.menuRun.addAction(self.actionRunL5)
        self.menuRun.addAction(self.actionRunL6)
        # Plot menu
        self.menuPlot.addAction(self.actionPlotL1)
        self.menuPlot.addAction(self.actionPlotL2)
        self.menuPlot.addAction(self.actionPlotL3)
        self.menuPlot.addAction(self.actionPlotL4)
        self.menuPlot.addAction(self.actionPlotL5)
        self.menuPlot.addAction(self.actionPlotL6)
        self.menuPlot.addSeparator()
        self.menuPlot.addAction(self.actionPlotFingerprints)
        self.menuPlot.addAction(self.actionPlotQuickCheck)
        self.menuPlot.addAction(self.actionPlotTimeSeries)
        self.menuPlot.addSeparator()
        self.menuPlot.addAction(self.actionPlotClosePlots)
        # Utilities menu
        self.menuUtilities.addAction(self.actionUtilitiesClimatology)
        self.menuUtilities.addAction(self.actionUtilitiesUstarCPD)
        # add individual menus to menu bar
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuRun.menuAction())
        self.menubar.addAction(self.menuPlot.menuAction())
        self.menubar.addAction(self.menuUtilities.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        # create a tab bar
        self.tabs = QtGui.QTabWidget(self)
        self.tabs.tab_index_all = 0
        self.tabs.tab_index_current = 0
        self.tabs.tab_dict = {}
        self.tabs.cfg_dict = {}
        # make the tabs closeable
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.closeTab)
        #self.setCentralWidget(self.tabs)
        # add the text editor to the first tab
        self.tabs.addTab(logTextBox.textBox, "Log")
        self.tabs.tab_index_all = self.tabs.tab_index_all + 1
        # hide the tab close icon for the console tab
        self.tabs.tabBar().setTabButton(0, QtGui.QTabBar.RightSide, None)
        # connect the tab-in-focus signal to the appropriate slot
        self.tabs.connect(self.tabs, QtCore.SIGNAL("currentChanged(int)"), self.tabSelected)

        # use VBoxLayout to position widgets so they resize with main window
        layout = QtGui.QVBoxLayout()
        # add widgets to the layout
        layout.addWidget(self.menubar)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setGeometry(50,50,800, 600)

        # Connect signals to slots
        # File menu actions
        self.actionFileConvertnc2biomet.triggered.connect(pfp_top_level.do_file_convert_biomet)
        self.actionFileConvertnc2xls.triggered.connect(pfp_top_level.do_file_convert_nc2xls)
        self.actionFileConvertnc2fluxnet.triggered.connect(pfp_top_level.do_file_convert_nc2fluxnet)
        self.actionFileConvertnc2reddyproc.triggered.connect(pfp_top_level.do_file_convert_nc2reddyproc)
        self.actionFileOpen.triggered.connect(self.open_controlfile)
        self.actionFileSave.triggered.connect(self.save_controlfile)
        self.actionFileSaveAs.triggered.connect(self.saveas_controlfile)
        self.actionFileConcatenate.triggered.connect(pfp_top_level.do_file_concatenate)
        self.actionFileSplit.triggered.connect(pfp_top_level.do_file_split)
        self.actionFileQuit.triggered.connect(QtGui.qApp.quit)
        # Edit menu actions
        self.actionEditPreferences.triggered.connect(self.edit_preferences)
        # Run menu actions
        self.actionRunCurrent.triggered.connect(self.run_current)
        self.actionRunL1.triggered.connect(pfp_top_level.do_run_l1)
        self.actionRunL2.triggered.connect(pfp_top_level.do_run_l2)
        self.actionRunL3.triggered.connect(pfp_top_level.do_run_l3)
        self.actionRunL4.triggered.connect(lambda:pfp_top_level.do_run_l4(self))
        self.actionRunL5.triggered.connect(pfp_top_level.do_run_l5)
        self.actionRunL6.triggered.connect(pfp_top_level.do_run_l6)
        # Plot menu actions
        self.actionPlotL1.triggered.connect(pfp_top_level.do_plot_l1)
        self.actionPlotL2.triggered.connect(pfp_top_level.do_plot_l2)
        self.actionPlotL3.triggered.connect(pfp_top_level.do_plot_l3)
        self.actionPlotL4.triggered.connect(pfp_top_level.do_plot_l4)
        self.actionPlotL5.triggered.connect(pfp_top_level.do_plot_l5)
        self.actionPlotL6.triggered.connect(pfp_top_level.do_plot_l6)
        self.actionPlotFingerprints.triggered.connect(pfp_top_level.do_plot_fingerprints)
        self.actionPlotQuickCheck.triggered.connect(pfp_top_level.do_plot_quickcheck)
        self.actionPlotTimeSeries.triggered.connect(pfp_top_level.do_plot_timeseries)
        self.actionPlotClosePlots.triggered.connect(pfp_top_level.do_plot_closeplots)
        # Utilities menu actions
        self.actionUtilitiesClimatology.triggered.connect(pfp_top_level.do_utilities_climatology)
        self.actionUtilitiesUstarCPD.triggered.connect(pfp_top_level.do_utilities_ustar_cpd)
        # add the L4 GUI
        self.l4_ui = pfp_gui.pfp_l4_ui(self)

    def open_controlfile(self):
        # get the control file path
        cfgpath = QtGui.QFileDialog.getOpenFileName(caption="Choose a control file ...")
        # read the contents of the control file
        self.cfg = ConfigObj(str(cfgpath))
        self.cfg["level"] = self.get_cf_level()
        # create a QtTreeView to edit the control file
        if self.cfg["level"] in ["L1", "L2", "L3"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L1L2L3(self.cfg)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["concatenate"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_concatenate(self.cfg)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["L4"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L4(self.cfg)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["L5", "L6"]:
            logger.error(" Level "+self.cfg["level"]+" not implemented yet")
        else:
            logger.error(" Unrecognised control file type: "+self.cfg["level"])
        # add a tab for the control file
        self.tabs.addTab(self.tabs.tab_dict[self.tabs.tab_index_all], os.path.basename(str(cfgpath)))
        self.tabs.setCurrentIndex(self.tabs.tab_index_all)
        self.tabs.tab_index_all = self.tabs.tab_index_all + 1

    def get_cf_level(self):
        """ Sniff the control file to find out it's type."""
        if "level" in self.cfg:
            return self.cfg["level"]
        # check for L1
        if self.check_cfg_L1():
            logger.info(" L1 control file detected")
            self.cfg["level"] = "L1"
        # check for L2
        elif self.check_cfg_L2():
            logger.info(" L2 control file detected")
            self.cfg["level"] = "L2"
        # check for L3
        elif self.check_cfg_L3():
            logger.info(" L3 control file detected")
            self.cfg["level"] = "L3"
        # check for concatenate
        elif self.check_cfg_concatenate():
            logger.info(" Concatenate control file detected")
            self.cfg["level"] = "concatenate"
        # check for L4
        elif self.check_cfg_L4():
            logger.info(" L4 control file detected")
            self.cfg["level"] = "L4"
        return self.cfg["level"]

    def check_cfg_L1(self):
        """ Return true if a control file is an L1 file."""
        result = False
        cfg_sections = self.cfg.keys()
        # remove the common sections
        common_sections = ["Files", "Global", "Output", "Plots", "General", "Options", "Soil", "Massman", "GUI"]
        for section in list(self.cfg.keys()):
            if section in common_sections:
                cfg_sections.remove(section)
        # now loop over the remaining sections
        for section in cfg_sections:
            subsections = self.cfg[section].keys()
            for subsection in subsections:
                if "Attr" in self.cfg[section][subsection].keys():
                    result = True
                    break
        return result

    def check_cfg_L2(self):
        """ Return true if a control file is an L2 file."""
        result = False
        got_sections = False
        cfg_sections = self.cfg.keys()
        if (("Files" in cfg_sections) and
            ("Variables" in cfg_sections)):
            got_sections = True
        # remove the common sections
        common_sections = ["Files", "Global", "Output", "Plots", "General", "Options", "Soil",
                           "Massman", "GUI"]
        for section in list(self.cfg.keys()):
            if section in common_sections:
                cfg_sections.remove(section)
        # loop over remaining sections
        got_qc = False
        qc_list = ["RangeCheck", "DiurnalCheck", "ExcludeDates", "DependencyCheck", "UpperCheck",
                   "LowerCheck", "ExcludeHours", "Linear", "CorrectWindDirection"]
        for section in cfg_sections:
            subsections = self.cfg[section].keys()
            for subsection in subsections:
                for qc in qc_list:
                    if qc in self.cfg[section][subsection].keys():
                        got_qc = True
                        break
        # final check
        if got_sections and got_qc and not self.check_cfg_L3() and not self.check_cfg_L4():
            result = True
        return result

    def check_cfg_L3(self):
        """ Return true if a control file is an L3 file."""
        result = False
        cfg_sections = self.cfg.keys()
        if (("General" in cfg_sections) or
            ("Soil" in cfg_sections) or
            ("Massman" in cfg_sections)):
            result = True
        return result

    def check_cfg_concatenate(self):
        """ Return true if control file is concatenation."""
        result = False
        cfg_sections = self.cfg.keys()
        if "Files" in cfg_sections:
            if (("Out" in self.cfg["Files"].keys()) and
                ("In" in self.cfg["Files"].keys())):
                result = True
        return result

    def check_cfg_L4(self):
        """ Return true if control file is L4."""
        result = False
        cfg_sections = self.cfg.keys()
        # remove the common sections
        common_sections = ["Files", "Global", "Output", "Plots", "General", "Options", "Soil", "Massman", "GUI"]
        for section in cfg_sections:
            if section in common_sections:
                cfg_sections.remove(section)
        # now loop over the remaining sections
        for section in cfg_sections:
            subsections = self.cfg[section].keys()
            for subsection in subsections:
                if (("GapFillFromAlternate" in self.cfg[section][subsection].keys()) or
                    ("GapFillFromClimatology" in self.cfg[section][subsection].keys()) or
                    ("MergeSeries" in self.cfg[section][subsection].keys())):
                    result = True
                    break
        return result

    def save_controlfile(self):
        print "Save goes here"
        pass

    def saveas_controlfile(self):
        print "Save As goes here"
        pass

    def edit_preferences(self):
        print "Edit/Preferences goes here"
        pass

    def tabSelected(self, arg=None):
        self.tabs.tab_index_current = arg

    def run_current(self):
        # save the current tab index
        tab_index_current = self.tabs.tab_index_current
        # set the focus back to the log tab
        self.tabs.setCurrentIndex(0)
        # call the appropriate processing routine depending on the level
        if self.tabs.cfg_dict[tab_index_current]["level"] == "L1":
            pfp_top_level.do_run_l1(cfg=self.tabs.cfg_dict[tab_index_current])
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L2":
            pfp_top_level.do_run_l2(cfg=self.tabs.cfg_dict[tab_index_current])
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L3":
            pfp_top_level.do_run_l3(cfg=self.tabs.cfg_dict[tab_index_current])
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "concatenate":
            pfp_top_level.do_file_concatenate(cfg=self.tabs.cfg_dict[tab_index_current])
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L4":
            pfp_top_level.do_run_l4(self, cfg=self.tabs.cfg_dict[tab_index_current])
        else:
            logger.error("Level not implemented yet ...")

    def closeTab (self, currentIndex):
        """ Close the selected tab."""
        # get the current tab from its index
        currentQWidget = self.tabs.widget(currentIndex)
        # delete the tab
        currentQWidget.deleteLater()
        self.tabs.removeTab(currentIndex)
        # remove the corresponding entry in cfg_dict
        self.tabs.cfg_dict.pop(currentIndex)
        # remove the corresponding entry in tab_dict
        self.tabs.tab_dict.pop(currentIndex)
        # decrement the tab index
        self.tabs.tab_index_all = self.tabs.tab_index_all - 1

if (__name__ == '__main__'):
    app = QtGui.QApplication(["PyFluxPro"])
    ui = pfp_main_ui()
    ui.show()
    sys.exit(app.exec_())