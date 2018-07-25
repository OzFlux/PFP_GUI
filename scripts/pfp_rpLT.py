import ast
import calendar
import constants as c
import datetime
import logging
import numpy
import matplotlib.pyplot as plt
import os
import pfp_utils
import scipy
import sys
import pdb

logger = logging.getLogger("pfp_log")

# code to integrate Ian's code into OzFluxQC
#def apply_turbulence_filter(data_dict,indicator):
    #data_dict["NEE"] = numpy.where(indicator==0,numpy.nan,data_dict["NEE"])

def get_configs_dict(cf,ds):
#    configs_dict = {'nan_value': -9999,
#                    'minimum_temperature_spread': 5,
#                    'step_size_days': 5,
#                    'window_size_days': 15,
#                    'min_pct_annual': 30,
#                    'min_pct_noct_window': 20,
#                    'min_pct_day_window': 50,
#                    'output_plots': False,
#                    'measurement_interval': 0.5,
#                    'QC_accept_code': 0,
#                    'plot_output_path': '/home/imchugh/Documents'}
    configs_dict = {}
    configs_dict["nan_value"] = int(c.missing_value)
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "minimum_temperature_spread",default=5)
    configs_dict["minimum_temperature_spread"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "step_size_days",default=5)
    configs_dict["step_size_days"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "window_size_days",default=15)
    configs_dict["window_size_days"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "minimum_percent_annual",default=30)
    configs_dict["minimum_pct_annual"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "minimum_percent_noct_window",default=20)
    configs_dict["minimum_pct_noct_window"] = int(opt)
    #opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     #"minimum_percent_day_window",
                                     #default=50)
    #configs_dict["minimum_pct_day_window"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "output_plots",default="False")
    configs_dict["output_plots"] = (opt=="True")
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "show_plots",default="False")
    configs_dict["show_plots"] = (opt=="True")
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "target",default="ER")
    configs_dict["target"] = str(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "drivers",default="['Ta']")
    configs_dict["drivers"] = ast.literal_eval(opt)[0]
    opt = pfp_utils.get_keyvaluefromcf(cf,["ER","ER_LT","ERUsingLloydTaylor"],
                                     "output",default="ER_LT_all")
    configs_dict["output_label"] = opt
    configs_dict["output_results"] = True
    ts = int(ds.globalattributes["time_step"])
    configs_dict["measurement_interval"] = float(ts)/60.0
    configs_dict["QC_accept_code"] = 0
    opt = pfp_utils.get_keyvaluefromcf(cf,["Files"],"plot_path",default="plots/")
    configs_dict["output_path"] = os.path.join(opt,"respiration/")
    return configs_dict

def get_data_dict(ds,configs_dict):
    data = {}
    # NOTE: series are ndarrays not masked arrays
    Fc,Fc_flag,a = pfp_utils.GetSeries(ds,"Fc")
    target = configs_dict["target"]
    ER,ER_flag,a = pfp_utils.GetSeries(ds,target)
    Fsd,Fsd_flag,a = pfp_utils.GetSeries(ds,"Fsd")
    T_label = configs_dict["drivers"]
    T,T_flag,a = pfp_utils.GetSeries(ds,T_label)
    VPD,VPD_flag,a = pfp_utils.GetSeries(ds,"VPD")
    ustar,ustar_flag,a = pfp_utils.GetSeries(ds,"ustar")
    # replace c.missing_value with numpy.nan
    Fc = numpy.where((Fc_flag!=0)|(Fc==c.missing_value),
                     numpy.nan,Fc)
    ustar = numpy.where((ustar_flag!=0)|(ustar==c.missing_value),
                        numpy.nan,ustar)
    ER = numpy.where((ER_flag!=0)|(ER==c.missing_value),
                     numpy.nan,ER)
    #Fsd = numpy.where((Fsd_flag!=0)|(Fsd==c.missing_value),
                      #numpy.nan,Fsd)
    #T = numpy.where((T_flag!=0)|(T==c.missing_value),
                    #numpy.nan,T)
    #VPD = numpy.where((VPD_flag!=0)|(VPD==c.missing_value),
                      #numpy.nan,VPD)
    # put the data in the dictionary
    #data["NEE"] = Fc
    data["NEE"] = ER
    data["PAR"] = Fsd*0.46*4.6
    data["TempC"] = T
    data["VPD"] = VPD
    data["ustar"] = ustar
    data["date_time"] = numpy.array(ds.series["DateTime"]["Data"])
    return data

