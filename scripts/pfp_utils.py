# the following line needed for unicode character in convert_anglestring
# -*- coding: latin-1 -*-
import ast
import constants as c
import copy
import datetime
import dateutil
import logging
import math
import meteorologicalfunctions as mf
import netCDF4
import numbers
import numpy
import os
import platform
import pytz
import sys
import time
import Tkinter,tkSimpleDialog
import xlrd
import xlwt

logger = logging.getLogger("pfp_log")

def bp(fx,tao):
    """
    Function to calculate the b and p coeficients of the Massman frequency correction.
    """
    bp = 2 * c.Pi * fx * tao
    return bp

def bisection(array,value):
    '''Given an ``array`` , and given a ``value`` , returns an index j such that ``value`` is between array[j]
    and array[j+1]. ``array`` must be monotonic increasing. j=-1 or j=len(array) is returned
    to indicate that ``value`` is out of range below and above respectively.
    Stolen from https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array/2566508'''
    n = len(array)
    if (value < array[0]):
        return -1
    elif (value > array[n-1]):
        return n
    jl = 0# Initialize lower
    ju = n-1# and upper limits.
    while (ju-jl > 1):# If we are not yet done,
        jm=(ju+jl) >> 1# compute a midpoint with a bitshift
        if (value >= array[jm]):
            jl=jm# and replace either the lower limit
        else:
            ju=jm# or the upper limit, as appropriate.
        # Repeat until the test condition is satisfied.
    if (value == array[0]):# edge cases at bottom
        return 0
    elif (value == array[n-1]):# and top
        return n-1
    else:
        return jl

def cfkeycheck(cf,Base='Variables',ThisOne=[],key=[]):
    if len(ThisOne) == 0:
        return
    if len(key) == 0:
        if Base in cf.keys() and ThisOne in cf[Base].keys():
            return ThisOne in cf[Base].keys()
        else:
            return
    else:
        if Base in cf.keys() and ThisOne in cf[Base].keys():
            return key in cf[Base][ThisOne].keys()
        else:
            return

def cfoptionskeylogical(cf,Key='',default=False):
    if 'Options' in cf:
        if Key in cf['Options']:
            returnValue = cf.get('Options').as_bool(Key)
            #if str(cf['Options'][Key]).lower()=="true" or str(cf['Options'][Key]).lower()=="yes":
                #returnValue = True
            #else:
                #returnValue = False
        else:
            returnValue = default
    else:
        returnValue = default
    return returnValue

def CheckQCFlags(ds):
    """
    Purpose:
     Make sure that all values of -9999 in a data series have a non-zero QC flag value.
    Usage:
     pfp_utils.CheckQCFlags(ds)
    Author: PRI
    Date: August 2014
    """
    msg = " Checking missing data and QC flags are consistent"
    logger.info(msg)
    labels = [label for label in ds.series.keys() if label not in ["DateTime"]]
    # force any values of -9999 with QC flags of 0 to have a QC flag of 8
    for label in labels:
        var = GetVariable(ds, label)
        condition = numpy.ma.getmaskarray(var["Data"]) & (numpy.mod(var["Flag"],10) == 0)
        idx = numpy.ma.where(condition == True)[0]
        if len(idx)!=0:
            msg = " "+label+": "+str(len(idx))+" missing values with flag = 0 (forced to 8)"
            logger.warning(msg)
            var["Flag"][idx] = numpy.int32(8)
            CreateVariable(ds, var)
    # force all values != -9999 to have QC flag = 0, 10, 20 etc
    nRecs = int(ds.globalattributes["nc_nrecs"])
    for label in labels:
        var = GetVariable(ds, label)
        condition = (numpy.ma.getmaskarray(var["Data"]) == False) & (numpy.mod(var["Flag"],10) != 0)
        idx = numpy.where(condition == True)[0]
        if len(idx)!=0:
            msg = " "+label+": "+str(len(idx))+" non-missing values with flag != 0"
            logger.warning(msg)
            #ds.series[label]["Data"][idx] = numpy.float64(c.missing_value)
    return

def CheckTimeStep(ds):
    """
    Purpose:
     Checks the datetime series in the data structure ds to see if there are
     any missing time stamps.
     This function returns a logical variable that is true if any gaps exist
     in the time stamp.
    Useage:
     has_gaps = CheckTimeSTep(ds)
     if has_gaps:
         <do something about missing time stamps>
    Author: PRI
    Date: April 2013
    """
    # set the has_gaps logical
    has_gaps = False
    # get the number of records
    nRecs = int(ds.globalattributes["nc_nrecs"])
    # get the time step
    ts = int(ds.globalattributes["time_step"])
    # time step between records in seconds
    dt = get_timestep(ds)
    # indices of elements where time step not equal to default
    index = numpy.where(dt!=ts*60)[0]
    # check to see if ww have any time step problems
    if len(index)!=0:
        has_gaps = True
        logger.warning(" CheckTimeStep: "+str(len(index))+" problems found with the time stamp")
    return has_gaps

def CheckUnits(ds, label, units, convert_units=False):
    """
    Purpose:
     General units checking and conversion.
    Usage:
     pfp_utils.CheckUnits(ds,label,units,convert_units=True)
     where ds is a data structure
           label (string) is the label of the series for which the units
                          are to be checked
           units (string) is the required units
           convert_units (logical, optional) is True to force conversion to
                        required units
    Author: PRI
    Date: January 2016
    """
    if isinstance(label, basestring):
        label_list = [label]
    elif isinstance(label, list):
        label_list = label
    else:
        msg = " CheckUnits: input label "+label+" must be a string or a list"
        logger.error(msg)
        return
    for label in label_list:
        if label not in ds.series.keys():
            msg = "CheckUnits: requested series "+label+" not found"
            logger.error(msg)
            continue
        variable = GetVariable(ds, label)
        if variable["Attr"]["units"] != units and convert_units:
            msg = " Units for "+label+" converted from "+variable["Attr"]["units"]+" to "+units
            logger.info(msg)
            variable = convert_units_func(ds, variable, units)
            CreateVariable(ds, variable)
        else:
            if not convert_units:
                msg = " Units mismatch but conversion disabled"
                logger.warning(msg)
    return

def contiguous_regions(condition):
    """
    Purpose:
     Finds contiguous True regions of the boolean array "condition". Returns
     a 2D array where the first column is the start index of the region and the
     second column is the end index.
    Author: Joe Kington (via StackOverflow)
    Date: September 2014
    """
    # Find the indicies of changes in "condition"
    d = numpy.diff(condition)
    idx, = d.nonzero()
    # We need to start things after the change in "condition". Therefore,
    # we'll shift the index by 1 to the right.
    idx += 1
    if condition[0]:
        # If the start of condition is True prepend a 0
        idx = numpy.r_[0, idx]
    if condition[-1]:
        # If the end of condition is True, append the length of the array
        idx = numpy.r_[idx, condition.size] # Edit
    # Reshape the result into two columns
    idx.shape = (-1,2)
    return idx

def ConvertCO2Units(cf, ds, CO2='CO2'):
    CO2_units_out = "mg/m3"            # default value
    CO2_units_in = ds.series[CO2]['Attr']['units']
    if 'Options' in cf:
        if 'CO2Units' in cf['Options']:
            CO2_units_out = str(cf['Options']['CO2Units'])
    if CO2_units_out!=CO2_units_in:
        logger.info(' Converting CO2 concentration from '+CO2_units_in+' to '+CO2_units_out)
        if CO2_units_out=="umol/mol" and CO2_units_in=="mg/m3":
            c_mgpm3,flag,attr = GetSeriesasMA(ds,CO2)
            T,f,a = GetSeriesasMA(ds,'Ta')
            p,f,a = GetSeriesasMA(ds,'ps')
            c_ppm = mf.co2_ppmfrommgpm3(c_mgpm3,T,p)
            attr["long_name"] = attr["long_name"]+", converted to umol/mol"
            attr["units"] = CO2_units_out
            attr["standard_name"] = "mole_concentration_of_carbon_dioxide_in_air"
            CreateSeries(ds,CO2,c_ppm,flag,attr)
        elif CO2_units_out=="mg/m3" and CO2_units_in=="umol/mol":
            c_ppm,flag,attr = GetSeriesasMA(ds,CO2)
            T,f,a = GetSeriesasMA(ds,'Ta')
            p,f,a = GetSeriesasMA(ds,'ps')
            c_mgpm3 = mf.co2_mgpm3fromppm(c_ppm,T,p)
            attr["long_name"] = attr["long_name"]+", converted to mg/m3"
            attr["units"] = CO2_units_out
            attr["standard_name"] = "mass_concentration_of_carbon_dioxide_in_air"
            CreateSeries(ds,CO2,c_mgpm3,flag,attr)
        else:
            logger.info('  ConvertCO2Units: input or output units for CO2 concentration not recognised')
    else:
        logger.info(" CO2 concentration already in requested units")

def ConvertFcUnits(cf, ds):
    """
    Purpose:
     Convert CO2 flux units as required.
    Usage:
    Side effects:
     The units of any CO2 flux in the data structure are converted to the units specified
     in the [Options] section of the control file.
    Author: PRI
    Date: Back in the day
    """
    if 'Options' not in cf:
        return
    if 'FcUnits' not in cf['Options']:
        return
    # get the Fc units requested by the user
    Fc_units_out = get_keyvaluefromcf(cf, ['Options'], "FcUnits", default="umol/m2/s")
    # get a list of Fc series
    Fc_list = [label for label in ds.series.keys() if label[0:2] == "Fc"]
    # convert units of Fc as required
    units_list = ["mg/m2/s", "umol/m2/s"]
    for label in Fc_list:
        # get the Fc variable
        Fc = GetVariable(ds, label)
        # check the units, we only operate on what we know (LBYL)
        if Fc["Attr"]["units"] not in units_list:
            Fc_list.remove(label)
            continue
        Fc_units_in = Fc["Attr"]["units"]
        # check to see if we need to convert units
        if Fc_units_in == Fc_units_out:
            # nothing to see here, folks
            continue
        # if we get here, we need to convert units
        logger.info(" Converting "+label+" from "+Fc_units_in+" to "+Fc_units_out)
        if Fc_units_out == "umol/m2/s" and Fc_units_in == "mg/m2/s":
            Fc["Data"] = mf.Fc_umolpm2psfrommgpm2ps(Fc["Data"])
            Fc["Attr"]["long_name"] = Fc["Attr"]["long_name"]+", converted to umol/m2/s"
            Fc["Attr"]["units"] = Fc_units_out
            #attr["standard_name"] = "surface_upward_mole_flux_of_carbon_dioxide"
            CreateVariable(ds, Fc)
        elif Fc_units_out == "mg/m2/s" and Fc_units_in == "umol/m2/s":
            Fc["Data"] = mf.Fc_mgpm2psfromumolpm2ps(Fc["Data"])
            Fc["Attr"]["long_name"] = Fc["Attr"]["long_name"]+", converted to mg/m2/s"
            Fc["Attr"]["units"] = Fc_units_out
            #attr["standard_name"] = "not defined"
            CreateVariable(ds, Fc)
        else:
            logger.info('  ConvertFcUnits: input or output units for Fc unrecognised')
    return

def convert_units_func(ds, variable, new_units, mode="quiet"):
    """
    Purpose:
     Generic routine for changing units.
     Nothing is done if the original units are the same as the requested units.
    Usage:
     new_data = pfp_utils.convert_units_func(old_data,old_units,new_units)
     where old_data is a 1D array of data in the original units
           old_units are the units of the original data
           new_units are the units of the new data
           ts is the time step
    Author: PRI
    Date: July 2015
    """
    old_units = variable["Attr"]["units"]
    if old_units == new_units:
        # old units same as new units, nothing to do ...
        return
    # check the units are something we understand
    # add more lists here to cope with water etc
    co2_list = ["umol/m2/s","gC/m2","mg/m3","mgCO2/m3","umol/mol","mg/m2/s","mgCO2/m2/s"]
    h2o_list = ["g/m3", "mmol/mol", "%", "frac", "kg/kg"]
    t_list = ["C", "K"]
    ps_list = ["Pa", "hPa", "kPa"]
    ok_list = co2_list+h2o_list+t_list+ps_list
    # parse the original units
    if old_units not in ok_list:
        if "Label" in variable:
            label = variable["Label"]
        else:
            label = "quantity provided"
        msg = " Unrecognised units ("+old_units+") in "+label
        logger.error(msg)
    elif new_units not in ok_list:
        msg = " Unrecognised units requested ("+new_units+")"
        logger.error(msg)
    elif new_units in co2_list:
        if old_units in co2_list:
            variable = convert_units_co2(ds, variable, new_units)
        else:
            msg = " New units ("+new_units+") not compatible with old ("+old_units+")"
            logger.error(msg)
    elif new_units in h2o_list:
        if old_units in h2o_list:
            variable = convert_units_h2o(ds, variable, new_units)
        else:
            msg = " New units ("+new_units+") not compatible with old ("+old_units+")"
            logger.error(msg)
    elif new_units in t_list:
        if old_units in t_list:
            variable = convert_units_t(ds, variable, new_units)
        else:
            msg = " New units ("+new_units+") not compatible with old ("+old_units+")"
            logger.error(msg)
    elif new_units in ps_list:
        if old_units in ps_list:
            variable = convert_units_ps(ds, variable, new_units)
        else:
            msg = " New units ("+new_units+") not compatible with old ("+old_units+")"
            logger.error(msg)
    else:
        msg = "Unrecognised units combination "+old_units+" and "+new_units
        logger.error(msg)

    return variable

