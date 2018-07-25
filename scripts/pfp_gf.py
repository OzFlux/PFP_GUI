# standard modules
import ast
import datetime
import os
import logging
import sys
# 3rd party modules
import numpy
import matplotlib.dates as mdt
import xlrd
# PFP modules
import constants as c
import pfp_io
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

# GapFillParseControlFile parses the L4 control file
def GapFillParseControlFile(cf, ds, series, ds_alt):
    # find the section containing the series
    section = pfp_utils.get_cfsection(cf, series=series, mode="quiet")
    # return empty handed if the series is not in a section
    if len(section) == 0:
        return
    if "GapFillFromAlternate" in cf[section][series].keys():
        # create the alternate dictionary in ds
        gfalternate_createdict(cf, ds, series, ds_alt)
    if "GapFillUsingSOLO" in cf[section][series].keys():
        # create the SOLO dictionary in ds
        gfSOLO_createdict(cf, ds, series)
    if "GapFillUsingMDS" in cf[section][series].keys():
        # create the MDS dictionary in ds
        gfMDS_createdict(cf, ds, series)
    if "GapFillFromClimatology" in cf[section][series].keys():
        # create the climatology dictionary in the data structure
        gfClimatology_createdict(cf, ds, series)
    if "MergeSeries" in cf[section][series].keys():
        # create the merge series dictionary in the data structure
        gfMergeSeries_createdict(cf, ds, series)