# code from dark_T_response_functions.py
def TRF(data_dict, Eo, rb):
    return rb * numpy.exp(Eo * (1 / (10 + 46.02) - 1 / (data_dict['TempC'] + 46.02)))

def optimise_rb(data_dict, params_dict):

    # Initialise error state variable
    error_state = 0

    # Get drivers and response
    drivers_dict = {driver: data_dict[driver] for driver in ['TempC']}
    response_array = data_dict['NEE']

    try:
        params = scipy.optimize.curve_fit(lambda x, b:
                           TRF(x, params_dict['Eo_default'], b),
                           drivers_dict,
                           response_array,
                           p0 = [params_dict['rb_prior']])[0]
    except RuntimeError:
        params = [numpy.nan]

    # If negative rb returned, set to nan
    if params[0] < 0:
        error_state = 9
        params = [numpy.nan]

    return params, error_state

# code from Partition_NEE.py
def get_dates(datetime_array, configs_dict):

    # Assign configs to local vars
    window = configs_dict['window_size_days']

    # Create a series of continuous whole day dates that will be used for output
    # (parameter series will be interpolated between window centres)
    start_date = datetime_array[0].date()
    end_date = datetime_array[-1].date()
    num_days = (end_date - start_date).days + 1 # Add 1 so is inclusive of both end members
    all_dates_array = numpy.array([start_date + datetime.timedelta(i) for i in xrange(num_days)])

    # Create a shifted array
    shift_mins = 60 * configs_dict['measurement_interval']
    shift_datetime_array = datetime_array - datetime.timedelta(minutes = shift_mins)

    # Check that first and last days are complete and revise start and end dates if required
    temp_date = datetime.datetime.combine((shift_datetime_array[0] + datetime.timedelta(1)).date(),
                                    datetime.datetime.min.time())
    num_obs = len(numpy.where(shift_datetime_array < temp_date)[0])
    if num_obs < 24 * (1 / configs_dict['measurement_interval']):
        start_date = start_date + datetime.timedelta(1)
    temp_date = datetime.datetime.combine(shift_datetime_array[-1].date(),
                                    datetime.datetime.min.time())
    num_obs = len(numpy.where(shift_datetime_array >= temp_date)[0])
    if num_obs < 24 * (1 / configs_dict['measurement_interval']):
        end_date = end_date - datetime.timedelta(1)

    # Calculate the dates that represent the centre of the window for each step
    num_days = (end_date - start_date).days + 1 - window # Add 1 so is inclusive of both end members
    first_fit_day = start_date + datetime.timedelta(window / 2)
    step_days = numpy.arange(0, num_days, configs_dict['step_size_days'])
    step_dates_array = [first_fit_day + datetime.timedelta(i) for i in step_days]

    # Make an index dictionary for step dates
    step_dates_index_dict = {}
    for date in step_dates_array:
        date_time = (datetime.datetime.combine(date, datetime.datetime.min.time())
                     + datetime.timedelta(hours = 12))
        start_date = date_time - datetime.timedelta(window / 2.0)
        start_date = max(start_date,datetime_array[0])
        end_date = date_time + datetime.timedelta(window / 2.0)
        end_date = min(end_date,datetime_array[-1])
        start_ind = numpy.where(datetime_array == start_date)[0].item() + 1
        end_ind = numpy.where(datetime_array == end_date)[0].item()
        step_dates_index_dict[date] = [start_ind, end_ind]

    # Make an index dictionary for all dates
    all_dates_index_dict = {}
    for date in all_dates_array:
        date_time = datetime.datetime.combine(date, datetime.datetime.min.time())
        if date == all_dates_array[0]:
            start_ind = 0
        else:
            start_date = date_time + datetime.timedelta(hours = configs_dict['measurement_interval'])
            start_date = max(start_date,datetime_array[0])
            if start_date>datetime_array[-1]: break
            start_ind = numpy.where(datetime_array == start_date)[0].item()
        if date >= all_dates_array[-1]:
            end_ind = len(datetime_array)
        else:
            end_date = date_time + datetime.timedelta(1)
            end_date = min(end_date,datetime_array[-1])
            end_ind = numpy.where(datetime_array == end_date)[0].item()
        all_dates_index_dict[date] = [start_ind, end_ind]

    # Make an index dictionary for years
    years_index_dict = {}
    year_array = numpy.array([i.year for i in shift_datetime_array])
    year_list = list(set(year_array))
    for yr in year_list:
        index = numpy.where(year_array == yr)[0]
        years_index_dict[yr] = [index[0], index[-1]]

    return step_dates_index_dict, all_dates_index_dict, years_index_dict

