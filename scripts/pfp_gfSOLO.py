# standard modules
import csv
import datetime
import logging
import os
import platform
import subprocess
# 3rd party modules
import dateutil
import numpy
import matplotlib
import matplotlib.dates as mdt
import matplotlib.pyplot as plt
import pylab
# PFP modules
import constants as c
import pfp_cfg
import pfp_ck
import pfp_gf
import pfp_io
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

# functions for GapFillUsingSOLO
def GapFillUsingSOLO(main_gui, ds, l5_info, called_by):
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
    ds.returncodes["value"] = 0
    ds.returncodes["message"] = "normal"
    # get the SOLO information
    solo = l5_info[called_by]
    # check the SOLO drivers for missing data
    pfp_gf.CheckDrivers(solo, ds)
    if ds.returncodes["value"] != 0:
        return ds
    if solo["info"]["call_mode"].lower() == "interactive":
        # put up a plot of the data coverage at L4
        gfSOLO_plotcoveragelines(ds, solo)
        # call the GapFillUsingSOLO GUI
        gfSOLO_gui(main_gui, ds, solo)
    #else:
        #gfSOLO_run_nogui(ds, info)

def  gfSOLO_gui(main_gui, ds, solo):
    """ Display the SOLO GUI and wait for the user to finish."""
    # add the data structures and the solo dictionary to self
    main_gui.solo_gui.ds = ds
    main_gui.solo_gui.solo = solo
    main_gui.solo_gui.edit_cfg = main_gui.tabs.tab_dict[main_gui.tabs.tab_index_running]
    main_gui.solo_gui.setWindowTitle(solo["info"]["called_by"])
    # put up the start and end dates
    start_date = ds.series["DateTime"]["Data"][0].strftime("%Y-%m-%d %H:%M")
    end_date = ds.series["DateTime"]["Data"][-1].strftime("%Y-%m-%d %H:%M")
    main_gui.solo_gui.label_DataStartDate_value.setText(start_date)
    main_gui.solo_gui.label_DataEndDate_value.setText(end_date)
    # set the default period and auto-complete state
    # NOTE: auto-complete should only be set if no long gaps detected
    if solo["info"]["called_by"] == "GapFillLongSOLO":
        main_gui.solo_gui.setWindowTitle("Gap fill using SOLO (long gaps)")
        main_gui.solo_gui.radioButton_Manual.setChecked(True)
        main_gui.solo_gui.lineEdit_MinPercent.setText("25")
        main_gui.solo_gui.lineEdit_Nodes.setText("Auto")
        main_gui.solo_gui.checkBox_AutoComplete.setChecked(True)
    elif solo["info"]["called_by"] == "GapFillUsingSOLO":
        main_gui.solo_gui.setWindowTitle("Gap fill using SOLO (short gaps)")
        main_gui.solo_gui.radioButton_NumberMonths.setChecked(True)
        main_gui.solo_gui.lineEdit_NumberMonths.setText("2")
        main_gui.solo_gui.lineEdit_MinPercent.setText("25")
        main_gui.solo_gui.lineEdit_Nodes.setText("Auto")
        auto_complete = solo["gui"]["auto_complete"]
        main_gui.solo_gui.checkBox_AutoComplete.setChecked(auto_complete)
    elif solo["info"]["called_by"] == "ERUsingSOLO":
        main_gui.solo_gui.setWindowTitle("ER using SOLO")
        main_gui.solo_gui.radioButton_Manual.setChecked(True)
        main_gui.solo_gui.lineEdit_Nodes.setText("1")
        main_gui.solo_gui.lineEdit_MinPercent.setText("10")
        main_gui.solo_gui.checkBox_AutoComplete.setChecked(True)
    # display the SOLO GUI
    main_gui.solo_gui.show()
    main_gui.solo_gui.exec_()

def gfSOLO_autocomplete(ds, solo):
    """
    Purpose:
     Gap fill long gaps.
    """
    if not solo["gui"]["auto_complete"]:
        return
    ldt = ds.series["DateTime"]["Data"]
    nRecs = len(ldt)
    for output in solo["outputs"].keys():
        not_enough_points = False
        target = solo["outputs"][output]["target"]
        data_solo, _, _ = pfp_utils.GetSeriesasMA(ds, output)
        if numpy.ma.count(data_solo) == 0:
            continue
        mask_solo = numpy.ma.getmaskarray(data_solo)
        gapstartend = pfp_utils.contiguous_regions(mask_solo)
        data_obs, _, _ = pfp_utils.GetSeriesasMA(ds, target)
        for si_gap, ei_gap in gapstartend:
            min_points = int((ei_gap-si_gap)*solo["gui"]["min_percent"]/100)
            num_good_points = numpy.ma.count(data_obs[si_gap: ei_gap])
            while num_good_points < min_points:
                si_gap = max([0, si_gap - solo["info"]["nperday"]])
                ei_gap = min([nRecs-1, ei_gap + solo["info"]["nperday"]])
                if si_gap == 0 and ei_gap == nRecs-1:
                    msg = " Unable to find enough good points in target " + target
                    logger.error(msg)
                    not_enough_points = True
                if not_enough_points:
                    break
                min_points = int((ei_gap-si_gap)*solo["gui"]["min_percent"]/100)
                num_good_points = numpy.ma.count(data_obs[si_gap: ei_gap])
            if not_enough_points:
                break
            si = max([0, si_gap])
            ei = min([len(ldt)-1, ei_gap])
            solo["info"]["startdate"] = ldt[si].strftime("%Y-%m-%d %H:%M")
            solo["info"]["enddate"] = ldt[ei].strftime("%Y-%m-%d %H:%M")
            gfSOLO_main(ds, solo, outputs=[output])
            gfSOLO_plotcoveragelines(ds, solo)

