# standard modules
import datetime
import logging
import os
# 3rd party modules
import dateutil
import ffnet
import matplotlib.pyplot as plt
import numpy
import pylab
# PFP modules
import constants as c
import pfp_gf
import pfp_utils

logger = logging.getLogger("pfp_log")

# functions for GapFillUsingFFNET
def GapFillUsingFFNET(main_gui, cf, dsa, dsb):
    '''
    This is the "Run FFNET" GUI.
    The FFNET GUI is displayed separately from the main PyFluxPro GUI.
    It consists of text to display the start and end datetime of the file,
    two entry boxes for the start and end datetimes of the FFNET run and
    a button to run FFNET ("Run") and a button to exit the FFNET GUI
    when we are done.  On exit, the PyFluxPro main GUI continues and eventually
    writes the gap filled data to file.
    '''
    # set the default return code
    dsb.returncodes["ffnet"] = "normal"
    if "ffnet" not in dir(dsb): return
    # check the FFNET drivers for missing data
    pfp_gf.CheckDrivers(cf, dsb, gf_type="FFNET")
    if dsb.returncodes["value"] != 0: return dsb
    # local pointer to the datetime series
    ldt = dsb.series["DateTime"]["Data"]
    startdate = ldt[0]
    enddate = ldt[-1]
    ffnet_info = {"file_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                  "file_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                  "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                  "enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                  "called_by": "GapFillingUsingFFNET",
                  "plot_path": cf["Files"]["plot_path"]}
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "call_mode", default="interactive")
    ffnet_info["call_mode"] = call_mode
    if call_mode.lower() == "interactive":
        ffnet_info["show_plots"] = True
    if call_mode.lower() == "interactive":
        # put up a plot of the data coverage at L4
        gfFFNET_plotcoveragelines(dsb, ffnet_info)
        # call the GapFillUsingSOLO GUI
        gfFFNET_gui(main_gui, dsa, dsb, ffnet_info)
    #else:
        #if "GUI" in cf:
            #if "SOLO" in cf["GUI"]:
                #gfSOLO_run_nogui(cf, dsa, dsb, solo_info)
            #else:
                #logger.warning(" No GUI sub-section found in Options section of control file")
                #gfSOLO_plotcoveragelines(dsb, solo_info)
                #gfSOLO_gui(main_gui, dsa, dsb, solo_info)
        #else:
            #logger.warning(" No GUI sub-section found in Options section of control file")
            #gfSOLO_plotcoveragelines(dsb, solo_info)
            #gfSOLO_gui(main_gui, dsa, dsb, solo_info)

def  gfFFNET_gui(main_gui, dsa, dsb, ffnet_info):
    """ Display the FFNET GUI and wait for the user to finish."""
    # add the data structures (dsa and dsb) and the ffnet_info dictionary to self
    main_gui.ffnet_gui.dsa = dsa
    main_gui.ffnet_gui.dsb = dsb
    main_gui.ffnet_gui.ffnet_info = ffnet_info
    main_gui.ffnet_gui.edit_cfg = main_gui.tabs.tab_dict[main_gui.tabs.tab_index_running]
    # put up the start and end dates
    main_gui.ffnet_gui.label_DataStartDate_value.setText(ffnet_info["startdate"])
    main_gui.ffnet_gui.label_DataEndDate_value.setText(ffnet_info["enddate"])
    # set the default period to manual
    main_gui.ffnet_gui.radioButton_NumberMonths.setChecked(True)
    # display the FFNET GUI
    main_gui.ffnet_gui.show()
    main_gui.ffnet_gui.exec_()

def gfFFNET_done(ffnet_gui):
    ds = ffnet_gui.dsb
    ffnet_info = ffnet_gui.ffnet_info
    # plot the summary statistics if gap filling was done manually
    #if ffnet_info["peropt"] == 1:
        ## write Excel spreadsheet with fit statistics
        #pfp_io.xl_write_FFNETStats(ds)
        ## plot the summary statistics
        #gfFFNET_plotsummary(ds, ffnet_info)
    # destroy the FFNET GUI
    ffnet_gui.close()
    # remove the FFNET dictionary from the data structure
    ds.returncodes["ffnet"] = "normal"

