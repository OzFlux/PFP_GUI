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

def ERUsingSOLO(main_gui, cf, ds, info):
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
    if "solo" not in info["er"]: return
    # local pointer to the datetime series
    ldt = ds.series["DateTime"]["Data"]
    startdate = ldt[0]
    enddate = ldt[-1]
    solo_info = {"file_startdate": startdate.strftime("%Y-%m-%d %H:%M"),
                 "file_enddate": enddate.strftime("%Y-%m-%d %H:%M"),
                 "startdate": startdate.strftime("%Y-%m-%d %H:%M"),
                 "enddate": enddate.strftime("%Y-%m-%d %H:%M"),
                 "plot_path": cf["Files"]["plot_path"],
                 "er": info["er"]["solo"],
                 "called_by": "ERUsingSOLO"}
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf,["Options"],"call_mode",default="interactive")
    solo_info["call_mode"]= call_mode
    #if call_mode.lower()=="interactive": solo_info["show_plots"] = True
    if call_mode.lower()=="interactive":
        # call the ERUsingSOLO GUI
        rpSOLO_gui(main_gui, cf, ds, solo_info)
    else:
        if "GUI" in cf:
            if "SOLO" in cf["GUI"]:
                rpSOLO_run_nogui(cf, ds, solo_info)

def rpSOLO_gui(main_gui, cf, ds, solo_info):
    """ Display the SOLO GUI and wait for the user to finish."""
    # add the data structures (dsa and dsb) and the solo_info dictionary to self
    main_gui.l5_ui.dsa = ds
    main_gui.l5_ui.dsb = ds
    main_gui.l5_ui.solo_info = solo_info
    # put up the start and end dates
    main_gui.l5_ui.label_DataStartDate_value.setText(solo_info["file_startdate"])
    main_gui.l5_ui.label_DataEndDate_value.setText(solo_info["file_enddate"])
    # set the default period to manual
    main_gui.l5_ui.radioButton_Manual.setChecked(True)
    # set the default number of nodes
    main_gui.l5_ui.lineEdit_Nodes.setText("1")
    # set the default minimum percentage of good data
    main_gui.l5_ui.lineEdit_MinPercent.setText("10")
    # display the SOLO GUI
    main_gui.l5_ui.show()
    main_gui.l5_ui.exec_()

def rpSOLO_quit(solo_gui):
    ds = solo_gui.dsb
    # destroy the GUI
    solo_gui.close()
    # put the return code in ds.returncodes
    ds.returncodes["solo"] = "quit"

def rp_getdiurnalstats(dt,data,info):
    ts = info["time_step"]
    nperday = info["nperday"]
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

def rpSOLO_createdict(cf,ds,series):
    """ Creates a dictionary in ds to hold information about the SOLO data used
        to gap fill the tower data."""
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("ERUsingSOLO: Series "+series+" not found in control file, skipping ...")
        return
    # check that none of the drivers have missing data
    driver_string = cf[section][series]["ERUsingSOLO"]["drivers"]
    if "," in driver_string:
        driver_list = driver_string.split(",")
    else:
        driver_list = [driver_string]
    target = cf[section][series]["ERUsingSOLO"]["target"]
    for label in driver_list:
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,label)
        if numpy.ma.count_masked(data)!=0:
            logger.error("ERUsingSOLO: driver "+label+" contains missing data, skipping target "+target)
            return
    # create the dictionary keys for this series
    solo_info = {}
    # site name
    solo_info["site_name"] = ds.globalattributes["site_name"]
    # source series for ER
    opt = pfp_utils.get_keyvaluefromcf(cf, [section,series,"ERUsingSOLO"], "source", default="Fc")
    solo_info["source"] = opt
    # target series name
    solo_info["target"] = target
    # list of drivers
    solo_info["drivers"] = driver_list
    # name of SOLO output series in ds
    solo_info["output"] = cf[section][series]["ERUsingSOLO"]["output"]
    # results of best fit for plotting later on
    solo_info["results"] = {"startdate":[],"enddate":[],"No. points":[],"r":[],
                            "Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                            "Avg (obs)":[],"Avg (SOLO)":[],
                            "Var (obs)":[],"Var (SOLO)":[],"Var ratio":[],
                            "m_ols":[],"b_ols":[]}
    # create an empty series in ds if the SOLO output series doesn't exist yet
    if solo_info["output"] not in ds.series.keys():
        data,flag,attr = pfp_utils.MakeEmptySeries(ds,solo_info["output"])
        pfp_utils.CreateSeries(ds,solo_info["output"],data,flag,attr)
    # create the merge directory in the data structure
    if "merge" not in dir(ds): ds.merge = {}
    if "standard" not in ds.merge.keys(): ds.merge["standard"] = {}
    # create the dictionary keys for this series
    ds.merge["standard"][series] = {}
    # output series name
    ds.merge["standard"][series]["output"] = series
    # source
    source_string = cf[section][series]["MergeSeries"]["Source"]
    if "," in source_string:
        source_list = source_string.split(",")
    else:
        source_list = [source_string]
    ds.merge["standard"][series]["source"] = source_list
    # create an empty series in ds if the output series doesn't exist yet
    if ds.merge["standard"][series]["output"] not in ds.series.keys():
        data,flag,attr = pfp_utils.MakeEmptySeries(ds,ds.merge["standard"][series]["output"])
        pfp_utils.CreateSeries(ds,ds.merge["standard"][series]["output"],data,flag,attr)
    return solo_info

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

