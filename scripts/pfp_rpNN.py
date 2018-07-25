import ast
import constants as c
import csv
import dateutil
import datetime
import logging
import numpy
import matplotlib.pyplot as plt
import os
import platform
import subprocess
import Tkinter
import pfp_io
import pfp_utils

# lets see if ffnet is installed
try:
    import ffnet
except ImportError:
    #log.error("ERUsingFFNET: Unable to import module ffnet")
    pass

logger = logging.getLogger("pfp_log")

def rpFFNET_gui(cf,ds,FFNET_info):
    ldt = ds.series["DateTime"]["Data"]
    # set up the GUI
    FFNET_gui = Tkinter.Toplevel()
    FFNET_gui.wm_title("FFNET GUI (ER)")
    FFNET_gui.grid()
    # top row
    nrow = 0
    FFNET_gui.nodesLabel = Tkinter.Label(FFNET_gui,text="Hidden Nodes")
    FFNET_gui.nodesLabel.grid(row=nrow,column=0,columnspan=1,sticky="E")
    FFNET_gui.nodesEntry = Tkinter.Entry(FFNET_gui,width=6)
    FFNET_gui.nodesEntry.grid(row=nrow,column=1,columnspan=1,sticky="W")
    FFNET_gui.nodesEntry.insert(0,"6,4")
    FFNET_gui.trainingLabel = Tkinter.Label(FFNET_gui,text="Training")
    FFNET_gui.trainingLabel.grid(row=nrow,column=2,columnspan=1,sticky="E")
    FFNET_gui.trainingEntry = Tkinter.Entry(FFNET_gui,width=6)
    FFNET_gui.trainingEntry.grid(row=nrow,column=3,columnspan=1,sticky="W")
    FFNET_gui.trainingEntry.insert(0,"500")
    # second row
    nrow = nrow + 1
    FFNET_gui.trainTypeVar = Tkinter.StringVar()
    FFNET_gui.trainTypeVar.set("Rprop")
    choices = ["BFGS","CG","Genetic","Back","Rprop","TNC"]
    FFNET_gui.trainTypeLabel = Tkinter.Label(FFNET_gui,text="Training type")
    FFNET_gui.trainTypeLabel.grid(row=nrow,column=0,columnspan=1,sticky="E")
    FFNET_gui.trainType = Tkinter.OptionMenu(FFNET_gui,FFNET_gui.trainTypeVar,*choices)
    FFNET_gui.trainType.grid(row=nrow,column=1,columnspan=1,sticky="E")
    FFNET_gui.connecVar = Tkinter.IntVar()
    FFNET_gui.connecVar.set(2)
    FFNET_gui.connecStd = Tkinter.Radiobutton(FFNET_gui,text="Standard",variable=FFNET_gui.connecVar,value=1)
    FFNET_gui.connecStd.grid(row=nrow,column=2,columnspan=1,sticky="W")
    FFNET_gui.connecFC = Tkinter.Radiobutton(FFNET_gui,text="Fully connected",variable=FFNET_gui.connecVar,value=2)
    FFNET_gui.connecFC.grid(row=nrow,column=3,columnspan=1,sticky="W")
    # third row
    nrow = nrow + 1
    FFNET_gui.filestartLabel = Tkinter.Label(FFNET_gui,text="File start date")
    FFNET_gui.filestartLabel.grid(row=nrow,column=0,columnspan=3)
    FFNET_gui.fileendLabel = Tkinter.Label(FFNET_gui,text="File end date")
    FFNET_gui.fileendLabel.grid(row=nrow,column=3,columnspan=3)
    # fourth row
    nrow = nrow + 1
    FFNET_gui.filestartValue = Tkinter.Label(FFNET_gui,text=str(ldt[0]))
    FFNET_gui.filestartValue.grid(row=nrow,column=0,columnspan=3)
    FFNET_gui.fileendValue = Tkinter.Label(FFNET_gui,text=str(ldt[-1]))
    FFNET_gui.fileendValue.grid(row=nrow,column=3,columnspan=3)
    # fifth row
    nrow = nrow + 1
    FFNET_gui.startLabel = Tkinter.Label(FFNET_gui, text="Start date (YYYY-MM-DD)")
    FFNET_gui.startLabel.grid(row=nrow,column=0,columnspan=3)
    FFNET_gui.startEntry = Tkinter.Entry(FFNET_gui)
    FFNET_gui.startEntry.grid(row=nrow,column=3,columnspan=3)
    # sixth row
    nrow = nrow + 1
    FFNET_gui.endLabel = Tkinter.Label(FFNET_gui, text="End date   (YYYY-MM-DD)")
    FFNET_gui.endLabel.grid(row=nrow,column=0,columnspan=3)
    FFNET_gui.endEntry = Tkinter.Entry(FFNET_gui)
    FFNET_gui.endEntry.grid(row=nrow,column=3,columnspan=3)
    # seventh row
    nrow = nrow + 1
    FFNET_gui.peropt = Tkinter.IntVar()
    FFNET_gui.peropt.set(1)
    FFNET_gui.manualperiod = Tkinter.Radiobutton(FFNET_gui,text="Manual",variable=FFNET_gui.peropt,value=1)
    FFNET_gui.manualperiod.grid(row=nrow,column=0,columnspan=1,sticky="W")
    FFNET_gui.yearsLabel = Tkinter.Radiobutton(FFNET_gui,text="Years",variable=FFNET_gui.peropt,value=4)
    FFNET_gui.yearsLabel.grid(row=nrow,column=1,columnspan=1,sticky="W")
    FFNET_gui.yearsEntry = Tkinter.Entry(FFNET_gui,width=3)
    FFNET_gui.yearsEntry.grid(row=nrow,column=2,columnspan=1,sticky="W")
    FFNET_gui.yearsEntry.insert(0,"1")
    FFNET_gui.minptsLabel = Tkinter.Label(FFNET_gui,text="Min. pts (%)")
    FFNET_gui.minptsLabel.grid(row=nrow,column=3,columnspan=1,sticky="E")
    FFNET_gui.minptsEntry = Tkinter.Entry(FFNET_gui,width=5)
    FFNET_gui.minptsEntry.grid(row=nrow,column=4,columnspan=1,sticky="W")
    FFNET_gui.minptsEntry.insert(0,"5")
    # eigth row
    nrow = nrow + 1
    FFNET_gui.automonthly = Tkinter.Radiobutton(FFNET_gui,text="Monthly",variable=FFNET_gui.peropt,value=2)
    FFNET_gui.automonthly.grid(row=nrow,column=0,columnspan=1,sticky="W")
    FFNET_gui.daysLabel = Tkinter.Radiobutton(FFNET_gui,text="Days",variable=FFNET_gui.peropt,value=3)
    FFNET_gui.daysLabel.grid(row=nrow,column=1,columnspan=1,sticky="W")
    FFNET_gui.daysEntry = Tkinter.Entry(FFNET_gui,width=3)
    FFNET_gui.daysEntry.grid(row=nrow,column=2,columnspan=1,sticky="W")
    FFNET_gui.daysEntry.insert(0,"90")
    FFNET_gui.autocompleteopt = Tkinter.IntVar()
    FFNET_gui.autocompleteopt.set(1)
    FFNET_gui.autocomplete = Tkinter.Checkbutton(FFNET_gui, text="Auto complete", variable=FFNET_gui.autocompleteopt)
    FFNET_gui.autocomplete.grid(row=nrow,column=3,columnspan=3,sticky="w")
    # ninth row
    nrow = nrow + 1
    FFNET_gui.pltopt = Tkinter.IntVar()
    FFNET_gui.pltopt.set(1)
    FFNET_gui.showplots = Tkinter.Checkbutton(FFNET_gui, text="Show plots", variable=FFNET_gui.pltopt)
    FFNET_gui.showplots.grid(row=nrow,column=0,columnspan=3,sticky="w")
    FFNET_gui.owopt = Tkinter.IntVar()
    FFNET_gui.owopt.set(0)
    FFNET_gui.overwrite = Tkinter.Checkbutton(FFNET_gui, text="Overwrite", variable=FFNET_gui.owopt)
    FFNET_gui.overwrite.grid(row=nrow,column=3,columnspan=3,sticky="w")
    # tenth row
    nrow = nrow + 1
    FFNET_gui.doneButton = Tkinter.Button (FFNET_gui, text="Done",command=lambda:rpFFNET_done(ds,FFNET_gui,FFNET_info))
    FFNET_gui.doneButton.grid(row=nrow,column=0,columnspan=2)
    FFNET_gui.runButton = Tkinter.Button (FFNET_gui, text="Run",command=lambda:rpFFNET_run_gui(ds,FFNET_gui,FFNET_info))
    FFNET_gui.runButton.grid(row=nrow,column=2,columnspan=2)
    FFNET_gui.quitButton = Tkinter.Button (FFNET_gui, text="Quit",command=lambda:rpFFNET_quit(ds,FFNET_gui))
    FFNET_gui.quitButton.grid(row=nrow,column=4,columnspan=2)
    # eleventh row
    nrow = nrow + 1
    FFNET_gui.progress_row = nrow
    FFNET_gui.progress = Tkinter.Label(FFNET_gui, text='Waiting for input ...')
    FFNET_gui.progress.grid(row=nrow,column=0,columnspan=6,sticky="W")

    FFNET_gui.wait_window(FFNET_gui)