def convert_units_co2(ds, variable, new_units):
    """
    Purpose:
     General purpose routine to convert from one set of CO2 concentration units
     to another.
     Conversions supported are:
      umol/m2/s to gC/m2 (per time step)
      gC/m2 (per time step) to umol/m2/s
      mg/m3 to umol/mol
      mgCO2/m3 to umol/mol
      umol/mol to mg/m3
      mg/m2/s to umol/m2/s
      mgCO2/m2/s to umol/m2/s
    Usage:
     new_data = pfp_utils.convert_units_co2(ds, variable, new_units)
      where ds is a data structure
            variable (dictionary) is a variable dictionary
            new_units (string) is the new units
    Author: PRI
    Date: January 2016
    """
    # get the current units and the timestep
    old_units = variable["Attr"]["units"]
    ts = variable["time_step"]
    # default values for the valid_range minimum and maximum
    valid_range_minimum = -1E35
    valid_range_maximum = 1E35
    # now check the units and see what we have to convert
    if old_units=="umol/m2/s" and new_units=="gC/m2":
        # convert the data
        variable["Data"] = variable["Data"]*12.01*ts*60/1E6
        # update the range check limits in the variable attribute
        # this one is easy because it is a simple numerical change
        for attr in ["rangecheck_lower", "rangecheck_upper"]:
            if attr in variable["Attr"]:
                attr_limit = numpy.array(parse_rangecheck_limits(variable["Attr"][attr]))
                attr_limit = attr_limit*12.01*ts*60/1E6
                variable["Attr"][attr] = list(attr_limit)
                if attr == "rangecheck_lower":
                    valid_range_minimum = numpy.amin(attr_limit)
                elif attr == "rangecheck_upper":
                    valid_range_maximum = numpy.amax(attr_limit)
                else:
                    # we shouldn't get here
                    msg = "convert_units_co2: unexpected option for attr ("+attr+")"
                    logger.error(msg)
                    continue
        # is the valid_range attribute defined for this variable?
        if "valid_range" in variable["Attr"]:
            # if so, then update it
            variable["Attr"]["valid_range"] = str(valid_range_minimum)+","+str(valid_range_maximum)
        # update the variable attributes to the new units
        variable["Attr"]["units"] = new_units
    elif old_units=="gC/m2" and new_units=="umol/m2/s":
        # convert the data
        variable["Data"] = variable["Data"]*1E6/(12.01*ts*60)
        # update the range check limits in the variable attribute
        # this one is easy because it is a simple numerical change
        for attr in ["rangecheck_lower", "rangecheck_upper"]:
            if attr in variable["Attr"]:
                attr_limit = numpy.array(parse_rangecheck_limits(variable["Attr"][attr]))
                attr_limit = attr_limit*1E6/(12.01*ts*60)
                variable["Attr"][attr] = list(attr_limit)
                if attr == "rangecheck_lower":
                    valid_range_minimum = numpy.amin(attr_limit)
                elif attr == "rangecheck_upper":
                    valid_range_maximum = numpy.amax(attr_limit)
                else:
                    # we shouldn't get here
                    msg = "convert_units_co2: unexpected option for attr ("+attr+")"
                    logger.error(msg)
                    continue
        # is the valid_range attribute defined for this variable?
        if "valid_range" in variable["Attr"]:
            # if so, then update it
            variable["Attr"]["valid_range"] = str(valid_range_minimum)+","+str(valid_range_maximum)
        # update the variable attributes to the new units
        variable["Attr"]["units"] = new_units
    elif old_units in ["mg/m3", "mgCO2/m3"] and new_units=="umol/mol":
        # convert the data
        Ta = GetVariable(ds, "Ta")
        ps = GetVariable(ds, "ps")
        Ta_def = numpy.full(12, numpy.ma.mean(Ta["Data"]))
        ps_def = numpy.full(12, numpy.ma.mean(ps["Data"]))
        variable["Data"] = mf.co2_ppmfrommgpm3(variable["Data"], Ta["Data"], ps["Data"])
        # update the range check limits in the variable attribute
        # this one is more complicated because it involves temperature and pressure
        for attr in ["rangecheck_lower", "rangecheck_upper"]:
            if attr in variable["Attr"]:
                # get the list of monthly maxima or minima
                limit_list = parse_rangecheck_limits(variable["Attr"][attr])
                # get an array of default conversions using mean temperature and pressure
                attr_limit = mf.co2_ppmfrommgpm3(numpy.array(limit_list), Ta_def, ps_def)
                # now loop over each month and get the maxima (rangecheck_lower) or minima
                # (rangecheck_upper) depending on the actual temperature and pressure
                for m, item in enumerate(limit_list):
                    month = m + 1
                    # get an index of the months
                    idx = numpy.where(ds.series["Month"]==month)[0]
                    # move on to next month if this one not in data
                    if len(idx) == 0:
                        continue
                    # get an array with the limit value for this month
                    data = numpy.full(len(idx), limit_list[m])
                    # convert the limit to new units
                    limit = mf.co2_ppmfrommgpm3(data, Ta["Data"][idx], ps["Data"][idx])
                    # set the appropriate element of the attr_limit array
                    if attr == "rangecheck_lower":
                        # take the maximum of the rangecheck_lower values
                        attr_limit[m] = numpy.ma.max(limit)
                    elif attr == "rangecheck_upper":
                        # take the minimum of the rangecheck_upper values
                        attr_limit[m] = numpy.ma.min(limit)
                    else:
                        # we shouldn't get here
                        msg = "convert_units_co2: unexpected option for attr ("+attr+")"
                        logger.error(msg)
                        continue
                # update the variable attribute with the converted limits
                variable["Attr"][attr] = list(attr_limit)
                # get the absolute minimum and maximum for the valid_range attribute
                if attr == "rangecheck_lower":
                    valid_range_minimum = numpy.amin(attr_limit)
                elif attr == "rangecheck_upper":
                    valid_range_maximum = numpy.amax(attr_limit)
                else:
                    # we shouldn't get here
                    msg = "convert_units_co2: unexpected option for attr ("+attr+")"
                    logger.error(msg)
                    continue
        if "valid_range" in variable["Attr"]:
            variable["Attr"]["valid_range"] = str(valid_range_minimum)+","+str(valid_range_maximum)
        # update the variable attributes to the new units
        variable["Attr"]["units"] = new_units
    elif old_units=="umol/mol" and new_units in ["mg/m3","mgCO2/m3"]:
        Ta = GetVariable(ds, "Ta")
        ps = GetVariable(ds, "ps")
        Ta_def = numpy.full(12, numpy.ma.mean(Ta["Data"]))
        ps_def = numpy.full(12, numpy.ma.mean(ps["Data"]))
        variable["Data"] = mf.co2_mgpm3fromppm(variable["Data"], Ta["Data"], ps["Data"])
        # update the range check limits in the variable attribute
        # this one is more complicated because it involves temperature and pressure
        for attr in ["rangecheck_lower", "rangecheck_upper"]:
            if attr in variable["Attr"]:
                # get the list of monthly maxima or minima
                limit_list = parse_rangecheck_limits(variable["Attr"][attr])
                # get an array of default conversions using mean temperature and pressure
                attr_limit = mf.co2_mgpm3fromppm(numpy.array(limit_list), Ta_def, ps_def)
                # now loop over each month and get the maxima (rangecheck_lower) or minima
                # (rangecheck_upper) depending on the actual temperature and pressure
                for m, item in enumerate(limit_list):
                    month = m + 1
                    # get an index of the months
                    idx = numpy.where(ds.series["Month"]==month)[0]
                    # move on to next month if this one not in data
                    if len(idx) == 0:
                        continue
                    # get an array with the limit value for this month
                    data = numpy.full(len(idx), limit_list[m])
                    # convert the limit to new units
                    limit = mf.co2_mgpm3fromppm(data, Ta["Data"][idx], ps["Data"][idx])
                    # set the appropriate element of the attr_limit array
                    if attr == "rangecheck_lower":
                        # take the maximum of the rangecheck_lower values
                        attr_limit[m] = numpy.ma.max(limit)
                    elif attr == "rangecheck_upper":
                        # take the minimum of the rangecheck_upper values
                        attr_limit[m] = numpy.ma.min(limit)
                    else:
                        # we shouldn't get here
                        msg = "convert_units_co2: unexpected option for attr ("+attr+")"
                        logger.error(msg)
                        continue
                # update the variable attribute with the converted limits
                variable["Attr"][attr] = list(attr_limit)
                # get the absolute minimum and maximum for the valid_range attribute
                if attr == "rangecheck_lower":
                    valid_range_minimum = numpy.amin(attr_limit)
                elif attr == "rangecheck_upper":
                    valid_range_maximum = numpy.amax(attr_limit)
                else:
                    # we shouldn't get here
                    msg = "convert_units_co2: unexpected option for attr ("+attr+")"
                    logger.error(msg)
                    continue
        if "valid_range" in variable["Attr"]:
            variable["Attr"]["valid_range"] = str(valid_range_minimum)+","+str(valid_range_maximum)
        # update the variable attributes to the new units
        variable["Attr"]["units"] = new_units
    elif old_units in ["mg/m2/s","mgCO2/m2/s"] and new_units=="umol/m2/s":
        # convert the data
        variable["Data"] = mf.Fc_umolpm2psfrommgpm2ps(variable["Data"])
        # update the range check limits in the variable attribute
        # this one is easy because it is a simple numerical change
        for attr in ["rangecheck_lower", "rangecheck_upper"]:
            if attr in variable["Attr"]:
                attr_limit = numpy.array(parse_rangecheck_limits(variable["Attr"][attr]))
                attr_limit = mf.Fc_umolpm2psfrommgpm2ps(attr_limit)
                variable["Attr"][attr] = list(attr_limit)
                if attr == "rangecheck_lower":
                    valid_range_minimum = numpy.amin(attr_limit)
                elif attr == "rangecheck_upper":
                    valid_range_maximum = numpy.amax(attr_limit)
                else:
                    # we shouldn't get here
                    msg = "convert_units_co2: unexpected option for attr ("+attr+")"
                    logger.error(msg)
                    continue
        # is the valid_range attribute defined for this variable?
        if "valid_range" in variable["Attr"]:
            # if so, then update it
            variable["Attr"]["valid_range"] = str(valid_range_minimum)+","+str(valid_range_maximum)
        # update the variable attributes to the new units
        variable["Attr"]["units"] = new_units
    else:
        msg = " Unrecognised conversion from "+old_units+" to "+new_units
        logger.error(msg)

    return variable

def convert_units_h2o(ds, variable, new_units):
    """
    Purpose:
     General purpose routine to convert from one set of H2O concentration units
     to another.
     Conversions supported are:
      g/m3 to mmol/mol
      mmol/mol to g/m3
    Usage:
     new_data = pfp_utils.convert_units_h2o(ds, variable, new_units)
      where ds is a data structure
            variable (dictionary) is a variable dictionary
            new_units (string) is the new units
    Author: PRI
    Date: January 2016
    """
    ts = int(ds.globalattributes["time_step"])
    if old_units=="mmol/mol" and new_units=="g/m3":
        Ta,f,a = GetSeriesasMA(ds,"Ta")
        ps,f,a = GetSeriesasMA(ds,"ps")
        new_data = mf.h2o_gpm3frommmolpmol(old_data,Ta,ps)
    elif old_units=="g/m3" and new_units=="mmol/mol":
        Ta,f,a = GetSeriesasMA(ds,"Ta")
        ps,f,a = GetSeriesasMA(ds,"ps")
        new_data = mf.h2o_mmolpmolfromgpm3(old_data,Ta,ps)
    elif old_units=="frac" and new_units=="%":
        new_data = old_data*float(100)
    elif old_units=="%" and new_units=="frac":
        new_data = old_data/float(100)
    else:
        msg = " Unrecognised conversion from "+old_units+" to "+new_units
        logger.error(msg)
        new_data = numpy.ma.array(old_data,copy=True,mask=True)
    return new_data

def convert_units_t(ds, var_in, new_units):
    """
    Purpose:
     General purpose routine to convert from one set of temperature units
     to another.
     Conversions supported are:
      C to K
      K to C
    Usage:
     new_data = pfp_utils.convert_units_t(ds, variable, new_units)
      where ds is a data structure
            variable is a variable dictionary (pfp_utils.GetVariable())
            new_units (string) is the new units
    Author: PRI
    Date: January 2016
    """
    var_out = copy.deepcopy(var_in)
    ts = int(ds.globalattributes["time_step"])
    if var_in["Attr"]["units"] == "C" and new_units == "K":
        var_out["Data"] = var_in["Data"] + c.C2K
        var_out["Attr"]["units"] = "K"
    elif var_in["Attr"]["units"] == "K" and new_units == "C":
        var_out["Data"] = var_in["Data"] - c.C2K
        var_out["Attr"]["units"] = "C"
    else:
        msg = " Unrecognised conversion from "+var_in["Attr"]["units"]+" to "+new_units
        logger.error(msg)
    return var_out

