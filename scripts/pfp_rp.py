# standard modules
import collections
import copy
import datetime
import logging
import os
import pandas
import pdb
# 3rd party modules
import dateutil
import matplotlib
import matplotlib.pyplot as plt
import numpy
import pylab
import xlrd
# PFP modules
import constants as c
import pfp_cfg
import pfp_gf
import pfp_gfSOLO
import pfp_gui
import pfp_io
import pfp_rpLL
import pfp_rpLT
import pfp_rputils
import pfp_ts
import pfp_utils

# Ian's modules
import sys
sys.path.append('/home/ian/Code/Python/Py3_6/Partitioning')
import partitioning_class as pt

logger = logging.getLogger("pfp_log")

def CalculateET(ds):
    """
    Purpose:
     Calculate ET from Fe
    Usage:
     pfp_rp.CalculateET(ds)
      where ds is a data structure
    Side effects:
     Series to hold the ET data are created in ds.
    Author: PRI
    Date: June 2015
    """
    ts = int(ds.globalattributes["time_step"])
    series_list = ds.series.keys()
    Fe_list = [item for item in series_list if "Fe" in item[0:2]]
    for label in Fe_list:
        Fe, flag, attr = pfp_utils.GetSeriesasMA(ds, label)
        ET = Fe*ts*60/c.Lv
        attr["long_name"] = "Evapo-transpiration calculated from latent heat flux"
        attr["units"] = "mm"
        pfp_utils.CreateSeries(ds, label.replace("Fe","ET"), ET, flag, attr)

def CalculateNEE(cf, ds, l6_info):
    """
    Purpose:
     Calculate NEE from observed Fc and observed/modeled ER.
     Input and output names are held in info["NetEcosystemExchange"].
    Usage:
     pfp_rp.CalculateNEE(cf,ds)
      where cf is a conbtrol file object
            ds is a data structure
    Side effects:
     Series to hold the NEE data are created in ds.
    Author: PRI
    Date: August 2014
    """
    if "NetEcosystemExchange" not in l6_info:
        return
    # get the Fsd threshold
    Fsd_threshold = float(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "Fsd_threshold", default=10))
    # get the incoming shortwave radiation
    Fsd, _, _ = pfp_utils.GetSeriesasMA(ds, "Fsd")
    for label in l6_info["NetEcosystemExchange"].keys():
        if "Fc" not in l6_info["NetEcosystemExchange"][label] and "ER" not in l6_info["NetEcosystemExchange"][label]:
            continue
        Fc_label = l6_info["NetEcosystemExchange"][label]["Fc"]
        ER_label = l6_info["NetEcosystemExchange"][label]["ER"]
        output_label = l6_info["NetEcosystemExchange"][label]["output"]
        Fc, Fc_flag, Fc_attr = pfp_utils.GetSeriesasMA(ds, Fc_label)
        ER, ER_flag, _ = pfp_utils.GetSeriesasMA(ds, ER_label)
        # put the day time Fc into the NEE series
        index = numpy.ma.where(Fsd >= Fsd_threshold)[0]
        ds.series[output_label]["Data"][index] = Fc[index]
        ds.series[output_label]["Flag"][index] = Fc_flag[index]
        # put the night time ER into the NEE series
        index = numpy.ma.where(Fsd < Fsd_threshold)[0]
        ds.series[output_label]["Data"][index] = ER[index]
        ds.series[output_label]["Flag"][index] = ER_flag[index]
        # update the attributes
        attr = ds.series[output_label]["Attr"]
        attr["units"] = Fc_attr["units"]
        attr["long_name"] = "Net Ecosystem Exchange"
        attr["description_l6"] = " Calculated from " + Fc_label + " and " + ER_label
        attr["comment1"] = "Fsd threshold used was " + str(Fsd_threshold)
        ds.series[output_label]["Attr"] = attr
    return

def CalculateNEP(cf, ds):
    """
    Purpose:
     Calculate NEP from NEE
    Usage:
     pfp_rp.CalculateNEP(cf, ds)
      where cf is a control file object
            ds is a data structure
    Side effects:
     Series to hold the NEP data are created in ds.
    Author: PRI
    Date: May 2015
    """
    for nee_name in cf["NetEcosystemExchange"].keys():
        nep_name = nee_name.replace("NEE", "NEP")
        nee, flag, attr = pfp_utils.GetSeriesasMA(ds, nee_name)
        nep = float(-1)*nee
        attr["long_name"] = "Net Ecosystem Productivity"
        attr["description_l6"] = "Calculated as -1*" + nee_name
        pfp_utils.CreateSeries(ds, nep_name, nep, flag, attr)

def cleanup_ustar_dict(ldt,ustar_dict):
    """
    Purpose:
     Clean up the ustar dictionary;
      - make sure all years are included
      - fill missing year values with the mean
    Usage:
    Author: PRI
    Date: September 2015
    """
    start_year = ldt[0].year
    end_year = ldt[-1].year
    data_years = range(start_year,end_year+1)
    ustar_years = ustar_dict.keys()
    ustar_list = ustar_dict[ustar_years[0]]
    for year in data_years:
        if str(year) not in ustar_years:
            ustar_dict[str(year)] = {}
            for item in ustar_list:
                ustar_dict[str(year)][item] = float(c.missing_value)
    # loop over the list of ustar thresholds
    year_list = ustar_dict.keys()
    year_list.sort()
    # get the average of good ustar threshold values
    good_values = []
    for year in year_list:
        ustar_threshold = float(ustar_dict[year]["ustar_mean"])
        if ustar_threshold!=float(c.missing_value):
            good_values.append(ustar_threshold)
    ustar_threshold_mean = numpy.sum(numpy.array(good_values))/len(good_values)
    # replace missing vaues with mean
    for year in year_list:
        if ustar_dict[year]["ustar_mean"]==float(c.missing_value):
            ustar_dict[year]["ustar_mean"] = ustar_threshold_mean

#def ERUsingLasslop(ds, l6_info):
#    """
#    Purpose:
#    Usage:
#    Side effects:
#    Author: IMcH, PRI
#    Date: Back in the day
#    """
#    if "ERUsingLasslop" not in l6_info:
#        return
#    logger.info("Estimating ER using Lasslop")
#    iel = l6_info["ERUsingLasslop"]
#    ielo = iel["outputs"]
#    # get a list of the required outputs
#    outputs = iel["outputs"].keys()
#    # need to loop over more than 1 output
#    output = outputs[0]
#    drivers = ielo[output]["drivers"]
#    target = ielo[output]["target"]
#    # get some useful things
#    ldt = ds.series["DateTime"]["Data"]
#    startdate = ldt[0]
#    enddate = ldt[-1]
#    ts = int(ds.globalattributes["time_step"])
#    site_name = ds.globalattributes["site_name"]
#    nrecs = int(ds.globalattributes["nc_nrecs"])
#    # get the data and synchronise the gaps
#    # *** PUT INTO SEPARATE FUNCTION
#    indicator = numpy.ones(nrecs, dtype=numpy.int)
#    Fsd, f, _ = pfp_utils.GetSeriesasMA(ds, "Fsd")
#    idx = numpy.where(f != 0)[0]
#    indicator[idx] = numpy.int(0)
#    D, f, _ = pfp_utils.GetSeriesasMA(ds, "VPD")
#    idx = numpy.where(f != 0)[0]
#    indicator[idx] = numpy.int(0)
#    T, f, _ = pfp_utils.GetSeriesasMA(ds, "Ta")
#    idx = numpy.where(f != 0)[0]
#    indicator[idx] = numpy.int(0)
#    _, f, _ = pfp_utils.GetSeriesasMA(ds, "ustar")
#    idx = numpy.where(f != 0)[0]
#    indicator[idx] = numpy.int(0)
#    Fc, f, Fc_attr = pfp_utils.GetSeriesasMA(ds, "Fc")
#    idx = numpy.where(f != 0)[0]
#    indicator[idx] = numpy.int(0)
#    indicator_night = numpy.copy(indicator)
#    # ***
#    # apply a day/night filter
#    idx = numpy.where(Fsd >= 10)[0]
#    indicator_night[idx] = numpy.int(0)
#    # synchronise the gaps and apply the ustar filter
#    T_night = numpy.ma.masked_where(indicator_night == 0, T)
#    ER = numpy.ma.masked_where(indicator_night == 0, Fc)
#    # loop over the windows and get E0
#    logger.info(" Estimating the rb and E0 parameters")
#    LT_results = pfp_rpLL.get_LT_params(ldt, ER, T_night, l6_info, output)
#    # interpolate parameters
#    # this should have a check to make sure we are not interpolating with a small
#    # number of points
#    LT_results["rb_int"] = pfp_rpLL.interp_params(LT_results["rb"])
#    LT_results["E0_int"] = pfp_rpLL.interp_params(LT_results["E0"])
#    # get series of rb and E0 from LT at the tower stime step
#    # *** PUT INTO SEPARATE FUNCTION
#    ntsperday = float(24)*float(60)/float(ts)
#    days_at_beginning = float(ielo[output]["window_size_days"])/2 - float(ielo[output]["step_size_days"])/2
#    rb_beginning = numpy.ones(int(days_at_beginning*ntsperday+0.5))*LT_results["rb_int"][0]
#    rb_middle = numpy.repeat(LT_results["rb_int"],ielo[output]["step_size_days"]*ntsperday)
#    nend = len(ldt) - (len(rb_beginning)+len(rb_middle))
#    E0_beginning = numpy.ones(int(days_at_beginning*ntsperday+0.5))*LT_results["E0_int"][0]
#    E0_middle = numpy.repeat(LT_results["E0_int"],ielo[output]["step_size_days"]*ntsperday)
#    nend = len(ldt) - (len(E0_beginning)+len(E0_middle))
#    # ***
#    # and get the ecosystem respiration at the tower time step
#    logger.info(" Calculating ER using Lloyd-Taylor")
#    # get a day time indicator
#    indicator_day = numpy.copy(indicator)
#    # apply a day/night filter
#    idx = numpy.where(Fsd <= ielo[output]["fsd_threshold"])[0]
#    indicator_day[idx] = numpy.int(0)
#    # synchronise the gaps and apply the day/night filter
#    Fsd_day = numpy.ma.masked_where(indicator_day==0,Fsd)
#    D_day = numpy.ma.masked_where(indicator_day==0,D)
#    T_day = numpy.ma.masked_where(indicator_day==0,T)
#    NEE_day = numpy.ma.masked_where(indicator_day==0,Fc)
#    # get the Lasslop parameters
#    logger.info(" Estimating the Lasslop parameters")
#    LL_results = pfp_rpLL.get_LL_params(ldt, Fsd_day, D_day, T_day, NEE_day, ER, LT_results, l6_info, output)
#    # interpolate parameters
#    LL_results["alpha_int"] = pfp_rpLL.interp_params(LL_results["alpha"])
#    LL_results["beta_int"] = pfp_rpLL.interp_params(LL_results["beta"])
#    LL_results["k_int"] = pfp_rpLL.interp_params(LL_results["k"])
#    LL_results["rb_int"] = pfp_rpLL.interp_params(LL_results["rb"])
#    LL_results["E0_int"] = pfp_rpLL.interp_params(LL_results["E0"])
#    # get the Lasslop parameters at the tower time step
#    # *** PUT INTO SEPARATE FUNCTION
#    ntsperday = float(24)*float(60)/float(ts)
#    days_at_beginning = float(ielo[output]["window_size_days"])/2 - float(ielo[output]["step_size_days"])/2
#    int_list = ["alpha_int","beta_int","k_int","rb_int","E0_int"]
#    tts_list = ["alpha_tts","beta_tts","k_tts","rb_tts","E0_tts"]
#    for tts_item,int_item in zip(tts_list,int_list):
#        beginning = numpy.ones(int(days_at_beginning*ntsperday+0.5))*LL_results[int_item][0]
#        middle = numpy.repeat(LL_results[int_item],ielo[output]["step_size_days"]*ntsperday)
#        nend = len(ldt) - (len(beginning)+len(middle))
#        end = numpy.ones(nend)*LL_results[int_item][-1]
#        LL_results[tts_item] = numpy.concatenate((beginning,middle,end))
#    # ***
#    # get ER, GPP and NEE using Lasslop
#    D0 = LL_results["D0"]
#    rb = LL_results["rb_tts"]
#    units = "umol/m2/s"
#    long_name = "Base respiration at Tref from Lloyd-Taylor method used in Lasslop et al (2010)"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    flag = numpy.zeros(len(rb),dtype=numpy.int32)
#    pfp_utils.CreateSeries(ds,"rb_LL",rb,flag,attr)
#    E0 = LL_results["E0_tts"]
#    units = "C"
#    long_name = "Activation energy from Lloyd-Taylor method used in Lasslop et al (2010)"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    pfp_utils.CreateSeries(ds,"E0_LL",E0,flag,attr)
#    logger.info(" Calculating ER using Lloyd-Taylor with Lasslop parameters")
#    ER_LL = pfp_rpLL.ER_LloydTaylor(T,rb,E0)
#    # write ecosystem respiration modelled by Lasslop et al (2010)
#    units = Fc_attr["units"]
#    long_name = "Ecosystem respiration modelled by Lasslop et al (2010)"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    pfp_utils.CreateSeries(ds,output,ER_LL,flag,attr)
#    # parameters associated with GPP and GPP itself
#    alpha = LL_results["alpha_tts"]
#    units = "umol/J"
#    long_name = "Canopy light use efficiency"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    pfp_utils.CreateSeries(ds,"alpha_LL",alpha,flag,attr)
#    beta = LL_results["beta_tts"]
#    units = "umol/m2/s"
#    long_name = "Maximum CO2 uptake at light saturation"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    pfp_utils.CreateSeries(ds,"beta_LL",beta,flag,attr)
#    k = LL_results["k_tts"]
#    units = "none"
#    long_name = "Sensitivity of response to VPD"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    pfp_utils.CreateSeries(ds,"k_LL",k,flag,attr)
#    GPP_LL = pfp_rpLL.GPP_RHLRC_D(Fsd,D,alpha,beta,k,D0)
#    units = "umol/m2/s"
#    long_name = "GPP modelled by Lasslop et al (2010)"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    pfp_utils.CreateSeries(ds,"GPP_LL_all",GPP_LL,flag,attr)
#    # NEE
#    data = {"Fsd":Fsd,"T":T,"D":D}
#    NEE_LL = pfp_rpLL.NEE_RHLRC_D(data,alpha,beta,k,D0,rb,E0)
#    units = "umol/m2/s"
#    long_name = "NEE modelled by Lasslop et al (2010)"
#    attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units=units)
#    pfp_utils.CreateSeries(ds,"NEE_LL_all",NEE_LL,flag,attr)
#    # plot the respiration estimated using Lasslop et al
#    # set the figure number
#    if len(plt.get_fignums())==0:
#        fig_num = 0
#    else:
#        fig_num = plt.get_fignums()[-1] + 1
#    title = site_name+" : ER estimated using Lasslop et al"
#    pd = pfp_rpLL.rpLL_initplot(site_name=site_name,label="ER",fig_num=fig_num,title=title,
#                         nDrivers=len(data.keys()),startdate=str(startdate),enddate=str(enddate))
#    pfp_rpLL.rpLL_plot(pd, ds, output, drivers, target, l6_info)

