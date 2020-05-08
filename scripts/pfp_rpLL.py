""" Routines for the Lasslop et al partitioning scheme."""
# standard modules
import datetime
import logging
import os
import warnings
# 3rd party modules
import matplotlib
import matplotlib.pyplot as plt
import numpy
from scipy.optimize import curve_fit, OptimizeWarning
# PFP modules
import constants as c
import pfp_cfg
import pfp_gui
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

def get_LL_params(ldt, Fsd, D, T, NEE, ER, LT_results, l6_info, output):
    # Lasslop as it was written in Lasslop et al (2010), mostly ...
    # Actually, the only intended difference is the window length and offset
    # Lasslop et al used window_length=4, window_offset=2
    # local pointers to entries in the info dictionary
    iel = l6_info["ERUsingLasslop"]
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

def get_LT_params(ldt, ER, T, l6_info, output, mode="verbose"):
    """
    Purpose:
     Returns rb and E0 for the Lloyd & Taylor respiration function.
    Usage:
    Author: PRI
    Date: April 2016
    """
    # local pointers to entries in the info dictionary
    iel = l6_info["ERUsingLasslop"]
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

def rpLL_createdict(cf, ds, l6_info, output, called_by, flag_code):
    """
    Purpose:
     Creates a dictionary in ds to hold information about estimating ecosystem
     respiration using the Lasslop method.
    Usage:
    Side effects:
    Author: PRI
    Date April 2016
    """
    nrecs = int(ds.globalattributes["nc_nrecs"])
    # make the L6 "description" attrubute for the target variable
    descr_level = "description_" + ds.globalattributes["nc_level"]
    # create the Lasslop settings directory
    if called_by not in l6_info.keys():
        l6_info[called_by] = {"outputs": {}, "info": {}, "gui": {}}
    # get the info section
    rpLL_createdict_info(cf, ds, l6_info[called_by], called_by)
    if ds.returncodes["value"] != 0:
        return
    # get the outputs section
    rpLL_createdict_outputs(cf, l6_info[called_by], output, called_by, flag_code)
    # create an empty series in ds if the output series doesn't exist yet
    Fc = pfp_utils.GetVariable(ds, l6_info[called_by]["info"]["source"])
    model_outputs = cf["EcosystemRespiration"][output][called_by].keys()
    for model_output in model_outputs:
        if model_output not in ds.series.keys():
            l6_info["RemoveIntermediateSeries"]["not_output"].append(model_output)
            # create an empty variable
            variable = pfp_utils.CreateEmptyVariable(model_output, nrecs)
            variable["Attr"]["long_name"] = "Ecosystem respiration"
            variable["Attr"]["drivers"] = l6_info[called_by]["outputs"][model_output]["drivers"]
            variable["Attr"][descr_level] = "Modeled by Lasslop et al. (2010)"
            variable["Attr"]["target"] = l6_info[called_by]["info"]["target"]
            variable["Attr"]["source"] = l6_info[called_by]["info"]["source"]
            variable["Attr"]["units"] = Fc["Attr"]["units"]
            pfp_utils.CreateVariable(ds, variable)
    # intermediate series to be deleted
    for item in ["alpha_LL", "beta_LL", "E0_LL", "k_LL", "rb_LL",
                 "NEE_LL_all", "GPP_LL_all"]:
        l6_info["RemoveIntermediateSeries"]["not_output"].append(item)
    return

