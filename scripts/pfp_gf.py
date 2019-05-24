# standard modules
import ast
import copy
import datetime
import os
import logging
import sys
# 3rd party modules
import dateutil
import numpy
import matplotlib.dates as mdt
import xlrd
# PFP modules
import constants as c
import pfp_cfg
import pfp_io
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

def CheckDrivers(l5_info, dsb, gf_type):
    """
    Purpose:
     Check the drivers specified for gap filling using SOLO and warn
     the user if any contain missing data.
    Usage:
    Side effects:
    Author: PRI
    Date: May 2019
    """
    msg = " Checking drivers for missing data"
    logger.info(msg)
    ts = int(dsb.globalattributes["time_step"])
    ldt = pfp_utils.GetVariable(dsb, "DateTime")
    gf_drivers = []
    if gf_type == "SOLO":
        for label in l5_info["solo"]["outputs"].keys():
            gf_drivers = gf_drivers + l5_info["solo"]["outputs"][label]["drivers"]
    elif gf_type == "FFNET":
        for label in l5_info["ffnet"]["outputs"].keys():
            gf_drivers = gf_drivers + l5_info["ffnet"]["outputs"][label]["drivers"]
    else:
        msg = "  Unrecognised gap fill type (" + gf_type + ")"
        logger.error(msg)
        return
    drivers = list(set(gf_drivers))
    drivers_with_missing = {}
    # loop over the drivers and check for missing data
    for label in drivers:
        var = pfp_utils.GetVariable(dsb, label)
        if numpy.ma.count_masked(var["Data"]) != 0:
            # save the number of missing data points and the datetimes when they occur
            idx = numpy.where(numpy.ma.getmaskarray(var["Data"]))[0]
            drivers_with_missing[label] = {"count": len(idx),
                                           "dates": ldt["Data"][idx],
                                           "end_date":[]}
    # check to see if any of the drivers have missing data
    if len(drivers_with_missing.keys()) == 0:
        msg = "  No missing data found in " + gf_type + " drivers"
        logger.info(msg)
        return
    # deal with drivers that contain missing data points
    logger.warning("!!!!!")
    s = ','.join(drivers_with_missing.keys())
    msg = "!!!!! The following variables contain missing data " + s
    logger.warning(msg)
    logger.warning("!!!!!")
    for label in drivers_with_missing.keys():
        var = pfp_utils.GetVariable(dsb, label)
        # check to see if this variable was imported
        if "end_date" in var["Attr"]:
            # it was, so perhaps this variable finishes before the tower data
            drivers_with_missing[label]["end_date"].append(dateutil.parser.parse(var["Attr"]["end_date"]))
    # check to see if any variables with missing data have an end date
    dwmwed = [l for l in drivers_with_missing.keys() if "end_date" in drivers_with_missing[l]]
    if len(dwmwed) == 0:
        # return with error message if no variables have end date
        s = ','.join(drivers_with_missing.keys())
        msg = "  Unable to resolve missing data in variables " + s
        logger.error(msg)
        dsb.returncodes["message"] = msg
        dsb.returncodes["value"] = 1
        return
    # check to see if the user wants us to truncate to an end date
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "TruncateToImports", default="Yes")
    if opt.lower() == "no":
        msg = "  Truncation to imported variable end date disabled in control file"
        logger.error(msg)
        dsb.returncodes["message"] = msg
        dsb.returncodes["value"] = 1
        return
    msg = "  Truncating data to end date of imported variable"
    logger.info(msg)
    dwmed = [drivers_with_missing[l]["end_date"] for l in drivers_with_missing.keys()]
    end_date = numpy.min(dwmed)
    ei = pfp_utils.GetDateIndex(ldt["Data"], end_date, ts=ts)
    # loop over the variables in the data structure
    for label in dsb.series.keys():
        var = pfp_utils.GetVariable(dsb, label, start=0, end=ei)
        pfp_utils.CreateVariable(dsb, var)
    # update the global attributes
    ldt = pfp_utils.GetVariable(dsb, "DateTime")
    dsb.globalattributes["nc_nrecs"] = len(ldt["Data"])
    dsb.globalattributes["end_date"] = ldt["Data"][-1].strftime("%Y-%m-%d %H:%M:%S")
    # ... and check again to see if any drivers have missing data
    drivers_with_missing = {}
    for label in drivers:
        var = pfp_utils.GetVariable(dsb, label)
        if numpy.ma.count_masked(var["Data"]) != 0:
            # save the number of missing data points and the datetimes when they occur
            idx = numpy.where(numpy.ma.getmaskarray(var["Data"]))[0]
            drivers_with_missing[label] = {"count": len(idx),
                                           "dates": ldt["Data"][idx],
                                           "end_date":[]}
    # check to see if any of the drivers still have missing data
    if len(drivers_with_missing.keys()) != 0:
        # return with error message if no variables have end date
        s = ','.join(drivers_with_missing.keys())
        msg = "  Unable to resolve missing data in variables " + s
        logger.error(msg)
        dsb.returncodes["message"] = msg
        dsb.returncodes["value"] = 1
        return
    else:
        # else we are all good, job done, so return
        msg = "  No missing data found in " + gf_type + " drivers"
        logger.info(msg)
        return