#def ERUsingLasslop2(ds, l6_info):
#    """
#    Purpose:
#     Estimate ecosystem respiration using Lasslop.
#     Ian McHugh wrote the LT code, PRI wrote the wrapper to integrate
#     this with OzFluxQC.
#    Usage:
#    Author: IMcH, PRI
#    Date: October 2015
#    """
#    if "ERUsingLasslop" not in l6_info:
#        return
#    logger.info("Estimating ER using Lasslop")
#    long_name = "Ecosystem respiration modelled by Lasslop"
#    ER_attr = pfp_utils.MakeAttributeDictionary(long_name=long_name, 
#                                                units="umol/m2/s")
#    site_name = ds.globalattributes["site_name"]
#
#    pdb.set_trace()
#
#    # Get configuration dict
#    iel = l6_info["ERUsingLasslop"]
#
#    # set the figure number
#    if len(plt.get_fignums()) == 0:
#        fig_num = 0
#    else:
#        fig_num = plt.get_fignums()[-1]
#    
#    # open the Excel file for writing all outputs
#    xl_name = iel['info']['data_file_path']
#    xl_writer = pandas.ExcelWriter(xl_name, engine = 'xlsxwriter')
#    
#    # loop over the series of ouputs (usually one only)
#    outputs = iel["outputs"].keys()
#    for output in outputs:
#        
#        # Make the filtered dataframe
#        ustars_dict = {x.split('_')[-1]: float(ds.series['Fc']['Attr'][x])
#                       for x in ds.series['Fc']['Attr'] if 'ustar' in x}
#        var_list = ['Fc', 'Ta', 'Ts', 'Fsd', 'ustar', 'VPD']
#        df = pandas.DataFrame({var: ds.series[var]['Data'] for var in var_list},
#                              index = ds.series['DateTime']['Data'])
#        is_valid = numpy.tile(True, int(ds.globalattributes['nc_nrecs']))
#        for this_var in df.columns: is_valid *= ds.series[this_var]['Flag'] == 0
#        df.loc[~is_valid, 'Fc'] = numpy.nan
#        for year in ustars_dict:
#            df.loc[(df.index.year == int(year)) & 
#                   (df.ustar < ustars_dict[year]) & 
#                   (df.Fsd < 10), 'Fc'] = numpy.nan
#        
#        # Pass the dataframe to the respiration class and get the results
#        ptc = pt.partition(df)
#        params_df = ptc.estimate_parameters(mode = 'day', fit_daytime_rb = True)
#        ER = ptc.estimate_er_time_series(params_df)
#        ER_flag = numpy.tile(30, len(ER))
#        pfp_utils.CreateSeries(ds, output, ER, ER_flag, ER_attr)
#    
#        # Write to excel
#        params_df.to_excel(xl_writer, output)
#        xl_writer.save()
#
#        # Get some info required for plotting
#        drivers = iel['outputs'][output]["drivers"]
#        target = iel["outputs"][output]["target"]
#        ER_attr['comment1'] = 'Drivers were {}'.format(str(drivers))
#        startdate = str(ds.series["DateTime"]["Data"][0])
#        enddate = str(ds.series["DateTime"]["Data"][-1])
#
#        # Do plotting
#        fig_num = fig_num + 1
#        title = site_name+" : "+output+" estimated using Lasslop"
#        pd = pfp_rpLL.rpLL_initplot(site_name=site_name, label=target, 
#                                    fig_num=fig_num, title=title,
#                                    nDrivers=len(drivers), 
#                                    startdate=str(startdate), 
#                                    enddate=str(enddate))
#        pfp_rputils.rp_plot(pd, ds, output, drivers, target, iel)

def ERUsingLasslop(ds, l6_info):
    
    if "ERUsingLasslop" not in l6_info:
        return
    logger.info("Estimating ER using Lasslop")
#    iel = l6_info["ERUsingLasslop"]
    EcoResp(ds, l6_info, 'ERUsingLasslop')
    
def ERUsingLloydTaylor(ds, l6_info):
    
    if "ERUsingLloydTaylor" not in l6_info:
        return
    logger.info("Estimating ER using Lloyd-Taylor")
#    iel = l6_info["ERUsingLloydTaylor"]
    EcoResp(ds, l6_info, 'ERUsingLloydTaylor')