def gfFFNET_initplot(**kwargs):
    # set the margins, heights, widths etc
    pd = {"margin_bottom":0.075, "margin_top":0.075, "margin_left":0.05, "margin_right":0.05,
          "xy_height":0.20, "xy_width":0.20, "xyts_space":0.05, "xyts_space":0.05,
          "ts_width":0.9}
    # set the keyword arguments
    for key, value in kwargs.iteritems():
        pd[key] = value
    # calculate bottom of the first time series and the height of the time series plots
    pd["ts_bottom"] = pd["margin_bottom"] + pd["xy_height"] + pd["xyts_space"]
    pd["ts_height"] = (1.0 - pd["margin_top"] - pd["ts_bottom"])/float(pd["nDrivers"]+1)
    return pd

def gfFFNET_main(dsa, dsb, ffnet_info, output_list=[]):
    """
    This is the main routine for running FFNET, an artifical neural network for estimating ER.
    """
    if len(output_list)==0: output_list = dsb.ffnet.keys()
    startdate = ffnet_info["startdate"]
    enddate = ffnet_info["enddate"]
    logger.info(" Gap filling using FFNET: " + startdate + " to " + enddate)
    # get some useful things
    site_name = dsa.globalattributes["site_name"]
    # get the time step and a local pointer to the datetime series
    ts = dsb.globalattributes["time_step"]
    ldt = dsb.series["DateTime"]["Data"]
    xldt = dsb.series["xlDateTime"]["Data"]
    # get the start and end datetime indices
    si = pfp_utils.GetDateIndex(ldt, startdate, ts=ts, default=0, match="exact")
    ei = pfp_utils.GetDateIndex(ldt, enddate, ts=ts, default=len(ldt)-1, match="exact")
    # check the start and end indices
    if si >= ei:
        msg = " GapFillUsingFFNET: end datetime index ("+str(ei)+") smaller that start ("+str(si)+")"
        logger.error(msg)
        return
    if si == 0 and ei == -1:
        msg = " GapFillUsingFFNET: no start and end datetime specified, using all data"
        logger.error(msg)
        nRecs = int(dsb.globalattributes["nc_nrecs"])
    else:
        nRecs = ei - si + 1
    # get the minimum number of points from the minimum percentage
    ffnet_info["min_points"] = int((ei-si)*ffnet_info["min_percent"]/100)
    # close any open plot windows
    if len(plt.get_fignums()) != 0:
        for i in plt.get_fignums():
            if i != 0: plt.close(i)
    fig_num = 0
    # loop over the series to be gap filled using ffnet
    for output in output_list:
        dsb.ffnet[output]["results"]["startdate"].append(xldt[si])
        dsb.ffnet[output]["results"]["enddate"].append(xldt[ei])
        target_label = dsb.ffnet[output]["label_tower"]
        target = pfp_utils.GetVariable(dsb, target_label, start=si, end=ei)
        if numpy.ma.count(target["Data"]) < ffnet_info["min_points"]:
            msg = "gfFFNET: Less than "+str(ffnet_info["min_points"])+" points available for series "+output+" ..."
            logger.error(msg)
            dsb.ffnet[output]["results"]["No. points"].append(float(0))
            results_list = dsb.ffnet[output]["results"].keys()
            for item in ["startdate", "enddate", "No. points"]:
                if item in results_list: results_list.remove(item)
            for item in results_list:
                dsb.ffnet[output]["results"][item].append(float(c.missing_value))
            continue
        # get the target mask
        mask = numpy.ma.getmaskarray(target["Data"])
        drivers = dsb.ffnet[output]["drivers"]
        # loop over the drivers and get a combined mask
        for label in drivers:
            driver = pfp_utils.GetVariable(dsb, label, start=si, end=ei)
            mask = numpy.ma.mask_or(mask, numpy.ma.getmaskarray(driver["Data"]))
        # apply the combined mask to the target
        target["Data"].mask = mask
        # create an empty array for the data
        nRecs = numpy.ma.count(target["Data"])
        ndrivers = len(drivers)
        data_nm = numpy.empty((nRecs, ndrivers+1))
        # put the drivers into the array
        for idx, label in enumerate(drivers):
            var = pfp_utils.GetVariable(dsb, label, start=si, end=ei)
            # apply the combined mask to the drivers
            var["Data"].mask = mask
            data_nm[:,idx] = numpy.ma.compressed(var["Data"])
        # put the target in as the last column
        data_nm[:,idx+1] = numpy.ma.compressed(target["Data"])
        # get the input training data
        input_train = data_nm[:,0:idx+1]
        # get the target training data
        target_train = data_nm[:,idx+1]
        # design the network
        hidden_layers = ffnet_info["nodes"].split(",")
        if len(hidden_layers) == 1:
            arch = (ndrivers, int(hidden_layers[0]), 1)
        elif len(hidden_layers)==2:
            arch = (ndrivers, int(hidden_layers[0]), int(hidden_layers[1]), 1)
        else:
            msg = "  GapFilleUsingFFNET: more than 2 hidden layers specified, using 1 ("+str(ndrivers)+")"
            logger.warning(msg)
            arch = (ndrivers, ndrivers, 1)
        if ffnet_info["connection_type"].lower() == "standard":
            conec = ffnet.mlgraph(arch, biases=True)
        elif ffnet_info["connection_type"].lower() == "full":
            conec = ffnet.tmlgraph(arch, biases=True)
        else:
            raise Exception("unrecognised FFNET connection option")
        net = ffnet.ffnet(conec)
        # train the network
        if ffnet_info["training_type"].lower() == "tnc":
            net.train_tnc(input_train, target_train)
        elif ffnet_info["training_type"].lower() == "bfgs":
            net.train_bfgs(input_train, target_train)
        elif ffnet_info["training_type"].lower() == "cg":
            net.train_cg(input_train, target_train)
        elif ffnet_info["training_type"].lower() == "genetic":
            net.train_genetic(input_train, target_train)
        elif ffnet_info["training_type"].lower() == "back":
            net.train_momentum(input_train, target_train)
        elif ffnet_info["training_type"].lower() == "rprop":
            try:
                net.train_rprop(input_train, target_train)
            except:
                logger.warning("  GapFillUsingFFNET: Rprop training failed, using TNC ...")
                net.train_tnc(input_train, target_train)
        else:
            raise Exception("unrecognised FFNET training option")
        #output,regress=net.test(input_train,target_train)
        # get the predictions
        # create and load the prediction data array
        input_predict = numpy.empty((len(target["Data"]),len(drivers)))
        for idx, label in enumerate(drivers):
            data = pfp_utils.GetVariable(dsb, label, start=si, end=ei)
            input_predict[:,idx] = data["Data"][:]
        # get the output predictions
        output_predict = net.call(input_predict)
        # load the output predictions into the data structure
        if ei == -1:
            dsb.series[output]['Data'][si:] = output_predict[:,0]
            dsb.series[output]['Flag'][si:] = numpy.int32(30)
        else:
            dsb.series[output]['Data'][si:ei+1] = output_predict[:,0]
            dsb.series[output]['Flag'][si:ei+1] = numpy.int32(30)
        # set the attributes
        dsb.series[output]["Attr"]["units"] = dsb.series[target_label]["Attr"]["units"]
        if "modelled by FFNET" not in dsb.series[output]["Attr"]["long_name"]:
            dsb.series[output]["Attr"]["long_name"] = "modelled by FFNET (ANN)"
            dsb.series[output]["Attr"]["comment1"] = "Target was "+str(target)
            dsb.series[output]["Attr"]["comment2"] = "Drivers were "+str(drivers)
        # plot the results
        fig_num = fig_num + 1
        title = site_name+" : " + target_label + " estimated using FFNET"
        pd = gfFFNET_initplot(site_name=site_name, label=target_label, fig_num=fig_num, title=title,
                              nDrivers=len(drivers), startdate=startdate, enddate=enddate)
        gfFFNET_plot(pd, dsb, drivers, target_label, output, ffnet_info, si=si, ei=ei)

