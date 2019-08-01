""" Routines for estimating ER using SOLO."""
# standard modules
import logging
# 3rd party modules
import numpy
# PFP modules
import constants as c
import pfp_gf
import pfp_gfSOLO
import pfp_utils

logger = logging.getLogger("pfp_log")

def ERUsingSOLO(main_gui, ds, l6_info, called_by):
    """
    Purpose:
     Estimate ER using SOLO.
    Usage:
    Side effects:
    Author: PRI
    Date: Back in the day
    Mods:
     21/8/2017 - moved GetERFromFc from pfp_ls.l6qc() to individual
                 ER estimation routines to allow for multiple sources
                 of ER.
    """
    # set the default return code
    ds.returncodes["value"] = 0
    ds.returncodes["message"] = "normal"
    # get the SOLO information
    solo = l6_info["ERUsingSOLO"]
    # check the SOLO drivers for missing data
    pfp_gf.CheckDrivers(solo, ds)
    if ds.returncodes["value"] != 0:
        return ds
    if solo["info"]["call_mode"].lower() == "interactive":
        # call the ERUsingSOLO GUI
        pfp_gfSOLO.gfSOLO_gui(main_gui, ds, solo)
    #else:
        #if "GUI" in cf:
            #if "SOLO" in cf["GUI"]:
                #rpSOLO_run_nogui(cf, ds, l6_info["ER"])

def rp_getdiurnalstats(dt, data, solo):
    ts = solo["info"]["time_step"]
    nperday = solo["info"]["nperday"]
    si = 0
    while abs(dt[si].hour+float(dt[si].minute)/60-float(ts)/60) > c.eps:
        si = si + 1
    ei = len(dt)-1
    while abs(dt[ei].hour+float(dt[ei].minute)/60) > c.eps:
        ei = ei - 1
    data_wholedays = data[si:ei+1]
    ndays = len(data_wholedays)/nperday
    data_2d = numpy.ma.reshape(data_wholedays, [ndays, nperday])
    diel_stats = {}
    diel_stats["Hr"] = numpy.ma.array([i*ts/float(60) for i in range(0, nperday)])
    diel_stats["Av"] = numpy.ma.average(data_2d, axis=0)
    diel_stats["Sd"] = numpy.ma.std(data_2d, axis=0)
    diel_stats["Mx"] = numpy.ma.max(data_2d, axis=0)
    diel_stats["Mn"] = numpy.ma.min(data_2d, axis=0)
    return diel_stats

def rpSOLO_createdict(cf, ds, l6_info, output, called_by):
    """
    Purpose:
     Creates a dictionary in l6_info to hold information about the SOLO data
     used to estimate ecosystem respiration.
    Usage:
    Side effects:
    Author: PRI
    Date: Back in the day
    """
    nrecs = int(ds.globalattributes["nc_nrecs"])
    # create the dictionary keys for this series
    if called_by not in l6_info.keys():
        l6_info[called_by] = {"outputs": {}, "info": {"source": "Fc", "target": "ER"}, "gui": {}}
    # get the info section
    pfp_gf.gfSOLO_createdict_info(cf, ds, l6_info[called_by], called_by)
    if ds.returncodes["value"] != 0:
        return
    # get the outputs section
    pfp_gf.gfSOLO_createdict_outputs(cf, l6_info[called_by], output, called_by)
    # create an empty series in ds if the SOLO output series doesn't exist yet
    Fc = pfp_utils.GetVariable(ds, l6_info[called_by]["info"]["source"])
    model_outputs = cf["EcosystemRespiration"][output][called_by].keys()
    for model_output in model_outputs:
        if model_output not in ds.series.keys():
            # create an empty variable
            variable = pfp_utils.CreateEmptyVariable(model_output, nrecs)
            variable["Attr"]["long_name"] = "Ecosystem respiration"
            variable["Attr"]["drivers"] = l6_info[called_by]["outputs"][model_output]["drivers"]
            variable["Attr"]["description_l6"] = "Modeled by neural network (SOLO)"
            variable["Attr"]["target"] = l6_info[called_by]["info"]["target"]
            variable["Attr"]["source"] = l6_info[called_by]["info"]["source"]
            variable["Attr"]["units"] = Fc["Attr"]["units"]
            pfp_utils.CreateVariable(ds, variable)
    return

def trap_masked_constant(num):
    if numpy.ma.is_masked(num):
        num = float(c.missing_value)
    return num
