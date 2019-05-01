"""
Purpose:
 Reads the hourly ACCESS files pulled from the BoM OPeNDAP site
 and concatenates them into a single file.
 This script file takes a control file name on the command line.
 The control file lists the sites to be processed and the variables
 to be processed.
 Normal usage is to process all files in a monthly sub-directory.
Usage:
 python access_concat.py access_concat.txt
Author: PRI
Date: September 2015
"""
# Python modules
import configobj
import datetime
import glob
import logging
import netCDF4
import numpy
import os
import pytz
import pdb
from scipy.interpolate import interp1d
import sys
# since the scripts directory is there, try importing the modules
sys.path.append('../scripts')
# PFP
import constants as c
import meteorologicalfunctions as mf
import qcio
import qcutils

# !!! classes !!!
class ACCESSData(object):
    def __init__(self):
        self.globalattr = {}
        self.globalattr["file_list"] = []
        self.variables = {}
        self.varattr = {}

# !!! start of function definitions !!!
def get_info_dict(cf,site):
    info = {}
    in_path = cf["Sites"][site]["in_filepath"]
    in_name = cf["Sites"][site]["in_filename"]
    info["in_filename"] = os.path.join(in_path,in_name)
    out_path = cf["Sites"][site]["out_filepath"]
    if not os.path.exists(out_path): os.makedirs(out_path)
    out_name = cf["Sites"][site]["out_filename"]
    info["out_filename"] = os.path.join(out_path,out_name)
    info["interpolate"] = True
    if not cf["Sites"][site].as_bool("interpolate"):
        info["interpolate"] = False
    info["site_name"] = cf["Sites"][site]["site_name"]
    info["site_timezone"] = cf["Sites"][site]["site_timezone"]
    info["site_tz"] = pytz.timezone(info["site_timezone"])
    return info

def get_datetime(ds_60minutes,f,info):
    valid_date = f.variables["valid_date"][:]
    nRecs = len(valid_date)
    valid_time = f.variables["valid_time"][:]
    dl = [datetime.datetime.strptime(str(int(valid_date[i])*10000+int(valid_time[i])),"%Y%m%d%H%M") for i in range(0,nRecs)]
    dt_utc_all = numpy.array(dl)
    time_step = numpy.array([(dt_utc_all[i]-dt_utc_all[i-1]).total_seconds() for i in range(1,len(dt_utc_all))])
    time_step = numpy.append(time_step,3600)
    idx = numpy.where(time_step!=0)[0]
    dt_utc = dt_utc_all[idx]
    dt_utc = [x.replace(tzinfo=pytz.utc) for x in dt_utc]
    dt_loc = [x.astimezone(info["site_tz"]) for x in dt_utc]
    dt_loc = [x-x.dst() for x in dt_loc]
    dt_loc = [x.replace(tzinfo=None) for x in dt_loc]
    ds_60minutes.series["DateTime"] = {}
    ds_60minutes.series["DateTime"]["Data"] = dt_loc
    nRecs = len(ds_60minutes.series["DateTime"]["Data"])
    ds_60minutes.globalattributes["nc_nrecs"] = nRecs
    return idx

def set_globalattributes(ds_60minutes,info):
    ds_60minutes.globalattributes["time_step"] = 60
    ds_60minutes.globalattributes["time_zone"] = info["site_timezone"]
    ds_60minutes.globalattributes["site_name"] = info["site_name"]
    ds_60minutes.globalattributes["xl_datemode"] = 0
    ds_60minutes.globalattributes["nc_level"] = "L1"
    return