def convert_units_ps(ds, var_in, new_units):
    """
    Purpose:
     General purpose routine to convert from one set of pressure units
     to another.
     Conversions supported are:
      Pa to kPa
      hPa to kPa
    Usage:
     new_data = pfp_utils.convert_units_ps(ds, variable, new_units)
      where ds is a data structure
            variable is a variable dictionary (pfp_utils.GetVariable())
            new_units (string) is the new units
    Author: PRI
    Date: February 2018
    """
    var_out = copy.deepcopy(var_in)
    ts = int(ds.globalattributes["time_step"])
    if var_in["Attr"]["units"] == "Pa" and new_units == "kPa":
        var_out["Data"] = var_in["Data"]/float(1000)
        var_out["Attr"]["units"] = "kPa"
    elif var_in["Attr"]["units"] == "hPa" and new_units == "kPa":
        var_out["Data"] = var_in["Data"]/float(10)
        var_out["Attr"]["units"] = "kPa"
    else:
        msg = " Unrecognised conversion from "+var_in["Attr"]["units"]+" to "+new_units
        logger.error(msg)
    return var_out

def convert_anglestring(anglestring):
    """
    Purpose:
     Attempt to convert an angle string to a float.
    Usage:
     a = pfp_utils.convert_anglestring(astr)
     Acceptable input formats:
      astr = '''34 12' 24" S'''
      astr = '''34 12 24S'''
      astr = '''34 12'24.123"S''
      astr = '''34.123 S'''
      astr = '''-34.123'''
    """
    quadlist=["N","E","S","W"]
    direction = {'N':1, 'S':-1, 'E': 1, 'W':-1}
    try:
        # simple casting may work, who knows?
        return float(anglestring)
    except ValueError:
        # replace the degrees, minutes and seconds symbols with spaces
        new = anglestring.replace(u'\B0',' ').replace('\'',' ').replace('"',' ')
        # check there is a space between the quadrant letter (assumed to be one of N, E, W or S)
        # and the next character to the left
        # find out which of N, E, S, or W is in the string
        for item in quadlist:
            if item in new: quadletter=item
        # now get the index of this character in the string
        i=new.index(quadletter)
        # check that the next character to the left is a space character
        if new[i-1] != " ": new = new[0:i]+" "+new[i:]
        # now split the string on space characters
        new = new.split()
        # get the quadrant letter
        new_dir = new.pop()
        # make sure we have 3 parts
        new.extend([0,0,0])
        # return with the string converted to a float
        return (float(new[0])+float(new[1])/60.0+float(new[2])/3600.0) * direction[new_dir]

def convert_WSWDtoUV(WS, WD):
    """
    Purpose:
     Convert wind speed and direction to U and V conponents.
     This routine follows the meteorological convention:
      - wind direction is positive going clockwise from north
      - U is positive towards east
      - V is positive towards north
    Usage:
     U, V = pfp_utils.convert_WSWDtoUV(WS, WD)
    Author: PRI
    Date: February 2015
    """
    nrecs = len(WS["Data"])
    # create variables of 1s and 0s for QC flags
    f0 = numpy.zeros(nrecs, dtype=numpy.int32)
    f1 = numpy.ones(nrecs, dtype=numpy.int32)
    # create empty variables for U and V
    U = create_empty_variable("u", nrecs)
    V = create_empty_variable("v", nrecs)
    # get the components from the wind speed and direction
    U["Data"] = -WS["Data"]*numpy.sin(numpy.radians(WD["Data"]))
    V["Data"] = -WS["Data"]*numpy.cos(numpy.radians(WD["Data"]))
    # set components to 0 when WS is less than 0.01
    U["Data"] = numpy.ma.where(WS["Data"] < 0.01, numpy.float64(0), U["Data"])
    V["Data"] = numpy.ma.where(WS["Data"] < 0.01, numpy.float64(0), V["Data"])
    # now set the QC flag
    U["Flag"] = numpy.where(numpy.ma.getmaskarray(U["Data"]) == True, f1, f0)
    V["Flag"] = numpy.where(numpy.ma.getmaskarray(V["Data"]) == True, f1, f0)
    # update the variable attributes
    U["Attr"]["long_name"] = "U component of wind velocity, positive east"
    U["Attr"]["units"] = "m/s"
    V["Attr"]["long_name"] = "V component of wind velocity, positive north"
    V["Attr"]["units"] = "m/s"
    # copy the datetime if it is available
    if "DateTime" in WS.keys():
        U["DateTime"] = copy.deepcopy(WS["DateTime"])
        V["DateTime"] = copy.deepcopy(WS["DateTime"])
    elif "DateTime" in WD.keys():
        U["DateTime"] = copy.deepcopy(WD["DateTime"])
        V["DateTime"] = copy.deepcopy(WD["DateTime"])
    return U, V

def convert_UVtoWSWD(U, V):
    """
    Purpose:
     Convert U and V conponents to wind speed and direction
     This routine follows the meteorological convention:
      - wind direction is positive going clockwise from north
      - U is positive towards east
      - V is positive towards north
    Usage:
     WS, WD = pfp_utils.convert_UVtoWSWD(U, V)
    Author: PRI
    Date: February 2015
    """
    nrecs = len(U["Data"])
    # create variables of 1s and 0s for QC flags
    f0 = numpy.zeros(nrecs)
    f1 = numpy.ones(nrecs)
    # create empty variables for WS and WD
    WS = create_empty_variable("Ws", nrecs)
    WD = create_empty_variable("Wd", nrecs)
    # get the wind speed and direction from the components
    WD["Data"] = float(270) - (numpy.degrees(numpy.ma.arctan2(V["Data"], U["Data"])))
    WD["Data"] = numpy.ma.mod(WD["Data"], 360)
    WS["Data"] = numpy.ma.sqrt(U["Data"]*U["Data"] + V["Data"]*V["Data"])
    # mask WD when the WS is less than 0.01
    WD["Data"] = numpy.ma.masked_where(WS["Data"] < 0.01, WD["Data"])
    # now set the QC flag
    WS["Flag"] = numpy.where(numpy.ma.getmaskarray(WS["Data"]) == True, f1, f0)
    WD["Flag"] = numpy.where(numpy.ma.getmaskarray(WD["Data"]) == True, f1, f0)
    # update the variable attributes
    WS["Attr"]["long_name"] = "Wind speed"
    WS["Attr"]["units"] = "m/s"
    WD["Attr"]["long_name"] = "Wind direction"
    WD["Attr"]["units"] = "deg"
    # copy the datetime if it is available
    if "DateTime" in U.keys():
        WS["DateTime"] = copy.deepcopy(U["DateTime"])
        WD["DateTime"] = copy.deepcopy(U["DateTime"])
    elif "DateTime" in V.keys():
        WS["DateTime"] = copy.deepcopy(V["DateTime"])
        WD["DateTime"] = copy.deepcopy(V["DateTime"])
    return WS, WD

def CreateSeries(ds,Label,Data,Flag,Attr):
    """
    Purpose:
     Create a series (1d array) of data in the data structure.
     If the series already exists in the data structure, data values and QC flags will be
     overwritten but attributes will be preserved.  However, the long_name and units attributes
     are treated differently.  The existing long_name will have long_name appended to it.  The
     existing units will be overwritten with units.
     This utility is the prefered method for creating or updating a data series because
     it implements a consistent method for creating series in the data structure.  Direct
     writes to the contents of the data structure are discouraged (unless PRI wrote the code:=P).
    Usage:
     Fsd,flag,attr = pfp_utils.GetSeriesasMA(ds,"Fsd")
      ... do something to Fsd here ...
     pfp_utils.CreateSeries(ds,"Fsd",Fsd,flag,attr)
    Author: PRI
    Date: Back in the day
    """
    ds.series['_tmp_'] = {}                       # create a temporary series to avoid premature overwrites
    # put the data into the temporary series
    if numpy.ma.isMA(Data):
        ds.series['_tmp_']['Data'] = numpy.ma.filled(Data,float(c.missing_value))
    else:
        ds.series['_tmp_']['Data'] = numpy.array(Data)
    # copy or make the QC flag
    if Flag is None:
        ds.series['_tmp_']['Flag'] = MakeQCFlag(ds,FList)
    else:
        ds.series['_tmp_']['Flag'] = Flag.astype(numpy.int32)
    # do the attributes
    ds.series['_tmp_']['Attr'] = {}
    if Label in ds.series.keys():                 # check to see if the series already exists
        for attr in ds.series[Label]['Attr']:     # if it does, copy the existing attributes
            if attr in Attr and ds.series[Label]['Attr'][attr]!=Attr[attr]:
                ds.series['_tmp_']['Attr'][attr] = Attr[attr]
            else:
                ds.series['_tmp_']['Attr'][attr] = ds.series[Label]['Attr'][attr]
        for attr in Attr:
            if attr not in ds.series['_tmp_']['Attr'].keys():
                ds.series['_tmp_']['Attr'][attr] = Attr[attr]
    else:
        for item in Attr:
            ds.series['_tmp_']['Attr'][item] = Attr[item]
    ds.series[unicode(Label)] = ds.series['_tmp_']     # copy temporary series to new series
    del ds.series['_tmp_']                        # delete the temporary series

def CreateDatetimeRange(start,stop,step=datetime.timedelta(minutes=30)):
    '''
    Purpose:
     Create a series of datetimes between the "start" and "stop" datetimes
     and with a time step of "step".
    Useage:
     dt = ds.series['DateTime']['Data']
     ts = ds.globaleattributes['time_step']
     dt_evenlyspaced = CreateDatetimeRange(dt[0],dt[-1],step=datetime.timedelta(minutes=ts))]
    Author: PRI
    Date: December 2013
    '''
    result = []
    while start<stop:
        result.append(start)
        start = start + step
    return result

def create_empty_variable(label, nrecs, datetime=[]):
    """
    Purpose:
     Returns an empty variable.  Data values are set to -9999, flag values are set to 1
     and default values for the attributes.
    Usage:
     variable = pfp_utils.create_empty_variable(label, nrecs)
     where label is the variable label
           nrecs is the number of elements in the variable data
    Author: PRI
    Date: December 2016
    """
    data = numpy.ones(nrecs, dtype=numpy.float64)*float(c.missing_value)
    flag = numpy.ones(nrecs, dtype=numpy.int32)
    attr = make_attribute_dictionary()
    variable = {"Label":label, "Data":data, "Flag":flag, "Attr":attr}
    if len(datetime) == nrecs:
        variable["DateTime"] = datetime
    return variable

def CreateVariable(ds,variable):
    """
    Purpose:
     Create a variable in the data structure.
     If the variable already exists in the data structure, data values, QC flags and
     attributes will be overwritten.
     This utility is the prefered method for creating or updating a data series because
     it implements a consistent method for creating series in the data structure.  Direct
     writes to the contents of the data structure are discouraged (unless PRI wrote the code:=P).
    Usage:
     Fsd = pfp_utils.GetVariable(ds,"Fsd")
      ... do something to Fsd here ...
      ... and don't forget to update the QC flag ...
      ... and the attributes ...
     pfp_utils.CreateVariable(ds,Fsd)
    Author: PRI
    Date: September 2016
    """
    label = variable["Label"]
    # create a temporary series to avoid premature overwrites
    ds.series["_tmp_"] = {}
    # put the data into the temporary series
    if numpy.ma.isMA(variable["Data"]):
        ds.series["_tmp_"]["Data"] = numpy.ma.filled(variable["Data"],
                                                     float(c.missing_value))
    else:
        ds.series["_tmp_"]["Data"] = numpy.array(variable["Data"])
    # copy or make the QC flag
    ds.series["_tmp_"]["Flag"] = numpy.array(variable["Flag"])
    # do the attributes
    ds.series["_tmp_"]["Attr"] = copy.deepcopy(variable["Attr"])
    # and copy the temporary series back to the original label
    ds.series[unicode(label)] = copy.deepcopy(ds.series['_tmp_'])
    # delete the temporary series
    del ds.series['_tmp_']

def file_exists(filename,mode="verbose"):
    if not os.path.exists(filename):
        if mode=="verbose":
            logger.error(' File '+filename+' not found')
        return False
    else:
        return True

def find_nearest_value(array, value):
    """
    Purpose:
     pfp_utils.bisection() gives the left bound of the interval of array containing
     value, this function gives the index of the closest value.
    """
    i = bisection(array, value)
    if i < len(array)-1:
        if abs(array[i+1]-value) <= abs(array[i]-value):
            i = i + 1
    return i