def gfalternate_createdict(cf, ds, series, ds_alt):
    """
    Purpose:
     Creates a dictionary in ds to hold information about the alternate data used to gap fill the tower data.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf, series=series, mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("GapFillFromAlternate: Series %s not found in control file, skipping ...", series)
        return
    # create the alternate directory in the data structure
    if "alternate" not in dir(ds):
        ds.alternate = {}
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
                logger.info("gfAlternate: unrecognised fit option for series %s, used OLS", output)
        # correct for lag?
        if "lag" in cf[section][series]["GapFillFromAlternate"][output]:
            if cf[section][series]["GapFillFromAlternate"][output]["lag"].lower() in ["no","false"]:
                ds.alternate[output]["lag"] = "no"
            elif cf[section][series]["GapFillFromAlternate"][output]["lag"].lower() in ["yes","true"]:
                ds.alternate[output]["lag"] = "yes"
            else:
                logger.info("gfAlternate: unrecognised lag option for series %s", output)
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
    # get the start and end times of the tower and the alternate data and see if they overlap
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    start_alternate = ldt_alternate[0]
    ldt_tower = ds.series["DateTime"]["Data"]
    end_tower = ldt_tower[-1]
    # since the datetime is monotonically increasing we need only check the start datetime
    overlap = start_alternate<=end_tower
    # do the alternate and tower data overlap?
    if overlap:
        # index of alternate datetimes that are also in tower datetimes
        #alternate_index = pfp_utils.FindIndicesOfBInA(ldt_tower,ldt_alternate)
        #alternate_index = [pfp_utils.find_nearest_value(ldt_tower, dt) for dt in ldt_alternate]
        # index of tower datetimes that are also in alternate datetimes
        #tower_index = pfp_utils.FindIndicesOfBInA(ldt_alternate,ldt_tower)
        #tower_index = [pfp_utils.find_nearest_value(ldt_alternate, dt) for dt in ldt_tower]
        tower_index, alternate_index = pfp_utils.FindMatchingIndices(ldt_tower, ldt_alternate)
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
            if series in ["DateTime","DateTime_UTC"]:
                continue
            _,  _, attr = pfp_utils.GetSeriesasMA(ds_alternate, series)
            data = numpy.full(nRecs, c.missing_value, dtype=numpy.float64)
            flag = numpy.ones(nRecs, dtype=numpy.int32)
            pfp_utils.CreateSeries(ds_alternate, series, data, flag, attr)
    ds.returncodes["GapFillFromAlternate"] = "normal"

def gfClimatology_createdict(cf, ds, series):
    """ Creates a dictionary in ds to hold information about the climatological data used
        to gap fill the tower data."""
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf, series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section) == 0:
        logger.error("GapFillFromClimatology: Series %s not found in control file, skipping ...", series)
        return
    # create the climatology directory in the data structure
    if "climatology" not in dir(ds):
        ds.climatology = {}
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
            data, flag, attr = pfp_utils.MakeEmptySeries(ds, output)
            pfp_utils.CreateSeries(ds, output, data, flag, attr)

def gfMDS_createdict(cf, ds, series):
    """
    Purpose:
     Create an information dictionary for MDS gap filling from the contents
     of the control file.
    Usage:
     info["MDS"] = gfMDS_createdict(cf)
    Author: PRI
    Date: May 2018
    """
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf, series=series, mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("GapFillUsingMDS: Series %s not found in control file, skipping ...", series)
        return
    # create the MDS attribute (a dictionary) in ds, this will hold all MDS settings
    if "mds" not in dir(ds):
        ds.mds = {}
    # name of MDS output series in ds
    output_list = cf[section][series]["GapFillUsingMDS"].keys()
    # loop over the outputs listed in the control file
    for output in output_list:
        # create the dictionary keys for this series
        ds.mds[output] = {}
        # get the target
        if "target" in cf[section][series]["GapFillUsingMDS"][output]:
            ds.mds[output]["target"] = cf[section][series]["GapFillUsingMDS"][output]["target"]
        else:
            ds.mds[output]["target"] = series
        # site name
        ds.mds[output]["site_name"] = ds.globalattributes["site_name"]
        # list of SOLO settings
        if "mds_settings" in cf[section][series]["GapFillUsingMDS"][output]:
            mdss_list = ast.literal_eval(cf[section][series]["GapFillUsingMDS"][output]["mds_settings"])

        # list of drivers
        ds.mds[output]["drivers"] = ast.literal_eval(cf[section][series]["GapFillUsingMDS"][output]["drivers"])
        # list of tolerances
        ds.mds[output]["tolerances"] = ast.literal_eval(cf[section][series]["GapFillUsingMDS"][output]["tolerances"])
        # get the ustar filter option
        opt = pfp_utils.get_keyvaluefromcf(cf, [section, series, "GapFillUsingMDS", output], "turbulence_filter", default="")
        ds.mds[output]["turbulence_filter"] = opt
        # get the day/night filter option
        opt = pfp_utils.get_keyvaluefromcf(cf, [section, series, "GapFillUsingMDS", output], "daynight_filter", default="")
        ds.mds[output]["daynight_filter"] = opt

    # check that all requested targets and drivers have a mapping to
    # a FluxNet label, remove if they don't
    fluxnet_label_map = {"Fc":"NEE", "Fe":"LE", "Fh":"H",
                         "Fsd":"SW_IN", "Ta":"TA", "VPD":"VPD"}
    for mds_label in ds.mds:
        ds.mds[mds_label]["mds_label"] = mds_label
        pfp_target = ds.mds[mds_label]["target"]
        if pfp_target not in fluxnet_label_map:
            msg = " Target ("+pfp_target+") not supported for MDS gap filling"
            logger.warning(msg)
            del ds.mds[mds_label]
        else:
            ds.mds[mds_label]["target_mds"] = fluxnet_label_map[pfp_target]
        pfp_drivers = ds.mds[mds_label]["drivers"]
        for pfp_driver in pfp_drivers:
            if pfp_driver not in fluxnet_label_map:
                msg = "Driver ("+pfp_driver+") not supported for MDS gap filling"
                logger.warning(msg)
                ds.mds[mds_label]["drivers"].remove(pfp_driver)
            else:
                if "drivers_mds" not in ds.mds[mds_label]:
                    ds.mds[mds_label]["drivers_mds"] = []
                ds.mds[mds_label]["drivers_mds"].append(fluxnet_label_map[pfp_driver])
        if len(ds.mds[mds_label]["drivers"]) == 0:
            del ds.mds[mds_label]
    return

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

def gfSOLO_createdict(cf,ds,series):
    """ Creates a dictionary in ds to hold information about the SOLO data used
        to gap fill the tower data."""
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("GapFillUsingSOLO: Series %s not found in control file, skipping ...", series)
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

# functions for GapFillUsingMDS: not implemented yet
def GapFillFluxUsingMDS(cf, ds, series=""):
    section = pfp_utils.get_cfsection(cf, series=series, mode="quiet")
    if len(section)==0:
        return
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
            logger.error(" GapFillFromClimatology: Climatology file %s doesn't exist", cli_filename)
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
            logger.error(" GapFillFromClimatology: unrecognised method option for %s", label)
            continue
    if 'GapFillFromClimatology' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+', GapFillFromClimatology'
    # remove the "climatology" attribute from ds
    #del ds.climatology

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
    for ii in idx:
        try:
            jj = pfp_utils.find_nearest_value(cdt, ldt[ii])
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
    index = numpy.where(abs(ds.series[output]['Data']-c.missing_value)<c.eps)[0]
    ds.series[output]['Data'][index] = val1d[index]
    ds.series[output]['Flag'][index] = numpy.int32(40)

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

# miscellaneous L4 routines
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