def rpLL_createdict_info(cf, ds, erll, called_by):
    """
    Purpose:
    Usage:
    Side effects:
    Author: PRI
    Date: Back in the day
          June 2019 - modified for new l5_info structure
    """
    # reset the return message and code
    ds.returncodes["message"] = "OK"
    ds.returncodes["value"] = 0
    # time step
    time_step = int(ds.globalattributes["time_step"])
    # get the level of processing
    level = ds.globalattributes["nc_level"]
    # local pointer to the datetime series
    ldt = ds.series["DateTime"]["Data"]
    # add an info section to the info["solo"] dictionary
    erll["info"]["file_startdate"] = ldt[0].strftime("%Y-%m-%d %H:%M")
    erll["info"]["file_enddate"] = ldt[-1].strftime("%Y-%m-%d %H:%M")
    erll["info"]["startdate"] = ldt[0].strftime("%Y-%m-%d %H:%M")
    erll["info"]["enddate"] = ldt[-1].strftime("%Y-%m-%d %H:%M")
    erll["info"]["called_by"] = called_by
    erll["info"]["time_step"] = time_step
    erll["info"]["source"] = "Fc"
    erll["info"]["target"] = "ER"
    # check to see if this is a batch or an interactive run
    call_mode = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "call_mode", default="interactive")
    erll["info"]["call_mode"] = call_mode
    erll["gui"]["show_plots"] = False
    if call_mode.lower() == "interactive":
        erll["gui"]["show_plots"] = True
    # truncate to last date in Imports?
    truncate = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "TruncateToImports", default="Yes")
    erll["info"]["truncate_to_imports"] = truncate
    # number of records per day and maximum lags
    nperhr = int(float(60)/time_step + 0.5)
    erll["info"]["nperday"] = int(float(24)*nperhr + 0.5)
    erll["info"]["maxlags"] = int(float(12)*nperhr + 0.5)
    # get the plot path
    plot_path = pfp_utils.get_keyvaluefromcf(cf, ["Files"], "plot_path", default="./plots/")
    plot_path = os.path.join(plot_path, level, "")
    if not os.path.exists(plot_path):
        try:
            os.makedirs(plot_path)
        except OSError:
            msg = "Unable to create the plot path " + plot_path + "\n"
            msg = msg + "Press 'Quit' to edit the control file.\n"
            msg = msg + "Press 'Continue' to use the default path.\n"
            result = pfp_gui.MsgBox_ContinueOrQuit(msg, title="Warning: L6 plot path")
            if result.clickedButton().text() == "Quit":
                # user wants to edit the control file
                msg = " Quitting L6 to edit control file"
                logger.warning(msg)
                ds.returncodes["message"] = msg
                ds.returncodes["value"] = 1
            else:
                plot_path = "./plots/"
                cf["Files"]["plot_path"] = "./plots/"
    erll["info"]["plot_path"] = plot_path
    return

def rpLL_createdict_outputs(cf, erll, target, called_by, flag_code):
    level = cf["level"]
    eo = erll["outputs"]
    # loop over the outputs listed in the control file
    section = "EcosystemRespiration"
    outputs = cf[section][target][called_by].keys()
    for output in outputs:
        # create the dictionary keys for this series
        eo[output] = {}
        # get the target
        sl = [section, target, called_by, output]
        eo[output]["target"] = pfp_utils.get_keyvaluefromcf(cf, sl, "target", default=target)
        eo[output]["source"] = pfp_utils.get_keyvaluefromcf(cf, sl, "source", default="Fc")
        # add the flag_code
        eo[output]["flag_code"] = flag_code
        # list of drivers
        opt = pfp_utils.get_keyvaluefromcf(cf, sl, "drivers", default="Ta")
        eo[output]["drivers"] = pfp_cfg.cfg_string_to_list(opt)
        opt = pfp_utils.get_keyvaluefromcf(cf, sl, "step_size_days", default=5)
        eo[output]["step_size_days"] = int(opt)
        opt = pfp_utils.get_keyvaluefromcf(cf, sl, "window_size_days", default=15)
        eo[output]["window_size_days"] = int(opt)
        opt = pfp_utils.get_keyvaluefromcf(cf, sl, "output_plots", default="False")
        eo[output]["output_plots"] = (opt == "True")
        opt = pfp_utils.get_keyvaluefromcf(cf, sl, "fsd_threshold", default=10)
        eo[output]["fsd_threshold"] = int(opt)
        # fit statistics for plotting later on
        eo[output]["results"] = {"startdate":[],"enddate":[],"No. points":[],"r":[],
                                 "Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                                 "Avg (obs)":[],"Avg (LL)":[],
                                 "Var (obs)":[],"Var (LL)":[],"Var ratio":[],
                                 "m_ols":[],"b_ols":[]}
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