def FindIndicesOfBInA(a,b):
    """
    Purpose:
     Find the indices of elements in b that also occur in a.
     The routine is intended for use only with lists of Python datetime
     values.  This ensures the input series are monotonically increasing
     (though this is not a requirement) and contain no duplicates (which
     is required, or at least not handled).
    Limitations:
     Argument a is converted to a set to greatly speed the comparison
     of b elements with a.  This means that duplicates in a will be
     dropped and hence only 1 index will be returned for each value
     in b.
    Usage:
     indices = pfp_utils.FindIndicesOfBInA(a,b)
     where a is a list of Python datetime objects
           b is a list of Python datetime objects
           indices is a list of indices in b where the elements of b
                also occur in a
    Author: PRI
    Date: July 2015
    Comments: Replaces find_indices used up to V2.9.3.
    March 2018 - rewritten to handle numpy.ndarray and lists
    """
    if len(set(a))!=len(a):
        msg = " FindIndicesOfBInA: first argument contains duplicate values"
        logger.warning(msg)
    if isinstance(a, numpy.ndarray) and isinstance(b, numpy.ndarray):
        asorted = numpy.argsort(a)
        bpos = numpy.searchsorted(a[asorted], b)
        indices = asorted[bpos]
    elif isinstance(a, list) and isinstance(b, list):
        tmpset = set(a)
        indices = [i for i,item in enumerate(b) if item in tmpset]
    else:
        msg = " FindIndicesOfBInA: inputs must be both list or both numpy arrays"
        logger.warning(msg)
        indices = []
    return indices

def FindMatchingIndices(a, b):
    a1=numpy.argsort(a)
    b1=numpy.argsort(b)
    # use searchsorted:
    sort_left_a=a[a1].searchsorted(b[b1], side='left')
    sort_right_a=a[a1].searchsorted(b[b1], side='right')
    sort_left_b=b[b1].searchsorted(a[a1], side='left')
    sort_right_b=b[b1].searchsorted(a[a1], side='right')
    # which values of b are also in a?
    inds_b=(sort_right_a-sort_left_a > 0).nonzero()[0]
    # which values of a are also in b?
    inds_a=(sort_right_b-sort_left_b > 0).nonzero()[0]
    return inds_a, inds_b

def RemoveDuplicateRecords(ds):
    """ Remove duplicate records."""
    # the ds.series["DateTime"]["Data"] series is actually a list
    for item in ["DateTime","DateTime_UTC"]:
        if item in ds.series.keys():
            ldt,ldt_flag,ldt_attr = GetSeries(ds,item)
            # ldt_nodups is returned as an ndarray
            ldt_nodups,idx_nodups = numpy.unique(ldt,return_index=True)
            # and put it back into the data structure
            ds.series[item]["Data"] = ldt_nodups
            ds.series[item]["Flag"] = ldt_flag[idx_nodups]
    # get a list of the series in the data structure
    series_list = [item for item in ds.series.keys() if '_QCFlag' not in item]
    # remove the DateTime
    for item in ["DateTime","DateTime_UTC"]:
        if item in series_list: series_list.remove(item)
    # loop over the series in the data structure
    for ThisOne in series_list:
        data_dups,flag_dups,attr = GetSeriesasMA(ds,ThisOne)
        data_nodups = data_dups[idx_nodups]
        flag_nodups = flag_dups[idx_nodups]
        CreateSeries(ds,ThisOne,data_nodups,flag_nodups,attr)
    ds.globalattributes['nc_nrecs'] = len(ds.series["DateTime"]["Data"])

def FixNonIntegralTimeSteps(ds,fixtimestepmethod=""):
    """
    Purpose:
     Fix time steps that are not an integral number of the default time step.
     The default time step is read from the "time_step" global attribute which is read from
     the L1 control file and written to the L1 netCDF file.
     The most common cause of non-integral time steps is drift in logger time stamp or
     rounding errors in Excel's treatment of datetimes.
    Usage:
     FixNonIntegralTimeSteps(ds)
    Called By: CheckTimeStep
    Author: PRI
    Date: February 2015
    To do:
     Implement [I]nterpolate
    """
    ts = int(ds.globalattributes["time_step"])
    ldt = ds.series["DateTime"]["Data"]
    dt_diffs = numpy.array([(ldt[i]-rounddttots(ldt[i],ts=ts)).total_seconds() for i in range(1,len(ldt))])
    logger.info(" Maximum drift is "+str(numpy.max(dt_diffs))+" seconds, minimum drift is "+str(numpy.min(dt_diffs))+" seconds")
    ans = fixtimestepmethod
    if ans=="": ans = raw_input("Do you want to [Q]uit, [I]nterploate or [R]ound? ")
    if ans.lower()[0]=="q":
        msg = "Quiting ..."
        logger.error(msg)
        sys.exit()
    if ans.lower()[0]=="i":
        msg = "Interpolation to regular time step not implemented yet ..."
        logger.error(msg)
        return
    if ans.lower()[0]=="r":
        logger.info(" Rounding to the nearest time step")
        ldt_rounded = numpy.array([rounddttots(dt,ts=ts) for dt in ldt])
        rdt = numpy.array([(ldt_rounded[i]-ldt_rounded[i-1]).total_seconds() for i in range(1,len(ldt))])
        logger.info(" Maximum time step is now "+str(numpy.max(rdt))+" seconds, minimum time step is now "+str(numpy.min(rdt)))
        # replace the existing datetime series with the datetime series rounded to the nearest time step
        ds.series["DateTime"]["Data"] = ldt_rounded
    ds.globalattributes['nc_nrecs'] = len(ds.series["DateTime"]["Data"])

def FixTimeGaps(ds):
    """
    Purpose:
     Fix gaps in datetime series found by CheckTimeStep.
    Useage:
     has_gaps = CheckTimeStep(ds)
     if has_gaps:
         FixTimeGaps(ds)
    Author: PRI
    Date: April 2013
    Modified:
     September 2014 - rewrite for clarity and efficiency
     February 2015 - and again ...
    """
    ts = int(ds.globalattributes["time_step"])
    #ldt_gaps,ldt_flag,ldt_attr = GetSeries(ds,"DateTime")
    ldt_gaps = ds.series["DateTime"]["Data"]
    # generate a datetime list from the start datetime to the end datetime
    ldt_start = ldt_gaps[0]
    ldt_end = ldt_gaps[-1]
    nogaps = [result for result in perdelta(ldt_start,ldt_end,datetime.timedelta(minutes=ts))]
    ldt_nogaps = numpy.array(nogaps)
    # update the global attribute containing the number of records
    nRecs = len(ldt_nogaps)
    ds.globalattributes['nc_nrecs'] = nRecs
    # find the indices of the no-gap data in the original data
    idx_gaps = FindIndicesOfBInA(ldt_nogaps,ldt_gaps)
    # update the series of Python datetimes
    ds.series['DateTime']['Data'] = ldt_nogaps
    ds.series['DateTime']['Flag'] = numpy.zeros(len(ldt_nogaps),dtype=numpy.int32)
    # get a list of series in the data structure
    series_list = [item for item in ds.series.keys() if '_QCFlag' not in item]
    # remove the datetime-related series from data structure
    datetime_list = ["DateTime","DateTime_UTC"]
    for item in datetime_list:
        if item in series_list: series_list.remove(item)
    # now loop over the rest of the series in the data structure
    for ThisOne in series_list:
        data_nogaps = numpy.ones(nRecs,dtype=numpy.float64)*float(-9999)
        flag_nogaps = numpy.ones(nRecs,dtype=numpy.int32)
        data_gaps,flag_gaps,attr = GetSeriesasMA(ds,ThisOne)
        data_nogaps[idx_gaps] = data_gaps
        flag_nogaps[idx_gaps] = flag_gaps
        CreateSeries(ds,ThisOne,data_nogaps,flag_nogaps,attr)
    return

def FixTimeStep(ds,fixtimestepmethod="round"):
    """
    Purpose:
     Fix problems with the time stamp.
    Useage:
     pfp_utils.FixTimeStep(ds,fixtimestepmethod=fixtimestepmethod)
    Author: PRI
    Date: April 2013
    Modified:
     February 2015 - split check and fix functions into different routines
    """
    # get the number of records
    nRecs = int(ds.globalattributes["nc_nrecs"])
    # get the time step
    ts = int(ds.globalattributes["time_step"])
    # time step between records in seconds
    dt = get_timestep(ds)
    dtmin = numpy.min(dt)
    dtmax = numpy.max(dt)
    if dtmin < ts*60:
        # duplicate or overlapping times found
        logger.info(' FixTimeStep: duplicate or overlapping times found, removing ...')
        RemoveDuplicateRecords(ds)
        dt = get_timestep(ds)
        dtmin = numpy.min(dt)
        dtmax = numpy.max(dt)
        #log.info("After RemoveDuplicateRecords:"+str(dtmin)+" "+str(dtmax))
    if numpy.min(numpy.mod(dt,ts*60))!=0 or numpy.max(numpy.mod(dt,ts*60))!=0:
        # non-integral time steps found
        # indices of elements where time step not equal to default
        index = numpy.where(numpy.min(numpy.mod(dt,ts*60))!=0 or numpy.max(numpy.mod(dt,ts*60))!=0)[0]
        logger.info(" FixTimeStep: Non-integral time steps found "+str(len(index))+" times out of "+str(nRecs))
        logger.info(" FixTimeStep: Maximum time step was "+str(numpy.max(dt))+" seconds, minimum time step was "+str(numpy.min(dt)))
        FixNonIntegralTimeSteps(ds,fixtimestepmethod=fixtimestepmethod)
        dt = get_timestep(ds)
        dtmin = numpy.min(dt)
        dtmax = numpy.max(dt)
        #log.info("After FixNonIntegralTimeSteps:"+str(dtmin)+" "+str(dtmax))
    if dtmax > ts*60:
        # time gaps found
        logger.info(' FixTimeStep: one or more time gaps found, inserting times ...')
        FixTimeGaps(ds)
        dt = get_timestep(ds)
        dtmin = numpy.min(dt)
        dtmax = numpy.max(dt)
        #log.info("After FixTimeGaps: "+str(dtmin)+" "+str(dtmax))

def GetAverageSeriesKeys(cf,ThisOne):
    if incf(cf,ThisOne) and haskey(cf,ThisOne,'AverageSeries'):
        if 'Source' in cf['Variables'][ThisOne]['AverageSeries'].keys():
            alist = ast.literal_eval(cf['Variables'][ThisOne]['AverageSeries']['Source'])
        else:
            logger.error('  GetAverageSeriesKeys: key "Source" not in control file AverageSeries section for '+ThisOne)
            alist = []
        if 'standard_name' in cf['Variables'][ThisOne]['AverageSeries'].keys():
            standardname = str(cf['Variables'][ThisOne]['AverageSeries']['standard_name'])
        else:
            standardname = "not defined"
    else:
        standardname = "not defined"
        logger.info('  GetAverageSeriesKeys: '+ThisOne+ ' not in control file or it does not have the "AverageSeries" key')
        alist = []
    return alist, standardname

def GetAltName(cf,ds,ThisOne):
    '''
    Check to see if the specified variable name is in the data structure (ds).
    If it is, return the variable name unchanged.
    If it isn't, check the control file to see if an alternate name has been specified
     and return the alternate name if one exists.
    '''
    if ThisOne not in ds.series.keys():
        if ThisOne in cf['Variables'].keys():
            ThisOne = cf['Variables'][ThisOne]['AltVarName']
            if ThisOne not in ds.series.keys():
                logger.error('GetAltName: alternate variable name not in ds')
        else:
            logger.error('GetAltName: cant find ',ThisOne,' in ds or control file')
    return ThisOne

def GetAltNameFromCF(cf,ThisOne):
    '''
    Get an alternate variable name from the control file.
    '''
    if ThisOne in cf['Variables'].keys():
        if 'AltVarName' in cf['Variables'][ThisOne].keys():
            ThisOne = str(cf['Variables'][ThisOne]['AltVarName'])
        else:
            msg = 'GetAltNameFromCF: AltVarName key not in control file for '+str(ThisOne)
            logger.warning(msg)
    else:
        msg = 'GetAltNameFromCF: '+str(ThisOne)+' not in control file'
        logger.warning(msg)
    return ThisOne

def GetAttributeDictionary(ds,ThisOne):
    attr = {}
    # if series ThisOne is in the data structure
    if ThisOne in ds.series.keys():
        attr = ds.series[ThisOne]['Attr']
    else:
        attr = MakeAttributeDictionary()
    return copy.deepcopy(attr)

def GetcbTicksFromCF(cf,ThisOne):
    '''
    Get colour bar tick labels from the control file.
    '''
    if ThisOne in cf['Variables'].keys():
        if 'Ticks' in cf['Variables'][ThisOne].keys():
            Ticks = eval(cf['Variables'][ThisOne]['Ticks'])
        else:
            msg = 'GetcbTicksFromCF: Ticks key not in control file for '+str(ThisOne)
            logger.warning(msg)
    else:
        msg = 'GetcbTicksFromCF: '+str(ThisOne)+' not in control file'
        logger.warning(msg)
    return Ticks

def GetRangesFromCF(cf,ThisOne,mode="verbose"):
    '''
    Get lower and upper range limits from the control file.
    '''
    if ThisOne in cf['Variables'].keys():
        if 'Lower' in cf['Variables'][ThisOne].keys():
            lower = float(cf['Variables'][ThisOne]['Lower'])
        else:
            if mode.lower()!="quiet":
                msg = "GetRangesFromCF: Lower key not in control file for "+str(ThisOne)
                logger.info(msg)
            lower = None
        if 'Upper' in cf['Variables'][ThisOne].keys():
            upper = float(cf['Variables'][ThisOne]['Upper'])
        else:
            if mode.lower()!="quiet":
                msg = "GetRangesFromCF: Upper key not in control file for "+str(ThisOne)
                logger.info(msg)
            upper = None
    else:
        if mode.lower()!="quiet":
            msg = "GetRangesFromCF: "+str(ThisOne)+" not in control file"
            logger.info(msg)
        lower, upper = None
    return lower, upper

