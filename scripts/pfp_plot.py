import ast
import constants as c
import datetime
import time
import math
import matplotlib
import matplotlib.dates as mdt
import matplotlib.pyplot as plt
import meteorologicalfunctions as pfp_mf
import numpy
import os
from scipy import stats
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

def plot_fcvsustar(ds):
    """
    Purpose:
     Plots Fc versus u* for each year and for each season
     (summer=DJF, autumn=MAM, winter=JJA, spring=SON) in
     each year.
    """
    site_name = ds.globalattributes["site_name"]
    nrecs = int(ds.globalattributes["nc_nrecs"])
    ts = int(ds.globalattributes["time_step"])
    ldt = pfp_utils.GetVariable(ds, "DateTime")
    nbins = 20
    # plot each year
    plt.ion()
    start_year = ldt["Data"][0].year
    end_year = ldt["Data"][-1].year
    logger.info(" Doing annual Fc versus u* plots")
    for year in range(start_year, end_year+1):
        # get the start and end datetimes
        start = datetime.datetime(year, 1, 1, 0, 30, 0)
        end = datetime.datetime(year+1, 1, 1, 0, 0, 0)
        # get the variables from the data structure
        Fc = pfp_utils.GetVariable(ds, "Fc", start=start, end=end)
        Fsd = pfp_utils.GetVariable(ds, "Fsd", start=start, end=end)
        ustar = pfp_utils.GetVariable(ds, "ustar", start=start, end=end)
        # get the observations and night time filters
        obs = (Fc["Flag"] == 0) & (ustar["Flag"] == 0)
        night = (Fsd["Data"] <= 10)
        obs_night_filter = obs & night
        # mask anything that is not an observation and at night
        ustar["Data"] = numpy.ma.masked_where(obs_night_filter == False, ustar["Data"])
        Fc["Data"] = numpy.ma.masked_where(obs_night_filter == False, Fc["Data"])
        # get mask when either ustar or Fc masked
        mask = numpy.ma.mask_or(numpy.ma.getmaskarray(ustar["Data"]), numpy.ma.getmaskarray(Fc["Data"]))
        # apply mask
        ustar["Data"] = numpy.ma.masked_where(mask == True, ustar["Data"])
        Fc["Data"] = numpy.ma.masked_where(mask == True, Fc["Data"])
        # remove masked elements
        ustar["Data"] = numpy.ma.compressed(ustar["Data"])
        Fc["Data"] = numpy.ma.compressed(Fc["Data"])
        # get the binned statistics
        count, edges, numbers = stats.binned_statistic(ustar["Data"],Fc["Data"], statistic='count', bins=nbins)
        means, edges, numbers = stats.binned_statistic(ustar["Data"],Fc["Data"], statistic='mean', bins=nbins)
        stdevs, edges, numbers = stats.binned_statistic(ustar["Data"],Fc["Data"], statistic='std', bins=nbins)
        mids = (edges[:-1]+edges[1:])/2
        # drop bins with less than 10 counts
        mids = numpy.array(mids[count >= 10])
        means = numpy.array(means[count >= 10])
        stdevs = numpy.array(stdevs[count >= 10])
        # do the plot
        fig = plt.figure()
        fig.canvas.set_window_title("Fc versus u*: "+str(year))
        plt.plot(ustar["Data"], Fc["Data"], 'b.', alpha=0.25)
        plt.errorbar(mids, means, yerr=stdevs, fmt='ro')
        plt.xlabel("u* ("+ustar["Attr"]["units"]+")")
        plt.ylabel("Fc ("+Fc["Attr"]["units"]+")")
        plt.title(site_name+": "+str(year))
        plt.draw()
    # plot 4 seasons for each year
    logger.info(" Doing seasonal Fc versus u* plots")
    seasons = {"summer":[12, 1, 2], "autumn":[3, 4, 5], "winter":[6, 7, 8], "spring":[9, 10, 11]}
    nrows = 2
    ncols = 2
    for year in range(start_year, end_year+1):
        fig, axs = plt.subplots(nrows=nrows, ncols=ncols)
        fig.canvas.set_window_title("Fc versus u*: "+str(year))
        for n, season in enumerate(["Summer", "Autumn", "Winter", "Spring"]):
            col = numpy.mod(n, ncols)
            row = n/ncols
            if season == "Summer":
                start = datetime.datetime(year-1, 12, 1, 0, 0, 0) + datetime.timedelta(minutes=ts)
                end = datetime.datetime(year, 3, 1, 0, 0, 0)
            elif season == "Autumn":
                start = datetime.datetime(year, 3, 1, 0, 0, 0) + datetime.timedelta(minutes=ts)
                end = datetime.datetime(year, 6, 1, 0, 0, 0)
            elif season == "Winter":
                start = datetime.datetime(year, 6, 1, 0, 0, 0) + datetime.timedelta(minutes=ts)
                end = datetime.datetime(year, 9, 1, 0, 0, 0)
            elif season == "Spring":
                start = datetime.datetime(year, 9, 1, 0, 0, 0) + datetime.timedelta(minutes=ts)
                end = datetime.datetime(year, 12, 1, 0, 0, 0)
            if end < ldt["Data"][0] or start > ldt["Data"][-1]:
                fig.delaxes(axs[row, col])
                continue
            # get the variables from the data structure
            Fc = pfp_utils.GetVariable(ds, "Fc", start=start, end=end)
            Fsd = pfp_utils.GetVariable(ds, "Fsd", start=start, end=end)
            ustar = pfp_utils.GetVariable(ds, "ustar", start=start, end=end)
            # get the observations and night time filters
            obs = (Fc["Flag"] == 0) & (ustar["Flag"] == 0)
            night = (Fsd["Data"] <= 10)
            obs_night_filter = obs & night
            # mask anything that is not an observation and at night
            ustar["Data"] = numpy.ma.masked_where(obs_night_filter == False, ustar["Data"])
            Fc["Data"] = numpy.ma.masked_where(obs_night_filter == False, Fc["Data"])
            # get mask when either ustar or Fc masked
            mask = numpy.ma.mask_or(numpy.ma.getmaskarray(ustar["Data"]), numpy.ma.getmaskarray(Fc["Data"]))
            # apply mask
            ustar["Data"] = numpy.ma.masked_where(mask == True, ustar["Data"])
            Fc["Data"] = numpy.ma.masked_where(mask == True, Fc["Data"])
            # remove masked elements
            ustar["Data"] = numpy.ma.compressed(ustar["Data"])
            Fc["Data"] = numpy.ma.compressed(Fc["Data"])
            # get the binned statistics
            count, edges, numbers = stats.binned_statistic(ustar["Data"],Fc["Data"], statistic='count', bins=nbins)
            means, edges, numbers = stats.binned_statistic(ustar["Data"],Fc["Data"], statistic='mean', bins=nbins)
            stdevs, edges, numbers = stats.binned_statistic(ustar["Data"],Fc["Data"], statistic='std', bins=nbins)
            mids = (edges[:-1]+edges[1:])/2
            # drop bins with less than 10 counts
            mids = numpy.array(mids[count >= 10])
            means = numpy.array(means[count >= 10])
            stdevs = numpy.array(stdevs[count >= 10])
            axs[row, col].plot(ustar["Data"], Fc["Data"], 'b.', alpha=0.25)
            axs[row, col].errorbar(mids, means, yerr=stdevs, fmt='ro')
            axs[row, col].set_title(site_name+": "+str(year)+" "+season)
            axs[row, col].set_xlabel("u* ("+ustar["Attr"]["units"]+")")
            axs[row, col].set_ylabel("Fc ("+Fc["Attr"]["units"]+")")
        fig.tight_layout()
        plt.draw()
    plt.ioff()
    return

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
            mypause(0.5)
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
        RH = pfp_mf.RHfromabsolutehumidity(Ah, Ta)
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
    L1XArray = dsa.series['DateTime']['Data']
    L2XArray = dsb.series['DateTime']['Data']
    p['XAxMin'] = min(L2XArray)
    p['XAxMax'] = max(L2XArray)
    p['loc'],p['fmt'] = get_ticks(p['XAxMin'],p['XAxMax'])
    plt.ion()
    # check to see if a figure with the same title already exists
    fig_titles = []
    # get a list of figure titles
    for i in plt.get_fignums():
        # get the figure
        figa = plt.figure(i)
        # get the figure title
        fig_title = figa.texts[0].get_text()
        # strip out the site name
        idx = fig_title.index(":")
        # and append to the figure title list
        fig_titles.append(fig_title[idx+2:])
    # check to see if a figure with the same title already exists
    if p['PlotDescription'] in fig_titles:
        # if it does, get the figure number (figure numbers start from 1)
        fig_num = fig_titles.index(p['PlotDescription']) + 1
        # get the figure
        fig = plt.figure(fig_num)
        # clear the figure (we should only update axes, not the whole figure)
        fig.clf()
    else:
        # create the figure if it doesn't already exist
        fig = plt.figure(figsize=(p['PlotWidth'],p['PlotHeight']))
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
                    NSdarr = numpy.array(pfp_ck.parse_rangecheck_limit(cf[section][ThisOne]['DiurnalCheck']['NumSd']))
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
    #fig.show()
    plt.draw()
    mypause(0.5)
    if "plot_path" in cf["Files"]:
        plot_path = os.path.join(cf["Files"]["plot_path"],Level)
    else:
        plot_path = "plots/"
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
    fname = os.path.join(plot_path, SiteName.replace(' ','')+'_'+Level+'_'+p['PlotDescription'].replace(' ','')+'.png')
    fig.savefig(fname,format='png')

