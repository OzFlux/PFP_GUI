# standard modules
import ast
import csv
import datetime
import logging
import os
import platform
import subprocess
import Tkinter
# 3rd party modules
import dateutil
import matplotlib.dates as mdt
import matplotlib.pyplot as plt
import numpy
import pylab
# PFP modules
import constants as c
import pfp_ck
import pfp_io
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

# functions for GapFillUsingSOLO
def GapFillUsingSOLO(cf, dsa, dsb):
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
    dsb.returncodes["solo"] = "normal"
    if "solo" not in dir(dsb):
        return
    # local pointer to the datetime series
    ldt = dsb.series["DateTime"]["Data"]
    startdate = ldt[0]
    enddate = ldt[-1]
    solo_info = {"file_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                 "file_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                 "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                 "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "call_mode", default="interactive")
    solo_info["call_mode"]= call_mode
    if call_mode.lower()=="interactive":
        solo_info["show_plots"] = True
    if call_mode.lower()=="interactive":
        # put up a plot of the data coverage at L4
        gfSOLO_plotcoveragelines(dsb, solo_info)
        # call the GapFillUsingSOLO GUI
        gfSOLO_gui(dsa, dsb, solo_info)
    else:
        if "GUI" in cf:
            if "SOLO" in cf["GUI"]:
                gfSOLO_run_nogui(cf, dsa, dsb, solo_info)
            else:
                logger.warning(" No GUI sub-section found in Options section of control file")
                gfSOLO_plotcoveragelines(dsb, solo_info)
                gfSOLO_gui(dsa, dsb, solo_info)
        else:
            logger.warning(" No GUI sub-section found in Options section of control file")
            gfSOLO_plotcoveragelines(dsb, solo_info)
            gfSOLO_gui(dsa, dsb, solo_info)

