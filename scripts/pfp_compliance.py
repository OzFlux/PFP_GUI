# standard modules
import copy
import datetime
import logging
import ntpath
import os
import platform
import time
import traceback
# 3rd party modules
import numpy
from PyQt5 import QtWidgets
import scipy.stats
import timezonefinder
import xlrd
# PFP modules
import constants as c
import pfp_cfg
import pfp_gui
import pfp_io
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

def change_variable_names(cfg, ds):
    """
    Purpose:
     Change variable names to the new (October 2018) scheme.
    Usage:
    Author: PRI
    Date: October 2018
    """
    # get a list of potential mappings
    rename_list = [v for v in list(cfg["rename"].keys())]
    # loop over the variables in the data structure
    series_list = list(ds.series.keys())
    for label in series_list:
        if label in rename_list:
            new_name = cfg["rename"][label]["rename"]
            ds.series[new_name] = ds.series.pop(label)
    return

def CheckExcelWorkbook(l1_info):
    """
    Purpose:
     Check that the requested sheets and variables are in the Excel workbook.
    Usage:
    Side effects:
    Author: PRI
    Date: February 2020
    """
    l1ire = l1_info["read_excel"]
    # get the labels of variables in the netCDF file
    # need to add check for duplicate variables on multiple sheets
    nc_labels = list(l1ire["Variables"].keys())
    l1ire["xl_sheets"] = {}
    # check the requested sheets are present and get a list of variables for each sheet
    msg = " Reading Excel workbook " + os.path.basename(l1ire["Files"]["file_name"])
    logger.info(msg)
    xl_book = xlrd.open_workbook(l1ire["Files"]["file_name"], on_demand=True)
    # put the Excel workbook datemode into the global attributes
    l1ire["Global"]["xl_datemode"] = str(xl_book.datemode)
    xl_sheets_present = xl_book.sheet_names()
    for nc_label in nc_labels:
        xl_sheet = l1ire["Variables"][nc_label]["xl"]["sheet"]
        xl_label = l1ire["Variables"][nc_label]["xl"]["name"]
        #print xl_sheet, xl_label, nc_label
        if xl_sheet not in xl_sheets_present:
            msg = " Sheet " + xl_sheet + " (" + xl_label + ") not found in workbook, skipping ..."
            logger.warning(msg)
            del l1ire["Variables"][nc_label]
            continue
        if xl_sheet not in list(l1ire["xl_sheets"].keys()):
            l1ire["xl_sheets"][xl_sheet] = {}
        l1ire["xl_sheets"][xl_sheet][xl_label] = nc_label
    # check the requested variables are on the specified sheets
    xl_data = {}
    for xl_sheet in list(l1ire["xl_sheets"].keys()):
        xl_data[xl_sheet] = xl_book.sheet_by_name(xl_sheet)
        headers = xl_data[xl_sheet].row_values(l1ire["Files"]["in_headerrow"])
        for xl_label in list(l1ire["xl_sheets"][xl_sheet].keys()):
            if xl_label not in headers:
                msg = " Variable " + xl_label + " not found on sheet " + xl_sheet + ", skipping ..."
                logger.warning(msg)
                del l1ire["xl_sheets"][xl_sheet][xl_label]
    # now we know what variables on which sheets have been requested and are present
    # find the timestamp label for each sheet
    fdr = int(l1ire["Files"]["in_firstdatarow"])
    for xl_sheet in list(l1ire["xl_sheets"].keys()):
        got_timestamp = False
        ldr = int(xl_data[xl_sheet].nrows)
        xl_labels = xl_data[xl_sheet].row_values(l1ire["Files"]["in_headerrow"])
        for xl_label in xl_labels:
            col = xl_labels.index(xl_label)
            types = numpy.array(xl_data[xl_sheet].col_types(col)[fdr:ldr])
            mode = scipy.stats.mode(types)
            #print xl_sheet, xl_label, col, mode[0][0], fdr, ldr
            if mode[0][0] == 3 and 100*mode[1][0]/len(types) > 75:
                got_timestamp = True
                #print " Time stamp is " + xl_label + " for sheet " + xl_sheet
                if xl_label not in l1ire["xl_sheets"][xl_sheet]:
                    l1ire["xl_sheets"][xl_sheet][xl_label] = "DateTime"
                break
        if not got_timestamp:
            msg = " Time stamp not found for sheet " + xl_sheet +", skipping ..."
            logger.warning(msg)
            del l1ire["xl_sheets"][xl_sheet]

    return xl_data

def check_executables():
    # check for the executable files required
    if platform.system() == "Windows":
        executable_extension = ".exe"
    else:
        executable_extension = ""
    executable_names = ["solo/bin/sofm", "solo/bin/solo", "solo/bin/seqsolo",
                        "mds/bin/gf_mds", "mpt/bin/ustar_mp"]
    missing_executable = False
    for executable_name in executable_names:
        executable_name = executable_name + executable_extension
        if not os.path.isfile(executable_name):
            missing_executable = True
    if missing_executable:
        msg = "One or more of the required executable files could not be found.\n"
        msg = msg + "If you are running on Windows, clone the repository again.\n"
        msg = msg + "If you are running on OSX or Linux, use the make_nix script\n"
        msg = msg + "to compile the executables."
        result = pfp_gui.MsgBox_Quit(msg, title="Critical")
    return

def check_status_ok(ds, info):
    if info["status"]["value"] != 0:
        ds.returncodes["value"] = info["status"]["value"]
        ds.returncodes["message"] = info["status"]["message"]
        logger.error(info["status"]["message"])
        return False
    else:
        return True

