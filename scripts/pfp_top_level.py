# standard modules
import logging
import os
# 3rd party modules
import matplotlib
from PyQt4 import QtCore
# PFP modules
import pfp_clim
import pfp_compliance
import pfp_cpd
import pfp_mpt
import pfp_io
import pfp_levels
import pfp_plot
import pfp_utils
import pfp_footprint
import pfp_windrose

logger = logging.getLogger("pfp_log")
# top level routines for the File menu
def do_file_concatenate(cfg=None):
    """
    Purpose:
     Top level routine for concatenating multiple, single-year files into
     a single, multiple-year file.
     NOTE: The input files must be listed in the control file in chronological
           order.
    Usage:
     pfp_top_level.do_file_concatenate()
    Side effects:
     Creates a single netCDF file containing the contents of the input files.
    Author: PRI
    Date: Back in the day
    Mods:
     June 2018: rewrite for use with new GUI.
    """
    logger.info(" Starting concatenation of netCDF files")
    if not cfg:
        cfg = pfp_io.load_controlfile(path="controlfiles")
        if len(cfg) == 0:
            logger.info("Quitting concatenation (no control file)")
            return
    pfp_io.nc_concatenate(cfg)
    logger.info(" Finished concatenating files")
    logger.info("")
    return
def do_file_convert_biomet():
    logger.warning("File/Convert/nc to biomet not implemented yet")
    return
def do_file_convert_nc2ecostress(cfg=None):
    """
    Purpose:
     Convert a PFP-style netCDF file to an ECOSTRESS CSV file.
    Usage:
    Side effects:
     Creates a CSV file in the same directory as the netCDF file.
    Author: PRI
    Date: Back in the day
    Mods:
     September 2018: rewrite for use with new GUI
    """
    logger.info(" Starting conversion to ECOSTRESS file")
    if not cfg:
        # check to see if there is an nc2ecostress.txt control file in controlfiles/standard
        #  if there is
        #   open controlfiles/standard/nc2csv_ecostress.txt
        #   ask for netCDF file name
        #   add [Files] section to control file
        stdname = "controlfiles/standard/nc2csv_ecostress.txt"
        if os.path.exists(stdname):
            cfg = pfp_io.get_controlfilecontents(stdname)
            filename = pfp_io.get_filename_dialog(file_path="../Sites", title="Choose a netCDF file")
            if len(filename) == 0:
                return
            if "Files" not in dir(cfg):
                cfg["Files"] = {}
            cfg["Files"]["file_path"] = os.path.join(os.path.split(filename)[0], "")
            cfg["Files"]["in_filename"] = os.path.split(filename)[1]
        else:
            cfg = pfp_io.load_controlfile(path="controlfiles")
            if len(cfg) == 0:
                return
    if "Options" not in cfg:
        cfg["Options"]={}
    cfg["Options"]["call_mode"] = "interactive"
    result = pfp_io.write_csv_ecostress(cfg)
    if result == 0:
        logger.info(" Finished converting netCDF file")
        logger.info("")
    else:
        logger.error("")
        logger.error(" An error occured, check the log messages")
        logger.error("")
    return
def do_file_convert_nc2xls():
    """
    Purpose:
     Convert a PFP-style netCDF file to an Excel workbook.
    Usage:
    Side effects:
     Creates an Excel workbook in the same directory as the netCDF file.
    Author: PRI
    Date: Back in the day
    Mods:
     August 2018: rewrite for use with new GUI
    """
    logger.info(" Starting conversion to Excel file")
    ncfilename = pfp_io.get_filename_dialog(file_path="../Sites",title="Choose a netCDF file", ext="*.nc")
    if len(ncfilename)==0:
        return
    logger.info(" Converting netCDF file to Excel file")
    pfp_io.nc_2xls(ncfilename, outputlist=None)
    logger.info(" Finished converting netCDF file")
    logger.info("")
    return