def plot_quickcheck_seb(nFig, plot_title, figure_name, data, daily):
    logger.info(" Doing surface energy balance plots")
    Fa_30min = data["Fa"]["Data"]
    Fh_30min = data["Fh"]["Data"]
    Fe_30min = data["Fe"]["Data"]
    mask = numpy.ma.mask_or(Fa_30min.mask, Fe_30min.mask)
    mask = numpy.ma.mask_or(mask, Fh_30min.mask)
    Fa_SEB = numpy.ma.array(Fa_30min, mask=mask)     # apply the mask
    FhpFe_SEB = numpy.ma.array(Fh_30min, mask=mask) + numpy.ma.array(Fe_30min, mask=mask)
    plt.ion()
    fig = plt.figure(nFig, figsize=(8, 8))
    fig.canvas.set_window_title("Surface Energy Balance")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment='center', size=16)
    xyplot(Fa_SEB, FhpFe_SEB, sub=[2,2,1], regr=1, title="All hours", xlabel='Fa (W/m2)', ylabel='Fh+Fe (W/m2)')
    # scatter plot of (Fh+Fe) versus Fa, 24 hour averages
    mask = numpy.ma.mask_or(daily["Fa"]["Data"].mask, daily["Fe"]["Data"].mask)
    mask = numpy.ma.mask_or(mask, daily["Fh"]["Data"].mask)
    Fa_daily = numpy.ma.array(daily["Fa"]["Data"], mask=mask)         # apply the mask
    Fe_daily = numpy.ma.array(daily["Fe"]["Data"], mask=mask)
    Fh_daily = numpy.ma.array(daily["Fh"]["Data"], mask=mask)
    Fa_daily_avg = numpy.ma.average(Fa_daily, axis=1)      # get the daily average
    Fe_daily_avg = numpy.ma.average(Fe_daily, axis=1)
    Fh_daily_avg = numpy.ma.average(Fh_daily, axis=1)
    FhpFe_daily_avg = Fh_daily_avg + Fe_daily_avg
    xyplot(Fa_daily_avg, FhpFe_daily_avg, sub=[2,2,2], regr=1, thru0=1,
           title="Daily Average", xlabel="Fa (W/m2)", ylabel="Fh+Fe (W/m2)")
    # scatter plot of (Fh+Fe) versus Fa, day time
    day_mask = (data["Fsd"]["Data"] >= 10)
    Fa_day = numpy.ma.masked_where(day_mask == False, Fa_30min)
    Fe_day = numpy.ma.masked_where(day_mask == False, Fe_30min)
    Fh_day = numpy.ma.masked_where(day_mask == False, Fh_30min)
    mask = numpy.ma.mask_or(Fa_day.mask, Fe_day.mask)
    mask = numpy.ma.mask_or(mask, Fh_day.mask)
    Fa_day = numpy.ma.array(Fa_day, mask=mask)         # apply the mask
    Fe_day = numpy.ma.array(Fe_day, mask=mask)
    Fh_day = numpy.ma.array(Fh_day, mask=mask)
    FhpFe_day = Fh_day + Fe_day
    xyplot(Fa_day, FhpFe_day, sub=[2,2,3], regr=1, title="Day", xlabel="Fa (W/m2)", ylabel="Fh+Fe (W/m2)")
    # scatter plot of (Fh+Fe) versus Fa, night time
    night_mask = (data["Fsd"]["Data"] < 10)
    Fa_night = numpy.ma.masked_where(night_mask==False, Fa_30min)
    Fe_night = numpy.ma.masked_where(night_mask==False, Fe_30min)
    Fh_night = numpy.ma.masked_where(night_mask==False, Fh_30min)
    mask = numpy.ma.mask_or(Fa_night.mask, Fe_night.mask)
    mask = numpy.ma.mask_or(mask, Fh_night.mask)
    Fa_night = numpy.ma.array(Fa_night, mask=mask)         # apply the mask
    Fe_night = numpy.ma.array(Fe_night, mask=mask)
    Fh_night = numpy.ma.array(Fh_night, mask=mask)
    FhpFe_night = Fh_night + Fe_night
    xyplot(Fa_night, FhpFe_night, sub=[2,2,4], regr=1, title="Night", xlabel="Fa (W/m2)", ylabel="Fh+Fe (W/m2)")
    # hard copy of plot
    fig.savefig(figure_name, format='png')
    # draw the plot on the screen
    plt.draw()
    plt.ioff()