def get_accessdata(cf,ds_60minutes,f,info):
            # latitude and longitude, chose central pixel of 3x3 grid
    ds_60minutes.globalattributes["latitude"] = f.variables["lat"][1]
    ds_60minutes.globalattributes["longitude"] = f.variables["lon"][1]
    # list of variables to process
    var_list = cf["Variables"].keys()
    # get a series of Python datetimes and put this into the data structure
    valid_date = f.variables["valid_date"][:]
    nRecs = len(valid_date)
    valid_time = f.variables["valid_time"][:]
    dl = [datetime.datetime.strptime(str(int(valid_date[i])*10000+int(valid_time[i])),"%Y%m%d%H%M") for i in range(0,nRecs)]
    dt_utc_all = numpy.array(dl)
    time_step = numpy.array([(dt_utc_all[i]-dt_utc_all[i-1]).total_seconds() for i in range(1,len(dt_utc_all))])
    time_step = numpy.append(time_step,3600)
    idxne0 = numpy.where(time_step!=0)[0]
    idxeq0 = numpy.where(time_step==0)[0]
    idx_clipped = numpy.where((idxeq0>0)&(idxeq0<nRecs))[0]
    idxeq0 = idxeq0[idx_clipped]
    dt_utc = dt_utc_all[idxne0]
    dt_utc = [x.replace(tzinfo=pytz.utc) for x in dt_utc]
    dt_loc = [x.astimezone(info["site_tz"]) for x in dt_utc]
    dt_loc = [x-x.dst() for x in dt_loc]
    dt_loc = [x.replace(tzinfo=None) for x in dt_loc]
    flag = numpy.zeros(len(dt_loc),dtype=numpy.int32)
    ds_60minutes.series["DateTime"] = {}
    ds_60minutes.series["DateTime"]["Data"] = dt_loc
    ds_60minutes.series["DateTime"]["Flag"] = flag
    ds_60minutes.series["DateTime_UTC"] = {}
    ds_60minutes.series["DateTime_UTC"]["Data"] = dt_utc
    ds_60minutes.series["DateTime_UTC"]["Flag"] = flag
    nRecs = len(ds_60minutes.series["DateTime"]["Data"])
    ds_60minutes.globalattributes["nc_nrecs"] = nRecs
    # we're done with valid_date and valid_time, drop them from the variable list
    for item in ["valid_date","valid_time","lat","lon"]:
        if item in var_list: var_list.remove(item)
    # create the QC flag with all zeros
    nRecs = ds_60minutes.globalattributes["nc_nrecs"]
    flag_60minutes = numpy.zeros(nRecs,dtype=numpy.int32)
    # get the UTC hour
    hr_utc = [x.hour for x in dt_utc]
    attr = qcutils.MakeAttributeDictionary(long_name='UTC hour')
    qcutils.CreateSeries(ds_60minutes,'Hr_UTC',hr_utc,Flag=flag_60minutes,Attr=attr)
    # now loop over the variables listed in the control file
    for label in var_list:
        # get the name of the variable in the ACCESS file
        access_name = qcutils.get_keyvaluefromcf(cf,["Variables",label],"access_name",default=label)
        # warn the user if the variable not found
        if access_name not in f.variables.keys():
            msg = "Requested variable "+access_name
            msg = msg+" not found in ACCESS data"
            logging.error(msg)
            continue
        # get the variable attibutes
        attr = get_variableattributes(f,access_name)
        # loop over the 3x3 matrix of ACCESS grid data supplied
        for i in range(0,3):
            for j in range(0,3):
                label_ij = label+'_'+str(i)+str(j)
                if len(f.variables[access_name].shape)==3:
                    series = f.variables[access_name][:,i,j]
                elif len(f.variables[access_name].shape)==4:
                    series = f.variables[access_name][:,0,i,j]
                else:
                    msg = "Unrecognised variable ("+label
                    msg = msg+") dimension in ACCESS file"
                    logging.error(msg)
                series = series[idxne0]
                qcutils.CreateSeries(ds_60minutes,label_ij,series,
                                     Flag=flag_60minutes,Attr=attr)
    return

def get_variableattributes(f,access_name):
    attr = {}
    # following code for netCDF4.MFDataset()