def rpSOLO_gui(cf,ds,solo_info):
    ldt = ds.series["DateTime"]["Data"]
    # use specific parameters are "Nodes", "Learning"
    # set up the GUI
    solo_gui = Tkinter.Toplevel()
    solo_gui.wm_title("SOLO GUI (ER)")
    solo_gui.grid()
    # top row
    nrow = 0
    solo_gui.nodesLabel = Tkinter.Label(solo_gui,text="Nodes")
    solo_gui.nodesLabel.grid(row=nrow,column=0,columnspan=1,sticky="E")
    solo_gui.nodesEntry = Tkinter.Entry(solo_gui,width=6)
    solo_gui.nodesEntry.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.nodesEntry.insert(0,"1")
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
    solo_gui.peropt.set(1)
    solo_gui.manualperiod = Tkinter.Radiobutton(solo_gui,text="Manual",variable=solo_gui.peropt,value=1)
    solo_gui.manualperiod.grid(row=nrow,column=0,columnspan=1,sticky="W")
    solo_gui.yearsLabel = Tkinter.Radiobutton(solo_gui,text="Years",variable=solo_gui.peropt,value=4)
    solo_gui.yearsLabel.grid(row=nrow,column=1,columnspan=1,sticky="W")
    solo_gui.yearsEntry = Tkinter.Entry(solo_gui,width=3)
    solo_gui.yearsEntry.grid(row=nrow,column=2,columnspan=1,sticky="W")
    solo_gui.yearsEntry.insert(0,"1")
    solo_gui.minptsLabel = Tkinter.Label(solo_gui,text="Min. pts (%)")
    solo_gui.minptsLabel.grid(row=nrow,column=3,columnspan=1,sticky="E")
    solo_gui.minptsEntry = Tkinter.Entry(solo_gui,width=5)
    solo_gui.minptsEntry.grid(row=nrow,column=4,columnspan=1,sticky="W")
    solo_gui.minptsEntry.insert(0,"5")
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
    solo_gui.doneButton = Tkinter.Button (solo_gui, text="Done",command=lambda:rpSOLO_done(ds,solo_gui,solo_info))
    solo_gui.doneButton.grid(row=nrow,column=0,columnspan=2)
    solo_gui.runButton = Tkinter.Button (solo_gui, text="Run",command=lambda:rpSOLO_run_gui(ds,solo_gui,solo_info))
    solo_gui.runButton.grid(row=nrow,column=2,columnspan=2)
    solo_gui.quitButton = Tkinter.Button (solo_gui, text="Quit",command=lambda:rpSOLO_quit(ds,solo_gui))
    solo_gui.quitButton.grid(row=nrow,column=4,columnspan=2)
    # eleventh row
    nrow = nrow + 1
    solo_gui.progress_row = nrow
    solo_gui.progress = Tkinter.Label(solo_gui, text='Waiting for input ...')
    solo_gui.progress.grid(row=nrow,column=0,columnspan=6,sticky="W")

    solo_gui.wait_window(solo_gui)

