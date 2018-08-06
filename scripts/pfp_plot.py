import ast
import constants as c
import datetime
import time
import math
import matplotlib.dates as mdt
import matplotlib.pyplot as plt
import meteorologicalfunctions as mf
import numpy
import os
import statsmodels.api as sm
import sys
import pfp_ck
import pfp_io
import pfp_utils
import logging

logger = logging.getLogger("pfp_log")

def get_diurnalstats(DecHour,Data,dt):
    nInts = 24*int((60/dt)+0.5)
    Hr = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    Av = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    Sd = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    Mx = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    Mn = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    for i in range(nInts):
        Hr[i] = float(i)*dt/60.
        li = numpy.where((abs(DecHour-Hr[i])<c.eps)&(abs(Data-float(c.missing_value))>c.eps))
        if numpy.size(li)!=0:
            Av[i] = numpy.mean(Data[li])
            Sd[i] = numpy.std(Data[li])
            Mx[i] = numpy.max(Data[li])
            Mn[i] = numpy.min(Data[li])
    return Hr, Av, Sd, Mx, Mn

def get_ticks(start, end):
    from datetime import timedelta as td
    delta = end - start

    if delta <= td(minutes=10):
        loc = mdt.MinuteLocator()
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(minutes=30):
        loc = mdt.MinuteLocator(byminute=range(0,60,5))
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(hours=1):
        loc = mdt.MinuteLocator(byminute=range(0,60,15))
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(hours=6):
        loc = mdt.HourLocator()
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(days=1):
        loc = mdt.HourLocator(byhour=range(0,24,3))
        fmt = mdt.DateFormatter('%H:%M')
    elif delta <= td(days=3):
        loc = mdt.HourLocator(byhour=range(0,24,12))
        fmt = mdt.DateFormatter('%d/%m %H')
    elif delta <= td(weeks=2):
        loc = mdt.DayLocator()
        fmt = mdt.DateFormatter('%d/%m')
    elif delta <= td(weeks=12):
        loc = mdt.WeekdayLocator()
        fmt = mdt.DateFormatter('%d/%m')
    elif delta <= td(weeks=104):
        loc = mdt.MonthLocator()
        fmt = mdt.DateFormatter('%d/%m')
    elif delta <= td(weeks=208):
        loc = mdt.MonthLocator(interval=3)
        fmt = mdt.DateFormatter('%d/%m/%y')
    else:
        loc = mdt.MonthLocator(interval=6)
        fmt = mdt.DateFormatter('%d/%m/%y')
    return loc,fmt

def get_yarray(ds,ThisOne):
    yarray = numpy.ma.masked_where(abs(ds.series[ThisOne]['Data']-float(c.missing_value))<c.eps,
                                        ds.series[ThisOne]['Data'])
    nRecs = numpy.ma.size(yarray)
    nNotM = numpy.ma.count(yarray)
    nMskd = numpy.ma.count_masked(yarray)
    if numpy.ma.count(yarray)==0:
        yarray = numpy.ma.zeros(numpy.size(yarray))
    return yarray,nRecs,nNotM,nMskd

def get_yaxislimitsfromcf(cf,nFig,maxkey,minkey,nSer,YArray):
    if maxkey in cf['Plots'][str(nFig)].keys():                               # Y axis minima specified
        maxlist = ast.literal_eval(cf['Plots'][str(nFig)][maxkey])     # Evaluate the minima list
        if str(maxlist[nSer])=='Auto':             # This entry is 'Auto' ...
            YAxMax = numpy.ma.maximum(YArray)                        # ... so take the array minimum value
        else:
            YAxMax = float(maxlist[nSer])         # Evaluate the entry for this series
    else:
        YAxMax = numpy.ma.maximum(YArray)                            # Y axis minima not given, use auto
    if minkey in cf['Plots'][str(nFig)].keys():                               # Y axis minima specified
        minlist = ast.literal_eval(cf['Plots'][str(nFig)][minkey])     # Evaluate the minima list
        if str(minlist[nSer])=='Auto':             # This entry is 'Auto' ...
            YAxMin = numpy.ma.minimum(YArray)                        # ... so take the array minimum value
        else:
            YAxMin = float(minlist[nSer])         # Evaluate the entry for this series
    else:
        YAxMin = numpy.ma.minimum(YArray)                            # Y axis minima not given, use auto
    if (abs(YAxMax-YAxMin) < c.eps):
        YAxDelta = 0.001*YAxMax
        if YAxDelta == 0:
            YAxDelta = 1
        YAxMax = YAxMax + YAxDelta
        YAxMin = YAxMin - YAxDelta
    return YAxMax,YAxMin

def pltfingerprint_createdict(cf,ds):
    fp_info = {}
    fp_info["general"] = {}
    fp_info["variables"] = {}
    # parse the control file to get the information for the fingerprint plot
    for var in cf["Variables"]:
        # create the dictionary for this variable
        fp_info["variables"][var] = {}
        # get the input filename
        if "in_filename" in cf["Variables"][var]:
            fp_info["variables"][var]["in_filename"] = str(cf["Variables"][var]["in_filename"])
        else:
            fp_info["variables"][var]["in_filename"] = pfp_io.get_infilenamefromcf(cf)
        # get the variable name
        if "nc_varname" in cf["Variables"][var]:
            fp_info["variables"][var]["nc_varname"] = str(cf["Variables"][var]["nc_varname"])
        else:
            fp_info["variables"][var]["nc_varname"] = str(var)
        # get the upper and lower range limits
        if "Lower" in cf["Variables"][var]:
            fp_info["variables"][var]["Lower"] = float(cf["Variables"][var]["Lower"])
        else:
            fp_info["variables"][var]["Lower"] = float(-1)*c.large_value
        if "Upper" in cf["Variables"][var]:
            fp_info["variables"][var]["Upper"] = float(cf["Variables"][var]["Upper"])
        else:
            fp_info["variables"][var]["Upper"] = c.large_value
    # get the start and end datetimes for all files and find the overlap period
    var_list = fp_info["variables"].keys()
    ds_0 = ds[fp_info["variables"][var_list[0]]["in_filename"]]
    fp_info["variables"][var_list[0]]["start_date"] = ds_0.series["DateTime"]["Data"][0]
    fp_info["variables"][var_list[0]]["end_date"] = ds_0.series["DateTime"]["Data"][-1]
    fp_info["general"]["overlap_start"] = fp_info["variables"][var_list[0]]["start_date"]
    fp_info["general"]["overlap_end"] = fp_info["variables"][var_list[0]]["end_date"]
    fp_info["variables"][var_list[0]]["nc_nrecs"] = int(ds_0.globalattributes["nc_nrecs"])
    fp_info["variables"][var_list[0]]["site_name"] = str(ds_0.globalattributes["site_name"])
    fp_info["variables"][var_list[0]]["nc_level"] = str(ds_0.globalattributes["nc_level"])
    fp_info["variables"][var_list[0]]["time_step"] = int(ds_0.globalattributes["time_step"])
    if len(var_list)>1:
        for var in var_list[1:]:
            ds_n = ds[fp_info["variables"][var]["in_filename"]]
            fp_info["variables"][var]["start_date"] = ds_n.series["DateTime"]["Data"][0]
            fp_info["variables"][var]["end_date"] = ds_n.series["DateTime"]["Data"][-1]
            fp_info["variables"][var]["nc_nrecs"] = int(ds_n.globalattributes["nc_nrecs"])
            fp_info["variables"][var]["site_name"] = str(ds_n.globalattributes["site_name"])
            fp_info["variables"][var]["nc_level"] = str(ds_n.globalattributes["nc_level"])
            fp_info["variables"][var]["time_step"] = int(ds_n.globalattributes["time_step"])
            # get the start and end datetimes where the files overlap
            fp_info["general"]["overlap_start"] = max([fp_info["general"]["overlap_start"],fp_info["variables"][var]["start_date"]])
            fp_info["general"]["overlap_end"] = min([fp_info["general"]["overlap_end"],fp_info["variables"][var]["end_date"]])
    return fp_info

def pltfingerprint_readncfiles(cf):
    ds = {}
    if "Files" in cf:
        infilename = pfp_io.get_infilenamefromcf(cf)
        ds[infilename] = pfp_io.nc_read_series(infilename)
    for var in cf["Variables"].keys():
        if "in_filename" in cf["Variables"][var]:
            if cf["Variables"][var]["in_filename"] not in ds:
                infilename = cf["Variables"][var]["in_filename"]
                ds[cf["Variables"][var]["in_filename"]] = pfp_io.nc_read_series(infilename)
    return ds

