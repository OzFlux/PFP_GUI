# standard
from collections import OrderedDict
import datetime
import glob
import os
import sys
import time
# 3rd party
from configobj import ConfigObj
import netCDF4
import numpy
import pytz
from scipy.interpolate import InterpolatedUnivariateSpline
import xlrd
# check the scripts directory is present
if not os.path.exists("../scripts/"):
    print "erai2nc: the scripts directory is missing"
    sys.exit()
# since the scripts directory is there, try importing the modules
sys.path.append('../scripts')
# PFP
import meteorologicalfunctions as mf
import pysolar
import qcio
import qclog
import qcutils

t = time.localtime()
rundatetime = datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]).strftime("%Y%m%d%H%M")
log_filename = 'erai2nc_'+rundatetime+'.log'
logger = qclog.init_logger(logger_name="pfp_log", file_handler=log_filename)

def read_site_master(xl_file_path, sheet_name):
    """
    """
    xl_book = xlrd.open_workbook(xl_file_path)
    xl_sheet = xl_book.sheet_by_name(sheet_name)
    last_row = int(xl_sheet.nrows)
    # find the header and first data rows
    for i in range(last_row):
        if xl_sheet.cell(i,0).value == "Site":
            header_row = i
            first_data_row = header_row + 1
            break
    # read the header row
    header_row_values = xl_sheet.row_values(header_row)
    # read the site data from the master Excel spreadsheet
    site_info = OrderedDict()
    for n in range(first_data_row,last_row):
        site_name = xl_sheet.cell(n,0).value
        site_name = site_name.replace(" ","")
        site_info[site_name] = OrderedDict()
        for item in header_row_values[1:]:
            i = header_row_values.index(item)
            site_info[site_name][item] = xl_sheet.cell(n,i).value

    return site_info

# read the control file file
cf = qcio.load_controlfile(path='../controlfiles')
xl_file_path = cf["Files"]["xl_file_path"]
xl_sheet_name = cf["Files"]["xl_sheet_name"]
erai_path = cf["Files"]["erai_path"]
out_base_path = cf["Files"]["out_base_path"]
site_sa_limit = cf["Options"]["site_sa_limit"]
# get the site information from the site master spreadsheet
site_info = read_site_master(xl_file_path, xl_sheet_name)
# get a list of sites
site_list = site_info.keys()
# and a list of the ERAI files to be processed
erai_list = sorted(glob.glob(erai_path))
#erai_list = ["/home/peter/OzFlux/ERAI/ERAI_2014.nc",
             #"/home/peter/OzFlux/ERAI/ERAI_2015.nc",
             #"/home/peter/OzFlux/ERAI/ERAI_2016.nc"]
# construct a dictionary of concatenation control files, this will be
# used to concatenate the yearly ERAI files for each site
cf_dict = OrderedDict()
for site_name in site_list:
    # construct the output file path
    out_file_path = os.path.join(out_base_path,site_name,"Data","ERAI",site_name+"_ERAI.nc")
    # initialise the concatenation control file
    cf_dict[site_name] = ConfigObj(indent_type="    ")
    cf_dict[site_name]["Options"] = {"NumberOfDimensions":1,
                                     "MaxGapInterpolate":0,
                                     "FixTimeStepMethod":"round",
                                     "Truncate":"No",
                                     "TruncateThreshold":50,
                                     "SeriesToCheck":[]}
    cf_dict[site_name]["Files"] = {"Out":{"ncFileName":out_file_path},
                                   "In":{}}