def GetDateIndex(ldt,date,ts=30,default=0,match='exact'):
    """
    Purpose:
     Return the index of a date/datetime string in an array of datetime objects
    Usage:
     si = pfp_utils.GetDateIndex(ldt,date_str,ts=30,default=0,match='exact')
    where
     ldt      - array of datetime objects
     date_str - a date or date/time string in a format dateutils can parse
     ts       - time step for the data, optional (integer)
     default  - default value, optional (integer)
     match    - type of match (string) options are:
                "exact"            - finds the specified datetime and returns
                                     the index
                "startnextday"     - returns the index of the first time period
                                     in the next day
                "endpreviousday"   - returns the index of the last time period
                                     in the previous day
                "startnexthour"    - returns the index of the first time period
                                     in the next hour
                "endprevioushour"  - returns the index of the last time period
                                     in the previous hour
                "startnextmonth"   - returns the index of the first time period
                                     in the next month
                "endpreviousmonth" - returns the index of the last time period
                                     in the previous month
                NOTE: "startnextday" and "endpreviousday" can be used to pick
                    out time periods with an integer number of days
    Author: PRI
    Date: Back in the day
    """
    # trap default values of -1 since -1 + 1 = 0
    if default == -1:
        default = len(ldt)-1
    # is the input date a string?
    if isinstance(date, str):
        # if so, is it an empty string?
        if len(date) != 0:
            # if not empty, see if we can parse it
            try:
                date = dateutil.parser.parse(date)
                if (date>=ldt[0]) and (date<=ldt[-1]):
                    # date string parsed OK, is it within the datetime range of the data?
                    i = find_nearest_value(ldt, date)
                else:
                    # set to default if not within the datetime range of the data
                    i = default
            except:
                # set to default if parsing date string failed
                i = default
        else:
            # set to default if date string empty
            i = default
    elif isinstance(date, datetime.datetime):
        # the input date was a datetime object
        # check it is within the datetime range of the data
        if (date>=ldt[0]) and (date<=ldt[-1]):
            i = find_nearest_value(ldt, date)
        else:
            # set to default if not within the datetime range of the data
            i = default
    else:
        msg = " Unrecognised object passed in as date, returning default index"
        logger.warning(msg)
        i = default
    if match=="exact":
        # if an exact match is required, do nothing
        pass
    elif match=="startnextmonth":
        # get to the start of the next day
        while abs(ldt[i].hour+float(ldt[i].minute)/60-float(ts)/60)>c.eps:
            i = i + 1
        while ldt[i].day!=1:
            i = i + int(float(24)/(float(ts)/60))
    elif match=='startnextday':
        while abs(ldt[i].hour+float(ldt[i].minute)/60-float(ts)/60)>c.eps:
            i = i + 1
    elif match=="startnexthour":
        # check the time step value
        if int(ts)!=60:
            # if the time step is 60 then it is always the start of the next hour
            # we assume here that the time period ends on the datetime stamp
            while ldt[i].minute!=ts:
                # iterate until the minutes equal the time step
                i = i + 1
    elif match=='endpreviousmonth':
        while abs(ldt[i].hour+float(ldt[i].minute)/60)>c.eps:
            i = i - 1
        while ldt[i].day!=1:
            i = i - int(float(24)/(float(ts)/60))
    elif match=='endpreviousday':
        while abs(ldt[i].hour+float(ldt[i].minute)/60)>c.eps:
            i = i - 1
    elif match=="endprevioushour":
        # check the time step value
        if int(ts)!=60:
            # if the time step is 60 then it is always the end of the previous hour
            # we assume here that the time period ends on the datetime stamp
            while ldt[i].minute!=0:
                # iterate until the minutes equal 0
                i = i - 1
    else:
        logger.error("GetDateIndex: Unrecognised match option")
    return i

def GetGlobalAttributeValue(cf,ds,ThisOne):
    if ThisOne not in ds.globalattributes.keys():
        if ThisOne in cf['General'].keys():
            ds.globalattributes[ThisOne] = cf['General'][ThisOne]
        else:
            logger.error('  GetGlobalAttributeValue: global attribute '+ThisOne+' was not found in the netCDF file or in the control file')
            ds.globalattributes[ThisOne] = None
    return ds.globalattributes[ThisOne]

def GetMergeSeriesKeys(cf,ThisOne,section=''):
    if len(section)==0: section = 'Variables'
    if 'Source' in cf[section][ThisOne]['MergeSeries'].keys():
        mlist = ast.literal_eval(cf[section][ThisOne]['MergeSeries']['Source'])
    else:
        logger.error('  GetMergeSeriesKeys: key "Source" not in control file MergeSeries section for '+ThisOne)
        mlist = []
    if 'standard_name' in cf[section][ThisOne]['MergeSeries'].keys():
        standardname = str(cf[section][ThisOne]['MergeSeries']['standard_name'])
    else:
        standardname = 'not defined'
    return mlist, standardname

def GetPlotTitleFromCF(cf, nFig):
    if 'Plots' in cf:
        if str(nFig) in cf['Plots']:
            if 'Title' in cf['Plots'][str(nFig)]:
                Title = str(cf['Plots'][str(nFig)]['Title'])
            else:
                msg = 'GetPlotTitleFromCF: Variables key not in control file for plot '+str(nFig)
                logger.warning(msg)
        else:
            msg = 'GetPlotTitleFromCF: '+str(nFig)+' key not in Plots section of control file'
            logger.warning(msg)
    else:
        msg = 'GetPlotTitleFromCF: Plots key not in control file'
        logger.warning(msg)
    return Title

def GetPlotVariableNamesFromCF(cf, n):
    if 'Plots' in cf:
        if str(n) in cf['Plots']:
            if 'Variables' in cf['Plots'][str(n)]:
                SeriesList = eval(cf['Plots'][str(n)]['Variables'])
            else:
                msg = 'GetPlotVariableNamesFromCF: Variables key not in control file for plot '+str(n)
                logger.warning(msg)
        else:
            msg = 'GetPlotVariableNamesFromCF: '+str(n)+' key not in Plots section of control file'
            logger.warning(msg)
    else:
        msg = 'GetPlotVariableNamesFromCF: Plots key not in control file'
        logger.warning(msg)
    return SeriesList

def GetSeries(ds,ThisOne,si=0,ei=-1,mode="truncate"):
    """ Returns the data, QC flag and attributes of a series from the data structure."""
    # number of records
    if "nc_nrecs" in ds.globalattributes:
        nRecs = int(ds.globalattributes["nc_nrecs"])
    else:
        nRecs = len(ds.series[ThisOne]["Data"])
    # check the series requested is in the data structure
    if ThisOne in ds.series.keys():
        # series is in the data structure
        if isinstance(ds.series[ThisOne]['Data'],list):
            # return a list if the series is a list
            Series = list(ds.series[ThisOne]['Data'])
        elif isinstance(ds.series[ThisOne]['Data'],numpy.ndarray):
            # return a numpy array if series is an array
            Series = ds.series[ThisOne]['Data'].copy()
        # now get the QC flag
        if 'Flag' in ds.series[ThisOne].keys():
            # return the QC flag if it exists
            Flag = ds.series[ThisOne]['Flag'].copy()
        else:
            # create a QC flag if one does not exist
            Flag = numpy.zeros(nRecs,dtype=numpy.int32)
        # now get the attribute dictionary
        if "Attr" in ds.series[ThisOne].keys():
            Attr = GetAttributeDictionary(ds,ThisOne)
        else:
            Attr = MakeAttributeDictionary()
    else:
        # make an empty series if the requested series does not exist in the data structure
        logger.warning("GetSeries: "+ThisOne+" not found, making empty series ...")
        Series,Flag,Attr = MakeEmptySeries(ds,ThisOne)
    # tidy up
    if ei==-1: ei = nRecs - 1
    if mode=="truncate":
        # truncate to the requested start and end indices
        si = max(0,si)                  # clip start index at 0
        ei = min(nRecs,ei)              # clip end index to nRecs
        Series = Series[si:ei+1]        # truncate the data
        Flag = Flag[si:ei+1]            # truncate the QC flag
    elif mode=="pad":
        # pad with missing data at the start and/or the end of the series
        if si<0 and ei>nRecs-1:
            # pad at the start
            Series = numpy.append(float(c.missing_value)*numpy.ones(abs(si),dtype=numpy.float64),Series)
            Flag = numpy.append(numpy.ones(abs(si),dtype=numpy.int32),Flag)
            # pad at the end
            Series = numpy.append(Series,float(c.missing_value)*numpy.ones((ei-(nRecs-1)),dtype=numpy.float64))
            Flag = numpy.append(Flag,numpy.ones((ei-(nRecs-1)),dtype=numpy.int32))
        elif si<0 and ei<=nRecs-1:
            # pad at the start, truncate the end
            Series = numpy.append(float(c.missing_value)*numpy.ones(abs(si),dtype=numpy.float64),Series[:ei+1])
            Flag = numpy.append(numpy.ones(abs(si),dtype=numpy.int32),Flag[:ei+1])
        elif si>=0 and ei>nRecs-1:
            # truncate at the start, pad at the end
            Series = numpy.append(Series[si:],float(c.missing_value)*numpy.ones((ei-(nRecs-1)),numpy.float64))
            Flag = numpy.append(Flag[si:],numpy.ones((ei-(nRecs-1)),dtype=numpy.int32))
        elif si>=0 and ei<=nRecs-1:
            # truncate at the start and end
            Series = Series[si:ei+1]
            Flag = Flag[si:ei+1]
        else:
            msg = 'GetSeries: unrecognised combination of si ('+str(si)+') and ei ('+str(ei)+')'
            raise ValueError(msg)
    elif mode=="mirror":
        # reflect data about end boundaries if si or ei are out of bounds
        if si<0 and ei>nRecs-1:
            # mirror at the start
            Series = numpy.append(numpy.fliplr([Series[1:abs(si)+1]])[0],Series)
            Flag = numpy.append(numpy.fliplr([Flag[1:abs(si)+1]])[0],Flag)
            # mirror at the end
            sim = 2*nRecs-1-ei
            eim = nRecs-1
            Series = numpy.append(Series,numpy.fliplr([Series[sim:eim]])[0])
            Flag = numpy.append(Flag,numpy.fliplr([Flag[sim:eim]])[0])
        elif si<0 and ei<=nRecs-1:
            # mirror at start, truncate at end
            Series = numpy.append(numpy.fliplr([Series[1:abs(si)+1]])[0],Series[:ei+1])
            Flag = numpy.append(numpy.fliplr([Flag[1:abs(si)+1]])[0],Flag[:ei+1])
        elif si>=0 and ei>nRecs-1:
            # truncate at start, mirror at end
            sim = 2*nRecs-1-ei
            eim = nRecs
            Series = numpy.append(Series[si:],numpy.fliplr([Series[sim:eim]])[0])
            Flag = numpy.append(Flag[si:],numpy.fliplr([Flag[sim:eim]])[0])
        elif si>=0 and ei<=nRecs-1:
            # truncate at the start and end
            Series = Series[si:ei+1]
            Flag = Flag[si:ei+1]
        else:
            msg = 'GetSeries: unrecognised combination of si ('+str(si)+') and ei ('+str(ei)+')'
            raise ValueError(msg)
    else:
        raise ValueError("GetSeries: unrecognised mode option "+str(mode))
    return Series,Flag,Attr

def MakeEmptySeries(ds,ThisOne):
    nRecs = int(ds.globalattributes['nc_nrecs'])
    Series = float(c.missing_value)*numpy.ones(nRecs,dtype=numpy.float64)
    Flag = numpy.ones(nRecs,dtype=numpy.int32)
    Attr = MakeAttributeDictionary()
    return Series,Flag,Attr

def GetSeriesasMA(ds,ThisOne,si=0,ei=-1,mode="truncate"):
    """
    Purpose:
     Returns a data series and the QC flag series from the data structure.
    Usage:
     data,flag,attr = pfp_utils.GetSeriesasMA(ds,label,si=0,ei=-1)
    where the arguments are;
      ds    - the data structure (dict)
      label - label of the data series in ds (string)
      si    - start index (integer), default 0
      ei    - end index (integer), default -1
    and the returned values are;
      data - values for the requested series in ds
             (numpy masked array, float64)
      flag - QC flag for the requested series in ds
             (numpy masked array, int32)
      attr - attribute dictionary for series
    Example:
     The code snippet below will return the incoming shortwave data values
     (Fsd) and the associated QC flag (f) as numpy masked arrays;
      ds = pfp_io.nc_read_series("HowardSprings_2011_L3.nc")
      Fsd,f,a = pfp_utils.GetSeriesasMA(ds,"Fsd")
    Author: PRI
    """
    Series,Flag,Attr = GetSeries(ds,ThisOne,si=si,ei=ei,mode=mode)
    Series,WasND = SeriestoMA(Series)
    return Series,Flag,Attr