def ParseL4ControlFile(cf, ds):
    l4_info = {}
    l4_info["cf"] = copy.deepcopy(cf)
    for target in cf["Drivers"].keys():
        if "GapFillFromAlternate" in cf["Drivers"][target].keys():
            gfalternate_createdict(cf, ds, l4_info, target)
        if "GapFillFromClimatology" in cf["Drivers"][target].keys():
            gfClimatology_createdict(cf, ds, l4_info, target)
        if "MergeSeries" in cf["Drivers"][target].keys():
            gfMergeSeries_createdict(cf, ds, l4_info, target)
    return l4_info

def ParseL5ControlFile(cf, ds):
    l5_info = {}
    l5_info["cf"] = copy.deepcopy(cf)
    for target in cf["Fluxes"].keys():
        if "GapFillUsingSOLO" in cf["Fluxes"][target].keys():
            gfSOLO_createdict(cf, ds, l5_info, target)
        if "GapFillUsingMDS" in cf["Fluxes"][target].keys():
            gfMDS_createdict(cf, ds, l5_info, target)
        if "MergeSeries" in cf["Fluxes"][target].keys():
            gfMergeSeries_createdict(cf, ds, l5_info, target)
    return l5_info

def ReadAlternateFiles(ds, l4_info):
    #l4_info["alternate"]["outputs"]["Fn_era5"]["file_name"]
    ds_alt = {}
    l4ao = l4_info["alternate"]["outputs"]
    # get a list of file names
    files = [l4ao[output]["file_name"] for output in l4ao.keys()]
    # read the alternate files
    for f in files:
        # if the file has not already been read, do it now
        if f not in ds_alt:
            ds_alternate = pfp_io.nc_read_series(f, fixtimestepmethod="round")
            gfalternate_matchstartendtimes(ds, ds_alternate)
            ds_alt[f] = ds_alternate
    return ds_alt