def plot_fingerprint(cf):
    """ Do a fingerprint plot"""
    # set up some variable aliases
    aliases = {"CO2":["CO2", "Cc"], "Cc":["Cc", "CO2"],
               "H2O":["H2O", "Ah"], "Ah":["Ah", "H2O"]}
    # read the input files
    ds = pltfingerprint_readncfiles(cf)
    # create a dictionary to hold the fingerprint plot information
    fp_info = pltfingerprint_createdict(cf,ds)
    overlap_start = fp_info["general"]["overlap_start"]
    overlap_end = fp_info["general"]["overlap_end"]
    # get a list of site names and remove duplicates
    var_list = fp_info["variables"].keys()
    site_name_list = [fp_info["variables"][var]["site_name"] for var in var_list]
    site_name_list = list(set(site_name_list))
    site_name = ','.join(str(x) for x in site_name_list)
    # do the same for processing levels
    level_list = [fp_info["variables"][var]["nc_level"] for var in var_list]
    level_list = list(set(level_list))
    level = ','.join(str(x) for x in level_list)
    title_str = site_name+' '+level
    title_str = title_str+' from '+str(overlap_start)+' to '+str(overlap_end)
    # loop over plots
    opt = pfp_utils.get_keyvaluefromcf(cf,["Options"],"show_plots",default="yes")
    for nFig in cf["Plots"].keys():
        if opt.lower()=="yes":
            plt.ion()
        else:
            plt.ioff()
        fig = plt.figure(nFig,figsize=(13,8))
        fig.clf()
        fig.canvas.set_window_title(cf["Plots"][str(nFig)]["Title"])
        plt.figtext(0.5,0.95,title_str,horizontalalignment='center')
        fig_var_list = pfp_utils.GetPlotVariableNamesFromCF(cf,nFig)
        logger.info("Plotting fingerprint: "+str(fig_var_list))
        nPlots = len(fig_var_list)
        for n,var in enumerate(fig_var_list):
            nc_varname = fp_info["variables"][var]["nc_varname"]
            infilename = fp_info["variables"][var]["in_filename"]
            ldt = ds[infilename].series["DateTime"]["Data"]
            ts = fp_info["variables"][var]["time_step"]
            si = pfp_utils.GetDateIndex(ldt,str(overlap_start),ts=ts,default=0,match='startnextday')
            ei = pfp_utils.GetDateIndex(ldt,str(overlap_end),ts=ts,default=-1,match='endpreviousday')
            ldt = ldt[si:ei+1]
            nPerHr = int(float(60)/ts+0.5)
            nPerDay = int(float(24)*nPerHr+0.5)
            nDays = len(ldt)/nPerDay
            sd = datetime.datetime.toordinal(ldt[0])
            ed = datetime.datetime.toordinal(ldt[-1])
            # let's check the named variable is in the data structure
            if nc_varname not in ds[infilename].series.keys():
                # if it isn't, let's look for an alias
                if nc_varname in aliases.keys():
                    found_alias = False
                    for alias in aliases[nc_varname]:
                        if alias in ds[infilename].series.keys():
                            nc_varname = alias
                            found_alias = True
                    if not found_alias:
                        msg = " Variable "+nc_varname+" not found in data structure, skipping ..."
                        logger.warning(msg)
                        continue
                else:
                    msg = " No alias found for "+nc_varname+", skipping ..."
                    logger.warning(msg)
                    continue
            data,flag,attr = pfp_utils.GetSeriesasMA(ds[infilename],nc_varname,si=si,ei=ei)
            data = pfp_ck.cliptorange(data,fp_info["variables"][var]["Lower"],fp_info["variables"][var]["Upper"])
            data_daily = data.reshape(nDays,nPerDay)
            units = str(ds[infilename].series[nc_varname]['Attr']['units'])
            label = var + ' (' + units + ')'
            loc,fmt = get_ticks(datetime.datetime.fromordinal(sd),datetime.datetime.fromordinal(ed))
            if n==0:
                ax = plt.subplot(1,nPlots,n+1)
            else:
                ax = plt.subplot(1,nPlots,n+1,sharey=ax)
            plt.imshow(data_daily,extent=[0,24,sd,ed],aspect='auto',origin='lower')
            ax.yaxis.set_major_locator(loc)
            ax.yaxis.set_major_formatter(fmt)
            # only plot the colourbar if there is data to plot
            if numpy.ma.count(data)!=0:
                cb = plt.colorbar(orientation='horizontal',fraction=0.02,pad=0.075)
                if numpy.min(data)==numpy.max(data):
                    if numpy.min(data)!=0:
                        data_min = numpy.min(data)-0.01*numpy.min(data)
                        data_max = numpy.max(data)+0.01*numpy.max(data)
                    else:
                        data_min = -1.0
                        data_max = 1.0
                else:
                    data_min = numpy.min(data)
                    data_max = numpy.max(data)
                cb.set_ticks(numpy.linspace(data_min,data_max,4))
            plt.xticks([0,6,12,18,24])
            plt.xlabel(label)
            if n!= 0: plt.setp(ax.get_yticklabels(), visible=False)
        if "Files" in cf:
            if "plot_path" in cf["Files"]:
                plot_path = cf["Files"]["plot_path"]+"fingerprint/"
            else:
                plot_path = "plots/"
        else:
            plot_path = "plots/"
        if not os.path.exists(plot_path): os.makedirs(plot_path)
        pngname = plot_path+site_name.replace(' ','')+'_'+level+'_'
        pngname = pngname+pfp_utils.GetPlotTitleFromCF(cf,nFig).replace(' ','_')+'.png'
        fig.savefig(pngname,format='png')
        if opt.lower=="yes":
            plt.draw()
            plt.ioff()
        else:
            plt.ion()

def plot_fluxnet(cf):
    """ Plot the FluxNet style plots. """

    series_list = cf["Variables"].keys()
    infilename = pfp_io.get_infilenamefromcf(cf)

    ds = pfp_io.nc_read_series(infilename)
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    site_name = ds.globalattributes["site_name"]

    ldt=ds.series["DateTime"]["Data"]
    sdt = ldt[0]
    edt = ldt[-1]
    # Tumbarumba doesn't have RH in the netCDF files
    if "RH" not in ds.series.keys():
        Ah,f,a = pfp_utils.GetSeriesasMA(ds,'Ah')
        Ta,f,a = pfp_utils.GetSeriesasMA(ds,'Ta')
        RH = mf.RHfromabsolutehumidity(Ah, Ta)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Relative humidity',units='%',standard_name='relative_humidity')
        flag = numpy.where(numpy.ma.getmaskarray(RH)==True,ones,zeros)
        pfp_utils.CreateSeries(ds,"RH",RH,flag,attr)

    nFig = 0
    plt.ion()
    for series in series_list:
        if series not in ds.series.keys():
            logger.error("Series "+series+" not found in input file, skipping ...")
            continue
        logger.info(" Doing plot for "+series)
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,series))
        nFig = nFig + 1
        fig = plt.figure(nFig,figsize=(10.9,7.5))
        fig.canvas.set_window_title(series)
        plt.plot(ldt,data,"b.")
        plt.xlim(sdt,edt)
        plt.xlabel("Date")
        plt.ylabel(series+" ("+attr["units"]+")")
        title_str = site_name+": "+sdt.strftime("%Y-%m-%d")+" to "+edt.strftime("%Y-%m-%d")+"; "+series
        plt.title(title_str)
        figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_FC_'+series+'.png'
        fig.savefig(figname,format='png')
        plt.draw()
    plt.ioff()

