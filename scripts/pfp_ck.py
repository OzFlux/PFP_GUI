# standard modules
import copy
import constants as c
import datetime
import logging
import time
# 3rd party
import numpy
import dateutil.parser
# pfp modules
import pfp_rp
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

def ApplyQCChecks(variable):
    """
    Purpose:
     Apply the QC checks speified in the control file object to a single variable
    Usage:
     pfp_ck.ApplyQCChecks(variable)
     where variable is a variable dictionary as returned by pfp_utils.GetVariable()
    Author: PRI
    Date: September 2016
    """
    # do the range check
    ApplyRangeCheckToVariable(variable)
    # do the diurnal check
    #do_diurnalcheck_variable(cf,variable)
    # do exclude dates
    #do_excludedates_variable(cf,variable)
    # do exclude hours
    #do_excludehours_variable(cf,variable)
    return

def ApplyRangeCheckToVariable(variable):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: September 2016
    """
    dt = variable["DateTime"]
    # Check to see if a lower limit has been specified
    if "rangecheck_lower" in variable["Attr"]:
        attr = variable["Attr"]["rangecheck_lower"]
        lower = numpy.array(parse_rangecheck_limit(attr))
        valid_lower = str(numpy.min(lower))
        month = numpy.array([dt[i].month for i in range(0,len(dt))])
        lower_series = lower[month-1]
        index = numpy.ma.where(variable["Data"]<lower_series)[0]
        variable["Data"][index] = numpy.ma.masked
        variable["Flag"][index] = numpy.int32(2)
        valid_range = variable["Attr"]["valid_range"]
        old_lower = valid_range.split(",")[0]
        valid_range = valid_range.replace(old_lower,valid_lower)
        variable["Attr"]["valid_range"] = valid_range
    if "rangecheck_upper" in variable["Attr"]:
        attr = variable["Attr"]["rangecheck_upper"]
        upper = numpy.array(parse_rangecheck_limit(attr))
        valid_upper = str(numpy.min(upper))
        month = numpy.array([dt[i].month for i in range(0,len(dt))])
        upper_series = upper[month-1]
        index = numpy.ma.where(variable["Data"]>upper_series)[0]
        variable["Data"][index] = numpy.ma.masked
        variable["Flag"][index] = numpy.int32(2)
        valid_range = variable["Attr"]["valid_range"]
        old_upper = valid_range.split(",")[1]
        valid_range = valid_range.replace(old_upper,valid_upper)
        variable["Attr"]["valid_range"] = valid_range
    return

def ApplyTurbulenceFilter(cf, ds, l5_info, ustar_threshold=None):
    """
    Purpose:
    Usage:
    Author:
    Date:
    """
    iris = l5_info["RemoveIntermediateSeries"]
    opt = ApplyTurbulenceFilter_checks(cf,ds)
    if not opt["OK"]:
        return
    # local point to datetime series
    ldt = ds.series["DateTime"]["Data"]
    # time step
    ts = int(ds.globalattributes["time_step"])
    # dictionary of utar thresold values
    if ustar_threshold==None:
        ustar_dict = pfp_rp.get_ustar_thresholds(cf, ds)
    else:
        ustar_dict = pfp_rp.get_ustar_thresholds_annual(ldt,ustar_threshold)
    # initialise a dictionary for the indicator series
    indicators = {}
    # get data for the indicator series
    ustar,ustar_flag,ustar_attr = pfp_utils.GetSeriesasMA(ds,"ustar")
    #Fsd,f,a = pfp_utils.GetSeriesasMA(ds,"Fsd")
    #if "solar_altitude" not in ds.series.keys():
        #pfp_ts.get_synthetic_fsd(ds)
    #Fsd_syn,f,a = pfp_utils.GetSeriesasMA(ds,"Fsd_syn")
    #sa,f,a = pfp_utils.GetSeriesasMA(ds,"solar_altitude")
    # get the day/night indicator series
    # indicators["day"] = 1 ==> day time, indicators["day"] = 0 ==> night time
    #indicators["day"] = pfp_rp.get_day_indicator(cf,Fsd,Fsd_syn,sa)
    indicators["day"] = pfp_rp.get_day_indicator(cf, ds)
    ind_day = indicators["day"]["values"]
    # get the turbulence indicator series
    if opt["turbulence_filter"].lower() == "ustar":
        # indicators["turbulence"] = 1 ==> turbulent, indicators["turbulence"] = 0 ==> not turbulent
        indicators["turbulence"] = pfp_rp.get_turbulence_indicator_ustar(ldt, ustar, ustar_dict, ts)
    elif opt["turbulence_filter"].lower() == "ustar_evg":
        # ustar >= threshold ==> ind_ustar = 1, ustar < threshold == ind_ustar = 0
        indicators["ustar"] = pfp_rp.get_turbulence_indicator_ustar(ldt, ustar, ustar_dict, ts)
        ind_ustar = indicators["ustar"]["values"]
        # ustar >= threshold during day AND ustar has been >= threshold since sunset ==> indicators["turbulence"] = 1
        # indicators["turbulence"] = 0 during night once ustar has dropped below threshold even if it
        # increases above the threshold later in the night
        indicators["turbulence"] = pfp_rp.get_turbulence_indicator_ustar_evg(ldt, ind_day, ind_ustar, ustar, ustar_dict)
    elif opt["turbulence_filter"].lower() == "l":
        #indicators["turbulence] = get_turbulence_indicator_l(ldt,L,z,d,zmdonL_threshold)
        indicators["turbulence"] = numpy.ones(len(ldt))
        msg = " Use of L as turbulence indicator not implemented, no filter applied"
        logger.warning(msg)
    else:
        msg = " Unrecognised turbulence filter option ("
        msg = msg + opt["turbulence_filter"] + "), no filter applied"
        logger.error(msg)
        return
    # initialise the final indicator series as the turbulence indicator
    # subsequent filters will modify the final indicator series
    # we must use copy.deepcopy() otherwise the "values" array will only
    # be copied by reference not value.  Damn Python's default of copy by reference!
    indicators["final"] = copy.deepcopy(indicators["turbulence"])
    # check to see if the user wants to accept all day time observations
    # regardless of ustar value
    if opt["accept_day_times"].lower()=="yes":
        # if yes, then we force the final indicator to be 1
        # if ustar is below the threshold during the day.
        idx = numpy.where(indicators["day"]["values"]==1)[0]
        indicators["final"]["values"][idx] = numpy.int(1)
        indicators["final"]["attr"].update(indicators["day"]["attr"])
    # get the evening indicator series
    #indicators["evening"] = pfp_rp.get_evening_indicator(cf,Fsd,Fsd_syn,sa,ts)
    indicators["evening"] = pfp_rp.get_evening_indicator(cf, ds)
    indicators["dayevening"] = {"values":indicators["day"]["values"]+indicators["evening"]["values"]}
    indicators["dayevening"]["attr"] = indicators["day"]["attr"].copy()
    indicators["dayevening"]["attr"].update(indicators["evening"]["attr"])
    if opt["use_evening_filter"].lower()=="yes":
        idx = numpy.where(indicators["dayevening"]["values"]==0)[0]
        indicators["final"]["values"][idx] = numpy.int(0)
        indicators["final"]["attr"].update(indicators["dayevening"]["attr"])
    # save the indicator series
    ind_flag = numpy.zeros(len(ldt))
    long_name = "Turbulence indicator, 1 for turbulent, 0 for non-turbulent"
    ind_attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units="None")
    pfp_utils.CreateSeries(ds,"turbulence_indicator",indicators["turbulence"]["values"],ind_flag,ind_attr)
    iris["not_output"].append("turbulence_indicator")
    long_name = "Day indicator, 1 for day time, 0 for night time"
    ind_attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units="None")
    pfp_utils.CreateSeries(ds,"day_indicator",indicators["day"]["values"],ind_flag,ind_attr)
    iris["not_output"].append("day_indicator")
    long_name = "Evening indicator, 1 for evening, 0 for not evening"
    ind_attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units="None")
    pfp_utils.CreateSeries(ds,"evening_indicator",indicators["evening"]["values"],ind_flag,ind_attr)
    iris["not_output"].append("evening_indicator")
    long_name = "Day/evening indicator, 1 for day/evening, 0 for not day/evening"
    ind_attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units="None")
    pfp_utils.CreateSeries(ds,"dayevening_indicator",indicators["dayevening"]["values"],ind_flag,ind_attr)
    iris["not_output"].append("dayevening_indicator")
    long_name = "Final indicator, 1 for use data, 0 for don't use data"
    ind_attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,units="None")
    pfp_utils.CreateSeries(ds,"final_indicator",indicators["final"]["values"],ind_flag,ind_attr)
    iris["not_output"].append("final_indicator")
    # loop over the series to be filtered
    descr_level = "description_" + ds.globalattributes["nc_level"]
    for series in opt["filter_list"]:
        msg = " Applying "+opt["turbulence_filter"]+" filter to "+series
        logger.info(msg)
        # get the data
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,series)
        # continue to next series if this series has been filtered before
        if "turbulence_filter" in attr:
            msg = " Series " + series + " has already been filtered, skipping ..."
            logger.warning(msg)
            continue
        # save the non-filtered data
        attr_nofilter = copy.deepcopy(attr)
        pfp_utils.CreateSeries(ds, series + "_nofilter", data,flag, attr_nofilter)
        iris["not_output"].append(series + "_nofilter")
        # now apply the filter
        data_filtered = numpy.ma.masked_where(indicators["final"]["values"]==0,data,copy=True)
        flag_filtered = numpy.copy(flag)
        idx = numpy.where(indicators["final"]["values"]==0)[0]
        flag_filtered[idx] = numpy.int32(61)
        attr_filtered = copy.deepcopy(attr)
        # update the series attributes
        for item in indicators["final"]["attr"].keys():
            attr_filtered[item] = indicators["final"]["attr"][item]
        # update the "description" attribute
        attr_filtered[descr_level] = pfp_utils.append_string(attr_filtered[descr_level],
                                                             "turbulence filter applied")
        # and write the filtered data to the data structure
        pfp_utils.CreateSeries(ds,series,data_filtered,flag_filtered,attr_filtered)
        # and write a copy of the filtered datas to the data structure so it
        # will still exist once the gap filling has been done
        pfp_utils.CreateSeries(ds,series+"_filtered",data_filtered,flag_filtered,attr_filtered)
        iris["not_output"].append(series+"_filtered")
        nnf = numpy.ma.count(data)
        nf = numpy.ma.count(data_filtered)
        pc = int(100*(float(nnf-nf)/float(nnf))+0.5)
        msg = "  " + opt["turbulence_filter"] + " filter removed " + str(pc) + "% from " + series
        logger.info(msg)
    return

def ApplyTurbulenceFilter_checks(cf, ds):
    """
    Purpose:
    Usage:
    Author:
    Date:
    """
    opt = {"OK":True,"turbulence_filter":"ustar","filter_list":['Fc']}
    # return if there is no Options section in control file
    if "Options" not in cf:
        msg = " ApplyTurbulenceFilter: Options section not found in control file"
        logger.warning(msg)
        opt["OK"] = False
        return opt
    # get the value of the TurbulenceFilter key in the Options section
    opt["turbulence_filter"] = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "TurbulenceFilter", default="ustar")
    # return if turbulence filter disabled
    if opt["turbulence_filter"].lower() == "none":
        msg = " Turbulence filter disabled in control file at "+ds.globalattributes["nc_level"]
        logger.info(msg)
        opt["OK"] = False
        return opt
    # check to see if filter type can be handled
    if opt["turbulence_filter"].lower() not in ["ustar", "ustar_evg", "l"]:
        msg = " Unrecognised turbulence filter option ("
        msg = msg+opt["turbulence_filter"]+"), no filter applied"
        logger.error(msg)
        opt["OK"] = False
        return opt
    # get the list of series to be filtered
    if "FilterList" in cf["Options"]:
        filter_string = cf["Options"]["FilterList"]
        if "," in filter_string:
            opt["filter_list"] = filter_string.split(",")
        else:
            opt["filter_list"] = [filter_string]
    # check to see if the series are in the data structure
    for item in opt["filter_list"]:
        if item not in ds.series.keys():
            msg = " Series "+item+" given in FilterList not found in data stucture"
            logger.warning(msg)
            opt["filter_list"].remove(item)
    # return if the filter list is empty
    if len(opt["filter_list"])==0:
        msg = " FilterList in control file is empty, skipping turbulence filter"
        logger.warning(msg)
        opt["OK"] = False
        return opt
    # get the value of the DayNightFilter key in the Options section
    opt["daynight_filter"] = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "DayNightFilter", default="Fsd")
    # check to see if filter type can be handled
    if opt["daynight_filter"].lower() not in ["fsd", "sa", "none"]:
        msg = " Unrecognised day/night filter option ("
        msg = msg+opt["daynight_filter"]+"), no filter applied"
        logger.error(msg)
        opt["OK"] = False
        return opt
    # check to see if all day time values are to be accepted
    opt["accept_day_times"] = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "AcceptDayTimes", default="Yes")
    opt["use_evening_filter"] = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "UseEveningFilter", default="No")

    return opt

def cliptorange(data, lower, upper):
    data = rangecheckserieslower(data,lower)
    data = rangecheckseriesupper(data,upper)
    return data

def CreateNewSeries(cf,ds):
    '''Create a new series using the MergeSeries or AverageSeries instructions.'''
    logger.info(' Checking for new series to create')
    for ThisOne in cf['Variables'].keys():
        if 'MergeSeries' in cf['Variables'][ThisOne].keys():
            pfp_ts.MergeSeries(cf,ds,ThisOne)
        if 'AverageSeries' in cf['Variables'][ThisOne].keys():
            pfp_ts.AverageSeriesByElements(cf,ds,ThisOne)

def do_SONICcheck(cf, ds, code=3):
    """
    Purpose:
     Does an implicit dependency check using the sonic diagnostic.
    Usage:
    Side effects:
    Assumptions:
    History:
     Started life in OzFluxQC as do_CSATcheck()
    Author: PRI
    Date: Back in the day
    """
    # check to see if the user has disabled the SONIC check
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "SONIC_Check", default="Yes")
    if opt.lower() == "no":
        return
    # do the SONIC check
    series_list = list(ds.series.keys())
    if "Diag_SONIC" in series_list:
        pass
    elif "Diag_CSAT" in series_list:
        ds.series[unicode("Diag_SONIC")] = copy.deepcopy(ds.series["Diag_CSAT"])
    else:
        msg = " Sonic diagnostics not found in data, skipping sonic checks ..."
        logger.warning(msg)
        return
    logger.info(" Doing the sonic check")
    sonic_all = ["Ux", "Uy", "Uz",
                "Ws_CSAT", "Ws_CSAT_Av", "Ws_CSAT_Sd", "Ws_CSAT_Vr",
                "Wd_CSAT", "Wd_CSAT_Av", "Wd_CSAT_Compass", "Wd_CSAT_Sd", "Wd_CSAT_Vr",
                "Ws_SONIC", "Ws_SONIC_Av", "Ws_SONIC_Sd", "Ws_SONIC_Vr",
                "Wd_SONIC", "Wd_SONIC_Av", "Wd_SONIC_Compass", "Wd_SONIC_Sd", "Wd_SONIC_Vr",
                "Tv_CSAT", "Tv_CSAT_Av", "Tv_CSAT_Sd", "Tv_CSAT_Vr",
                "Tv_SONIC", "Tv_SONIC_Av", "Tv_SONIC_Sd", "Tv_SONIC_Vr",
                "UzT", "UxT", "UyT", "UzA", "UxA", "UyA", "UzC", "UxC", "UyC",
                "UxUz", "UyUz", "UxUy", "UxUx", "UyUy", "UzUz"]
    sonic_list = []
    for item in sonic_all:
        if item in series_list:
            sonic_list.append(item)
    index = numpy.where(ds.series['Diag_SONIC']['Flag'] != 0)
    msg = "  SONICCheck: Diag_SONIC rejected "+str(numpy.size(index))+" points"
    logger.info(msg)
    for label in sonic_list:
        if label in ds.series.keys():
            ds.series[label]["Data"][index] = numpy.float64(c.missing_value)
            ds.series[label]["Flag"][index] = numpy.int32(code)
        else:
            logger.error("  SONICcheck: series "+str(label)+" not found in data")
    return

def do_dependencycheck(cf, ds, section, series, code=23, mode="quiet"):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: Back in the day
    """
    if len(section) == 0 and len(series) == 0:
        return
    if len(section) == 0:
        section = pfp_utils.get_cfsection(cf, series=series, mode='quiet')
    if "DependencyCheck" not in cf[section][series].keys():
        return
    if "source" not in cf[section][series]["DependencyCheck"]:
        msg = " DependencyCheck: keyword 'source' not found for series " + series + ", skipping ..."
        logger.error(msg)
        return
    if mode == "verbose":
        msg = " Doing DependencyCheck for " + series
        logger.info(msg)
    # get the precursor source list from the control file
    source_string = cf[section][series]["DependencyCheck"]["source"]
    if "," in source_string:
        source_list = source_string.split(",")
    else:
        source_list = [source_string]
    # check to see if the "ignore_missing" flag is set
    opt = pfp_utils.get_keyvaluefromcf(cf, [section,series,"DependencyCheck"], "ignore_missing", default="no")
    ignore_missing = False
    if opt.lower() in ["yes", "y", "true", "t"]:
        ignore_missing = True
    # get the data
    dependent_data,dependent_flag,dependent_attr = pfp_utils.GetSeries(ds, series)
    # loop over the precursor source list
    for item in source_list:
        # check the precursor is in the data structure
        if item not in ds.series.keys():
            msg = " DependencyCheck: "+series+" precursor series "+item+" not found, skipping ..."
            logger.warning(msg)
            continue
        # get the precursor data
        precursor_data,precursor_flag,precursor_attr = pfp_utils.GetSeries(ds,item)
        # check if the user wants to ignore missing precursor data
        if ignore_missing:
            # they do, so make an array of missing values
            nRecs = int(ds.globalattributes["nc_nrecs"])
            missing_array = numpy.ones(nRecs)*float(c.missing_value)
            # and find the indicies of elements equal to the missing value
            bool_array = numpy.isclose(precursor_data, missing_array)
            idx = numpy.where(bool_array == True)[0]
            # and set these flags to 0 so missing data is ignored
            precursor_flag[idx] = numpy.int32(0)
        # mask the dependent data where the precursor flag shows data not OK
        dependent_data = numpy.ma.masked_where(numpy.mod(precursor_flag, 10)!=0, dependent_data)
        # get an index where the precursor flag shows data not OK
        idx = numpy.ma.where(numpy.mod(precursor_flag, 10)!=0)[0]
        # set the dependent QC flag
        dependent_flag[idx] = numpy.int32(code)
    # put the data back into the data structure
    dependent_attr["DependencyCheck_source"] = str(source_list)
    pfp_utils.CreateSeries(ds,series,dependent_data,dependent_flag,dependent_attr)
    # our work here is done
    return