def GetVariable(ds, label, start=0, end=-1, mode="truncate", out_type="ma"):
    """
    Purpose:
     Returns a data variable from the data structure as a dictionary.
    Usage:
     data,flag,attr = pfp_utils.GetSeriesasMA(ds,label,si=0,ei=-1)
    where the arguments are;
      ds    - the data structure (dict)
      label - label of the data variable in ds (string)
      start - start date or index (integer), default 0
      end   - end date or index (integer), default -1
    and the returned values are;
     The data are returned as a dictionary;
      variable["label"] - variable label in data structure
      variable["data"] - numpy float64 masked array containing data
      variable["flag"] - numpy int32 array containing QC flags
      variable["attr"] - dictionary of variable attributes
    Example:
     The code snippet below will return the incoming shortwave data values
     (Fsd), the associated QC flag and the variable attributes;
      ds = pfp_io.nc_read_series("HowardSprings_2011_L3.nc")
      Fsd = pfp_utils.GetSeriesAsDict(ds,"Fsd")
    Author: PRI
    """
    nrecs = int(ds.globalattributes["nc_nrecs"])
    if end == -1:
        end = nrecs
    ts = int(ds.globalattributes["time_step"])
    ldt = ds.series["DateTime"]["Data"]
    si = get_start_index(ldt, start)
    ei = get_end_index(ldt, end)
    data,flag,attr = GetSeries(ds, label, si=si, ei=ei, mode=mode)
    if isinstance(data, numpy.ndarray):
        data, WasND = SeriestoMA(data)
    variable = {"Label":label,"Data":data,"Flag":flag,"Attr":attr,
                "DateTime":ldt[si:ei+1],"time_step":ts}
    return variable

def GetUnitsFromds(ds, ThisOne):
    units = ds.series[ThisOne]['Attr']['units']
    return units

def get_cfsection(cf,series='',mode='quiet'):
    '''
    Find the section in the control file that contains an entry for the series "series".
    USEAGE:  section = pfp_utils.get_cfsection(cf,series=<series_name>)
    INPUT:   cf            - a control file object (from ConfigObj)
             <series_name> - the name of the series (string)
    RETURNS: section       - the name of the section containing an entry for <series_name> (string)
    Note that the returned section name is an empty string if there is no entry for <series_name> in
    the control file.
    '''
    section = ''
    sectionlist = ['Variables','Drivers','Fluxes','Respiration','Partition','ER','GPP','NEE']
    if len(series)==0:
        msgtxt = ' get_cfsection: no input series specified'
        if mode!='quiet': logger.info(msgtxt)
        return section
    for ThisSection in sectionlist:
        if ThisSection in cf.keys():
            if series in cf[ThisSection]: section = ThisSection
    if len(section)==0:
        msgtxt = ' get_cfsection: series '+str(series)+' not found in control file'
        if mode!='quiet': logger.info(msgtxt)
    return section

def get_coverage_groups(ds,rad=None,met=None,flux=None,soil=None):
    level = "L1"
    if "nc_level" in ds.globalattributes:
        level = str(ds.globalattributes["nc_level"])
    rad = ['Fsd','Fsu','Fld','Flu','Fn']
    met = ['Ah','Cc','Precip','ps','Ta','Ws','Wd']
    flux = ['Fm','ustar','Fh','Fe','Fc']
    soil = ['Fg','Ts','Sws']
    for ThisGroup, ThisLabel in zip([rad,met,flux,soil],['radiation','meteorology','flux','soil']):
        sum_coverage = float(0); count = float(0)
        for ThisOne in ThisGroup:
            if ThisOne in ds.series.keys():
                sum_coverage = sum_coverage + float(ds.series[ThisOne]['Attr']['coverage_'+level])
                count = count + 1
        if count!=0:
            coverage_group = sum_coverage/count
        else:
            coverage_group = 0
        ds.globalattributes['coverage_'+ThisLabel+'_'+level] = str('%d'%coverage_group)

def get_coverage_individual(ds):
    level = "L1"
    if "nc_level" in ds.globalattributes:
        level = str(ds.globalattributes["nc_level"])
    SeriesList = ds.series.keys()
    for ThisOne in ["DateTime","DateTime_UTC"]:
        if ThisOne in SeriesList: SeriesList.remove(ThisOne)
    for ThisOne in SeriesList:
        num_good = len(numpy.where(abs(ds.series[ThisOne]['Data']-float(c.missing_value))>c.eps)[0])
        coverage = 100*float(num_good)/float(ds.globalattributes['nc_nrecs'])
        ds.series[ThisOne]['Attr']['coverage_'+level] = str('%d'%coverage)

def get_datetimefromnctime(ds,time,time_units):
    """
    Purpose:
     Create a series of datetime objects from the time read from a netCDF file.
    Usage:
     pfp_utils.get_datetimefromnctime(ds,time,time_units)
    Side effects:
     Creates a Python datetime series in the data structure
    Author: PRI
    Date: September 2014
    """
    ts = int(ds.globalattributes["time_step"])
    nRecs = int(ds.globalattributes["nc_nrecs"])
    dt = netCDF4.num2date(time,time_units)
    ds.series[unicode("DateTime")] = {}
    ds.series["DateTime"]["Data"] = dt
    ds.series["DateTime"]["Flag"] = numpy.zeros(nRecs)
    ds.series["DateTime"]["Attr"] = {}
    ds.series["DateTime"]["Attr"]["long_name"] = "Datetime in local timezone"
    ds.series["DateTime"]["Attr"]["units"] = "None"

def get_datetimefromxldate(ds):
    ''' Creates a series of Python datetime objects from the Excel date read from the Excel file.
        Thanks to John Machin for the quick and dirty code
         see http://stackoverflow.com/questions/1108428/how-do-i-read-a-date-in-excel-format-in-python'''

    logger.info(' Getting the Python datetime series from the Excel datetime')
    xldate = ds.series['xlDateTime']['Data']
    nRecs = len(ds.series['xlDateTime']['Data'])
    datemode = int(ds.globalattributes['xl_datemode'])
    ds.series[unicode('DateTime')] = {}
    basedate = datetime.datetime(1899, 12, 30)
    dt = [None]*nRecs
    for i in range(nRecs):
        dt[i] = basedate + datetime.timedelta(days=xldate[i] + 1462 * datemode)
    ds.series['DateTime']['Data'] = numpy.array(dt)
    ds.series['DateTime']['Flag'] = numpy.zeros(nRecs)
    ds.series['DateTime']['Attr'] = {}
    ds.series['DateTime']['Attr']['long_name'] = 'Datetime in local timezone'
    ds.series['DateTime']['Attr']['units'] = 'None'

def get_datetimefromymdhms(ds):
    ''' Creates a series of Python datetime objects from the year, month,
    day, hour, minute and second series stored in the netCDF file.'''
    SeriesList = ds.series.keys()
    if 'Year' not in SeriesList or 'Month' not in SeriesList or 'Day' not in SeriesList or 'Hour' not in SeriesList or 'Minute' not in SeriesList or 'Second' not in SeriesList:
        logger.info(' get_datetimefromymdhms: unable to find all datetime fields required')
        return
    logger.info(' Getting the date and time series')
    nRecs = get_nrecs(ds)
    ts = ds.globalattributes["time_step"]
    ds.series[unicode('DateTime')] = {}
    dt = [None]*nRecs
    if "Microseconds" in ds.series.keys():
        microseconds = ds.series["Microseconds"]["Data"]
    else:
        microseconds = numpy.zeros(nRecs,dtype=numpy.float64)
    for i in range(nRecs):
        dt = datetime.datetime(int(ds.series['Year']['Data'][i]),
                                int(ds.series['Month']['Data'][i]),
                                int(ds.series['Day']['Data'][i]),
                                int(ds.series['Hour']['Data'][i]),
                                int(ds.series['Minute']['Data'][i]),
                                int(ds.series['Second']['Data'][i]),
                                int(microseconds[i]))
    ds.series['DateTime']['Data'] = numpy.array(dt)
    ds.series['DateTime']['Flag'] = numpy.zeros(nRecs)
    ds.series['DateTime']['Attr'] = {}
    ds.series['DateTime']['Attr']['long_name'] = 'Date-time object'
    ds.series['DateTime']['Attr']['units'] = 'None'

def get_diurnalstats(dt,data,info):
    ts = info["time_step"]
    nperday = info["nperday"]
    si = 0
    while abs(dt[si].hour+float(dt[si].minute)/60-float(ts)/60)>c.eps:
        si = si + 1
    ei = len(dt)-1
    while abs(dt[ei].hour+float(dt[ei].minute)/60)>c.eps:
        ei = ei - 1
    data_wholedays = data[si:ei+1]
    ndays = len(data_wholedays)/nperday
    data_2d = numpy.ma.reshape(data_wholedays,[ndays,nperday])
    diel_stats = {}
    diel_stats["Hr"] = numpy.ma.array([i*ts/float(60) for i in range(0,nperday)])
    diel_stats["Av"] = numpy.ma.average(data_2d,axis=0)
    diel_stats["Sd"] = numpy.ma.std(data_2d,axis=0)
    diel_stats["Mx"] = numpy.ma.max(data_2d,axis=0)
    diel_stats["Mn"] = numpy.ma.min(data_2d,axis=0)
    return diel_stats

def get_end_index(ldt, end, mode="quiet"):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: October 2016
    """
    if isinstance(end, basestring):
        try:
            end = dateutil.parser.parse(end)
            if end <= ldt[-1] and end >= ldt[0]:
                ei = numpy.where(ldt == end)[0][0]
            else:
                if mode == "verbose":
                    msg = "Requested end date not found, setting to last date"
                    logger.warning(msg)
                ei = len(ldt)
        except ValueError as error:
            if mode == "verbose":
                msg = "Error parsing end date string, setting to last date"
                logger.warning(msg)
            ei = len(ldt)
    elif isinstance(end, datetime.datetime):
        if end >= ldt[0] and end <= ldt[-1]:
            ei = numpy.where(ldt == end)[0][0]
        else:
            if mode == "verbose":
                msg = "Requested end date not found, setting to last date"
                logger.warning(msg)
            ei = len(ldt)
    elif (isinstance(end, numbers.Number)):
        ei = min([int(end), len(ldt)])
    else:
        if mode == "verbose":
            msg = "Unrecognised type for end date, setting to last date"
            logger.warning(msg)
        ei = len(ldt)
    return ei

def get_keyvaluefromcf(cf,sections,key,default=None,mode="quiet"):
    """
    Purpose:
     General return a keyword value from a control file.
    Usage:
     keyval = pfp_utils.get_keyvaluefromcf(cf,sections,key,default=default)
     where
      cf is a control file object from ConfigObj
      sections is a list of sections and nested sub-sections to search
      key is the keyword
      default is a default value
    Example:
     ncOutFileName = pfp_utils.get_keyvaluefromcf(cf,["Files","Out"],"ncFileName",default="")
     The example above will return the value for ncFileName from the ["Files"]["Out"] sub-section
     in the control file.
    Author: PRI
    Date: February 2015
    """
    if len(sections)<1:
        msg = " get_keyvaluefromsections: no sections specified"
        if mode.lower()!="quiet": logger.info(msg)
    if sections[0] in cf:
        section = cf[sections[0]]
        if len(sections)>1:
            for item in sections[1:]:
                if item in section:
                    section = section[item]
                else:
                    msg = " get_keyvaluefromcf: Sub section "+item+" not found in control file, used default ("+str(default)+")"
                    if mode.lower()!="quiet": logger.info(msg)
                    value = default
        if key in section:
            value = section[key]
        else:
            msg = " get_keyvaluefromcf: Key "+key+" not found in section, used default ("+str(default)+")"
            if mode.lower()!="quiet": logger.info(msg)
            value = default
    else:
        msg = " get_keyvaluefromcf: Section "+sections[0]+" not found in control file, used default ("+str(default)+")"
        if mode.lower()!="quiet": logger.error(msg)
        value = default
    return value

def get_label_list_from_cf(cf):
    """
    Purpose:
     Returns a list of variable labels from a control file.
    Usage:
     label_list = pfp_utils.get_label_list_from_cf(cf)
     where cf is a control file object
           label_list is a list of variable labels referenced in the control file.
    """
    if "Variables" in cf:
        label_list = cf["Variables"].keys()
    elif "Drivers" in cf:
        label_list = cf["Drivers"].keys()
    elif "Fluxes" in cf:
        label_list = cf["Fluxes"].keys()
    else:
        label_list = []
        msg = "No Variables, Drivers or Fluxes section found in control file"
        logger.error(msg)
    return label_list

def get_missingingapfilledseries(ds):
    """
    Purpose:
     Check series in data structure and print a message to the screen if missing points are found.
    Usage:
     gfalternate_checkformissing(ds,series_list=series_list)
      where ds is a data structure
            series_list is a list of series to check
    Author: PRI
    Date: March 2015
    """
    # get a local pointer to the datetime
    ldt = ds.series["DateTime"]["Data"]
    # create an empty list
    alt_list = []
    # check to see if there was any gap filling using data from alternate sources
    if "alternate" in dir(ds):
        # if so, get a list of the quantities gap filled from alternate sources
        alt_list = list(set([ds.alternate[item]["label_tower"] for item in ds.alternate.keys()]))
    # create an empty list
    cli_list = []
    # check to see if there was any gap filling from climatology
    if "climatology" in dir(ds):
        # if so, get a list of the quantities gap filled using climatology
        cli_list = list(set([ds.climatology[item]["label_tower"] for item in ds.climatology.keys()]))
    # one list to rule them, one list to bind them ...
    gf_list = list(set(alt_list+cli_list))
    # clear out if there was no gap filling
    if len(gf_list)==0: return
    # loop over the series to be checked
    gap_found = False
    for series in gf_list:
        if series not in ds.series.keys(): continue
        data,flag,attr = GetSeriesasMA(ds,series)
        idx = numpy.ma.where(data.mask==True)[0]
        if len(idx)!=0:
            gap_found = True
            msg = " Missing points ("+str(len(idx))+") found in "+series
            logger.error(msg)
            #ldt_missing = [ldt[i] for i in idx]
            #msg = " The first 10 missing data is at datetimes "+str(ldt_missing[0:9])
            #log.error(msg)
    if not gap_found:
        msg = " No missing values found in gap filled series"
        logger.info(msg)

def get_number_from_heightstring(height):
    z = str(height)
    if "m" in z: z = z.replace("m","")
    try:
        z = float(z)
    except:
        z = 0.0
    return z

def get_nctime_from_datetime(ds, time_units="seconds since 1970-01-01 00:00:00.0",
                             calendar="gregorian"):
    """
    Purpose:
     Generate a time series in the supplied units from the datetime objects stored
     in the data structure ds.
    Usage:
     get_nctime_from_datetime(ds, time_units)
     where ds is a data structure (data_structure)
           group is the group in the data structure be handled (string)
           time_units provides the units and the reference datetime (string)
                      e.g. time_units = "seconds since 1970-01-01 00:00:00.0"
    Author: PRI
    Date: October 2017
    """
    ldt = ds.series["DateTime"]["Data"]
    data = netCDF4.date2num(ldt, time_units, calendar=calendar)
    flag = numpy.zeros(len(data))
    attr = {"long_name":"time", "standard_name":"time", "units":time_units, "calendar":calendar}
    variable = {"Label":"time", "Data":data, "Flag":flag, "Attr":attr}
    CreateVariable(ds, variable)

    return

def get_nrecs(ds):
    if 'nc_nrecs' in ds.globalattributes.keys():
        nRecs = int(ds.globalattributes['nc_nrecs'])
    elif 'NumRecs' in ds.globalattributes.keys():
        nRecs = int(ds.globalattributes['NumRecs'])
    else:
        series_list = ds.series.keys()
        nRecs = len(ds.series[series_list[0]]['Data'])
    return nRecs

def get_start_index(ldt, start, mode="quiet"):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: October 2016
    """
    if isinstance(start, basestring):
        try:
            start = dateutil.parser.parse(start)
            if start >= ldt[0] and start <= ldt[-1]:
                si = numpy.where(ldt == start)[0][0]
            else:
                if mode == "verbose":
                    msg = "Requested start date not found, setting to first date"
                    logger.warning(msg)
                si = 0
        except ValueError as error:
            if mode == "verbose":
                msg = "Error parsing start date string, setting to first date"
                logger.warning(msg)
            si = 0
    elif isinstance(start, datetime.datetime):
        if start >= ldt[0] and start <= ldt[-1]:
            si = numpy.where(ldt == start)[0][0]
        else:
            if mode == "verbose":
                msg = "Requested start date not found, setting to first date"
                logger.warning(msg)
            si = 0
    elif (isinstance(start, numbers.Number)):
        si = max([0,int(start)])
    else:
        if mode == "verbose":
            msg = "Unrecognised type for start, setting to first date"
            logger.warning(msg)
        si = 0
    return si