def plottimeseries(cf, nFig, dsa, dsb):
    SiteName = dsa.globalattributes['site_name']
    Level = dsb.globalattributes['nc_level']
    dt = int(dsa.globalattributes['time_step'])
    Month = dsa.series['Month']['Data'][0]
    p = plot_setup(cf,nFig)
    logger.info(' Plotting series: '+str(p['SeriesList']))
    #L1XArray = numpy.array(dsa.series['DateTime']['Data'][si:ei])
    #L2XArray = numpy.array(dsb.series['DateTime']['Data'][si:ei])
    L1XArray = dsa.series['DateTime']['Data']
    L2XArray = dsb.series['DateTime']['Data']
    p['XAxMin'] = min(L2XArray)
    p['XAxMax'] = max(L2XArray)
    p['loc'],p['fmt'] = get_ticks(p['XAxMin'],p['XAxMax'])
    plt.ion()
    #plt.ioff()
    fig = plt.figure(figsize=(p['PlotWidth'],p['PlotHeight']))
    fig.clf()
    fig.canvas.set_window_title(p['PlotDescription'])
    plt.figtext(0.5,0.95,SiteName+': '+p['PlotDescription'],ha='center',size=16)
    for ThisOne, n in zip(p['SeriesList'],range(p['nGraphs'])):
        if ThisOne in dsa.series.keys():
            aflag = dsa.series[ThisOne]['Flag']
            p['Units'] = dsa.series[ThisOne]['Attr']['units']
            p['YAxOrg'] = p['ts_YAxOrg'] + n*p['yaxOrgOffset']
            L1YArray,p['nRecs'],p['nNotM'],p['nMskd'] = get_yarray(dsa, ThisOne)
            # check the control file to see if the Y axis minima have been specified
            nSer = p['SeriesList'].index(ThisOne)
            p['LYAxMax'],p['LYAxMin'] = get_yaxislimitsfromcf(cf,nFig,'YLMax','YLMin',nSer,L1YArray)
            plot_onetimeseries_left(fig,n,ThisOne,L1XArray,L1YArray,p)
        if ThisOne in dsb.series.keys():
            bflag = dsb.series[ThisOne]['Flag']
            p['Units'] = dsb.series[ThisOne]['Attr']['units']
            p['YAxOrg'] = p['ts_YAxOrg'] + n*p['yaxOrgOffset']
            #Plot the Level 2 data series on the same X axis but with the scale on the right Y axis.
            L2YArray,p['nRecs'],p['nNotM'],p['nMskd'] = get_yarray(dsb, ThisOne)
            # check the control file to see if the Y axis minima have been specified
            nSer = p['SeriesList'].index(ThisOne)
            p['RYAxMax'],p['RYAxMin'] = get_yaxislimitsfromcf(cf,nFig,'YRMax','YRMin',nSer,L2YArray)
            plot_onetimeseries_right(fig,n,ThisOne,L2XArray,L2YArray,p)

            #Plot the diurnal averages.
            Hr2,Av2,Sd2,Mx2,Mn2=get_diurnalstats(dsb.series['Hdh']['Data'], dsb.series[ThisOne]['Data'], dt)
            Av2 = numpy.ma.masked_where(Av2==c.missing_value,Av2)
            Sd2 = numpy.ma.masked_where(Sd2==c.missing_value,Sd2)
            Mx2 = numpy.ma.masked_where(Mx2==c.missing_value,Mx2)
            Mn2 = numpy.ma.masked_where(Mn2==c.missing_value,Mn2)
            hr2_ax = fig.add_axes([p['hr1_XAxOrg'],p['YAxOrg'],p['hr2_XAxLen'],p['ts_YAxLen']])
            #hr2_ax.hold(True)
            hr2_ax.plot(Hr2,Av2,'y-',Hr2,Mx2,'r-',Hr2,Mn2,'b-')
            section = pfp_utils.get_cfsection(cf,series=ThisOne,mode='quiet')
            if len(section)!=0:
                if 'DiurnalCheck' in cf[section][ThisOne].keys():
                    NSdarr = numpy.array(eval(cf[section][ThisOne]['DiurnalCheck']['NumSd']),dtype=float)
                    nSd = NSdarr[Month-1]
                    hr2_ax.plot(Hr2,Av2+nSd*Sd2,'r.',Hr2,Av2-nSd*Sd2,'b.')
            plt.xlim(0,24)
            plt.xticks([0,6,12,18,24])
            if n==0:
                hr2_ax.set_xlabel('Hour',visible=True)
            else:
                hr2_ax.set_xlabel('',visible=False)
                plt.setp(hr2_ax.get_xticklabels(), visible=False)
            #if n > 0: plt.setp(hr2_ax.get_xticklabels(), visible=False)

            # vertical lines to show frequency distribution of flags
            bins = numpy.arange(0.5,23.5)
            ind = bins[:len(bins)-1]+0.5
            index = numpy.where(numpy.mod(bflag,10)==0)    # find the elements with flag = 0, 10, 20 etc
            bflag[index] = 0                               # set them all to 0
            hist, bin_edges = numpy.histogram(bflag, bins=bins)
            ymin = hist*0
            delta = 0.01*(numpy.max(hist)-numpy.min(hist))
            bar_ax = fig.add_axes([p['hr2_XAxOrg'],p['YAxOrg'],p['bar_XAxLen'],p['ts_YAxLen']])
            bar_ax.set_ylim(0,numpy.max([1,numpy.max(hist)]))
            bar_ax.vlines(ind,ymin,hist)
            for i,j in zip(ind,hist):
                if j>0.05*numpy.max(hist): bar_ax.text(i,j+delta,str(int(i)),ha='center',size='small')
            if n==0:
                bar_ax.set_xlabel('Flag',visible=True)
            else:
                bar_ax.set_xlabel('',visible=False)
                plt.setp(bar_ax.get_xticklabels(), visible=False)
            #if n > 0: plt.setp(bar_ax.get_xticklabels(), visible=False)
        else:
            logger.error('  plttimeseries: series '+ThisOne+' not in data structure')
    fig.show()
    if "plot_path" in cf["Files"]:
        plot_path = os.path.join(cf["Files"]["plot_path"],Level)
    else:
        plot_path = "plots/"
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
    fname = os.path.join(plot_path, SiteName.replace(' ','')+'_'+Level+'_'+p['PlotDescription'].replace(' ','')+'.png')
    fig.savefig(fname,format='png')