def do_file_convert_nc2fluxnet():
    logger.warning("File/Convert/nc to Fluxnet not implemented yet")
    return
def do_file_convert_nc2reddyproc():
    logger.warning("File/Convert/nc to REddyProc not implemented yet")
    return
def do_file_convert_ncupdate(cfg=None):
    """
    Purpose:
     Convert from original netCDF files to V1 (October 2018).
    Usage:
    Author: PRI
    Date: October 2018
    """
    logger.info(" Starting conversion of netCDF")
    if not cfg:
        # check to see if there is an nc2ecostress.txt control file in controlfiles/standard
        #  if there is
        #   open controlfiles/standard/nc2csv_ecostress.txt
        #   ask for netCDF file name
        #   add [Files] section to control file
        stdname = os.path.join("controlfiles", "standard", "map_old_to_new.txt")
        if os.path.exists(stdname):
            cfg = pfp_io.get_controlfilecontents(stdname)
            filename = pfp_io.get_filename_dialog(file_path="../OzFlux/Sites", title="Choose a netCDF file")
            if len(filename) == 0:
                return
            if "Files" not in dir(cfg):
                cfg["Files"] = {}
            cfg["Files"]["file_path"] = os.path.join(os.path.split(filename)[0], "")
            cfg["Files"]["in_filename"] = os.path.split(filename)[1]
        else:
            cfg = pfp_io.load_controlfile(path="controlfiles")
            if len(cfg) == 0:
                return
    if "Options" not in cfg:
        cfg["Options"]={}
    cfg["Options"]["call_mode"] = "interactive"
    result = pfp_compliance.nc_update(cfg)
    if result == 0:
        logger.info(" Finished converting netCDF file")
        logger.info("")
    else:
        logger.error("")
        logger.error(" An error occured, check the log messages")
        logger.error("")
    return
def do_file_split():
    logger.warning("File/Split not implemented yet")
    return
# top level routines for the Run menu
def do_run_l1(cfg=None):
    """
    Purpose:
     Top level routine for running the L1 data import.
    Usage:
     pfp_top_level.do_l1()
    Side effects:
     Creates an L1 netCDF file.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting L1 processing")
    if not cfg:
        cfg = pfp_io.load_controlfile()
        if len(cfg)==0:
            logger.info("Quiting L1 processing (no control file)")
            return
    ds1 = pfp_levels.l1qc(cfg)
    if ds1.returncodes["value"] == 0:
        outfilename = pfp_io.get_outfilenamefromcf(cfg)
        ncFile = pfp_io.nc_open_write(outfilename)
        pfp_io.nc_write_series(ncFile, ds1)
        logger.info("Finished L1 processing")
        logger.info("")
    else:
        msg = "An error occurred during L1 processing"
        logger.error(msg)
    return
def do_run_l2(cfg=None):
    """
    Purpose:
     Top level routine for running the L2 quality control.
    Usage:
     pfp_top_level.do_l2()
    Side effects:
     Creates an L2 netCDF file.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting L2 processing")
    if not cfg:
        cfg = pfp_io.load_controlfile()
        if len(cfg)==0:
            logger.info("Quiting L2 processing (no control file)")
            return
    in_filepath = pfp_io.get_infilenamefromcf(cfg)
    if not pfp_utils.file_exists(in_filepath):
        in_filename = os.path.split(in_filepath)
        logger.error("File "+in_filename[1]+" not found")
        return
    ds1 = pfp_io.nc_read_series(in_filepath)
    ds2 = pfp_levels.l2qc(cfg, ds1)
    if ds2.returncodes["value"] != 0:
        logger.error("An error occurred during L2 processing")
        logger.error("")
        return
    out_filepath = pfp_io.get_outfilenamefromcf(cfg)
    nc_file = pfp_io.nc_open_write(out_filepath)
    pfp_io.nc_write_series(nc_file, ds2)
    logger.info("Finished L2 processing")
    logger.info("Plotting L1 and L2 data")
    for nFig in cfg['Plots'].keys():
        plt_cf = cfg['Plots'][str(nFig)]
        if 'Type' in plt_cf.keys():
            if str(plt_cf['Type']).lower() =='xy':
                pfp_plot.plotxy(cfg, nFig, plt_cf, ds1, ds2)
            else:
                pfp_plot.plottimeseries(cfg, nFig, ds1, ds2)
        else:
            pfp_plot.plottimeseries(cfg, nFig, ds1, ds2)
    logger.info("Finished plotting L1 and L2 data")
    logger.info("")
    return
