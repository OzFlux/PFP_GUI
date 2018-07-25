# standard modules
import datetime
import logging
# 3rd party
import dateutil
import numpy
# PFP modules
import meteorologicalfunctions as mf
import pfp_utils

logger = logging.getLogger("pfp_log")

def AhfromRH(ds,Ah_out,RH_in,Ta_in):
    """
    Purpose:
     Function to calculate absolute humidity given relative humidity and
     air temperature.  Absolute humidity is not calculated if any of the
     input series are missing or if the specified output series already
     exists in the data structure.
     The calculated absolute humidity is created as a new series in the
     data structure.
    Usage:
     pfp_func.AhfromRH(ds,"Ah_HMP_2m","RH_HMP_2m","Ta_HMP_2m")
    Author: PRI
    Date: September 2015
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    for item in [RH_in,Ta_in]:
        if item not in ds.series.keys():
            msg = " AhfromRH: Requested series "+item+" not found, "+Ah_out+" not calculated"
            logger.error(msg)
            return 0
    if Ah_out in ds.series.keys():
        msg = " AhfromRH: Output series "+Ah_out+" already exists, skipping ..."
        logger.error(msg)
        return 0
    RH_data,RH_flag,RH_attr = pfp_utils.GetSeriesasMA(ds,RH_in)
    Ta_data,Ta_flag,Ta_attr = pfp_utils.GetSeriesasMA(ds,Ta_in)
    Ah_data = mf.absolutehumidityfromRH(Ta_data,RH_data)
    Ah_attr = pfp_utils.MakeAttributeDictionary(long_name="Absolute humidity calculated from "+RH_in+" and "+Ta_in,
                                              height=RH_attr["height"],
                                              units="g/m3")
    flag = numpy.where(numpy.ma.getmaskarray(Ah_data)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,Ah_out,Ah_data,flag,Ah_attr)
    return 1

def AhfromMR(ds,Ah_out,MR_in,Ta_in,ps_in):
    """
    Purpose:
     Function to calculate absolute humidity given the water vapour mixing
     ratio, air temperature and pressure.  Absolute humidity is not calculated
     if any of the input series are missing or if the specified output series
     already exists in the data structure.
     The calculated absolute humidity is created as a new series in the
     data structure.
    Usage:
     pfp_func.AhfromMR(ds,"Ah_IRGA_Av","H2O_IRGA_Av","Ta_HMP_2m","ps")
    Author: PRI
    Date: September 2015
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    for item in [MR_in,Ta_in,ps_in]:
        if item not in ds.series.keys():
            msg = " AhfromMR: Requested series "+item+" not found, "+Ah_out+" not calculated"
            logger.error(msg)
            return 0
    if Ah_out in ds.series.keys():
        msg = " AhfromMR: Output series "+Ah_out+" already exists, skipping ..."
        logger.error(msg)
        return 0
    MR_data,MR_flag,MR_attr = pfp_utils.GetSeriesasMA(ds,MR_in)
    Ta_data,Ta_flag,Ta_attr = pfp_utils.GetSeriesasMA(ds,Ta_in)
    ps_data,ps_flag,ps_attr = pfp_utils.GetSeriesasMA(ds,ps_in)
    Ah_data = mf.h2o_gpm3frommmolpmol(MR_data,Ta_data,ps_data)
    long_name = "Absolute humidity calculated from "+MR_in+", "+Ta_in+" and "+ps_in
    Ah_attr = pfp_utils.MakeAttributeDictionary(long_name=long_name,
                                              height=MR_attr["height"],
                                              units="g/m3")
    flag = numpy.where(numpy.ma.getmaskarray(Ah_data)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,Ah_out,Ah_data,flag,Ah_attr)
    return 1

def ConvertK2C(ds, T_in, T_out):
    """
    Purpose:
     Function to convert temperature from K to C.
    Usage:
     pfp_func.ConvertK2C(ds, T_in, T_out)
    Author: PRI
    Date: February 2018
    """
    var_in = pfp_utils.GetVariable(ds, T_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "C", mode="quiet")
    var_out["Label"] = T_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def ConvertPa2kPa(ds, ps_in, ps_out):
    """
    Purpose:
     Function to convert pressure from Pa to kPa.
    Usage:
     pfp_func.ConvertPa2kPa(ds, ps_in, ps_out)
    Author: PRI
    Date: February 2018
    """
    var_in = pfp_utils.GetVariable(ds, ps_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "kPa", mode="quiet")
    var_out["Label"] = ps_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def DateTimeFromDoY(ds,Year_in,DoY_in,Hdh_in):
    year,f,a = pfp_utils.GetSeriesasMA(ds,Year_in)
    doy,f,a = pfp_utils.GetSeriesasMA(ds,DoY_in)
    hdh,f,a = pfp_utils.GetSeriesasMA(ds,Hdh_in)
    idx = numpy.ma.where((numpy.ma.getmaskarray(year)==False)&
                         (numpy.ma.getmaskarray(doy)==False)&
                         (numpy.ma.getmaskarray(hdh)==False))[0]
    year = year[idx]
    doy = doy[idx]
    hdh = hdh[idx]
    hour = numpy.array(hdh,dtype=numpy.integer)
    minute = numpy.array((hdh-hour)*60,dtype=numpy.integer)
    dt = [datetime.datetime(int(y),1,1,h,m)+datetime.timedelta(int(d)-1) for y,d,h,m in zip(year,doy,hour,minute)]
    nRecs = len(dt)
    ds.series["DateTime"] = {}
    ds.series["DateTime"]["Data"] = dt
    ds.series["DateTime"]["Flag"] = numpy.zeros(len(dt),dtype=numpy.int32)
    ds.series["DateTime"]["Attr"] = {}
    ds.series["DateTime"]["Attr"]["long_name"] = "Datetime in local timezone"
    ds.series["DateTime"]["Attr"]["units"] = "None"
    # now remove any "data"" from empty lines
    series_list = ds.series.keys()
    if "DateTime" in series_list: series_list.remove("DateTime")
    for item in series_list:
        ds.series[item]["Data"] = ds.series[item]["Data"][idx]
        ds.series[item]["Flag"] = ds.series[item]["Flag"][idx]
    ds.globalattributes["nc_nrecs"] = nRecs
    return 1