def rpLL_plot(pd, ds, output, drivers, target, l6_info, si=0, ei=-1):
    """ Plot the results of the Lasslop run. """
    iel = l6_info["ERUsingLasslop"]
    ieli = l6_info["ERUsingLasslop"]["info"]
    ielo = l6_info["ERUsingLasslop"]["outputs"]
    # get a local copy of the datetime series
    if ei==-1:
        dt = ds.series['DateTime']['Data'][si:]
    else:
        dt = ds.series['DateTime']['Data'][si:ei+1]
    xdt = numpy.array(dt)
    #Hdh, f, a = pfp_utils.GetSeriesasMA(ds, 'Hdh', si=si, ei=ei)
    Hdh = numpy.array([d.hour+(d.minute+d.second/float(60))/float(60) for d in xdt])
    # get the observed and modelled values
    obs, f, a = pfp_utils.GetSeriesasMA(ds, target, si=si, ei=ei)
    mod, f, a = pfp_utils.GetSeriesasMA(ds, output, si=si, ei=ei)
    # make the figure
    if iel["gui"]["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"], figsize=(13, 8))
    fig.clf()
    fig.canvas.set_window_title(target + " (LL): " + pd["startdate"] + " to " + pd["enddate"])
    plt.figtext(0.5, 0.95, pd["title"], ha='center', size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask, mod.mask)
    obs_mor = numpy.ma.array(obs, mask=mask)
    dstats = pfp_utils.get_diurnalstats(xdt, obs_mor, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'b-', label="Obs")
    # get the diurnal stats of all predictions
    dstats = pfp_utils.get_diurnalstats(xdt, mod, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'r-', label="LL(all)")
    mod_mor = numpy.ma.masked_where(numpy.ma.getmaskarray(obs) == True, mod, copy=True)
    dstats = pfp_utils.get_diurnalstats(xdt, mod_mor, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'g-', label="LL(obs)")
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
    ax2.set_xlabel(target + '_LL')
    # plot the best fit line
    coefs = numpy.ma.polyfit(numpy.ma.copy(mod), numpy.ma.copy(obs), 1)
    xfit = numpy.ma.array([numpy.ma.min(mod), numpy.ma.max(mod)])
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
    ielo[output]["results"]["Bias"].append(bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    plt.figtext(0.725, 0.225, 'No. points')
    plt.figtext(0.825, 0.225, str(numpoints))
    ielo[output]["results"]["No. points"].append(numpoints)
    plt.figtext(0.725, 0.200, 'No. filled')
    plt.figtext(0.825, 0.200, str(numfilled))
    plt.figtext(0.725, 0.175, 'Slope')
    plt.figtext(0.825, 0.175, str(pfp_utils.round2significant(coefs[0], 4)))
    ielo[output]["results"]["m_ols"].append(coefs[0])
    plt.figtext(0.725, 0.150, 'Offset')
    plt.figtext(0.825, 0.150, str(pfp_utils.round2significant(coefs[1], 4)))
    ielo[output]["results"]["b_ols"].append(coefs[1])
    plt.figtext(0.725, 0.125, 'r')
    plt.figtext(0.825, 0.125, str(pfp_utils.round2significant(r[0][1], 4)))
    ielo[output]["results"]["r"].append(r[0][1])
    plt.figtext(0.725, 0.100, 'RMSE')
    plt.figtext(0.825, 0.100, str(pfp_utils.round2significant(rmse, 4)))
    ielo[output]["results"]["RMSE"].append(rmse)
    var_obs = numpy.ma.var(obs)
    ielo[output]["results"]["Var (obs)"].append(var_obs)
    var_mod = numpy.ma.var(mod)
    ielo[output]["results"]["Var (LL)"].append(var_mod)
    ielo[output]["results"]["Var ratio"].append(var_obs/var_mod)
    ielo[output]["results"]["Avg (obs)"].append(numpy.ma.average(obs))
    ielo[output]["results"]["Avg (LL)"].append(numpy.ma.average(mod))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"], pd["ts_bottom"], pd["ts_width"], pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    #ts_axes[0].plot(xdt,obs,'b.',xdt,mod,'r-')
    ts_axes[0].scatter(xdt, obs, c=Hdh)
    ts_axes[0].plot(xdt, mod, 'r-')
    plt.axhline(0)
    ts_axes[0].set_xlim(xdt[0], xdt[-1])
    TextStr = target + '_obs (' + ds.series[target]['Attr']['units'] + ')'
    ts_axes[0].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[0].transAxes)
    TextStr = output + '(' + ds.series[output]['Attr']['units'] + ')'
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
    if not os.path.exists(ieli["plot_path"]):
        os.makedirs(ieli["plot_path"])
    figname = ieli["plot_path"] + pd["site_name"].replace(" ","") + "_LL_" + pd["label"]
    figname = figname + "_" + sdt + "_" + edt + '.png'
    fig.savefig(figname, format='png')
    # draw the plot on the screen
    if iel["gui"]["show_plots"]:
        plt.draw()
        #plt.pause(1)
        mypause(1)
        plt.ioff()
    else:
        plt.close(fig)
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