def do_run_l3(cfg=None):
    """
    Purpose:
     Top level routine for running the L23 post-processing.
    Usage:
     pfp_top_level.do_l3()
    Side effects:
     Creates an L3 netCDF file.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting L3 processing")
    if not cfg:
        cfg = pfp_io.load_controlfile()
        if len(cfg) == 0:
            logger.info("Quiting L3 processing (no control file)")
            return
    in_filepath = pfp_io.get_infilenamefromcf(cfg)
    if not pfp_utils.file_exists(in_filepath):
        in_filename = os.path.split(in_filepath)
        logger.error("File "+in_filename[1]+" not found")
        return
    ds2 = pfp_io.nc_read_series(in_filepath)
    ds3 = pfp_levels.l3qc(cfg, ds2)
    if ds3.returncodes["value"] != 0:
        logger.error("An error occurred during L3 processing")
        logger.error("")
        return
    out_filepath = pfp_io.get_outfilenamefromcf(cfg)
    nc_file = pfp_io.nc_open_write(out_filepath)
    pfp_io.nc_write_series(nc_file, ds3)
    logger.info("Finished L3 processing")
    logger.info("Plotting L3 data")
    for nFig in cfg['Plots'].keys():
        plt_cf = cfg['Plots'][str(nFig)]
        if 'Type' in plt_cf.keys():
            if str(plt_cf['Type']).lower() =='xy':
                pfp_plot.plotxy(cfg, nFig, plt_cf, ds2, ds3)
            else:
                pfp_plot.plottimeseries(cfg, nFig, ds2, ds3)
        else:
            pfp_plot.plottimeseries(cfg, nFig, ds2, ds3)
    logger.info("Finished plotting L3 data")
    logger.info("")
    return
def do_run_l4(main_gui, cfg=None):
    """
    Purpose:
     Top level routine for running the L4 gap filling.
    Usage:
     pfp_top_level.do_run_l4()
    Side effects:
     Creates an L4 netCDF file with gap filled meteorology.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting L4 processing")
    if not cfg:
        cfg = pfp_io.load_controlfile(path='controlfiles')
        if len(cfg) == 0:
            logger.info("Quiting L4 processing (no control file)")
            return
    in_filepath = pfp_io.get_infilenamefromcf(cfg)
    if not pfp_utils.file_exists(in_filepath):
        in_filename = os.path.split(in_filepath)
        logger.error("File "+in_filename[1]+" not found")
        return
    ds3 = pfp_io.nc_read_series(in_filepath)
    #ds3.globalattributes['controlfile_name'] = cfg['controlfile_name']
    sitename = ds3.globalattributes['site_name']
    if "Options" not in cfg:
        cfg["Options"]={}
    cfg["Options"]["call_mode"] = "interactive"
    ds4 = pfp_levels.l4qc(main_gui, cfg, ds3)
    if ds4.returncodes["alternate"]=="quit":
        logger.info("Quitting L4: "+sitename)
    else:
        logger.info("Finished L4: "+sitename)
        out_filepath = pfp_io.get_outfilenamefromcf(cfg)
        nc_file = pfp_io.nc_open_write(out_filepath)
        pfp_io.nc_write_series(nc_file, ds4)         # save the L4 data
        logger.info("Finished saving L4 gap filled data")
    logger.info("")
    return