def plot_quickcheck_get_seb(daily):
    # get the SEB ratio
    # get the daytime data, defined by Fsd>10 W/m2
    nm = daily["night_mask"]["Data"]
    Fa_daily = daily["Fa"]["Data"]
    Fe_daily = daily["Fe"]["Data"]
    Fh_daily = daily["Fh"]["Data"]
    Fa_day = numpy.ma.masked_where(nm == True, Fa_daily)
    Fe_day = numpy.ma.masked_where(nm == True, Fe_daily)
    Fh_day = numpy.ma.masked_where(nm == True, Fh_daily)
    # mask based on dependencies, set all to missing if any missing
    mask = numpy.ma.mask_or(Fa_day.mask, Fe_day.mask)
    mask = numpy.ma.mask_or(mask, Fh_day.mask)
    # apply the mask
    Fa_day = numpy.ma.array(Fa_day, mask=mask)
    Fe_day = numpy.ma.array(Fe_day, mask=mask)
    Fh_day = numpy.ma.array(Fh_day, mask=mask)
    # get the daily averages
    Fa_day_avg = numpy.ma.average(Fa_day, axis=1)
    Fe_day_avg = numpy.ma.average(Fe_day, axis=1)
    Fh_day_avg = numpy.ma.average(Fh_day, axis=1)
    SEB = {"label": "(Fh+Fe)/Fa"}
    # get the number of values in the daily average
    SEB["Count"] = numpy.ma.count(Fh_day, axis=1)
    # get the SEB ratio
    SEB["Avg"] = (Fe_day_avg + Fh_day_avg)/Fa_day_avg
    SEB["Avg"] = numpy.ma.masked_where(SEB["Count"] <= 5, SEB["Avg"])
    idx = numpy.where(numpy.ma.getmaskarray(SEB["Avg"]) == True)[0]
    SEB["Count"][idx] = 0
    return SEB

