#%run basics
# Python modules
import calendar
from collections import OrderedDict
import copy
import csv
import datetime
import gzip
import logging
import os
import pytz
import sys
import time
# 3rd party modules
from configobj import ConfigObj
import matplotlib.pyplot as plt
import numpy
import scipy
import scipy.stats
from scipy.interpolate import InterpolatedUnivariateSpline
import xlrd
import xlwt
# pfp modules
if not os.path.exists("../scripts/"):
    print "PyFluxPro: the scripts directory is missing"
    sys.exit()
# since the scripts directory is there, try importing the modules
sys.path.append('../scripts')
import constants as c
import meteorologicalfunctions as mf
import qcio
import qclog
import qcutils

t = time.localtime()
rundatetime = datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]).strftime("%Y%m%d%H%M")
log_filename = 'isd2nc_'+rundatetime+'.log'
logger = qclog.init_logger(logger_name="pfp_log", file_handler=log_filename)

def read_isd_file(isd_file_path):
    """
    Purpose:
     Reads an ISD CSV file (gz or uncompressed) and returns the data in a data structure.
    Assumptions:
    Usage:
    Author: PRI
    Date: June 2017
    """
    isd_file_name = os.path.split(isd_file_path)[1]
    msg = "Reading ISD file "+isd_file_name
    logger.info(msg)
    isd_site_id = isd_file_name.split("-")
    isd_site_id = isd_site_id[0]+"-"+isd_site_id[1]
    # read the file
    if os.path.splitext(isd_file_path)[1] == ".gz":
        with gzip.open(isd_file_path, 'rb') as fp:
            content = fp.readlines()
    else:
        with open(isd_file_path) as fp:
            content = fp.readlines()
    # get a data structure
    ds = qcio.DataStructure()
    # get the site latitude, longitude and altitude
    ds.globalattributes["altitude"] = float(content[0][46:51])
    ds.globalattributes["latitude"] = float(content[0][28:34])/float(1000)
    ds.globalattributes["longitude"] = float(content[0][34:41])/float(1000)
    ds.globalattributes["isd_site_id"] = isd_site_id
    # initialise the data structure
    ds.series["DateTime"] = {"Data":[],"Flag":[],"Attr":{"long_name":"Datetime","units":"none"}}
    ds.series["Wd"] = {"Data":[],"Flag":[],"Attr":{"long_name":"Wind direction","units":"degrees"}}
    ds.series["Ws"] = {"Data":[],"Flag":[],"Attr":{"long_name":"Wind speed","units":"m/s"}}
    ds.series["Ta"] = {"Data":[],"Flag":[],"Attr":{"long_name":"Air temperature","units":"C"}}
    ds.series["Td"] = {"Data":[],"Flag":[],"Attr":{"long_name":"Dew point temperature","units":"C"}}
    ds.series["ps"] = {"Data":[],"Flag":[],"Attr":{"long_name":"Surface pressure","units":"kPa"}}
    ds.series["Precip"] = {"Data":[],"Flag":[],"Attr":{"long_name":"Precipitation","units":"mm"}}
    # define the codes for good data in the ISD file
    OK_obs_code = ["AUTO ","CRN05","CRN15","FM-12","FM-15","FM-16","SY-MT"]
    # iterate over the lines in the file and decode the data
    for i in range(len(content)-1):
    #for i in range(10):
        # filter out anything other than hourly data
        if content[i][41:46] not in OK_obs_code: continue
        YY = int(content[i][15:19])
        MM = int(content[i][19:21])
        DD = int(content[i][21:23])
        HH = int(content[i][23:25])
        mm = int(content[i][25:27])
        dt = datetime.datetime(YY,MM,DD,HH,mm,0)
        ds.series["DateTime"]["Data"].append(pytz.utc.localize(dt))
        # wind direction, degT
        try:
            ds.series["Wd"]["Data"].append(float(content[i][60:63]))
        except:
            ds.series["Wd"]["Data"].append(float(999))
        # wind speed, m/s
        try:
            ds.series["Ws"]["Data"].append(float(content[i][65:69])/float(10))
        except:
            ds.series["Ws"]["Data"].append(float(999.9))
        # air temperature, C
        try:
            ds.series["Ta"]["Data"].append(float(content[i][87:92])/float(10))
        except:
            ds.series["Ta"]["Data"].append(float(999.9))
        # dew point temperature, C
        try:
            ds.series["Td"]["Data"].append(float(content[i][93:98])/float(10))
        except:
            ds.series["Td"]["Data"].append(float(999.9))
        # sea level pressure, hPa
        try:
            ds.series["ps"]["Data"].append(float(content[i][99:104])/float(10))
        except:
            ds.series["ps"]["Data"].append(float(9999.9))
        # precipitation, mm
        if content[i][108:111] == "AA1":
            try:
                ds.series["Precip"]["Data"].append(float(content[i][113:117])/float(10))
            except:
                ds.series["Precip"]["Data"].append(float(999.9))
        else:
            ds.series["Precip"]["Data"].append(float(999.9))
    # add the time zone to the DateTime ataributes
    ds.series["DateTime"]["Attr"]["time_zone"] = "UTC"
    # convert from lists to masked arrays
    f0 = numpy.zeros(len(ds.series["DateTime"]["Data"]))
    f1 = numpy.ones(len(ds.series["DateTime"]["Data"]))
    ds.series["DateTime"]["Data"] = numpy.array(ds.series["DateTime"]["Data"])
    ds.series["DateTime"]["Flag"] = f0
    ds.globalattributes["nc_nrecs"] = len(f0)

    dt_delta = qcutils.get_timestep(ds)
    ts = scipy.stats.mode(dt_delta)[0]/60
    ds.globalattributes["time_step"] = ts[0]

    ds.series["Wd"]["Data"] = numpy.ma.masked_equal(ds.series["Wd"]["Data"],999)
    ds.series["Wd"]["Flag"] = numpy.where(numpy.ma.getmaskarray(ds.series["Wd"]["Data"])==True,f1,f0)
    ds.series["Ws"]["Data"] = numpy.ma.masked_equal(ds.series["Ws"]["Data"],999.9)
    ds.series["Ws"]["Flag"] = numpy.where(numpy.ma.getmaskarray(ds.series["Ws"]["Data"])==True,f1,f0)
    ds.series["Ta"]["Data"] = numpy.ma.masked_equal(ds.series["Ta"]["Data"],999.9)
    ds.series["Ta"]["Flag"] = numpy.where(numpy.ma.getmaskarray(ds.series["Ta"]["Data"])==True,f1,f0)
    ds.series["Td"]["Data"] = numpy.ma.masked_equal(ds.series["Td"]["Data"],999.9)
    ds.series["Td"]["Flag"] = numpy.where(numpy.ma.getmaskarray(ds.series["Td"]["Data"])==True,f1,f0)
    # hPa to kPa
    ds.series["ps"]["Data"] = numpy.ma.masked_equal(ds.series["ps"]["Data"],9999.9)/float(10)
    ds.series["ps"]["Flag"] = numpy.where(numpy.ma.getmaskarray(ds.series["ps"]["Data"])==True,f1,f0)
    # convert sea level pressure to station pressure
    site_altitude = float(ds.globalattributes["altitude"])
    cfac = numpy.ma.exp((-1*site_altitude)/((ds.series["Ta"]["Data"]+273.15)*29.263))
    ds.series["ps"]["Data"] = ds.series["ps"]["Data"]*cfac
    # do precipitation and apply crude limits
    ds.series["Precip"]["Data"] = numpy.ma.masked_equal(ds.series["Precip"]["Data"],999.9)
    condition = (ds.series["Precip"]["Data"]<0)|(ds.series["Precip"]["Data"]>100)
    ds.series["Precip"]["Data"] = numpy.ma.masked_where(condition,ds.series["Precip"]["Data"])
    ds.series["Precip"]["Flag"] = numpy.where(numpy.ma.getmaskarray(ds.series["Precip"]["Data"])==True,f1,f0)
    # get the humidities from Td
    Ta, flag, attr = qcutils.GetSeriesasMA(ds, "Ta")
    Td, flag, attr = qcutils.GetSeriesasMA(ds, "Td")
    ps, flag, attr = qcutils.GetSeriesasMA(ds, "ps")
    RH = mf.RHfromdewpoint(Td, Ta)
    flag = numpy.where(numpy.ma.getmaskarray(RH)==True, f1, f0)
    attr = {"long_name":"Relative humidity", "units":"%"}
    qcutils.CreateSeries(ds, "RH", RH, Flag=flag, Attr=attr)
    Ah = mf.absolutehumidityfromRH(Ta, RH)
    flag = numpy.where(numpy.ma.getmaskarray(Ah)==True, f1, f0)
    attr = {"long_name":"Absolute humidity", "units":"g/m3"}
    qcutils.CreateSeries(ds, "Ah", Ah, Flag=flag, Attr=attr)
    q = mf.specifichumidityfromRH(RH, Ta, ps)
    flag = numpy.where(numpy.ma.getmaskarray(q)==True, f1, f0)
    attr = {"long_name":"Specific humidity", "units":"kg/kg"}
    qcutils.CreateSeries(ds, "q", q, Flag=flag, Attr=attr)
    # return the data
    return ds