def DateTimeFromTimeStamp(ds,TimeStamp_in,fmt=""):
    if TimeStamp_in not in ds.series.keys():
        logger.error(" Required series "+TimeStamp_in+" not found")
        return 0
    TimeStamp = ds.series[TimeStamp_in]["Data"]
    # guard against empty fields in what we assume is the datetime
    idx = [i for i in range(len(TimeStamp)) if len(str(TimeStamp[i]))>0]
    if len(fmt)==0:
        dt = [dateutil.parser.parse(str(TimeStamp[i])) for i in idx]
    else:
        yearfirst = False
        dayfirst = False
        if fmt.index("Y") < fmt.index("D"): yearfirst = True
        if fmt.index("D") < fmt.index("M"): dayfirst = True
        dt = [dateutil.parser.parse(str(TimeStamp[i]),dayfirst=dayfirst,yearfirst=yearfirst)
              for i in idx]
    # we have finished with the timestamp so delete it from the data structure
    del ds.series[TimeStamp_in]
    nRecs = len(dt)
    ds.series["DateTime"] = {}
    ds.series["DateTime"]["Data"] = dt
    ds.series["DateTime"]["Flag"] = numpy.zeros(len(dt),dtype=numpy.int32)
    ds.series["DateTime"]["Attr"] = {}
    ds.series["DateTime"]["Attr"]["long_name"] = "Datetime in local timezone"
    ds.series["DateTime"]["Attr"]["units"] = "None"
    # now remove any "data"" from empty lines
    series_list = ds.series.keys()
    if "DateTime" in series_list: series_list.remove("DateTime")
    for item in series_list:
        ds.series[item]["Data"] = ds.series[item]["Data"][idx]
        ds.series[item]["Flag"] = ds.series[item]["Flag"][idx]
    ds.globalattributes["nc_nrecs"] = nRecs
    return 1

def DateTimeFromDateAndTimeString(ds,DateString_in,TimeString_in):
    if DateString_in not in ds.series.keys():
        logger.error(" Requested date series "+DateString_in+" not found")
        return 0
    if TimeString_in not in ds.series.keys():
        logger.error(" Requested time series "+TimeString_in+" not found")
        return 0
    DateString = ds.series[DateString_in]["Data"]
    TimeString = ds.series[TimeString_in]["Data"]
    # guard against empty fields in what we assume is the datetime
    idx = [i for i in range(len(DateString)) if len(str(DateString[i]))>0]
    dt = [dateutil.parser.parse(str(DateString[i])+" "+str(TimeString[i])) for i in idx]
    # we have finished with the date and time strings so delete them from the data structure
    del ds.series[DateString_in],ds.series[TimeString_in]
    nRecs = len(dt)
    ds.series["DateTime"] = {}
    ds.series["DateTime"]["Data"] = dt
    ds.series["DateTime"]["Flag"] = numpy.zeros(len(dt),dtype=numpy.int32)
    ds.series["DateTime"]["Attr"] = {}
    ds.series["DateTime"]["Attr"]["long_name"] = "Datetime in local timezone"
    ds.series["DateTime"]["Attr"]["units"] = "None"
    # now remove any "data"" from empty lines
    series_list = ds.series.keys()
    if "DateTime" in series_list: series_list.remove("DateTime")
    for item in series_list:
        ds.series[item]["Data"] = ds.series[item]["Data"][idx]
        ds.series[item]["Flag"] = ds.series[item]["Flag"][idx]
    ds.globalattributes["nc_nrecs"] = nRecs
    return 1

def MRfromRH(ds, MR_out, RH_in, Ta_in, ps_in):
    """
    Purpose:
     Calculate H2O mixing ratio from RH.
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    for item in [RH_in, Ta_in, ps_in]:
        if item not in ds.series.keys():
            msg = " MRfromRH: Requested series "+item+" not found, "+MR_out+" not calculated"
            logger.error(msg)
            return 0
    if MR_out in ds.series.keys():
        msg = " MRfromRH: Output series "+MR_out+" already exists, skipping ..."
        logger.error(msg)
        return 0
    RH_data,RH_flag,RH_attr = pfp_utils.GetSeriesasMA(ds, RH_in)
    Ta_data,Ta_flag,Ta_attr = pfp_utils.GetSeriesasMA(ds, Ta_in)
    Ah_data = mf.absolutehumidityfromRH(Ta_data, RH_data)
    ps_data,ps_flag,ps_attr = pfp_utils.GetSeriesasMA(ds, ps_in)
    MR_data = mf.h2o_mmolpmolfromgpm3(Ah_data, Ta_data, ps_data)
    MR_attr = pfp_utils.MakeAttributeDictionary(long_name="H2O mixing ratio calculated from "+RH_in+", "+Ta_in+" and "+ps_in,
                                              height=RH_attr["height"],
                                              units="mmol/mol")
    flag = numpy.where(numpy.ma.getmaskarray(MR_data)==True,ones,zeros)
    pfp_utils.CreateSeries(ds, MR_out, MR_data, flag, MR_attr)
    return 1