def get_timestep(ds):
    """
    Purpose:
     Return an array of time steps in seconds between records
    Useage:
     dt = pfp_utils.get_timestep(ds)
    Author: PRI
    Date: February 2015
    """
    # local pointer to the Python datetime series
    ldt = ds.series["DateTime"]["Data"]
    # time step between records in seconds
    dt = numpy.array([(ldt[i]-ldt[i-1]).total_seconds() for i in range(1,len(ldt))])
    return dt

def get_timezone(site_name,prompt="no"):
    """ Return the time zone based on the site name."""
    time_zone = ""
    found = False
    # strip out spaces and commas from the site name
    site_name = site_name.replace(" ","").replace(",","")
    for item in c.tz_dict.keys():
        if item in site_name.lower():
            time_zone = c.tz_dict[item]
            found = True
        else:
            # cant find the site in the dictionary so ask the user
            if prompt.lower()=="yes":
                root = Tkinter.Tk(); root.withdraw()
                time_zone = tkSimpleDialog.askstring("Time zone","Enter time zone eg Australia/Melbourne")
                root.destroy()
                found = True
    return time_zone,found

def get_UTCfromlocaltime(ds):
    '''
    Purpose:
     Creates a UTC datetime series in the data structure from the
     local datetime series.
    Usage:
     ldt_UTC = pfp_utils.get_UTCfromlocaltime(ds)
    Assumptions:
     No daylight savings used in the local datetime
    Author: PRI
    '''
    # check the time_zone global attribute is set, we cant continue without it
    if "time_zone" not in ds.globalattributes.keys():
        logger.warning("get_UTCfromlocaltime: time_zone not in global attributes, checking elsewhere ...")
        if "site_name" in ds.globalattributes.keys():
            site_name = ds.globalattributes["site_name"]
        else:
            logger.warning("get_UTCfromlocaltime: site_name not in global attributes, skipping UTC calculation ...")
            return
        time_zone,found = get_timezone(site_name,prompt="no")
        if not found:
            logger.warning("get_UTCfromlocaltime: site_name not in time zone dictionary")
            return
        else:
            logger.info("get_UTCfromlocaltime: time_zone found in time zone dictionary")
            ds.globalattributes["time_zone"] = time_zone
    logger.info(' Getting the UTC datetime from the local datetime')
    # get the number of records
    nRecs = int(ds.globalattributes["nc_nrecs"])
    # get the time zone
    tz = ds.globalattributes["time_zone"]
    # create a timezone object
    loc_tz = pytz.timezone(tz)
    # local pointer to the datetime series in ds
    ldt = ds.series["DateTime"]["Data"]
    # localise the datetime by assigning a time zone
    ldt_loc = [loc_tz.localize(dt) for dt in ldt]
    # remove any daylight saving time
    ldt_loc_nodst = [dt+dt.dst() for dt in ldt_loc]
    # convert to UTC
    ldt_utc = [dt.astimezone(pytz.utc) for dt in ldt_loc_nodst]
    return ldt_utc

def get_xldatefromdatetime(ds):
    '''
    Purpose:
     Returns a list of xldatetime (floating point number represent decimal days
     since 00:00 1/1/1900) from a list of Python datetimes
    Usage:
     pfp_utils.get_xldatefromdatetime(ds)
    Assumptions:
     The Excel datetime series ("xlDateTime") exists in the data structure ds.
    Author: PRI
    '''
    # get the datemode of the original Excel spreadsheet
    if "xl_datemode" in ds.globalattributes.keys():
        datemode = int(ds.globalattributes["xl_datemode"])
    else:
        datemode = int(0)
    nRecs = int(ds.globalattributes["nc_nrecs"])
    # get the Excel datetime attributes
    xldt_attr = MakeAttributeDictionary(long_name="Date/time in Excel format",units="days since 1899-12-31 00:00:00")
    # get a local pointer to the Python DateTime series in ds
    ldt = ds.series["DateTime"]["Data"]
    flag = ds.series["DateTime"]["Flag"]
    # get a list of Excel datetimes from the Python datetime objects
    xldate = [xlrd.xldate.xldate_from_datetime_tuple((ldt[i].year,
                                                      ldt[i].month,
                                                      ldt[i].day,
                                                      ldt[i].hour,
                                                      ldt[i].minute,
                                                      ldt[i].second),
                                                      datemode) for i in range(0,len(ldt))]
    xldt_new = numpy.ma.array(xldate, dtype=numpy.float64)
    # create the Excel datetime series
    CreateSeries(ds,"xlDateTime",xldt_new,flag,xldt_attr)

def get_ymdhmsfromdatetime(ds):
    '''
    Purpose:
     Gets the year, month, day, hour, minute and second from a list of
     Python datetimes.  The Python datetime series is read from
     the input data structure and the results are written back to the
     data structure.
    Usage:
     pfp_utils.get_ymdhmsfromdatetime(ds)
    Assumptions:
     None
    Author: PRI
    '''
    nRecs = int(ds.globalattributes["nc_nrecs"])
    dt = ds.series["DateTime"]["Data"]
    flag = numpy.zeros(nRecs,dtype=numpy.int32)
    Year = numpy.array([dt[i].year for i in range(0,nRecs)]).astype(numpy.int32)
    Month = numpy.array([dt[i].month for i in range(0,nRecs)]).astype(numpy.int32)
    Day = numpy.array([dt[i].day for i in range(0,nRecs)]).astype(numpy.int32)
    Hour = numpy.array([dt[i].hour for i in range(0,nRecs)]).astype(numpy.int32)
    Minute = numpy.array([dt[i].minute for i in range(0,nRecs)]).astype(numpy.int32)
    Second = numpy.array([dt[i].second for i in range(0,nRecs)]).astype(numpy.int32)
    Hdh = numpy.array([float(Hour[i])+float(Minute[i])/60. for i in range(0,nRecs)]).astype(numpy.float64)
    Ddd = numpy.array([(dt[i] - datetime.datetime(Year[i],1,1)).days+1+Hdh[i]/24. for i in range(0,nRecs)]).astype(numpy.float64)
    CreateSeries(ds,'Year',Year,flag,MakeAttributeDictionary(long_name='Year',units='none'))
    CreateSeries(ds,'Month',Month,flag,MakeAttributeDictionary(long_name='Month',units='none'))
    CreateSeries(ds,'Day',Day,flag,MakeAttributeDictionary(long_name='Day',units='none'))
    CreateSeries(ds,'Hour',Hour,flag,MakeAttributeDictionary(long_name='Hour',units='none'))
    CreateSeries(ds,'Minute',Minute,flag,MakeAttributeDictionary(long_name='Minute',units='none'))
    CreateSeries(ds,'Second',Second,flag,MakeAttributeDictionary(long_name='Second',units='none'))
    CreateSeries(ds,'Hdh',Hdh,flag,MakeAttributeDictionary(long_name='Decimal hour of the day',units='none'))
    CreateSeries(ds,'Ddd',Ddd,flag,MakeAttributeDictionary(long_name='Decimal day of the year',units='none'))

def get_ymdhmsfromxldate(ds):
    """
        Gets year, month, day, hour, and if available seconds, from
        excel-formatted Timestamp

        Usage pfp_ts.get_ymdhmsfromxldate(ds)
        cf: control file
        ds: data structure
        """
    logger.info(' Getting date and time variables')
    # get the date mode of the original Excel datetime
    datemode = int(ds.globalattributes['xl_datemode'])
    nRecs = len(ds.series['xlDateTime']['Data'])
    Year = numpy.array([c.missing_value]*nRecs,numpy.int32)
    Month = numpy.array([c.missing_value]*nRecs,numpy.int32)
    Day = numpy.array([c.missing_value]*nRecs,numpy.int32)
    Hour = numpy.array([c.missing_value]*nRecs,numpy.int32)
    Minute = numpy.array([c.missing_value]*nRecs,numpy.int32)
    Second = numpy.array([c.missing_value]*nRecs,numpy.int32)
    Hdh = numpy.array([c.missing_value]*nRecs,numpy.float64)
    Ddd = numpy.array([c.missing_value]*nRecs,numpy.float64)
    flag = numpy.zeros(nRecs)
    for i in range(nRecs):
        DateTuple = xlrd.xldate_as_tuple(ds.series['xlDateTime']['Data'][i],datemode)
        Year[i] = int(DateTuple[0])
        Month[i] = int(DateTuple[1])
        Day[i] = int(DateTuple[2])
        Hour[i] = int(DateTuple[3])
        Minute[i] = int(DateTuple[4])
        Second[i] = int(DateTuple[5])
        Hdh[i] = float(DateTuple[3])+float(DateTuple[4])/60.
        Ddd[i] = ds.series['xlDateTime']['Data'][i] - xlrd.xldate.xldate_from_date_tuple((Year[i],1,1),datemode) + 1
    CreateSeries(ds,'Year',Year,flag,MakeAttributeDictionary(long_name='Year',units='none'))
    CreateSeries(ds,'Month',Month,flag,MakeAttributeDictionary(long_name='Month',units='none'))
    CreateSeries(ds,'Day',Day,flag,MakeAttributeDictionary(long_name='Day',units='none'))
    CreateSeries(ds,'Hour',Hour,flag,MakeAttributeDictionary(long_name='Hour',units='none'))
    CreateSeries(ds,'Minute',Minute,flag,MakeAttributeDictionary(long_name='Minute',units='none'))
    CreateSeries(ds,'Second',Second,flag,MakeAttributeDictionary(long_name='Second',units='none'))
    CreateSeries(ds,'Hdh',Hdh,flag,MakeAttributeDictionary(long_name='Decimal hour of the day',units='none'))
    CreateSeries(ds,'Ddd',Ddd,flag,MakeAttributeDictionary(long_name='Decimal day of the year',units='none'))

