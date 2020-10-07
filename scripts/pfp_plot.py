import datetime
import logging
import math
import os
# 3rd party
import matplotlib
import matplotlib.dates as mdt
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy
from scipy import stats
import statsmodels.api as sm
# PFP modules
import constants as c
import meteorologicalfunctions as pfp_mf
import pfp_cfg
import pfp_ck
import pfp_io
import pfp_utils

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

def get_yaxislimitsfromcf(cf, nFig, maxkey, minkey, nSer, YArray):
    # Y axis maxima specified
    if maxkey in cf['Plots'][str(nFig)].keys():
        # Evaluate the minima list
        maxlist = pfp_cfg.cfg_string_to_list(cf['Plots'][str(nFig)][maxkey])
        # This entry is 'Auto' ...
        if str(maxlist[nSer])=='Auto':
            # ... so take the array minimum value
            YAxMax = numpy.ma.max(YArray)
        else:
            # Evaluate the entry for this series
            YAxMax = float(maxlist[nSer])
    else:
        # Y axis minima not given, use auto
        YAxMax = numpy.ma.max(YArray)
    # Y axis minima specified
    if minkey in cf['Plots'][str(nFig)].keys():
        # Evaluate the minima list
        minlist = pfp_cfg.cfg_string_to_list(cf['Plots'][str(nFig)][minkey])
        # This entry is 'Auto' ...
        if str(minlist[nSer])=='Auto':
             # ... so take the array minimum value
            YAxMin = numpy.ma.min(YArray)
        else:
            # Evaluate the entry for this series
            YAxMin = float(minlist[nSer])
    else:
        # Y axis minima not given, use auto
        YAxMin = numpy.ma.min(YArray)
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
        mypause(0.5)
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
            if (end < ldt["Data"][0]) or (start > ldt["Data"][-1]):
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
            # if no data, skip this plot and delete the axes
            if (len(ustar["Data"]) == 0) or (len(Fc["Data"]) == 0):
                fig.delaxes(axs[row, col])
                continue
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
        mypause(0.5)
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
        if "name" in cf["Variables"][var]:
            fp_info["variables"][var]["name"] = str(cf["Variables"][var]["name"])
        else:
            fp_info["variables"][var]["name"] = str(var)
        # get the upper and lower range limits
        if "lower" in cf["Variables"][var]:
            fp_info["variables"][var]["lower"] = float(cf["Variables"][var]["lower"])
        else:
            fp_info["variables"][var]["lower"] = float(-1)*c.large_value
        if "upper" in cf["Variables"][var]:
            fp_info["variables"][var]["upper"] = float(cf["Variables"][var]["upper"])
        else:
            fp_info["variables"][var]["upper"] = c.large_value
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
        if ds[infilename].returncodes["value"] != 0: return ds
    for var in cf["Variables"].keys():
        if "in_filename" in cf["Variables"][var]:
            if cf["Variables"][var]["in_filename"] not in ds:
                infilename = cf["Variables"][var]["in_filename"]
                ds[cf["Variables"][var]["in_filename"]] = pfp_io.nc_read_series(infilename)
                if ds[cf["Variables"][var]["in_filename"]].returncodes["value"] != 0: return ds
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
    show_plots = pfp_utils.get_optionskeyaslogical(cf, "show_plots", default=True)
    for nFig, title in enumerate(cf["Plots"].keys()):
        if show_plots:
            plt.ion()
        else:
            plt.ioff()
        fig = plt.figure(nFig, figsize=(13,8))
        fig.clf()
        fig.canvas.set_window_title(title)
        plt.figtext(0.5, 0.95, title_str, horizontalalignment="center")
        fig_var_list = pfp_cfg.cfg_string_to_list(cf["Plots"][title]["variables"])
        logger.info(" Plotting fingerprint: " + str(fig_var_list))
        nPlots = len(fig_var_list)
        for n,var in enumerate(fig_var_list):
            nc_varname = fp_info["variables"][var]["name"]
            infilename = fp_info["variables"][var]["in_filename"]
            ldt = ds[infilename].series["DateTime"]["Data"]
            ts = fp_info["variables"][var]["time_step"]
            si = pfp_utils.GetDateIndex(ldt, str(overlap_start), ts=ts, default=0, match='startnextday')
            ei = pfp_utils.GetDateIndex(ldt, str(overlap_end), ts=ts, default=-1, match='endpreviousday')
            ldt = ldt[si:ei + 1]
            nPerHr = int(float(60)/ts + 0.5)
            nPerDay = int(float(24)*nPerHr + 0.5)
            nDays = len(ldt)/nPerDay
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
            data = pfp_ck.cliptorange(data,fp_info["variables"][var]["lower"], fp_info["variables"][var]["upper"])
            data_daily = data.reshape(nDays,nPerDay)
            units = str(ds[infilename].series[nc_varname]['Attr']['units'])
            label = var + ' (' + units + ')'
            if n==0:
                ax = plt.subplot(1,nPlots,n+1)
            else:
                ax = plt.subplot(1,nPlots,n+1,sharey=ax)
            sd = mdt.date2num(ldt[0])
            ed = mdt.date2num(ldt[-1])
            # only plot the fingerprint if there is data to plot
            if numpy.ma.count(data) != 0:
                plt.imshow(data_daily,extent=[0,24,sd,ed],aspect='auto',origin='lower')
                ax.yaxis_date()
                cb = plt.colorbar(orientation='horizontal',fraction=0.02,pad=0.075)
                if numpy.ma.min(data) == numpy.ma.max(data):
                    if numpy.min(data)!=0:
                        data_min = numpy.ma.min(data)-0.01*numpy.ma.min(data)
                        data_max = numpy.ma.max(data)+0.01*numpy.ma.max(data)
                    else:
                        data_min = -1.0
                        data_max = 1.0
                else:
                    data_min = numpy.ma.min(data)
                    data_max = numpy.ma.max(data)
                cb.set_ticks(numpy.linspace(data_min,data_max,4))
            plt.xticks([0,6,12,18,24])
            plt.xlabel(label)
            if n!= 0:
                plt.setp(ax.get_yticklabels(), visible=False)
        if "Files" in cf:
            if "plot_path" in cf["Files"]:
                plot_path = cf["Files"]["plot_path"]+"fingerprints/"
            else:
                plot_path = "plots/"
        else:
            plot_path = "plots/"
        if not os.path.exists(plot_path):
            os.makedirs(plot_path)
        pngname = plot_path + site_name.replace(" ","") + "_" + level + "_"
        pngname = pngname + title.replace(" ", "_") + ".png"
        fig.savefig(pngname, format="png")
        if show_plots:
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
    if ds.returncodes["value"] != 0: return
    site_name = ds.globalattributes["site_name"]
    ldt=ds.series["DateTime"]["Data"]
    sdt = ldt[0]
    edt = ldt[-1]
    nFig = 0
    plt.ion()
    for series in series_list:
        if "name" in cf["Variables"][series]:
            label = cf["Variables"][series]["name"]
        else:
            label = series
        if label not in ds.series.keys():
            logger.error("Series " + label + " not found in input file, skipping ...")
            continue
        logger.info(" Doing plot for " + label)
        data, flag, attr = pfp_utils.GetSeriesasMA(ds, label)
        nFig = nFig + 1
        fig = plt.figure(nFig,figsize=(10.9, 7.5))
        fig.canvas.set_window_title(label)
        plt.plot(ldt, data, "b.")
        plt.xlim(sdt, edt)
        plt.xlabel("Date")
        plt.ylabel(label + " (" + attr["units"] + ")")
        title_str = site_name + ": " + sdt.strftime("%Y-%m-%d") + " to "
        title_str += edt.strftime("%Y-%m-%d") + "; " + series
        plt.title(title_str)
        figname = 'plots/' + ds.globalattributes['site_name'].replace(' ','')
        figname += '_' + ds.globalattributes['nc_level'] + '_FC_' + label + '.png'
        fig.savefig(figname, format='png')
        plt.draw()
        mypause(0.5)
    plt.ioff()
    return

