""" Routines for estimating ER using SOLO."""
# standard modules
import csv
import datetime
import logging
import os
import platform
import subprocess
# 3rd party modules
import dateutil
import matplotlib.pyplot as plt
import numpy
# PFP modules
import constants as c
import pfp_cfg
import pfp_io
import pfp_utils

logger = logging.getLogger("pfp_log")

def ERUsingSOLO(main_gui, cf, ds, l6_info):
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
    ds.returncodes["message"] = "normal"
    # get the SOLO information
    solo = l6_info["ER"]["ERUsingSOLO"]
    if solo["info"]["call_mode"].lower() == "interactive":
        # call the ERUsingSOLO GUI
        rpSOLO_gui(main_gui, ds, solo)
    #else:
        #if "GUI" in cf:
            #if "SOLO" in cf["GUI"]:
                #rpSOLO_run_nogui(cf, ds, l6_info["ER"])

def rpSOLO_gui(main_gui, ds, solo):
    """ Display the SOLO GUI and wait for the user to finish."""
    # add the data structures (dsa and dsb) and the solo_info dictionary to self
    main_gui.solo_gui.ds = ds
    main_gui.solo_gui.solo = solo
    # put up the start and end dates
    main_gui.solo_gui.label_DataStartDate_value.setText(solo["info"]["file_startdate"])
    main_gui.solo_gui.label_DataEndDate_value.setText(solo["info"]["file_enddate"])
    # set the default period to manual
    main_gui.solo_gui.radioButton_Manual.setChecked(True)
    # set the default number of nodes
    main_gui.solo_gui.lineEdit_Nodes.setText("1")
    # set the default minimum percentage of good data
    main_gui.solo_gui.lineEdit_MinPercent.setText("10")
    # display the SOLO GUI
    main_gui.solo_gui.show()
    main_gui.solo_gui.exec_()

def rpSOLO_quit(solo_gui):
    ds = solo_gui.ds
    # destroy the GUI
    solo_gui.close()
    # put the return code in ds.returncodes
    ds.returncodes["message"] = "quit"

def rp_getdiurnalstats(dt, data, solo):
    ts = solo["info"]["time_step"]
    nperday = solo["info"]["nperday"]
    si = 0
    while abs(dt[si].hour+float(dt[si].minute)/60-float(ts)/60)>c.eps:
        si = si + 1
    ei = len(dt)-1
    while abs(dt[ei].hour+float(dt[ei].minute)/60)>c.eps:
        ei = ei - 1
    data_wholedays = data[si:ei+1]
    ndays = len(data_wholedays)/nperday
    data_2d = numpy.ma.reshape(data_wholedays,[ndays,nperday])
    diel_stats = {}
    diel_stats["Hr"] = numpy.ma.array([i*ts/float(60) for i in range(0,nperday)])
    diel_stats["Av"] = numpy.ma.average(data_2d,axis=0)
    diel_stats["Sd"] = numpy.ma.std(data_2d,axis=0)
    diel_stats["Mx"] = numpy.ma.max(data_2d,axis=0)
    diel_stats["Mn"] = numpy.ma.min(data_2d,axis=0)
    return diel_stats

