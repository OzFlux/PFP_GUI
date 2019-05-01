import netCDF4
import scipy
import qcutils

cutout_width = 3
cutout_height = 3

dap_url = "http://www.auscover.org.au/thredds/dodsC/"
dap_folder = "auscover/lpdaac-aggregates/c5/v2-nc4/aust/MOD13Q1.005/"
dap_name = "MOD13Q1.aggregated.aust.005.enhanced_vegetation_index.ncml"
dap_file = dap_url+dap_folder+dap_name

nc_file = netCDF4.Dataset(dap_file,"r")

lat_resolution = getattr(nc_file,"geospatial_lat_resolution")
lon_resolution = getattr(nc_file,"geospatial_lon_resolution")
delta_width = cutout_width*lat_resolution/2
delta_height = cutout_height*lon_resolution/2

# get the site information and the AWS stations to use
xlname = "../../BoM/Locations/AWS_Locations.xls"
wb = xlrd.open_workbook(xlname)
sheet = wb.sheet_by_name("OzFlux")
xl_row = 10
xl_col = 0
bom_sites_info = {}
for n in range(xl_row,sheet.nrows):
    xlrow = sheet.row_values(n)
    bom_sites_info[str(xlrow[0])] = {}
    bom_sites_info[xlrow[0]]["latitude"] = xlrow[1]
    bom_sites_info[xlrow[0]]["longitude"] = xlrow[2]
    bom_sites_info[xlrow[0]]["elevation"] = xlrow[3]
    for i in [4,10,16,22]:
        if xlrow[i]!="":
            bom_sites_info[str(xlrow[0])][str(int(xlrow[i+1]))] = {}
            bom_sites_info[str(xlrow[0])][str(int(xlrow[i+1]))]["site_name"] = xlrow[i]
            bom_sites_info[str(xlrow[0])][str(int(xlrow[i+1]))]["latitude"] = xlrow[i+2]
            bom_sites_info[str(xlrow[0])][str(int(xlrow[i+1]))]["longitude"] = xlrow[i+3]
            bom_sites_info[str(xlrow[0])][str(int(xlrow[i+1]))]["elevation"] = xlrow[i+4]
            bom_sites_info[str(xlrow[0])][str(int(xlrow[i+1]))]["distance"] = xlrow[i+5]