def gfFFNET_plot(pd, dsb, driverlist, targetlabel, outputlabel, ffnet_info, si=0, ei=-1):
    """ Plot the results of the FFNET run. """
    # get the time step
    ts = int(dsb.globalattributes['time_step'])
    # get a local copy of the datetime series
    xdt = dsb.series['DateTime']['Data'][si:ei+1]
    Hdh,f,a = pfp_utils.GetSeriesasMA(dsb,'Hdh',si=si,ei=ei)
    # get the observed and modelled values
    obs,f,a = pfp_utils.GetSeriesasMA(dsb,targetlabel,si=si,ei=ei)
    mod,f,a = pfp_utils.GetSeriesasMA(dsb,outputlabel,si=si,ei=ei)
    # make the figure
    if ffnet_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"], figsize=(13, 8))
    fig.clf()
    fig.canvas.set_window_title(targetlabel)
    plt.figtext(0.5, 0.95, pd["title"], ha='center', size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask, mod.mask)
    obs_mor = numpy.ma.array(obs, mask=mask)
    Num1, Hr1, Av1, Sd1, Mx1, Mn1 = gf_getdiurnalstats(Hdh, obs_mor, ts)
    ax1.plot(Hr1, Av1, 'b-', label="Obs")
    # get the diurnal stats of all FFNET predictions
    Num2, Hr2, Av2, Sd2, Mx2, Mn2 = gf_getdiurnalstats(Hdh, mod, ts)
    ax1.plot(Hr2, Av2, 'r-', label="FFNET(all)")
    # get the diurnal stats of FFNET predictions when the obs are present
    mod_mor = numpy.ma.array(mod, mask=mask)
    if numpy.ma.count_masked(obs) != 0:
        index = numpy.where(numpy.ma.getmaskarray(obs) == False)[0]
        # get the diurnal stats of FFNET predictions when observations are present
        Num3, Hr3, Av3, Sd3, Mx3, Mn3 = gf_getdiurnalstats(Hdh[index], mod_mor[index], ts)
        ax1.plot(Hr3, Av3, 'g-', label="FFNET(obs)")
    plt.xlim(0, 24)
    plt.xticks([0, 6, 12, 18, 24])
    ax1.set_ylabel(targetlabel)
    ax1.set_xlabel('Hour')
    ax1.legend(loc='upper right', frameon=False, prop={'size':8})
    # XY plot of the 30 minute data
    rect2 = [0.40, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax2 = plt.axes(rect2)
    ax2.plot(mod, obs, 'b.')
    ax2.set_ylabel(targetlabel+'_obs')
    ax2.set_xlabel(targetlabel+'_FFNET')
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
    dsb.ffnet[outputlabel]["results"]["Bias"].append(bias)
    dsb.ffnet[outputlabel]["results"]["Frac Bias"].append(fractional_bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    mean_mod = numpy.ma.mean(mod)
    mean_obs = numpy.ma.mean(obs)
    data_range = numpy.ma.maximum(obs)-numpy.ma.minimum(obs)
    nmse = rmse/data_range
    plt.figtext(0.65, 0.225, 'No. points')
    plt.figtext(0.75, 0.225, str(numpoints))
    dsb.ffnet[outputlabel]["results"]["No. points"].append(numpoints)
    plt.figtext(0.65, 0.200, 'No. filled')
    plt.figtext(0.75, 0.200, str(numfilled))
    plt.figtext(0.65, 0.175, 'Hidden nodes')
    plt.figtext(0.75, 0.175, str(ffnet_info["nodes"]))
    plt.figtext(0.65, 0.150, 'Training')
    plt.figtext(0.75, 0.150, str(ffnet_info["training"]))
    plt.figtext(0.65, 0.125, 'Training type')
    plt.figtext(0.75, 0.125, str(ffnet_info["training_type"]))
    plt.figtext(0.65, 0.100, 'Connection')
    plt.figtext(0.75, 0.100, str(ffnet_info["connection_type"]))
    plt.figtext(0.815, 0.225, 'Slope')
    plt.figtext(0.915, 0.225, str(pfp_utils.round2sig(coefs[0], sig=4)))
    dsb.ffnet[outputlabel]["results"]["m_ols"].append(trap_masked_constant(coefs[0]))
    plt.figtext(0.815, 0.200, 'Offset')
    plt.figtext(0.915, 0.200, str(pfp_utils.round2sig(coefs[1], sig=4)))
    dsb.ffnet[outputlabel]["results"]["b_ols"].append(trap_masked_constant(coefs[1]))
    plt.figtext(0.815, 0.175, 'r')
    plt.figtext(0.915, 0.175, str(pfp_utils.round2sig(r[0][1], sig=4)))
    dsb.ffnet[outputlabel]["results"]["r"].append(trap_masked_constant(r[0][1]))
    plt.figtext(0.815, 0.150, 'RMSE')
    plt.figtext(0.915, 0.150, str(pfp_utils.round2sig(rmse, sig=4)))
    dsb.ffnet[outputlabel]["results"]["RMSE"].append(trap_masked_constant(rmse))
    dsb.ffnet[outputlabel]["results"]["NMSE"].append(trap_masked_constant(nmse))
    var_obs = numpy.ma.var(obs)
    plt.figtext(0.815, 0.125, 'Var (obs)')
    plt.figtext(0.915, 0.125, '%.4g'%(var_obs))
    dsb.ffnet[outputlabel]["results"]["Var (obs)"].append(trap_masked_constant(var_obs))
    var_mod = numpy.ma.var(mod)
    plt.figtext(0.815, 0.100, 'Var (FFNET)')
    plt.figtext(0.915, 0.100, '%.4g'%(var_mod))
    dsb.ffnet[outputlabel]["results"]["Var (FFNET)"].append(trap_masked_constant(var_mod))
    dsb.ffnet[outputlabel]["results"]["Var ratio"].append(trap_masked_constant(var_obs/var_mod))
    dsb.ffnet[outputlabel]["results"]["Avg (obs)"].append(trap_masked_constant(numpy.ma.average(obs)))
    dsb.ffnet[outputlabel]["results"]["Avg (FFNET)"].append(trap_masked_constant(numpy.ma.average(mod)))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"], pd["ts_bottom"], pd["ts_width"], pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    ts_axes[0].plot(xdt, obs, 'b.', xdt, mod, 'r-')
    ts_axes[0].set_xlim(xdt[0], xdt[-1])
    TextStr = targetlabel + '_obs (' + dsb.series[targetlabel]['Attr']['units'] + ')'
    ts_axes[0].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[0].transAxes)
    TextStr = outputlabel + '(' + dsb.series[outputlabel]['Attr']['units'] + ')'
    ts_axes[0].text(0.85, 0.85, TextStr, color='r', horizontalalignment='right', transform=ts_axes[0].transAxes)
    for ThisOne, i in zip(driverlist, range(1, pd["nDrivers"]+1)):
        this_bottom = pd["ts_bottom"] + i*pd["ts_height"]
        rect = [pd["margin_left"], this_bottom, pd["ts_width"], pd["ts_height"]]
        ts_axes.append(plt.axes(rect, sharex=ts_axes[0]))
        data, flag, attr = pfp_utils.GetSeriesasMA(dsb, ThisOne, si=si, ei=ei)
        data_notgf = numpy.ma.masked_where(flag != 0,data)
        data_gf = numpy.ma.masked_where(flag == 0,data)
        ts_axes[i].plot(xdt, data_notgf, 'b-')
        ts_axes[i].plot(xdt, data_gf, 'r-')
        plt.setp(ts_axes[i].get_xticklabels(), visible=False)
        TextStr = ThisOne + '(' + dsb.series[ThisOne]['Attr']['units'] + ')'
        ts_axes[i].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[i].transAxes)
    # save a hard copy of the plot
    sdt = xdt[0].strftime("%Y%m%d")
    edt = xdt[-1].strftime("%Y%m%d")
    plot_path = os.path.join(ffnet_info["plot_path"], "L5", "")
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path + pd["site_name"].replace(" ","") + "_FFNET_" + pd["label"]
    figname = figname + "_" + sdt + "_" + edt + '.png'
    fig.savefig(figname, format='png')
    # draw the plot on the screen
    if ffnet_info["show_plots"]:
        plt.draw()
        plt.pause(1)
        plt.ioff()
    else:
        plt.ion()