def plot_explore_histograms(ds, labels):
    """ Plot histograms of selected variables."""
    # set up a dictionary with the percentiles of the histograms to be plotted
    p = {0: {"lwr": 0.0, "upr": 100.0},
         1: {"lwr": 0.1, "upr": 99.9},
         2: {"lwr": 0.5, "upr": 99.5},
         3: {"lwr": 1.0, "upr": 99.0},
         4: {"lwr": 2.5, "upr": 97.5}}
    site_name = ds.globalattributes["site_name"]
    plt.ion()
    for label in labels:
        var = pfp_utils.GetVariable(ds, label)
        sdt = var["DateTime"][0]
        edt = var["DateTime"][-1]
        fig = plt.figure(figsize=(11, 8), tight_layout=True)
        window_title = site_name + ": " + var["Label"]
        fig.canvas.set_window_title(window_title)
        gs = gridspec.GridSpec(2, 5, height_ratios=[1, 0.5])
        ax_ts = fig.add_subplot(gs[0, :])
        title_str = site_name + ": " + sdt.strftime("%Y-%m-%d") + " to "
        title_str += edt.strftime("%Y-%m-%d")
        ax_ts.set_title(title_str)
        ax_ts.plot(var["DateTime"], var["Data"], 'b.', label=var["Label"])
        ax_ts.legend()
        for n in p:
            d = plot_explore_do_histogram(var, p[n]["lwr"], p[n]["upr"])
            lwrs = str(pfp_utils.round2significant(d["lwr"], 4))
            uprs = str(pfp_utils.round2significant(d["upr"], 4))
            x = numpy.arange(len(d["hist"]))
            ax_hist = fig.add_subplot(gs[1, n])
            label = str(p[n]["lwr"]) + "," + str(p[n]["upr"])
            ax_hist.bar(x, d["hist"])
            ax_hist.text(0.5, 0.9, label, transform=ax_hist.transAxes,
                        horizontalalignment='center')
            ax_hist.set_xticks([x[1], x[-2]])
            ax_hist.set_xticklabels([lwrs, uprs])
        plt.draw()
        mypause(0.5)
    return