def EcoResp(ds, l6_info, called_by):
    """
    Purpose:
    Estimate ecosystem respiration
    Args:
        * ds: PyFluxPro data structure (class)
        * l6_info: information derived from L6 control file (dict)
    Kwargs:
        * mode: choice of whether to to use Lloyd Taylor os Lasslop methods to 
          estimate respiration (str; options "LT" [Lloyd Taylor - default] 
          and "LL" [Lasslop])
    Author: IMcH, PRI
    Date: August 2019
    """

    iel = l6_info[called_by]

    # Set dict to select day or night fitting of rb depending on mode
    partition_dict = {'ERUsingLasslop': {'day_night_mode': 
                                         'day', 'day_rb_bool': True},
                      'ERUsingLloydTaylor': {'day_night_mode': 'night', 
                                             'day_rb_bool': False}}
    er_mode = partition_dict[called_by]['day_night_mode']
    rb_mode = partition_dict[called_by]['day_rb_bool']

    # Set attributes for ER and plotting   
    long_name_dict = {'ERUsingLasslop': "Ecosystem respiration modelled by Lloyd-Taylor",
                      'ERUsingLloydTaylor': "Ecosystem respiration modelled by Lasslop"}
    long_name = long_name_dict[called_by]
    ER_attr = pfp_utils.MakeAttributeDictionary(long_name = long_name, 
                                                units="umol/m2/s")
    site_name = ds.globalattributes["site_name"]

    # set the figure number
    if len(plt.get_fignums()) == 0:
        fig_num = 0
    else:
        fig_num = plt.get_fignums()[-1]
    
    # open the Excel file for writing all outputs
    xl_name = iel['info']['data_file_path']
    xl_writer = pandas.ExcelWriter(xl_name, engine = 'xlsxwriter')
    
    # loop over the series of ouputs (usually one only)
    outputs = iel["outputs"].keys()
    for output in outputs:
        
        # Make the filtered dataframe
        ustars_dict = {x.split('_')[-1]: float(ds.series['Fc']['Attr'][x])
                       for x in ds.series['Fc']['Attr'] if 'ustar' in x}
        var_list = ['Fc', 'Ta', 'Ts', 'Fsd', 'ustar', 'VPD']
        df = pandas.DataFrame({var: ds.series[var]['Data'] for var in var_list},
                              index = ds.series['DateTime']['Data'])
        is_valid = numpy.tile(True, int(ds.globalattributes['nc_nrecs']))
        for this_var in df.columns: is_valid *= ds.series[this_var]['Flag'] == 0
        df.loc[~is_valid, 'Fc'] = numpy.nan
        for year in ustars_dict:
            df.loc[(df.index.year == int(year)) & 
                   (df.ustar < ustars_dict[year]) & 
                   (df.Fsd < 10), 'Fc'] = numpy.nan
        
        # Set the weighting of air and soil temperatures
        configs_dict = iel["outputs"][output]
        drivers = configs_dict['drivers']
        weighting = configs_dict['weights_air_soil']
        re_drivers = [x for x in drivers if x in ['Ta', 'Ts']]
        if len(re_drivers) == 1:
            if re_drivers[0] == 'Ta': weighting = 'air'
            if re_drivers[0] == 'Ts': weighting = 'soil'
        elif len(re_drivers) == 2:
            if len(weighting) == 1: 
                weighting = 'air'
            elif len(weighting) == 2:
                try:
                    weighting = [float(x) for x in weighting]
                except TypeError:
                    weighting = 'air'
            else:
                weighting = 'air'
        
        # Pass the dataframe to the respiration class and get the results
        ptc = pt.partition(df, weights_air_soil = weighting)
        params_df = ptc.estimate_parameters(mode = er_mode, fit_daytime_rb = rb_mode)
        ER = ptc.estimate_er_time_series(params_df)
        ER_flag = numpy.tile(30, len(ER))
        pfp_utils.CreateSeries(ds, output, ER, ER_flag, ER_attr)
    
        # Write to excel
        params_df.to_excel(xl_writer, output)
        xl_writer.save()

        # Get some info required for plotting
        drivers = iel['outputs'][output]["drivers"]
        target = iel["outputs"][output]["target"]
        ER_attr['comment1'] = 'Drivers were {}'.format(str(drivers))
        startdate = str(ds.series["DateTime"]["Data"][0])
        enddate = str(ds.series["DateTime"]["Data"][-1])

        # Do plotting
        fig_num = fig_num + 1
        title_snippet = (' ').join(long_name.split(' ')[2:])
        title = site_name+" : " + output + title_snippet
        pd = pfp_rputils.rp_initplot(site_name=site_name, label=target, 
                                    fig_num=fig_num, title=title,
                                    nDrivers=len(drivers), 
                                    startdate=str(startdate), 
                                    enddate=str(enddate))
        pfp_rputils.rp_plot(pd, ds, output, drivers, target, iel, called_by)

def ERUsingSOLO(main_gui, ds, l6_info, called_by):
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
    # set the default return code
    ds.returncodes["value"] = 0
    ds.returncodes["message"] = "normal"
    # check the SOLO drivers for missing data
    pfp_gf.CheckDrivers(ds, l6_info, called_by)
    if ds.returncodes["value"] != 0:
        return ds
    if l6_info["ERUsingSOLO"]["info"]["call_mode"].lower() == "interactive":
        # call the ERUsingSOLO GUI
        pfp_gfSOLO.gfSOLO_gui(main_gui, ds, l6_info, called_by)
    else:
        # ["gui"] settings dictionary done in pfp_rp.ParseL6ControlFile()
        pfp_gfSOLO.gfSOLO_run(ds, l6_info, called_by)

def GetERFromFc(cf, ds):
    """
    Purpose:
     Get the observed ecosystem respiration from measurements of Fc by
     filtering out daytime periods.  Note that the removal of low tubulence
     periods has been done by pfp_ck.ApplyTurbulenceFilter() before this
     routine is called.
     The Fsd threshold for determining day time and night time and the
     ustar threshold are set in the [Params] section of the L5 control
     file.
     Re-write of the original penned in August 2014
    Usage:
     pfp_rp.GetERFromFc(cf, ds)
     where cf is a control file object
           ds is a data structure
    Side effects:
     A new series called "ER" is created in the data structure.
    Author: PRI
    Date: October 2015
    """
    ER = {"Label": "ER"}
    Fc = pfp_utils.GetVariable(ds, "Fc")
    # check to see if a turbulence filter has been applied to the CO2 flux
    if "turbulence_filter" not in Fc["Attr"]:
        # print error message to the log window
        msg = "CO2 flux series Fc did not have a turbulence filter applied."
        logger.error(msg)
        msg = "Please repeat the L5 processing and apply a turbulence filter."
        logger.error(msg)
        msg = "Quiting L6 processing ..."
        logger.error(msg)
        # check to see if we are running in interactive mode
        if cf["Options"]["call_mode"].lower() == "interactive":
            # if so, put up a message box
            msg = "CO2 flux series Fc did not have a turbulence filter applied.\n"
            msg = msg + "Please repeat the L5 processing and apply a turbulence filter.\n"
            msg = msg + "Quiting L6 processing ..."
            msgbox = pfp_gui.myMessageBox(msg, title="Critical")
        # set the return code to non-zero ...
        ds.returncodes["value"] = 1
        ds.returncodes["message"] = "quit"
        # ... and return
        return
    # get a copy of the Fc flag and make the attribute dictionary
    ER["Flag"] = numpy.array(Fc["Flag"])
    long_name = "Ecosystem respiration (observed) derived from Fc"
    units = Fc["Attr"]["units"]
    ER["Attr"] = pfp_utils.MakeAttributeDictionary(long_name=long_name, units=units)
    # only accept Fc with QC flag value of 0
    Fc["Data"] = numpy.ma.masked_where((Fc["Flag"] != 0), Fc["Data"])
    idx_notok = numpy.where((Fc["Flag"] != 0))[0]
    ER["Flag"][idx_notok] = numpy.int32(61)
    # get the indicator series
    daynight_indicator = get_daynight_indicator(cf, ds)
    idx = numpy.where(daynight_indicator["values"] == 0)[0]
    ER["Flag"][idx] = numpy.int32(63)
    # apply the filter to get ER from Fc
    ER["Data"] = numpy.ma.masked_where(daynight_indicator["values"] == 0, Fc["Data"], copy=True)
    for item in daynight_indicator["attr"]:
        ER["Attr"][item] = daynight_indicator["attr"][item]
    pfp_utils.CreateVariable(ds, ER)
    return

def check_for_missing_data(series_list, label_list):
    for item, label in zip(series_list, label_list):
        index = numpy.where(numpy.ma.getmaskarray(item) == True)[0]
        if len(index) != 0:
            msg = " GetERFromFc: missing data in series " + label
            logger.error(msg)
            return 0
    return 1

def get_ustar_thresholds(cf,ldt):
    if "cpd_filename" in cf["Files"]:
        ustar_dict = get_ustarthreshold_from_cpdresults(cf)
    else:
        msg = " CPD results filename not in control file"
        logger.warning(msg)
        ustar_dict = get_ustarthreshold_from_cf(cf,ldt)
    cleanup_ustar_dict(ldt,ustar_dict)
    return ustar_dict

def get_daynight_indicator(cf, ds):
    Fsd, _, _ = pfp_utils.GetSeriesasMA(ds, "Fsd")
    # get the day/night indicator
    daynight_indicator = {"values":numpy.zeros(len(Fsd), dtype=numpy.int32), "attr":{}}
    inds = daynight_indicator["values"]
    attr = daynight_indicator["attr"]
    # get the filter type
    filter_type = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "DayNightFilter", default="Fsd")
    attr["daynight_filter"] = filter_type
    use_fsdsyn = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "UseFsdsyn_threshold", default="No")
    attr["use_fsdsyn"] = use_fsdsyn
    # get the indicator series
    if filter_type.lower() == "fsd":
        # get the Fsd threshold
        Fsd_threshold = int(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "Fsd_threshold", default=10))
        attr["Fsd_threshold"] = str(Fsd_threshold)
        # we are using Fsd only to define day/night
        idx = numpy.ma.where(Fsd <= Fsd_threshold)[0]
        inds[idx] = numpy.int32(1)
    elif filter_type.lower() == "sa":
        # get the solar altitude threshold
        sa_threshold = int(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "sa_threshold", default="-5"))
        attr["sa_threshold"] = str(sa_threshold)
        # we are using solar altitude to define day/night
        if "solar_altitude" not in ds.series.keys():
            pfp_ts.get_synthetic_fsd(ds)
        sa, _, _ = pfp_utils.GetSeriesasMA(ds, "solar_altitude")
        idx = numpy.ma.where(sa < sa_threshold)[0]
        inds[idx] = numpy.int32(1)
    else:
        msg = "Unrecognised DayNightFilter option in L6 control file"
        raise Exception(msg)
    return daynight_indicator

def get_day_indicator(cf, ds):
    """
    Purpose:
     Returns a dictionary containing an indicator series and some attributes.
     The indicator series is 1 during day time and 0 at night time.  The threshold
     between night and day is the Fsd threshold specified in the control file.
    Usage:
     indicators["day"] = get_day_indicator(cf, ds)
     where;
      cf is a control file object
      ds is a data structure
    and;
      indicators["day"] is a dictionary containing
      indicators["day"]["values"] is the indicator series
      indicators["day"]["attr"] are the attributes
    Author: PRI
    Date: March 2016
    Mods:
     PRI 6/12/2018 - removed calculation of Fsd_syn by default
    """
    Fsd, _, _ = pfp_utils.GetSeriesasMA(ds, "Fsd")
    # indicator = 1 ==> day, indicator = 0 ==> night
    day_indicator = {"values":numpy.ones(len(Fsd), dtype=numpy.int32), "attr":{}}
    inds = day_indicator["values"]
    attr = day_indicator["attr"]
    # get the filter type
    filter_type = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "DayNightFilter", default="Fsd")
    attr["daynight_filter_type"] = filter_type
    use_fsdsyn = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "UseFsdsyn_threshold", default="No")
    attr["use_fsdsyn"] = use_fsdsyn
    # get the indicator series
    if filter_type.lower() == "fsd":
        # get the Fsd threshold
        Fsd_threshold = int(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "Fsd_threshold", default=10))
        attr["Fsd_threshold"] = str(Fsd_threshold)
        # we are using Fsd only to define day/night
        idx = numpy.ma.where(Fsd <= Fsd_threshold)[0]
        inds[idx] = numpy.int32(0)
    elif filter_type.lower() == "sa":
        # get the solar altitude threshold
        sa_threshold = int(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "sa_threshold", default="-5"))
        attr["sa_threshold"] = str(sa_threshold)
        # we are using solar altitude to define day/night
        if "solar_altitude" not in ds.series.keys():
            pfp_ts.get_synthetic_fsd(ds)
        sa, _, _ = pfp_utils.GetSeriesasMA(ds, "solar_altitude")
        index = numpy.ma.where(sa < sa_threshold)[0]
        inds[index] = numpy.int32(0)
    else:
        msg = "Unrecognised DayNightFilter option in control file"
        raise Exception(msg)
    return day_indicator

