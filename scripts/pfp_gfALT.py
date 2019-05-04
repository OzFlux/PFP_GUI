# standard modules
import ast
import datetime
import logging
import os
import sys
import warnings
# 3rd party modules
import dateutil
import numpy
import matplotlib.dates as mdt
import matplotlib.pyplot as plt
import pylab
from PyQt4 import QtGui
import scipy
import statsmodels.api as sm
# PFP modules
import constants as c
import pfp_ck
import pfp_io
import pfp_ts
import pfp_utils

warnings.filterwarnings("ignore",".*GUI is implemented.*")
logger = logging.getLogger("pfp_log")

# functions for GapFillFromAlternate
def GapFillFromAlternate(main_gui, cf, ds4, ds_alt):
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
    if "alternate" not in dir(ds4):
        return
    # get a local pointer to the tower datetime series
    ldt_tower = ds4.series["DateTime"]["Data"]
    # get the start and end datetime of the tower data
    startdate = ldt_tower[0]
    enddate = ldt_tower[-1]
    # create the alternate_info dictionary, this will hold much useful information
    alternate_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                      "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                      "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                      "enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                      "plot_path": cf["Files"]["plot_path"]}
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "call_mode", default="interactive")
    alternate_info["call_mode"]= call_mode
    if call_mode.lower()=="interactive":
        alternate_info["show_plots"] = True
    if call_mode.lower()=="interactive":
        # put up a plot of the data coverage at L3
        gfalternate_plotcoveragelines(ds4)
        # call the GapFillFromAlternate GUI
        gfalternate_gui(main_gui, ds4, ds_alt, alternate_info)
    else:
        if "GUI" in cf:
            if "Alternate" in cf["GUI"]:
                gfalternate_run_nogui(cf, ds4, ds_alt, alternate_info)
            else:
                logger.warning(" No GUI sub-section found in Options section of control file")
                gfalternate_plotcoveragelines(ds4)
                gfalternate_gui(main_gui, ds4, ds_alt, alternate_info)
        else:
            logger.warning(" No GUI sub-section found in Options section of control file")
            gfalternate_plotcoveragelines(ds4)
            gfalternate_gui(main_gui, ds4, ds_alt, alternate_info)

def gfalternate_gui(main_gui, ds4, ds_alt, alternate_info):
    # put up the start and end dates
    main_gui.l4_ui.ds4 = ds4
    main_gui.l4_ui.ds_alt = ds_alt
    main_gui.l4_ui.alternate_info = alternate_info
    main_gui.l4_ui.edit_cfg = main_gui.tabs.tab_dict[main_gui.tabs.tab_index_running]
    start_date = ds4.series["DateTime"]["Data"][0].strftime("%Y-%m-%d %H:%M")
    end_date = ds4.series["DateTime"]["Data"][-1].strftime("%Y-%m-%d %H:%M")
    main_gui.l4_ui.label_DataStartDate_value.setText(start_date)
    main_gui.l4_ui.label_DataEndDate_value.setText(end_date)
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
        data_composite, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label_composite, si=si_tower, ei=ei_tower)
        data_tower, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label_tower, si=si_tower, ei=ei_tower)
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
                data_alt, _, _ = pfp_utils.GetSeriesasMA(ds_alternate, label_alternate, si=si_alternate, ei=ei_alternate)
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
        if mode.lower() != "quiet":
            logger.info(" autocomplete: variable %s has %s gaps", label_tower, str(len(gapstartend)))
        logger.info(" Auto-complete gap filling for %s (%s gaps)", label_tower, str(gotdataforgap.count(True)))
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
            gapfillperiod_startdate = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
            gapfillperiod_enddate = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
            if mode.lower()!="quiet":
                msg = " autocomplete: gap fill period is "+gapfillperiod_startdate+" to "+gapfillperiod_enddate
                logger.info(msg)
            alternate_info["startdate"] = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
            alternate_info["enddate"] = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
            gfalternate_main(ds_tower, ds_alt, alternate_info, label_tower_list=[label_tower])
            gfalternate_plotcoveragelines(ds_tower)
            if not_enough_points: break

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