def make_initial_guess_dict(data_d):

    # Calculate the parameter values that are intialised from data
    index = numpy.where(data_d['PAR'] < 10)[0]
    daytime_NEE_mean = numpy.nanmean(data_d['NEE'][index])
    daytime_NEE_range = (numpy.nanpercentile(data_d['NEE'][index], 5) -
                         numpy.nanpercentile(data_d['NEE'][index], 95))

    params_dict = {'Eo_prior': 100,
                   'k_prior': 0,
                   'alpha_prior': -0.01,
                   'rb_prior': daytime_NEE_mean,
                   'beta_prior': daytime_NEE_range,
                   'alpha_default': 0,
                   'beta_default': 0,
                   'k_default': 0 }

    return params_dict

def optimise_all(data_dict, params_dict):

    # Initialise error state variable
    error_state = 0

    drivers_dict = {driver: data_dict[driver] for driver in ['TempC']}
    response_array = data_dict['NEE']

    try:
        params = scipy.optimize.curve_fit(lambda x, a, b:
                           TRF(x, a, b),
                           drivers_dict,
                           response_array,
                           p0 = [params_dict['Eo_prior'],
                                 params_dict['rb_prior']])[0]
    except RuntimeError:
        params = [np.nan, np.nan]
        error_state = 3

    return params, error_state

def optimise_annual_Eo(data_dict, params_dict, configs_dict, year_index_dict):

    # Initialise local variables with configurations
    min_pct = configs_dict['minimum_pct_annual']
    msmt_int = configs_dict['measurement_interval']

    # Get Eo for each year and compile dictionary
    status = {"code":0,"message":"OK"}
    yearsEo_dict = {}
    yearsEo_raw_dict = {}
    yearsQC_dict = {}
    yearsQC_raw_dict = {}
    Eo_pass_keys = []
    Eo_range_fail_keys = []
    Eo_nan_fail_keys = []
    year_list = year_index_dict.keys()
    logger.info(" E0 optimised using whole year is as follows")
    for yr in year_list:

        # Calculate number of recs for year
        days = 366 if calendar.isleap(yr) else 365
        recs = days * (24 / msmt_int) / 2

        # Subset data
        sub_dict = subset_window(data_dict, year_index_dict[yr])
        sub_dict = subset_nan(sub_dict)
        noct_flag = True
        # no need to subset for day/night when input data is ER
        #sub_dict = subset_daynight(sub_dict, noct_flag)

        # Calculate percent of potential annual data that the subset contains
        pct = round(float(len(sub_dict['NEE'])) / recs * 100)

        # Fit L&T parameters if minimum data criterion satisfied, otherwise nan
        if pct >= min_pct:
            params, error_code = optimise_all(sub_dict, params_dict)
        else:
            msg = " Less than "+str(min_pct)+ "% for year "+str(yr)+" ("+str(pct)+"%)"
            logger.warning(msg)
            params, error_code = [numpy.nan, numpy.nan], 10

        # Assign year to pass, range_fail or nan_fail list for subsequent QC and fill
        Eo = params[0]
        yearsEo_dict[yr] = Eo
        yearsEo_raw_dict[yr] = Eo
        yearsQC_dict[yr] = error_code
        yearsQC_raw_dict[yr] = error_code
        if numpy.isnan(Eo):
            Eo_nan_fail_keys.append(yr)
        elif ((Eo < 50) | (Eo > 400)):
            Eo_range_fail_keys.append(yr)
        else:
            Eo_pass_keys.append(yr)

        logger.info(" E0 for "+str(yr) + ": " + str(round(params[0], 1)))

    # Do QC on Eo
    if len(Eo_pass_keys) != len(yearsEo_dict):
        if len(Eo_nan_fail_keys) == len(yearsEo_dict):
            msg = "  Could not find any values of Eo for any years! Exiting..."
            status["code"] = 1
            status["message"] = msg
            return yearsEo_dict, yearsQC_dict, yearsEo_raw_dict, yearsQC_raw_dict, status
        elif len(Eo_pass_keys) != 0:
            Eo_mean = numpy.array([yearsEo_dict[i] for i in Eo_pass_keys]).mean()
            all_fail_keys = Eo_range_fail_keys + Eo_nan_fail_keys
            for i in (all_fail_keys):
                yearsEo_dict[i] = Eo_mean
            all_fail_keys = [str(key) for key in all_fail_keys]
            if len(all_fail_keys) > 1:
                all_fail_str = ', '.join(all_fail_keys)
            else:
                all_fail_str = all_fail_keys[0]
            logger.warning(" Eo optimisation failed for the following years: " + all_fail_str)
            logger.warning(" Eo estimated from the mean of all other years")
        else:
            for i in Eo_range_fail_keys:
                if yearsEo_dict[i] < 50:
                    yearsEo_dict[i]=50
                else:
                    yearsEo_dict[i]=400
            if len(Eo_range_fail_keys)<=1:
                Eo_mean = yearsEo_dict[Eo_range_fail_keys[0]]
            else:
                l = [yearsEo_dict[i] for i in Eo_range_fail_keys]
                Eo_mean = sum(l)/float(len(l))
            for i in Eo_nan_fail_keys:
                yearsEo_dict[i] = Eo_mean
            logger.warning(" Eo estimates were out of range for all years")
            logger.warning(" Low estimates have been set to lower limit (50)")
            logger.warning(" High estimates have been set to upper limit (400)")
            logger.warning(" Parameter estimates are unlikely to be robust!")
    else:
        logger.info(" Eo estimates passed QC for all years")
    return yearsEo_dict, yearsQC_dict, yearsEo_raw_dict, yearsQC_raw_dict, status

