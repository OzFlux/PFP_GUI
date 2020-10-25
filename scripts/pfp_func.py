# standard modules
import logging
# 3rd party
import numpy
# PFP modules
import meteorologicalfunctions as pfp_mf
import pfp_utils

logger = logging.getLogger("pfp_log")

def Convert_fraction_to_percent(ds, RH_out, RH_in):
    """
    Purpose:
     Function to convert RH in units of "frac" (0 to 1) to "percent" (1 to 100).
    Usage:
     pfp_func.Convert_fraction_to_percent(ds, RH_out, RH_in)
    Author: PRI
    Date: August 2019
    """
    var_in = pfp_utils.GetVariable(ds, RH_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "%", mode="quiet")
    var_out["Label"] = RH_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_gH2Opm3_to_percent(ds, RH_out, Ah_in, Ta_in):
    """
    Purpose:
     Function to convert absolute humidity in units of g/m3 to relative humidity in percent.
    Usage:
     pfp_func.Convert_gH2Opm3_to_percent(ds, RH_out, Ah_in, Ta_in)
    Author: PRI
    Date: September 2020
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    for item in [Ah_in, Ta_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + RH_out + " not calculated"
            logger.error(msg)
            return 0
    Ah = pfp_utils.GetVariable(ds, Ah_in)
    Ta = pfp_utils.GetVariable(ds, Ta_in)
    RH = pfp_utils.GetVariable(ds, RH_out)
    RH["Data"] = pfp_mf.RHfromabsolutehumidity(Ah["Data"], Ta["Data"])
    RH["Flag"] = numpy.where(numpy.ma.getmaskarray(RH["Data"]) == True, ones, zeros)
    RH["Attr"]["units"] = "%"
    pfp_utils.CreateVariable(ds, RH)
    return 1

def Convert_gH2Opm3_to_mmolpm3(ds, H2O_out, Ah_in):
    """
    Purpose:
     Calculate H2O molar density in mmol/m3 from absolute humidity in g/m3.
    Usage:
     pfp_func.Convert_gH2Opm3_to_mmolpm3(ds, MD_out, Ah_in)
    Author: PRI
    Date: September 2020
    """
    for item in [Ah_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + H2O_out + " not calculated"
            logger.error(msg)
            return 0
    var_in = pfp_utils.GetVariable(ds, Ah_in)
    got_variance = False
    if "Vr" in var_in["Label"] and ")2" in var_in["Attr"]["units"]:
        got_variance = True
        var_in["Data"] = numpy.ma.sqrt(var_in["Data"])
        var_in["Attr"]["units"] = pfp_utils.units_variance_to_standard_deviation(var_in["Attr"]["units"])
    var_out = pfp_utils.convert_units_func(ds, var_in, "mmol/m3", mode="quiet")
    var_out["Label"] = H2O_out
    if got_variance:
        var_out["Data"] = var_out["Data"]*var_out["Data"]
        var_out["Attr"]["units"] = pfp_utils.units_standard_deviation_to_variance(var_out["Attr"]["units"])
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_gH2Opm3_to_mmolpmol(ds, MF_out, Ah_in, Ta_in, ps_in):
    """
    Purpose:
     Calculate H2O mole fraction in mml/mol from absolute humidity in g/m3.
    Usage:
     pfp_func.Convert_gH2Opm3_to_mmolpmol(ds, MF_out, Ah_in, Ta_in, ps_in)
    Author: PRI
    Date: August 2019
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    for item in [Ah_in, Ta_in, ps_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + MF_out + " not calculated"
            logger.error(msg)
            return 0
    Ah = pfp_utils.GetVariable(ds, Ah_in)
    Ah = pfp_utils.convert_units_func(ds, Ah, "g/m3")
    Ta = pfp_utils.GetVariable(ds, Ta_in)
    Ta = pfp_utils.convert_units_func(ds, Ta, "C")
    ps = pfp_utils.GetVariable(ds, ps_in)
    ps = pfp_utils.convert_units_func(ds, ps, "kPa")
    MF = pfp_utils.GetVariable(ds, MF_out)
    MF["Data"] = pfp_mf.h2o_mmolpmolfromgpm3(Ah["Data"], Ta["Data"], ps["Data"])
    MF["Flag"] = numpy.where(numpy.ma.getmaskarray(MF["Data"]) == True, ones, zeros)
    MF["Attr"]["units"] = "mmol/mol"
    pfp_utils.CreateVariable(ds, MF)
    return 1

def Convert_hPa_to_kPa(ds, ps_out, ps_in):
    """
    Purpose:
     Function to convert pressure from hPa (mb) to kPa.
    Usage:
     pfp_func.ConverthPa2kPa(ds, ps_in, ps_out)
    Author: PRI
    Date: February 2018
    """
    var_in = pfp_utils.GetVariable(ds, ps_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "kPa", mode="quiet")
    var_out["Label"] = ps_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_K_to_C(ds, T_out, T_in):
    """
    Purpose:
     Function to convert temperature from K to C.
    Usage:
     pfp_func.Convert_K_to_C(ds, T_out, T_in)
    Author: PRI
    Date: February 2018
    """
    if T_in not in ds.series.keys():
        msg = " ConvertK2C: variable " + T_in + " not found, skipping ..."
        logger.warning(msg)
        return 0
    if "<" in T_out or ">" in T_out:
        logger.warning(" ***")
        msg = " *** " + T_in + ": illegal name (" + T_out + ") in function, skipping ..."
        logger.warning(msg)
        logger.warning(" ***")
        return 0
    var_in = pfp_utils.GetVariable(ds, T_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "C", mode="quiet")
    var_out["Label"] = T_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_kgpm3_to_gpm3(ds, Ah_out, Ah_in):
    """
    Purpose:
     Function to convert absolute humidity from kg/m3 to g/m3.
    Usage:
     pfp_func.Convertkgpm32gpm3(ds, Ah_out, Ah_in)
    Author: PRI
    Date: August 2020
    """
    var_in = pfp_utils.GetVariable(ds, Ah_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "g/m3", mode="quiet")
    var_out["Label"] = Ah_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_mgCO2pm3_to_mmolpm3(ds, CO2_out, CO2_in):
    """
    Purpose:
     Calculate CO2 molar density in mmol/m3 from CO2 concentration in mg/m3.
    Usage:
     pfp_func.Convert_mgCO2pm3_to_mmolpm3(ds, CO2_out, CO2_in)
    Author: PRI
    Date: September 2020
    """
    for item in [CO2_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + CO2_out + " not calculated"
            logger.error(msg)
            return 0
    var_in = pfp_utils.GetVariable(ds, CO2_in)
    got_variance = False
    if "Vr" in var_in["Label"] and ")2" in var_in["Attr"]["units"]:
        got_variance = True
        var_in["Data"] = numpy.ma.sqrt(var_in["Data"])
        var_in["Attr"]["units"] = pfp_utils.units_variance_to_standard_deviation(var_in["Attr"]["units"])
    var_out = pfp_utils.convert_units_func(ds, var_in, "mmol/m3", mode="quiet")
    var_out["Label"] = CO2_out
    if got_variance:
        var_out["Data"] = var_out["Data"]*var_out["Data"]
        var_out["Attr"]["units"] = pfp_utils.units_standard_deviation_to_variance(var_out["Attr"]["units"])
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_mgCO2pm3_to_umolpmol(ds, MF_out, Cc_in, Ta_in, ps_in):
    """
    Purpose:
     Calculate CO2 mole fraction in uml/mol from mass density in mgCO2/m3.
    Usage:
     pfp_func.Convert_mgCO2pm3_to_umolpmol(ds, MF_out, Cc_in, Ta_in, ps_in)
    Author: PRI
    Date: August 2019
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    for item in [Cc_in, Ta_in, ps_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + MF_out + " not calculated"
            logger.error(msg)
            return 0
    Cc = pfp_utils.GetVariable(ds, Cc_in)
    Cc = pfp_utils.convert_units_func(ds, Cc, "mg/m3")
    Ta = pfp_utils.GetVariable(ds, Ta_in)
    Ta = pfp_utils.convert_units_func(ds, Ta, "C")
    ps = pfp_utils.GetVariable(ds, ps_in)
    ps = pfp_utils.convert_units_func(ds, ps, "kPa")
    MF = pfp_utils.GetVariable(ds, MF_out)
    MF["Data"] = pfp_mf.co2_ppmfrommgCO2pm3(Cc["Data"], Ta["Data"], ps["Data"])
    MF["Flag"] = numpy.where(numpy.ma.getmaskarray(MF["Data"]) == True, ones, zeros)
    MF["Attr"]["units"] = "umol/mol"
    pfp_utils.CreateVariable(ds, MF)
    return 1

def Convert_mmolpm3_to_gH2Opm3(ds, Ah_out, H2O_in):
    """
    Purpose:
     Function to convert mmol/m3 (molar density) to g/m3 (mass density).
    Usage:
     pfp_func.Convert_mmolpm3_to_gpm3(ds, Ah_out, H2O_in)
    Author: PRI
    Date: August 2020
    """
    for item in [H2O_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + Ah_out + " not calculated"
            logger.error(msg)
            return 0
    var_in = pfp_utils.GetVariable(ds, H2O_in)
    got_variance = False
    if "Vr" in var_in["Label"] and ")2" in var_in["Attr"]["units"]:
        got_variance = True
        var_in["Data"] = numpy.ma.sqrt(var_in["Data"])
        var_in["Attr"]["units"] = pfp_utils.units_variance_to_standard_deviation(var_in["Attr"]["units"])
    var_out = pfp_utils.convert_units_func(ds, var_in, "g/m3", mode="quiet")
    var_out["Label"] = Ah_out
    if got_variance:
        var_out["Data"] = var_out["Data"]*var_out["Data"]
        var_out["Attr"]["units"] = pfp_utils.units_standard_deviation_to_variance(var_out["Attr"]["units"])
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_mmolpmol_to_gH2Opm3(ds, Ah_out, MF_in, Ta_in, ps_in):
    """
    Purpose:
     Function to calculate absolute humidity given the water vapour mole
     fraction, air temperature and pressure.  Absolute humidity is not calculated
     if any of the input series are missing or if the specified output series
     already exists in the data structure.
     The calculated absolute humidity is created as a new series in the
     data structure.
    Usage:
     pfp_func.Convert_mmolpmol_to_gpm3(ds,"Ah_IRGA_Av","H2O_IRGA_Av","Ta_HMP_2m","ps")
    Author: PRI
    Date: September 2015
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    for item in [MF_in, Ta_in, ps_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + Ah_out + " not calculated"
            logger.error(msg)
            return 0
    MF = pfp_utils.GetVariable(ds, MF_in)
    MF = pfp_utils.convert_units_func(ds, MF, "mmol/mol")
    Ta = pfp_utils.GetVariable(ds, Ta_in)
    Ta = pfp_utils.convert_units_func(ds, Ta, "C")
    ps = pfp_utils.GetVariable(ds, ps_in)
    ps = pfp_utils.convert_units_func(ds, ps, "kPa")
    Ah = pfp_utils.GetVariable(ds, Ah_out)
    Ah["Data"] = pfp_mf.h2o_gpm3frommmolpmol(MF["Data"], Ta["Data"], ps["Data"])
    Ah["Flag"] = numpy.where(numpy.ma.getmaskarray(Ah["Data"]) == True, ones, zeros)
    Ah["Attr"]["units"] = "g/m3"
    pfp_utils.CreateVariable(ds, Ah)
    return 1

def Convert_percent_to_mmolpmol(ds, MF_out, RH_in, Ta_in, ps_in):
    """
    Purpose:
     Calculate H2O mole fraction from relative humidity (RH).
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    for item in [RH_in, Ta_in, ps_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + MF_out + " not calculated"
            logger.error(msg)
            return 0
    # get the relative humidity and check the units
    RH = pfp_utils.GetVariable(ds, RH_in)
    RH = pfp_utils.convert_units_func(ds, RH, "%")
    # get the temperature and check the units
    Ta = pfp_utils.GetVariable(ds, Ta_in)
    Ta = pfp_utils.convert_units_func(ds, Ta, "C")
    # get the absoulte humidity
    Ah_data = pfp_mf.absolutehumidityfromRH(Ta["Data"], RH["Data"])
    # get the atmospheric pressure and check the units
    ps = pfp_utils.GetVariable(ds, ps_in)
    ps = pfp_utils.convert_units_func(ds, ps, "kPa")
    # get the output variable (created in pfp_ts.DoFunctions())
    MF = pfp_utils.GetVariable(ds, MF_out)
    # do the business
    MF["Data"] = pfp_mf.h2o_mmolpmolfromgpm3(Ah_data, Ta["Data"], ps["Data"])
    MF["Flag"] = numpy.where(numpy.ma.getmaskarray(MF["Data"]) == True, ones, zeros)
    MF["Attr"]["units"] = "mmol/mol"
    # put the output variable back into the data structure
    pfp_utils.CreateVariable(ds, MF)
    return 1

def Convert_percent_to_gH2Opm3(ds, Ah_out, RH_in, Ta_in):
    """
    Purpose:
     Function to calculate absolute humidity given relative humidity and
     air temperature.  Absolute humidity is not calculated if any of the
     input series are missing or if the specified output series already
     exists in the data structure.
     The calculated absolute humidity is created as a new series in the
     data structure.
    Usage:
     pfp_func.Convert_percent_to_gpm3(ds,"Ah_HMP_2m","RH_HMP_2m","Ta_HMP_2m")
    Author: PRI
    Date: September 2015
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    for item in [RH_in, Ta_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + Ah_out + " not calculated"
            logger.error(msg)
            return 0
    # get the relative humidity and check the units
    RH = pfp_utils.GetVariable(ds, RH_in)
    RH = pfp_utils.convert_units_func(ds, RH, "%")
    # get the temperature and check the units
    Ta = pfp_utils.GetVariable(ds, Ta_in)
    Ta = pfp_utils.convert_units_func(ds, Ta, "C")
    # get the absolute humidity
    Ah = pfp_utils.GetVariable(ds, Ah_out)
    Ah["Data"] = pfp_mf.absolutehumidityfromRH(Ta["Data"], RH["Data"])
    Ah["Flag"] = numpy.where(numpy.ma.getmaskarray(Ah["Data"]) == True, ones, zeros)
    Ah["Attr"]["units"] = "g/m3"
    pfp_utils.CreateVariable(ds, Ah)
    return 1

def Convert_Pa_to_kPa(ds, ps_out, ps_in):
    """
    Purpose:
     Function to convert pressure from Pa to kPa.
    Usage:
     pfp_func.ConvertPa2kPa(ds, ps_out, ps_in)
    Author: PRI
    Date: February 2018
    """
    var_in = pfp_utils.GetVariable(ds, ps_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "kPa", mode="quiet")
    var_out["Label"] = ps_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Convert_percent_to_m3pm3(ds, Sws_out, Sws_in):
    """
    Purpose:
     Function to convert Sws in units of "percent" (1 to 100) to "frac" (0 to 1).
    Usage:
     pfp_func.ConvertPercent2m3pm3(ds, Sws_out, Sws_in)
    Author: PRI
    Date: April 2020
    """
    var_in = pfp_utils.GetVariable(ds, Sws_in)
    var_out = pfp_utils.convert_units_func(ds, var_in, "m3/m3", mode="quiet")
    var_out["Label"] = Sws_out
    pfp_utils.CreateVariable(ds, var_out)
    return 1

def Linear(ds, label_out, label_in, slope, offset):
    """
    Purpose:
     Function to apply a linear correction to a variable.
    Usage:
     pfp_func.Linear(ds, label_out, label_in, slope, offset)
    Author: PRI
    Date: August 2019
    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    for item in [label_in]:
        if item not in ds.series.keys():
            msg = " Requested series " + item + " not found, " + label_out + " not calculated"
            logger.error(msg)
            return 0
    var_in = pfp_utils.GetVariable(ds, label_in)
    var_out = pfp_utils.GetVariable(ds, label_out)
    var_out["Data"] = var_in["Data"] * float(slope) + float(offset)
    var_out["Flag"] = numpy.where(numpy.ma.getmaskarray(var_out["Data"]) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, var_out)
    return 1

#def DateTime_from_DoY(ds, dt_out, Year_in, DoY_in, Hdh_in):
    #year,f,a = pfp_utils.GetSeriesasMA(ds,Year_in)
    #doy,f,a = pfp_utils.GetSeriesasMA(ds,DoY_in)
    #hdh,f,a = pfp_utils.GetSeriesasMA(ds,Hdh_in)
    #idx = numpy.ma.where((numpy.ma.getmaskarray(year)==False)&
                         #(numpy.ma.getmaskarray(doy)==False)&
                         #(numpy.ma.getmaskarray(hdh)==False))[0]
    #year = year[idx]
    #doy = doy[idx]
    #hdh = hdh[idx]
    #hour = numpy.array(hdh,dtype=numpy.integer)
    #minute = numpy.array((hdh-hour)*60,dtype=numpy.integer)
    #dt = [datetime.datetime(int(y),1,1,h,m)+datetime.timedelta(int(d)-1) for y,d,h,m in zip(year,doy,hour,minute)]
    #nRecs = len(dt)
    #ds.series[dt_out] = {}
    #ds.series[dt_out]["Data"] = dt
    #ds.series[dt_out]["Flag"] = numpy.zeros(len(dt),dtype=numpy.int32)
    #ds.series[dt_out]["Attr"] = {}
    #ds.series[dt_out]["Attr"]["long_name"] = "Datetime in local timezone"
    #ds.series[dt_out]["Attr"]["units"] = "None"
    ## now remove any "data"" from empty lines
    #series_list = ds.series.keys()
    #if dt_out in series_list: series_list.remove(dt_out)
    #for item in series_list:
        #ds.series[item]["Data"] = ds.series[item]["Data"][idx]
        #ds.series[item]["Flag"] = ds.series[item]["Flag"][idx]
    #ds.globalattributes["nc_nrecs"] = nRecs
    #return 1

#def DateTime_from_TimeStamp(ds, dt_out, TimeStamp_in, fmt=""):
    #if TimeStamp_in not in ds.series.keys():
        #logger.error(" Required series "+TimeStamp_in+" not found")
        #return 0
    #TimeStamp = ds.series[TimeStamp_in]["Data"]
    ## guard against empty fields in what we assume is the datetime
    #idx = [i for i in range(len(TimeStamp)) if len(str(TimeStamp[i]))>0]
    #if len(fmt)==0:
        #dt = [dateutil.parser.parse(str(TimeStamp[i])) for i in idx]
    #else:
        #yearfirst = False
        #dayfirst = False
        #if fmt.index("Y") < fmt.index("D"): yearfirst = True
        #if fmt.index("D") < fmt.index("M"): dayfirst = True
        #dt = [dateutil.parser.parse(str(TimeStamp[i]),dayfirst=dayfirst,yearfirst=yearfirst)
              #for i in idx]
    ## we have finished with the timestamp so delete it from the data structure
    #del ds.series[TimeStamp_in]
    #nRecs = len(dt)
    #ds.series[dt_out] = {}
    #ds.series[dt_out]["Data"] = dt
    #ds.series[dt_out]["Flag"] = numpy.zeros(len(dt),dtype=numpy.int32)
    #ds.series[dt_out]["Attr"] = {}
    #ds.series[dt_out]["Attr"]["long_name"] = "Datetime in local timezone"
    #ds.series[dt_out]["Attr"]["units"] = "None"
    ## now remove any "data"" from empty lines
    #series_list = ds.series.keys()
    #if dt_out in series_list: series_list.remove(dt_out)
    #for item in series_list:
        #ds.series[item]["Data"] = ds.series[item]["Data"][idx]
        #ds.series[item]["Flag"] = ds.series[item]["Flag"][idx]
    #ds.globalattributes["nc_nrecs"] = nRecs
    #return 1

#def DateTime_from_ExcelDateAndTime(ds, dt_out, xlDate, xlTime):
    #""" Get Datetime from Excel date and time fields."""
    #xldate = ds.series[xlDate]
    #xltime = ds.series[xlTime]
    #nrecs = len(xldate["Data"])
    #xldatetime = pfp_utils.CreateEmptyVariable("xlDateTime", nrecs)
    #xldatetime["Data"] = xldate["Data"] + xltime["Data"]
    #xldatetime["Attr"]["long_name"] = "Date/time in Excel format"
    #xldatetime["Attr"]["units"] = "days since 1899-12-31 00:00:00"
    #pfp_utils.CreateVariable(ds, xldatetime)
    #pfp_utils.get_datetime_from_xldatetime(ds)
    #return 1

#def DateTime_from_DateAndTimeString(ds, dt_out, Date, Time):
    #if Date not in ds.series.keys():
        #logger.error(" Requested date series "+Date+" not found")
        #return 0
    #if Time not in ds.series.keys():
        #logger.error(" Requested time series "+Time+" not found")
        #return 0
    #DateString = ds.series[Date]["Data"]
    #TimeString = ds.series[Time]["Data"]
    ## guard against empty fields in what we assume is the datetime
    #idx = [i for i in range(len(DateString)) if len(str(DateString[i]))>0]
    #dt = [dateutil.parser.parse(str(DateString[i])+" "+str(TimeString[i])) for i in idx]
    ## we have finished with the date and time strings so delete them from the data structure
    #del ds.series[Date], ds.series[Time]
    #nRecs = len(dt)
    #ds.series[dt_out] = {}
    #ds.series[dt_out]["Data"] = dt
    #ds.series[dt_out]["Flag"] = numpy.zeros(len(dt),dtype=numpy.int32)
    #ds.series[dt_out]["Attr"] = {}
    #ds.series[dt_out]["Attr"]["long_name"] = "Datetime in local timezone"
    #ds.series[dt_out]["Attr"]["units"] = "None"
    ## now remove any "data"" from empty lines
    #series_list = ds.series.keys()
    #if dt_out in series_list: series_list.remove(dt_out)
    #for item in series_list:
        #ds.series[item]["Data"] = ds.series[item]["Data"][idx]
        #ds.series[item]["Flag"] = ds.series[item]["Flag"][idx]
    #ds.globalattributes["nc_nrecs"] = nRecs
    #return 1

#def Sd_from_Vr(ds, Sd_out, Vr_in):
    #"""
    #Purpose:
     #Get the standard deviation from the variance.
    #"""
    #if Vr_in not in list(ds.series.keys()):
        #msg = " Sd_from_Vr: Requested series " + Vr_in + " not found, " + Sd_out + " not calculated"
        #logger.error(msg)
        #return 0
    #if Sd_out in list(ds.series.keys()):
        #msg = " Sd_from_Vr: Output series " + Sd_out + " already exists, skipping ..."
        #logger.error(msg)
        #return 0
    #vr = pfp_utils.GetVariable(ds, Vr_in)
    #sd = copy.deepcopy(vr)
    #sd["Data"] = numpy.ma.sqrt(vr["Data"])
    #sd["Attr"]["units"] = pfp_utils.units_variance_to_standard_deviation(vr["Attr"]["units"])
    #pfp_utils.CreateVariable(ds, sd)
    #return 1

#def Vr_from_Sd(ds, Vr_out, Sd_in):
    #"""
    #Purpose:
     #Get the variance from the standard deviation.
    #"""
    #if Sd_in not in list(ds.series.keys()):
        #msg = " Vr_from_Sd: Requested series " + Sd_in + " not found, " + Vr_out + " not calculated"
        #logger.error(msg)
        #return 0
    #if Vr_out in list(ds.series.keys()):
        #msg = " Vr_from_Sd: Output series " + Vr_out + " already exists, skipping ..."
        #logger.error(msg)
        #return 0
    #sd = pfp_utils.GetVariable(ds, Sd_in)
    #vr = copy.deepcopy(sd)
    #vr["Data"] = sd["Data"]*sd["Data"]
    #vr["Attr"]["units"] = pfp_utils.units_standard_deviation_to_variance(sd["Attr"]["units"])
    #pfp_utils.CreateVariable(ds, vr)
    #return 1
