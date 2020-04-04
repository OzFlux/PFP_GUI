# standard
import ast
import copy
import datetime
import inspect
import logging
import os
import sys
import time
# 3d party
import numpy
from matplotlib.dates import date2num
from matplotlib.mlab import griddata
from scipy import interpolate, signal
import xlrd
import xlwt
# PFP
import constants as c
import meteorologicalfunctions as pfp_mf
import pfp_ck
import pfp_func
import pfp_io
import pfp_utils
import pysolar

logger = logging.getLogger("pfp_log")

def ApplyLinear(cf,ds,ThisOne):
    """
        Applies a linear correction to variable passed from pfp_ls. Time period
        to apply the correction, slope and offset are specified in the control
        file.

        Usage pfp_ts.ApplyLinear(cf,ds,x)
        cf: control file
        ds: data structure
        x: input/output variable in ds.  Example: 'Cc_7500_Av'
        """
    if ThisOne not in ds.series.keys(): return
    if pfp_utils.incf(cf,ThisOne) and pfp_utils.haskey(cf,ThisOne,'Linear'):
        logger.info('  Applying linear correction to '+ThisOne)
        data = numpy.ma.masked_where(ds.series[ThisOne]['Data']==float(c.missing_value),ds.series[ThisOne]['Data'])
        flag = ds.series[ThisOne]['Flag'].copy()
        ldt = ds.series['DateTime']['Data']
        LinearList = cf['Variables'][ThisOne]['Linear'].keys()
        for i in range(len(LinearList)):
            linear_dates_string = cf['Variables'][ThisOne]['Linear'][str(i)]
            linear_dates_list = linear_dates_string.split(",")
            try:
                dt = datetime.datetime.strptime(linear_dates_list[0],'%Y-%m-%d %H:%M')
                si = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                si = 0
            try:
                dt = datetime.datetime.strptime(linear_dates_list[1],'%Y-%m-%d %H:%M')
                ei = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                ei = -1
            Slope = float(linear_dates_list[2])
            Offset = float(linear_dates_list[3])
            data[si:ei] = Slope * data[si:ei] + Offset
            index = numpy.where(flag[si:ei]==0)[0]
            flag[si:ei][index] = numpy.int32(10)
            ds.series[ThisOne]['Data'] = numpy.ma.filled(data,float(c.missing_value)).astype(numpy.float64)
            ds.series[ThisOne]['Flag'] = flag

def ApplyLinearDrift(cf,ds,ThisOne):
    """
        Applies a linear correction to variable passed from pfp_ls. The slope is
        interpolated for each 30-min period between the starting value at time 0
        and the ending value at time 1.  Slope0, Slope1 and Offset are defined
        in the control file.  This function applies to a dataset in which the
        start and end times in the control file are matched by the time period
        in the dataset.

        Usage pfp_ts.ApplyLinearDrift(cf,ds,x)
        cf: control file
        ds: data structure
        x: input/output variable in ds.  Example: 'Cc_7500_Av'
        """
    if ThisOne not in ds.series.keys(): return
    if pfp_utils.incf(cf,ThisOne) and pfp_utils.haskey(cf,ThisOne,'Drift'):
        logger.info('  Applying linear drift correction to '+ThisOne)
        data = numpy.ma.masked_where(ds.series[ThisOne]['Data']==float(c.missing_value),ds.series[ThisOne]['Data'])
        flag = ds.series[ThisOne]['Flag']
        ldt = ds.series['DateTime']['Data']
        DriftList = cf['Variables'][ThisOne]['Drift'].keys()
        for i in range(len(DriftList)):
            DriftItemList = ast.literal_eval(cf['Variables'][ThisOne]['Drift'][str(i)])
            try:
                dt = datetime.datetime.strptime(DriftItemList[0],'%Y-%m-%d %H:%M')
                si = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                si = 0
            try:
                dt = datetime.datetime.strptime(DriftItemList[1],'%Y-%m-%d %H:%M') + 1
                ei = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                ei = -1
            Slope = numpy.zeros(len(data))
            Slope0 = float(DriftItemList[2])
            Slope1 = float(DriftItemList[3])
            Offset = float(DriftItemList[4])
            nRecs = len(Slope[si:ei])
            for i in range(nRecs):
                ssi = si + i
                Slope[ssi] = ((((Slope1 - Slope0) / nRecs) * i) + Slope0)
            data[si:ei] = Slope[si:ei] * data[si:ei] + Offset
            flag[si:ei] = 10
            ds.series[ThisOne]['Data'] = numpy.ma.filled(data,float(c.missing_value))
            ds.series[ThisOne]['Flag'] = flag

def ApplyLinearDriftLocal(cf,ds,ThisOne):
    """
        Applies a linear correction to variable passed from pfp_ls. The slope is
        interpolated since the starting value at time 0 using a known 30-min
        increment.  Slope0, SlopeIncrement and Offset are defined in the control
        file.  This function applies to a dataset in which the start time in the
        control file is matched by dataset start time, but in which the end time
        in the control file extends beyond the dataset end.

        Usage pfp_ts.ApplyLinearDriftLocal(cf,ds,x)
        cf: control file
        ds: data structure
        x: input/output variable in ds.  Example: 'Cc_7500_Av'
        """
    if ThisOne not in ds.series.keys(): return
    if pfp_utils.incf(cf,ThisOne) and pfp_utils.haskey(cf,ThisOne,'LocalDrift'):
        logger.info('  Applying linear drift correction to '+ThisOne)
        data = numpy.ma.masked_where(ds.series[ThisOne]['Data']==float(c.missing_value),ds.series[ThisOne]['Data'])
        flag = ds.series[ThisOne]['Flag']
        ldt = ds.series['DateTime']['Data']
        DriftList = cf['Variables'][ThisOne]['LocalDrift'].keys()
        for i in range(len(DriftList)):
            DriftItemList = ast.literal_eval(cf['Variables'][ThisOne]['LocalDrift'][str(i)])
            try:
                dt = datetime.datetime.strptime(DriftItemList[0],'%Y-%m-%d %H:%M')
                si = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                si = 0
            try:
                dt = datetime.datetime.strptime(DriftItemList[1],'%Y-%m-%d %H:%M') + 1
                ei = pfp_utils.find_nearest_value(ldt, dt)
            except ValueError:
                ei = -1
            Slope = numpy.zeros(len(data))
            Slope0 = float(DriftItemList[2])
            SlopeIncrement = float(DriftItemList[3])
            Offset = float(DriftItemList[4])
            nRecs = len(Slope[si:ei])
            for i in range(nRecs):
                ssi = si + i
                Slope[ssi] = (SlopeIncrement * i) + Slope0
            data[si:ei] = Slope[si:ei] * data[si:ei] + Offset
            flag[si:ei] = numpy.int32(10)
            ds.series[ThisOne]['Data'] = numpy.ma.filled(data,float(c.missing_value))
            ds.series[ThisOne]['Flag'] = flag

def AverageSeriesByElements(cf,ds,Av_out):
    """
        Calculates the average of multiple time series.  Multiple time series
        are entered and a single time series representing the average at each
        observational period is returned.

        Usage pfp_ts.AverageSeriesByElements(cf,ds,Av_out)
        cf: control file object (must contain an entry for Av_out)
        ds: data structure
        Av_out: output variable to ds.  Example: 'Fg'
        Series_in: input variable series in ds.  Example: ['Fg_8cma','Fg_8cmb']
        """
    if Av_out not in cf['Variables'].keys(): return
    if Av_out in ds.averageserieslist: return
    srclist = pfp_utils.GetAverageSeriesKeys(cf,Av_out)
    logger.info(' Averaging '+str(srclist)+'==>'+Av_out)

    nSeries = len(srclist)
    if nSeries==0:
        logger.error('  AverageSeriesByElements: no input series specified for'+str(Av_out))
        return
    if nSeries==1:
        tmp_data = ds.series[srclist[0]]['Data'].copy()
        tmp_flag = ds.series[srclist[0]]['Flag'].copy()
        tmp_attr = ds.series[srclist[0]]['Attr'].copy()
        Av_data = numpy.ma.masked_where(tmp_data==float(c.missing_value),tmp_data)
        Mn_flag = tmp_flag
        SeriesNameString = srclist[0]
    else:
        tmp_data = ds.series[srclist[0]]['Data'].copy()
        tmp_flag = ds.series[srclist[0]]['Flag'].copy()

        index = numpy.where(numpy.mod(tmp_flag,10)==0)    # find the elements with flag = 0, 10, 20 etc
        tmp_flag[index] = 0                               # set them all to 0

        tmp_attr = ds.series[srclist[0]]['Attr'].copy()
        SeriesNameString = srclist[0]
        srclist.remove(srclist[0])
        for ThisOne in srclist:
            SeriesNameString = SeriesNameString+', '+ThisOne
            tmp_data = numpy.vstack((tmp_data,ds.series[ThisOne]['Data'].copy()))
            tmp_flag = numpy.vstack((tmp_flag,ds.series[ThisOne]['Flag'].copy()))
        tmp_data = numpy.ma.masked_where(tmp_data==float(c.missing_value),tmp_data)
        Av_data = numpy.ma.average(tmp_data,axis=0)
        Mn_flag = numpy.min(tmp_flag,axis=0)
    ds.averageserieslist.append(Av_out)
    #attr = pfp_utils.MakeAttributeDictionary(long_name='Element-wise average of series '+SeriesNameString,
                                       #standard_name=standardname,units=ds.series[srclist[0]]['Attr']['units'])
    # this is a temporary fix, better to have a routine update the attr dictionary
    tmp_attr["long_name"] = tmp_attr["long_name"]+", element-wise average of series " + SeriesNameString
    pfp_utils.CreateSeries(ds,Av_out,Av_data,Mn_flag,tmp_attr)

def CalculateAvailableEnergy(ds,Fa_out='Fa',Fn_in='Fn',Fg_in='Fg'):
    """
        Calculate the average energy as Fn - G.

        Usage pfp_ts.CalculateAvailableEnergy(ds,Fa_out='Fa',Fn_in='Fn',Fg_in='Fg')
        ds: data structure
        Fa_out: output available energy variable to ds.  Example: 'Fa'
        Fn_in: input net radiation in ds.  Example: 'Fn'
        Fg_in: input ground heat flux in ds.  Example: 'Fg'
        """
    logger.info(' Calculating available energy from Fn and Fg')
    if Fn_in not in ds.series.keys():
        logger.warning(" Series "+Fn_in+" not found in data file")
        return
    if Fg_in not in ds.series.keys():
        logger.warning(" Series "+Fg_in+" not found in data file")
        return
    Fn,Fn_flag,a = pfp_utils.GetSeriesasMA(ds,Fn_in)
    Fg,Fg_flag,a = pfp_utils.GetSeriesasMA(ds,Fg_in)
    Fa_calc = Fn - Fg
    Fa_calc_flag = numpy.zeros(len(Fa_calc),dtype=numpy.int32)
    idx = numpy.where((numpy.ma.getmaskarray(Fn)==True)|(numpy.ma.getmaskarray(Fg)==True))[0]
    Fa_calc_flag[idx] = numpy.int32(1)
    if Fa_out not in ds.series.keys():
        attr = pfp_utils.MakeAttributeDictionary(long_name='Available energy using '+Fn_in+','+Fg_in,units='W/m2')
        pfp_utils.CreateSeries(ds,Fa_out,Fa_calc,Fa_calc_flag,attr)
    else:
        Fa_exist,flag,attr = pfp_utils.GetSeriesasMA(ds,Fa_out)
        idx = numpy.where((numpy.ma.getmaskarray(Fa_exist)==True)&(numpy.ma.getmaskarray(Fa_calc)==False))[0]
        if len(idx)!=0:
            Fa_exist[idx] = Fa_calc[idx]
            flag[idx] = numpy.int32(20)
        pfp_utils.CreateSeries(ds,Fa_out,Fa_exist,flag,attr)
    return

def CalculateFluxes(cf, ds):
    """
        Calculate the fluxes from the rotated covariances.

        Usage pfp_ts.CalculateFluxes(ds)
        ds: data structure

        Pre-requisite: CoordRotation2D

        Accepts meteorological constants or variables
        """
    descr_level = "description_" + ds.globalattributes["nc_level"]
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    Ta = pfp_utils.GetVariable(ds, "Ta")
    ps = pfp_utils.GetVariable(ds, "ps")
    Ah = pfp_utils.GetVariable(ds, "Ah")
    rhom = pfp_utils.GetVariable(ds, "rhom")
    RhoCp = pfp_utils.GetVariable(ds, "RhoCp")
    Lv = pfp_utils.GetVariable(ds, "Lv")

    logger.info(" Calculating fluxes from covariances")
    if "wT" in ds.series.keys():
        ok_units = ["mC/s", "Cm/s"]
        wT = pfp_utils.GetVariable(ds, "wT")
        if wT["Attr"]["units"] in ok_units:
            Fhv = RhoCp["Data"]*wT["Data"]
            attr = {"group_name": "flux", "long_name": "Virtual heat flux", "units": "W/m2",
                    "standard_name": "not defined",
                    descr_level: "Rotated to natural wind coordinates"}
            for item in ["instrument", "height", "serial_number"]:
                attr[item] = wT["Attr"][item]
            flag = numpy.where(numpy.ma.getmaskarray(Fhv) == True, ones, zeros)
            pfp_utils.CreateVariable(ds, {"Label": "Fhv", "Data": Fhv, "Flag": flag, "Attr": attr})
        else:
            logger.error(" CalculateFluxes: Incorrect units for wT, Fhv not calculated")
    else:
        logger.error("  CalculateFluxes: wT not found, Fhv not calculated")
    if "wA" in ds.series.keys():
        wA = pfp_utils.GetVariable(ds, "wA")
        if wA["Attr"]["units"] == "g/m2/s":
            Fe = Lv["Data"]*wA["Data"]/float(1000)
            attr = {"group_name": "flux", "long_name": "Latent heat flux", "units": "W/m2",
                    "standard_name": "surface_upward_latent_heat_flux",
                    descr_level: "Rotated to natural wind coordinates"}
            for item in ["instrument", "height", "serial_number"]:
                attr[item] = wA["Attr"][item]
            flag = numpy.where(numpy.ma.getmaskarray(Fe) == True, ones, zeros)
            pfp_utils.CreateVariable(ds, {"Label": "Fe", "Data": Fe, "Flag": flag, "Attr": attr})
        else:
            logger.error(" CalculateFluxes: Incorrect units for wA, Fe not calculated")
    else:
        logger.error("  CalculateFluxes: wA not found, Fe not calculated")
    if "wC" in ds.series.keys():
        wC = pfp_utils.GetVariable(ds, "wC")
        if wC["Attr"]["units"] == "mg/m2/s":
            Fc = wC["Data"]
            attr = {"group_name": "flux", "long_name": "CO2 flux", "units": "mg/m2/s",
                    "standard_name": "not defined",
                    descr_level: "Rotated to natural wind coordinates"}
            for item in ["instrument", "height", "serial_number"]:
                attr[item] = wC["Attr"][item]
            flag = numpy.where(numpy.ma.getmaskarray(Fc) == True, ones, zeros)
            pfp_utils.CreateVariable(ds, {"Label": "Fc", "Data": Fc, "Flag": flag, "Attr": attr})
        else:
            logger.error(" CalculateFluxes: Incorrect units for wC, Fc not calculated")
    else:
        logger.error("  CalculateFluxes: wC not found, Fc not calculated")
    if "uw" in ds.series.keys():
        if "vw" in ds.series.keys():
            uw = pfp_utils.GetVariable(ds, "uw")
            vw = pfp_utils.GetVariable(ds, "vw")
            vs = uw["Data"]*uw["Data"] + vw["Data"]*vw["Data"]
            Fm = rhom["Data"]*numpy.ma.sqrt(vs)
            us = numpy.ma.sqrt(numpy.ma.sqrt(vs))
            attr = {"group_name": "flux", "long_name": "Momentum flux", "units": "kg/m/s2",
                    "standard_name": "not defined",
                    descr_level: "Rotated to natural wind coordinates"}
            for item in ["instrument", "height", "serial_number"]:
                attr[item] = uw["Attr"][item]
            flag = numpy.where(numpy.ma.getmaskarray(Fm) == True, ones, zeros)
            pfp_utils.CreateVariable(ds, {"Label": "Fm", "Data": Fm, "Flag": flag, "Attr": attr})
            pfp_utils.CreateVariable(ds, {"Label": "Fm_PFP", "Data": Fm, "Flag": flag, "Attr": attr})
            attr = {"group_name": "flux", "long_name": "Friction velocity", "units": "m/s",
                    "standard_name": "not defined",
                    descr_level: "Rotated to natural wind coordinates"}
            for item in ["instrument", "height", "serial_number"]:
                attr[item] = uw["Attr"][item]
            flag = numpy.where(numpy.ma.getmaskarray(us) == True, ones, zeros)
            pfp_utils.CreateVariable(ds, {"Label": "ustar", "Data": us, "Flag": flag, "Attr": attr})
            pfp_utils.CreateVariable(ds, {"Label": "ustar_PFP", "Data": us, "Flag": flag, "Attr": attr})
        else:
            logger.error("  CalculateFluxes: vw not found, Fm and ustar not calculated")
    else:
        logger.error("  CalculateFluxes: uw not found, Fm and ustar not calculated")

def CalculateLongwave(ds,Fl_out,Fl_in,Tbody_in):
    """
        Calculate the longwave radiation given the raw thermopile output and the
        sensor body temperature.

        Usage pfp_ts.CalculateLongwave(ds,Fl_out,Fl_in,Tbody_in)
        ds: data structure
        Fl_out: output longwave variable to ds.  Example: 'Flu'
        Fl_in: input longwave in ds.  Example: 'Flu_raw'
        Tbody_in: input sensor body temperature in ds.  Example: 'Tbody'
        """
    logger.info(' Calculating longwave radiation')
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    Fl_raw,f,a = pfp_utils.GetSeriesasMA(ds,Fl_in)
    Tbody,f,a = pfp_utils.GetSeriesasMA(ds,Tbody_in)
    Fl = Fl_raw + c.sb*(Tbody + 273.15)**4
    attr = pfp_utils.MakeAttributeDictionary(long_name='Calculated longwave radiation using '+Fl_in+','+Tbody_in,units='W/m2')
    flag = numpy.where(numpy.ma.getmaskarray(Fl)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,Fl_out,Fl,flag,attr)

def CalculateHumidities(ds):
    """
    Purpose:
     Calculate any missing humidities from whatever is available.
     If absolute humidity (Ah) is available then;
      - calculate specific humidity (q) if it is not present
      - calculate relative humidity (RH) if it is not present
     If specific humidity (q) is available then;
      - calculate absolute humidity (Ah) if it is not present
      - calculate relative humidity (RH) if it is not present
     If reative humidity (RH) is available then;
      - calculate specific humidity (q) if it is not present
      - calculate relative humidity (RH) if it is not present
    Usage:
     pfp_ts.CalculateHumidities(ds)
    Date:
     March 2015
    Author: PRI
    """
    if "Ah" not in ds.series.keys():
        if "SH" in ds.series.keys():
            AbsoluteHumidityFromq(ds)    # calculate Ah from q
        elif "RH" in ds.series.keys():
            AbsoluteHumidityFromRH(ds)   # calculate Ah from RH
    if "SH" not in ds.series.keys():
        if "Ah" in ds.series.keys():
            SpecificHumidityFromAh(ds)
        elif "RH" in ds.series.keys():
            SpecificHumidityFromRH(ds)
    if "RH" not in ds.series.keys():
        if "Ah" in ds.series.keys():
            RelativeHumidityFromAh(ds)
        elif "SH" in ds.series.keys():
            RelativeHumidityFromq(ds)