def concatenate_update_controlfile(cfg):
    """
    Purpose:
     Parse the concatenate control file to update the syntax from earlier OFQC/PFP
     versions to the syntax used by this version.
    Usage:
     result = pfp_compliance.concatenate_update_controlfile(cfg)
     where cfg is a ConfigObj object
           result is True if the concatenate control file was updated successfully
                     False if it couldn't be updated
    Side effects:
    Author: PRI
    Date: February 2020
    """
    # copy the control file
    cfg_original = copy.deepcopy(cfg)
    # initialise the return logical
    ok = True
    try:
        strip_list = ['"', "'", "[", "]"]
        for key1 in cfg:
            if key1 in ["level"]:
                cfg[key1] = parse_cfg_values(key1, cfg[key1], strip_list)
            elif key1 in ["Options"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    if key2 in ["MaxGapInterpolate"]:
                        cfg2 = parse_cfg_values(key2, cfg2, strip_list)
                    else:
                        del cfg[key1][key2]
            elif key1 in ["Files"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    for key3 in cfg2:
                        cfg3 = cfg[key1][key2][key3]
                        cfg3 = parse_cfg_values(key3, cfg3, strip_list)
            else:
                del cfg[key1]
        # check to see if the control file object has been changed
        if cfg != cfg_original:
            # and save it if it has changed
            file_name = os.path.basename(cfg.filename)
            logger.info(" Updated and saved control file " + file_name)
            cfg.write()
    except Exception:
        ok = False
        msg = " An error occurred while updating the concatenate control file syntax"
        logger.error(msg)
        error_message = traceback.format_exc()
        logger.error(error_message)
    return ok

def consistent_Fc_storage(ds, file_name):
    """
    Purpose:
     Make the various incarnations of single point Fc storage consistent.
    Author: PRI
    Date: November 2019
    """
    # save Fc_single if it exists - debug only
    labels = ds.series.keys()
    if "Fc_single" in labels:
        variable = pfp_utils.GetVariable(ds, "Fc_single")
        variable["Label"] = "Fc_sinorg"
        pfp_utils.CreateVariable(ds, variable)
        pfp_utils.DeleteVariable(ds, "Fc_single")
    # do nothing if Fc_single exists
    labels = ds.series.keys()
    if "Fc_single" in labels:
        pass
    # Fc_single may be called Fc_storage
    elif "Fc_storage" in labels:
        level = ds.globalattributes["nc_level"]
        descr = "description_" + level
        variable = pfp_utils.GetVariable(ds, "Fc_storage")
        if "using single point CO2 measurement" in variable["Attr"][descr]:
            variable["Label"] = "Fc_single"
            pfp_utils.CreateVariable(ds, variable)
            pfp_utils.DeleteVariable(ds, "Fc_storage")
    else:
        # neither Fc_single nor Fc_storage exist, try to calculate
        # check to see if the measurement height is defined
        CO2 = pfp_utils.GetVariable(ds, "CO2")
        zms = pfp_utils.get_number_from_heightstring(CO2["Attr"]["height"])
        if zms == None:
            while zms == None:
                text, ok = QtWidgets.QInputDialog.getText(None, file_name,
                                                          "Enter CO2 measuement height in metres",
                                                          QtWidgets.QLineEdit.Normal,"")
                zms = pfp_utils.get_number_from_heightstring(text)
        # update the CO2 variable attribute
        CO2["Attr"]["height"] = zms
        pfp_utils.CreateVariable(ds, CO2)
        # calculate single point Fc storage term
        cf = {"Options": {"zms": zms}}
        pfp_ts.CalculateFcStorageSinglePoint(cf, ds)
        # convert Fc_single from mg/m2/s to umol/m2/s
        pfp_utils.CheckUnits(ds, "Fc_single", "umol/m2/s", convert_units=True)
    return

def copy_ws_wd(ds):
    """
    Purpose:
     Make sure the Ws and Wd variables are in the L3 netCDF files.
    Usage:
    Author: PRI
    Date: October 2018
    """
    # get a list of the series
    series_list = sorted(list(ds.series.keys()))
    if "Wd" not in series_list:
        if "Wd_SONIC_Av" in series_list:
            ds.series["Wd"] = copy.deepcopy(ds.series["Wd_SONIC_Av"])
            ds.series["Wd"]["Attr"]["long_name"] = "Wind direction (copied from Wd_SONIC_Av)"
    if "Ws" not in series_list:
        if "Ws_SONIC_Av" in series_list:
            ds.series["Ws"] = copy.deepcopy(ds.series["Ws_SONIC_Av"])
            ds.series["Ws"]["Attr"]["long_name"] = "Wind speed (copied from Ws_SONIC_Av)"
    return

def ParseConcatenateControlFile(cf):
    """
    Purpose:
     Make the concatenate information dictionary
    Usage:
    Side effects:
    Author: PRI
    Date: August 2019
    """
    info = {}
    info["NetCDFConcatenate"] = {"OK": True}
    inc = info["NetCDFConcatenate"]
    # check the control file has a Files section
    if "Files" not in cf:
        msg = " Files section missing from control file"
        logger.error(msg)
        inc["OK"] = False
        return info
    # check the [Files] section contains an [Out] section and an [In] section
    for item in ["Out", "In"]:
        if item not in cf["Files"]:
            msg = " " + item + " subsection missing from Files section"
            logger.error(msg)
            inc["OK"] = False
            return info
    # check the [In] section contains at least 1 entry
    if len(cf["Files"]["In"].keys()) < 2:
        msg = " Less than 2 input files specified"
        logger.error(msg)
        inc["OK"] = False
        return info
    # get a list of the input file names
    inc["in_file_names"] = []
    for key in sorted(list(cf["Files"]["In"].keys())):
        file_name = cf["Files"]["In"][key]
        if os.path.isfile(file_name):
            inc["in_file_names"].append(file_name)
        else:
            msg = " File not found (" + ntpath.basename(file_name) + ")"
            logger.warning(msg)
    # get the output file name
    if "ncFileName" not in cf["Files"]["Out"]:
        msg = " No ncFileName key in Out subsection of Files section"
        logger.error(msg)
        inc["OK"] = False
        return info
    inc["out_file_name"] = cf["Files"]["Out"]["ncFileName"]
    # check the output path exists, create if it doesn't
    file_path, file_name = os.path.split(inc["out_file_name"])
    if not os.path.isdir(file_path):
        os.makedirs(file_path)
    # work through the choices in the [Options] section
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "NumberOfDimensions", default=3)
    inc["NumberOfDimensions"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "MaxGapInterpolate", default=0)
    inc["MaxGapInterpolate"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "FixTimeStepMethod", default="round")
    inc["FixTimeStepMethod"] = str(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "Truncate", default="Yes")
    inc["Truncate"] = str(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "TruncateThreshold", default=50)
    inc["TruncateThreshold"] = float(opt)
    s = "Ah,CO2,Fa,Fg,Fld,Flu,Fn,Fsd,Fsu,ps,Sws,Ta,Ts,Ws,Wd,Precip"
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "SeriesToCheck", default=s)
    inc["SeriesToCheck"] = pfp_utils.csv_string_to_list(s)
    # now add the bits and pieces
    inc["start_date"] = []
    inc["end_date"] = []
    inc["chrono_files"] = []
    inc["labels"] = []
    inc["attributes"] = ["height", "instrument", "long_name", "serial_number",
                         "standard_name", "units", "valid_range"]
    # add key for updating netCDF files
    stdname = os.path.join("controlfiles", "standard", "nc_cleanup.txt")
    info["NetCDFUpdate"] = pfp_io.get_controlfilecontents(stdname)
    # add key for suppressing output of intermediate variables e.g. Cpd etc
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "KeepIntermediateSeries", default="No")
    info["RemoveIntermediateSeries"] = {"KeepIntermediateSeries": opt, "not_output": []}
    return info

