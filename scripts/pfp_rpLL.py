""" Routines for the Lasslop et al partitioning scheme."""
# standard modules
import ast
import datetime
import logging
import os
import warnings
# 3rd party modules
import matplotlib.pyplot as plt
import numpy
from scipy.optimize import curve_fit, OptimizeWarning
# PFP modules
import constants as c
import pfp_cfg
import pfp_utils

warnings.simplefilter("ignore", OptimizeWarning)
logger = logging.getLogger("pfp_log")

def ER_LloydTaylor(T,rb,E0):
    return rb*numpy.exp(E0*(1/(c.Tref-c.T0)-1/(T-c.T0)))

def ER_LloydTaylor_fixedE0(data,rb):
    T = data[0]
    E0 = data[1]
    return rb*numpy.exp(E0*(1/(c.Tref-c.T0)-1/(T-c.T0)))

def NEE_RHLRC_D(data,alpha,beta,k,D0,rb,E0):
    Fsd = data["Fsd"]
    D = data["D"]
    T = data["T"]
    NEE = -1*GPP_RHLRC_D(Fsd,D,alpha,beta,k,D0) + ER_LloydTaylor(T,rb,E0)
    return NEE

def GPP_RHLRC_D(Fsd,D,alpha,beta,k,D0):
    beta = beta*SHD_func_Lasslop(D,k,D0)
    GPP = alpha*beta*Fsd/(alpha*Fsd+beta)
    return GPP

def SHD_func_Lasslop(D,k,D0):
    SHD_func = numpy.ones(len(D))
    idx = numpy.where(D>D0)[0]
    if isinstance(k,numpy.ndarray):
        SHD_func[idx] = numpy.exp(-k[idx]*(D[idx]-D0))
    else:
        SHD_func[idx] = numpy.exp(-k*(D[idx]-D0))
    return SHD_func

def interp_params(param_rslt_array):

    def do_interp(array_1D):
        xp = numpy.arange(len(arr))
        fp = array_1D[:]
        nan_index = numpy.isnan(fp)
        fp[nan_index] = numpy.interp(xp[nan_index], xp[~nan_index], fp[~nan_index])
        return fp

    arr = param_rslt_array.copy()
    num_vars = numpy.shape(arr)
    if len(num_vars) == 1:
        arr = do_interp(arr)
    else:
        num_vars = num_vars[1]
        for i in range(num_vars):
            arr[:, i] = do_interp(arr[:, i])

    return arr