def CalculateHumiditiesAfterGapFill(ds, info):
    """
    Purpose:
     Check to see which humidity quantities (Ah, RH or q) have been gap filled
     and, if necessary, calculate the other humidity quantities from the gap
     filled one.
    Usage:
     pfp_ts.CalculateHumiditiesAfterGapFill(ds, info)
     where ds is a data structure
    Author: PRI
    Date: April 2015
    """
    # create an empty list
    alt_list = []
    # check to see if there was any gap filling using data from alternate sources
    if "GapFillFromAlternate" in info.keys():
        ia = info["GapFillFromAlternate"]
        # if so, get a list of the quantities gap filled from alternate sources
        alt_list = list(set([ia["outputs"][item]["target"] for item in ia["outputs"].keys()]))
    # create an empty list
    cli_list = []
    # check to see if there was any gap filling from climatology
    if "GapFillFromClimatology" in info.keys():
        ic = info["GapFillFromClimatology"]
        # if so, get a list of the quantities gap filled using climatology
        cli_list = list(set([ic["outputs"][item]["target"] for item in ic["outputs"].keys()]))
    # one list to rule them, one list to bind them ...
    gf_list = list(set(alt_list+cli_list))
    # clear out if there was no gap filling
    if len(gf_list)==0: return
    # check to see if absolute humidity (Ah) was gap filled ...
    if "Ah" in gf_list:
        if "SH" not in gf_list: SpecificHumidityFromAh(ds)
        if "RH" not in gf_list: RelativeHumidityFromAh(ds)
    # ... or was relative humidity (RH) gap filled ...
    elif "RH" in gf_list:
        if "Ah" not in gf_list: AbsoluteHumidityFromRH(ds)
        if "SH" not in gf_list: SpecificHumidityFromRH(ds)
    # ... or was specific humidity (q) gap filled ...
    elif "SH" in gf_list:
        if "Ah" not in gf_list: AbsoluteHumidityFromq(ds)
        if "RH" not in gf_list: RelativeHumidityFromq(ds)
    else:
        msg = "No humidities were gap filled!"
        logger.warning(msg)

def AbsoluteHumidityFromRH(ds):
    """ Calculate absolute humidity from relative humidity. """
    logger.info(' Calculating absolute humidity from relative humidity')
    descr_level = "description_" + ds.globalattributes["nc_level"]
    Ta,Ta_flag,a = pfp_utils.GetSeriesasMA(ds,"Ta")
    RH,RH_flag,a = pfp_utils.GetSeriesasMA(ds,"RH")
    Ah_new_flag = pfp_utils.MergeQCFlag([Ta_flag,RH_flag])
    Ah_new = pfp_mf.absolutehumidityfromRH(Ta,RH)
    if "Ah" in ds.series.keys():
        Ah,Ah_flag,Ah_attr = pfp_utils.GetSeriesasMA(ds,"Ah")
        index = numpy.where(numpy.ma.getmaskarray(Ah)==True)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(Ah)==True)[0]
        Ah[index] = Ah_new[index]
        Ah_flag[index] = Ah_new_flag[index]
        if descr_level in Ah_attr:
            Ah_attr[descr_level] += ", merged with Ah calculated from RH"
        else:
            Ah_attr[descr_level] = "Merged with Ah calculated from RH"
        pfp_utils.CreateSeries(ds,"Ah",Ah,Ah_flag,Ah_attr)
    else:
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity',units='g/m3',standard_name='mass_concentration_of_water_vapor_in_air')
        attr[descr_level] = "Absoulte humidity calculated from Ta and RH"
        attr["group_name"] = "meteorology"
        pfp_utils.CreateSeries(ds, "Ah", Ah_new, Ah_new_flag, attr)

def AbsoluteHumidityFromq(ds):
    """ Calculate absolute humidity from specific humidity. """
    logger.info(' Calculating absolute humidity from specific humidity')
    descr_level = "description_" + ds.globalattributes["nc_level"]
    Ta,Ta_flag,a = pfp_utils.GetSeriesasMA(ds,"Ta")
    ps,ps_flag,a = pfp_utils.GetSeriesasMA(ds,"ps")
    q, q_flag, a = pfp_utils.GetSeriesasMA(ds, "SH")
    Ah_new_flag = pfp_utils.MergeQCFlag([Ta_flag,ps_flag,q_flag])
    RH = pfp_mf.RHfromspecifichumidity(q,Ta,ps)
    Ah_new = pfp_mf.absolutehumidityfromRH(Ta,RH)
    if "Ah" in ds.series.keys():
        Ah,Ah_flag,Ah_attr = pfp_utils.GetSeriesasMA(ds,"Ah")
        index = numpy.where(numpy.ma.getmaskarray(Ah)==True)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(Ah)==True)[0]
        Ah[index] = Ah_new[index]
        Ah_flag[index] = Ah_new_flag[index]
        if descr_level in Ah_attr:
            Ah_attr[descr_level] += ", merged with Ah calculated from q"
        else:
            Ah_attr[descr_level] = "Merged with Ah calculated from q"
        pfp_utils.CreateSeries(ds,"Ah",Ah,Ah_flag,Ah_attr)
    else:
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity',units='g/m3',standard_name='mass_concentration_of_water_vapor_in_air')
        attr[descr_level] = "Absoulte humidity calculated from Ta, ps and q"
        attr["group_name"] = "meteorology"
        pfp_utils.CreateSeries(ds,"Ah",Ah_new,Ah_new_flag,attr)

def RelativeHumidityFromq(ds):
    """ Calculate relative humidity from specific humidity. """
    logger.info(' Calculating relative humidity from specific humidity')
    descr_level = "description_" + ds.globalattributes["nc_level"]
    Ta,Ta_flag,a = pfp_utils.GetSeriesasMA(ds,"Ta")
    ps,ps_flag,a = pfp_utils.GetSeriesasMA(ds,"ps")
    q, q_flag, a = pfp_utils.GetSeriesasMA(ds, "SH")
    RH_new_flag = pfp_utils.MergeQCFlag([Ta_flag,ps_flag,q_flag])
    RH_new = pfp_mf.RHfromspecifichumidity(q,Ta,ps)
    if "RH" in ds.series.keys():
        RH,RH_flag,RH_attr = pfp_utils.GetSeriesasMA(ds,"RH")
        index = numpy.where(numpy.ma.getmaskarray(RH)==True)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(RH)==True)[0]
        RH[index] = RH_new[index]
        RH_flag[index] = RH_new_flag[index]
        if descr_level in RH_attr:
            RH_attr[descr_level] += ", merged with RH calculated from q"
        else:
            RH_attr[descr_level] = "Merged with RH calculated from q"
        pfp_utils.CreateSeries(ds,"RH",RH,RH_flag,RH_attr)
    else:
        attr = pfp_utils.MakeAttributeDictionary(long_name='Relative humidity',units='%',standard_name='relative_humidity')
        attr[descr_level] = "Relative humidity calculated from SH, Ta and ps"
        attr["group_name"] = "meteorology"
        pfp_utils.CreateSeries(ds, "RH", RH_new, RH_new_flag, attr)

def RelativeHumidityFromAh(ds):
    """ Calculate relative humidity from absolute humidity. """
    logger.info(' Calculating relative humidity from absolute humidity')
    descr_level = "description_" + ds.globalattributes["nc_level"]
    Ta,Ta_flag,a = pfp_utils.GetSeriesasMA(ds,"Ta")
    Ah,Ah_flag,a = pfp_utils.GetSeriesasMA(ds,"Ah")
    RH_new_flag = pfp_utils.MergeQCFlag([Ta_flag,Ah_flag])
    RH_new = pfp_mf.RHfromabsolutehumidity(Ah,Ta)     # relative humidity in units of percent
    if "RH" in ds.series.keys():
        RH,RH_flag,RH_attr = pfp_utils.GetSeriesasMA(ds,"RH")
        index = numpy.where(numpy.ma.getmaskarray(RH)==True)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(RH)==True)[0]
        RH[index] = RH_new[index]
        RH_flag[index] = RH_new_flag[index]
        if descr_level in RH_attr:
            RH_attr[descr_level] += ", merged with RH calculated from Ah"
        else:
            RH_attr[descr_level] = "Merged with RH calculated from Ah"
        pfp_utils.CreateSeries(ds,"RH",RH,RH_flag,RH_attr)
    else:
        attr = pfp_utils.MakeAttributeDictionary(long_name='Relative humidity',units='%',standard_name='relative_humidity')
        attr[descr_level] = "Relative humidity calculated from Ah and Ta"
        attr["group_name"] = "meteorology"
        pfp_utils.CreateSeries(ds,"RH",RH_new,RH_new_flag,attr)

def smooth(x,window_len=11,window='hanning'):
    """
    Purpose:
        Smooth the data using a window with requested size.
        This method is based on the convolution of a scaled window with the signal.
        The signal is prepared by introducing reflected copies of the signal
        (with the window size) in both ends so that transient parts are minimized
        in the begining and end part of the output signal.
    Input:
        x: the input signal
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.
    Output:
        the smoothed signal
    Example:
        t=linspace(-2,2,0.1)
        x=sin(t)+randn(len(t))*0.1
        y=smooth(x)
    See also:
        numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
        scipy.signal.lfilter
    TODO: the window parameter could be the window itself if an array instead of a string
    Note:
        1) length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
        2) odd values for window_len return output with different length from input
    Source:
        Lifted from scipy Cookbook (http://wiki.scipy.org/Cookbook/SignalSmooth)
    """
    if x.ndim != 1:
        raise ValueError, "smooth only accepts 1 dimension arrays."
    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."
    if window_len<3:
        return x
    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"
    s=numpy.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    if window == 'flat': #moving average
        w=numpy.ones(window_len,'d')
    else:
        w=eval('numpy.'+window+'(window_len)')
    y=numpy.convolve(w/w.sum(),s,mode='valid')
#    return y
    return y[(window_len/2-1):-(window_len/2)]

def SpecificHumidityFromAh(ds):
    """ Calculate specific humidity from absolute humidity. """
    logger.info(' Calculating specific humidity from absolute humidity')
    descr_level = "description_" + ds.globalattributes["nc_level"]
    Ta,Ta_flag,a = pfp_utils.GetSeriesasMA(ds,"Ta")
    ps,ps_flag,a = pfp_utils.GetSeriesasMA(ds,"ps")
    Ah,Ah_flag,a = pfp_utils.GetSeriesasMA(ds,"Ah")
    q_new_flag = pfp_utils.MergeQCFlag([Ta_flag,ps_flag,Ah_flag])
    RH = pfp_mf.RHfromabsolutehumidity(Ah,Ta)
    q_new = pfp_mf.specifichumidityfromRH(RH, Ta, ps)
    if "SH" in ds.series.keys():
        q, q_flag, q_attr = pfp_utils.GetSeriesasMA(ds, "SH")
        index = numpy.where(numpy.ma.getmaskarray(q)==True)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(q)==True)[0]
        q[index] = q_new[index]
        q_flag[index] = q_new_flag[index]
        if descr_level in q_attr:
            q_attr[descr_level] += ", merged with q calculated from Ah"
        else:
            q_attr[descr_level] = "Merged with q calculated from Ah"
        pfp_utils.CreateSeries(ds, "SH", q, q_flag, q_attr)
    else:
        attr = pfp_utils.MakeAttributeDictionary(long_name='Specific humidity',units='kg/kg',standard_name='specific_humidity')
        attr[descr_level] = "Specific humidity calculated from Ah, Ta and ps"
        attr["group_name"] = "meteorology"
        pfp_utils.CreateSeries(ds, "SH", q_new, q_new_flag, attr)

def SpecificHumidityFromRH(ds):
    """ Calculate specific humidity from relative humidity."""
    logger.info(' Calculating specific humidity from relative humidity')
    descr_level = "description_" + ds.globalattributes["nc_level"]
    Ta,Ta_flag,a = pfp_utils.GetSeriesasMA(ds,"Ta")
    ps,ps_flag,a = pfp_utils.GetSeriesasMA(ds,"ps")
    RH,RH_flag,a = pfp_utils.GetSeriesasMA(ds,"RH")
    q_new_flag = pfp_utils.MergeQCFlag([Ta_flag,ps_flag,RH_flag])
    q_new = pfp_mf.specifichumidityfromRH(RH,Ta,ps)   # specific humidity in units of kg/kg
    if "SH" in ds.series.keys():
        q, q_flag, q_attr = pfp_utils.GetSeriesasMA(ds, "SH")
        index = numpy.where(numpy.ma.getmaskarray(q)==True)[0]
        #index = numpy.ma.where(numpy.ma.getmaskarray(q)==True)[0]
        q[index] = q_new[index]
        q_flag[index] = q_new_flag[index]
        if descr_level in q_attr:
            q_attr[descr_level] += ", merged with q calculated from RH"
        else:
            q_attr[descr_level] = "Merged with q calculated from RH"
        pfp_utils.CreateSeries(ds, "SH", q, q_flag, q_attr)
    else:
        attr = pfp_utils.MakeAttributeDictionary(long_name='Specific humidity',units='kg/kg',standard_name='specific_humidity')
        attr[descr_level] = "Specific humidity calculated from Ah, Ta and ps"
        attr["group_name"] = "meteorology"
        pfp_utils.CreateSeries(ds, "SH", q_new, q_new_flag, attr)

def CalculateMeteorologicalVariables(ds, info, Ta_name='Ta', Tv_name='Tv_SONIC_Av',
                                     ps_name='ps', q_name="SH", Ah_name='Ah', RH_name='RH'):
    """
        Add time series of meteorological variables based on fundamental
        relationships (Stull 1988)

        Usage pfp_ts.CalculateMeteorologicalVariables(ds,Ta_name,Tv_name,ps_name,q_name,Ah_name,RH_name)
        ds: data structure
        Ta_name: data series name for air temperature
        Tv_name: data series name for sonic virtual air temperature
        ps_name: data series name for pressure
        Ah_name: data series name for absolute humidity
        q_name : data series name for specific humidity
        RH_name: data series for relative humidity

        Variables added:
            rhom: density of moist air, pfp_mf.densitymoistair(Ta,ps,Ah)
            Lv: latent heat of vapourisation, pfp_mf.Lv(Ta)
            q: specific humidity, pfp_mf.specifichumidity(mr)
                where mr (mixing ratio) = pfp_mf.mixingratio(ps,vp)
            Cpm: specific heat of moist air, pfp_mf.specificheatmoistair(q)
            VPD: vapour pressure deficit, VPD = esat - e
        """
    iris = info["RemoveIntermediateSeries"]
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    for item in [Ta_name,ps_name,Ah_name,q_name]:
        if item not in ds.series.keys():
            msg = " CalculateMeteorologicalVariables: series "
            msg = msg + item + " not found, returning ..."
            logger.warning(msg)
            return
    logger.info(' Adding standard met variables to database')
    descr_level = "description_" + ds.globalattributes["nc_level"]
    # get the required data series
    Ta,f,a = pfp_utils.GetSeriesasMA(ds,Ta_name)
    # deal with possible aliases for the sonic temperature for the time being
    if Tv_name not in ds.series.keys():
        if "Tv_CSAT_Av" in ds.series.keys():
            Tv_name = "Tv_CSAT_Av"
        elif "Tv_CSAT" in ds.series.keys():
            Tv_name = "Tv_CSAT"
        else:
            Tv_name = Ta_name   # use Tv_CSAT if it is in the data structure, otherwise use Ta

    Tv,f,a = pfp_utils.GetSeriesasMA(ds,Tv_name)
    ps,f,a = pfp_utils.GetSeriesasMA(ds,ps_name)
    Ah,f,a = pfp_utils.GetSeriesasMA(ds,Ah_name)
    q,f,a = pfp_utils.GetSeriesasMA(ds,q_name)
    # do the calculations
    vp = pfp_mf.vapourpressure(Ah, Ta)                # vapour pressure from absolute humidity and temperature
    vpsat = pfp_mf.es(Ta)                             # saturation vapour pressure
    rhod = pfp_mf.densitydryair(Ta, ps, vp)           # partial density of dry air
    rhom = pfp_mf.densitymoistair(Ta, ps, vp)         # density of moist air
    rhow = pfp_mf.densitywatervapour(Ta, vp)          # partial density of water vapour
    Lv = pfp_mf.Lv(Ta)                                # latent heat of vapourisation
    mr = pfp_mf.mixingratio(ps, vp)                   # mixing ratio
    mrsat = pfp_mf.mixingratio(ps, vpsat)             # saturation mixing ratio
    qsat = pfp_mf.specifichumidity(mrsat)             # saturation specific humidity from saturation mixing ratio
    Cpd = pfp_mf.specificheatcapacitydryair(Tv)
    Cpw = pfp_mf.specificheatcapacitywatervapour(Ta,Ah)
    RhoCp = pfp_mf.densitytimesspecificheat(rhow,Cpw,rhod,Cpd)
    Cpm = pfp_mf.specificheatmoistair(q)              # specific heat of moist air
    VPD = vpsat - vp                                  # vapour pressure deficit
    SHD = qsat - q                                # specific humidity deficit
    h2o = pfp_mf.h2o_mmolpmolfromgpm3(Ah,Ta,ps)
    # write the meteorological series to the data structure
    attr = pfp_utils.MakeAttributeDictionary(long_name='Vapour pressure',units='kPa',standard_name='water_vapor_partial_pressure_in_air')
    attr["group_name"] = "meteorology"
    attr[descr_level] = "Vapour pressure calculated from Ah, Ta and ps"
    flag = numpy.where(numpy.ma.getmaskarray(vp) == True, ones, zeros)
    pfp_utils.CreateSeries(ds, 'VP', vp, flag, attr)

    attr = pfp_utils.MakeAttributeDictionary(long_name='Saturation vapour pressure',units='kPa')
    flag = numpy.where(numpy.ma.getmaskarray(vpsat) == True, ones, zeros)
    pfp_utils.CreateSeries(ds, 'VPsat', vpsat, flag, attr)
    iris["not_output"].append("VPsat")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Density of dry air',units='kg/m3')
    flag = numpy.where(numpy.ma.getmaskarray(rhod)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'rhod',rhod,flag,attr)
    iris["not_output"].append("rhod")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Density of moist air',units='kg/m3',standard_name='air_density')
    flag = numpy.where(numpy.ma.getmaskarray(rhom)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'rhom',rhom,flag,attr)
    iris["not_output"].append("rhom")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Partial density of water vapour',units='kg/m3')
    flag = numpy.where(numpy.ma.getmaskarray(rhow)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'rhow',rhow,flag,attr)
    iris["not_output"].append("rhow")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Latent heat of vapourisation',units='J/kg')
    flag = numpy.where(numpy.ma.getmaskarray(Lv)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'Lv',Lv,flag,attr)
    iris["not_output"].append("Lv")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Specific heat capacity of dry air',units='J/kg-K')
    flag = numpy.where(numpy.ma.getmaskarray(Cpd)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'Cpd',Cpd,flag,attr)
    iris["not_output"].append("Cpd")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Specific heat capacity of water vapour',units='J/kg-K')
    flag = numpy.where(numpy.ma.getmaskarray(Cpw)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'Cpw',Cpw,flag,attr)
    iris["not_output"].append("Cpw")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Specific heat capacity of moist air',units='J/kg-K')
    flag = numpy.where(numpy.ma.getmaskarray(Cpm)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'Cpm',Cpm,flag,attr)
    iris["not_output"].append("Cpm")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Product of air density and specific heat capacity',units='J/m3-K')
    flag = numpy.where(numpy.ma.getmaskarray(RhoCp)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'RhoCp',RhoCp,flag,attr)
    iris["not_output"].append("RhoCp")

    attr = pfp_utils.MakeAttributeDictionary(long_name='Vapour pressure deficit',units='kPa',standard_name='water_vapor_saturation_deficit_in_air')
    attr["group_name"] = "meteorology"
    attr[descr_level] = "Vapour pressure deficit calculated from Ah, Ta and ps"
    flag = numpy.where(numpy.ma.getmaskarray(VPD)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'VPD',VPD,flag,attr)

    attr = pfp_utils.MakeAttributeDictionary(long_name='Specific humidity deficit',units='kg/kg')
    attr["group_name"] = "meteorology"
    attr[descr_level] = "Specific humidity deficit calculated from SH, Ta and ps"
    flag = numpy.where(numpy.ma.getmaskarray(SHD)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'SHD',SHD,flag,attr)

    attr = pfp_utils.MakeAttributeDictionary(long_name='H2O concentration', units='mmol/mol', standard_name='mole_concentration_of_water_vapor_in_air')
    attr["group_name"] = "meteorology"
    attr[descr_level] = "Water vapour mixing ratio calculated from Ah, Ta and ps"
    flag = numpy.where(numpy.ma.getmaskarray(h2o)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,'H2O',h2o,flag,attr)

