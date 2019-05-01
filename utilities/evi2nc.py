import datetime
import matplotlib.pyplot as plt
import netCDF4
import numpy
import os
import pytz
import scipy
import sys
# check the scripts directory is present
if not os.path.exists("../scripts/"):
    print "erai2nc: the scripts directory is missing"
    sys.exit()
# since the scripts directory is there, try importing the modules
sys.path.append('../scripts')
import meteorologicalfunctions as mf
import qcio
import qcutils

do_plots = True

# load the control file contents
cf = qcio.load_controlfile(path="../controlfiles/MODIS/")
# get the DAP file name
evi_url = cf["Files"]["evi_path"]
evi_file = cf["Files"]["evi_file"]
evi_filename = os.path.join(evi_url,evi_file)
# open the EVI file on the AusCover THREDDS server
nc_file = netCDF4.Dataset(evi_filename,"r")
# get the latitude and longitude resolution
lat_resolution = getattr(nc_file,"geospatial_lat_resolution")
lon_resolution = getattr(nc_file,"geospatial_lon_resolution")
# read latitude, longitude and time from the MODIS file
lat = nc_file.variables["latitude"][:]
lon = nc_file.variables["longitude"][:]
modis_time = nc_file.variables["time"][:]
# get a Python datetime series from the netCDF time (UTC)
modis_time_units = getattr(nc_file.variables["time"],"units")
modis_dt =  netCDF4.num2date(modis_time,modis_time_units)
# now we loop over the sites in the control file
#site_list = cf["Sites"].keys()
site_list = ["Calperum"]
for site in site_list:
    # get the site information from the control file
    site_name = cf["Sites"][site]["site_name"]
    print "Processing "+site_name
    out_filepath = cf["Sites"][site]["out_filepath"]
    if not os.path.exists(out_filepath):
        os.makedirs(out_filepath)
    out_filename = cf["Sites"][site]["out_filename"]
    out_name = os.path.join(out_filepath,out_filename)
    site_timezone = cf["Sites"][site]["site_timezone"]
    site_latitude = float(cf["Sites"][site]["site_latitude"])
    site_longitude = float(cf["Sites"][site]["site_longitude"])
    site_timestep = int(cf["Sites"][site]["site_timestep"])
    site_cutout = int(cf["Sites"][site]["site_cutout"])
    evi_quality_threshold = int(cf["Sites"][site]["evi_quality_threshold"])
    evi_sd_threshold = float(cf["Sites"][site]["evi_sd_threshold"])
    evi_interpolate = cf["Sites"][site]["evi_interpolate"]
    evi_smooth_filter = cf["Sites"][site]["evi_smooth_filter"]
    sg_num_points = int(cf["Sites"][site]["sg_num_points"])
    sg_order = int(cf["Sites"][site]["sg_order"])
    # get the upper and lower bounds of the cut out
    delta_width = site_cutout*lat_resolution/2
    delta_height = site_cutout*lon_resolution/2
    lat_bound_lower = site_latitude - delta_width
    lat_bound_upper = site_latitude + delta_width
    lon_bound_lower = site_longitude - delta_height
    lon_bound_upper = site_longitude + delta_height
    # get the EVI and the quality flag for this site
    lat_index = numpy.where((lat>=lat_bound_lower)&(lat<=lat_bound_upper))[0]
    lon_index = numpy.where((lon>=lon_bound_lower)&(lon<=lon_bound_upper))[0]
    # get the EVI
    evi = nc_file.variables["evi"][:,lat_index,lon_index]
    # get the quality flags
    quality = nc_file.variables["quality"][:,lat_index,lon_index]
    # QC the EVI
    evi_qc = numpy.ma.masked_where(quality>evi_quality_threshold,evi)
    # get the mean and standard deviation of the QC'd pixels
    evi_median = numpy.ma.median(evi.reshape(evi_qc.shape[0],-1),axis=1)
    evi_mean = numpy.ma.mean(evi.reshape(evi_qc.shape[0],-1),axis=1)
    evi_sd = numpy.ma.std(evi.reshape(evi_qc.shape[0],-1),axis=1)
    evi_mean = numpy.ma.masked_where(evi_sd>evi_sd_threshold,evi_mean)
    evi_sd = numpy.ma.masked_where(evi_sd>evi_sd_threshold,evi_sd)
    # strip out masked elements, convert to ndarray from masked array and get various
    # time series to do the interpolation
    idx = numpy.where(numpy.ma.getmaskarray(evi_mean)==False)[0]
    evi_raw = numpy.array(evi_mean[idx])
    modis_time_raw = numpy.array(modis_time[idx])
    modis_dt_raw = netCDF4.num2date(modis_time_raw,modis_time_units)
    start_date = modis_dt_raw[0]
    end_date = modis_dt_raw[-1]
    tdts = datetime.timedelta(days=16)
    modis_dt_interp = [result for result in qcutils.perdelta(start_date,end_date,tdts)]
    modis_time_interp = netCDF4.date2num(modis_dt_interp,modis_time_units)
    # fill the missing MODIS data with linear interpolation
    if evi_interpolate.lower()=="linear":
        k = 1
    elif evi_interpolate.lower()=="quadratic":
        k = 2
    elif evi_interpolate.lower()=="cubic":
        k = 3
    else:
        print "Unrecognised interpolation option, using linear ..."
        k = 1
    s = scipy.interpolate.InterpolatedUnivariateSpline(modis_time_raw,evi_raw,k=k)
    evi_interp = s(modis_time)
    # apply the Savitsky-Golay smoothing filter if requested
    if evi_smooth_filter.lower()=="savitsky-golay":
        evi_interp_smooth = scipy.signal.savgol_filter(evi_interp,sg_num_points,sg_order,mode="mirror")
    else:
        print "No smoothing applied to EVI"
        evi_interp_smooth = numpy.array(evi_interp)
    # interpolate the smoothed EVI from the MODIS 16 day time step to the tower time step
    start_date = modis_dt_raw[0]
    end_date = modis_dt_raw[-1]
    tdts = datetime.timedelta(minutes=site_timestep)
    dt_UTC = [result for result in qcutils.perdelta(start_date,end_date,tdts)]
    time_UTC = netCDF4.date2num(dt_UTC,modis_time_units)
    # first we do the gap filled but not smoothed EVI
    s = scipy.interpolate.InterpolatedUnivariateSpline(modis_time,evi_interp,k=1)
    evi_interp2 = s(time_UTC)
    # and then we do the gap filled and smoothed EVI
    s = scipy.interpolate.InterpolatedUnivariateSpline(modis_time,evi_interp_smooth,k=1)
    evi_interp2_smooth = s(time_UTC)
    # if requested, plot the data prior to output
    if do_plots:
        plt.ion()
        fig=plt.figure()
        ax1 = plt.subplot(211)
        for i in range(evi.shape[1]):
            for j in range(evi.shape[2]):
                ax1.plot(modis_dt,evi[:,i,j],'b.')
                ax1.plot(modis_dt,evi_qc[:,i,j],'r+')
        ax1.errorbar(modis_dt,evi_mean,yerr=evi_sd, fmt='ro')
        ax1.plot(modis_dt,evi_interp,'g^')
        ax1.plot(modis_dt,evi_interp,'g--')
        ax1.plot(modis_dt,evi_interp_smooth,'y-')
        #for item in fire_dates: plt.axvline(item)
        ax2 = plt.subplot(212,sharex=ax1)
        ax2.errorbar(modis_dt,evi_mean,yerr=evi_sd, fmt='ro')
        ax2.plot(dt_UTC,evi_interp2_smooth,'b-')
        png_filename = out_name.replace(".nc",".png")
        fig.savefig(png_filename,format="png")
        plt.draw()
        plt.ioff()

    # create a data structure and write the global attributes
    ds = qcio.DataStructure()
    ds.series["DateTime"] = {}
    ds.globalattributes["site_name"] = site_name
    ds.globalattributes["time_zone"] = site_timezone
    ds.globalattributes["longitude"] = site_longitude
    ds.globalattributes["latitude"] = site_latitude
    ds.globalattributes["time_step"] = site_timestep
    ds.globalattributes["xl_datemode"] = str(0)
    ds.globalattributes["nc_level"] = "L1"
    # convert from UTC to local time
    site_tz = pytz.timezone(site_timezone)
    # put the time zone (UTC) into the datetime
    dt_utc = [x.replace(tzinfo=pytz.utc) for x in dt_UTC]
    # convert from UTC to local time
    dt_loc = [x.astimezone(site_tz) for x in dt_utc]
    # remove any daylight saving adjustments (towers run on standard time)
    dt_loc = [x-x.dst() for x in dt_loc]
    # strip the time zone from the local datetime series
    dt_loc = [x.replace(tzinfo=None) for x in dt_loc]
    ds.series["DateTime"]["Data"] = dt_loc
    # update global attributes
    ds.globalattributes["nc_nrecs"] = len(dt_loc)
    ds.globalattributes["start_datetime"] = str(dt_loc[0])
    ds.globalattributes["end_datetime"] = str(dt_loc[-1])
    # get the Excel datetime
    qcutils.get_xldatefromdatetime(ds)
    # get the year, month, day, hour, minute and second
    qcutils.get_ymdhmsfromdatetime(ds)
    # put the QC'd, smoothed and interpolated EVI into the data structure
    flag = numpy.zeros(len(dt_loc),dtype=numpy.int32)
    attr = qcutils.MakeAttributeDictionary(long_name="MODIS EVI, smoothed and interpolated",units="none",
                                           horiz_resolution="250m",
                                           cutout_size=str(site_cutout),
                                           evi_quality_threshold=str(evi_quality_threshold),
                                           evi_sd_threshold=str(evi_sd_threshold),
                                           evi_interpolate=str(evi_interpolate),
                                           evi_smooth_filter=str(evi_smooth_filter),
                                           sg_num_points=str(sg_num_points),
                                           sg_order=str(sg_num_points))
    qcutils.CreateSeries(ds,"EVI",evi_interp2_smooth,flag,attr)

    attr = qcutils.MakeAttributeDictionary(long_name="MODIS EVI, interpolated",units="none",
                                           horiz_resolution="250m",
                                           cutout_size=str(site_cutout),
                                           evi_quality_threshold=str(evi_quality_threshold),
                                           evi_sd_threshold=str(evi_sd_threshold),
                                           evi_interpolate=str(evi_interpolate))
    qcutils.CreateSeries(ds,"EVI_notsmoothed",evi_interp2,flag,attr)
    # now write the data structure to a netCDF file
    out_file = qcio.nc_open_write(out_name)
    qcio.nc_write_series(out_file,ds,ndims=1)