def ParseL1ControlFile(cf):
    """
    Purpose:
     Check the contents of the Li control file.
     If the L1 control file contents are OK, return with the required information.
     If the L1 control file contents are not OK, return with an error message.
    """
    logger.info(" Parsing the L1 control file")
    # create the settings dictionary
    l1_info = {"status": {"value": 0, "message": "OK"},
              "read_excel": {}}
    l1ire = l1_info["read_excel"]
    # check we have an L1 control file
    if "level" not in cf:
        error_handler(l1_info, "Key 'level' not found in control file", 1)
        return l1_info
    if cf["level"] != "L1":
        error_handler(l1_info, "Not an L1 control file", 1)
        return l1_info
    # check the expected sections are in the control file
    for item in ["Files", "Global", "Variables"]:
        if item not in list(cf.keys()):
            msg = "Section '" + item + "' not in control file"
            error_handler(l1_info, msg, 1)
            return l1_info
    # copy the files section from the control file
    l1ire["Files"] = copy.deepcopy(cf["Files"])
    # get the input file and check it exists
    xl_file_name = pfp_io.get_infilenamefromcf(cf)
    if not os.path.isfile(xl_file_name):
        msg = "Input file not found: " + xl_file_name
        error_handler(l1_info, msg, 1)
        return l1_info
    l1ire["Files"]["file_name"] = xl_file_name
    # get the header row
    try:
        opt = pfp_utils.get_keyvaluefromcf(cf, ["Files"], "in_headerrow", default=2)
        l1ire["Files"]["in_headerrow"] = int(opt) - 1
    except ValueError:
        error_handler(l1_info, "in_headerrow is not a number", 1)
        return l1_info
    # get the first data row
    try:
        opt = pfp_utils.get_keyvaluefromcf(cf, ["Files"], "in_firstdatarow", default=5)
        l1ire["Files"]["in_firstdatarow"] = int(opt) - 1
    except ValueError:
        error_handler(l1_info, "in_firstdatarow is not a number", 1)
        return l1_info
    # get the global attributes
    l1ire["Global"] = copy.deepcopy(cf["Global"])
    # check time step is present and makes sense
    try:
        ts = int(l1ire["Global"]["time_step"])
    except ValueError:
        error_handler(l1_info, "Global attribute 'time_step' is not a number", 1)
        return l1_info
    if ts not in [15, 20, 30, 60]:
        msg = "Global attribute 'time_step' must be 15, 20, 30 or 60"
        error_handler(l1_info, msg, 1)
        return l1_info
    # check latitude and longitude are present and make sense
    try:
        lat = float(l1ire["Global"]["latitude"])
    except ValueError:
        error_handler(l1_info, "Global attribute 'latitude' is not a number", 1)
        return l1_info
    if lat < -90.0 or lat > 90.0:
        msg = "Global attribute 'latitude' must be between -90 and 90"
        error_handler(l1_info, msg, 1)
        return l1_info
    try:
        lon = float(l1ire["Global"]["longitude"])
    except ValueError:
        error_handler(l1_info, "Global attribute 'longitude' is not a number", 1)
        return l1_info
    if lat < -180.0 or lat > 180.0:
        msg = "Global attribute 'longitude' must be between -180 and 180"
        error_handler(l1_info, msg, 1)
        return l1_info
    # check the time zone
    try:
        tf = timezonefinder.TimezoneFinder()
        tz_from_lat_lon = tf.timezone_at(lng=lon, lat=lat)
        opt = pfp_utils.get_keyvaluefromcf(l1ire, ["Global"], "time_zone", default=tz_from_lat_lon)
        if opt.lower() != tz_from_lat_lon.lower():
            msg = "Global attribute 'time_zone' inconsistent with latitude and longitude"
            error_handler(l1_info, msg, 1)
            return l1_info
        l1ire["Global"]["time_zone"] = opt
    except:
        error_handler(l1_info, "Error checking global attribute 'time_zone'", 1)
        return l1_info
    # get the variables
    l1ire["Variables"] = copy.deepcopy(cf["Variables"])
    # checks of the 'Variables' sections would go here
    for label in list(l1ire["Variables"].keys()):
        # check the 'xl' and 'Attr' subsections are present
        ok = True
        for item in ["xl", "Attr"]:
            if item not in list(l1ire["Variables"][label].keys()):
                msg = " Skipping " + label + " (subsection '" + item + "' not found)"
                logger.warning(msg)
                ok = False
        if not ok:
            del l1ire["Variables"][label]
            continue
        # check 'sheet' and 'name' are in the 'xl' subsection
        ok = True
        for item in ["sheet", "name"]:
            if item not in list(l1ire["Variables"][label]["xl"].keys()):
                msg = " Skipping " + label + " (subsection '" + item + "' not found)"
                logger.warning(msg)
                ok = False
        if not ok:
            del l1ire["Variables"][label]
            continue
        # check the 'Attr' subsection
        ok = True
        for item in ["long_name", "units"]:
            if item not in list(l1ire["Variables"][label]["Attr"].keys()):
                msg = " Skipping " + label + " (subsection '" + item + "' not found)"
                logger.warning(msg)
                ok = False
        if not ok:
            del l1ire["Variables"][label]
            continue
    return l1_info

def ParseL3ControlFile(cf, ds):
    """
    Purpose:
     Parse the L3 control file and return contents in the l3_info dictionary.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2019
    """
    ds.returncodes["message"] = "OK"
    ds.returncodes["value"] = 0
    l3_info = {}
    # add key for suppressing output of intermediate variables e.g. Cpd etc
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "KeepIntermediateSeries", default="No")
    l3_info["RemoveIntermediateSeries"] = {"KeepIntermediateSeries": opt, "not_output": []}
    return l3_info

#def ParseL6ControlFile(cf, ds):
    #"""
    #Purpose:
     #Parse the L6 control file.
    #Usage:
    #Side effects:
    #Author: PRI
    #Date: Back in the day
    #"""
    ## create the L6 information dictionary
    #l6_info = {}
    ## add key for suppressing output of intermediate variables e.g. Ta_aws
    #opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "KeepIntermediateSeries", default="No")
    #l6_info["RemoveIntermediateSeries"] = {"KeepIntermediateSeries": opt, "not_output": []}
    #if "EcosystemRespiration" in cf.keys():
        #for output in cf["EcosystemRespiration"].keys():
            #if "ERUsingSOLO" in cf["EcosystemRespiration"][output].keys():
                #rpSOLO_createdict(cf, ds, l6_info, output, "ERUsingSOLO", 610)
            #if "ERUsingLloydTaylor" in cf["EcosystemRespiration"][output].keys():
                #pfp_rpLT.rpLT_createdict(cf, ds, l6_info, output, "ERUsingLloydTaylor", 620)
            #if "ERUsingLasslop" in cf["EcosystemRespiration"][output].keys():
                #pfp_rpLL.rpLL_createdict(cf, ds, l6_info, output, "ERUsingLasslop", 630)
            #if "MergeSeries" in cf["EcosystemRespiration"][output].keys():
                #rpMergeSeries_createdict(cf, ds, l6_info, output, "MergeSeries")
    #if "NetEcosystemExchange" in cf.keys():
        #l6_info["NetEcosystemExchange"] = {}
        #for output in cf["NetEcosystemExchange"].keys():
            #rpNEE_createdict(cf, ds, l6_info["NetEcosystemExchange"], output)
    #if "GrossPrimaryProductivity" in cf.keys():
        #l6_info["GrossPrimaryProductivity"] = {}
        #for output in cf["GrossPrimaryProductivity"].keys():
            #rpGPP_createdict(cf, ds, l6_info["GrossPrimaryProductivity"], output)
    #return l6_info
    # check to see if a turbulence filter has been applied to the CO2 flux
    #if "turbulence_filter" not in Fc["Attr"]:
        ## print error message to the log window
        #msg = "CO2 flux series Fc did not have a turbulence filter applied."
        #logger.error(msg)
        #msg = "Please repeat the L5 processing and apply a turbulence filter."
        #logger.error(msg)
        #msg = "Quiting L6 processing ..."
        #logger.error(msg)
        ## check to see if we are running in interactive mode
        #if cf["Options"]["call_mode"].lower() == "interactive":
            ## if so, put up a message box
            #msg = "CO2 flux series Fc did not have a turbulence filter applied.\n"
            #msg = msg + "Please repeat the L5 processing and apply a turbulence filter.\n"
            #msg = msg + "Quiting L6 processing ..."
            #msgbox = pfp_gui.myMessageBox(msg, title="Critical")
        ## set the return code to non-zero ...
        #ds.returncodes["value"] = 1
        #ds.returncodes["message"] = "quit"
        ## ... and return
        #return