def do_diurnalcheck(cf, ds, section, series,code=5):
    """
    Purpose:
     Do the diurnal QC check.
    Usage:
    Author: PRI
    Date: Back in the day
    """
    if 'DiurnalCheck' not in cf[section][series].keys():
        return
    if 'NumSd' not in cf[section][series]["DiurnalCheck"].keys():
        return
    dt = ds.series["DateTime"]["Data"]
    Hdh = numpy.array([d.hour+d.minute/float(60) for d in dt])
    ts = float(ds.globalattributes["time_step"])
    n = int((60./ts) + 0.5)             #Number of timesteps per hour
    nInts = int((1440.0/ts)+0.5)        #Number of timesteps per day
    Av = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    Sd = numpy.array([c.missing_value]*nInts,dtype=numpy.float64)
    NSd = numpy.array(parse_rangecheck_limit(cf[section][series]["DiurnalCheck"]["NumSd"]))
    for m in range(1,13):
        mindex = numpy.where(ds.series["Month"]["Data"]==m)[0]
        if len(mindex)!=0:
            lHdh = Hdh[mindex]
            l2ds = ds.series[series]["Data"][mindex]
            for i in range(nInts):
                li = numpy.where((abs(lHdh-(float(i)/float(n)))<c.eps)&(l2ds!=float(c.missing_value)))
                if numpy.size(li)!=0:
                    Av[i] = numpy.mean(l2ds[li])
                    Sd[i] = numpy.std(l2ds[li])
                else:
                    Av[i] = float(c.missing_value)
                    Sd[i] = float(c.missing_value)
            Lwr = Av - NSd[m-1]*Sd
            Upr = Av + NSd[m-1]*Sd
            hindex = numpy.array(n*lHdh,int)
            index = numpy.where(((l2ds!=float(c.missing_value))&(l2ds<Lwr[hindex]))|
                                ((l2ds!=float(c.missing_value))&(l2ds>Upr[hindex])))[0] + mindex[0]
            ds.series[series]['Data'][index] = numpy.float64(c.missing_value)
            ds.series[series]['Flag'][index] = numpy.int32(code)
            ds.series[series]['Attr']['diurnalcheck_numsd'] = cf[section][series]['DiurnalCheck']['NumSd']
    if 'DiurnalCheck' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+',DiurnalCheck'