def CalculateMoninObukhovLength(ds):
    """
    Purpose:
     Calculate the Monin Obukhov length.
    Usage:
     pfp_ts.CalculateMoninObukhovLength(ds)
     where ds is a data structure
    Side effects:
     Creates a new series in the data structure containing the Monin-Obukhov length.
    Author: PRI
    Date: April 2018
    """
    logger.info(' Calculating Monin-Obukhov length')
    # create a variable dictionary for L
    nrecs = int(ds.globalattributes["nc_nrecs"])
    ldt = pfp_utils.GetVariable(ds, "DateTime")
    L = pfp_utils.CreateEmptyVariable("L", nrecs, datetime=ldt["Data"])
    # create QC flags
    zeros = numpy.zeros(nrecs, dtype=numpy.int32)
    ones = numpy.ones(nrecs, dtype=numpy.int32)
    # get the required meteorological variables
    Ta = pfp_utils.GetVariable(ds, "Ta")
    ps = pfp_utils.GetVariable(ds, "ps")
    vp = pfp_utils.GetVariable(ds, "VP")
    # get the required fluxes
    ustar = pfp_utils.GetVariable(ds, "ustar")
    Fh = pfp_utils.GetVariable(ds, "Fh")
    # calculate the density of dry air
    rho_dry = pfp_mf.densitydryair(Ta["Data"], ps["Data"], vp["Data"])
    # calculate virtual potential temperature
    Tp = pfp_mf.theta(Ta["Data"], ps["Data"])
    mr = pfp_mf.mixingratio(ps["Data"], vp["Data"])
    Tvp = pfp_mf.virtualtheta(Tp, mr)
    L["Data"] = -Tvp*rho_dry*c.Cp*(ustar["Data"]**3)/(c.g*c.k*Fh["Data"])
    # get the QC flag
    L["Flag"] = numpy.where(numpy.ma.getmaskarray(L["Data"]) == True, ones, zeros)
    # update the variable attributes
    L["Attr"]["units"] = "m"
    L["Attr"]["long_name"] = "Monin-Obukhov length"
    L["Attr"]["standard_name"] = "not defined"
    # put the Monin-Obukhov variable in the data structure
    pfp_utils.CreateVariable(ds, L)
    return

def CalculateNetRadiation(cf,ds,Fn_out='Fn_4cmpt',Fsd_in='Fsd',Fsu_in='Fsu',Fld_in='Fld',Flu_in='Flu'):
    """
    Purpose:
     Calculate the net radiation from the 4 components of the surface
     radiation budget.
    Usage:
     pfp_ts.CalculateNetRadiation(cf,ds,Fn_out,Fsd_in,Fsu_in,Fld_in,Flu_in)
        cf: control file
        ds: data structure
        Fn_out: output net radiation variable to ds.  Example: 'Fn_KZ'
        Fsd_in: input downwelling solar radiation in ds.  Example: 'Fsd'
        Fsu_in: input upwelling solar radiation in ds.  Example: 'Fsu'
        Fld_in: input downwelling longwave radiation in ds.  Example: 'Fld'
        Flu_in: input upwelling longwave radiation in ds.  Example: 'Flu'
    Side effects:
     Creates a new series in the data structure containing the net radiation.
    Author: PRI
    Date: Sometime early on
    """
    logger.info(' Calculating net radiation from 4 components')
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    if Fsd_in in ds.series.keys() and Fsu_in in ds.series.keys() and Fld_in in ds.series.keys() and Flu_in in ds.series.keys():
        Fsd,f,a = pfp_utils.GetSeriesasMA(ds,Fsd_in)
        Fsu,f,a = pfp_utils.GetSeriesasMA(ds,Fsu_in)
        Fld,f,a = pfp_utils.GetSeriesasMA(ds,Fld_in)
        Flu,f,a = pfp_utils.GetSeriesasMA(ds,Flu_in)
        Fn_calc = (Fsd - Fsu) + (Fld - Flu)
        if Fn_out not in ds.series.keys():
            attr = pfp_utils.MakeAttributeDictionary(long_name='Calculated net radiation using '+Fsd_in+','+Fsu_in+','+Fld_in+','+Flu_in,
                                 standard_name='surface_net_downwawrd_radiative_flux',units='W/m2')
            flag = numpy.where(numpy.ma.getmaskarray(Fn_calc)==True,ones,zeros)
            pfp_utils.CreateSeries(ds,Fn_out,Fn_calc,flag,attr)
        else:
            Fn_exist,flag,attr = pfp_utils.GetSeriesasMA(ds,Fn_out)
            idx = numpy.where((numpy.ma.getmaskarray(Fn_exist)==True)&(numpy.ma.getmaskarray(Fn_calc)==False))[0]
            if len(idx)!=0:
                Fn_exist[idx] = Fn_calc[idx]
                flag[idx] = numpy.int32(20)
            pfp_utils.CreateSeries(ds,Fn_out,Fn_exist,flag,attr)
    else:
        nRecs = int(ds.globalattributes['nc_nrecs'])
        Fn = numpy.array([c.missing_value]*nRecs,dtype=numpy.float64)
        flag = numpy.ones(nRecs,dtype=numpy.int32)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Calculated net radiation (one or more components missing)',
                             standard_name='surface_net_downwawrd_radiative_flux',units='W/m2')
        pfp_utils.CreateSeries(ds,Fn_out,Fn,flag,attr)