def rpSOLO_createdict(cf, ds, l6_info, label, called_by):
    """ Creates a dictionary in ds to hold information about the SOLO data used
        to gap fill the tower data."""
    nrecs = int(ds.globalattributes["nc_nrecs"])
    # get the target and output labels
    target = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingSOLO"], "target", default="ER")
    output = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingSOLO"], "output", default="ER_SOLO_all")
    # check that none of the drivers have missing data
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingSOLO"], "drivers", default="Ta,Ts,Sws")
    drivers = pfp_cfg.cfg_string_to_list(opt)
    for driver in drivers:
        variable = pfp_utils.GetVariable(ds, driver)
        if numpy.ma.count_masked(variable["Data"]) != 0:
            msg = "ERUsingSOLO: driver " + driver + " contains missing data, skipping target " + target
            logger.error(msg)
            return
    # create the dictionary keys for this series
    if called_by not in l6_info["ER"].keys():
        l6_info["ER"][called_by] = {"outputs": {}, "info": {}, "gui": {}}
    isol = l6_info["ER"][called_by]["outputs"][output] = {}
    # target series name
    isol["target"] = target
    # list of drivers
    isol["drivers"] = drivers
    # source to use as CO2 flux
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingSOLO"], "source", default="Fc")
    isol["source"] = opt
    # name of SOLO output series in ds
    isol["output"] = output
    # results of best fit for plotting later on
    isol["results"] = {"startdate":[], "enddate":[], "No. points":[], "r":[],
                       "Bias":[], "RMSE":[], "Frac Bias":[], "NMSE":[],
                       "Avg (obs)":[], "Avg (SOLO)":[],
                       "Var (obs)":[], "Var (SOLO)":[], "Var ratio":[],
                       "m_ols":[], "b_ols":[]}
    # create an empty series in ds if the SOLO output series doesn't exist yet
    if output not in ds.series.keys():
        variable = pfp_utils.CreateEmptyVariable(output, nrecs)
        pfp_utils.CreateVariable(ds, variable)
    # local pointer to the datetime series
    ldt = ds.series["DateTime"]["Data"]
    startdate = ldt[0]
    enddate = ldt[-1]
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "call_mode", default="interactive")
    l6_info["ER"][called_by]["info"] = {"file_startdate": startdate.strftime("%Y-%m-%d %H:%M"),
                                        "file_enddate": enddate.strftime("%Y-%m-%d %H:%M"),
                                        "startdate": startdate.strftime("%Y-%m-%d %H:%M"),
                                        "enddate": enddate.strftime("%Y-%m-%d %H:%M"),
                                        "plot_path": cf["Files"]["plot_path"],
                                        "call_mode": call_mode,
                                        "called_by": called_by}
    return

def rpSOLO_done(solo_gui):
    # destroy the SOLO GUI
    solo_gui.close()

def rpSOLO_initplot(**kwargs):
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

def rpSOLO_main(ds, solo, outputs=[]):
    """
    This is the main routine for running SOLO, an artifical neural network for estimating ER.
    """
    if len(outputs) == 0:
        outputs = solo["outputs"].keys()
    startdate = solo["info"]["startdate"]
    enddate = solo["info"]["enddate"]
    logger.info(" Estimating ER using SOLO: " + startdate + " to " + enddate)
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
        msg = " ERUsingSOLO: end datetime index ("+str(ei)+") smaller that start ("+str(si)+")"
        logger.error(msg)
        return
    if si==0 and ei==len(ldt)-1:
        msg = " ERUsingSOLO: no start and end datetime specified, using all data"
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
        output_all = solo["outputs"][output]["output"]
        solo["outputs"][output]["results"]["startdate"].append(ldt[si])
        solo["outputs"][output]["results"]["enddate"].append(ldt[ei])
        d, f, a = pfp_utils.GetSeriesasMA(ds, target, si=si, ei=ei)
        if numpy.ma.count(d) < solo["gui"]["min_points"]:
            pts = solo["gui"]["min_points"]
            pct = int(float(100)*pts/len(d) + 0.5)
            msg = "rpSOLO: Less than " + str(pts) + " points (" + str(pct) + "%) available for series " + target + " ..."
            logger.error(msg)
            solo["outputs"][output]["results"]["No. points"].append(float(0))
            results = solo["outputs"][output]["results"].keys()
            for item in ["startdate", "enddate", "No. points"]:
                if item in results: results.remove(item)
            for item in results:
                solo["outputs"][output]["results"][item].append(float(c.missing_value))
            continue
        drivers = solo["outputs"][output]["drivers"]
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
        rpSOLO_writeinffiles(solo)
        # run SOFM
        result = rpSOLO_runsofm(ds, drivers, target, nRecs, si=si, ei=ei)
        if result != 1:
            return
        # run SOLO
        result = rpSOLO_runsolo(ds, drivers, target, nRecs, si=si, ei=ei)
        if result != 1:
            return
        # run SEQSOLO and put the SOLO data into the data structure
        result = rpSOLO_runseqsolo(ds, drivers, target, output_all, nRecs, si=si, ei=ei)
        if result != 1:
            return
        # plot the results
        fig_num = fig_num + 1
        title = site_name + " : " + output + " estimated using SOLO"
        pd = rpSOLO_initplot(site_name=site_name, label=target, fig_num=fig_num,
                             title=title, nDrivers=len(drivers),
                             startdate=startdate, enddate=enddate)
        rpSOLO_plot(pd, ds, drivers, target, output_all, solo, si=si, ei=ei)