def gfFFNET_plotcoveragelines(dsb, ffnet_info):
    ldt = dsb.series["DateTime"]["Data"]
    site_name = dsb.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    output_list = dsb.ffnet.keys()
    series_list = [dsb.ffnet[item]["label_tower"] for item in dsb.ffnet.keys()]
    ylabel_list = [""] + series_list + [""]
    ylabel_right_list = [""]
    series_list = [dsb.ffnet[item]["label_tower"] for item in output_list]
    color_list = ["blue", "red", "green", "yellow", "magenta", "black", "cyan", "brown"]
    xsize = 15.0
    ysize = max([len(output_list)*0.3, 1])
    plt.ion()
    if plt.fignum_exists(0):
        fig=plt.figure(0)
        plt.clf()
        ax1 = plt.subplot(111)
    else:
        fig=plt.figure(0, figsize=(xsize, ysize))
        ax1 = plt.subplot(111)
    title = "Coverage: " + site_name + " " + start_date + " to " + end_date
    fig.canvas.set_window_title(title)
    plt.ylim([0, len(output_list)+1])
    plt.xlim([ldt[0], ldt[-1]])
    for output, series, n in zip(output_list, series_list, range(1, len(output_list)+1)):
        data_output, f, a = pfp_utils.GetSeriesasMA(dsb, output)
        data_series, f, a = pfp_utils.GetSeriesasMA(dsb, series)
        percent = 100*numpy.ma.count(data_series)/len(data_series)
        ylabel_right_list.append("{0:.0f}%".format(percent))
        ind_series = numpy.ma.ones(len(data_series))*float(n)
        ind_series = numpy.ma.masked_where(numpy.ma.getmaskarray(data_series) == True, ind_series)
        ind_output = numpy.ma.ones(len(data_output))*float(n)
        ind_output = numpy.ma.masked_where(numpy.ma.getmaskarray(data_output) == True, ind_output)
        plt.plot(ldt, ind_series, color=color_list[numpy.mod(n, 8)], linewidth=1)
        plt.plot(ldt, ind_output, color=color_list[numpy.mod(n, 8)], linewidth=4)
    ylabel_posn = range(0, len(output_list)+2)
    pylab.yticks(ylabel_posn, ylabel_list)
    ylabel_right_list.append("")
    ax2 = ax1.twinx()
    pylab.yticks(ylabel_posn, ylabel_right_list)
    fig.tight_layout()
    #fig.canvas.manager.window.attributes('-topmost', 1)
    plt.draw()
    plt.ioff()