def gfalternate_createdict(cf, ds, l4_info, label):
    """
    Purpose:
     Creates a dictionary in l4_info to hold information about the alternate data
     used to gap fill the tower data.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # create the alternate directory in the data structure
    if "alternate" not in l4_info.keys():
        l4_info["alternate"] = {"outputs": {}}
    # name of alternate output series in ds
    outputs = cf["Drivers"][label]["GapFillFromAlternate"].keys()
    # loop over the outputs listed in the control file
    l4ao = l4_info["alternate"]["outputs"]
    cfalt = cf["Drivers"][label]["GapFillFromAlternate"]
    for output in outputs:
        # create the dictionary keys for this output
        l4ao[output] = {}
        # get the target
        if "target" in cfalt[output]:
            l4ao[output]["target"] = cfalt[output]["target"]
        else:
            l4ao[output]["target"] = label
        # source name
        l4ao[output]["source"] = cfalt[output]["source"]
        ## site name
        #l4ao[output]["site_name"] = ds.globalattributes["site_name"]
        # alternate data file name
        # first, look in the [Files] section for a generic file name
        file_list = cf["Files"].keys()
        lower_file_list = [item.lower() for item in file_list]
        if l4ao[output]["source"].lower() in lower_file_list:
            # found a generic file name
            i = lower_file_list.index(l4ao[output]["source"].lower())
            l4ao[output]["file_name"] = cf["Files"][file_list[i]]
        else:
            # no generic file name found, look for a file name in the variable section
            l4ao[output]["file_name"] = cfalt[output]["file_name"]
        # get the type of fit
        l4ao[output]["fit_type"] = "OLS"
        if "fit" in cfalt[output]:
            if cfalt[output]["fit"].lower() in ["ols", "ols_thru0", "mrev", "replace", "rma", "odr"]:
                l4ao[output]["fit_type"] = cfalt[output]["fit"]
            else:
                logger.info("gfAlternate: unrecognised fit option for series %s, used OLS", output)
        # correct for lag?
        if "lag" in cfalt[output]:
            if cfalt[output]["lag"].lower() in ["no", "false"]:
                l4ao[output]["lag"] = "no"
            elif cfalt[output]["lag"].lower() in ["yes", "true"]:
                l4ao[output]["lag"] = "yes"
            else:
                logger.info("gfAlternate: unrecognised lag option for series %s", output)
        else:
            l4ao[output]["lag"] = "yes"
        # choose specific alternate variable?
        if "usevars" in cfalt[output]:
            l4ao[output]["usevars"] = ast.literal_eval(cfalt[output]["usevars"])
        # alternate data variable name if different from name used in control file
        if "alternate_name" in cfalt[output]:
            l4ao[output]["alternate_name"] = cfalt[output]["alternate_name"]
        else:
            l4ao[output]["alternate_name"] = output
        # results of best fit for plotting later on
        l4ao[output]["results"] = {"startdate":[], "enddate":[], "No. points":[], "No. filled":[],
                                   "r":[], "Bias":[], "RMSE":[], "Frac Bias":[], "NMSE":[],
                                   "Avg (Tower)":[], "Avg (Alt)":[],
                                   "Var (Tower)":[], "Var (Alt)":[], "Var ratio":[]}
        # create an empty series in ds if the alternate output series doesn't exist yet
        if output not in ds.series.keys():
            data, flag, attr = pfp_utils.MakeEmptySeries(ds, output)
            pfp_utils.CreateSeries(ds, output, data, flag, attr)
            pfp_utils.CreateSeries(ds, label + "_composite", data, flag, attr)

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

def gfClimatology_createdict(cf, ds, l4_info, label):
    """
    Purpose:
     Creates a dictionary in l4_info to hold information about the climatological data
     used to gap fill the tower data.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # create the climatology directory in the data structure
    if "climatology" not in l4_info.keys():
        l4_info["climatology"] = {"outputs": {}}
    # name of alternate output series in ds
    outputs = cf["Drivers"][label]["GapFillFromClimatology"].keys()
    # loop over the outputs listed in the control file
    l4co = l4_info["climatology"]["outputs"]
    cfcli = cf["Drivers"][label]["GapFillFromClimatology"]
    for output in outputs:
        # create the dictionary keys for this output
        l4co[output] = {}
        l4co[output]["target"] = label
        # Climatology file name
        file_list = cf["Files"].keys()
        lower_file_list = [item.lower() for item in file_list]
        # first, look in the [Files] section for a generic file name
        if "climatology" in lower_file_list:
            # found a generic file name
            i = lower_file_list.index("climatology")
            l4co[output]["file_name"] = cf["Files"][file_list[i]]
        else:
            # no generic file name found, look for a file name in the variable section
            l4co[output]["file_name"] = cfcli[output]["file_name"]
        # climatology variable name if different from name used in control file
        if "climatology_name" in cfcli[output]:
            l4co[output]["climatology_name"] = cfcli[output]["climatology_name"]
        else:
            l4co[output]["climatology_name"] = label
        # climatology gap filling method
        if "method" not in cfcli[output].keys():
            # default if "method" missing is "interpolated_daily"
            l4co[output]["method"] = "interpolated_daily"
        else:
            l4co[output]["method"] = cfcli[output]["method"]
        # create an empty series in ds if the climatology output series doesn't exist yet
        if output not in ds.series.keys():
            data, flag, attr = pfp_utils.MakeEmptySeries(ds, output)
            pfp_utils.CreateSeries(ds, output, data, flag, attr)