def interpolate_ds(ds_in, ts, k=3):
    """
    Purpose:
     Interpolate the contents of a data structure onto a different time step.
    Assumptions:
    Usage:
    Author: PRI
    Date: June 2017
    """
    # instance the output data structure
    ds_out = qcio.DataStructure()
    # copy the global attributes
    for key in ds_in.globalattributes.keys():
        ds_out.globalattributes[key] = ds_in.globalattributes[key]
    # add the time step
    ds_out.globalattributes["time_step"] = str(ts)
    # generate a regular time series at the required time step
    dt = ds_in.series["DateTime"]["Data"]
    dt0 = dt[0] - datetime.timedelta(minutes=30)
    start = datetime.datetime(dt0.year, dt0.month, dt0.day, dt0.hour, 0, 0)
    dt1 = dt[-1] + datetime.timedelta(minutes=30)
    end = datetime.datetime(dt1.year, dt1.month, dt1.day, dt1.hour, 0, 0)
    idt = [result for result in perdelta(start, end, datetime.timedelta(minutes=ts))]
    x1 = numpy.array([toTimestamp(dt[i]) for i in range(len(dt))])
    x2 = numpy.array([toTimestamp(idt[i]) for i in range(len(idt))])
    # loop over the series in the data structure and interpolate
    ds_out.series["DateTime"] = {}
    ds_out.series["DateTime"]["Data"] = idt
    ds_out.series["DateTime"]["Flag"] = numpy.zeros(len(idt))
    ds_out.series["DateTime"]["Attr"] = {"long_name":"Datetime","units":"none"}
    ds_out.globalattributes["nc_nrecs"] = len(idt)
    series_list = list(ds_in.series.keys())
    if "DateTime" in series_list:
        series_list.remove("DateTime")
    for label in series_list:
        #print label
        data_in, flag_in, attr_in = qcutils.GetSeriesasMA(ds_in, label)
        # check if we are dealing with precipitation
        if "Precip" in label:
            # precipitation shouldn't be interpolated, just assign any precipitation
            # to the ISD time stamp.
            data_out = numpy.ma.zeros(len(idt), dtype=numpy.float64)
            idx = numpy.searchsorted(x2, numpy.intersect1d(x2, x1))
            data_out[idx] = data_in
        else:
            # interpolate everything else
            data_out = interpolate_1d(x1, data_in, x2)
        flag_out = numpy.zeros(len(idt))
        attr_out = attr_in
        qcutils.CreateSeries(ds_out, label, data_out, Flag=flag_out, Attr=attr_out)

    return ds_out