def CheckCovarianceUnits(ds):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: September 2015
    """
    logger.info(' Checking covariance units')
    co2_list = ["UxC","UyC","UzC"]
    h2o_list = ["UxA","UyA","UzA","UxH","UyH","UzH"]
    for item in co2_list:
        if item not in ds.series.keys(): continue
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,item)
        if "umol" in attr["units"]:
            Ta,f,a = pfp_utils.GetSeriesasMA(ds,"Ta")
            ps,f,a = pfp_utils.GetSeriesasMA(ds,"ps")
            data = pfp_mf.co2_mgCO2pm3fromppm(data,Ta,ps)
            attr["units"] = "mg/m2/s"
            pfp_utils.CreateSeries(ds,item,data,flag,attr)
    for item in h2o_list:
        if item not in ds.series.keys(): continue
        data,flag,attr = pfp_utils.GetSeriesasMA(ds,item)
        if "mmol" in attr["units"]:
            Ta,f,a = pfp_utils.GetSeriesasMA(ds,"Ta")
            ps,f,a = pfp_utils.GetSeriesasMA(ds,"ps")
            data = pfp_mf.h2o_gpm3frommmolpmol(data,Ta,ps)
            attr["units"] = "g/m2/s"
            if "H" in item: item = item.replace("H","A")
            pfp_utils.CreateSeries(ds,item,data,flag,attr)

def CombineSeries(cf, ds, label, convert_units=False, save_originals=False):
    """
    Purpose:
     Combine two variables by merging or element-wise averaging.
     This is a wrapper that decides whether to merge or average 2 variables
     based on the key specified in the control file.
    Usage:
     pfp_ts.CombineSeries(cf, ds, label, convert_units=False, save_originals=False)
     where cf is a cotrol file
           ds is a data structure
           label is the label of the output (merged or averaged) variable
           convert_units=True if you want to check all variables have the same units
                              before merging or averaging
           save_originals=True if you want to save the orginal series if the output
                               label is the same as an input variable
    Side effects:
    Author: PRI
    Date: October 2019
    """
    if label not in cf["Variables"]:
        msg = " CombineSeries: Variable " + label + " not found in control file"
        msg += ", skipping ..."
        logger.warning(msg)
        return
    if "MergeSeries" in cf["Variables"][label]:
        MergeSeries(cf, ds, label, convert_units=convert_units, save_originals=save_originals)
    elif "AverageSeries" in cf["Variables"][label]:
        AverageSeriesByElements(cf, ds, label)
    else:
        msg = " CombineSeries: Neither MergeSeries nor AverageSeries "
        msg += " option given for variable " + label
        msg += ", skipping ..."
        logger.warning(msg)
    return

def CoordRotation2D(cf, ds):
    """
        2D coordinate rotation to force v = w = 0.  Based on Lee et al, Chapter
        3 of Handbook of Micrometeorology.  This routine does not do the third
        rotation to force v'w' = 0.

        Usage pfp_ts.CoordRotation2D(ds)
        ds: data structure
        """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    # get the raw wind velocity components
    Ux = pfp_utils.GetVariable(ds, "Ux")          # longitudinal component in CSAT coordinate system
    Uy = pfp_utils.GetVariable(ds, "Uy")          # lateral component in CSAT coordinate system
    Uz = pfp_utils.GetVariable(ds, "Uz")          # vertical component in CSAT coordinate system
    # get the raw covariances
    UxUz = pfp_utils.GetVariable(ds, "UxUz")      # covariance(Ux,Uz)
    UyUz = pfp_utils.GetVariable(ds, "UyUz")      # covariance(Uy,Uz)
    UxUy = pfp_utils.GetVariable(ds, "UxUy")      # covariance(Ux,Uy)
    UyUy = pfp_utils.GetVariable(ds, "UyUy")      # variance(Uy)
    UxUx = pfp_utils.GetVariable(ds, "UxUx")      # variance(Ux)
    UzUz = pfp_utils.GetVariable(ds, "UzUz")      # variance(Ux)
    UzC = pfp_utils.GetVariable(ds, "UzC")        # covariance(Uz,C)
    UzA = pfp_utils.GetVariable(ds, "UzA")        # covariance(Uz,A)
    UzT = pfp_utils.GetVariable(ds, "UzT")        # covariance(Uz,T)
    UxC = pfp_utils.GetVariable(ds, "UxC")        # covariance(Ux,C)
    UyC = pfp_utils.GetVariable(ds, "UyC")        # covariance(Uy,C)
    UxA = pfp_utils.GetVariable(ds, "UxA")        # covariance(Ux,A)
    UyA = pfp_utils.GetVariable(ds, "UyA")        # covariance(Ux,A)
    UxT = pfp_utils.GetVariable(ds, "UxT")        # covariance(Ux,T)
    UyT = pfp_utils.GetVariable(ds, "UyT")        # covariance(Uy,T)
    # apply 2D coordinate rotation unless otherwise specified in control file
    rotate = True
    if ("Options" in cf) and ("2DCoordRotation" in cf["Options"].keys()):
        if not cf["Options"].as_bool("2DCoordRotation"):
            rotate = False
    if rotate:
        logger.info(" Applying 2D coordinate rotation (components and covariances)")
        # get the 2D and 3D wind speeds
        ws2d = numpy.ma.sqrt(Ux["Data"]**2 + Uy["Data"]**2)
        ws3d = numpy.ma.sqrt(Ux["Data"]**2 + Uy["Data"]**2 + Uz["Data"]**2)
        # get the sine and cosine of the angles through which to rotate
        #  - first we rotate about the Uz axis by eta to get v = 0
        #  - then we rotate about the v axis by theta to get w = 0
        ce = Ux["Data"]/ws2d          # cos(eta)
        se = Uy["Data"]/ws2d          # sin(eta)
        ct = ws2d/ws3d                # cos(theta)
        st = Uz["Data"]/ws3d          # sin(theta)
        # get the rotation angles
        theta = numpy.rad2deg(numpy.arctan2(st, ct))
        eta = numpy.rad2deg(numpy.arctan2(se, ce))
        # do the wind velocity components first
        u = Ux["Data"]*ct*ce + Uy["Data"]*ct*se + Uz["Data"]*st   # longitudinal component in natural wind coordinates
        v = Uy["Data"]*ce - Ux["Data"]*se                         # lateral component in natural wind coordinates
        w = Uz["Data"]*ct - Ux["Data"]*st*ce - Uy["Data"]*st*se   # vertical component in natural wind coordinates
        # do the variances
        uu = UxUx["Data"]*ct**2*ce**2 + UyUy["Data"]*ct**2*se**2 + UzUz["Data"]*st**2 + \
            2*UxUy["Data"]*ct**2*ce*se + 2*UxUz["Data"]*ct*st*ce + 2*UyUz["Data"]*ct*st*se
        vv = UyUy["Data"]*ce**2 + UxUx["Data"]*se**2 - 2*UxUy["Data"]*ce*se
        ww = UzUz["Data"]*ct**2 + UxUx["Data"]*st**2*ce**2 + UyUy["Data"]*st**2*se**2 - \
            2*UxUz["Data"]*ct*st*ce - 2*UyUz["Data"]*ct*st*se + 2*UxUy["Data"]*st**2*ce*se
        # now do the scalar covariances
        wT = UzT["Data"]*ct - UxT["Data"]*st*ce - UyT["Data"]*st*se       # covariance(w,T) in natural wind coordinate system
        wA = UzA["Data"]*ct - UxA["Data"]*st*ce - UyA["Data"]*st*se       # covariance(w,A) in natural wind coordinate system
        wC = UzC["Data"]*ct - UxC["Data"]*st*ce - UyC["Data"]*st*se       # covariance(w,C) in natural wind coordinate system
        # now do the momentum covariances
        # full equations, Wesely PhD thesis via James Cleverly and EddyPro
        # covariance(w,x) in natural wind coordinate system
        uw = UxUz["Data"]*ce*(ct*ct-st*st) - 2*UxUy["Data"]*ct*st*ce*se + \
            UyUz["Data"]*se*(ct*ct-st*st) - UxUx["Data"]*ct*st*ce*ce - \
            UyUy["Data"]*ct*st*se*se + UzUz["Data"]*ct*st
        # covariance(x,y) in natural wind coordinate system
        uv = UxUy["Data"]*ct*(ce*ce-se*se) + UyUz["Data"]*st*ce - \
            UxUz["Data"]*st*se - UxUx["Data"]*ct*ce*se + UyUy["Data"]*ct*ce*se
        # covariance(w,y) in natural wind coordinate system
        vw = UyUz["Data"]*ct*ce - UxUz["Data"]*ct*se - UxUy["Data"]*st*(ce*ce-se*se) + \
             UxUx["Data"]*st*ce*se - UyUy["Data"]*st*ce*se
    else:
        logger.info(" 2D coordinate rotation disabled, using unrotated components and covariances")
        # dummy series for rotation angles
        theta = numpy.zeros(nRecs)
        eta = numpy.zeros(nRecs)
        # unrotated wind components
        u = Ux["Data"]           # unrotated x xomponent
        v = Uy["Data"]           # unrotated y xomponent
        w = Uz["Data"]           # unrotated z xomponent
        # unrotated covariances
        wT = UzT["Data"]       # unrotated  wT covariance
        wA = UzA["Data"]       # unrotated  wA covariance
        wC = UzC["Data"]       # unrotated  wC covariance
        uw = UxUz["Data"]      # unrotated  uw covariance
        vw = UyUz["Data"]      # unrotated  vw covariance
        uv = UxUy["Data"]      # unrotated  uv covariance
        # unrotated variances
        uu = UxUx["Data"]      # unrotated  u variance
        vv = UyUy["Data"]      # unrotated  v variance
        ww = UzUz["Data"]      # unrotated  w variance
    # store the rotated quantities in the data structure
    attr = pfp_utils.MakeAttributeDictionary(long_name="Horizontal rotation angle",
                                             units="deg", height=Uz["Attr"]["height"])
    flag = numpy.where(numpy.ma.getmaskarray(eta) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "eta", "Data": eta, "Flag": flag, "Attr": attr})

    attr = pfp_utils.MakeAttributeDictionary(long_name="Vertical rotation angle",
                                             units="deg", height=Uz["Attr"]["height"])
    flag = numpy.where(numpy.ma.getmaskarray(theta) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "theta", "Data": theta, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(Ux["Attr"])
    attr["long_name"] = "Longitudinal component of wind-speed in natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(u) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "U_SONIC_Av", "Data": u, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(Uy["Attr"])
    attr["long_name"] = "Lateral component of wind-speed in natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(v) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "V_SONIC_Av", "Data": v, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(Uz["Attr"])
    attr["long_name"] = "Vertical component of wind-speed in natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(w) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "W_SONIC_Av", "Data": w, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UzT["Attr"])
    attr["long_name"] = "Kinematic heat flux, rotated to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(wT) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "wT", "Data": wT, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UzA["Attr"])
    attr["long_name"] = "Kinematic vapour flux, rotated to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(wA) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "wA", "Data": wA, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UzC["Attr"])
    attr["long_name"] = "Kinematic CO2 flux, rotated to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(wC) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "wC", "Data": wC, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UxUz["Attr"])
    attr["long_name"] = "Momentum flux X component, corrected to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(uw) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "uw", "Data": uw, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UxUy["Attr"])
    attr["long_name"] = "Horizontal streamwise-crosswind covariance, rotated to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(uv) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "uv", "Data": uv, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UyUz["Attr"])
    attr["long_name"] = "Momentum flux Y component, corrected to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(vw) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "vw", "Data": vw, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UxUx["Attr"])
    attr["long_name"] = "Variance of streamwise windspeed, rotated to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(uu) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "U_SONIC_Vr", "Data": uu, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UyUy["Attr"])
    attr["long_name"] = "Variance of crossstream windspeed, rotated to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(vv) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "V_SONIC_Vr", "Data": vv, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(UzUz["Attr"])
    attr["long_name"] = "Variance of vertical windspeed, rotated to natural wind coordinates"
    flag = numpy.where(numpy.ma.getmaskarray(ww) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "W_SONIC_Vr", "Data": ww, "Flag": flag, "Attr": attr})

    if pfp_utils.get_optionskeyaslogical(cf, "RelaxRotation"):
        RotatedSeriesList = ['wT', 'wA', 'wC', 'uw', 'vw']
        NonRotatedSeriesList = ['UzT', 'UzA', 'UzC', 'UxUz', 'UyUz']
        for ThisOne, ThatOne in zip(RotatedSeriesList, NonRotatedSeriesList):
            ReplaceWhereMissing(ds.series[ThisOne], ds.series[ThisOne], ds.series[ThatOne], FlagValue=21)

def CalculateComponentsFromWsWd(ds):
    """
    Purpose:
     Calculate U (positive east) and V (positive north) from wind speed and direction and
     put the components into the data structure.
    Usage:
     pfp_ts.CalculateComponentsFromWsWd(ds)
    Author: PRI/WW/MK/EvG
    Date: July 2016
    """
    Wd = pfp_utils.GetVariable(ds, "Wd")
    Ws = pfp_utils.GetVariable(ds, "Ws")
    u, v = pfp_utils.convert_WSWDtoUV(Ws, Wd)
    pfp_utils.CreateVariable(ds, u)
    pfp_utils.CreateVariable(ds, v)

def CalculateFcStorageSinglePoint(cf, ds, Fc_out="Fc_single", CO2_in="CO2"):
    """
    Calculate CO2 flux storage term in the air column beneath the CO2 instrument.  This
    routine assumes the air column between the sensor and the surface is well mixed.

    Usage pfp_ts.CalculateFcStorageSinglePoint(cf, ds, Fc_out='Fc_single', CO2_in='CO2')
    cf: control file object
    ds: data structure
    Fc_out: series label of the CO2 flux storage term
    CO2_in: series label of the CO2 concentration

    Parameters loaded from control file:
        zms: measurement height from surface, m
    """
    if Fc_out not in ds.series.keys():
        logger.info(" Calculating Fc storage (single height)")
        nRecs = int(ds.globalattributes["nc_nrecs"])
        zeros = numpy.zeros(nRecs, dtype=numpy.int32)
        ones = numpy.ones(nRecs, dtype=numpy.int32)
        ts = int(ds.globalattributes["time_step"])
        level = str(ds.globalattributes["nc_level"])
        descr = "description_" + level
        # create an empty output variable
        ldt = pfp_utils.GetVariable(ds, "DateTime")
        Fc_single = pfp_utils.CreateEmptyVariable(Fc_out, nRecs, datetime=ldt["Data"])
        # get the input data
        if CO2_in not in ds.series.keys():
            if "Cc" in ds.series.keys():
                CO2_in = "Cc"
            else:
                msg = "  Neither CO2 nor Cc not in data structure, storage not calculated"
                logger.error(msg)
                pfp_utils.CreateVariable(ds, Fc_single)
                return
        CO2 = pfp_utils.GetVariable(ds, CO2_in)
        Fc = pfp_utils.GetVariable(ds, "Fc")
        Ta = pfp_utils.GetVariable(ds, "Ta")
        ps = pfp_utils.GetVariable(ds, "ps")
        # try to get a value for zms, the instrument height above ground
        got_zms = False
        if "height" in CO2["Attr"] and not got_zms:
            try:
                zms = float(pfp_utils.strip_non_numeric(CO2["Attr"]["height"]))
                got_zms = True
            except:
                pass
        if "height" in Fc["Attr"] and not got_zms:
            try:
                zms = float(pfp_utils.strip_non_numeric(Fc["Attr"]["height"]))
                got_zms = True
            except:
                pass
        if "tower_height" in ds.globalattributes.keys() and not got_zms:
            try:
                zms = float(pfp_utils.strip_non_numeric(ds.globalattributes["tower_height"]))
                got_zms = True
            except:
                pass
        if pfp_utils.cfkeycheck(cf, Base="General", ThisOne="zms") and not got_zms:
            try:
                zms = float(pfp_utils.strip_non_numeric(cf["General"]["zms"]))
                got_zms = True
            except:
                pass
        if pfp_utils.cfkeycheck(cf, Base="Options", ThisOne="zms") and not got_zms:
            try:
                zms = float(pfp_utils.strip_non_numeric(cf["Options"]["zms"]))
                got_zms = True
            except:
                pass
        if got_zms:
            # check the CO2 concentration units
            # if the units are mg/m3, convert CO2 concentration to umol/mol before taking the difference
            pfp_utils.convert_units_co2(ds, CO2, "umol/mol")
            # calculate the change in CO2 concentration between time steps
            # CO2 concentration assumed to be in umol/mol
            dc = numpy.ma.ediff1d(CO2["Data"], to_begin=0)
            # convert the CO2 concentration difference from umol/mol to umol/m3
            dc = pfp_mf.co2_umolpm3fromppm(dc, Ta["Data"], ps["Data"])
            # calculate the time step in seconds
            epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
            seconds = numpy.array([(dt-epoch).total_seconds() for dt in ldt["Data"]])
            dt = numpy.ediff1d(seconds, to_begin=float(ts)*60)
            # calculate the CO2 flux based on storage below the measurement height
            Fc_single["Data"] = zms*dc/dt
            # do the attributes
            Fc_single["Attr"] = {}
            for attr in ["height", "instrument", "serial_number"]:
                if attr in CO2["Attr"]:
                    Fc_single["Attr"][attr] = CO2["Attr"][attr]
            Fc_single["Attr"]["units"] = "umol/m2/s"
            Fc_single["Attr"]["standard_name"] = "not defined"
            Fc_single["Attr"]["long_name"] = "CO2 flux (storage term)"
            Fc_single["Attr"]["group_name"] = "flux"
            Fc_single["Attr"][descr] = "Fc storage component calcuated using single point \
                                        CO2 measurement"
            # put the storage flux in the data structure
            mask = numpy.ma.getmaskarray(Fc_single["Data"])
            Fc_single["Flag"] = numpy.where(mask == True, ones, zeros)
            # match the units of Fc_single to the units of Fc
            pfp_utils.convert_units_co2(ds, Fc_single, Fc["Attr"]["units"])
        else:
            msg = "  Measurement height not found, storage not calculated"
            logger.error(msg)
        pfp_utils.CreateVariable(ds, Fc_single)
    else:
        msg = "  " + Fc_out + " found in data structure, not calculated"
        logger.info(msg)
    return

def CorrectFcForStorage(cf,ds,Fc_out='Fc',Fc_in='Fc',Fc_storage_in='Fc_single'):
    """
    Correct CO2 flux for storage in the air column beneath the CO2 instrument.

    Usage pfp_ts.CorrectFcForStorage(cf,ds,Fc_out,Fc_in,Fc_storage_in)
    cf: control file object
    ds: data structure
    Fc_out: series label of the corrected CO2 flux
    Fc_in: series label of the input CO2 flux
    Fc_storage: series label of the CO2 flux storage term

    """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    # check to see if applying the Fc storage term has been requested for any
    # individual variables
    apply_storage = {}
    for label in cf["Variables"].keys():
        if "ApplyFcStorage" in cf["Variables"][label]:
            source = str(cf["Variables"][label]["ApplyFcStorage"]["source"])
            apply_storage[label] = source
    # if no individual series have been specified, do the default
    if len(apply_storage.keys()) == 0:
        # check to see if correction for storage has been requested in [Options]
        if not pfp_utils.get_optionskeyaslogical(cf, "ApplyFcStorage"):
            return
        # check to see if we have the required data series
        if (Fc_in not in ds.series.keys()) or (Fc_storage_in not in ds.series.keys()):
            msg = "CorrectFcForStorage: Fc or Fc_storage not found, skipping ..."
            logger.warning(msg)
            return
        # check to see if we have an Fc_profile series
        if "Fc_profile" in ds.series.keys():
            Fc_storage_in = "Fc_profile"
        elif "Fc_storage" in ds.series.keys():
            Fc_storage_in = "Fc_storage"
        logger.info(" ***!!! Applying Fc storage term !!!***")
        Fc_raw,Fc_flag,Fc_attr = pfp_utils.GetSeriesasMA(ds,Fc_in)
        Fc_storage,Fc_storage_flag,Fc_storage_attr = pfp_utils.GetSeriesasMA(ds,Fc_storage_in)
        if Fc_attr["units"]!=Fc_storage_attr["units"]:
            logger.error("CorrectFcForStorage: units of Fc do not match those of storage term, storage not applied")
            return
        Fc = Fc_raw + Fc_storage
        if pfp_utils.get_optionskeyaslogical(cf, "RelaxFcStorage"):
            idx=numpy.where(numpy.ma.getmaskarray(Fc)==True)[0]
            Fc[idx]=Fc_raw[idx]
            logger.info(" Replaced corrected Fc with "+str(len(idx))+" raw values")
        Fc_attr["long_name"] = Fc_attr["long_name"] + ", uncorrected"
        pfp_utils.CreateSeries(ds,"Fc_raw",Fc_raw,Fc_flag,Fc_attr)
        Fc_attr["long_name"] = Fc_attr["long_name"].replace(", uncorrected",", corrected for storage using supplied storage term")
        flag = numpy.where(numpy.ma.getmaskarray(Fc)==True,ones,zeros)
        pfp_utils.CreateSeries(ds,Fc_out,Fc,flag,Fc_attr)
    else:
        # loop over the series for which apply Fc storage was requested
        for label in apply_storage.keys():
            # check to make sure the requested series is in the data structure
            if label not in ds.series.keys():
                # skip if it isn't
                msg = " Requested series "+label+" not found in data structure"
                logger.error(msg)
                continue
            # get the storage flux label
            source = apply_storage[label]
            if source not in ds.series.keys():
                msg = " Requested series "+source+" not found in data structure"
                logger.error(msg)
                continue
            # get the data
            Fc_un = pfp_utils.GetVariable(ds, label)
            Sc = pfp_utils.GetVariable(ds, source)
            # check the units
            if Fc_un["Attr"]["units"] != Sc["Attr"]["units"]:
                msg = " Units for "+label+" and "+source+" don't match"
                logger.error(msg)
                return
            msg = " *** Applying storage term "+source+" to "+label+" ***"
            logger.info(msg)
            # Make a copy of the uncorrected Fc
            Fc = copy.deepcopy(Fc_un)
            # update the label, the long name and write the uncorrected data to the data structure
            Fc_un["Label"] = Fc_un["Label"]+"_raw"
            Fc_un["Attr"]["long_name"] = Fc_un["Attr"]["long_name"] + ", uncorrected"
            pfp_utils.CreateVariable(ds, Fc_un)
            # correct Fc by adding the storage
            Fc["Data"] = Fc_un["Data"] + Sc["Data"]
            # check to see if the user wants to relax the correct
            if pfp_utils.get_optionskeyaslogical(cf, "RelaxFcStorage"):
                # if so, replace missing corrected Fc with uncorrected Fc
                idx = numpy.where(numpy.ma.getmaskarray(Fc["Data"])==True)[0]
                Fc[idx] = Fc_un[idx]
                logger.info(" Replaced corrected Fc with "+str(len(idx))+" uncorrected values")
            Fc["Flag"] = numpy.where(numpy.ma.getmaskarray(Fc["Data"])==True, ones, zeros)
            Fc["Attr"] = copy.deepcopy(Fc_un["Attr"])
            Fc["Attr"]["long_name"] = Fc["Attr"]["long_name"].replace(", uncorrected",
                                                                      ", corrected for storage using supplied storage term")
            pfp_utils.CreateVariable(ds, Fc)
    return

def CorrectIndividualFgForStorage(cf,ds):
    if pfp_utils.cfkeycheck(cf,Base='FunctionArgs',ThisOne='CFgArgs'):
        List = cf['FunctionArgs']['CFgArgs'].keys()
        for i in range(len(List)):
            CFgArgs = ast.literal_eval(cf['FunctionArgs']['CFgArgs'][str(i)])
            CorrectFgForStorage(cf,ds,Fg_out=CFgArgs[0],Fg_in=CFgArgs[1],Ts_in=CFgArgs[2],Sws_in=CFgArgs[3])
        return

def CorrectFgForStorage(cf,ds,Fg_out='Fg',Fg_in='Fg',Ts_in='Ts',Sws_in='Sws'):
    """
        Correct ground heat flux for storage in the layer above the heat flux plate

        Usage pfp_ts.CorrectFgForStorage(cf,ds,Fg_out,Fg_in,Ts_in,Sws_in)
        ds: data structure
        Fg_out: output soil heat flux variable to ds.  Example: 'Fg'
        Fg_in: input soil heat flux in ds.  Example: 'Fg_Av'
        Ts_in: input soil temperature in ds.  Example: 'Ts'

        Parameters loaded from control file:
            FgDepth: Depth of soil heat flux plates, m
            BulkDensity: soil bulk density, kg/m3
            OrganicContent: soil organic content, fraction
            SwsDefault: default value of soil moisture content used when no sensors present
        """
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    # check to see if the user wants to skip the correction
    if not pfp_utils.get_optionskeyaslogical(cf, "CorrectFgForStorage", default=True):
        logger.info(' CorrectFgForStorage: storage correction disabled in control file')
        return
    # check to see if there is a [Soil] section in the control file
    if 'Soil' not in cf.keys():
        # if there isn't, check to see if the soil information is in the netCDF global attributes
        if "FgDepth" in ds.globalattributes.keys():
            # if it is, read it into the control file object so we can use it later
            cf["Soil"] = {}
            cf["Soil"]["FgDepth"] = ds.globalattributes["FgDepth"]
            cf["Soil"]["BulkDensity"] = ds.globalattributes["BulkDensity"]
            cf["Soil"]["OrganicContent"] = ds.globalattributes["OrganicContent"]
            cf["Soil"]["SwsDefault"] = ds.globalattributes["SwsDefault"]
        else:
            # tell the user if we can't find the information needed
            logger.warning(' CorrectFgForStorage: [Soil] section not found in control file or global attributes, Fg not corrected')
            return
    if Fg_in not in ds.series.keys() or Ts_in not in ds.series.keys():
        logger.warning(' CorrectFgForStorage: '+Fg_in+' or '+Ts_in+' not found in data structure, Fg not corrected')
        return
    logger.info(' Correcting soil heat flux for storage')
    # put the contents of the soil section into the global attributes
    for item in cf["Soil"].keys(): ds.globalattributes[item] = cf["Soil"][item]
    d = max(0.0,min(0.5,float(cf['Soil']['FgDepth'])))
    bd = max(1200.0,min(2500.0,float(cf['Soil']['BulkDensity'])))
    oc = max(0.0,min(1.0,float(cf['Soil']['OrganicContent'])))
    mc = 1.0 - oc
    Sws_default = min(1.0,max(0.0,float(cf['Soil']['SwsDefault'])))
    # get the data
    Fg,Fg_flag,Fg_attr = pfp_utils.GetSeriesasMA(ds,Fg_in)
    Ts,Ts_flag,Ts_attr = pfp_utils.GetSeriesasMA(ds,Ts_in)
    Sws,Sws_flag,Sws_attr = pfp_utils.GetSeriesasMA(ds,Sws_in)
    iom = numpy.where(numpy.mod(Sws_flag,10)!=0)[0]
    if len(iom) != 0:
        msg = "  CorrectFgForStorage: default soil moisture used for "
        msg += str(len(iom)) + " values"
        logger.warning(msg)
        Sws[iom] = Sws_default
    # get the soil temperature difference from time step to time step
    dTs = numpy.ma.zeros(nRecs)
    dTs[1:] = numpy.ma.diff(Ts)
    # set the temporal difference in Ts for the first value of the series to missing value ...
    dTs[0] = numpy.ma.masked
    # write the temperature difference into the data structure so we can use its flag later
    dTs_flag = numpy.zeros(nRecs,dtype=numpy.int32)
    index = numpy.where(numpy.ma.getmaskarray(dTs)==True)[0]
    #index = numpy.ma.where(numpy.ma.getmaskarray(dTs)==True)[0]
    dTs_flag[index] = numpy.int32(1)
    #logger.warning('  Setting first SHFstorage in series to missing value')
    attr = pfp_utils.MakeAttributeDictionary(long_name='Change in soil temperature',units='C')
    pfp_utils.CreateSeries(ds,"dTs",dTs,dTs_flag,attr)
    # get the time difference
    dt = numpy.ma.zeros(nRecs)
    dt[1:] = numpy.diff(date2num(ds.series['DateTime']['Data']))*float(86400)
    dt[0] = dt[1]
    # calculate the specific heat capacity of the soil
    Cs = mc*bd*c.Cd + oc*bd*c.Co + Sws*c.rho_water*c.Cw
    # calculate the soil heat storage
    S = Cs*(dTs/dt)*d
    # apply the storage term
    Fg_out_data = Fg + S
    # work out the QC flag
    #Fg_out_flag = numpy.zeros(nRecs,dtype=numpy.int32)
    #for item in [Fg_flag,Ts_flag,Sws_flag]:
        #Fg_out_flag = numpy.maximum(Fg_out_flag,item)
    ## trap and re-instate flag values of 1 (data missing at L1)
    #for item in [Fg_flag,Ts_flag,Sws_flag]:
        #index = numpy.where(item==numpy.int32(1))[0]
        #Fg_out_flag[index] = numpy.int32(1)
    # put the corrected soil heat flux into the data structure
    attr= pfp_utils.MakeAttributeDictionary(long_name='Soil heat flux corrected for storage',units='W/m2',standard_name='downward_heat_flux_in_soil')
    flag = numpy.where(numpy.ma.getmaskarray(Fg_out_data)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,Fg_out,Fg_out_data,flag,attr)
    # save the input (uncorrected) soil heat flux series, this will be used if the correction is relaxed
    attr = pfp_utils.MakeAttributeDictionary(long_name='Soil heat flux uncorrected for storage',units='W/m2')
    pfp_utils.CreateSeries(ds,'Fg_Av',Fg,Fg_flag,attr)
    flag = numpy.where(numpy.ma.getmaskarray(S)==True,ones,zeros)
    attr = pfp_utils.MakeAttributeDictionary(long_name='Soil heat flux storage',units='W/m2')
    pfp_utils.CreateSeries(ds,'S',S,flag,attr)
    flag = numpy.where(numpy.ma.getmaskarray(Cs)==True,ones,zeros)
    attr = pfp_utils.MakeAttributeDictionary(long_name='Specific heat capacity',units='J/m3/K')
    pfp_utils.CreateSeries(ds,'Cs',Cs,flag,attr)
    if pfp_utils.get_optionskeyaslogical(cf, "RelaxFgStorage"):
        ReplaceWhereMissing(ds.series['Fg'],ds.series['Fg'],ds.series['Fg_Av'],FlagValue=20)

def CorrectSWC(cf,ds):
    """
        Correct soil moisture data using calibration curve developed from
        collected soil samples.  To avoid unrealistic or unphysical extreme
        values upon extrapolation, exponential and logarithmic using ln
        functions are applied to small and large values, respectively.
        Threshold values where one model replaces the other is determined where
        the functions cross.  The logarithmic curve is constrained at with a
        point at which the soil measurement = field porosity and the sensor
        measurement is maximised under saturation at field capacity.

        Usage pfp_ts.CorrectSWC(cf,ds)
        cf: control file
        ds: data structure

        Parameters loaded from control file:
            SWCempList: list of raw CS616 variables
            SWCoutList: list of corrected CS616 variables
            SWCattr:  list of meta-data attributes for corrected CS616 variables
            SWC_a0: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            SWC_a1: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            SWC_b0: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            SWC_b1: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            SWC_t: threshold parameter for switching from exponential to logarithmic model
            TDRempList: list of raw CS610 variables
            TDRoutList: list of corrected CS610 variables
            TDRattr:  list of meta-data attributes for corrected CS610 variables
            TDRlinList: list of deep TDR probes requiring post-hoc linear correction to match empirical samples
            TDR_a0: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            TDR_a1: parameter in logarithmic model, actual = a1 * ln(sensor) + a0
            TDR_b0: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            TDR_b1: parameter in exponential model, actual = b0 * exp(b1 * sensor)
            TDR_t: threshold parameter for switching from exponential to logarithmic model
        """
    if not pfp_utils.get_optionskeyaslogical(cf, "CorrectSWC"):
        return
    logger.info(' Correcting soil moisture data ...')
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    SWCempList = ast.literal_eval(cf['Soil']['empSWCin'])
    SWCoutList = ast.literal_eval(cf['Soil']['empSWCout'])
    SWCattr = ast.literal_eval(cf['Soil']['SWCattr'])
    if cf['Soil']['TDR']=='Yes':
        TDRempList = ast.literal_eval(cf['Soil']['empTDRin'])
        TDRoutList = ast.literal_eval(cf['Soil']['empTDRout'])
        TDRlinList = ast.literal_eval(cf['Soil']['linTDRin'])
        TDRattr = ast.literal_eval(cf['Soil']['TDRattr'])
        TDR_a0 = float(cf['Soil']['TDR_a0'])
        TDR_a1 = float(cf['Soil']['TDR_a1'])
        TDR_b0 = float(cf['Soil']['TDR_b0'])
        TDR_b1 = float(cf['Soil']['TDR_b1'])
        TDR_t = float(cf['Soil']['TDR_t'])
    SWC_a0 = float(cf['Soil']['SWC_a0'])
    SWC_a1 = float(cf['Soil']['SWC_a1'])
    SWC_b0 = float(cf['Soil']['SWC_b0'])
    SWC_b1 = float(cf['Soil']['SWC_b1'])
    SWC_t = float(cf['Soil']['SWC_t'])

    for i in range(len(SWCempList)):
        logger.info('  Applying empirical correction to '+SWCempList[i])
        invar = SWCempList[i]
        outvar = SWCoutList[i]
        attr = SWCattr[i]
        Sws,f,a = pfp_utils.GetSeriesasMA(ds,invar)

        nRecs = len(Sws)

        Sws_out = numpy.ma.empty(nRecs,float)
        Sws_out.fill(c.missing_value)
        Sws_out.mask = numpy.ma.empty(nRecs,bool)
        Sws_out.mask.fill(True)

        index_high = numpy.ma.where((Sws.mask == False) & (Sws > SWC_t))[0]
        index_low = numpy.ma.where((Sws.mask == False) & (Sws < SWC_t))[0]

        Sws_out[index_low] = SWC_b0 * numpy.exp(SWC_b1 * Sws[index_low])
        Sws_out[index_high] = (SWC_a1 * numpy.log(Sws[index_high])) + SWC_a0

        attr = pfp_utils.MakeAttributeDictionary(long_name=attr,units='cm3 water/cm3 soil',standard_name='soil_moisture_content')
        flag = numpy.where(numpy.ma.getmaskarray(Sws_out)==True,ones,zeros)
        pfp_utils.CreateSeries(ds,outvar,Sws_out,flag,attr)
    if cf['Soil']['TDR']=='Yes':
        for i in range(len(TDRempList)):
            logger.info('  Applying empirical correction to '+TDRempList[i])
            invar = TDRempList[i]
            outvar = TDRoutList[i]
            attr = TDRattr[i]
            Sws,f,a = pfp_utils.GetSeriesasMA(ds,invar)

            nRecs = len(Sws)

            Sws_out = numpy.ma.empty(nRecs,float)
            Sws_out.fill(c.missing_value)
            Sws_out.mask = numpy.ma.empty(nRecs,bool)
            Sws_out.mask.fill(True)

            index_high = numpy.ma.where((Sws.mask == False) & (Sws > TDR_t))[0]
            index_low = numpy.ma.where((Sws.mask == False) & (Sws < TDR_t))[0]

            Sws_out[index_low] = TDR_b0 * numpy.exp(TDR_b1 * Sws[index_low])
            Sws_out[index_high] = (TDR_a1 * numpy.log(Sws[index_high])) + TDR_a0

            attr = pfp_utils.MakeAttributeDictionary(long_name=attr,units='cm3 water/cm3 soil',standard_name='soil_moisture_content')
            flag = numpy.where(numpy.ma.getmaskarray(Sws_out)==True,ones,zeros)
            pfp_utils.CreateSeries(ds,outvar,Sws_out,flag,attr)

def CorrectWindDirection(cf, ds, Wd_in):
    """
        Correct wind direction for mis-aligned sensor direction.

        Usage pfp_ts.CorrectWindDirection(cf, ds, Wd_in)
        cf: control file
        ds: data structure
        Wd_in: input/output wind direction variable in ds.  Example: 'Wd_CSAT'
        """
    logger.info(" Correcting wind direction")
    ts = int(ds.globalattributes["time_step"])
    Wd,f,a = pfp_utils.GetSeriesasMA(ds,Wd_in)
    ldt = ds.series["DateTime"]["Data"]
    KeyList = cf["Variables"][Wd_in]["CorrectWindDirection"].keys()
    for i in range(len(KeyList)):
        correct_wd_string = cf["Variables"][Wd_in]["CorrectWindDirection"][str(i)]
        correct_wd_list = correct_wd_string.split(",")
        for i, item in enumerate(correct_wd_list):
            correct_wd_list[i] = correct_wd_list[i].strip()
        try:
            si = pfp_utils.get_start_index(ldt, correct_wd_list[0], mode="quiet")
        except ValueError:
            msg = " CorrectWindDirection: start date (" + correct_wd_list[0] + ") not found"
            logger.warning(msg)
            continue
        try:
            ei = pfp_utils.get_end_index(ldt, correct_wd_list[1], mode="quiet")
        except ValueError:
            msg = " CorrectWindDirection: end date (" + correct_wd_list[1] + ") not found"
            logger.warning(msg)
            continue
        try:
            Correction = float(correct_wd_list[2])
        except:
            msg = " CorrectWindDirection: bad value (" + correct_wd_list[2] + ") for correction"
            logger.warning(msg)
            continue
        Wd[si:ei] = Wd[si:ei] + Correction
    Wd = numpy.mod(Wd, float(360))
    ds.series[Wd_in]["Data"] = numpy.ma.filled(Wd, float(c.missing_value))
    return

def do_attributes(cf,ds):
    """
        Import attriubes in L1 control file to netCDF dataset.  Included
        global and variable attributes.  Also attach flag definitions to global
        meta-data for reference.

        Usage pfp_ts.do_attributes(cf,ds)
        cf: control file
        ds: data structure
        """
    logger.info(' Getting the attributes given in control file')
    if 'Global' in cf.keys():
        for gattr in cf['Global'].keys():
            ds.globalattributes[gattr] = cf['Global'][gattr]
        ds.globalattributes['Flag00'] = 'Good data'
        ds.globalattributes['Flag10'] = 'Corrections: Apply Linear'
        ds.globalattributes['Flag20'] = 'GapFilling: Driver gap filled using ACCESS'
        ds.globalattributes['Flag30'] = 'GapFilling: Flux gap filled by ANN (SOLO)'
        ds.globalattributes['Flag40'] = 'GapFilling: Gap filled by climatology'
        ds.globalattributes['Flag50'] = 'GapFilling: Gap filled by interpolation'
        ds.globalattributes['Flag60'] = 'GapFilling: Flux gap filled using ratios'
        ds.globalattributes['Flag01'] = 'QA/QC: Missing value in L1 dataset'
        ds.globalattributes['Flag02'] = 'QA/QC: L2 Range Check'
        ds.globalattributes['Flag03'] = 'QA/QC: CSAT Diagnostic'
        ds.globalattributes['Flag04'] = 'QA/QC: LI7500 Diagnostic'
        ds.globalattributes['Flag05'] = 'QA/QC: L2 Diurnal SD Check'
        ds.globalattributes['Flag06'] = 'QA/QC: Excluded Dates'
        ds.globalattributes['Flag07'] = 'QA/QC: Excluded Hours'
        ds.globalattributes['Flag08'] = 'QA/QC: Missing value found with QC flag = 0'
        ds.globalattributes['Flag11'] = 'Corrections/Combinations: Coordinate Rotation (Ux, Uy, Uz, UxT, UyT, UzT, UxA, UyA, UzA, UxC, UyC, UzC, UxUz, UxUx, UxUy, UyUz, UxUy, UyUy)'
        ds.globalattributes['Flag12'] = 'Corrections/Combinations: Massman Frequency Attenuation Correction (Coord Rotation, Tv_CSAT, Ah_HMP, ps)'
        ds.globalattributes['Flag13'] = 'Corrections/Combinations: Virtual to Actual Fh (Coord Rotation, Massman, Ta_HMP)'
        ds.globalattributes['Flag14'] = 'Corrections/Combinations: WPL correction for flux effects on density measurements (Coord Rotation, Massman, Fhv to Fh, Cc_7500_Av)'
        ds.globalattributes['Flag15'] = 'Corrections/Combinations: Ta from Tv'
        ds.globalattributes['Flag16'] = 'Corrections/Combinations: L3 Range Check'
        ds.globalattributes['Flag17'] = 'Corrections/Combinations: L3 Diurnal SD Check'
        ds.globalattributes['Flag18'] = 'Corrections/Combinations: u* filter'
        ds.globalattributes['Flag19'] = 'Corrections/Combinations: Gap coordination'
        ds.globalattributes['Flag21'] = 'GapFilling: Used non-rotated covariance'
        ds.globalattributes['Flag31'] = 'GapFilling: Flux gap not filled by ANN'
        ds.globalattributes['Flag38'] = 'GapFilling: L4 Range Check'
        ds.globalattributes['Flag39'] = 'GapFilling: L4 Diurnal SD Check'
        # the following flags are used by James Cleverly's version but not
        # by the standard OzFlux version.
        #ds.globalattributes['Flag51'] = 'albedo: bad Fsd < threshold (290 W/m2 default) only if bad time flag (31) not set'
        #ds.globalattributes['Flag52'] = 'albedo: bad time flag (not midday 10.00 to 14.00)'
        #ds.globalattributes['Flag61'] = 'Penman-Monteith: bad rst (rst < 0) only if bad Uavg (35), bad Fe (33) and bad Fsd (34) flags not set'
        #ds.globalattributes['Flag62'] = 'Penman-Monteith: bad Fe < threshold (0 W/m2 default) only if bad Fsd (34) flag not set'
        #ds.globalattributes['Flag63'] = 'Penman-Monteith: bad Fsd < threshold (10 W/m2 default)'
        #ds.globalattributes['Flag64'] = 'Penman-Monteith: Uavg == 0 (undefined aerodynamic resistance under calm conditions) only if bad Fe (33) and bad Fsd (34) flags not set'
        #ds.globalattributes['Flag70'] = 'Partitioning Night: Re computed from exponential temperature response curves'
        #ds.globalattributes['Flag80'] = 'Partitioning Day: GPP/Re computed from light-response curves, GPP = Re - Fc'
        #ds.globalattributes['Flag81'] = 'Partitioning Day: GPP night mask'
        #ds.globalattributes['Flag82'] = 'Partitioning Day: Fc > Re, GPP = 0, Re = Fc'
    for ThisOne in ds.series.keys():
        if ThisOne in cf['Variables']:
            if 'Attr' in cf['Variables'][ThisOne].keys():
                ds.series[ThisOne]['Attr'] = {}
                for attr in cf['Variables'][ThisOne]['Attr'].keys():
                    ds.series[ThisOne]['Attr'][attr] = cf['Variables'][ThisOne]['Attr'][attr]
                if "missing_value" not in ds.series[ThisOne]['Attr'].keys():
                    ds.series[ThisOne]['Attr']["missing_value"] = numpy.int32(c.missing_value)

def DoFunctions(ds, info):
    """
    Purpose:
     Evaluate functions used in the L1 control file.
    Usage:
    Author: PRI
    Date: September 2015
    """
    implemented_functions = [name for name,data in inspect.getmembers(pfp_func,inspect.isfunction)]
    functions = {}
    convert_vars = []
    function_vars = []
    for var in info["Variables"].keys():
        # datetime functions handled elsewhere for now
        if var == "DateTime": continue
        if "Function" not in info["Variables"][var].keys(): continue
        if "func" not in info["Variables"][var]["Function"].keys():
            msg = " DoFunctions: 'func' keyword not found in [Functions] for "+var
            logger.error(msg)
            continue
        function_string = info["Variables"][var]["Function"]["func"]
        function_string = function_string.replace('"','')
        function_name = function_string.split("(")[0]
        function_args = function_string.split("(")[1].replace(")","").replace(" ","").split(",")
        if function_name not in implemented_functions:
            msg = " DoFunctions: Requested function "+function_name+" not imlemented, skipping ..."
            logger.error(msg)
            continue
        else:
            functions[var] = {"name":function_name, "arguments":function_args}
            if "convert" in function_name.lower():
                convert_vars.append(var)
            else:
                function_vars.append(var)
    for var in convert_vars:
        result = getattr(pfp_func, functions[var]["name"])(ds, var, *functions[var]["arguments"])
        if result:
            msg = " Completed units conversion for " + var
            logger.info(msg)
    for var in function_vars:
        result = getattr(pfp_func, functions[var]["name"])(ds, var, *functions[var]["arguments"])
        if result:
            msg = " Completed function for " + var
            logger.info(msg)

def CalculateStandardDeviations(ds):
    logger.info(' Getting variances from standard deviations & vice versa')
    if 'AhAh' in ds.series.keys() and 'Ah_7500_Sd' not in ds.series.keys():
        AhAh,flag,attr = pfp_utils.GetSeriesasMA(ds,'AhAh')
        Ah_7500_Sd = numpy.ma.sqrt(AhAh)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity from IRGA, standard deviation',units='g/m3')
        pfp_utils.CreateSeries(ds,'Ah_7500_Sd',Ah_7500_Sd,flag,attr)
    if 'Ah_7500_Sd' in ds.series.keys() and 'AhAh' not in ds.series.keys():
        Ah_7500_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'Ah_7500_Sd')
        AhAh = Ah_7500_Sd*Ah_7500_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity from IRGA, variance',units='(g/m3)2')
        pfp_utils.CreateSeries(ds,'AhAh',AhAh,flag,attr)
    if 'Ah_IRGA_Vr' in ds.series.keys() and 'Ah_IRGA_Sd' not in ds.series.keys():
        Ah_IRGA_Vr,flag,attr = pfp_utils.GetSeriesasMA(ds,'Ah_IRGA_Vr')
        Ah_IRGA_Sd = numpy.ma.sqrt(Ah_IRGA_Vr)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity from IRGA, standard deviation',units='g/m3')
        pfp_utils.CreateSeries(ds,'Ah_IRGA_Sd',Ah_IRGA_Sd,flag,attr)
    if 'Ah_IRGA_Sd' in ds.series.keys() and 'Ah_IRGA_Vr' not in ds.series.keys():
        Ah_IRGA_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'Ah_IRGA_Sd')
        Ah_IRGA_Vr = Ah_IRGA_Sd*Ah_IRGA_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity from IRGA, variance',units='(g/m3)2')
        pfp_utils.CreateSeries(ds,'Ah_IRGA_Vr',Ah_IRGA_Vr,flag,attr)
    if 'H2O_IRGA_Vr' in ds.series.keys() and 'H2O_IRGA_Sd' not in ds.series.keys():
        H2O_IRGA_Vr,flag,attr = pfp_utils.GetSeriesasMA(ds,'H2O_IRGA_Vr')
        H2O_IRGA_Sd = numpy.ma.sqrt(H2O_IRGA_Vr)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity from IRGA, standard deviation',units='g/m3')
        pfp_utils.CreateSeries(ds,'H2O_IRGA_Sd',H2O_IRGA_Sd,flag,attr)
    if 'H2O_IRGA_Sd' in ds.series.keys() and 'H2O_IRGA_Vr' not in ds.series.keys():
        H2O_IRGA_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'H2O_IRGA_Sd')
        H2O_IRGA_Vr = H2O_IRGA_Sd*H2O_IRGA_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='Absolute humidity from IRGA, variance',units='(g/m3)2')
        pfp_utils.CreateSeries(ds,'H2O_IRGA_Vr',H2O_IRGA_Vr,flag,attr)
    if 'CcCc' in ds.series.keys() and 'Cc_7500_Sd' not in ds.series.keys():
        CcCc,flag,attr = pfp_utils.GetSeriesasMA(ds,'CcCc')
        Cc_7500_Sd = numpy.ma.sqrt(CcCc)
        attr = pfp_utils.MakeAttributeDictionary(long_name='CO2 concentration from IRGA, standard deviation',units='mg/m3')
        pfp_utils.CreateSeries(ds,'Cc_7500_Sd',Cc_7500_Sd,flag,attr)
    if 'CO2_IRGA_Sd' in ds.series.keys() and 'CO2_IRGA_Vr' not in ds.series.keys():
        CO2_IRGA_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'CO2_IRGA_Sd')
        CO2_IRGA_Vr = CO2_IRGA_Sd*CO2_IRGA_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='CO2 concentration from IRGA, variance',units='(mg/m3)2')
        pfp_utils.CreateSeries(ds,'CO2_IRGA_Vr',CO2_IRGA_Vr,flag,attr)
    if 'Cc_7500_Sd' in ds.series.keys() and 'CcCc' not in ds.series.keys():
        Cc_7500_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'Cc_7500_Sd')
        CcCc = Cc_7500_Sd*Cc_7500_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='CO2 concentration from IRGA, variance',units='(mg/m3)2')
        pfp_utils.CreateSeries(ds,'CcCc',CcCc,flag,attr)
    if 'CO2_IRGA_Vr' in ds.series.keys() and 'CO2_IRGA_Sd' not in ds.series.keys():
        CO2_IRGA_Vr,flag,attr = pfp_utils.GetSeriesasMA(ds,'CO2_IRGA_Vr')
        CO2_IRGA_Sd = numpy.ma.sqrt(CO2_IRGA_Vr)
        attr = pfp_utils.MakeAttributeDictionary(long_name='CO2 concentration from IRGA, standard deviation',units='mg/m3')
        pfp_utils.CreateSeries(ds,'CO2_IRGA_Sd',CO2_IRGA_Sd,flag,attr)
    if 'Ux_Sd' in ds.series.keys() and 'UxUx' not in ds.series.keys():
        Ux_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'Ux_Sd')
        UxUx = Ux_Sd*Ux_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='Longitudinal velocity component from CSAT, variance',units='(m/s)2')
        pfp_utils.CreateSeries(ds,'UxUx',UxUx,flag,attr)
    if 'UxUx' in ds.series.keys() and 'Ux_Sd' not in ds.series.keys():
        UxUx,flag,attr = pfp_utils.GetSeriesasMA(ds,'UxUx')
        Ux_Sd = numpy.ma.sqrt(UxUx)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Longitudinal velocity component from CSAT, standard deviation',units='m/s')
        pfp_utils.CreateSeries(ds,'Ux_Sd',Ux_Sd,flag,attr)
    if 'Uy_Sd' in ds.series.keys() and 'UyUy' not in ds.series.keys():
        Uy_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'Uy_Sd')
        UyUy = Uy_Sd*Uy_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='Lateral velocity component from CSAT, variance',units='(m/s)2')
        pfp_utils.CreateSeries(ds,'UyUy',UyUy,flag,attr)
    if 'UyUy' in ds.series.keys() and 'Uy_Sd' not in ds.series.keys():
        UyUy,flag,attr = pfp_utils.GetSeriesasMA(ds,'UyUy')
        Uy_Sd = numpy.ma.sqrt(UyUy)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Lateral velocity component from CSAT, standard deviation',units='m/s')
        pfp_utils.CreateSeries(ds,'Uy_Sd',Uy_Sd,flag,attr)
    if 'Uz_Sd' in ds.series.keys() and 'UzUz' not in ds.series.keys():
        Uz_Sd,flag,attr = pfp_utils.GetSeriesasMA(ds,'Uz_Sd')
        UzUz = Uz_Sd*Uz_Sd
        attr = pfp_utils.MakeAttributeDictionary(long_name='Vertical velocity component from CSAT, variance',units='(m/s)2')
        pfp_utils.CreateSeries(ds,'UzUz',UzUz,flag,attr)
    if 'UzUz' in ds.series.keys() and 'Uz_Sd' not in ds.series.keys():
        UzUz,flag,attr = pfp_utils.GetSeriesasMA(ds,'UzUz')
        Uz_Sd = numpy.ma.sqrt(UzUz)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Vertical velocity component from CSAT, standard deviation',units='m/s')
        pfp_utils.CreateSeries(ds,'Uz_Sd',Uz_Sd,flag,attr)

def do_mergeseries(ds,target,srclist,mode="verbose"):
    if mode.lower()!="quiet":
        logger.info(' Merging '+str(srclist)+' ==> '+target)
    if srclist[0] not in ds.series.keys():
        if mode.lower()!="quiet":
            logger.error('  MergeSeries: primary input series '+srclist[0]+' not found')
            return
    data = ds.series[srclist[0]]['Data'].copy()
    flag1 = ds.series[srclist[0]]['Flag'].copy()
    flag2 = ds.series[srclist[0]]['Flag'].copy()
    attr = ds.series[srclist[0]]['Attr'].copy()
    SeriesNameString = srclist[0]
    tmplist = list(srclist)
    tmplist.remove(tmplist[0])
    for label in tmplist:
        if label in ds.series.keys():
            SeriesNameString = SeriesNameString+', '+label
            index = numpy.where(numpy.mod(flag1,10)==0)[0]         # find the elements with flag = 0, 10, 20 etc
            flag2[index] = 0                                        # set them all to 0
            if label=="Fg":
                index = numpy.where(flag2==22)[0]
                if len(index)!=0: flag2[index] = 0
            index = numpy.where(flag2!=0)[0]                        # index of flag values other than 0,10,20,30 ...
            data[index] = ds.series[label]['Data'][index].copy()  # replace bad primary with good secondary
            flag1[index] = ds.series[label]['Flag'][index].copy()
        else:
            logger.error(" MergeSeries: secondary input series "+label+" not found")
    attr["long_name"] = attr["long_name"]+", merged from " + SeriesNameString
    pfp_utils.CreateSeries(ds,target,data,flag1,attr)

def Fc_WPL(cf, ds):
    """
        Apply Webb, Pearman and Leuning correction to carbon flux.  This
        correction is necessary to account for flux effects on density
        measurements.  Original formulation: Campbell Scientific

        Usage pfp_ts.Fc_WPL(cf, ds)
        cf: control file
        ds: data structure

        Used for fluxes that are raw or rotated.

        Pre-requisite: CalculateFluxes, CalculateFluxes_Unrotated or CalculateFluxesRM
        Pre-requisite: FhvtoFh
        Pre-requisite: Fe_WPL

        Accepts meteorological constants or variables
        """
    if "DisableFcWPL" in cf["Options"]:
        if cf["Options"].as_bool("DisableFcWPL"):
            logger.warning(" WPL correction for Fc disabled in control file")
            return 0
    logger.info(" Applying WPL correction to Fc")
    descr_level = "description_" + ds.globalattributes["nc_level"]
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    Fc = pfp_utils.GetVariable(ds, "Fc")
    Fh = pfp_utils.GetVariable(ds, "Fh")
    Fe = pfp_utils.GetVariable(ds, "Fe")
    ps = pfp_utils.GetVariable(ds, "ps")
    Ta = pfp_utils.GetVariable(ds, "Ta")
    Ta["Data"] = Ta["Data"] + c.C2K
    Ah = pfp_utils.GetVariable(ds, "Ah")
    Ah["Data"] = Ah["Data"] * c.g2kg
    rhod = pfp_utils.GetVariable(ds, "rhod")
    RhoCp = pfp_utils.GetVariable(ds, "RhoCp")
    Lv = pfp_utils.GetVariable(ds, "Lv")
    # deal with aliases for CO2 concentration
    if "Cc" in ds.series.keys():
        CO2_in = "Cc"
    elif "CO2" in ds.series.keys():
        CO2_in = "CO2"
    else:
        msg = " Fc_WPL: did not find CO2 in data structure"
        logger.error(msg)
        ds.returncodes["message"] = msg
        ds.returncodes["value"] = 1
        return 1
    CO2 = pfp_utils.GetVariable(ds, CO2_in)
    if CO2["Attr"]["units"] != "mg/m3":
        if CO2["Attr"]["units"] == "umol/mol":
            msg = " Fc_WPL: CO2 units ("+CO2["Attr"]["units"]+") converted to mg/m3"
            logger.warning(msg)
            CO2["Data"] = pfp_mf.co2_mgCO2pm3fromppm(CO2["Data"], Ta["Data"], ps["Data"])
        else:
            msg = " Fc_WPL: unrecognised units ("+CO2["Attr"]["units"]+") for CO2"
            logger.error(msg)
            ds.returncodes["message"] = msg
            ds.returncodes["value"] = 1
            return 1
    sigma = Ah["Data"] / rhod["Data"]
    co2_wpl_Fe = (c.mu/(1+c.mu*sigma))*(CO2["Data"]/rhod["Data"])*(Fe["Data"]/Lv["Data"])
    co2_wpl_Fh = (CO2["Data"]/Ta["Data"])*(Fh["Data"]/RhoCp["Data"])
    Fc_wpl_data = Fc["Data"] + co2_wpl_Fe + co2_wpl_Fh
    Fc_wpl_flag = numpy.zeros(len(Fc_wpl_data))
    index = numpy.where(numpy.ma.getmaskarray(Fc_wpl_data) == True)[0]
    Fc_wpl_flag[index] = numpy.int32(14)
    attr = {"group_name": "flux", "long_name": "CO2 flux", "units": "mg/m2/s",
            "standard_name": "not defined", descr_level: "WPL corrected"}
    for item in ["instrument", "height", "serial_number"]:
        attr[item] = Fc["Attr"][item]
    variable = {"Label": "Fc", "Data": Fc_wpl_data, "Flag": Fc_wpl_flag, "Attr": attr}
    pfp_utils.CreateVariable(ds, variable)
    variable = {"Label": "Fc_PFP", "Data": Fc_wpl_data, "Flag": Fc_wpl_flag, "Attr": attr}
    pfp_utils.CreateVariable(ds, variable)
    return 0

def Fe_WPL(cf, ds):
    """
        Apply Webb, Pearman and Leuning correction to vapour flux.  This
        correction is necessary to account for flux effects on density
        measurements.  Original formulation: Campbell Scientific

        Usage pfp_ts.Fe_WPL(cf, ds)
        cf: control file
        ds: data structure

        Used for fluxes that are raw or rotated.

        Pre-requisite: CalculateFluxes, CalculateFluxes_Unrotated or CalculateFluxesRM
        Pre-requisite: FhvtoFh

        Accepts meteorological constants or variables
        """
    if "DisableFeWPL" in cf["Options"]:
        if cf["Options"].as_bool("DisableFeWPL"):
            logger.warning(" WPL correction for Fe disabled in control file")
            return 0
    logger.info(" Applying WPL correction to Fe")
    descr_level = "description_" + ds.globalattributes["nc_level"]
    Fe = pfp_utils.GetVariable(ds, "Fe")
    Fh = pfp_utils.GetVariable(ds, "Fh")
    Ta = pfp_utils.GetVariable(ds, "Ta")
    Ta["Data"] = Ta["Data"] + c.C2K
    Ah = pfp_utils.GetVariable(ds, "Ah")
    ps = pfp_utils.GetVariable(ds, "ps")
    rhod = pfp_utils.GetVariable(ds, "rhod")
    rhom = pfp_utils.GetVariable(ds, "rhom")
    RhoCp = pfp_utils.GetVariable(ds, "RhoCp")
    Lv = pfp_utils.GetVariable(ds, "Lv")
    Ah["Data"] = Ah["Data"]*c.g2kg
    sigma = Ah["Data"]/rhod["Data"]
    h2o_wpl_Fe = c.mu*sigma*Fe["Data"]
    h2o_wpl_Fh = (1+c.mu*sigma)*Ah["Data"]*Lv["Data"]*(Fh["Data"]/RhoCp["Data"])/Ta["Data"]
    Fe_wpl_data = Fe["Data"] + h2o_wpl_Fe + h2o_wpl_Fh
    Fe_wpl_flag = numpy.zeros(len(Fe_wpl_data))
    idx = numpy.where(numpy.ma.getmaskarray(Fe_wpl_data) == True)[0]
    Fe_wpl_flag[idx] = numpy.int32(14)
    attr = {"group_name": "flux", "long_name": "Latent heat flux", "units": "W/m2",
            "standard_name": "surface_upward_latent_heat_flux",
            descr_level: "WPL corrected"}
    for item in ["instrument", "height", "serial_number"]:
        attr[item] = Fe["Attr"][item]
    variable = {"Label": "Fe", "Data": Fe_wpl_data, "Flag": Fe_wpl_flag, "Attr": attr}
    pfp_utils.CreateVariable(ds, variable)
    variable = {"Label": "Fe_PFP", "Data": Fe_wpl_data, "Flag": Fe_wpl_flag, "Attr": attr}
    pfp_utils.CreateVariable(ds, variable)
    if pfp_utils.get_optionskeyaslogical(cf, "RelaxFeWPL"):
        ReplaceWhereMissing(ds.series['Fe'], ds.series['Fe'], ds.series['Fe_raw'], FlagValue=20)
    return 0

def FhvtoFh(cf, ds):
    '''
    Convert the virtual heat flux to the sensible heat flux.
    USEAGE:
     pfp_ts.FhvtoFh(cf, ds)
    INPUT:
     All inputs are read from the data structure.
    OUTPUT:
     All outputs are written to the data structure.
    '''
    logger.info(' Converting virtual Fh to Fh')
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    # deal with sonic temperature aliases
    Tv_in = "Tv_SONIC_Av"
    if Tv_in not in ds.series.keys():
        if "Tv_CSAT" in ds.series.keys():
            Tv_in = "Tv_CSAT"
        elif "Tv_CSAT_Av" in ds.series.keys():
            Tv_in = "Tv_CSAT_Av"
        else:
            logger.error(" FhvtoFh: sonic virtual temperature not found in data structure")
            return
    # get the input series
    Fhv = pfp_utils.GetVariable(ds, "Fhv")              # get the virtual heat flux
    Tv = pfp_utils.GetVariable(ds, Tv_in)               # get the virtual temperature, C
    Tv["Data"] = Tv["Data"] + c.C2K                     # convert from C to K
    wA = pfp_utils.GetVariable(ds, "wA")                # get the wA covariance, g/m2/s
    wA["Data"] = wA["Data"] * c.g2kg                    # convert from g/m2/s to kg/m2/s
    SH = pfp_utils.GetVariable(ds, "SH")                # get the specific humidity, kg/kg
    wT = pfp_utils.GetVariable(ds, "wT")                # get the wT covariance, mK/s
    # get the utility series
    RhoCp = pfp_utils.GetVariable(ds, "RhoCp")          # get rho*Cp
    rhom = pfp_utils.GetVariable(ds, "rhom")            # get the moist air density, kg/m3
    # define local constants
    alpha = 0.51
    # do the conversion
    t1 = RhoCp["Data"]*alpha*Tv["Data"]*wA["Data"]/rhom["Data"]
    t2 = RhoCp["Data"]*alpha*SH["Data"]*wT["Data"]
    Fh = Fhv["Data"] - t1 - t2
    # put the calculated sensible heat flux into the data structure
    attr = {"group_name": "flux", "long_name": "Sensible heat flux", "units": "W/m2",
                    "standard_name": "surface_upward_sensible_heat_flux"}
    for item in ["instrument", "height", "serial_number"]:
        attr[item] = wT["Attr"][item]
    flag = numpy.where(numpy.ma.getmaskarray(Fh) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": "Fh", "Data": Fh, "Flag": flag, "Attr": attr})
    pfp_utils.CreateVariable(ds, {"Label": "Fh_PFP", "Data": Fh, "Flag": flag, "Attr": attr})
    if pfp_utils.get_optionskeyaslogical(cf, "RelaxFhvtoFh"):
        ReplaceWhereMissing(ds.series['Fh'], ds.series['Fh'], ds.series['Fhv'], FlagValue=20)

def get_averages(Data):
    """
        Get daily averages on days when no 30-min observations are missing.
        Days with missing observations return a value of c.missing_value
        Values returned are sample size (Num) and average (Av)

        Usage pfp_ts.get_averages(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(c.missing_value))>c.eps)
    Num = numpy.size(li)
    if Num == 0:
        Av = c.missing_value
    elif Num == 48:
        Av = numpy.ma.mean(Data[li])
    else:
        x = 0
        index = numpy.ma.where(Data.mask == True)[0]
        if len(index) == 1:
            x = 1
        elif len(index) > 1:
            for i in range(len(Data)):
                if Data.mask[i] == True:
                    x = x + 1

        if x == 0:
            Av = numpy.ma.mean(Data[li])
        else:
            Av = c.missing_value
    return Num, Av