#    for vattr in f.variables[access_name].ncattrs():
#        attr[vattr] = getattr(f.variables[access_name],vattr)
    # following code for access_read_mfiles2()
    attr = f.varattr[access_name]
    attr["missing_value"] = c.missing_value
    return attr

def changeunits_airtemperature(ds_60minutes):
    attr = qcutils.GetAttributeDictionary(ds_60minutes,"Ta_00")
    if attr["units"] == "K":
        for i in range(0,3):
            for j in range(0,3):
                label = "Ta_"+str(i)+str(j)
                Ta,f,a = qcutils.GetSeriesasMA(ds_60minutes,label)
                Ta = Ta - c.C2K
                attr["units"] = "C"
                qcutils.CreateSeries(ds_60minutes,label,Ta,Flag=f,Attr=attr)
    return

def changeunits_soiltemperature(ds_60minutes):
    attr = qcutils.GetAttributeDictionary(ds_60minutes,"Ts_00")
    if attr["units"] == "K":
        for i in range(0,3):
            for j in range(0,3):
                label = "Ts_"+str(i)+str(j)
                Ts,f,a = qcutils.GetSeriesasMA(ds_60minutes,label)
                Ts = Ts - c.C2K
                attr["units"] = "C"
                qcutils.CreateSeries(ds_60minutes,label,Ts,Flag=f,Attr=attr)
    return

def changeunits_pressure(ds_60minutes):
    attr = qcutils.GetAttributeDictionary(ds_60minutes,"ps_00")
    if attr["units"] == "Pa":
        for i in range(0,3):
            for j in range(0,3):
                label = "ps_"+str(i)+str(j)
                ps,f,a = qcutils.GetSeriesasMA(ds_60minutes,label)
                ps = ps/float(1000)
                attr["units"] = "kPa"
                qcutils.CreateSeries(ds_60minutes,label,ps,Flag=f,Attr=attr)
    return

def get_windspeedanddirection(ds_60minutes):
    for i in range(0,3):
        for j in range(0,3):
            u_label = "u_"+str(i)+str(j)
            v_label = "v_"+str(i)+str(j)
            Ws_label = "Ws_"+str(i)+str(j)
            u,f,a = qcutils.GetSeriesasMA(ds_60minutes,u_label)
            v,f,a = qcutils.GetSeriesasMA(ds_60minutes,v_label)
            Ws = numpy.sqrt(u*u+v*v)
            attr = qcutils.MakeAttributeDictionary(long_name="Wind speed",
                                                   units="m/s",height="10m")
            qcutils.CreateSeries(ds_60minutes,Ws_label,Ws,Flag=f,Attr=attr)
    # wind direction from components
    for i in range(0,3):
        for j in range(0,3):
            u_label = "u_"+str(i)+str(j)
            v_label = "v_"+str(i)+str(j)
            Wd_label = "Wd_"+str(i)+str(j)
            u,f,a = qcutils.GetSeriesasMA(ds_60minutes,u_label)
            v,f,a = qcutils.GetSeriesasMA(ds_60minutes,v_label)
            Wd = float(270) - numpy.ma.arctan2(v,u)*float(180)/numpy.pi
            index = numpy.ma.where(Wd>360)[0]
            if len(index)>0: Wd[index] = Wd[index] - float(360)
            attr = qcutils.MakeAttributeDictionary(long_name="Wind direction",
                                                   units="degrees",height="10m")
            qcutils.CreateSeries(ds_60minutes,Wd_label,Wd,Flag=f,Attr=attr)
    return

def get_relativehumidity(ds_60minutes):
    for i in range(0,3):
        for j in range(0,3):
            q_label = "q_"+str(i)+str(j)
            Ta_label = "Ta_"+str(i)+str(j)
            ps_label = "ps_"+str(i)+str(j)
            RH_label = "RH_"+str(i)+str(j)
            q,f,a = qcutils.GetSeriesasMA(ds_60minutes,q_label)
            Ta,f,a = qcutils.GetSeriesasMA(ds_60minutes,Ta_label)
            ps,f,a = qcutils.GetSeriesasMA(ds_60minutes,ps_label)
            RH = mf.RHfromspecifichumidity(q, Ta, ps)
            attr = qcutils.MakeAttributeDictionary(long_name='Relative humidity',
                                                   units='%',standard_name='not defined')
            qcutils.CreateSeries(ds_60minutes,RH_label,RH,Flag=f,Attr=attr)
    return

