# standard modules
import logging
import os
# 3rd party modules
import dateutil
import numpy
import matplotlib
import matplotlib.pyplot as plt
import pylab
import scipy
import statsmodels.api as sm
# PFP modules
import constants as c
import pfp_io
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

# functions for GapFillFromAlternate
def GapFillFromAlternate(main_gui, ds4, ds_alt, l4_info, called_by):
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
    ds4.returncodes["message"] = "normal"
    # get the alternate data information
    if l4_info[called_by]["info"]["call_mode"] == "interactive":
        # put up a plot of the data coverage at L3
        gfalternate_plotcoveragelines(ds4, l4_info, called_by)
        # call the GapFillFromAlternate GUI
        gfalternate_gui(main_gui, ds4, ds_alt, l4_info, called_by)
    else:
        # ["gui"] settings dictionary done in pfp_gf.ParseL4ControlFile()
        gfalternate_run(ds4, ds_alt, l4_info, called_by)

def gfalternate_gui(main_gui, ds4, ds_alt, l4_info, called_by):
    # put up the start and end dates
    main_gui.l4_ui.ds4 = ds4
    main_gui.l4_ui.ds_alt = ds_alt
    main_gui.l4_ui.l4_info = l4_info
    main_gui.l4_ui.called_by = called_by
    main_gui.l4_ui.edit_cfg = main_gui.tabs.tab_dict[main_gui.tabs.tab_index_running]
    start_date = ds4.series["DateTime"]["Data"][0].strftime("%Y-%m-%d %H:%M")
    end_date = ds4.series["DateTime"]["Data"][-1].strftime("%Y-%m-%d %H:%M")
    main_gui.l4_ui.label_DataStartDate_value.setText(start_date)
    main_gui.l4_ui.label_DataEndDate_value.setText(end_date)
    main_gui.l4_ui.show()
    main_gui.l4_ui.exec_()

def gfalternate_autocomplete(ds_tower, ds_alt, l4_info, called_by, mode="verbose"):
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
    l4a = l4_info[called_by]
    mode = "quiet" #"verbose" #"quiet"
    if not l4a["gui"]["auto_complete"]:
        return
    dt_tower = ds_tower.series["DateTime"]["Data"]
    nRecs = len(dt_tower)
    ts = int(ds_tower.globalattributes["time_step"])
    si_tower = pfp_utils.GetDateIndex(dt_tower, l4a["gui"]["startdate"], ts=ts, default=0)
    ei_tower = pfp_utils.GetDateIndex(dt_tower, l4a["gui"]["enddate"], ts=ts, default=nRecs-1)
    ldt_tower = dt_tower[si_tower: ei_tower + 1]
    nRecs_gui = len(ldt_tower)
    label_tower_list = l4a["gui"]["series_list"]
    for label_tower in label_tower_list:
        data_all = {}
        label_composite = label_tower + "_composite"
        not_enough_points = False
        data_composite, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label_composite, si=si_tower, ei=ei_tower)
        data_tower, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label_tower, si=si_tower, ei=ei_tower)
        mask_composite = numpy.ma.getmaskarray(data_composite)
        gapstartend = pfp_utils.contiguous_regions(mask_composite)
        if len(gapstartend) == 0:
            if mode.lower() != "quiet":
                msg = " autocomplete: composite " + label_composite + " has no gaps to fill, skipping ..."
                logger.info(msg)
            continue
        # now check all of the alternate data sources to see if they have anything to contribute
        gotdataforgap = [False]*len(gapstartend)
        label_output_list = gfalternate_getlabeloutputlist(l4_info, label_tower)
        for label_output in label_output_list:
            alt_filename = l4a["outputs"][label_output]["file_name"]
            ds_alternate = ds_alt[alt_filename]
            dt_alternate = ds_alternate.series["DateTime"]["Data"]
            si_alternate = pfp_utils.GetDateIndex(dt_alternate, l4a["gui"]["startdate"], ts=ts, default=0)
            ei_alternate = pfp_utils.GetDateIndex(dt_alternate, l4a["gui"]["enddate"], ts=ts, default=nRecs-1)
            alt_series_list = [item for item in ds_alternate.series.keys() if "_QCFlag" not in item]
            alt_series_list = [item for item in alt_series_list if l4a["outputs"][label_output]["target"] in item]
            for label_alternate in alt_series_list:
                data_alt, _, _ = pfp_utils.GetSeriesasMA(ds_alternate, label_alternate, si=si_alternate, ei=ei_alternate)
                data_all[label_alternate] = data_alt
                for n, gap in enumerate(gapstartend):
                    min_points = max([int(((gap[1]-gap[0])+1)*l4a["gui"]["min_percent"]/100),3*l4a["gui"]["nperhr"]])
                    if numpy.ma.count(data_alt[gap[0]: gap[1]]) >= min_points:
                        if mode.lower() != "quiet":
                            msg = " autocomplete: " + label_tower + ldt_tower[gap[0]] + ldt_tower[gap[1]] + " got data to fill gap"
                            logger.info(msg)
                        gotdataforgap[n] = True
                    if numpy.ma.count_masked(data_tower[gap[0]: gap[1]]) == 0:
                        if mode.lower() != "quiet":
                            msg = " autocomplete: "+label_tower + ldt_tower[gap[0]] + ldt_tower[gap[1]] + " no gap to fill"
                            logger.info(msg)
                        gotdataforgap[n] = False
        # finished checking all alternate data sources for data to fill remaining gaps
        if mode.lower() != "quiet":
            logger.info(" autocomplete: variable %s has %s gaps", label_tower, str(len(gapstartend)))
        logger.info(" Auto-complete gap filling for %s (%s gaps)", label_tower, str(gotdataforgap.count(True)))
        for n, gap in enumerate(gapstartend):
            l4a["gui"]["autoforce"] = False
            if not gotdataforgap[n]:
                if mode.lower() != "quiet":
                    gap_startdate = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
                    gap_enddate = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
                    msg = " autocomplete: no alternate data for " + gap_startdate + " to " + gap_enddate
                    logger.info(msg)
                continue
            si = max([0, gap[0]])
            ei = min([len(ldt_tower) - 1, gap[1]])
            gap_startdate = ldt_tower[si].strftime("%Y-%m-%d %H:%M")
            gap_enddate = ldt_tower[ei].strftime("%Y-%m-%d %H:%M")
            if mode.lower() != "quiet":
                msg = " autocomplete: gap is " + gap_startdate + " to " + gap_enddate
                logger.info(msg)
            min_points = max([int(((gap[1]-gap[0])+1)*l4a["gui"]["min_percent"]/100), 3*l4a["gui"]["nperhr"]])
            num_good_points = 0
            num_points_list = data_all.keys()
            for label in data_all.keys():
                if numpy.ma.count(data_all[label][gap[0]:gap[1]]) < min_points:
                    num_points_list.remove(label)
                    continue
                ngpts = gfalternate_getnumgoodpoints(data_tower[gap[0]:gap[1]], data_all[label][gap[0]:gap[1]])
                #ngpts = int(len(data_tower[gap[0]:gap[1]+1])*l4a["gui"]["min_percent"]/100)
                num_good_points = max([num_good_points, ngpts])
            while num_good_points < min_points:
                gap[0] = max(0, gap[0] - l4a["gui"]["nperday"])
                gap[1] = min(nRecs_gui - 1, gap[1] + l4a["gui"]["nperday"])
                if gap[0] == 0 and gap[1] == nRecs_gui - 1:
                    msg = " Unable to find enough good points in data set for " + label_tower
                    logger.error(msg)
                    msg = " Replacing missing tower data with unmodified alternate data"
                    logger.error(msg)
                    gap[0] = 0; gap[1] = -1
                    l4a["gui"]["autoforce"] = True
                    not_enough_points = True
                if not_enough_points: break
                min_points = max([int(((gap[1]-gap[0])+1)*l4a["gui"]["min_percent"]/100), 3*l4a["gui"]["nperhr"]])
                for label in num_points_list:
                    ngpts = gfalternate_getnumgoodpoints(data_tower[gap[0]:gap[1]+1], data_all[label][gap[0]:gap[1]+1])
                    #ngpts = int(len(data_tower[gap[0]:gap[1]+1])*l4a["gui"]["min_percent"]/100)
                    if ngpts > num_good_points:
                        num_good_points = ngpts
            gapfillperiod_startdate = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
            gapfillperiod_enddate = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
            if mode.lower() != "quiet":
                msg = " autocomplete: gap fill period is " + gapfillperiod_startdate + " to " + gapfillperiod_enddate
                logger.info(msg)
            l4a["run"]["startdate"] = ldt_tower[gap[0]].strftime("%Y-%m-%d %H:%M")
            l4a["run"]["enddate"] = ldt_tower[gap[1]].strftime("%Y-%m-%d %H:%M")
            gfalternate_main(ds_tower, ds_alt, l4_info, called_by, label_tower_list=[label_tower])
            gfalternate_plotcoveragelines(ds_tower, l4_info, called_by)
            if not_enough_points: break

