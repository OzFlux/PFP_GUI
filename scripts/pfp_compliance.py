# standard modules
import copy
import logging
import os
import platform
# 3rd party modules
import timezonefinder
# PFP modules
import pfp_gui
import pfp_io
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
    rename_list = [v for v in list(cfg["Variables"].keys()) if "rename" in cfg["Variables"][v]]
    # loop over the variables in the data structure
    series_list = list(ds.series.keys())
    for label in series_list:
        if label in rename_list:
            new_name = cfg["Variables"][label]["rename"]
            ds.series[new_name] = ds.series.pop(label)
    return

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

def check_l6_controlfile(cf):
    """
    Purpose:
     Check a control file to see if it conforms to the the syntax expected at L6.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2019
    """
    ok = True
    # check to see if we have an old style L6 control file
    if "ER" in cf.keys() or "NEE" in cf.keys() or "GPP" in cf.keys():
        ok = False
        msg = "This is an old version of the L6 control file.\n"
        msg = msg + "Close the L6 control file and create a new one from\n"
        msg = msg + "the template in PyFluxPro/controlfiles/template/L6."
        result = pfp_gui.MsgBox_Quit(msg, title="Critical")
    return ok

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
        logger.warning("Globel attributes: site_name not found")
    # check latitude and longitude are in ds.globalattributes
    if "latitude" not in gattr_list:
        logger.warning("Global attributes: latitude not found")
    else:
        lat_string = str(ds.globalattributes["latitude"])
        if len(lat_string) == 0:
            logger.warning("Global attributes: latitude empty")
        else:
            lat = pfp_utils.convert_anglestring(lat_string)
        ds.globalattributes["latitude"] = str(lat)
    if "longitude" not in gattr_list:
        logger.warning("Global attributes: longitude not found")
    else:
        lon_string = str(ds.globalattributes["longitude"])
        if len(lon_string) == 0:
            logger.warning("Global attributes: longitude empty")
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
                    logger.warning("Global attributes: unable to define time zone")
                    ds.globalattributes["time_zone"] = ""
    # add or change global attributes as required
    gattr_list = sorted(list(cfg["Global"].keys()))
    for gattr in gattr_list:
        ds.globalattributes[gattr] = cfg["Global"][gattr]
    # remove deprecated global attributes
    flag_list = [g for g in ds.globalattributes.keys() if "Flag" in g]
    others_list = ["end_datetime", "start_datetime", "doi"]
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

def nc_update(cfg):
    """
    Purpose:
     Update a PFP-style netCDF file by changing variable names and attributes.
    Usage:
    Author: PRI
    Date: October 2018
    """
    nc_file_path = pfp_io.get_infilenamefromcf(cfg)
    ds = pfp_io.nc_read_series(nc_file_path)
    change_variable_names(cfg, ds)
    copy_ws_wd(ds)
    remove_variables(cfg, ds)
    change_global_attributes(cfg, ds)
    nc_file = pfp_io.nc_open_write(nc_file_path)
    pfp_io.nc_write_series(nc_file, ds)
    return 0