def get_LL_params(ldt, Fsd, D, T, NEE, ER, LT_results, info, output):
    # Lasslop as it was written in Lasslop et al (2010), mostly ...
    # Actually, the only intended difference is the window length and offset
    # Lasslop et al used window_length=4, window_offset=2
    # local pointers to entries in the info dictionary
    iel = info["er"]["lasslop"]
    ielo = iel["outputs"]
    ieli = iel["info"]
    # window and step sizes
    window_size_days = ielo[output]["window_size_days"]
    step_size_days = ielo[output]["step_size_days"]
    # initialise results, missed dates and prior dictionaries
    mta = numpy.array([])
    LL_results = {"start_date": mta, "mid_date": mta, "end_date": mta,
                  "alpha": mta, "beta": mta, "k": mta, "rb": mta,
                  "alpha_low": mta, "rb_low": mta, "rb_prior": mta, "E0": mta}
    LL_prior = {"rb":1.0, "alpha":0.01, "beta":10, "k":0}
    LL_fixed = {"D0":1}
    D0 = LL_fixed["D0"]
    drivers = {}
    start_date = ldt[0]
    last_date = ldt[-1]
    end_date = start_date+datetime.timedelta(days=window_size_days)
    while end_date <= last_date:
        sub_results = {"RMSE":[], "alpha":[], "beta":[], "k":[], "rb":[]}
        si = pfp_utils.GetDateIndex(ldt, str(start_date), ts=ieli["time_step"])
        ei = pfp_utils.GetDateIndex(ldt, str(end_date), ts=ieli["time_step"])
        drivers["Fsd"] = numpy.ma.compressed(Fsd[si:ei+1])
        drivers["D"] = numpy.ma.compressed(D[si:ei+1])
        drivers["T"] = numpy.ma.compressed(T[si:ei+1])
        NEEsub = numpy.ma.compressed(NEE[si:ei+1])
        ERsub = numpy.ma.compressed(ER[si:ei+1])
        mid_date = start_date+(end_date-start_date)/2
        # get the value of E0 for the period closest to the mid-point of this period
        diffs = [abs(dt-mid_date) for dt in LT_results["mid_date"]]
        val, idx = min((val, idx) for (idx, val) in enumerate(diffs))
        LL_results["E0"] = numpy.append(LL_results["E0"], LT_results["E0_int"][idx])
        LL_results["start_date"] = numpy.append(LL_results["start_date"], start_date)
        LL_results["mid_date"] = numpy.append(LL_results["mid_date"], mid_date)
        LL_results["end_date"] = numpy.append(LL_results["end_date"], end_date)
        if len(NEEsub) >= 10:
            # alpha and rb from linear fit between NEE and Fsd at low light levels
            idx = numpy.where(drivers["Fsd"] < 100)[0]
            if len(idx) >= 2:
                alpha_low, rb_low = numpy.polyfit(drivers["Fsd"][idx], NEEsub[idx], 1)
            else:
                alpha_low, rb_low = numpy.nan, numpy.nan
            if len(ERsub) >= 10: LL_prior["rb"] = numpy.mean(ERsub)
            for bm in [0.5, 1,2]:
                LL_prior["beta"] = numpy.abs(numpy.percentile(NEEsub, 3)-numpy.percentile(NEEsub, 97))
                LL_prior["beta"] = bm*LL_prior["beta"]
                E0 = LL_results["E0"][-1]
                p0 = [LL_prior["alpha"],LL_prior["beta"],LL_prior["k"],LL_prior["rb"]]
                try:
                    fopt = lambda x,alpha,beta,k,rb:NEE_RHLRC_D(x,alpha,beta,k,D0,rb,E0)
                    popt,pcov = curve_fit(fopt,drivers,NEEsub,p0=p0)
                    alpha,beta,k,rb = popt[0],popt[1],popt[2],popt[3]
                    last_alpha_OK = True
                except RuntimeError:
                    alpha,beta,k,rb = numpy.nan,numpy.nan,numpy.nan,numpy.nan
                    last_alpha_OK = False
                # QC the parameters
                # k first
                if numpy.isnan(k) or k<0 or k>2:
                    k = 0
                    try:
                        p0 = [LL_prior["alpha"],LL_prior["beta"],LL_prior["rb"]]
                        fopt = lambda x,alpha,beta,rb:NEE_RHLRC_D(x,alpha,beta,k,D0,rb,E0)
                        popt,pcov = curve_fit(fopt,drivers,NEEsub,p0=p0)
                        alpha,beta,rb = popt[0],popt[1],popt[2]
                        last_alpha_OK = True
                    except RuntimeError:
                        alpha,beta,k,rb = numpy.nan,numpy.nan,numpy.nan,numpy.nan
                        last_alpha_OK = False
                # then alpha
                if numpy.isnan(alpha) or alpha<0 or alpha>0.22:
                    if last_alpha_OK==True and len(LL_results["alpha"]) > 0:
                        alpha = LL_results["alpha"][-1]
                    else:
                        alpha = 0
                    try:
                        p0 = [LL_prior["beta"],LL_prior["k"],LL_prior["rb"]]
                        fopt = lambda x,beta,k,rb:NEE_RHLRC_D(x,alpha,beta,k,D0,rb,E0)
                        popt,pcov = curve_fit(fopt,drivers,NEEsub,p0=p0)
                        beta,k,rb = popt[0],popt[1],popt[2]
                    except RuntimeError:
                        alpha,beta,k,rb = numpy.nan,numpy.nan,numpy.nan,numpy.nan
                # then beta
                if beta<0:
                    beta = 0
                    try:
                        p0 = [LL_prior["alpha"],LL_prior["k"],LL_prior["rb"]]
                        fopt = lambda x,alpha,k,rb:NEE_RHLRC_D(x,alpha,beta,k,D0,rb,E0)
                        popt,pcov = curve_fit(fopt,drivers,NEEsub,p0=p0)
                        alpha,k,rb = popt[0],popt[1],popt[2]
                    except RuntimeError:
                        alpha,beta,k,rb = numpy.nan,numpy.nan,numpy.nan,numpy.nan
                elif beta>250:
                    alpha,beta,k,rb = numpy.nan,numpy.nan,numpy.nan,numpy.nan
                # and finally rb
                if rb<0:
                    alpha,beta,k,rb = numpy.nan,numpy.nan,numpy.nan,numpy.nan
                # now get the RMSE for this set of parameters
                if not numpy.isnan(alpha) and not numpy.isnan(beta) and not numpy.isnan(k) and not numpy.isnan(rb):
                    NEEest = NEE_RHLRC_D(drivers,alpha,beta,k,D0,rb,E0)
                    sub_results["RMSE"].append(numpy.sqrt(numpy.mean((NEEsub-NEEest)**2)))
                    sub_results["alpha"].append(alpha)
                    sub_results["beta"].append(beta)
                    sub_results["k"].append(k)
                    sub_results["rb"].append(rb)
            # now find the minimum RMSE and the set of parameters for the minimum
            if len(sub_results["RMSE"])!=0:
                min_RMSE = min(sub_results["RMSE"])
                idx = sub_results["RMSE"].index(min_RMSE)
                LL_results["alpha"] = numpy.append(LL_results["alpha"],sub_results["alpha"][idx])
                LL_results["alpha_low"] = numpy.append(LL_results["alpha_low"],float(-1)*alpha_low)
                LL_results["rb"] = numpy.append(LL_results["rb"],sub_results["rb"][idx])
                LL_results["rb_low"] = numpy.append(LL_results["rb_low"],rb_low)
                LL_results["rb_prior"] = numpy.append(LL_results["rb_prior"],LL_prior["rb"])
                LL_results["beta"] = numpy.append(LL_results["beta"],sub_results["beta"][idx])
                LL_results["k"] = numpy.append(LL_results["k"],sub_results["k"][idx])
            else:
                LL_results["alpha"] = numpy.append(LL_results["alpha"],numpy.nan)
                LL_results["alpha_low"] = numpy.append(LL_results["alpha_low"],float(-1)*alpha_low)
                LL_results["rb"] = numpy.append(LL_results["rb"],numpy.nan)
                LL_results["rb_low"] = numpy.append(LL_results["rb_low"],rb_low)
                LL_results["rb_prior"] = numpy.append(LL_results["rb_prior"],LL_prior["rb"])
                LL_results["beta"] = numpy.append(LL_results["beta"],numpy.nan)
                LL_results["k"] = numpy.append(LL_results["k"],numpy.nan)
        else:
            LL_results["alpha"] = numpy.append(LL_results["alpha"],numpy.nan)
            LL_results["alpha_low"] = numpy.append(LL_results["alpha_low"],numpy.nan)
            LL_results["rb"] = numpy.append(LL_results["rb"],numpy.nan)
            LL_results["rb_low"] = numpy.append(LL_results["rb_low"],numpy.nan)
            LL_results["rb_prior"] = numpy.append(LL_results["rb_prior"],LL_prior["rb"])
            LL_results["beta"] = numpy.append(LL_results["beta"],numpy.nan)
            LL_results["k"] = numpy.append(LL_results["k"],numpy.nan)
        # update the start and end datetimes
        start_date = start_date+datetime.timedelta(days=window_size_days)
        end_date = start_date+datetime.timedelta(days=step_size_days)
    LL_results["D0"] = D0
    return LL_results