def do_run_l5(main_gui, cfg=None):
    """
    Purpose:
     Top level routine for running the L5 gap filling.
    Usage:
     pfp_top_level.do_run_l5()
    Side effects:
     Creates an L5 netCDF file with gap filled meteorology.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting L5 processing")
    if not cfg:
        cfg = pfp_io.load_controlfile(path='controlfiles')
        if len(cfg) == 0:
            logger.info("Quiting L5 processing (no control file)")
            return
    in_filepath = pfp_io.get_infilenamefromcf(cfg)
    if not pfp_utils.file_exists(in_filepath):
        in_filename = os.path.split(in_filepath)
        logger.error("File "+in_filename[1]+" not found")
        return
    ds4 = pfp_io.nc_read_series(in_filepath)
    #ds4.globalattributes['controlfile_name'] = cfg['controlfile_name']
    sitename = ds4.globalattributes['site_name']
    if "Options" not in cfg:
        cfg["Options"] = {}
    cfg["Options"]["call_mode"] = "interactive"
    ds5 = pfp_levels.l5qc(main_gui, cfg, ds4)
    if ds5.returncodes["solo"] == "quit":
        logger.info("Quitting L5: "+sitename)
    else:
        logger.info("Finished L5: "+sitename)
        out_filepath = pfp_io.get_outfilenamefromcf(cfg)
        nc_file = pfp_io.nc_open_write(out_filepath)
        pfp_io.nc_write_series(nc_file, ds5)
        logger.info("Finished saving L5 gap filled data")
    logger.info("")
    return
def do_run_l6(main_gui, cfg=None):
    """
    Purpose:
     Top level routine for running the L6 gap filling.
    Usage:
     pfp_top_level.do_run_l6()
    Side effects:
     Creates an L6 netCDF file with NEE partitioned into GPP and ER.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting L6 processing")
    if not cfg:
        cfg = pfp_io.load_controlfile(path='controlfiles')
        if len(cfg) == 0:
            logger.info("Quiting L6 processing (no control file)")
            return
    in_filepath = pfp_io.get_infilenamefromcf(cfg)
    if not pfp_utils.file_exists(in_filepath):
        in_filename = os.path.split(in_filepath)
        logger.error("File "+in_filename[1]+" not found")
        return
    ds5 = pfp_io.nc_read_series(in_filepath)
    #ds5.globalattributes['controlfile_name'] = cfg['controlfile_name']
    sitename = ds5.globalattributes['site_name']
    if "Options" not in cfg:
        cfg["Options"] = {}
    cfg["Options"]["call_mode"] = "interactive"
    ds6 = pfp_levels.l6qc(main_gui, cfg, ds5)
    if ds6.returncodes["solo"] == "quit":
        logger.info("Quitting L6: "+sitename)
    else:
        logger.info("Finished L6: "+sitename)
        out_filepath = pfp_io.get_outfilenamefromcf(cfg)
        nc_file = pfp_io.nc_open_write(out_filepath)
        pfp_io.nc_write_series(nc_file, ds6)
        logger.info("Finished saving L6 gap filled data")
    logger.info("")
    return
# top level routines for the Plot menu
def do_plot_l1():
    logger.warning("L1 plotting not implemented yet")
    return
def do_plot_l2():
    logger.warning("L2 plotting not implemented yet")
    return
def do_plot_l3():
    logger.warning("L3 plotting not implemented yet")
    return
def do_plot_l4():
    logger.warning("L4 plotting not implemented yet")
    return
def do_plot_l5():
    logger.warning("L5 plotting not implemented yet")
    return
def do_plot_l6():
    logger.warning("L6 plotting not implemented yet")
    return