for n, erai_name in enumerate(erai_list):
    logger.info("Processing ERAI file "+erai_name)
    erai_timestep = 180
    erai_file = netCDF4.Dataset(erai_name)
    latitude = erai_file.variables["latitude"][:]
    longitude = erai_file.variables["longitude"][:]
    lat_resolution = abs(latitude[-1]-latitude[0])/(len(latitude)-1)
    lon_resolution = abs(longitude[-1]-longitude[0])/(len(longitude)-1)
    # get the time and convert to Python datetime object
    erai_time = erai_file.variables["time"][:]
    time_units = getattr(erai_file.variables["time"],"units")
    dt_erai = netCDF4.num2date(erai_time,time_units)
    start_date_erai = dt_erai[0]
    end_date_erai = dt_erai[-1]
    hour_utc = numpy.array([dt.hour for dt in dt_erai])
    # get the datetime in the middle of the accumulation period
    erai_offset = datetime.timedelta(minutes=float(erai_timestep)/2)
    dt_erai_cor = [x - erai_offset for x in dt_erai]
    # get a series of time, corrected for the offset
    # NOTE: netCDF4.date2num doesn't handle timezone-aware datetimes
    erai_time_3hr = netCDF4.date2num(dt_erai_cor,time_units)
    # make utc_dt timezone aware so we can generate local times later
    dt_erai_utc_cor = [x.replace(tzinfo=pytz.utc) for x in dt_erai_cor]
    #site_list = ["Calperum"]
    # now loop over the sies
    for site_name in site_list:
        # get the output file name
        out_site_path = os.path.join(out_base_path, site_name, "Data", "ERAI")
        if not os.path.exists(out_site_path):
            os.makedirs(out_site_path)
        out_file_name = site_name+"_ERAI_"+start_date_erai.strftime("%Y%m%d")
        out_file_name = out_file_name+"_"+end_date_erai.strftime("%Y%m%d")+".nc"
        out_file_path = os.path.join(out_site_path, out_file_name)
        # get the metadata from the control file
        logger.info("Processing "+site_name)
        # get the metadata from the site master file information
        site_latitude = site_info[site_name]["Latitude"]
        site_longitude = site_info[site_name]["Longitude"]
        site_timezone = site_info[site_name]["Time zone"]
        site_timestep = int(round(float(site_info[site_name]["Time step"])))
        # index of the site in latitude dimension
        site_lat_index = int(((latitude[0]-site_latitude)/lat_resolution)+0.5)
        erai_latitude = latitude[site_lat_index]
        # index of the site in longitude dimension
        if site_longitude<0: site_longitude = float(360) + site_longitude
        site_lon_index = int(((site_longitude-longitude[0])/lon_resolution)+0.5)
        erai_longitude = longitude[site_lon_index]
        logger.info("Site coordinates: "+str(site_latitude)+" "+str(site_longitude))
        logger.info("ERAI grid: "+str(latitude[site_lat_index])+" "+str(longitude[site_lon_index]))
        # get an instance of the Datastructure
        ds_erai = qcio.DataStructure()
        ds_erai.series["DateTime"] = {}
        ds_erai.globalattributes["site_name"] = site_name
        ds_erai.globalattributes["time_zone"] = site_timezone
        ds_erai.globalattributes["latitude"] = site_latitude
        ds_erai.globalattributes["longitude"] = site_longitude
        ds_erai.globalattributes["time_step"] = site_timestep
        ds_erai.globalattributes["sa_limit"] = site_sa_limit
        ds_erai.globalattributes['xl_datemode'] = str(0)
        ds_erai.globalattributes["nc_level"] = "L1"
        # get the UTC and local datetime series
        site_tz = pytz.timezone(site_timezone)
        # now we get the datetime series at the tower time step
        tdts = datetime.timedelta(minutes=site_timestep)
        # get the start and end datetimes rounded to the nearest time steps
        # that lie between the first and last times
        start_date = qcutils.rounddttots(dt_erai_utc_cor[0],ts=site_timestep)
        if start_date<dt_erai_utc_cor[0]: start_date = start_date+tdts
        end_date = qcutils.rounddttots(dt_erai_utc_cor[-1],ts=site_timestep)
        if end_date>dt_erai_utc_cor[-1]: end_date = end_date-tdts
        msg = "Data: "+start_date.strftime("%Y-%m-%d %H:%M")+" UTC to "
        msg = msg+end_date.strftime("%Y-%m-%d %H:%M")+" UTC"
        logger.info(msg)
        #print site_name,end_date,dt_erai_utc_cor[-1]
        # UTC datetime series at the tower time step
        dt_erai_utc_tts = [x for x in qcutils.perdelta(start_date,end_date,tdts)]
        # UTC netCDF time series at tower time step for interpolation
        tmp = [x.replace(tzinfo=None) for x in dt_erai_utc_tts]
        erai_time_tts = netCDF4.date2num(tmp,time_units)
        # local datetime series at tower time step
        dt_erai_loc_tts = [x.astimezone(site_tz) for x in dt_erai_utc_tts]
        # NOTE: will have to disable daylight saving at some stage, towers stay on Standard Time
        # PRI hopes that the following line will do this ...
        dt_erai_loc_tts = [x-x.dst() for x in dt_erai_loc_tts]
        # make the datetime series timezone naive and put it in data structure
        dt_erai_loc_tts = [x.replace(tzinfo=None) for x in dt_erai_loc_tts]
        ds_erai.series["DateTime"]["Data"] = dt_erai_loc_tts
        ds_erai.series["DateTime"]["Flag"] = numpy.zeros(len(dt_erai_loc_tts))
        ds_erai.globalattributes["nc_nrecs"] = len(dt_erai_loc_tts)
        ds_erai.globalattributes["start_datetime"] = str(dt_erai_loc_tts[0])
        ds_erai.globalattributes["end_datetime"] = str(dt_erai_loc_tts[-1])
        # get the Excel datetime
        qcutils.get_xldatefromdatetime(ds_erai)
        # get the year, month, day, hour, minute and second
        qcutils.get_ymdhmsfromdatetime(ds_erai)
        # get the solar altitude, we will use this later to interpolate the ERA Interim solar
        # data from the ERA-I 3 hour time step to the tower time step.
        # NOTE: alt_solar is in degrees
        alt_solar_3hr = numpy.array([pysolar.GetAltitude(erai_latitude,erai_longitude,dt) for dt in dt_erai_utc_cor])
        # get the solar altitude at the tower time step
        alt_solar_tts = numpy.array([pysolar.GetAltitude(erai_latitude,erai_longitude,dt) for dt in dt_erai_utc_tts])
        idx = numpy.where(alt_solar_tts<=0)[0]
        alt_solar_tts[idx] = float(0)

        # Interpolate the 3 hourly accumulated downwelling shortwave to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Fsd_3d = erai_file.variables["ssrd"][:,:,:]
        Fsd_accum = Fsd_3d[:,site_lat_index,site_lon_index]
        # Downwelling shortwave in ERA-I is a cummulative value that is reset to 0 at 0300 and 1500 UTC.
        # Here we convert the cummulative values to 3 hourly values.
        Fsd_erai_3hr = numpy.ediff1d(Fsd_accum,to_begin=0)
        idx = numpy.where((hour_utc==3)|(hour_utc==15))[0]
        Fsd_erai_3hr[idx] = Fsd_accum[idx]
        Fsd_erai_3hr = Fsd_erai_3hr/(erai_timestep*60)
        # normalise the ERA-I downwelling shortwave by the solar altitude
        # clamp solar altitude to a minimum value to avoid numerical problems
        # when alt_solar is close to 0
        alt_solar_limit = float(site_sa_limit)*numpy.ones(len(alt_solar_3hr))
        sa = numpy.where(alt_solar_3hr<=float(site_sa_limit),alt_solar_limit,alt_solar_3hr)
        coef_3hr = Fsd_erai_3hr/numpy.sin(numpy.deg2rad(sa))
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, coef_3hr, k=1)
        # get the coefficient at the tower time step
        coef_tts = s(erai_time_tts)
        # get the downwelling solar radiation at the tower time step
        Fsd_erai_tts = coef_tts*numpy.sin(numpy.deg2rad(alt_solar_tts))
        flag = numpy.zeros(len(Fsd_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Downwelling short wave radiation",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fsd",Fsd_erai_tts,flag,attr)

        # Interpolate the 3 hourly accumulated net shortwave to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Fn_sw_3d = erai_file.variables["ssr"][:,:,:]
        Fn_sw_accum = Fn_sw_3d[:,site_lat_index,site_lon_index]
        # Net shortwave in ERA-I is a cummulative value that is reset to 0 at 0300 and 1500 UTC.
        # Here we convert the cummulative values to 3 hourly values.
        Fn_sw_erai_3hr = numpy.ediff1d(Fn_sw_accum,to_begin=0)
        # deal with the reset times at 0300 and 1500
        idx = numpy.where((hour_utc==3)|(hour_utc==15))[0]
        Fn_sw_erai_3hr[idx] = Fn_sw_accum[idx]
        # get the average value over the 3 hourly period
        Fn_sw_erai_3hr = Fn_sw_erai_3hr/(erai_timestep*60)
        # normalise the ERA-I et shortwave by the solar altitude
        coef_3hr = Fn_sw_erai_3hr/numpy.sin(numpy.deg2rad(sa))
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, coef_3hr, k=1)
        # get the coefficient at the tower time step
        coef_tts = s(erai_time_tts)
        # get the downwelling solar radiation at the tower time step
        Fn_sw_erai_tts = coef_tts*numpy.sin(numpy.deg2rad(alt_solar_tts))
        flag = numpy.zeros(len(Fn_sw_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Net short wave radiation",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fn_sw",Fn_sw_erai_tts,flag,attr)

        Fsu_erai_tts = Fsd_erai_tts - Fn_sw_erai_tts
        flag = numpy.zeros(len(Fsu_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Upwelling short wave radiation",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fsu",Fsu_erai_tts,flag,attr)

        # Interpolate the 3 hourly accumulated downwelling longwave to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Fld_3d = erai_file.variables["strd"][:,:,:]
        Fld_accum = Fld_3d[:,site_lat_index,site_lon_index]
        # Downwelling longwave in ERA-I is a cummulative value that is reset to 0 at 0300 and 1500 UTC.
        # Here we convert the cummulative values to 3 hourly values.
        Fld_erai_3hr = numpy.ediff1d(Fld_accum,to_begin=0)
        idx = numpy.where((hour_utc==3)|(hour_utc==15))[0]
        Fld_erai_3hr[idx] = Fld_accum[idx]
        Fld_erai_3hr = Fld_erai_3hr/(erai_timestep*60)
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Fld_erai_3hr, k=1)
        # get the downwelling longwave at the tower time step
        Fld_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Fld_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Downwelling long wave radiation",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fld",Fld_erai_tts,flag,attr)

        # Interpolate the 3 hourly accumulated net longwave to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Fn_lw_3d = erai_file.variables["str"][:,:,:]
        Fn_lw_accum = Fn_lw_3d[:,site_lat_index,site_lon_index]
        # Net longwave in ERA-I is a cummulative value that is reset at 0300 and 1500 UTC.
        # Here we convert the cummulative values to 3 hourly values.
        Fn_lw_erai_3hr = numpy.ediff1d(Fn_lw_accum,to_begin=0)
        # deal with the reset times at 0300 and 1500
        idx = numpy.where((hour_utc==3)|(hour_utc==15))[0]
        Fn_lw_erai_3hr[idx] = Fn_lw_accum[idx]
        # get the average value over the 3 hourly period
        Fn_lw_erai_3hr = Fn_lw_erai_3hr/(erai_timestep*60)
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Fn_lw_erai_3hr, k=1)
        # get the net longwave at the tower time step
        Fn_lw_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Fn_lw_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Net long wave radiation",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fn_lw",Fn_lw_erai_tts,flag,attr)

        Flu_erai_tts = Fld_erai_tts - Fn_lw_erai_tts
        flag = numpy.zeros(len(Flu_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Upwelling long wave radiation",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Flu",Flu_erai_tts,flag,attr)

        Fn_erai_tts = (Fsd_erai_tts - Fsu_erai_tts) + (Fld_erai_tts - Flu_erai_tts)
        flag = numpy.zeros(len(Fn_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Net all wave radiation",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fn",Fn_erai_tts,flag,attr)

        # Interpolate the 3 hourly accumulated sensible heat flux to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Fh_3d = erai_file.variables["sshf"][:,:,:]
        Fh_accum = float(-1)*Fh_3d[:,site_lat_index,site_lon_index]
        # Sensible heat flux in ERA-I is a cummulative value that is reset at 0300 and 1500 UTC.
        # Here we convert the cummulative values to 3 hourly values.
        Fh_erai_3hr = numpy.ediff1d(Fh_accum,to_begin=0)
        # deal with the reset times at 0300 and 1500
        idx = numpy.where((hour_utc==3)|(hour_utc==15))[0]
        Fh_erai_3hr[idx] = Fh_accum[idx]
        # get the average value over the 3 hourly period
        Fh_erai_3hr = Fh_erai_3hr/(erai_timestep*60)
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Fh_erai_3hr, k=1)
        # get the net longwave at the tower time step
        Fh_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Fh_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Sensible heat flux",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fh",Fh_erai_tts,flag,attr)

        # Interpolate the 3 hourly accumulated latent heat flux to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Fe_3d = erai_file.variables["slhf"][:,:,:]
        Fe_accum = float(-1)*Fe_3d[:,site_lat_index,site_lon_index]
        # Latent heat flux in ERA-I is a cummulative value that is reset at 0300 and 1500 UTC.
        # Here we convert the cummulative values to 3 hourly values.
        Fe_erai_3hr = numpy.ediff1d(Fe_accum,to_begin=0)
        # deal with the reset times at 0300 and 1500
        idx = numpy.where((hour_utc==3)|(hour_utc==15))[0]
        Fe_erai_3hr[idx] = Fe_accum[idx]
        # get the average value over the 3 hourly period
        Fe_erai_3hr = Fe_erai_3hr/(erai_timestep*60)
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Fe_erai_3hr, k=1)
        # get the net longwave at the tower time step
        Fe_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Fe_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Latent heat flux",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fe",Fe_erai_tts,flag,attr)

        # get Fg as residual
        Fg_erai_tts = Fn_erai_tts - Fh_erai_tts - Fe_erai_tts
        flag = numpy.zeros(len(Fg_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Ground heat flux",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fg",Fg_erai_tts,flag,attr)
        # and then Fa
        Fa_erai_tts = Fn_erai_tts - Fg_erai_tts
        flag = numpy.zeros(len(Fa_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Available energy",units="W/m2")
        qcutils.CreateSeries(ds_erai,"Fa",Fa_erai_tts,flag,attr)

        # Interpolate the 3 hourly air pressure to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        ps_3d = erai_file.variables["sp"][:,:,:]
        ps_erai_3hr = ps_3d[:,site_lat_index,site_lon_index]/float(1000)
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, ps_erai_3hr, k=1)
        # get the air pressure at the tower time step
        ps_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(ps_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Surface pressure",units="kPa")
        qcutils.CreateSeries(ds_erai,"ps",ps_erai_tts,flag,attr)

        # Interpolate the 3 hourly air temperature to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Ta_3d = erai_file.variables["t2m"][:,:,:]
        Ta_erai_3hr = Ta_3d[:,site_lat_index,site_lon_index] - 273.15
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Ta_erai_3hr, k=1)
        # get the air temperature at the tower time step
        Ta_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Ta_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Air temperature",units="C")
        qcutils.CreateSeries(ds_erai,"Ta",Ta_erai_tts,flag,attr)

        # Interpolate the 3 hourly dew point temperature to the tower time step
        # and convert to Ah, RH and q
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Td_3d = erai_file.variables["d2m"][:,:,:]
        Td_erai_3hr = Td_3d[:,site_lat_index,site_lon_index] - 273.15
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Td_erai_3hr, k=1)
        # get the dew point temperature at the towespeedr time step
        Td_erai_tts = s(erai_time_tts)
        # get the relative humidity
        es_erai_tts = mf.es(Ta_erai_tts)
        e_erai_tts = mf.es(Td_erai_tts)
        VPD_erai_tts = es_erai_tts - e_erai_tts
        flag = numpy.zeros(len(VPD_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Vapour pressure deficit",units="kPa")
        qcutils.CreateSeries(ds_erai,"VPD",VPD_erai_tts,flag,attr)
        RH_erai_tts = float(100)*e_erai_tts/es_erai_tts
        flag = numpy.zeros(len(RH_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Relative humidity",units="percent")
        qcutils.CreateSeries(ds_erai,"RH",RH_erai_tts,flag,attr)
        # get the absolute humidity
        Ah_erai_tts = mf.absolutehumidityfromRH(Ta_erai_tts,RH_erai_tts)
        flag = numpy.zeros(len(Ah_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Absolute humidity",units="g/m3")
        qcutils.CreateSeries(ds_erai,"Ah",Ah_erai_tts,flag,attr)
        # get the specific humidity
        q_erai_tts = mf.specifichumidityfromRH(RH_erai_tts,Ta_erai_tts,ps_erai_tts)
        flag = numpy.zeros(len(q_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Specific humidity",units="kg/kg")
        qcutils.CreateSeries(ds_erai,"q",q_erai_tts,flag,attr)

        # Interpolate the 3 hourly boundary layer height to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Habl_3d = erai_file.variables["blh"][:,:,:]
        Habl_erai_3hr = Habl_3d[:,site_lat_index,site_lon_index]
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Habl_erai_3hr, k=1)
        # get the boundary layer height at the tower time step
        Habl_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Habl_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Boundary layer height",units="m")
        qcutils.CreateSeries(ds_erai,"Habl",Habl_erai_tts,flag,attr)

        # Spread the 3 hourly accumulated precipitation to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Precip_3d = erai_file.variables["tp"][:,:,:]
        Precip_accum = Precip_3d[:,site_lat_index,site_lon_index]
        Precip_erai_3hr = numpy.ediff1d(Precip_accum,to_begin=0)
        idx = numpy.where((hour_utc==3)|(hour_utc==15))[0]
        Precip_erai_3hr[idx] = Precip_accum[idx]
        Precip_erai_3hr = Precip_erai_3hr*float(1000)
        Precip_erai_tts = numpy.zeros(len(dt_erai_loc_tts))
        idx = qcutils.FindIndicesOfBInA(dt_erai_utc_cor,dt_erai_utc_tts)
        Precip_erai_tts[idx] = Precip_erai_3hr
        flag = numpy.zeros(len(Precip_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Precipitation",units="mm")
        qcutils.CreateSeries(ds_erai,"Precip",Precip_erai_tts,flag,attr)

        # Interpolate the 3 hourly soil moisture to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Sws_3d = erai_file.variables["swvl1"][:,:,:]
        Sws_erai_3hr = Sws_3d[:,site_lat_index,site_lon_index]
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Sws_erai_3hr, k=1)
        # get the soil moisture at the tower time step
        Sws_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Sws_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Soil moisture",units="frac")
        qcutils.CreateSeries(ds_erai,"Sws",Sws_erai_tts,flag,attr)

        # Interpolate the 3 hourly soil temperature to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        Ts_3d = erai_file.variables["stl1"][:,:,:]
        Ts_erai_3hr = Ts_3d[:,site_lat_index,site_lon_index] - 273.15
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, Ts_erai_3hr, k=1)
        # get the soil moisture at the tower time step
        Ts_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(Ts_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Soil temperature",units="C")
        qcutils.CreateSeries(ds_erai,"Ts",Ts_erai_tts,flag,attr)

        # Interpolate the 3 hourly U and V components to the tower time step
        # NOTE: ERA-I variables are dimensioned [time,latitude,longitude]
        # U first ...
        U_3d = erai_file.variables["u10"][:,:,:]
        U_erai_3hr = U_3d[:,site_lat_index,site_lon_index]
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, U_erai_3hr, k=1)
        # get the soil moisture at the tower time step
        U_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(U_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="U component of wind speed",units="m/s")
        qcutils.CreateSeries(ds_erai,"U",U_erai_tts,flag,attr)
        # ... then V
        V_3d = erai_file.variables["v10"][:,:,:]
        V_erai_3hr = V_3d[:,site_lat_index,site_lon_index]
        # get the spline interpolation function
        s = InterpolatedUnivariateSpline(erai_time_3hr, V_erai_3hr, k=1)
        # get the soil moisture at the tower time step
        V_erai_tts = s(erai_time_tts)
        flag = numpy.zeros(len(V_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="V component of wind speed",units="m/s")
        qcutils.CreateSeries(ds_erai,"V",V_erai_tts,flag,attr)
        # now get the wind speed and direction
        Ws_erai_tts = numpy.sqrt(U_erai_tts*U_erai_tts + V_erai_tts*V_erai_tts)
        flag = numpy.zeros(len(Ws_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Wind speed",units="m/s")
        qcutils.CreateSeries(ds_erai,"Ws",Ws_erai_tts,flag,attr)
        Wd_erai_tts = float(270) - numpy.arctan2(V_erai_tts,U_erai_tts)*float(180)/numpy.pi
        idx = numpy.where(Wd_erai_tts>360)[0]
        if len(idx)>0: Wd_erai_tts[idx] = Wd_erai_tts[idx] - float(360)
        flag = numpy.zeros(len(Wd_erai_tts),dtype=numpy.int32)
        attr = qcutils.MakeAttributeDictionary(long_name="Wind direction",units="deg")
        qcutils.CreateSeries(ds_erai,"Wd",Wd_erai_tts,flag,attr)
        # write the yearly file for this site
        ncfile = qcio.nc_open_write(out_file_path)
        qcio.nc_write_series(ncfile,ds_erai,ndims=1)
        # add this yearly file to the control file dictionary for this site
        cf_dict[site_name]["Files"]["In"][str(n)] = out_file_path
        # tell the user we have finished this site
        logger.info("Finished "+site_name)
        logger.info("")
# now we need to loop over the contents of the concatenate control file dictionary
for site_name in site_list:
    cf_concat = cf_dict[site_name]
    #cf_concat.filename = os.path.join("../controlfiles/OzFlux/ERAI/",site_name+"_concatenate.txt")
    #cf_concat.write()
    msg = "Concatenating yearly files for "+site_name
    logger.info(msg)
    qcio.nc_concatenate(cf_concat)