def gfMDS_createdict(cf, ds, l5_info, label):
    """
    Purpose:
     Create an information dictionary for MDS gap filling from the contents
     of the control file.
    Usage:
     gfMDS_createdict(cf, ds, l5_info, label)
    Author: PRI
    Date: May 2018
    """
    if "mds" not in l5_info:
        l5_info["mds"] = {"outputs": {}}
    # name of MDS output series in ds
    outputs = cf["Fluxes"][label]["GapFillUsingMDS"].keys()
    # loop over the outputs listed in the control file
    l5mo = l5_info["mds"]["outputs"]
    for output in outputs:
        # create the dictionary keys for this series
        l5mo[output] = {}
        # get the target
        if "target" in cf["Fluxes"][label]["GapFillUsingMDS"][output]:
            l5mo[output]["target"] = cf["Fluxes"][label]["GapFillUsingMDS"][output]["target"]
        else:
            l5mo[output]["target"] = label
        # list of MDS settings
        if "mds_settings" in cf["Fluxes"][label]["GapFillUsingMDS"][output]:
            mdss_string = cf["Fluxes"][label]["GapFillUsingMDS"][output]["mds_settings"]
            mdss_string = mdss_string.replace(" ","")
            if "," in mdss_string:
                l5mo[output]["mds_settings"] = mdss_string.split(",")
            else:
                l5mo[output]["mds_settings"] = [mdss_string]
        # list of drivers
        drivers_string = cf["Fluxes"][label]["GapFillUsingMDS"][output]["drivers"]
        drivers_string = drivers_string.replace(" ","")
        if "," in drivers_string:
            if len(drivers_string.split(",")) == 3:
                l5mo[output]["drivers"] = drivers_string.split(",")
            else:
                msg = " MDS: incorrect number of drivers for " + label + ", skipping ..."
                logger.error(msg)
                continue
        else:
            msg = " MDS: incorrect number of drivers for " + label + ", skipping ..."
            logger.error(msg)
            continue
        # list of tolerances
        tolerances_string = cf["Fluxes"][label]["GapFillUsingMDS"][output]["tolerances"]
        tolerances_string = tolerances_string.replace(" ","")
        tolerances_string = tolerances_string.replace("(","").replace(")","")
        if "," in tolerances_string:
            if len(tolerances_string.split(",")) == 4:
                parts = tolerances_string.split(",")
                l5mo[output]["tolerances"] = [(parts[0], parts[1]), parts[2], parts[3]]
            else:
                msg = " MDS: incorrect format for tolerances for " + label + ", skipping ..."
                logger.error(msg)
                continue
        else:
            msg = " MDS: incorrect format for tolerances for " + label + ", skipping ..."
            logger.error(msg)
            continue
    # check that all requested targets and drivers have a mapping to
    # a FluxNet label, remove if they don't
    fluxnet_label_map = {"Fc":"NEE", "Fe":"LE", "Fh":"H",
                         "Fsd":"SW_IN", "Ta":"TA", "VPD":"VPD"}
    for mds_label in l5_info["mds"]["outputs"]:
        l5_info["mds"]["outputs"][mds_label]["mds_label"] = mds_label
        pfp_target = l5_info["mds"]["outputs"][mds_label]["target"]
        if pfp_target not in fluxnet_label_map:
            msg = " Target ("+pfp_target+") not supported for MDS gap filling"
            logger.warning(msg)
            del l5_info["mds"]["outputs"][mds_label]
        else:
            l5_info["mds"]["outputs"][mds_label]["target_mds"] = fluxnet_label_map[pfp_target]
        pfp_drivers = l5_info["mds"]["outputs"][mds_label]["drivers"]
        for pfp_driver in pfp_drivers:
            if pfp_driver not in fluxnet_label_map:
                msg = "Driver ("+pfp_driver+") not supported for MDS gap filling"
                logger.warning(msg)
                l5_info["mds"]["outputs"][mds_label]["drivers"].remove(pfp_driver)
            else:
                if "drivers_mds" not in l5_info["mds"]["outputs"][mds_label]:
                    l5_info["mds"]["outputs"][mds_label]["drivers_mds"] = []
                l5_info["mds"]["outputs"][mds_label]["drivers_mds"].append(fluxnet_label_map[pfp_driver])
        if len(l5_info["mds"]["outputs"][mds_label]["drivers"]) == 0:
            del l5_info["mds"]["outputs"][mds_label]
    return