def rpSOLO_quit(ds,solo_gui):
    # destroy the GUI
    solo_gui.destroy()
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

def rpFFNET_createdict(cf,ds,series):
    """ Creates a dictionary in ds to hold information about the FFNET data used
        to gap fill the tower data."""
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("ERUsingFFNET: Series "+series+" not found in control file, skipping ...")
        return
    # check that none of the drivers have missing data
    driver_list = ast.literal_eval(cf[section][series]["ERUsingFFNET"]["drivers"])
    target = cf[section][series]["ERUsingFFNET"]["target"]
    for label in driver_list:
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,label)
        if numpy.ma.count_masked(data)!=0:
            logger.error("ERUsingFFNET: driver "+label+" contains missing data, skipping target "+target)
            return
    # create the dictionary keys for this series
    ffnet_info = {}
    # site name
    ffnet_info["site_name"] = ds.globalattributes["site_name"]
    # source series for ER
    opt = pfp_utils.get_keyvaluefromcf(cf, [section,series,"ERUsingFFNET"], "source", default="Fc")
    ffnet_info["source"] = opt
    # target series name
    ffnet_info["target"] = cf[section][series]["ERUsingFFNET"]["target"]
    # list of drivers
    ffnet_info["drivers"] = ast.literal_eval(cf[section][series]["ERUsingFFNET"]["drivers"])
    # name of ffnet output series in ds
    ffnet_info["output"] = cf[section][series]["ERUsingFFNET"]["output"]
    # results of best fit for plotting later on
    ffnet_info["results"] = {"startdate":[],"enddate":[],"No. points":[],"r":[],
                             "Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                             "Avg (obs)":[],"Avg (FFNET)":[],
                             "Var (obs)":[],"Var (FFNET)":[],"Var ratio":[],
                             "m_ols":[],"b_ols":[]}
    # create an empty series in ds if the SOLO output series doesn't exist yet
    if ffnet_info["output"] not in ds.series.keys():
        data,flag,attr = pfp_utils.MakeEmptySeries(ds,ffnet_info["output"])
        pfp_utils.CreateSeries(ds,ffnet_info["output"],data,flag,attr)
    # create the merge directory in the data structure
    if "merge" not in dir(ds): ds.merge = {}
    if "standard" not in ds.merge.keys(): ds.merge["standard"] = {}
    # create the dictionary keys for this series
    ds.merge["standard"][series] = {}
    # output series name
    ds.merge["standard"][series]["output"] = series
    # source
    ds.merge["standard"][series]["source"] = ast.literal_eval(cf[section][series]["MergeSeries"]["Source"])
    # create an empty series in ds if the output series doesn't exist yet
    if ds.merge["standard"][series]["output"] not in ds.series.keys():
        data,flag,attr = pfp_utils.MakeEmptySeries(ds,ds.merge["standard"][series]["output"])
        pfp_utils.CreateSeries(ds,ds.merge["standard"][series]["output"],data,flag,attr)
    return ffnet_info

def rpFFNET_done(ds,FFNET_gui,rpFFNET_info):
    # destroy the FFNET GUI
    FFNET_gui.destroy()

def rpFFNET_initplot(**kwargs):
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