def  gfSOLO_gui(dsa, dsb, solo_info):
    ldt = dsb.series["DateTime"]["Data"]
    # set up the GUI
    solo_gui = Tkinter.Toplevel()
    solo_gui.wm_title("SOLO GUI (Fluxes)")
    solo_gui.grid()
    # top row
    nrow = 0
    solo_gui.nodesLabel = Tkinter.Label(solo_gui,text="Nodes")
    solo_gui.nodesLabel.grid(row=nrow,column=0,columnspan=1,sticky="E")
    solo_gui.nodesEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.nodesEntry.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.nodesEntry.insert(0,"Auto")
    solo_gui.trainingLabel = Tkinter.Label(solo_gui,text="Training")
    solo_gui.trainingLabel.grid(row=nrow,column=2,columnspan=1,sticky="E")
    solo_gui.trainingEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.trainingEntry.grid(row=nrow,column=3,columnspan=1,sticky="W")
    solo_gui.trainingEntry.insert(0,"500")
    solo_gui.factorLabel = Tkinter.Label(solo_gui,text="Nda factor")
    solo_gui.factorLabel.grid(row=nrow,column=4,columnspan=1,sticky="E")
    solo_gui.factorEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.factorEntry.grid(row=nrow,column=5,columnspan=1,sticky="W")
    solo_gui.factorEntry.insert(0,"5")
    # second row
    nrow = nrow + 1
    solo_gui.learningrateLabel = Tkinter.Label(solo_gui,text="Learning")
    solo_gui.learningrateLabel.grid(row=nrow,column=2,columnspan=1,sticky="E")
    solo_gui.learningrateEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.learningrateEntry.grid(row=nrow,column=3,columnspan=1,sticky="W")
    solo_gui.learningrateEntry.insert(0,"0.001")
    solo_gui.iterationsLabel = Tkinter.Label(solo_gui,text="Iterations")
    solo_gui.iterationsLabel.grid(row=nrow,column=4,columnspan=1,sticky="E")
    solo_gui.iterationsEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.iterationsEntry.grid(row=nrow,column=5,columnspan=1,sticky="W")
    solo_gui.iterationsEntry.insert(0,"500")
    # third row
    nrow = nrow + 1
    solo_gui.filestartLabel = Tkinter.Label(solo_gui,text="File start date")
    solo_gui.filestartLabel.grid(row=nrow,column=0,columnspan=3)
    solo_gui.fileendLabel = Tkinter.Label(solo_gui,text="File end date")
    solo_gui.fileendLabel.grid(row=nrow,column=3,columnspan=3)
    # fourth row
    nrow = nrow + 1
    solo_gui.filestartValue = Tkinter.Label(solo_gui,text=str(ldt[0]))
    solo_gui.filestartValue.grid(row=nrow,column=0,columnspan=3)
    solo_gui.fileendValue = Tkinter.Label(solo_gui,text=str(ldt[-1]))
    solo_gui.fileendValue.grid(row=nrow,column=3,columnspan=3)
    # fifth row
    nrow = nrow + 1
    solo_gui.startLabel = Tkinter.Label(solo_gui, text="Start date (YYYY-MM-DD)")
    solo_gui.startLabel.grid(row=nrow,column=0,columnspan=3)
    solo_gui.startEntry = Tkinter.Entry(solo_gui)
    solo_gui.startEntry.grid(row=nrow,column=3,columnspan=3)
    # sixth row
    nrow = nrow + 1
    solo_gui.endLabel = Tkinter.Label(solo_gui, text="End date   (YYYY-MM-DD)")
    solo_gui.endLabel.grid(row=nrow,column=0,columnspan=3)
    solo_gui.endEntry = Tkinter.Entry(solo_gui)
    solo_gui.endEntry.grid(row=nrow,column=3,columnspan=3)
    # seventh row
    nrow = nrow + 1
    solo_gui.peropt = Tkinter.IntVar()
    solo_gui.peropt.set(2)
    solo_gui.manualperiod = Tkinter.Radiobutton(solo_gui,text="Manual",variable=solo_gui.peropt,value=1)
    solo_gui.manualperiod.grid(row=nrow,column=0,columnspan=1,sticky="W")
    #solo_gui.manualperiod = Tkinter.Radiobutton(solo_gui,text="Auto",variable=solo_gui.peropt,value=4)
    #solo_gui.manualperiod.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.minptsLabel = Tkinter.Label(solo_gui,text="Min. pts (%)")
    solo_gui.minptsLabel.grid(row=nrow,column=3,columnspan=1,sticky="E")
    solo_gui.minptsEntry = Tkinter.Entry(solo_gui,width=5)
    solo_gui.minptsEntry.grid(row=nrow,column=4,columnspan=1,sticky="W")
    solo_gui.minptsEntry.insert(0,"25")
    # eigth row
    nrow = nrow + 1
    solo_gui.automonthly = Tkinter.Radiobutton(solo_gui,text="Monthly",variable=solo_gui.peropt,value=2)
    solo_gui.automonthly.grid(row=nrow,column=0,columnspan=1,sticky="W")
    solo_gui.daysLabel = Tkinter.Radiobutton(solo_gui,text="Days",variable=solo_gui.peropt,value=3)
    solo_gui.daysLabel.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.daysEntry = Tkinter.Entry(solo_gui,width=3)
    solo_gui.daysEntry.grid(row=nrow,column=2,columnspan=1,sticky="W")
    solo_gui.daysEntry.insert(0,"90")
    solo_gui.autocompleteopt = Tkinter.IntVar()
    solo_gui.autocompleteopt.set(1)
    solo_gui.autocomplete = Tkinter.Checkbutton(solo_gui, text="Auto complete", variable=solo_gui.autocompleteopt)
    solo_gui.autocomplete.grid(row=nrow,column=3,columnspan=3,sticky="w")
    # ninth row
    nrow = nrow + 1
    solo_gui.pltopt = Tkinter.IntVar()
    solo_gui.pltopt.set(1)
    solo_gui.showplots = Tkinter.Checkbutton(solo_gui, text="Show plots", variable=solo_gui.pltopt)
    solo_gui.showplots.grid(row=nrow,column=0,columnspan=3,sticky="w")
    solo_gui.owopt = Tkinter.IntVar()
    solo_gui.owopt.set(0)
    solo_gui.overwrite = Tkinter.Checkbutton(solo_gui, text="Overwrite", variable=solo_gui.owopt)
    solo_gui.overwrite.grid(row=nrow,column=3,columnspan=3,sticky="w")
    # tenth row
    nrow = nrow + 1
    solo_gui.doneButton = Tkinter.Button (solo_gui, text="Done",command=lambda:gfSOLO_done(dsb,solo_gui,solo_info))
    solo_gui.doneButton.grid(row=nrow,column=0,columnspan=2)
    solo_gui.runButton = Tkinter.Button (solo_gui, text="Run",command=lambda:gfSOLO_run_gui(dsa,dsb,solo_gui,solo_info))
    solo_gui.runButton.grid(row=nrow,column=2,columnspan=2)
    solo_gui.quitButton = Tkinter.Button (solo_gui, text="Quit",command=lambda:gfSOLO_quit(dsb,solo_gui))
    solo_gui.quitButton.grid(row=nrow,column=4,columnspan=2)
    # eleventh row
    nrow = nrow + 1
    solo_gui.progress_row = nrow
    solo_gui.progress = Tkinter.Label(solo_gui, text='Waiting for input ...')
    solo_gui.progress.grid(row=nrow,column=0,columnspan=6,sticky="W")

    solo_gui.wait_window(solo_gui)

def gfSOLO_autocomplete(dsa, dsb, solo_info):
    if not solo_info["auto_complete"]: return
    ldt = dsb.series["DateTime"]["Data"]
    nRecs = len(ldt)
    for output in dsb.solo.keys():
        not_enough_points = False
        series = dsb.solo[output]["label_tower"]
        data_solo, _, _ = pfp_utils.GetSeriesasMA(dsb, output)
        if numpy.ma.count(data_solo)==0:
            continue
        mask_solo = numpy.ma.getmaskarray(data_solo)
        gapstartend = pfp_utils.contiguous_regions(mask_solo)
        data_obs, _, _ = pfp_utils.GetSeriesasMA(dsb, series)
        for si_gap, ei_gap in gapstartend:
            min_points = int((ei_gap-si_gap)*solo_info["min_percent"]/100)
            num_good_points = numpy.ma.count(data_obs[si_gap:ei_gap])
            while num_good_points < min_points:
                si_gap = max([0, si_gap - solo_info["nperday"]])
                ei_gap = min([nRecs-1, ei_gap + solo_info["nperday"]])
                if si_gap == 0 and ei_gap == nRecs-1:
                    msg = " Unable to find enough good points in series "+series
                    logger.error(msg)
                    not_enough_points = True
                if not_enough_points:
                    break
                min_points = int((ei_gap-si_gap)*solo_info["min_percent"]/100)
                num_good_points = numpy.ma.count(data_obs[si_gap:ei_gap])
            if not_enough_points:
                break
            si = max([0, si_gap])
            ei = min([len(ldt)-1, ei_gap])
            solo_info["startdate"] = ldt[si].strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = ldt[ei].strftime("%Y-%m-%d %H:%M")
            gfSOLO_main(dsa, dsb, solo_info, output_list=[output])
            gfSOLO_plotcoveragelines(dsb, solo_info)