def get_evening_indicator(cf, ds):
    """
    Purpose:
     Returns a dictionary containing an indicator series and some attributes.
     The indicator series is 1 during the evening and 0 at all other times.
     Evening is defined as the period between sunset and the number of hours
     specified in the control file [Options] section as the EveningFilterLength
     key.
    Usage:
     indicators["evening"] = get_evening_indicator(cf,Fsd,Fsd_syn,sa,ts)
     where;
      cf is a control file object
      Fsd is a series of incoming shortwave radiation values (ndarray)
      Fsd_syn is a series of calculated Fsd (ndarray)
      sa is a series of solar altitude values (ndarray)
      ts is the time step (minutes), integer
    and;
      indicators["evening"] is a dictionary containing
      indicators["evening"]["values"] is the indicator series
      indicators["evening"]["attr"] are the attributes
    Author: PRI
    Date: March 2016
    """
    ts = int(ds.globalattributes["time_step"])
    Fsd, _, _ = pfp_utils.GetSeriesasMA(ds, "Fsd")
    evening_indicator = {"values":numpy.zeros(len(Fsd), dtype=numpy.int32), "attr":{}}
    attr = evening_indicator["attr"]
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "EveningFilterLength", default="3")
    num_hours = int(opt)
    if num_hours <= 0 or num_hours >= 12:
        evening_indicator["values"] = numpy.zeros(len(Fsd))
        evening_indicator["attr"]["evening_filter_length"] = num_hours
        msg = " Evening filter period outside 0 to 12 hours, skipping ..."
        logger.warning(msg)
        return evening_indicator
    night_indicator = get_night_indicator(cf, ds)
    day_indicator = get_day_indicator(cf, ds)
    ntsperhour = int(0.5+float(60)/float(ts))
    shift = num_hours*ntsperhour
    day_indicator_shifted = numpy.roll(day_indicator["values"], shift)
    evening_indicator["values"] = night_indicator["values"]*day_indicator_shifted
    attr["evening_filter_length"] = num_hours
    return evening_indicator

def get_night_indicator(cf, ds):
    """
    Purpose:
     Returns a dictionary containing an indicator series and some attributes.
     The indicator series is 1 during night time and 0 during the day.  The
     threshold for determining night and day is the Fsd threshold
     given in the control file [Options] section.
    Usage:
     indicators["night"] = get_night_indicator(cf, ds)
     where;
      cf is a control file object
      ds is a data structure
    and;
      indicators["night"] is a dictionary containing
      indicators["night"]["values"] is the indicator series
      indicators["night"]["attr"] are the attributes
    Author: PRI
    Date: March 2016
    """
    Fsd, _, _ = pfp_utils.GetSeriesasMA(ds, "Fsd")
    # indicator = 1 ==> night, indicator = 0 ==> day
    night_indicator = {"values":numpy.zeros(len(Fsd), dtype=numpy.int32), "attr":{}}
    inds = night_indicator["values"]
    attr = night_indicator["attr"]
    # get the filter type
    filter_type = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "DayNightFilter", default="Fsd")
    attr["daynight_filter_type"] = filter_type
    use_fsdsyn = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "UseFsdsyn_threshold", default="No")
    attr["use_fsdsyn"] = use_fsdsyn
    # get the indicator series
    if filter_type.lower() == "fsd":
        # get the Fsd threshold
        Fsd_threshold = int(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "Fsd_threshold", default=10))
        attr["Fsd_threshold"] = str(Fsd_threshold)
        # we are using Fsd only to define day/night
        idx = numpy.ma.where(Fsd <= Fsd_threshold)[0]
        inds[idx] = numpy.int32(1)
    elif filter_type.lower() == "sa":
        # get the solar altitude threshold
        sa_threshold = int(pfp_utils.get_keyvaluefromcf(cf, ["Options"], "sa_threshold", default="-5"))
        attr["sa_threshold"] = str(sa_threshold)
        # we are using solar altitude to define day/night
        if "solar_altitude" not in ds.series.keys():
            pfp_ts.get_synthetic_fsd(ds)
        sa, _, _ = pfp_utils.GetSeriesasMA(ds, "solar_altitude")
        index = numpy.ma.where(sa < sa_threshold)[0]
        inds[index] = numpy.int32(1)
    else:
        msg = "Unrecognised DayNightFilter option in control file"
        raise Exception(msg)
    return night_indicator

def get_turbulence_indicator_l(ldt, L, z, d, zmdonL_threshold):
    turbulence_indicator = numpy.zeros(len(ldt),dtype=numpy.int32)
    zmdonL = (z-d)/L
    idx = numpy.ma.where(zmdonL <= zmdonL_threshold)[0]
    turbulence_indicator[idx] = numpy.int32(1)
    return turbulence_indicator

def get_turbulence_indicator_ustar(ldt, ustar, ustar_dict, ts):
    """
    Purpose:
     Returns a dictionary containing an indicator series and some attributes.
     The indicator series is 1 when ustar is above the threshold and 0 when
     ustar is below the threshold.
     By default, all day time observations are accepted regardless of ustar value.
    Usage:
     indicators["turbulence"] = get_turbulence_indicator_ustar(ldt,ustar,ustar_dict,ts)
     where;
      ldt is a list of datetimes
      ustar is a series of ustar values (ndarray)
      ustar_dict is a dictionary of ustar thresholds returned by pfp_rp.get_ustar_thresholds
      ts is the time step for ustar
    and;
     indicators["turbulence"] is a dictionary containing
      indicators["turbulence"]["values"] is the indicator series
      indicators["turbulence"]["attr"] are the attributes
    Author: PRI
    Date: March 2016
    """
    year_list = ustar_dict.keys()
    year_list.sort()
    # now loop over the years in the data to apply the ustar threshold
    turbulence_indicator = {"values":numpy.zeros(len(ldt)), "attr":{}}
    inds = turbulence_indicator["values"]
    attr = turbulence_indicator["attr"]
    attr["turbulence_filter"] = "ustar"
    for year in year_list:
        start_date = str(year)+"-01-01 00:30"
        if ts==60: start_date = str(year)+"-01-01 01:00"
        end_date = str(int(year)+1)+"-01-01 00:00"
        # get the ustar threshold
        ustar_threshold = float(ustar_dict[year]["ustar_mean"])
        attr["ustar_threshold_"+str(year)] = str(ustar_threshold)
        # get the start and end datetime indices
        si = pfp_utils.GetDateIndex(ldt,start_date,ts=ts,default=0,match='exact')
        ei = pfp_utils.GetDateIndex(ldt,end_date,ts=ts,default=len(ldt),match='exact')
        # set the QC flag
        idx = numpy.ma.where(ustar[si:ei]>=ustar_threshold)[0]
        inds[si:ei][idx] = numpy.int32(1)
    return turbulence_indicator

def get_turbulence_indicator_ustar_evg(ldt, ind_day, ind_ustar, ustar, ustar_dict):
    """
    Purpose:
     Returns a dictionary containing an indicator series and some attributes.
     The indicator series is 1 when ustar is above the threshold after sunset
     and remains 1 until ustar falls below the threshold after which it remains
     0 until the following evening.
     By default, all day time observations are accepted regardless of ustar value.
     Based on a ustar filter scheme designed by Eva van Gorsel for use at the
     Tumbarumba site.
    Usage:
     indicators["turbulence"] = get_turbulence_indicator_ustar_evg(ldt,ind_day,ustar,ustar_dict)
     where;
      ldt is a list of datetimes
      ind_day is a day/night indicator
      ustar is a series of ustar values (ndarray)
      ustar_dict is a dictionary of ustar thresholds returned by pfp_rp.get_ustar_thresholds
      ts is the time step for ustar
    and;
     indicators["turbulence"] is a dictionary containing
      indicators["turbulence"]["values"] is the indicator series
      indicators["turbulence"]["attr"] are the attributes
    Author: PRI, EVG, WW
    Date: December 2016
    """
    # differentiate the day/night indicator series, we will
    # use this value to indicate the transition from day to night
    dinds = numpy.ediff1d(ind_day, to_begin=0)
    # get the list of years
    year_list = ustar_dict.keys()
    year_list.sort()
    # now loop over the years in the data to apply the ustar threshold
    # ustar >= threshold ==> ind_ustar = 1 else ind_ustar = 0
    turbulence_indicator = {"values":ind_ustar,"attr":{}}
    attr = turbulence_indicator["attr"]
    attr["turbulence_filter"] = "ustar_evg"
    # get an array of ustar threshold values
    year = numpy.array([ldt[i].year for i in range(len(ldt))])
    ustar_threshold = numpy.zeros(len(ldt))
    for yr in year_list:
        idx = numpy.where(year==int(yr))[0]
        ustar_threshold[idx] = float(ustar_dict[yr]["ustar_mean"])
        attr["ustar_threshold_"+str(yr)] = str(ustar_dict[yr]["ustar_mean"])
    # get the indicator series
    ind_evg = ind_day.copy()
    idx = numpy.where(dinds<-0.5)[0]
    for i in idx:
        n = i
        while ustar[n]>=ustar_threshold[n]:
            ind_evg[n] = 1
            n = n+1
            if n>=len(ldt):
                break
    turbulence_indicator["values"] = turbulence_indicator["values"]*ind_evg
    return turbulence_indicator

def get_ustarthreshold_from_cf(cf,ldt):
    """
    Purpose:
     Returns a dictionary containing ustar thresholds for each year read from
     the control file.  If no [ustar_threshold] section is found then a
     default value of 0.25 is used.
    Usage:
     ustar_dict = pfp_rp.get_ustarthreshold_from_cf(cf,ldt)
     where cf is the control file object
           ldt is the Python datetime series from the data structure
    Author: PRI
    Date: July 2015
    """
    ustar_dict = collections.OrderedDict()
    ustar_threshold_list = []
    if "ustar_threshold" in cf.keys():
        msg = " Using values from ustar_threshold section"
        logger.info(msg)
        for n in cf["ustar_threshold"].keys():
            ustar_string = cf["ustar_threshold"][str(n)]
            ustar_list = ustar_string.split(",")
            ustar_threshold_list.append(ustar_list)
        for item in ustar_threshold_list:
            startdate = dateutil.parser.parse(item[0])
            year = startdate.year
            ustar_dict[str(year)] = {}
            ustar_dict[str(year)]["ustar_mean"] = float(item[2])
    else:
        logger.error(" No [ustar_threshold] section in control file")
        logger.error(" ... using default value of 0.25 m/s")
        startyear = ldt[0].year
        endyear = ldt[-1].year
        years = range(startyear,endyear+1)
        for year in years:
            ustar_dict[str(year)] = {}
            ustar_dict[str(year)]["ustar_mean"] = float(0.25)
    return ustar_dict

