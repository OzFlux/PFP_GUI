import sys
sys.path.append('../scripts')
import csv
import datetime
import constants as c
import glob
import logging
import meteorologicalfunctions as mf
import netCDF4
import numpy
import os
import qcio
import qcts
import qcutils
import xlrd

logging.basicConfig()
# open the logging file
log = qcutils.startlog('aws2nc','../logfiles/aws2nc.log')

# dummy control file for FixTimeSteps
cf = {"Options":{"FixTimeStepMethod":"round"}}

# get the site information and the AWS stations to use
xlname = "/home/peter/OzFlux/BoM/AWS_Locations.xls"
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

in_path = "/home/peter/OzFlux/BoM/AWS/Current/"
out_path = "/home/peter/OzFlux/Sites/"
in_filename = in_path+"HM01X_Data*.csv"
file_list = sorted(glob.glob(in_filename))

#site_list = bom_sites_info.keys()
#site_list = ["Tumbarumba"]
#site_list = ["Great Western Woodlands"]
#site_list = ["Otway"]
site_list = ["Dwellingup"]
for site_name in sorted(site_list):
    log.info("Starting site: "+site_name)
    sname = site_name.replace(" ","")
    ncname = os.path.join(out_path,sname,"/Data/AWS/",sname+"_AWS.nc")
    site_latitude = bom_sites_info[site_name]["latitude"]
    site_longitude = bom_sites_info[site_name]["longitude"]
    site_elevation = bom_sites_info[site_name]["elevation"]
    site_number_list = bom_sites_info[site_name].keys()
    for item in ["latitude","longitude","elevation"]:
        if item in site_number_list: site_number_list.remove(item)
    # read the CSV files and put the contents into data_dict
    data_dict = {}
    for idx,sn in enumerate(site_number_list):
        # get a list of file names that contain the relevent station numbers
        csvname = [fn for fn in file_list if str(sn) in fn]
        # continue to next station if this station not in file_list
        if len(csvname)==0: continue
        log.info("Reading CSV file: "+str(csvname[0]))
        # columns are:
        # file data content
        #  1    0    station number
        #  7    1    year, local standard time
        #  8    2    month, local standard time
        #  9    3    day, local standard time
        #  10   4    hour, local standard time
        #  11   5    minute, local standard time
        #  12   6    precip since 0900
        #  14   7    air temperature, C
        #  16   8    dew point temperature, C
        #  18   9    relative humidity, %
        #  20   10   wind speed, m/s
        #  22   11   wind direction, degT
        #  24   12   gust in last 10 minutes, m/s
        #  26   13   station pressure, hPa
        data=numpy.genfromtxt(csvname[0],skip_header=1,delimiter=",",usecols=(1,7,8,9,10,11,12,14,16,18,20,22,24,26),
                              missing_values=-9999,filling_values=-9999)
        data = numpy.ma.masked_equal(data,float(-9999),copy=True)
        data_dict[sn] = data
    # now pull the data out and put it in separate data structures, one per station, all
    # of which are held in a data structure dictionary
    ds_dict = {}
    for bom_id in data_dict.keys():
        log.info("Processing BoM station: "+str(bom_id))
        # create a data structure
        ds=qcio.DataStructure()
        # put the year, month, day, hour and minute into the data structure
        nRecs = data_dict[bom_id].shape[0]
        ds.globalattributes["nc_nrecs"] = nRecs
        ds.globalattributes["time_step"] = 30
        ds.globalattributes["latitude"] = bom_sites_info[site_name][str(bom_id)]["latitude"]
        ds.globalattributes["longitude"] = bom_sites_info[site_name][str(bom_id)]["longitude"]
        flag = numpy.zeros(nRecs,dtype=numpy.int32)
        Seconds = numpy.zeros(nRecs,dtype=numpy.float64)
        qcutils.CreateSeries(ds,'Year',data_dict[bom_id][:,1],flag,qcutils.MakeAttributeDictionary(long_name='Year',units='none'))
        qcutils.CreateSeries(ds,'Month',data_dict[bom_id][:,2],flag,qcutils.MakeAttributeDictionary(long_name='Month',units='none'))
        qcutils.CreateSeries(ds,'Day',data_dict[bom_id][:,3],flag,qcutils.MakeAttributeDictionary(long_name='Day',units='none'))
        qcutils.CreateSeries(ds,'Hour',data_dict[bom_id][:,4],flag,qcutils.MakeAttributeDictionary(long_name='Hour',units='none'))
        qcutils.CreateSeries(ds,'Minute',data_dict[bom_id][:,5],flag,qcutils.MakeAttributeDictionary(long_name='Minute',units='none'))
        qcutils.CreateSeries(ds,'Second',Seconds,flag,qcutils.MakeAttributeDictionary(long_name='Second',units='none'))
        # now get the Python datetime
        qcutils.get_datetimefromymdhms(ds)
        # now put the data into the data structure
        attr=qcutils.MakeAttributeDictionary(long_name='Precipitation since 0900',units='mm',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'Precip',data_dict[bom_id][:,6],flag,attr)
        attr=qcutils.MakeAttributeDictionary(long_name='Air temperature',units='C',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'Ta',data_dict[bom_id][:,7],flag,attr)
        attr=qcutils.MakeAttributeDictionary(long_name='Dew point temperature',units='C',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'Td',data_dict[bom_id][:,8],flag,attr)
        attr=qcutils.MakeAttributeDictionary(long_name='Relative humidity',units='%',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'RH',data_dict[bom_id][:,9],flag,attr)
        attr=qcutils.MakeAttributeDictionary(long_name='Wind speed',units='m/s',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'Ws',data_dict[bom_id][:,10],flag,attr)
        attr=qcutils.MakeAttributeDictionary(long_name='Wind direction',units='degT',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'Wd',data_dict[bom_id][:,11],flag,attr)
        attr=qcutils.MakeAttributeDictionary(long_name='Wind gust',units='m/s',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'Wg',data_dict[bom_id][:,12],flag,attr)
        data_dict[bom_id][:,13] = data_dict[bom_id][:,13]/float(10)
        attr=qcutils.MakeAttributeDictionary(long_name='Air Pressure',units='kPa',
                                             bom_id=str(bom_id),bom_name=bom_sites_info[site_name][str(bom_id)]["site_name"],
                                             bom_dist=bom_sites_info[site_name][str(bom_id)]["distance"])
        qcutils.CreateSeries(ds,'ps',data_dict[bom_id][:,13],flag,attr)
        # fix any time stamp issues
        if qcutils.CheckTimeStep(ds):
            qcutils.FixTimeStep(ds)
            # update the Year, Month, Day etc from the Python datetime
            qcutils.get_ymdhmsfromdatetime(ds)
        # now interpolate
        for label in ["Precip","Ta","Td","RH","Ws","Wd","Wg","ps"]:
            qcts.InterpolateOverMissing(ds,series=label,maxlen=2)
        # put this stations data into the data structure dictionary
        ds_dict[bom_id] = ds

    # get the earliest start datetime and the latest end datetime
    log.info("Finding the start and end dates")
    bom_id_list = ds_dict.keys()
    ds0 = ds_dict[bom_id_list[0]]
    ldt = ds0.series["DateTime"]["Data"]
    #print bom_id_list[0],":",ldt[0],ldt[-1]
    start_date = ldt[0]
    end_date = ldt[-1]
    bom_id_list.remove(bom_id_list[0])
    for bom_id in bom_id_list:
        dsn = ds_dict[bom_id]
        ldtn = dsn.series["DateTime"]["Data"]
        #print bom_id,":",ldtn[0],ldtn[-1]
        start_date = min([start_date,ldtn[0]])
        end_date = max([end_date,ldtn[-1]])
    #print start_date,end_date

    # merge the individual data structures into a single one
    log.info("Merging file contents")
    ds_all = qcio.DataStructure()
    ds_all.globalattributes["time_step"] = 30
    ds_all.globalattributes["xl_datemode"] = 0
    ds_all.globalattributes["site_name"] = site_name
    ds_all.globalattributes["latitude"] = site_latitude
    ds_all.globalattributes["longitude"] = site_longitude
    ds_all.globalattributes["elevation"] = site_elevation
    ts = int(ds_all.globalattributes["time_step"])
    ldt_all = [result for result in qcutils.perdelta(start_date,end_date,datetime.timedelta(minutes=ts))]
    nRecs = len(ldt_all)
    ds_all.globalattributes["nc_nrecs"] = nRecs
    ds_all.series["DateTime"] = {}
    ds_all.series["DateTime"]["Data"] = ldt_all
    flag = numpy.zeros(nRecs,dtype=numpy.int32)
    ds_all.series["DateTime"]["Flag"] = flag
    ds_all.series["DateTime"]["Attr"] = {}
    ds_all.series['DateTime']["Attr"]["long_name"] = "Date-time object"
    ds_all.series['DateTime']["Attr"]["units"] = "None"
    # get the year, month, day, hour, minute and seconds from the Python datetime
    qcutils.get_ymdhmsfromdatetime(ds_all)
    # get the xlDateTime from the
    xlDateTime = qcutils.get_xldatefromdatetime(ds_all)
    attr = qcutils.MakeAttributeDictionary(long_name="Date/time in Excel format",units="days since 1899-12-31 00:00:00")
    qcutils.CreateSeries(ds_all,"xlDateTime",xlDateTime,flag,attr)
    # loop over the stations
    for idx,bom_id in enumerate(ds_dict.keys()):
        log.info("Merging BoM site: "+str(bom_id))
        ds = ds_dict[bom_id]
        ldt = ds.series["DateTime"]["Data"]
        index = qcutils.FindIndicesOfBInA(ldt,ldt_all)
        # loop over the variables
        for label in ["Precip","Ta","Td","RH","Ws","Wd","Wg","ps"]:
            data_all = numpy.ma.ones(nRecs,dtype=numpy.float64)*float(c.missing_value)
            flag_all = numpy.zeros(nRecs,dtype=numpy.int32)
            data,flag,attr = qcutils.GetSeriesasMA(ds,label)
            data_all[index] = data
            flag_all[index] = flag
            output_label = label+"_"+str(idx)
            attr["bom_id"] = str(bom_id)
            qcutils.CreateSeries(ds_all,output_label,data_all,flag_all,attr)
    # get precipitation per time step
    # now get precipitation per time step from the interpolated precipitation accumulated over the day
    precip_list = [x for x in ds_all.series.keys() if ("Precip" in x) and ("_QCFlag" not in x)]
    #print precip_list
    log.info("Converting 24 hour accumulated precipitation")
    for output_label in precip_list:
        # getthe accumlated precipitation
        accum_data,accum_flag,accum_attr = qcutils.GetSeriesasMA(ds_all,output_label)
        # make the flag a masked array
        accum_flag = numpy.ma.array(accum_flag)
        # round small precipitations to 0
        index = numpy.ma.where(accum_data<0.01)[0]
        accum_data[index] = float(0)
        # get the precipitation per time step
        precip = numpy.ma.ediff1d(accum_data,to_begin=0)
        # trap the times when the accumlated precipitation is reset
        # This should be at a standard time every day for all BoM sites but this is not the case
        # For eaxample, at 72161, there is a period in 09/2010 when the reset seems to occur at
        # 1000 instead of the expected 0900 (possible daylight saving error?)
        # To get around this, we check the differentiated precipitation:
        # - if the precipitation per time step is positive, do nothing
        # - if the precipitation per time step is negative;
        #   - if the QC flag is 50 (linear interpolation) then set the precipitation to 0
        #   - if the QC flag is 0 then set the precipitation per time step to the accumlated
        #     precipitation
        # find times when the precipitation per time step is negative and the QC flag is not 0 ...
        index = numpy.ma.where((precip<0)&(accum_flag!=0))[0]
        # ... and set the precipitation per time step for these times to 0
        precip[index] = float(0)
        # find any remaining times when the precipitation per time step is negative ...
        index = numpy.ma.where(precip<0)[0]
        # ... and set them to the accumulated precipitation
        precip[index] = accum_data[index]
        #index = [x for x in range(len(ldt_all)) if (ldt_all[x].hour==8) and (ldt_all[x].minute==30)]
        #precip[index] = float(0)
        #index = [x for x in range(len(ldt_all)) if (ldt_all[x].hour==9) and (ldt_all[x].minute==0)]
        #precip[index] = accum_24hr[index]
        # set attributes as appropriate
        accum_attr["long_name"] = "Precipitation total over time step"
        accum_attr["units"] = "mm/30 minutes"
        # put the precipitation per time step back into the data struicture
        qcutils.CreateSeries(ds_all,output_label,precip,accum_flag,accum_attr)
    # calculate missing humidities
    RH_list = sorted([x for x in ds_all.series.keys() if ("RH" in x) and ("_QCFlag" not in x)])
    Ta_list = sorted([x for x in ds_all.series.keys() if ("Ta" in x) and ("_QCFlag" not in x)])
    ps_list = sorted([x for x in ds_all.series.keys() if ("ps" in x) and ("_QCFlag" not in x)])
    for RH_label,Ta_label,ps_label in zip(RH_list,Ta_list,ps_list):
        Ta,f,a = qcutils.GetSeriesasMA(ds_all,Ta_label)
        RH,f,a = qcutils.GetSeriesasMA(ds_all,RH_label)
        ps,f,a = qcutils.GetSeriesasMA(ds_all,ps_label)
        Ah = mf.absolutehumidityfromRH(Ta, RH)
        attr = qcutils.MakeAttributeDictionary(long_name='Absolute humidity',units='g/m3',standard_name='not defined',
                                               bom_id=a["bom_id"],bom_name=a["bom_name"],bom_dist=a["bom_dist"])
        qcutils.CreateSeries(ds_all,RH_label.replace("RH","Ah"),Ah,f,attr)
        q = mf.specifichumidityfromRH(RH, Ta, ps)
        attr = qcutils.MakeAttributeDictionary(long_name='Specific humidity',units='kg/kg',standard_name='not defined',
                                               bom_id=a["bom_id"],bom_name=a["bom_name"],bom_dist=a["bom_dist"])
        qcutils.CreateSeries(ds_all,RH_label.replace("RH","q"),q,f,attr)

    # now write the data structure to file
    # OMG, the user may want to overwrite the old data ...
    if os.path.exists(ncname):
        # ... but we will save them from themselves!
        t = time.localtime()
        rundatetime = datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]).strftime("%Y%m%d%H%M")
        new_ext = "_"+rundatetime+".nc"
        # add the current local datetime the old file name
        newFileName = ncname.replace(".nc",new_ext)
        msg = " Renaming "+ncname+" to "+newFileName
        log.info(msg)
        # ... and rename the old file to preserve it
        os.rename(ncname,newFileName)
        # now the old file will not be overwritten
    ncfile = qcio.nc_open_write(ncname)
    qcio.nc_write_series(ncfile,ds_all,ndims=1)
    log.info("Finished site: "+site_name)

print "aws2nc: All done"