def get_absolutehumidity(ds_60minutes):
    for i in range(0,3):
        for j in range(0,3):
            Ta_label = "Ta_"+str(i)+str(j)
            RH_label = "RH_"+str(i)+str(j)
            Ah_label = "Ah_"+str(i)+str(j)
            Ta,f,a = qcutils.GetSeriesasMA(ds_60minutes,Ta_label)
            RH,f,a = qcutils.GetSeriesasMA(ds_60minutes,RH_label)
            Ah = mf.absolutehumidityfromRH(Ta, RH)
            attr = qcutils.MakeAttributeDictionary(long_name='Absolute humidity',
                                                   units='g/m3',standard_name='not defined')
            qcutils.CreateSeries(ds_60minutes,Ah_label,Ah,Flag=f,Attr=attr)
    return

def changeunits_soilmoisture(ds_60minutes):
    attr = qcutils.GetAttributeDictionary(ds_60minutes,"Sws_00")
    for i in range(0,3):
        for j in range(0,3):
            label = "Sws_"+str(i)+str(j)
            Sws,f,a = qcutils.GetSeriesasMA(ds_60minutes,label)
            Sws = Sws/float(100)
            attr["units"] = "frac"
            qcutils.CreateSeries(ds_60minutes,label,Sws,Flag=f,Attr=attr)
    return

def get_radiation(ds_60minutes):
    for i in range(0,3):
        for j in range(0,3):
            label_Fn = "Fn_"+str(i)+str(j)
            label_Fsd = "Fsd_"+str(i)+str(j)
            label_Fld = "Fld_"+str(i)+str(j)
            label_Fsu = "Fsu_"+str(i)+str(j)
            label_Flu = "Flu_"+str(i)+str(j)
            label_Fn_sw = "Fn_sw_"+str(i)+str(j)
            label_Fn_lw = "Fn_lw_"+str(i)+str(j)
            Fsd,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fsd)
            Fld,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fld)
            Fn_sw,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fn_sw)
            Fn_lw,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fn_lw)
            Fsu = Fsd - Fn_sw
            Flu = Fld - Fn_lw
            Fn = (Fsd-Fsu)+(Fld-Flu)
            attr = qcutils.MakeAttributeDictionary(long_name='Up-welling long wave',
                                                   standard_name='surface_upwelling_longwave_flux_in_air',
                                                   units='W/m2')
            qcutils.CreateSeries(ds_60minutes,label_Flu,Flu,Flag=f,Attr=attr)
            attr = qcutils.MakeAttributeDictionary(long_name='Up-welling short wave',
                                                   standard_name='surface_upwelling_shortwave_flux_in_air',
                                                   units='W/m2')
            qcutils.CreateSeries(ds_60minutes,label_Fsu,Fsu,Flag=f,Attr=attr)
            attr = qcutils.MakeAttributeDictionary(long_name='Calculated net radiation',
                                                   standard_name='surface_net_allwave_radiation',
                                                   units='W/m2')
            qcutils.CreateSeries(ds_60minutes,label_Fn,Fn,Flag=f,Attr=attr)
    return