def rpLT_createdict(cf,ds,series):
    """
    Purpose:
     Creates a dictionary in ds to hold information about estimating ecosystem
     respiration using the Lloyd-Taylor method.
    Usage:
    Author: PRI
    Date October 2015
    """
    # get the section of the control file containing the series
    section = pfp_utils.get_cfsection(cf,series=series,mode="quiet")
    # return without doing anything if the series isn't in a control file section
    if len(section)==0:
        logger.error("ERUsingLloydTaylor: Series "+series+" not found in control file, skipping ...")
        return
    # check that none of the drivers have missing data
    driver_list = ast.literal_eval(cf[section][series]["ERUsingLloydTaylor"]["drivers"])
    target = cf[section][series]["ERUsingLloydTaylor"]["target"]
    for label in driver_list:
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,label)
        if numpy.ma.count_masked(data)!=0:
            logger.error("ERUsingLloydTaylor: driver "+label+" contains missing data, skipping target "+target)
            return
    # create the dictionary keys for this series
    rpLT_info = {}
    # site name
    rpLT_info["site_name"] = ds.globalattributes["site_name"]
    # source series for ER
    opt = pfp_utils.get_keyvaluefromcf(cf, [section,series,"ERUsingLloydTaylor"], "source", default="Fc")
    rpLT_info["source"] = opt
    # target series name
    rpLT_info["target"] = cf[section][series]["ERUsingLloydTaylor"]["target"]
    # list of drivers
    rpLT_info["drivers"] = ast.literal_eval(cf[section][series]["ERUsingLloydTaylor"]["drivers"])
    # name of SOLO output series in ds
    rpLT_info["output"] = cf[section][series]["ERUsingLloydTaylor"]["output"]
    # results of best fit for plotting later on
    rpLT_info["results"] = {"startdate":[],"enddate":[],"No. points":[],"r":[],
                            "Bias":[],"RMSE":[],"Frac Bias":[],"NMSE":[],
                            "Avg (obs)":[],"Avg (LT)":[],
                            "Var (obs)":[],"Var (LT)":[],"Var ratio":[],
                            "m_ols":[],"b_ols":[]}
    # create the configuration dictionary
    rpLT_info["configs_dict"] = get_configs_dict(cf,ds)
    # create an empty series in ds if the output series doesn't exist yet
    if rpLT_info["output"] not in ds.series.keys():
        data,flag,attr = pfp_utils.MakeEmptySeries(ds,rpLT_info["output"])
        pfp_utils.CreateSeries(ds,rpLT_info["output"],data,flag,attr)
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
    return rpLT_info