def gfSOLO_done(solo_gui):
    ds = solo_gui.ds
    solo = solo_gui.solo
    # plot the summary statistics if gap filling was done manually
    cl = ["GapFillUsingSOLO", "GapFillLongSOLO"]
    if (solo["gui"]["period_option"] == 1 and
        solo["info"]["called_by"] in cl):
            # write Excel spreadsheet with fit statistics
            pfp_io.xl_write_SOLOStats(ds, solo)
            # plot the summary statistics
            gfSOLO_plotsummary(ds, solo)
    # destroy the SOLO GUI
    solo_gui.close()
    # remove the solo dictionary from the data structure
    ds.returncodes["message"] = "normal"

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
    pd = {"margin_bottom":0.075, "margin_top":0.075, "margin_left":0.05, "margin_right":0.05,
          "xy_height":0.20, "xy_width":0.20, "xyts_space":0.05, "ts_width":0.9}
    # set the keyword arguments
    for key, value in kwargs.iteritems():
        pd[key] = value
    # calculate bottom of the first time series and the height of the time series plots
    pd["ts_bottom"] = pd["margin_bottom"]+pd["xy_height"]+pd["xyts_space"]
    pd["ts_height"] = (1.0 - pd["margin_top"] - pd["ts_bottom"])/float(pd["nDrivers"]+1)
    return pd

def gfSOLO_main(ds, solo, outputs=[]):
    '''
    This is the main routine for running SOLO, an artifical neural network for gap filling fluxes.
    '''
    if len(outputs) == 0:
        outputs = solo["outputs"].keys()
    startdate = solo["info"]["startdate"]
    enddate = solo["info"]["enddate"]
    logger.info(" Gap filling using SOLO: " + startdate + " to " + enddate)
    # get some useful things
    site_name = ds.globalattributes["site_name"]
    # get the time step and a local pointer to the datetime series
    ts = int(ds.globalattributes["time_step"])
    ldt = ds.series["DateTime"]["Data"]
    # get the start and end datetime indices
    si = pfp_utils.GetDateIndex(ldt, startdate, ts=ts, default=0, match="exact")
    ei = pfp_utils.GetDateIndex(ldt, enddate, ts=ts, default=len(ldt)-1, match="exact")
    # check the start and end indices
    if si >= ei:
        msg = " GapFillUsingSOLO: end datetime index ("+str(ei)+") smaller that start ("+str(si)+")"
        logger.warning(msg)
        return
    if si == 0 and ei == len(ldt)-1:
        msg = " GapFillUsingSOLO: no start and end datetime specified, using all data"
        logger.warning(msg)
        nRecs = int(ds.globalattributes["nc_nrecs"])
    else:
        nRecs = ei - si + 1
    # get the minimum number of points from the minimum percentage
    solo["gui"]["min_points"] = int((ei-si)*solo["gui"]["min_percent"]/100)
    # get the figure number
    fig_num = 0
    # loop over the series to be gap filled using solo
    for output in outputs:
        # get the target series label
        target = solo["outputs"][output]["target"]
        # get the drivers
        drivers = solo["outputs"][output]["drivers"]
        # get the start and end datetimes
        solo["outputs"][output]["results"]["startdate"].append(ldt[si])
        solo["outputs"][output]["results"]["enddate"].append(ldt[ei])
        # get the target data and check there is enough to continue
        d, f, a = pfp_utils.GetSeriesasMA(ds, target, si=si, ei=ei)
        if numpy.ma.count(d) < solo["gui"]["min_points"]:
            msg = "SOLO: Less than " + str(solo["gui"]["min_points"]) + " points available for target " + target
            logger.warning(msg)
            solo["outputs"][output]["results"]["No. points"].append(float(0))
            results = solo["outputs"][output]["results"].keys()
            for item in ["startdate", "enddate", "No. points"]:
                if item in results: results.remove(item)
            for item in results:
                solo["outputs"][output]["results"][item].append(float(c.missing_value))
            continue
        # get the number of nodes to use for the neural network
        if str(solo["gui"]["nodes"]).lower() == "auto":
            solo["gui"]["nodes_target"] = len(drivers) + 1
        else:
            solo["gui"]["nodes_target"] = int(solo["gui"]["nodes"])
        # overwrite the GUI settings if required
        if "solo_settings" in solo["outputs"][output]:
            solo["gui"]["nodes_target"] = solo["outputs"][output]["solo_settings"]["nodes_target"]
            solo["gui"]["training"] = solo["outputs"][output]["solo_settings"]["training"]
            solo["gui"]["nda_factor"] = solo["outputs"][output]["solo_settings"]["nda_factor"]
            solo["gui"]["learning_rate"] = solo["outputs"][output]["solo_settings"]["learning_rate"]
            solo["gui"]["iterations"] = solo["outputs"][output]["solo_settings"]["iterations"]
        # write the inf files for sofm, solo and seqsolo
        gfSOLO_writeinffiles(solo)
        # run SOFM
        result = gfSOLO_runsofm(ds, drivers, target, nRecs, si=si, ei=ei)
        if result != 1:
            return
        # run SOLO
        result = gfSOLO_runsolo(ds, drivers, target, nRecs, si=si, ei=ei)
        if result != 1:
            return
        # run seqsolo and put the solo_modelled data into the ds series
        result = gfSOLO_runseqsolo(ds, drivers, target, output, nRecs, si=si, ei=ei)
        if result != 1:
            return
        # plot the results
        fig_num = fig_num + 1
        title = site_name + " : Comparison of tower and SOLO data for " + target
        pd = gfSOLO_initplot(site_name=site_name, label=target, fig_num=fig_num,
                             title=title, nDrivers=len(drivers))
        gfSOLO_plot(pd, ds, drivers, target, output, solo, si=si, ei=ei)

