# standard modules
import copy
import logging
import os
import sys
import time
# force QVariant API to V2 to avoid AttributeErrors on Mac OS X
import sip
sip.setapi('QVariant', 2)
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
# now check the logfiles and plots directories are present
dir_list = ["./logfiles/", "./plots/"]
for item in dir_list:
    if not os.path.exists(item):
        os.makedirs(item)
# now check the solo/inf, solo/input, solo/log and solo/output directories are present
dir_list = ["./solo/inf", "./solo/input", "./solo/log", "./solo/output"]
for item in dir_list:
    if not os.path.exists(item):
        os.makedirs(item)
# next we make sure the MPT directories are present ...
dir_list = ["./mpt/input", "./mpt/log", "./mpt/output"]
for item in dir_list:
    if not os.path.exists(item):
        os.makedirs(item)
# ... and make sure the MDS directories are present
dir_list = ["./mds/input", "./mds/log", "./mds/output"]
for item in dir_list:
    if not os.path.exists(item):
        os.makedirs(item)

logger = logging.getLogger("pfp_log")
logfmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s','%H:%M:%S')
logger.setLevel(logging.DEBUG)

class myMessageBox(QtGui.QMessageBox):
    def __init__(self, msg, title="Information", parent=None):
        super(myMessageBox, self).__init__(parent)
        self.setIcon(QtGui.QMessageBox.Information)
        self.setText(msg)
        self.setWindowTitle(title)
        self.setStandardButtons(QtGui.QMessageBox.Ok)
        self.exec_()

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
        self.actionFileSaveAs.setShortcut('Shift+Ctrl+S')
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
        self.actionFileConvertnc2ecostress = QtGui.QAction(self)
        self.actionFileConvertnc2ecostress.setText("nc to ECOSTRESS")
        self.actionFileConvertnc2xls = QtGui.QAction(self)
        self.actionFileConvertnc2xls.setText("nc to Excel")
        self.actionFileConvertnc2fluxnet = QtGui.QAction(self)
        self.actionFileConvertnc2fluxnet.setText("nc to FluxNet")
        self.actionFileConvertnc2reddyproc = QtGui.QAction(self)
        self.actionFileConvertnc2reddyproc.setText("nc to REddyProc")
        self.actionFileConvertncupdate = QtGui.QAction(self)
        self.actionFileConvertncupdate.setText("nc update")
        # Edit menu items
        self.actionEditPreferences = QtGui.QAction(self)
        self.actionEditPreferences.setText("Preferences...")
        # Run menu items
        self.actionRunCurrent = QtGui.QAction(self)
        self.actionRunCurrent.setText("Current...")
        self.actionRunCurrent.setShortcut('Ctrl+R')
        # Plot menu items
        self.actionPlotFcVersusUstar = QtGui.QAction(self)
        self.actionPlotFcVersusUstar.setText("Fc vs u*")
        self.actionPlotFingerprints = QtGui.QAction(self)
        self.actionPlotFingerprints.setText("Fingerprints")
        self.actionPlotQuickCheck = QtGui.QAction(self)
        self.actionPlotQuickCheck.setText("Summary")
        self.actionPlotTimeSeries = QtGui.QAction(self)
        self.actionPlotTimeSeries.setText("Time series")
        self.actionPlotClosePlots = QtGui.QAction(self)
        self.actionPlotClosePlots.setText("Close plots")
        # Utilities menu
        self.actionUtilitiesClimatology = QtGui.QAction(self)
        self.actionUtilitiesClimatology.setText("Climatology")
        self.actionUtilitiesUstarCPD = QtGui.QAction(self)
        self.actionUtilitiesUstarCPD.setText("u* threshold (CPD)")
        self.actionUtilitiesUstarMPT = QtGui.QAction(self)
        self.actionUtilitiesUstarMPT.setText("u* threshold (MPT)")
        # add the actions to the menus
        # File/Convert submenu
        self.menuFileConvert.addAction(self.actionFileConvertnc2xls)
        self.menuFileConvert.addAction(self.actionFileConvertnc2biomet)
        self.menuFileConvert.addAction(self.actionFileConvertnc2ecostress)
        self.menuFileConvert.addAction(self.actionFileConvertnc2fluxnet)
        self.menuFileConvert.addAction(self.actionFileConvertnc2reddyproc)
        self.menuFileConvert.addAction(self.actionFileConvertncupdate)
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
        # Plot menu
        self.menuPlot.addAction(self.actionPlotFcVersusUstar)
        self.menuPlot.addAction(self.actionPlotFingerprints)
        self.menuPlot.addAction(self.actionPlotQuickCheck)
        self.menuPlot.addAction(self.actionPlotTimeSeries)
        self.menuPlot.addSeparator()
        self.menuPlot.addAction(self.actionPlotClosePlots)
        # Utilities menu
        self.menuUtilities.addAction(self.actionUtilitiesClimatology)
        self.menuUtilities.addAction(self.actionUtilitiesUstarCPD)
        self.menuUtilities.addAction(self.actionUtilitiesUstarMPT)
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
        self.actionFileConvertnc2ecostress.triggered.connect(pfp_top_level.do_file_convert_nc2ecostress)
        self.actionFileConvertnc2xls.triggered.connect(pfp_top_level.do_file_convert_nc2xls)
        self.actionFileConvertnc2fluxnet.triggered.connect(pfp_top_level.do_file_convert_nc2fluxnet)
        self.actionFileConvertnc2reddyproc.triggered.connect(pfp_top_level.do_file_convert_nc2reddyproc)
        self.actionFileConvertncupdate.triggered.connect(pfp_top_level.do_file_convert_ncupdate)
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
        # Plot menu actions
        self.actionPlotFcVersusUstar.triggered.connect(pfp_top_level.do_plot_fcvsustar)
        self.actionPlotFingerprints.triggered.connect(pfp_top_level.do_plot_fingerprints)
        self.actionPlotQuickCheck.triggered.connect(pfp_top_level.do_plot_quickcheck)
        self.actionPlotTimeSeries.triggered.connect(pfp_top_level.do_plot_timeseries)
        self.actionPlotClosePlots.triggered.connect(pfp_top_level.do_plot_closeplots)
        # Utilities menu actions
        self.actionUtilitiesClimatology.triggered.connect(lambda:pfp_top_level.do_utilities_climatology(mode="standard"))
        self.actionUtilitiesUstarCPD.triggered.connect(lambda:pfp_top_level.do_utilities_ustar_cpd(mode="standard"))
        self.actionUtilitiesUstarMPT.triggered.connect(lambda:pfp_top_level.do_utilities_ustar_mpt(mode="standard"))
        # add the L4 GUI
        self.l4_ui = pfp_gui.pfp_l4_ui(self)
        # add the L5 GUI
        self.l5_ui = pfp_gui.pfp_l5_ui(self)

    def open_controlfile(self):
        # get the control file path
        cfgpath = QtGui.QFileDialog.getOpenFileName(caption="Choose a control file ...")
        cfgpath = str(cfgpath)
        # check to see if file open was cancelled
        if len(str(cfgpath)) == 0:
            return
        # read the contents of the control file
        logger.info(" Opening "+cfgpath)
        self.cfg = ConfigObj(cfgpath, indent_type="    ", list_values=False)
        self.cfg["level"] = self.get_cf_level()
        # create a QtTreeView to edit the control file
        if self.cfg["level"] in ["L1"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L1(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["L2"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L2(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["L3"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L3(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["concatenate"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_concatenate(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["L4"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L4(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["L5"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L5(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["L6"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_L6(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        elif self.cfg["level"] in ["nc2csv_ecostress"]:
            self.tabs.tab_dict[self.tabs.tab_index_all] = pfp_gui.edit_cfg_nc2csv_ecostress(self)
            self.tabs.cfg_dict[self.tabs.tab_index_all] = self.tabs.tab_dict[self.tabs.tab_index_all].get_data_from_model()
            self.tabs.cfg_dict[self.tabs.tab_index_all]["controlfile_name"] = cfgpath
        else:
            logger.error(" Unrecognised control file type: "+self.cfg["level"])
        # add a tab for the control file
        self.tabs.addTab(self.tabs.tab_dict[self.tabs.tab_index_all], os.path.basename(str(cfgpath)))
        self.tabs.setCurrentIndex(self.tabs.tab_index_all)
        if self.tabs.tab_dict[self.tabs.tab_index_all].cfg_changed:
            self.update_tab_text()
        self.tabs.tab_index_all = self.tabs.tab_index_all + 1

    def get_cf_level(self):
        """ Sniff the control file to find out it's type."""
        if "level" in self.cfg:
            return self.cfg["level"]
        self.cfg["level"] = ""
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
        # check for L5
        elif self.check_cfg_L5():
            logger.info(" L5 control file detected")
            self.cfg["level"] = "L5"
        # check for L6
        elif self.check_cfg_L6():
            logger.info(" L6 control file detected")
            self.cfg["level"] = "L6"
        else:
            logger.info(" Unable to detect level, enter manually ...")
            text, ok = QtGui.QInputDialog.getText(self, 'Processing level', 'Enter the processing level:')
            if ok:
                self.cfg["level"] = text
        return self.cfg["level"]

    def check_cfg_L1(self):
        """ Return true if a control file is an L1 file."""
        result = False
        try:
            cfg_sections = self.cfg.keys()
            # remove the common sections
            common_sections = ["level", "controlfile_name", "Files", "Global", "Output",
                               "Plots", "General", "Options", "Soil", "Massman", "GUI"]
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
        except:
            result = False
        return result

    def check_cfg_L2(self):
        """ Return true if a control file is an L2 file."""
        result = False
        try:
            got_sections = False
            cfg_sections = self.cfg.keys()
            if (("Files" in cfg_sections) and
                ("Variables" in cfg_sections)):
                got_sections = True
            # loop over [Variables] sections
            got_qc = False
            qc_list = ["RangeCheck", "DiurnalCheck", "ExcludeDates", "DependencyCheck", "UpperCheck",
                       "LowerCheck", "ExcludeHours", "Linear", "CorrectWindDirection"]
            for section in ["Variables"]:
                subsections = self.cfg[section].keys()
                for subsection in subsections:
                    for qc in qc_list:
                        if qc in self.cfg[section][subsection].keys():
                            got_qc = True
                            break
            # final check
            if got_sections and got_qc and not self.check_cfg_L3() and not self.check_cfg_L4():
                result = True
        except:
            result = False
        return result

    def check_cfg_L3(self):
        """ Return true if a control file is an L3 file."""
        result = False
        try:
            cfg_sections = self.cfg.keys()
            if ((("General" in cfg_sections) or
                ("Soil" in cfg_sections) or
                ("Massman" in cfg_sections)) and
                ("Options" in cfg_sections)):
                result = True
        except:
            result = False
        return result

    def check_cfg_concatenate(self):
        """ Return true if control file is concatenation."""
        result = False
        try:
            cfg_sections = self.cfg.keys()
            if "Files" in cfg_sections:
                if (("Out" in self.cfg["Files"].keys()) and
                    ("In" in self.cfg["Files"].keys())):
                    result = True
        except:
            result = False
        return result

    def check_cfg_L4(self):
        """ Return true if control file is L4."""
        result = False
        try:
            cfg_sections = self.cfg.keys()
            for section in cfg_sections:
                if section in ["Variables", "Drivers", "Fluxes"]:
                    subsections = self.cfg[section].keys()
                    for subsection in subsections:
                        if (("GapFillFromAlternate" in self.cfg[section][subsection].keys()) or
                            ("GapFillFromClimatology" in self.cfg[section][subsection].keys())):
                            result = True
                            break
        except:
            result = False
        return result

    def check_cfg_L5(self):
        """ Return true if control file is L5."""
        result = False
        try:
            cfg_sections = self.cfg.keys()
            for section in cfg_sections:
                if section in ["Variables", "Drivers", "Fluxes"]:
                    subsections = self.cfg[section].keys()
                    for subsection in subsections:
                        if (("GapFillUsingSOLO" in self.cfg[section][subsection].keys()) or
                            ("GapFillUsingMDS" in self.cfg[section][subsection].keys())):
                            result = True
                            break
        except:
            result = False
        return result

    def check_cfg_L6(self):
        """ Return true if control file is L6."""
        result = False
        try:
            cfg_sections = self.cfg.keys()
            if ("ER" in cfg_sections) or ("NEE" in cfg_sections) or ("GPP" in cfg_sections):
                result = True
        except:
            result = False
        return result

    def direct_run(self):
        """ Placeholder until full implementation done."""
        msg = " Open control file and use 'Run/Current ...'"
        logger.warning(msg)
        return

    def save_controlfile(self):
        """ Save the current tab as a control file."""
        # get the current tab index
        tab_index_current = self.tabs.tab_index_current
        # get the control file name
        cfg_filename = self.tabs.cfg_dict[tab_index_current]["controlfile_name"]
        # get the updated control file data
        cfg = self.tabs.tab_dict[tab_index_current].get_data_from_model()
        # check to make sure we are not overwriting the template version
        if "template" not in cfg_filename:
            # set the control file name
            cfg.filename = cfg_filename
        else:
            msg = " You are trying to write to the template folder.\n"
            msg = msg + "Please save this control file to a different location."
            msgbox = myMessageBox(msg)
            # put up a "Save as ..." dialog
            cfg_filename = QtGui.QFileDialog.getSaveFileName(self, "Save as ...")
            # return without doing anything if cancel used
            if len(str(cfg_filename)) == 0:
                return
            # set the control file name
            cfg.filename = str(cfg_filename)
        # write the control file
        logger.info(" Saving "+cfg.filename)
        cfg.write()
        # remove the asterisk in the tab text
        tab_text = str(self.tabs.tabText(tab_index_current))
        self.tabs.setTabText(self.tabs.tab_index_current, tab_text.replace("*",""))
        # reset the cfg changed logical to false
        self.tabs.tab_dict[tab_index_current].cfg_changed = False

    def saveas_controlfile(self):
        """ Save the current tab with a different name."""
        # get the current tab index
        tab_index_current = self.tabs.tab_index_current
        # get the updated control file data
        cfg = self.tabs.tab_dict[tab_index_current].get_data_from_model()
        # put up a "Save as ..." dialog
        cfgpath = QtGui.QFileDialog.getSaveFileName(self, "Save as ...")
        # return without doing anything if cancel used
        if len(str(cfgpath)) == 0:
            return
        # set the control file name
        cfg.filename = str(cfgpath)
        # write the control file
        logger.info(" Saving "+cfg.filename)        
        cfg.write()
        # update the tab text
        self.tabs.setTabText(tab_index_current, os.path.basename(str(cfgpath)))
        # reset the cfg changed logical to false
        self.tabs.tab_dict[tab_index_current].cfg_changed = False

    def edit_preferences(self):
        print "Edit/Preferences goes here"
        pass

    def tabSelected(self, arg=None):
        self.tabs.tab_index_current = arg

    def run_current(self):
        # save the current tab index
        tab_index_current = self.tabs.tab_index_current
        if tab_index_current == 0:
            msg = " No control file selected ..."
            logger.warning(msg)
            return
        # get the updated control file data
        cfg = self.tabs.tab_dict[tab_index_current].get_data_from_model()
        # set the focus back to the log tab
        self.tabs.setCurrentIndex(0)
        # call the appropriate processing routine depending on the level
        self.tabs.tab_index_running = tab_index_current
        if self.tabs.cfg_dict[tab_index_current]["level"] == "L1":
            pfp_top_level.do_run_l1(cfg=cfg)
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L2":
            pfp_top_level.do_run_l2(cfg=cfg)
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L3":
            pfp_top_level.do_run_l3(cfg=cfg)
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "concatenate":
            pfp_top_level.do_file_concatenate(cfg=cfg)
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L4":
            pfp_top_level.do_run_l4(self, cfg=cfg)
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L5":
            pfp_top_level.do_run_l5(self, cfg=cfg)
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "L6":
            pfp_top_level.do_run_l6(self, cfg=cfg)
        elif self.tabs.cfg_dict[tab_index_current]["level"] == "nc2csv_ecostress":
            pfp_top_level.do_file_convert_nc2ecostress(cfg=cfg)
        else:
            logger.error("Level not implemented yet ...")

    def closeTab (self, currentIndex):
        """ Close the selected tab."""
        # check to see if the tab contents have been saved
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" in tab_text:
            msg = "Save control file?"
            reply = QtGui.QMessageBox.question(self, 'Message', msg,
                                               QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.save_controlfile()
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
        return

    def update_tab_text(self):
        """ Add an asterisk to the tab title text to indicate tab contents have changed."""
        # add an asterisk to the tab text to indicate the tab contents have changed
        tab_text = str(self.tabs.tabText(self.tabs.tab_index_current))
        if "*" not in tab_text:
            self.tabs.setTabText(self.tabs.tab_index_current, tab_text+"*")

if (__name__ == '__main__'):
    app = QtGui.QApplication(["PyFluxPro"])
    ui = pfp_main_ui()
    ui.show()
    sys.exit(app.exec_())