def rpFFNET_main(ds, rpFFNET_info,FFNET_gui=None):
    """
    This is the main routine for running FFNET, an artifical neural network for estimating ER.
    """
    startdate = rpFFNET_info["startdate"]
    enddate = rpFFNET_info["enddate"]
    logger.info(" Estimating ER using FFNET: "+startdate+" to "+enddate)
    # read the control file again, this allows the contents of the control file to
    # be changed with the FFNET GUI still displayed
    cfname = ds.globalattributes["controlfile_name"]
    cf = pfp_io.get_controlfilecontents(cfname,mode="quiet")
    ffnet_series = rpFFNET_info["er"].keys()
    for series in ffnet_series:
        section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
        if len(section)==0: continue
        if series not in ds.series.keys(): continue
        rpFFNET_info["er"][series]["target"] = cf[section][series]["ERUsingFFNET"]["target"]
        rpFFNET_info["er"][series]["drivers"] = ast.literal_eval(cf[section][series]["ERUsingFFNET"]["drivers"])
        rpFFNET_info["er"][series]["output"] = cf[section][series]["ERUsingFFNET"]["output"]
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
        logger.error(" ERUsingFFNET: end datetime index ("+str(ei)+") smaller that start ("+str(si)+")")
        return
    if si==0 and ei==-1:
        logger.error(" ERUsingFFNET: no start and end datetime specified, using all data")
        nRecs = int(ds.globalattributes["nc_nrecs"])
    else:
        nRecs = ei - si + 1
    # get the minimum number of points from the minimum percentage
    rpFFNET_info["min_points"] = int((ei-si)*rpFFNET_info["min_percent"]/100)
    # get the figure number
    if len(plt.get_fignums())==0:
        fig_num = 0
    else:
        #fig_nums = plt.get_fignums()
        #fig_num = fig_nums[-1]
        fig_num = plt.get_fignums()[-1]
    # loop over the series to be gap filled using ffnet
    for series in ffnet_series:
        rpFFNET_info["er"][series]["results"]["startdate"].append(xldt[si])
        rpFFNET_info["er"][series]["results"]["enddate"].append(xldt[ei])
        target = rpFFNET_info["er"][series]["target"]
        d,f,a = pfp_utils.GetSeriesasMA(ds,target,si=si,ei=ei)
        if numpy.ma.count(d)<rpFFNET_info["min_points"]:
            logger.error("rpFFNET: Less than "+str(rpFFNET_info["min_points"])+" points available for series "+series+" ...")
            rpFFNET_info["er"][series]["results"]["No. points"].append(float(0))
            results_list = rpFFNET_info["er"][series]["results"].keys()
            for item in ["startdate","enddate","No. points"]:
                if item in results_list: results_list.remove(item)
            for item in results_list:
                rpFFNET_info["er"][series]["results"][item].append(float(c.missing_value))
            continue
        drivers = rpFFNET_info["er"][series]["drivers"]
        ndrivers = len(drivers)
        output = rpFFNET_info["er"][series]["output"]
        # prepare the input and target data for training
        ER,f,a = pfp_utils.GetSeriesasMA(ds,target,si=si,ei=ei)
        mask = numpy.ma.getmask(ER)
        for val in drivers:
            d,f,a = pfp_utils.GetSeriesasMA(ds,val,si=si,ei=ei)
            mask = numpy.ma.mask_or(mask,d.mask)
        ER.mask = mask
        nRecs = numpy.ma.count(ER)
        data_nm = numpy.empty((nRecs,len(drivers)+1))
        for idx,val in enumerate(drivers):
            d,f,a = pfp_utils.GetSeriesasMA(ds,val,si=si,ei=ei)
            d.mask = mask
            data_nm[:,idx] = numpy.ma.compressed(d)
        data_nm[:,idx+1] = numpy.ma.compressed(ER)
        input_train = data_nm[:,0:idx+1]
        target_train = data_nm[:,idx+1]
        # design the network
        hidden_layers = rpFFNET_info["hidden"].split(",")
        if len(hidden_layers)==1:
            arch = (ndrivers,int(hidden_layers[0]),1)
        elif len(hidden_layers)==2:
            arch = (ndrivers,int(hidden_layers[0]),int(hidden_layers[1]),1)
        else:
            logger.error("ERUsingFFNET: more than 2 hidden layers specified, using 1 ("+str(ndrivers)+")")
            arch = (ndrivers,ndrivers,1)
        if rpFFNET_info["connection"]=="standard":
            conec = ffnet.mlgraph(arch,biases=True)
        elif rpFFNET_info["connection"]=="full":
            conec = ffnet.tmlgraph(arch,biases=True)
        else:
            raise Exception("rpFFNET: unrecognised FFNET connection option")
        net = ffnet.ffnet(conec)
        # train the network
        if rpFFNET_info["training_type"].lower()=="tnc":
            net.train_tnc(input_train,target_train)
        elif rpFFNET_info["training_type"].lower()=="bfgs":
            net.train_bfgs(input_train,target_train)
        elif rpFFNET_info["training_type"].lower()=="cg":
            net.train_cg(input_train,target_train)
        elif rpFFNET_info["training_type"].lower()=="genetic":
            net.train_genetic(input_train,target_train)
        elif rpFFNET_info["training_type"].lower()=="back":
            net.train_momentum(input_train,target_train)
        elif rpFFNET_info["training_type"].lower()=="rprop":
            try:
                net.train_rprop(input_train,target_train)
            except:
                logger.warning("rpFFNET: Rprop training failed, using TNC ...")
                net.train_tnc(input_train,target_train)
        else:
            raise Exception("rpFFNET: unrecognised FFNET training option")
        #output,regress=net.test(input_train,target_train)
        # get the predictions
        input_predict = numpy.empty((len(ER),len(drivers)))
        for idx,val in enumerate(drivers):
            d,f,a = pfp_utils.GetSeries(ds,val,si=si,ei=ei)
            input_predict[:,idx] = d[:]
        output_predict = net.call(input_predict)
        if ei==-1:
            ds.series[output]['Data'][si:] = output_predict[:,0]
            ds.series[output]['Flag'][si:] = numpy.int32(30)
        else:
            ds.series[output]['Data'][si:ei+1] = output_predict[:,0]
            ds.series[output]['Flag'][si:ei+1] = numpy.int32(30)
        # set the attributes
        ds.series[output]["Attr"]["units"] = ds.series[target]["Attr"]["units"]
        if "modelled by FFNET" not in ds.series[output]["Attr"]["long_name"]:
            ds.series[output]["Attr"]["long_name"] = "Ecosystem respiration modelled by FFNET (ANN)"
            ds.series[output]["Attr"]["comment1"] = "Target was "+str(target)
            ds.series[output]["Attr"]["comment2"] = "Drivers were "+str(drivers)
        # plot the results
        fig_num = fig_num + 1
        title = site_name+" : "+series+" estimated using FFNET"
        pd = rpFFNET_initplot(site_name=site_name,label=target,fig_num=fig_num,title=title,
                             nDrivers=len(drivers),startdate=startdate,enddate=enddate)
        rpFFNET_plot(pd,ds,series,drivers,target,output,rpFFNET_info,si=si,ei=ei)
    if 'ERUsingFFNET' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+', ERUsingFFNET'