def gfFFNET_quit(ffnet_gui):
    """ Quit the SOLO GUI."""
    dsb = ffnet_gui.dsb
    # destroy the GUI
    ffnet_gui.close()
    # put the return code in ds.returncodes
    dsb.returncodes["ffnet"] = "quit"

def gfFFNET_run_gui(ffnet_gui):
    """ Run the FFNET neural network to gap fill the fluxes."""
    # local pointers to useful things
    dsa = ffnet_gui.dsa
    dsb = ffnet_gui.dsb
    ffnet_info = ffnet_gui.ffnet_info
    # populate the ffnet_info dictionary with more useful things
    if str(ffnet_gui.radioButtons.checkedButton().text()) == "Manual":
        ffnet_info["peropt"] = 1
    elif str(ffnet_gui.radioButtons.checkedButton().text()) == "Months":
        ffnet_info["peropt"] = 2
    elif str(ffnet_gui.radioButtons.checkedButton().text()) == "Days":
        ffnet_info["peropt"] = 3

    ffnet_info["overwrite"] = ffnet_gui.checkBox_Overwrite.isChecked()
    ffnet_info["show_plots"] = ffnet_gui.checkBox_ShowPlots.isChecked()
    ffnet_info["show_all"] = ffnet_gui.checkBox_PlotAll.isChecked()
    ffnet_info["auto_complete"] = ffnet_gui.checkBox_AutoComplete.isChecked()
    ffnet_info["min_percent"] = max(int(str(ffnet_gui.lineEdit_MinPercent.text())), 1)

    ffnet_info["nodes"] = str(ffnet_gui.lineEdit_Nodes.text())
    ffnet_info["training"] = str(ffnet_gui.lineEdit_Training.text())
    ffnet_info["training_type"] = str(ffnet_gui.combo_TrainingType.currentText())
    ffnet_info["connection_type"] = str(ffnet_gui.combo_ConnectionType.currentText())

    ffnet_info["site_name"] = dsb.globalattributes["site_name"]
    ffnet_info["time_step"] = int(dsb.globalattributes["time_step"])
    ffnet_info["nperhr"] = int(float(60)/ffnet_info["time_step"]+0.5)
    ffnet_info["nperday"] = int(float(24)*ffnet_info["nperhr"]+0.5)
    ffnet_info["maxlags"] = int(float(12)*ffnet_info["nperhr"]+0.5)
    ffnet_info["series"] = dsb.ffnet.keys()
    ffnet_info["tower"] = {}
    ffnet_info["alternate"] = {}
    series_list = [dsb.ffnet[item]["label_tower"] for item in dsb.ffnet.keys()]

    logger.info(" Gap filling "+str(series_list)+" using FFNET")
    if ffnet_info["peropt"] == 1:
        logger.info(" Starting manual run ...")
        # get the start and end datetimes entered in the FFNET GUI
        if len(str(ffnet_gui.lineEdit_StartDate.text())) != 0:
            ffnet_info["startdate"] = str(ffnet_gui.lineEdit_StartDate.text())
        if len(str(ffnet_gui.lineEdit_EndDate.text())) != 0:
            ffnet_info["enddate"] = str(ffnet_gui.lineEdit_EndDate.text())
        # get the control file contents
        cfg = ffnet_gui.edit_cfg.get_data_from_model()
        # run the QC checks again
        #gfSOLO_qcchecks(cfg, dsa, dsb, mode="quiet")
        # get a list of series altered in GUI
        # if none have been altered, this list will be empty, output_list passed
        # to gfSOLO_main() will be empty and then all series will be done
        #altered = list(set(ffnet_gui.edit_cfg.altered))
        #for label in altered:
        output_list = []
        for label in cfg["Fluxes"].keys():
            output_list += cfg["Fluxes"][label]["GapFillUsingFFNET"].keys()
        # run the main FFNET gap fill routine
        gfFFNET_main(dsa, dsb, ffnet_info, output_list=output_list)
        # reset the altered list to empty
        ffnet_gui.edit_cfg.altered = []
        # plot the coverage lines
        gfFFNET_plotcoveragelines(dsb, ffnet_info)
        logger.info("Finished manual run")
    elif ffnet_info["peropt"] == 2:
        logger.info("Starting auto (months) run ...")
        # get the start datetime entered in the FFNET GUI
        nMonths = int(ffnet_gui.lineEdit_NumberMonths.text())
        if len(str(ffnet_gui.lineEdit_StartDate.text())) != 0:
            ffnet_info["startdate"] = str(ffnet_gui.lineEdit_StartDate.text())
        if len(str(ffnet_gui.lineEdit_EndDate.text())) != 0:
            ffnet_info["enddate"] = str(ffnet_gui.lineEdit_EndDate.text())
        startdate = dateutil.parser.parse(ffnet_info["startdate"])
        file_startdate = dateutil.parser.parse(ffnet_info["file_startdate"])
        file_enddate = dateutil.parser.parse(ffnet_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
        enddate = min([file_enddate, enddate])
        ffnet_info["enddate"] = datetime.datetime.strftime(enddate, "%Y-%m-%d %H:%M")
        while startdate < file_enddate:
            gfFFNET_main(dsa, dsb, ffnet_info)
            gfFFNET_plotcoveragelines(dsb, ffnet_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
            ffnet_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            ffnet_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        #gfFFNET_autocomplete(dsa, dsb, ffnet_info)
        # write Excel spreadsheet with fit statistics
        #pfp_io.xl_write_FFNETStats(dsb)
        # plot the summary statistics
        #gfFFNET_plotsummary(dsb, ffnet_info)
        logger.info(" Finished auto (months) run ...")
    elif ffnet_info["peropt"] == 3:
        logger.info("Starting auto (days) run ...")
        # get the start datetime entered in the SOLO GUI
        nDays = int(ffnet_gui.lineEdit_NumberDays.text())
        if len(str(ffnet_gui.lineEdit_StartDate.text())) != 0:
            ffnet_info["startdate"] = str(ffnet_gui.lineEdit_StartDate.text())
        if len(ffnet_gui.lineEdit_EndDate.text()) != 0:
            ffnet_info["enddate"] = str(ffnet_gui.lineEdit_EndDate.text())
        ffnet_info["gui_startdate"] = ffnet_info["startdate"]
        ffnet_info["gui_enddate"] = ffnet_info["enddate"]
        startdate = dateutil.parser.parse(ffnet_info["startdate"])
        gui_enddate = dateutil.parser.parse(ffnet_info["gui_enddate"])
        file_startdate = dateutil.parser.parse(ffnet_info["file_startdate"])
        file_enddate = dateutil.parser.parse(ffnet_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate, enddate, gui_enddate])
        ffnet_info["enddate"] = datetime.datetime.strftime(enddate, "%Y-%m-%d %H:%M")
        ffnet_info["startdate"] = datetime.datetime.strftime(startdate, "%Y-%m-%d %H:%M")
        stopdate = min([file_enddate, gui_enddate])
        while startdate < stopdate:
            gfFFNET_main(dsa, dsb, ffnet_info)
            gfFFNET_plotcoveragelines(dsb, ffnet_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate, enddate])
            ffnet_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            ffnet_info["enddate"] = run_enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        #gfSOLO_autocomplete(dsa, dsb, solo_info)
        # write Excel spreadsheet with fit statistics
        #pfp_io.xl_write_SOLOStats(dsb)
        # plot the summary statistics
        #gfSOLO_plotsummary(dsb, solo_info)
        logger.info(" Finished auto (days) run ...")
    elif ffnet_info["peropt"] == 4:
        pass