def get_LT_params(ldt, ER, T, info, output, mode="verbose"):
    """
    Purpose:
     Returns rb and E0 for the Lloyd & Taylor respiration function.
    Usage:
    Author: PRI
    Date: April 2016
    """
    # local pointers to entries in the info dictionary
    iel = info["er"]["lasslop"]
    ielo = iel["outputs"]
    ieli = iel["info"]
    # window and step sizes
    window_step_size = ielo[output]["window_size_days"]
    step_size_days = ielo[output]["step_size_days"]
    # initialise results, missed dates and prior dictionaries
    mta = numpy.array([])
    LT_results = {"start_date": mta, "mid_date": mta, "end_date": mta,
                  "rb": mta, "E0": mta, "rb_prior": mta, "E0_prior": mta}
    missed_dates = {"start_date":[], "end_date":[]}
    LT_prior = {"rb": 1.0, "E0": 100}
    # get the start and end date
    start_date = ldt[0]
    last_date = ldt[-1]
    end_date = start_date+datetime.timedelta(days=ielo[output]["window_size_days"])
    last_E0_OK = False
    while end_date <= last_date:
        LT_results["start_date"] = numpy.append(LT_results["start_date"], start_date)
        LT_results["mid_date"] = numpy.append(LT_results["mid_date"], start_date+(end_date-start_date)/2)
        LT_results["end_date"] = numpy.append(LT_results["end_date"], end_date)
        si = pfp_utils.GetDateIndex(ldt, str(start_date), ts=ieli["time_step"])
        ei = pfp_utils.GetDateIndex(ldt, str(end_date), ts=ieli["time_step"])
        Tsub = numpy.ma.compressed(T[si: ei+1])
        ERsub = numpy.ma.compressed(ER[si: ei+1])
        if len(ERsub) >= 10:
            LT_prior["rb"] = numpy.mean(ERsub)
            p0 = [LT_prior["rb"], LT_prior["E0"]]
            try:
                popt, pcov = curve_fit(ER_LloydTaylor, Tsub, ERsub, p0=p0)
            except RuntimeError:
                missed_dates["start_date"].append(start_date)
                missed_dates["end_date"].append(end_date)
            # QC E0 results
            if popt[1] < 50 or popt[1] > 400:
                if last_E0_OK:
                    popt[1] = LT_results["E0"][-1]
                    last_E0_OK = False
                else:
                    if popt[1] <50: popt[1] = float(50)
                    if popt[1] > 400: popt[1] = float(400)
                    last_E0_OK = False
                # now recalculate rb
                p0 = LT_prior["rb"]
                if numpy.isnan(popt[1]): popt[1] = float(50)
                E0 = numpy.ones(len(Tsub))*float(popt[1])
                popt1, pcov1 = curve_fit(ER_LloydTaylor_fixedE0, [Tsub,E0], ERsub, p0=p0)
                popt[0] = popt1[0]
            else:
                last_E0_OK = True
            # QC rb results
            if popt[0] < 0: popt[0] = float(0)
            LT_results["rb"] = numpy.append(LT_results["rb"], popt[0])
            LT_results["E0"] = numpy.append(LT_results["E0"], popt[1])
            LT_results["rb_prior"] = numpy.append(LT_results["rb_prior"], numpy.mean(ERsub))
            LT_results["E0_prior"] = numpy.append(LT_results["E0_prior"], LT_prior["E0"])
        else:
            LT_results["rb"] = numpy.append(LT_results["rb"], numpy.nan)
            LT_results["E0"] = numpy.append(LT_results["E0"], numpy.nan)
            LT_results["rb_prior"] = numpy.append(LT_results["rb_prior"], numpy.nan)
            LT_results["E0_prior"] = numpy.append(LT_results["E0_prior"], numpy.nan)
        start_date = start_date+datetime.timedelta(days=ielo[output]["window_size_days"])
        end_date = start_date+datetime.timedelta(days=ielo[output]["step_size_days"])
    #    start_date = end_date
    #    end_date = start_date+dateutil.relativedelta.relativedelta(years=1)
    if mode == "verbose":
        if len(missed_dates["start_date"]) != 0:
            msg = " No solution found for the following dates:"
            logger.warning(msg)
            for sd, ed in zip(missed_dates["start_date"], missed_dates["end_date"]):
                msg = "  " + str(sd) + " to " + str(ed)
                logger.warning(msg)
    return LT_results