def do_plot_fcvsustar():
    """
    Purpose:
     Plot Fc versus u*.
    Usage:
     pfp_top_level.do_plot_fcvsustar()
    Side effects:
     Annual and seasonal plots of Fc versus u* to the screen and creates .PNG
     hardcopies of the plots.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting Fc versus u* plots")
    file_path = pfp_io.get_filename_dialog(file_path="../Sites",title="Choose a netCDF file")
    if len(file_path) == 0 or not os.path.isfile(file_path):
        return
    # read the netCDF file
    ds = pfp_io.nc_read_series(file_path)
    logger.info(" Plotting Fc versus u* ...")
    pfp_plot.plot_fcvsustar(ds)
    logger.info("Finished plotting Fc versus u*")
    logger.info("")
    return
def do_plot_fingerprints():
    """
    Purpose:
     Plot fingerprints using the standard fingerprint control file.
    Usage:
     pfp_top_level.do_plot_fingerprints()
    Side effects:
     Plots fingerprints to the screen and creates .PNG hardcopies of
     the plots.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting fingerprint plot")
    stdname = "controlfiles/standard/fingerprint.txt"
    if os.path.exists(stdname):
        cf = pfp_io.get_controlfilecontents(stdname)
        filename = pfp_io.get_filename_dialog(file_path="../Sites",title="Choose a netCDF file")
        if len(filename)==0:
            return
        if "Files" not in dir(cf): cf["Files"] = {}
        cf["Files"]["file_path"] = os.path.split(filename)[0]+"/"
        cf["Files"]["in_filename"] = os.path.split(filename)[1]
    else:
        cf = pfp_io.load_controlfile(path="controlfiles")
        if len(cf)==0:
            return
    logger.info("Loaded control file ...")
    if "Options" not in cf: cf["Options"]={}
    cf["Options"]["call_mode"] = "interactive"
    logger.info(" Plotting fingerprint ...")
    pfp_plot.plot_fingerprint(cf)
    logger.info("Finished plotting fingerprint")
    logger.info("")
    return