def get_groundheatflux(ds_60minutes):
    for i in range(0,3):
        for j in range(0,3):
            label_Fg = "Fg_"+str(i)+str(j)
            label_Fn = "Fn_"+str(i)+str(j)
            label_Fh = "Fh_"+str(i)+str(j)
            label_Fe = "Fe_"+str(i)+str(j)
            Fn,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fn)
            Fh,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fh)
            Fe,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fe)
            Fg = Fn - Fh - Fe
            attr = qcutils.MakeAttributeDictionary(long_name='Calculated ground heat flux',
                                                   standard_name='downward_heat_flux_in_soil',
                                                   units='W/m2')
            qcutils.CreateSeries(ds_60minutes,label_Fg,Fg,Flag=f,Attr=attr)
    return

def get_availableenergy(ds_60miutes):
    for i in range(0,3):
        for j in range(0,3):
            label_Fg = "Fg_"+str(i)+str(j)
            label_Fn = "Fn_"+str(i)+str(j)
            label_Fa = "Fa_"+str(i)+str(j)
            Fn,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fn)
            Fg,f,a = qcutils.GetSeriesasMA(ds_60minutes,label_Fg)
            Fa = Fn - Fg
            attr = qcutils.MakeAttributeDictionary(long_name='Calculated available energy',
                                                   standard_name='not defined',units='W/m2')
            qcutils.CreateSeries(ds_60minutes,label_Fa,Fa,Flag=f,Attr=attr)
    return

def perdelta(start,end,delta):
    curr = start
    while curr <= end:
        yield curr
        curr += delta

def interpolate_to_30minutes(ds_60minutes):
    ds_30minutes = qcio.DataStructure()
    # copy the global attributes
    for this_attr in ds_60minutes.globalattributes.keys():
        ds_30minutes.globalattributes[this_attr] = ds_60minutes.globalattributes[this_attr]
    # update the global attribute "time_step"
    ds_30minutes.globalattributes["time_step"] = 30
    # generate the 30 minute datetime series
    dt_loc_60minutes = ds_60minutes.series["DateTime"]["Data"]
    dt_loc_30minutes = [x for x in perdelta(dt_loc_60minutes[0],dt_loc_60minutes[-1],datetime.timedelta(minutes=30))]
    nRecs_30minutes = len(dt_loc_30minutes)
    dt_utc_60minutes = ds_60minutes.series["DateTime_UTC"]["Data"]
    dt_utc_30minutes = [x for x in perdelta(dt_utc_60minutes[0],dt_utc_60minutes[-1],datetime.timedelta(minutes=30))]
    # update the global attribute "nc_nrecs"
    ds_30minutes.globalattributes['nc_nrecs'] = nRecs_30minutes
    ds_30minutes.series["DateTime"] = {}
    ds_30minutes.series["DateTime"]["Data"] = dt_loc_30minutes
    flag = numpy.zeros(len(dt_loc_30minutes),dtype=numpy.int32)
    ds_30minutes.series["DateTime"]["Flag"] = flag
    ds_30minutes.series["DateTime_UTC"] = {}
    ds_30minutes.series["DateTime_UTC"]["Data"] = dt_utc_30minutes
    flag = numpy.zeros(len(dt_utc_30minutes),dtype=numpy.int32)
    ds_30minutes.series["DateTime_UTC"]["Flag"] = flag
    # get the year, month etc from the datetime
    qcutils.get_xldatefromdatetime(ds_30minutes)
    qcutils.get_ymdhmsfromdatetime(ds_30minutes)
    # interpolate to 30 minutes
    nRecs_60 = len(ds_60minutes.series["DateTime"]["Data"])
    nRecs_30 = len(ds_30minutes.series["DateTime"]["Data"])
    x_60minutes = numpy.arange(0,nRecs_60,1)
    x_30minutes = numpy.arange(0,nRecs_60-0.5,0.5)
    varlist_60 = ds_60minutes.series.keys()
    # strip out the date and time variables already done
    for item in ["DateTime","DateTime_UTC","xlDateTime","Year","Month","Day","Hour","Minute","Second","Hdh","Hr_UTC"]:
        if item in varlist_60: varlist_60.remove(item)
    # now do the interpolation (its OK to interpolate accumulated precipitation)
    for label in varlist_60:
        series_60minutes,flag,attr = qcutils.GetSeries(ds_60minutes,label)
        ci_60minutes = numpy.zeros(len(series_60minutes))
        idx = numpy.where(abs(series_60minutes-float(c.missing_value))<c.eps)[0]
        ci_60minutes[idx] = float(1)
        int_fn = interp1d(x_60minutes,series_60minutes)
        series_30minutes = int_fn(x_30minutes)
        int_fn = interp1d(x_60minutes,ci_60minutes)
        ci_30minutes = int_fn(x_30minutes)
        idx = numpy.where(abs(ci_30minutes-float(0))>c.eps)[0]
        series_30minutes[idx] = numpy.float64(c.missing_value)
        flag_30minutes = numpy.zeros(nRecs_30, dtype=numpy.int32)
        flag_30minutes[idx] = numpy.int32(1)
        qcutils.CreateSeries(ds_30minutes,label,series_30minutes,Flag=flag_30minutes,Attr=attr)
    # get the UTC hour
    hr_utc = [float(x.hour)+float(x.minute)/60 for x in dt_utc_30minutes]
    attr = qcutils.MakeAttributeDictionary(long_name='UTC hour')
    flag_30minutes = numpy.zeros(nRecs_30, dtype=numpy.int32)
    qcutils.CreateSeries(ds_30minutes,'Hr_UTC',hr_utc,Flag=flag_30minutes,Attr=attr)
    return ds_30minutes