def rpSOLO_main(ds, solo_info):
    """
    This is the main routine for running SOLO, an artifical neural network for estimating ER.
    """
    startdate = solo_info["startdate"]
    enddate = solo_info["enddate"]
    logger.info(" Estimating ER using SOLO: "+startdate+" to "+enddate)
    solo_series = solo_info["er"].keys()
    ## read the control file again, this allows the contents of the control file to
    ## be changed with the SOLO GUI still displayed
    #cfname = ds.globalattributes["controlfile_name"]
    #cf = pfp_io.get_controlfilecontents(cfname,mode="quiet")
    #for series in solo_series:
        #section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
        #if len(section)==0: continue
        #if series not in ds.series.keys(): continue
        #solo_info["er"][series]["target"] = cf[section][series]["ERUsingSOLO"]["target"]
        #input_string = cf[section][series]["ERUsingSOLO"]["drivers"]
        #solo_info["er"][series]["drivers"] = pfp_cfg.cfg_string_to_list(input_string)
        #solo_info["er"][series]["output"] = cf[section][series]["ERUsingSOLO"]["output"]
    # get some useful things
    site_name = ds.globalattributes["site_name"]
    # get the time step and a local pointer to the datetime series
    ts = ds.globalattributes["time_step"]
    ldt = ds.series["DateTime"]["Data"]
    xldt = ds.series["xlDateTime"]["Data"]
    # get the start and end datetime indices
    si = pfp_utils.GetDateIndex(ldt,startdate,ts=ts,default=0,match="exact")
    ei = pfp_utils.GetDateIndex(ldt,enddate,ts=ts,default=-1,match="exact")
    # check the start and end indices
    if si >= ei:
        logger.error(" ERUsingSOLO: end datetime index ("+str(ei)+") smaller that start ("+str(si)+")")
        return
    if si==0 and ei==-1:
        logger.error(" ERUsingSOLO: no start and end datetime specified, using all data")
        nRecs = int(ds.globalattributes["nc_nrecs"])
    else:
        nRecs = ei - si + 1
    # get the minimum number of points from the minimum percentage
    solo_info["min_points"] = int((ei-si)*solo_info["min_percent"]/100)
    # get the figure number
    if len(plt.get_fignums())==0:
        fig_num = 0
    else:
        #fig_nums = plt.get_fignums()
        #fig_num = fig_nums[-1]
        fig_num = plt.get_fignums()[-1]
    # loop over the series to be gap filled using solo
    for series in solo_series:
        solo_info["er"][series]["results"]["startdate"].append(xldt[si])
        solo_info["er"][series]["results"]["enddate"].append(xldt[ei])
        target = solo_info["er"][series]["target"]
        d,f,a = pfp_utils.GetSeriesasMA(ds,target,si=si,ei=ei)
        if numpy.ma.count(d)<solo_info["min_points"]:
            logger.error("rpSOLO: Less than "+str(solo_info["min_points"])+" points available for series "+target+" ...")
            solo_info["er"][series]["results"]["No. points"].append(float(0))
            results_list = solo_info["er"][series]["results"].keys()
            for item in ["startdate","enddate","No. points"]:
                if item in results_list: results_list.remove(item)
            for item in results_list:
                solo_info["er"][series]["results"][item].append(float(c.missing_value))
            continue
        drivers = solo_info["er"][series]["drivers"]
        output = solo_info["er"][series]["output"]
        # set the number of nodes for the inf files
        #if solo_info["call_mode"].lower()=="interactive":
            #nodesAuto = rpSOLO_setnodesEntry(SOLO_gui,drivers,default=10)
        # write the inf files for sofm, solo and seqsolo
        # check this one for SOLO_gui change to solo_info
        rpSOLO_writeinffiles(solo_info)
        # run SOFM
        # check this one for SOLO_gui change to solo_info
        result = rpSOLO_runsofm(ds,solo_info,drivers,target,nRecs,si=si,ei=ei)
        if result!=1: return
        # run SOLO
        result = rpSOLO_runsolo(ds,drivers,target,nRecs,si=si,ei=ei)
        if result!=1: return
        # run SEQSOLO and put the SOLO data into the data structure
        result = rpSOLO_runseqsolo(ds,drivers,target,output,nRecs,si=si,ei=ei)
        if result!=1: return
        # plot the results
        fig_num = fig_num + 1
        title = site_name+" : "+series+" estimated using SOLO"
        pd = rpSOLO_initplot(site_name=site_name,label=target,fig_num=fig_num,title=title,
                             nDrivers=len(drivers),startdate=startdate,enddate=enddate)
        rpSOLO_plot(pd,ds,series,drivers,target,output,solo_info,si=si,ei=ei)
        # reset the nodesEntry in the SOLO_gui
        #if solo_info["call_mode"].lower()=="interactive":
            #if nodesAuto: rpSOLO_resetnodesEntry(SOLO_gui)
    #if 'ERUsingSOLO' not in ds.globalattributes['Functions']:
        #ds.globalattributes['Functions'] = ds.globalattributes['Functions']+', ERUsingSOLO'