def get_laggedcorrelation(x_in,y_in,maxlags):
    """
    Calculate the lagged cross-correlation between 2 1D arrays.
    Taken from the matplotlib.pyplot.xcorr source code.
    PRI added handling of masked arrays.
    """
    lags = numpy.arange(-maxlags,maxlags+1)
    mask = numpy.ma.mask_or(x_in.mask,y_in.mask,copy=True,shrink=False)
    x = numpy.ma.array(x_in,mask=mask,copy=True)
    y = numpy.ma.array(y_in,mask=mask,copy=True)
    x = numpy.ma.compressed(x)
    y = numpy.ma.compressed(y)
    corr = numpy.correlate(x, y, mode=2)
    corr/= numpy.sqrt(numpy.dot(x,x) * numpy.dot(y,y))
    if maxlags is None: maxlags = len(x) - 1
    if maxlags >= len(x) or maxlags < 1:
        raise ValueError('pfp_ts.get_laggedcorrelation: maxlags must be None or strictly positive < %d'%len(x))
    corr = corr[len(x)-1-maxlags:len(x)+maxlags]
    return lags,corr

def get_minmax(Data):
    """
        Get daily minima and maxima on days when no 30-min observations are missing.
        Days with missing observations return a value of c.missing_value
        Values returned are sample size (Num), minimum (Min) and maximum (Max)

        Usage pfp_ts.get_minmax(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(c.missing_value))>c.eps)
    Num = numpy.size(li)
    if Num == 0:
        Min = c.missing_value
        Max = c.missing_value
    elif Num == 48:
        Min = numpy.ma.min(Data[li])
        Max = numpy.ma.max(Data[li])
    else:
        x = 0
        index = numpy.ma.where(Data.mask == True)[0]
        if len(index) == 1:
            x = 1
        elif len(index) > 1:
            for i in range(len(Data)):
                if Data.mask[i] == True:
                    x = x + 1

        if x == 0:
            Min = numpy.ma.min(Data[li])
            Max = numpy.ma.max(Data[li])
        else:
            Min = c.missing_value
            Max = c.missing_value
    return Num, Min, Max

def get_nightsums(Data):
    """
        Get nightly sums and averages on nights when no 30-min observations are missing.
        Nights with missing observations return a value of c.missing_value
        Values returned are sample size (Num), sums (Sum) and average (Av)

        Usage pfp_ts.get_nightsums(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(Data.mask == False)[0]
    Num = numpy.size(li)
    if Num == 0:
        Sum = c.missing_value
        Av = c.missing_value
    else:
        x = 0
        for i in range(len(Data)):
            if Data.mask[i] == True:
                x = x + 1

        if x == 0:
            Sum = numpy.ma.sum(Data[li])
            Av = numpy.ma.mean(Data[li])
        else:
            Sum = c.missing_value
            Av = c.missing_value

    return Num, Sum, Av

def get_soilaverages(Data):
    """
        Get daily averages of soil water content on days when 15 or fewer 30-min observations are missing.
        Days with 16 or more missing observations return a value of c.missing_value
        Values returned are sample size (Num) and average (Av)

        Usage pfp_ts.get_soilaverages(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(c.missing_value))>c.eps)
    Num = numpy.size(li)
    if Num > 33:
        Av = numpy.ma.mean(Data[li])
    else:
        Av = c.missing_value
    return Num, Av

def get_subsums(Data):
    """
        Get separate daily sums of positive and negative fluxes when no 30-min observations are missing.
        Days with missing observations return a value of c.missing_value
        Values returned are positive and negative sample sizes (PosNum and NegNum) and sums (SumPos and SumNeg)

        Usage pfp_ts.get_subsums(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(c.missing_value))>c.eps)
    Num = numpy.size(li)
    if Num == 48:
        pi = numpy.ma.where(Data[li]>0)
        ni = numpy.ma.where(Data[li]<0)
        PosNum = numpy.size(pi)
        NegNum = numpy.size(ni)
        if PosNum > 0:
            SumPos = numpy.ma.sum(Data[pi])
        else:
            SumPos = 0
        if NegNum > 0:
            SumNeg = numpy.ma.sum(Data[ni])
        else:
            SumNeg = 0
    else:
        pi = numpy.ma.where(Data[li]>0)
        ni = numpy.ma.where(Data[li]<0)
        PosNum = numpy.size(pi)
        NegNum = numpy.size(ni)
        SumPos = c.missing_value
        SumNeg = c.missing_value
    return PosNum, NegNum, SumPos, SumNeg