def get_ustarthreshold_from_cpdresults(cf):
    """
    Purpose:
     Returns a dictionary containing ustar thresholds for each year read from
     the CPD results file.  If there is no CPD results file name found in the
     control file then return an empty dictionary
    Usage:
     ustar_dict = pfp_rp.get_ustarthreshold_from_cpdresults(cf)
     where cf is the control file object
           ustar_dict is a dictionary of ustar thtresholds, 1 entry per year
    Author: PRI
    Date: July 2015
    """
    ustar_dict = collections.OrderedDict()
    if "cpd_filename" not in cf["Files"]:
        msg = " CPD results filename not in control file"
        logger.warning(msg)
        return ustar_dict
    cpd_path = cf["Files"]["file_path"]
    cpd_name = cpd_path+cf["Files"]["cpd_filename"]
    cpd_wb = xlrd.open_workbook(cpd_name)
    annual_ws = cpd_wb.sheet_by_name("Annual")
    header_list = [x for x in annual_ws.row_values(0)]
    year_list = [str(int(x)) for x in annual_ws.col_values(0)[1:]]
    for i,year in enumerate(year_list):
        ustar_dict[year] = collections.OrderedDict()
        for item in header_list:
            xlcol = header_list.index(item)
            val = annual_ws.col_values(xlcol)[i+1]
            typ = annual_ws.col_types(xlcol)[i+1]
            if typ==2:
                ustar_dict[year][item] = float(val)
            else:
                ustar_dict[year][item] = float(c.missing_value)
    return ustar_dict

def get_ustar_thresholds_annual(ldt,ustar_threshold):
    """
    Purpose:
     Returns a dictionary containing ustar thresholds for all years using
     a single value enetred as the ustar_threshold argument.
    Usage:
     ustar_dict = pfp_rp.get_ustar_thresholds_annual(ldt,ustar_threshold)
     where ldt is a list of datetime objects
           ustar_threshold is the value to be used
    Author: PRI
    Date: July 2015
    """
    ustar_dict = collections.OrderedDict()
    if not isinstance(ustar_threshold,float):
        ustar_threshold = float(ustar_threshold)
    start_year = ldt[0].year
    end_year = ldt[-1].year
    for year in range(start_year,end_year+1):
        ustar_dict[year] = {}
        ustar_dict[year]["ustar_mean"] = ustar_threshold
    return ustar_dict

def L6_summary(cf, ds):
    """
    Purpose:
     Produce summaries of L6 data, write them to an Excel spreadsheet and plot them.
    Usage:
    Author: PRI
    Date: June 2015
    """
    logger.info("Doing the L6 summary")
    # set up a dictionary of lists
    series_dict = L6_summary_createseriesdict(cf, ds)
    # open the Excel workbook
    out_name = pfp_io.get_outfilenamefromcf(cf)
    xl_name = out_name.replace(".nc", "_Summary.xls")
    try:
        xl_file = pfp_io.xl_open_write(xl_name)
    except IOError:
        msg = " L6_summary: error opening Excel file " + xl_name
        logger.error(msg)
        return 0
    # open the netCDF file for the summary results
    nc_name = out_name.replace(".nc", "_Summary.nc")
    try:
        nc_file = pfp_io.nc_open_write(nc_name, nctype='NETCDF4')
        pfp_io.nc_write_globalattributes(nc_file, ds, flag_defs=False)
    except IOError:
        msg = " L6_summary: error opening netCDF file " + nc_name
        logger.error(msg)
        return 0
    # daily averages and totals
    daily_dict = L6_summary_daily(ds, series_dict)
    L6_summary_write_xlfile(xl_file, "Daily (all)", daily_dict)
    L6_summary_write_ncfile(nc_file, "Daily_all", daily_dict)
    #flag_dict = L6_summary_daily_flag(ds,series_dict)
    fluxes_dict = L6_summary_co2andh2o_fluxes(ds, series_dict, daily_dict)
    L6_summary_write_xlfile(xl_file, "Daily (CO2,H2O)", fluxes_dict)
    L6_summary_write_ncfile(nc_file, "Daily_CO2_H2O", fluxes_dict)
    # monthly averages and totals
    monthly_dict = L6_summary_monthly(ds, series_dict)
    L6_summary_write_xlfile(xl_file, "Monthly", monthly_dict)
    L6_summary_write_ncfile(nc_file, "Monthly", monthly_dict)
    # annual averages and totals
    annual_dict = L6_summary_annual(ds, series_dict)
    L6_summary_write_xlfile(xl_file, "Annual", annual_dict)
    L6_summary_write_ncfile(nc_file, "Annual", annual_dict)
    # cumulative totals
    cumulative_dict = L6_summary_cumulative(ds, series_dict)
    for year in cumulative_dict.keys():
        L6_summary_write_xlfile(xl_file, "Cummulative("+str(year)+")", cumulative_dict[str(year)])
        L6_summary_write_ncfile(nc_file, "Cummulative_"+str(year), cumulative_dict[str(year)])
    # close the Excel workbook
    xl_file.save(xl_name)
    # close the netCDF file
    nc_file.close()
    # plot the daily averages and sums
    L6_summary_plotdaily(cf, ds, daily_dict)
    # plot the cumulative sums
    L6_summary_plotcumulative(cf, ds, cumulative_dict)

def L6_summary_plotdaily(cf, ds, daily_dict):
    """
    Purpose:
     Plot the daily averages or sums with a 30 day filter.
    Usage:
     L6_summary_plotdaily(daily_dict)
     where daily_dict is the dictionary of results returned by L6_summary_daily
    Author: PRI
    Date: June 2015
    """
    ddv = daily_dict["variables"]
    type_list = []
    for item in ddv.keys():
        if item[0:2] == "ER": type_list.append(item[2:])
    for item in type_list:
        if "NEE" + item not in ddv or "GPP" + item not in ddv:
            type_list.remove(item)
    # plot time series of NEE, GPP and ER
    sdate = ddv["DateTime"]["data"][0].strftime("%d-%m-%Y")
    edate = ddv["DateTime"]["data"][-1].strftime("%d-%m-%Y")
    site_name = ds.globalattributes["site_name"]
    title_str = site_name+": "+sdate+" to "+edate
    for item in type_list:
        if cf["Options"]["call_mode"].lower()=="interactive":
            plt.ion()
        else:
            plt.ioff()
        fig = plt.figure(figsize=(16,4))
        fig.canvas.set_window_title("Carbon Budget: "+item.replace("_",""))
        plt.figtext(0.5,0.95,title_str,horizontalalignment='center')
        plt.plot(ddv["DateTime"]["data"],ddv["NEE"+item]["data"],'b-',alpha=0.3)
        plt.plot(ddv["DateTime"]["data"],pfp_ts.smooth(ddv["NEE"+item]["data"],window_len=30),
                 'b-',linewidth=2,label="NEE"+item+" (30 day filter)")
        plt.plot(ddv["DateTime"]["data"],ddv["GPP"+item]["data"],'g-',alpha=0.3)
        plt.plot(ddv["DateTime"]["data"],pfp_ts.smooth(ddv["GPP"+item]["data"],window_len=30),
                 'g-',linewidth=2,label="GPP"+item+" (30 day filter)")
        plt.plot(ddv["DateTime"]["data"],ddv["ER"+item]["data"],'r-',alpha=0.3)
        plt.plot(ddv["DateTime"]["data"],pfp_ts.smooth(ddv["ER"+item]["data"],window_len=30),
                 'r-',linewidth=2,label="ER"+item+" (30 day filter)")
        plt.axhline(0)
        plt.xlabel("Date")
        plt.ylabel(ddv["NEE"+item]["attr"]["units"])
        plt.legend(loc='upper left',prop={'size':8})
        plt.tight_layout()
        sdt = ddv["DateTime"]["data"][0].strftime("%Y%m%d")
        edt = ddv["DateTime"]["data"][-1].strftime("%Y%m%d")
        plot_path = os.path.join(cf["Files"]["plot_path"], "L6", "")
        if not os.path.exists(plot_path): os.makedirs(plot_path)
        figure_name = site_name.replace(" ","")+"_CarbonBudget"+item+"_"+sdt+"_"+edt+'.png'
        figure_path = os.path.join(plot_path, figure_name)
        fig.savefig(figure_path, format='png')
        if cf["Options"]["call_mode"].lower()=="interactive":
            plt.draw()
            mypause(1)
            plt.ioff()
        else:
            plt.close(fig)
            plt.ion()
    # plot time series of Fn,Fg,Fh,Fe
    if cf["Options"]["call_mode"].lower()=="interactive":
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(figsize=(16,4))
    fig.canvas.set_window_title("Surface Energy Budget")
    plt.figtext(0.5,0.95,title_str,horizontalalignment='center')
    for label, line in zip(["Fn", "Fg", "Fh", "Fe"], ["k-", "g-", "r-", "b-"]):
        if label in daily_dict["variables"]:
            plt.plot(ddv["DateTime"]["data"], ddv[label]["data"], line, alpha=0.3)
            plt.plot(ddv["DateTime"]["data"], pfp_ts.smooth(ddv[label]["data"], window_len=30),
                     line, linewidth=2, label=label+" (30 day filter)")
    plt.xlabel("Date")
    plt.ylabel(ddv["Fn"]["attr"]["units"])
    plt.legend(loc='upper left',prop={'size':8})
    plt.tight_layout()
    sdt = ddv["DateTime"]["data"][0].strftime("%Y%m%d")
    edt = ddv["DateTime"]["data"][-1].strftime("%Y%m%d")
    plot_path = cf["Files"]["plot_path"]+"L6/"
    if not os.path.exists(plot_path): os.makedirs(plot_path)
    figname = plot_path+site_name.replace(" ","")+"_SEB"
    figname = figname+"_"+sdt+"_"+edt+'.png'
    fig.savefig(figname,format='png')
    if cf["Options"]["call_mode"].lower()=="interactive":
        plt.draw()
        mypause(1)
        plt.ioff()
    else:
        plt.close(fig)
        plt.ion()