site_list = bom_sites_info.keys()
# loop over sites
for site in site_list:
    # create a data structure
    ds = qcio.DataStructure()
    # get the site latitude and longitude
    site_latitude = bom_sites_info[site]["latitude"]
    site_longitude = bom_sites_info[site]["longitude"]
    # get the upper and lower latitude and longitude bounds
    lat_bound_lower = site_latitude - delta_width
    lat_bound_upper = site_latitude + delta_width
    lon_bound_lower = site_longitude - delta_height
    lon_bound_upper = site_longitude + delta_height
    # read the latitude, longitude and time variables from the MODIS file
    lat = nc_file.variables["latitude"][:]
    lon = nc_file.variables["longitude"][:]
    modis_time = nc_file.variables["time"][:]
    # get a Python datetime series from the netCDF time
    modis_time_units = getattr(nc_file.variables["time"],"units")
    modis_dt =  netCDF4.num2date(modis_time,modis_time_units)
    print modis_dt[0],modis_dt[-1]
    # get the index of points within the latitude and longitude bounds
    lat_index = numpy.where((lat>=lat_bound_lower)&(lat<=lat_bound_upper))[0]
    lon_index = numpy.where((lon>=lon_bound_lower)&(lon<=lon_bound_upper))[0]
    # loop over MODIS products here
    # get the EVI
    evi_attr = qcutils.MakeAttributeDictionary(long_name="Enhanced Vegetation Index from MODIS",
                                               MODIS_product="MOD13Q1",source="TERN-AusCover",
                                               dap_url=dap_url,evi_name=evi_name)
    evi = nc_file.variables["evi"][:,lat_index,lon_index]
    evi_flag = numpy.zeros(len(evi),dtype=numpy.int32)
    # get the quality flags
    quality = nc_file.variables["quality"][:,lat_index,lon_index]
    ok_mask = numpy.ones_like(evi)
    ok_list = [2048,2049,2052,2053,2112,2113,2116,2117,2560,2561,2564,2565,2624,2625,2628,2629]
    for item in ok_list:
        index = numpy.ma.where(quality==item)[0]
        ok_mask[index] = 0
    evi_masked = numpy.ma.masked_where(ok_mask!=0,evi)
    evi_masked_median = numpy.ma.median(evi_masked.reshape(evi_masked.shape[0],-1),axis=1)
    # get data for interpolation
    start = modis_dt[0]
    end = modis_dt[-1]
    modis_dt_interp = [result for result in perdelta(start,end,datetime.timedelta(minutes=ts))]
    modis_time_interp = netCDF4.date2num(modis_dt_interp,modis_time_units)
    modis_time_masked = numpy.ma.masked_where(numpy.ma.getmaskarray(evi_masked_median)==True,modis_time)
    modis_time_comp = numpy.ma.compressed(modis_time_masked)
    evi_masked_median_comp = numpy.ma.compressed(evi_masked_median)
    x_org = modis_time_comp
    y_org = evi_masked_median_comp
    # interpolate onto the tower time step
    interp_type = qcutils.get_keyvaluefromcf(cf,["EVI"],"interp_type",default="linear")
    if interp_type.lower() not in ["linear","smooth_interp"]:
        msg = " Unrecognised interpolation type ("+interp_type+"), using linear ..."
        log.warning(msg)
        interp_type = "linear"
    if interp_type.lower()=="linear":
        # linear interpolation
        log.info(" Using linear interpolation")
        f = scipy.interpolate.interp1d(x_org,y_org,bounds_error=False)
        evi_interp = f(modis_time_interp)
        filter_type = qcutils.get_keyvaluefromcf(cf,["EVI"],"filter_type",default="savgol")
        if filter_type.lower() not in ["savgol"]:
            msg = " Unrecognised filter type ("+filter_type+"), using Savitsky-Golay ..."
            log.warning(msg)
            filter_type = "savgol"
        if filter_type.lower()=="savgol":
            # Savitsky-Golay filter
            log.info(" Using Savitsky-Golay filter")
            savgol_window = qcutils.get_keyvaluefromcf(cf,["EVI"],"savgol_window",default=10001)
            savgol_order = qcutils.get_keyvaluefromcf(cf,["EVI"],"savgol_order",default=4)
            evi_interp_smooth = scipy.signal.savgol_filter(evi_interp,savgol_window,savgol_order)
    elif interp_type.lower()=="smooth_interp":
        # smoothed spline interpolation
        log.info(" Using smoothed spline interpolation")
        smooth_factor = qcutils.get_keyvaluefromcf(cf,["EVI"],"smooth_factor",default=0.03)
        tck = scipy.interpolate.splrep(x_org,y_org,s=smooth_factor)
        evi_interp_smooth = scipy.interpolate.splev(modis_time_interp,tck,der=0)
    # now put data into a data structure
    ds.series["DateTime"] = {}
    ds.series["DateTime"]["Data"] = modis_dt_interp
    ds.series["DateTime"]["Flag"] = numpy.zeros(len(modis_dt_interp),dtype=numpy.int32)
    ds.series["DateTime"]["Attr"] = {}
    ds.series["DateTime"]["Attr"]["long_name"] = "Datetime in local timezone"
    ds.series["DateTime"]["Attr"]["units"] = "None"
    qcutils.get_ymdhmsfromdatetime(ds)
    qcutils.CreateSeries(ds,"evi",evi_interp_smooth,evi_flag,evi_attr)
    nc_file = qcio.nc_open_write(outfilename)
    qcio.nc_write_series(nc_file,ds)
