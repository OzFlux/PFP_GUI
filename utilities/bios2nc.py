import sys
sys.path.append('../scripts')
import constants as c
import glob
import meteorologicalfunctions as mf
import netCDF4
import numpy
import os.path
import qcio
import qcutils

# open the logging file
log = qcutils.startlog('bios2nc','../logfiles/bios2nc.log')

# get the control file
cf = qcio.load_controlfile(path='../controlfiles')
if len(cf)==0: sys.exit()
start_date = cf["General"]["start_date"]
end_date = cf["General"]["end_date"]
var_list = cf["Variables"].keys()
site_list = cf["Sites"].keys()
for site in site_list:
    # get the input file mask
    infilename = cf["Sites"][site]["in_filepath"]+cf["Sites"][site]["in_filename"]
    if not os.path.isfile(infilename):
        log.error("netCDF file "+infilename+" not found, skipping ...")
        continue
    log.info("Starting site: "+site)
    # get a data structure
    ds_30 = qcio.DataStructure()
    # get the output file name
    outfilename = cf["Sites"][site]["out_filepath"]+cf["Sites"][site]["out_filename"]
    # average to 30 minutes or not
    average = True
    if not cf["Sites"][site].as_bool("average"): average = False
    # get the site time zone
    site_timezone = cf["Sites"][site]["site_timezone"]
    # read the BIOS file
    bios_ncfile = netCDF4.Dataset(infilename)
    time = bios_ncfile.variables["time"][:]
    nRecs = len(time)
    # set some global attributes
    ts = ds_30.globalattributes["time_step"] = 30
    ds_30.globalattributes["time_zone"] = site_timezone
    ds_30.globalattributes["nc_nrecs"] = nRecs
    ds_30.globalattributes["xl_datemode"] = str(0)
    ds_30.globalattributes["site_name"] = cf["Sites"][site]["site_name"]
    time_units = getattr(bios_ncfile.variables["time"],"units")
    qcutils.get_datetimefromnctime(ds_30,time,time_units)
    qcutils.round_datetime(ds_30,mode="nearest_timestep")
    if qcutils.CheckTimeStep(ds_30): qcutils.FixTimeStep(ds_30)
    ldt_30 = ds_30.series["DateTime"]["Data"]
    si = qcutils.GetDateIndex(ldt_30,start_date,default=0,ts=ts,match="startnexthour")
    ei = qcutils.GetDateIndex(ldt_30,end_date,default=len(ldt_30),ts=ts,match="endprevioushour")
    ds_30.series["DateTime"]["Data"] = ds_30.series["DateTime"]["Data"][si:ei+1]
    ds_30.series["DateTime"]["Flag"] = ds_30.series["DateTime"]["Flag"][si:ei+1]
    ldt_30 = ds_30.series["DateTime"]["Data"]
    nRecs = ds_30.globalattributes["nc_nrecs"] = len(ldt_30)
    flag = numpy.zeros(nRecs)
    qcutils.get_ymdhmsfromdatetime(ds_30)
    xl_date_loc = qcutils.get_xldatefromdatetime(ds_30)
    attr = qcutils.MakeAttributeDictionary(long_name="Date/time (local) in Excel format",units="days since 1899-12-31 00:00:00")
    qcutils.CreateSeries(ds_30,"xlDateTime",xl_date_loc,flag,attr)
    # get the data
    for label in var_list:
        bios_name = cf["Variables"][label]["bios_name"]
        if len(bios_ncfile.variables[bios_name].shape)==1:
            #print label+" has 1 dimension"
            data = bios_ncfile.variables[bios_name][:][si:ei+1]
        elif len(bios_ncfile.variables[bios_name].shape)==2:
            #print label+" has 2 dimensions"
            data = bios_ncfile.variables[bios_name][:,0][si:ei+1]
        elif len(bios_ncfile.variables[bios_name].shape)==3:
            #print label+" has 3 dimensions"
            data = bios_ncfile.variables[bios_name][:,0,0][si:ei+1]
        attr = {}
        for this_attr in bios_ncfile.variables[bios_name].ncattrs():
            attr[this_attr] = getattr(bios_ncfile.variables[bios_name],this_attr)
        attr["missing_value"] = c.missing_value
        qcutils.CreateSeries(ds_30,label,data,flag,attr)
    # close the netCDF file
    bios_ncfile.close()
    # convert precipitation from kg/m2/s to mm/30 minutes
    precip,flag,attr = qcutils.GetSeriesasMA(ds_30,"Precip")
    precip = float(1800)*precip
    attr["units"] = "mm"
    qcutils.CreateSeries(ds_30,"Precip",precip,flag,attr)
    # convert Ta from K to C
    Ta,flag,attr = qcutils.GetSeriesasMA(ds_30,"Ta")
    Ta = Ta - c.C2K
    attr["units"] = "C"
    qcutils.CreateSeries(ds_30,"Ta",Ta,flag,attr)
    # convert Ts from K to C
    Ts,flag,attr = qcutils.GetSeriesasMA(ds_30,"Ts")
    Ts = Ts - c.C2K
    attr["units"] = "C"
    qcutils.CreateSeries(ds_30,"Ts",Ts,flag,attr)
    # convert ps from hPa to kPa
    ps,flag,attr = qcutils.GetSeriesasMA(ds_30,"ps")
    ps = ps/float(10)
    attr["units"] = "kPa"
    qcutils.CreateSeries(ds_30,"ps",ps,flag,attr)
    # calculate relative humidity
    q,f,a = qcutils.GetSeriesasMA(ds_30,"q")
    Ta,f,a = qcutils.GetSeriesasMA(ds_30,"Ta")
    ps,f,a = qcutils.GetSeriesasMA(ds_30,"ps")
    RH = mf.RHfromspecifichumidity(q, Ta, ps)
    attr = qcutils.MakeAttributeDictionary(long_name='Relative humidity',units='%',standard_name='not defined')
    qcutils.CreateSeries(ds_30,"RH",RH,flag,attr)
    # calculate absolute humidity
    Ta,f,a = qcutils.GetSeriesasMA(ds_30,"Ta")
    RH,f,a = qcutils.GetSeriesasMA(ds_30,"RH")
    Ah = mf.absolutehumidityfromRH(Ta, RH)
    attr = qcutils.MakeAttributeDictionary(long_name='Absolute humidity',units='g/m3',standard_name='not defined')
    qcutils.CreateSeries(ds_30,"Ah",Ah,flag,attr)
    # calculate net radiation
    Fsd,f,a = qcutils.GetSeriesasMA(ds_30,"Fsd")
    Fld,f,a = qcutils.GetSeriesasMA(ds_30,"Fld")
    Fn_sw,f,a = qcutils.GetSeriesasMA(ds_30,"Fn_sw")
    Fn_lw,f,a = qcutils.GetSeriesasMA(ds_30,"Fn_lw")
    Fsu = Fsd - Fn_sw
    Flu = Fld - Fn_lw
    Fn = (Fsd-Fsu)+(Fld-Flu)
    attr = qcutils.MakeAttributeDictionary(long_name='Up-welling long wave',
                         standard_name='surface_upwelling_longwave_flux_in_air',units='W/m2')
    qcutils.CreateSeries(ds_30,"Flu",Flu,flag,attr)
    attr = qcutils.MakeAttributeDictionary(long_name='Up-welling short wave',
                         standard_name='surface_upwelling_shortwave_flux_in_air',units='W/m2')
    qcutils.CreateSeries(ds_30,"Fsu",Fsu,flag,attr)
    attr = qcutils.MakeAttributeDictionary(long_name='Calculated net radiation',
                         standard_name='surface_net_allwave_radiation',units='W/m2')
    qcutils.CreateSeries(ds_30,"Fn",Fn,flag,attr)
    # calculate available energy
    Fn,f,a = qcutils.GetSeriesasMA(ds_30,"Fn")
    Fg,f,a = qcutils.GetSeriesasMA(ds_30,"Fg")
    Fa = Fn - Fg
    attr = qcutils.MakeAttributeDictionary(long_name='Calculated available energy',
                         standard_name='not defined',units='W/m2')
    qcutils.CreateSeries(ds_30,"Fa",Fa,flag,attr)
    # if requested, average from 30 minute time step to 60 minute time step
    if average:
        nRecs_30 = ds_30.globalattributes["nc_nrecs"]
        # get the datetime at hourly intervals
        ldt_60=[ldt_30[i] for i in range(len(ldt_30)) if ldt_30[i].minute==0]
        nRecs_60 = len(ldt_60)
        flag_60 = numpy.zeros(nRecs_60)
        # get a fresh data structure for the 60 minute data
        ds_60 = qcio.DataStructure()
        # put the hourly datetime in the data structure
        ds_60.series["DateTime"] = {}
        ds_60.series["DateTime"]["Data"] = ldt_60
        ds_60.series["DateTime"]["Flag"] = flag_60
        ds_60.series["DateTime"]["Attr"] = ds_30.series["DateTime"]["Attr"]
        # copy across the global attributes
        for gattr in ds_30.globalattributes.keys():
            ds_60.globalattributes[gattr] = ds_30.globalattributes[gattr]
        # set some hourly specific global attributes
        ds_60.globalattributes["nc_nrecs"] = nRecs_60
        ds_60.globalattributes["time_step"] = 60
        # now we do variables that are not averaged
        # first, the time variable
        idx = [i for i in range(len(ldt_30)) if ldt_30[i].minute==0]
        time_30,flag_30,attr = qcutils.GetSeriesasMA(ds_30,"time")
        time_60 = time_30[idx]
        qcutils.CreateSeries(ds_60,"time",time_60,flag_60,attr)
        # and then precipitation
        precip_30,flag_30,attr = qcutils.GetSeriesasMA(ds_30,"Precip")
        precip_30_2d = numpy.reshape(precip_30,(nRecs_60,2))
        precip_60 = numpy.sum(precip_30_2d,axis=1)
        qcutils.CreateSeries(ds_60,"Precip",precip_60,flag_60,attr)
        # get a list of the variables, exclude the QC flags
        series_list = [item for item in ds_30.series.keys() if "_QCFlag" not in item]
        # remove the datetime variables
        for item in ["DateTime","DateTime_UTC","time","Precip","xlDateTime","xlDateTime_UTC"
                     "Year","Month","Day","Hour","Minute","Second"]:
            if item in series_list: series_list.remove(item)
        # loop over variables
        for series in series_list:
            data_30,flag_30,attr = qcutils.GetSeriesasMA(ds_30,series)
            data_30_2d=numpy.reshape(data_30,(nRecs_60,2))
            data_60=numpy.average(data_30_2d,axis=1)
            qcutils.CreateSeries(ds_60,series,data_60,flag_60,attr)
        # get the year, month etc
        qcutils.get_ymdhmsfromdatetime(ds_60)
        # get the Excel datetime values
        xl_date_loc = qcutils.get_xldatefromdatetime(ds_60)
        # write the output file
        ncfile = qcio.nc_open_write(outfilename)
        qcio.nc_write_series(ncfile,ds_60,ndims=1)
    else:
        # write the output file
        ncfile = qcio.nc_open_write(outfilename)
        qcio.nc_write_series(ncfile,ds_30,ndims=1)
    log.info("Finished site: "+site)

print "All done"