def rpSOLO_plot(pd, ds, drivers, target, output, solo, si=0, ei=-1):
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
    dstats = rp_getdiurnalstats(xdt, obs_mor, solo)
    ax1.plot(dstats["Hr"], dstats["Av"], 'b-', label="Obs")
    # get the diurnal stats of all SOLO predictions
    dstats = rp_getdiurnalstats(xdt, mod, solo)
    ax1.plot(dstats["Hr"], dstats["Av"], 'r-', label="SOLO(all)")
    # get the diurnal stats of SOLO predictions when the obs are present
    mod_mor = numpy.ma.masked_where(numpy.ma.getmaskarray(obs) == True, mod, copy=True)
    if numpy.ma.count_masked(obs) != 0:
        index = numpy.where(numpy.ma.getmaskarray(obs) == False)[0]
        # get the diurnal stats of SOLO predictions when observations are present
        dstats = rp_getdiurnalstats(xdt, mod_mor, solo)
        ax1.plot(dstats["Hr"], dstats["Av"], 'g-', label="SOLO(obs)")
    plt.xlim(0,24)
    plt.xticks([0, 6, 12, 18, 24])
    ax1.set_ylabel(target)
    ax1.set_xlabel('Hour')
    ax1.legend(loc='upper right', frameon=False, prop={'size':8})
    # XY plot of the 30 minute data
    rect2 = [0.40, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax2 = plt.axes(rect2)
    ax2.plot(mod,obs, 'b.')
    ax2.set_ylabel(target + '_obs')
    ax2.set_xlabel(target + '_SOLO')
    # plot the best fit line
    coefs = numpy.ma.polyfit(numpy.ma.copy(mod), numpy.ma.copy(obs), 1)
    xfit = numpy.ma.array([numpy.ma.minimum(mod), numpy.ma.maximum(mod)])
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
    data_range = numpy.ma.maximum(obs)-numpy.ma.minimum(obs)
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
    ts_axes[0].scatter(xdt, obs, c=Hdh)
    ts_axes[0].plot(xdt, mod, 'r-')
    plt.axhline(0)
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
    plot_path = os.path.join(solo["info"]["plot_path"], "L6", "")
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
    figname = plot_path + pd["site_name"].replace(" ","") + "_SOLO_" + pd["label"]
    figname = figname + "_" + sdt + "_" + edt + '.png'
    fig.savefig(figname, format='png')
    # draw the plot on the screen
    if solo["gui"]["show_plots"]:
        plt.draw()
        plt.ioff()
    else:
        plt.ion()

def rpSOLO_run_gui(solo_gui):
    # local pointers to useful things
    ds = solo_gui.ds
    solo = solo_gui.solo
    # populate the solo_info dictionary with more useful things
    if str(solo_gui.radioButtons.checkedButton().text()) == "Manual":
        solo["gui"]["period_option"] = 1
    elif str(solo_gui.radioButtons.checkedButton().text()) == "Months":
        solo["gui"]["period_option"] = 2
    elif str(solo_gui.radioButtons.checkedButton().text()) == "Days":
        solo["gui"]["period_option"] = 3

    solo["gui"]["overwrite"] = solo_gui.checkBox_Overwrite.isChecked()
    solo["gui"]["show_plots"] = solo_gui.checkBox_ShowPlots.isChecked()
    solo["gui"]["show_all"] = solo_gui.checkBox_PlotAll.isChecked()
    solo["gui"]["auto_complete"] = solo_gui.checkBox_AutoComplete.isChecked()
    solo["gui"]["min_percent"] = max(int(str(solo_gui.lineEdit_MinPercent.text())), 1)

    solo["gui"]["nodes"] = str(solo_gui.lineEdit_Nodes.text())
    solo["gui"]["training"] = str(solo_gui.lineEdit_Training.text())
    solo["gui"]["nda_factor"] = str(solo_gui.lineEdit_NdaFactor.text())
    solo["gui"]["learning_rate"] = str(solo_gui.lineEdit_Learning.text())
    solo["gui"]["iterations"] = str(solo_gui.lineEdit_Iterations.text())
    #solo["gui"]["drivers"] = str(solo_gui.lineEdit_Drivers.text())

    # populate the solo_info dictionary with things that will be useful
    solo["info"]["site_name"] = ds.globalattributes["site_name"]
    solo["info"]["time_step"] = int(ds.globalattributes["time_step"])
    solo["info"]["nperhr"] = int(float(60)/solo["info"]["time_step"]+0.5)
    solo["info"]["nperday"] = int(float(24)*solo["info"]["nperhr"]+0.5)
    solo["info"]["maxlags"] = int(float(12)*solo["info"]["nperhr"]+0.5)
    #log.info(" Estimating ER using SOLO")
    if solo["gui"]["period_option"] == 1:
        # manual run using start and end datetime entered via GUI
        logger.info(" Starting manual run ...")
        # get the start and end datetimes entered in the SOLO GUI
        if len(str(solo_gui.lineEdit_StartDate.text())) != 0:
            solo["info"]["startdate"] = str(solo_gui.lineEdit_StartDate.text())
        if len(str(solo_gui.lineEdit_EndDate.text())) != 0:
            solo["info"]["enddate"] = str(solo_gui.lineEdit_EndDate.text())
        rpSOLO_main(ds, solo)
        logger.info(" Finished manual run ...")
    elif solo["gui"]["period_option"] == 2:
        # automatic run with monthly datetime periods
        logger.info(" Starting auto (months) run ...")
        nMonths = int(solo_gui.lineEdit_NumberMonths.text())
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
            rpSOLO_main(ds, solo)
            startdate = enddate
            enddate = startdate + dateutil.relativedelta.relativedelta(months=nMonths)
            solo["info"]["startdate"] = startdate.strftime("%Y-%m-%d")
            solo["info"]["enddate"] = enddate.strftime("%Y-%m-%d")
        logger.info(" Finished auto (monthly) run ...")
    elif solo["gui"]["period_option"] == 3:
        # automatic run with number of days specified by user via the GUI
        logger.info(" Starting auto (days) run ...")
        # get the start datetime entered in the SOLO GUI
        nDays = int(solo_gui.lineEdit_NumberDays.text())
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
        while startdate < stopdate:  #file_enddate:
            rpSOLO_main(ds, solo)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            solo["info"]["startdate"] = startdate.strftime("%Y-%m-%d")
            solo["info"]["enddate"] = run_enddate.strftime("%Y-%m-%d")
        logger.info(" Finished auto (days) run ...")

def rpSOLO_run_nogui(cf,ds,solo_info):
    # populate the solo_info dictionary with things that will be useful
    # period option
    dt = ds.series["DateTime"]["Data"]
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"period_option",default="manual")
    if opt=="manual":
        solo_info["peropt"] = 1
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"start_date",default="")
        solo_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: solo_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"end_date",default="")
        solo_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: solo_info["enddate"] = ed
    elif opt=="monthly":
        solo_info["peropt"] = 2
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"start_date",default="")
        solo_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: solo_info["startdate"] = sd
    elif opt=="days":
        solo_info["peropt"] = 3
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"start_date",default="")
        solo_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: solo_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"end_date",default="")
        solo_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: solo_info["enddate"] = ed
    elif opt=="yearly":
        solo_info["peropt"] = 4
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"start_date",default="")
        solo_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: solo_info["startdate"] = sd
    # overwrite option
    solo_info["overwrite"] = False
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"overwrite",default="no")
    if opt.lower()=="yes": solo_info["overwrite"] = True
    # show plots option
    solo_info["show_plots"] = True
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"show_plots",default="yes")
    if opt.lower()=="no": solo_info["show_plots"] = False
    # auto-complete option
    solo_info["auto_complete"] = True
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"auto_complete",default="yes")
    if opt.lower()=="no": alternate_info["auto_complete"] = False
    # minimum percentage of good points required
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"min_percent",default=50)
    solo_info["min_percent"] = int(opt)
    # number of days
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"number_days",default=90)
    solo_info["number_days"] = int(opt)
    # nodes for SOFM/SOLO network
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"nodes",default="auto")
    solo_info["nodes"] = str(opt)
    # training iterations
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"training",default="500")
    solo_info["training"] = str(opt)
    # nda factor
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"nda_factor",default="5")
    solo_info["nda_factor"] = str(opt)
    # learning rate
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"learning",default="0.01")
    solo_info["learningrate"] = str(opt)
    # learning iterations
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","SOLO"],"iterations",default="500")
    solo_info["iterations"] = str(opt)
    # now set up the rest of the solo_info dictionary
    solo_info["site_name"] = ds.globalattributes["site_name"]
    solo_info["time_step"] = int(ds.globalattributes["time_step"])
    solo_info["nperhr"] = int(float(60)/solo_info["time_step"]+0.5)
    solo_info["nperday"] = int(float(24)*solo_info["nperhr"]+0.5)
    solo_info["maxlags"] = int(float(12)*solo_info["nperhr"]+0.5)
    solo_info["series"] = solo_info["er"].keys()
    if solo_info["peropt"]==1:
        rpSOLO_main(ds,solo_info)
        #logger.info(" Finished manual run ...")
    elif solo_info["peropt"]==2:
        # get the start datetime entered in the SOLO GUI
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<file_enddate:
            rpSOLO_main(ds,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        ## now fill any remaining gaps
        #gfSOLO_autocomplete(dsa,dsb,solo_info)
        ## plot the summary statistics
        #gfSOLO_plotsummary(dsb,solo_info)
        logger.info(" Finished auto (monthly) run ...")
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
            rpSOLO_main(ds,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        ## now fill any remaining gaps
        #gfSOLO_autocomplete(dsa,dsb,solo_info)
        ## plot the summary statistics
        #gfSOLO_plotsummary(dsb,solo_info)
        logger.info(" Finished auto (days) run ...")
    elif solo_info["peropt"]==4:
        if len(solo_info["startdate"])==0: solo_info["startdate"] = solo_info["file_startdate"]
        startdate = dateutil.parser.parse(solo_info["startdate"])
        # get the start year
        start_year = startdate.year
        enddate = dateutil.parser.parse(str(start_year+1)+"-01-01 00:00")
        #file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        #enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        while startdate<file_enddate:
            rpSOLO_main(ds,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(years=1)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d")
        logger.info(" Finished auto (yearly) run ...")

def rpSOLO_runseqsolo(ds, drivers, targetlabel, outputlabel, nRecs, si=0, ei=-1):
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
        driver, flag, attr = pfp_utils.GetSeries(ds, label, si=si, ei=ei)
        seqsoloinputdata[:, i] = driver[:]
        i = i + 1
    # a clean copy of the target is pulled from the unmodified ds each time
    target, flag, attr = pfp_utils.GetSeries(ds, targetlabel, si=si, ei=ei)
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
            ds.series[outputlabel]['Data'][si:][goodindex] = seqdata[:, 1]
            ds.series[outputlabel]['Flag'][si:][goodindex] = numpy.int32(30)
        else:
            ds.series[outputlabel]['Data'][si:ei+1][goodindex] = seqdata[:, 1]
            ds.series[outputlabel]['Flag'][si:ei+1][goodindex] = numpy.int32(30)
        # set the attributes
        ds.series[outputlabel]["Attr"]["units"] = ds.series[targetlabel]["Attr"]["units"]
        if "modelled by SOLO" not in ds.series[outputlabel]["Attr"]["long_name"]:
            ds.series[outputlabel]["Attr"]["long_name"] = "Ecosystem respiration modelled by SOLO (ANN)"
            ds.series[outputlabel]["Attr"]["comment1"] = "Target was "+str(targetlabel)
            ds.series[outputlabel]["Attr"]["comment2"] = "Drivers were "+str(drivers)
        return 1
    else:
        logger.error(' SOLO_runseqsolo: SEQSOLO did not run correctly, check the SOLO GUI and the log files')
        return 0

def rpSOLO_runsofm(ds, drivers, targetlabel, nRecs, si=0, ei=-1):
    """
    Run SOFM, the pre-processor for SOLO.
    """
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
        driver, flag, attr = pfp_utils.GetSeries(ds, label, si=si, ei=ei)
        index = numpy.where(abs(driver-float(c.missing_value)) < c.eps)[0]
        if len(index) != 0:
            msg = " ERUsingSOLO: c.missing_value found in driver " + label + " at lines " + str(index)
            logger.error(msg)
            badlines = badlines+index.tolist()
            for n in index:
                baddates.append(ds.series["DateTime"]["Data"][n])
                badvalues.append(ds.series[label]["Data"][n])
            msg = " GapFillUsingSOLO: driver values: " + str(badvalues)
            logger.error(msg)
            msg = " GapFillUsingSOLO: datetimes: " + str(baddates)
            logger.error(msg)
        sofminputdata[:,i] = driver[:]
        i = i + 1
    if len(badlines) != 0:
        nBad = len(badlines)
        goodlines = [x for x in range(0, nRecs) if x not in badlines]
        sofminputdata = sofminputdata[goodlines, :]
        msg = " ERUsingSOLO: removed " + str(nBad) + " lines from sofm input file"
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
        msg = " ERUsingSOLO SOFM did not run correctly, check the GUI and the log files"
        logger.error(msg)
        return 0

def rpSOLO_runsolo(ds, drivers, targetlabel, nRecs, si=0, ei=-1):
    '''
    Run SOLO.
    '''
    ndrivers = len(drivers)
    # add an extra column for the target data
    soloinputdata = numpy.zeros((nRecs, ndrivers+1))
    # now fill the driver data array, drivers come from the modified ds
    i = 0
    for label in drivers:
        driver, flag, attr = pfp_utils.GetSeries(ds, label, si=si, ei=ei)
        soloinputdata[:,i] = driver[:]
        i = i + 1
    # get the target data
    target, flag, attr = pfp_utils.GetSeries(ds, targetlabel, si=si, ei=ei)
    # now load the target data into the data array
    soloinputdata[:, ndrivers] = target[:]
    # now strip out the bad data
    cind = numpy.zeros(nRecs)
    for i in range(ndrivers+1):
        index = numpy.where(soloinputdata[:, i] == c.missing_value)[0]
        if len(index) != 0:
            cind[index] = 1
    index = numpy.where(cind == 0)[0]
    nRecs_good = len(index)
    gooddata = numpy.zeros((nRecs_good, ndrivers+1))
    for i in range(ndrivers+1):
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
        msg = " ERUsingSOLO: SOLO did not run correctly, check the SOLO GUI and the log files"
        logger.error(msg)
        return 0

def rpSOLO_writeinffiles(solo):
    # sofm inf file
    f = open('solo/inf/sofm.inf','w')
    f.write(str(solo["gui"]["nodes"])+'\n')
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
    f.write(str(solo["gui"]["nodes"])+'\n')
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
    f.write(str(solo["gui"]["nodes"])+'\n')
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

def trap_masked_constant(num):
    if numpy.ma.is_masked(num):
        num = float(c.missing_value)
    return num