def plot_quickcheck_get_ef(daily):
    # get the EF
    # get the daytime data, defined by Fsd>10 W/m2
    nm = daily["night_mask"]["Data"]
    Fa_daily = daily["Fa"]["Data"]
    Fe_daily = daily["Fe"]["Data"]
    Fa_day = numpy.ma.masked_where(nm == True, Fa_daily)
    Fe_day = numpy.ma.masked_where(nm == True, Fe_daily)
    # mask based on dependencies, set all to missing if any missing
    mask = numpy.ma.mask_or(Fa_day.mask, Fe_day.mask)
    # apply the mask
    Fa_day = numpy.ma.array(Fa_day, mask=mask)
    Fe_day = numpy.ma.array(Fe_day, mask=mask)
    # get the daily averages
    Fa_day_avg = numpy.ma.average(Fa_day, axis=1)
    Fe_day_avg = numpy.ma.average(Fe_day, axis=1)
    # get the number of values in the daily average
    EF = {"label": "EF=Fe/Fa"}
    EF["Count"] = numpy.ma.count(Fe_day, axis=1)
    # get the EF ratio
    EF["Avg"] = Fe_day_avg/Fa_day_avg
    EF["Avg"] = numpy.ma.masked_where(EF["Count"] <= 5, EF["Avg"])
    idx = numpy.where(numpy.ma.getmaskarray(EF["Avg"]) == True)[0]
    EF["Count"][idx] = 0
    return EF