def plot_LLparams(LT_results,LL_results):
    fig, axs = plt.subplots(4,1,sharex=True,figsize=(24,6))
    axs[0].plot(LT_results["mid_date"],LT_results["rb"],'bo')
    axs[0].plot(LL_results["mid_date"],LL_results["rb"],'ro')
    axs[0].plot(LL_results["mid_date"],LL_results["rb_low"],'go')
    axs[0].plot(LL_results["mid_date"],LL_results["rb_prior"],'yo')
    axs[0].set_ylabel("rb")
    axs[1].plot(LL_results["mid_date"],LL_results["alpha"],'bo')
    axs[1].plot(LL_results["mid_date"],LL_results["alpha_low"],'ro')
    axs[1].set_ylabel("alpha")
    axs[2].plot(LL_results["mid_date"],LL_results["beta"],'bo')
    axs[2].set_ylabel("beta")
    axs[3].plot(LL_results["mid_date"],LL_results["k"],'bo')
    axs[3].set_ylabel("k")
    plt.tight_layout()
    plt.show()

def plot_LTparams_ER(ldt,ER,ER_LT,LT_results):
    fig, axs = plt.subplots(3,1,sharex=True,figsize=(24,6))
    axs[0].plot(LT_results["mid_date"],LT_results["rb"],'bo')
    axs[0].set_ylabel("rb (umol/m2/s)")
    axs[1].plot(LT_results["mid_date"],LT_results["E0"],'bo')
    axs[1].set_ylabel("E0 (C)")
    axs[2].plot(ldt,ER,'bo')
    axs[2].plot(ldt,ER_LT,'r--')
    axs[2].axhline(y=0,linewidth=4,color="r")
    axs[2].set_ylabel("ER (umol/m2/s)")
    plt.tight_layout()
    plt.draw()