def gfalternate_done(alt_gui):
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
    ds = alt_gui.ds4
    # plot the summary statistics
    #gfalternate_plotsummary(ds,alternate_info)
    # destroy the alternate GUI
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
    si_tower = pfp_utils.GetDateIndex(ldt_tower, startdate,ts=ts)
    ei_tower = pfp_utils.GetDateIndex(ldt_tower, enddate,ts=ts)
    data_tower, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label_tower, si=si_tower, ei=ei_tower)
    # local pointers to the start and end indices
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    si_alternate = pfp_utils.GetDateIndex(ldt_alternate, startdate, ts=ts)
    ei_alternate = pfp_utils.GetDateIndex(ldt_alternate, enddate, ts=ts)
    # create an array for the correlations and a list for the alternate variables in order of decreasing correlation
    if "usevars" not in ds_tower.alternate[label_output]:
        altvar_list = gfalternate_getalternatevarlist(ds_alternate, alternate_info["alternate_name"])
    else:
        altvar_list = ds_tower.alternate[label_output]["usevars"]
    r = numpy.zeros(len(altvar_list))
    # loop over the variables in the alternate file
    for idx,var in enumerate(altvar_list):
        # get the alternate data
        data_alternate, _, _ = pfp_utils.GetSeriesasMA(ds_alternate, var, si=si_alternate, ei=ei_alternate)
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
        r[idx] = numpy.ma.filled(rval, float(c.missing_value))
    # save the correlation array for later plotting
    alternate_info["r"] = r
    # sort the correlation array and the alternate variable list
    idx = numpy.flipud(numpy.argsort(r))
    altvar_list_sorted = [altvar_list[j] for j in list(idx)]
    # return the name of the alternate variable that has the highest correlation with the tower data
    if ds_tower.alternate[label_output]["source"].lower()=="access": altvar_list_sorted = altvar_list_sorted[0:1]
    return altvar_list_sorted

def gfalternate_getalternatevarlist(ds_alternate, label):
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
        logger.error("gfalternate_getalternatevarlist: series %s not in alternate data file", label)
    return alternate_var_list

def gfalternate_getdataas2d(odt, data,alternate_info):
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

def gfalternate_getcorrecteddata(ds_alternate, data_dict, stat_dict, alternate_info):
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
            data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.masked_all_like(data_dict[label_output][label_alternate]["data"])
            stat_dict[label_output][label_alternate]["slope"] = float(0)
            stat_dict[label_output][label_alternate]["offset"] = float(0)
            stat_dict[label_output][label_alternate]["eqnstr"] = "Too few points"
    else:
        msg = "getcorrecteddata: Unrecognised combination of logical tests"
        logger.error(msg)