def get_instantaneous_precip30(ds_30minutes):
    hr_utc,f,a = qcutils.GetSeries(ds_30minutes,'Hr_UTC')
    for i in range(0,3):
        for j in range(0,3):
            label = "Precip_"+str(i)+str(j)
            # get the accumulated precipitation
            accum,flag,attr = qcutils.GetSeries(ds_30minutes,label)
            # get the 30 minute precipitation
            precip = numpy.ediff1d(accum,to_begin=0)
            # now we deal with the reset of accumulated precipitation at 00, 06, 12 and 18 UTC
            # indices of analysis times 00, 06, 12, and 18
            idx1 = numpy.where(numpy.mod(hr_utc,6)==0)[0]
            # set 30 minute precipitation at these times to half of the analysis value
            precip[idx1] = accum[idx1]/float(2)
            # now get the indices of the 30 minute period immediately the analysis time
            # these values will have been interpolated between the last forecast value
            # and the analysis value, they need to be set to half of the analysis value
            idx2 = idx1-1
            # remove negative indices
            idx2 = idx2[idx2>=0]
            # set these 30 minute times to half the analysis value
            precip[idx2] = accum[idx2+1]/float(2)
            # set precipitations less than 0.01 mm to 0
            idx3 = numpy.ma.where(precip<0.01)[0]
            precip[idx3] = float(0)
            # set instantaneous precipitation to missing when accumlated precipitation was missing
            idx = numpy.where(flag!=0)[0]
            precip[idx] = float(c.missing_value)
            # set some variable attributes
            attr["long_name"] = "Precipitation total over time step"
            attr["units"] = "mm/30 minutes"
            qcutils.CreateSeries(ds_30minutes,label,precip,Flag=flag,Attr=attr)
    return

def get_instantaneous_precip60(ds_60minutes):
    hr_utc,f,a = qcutils.GetSeries(ds_60minutes,'Hr_UTC')
    for i in range(0,3):
        for j in range(0,3):
            label = "Precip_"+str(i)+str(j)
            # get the accumulated precipitation
            accum,flag,attr = qcutils.GetSeries(ds_60minutes,label)
            # get the 30 minute precipitation
            precip = numpy.ediff1d(accum,to_begin=0)
            # now we deal with the reset of accumulated precipitation at 00, 06, 12 and 18 UTC
            # indices of analysis times 00, 06, 12, and 18
            idx1 = numpy.where(numpy.mod(hr_utc,6)==0)[0]
            # set 30 minute precipitation at these times to the analysis value
            precip[idx1] = accum[idx1]
            # set accumulated precipitations less than 0.001 mm to 0
            idx2 = numpy.ma.where(precip<0.01)[0]
            precip[idx2] = float(0)
            # set instantaneous precipitation to missing when accumlated precipitation was missing
            idx = numpy.where(flag!=0)[0]
            precip[idx] = float(c.missing_value)
            # set some variable attributes
            attr["long_name"] = "Precipitation total over time step"
            attr["units"] = "mm/60 minutes"
            qcutils.CreateSeries(ds_60minutes,label,precip,Flag=flag,Attr=attr)