def plot_quickcheck_get_br(daily):
    # get the BR
    # get the daytime data, defined by Fsd>10 W/m2
    nm = daily["night_mask"]["Data"]
    Fh_daily = daily["Fh"]["Data"]
    Fe_daily = daily["Fe"]["Data"]
    Fe_day = numpy.ma.masked_where(nm == True, Fe_daily)
    Fh_day = numpy.ma.masked_where(nm == True, Fh_daily)
    # mask based on dependencies, set all to missing if any missing
    mask = numpy.ma.mask_or(Fe_day.mask, Fh_day.mask)
    # apply the mask
    Fe_day = numpy.ma.array(Fe_day, mask=mask)
    Fh_day = numpy.ma.array(Fh_day, mask=mask)
    # get the daily averages
    Fe_day_avg = numpy.ma.average(Fe_day, axis=1)
    Fh_day_avg = numpy.ma.average(Fh_day, axis=1)
    # get the number of values in the daily average
    BR = {"label": "BR=Fh/Fe"}
    BR["Count"] = numpy.ma.count(Fh_day, axis=1)
    # get the BR ratio
    BR["Avg"] = Fh_day_avg/Fe_day_avg
    BR["Avg"] = numpy.ma.masked_where(BR["Count"] <= 5, BR["Avg"])
    idx = numpy.where(numpy.ma.getmaskarray(BR["Avg"]) == True)[0]
    BR["Count"][idx] = 0
    return BR