def gfSOLO_done(ds,solo_gui,solo_info):
    # plot the summary statistics if gap filling was done manually
    if solo_gui.peropt.get()==1:
        # write Excel spreadsheet with fit statistics
        pfp_io.xl_write_SOLOStats(ds)
        # plot the summary statistics
        gfSOLO_plotsummary(ds,solo_info)
    # destroy the SOLO GUI
    solo_gui.destroy()
    # remove the solo dictionary from the data structure
    ds.returncodes["solo"] = "normal"

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

def gfSOLO_main(dsa,dsb,solo_info,output_list=[]):
    '''
    This is the main routine for running SOLO, an artifical neural network for gap filling fluxes.
    '''
    if len(output_list)==0: output_list = dsb.solo.keys()
    startdate = solo_info["startdate"]
    enddate = solo_info["enddate"]
    logger.info(" Gap filling using SOLO: "+startdate+" to "+enddate)
    # read the control file again, this allows the contents of the control file to
    # be changed with the SOLO GUI still displayed
    cfname = dsb.globalattributes["controlfile_name"]
    cf = pfp_io.get_controlfilecontents(cfname,mode="quiet")
    solo_info["plot_path"] = cf["Files"]["plot_path"]
    # put the control file object in the solo_info dictionary
    dsb.cf = cf.copy()
    # get some useful things
    site_name = dsa.globalattributes["site_name"]
    # get the time step and a local pointer to the datetime series
    ts = dsb.globalattributes["time_step"]
    ldt = dsb.series["DateTime"]["Data"]
    xldt = dsb.series["xlDateTime"]["Data"]
    # get the start and end datetime indices
    si = pfp_utils.GetDateIndex(ldt,startdate,ts=ts,default=0,match="exact")
    ei = pfp_utils.GetDateIndex(ldt,enddate,ts=ts,default=len(ldt)-1,match="exact")
    # check the start and end indices
    if si >= ei:
        msg = " GapFillUsingSOLO: end datetime index ("+str(ei)+") smaller that start ("+str(si)+")"
        logger.warning(msg)
        return
    if si==0 and ei==-1:
        msg = " GapFillUsingSOLO: no start and end datetime specified, using all data"
        logger.warning(msg)
        nRecs = int(dsb.globalattributes["nc_nrecs"])
    else:
        nRecs = ei - si + 1
    # loop over the series to be gap filled using solo
    #solo_info["min_points"] = int(nRecs*solo_info["min_percent"]/100)
    solo_info["min_points"] = int((ei-si)*solo_info["min_percent"]/100)
    # close any open plot windows
    if len(plt.get_fignums())!=0:
        for i in plt.get_fignums():
            if i!=0: plt.close(i)
    fig_num = 0
    for output in output_list:
        # get the target series label
        series = dsb.solo[output]["label_tower"]
        # clean up the target series if required
        variable = pfp_utils.GetVariable(dsb, series)
        pfp_ck.UpdateVariableAttributes_QC(cf, variable)
        pfp_ck.ApplyQCChecks(variable)
        pfp_utils.CreateVariable(dsb, variable)
        # check to see if we are gap filling L5 or L4
        if dsb.globalattributes["nc_level"].lower()=="l4":
            for driver in dsb.solo[output]["drivers"]:
                for mlist in dsb.merge.keys():
                    if driver in dsb.merge[mlist]:
                        srclist = dsb.merge[mlist][driver]["source"]
                pfp_ts.do_mergeseries(dsb,driver,srclist,mode="quiet")
        dsb.solo[output]["results"]["startdate"].append(xldt[si])
        dsb.solo[output]["results"]["enddate"].append(xldt[ei])
        d,f,a = pfp_utils.GetSeriesasMA(dsb,series,si=si,ei=ei)
        if numpy.ma.count(d)<solo_info["min_points"]:
            logger.warning("gfSOLO: Less than "+str(solo_info["min_points"])+" points available for series "+series+" ...")
            dsb.solo[output]["results"]["No. points"].append(float(0))
            results_list = dsb.solo[output]["results"].keys()
            for item in ["startdate","enddate","No. points"]:
                if item in results_list: results_list.remove(item)
            for item in results_list:
                dsb.solo[output]["results"][item].append(float(c.missing_value))
            continue
        drivers = dsb.solo[output]["drivers"]
        if str(solo_info["nodes"]).lower()=="auto":
            solo_info["nodes_target"] = len(drivers)+1
        else:
            solo_info["nodes_target"] = int(solo_info["nodes"])
        #output = dsb.solo[series]["output"]
        # set the number of nodes for the inf files
        #nodesAuto = gfSOLO_setnodesEntry(solo_gui,drivers)
        # overwrite the GUI settings if required
        if "solo_settings" in dsb.solo[output]:
            solo_info["nodes_target"] = dsb.solo[output]["solo_settings"]["nodes_target"]
            solo_info["training"] = dsb.solo[output]["solo_settings"]["training"]
            solo_info["factor"] = dsb.solo[output]["solo_settings"]["factor"]
            solo_info["learningrate"] = dsb.solo[output]["solo_settings"]["learningrate"]
            solo_info["iterations"] = dsb.solo[output]["solo_settings"]["iterations"]
        # write the inf files for sofm, solo and seqsolo
        gfSOLO_writeinffiles(solo_info)
        # run SOFM
        result = gfSOLO_runsofm(dsa,dsb,drivers,series,nRecs,si=si,ei=ei)
        if result!=1: return
        # run SOLO
        result = gfSOLO_runsolo(dsa,dsb,drivers,series,nRecs,si=si,ei=ei)
        if result!=1: return
        # run seqsolo and put the solo_modelled data into the ds series
        result = gfSOLO_runseqsolo(dsa,dsb,drivers,series,output,nRecs,si=si,ei=ei)
        if result!=1: return
        # plot the results
        fig_num = fig_num + 1
        title = site_name+' : Comparison of tower and SOLO data for '+series
        pd = gfSOLO_initplot(site_name=site_name,label=series,fig_num=fig_num,title=title,
                             nDrivers=len(drivers))
        gfSOLO_plot(pd,dsa,dsb,drivers,series,output,solo_info,si=si,ei=ei)
        # reset the nodesEntry in the solo_gui
        #if nodesAuto: gfSOLO_resetnodesEntry(solo_gui)
    if 'GapFillUsingSOLO' not in dsb.globalattributes['Functions']:
        dsb.globalattributes['Functions'] = dsb.globalattributes['Functions']+', GapFillUsingSOLO'