def parse_variable_attributes(attributes):
    """
    Purpose:
     Clean up the variable attributes.
    Usage:
    Author: PRI
    Date: September 2019
    """
    for attr in attributes:
        value = attributes[attr]
        if not isinstance(value, basestring):
            continue
        if attr in ["rangecheck_lower", "rangecheck_upper", "diurnalcheck_numsd"]:
            if ("[" in value) and ("]" in value) and ("*" in value):
                # old style of [value]*12
                value = value[value.index("[")+1:value.index("]")]
            elif ("[" in value) and ("]" in value) and ("*" not in value):
                # old style of [1,2,3,4,5,6,7,8,9,10,11,12]
                value = value.replace("[", "").replace("]", "")
            strip_list = [" ", '"', "'"]
        elif ("ExcludeDates" in attr or
              "ExcludeHours" in attr or
              "LowerCheck" in attr or
              "UpperCheck" in attr):
            strip_list = ["[", "]", '"', "'"]
        else:
            strip_list = ['"', "'"]
        for c in strip_list:
            if c in value:
                value = value.replace(c, "")
        attributes[attr] = value
    return attributes

def remove_variables(cfg, ds):
    """
    Purpose:
     Remove deprecated variables from a netCDF file.
    Usage:
    Author: PRI
    Date: October 2018
    """
    remove_list = [v for v in list(cfg["Variables"].keys()) if "remove" in cfg["Variables"][v]]
    series_list = sorted(list(ds.series.keys()))
    for label in series_list:
        if label in remove_list:
            ds.series.pop(label)
    return

def change_global_attributes(cfg, ds):
    """
    Purpose:
     Clean up the global attributes.
    Usage:
    Author: PRI
    Date: October 2018
    """
    # check site_name is in ds.globalattributes
    gattr_list = list(ds.globalattributes.keys())
    if "site_name" not in gattr_list:
        print "Global attributes: site_name not found"
    # check latitude and longitude are in ds.globalattributes
    if "latitude" not in gattr_list:
        print "Global attributes: latitude not found"
    else:
        lat_string = str(ds.globalattributes["latitude"])
        if len(lat_string) == 0:
            print "Global attributes: latitude empty"
        else:
            lat = pfp_utils.convert_anglestring(lat_string)
        ds.globalattributes["latitude"] = str(lat)
    if "longitude" not in gattr_list:
        print "Global attributes: longitude not found"
    else:
        lon_string = str(ds.globalattributes["longitude"])
        if len(lon_string) == 0:
            print "Global attributes: longitude empty"
        else:
            lon = pfp_utils.convert_anglestring(lon_string)
        ds.globalattributes["longitude"] = str(lon)
    # check to see if there there is a time_zone global attribute
    gattr_list = list(ds.globalattributes.keys())
    if not "time_zone" in gattr_list:
        # get the site name
        site_name = ds.globalattributes["site_name"]
        sn = site_name.replace(" ","").replace(",","").lower()
        # first, see if the site is in constants.tz_dict
        if sn in list(c.tz_dict.keys()):
            ds.globalattributes["time_zone"] = c.tz_dict[sn]
        else:
            if "latitude" in gattr_list and "longitude" in gattr_list:
                lat = float(ds.globalattributes["latitude"])
                lon = float(ds.globalattributes["longitude"])
                if lat != -9999 and lon != -9999:
                    tf = timezonefinder.TimezoneFinder()
                    tz = tf.timezone_at(lng=lon, lat=lat)
                    ds.globalattributes["time_zone"] = tz
                else:
                    print "Global attributes: unable to define time zone"
                    ds.globalattributes["time_zone"] = ""
    # add or change global attributes as required
    gattr_list = sorted(list(cfg["Global"].keys()))
    for gattr in gattr_list:
        ds.globalattributes[gattr] = cfg["Global"][gattr]
    # remove deprecated global attributes
    flag_list = [g for g in ds.globalattributes.keys() if "Flag" in g]
    others_list = ["end_datetime", "start_datetime", "Functions", "doi"]
    remove_list = others_list + flag_list
    for gattr in list(ds.globalattributes.keys()):
        if gattr in remove_list:
            ds.globalattributes.pop(gattr)
    # rename global attributes
    rename_dict = {"EPDversion":"PythonVersion", "elevation":"altitude"}
    for item in rename_dict:
        if item in list(ds.globalattributes.keys()):
            new_key = rename_dict[item]
            ds.globalattributes[new_key] = ds.globalattributes.pop(item)
    return

def change_variable_attributes(cfg, ds):
    """
    Purpose:
     Clean up the variable attributes.
    Usage:
    Author: PRI
    Date: November 2018
    """
    # rename existing long_name to description, introduce a
    # consistent long_name attribute and introduce the group_name
    # attribute
    vattr_list = list(cfg["variable_attributes"].keys())
    series_list = list(ds.series.keys())
    descr = "description_" + ds.globalattributes["nc_level"]
    for label in series_list:
        variable = pfp_utils.GetVariable(ds, label)
        variable["Attr"][descr] = copy.deepcopy(variable["Attr"]["long_name"])
        for item in vattr_list:
            if label[:len(item)] == item:
                for key in list(cfg["variable_attributes"][item].keys()):
                    variable["Attr"][key] = cfg["variable_attributes"][item][key]
        pfp_utils.CreateVariable(ds, variable)
    # parse variable attributes to new format, remove deprecated variable attributes
    # and fix valid_range == "-1e+35,1e+35"
    tmp = cfg["variable_attributes"]["deprecated"]
    deprecated = pfp_cfg.cfg_string_to_list(tmp)
    series_list = list(ds.series.keys())
    for label in series_list:
        variable = pfp_utils.GetVariable(ds, label)
        # parse variable attributes to new format
        variable["Attr"] = parse_variable_attributes(variable["Attr"])
        # remove deprecated variable attributes
        for vattr in deprecated:
            if vattr in list(variable["Attr"].keys()):
                del variable["Attr"][vattr]
        # fix valid_range == "-1e+35,1e+35"
        if "valid_range" in variable["Attr"]:
            valid_range = variable["Attr"]["valid_range"]
            if valid_range == "-1e+35,1e+35":
                d = numpy.ma.min(variable["Data"])
                mn = pfp_utils.round2significant(d, 4, direction='down')
                d = numpy.ma.max(variable["Data"])
                mx = pfp_utils.round2significant(d, 4, direction='up')
                variable["Attr"]["valid_range"] = repr(mn) + "," + repr(mx)
        pfp_utils.CreateVariable(ds, variable)
    return

