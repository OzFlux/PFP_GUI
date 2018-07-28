# standard modules
import logging
import os
# 3rd party modules
import matplotlib
from PyQt4 import QtCore
# PFP modules
import pfp_clim
import pfp_cpd
import pfp_io
import pfp_levels
import pfp_plot
import pfp_utils

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
        cfg = pfp_io.load_controlfile(path='controlfiles')
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
def do_file_convert_nc2xls():
    logger.warning("File/Convert/nc to Excel not implemented yet")
    return
def do_file_convert_nc2fluxnet():
    logger.warning("File/Convert/nc to Fluxnet not implemented yet")
    return
def do_file_convert_nc2reddyproc():
    logger.warning("File/Convert/nc to REddyProc not implemented yet")
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
    ds3.globalattributes['controlfile_name'] = cfg['controlfile_name']
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
    ds4.globalattributes['controlfile_name'] = cfg['controlfile_name']
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
def do_run_l6():
    logger.warning("L6 processing not implemented yet")
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
        filename = pfp_io.get_filename_dialog(path="../Sites",title="Choose a netCDF file")
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
    logger.info("Plotting fingerprint ...")
    pfp_plot.plot_fingerprint(cf)
    logger.info("Finished plotting fingerprint")
    logger.info("")
    return
def do_plot_quickcheck():
    logger.warning("Quick check plotting not implemented yet")
    return
def do_plot_timeseries():
    logger.warning("Time series plotting not implemented yet")
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
            filename = pfp_io.get_filename_dialog(path="../Sites", title='Choose a netCDF file')
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
            filename = pfp_io.get_filename_dialog(path="../Sites", title='Choose a netCDF file')
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