def do_EC155check(cf,ds):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: September 2015
    """
    # check to see if we have a Diag_IRGA series to work with
    if "Diag_IRGA" not in ds.series.keys():
        msg = " Diag_IRGA not found in data, skipping IRGA checks ..."
        logger.warning(msg)
        return
    # seems OK to continue
    irga_type = str(ds.globalattributes["irga_type"])
    msg = " Doing the " + irga_type+" check"
    logger.info(msg)
    # list of series that depend on IRGA data quality
    EC155_list = ['H2O_IRGA_Av','CO2_IRGA_Av','H2O_IRGA_Sd','CO2_IRGA_Sd','H2O_IRGA_Vr','CO2_IRGA_Vr',
                 'UzA','UxA','UyA','UzH','UxH','UyH','UzC','UxC','UyC']
    idx = numpy.where(ds.series['Diag_IRGA']['Flag'] !=0 )
    msg = "  "+irga_type+"Check: Diag_IRGA rejects " + str(numpy.size(idx))
    logger.info(msg)
    used_Signal = False
    used_H2O = False
    used_CO2 = False
    EC155_dependents = []
    for item in ['Signal_H2O','Signal_CO2','H2O_IRGA_Sd','CO2_IRGA_Sd']:
        if item in ds.series.keys():
            if ("Signal_H2O" in item) or ("Signal_CO2" in item):
                used_Signal = True
            if ("H2O" in item) or ("Ah" in item):
                used_H2O = True
            if ("CO2" in item) or ("Cc" in item):
                used_CO2 = True
            EC155_dependents.append(item)
    if not used_Signal:
        msg = " Signal_H2O or Signal_CO2 value not used in QC (not in data)"
        logger.warning(msg)
    if not used_H2O:
        msg = " H2O stdev or var not used in QC (not in data)"
        logger.warning(msg)
    if not used_CO2:
        msg = " CO2 stdev or var not used in QC (not in data)"
        logger.warning(msg)
    flag = numpy.copy(ds.series['Diag_IRGA']['Flag'])
    for item in EC155_dependents:
        idx = numpy.where(ds.series[item]['Flag'] != 0)[0]
        msg = "  " + irga_type+"Check: "+item+" rejected "+str(numpy.size(idx))+" points"
        logger.info(msg)
        flag[idx] = numpy.int32(1)
    idx = numpy.where(flag !=0 )[0]
    msg = "  "+irga_type+"Check: Total rejected " + str(numpy.size(idx))
    logger.info(msg)
    for ThisOne in EC155_list:
        if ThisOne in ds.series.keys():
            ds.series[ThisOne]['Data'][idx] = numpy.float64(c.missing_value)
            ds.series[ThisOne]['Flag'][idx] = numpy.int32(4)
        #else:
            #logger.warning(' do_EC155check: series '+str(ThisOne)+' in EC155 list not found in data structure')

def do_EPQCFlagCheck(cf, ds, section, series, code=9):
    """
    Purpose:
     Mask data according to the value of an EddyPro QC flag.
    Usage:
    Author: PRI
    Date: August 2017
    """
    # return if "EPQCFlagCheck" not used for this variable
    if "EPQCFlagCheck" not in cf[section][series].keys():
        return
    # check the "source" key exists and is a string
    if "source" not in cf[section][series]["EPQCFlagCheck"]:
        msg = "  EPQCFlagCheck: 'source' key not found for (" + series + ")"
        logger.error(msg)
        return
    if not isinstance(cf[section][series]["EPQCFlagCheck"]["source"], basestring):
        msg = "  EPQCFlagCheck: 'source' value must be a string (" + series + ")"
        logger.error(msg)
        return
    # comma separated string to list
    source_list = cf[section][series]["EPQCFlagCheck"]["source"].split(",")
    # check the "reject" key exists and is a string
    if "reject" not in cf[section][series]["EPQCFlagCheck"]:
        msg = "  EPQCFlagCheck: 'reject' key not found for (" + series + ")"
        logger.error(msg)
        return
    if not isinstance(cf[section][series]["EPQCFlagCheck"]["reject"], basestring):
        msg = "  EPQCFlagCheck: 'reject' value must be a string (" + series + ")"
        logger.error(msg)
        return
    # comma separated string to list
    reject_list = cf[section][series]["EPQCFlagCheck"]["reject"].split(",")
    nRecs = int(ds.globalattributes["nc_nrecs"])
    flag = numpy.zeros(nRecs, dtype=numpy.int32)
    variable = pfp_utils.GetVariable(ds, series)
    for source in source_list:
        epflag = pfp_utils.GetVariable(ds, source)
        for value in reject_list:
            bool_array = numpy.isclose(epflag["Data"], float(value))
            idx = numpy.where(bool_array == True)[0]
            flag[idx] = numpy.int32(1)
    idx = numpy.where(flag == 1)[0]
    variable["Data"][idx] = numpy.float(c.missing_value)
    variable["Flag"][idx] = numpy.int32(9)
    pfp_utils.CreateVariable(ds, variable)
    return

def do_excludedates(cf,ds,section,series,code=6):
    if 'ExcludeDates' not in cf[section][series].keys():
        return
    ldt = ds.series['DateTime']['Data']
    ExcludeList = cf[section][series]['ExcludeDates'].keys()
    NumExclude = len(ExcludeList)
    for i in range(NumExclude):
        exclude_dates_string = cf[section][series]['ExcludeDates'][str(i)]
        exclude_dates_list = exclude_dates_string.split(",")
        if len(exclude_dates_list) == 1:
            try:
                dt = datetime.datetime.strptime(exclude_dates_list[0].strip(),'%Y-%m-%d %H:%M')
                si = pfp_utils.find_nearest_value(ldt, dt)
                ei = si + 1
            except ValueError:
                si = 0
                ei = -1
        elif len(exclude_dates_list) == 2:
            try:
                dt = datetime.datetime.strptime(exclude_dates_list[0].strip(),'%Y-%m-%d %H:%M')
                si = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                si = 0
            try:
                dt = datetime.datetime.strptime(exclude_dates_list[1].strip(),'%Y-%m-%d %H:%M')
                ei = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                ei = -1
            if si == ei:
                ei = si + 1
        else:
            msg = "ExcludeDates: bad date string ("+exclude_dates_string+"), skipping ..."
            logger.warning(msg)
            return
        ds.series[series]['Data'][si:ei] = numpy.float64(c.missing_value)
        ds.series[series]['Flag'][si:ei] = numpy.int32(code)
        ds.series[series]['Attr']['ExcludeDates_'+str(i)] = cf[section][series]['ExcludeDates'][str(i)]
    return

def do_excludehours(cf,ds,section,series,code=7):
    if 'ExcludeHours' not in cf[section][series].keys(): return
    ldt = ds.series['DateTime']['Data']
    ExcludeList = cf[section][series]['ExcludeHours'].keys()
    NumExclude = len(ExcludeList)
    for i in range(NumExclude):
        exclude_hours_string = cf[section][series]['ExcludeHours'][str(i)]
        ExcludeHourList = exclude_hours_string.split(",")
        try:
            dt = datetime.datetime.strptime(ExcludeHourList[0],'%Y-%m-%d %H:%M')
            si = pfp_utils.find_nearest_value(ldt, dt)
        except ValueError:
            si = 0
        try:
            dt = datetime.datetime.strptime(ExcludeHourList[1],'%Y-%m-%d %H:%M')
            ei = pfp_utils.find_nearest_value(ldt, dt)
        except ValueError:
            ei = -1
        for j in range(2,len(ExcludeHourList)):
            ExHr = datetime.datetime.strptime(ExcludeHourList[j],'%H:%M').hour
            ExMn = datetime.datetime.strptime(ExcludeHourList[j],'%H:%M').minute
            index = numpy.where((ds.series['Hour']['Data'][si:ei]==ExHr)&
                                (ds.series['Minute']['Data'][si:ei]==ExMn))[0] + si
            ds.series[series]['Data'][index] = numpy.float64(c.missing_value)
            ds.series[series]['Flag'][index] = numpy.int32(code)
            ds.series[series]['Attr']['ExcludeHours_'+str(i)] = cf[section][series]['ExcludeHours'][str(i)]
    if 'ExcludeHours' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+',ExcludeHours'

def do_IRGAcheck(cf,ds):
    """
    Purpose:
     Decide which IRGA check routine to use depending on the setting
     of the "irga_type" key in the [Options] section of the control
     file.  The default is Li7500.
    Usage:
    Author: PRI
    Date: September 2015
    """
    # check to see if the user has disabled the IRGA check
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "IRGA_Check", default="Yes")
    if opt.lower() == "no":
        return
    # get the IRGA type from the control file
    irga_type = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "irga_type", default="not found")
    if irga_type == "not found":
        msg = " IRGA type not specified in Options section, using default (Li-7500)"
        logger.warning(msg)
        irga_type = "Li-7500"
    # do the IRGA checks
    if irga_type in ["Li-7500", "Li-7500A", "Li-7500A (<V6.5)"]:
        ds.globalattributes["irga_type"] = irga_type
        do_li7500check(cf, ds)
    elif irga_type in ["Li-7500A (>=V6.5)", "Li-7500RS"]:
        ds.globalattributes["irga_type"] = irga_type
        do_li7500acheck(cf, ds)
    elif irga_type in ["EC150", "EC155", "IRGASON"]:
        ds.globalattributes["irga_type"] = irga_type
        do_EC155check(cf, ds)
    else:
        msg = " Unsupported IRGA type " + irga_type + ", contact the devloper ..."
        logger.error(msg)
        return
    return

def do_li7500check(cf, ds, code=4):
    '''Rejects data values for series specified in LI75List for times when the Diag_7500
       flag is non-zero.  If the Diag_7500 flag is not present in the data structure passed
       to this routine, it is constructed from the QC flags of the series specified in
       LI75Lisat.  Additional checks are done for AGC_7500 (the LI-7500 AGC value),
       Ah_7500_Sd (standard deviation of absolute humidity) and Cc_7500_Sd (standard
       deviation of CO2 concentration).'''
    series_list = list(ds.series.keys())
    # check we have an IRGA diagnostics series to use
    if "Diag_IRGA" in series_list:
        pass
    elif "Diag_7500" in series_list:
        # backward compatibility with early OFQC
        ds.series[unicode("Diag_IRGA")] = copy.deepcopy(ds.series["Diag_7500"])
    else:
        msg = " IRGA diagnostics not found in data, skipping IRGA checks ..."
        logger.warning(msg)
        return
    logger.info(" Doing the LI-7500 check")
    # let's check the contents of ds and see what we have to work with
    # first, list everything we may have once used for some kind of LI-7500 output
    # we do this for backwards compatibility
    irga_list_all = ["Ah_7500_Av", "Ah_7500_Sd", "Ah_IRGA_Av", "Ah_IRGA_Sd",
                     "Cc_7500_Av", "Cc_7500_Sd", "Cc_7500_Av", "Cc_7500_Sd",
                     "H2O_IRGA_Av", "H2O_IRGA_Vr","CO2_IRGA_Av", "CO2_IRGA_Vr",
                     "UzA", "UxA", "UyA", "UzC", "UxC", "UyC"]
    # now get a list of what is actually there
    irga_list = []
    for label in series_list:
        if label in irga_list_all:
            irga_list.append(label)
    # now tell the user how many points the IRGA diagnostic will remove
    idx = numpy.where(ds.series["Diag_IRGA"]["Flag"] != 0)
    msg = "  Diag_IRGA rejected "+str(numpy.size(idx))+" points"
    logger.info(msg)
    # and then we start with the dependents
    # and again we list everything we may have used in the past for backwards compatibility
    irga_dependents_all = ["AGC_7500", "AGC_IRGA",
                           "Ah_7500_Sd","Cc_7500_Sd",
                           "Ah_IRGA_Sd", "Cc_IRGA_Sd",
                           "H2O_IRGA_Sd", "CO2_IRGA_Sd",
                           "AhAh","CcCc",
                           "Ah_IRGA_Vr", "Cc_IRGA_Vr",
                           "H2O_IRGA_Vr", "CO2_IRGA_Vr"]
    # and then check to see what we actually have to work with
    irga_dependents = []
    for label in irga_dependents_all:
        if label in series_list:
            irga_dependents.append(label)
    # and then remove variances where variances and standard deviations are duplicated
    std_list = ["Ah_7500_Sd", "Cc_7500_Sd", "Ah_IRGA_Sd", "Cc_IRGA_Sd", "H2O_IRGA_Sd", "CO2_IRGA_Sd"]
    var_list = ["AhAh",       "CcCc",       "AhAh",       "CcCc",       "H2O_IRGA_Vr", "CO2_IRGA_Vr"]
    irga_dependents_nodups = copy.deepcopy(irga_dependents)
    for std, var in zip(std_list, var_list):
        if (std in irga_dependents) and (var in irga_dependents):
            irga_dependents_nodups.remove(var)
    # now we can do the business
    used_AGC = False
    used_H2O = False
    used_CO2 = False
    flag = numpy.copy(ds.series["Diag_IRGA"]["Flag"])
    for label in irga_dependents_nodups:
        if "AGC" in label:
            used_AGC = True
        if ("H2O" in label) or ("Ah" in label):
            used_H2O = True
        if ("CO2" in label) or ("Cc" in label):
            used_CO2 = True
        idx = numpy.where(ds.series[label]["Flag"] != 0)
        logger.info("  IRGACheck: "+label+" rejected "+str(numpy.size(idx))+" points")
        flag[idx] = numpy.int32(1)
    if not used_AGC:
        msg = " AGC value not used in QC (not in data)"
        logger.warning(msg)
    if not used_H2O:
        msg = " H2O stdev or var not used in QC (not in data)"
        logger.warning(msg)
    if not used_CO2:
        msg = " CO2 stdev or var not used in QC (not in data)"
        logger.warning(msg)
    idx = numpy.where(flag != 0)[0]
    msg = "  IRGACheck: Total rejected is " + str(numpy.size(idx))
    percent = float(100)*numpy.size(idx)/numpy.size(flag)
    msg = msg + " (" + str(int(percent+0.5)) + "%)"
    logger.info(msg)
    for label in irga_list:
        ds.series[label]['Data'][idx] = numpy.float64(c.missing_value)
        ds.series[label]['Flag'][idx] = numpy.int32(code)

def do_li7500acheck(cf,ds):
    '''Rejects data values for series specified in LI75List for times when the Diag_7500
       flag is non-zero.  If the Diag_IRGA flag is not present in the data structure passed
       to this routine, it is constructed from the QC flags of the series specified in
       LI75Lisat.  Additional checks are done for AGC_7500 (the LI-7500 AGC value),
       Ah_7500_Sd (standard deviation of absolute humidity) and Cc_7500_Sd (standard
       deviation of CO2 concentration).'''
    if "Diag_IRGA" not in ds.series.keys():
        msg = " Diag_IRGA not found in data, skipping IRGA checks ..."
        logger.warning(msg)
        return
    logger.info(' Doing the 7500A check')
    LI75List = ['H2O_IRGA_Av','CO2_IRGA_Av','H2O_IRGA_Sd','CO2_IRGA_Sd','H2O_IRGA_Vr','CO2_IRGA_Vr',
                'UzA','UxA','UyA','UzC','UxC','UyC']
    idx = numpy.where(ds.series['Diag_IRGA']['Flag']!=0)[0]
    logger.info('  7500ACheck: Diag_IRGA ' + str(numpy.size(idx)))
    # initialise logicals to track which QC data used
    used_Signal = False
    used_H2O = False
    used_CO2 = False
    LI75_dependents = []
    for item in ['Signal_H2O','Signal_CO2','H2O_IRGA_Sd','CO2_IRGA_Sd','H2O_IRGA_Vr','CO2_IRGA_Vr']:
        if item in ds.series.keys():
            if ("Signal_H2O" in item) or ("Signal_CO2" in item):
                used_Signal = True
            if ("H2O" in item) or ("Ah" in item):
                used_H2O = True
            if ("CO2" in item) or ("Cc" in item):
                used_CO2 = True
            LI75_dependents.append(item)
    if "H2O_IRGA_Sd" and "H2O_IRGA_Vr" in LI75_dependents:
        LI75_dependents.remove("H2O_IRGA_Vr")
    if "CO2_IRGA_Sd" and "CO2_IRGA_Vr" in LI75_dependents:
        LI75_dependents.remove("CO2_IRGA_Vr")
    if not used_Signal:
        msg = " Signal_H2O or Signal_CO2 value not used in QC (not in data)"
        logger.warning(msg)
    if not used_H2O:
        msg = " H2O stdev or var not used in QC (not in data)"
        logger.warning(msg)
    if not used_CO2:
        msg = " CO2 stdev or var not used in QC (not in data)"
        logger.warning(msg)
    flag = numpy.copy(ds.series['Diag_IRGA']['Flag'])
    for item in LI75_dependents:
        if item in ds.series.keys():
            idx = numpy.where(ds.series[item]['Flag']!=0)
            logger.info('  7500ACheck: '+item+' rejected '+str(numpy.size(idx))+' points')
            flag[idx] = numpy.int32(1)
    idx = numpy.where(flag != 0)[0]
    logger.info('  7500ACheck: Total ' + str(numpy.size(idx)))
    for ThisOne in LI75List:
        if ThisOne in ds.series.keys():
            ds.series[ThisOne]['Data'][idx] = numpy.float64(c.missing_value)
            ds.series[ThisOne]['Flag'][idx] = numpy.int32(4)
        else:
            #logger.warning('  pfp_ck.do_7500acheck: series '+str(ThisOne)+' in LI75List not found in ds.series')
            pass
    if '7500ACheck' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+',7500ACheck'

def do_linear(cf,ds):
    level = ds.globalattributes['nc_level']
    for ThisOne in cf['Variables'].keys():
        if pfp_utils.haskey(cf,ThisOne,'Linear'):
            pfp_ts.ApplyLinear(cf,ds,ThisOne)
        if pfp_utils.haskey(cf,ThisOne,'Drift'):
            pfp_ts.ApplyLinearDrift(cf,ds,ThisOne)
        if pfp_utils.haskey(cf,ThisOne,'LocalDrift'):
            pfp_ts.ApplyLinearDriftLocal(cf,ds,ThisOne)
    if 'do_linear' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+',do_linear'

def parse_rangecheck_limit(s):
    """
    Purpose:
     Parse the RangeCheck Upper or Lower value string.
     Valid string formats are;
      '100'
      '[100]*12'
      '[1,2,3,4,5,6,7,8,9,10,11,12]'
      '1,2,3,4,5,6,7,8,9,10,11,12'
    Author: PRI
    Date: August 2018
    """
    val_list = []
    try:
        val_list = [float(s)]*12
    except ValueError as e:
        if ("[" in s) and ("]" in s) and ("*" in s):
            val = s[s.index("[")+1:s.index("]")]
            val_list = [float(val)]*12
        elif ("[" in s) and ("]" in s) and ("," in s) and ("*" not in s):
            s = s.replace("[","").replace("]","")
            val_list = [float(n) for n in s.split(",")]
        elif ("[" not in s) and ("]" not in s) and ("," in s) and ("*" not in s):
            val_list = [float(n) for n in s.split(",")]
        else:
            msg = " Unrecognised format for RangeCheck limit ("+s+")"
            logger.error(msg)
    return val_list

def do_rangecheck(cf, ds, section, series, code=2):
    """
    Purpose:
     Applies a range check to data series listed in the control file.  Data values that
     are less than the lower limit or greater than the upper limit are replaced with
     c.missing_value and the corresponding QC flag element is set to 2.
    Usage:
    Author: PRI
    Date: Back in the day
    """
    # check that RangeCheck has been requested for this series
    if 'RangeCheck' not in cf[section][series].keys():
        return
    # check that the upper and lower limits have been given
    if ("Lower" not in cf[section][series]["RangeCheck"].keys() or
        "Upper" not in cf[section][series]["RangeCheck"].keys()):
        msg = "RangeCheck: key not found in control file for "+series+", skipping ..."
        logger.warning(msg)
        return
    # get the upper and lower limits
    upper = cf[section][series]['RangeCheck']['Upper']
    upr = numpy.array(parse_rangecheck_limit(upper))
    if len(upr) != 12:
        msg = " Need 12 'Upper' values, got "+str(len(upr))+" for "+series
        logger.error(msg)
        return
    valid_upper = numpy.min(upr)
    upr = upr[ds.series['Month']['Data']-1]
    lower = cf[section][series]['RangeCheck']['Lower']
    lwr = numpy.array(parse_rangecheck_limit(lower))
    if len(lwr) != 12:
        msg = " Need 12 'Lower' values, got "+str(len(lwr))+" for "+series
        logger.error(msg)
        return
    valid_lower = numpy.min(lwr)
    lwr = lwr[ds.series['Month']['Data']-1]
    # get the data, flag and attributes
    data, flag, attr = pfp_utils.GetSeriesasMA(ds, series)
    # convert the data from a masked array to an ndarray so the range check works
    data = numpy.ma.filled(data, fill_value=c.missing_value)
    # get the indices of elements outside this range
    idx = numpy.where((data<lwr)|(data>upr))[0]
    # set elements outside range to missing and set the QC flag
    data[idx] = numpy.float64(c.missing_value)
    flag[idx] = numpy.int32(code)
    # update the variable attributes
    attr["rangecheck_lower"] = cf[section][series]["RangeCheck"]["Lower"]
    attr["rangecheck_upper"] = cf[section][series]["RangeCheck"]["Upper"]
    attr["valid_range"] = str(valid_lower)+","+str(valid_upper)
    # and now put the data back into the data structure
    pfp_utils.CreateSeries(ds, series, data, Flag=flag, Attr=attr)
    # now we can return
    return

def do_qcchecks(cf,ds,mode="verbose"):
    if "nc_level" in ds.globalattributes:
        level = str(ds.globalattributes["nc_level"])
        if mode!="quiet": logger.info(" Doing the QC checks at level "+str(level))
    else:
        if mode!="quiet": logger.info(" Doing the QC checks")
    # get the series list from the control file
    series_list = []
    for item in ["Variables","Drivers","Fluxes"]:
        if item in cf:
            section = item
            series_list = cf[item].keys()
    if len(series_list)==0:
        msg = " do_qcchecks: Variables, Drivers or Fluxes section not found in control file, skipping QC checks ..."
        logger.warning(msg)
        return
    # loop over the series specified in the control file
    # first time for general QC checks
    for series in series_list:
        # check the series is in the data structure
        if series not in ds.series.keys():
            if mode!="quiet":
                msg = " do_qcchecks: series "+series+" not found in data structure, skipping ..."
                logger.warning(msg)
            continue
        # if so, do the QC checks
        do_qcchecks_oneseries(cf,ds,section,series)
    # loop over the series in the control file
    # second time for dependencies
    for series in series_list:
        # check the series is in the data structure
        if series not in ds.series.keys():
            if mode!="quiet":
                msg = " do_qcchecks: series "+series+" not found in data structure, skipping ..."
                logger.warning(msg)
            continue
        # if so, do dependency check
        do_dependencycheck(cf,ds,section,series,code=23,mode="quiet")

def do_qcchecks_oneseries(cf,ds,section,series):
    if len(section)==0:
        section = pfp_utils.get_cfsection(cf,series=series,mode='quiet')
        if len(section)==0: return
    # do the range check
    do_rangecheck(cf,ds,section,series,code=2)
    # do the lower range check
    do_lowercheck(cf,ds,section,series,code=2)
    # do the upper range check
    do_uppercheck(cf,ds,section,series,code=2)
    # do the diurnal check
    do_diurnalcheck(cf,ds,section,series,code=5)
    # do the EP QC flag check
    do_EPQCFlagCheck(cf,ds,section,series,code=9)
    # do exclude dates
    do_excludedates(cf,ds,section,series,code=6)
    # do exclude hours
    do_excludehours(cf,ds,section,series,code=7)
    # do wind direction corrections
    do_winddirectioncorrection(cf,ds,section,series)
    if 'do_qcchecks' not in ds.globalattributes['Functions']:
        ds.globalattributes['Functions'] = ds.globalattributes['Functions']+',do_qcchecks'

def do_winddirectioncorrection(cf, ds, section, series):
    if "CorrectWindDirection" not in cf[section][series].keys():
        return
    pfp_ts.CorrectWindDirection(cf, ds, series)

def rangecheckserieslower(data,lower):
    if lower is None:
        logger.info(' rangecheckserieslower: no lower bound set')
        return data
    if numpy.ma.isMA(data):
        data = numpy.ma.masked_where(data<lower,data)
    else:
        index = numpy.where((abs(data-numpy.float64(c.missing_value))>c.eps)&(data<lower))[0]
        data[index] = numpy.float64(c.missing_value)
    return data

def rangecheckseriesupper(data,upper):
    if upper is None:
        logger.info(' rangecheckserieslower: no upper bound set')
        return data
    if numpy.ma.isMA(data):
        data = numpy.ma.masked_where(data>upper,data)
    else:
        index = numpy.where((abs(data-numpy.float64(c.missing_value))>c.eps)&(data>upper))[0]
        data[index] = numpy.float64(c.missing_value)
    return data

def do_lowercheck(cf,ds,section,series,code=2):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: February 2017
    """
    # check to see if LowerCheck requested for this variable
    if "LowerCheck" not in cf[section][series]:
        return
    # Check to see if limits have been specified
    if len(cf[section][series]["LowerCheck"].keys()) == 0:
        msg = "do_lowercheck: no date ranges specified"
        logger.info(msg)
        return

    ldt = ds.series["DateTime"]["Data"]
    ts = ds.globalattributes["time_step"]
    data, flag, attr = pfp_utils.GetSeriesasMA(ds, series)

    lc_list = list(cf[section][series]["LowerCheck"].keys())
    for n,item in enumerate(lc_list):
        # this should be a list and we should probably check for compliance
        lwr_string = cf[section][series]["LowerCheck"][item]
        attr["lowercheck_"+str(n)] = lwr_string
        lwr_list = lwr_string.split(",")
        start_date = dateutil.parser.parse(lwr_list[0])
        su = float(lwr_list[1])
        end_date = dateutil.parser.parse(lwr_list[2])
        eu = float(lwr_list[3])
        # get the start and end indices
        si = pfp_utils.GetDateIndex(ldt, start_date, ts=ts, default=0, match="exact")
        ei = pfp_utils.GetDateIndex(ldt, end_date, ts=ts, default=len(ldt)-1, match="exact")
        # get the segment of data between this start and end date
        seg_data = data[si:ei+1]
        seg_flag = flag[si:ei+1]
        x = numpy.arange(si, ei+1, 1)
        lower = numpy.interp(x, [si,ei], [su,eu])
        index = numpy.ma.where((seg_data<lower))[0]
        seg_data[index] = numpy.ma.masked
        seg_flag[index] = numpy.int32(code)
        data[si:ei+1] = seg_data
        flag[si:ei+1] = seg_flag
    # now put the data back into the data structure
    pfp_utils.CreateSeries(ds, series, data, Flag=flag, Attr=attr)
    return