def gfalternate_createdataandstatsdict(ldt_tower, data_tower, attr_tower, l4a):
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
    label_tower = l4a["run"]["label_tower"]
    label_composite = l4a["run"]["label_composite"]
    data_dict["DateTime"] = {"data": ldt_tower}
    data_dict[label_tower] = {"attr": attr_tower,
                              "output_list": [label_tower, label_composite],
                              "data": data_tower}
    data_dict[label_composite] = {"data": numpy.ma.masked_all_like(data_tower),
                                  "fitcorr": numpy.ma.masked_all_like(data_tower),
                                  "attr": attr_tower}
    stat_dict[label_tower] = {"startdate": l4a["run"]["startdate"],
                              "enddate": l4a["run"]["enddate"]}
    stat_dict[label_composite] = {"startdate": l4a["run"]["startdate"],
                                  "enddate":l4a["run"]["enddate"]}
    return data_dict, stat_dict

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
    # plot the summary statistics
    #gfalternate_plotsummary(ds,alternate_info)
    # close any open plots
    if len(plt.get_fignums()) != 0:
        for i in plt.get_fignums():
            plt.close(i)
    # destroy the alternate GUI
    alt_gui.close()
    # write Excel spreadsheet with fit statistics
    pfp_io.xl_write_AlternateStats(alt_gui.ds4, alt_gui.l4_info)
    # put the return code into ds.returncodes
    alt_gui.ds4.returncodes["message"] = "normal"

def gfalternate_getalternatevaratmaxr(ds_tower, ds_alternate, l4a, mode="verbose"):
    """
    Purpose:
     Get a list of alternate variable names that are sorted based on correlation
     with the tower data.
    Usage:
    Side effects:
    Author: PRI
    Date: August 2014
    """
    # get a list of alternate variables for this tower variable
    label_tower = l4a["run"]["label_tower"]
    label_output = l4a["run"]["label_output"]
    startdate = l4a["run"]["startdate"]
    enddate = l4a["run"]["enddate"]
    ts = int(ds_tower.globalattributes["time_step"])
    ldt_tower = ds_tower.series["DateTime"]["Data"]
    si_tower = pfp_utils.GetDateIndex(ldt_tower, startdate, ts=ts)
    ei_tower = pfp_utils.GetDateIndex(ldt_tower, enddate, ts=ts)
    data_tower, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label_tower, si=si_tower, ei=ei_tower)
    # local pointers to the start and end indices
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    si_alternate = pfp_utils.GetDateIndex(ldt_alternate, startdate, ts=ts)
    ei_alternate = pfp_utils.GetDateIndex(ldt_alternate, enddate, ts=ts)
    # create an array for the correlations and a list for the alternate variables in order of decreasing correlation
    if "usevars" not in l4a["outputs"][label_output]:
        altvar_list = gfalternate_getalternatevarlist(ds_alternate, l4a["run"]["label_tower"])
    else:
        altvar_list = l4a["outputs"][label_output]["usevars"]
    r = numpy.zeros(len(altvar_list))
    # loop over the variables in the alternate file
    for idx, var in enumerate(altvar_list):
        # get the alternate data
        data_alternate, _, _ = pfp_utils.GetSeriesasMA(ds_alternate, var, si=si_alternate, ei=ei_alternate)
        l4a["run"]["gotminpoints_alternate"] = gfalternate_gotminpoints(data_alternate, l4a,
                                                                        label_tower, mode="quiet")
        if numpy.ma.count(data_alternate) > l4a["run"]["min_points"]:
            # check the lengths of the tower and alternate data are the same
            if len(data_alternate) != len(data_tower):
                msg = "gfalternate_getalternatevaratmaxr: alternate data length is " + str(len(data_alternate))
                logger.info(msg)
                msg = "gfalternate_getalternatevaratmaxr: tower data length is " + str(len(data_tower))
                logger.info(msg)
                raise ValueError('gfalternate_getalternatevaratmaxr: data_tower and data_alternate lengths differ')
            # put the correlation into the r array
            rval = numpy.ma.corrcoef(data_tower, data_alternate)[0, 1]
            if rval == "nan": rval = float(0)
        else:
            if mode!="quiet":
                msg = " getalternatevaratmaxr: not enough good data in alternate "+var
                logger.error(msg)
            rval = float(0)
        r[idx] = numpy.ma.filled(rval, float(c.missing_value))
    # save the correlation array for later plotting
    l4a["run"]["r"] = r
    # sort the correlation array and the alternate variable list
    idx = numpy.flipud(numpy.argsort(r))
    altvar_list_sorted = [altvar_list[j] for j in list(idx)]
    # return the name of the alternate variable that has the highest correlation with the tower data
    if l4a["outputs"][label_output]["source"].lower() == "access":
        altvar_list_sorted = altvar_list_sorted[0:1]
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

def gfalternate_getdataas2d(odt, data, l4a):
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
    ts = l4a["info"]["time_step"]
    nperday = l4a["gui"]["nperday"]
    si = 0
    while abs(odt[si].hour + float(odt[si].minute)/60 - float(ts)/60) > c.eps:
        si = si + 1
    ei = len(odt) - 1
    while abs(odt[ei].hour + float(odt[ei].minute)/60) > c.eps:
        ei = ei - 1
    data_wholedays = data[si: ei + 1]
    ndays = len(data_wholedays)/nperday
    return numpy.ma.reshape(data_wholedays, [ndays, nperday])

def gfalternate_getdielaverage(data_dict, l4a):
    odt = data_dict["DateTime"]["data"]
    label_tower = l4a["run"]["label_tower"]
    output_list = list(data_dict[label_tower]["output_list"])
    diel_avg = {}
    for label_output in output_list:
        diel_avg[label_output] = {}
        if "data" in data_dict[label_output].keys():
            data_2d = gfalternate_getdataas2d(odt, data_dict[label_output]["data"], l4a)
            diel_avg[label_output]["data"] = numpy.ma.average(data_2d, axis=0)
        if "fitcorr" in data_dict[label_output].keys():
            data_2d = gfalternate_getdataas2d(odt, data_dict[label_output]["fitcorr"], l4a)
            diel_avg[label_output]["fitcorr"] = numpy.ma.average(data_2d, axis=0)
    return diel_avg

