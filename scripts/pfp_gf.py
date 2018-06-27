import ast
from calendar import isleap
from configobj import ConfigObj
import constants as c
import csv
import datetime
import dateutil
import logging
import numpy
import matplotlib as mpl
import matplotlib.dates as mdt
import matplotlib.pyplot as plt
import os
import platform
import pylab
import pfp_ck
import pfp_io
import pfp_ts
import pfp_utils
import scipy
import scipy.odr
import shutil
import statsmodels.api as sm
import subprocess
import sys
import time
import Tkinter
import warnings
import xlrd
from PyQt4 import QtGui

# suppress deprecation warning from matplotlib on use of matplotlib.pyplot.pause()
warnings.filterwarnings("ignore",".*GUI is implemented.*")

logger = logging.getLogger("pfp_log")

# GapFillParseControlFile parses the L4 control file
def GapFillParseControlFile(cf,ds,series,ds_alt):
    # find the section containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return empty handed if the series is not in a section
    if len(section)==0: return
    if "GapFillFromAlternate" in cf[section][series].keys():
        # create the alternate dictionary in ds
        gfalternate_createdict(cf,ds,series,ds_alt)
    if "GapFillUsingSOLO" in cf[section][series].keys():
        # create the SOLO dictionary in ds
        gfSOLO_createdict(cf,ds,series)
    if "GapFillFromClimatology" in cf[section][series].keys():
        # create the climatology dictionary in the data structure
        gfClimatology_createdict(cf,ds,series)
    if "MergeSeries" in cf[section][series].keys():
        # create the merge series dictionary in the data structure
        gfMergeSeries_createdict(cf,ds,series)

# function to handle MergeSeries keys in L4 control file
def gfMergeSeries_createdict(cf,ds,series):
    """ Creates a dictionary in ds to hold information about the merging of gap filled
        and tower data."""
    merge_prereq_list = ["Fsd","Fsu","Fld","Flu","Ts","Sws"]
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # create the merge directory in the data structure
    if "merge" not in dir(ds): ds.merge = {}
    # check to see if this series is in the "merge first" list
    # series in the "merge first" list get merged first so they can be used with existing tower
    # data to re-calculate Fg, Fn and Fa
    merge_order = "standard"
    if series in merge_prereq_list: merge_order = "prerequisite"
    if merge_order not in ds.merge.keys(): ds.merge[merge_order] = {}
    # create the dictionary keys for this series
    ds.merge[merge_order][series] = {}
    # output series name
    ds.merge[merge_order][series]["output"] = series
    # site name
    ds.merge[merge_order][series]["source"] = ast.literal_eval(cf[section][series]["MergeSeries"]["Source"])
    # create an empty series in ds if the output series doesn't exist yet
    if ds.merge[merge_order][series]["output"] not in ds.series.keys():
        data,flag,attr = pfp_utils.MakeEmptySeries(ds,ds.merge[merge_order][series]["output"])
        pfp_utils.CreateSeries(ds,ds.merge[merge_order][series]["output"],data,flag,attr)

# functions for GapFillFluxFromDayRatio: deprecated
def GapFillFluxFromDayRatio(cf,ds,series=''):
    section = pfp_utils.get_cfsection(cf,series=series,mode='quiet')
    if len(section)==0: return
    if 'GapFillFluxFromDayRatio' not in cf[section][series].keys(): return
    ndays = 365
    if isleap(ds.series['Year']['Data'][0]): ndays = 366
    dt = int(ds.globalattributes['time_step'])    # time step in minutes
    nts = int(24/(float(dt)/float(60)))           # number of time steps in a day
    nmn = int(12)                                 # number of months in year
    # if no series list passed in then create one
    logger.info(' Gap filling '+series+' using daily ratio (day) and climatology (night)')
    # get the details from the control file
    alt_filename = cf[section][series]['GapFillFluxFromDayRatio']['file_name']
    if not os.path.exists(alt_filename):
        logger.error(" GapFillFromDayRatio: Climatology file "+alt_filename+" doesn't exist")
        return
    xlbook = xlrd.open_workbook(alt_filename)
    ratio_label = cf[section][series]['GapFillFluxFromDayRatio']['ratio_xlSheet']
    ratio_xlsheet = xlbook.sheet_by_name(ratio_label)
    driver_label = cf[section][series]['GapFillFluxFromDayRatio']['drivers']
    flux_xlsheet = xlbook.sheet_by_name(cf[section][series]['GapFillFluxFromDayRatio']['flux_xlSheet'])
    out_label = cf[section][series]['GapFillFluxFromDayRatio']['output']
    # get the data series as masked arrays from the data structure
    Fsd,Fsd_flag,Fsd_attr = pfp_utils.GetSeriesasMA(ds,'Fsd')
    us,us_flag,us_attr = pfp_utils.GetSeriesasMA(ds,'ustar')
    driver,driver_flag,driver_attr = pfp_utils.GetSeriesasMA(ds, driver_label)
    nRecs = len(driver)
    # get the flux series to be gap filled
    flux,flux_flag,flux_attr = pfp_utils.GetSeriesasMA(ds,series)
    # initialise arrays for the ratios and the fluxes
    ratio_ts = numpy.zeros(ndays*nts,dtype=numpy.float64)
    flux_monthly = numpy.zeros((nts,nmn),dtype=numpy.float64)
    # read the ratio from the climatology workbook
    for xlRow in range(ndays):
        ratio_ts[xlRow*nts:(xlRow+1)*nts] = ratio_xlsheet.row_values(xlRow+2,start_colx=1,end_colx=nts+1)
    # add an extra constraint (WUE must be <0 during the day) if we are doing Fc
    # PRI - relocated from original position in code (just before calls to CreateSeries
    #       and eventually deprecated as it may be dangerous
    #if 'Fc' in ThisOne: index = numpy.ma.where((Fsd>50)&(ratio_ts<0))
    # read the monthly flux data from the climatology workbook
    for xlCol in range(nmn):
        flux_monthly[:,xlCol] = flux_xlsheet.col_values(xlCol+1)[2:nts+2]
    # now we interpolate the climatological fluxes from monthly to a daily time step
    flux_monthly_tiled = numpy.tile(flux_monthly,(3,3))                              # tile the climatological flux into a 3 by 3 matrix
    nx = numpy.shape(flux_monthly_tiled)[1]; ny = numpy.shape(flux_monthly_tiled)[0] # get the dimensions of the original flux array
    nxi = ndays*3; nyi = numpy.shape(flux_monthly_tiled)[0]                          # get the dimensions of the daily array (still tiled)
    x = numpy.linspace(1,nx,nx); y = numpy.linspace(1,ny,ny)                         # 1d array of x and y dimension indices, tiled original
    xi = numpy.linspace(1,nx,nxi); yi = numpy.linspace(1,ny,nyi)                     # 1d array of x and y dimension indices, tiled interpolated
    # interpolate from monthly to daily time step
    nk = scipy.interpolate.RectBivariateSpline(y,x,flux_monthly_tiled,kx=2,ky=2)     # quadratic spline
    flux_daily_tiled = nk(yi,xi)                                                     # do the interpolation
    flux_daily = flux_daily_tiled[nyi/3:2*nyi/3,nxi/3:2*nxi/3]                       # pick out the central tile (still a 2D array)
    flux_ic = numpy.ravel(flux_daily,order='F')                                      # convert 2D array to 1D array, same length as data series, correct order
    # calculate the flux from the ratio (EF, BR or WUE) and the driver (Fa, Fe or Fe)
    flux_rd = ratio_ts * driver
    # create the gap filling series and initialise it to the interpolated climatological fluxes
    flux_gf = flux_ic.copy()
    # now figure out when its daytime and night time
    index = numpy.ma.where(Fsd>50)[0]
    # replace the interpolated climatological fluxes with the daytime values
    # calculated from the ratio (EF, BR or WUE) and the driver (Fa, Fe or Fe)
    flux_gf[index] = flux_rd[index]
    # generate a QC flag to indicate data has been estimated from ratios (day time)
    # and interpolated climatology (night time).
    flag = numpy.array([60]*nRecs,dtype=numpy.int32)
    # put the gap filled data into the data structure
    units=pfp_utils.GetUnitsFromds(ds, series)
    attr = pfp_utils.MakeAttributeDictionary(long_name='gap filled using ratio (daily)',units=units)
    pfp_utils.CreateSeries(ds,out_label,flux_gf,flag,attr)
    attr = pfp_utils.MakeAttributeDictionary(long_name='interpolated '+ratio_label,units='None')
    pfp_utils.CreateSeries(ds,ratio_label,ratio_ts,flag,attr)
    attr = pfp_utils.MakeAttributeDictionary(long_name='ratio times driver',units=units)
    pfp_utils.CreateSeries(ds,series+'_rd',flux_rd,flag,attr)
    attr = pfp_utils.MakeAttributeDictionary(long_name='interpolated climatological fluxes',units=units)
    pfp_utils.CreateSeries(ds,series+'_ic',flux_ic,flag,attr)
    if 'GapFillFluxFromDayRatio' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+', GapFillFluxFromDayRatio'

# functions for GapFillUsingMDS: not implemented yet
def GapFillFluxUsingMDS(cf,ds,series=""):
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    if len(section)==0: return
    if "GapFillFluxUsingMDS" in cf[section][series].keys():
        logger.info(" GapFillFluxUsingMDS: not implemented yet")
        return

# functions for GapFillFromClimatology
def GapFillFromClimatology(ds):
    '''
    Gap fill missing data using data from the climatology spreadsheet produced by
    the climatology.py script.
    '''
    if "climatology" not in dir(ds): return
    # tell the user what we are going to do
    msg = " Reading climatology file and creating climatology series"
    logger.info(msg)
    # loop over the series to be gap filled using climatology
    cli_xlbooks = {}
    for output in ds.climatology.keys():
        # check to see if there are any gaps in "series"
        #index = numpy.where(abs(ds.series[label]['Data']-float(c.missing_value))<c.eps)[0]
        #if len(index)==0: continue                      # no gaps found in "series"
        cli_filename = ds.climatology[output]["file_name"]
        if not os.path.exists(cli_filename):
            logger.error(" GapFillFromClimatology: Climatology file "+cli_filename+" doesn't exist")
            continue
        if cli_filename not in cli_xlbooks: cli_xlbooks[cli_filename] = xlrd.open_workbook(cli_filename)
        # local pointers to the series name and climatology method
        label = ds.climatology[output]["label_tower"]
        method = ds.climatology[output]["method"]
        # do the gap filling
        # choose the gap filling method
        if method=="monthly":
            gfClimatology_monthly(ds,label,output,cli_xlbooks)
        elif method=="interpolated daily":
            gfClimatology_interpolateddaily(ds,label,output,cli_xlbooks)
        else:
            logger.error(" GapFillFromClimatology: unrecognised method option for "+label)
            continue
    if 'GapFillFromClimatology' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+', GapFillFromClimatology'
    # remove the "climatology" attribute from ds
    #del ds.climatology

def gfClimatology_createdict(cf,ds,series):
    """ Creates a dictionary in ds to hold information about the climatological data used
        to gap fill the tower data."""
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("GapFillFromClimatology: Series "+series+" not found in control file, skipping ...")
        return
    # create the climatology directory in the data structure
    if "climatology" not in dir(ds): ds.climatology = {}
    # name of alternate output series in ds
    output_list = cf[section][series]["GapFillFromClimatology"].keys()
    # loop over the outputs listed in the control file
    for output in output_list:
        # create the dictionary keys for this output
        ds.climatology[output] = {}
        ds.climatology[output]["label_tower"] = series
        # site name
        ds.climatology[output]["site_name"] = ds.globalattributes["site_name"]
        # Climatology file name
        file_list = cf["Files"].keys()
        lower_file_list = [item.lower() for item in file_list]
        # first, look in the [Files] section for a generic file name
        if "climatology" in lower_file_list:
            # found a generic file name
            i = lower_file_list.index("climatology")
            ds.climatology[output]["file_name"] = cf["Files"][file_list[i]]
        else:
            # no generic file name found, look for a file name in the variable section
            ds.climatology[output]["file_name"] = cf[section][series]["GapFillFromClimatology"][output]["file_name"]
        # climatology variable name if different from name used in control file
        if "climatology_name" in cf[section][series]["GapFillFromClimatology"][output]:
            ds.climatology[output]["climatology_name"] = cf[section][series]["GapFillFromClimatology"][output]["climatology_name"]
        else:
            ds.climatology[output]["climatology_name"] = series
        # climatology gap filling method
        if "method" not in cf[section][series]["GapFillFromClimatology"][output].keys():
            # default if "method" missing is "interpolated_daily"
            ds.climatology[output]["method"] = "interpolated_daily"
        else:
            ds.climatology[output]["method"] = cf[section][series]["GapFillFromClimatology"][output]["method"]
        # create an empty series in ds if the climatology output series doesn't exist yet
        if output not in ds.series.keys():
            data,flag,attr = pfp_utils.MakeEmptySeries(ds,output)
            pfp_utils.CreateSeries(ds,output,data,flag,attr)

def gfClimatology_interpolateddaily(ds,series,output,xlbooks):
    """
    Gap fill using data interpolated over a 2D array where the days are
    the rows and the time of day is the columns.
    """
    # gap fill from interpolated 30 minute data
    xlfilename = ds.climatology[output]["file_name"]
    sheet_name = series+'i(day)'
    if sheet_name not in xlbooks[xlfilename].sheet_names():
        msg = " gfClimatology: sheet "+sheet_name+" not found, skipping ..."
        logger.warning(msg)
        return
    ts = ds.globalattributes["time_step"]
    ldt = ds.series["DateTime"]["Data"]
    thissheet = xlbooks[xlfilename].sheet_by_name(sheet_name)
    datemode = xlbooks[xlfilename].datemode
    basedate = datetime.datetime(1899, 12, 30)
    nts = thissheet.ncols - 1
    ndays = thissheet.nrows - 2
    # read the time stamp values from the climatology worksheet
    tsteps = thissheet.row_values(1,start_colx=1,end_colx=nts+1)
    # read the data from the climatology workbook
    val1d = numpy.ma.zeros(ndays*nts,dtype=numpy.float64)
    # initialise an array for the datetime of the climatological values
    cdt = [None]*nts*ndays
    # loop over the rows (days) of data
    for xlRow in range(ndays):
        # get the Excel datetime value
        xldatenumber = int(thissheet.cell_value(xlRow+2,0))
        # convert this to a Python Datetime
        xldatetime = basedate+datetime.timedelta(days=xldatenumber+1462*datemode)
        # fill the climatology datetime array
        cdt[xlRow*nts:(xlRow+1)*nts] = [xldatetime+datetime.timedelta(hours=hh) for hh in tsteps]
        # fill the climatological value array
        val1d[xlRow*nts:(xlRow+1)*nts] = thissheet.row_values(xlRow+2,start_colx=1,end_colx=nts+1)
    # get the data to be filled with climatological values
    data,flag,attr = pfp_utils.GetSeriesasMA(ds,series)
    # get an index of missing values
    idx = numpy.where(numpy.ma.getmaskarray(data)==True)[0]
    #idx = numpy.ma.where(numpy.ma.getmaskarray(data)==True)[0]
    # there must be a better way to do this ...
    # simply using the index (idx) to set a slice of the data array to the gap filled values in val1d
    # does not seem to work (mask stays true on replaced values in data), the work around is to
    # step through the indices, find the time of the missing value in data, find the same time in the
    # gap filled values val1d and set the missing element of data to this element of val1d
    # actually ...
    # this may not be the fastest but it may be the most robust because it matches dates of missing data
    # to dates in the climatology file
    li = 0
    for ii in idx:
        try:
            jj = cdt.index(ldt[ii],li)
            li = jj
            data[ii] = val1d[jj]
            flag[ii] = numpy.int32(40)
        except ValueError:
            data[ii] = numpy.float64(c.missing_value)
            flag[ii] = numpy.int32(41)
    # put the gap filled data back into the data structure
    pfp_utils.CreateSeries(ds,output,data,flag,attr)

def gfClimatology_monthly(ds,series,output,xlbook):
    """ Gap fill using monthly climatology."""
    thissheet = xlbook.sheet_by_name(series)
    val1d = numpy.zeros_like(ds.series[series]['Data'])
    values = numpy.zeros([48,12])
    for month in range(1,13):
        xlCol = (month-1)*5 + 2
        values[:,month-1] = thissheet.col_values(xlCol)[2:50]
    for i in range(len(ds.series[series]['Data'])):
        h = numpy.int(2*ds.series['Hdh']['Data'][i])
        m = numpy.int(ds.series['Month']['Data'][i])
        val1d[i] = values[h,m-1]
    ds.series[output]['Data'][index] = val1d[index]
    ds.series[output]['Flag'][index] = numpy.int32(40)

# functions for GapFillFromAlternate
def GapFillFromAlternate(self, cf, ds4, ds_alt):
    '''
    This is the gap fill from alternate data GUI.
    The alternate data gap fill GUI is displayed separately from the main OzFluxQC GUI.
    It consists of text to display the start and end datetime of the file,
    two entry boxes for the start and end datetimes of the alternate data gap fill and
    a button to insert the gap fill data ("Run") and a button to exit ("Done")
    the GUI when we are done.  On exit, the OzFluxQC main GUI continues
    and eventually writes the gap filled data to file.
    '''
    # set the default return code
    ds4.returncodes["alternate"] = "normal"
    if "alternate" not in dir(ds4): return
    # get a local pointer to the tower datetime series
    ldt_tower = ds4.series["DateTime"]["Data"]
    # get the start and end datetime of the tower data
    startdate = ldt_tower[0]
    enddate = ldt_tower[-1]
    # create the alternate_info dictionary, this will hold much useful information
    alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                      "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                      "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                      "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf,["Options"],"call_mode",default="interactive")
    alternate_info["call_mode"]= call_mode
    if call_mode.lower()=="interactive": alternate_info["show_plots"] = True
    if call_mode.lower()=="interactive":
        # put up a plot of the data coverage at L3
        gfalternate_plotcoveragelines(ds4,alternate_info)
        # call the GapFillFromAlternate GUI
        gfalternate_gui(self, cf, ds4,  ds_alt, alternate_info)
    else:
        if "GUI" in cf:
            if "Alternate" in cf["GUI"]:
                gfalternate_run_nogui(cf,ds4,ds_alt,alternate_info)
            else:
                logger.warning(" No GUI sub-section found in Options section of control file")
                gfalternate_plotcoveragelines(ds4,alternate_info)
                gfalternate_gui(cf,ds4,ds_alt,alternate_info)
        else:
            logger.warning(" No GUI sub-section found in Options section of control file")
            gfalternate_plotcoveragelines(ds4,alternate_info)
            gfalternate_gui(cf,ds4,ds_alt,alternate_info)

def gfalternate_gui(main_gui, cf, ds4, ds_alt, alternate_info):
    # put up the start and end dates
    start_date = ds4.series["DateTime"]["Data"][0].strftime("%Y-%m-%d %H:%M")
    end_date = ds4.series["DateTime"]["Data"][-1].strftime("%Y-%m-%d %H:%M")
    main_gui.l4_ui.label_DataStartDate_value.setText(start_date)
    main_gui.l4_ui.label_DataEndDate_value.setText(end_date)

    main_gui.l4_ui.RunButton.clicked.connect(lambda:gfalternate_run_gui(ds4, ds_alt, main_gui.l4_ui, alternate_info))
    main_gui.l4_ui.DoneButton.clicked.connect(lambda:gfalternate_done(ds4, main_gui.l4_ui))
    main_gui.l4_ui.QuitButton.clicked.connect(lambda:gfalternate_quit(ds4, main_gui.l4_ui))
    main_gui.l4_ui.show()
    main_gui.l4_ui.exec_()