def rpLT_initplot(**kwargs):
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

def rpLT_plot(pd,ds,series,driverlist,targetlabel,outputlabel,LT_info,si=0,ei=-1):
    """ Plot the results of the Lloyd-Taylor run. """
    # get the time step
    ts = int(ds.globalattributes['time_step'])
    # get a local copy of the datetime series
    if ei==-1:
        dt = ds.series['DateTime']['Data'][si:]
    else:
        dt = ds.series['DateTime']['Data'][si:ei+1]
    xdt = numpy.array(dt)
    Hdh,f,a = pfp_utils.GetSeriesasMA(ds,'Hdh',si=si,ei=ei)
    # get the observed and modelled values
    obs,f,a = pfp_utils.GetSeriesasMA(ds,targetlabel,si=si,ei=ei)
    mod,f,a = pfp_utils.GetSeriesasMA(ds,outputlabel,si=si,ei=ei)
    # make the figure
    if LT_info["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"],figsize=(13,8))
    fig.clf()
    fig.canvas.set_window_title(targetlabel+" (LT): "+pd["startdate"]+" to "+pd["enddate"])
    plt.figtext(0.5,0.95,pd["title"],ha='center',size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10,pd["margin_bottom"],pd["xy_width"],pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask,mod.mask)
    obs_mor = numpy.ma.array(obs,mask=mask)
    dstats = pfp_utils.get_diurnalstats(dt,obs_mor,LT_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'b-',label="Obs")
    # get the diurnal stats of all SOLO predictions
    dstats = pfp_utils.get_diurnalstats(dt,mod,LT_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'r-',label="LT(all)")
    mod_mor = numpy.ma.masked_where(numpy.ma.getmaskarray(obs)==True,mod,copy=True)
    dstats = pfp_utils.get_diurnalstats(dt,mod_mor,LT_info)
    ax1.plot(dstats["Hr"],dstats["Av"],'g-',label="LT(obs)")
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
    ax2.set_xlabel(targetlabel+'_LT')
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
    LT_info["er"][series]["results"]["Bias"].append(bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    plt.figtext(0.725,0.225,'No. points')
    plt.figtext(0.825,0.225,str(numpoints))
    LT_info["er"][series]["results"]["No. points"].append(numpoints)
    plt.figtext(0.725,0.200,'No. filled')
    plt.figtext(0.825,0.200,str(numfilled))
    plt.figtext(0.725,0.175,'Slope')
    plt.figtext(0.825,0.175,str(pfp_utils.round2sig(coefs[0],sig=4)))
    LT_info["er"][series]["results"]["m_ols"].append(coefs[0])
    plt.figtext(0.725,0.150,'Offset')
    plt.figtext(0.825,0.150,str(pfp_utils.round2sig(coefs[1],sig=4)))
    LT_info["er"][series]["results"]["b_ols"].append(coefs[1])
    plt.figtext(0.725,0.125,'r')
    plt.figtext(0.825,0.125,str(pfp_utils.round2sig(r[0][1],sig=4)))
    LT_info["er"][series]["results"]["r"].append(r[0][1])
    plt.figtext(0.725,0.100,'RMSE')
    plt.figtext(0.825,0.100,str(pfp_utils.round2sig(rmse,sig=4)))
    LT_info["er"][series]["results"]["RMSE"].append(rmse)
    var_obs = numpy.ma.var(obs)
    LT_info["er"][series]["results"]["Var (obs)"].append(var_obs)
    var_mod = numpy.ma.var(mod)
    LT_info["er"][series]["results"]["Var (LT)"].append(var_mod)
    LT_info["er"][series]["results"]["Var ratio"].append(var_obs/var_mod)
    LT_info["er"][series]["results"]["Avg (obs)"].append(numpy.ma.average(obs))
    LT_info["er"][series]["results"]["Avg (LT)"].append(numpy.ma.average(mod))
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
    plot_path = LT_info["plot_path"]+"L6/"
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+pd["site_name"].replace(" ","")+"_LT_"+pd["label"]
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    # draw the plot on the screen
    if LT_info["show_plots"]:
        plt.draw()
        plt.pause(1)
        plt.ioff()
    else:
        plt.close(fig)
        plt.ion()

def subset_window(data_dict, index_list):
    # Subset the arrays on basis of index list
    sub_dict = {}
    for i in data_dict.keys():
        sub_dict[i] = data_dict[i][index_list[0]: index_list[1] + 1]

    return sub_dict

def subset_daynight(data_dict, noct_flag):
    # Turn dictionary into an array
    temp_array = numpy.empty([len(data_dict['NEE']), len(data_dict)])
    for i, var in enumerate(data_dict.keys()):
        temp_array[:, i] = data_dict[var]

    # Create night / day subsetting index and subset data
    if noct_flag:
        daynight_index = numpy.where(data_dict['PAR'] < 10)[0]
    else:
        daynight_index = numpy.where(data_dict['PAR'] > 10)[0]
    temp_array = temp_array[daynight_index]

    sub_dict = {var: temp_array[:, i] for i, var in enumerate(data_dict.keys())}

    return sub_dict

def subset_nan(data_dict):

    # Turn dictionary into an array
    temp_array = numpy.empty([len(data_dict['NEE']), len(data_dict)])
    for i, var in enumerate(data_dict.keys()):
        temp_array[:, i] = data_dict[var]

    # Create nan subsetting index and subset data and count
    QCdata_index = numpy.where(numpy.all(~numpy.isnan(temp_array), axis=1))
    temp_array = temp_array[QCdata_index]

    sub_dict = {var: temp_array[:, i] for i, var in enumerate(data_dict.keys())}

    return sub_dict

def ER_LloydTaylor(T,E0,rb):
    t1 = 1/(c.Tref-c.T0)
    t2 = 1/(T-c.T0)
    ER = rb*numpy.exp(E0*(t1-t2))
    return ER

def estimate_Re_GPP(sub_d, params_d, GPP = False):

    return_dict = {}
    if GPP:
        GPP, Re = light.LRF_part(sub_d, params_d['Eo'], params_d['rb'],
                                 params_d['alpha'], params_d['beta'],
                                 params_d['k'])
        return_dict['Re'] = Re
        return_dict['GPP'] = GPP
    else:
        Re = TRF(sub_d, params_d['Eo'], params_d['rb'])
        return_dict['Re'] = Re
    return return_dict

def plot_windows(data_dict, configs_dict, date, noct_flag):

    # Set parameters from dicts
    path = configs_dict['window_plot_output_path']
    window = configs_dict['window_size_days']

    for i in range(2):
        sub_d = subset_daynight(data_dict, noct_flag)
        if noct_flag:
            daynight_ind = 'noct'
            x_lab = r'Temperature ($^{o}C$)'
            x_var = sub_d['TempC']
            y_var1 = sub_d['NEE']
            y_var2 = sub_d['Re']
        else:
            daynight_ind = 'day'
            x_lab = r'PAR ($\mu mol\/photons\/m^{-2}s^{-1}$)'
            x_var = sub_d['PAR']
            y_var1 = sub_d['NEE']
            y_var2 = sub_d['NEE_est']

        # Plot
        date_str = datetime.datetime.strftime(date,'%Y-%m-%d')
        fig = plt.figure(figsize = (13,8))
        fig.patch.set_facecolor('white')
        plt.plot(x_var, y_var1, 'bo' , label = 'NEE_obs')
        plt.plot(x_var, y_var2, 'ro', label = 'NEE_est')
        plt.title('Fit for ' + str(window) + ' day window centred on ' +
                  date_str + '\n', fontsize = 22)
        plt.xlabel(x_lab, fontsize = 16)
        plt.ylabel(r'NEE ($\mu mol C\/m^{-2} s^{-1}$)', fontsize = 16)
        plt.axhline(y = 0, color = 'black')
        plot_out_name = daynight_ind + '_' + date_str + '.jpg'
        plt.tight_layout()
        fig.savefig(os.path.join(path, plot_out_name))
        plt.close(fig)

    return

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