def gfalternate_getfitcorrecteddata(data_dict, stat_dict, l4a):
    """
    Wrapper for the various methods of fitting the alternate data to the tower data.
    """
    if l4a["run"]["fit_type"].lower() == "ols":
        gfalternate_getolscorrecteddata(data_dict, stat_dict, l4a)
    if l4a["run"]["fit_type"].lower() == "ols_thru0":
        gfalternate_getolscorrecteddata(data_dict, stat_dict, l4a)
    if l4a["run"]["fit_type"].lower() == "mrev":
        gfalternate_getmrevcorrected(data_dict, stat_dict, l4a)
    if l4a["run"]["fit_type"].lower() == "replace":
        gfalternate_getreplacedata(data_dict, stat_dict, l4a)
    if l4a["run"]["fit_type"].lower() == "rma":
        gfalternate_getrmacorrecteddata(data_dict, stat_dict, l4a)
    if l4a["run"]["fit_type"].lower() == "odr":
        gfalternate_getodrcorrecteddata(data_dict, stat_dict, l4a)

def gfalternate_getlabeloutputlist(l4_info, label_tower):
    l4a = l4_info["GapFillFromAlternate"]
    l4m = l4_info["MergeSeries"]
    olist = [item for item in l4a["outputs"].keys() if l4a["outputs"][item]["target"] == label_tower]
    for item in l4m.keys():
        if label_tower in l4m[item].keys():
            mlist = l4m[item][label_tower]["source"]
    label_output_list = []
    for item in mlist:
        if item in olist: label_output_list.append(item)
    return label_output_list