def plot_explore_do_histogram(var, plwr, pupr):
    """ Return a dictionary with the histogram results for given percentiles."""
    d = {}
    idx = numpy.where(numpy.ma.getmaskarray(var["Data"]) == False)[0]
    d["lwr"], d["upr"] = numpy.percentile(var["Data"][idx],[plwr, pupr])
    idx = numpy.ma.where((var["Data"] >= d["lwr"]) &
                         (var["Data"] <= d["upr"]))[0]
    bins = numpy.linspace(d["lwr"], d["upr"], num=25)
    bins = numpy.insert(bins, 0, numpy.ma.min(var["Data"]))
    d["bins"] = numpy.append(bins, numpy.ma.max(var["Data"]))
    d["hist"], d["edges"] = numpy.histogram(var["Data"][idx], bins=d["bins"])
    d["idx"] = idx
    return d

def plot_explore_percentiles(ds, labels):
    """ Plot time series histograms of selected variables."""
    p = {0: {"lwr": 0.0, "upr": 100.0},
         1: {"lwr": 0.1, "upr": 99.9},
         2: {"lwr": 0.5, "upr": 99.5},
         3: {"lwr": 1.0, "upr": 99.0},
         4: {"lwr": 2.5, "upr": 97.5}}
    site_name = ds.globalattributes["site_name"]
    plt.ion()
    for label in labels:
        var = pfp_utils.GetVariable(ds, label)
        sdt = var["DateTime"][0]
        edt = var["DateTime"][-1]
        fig = plt.figure(figsize=(11, 8), tight_layout=True)
        window_title = site_name + ": " + var["Label"]
        fig.canvas.set_window_title(window_title)
        gs = gridspec.GridSpec(5, 2, width_ratios=[5, 1])
        for n in p:
            d = plot_explore_do_histogram(var, p[n]["lwr"], p[n]["upr"])
            ax_ts = fig.add_subplot(gs[n, 0])
            if n == 0:
                title_str = site_name + ": " + sdt.strftime("%Y-%m-%d") + " to "
                title_str += edt.strftime("%Y-%m-%d")
                ax_ts.set_title(title_str)
            ax_ts.plot(var["DateTime"][d["idx"]], var["Data"][d["idx"]], 'b.')
            lwrs = str(pfp_utils.round2significant(d["lwr"], 4))
            uprs = str(pfp_utils.round2significant(d["upr"], 4))
            x = numpy.arange(len(d["hist"]))
            ax_hist = fig.add_subplot(gs[n, 1])
            label = str(p[n]["lwr"]) + "," + str(p[n]["upr"])
            ax_hist.bar(x, d["hist"])
            ax_hist.text(0.5, 0.85, label, transform=ax_hist.transAxes,
                         horizontalalignment='center')
            ax_hist.set_xticks([x[1], x[-2]])
            ax_hist.set_xticklabels([lwrs, uprs])
        plt.draw()
        mypause(0.5)
    return