def gfSOLO_plot(pd,dsa,dsb,driverlist,targetlabel,outputlabel,solo_info,si=0,ei=-1):
    """ Plot the results of the SOLO run. """
    # get the time step
    ts = int(dsb.globalattributes['time_step'])
    # get a local copy of the datetime series
    xdt = dsb.series["DateTime"]["Data"][si:ei+1]
    Hdh,f,a = pfp_utils.GetSeriesasMA(dsb,'Hdh',si=si,ei=ei)
    # get the observed and modelled values
    obs,f,a = pfp_utils.GetSeriesasMA(dsb,targetlabel,si=si,ei=ei)
    mod,f,a = pfp_utils.GetSeriesasMA(dsb,outputlabel,si=si,ei=ei)
    # make the figure
    if solo_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"],figsize=(13,8))
    fig.clf()
    fig.canvas.set_window_title(targetlabel)
    plt.figtext(0.5,0.95,pd["title"],ha='center',size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask,mod.mask)
    obs_mor = numpy.ma.array(obs,mask=mask)
    Num1,Hr1,Av1,Sd1,Mx1,Mn1 = gf_getdiurnalstats(Hdh,obs_mor,ts)
    ax1.plot(Hr1,Av1,'b-',label="Obs")
    # get the diurnal stats of all SOLO predictions
    Num2,Hr2,Av2,Sd2,Mx2,Mn2 = gf_getdiurnalstats(Hdh,mod,ts)
    ax1.plot(Hr2,Av2,'r-',label="SOLO(all)")
    # get the diurnal stats of SOLO predictions when the obs are present
    mod_mor = numpy.ma.array(mod,mask=mask)
    if numpy.ma.count_masked(obs)!=0:
        index = numpy.where(numpy.ma.getmaskarray(obs)==False)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(obs)==False)[0]
        # get the diurnal stats of SOLO predictions when observations are present
        Num3,Hr3,Av3,Sd3,Mx3,Mn3=gf_getdiurnalstats(Hdh[index],mod_mor[index],ts)
        ax1.plot(Hr3,Av3,'g-',label="SOLO(obs)")
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
    numpoints = trap_masked_constant(numpy.ma.count(obs))
    numfilled = trap_masked_constant(numpy.ma.count(mod)-numpy.ma.count(obs))
    diff = mod - obs
    bias = trap_masked_constant(numpy.ma.average(diff))
    fractional_bias = trap_masked_constant(bias/(0.5*(numpy.ma.average(obs+mod))))
    dsb.solo[outputlabel]["results"]["Bias"].append(bias)
    dsb.solo[outputlabel]["results"]["Frac Bias"].append(fractional_bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    mean_mod = numpy.ma.mean(mod)
    mean_obs = numpy.ma.mean(obs)
    data_range = numpy.ma.maximum(obs)-numpy.ma.minimum(obs)
    nmse = rmse/data_range
    plt.figtext(0.65,0.225,'No. points')
    plt.figtext(0.75,0.225,str(numpoints))
    dsb.solo[outputlabel]["results"]["No. points"].append(numpoints)
    plt.figtext(0.65,0.200,'No. filled')
    plt.figtext(0.75,0.200,str(numfilled))
    plt.figtext(0.65,0.175,'Nodes')
    plt.figtext(0.75,0.175,str(solo_info["nodes_target"]))
    plt.figtext(0.65,0.150,'Training')
    plt.figtext(0.75,0.150,str(solo_info["training"]))
    plt.figtext(0.65,0.125,'Nda factor')
    plt.figtext(0.75,0.125,str(solo_info["factor"]))
    plt.figtext(0.65,0.100,'Learning rate')
    plt.figtext(0.75,0.100,str(solo_info["learningrate"]))
    plt.figtext(0.65,0.075,'Iterations')
    plt.figtext(0.75,0.075,str(solo_info["iterations"]))
    plt.figtext(0.815,0.225,'Slope')
    plt.figtext(0.915,0.225,str(pfp_utils.round2sig(coefs[0],sig=4)))
    dsb.solo[outputlabel]["results"]["m_ols"].append(trap_masked_constant(coefs[0]))
    plt.figtext(0.815,0.200,'Offset')
    plt.figtext(0.915,0.200,str(pfp_utils.round2sig(coefs[1],sig=4)))
    dsb.solo[outputlabel]["results"]["b_ols"].append(trap_masked_constant(coefs[1]))
    plt.figtext(0.815,0.175,'r')
    plt.figtext(0.915,0.175,str(pfp_utils.round2sig(r[0][1],sig=4)))
    dsb.solo[outputlabel]["results"]["r"].append(trap_masked_constant(r[0][1]))
    plt.figtext(0.815,0.150,'RMSE')
    plt.figtext(0.915,0.150,str(pfp_utils.round2sig(rmse,sig=4)))
    dsb.solo[outputlabel]["results"]["RMSE"].append(trap_masked_constant(rmse))
    dsb.solo[outputlabel]["results"]["NMSE"].append(trap_masked_constant(nmse))
    var_obs = numpy.ma.var(obs)
    plt.figtext(0.815,0.125,'Var (obs)')
    plt.figtext(0.915,0.125,'%.4g'%(var_obs))
    dsb.solo[outputlabel]["results"]["Var (obs)"].append(trap_masked_constant(var_obs))
    var_mod = numpy.ma.var(mod)
    plt.figtext(0.815,0.100,'Var (SOLO)')
    plt.figtext(0.915,0.100,'%.4g'%(var_mod))
    dsb.solo[outputlabel]["results"]["Var (SOLO)"].append(trap_masked_constant(var_mod))
    dsb.solo[outputlabel]["results"]["Var ratio"].append(trap_masked_constant(var_obs/var_mod))
    dsb.solo[outputlabel]["results"]["Avg (obs)"].append(trap_masked_constant(numpy.ma.average(obs)))
    dsb.solo[outputlabel]["results"]["Avg (SOLO)"].append(trap_masked_constant(numpy.ma.average(mod)))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"],pd["ts_bottom"],pd["ts_width"],pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    ts_axes[0].plot(xdt,obs,'b.',xdt,mod,'r-')
    ts_axes[0].set_xlim(xdt[0],xdt[-1])
    TextStr = targetlabel+'_obs ('+dsb.series[targetlabel]['Attr']['units']+')'
    ts_axes[0].text(0.05,0.85,TextStr,color='b',horizontalalignment='left',transform=ts_axes[0].transAxes)
    TextStr = outputlabel+'('+dsb.series[outputlabel]['Attr']['units']+')'
    ts_axes[0].text(0.85,0.85,TextStr,color='r',horizontalalignment='right',transform=ts_axes[0].transAxes)
    for ThisOne,i in zip(driverlist,range(1,pd["nDrivers"]+1)):
        this_bottom = pd["ts_bottom"] + i*pd["ts_height"]
        rect = [pd["margin_left"],this_bottom,pd["ts_width"],pd["ts_height"]]
        ts_axes.append(plt.axes(rect,sharex=ts_axes[0]))
        data,flag,attr = pfp_utils.GetSeriesasMA(dsb,ThisOne,si=si,ei=ei)
        data_notgf = numpy.ma.masked_where(flag!=0,data)
        data_gf = numpy.ma.masked_where(flag==0,data)
        ts_axes[i].plot(xdt,data_notgf,'b-')
        ts_axes[i].plot(xdt,data_gf,'r-',linewidth=2)
        plt.setp(ts_axes[i].get_xticklabels(),visible=False)
        TextStr = ThisOne+'('+dsb.series[ThisOne]['Attr']['units']+')'
        ts_axes[i].text(0.05,0.85,TextStr,color='b',horizontalalignment='left',transform=ts_axes[i].transAxes)
    # save a hard copy of the plot
    sdt = xdt[0].strftime("%Y%m%d")
    edt = xdt[-1].strftime("%Y%m%d")
    plot_path = solo_info["plot_path"]+"L5/"
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+pd["site_name"].replace(" ","")+"_SOLO_"+pd["label"]
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    if solo_info["show_plots"]:
        plt.draw()
        plt.pause(0.1)
        plt.ioff()
    else:
        plt.ion()

def gfSOLO_plotcoveragelines(dsb,solo_info):
    ldt = dsb.series["DateTime"]["Data"]
    site_name = dsb.globalattributes["site_name"]
    start_date = ldt[0].strftime("%Y-%m-%d")
    end_date = ldt[-1].strftime("%Y-%m-%d")
    output_list = dsb.solo.keys()
    series_list = [dsb.solo[item]["label_tower"] for item in dsb.solo.keys()]
    ylabel_list = [""]+series_list+[""]
    ylabel_right_list = [""]
    series_list = [dsb.solo[item]["label_tower"] for item in output_list]
    color_list = ["blue","red","green","yellow","magenta","black","cyan","brown"]
    xsize = 15.0
    ysize = max([len(output_list)*0.3,1])
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
    plt.ylim([0,len(output_list)+1])
    plt.xlim([ldt[0],ldt[-1]])
    for output,series,n in zip(output_list,series_list,range(1,len(output_list)+1)):
        data_output,f,a = pfp_utils.GetSeriesasMA(dsb,output)
        data_series,f,a = pfp_utils.GetSeriesasMA(dsb,series)
        percent = 100*numpy.ma.count(data_series)/len(data_series)
        ylabel_right_list.append("{0:.0f}%".format(percent))
        ind_series = numpy.ma.ones(len(data_series))*float(n)
        ind_series = numpy.ma.masked_where(numpy.ma.getmaskarray(data_series)==True,ind_series)
        ind_output = numpy.ma.ones(len(data_output))*float(n)
        ind_output = numpy.ma.masked_where(numpy.ma.getmaskarray(data_output)==True,ind_output)
        plt.plot(ldt,ind_series,color=color_list[numpy.mod(n,8)],linewidth=1)
        plt.plot(ldt,ind_output,color=color_list[numpy.mod(n,8)],linewidth=4)
    ylabel_posn = range(0,len(output_list)+2)
    pylab.yticks(ylabel_posn,ylabel_list)
    ylabel_right_list.append("")
    ax2 = ax1.twinx()
    pylab.yticks(ylabel_posn,ylabel_right_list)
    fig.tight_layout()
    #fig.canvas.manager.window.attributes('-topmost', 1)
    plt.draw()
    plt.ioff()

def gfSOLO_plotsummary(ds,solo_info):
    """ Plot single pages of summary results for groups of variables. """
    if "SOLO_Summary" not in ds.cf:
        msg = " SOLO summary section not in control file"
        logger.info(msg)
        return
    # get a list of variables for which SOLO data was available
    label_list = ds.solo.keys()
    if len(ds.solo[label_list[0]]["results"]["startdate"])==0:
        logger.info("gfSOLO: no summary data to plot")
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
    for xldt in ds.solo[label_list[0]]["results"]["startdate"]:
        dt_start.append(basedate+datetime.timedelta(days=xldt+1462*datemode))
    startdate = min(dt_start)
    # and then the end datetimes
    dt_end = []
    for xldt in ds.solo[label_list[0]]["results"]["enddate"]:
        dt_end.append(basedate+datetime.timedelta(days=xldt+1462*datemode))
    enddate = max(dt_end)
    # get the major tick locator and label format
    MTLoc = mdt.AutoDateLocator(minticks=3,maxticks=5)
    MTFmt = mdt.DateFormatter('%b')
    # group lists of the resuts to be plotted
    result_list = ["r","Bias","RMSE","Var ratio","m_ols","b_ols"]
    ylabel_list = ["r","Bias","RMSE","Var ratio","Slope","Offset"]
    # turn on interactive plotting
    if solo_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    # now loop over the group lists
    for nFig in ds.cf["SOLO_Summary"].keys():
        plot_title = ds.cf["SOLO_Summary"][str(nFig)]["Title"]
        var_list = ast.literal_eval(ds.cf["SOLO_Summary"][str(nFig)]["Variables"])
        # set up the subplots on the page
        fig,axs = plt.subplots(len(result_list),len(var_list),figsize=(13,8))
        fig.canvas.set_window_title("SOLO summary: "+plot_title)
        # make a title string for the plot and render it
        title_str = "SOLO: "+plot_title+"; "+site_name+" "+datetime.datetime.strftime(startdate,"%Y-%m-%d")
        title_str = title_str+" to "+datetime.datetime.strftime(enddate,"%Y-%m-%d")
        fig.suptitle(title_str, fontsize=14, fontweight='bold')
        # now loop over the variables in the group list
        for col,label in enumerate(var_list):
            # and loop over rows in plot
            for row,rlabel,ylabel in zip(range(len(result_list)),result_list,ylabel_list):
                # get the results to be plotted
                #result = numpy.ma.masked_equal(ds.solo[label]["results"][rlabel],float(c.missing_value))
                # put the data into the right order to be plotted
                dt, data = gfSOLO_plotsummary_getdata(dt_start, dt_end, ds.solo[label]["results"][rlabel])
                dt = numpy.ma.masked_equal(dt, float(c.missing_value))
                data = numpy.ma.masked_equal(data, float(c.missing_value))
                # plot the results
                axs[row,col].plot(dt,data)
                # put in the major ticks
                axs[row,col].xaxis.set_major_locator(MTLoc)
                # if this is the left-most column, add the Y axis labels
                if col==0: axs[row,col].set_ylabel(ylabel,visible=True)
                # if this is not the last row, hide the tick mark labels
                if row<len(result_list)-1: plt.setp(axs[row,col].get_xticklabels(),visible=False)
                # if this is the first row, add the column title
                if row==0: axs[row,col].set_title(label)
                # if this is the last row, add the major tick mark and axis labels
                if row==len(result_list)-1:
                    axs[row,col].xaxis.set_major_formatter(MTFmt)
                    axs[row,col].set_xlabel('Month',visible=True)
        # make the hard-copy file name and save the plot as a PNG file
        sdt = startdate.strftime("%Y%m%d")
        edt = enddate.strftime("%Y%m%d")
        plot_path = solo_info["plot_path"]+"L5/"
        if not os.path.exists(plot_path): os.makedirs(plot_path)
        figname = plot_path+site_name.replace(" ","")+"_SOLO_FitStatistics_"
        figname = figname+"_"+sdt+"_"+edt+".png"
        fig.savefig(figname,format="png")
        if solo_info["show_plots"]:
            plt.draw()
            plt.ioff()
        else:
            plt.ion()

def gfSOLO_plotsummary_getdata(dt_start,dt_end,result):
    dt = []
    data = []
    for s,e,r in zip(dt_start,dt_end,result):
        dt.append(s)
        data.append(r)
        dt.append(e)
        data.append(r)
    return dt,data

def gfSOLO_progress(solo_gui,text):
    """
        Update progress message in SOLO GUI
        """
    solo_gui.progress.destroy()
    solo_gui.progress = Tkinter.Label(solo_gui, text=text)
    solo_gui.progress.grid(row=solo_gui.progress_row,column=0,columnspan=6,sticky="W")
    solo_gui.update()

def gfSOLO_quit(ds,solo_gui):
    # destroy the GUI
    solo_gui.destroy()
    # put the return code in ds.returncodes
    ds.returncodes["solo"] = "quit"

def gfSOLO_resetnodesEntry(solo_gui):
    solo_gui.nodesEntry.delete(0,Tkinter.END)
    solo_gui.nodesEntry.insert(0,"Auto")

def gfSOLO_run_gui(dsa,dsb,solo_gui,solo_info):
    # populate the solo_info dictionary with things that will be useful
    solo_info["peropt"] = solo_gui.peropt.get()
    solo_info["overwrite"] = True
    if solo_gui.owopt.get()==0: solo_info["overwrite"] = False
    solo_info["show_plots"] = True
    if solo_gui.pltopt.get()==0: solo_info["show_plots"] = False
    solo_info["auto_complete"] = True
    if solo_gui.autocompleteopt.get()==0: solo_info["auto_complete"] = False
    solo_info["min_percent"] = int(solo_gui.minptsEntry.get())
    solo_info["nodes"] = str(solo_gui.nodesEntry.get())
    solo_info["training"] = str(solo_gui.trainingEntry.get())
    solo_info["factor"] = str(solo_gui.factorEntry.get())
    solo_info["learningrate"] = str(solo_gui.learningrateEntry.get())
    solo_info["iterations"] = str(solo_gui.iterationsEntry.get())
    solo_info["site_name"] = dsb.globalattributes["site_name"]
    solo_info["time_step"] = int(dsb.globalattributes["time_step"])
    solo_info["nperhr"] = int(float(60)/solo_info["time_step"]+0.5)
    solo_info["nperday"] = int(float(24)*solo_info["nperhr"]+0.5)
    solo_info["maxlags"] = int(float(12)*solo_info["nperhr"]+0.5)
    solo_info["series"] = dsb.solo.keys()
    solo_info["tower"] = {}
    solo_info["alternate"] = {}
    series_list = [dsb.solo[item]["label_tower"] for item in dsb.solo.keys()]
    logger.info(" Gap filling "+str(series_list)+" using SOLO")
    if solo_gui.peropt.get()==1:
        gfSOLO_progress(solo_gui,"Starting manual run ...")
        # get the start and end datetimes entered in the SOLO GUI
        if len(solo_gui.startEntry.get())!=0: solo_info["startdate"] = solo_gui.startEntry.get()
        if len(solo_gui.endEntry.get())!=0: solo_info["enddate"] = solo_gui.endEntry.get()
        gfSOLO_main(dsa,dsb,solo_info)
        gfSOLO_plotcoveragelines(dsb,solo_info)
        gfSOLO_progress(solo_gui,"Finished manual run ...")
        logger.info(" GapFillUsingSOLO: Finished manual run ...")
    elif solo_gui.peropt.get()==2:
        gfSOLO_progress(solo_gui,"Starting auto (monthly) run ...")
        # get the start datetime entered in the SOLO GUI
        if len(solo_gui.startEntry.get())!=0: solo_info["startdate"] = solo_gui.startEntry.get()
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<file_enddate:
            gfSOLO_main(dsa,dsb,solo_info)
            gfSOLO_plotcoveragelines(dsb,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(dsa,dsb,solo_info)
        # write Excel spreadsheet with fit statistics
        pfp_io.xl_write_SOLOStats(dsb)
        # plot the summary statistics
        gfSOLO_plotsummary(dsb,solo_info)
        gfSOLO_progress(solo_gui,"Finished auto (monthly) run ...")
        logger.info(" GapFillUsingSOLO: Finished auto (monthly) run ...")
    elif solo_gui.peropt.get()==3:
        gfSOLO_progress(solo_gui,"Starting auto (days) run ...")
        # get the start datetime entered in the SOLO GUI
        if len(solo_gui.startEntry.get())!=0: solo_info["startdate"] = solo_gui.startEntry.get()  # if you read the GUIs startdate
        if len(solo_gui.endEntry.get())!=0: solo_info["enddate"] = solo_gui.endEntry.get()        # you need to include end date too
        solo_info["gui_startdate"] = solo_info["startdate"]
        solo_info["gui_enddate"] = solo_info["enddate"]
        startdate = dateutil.parser.parse(solo_info["startdate"])
        gui_enddate = dateutil.parser.parse(solo_info["gui_enddate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        nDays = int(solo_gui.daysEntry.get())
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate,enddate,gui_enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        solo_info["startdate"] = datetime.datetime.strftime(startdate,"%Y-%m-%d %H:%M")
        stopdate = min([file_enddate,gui_enddate])
        while startdate<stopdate: #file_enddate:
            gfSOLO_main(dsa,dsb,solo_info)
            gfSOLO_plotcoveragelines(dsb,solo_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            solo_info["enddate"] = run_enddate.strftime("%Y-%m-%d %H:%M")
        # now fill any remaining gaps
        gfSOLO_autocomplete(dsa,dsb,solo_info)
        # write Excel spreadsheet with fit statistics
        pfp_io.xl_write_SOLOStats(dsb)
        # plot the summary statistics
        gfSOLO_plotsummary(dsb,solo_info)
        gfSOLO_progress(solo_gui,"Finished auto (days) run ...")
        logger.info(" GapFillUsingSOLO: Finished auto (days) run ...")
    elif solo_gui.peropt.get()==4:
        pass

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
    solo_info["tower"] = {}
    solo_info["alternate"] = {}
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
    pfp_io.xl_write_SOLOStats(dsb)
    # plot the summary statistics
    gfSOLO_plotsummary(dsb,solo_info)

def gfSOLO_runseqsolo(dsa,dsb,driverlist,targetlabel,outputlabel,nRecs,si=0,ei=-1):
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
        driver,flag,attr = pfp_utils.GetSeries(dsb,TheseOnes,si=si,ei=ei)
        seqsoloinputdata[:,i] = driver[:]
        i = i + 1
    ## a clean copy of the target is pulled from the unmodified ds each time
    #target,flag,attr = pfp_utils.GetSeries(dsa,targetlabel,si=si,ei=ei)
    # get the target data
    target,flag,attr = pfp_utils.GetSeries(dsb,targetlabel,si=si,ei=ei)
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
            dsb.series[outputlabel]['Data'][si:][goodindex] = seqdata[:,1]
            dsb.series[outputlabel]['Flag'][si:][goodindex] = numpy.int32(30)
        else:
            dsb.series[outputlabel]['Data'][si:ei+1][goodindex] = seqdata[:,1]
            dsb.series[outputlabel]['Flag'][si:ei+1][goodindex] = numpy.int32(30)
        # set the attributes
        if targetlabel in dsa.series.keys():
            for attr in dsa.series[targetlabel]["Attr"].keys():
                dsb.series[outputlabel]["Attr"][attr] = dsa.series[targetlabel]["Attr"][attr]
        dsb.series[outputlabel]["Attr"]["long_name"] = dsb.series[outputlabel]["Attr"]["long_name"]+", modeled by SOLO"
        return 1
    else:
        logger.error(' gfSOLO_runseqsolo: SEQSOLO did not run correctly, check the SOLO GUI and the log files')
        return 0

def gfSOLO_runsofm(dsa,dsb,driverlist,targetlabel,nRecs,si=0,ei=-1):
    '''
    Run sofm, the pre-processor for SOLO.
    '''
    # get the number of drivers
    ndrivers = len(driverlist)
    # add an extra column for the target data
    sofminputdata = numpy.zeros((nRecs,ndrivers))
    # now fill the driver data array
    i = 0
    badlines = []
    baddates = []
    badvalues = []
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(dsb,TheseOnes,si=si,ei=ei)
        index = numpy.where(abs(driver-float(c.missing_value))<c.eps)[0]
        if len(index)!=0:
            logger.error(' GapFillUsingSOLO: c.missing_value found in driver '+TheseOnes+' at lines '+str(index))
            badlines = badlines+index.tolist()
            for n in index:
                baddates.append(dsb.series["DateTime"]["Data"][n])
                badvalues.append(dsb.series[TheseOnes]["Data"][n])
            logger.error(' GapFillUsingSOLO: driver values: '+str(badvalues))
            logger.error(' GapFillUsingSOLO: datetimes: '+str(baddates))
        sofminputdata[:,i] = driver[:]
        i = i + 1
    if len(badlines)!=0:
        nBad = len(badlines)
        goodlines = [x for x in range(0,nRecs) if x not in badlines]
        sofminputdata = sofminputdata[goodlines,:]
        logger.info(' GapFillUsingSOLO: removed '+str(nBad)+' lines from sofm input file')
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
        logger.error(' gfSOLO_runsofm: SOFM did not run correctly, check the SOLO GUI and the log files')
        return 0

def gfSOLO_runsolo(dsa,dsb,driverlist,targetlabel,nRecs,si=0,ei=-1):
    '''
    Run SOLO.
    '''
    ndrivers = len(driverlist)
    # add an extra column for the target data
    soloinputdata = numpy.zeros((nRecs,ndrivers+1))
    # now fill the driver data array, drivers come from the modified ds
    i = 0
    for TheseOnes in driverlist:
        driver,flag,attr = pfp_utils.GetSeries(dsb,TheseOnes,si=si,ei=ei)
        soloinputdata[:,i] = driver[:]
        i = i + 1
    ## a clean copy of the target is pulled from the unmodified ds each time
    #target,flag,attr = pfp_utils.GetSeries(dsa,targetlabel,si=si,ei=ei)
    # get the target data
    target,flag,attr = pfp_utils.GetSeries(dsb,targetlabel,si=si,ei=ei)
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
        logger.error(' gfSOLO_runsolo: SOLO did not run correctly, check the SOLO GUI and the log files')
        return 0

def gfSOLO_setnodesEntry(solo_gui,drivers):
    nodesAuto = False
    if str(solo_gui.nodesEntry.get()).lower()=="auto":
        nodesAuto = True
        solo_gui.nodesEntry.delete(0,Tkinter.END)
        solo_gui.nodesEntry.insert(0,str(len(drivers)+1))
    return nodesAuto

def gfSOLO_writeinffiles(solo_info):
    # sofm inf file
    f = open('solo/inf/sofm.inf','w')
    f.write(str(solo_info["nodes_target"])+'\n')
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
    f.write(str(solo_info["nodes_target"])+'\n')
    f.write(str(solo_info["factor"])+'\n')
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
    f.write(str(solo_info["nodes_target"])+'\n')
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