def get_sums(Data):
    """
        Get daily sums when no 30-min observations are missing.
        Days with missing observations return a value of c.missing_value
        Values returned are sample size (Num) and sum (Sum)

        Usage pfp_ts.get_sums(Data)
        Data: 1-day dataset
        """
    li = numpy.ma.where(abs(Data-float(c.missing_value))>c.eps)
    Num = numpy.size(li)
    if Num == 0:
        Sum = c.missing_value
    elif Num == 48:
        Sum = numpy.ma.sum(Data[li])
    else:
        x = 0
        index = numpy.ma.where(Data.mask == True)[0]
        if len(index) == 1:
            x = 1
        elif len(index) > 1:
            for i in range(len(Data)):
                if Data.mask[i] == True:
                    x = x + 1

        if x == 0:
            Sum = numpy.ma.sum(Data[li])
        else:
            Sum = c.missing_value
    return Num, Sum

def get_qcflag(ds):
    """
        Set up flags during ingest of L1 data.
        Identifies missing observations as c.missing_value and sets flag value 1

        Usage pfp_ts.get_qcflag(ds)
        ds: data structure
        """
    logger.info(' Setting up the QC flags')
    nRecs = len(ds.series['xlDateTime']['Data'])
    for ThisOne in ds.series.keys():
        ds.series[ThisOne]['Flag'] = numpy.zeros(nRecs,dtype=numpy.int32)
        index = numpy.where(ds.series[ThisOne]['Data']==c.missing_value)[0]
        ds.series[ThisOne]['Flag'][index] = numpy.int32(1)

def get_synthetic_fsd(ds):
    """
    Purpose:
     Calculates a time series of synthetic downwelling shortwave radiation.  The
     solar altitude is also output.
    Useage:
     pfp_ts.get_synthetic_fsd(ds)
    Author: PRI
    Date: Sometime in 2014
    """
    logger.info(' Calculating synthetic Fsd')
    # get the latitude and longitude
    lat = float(ds.globalattributes["latitude"])
    lon = float(ds.globalattributes["longitude"])
    # get the UTC time from the local time
    ldt_UTC = pfp_utils.get_UTCfromlocaltime(ds)
    # get the solar altitude
    alt_solar = [pysolar.GetAltitude(lat,lon,dt) for dt in ldt_UTC]
    # get the synthetic downwelling shortwave radiation
    Fsd_syn = [pysolar.GetRadiationDirect(dt,alt) for dt,alt in zip(ldt_UTC,alt_solar)]
    Fsd_syn = numpy.ma.array(Fsd_syn)
    # get the QC flag
    nRecs = len(Fsd_syn)
    flag = numpy.zeros(nRecs,dtype=numpy.int32)
    # add the synthetic downwelling shortwave radiation to the data structure
    attr = pfp_utils.MakeAttributeDictionary(long_name='Synthetic downwelling shortwave radiation',units='W/m2',
                                           standard_name='surface_downwelling_shortwave_flux_in_air')
    pfp_utils.CreateSeries(ds,"Fsd_syn",Fsd_syn,flag,attr)
    ds.intermediate.append("Fsd_syn")
    # add the solar altitude to the data structure
    attr = pfp_utils.MakeAttributeDictionary(long_name='Solar altitude',units='deg',
                                           standard_name='not defined')
    pfp_utils.CreateSeries(ds,"solar_altitude",alt_solar,flag,attr)
    ds.intermediate.append("solar_altitude")