def gfalternate_getlagcorrecteddata(ds_alternate, data_dict, stat_dict, alternate_info):
    label_tower = alternate_info["label_tower"]
    label_output = alternate_info["label_output"]
    label_alternate = alternate_info["label_alternate"]
    data_tower = data_dict[label_tower]["data"]
    data_alternate = data_dict[label_output][label_alternate]["data"]
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    startdate = alternate_info["startdate"]
    enddate = alternate_info["enddate"]
    ts = alternate_info["time_step"]
    si_alternate = pfp_utils.GetDateIndex(ldt_alternate, startdate, ts=ts)
    ei_alternate = pfp_utils.GetDateIndex(ldt_alternate, enddate, ts=ts)
    if alternate_info["lag"].lower() == "yes":
        maxlags = alternate_info["max_lags"]
        _, corr = pfp_ts.get_laggedcorrelation(data_tower, data_alternate, maxlags)
        nLags = numpy.argmax(corr) - alternate_info["max_lags"]
        if nLags > alternate_info["nperhr"]*6:
            logger.error("getlagcorrecteddata: lag is more than 6 hours for %s", label_tower)
        si_alternate = si_alternate - nLags
        ei_alternate = ei_alternate - nLags
        data_alternate, _, _ = pfp_utils.GetSeriesasMA(ds_alternate, label_alternate, si=si_alternate, ei=ei_alternate, mode="mirror")
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
            nx = len(x)
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
        stat_dict[label]["No. filled"] = trap_masked_constant(num)
        # correlation coefficient
        r = numpy.ma.corrcoef(data_dict[label_tower]["data"],data_dict[label]["fitcorr"])
        stat_dict[label]["r"] = trap_masked_constant(r[0,1])
        # means
        avg = numpy.ma.mean(data_dict[label_tower]["data"])
        stat_dict[label]["Avg (Tower)"] = trap_masked_constant(avg)
        avg = numpy.ma.mean(data_dict[label]["fitcorr"])
        stat_dict[label]["Avg (Alt)"] = trap_masked_constant(avg)
        # variances
        var_tower = numpy.ma.var(data_dict[label_tower]["data"])
        stat_dict[label]["Var (Tower)"] = trap_masked_constant(var_tower)
        var_alt = numpy.ma.var(data_dict[label]["fitcorr"])
        stat_dict[label]["Var (Alt)"] = trap_masked_constant(var_alt)
        if var_alt != 0:
            stat_dict[label]["Var ratio"] = var_tower/var_alt
        else:
            stat_dict[label]["Var ratio"] = float(c.missing_value)
        # RMSE & NMSE
        error = (data_dict[label_tower]["data"]-data_dict[label]["fitcorr"])
        rmse = numpy.ma.sqrt(numpy.ma.average(error*error))
        stat_dict[label]["RMSE"] = trap_masked_constant(rmse)
        data_range = numpy.ma.maximum(data_dict[label_tower]["data"])-numpy.ma.minimum(data_dict[label_tower]["data"])
        nmse = rmse/data_range
        stat_dict[label]["NMSE"] = trap_masked_constant(nmse)
        # bias & fractional bias
        stat_dict[label]["Bias"] = trap_masked_constant(numpy.ma.average(error))
        norm_error = (error)/(0.5*(data_dict[label_tower]["data"]+data_dict[label]["fitcorr"]))
        stat_dict[label]["Frac Bias"] = trap_masked_constant(numpy.ma.average(norm_error))

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
    label_output = alternate_info["label_output"]
    label_composite = alternate_info["label_composite"]
    label_alternate = alternate_info["label_alternate"]
    ts = alternate_info["time_step"]
    si = pfp_utils.GetDateIndex(ldt_tower,alternate_info["startdate"],ts=ts,default=0)
    ei = pfp_utils.GetDateIndex(ldt_tower,alternate_info["enddate"],ts=ts,default=len(ldt_tower))
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