def gfalternate_autocomplete(ds_tower,ds_alt,alternate_info,mode="verbose"):
    """
    Purpose:
     Gap fill using alternate data with gaps identified automatically.
    Usage:
     This routine is usually called after an initial gap filling process, either manual
     or automatic monthly or number of days, has been done.  It is intended to detect
     remaining gaps, figure out the period either side of the gaps needed to get the
     minimum number of good points and run the gap filling using alternate data on that
     period.
    Side effects:
    Author: PRI
    Date: April 2015
    """
    # needs a re-write to improve the logic and simplify the code
    # - alt_series_list needs to be ordered by decreasing correlation,
    #   as currently written the first alternate variable with the numbers
    #   is chosen
    # - gfalternate_main is called from here AFTER we have figured out
    #   the "best" alternate variable to use but without passing the
    #   alternate variable name, gfalternate_main then figures out the
    #   "best" alternate variable by a different method
    # - there is duplication of functionality between this routine and
    #   gfalternate_main
    # - there are logical inconsistencies between this routine and
    #   gfalternate_main
    mode = "quiet" #"verbose" #"quiet"
    if not alternate_info["auto_complete"]: return
    dt_tower = ds_tower.series["DateTime"]["Data"]
    nRecs = len(dt_tower)
    ts = alternate_info["time_step"]
    si_tower = pfp_utils.GetDateIndex(dt_tower,alternate_info["gui_startdate"],ts=ts,default=0)
    ei_tower = pfp_utils.GetDateIndex(dt_tower,alternate_info["gui_enddate"],ts=ts,default=nRecs-1)
    ldt_tower = dt_tower[si_tower:ei_tower+1]
    nRecs_gui = len(ldt_tower)
    label_tower_list = list(set(alternate_info["series_list"]))
    for label_tower in label_tower_list:
        data_all = {}
        label_composite = label_tower+"_composite"
        not_enough_points = False
        data_composite,flag_composite,attr_composite = pfp_utils.GetSeriesasMA(ds_tower,label_composite,si=si_tower,ei=ei_tower)
        data_tower,flag_tower,attr_tower = pfp_utils.GetSeriesasMA(ds_tower,label_tower,si=si_tower,ei=ei_tower)
        mask_composite = numpy.ma.getmaskarray(data_composite)
        gapstartend = pfp_utils.contiguous_regions(mask_composite)
        if len(gapstartend)==0:
            if mode.lower()!="quiet":
                msg = " autocomplete: composite "+label_composite+" has no gaps to fill, skipping ..."
                logger.info(msg)
            continue
        # now check all of the alternate data sources to see if they have anything to contribute
        gotdataforgap = [False]*len(gapstartend)
        label_output_list = gfalternate_getlabeloutputlist(ds_tower,label_tower)
        for label_output in label_output_list:
            alt_filename = ds_tower.alternate[label_output]["file_name"]
            ds_alternate = ds_alt[alt_filename]
            dt_alternate = ds_alternate.series["DateTime"]["Data"]
            si_alternate = pfp_utils.GetDateIndex(dt_alternate,alternate_info["gui_startdate"],ts=ts,default=0)
            ei_alternate = pfp_utils.GetDateIndex(dt_alternate,alternate_info["gui_enddate"],ts=ts,default=nRecs-1)
            alt_series_list = [item for item in ds_alternate.series.keys() if "_QCFlag" not in item]
            alt_series_list = [item for item in alt_series_list if ds_tower.alternate[label_output]["alternate_name"] in item]
            for label_alternate in alt_series_list:
                data_alt,flag_alt,attr_alt = pfp_utils.GetSeriesasMA(ds_alternate,label_alternate,si=si_alternate,ei=ei_alternate)
                data_all[label_alternate] = data_alt
                for n,gap in enumerate(gapstartend):
                    min_points = max([int(((gap[1]-gap[0])+1)*alternate_info["min_percent"]/100),3*alternate_info["nperhr"]])
                    if numpy.ma.count(data_alt[gap[0]:gap[1]])>=min_points:
                        if mode.lower()!="quiet":
                            msg = " autocomplete: "+label_tower,ldt_tower[gap[0]],ldt_tower[gap[1]]," got data to fill gap"
                            logger.info(msg)
                        gotdataforgap[n] = True
                    if numpy.ma.count_masked(data_tower[gap[0]:gap[1]])==0:
                        if mode.lower()!="quiet":
                            msg = " autocomplete: "+label_tower,ldt_tower[gap[0]],ldt_tower[gap[1]]," no gap to fill"
                            logger.info(msg)
                        gotdataforgap[n] = False
        # finished checking all alternate data sources for data to fill remaining gaps
        if mode.lower()!="quiet": logger.info(" autocomplete: variable "+label_tower+" has "+str(len(gapstartend))+" gaps")
        logger.info(" Auto-complete gap filling for "+label_tower+" ("+str(gotdataforgap.count(True))+" gaps)")
        for n,gap in enumerate(gapstartend):
            alternate_info["autoforce"] = False
            if not gotdataforgap[n]:
                if mode.lower()!="quiet":
                    gap_startdate = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
                    gap_enddate = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
                    msg = " autocomplete: no alternate data for "+gap_startdate+" to "+gap_enddate
                    logger.info(msg)
                continue
            si = max([0,gap[0]])
            ei = min([len(ldt_tower)-1,gap[1]])
            gap_startdate = ldt_tower[si].strftime("%Y-%m-%d %H:%M")
            gap_enddate = ldt_tower[ei].strftime("%Y-%m-%d %H:%M")
            if mode.lower()!="quiet":
                msg = " autocomplete: gap is "+gap_startdate+" to "+gap_enddate
                logger.info(msg)
            min_points = max([int(((gap[1]-gap[0])+1)*alternate_info["min_percent"]/100),3*alternate_info["nperhr"]])
            num_good_points = 0
            num_points_list = data_all.keys()
            for label in data_all.keys():
                if numpy.ma.count(data_all[label][gap[0]:gap[1]])<min_points:
                    num_points_list.remove(label)
                    continue
                ngpts = gfalternate_getnumgoodpoints(data_tower[gap[0]:gap[1]],data_all[label][gap[0]:gap[1]])
                num_good_points = max([num_good_points,ngpts])
            while num_good_points<min_points:
                gap[0] = max(0,gap[0] - alternate_info["nperday"])
                gap[1] = min(nRecs_gui-1,gap[1] + alternate_info["nperday"])
                if gap[0]==0 and gap[1]==nRecs_gui-1:
                    msg = " Unable to find enough good points in data set for "+label_tower
                    logger.error(msg)
                    msg = " Replacing missing tower data with unmodified alternate data"
                    logger.error(msg)
                    gap[0] = 0; gap[1] = -1
                    alternate_info["autoforce"] = True
                    not_enough_points = True
                if not_enough_points: break
                min_points = max([int(((gap[1]-gap[0])+1)*alternate_info["min_percent"]/100),3*alternate_info["nperhr"]])
                for label in num_points_list:
                    ngpts = gfalternate_getnumgoodpoints(data_tower[gap[0]:gap[1]+1],data_all[label][gap[0]:gap[1]+1])
                    if ngpts>num_good_points:
                        num_good_points = ngpts
                        label_alternate_list = [label]
            gapfillperiod_startdate = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
            gapfillperiod_enddate = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
            if mode.lower()!="quiet":
                msg = " autocomplete: gap fill period is "+gapfillperiod_startdate+" to "+gapfillperiod_enddate
                logger.info(msg)
            alternate_info["startdate"] = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
            alternate_info["enddate"] = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
            gfalternate_main(ds_tower,ds_alt,alternate_info,label_tower_list=[label_tower])
            gfalternate_plotcoveragelines(ds_tower,alternate_info)
            if not_enough_points: break

def gfalternate_autocomplete_rewrite(ds_tower,ds_alt,alternate_info,mode="verbose"):
    """
    *** Work in progress ***
    This is intended to be the rewrite of gfalternate_autocomplete.
    Remaining changes to be made:
     - gap filling code inserted
     - make this routine indepedent of gfalternate_main
    Purpose:
     Gap fill using alternate data with gaps identified automatically.
    Usage:
     This routine is usually called after an initial gap filling process, either manual
     or automatic monthly or number of days, has been done.  It is intended to detect
     remaining gaps, figure out the period either side of the gaps needed to get the
     minimum number of good points and run the gap filling using alternate data on that
     period.
    Side effects:
    Author: PRI
    Date: April 2015
    """
    # needs a re-write to improve the logic and simplify the code
    # - alt_series_list needs to be ordered by decreasing correlation,
    #   as currently written the first alternate variable with the numbers
    #   is chosen
    # - gfalternate_main is called from here AFTER we have figured out
    #   the "best" alternate variable to use but without passing the
    #   alternate variable name, gfalternate_main then figures out the
    #   "best" alternate variable by a different method
    # - there is duplication of functionality between this routine and
    #   gfalternate_main
    # - there are logical inconsistencies between this routine and
    #   gfalternate_main
    mode = "quiet" #"verbose" #"quiet"
    if not alternate_info["auto_complete"]: return
    dt_tower = ds_tower.series["DateTime"]["Data"]
    nRecs = len(dt_tower)
    ts = alternate_info["time_step"]
    si_tower = pfp_utils.GetDateIndex(dt_tower,alternate_info["gui_startdate"],ts=ts,default=0)
    ei_tower = pfp_utils.GetDateIndex(dt_tower,alternate_info["gui_enddate"],ts=ts,default=nRecs-1)
    ldt_tower = dt_tower[si_tower:ei_tower+1]
    nRecs_gui = len(ldt_tower)
    label_tower_list = list(set(alternate_info["series_list"]))
    for label_tower in label_tower_list:
        data_all = {}
        label_composite = label_tower+"_composite"
        not_enough_points = False
        data_composite,flag_composite,attr_composite = pfp_utils.GetSeriesasMA(ds_tower,label_composite,si=si_tower,ei=ei_tower)
        data_tower,flag_tower,attr_tower = pfp_utils.GetSeriesasMA(ds_tower,label_tower,si=si_tower,ei=ei_tower)
        mask_composite = numpy.ma.getmaskarray(data_composite)
        gapstartend = pfp_utils.contiguous_regions(mask_composite)
        for gap in gapstartend:
            # skip this if there are no gaps in the tower data
            if numpy.ma.count_masked(data_tower[gap[0]:gap[1]])==0:
                print label_tower,ldt_tower[gap[0]],ldt_tower[gap[1]]," no gaps to fill"
                continue
            min_points = int((gap[1]-gap[0])*alternate_info["min_percent"]/100)
            # clamp min_points to 3 hours or longer
            min_points = max([3*alternate_info["nperhr"],min_points])
            label_output_list = gfalternate_getlabeloutputlist(ds_tower,label_tower)
            for label_output in label_output_list:
                alt_filename = ds_tower.alternate[label_output]["file_name"]
                ds_alternate = ds_alt[alt_filename]
                dt_alternate = ds_alternate.series["DateTime"]["Data"]
                si_alternate = pfp_utils.GetDateIndex(dt_alternate,alternate_info["gui_startdate"],ts=ts,default=0)
                ei_alternate = pfp_utils.GetDateIndex(dt_alternate,alternate_info["gui_enddate"],ts=ts,default=nRecs-1)
                # the list of alternate variables should be in descending order of correlation
                alt_series_list = [item for item in ds_alternate.series.keys() if label_tower in item]
                num_good_points = 0
                for label_alternate in alt_series_list:
                    data_alt,flag_alt,attr_alt = pfp_utils.GetSeriesasMA(ds_alternate,label_alternate,si=si_alternate,ei=ei_alternate)
                    data_all[label_alternate] = data_alt
                    ngpts = gfalternate_getnumgoodpoints(data_tower[gap[0]:gap[1]],data_alt[gap[0]:gap[1]])
                    num_good_points = max([num_good_points,ngpts])
                    print label_tower,label_output,label_alternate,min_points,num_good_points
                    while num_good_points<min_points:
                        gap[0] = max(0,gap[0] - alternate_info["nperday"])
                        gap[1] = min(nRecs_gui-1,gap[1] + alternate_info["nperday"])
                        if gap[0]==0 and gap[1]==nRecs_gui-1:
                            msg = " Unable to find enough good points in data set for "+label_tower
                            logger.error(msg)
                            msg = " Replacing missing tower data with unmodified alternate data"
                            logger.error(msg)
                            gap[0] = 0; gap[1] = -1
                            alternate_info["autoforce"] = True
                            not_enough_points = True
                        if not_enough_points: break
                        ngpts = gfalternate_getnumgoodpoints(data_tower[gap[0]:gap[1]],data_alt[gap[0]:gap[1]])
                        num_good_points = max([num_good_points,ngpts])
                        print label_tower,label_output,label_alternate,num_good_points,min_points,gap[0],gap[1]
                    print "I would gap fill ",label_tower," here from ",ldt_tower[gap[0]],ldt_tower[gap[1]]

def gfalternate_createdataandstatsdict(ldt_tower,data_tower,attr_tower,alternate_info):
    """
    Purpose:
     Creates the data_dict and stat_dict to hold data and statistics during gap filling from
     alternate data sources.
    Usage:
    Side effects:
    Called by:
    Calls:
    Author: PRI
    Date: May 2015
    """
    data_dict = {}
    stat_dict = {}
    label_tower = alternate_info["label_tower"]
    label_composite = alternate_info["label_composite"]
    data_dict["DateTime"] = {"data":ldt_tower}
    data_dict[label_tower] = {"attr":attr_tower,
                              "output_list":[label_tower,label_composite],
                              "data":data_tower}
    data_dict[label_composite] = {"data":numpy.ma.masked_all_like(data_tower),
                                  "fitcorr":numpy.ma.masked_all_like(data_tower),
                                  "attr":attr_tower}
    stat_dict[label_tower] = {"startdate":alternate_info["startdate"],"enddate":alternate_info["enddate"]}
    stat_dict[label_composite] = {"startdate":alternate_info["startdate"],"enddate":alternate_info["enddate"]}
    return data_dict,stat_dict

def gfalternate_createdict(cf,ds,series,ds_alt):
    """
    Purpose:
     Creates a dictionary in ds to hold information about the alternate data used to gap fill the tower data.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("GapFillFromAlternate: Series "+series+" not found in control file, skipping ...")
        return
    # get the tower time step
    ts_tower = int(ds.globalattributes["time_step"])
    # create the alternate directory in the data structure
    if "alternate" not in dir(ds): ds.alternate = {}
    # name of alternate output series in ds
    output_list = cf[section][series]["GapFillFromAlternate"].keys()
    # loop over the outputs listed in the control file
    for output in output_list:
        # create the dictionary keys for this output
        ds.alternate[output] = {}
        ds.alternate[output]["label_tower"] = series
        # source name
        ds.alternate[output]["source"] = cf[section][series]["GapFillFromAlternate"][output]["source"]
        # site name
        ds.alternate[output]["site_name"] = ds.globalattributes["site_name"]
        # alternate data file name
        # first, look in the [Files] section for a generic file name
        file_list = cf["Files"].keys()
        lower_file_list = [item.lower() for item in file_list]
        if ds.alternate[output]["source"].lower() in lower_file_list:
            # found a generic file name
            i = lower_file_list.index(ds.alternate[output]["source"].lower())
            ds.alternate[output]["file_name"] = cf["Files"][file_list[i]]
        else:
            # no generic file name found, look for a file name in the variable section
            ds.alternate[output]["file_name"] = cf[section][series]["GapFillFromAlternate"][output]["file_name"]
        # if the file has not already been read, do it now
        if ds.alternate[output]["file_name"] not in ds_alt:
            ds_alternate = pfp_io.nc_read_series(ds.alternate[output]["file_name"],fixtimestepmethod="round")
            gfalternate_matchstartendtimes(ds,ds_alternate)
            ds_alt[ds.alternate[output]["file_name"]] = ds_alternate
        # get the type of fit
        ds.alternate[output]["fit_type"] = "OLS"
        if "fit" in cf[section][series]["GapFillFromAlternate"][output]:
            if cf[section][series]["GapFillFromAlternate"][output]["fit"].lower() in ["ols","ols_thru0","mrev","replace","rma","odr"]:
                ds.alternate[output]["fit_type"] = cf[section][series]["GapFillFromAlternate"][output]["fit"]
            else:
                logger.info("gfAlternate: unrecognised fit option for series "+output+", used OLS")
        # correct for lag?
        if "lag" in cf[section][series]["GapFillFromAlternate"][output]:
            if cf[section][series]["GapFillFromAlternate"][output]["lag"].lower() in ["no","false"]:
                ds.alternate[output]["lag"] = "no"
            elif cf[section][series]["GapFillFromAlternate"][output]["lag"].lower() in ["yes","true"]:
                ds.alternate[output]["lag"] = "yes"
            else:
                logger.info("gfAlternate: unrecognised lag option for series "+output)
        else:
            ds.alternate[output]["lag"] = "yes"
        # choose specific alternate variable?
        if "usevars" in cf[section][series]["GapFillFromAlternate"][output]:
            ds.alternate[output]["usevars"] = ast.literal_eval(cf[section][series]["GapFillFromAlternate"][output]["usevars"])
        # alternate data variable name if different from name used in control file
        if "alternate_name" in cf[section][series]["GapFillFromAlternate"][output]:
            ds.alternate[output]["alternate_name"] = cf[section][series]["GapFillFromAlternate"][output]["alternate_name"]
        else:
            ds.alternate[output]["alternate_name"] = series
        # results of best fit for plotting later on
        ds.alternate[output]["results"] = {"startdate":[],"enddate":[],"No. points":[],"No. filled":[],
                                           "r":[],"Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                                           "Avg (Tower)":[],"Avg (Alt)":[],
                                           "Var (Tower)":[],"Var (Alt)":[],"Var ratio":[]}
        # create an empty series in ds if the alternate output series doesn't exist yet
        if output not in ds.series.keys():
            data,flag,attr = pfp_utils.MakeEmptySeries(ds,output)
            pfp_utils.CreateSeries(ds,output,data,flag,attr)
            pfp_utils.CreateSeries(ds,series+"_composite",data,flag,attr)

def gfalternate_done(ds,alt_gui):
    """
    Purpose:
     Finishes up after gap filling from alternate data:
      - destroy the GapFillFromAlternate GUI
      - plot the summary statistics
      - write the summary statistics to an Excel file
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # plot the summary statistics
    #gfalternate_plotsummary(ds,alternate_info)
    # destroy the alternate GUI
    #alt_gui.destroy()
    alt_gui.close()
    if len(plt.get_fignums())!=0:
        for i in plt.get_fignums():
            plt.close(i)
    # write Excel spreadsheet with fit statistics
    pfp_io.xl_write_AlternateStats(ds)
    # put the return code into ds.alternate
    ds.returncodes["alternate"] = "normal"

def gfalternate_getalternatevaratmaxr(ds_tower,ds_alternate,alternate_info,mode="verbose"):
    """
    Purpose:
     Get a list of alternate variable names that are sorted based on correlation with the tower data.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # get a list of alternate variables for this tower variable
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    startdate = alternate_info["startdate"]
    enddate = alternate_info["enddate"]
    ts = alternate_info["time_step"]
    ldt_tower = ds_tower.series["DateTime"]["Data"]
    #si_tower = pfp_utils.GetDateIndex(ldt_tower,startdate,ts=ts)
    #ei_tower = pfp_utils.GetDateIndex(ldt_tower,enddate,ts=ts)
    si_tower = alternate_info["si_tower"]
    ei_tower = alternate_info["ei_tower"]
    data_tower,flag_tower,attr_tower = pfp_utils.GetSeriesasMA(ds_tower,label_tower,si=si_tower,ei=ei_tower)
    # local pointers to the start and end indices
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    #si_alternate = pfp_utils.GetDateIndex(ldt_alternate,startdate,ts=ts)
    #ei_alternate = pfp_utils.GetDateIndex(ldt_alternate,enddate,ts=ts)
    si_alternate = alternate_info["si_alternate"]
    ei_alternate = alternate_info["ei_alternate"]
    # create an array for the correlations and a list for the alternate variables in order of decreasing correlation
    if "usevars" not in ds_tower.alternate[label_output]:
        altvar_list = gfalternate_getalternatevarlist(ds_alternate,alternate_info["alternate_name"])
    else:
        altvar_list = ds_tower.alternate[label_output]["usevars"]
    r = numpy.zeros(len(altvar_list))
    # loop over the variables in the alternate file
    for idx,var in enumerate(altvar_list):
        # get the alternate data
        data_alternate,flag,attr = pfp_utils.GetSeriesasMA(ds_alternate,var,si=si_alternate,ei=ei_alternate)
        alternate_info["gotminpoints_alternate"] = gfalternate_gotminpoints(data_alternate,alternate_info,label_tower,mode="quiet")
        if numpy.ma.count(data_alternate)>alternate_info["min_points"]:
            # check the lengths of the tower and alternate data are the same
            if len(data_alternate)!=len(data_tower):
                msg = "gfalternate_getalternatevaratmaxr: alternate data length is "+str(len(data_alternate))
                logger.info(msg)
                msg = "gfalternate_getalternatevaratmaxr: tower data length is "+str(len(data_tower))
                logger.info(msg)
                raise ValueError('gfalternate_getalternatevaratmaxr: data_tower and data_alternate lengths differ')
            # put the correlation into the r array
            rval = numpy.ma.corrcoef(data_tower,data_alternate)[0,1]
            if rval=="nan": rval = float(0)
        else:
            if mode!="quiet":
                msg = " getalternatevaratmaxr: not enough good data in alternate "+var
                logger.error(msg)
            rval = float(0)
        r[idx] = rval
    # save the correlation array for later plotting
    alternate_info["r"] = r
    # sort the correlation array and the alternate variable list
    idx = numpy.flipud(numpy.argsort(r))
    altvar_list_sorted = [altvar_list[j] for j in list(idx)]
    # return the name of the alternate variable that has the highest correlation with the tower data
    if ds_tower.alternate[label_output]["source"].lower()=="access": altvar_list_sorted = altvar_list_sorted[0:1]
    return altvar_list_sorted

def gfalternate_getalternatevarlist(ds_alternate,label):
    """
    Purpose:
     Get a list of alternate variable names from the alternate data structure.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    alternate_var_list = [item for item in ds_alternate.series.keys() if label in item]
    # remove any extraneous Fn labels (alternate has Fn_lw and Fn_sw)
    if label=="Fn":
        alternate_var_list = [item for item in alternate_var_list if "lw" not in item]
        alternate_var_list = [item for item in alternate_var_list if "sw" not in item]
    # check the series in the alternate data
    if len(alternate_var_list)==0:
        logger.error("gfalternate_getalternatevarlist: series "+label+" not in alternate data file")
    return alternate_var_list

def gfalternate_getdataas2d(odt,data,alternate_info):
    """
    Purpose:
     Return data, a 1D array, as a 2D array with hours along axis=0 and days along
     axis=1
    Usage:
    Side effects:
     The 1D array, data, is truncated at the start and end to make whole days.
    Author: PRI
    Date: August 2014
    """
    ts = alternate_info["time_step"]
    nperday = alternate_info["nperday"]
    si = 0
    while abs(odt[si].hour+float(odt[si].minute)/60-float(ts)/60)>c.eps:
        si = si + 1
    ei = len(odt)-1
    while abs(odt[ei].hour+float(odt[ei].minute)/60)>c.eps:
        ei = ei - 1
    data_wholedays = data[si:ei+1]
    ndays = len(data_wholedays)/nperday
    return numpy.ma.reshape(data_wholedays,[ndays,nperday])

def gfalternate_getdateindices(ldt_tower,ldt_alternate,alternate_info,match):
    if match=="exact":
        si_match = "exact"
        ei_match = "exact"
    elif match=="wholedays":
        si_match = "startnextday"
        ei_match = "endpreviousday"
    else:
        msg = "gfalternate_getdateindices: unrecognised match option ("+match+")"
        logger.error(msg)
    startdate = alternate_info["startdate"]
    enddate = alternate_info["enddate"]
    ts = alternate_info["time_step"]
    # get the indices of the start and end datetimes in the tower and the alternate data.
    si_tower = pfp_utils.GetDateIndex(ldt_tower,startdate,ts=ts,match=si_match,default=0)
    ei_tower = pfp_utils.GetDateIndex(ldt_tower,enddate,ts=ts,match=ei_match,default=len(ldt_tower)-1)
    si_alternate = pfp_utils.GetDateIndex(ldt_alternate,startdate,ts=ts,match=si_match,default=0)
    ei_alternate = pfp_utils.GetDateIndex(ldt_alternate,enddate,ts=ts,match=ei_match,default=len(ldt_alternate)-1)
    alternate_info["tower"]["si"] = si_tower
    alternate_info["tower"]["ei"] = ei_tower
    alternate_info["alternate"]["si"] = si_alternate
    alternate_info["alternate"]["ei"] = ei_alternate

def gfalternate_getdielaverage(data_dict,alternate_info):
    odt = data_dict["DateTime"]["data"]
    label_tower = alternate_info["label_tower"]
    output_list = list(data_dict[label_tower]["output_list"])
    diel_avg = {}
    for label_output in output_list:
        diel_avg[label_output] = {}
        if "data" in data_dict[label_output].keys():
            data_2d = gfalternate_getdataas2d(odt,data_dict[label_output]["data"],alternate_info)
            diel_avg[label_output]["data"] = numpy.ma.average(data_2d,axis=0)
        if "fitcorr" in data_dict[label_output].keys():
            data_2d = gfalternate_getdataas2d(odt,data_dict[label_output]["fitcorr"],alternate_info)
            diel_avg[label_output]["fitcorr"] = numpy.ma.average(data_2d,axis=0)
    return diel_avg