def gfSOLO_plot(pd, ds, drivers, target, output, solo, si=0, ei=-1):
    """ Plot the results of the SOLO run. """
    # get the time step
    ts = int(ds.globalattributes['time_step'])
    # get a local copy of the datetime series
    xdt = ds.series["DateTime"]["Data"][si:ei+1]
    Hdh, f, a = pfp_utils.GetSeriesasMA(ds, 'Hdh', si=si, ei=ei)
    # get the observed and modelled values
    obs, f, a = pfp_utils.GetSeriesasMA(ds, target, si=si, ei=ei)
    mod, f, a = pfp_utils.GetSeriesasMA(ds, output, si=si, ei=ei)
    # make the figure
    if solo["gui"]["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    #fig = plt.figure(pd["fig_num"], figsize=(13, 8))
    if plt.fignum_exists(1):
        fig = plt.figure(1)
        plt.clf()
    else:
        fig = plt.figure(1, figsize=(13, 8))
    fig.canvas.set_window_title(target)
    plt.figtext(0.5, 0.95, pd["title"], ha='center', size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask, mod.mask)
    obs_mor = numpy.ma.array(obs, mask=mask)
    Num1, Hr1, Av1, Sd1, Mx1, Mn1 = gf_getdiurnalstats(Hdh, obs_mor, ts)
    ax1.plot(Hr1, Av1, 'b-', label="Obs")
    # get the diurnal stats of all SOLO predictions
    Num2, Hr2, Av2, Sd2, Mx2, Mn2 = gf_getdiurnalstats(Hdh, mod, ts)
    ax1.plot(Hr2, Av2, 'r-', label="SOLO(all)")
    # get the diurnal stats of SOLO predictions when the obs are present
    mod_mor = numpy.ma.array(mod, mask=mask)
    if numpy.ma.count_masked(obs) != 0:
        index = numpy.where(numpy.ma.getmaskarray(obs) == False)[0]
        # get the diurnal stats of SOLO predictions when observations are present
        Num3, Hr3, Av3, Sd3, Mx3, Mn3 = gf_getdiurnalstats(Hdh[index], mod_mor[index], ts)
        ax1.plot(Hr3, Av3, 'g-', label="SOLO(obs)")
    plt.xlim(0, 24)
    plt.xticks([0, 6, 12, 18, 24])
    ax1.set_ylabel(target)
    ax1.set_xlabel('Hour')
    ax1.legend(loc='upper right', frameon=False, prop={'size':8})
    # XY plot of the 30 minute data
    rect2 = [0.40, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax2 = plt.axes(rect2)
    ax2.plot(mod, obs, 'b.')
    ax2.set_ylabel(target + '_obs')
    ax2.set_xlabel(target + '_SOLO')
    # plot the best fit line
    coefs = numpy.ma.polyfit(numpy.ma.copy(mod), numpy.ma.copy(obs), 1)
    xfit = numpy.ma.array([numpy.ma.minimum.reduce(mod), numpy.ma.maximum.reduce(mod)])
    yfit = numpy.polyval(coefs, xfit)
    r = numpy.ma.corrcoef(mod, obs)
    ax2.plot(xfit, yfit, 'r--', linewidth=3)
    eqnstr = 'y = %.3fx + %.3f, r = %.3f'%(coefs[0], coefs[1], r[0][1])
    ax2.text(0.5, 0.875, eqnstr, fontsize=8, horizontalalignment='center', transform=ax2.transAxes)
    # write the fit statistics to the plot
    numpoints = trap_masked_constant(numpy.ma.count(obs))
    numfilled = trap_masked_constant(numpy.ma.count(mod)-numpy.ma.count(obs))
    diff = mod - obs
    bias = trap_masked_constant(numpy.ma.average(diff))
    fractional_bias = trap_masked_constant(bias/(0.5*(numpy.ma.average(obs+mod))))
    solo["outputs"][output]["results"]["Bias"].append(bias)
    solo["outputs"][output]["results"]["Frac Bias"].append(fractional_bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    mean_mod = numpy.ma.mean(mod)
    mean_obs = numpy.ma.mean(obs)
    data_range = numpy.ma.maximum.reduce(obs)-numpy.ma.minimum.reduce(obs)
    nmse = rmse/data_range
    plt.figtext(0.65, 0.225, 'No. points')
    plt.figtext(0.75, 0.225, str(numpoints))
    solo["outputs"][output]["results"]["No. points"].append(numpoints)
    plt.figtext(0.65, 0.200, 'No. filled')
    plt.figtext(0.75, 0.200, str(numfilled))
    plt.figtext(0.65, 0.175, 'Nodes')
    plt.figtext(0.75, 0.175, str(solo["gui"]["nodes_target"]))
    plt.figtext(0.65, 0.150, 'Training')
    plt.figtext(0.75, 0.150, str(solo["gui"]["training"]))
    plt.figtext(0.65, 0.125, 'Nda factor')
    plt.figtext(0.75, 0.125, str(solo["gui"]["nda_factor"]))
    plt.figtext(0.65, 0.100, 'Learning rate')
    plt.figtext(0.75, 0.100, str(solo["gui"]["learning_rate"]))
    plt.figtext(0.65, 0.075, 'Iterations')
    plt.figtext(0.75, 0.075, str(solo["gui"]["iterations"]))
    plt.figtext(0.815, 0.225, 'Slope')
    plt.figtext(0.915, 0.225, str(pfp_utils.round2sig(coefs[0], sig=4)))
    solo["outputs"][output]["results"]["m_ols"].append(trap_masked_constant(coefs[0]))
    plt.figtext(0.815, 0.200, 'Offset')
    plt.figtext(0.915, 0.200, str(pfp_utils.round2sig(coefs[1], sig=4)))
    solo["outputs"][output]["results"]["b_ols"].append(trap_masked_constant(coefs[1]))
    plt.figtext(0.815, 0.175, 'r')
    plt.figtext(0.915, 0.175, str(pfp_utils.round2sig(r[0][1], sig=4)))
    solo["outputs"][output]["results"]["r"].append(trap_masked_constant(r[0][1]))
    plt.figtext(0.815, 0.150, 'RMSE')
    plt.figtext(0.915, 0.150, str(pfp_utils.round2sig(rmse, sig=4)))
    solo["outputs"][output]["results"]["RMSE"].append(trap_masked_constant(rmse))
    solo["outputs"][output]["results"]["NMSE"].append(trap_masked_constant(nmse))
    var_obs = numpy.ma.var(obs)
    plt.figtext(0.815, 0.125, 'Var (obs)')
    plt.figtext(0.915, 0.125, '%.4g'%(var_obs))
    solo["outputs"][output]["results"]["Var (obs)"].append(trap_masked_constant(var_obs))
    var_mod = numpy.ma.var(mod)
    plt.figtext(0.815, 0.100, 'Var (SOLO)')
    plt.figtext(0.915, 0.100, '%.4g'%(var_mod))
    solo["outputs"][output]["results"]["Var (SOLO)"].append(trap_masked_constant(var_mod))
    solo["outputs"][output]["results"]["Var ratio"].append(trap_masked_constant(var_obs/var_mod))
    solo["outputs"][output]["results"]["Avg (obs)"].append(trap_masked_constant(numpy.ma.average(obs)))
    solo["outputs"][output]["results"]["Avg (SOLO)"].append(trap_masked_constant(numpy.ma.average(mod)))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"], pd["ts_bottom"], pd["ts_width"], pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    ts_axes[0].plot(xdt, obs, 'b.')
    ts_axes[0].plot(xdt, mod, 'r-')
    #plt.axhline(0)
    ts_axes[0].set_xlim(xdt[0], xdt[-1])
    TextStr = target + '_obs (' + ds.series[target]['Attr']['units'] + ')'
    ts_axes[0].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[0].transAxes)
    TextStr = output + '(' + ds.series[output]['Attr']['units'] + ')'
    ts_axes[0].text(0.85, 0.85, TextStr, color='r', horizontalalignment='right', transform=ts_axes[0].transAxes)
    for label, i in zip(drivers, range(1, pd["nDrivers"] + 1)):
        this_bottom = pd["ts_bottom"] + i*pd["ts_height"]
        rect = [pd["margin_left"], this_bottom, pd["ts_width"], pd["ts_height"]]
        ts_axes.append(plt.axes(rect, sharex=ts_axes[0]))
        data, flag, attr = pfp_utils.GetSeriesasMA(ds, label, si=si, ei=ei)
        data_notgf = numpy.ma.masked_where(flag != 0, data)
        data_gf = numpy.ma.masked_where(flag == 0, data)
        ts_axes[i].plot(xdt, data_notgf, 'b-')
        ts_axes[i].plot(xdt, data_gf, 'r-', linewidth=2)
        plt.setp(ts_axes[i].get_xticklabels(), visible=False)
        TextStr = label + '(' + attr['units'] + ')'
        ts_axes[i].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[i].transAxes)
    # save a hard copy of the plot
    sdt = xdt[0].strftime("%Y%m%d")
    edt = xdt[-1].strftime("%Y%m%d")
    figname = pd["site_name"].replace(" ", "") + "_SOLO_" + pd["label"]
    figname = figname + "_" + sdt + "_" + edt + '.png'
    figname = os.path.join(solo["info"]["plot_path"], figname)
    fig.savefig(figname, format='png')
    # draw the plot on the screen
    if solo["gui"]["show_plots"]:
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

def gfSOLO_plotcoveragelines(ds, solo):
    """
    Purpose:
     Plot a line representing the coverage of variables being gap filled.
    Usage:
    Author: PRI
    Date: Back in the day
    """
    # local pointer to datetime
    ldt = ds.series["DateTime"]["Data"]
    # get the site name and the start and end datetimes
    site_name = ds.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    # list of outputs to plot
    outputs = solo["outputs"].keys()
    # list of targets
    targets = [solo["outputs"][output]["target"] for output in solo["outputs"].keys()]
    ylabel_list = [""] + targets + [""]
    ylabel_right_list = [""]
    colors = ["blue", "red", "green", "yellow", "magenta", "black", "cyan", "brown"]
    xsize = 15.0
    ysize = max([len(outputs)*0.3, 1])
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
    plt.ylim([0, len(outputs) + 1])
    plt.xlim([ldt[0], ldt[-1]])
    for olabel, tlabel, n in zip(outputs, targets, range(1, len(outputs)+1)):
        output = pfp_utils.GetVariable(ds, olabel)
        target = pfp_utils.GetVariable(ds, tlabel)
        percent = 100*numpy.ma.count(target["Data"])/len(target["Data"])
        ylabel_right_list.append("{0:.0f}%".format(percent))
        ind_target = numpy.ma.ones(len(target["Data"]))*float(n)
        ind_target = numpy.ma.masked_where(numpy.ma.getmaskarray(target["Data"]) == True, ind_target)
        ind_output = numpy.ma.ones(len(output["Data"]))*float(n)
        ind_output = numpy.ma.masked_where(numpy.ma.getmaskarray(output["Data"]) == True, ind_output)
        plt.plot(ldt, ind_target, color=colors[numpy.mod(n, 8)], linewidth=1)
        plt.plot(ldt, ind_output, color=colors[numpy.mod(n, 8)], linewidth=4)
    ylabel_posn = range(0, len(outputs)+2)
    pylab.yticks(ylabel_posn, ylabel_list)
    ylabel_right_list.append("")
    ax2 = ax1.twinx()
    pylab.yticks(ylabel_posn, ylabel_right_list)
    fig.tight_layout()
    plt.draw()
    plt.ioff()

def gfSOLO_plotsummary(ds, solo):
    """ Plot single pages of summary results for groups of variables. """
    # find out who's calling
    called_by = solo["info"]["called_by"]
    # get a list of variables for which SOLO data is available
    outputs = solo["outputs"].keys()
    # site name for titles
    site_name = ds.globalattributes["site_name"]
    # get the start and end dates of the SOLO windows
    dt_start = []
    for ldt in solo["outputs"][outputs[0]]["results"]["startdate"]:
        dt_start.append(ldt)
    startdate = min(dt_start)
    dt_end = []
    for ldt in solo["outputs"][outputs[0]]["results"]["enddate"]:
        dt_end.append(ldt)
    enddate = max(dt_end)
    # get the major tick locator and label format
    MTLoc = mdt.AutoDateLocator(minticks=3, maxticks=5)
    MTFmt = mdt.DateFormatter('%b')
    # group lists of the resuts to be plotted
    result_list = ["r", "Bias", "RMSE", "Var ratio", "m_ols", "b_ols"]
    ylabel_list = ["r", "Bias", "RMSE", "Var ratio", "Slope", "Offset"]
    # turn on interactive plotting
    if solo["gui"]["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    # plot the summary statistics
    # set up the subplots on the page
    if plt.fignum_exists(1):
        fig = plt.figure(1)
        plt.clf()
        # axs = fig.subplots(len(result_list), len(outputs)) may be supported in matplotlib V2.1 and above
        # meanwhile, we do it the hard way
        axs = numpy.empty((len(result_list), len(outputs)), dtype="O")
        for row in range(len(result_list)):
            for col in range(len(outputs)):
                axs[row, col] = fig.add_subplot(len(result_list), len(outputs), col+row*len(outputs)+1)
    else:
        fig, axs = plt.subplots(len(result_list), len(outputs), figsize=(13, 8))
    fig.canvas.set_window_title(called_by + ": summary statistics")
    # make a title string for the plot and render it
    title_str = called_by + ": " + site_name + " " + datetime.datetime.strftime(startdate, "%Y-%m-%d")
    title_str = title_str + " to " + datetime.datetime.strftime(enddate, "%Y-%m-%d")
    fig.suptitle(title_str, fontsize=14, fontweight='bold')
    # now loop over the variables in the group list
    for col, label in enumerate(outputs):
        # and loop over rows in plot
        for row, rlabel, ylabel in zip(range(len(result_list)), result_list, ylabel_list):
            # get the results to be plotted
            #result = numpy.ma.masked_equal(ds.solo[label]["results"][rlabel],float(c.missing_value))
            # put the data into the right order to be plotted
            dt, data = gfSOLO_plotsummary_getdata(dt_start, dt_end, solo["outputs"][label]["results"][rlabel])
            dt = numpy.ma.masked_equal(dt, float(c.missing_value))
            data = numpy.ma.masked_equal(data, float(c.missing_value))
            # plot the results
            axs[row, col].plot(dt, data)
            # put in the major ticks
            axs[row, col].xaxis.set_major_locator(MTLoc)
            # if this is the left-most column, add the Y axis labels
            if col == 0: axs[row, col].set_ylabel(ylabel, visible=True)
            # if this is not the last row, hide the tick mark labels
            if row < len(result_list)-1: plt.setp(axs[row, col].get_xticklabels(), visible=False)
            # if this is the first row, add the column title
            if row == 0: axs[row, col].set_title(label)
            # if this is the last row, add the major tick mark and axis labels
            if row == len(result_list)-1:
                axs[row, col].xaxis.set_major_formatter(MTFmt)
                axs[row, col].set_xlabel('Month', visible=True)
    # make the hard-copy file name and save the plot as a PNG file
    sdt = startdate.strftime("%Y%m%d")
    edt = enddate.strftime("%Y%m%d")
    plot_path = os.path.join(solo["info"]["plot_path"], "L5", "")
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path + site_name.replace(" ", "") + "_"+called_by+"_FitStatistics_"
    figname = figname + "_" + sdt + "_" + edt + ".png"
    fig.savefig(figname, format="png")
    if solo["gui"]["show_plots"]:
        plt.draw()
        plt.ioff()
    else:
        plt.ion()

def gfSOLO_plotsummary_getdata(dt_start, dt_end, result):
    dt = []
    data = []
    for s, e, r in zip(dt_start, dt_end, result):
        dt.append(s)
        data.append(r)
        dt.append(e)
        data.append(r)
    return dt, data

def gfSOLO_qcchecks(cfg, dsa, dsb, mode="quiet"):
    """ Apply QC checks to series being gap filled."""
    outputs = list(dsb.solo.keys())
    for output in outputs:
        # get the target label and the control file section that contains it
        label = dsb.solo[output]["label_tower"]
        section = pfp_utils.get_cfsection(cfg, series=label)
        # copy the variable from dsa to dsb
        variable = pfp_utils.GetVariable(dsa, label)
        pfp_utils.CreateVariable(dsb, variable)
        # do the QC checks
        pfp_ck.do_rangecheck(cfg, dsb, section, label, code=2)
        pfp_ck.do_diurnalcheck(cfg, dsb, section, label, code=5)
        pfp_ck.do_excludedates(cfg, dsb, section, label, code=6)
        pfp_ck.do_dependencycheck(cfg, dsb, section, label, code=23, mode="quiet")
    return

def gfSOLO_quit(solo_gui):
    """ Quit the SOLO GUI."""
    # put the return code into ds.returncodes
    solo_gui.ds.returncodes["message"] = "quit"
    solo_gui.ds.returncodes["value"] = 1
    # destroy the GUI
    solo_gui.close()

def gfSOLO_run_interactive(solo_gui):
    """
    Purpose:
     Gets settings from the GapFillUsingSOLO GUI and loads them
     into the l5_info["gui"] dictionary
    Usage:
     Called when the "Run" button is clicked.
    Side effects:
     Loads settings into the l5_info["gui"] dictionary.
    Author: PRI
    Date: Re-written August 2019
    """
    # local pointers to useful things
    ds = solo_gui.ds
    called_by = solo_gui.called_by
    l5_info = solo_gui.l5_info
    l5s = l5_info[called_by]
    # populate the solo dictionary with more useful things
    ts = int(ds.globalattributes["time_step"])
    l5s["gui"]["nperhr"] = int(float(60)/ts + 0.5)
    l5s["gui"]["nperday"] = int(float(24)*l5s["gui"]["nperhr"] + 0.5)
    # window period length
    if str(solo_gui.radioButtons.checkedButton().text()) == "Manual":
        l5s["gui"]["period_option"] = 1
    elif str(solo_gui.radioButtons.checkedButton().text()) == "Months":
        l5s["gui"]["period_option"] = 2
        l5s["gui"]["number_months"] = int(solo_gui.lineEdit_NumberMonths.text())
    elif str(solo_gui.radioButtons.checkedButton().text()) == "Days":
        l5s["gui"]["period_option"] = 3
        l5s["gui"]["number_days"] = int(solo_gui.lineEdit_NumberDays.text())
    # plot settings
    l5s["gui"]["overwrite"] = solo_gui.checkBox_Overwrite.isChecked()
    l5s["gui"]["show_plots"] = solo_gui.checkBox_ShowPlots.isChecked()
    l5s["gui"]["show_all"] = solo_gui.checkBox_PlotAll.isChecked()
    # auto-complete settings
    l5s["gui"]["auto_complete"] = solo_gui.checkBox_AutoComplete.isChecked()
    solo["gui"]["min_percent"] = max(int(str(solo_gui.lineEdit_MinPercent.text())), 1)
    # minimum percentage of good data required
    l5s["gui"]["nodes"] = str(solo_gui.lineEdit_Nodes.text())
    solo["gui"]["training"] = str(solo_gui.lineEdit_Training.text())
    solo["gui"]["nda_factor"] = str(solo_gui.lineEdit_NdaFactor.text())
    solo["gui"]["learning_rate"] = str(solo_gui.lineEdit_Learning.text())
    solo["gui"]["iterations"] = str(solo_gui.lineEdit_Iterations.text())

    targets = [solo["outputs"][output]["target"] for output in solo["outputs"].keys()]
    logger.info(" Gap filling "+str(targets)+" using SOLO")
    if solo["gui"]["period_option"] == 1:
        logger.info(" Starting manual run ...")
        # get the start and end datetimes entered in the SOLO GUI
        if len(str(solo_gui.lineEdit_StartDate.text())) != 0:
            solo["info"]["startdate"] = str(solo_gui.lineEdit_StartDate.text())
        if len(str(solo_gui.lineEdit_EndDate.text())) != 0:
            solo["info"]["enddate"] = str(solo_gui.lineEdit_EndDate.text())
        # run the main SOLO gap fill routine
        gfSOLO_main(ds, solo)
        # plot the coverage lines
        if solo["info"]["called_by"] in ["GapFillUsingSOLO", "GapFillLongSOLO"]:
            gfSOLO_plotcoveragelines(ds, solo)
        logger.info(" Finished manual run")
    elif solo["gui"]["period_option"] == 2:
        logger.info(" Starting auto (months) run ...")
        # get the start datetime entered in the SOLO GUI
        nMonths = int(solo_gui.lineEdit_NumberMonths.text())
        solo["gui"]["number_months"] = nMonths
        if len(str(solo_gui.lineEdit_StartDate.text())) != 0:
            solo["info"]["startdate"] = str(solo_gui.lineEdit_StartDate.text())
        if len(str(solo_gui.lineEdit_EndDate.text())) != 0:
            solo["info"]["enddate"] = str(solo_gui.lineEdit_EndDate.text())
        startdate = dateutil.parser.parse(solo["info"]["startdate"])
        file_startdate = dateutil.parser.parse(solo["info"]["file_startdate"])
        file_enddate = dateutil.parser.parse(solo["info"]["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
        enddate = min([file_enddate, enddate])
        solo["info"]["enddate"] = datetime.datetime.strftime(enddate, "%Y-%m-%d %H:%M")
        while startdate < file_enddate:
            gfSOLO_main(ds, solo)
            if solo["info"]["called_by"] in ["GapFillUsingSOLO", "GapFillLongSOLO"]:
                gfSOLO_plotcoveragelines(ds, solo)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
            solo["info"]["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo["info"]["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(ds, solo)
        if solo["info"]["called_by"] in ["GapFillUsingSOLO", "GapFillLongSOLO"]:
            # write Excel spreadsheet with fit statistics
            pfp_io.xl_write_SOLOStats(ds, solo)
            # plot the summary statistics
            gfSOLO_plotsummary(ds, solo)
        logger.info(" Finished auto (months) run ...")
    elif solo["gui"]["period_option"] == 3:
        logger.info(" Starting auto (days) run ...")
        # get the start datetime entered in the SOLO GUI
        nDays = int(solo_gui.lineEdit_NumberDays.text())
        solo["gui"]["number_days"] = nDays
        if len(str(solo_gui.lineEdit_StartDate.text())) != 0:
            solo["info"]["startdate"] = str(solo_gui.lineEdit_StartDate.text())
        if len(solo_gui.lineEdit_EndDate.text()) != 0:
            solo["info"]["enddate"] = str(solo_gui.lineEdit_EndDate.text())
        solo["info"]["gui_startdate"] = solo["info"]["startdate"]
        solo["info"]["gui_enddate"] = solo["info"]["enddate"]
        startdate = dateutil.parser.parse(solo["info"]["startdate"])
        gui_enddate = dateutil.parser.parse(solo["info"]["gui_enddate"])
        file_startdate = dateutil.parser.parse(solo["info"]["file_startdate"])
        file_enddate = dateutil.parser.parse(solo["info"]["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate, enddate, gui_enddate])
        solo["info"]["enddate"] = datetime.datetime.strftime(enddate, "%Y-%m-%d %H:%M")
        solo["info"]["startdate"] = datetime.datetime.strftime(startdate, "%Y-%m-%d %H:%M")
        stopdate = min([file_enddate, gui_enddate])
        while startdate < stopdate:
            gfSOLO_main(ds, solo)
            if solo["info"]["called_by"] in ["GapFillUsingSOLO", "GapFillLongSOLO"]:
                gfSOLO_plotcoveragelines(ds, solo)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate, enddate])
            solo["info"]["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo["info"]["enddate"] = run_enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(ds, solo)
        if solo["info"]["called_by"] in ["GapFillUsingSOLO", "GapFillLongSOLO"]:
            # write Excel spreadsheet with fit statistics
            pfp_io.xl_write_SOLOStats(ds, solo)
            # plot the summary statistics
            gfSOLO_plotsummary(ds, solo)
        logger.info(" Finished auto (days) run ...")

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
    if opt.lower()=="no": solo_info["auto_complete"] = False
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
    #solo_info["tower"] = {}
    #solo_info["alternate"] = {}
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
    pfp_io.xl_write_SOLOStats(ds, info)
    # plot the summary statistics
    gfSOLO_plotsummary(ds, info)

def gfSOLO_runseqsolo(dsb, drivers, targetlabel, outputlabel, nRecs, si=0, ei=-1):
    '''
    Run SEQSOLO.
    '''
    # get the number of drivers
    ndrivers = len(drivers)
    # add an extra column for the target data
    seqsoloinputdata = numpy.zeros((nRecs, ndrivers + 1))
    # now fill the driver data array
    i = 0
    for label in drivers:
        driver, flag, attr = pfp_utils.GetSeries(dsb, label, si=si, ei=ei)
        seqsoloinputdata[:, i] = driver[:]
        i = i + 1
    # get the target data
    target, flag, attr = pfp_utils.GetSeries(dsb, targetlabel, si=si, ei=ei)
    # now load the target data into the data array
    seqsoloinputdata[:, ndrivers] = target[:]
    # now strip out the bad data
    cind = numpy.zeros(nRecs)
    iind = numpy.arange(nRecs)
    # do only the drivers not the target
    for i in range(ndrivers):
        index = numpy.where(seqsoloinputdata[:, i] == c.missing_value)[0]
        if len(index) != 0:
            cind[index] = 1
    # index of good data
    index = numpy.where(cind == 0)[0]
    nRecs_good = len(index)
    gooddata = numpy.zeros((nRecs_good, ndrivers+1))
    for i in range(ndrivers + 1):
        gooddata[:, i] = seqsoloinputdata[:, i][index]
    # keep track of the good data indices
    goodindex = iind[index]
    # and then write the seqsolo input file
    seqsolofile = open('solo/input/seqsolo_input.csv', 'wb')
    wr = csv.writer(seqsolofile, delimiter=',')
    for i in range(gooddata.shape[0]):
        wr.writerow(gooddata[i, 0:ndrivers + 1])
    seqsolofile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/seqOut2.out'):
        os.remove('solo/output/seqOut2.out')
    # now run SEQSOLO
    seqsolologfile = open('solo/log/seqsolo.log', 'wb')
    if platform.system() == "Windows":
        subprocess.call(['./solo/bin/seqsolo.exe', 'solo/inf/seqsolo.inf'], stdout=seqsolologfile)
    else:
        subprocess.call(['./solo/bin/seqsolo', 'solo/inf/seqsolo.inf'], stdout=seqsolologfile)
    seqsolologfile.close()
    # check to see if the solo output file exists, this is used to indicate that solo ran correctly
    if os.path.exists('solo/output/seqOut2.out'):
        # now read in the seqsolo results, use the seqOut2 file so that the learning capability of
        # seqsolo can be used via the "learning rate" and "Iterations" GUI options
        seqdata = numpy.genfromtxt('solo/output/seqOut2.out')
        # put the SOLO modelled data back into the data series
        if ei == -1:
            dsb.series[outputlabel]['Data'][si:][goodindex] = seqdata[:, 1]
            dsb.series[outputlabel]['Flag'][si:][goodindex] = numpy.int32(30)
        else:
            dsb.series[outputlabel]['Data'][si:ei+1][goodindex] = seqdata[:, 1]
            dsb.series[outputlabel]['Flag'][si:ei+1][goodindex] = numpy.int32(30)
        return 1
    else:
        msg = " SEQSOLO did not run correctly, check the GUI and the log files"
        logger.error(msg)
        return 0

def gfSOLO_runsofm(dsb, drivers, targetlabel, nRecs, si=0, ei=-1):
    '''
    Run SOFM, the pre-processor for SOLO.
    '''
    # get the number of drivers
    ndrivers = len(drivers)
    # add an extra column for the target data
    sofminputdata = numpy.zeros((nRecs, ndrivers))
    # now fill the driver data array
    i = 0
    badlines = []
    baddates = []
    badvalues = []
    for label in drivers:
        driver, flag, attr = pfp_utils.GetSeries(dsb, label, si=si, ei=ei)
        index = numpy.where(abs(driver-float(c.missing_value)) < c.eps)[0]
        if len(index) != 0:
            msg = " GapFillUsingSOLO: c.missing_value found in driver " + label + " at lines " + str(index)
            logger.error(msg)
            badlines = badlines + index.tolist()
            for n in index:
                baddates.append(dsb.series["DateTime"]["Data"][n])
                badvalues.append(dsb.series[label]["Data"][n])
            msg = " GapFillUsingSOLO: driver values: " + str(badvalues)
            logger.error(msg)
            msg = " GapFillUsingSOLO: datetimes: " + str(baddates)
            logger.error(msg)
        sofminputdata[:, i] = driver[:]
        i = i + 1
    if len(badlines) != 0:
        nBad = len(badlines)
        goodlines = [x for x in range(0, nRecs) if x not in badlines]
        sofminputdata = sofminputdata[goodlines, :]
        msg = " GapFillUsingSOLO: removed " + str(nBad) + " lines from sofm input file"
        logger.info(msg)
        nRecs = len(goodlines)
    # now write the drivers to the SOFM input file
    sofmfile = open('solo/input/sofm_input.csv', 'wb')
    wr = csv.writer(sofmfile, delimiter=',')
    for i in range(sofminputdata.shape[0]):
        wr.writerow(sofminputdata[i, 0:ndrivers])
    sofmfile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/sofm_4.out'):
        os.remove('solo/output/sofm_4.out')
    # now run SOFM
    sofmlogfile = open('solo/log/sofm.log', 'wb')
    if platform.system() == "Windows":
        subprocess.call(['./solo/bin/sofm.exe', 'solo/inf/sofm.inf'], stdout=sofmlogfile)
    else:
        subprocess.call(['./solo/bin/sofm', 'solo/inf/sofm.inf'], stdout=sofmlogfile)
    sofmlogfile.close()
    # check to see if the sofm output file exists, this is used to indicate that sofm ran correctly
    if os.path.exists('solo/output/sofm_4.out'):
        return 1
    else:
        msg = " SOFM did not run correctly, check the GUI and the log files"
        logger.error(msg)
        return 0

def gfSOLO_runsolo(dsb, drivers, targetlabel, nRecs, si=0, ei=-1):
    '''
    Run SOLO.
    '''
    ndrivers = len(drivers)
    # add an extra column for the target data
    soloinputdata = numpy.zeros((nRecs, ndrivers+1))
    # now fill the driver data array, drivers come from the modified ds
    i = 0
    for label in drivers:
        driver, flag, attr = pfp_utils.GetSeries(dsb, label, si=si, ei=ei)
        soloinputdata[:, i] = driver[:]
        i = i + 1
    # get the target data
    target, flag, attr = pfp_utils.GetSeries(dsb, targetlabel, si=si, ei=ei)
    # now load the target data into the data array
    soloinputdata[:, ndrivers] = target[:]
    # now strip out the bad data
    cind = numpy.zeros(nRecs)
    for i in range(ndrivers + 1):
        index = numpy.where(soloinputdata[:, i] == c.missing_value)[0]
        if len(index) != 0:
            cind[index] = 1
    index = numpy.where(cind == 0)[0]
    nRecs_good = len(index)
    gooddata = numpy.zeros((nRecs_good, ndrivers+1))
    for i in range(ndrivers + 1):
        gooddata[:, i] = soloinputdata[:, i][index]
    # and then write the solo input file, the name is assumed by the solo.inf control file
    solofile = open('solo/input/solo_input.csv', 'wb')
    wr = csv.writer(solofile, delimiter=',')
    for i in range(gooddata.shape[0]):
        wr.writerow(gooddata[i, 0:ndrivers + 1])
    solofile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/eigenValue.out'):
        os.remove('solo/output/eigenValue.out')
    # now run SOLO
    solologfile = open('solo/log/solo.log', 'wb')
    if platform.system() == "Windows":
        subprocess.call(['./solo/bin/solo.exe', 'solo/inf/solo.inf'], stdout=solologfile)
    else:
        subprocess.call(['./solo/bin/solo', 'solo/inf/solo.inf'], stdout=solologfile)
    solologfile.close()
    # check to see if the solo output file exists, this is used to indicate that solo ran correctly
    if os.path.exists('solo/output/eigenValue.out'):
        return 1
    else:
        msg = " SOLO did not run correctly, check the GUI and the log files"
        logger.error(msg)
        return 0

def gfSOLO_writeinffiles(solo):
    # sofm inf file
    f = open('solo/inf/sofm.inf','w')
    f.write(str(solo["gui"]["nodes_target"])+'\n')
    f.write(str(solo["gui"]["training"])+'\n')
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
    f.write(str(solo["gui"]["nodes_target"])+'\n')
    f.write(str(solo["gui"]["nda_factor"])+'\n')
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
    f.write(str(solo["gui"]["nodes_target"])+'\n')
    f.write(str(0)+'\n')
    f.write(str(solo["gui"]["learning_rate"])+'\n')
    f.write(str(solo["gui"]["iterations"])+'\n')
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
                Mx[i] = numpy.ma.maximum.reduce(Data[li])
                Mn[i] = numpy.ma.minimum.reduce(Data[li])
    return Num, Hr, Av, Sd, Mx, Mn

def trap_masked_constant(num):
    if numpy.ma.is_masked(num):
        num = float(c.missing_value)
    return num