def gfalternate_main(ds_tower, ds_alt, alternate_info, label_tower_list=[]):
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
    # get local pointer to the datetime series
    dt_tower = ds_tower.series["DateTime"]["Data"]
    si_tower = pfp_utils.GetDateIndex(dt_tower, alternate_info["startdate"], ts=ts, default=0)
    ei_tower = pfp_utils.GetDateIndex(dt_tower, alternate_info["enddate"], ts=ts, default=len(dt_tower)-1)
    ldt_tower = dt_tower[si_tower:ei_tower+1]
    # now loop over the variables to be gap filled using the alternate data
    if len(label_tower_list)==0:
        label_tower_list = list(set(alternate_info["series_list"]))
    for fig_num,label_tower in enumerate(label_tower_list):
        alternate_info["label_tower"] = label_tower
        label_composite = label_tower+"_composite"
        alternate_info["label_composite"] = label_composite
        # read the tower data and check for gaps
        data_tower, _,attr_tower = pfp_utils.GetSeriesasMA(ds_tower,label_tower,si=si_tower,ei=ei_tower)
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
            si_alternate = pfp_utils.GetDateIndex(ldt_alternate, alternate_info["startdate"], ts=ts, default=0)
            ei_alternate = pfp_utils.GetDateIndex(ldt_alternate, alternate_info["enddate"], ts=ts, default=len(ldt_alternate)-1)
            # get the alternate series that has the highest correlation with the tower data
            label_alternate_list = gfalternate_getalternatevaratmaxr(ds_tower,ds_alternate,alternate_info,mode=mode)
            # loop over alternate variables
            for label_alternate in label_alternate_list:
                alternate_info["label_alternate"] = label_alternate
                # get the raw alternate data
                data_alternate, _,attr_alternate = pfp_utils.GetSeriesasMA(ds_alternate, label_alternate, si=si_alternate, ei=ei_alternate)
                # check this alternate variable to see if there are enough points
                alternate_info["gotminpoints_alternate"] = gfalternate_gotminpoints(data_alternate, alternate_info, label_alternate, mode=mode)
                alternate_info["gotdataforgaps_alternate"] = gfalternate_gotdataforgaps(data_dict[label_output]["data"], data_alternate,alternate_info, mode=mode)
                alternate_info["gotminpoints_both"] = gfalternate_gotminpointsboth(data_tower, data_alternate, alternate_info, label_tower, label_alternate, mode=mode)
                # update the data and sata dictionaries
                stat_dict[label_output][label_alternate] = {"startdate":alternate_info["startdate"], "enddate":alternate_info["enddate"]}
                if label_output not in data_dict[label_tower]["output_list"]:
                    data_dict[label_tower]["output_list"].append(label_output)
                data_dict[label_output][label_alternate] = {"data":data_alternate, "attr":attr_alternate}
                gfalternate_getcorrecteddata(ds_alternate, data_dict, stat_dict, alternate_info)
                gfalternate_loadoutputdata(ds_tower, data_dict, alternate_info)
                # check to see if we have alternate data for this whole period, if so there is no reason to continue
                ind_tower = numpy.where(abs(ds_tower.series[label_output]["Data"][si_tower:ei_tower+1]-float(c.missing_value))<c.eps)[0]
                if len(ind_tower)==0:
                    break
        # we have completed the loop over the alternate data for this output
        # now do the statistics, diurnal average and daily averages for this output
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
        pd = gfalternate_initplot(data_dict,alternate_info)
        diel_avg = gfalternate_getdielaverage(data_dict,alternate_info)
        # reserve figure number 0 for the coverage lines/progress plot
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
    if alternate_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    # create the figure canvas
    fig = plt.figure(nfig,figsize=(13,8))
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
    plot_path = os.path.join(alternate_info["plot_path"], "L4", "")
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+alternate_info["site_name"].replace(" ","")+"_Alternate_"+label_tower
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    if alternate_info["show_plots"]:
        plt.draw()
        plt.pause(1)
        plt.ioff()
    else:
        plt.ion()

def gfalternate_plotcoveragelines(ds_tower):
    ldt = ds_tower.series["DateTime"]["Data"]
    site_name = ds_tower.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    slist = [ds_tower.alternate[item]["label_tower"] for item in ds_tower.alternate.keys()]
    series_list = list(set(slist))
    ylabel_list = [""]+series_list+[""]
    ylabel_right_list = [""]
    color_list = ["blue", "red", "green", "yellow", "magenta", "black", "cyan", "brown"]
    xsize = 15.0
    ysize = max([len(series_list)*0.2, 1])
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
    plt.ylim([0,len(series_list)+1])
    plt.xlim([ldt[0],ldt[-1]])
    for series,n in zip(series_list,range(1,len(series_list)+1)):
        data_series, _, _ = pfp_utils.GetSeriesasMA(ds_tower,series)
        percent = 100*numpy.ma.count(data_series)/len(data_series)
        ylabel_right_list.append("{0:.0f}%".format(percent))
        ind_series = numpy.ma.ones(len(data_series))*float(n)
        ind_series = numpy.ma.masked_where(numpy.ma.getmaskarray(data_series)==True,ind_series)
        plt.plot(ldt,ind_series,color=color_list[numpy.mod(n,8)],linewidth=1)
        if series+"_composite" in ds_tower.series.keys():
            data_composite, _, _ = pfp_utils.GetSeriesasMA(ds_tower,series+"_composite")
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
    plt.draw()
    plt.ioff()

def gfalternate_plotsummary(ds,alternate_info):
    """ Plot single pages of summary results for groups of variables. """
    # get a list of variables for which alternate data is available
    output_list = ds.alternate.keys()
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
                logger.error("Series %s requested for summary plot is not available", output)
                continue
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
        plot_path = os.path.join(alternate_info["plot_path"], "L4", "")
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