def gfalternate_getcorrecteddata(ds_alternate, data_dict, stat_dict, l4a):
    label_output = l4a["run"]["label_output"]
    label_alternate = l4a["run"]["label_alternate"]
    if l4a["run"]["nogaps_tower"]:
        # tower data has no gaps
        stat_dict[label_output][label_alternate]["nLags"] = int(0)
        data_dict[label_output][label_alternate]["lagcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        stat_dict[label_output][label_alternate]["slope"] = float(0)
        stat_dict[label_output][label_alternate]["offset"] = float(0)
        stat_dict[label_output][label_alternate]["eqnstr"] = "No gaps in tower"
    elif not l4a["run"]["nogaps_tower"] and l4a["run"]["gotminpoints_both"]:
        # got enough good points common to both data series
        gfalternate_getlagcorrecteddata(ds_alternate, data_dict, stat_dict, l4a)
        gfalternate_getfitcorrecteddata(data_dict, stat_dict, l4a)
    elif not l4a["run"]["nogaps_tower"] and not l4a["run"]["gotminpoints_both"]:
        stat_dict[label_output][label_alternate]["nLags"] = int(0)
        data_dict[label_output][label_alternate]["lagcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        if l4a["run"]["fit_type"].lower() == "replace":
            gfalternate_getfitcorrecteddata(data_dict, stat_dict, l4a)
        else:
            data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.masked_all_like(data_dict[label_output][label_alternate]["data"])
            stat_dict[label_output][label_alternate]["slope"] = float(0)
            stat_dict[label_output][label_alternate]["offset"] = float(0)
            stat_dict[label_output][label_alternate]["eqnstr"] = "Too few points"
    else:
        msg = "getcorrecteddata: Unrecognised combination of logical tests"
        logger.error(msg)

def gfalternate_getlagcorrecteddata(ds_alternate, data_dict, stat_dict, l4a):
    label_tower = l4a["run"]["label_tower"]
    label_output = l4a["run"]["label_output"]
    label_alternate = l4a["run"]["label_alternate"]
    data_tower = data_dict[label_tower]["data"]
    data_alternate = data_dict[label_output][label_alternate]["data"]
    ldt_alternate = ds_alternate.series["DateTime"]["Data"]
    startdate = l4a["run"]["startdate"]
    enddate = l4a["run"]["enddate"]
    ts = l4a["info"]["time_step"]
    si_alternate = pfp_utils.GetDateIndex(ldt_alternate, startdate, ts=ts)
    ei_alternate = pfp_utils.GetDateIndex(ldt_alternate, enddate, ts=ts)
    if l4a["run"]["lag"].lower() == "yes":
        maxlags = l4a["gui"]["max_lags"]
        _, corr = pfp_ts.get_laggedcorrelation(data_tower, data_alternate, maxlags)
        nLags = numpy.argmax(corr) - l4a["gui"]["max_lags"]
        if nLags > l4a["gui"]["nperhr"]*6:
            logger.error("getlagcorrecteddata: lag is more than 6 hours for %s", label_tower)
        si_alternate = si_alternate - nLags
        ei_alternate = ei_alternate - nLags
        data_alternate, _, _ = pfp_utils.GetSeriesasMA(ds_alternate, label_alternate, si=si_alternate, ei=ei_alternate, mode="mirror")
        data_dict[label_output][label_alternate]["lagcorr"] = data_alternate
        stat_dict[label_output][label_alternate]["nLags"] = nLags
    else:
        data_dict[label_output][label_alternate]["lagcorr"] = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
        stat_dict[label_output][label_alternate]["nLags"] = int(0)

def gfalternate_getmrevcorrected(data_dict, stat_dict, l4a):
    """
    Fit alternate data to tower data by replacing means and equalising variance.
    """
    odt = data_dict["DateTime"]["data"]
    label_tower = l4a["run"]["label_tower"]
    label_output = l4a["run"]["label_output"]
    label_alternate = l4a["run"]["label_alternate"]
    # local copies of the data
    data_tower = numpy.ma.copy(data_dict[label_tower]["data"])
    data_alternate = numpy.ma.copy(data_dict[label_output][label_alternate]["data"])
    data_2d = gfalternate_getdataas2d(odt, data_tower, l4a)
    data_twr_hravg = numpy.ma.average(data_2d, axis=0)
    data_2d = gfalternate_getdataas2d(odt, data_alternate, l4a)
    data_alt_hravg = numpy.ma.average(data_2d, axis=0)
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

def gfalternate_getnumgoodpoints(data_tower, data_alternate):
    mask = numpy.ma.mask_or(data_tower.mask, data_alternate.mask, copy=True, shrink=False)
    return len(numpy.where(mask == False)[0])

def gfalternate_getodrcorrecteddata(data_dict, stat_dict, l4a):
    """
    Calculate the orthogonal distance regression fit between 2 1D arrays.
    """
    label_tower = l4a["run"]["label_tower"]
    label_output = l4a["run"]["label_output"]
    label_alternate = l4a["run"]["label_alternate"]
    y_in = numpy.ma.copy(data_dict[label_tower]["data"])
    x_in = numpy.ma.copy(data_dict[label_output][label_alternate]["lagcorr"])
    mask = numpy.ma.mask_or(x_in.mask, y_in.mask, copy=True, shrink=False)
    x = numpy.ma.compressed(numpy.ma.array(x_in ,mask=mask, copy=True))
    y = numpy.ma.compressed(numpy.ma.array(y_in, mask=mask, copy=True))
    # attempt an ODR fit
    linear = scipy.odr.Model(pfp_utils.linear_function)
    mydata = scipy.odr.Data(x, y)
    myodr = scipy.odr.ODR(mydata, linear, beta0=[1, 0])
    myoutput = myodr.run()
    odr_slope = myoutput.beta[0]
    odr_offset = myoutput.beta[1]
    data_dict[label_output][label_alternate]["fitcorr"] = odr_slope * x_in + odr_offset
    stat_dict[label_output][label_alternate]["slope"] = odr_slope
    stat_dict[label_output][label_alternate]["offset"] = odr_offset
    stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx + %.3f"%(odr_slope, odr_offset)

def gfalternate_getolscorrecteddata(data_dict, stat_dict, l4a):
    """
    Calculate the ordinary least squares fit between 2 1D arrays.
    """
    label_tower = l4a["run"]["label_tower"]
    label_output = l4a["run"]["label_output"]
    label_alternate = l4a["run"]["label_alternate"]
    y_in = numpy.ma.copy(data_dict[label_tower]["data"])
    x_in = numpy.ma.copy(data_dict[label_output][label_alternate]["lagcorr"])
    mask = numpy.ma.mask_or(x_in.mask,y_in.mask, copy=True, shrink=False)
    x = numpy.ma.compressed(numpy.ma.array(x_in, mask=mask, copy=True))
    y = numpy.ma.compressed(numpy.ma.array(y_in, mask=mask, copy=True))
    # attempt an OLS fit
    if l4a["run"]["fit_type"].lower() == "ols_thru0":
        resols = sm.OLS(y, x).fit()
        data_dict[label_output][label_alternate]["fitcorr"] = resols.params[0]*x_in
        stat_dict[label_output][label_alternate]["slope"] = resols.params[0]
        stat_dict[label_output][label_alternate]["offset"] = float(0)
        stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx"%(resols.params[0])
    else:
        resols = sm.OLS(y, sm.add_constant(x, prepend=False)).fit()
        if resols.params.shape[0] == 2:
            data_dict[label_output][label_alternate]["fitcorr"] = resols.params[0]*x_in+resols.params[1]
            stat_dict[label_output][label_alternate]["slope"] = resols.params[0]
            stat_dict[label_output][label_alternate]["offset"] = resols.params[1]
            stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx + %.3f"%(resols.params[0], resols.params[1])
        else:
            data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(x_in)
            stat_dict[label_output][label_alternate]["slope"] = float(0)
            stat_dict[label_output][label_alternate]["offset"] = float(0)
            stat_dict[label_output][label_alternate]["eqnstr"] = "OLS error, replaced"

def gfalternate_getoutputstatistics(data_dict, stat_dict, l4a):
    label_tower = l4a["run"]["label_tower"]
    output_list = list(data_dict[label_tower]["output_list"])
    if label_tower in output_list:
        output_list.remove(label_tower)
    for label in output_list:
        # OLS slope and offset
        if l4a["run"]["fit_type"] != "replace":
            x_in = numpy.ma.copy(data_dict[label]["fitcorr"])
            y_in = numpy.ma.copy(data_dict[label_tower]["data"])
            mask = numpy.ma.mask_or(x_in.mask, y_in.mask, copy=True, shrink=False)
            x = numpy.ma.compressed(numpy.ma.array(x_in, mask=mask, copy=True))
            y = numpy.ma.compressed(numpy.ma.array(y_in, mask=mask, copy=True))
            # get the array lengths
            nx = len(x)
            # attempt an OLS fit
            if nx >= l4a["run"]["min_points"]:
                if l4a["run"]["fit_type"].lower() == "ols":
                    resols = sm.OLS(y, sm.add_constant(x, prepend=False)).fit()
                    if resols.params.shape[0] == 2:
                        stat_dict[label]["slope"] = resols.params[0]
                        stat_dict[label]["offset"] = resols.params[1]
                        stat_dict[label]["eqnstr"] = "y = %.3fx + %.3f"%(resols.params[0], resols.params[1])
                    else:
                        stat_dict[label]["slope"] = float(0)
                        stat_dict[label]["offset"] = float(0)
                        stat_dict[label]["eqnstr"] = "OLS error"
                else:
                    resols = sm.OLS(y, x).fit()
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
        if num < 0: num = 0
        stat_dict[label]["No. filled"] = trap_masked_constant(num)
        # correlation coefficient
        r = numpy.ma.corrcoef(data_dict[label_tower]["data"], data_dict[label]["fitcorr"])
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
            stat_dict[label]["Var ratio"] = trap_masked_constant(var_tower/var_alt)
        else:
            stat_dict[label]["Var ratio"] = float(c.missing_value)
        # RMSE & NMSE
        error = (data_dict[label_tower]["data"]-data_dict[label]["fitcorr"])
        rmse = numpy.ma.sqrt(numpy.ma.average(error*error))
        stat_dict[label]["RMSE"] = trap_masked_constant(rmse)
        data_range = numpy.ma.maximum.reduce(data_dict[label_tower]["data"])-numpy.ma.minimum.reduce(data_dict[label_tower]["data"])
        if numpy.ma.is_masked(data_range) or abs(data_range) < c.eps:
            nmse = float(c.missing_value)
        else:
            nmse = rmse/data_range
        stat_dict[label]["NMSE"] = trap_masked_constant(nmse)
        # bias & fractional bias
        stat_dict[label]["Bias"] = trap_masked_constant(numpy.ma.average(error))
        norm_error = (error)/(0.5*(data_dict[label_tower]["data"]+data_dict[label]["fitcorr"]))
        stat_dict[label]["Frac Bias"] = trap_masked_constant(numpy.ma.average(norm_error))

def gfalternate_getreplacedata(data_dict, stat_dict, l4a):
    label_output = l4a["run"]["label_output"]
    label_alternate = l4a["run"]["label_alternate"]
    data_alternate = data_dict[label_output][label_alternate]["lagcorr"]
    data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(data_alternate)
    stat_dict[label_output][label_alternate]["slope"] = float(1)
    stat_dict[label_output][label_alternate]["offset"] = float(0)
    stat_dict[label_output][label_alternate]["eqnstr"] = "No OLS, replaced"

def gfalternate_getrmacorrecteddata(data_dict, stat_dict, l4a):
    """
    Calculate the ordinary least squares fit between 2 1D arrays.
    """
    label_tower = l4a["run"]["label_tower"]
    label_output = l4a["run"]["label_output"]
    label_alternate = l4a["run"]["label_alternate"]
    y_in = numpy.ma.copy(data_dict[label_tower]["data"])
    x_in = numpy.ma.copy(data_dict[label_output][label_alternate]["lagcorr"])
    mask = numpy.ma.mask_or(x_in.mask, y_in.mask, copy=True, shrink=False)
    x = numpy.ma.compressed(numpy.ma.array(x_in, mask=mask, copy=True))
    y = numpy.ma.compressed(numpy.ma.array(y_in, mask=mask, copy=True))
    # attempt an OLS fit
    if l4a["run"]["fit_type"].lower() == "ols_thru0":
        resols = sm.OLS(y, x).fit()
        rma_slope = resols.params[0]/numpy.sqrt(resols.rsquared)
        rma_offset = numpy.mean(y) - rma_slope * numpy.mean(x)
        data_dict[label_output][label_alternate]["fitcorr"] = rma_slope*x_in
        stat_dict[label_output][label_alternate]["slope"] = rma_slope
        stat_dict[label_output][label_alternate]["offset"] = float(0)
        stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx"%(rma_slope)
    else:
        resols = sm.OLS(y, sm.add_constant(x, prepend=False)).fit()
        if resols.params.shape[0] == 2:
            rma_slope = resols.params[0]/numpy.sqrt(resols.rsquared)
            rma_offset = numpy.mean(y) - rma_slope * numpy.mean(x)
            data_dict[label_output][label_alternate]["fitcorr"] = rma_slope*x_in+rma_offset
            stat_dict[label_output][label_alternate]["slope"] = rma_slope
            stat_dict[label_output][label_alternate]["offset"] = rma_offset
            stat_dict[label_output][label_alternate]["eqnstr"] = "y = %.3fx + %.3f"%(rma_slope, rma_offset)
        else:
            data_dict[label_output][label_alternate]["fitcorr"] = numpy.ma.copy(x_in)
            stat_dict[label_output][label_alternate]["slope"] = float(0)
            stat_dict[label_output][label_alternate]["offset"] = float(0)
            stat_dict[label_output][label_alternate]["eqnstr"] = "RMA error, replaced"

def gfalternate_gotdataforgaps(data, data_alternate, l4a, mode="verbose"):
    """
    Returns true if the alternate series has data where the composite series has gaps.
    """
    return_code = True
    ind = numpy.where((numpy.ma.getmaskarray(data) == True) & (numpy.ma.getmaskarray(data_alternate) == False))[0]
    if len(ind) == 0:
        if mode == "verbose":
            label_alternate = l4a["run"]["label_alternate"]
            msg = " Alternate series " + label_alternate + " has nothing to contribute"
            logger.info(msg)
        return_code = False
    return return_code

def gfalternate_gotnogaps(data, label, mode="verbose"):
    """
    Returns true if the data series has no gaps, false if there are gaps
    """
    return_code = True
    if numpy.ma.count_masked(data) == 0:
        if mode == "verbose":
            msg = " No gaps in " + label
            logger.info(msg)
        return_code = True
    else:
        return_code = False
    return return_code

def gfalternate_gotminpoints(data, l4a, label, mode="verbose"):
    """
    Returns true if data contains more than the minimum number of points required
    or data contains less than the minimum number but the fit type is replace.
    """
    return_code = True
    if numpy.ma.count(data) < l4a["run"]["min_points"]:
        if mode == "verbose":
            msg = " Less than " + str(l4a["gui"]["min_percent"]) + " % data in series "
            msg = msg + label + ", skipping ..."
            logger.info(msg)
            msg = "gotminpoints: " + label + " " + str(numpy.ma.count(data))
            msg = msg + " " + str(l4a["run"]["min_points"])
            logger.info(msg)
        return_code = False
    return return_code

def gfalternate_gotminpointsboth(data_tower, data_alternate, l4a, label_tower, label_alternate, mode="verbose"):
    return_code = True
    mask = numpy.ma.mask_or(numpy.ma.getmaskarray(data_tower), numpy.ma.getmaskarray(data_alternate),
                            copy=True, shrink=False)
    if len(numpy.where(mask == False)[0]) < l4a["run"]["min_points"]:
        if mode != "quiet":
            msg = " Less than " + str(l4a["run"]["min_percent"]) + " % good data common to both series "
            logger.info(msg)
            msg = "gotminpointsboth: " + label_tower + " " + str(numpy.ma.count(data_tower))
            msg = msg + " " + str(l4a["run"]["min_points"])
            logger.info(msg)
            msg = "gotminpointsboth: " + label_alternate + " " + str(numpy.ma.count(data_alternate))
            msg = msg + " " + str(l4a["run"]["min_points"])
            logger.info(msg)
        return_code = False
    return return_code

def gfalternate_initplot(data_dict, l4a, **kwargs):
    pd = {"margin_bottom":0.075, "margin_top":0.05, "margin_left":0.075, "margin_right":0.05,
          "xy_height":0.25, "xy_width":0.20, "xyts_space":0.05, "xyxy_space":0.05, "ts_width":0.9,
          "text_left":0.675, "num_left":0.825, "row_bottom":0.35, "row_space":0.030}
    # calculate bottom of the first time series and the height of the time series plots
    label_tower = l4a["run"]["label_tower"]
    label_composite = l4a["run"]["label_composite"]
    output_list = list(data_dict[label_tower]["output_list"])
    for item in [label_tower, label_composite]:
        if item in output_list: output_list.remove(item)
    nts = len(output_list) + 1
    pd["ts_bottom"] = pd["margin_bottom"] + pd["xy_height"] + pd["xyts_space"]
    pd["ts_height"] = (1.0 - pd["margin_top"] - pd["ts_bottom"])/nts
    for key, value in kwargs.iteritems():
        pd[key] = value
    return pd

def gfalternate_loadoutputdata(ds_tower, data_dict, l4a):
    ldt_tower = ds_tower.series["DateTime"]["Data"]
    label_output = l4a["run"]["label_output"]
    label_composite = l4a["run"]["label_composite"]
    label_alternate = l4a["run"]["label_alternate"]
    ts = l4a["info"]["time_step"]
    si = pfp_utils.GetDateIndex(ldt_tower, l4a["run"]["startdate"], ts=ts, default=0)
    ei = pfp_utils.GetDateIndex(ldt_tower, l4a["run"]["enddate"], ts=ts, default=len(ldt_tower))
    if l4a["gui"]["overwrite"]:
        ind1 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"]) == False)[0]
    else:
        ind1 = numpy.where((numpy.ma.getmaskarray(data_dict[label_output]["data"]) == True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"]) == False))[0]
    data_dict[label_output]["data"][ind1] = data_dict[label_output][label_alternate]["data"][ind1]
    if l4a["gui"]["overwrite"]:
        ind2 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False)[0]
    else:
        ind2 = numpy.where((numpy.ma.getmaskarray(data_dict[label_output]["fitcorr"]) == True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False))[0]
    data_dict[label_output]["fitcorr"][ind2] = data_dict[label_output][label_alternate]["fitcorr"][ind2]
    if l4a["gui"]["overwrite"]:
        ind3 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"]) == False)[0]
    else:
        ind3 = numpy.where((numpy.ma.getmaskarray(data_dict[label_composite]["data"]) == True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["data"]) == False))[0]
    data_dict[label_composite]["data"][ind3] = data_dict[label_output][label_alternate]["data"][ind3]
    if l4a["gui"]["overwrite"]:
        ind4 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False)[0]
    else:
        ind4 = numpy.where((numpy.ma.getmaskarray(data_dict[label_composite]["fitcorr"]) == True)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False))[0]
    data_dict[label_composite]["fitcorr"][ind4] = data_dict[label_output][label_alternate]["fitcorr"][ind4]
    if l4a["gui"]["overwrite"]:
        ind5 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False)[0]
    else:
        ind5 = numpy.where((abs(ds_tower.series[label_composite]["Data"][si:ei+1]-float(c.missing_value)) < c.eps)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False))[0]
    ds_tower.series[label_composite]["Data"][si:ei+1][ind5] = numpy.ma.filled(data_dict[label_output][label_alternate]["fitcorr"][ind5], c.missing_value)
    ds_tower.series[label_composite]["Flag"][si:ei+1][ind5] = numpy.int32(20)
    if l4a["gui"]["overwrite"]:
        ind6 = numpy.where(numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False)[0]
    else:
        ind6 = numpy.where((abs(ds_tower.series[label_output]["Data"][si:ei+1]-float(c.missing_value)) < c.eps)&
                           (numpy.ma.getmaskarray(data_dict[label_output][label_alternate]["fitcorr"]) == False))[0]
    ds_tower.series[label_output]["Data"][si:ei+1][ind6] = numpy.ma.filled(data_dict[label_output][label_alternate]["fitcorr"][ind6], c.missing_value)
    ds_tower.series[label_output]["Flag"][si:ei+1][ind6] = numpy.int32(20)