def access_read_mfiles2(file_list,var_list=[]):
    f = ACCESSData()
    # check that we have a list of files to process
    if len(file_list)==0:
        print "access_read_mfiles: empty file_list received, returning ..."
        return f
    # make sure latitude and longitude are read
    if "lat" not in var_list: var_list.append("lat")
    if "lon" not in var_list: var_list.append("lon")
    # make sure valid_date and valid_time are read
    if "valid_date" not in var_list: var_list.append("valid_date")
    if "valid_time" not in var_list: var_list.append("valid_time")
    for file_name in file_list:
        # open the netCDF file
        ncfile = netCDF4.Dataset(file_name)
        # check the number of records
        dims = ncfile.dimensions
        shape = (len(dims["time"]),len(dims["lat"]),len(dims["lon"]))
        # move to the next file if this file doesn't have 25 time records
        if shape[0]!=1:
            print "access_read_mfiles: length of time dimension in "+file_name+" is "+str(shape[0])+" (expected 1)"
            continue
        # move to the next file if this file doesn't have 3 latitude records
        if shape[1]!=3:
            print "access_read_mfiles: length of lat dimension in "+file_name+" is "+str(shape[1])+" (expected 3)"
            continue
        # move to the next file if this file doesn't have 3 longitude records
        if shape[2]!=3:
            print "access_read_mfiles: length of lon dimension in "+file_name+" is "+str(shape[2])+" (expected 3)"
            continue
        # seems OK to continue with this file ...
        # add the file name to the file_list in the global attributes
        f.globalattr["file_list"].append(file_name)
        # get the global attributes
        for gattr in ncfile.ncattrs():
            if gattr not in f.globalattr:
                f.globalattr[gattr] = getattr(ncfile,gattr)
        # if no variable list was passed to this routine, use all variables
        if len(var_list)==0:
            var_list=ncfile.variables.keys()
        # load the data into the data structure
        for var in var_list:
            # get the name of the variable in the ACCESS file
            access_name = qcutils.get_keyvaluefromcf(cf,["Variables",var],"access_name",default=var)
            # check that the requested variable exists in the ACCESS file
            if access_name in ncfile.variables.keys():
                # check to see if the variable is already in the data structure
                if access_name not in f.variables.keys():
                    f.variables[access_name] = ncfile.variables[access_name][:]
                else:
                    f.variables[access_name] = numpy.concatenate((f.variables[access_name],ncfile.variables[access_name][:]),axis=0)
                # now copy the variable attribiutes
                # create the variable attribute dictionary
                if access_name not in f.varattr: f.varattr[access_name] = {}
                # loop over the variable attributes
                for this_attr in ncfile.variables[access_name].ncattrs():
                    # check to see if the attribute has already 
                    if this_attr not in f.varattr[access_name].keys():
                        # add the variable attribute if it's not there already
                        f.varattr[access_name][this_attr] = getattr(ncfile.variables[access_name],this_attr)
            else:
                print "access_read_mfiles: ACCESS variable "+access_name+" not found in "+file_name
                if access_name not in f.variables.keys():
                    f.variables[access_name] = makedummyseries(shape)
                else:
                    f.variables[access_name] = numpy.concatenate((f.variables[access_name],makedummyseries(shape)),axis=0)
        # close the netCDF file
        ncfile.close()
    # return with the data structure
    return f