def error_handler(info, msg, val):
    """
    Purpose:
     Handle errors from ParseL1ControlFile().
    """
    #print msg
    logger.error(msg)
    info["status"]["message"] = msg
    info["status"]["value"] = val
    return

def exclude_variables(cfg, ds):
    """
    Purpose:
     Remove deprecated variables from a netCDF file.
    Usage:
    Author: PRI
    Date: October 2018
    """
    series_list = sorted(list(ds.series.keys()))
    var_list = [v for v in list(cfg["exclude"].keys())]
    flag_list = [v+"_QCFlag" for v in var_list if v+"_QCFlag" in series_list]
    remove_list = var_list + flag_list
    for label in series_list:
        if label in remove_list:
            ds.series.pop(label)
    return

def include_variables(cfg, ds_in):
    """
    Purpose:
     Only pick variables that match the specified string for the length
     of the specified string.
    Usage:
    Author: PRI
    Date: November 2018
    """
    # get a new data structure
    ds_out = pfp_io.DataStructure()
    # copy the global attributes
    for gattr in ds_in.globalattributes:
        ds_out.globalattributes[gattr] = ds_in.globalattributes[gattr]
    # loop over variables to be included
    include_list = list(cfg["include"].keys())
    series_list = list(ds_in.series.keys())
    for item in include_list:
        for label in series_list:
            if label[0:len(item)] == item:
                ds_out.series[label] = ds_in.series[label]
    return ds_out

def l1_update_controlfile(cfg):
    """
    Purpose:
     Parse the L1 control file to update the syntax from earlier OFQC/PFP versions
     to the syntax used by this version.
    Usage:
     result = pfp_compliance.l1_update_controlfile(cfg)
     where cfg is a ConfigObj object
           result is True if the L1 control file was updated successfully
                     False if it couldn't be updated
    Side effects:
    Author: PRI
    Date: February 2020
    """
    # copy the control file
    cfg_original = copy.deepcopy(cfg)
    # initialise the return logical
    ok = True
    try:
        cfg = l1_update_cfg_syntax(cfg)
    except Exception:
        ok = False
        msg = " An error occurred updating the L1 control file syntax"
    # check to see if we can load the nc_cleanup.txt standard control file
    try:
        stdname = "controlfiles/standard/nc_cleanup.txt"
        cfg_std = pfp_io.get_controlfilecontents(stdname)
    except Exception:
        ok = False
        msg = " Unable to load standard control file " + stdname
    # clean up the variable names
    try:
        cfg = l1_update_cfg_variable_names(cfg, cfg_std)
        cfg = l1_update_cfg_global_attributes(cfg, cfg_std)
        cfg = l1_update_cfg_variable_attributes(cfg, cfg_std)
    except Exception:
        ok = False
        msg = " An error occurred updating the L1 control file contents"
    if ok:
        # check to see if the control file object has been changed
        if cfg != cfg_original:
            # and save it if it has changed
            file_name = os.path.basename(cfg.filename)
            logger.info(" Updated and saved control file " + file_name)
            cfg.write()
    else:
        logger.error(msg)
        error_message = traceback.format_exc()
        logger.error(error_message)
    return ok

def l1_update_cfg_global_attributes(cfg, cfg_std):
    """
    Purpose:
     Update the global attributes according to the rules in the standard control file.
    Usage:
    Author: PRI
    Date: May 2020
    """
    # check for the essential global attributes
    essentials = ["latitude", "longitude", "site_name", "time_step", "time_zone"]
    for gattr in essentials:
        if gattr not in cfg["Global"]:
            cfg["Global"][gattr] = ""
    # remove deprecated global attributes
    deprecated = ["end_datetime", "start_datetime", "Functions", "doi"]
    for gattr in deprecated:
        if gattr in cfg["Global"]:
            cfg["Global"].pop(gattr)
    # rename global attributes
    renames = {"EPDversion":"PythonVersion", "elevation":"altitude"}
    for rename in list(renames.keys()):
        if rename in cfg["Global"]:
            cfg["Global"][renames[rename]] = cfg["Global"].pop(rename)
    # add or change global attributes as required
    gattrs = sorted(list(cfg_std["Global"].keys()))
    for gattr in gattrs:
        cfg["Global"][gattr] = cfg_std["Global"][gattr]
    return cfg

def l1_update_cfg_syntax(cfg):
    """
    Purpose:
     Update an L1 control file from the old-style (pre PFP V1.0) syntax to the
     new-style syntax (post PFP V1.0).
    Usage:
    Side effects:
     Returns a modified control file object.
    Author: PRI
    Date: 9th May 2020, the day after my 64th birthday!
    """
    strip_list = ['"', "'", "[", "]"]
    for key1 in cfg:
        if key1 in ["level"]:
            cfg[key1] = parse_cfg_values(key1, cfg[key1], strip_list)
        elif key1 in ["Files", "Global"]:
            for key2 in cfg[key1]:
                cfg[key1][key2] = parse_cfg_values(key2, cfg[key1][key2], strip_list)
        elif key1 in ["Variables"]:
            for key2 in cfg[key1]:
                for key3 in cfg[key1][key2]:
                    if key3 in ["xl", "csv", "Attr"]:
                        cfg3 = cfg[key1][key2][key3]
                        for key4 in cfg3:
                            # for keywords to lower case
                            if key4.lower() != key4:
                                cfg3[key4.lower()] = cfg3.pop(key4)
                            cfg3[key4.lower()] = parse_cfg_variables_value(key3, cfg3[key4.lower()])
        else:
            del cfg[key1]
    return cfg