def rpLL_createdict(cf, ds, info, label):
    """
    Purpose:
     Creates a dictionary in ds to hold information about estimating ecosystem
     respiration using the Lasslop method.
    Usage:
    Author: PRI
    Date April 2016
    """
    # get the target
    target = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingLasslop"], "target", default="ER")
    # check that none of the drivers have missing data
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingLasslop"], "drivers", default="Ta")
    drivers = pfp_cfg.cfg_string_to_list(opt)
    for driver in drivers:
        data, flag, attr = pfp_utils.GetSeriesasMA(ds, driver)
        if numpy.ma.count_masked(data) != 0:
            msg = "ERUsingLasslop: driver " + driver + " contains missing data, skipping target " + target
            logger.error(msg)
            return
    # create the dictionary keys for this series
    if "lasslop" not in info:
        info["lasslop"] = {"outputs": {label: {}}}
    ilol = info["lasslop"]["outputs"][label]
    # target series name
    ilol["target"] = target
    # list of drivers
    ilol["drivers"] = drivers
    # source to use as CO2 flux
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingLasslop"], "source", default="Fc")
    ilol["source"] = opt
    # name of output series in ds
    output = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingLasslop"], "output", default="ER_LL_all")
    ilol["output"] = output
    # results of best fit for plotting later on
    ilol["results"] = {"startdate":[], "enddate":[], "No. points":[], "r":[],
                       "Bias":[], "RMSE":[], "Frac Bias":[], "NMSE":[],
                       "Avg (obs)":[], "Avg (LL)":[],
                       "Var (obs)":[], "Var (LL)":[], "Var ratio":[],
                       "m_ols":[], "b_ols":[]}
    # step size
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingLasslop"], "step_size_days", default=5)
    ilol["step_size_days"] = int(opt)
    # window size
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingLasslop"], "window_size_days", default=15)
    ilol["window_size_days"] = int(opt)
    # Fsd day/night threshold
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "ERUsingLasslop"], "fsd_threshold", default=10)
    ilol["fsd_threshold"] = float(opt)
    # create an empty series in ds if the output series doesn't exist yet
    if ilol["output"] not in ds.series.keys():
        data, flag, attr = pfp_utils.MakeEmptySeries(ds, ilol["output"])
        pfp_utils.CreateSeries(ds, ilol["output"], data, flag, attr)
    # create the merge directory in the data structure
    if "merge" not in info:
        info["merge"] = {}
    if "standard" not in info["merge"].keys():
        info["merge"]["standard"] = {}
    # create the dictionary keys for this series
    info["merge"]["standard"][label] = {}
    # output series name
    info["merge"]["standard"][label]["output"] = label
    # source
    opt = pfp_utils.get_keyvaluefromcf(cf, ["ER", label, "MergeSeries"], "Source", default="ER,ER_LL_all")
    info["merge"]["standard"][label]["source"] = pfp_cfg.cfg_string_to_list(opt)
    # create an empty series in ds if the output series doesn't exist yet
    if info["merge"]["standard"][label]["output"] not in ds.series.keys():
        data, flag, attr = pfp_utils.MakeEmptySeries(ds, info["merge"]["standard"][label]["output"])
        pfp_utils.CreateSeries(ds, info["merge"]["standard"][label]["output"], data, flag, attr)
    return