def gfMergeSeries_createdict(cf, ds, info, label):
    """ Creates a dictionary in ds to hold information about the merging of gap filled
        and tower data."""
    merge_prereq_list = ["Fsd","Fsu","Fld","Flu","Ts","Sws"]
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=label,mode="quiet")
    # create the merge directory in the data structure
    if "merge" not in info:
        info["merge"] = {}
    # check to see if this series is in the "merge first" list
    # series in the "merge first" list get merged first so they can be used with existing tower
    # data to re-calculate Fg, Fn and Fa
    merge_order = "standard"
    if label in merge_prereq_list:
        merge_order = "prerequisite"
    if merge_order not in info["merge"].keys():
        info["merge"][merge_order] = {}
    # create the dictionary keys for this series
    info["merge"][merge_order][label] = {}
    # output series name
    info["merge"][merge_order][label]["output"] = label
    # merge source list
    src_string = cf[section][label]["MergeSeries"]["Source"]
    if "," in src_string:
        src_list = src_string.split(",")
    else:
        src_list = [src_string]
    info["merge"][merge_order][label]["source"] = src_list
    # create an empty series in ds if the output series doesn't exist yet
    if label not in ds.series.keys():
        data, flag, attr = pfp_utils.MakeEmptySeries(ds, label)
        pfp_utils.CreateSeries(ds, label, data, flag, attr)