def do_plot_quickcheck():
    """
    Purpose:
     Plot summaries of data, usually L3 and above.
    Usage:
     pfp_top_level.do_plot_quickcheck()
    Side effects:
     Plots summaries to the screen and creates .PNG hardcopies of
     the plots.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting summary plots")
    stdname = "controlfiles/standard/quickcheck.txt"
    if os.path.exists(stdname):
        cf = pfp_io.get_controlfilecontents(stdname)
        filename = pfp_io.get_filename_dialog(file_path="../Sites",title="Choose a netCDF file")
        if len(filename)==0:
            return
        if "Files" not in dir(cf): cf["Files"] = {}
        cf["Files"]["file_path"] = os.path.split(filename)[0]+"/"
        cf["Files"]["in_filename"] = os.path.split(filename)[1]
    else:
        cf = pfp_io.load_controlfile(path="controlfiles")
        if len(cf)==0:
            return
    logger.info("Loaded control file ...")
    if "Options" not in cf: cf["Options"]={}
    cf["Options"]["call_mode"] = "interactive"
    logger.info(" Plotting summary plots ...")
    pfp_plot.plot_quickcheck(cf)
    logger.info("Finished plotting summaries")
    logger.info("")
    return
def do_plot_timeseries():
    """
    Purpose:
     Plot time series of data, usually L3 and above.
    Usage:
     pfp_top_level.do_plot_timeseries()
    Side effects:
     Plots timeseries to the screen and creates .PNG hardcopies of
     the plots.
    Author: PRI
    Date: Back in the day
    Mods:
     December 2017: rewrite for use with new GUI
    """
    logger.info("Starting timeseries plot")
    stdname = "controlfiles/standard/fluxnet.txt"
    if os.path.exists(stdname):
        cf = pfp_io.get_controlfilecontents(stdname)
        filename = pfp_io.get_filename_dialog(file_path="../Sites",title="Choose a netCDF file")
        if len(filename)==0:
            return
        if "Files" not in dir(cf): cf["Files"] = {}
        cf["Files"]["file_path"] = os.path.split(filename)[0]+"/"
        cf["Files"]["in_filename"] = os.path.split(filename)[1]
    else:
        cf = pfp_io.load_controlfile(path="controlfiles")
        if len(cf)==0:
            return
    logger.info("Loaded control file ...")
    if "Options" not in cf: cf["Options"]={}
    cf["Options"]["call_mode"] = "interactive"
    logger.info(" Plotting time series ...")
    pfp_plot.plot_fluxnet(cf)
    logger.info("Finished plotting fingerprint")
    logger.info("")
    return
def do_plot_windrose():
    """
    Purpose:
     Plot windrose of data, usually L3 and above.
    Usage:
     pfp_top_level.do_plot_windrose()
    Side effects:
     Plots windrose to the screen and creates .PNG hardcopies of
     the plots.
    Author: CME
    Date: a while ago
    Mods:
     March 2019: rewrite for use with new GUI
    """
    logger.info("Starting windrose plot")
    stdname = "controlfiles/standard/windrose.txt"
    if os.path.exists(stdname):
        cf = pfp_io.get_controlfilecontents(stdname)
        filename = pfp_io.get_filename_dialog(file_path="../Sites",title="Choose a netCDF file")
        if len(filename)==0:
            return
        if "Files" not in dir(cf): cf["Files"] = {}
        cf["Files"]["file_path"] = os.path.split(filename)[0]+"/"
        cf["Files"]["in_filename"] = os.path.split(filename)[1]
    else:
        cf = pfp_io.load_controlfile(path="controlfiles")
        if len(cf)==0:
            return
    logger.info("Loaded control file ...")
    if "Options" not in cf: cf["Options"]={}
    cf["Options"]["call_mode"] = "interactive"
    logger.info(" Plotting windrose ...")
    pfp_windrose.windrose_main(cf)
    logger.info("Finished plotting windrose")
    logger.info("")
    return
def do_plot_closeplots():
    """
    Close plot windows.
    """
    logger.info("Closing plot windows ...")
    matplotlib.pyplot.close("all")
    return
# top level routines for the Utilities menu
def do_utilities_climatology(mode="standard"):
    logger.info(" Starting climatology")
    if mode == "standard":
        stdname = "controlfiles/standard/climatology.txt"
        if os.path.exists(stdname):
            cf = pfp_io.get_controlfilecontents(stdname)
            filename = pfp_io.get_filename_dialog(file_path="../Sites", title='Choose a netCDF file')
            if not os.path.exists(filename):
                logger.info( " Climatology: no input file chosen")
                return
            if "Files" not in cf:
                cf["Files"] = {}
            cf["Files"]["file_path"] = os.path.join(os.path.split(filename)[0],"")
            in_filename = os.path.split(filename)[1]
            cf["Files"]["in_filename"] = in_filename
            cf["Files"]["out_filename"] = in_filename.replace(".nc", "_Climatology.xls")
        else:
            cf = pfp_io.load_controlfile(path="controlfiles")
            if len(cf) == 0:
                return
    else:
        logger.info("Loading control file ...")
        cf = pfp_io.load_controlfile(path='controlfiles')
        if len(cf) == 0:
            return
    logger.info("Doing the climatology")
    pfp_clim.climatology(cf)
    logger.info(' Finished climatology')
    logger.info("")
    return
def do_utilities_ustar_cpd(mode="standard"):
    logger.info(" Starting u* threshold detection (CPD)")
    if mode == "standard":
        stdname = "controlfiles/standard/cpd.txt"
        if os.path.exists(stdname):
            cf = pfp_io.get_controlfilecontents(stdname)
            filename = pfp_io.get_filename_dialog(file_path="../Sites", title="Choose a netCDF file")
            if not os.path.exists(filename):
                logger.info( " CPD: no input file chosen")
                return
            if "Files" not in cf:
                cf["Files"] = {}
            cf["Files"]["file_path"] = os.path.join(os.path.split(filename)[0],"")
            in_filename = os.path.split(filename)[1]
            cf["Files"]["in_filename"] = in_filename
            cf["Files"]["out_filename"] = in_filename.replace(".nc", "_CPD.xls")
        else:
            cf = pfp_io.load_controlfile(path="controlfiles")
            if len(cf) == 0:
                return
    else:
        logger.info("Loading control file ...")
        cf = pfp_io.load_controlfile(path='controlfiles')
        if len(cf) == 0:
            return
    logger.info("Doing u* threshold detection (CPD)")
    pfp_cpd.cpd_main(cf)
    logger.info(" Finished u* threshold detection (CPD)")
    logger.info("")
    return
def do_utilities_ustar_mpt(mode="standard"):
    """
    Calls pfp_mpt.mpt_main
    Calculate the u* threshold using the Moving Point Threshold (MPT) method.
    """
    logger.info(" Starting u* threshold detection (MPT)")
    if mode == "standard":
        stdname = "controlfiles/standard/mpt.txt"
        if os.path.exists(stdname):
            cf = pfp_io.get_controlfilecontents(stdname)
            filename = pfp_io.get_filename_dialog(file_path='../Sites', title="Choose a netCDF file")
            if not os.path.exists(filename):
                logger.info( " MPT: no input file chosen")
                return
            if "Files" not in dir(cf):
                cf["Files"] = {}
            cf["Files"]["file_path"] = os.path.join(os.path.split(filename)[0], "")
            in_filename = os.path.split(filename)[1]
            cf["Files"]["in_filename"] = in_filename
            cf["Files"]["out_filename"] = in_filename.replace(".nc", "_MPT.xls")
        else:
            cf = pfp_io.load_controlfile(path="controlfiles")
            if len(cf) == 0:
                return
    else:
        logger.info("Loading control file ...")
        cf = pfp_io.load_controlfile(path="controlfiles")
        if len(cf) == 0:
            return
    logger.info(" Doing u* threshold detection (MPT)")
    if "Options" not in cf:
        cf["Options"] = {}
    cf["Options"]["call_mode"] = "interactive"
    pfp_mpt.mpt_main(cf)
    logger.info(" Finished u* threshold detection (MPT)")
    logger.info("")
    return

def do_utilities_footprint(mode="standard"):
    """
    Calls pfp_footprint.footprint_main
    Calculate the footprint using either Natasha Kljun's 2015 or Kormann and Meixner 2001 method.
    """
    logger.info(" Starting footprint calculation")
    if mode == "standard":
        stdname = "controlfiles/standard/footprint.txt"
        if os.path.exists(stdname):
            cf = pfp_io.get_controlfilecontents(stdname)
            filename = pfp_io.get_filename_dialog(file_path='../Sites', title="Choose a netCDF file")
            if not os.path.exists(filename):
                logger.info( " FootPrint: no input file chosen")
                return
            if "Files" not in dir(cf):
                cf["Files"] = {}
            cf["Files"]["file_path"] = os.path.join(os.path.split(filename)[0], "")
            in_filename = os.path.split(filename)[1]
            cf["Files"]["in_filename"] = in_filename
            cf["Files"]["out_filename"] = in_filename.replace(".nc", "_FP.xls")
        else:
            cf = pfp_io.load_controlfile(path="controlfiles")
            if len(cf) == 0:
                return
    else:
        logger.info("Loading control file ...")
        cf = pfp_io.load_controlfile(path="controlfiles")
        if len(cf) == 0:
            return
    logger.info(" Doing footprint calculation")
    if "Options" not in cf:
        cf["Options"] = {}
    cf["Options"]["call_mode"] = "interactive"
    pfp_footprint.footprint_main(cf,mode)
    logger.info(" Finished footprint calculation")
    logger.info("")
    return