def rpLL_initplot(**kwargs):
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

def rpLL_plot(pd, ds, series, drivers, targetlabel, outputlabel, info, si=0, ei=-1):
    """ Plot the results of the Lasslop run. """
    ieli = info["er"]["lasslop"]["info"]
    ielo = info["er"]["lasslop"]["outputs"]
    # get a local copy of the datetime series
    if ei==-1:
        dt = ds.series['DateTime']['Data'][si:]
    else:
        dt = ds.series['DateTime']['Data'][si:ei+1]
    xdt = numpy.array(dt)
    Hdh, f, a = pfp_utils.GetSeriesasMA(ds, 'Hdh', si=si, ei=ei)
    # get the observed and modelled values
    obs, f, a = pfp_utils.GetSeriesasMA(ds, targetlabel, si=si, ei=ei)
    mod, f, a = pfp_utils.GetSeriesasMA(ds, outputlabel, si=si, ei=ei)
    # make the figure
    if info["er"]["lasslop"]["info"]["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"], figsize=(13, 8))
    fig.clf()
    fig.canvas.set_window_title(targetlabel + " (LL): " + pd["startdate"] + " to " + pd["enddate"])
    plt.figtext(0.5, 0.95, pd["title"], ha='center', size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask, mod.mask)
    obs_mor = numpy.ma.array(obs, mask=mask)
    dstats = pfp_utils.get_diurnalstats(dt, obs_mor, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'b-', label="Obs")
    # get the diurnal stats of all predictions
    dstats = pfp_utils.get_diurnalstats(dt, mod, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'r-', label="LL(all)")
    mod_mor = numpy.ma.masked_where(numpy.ma.getmaskarray(obs) == True, mod, copy=True)
    dstats = pfp_utils.get_diurnalstats(dt, mod_mor, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'g-', label="LL(obs)")
    plt.xlim(0, 24)
    plt.xticks([0, 6, 12, 18, 24])
    ax1.set_ylabel(targetlabel)
    ax1.set_xlabel('Hour')
    ax1.legend(loc='upper right', frameon=False, prop={'size':8})
    # XY plot of the 30 minute data
    rect2 = [0.40, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax2 = plt.axes(rect2)
    ax2.plot(mod, obs, 'b.')
    ax2.set_ylabel(targetlabel + '_obs')
    ax2.set_xlabel(targetlabel + '_LL')
    # plot the best fit line
    coefs = numpy.ma.polyfit(numpy.ma.copy(mod), numpy.ma.copy(obs), 1)
    xfit = numpy.ma.array([numpy.ma.minimum(mod), numpy.ma.maximum(mod)])
    yfit = numpy.polyval(coefs, xfit)
    r = numpy.ma.corrcoef(mod, obs)
    ax2.plot(xfit, yfit, 'r--', linewidth=3)
    eqnstr = 'y = %.3fx + %.3f, r = %.3f'%(coefs[0], coefs[1], r[0][1])
    ax2.text(0.5, 0.875, eqnstr, fontsize=8, horizontalalignment='center', transform=ax2.transAxes)
    # write the fit statistics to the plot
    numpoints = numpy.ma.count(obs)
    numfilled = numpy.ma.count(mod)-numpy.ma.count(obs)
    diff = mod - obs
    bias = numpy.ma.average(diff)
    ielo[series]["results"]["Bias"].append(bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    plt.figtext(0.725, 0.225, 'No. points')
    plt.figtext(0.825, 0.225, str(numpoints))
    ielo[series]["results"]["No. points"].append(numpoints)
    plt.figtext(0.725, 0.200, 'No. filled')
    plt.figtext(0.825, 0.200, str(numfilled))
    plt.figtext(0.725, 0.175, 'Slope')
    plt.figtext(0.825, 0.175, str(pfp_utils.round2sig(coefs[0], sig=4)))
    ielo[series]["results"]["m_ols"].append(coefs[0])
    plt.figtext(0.725, 0.150, 'Offset')
    plt.figtext(0.825, 0.150, str(pfp_utils.round2sig(coefs[1], sig=4)))
    ielo[series]["results"]["b_ols"].append(coefs[1])
    plt.figtext(0.725, 0.125, 'r')
    plt.figtext(0.825, 0.125, str(pfp_utils.round2sig(r[0][1], sig=4)))
    ielo[series]["results"]["r"].append(r[0][1])
    plt.figtext(0.725, 0.100, 'RMSE')
    plt.figtext(0.825, 0.100, str(pfp_utils.round2sig(rmse, sig=4)))
    ielo[series]["results"]["RMSE"].append(rmse)
    var_obs = numpy.ma.var(obs)
    ielo[series]["results"]["Var (obs)"].append(var_obs)
    var_mod = numpy.ma.var(mod)
    ielo[series]["results"]["Var (LL)"].append(var_mod)
    ielo[series]["results"]["Var ratio"].append(var_obs/var_mod)
    ielo[series]["results"]["Avg (obs)"].append(numpy.ma.average(obs))
    ielo[series]["results"]["Avg (LL)"].append(numpy.ma.average(mod))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"], pd["ts_bottom"], pd["ts_width"], pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    #ts_axes[0].plot(xdt,obs,'b.',xdt,mod,'r-')
    ts_axes[0].scatter(xdt, obs, c=Hdh)
    ts_axes[0].plot(xdt, mod, 'r-')
    plt.axhline(0)
    ts_axes[0].set_xlim(xdt[0], xdt[-1])
    TextStr = targetlabel + '_obs (' + ds.series[targetlabel]['Attr']['units'] + ')'
    ts_axes[0].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[0].transAxes)
    TextStr = outputlabel + '(' + ds.series[outputlabel]['Attr']['units'] + ')'
    ts_axes[0].text(0.85, 0.85, TextStr, color='r', horizontalalignment='right', transform=ts_axes[0].transAxes)
    for ThisOne, i in zip(drivers, range(1, pd["nDrivers"] + 1)):
        this_bottom = pd["ts_bottom"] + i*pd["ts_height"]
        rect = [pd["margin_left"], this_bottom, pd["ts_width"], pd["ts_height"]]
        ts_axes.append(plt.axes(rect, sharex=ts_axes[0]))
        data, flag, attr = pfp_utils.GetSeriesasMA(ds, ThisOne, si=si, ei=ei)
        data_notgf = numpy.ma.masked_where(flag != 0, data)
        data_gf = numpy.ma.masked_where(flag == 0, data)
        ts_axes[i].plot(xdt, data_notgf, 'b-')
        ts_axes[i].plot(xdt, data_gf, 'r-')
        plt.setp(ts_axes[i].get_xticklabels(), visible=False)
        TextStr = ThisOne + '(' + ds.series[ThisOne]['Attr']['units'] + ')'
        ts_axes[i].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[i].transAxes)
    # save a hard copy of the plot
    sdt = xdt[0].strftime("%Y%m%d")
    edt = xdt[-1].strftime("%Y%m%d")
    plot_path = os.path.join(info["er"]["lasslop"]["info"]["plot_path"], "L6", "")
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
    figname = plot_path + pd["site_name"].replace(" ","") + "_LL_" + pd["label"]
    figname = figname + "_" + sdt + "_" + edt + '.png'
    fig.savefig(figname, format='png')
    # draw the plot on the screen
    if ieli["show_plots"]:
        plt.draw()
        plt.pause(1)
        plt.ioff()
    else:
        plt.close(fig)
        plt.ion()