def InvertSign(ds,ThisOne):
    logger.info(' Inverting sign of '+ThisOne)
    index = numpy.where(abs(ds.series[ThisOne]['Data']-float(c.missing_value))>c.eps)[0]
    ds.series[ThisOne]['Data'][index] = float(-1)*ds.series[ThisOne]['Data'][index]

def InterpolateOverMissing(ds, labels, max_length_hours=0, int_type="linear"):
    """
    Purpose:
     Interpolate over periods of missing data.  Uses linear interpolation.
    Usage:
     pfp_ts.InterpolateOverMissing(ds, labels, max_length_hours=0, int_type="linear")
     where ds is the data structure
           label is a series label or a list of labels
           max_length_hours is the maximum gap length (hours) to be filled by interpolation
           int_type is the interpolation type ("linear" or "Akima")
    Side effects:
     Fills gaps.
    Author: PRI
    Date: September 2014
    """
    # check to see if we need to do anything
    if max_length_hours == 0:
        return
    if isinstance(labels, basestring):
        labels = [labels]
    elif isinstance(labels, list):
        pass
    else:
        msg = " Input label " + labels + " must be a string or a list"
        logger.error(msg)
        return
    ts = int(ds.globalattributes["time_step"])
    max_length_points = int((max_length_hours * float(60)/float(ts)) + 0.5)
    for label in labels:
        # check that series is in the data structure
        if label not in ds.series.keys():
            msg = " Variable " + label + " not found in data structure"
            logger.error(msg)
            continue
        # convert the Python datetime to a number
        DateNum = date2num(ds.series["DateTime"]["Data"])
        # get the data
        data_org, flag_org, attr_org = pfp_utils.GetSeries(ds, label)
        # number of records
        nRecs = len(data_org)
        # index of good values
        iog = numpy.where(abs(data_org - float(c.missing_value)) > c.eps)[0]
        # index of missing values
        iom = numpy.where(abs(data_org - float(c.missing_value)) <= c.eps)[0]
        # return if there is not enough data to use
        if len(iog) < 2:
            msg = " Less than 2 good points available for interpolation " + str(label)
            logger.info(msg)
            continue
        if int_type == "linear":
            # linear interpolation function
            f = interpolate.interp1d(DateNum[iog], data_org[iog], bounds_error=False,
                                     fill_value=float(c.missing_value))
            # interpolate over the whole time series
            data_int = f(DateNum).astype(numpy.float64)
        elif int_type == "Akima":
            int_fn = interpolate.Akima1DInterpolator(DateNum[iog], data_org[iog])
            data_int = int_fn(DateNum)
            # trap non-finite values from the Akima 1D interpolator
            data_int = numpy.where(numpy.isfinite(data_int) == True, data_int,
                                   numpy.float(c.missing_value))
        else:
            msg = " Unrecognised interpolator option (" + int_type + "), skipping ..."
            logger.error(msg)
            continue
        # copy the original flag
        flag_int = numpy.copy(flag_org)
        # index of interpolates that are not equal to the missing value
        index = numpy.where(abs(data_int - float(c.missing_value)) > c.eps)[0]
        # set the flag for these points
        if len(index) != 0:
            flag_int[index] = numpy.int32(50)
        # restore the original good data
        data_int[iog] = data_org[iog]
        flag_int[iog] = flag_org[iog]
        # now replace data in contiguous blocks of length > min with missing data
        # first, a conditional index, 0 where data is good, 1 where it is missing
        cond_ind = numpy.zeros(nRecs, dtype=numpy.int32)
        cond_ind[iom] = 1
        cond_bool = (cond_ind==1)
        # start and stop indices of contiguous blocks
        for start, stop in pfp_utils.contiguous_regions(cond_bool):
            # code to handle minimum segment length goes here
            duration = stop - start
            if duration > max_length_points:
                data_int[start:stop] = numpy.float64(c.missing_value)
                flag_int[start:stop] = flag_org[start:stop]
        # put data_int back into the data structure
        attr_int = dict(attr_org)
        pfp_utils.CreateSeries(ds, label, data_int, flag_int, attr_int)
    return