def plot_explore_timeseries(ds, labels):
    """ Plot time series of selected variables."""
    site_name = ds.globalattributes["site_name"]
    nrows = len(labels)
    plt.ion()
    fig, axs = plt.subplots(nrows=nrows, sharex=True, figsize=(10.9, 7.5))
    fig.subplots_adjust(wspace=0.0, hspace=0.05, left=0.1, right=0.95, top=0.95, bottom=0.1)
    if nrows == 1: axs = [axs]
    fig.canvas.set_window_title(site_name)
    for n, label in enumerate(labels):
        var = pfp_utils.GetVariable(ds, label)
        sdt = var["DateTime"][0]
        edt = var["DateTime"][-1]
        axs[n].plot(var["DateTime"], var["Data"], "b.", label=label)
        axs[n].legend()
        if n == 0:
            title_str = site_name + ": " + sdt.strftime("%Y-%m-%d") + " to "
            title_str += edt.strftime("%Y-%m-%d")
            axs[n].set_title(title_str)
        if n == nrows-1:
            axs[n].set_xlabel("Date")
        axs[n].set_ylabel("(" + var["Attr"]["units"] + ")")
    plt.draw()
    mypause(0.5)
    plt.ioff()
    return

def plottimeseries(cf, nFig, dsa, dsb):
    SiteName = dsa.globalattributes['site_name']
    Level = dsb.globalattributes['nc_level']
    ts = int(dsa.globalattributes['time_step'])
    ldt = dsa.series["DateTime"]["Data"]
    Month = ldt[0].month
    Hdh = [dt.hour+(dt.minute+dt.second/float(60))/float(60) for dt in ldt]
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
            Hr2, Av2, Sd2, Mx2, Mn2 = get_diurnalstats(Hdh, dsb.series[ThisOne]['Data'], ts)
            Av2 = numpy.ma.masked_where(Av2==c.missing_value,Av2)
            Sd2 = numpy.ma.masked_where(Sd2==c.missing_value,Sd2)
            Mx2 = numpy.ma.masked_where(Mx2==c.missing_value,Mx2)
            Mn2 = numpy.ma.masked_where(Mn2==c.missing_value,Mn2)
            hr2_ax = fig.add_axes([p['hr1_XAxOrg'],p['YAxOrg'],p['hr2_XAxLen'],p['ts_YAxLen']])
            #hr2_ax.hold(True)
            hr2_ax.plot(Hr2,Av2,'y-',Hr2,Mx2,'r-',Hr2,Mn2,'b-')
            section = pfp_utils.get_cfsection(cf, ThisOne, mode='quiet')
            if section != None:
                if 'DiurnalCheck' in cf[section][ThisOne].keys():
                    NSdarr = numpy.array(pfp_ck.parse_rangecheck_limit(cf[section][ThisOne]['DiurnalCheck']['numsd']))
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
    if ds.returncodes["value"] != 0: return
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
    data = {"Month":{"Attr":{}}, "Hour":{"Attr":{}}, "Minute":{"Attr":{}}}
    # do the month, hour and minute separately
    data["Month"]["Data"] = numpy.array([d.month for d in DateTime])
    data["Hour"]["Data"] = numpy.array([d.hour for d in DateTime])
    data["Minute"]["Data"] = numpy.array([d.minute for d in DateTime])
    # now do the data we want to plot
    data_list = ["Fsd", "Fsu", "Fld", "Flu", "Fn",
                 "Fg", "Fa", "Fe", "Fh", "Fc", "ustar",
                 "Ta", "H2O", "CO2", "Precip", "Ws",
                 "Sws", "Ts"]
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
    mypause(0.5)
    # plot the daily ratios
    cmap = plt.cm.get_cmap("RdYlBu")
    logger.info(" Doing the daily ratios plot")
    plt.ion()
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Ratios")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    plt.figtext(0.5, 0.90, "Day time data points only", horizontalalignment="center", size=14)
    tsplot1_list = ["SEB", "EF", "BR", "WUE", "Sws", "Precip"]
    nplots = len(tsplot1_list)
    for nrow, label in enumerate(tsplot1_list):
        percent = 100*daily[label]["Count"]/ntsInDay
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], ylabel=label,
               colours=percent, cmap=cmap, vmin=0, vmax=100)
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailyRatios.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    mypause(0.5)
    # plot the daily average radiation
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Radiation")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot2_list = ["Fsd", "Fsu", "Fld", "Flu", "Fn", "Fg"]
    nplots = len(tsplot2_list)
    for nrow, label in enumerate(tsplot2_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label)
        percent = 100*daily[label]["Count"]/ntsInDay
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], ylabel=label,
               colours=percent, cmap=cmap, vmin=0, vmax=100)
    file_name = site_name.replace(" ", "") + "_" + level +"_QC_DailyRadn.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    mypause(0.5)
    # plot the daily average fluxes
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Fluxes")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    plt.figtext(0.5, 0.90, "Day time data points only", horizontalalignment="center", size=14)
    tsplot3_list = ["Fsd", "Fa", "Fe", "Fh", "Fc"]
    nplots = len(tsplot3_list)
    for nrow, label in enumerate(tsplot3_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label, filter_type="day")
        percent = 100*daily[label]["Count"]/ntsInDay
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], ylabel=label,
               colours=percent, cmap=cmap, vmin=0, vmax=100)
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailyFluxes.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    mypause(0.5)
    # plot the daily average meteorology
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Meteorology")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot4_list = ["Ta", "H2O", "CO2", "Ws", "Precip"]
    nplots = len(tsplot4_list)
    for nrow, label in enumerate(tsplot4_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label)
        percent = 100*daily[label]["Count"]/ntsInDay
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], ylabel=label,
               colours=percent, cmap=cmap, vmin=0, vmax=100)
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailyMet.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    mypause(0.5)
    # plot the daily average soil data
    nFig = nFig + 1
    fig = plt.figure(nFig, figsize=(9, 6))
    fig.canvas.set_window_title("Daily Average Soil Data")
    plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
    tsplot5_list = ["Ta", "Ts", "Sws", "Fg", "Precip"]
    nplots = len(tsplot5_list)
    for nrow, label in enumerate(tsplot5_list):
        daily[label]["Avg"], daily[label]["Count"] = plot_quickcheck_get_avg(daily, label)
        percent = 100*daily[label]["Count"]/ntsInDay
        tsplot(DT_daily, daily[label]["Avg"], sub=[nplots, 1, nrow+1], ylabel=label,
               colours=percent, cmap=cmap, vmin=0, vmax=100)
    file_name = site_name.replace(" ", "") + "_" + level + "_QC_DailySoil.png"
    figure_name = os.path.join("plots", file_name)
    fig.savefig(figure_name, format="png")
    plt.draw()
    mypause(0.5)
    # *** end of section for time series of daily averages
    # *** start of section for diurnal plots by month ***
    # month labels
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    # variable labels
    labels = ["Fsd", "Fsu", "Fa", "Fn", "Fg", "Ta", "Ts", "Fh", "Fe", "Fc"]
    # get the colour map, points will be coloured according to the percentage of good data
    cm = plt.cm.get_cmap("RdYlBu")
    # 12 plots per page, 1 for each month
    nrows = 4
    ncols = 3
    # loop over the variables to be plotted
    for label in labels:
        # skip if the label is not in the data structure
        if label not in series_list:
            continue
        # put up a log message
        msg = " Doing the monthly diurnal plots for " + label
        logger.info(msg)
        # increment the figure number so we don't overwrite any plots
        nFig = nFig + 1
        # create the sub plots, 4 rows of 3 columns each with shared X and Y axes
        fig, axs = plt.subplots(num=nFig, nrows=nrows, ncols=ncols, sharex=True, sharey=True,
                                figsize=(8, 10))
        # do the window and plot titles
        window_title = "Diurnal " + label
        fig.canvas.set_window_title(window_title)
        plt.figtext(0.5, 0.95, plot_title, horizontalalignment="center", size=16)
        # loop over each month
        for j, i in enumerate([12] + range(1, 12)):
            # indices of this month in the daily data
            idx = numpy.where(daily["Month"]["Data"] == i)[0]
            # column and row number for this plot
            ncol = numpy.mod(j, ncols)
            nrow = j/ncols
            # skip month and remove axes if there is no data for this month
            if len(idx) == 0:
                axs[nrow, ncol].remove()
                continue
            # turn off the X axis and tick labels for all but the last row
            if nrow > 0:
                axs[nrow-1, ncol].tick_params(labelbottom=False)
                axs[nrow-1, ncol].xaxis.label.set_visible(False)
            # turn off the Y axis labels for all but the first column
            if ncol > 0:
                axs[nrow, ncol].yaxis.label.set_visible(False)
            # get the decimal hour
            hr = daily["Hour"]["Data"][idx] + daily["Minute"]["Data"][idx]/float(60)
            # get the average and number of good data points at each time of the day for this month
            avg = numpy.ma.average(daily[label]["Data"][idx], axis=0)
            num = 100*numpy.ma.count(daily[label]["Data"][idx], axis=0)/len(idx)
            # plot the average for each time of the day, colour set by percentage of good data
            ax = axs[nrow, ncol].scatter(hr[0], avg, c=num, cmap=cm, vmin=0, vmax=100)
            # add the title, axis labels, tick marks etc
            axs[nrow, ncol].set_title(months[i-1])
            axs[nrow, ncol].set_xlim([0, 24])
            axs[nrow, ncol].set_xticks([0, 6, 12, 18, 24])
            axs[nrow, ncol].tick_params(labelbottom=True)
            axs[nrow, ncol].set_xlabel("Hour")
            axs[nrow, ncol].set_ylabel(label + " (" + daily[label]["Attr"]["units"] + ")")
            # add colour bar as an inset
            cbins = inset_axes(axs[nrow, ncol], width="50%", height="5%", loc="upper center")
            ticks = [0, 50, 100]
            fig.colorbar(ax, cax=cbins, orientation="horizontal", ticks=ticks)
        # save the plot to file
        level = ds.globalattributes["nc_level"]
        file_name = site_name.replace(" ", "") + "_" + level + "_QC_Diurnal" + label + "ByMonth.png"
        figure_name = os.path.join("plots", file_name)
        fig.savefig(figure_name, format="png")
        # draw the plot on the screen
        plt.draw()
        mypause(0.5)
    plt.ioff()
    return