def l1_update_cfg_variable_attributes(cfg, cfg_std):
    """
    Purpose:
     Update the variable attributes.
    Usage:
    Author: PRI
    Date: May 2020
    """
    # list of essential variable attributes
    vattrs_essential= ["group_name", "height", "instrument", "long_name", "standard_name", "units"]
    # list of standard attribute values
    labels_standard = list(cfg_std["variable_attributes"].keys())
    labels_cfg = list(cfg["Variables"].keys())
    # add any essential variable attributes that are missing
    for label in labels_cfg:
        vattrs_cfg = list(cfg["Variables"][label]["Attr"].keys())
        for vattr in vattrs_essential:
            if vattr not in vattrs_cfg:
                cfg["Variables"][label]["Attr"][vattr] = ""
    # force some variable attributes to particular values
    for label in labels_cfg:

        labels = [l for l in labels_cfg if label in l[:len(label)]]
    return

def l1_update_cfg_variable_names(cfg, cfg_std):
    """
    Purpose:
     Update the variable names according to the rules in the standard control file.
    Usage:
    Author: PRI
    Date: May 2020
    """
    renames = list(cfg_std["rename"].keys())
    # loop over the variables in the control file
    labels = list(cfg["Variables"].keys())
    for label in labels:
        if label in renames:
            new_name = cfg["rename"][label]["rename"]
            cfg[new_name] = cfg.pop(label)
    return cfg