def interpolate_1d(x1, y1, x2):
    """
    Purpose:
     Interpolate data from one time step to another.
    Assumptions:
    Usage:
    Author: PRI
    Date: June 2017
    """
    # off we go
    if numpy.ma.is_masked(y1):
        # check we have at least 2 non-masked points
        if numpy.ma.count(y1) >= 2:
            # input Y array is a masked array
            idx = numpy.where(numpy.ma.getmaskarray(y1) == False)[0]
            int_fn = scipy.interpolate.Akima1DInterpolator(x1[idx], y1[idx].data)
            y2 = int_fn(x2)
        else:
            msg = "Not enough points (<2) to interpolate"
            logger.warning(msg)
            y2 = numpy.ma.ones(len(x2))*float(c.missing_value)
    else:
        int_fn = scipy.interpolate.Akima1DInterpolator(x1, y1)
        y2 = int_fn(x2)
    return y2

def interpolate_1d_old(x1,y1,x2,k=3,ext=0):
    """
    Purpose:
     Interpolate data from one time step to another.
    Assumptions:
    Usage:
    Author: PRI
    Date: June 2017
    """
    # off we go
    if numpy.ma.is_masked(y1):
        # check we have at least 2 non-masked points
        if numpy.ma.count(y1) >= 2:
            # input Y array is a masked array
            cidx = numpy.zeros(len(y1),dtype=numpy.float64)
            idx = numpy.where(numpy.ma.getmaskarray(y1)==True)[0]
            cidx[idx] = numpy.float64(1)
            idx = numpy.where(numpy.ma.getmaskarray(y1)==False)[0]
            spl = InterpolatedUnivariateSpline(x1[idx], y1[idx], k=k, ext=ext)
            y2 = spl(x2)    
            spl = InterpolatedUnivariateSpline(x1, cidx, k=k, ext=ext)
            cidxi = spl(x2)
            y2 = numpy.ma.masked_where(cidxi!=0,y2)
        else:
            msg = "Not enough points (<2) to interpolate"
            logger.warning(msg)
            #raise RuntimeError(msg)
            y2 = numpy.ma.ones(len(x2))*float(c.missing_value)
    else:
        spl = InterpolatedUnivariateSpline(x1, y1, k=k, ext=ext)
        y2 = spl(x2)
    return y2