#def rpFFNET_run_nogui(cf,ds,rpFFNET_info):
    ## populate the rpFFNET_info dictionary with things that will be useful
    #dt = ds.series["DateTime"]["Data"]
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"period_option",default="manual")
    #if opt=="manual":
        #rpFFNET_info["peropt"] = 1
        #sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        #rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        #if len(sd)!=0: rpFFNET_info["startdate"] = sd
        #ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"end_date",default="")
        #rpFFNET_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        #if len(ed)!=0: rpFFNET_info["enddate"] = ed
    #elif opt=="monthly":
        #rpFFNET_info["peropt"] = 2
        #sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        #rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        #if len(sd)!=0: rpFFNET_info["startdate"] = sd
    #elif opt=="days":
        #rpFFNET_info["peropt"] = 3
        #sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        #rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        #if len(sd)!=0: rpFFNET_info["startdate"] = sd
        #ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"end_date",default="")
        #rpFFNET_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        #if len(ed)!=0: rpFFNET_info["enddate"] = ed
    #elif opt=="yearly":
        #rpFFNET_info["peropt"] = 4
        #sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        #rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        #if len(sd)!=0: rpFFNET_info["startdate"] = sd
    ## number of hidden layers
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"hidden_nodes",default="6,4")
    #rpFFNET_info["hidden"] = str(opt)
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"training",default=500)
    #rpFFNET_info["training"] = int(opt)
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"training_type",default="rprop")
    #rpFFNET_info["training_type"] = str(opt)
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"connection",default="full")
    #rpFFNET_info["connection"] = str(opt)
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"min_percent",default=10)
    #rpFFNET_info["min_percent"] = int(opt)
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"number_days",default=90)
    #rpFFNET_info["number_days"] = int(opt)
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"number_months",default=6)
    #rpFFNET_info["number_months"] = int(opt)
    #rpFFNET_info["show_plots"] = True
    #opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"show_plots",default="yes")
    #if opt.lower()=="no": rpFFNET_info["show_plots"] = False

    #rpFFNET_info["site_name"] = ds.globalattributes["site_name"]
    #rpFFNET_info["time_step"] = int(ds.globalattributes["time_step"])
    #rpFFNET_info["nperhr"] = int(float(60)/rpFFNET_info["time_step"]+0.5)
    #rpFFNET_info["nperday"] = int(float(24)*rpFFNET_info["nperhr"]+0.5)
    #rpFFNET_info["maxlags"] = int(float(12)*rpFFNET_info["nperhr"]+0.5)
    #rpFFNET_info["tower"] = {}
    #rpFFNET_info["access"] = {}
    #if rpFFNET_info["peropt"]==1:
        #rpFFNET_main(ds,rpFFNET_info)
    #elif rpFFNET_info["peropt"]==2:
        ## get the start datetime entered in the SOLO GUI
        #startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        #file_startdate = dateutil.parser.parse(rpFFNET_info["file_startdate"])
        #file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        #nDays = rpFFNET_info["number_days"]
        #enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        #enddate = min([file_enddate,enddate])
        #rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        #while startdate<file_enddate:
            #rpFFNET_main(ds,rpFFNET_info)
            #startdate = enddate
            #enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            #rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            #rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
    #elif rpFFNET_info["peropt"]==3:
        ## get the start datetime entered in the SOLO GUI
        #startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        #file_startdate = dateutil.parser.parse(rpFFNET_info["file_startdate"])
        #file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        #nMonths = rpFFNET_info["number_months"]
        #enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
        #enddate = min([file_enddate,enddate])
        #rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        #while startdate<file_enddate:
            #rpFFNET_main(ds,rpFFNET_info)
            #startdate = enddate
            #enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
            #rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            #rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
    #elif rpFFNET_info["peropt"]==4:
        ## get the start date
        #startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        ## get the start year
        #start_year = startdate.year
        #enddate = dateutil.parser.parse(str(start_year+1)+"-01-01 00:00")
        #file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        #enddate = min([file_enddate,enddate])
        #rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        #while startdate<file_enddate:
            #rpFFNET_main(ds,rpFFNET_info)
            #startdate = enddate
            #enddate = startdate+dateutil.relativedelta.relativedelta(years=1)
            #rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            #rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
    #elif FFNET_gui.peropt.get()==5:
        #pass

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

def trap_masked_constant(num):
    if numpy.ma.is_masked(num):
        num = float(c.missing_value)
    return num