def l2_update_controlfile(cfg):
    """
    Purpose:
     Parse the L2 control file to update the syntax from earlier OFQC/PFP versions
     to the syntax used by this version.
    Usage:
     result = pfp_compliance.l2_update_controlfile(cfg)
     where cfg is a ConfigObj object
           result is True if the L2 control file was updated successfully
                     False if it couldn't be updated
    Side effects:
    Author: PRI
    Date: February 2020
    """
    # copy the control file
    cfg_original = copy.deepcopy(cfg)
    # initialise the return logical
    ok = True
    try:
        strip_list = ['"', "'", "[", "]"]
        for key1 in cfg:
            if key1 in ["level"]:
                cfg[key1] = parse_cfg_values(key1, cfg[key1], strip_list)
            elif key1 in ["Files"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    cfg2 = parse_cfg_values(key2, cfg2, strip_list)
            elif key1 in ["Options"]:
                for key2 in cfg[key1]:
                    if key2 in ["irga_type", "SONIC_Check", "IRGA_Check"]:
                        cfg2 = cfg[key1][key2]
                        cfg2 = parse_cfg_values(key2, cfg2, strip_list)
                    else:
                        del cfg[key1][key2]
            elif key1 in ["Plots"]:
                for key2 in cfg[key1]:
                    title = parse_cfg_plots_title(cfg, key1, key2)
                    cfg[key1].rename(key2, title)
                    cfg2 = cfg[key1][title]
                    for key3 in cfg2:
                        # force keywords to lower case
                        cfg2.rename(key3, key3.lower())
                        cfg3 = cfg2[key3.lower()]
                        cfg3 = parse_cfg_plots_value(key3, cfg3)
            elif key1 in ["Variables"]:
                for key2 in cfg[key1]:
                    # deprecated variables
                    if key2 in ["ustar_filtered"]:
                        del cfg[key1][key2]
                        continue
                    for key3 in cfg[key1][key2]:
                        cfg3 = cfg[key1][key2][key3]
                        if key3 in ["RangeCheck", "DependencyCheck", "DiurnalCheck", "ExcludeDates",
                                    "ApplyFcStorage", "MergeSeries", "AverageSeries"]:
                            for key4 in cfg3:
                                # force keywords to lower case
                                cfg3.rename(key4, key4.lower())
                                cfg4 = cfg3[key4.lower()]
                                cfg4 = parse_cfg_variables_value(key3, cfg4)
            else:
                del cfg[key1]
        # check to see if the control file object has been changed
        if cfg != cfg_original:
            # and save it if it has changed
            file_name = os.path.basename(cfg.filename)
            logger.info(" Updated and saved control file " + file_name)
            cfg.write()
    except Exception:
        ok = False
        msg = " An error occurred while updating the L2 control file syntax"
        logger.error(msg)
        error_message = traceback.format_exc()
        logger.error(error_message)
    return ok

def l3_correct_legacy_variable_names(cfg):
    """ Correct some legacy variable names."""
    # change Fn_KZ to Fn_4cmpt
    opt = pfp_utils.get_keyvaluefromcf(cfg, ["Variables", "Fn", "MergeSeries"],
                                       "source", default="", mode="quiet")
    if len(opt) != 0:
        if "Fn_KZ" in opt:
            opt = opt.replace("Fn_KZ", "Fn_4cmpt")
            cfg["Variables"]["Fn"]["MergeSeries"]["source"] = opt
            cfg["changed"] = True
    return

def l3_transfer_general_to_options(cfg):
    """ Copy any entries in [General] to [Options] then delete [General]."""
    if "General" in cfg:
        if "Options" not in cfg:
            cfg["Options"] = {}
        for item in cfg["General"]:
            cfg["Options"][item] = cfg["General"][item]
        del cfg["General"]
    return

def l3_update_controlfile(cfg):
    """
    Purpose:
     Parse the L3 control file to update the syntax from earlier OFQC/PFP versions
     to the syntax used by this version.
    Usage:
     result = pfp_compliance.update_l3_controlfile(cfg)
     where cfg is a ConfigObj object
           result is True if the L3 control file was updated successfully
                     False if it couldn't be updated
    Side effects:
    Author: PRI
    Date: February 2020
    """
    # get a copy of the original control file object
    cfg_original = copy.deepcopy(cfg)
    # initialise the return logical
    ok = True
    try:
        # transfer anything in the [General] section to [Options]
        l3_transfer_general_to_options(cfg)
        strip_list = ['"', "'", "[", "]"]
        for key1 in cfg:
            if key1 in ["level"]:
                cfg[key1] = parse_cfg_values(key1, cfg[key1], strip_list)
            elif key1 in ["Files", "Global", "Soil", "Massman"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    cfg2 = parse_cfg_values(key2, cfg2, strip_list)
            elif key1 in ["Options"]:
                for key2 in cfg[key1]:
                    if key2 in ["MassmanCorrection", "CO2Units", "FcUnits", "UseL2Fluxes",
                                "2DCoordRotation", "ApplyFcStorage", "CorrectIndividualFg",
                                "CorrectFgForStorage", "zms"]:
                        cfg2 = cfg[key1][key2]
                        cfg2 = parse_cfg_values(key2, cfg2, strip_list)
                    else:
                        del cfg[key1][key2]
            elif key1 in ["Plots"]:
                for key2 in cfg[key1]:
                    title = parse_cfg_plots_title(cfg, key1, key2)
                    cfg[key1].rename(key2, title)
                    cfg2 = cfg[key1][title]
                    for key3 in cfg2:
                        # force keywords to lower case
                        cfg2.rename(key3, key3.lower())
                        cfg3 = cfg2[key3.lower()]
                        cfg3 = parse_cfg_plots_value(key3, cfg3)
            elif key1 in ["Variables"]:
                for key2 in cfg[key1]:
                    # deprecated variables
                    if key2 in ["ustar_filtered"]:
                        del cfg[key1][key2]
                        continue
                    for key3 in cfg[key1][key2]:
                        if key3 in ["RangeCheck", "DependencyCheck", "DiurnalCheck", "ExcludeDates",
                                    "ApplyFcStorage", "MergeSeries", "AverageSeries"]:
                            cfg3 = cfg[key1][key2][key3]
                            for key4 in cfg3:
                                # for keywords to lower case
                                cfg3.rename(key4, key4.lower())
                                cfg4 = cfg3[key4.lower()]
                                cfg4 = parse_cfg_variables_value(key3, cfg4)
            else:
                del cfg[key1]
        # correct legacy variable names in the control file
        l3_correct_legacy_variable_names(cfg)
        # check to see if the control file object has been changed
        if cfg != cfg_original:
            # and save it if it has changed
            file_name = os.path.basename(cfg.filename)
            logger.info(" Updated and saved control file " + file_name)
            cfg.write()
    except Exception:
        ok = False
        msg = " An error occurred while updating the L3 control file syntax"
        logger.error(msg)
        error_message = traceback.format_exc()
        logger.error(error_message)
    return ok

def l4_update_controlfile(cfg):
    """
    Purpose:
     Parse the L4 control file to make sure the syntax is correct and that the
     control file contains all of the information needed.
    Usage:
     result = pfp_compliance.l4_update_controlfile(cf)
     where cf is a ConfigObj object
           result is True if the L4 control file is compliant
                     False if it is not compliant
    Side effects:
    Author: PRI
    Date: September 2019
    """
    # get a copy of the original control file object
    cfg_original = copy.deepcopy(cfg)
    # initialise the return logical
    ok = True
    try:
        strip_list = ['"', "'", "[", "]"]
        for key1 in cfg:
            if key1 in ["level"]:
                cfg[key1] = parse_cfg_values(key1, cfg[key1], strip_list)
            elif key1 in ["Files", "Global"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    cfg2 = parse_cfg_values(key2, cfg2, strip_list)
            elif key1 in ["Options"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    if key2 in ["MaxGapInterpolate"]:
                        cfg2 = parse_cfg_values(key2, cfg2, strip_list)
                    else:
                        del cfg[key1][key2]
            elif key1 in ["Imports"]:
                if key1 in ["Imports"]:
                    for key2 in cfg[key1]:
                        for key3 in cfg[key1][key2]:
                            cfg3 = cfg[key1][key2][key3]
                            cfg3 = parse_cfg_values(key3, cfg3, strip_list)
            elif key1 in ["Drivers"]:
                for key2 in cfg[key1]:
                    for key3 in cfg[key1][key2]:
                        cfg3 = cfg[key1][key2][key3]
                        if key3 in ["GapFillFromAlternate", "GapFillFromClimatology",
                                    "GapFillUsingMDS"]:
                            for key4 in cfg3:
                                cfg4 = cfg[key1][key2][key3][key4]
                                for key5 in cfg4:
                                    cfg4.rename(key5, key5.lower())
                                    cfg5 = cfg4[key5.lower()]
                                    cfg5 = parse_cfg_values(key5, cfg5, strip_list)
                        elif key3 in ["RangeCheck", "DependencyCheck", "DiurnalCheck",
                                      "ExcludeDates", "MergeSeries"]:
                            # strip out unwanted characters
                            for key4 in cfg3:
                                # force lower case
                                cfg3.rename(key4, key4.lower())
                                cfg4 = cfg[key1][key2][key3][key4.lower()]
                                cfg4 = parse_cfg_variables_value(key3, cfg4)
            else:
                del cfg[key1]
        # check to see if the control file object has been changed
        if cfg != cfg_original:
            # and save it if it has changed
            file_name = os.path.basename(cfg.filename)
            logger.info(" Updated and saved control file " + file_name)
            cfg.write()
    except Exception:
        ok = False
        msg = " An error occurred while parsing the L4 control file"
        logger.error(msg)
        error_message = traceback.format_exc()
        logger.error(error_message)
    return ok

def l5_update_controlfile(cfg):
    """
    Purpose:
     Parse the L5 control file to make sure the syntax is correct and that the
     control file contains all of the information needed.
    Usage:
     result = pfp_compliance.l5_update_controlfile(cfg)
     where cfg is a ConfigObj object
           result is True if the L5 control file is compliant
                     False if it is not compliant
    Side effects:
    Author: PRI
    Date: September 2019
    """
    # get a copy of the original control file object
    cfg_original = copy.deepcopy(cfg)
    # initialise the return logical
    ok = True
    try:
        strip_list = ['"', "'", "[", "]"]
        for key1 in cfg:
            if key1 in ["level"]:
                cfg[key1] = parse_cfg_values(key1, cfg[key1], strip_list)
            elif key1 in ["Files", "Global", "ustar_threshold"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    cfg2 = parse_cfg_values(key2, cfg2, strip_list)
            elif key1 in ["Options"]:
                for key2 in cfg[key1]:
                    if key2 in ["MaxGapInterpolate", "MaxShortGapLength", "FilterList",
                                "TurbulenceFilter", "DayNightFilter", "AcceptDayTimes",
                                "TruncateToImports"]:
                        cfg2 = cfg[key1][key2]
                        cfg2 = parse_cfg_values(key2, cfg2, strip_list)
                    else:
                        del cfg[key1][key2]
            elif key1 in ["Imports"]:
                for key2 in cfg[key1]:
                    for key3 in cfg[key1][key2]:
                        cfg3 = cfg[key1][key2][key3]
                        cfg3 = parse_cfg_values(key3, cfg3, strip_list)
            elif key1 in ["Fluxes"]:
                # key2 is the variable name
                for key2 in cfg[key1]:
                    # key3 is the gap filling method
                    for key3 in cfg[key1][key2]:
                        cfg3 = cfg[key1][key2][key3]
                        if key3 in ["GapFillUsingSOLO", "GapFillLongSOLO", "GapFillUsingMDS",
                                    "GapFillFromClimatology"]:
                            # key4 is the gap fill variable
                            for key4 in cfg3:
                                cfg4 = cfg[key1][key2][key3][key4]
                                for key5 in cfg4:
                                    cfg4.rename(key5, key5.lower())
                                    cfg5 = cfg4[key5.lower()]
                                    cfg5 = parse_cfg_values(key5, cfg5, strip_list)
                        elif key3 in ["MergeSeries", "RangeCheck", "DependencyCheck",
                                      "DiurnalCheck", "ExcludeDates"]:
                            # strip out unwanted characters
                            for key4 in cfg3:
                                # force lower case
                                cfg3.rename(key4, key4.lower())
                                cfg4 = cfg3[key4.lower()]
                                cfg4 = parse_cfg_variables_value(key3, cfg4)
            else:
                del cfg[key1]
        # check to see if the control file object has been changed
        if cfg != cfg_original:
            # and save it if it has changed
            file_name = os.path.basename(cfg.filename)
            logger.info(" Updated and saved control file " + file_name)
            cfg.write()
    except Exception:
        ok = False
        msg = " An error occurred while parsing the L4 control file"
        logger.error(msg)
        error_message = traceback.format_exc()
        logger.error(error_message)
    return ok

def l6_update_controlfile(cfg):
    """
    Purpose:
     Check a control file to see if it conforms to the the syntax expected at L6.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2019
    """
    # get a copy of the original control file object
    cfg_original = copy.deepcopy(cfg)
    # initialise the return logical
    ok = True
    # check to see if we have an old style L6 control file
    if "ER" in cfg.keys() or "NEE" in cfg.keys() or "GPP" in cfg.keys():
        ok = False
        msg = "This is an old version of the L6 control file.\n"
        msg = msg + "Close the L6 control file and create a new one from\n"
        msg = msg + "the template in PyFluxPro/controlfiles/template/L6."
        result = pfp_gui.MsgBox_Quit(msg, title="Critical")
        return ok
    try:
        strip_list = ['"', "'", "[", "]"]
        for key1 in cfg:
            if key1 in ["level"]:
                cfg[key1] = parse_cfg_values(key1, cfg[key1], strip_list)
            elif key1 in ["Files", "Global"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    cfg2 = parse_cfg_values(key2, cfg2, strip_list)
            elif key1 in ["Options"]:
                # no options section in L6 control file yet
                pass
            elif key1 in ["EcosystemRespiration"]:
                for key2 in cfg[key1]:
                    cfg2 = cfg[key1][key2]
                    for key3 in cfg2:
                        cfg3 = cfg[key1][key2][key3]
                        if key3 in ["ERUsingSOLO", "ERUsingLloydTaylor", "ERUsingLasslop"]:
                            for key4 in cfg3:
                                cfg4 = cfg[key1][key2][key3][key4]
                                for key5 in cfg4:
                                    cfg4.rename(key5, key5.lower())
                                    cfg5 = cfg4[key5.lower()]
                                    cfg5 = parse_cfg_values(key5, cfg5, strip_list)
                        elif key3 in ["MergeSeries"]:
                            # strip out unwanted characters
                            for key4 in cfg[key1][key2][key3]:
                                # force lower case
                                cfg3.rename(key4, key4.lower())
                                cfg4 = cfg3[key4.lower()]
                                cfg4 = parse_cfg_variables_value(key3, cfg4)
            elif key1 in ["NetEcosystemExchange", "GrossPrimaryProductivity"]:
                for key2 in cfg[key1]:
                    for key3 in cfg[key1][key2]:
                        cfg3 = cfg[key1][key2][key3]
                        cfg3 = parse_cfg_values(key3, cfg3, strip_list)
            else:
                del cfg[key1]
        # check to see if the control file object has been changed
        if cfg != cfg_original:
            # and save it if it has changed
            file_name = os.path.basename(cfg.filename)
            logger.info(" Updated and saved control file " + file_name)
            cfg.write()
    except Exception:
        ok = False
        msg = " An error occurred while parsing the L6 control file"
        logger.error(msg)
        error_message = traceback.format_exc()
        logger.error(error_message)
    return ok

def parse_cfg_plots_title(cfg, key1, key2):
    """ Parse the [Plots] section for a title."""
    title = key2
    for item in cfg[key1][key2].keys():
        if item.lower() == "title":
            title = cfg[key1][key2][item]
            del cfg[key1][key2][item]
            break
    strip_list = ['"', "'"]
    for c in strip_list:
        if c in title:
            title = title.replace(c, "")
    return title

def parse_cfg_plots_value(k, v):
    """ Parse the [Plots] section keys to remove unnecessary characters."""
    if k.lower() in ["variables", "type", "xseries", "yseries"]:
        if ("[" in v) and ("]" in v):
            v = v.replace("[", "").replace("]", "")
    strip_list = [" ", '"', "'"]
    for c in strip_list:
        if c in v:
            v = v.replace(c, "")
    return v

def parse_cfg_values(k, v, strip_list):
    """ Parse key values to remove unnecessary characters."""
    # strip unwanted characters
    for c in strip_list:
        if c in v:
            v = v.replace(c, "")
    if k in ["file_path", "plot_path"] and "browse" not in v:
        if os.path.join(str(v), "") != v:
            v = os.path.join(str(v), "")
    return v

def parse_cfg_variables_value(k, v):
    """ Parse value from control file to remove unnecessary characters."""
    try:
        # check to see if it is a number
        r = float(v)
    except ValueError as e:
        if ("[" in v) and ("]" in v) and ("*" in v):
            # old style of [value]*12
            v = v[v.index("[")+1:v.index("]")]
        elif ("[" in v) and ("]" in v) and ("*" not in v):
            # old style of [1,2,3,4,5,6,7,8,9,10,11,12]
            v = v.replace("[", "").replace("]", "")
    # remove white space and quotes
    if k in ["ExcludeDates", "ExcludeHours", "LowerCheck", "UpperCheck"]:
        # don't remove white space between date and time
        strip_list = ['"', "'"]
    elif k in ["Attr"]:
        # don't remove white space from variable attributes
        strip_list = ['"', "'"]
    else:
        strip_list = [" ", '"', "'"]
    # strip unwanted characters
    for c in strip_list:
        if c in v:
            v = v.replace(c, "")
    return v

def nc_update(cfg):
    """
    Purpose:
     Update an OFQC-style netCDF by changing variable names and attributes.
    Usage:
    Author: PRI
    Date: October 2018
    """
    # get the input file path
    nc_file_path = pfp_io.get_infilenamefromcf(cfg)
    msg = " Converting file " + os.path.split(nc_file_path)[1]
    logger.info(msg)
    # read the input file
    ds1 = pfp_io.nc_read_series(nc_file_path)
    # update the variable names
    change_variable_names(cfg, ds1)
    # make sure there are Ws and Wd series
    copy_ws_wd(ds1)
    # make sure we have all the variables we want ...
    ds2 = include_variables(cfg, ds1)
    # ... but not the ones we don't
    exclude_variables(cfg, ds2)
    # update the global attributes
    change_global_attributes(cfg, ds2)
    # update the variable attributes
    change_variable_attributes(cfg, ds2)
    # Fc single point storage
    consistent_Fc_storage(ds2, os.path.split(nc_file_path)[1])
    # rename the original file to prevent it being overwritten
    t = time.localtime()
    rundatetime = datetime.datetime(t[0], t[1], t[2], t[3], t[4], t[5]).strftime("%Y%m%d%H%M")
    new_ext = "_" + rundatetime + ".nc"
    # add the current local datetime the base file name
    new_file_path = nc_file_path.replace(".nc", new_ext)
    msg = " Renaming original file to " + os.path.split(new_file_path)[1]
    logger.info(msg)
    # ... and rename the base file to preserve it
    os.rename(nc_file_path, new_file_path)
    # write the updated file
    nc_file = pfp_io.nc_open_write(nc_file_path)
    pfp_io.nc_write_series(nc_file, ds2)

    return 0