def gfalternate_getfitcorrecteddata(data_dict,stat_dict,alternate_info):
    """
    Wrapper for the various methods of fitting the alternate data to the tower data.
    """
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    if alternate_info["fit_type"].lower()=="ols":
        gfalternate_getolscorrecteddata(data_dict,stat_dict,alternate_info)
    if alternate_info["fit_type"].lower()=="ols_thru0":
        gfalternate_getolscorrecteddata(data_dict,stat_dict,alternate_info)
    if alternate_info["fit_type"].lower()=="mrev":
        gfalternate_getmrevcorrected(data_dict,stat_dict,alternate_info)
    if alternate_info["fit_type"].lower()=="replace":
        gfalternate_getreplacedata(data_dict,stat_dict,alternate_info)
    if alternate_info["fit_type"].lower()=="rma":
        gfalternate_getrmacorrecteddata(data_dict,stat_dict,alternate_info)
    if alternate_info["fit_type"].lower()=="odr":
        gfalternate_getodrcorrecteddata(data_dict,stat_dict,alternate_info)

def gfalternate_getlabeloutputlist(ds_tower,label_tower):
    olist = [item for item in ds_tower.alternate.keys() if ds_tower.alternate[item]["label_tower"]==label_tower]
    for item in ds_tower.merge.keys():
        if label_tower in ds_tower.merge[item].keys():
            mlist = ds_tower.merge[item][label_tower]["source"]
    label_output_list = []
    for item in mlist:
        if item in olist: label_output_list.append(item)
    return label_output_list