def MassmanStandard(cf, ds, Ta_in='Ta', Ah_in='Ah', ps_in='ps', u_in="U_SONIC_Av",
                    ustar_in='ustar', ustar_out='ustar', L_in='L', L_out ='L',
                    uw_out='uw', vw_out='vw', wT_out='wT', wA_out='wA', wC_out='wC'):
    """
       Massman corrections.
       The steps involved are as follows:
        1) calculate ustar and L using rotated but otherwise uncorrected covariances
       """
    if "Massman" not in cf:
        msg = " Massman section not in control file, skipping correction ..."
        logger.warning(msg)
        return
    logger.info(" Correcting for flux loss from spectral attenuation")
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs, dtype=numpy.int32)
    ones = numpy.ones(nRecs, dtype=numpy.int32)
    zmd = float(cf["Massman"]["zmd"])             # z-d for site
    if ("angle" in cf["Massman"] and
        "CSATarm" in cf["Massman"] and
        "IRGAarm" in cf["Massman"]):
        # this is the original definition of lateral and longitudinal separation
        # as coded by James
        angle = float(cf["Massman"]["angle"])         # CSAT3-IRGA separation angle
        CSATarm = float(cf["Massman"]["CSATarm"])     # CSAT3 mounting distance
        IRGAarm = float(cf["Massman"]["IRGAarm"])     # IRGA mounting distance
        lLat = numpy.ma.sin(numpy.deg2rad(angle)) * IRGAarm
        lLong = CSATarm - (numpy.ma.cos(numpy.deg2rad(angle)) * IRGAarm)
    elif ("north_separation" in cf["Massman"] and
          "east_separation" in cf["Massman"]):
        # the following is the definition of lateral and longitudinal separation
        # used in EddyPro, it is not equivalent to the one used above
        nsep = numpy.float(cf["Massman"]["north_separation"])
        esep = numpy.float(cf["Massman"]["east_separation"])
        lLat = numpy.sqrt(nsep*nsep + esep*esep)
        lLong = numpy.float(0)
    else:
        msg = " Required separation information not found in Massman section of control file"
        logger.error(msg)
        return
    # *** Massman_1stpass starts here ***
    #  The code for the first and second passes is very similar.  It would be useful to make them the
    #  same and put into a loop to reduce the number of lines in this function.
    # calculate ustar and Monin-Obukhov length from rotated but otherwise uncorrected covariances
    Ta = pfp_utils.GetVariable(ds, Ta_in)
    Ah = pfp_utils.GetVariable(ds, Ah_in)
    ps = pfp_utils.GetVariable(ds, ps_in)
    u = pfp_utils.GetVariable(ds, u_in)
    uw = pfp_utils.GetVariable(ds, "uw")
    vw = pfp_utils.GetVariable(ds, "vw")
    wT = pfp_utils.GetVariable(ds, "wT")
    wC = pfp_utils.GetVariable(ds, "wC")
    wA = pfp_utils.GetVariable(ds, "wA")
    if ustar_in not in ds.series.keys():
        ustarm = numpy.ma.sqrt(numpy.ma.sqrt(uw["Data"] ** 2 + vw["Data"] ** 2))
    else:
        ustarm, _, _ = pfp_utils.GetSeriesasMA(ds, ustar_in)
    if L_in not in ds.series.keys():
        Lm = pfp_mf.molen(Ta["Data"], Ah["Data"], ps["Data"], ustarm, wT["Data"], fluxtype="kinematic")
    else:
        Lm, _, _ = pfp_utils.GetSeriesasMA(ds, L_in)
    # now calculate z on L
    zoLm = zmd / Lm
    # start calculating the correction coefficients for approximate corrections
    #  create nxMom, nxScalar and alpha series with their unstable values by default
    nxMom, nxScalar, alpha = pfp_utils.nxMom_nxScalar_alpha(zoLm)
    # now calculate the fxMom and fxScalar coefficients
    fxMom = nxMom * u["Data"] / zmd
    fxScalar = nxScalar * u["Data"] / zmd
    # compute spectral filters
    tau_sonic_law_4scalar = c.lwVert / (8.4 * u["Data"])
    tau_sonic_laT_4scalar = c.lTv / (4.0 * u["Data"])
    tau_irga_la = (c.lIRGA / (4.0 * u["Data"]))
    tau_irga_va = (0.2+0.4*c.dIRGA/c.lIRGA)*(c.lIRGA/u["Data"])
    tau_irga_bw = 0.016
    tau_irga_lat = (lLat / (1.1 * u["Data"]))
    tau_irga_lon = (lLong / (1.05 * u["Data"]))

    tao_eMom = numpy.ma.sqrt(((c.lwVert / (5.7 * u["Data"])) ** 2) +
                             ((c.lwHor / (2.8 * u["Data"])) ** 2))
    tao_ewT = numpy.ma.sqrt((tau_sonic_law_4scalar ** 2) + (tau_sonic_laT_4scalar ** 2))

    tao_ewIRGA = numpy.ma.sqrt((tau_sonic_law_4scalar ** 2) +
                               (tau_irga_la ** 2) +
                               (tau_irga_va ** 2) +
                               (tau_irga_bw ** 2) +
                               (tau_irga_lat ** 2) +
                               (tau_irga_lon ** 2))

    tao_b = c.Tb / 2.8
    # calculate coefficients
    bMom = pfp_utils.bp(fxMom, tao_b)
    bScalar = pfp_utils.bp(fxScalar, tao_b)
    pMom = pfp_utils.bp(fxMom, tao_eMom)
    pwT = pfp_utils.bp(fxScalar, tao_ewT)
    # calculate corrections for momentum and scalars
    rMom = pfp_utils.r(bMom, pMom, alpha)
    rwT = pfp_utils.r(bScalar, pwT, alpha)
    # determine approximately-true Massman fluxes
    uwm = uw["Data"] / rMom
    vwm = vw["Data"] / rMom
    wTm = wT["Data"] / rwT
    # *** Massman_1stpass ends here ***
    # *** Massman_2ndpass starts here ***
    # we have calculated the first pass corrected momentum and temperature covariances, now we use
    # these to calculate the final corrections
    #  first, get the 2nd pass corrected friction velocity and Monin-Obukhov length
    ustarm = numpy.ma.sqrt(numpy.ma.sqrt(uwm ** 2 + vwm ** 2))
    Lm = pfp_mf.molen(Ta["Data"], Ah["Data"], ps["Data"], ustarm, wTm, fluxtype='kinematic')
    zoLm = zmd / Lm
    nxMom, nxScalar, alpha = pfp_utils.nxMom_nxScalar_alpha(zoLm)
    fxMom = nxMom * (u["Data"] / zmd)
    fxScalar = nxScalar * (u["Data"] / zmd)
    # calculate coefficients
    bMom = pfp_utils.bp(fxMom, tao_b)
    bScalar = pfp_utils.bp(fxScalar, tao_b)
    pMom = pfp_utils.bp(fxMom, tao_eMom)
    pwT = pfp_utils.bp(fxScalar, tao_ewT)
    pwIRGA = pfp_utils.bp(fxScalar, tao_ewIRGA)
    # calculate corrections for momentum and scalars
    rMom = pfp_utils.r(bMom, pMom, alpha)
    rwT = pfp_utils.r(bScalar, pwT, alpha)
    rwIRGA = pfp_utils.r(bScalar, pwIRGA, alpha)
    # determine true fluxes
    uwM = uw["Data"] / rMom
    vwM = vw["Data"] / rMom
    wTM = wT["Data"] / rwT
    wCM = wC["Data"] / rwIRGA
    wAM = wA["Data"] / rwIRGA
    ustarM = numpy.ma.sqrt(numpy.ma.sqrt(uwM ** 2 + vwM ** 2))
    LM = pfp_mf.molen(Ta["Data"], Ah["Data"], ps["Data"], ustarM, wTM, fluxtype="kinematic")
    # write the 2nd pass Massman corrected covariances to the data structure
    attr = pfp_utils.MakeAttributeDictionary(long_name="Massman true ustar", units="m/s")
    flag = numpy.where(numpy.ma.getmaskarray(ustarM) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": ustar_out, "Data": ustarM, "Flag": flag, "Attr": attr})

    attr = pfp_utils.MakeAttributeDictionary(long_name="Massman true Obukhov Length", units="m")
    flag = numpy.where(numpy.ma.getmaskarray(LM) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": L_out, "Data": LM, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(uw["Attr"])
    attr["long_name"] = attr["long_name"] + ", Massman frequency correction"
    flag = numpy.where(numpy.ma.getmaskarray(uwM) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": uw_out, "Data": uwM, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(vw["Attr"])
    attr["long_name"] = attr["long_name"] + ", Massman frequency correction"
    flag = numpy.where(numpy.ma.getmaskarray(vwM) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": vw_out, "Data": vwM, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(wT["Attr"])
    attr["long_name"] = attr["long_name"] + ", Massman frequency correction"
    flag = numpy.where(numpy.ma.getmaskarray(wTM) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": wT_out, "Data": wTM, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(wA["Attr"])
    attr["long_name"] = attr["long_name"] + ", Massman frequency correction"
    flag = numpy.where(numpy.ma.getmaskarray(wAM) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": wA_out, "Data": wAM, "Flag": flag, "Attr": attr})

    attr = copy.deepcopy(wC["Attr"])
    attr["long_name"] = attr["long_name"] + ", Massman frequency correction"
    flag = numpy.where(numpy.ma.getmaskarray(wCM) == True, ones, zeros)
    pfp_utils.CreateVariable(ds, {"Label": wC_out, "Data": wCM, "Flag": flag, "Attr": attr})
    # *** Massman_2ndpass ends here ***
    return

def MergeSeriesUsingDict(ds, info, merge_order="standard"):
    """ Merge series as defined in the merge dictionary."""
    # create decsription level attribute string
    descr_level = "description_" + ds.globalattributes["nc_level"]
    merge = info["MergeSeries"]
    if merge_order not in merge:
        msg = "MergeSeriesUsingDict: merge order " + merge_order + " not found"
        logger.warning(msg)
        return
    # loop over the entries in merge
    for target in merge[merge_order].keys():
        srclist = merge[merge_order][target]["source"]
        logger.info(" Merging "+str(srclist)+"==>"+target)
        if srclist[0] not in ds.series.keys():
            logger.error("  MergeSeries: primary input series "+srclist[0]+" not found")
            continue
        data = ds.series[srclist[0]]["Data"].copy()
        flag1 = ds.series[srclist[0]]["Flag"].copy()
        flag2 = ds.series[srclist[0]]["Flag"].copy()
        attr = ds.series[srclist[0]]["Attr"].copy()
        SeriesNameString = srclist[0]
        tmplist = list(srclist)
        tmplist.remove(tmplist[0])
        s2add = ""
        for label in tmplist:
            if label in ds.series.keys():
                SeriesNameString = SeriesNameString+", "+label
                index = numpy.where(numpy.mod(flag1, 10) == 0)[0]       # find the elements with flag = 0, 10, 20 etc
                flag2[index] = 0                                        # set them all to 0
                if label=="Fg":
                    index = numpy.where(flag2 == 22)[0]
                    if len(index) != 0:
                        flag2[index] = 0
                index = numpy.where(flag2 != 0)[0]                      # index of flag values other than 0,10,20,30 ...
                data[index] = ds.series[label]["Data"][index].copy()    # replace bad primary with good secondary
                flag1[index] = ds.series[label]["Flag"][index].copy()
                s2add = pfp_utils.append_string(s2add, ds.series[label]["Attr"][descr_level], caps=False)
            else:
                logger.error(" MergeSeries: secondary input series "+label+" not found")
        s2add = "gap filled using " + s2add
        attr[descr_level] = pfp_utils.append_string(attr[descr_level], s2add)
        pfp_utils.CreateSeries(ds, target, data, flag1, attr)
    return

def MergeDataStructures(ds_dict, l1_info):
    """
    Purpose:
     Merge multiple data structures into a single data structure.
     Merging is done on the time axis as follows:
      1) find the earliest start time
      2) find the latest end time
      3) construct a datetime series between the earliest start datetime
         and the latest end datetime at the time step interval
      4) create the datetime series in the merged data structure
      5) insert the data from each individual data structure into
         the merged data structure by matching the datetimes
    Usage:
    Side effects:
     Returns a new data structure with the contents of the individual
     data structures passed in as ds_dict.
    Author: PRI
    Date: February 2020
    """
    msg = " Merging " + str(list(ds_dict.keys()))
    logger.info(msg)
    l1ire = l1_info["read_excel"]
    # data structure to hold all data
    ds = pfp_io.DataStructure()
    ds.globalattributes = copy.deepcopy(l1ire["Global"])
    # get the earliest start datetime and the latest datetime
    start = []
    end = []
    for item in list(ds_dict.keys()):
        start.append(ds_dict[item].series["DateTime"]["Data"][0])
        end.append(ds_dict[item].series["DateTime"]["Data"][-1])
    start = min(start)
    end = max(end)
    # put the datetime into the data structure
    ts = int(ds.globalattributes["time_step"])
    dts = datetime.timedelta(minutes=ts)
    # generate an aray of datetime from start to end with spacing of ts
    dt = numpy.array([d for d in pfp_utils.perdelta(start, end, dts)])
    nrecs = len(dt)
    var = pfp_utils.CreateEmptyVariable("DateTime", nrecs)
    var["Label"] = "DateTime"
    var["Data"] = dt
    var["Flag"] = numpy.zeros(len(var["Data"]), dtype=numpy.int32)
    var["Attr"] = {"long_name": "Datetime in local timezone",
                   "cf_role": "timeseries_id",
                   "units": "days since 1899-12-31 00:00:00"}
    pfp_utils.CreateVariable(ds, var)
    # update the global attributes
    ds.globalattributes["start_date"] = str(dt[0])
    ds.globalattributes["end_date"] = str(dt[-1])
    ds.globalattributes["nc_nrecs"] = len(dt)
    # put the data into the data structure
    dt1 = pfp_utils.GetVariable(ds, "DateTime")
    for item in list(ds_dict.keys()):
        #print item
        # get the datetime for this worksheet
        dtn = pfp_utils.GetVariable(ds_dict[item], "DateTime")
        # remove duplicate timestamps
        dtn_unique, index_unique = numpy.unique(dtn["Data"], return_index=True)
        # restore the original order of the unique timestamps
        dtn_sorted = dtn_unique[numpy.argsort(index_unique)]
        # check to see if there were duplicates
        if len(dtn_sorted) < len(dtn["Data"]):
            n = len(dtn["Data"]) - len(dtn_sorted)
            msg = str(n) + " duplicate time stamps were removed for sheet " + item
            logger.warning(msg)
        # get the indices where the timestamps match
        idxa, idxb = pfp_utils.FindMatchingIndices(dt1["Data"], dtn_sorted)
        # check that all datetimes in ds_dict[item] were found in ds
        if len(idxa) != len(dtn_sorted):
            no_match = 100*(len(dtn_sorted) - len(idxa))/len(dtn_sorted)
            msg = no_match + "% of time stamps for " + item + " do not match"
            logger.warning(msg)
        labels = list(ds_dict[item].series.keys())
        if "DateTime" in labels:
            labels.remove("DateTime")
        for label in labels:
            var1 = pfp_utils.CreateEmptyVariable(label, nrecs)
            varn = pfp_utils.GetVariable(ds_dict[item], label)
            var1["Data"][idxa] = varn["Data"][idxb]
            var1["Flag"][idxa] = varn["Flag"][idxb]
            var1["Attr"] = varn["Attr"]
            pfp_utils.CreateVariable(ds, var1)
    return ds

def MergeHumidities(cf, ds, convert_units=False):
    if "Ah" not in cf["Variables"] and "RH" not in cf["Variables"] and "SH" not in cf["Variables"]:
        logger.error(" MergeHumidities: No humidities found in control file, returning ...")
        return
    if "Ah" in cf["Variables"]:
        if "MergeSeries" in cf["Variables"]["Ah"]:
            MergeSeries(cf, ds, "Ah", convert_units=convert_units)
            pfp_utils.CheckUnits(ds, "Ah", "g/m3", convert_units=True)
        elif "AverageSeries" in cf["Variables"]["Ah"]:
            AverageSeriesByElements(cf, ds, "Ah")
            pfp_utils.CheckUnits(ds, "Ah", "g/m3", convert_units=True)
    if "RH" in cf["Variables"]:
        if "MergeSeries" in cf["Variables"]["RH"]:
            MergeSeries(cf, ds, "RH", convert_units=convert_units)
            pfp_utils.CheckUnits(ds, "RH", "%", convert_units=True)
        elif "AverageSeries" in cf["Variables"]["RH"]:
            AverageSeriesByElements(cf, ds, "RH")
            pfp_utils.CheckUnits(ds, "RH", "%", convert_units=True)
    if "SH" in cf["Variables"]:
        if "MergeSeries" in cf["Variables"]["SH"]:
            MergeSeries(cf, ds, "SH", convert_units=convert_units)
            pfp_utils.CheckUnits(ds, "SH", "kg/kg", convert_units=True)
        elif "AverageSeries" in cf["Variables"]["SH"]:
            AverageSeriesByElements(cf, ds, "SH")
            pfp_utils.CheckUnits(ds, "SH", "kg/kg", convert_units=True)
    return

def MergeSeries(cf,ds,series,okflags=[0,10,20,30,40,50,60],convert_units=False,save_originals=False):
    """
    Purpose:
     Merge two series of data to produce one series containing the best data from both.
     If the QC flag for Primary is in okflags, the value from Primary is placed in destination.
     If the QC flag for Primary is not in okflags but the QC flag for Secondary is, the value
     from Secondary is placed in Destination.
    Usage:
     pfp_ts.MergeSeries(cf,ds,series,okflags=okflags.convert_units=False,save_originals=False)
         where ds is the data structure containing all series
               series (str) is the label of the destination series
               okflags (list) is a list of QC flag values for which the data is considered acceptable
               convert_units (boolean) if True, we will attempt to match units if they are not the same
               save_originals (boolean) it True, original series will be saved before merge
    Author: PRI
    Date: Back in the day
    History:
     16/7/2017 - made okflags optional, implemented save_originals
     30/10/2018 - rewrote to use pfp_utils.GetVariable()
    """
    # check to see if the series is specified in the control file
    section = pfp_utils.get_cfsection(cf, series)
    if section == None:
        return
    # check to see if the entry for series in the control file has the MergeSeries key
    if 'MergeSeries' not in cf[section][series].keys():
        return
    # check to see if the series has already been merged
    if series in ds.mergeserieslist: return
    # now get the source list and the standard name
    srclist = pfp_utils.GetMergeSeriesKeys(cf,series,section=section)
    nSeries = len(srclist)
    if nSeries==0:
        logger.warning(' MergeSeries: no input series specified for '+str(series))
        return
    if nSeries == 1:
        msg = ' Merging ' + str(srclist) + '==>' + series
        logger.info(msg)
        primary_series = srclist[0]
        if primary_series not in ds.series.keys():
            msg = "  MergeSeries: primary input series " + primary_series
            msg = msg + " not found for " + str(series)
            logger.warning(msg)
            return
        primary = pfp_utils.GetVariable(ds, primary_series)
        if (primary_series == series) and save_originals:
            tmp = pfp_utils.CopyVariable(primary)
            tmp["Label"] = tmp["Label"] + "_b4merge"
            pfp_utils.CreateVariable(ds, tmp)
        SeriesNameString = primary_series
    else:
        msg = " Merging " + str(srclist) + "==>" + series
        logger.info(msg)
        if srclist[0] not in ds.series.keys():
            msg = "  MergeSeries: primary input series " + srclist[0] + " not found for " + str(series)
            logger.warning(msg)
            return
        primary_series = srclist[0]
        if primary_series not in ds.series.keys():
            msg = "  MergeSeries: primary input series " + primary_series
            msg = msg + " not found for " + str(series)
            logger.warning(msg)
            return
        primary = pfp_utils.GetVariable(ds, primary_series)
        p_recs = len(primary["Data"])
        if (primary_series == series) and save_originals:
            tmp = pfp_utils.CopyVariable(primary)
            tmp["Label"] = tmp["Label"] + "_b4merge"
            pfp_utils.CreateVariable(ds, tmp)
        SeriesNameString = primary_series
        srclist.remove(primary_series)
        for secondary_series in srclist:
            if secondary_series in ds.series.keys():
                secondary = pfp_utils.GetVariable(ds, secondary_series)
                s_recs = len(secondary["Data"])
                if (secondary_series == series) and save_originals:
                    tmp = pfp_utils.CopyVariable(secondary)
                    tmp["Label"] = tmp["Label"] + "_b4merge"
                    pfp_utils.CreateVariable(ds, tmp)
                if secondary["Attr"]["units"] != primary["Attr"]["units"]:
                    msg = " " + secondary_series + " units don't match " + primary_series + " units"
                    logger.warning(msg)
                    if convert_units:
                        msg = " " + secondary_series + " units converted from "
                        msg = msg + secondary["Attr"]["units"] + " to " + primary["Attr"]["units"]
                        logger.info(msg)
                        secondary = pfp_utils.convert_units_func(ds, secondary, primary["Attr"]["units"])
                    else:
                        msg = " MergeSeries: " + secondary_series + " ignored"
                        logger.error(msg)
                        continue
                SeriesNameString = SeriesNameString + ", " + secondary_series
                p_idx = numpy.zeros(p_recs, dtype=numpy.int)
                s_idx = numpy.zeros(s_recs, dtype=numpy.int)
                for okflag in okflags:
                    # index of acceptable primary values
                    index = numpy.where(primary["Flag"] == okflag)[0]
                    # set primary index to 1 when primary good
                    p_idx[index] = 1
                    # same process for secondary
                    index = numpy.where(secondary["Flag"] == okflag)[0]
                    s_idx[index] = 1
                # index where primary bad but secondary good
                index = numpy.where((p_idx != 1 ) & (s_idx == 1))[0]
                # replace bad primary with good secondary
                primary["Data"][index] = secondary["Data"][index]
                primary["Flag"][index] = secondary["Flag"][index]
            else:
                msg = "  MergeSeries: secondary input series " + secondary_series + " not found"
                logger.warning(msg)
    ds.mergeserieslist.append(series)
    primary["Label"] = series
    primary["Attr"]["long_name"] += ", merged from " + SeriesNameString
    pfp_utils.CreateVariable(ds, primary)

def PT100(ds,T_out,R_in,m):
    logger.info(' Calculating temperature from PT100 resistance')
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    R,f,a = pfp_utils.GetSeriesasMA(ds,R_in)
    R = m*R
    T = (-c.PT100_alpha+numpy.sqrt(c.PT100_alpha**2-4*c.PT100_beta*(-R/100+1)))/(2*c.PT100_beta)
    attr = pfp_utils.MakeAttributeDictionary(long_name='Calculated PT100 temperature using '+str(R_in),units='degC')
    flag = numpy.where(numpy.ma.getmaskarray(T)==True,ones,zeros)
    pfp_utils.CreateSeries(ds,T_out,T,flag,attr)

def ReplaceRotatedCovariance(cf,ds,rot_cov_label,non_cov_label):
    logger.info(' Replacing missing '+rot_cov_label+' when '+non_cov_label+' is good')
    cr_data,cr_flag,cr_attr = pfp_utils.GetSeriesasMA(ds,rot_cov_label)
    cn_data,cn_flag,cn_attr = pfp_utils.GetSeriesasMA(ds,non_cov_label)
    index = numpy.where((numpy.ma.getmaskarray(cr_data)==True)&
                           (numpy.ma.getmaskarray(cn_data)==False))[0]
    #index = numpy.ma.where((numpy.ma.getmaskarray(cr_data)==True)&
                           #(numpy.ma.getmaskarray(cn_data)==False))[0]
    if len(index)!=0:
        ds.series[rot_cov_label]['Data'][index] = cn_data[index]
        ds.series[rot_cov_label]['Flag'][index] = numpy.int32(20)
    return

def RemoveIntermediateSeries(ds, info):
    """
    Purpose:
     Remove the alternate, solo, mds, climatology and composite variables
     from the L4 or L5 data structures.
    Usage:
    Side effects:
    Author: PRI
    Date: November 2018
    """
    iris = info["RemoveIntermediateSeries"]
    if iris["KeepIntermediateSeries"] == "Yes":
        return
    if "not_output" in iris:
        if len(iris["not_output"]) > 0:
            msg = " Removing intermediate series from data structure"
            logger.info(msg)
            for label in iris["not_output"]:
                if label in list(ds.series.keys()):
                    del ds.series[label]
            iris["not_output"] = []
    return

def ReplaceOnDiff(cf,ds,series=''):
    # Gap fill using data from alternate sites specified in the control file
    ts = ds.globalattributes['time_step']
    if len(series)!=0:
        ds_alt = {}                     # create a dictionary for the data from alternate sites
        open_ncfiles = []               # create an empty list of open netCDF files
        for ThisOne in series:          # loop over variables in the series list
            # has ReplaceOnDiff been specified for this series?
            if pfp_utils.incf(cf,ThisOne) and pfp_utils.haskey(cf,ThisOne,'ReplaceOnDiff'):
                # loop over all entries in the ReplaceOnDiff section
                for Alt in cf['Variables'][ThisOne]['ReplaceOnDiff'].keys():
                    if 'FileName' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                        alt_filename = cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['FileName']
                        if 'AltVarName' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            alt_varname = cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['AltVarName']
                        else:
                            alt_varname = ThisOne
                        if alt_filename not in open_ncfiles:
                            n = len(open_ncfiles)
                            open_ncfiles.append(alt_filename)
                            ds_alt[n] = pfp_io.nc_read_series(alt_filename)
                        else:
                            n = open_ncfiles.index(alt_filename)
                        if 'Transform' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            AltDateTime = ds_alt[n].series['DateTime']['Data']
                            AltSeriesData = ds_alt[n].series[alt_varname]['Data']
                            TList = ast.literal_eval(cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['Transform'])
                            for TListEntry in TList:
                                TransformAlternate(TListEntry,AltDateTime,AltSeriesData,ts=ts)
                        if 'Range' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            RList = ast.literal_eval(cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['Range'])
                            for RListEntry in RList:
                                ReplaceWhenDiffExceedsRange(ds.series['DateTime']['Data'],ds.series[ThisOne],
                                                            ds.series[ThisOne],ds_alt[n].series[alt_varname],
                                                            RListEntry)
                    elif 'AltVarName' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                        alt_varname = ThisOne
                        if 'Range' in cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt].keys():
                            RList = ast.literal_eval(cf['Variables'][ThisOne]['ReplaceOnDiff'][Alt]['Range'])
                            for RListEntry in RList:
                                ReplaceWhenDiffExceedsRange(ds.series['DateTime']['Data'],ds.series[ThisOne],
                                                            ds.series[ThisOne],ds.series[alt_varname],
                                                            RListEntry)
                    else:
                        logger.error('ReplaceOnDiff: Neither AltFileName nor AltVarName given in control file')
    else:
        logger.error('ReplaceOnDiff: No input series specified')

def ReplaceWhereMissing(Destination,Primary,Secondary,FlagOffset=None,FlagValue=None):
    p_data = Primary['Data'].copy()
    p_flag = Primary['Flag'].copy()
    s_data = Secondary['Data'].copy()
    s_flag = Secondary['Flag'].copy()
    if numpy.size(p_data)>numpy.size(s_data):
        p_data = p_data[0:numpy.size(s_data)]
    if numpy.size(s_data)>numpy.size(p_data):
        s_data = s_data[0:numpy.size(p_data)]
    index = numpy.where((abs(p_data-float(c.missing_value))<c.eps)&
                        (abs(s_data-float(c.missing_value))>c.eps))[0]
    p_data[index] = s_data[index]
    if FlagValue is None and FlagOffset is not None:
        p_flag[index] = s_flag[index] + numpy.int32(FlagOffset)
    elif FlagValue is not None and FlagOffset is None:
        p_flag[index] = numpy.int32(FlagValue)
    else:
        p_flag[index] = s_flag[index]
    Destination['Data'] = Primary['Data'].copy()
    Destination['Flag'] = Primary['Flag'].copy()
    Destination['Data'][0:len(p_data)] = p_data
    Destination['Flag'][0:len(p_flag)] = p_flag
    Destination['Attr']['long_name'] = 'Merged from original and alternate'
    Destination['Attr']['units'] = Primary['Attr']['units']

def ReplaceWhenDiffExceedsRange(DateTime,Destination,Primary,Secondary,RList):
    # get the primary data series
    p_data = numpy.ma.array(Primary['Data'])
    p_flag = Primary['Flag'].copy()
    # get the secondary data series
    s_data = numpy.ma.array(Secondary['Data'])
    s_flag = Secondary['Flag'].copy()
    # truncate the longest series if the sizes do not match
    if numpy.size(p_data)!=numpy.size(s_data):
        logger.warning(' ReplaceWhenDiffExceedsRange: Series lengths differ, longest will be truncated')
        if numpy.size(p_data)>numpy.size(s_data):
            p_data = p_data[0:numpy.size(s_data)]
        if numpy.size(s_data)>numpy.size(p_data):
            s_data = s_data[0:numpy.size(p_data)]
    # get the difference between the two data series
    d_data = p_data-s_data
    # normalise the difference if requested
    if RList[3]=='s':
        d_data = (p_data-s_data)/s_data
    elif RList[3]=='p':
        d_data = (p_data-s_data)/p_data
    #si = pfp_utils.GetDateIndex(DateTime,RList[0],0)
    #ei = pfp_utils.GetDateIndex(DateTime,RList[1],0)
    Range = RList[2]
    Upper = float(Range[0])
    Lower = float(Range[1])
    index = numpy.ma.where((abs(d_data)<Lower)|(abs(d_data)>Upper))
    p_data[index] = s_data[index]
    p_flag[index] = 35
    Destination['Data'] = numpy.ma.filled(p_data,float(c.missing_value))
    Destination['Flag'] = p_flag.copy()
    Destination['Attr']['long_name'] = 'Replaced original with alternate when difference exceeded threshold'
    Destination['Attr']['units'] = Primary['Attr']['units']

def savitzky_golay(y, window_size, order, deriv=0):
    ''' Apply Savitsky-Golay low-pass filter to data.'''
    try:
        window_size = numpy.abs(numpy.int(window_size))
        order = numpy.abs(numpy.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = numpy.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = numpy.linalg.pinv(b).A[deriv]
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - numpy.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + numpy.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = numpy.concatenate((firstvals, y, lastvals))
    return numpy.convolve( m, y, mode='valid')

def Square(Series):
    tmp = numpy.array([c.missing_value]*numpy.size(Series),Series.dtype)
    index = numpy.where(Series!=float(c.missing_value))[0]
    tmp[index] = Series[index] ** 2
    return tmp

def SquareRoot(Series):
    tmp = numpy.array([c.missing_value]*numpy.size(Series),Series.dtype)
    index = numpy.where(Series!=float(c.missing_value))[0]
    tmp[index] = Series[index] ** .5
    return tmp

def TaFromTv(cf,ds,Ta_out='Ta_SONIC_Av',Tv_in='Tv_SONIC_Av',Ah_in='Ah',RH_in='RH',q_in='SH',ps_in='ps'):
    # Calculate the air temperature from the virtual temperature, the
    # absolute humidity and the pressure.
    # NOTE: the virtual temperature is used in place of the air temperature
    #       to calculate the vapour pressure from the absolute humidity, the
    #       approximation involved here is of the order of 1%.
    logger.info(' Calculating Ta from Tv')
    # check to see if we have enough data to proceed
    # deal with possible aliases for the sonic temperature
    if Tv_in not in ds.series.keys():
        if "Tv_CSAT_Av" in ds.series.keys():
            Tv_in = "Tv_CSAT_Av"
            Ta_out = "Ta_CSAT_Av"
        elif "Tv_CSAT" in ds.series.keys():
            Tv_in = "Tv_CSAT"
            Ta_out = "Ta_CSAT"
        else:
            logger.error(" TaFromTv: sonic virtual temperature not found in data structure")
            return
    if Ah_in not in ds.series.keys() and RH_in not in ds.series.keys() and q_in not in ds.series.keys():
        labstr = str(Ah_in)+","+str(RH_in)+","+str(q_in)
        logger.error(" TaFromTv: no humidity data ("+labstr+") found in data structure")
        return
    if ps_in not in ds.series.keys():
        logger.error(" TaFromTv: pressure ("+str(ps_in)+") not found in data structure")
        return
    # we seem to have enough to continue
    Tv,f,a = pfp_utils.GetSeriesasMA(ds,Tv_in)
    ps,f,a = pfp_utils.GetSeriesasMA(ds,ps_in)
    if Ah_in in ds.series.keys():
        Ah,f,a = pfp_utils.GetSeriesasMA(ds,Ah_in)
        vp = pfp_mf.vapourpressure(Ah,Tv)
        mr = pfp_mf.mixingratio(ps,vp)
        q = pfp_mf.specifichumidity(mr)
    elif RH_in in ds.series.keys():
        RH,f,a = pfp_utils.GetSeriesasMA(ds,RH_in)
        q = pfp_mf.specifichumidityfromRH(RH,Tv,ps)
    elif q_in in ds.series.keys():
        q,f,a = pfp_utils.GetSeriesasMA(ds,q_in)
    Ta_data = pfp_mf.tafromtv(Tv,q)
    nRecs = int(ds.globalattributes['nc_nrecs'])
    Ta_flag = numpy.zeros(nRecs,numpy.int32)
    mask = numpy.ma.getmask(Ta_data)
    index = numpy.where(mask.astype(numpy.int32)==1)
    Ta_flag[index] = 15
    attr = pfp_utils.MakeAttributeDictionary(long_name='Ta calculated from Tv using '+Tv_in,units='C',standard_name='air_temperature')
    pfp_utils.CreateSeries(ds,Ta_out,Ta_data,Ta_flag,attr)

def TransformAlternate(TList,DateTime,Series,ts=30):
    # Apply polynomial transform to data series being used as replacement data for gap filling
    si = pfp_utils.GetDateIndex(DateTime,TList[0],ts=ts,default=0,match='exact')
    ei = pfp_utils.GetDateIndex(DateTime,TList[1],ts=ts,default=-1,match='exact')
    Series = numpy.ma.masked_where(abs(Series-float(c.missing_value))<c.eps,Series)
    Series[si:ei] = pfp_utils.polyval(TList[2],Series[si:ei])
    Series = numpy.ma.filled(Series,float(c.missing_value))
