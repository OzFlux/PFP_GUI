import csv
import dateutil
import datetime
import netCDF4
import numpy
import matplotlib.pyplot as plt
import os
from PyQt4 import Qt
import pytz
import scipy.interpolate, scipy.signal
import sys
# check the scripts directory is present
if not os.path.exists("../scripts/"):
    print("modis_evi2nc: the scripts directory is missing")
    sys.exit()
# since the scripts directory is there, try importing the modules
sys.path.append('../scripts')
import pfp_io
import pfp_utils

def read_evi_file(evi_name):
    # open the CSV file
    evi_file = open(evi_name, 'rb')
    # read the header line
    header = evi_file.readline()
    # close the file
    evi_file.close()
    # get a list of variable names
    names = header.replace("\n", "").split(",")
    # read the CSV file using genfromtxt
    tmp = numpy.genfromtxt(evi_name, delimiter=',', dtype=None, names=names,
                           skip_header=1, deletechars=deletechars)
    # get the datetime from the character date string
    dt = numpy.array([dateutil.parser.parse(s) for s in tmp["Date"]])
    names.remove("Date")
    # create the data dictionary
    evi = {"DateTime": dt}
    # load the data into the dictionary
    for item in names:
        evi[item] = numpy.array(tmp[item], dtype=numpy.float64)
    # return the data dictionary
    return evi

# load the control file
app = Qt.QApplication([])
cf = pfp_io.load_controlfile(path="../controlfiles/MODIS/")

deletechars = set("""~!@#$^&=+~\|]}[{';: ?.>,<""")
ts = 30
evi_time_units = "seconds since 1970-01-01 00:00:00.0"
do_plots = True

sites = list(cf["Sites"].keys())
site = sites[0]
site_timezone = cf["Sites"][site]["site_timezone"]
site_latitude = float(cf["Sites"][site]["site_latitude"])
site_longitude = float(cf["Sites"][site]["site_longitude"])
site_timestep = int(cf["Sites"][site]["site_timestep"])
evi_min = float(cf["Sites"][site]["evi_min"])
evi_max = float(cf["Sites"][site]["evi_max"])
sgnp = int(cf["Sites"][site]["sg_num_points"])
sgo = int(cf["Sites"][site]["sg_order"])
# MOD13 (Terra)
mod_file_name = site+"_"+cf["Files"]["mod_file"]
mod_file_path = os.path.join(cf["Files"]["base_path"],site,"Data","MODIS","MOD13Q1",mod_file_name)
if not os.path.exists(mod_file_path):
    print("modis_evi2nc: " + mod_file_path)
    print("modis_evi2nc: MOD13Q1 file not found")
    sys.exit()
evi_mod = read_evi_file(mod_file_path)
names_mod = list(evi_mod.keys())
# MYD13 (Aqua)
myd_file_name = site+"_"+cf["Files"]["myd_file"]
myd_file_path = os.path.join(cf["Files"]["base_path"],site,"Data","MODIS","MYD13Q1",myd_file_name)
if not os.path.exists(myd_file_path):
    print("modis_evi2nc: " + myd_file_path)
    print("modis_evi2nc: MYD13Q1 file not found")
    sys.exit()
evi_myd = read_evi_file(myd_file_path)
names_myd = list(evi_myd.keys())
if not (names_mod == names_myd):
    print("modis_evi2nc: column names in MOD and MYD do not agree")
    sys.exit()
names = list(names_mod)
if "DateTime" in names:
    names.remove("DateTime")
# combine MOD13 and MYD13 dictionaries
evi = {"DateTime": numpy.concatenate((evi_mod["DateTime"], evi_myd["DateTime"]))}
for item in names:
    evi[item] = numpy.concatenate((evi_mod[item], evi_myd[item]))
# sort the combination based on datetime
idx = evi["DateTime"].argsort()
evi["DateTime"] = evi["DateTime"][idx]
for item in names:
    evi[item] = evi[item][idx]
# QC the pixel values
pixels = [l for l in list(evi.keys()) if "EVI_pixel" in l]
pixel_values = numpy.vstack([evi[p] for p in pixels])
# mask if below 0.1 or above 0.45
pixel_values = numpy.ma.masked_where((pixel_values < evi_min)|(pixel_values > evi_max), pixel_values)
# calculate the 10 and 90 percentile values
lo, hi = numpy.percentile(pixel_values, (10, 90), axis=0)
# mask if less than the 10th percentile or greater than the 90th percentile
pixel_values = numpy.ma.masked_where((pixel_values < lo)|(pixel_values > hi), pixel_values)
evi_qc = {"DateTime": evi["DateTime"]}
evi_qc["time"] = numpy.ma.array(netCDF4.date2num(evi_qc["DateTime"], evi_time_units))
# get the statistics
evi_qc["mean"] = numpy.ma.mean(pixel_values, axis=0)
evi_qc["count"] = numpy.ma.count(pixel_values, axis=0)
evi_qc["min"] = numpy.ma.min(pixel_values, axis=0)
evi_qc["max"] = numpy.ma.max(pixel_values, axis=0)

if do_plots:
    fig, axs = plt.subplots(2, 1, figsize=(11,8), sharex=True)
    axs[0].plot(evi["DateTime"], evi["mean"], 'b.')
    axs[0].plot(evi["DateTime"], evi["min"], 'r+')
    axs[0].plot(evi["DateTime"], evi["max"], 'gx')
    axs[1].plot(evi_qc["DateTime"], evi_qc["mean"], 'b.')
    axs[1].plot(evi_qc["DateTime"], evi_qc["min"], 'r+')
    axs[1].plot(evi_qc["DateTime"], evi_qc["max"], 'gx')
    axs[0].set_ylabel("EVI")
    axs[1].set_ylabel("EVI QC")
    fig.show()