def rpSOLO_plot(pd,ds,series,driverlist,targetlabel,outputlabel,solo_info,si=0,ei=-1):
    """ Plot the results of the SOLO run. """
    # get the time step
    ts = int(ds.globalattributes['time_step'])
    # get a local copy of the datetime series
    dt = ds.series['DateTime']['Data'][si:ei+1]
    xdt = numpy.array(dt)
    Hdh,f,a = pfp_utils.GetSeriesasMA(ds,'Hdh',si=si,ei=ei)
    # get the observed and modelled values
    obs,f,a = pfp_utils.GetSeriesasMA(ds,targetlabel,si=si,ei=ei)
    mod,f,a = pfp_utils.GetSeriesasMA(ds,outputlabel,si=si,ei=ei)
    # make the figure
    if solo_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"],figsize=(13,8))
    fig.clf()
    fig.canvas.set_window_title(targetlabel+" (SOLO): "+pd["startdate"]+" to "+pd["enddate"])
    plt.figtext(0.5,0.95,pd["title"],ha='center',size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask,mod.mask)
    obs_mor = numpy.ma.array(obs,mask=mask)
    dstats = rp_getdiurnalstats(dt,obs_mor,solo_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'b-',label="Obs")
    # get the diurnal stats of all SOLO predictions
    dstats = rp_getdiurnalstats(dt,mod,solo_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'r-',label="SOLO(all)")
    mod_mor = numpy.ma.masked_where(numpy.ma.getmaskarray(obs)==True,mod,copy=True)
    dstats = rp_getdiurnalstats(dt,mod_mor,solo_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'g-',label="SOLO(obs)")
    plt.xlim(0,24)
    plt.xticks([0,6,12,18,24])
    ax1.set_ylabel(targetlabel)
    ax1.set_xlabel('Hour')
    ax1.legend(loc='upper right',frameon=False,prop={'size':8})
    # XY plot of the 30 minute data
    rect2 = [0.40,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    ax2 = plt.axes(rect2)
    ax2.plot(mod,obs,'b.')
    ax2.set_ylabel(targetlabel+'_obs')
    ax2.set_xlabel(targetlabel+'_SOLO')
    # plot the best fit line
    coefs = numpy.ma.polyfit(numpy.ma.copy(mod),numpy.ma.copy(obs),1)
    xfit = numpy.ma.array([numpy.ma.minimum(mod),numpy.ma.maximum(mod)])
    yfit = numpy.polyval(coefs,xfit)
    r = numpy.ma.corrcoef(mod,obs)
    ax2.plot(xfit,yfit,'r--',linewidth=3)
    eqnstr = 'y = %.3fx + %.3f, r = %.3f'%(coefs[0],coefs[1],r[0][1])
    ax2.text(0.5,0.875,eqnstr,fontsize=8,horizontalalignment='center',transform=ax2.transAxes)
    # write the fit statistics to the plot
    numpoints = numpy.ma.count(obs)
    numfilled = numpy.ma.count(mod)-numpy.ma.count(obs)
    diff = mod - obs
    bias = numpy.ma.average(diff)
    solo_info["er"][series]["results"]["Bias"].append(bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    plt.figtext(0.65,0.225,'No. points')
    plt.figtext(0.75,0.225,str(numpoints))
    solo_info["er"][series]["results"]["No. points"].append(numpoints)
    plt.figtext(0.65,0.200,'Nodes')
    plt.figtext(0.75,0.200,str(solo_info["nodes"]))
    plt.figtext(0.65,0.175,'Training')
    plt.figtext(0.75,0.175,str(solo_info["training"]))
    plt.figtext(0.65,0.150,'Nda factor')
    plt.figtext(0.75,0.150,str(solo_info["nda_factor"]))
    plt.figtext(0.65,0.125,'Learning rate')
    plt.figtext(0.75,0.125,str(solo_info["learningrate"]))
    plt.figtext(0.65,0.100,'Iterations')
    plt.figtext(0.75,0.100,str(solo_info["iterations"]))
    plt.figtext(0.815,0.225,'No. filled')
    plt.figtext(0.915,0.225,str(numfilled))
    plt.figtext(0.815,0.200,'Slope')
    plt.figtext(0.915,0.200,str(pfp_utils.round2sig(coefs[0],sig=4)))
    solo_info["er"][series]["results"]["m_ols"].append(coefs[0])
    plt.figtext(0.815,0.175,'Offset')
    plt.figtext(0.915,0.175,str(pfp_utils.round2sig(coefs[1],sig=4)))
    solo_info["er"][series]["results"]["b_ols"].append(coefs[1])
    plt.figtext(0.815,0.150,'r')
    plt.figtext(0.915,0.150,str(pfp_utils.round2sig(r[0][1],sig=4)))
    solo_info["er"][series]["results"]["r"].append(r[0][1])
    plt.figtext(0.815,0.125,'RMSE')
    plt.figtext(0.915,0.125,str(pfp_utils.round2sig(rmse,sig=4)))
    solo_info["er"][series]["results"]["RMSE"].append(rmse)
    var_obs = numpy.ma.var(obs)
    solo_info["er"][series]["results"]["Var (obs)"].append(var_obs)
    var_mod = numpy.ma.var(mod)
    solo_info["er"][series]["results"]["Var (SOLO)"].append(var_mod)
    solo_info["er"][series]["results"]["Var ratio"].append(var_obs/var_mod)
    solo_info["er"][series]["results"]["Avg (obs)"].append(numpy.ma.average(obs))
    solo_info["er"][series]["results"]["Avg (SOLO)"].append(numpy.ma.average(mod))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"],pd["ts_bottom"],pd["ts_width"],pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    #ts_axes[0].plot(xdt,obs,'b.',xdt,mod,'r-')
    ts_axes[0].scatter(xdt,obs,c=Hdh)
    ts_axes[0].plot(xdt,mod,'r-')
    plt.axhline(0)
    ts_axes[0].set_xlim(xdt[0],xdt[-1])
    TextStr = targetlabel+'_obs ('+ds.series[targetlabel]['Attr']['units']+')'
    ts_axes[0].text(0.05,0.85,TextStr,color='b',horizontalalignment='left',transform=ts_axes[0].transAxes)
    TextStr = outputlabel+'('+ds.series[outputlabel]['Attr']['units']+')'
    ts_axes[0].text(0.85,0.85,TextStr,color='r',horizontalalignment='right',transform=ts_axes[0].transAxes)
    for ThisOne,i in zip(driverlist,range(1,pd["nDrivers"]+1)):
        this_bottom = pd["ts_bottom"] + i*pd["ts_height"]
        rect = [pd["margin_left"],this_bottom,pd["ts_width"],pd["ts_height"]]
        ts_axes.append(plt.axes(rect,sharex=ts_axes[0]))
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,ThisOne,si=si,ei=ei)
        data_notgf = numpy.ma.masked_where(flag!=0,data)
        data_gf = numpy.ma.masked_where(flag==0,data)
        ts_axes[i].plot(xdt,data_notgf,'b-')
        ts_axes[i].plot(xdt,data_gf,'r-')
        plt.setp(ts_axes[i].get_xticklabels(),visible=False)
        TextStr = ThisOne+'('+ds.series[ThisOne]['Attr']['units']+')'
        ts_axes[i].text(0.05,0.85,TextStr,color='b',horizontalalignment='left',transform=ts_axes[i].transAxes)
    # save a hard copy of the plot
    sdt = xdt[0].strftime("%Y%m%d")
    edt = xdt[-1].strftime("%Y%m%d")
    plot_path = solo_info["plot_path"]+"L6/"
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+pd["site_name"].replace(" ","")+"_SOLO_"+pd["label"]
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    if solo_info["show_plots"]:
        plt.draw()
        plt.ioff()
    else:
        plt.ion()

def rpSOLO_run_gui(solo_gui):
    # local pointers to useful things
    ds = solo_gui.dsa
    #dsb = solo_gui.dsb
    solo_info = solo_gui.solo_info
    # populate the solo_info dictionary with more useful things
    if str(solo_gui.radioButtons.checkedButton().text()) == "Manual":
        solo_info["peropt"] = 1
    elif str(solo_gui.radioButtons.checkedButton().text()) == "Months":
        solo_info["peropt"] = 2
    elif str(solo_gui.radioButtons.checkedButton().text()) == "Days":
        solo_info["peropt"] = 3

    solo_info["overwrite"] = solo_gui.checkBox_Overwrite.isChecked()
    solo_info["show_plots"] = solo_gui.checkBox_ShowPlots.isChecked()
    solo_info["show_all"] = solo_gui.checkBox_PlotAll.isChecked()
    solo_info["auto_complete"] = solo_gui.checkBox_AutoComplete.isChecked()
    solo_info["min_percent"] = max(int(str(solo_gui.lineEdit_MinPercent.text())), 1)

    solo_info["nodes"] = str(solo_gui.lineEdit_Nodes.text())
    solo_info["training"] = str(solo_gui.lineEdit_Training.text())
    solo_info["nda_factor"] = str(solo_gui.lineEdit_NdaFactor.text())
    solo_info["learningrate"] = str(solo_gui.lineEdit_Learning.text())
    solo_info["iterations"] = str(solo_gui.lineEdit_Iterations.text())


    # populate the solo_info dictionary with things that will be useful
    solo_info["site_name"] = ds.globalattributes["site_name"]
    solo_info["time_step"] = int(ds.globalattributes["time_step"])
    solo_info["nperhr"] = int(float(60)/solo_info["time_step"]+0.5)
    solo_info["nperday"] = int(float(24)*solo_info["nperhr"]+0.5)
    solo_info["maxlags"] = int(float(12)*solo_info["nperhr"]+0.5)
    solo_info["tower"] = {}
    solo_info["access"] = {}
    #log.info(" Estimating ER using SOLO")
    if solo_info["peropt"] == 1:
        # manual run using start and end datetime entered via GUI
        logger.info(" Starting manual run ...")
        # get the start and end datetimes entered in the SOLO GUI
        if len(str(solo_gui.lineEdit_StartDate.text())) != 0:
            solo_info["startdate"] = str(solo_gui.lineEdit_StartDate.text())
        if len(str(solo_gui.lineEdit_EndDate.text())) != 0:
            solo_info["enddate"] = str(solo_gui.lineEdit_EndDate.text())
        rpSOLO_main(ds, solo_info)
        logger.info("Finished manual run ...")
    elif solo_info["peropt"] == 2:
        # automatic run with monthly datetime periods
        logger.info("Starting auto (monthly) run ...")
        nMonths = int(solo_gui.lineEdit_NumberMonths.text())
        if len(str(solo_gui.lineEdit_StartDate.text())) != 0:
            solo_info["startdate"] = str(solo_gui.lineEdit_StartDate.text())
        if len(str(solo_gui.lineEdit_EndDate.text())) != 0:
            solo_info["enddate"] = str(solo_gui.lineEdit_EndDate.text())
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
        enddate = min([file_enddate, enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate, "%Y-%m-%d %H:%M")
        while startdate<file_enddate:
            rpSOLO_main(ds, solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d")
        logger.info("Finished auto (monthly) run ...")
    elif solo_info["peropt"] == 3:
        # automatic run with number of days specified by user via the GUI
        logger.info("Starting auto (days) run ...")
        # get the start datetime entered in the SOLO GUI
        nDays = int(solo_gui.lineEdit_NumberDays.text())
        if len(str(solo_gui.lineEdit_StartDate.text())) != 0:
            solo_info["startdate"] = str(solo_gui.lineEdit_StartDate.text())
        if len(solo_gui.lineEdit_EndDate.text()) != 0:
            solo_info["enddate"] = str(solo_gui.lineEdit_EndDate.text())
        solo_info["gui_startdate"] = solo_info["startdate"]
        solo_info["gui_enddate"] = solo_info["enddate"]
        startdate = dateutil.parser.parse(solo_info["startdate"])
        gui_enddate = dateutil.parser.parse(solo_info["gui_enddate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate, enddate, gui_enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate, "%Y-%m-%d %H:%M")
        solo_info["startdate"] = datetime.datetime.strftime(startdate, "%Y-%m-%d %H:%M")
        stopdate = min([file_enddate, gui_enddate])
        while startdate<stopdate:  #file_enddate:
            rpSOLO_main(ds, solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d")
            solo_info["enddate"] = run_enddate.strftime("%Y-%m-%d")
        logger.info("Finished auto (days) run ...")
    elif solo_info["peropt"] == 4:
        ## automatic run with yearly datetime periods
        #rpSOLO_progress(SOLO_gui,"Starting auto (yearly) run ...")
        ## get the start date
        #solo_info["startdate"] = SOLO_gui.startEntry.get()
        #if len(solo_info["startdate"])==0: solo_info["startdate"] = solo_info["file_startdate"]
        #startdate = dateutil.parser.parse(solo_info["startdate"])
        ## get the start year
        #start_year = startdate.year
        #enddate = dateutil.parser.parse(str(start_year+1)+"-01-01 00:00")
        ##file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        #file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        ##enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        #enddate = min([file_enddate,enddate])
        #solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        #while startdate<file_enddate:
            #rpSOLO_main(ds,solo_info,SOLO_gui=SOLO_gui)
            #startdate = enddate
            #enddate = startdate+dateutil.relativedelta.relativedelta(years=1)
            #solo_info["startdate"] = startdate.strftime("%Y-%m-%d")
            #solo_info["enddate"] = enddate.strftime("%Y-%m-%d")
        #rpSOLO_progress(SOLO_gui,"Finished auto (yearly) run ...")
        pass
    elif SOLO_gui.peropt.get()==5:
        pass

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

def rpSOLO_runseqsolo(ds,driverlist,targetlabel,outputlabel,nRecs,si=0,ei=-1):
    '''
    Run SEQSOLO.
    '''
    # get the number of drivers
    ndrivers = len(driverlist)
    # add an extra column for the target data
    seqsoloinputdata = numpy.zeros((nRecs,ndrivers+1))
    # now fill the driver data array
    i = 0
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(ds,TheseOnes,si=si,ei=ei)
        seqsoloinputdata[:,i] = driver[:]
        i = i + 1
    # a clean copy of the target is pulled from the unmodified ds each time
    target,flag,attr = pfp_utils.GetSeries(ds,targetlabel,si=si,ei=ei)
    # now load the target data into the data array
    seqsoloinputdata[:,ndrivers] = target[:]
    # now strip out the bad data
    cind = numpy.zeros(nRecs)
    iind = numpy.arange(nRecs)
    # do only the drivers not the target
    for i in range(ndrivers):
        index = numpy.where(seqsoloinputdata[:,i]==c.missing_value)[0]
        if len(index!=0): cind[index] = 1
    # index of good data
    index = numpy.where(cind==0)[0]
    nRecs_good = len(index)
    gooddata = numpy.zeros((nRecs_good,ndrivers+1))
    for i in range(ndrivers+1):
        gooddata[:,i] = seqsoloinputdata[:,i][index]
    # keep track of the good data indices
    goodindex = iind[index]
    # and then write the seqsolo input file
    seqsolofile = open('solo/input/seqsolo_input.csv','wb')
    wr = csv.writer(seqsolofile,delimiter=',')
    for i in range(gooddata.shape[0]):
        wr.writerow(gooddata[i,0:ndrivers+1])
    seqsolofile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/seqOut2.out'): os.remove('solo/output/seqOut2.out')
    # now run SEQSOLO
    #log.info(' GapFillUsingSOLO: running SEQSOLO')
    seqsolologfile = open('solo/log/seqsolo.log','wb')
    if platform.system()=="Windows":
        subprocess.call(['./solo/bin/seqsolo.exe','solo/inf/seqsolo.inf'],stdout=seqsolologfile)
    else:
        subprocess.call(['./solo/bin/seqsolo','solo/inf/seqsolo.inf'],stdout=seqsolologfile)
    seqsolologfile.close()
    # check to see if the solo output file exists, this is used to indicate that solo ran correctly
    if os.path.exists('solo/output/seqOut2.out'):
        # now read in the seqsolo results, use the seqOut2 file so that the learning capability of
        # seqsolo can be used via the "learning rate" and "Iterations" GUI options
        seqdata = numpy.genfromtxt('solo/output/seqOut2.out')
        # put the SOLO modelled data back into the data series
        if ei==-1:
            ds.series[outputlabel]['Data'][si:][goodindex] = seqdata[:,1]
            ds.series[outputlabel]['Flag'][si:][goodindex] = numpy.int32(30)
        else:
            ds.series[outputlabel]['Data'][si:ei+1][goodindex] = seqdata[:,1]
            ds.series[outputlabel]['Flag'][si:ei+1][goodindex] = numpy.int32(30)
        # set the attributes
        ds.series[outputlabel]["Attr"]["units"] = ds.series[targetlabel]["Attr"]["units"]
        if "modelled by SOLO" not in ds.series[outputlabel]["Attr"]["long_name"]:
            ds.series[outputlabel]["Attr"]["long_name"] = "Ecosystem respiration modelled by SOLO (ANN)"
            ds.series[outputlabel]["Attr"]["comment1"] = "Target was "+str(targetlabel)
            ds.series[outputlabel]["Attr"]["comment2"] = "Drivers were "+str(driverlist)
        return 1
    else:
        logger.error(' SOLO_runseqsolo: SEQSOLO did not run correctly, check the SOLO GUI and the log files')
        return 0

def rpSOLO_runsofm(ds,SOLO_gui,driverlist,targetlabel,nRecs,si=0,ei=-1):
    """
    Run sofm, the pre-processor for SOLO.
    """
    # get the number of drivers
    ndrivers = len(driverlist)
    # add an extra column for the target data
    sofminputdata = numpy.zeros((nRecs,ndrivers))
    # now fill the driver data array
    i = 0
    badlines = []
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(ds,TheseOnes,si=si,ei=ei)
        index = numpy.where(abs(driver-float(c.missing_value))<c.eps)[0]
        if len(index)!=0:
            logger.error(' SOLO_runsofm: c.missing_value found in driver '+TheseOnes+' at lines '+str(index))
            badlines = badlines+index.tolist()
        sofminputdata[:,i] = driver[:]
        i = i + 1
    if len(badlines)!=0:
        nBad = len(badlines)
        goodlines = [x for x in range(0,nRecs) if x not in badlines]
        sofminputdata = sofminputdata[goodlines,:]
        logger.info(' SOLO_runsofm: removed '+str(nBad)+' lines from sofm input file')
        nRecs = len(goodlines)
    # now write the drivers to the SOFM input file
    sofmfile = open('solo/input/sofm_input.csv','wb')
    wr = csv.writer(sofmfile,delimiter=',')
    for i in range(sofminputdata.shape[0]):
        wr.writerow(sofminputdata[i,0:ndrivers])
    sofmfile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/sofm_4.out'): os.remove('solo/output/sofm_4.out')
    # now run SOFM
    sofmlogfile = open('solo/log/sofm.log','wb')
    if platform.system()=="Windows":
        subprocess.call(['./solo/bin/sofm.exe','solo/inf/sofm.inf'],stdout=sofmlogfile)
    else:
        subprocess.call(['./solo/bin/sofm','solo/inf/sofm.inf'],stdout=sofmlogfile)
    sofmlogfile.close()
    # check to see if the sofm output file exists, this is used to indicate that sofm ran correctly
    if os.path.exists('solo/output/sofm_4.out'):
        return 1
    else:
        logger.error(' SOLO_runsofm: SOFM did not run correctly, check the GUI and the log files')
        return 0

def rpSOLO_runsolo(ds,driverlist,targetlabel,nRecs,si=0,ei=-1):
    '''
    Run SOLO.
    '''
    ndrivers = len(driverlist)
    # add an extra column for the target data
    soloinputdata = numpy.zeros((nRecs,ndrivers+1))
    # now fill the driver data array, drivers come from the modified ds
    i = 0
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(ds,TheseOnes,si=si,ei=ei)
        soloinputdata[:,i] = driver[:]
        i = i + 1
    # a clean copy of the target is pulled from the ds each time
    target,flag,attr = pfp_utils.GetSeries(ds,targetlabel,si=si,ei=ei)
    # now load the target data into the data array
    soloinputdata[:,ndrivers] = target[:]
    # now strip out the bad data
    cind = numpy.zeros(nRecs)
    for i in range(ndrivers+1):
        index = numpy.where(soloinputdata[:,i]==c.missing_value)[0]
        if len(index!=0): cind[index] = 1
    index = numpy.where(cind==0)[0]
    nRecs_good = len(index)
    gooddata = numpy.zeros((nRecs_good,ndrivers+1))
    for i in range(ndrivers+1):
        gooddata[:,i] = soloinputdata[:,i][index]
    # and then write the solo input file, the name is assumed by the solo.inf control file
    solofile = open('solo/input/solo_input.csv','wb')
    wr = csv.writer(solofile,delimiter=',')
    for i in range(gooddata.shape[0]):
        wr.writerow(gooddata[i,0:ndrivers+1])
    solofile.close()
    # if the output file from a previous run exists, delete it
    if os.path.exists('solo/output/eigenValue.out'): os.remove('solo/output/eigenValue.out')
    # now run SOLO
    #log.info(' GapFillUsingSOLO: running SOLO')
    solologfile = open('solo/log/solo.log','wb')
    if platform.system()=="Windows":
        subprocess.call(['./solo/bin/solo.exe','solo/inf/solo.inf'],stdout=solologfile)
    else:
        subprocess.call(['./solo/bin/solo','solo/inf/solo.inf'],stdout=solologfile)
    solologfile.close()
    # check to see if the solo output file exists, this is used to indicate that solo ran correctly
    if os.path.exists('solo/output/eigenValue.out'):
        return 1
    else:
        logger.error(' SOLO_runsolo: SOLO did not run correctly, check the SOLO GUI and the log files')
        return 0

def rpSOLO_writeinffiles(solo_info):
    # sofm inf file
    f = open('solo/inf/sofm.inf','w')
    f.write(str(solo_info["nodes"])+'\n')
    f.write(str(solo_info["training"])+'\n')
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
    f.write(str(solo_info["nodes"])+'\n')
    f.write(str(solo_info["nda_factor"])+'\n')
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
    f.write(str(solo_info["nodes"])+'\n')
    f.write(str(0)+'\n')
    f.write(str(solo_info["learningrate"])+'\n')
    f.write(str(solo_info["iterations"])+'\n')
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