def gfalternate_main(ds_tower, ds_alt, l4_info, called_by, label_tower_list=None):
    """
    This is the main routine for using alternate data to gap fill drivers.
    """
    l4a = l4_info[called_by]
    mode = "quiet" #"quiet"  #"verbose"
    ts = int(ds_tower.globalattributes["time_step"])
    startdate = l4a["run"]["startdate"]
    enddate = l4a["run"]["enddate"]
    logger.info(" Gap fill with alternate: " + startdate + " to " + enddate)
    # get local pointer to the datetime series
    dt_tower = ds_tower.series["DateTime"]["Data"]
    si_tower = pfp_utils.GetDateIndex(dt_tower, startdate, ts=ts, default=0)
    ei_tower = pfp_utils.GetDateIndex(dt_tower, enddate, ts=ts, default=len(dt_tower)-1)
    ldt_tower = dt_tower[si_tower:ei_tower + 1]
    # now loop over the variables to be gap filled using the alternate data
    if label_tower_list == None:
        label_tower_list = l4a["gui"]["series_list"]
    for label_tower in label_tower_list:
        l4a["run"]["label_tower"] = label_tower
        label_composite = label_tower + "_composite"
        l4a["run"]["label_composite"] = label_composite
        # read the tower data and check for gaps
        data_tower, _, attr_tower = pfp_utils.GetSeriesasMA(ds_tower, label_tower, si=si_tower, ei=ei_tower)
        l4a["run"]["min_points"] = int(len(data_tower)*l4a["gui"]["min_percent"]/100)
        # check to see if we have any gaps to fill
        l4a["run"]["nogaps_tower"] = gfalternate_gotnogaps(data_tower, label_tower, mode=mode)
        # check to see if we have more than the minimum number of points
        l4a["run"]["gotminpoints_tower"] = gfalternate_gotminpoints(data_tower, l4a, label_tower, mode=mode)
        # initialise a dictionary to hold the data
        data_dict, stat_dict = gfalternate_createdataandstatsdict(ldt_tower, data_tower, attr_tower, l4a)
        # get a list of the output names for this tower series
        label_output_list = gfalternate_getlabeloutputlist(l4_info, label_tower)
        # loop over the outputs for this tower series
        for label_output in label_output_list:
            l4a["run"]["label_output"] = label_output
            l4a["run"]["alternate_name"] = l4a["outputs"][label_output]["alternate_name"]
            # update the alternate_info dictionary
            gfalternate_update_alternate_info(l4a)
            # update the dictionaries
            stat_dict[label_output] = {"startdate": startdate,
                                       "enddate": enddate}
            data_dict[label_output] = {"data": numpy.ma.masked_all_like(data_tower),
                                       "fitcorr": numpy.ma.masked_all_like(data_tower),
                                       "attr": attr_tower,
                                       "source": l4a["outputs"][label_output]["source"]}
            # get a local pointer to the alternate data structure
            ds_alternate = ds_alt[l4a["outputs"][label_output]["file_name"]]
            ldt_alternate = ds_alternate.series["DateTime"]["Data"]
            # start and end idices for this time range in the alternate data
            si_alternate = pfp_utils.GetDateIndex(ldt_alternate, startdate, ts=ts, default=0)
            ei_alternate = pfp_utils.GetDateIndex(ldt_alternate, enddate, ts=ts, default=len(ldt_alternate)-1)
            # get the alternate series that has the highest correlation with the tower data
            label_alternate_list = gfalternate_getalternatevaratmaxr(ds_tower, ds_alternate, l4a, mode=mode)
            # loop over alternate variables
            for label_alternate in label_alternate_list:
                l4a["run"]["label_alternate"] = label_alternate
                # get the raw alternate data
                data_alternate, _, attr_alternate = pfp_utils.GetSeriesasMA(ds_alternate, label_alternate, si=si_alternate, ei=ei_alternate)
                # check this alternate variable to see if there are enough points
                l4a["run"]["gotminpoints_alternate"] = gfalternate_gotminpoints(data_alternate, l4a, label_alternate, mode=mode)
                l4a["run"]["gotdataforgaps_alternate"] = gfalternate_gotdataforgaps(data_dict[label_output]["data"], data_alternate, l4a, mode=mode)
                l4a["run"]["gotminpoints_both"] = gfalternate_gotminpointsboth(data_tower, data_alternate, l4a, label_tower, label_alternate, mode=mode)
                # update the data and sata dictionaries
                stat_dict[label_output][label_alternate] = {"startdate": startdate,
                                                            "enddate": enddate}
                if label_output not in data_dict[label_tower]["output_list"]:
                    data_dict[label_tower]["output_list"].append(label_output)
                data_dict[label_output][label_alternate] = {"data": data_alternate,
                                                            "attr": attr_alternate}
                gfalternate_getcorrecteddata(ds_alternate, data_dict, stat_dict, l4a)
                gfalternate_loadoutputdata(ds_tower, data_dict, l4a)
                # check to see if we have alternate data for this whole period, if so there is no reason to continue
                ind_tower = numpy.where(abs(ds_tower.series[label_output]["Data"][si_tower:ei_tower+1]-float(c.missing_value)) < c.eps)[0]
                if len(ind_tower) == 0:
                    break
        # we have completed the loop over the alternate data for this output
        # now do the statistics, diurnal average and daily averages for this output
        gfalternate_getoutputstatistics(data_dict, stat_dict, l4a)
        for label_output in label_output_list:
            for result in l4a["outputs"][label_output]["results"]:
                l4a["outputs"][label_output]["results"][result].append(stat_dict[label_output][result])
        if l4a["run"]["nogaps_tower"]:
            if l4a["gui"]["show_all"]:
                pass
            else:
                continue
        # plot the gap filled data
        pd = gfalternate_initplot(data_dict, l4a)
        diel_avg = gfalternate_getdielaverage(data_dict, l4a)
        # reserve figure number 0 for the coverage lines/progress plot
        gfalternate_plotcomposite(data_dict, stat_dict, diel_avg, l4a, pd)