# interpolate onto a regular 8 day time step
evi_8day = {}
start = evi_qc["DateTime"][0]
end = evi_qc["DateTime"][-1]
tdts = datetime.timedelta(days=8)
evi_8day["DateTime"] = [result for result in pfp_utils.perdelta(start, end, tdts)]
evi_8day["time"] = netCDF4.date2num(evi_8day["DateTime"], evi_time_units)
# get rid of any masked elements
m1 = numpy.ma.getmaskarray(evi_qc["time"])
m2 = numpy.ma.getmaskarray(evi_qc["mean"])
mask = numpy.ma.mask_or(m1, m2)
time = numpy.ma.compressed(numpy.ma.masked_where(mask, evi_qc["time"]))
mean = numpy.ma.compressed(numpy.ma.masked_where(mask, evi_qc["mean"]))
# now we can do the interpolation and smoothing
f = scipy.interpolate.Akima1DInterpolator(time, mean)
evi_8day["mean"] = f(evi_8day["time"])
# run a Savitzky-Golay filter through the 8 day values
evi_8day["smoothed"] = scipy.signal.savgol_filter(evi_8day["mean"], sgnp, sgo, mode="mirror")

if do_plots:
    fig, axs = plt.subplots(1, 1, figsize=(11,8), sharex=True)
    axs.plot(evi["DateTime"], evi["mean"], 'b.')
    axs.plot(evi_8day["DateTime"], evi_8day["mean"], 'r+')
    axs.plot(evi_8day["DateTime"], evi_8day["smoothed"], 'g--')
    axs.set_ylabel("EVI")
    fig.show()

# interpolate to the tower time step
interpolation = "Akima"
start = evi_8day["DateTime"][0]
end = evi_8day["DateTime"][-1]
evi_ts = {}
tdts = datetime.timedelta(minutes=site_timestep)
evi_ts["DateTime"] = [result for result in pfp_utils.perdelta(start, end, tdts)]
evi_ts["time"] = netCDF4.date2num(evi_ts["DateTime"], evi_time_units)
if interpolation == "linear":
    fm = scipy.interpolate.interp1d(evi_8day["time"], evi_8day["mean"], bounds_error=False)
    fs = scipy.interpolate.interp1d(evi_8day["time"], evi_8day["smoothed"], bounds_error=False)
elif interpolation == "Akima":
    fm = scipy.interpolate.Akima1DInterpolator(evi_8day["time"], evi_8day["mean"])
    fs = scipy.interpolate.Akima1DInterpolator(evi_8day["time"], evi_8day["smoothed"])
evi_ts["mean"] = fm(evi_ts["time"])
evi_ts["smoothed"] = fs(evi_ts["time"])

if do_plots:
    fig, axs = plt.subplots(1, 1, figsize=(11,8), sharex=True)
    axs.plot(evi_ts["DateTime"], evi_ts["mean"], 'b-')
    axs.plot(evi_8day["DateTime"], evi_8day["mean"], 'bo')
    axs.plot(evi_ts["DateTime"], evi_ts["smoothed"], 'r--')
    axs.plot(evi_8day["DateTime"], evi_8day["smoothed"], 'ro')
    axs.set_ylabel("EVI")
    fig.show()

# create a data structure and write the global attributes
ds = pfp_io.DataStructure()
ds.series["DateTime"] = {}
ds.globalattributes["site_name"] = site
ds.globalattributes["time_zone"] = site_timezone
ds.globalattributes["longitude"] = site_longitude
ds.globalattributes["latitude"] = site_latitude
ds.globalattributes["time_step"] = site_timestep
ds.globalattributes["xl_datemode"] = str(0)
ds.globalattributes["nc_level"] = "L1"
# convert from UTC to local time
site_tz = pytz.timezone(site_timezone)
# put the time zone (UTC) into the datetime
dt_utc = [x.replace(tzinfo=pytz.utc) for x in evi_ts["DateTime"]]
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
# put the QC'd, smoothed and interpolated EVI into the data structure
flag = numpy.zeros(len(dt_loc),dtype=numpy.int32)
attr = pfp_utils.MakeAttributeDictionary(long_name="MODIS EVI, smoothed and interpolated", units="none",
                                       horiz_resolution="250m",
                                       cutout_size=str(3),
                                       evi_min=str(evi_min),
                                       evi_max=str(evi_max),
                                       sg_num_points=str(sgnp),
                                       sg_order=str(sgo))
pfp_utils.CreateSeries(ds, "EVI", evi_ts["smoothed"], flag, attr)

attr = pfp_utils.MakeAttributeDictionary(long_name="MODIS EVI, interpolated", units="none",
                                       horiz_resolution="250m",
                                       cutout_size=str(3),
                                       evi_min=str(evi_min),
                                       evi_max=str(evi_max))
pfp_utils.CreateSeries(ds, "EVI_notsmoothed", evi_ts["mean"], flag, attr)
# now write the data structure to a netCDF file
out_name = os.path.join(cf["Files"]["base_path"],site,"Data","MODIS",site+"_EVI.nc")
out_file = pfp_io.nc_open_write(out_name)
pfp_io.nc_write_series(out_file, ds, ndims=1)

print("modis_evi2nc: finished")