def perdelta(start, end, delta):
    curr = start
    while curr <= end:
        yield curr
        curr += delta

def toTimestamp(d):
    return calendar.timegm(d.timetuple())

def convert_time_zone(ds, from_time_zone, to_time_zone):
    """
    Purpose:
     Convert the datetime series in a data structure from one timezone to another.
    Usage:
    Author: PRI
    Date: June 2017
    """
    local_time_zone = pytz.timezone(to_time_zone)
    from_dt_naive = ds.series["DateTime"]["Data"]
    to_dt_aware = [dt.replace(tzinfo=from_time_zone).astimezone(local_time_zone) for dt in from_dt_naive]
    to_dt_naive = [dt.replace(tzinfo=None) for dt in to_dt_aware]
    ds.series["DateTime"]["Data"] = to_dt_naive
    ds.series["DateTime"]["Attr"]["time_zone"] = local_time_zone
    return

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

def xl_write_ISD_timesteps(xl_file_path, data):
    """
    Purpose:
     Writes a dictionary to a worksheet in an Excel workbook.
     This routine has 2 arguments,an Excel worksheet instance and
     a dictionary of data to be written out.  The dictionary
     format needs to be:
      data[site][year]["mean"]
      data[site][year]["stdev"]
      data[site][year]["mode"]
    Usage:
     qcio.xl_write_ISD_timesteps(xl_file_path, data)
      where xl_file_path is an Excel workbook file name
            data         is a dictionary as defined above
    Side effects:
     Writes to an Excel worksheet instance.
    Called by:
    Calls:
    Author: PRI
    Date: August 2017
    """
    # get a workbook
    xl_book = xlwt.Workbook()
    # get a list of the sheets to add
    site_list = data.keys()
    year_list = data[site_list[0]].keys()
    stat_list = data[site_list[0]][year_list[0]].keys()
    # loop over the statistics
    for stat in stat_list:
        # add a worksheet for the statistics
        xl_sheet = xl_book.add_sheet(stat)
        # write the header line
        for col, year in enumerate(year_list):
            xl_sheet.write(0,col+1,year)
        # write the data, one row per site, one column per year
        for row, site in enumerate(site_list):
            xl_sheet.write(row+1,0,site)
            for col, year in enumerate(year_list):
                if stat in data[site][year].keys():
                    xl_sheet.write(row+1,col+1,data[site][year][stat])
                else:
                    xl_sheet.write(row+1,col+1,"")
    # save the workbook
    xl_book.save(xl_file_path)
    
    return

# read the control file file
cf = qcio.load_controlfile(path='../controlfiles')
xl_file_path = cf["Files"]["xl_file_path"]
xl_sheet_name = cf["Files"]["xl_sheet_name"]
isd_base_path = cf["Files"]["isd_base_path"]
out_base_path = cf["Files"]["out_base_path"]
# read the site master spreadsheet
site_info = read_site_master(xl_file_path, xl_sheet_name)
# get a list of sites
site_list = site_info.keys()
# creat a dictionary to hold the ISD site time steps
isd_time_steps = OrderedDict()