def plot_quickcheck(cf):
    nFig = 0
    # get the netCDF filename
    ncfilename = pfp_io.get_infilenamefromcf(cf)
    # get the plot width and height
    PlotWidth_landscape = float(13)
    PlotHeight_landscape = float(8)
    PlotWidth_portrait = float(5)
    PlotHeight_portrait = float(8)
    # read the netCDF file and return the data structure "ds"
    logger.info(' Opening and reading netCDF file '+ncfilename)
    ds = pfp_io.nc_read_series(ncfilename)
    if len(ds.series.keys())==0: logger.error(' netCDF file '+ncfilename+' not found'); sys.exit()
    # get the time step
    ts = int(ds.globalattributes['time_step'])
    # get the site name
    SiteName = ds.globalattributes['site_name']
    # get the datetime series
    DateTime = ds.series['DateTime']['Data']
    # get the initial start and end dates
    StartDate = str(DateTime[0])
    EndDate = str(DateTime[-1])
    # find the start index of the first whole day (time=00:30)
    si = pfp_utils.GetDateIndex(DateTime,StartDate,ts=ts,default=0,match='startnextday')
    # find the end index of the last whole day (time=00:00)
    ei = pfp_utils.GetDateIndex(DateTime,EndDate,ts=ts,default=-1,match='endpreviousday')
    DateTime = DateTime[si:ei+1]
    PlotTitle = SiteName + ': ' + str(DateTime[0]) + ' to ' + str(DateTime[-1])
    # get the final start and end dates
    StartDate = str(DateTime[0])
    EndDate = str(DateTime[-1])
    # get the 30 minute data from the data structure
    logger.info(' Getting data from data structure ')
    #  radiation first ...
    Mnth_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Month'),si=si,ei=ei)
    Hour_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Hour'),si=si,ei=ei)
    Mnit_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Minute'),si=si,ei=ei)
    Fsd,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fsd'),si=si,ei=ei)
    if 'Fsd_syn' in ds.series.keys():
        Fsd_syn,flag,attr = pfp_utils.GetSeriesasMA(ds,'Fsd_syn',si=si,ei=ei)
        index = numpy.where(numpy.ma.getmaskarray(Fsd)==True)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(Fsd)==True)[0]
        Fsd[index] = Fsd_syn[index]
    night_mask = (Fsd<10)
    day_mask = (Fsd>=10)
    Fsd_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fsd'),si=si,ei=ei)
    Fsu_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fsu'),si=si,ei=ei)
    Fld_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fld'),si=si,ei=ei)
    Flu_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Flu'),si=si,ei=ei)
    Fn_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fn'),si=si,ei=ei)
    #  then fluxes ...
    Fg_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fg'),si=si,ei=ei)
    Fa2_30min = Fn_30min - Fg_30min
    Fa_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fa'),si=si,ei=ei)
    index = numpy.where((numpy.ma.getmaskarray(Fa_30min)==True)&(numpy.ma.getmaskarray(Fa2_30min)==False))[0]
    Fa_30min[index] = Fa2_30min[index]
    Fe_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fe'),si=si,ei=ei)
    Fh_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fh'),si=si,ei=ei)
    Fc_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Fc'),si=si,ei=ei)
    Fc_units = ds.series[pfp_utils.GetAltName(cf,ds,'Fc')]['Attr']['units']
    us_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'ustar'),si=si,ei=ei)
    #  then meteorology ...
    Ta_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Ta'),si=si,ei=ei)
    H2O_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'H2O'),si=si,ei=ei)
    H2O_units = ds.series[pfp_utils.GetAltName(cf,ds,'H2O')]['Attr']['units']
    CO2_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'CO2'),si=si,ei=ei)
    CO2_units = ds.series[pfp_utils.GetAltName(cf,ds,'CO2')]['Attr']['units']
    Rain_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Precip'),si=si,ei=ei)
    Ws_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Ws'),si=si,ei=ei)
    #  then soil ...
    Sws_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Sws'),si=si,ei=ei)
    Ts_30min,flag,attr = pfp_utils.GetSeriesasMA(ds,pfp_utils.GetAltName(cf,ds,'Ts'),si=si,ei=ei)

    # get the number of days in the data set
    ntsInDay = float(24.0*60.0/float(ts))
    if math.modf(ntsInDay)[0]!=0:
        print 'quickcheck: Time step is not a sub-multiple of 60 minutes ', ts
        sys.exit
    ntsInDay = int(ntsInDay)
    nDays = float(len(DateTime))/ntsInDay
    if math.modf(nDays)[0]!=0:
        print 'quickcheck: Not a whole number of days ', nDays
        sys.exit
    nDays = int(nDays)

    # *** start of section based on 30 minute data ***
    # scatter plot of (Fh+Fe) versys Fa, all data
    logger.info(' Doing surface energy balance plots ')
    mask = numpy.ma.mask_or(Fa_30min.mask,Fe_30min.mask)
    mask = numpy.ma.mask_or(mask,Fh_30min.mask)
    Fa_SEB = numpy.ma.array(Fa_30min,mask=mask)     # apply the mask
    FhpFe_SEB = numpy.ma.array(Fh_30min,mask=mask) + numpy.ma.array(Fe_30min,mask=mask)
    nFig = nFig + 1
    plt.ion()
    fig = plt.figure(nFig,figsize=(8,8))
    fig.canvas.set_window_title("Surface Energy Balance")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    xyplot(Fa_SEB,FhpFe_SEB,sub=[2,2,1],regr=1,title="All hours",xlabel='Fa (W/m2)',ylabel='Fh+Fe (W/m2)')
    # scatter plot of (Fh+Fe) versus Fa, 24 hour averages
    Fa_daily = Fa_30min.reshape(nDays,ntsInDay)
    Fe_daily = Fe_30min.reshape(nDays,ntsInDay)
    Fh_daily = Fh_30min.reshape(nDays,ntsInDay)
    mask = numpy.ma.mask_or(Fa_daily.mask,Fe_daily.mask)
    mask = numpy.ma.mask_or(mask,Fh_daily.mask)
    Fa_daily = numpy.ma.array(Fa_daily,mask=mask)         # apply the mask
    Fe_daily = numpy.ma.array(Fe_daily,mask=mask)
    Fh_daily = numpy.ma.array(Fh_daily,mask=mask)
    Fa_daily_avg = numpy.ma.average(Fa_daily,axis=1)      # get the daily average
    Fe_daily_avg = numpy.ma.average(Fe_daily,axis=1)
    Fh_daily_avg = numpy.ma.average(Fh_daily,axis=1)
    FhpFe_daily_avg = Fh_daily_avg + Fe_daily_avg
    xyplot(Fa_daily_avg,FhpFe_daily_avg,sub=[2,2,2],regr=1,thru0=1,title="Daily Average",xlabel='Fa (W/m2)',ylabel='Fh+Fe (W/m2)')
    # scatter plot of (Fh+Fe) versus Fa, day time
    Fa_day = numpy.ma.masked_where(day_mask==False,Fa_30min)
    Fe_day = numpy.ma.masked_where(day_mask==False,Fe_30min)
    Fh_day = numpy.ma.masked_where(day_mask==False,Fh_30min)
    mask = numpy.ma.mask_or(Fa_day.mask,Fe_day.mask)
    mask = numpy.ma.mask_or(mask,Fh_day.mask)
    Fa_day = numpy.ma.array(Fa_day,mask=mask)         # apply the mask
    Fe_day = numpy.ma.array(Fe_day,mask=mask)
    Fh_day = numpy.ma.array(Fh_day,mask=mask)
    FhpFe_day = Fh_day + Fe_day
    xyplot(Fa_day,FhpFe_day,sub=[2,2,3],regr=1,title="Day",xlabel='Fa (W/m2)',ylabel='Fh+Fe (W/m2)')
    # scatter plot of (Fh+Fe) versus Fa, night time
    Fa_night = numpy.ma.masked_where(night_mask==False,Fa_30min)
    Fe_night = numpy.ma.masked_where(night_mask==False,Fe_30min)
    Fh_night = numpy.ma.masked_where(night_mask==False,Fh_30min)
    mask = numpy.ma.mask_or(Fa_night.mask,Fe_night.mask)
    mask = numpy.ma.mask_or(mask,Fh_night.mask)
    Fa_night = numpy.ma.array(Fa_night,mask=mask)         # apply the mask
    Fe_night = numpy.ma.array(Fe_night,mask=mask)
    Fh_night = numpy.ma.array(Fh_night,mask=mask)
    FhpFe_night = Fh_night + Fe_night
    xyplot(Fa_night,FhpFe_night,sub=[2,2,4],regr=1,title="Night",xlabel='Fa (W/m2)',ylabel='Fh+Fe (W/m2)')
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'SEB_30minutes.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # *** start of section based on daily averages ***
    logger.info(' Getting daily averages from 30 minute data ')
    MTFmt = mdt.DateFormatter('%m/%Y')
    # reshape the 1D array of 30 minute data into a 2D array of (nDays,ntsInDay)
    DT_daily = DateTime[0::ntsInDay]
    Mnth_daily = Mnth_30min.reshape(nDays,ntsInDay)
    Hour_daily = Hour_30min.reshape(nDays,ntsInDay)
    Mnit_daily = Mnit_30min.reshape(nDays,ntsInDay)
    dm_daily = day_mask.reshape(nDays,ntsInDay)
    nm_daily = night_mask.reshape(nDays,ntsInDay)
    Fn_daily = Fn_30min.reshape(nDays,ntsInDay)
    Fa_daily = Fa_30min.reshape(nDays,ntsInDay)
    Fe_daily = Fe_30min.reshape(nDays,ntsInDay)
    Fh_daily = Fh_30min.reshape(nDays,ntsInDay)
    Fc_daily = Fc_30min.reshape(nDays,ntsInDay)
    Rain_daily = Rain_30min.reshape(nDays,ntsInDay)
    Sws_daily = Sws_30min.reshape(nDays,ntsInDay)
    Ts_daily = Ts_30min.reshape(nDays,ntsInDay)
    us_daily = us_30min.reshape(nDays,ntsInDay)

    # get the SEB ratio
    # get the daytime data, defined by Fsd>10 W/m2
    Fa_day = numpy.ma.masked_where(nm_daily==True,Fa_daily)
    Fe_day = numpy.ma.masked_where(nm_daily==True,Fe_daily)
    Fh_day = numpy.ma.masked_where(nm_daily==True,Fh_daily)
    mask = numpy.ma.mask_or(Fa_day.mask,Fe_day.mask)  # mask based on dependencies, set all to missing if any missing
    mask = numpy.ma.mask_or(mask,Fh_day.mask)
    Fa_day = numpy.ma.array(Fa_day,mask=mask)         # apply the mask
    Fe_day = numpy.ma.array(Fe_day,mask=mask)
    Fh_day = numpy.ma.array(Fh_day,mask=mask)
    Fa_day_avg = numpy.ma.average(Fa_day,axis=1)      # get the daily average
    Fe_day_avg = numpy.ma.average(Fe_day,axis=1)
    Fh_day_avg = numpy.ma.average(Fh_day,axis=1)      # get the number of values in the daily average
    SEB_day_num = numpy.ma.count(Fh_day,axis=1)       # get the SEB ratio
    SEB_day_avg = (Fe_day_avg+Fh_day_avg)/Fa_day_avg
    SEB_day_avg = numpy.ma.masked_where(SEB_day_num<=5,SEB_day_avg)
    index = numpy.where(numpy.ma.getmaskarray(SEB_day_avg)==True)[0]
    #index = numpy.ma.where(numpy.ma.getmaskarray(SEB_day_avg)==True)[0]
    SEB_day_num[index] = 0

    # get the EF
    # get the daytime data, defined by Fsd>10 W/m2
    Fa_day = numpy.ma.masked_where(nm_daily==True,Fa_daily)
    Fe_day = numpy.ma.masked_where(nm_daily==True,Fe_daily)
    mask = numpy.ma.mask_or(Fa_day.mask,Fe_day.mask)  # mask based on dependencies, set all to missing if any missing
    Fa_day = numpy.ma.array(Fa_day,mask=mask)         # apply the mask
    Fe_day = numpy.ma.array(Fe_day,mask=mask)
    Fa_day_avg = numpy.ma.average(Fa_day,axis=1)      # get the daily average
    Fe_day_avg = numpy.ma.average(Fe_day,axis=1)
    EF_day_num = numpy.ma.count(Fe_day,axis=1)        # get the number of values in the daily average
    EF_day_avg = Fe_day_avg/Fa_day_avg                # get the EF ratio
    EF_day_avg = numpy.ma.masked_where(EF_day_num<=5,EF_day_avg)
    index = numpy.where(numpy.ma.getmaskarray(EF_day_avg)==True)[0]
    #index = numpy.ma.where(numpy.ma.getmaskarray(EF_day_avg)==True)[0]
    EF_day_num[index] = 0

    # get the BR
    # get the daytime data, defined by Fsd>10 W/m2
    Fe_day = numpy.ma.masked_where(nm_daily==True,Fe_daily)
    Fh_day = numpy.ma.masked_where(nm_daily==True,Fh_daily)
    mask = numpy.ma.mask_or(Fe_day.mask,Fh_day.mask)  # mask based on dependencies, set all to missing if any missing
    Fe_day = numpy.ma.array(Fe_day,mask=mask)         # apply the mask
    Fh_day = numpy.ma.array(Fh_day,mask=mask)
    Fe_day_avg = numpy.ma.average(Fe_day,axis=1)      # get the daily average
    Fh_day_avg = numpy.ma.average(Fh_day,axis=1)
    BR_day_num = numpy.ma.count(Fh_day,axis=1)        # get the number of values in the daily average
    BR_day_avg = Fh_day_avg/Fe_day_avg                # get the BR ratio
    BR_day_avg = numpy.ma.masked_where(BR_day_num<=5,BR_day_avg)
    index = numpy.where(numpy.ma.getmaskarray(BR_day_avg)==True)[0]
    #index = numpy.ma.where(numpy.ma.getmaskarray(BR_day_avg)==True)[0]
    BR_day_num[index] = 0

    # get the Wue
    # get the daytime data, defined by Fsd>10 W/m2
    Fe_day = numpy.ma.masked_where(nm_daily==True,Fe_daily)
    Fc_day = numpy.ma.masked_where(nm_daily==True,Fc_daily)
    mask = numpy.ma.mask_or(Fe_day.mask,Fc_day.mask)  # mask based on dependencies, set all to missing if any missing
    Fe_day = numpy.ma.array(Fe_day,mask=mask)         # apply the mask
    Fc_day = numpy.ma.array(Fc_day,mask=mask)
    Fe_day_avg = numpy.ma.average(Fe_day,axis=1)      # get the daily average
    Fc_day_avg = numpy.ma.average(Fc_day,axis=1)
    WUE_day_num = numpy.ma.count(Fc_day,axis=1)       # get the number of values in the daily average
    WUE_day_avg = Fc_day_avg/Fe_day_avg
    WUE_day_avg = numpy.ma.masked_where(WUE_day_num<=5,WUE_day_avg)
    index = numpy.where(numpy.ma.getmaskarray(WUE_day_avg)==True)[0]
    #index = numpy.ma.where(numpy.ma.getmaskarray(WUE_day_avg)==True)[0]
    WUE_day_num[index] = 0
    # get the soil moisture
    Sws_daily_avg = numpy.ma.average(Sws_daily,axis=1)
    Sws_daily_num = numpy.ma.count(Sws_daily,axis=1)
    # get the rainfall
    Rain_daily_sum = numpy.ma.sum(Rain_daily,axis=1)
    Rain_daily_num = numpy.ma.count(Rain_daily,axis=1)
    # plot the SEB, EF and Wue
    logger.info(' Doing the daily ratios plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_landscape,PlotHeight_landscape))
    fig.canvas.set_window_title("Daily Average Ratios")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    tsplot(DT_daily,SEB_day_avg,sub=[6,1,1],colours=SEB_day_num,ylabel='(Fh+Fe)/Fa',lineat=1)
    tsplot(DT_daily,EF_day_avg,sub=[6,1,2],colours=EF_day_num,ylabel='EF=Fe/Fa')
    tsplot(DT_daily,BR_day_avg,sub=[6,1,3],colours=BR_day_num,ylabel='BR=Fh/Fe')
    tsplot(DT_daily,WUE_day_avg,sub=[6,1,4],colours=WUE_day_num,ylabel='WUE=Fc/Fe',lineat=0)
    tsplot(DT_daily,Sws_daily_avg,sub=[6,1,5],colours=Sws_daily_num,ylabel='Sws')
    tsplot(DT_daily,Rain_daily_sum,sub=[6,1,6],colours=Rain_daily_num,ylabel='Rain')
    #fig.show()
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DailyRatios.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # now we do the daily averages of the fluxes and the meteorology
    # get the 1D array of 30 minute data into a 2D array with a dimension for
    #  the day number and a dimension for the time of day
    Fsd_daily = Fsd_30min.reshape(nDays,ntsInDay)
    Fsu_daily = Fsu_30min.reshape(nDays,ntsInDay)
    Fld_daily = Fld_30min.reshape(nDays,ntsInDay)
    Flu_daily = Flu_30min.reshape(nDays,ntsInDay)
    Fn_daily = Fn_30min.reshape(nDays,ntsInDay)
    Fg_daily = Fg_30min.reshape(nDays,ntsInDay)
    Fsd_day = numpy.ma.masked_where(nm_daily==True,Fsd_daily)
    Fsu_day = numpy.ma.masked_where(nm_daily==True,Fsu_daily)
    Fld_day = numpy.ma.masked_where(nm_daily==True,Fld_daily)
    Flu_day = numpy.ma.masked_where(nm_daily==True,Flu_daily)
    Fn_day = numpy.ma.masked_where(nm_daily==True,Fn_daily)
    Fg_day = numpy.ma.masked_where(nm_daily==True,Fg_daily)
    Fsd_day_avg = numpy.ma.average(Fsd_day,axis=1)
    Fsu_day_avg = numpy.ma.average(Fsu_day,axis=1)
    Fld_day_avg = numpy.ma.average(Fld_day,axis=1)
    Flu_day_avg = numpy.ma.average(Flu_day,axis=1)
    Fn_day_avg = numpy.ma.average(Fn_day,axis=1)
    Fg_day_avg = numpy.ma.average(Fg_day,axis=1)
    Fsd_day_num = numpy.ma.count(Fsd_day,axis=1)
    Fsu_day_num = numpy.ma.count(Fsu_day,axis=1)
    Fld_day_num = numpy.ma.count(Fld_day,axis=1)
    Flu_day_num = numpy.ma.count(Flu_day,axis=1)
    Fn_day_num = numpy.ma.count(Fn_day,axis=1)
    Fg_day_num = numpy.ma.count(Fg_day,axis=1)
    logger.info(' Doing the daily radiation plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_landscape,PlotHeight_landscape))
    fig.canvas.set_window_title("Daily Average Radiation")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    tsplot(DT_daily,Fsd_day_avg,sub=[6,1,1],colours=Fsd_day_num,ylabel='Fsd (W/m2)')
    tsplot(DT_daily,Fsu_day_avg,sub=[6,1,2],colours=Fsu_day_num,ylabel='Fsu (W/m2)')
    tsplot(DT_daily,Fld_day_avg,sub=[6,1,3],colours=Fld_day_num,ylabel='Fld (W/m2)')
    tsplot(DT_daily,Flu_day_avg,sub=[6,1,4],colours=Flu_day_num,ylabel='Flu (W/m2)')
    tsplot(DT_daily,Fn_day_avg,sub=[6,1,5],colours=Fn_day_num,ylabel='Fn (W/m2)')
    tsplot(DT_daily,Fg_day_avg,sub=[6,1,6],colours=Fg_day_num,ylabel='Fg (W/m2)')
    #fig.show()
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DailyRadn.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    Fsd_daily = Fsd_30min.reshape(nDays,ntsInDay)
    Fa_daily = Fa_30min.reshape(nDays,ntsInDay)
    Fe_daily = Fe_30min.reshape(nDays,ntsInDay)
    Fh_daily = Fh_30min.reshape(nDays,ntsInDay)
    Fc_daily = Fc_30min.reshape(nDays,ntsInDay)
    # ... then get the day time values only (defined by Fsd>10 W/m2)
    Fsd_day = numpy.ma.masked_where(nm_daily==True,Fsd_daily)
    Fa_day = numpy.ma.masked_where(nm_daily==True,Fa_daily)
    Fe_day = numpy.ma.masked_where(nm_daily==True,Fe_daily)
    Fh_day = numpy.ma.masked_where(nm_daily==True,Fh_daily)
    Fc_day = numpy.ma.masked_where(nm_daily==True,Fc_daily)
    Fc_night = numpy.ma.masked_where(nm_daily==True,Fc_daily)
    # ... then get the daily averages
    Fsd_day_avg = numpy.ma.average(Fsd_day,axis=1)      # get the daily average
    Fa_day_avg = numpy.ma.average(Fa_day,axis=1)      # get the daily average
    Fe_day_avg = numpy.ma.average(Fe_day,axis=1)      # get the daily average
    Fh_day_avg = numpy.ma.average(Fh_day,axis=1)      # get the daily average
    Fc_day_avg = numpy.ma.average(Fc_day,axis=1)      # get the daily average
    Fc_night_avg = numpy.ma.average(Fc_night,axis=1)      # get the daily average
    # ... then the number of values in each day time block
    Fsd_day_num = numpy.ma.count(Fsd_day,axis=1)
    Fa_day_num = numpy.ma.count(Fa_day,axis=1)
    Fe_day_num = numpy.ma.count(Fe_day,axis=1)
    Fh_day_num = numpy.ma.count(Fh_day,axis=1)
    Fc_day_num = numpy.ma.count(Fc_day,axis=1)
    Fc_night_num = numpy.ma.count(Fc_night,axis=1)
    # ... now plot the day time averages with the colour of the points controlled
    #     by the number of values used to get the average
    logger.info(' Doing the daily fluxes plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_landscape,PlotHeight_landscape))
    fig.canvas.set_window_title("Daily Average Fluxes")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    tsplot(DT_daily,Fsd_day_avg,sub=[5,1,1],colours=Fsd_day_num,ylabel='Fsd (W/m2)')
    tsplot(DT_daily,Fa_day_avg,sub=[5,1,2],colours=Fa_day_num,ylabel='Fa (W/m2)')
    tsplot(DT_daily,Fe_day_avg,sub=[5,1,3],colours=Fe_day_num,ylabel='Fe (W/m2)')
    tsplot(DT_daily,Fh_day_avg,sub=[5,1,4],colours=Fh_day_num,ylabel='Fh (W/m2)')
    tsplot(DT_daily,Fc_day_avg,sub=[5,1,5],colours=Fc_day_num,ylabel='Fc ('+Fc_units+')',lineat=0)
    #fig.show()
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DailyFluxes.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    Ta_daily = Ta_30min.reshape(nDays,ntsInDay)
    H2O_daily = H2O_30min.reshape(nDays,ntsInDay)
    CO2_daily = CO2_30min.reshape(nDays,ntsInDay)
    Ws_daily = Ws_30min.reshape(nDays,ntsInDay)
    CO2_day = numpy.ma.masked_where(nm_daily==True,CO2_daily)
    Ta_daily_avg = numpy.ma.average(Ta_daily,axis=1)      # get the daily average
    Ta_daily_num = numpy.ma.count(Ta_daily,axis=1)
    H2O_daily_avg = numpy.ma.average(H2O_daily,axis=1)      # get the daily average
    H2O_daily_num = numpy.ma.count(H2O_daily,axis=1)
    CO2_day_avg = numpy.ma.average(CO2_day,axis=1)          # get the daily average
    CO2_day_num = numpy.ma.count(CO2_day,axis=1)
    Ws_daily_avg = numpy.ma.average(Ws_daily,axis=1)      # get the daily average
    Ws_daily_num = numpy.ma.count(Ws_daily,axis=1)
    logger.info(' Doing the daily meteorology plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_landscape,PlotHeight_landscape))
    fig.canvas.set_window_title("Daily Average Meteorology")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    tsplot(DT_daily,Ta_daily_avg,sub=[5,1,1],colours=Ta_daily_num,ylabel='Ta (C)')
    tsplot(DT_daily,H2O_daily_avg,sub=[5,1,2],colours=H2O_daily_num,ylabel='H2O ('+H2O_units+')')
    tsplot(DT_daily,CO2_day_avg,sub=[5,1,3],colours=CO2_day_num,ylabel='CO2 ('+CO2_units+')')
    tsplot(DT_daily,Ws_daily_avg,sub=[5,1,4],colours=Ws_daily_num,ylabel='WS (m/s)')
    tsplot(DT_daily,Rain_daily_sum,sub=[5,1,5],colours=Rain_daily_num,ylabel='Rain (mm)')
    #fig.show()
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DailyMet.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    Ta_daily = Ta_30min.reshape(nDays,ntsInDay)
    Ts_daily = Ts_30min.reshape(nDays,ntsInDay)
    Sws_daily = Sws_30min.reshape(nDays,ntsInDay)
    Fg_daily = Fg_30min.reshape(nDays,ntsInDay)
    Rain_daily = Rain_30min.reshape(nDays,ntsInDay)
    Ta_daily_avg = numpy.ma.average(Ta_daily,axis=1)      # get the daily average
    Ta_daily_num = numpy.ma.count(Ta_daily,axis=1)
    Ts_daily_avg = numpy.ma.average(Ts_daily,axis=1)      # get the daily average
    Ts_daily_num = numpy.ma.count(Ts_daily,axis=1)
    Sws_day_avg = numpy.ma.average(Sws_daily,axis=1)          # get the daily average
    Sws_day_num = numpy.ma.count(Sws_daily,axis=1)
    Fg_daily_avg = numpy.ma.average(Fg_daily,axis=1)      # get the daily average
    Fg_daily_num = numpy.ma.count(Fg_daily,axis=1)
    Fg_daily_avg = numpy.ma.average(Fg_daily,axis=1)      # get the daily average
    Rain_daily_sum = numpy.ma.sum(Rain_daily,axis=1)
    Rain_daily_num = numpy.ma.count(Rain_daily,axis=1)
    logger.info(' Doing the daily soil data plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_landscape,PlotHeight_landscape))
    fig.canvas.set_window_title("Daily Average Soil")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    tsplot(DT_daily,Ta_daily_avg,sub=[5,1,1],colours=Ta_daily_num,ylabel='Ta (C)')
    tsplot(DT_daily,Ts_daily_avg,sub=[5,1,2],colours=Ts_daily_num,ylabel='Ts (C)')
    tsplot(DT_daily,Sws_day_avg,sub=[5,1,3],colours=Sws_day_num,ylabel='Sws (frac)')
    tsplot(DT_daily,Fg_daily_avg,sub=[5,1,4],colours=Fg_daily_num,ylabel='Fg (W/m2)')
    tsplot(DT_daily,Rain_daily_sum,sub=[5,1,5],colours=Rain_daily_num,ylabel='Rain (mm)')
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DailySoil.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # *** end of section for time series of daily averages
    # *** start of section for diurnal plots by month ***
    MnthList = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    # plot Fsd
    logger.info(' Doing the diurnal Fsd by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Fsd")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Fsd_hr_avg = numpy.ma.average(Fsd_daily[index],axis=0)
            Fsd_hr_num = numpy.ma.count(Fsd_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Fsd (W/m2)'
            hrplot(hr[0],Fsd_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fsd_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalFsdByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # plot Fa
    logger.info(' Doing the diurnal Fa by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Fa")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Fa_hr_avg = numpy.ma.average(Fa_daily[index],axis=0)
            Fa_hr_num = numpy.ma.count(Fa_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Fa (W/m2)'
            hrplot(hr[0],Fa_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fa_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalFaByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # plot Fn
    logger.info(' Doing the diurnal Fn by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Fn")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Fn_hr_avg = numpy.ma.average(Fn_daily[index],axis=0)
            Fn_hr_num = numpy.ma.count(Fn_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Fn (W/m2)'
            hrplot(hr[0],Fn_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fn_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalFnByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # plot Fg
    logger.info(' Doing the diurnal Fg by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Fg")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Fg_hr_avg = numpy.ma.average(Fg_daily[index],axis=0)
            Fg_hr_num = numpy.ma.count(Fg_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Fg (W/m2)'
            hrplot(hr[0],Fg_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fg_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalFgByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # plot Ts
    logger.info(' Doing the diurnal Ts by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Ts")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Ts_hr_avg = numpy.ma.average(Ts_daily[index],axis=0)
            Ts_hr_num = numpy.ma.count(Ts_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Ts (C)'
            hrplot(hr[0],Ts_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fg_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalTsByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # plot Fh
    logger.info(' Doing the diurnal Fh by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Fh")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Fh_hr_avg = numpy.ma.average(Fh_daily[index],axis=0)
            Fh_hr_num = numpy.ma.count(Fh_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Fh (W/m2)'
            hrplot(hr[0],Fh_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fh_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalFhByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # plot Fe
    logger.info(' Doing the diurnal Fe by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Fe")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Fe_hr_avg = numpy.ma.average(Fe_daily[index],axis=0)
            Fe_hr_num = numpy.ma.count(Fe_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Fe (W/m2)'
            hrplot(hr[0],Fe_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fe_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalFeByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()
    # plot Fc
    logger.info(' Doing the diurnal Fc by month plot ')
    nFig = nFig + 1
    fig = plt.figure(nFig,figsize=(PlotWidth_portrait,PlotHeight_portrait))
    fig.canvas.set_window_title("Diurnal Fc")
    plt.figtext(0.5,0.95,PlotTitle,horizontalalignment='center',size=16)
    j = 0
    for i in [12,1,2,3,4,5,6,7,8,9,10,11]:
        j = j + 1
        index = numpy.where(Mnth_daily==i)[0]
        if len(index)!=0:
            hr = Hour_daily[index]+Mnit_daily[index]/float(60)
            Fc_hr_avg = numpy.ma.average(Fc_daily[index],axis=0)
            Fc_hr_num = numpy.ma.count(Fc_daily[index],axis=0)
            if j in [1,2,3,4,5,6,7,8,9]:
                xlabel = None
            else:
                xlabel = 'Hour'
            if j in [2,3,5,6,8,9,11,12]:
                ylabel = None
            else:
                ylabel = 'Fc ('+Fc_units+')'
            hrplot(hr[0],Fc_hr_avg,sub=[4,3,j],
                   title=MnthList[i-1],xlabel=xlabel,ylabel=ylabel,
                   colours=Fc_hr_num)
    # save the plot to file
    figname='plots/'+ds.globalattributes['site_name'].replace(' ','')+'_'+ds.globalattributes['nc_level']+'_QC_'+'DiurnalFcByMonth.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    plt.draw()

def plot_setup(cf, title):
    p = {}
    if "plot_path" in cf["Files"]:
        p["plot_path"] = os.path.join(cf["Files"]["plot_path"], cf["level"])
    else:
        p["plot_path"] = os.path.join("plots", cf["level"])
    p['PlotDescription'] = str(title)
    #p['SeriesList'] = ast.literal_eval(cf['Plots'][str(nFig)]['Variables'])
    if "," in cf['Plots'][str(title)]['Variables']:
        var_string = cf['Plots'][str(title)]['Variables']
        p['SeriesList'] = var_string.split(",")
    else:
        p['SeriesList'] = [var_string]
    p['nGraphs'] = len(p['SeriesList'])
    p['PlotWidth'] = 13
    p['PlotHeight'] = 8
    p['ts_YAxOrg'] = 0.08
    p['ts_XAxOrg'] = 0.06
    p['ts_XAxLen'] = 0.6
    p['hr_XAxLen'] = 0.1
    p['ts_YAxLen'] = (0.85 - (p['nGraphs'] - 1)*0.02)/p['nGraphs']
    if p['nGraphs']==1:
        p['yaxOrgOffset'] = (0.85 - p['ts_YAxLen'])
    else:
        p['yaxOrgOffset'] = (0.85 - p['ts_YAxLen'])/(p['nGraphs'] - 1)
    p['hr1_XAxOrg'] = p['ts_XAxOrg']+p['ts_XAxLen']+0.07
    p['hr1_XAxLen'] = p['hr_XAxLen']
    p['hr2_XAxOrg'] = p['hr1_XAxOrg']+p['hr1_XAxLen']+0.05
    p['hr2_XAxLen'] = p['hr_XAxLen']
    p['bar_XAxOrg'] = p['hr1_XAxOrg']+p['hr1_XAxLen']+0.05+p['hr1_XAxLen']+0.05
    p['bar_XAxLen'] = p['hr_XAxLen']
    p['ts_ax_left'] = [None]*p["nGraphs"]
    p['ts_ax_right'] = [None]*p["nGraphs"]
    return p

def plot_onetimeseries_left(fig,n,ThisOne,xarray,yarray,p):
    """
    Purpose:
     Plots a single time series graph with labelling on the left y axis.
    Usage:
     pfp_plot.plot_onetimeseries_left(fig,n,ThisOne,XArray,YArray,p)
      where fig     is a matplotlib figure instance
            n       is the number of this graph
            ThisOne is the series label
            XArray  is a numpy ndarray or masked array of X data (usually datetime)
            YArray  is a numpy ndarray or masked array of Y data
            p       is a dictionary of plot data (created using pfp_plot.plot_setup)
    Side effects:
     Creates a matplotlib plot of time series, diurnal variation and flag statistics.
    Author: PRI
    Date: Sometime
    """
    # check to see if this is the first graph
    if n==0:
        # if so, define the X axis
        rect = [p['ts_XAxOrg'],p['YAxOrg'],p['ts_XAxLen'],p['ts_YAxLen']]
        ts_ax_left = fig.add_axes(rect)
    else:
        # if not, then use an existing axis
        rect = [p['ts_XAxOrg'],p['YAxOrg'],p['ts_XAxLen'],p['ts_YAxLen']]
        if p["ts_ax_left"][0] is not None:
            # a left axis was defined for the first graph, use it
            ts_ax_left = fig.add_axes(rect,sharex=p["ts_ax_left"][0])
        else:
            # a right axis was defined for the first graph, use it
            ts_ax_left = fig.add_axes(rect,sharex=p["ts_ax_right"][0])
    # let the axes change
    #ts_ax_left.hold(False)
    # put this axis in the plot setup dictionary
    p["ts_ax_left"][n] = ts_ax_left
    # plot the data on this axis
    ts_ax_left.plot(xarray,yarray,'b-')
    # set the major tick marks on the X (datetime) axis
    ts_ax_left.xaxis.set_major_locator(p['loc'])
    ts_ax_left.xaxis.set_major_formatter(p['fmt'])
    # set the axes limits
    ts_ax_left.set_xlim(p['XAxMin'],p['XAxMax'])
    ts_ax_left.set_ylim(p['LYAxMin'],p['LYAxMax'])
    # check to see if this is the first graph
    if n==0:
        # if it is, label the X axis
        ts_ax_left.set_xlabel('Date',visible=True)
    else:
        # if it isnt, hide the X axis labels
        ts_ax_left.set_xlabel('',visible=False)
    # now put a text string on the graph with the series plotted, units, number in series,
    # number not masked (data OK) and number masked (data not OK)
    TextStr = ThisOne+'('+p['Units']+')'+str(p['nRecs'])+' '+str(p['nNotM'])+' '+str(p['nMskd'])
    txtXLoc = p['ts_XAxOrg']+0.01
    txtYLoc = p['YAxOrg']+p['ts_YAxLen']-0.025
    plt.figtext(txtXLoc,txtYLoc,TextStr,color='b',horizontalalignment='left')
    if n > 0: plt.setp(ts_ax_left.get_xticklabels(),visible=False)

def plot_onetimeseries_right(fig,n,ThisOne,xarray,yarray,p):
    if p["ts_ax_left"][n] is not None:
        ts_ax_right = p["ts_ax_left"][n].twinx()
    else:
        rect = [p['ts_XAxOrg'],p['YAxOrg'],p['ts_XAxLen'],p['ts_YAxLen']]
        if p["ts_ax_left"][0] is not None:
            # a left axis was defined for the first graph, use it
            ts_ax_right = fig.add_axes(rect,sharex=p["ts_ax_left"][0])
        else:
            # a right axis was defined for the first graph, use it
            ts_ax_right = fig.add_axes(rect,sharex=p["ts_ax_right"][0])
        #ts_ax_right.hold(False)
        ts_ax_right.yaxis.tick_right()
        TextStr = ThisOne+'('+p['Units']+')'
        txtXLoc = p['ts_XAxOrg']+0.01
        txtYLoc = p['YAxOrg']+p['ts_YAxLen']-0.025
        plt.figtext(txtXLoc,txtYLoc,TextStr,color='b',horizontalalignment='left')
    colour = 'r'
    p["ts_ax_right"][n] = ts_ax_right
    ts_ax_right.plot(xarray,yarray,'r-')
    ts_ax_right.xaxis.set_major_locator(p['loc'])
    ts_ax_right.xaxis.set_major_formatter(p['fmt'])
    ts_ax_right.set_xlim(p['XAxMin'],p['XAxMax'])
    ts_ax_right.set_ylim(p['RYAxMin'],p['RYAxMax'])
    if n==0:
        ts_ax_right.set_xlabel('Date',visible=True)
    else:
        ts_ax_right.set_xlabel('',visible=False)
    TextStr = str(p['nNotM'])+' '+str(p['nMskd'])
    txtXLoc = p['ts_XAxOrg']+p['ts_XAxLen']-0.01
    txtYLoc = p['YAxOrg']+p['ts_YAxLen']-0.025
    plt.figtext(txtXLoc,txtYLoc,TextStr,color='r',horizontalalignment='right')
    if n > 0: plt.setp(ts_ax_right.get_xticklabels(),visible=False)

def plotxy(cf, title, plt_cf, dsa, dsb):
    SiteName = dsa.globalattributes['site_name']
    PlotDescription = str(title)
    fig = plt.figure()
    fig.clf()
    fig.canvas.set_window_title(PlotDescription)
    plt.figtext(0.5,0.95,SiteName+': '+PlotDescription,ha='center',size=16)
    #XSeries = ast.literal_eval(plt_cf['XSeries'])
    #YSeries = ast.literal_eval(plt_cf['YSeries'])
    if "," in plt_cf['XSeries']:
        XSeries = plt_cf['XSeries'].split(",")
    else:
        XSeries = [plt_cf['XSeries']]
    if "," in plt_cf['YSeries']:
        YSeries = plt_cf['YSeries'].split(",")
    else:
        YSeries = [plt_cf['YSeries']]
    logger.info(' Plotting xy: '+str(XSeries)+' v '+str(YSeries))
    if dsa == dsb:
        for xname,yname in zip(XSeries,YSeries):
            xa,flag,attr = pfp_utils.GetSeriesasMA(dsa,xname)
            ya,flag,attr = pfp_utils.GetSeriesasMA(dsa,yname)
            xyplot(xa,ya,sub=[1,1,1],regr=1,xlabel=xname,ylabel=yname)
    else:
        for xname,yname in zip(XSeries,YSeries):
            xa,flag,attr = pfp_utils.GetSeriesasMA(dsa,xname)
            ya,flag,attr = pfp_utils.GetSeriesasMA(dsa,yname)
            xb,flag,attr = pfp_utils.GetSeriesasMA(dsb,xname)
            yb,flag,attr = pfp_utils.GetSeriesasMA(dsb,yname)
            xyplot(xa,ya,sub=[1,2,1],xlabel=xname,ylabel=yname)
            xyplot(xb,yb,sub=[1,2,2],regr=1,xlabel=xname,ylabel=yname)
    fig.show()

def xyplot(x,y,sub=[1,1,1],regr=0,thru0=0,title=None,xlabel=None,ylabel=None,fname=None):
    '''Generic XY scatter plot routine'''
    wspace = 0.0
    hspace = 0.0
    plt.subplot(sub[0],sub[1],sub[2])
    plt.plot(x,y,'b.')
    ax = plt.gca()
    if xlabel is not None:
        plt.xlabel(xlabel)
        hspace = 0.3
    if ylabel is not None:
        plt.ylabel(ylabel)
        wspace = 0.3
    if title is not None:
        plt.title(title)
        hspace = 0.3
    if regr==1:
        coefs = numpy.ma.polyfit(numpy.ma.copy(x),numpy.ma.copy(y),1)
        xfit = numpy.ma.array([numpy.ma.minimum(x),numpy.ma.maximum(x)])
        yfit = numpy.polyval(coefs,xfit)
        r = numpy.ma.corrcoef(x,y)
        eqnstr = 'y = %.3fx + %.3f (OLS)'%(coefs[0],coefs[1])
        plt.plot(xfit,yfit,'r--',linewidth=3)
        plt.text(0.5,0.93,eqnstr,fontsize=8,horizontalalignment='center',transform=ax.transAxes)
        eqnstr = 'r = %.3f'%(r[0][1])
        plt.text(0.5,0.89,eqnstr,fontsize=8,horizontalalignment='center',transform=ax.transAxes)
    elif regr==2:
        mask = (x.mask)|(y.mask)
        x.mask = mask
        y.mask = mask
        x_nm = numpy.ma.compressed(x)
        x_nm = sm.add_constant(x_nm,prepend=False)
        y_nm = numpy.ma.compressed(y)
        if len(y_nm)!=0 or len(x_nm)!=0:
            resrlm = sm.RLM(y_nm,x_nm,M=sm.robust.norms.TukeyBiweight()).fit()
            if numpy.isnan(resrlm.params[0]):
                resrlm = sm.RLM(y_nm,x_nm,M=sm.robust.norms.TrimmedMean()).fit()
            r = numpy.corrcoef(numpy.ma.compressed(x),numpy.ma.compressed(y))
            eqnstr = 'y = %.3fx + %.3f (RLM)'%(resrlm.params[0],resrlm.params[1])
            plt.plot(x_nm[:,0],resrlm.fittedvalues,'r--',linewidth=3)
            plt.text(0.5,0.93,eqnstr,fontsize=8,horizontalalignment='center',transform=ax.transAxes)
            eqnstr = 'r = %.3f'%(r[0][1])
            plt.text(0.5,0.89,eqnstr,fontsize=8,horizontalalignment='center',transform=ax.transAxes)
        else:
            logger.info("xyplot: nothing to plot!")
    if thru0!=0:
        x = x[:,numpy.newaxis]
        a, _, _, _ = numpy.linalg.lstsq(x, y)
        eqnstr = 'y = %.3fx'%(a)
        plt.text(0.5,0.875,eqnstr,fontsize=8,horizontalalignment='center',transform=ax.transAxes)
    plt.subplots_adjust(wspace=wspace,hspace=hspace)

def hrplot(x,y,sub=[1,1,1],title=None,xlabel=None,ylabel=None,colours=None):
    plt.subplot(sub[0],sub[1],sub[2])
    if (y.all() is numpy.ma.masked):
        y = numpy.ma.zeros(len(y))
    if colours is not None:
        plt.scatter(x,y,c=colours)
    else:
        plt.scatter(x,y)
    plt.xlim(0,24)
    plt.xticks([0,6,12,18,24])
    if title is not None:
        plt.title(title)
    if ylabel is not None:
        plt.ylabel(ylabel)
    if xlabel is not None:
        plt.xlabel(xlabel)

def tsplot(x,y,sub=[1,1,1],title=None,xlabel=None,ylabel=None,colours=None,lineat=None):
    plt.subplot(sub[0],sub[1],sub[2])
    MTFmt = mdt.DateFormatter('%d/%m')
    if (y.all() is numpy.ma.masked):
        y = numpy.ma.zeros(len(y))
    if colours is not None:
        plt.scatter(x,y,c=colours)
    else:
        plt.scatter(x,y)
    if lineat is not None:
        plt.plot((x[0],x[-1]),(float(lineat),float(lineat)))
    plt.xlim((x[0],x[-1]))
    ax = plt.gca()
    ax.xaxis.set_major_formatter(MTFmt)
    if title is not None:
        plt.title(title)
    if ylabel is not None:
        ax.yaxis.set_label_text(ylabel)
    if xlabel is not None:
        ax.xaxis.set_label_text(xlabel)