def plot_setup(cf, title):
    p = {}
    if "plot_path" in cf["Files"]:
        p["plot_path"] = os.path.join(cf["Files"]["plot_path"], cf["level"])
    else:
        p["plot_path"] = os.path.join("plots", cf["level"])
    p['PlotDescription'] = str(title)
    var_string = cf['Plots'][str(title)]['variables']
    p['SeriesList'] = pfp_cfg.cfg_string_to_list(var_string)
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
    if n == 0:
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
    # put this axis in the plot setup dictionary
    p["ts_ax_left"][n] = ts_ax_left
    # plot the data on this axis
    ts_ax_left.plot(xarray,yarray,'b-')
    # set the axes limits
    ts_ax_left.set_xlim(p['XAxMin'],p['XAxMax'])
    ts_ax_left.set_ylim(p['LYAxMin'],p['LYAxMax'])
    # check to see if this is the first graph
    if n == 0:
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
    Level = dsb.globalattributes['nc_level']
    PlotDescription = str(title)
    fig = plt.figure()
    fig.clf()
    fig.canvas.set_window_title(PlotDescription)
    plt.figtext(0.5,0.95,SiteName+': '+PlotDescription,ha='center',size=16)
    if "," in plt_cf['xseries']:
        XSeries = plt_cf['xseries'].split(",")
    else:
        XSeries = [plt_cf['xseries']]
    if "," in plt_cf['yseries']:
        YSeries = plt_cf['yseries'].split(",")
    else:
        YSeries = [plt_cf['yseries']]
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
    #fig.show()
    plt.draw()
    mypause(0.5)
    if "plot_path" in cf["Files"]:
        plot_path = os.path.join(cf["Files"]["plot_path"],Level)
    else:
        plot_path = "plots/"
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
    fname = os.path.join(plot_path, SiteName.replace(' ','')+'_'+Level+'_'+PlotDescription.replace(' ','')+'.png')
    fig.savefig(fname,format='png')

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
        xfit = numpy.ma.array([numpy.ma.min(x),numpy.ma.max(x)])
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
        a, _, _, _ = numpy.linalg.lstsq(x, y, rcond=-1)
        eqnstr = 'y = %.3fx'%(a)
        plt.text(0.5,0.875,eqnstr,fontsize=8,horizontalalignment='center',transform=ax.transAxes)
    return