for site in site_list:
    # construct the output file path
    fluxnet_id = site_info[site]["FluxNet ID"]
    if len(fluxnet_id) == 0:
        nc_out_path = os.path.join(out_base_path,site,"Data","ISD",site+"_ISD.nc")
    else:
        nc_out_path = os.path.join(out_base_path,fluxnet_id,"Data","ISD",fluxnet_id+"_ISD.nc")
    # construct the config dictionary for the concatenate routine
    cf_concat = ConfigObj(indent_type="    ")    
    cf_concat["Options"] = {"NumberOfDimensions":1,
                            "MaxGapInterpolate":0,
                            "FixTimeStepMethod":"round",
                            "Truncate":"No",
                            "TruncateThreshold":50,
                            "SeriesToCheck":[]}
    cf_concat["Files"] = {"Out":{"ncFileName":nc_out_path},
                          "In":{}}
    # get the list of ISD stations to be used for this site
    #isd_site_list = cf["Sites"][site]["isd_sites"]
    isd_site_list = []
    for item in ["ISD_ID_1","ISD_ID_2","ISD_ID_3","ISD_ID_4"]:
        if len(site_info[site][item]) != 0:
            isd_site_list.append(site_info[site][item])

    # now get a dictionary that ties the ISD station ID to a number
    # that will be appended to the variable name
    site_index = {}
    for n, isd_site in enumerate(isd_site_list):
        site_index[isd_site] = n
    if not isinstance(isd_site_list, list):
        isd_site_list = [isd_site_list]
    time_zone = site_info[site]["Time zone"]
    time_step = int(round(float(site_info[site]["Time step"])))
    start_year = int(site_info[site]["Start year"])
    end_year = int(site_info[site]["End year"])
    # get the list of years to process
    year_list = range(start_year,end_year+1)
    for n, year in enumerate(year_list):
        # we will collect the data for each site for this year into a single dictionary
        ds_out = {}
        isd_year_path = os.path.join(isd_base_path,str(year))
        for isd_site in isd_site_list:
            if isd_site not in isd_time_steps.keys():
                isd_time_steps[isd_site] = OrderedDict()
            if year not in isd_time_steps[isd_site].keys():
                isd_time_steps[isd_site][year] = OrderedDict()
            isd_file_path = os.path.join(isd_year_path,str(isd_site)+"-"+str(year)+".gz")
            if not os.path.isfile(isd_file_path):
                continue
            try:
                ds_in = read_isd_file(isd_file_path)
            except:
                msg = " Unable to read file, skipping ..."
                logger.warning(msg)
                continue
            # get an array of time steps in seconds
            dt = qcutils.get_timestep(ds_in)
            # and get dt in minutes
            dt = dt/float(60)
            isd_time_steps[isd_site][year]["mean"] = numpy.mean(dt)
            isd_time_steps[isd_site][year]["stdev"] = numpy.std(dt)
            isd_time_steps[isd_site][year]["mode"] = scipy.stats.mode(dt)[0][0]
            # interpolate from the ISD site time step to the tower time step
            ds_out[site_index[isd_site]] = interpolate_ds(ds_in, time_step, k=1)
            # adjust time from UTC to local using the time zone
            convert_time_zone(ds_out[site_index[isd_site]], pytz.utc, time_zone)
            # add some useful global attributes
            ds_out[site_index[isd_site]].globalattributes["isd_site_id"] = isd_site
            ds_out[site_index[isd_site]].globalattributes["time_zone"] = time_zone
            # write out a netCDF file for each ISD site and each year
            #nc_file_name = isd_site+"_"+str(year)+".nc"
            #nc_dir_path = os.path.join(out_base_path,site,"Data","ISD")
            #if not os.path.exists(nc_dir_path):
                #os.makedirs(nc_dir_path)
            #nc_file_path = os.path.join(nc_dir_path,nc_file_name)
            #nc_file = qcio.nc_open_write(nc_file_path)
            #qcio.nc_write_series(nc_file, ds_out[site_index[isd_site]], ndims=1)
        # now we merge the data structures for each ISD station into a single data structure
        # first, instance a data structure
        ds_all = qcio.DataStructure()
        ds_all.globalattributes["latitude"] = site_info[site]["Latitude"]
        ds_all.globalattributes["longitude"] = site_info[site]["Longitude"]
        ds_all.globalattributes["altitude"] = site_info[site]["Altitude"]
        # now loop over the data structures for each ISD station and get the earliest
        # start time and the latest end time
        start_datetime = []
        end_datetime = []
        for i in list(ds_out.keys()):
            start_datetime.append(ds_out[i].series["DateTime"]["Data"][0])
            end_datetime.append(ds_out[i].series["DateTime"]["Data"][-1])
        print site, year
        start = min(start_datetime)
        end = max(end_datetime)
        # now make a datetime series at the required time step from the earliest start
        # datetime to the latest end datetime
        ldt_all = [result for result in perdelta(start, end, datetime.timedelta(minutes=time_step))]
        nrecs = len(ldt_all)
        ds_all.globalattributes["nc_nrecs"] = nrecs
        # and add the datetime to the all-stations data structure
        ds_all.series["DateTime"] = {}
        ds_all.series["DateTime"]["Data"] = ldt_all
        ds_all.series["DateTime"]["Flag"] = numpy.zeros(len(ldt_all))
        ds_all.series["DateTime"]["Attr"] = {"long_name":"DateTime","units":"none"}
        # now copy the contents of the ISD station data structures to the all-stations
        # data structure
        for i in list(ds_out.keys()):
            isd_site_id = ds_out[i].globalattributes["isd_site_id"]
            # copy the global attributes
            gattr_list = list(ds_out[i].globalattributes.keys())
            # remove the site specific global attributes
            for item in ["latitude", "longitude", "altitude", "isd_site_id"]:
                gattr_list.remove(item)
            # copy everything else
            for gattr in gattr_list:
                if gattr not in ds_all.globalattributes:
                    ds_all.globalattributes[gattr] = ds_out[i].globalattributes[gattr]
            # and update the site specific global attributes
            ds_all.globalattributes["time_zone_"+isd_site_id] = ds_out[i].globalattributes["time_zone"]
            ds_all.globalattributes["latitude_"+isd_site_id] = ds_out[i].globalattributes["latitude"]
            ds_all.globalattributes["longitude_"+isd_site_id] = ds_out[i].globalattributes["longitude"]
            ds_all.globalattributes["altitude_"+isd_site_id] = ds_out[i].globalattributes["altitude"]
            # now copy the variables
            # first, we get the indices of matching datetimes
            ldt_one = ds_out[i].series["DateTime"]["Data"]
            idx = numpy.searchsorted(ldt_all, numpy.intersect1d(ldt_all, ldt_one))
            # then we get a list of the variables to copy
            series_list = ds_out[i].series.keys()
            # and remove the datetime
            if "DateTime" in series_list:
                series_list.remove("DateTime")
            # and then we loop over the variables to be copied
            for label in series_list:
                # append a number, unique to each ISD station, to the variable label
                all_label = label+"_"+str(i)
                # create empty data and flag arrays
                variable = qcutils.create_empty_variable(all_label, nrecs)
                qcutils.CreateSeries(ds_all, all_label, variable["Data"], Flag = variable["Flag"],
                                    Attr = variable["Attr"])
                # read the data out of the ISD site data structure
                data, flag, attr = qcutils.GetSeriesasMA(ds_out[i], label)
                # add the ISD site ID
                attr["isd_site_id"] = isd_site_id
                # put the data, flag and attributes into the all-in-one data structure
                ds_all.series[all_label]["Data"][idx] = data
                ds_all.series[all_label]["Flag"][idx] = flag
                ds_all.series[all_label]["Attr"] = copy.deepcopy(attr)
        # write the netCDF file with the combined data for this year
        if len(fluxnet_id) == 0:
            nc_dir_path = os.path.join(out_base_path,site,"Data","ISD")
            nc_file_name = site+"_ISD_"+str(year)+".nc"
        else:
            nc_dir_path = os.path.join(out_base_path,fluxnet_id,"Data","ISD")
            nc_file_name = fluxnet_id+"_ISD_"+str(year)+".nc"
        if not os.path.exists(nc_dir_path):
            os.makedirs(nc_dir_path)
        nc_file_path = os.path.join(nc_dir_path,nc_file_name)
        nc_file = qcio.nc_open_write(nc_file_path)
        qcio.nc_write_series(nc_file, ds_all, ndims=1)
        cf_concat["Files"]["In"][str(n)] = nc_file_path
    # concatenate the yearly files for this site
    #cf_concat.filename = "../controlfiles/ISD/concat.txt"
    #cf_concat.write()
    qcio.nc_concatenate(cf_concat)    

# write the time steps out to an Excel file
xl_file_path = os.path.join(isd_base_path, "ISD_site_timesteps.xls")
xl_write_ISD_timesteps(xl_file_path, isd_time_steps)

logger.info("All done")