def gfalternate_plotcomposite(data_dict, stat_dict, diel_avg, l4a, pd):
    # set up some local pointers
    label_tower = l4a["run"]["label_tower"]
    label_composite = l4a["run"]["label_composite"]
    time_step = l4a["info"]["time_step"]
    points_test = numpy.ma.count(data_dict[label_tower]["data"]) < l4a["run"]["min_points"]
    fit_test = l4a["run"]["fit_type"] != "replace"
    if points_test and fit_test: return
    # turn on interactive plotting
    if l4a["gui"]["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    # create the figure canvas or re-use existing
    if plt.fignum_exists(1):
        fig = plt.figure(1)
        plt.clf()
    else:
        fig = plt.figure(1, figsize=(13, 8))
    fig.canvas.set_window_title(label_tower)
    # get the plot title string
    title = l4a["info"]["site_name"] + " : Comparison of tower and alternate data for " + label_tower
    plt.figtext(0.5, 0.96, title, ha='center', size=16)
    # bottom row of XY plots: scatter plot of 30 minute data
    rect1 = [0.10, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    xyscatter = plt.axes(rect1)
    xyscatter.set_ylabel("Tower (" + data_dict[label_tower]["attr"]["units"] + ")")
    xyscatter.set_xlabel("Alt (" + data_dict[label_composite]["attr"]["units"] + ")")
    text = str(time_step) + " minutes"
    xyscatter.text(0.6, 0.075, text, fontsize=10, horizontalalignment="left",
                   transform=xyscatter.transAxes)
    xyscatter.plot(data_dict[label_composite]["fitcorr"], data_dict[label_tower]["data"], 'b.')
    # trap caes where all fitted, corrected data is masked
    mamin = numpy.ma.min(data_dict[label_composite]["fitcorr"])
    mamax = numpy.ma.max(data_dict[label_composite]["fitcorr"])
    if not numpy.ma.is_masked(mamin) and not numpy.ma.is_masked(mamax):
        xfit = numpy.array([mamin,mamax])
        yfit = xfit*stat_dict[label_composite]["slope"] + stat_dict[label_composite]["offset"]
        xyscatter.plot(xfit, yfit, 'g--', linewidth=3)
        xyscatter.text(0.5, 0.9, stat_dict[label_composite]["eqnstr"], fontsize=8,
                       horizontalalignment='center', transform=xyscatter.transAxes, color='green')
    # bottom row of XY plots: scatter plot of diurnal averages
    ind = numpy.arange(l4a["gui"]["nperday"])/float(l4a["gui"]["nperhr"])
    rect2 = [0.40, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    diel_axes = plt.axes(rect2)
    diel_axes.plot(ind, diel_avg[label_composite]["fitcorr"], 'g-', label="Alt (fit)")
    diel_axes.plot(ind, diel_avg[label_composite]["data"], 'b-', label="Alt")
    diel_axes.set_ylabel(label_tower + " (" + data_dict[label_tower]["attr"]["units"] + ")")
    diel_axes.set_xlim(0, 24)
    diel_axes.xaxis.set_ticks([0, 6, 12, 18, 24])
    diel_axes.set_xlabel('Hour')
    diel_axes.plot(ind, diel_avg[label_tower]["data"], 'ro', label="Tower")
    diel_axes.legend(loc='upper right', frameon=False, prop={'size':8})
    # top row: time series
    ts_axes = []
    rect3 = [pd["margin_left"], pd["ts_bottom"], pd["ts_width"], pd["ts_height"]]
    ts_axes.append(plt.axes(rect3))
    ts_axes[0].plot(data_dict["DateTime"]["data"], data_dict[label_tower]["data"], 'ro', label="Tower")
    ts_axes[0].plot(data_dict["DateTime"]["data"], data_dict[label_composite]["fitcorr"], 'g-', label="Alt (fitted)")
    ts_axes[0].set_xlim(data_dict["DateTime"]["data"][0], data_dict["DateTime"]["data"][-1])
    ts_axes[0].legend(loc='upper right', frameon=False, prop={'size':10})
    ts_axes[0].set_ylabel(label_tower + " (" + data_dict[label_tower]["attr"]["units"] + ")")
    output_list = list(data_dict[label_tower]["output_list"])
    for item in [label_tower, label_composite]:
        if item in output_list: output_list.remove(item)
    for n, label_output in enumerate(output_list):
        n = n + 1
        source = data_dict[label_output]["source"]
        this_bottom = pd["ts_bottom"] + n*pd["ts_height"]
        rect = [pd["margin_left"], this_bottom, pd["ts_width"], pd["ts_height"]]
        ts_axes.append(plt.axes(rect, sharex=ts_axes[0]))
        ts_axes[n].plot(data_dict["DateTime"]["data"], data_dict[label_output]["data"], 'b-', label=source)
        plt.setp(ts_axes[n].get_xticklabels(), visible=False)
        ts_axes[n].legend(loc='upper right', frameon=False, prop={'size':10})
        ts_axes[n].set_ylabel(label_tower + " (" + data_dict[label_tower]["attr"]["units"] + ")")
    # write the comparison statistics
    stats_list = ["Var (Alt)", "Var (Tower)", "RMSE", "Bias", "r", "No. filled", "No. points"]
    for n, item in enumerate(stats_list):
        row_posn = pd["margin_bottom"] + n*pd["row_space"]
        plt.figtext(pd["text_left"], row_posn, item)
        plt.figtext(pd["num_left"], row_posn, '%.4g'%(stat_dict[label_composite][item]))
    # save a hard copy of the plot
    sdt = data_dict["DateTime"]["data"][0].strftime("%Y%m%d")
    edt = data_dict["DateTime"]["data"][-1].strftime("%Y%m%d")
    figname = l4a["info"]["site_name"].replace(" ", "") + "_Alternate_" + label_tower
    figname = figname + "_" + sdt + "_" + edt + '.png'
    figname = os.path.join(l4a["info"]["plot_path"], figname)
    fig.savefig(figname, format='png')
    # draw the plot on the screen
    if l4a["gui"]["show_plots"]:
        plt.draw()
        #plt.pause(1)
        mypause(1)
        plt.ioff()
    else:
        plt.ion()

def mypause(interval):
    backend = plt.rcParams['backend']
    if backend in matplotlib.rcsetup.interactive_bk:
        figManager = matplotlib._pylab_helpers.Gcf.get_active()
        if figManager is not None:
            canvas = figManager.canvas
            if canvas.figure.stale:
                canvas.draw()
            canvas.start_event_loop(interval)
            return

def gfalternate_plotcoveragelines(ds_tower, l4_info, called_by):
    """
    Purpose:
     Plot a line representing the coverage of variables being gap filled.
    Usage:
    Author: PRI
    Date: Back in the day
    """
    # local pointer to l4_info["GapFillFromAlternate"]
    l4ia = l4_info[called_by]
    # local pointer to datetime
    ldt = ds_tower.series["DateTime"]["Data"]
    # get the site name and the start and end date
    site_name = ds_tower.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    # list of targets to plot
    targets = [l4ia["outputs"][output]["target"] for output in l4ia["outputs"].keys()]
    targets = list(set(targets))
    ylabel_list = [""] + targets + [""]
    ylabel_right_list = [""]
    colors = ["blue", "red", "green", "yellow", "magenta", "black", "cyan", "brown"]
    xsize = 15.0
    ysize = max([len(targets)*0.2, 1])
    plt.ion()
    if plt.fignum_exists(0):
        fig = plt.figure(0)
        plt.clf()
        ax1 = plt.subplot(111)
    else:
        fig = plt.figure(0, figsize=(xsize, ysize))
        ax1 = plt.subplot(111)
    title = "Coverage: " + site_name + " " + start_date + " to " + end_date
    fig.canvas.set_window_title(title)
    plt.ylim([0, len(targets) + 1])
    plt.xlim([ldt[0], ldt[-1]])
    for label, n in zip(targets, range(1, len(targets) + 1)):
        data_series, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label)
        percent = 100*numpy.ma.count(data_series)/len(data_series)
        ylabel_right_list.append("{0:.0f}%".format(percent))
        ind_series = numpy.ma.ones(len(data_series))*float(n)
        ind_series = numpy.ma.masked_where(numpy.ma.getmaskarray(data_series) == True, ind_series)
        plt.plot(ldt, ind_series, color=colors[numpy.mod(n, 8)], linewidth=1)
        if label+"_composite" in ds_tower.series.keys():
            data_composite, _, _ = pfp_utils.GetSeriesasMA(ds_tower, label+"_composite")
            ind_composite = numpy.ma.ones(len(data_composite))*float(n)
            ind_composite = numpy.ma.masked_where(numpy.ma.getmaskarray(data_composite) == True, ind_composite)
            plt.plot(ldt, ind_composite, color=colors[numpy.mod(n,8)], linewidth=4)
    ylabel_posn = range(0, len(targets)+2)
    pylab.yticks(ylabel_posn, ylabel_list)
    ylabel_right_list.append("")
    ax2 = ax1.twinx()
    pylab.yticks(ylabel_posn, ylabel_right_list)
    fig.tight_layout()
    plt.draw()
    plt.ioff()

def gfalternate_quit(alt_gui):
    """ Quit the GapFillFromAlternate GUI."""
    # put the return code into ds.returncodes
    alt_gui.ds4.returncodes["message"] = "quit"
    alt_gui.ds4.returncodes["value"] = 1
    # destroy the alternate GUI
    alt_gui.close()

def gfalternate_run_interactive(alt_gui):
    """
    Purpose:
     Gets settings from the GapFillFromAlternate GUI and loads them
     into the l4_info["gui"] dictionary
    Usage:
     Called when the "Run" button is clicked.
    Side effects:
     Loads settings into the l4_info["gui"] dictionary.
    Author: PRI
    Date: Re-written July 2019
    """
    # local pointers to useful things
    ds_tower = alt_gui.ds4
    ds_alt = alt_gui.ds_alt
    called_by = alt_gui.called_by
    l4_info = alt_gui.l4_info
    l4a = l4_info[called_by]
    # populate the l4_info["gui"] dictionary with things that will be useful
    ts = int(ds_tower.globalattributes["time_step"])
    l4a["gui"]["nperhr"] = int(float(60)/ts + 0.5)
    l4a["gui"]["nperday"] = int(float(24)*l4a["gui"]["nperhr"] + 0.5)
    l4a["gui"]["max_lags"] = int(float(12)*l4a["gui"]["nperhr"] + 0.5)
    # window period length
    if str(alt_gui.radioButtons.checkedButton().text()) == "Manual":
        l4a["gui"]["period_option"] = 1
    elif str(alt_gui.radioButtons.checkedButton().text()) == "Months":
        l4a["gui"]["period_option"] = 2
        l4a["gui"]["number_months"] = int(alt_gui.lineEdit_NumberMonths.text())
    elif str(alt_gui.radioButtons.checkedButton().text()) == "Days":
        l4a["gui"]["period_option"] = 3
        l4a["gui"]["number_days"] = int(alt_gui.lineEdit_NumberDays.text())
    # plot settings
    l4a["gui"]["overwrite"] = alt_gui.checkBox_Overwrite.isChecked()
    l4a["gui"]["show_plots"] = alt_gui.checkBox_ShowPlots.isChecked()
    l4a["gui"]["show_all"] = alt_gui.checkBox_PlotAll.isChecked()
    # auto-complete settings
    l4a["gui"]["auto_complete"] = alt_gui.checkBox_AutoComplete.isChecked()
    l4a["gui"]["autoforce"] = False
    # minimum percentage of good data required
    l4a["gui"]["min_percent"] = max(int(str(alt_gui.lineEdit_MinPercent.text())),1)
    # get the start and end datetimes entered in the alternate GUI
    if len(str(alt_gui.lineEdit_StartDate.text())) != 0:
        l4a["gui"]["startdate"] = str(alt_gui.lineEdit_StartDate.text())
    else:
        l4a["gui"]["startdate"] = l4a["info"]["startdate"]
    if len(str(alt_gui.lineEdit_EndDate.text())) != 0:
        l4a["gui"]["enddate"] = str(alt_gui.lineEdit_EndDate.text())
    else:
        l4a["gui"]["enddate"] = l4a["info"]["enddate"]
    # now do the work
    gfalternate_run(ds_tower, ds_alt, l4_info, called_by)
    return

def gfalternate_run(ds_tower, ds_alt, l4_info, called_by):
    """ Run the GapFillFromAlternate GUI."""
    l4a = l4_info[called_by]
    # get a list of target variables
    series_list = [l4a["outputs"][item]["target"] for item in l4a["outputs"].keys()]
    l4a["gui"]["series_list"] = sorted(list(set(series_list)))
    logger.info(" Gap filling %s using alternate data", l4a["gui"]["series_list"])
    # initialise the l4_info["run"] dictionary
    l4a["run"] = {"startdate": l4a["gui"]["startdate"],
                  "enddate": l4a["gui"]["enddate"]}
    # run the main gap filling routine depending on window period
    if l4a["gui"]["period_option"] == 1:
        # manual run, window specified in GUI start and end datetime boxes
        logger.info(" Starting manual run ...")
        gfalternate_main(ds_tower, ds_alt, l4_info, called_by)
        if l4a["info"]["call_mode"] == "interactive":
            gfalternate_plotcoveragelines(ds_tower, l4_info, called_by)
        logger.info(" Finished manual run ...")
    elif l4a["gui"]["period_option"] == 2:
        # automated run with window length in months
        logger.info("Starting auto (months) run ...")
        startdate = dateutil.parser.parse(l4a["run"]["startdate"])
        enddate = startdate + dateutil.relativedelta.relativedelta(months=l4a["gui"]["number_months"])
        enddate = min([dateutil.parser.parse(l4a["info"]["enddate"]), enddate])
        l4a["run"]["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        while startdate < enddate:
            gfalternate_main(ds_tower, ds_alt, l4_info, called_by)
            if l4a["info"]["call_mode"] == "interactive":
                gfalternate_plotcoveragelines(ds_tower, l4_info, called_by)
            startdate = enddate
            l4a["run"]["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            enddate = startdate + dateutil.relativedelta.relativedelta(months=l4a["gui"]["number_months"])
            enddate = min([dateutil.parser.parse(l4a["info"]["enddate"]), enddate])
            l4a["run"]["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # fill long gaps with autocomplete
        gfalternate_autocomplete(ds_tower, ds_alt, l4_info, called_by)
        logger.info(" Finished auto (months) run ...")
    elif l4a["gui"]["period_option"] == 3:
        # automated run with window length in days
        logger.info("Starting auto (days) run ...")
        # get the start datetime entered in the alternate GUI
        startdate = dateutil.parser.parse(l4a["run"]["startdate"])
        # get the end datetime from the start datetime
        enddate = startdate + dateutil.relativedelta.relativedelta(days=l4a["gui"]["number_days"])
        # clip end datetime to last datetime in tower file
        enddate = min([dateutil.parser.parse(l4a["info"]["enddate"]), enddate])
        l4a["run"]["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        while startdate < enddate:
            gfalternate_main(ds_tower, ds_alt, l4_info, called_by)
            if l4a["info"]["call_mode"] == "interactive":
                gfalternate_plotcoveragelines(ds_tower, l4_info, called_by)
            startdate = enddate
            l4a["run"]["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            enddate = startdate + dateutil.relativedelta.relativedelta(days=l4a["gui"]["number_days"])
            enddate = min([dateutil.parser.parse(l4a["info"]["enddate"]), enddate])
            l4a["run"]["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        gfalternate_autocomplete(ds_tower, ds_alt, l4_info, called_by)
        logger.info(" Finished auto (days) run ...")
    else:
        logger.error("GapFillFromAlternate: unrecognised period option")

def gfalternate_update_alternate_info(l4a):
    """Update the l4_info dictionary."""
    label_output = l4a["run"]["label_output"]
    l4a["run"]["fit_type"] = l4a["outputs"][label_output]["fit_type"]
    l4a["run"]["lag"] = l4a["outputs"][label_output]["lag"]
    # autoforce is set true in gfalternate_autocomplete if there is not enough good points
    # in the tower data for the whole time series, in this case we will use the alternate
    # data "as is" by forcing a "replace" with no lag correction.
    if l4a["gui"]["autoforce"]:
        l4a["run"]["min_points"] = 0
        l4a["run"]["fit_type"] = "replace"
        l4a["run"]["lag"] = "no"

def trap_masked_constant(num):
    if numpy.ma.is_masked(num):
        num = float(c.missing_value)
    return num