def plot_quickcheck_get_wue(daily):
    # get the Wue
    # get the daytime data, defined by Fsd>10 W/m2
    nm = daily["night_mask"]["Data"]
    Fc_daily = daily["Fc"]["Data"]
    Fe_daily = daily["Fe"]["Data"]
    Fe_day = numpy.ma.masked_where(nm == True, Fe_daily)
    Fc_day = numpy.ma.masked_where(nm == True, Fc_daily)
    # mask based on dependencies, set all to missing if any missing
    mask = numpy.ma.mask_or(Fe_day.mask, Fc_day.mask)
    # apply the mask
    Fe_day = numpy.ma.array(Fe_day,mask=mask)
    Fc_day = numpy.ma.array(Fc_day,mask=mask)
    # get the daily averages
    Fe_day_avg = numpy.ma.average(Fe_day, axis=1)
    Fc_day_avg = numpy.ma.average(Fc_day, axis=1)
    # get the number of values in the daily average
    WUE = {"label": "WUE=Fc/Fe"}
    WUE["Count"] = numpy.ma.count(Fc_day, axis=1)
    WUE["Avg"] = Fc_day_avg/Fe_day_avg
    WUE["Avg"] = numpy.ma.masked_where(WUE["Count"] <= 5, WUE["Avg"])
    idx = numpy.where(numpy.ma.getmaskarray(WUE["Avg"]) == True)[0]
    WUE["Avg"][idx] = 0
    return WUE

def plot_quickcheck_get_avg(daily, label, filter_type=None):
    """
    Purpose:
     Apply a day time or night time filter to data, if reuested, and return
     the daily average of the (filtered) data and the number of data points
     used to provide the average.
    Usage:
     avg, count = pfp_plot.plot_quickcheck_get_avg(daily, label, filter_type="day")
     where;
      daily is a dictionary of data as 2D arrays (axis 0 is hour of the day, axis 1 is the day)
      label is the label of the data
      filter_type is the type of filter to apply ("day", "night" or None)
     and
      avg is the daily average
      count is the number of points used in the average
    Author: PRI
    Date: March 2019
    """
    if filter_type is None:
        data = daily[label]["Data"]
    elif filter_type.lower() == "day":
        dm = daily["day_mask"]["Data"]
        data = numpy.ma.masked_where(dm == False, daily[label]["Data"])
    elif filter_type.lower() == "night":
        nm = daily["night_mask"]["Data"]
        data = numpy.ma.masked_where(nm == False, daily[label]["Data"])
    else:
        msg = "plot_quickcheck_get_avg: unrecognised filter type (" + filter_type + ")"
        logger.warning(msg)
        msg = "plot_quickcheck_get_avg: no filter applied"
        logger.warning(msg)
    avg = numpy.ma.average(data, axis=1)
    count = numpy.ma.count(data, axis=1)
    return avg, count