def gfalternate_quit(alt_gui):
    """ Quit the GapFillFromAlternate GUI."""
    ds = alt_gui.ds4
    # destroy the alternate GUI
    alt_gui.close()
    # put the return code into ds.alternate
    ds.returncodes["alternate"] = "quit"

def gfalternate_run_gui(alt_gui):
    """ Run the GapFillFromAlternate GUI."""
    ds_tower = alt_gui.ds4
    ds_alt = alt_gui.ds_alt
    alternate_info = alt_gui.alternate_info
    # populate the alternate_info dictionary with things that will be useful
    if str(alt_gui.radioButtons.checkedButton().text()) == "Manual":
        alternate_info["peropt"] = 1
    elif str(alt_gui.radioButtons.checkedButton().text()) == "Months":
        alternate_info["peropt"] = 2
    elif str(alt_gui.radioButtons.checkedButton().text()) == "Days":
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
    logger.info(" Gap filling %s using alternate data", str(list(set(series_list))))
    if alternate_info["peropt"]==1:
        logger.info(" Starting manual run ...")
        #gfalternate_progress(alt_gui,"Starting manual run ...")
        # get the start and end datetimes entered in the alternate GUI
        if len(str(alt_gui.lineEdit_StartDate.text())) != 0:
            alternate_info["startdate"] = str(alt_gui.lineEdit_StartDate.text())
        if len(str(alt_gui.lineEdit_EndDate.text())) != 0:
            alternate_info["enddate"] = str(alt_gui.lineEdit_EndDate.text())
        gfalternate_main(ds_tower, ds_alt, alternate_info)
        gfalternate_plotcoveragelines(ds_tower)
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
        logger.info("Starting auto (months) run ...")
        #gfalternate_progress(alt_gui,"Starting auto (monthly) run ...")
        # get the start datetime entered in the alternate GUI
        nMonths = int(alt_gui.lineEdit_NumberMonths.text())
        if len(str(alt_gui.lineEdit_StartDate.text()))!=0:
            alternate_info["startdate"] = str(alt_gui.lineEdit_StartDate.text())
        if len(str(alt_gui.lineEdit_EndDate.text())) != 0:
            alternate_info["enddate"] = str(alt_gui.lineEdit_EndDate.text())
        alternate_info["gui_startdate"] = alternate_info["startdate"]
        alternate_info["gui_enddate"] = alternate_info["enddate"]
        startdate = dateutil.parser.parse(alternate_info["startdate"])
        overlap_enddate = dateutil.parser.parse(alternate_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
        enddate = min([overlap_enddate,enddate])
        alternate_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<overlap_enddate:
            gfalternate_main(ds_tower, ds_alt, alternate_info)
            gfalternate_plotcoveragelines(ds_tower)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
            alternate_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            enddate = min([enddate,overlap_enddate])
            alternate_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        gfalternate_autocomplete(ds_tower,ds_alt,alternate_info)
        #gfalternate_progress(alt_gui,"Finished auto (monthly) run ...")
        logger.info("Finished auto (months) run ...")
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
            gfalternate_main(ds_tower, ds_alt, alternate_info)
            gfalternate_plotcoveragelines(ds_tower)
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
    logger.info(" Gap filling %s using alternate data", str(list(set(series_list))))
    if alternate_info["peropt"]==1:
        gfalternate_main(ds_tower, ds_alt, alternate_info)
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
        overlap_enddate = dateutil.parser.parse(alternate_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([overlap_enddate,enddate])
        alternate_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<overlap_enddate:
            gfalternate_main(ds_tower, ds_alt, alternate_info)
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
            gfalternate_main(ds_tower, ds_alt, alternate_info)
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
                    logger.info("gfAlternate: unrecognised fit option for series %s", output)
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
                    logger.info("gfAlternate: unrecognised lag option for series %s", output)
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

def trap_masked_constant(num):
    if numpy.ma.is_masked(num):
        num = float(c.missing_value)
    return num