def hrplot(x, y, sub=[1,1,1], title=None, xlabel=None, ylabel=None, colours=None, cmap=None,
           show_xtick_labels=True):
    plt.subplot(sub[0],sub[1],sub[2])
    if (y.all() is numpy.ma.masked):
        y = numpy.ma.zeros(len(y))
    if colours is not None:
        #cm = plt.cm.get_cmap("RdYlBu")
        #sc = plt.scatter(x,y,c=colours,cmap=cm)
        #plt.colorbar(sc)
        if cmap is not None:
            plt.scatter(x, y, c=colours, cmap=cmap)
        else:
            plt.scatter(x, y, c=colours)
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
    return

def tsplot(x, y, sub=[1,1,1], title=None, xlabel=None, ylabel=None, lineat=None,
           colours=None, cmap=None, vmin=None, vmax=None):
    """
    Purpose:
     Plot a time series of data with optional colouring of points and a colour bar.
    Author: PRI
    Date: Back in the day
    """
    axs = plt.subplot(sub[0],sub[1],sub[2])
    if (y.all() is numpy.ma.masked):
        y = numpy.ma.zeros(len(y))
    if ((colours is not None) and (cmap is not None) and
        (vmin is not None) and (vmax is not None)):
        ax = axs.scatter(x, y, c=colours, cmap=cmap, vmin=vmin, vmax=vmax)
        cbins = inset_axes(axs, width="10%", height="10%", loc="upper right")
        ticks = [0, 50, 100]
        plt.colorbar(ax, cax=cbins, orientation="horizontal", ticks=ticks)
    else:
        ax = axs.scatter(x, y)
    if lineat is not None:
        ax = axs.plot((x[0], x[-1]), (float(lineat), float(lineat)))
    axs.set_xlim([x[0], x[-1]])
    if title is not None:
        plt.title(title)
    if ylabel is not None:
        axs.yaxis.set_label_text(ylabel)
    if xlabel is not None:
        axs.xaxis.set_label_text(xlabel)
    if sub[2] != sub[0]:
        axs.set_xlabel('',visible=False)
        axs.tick_params(labelbottom=False)
    return

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