def gfSOLO_createdict(cf, ds, l5_info, label):
    """
    Purpose:
     Creates a dictionary in l5_info to hold information about the SOLO data
     used to gap fill the tower data.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # create the solo settings directory
    if "solo" not in l5_info:
        l5_info["solo"] = {"outputs": {}}
    # name of SOLO output series in ds
    outputs = cf["Fluxes"][label]["GapFillUsingSOLO"].keys()
    # loop over the outputs listed in the control file
    l5so = l5_info["solo"]["outputs"]
    for output in outputs:
        # create the dictionary keys for this series
        l5so[output] = {}
        # get the target
        if "target" in cf["Fluxes"][label]["GapFillUsingSOLO"][output]:
            l5so[output]["target"] = cf["Fluxes"][label]["GapFillUsingSOLO"][output]["target"]
        else:
            l5so[output]["target"] = label
        # list of SOLO settings
        if "solo_settings" in cf["Fluxes"][label]["GapFillUsingSOLO"][output]:
            src_string = cf["Fluxes"][label]["GapFillUsingSOLO"][output]["solo_settings"]
            src_list = src_string.split(",")
            l5so[output]["solo_settings"] = {}
            l5so[output]["solo_settings"]["nodes_target"] = int(src_list[0])
            l5so[output]["solo_settings"]["training"] = int(src_list[1])
            l5so[output]["solo_settings"]["nda_factor"] = int(src_list[2])
            l5so[output]["solo_settings"]["learning_rate"] = float(src_list[3])
            l5so[output]["solo_settings"]["iterations"] = int(src_list[4])
        # list of drivers
        drivers_string = cf["Fluxes"][label]["GapFillUsingSOLO"][output]["drivers"]
        l5so[output]["drivers"] = pfp_cfg.cfg_string_to_list(drivers_string)
        # results of best fit for plotting later on
        l5so[output]["results"] = {"startdate":[],"enddate":[],"No. points":[],"r":[],
                                   "Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                                   "Avg (obs)":[],"Avg (SOLO)":[],
                                   "Var (obs)":[],"Var (SOLO)":[],"Var ratio":[],
                                   "m_ols":[],"b_ols":[]}
        # create an empty series in ds if the SOLO output series doesn't exist yet
        if output not in ds.series.keys():
            nrecs = int(ds.globalattributes["nc_nrecs"])
            variable = pfp_utils.CreateEmptyVariable(output, nrecs)
            pfp_utils.CreateVariable(ds, variable)

# functions for GapFillUsingMDS: not implemented yet
def GapFillFluxUsingMDS(cf, ds, series=""):
    section = pfp_utils.get_cfsection(cf, series=series, mode="quiet")
    if len(section)==0:
        return
    if "GapFillFluxUsingMDS" in cf[section][series].keys():
        logger.info(" GapFillFluxUsingMDS: not implemented yet")
        return

# functions for GapFillFromClimatology
def GapFillFromClimatology(ds, l4_info):
    '''
    Gap fill missing data using data from the climatology spreadsheet produced by
    the climatology.py script.
    '''
    if "climatology" not in l4_info.keys():
        return
    l4co = l4_info["climatology"]["outputs"]
    # tell the user what we are going to do
    msg = " Reading climatology file and creating climatology series"
    logger.info(msg)
    # loop over the series to be gap filled using climatology
    cli_xlbooks = {}
    for output in l4co.keys():
        # check to see if there are any gaps in "series"
        #index = numpy.where(abs(ds.series[label]['Data']-float(c.missing_value))<c.eps)[0]
        #if len(index)==0: continue                      # no gaps found in "series"
        cli_filename = l4co[output]["file_name"]
        if not os.path.exists(cli_filename):
            logger.error(" GapFillFromClimatology: Climatology file %s doesn't exist", cli_filename)
            continue
        if cli_filename not in cli_xlbooks:
            cli_xlbooks[cli_filename] = xlrd.open_workbook(cli_filename)
        # local pointers to the series name and climatology method
        label = l4co[output]["target"]
        method = l4co[output]["method"]
        # do the gap filling
        cli_xlbook = cli_xlbooks[cli_filename]
        # choose the gap filling method
        if method == "interpolated daily":
            gfClimatology_interpolateddaily(ds, label, output, cli_xlbook)
        else:
            logger.error(" GapFillFromClimatology: unrecognised method option for %s", label)
            continue

def gfClimatology_interpolateddaily(ds, series, output, xlbook):
    """
    Gap fill using data interpolated over a 2D array where the days are
    the rows and the time of day is the columns.
    """
    # gap fill from interpolated 30 minute data
    sheet_name = series + 'i(day)'
    if sheet_name not in xlbook.sheet_names():
        msg = " gfClimatology: sheet " + sheet_name + " not found, skipping ..."
        logger.warning(msg)
        return
    ldt = ds.series["DateTime"]["Data"]
    thissheet = xlbook.sheet_by_name(sheet_name)
    datemode = xlbook.datemode
    basedate = datetime.datetime(1899, 12, 30)
    nts = thissheet.ncols - 1
    ndays = thissheet.nrows - 2
    # read the time stamp values from the climatology worksheet
    tsteps = thissheet.row_values(1, start_colx=1, end_colx=nts+1)
    # read the data from the climatology workbook
    val1d = numpy.ma.zeros(ndays*nts, dtype=numpy.float64)
    # initialise an array for the datetime of the climatological values
    cdt = [None]*nts*ndays
    # loop over the rows (days) of data
    for xlRow in range(ndays):
        # get the Excel datetime value
        xldatenumber = int(thissheet.cell_value(xlRow+2, 0))
        # convert this to a Python Datetime
        xldatetime = basedate + datetime.timedelta(days=xldatenumber + 1462*datemode)
        # fill the climatology datetime array
        cdt[xlRow*nts:(xlRow+1)*nts] = [xldatetime+datetime.timedelta(hours=hh) for hh in tsteps]
        # fill the climatological value array
        val1d[xlRow*nts:(xlRow+1)*nts] = thissheet.row_values(xlRow+2, start_colx=1, end_colx=nts+1)
    # get the data to be filled with climatological values
    data, flag, attr = pfp_utils.GetSeriesasMA(ds, series)
    # get an index of missing values
    idx = numpy.where(numpy.ma.getmaskarray(data) == True)[0]
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
    pfp_utils.CreateSeries(ds, output, data, flag, attr)

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
def GapFillUsingInterpolation(cf, ds):
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
    ts = int(ds.globalattributes["time_step"])
    # get list of variables from control file
    label_list = pfp_utils.get_label_list_from_cf(cf)
    # get the maximum gap length to be filled by interpolation
    max_length_hours = int(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "MaxGapInterpolate", default=3))
    # bug out if interpolation disabled in control file
    if max_length_hours == 0:
        msg = " Gap fill by interpolation disabled in control file"
        logger.info(msg)
        return
    # get the interpolation type
    int_type = str(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "InterpolateType", default="Akima"))
    # tell the user what we are doing
    msg = " Using " + int_type +" interpolation (max. gap = " + str(max_length_hours) +" hours)"
    logger.info(msg)
    # do the business
    # convert from max. gap length in hours to number of time steps
    max_length_points = int((max_length_hours*float(60)/float(ts))+0.5)
    for label in label_list:
        pfp_ts.InterpolateOverMissing(ds, series=label, maxlen=max_length_points, int_type=int_type)

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
    if "Imports" not in cf.keys():
        return
    # number of records
    nRecs = int(ds.globalattributes["nc_nrecs"])
    # get the start and end datetime
    ldt = ds.series["DateTime"]["Data"]
    start_date = ldt[0]
    end_date = ldt[-1]
    # loop over the series in the Imports section
    for label in cf["Imports"].keys():
        import_filename = pfp_utils.get_keyvaluefromcf(cf, ["Imports", label], "file_name", default="")
        if import_filename == "":
            msg = " ImportSeries: import filename not found in control file, skipping ..."
            logger.warning(msg)
            continue
        var_name = pfp_utils.get_keyvaluefromcf(cf, ["Imports", label], "var_name", default="")
        if var_name == "":
            msg = " ImportSeries: variable name not found in control file, skipping ..."
            logger.warning(msg)
            continue
        ds_import = pfp_io.nc_read_series(import_filename)
        ts_import = ds_import.globalattributes["time_step"]
        ldt_import = ds_import.series["DateTime"]["Data"]
        si = pfp_utils.GetDateIndex(ldt_import, str(start_date), ts=ts_import, default=0, match="exact")
        ei = pfp_utils.GetDateIndex(ldt_import, str(end_date), ts=ts_import, default=len(ldt_import)-1, match="exact")
        data = numpy.ma.ones(nRecs)*float(c.missing_value)
        flag = numpy.ma.ones(nRecs)
        data_import, flag_import, attr_import = pfp_utils.GetSeriesasMA(ds_import, var_name, si=si, ei=ei)
        attr_import["start_date"] = ldt_import[0].strftime("%Y-%m-%d %H:%M")
        attr_import["end_date"] = ldt_import[-1].strftime("%Y-%m-%d %H:%M")
        ldt_import = ldt_import[si:ei+1]
        #index = pfp_utils.FindIndicesOfBInA(ldt_import,ldt)
        indainb, indbina = pfp_utils.FindMatchingIndices(ldt_import, ldt)
        data[indbina] = data_import[indainb]
        flag[indbina] = flag_import[indainb]
        pfp_utils.CreateSeries(ds, label, data, flag, attr_import)