def haskey(cf,ThisOne,key):
    return key in cf['Variables'][ThisOne].keys()

def incf(cf,ThisOne):
    return ThisOne in cf['Variables'].keys()

def linear_function(B,x):
    """
    Purpose:
     Linear function for use with orthogonal distance regression.
    Usage:
     linear = scipy.odr.Model(pfp_utils.linear_function)
     where B is a list of slope and offset values
           x is an array of x values
    """
    return B[0]*x + B[1]

def MakeAttributeDictionary(**kwargs):
    """
    Purpose:
     Make an attribute dictionary.
    Usage:
     attr_new = pfp_utils.MakeAttributeDictionary(long_name = "some string",attr_exist)
     where long_name is an attribute to be written to the new attribute dictionary
           attr_exist is an existing attribute dictionary
    Author: PRI
    Date: Back in the day
    """
    default_list = ["ancillary_variables","height","instrument","long_name","serial_number","standard_name",
                    "units","valid_range"]
    attr = {}
    for item in kwargs:
        if isinstance(item, dict):
            for entry in item: attr[entry] = item[entry]
        else:
            attr[item] = kwargs.get(item,"not defined")
        if item in default_list: default_list.remove(item)
    if len(default_list)!=0:
        for item in default_list:
            if item == "valid_range":
                attr[item] = str(c.small_value)+","+str(c.large_value)
            else:
                attr[item] = "not defined"
    attr["missing_value"] = c.missing_value
    return copy.deepcopy(attr)

def make_attribute_dictionary(**kwargs):
    """
    Purpose:
     Make an empty attribute dictionary.
    Usage:
     attr_new = pfp_utils.make_attribute_dictionary(long_name = "some string",attr_exist)
     where long_name is an attribute to be written to the new attribute dictionary
           attr_exist is an existing attribute dictionary
    Author: PRI
    Date: Back in the day
    """
    default_list = ['ancillary_variables', 'height', 'instrument', 'serial_number',
                    'standard_name', 'long_name', 'units']
    attr = {}
    for item in kwargs:
        if isinstance(item, dict):
            for entry in item:
                attr[entry] = item[entry]
        else:
            attr[item] = kwargs.get(item, 'not defined')
        if item in default_list:
            default_list.remove(item)
    if len(default_list) != 0:
        for item in default_list:
            attr[item] = 'not defined'
    attr["missing_value"] = c.missing_value
    return copy.deepcopy(attr)

def MakeQCFlag(ds,SeriesList):
    flag = []
    if len(SeriesList)<=0:
        #log.info('  MakeQCFlag: no series list specified')
        pass
    if len(SeriesList)==1:
        if SeriesList[0] in ds.series.keys():
            flag = ds.series[SeriesList[0]]['Flag'].copy()
        else:
            logger.error('  MakeQCFlag: series '+str(SeriesList[0])+' not in ds.series')
    if len(SeriesList)>1:
        for ThisOne in SeriesList:
            if ThisOne in ds.series.keys():
                if len(flag)==0:
                    #flag = numpy.ones(numpy.size(ds.series[ThisOne]['Flag']))
                    flag = ds.series[ThisOne]['Flag'].copy()
                else:
                    tmp_flag = ds.series[ThisOne]['Flag'].copy()      # get a temporary copy of the flag
                    index = numpy.where(numpy.mod(tmp_flag,10)==0)    # find the elements with flag = 0, 10, 20 etc
                    tmp_flag[index] = 0                               # set them all to 0
                    flag = numpy.maximum(flag,tmp_flag)               # now take the maximum
            else:
                logger.error('  MakeQCFlag: series '+ThisOne+' not in ds.series')
    return flag.astype(numpy.int32)

def MAtoSeries(Series):
    """
    Convert a masked array to a numpy ndarray with masked elements set to c.missing_value.
    Useage:
     Series, WasMA = MAtoSeries(Series)
     where:
      Series (input)    is the data series to be converted.
      WasMA  (returned) is a logical, True if the input series was a masked array.
      Series (output)   is the input series convered to an ndarray with c.missing_value values
                        for missing data.
    """
    WasMA = False
    if numpy.ma.isMA(Series):
        WasMA = True
        Series = numpy.ma.filled(Series,float(c.missing_value))
    return Series, WasMA

def MergeQCFlag(QCFlag_list):
    """ Merge a list of QC flags by taking the element-wise maximum."""
    if len(QCFlag_list)==0: return None
    if len(QCFlag_list)==1: return QCFlag_list[0]
    flag = QCFlag_list[0].copy()                            # get a copy of the first flag
    for item in QCFlag_list[1:]:                            # loop over the list of flags
        tmp_flag = item.copy()                              # get a copy of the next flag
        index = numpy.where(numpy.mod(tmp_flag,10)==0)      # find the elements with flag = 0, 10, 20 etc
        tmp_flag[index] = 0                                 # set them all to 0
        flag = numpy.maximum(flag,tmp_flag)                 # now take the maximum
    return flag

def nxMom_nxScalar_alpha(zoL):
    nRecs = numpy.size(zoL)
    nxMom = numpy.ma.ones(nRecs) * 0.079
    nxScalar = numpy.ma.ones(nRecs) * 0.085
    alpha = numpy.ma.ones(nRecs) * 0.925
    #  get the index of stable conditions
    stable = numpy.ma.where(zoL>0)[0]
    #  now set the series to their stable values
    nxMom[stable] = 0.079 * (1 + 7.9 * zoL[stable]) ** 0.75
    nxScalar[stable] = 2.0 - 1.915 / (1 + 0.5 * zoL[stable])
    alpha[stable] = 1
    return nxMom, nxScalar, alpha

def parse_rangecheck_limits(s):
    """
    Purpose:
     Parse the RangeCheck limits string either read from a control file or
     from a variable attribute without resorting to Python's eval statement.
     And as a bonus, we will do some error checking ...
    Usage:
     rangecheck_limit_list = pfp_utils.parse_rangecheck_limits(s)
     where s is the input string
           rangecheck_limits_list is the returned list
    Side effects:
     Returns an empty list and logs an error message if the input string can
     not be handled.
    Author: PRI
    Date: September 2017
    """
    # initialise the returned list to an empty list
    l = []
    # check to see that a string was passed in
    if not isinstance(s, basestring):
        # error message and return if input was not a string
        msg = "parse_rangecheck_limits: argument must be a string"
        logger.error(msg)
    elif "]*" in s:
        # might be a string using the shorthand "expand this" notation
        try:
            # let's try to parse this construct
            val = s[s.index('[')+1:s.index(']')]
            rep = s[s.index('*')+1:]
            # there must be 1 value per month
            if rep == "12":
                # construct the list if there are 12 values
                if "." in val:
                    l = [float(val)]*int(rep)
                else:
                    l = [int(val)]*int(rep)
            else:
                # error if not 12 values
                msg = "parse_rangecheck_limits: expected 12 repetitions, got "+rep
                logger.error(msg)
        except:
            # and error if we can't
            msg = "parse_rangecheck_limits: unable to parse string "+s
            logger.error(msg)
    else:
        # might be a list as a string
        try:
            # in which case literal_eval will do the trick
            l = ast.literal_eval(s)
            # there must be 1 value per month
            if len(l) != 12:
                # error if not 12 values
                l = []
                msg = "parse_rangecheck_limits: expected 12 in list, got "+str(len(l))
                logger.error(msg)
        except:
            # error if literal_eval can't handle this string
            msg = "parse_rangecheck_limits: literal_eval unable to parse string "+s
            logger.error(msg)
    # return the list
    return l

def path_exists(pathname,mode="verbose"):
    if not os.path.isdir(pathname):
        if mode=="verbose":
            logger.error(' Path '+pathname+' not found')
        return False
    else:
        return True

def perdelta(start, end, delta):
    """
    Yields an iterator of datetime objects from start to end with time step delta.
    """
    curr = start
    while curr <= end:
        yield curr
        curr += delta

def polyval(p,x):
    """
    Replacement for the polyval routine in numpy.  This version doesnt check the
    input variables to make sure they are array_like.  This means that when
    masked arrays are treated correctly when they are passed to this routine.
    Parameters
    ----------
     p : a 1D array of coefficients, highest order first
     x : a 1D array of points at which to evaluate the polynomial described by
         the coefficents in p
    Example
    -------
    >>> x = numpy.array([1,2,3])
    >>> p = numpy.array([2,0])
    >>> pfp_utils.polyval(p,x)
        array([2,4,6])
    >>> y = numpy.array([1,c.missing_value,3])
    >>> y = numpy.ma.masked_where(y==c.missing_value,y)
    >>> pfp_utils.polyval(p,y)
    masked_array(data = [2 -- 6],
                 mask = [False True False],
                 fill_value = 999999)
    """
    y = 0
    for i in range(len(p)):
        y = x*y + p[i]
    return y

def rounddttots(dt,ts=30):
    """
    Purpose:
     Round the time stamp to the nearest time step.
    Usage:
    Author: PRI (probably stolen from StackOverFlow)
    Date: Back in the day
    """
    dt += datetime.timedelta(minutes=int(ts/2))
    dt -= datetime.timedelta(minutes=dt.minute % int(ts),seconds=dt.second,microseconds=dt.microsecond)
    return dt

def rounddttoseconds(dt):
    """
    Purpose:
     Round the time stamp to the nearest the nearest second.
    Usage:
    Author: PRI (probably stolen from StackOverFlow)
    Date: Back in the day
    """
    dt += datetime.timedelta(seconds=0.5)
    dt -= datetime.timedelta(seconds=dt.second % 1,microseconds=dt.microsecond)
    return dt

def round_datetime(ds,mode="nearest_timestep"):
    """
    Purpose:
     Round the series of Python datetimes to the nearest time based on mode
    Usage:
     pfp_utils.round_datetime(ds,mode=mode)
     where;
      mode = "nearest_second" rounds to the nearesy second
      mode = "nearest_timestep" rounds to the nearest time step
    Author: PRI
    Date: February 2015
    """
    # local pointer to the datetime series
    ldt = ds.series["DateTime"]["Data"]
    # check which rounding option has been chosen
    if mode.lower()=="nearest_timestep":
        # get the time step
        if "time_step" in ds.globalattributes:
            ts = int(ds.globalattributes["time_step"])
        else:
            ts = numpy.mean(get_timestep(ds)/60)
            ts = roundtobase(ts,base=30)
            ds.globalattributes["time_step"] = ts
        # round to the nearest time step
        rldt = [rounddttots(dt,ts=ts) for dt in ldt]
    elif mode.lower()=="nearest_second":
        # round to the nearest second
        rldt = [rounddttoseconds(dt) for dt in ldt]
    else:
        # unrecognised option for mode, return original datetime series
        logger.error(" round_datetime: unrecognised mode ("+str(mode)+")"+" ,returning original time series")
        rldt = ds.series["DateTime"]["Data"]
    # replace the original datetime series with the rounded one
    ds.series["DateTime"]["Data"] = numpy.array(rldt)
    return

def roundtobase(x,base=5):
    return int(base*round(float(x)/base))

def round2sig(x,sig=2):
    '''
    Round a float to a specified number of significant digits (default is 2).
    '''
    return round(x, sig-int(math.floor(math.log10(abs(x))))-1)

def r(b, p, alpha):
    """
    Function to calculate the r coeficient of the Massman frequency correction.
    """
    r = ((b ** alpha) / (b ** alpha + 1)) * \
           ((b ** alpha) / (b ** alpha + p ** alpha)) * \
           (1 / (p ** alpha + 1))
    return r

def SeriestoMA(Series):
    """
    Convert a numpy ndarray to a masked array.
    Useage:
     Series, WasND = SeriestoMA(Series)
     where:
      Series (input)    is the data series to be converted.
      WasND  (returned) is a logical, True if the input series was an ndarray
      Series (output)   is the input series convered to a masked array.
    """
    WasND = False
    if Series.dtype == "float64":
        if not numpy.ma.isMA(Series):
            WasND = True
            Series = numpy.ma.masked_where(abs(Series-numpy.float64(c.missing_value)) < c.eps, Series)
    return Series, WasND

def SetUnitsInds(ds, ThisOne, units):
    ds.series[ThisOne]['Attr']['units'] = units

def startlog(loggername,loggerfile):
    logger = logging.getLogger(loggername)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(loggerfile)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
    #formatter = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-6s %(message)s', '%d-%m-%y %H:%M')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

def UpdateGlobalAttributes(cf,ds,level):
    ds.globalattributes["nc_level"] = str(level)
    ds.globalattributes["EPDversion"] = sys.version
    # put the control file name into the global attributes
    if "controlfile_name" in cf:
        ds.globalattributes["controlfile_name"] = cf["controlfile_name"]
    if "Global" in cf:
        for item in cf["Global"].keys():
            if item not in ds.globalattributes.keys():
                ds.globalattributes[item] = cf["Global"][item].replace("\n"," ").replace("\r","")

def update_progress(progress):
    barLength = 50 # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(barLength*progress))
    progress = round(progress,2)
    text = "\rPercent: [{0}] {1}% {2}".format( "#"*block + "-"*(barLength-block), progress*100, status)
    sys.stdout.write(text)
    sys.stdout.flush()