def do_uppercheck(cf,ds,section,series,code=2):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: February 2017
    """
    # check to see if UpperCheck requested for this variable
    if "UpperCheck" not in cf[section][series]:
        return
    # Check to see if limits have been specified
    if len(cf[section][series]["UpperCheck"].keys()) == 0:
        msg = "do_uppercheck: no date ranges specified"
        logger.info(msg)
        return

    ldt = ds.series["DateTime"]["Data"]
    ts = ds.globalattributes["time_step"]
    data, flag, attr = pfp_utils.GetSeriesasMA(ds, series)

    lc_list = list(cf[section][series]["UpperCheck"].keys())
    for n,item in enumerate(lc_list):
        # this should be a list and we should probably check for compliance
        upr_info = cf[section][series]["UpperCheck"][item]
        attr["uppercheck_"+str(n)] = str(upr_info)
        start_date = dateutil.parser.parse(upr_info[0])
        su = float(upr_info[1])
        end_date = dateutil.parser.parse(upr_info[2])
        eu = float(upr_info[3])
        # get the start and end indices
        si = pfp_utils.GetDateIndex(ldt, start_date, ts=ts, default=0, match="exact")
        ei = pfp_utils.GetDateIndex(ldt, end_date, ts=ts, default=len(ldt)-1, match="exact")
        seg_data = data[si:ei+1]
        seg_flag = flag[si:ei+1]
        x = numpy.arange(si, ei+1, 1)
        upper = numpy.interp(x, [si,ei], [su,eu])
        index = numpy.ma.where((seg_data>upper))[0]
        seg_data[index] = numpy.ma.masked
        seg_flag[index] = numpy.int32(code)
        data[si:ei+1] = seg_data
        flag[si:ei+1] = seg_flag
    # now put the data back into the data structure
    pfp_utils.CreateSeries(ds, series, data, Flag=flag, Attr=attr)
    return

def UpdateVariableAttributes_QC(cf, variable):
    """
    Purpose:
    Usage:
    Side effects:
    Author: PRI
    Date: November 2016
    """
    label = variable["Label"]
    section = pfp_utils.get_cfsection(cf,series=label,mode='quiet')
    if label not in cf[section]:
        return
    if "RangeCheck" not in cf[section][label]:
        return
    if "Lower" in cf[section][label]["RangeCheck"]:
        variable["Attr"]["rangecheck_lower"] = cf[section][label]["RangeCheck"]["Lower"]
    if "Upper" in cf[section][label]["RangeCheck"]:
        variable["Attr"]["rangecheck_upper"] = cf[section][label]["RangeCheck"]["Upper"]
    return