def rpFFNET_plot(pd,ds,series,driverlist,targetlabel,outputlabel,rpFFNET_info,si=0,ei=-1):
    """ Plot the results of the FFNET run. """
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
    if rpFFNET_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"],figsize=(13,8))
    fig.clf()
    fig.canvas.set_window_title(targetlabel+" (FFNET): "+pd["startdate"]+" to "+pd["enddate"])
    plt.figtext(0.5,0.95,pd["title"],ha='center',size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    dstats = rp_getdiurnalstats(dt,obs,rpFFNET_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'b-',label="Obs")
    # get the diurnal stats of all SOLO predictions
    dstats = rp_getdiurnalstats(dt,mod,rpFFNET_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'r-',label="FFNET(all)")
    mod_mor = numpy.ma.masked_where(numpy.ma.getmaskarray(obs)==True,mod,copy=True)
    dstats = rp_getdiurnalstats(dt,mod_mor,rpFFNET_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'g-',label="FFNET(obs)")
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
    ax2.set_xlabel(targetlabel+'_FFNET')
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
    rpFFNET_info["er"][series]["results"]["Bias"].append(bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    plt.figtext(0.65,0.225,'No. points')
    plt.figtext(0.75,0.225,str(numpoints))
    rpFFNET_info["er"][series]["results"]["No. points"].append(numpoints)
    plt.figtext(0.65,0.200,'Hidden nodes')
    plt.figtext(0.75,0.200,str(rpFFNET_info["hidden"]))
    plt.figtext(0.65,0.175,'Training')
    plt.figtext(0.75,0.175,str(rpFFNET_info["training"]))
    plt.figtext(0.65,0.150,'Training type')
    plt.figtext(0.75,0.150,str(rpFFNET_info["training_type"]))
    plt.figtext(0.65,0.125,'Connection')
    connection = "Std"
    if rpFFNET_info["connection"]=="full": connection = "Full"
    plt.figtext(0.75,0.125,connection)
    plt.figtext(0.815,0.225,'No. filled')
    plt.figtext(0.915,0.225,str(numfilled))
    plt.figtext(0.815,0.200,'Slope')
    plt.figtext(0.915,0.200,str(pfp_utils.round2sig(coefs[0],sig=4)))
    rpFFNET_info["er"][series]["results"]["m_ols"].append(coefs[0])
    plt.figtext(0.815,0.175,'Offset')
    plt.figtext(0.915,0.175,str(pfp_utils.round2sig(coefs[1],sig=4)))
    rpFFNET_info["er"][series]["results"]["b_ols"].append(coefs[1])
    plt.figtext(0.815,0.150,'r')
    plt.figtext(0.915,0.150,str(pfp_utils.round2sig(r[0][1],sig=4)))
    rpFFNET_info["er"][series]["results"]["r"].append(r[0][1])
    plt.figtext(0.815,0.125,'RMSE')
    plt.figtext(0.915,0.125,str(pfp_utils.round2sig(rmse,sig=4)))
    rpFFNET_info["er"][series]["results"]["RMSE"].append(rmse)
    var_obs = numpy.ma.var(obs)
    rpFFNET_info["er"][series]["results"]["Var (obs)"].append(var_obs)
    var_mod = numpy.ma.var(mod)
    rpFFNET_info["er"][series]["results"]["Var (FFNET)"].append(var_mod)
    rpFFNET_info["er"][series]["results"]["Var ratio"].append(var_obs/var_mod)
    rpFFNET_info["er"][series]["results"]["Avg (obs)"].append(numpy.ma.average(obs))
    rpFFNET_info["er"][series]["results"]["Avg (FFNET)"].append(numpy.ma.average(mod))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"],pd["ts_bottom"],pd["ts_width"],pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    #ts_axes[0].plot(xdt,obs,'b.',xdt,mod,'r-')
    ts_axes[0].scatter(xdt,obs,c=Hdh)
    ts_axes[0].plot(xdt,mod,'r-')
    ts_axes[0].set_xlim(xdt[0],xdt[-1])
    plt.axhline(0)
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
    plot_path = rpFFNET_info["plot_path"]+"L6/"
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+pd["site_name"].replace(" ","")+"_FFNET_"+pd["label"]
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    if rpFFNET_info["show_plots"]:
        plt.draw()
        plt.ioff()
    else:
        plt.ion()

def rpFFNET_progress(FFNET_gui,text):
    """
        Update progress message in FFNET GUI
        """
    FFNET_gui.progress.destroy()
    FFNET_gui.progress = Tkinter.Label(FFNET_gui, text=text)
    FFNET_gui.progress.grid(row=FFNET_gui.progress_row,column=0,columnspan=4,sticky="W")
    FFNET_gui.update()

def rpFFNET_quit(ds,FFNET_gui):
    # destroy the GUI
    FFNET_gui.destroy()
    # put the return code in ds.returncodes
    ds.returncodes["ffnet"] = "quit"

def rpFFNET_run_gui(ds,FFNET_gui,rpFFNET_info):
    # populate the rpFFNET_info dictionary with things that will be useful
    #
    rpFFNET_info["overwrite"] = True
    if FFNET_gui.owopt.get()==0: rpFFNET_info["overwrite"] = False
    rpFFNET_info["show_plots"] = True
    if FFNET_gui.pltopt.get()==0: rpFFNET_info["show_plots"] = False
    rpFFNET_info["auto_complete"] = True
    if FFNET_gui.autocompleteopt.get()==0: rpFFNET_info["auto_complete"] = False
    #
    rpFFNET_info["hidden"] = FFNET_gui.nodesEntry.get()
    rpFFNET_info["training"] = FFNET_gui.trainingEntry.get()
    if int(FFNET_gui.connecVar.get())==1:
        rpFFNET_info["connection"] = "standard"
    else:
        rpFFNET_info["connection"] = "full"
    rpFFNET_info["training_type"] = str(FFNET_gui.trainTypeVar.get())
    rpFFNET_info["peropt"] = FFNET_gui.peropt.get()
    rpFFNET_info["min_percent"] = int(FFNET_gui.minptsEntry.get())
    rpFFNET_info["site_name"] = ds.globalattributes["site_name"]
    rpFFNET_info["time_step"] = int(ds.globalattributes["time_step"])
    rpFFNET_info["nperhr"] = int(float(60)/rpFFNET_info["time_step"]+0.5)
    rpFFNET_info["nperday"] = int(float(24)*rpFFNET_info["nperhr"]+0.5)
    rpFFNET_info["maxlags"] = int(float(12)*rpFFNET_info["nperhr"]+0.5)
    rpFFNET_info["tower"] = {}
    rpFFNET_info["access"] = {}
    #log.info(" Estimating ER using SOLO")
    if FFNET_gui.peropt.get()==1:
        rpFFNET_progress(FFNET_gui,"Starting manual run ...")
        # get the start and end datetimes entered in the SOLO GUI
        rpFFNET_info["startdate"] = FFNET_gui.startEntry.get()
        if len(rpFFNET_info["startdate"])==0: rpFFNET_info["startdate"] = rpFFNET_info["file_startdate"]
        rpFFNET_info["enddate"] = FFNET_gui.endEntry.get()
        if len(rpFFNET_info["enddate"])==0: rpFFNET_info["enddate"] = rpFFNET_info["file_enddate"]
        rpFFNET_main(ds,rpFFNET_info,FFNET_gui=FFNET_gui)
        rpFFNET_progress(FFNET_gui,"Finished manual run ...")
    elif FFNET_gui.peropt.get()==2:
        rpFFNET_progress(FFNET_gui,"Starting auto (monthly) run ...")
        # get the start datetime entered in the SOLO GUI
        rpFFNET_info["startdate"] = FFNET_gui.startEntry.get()
        if len(rpFFNET_info["startdate"])==0: rpFFNET_info["startdate"] = rpFFNET_info["file_startdate"]
        startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        file_startdate = dateutil.parser.parse(rpFFNET_info["file_startdate"])
        file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([file_enddate,enddate])
        rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        while startdate<file_enddate:
            rpFFNET_main(ds,rpFFNET_info,FFNET_gui=FFNET_gui)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
        rpFFNET_progress(FFNET_gui,"Finished auto (monthly) run ...")
    elif FFNET_gui.peropt.get()==3:
        rpFFNET_progress(FFNET_gui,"Starting auto (days) run ...")
        # get the start datetime entered in the SOLO GUI
        rpFFNET_info["startdate"] = FFNET_gui.startEntry.get()
        rpFFNET_info["enddate"] = FFNET_gui.endEntry.get()
        if len(rpFFNET_info["startdate"])==0: rpFFNET_info["startdate"] = rpFFNET_info["file_startdate"]
        if len(rpFFNET_info["enddate"])==0: rpFFNET_info["enddate"] = rpFFNET_info["file_enddate"]
        startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        rpFFNET_info["gui_enddate"] = rpFFNET_info["enddate"]
        gui_enddate = dateutil.parser.parse(rpFFNET_info["gui_enddate"])
        file_startdate = dateutil.parser.parse(rpFFNET_info["file_startdate"])
        file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        nDays = int(FFNET_gui.daysEntry.get())
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate,enddate,gui_enddate])
        rpFFNET_info["startdate"] = datetime.datetime.strftime(startdate,"%Y-%m-%d")
        rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        stopdate = min([file_enddate,gui_enddate])
        while startdate<stopdate:  #file_enddate:
            rpFFNET_main(ds,rpFFNET_info,FFNET_gui=FFNET_gui)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            rpFFNET_info["enddate"] = run_enddate.strftime("%Y-%m-%d")
        rpFFNET_progress(FFNET_gui,"Finished auto (days) run ...")
    elif FFNET_gui.peropt.get()==4:
        # automatic run with yearly datetime periods
        rpFFNET_progress(FFNET_gui,"Starting auto (yearly) run ...")
        # get the start date
        rpFFNET_info["startdate"] = FFNET_gui.startEntry.get()
        if len(rpFFNET_info["startdate"])==0: rpFFNET_info["startdate"] = rpFFNET_info["file_startdate"]
        startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        # get the start year
        start_year = startdate.year
        enddate = dateutil.parser.parse(str(start_year+1)+"-01-01 00:00")
        file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        enddate = min([file_enddate,enddate])
        rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        while startdate<file_enddate:
            rpFFNET_main(ds,rpFFNET_info,FFNET_gui=FFNET_gui)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(years=1)
            rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
        rpFFNET_progress(FFNET_gui,"Finished auto (yearly) run ...")
    elif FFNET_gui.peropt.get()==5:
        pass