def makedummyseries(shape):
    return numpy.ma.masked_all(shape)
# !!! end of function definitions !!!

# !!! start of main program !!!
# start the logger
logging.basicConfig(filename='access_concat.log',level=logging.DEBUG)
console = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
console.setFormatter(formatter)
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)
# get the control file name from the command line
#cf_name = sys.argv[1]
cf_name = qcio.get_controlfilename(path='../controlfiles',title='Choose a control file')
# get the control file contents
logging.info('Reading the control file')
cf = configobj.ConfigObj(cf_name)
# get stuff from the control file
logging.info('Getting control file contents')
site_list = cf["Sites"].keys()
var_list = cf["Variables"].keys()
# loop over sites
#site_list = ["AdelaideRiver"]
for site in site_list:
    info = get_info_dict(cf,site)
    logging.info("Processing site "+info["site_name"])
    # instance the data structures
    logging.info('Creating the data structures')
    ds_60minutes = qcio.DataStructure()
    # get a sorted list of files that match the mask in the control file
    file_list = sorted(glob.glob(info["in_filename"]))
    # read the netcdf files
    logging.info('Reading the netCDF files for '+info["site_name"])
    f = access_read_mfiles2(file_list,var_list=var_list)
    # get the data from the netCDF files and write it to the 60 minute data structure
    logging.info('Getting the ACCESS data')
    get_accessdata(cf,ds_60minutes,f,info)
    # set some global attributes
    logging.info('Setting global attributes')
    set_globalattributes(ds_60minutes,info)
    # check for time gaps in the file
    logging.info("Checking for time gaps")
    if qcutils.CheckTimeStep(ds_60minutes):
        qcutils.FixTimeStep(ds_60minutes)
    # get the datetime in some different formats
    logging.info('Getting xlDateTime and YMDHMS')
    qcutils.get_xldatefromdatetime(ds_60minutes)
    qcutils.get_ymdhmsfromdatetime(ds_60minutes)
    #f.close()
    # get derived quantities and adjust units
    logging.info("Changing units and getting derived quantities")
    # air temperature from K to C
    changeunits_airtemperature(ds_60minutes)
    # soil temperature from K to C
    changeunits_soiltemperature(ds_60minutes)
    # pressure from Pa to kPa
    changeunits_pressure(ds_60minutes)
    # wind speed from components
    get_windspeedanddirection(ds_60minutes)
    # relative humidity from temperature, specific humidity and pressure
    get_relativehumidity(ds_60minutes)
    # absolute humidity from temperature and relative humidity
    get_absolutehumidity(ds_60minutes)
    # soil moisture from kg/m2 to m3/m3
    changeunits_soilmoisture(ds_60minutes)
    # net radiation and upwelling short and long wave radiation
    get_radiation(ds_60minutes)
    # ground heat flux as residual
    get_groundheatflux(ds_60minutes)
    # Available energy
    get_availableenergy(ds_60minutes)
    if info["interpolate"]:
        # interploate from 60 minute time step to 30 minute time step
        logging.info("Interpolating data to 30 minute time step")
        ds_30minutes = interpolate_to_30minutes(ds_60minutes)
        # get instantaneous precipitation from accumulated precipitation
        get_instantaneous_precip30(ds_30minutes)
        # write to netCDF file
        logging.info("Writing 30 minute data to netCDF file")
        ncfile = qcio.nc_open_write(info["out_filename"])
        qcio.nc_write_series(ncfile, ds_30minutes,ndims=1)
    else:
        # get instantaneous precipitation from accumulated precipitation
        get_instantaneous_precip60(ds_60minutes)
        # write to netCDF file
        logging.info("Writing 60 minute data to netCDF file")
        ncfile = qcio.nc_open_write(info["out_filename"])
        qcio.nc_write_series(ncfile, ds_60minutes,ndims=1)

logging.info('All done!')