def plot_quickcheck(cf):
    nFig = 0
    # get the netCDF filename
    ncfilename = pfp_io.get_infilenamefromcf(cf)
    # read the netCDF file and return the data structure "ds"
    ds = pfp_io.nc_read_series(ncfilename)
    series_list = ds.series.keys()
    # get the time step
    ts = int(ds.globalattributes["time_step"])
    # get the site name
    site_name = ds.globalattributes["site_name"]
    level = ds.globalattributes["nc_level"]
    # get the datetime series
    DateTime = ds.series["DateTime"]["Data"]
    # get the initial start and end dates
    StartDate = str(DateTime[0])
    EndDate = str(DateTime[-1])
    # find the start index of the first whole day (time=00:30)
    si = pfp_utils.GetDateIndex(DateTime, StartDate, ts=ts, default=0, match="startnextday")
    # find the end index of the last whole day (time=00:00)
    ei = pfp_utils.GetDateIndex(DateTime, EndDate, ts=ts, default=-1, match="endpreviousday")
    DateTime = DateTime[si:ei+1]
    nrecs = len(DateTime)
    plot_title = site_name + ": " + DateTime[0].strftime("%Y-%m-%d") + " to " + DateTime[-1].strftime("%Y-%m-%d")
    # get the final start and end dates
    StartDate = str(DateTime[0])
    EndDate = str(DateTime[-1])
    # get the 30 minute data from the data structure
    logger.info(" Getting data from data structure")
    data_list = ["Month", "Hour", "Minute",
                 "Fsd", "Fsu", "Fld", "Flu", "Fn",
                 "Fg", "Fa", "Fe", "Fh", "Fc", "ustar",
                 "Ta", "H2O", "CO2", "Precip", "Ws",
                 "Sws", "Ts"]
    data = {}
    for label in data_list:
        if label in series_list:
            data[label] = pfp_utils.GetVariable(ds, label, start=si, end=ei)
        else:
            data[label] = pfp_utils.CreateEmptyVariable(label, nrecs, datetime=DateTime)
    # get the number of days in the data set
    ntsInDay = float(24.0*60.0/float(ts))
    if math.modf(ntsInDay)[0] != 0:
        msg = " Time step (" + str(ts) + ") is not a sub-multiple of 60 minutes "
        logger.error(msg)
        return
    ntsInDay = int(ntsInDay)
    nDays = float(len(DateTime))/ntsInDay
    if math.modf(nDays)[0] != 0:
        msg = "Not a whole number of days (" + str(nDays) +")"
        logger.error(msg)
        return
    nDays = int(nDays)
    logger.info(" Getting daily averages from 30 minute data")
    # reshape the 1D array of 30 minute data into a 2D array of (nDays,ntsInDay)
    DT_daily = DateTime[0::ntsInDay]
    daily = {}
    for label in list(data.keys()):
        daily[label] = {"label": label}
        daily[label]["Data"] = data[label]["Data"].reshape(nDays, ntsInDay)
        daily[label]["Attr"] = data[label]["Attr"]
    # add the day and night masks
    daily["day_mask"] = {"Data": (data["Fsd"]["Data"] >= 10).reshape(nDays, ntsInDay)}
    daily["night_mask"] = {"Data": (data["Fsd"]["Data"] < 10).reshape(nDays, ntsInDay)}
    # get the daily ratios
    daily["SEB"] = plot_quickcheck_get_seb(daily)
    daily["EF"] = plot_quickcheck_get_ef(daily)
    daily["BR"] = plot_quickcheck_get_br(daily)
    daily["WUE"] = plot_quickcheck_get_wue(daily)
    daily["Sws"]["Avg"], daily["Sws"]["Count"] = plot_quickcheck_get_avg(daily, "Sws")
    daily["Precip"]["Avg"], daily["Precip"]["Count"] = plot_quickcheck_get_avg(daily, "Precip")
    # scatter plot of (Fh+Fe) versys Fa, all data
    nFig = nFig + 1
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_SEB_30minutes.png"
    figure_name = os.path.join("plots", file_name)
    plot_quickcheck_seb(nFig, plot_title, figure_name, data, daily)
    # plot the daily ratios
    logger.info(" Doing the daily ratios plot")
    plt.ion()
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Ratios")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot1_list = ["SEB", "EF", "BR", "WUE", "Sws", "Precip"]
    nplots = len(tsplot1_list)
    for nrow, label in enumerate(tsplot1_list):
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], colours=daily[label]["Count"],
               ylabel=daily[label]["label"])
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailyRatios.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    # plot the daily average radiation
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Radiation")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot2_list = ["Fsd", "Fsu", "Fld", "Flu", "Fn", "Fg"]
    nplots = len(tsplot2_list)
    for nrow, label in enumerate(tsplot2_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label)
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], colours=daily[label]["Count"],
               ylabel=daily[label]["label"])
    file_name = site_name.replace(" ", "") + "_" + level +"_QC_DailyRadn.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    # plot the daily average fluxes
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Fluxes")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot3_list = ["Fsd", "Fa", "Fe", "Fh", "Fc"]
    nplots = len(tsplot3_list)
    for nrow, label in enumerate(tsplot3_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label, filter_type="day")
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], colours=daily[label]["Count"],
               ylabel=daily[label]["label"])
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailyFluxes.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    # plot the daily average meteorology
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Meteorology")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot4_list = ["Ta", "H2O", "CO2", "Ws", "Precip"]
    nplots = len(tsplot4_list)
    for nrow, label in enumerate(tsplot4_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label)
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], colours=daily[label]["Count"],
               ylabel=daily[label]["label"])
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailyMet.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    # plot the daily average soil data
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Soil Data")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot5_list = ["Ta", "Ts", "Sws", "Fg", "Precip"]
    nplots = len(tsplot5_list)
    for nrow, label in enumerate(tsplot5_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label)
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], colours=daily[label]["Count"],
               ylabel=daily[label]["label"])
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailySoil.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    # *** end of section for time series of daily averages
    # *** start of section for diurnal plots by month ***
    month_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    diurnal_list = ["Fsd", "Fsu", "Fa", "Fn", "Fg", "Ta", "Ts", "Fh", "Fe", "Fc"]
    # plot diurnals
    for label in diurnal_list:
        if label not in series_list:
            continue
        msg = " Doing the monthly diurnal plots for " + label
        logger.info(msg)
        nFig = nFig + 1
        fig = plt.figure(nFig, figsize=(6, 9))
        window_title = "Diurnal " + label
        fig.canvas.set_window_title(window_title)
        plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
        j = 0
        for i in [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
            j = j + 1
            idx = numpy.where(daily["Month"]["Data"] == i)[0]
            if len(idx) == 0:
                continue
            hr = daily["Hour"]["Data"][idx] + daily["Minute"]["Data"][idx]/float(60)
            avg = numpy.ma.average(daily[label]["Data"][idx], axis=0)
            num = numpy.ma.count(daily[label]["Data"][idx], axis=0)
            if j in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
                xlabel = None
                show_xtick_labels = False
            else:
                xlabel = "Hour"
                show_xtick_labels = True
            if j in [2, 3, 5, 6, 8, 9, 11, 12]:
                ylabel = None
            else:
                ylabel = label + " (" + daily[label]["Attr"]["units"] + ")"
            hrplot(hr[0], avg, sub=[4, 3, j], colours=num,
                   title=month_list[i-1], xlabel=xlabel, ylabel=ylabel,
                   show_xtick_labels=show_xtick_labels)
        # save the plot to file
        level = ds.globalattributes["nc_level"]
        file_name = site_name.replace(" ", "") + "_" + level + "_QC_Diurnal" + label + "ByMonth.png"
        figure_name = os.path.join("plots", file_name)
        fig.savefig(figure_name, format="png")
        # draw the plot on the screen
        plt.draw()
    plt.ioff()
    return

def plot_setup(cf, title):
    p = {}
    if "plot_path" in cf["Files"]:
        p["plot_path"] = os.path.join(cf["Files"]["plot_path"], cf["level"])
    else:
        p["plot_path"] = os.path.join("plots", cf["level"])
    p['PlotDescription'] = str(title)
    #p['SeriesList'] = ast.literal_eval(cf['Plots'][str(nFig)]['Variables'])
    var_string = cf['Plots'][str(title)]['Variables']
    if "," in var_string:
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
    plt.subplot(sub[0], sub[1], sub[2])
    plt.plot(x, y, 'b.')
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
    plt.subplots_adjust(wspace=wspace, hspace=hspace)
    if (numpy.ma.count(x) == 0) or (numpy.ma.count(y) == 0):
        return
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
    return

def hrplot(x,y,sub=[1,1,1],title=None,xlabel=None,ylabel=None,colours=None,show_xtick_labels=True):
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
    if not show_xtick_labels:
        ax = plt.gca()
        ax.tick_params(labelbottom=False)

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
    if sub[2] != sub[0]:
        ax.set_xlabel('',visible=False)
        ax.tick_params(labelbottom=False)

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