def L6_summary_plotcumulative(cf, ds, cumulative_dict):
    # cumulative plots
    color_list = ["blue","red","green","yellow","magenta","black","cyan","brown"]
    year_list = cumulative_dict.keys()
    year_list.sort()
    cdy0 = cumulative_dict[year_list[0]]
    type_list = []
    for item in cdy0["variables"].keys():
        if item[0:2]=="ER": type_list.append(item[2:])
    for item in type_list:
        if "NEE"+item not in cdy0["variables"] or "GPP"+item not in cdy0["variables"]:
            type_list.remove(item)
    # do the plots
    site_name = ds.globalattributes["site_name"]
    title_str = site_name+": "+year_list[0]+" to "+year_list[-1]
    # get lists of X labels (letter of month) and position
    xlabels = numpy.array(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    xlabel_posn = numpy.array([0,31, 59, 89, 120, 150, 181, 212, 242, 273, 303, 334])/float(366)
    for item in type_list:
        if cf["Options"]["call_mode"].lower()=="interactive":
            plt.ion()
        else:
            plt.ioff()
        fig = plt.figure(figsize=(8,8))
        fig.canvas.set_window_title("Cumulative plots: "+item.replace("_",""))
        plt.suptitle(title_str)
        plt.subplot(221)
        plt.title("NEE: "+item.replace("_",""),fontsize=12)
        for n,year in enumerate(year_list):
            cdyv = cumulative_dict[year]["variables"]
            cdyt = cdyv["DateTime"]["data"]
            cyf = [pfp_utils.get_yearfractionfromdatetime(dt) - int(year) for dt in cdyt]
            plt.plot(cyf, cdyv["NEE"+item]["data"], color=color_list[numpy.mod(n,8)],
                     label=str(year))
        plt.xlim([0, 1])
        pylab.xticks(xlabel_posn, xlabels)
        plt.xlabel("Month")
        plt.ylabel(cdyv["NEE"+item]["attr"]["units"])
        plt.legend(loc='lower left',prop={'size':8})

        plt.subplot(222)
        plt.title("GPP: "+item.replace("_",""),fontsize=12)
        for n,year in enumerate(year_list):
            cdyv = cumulative_dict[year]["variables"]
            cdyt = cdyv["DateTime"]["data"]
            cyf = [pfp_utils.get_yearfractionfromdatetime(dt) - int(year) for dt in cdyt]
            plt.plot(cyf, cdyv["GPP"+item]["data"],color=color_list[numpy.mod(n,8)],
                     label=str(year))
        plt.xlim([0, 1])
        pylab.xticks(xlabel_posn, xlabels)
        plt.xlabel("Month")
        plt.ylabel(cdyv["GPP"+item]["attr"]["units"])
        plt.legend(loc='lower right',prop={'size':8})

        plt.subplot(223)
        plt.title("ER: "+item.replace("_",""),fontsize=12)
        for n,year in enumerate(year_list):
            cdyv = cumulative_dict[year]["variables"]
            cdyt = cdyv["DateTime"]["data"]
            cyf = [pfp_utils.get_yearfractionfromdatetime(dt) - int(year) for dt in cdyt]
            plt.plot(cyf, cdyv["ER"+item]["data"],color=color_list[numpy.mod(n,8)],
                     label=str(year))
        plt.xlim([0, 1])
        pylab.xticks(xlabel_posn, xlabels)
        plt.xlabel("Month")
        plt.ylabel(cdyv["ER"+item]["attr"]["units"])
        plt.legend(loc='lower right',prop={'size':8})

        plt.subplot(224)
        plt.title("ET & Precip",fontsize=12)
        for n,year in enumerate(year_list):
            cdyv = cumulative_dict[year]["variables"]
            cdyt = cdyv["DateTime"]["data"]
            cyf = [pfp_utils.get_yearfractionfromdatetime(dt) - int(year) for dt in cdyt]
            plt.plot(cyf, cdyv["ET"]["data"],color=color_list[numpy.mod(n,8)],
                     label=str(year))
            plt.plot(cyf, cdyv["Precip"]["data"],color=color_list[numpy.mod(n,8)],
                     linestyle='--')
        plt.xlim([0, 1])
        pylab.xticks(xlabel_posn, xlabels)
        plt.xlabel("Month")
        plt.ylabel(cdyv["ET"]["attr"]["units"])
        plt.legend(loc='upper left',prop={'size':8})
        plt.tight_layout(rect=[0, 0, 1, 0.98])
        # save a hard copy of the plot
        sdt = year_list[0]
        edt = year_list[-1]
        plot_path = os.path.join(cf["Files"]["plot_path"], "L6", "")
        if not os.path.exists(plot_path): os.makedirs(plot_path)
        figure_name = site_name.replace(" ", "")+"_Cumulative"+item+"_"+sdt+"_"+edt+'.png'
        figure_path = os.path.join(plot_path, figure_name)
        fig.savefig(figure_path, format='png')
        if cf["Options"]["call_mode"].lower()=="interactive":
            plt.draw()
            mypause(1)
            plt.ioff()
        else:
            plt.close(fig)
            plt.ion()

def L6_summary_createseriesdict(cf,ds):
    """
    Purpose:
     Create a dictionary containing lists of variables, operators and formats
    for use by the daily, annual and cumulative routines.
    Usage:
     series_dict = L6_summary_createseriesdict(cf,ds)
     where cf is a control file object
           ds is an OzFluxQC data structure
           series_dict is a dictionary of various variable lists
    Author: PRI
    Date: June 2015
    """
    series_dict = {"daily":{},"annual":{},"cumulative":{},"lists":{}}
    # adjust units of NEE, NEP, GPP and ER
    sdl = series_dict["lists"]
    sdl["nee"] = [item for item in cf["NetEcosystemExchange"].keys() if "NEE" in item[0:3] and item in ds.series.keys()]
    sdl["gpp"] = [item for item in cf["GrossPrimaryProductivity"].keys() if "GPP" in item[0:3] and item in ds.series.keys()]
    sdl["fre"] = [item for item in cf["EcosystemRespiration"].keys() if "ER" in item[0:2] and item in ds.series.keys()]
    sdl["nep"] = [item.replace("NEE","NEP") for item in sdl["nee"]]
    sdl["nep"] = [item for item in sdl["nep"] if item in ds.series.keys()]
    sdl["co2"] = sdl["nee"]+sdl["nep"]+sdl["gpp"]+sdl["fre"]
    for item in sdl["co2"]:
        series_dict["daily"][item] = {}
        series_dict["cumulative"][item] = {}
        series_dict["daily"][item]["operator"] = "sum"
        series_dict["daily"][item]["format"] = "0.00"
        series_dict["cumulative"][item]["operator"] = "sum"
        series_dict["cumulative"][item]["format"] = "0.00"
    sdl["ET"] = [item for item in ds.series.keys() if "ET" in item[0:2]]
    sdl["Precip"] = [item for item in ds.series.keys() if "Precip" in item[0:6]]
    sdl["h2o"] = sdl["ET"]+sdl["Precip"]
    for item in sdl["h2o"]:
        series_dict["daily"][item] = {"operator":"sum","format":"0.00"}
        series_dict["cumulative"][item] = {"operator":"sum","format":"0.00"}
    if "Ah" in ds.series.keys():
        series_dict["daily"]["Ah"] = {"operator":"average","format":"0.00"}
    if "Cc" in ds.series.keys():
        series_dict["daily"]["Cc"] = {"operator":"average","format":"0.0"}
    if "Fc" in ds.series.keys():
        series_dict["daily"]["Fc"] = {"operator":"average","format":"0.00"}
    if "Fe" in ds.series.keys():
        series_dict["daily"]["Fe"] = {"operator":"average","format":"0.0"}
    if "Fh" in ds.series.keys():
        series_dict["daily"]["Fh"] = {"operator":"average","format":"0.0"}
    if "Fg" in ds.series.keys():
        series_dict["daily"]["Fg"] = {"operator":"average","format":"0.0"}
    if "Fn" in ds.series.keys():
        series_dict["daily"]["Fn"] = {"operator":"average","format":"0.0"}
    if "Fsd" in ds.series.keys():
        series_dict["daily"]["Fsd"] = {"operator":"average","format":"0.0"}
    if "Fsu" in ds.series.keys():
        series_dict["daily"]["Fsu"] = {"operator":"average","format":"0.0"}
    if "Fld" in ds.series.keys():
        series_dict["daily"]["Fld"] = {"operator":"average","format":"0.0"}
    if "Flu" in ds.series.keys():
        series_dict["daily"]["Flu"] = {"operator":"average","format":"0.0"}
    if "ps" in ds.series.keys():
        series_dict["daily"]["ps"] = {"operator":"average","format":"0.00"}
    if "q" in ds.series.keys():
        series_dict["daily"]["q"] = {"operator":"average","format":"0.0000"}
    if "RH" in ds.series.keys():
        series_dict["daily"]["RH"] = {"operator":"average","format":"0"}
    if "Sws" in ds.series.keys():
        series_dict["daily"]["Sws"] = {"operator":"average","format":"0.000"}
    if "Ta" in ds.series.keys():
        series_dict["daily"]["Ta"] = {"operator":"average","format":"0.00"}
    if "Ts" in ds.series.keys():
        series_dict["daily"]["Ts"] = {"operator":"average","format":"0.00"}
    if "ustar" in ds.series.keys():
        series_dict["daily"]["ustar"] = {"operator":"average","format":"0.00"}
    if "Ws" in ds.series.keys():
        series_dict["daily"]["Ws"] = {"operator":"average","format":"0.00"}
    series_dict["annual"] = series_dict["daily"]
    series_dict["monthly"] = series_dict["daily"]
    return series_dict

def L6_summary_daily(ds, series_dict):
    """
    Purpose:
     Calculate the daily averages or sums of various quantities and write
     them to a worksheet in an Excel workbook.
    Usage:
     L6_summary_daily(ds, series_dict)
     where ds is an OzFluxQC data structure
           series_dict is a dictionary of various variable lists
    Author: PRI
    Date: June 2015
    """
    logger.info(" Doing the daily summary (data) at L6")
    dt = ds.series["DateTime"]["Data"]
    ts = int(ds.globalattributes["time_step"])
    si = pfp_utils.GetDateIndex(dt,str(dt[0]),ts=ts,default=0,match="startnextday")
    ei = pfp_utils.GetDateIndex(dt,str(dt[-1]),ts=ts,default=len(dt)-1,match="endpreviousday")
    ldt = dt[si:ei+1]
    ntsInDay = int(24.0*60.0/float(ts))
    nDays = int(len(ldt))/ntsInDay
    # create an empty data array and an array of zeros for the flag
    f0 = numpy.zeros(nDays, dtype=numpy.int32)
    ldt_daily = [ldt[0]+datetime.timedelta(days=i) for i in range(0,nDays)]
    # create a dictionary to hold the daily statistics
    daily_dict = {"globalattributes":{},"variables":{}}
    # copy the global attributes
    daily_dict["globalattributes"] = copy.deepcopy(ds.globalattributes)
    # create the datetime variable
    daily_dict["variables"]["DateTime"] = {"data":ldt_daily,
                                           "flag":f0,
                                           "attr":{"units":"Days","format":"dd/mm/yyyy",
                                                   "time_step":"Daily"}}
    series_list = series_dict["daily"].keys()
    series_list.sort()
    for item in series_list:
        if item not in ds.series.keys(): continue
        daily_dict["variables"][item] = {"data":[],"attr":{}}
        variable = pfp_utils.GetVariable(ds, item, start=si, end=ei)
        if item in series_dict["lists"]["co2"]:
            variable = pfp_utils.convert_units_func(ds, variable, "gC/m2")
            daily_dict["variables"][item]["attr"]["units"] = "gC/m2"
        else:
            daily_dict["variables"][item]["attr"]["units"] = variable["Attr"]["units"]
        data_2d = variable["Data"].reshape(nDays, ntsInDay)
        if series_dict["daily"][item]["operator"].lower() == "average":
            daily_dict["variables"][item]["data"] = numpy.ma.average(data_2d, axis=1)
        elif series_dict["daily"][item]["operator"].lower() == "sum":
            daily_dict["variables"][item]["data"] = numpy.ma.sum(data_2d, axis=1)
            daily_dict["variables"][item]["attr"]["units"] = daily_dict["variables"][item]["attr"]["units"]+"/day"
        else:
            msg = "Unrecognised operator ("+series_dict["daily"][item]["operator"]
            msg = msg+") for series "+item
            logger.error(msg)
            continue
        # add the format to be used
        daily_dict["variables"][item]["attr"]["format"] = series_dict["daily"][item]["format"]
        # now do the flag, this is the fraction of data with QC flag = 0 in the day
        daily_dict["variables"][item]["flag"] = numpy.zeros(nDays, dtype=numpy.float64)
        flag_2d = variable["Flag"].reshape(nDays, ntsInDay)
        for i in range(nDays):
            daily_dict["variables"][item]["flag"][i] = 1-float(numpy.count_nonzero(flag_2d[i,:]))/float(ntsInDay)
    return daily_dict

def L6_summary_co2andh2o_fluxes(ds, series_dict, daily_dict):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: March 2016
    """
    logger.info(" Doing the daily summary (fluxes) at L6")
    sdl = series_dict["lists"]
    series_list = sdl["h2o"]+sdl["co2"]
    fluxes_dict = {"globalattributes":{}, "variables":{}}
    # copy the global attributes
    fluxes_dict["globalattributes"] = copy.deepcopy(ds.globalattributes)
    # create the datetime variable
    fluxes_dict["variables"]["DateTime"] = daily_dict["variables"]["DateTime"]
    for item in series_list:
        fluxes_dict["variables"][item] = {}
        fluxes_dict["variables"][item]["data"] = daily_dict["variables"][item]["data"]
        fluxes_dict["variables"][item]["attr"] = daily_dict["variables"][item]["attr"]
        fluxes_dict["variables"][item+"_flag"] = {}
        fluxes_dict["variables"][item+"_flag"]["data"] = daily_dict["variables"][item]["flag"]
        fluxes_dict["variables"][item+"_flag"]["attr"] = {"units":"frac","format":"0.00"}
    return fluxes_dict

def L6_summary_write_ncfile(nc_file, nc_group, data_dict):
    """
    Purpose:
     Write the L6 summary statistics (daily, monthly, annual and cummulative)
     to a single netCDF file with different groups for each time period.
    Usage:
    Author: PRI
    Date: January 2018
    """
    # create the group in the netCDF file
    nc_group = nc_file.createGroup(nc_group)
    # write the data to the group
    pfp_io.nc_write_data(nc_group, data_dict)
    return

def L6_summary_write_xlfile(xl_file,sheet_name,data_dict):
    # add the daily worksheet to the summary Excel file
    xl_sheet = xl_file.add_sheet(sheet_name)
    pfp_io.xl_write_data(xl_sheet,data_dict["variables"])

def L6_summary_monthly(ds,series_dict):
    """
    Purpose:
     Calculate the monthly averages or sums of various quantities and write
     them to a worksheet in an Excel workbook.
    Usage:
     L6_summary_monthly(ds,series_dict)
     where ds is an OzFluxQC data structure
           series_dict is a dictionary of various variable lists
    Author: PRI
    Date: July 2015
    """
    logger.info(" Doing the monthly summaries at L6")
    dt = ds.series["DateTime"]["Data"]
    ts = int(ds.globalattributes["time_step"])
    si = pfp_utils.GetDateIndex(dt,str(dt[0]),ts=ts,default=0,match="startnextmonth")
    ldt = dt[si:]
    monthly_dict = {"globalattributes":{}, "variables":{}}
    # copy the global attributes
    monthly_dict["globalattributes"] = copy.deepcopy(ds.globalattributes)
    monthly_dict["variables"]["DateTime"] = {"data":[],
                                             "flag":numpy.array([]),
                                             "attr":{"units":"Months", "format":"dd/mm/yyyy",
                                                     "time_step":"Monthly"}}
    # create arrays in monthly_dict
    series_list = series_dict["monthly"].keys()
    series_list.sort()
    # create the data arrays
    for item in series_list:
        monthly_dict["variables"][item] = {"data":numpy.ma.array([]),
                                           "flag":numpy.array([]),
                                           "attr":{"units":'',"format":''}}
    # loop over the months in the data file
    start_date = ldt[0]
    end_date = start_date+dateutil.relativedelta.relativedelta(months=1)
    end_date = end_date-dateutil.relativedelta.relativedelta(minutes=ts)
    last_date = ldt[-1]
    while start_date<=last_date:
        # *** The Elise Pendall bug fix ***
        si = pfp_utils.GetDateIndex(dt, str(start_date), ts=ts, default=0)
        ei = pfp_utils.GetDateIndex(dt, str(end_date), ts=ts, default=len(dt)-1)
        monthly_dict["variables"]["DateTime"]["data"].append(dt[si])
        for item in series_list:
            if item not in ds.series.keys(): continue
            variable = pfp_utils.GetVariable(ds, item, start=si, end=ei)
            if item in series_dict["lists"]["co2"]:
                variable = pfp_utils.convert_units_func(ds, variable, "gC/m2")
                monthly_dict["variables"][item]["attr"]["units"] = "gC/m2"
            else:
                monthly_dict["variables"][item]["attr"]["units"] = variable["Attr"]["units"]
            if series_dict["monthly"][item]["operator"].lower()=="average":
                monthly_dict["variables"][item]["data"] = numpy.append(monthly_dict["variables"][item]["data"],
                                                                       numpy.ma.average(variable["Data"]))
            elif series_dict["monthly"][item]["operator"].lower()=="sum":
                monthly_dict["variables"][item]["data"] = numpy.append(monthly_dict["variables"][item]["data"],
                                                                       numpy.ma.sum(variable["Data"]))
                monthly_dict["variables"][item]["attr"]["units"] = monthly_dict["variables"][item]["attr"]["units"]+"/month"
            else:
                msg = "L6_summary_monthly: unrecognised operator"
                logger.error(msg)
            monthly_dict["variables"][item]["attr"]["format"] = series_dict["monthly"][item]["format"]
        start_date = end_date+dateutil.relativedelta.relativedelta(minutes=ts)
        end_date = start_date+dateutil.relativedelta.relativedelta(months=1)
        end_date = end_date-dateutil.relativedelta.relativedelta(minutes=ts)
    return monthly_dict

def L6_summary_annual(ds, series_dict):
    """
    Purpose:
     Calculate the annual averages or sums of various quantities and write
     them to a worksheet in an Excel workbook.
    Usage:
     L6_summary_annual(ds,series_dict)
     where ds is an OzFluxQC data structure
           series_dict is a dictionary of various variable lists
    Author: PRI
    Date: June 2015
    """
    logger.info(" Doing the annual summaries at L6")
    dt = ds.series["DateTime"]["Data"]
    ts = int(ds.globalattributes["time_step"])
    nperDay = int(24/(float(ts)/60.0)+0.5)
    si = pfp_utils.GetDateIndex(dt, str(dt[0]), ts=ts, default=0, match="startnextday")
    ei = pfp_utils.GetDateIndex(dt, str(dt[-1]), ts=ts, default=len(dt)-1, match="endpreviousday")
    ldt = dt[si:ei+1]
    start_year = ldt[0].year
    end_year = ldt[-1].year
    year_list = range(start_year, end_year+1, 1)
    nYears = len(year_list)
    annual_dict = {"globalattributes":{}, "variables":{}}
    # copy the global attributes
    annual_dict["globalattributes"] = copy.deepcopy(ds.globalattributes)
    annual_dict["variables"]["DateTime"] = {"data":[datetime.datetime(yr,1,1) for yr in year_list],
                                            "flag":numpy.zeros(nYears, dtype=numpy.int32),
                                            "attr":{"units":"Years", "format":"dd/mm/yyyy",
                                                    "time_step":"Annual"}}
    annual_dict["variables"]["nDays"] = {"data":numpy.full(nYears, c.missing_value, dtype=numpy.float64),
                                         "flag":numpy.zeros(nYears, dtype=numpy.int32),
                                         "attr":{"units":"Number of days","format":"0"}}
    # create arrays in annual_dict
    series_list = series_dict["annual"].keys()
    series_list.sort()
    for item in series_list:
        annual_dict["variables"][item] = {"data":numpy.ma.array([float(-9999)]*len(year_list)),
                                          "flag":numpy.zeros(nYears, dtype=numpy.int32),
                                          "attr":{"units":"Number of days","format":"0"}}
    for i,year in enumerate(year_list):
        if ts==30:
            start_date = str(year)+"-01-01 00:30"
        elif ts==60:
            start_date = str(year)+"-01-01 01:00"
        end_date = str(year+1)+"-01-01 00:00"
        si = pfp_utils.GetDateIndex(dt,start_date,ts=ts,default=0)
        ei = pfp_utils.GetDateIndex(dt,end_date,ts=ts,default=len(dt)-1)
        nDays = int((ei-si+1)/nperDay+0.5)
        annual_dict["variables"]["nDays"]["data"][i] = nDays
        for item in series_list:
            if item not in ds.series.keys(): continue
            variable = pfp_utils.GetVariable(ds, item, start=si, end=ei)
            if item in series_dict["lists"]["co2"]:
                variable = pfp_utils.convert_units_func(ds, variable, "gC/m2")
                annual_dict["variables"][item]["attr"]["units"] = "gC/m2"
            else:
                annual_dict["variables"][item]["attr"]["units"] = variable["Attr"]["units"]
            if series_dict["annual"][item]["operator"].lower()=="average":
                annual_dict["variables"][item]["data"][i] = numpy.ma.average(variable["Data"])
            elif series_dict["annual"][item]["operator"].lower()=="sum":
                annual_dict["variables"][item]["data"][i] = numpy.ma.sum(variable["Data"])
                annual_dict["variables"][item]["attr"]["units"] = annual_dict["variables"][item]["attr"]["units"]+"/year"
            else:
                msg = "L6_summary_annual: unrecognised operator"
                logger.error(msg)
            annual_dict["variables"][item]["attr"]["format"] = series_dict["annual"][item]["format"]
    return annual_dict

def L6_summary_cumulative(ds, series_dict):
    """
    Purpose:
     Calculate the cumulative sums of various quantities and write
     them to a worksheet in an Excel workbook.
    Usage:
     L6_summary_cumulative(xl_file,ds,series_dict)
     where xl_file is an Excel file object
           ds is an OzFluxQC data structure
           series_dict is a dictionary of various variable lists
    Author: PRI
    Date: June 2015
    """
    logger.info(" Doing the cumulative summaries at L6")
    dt = ds.series["DateTime"]["Data"]
    ts = int(ds.globalattributes["time_step"])
    si = pfp_utils.GetDateIndex(dt, str(dt[0]), ts=ts, default=0, match="startnextday")
    ei = pfp_utils.GetDateIndex(dt, str(dt[-1]), ts=ts, default=len(dt)-1, match="endpreviousday")
    ldt = dt[si:ei+1]
    start_year = ldt[0].year
    end_year = ldt[-1].year
    year_list = range(start_year, end_year+1, 1)
    series_list = series_dict["cumulative"].keys()
    cumulative_dict = {}
    for year in year_list:
        cumulative_dict[str(year)] = cdyr = {"globalattributes":{}, "variables":{}}
        # copy the global attributes
        cdyr["globalattributes"] = copy.deepcopy(ds.globalattributes)
        if ts==30:
            start_date = str(year)+"-01-01 00:30"
        elif ts==60:
            start_date = str(year)+"-01-01 01:00"
        end_date = str(year+1)+"-01-01 00:00"
        si = pfp_utils.GetDateIndex(dt, start_date, ts=ts, default=0)
        ei = pfp_utils.GetDateIndex(dt, end_date, ts=ts, default=len(dt)-1)
        ldt = dt[si:ei+1]
        f0 = numpy.zeros(len(ldt), dtype=numpy.int32)
        cdyr["variables"]["DateTime"] = {"data":ldt,"flag":f0,
                                         "attr":{"units":"Year","format":"dd/mm/yyyy HH:MM",
                                                 "time_step":str(ts)}}
        for item in series_list:
            cdyr["variables"][item] = {"data":[],"attr":{}}
            variable = pfp_utils.GetVariable(ds, item, start=si, end=ei)
            if item in series_dict["lists"]["co2"]:
                variable = pfp_utils.convert_units_func(ds, variable, "gC/m2")
                cdyr["variables"][item]["attr"]["units"] = "gC/m2"
            else:
                cdyr["variables"][item]["attr"]["units"] = variable["Attr"]["units"]
            cdyr["variables"][item]["data"] = numpy.ma.cumsum(variable["Data"])
            cdyr["variables"][item]["attr"]["format"] = series_dict["cumulative"][item]["format"]
            cdyr["variables"][item]["attr"]["units"] = cdyr["variables"][item]["attr"]["units"]+"/year"
    return cumulative_dict

def ParseL6ControlFile(cf, ds):
    """
    Purpose:
     Parse the L6 control file.
    Usage:
    Side effects:
    Author: PRI
    Date: Back in the day
    """
    # create the L6 information dictionary
    l6_info = {}
    if "EcosystemRespiration" in cf.keys():
        for output in cf["EcosystemRespiration"].keys():
            if "ERUsingSOLO" in cf["EcosystemRespiration"][output].keys():
                rpSOLO_createdict(cf, ds, l6_info, output, "ERUsingSOLO")
            if "ERUsingLloydTaylor" in cf["EcosystemRespiration"][output].keys():
                pfp_rpLT.rpLT_createdict(cf, ds, l6_info, output, "ERUsingLloydTaylor")
            if "ERUsingLasslop" in cf["EcosystemRespiration"][output].keys():
                pfp_rpLL.rpLL_createdict(cf, ds, l6_info, output, "ERUsingLasslop")
            if "MergeSeries" in cf["EcosystemRespiration"][output].keys():
                rpMergeSeries_createdict(cf, ds, l6_info, output, "MergeSeries")
    if "NetEcosystemExchange" in cf.keys():
        l6_info["NetEcosystemExchange"] = {}
        for output in cf["NetEcosystemExchange"].keys():
            rpNEE_createdict(cf, ds, l6_info["NetEcosystemExchange"], output)
    if "GrossPrimaryProductivity" in cf.keys():
        l6_info["GrossPrimaryProductivity"] = {}
        for output in cf["GrossPrimaryProductivity"].keys():
            rpGPP_createdict(cf, ds, l6_info["GrossPrimaryProductivity"], output)
    return l6_info

def PartitionNEE(ds, l6_info):
    """
    Purpose:
     Partition NEE into GPP and ER.
     Input and output names are held in info['gpp'].
    Usage:
     pfp_rp.PartitionNEE(ds, info)
      where cf is a conbtrol file object
            ds is a data structure
    Side effects:
     Series to hold the GPP data are created in ds.
    Author: PRI
    Date: August 2014
    """
    if "GrossPrimaryProductivity" not in l6_info:
        return
    # calculate GPP from NEE and ER
    for label in l6_info["GrossPrimaryProductivity"].keys():
        if ("NEE" not in l6_info["GrossPrimaryProductivity"][label] and
            "ER" not in l6_info["GrossPrimaryProductivity"][label]):
            continue
        NEE_label = l6_info["GrossPrimaryProductivity"][label]["NEE"]
        ER_label = l6_info["GrossPrimaryProductivity"][label]["ER"]
        output_label = l6_info["GrossPrimaryProductivity"][label]["output"]
        NEE, NEE_flag, NEE_attr = pfp_utils.GetSeriesasMA(ds, NEE_label)
        ER, _, _ = pfp_utils.GetSeriesasMA(ds, ER_label)
        # calculate GPP
        # here we use the conventions from Chapin et al (2006)
        #  NEP = -1*NEE
        #  GPP = NEP + ER ==> GPP = -1*NEE + ER
        GPP = float(-1)*NEE + ER
        ds.series[output_label]["Data"] = GPP
        ds.series[output_label]["Flag"] = NEE_flag
        # copy the attributes
        attr = ds.series[output_label]["Attr"]
        attr["units"] = NEE_attr["units"]
        attr["long_name"] = "Gross Primary Productivity"
        attr["description_l6"] = "Calculated as -1*" + NEE_label + " + " + ER_label
        ds.series[output_label]["Attr"] = attr

def rpGPP_createdict(cf, ds, info, label):
    """ Creates a dictionary in ds to hold information about calculating GPP."""
    # create the dictionary keys for this series
    info[label] = {}
    # output series name
    info[label]["output"] = label
    # net ecosystem exchange
    default = label.replace("GPP", "NEE")
    opt = pfp_utils.get_keyvaluefromcf(cf, ["GrossPrimaryProductivity", label], "NEE", default=default)
    info[label]["NEE"] = opt
    # ecosystem respiration
    default = label.replace("GPP", "ER")
    opt = pfp_utils.get_keyvaluefromcf(cf, ["GrossPrimaryProductivity", label], "ER", default=default)
    info[label]["ER"] = opt
    # create an empty series in ds if the output series doesn't exist yet
    if info[label]["output"] not in ds.series.keys():
        data, flag, attr = pfp_utils.MakeEmptySeries(ds, info[label]["output"])
        pfp_utils.CreateSeries(ds, info[label]["output"], data, flag, attr)
    return

def rpNEE_createdict(cf, ds, info, label):
    """ Creates a dictionary in ds to hold information about calculating NEE."""
    # create the dictionary keys for this series
    info[label] = {}
    # output series name
    info[label]["output"] = label
    # CO2 flux
    sl = ["NetEcosystemExchange", label]
    opt = pfp_utils.get_keyvaluefromcf(cf, sl, "Fc", default="Fc")
    info[label]["Fc"] = opt
    Fc = pfp_utils.GetVariable(ds, opt)
    # ecosystem respiration
    default = label.replace("NEE", "ER")
    opt = pfp_utils.get_keyvaluefromcf(cf, sl, "ER", default=default)
    info[label]["ER"] = opt
    # create an empty series in ds if the output series doesn't exist yet
    if info[label]["output"] not in ds.series.keys():
        data, flag, attr = pfp_utils.MakeEmptySeries(ds, info[label]["output"])
        attr["long_name"] = "Net Ecosystem Exchange"
        attr["units"] = Fc["Attr"]["units"]
        pfp_utils.CreateSeries(ds, info[label]["output"], data, flag, attr)
    return

def rpMergeSeries_createdict(cf, ds, l6_info, label, called_by):
    """ Creates a dictionary in ds to hold information about the merging of gap filled
        and tower data."""
    nrecs = int(ds.globalattributes["nc_nrecs"])
    # create the merge directory in the info dictionary
    if called_by not in l6_info:
        l6_info[called_by] = {}
    if "standard" not in l6_info[called_by].keys():
        l6_info[called_by]["standard"] = {}
    # create the dictionary keys for this series
    l6_info[called_by]["standard"][label] = {}
    # output series name
    l6_info[called_by]["standard"][label]["output"] = label
    # source
    opt = pfp_utils.get_keyvaluefromcf(cf, ["EcosystemRespiration", label, "MergeSeries"], "Source", default="ER,ER_SOLO_all")
    sources = pfp_cfg.cfg_string_to_list(opt)
    l6_info[called_by]["standard"][label]["source"] = sources
    # create an empty series in ds if the output series doesn't exist yet
    if l6_info[called_by]["standard"][label]["output"] not in ds.series.keys():
        variable = pfp_utils.CreateEmptyVariable(label, nrecs)
        pfp_utils.CreateVariable(ds, variable)
    return

def rpSOLO_createdict(cf, ds, l6_info, output, called_by):
    """
    Purpose:
     Creates a dictionary in l6_info to hold information about the SOLO data
     used to estimate ecosystem respiration.
    Usage:
    Side effects:
    Author: PRI
    Date: Back in the day
    """
    nrecs = int(ds.globalattributes["nc_nrecs"])
    # create the dictionary keys for this series
    if called_by not in l6_info.keys():
        l6_info[called_by] = {"outputs": {}, "info": {"source": "Fc", "target": "ER"}, "gui": {}}
        # only need to create the ["info"] dictionary on the first pass
        pfp_gf.gfSOLO_createdict_info(cf, ds, l6_info, called_by)
        if ds.returncodes["value"] != 0:
            return
        # only need to create the ["gui"] dictionary on the first pass
        pfp_gf.gfSOLO_createdict_gui(cf, ds, l6_info, called_by)
    # get the outputs section
    pfp_gf.gfSOLO_createdict_outputs(cf, l6_info, output, called_by)
    # create an empty series in ds if the SOLO output series doesn't exist yet
    Fc = pfp_utils.GetVariable(ds, l6_info[called_by]["info"]["source"])
    model_outputs = cf["EcosystemRespiration"][output][called_by].keys()
    for model_output in model_outputs:
        if model_output not in ds.series.keys():
            # create an empty variable
            variable = pfp_utils.CreateEmptyVariable(model_output, nrecs)
            variable["Attr"]["long_name"] = "Ecosystem respiration"
            variable["Attr"]["drivers"] = l6_info[called_by]["outputs"][model_output]["drivers"]
            variable["Attr"]["description_l6"] = "Modeled by neural network (SOLO)"
            variable["Attr"]["target"] = l6_info[called_by]["info"]["target"]
            variable["Attr"]["source"] = l6_info[called_by]["info"]["source"]
            variable["Attr"]["units"] = Fc["Attr"]["units"]
            pfp_utils.CreateVariable(ds, variable)
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