def rpFFNET_run_nogui(cf,ds,rpFFNET_info):
    # populate the rpFFNET_info dictionary with things that will be useful
    dt = ds.series["DateTime"]["Data"]
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"period_option",default="manual")
    if opt=="manual":
        rpFFNET_info["peropt"] = 1
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: rpFFNET_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"end_date",default="")
        rpFFNET_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: rpFFNET_info["enddate"] = ed
    elif opt=="monthly":
        rpFFNET_info["peropt"] = 2
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: rpFFNET_info["startdate"] = sd
    elif opt=="days":
        rpFFNET_info["peropt"] = 3
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: rpFFNET_info["startdate"] = sd
        ed = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"end_date",default="")
        rpFFNET_info["enddate"] = dt[-1].strftime("%Y-%m-%d %H:%M")
        if len(ed)!=0: rpFFNET_info["enddate"] = ed
    elif opt=="yearly":
        rpFFNET_info["peropt"] = 4
        sd = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"start_date",default="")
        rpFFNET_info["startdate"] = dt[0].strftime("%Y-%m-%d %H:%M")
        if len(sd)!=0: rpFFNET_info["startdate"] = sd
    # number of hidden layers
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"hidden_nodes",default="6,4")
    rpFFNET_info["hidden"] = str(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"training",default=500)
    rpFFNET_info["training"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"training_type",default="rprop")
    rpFFNET_info["training_type"] = str(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"connection",default="full")
    rpFFNET_info["connection"] = str(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"min_percent",default=10)
    rpFFNET_info["min_percent"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"number_days",default=90)
    rpFFNET_info["number_days"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"number_months",default=6)
    rpFFNET_info["number_months"] = int(opt)
    rpFFNET_info["show_plots"] = True
    opt = pfp_utils.get_keyvaluefromcf(cf,["GUI","FFNET"],"show_plots",default="yes")
    if opt.lower()=="no": rpFFNET_info["show_plots"] = False

    rpFFNET_info["site_name"] = ds.globalattributes["site_name"]
    rpFFNET_info["time_step"] = int(ds.globalattributes["time_step"])
    rpFFNET_info["nperhr"] = int(float(60)/rpFFNET_info["time_step"]+0.5)
    rpFFNET_info["nperday"] = int(float(24)*rpFFNET_info["nperhr"]+0.5)
    rpFFNET_info["maxlags"] = int(float(12)*rpFFNET_info["nperhr"]+0.5)
    rpFFNET_info["tower"] = {}
    rpFFNET_info["access"] = {}
    if rpFFNET_info["peropt"]==1:
        rpFFNET_main(ds,rpFFNET_info)
    elif rpFFNET_info["peropt"]==2:
        # get the start datetime entered in the SOLO GUI
        startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        file_startdate = dateutil.parser.parse(rpFFNET_info["file_startdate"])
        file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        nDays = rpFFNET_info["number_days"]
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate,enddate])
        rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        while startdate<file_enddate:
            rpFFNET_main(ds,rpFFNET_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
    elif rpFFNET_info["peropt"]==3:
        # get the start datetime entered in the SOLO GUI
        startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        file_startdate = dateutil.parser.parse(rpFFNET_info["file_startdate"])
        file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        nMonths = rpFFNET_info["number_months"]
        enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
        enddate = min([file_enddate,enddate])
        rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        while startdate<file_enddate:
            rpFFNET_main(ds,rpFFNET_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
            rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
    elif rpFFNET_info["peropt"]==4:
        # get the start date
        startdate = dateutil.parser.parse(rpFFNET_info["startdate"])
        # get the start year
        start_year = startdate.year
        enddate = dateutil.parser.parse(str(start_year+1)+"-01-01 00:00")
        file_enddate = dateutil.parser.parse(rpFFNET_info["file_enddate"])
        enddate = min([file_enddate,enddate])
        rpFFNET_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        while startdate<file_enddate:
            rpFFNET_main(ds,rpFFNET_info)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(years=1)
            rpFFNET_info["startdate"] = startdate.strftime("%Y-%m-%d")
            rpFFNET_info["enddate"] = enddate.strftime("%Y-%m-%d")
    elif FFNET_gui.peropt.get()==5:
        pass

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
    driver_list = ast.literal_eval(cf[section][series]["ERUsingSOLO"]["drivers"])
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
    solo_info["target"] = cf[section][series]["ERUsingSOLO"]["target"]
    # list of drivers
    solo_info["drivers"] = ast.literal_eval(cf[section][series]["ERUsingSOLO"]["drivers"])
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
    ds.merge["standard"][series]["source"] = ast.literal_eval(cf[section][series]["MergeSeries"]["Source"])
    # create an empty series in ds if the output series doesn't exist yet
    if ds.merge["standard"][series]["output"] not in ds.series.keys():
        data,flag,attr = pfp_utils.MakeEmptySeries(ds,ds.merge["standard"][series]["output"])
        pfp_utils.CreateSeries(ds,ds.merge["standard"][series]["output"],data,flag,attr)
    return solo_info

def rpSOLO_done(ds,SOLO_gui,solo_info):
    # destroy the SOLO GUI
    SOLO_gui.destroy()

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

def rpSOLO_main(ds,solo_info,SOLO_gui=None):
    """
    This is the main routine for running SOLO, an artifical neural network for estimating ER.
    """
    startdate = solo_info["startdate"]
    enddate = solo_info["enddate"]
    logger.info(" Estimating ER using SOLO: "+startdate+" to "+enddate)
    # read the control file again, this allows the contents of the control file to
    # be changed with the SOLO GUI still displayed
    cfname = ds.globalattributes["controlfile_name"]
    cf = pfp_io.get_controlfilecontents(cfname,mode="quiet")
    solo_series = solo_info["er"].keys()
    for series in solo_series:
        section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
        if len(section)==0: continue
        if series not in ds.series.keys(): continue
        solo_info["er"][series]["target"] = cf[section][series]["ERUsingSOLO"]["target"]
        solo_info["er"][series]["drivers"] = ast.literal_eval(cf[section][series]["ERUsingSOLO"]["drivers"])
        solo_info["er"][series]["output"] = cf[section][series]["ERUsingSOLO"]["output"]
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
        if solo_info["call_mode"].lower()=="interactive":
            nodesAuto = rpSOLO_setnodesEntry(SOLO_gui,drivers,default=10)
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
        if solo_info["call_mode"].lower()=="interactive":
            if nodesAuto: rpSOLO_resetnodesEntry(SOLO_gui)
    if 'ERUsingSOLO' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+', ERUsingSOLO'

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

def rpSOLO_progress(SOLO_gui,text):
    """
        Update progress message in SOLO GUI
        """
    SOLO_gui.progress.destroy()
    SOLO_gui.progress = Tkinter.Label(SOLO_gui, text=text)
    SOLO_gui.progress.grid(row=SOLO_gui.progress_row,column=0,columnspan=6,sticky="W")
    SOLO_gui.update()

def rpSOLO_resetnodesEntry(SOLO_gui):
    SOLO_gui.nodesEntry.delete(0,Tkinter.END)
    SOLO_gui.nodesEntry.insert(0,"10")

def rpSOLO_run_gui(ds,SOLO_gui,solo_info):
    # populate the solo_info dictionary with things that will be useful
    #
    solo_info["overwrite"] = True
    if SOLO_gui.owopt.get()==0: solo_info["overwrite"] = False
    solo_info["show_plots"] = True
    if SOLO_gui.pltopt.get()==0: solo_info["show_plots"] = False
    solo_info["auto_complete"] = True
    if SOLO_gui.autocompleteopt.get()==0: solo_info["auto_complete"] = False
    #
    solo_info["nodes"] = SOLO_gui.nodesEntry.get()
    solo_info["training"] = SOLO_gui.trainingEntry.get()
    solo_info["nda_factor"] = SOLO_gui.factorEntry.get()
    solo_info["learningrate"] = SOLO_gui.learningrateEntry.get()
    solo_info["iterations"] = SOLO_gui.iterationsEntry.get()
    solo_info["peropt"] = SOLO_gui.peropt.get()
    solo_info["min_percent"] = int(SOLO_gui.minptsEntry.get())
    solo_info["site_name"] = ds.globalattributes["site_name"]
    solo_info["time_step"] = int(ds.globalattributes["time_step"])
    solo_info["nperhr"] = int(float(60)/solo_info["time_step"]+0.5)
    solo_info["nperday"] = int(float(24)*solo_info["nperhr"]+0.5)
    solo_info["maxlags"] = int(float(12)*solo_info["nperhr"]+0.5)
    solo_info["tower"] = {}
    solo_info["access"] = {}
    #log.info(" Estimating ER using SOLO")
    if SOLO_gui.peropt.get()==1:
        # manual run using start and end datetime entered via GUI
        rpSOLO_progress(SOLO_gui,"Starting manual run ...")
        solo_info["startdate"] = SOLO_gui.startEntry.get()
        if len(solo_info["startdate"])==0: solo_info["startdate"] = solo_info["file_startdate"]
        solo_info["enddate"] = SOLO_gui.endEntry.get()
        if len(solo_info["enddate"])==0: solo_info["enddate"] = solo_info["file_enddate"]
        rpSOLO_main(ds,solo_info,SOLO_gui=SOLO_gui)
        rpSOLO_progress(SOLO_gui,"Finished manual run ...")
    elif SOLO_gui.peropt.get()==2:
        # automatic run with monthly datetime periods
        rpSOLO_progress(SOLO_gui,"Starting auto (monthly) run ...")
        solo_info["startdate"] = SOLO_gui.startEntry.get()
        if len(solo_info["startdate"])==0: solo_info["startdate"] = solo_info["file_startdate"]
        startdate = dateutil.parser.parse(solo_info["startdate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
        enddate = min([file_enddate,enddate])
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        while startdate<file_enddate:
            rpSOLO_main(ds,solo_info,SOLO_gui=SOLO_gui)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=1)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d")
        rpSOLO_progress(SOLO_gui,"Finished auto (monthly) run ...")
    elif SOLO_gui.peropt.get()==3:
        # automatc run with number of days specified by user via the GUI
        rpSOLO_progress(SOLO_gui,"Starting auto (days) run ...")
        solo_info["startdate"] = SOLO_gui.startEntry.get()
        solo_info["enddate"] = SOLO_gui.endEntry.get()
        if len(solo_info["startdate"])==0: solo_info["startdate"] = solo_info["file_startdate"]
        if len(solo_info["enddate"])==0: solo_info["enddate"] = solo_info["file_enddate"]
        startdate = dateutil.parser.parse(solo_info["startdate"])
        solo_info["gui_enddate"] = solo_info["enddate"]
        gui_enddate = dateutil.parser.parse(solo_info["gui_enddate"])
        file_startdate = dateutil.parser.parse(solo_info["file_startdate"])
        file_enddate = dateutil.parser.parse(solo_info["file_enddate"])
        nDays = int(SOLO_gui.daysEntry.get())
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([file_enddate,enddate,gui_enddate])
        solo_info["startdate"] = datetime.datetime.strftime(startdate,"%Y-%m-%d")
        solo_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d")
        stopdate = min([file_enddate,gui_enddate])
        while startdate<stopdate:  #file_enddate:
            rpSOLO_main(ds,solo_info,SOLO_gui=SOLO_gui)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d")
            solo_info["enddate"] = run_enddate.strftime("%Y-%m-%d")
        rpSOLO_progress(SOLO_gui,"Finished auto (days) run ...")
    elif SOLO_gui.peropt.get()==4:
        # automatic run with yearly datetime periods
        rpSOLO_progress(SOLO_gui,"Starting auto (yearly) run ...")
        # get the start date
        solo_info["startdate"] = SOLO_gui.startEntry.get()
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
            rpSOLO_main(ds,solo_info,SOLO_gui=SOLO_gui)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(years=1)
            solo_info["startdate"] = startdate.strftime("%Y-%m-%d")
            solo_info["enddate"] = enddate.strftime("%Y-%m-%d")
        rpSOLO_progress(SOLO_gui,"Finished auto (yearly) run ...")
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

def rpSOLO_setnodesEntry(SOLO_gui,drivers,default=2):
    nodesAuto = False
    if str(SOLO_gui.nodesEntry.get()).lower()=="auto":
        nodesAuto = True
        SOLO_gui.nodesEntry.delete(0,Tkinter.END)
        num_nodes = max([len(drivers)+1,default])
        SOLO_gui.nodesEntry.insert(0,str(num_nodes))
    return nodesAuto

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