def gfalternate_getcorrecteddata(ds_alternate,data_dict,stat_dict,alternate_info,mode="quiet"):
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    if alternate_info["nogaps_tower"]:
        # tower data has no gaps
        stat_dict[label_output][label_alternate]["nLags"] = int(0)
        data_dict[label_output][label_alternate]["lagcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        stat_dict[label_output][label_alternate]["slope"] = float(0)
        stat_dict[label_output][label_alternate]["offset"] = float(0)
        stat_dict[label_output][label_alternate]["eqnstr"] = "No gaps in tower"
    elif not alternate_info["nogaps_tower"] and alternate_info["gotminpoints_both"]:
        # got enough good points common to both data series
        gfalternate_getlagcorrecteddata(ds_alternate, data_dict,stat_dict,alternate_info)
        gfalternate_getfitcorrecteddata(data_dict, stat_dict, alternate_info)
    elif not alternate_info["nogaps_tower"] and not alternate_info["gotminpoints_both"]:
        stat_dict[label_output][label_alternate]["nLags"] = int(0)
        data_dict[label_output][label_alternate]["lagcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        if alternate_info["fit_type"].lower()=="replace":
            gfalternate_getfitcorrecteddata(data_dict, stat_dict, alternate_info)
        else:
            #data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.masked_all_like(data_dict[label_output][label_alternate]["data"])
            data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
            stat_dict[label_output][label_alternate]["slope"] = float(0)
            stat_dict[label_output][label_alternate]["offset"] = float(0)
            stat_dict[label_output][label_alternate]["eqnstr"] = "Too few points"
    else:
        msg = "getcorrecteddata: Unrecognised combination of logical tests"
        logger.error(msg)

def gfalternate_getlagcorrecteddata(ds_alternate, data_dict,stat_dict,alternate_info):
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    data_tower = data_dict[label_tower]["data"]
    data_alternate = data_dict[label_output][label_alternate]["data"]
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    startdate = alternate_info["startdate"]
    enddate = alternate_info["enddate"]
    ts = alternate_info["time_step"]
    si_alternate = pfp_utils.GetDateIndex(ldt_alternate,startdate,ts=ts)
    ei_alternate = pfp_utils.GetDateIndex(ldt_alternate,enddate,ts=ts)
    if alternate_info["lag"].lower()=="yes":
        maxlags = alternate_info["max_lags"]
        minpoints = alternate_info["min_points"]
        lags,corr = pfp_ts.get_laggedcorrelation(data_tower,data_alternate,maxlags)
        nLags = numpy.argmax(corr) - alternate_info["max_lags"]
        if nLags>alternate_info["nperhr"]*6:
            logger.error("getlagcorrecteddata: lag is more than 6 hours for "+label_tower)
        si_alternate = si_alternate - nLags
        ei_alternate = ei_alternate - nLags
        data_alternate,flag_alternate,attr_alternate = pfp_utils.GetSeriesasMA(ds_alternate,label_alternate,si=si_alternate,ei=ei_alternate,mode="mirror")
        data_dict[label_output][label_alternate]["lagcorr"] = data_alternate
        stat_dict[label_output][label_alternate]["nLags"] = nLags
    else:
        data_dict[label_output][label_alternate]["lagcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        stat_dict[label_output][label_alternate]["nLags"] = int(0)

def gfalternate_getmrevcorrected(data_dict,stat_dict,alternate_info):
    """
    Fit alternate data to tower data by replacing means and equalising variance.
    """
    odt = data_dict["DateTime"]["data"]
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    # local copies of the data
    data_tower = numpy.ma.copy(data_dict[label_tower]["data"])
    data_alternate = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])

    data_2d = gfalternate_getdataas2d(odt,data_tower,alternate_info)
    data_twr_hravg = numpy.ma.average(data_2d,axis=0)
    data_2d = gfalternate_getdataas2d(odt,data_alternate,alternate_info)
    data_alt_hravg = numpy.ma.average(data_2d,axis=0)

    #data_twr_hravg = numpy.ma.copy(data_plot["tower"]["hourlyavg"])
    #data_alt_hravg = numpy.ma.copy(data_plot["alternate"][label_alternate]["lagcorr"]["hourlyavg"])

    # calculate the means
    mean_tower = numpy.ma.mean(data_tower)
    mean_alternate = numpy.ma.mean(data_alternate)
    # calculate the variances
    var_twr_hravg = numpy.ma.var(data_twr_hravg)
    var_alt_hravg = numpy.ma.var(data_alt_hravg)
    var_ratio = var_twr_hravg/var_alt_hravg
    # correct the alternate data
    data_dict[label_output][label_alternate]["fitcorr"] = ((data_alternate - mean_alternate)*var_ratio) + mean_tower
    stat_dict[label_output][label_alternate]["eqnstr"] = "Mean replaced, equal variance"
    stat_dict[label_output][label_alternate]["slope"] = float(0)
    stat_dict[label_output][label_alternate]["offset"] = float(0)

def gfalternate_getnumgoodpoints(data_tower,data_alternate):
    mask = numpy.ma.mask_or(data_tower.mask,data_alternate.mask,copy=True,shrink=False)
    return len(numpy.where(mask==False)[0])

def gfalternate_getodrcorrecteddata(data_dict,stat_dict,alternate_info):
    """
    Calculate the orthogonal distance regression fit between 2 1D arrays.
    """
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    y_in = numpy.ma.copy(data_dict[label_tower]["data"])
    x_in = numpy.ma.copy(data_dict[label_output][label_alternate]["lagcorr"])
    mask = numpy.ma.mask_or(x_in.mask,y_in.mask,copy=True,shrink=False)
    x = numpy.ma.compressed(numpy.ma.array(x_in,mask=mask,copy=True))
    y = numpy.ma.compressed(numpy.ma.array(y_in,mask=mask,copy=True))
    # attempt an ODR fit
    linear = scipy.odr.Model(pfp_utils.linear_function)
    mydata = scipy.odr.Data(x,y)
    myodr = scipy.odr.ODR(mydata,linear,beta0=[1,0])
    myoutput = myodr.run()
    odr_slope = myoutput.beta[0]
    odr_offset = myoutput.beta[1]
    data_dict[label_output][label_alternate]["fitcorr"] = odr_slope*x_in+odr_offset
    stat_dict[label_output][label_alternate]["slope"] = odr_slope
    stat_dict[label_output][label_alternate]["offset"] = odr_offset
    stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx + %.3f"%(odr_slope,odr_offset)

    #resols = sm.OLS(y,sm.add_constant(x,prepend=False)).fit()
    #if resols.params.shape[0]==2:
        #rma_slope = resols.params[0]/numpy.sqrt(resols.rsquared)
        #rma_offset = numpy.mean(y) - rma_slope * numpy.mean(x)
        #data_dict[label_output][label_alternate]["fitcorr"] = rma_slope*x_in+rma_offset
        #stat_dict[label_output][label_alternate]["slope"] = rma_slope
        #stat_dict[label_output][label_alternate]["offset"] = rma_offset
        #stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx + %.3f"%(rma_slope,rma_offset)
    #else:
        #data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(x_in)
        #stat_dict[label_output][label_alternate]["slope"] = float(0)
        #stat_dict[label_output][label_alternate]["offset"] = float(0)
        #stat_dict[label_output][label_alternate]["eqnstr"] = "RMA error, replaced"

def gfalternate_getolscorrecteddata(data_dict,stat_dict,alternate_info):
    """
    Calculate the ordinary least squares fit between 2 1D arrays.
    """
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    y_in = numpy.ma.copy(data_dict[label_tower]["data"])
    x_in = numpy.ma.copy(data_dict[label_output][label_alternate]["lagcorr"])
    mask = numpy.ma.mask_or(x_in.mask,y_in.mask,copy=True,shrink=False)
    x = numpy.ma.compressed(numpy.ma.array(x_in,mask=mask,copy=True))
    y = numpy.ma.compressed(numpy.ma.array(y_in,mask=mask,copy=True))
    # attempt an OLS fit
    if alternate_info["fit_type"].lower()=="ols_thru0":
        resols = sm.OLS(y,x).fit()
        data_dict[label_output][label_alternate]["fitcorr"] = resols.params[0]*x_in
        stat_dict[label_output][label_alternate]["slope"] = resols.params[0]
        stat_dict[label_output][label_alternate]["offset"] = float(0)
        stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx"%(resols.params[0])
    else:
        resols = sm.OLS(y,sm.add_constant(x,prepend=False)).fit()
        if resols.params.shape[0]==2:
            data_dict[label_output][label_alternate]["fitcorr"] = resols.params[0]*x_in+resols.params[1]
            stat_dict[label_output][label_alternate]["slope"] = resols.params[0]
            stat_dict[label_output][label_alternate]["offset"] = resols.params[1]
            stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx + %.3f"%(resols.params[0],resols.params[1])
        else:
            data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(x_in)
            stat_dict[label_output][label_alternate]["slope"] = float(0)
            stat_dict[label_output][label_alternate]["offset"] = float(0)
            stat_dict[label_output][label_alternate]["eqnstr"] = "OLS error, replaced"

def gfalternate_getoutputstatistics(data_dict,stat_dict,alternate_info):
    label_tower = alternate_info["label_tower"]
    label_composite = alternate_info["label_composite"]
    output_list = list(data_dict[label_tower]["output_list"])
    if label_tower in output_list: output_list.remove(label_tower)
    for label in output_list:
        # OLS slope and offset
        if alternate_info["fit_type"]!="replace":
            x_in = numpy.ma.copy(data_dict[label]["fitcorr"])
            y_in = numpy.ma.copy(data_dict[label_tower]["data"])
            mask = numpy.ma.mask_or(x_in.mask,y_in.mask,copy=True,shrink=False)
            x = numpy.ma.compressed(numpy.ma.array(x_in,mask=mask,copy=True))
            y = numpy.ma.compressed(numpy.ma.array(y_in,mask=mask,copy=True))
            # get the array lengths
            nx = len(x); ny = len(y)
            # attempt an OLS fit
            if nx>=alternate_info["min_points"]:
                if alternate_info["fit_type"].lower()=="ols":
                    resols = sm.OLS(y,sm.add_constant(x,prepend=False)).fit()
                    if resols.params.shape[0]==2:
                        stat_dict[label]["slope"] = resols.params[0]
                        stat_dict[label]["offset"] = resols.params[1]
                        stat_dict[label]["eqnstr"] = "y = %.3fx + %.3f"%(resols.params[0],resols.params[1])
                    else:
                        stat_dict[label]["slope"] = float(0)
                        stat_dict[label]["offset"] = float(0)
                        stat_dict[label]["eqnstr"] = "OLS error"
                else:
                    resols = sm.OLS(y,x).fit()
                    stat_dict[label]["slope"] = resols.params[0]
                    stat_dict[label]["offset"] = float(0)
                    stat_dict[label]["eqnstr"] = "y = %.3fx"%(resols.params[0])
            else:
                stat_dict[label]["slope"] = float(0)
                stat_dict[label]["offset"] = float(0)
                stat_dict[label]["eqnstr"] = "Too few points"
        else:
            stat_dict[label]["slope"] = float(1)
            stat_dict[label]["offset"] = float(0)
            stat_dict[label]["eqnstr"] = "Data replaced"
        # number of points
        stat_dict[label]["No. points"] = len(data_dict[label_tower]["data"])
        num = numpy.ma.count(data_dict[label]["fitcorr"])-numpy.ma.count(data_dict[label_tower]["data"])
        if num<0: num = 0
        stat_dict[label]["No. filled"] = num
        # correlation coefficient
        r = numpy.ma.corrcoef(data_dict[label_tower]["data"],data_dict[label]["fitcorr"])
        stat_dict[label]["r"] = r[0,1]
        # means
        avg = numpy.ma.mean(data_dict[label_tower]["data"])
        stat_dict[label]["Avg (Tower)"] = avg
        avg = numpy.ma.mean(data_dict[label]["fitcorr"])
        stat_dict[label]["Avg (Alt)"] = avg
        # variances
        var_tower = numpy.ma.var(data_dict[label_tower]["data"])
        stat_dict[label]["Var (Tower)"] = var_tower
        var_alt = numpy.ma.var(data_dict[label]["fitcorr"])
        stat_dict[label]["Var (Alt)"] = var_alt
        if var_alt!=0:
            stat_dict[label]["Var ratio"] = var_tower/var_alt
        else:
            stat_dict[label]["Var ratio"] = float(c.missing_value)
        # RMSE & NMSE
        error = (data_dict[label_tower]["data"]-data_dict[label]["fitcorr"])
        rmse = numpy.ma.sqrt(numpy.ma.average(error*error))
        stat_dict[label]["RMSE"] = rmse
        data_range = numpy.ma.maximum(data_dict[label_tower]["data"])-numpy.ma.minimum(data_dict[label_tower]["data"])
        nmse = rmse/data_range
        stat_dict[label]["NMSE"] = nmse
        # bias & fractional bias
        stat_dict[label]["Bias"] = numpy.ma.average(error)
        norm_error = (error)/(0.5*(data_dict[label_tower]["data"]+data_dict[label]["fitcorr"]))
        stat_dict[label]["Frac Bias"] = numpy.ma.average(norm_error)

def gfalternate_getreplacedata(data_dict,stat_dict,alternate_info):
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    data_alternate = data_dict[label_output][label_alternate]["lagcorr"]
    data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(data_alternate)
    stat_dict[label_output][label_alternate]["slope"] = float(1)
    stat_dict[label_output][label_alternate]["offset"] = float(0)
    stat_dict[label_output][label_alternate]["eqnstr"] = "No OLS, replaced"

def gfalternate_getrmacorrecteddata(data_dict,stat_dict,alternate_info):
    """
    Calculate the ordinary least squares fit between 2 1D arrays.
    """
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    y_in = numpy.ma.copy(data_dict[label_tower]["data"])
    x_in = numpy.ma.copy(data_dict[label_output][label_alternate]["lagcorr"])
    mask = numpy.ma.mask_or(x_in.mask,y_in.mask,copy=True,shrink=False)
    x = numpy.ma.compressed(numpy.ma.array(x_in,mask=mask,copy=True))
    y = numpy.ma.compressed(numpy.ma.array(y_in,mask=mask,copy=True))
    # attempt an OLS fit
    if alternate_info["fit_type"].lower()=="ols_thru0":
        resols = sm.OLS(y,x).fit()
        rma_slope = resols.params[0]/numpy.sqrt(resols.rsquared)
        rma_offset = numpy.mean(y) - rma_slope * numpy.mean(x)
        data_dict[label_output][label_alternate]["fitcorr"] = rma_slope*x_in
        stat_dict[label_output][label_alternate]["slope"] = rma_slope
        stat_dict[label_output][label_alternate]["offset"] = float(0)
        stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx"%(rma_slope)
    else:
        resols = sm.OLS(y,sm.add_constant(x,prepend=False)).fit()
        if resols.params.shape[0]==2:
            rma_slope = resols.params[0]/numpy.sqrt(resols.rsquared)
            rma_offset = numpy.mean(y) - rma_slope * numpy.mean(x)
            data_dict[label_output][label_alternate]["fitcorr"] = rma_slope*x_in+rma_offset
            stat_dict[label_output][label_alternate]["slope"] = rma_slope
            stat_dict[label_output][label_alternate]["offset"] = rma_offset
            stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx + %.3f"%(rma_slope,rma_offset)
        else:
            data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(x_in)
            stat_dict[label_output][label_alternate]["slope"] = float(0)
            stat_dict[label_output][label_alternate]["offset"] = float(0)
            stat_dict[label_output][label_alternate]["eqnstr"] = "RMA error, replaced"

def gfalternate_gotdataforgaps(data,data_alternate,alternate_info,mode="verbose"):
    """
    Returns true if the alternate series has data where the composite series has gaps.
    """
    return_code = True
    ind = numpy.where((numpy.ma.getmaskarray(data)==True)&(numpy.ma.getmaskarray(data_alternate)==False))[0]
    if len(ind)==0:
        if mode=="verbose":
            label_alternate = alternate_info["label_alternate"]
            msg = " Alternate series "+label_alternate+" has nothing to contribute"
            logger.info(msg)
        return_code = False
    return return_code

def gfalternate_gotnogaps(data,label,mode="verbose"):
    """
    Returns true if the data series has no gaps, false if there are gaps
    """
    return_code = True
    if numpy.ma.count_masked(data)==0:
        if mode=="verbose":
            msg = " No gaps in "+label
            logger.info(msg)
        return_code = True
    else:
        return_code = False
    return return_code

def gfalternate_gotminpoints(data,alternate_info,label,mode="verbose"):
    """
    Returns true if data contains more than the minimum number of points required
    or data contains less than the minimum number but the fit type is replace.
    """
    return_code = True
    if numpy.ma.count(data)<alternate_info["min_points"]:
        if mode=="verbose":
            msg = " Less than "+str(alternate_info["min_percent"])+" % data in series "+label+", skipping ..."
            logger.info(msg)
            msg = "gotminpoints: "+label+" "+str(numpy.ma.count(data))+" "+str(alternate_info["min_points"])
            logger.info(msg)
        return_code = False
    return return_code

def gfalternate_gotminpointsboth(data_tower,data_alternate,alternate_info,label_tower,label_alternate,mode="verbose"):
    return_code = True
    mask = numpy.ma.mask_or(numpy.ma.getmaskarray(data_tower),numpy.ma.getmaskarray(data_alternate),copy=True,shrink=False)
    if len(numpy.where(mask==False)[0])<alternate_info["min_points"]:
        if mode!="quiet":
            msg = " Less than "+str(alternate_info["min_percent"])+" % good data common to both series "
            logger.info(msg)
            msg = "gotminpointsboth: "+label_tower+" "+str(numpy.ma.count(data_tower))+" "+str(alternate_info["min_points"])
            logger.info(msg)
            msg = "gotminpointsboth: "+label_alternate+" "+str(numpy.ma.count(data_alternate))+" "+str(alternate_info["min_points"])
            logger.info(msg)
        return_code = False
    return return_code

def gfalternate_initplot(data_dict,alternate_info,**kwargs):
    pd = {"margin_bottom":0.075,"margin_top":0.05,"margin_left":0.075,"margin_right":0.05,
          "xy_height":0.25,"xy_width":0.20,"xyts_space":0.05,"xyxy_space":0.05,"ts_width":0.9,
          "text_left":0.675,"num_left":0.825,"row_bottom":0.35,"row_space":0.030}
    # calculate bottom of the first time series and the height of the time series plots
    #pd["ts_bottom"] = pd["margin_bottom"]+pd["xy_height"]+pd["xyxy_space"]+pd["xy_height"]+pd["xyts_space"]
    label_tower = alternate_info["label_tower"]
    label_composite = alternate_info["label_composite"]

    output_list = list(data_dict[label_tower]["output_list"])
    for item in [label_tower,label_composite]:
        if item in output_list: output_list.remove(item)
    nts = len(output_list)+1
    pd["ts_bottom"] = pd["margin_bottom"]+pd["xy_height"]+pd["xyts_space"]
    pd["ts_height"] = (1.0-pd["margin_top"]-pd["ts_bottom"])/nts
    for key, value in kwargs.iteritems():
        pd[key] = value
    return pd

def gfalternate_loadoutputdata(ds_tower,data_dict,alternate_info):
    ldt_tower = ds_tower.series["DateTime"]["Data"]
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_composite = alternate_info["label_composite"]
    label_alternate = alternate_info["label_alternate"]
    data_tower = data_dict[label_tower]["data"]
    ts = alternate_info["time_step"]
    #si = pfp_utils.GetDateIndex(ldt_tower,alternate_info["startdate"],ts=ts,default=0)
    #ei = pfp_utils.GetDateIndex(ldt_tower,alternate_info["enddate"],ts=ts,default=len(ldt_tower))
    si = alternate_info["si_tower"]
    ei = alternate_info["ei_tower"]
    if alternate_info["overwrite"]:
        ind1 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"])==False)[0]
    else:
        ind1 = numpy.where((numpy.ma.getmaskarray(data_dict[label_output]["data"])==True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"])==False))[0]
    data_dict[label_output]["data"][ind1] = data_dict[label_output][label_alternate]["data"][ind1]
    if alternate_info["overwrite"]:
        ind2 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False)[0]
    else:
        ind2 = numpy.where((numpy.ma.getmaskarray(data_dict[label_output]["fitcorr"])==True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False))[0]
    data_dict[label_output]["fitcorr"][ind2] = data_dict[label_output][label_alternate]["fitcorr"][ind2]
    if alternate_info["overwrite"]:
        ind3 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"])==False)[0]
    else:
        ind3 = numpy.where((numpy.ma.getmaskarray(data_dict[label_composite]["data"])==True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"])==False))[0]
    data_dict[label_composite]["data"][ind3] = data_dict[label_output][label_alternate]["data"][ind3]
    if alternate_info["overwrite"]:
        ind4 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False)[0]
    else:
        ind4 = numpy.where((numpy.ma.getmaskarray(data_dict[label_composite]["fitcorr"])==True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False))[0]
    data_dict[label_composite]["fitcorr"][ind4] = data_dict[label_output][label_alternate]["fitcorr"][ind4]
    if alternate_info["overwrite"]:
        ind5 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False)[0]
    else:
        ind5 = numpy.where((abs(ds_tower.series[label_composite]["Data"][si:ei+1]-float(c.missing_value))<c.eps)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False))[0]
    ds_tower.series[label_composite]["Data"][si:ei+1][ind5] = numpy.ma.filled(data_dict[label_output][label_alternate]["fitcorr"][ind5],c.missing_value)
    ds_tower.series[label_composite]["Flag"][si:ei+1][ind5] = numpy.int32(20)
    if alternate_info["overwrite"]:
        ind6 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False)[0]
    else:
        ind6 = numpy.where((abs(ds_tower.series[label_output]["Data"][si:ei+1]-float(c.missing_value))<c.eps)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"])==False))[0]
    ds_tower.series[label_output]["Data"][si:ei+1][ind6] = numpy.ma.filled(data_dict[label_output][label_alternate]["fitcorr"][ind6],c.missing_value)
    ds_tower.series[label_output]["Flag"][si:ei+1][ind6] = numpy.int32(20)

def gfalternate_matchstartendtimes(ds,ds_alternate):
    """
    Purpose:
     Match the start and end times of the alternate and tower data.
     The logic is as follows:
      - if there is no overlap between the alternate and tower data then
        dummy series with missing data are created for the alternate data
        for the period of the tower data
      - if the alternate and tower data overlap then truncate or pad (with
        missing values) the alternate data series so that the periods of the
        tower data and alternate data match.
    Usage:
     gfalternate_matchstartendtimes(ds,ds_alternate)
     where ds is the data structure containing the tower data
           ds_alternate is the data structure containing the alternate data
    Author: PRI
    Date: July 2015
    """
    # check the time steps are the same
    ts_tower = int(ds.globalattributes["time_step"])
    ts_alternate = int(ds_alternate.globalattributes["time_step"])
    if ts_tower!=ts_alternate:
        msg = " GapFillFromAlternate: time step for tower and alternate data are different, returning ..."
        logger.error(msg)
        ds.returncodes["GapFillFromAlternate"] = "error"
        return
    ts = ts_tower
    # get the start and end times of the tower and the alternate data and see if they overlap
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    start_alternate = ldt_alternate[0]
    end_alternate = ldt_alternate[-1]
    ldt_tower = ds.series["DateTime"]["Data"]
    start_tower = ldt_tower[0]
    end_tower = ldt_tower[-1]
    # since the datetime is monotonically increasing we need only check the start datetime
    overlap = start_alternate<=end_tower
    # do the alternate and tower data overlap?
    if overlap:
        # index of alternate datetimes that are also in tower datetimes
        alternate_index = pfp_utils.FindIndicesOfBInA(ldt_tower,ldt_alternate)
        # index of tower datetimes that are also in alternate datetimes
        tower_index = pfp_utils.FindIndicesOfBInA(ldt_alternate,ldt_tower)
        # check that the indices point to the same times
        ldta = [ldt_alternate[i] for i in alternate_index]
        ldtt = [ldt_tower[i] for i in tower_index]
        if ldta!=ldtt:
            # and exit with a helpful message if they dont
            logger.error(" Something went badly wrong and I'm giving up")
            sys.exit()
        # get a list of alternate series
        alternate_series_list = [item for item in ds_alternate.series.keys() if "_QCFlag" not in item]
        # number of records in truncated or padded alternate data
        nRecs_tower = len(ldt_tower)
        # force the alternate dattime to be the tower date time
        ds_alternate.series["DateTime"] = ds.series["DateTime"]
        # loop over the alternate series and truncate or pad as required
        # truncation or padding is handled by the indices
        for series in alternate_series_list:
            if series in ["DateTime","DateTime_UTC"]: continue
            # get the alternate data
            data,flag,attr = pfp_utils.GetSeriesasMA(ds_alternate,series)
            # create an array of missing data of the required length
            data_overlap = numpy.full(nRecs_tower,c.missing_value,dtype=numpy.float64)
            flag_overlap = numpy.ones(nRecs_tower,dtype=numpy.int32)
            # replace missing data with alternate data where times match
            data_overlap[tower_index] = data[alternate_index]
            flag_overlap[tower_index] = flag[alternate_index]
            # write the truncated or padded series back into the alternate data structure
            pfp_utils.CreateSeries(ds_alternate,series,data_overlap,flag_overlap,attr)
        # update the number of records in the file
        ds_alternate.globalattributes["nc_nrecs"] = nRecs_tower
    else:
        # there is no overlap between the alternate and tower data, create dummy series
        nRecs = len(ldt_tower)
        ds_alternate.globalattributes["nc_nrecs"] = nRecs
        ds_alternate.series["DateTime"] = ds.series["DateTime"]
        alternate_series_list = [item for item in ds_alternate.series.keys() if "_QCFlag" not in item]
        for series in alternate_series_list:
            if series in ["DateTime","DateTime_UTC"]: continue
            d,f,attr = pfp_utils.GetSeriesasMA(ds_alternate,series)
            data = numpy.full(nRecs,c.missing_value,dtype=numpy.float64)
            flag = numpy.ones(nRecs,dtype=numpy.int32)
            pfp_utils.CreateSeries(ds_alternate,series,data,flag,attr)
    ds.returncodes["GapFillFromAlternate"] = "normal"

def gfalternate_main(ds_tower,ds_alt,alternate_info,label_tower_list=[]):
    '''
    This is the main routine for using alternate data to gap fill drivers.
    '''
    mode = "quiet" #"quiet"  #"verbose"
    ts = alternate_info["time_step"]
    startdate = alternate_info["startdate"]
    enddate = alternate_info["enddate"]
    logger.info(" Gap fill with alternate: "+startdate+" to "+enddate)
    # close any open plot windows
    if len(plt.get_fignums())!=0:
        for i in plt.get_fignums():
            if i!=0: plt.close(i)
        QtGui.QApplication.processEvents()
    # read the control file again
    cfname = ds_tower.globalattributes["controlfile_name"]
    cf = pfp_io.get_controlfilecontents(cfname, mode="quiet")
    alternate_info["plot_path"] = cf["Files"]["plot_path"]
    # do any QC checks
    pfp_ck.do_qcchecks(cf,ds_tower,mode="quiet")
    # update the ds.alternate dictionary
    gfalternate_updatedict(cf,ds_tower,ds_alt)
    # get local pointer to the datetime series
    dt_tower = ds_tower.series["DateTime"]["Data"]
    attr_ldt_tower = ds_tower.series["DateTime"]["Attr"]
    si_tower = pfp_utils.GetDateIndex(dt_tower,alternate_info["startdate"],ts=ts,default=0)
    alternate_info["si_tower"] = si_tower
    ei_tower = pfp_utils.GetDateIndex(dt_tower,alternate_info["enddate"],ts=ts,default=len(dt_tower)-1)
    alternate_info["ei_tower"] = ei_tower
    ldt_tower = dt_tower[si_tower:ei_tower+1]
    # now loop over the variables to be gap filled using the alternate data
    if len(label_tower_list)==0:
        label_tower_list = list(set(alternate_info["series_list"]))
    for fig_num,label_tower in enumerate(label_tower_list):
        ok = True
        alternate_info["label_tower"] = label_tower
        label_composite = label_tower+"_composite"
        alternate_info["label_composite"] = label_composite
        # read the tower data and check for gaps
        data_tower,flag_tower,attr_tower = pfp_utils.GetSeriesasMA(ds_tower,label_tower,si=si_tower,ei=ei_tower)
        alternate_info["min_points"] = int(len(data_tower)*alternate_info["min_percent"]/100)
        # check to see if we have any gaps to fill
        alternate_info["nogaps_tower"] = gfalternate_gotnogaps(data_tower,label_tower,mode=mode)
        # check to see if we have more than the minimum number of points
        alternate_info["gotminpoints_tower"] = gfalternate_gotminpoints(data_tower,alternate_info,label_tower,mode=mode)
        # initialise a dictionary to hold the data
        data_dict,stat_dict = gfalternate_createdataandstatsdict(ldt_tower,data_tower,attr_tower,alternate_info)
        # get a list of the output names for this tower series
        label_output_list = gfalternate_getlabeloutputlist(ds_tower,label_tower)
        # loop over the outputs for this tower series
        for label_output in label_output_list:
            alternate_info["label_output"] = label_output
            alternate_info["alternate_name"] = ds_tower.alternate[label_output]["alternate_name"]
            # update the alternate_info dictionary
            gfalternate_update_alternate_info(ds_tower,alternate_info)
            # update the dictionaries
            stat_dict[label_output] = {"startdate":alternate_info["startdate"],"enddate":alternate_info["enddate"]}
            data_dict[label_output] = {"data":numpy.ma.masked_all_like(data_tower),
                                       "fitcorr":numpy.ma.masked_all_like(data_tower),
                                       "attr":attr_tower,"source":ds_tower.alternate[label_output]["source"]}
            # get a local pointer to the alternate data structure
            ds_alternate = ds_alt[ds_tower.alternate[label_output]["file_name"]]
            ldt_alternate = ds_alternate.series["DateTime"]["Data"]
            # start and end idices for this time range in the alternate data
            si_alternate = pfp_utils.GetDateIndex(ldt_alternate,alternate_info["startdate"],ts=ts,default=0)
            alternate_info["si_alternate"] = si_alternate
            ei_alternate = pfp_utils.GetDateIndex(ldt_alternate,alternate_info["enddate"],ts=ts,default=len(ldt_alternate)-1)
            alternate_info["ei_alternate"] = ei_alternate
            # get the alternate series that has the highest correlation with the tower data
            label_alternate_list = gfalternate_getalternatevaratmaxr(ds_tower,ds_alternate,alternate_info,mode=mode)
            # loop over alternate variables
            for label_alternate in label_alternate_list:
                alternate_info["label_alternate"] = label_alternate
                # get the raw alternate data
                data_alternate,flag_alternate,attr_alternate = pfp_utils.GetSeriesasMA(ds_alternate,label_alternate,si=si_alternate,ei=ei_alternate)
                # check this alternate variable to see if there are enough points
                alternate_info["gotminpoints_alternate"] = gfalternate_gotminpoints(data_alternate,alternate_info,label_alternate,mode=mode)
                alternate_info["gotdataforgaps_alternate"] = gfalternate_gotdataforgaps(data_dict[label_output]["data"],data_alternate,alternate_info,mode=mode)
                alternate_info["gotminpoints_both"] = gfalternate_gotminpointsboth(data_tower,data_alternate,alternate_info,label_tower,label_alternate,mode=mode)
                # update the data and sata dictionaries
                stat_dict[label_output][label_alternate] = {"startdate":alternate_info["startdate"],"enddate":alternate_info["enddate"]}
                if label_output not in data_dict[label_tower]["output_list"]:
                    data_dict[label_tower]["output_list"].append(label_output)
#                    if alternate_info["gotminpoints_both"]: data_dict[label_tower]["output_list"].append(label_output)
                data_dict[label_output][label_alternate] = {"data":data_alternate,"attr":attr_alternate}
                gfalternate_getcorrecteddata(ds_alternate,data_dict,stat_dict,alternate_info,mode=mode)
                gfalternate_loadoutputdata(ds_tower,data_dict,alternate_info)
                # check to see if we have alternate data for this whole period, if so there is no reason to continue
                #ind_tower = numpy.where(abs(ds_tower.series[label_output]["Data"][si_tower:ei_tower+1]-float(c.missing_value))<c.eps)[0]
                #if len(ind_tower)==0: break
        # we have completed the loop over the alternate data for this output
        # now do the statistics, diurnal average and daily averages for this output
        #logger.info(" Calling gfalternate_getoutputstatistics ...")
        gfalternate_getoutputstatistics(data_dict,stat_dict,alternate_info)
        for label_output in label_output_list:
            for result in ds_tower.alternate[label_output]["results"]:
                ds_tower.alternate[label_output]["results"][result].append(stat_dict[label_output][result])
        if alternate_info["nogaps_tower"]:
            if alternate_info["show_all"]:
                pass
            else:
                continue
        # plot the gap filled data
        #logger.info(" Gap fill with alternate: Plotting ...")
        #logger.info(" Calling gfalternate_getdielaverage ...")
        pd = gfalternate_initplot(data_dict,alternate_info)
        diel_avg = gfalternate_getdielaverage(data_dict,alternate_info)
        # reserve figure number 0 for the coverage lines/progress plot
        #logger.info(" Calling gfalternate_plotcomposite ...")
        fig_num = fig_num+1
        gfalternate_plotcomposite(fig_num,data_dict,stat_dict,diel_avg,alternate_info,pd)
        # reset the logicals in alternate_info
        #logger.info(" Gap fill with alternate: Finished plotting")
    # make sure this processing step gets written to the global attribute "Functions"
    if "GapFillFromalternate" not in ds_tower.globalattributes["Functions"]:
        ds_tower.globalattributes["Functions"] = ds_tower.globalattributes["Functions"]+", GapFillFromalternate"

def gfalternate_plotcomposite(nfig,data_dict,stat_dict,diel_avg,alternate_info,pd):
    # set up some local pointers
    label_tower = alternate_info["label_tower"]
    label_composite = alternate_info["label_composite"]
    time_step = alternate_info["time_step"]
    points_test = numpy.ma.count(data_dict[label_tower]["data"])<alternate_info["min_points"]
    fit_test = alternate_info["fit_type"]!="replace"
    if points_test and fit_test: return
    # turn on interactive plotting
    #if alternate_info["show_plots"]:
        ##plt.ion()
        #plt.ioff()
    #else:
        #plt.ioff()
    # create the figure canvas
    #fig = plt.figure(nfig,figsize=(13,8))
    if plt.fignum_exists(1):
        fig=plt.figure(1)
        plt.clf()
    else:
        fig = plt.figure(1,figsize=(13,8))
    fig.canvas.set_window_title(label_tower)
    # get the plot title string
    title = alternate_info["site_name"]+" : Comparison of tower and alternate data for "+label_tower
    plt.figtext(0.5,0.96,title,ha='center',size=16)
    # bottom row of XY plots: scatter plot of 30 minute data
    rect1 = [0.10,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    xyscatter = plt.axes(rect1)
    xyscatter.set_ylabel("Tower ("+data_dict[label_tower]["attr"]["units"]+")")
    xyscatter.set_xlabel("Alt ("+data_dict[label_composite]["attr"]["units"]+")")
    text = str(time_step)+" minutes"
    xyscatter.text(0.6,0.075,text,fontsize=10,horizontalalignment="left",transform=xyscatter.transAxes)
    xyscatter.plot(data_dict[label_composite]["fitcorr"],data_dict[label_tower]["data"],'b.')
    xfit = numpy.array([numpy.ma.min(data_dict[label_composite]["fitcorr"]),
                        numpy.ma.max(data_dict[label_composite]["fitcorr"])])
    yfit = xfit*stat_dict[label_composite]["slope"]+stat_dict[label_composite]["offset"]
    xyscatter.plot(xfit,yfit,'g--',linewidth=3)
    xyscatter.text(0.5,0.9,stat_dict[label_composite]["eqnstr"],fontsize=8,horizontalalignment='center',transform=xyscatter.transAxes,color='green')
    # bottom row of XY plots: scatter plot of diurnal averages
    ind = numpy.arange(alternate_info["nperday"])/float(alternate_info["nperhr"])
    rect2 = [0.40,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    diel_axes = plt.axes(rect2)
    diel_axes.plot(ind,diel_avg[label_composite]["fitcorr"],'g-',label="Alt (fit)")
    diel_axes.plot(ind,diel_avg[label_composite]["data"],'b-',label="Alt")
    diel_axes.set_ylabel(label_tower+" ("+data_dict[label_tower]["attr"]["units"]+")")
    diel_axes.set_xlim(0,24)
    diel_axes.xaxis.set_ticks([0,6,12,18,24])
    diel_axes.set_xlabel('Hour')
    diel_axes.plot(ind,diel_avg[label_tower]["data"],'ro',label="Tower")
    diel_axes.legend(loc='upper right',frameon=False,prop={'size':8})
    # top row: time series
    ts_axes = []
    rect3 = [pd["margin_left"],pd["ts_bottom"],pd["ts_width"],pd["ts_height"]]
    ts_axes.append(plt.axes(rect3))
    ts_axes[0].plot(data_dict["DateTime"]["data"],data_dict[label_tower]["data"],'ro',label="Tower")
    ts_axes[0].plot(data_dict["DateTime"]["data"],data_dict[label_composite]["fitcorr"],'g-',label="Alt (fitted)")
    ts_axes[0].set_xlim(data_dict["DateTime"]["data"][0],data_dict["DateTime"]["data"][-1])
    ts_axes[0].legend(loc='upper right',frameon=False,prop={'size':10})
    ts_axes[0].set_ylabel(label_tower+" ("+data_dict[label_tower]["attr"]["units"]+")")
    output_list = list(data_dict[label_tower]["output_list"])
    for item in [label_tower,label_composite]:
        if item in output_list: output_list.remove(item)
    for n,label_output in enumerate(output_list):
        n = n + 1
        source = data_dict[label_output]["source"]
        this_bottom = pd["ts_bottom"] + n*pd["ts_height"]
        rect = [pd["margin_left"],this_bottom,pd["ts_width"],pd["ts_height"]]
        ts_axes.append(plt.axes(rect,sharex=ts_axes[0]))
        ts_axes[n].plot(data_dict["DateTime"]["data"],data_dict[label_output]["data"],'b-',label=source)
        plt.setp(ts_axes[n].get_xticklabels(),visible=False)
        ts_axes[n].legend(loc='upper right',frameon=False,prop={'size':10})
        ts_axes[n].set_ylabel(label_tower+" ("+data_dict[label_tower]["attr"]["units"]+")")
    # write the comparison statistics
    stats_list = ["Var (Alt)","Var (Tower)","RMSE","Bias","r","No. filled","No. points"]
    for n,item in enumerate(stats_list):
        row_posn = pd["margin_bottom"] + n*pd["row_space"]
        plt.figtext(pd["text_left"],row_posn,item)
        plt.figtext(pd["num_left"],row_posn,'%.4g'%(stat_dict[label_composite][item]))
    # save a hard copy of the plot
    sdt = data_dict["DateTime"]["data"][0].strftime("%Y%m%d")
    edt = data_dict["DateTime"]["data"][-1].strftime("%Y%m%d")
    plot_path = alternate_info["plot_path"]+"L4/"
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+alternate_info["site_name"].replace(" ","")+"_Alternate_"+label_tower
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    if alternate_info["show_plots"]:
        #plt.draw()
        plt.show(block=False)
        plt.pause(0.001)
        #plt.ioff()
    #else:
        #plt.ion()

def gfalternate_plotcoveragelines(ds_tower,alternate_info):
    ldt = ds_tower.series["DateTime"]["Data"]
    site_name = ds_tower.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    slist = [ds_tower.alternate[item]["label_tower"] for item in ds_tower.alternate.keys()]
    series_list = list(set(slist))
    ylabel_list = [""]+series_list+[""]
    ylabel_right_list = [""]
    color_list = ["blue","red","green","yellow","magenta","black","cyan","brown"]
    xsize = 15.0
    ysize = max([len(series_list)*0.2,1])
    if plt.fignum_exists(0):
        fig=plt.figure(0)
        for series,n in zip(series_list,range(1,len(series_list)+1)):
            if series+"_composite" in ds_tower.series.keys():
                data_composite,f,a = pfp_utils.GetSeriesasMA(ds_tower,series+"_composite")
                ind_composite = numpy.ma.ones(len(data_composite))*float(n)
                ind_composite = numpy.ma.masked_where(numpy.ma.getmaskarray(data_composite)==True,ind_composite)
                #plt.plot(ldt,ind_composite,color=color_list[numpy.mod(n,8)],linewidth=4)
                fig.mylines[series][0].set_ydata(ind_composite)
                fig.mylines[series][0].set_xdata(ldt)
        plt.draw()
        plt.pause(0.001)
    else:
        fig=plt.figure(0,figsize=(xsize,ysize))
        ax1 = plt.subplot(111)
        title = "Coverage: "+site_name+" "+start_date+" to "+end_date
        fig.canvas.set_window_title(title)
        plt.ylim([0,len(series_list)+1])
        plt.xlim([ldt[0],ldt[-1]])
        fig.mylines = {}
        for series,n in zip(series_list,range(1,len(series_list)+1)):
            data_series,f,a = pfp_utils.GetSeriesasMA(ds_tower,series)
            percent = 100*numpy.ma.count(data_series)/len(data_series)
            ylabel_right_list.append("{0:.0f}%".format(percent))
            ind_series = numpy.ma.ones(len(data_series))*float(n)
            ind_series = numpy.ma.masked_where(numpy.ma.getmaskarray(data_series)==True,ind_series)
            plt.plot(ldt,ind_series,color=color_list[numpy.mod(n,8)],linewidth=1)
            if series+"_composite" in ds_tower.series.keys():
                data_composite,f,a = pfp_utils.GetSeriesasMA(ds_tower,series+"_composite")
                ind_composite = numpy.ma.ones(len(data_composite))*float(n)
                ind_composite = numpy.ma.masked_where(numpy.ma.getmaskarray(data_composite)==True,ind_composite)
                fig.mylines[series] = plt.plot(ldt,ind_composite,color=color_list[numpy.mod(n,8)],linewidth=4)
        ylabel_posn = range(0,len(series_list)+2)
        pylab.yticks(ylabel_posn,ylabel_list)
        ylabel_right_list.append("")
        ax2 = ax1.twinx()
        pylab.yticks(ylabel_posn,ylabel_right_list)
        fig.tight_layout()
        plt.show(block=False)
        plt.pause(0.001)

def gfalternate_plotcoveragelines_original(ds_tower,alternate_info):
    ldt = ds_tower.series["DateTime"]["Data"]
    site_name = ds_tower.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    slist = [ds_tower.alternate[item]["label_tower"] for item in ds_tower.alternate.keys()]
    series_list = list(set(slist))
    ylabel_list = [""]+series_list+[""]
    ylabel_right_list = [""]
    color_list = ["blue","red","green","yellow","magenta","black","cyan","brown"]
    xsize = 15.0
    ysize = max([len(series_list)*0.2,1])
    #plt.ion()
    #plt.ioff()
    if plt.fignum_exists(0):
        fig=plt.figure(0)
        plt.clf()
        ax1 = plt.subplot(111)
    else:
        fig=plt.figure(0,figsize=(xsize,ysize))
        ax1 = plt.subplot(111)
    title = "Coverage: "+site_name+" "+start_date+" to "+end_date
    fig.canvas.set_window_title(title)
    plt.ylim([0,len(series_list)+1])
    plt.xlim([ldt[0],ldt[-1]])
    for series,n in zip(series_list,range(1,len(series_list)+1)):
        data_series,f,a = pfp_utils.GetSeriesasMA(ds_tower,series)
        percent = 100*numpy.ma.count(data_series)/len(data_series)
        ylabel_right_list.append("{0:.0f}%".format(percent))
        ind_series = numpy.ma.ones(len(data_series))*float(n)
        ind_series = numpy.ma.masked_where(numpy.ma.getmaskarray(data_series)==True,ind_series)
        plt.plot(ldt,ind_series,color=color_list[numpy.mod(n,8)],linewidth=1)
        if series+"_composite" in ds_tower.series.keys():
            data_composite,f,a = pfp_utils.GetSeriesasMA(ds_tower,series+"_composite")
            ind_composite = numpy.ma.ones(len(data_composite))*float(n)
            ind_composite = numpy.ma.masked_where(numpy.ma.getmaskarray(data_composite)==True,ind_composite)
            plt.plot(ldt,ind_composite,color=color_list[numpy.mod(n,8)],linewidth=4)
    ylabel_posn = range(0,len(series_list)+2)
    pylab.yticks(ylabel_posn,ylabel_list)
    ylabel_right_list.append("")
    ax2 = ax1.twinx()
    pylab.yticks(ylabel_posn,ylabel_right_list)
    fig.tight_layout()
    #fig.canvas.manager.window.attributes('-topmost', 1)
    #plt.draw()
    plt.show(block=False)
    plt.pause(0.001)
    #plt.ioff()

def gfalternate_plotsummary(ds,alternate_info):
    """ Plot single pages of summary results for groups of variables. """
    # get a list of variables for which alternate data is available
    output_list = ds.alternate.keys()
    series_list = [ds.alternate[item]["label_tower"] for item in ds.alternate.keys()]
    if len(ds.alternate[output_list[0]]["results"]["startdate"])==0:
        logger.info("gfalternate: no summary data to plot")
        return
    # get the Excel datemode, needed to convert the Excel datetime to Python datetimes
    datemode = int(ds.globalattributes['xl_datemode'])
    # site name for titles
    site_name = ds.globalattributes["site_name"]
    # datetimes are stored in ds.alternate as Excel datetimes, here we convert to Python datetimes
    # for ease of handling and plotting.
    # start datetimes of the periods compared first
    basedate = datetime.datetime(1899, 12, 30)
    dt_start = []
    for xldt in ds.alternate[output_list[0]]["results"]["startdate"]:
        dt_start.append(basedate+datetime.timedelta(days=xldt+1462*datemode))
    startdate = min(dt_start)
    # and then the end datetimes
    dt_end = []
    for xldt in ds.alternate[output_list[0]]["results"]["enddate"]:
        dt_end.append(basedate+datetime.timedelta(days=xldt+1462*datemode))
    enddate = max(dt_end)
    # get the major tick locator and label format
    MTLoc = mdt.AutoDateLocator(minticks=3,maxticks=5)
    MTFmt = mdt.DateFormatter('%b')
    # group lists of the resuts to be plotted
    result_list = ["r","Bias","RMSE","Var ratio","Lag (uncorrected)","Slope","Offset"]
    ylabel_list = ["r","Bias","RMSE","Var ratio","Lag","Slope","Offset"]
    # turn on interactive plotting
    plt.ion()
    # now loop over the group lists
    for nFig in ds.cf["Alternate_Summary"].keys():
        plot_title = ds.cf["Alternate_Summary"][str(nFig)]["Title"]
        var_list = ast.literal_eval(ds.cf["Alternate_Summary"][str(nFig)]["Variables"])
        # set up the subplots on the page
        fig,axs = plt.subplots(len(result_list),len(var_list),figsize=(13,8))
        fig.canvas.set_window_title("Alternate summary: "+plot_title)
        # make a title string for the plot and render it
        title_str = "Alternate: "+plot_title+"; "+site_name+" "+datetime.datetime.strftime(startdate,"%Y-%m-%d")
        title_str = title_str+" to "+datetime.datetime.strftime(enddate,"%Y-%m-%d")
        fig.suptitle(title_str, fontsize=14, fontweight='bold')
        # initialise a string to take the concatenated variable names, used in the name of the hard-copy of the plot
        figlab = ""
        # now loop over the variables in the group list
        for col,output in enumerate(var_list):
            if output not in output_list:
                logger.error("Series "+output+" requested for summary plot is not available")
                continue
            source = ds.alternate[output]["source"]
            # append the variable name to the variable name string
            figlab = figlab+output
            # and loop over rows in plot
            for row,rlabel,ylabel in zip(range(len(result_list)),result_list,ylabel_list):
                # if this is the first row, add the column title
                #if row==0: axs[row,col].set_title(output+" ("+source+")")
                if row==0: axs[row,col].set_title(output)
                # if this is the left-most column, add the Y axis labels
                if col==0: axs[row,col].set_ylabel(ylabel,visible=True)
                # get the results to be plotted
                result = numpy.ma.masked_equal(ds.alternate[output]["results"][rlabel],float(c.missing_value))
                if numpy.ma.count(result)==0: result = numpy.ma.ones(len(dt_start),dtype=numpy.float32)*float(c.large_value)
                # put the data into the right order to be plotted
                dt,data = gfalternate_plotsummary_getdata(dt_start,dt_end,result)
                # plot the results
                axs[row,col].plot(dt,data)
                # put in the major ticks
                axs[row,col].xaxis.set_major_locator(MTLoc)
                # if this is not the last row, hide the tick mark labels
                if row<len(result_list)-1: plt.setp(axs[row,col].get_xticklabels(),visible=False)
                # if this is the last row, add the major tick mark and axis labels
                if row==len(result_list)-1:
                    axs[row,col].xaxis.set_major_formatter(MTFmt)
                    axs[row,col].set_xlabel('Month',visible=True)
        # draw the plot
        plt.draw()
        # make the hard-copy file name and save the plot as a PNG file
        sdt = startdate.strftime("%Y%m%d")
        edt = enddate.strftime("%Y%m%d")
        plot_path = alternate_info["plot_path"]+"L4/"
        if not os.path.exists(plot_path): os.makedirs(plot_path)
        figname = plot_path+site_name.replace(" ","")+"_Alternate_FitStatistics_"+figlab
        figname = figname+"_"+sdt+"_"+edt+".png"
        fig.savefig(figname,format="png")

def gfalternate_plotsummary_getdata(dt_start,dt_end,result):
    dt = []
    data = []
    for s,e,r in zip(dt_start,dt_end,result):
        dt.append(s)
        data.append(r)
        dt.append(e)
        data.append(r)
    return dt,data

def gfalternate_progress(alt_gui,text):
    """ Update progress message in alternate GUI."""
    alt_gui.progress.destroy()
    alt_gui.progress = Tkinter.Label(alt_gui, text=text)
    alt_gui.progress.grid(row=9,column=0,columnspan=6,sticky="W")
    alt_gui.update()

def gfalternate_quit(ds,alt_gui):
    """ Quit the GapFillFromAlternate GUI."""
    # destroy the alternate GUI
    #alt_gui.destroy()
    alt_gui.close()
    # put the return code into ds.alternate
    ds.returncodes["alternate"] = "quit"

def gfalternate_run_gui(ds_tower,ds_alt,alt_gui,alternate_info):
    # populate the alternate_info dictionary with things that will be useful
    if str(alt_gui.radioButtons.checkedButton().text()) == "Manual":
        alternate_info["peropt"] = 1
    elif str(alt_gui.radioButtons.checkedButton().text()) == "Monthly":
        alternate_info["peropt"] = 2
    elif str(alt_gui.radioButtons.checkedButton().text()) == "No. Days":
        alternate_info["peropt"] = 3

    alternate_info["overwrite"] = alt_gui.checkBox_Overwrite.isChecked()
    alternate_info["show_plots"] = alt_gui.checkBox_ShowPlots.isChecked()
    alternate_info["show_all"] = alt_gui.checkBox_PlotAll.isChecked()
    alternate_info["auto_complete"] = alt_gui.checkBox_AutoComplete.isChecked()
    alternate_info["autoforce"] = False
    alternate_info["min_percent"] = max(int(str(alt_gui.lineEdit_MinPercent.text())),1)

    alternate_info["site_name"] = ds_tower.globalattributes["site_name"]
    alternate_info["time_step"] = int(ds_tower.globalattributes["time_step"])
    alternate_info["nperhr"] = int(float(60)/alternate_info["time_step"]+0.5)
    alternate_info["nperday"] = int(float(24)*alternate_info["nperhr"]+0.5)
    alternate_info["max_lags"] = int(float(12)*alternate_info["nperhr"]+0.5)
    alternate_info["tower"] = {}
    alternate_info["alternate"] = {}
    series_list = [ds_tower.alternate[item]["label_tower"] for item in ds_tower.alternate.keys()]
    alternate_info["series_list"] = series_list
    #alternate_info["series_list"] = ["Ah","Ta"]
    logger.info(" Gap filling "+str(list(set(series_list)))+" using alternate data")
    if alternate_info["peropt"]==1:
        logger.info("Starting manual run ...")
        #gfalternate_progress(alt_gui,"Starting manual run ...")
        # get the start and end datetimes entered in the alternate GUI
        if len(str(alt_gui.lineEdit_StartDate.text())) != 0:
            alternate_info["startdate"] = str(alt_gui.lineEdit_StartDate.text())
        if len(str(alt_gui.lineEdit_EndDate.text())) != 0:
            alternate_info["enddate"] = str(alt_gui.lineEdit_EndDate.text())
        #logger.info(" Calling gfalternate_main ...")
        gfalternate_main(ds_tower,ds_alt,alternate_info)
        #logger.info(" Calling gfalternate_plotcoveragelines ...")
        gfalternate_plotcoveragelines(ds_tower,alternate_info)
        #gfalternate_progress(alt_gui,"Finished manual run ...")
        logger.info("Finished manual run ...")
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the alternate_info dictionary, this will hold much useful information
        alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    elif alternate_info["peropt"]==2:
        logger.info("Starting auto (monthly) run ...")
        #gfalternate_progress(alt_gui,"Starting auto (monthly) run ...")
        # get the start datetime entered in the alternate GUI
        if len(str(alt_gui.lineEdit_StartDate.text()))!=0:
            alternate_info["startdate"] = str(alt_gui.lineEdit_StartDate.text())
        alternate_info["gui_startdate"] = alternate_info["startdate"]
        alternate_info["gui_enddate"] = alternate_info["enddate"]
        startdate = dateutil.parser.parse(alternate_info["startdate"])
        overlap_startdate = dateutil.parser.parse(alternate_info["overlap_startdate"])
        overlap_enddate = dateutil.parser.parse(alternate_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([overlap_enddate,enddate])
        alternate_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<overlap_enddate:
            gfalternate_main(ds_tower,ds_alt,alternate_info)
            gfalternate_plotcoveragelines(ds_tower,alternate_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            alternate_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            enddate = min([enddate,overlap_enddate])
            alternate_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        gfalternate_autocomplete(ds_tower,ds_alt,alternate_info)
        #gfalternate_progress(alt_gui,"Finished auto (monthly) run ...")
        logger.info("Finished auto (monthly) run ...")
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the alternate_info dictionary, this will hold much useful information
        alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    elif alternate_info["peropt"]==3:
        logger.info("Starting auto (days) run ...")
        #gfalternate_progress(alt_gui,"Starting auto (days) run ...")
        # get the start datetime entered in the alternate GUI
        nDays = int(alt_gui.lineEdit_NumberDays.text())
        if len(str(alt_gui.lineEdit_StartDate.text())) != 0:
            alternate_info["startdate"] = str(alt_gui.lineEdit_StartDate.text())
        if len(str(alt_gui.lineEdit_EndDate.text())) != 0:
            alternate_info["enddate"] = str(alt_gui.lineEdit_EndDate.text())
        alternate_info["gui_startdate"] = alternate_info["startdate"]
        alternate_info["gui_enddate"] = alternate_info["enddate"]
        startdate = dateutil.parser.parse(alternate_info["startdate"])
        gui_enddate = dateutil.parser.parse(alternate_info["gui_enddate"])
        overlap_enddate = dateutil.parser.parse(alternate_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([overlap_enddate,enddate,gui_enddate])
        alternate_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        alternate_info["startdate"] = datetime.datetime.strftime(startdate,"%Y-%m-%d %H:%M")
        stopdate = min([overlap_enddate,gui_enddate])
        while startdate<stopdate:
            gfalternate_main(ds_tower,ds_alt,alternate_info)
            gfalternate_plotcoveragelines(ds_tower,alternate_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            alternate_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            alternate_info["enddate"] = run_enddate.strftime("%Y-%m-%d %H:%M")
        gfalternate_autocomplete(ds_tower,ds_alt,alternate_info)
        #gfalternate_progress(alt_gui,"Finished auto (days) run ...")
        logger.info("Finished auto (days) run ...")
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the alternate_info dictionary, this will hold much useful information
        alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    else:
        logger.error("GapFillFromAlternate: unrecognised period option")
    # write Excel spreadsheet with fit statistics
    #pfp_io.xl_write_AlternateStats(ds_tower)

def gfalternate_run_nogui(cf,ds_tower,ds_alt,alternate_info):
    # populate the alternate_info dictionary with things that will be useful
    # autoforce is used by gfalternate_autocomplete
    alternate_info["autoforce"] = False
    # period option
    dt_tower = ds_tower.series["DateTime"]["Data"]
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"period_option",default="manual",mode="quiet")
    if opt=="manual":
        alternate_info["peropt"] = 1
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"start_date",default="",mode="quiet")
        alternate_info["startdate"] = dt_tower[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: alternate_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"end_date",default="",mode="quiet")
        alternate_info["enddate"] = dt_tower[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: alternate_info["enddate"] = ed
    elif opt=="monthly":
        alternate_info["peropt"] = 2
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"start_date",default="",mode="quiet")
        alternate_info["startdate"] = dt_tower[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: alternate_info["startdate"] = sd
    elif opt=="days":
        alternate_info["peropt"] = 3
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"start_date",default="",mode="quiet")
        alternate_info["startdate"] = dt_tower[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: alternate_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"end_date",default="",mode="quiet")
        alternate_info["enddate"] = dt_tower[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: alternate_info["enddate"] = ed
    # overwrite option
    alternate_info["overwrite"] = False
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"overwrite",default="no",mode="quiet")
    if opt.lower()=="yes": alternate_info["overwrite"] = True
    # show plots option
    alternate_info["show_plots"] = True
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"show_plots",default="yes",mode="quiet")
    if opt.lower()=="no": alternate_info["show_plots"] = False
    # show all plots option
    alternate_info["show_all"] = False
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"show_all",default="no",mode="quiet")
    if opt.lower()=="yes": alternate_info["show_all"] = True
    # auto-complete option
    alternate_info["auto_complete"] = True
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"auto_complete",default="yes",mode="quiet")
    if opt.lower()=="no": alternate_info["auto_complete"] = False
    # minimum percentage of good points required
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"min_percent",default=50,mode="quiet")
    alternate_info["min_percent"] = max(int(opt),1)
    # number of days
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","Alternate"],"number_days",default=90,mode="quiet")
    alternate_info["number_days"] = int(opt)
    # now set up the rest of the alternate_info dictionary
    alternate_info["site_name"] = ds_tower.globalattributes["site_name"]
    alternate_info["time_step"] = int(ds_tower.globalattributes["time_step"])
    alternate_info["nperhr"] = int(float(60)/alternate_info["time_step"]+0.5)
    alternate_info["nperday"] = int(float(24)*alternate_info["nperhr"]+0.5)
    alternate_info["max_lags"] = int(float(12)*alternate_info["nperhr"]+0.5)
    alternate_info["tower"] = {}
    alternate_info["alternate"] = {}
    series_list = [ds_tower.alternate[item]["label_tower"] for item in ds_tower.alternate.keys()]
    alternate_info["series_list"] = series_list
    #alternate_info["series_list"] = ["Ah","Ta"]
    logger.info(" Gap filling "+str(list(set(series_list)))+" using alternate data")
    if alternate_info["peropt"]==1:
        gfalternate_main(ds_tower,ds_alt,alternate_info)
        #gfalternate_plotcoveragelines(ds_tower)
        # get the start and end datetime of the tower data
        startdate = dt_tower[0]
        enddate = dt_tower[-1]
        # create the alternate_info dictionary, this will hold much useful information
        alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    elif alternate_info["peropt"]==2:
        startdate = dateutil.parser.parse(alternate_info["startdate"])
        overlap_startdate = dateutil.parser.parse(alternate_info["overlap_startdate"])
        overlap_enddate = dateutil.parser.parse(alternate_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([overlap_enddate,enddate])
        alternate_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<overlap_enddate:
            gfalternate_main(ds_tower,ds_alt,alternate_info)
            #gfalternate_plotcoveragelines(ds_tower)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            alternate_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            alternate_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        gfalternate_autocomplete(ds_tower,ds_alt,alternate_info)
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the alternate_info dictionary, this will hold much useful information
        alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    elif alternate_info["peropt"]==3:
        nDays = alternate_info["number_days"]
        alternate_info["gui_startdate"] = alternate_info["startdate"]
        alternate_info["gui_enddate"] = alternate_info["enddate"]
        startdate = dateutil.parser.parse(alternate_info["startdate"])
        gui_enddate = dateutil.parser.parse(alternate_info["gui_enddate"])
        overlap_enddate = dateutil.parser.parse(alternate_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([overlap_enddate,enddate,gui_enddate])
        alternate_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        alternate_info["startdate"] = datetime.datetime.strftime(startdate,"%Y-%m-%d %H:%M")
        stopdate = min([overlap_enddate,gui_enddate])
        while startdate<stopdate:
            gfalternate_main(ds_tower,ds_alt,alternate_info)
            #gfalternate_plotcoveragelines(ds_tower)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            alternate_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            alternate_info["enddate"] = run_enddate.strftime("%Y-%m-%d %H:%M")
        gfalternate_autocomplete(ds_tower,ds_alt,alternate_info)
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the alternate_info dictionary, this will hold much useful information
        alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    else:
        logger.error("GapFillFromAlternate: unrecognised period option")
    # write Excel spreadsheet with fit statistics
    pfp_io.xl_write_AlternateStats(ds_tower)

#def gfalternate_startendtimesmatch(ldt_tower,ldt_alternate,alternate_info,mode="verbose"):
    #""" Checks the start and end times of the tower and alternate data."""
    ## initialise the return code
    #return_code = True
    ## local pointers to the start and end indices for the tower and alternate data
    #si_tower = alternate_info["tower"]["si"]
    #ei_tower = alternate_info["tower"]["ei"]
    #si_alternate = alternate_info["alternate"]["si"]
    #ei_alternate = alternate_info["alternate"]["ei"]
    ## test for the start and end times being equal
    #match_start = (ldt_tower[si_tower]==ldt_alternate[si_alternate])
    #match_end = (ldt_tower[ei_tower]==ldt_alternate[ei_alternate])
    #no_overlap_start = (ldt_tower[si_tower]>=ldt_alternate[ei_alternate])
    #no_overlap_end = (ldt_tower[ei_tower]<=ldt_alternate[si_alternate])
    #overlap_start = (ldt_tower[si_tower]>ldt_alternate[si_alternate]) and (ldt_tower[si_tower]<ldt_alternate[ei_tower])
    #overlap_end = (ldt_tower[ei_tower]>ldt_alternate[si_alternate]) and (ldt_tower[ei_tower]<ldt_alternate[ei_tower])
    ## if the start and end times are equal then set the match type and return
    #if match_start and match_end:
        #msg = " Start and end times match for "+alternate_info["label_output"]
        #if mode=="verbose": logger.info(msg)
        #return_code = True
        #alternate_info["getseries_mode"] = "truncate"
    ## check for no overlap
    #elif no_overlap_start or no_overlap_end:
        #msg = " No overlap between tower and alternate data for "+alternate_info["label_output"]
        #if mode=="verbose": logger.info(msg)
        #return_code = False
        #alternate_info["getseries_mode"] = "truncate"
    ## check for overlap
    #elif overlap_start or overlap_end:
        #msg = " Start and end times overlap for "+alternate_info["label_output"]
        #if mode=="verbose": logger.info(msg)
        #return_code = True
        #alternate_info["getseries_mode"] = "pad"
        #pass
    #else:
        #msg = " gfalternate_startendtimesmatch: Unrecognised start or end time combination"
        #log.error(msg)
        #msg = " gfalternate_startendtimesmatch: variables are: "+alternate_info["label_tower"]
        #msg = msg+","+alternate_info["label_output"]+","+alternate_info["label_alternate"]
        #log.error(msg)
        #return_code = False
        #alternate_info["getseries_mode"] = "truncate"
    #return return_code

def gfalternate_updatedict(cf,ds_tower,ds_alt):
    """
    Update the ds.alternate dictionary.  This is done after reading the control file so
    that the user can make changes to the control file while the gap fill GUI is still
    displayed and the re-run the gap filling.  This gives a measure of interactive-like
    behaviour to the gap filling process.
    """
    if "alternate" not in dir(ds_tower): return
    section = "Drivers"
    series_list = cf[section].keys()
    for series in series_list:
        if "GapFillFromAlternate" not in cf[section][series].keys(): continue
        # name of alternate output series in ds
        output_list = cf[section][series]["GapFillFromAlternate"].keys()
        # loop over the outputs listed in the control file
        for output in output_list:
            if output not in ds_tower.alternate.keys(): ds_tower.alternate[output] = {}
            ds_tower.alternate[output]["label_tower"] = series
            # source name
            ds_tower.alternate[output]["source"] = cf[section][series]["GapFillFromAlternate"][output]["source"]
            # site name
            ds_tower.alternate[output]["site_name"] = ds_tower.globalattributes["site_name"]
            # alternate data file name
            # first, look in the [Files] section for a generic file name
            file_list = cf["Files"].keys()
            lower_file_list = [item.lower() for item in file_list]
            if ds_tower.alternate[output]["source"].lower() in lower_file_list:
                # found a generic file name
                i = lower_file_list.index(ds_tower.alternate[output]["source"].lower())
                ds_tower.alternate[output]["file_name"] = cf["Files"][file_list[i]]
            else:
                # no generic file name found, look for a file name in the variable section
                ds_tower.alternate[output]["file_name"] = cf[section][series]["GapFillFromAlternate"][output]["file_name"]
            # if the file has not already been read, do it now
            if ds_tower.alternate[output]["file_name"] not in ds_alt:
                ds_alt[ds_tower.alternate[output]["file_name"]] = pfp_io.nc_read_series(ds_tower.alternate[output]["file_name"])
            # get the type of fit
            ds_tower.alternate[output]["fit_type"] = "OLS"
            if "fit" in cf[section][series]["GapFillFromAlternate"][output]:
                if cf[section][series]["GapFillFromAlternate"][output]["fit"].lower() in ["ols","ols_thru0","mrev","replace","rma","odr"]:
                    ds_tower.alternate[output]["fit_type"] = cf[section][series]["GapFillFromAlternate"][output]["fit"]
                else:
                    logger.info("gfAlternate: unrecognised fit option for series "+output)
            # force the fit through the origin
            #ds_tower.alternate[output]["thru0"] = "no"
            #if "thru0" in cf[section][series]["GapFillFromAlternate"][output]:
                #if cf[section][series]["GapFillFromAlternate"][output]["thru0"].lower() in ["yes","true"]:
                    #ds_tower.alternate[output]["thru0"] = "yes"
                #else:
                    #log.info("gfAlternate: unrecognised thru0 option for series "+output)
            # correct for lag?
            if "lag" in cf[section][series]["GapFillFromAlternate"][output]:
                if cf[section][series]["GapFillFromAlternate"][output]["lag"].lower() in ["no","false"]:
                    ds_tower.alternate[output]["lag"] = "no"
                elif cf[section][series]["GapFillFromAlternate"][output]["lag"].lower() in ["yes","true"]:
                    ds_tower.alternate[output]["lag"] = "yes"
                else:
                    logger.info("gfAlternate: unrecognised lag option for series "+output)
            else:
                ds_tower.alternate[output]["lag"] = "yes"
            # alternate data variable name if different from name used in control file
            if "alternate_name" in cf[section][series]["GapFillFromAlternate"][output]:
                ds_tower.alternate[output]["alternate_name"] = cf[section][series]["GapFillFromAlternate"][output]["alternate_name"]
            else:
                ds_tower.alternate[output]["alternate_name"] = series
            # results of best fit for plotting later on
            if "results" not in ds_tower.alternate[output].keys():
                ds_tower.alternate[output]["results"] = {"startdate":[],"enddate":[],"No. points":[],"r":[],
                                                         "Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                                                         "Avg (tower)":[],"Avg (alternate)":[],
                                                         "Var (tower)":[],"Var (alternate)":[],"Var ratio":[],
                                                         "Lag (uncorrected)":[],"Lag (corrected)":[],
                                                         "Slope":[],"Offset":[]}
            # create an empty series in ds if the alternate output series doesn't exist yet
            if output not in ds_tower.series.keys():
                data,flag,attr = pfp_utils.MakeEmptySeries(ds_tower,output)
                pfp_utils.CreateSeries(ds_tower,output,data,flag,attr)

def gfalternate_update_alternate_info(ds_tower,alternate_info):
    """Update the alternate_info dictionary."""
    label_output = alternate_info["label_output"]
    alternate_info["fit_type"] = ds_tower.alternate[label_output]["fit_type"]
    alternate_info["lag"] = ds_tower.alternate[label_output]["lag"]
    #alternate_info["thru0"] = ds_tower.alternate[label_output]["thru0"]
    # autoforce is set true in gfalternate_autocomplete if there is not enough good points
    # in the tower data for the whole time series, in this case we will use the alternate
    # data "as is" by forcing a "replace" with no lag correction.
    if alternate_info["autoforce"]:
        alternate_info["min_points"] = 0
        alternate_info["fit_type"] = "replace"
        alternate_info["lag"] = "no"

# functions for GapFillUsingInterpolation
def GapFillUsingInterpolation(cf,ds):
    """
    Purpose:
     Gap fill variables in the data structure using interpolation.
     All variables in the [Variables], [Drivers] and [Fluxes] section
     are processed.
    Usage:
     pfp_gf.GapFillUsingInterpolation(cf,ds)
     where cf is a control file object
           ds is a data structure
    Author: PRI
    Date: September 2016
    """
    label_list = pfp_utils.get_label_list_from_cf(cf)
    maxlen = int(pfp_utils.get_keyvaluefromcf(cf,["Options"],"MaxGapInterpolate",default=2))
    if maxlen==0:
        msg = " Gap fill by interpolation disabled in control file"
        logger.info(msg)
        return
    for label in label_list:
        section = pfp_utils.get_cfsection(cf, series=label)
        if "MaxGapInterpolate" in cf[section][label]:
            maxlen = int(pfp_utils.get_keyvaluefromcf(cf,[section,label],"MaxGapInterpolate",default=2))
            if maxlen==0:
                msg = " Gap fill by interpolation disabled for "+label
                logger.info(msg)
                continue
            pfp_ts.InterpolateOverMissing(ds,series=label,maxlen=2)

# functions for GapFillUsingSOLO
def GapFillUsingSOLO(cf,dsa,dsb):
    '''
    This is the "Run SOLO" GUI.
    The SOLO GUI is displayed separately from the main OzFluxQC GUI.
    It consists of text to display the start and end datetime of the file,
    two entry boxes for the start and end datetimes of the SOLO run and
    a button to run SOLO ("Run SOLO") and a button to exit the SOLO GUI
    when we are done.  On exit, the OzFluxQC main GUI continues and eventually
    writes the gap filled data to file.
    '''
    # set the default return code
    dsb.returncodes["solo"] = "normal"
    if "solo" not in dir(dsb): return
    # local pointer to the datetime series
    ldt = dsb.series["DateTime"]["Data"]
    startdate = ldt[0]
    enddate = ldt[-1]
    solo_info = {"file_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                 "file_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                 "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                 "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf,["Options"],"call_mode",default="interactive")
    solo_info["call_mode"]= call_mode
    if call_mode.lower()=="interactive": solo_info["show_plots"] = True
    if call_mode.lower()=="interactive":
        # put up a plot of the data coverage at L4
        gfSOLO_plotcoveragelines(dsb,solo_info)
        # call the GapFillUsingSOLO GUI
        gfSOLO_gui(cf,dsa,dsb,solo_info)
    else:
        if "GUI" in cf:
            if "SOLO" in cf["GUI"]:
                gfSOLO_run_nogui(cf,dsa,dsb,solo_info)
            else:
                logger.warning(" No GUI sub-section found in Options section of control file")
                gfSOLO_plotcoveragelines(dsb,solo_info)
                gfSOLO_gui(cf,dsa,dsb,solo_info)
        else:
            logger.warning(" No GUI sub-section found in Options section of control file")
            gfSOLO_plotcoveragelines(dsb,solo_info)
            gfSOLO_gui(cf,dsa,dsb,solo_info)

def  gfSOLO_gui(cf,dsa,dsb,solo_info):
    ldt = dsb.series["DateTime"]["Data"]
    # set up the GUI
    solo_gui = Tkinter.Toplevel()
    solo_gui.wm_title("SOLO GUI (Fluxes)")
    solo_gui.grid()
    # top row
    nrow = 0
    solo_gui.nodesLabel = Tkinter.Label(solo_gui,text="Nodes")
    solo_gui.nodesLabel.grid(row=nrow,column=0,columnspan=1,sticky="E")
    solo_gui.nodesEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.nodesEntry.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.nodesEntry.insert(0,"Auto")
    solo_gui.trainingLabel = Tkinter.Label(solo_gui,text="Training")
    solo_gui.trainingLabel.grid(row=nrow,column=2,columnspan=1,sticky="E")
    solo_gui.trainingEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.trainingEntry.grid(row=nrow,column=3,columnspan=1,sticky="W")
    solo_gui.trainingEntry.insert(0,"500")
    solo_gui.factorLabel = Tkinter.Label(solo_gui,text="Nda factor")
    solo_gui.factorLabel.grid(row=nrow,column=4,columnspan=1,sticky="E")
    solo_gui.factorEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.factorEntry.grid(row=nrow,column=5,columnspan=1,sticky="W")
    solo_gui.factorEntry.insert(0,"5")
    # second row
    nrow = nrow + 1
    solo_gui.learningrateLabel = Tkinter.Label(solo_gui,text="Learning")
    solo_gui.learningrateLabel.grid(row=nrow,column=2,columnspan=1,sticky="E")
    solo_gui.learningrateEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.learningrateEntry.grid(row=nrow,column=3,columnspan=1,sticky="W")
    solo_gui.learningrateEntry.insert(0,"0.001")
    solo_gui.iterationsLabel = Tkinter.Label(solo_gui,text="Iterations")
    solo_gui.iterationsLabel.grid(row=nrow,column=4,columnspan=1,sticky="E")
    solo_gui.iterationsEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.iterationsEntry.grid(row=nrow,column=5,columnspan=1,sticky="W")
    solo_gui.iterationsEntry.insert(0,"500")
    # third row
    nrow = nrow + 1
    solo_gui.filestartLabel = Tkinter.Label(solo_gui,text="File start date")
    solo_gui.filestartLabel.grid(row=nrow,column=0,columnspan=3)
    solo_gui.fileendLabel = Tkinter.Label(solo_gui,text="File end date")
    solo_gui.fileendLabel.grid(row=nrow,column=3,columnspan=3)
    # fourth row
    nrow = nrow + 1
    solo_gui.filestartValue = Tkinter.Label(solo_gui,text=str(ldt[0]))
    solo_gui.filestartValue.grid(row=nrow,column=0,columnspan=3)
    solo_gui.fileendValue = Tkinter.Label(solo_gui,text=str(ldt[-1]))
    solo_gui.fileendValue.grid(row=nrow,column=3,columnspan=3)
    # fifth row
    nrow = nrow + 1
    solo_gui.startLabel = Tkinter.Label(solo_gui, text="Start date (YYYY-MM-DD)")
    solo_gui.startLabel.grid(row=nrow,column=0,columnspan=3)
    solo_gui.startEntry = Tkinter.Entry(solo_gui)
    solo_gui.startEntry.grid(row=nrow,column=3,columnspan=3)
    # sixth row
    nrow = nrow + 1
    solo_gui.endLabel = Tkinter.Label(solo_gui, text="End date   (YYYY-MM-DD)")
    solo_gui.endLabel.grid(row=nrow,column=0,columnspan=3)
    solo_gui.endEntry = Tkinter.Entry(solo_gui)
    solo_gui.endEntry.grid(row=nrow,column=3,columnspan=3)
    # seventh row
    nrow = nrow + 1
    solo_gui.peropt = Tkinter.IntVar()
    solo_gui.peropt.set(2)
    solo_gui.manualperiod = Tkinter.Radiobutton(solo_gui,text="Manual",variable=solo_gui.peropt,value=1)
    solo_gui.manualperiod.grid(row=nrow,column=0,columnspan=1,sticky="W")
    #solo_gui.manualperiod = Tkinter.Radiobutton(solo_gui,text="Auto",variable=solo_gui.peropt,value=4)
    #solo_gui.manualperiod.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.minptsLabel = Tkinter.Label(solo_gui,text="Min. pts (%)")
    solo_gui.minptsLabel.grid(row=nrow,column=3,columnspan=1,sticky="E")
    solo_gui.minptsEntry = Tkinter.Entry(solo_gui,width=5)
    solo_gui.minptsEntry.grid(row=nrow,column=4,columnspan=1,sticky="W")
    solo_gui.minptsEntry.insert(0,"25")
    # eigth row
    nrow = nrow + 1
    solo_gui.automonthly = Tkinter.Radiobutton(solo_gui,text="Monthly",variable=solo_gui.peropt,value=2)
    solo_gui.automonthly.grid(row=nrow,column=0,columnspan=1,sticky="W")
    solo_gui.daysLabel = Tkinter.Radiobutton(solo_gui,text="Days",variable=solo_gui.peropt,value=3)
    solo_gui.daysLabel.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.daysEntry = Tkinter.Entry(solo_gui,width=3)
    solo_gui.daysEntry.grid(row=nrow,column=2,columnspan=1,sticky="W")
    solo_gui.daysEntry.insert(0,"90")
    solo_gui.autocompleteopt = Tkinter.IntVar()
    solo_gui.autocompleteopt.set(1)
    solo_gui.autocomplete = Tkinter.Checkbutton(solo_gui, text="Auto complete", variable=solo_gui.autocompleteopt)
    solo_gui.autocomplete.grid(row=nrow,column=3,columnspan=3,sticky="w")
    # ninth row
    nrow = nrow + 1
    solo_gui.pltopt = Tkinter.IntVar()
    solo_gui.pltopt.set(1)
    solo_gui.showplots = Tkinter.Checkbutton(solo_gui, text="Show plots", variable=solo_gui.pltopt)
    solo_gui.showplots.grid(row=nrow,column=0,columnspan=3,sticky="w")
    solo_gui.owopt = Tkinter.IntVar()
    solo_gui.owopt.set(0)
    solo_gui.overwrite = Tkinter.Checkbutton(solo_gui, text="Overwrite", variable=solo_gui.owopt)
    solo_gui.overwrite.grid(row=nrow,column=3,columnspan=3,sticky="w")
    # tenth row
    nrow = nrow + 1
    solo_gui.doneButton = Tkinter.Button (solo_gui, text="Done",command=lambda:gfSOLO_done(dsb,solo_gui,solo_info))
    solo_gui.doneButton.grid(row=nrow,column=0,columnspan=2)
    solo_gui.runButton = Tkinter.Button (solo_gui, text="Run",command=lambda:gfSOLO_run_gui(dsa,dsb,solo_gui,solo_info))
    solo_gui.runButton.grid(row=nrow,column=2,columnspan=2)
    solo_gui.quitButton = Tkinter.Button (solo_gui, text="Quit",command=lambda:gfSOLO_quit(dsb,solo_gui))
    solo_gui.quitButton.grid(row=nrow,column=4,columnspan=2)
    # eleventh row
    nrow = nrow + 1
    solo_gui.progress_row = nrow
    solo_gui.progress = Tkinter.Label(solo_gui, text='Waiting for input ...')
    solo_gui.progress.grid(row=nrow,column=0,columnspan=6,sticky="W")

    solo_gui.wait_window(solo_gui)

def gfSOLO_autocomplete(dsa,dsb,solo_info):
    if not solo_info["auto_complete"]: return
    ldt = dsb.series["DateTime"]["Data"]
    nRecs = len(ldt)
    for output in dsb.solo.keys():
        not_enough_points = False
        series = dsb.solo[output]["label_tower"]
        data_solo,flag,attr = pfp_utils.GetSeriesasMA(dsb,output)
        if numpy.ma.count(data_solo)==0: continue
        mask_solo = numpy.ma.getmaskarray(data_solo)
        gapstartend = pfp_utils.contiguous_regions(mask_solo)
        data_obs,flag,attr = pfp_utils.GetSeriesasMA(dsb,series)
        for si_gap,ei_gap in gapstartend:
            #min_points = max([int(((gap[1]-gap[0])+1)*solo_info["min_percent"]/100),3*solo_info["nperhr"]])
            min_points = int((ei_gap-si_gap)*solo_info["min_percent"]/100)
            num_good_points = numpy.ma.count(data_obs[si_gap:ei_gap])
            #print "before while loop ",num_good_points,min_points
            while num_good_points<min_points:
                si_gap = max([0,si_gap - solo_info["nperday"]])
                ei_gap = min([nRecs-1,ei_gap + solo_info["nperday"]])
                if si_gap==0 and ei_gap==nRecs-1:
                    msg = " Unable to find enough good points in series "+series
                    logger.error(msg)
                    not_enough_points = True
                if not_enough_points: break
                min_points = int((ei_gap-si_gap)*solo_info["min_percent"]/100)
                num_good_points = numpy.ma.count(data_obs[si_gap:ei_gap])
            if not_enough_points: break
            si = max([0,si_gap])
            ei = min([len(ldt)-1,ei_gap])
            solo_info["startdate"] = ldt[si].strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = ldt[ei].strftime("%Y-%m-%d %H:%M")
            gfSOLO_main(dsa,dsb,solo_info,output_list=[output])
            gfSOLO_plotcoveragelines(dsb,solo_info)

def gfSOLO_createdict(cf,ds,series):
    """ Creates a dictionary in ds to hold information about the SOLO data used
        to gap fill the tower data."""
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("GapFillUsingSOLO: Series "+series+" not found in control file, skipping ...")
        return
    # create the solo directory in the data structure
    if "solo" not in dir(ds): ds.solo = {}
    # name of SOLO output series in ds
    output_list = cf[section][series]["GapFillUsingSOLO"].keys()
    # loop over the outputs listed in the control file
    for output in output_list:
        # create the dictionary keys for this series
        ds.solo[output] = {}
        # get the target
        if "target" in cf[section][series]["GapFillUsingSOLO"][output]:
            ds.solo[output]["label_tower"] = cf[section][series]["GapFillUsingSOLO"][output]["target"]
        else:
            ds.solo[output]["label_tower"] = series
        # site name
        ds.solo[output]["site_name"] = ds.globalattributes["site_name"]
        # list of SOLO settings
        if "solo_settings" in cf[section][series]["GapFillUsingSOLO"][output]:
            ss_list = ast.literal_eval(cf[section][series]["GapFillUsingSOLO"][output]["solo_settings"])
            ds.solo[output]["solo_settings"] = {}
            ds.solo[output]["solo_settings"]["nodes_target"] = int(ss_list[0])
            ds.solo[output]["solo_settings"]["training"] = int(ss_list[1])
            ds.solo[output]["solo_settings"]["factor"] = int(ss_list[2])
            ds.solo[output]["solo_settings"]["learningrate"] = float(ss_list[3])
            ds.solo[output]["solo_settings"]["iterations"] = int(ss_list[4])
        # list of drivers
        ds.solo[output]["drivers"] = ast.literal_eval(cf[section][series]["GapFillUsingSOLO"][output]["drivers"])
        # apply ustar filter
        opt = pfp_utils.get_keyvaluefromcf(cf,[section,series,"GapFillUsingSOLO",output],
                                         "turbulence_filter",default="")
        ds.solo[output]["turbulence_filter"] = opt
        opt = pfp_utils.get_keyvaluefromcf(cf,[section,series,"GapFillUsingSOLO",output],
                                         "daynight_filter",default="")
        ds.solo[output]["daynight_filter"] = opt
        # results of best fit for plotting later on
        ds.solo[output]["results"] = {"startdate":[],"enddate":[],"No. points":[],"r":[],
                                      "Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                                      "Avg (obs)":[],"Avg (SOLO)":[],
                                      "Var (obs)":[],"Var (SOLO)":[],"Var ratio":[],
                                      "m_ols":[],"b_ols":[]}
        # create an empty series in ds if the SOLO output series doesn't exist yet
        if output not in ds.series.keys():
            data,flag,attr = pfp_utils.MakeEmptySeries(ds,output)
            pfp_utils.CreateSeries(ds,output,data,flag,attr)

def gfSOLO_done(ds,solo_gui,solo_info):
    # plot the summary statistics if gap filling was done manually
    if solo_gui.peropt.get()==1:
        # write Excel spreadsheet with fit statistics
        pfp_io.xl_write_SOLOStats(ds)
        # plot the summary statistics
        gfSOLO_plotsummary(ds,solo_info)
    # destroy the SOLO GUI
    solo_gui.destroy()
    # remove the solo dictionary from the data structure
    ds.returncodes["solo"] = "normal"

def gfSOLO_getserieslist(cf):
    series_list = []
    if "Drivers" in cf.keys():
        for series in cf["Drivers"].keys():
            if "GapFillUsingSOLO" in cf["Drivers"][series]:
                series_list.append(series)
    elif "Fluxes" in cf.keys():
        for series in cf["Fluxes"].keys():
            if "GapFillUsingSOLO" in cf["Fluxes"][series]:
                series_list.append(series)
    elif "Variables" in cf.keys():
        for series in cf["Variables"].keys():
            if "GapFillUsingSOLO" in cf["Variables"][series]:
                series_list.append(series)
    else:
        series_list = []
        msg = "No Variables, Drivers or Fluxes section found in control file"
        logger.error(msg)
    return series_list

def gfSOLO_initplot(**kwargs):
    # set the margins, heights, widths etc
    pd = {"margin_bottom":0.075,"margin_top":0.075,"margin_left":0.05,"margin_right":0.05,
          "xy_height":0.20,"xy_width":0.20,"xyts_space":0.05,"xyts_space":0.05,
          "ts_width":0.9}
    # set the keyword arguments
    for key, value in kwargs.iteritems():
        pd[key] = value
    # calculate bottom of the first time series and the height of the time series plots
    pd["ts_bottom"] = pd["margin_bottom"]+pd["xy_height"]+pd["xyts_space"]
    pd["ts_height"] = (1.0 - pd["margin_top"] - pd["ts_bottom"])/float(pd["nDrivers"]+1)
    return pd

def gfSOLO_main(dsa,dsb,solo_info,output_list=[]):
    '''
    This is the main routine for running SOLO, an artifical neural network for gap filling fluxes.
    '''
    if len(output_list)==0: output_list = dsb.solo.keys()
    startdate = solo_info["startdate"]
    enddate = solo_info["enddate"]
    logger.info(" Gap filling using SOLO: "+startdate+" to "+enddate)
    # read the control file again, this allows the contents of the control file to
    # be changed with the SOLO GUI still displayed
    cfname = dsb.globalattributes["controlfile_name"]
    cf = pfp_io.get_controlfilecontents(cfname, mode="quiet")
    solo_info["plot_path"] = cf["Files"]["plot_path"]
    # put the control file object in the solo_info dictionary
    dsb.cf = cf.copy()
    # get some useful things
    site_name = dsa.globalattributes["site_name"]
    # get the time step and a local pointer to the datetime series
    ts = dsb.globalattributes["time_step"]
    ldt = dsb.series["DateTime"]["Data"]
    xldt = dsb.series["xlDateTime"]["Data"]
    # get the start and end datetime indices
    si = pfp_utils.GetDateIndex(ldt,startdate,ts=ts,default=0,match="exact")
    ei = pfp_utils.GetDateIndex(ldt,enddate,ts=ts,default=len(ldt)-1,match="exact")
    # check the start and end indices
    if si >= ei:
        print " GapFillUsingSOLO: end datetime index ("+str(ei)+") smaller that start ("+str(si)+")"
        return
    if si==0 and ei==-1:
        print " GapFillUsingSOLO: no start and end datetime specified, using all data"
        nRecs = int(dsb.globalattributes["nc_nrecs"])
    else:
        nRecs = ei - si + 1
    # loop over the series to be gap filled using solo
    #solo_info["min_points"] = int(nRecs*solo_info["min_percent"]/100)
    solo_info["min_points"] = int((ei-si)*solo_info["min_percent"]/100)
    # close any open plot windows
    if len(plt.get_fignums())!=0:
        for i in plt.get_fignums():
            if i!=0: plt.close(i)
    fig_num = 0
    for output in output_list:
        # get the target series label
        series = dsb.solo[output]["label_tower"]
        # clean up the target series if required
        variable = pfp_utils.GetVariable(dsb, series)
        pfp_ck.UpdateVariableAttributes_QC(cf, variable)
        pfp_ck.ApplyQCChecks(variable)
        pfp_utils.CreateVariable(dsb, variable)
        # check to see if we are gap filling L5 or L4
        if dsb.globalattributes["nc_level"].lower()=="l4":
            for driver in dsb.solo[output]["drivers"]:
                for mlist in dsb.merge.keys():
                    if driver in dsb.merge[mlist]:
                        srclist = dsb.merge[mlist][driver]["source"]
                pfp_ts.do_mergeseries(dsb,driver,srclist,mode="quiet")
        dsb.solo[output]["results"]["startdate"].append(xldt[si])
        dsb.solo[output]["results"]["enddate"].append(xldt[ei])
        d,f,a = pfp_utils.GetSeriesasMA(dsb,series,si=si,ei=ei)
        if numpy.ma.count(d)<solo_info["min_points"]:
            logger.warning("gfSOLO: Less than "+str(solo_info["min_points"])+" points available for series "+series+" ...")
            dsb.solo[output]["results"]["No. points"].append(float(0))
            results_list = dsb.solo[output]["results"].keys()
            for item in ["startdate","enddate","No. points"]:
                if item in results_list: results_list.remove(item)
            for item in results_list:
                dsb.solo[output]["results"][item].append(float(c.missing_value))
            continue
        drivers = dsb.solo[output]["drivers"]
        if str(solo_info["nodes"]).lower()=="auto":
            solo_info["nodes_target"] = len(drivers)+1
        else:
            solo_info["nodes_target"] = int(solo_info["nodes"])
        #output = dsb.solo[series]["output"]
        # set the number of nodes for the inf files
        #nodesAuto = gfSOLO_setnodesEntry(solo_gui,drivers)
        # overwrite the GUI settings if required
        if "solo_settings" in dsb.solo[output]:
            solo_info["nodes_target"] = dsb.solo[output]["solo_settings"]["nodes_target"]
            solo_info["training"] = dsb.solo[output]["solo_settings"]["training"]
            solo_info["factor"] = dsb.solo[output]["solo_settings"]["factor"]
            solo_info["learningrate"] = dsb.solo[output]["solo_settings"]["learningrate"]
            solo_info["iterations"] = dsb.solo[output]["solo_settings"]["iterations"]
        # write the inf files for sofm, solo and seqsolo
        gfSOLO_writeinffiles(solo_info)
        # run SOFM
        result = gfSOLO_runsofm(dsa,dsb,drivers,series,nRecs,si=si,ei=ei)
        if result!=1: return
        # run SOLO
        result = gfSOLO_runsolo(dsa,dsb,drivers,series,nRecs,si=si,ei=ei)
        if result!=1: return
        # run seqsolo and put the solo_modelled data into the ds series
        result = gfSOLO_runseqsolo(dsa,dsb,drivers,series,output,nRecs,si=si,ei=ei)
        if result!=1: return
        # plot the results
        fig_num = fig_num + 1
        title = site_name+' : Comparison of tower and SOLO data for '+series
        pd = gfSOLO_initplot(site_name=site_name,label=series,fig_num=fig_num,title=title,
                             nDrivers=len(drivers))
        gfSOLO_plot(pd,dsa,dsb,drivers,series,output,solo_info,si=si,ei=ei)
        # reset the nodesEntry in the solo_gui
        #if nodesAuto: gfSOLO_resetnodesEntry(solo_gui)
    if 'GapFillUsingSOLO' not in dsb.globalattributes['Functions']:
        dsb.globalattributes['Functions'] = dsb.globalattributes['Functions']+', GapFillUsingSOLO'

def gfSOLO_plot(pd,dsa,dsb,driverlist,targetlabel,outputlabel,solo_info,si=0,ei=-1):
    """ Plot the results of the SOLO run. """
    # get the time step
    ts = int(dsb.globalattributes['time_step'])
    # get a local copy of the datetime series
    xdt = numpy.array(dsb.series['DateTime']['Data'][si:ei+1])
    Hdh,f,a = pfp_utils.GetSeriesasMA(dsb,'Hdh',si=si,ei=ei)
    # get the observed and modelled values
    obs,f,a = pfp_utils.GetSeriesasMA(dsb,targetlabel,si=si,ei=ei)
    mod,f,a = pfp_utils.GetSeriesasMA(dsb,outputlabel,si=si,ei=ei)
    # make the figure
    if solo_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"],figsize=(13,8))
    fig.clf()
    fig.canvas.set_window_title(targetlabel)
    plt.figtext(0.5,0.95,pd["title"],ha='center',size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask,mod.mask)
    obs_mor = numpy.ma.array(obs,mask=mask)
    Num1,Hr1,Av1,Sd1,Mx1,Mn1 = gf_getdiurnalstats(Hdh,obs_mor,ts)
    ax1.plot(Hr1,Av1,'b-',label="Obs")
    # get the diurnal stats of all SOLO predictions
    Num2,Hr2,Av2,Sd2,Mx2,Mn2 = gf_getdiurnalstats(Hdh,mod,ts)
    ax1.plot(Hr2,Av2,'r-',label="SOLO(all)")
    # get the diurnal stats of SOLO predictions when the obs are present
    mod_mor = numpy.ma.array(mod,mask=mask)
    if numpy.ma.count_masked(obs)!=0:
        index = numpy.where(numpy.ma.getmaskarray(obs)==False)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(obs)==False)[0]
        # get the diurnal stats of SOLO predictions when observations are present
        Num3,Hr3,Av3,Sd3,Mx3,Mn3=gf_getdiurnalstats(Hdh[index],mod_mor[index],ts)
        ax1.plot(Hr3,Av3,'g-',label="SOLO(obs)")
    plt.xlim(0,24)
    plt.xticks([0,6,12,18,24])
    ax1.set_ylabel(targetlabel)
    ax1.set_xlabel('Hour')
    ax1.legend(loc='upper right',frameon=False,prop={'size':8})
    # XY plot of the 30 minute data
    rect2 = [0.40,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    ax2 = plt.axes(rect2)
    ax2.plot(mod,obs,'b.')
    ax2.set_ylabel(targetlabel+'_obs')
    ax2.set_xlabel(targetlabel+'_SOLO')
    # plot the best fit line
    coefs = numpy.ma.polyfit(numpy.ma.copy(mod),numpy.ma.copy(obs),1)
    xfit = numpy.ma.array([numpy.ma.minimum(mod),numpy.ma.maximum(mod)])
    yfit = numpy.polyval(coefs,xfit)
    r = numpy.ma.corrcoef(mod,obs)
    ax2.plot(xfit,yfit,'r--',linewidth=3)
    eqnstr = 'y = %.3fx + %.3f, r = %.3f'%(coefs[0],coefs[1],r[0][1])
    ax2.text(0.5,0.875,eqnstr,fontsize=8,horizontalalignment='center',transform=ax2.transAxes)
    # write the fit statistics to the plot
    numpoints = numpy.ma.count(obs)
    numfilled = numpy.ma.count(mod)-numpy.ma.count(obs)
    diff = mod - obs
    bias = numpy.ma.average(diff)
    fractional_bias = bias/(0.5*(numpy.ma.average(obs+mod)))
    dsb.solo[outputlabel]["results"]["Bias"].append(bias)
    dsb.solo[outputlabel]["results"]["Frac Bias"].append(fractional_bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    mean_mod = numpy.ma.mean(mod)
    mean_obs = numpy.ma.mean(obs)
    data_range = numpy.ma.maximum(obs)-numpy.ma.minimum(obs)
    nmse = rmse/data_range
    plt.figtext(0.65,0.225,'No. points')
    plt.figtext(0.75,0.225,str(numpoints))
    dsb.solo[outputlabel]["results"]["No. points"].append(numpoints)
    plt.figtext(0.65,0.200,'No. filled')
    plt.figtext(0.75,0.200,str(numfilled))
    plt.figtext(0.65,0.175,'Nodes')
    plt.figtext(0.75,0.175,str(solo_info["nodes_target"]))
    plt.figtext(0.65,0.150,'Training')
    plt.figtext(0.75,0.150,str(solo_info["training"]))
    plt.figtext(0.65,0.125,'Nda factor')
    plt.figtext(0.75,0.125,str(solo_info["factor"]))
    plt.figtext(0.65,0.100,'Learning rate')
    plt.figtext(0.75,0.100,str(solo_info["learningrate"]))
    plt.figtext(0.65,0.075,'Iterations')
    plt.figtext(0.75,0.075,str(solo_info["iterations"]))
    plt.figtext(0.815,0.225,'Slope')
    plt.figtext(0.915,0.225,str(pfp_utils.round2sig(coefs[0],sig=4)))
    dsb.solo[outputlabel]["results"]["m_ols"].append(coefs[0])
    plt.figtext(0.815,0.200,'Offset')
    plt.figtext(0.915,0.200,str(pfp_utils.round2sig(coefs[1],sig=4)))
    dsb.solo[outputlabel]["results"]["b_ols"].append(coefs[1])
    plt.figtext(0.815,0.175,'r')
    plt.figtext(0.915,0.175,str(pfp_utils.round2sig(r[0][1],sig=4)))
    dsb.solo[outputlabel]["results"]["r"].append(r[0][1])
    plt.figtext(0.815,0.150,'RMSE')
    plt.figtext(0.915,0.150,str(pfp_utils.round2sig(rmse,sig=4)))
    dsb.solo[outputlabel]["results"]["RMSE"].append(rmse)
    dsb.solo[outputlabel]["results"]["NMSE"].append(nmse)
    var_obs = numpy.ma.var(obs)
    plt.figtext(0.815,0.125,'Var (obs)')
    plt.figtext(0.915,0.125,'%.4g'%(var_obs))
    dsb.solo[outputlabel]["results"]["Var (obs)"].append(var_obs)
    var_mod = numpy.ma.var(mod)
    plt.figtext(0.815,0.100,'Var (SOLO)')
    plt.figtext(0.915,0.100,'%.4g'%(var_mod))
    dsb.solo[outputlabel]["results"]["Var (SOLO)"].append(var_mod)
    dsb.solo[outputlabel]["results"]["Var ratio"].append(var_obs/var_mod)
    dsb.solo[outputlabel]["results"]["Avg (obs)"].append(numpy.ma.average(obs))
    dsb.solo[outputlabel]["results"]["Avg (SOLO)"].append(numpy.ma.average(mod))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"],pd["ts_bottom"],pd["ts_width"],pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    ts_axes[0].plot(xdt,obs,'b.',xdt,mod,'r-')
    ts_axes[0].set_xlim(xdt[0],xdt[-1])
    TextStr = targetlabel+'_obs ('+dsb.series[targetlabel]['Attr']['units']+')'
    ts_axes[0].text(0.05,0.85,TextStr,color='b',horizontalalignment='left',transform=ts_axes[0].transAxes)
    TextStr = outputlabel+'('+dsb.series[outputlabel]['Attr']['units']+')'
    ts_axes[0].text(0.85,0.85,TextStr,color='r',horizontalalignment='right',transform=ts_axes[0].transAxes)
    for ThisOne,i in zip(driverlist,range(1,pd["nDrivers"]+1)):
        this_bottom = pd["ts_bottom"] + i*pd["ts_height"]
        rect = [pd["margin_left"],this_bottom,pd["ts_width"],pd["ts_height"]]
        ts_axes.append(plt.axes(rect,sharex=ts_axes[0]))
        data,flag,attr = pfp_utils.GetSeriesasMA(dsb,ThisOne,si=si,ei=ei)
        data_notgf = numpy.ma.masked_where(flag!=0,data)
        data_gf = numpy.ma.masked_where(flag==0,data)
        ts_axes[i].plot(xdt,data_notgf,'b-')
        ts_axes[i].plot(xdt,data_gf,'r-',linewidth=2)
        plt.setp(ts_axes[i].get_xticklabels(),visible=False)
        TextStr = ThisOne+'('+dsb.series[ThisOne]['Attr']['units']+')'
        ts_axes[i].text(0.05,0.85,TextStr,color='b',horizontalalignment='left',transform=ts_axes[i].transAxes)
    # save a hard copy of the plot
    sdt = xdt[0].strftime("%Y%m%d")
    edt = xdt[-1].strftime("%Y%m%d")
    plot_path = solo_info["plot_path"]+"L5/"
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+pd["site_name"].replace(" ","")+"_SOLO_"+pd["label"]
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    if solo_info["show_plots"]:
        plt.draw()
        plt.pause(0.1)
        plt.ioff()
    else:
        plt.ion()

def gfSOLO_plotcoveragelines(dsb,solo_info):
    ldt = dsb.series["DateTime"]["Data"]
    site_name = dsb.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    output_list = dsb.solo.keys()
    series_list = [dsb.solo[item]["label_tower"] for item in dsb.solo.keys()]
    ylabel_list = [""]+series_list+[""]
    ylabel_right_list = [""]
    series_list = [dsb.solo[item]["label_tower"] for item in output_list]
    color_list = ["blue","red","green","yellow","magenta","black","cyan","brown"]
    xsize = 15.0
    ysize = max([len(output_list)*0.3,1])
    plt.ion()
    if plt.fignum_exists(0):
        fig=plt.figure(0)
        plt.clf()
        ax1 = plt.subplot(111)
    else:
        fig=plt.figure(0,figsize=(xsize,ysize))
        ax1 = plt.subplot(111)
    title = "Coverage: "+site_name+" "+start_date+" to "+end_date
    fig.canvas.set_window_title(title)
    plt.ylim([0,len(output_list)+1])
    plt.xlim([ldt[0],ldt[-1]])
    for output,series,n in zip(output_list,series_list,range(1,len(output_list)+1)):
        data_output,f,a = pfp_utils.GetSeriesasMA(dsb,output)
        data_series,f,a = pfp_utils.GetSeriesasMA(dsb,series)
        percent = 100*numpy.ma.count(data_series)/len(data_series)
        ylabel_right_list.append("{0:.0f}%".format(percent))
        ind_series = numpy.ma.ones(len(data_series))*float(n)
        ind_series = numpy.ma.masked_where(numpy.ma.getmaskarray(data_series)==True,ind_series)
        ind_output = numpy.ma.ones(len(data_output))*float(n)
        ind_output = numpy.ma.masked_where(numpy.ma.getmaskarray(data_output)==True,ind_output)
        plt.plot(ldt,ind_series,color=color_list[numpy.mod(n,8)],linewidth=1)
        plt.plot(ldt,ind_output,color=color_list[numpy.mod(n,8)],linewidth=4)
    ylabel_posn = range(0,len(output_list)+2)
    pylab.yticks(ylabel_posn,ylabel_list)
    ylabel_right_list.append("")
    ax2 = ax1.twinx()
    pylab.yticks(ylabel_posn,ylabel_right_list)
    fig.tight_layout()
    #fig.canvas.manager.window.attributes('-topmost', 1)
    plt.draw()
    plt.ioff()

def gfSOLO_plotsummary(ds,solo_info):
    """ Plot single pages of summary results for groups of variables. """
    if "SOLO_Summary" not in ds.cf:
        msg = " SOLO summary section not in control file"
        logger.info(msg)
        return
    # get a list of variables for which SOLO data was available
    label_list = ds.solo.keys()
    if len(ds.solo[label_list[0]]["results"]["startdate"])==0:
        logger.info("gfSOLO: no summary data to plot")
        return
    # get the Excel datemode, needed to convert the Excel datetime to Python datetimes
    datemode = int(ds.globalattributes['xl_datemode'])
    # site name for titles
    site_name = ds.globalattributes["site_name"]
    # datetimes are stored in ds.alternate as Excel datetimes, here we convert to Python datetimes
    # for ease of handling and plotting.
    # start datetimes of the periods compared first
    basedate = datetime.datetime(1899, 12, 30)
    dt_start = []
    for xldt in ds.solo[label_list[0]]["results"]["startdate"]:
        dt_start.append(basedate+datetime.timedelta(days=xldt+1462*datemode))
    startdate = min(dt_start)
    # and then the end datetimes
    dt_end = []
    for xldt in ds.solo[label_list[0]]["results"]["enddate"]:
        dt_end.append(basedate+datetime.timedelta(days=xldt+1462*datemode))
    enddate = max(dt_end)
    # get the major tick locator and label format
    MTLoc = mdt.AutoDateLocator(minticks=3,maxticks=5)
    MTFmt = mdt.DateFormatter('%b')
    # group lists of the resuts to be plotted
    result_list = ["r","Bias","RMSE","Var ratio","m_ols","b_ols"]
    ylabel_list = ["r","Bias","RMSE","Var ratio","Slope","Offset"]
    # turn on interactive plotting
    if solo_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    # now loop over the group lists
    for nFig in ds.cf["SOLO_Summary"].keys():
        plot_title = ds.cf["SOLO_Summary"][str(nFig)]["Title"]
        var_list = ast.literal_eval(ds.cf["SOLO_Summary"][str(nFig)]["Variables"])
        # set up the subplots on the page
        fig,axs = plt.subplots(len(result_list),len(var_list),figsize=(13,8))
        fig.canvas.set_window_title("SOLO summary: "+plot_title)
        # make a title string for the plot and render it
        title_str = "SOLO: "+plot_title+"; "+site_name+" "+datetime.datetime.strftime(startdate,"%Y-%m-%d")
        title_str = title_str+" to "+datetime.datetime.strftime(enddate,"%Y-%m-%d")
        fig.suptitle(title_str, fontsize=14, fontweight='bold')
        # now loop over the variables in the group list
        for col,label in enumerate(var_list):
            # and loop over rows in plot
            for row,rlabel,ylabel in zip(range(len(result_list)),result_list,ylabel_list):
                # get the results to be plotted
                result = numpy.ma.masked_equal(ds.solo[label]["results"][rlabel],float(c.missing_value))
                # put the data into the right order to be plotted
                dt,data = gfSOLO_plotsummary_getdata(dt_start,dt_end,result)
                # plot the results
                axs[row,col].plot(dt,data)
                # put in the major ticks
                axs[row,col].xaxis.set_major_locator(MTLoc)
                # if this is the left-most column, add the Y axis labels
                if col==0: axs[row,col].set_ylabel(ylabel,visible=True)
                # if this is not the last row, hide the tick mark labels
                if row<len(result_list)-1: plt.setp(axs[row,col].get_xticklabels(),visible=False)
                # if this is the first row, add the column title
                if row==0: axs[row,col].set_title(label)
                # if this is the last row, add the major tick mark and axis labels
                if row==len(result_list)-1:
                    axs[row,col].xaxis.set_major_formatter(MTFmt)
                    axs[row,col].set_xlabel('Month',visible=True)
        # make the hard-copy file name and save the plot as a PNG file
        sdt = startdate.strftime("%Y%m%d")
        edt = enddate.strftime("%Y%m%d")
        plot_path = solo_info["plot_path"]+"L5/"
        if not os.path.exists(plot_path): os.makedirs(plot_path)
        figname = plot_path+site_name.replace(" ","")+"_SOLO_FitStatistics_"
        figname = figname+"_"+sdt+"_"+edt+".png"
        fig.savefig(figname,format="png")
        if solo_info["show_plots"]:
            plt.draw()
            plt.ioff()
        else:
            plt.ion()

def gfSOLO_plotsummary_getdata(dt_start,dt_end,result):
    dt = []
    data = []
    for s,e,r in zip(dt_start,dt_end,result):
        dt.append(s)
        data.append(r)
        dt.append(e)
        data.append(r)
    return dt,data

def gfSOLO_progress(solo_gui,text):
    """
        Update progress message in SOLO GUI
        """
    solo_gui.progress.destroy()
    solo_gui.progress = Tkinter.Label(solo_gui, text=text)
    solo_gui.progress.grid(row=solo_gui.progress_row,column=0,columnspan=6,sticky="W")
    solo_gui.update()

def gfSOLO_quit(ds,solo_gui):
    # destroy the GUI
    solo_gui.destroy()
    # put the return code in ds.returncodes
    ds.returncodes["solo"] = "quit"

def gfSOLO_resetnodesEntry(solo_gui):
    solo_gui.nodesEntry.delete(0,Tkinter.END)
    solo_gui.nodesEntry.insert(0,"Auto")

def gfSOLO_run_gui(dsa,dsb,solo_gui,solo_info):
    # populate the solo_info dictionary with things that will be useful
    solo_info["peropt"] = solo_gui.peropt.get()
    solo_info["overwrite"] = True
    if solo_gui.owopt.get()==0: solo_info["overwrite"] = False
    solo_info["show_plots"] = True
    if solo_gui.pltopt.get()==0: solo_info["show_plots"] = False
    solo_info["auto_complete"] = True
    if solo_gui.autocompleteopt.get()==0: solo_info["auto_complete"] = False
    solo_info["min_percent"] = int(solo_gui.minptsEntry.get())
    solo_info["nodes"] = str(solo_gui.nodesEntry.get())
    solo_info["training"] = str(solo_gui.trainingEntry.get())
    solo_info["factor"] = str(solo_gui.factorEntry.get())
    solo_info["learningrate"] = str(solo_gui.learningrateEntry.get())
    solo_info["iterations"] = str(solo_gui.iterationsEntry.get())
    solo_info["site_name"] = dsb.globalattributes["site_name"]
    solo_info["time_step"] = int(dsb.globalattributes["time_step"])
    solo_info["nperhr"] = int(float(60)/solo_info["time_step"]+0.5)
    solo_info["nperday"] = int(float(24)*solo_info["nperhr"]+0.5)
    solo_info["maxlags"] = int(float(12)*solo_info["nperhr"]+0.5)
    solo_info["series"] = dsb.solo.keys()
    solo_info["tower"] = {}
    solo_info["alternate"] = {}
    series_list = [dsb.solo[item]["label_tower"] for item in dsb.solo.keys()]
    logger.info(" Gap filling "+str(series_list)+" using SOLO")
    if solo_gui.peropt.get()==1:
        gfSOLO_progress(solo_gui,"Starting manual run ...")
        # get the start and end datetimes entered in the SOLO GUI
        if len(solo_gui.startEntry.get())!=0: solo_info["startdate"] = solo_gui.startEntry.get()
        if len(solo_gui.endEntry.get())!=0: solo_info["enddate"] = solo_gui.endEntry.get()
        gfSOLO_main(dsa,dsb,solo_info)
        gfSOLO_plotcoveragelines(dsb,solo_info)
        gfSOLO_progress(solo_gui,"Finished manual run ...")
        logger.info(" GapFillUsingSOLO: Finished manual run ...")
    elif solo_gui.peropt.get()==2:
        gfSOLO_progress(solo_gui,"Starting auto (monthly) run ...")
        # get the start datetime entered in the SOLO GUI
        if len(solo_gui.startEntry.get())!=0: solo_info["startdate"] = solo_gui.startEntry.get()
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<file_enddate:
            gfSOLO_main(dsa,dsb,solo_info)
            gfSOLO_plotcoveragelines(dsb,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(dsa,dsb,solo_info)
        # write Excel spreadsheet with fit statistics
        pfp_io.xl_write_SOLOStats(dsb)
        # plot the summary statistics
        gfSOLO_plotsummary(dsb,solo_info)
        gfSOLO_progress(solo_gui,"Finished auto (monthly) run ...")
        logger.info(" GapFillUsingSOLO: Finished auto (monthly) run ...")
    elif solo_gui.peropt.get()==3:
        gfSOLO_progress(solo_gui,"Starting auto (days) run ...")
        # get the start datetime entered in the SOLO GUI
        if len(solo_gui.startEntry.get())!=0: solo_info["startdate"] = solo_gui.startEntry.get()
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        nDays = int(solo_gui.daysEntry.get())
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<file_enddate:
            gfSOLO_main(dsa,dsb,solo_info)
            gfSOLO_plotcoveragelines(dsb,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(dsa,dsb,solo_info)
        # write Excel spreadsheet with fit statistics
        pfp_io.xl_write_SOLOStats(dsb)
        # plot the summary statistics
        gfSOLO_plotsummary(dsb,solo_info)
        gfSOLO_progress(solo_gui,"Finished auto (days) run ...")
        logger.info(" GapFillUsingSOLO: Finished auto (days) run ...")
    elif solo_gui.peropt.get()==4:
        pass

def gfSOLO_run_nogui(cf,dsa,dsb,solo_info):
    # populate the solo_info dictionary with things that will be useful
    # period option
    dt = dsb.series["DateTime"]["Data"]
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"period_option",default="manual",mode="quiet")
    if opt=="manual":
        solo_info["peropt"] = 1
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"start_date",default="",mode="quiet")
        solo_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: solo_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"end_date",default="",mode="quiet")
        solo_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: solo_info["enddate"] = ed
    elif opt=="monthly":
        solo_info["peropt"] = 2
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"start_date",default="",mode="quiet")
        solo_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: solo_info["startdate"] = sd
    elif opt=="days":
        solo_info["peropt"] = 3
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"start_date",default="",mode="quiet")
        solo_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: solo_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"end_date",default="",mode="quiet")
        solo_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: solo_info["enddate"] = ed
    # overwrite option
    solo_info["overwrite"] = False
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"overwrite",default="no",mode="quiet")
    if opt.lower()=="yes": solo_info["overwrite"] = True
    # show plots option
    solo_info["show_plots"] = True
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"show_plots",default="yes",mode="quiet")
    if opt.lower()=="no": solo_info["show_plots"] = False
    # auto-complete option
    solo_info["auto_complete"] = True
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"auto_complete",default="yes",mode="quiet")
    if opt.lower()=="no": alternate_info["auto_complete"] = False
    # minimum percentage of good points required
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"min_percent",default=50,mode="quiet")
    solo_info["min_percent"] = int(opt)
    # number of days
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"number_days",default=90,mode="quiet")
    solo_info["number_days"] = int(opt)
    # nodes for SOFM/SOLO network
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"nodes",default="auto",mode="quiet")
    solo_info["nodes"] = str(opt)
    # training iterations
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"training",default="500",mode="quiet")
    solo_info["training"] = str(opt)
    # nda factor
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"nda_factor",default="5",mode="quiet")
    solo_info["factor"] = str(opt)
    # learning rate
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"learning",default="0.01",mode="quiet")
    solo_info["learningrate"] = str(opt)
    # learning iterations
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"iterations",default="500",mode="quiet")
    solo_info["iterations"] = str(opt)
    # now set up the rest of the solo_info dictionary
    solo_info["site_name"] = dsb.globalattributes["site_name"]
    solo_info["time_step"] = int(dsb.globalattributes["time_step"])
    solo_info["nperhr"] = int(float(60)/solo_info["time_step"]+0.5)
    solo_info["nperday"] = int(float(24)*solo_info["nperhr"]+0.5)
    solo_info["maxlags"] = int(float(12)*solo_info["nperhr"]+0.5)
    solo_info["series"] = dsb.solo.keys()
    solo_info["tower"] = {}
    solo_info["alternate"] = {}
    series_list = [dsb.solo[item]["label_tower"] for item in dsb.solo.keys()]
    logger.info(" Gap filling "+str(series_list)+" using SOLO")
    if solo_info["peropt"]==1:
        gfSOLO_main(dsa,dsb,solo_info)
        logger.info(" GapFillUsingSOLO: Finished manual run ...")
    elif solo_info["peropt"]==2:
        # get the start datetime entered in the SOLO GUI
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<file_enddate:
            gfSOLO_main(dsa,dsb,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(dsa,dsb,solo_info)
        logger.info(" GapFillUsingSOLO: Finished auto (monthly) run ...")
    elif solo_info["peropt"]==3:
        # get the start datetime entered in the SOLO GUI
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        nDays = int(solo_info["number_days"])
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<file_enddate:
            gfSOLO_main(dsa,dsb,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(dsa,dsb,solo_info)
        logger.info(" GapFillUsingSOLO: Finished auto (days) run ...")
    elif solo_info["peropt"]==4:
        pass
    # write the SOLO fit statistics to an Excel file
    pfp_io.xl_write_SOLOStats(dsb)
    # plot the summary statistics
    gfSOLO_plotsummary(dsb,solo_info)

def gfSOLO_runseqsolo(dsa,dsb,driverlist,targetlabel,outputlabel,nRecs,si=0,ei=-1):
    '''
    Run SEQSOLO.
    '''
    # get the number of drivers
    ndrivers = len(driverlist)
    # add an extra column for the target data
    seqsoloinputdata = numpy.zeros((nRecs,ndrivers+1))
    # now fill the driver data array
    i = 0
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(dsb,TheseOnes,si=si,ei=ei)
        seqsoloinputdata[:,i] = driver[:]
        i = i + 1
    ## a clean copy of the target is pulled from the unmodified ds each time
    #target,flag,attr = pfp_utils.GetSeries(dsa,targetlabel,si=si,ei=ei)
    # get the target data
    target,flag,attr = pfp_utils.GetSeries(dsb,targetlabel,si=si,ei=ei)
    # now load the target data into the data array
    seqsoloinputdata[:,ndrivers] = target[:]
    # now strip out the bad data
    cind = numpy.zeros(nRecs)
    iind = numpy.arange(nRecs)
    # do only the drivers not the target
    for i in range(ndrivers):
        index = numpy.where(seqsoloinputdata[:,i]==c.missing_value)[0]
        if len(index!=0): cind[index] = 1
    # index of good data
    index = numpy.where(cind==0)[0]
    nRecs_good = len(index)
    gooddata = numpy.zeros((nRecs_good,ndrivers+1))
    for i in range(ndrivers+1):
        gooddata[:,i] = seqsoloinputdata[:,i][index]
    # keep track of the good data indices
    goodindex = iind[index]
    # and then write the seqsolo input file
    seqsolofile = open('solo/input/seqsolo_input.csv','wb')
    wr = csv.writer(seqsolofile,delimiter=',')
    for i in range(gooddata.shape[0]):
        wr.writerow(gooddata[i,0:ndrivers+1])
    seqsolofile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/seqOut2.out'): os.remove('solo/output/seqOut2.out')
    # now run SEQSOLO
    #log.info(' GapFillUsingSOLO: running SEQSOLO')
    seqsolologfile = open('solo/log/seqsolo.log','wb')
    if platform.system()=="Windows":
        subprocess.call(['./solo/bin/seqsolo.exe','solo/inf/seqsolo.inf'],stdout=seqsolologfile)
    else:
        subprocess.call(['./solo/bin/seqsolo','solo/inf/seqsolo.inf'],stdout=seqsolologfile)
    seqsolologfile.close()
    # check to see if the solo output file exists, this is used to indicate that solo ran correctly
    if os.path.exists('solo/output/seqOut2.out'):
        # now read in the seqsolo results, use the seqOut2 file so that the learning capability of
        # seqsolo can be used via the "learning rate" and "Iterations" GUI options
        seqdata = numpy.genfromtxt('solo/output/seqOut2.out')
        # put the SOLO modelled data back into the data series
        if ei==-1:
            dsb.series[outputlabel]['Data'][si:][goodindex] = seqdata[:,1]
            dsb.series[outputlabel]['Flag'][si:][goodindex] = numpy.int32(30)
        else:
            dsb.series[outputlabel]['Data'][si:ei+1][goodindex] = seqdata[:,1]
            dsb.series[outputlabel]['Flag'][si:ei+1][goodindex] = numpy.int32(30)
        # set the attributes
        if targetlabel in dsa.series.keys():
            for attr in dsa.series[targetlabel]["Attr"].keys():
                dsb.series[outputlabel]["Attr"][attr] = dsa.series[targetlabel]["Attr"][attr]
        dsb.series[outputlabel]["Attr"]["long_name"] = dsb.series[outputlabel]["Attr"]["long_name"]+", modeled by SOLO"
        return 1
    else:
        logger.error(' gfSOLO_runseqsolo: SEQSOLO did not run correctly, check the SOLO GUI and the log files')
        return 0

def gfSOLO_runsofm(dsa,dsb,driverlist,targetlabel,nRecs,si=0,ei=-1):
    '''
    Run sofm, the pre-processor for SOLO.
    '''
    # get the number of drivers
    ndrivers = len(driverlist)
    # add an extra column for the target data
    sofminputdata = numpy.zeros((nRecs,ndrivers))
    # now fill the driver data array
    i = 0
    badlines = []
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(dsb,TheseOnes,si=si,ei=ei)
        index = numpy.where(abs(driver-float(c.missing_value)<c.eps))[0]
        if len(index)!=0:
            logger.error(' GapFillUsingSOLO: c.missing_value found in driver '+TheseOnes+' at lines '+str(index))
            badlines = badlines+index.tolist()
        sofminputdata[:,i] = driver[:]
        i = i + 1
    if len(badlines)!=0:
        nBad = len(badlines)
        goodlines = [x for x in range(0,nRecs) if x not in badlines]
        sofminputdata = sofminputdata[goodlines,:]
        logger.info(' GapFillUsingSOLO: removed '+str(nBad)+' lines from sofm input file')
        nRecs = len(goodlines)
    # now write the drivers to the SOFM input file
    sofmfile = open('solo/input/sofm_input.csv','wb')
    wr = csv.writer(sofmfile,delimiter=',')
    for i in range(sofminputdata.shape[0]):
        wr.writerow(sofminputdata[i,0:ndrivers])
    sofmfile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/sofm_4.out'): os.remove('solo/output/sofm_4.out')
    # now run SOFM
    sofmlogfile = open('solo/log/sofm.log','wb')
    if platform.system()=="Windows":
        subprocess.call(['./solo/bin/sofm.exe','solo/inf/sofm.inf'],stdout=sofmlogfile)
    else:
        subprocess.call(['./solo/bin/sofm','solo/inf/sofm.inf'],stdout=sofmlogfile)
    sofmlogfile.close()
    # check to see if the sofm output file exists, this is used to indicate that sofm ran correctly
    if os.path.exists('solo/output/sofm_4.out'):
        return 1
    else:
        logger.error(' gfSOLO_runsofm: SOFM did not run correctly, check the SOLO GUI and the log files')
        return 0

def gfSOLO_runsolo(dsa,dsb,driverlist,targetlabel,nRecs,si=0,ei=-1):
    '''
    Run SOLO.
    '''
    ndrivers = len(driverlist)
    # add an extra column for the target data
    soloinputdata = numpy.zeros((nRecs,ndrivers+1))
    # now fill the driver data array, drivers come from the modified ds
    i = 0
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(dsb,TheseOnes,si=si,ei=ei)
        soloinputdata[:,i] = driver[:]
        i = i + 1
    ## a clean copy of the target is pulled from the unmodified ds each time
    #target,flag,attr = pfp_utils.GetSeries(dsa,targetlabel,si=si,ei=ei)
    # get the target data
    target,flag,attr = pfp_utils.GetSeries(dsb,targetlabel,si=si,ei=ei)
    # now load the target data into the data array
    soloinputdata[:,ndrivers] = target[:]
    # now strip out the bad data
    cind = numpy.zeros(nRecs)
    for i in range(ndrivers+1):
        index = numpy.where(soloinputdata[:,i]==c.missing_value)[0]
        if len(index!=0): cind[index] = 1
    index = numpy.where(cind==0)[0]
    nRecs_good = len(index)
    gooddata = numpy.zeros((nRecs_good,ndrivers+1))
    for i in range(ndrivers+1):
        gooddata[:,i] = soloinputdata[:,i][index]
    # and then write the solo input file, the name is assumed by the solo.inf control file
    solofile = open('solo/input/solo_input.csv','wb')
    wr = csv.writer(solofile,delimiter=',')
    for i in range(gooddata.shape[0]):
        wr.writerow(gooddata[i,0:ndrivers+1])
    solofile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/eigenValue.out'): os.remove('solo/output/eigenValue.out')
    # now run SOLO
    #log.info(' GapFillUsingSOLO: running SOLO')
    solologfile = open('solo/log/solo.log','wb')
    if platform.system()=="Windows":
        subprocess.call(['./solo/bin/solo.exe','solo/inf/solo.inf'],stdout=solologfile)
    else:
        subprocess.call(['./solo/bin/solo','solo/inf/solo.inf'],stdout=solologfile)
    solologfile.close()
    # check to see if the solo output file exists, this is used to indicate that solo ran correctly
    if os.path.exists('solo/output/eigenValue.out'):
        return 1
    else:
        logger.error(' gfSOLO_runsolo: SOLO did not run correctly, check the SOLO GUI and the log files')
        return 0

def gfSOLO_setnodesEntry(solo_gui,drivers):
    nodesAuto = False
    if str(solo_gui.nodesEntry.get()).lower()=="auto":
        nodesAuto = True
        solo_gui.nodesEntry.delete(0,Tkinter.END)
        solo_gui.nodesEntry.insert(0,str(len(drivers)+1))
    return nodesAuto

def gfSOLO_writeinffiles(solo_info):
    # sofm inf file
    f = open('solo/inf/sofm.inf','w')
    f.write(str(solo_info["nodes_target"])+'\n')
    f.write(str(solo_info["training"])+'\n')
    f.write(str(20)+'\n')
    f.write(str(0.01)+'\n')
    f.write(str(1234)+'\n')
    f.write('solo/input/sofm_input.csv'+'\n')
    f.write('solo/output/sofm_1.out'+'\n')
    f.write('solo/output/sofm_2.out'+'\n')
    f.write('solo/output/sofm_3.out'+'\n')
    f.write('solo/output/sofm_4.out'+'\n')
    f.write(str(50)+'\n')
    f.write('### Comment lines ###\n')
    f.write('Line 1: No. of nodes - default is the number of drivers plus 1 (changeable via GUI if used)\n')
    f.write('Line 2: No. of training iterations - default is 500 (changeable via GUI if used)\n')
    f.write('Line 3: No. of iterations per screen output - default is 20\n')
    f.write('Line 4: Spacing between initial weights - default is 0.01\n')
    f.write('Line 5: Seed for random number generator - default is 1234\n')
    f.write('Line 6: input data filename with path relative to current directory\n')
    f.write('Line 7: first output filename with path relative to current directory\n')
    f.write('Line 8: second output filename with path relative to current directory\n')
    f.write('Line 9: third output filename with path relative to current directory\n')
    f.write('Line 10: fourth output filename with path relative to current directory (used by SOLO)\n')
    f.write('Line 11: No. iterations per write of weights to screen - default is 50\n')
    f.close()
    # solo inf file
    f = open('solo/inf/solo.inf','w')
    f.write(str(solo_info["nodes_target"])+'\n')
    f.write(str(solo_info["factor"])+'\n')
    f.write('solo/output/sofm_4.out'+'\n')
    f.write('solo/input/solo_input.csv'+'\n')
    f.write('training'+'\n')
    f.write(str(5678)+'\n')
    f.write(str(0)+'\n')
    f.write('solo/output/eigenValue.out'+'\n')
    f.write('solo/output/eigenVector.out'+'\n')
    f.write('solo/output/accumErr.out'+'\n')
    f.write('solo/output/accumRR.out'+'\n')
    f.write('solo/output/trainProcess.out'+'\n')
    f.write('solo/output/freqTable.out'+'\n')
    f.write('solo/output/hidOutputWt.out'+'\n')
    f.write('solo/output/errorMap.out'+'\n')
    f.write('solo/output/finResult.out'+'\n')
    f.write('solo/output/trainWin.out'+'\n')
    f.write('solo/output/trainWout.out'+'\n')
    f.write('### Comment lines ###\n')
    f.write('Line 1: No. of nodes - default is the number of drivers plus 1 (changeable via GUI if used)\n')
    f.write('Line 2: multiplier for minimum number of points per node (NdaFactor) - default is 5 (ie 5*(no. of drivers+1) (changeable via GUI if used)\n')
    f.write('Line 3: fourth output file from SOFM, used as input to SOLO\n')
    f.write('Line 4: input data filename with path relative to current directory\n')
    f.write('Line 5: type of run ("training" or "simulation", always "training" for SOLO)\n')
    f.write('Line 6: seed for random number generator - default is 5678\n')
    f.write('Line 7: "calThreshold", not used by SOLO\n')
    f.write('Lines 8 to 18: output files from SOLO with path relative to current directory\n')
    f.close()
    # seqsolo inf file
    f = open('solo/inf/seqsolo.inf','w')
    f.write(str(solo_info["nodes_target"])+'\n')
    f.write(str(0)+'\n')
    f.write(str(solo_info["learningrate"])+'\n')
    f.write(str(solo_info["iterations"])+'\n')
    f.write('solo/output/sofm_4.out'+'\n')
    f.write('solo/input/seqsolo_input.csv'+'\n')
    f.write('simulation'+'\n')
    f.write(str(9100)+'\n')
    f.write(str(0)+'\n')
    f.write('solo/output/eigenValue.out'+'\n')
    f.write('solo/output/eigenVector.out'+'\n')
    f.write('solo/output/trainWout.out'+'\n')
    f.write('solo/output/freqTable.out'+'\n')
    f.write('solo/output/errorMap.out'+'\n')
    f.write('solo/output/finResult.out'+'\n')
    f.write('solo/output/trainingRMSE.out'+'\n')
    f.write('solo/output/seqOut0.out'+'\n')
    f.write('solo/output/seqOut1.out'+'\n')
    f.write('solo/output/seqOut2.out'+'\n')
    f.write('solo/output/seqHidOutW.out'+'\n')
    f.write('solo/output/seqFreqMap.out'+'\n')
    f.write(str(c.missing_value)+'\n')
    f.write('### Comment lines ###\n')
    f.write('Line 1: No. of nodes - default is the number of drivers plus 1 (changeable via GUI if used)\n')
    f.write('Line 2: NdaFactor - not used by SEQSOLO, default value is 0\n')
    f.write('Line 3: learning rate - default value 0.01 (must be between 0.0 1nd 1.0, changeable via GUI if used)\n')
    f.write('Line 4: number of iterations for sequential training, default value is 500 (changeable via GUI if used)\n')
    f.write('Line 5: fourth output file from SOFM, used as input file by SEQSOLO\n')
    f.write('Line 6: input data filename with path relative to current directory\n')
    f.write('Line 7: type of run ("training" or "simulation", always "simulation" for SEQSOLO)\n')
    f.write('Line 8: seed for random number generator - default is 9100\n')
    f.write('Line 9: "calThreshold" - minimum number of data points for SOLO node to be used in simulation, default value is 0 (use all nodes)\n')
    f.write('Lines 10 to 21: output files from SEQSOLO with path relative to current directory\n')
    f.write('Line 22: missing data value, default value is c.missing_value.0\n')
    f.close()

# miscellaneous L4 routines
#def gf_getdiurnalstats(DecHour,Data,dt):
    #nInts = 24*int((60/dt)+0.5)
    #Hr = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    #Av = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    #Sd = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    #Mx = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    #Mn = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    #for i in range(nInts):
        #Hr[i] = float(i)*dt/60.
        #li = numpy.where((abs(DecHour-Hr[i])<c.eps)&(abs(Data-float(c.missing_value))>c.eps))
        #if numpy.size(li)!=0:
            #Av[i] = numpy.mean(Data[li])
            #Sd[i] = numpy.std(Data[li])
            #Mx[i] = numpy.max(Data[li])
            #Mn[i] = numpy.min(Data[li])
    #return Hr, Av, Sd, Mx, Mn

def gf_getdiurnalstats(DecHour,Data,ts):
    nInts = 24*int((60/ts)+0.5)
    Num = numpy.ma.zeros(nInts,dtype=int)
    Hr = numpy.ma.zeros(nInts,dtype=float)
    for i in range(nInts):
        Hr[i] = float(i)*ts/60.
    Av = numpy.ma.masked_all(nInts)
    Sd = numpy.ma.masked_all(nInts)
    Mx = numpy.ma.masked_all(nInts)
    Mn = numpy.ma.masked_all(nInts)
    if numpy.size(Data)!=0:
        for i in range(nInts):
            li = numpy.ma.where((abs(DecHour-Hr[i])<c.eps)&(abs(Data-float(c.missing_value))>c.eps))
            Num[i] = numpy.size(li)
            if Num[i]!=0:
                Av[i] = numpy.ma.mean(Data[li])
                Sd[i] = numpy.ma.std(Data[li])
                Mx[i] = numpy.ma.maximum(Data[li])
                Mn[i] = numpy.ma.minimum(Data[li])
    return Num, Hr, Av, Sd, Mx, Mn

def gf_getdateticks(start, end):
    from datetime import timedelta as td
    delta = end - start
    if delta <= td(minutes=10):
        loc = mdt.MinuteLocator()
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(minutes=30):
        loc = mdt.MinuteLocator(byminute=range(0,60,5))
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(hours=1):
        loc = mdt.MinuteLocator(byminute=range(0,60,15))
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(hours=6):
        loc = mdt.HourLocator()
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(days=1):
        loc = mdt.HourLocator(byhour=range(0,24,3))
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(days=3):
        loc = mdt.HourLocator(byhour=range(0,24,12))
        fmt = mdt.DateFormatter('%d/%m %H')
    elif delta <= td(weeks=2):
        loc = mdt.DayLocator()
        fmt = mdt.DateFormatter('%d/%m')
    elif delta <= td(weeks=12):
        loc = mdt.WeekdayLocator()
        fmt = mdt.DateFormatter('%d/%m')
    elif delta <= td(weeks=104):
        loc = mdt.MonthLocator()
        fmt = mdt.DateFormatter('%d/%m')
    elif delta <= td(weeks=208):
        loc = mdt.MonthLocator(interval=3)
        fmt = mdt.DateFormatter('%d/%m/%y')
    else:
        loc = mdt.MonthLocator(interval=6)
        fmt = mdt.DateFormatter('%d/%m/%y')
    return loc,fmt

def ImportSeries(cf,ds):
    # check to see if there is an Imports section
    if "Imports" not in cf.keys(): return
    # number of records
    nRecs = int(ds.globalattributes["nc_nrecs"])
    # get the start and end datetime
    ldt = ds.series["DateTime"]["Data"]
    start_date = ldt[0]
    end_date = ldt[-1]
    # loop over the series in the Imports section
    for label in cf["Imports"].keys():
        import_filename = pfp_utils.get_keyvaluefromcf(cf,["Imports",label],"file_name",default="")
        if import_filename=="":
            msg = " ImportSeries: import filename not found in control file, skipping ..."
            logger.warning(msg)
            continue
        var_name = pfp_utils.get_keyvaluefromcf(cf,["Imports",label],"var_name",default="")
        if var_name=="":
            msg = " ImportSeries: variable name not found in control file, skipping ..."
            logger.warning(msg)
            continue
        ds_import = pfp_io.nc_read_series(import_filename)
        ts_import = ds_import.globalattributes["time_step"]
        ldt_import = ds_import.series["DateTime"]["Data"]
        si = pfp_utils.GetDateIndex(ldt_import,str(start_date),ts=ts_import,default=0,match="exact")
        ei = pfp_utils.GetDateIndex(ldt_import,str(end_date),ts=ts_import,default=len(ldt_import)-1,match="exact")
        data = numpy.ma.ones(nRecs)*float(c.missing_value)
        flag = numpy.ma.ones(nRecs)
        data_import,flag_import,attr_import = pfp_utils.GetSeriesasMA(ds_import,var_name,si=si,ei=ei)
        ldt_import = ldt_import[si:ei+1]
        index = pfp_utils.FindIndicesOfBInA(ldt_import,ldt)
        data[index] = data_import
        flag[index] = flag_import
        pfp_utils.CreateSeries(ds,label,data,flag,attr_import)