# Python modules
from configobj import ConfigObj
from collections import OrderedDict
import ast
import copy
import csv
import datetime
import dateutil
import logging
import netCDF4
import numpy
import ntpath
import os
import pandas
import pdb
import platform
import sys
import time
import Tkinter, tkFileDialog
import xlrd
import xlwt
import xlsxwriter
from PyQt4 import QtGui
# PFP modules
import cfg
import constants as c
import meteorologicalfunctions as pfp_mf
import pfp_cfg
import pfp_ck
import pfp_compliance
import pfp_func
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

class DataStructure(object):
    def __init__(self):
        self.series = {}
        self.globalattributes = {}
        self.globalattributes["Functions"] = ""
        self.mergeserieslist = []
        self.averageserieslist = []
        self.returncodes = {"value":0,"message":"OK"}

def convert_v27tov28():
    """ Convert V2.7 (1D) netCDF files to V2.8 (3D). """
    # get the file names
    ncV27name = get_filename_dialog(path="../Sites")
    ncV28name = ncV27name.replace(".nc","_V28.nc")
    # read the V2.7 file
    ds = nc_read_series(ncV27name)
    # add the "time_zone" global attribute if it is not present
    if "time_zone" not in ds.globalattributes.keys():
        for gattr in ["site_name","SiteName"]:
            if gattr in ds.globalattributes.keys():
                time_zone,found = pfp_utils.get_timezone(ds.globalattributes[gattr],prompt="yes")
        ds.globalattributes["time_zone"] = time_zone
    # add the "missing_value" attribute if it is not present
    for ThisOne in ds.series.keys():
        if "missing_value" not in ds.series[ThisOne]["Attr"].keys():
            ds.series[ThisOne]["Attr"]["missing_value"] = numpy.int32(c.missing_value)
    # write the V2.8 file
    ncFile = nc_open_write(ncV28name,nctype='NETCDF4')
    nc_write_series(ncFile, ds)

def copy_datastructure(cf,ds_in):
    '''
    Return a copy of a data structure based on the following rules:
     1) if the netCDF file at the "copy_to" level does not exist
        then copy the existing data structure at the "input" level
        to create a new data structure at the "output" level.
    '''
    # assumptions that need to be checked are:
    #  - the start datetime of the two sets of data are the same
    #  - the end datetime of the L3 data is the same or after the
    #    end datetime of the the L4 data
    #    - if the end datetimes are the same then we are just re-processing something
    #    - if the end datetime for the L3 data is after the end date of the L4 data
    #      then more data has been added to this year and the user wants to gap fill
    #      the new data
    # modificatons to be made:
    #  - check the modification datetime of the L3 and L4 files:
    #     - if the L3 file is newer than the L4 file the disregard the "UseExistingOutFile" setting
    # get the output (L4) file name
    ct_filename = cf['Files']['file_path']+cf['Files']['out_filename']
    # if the L4 file does not exist then create the L4 data structure as a copy
    # of the L3 data structure
    if not os.path.exists(ct_filename):
        ds_out = copy.deepcopy(ds_in)
    # if the L4 file does exist ...
    if os.path.exists(ct_filename):
        # check to see if the user wants to use it
        if pfp_utils.get_keyvaluefromcf(cf,["Options"],"UseExistingOutFile",default="No")!='Yes':
            # if the user doesn't want to use the existing L4 data then create
            # the L4 data structure as a copy of the L3 data structure
            ds_out = copy.deepcopy(ds_in)
        else:
            # the user wants to use the data from an existing L4 file
            # get the netCDF file name at the "input" level
            outfilename = get_outfilenamefromcf(cf)
            # read the netCDF file at the "input" level
            ds_file = nc_read_series(outfilename)
            dt_file = ds_file.series['DateTime']['Data']
            sd_file = str(dt_file[0])
            ed_file = str(dt_file[-1])
            # create a copy of the data
            ds_out = copy.deepcopy(ds_in)
            dt_out = ds_out.series['DateTime']['Data']
            ts = ds_out.globalattributes['time_step']
            sd_out = str(dt_out[0])
            ed_out = str(dt_out[-1])
            # get the start and end indices based on the start and end dates
            si = pfp_utils.GetDateIndex(dt_out,sd_file,ts=ts,default=0,match='exact')
            ei = pfp_utils.GetDateIndex(dt_out,ed_file,ts=ts,default=-1,match='exact')
            # now replace parts of ds_out with the data read from file
            for ThisOne in ds_file.series.keys():
                # check to see if the L4 series exists in the L3 data
                if ThisOne in ds_out.series.keys():
                    # ds_out is the copy of the L3 data, now fill it with the L4 data read from file
                    ds_out.series[ThisOne]['Data'][si:ei+1] = ds_file.series[ThisOne]['Data']
                    ds_out.series[ThisOne]['Flag'][si:ei+1] = ds_file.series[ThisOne]['Flag']
                else:
                    # if it doesn't, create the series and put the data into it
                    ds_out.series[ThisOne] = {}
                    ds_out.series[ThisOne] = ds_file.series[ThisOne].copy()
                    # check to see if we have to append data to make the copy of the L4 data now
                    # in the L3 data structure the same length as the existing L3 data
                    nRecs_file = int(ds_file.globalattributes['nc_nrecs'])
                    nRecs_out = int(ds_out.globalattributes['nc_nrecs'])
                    if nRecs_file < nRecs_out:
                        # there is more data at L3 than at L4
                        # append missing data to make the series the same length
                        nRecs_append = nRecs_out - nRecs_file
                        data = numpy.array([c.missing_value]*nRecs_append,dtype=numpy.float64)
                        flag = numpy.ones(nRecs_append,dtype=numpy.int32)
                        ds_out.series[ThisOne]['Data'] = numpy.concatenate((ds_out.series[ThisOne]['Data'],data))
                        ds_out.series[ThisOne]['Flag'] = numpy.concatenate((ds_out.series[ThisOne]['Flag'],flag))
                    elif nRecs_file > nRecs_out:
                        # tell the user something is wrong
                        logger.error('copy_datastructure: L3 file contains less data than L4 file')
                        # return an empty dictionary
                        ds_out = {}
                    else:
                        # nRecs_file and nRecs_out are equal so we do not need to do anything
                        pass
    return ds_out

def csv_read_parse_cf(cf):
    info = {"cf_ok":False}
    if "DateTime" not in cf["Variables"]:
        msg = "No [[DateTime]] section in control file ..."
        logger.error(msg)
        return info
    if "Function" not in cf["Variables"]["DateTime"]:
        msg = "No [[[Function]]] section in [[DateTime]] section ..."
        logger.error(msg)
        return info
    # get the filename, return if missing or doesn't exist
    csv_filename = get_infilenamefromcf(cf)
    if len(csv_filename)==0:
        msg = ' in_filename not found in control file'
        logger.error(msg)
        return info
    if not os.path.exists(csv_filename):
        msg = ' Input file '+csv_filename+' specified in control file not found'
        logger.error(msg)
        return info
    else:
        info["csv_filename"] = csv_filename

    # get the header row, first data row and units row
    opt = pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_firstdatarow",default=2)
    info["first_data_row"] = int(opt)
    info["skip_header"] = info["first_data_row"]-1
    opt = pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_headerrow",default=1)
    info["header_row"] = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_unitsrow",default=-1)
    info["units_row"] = int(opt)
    # set the delimiters
    info["delimiters"] = [",", "\t"]

    # sniff the file to find out the dialect and the delimiter
    csv_file = open(info["csv_filename"],'rb')
    # skip to the header row
    for i in range(0, info["first_data_row"]):
        line = csv_file.readline()
        if i == info["header_row"]-1 or i == info["units_row"]-1:
            # sniff the CSV dialect
            info["dialect"] = csv.Sniffer().sniff(line, info["delimiters"])
        if i == info["header_row"]-1:
            info["header_line"] = line
            # header line from comma separated string to list
            info["header_list"] = info["header_line"].split(info["dialect"].delimiter)
        if i == info["units_row"]-1:
            info["units_line"] = line
            # units line from comma separated string to list
            info["units_list"] = info["units_line"].split(info["dialect"].delimiter)
    csv_file.close()
    # get a list of series to be read from CSV file and check
    # to make sure the requested variables are in the csv file,
    # dump them if they aren't
    csv_varnames = {}
    for item in cf["Variables"].keys():
        if "csv" in cf["Variables"][item].keys():
            opt = pfp_utils.get_keyvaluefromcf(cf, ["Variables", item, "csv"], "name", default="")
            if opt in info["header_line"]:
                csv_varnames[item] = str(opt)
            else:
                msg = "  "+str(opt)+" not found in CSV file, skipping ..."
                logger.error(msg)
                continue
        elif "Function" not in cf["Variables"][item].keys():
            msg = " No csv or Function section in control file for "+item
            logger.info(msg)
            continue
    info["csv_varnames"] = csv_varnames
    info["var_list"] = csv_varnames.keys()
    info["csv_list"] = [csv_varnames[x] for x in info["var_list"]]
    info["col_list"] = [info["header_list"].index(item) for item in info["csv_list"]]

    # define the missing values and the value with which to fill them
    info["missing_values"] = "NA,N/A,NAN,NaN,nan,#NAME?,#VALUE!,#DIV/0!,#REF!,Infinity,-Infinity"
    info["filling_values"] = c.missing_value
    info["deletechars"] = set("""~!@#$%^&=+~\|]}[{';: ?.>,<""")

    info["cf_ok"] = True

    return info

def csv_read_series(cf):
    """
    Purpose:
     Reads a CSV file and returns the data in a data structure.
    Usage:
     ds = csv_read_series(cf)
     where cf is a control file
           ds is a data structure
    Author: PRI
    Date: September 2015
    Mods: February 2018 (PRI) - rewrite
    """
    # get a data structure
    ds = DataStructure()
    # add the global atributes
    for gattr in cf['Global'].keys():
        ds.globalattributes[gattr] = cf['Global'][gattr]
    # parse the control file
    info = csv_read_parse_cf(cf)
    # return with an empty data structure if parsing failed
    if not info["cf_ok"]:
        return ds
    # read the csv file using numpy's genfromtxt
    file_name = os.path.split(info["csv_filename"])
    logger.info(" Reading "+file_name[1])
    # read the CSV file
    data_array = numpy.genfromtxt(info["csv_filename"], delimiter=info["dialect"].delimiter,
                                  skip_header=info["skip_header"], names=info["header_line"],
                                  usecols=info["col_list"], missing_values=info["missing_values"],
                                  filling_values=info["filling_values"], deletechars=info["deletechars"],
                                  usemask=True, dtype=None)
    # get the variables and put them into the data structure
    # we'll deal with DateTime separately
    for item in ["DateTime"]:
        if item in info["var_list"]:
            info["var_list"].remove(item)
    # put the data into the data structure
    for label in info["var_list"]:
        csv_label = info["csv_varnames"][label]
        variable = {"Label":label}
        # make the flag
        flag = numpy.zeros(len(data_array[csv_label]), dtype=numpy.int32)
        # get the data
        try:
            data = numpy.array(data_array[info["csv_varnames"][label]], dtype=numpy.float64)
            idx = numpy.where(numpy.isfinite(data) == False)[0]
            data[idx] = numpy.float64(c.missing_value)
            flag[idx] = numpy.int32(1)
        except ValueError:
            data = data_array[info["csv_varnames"][label]]
        # set flag of missing data to 1
        missing = numpy.full_like(data, c.missing_value)
        idx = numpy.where(data == missing)[0]
        flag[idx] = numpy.int32(1)
        variable["Data"] = data
        variable["Flag"] = flag
        # make the attribute dictionary ...
        attr = {}
        variable["Attr"] = copy.deepcopy(attr)
        pfp_utils.CreateVariable(ds, variable)
    ## call the function given in the control file to convert the date/time string to a datetime object
    ## NOTE: the function being called needs to deal with missing date values and empty lines
    #function_string = cf["Variables"]["DateTime"]["Function"]["func"]
    #function_name = function_string.split("(")[0]
    #function_args = function_string.split("(")[1].replace(")","").split(",")
    #result = getattr(pfp_func,function_name)(ds, *function_args)
    # set some global attributes
    ds.globalattributes['featureType'] = 'timeseries'
    ds.globalattributes['csv_filename'] = info["csv_filename"]
    ds.globalattributes['xl_datemode'] = str(0)
    s = os.stat(info["csv_filename"])
    t = time.localtime(s.st_mtime)
    ds.globalattributes['csv_moddatetime'] = str(datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]))
    ds.returncodes = {"value":0,"message":"OK"}
    return ds

def nc_2xls(ncfilename,outputlist=None):
    # read the netCDF file
    ds = nc_read_series(ncfilename,checktimestep=False)
    nRecs = int(ds.globalattributes["nc_nrecs"])
    nCols = len(ds.series.keys())
    if outputlist!=None: nCols = len(outputlist)
    # xlwt seems to only handle 225 columns
    if nRecs<65535 and nCols<220:
        # write the variables to the Excel 97/2003 file
        xlfilename= ncfilename.replace('.nc','.xls')
        xl_write_series(ds,xlfilename,outputlist=outputlist)
    else:
        # write the variables to the Excel 2010 file
        xlsxfilename= ncfilename.replace('.nc','.xlsx')
        xlsx_write_series(ds,xlsxfilename,outputlist=outputlist)

def read_eddypro_full(csvname):
    ds = DataStructure()
    csvfile = open(csvname,'rb')
    csvreader = csv.reader(csvfile)
    n = 0
    adatetime = []
    us_data_list = []
    us_flag_list = []
    Fh_data_list = []
    Fh_flag_list = []
    Fe_data_list = []
    Fe_flag_list = []
    Fc_data_list = []
    Fc_flag_list = []
    for row in csvreader:
        if n==0:
            header=row
        elif n==1:
            varlist=row
            us_data_col = varlist.index('u*')
            us_flag_col = varlist.index('qc_Tau')
            Fh_data_col = varlist.index('H')
            Fh_flag_col = varlist.index('qc_H')
            Fe_data_col = varlist.index('LE')
            Fe_flag_col = varlist.index('qc_LE')
            Fc_data_col = varlist.index('co2_flux')
            Fc_flag_col = varlist.index('qc_co2_flux')
        elif n==2:
            unitlist=row
        else:
            adatetime.append(datetime.datetime.strptime(row[1]+' '+row[2],'%Y-%m-%d %H:%M'))
            us_data_list.append(float(row[us_data_col]))
            us_flag_list.append(float(row[us_flag_col]))
            Fh_data_list.append(float(row[Fh_data_col]))
            Fh_flag_list.append(float(row[Fh_flag_col]))
            Fe_data_list.append(float(row[Fe_data_col]))
            Fe_flag_list.append(float(row[Fe_flag_col]))
            Fc_data_list.append(float(row[Fc_data_col]))
            Fc_flag_list.append(float(row[Fc_flag_col]))
        n = n + 1
    nRecs = len(adatetime)
    ds.globalattributes["nc_nrecs"] = nRecs
    ds.series['DateTime'] = {}
    ds.series['DateTime']['Data'] = adatetime
    pfp_utils.round_datetime(ds,mode="nearest_timestep")
    pfp_utils.get_ymdhmsfromdatetime(ds)

    variable = {"Label":"ustar"}
    variable["Data"] = numpy.array(us_data_list,dtype=numpy.float64)
    variable["Flag"] = numpy.array(us_flag_list,dtype=numpy.int32)
    variable["Attr"] = pfp_utils.MakeAttributeDictionary()
    pfp_utils.CreateVariable(ds, variable)
    variable = {"Label":"Fh"}
    variable["Data"] = numpy.array(Fh_data_list,dtype=numpy.float64)
    variable["Flag"] = numpy.array(Fh_flag_list,dtype=numpy.int32)
    variable["Attr"] = pfp_utils.MakeAttributeDictionary()
    pfp_utils.CreateVariable(ds, variable)
    variable = {"Label":"Fe"}
    variable["Data"] = numpy.array(Fe_data_list,dtype=numpy.float64)
    variable["Flag"] = numpy.array(Fe_flag_list,dtype=numpy.int32)
    variable["Attr"] = pfp_utils.MakeAttributeDictionary()
    pfp_utils.CreateVariable(ds, variable)
    variable = {"Label":"Fc"}
    variable["Data"] = numpy.array(Fc_data_list,dtype=numpy.float64)
    variable["Flag"] = numpy.array(Fc_flag_list,dtype=numpy.int32)
    variable["Attr"] = pfp_utils.MakeAttributeDictionary()
    pfp_utils.CreateVariable(ds, variable)

    return ds

def reddyproc_write_csv(cf):
    # this needs to be re-written!
    # get the file names
    file_path = cf["Files"]["file_path"]
    nc_name = cf["Files"]["in_filename"]
    ncFileName = os.path.join(file_path, nc_name)
    if not os.path.exists(ncFileName):
        msg = " netCDF file "+ncFileName+" not found"
        logger.warning(msg)
        return
    csv_name = cf["Files"]["out_filename"]
    csvFileName = os.path.join(file_path, csv_name)
    file_name = os.path.split(csvFileName)
    if not os.path.exists(file_name[0]):
        os.makedirs(file_name[0])
    # open the csv file
    csvfile = open(csvFileName,'wb')
    writer = csv.writer(csvfile,dialect='excel-tab')
    # read the netCDF file
    ds = nc_read_series(ncFileName)
    # get the datetime series
    dt = ds.series["DateTime"]["Data"]
    ts = int(ds.globalattributes["time_step"])
    # get the start and end indices for whole days
    start_date = dt[0]
    end_date = dt[-1]
    si = pfp_utils.GetDateIndex(dt,str(start_date),ts=ts,default=0,match='startnextday')
    ei = pfp_utils.GetDateIndex(dt,str(end_date),ts=ts,default=len(dt)-1,match='endpreviousday')
    # get the date and time data
    Year,flag,attr = pfp_utils.GetSeries(ds,'Year',si=si,ei=ei)
    Ddd,flag,attr = pfp_utils.GetSeries(ds,'Ddd',si=si,ei=ei)
    Hhh,flag,attr = pfp_utils.GetSeries(ds,'Hdh',si=si,ei=ei)
    # get the data
    data = OrderedDict()
    for label in cf["Variables"].keys():
        data[label] = {"ncname":cf["Variables"][label]["ncname"],
                       "format":cf["Variables"][label]["format"]}
    series_list = data.keys()
    for series in series_list:
        ncname = data[series]["ncname"]
        if ncname not in ds.series.keys():
            logger.error("Series "+ncname+" not in netCDF file, skipping ...")
            series_list.remove(series)
            continue
        d,f,a = pfp_utils.GetSeries(ds,ncname,si=si,ei=ei)
        data[series]["Data"] = d
        data[series]["Flag"] = f
        data[series]["Attr"] = a
        fmt = data[series]["format"]
        if "." in fmt:
            numdec = len(fmt) - (fmt.index(".") + 1)
            strfmt = "{0:."+str(numdec)+"f}"
        else:
            strfmt = "{0:d}"
        data[series]["fmt"] = strfmt
    # adjust units as required
    # this could be done better, pete!
    for series in series_list:
        if series=="NEE":
            if data[series]["Attr"]["units"] in ["mg/m2/s","mgCO2/m2/s"]:
                data[series]["Data"] = pfp_mf.Fc_umolpm2psfrommgCO2pm2ps(data[series]["Data"])
                data[series]["Attr"]["units"] = "umolm-2s-1"
            elif data[series]["Attr"]["units"]=='umol/m2/s':
                data[series]["Attr"]["units"] = "umolm-2s-1"
            else:
                msg = " reddyproc_write_csv: unrecognised units for "+series+", returning ..."
                logger.error(msg)
                return 0
        if series=="LE" or series=="H" or series=="Rg":
            data[series]["Attr"]["units"] = "Wm-2"
        if series=="Tair" or series=="Tsoil":
            data[series]["Attr"]["units"] = "degC"
        if series=="rH" and data[series]["Attr"]["units"] in ["fraction","frac"]:
            idx = numpy.where(data[series]["Data"]!=c.missing_value)[0]
            data[series]["Data"][idx] = float(100)*data[series]["Data"][idx]
            data[series]["Attr"]["units"] = "%"
        if series=="VPD" and data[series]["Attr"]["units"]=="kPa":
            idx = numpy.where(data[series]["Data"]!=c.missing_value)[0]
            data[series]["Data"][idx] = float(10)*data[series]["Data"][idx]
            data[series]["Attr"]["units"] = "hPa"
        if series=="Ustar":
            if data[series]["Attr"]["units"]=="m/s":
                data[series]["Attr"]["units"] = "ms-1"
    # write the variable names to the csv file
    row_list = ['Year','DoY','Hour']
    for item in series_list:
        row_list.append(item)
    writer.writerow(row_list)
    # write the units line to the csv file
    units_list = ["-","-","-"]
    for item in series_list:
        units_list.append(data[item]["Attr"]["units"])
    writer.writerow(units_list)
    # now write the data
    for i in range(len(Year)):
        data_list = ['%d'%(Year[i]),'%d'%(int(Ddd[i])),'%.1f'%(Hhh[i])]
        for series in series_list:
            strfmt = data[series]["fmt"]
            if "d" in strfmt:
                data_list.append(strfmt.format(int(round(data[series]["Data"][i]))))
            else:
                data_list.append(strfmt.format(data[series]["Data"][i]))
        writer.writerow(data_list)
    # close the csv file
    csvfile.close()
    return

def smap_datetodatadictionary(ds,data_dict,nperday,ndays,si,ei):
    ldt = ds.series["DateTime"]["Data"][si:ei+1]
    # do the months
    month_1d,f,a = pfp_utils.GetSeries(ds,"Month",si=si,ei=ei)
    data_dict["Mo"] = {}
    data_dict["Mo"]["data"] = numpy.reshape(month_1d,[ndays,nperday])[:,0]
    data_dict["Mo"]["fmt"] = "0"
    # do the days
    data_dict["Day"] = {}
    day_1d,f,a = pfp_utils.GetSeries(ds,"Day",si=si,ei=ei)
    data_dict["Day"]["data"] = numpy.reshape(day_1d,[ndays,nperday])[:,0]
    data_dict["Day"]["fmt"] = "0"
    # day of the year
    data_dict["DOY"] = {}
    doy_1d = numpy.array([item.timetuple().tm_yday for item in ldt])
    data_dict["DOY"]["data"] = numpy.reshape(doy_1d,[ndays,nperday])[:,0]
    data_dict["DOY"]["fmt"] = "0"

def smap_docarbonfluxes(cf,ds,smap_label,si,ei):
    ncname = cf["Variables"][smap_label]["ncname"]
    data,flag,attr = pfp_utils.GetSeriesasMA(ds,ncname,si=si,ei=ei)
    data = data*12.01*1800/1E6
    data = numpy.ma.filled(data,float(-9999))
    return data,flag

def smap_donetshortwave(ds,smap_label,si,ei):
    ts = int(ds.globalattributes["time_step"])
    # do the net shortwave radiation
    Fsd,Fsd_flag,a = pfp_utils.GetSeriesasMA(ds,"Fsd",si=si,ei=ei)
    Fsu,Fsu_flag,a = pfp_utils.GetSeriesasMA(ds,"Fsu",si=si,ei=ei)
    # get the net shortwave radiation and convert to MJ/m2/day at the same time
    Fnsw = ((Fsd - Fsu)*ts*60)/1E6
    # now get the QC flag
    Fnsw_flag = Fsd_flag+Fsu_flag
    Fnsw = numpy.ma.filled(Fnsw,float(-9999))
    return Fnsw,Fnsw_flag

def smap_dopressure(ds,smap_label,si,ei):
    ps,ps_flag,attr = pfp_utils.GetSeriesasMA(ds,"ps",si=si,ei=ei)
    ps = ps/float(1000)
    ps = numpy.ma.filled(ps,float(-9999))
    return ps,ps_flag

def smap_doshortwave(ds,smap_label,si,ei):
    ts = int(ds.globalattributes["time_step"])
    Fsd,Fsd_flag,a = pfp_utils.GetSeriesasMA(ds,"Fsd",si=si,ei=ei)
    Fsd = (Fsd*ts*60)/1E6
    Fsd = numpy.ma.filled(Fsd,float(-9999))
    return Fsd,Fsd_flag

def smap_parseformat(fmt):
    if "." in fmt:
        numdec = len(fmt) - (fmt.index(".") + 1)
        strfmt = "{0:."+str(numdec)+"f}"
    else:
        strfmt = "{0:d}"
    return strfmt

def smap_qclabel(smap_label):
    if "_f" in smap_label:
        smap_qc_label=smap_label.replace("_f","_qc")
    else:
        smap_qc_label=smap_label+"_qc"
    return smap_qc_label

def smap_updatedatadictionary(cfvars,data_dict,data,flag,smap_label,nperday,ndays):
    data_dict[smap_label] = {}
    if cfvars[smap_label]["daily"].lower()=="sum":
        data_dict[smap_label]["data"] = numpy.ma.sum(numpy.ma.reshape(data,[ndays,nperday]),axis=1)
    elif cfvars[smap_label]["daily"].lower()=="average":
        data_dict[smap_label]["data"] = numpy.ma.average(numpy.ma.reshape(data,[ndays,nperday]),axis=1)
    elif cfvars[smap_label]["daily"].lower()=="skip":
        data_dict[smap_label]["data"] = numpy.reshape(data,[ndays,nperday])[:,0]
    else:
        msg = "smap_updatedatadictionary: unrecognised option for daily ("+str(cfvars[smap_label]["daily"])+")"
        logger.warning(msg)
    data_dict[smap_label]["fmt"] = cfvars[smap_label]["format"]
    if cfvars[smap_label]["genqc"]=="True":
        smap_qc_label = smap_qclabel(smap_label)
        data_dict[smap_qc_label] = {}
        index_0 = numpy.where(flag==0)[0]
        index_not0 = numpy.where(flag>0)[0]
        flag[index_0] = numpy.int32(1)
        flag[index_not0] = numpy.int32(0)
        data_dict[smap_qc_label]["data"] = numpy.ma.sum(numpy.ma.reshape(flag,[ndays,nperday]),axis=1)/float(nperday)
        data_dict[smap_qc_label]["fmt"] = "0.00"

def smap_write_csv(cf):
    cfvars = cf["Variables"]
    smap_list = cfvars.keys()
    ncFileName = get_infilenamefromcf(cf)
    csvFileName_base = get_outfilenamefromcf(cf)
    # read the netCDF file
    ds = nc_read_series(ncFileName)
    ts = int(ds.globalattributes["time_step"])
    nRecs = int(ds.globalattributes["nc_nrecs"])
    nperhr = int(float(60)/ts+0.5)
    nperday = int(float(24)*nperhr+0.5)
    dt = ds.series["DateTime"]["Data"]
    # get a list of years in the data file
    year_list = range(dt[0].year,dt[-1].year+1)
    years = numpy.array([item.year for item in dt])
    # loop over years in the data file
    data_dict = OrderedDict()
    for year in year_list:
        csvFileName = csvFileName_base+"_"+str(year)+"_SMAP.csv"
        # open the csv file
        csvfile = open(csvFileName,'wb')
        # write the header lines
        writer = smap_writeheaders(cf,csvfile)
        # get the start and end datetime
        year_index = numpy.where(years==year)[0]
        # add the last record from this year
        year_index = numpy.append(year_index,year_index[-1]+1)
        sdate = dt[max([0,year_index[0]])]
        edate = dt[min([year_index[-1],nRecs-1])]
        si = pfp_utils.GetDateIndex(dt,str(sdate),ts=ts,default=0,match="startnextday")
        ei = pfp_utils.GetDateIndex(dt,str(edate),ts=ts,default=nRecs-1,match="endpreviousday")
        data_dict["DateTime"] = dt[si:ei+1]
        logger.info(" Writing "+str(data_dict["DateTime"][0])+" to "+ str(data_dict["DateTime"][-1]))
        ndays = len(data_dict["DateTime"])/nperday
        # put the month, day and DOY into the data dictionary
        smap_datetodatadictionary(ds,data_dict,nperday,ndays,si,ei)
        # first column in SMAP csv file will be the SMAP ID number
        smap_id = numpy.array([cf["General"]["SMAP_ID"]]*ndays)
        # loop over the data required, massage units if necessary and put the data into a dictionary for later use
        smap_list = ["Rn_f","Rs_f","PAR_f","Ta","VPD","Ts_f","PREC","SWC","NEE","GPP","Reco","PRESS","SNOWD"]
        for smap_label in smap_list:
            if smap_label in ["Mo","Day","DOY"]: continue
            if smap_label=="Rn_f":
                data,flag = smap_donetshortwave(ds,smap_label,si,ei)
            elif smap_label=="Rs_f":
                data,flag = smap_doshortwave(ds,smap_label,si,ei)
            elif smap_label=="PAR_f" or smap_label=="SNOWD":
                data = numpy.array([-9999]*len(data_dict["DateTime"]))
                flag = numpy.array([1]*len(data_dict["DateTime"]))
                cfvars[smap_label]["daily"] = "skip"
            elif smap_label=="PRESS":
                data,flag = smap_dopressure(ds,smap_label,si,ei)
            elif smap_label in ["GPP","NEE","Reco"]:
                data,flag = smap_docarbonfluxes(cf,ds,smap_label,si,ei)
            else:
                data,flag,attr = pfp_utils.GetSeries(ds,cfvars[smap_label]["ncname"],si=si,ei=ei)
            smap_updatedatadictionary(cfvars,data_dict,data,flag,smap_label,nperday,ndays)
        # now loop over the days and write the data out
        for i in range(ndays):
            data_list = []
            data_list.append(smap_id[i])
            for smap_label in data_dict.keys():
                if smap_label=="DateTime": continue
                strfmt = smap_parseformat(data_dict[smap_label]["fmt"])
                if "d" in strfmt:
                    data_list.append(strfmt.format(int(round(data_dict[smap_label]["data"][i]))))
                else:
                    data_list.append(strfmt.format(data_dict[smap_label]["data"][i]))
            writer.writerow(data_list)
        csvfile.close()

def smap_writeheaders(cf,csvfile):
    writer = csv.writer(csvfile)
    # write the header lines to the csv file
    series_list = cf["Variables"].keys()
    for item in cf["General"]:
        if item in ["SMAP_ID"]: continue
        writer.writerow([item,str(cf['General'][item])])
    # write the units and variable name header lines to the csv file
    units_list = ["-","-","-","-"]
    row_list = ['ID','Mo','Day','DOY']
    for smap_label in series_list:
        row_list.append(smap_label)
        units_list.append(cf["Variables"][smap_label]["units"])
        if cf["Variables"][smap_label]["genqc"]=="True":
            smap_qc_label = smap_qclabel(smap_label)
            row_list.append(smap_qc_label)
            units_list.append("-")
    writer.writerow(units_list)
    writer.writerow(row_list)
    return writer

def write_csv_ecostress(cf):
    """
    Purpose:
     Write the data structure to an ECOSTRESS CSV file.
    Usage:
    Side effects:
    Author: PRI
    Date: September 2018
    """
    # get the file names
    file_path = pfp_utils.get_keyvaluefromcf(cf, ["Files"], "file_path", default="")
    if not os.path.isdir(file_path):
        msg = " Specified file path "+file_path+" doesn't exist ..."
        logger.error(msg)
        return 1
    in_filename = pfp_utils.get_keyvaluefromcf(cf, ["Files"], "in_filename", default="")
    nc_file_name = os.path.join(file_path, in_filename)
    if not os.path.exists(nc_file_name):
        msg = " Specified input file "+nc_file_name+" not found ..."
        logger.error(msg)
        return 1
    out_filename = pfp_utils.get_keyvaluefromcf(cf, ["Files"], "out_filename", default="")
    if len(out_filename) == 0:
        csv_file_name = nc_file_name.replace(".nc", "_ECOSTRESS.csv")
    else:
        csv_file_name = os.path.join(file_path, out_filename)
    # open the csv file
    csv_file = open(csv_file_name, 'wb')
    csv_writer = csv.writer(csv_file)
    # read the netCDF file
    ds = nc_read_series(nc_file_name)
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    ts = int(ds.globalattributes["time_step"])
    ts_delta = datetime.timedelta(minutes=ts)
    # get the datetime series
    dt = ds.series["DateTime"]["Data"]
    # get the data
    data = {}
    series_list = cf["Variables"].keys()
    for series in series_list:
        ncname = cf["Variables"][series]["in_name"]
        data[series] = pfp_utils.GetVariable(ds, ncname)
        fmt = cf["Variables"][series]["out_format"]
        if "E" in fmt or "e" in fmt:
            numdec = (fmt.index("E")) - (fmt.index(".")) - 1
            strfmt = "{:."+str(numdec)+"e}"
        elif "." in fmt:
            numdec = len(fmt) - (fmt.index(".") + 1)
            strfmt = "{0:."+str(numdec)+"f}"
        else:
            strfmt = "{0:d}"
        data[series]["Attr"]["fmt"] = strfmt
    # adjust units as required
    # GPP
    data["GPP"]["Data"] = pfp_mf.Fc_gCpm2psfromumolpm2ps(data["GPP"]["Data"])
    data["GPP"]["Attr"]["units"] = "gC/m2/s"
    # SWC
    data["SWC"]["Attr"]["units"] = "m3/m3"
    # add the QC flags for Fh, Fe, Fg, GPP, Ta, T2, VPD, Fn
    # for Fh, Fe, Fg, Fn, Ta, T2 and VPD QC flag is:
    #  a) 0 for observation
    #  b) 1 for gap filled high quality
    #  c) 2 for gap filled medium quality
    #  d) 3 for gap filled low quality
    for series in ["LHF", "SHF", "GHF", "GPP", "Ta", "T2", "VPD", "Rn"]:
        qc_label = series + "_qc"
        series_list.insert(series_list.index(series)+1, qc_label)
        data[qc_label] = {}
        data[qc_label]["Data"] = numpy.where(data[series]["Flag"] == 0, zeros, ones)
        data[qc_label]["Attr"] = {}
        data[qc_label]["Attr"]["fmt"] = "{0:d}"
        data[qc_label]["Attr"]["units"] = "-"
    # write the metadata to the CSV file
    if "General" in cf:
        for item in cf["General"]:
            csv_writer.writerow([item,str(cf['General'][item])])
        csv_writer.writerow("")
    # write the units row
    row_list = ["YYYYMMDDhhmm", "YYYYMMDDhhmm"]
    for item in series_list:
        row_list.append(data[item]["Attr"]["units"])
    csv_writer.writerow(row_list)
    # write the variable names to the csv file
    row_list = ["TIME_START", "TIME_END"]
    for item in series_list:
        row_list.append(item)
    csv_writer.writerow(row_list)
    # now write the data
    for i in range(len(dt)):
        # get the timestamp at the start and end of the period
        timestamp_end = dt[i].strftime("%Y%m%d%H%M")
        timestamp_start = (dt[i] - datetime.timedelta(minutes=ts)).strftime("%Y%m%d%H%M")
        data_list = [timestamp_start, timestamp_end]
        for series in series_list:
            # convert from masked array to ndarray with -9999 for missing data
            data[series]["Data"] = numpy.ma.filled(data[series]["Data"], fill_value=float(-9999))
            strfmt = data[series]["Attr"]["fmt"]
            if "d" in strfmt:
                data_list.append(strfmt.format(int(round(data[series]["Data"][i]))))
            else:
                data_list.append(strfmt.format(data[series]["Data"][i]))
        csv_writer.writerow(data_list)
    # close the csv file
    csv_file.close()
    return 0

def xl2nc(cf,InLevel):
    # get the data series from the Excel file
    in_filename = get_infilenamefromcf(cf)
    if not pfp_utils.file_exists(in_filename,mode="quiet"):
        msg = " Input file "+in_filename+" not found ..."
        logger.error(msg)
        return 0
    file_name,file_extension = os.path.splitext(in_filename)
    if "csv" in file_extension.lower():
        ds = csv_read_series(cf)
        if ds==0: return 0
        # get a series of Excel datetime from the Python datetime objects
        pfp_utils.get_xldatefromdatetime(ds)
    else:
        ds = xl_read_series(cf)
        if ds==0: return 0
        # get a series of Python datetime objects from the Excel datetime
        pfp_utils.get_datetimefromxldate(ds)
    # get the netCDF attributes from the control file
    pfp_ts.do_attributes(cf,ds)
    # round the Python datetime to the nearest second
    pfp_utils.round_datetime(ds,mode="nearest_second")
    #check for gaps in the Python datetime series and fix if present
    fixtimestepmethod = pfp_utils.get_keyvaluefromcf(cf,["options"],"FixTimeStepMethod",default="round")
    if pfp_utils.CheckTimeStep(ds): pfp_utils.FixTimeStep(ds,fixtimestepmethod=fixtimestepmethod)
    # recalculate the Excel datetime
    pfp_utils.get_xldatefromdatetime(ds)
    # get the Year, Month, Day etc from the Python datetime
    pfp_utils.get_ymdhmsfromdatetime(ds)
    # write the processing level to a global attribute
    ds.globalattributes['nc_level'] = str(InLevel)
    # get the start and end date from the datetime series unless they were
    # given in the control file
    if 'start_date' not in ds.globalattributes.keys():
        ds.globalattributes['start_date'] = str(ds.series['DateTime']['Data'][0])
    if 'end_date' not in ds.globalattributes.keys():
        ds.globalattributes['end_date'] = str(ds.series['DateTime']['Data'][-1])
    # calculate variances from standard deviations and vice versa
    pfp_ts.CalculateStandardDeviations(cf,ds)
    # create new variables using user defined functions
    pfp_ts.DoFunctions(cf,ds)
    # create a series of synthetic downwelling shortwave radiation
    pfp_ts.get_synthetic_fsd(ds)
    # write the data to the netCDF file
    outfilename = get_outfilenamefromcf(cf)
    ncFile = nc_open_write(outfilename)
    nc_write_series(ncFile,ds)
    return 1

def ep_biomet_write_csv(cf):
    """
    Purpose:
     Write a bionmet file for use with EddyPro.
    Usage:
     pfp_io.ep_biomet_write_csv(cf)
     where:
      cf - a control file object that specifies the input and output file
           names and the variable mapping to use.
    Author: PRI
    Date: August 2016
    """
    # get the file names
    ncFileName = get_infilenamefromcf(cf)
    if not pfp_utils.file_exists(ncFileName,mode="verbose"): return 0
    csvFileName = get_outfilenamefromcf(cf)
    if not pfp_utils.path_exists(os.path.dirname(csvFileName),mode="verbose"): return 0
    # open the csv file
    csvfile = open(csvFileName,'wb')
    writer = csv.writer(csvfile)
    # read the netCDF file
    ds = nc_read_series(ncFileName)
    nrecs = int(ds.globalattributes["nc_nrecs"])
    # get the date and time data
    Day,flag,attr = pfp_utils.GetSeries(ds,'Day')
    Month,flag,attr = pfp_utils.GetSeries(ds,'Month')
    Year,flag,attr = pfp_utils.GetSeries(ds,'Year')
    Hour,flag,attr = pfp_utils.GetSeries(ds,'Hour')
    Minute,flag,attr = pfp_utils.GetSeries(ds,'Minute')
    # get the data
    data = ep_biomet_get_data(cf,ds)
    # check and adjust units if required
    # get a list of the EddyPro series to be output
    ep_series_list = data.keys()
    ep_series_list.sort()
    for ep_series in ep_series_list:
        # loop over the netCDF series names and check they exist in constants.units_synonyms dictionary
        ncname = data[ep_series]["ncname"]
        if ncname not in c.units_synonyms.keys():
            msg = "No entry for "+ncname+" in cfg.units_synonyms, skipping ..."
            logger.warning(msg)
            continue
        if (data[ep_series]["Attr"]["units"] not in c.units_synonyms[ncname] and
            ds.series[ncname]["Attr"]["units"] not in c.units_synonyms[ncname]):
            msg = "Inconsistent units found for series "+ep_series+" and "+ncname
            logger.warning(msg)
    # write the variable names to the csv file
    row_list = ['TIMESTAMP_1']
    for item in ep_series_list:
        row_list.append(item)
    writer.writerow(row_list)
    # write the units line to the csv file
    units_list = ["yyyy-mm-dd HHMM"]
    for item in ep_series_list:
        units_list.append(data[item]["units"])
    writer.writerow(units_list)
    # now write the data
    for i in range(nrecs):
        # get the datetime string
        dtstr = '%d-%02d-%02d %02d%02d'%(Year[i],Month[i],Day[i],Hour[i],Minute[i])
        data_list = [dtstr]
        for ep_series in ep_series_list:
            strfmt = data[ep_series]["fmt"]
            if "d" in strfmt:
                data_list.append(strfmt.format(int(round(data[ep_series]["Data"][i]))))
            else:
                data_list.append(strfmt.format(data[ep_series]["Data"][i]))
        writer.writerow(data_list)
    # close the csv file
    csvfile.close()
    return 1

def ep_biomet_get_data(cf,ds):
    data = {}
    ep_series_list = cf["Variables"].keys()
    for ep_series in ep_series_list:
        ncname = cf["Variables"][ep_series]["ncname"]
        if ncname not in ds.series.keys():
            logger.error("Series "+ncname+" not in netCDF file, skipping ...")
            ep_series_list.remove(ep_series)
            continue
        data[ep_series] = copy.deepcopy(ds.series[ncname])
        data[ep_series]["ncname"] = ncname
        data[ep_series]["units"] = cf["Variables"][ep_series]["units"]
        fmt = cf["Variables"][ep_series]["format"]
        if "." in fmt:
            numdec = len(fmt) - (fmt.index(".") + 1)
            strfmt = "{0:."+str(numdec)+"f}"
        else:
            strfmt = "{0:d}"
        data[ep_series]["fmt"] = strfmt
    return data

def fn_write_csv(cf):
    # get the file names
    ncFileName = get_infilenamefromcf(cf)
    csvFileName = get_outfilenamefromcf(cf)
    # open the csv file
    csvfile = open(csvFileName,'wb')
    writer = csv.writer(csvfile)
    # read the netCDF file
    ds = nc_read_series(ncFileName)
    nRecs = int(ds.globalattributes["nc_nrecs"])
    zeros = numpy.zeros(nRecs,dtype=numpy.int32)
    ones = numpy.ones(nRecs,dtype=numpy.int32)
    # Tumbarumba doesn't have RH in the netCDF files
    if "RH" not in ds.series.keys():
        Ah,f,a = pfp_utils.GetSeriesasMA(ds,'Ah')
        Ta,f,a = pfp_utils.GetSeriesasMA(ds,'Ta')
        RH = pfp_mf.RHfromabsolutehumidity(Ah, Ta)
        attr = pfp_utils.MakeAttributeDictionary(long_name='Relative humidity',units='%',standard_name='relative_humidity')
        flag = numpy.where(numpy.ma.getmaskarray(RH)==True,ones,zeros)
        pfp_utils.CreateSeries(ds,"RH",RH,flag,attr)
    ts = int(ds.globalattributes["time_step"])
    ts_delta = datetime.timedelta(minutes=ts)
    # get the datetime series
    dt = ds.series["DateTime"]["Data"]
    # check the start datetime of the series and adjust if necessary
    start_datetime = dateutil.parser.parse(str(cf["General"]["start_datetime"]))
    if dt[0]<start_datetime:
        # requested start_datetime is after the start of the file
        logger.info(" Truncating start of file")
        si = pfp_utils.GetDateIndex(dt,str(start_datetime),ts=ts,match="exact")
        for thisone in ds.series.keys():
            ds.series[thisone]["Data"] = ds.series[thisone]["Data"][si:]
            ds.series[thisone]["Flag"] = ds.series[thisone]["Flag"][si:]
        ds.globalattributes["nc_nrecs"] = str(len(ds.series["DateTime"]["Data"]))
    elif dt[0]>start_datetime:
        # requested start_datetime is before the start of the file
        logger.info(" Padding start of file")
        dt_patched = [ldt for ldt in pfp_utils.perdelta(start_datetime, dt[0]-ts_delta, ts_delta)]
        data_patched = numpy.ones(len(dt_patched))*float(c.missing_value)
        flag_patched = numpy.ones(len(dt_patched))
        # list of series in the data structure
        series_list = ds.series.keys()
        # ds.series["DateTime"]["Data"] is a list not a numpy array so we must treat it differently
        ds.series["DateTime"]["Data"] = dt_patched+ds.series["DateTime"]["Data"]
        ds.series["DateTime"]["Flag"] = numpy.concatenate((flag_patched,ds.series["DateTime"]["Flag"]))
        series_list.remove("DateTime")
        for thisone in series_list:
            ds.series[thisone]["Data"] = numpy.concatenate((data_patched,ds.series[thisone]["Data"]))
            ds.series[thisone]["Flag"] = numpy.concatenate((flag_patched,ds.series[thisone]["Flag"]))
        ds.globalattributes["nc_nrecs"] = str(len(ds.series["DateTime"]["Data"]))
        # refresh the year, month, day etc arrays now that we have padded the datetime series
        pfp_utils.get_ymdhmsfromdatetime(ds)
    # now check the end datetime of the file
    end_datetime = dateutil.parser.parse(str(cf["General"]["end_datetime"]))
    if dt[-1]>end_datetime:
        # requested end_datetime is before the end of the file
        msg = " Truncating end of file "+dt[-1].strftime("%Y-%m-%d %H:%M")+" "+end_datetime.strftime("%Y-%m-%d %H:%M")
        logger.info(msg)
        ei = pfp_utils.GetDateIndex(dt,str(end_datetime),ts=ts,match="exact")
        for thisone in ds.series.keys():
            ds.series[thisone]["Data"] = ds.series[thisone]["Data"][:ei+1]
            ds.series[thisone]["Flag"] = ds.series[thisone]["Flag"][:ei+1]
        ds.globalattributes["nc_nrecs"] = str(len(ds.series["DateTime"]["Data"]))
    elif dt[-1]<end_datetime:
        # requested end_datetime is before the requested end date
        msg = " Padding end of file "+dt[-1].strftime("%Y-%m-%d %H:%M")+" "+end_datetime.strftime("%Y-%m-%d %H:%M")
        logger.info(msg)
        dt_patched = [ldt for ldt in pfp_utils.perdelta(dt[-1]+ts_delta, end_datetime, ts_delta)]
        data_patched = numpy.ones(len(dt_patched))*float(c.missing_value)
        flag_patched = numpy.ones(len(dt_patched))
        # list of series in the data structure
        series_list = ds.series.keys()
        # ds.series["DateTime"]["Data"] is a list not a numpy array so we must treat it differently
        ds.series["DateTime"]["Data"] = ds.series["DateTime"]["Data"]+dt_patched
        ds.series["DateTime"]["Flag"] = numpy.concatenate((ds.series["DateTime"]["Flag"],flag_patched))
        series_list.remove("DateTime")
        for thisone in series_list:
            ds.series[thisone]["Data"] = numpy.concatenate((ds.series[thisone]["Data"],data_patched))
            ds.series[thisone]["Flag"] = numpy.concatenate((ds.series[thisone]["Flag"],flag_patched))
        ds.globalattributes["nc_nrecs"] = str(len(ds.series["DateTime"]["Data"]))
        # refresh the year, month, day etc arrays now that we have padded the datetime series
        pfp_utils.get_ymdhmsfromdatetime(ds)
    if ts==30:
        nRecs_year = 17520
        nRecs_leapyear = 17568
    elif ts==60:
        nRecs_year = 8760
        nRecs_leapyear = 8784
    else:
        logger.error(" Unrecognised time step ("+str(ts)+")")
        return
    if (int(ds.globalattributes["nc_nrecs"])!=nRecs_year) & (int(ds.globalattributes["nc_nrecs"])!=nRecs_leapyear):
        logger.error(" Number of records in file does not equal "+str(nRecs_year)+" or "+str(nRecs_leapyear))
        msg = str(len(ds.series["DateTime"]["Data"]))+" "+str(ds.series["DateTime"]["Data"][0])
        msg = msg+" "+str(ds.series["DateTime"]["Data"][-1])
        logger.error(msg)
        return
    # get the date and time data
    Day,flag,attr = pfp_utils.GetSeries(ds,'Day')
    Month,flag,attr = pfp_utils.GetSeries(ds,'Month')
    Year,flag,attr = pfp_utils.GetSeries(ds,'Year')
    Hour,flag,attr = pfp_utils.GetSeries(ds,'Hour')
    Minute,flag,attr = pfp_utils.GetSeries(ds,'Minute')
    # get the data
    data = {}
    series_list = cf["Variables"].keys()
    for series in series_list:
        ncname = cf["Variables"][series]["ncname"]
        if ncname not in ds.series.keys():
            logger.error("Series "+ncname+" not in netCDF file, skipping ...")
            series_list.remove(series)
            continue
        data[series] = ds.series[ncname]
        fmt = cf["Variables"][series]["format"]
        if "." in fmt:
            numdec = len(fmt) - (fmt.index(".") + 1)
            strfmt = "{0:."+str(numdec)+"f}"
        else:
            strfmt = "{0:d}"
        data[series]["fmt"] = strfmt
    #adjust units if required
    for series in series_list:
        if series=="FC" and data[series]["Attr"]["units"]=='mg/m2/s':
            data[series]["Data"] = pfp_mf.Fc_umolpm2psfrommgCO2pm2ps(data[series]["Data"])
            data[series]["Attr"]["units"] = "umol/m2/s"
        if series=="CO2" and data[series]["Attr"]["units"]=='mg/m3':
            CO2 = data["CO2"]["Data"]
            TA = data["TA"]["Data"]
            PA = data["PA"]["Data"]
            data[series]["Data"] = pfp_mf.co2_ppmfrommgCO2pm3(CO2,TA,PA)
            data[series]["Attr"]["units"] = "umol/mol"
        if series=="H2O" and data[series]["Attr"]["units"]=='g/m3':
            H2O = data["H2O"]["Data"]
            TA = data["TA"]["Data"]
            PA = data["PA"]["Data"]
            data[series]["Data"] = pfp_mf.h2o_mmolpmolfromgpm3(H2O,TA,PA)
            data[series]["Attr"]["units"] = "mmol/mol"
        if series=="RH" and data[series]["Attr"]["units"] in ["fraction","frac"]:
            data[series]["Data"] = float(100)*data[series]["Data"]
            data[series]["Attr"]["units"] = "%"
    # write the general information to csv file
    for item in cf["General"]:
        writer.writerow([item,str(cf['General'][item])])
    # write the variable names to the csv file
    row_list = ['DateTime','Year','Month','Day','HHMM']
    for item in series_list:
        row_list.append(item)
    writer.writerow(row_list)
    # write the units line to the csv file
    units_list = ["-","-","-","-","-"]
    for item in series_list:
        units_list.append(data[item]["Attr"]["units"])
    writer.writerow(units_list)
    # now write the data
    for i in range(len(Year)):
        # get the datetime string
        dtstr = '%02d/%02d/%d %02d:%02d'%(Day[i],Month[i],Year[i],Hour[i],Minute[i])
        hrmn = '%02d%02d'%(Hour[i],Minute[i])
        dttup = datetime.datetime(Year[i],Month[i],Day[i],Hour[i],Minute[i]).timetuple()
        doy = float(dttup.tm_yday) + float(dttup.tm_hour)/24 + float(dttup.tm_min)/1440
        data_list = [dtstr,'%d'%(Year[i]),'%02d'%(Month[i]),'%02d'%(Day[i]),hrmn]
        for series in series_list:
            strfmt = data[series]["fmt"]
            if "d" in strfmt:
                data_list.append(strfmt.format(int(round(data[series]["Data"][i]))))
            else:
                data_list.append(strfmt.format(data[series]["Data"][i]))
        writer.writerow(data_list)
    # close the csv file
    csvfile.close()
    return

def get_controlfilecontents(ControlFileName,mode="verbose"):
    if mode!="quiet": logger.info(' Processing the control file ')
    if len(ControlFileName)!=0:
        cf = ConfigObj(ControlFileName)
        cf['controlfile_name'] = ControlFileName
    else:
        cf = ConfigObj()
    if "Files" in cf:
        if "plot_path" not in cf["Files"].keys():
            cf["Files"]["plot_path"] = "plots/"
    return cf

def get_ncdtype(Series):
    sd = Series.dtype.name
    dt = 'f'
    if sd=='float64': dt = 'd'
    if sd=='int32': dt = 'i'
    if sd=='int64': dt = 'l'
    return dt

def get_filename_dialog(file_path='.', title='Choose a file', ext="*.*"):
    """
    Purpose:
     Put up a file open dialog and let the user browse to open a file
    Usage:
     fname = pfp_io.get_filename_dialog(path=<path_to_file>,title=<tile>)
     where path  - the path to the file location, optional
           title - the title for the file open dialog, optional
    Returns:
     fname - the full file name including path, string
    Author: PRI
    Date: Back in the day
    """
    file_name = QtGui.QFileDialog.getOpenFileName(caption=title, directory=file_path, filter=ext)
    return str(file_name)

def get_infilenamefromcf(cf):
    path = pfp_utils.get_keyvaluefromcf(cf,["Files"],"file_path",default="")
    path = os.path.join(str(path), "")
    name = pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_filename",default="")
    return str(path)+str(name)

def get_outfilenamefromcf(cf):
    path = pfp_utils.get_keyvaluefromcf(cf,["Files"],"file_path",default="")
    path = os.path.join(str(path), "")
    name = pfp_utils.get_keyvaluefromcf(cf,["Files"],"out_filename",default="")
    return str(path)+str(name)

def get_outputlistfromcf(cf,filetype):
    try:
        outputlist = ast.literal_eval(cf['Output'][filetype])
    except:
        #log.info('get_outputlistfromcf: Unable to get output list from Output section in control file')
        outputlist = None
    return outputlist

def get_seriesstats(cf,ds):
    # open an Excel file for the flag statistics
    level = ds.globalattributes['nc_level']
    out_filename = get_outfilenamefromcf(cf)
    xl_filename = out_filename.replace('.nc','_FlagStats.xls')
    file_name = os.path.split(xl_filename)
    logger.info(' Writing flag stats to '+file_name[1])
    xlFile = xlwt.Workbook()
    xlFlagSheet = xlFile.add_sheet('Flag')
    # get the flag statistics
    #xlRow = 0
    #xlCol = 0
    #xlFlagSheet.write(xlRow,xlCol,'0:')
    #xlFlagSheet.write(xlRow,xlCol+1,ds.globalattributes['Flag00'])
    #xlFlagSheet.write(xlRow,xlCol+2,'1:')
    #xlFlagSheet.write(xlRow,xlCol+3,ds.globalattributes['Flag01'])
    #xlFlagSheet.write(xlRow,xlCol+4,'2:')
    #xlFlagSheet.write(xlRow,xlCol+5,ds.globalattributes['Flag02'])
    #xlFlagSheet.write(xlRow,xlCol+6,'3:')
    #xlFlagSheet.write(xlRow,xlCol+7,ds.globalattributes['Flag03'])
    #xlFlagSheet.write(xlRow,xlCol+8,'4:')
    #xlFlagSheet.write(xlRow,xlCol+9,ds.globalattributes['Flag04'])
    #xlFlagSheet.write(xlRow,xlCol+10,'5:')
    #xlFlagSheet.write(xlRow,xlCol+11,ds.globalattributes['Flag05'])
    #xlFlagSheet.write(xlRow,xlCol+12,'6:')
    #xlFlagSheet.write(xlRow,xlCol+13,ds.globalattributes['Flag06'])
    #xlFlagSheet.write(xlRow,xlCol+14,'7:')
    #xlFlagSheet.write(xlRow,xlCol+15,ds.globalattributes['Flag07'])
    #xlRow = xlRow + 1
    #xlFlagSheet.write(xlRow,xlCol,'10:')
    #xlFlagSheet.write(xlRow,xlCol+1,ds.globalattributes['Flag10'])
    #xlFlagSheet.write(xlRow,xlCol+2,'11:')
    #xlFlagSheet.write(xlRow,xlCol+3,ds.globalattributes['Flag11'])
    #xlFlagSheet.write(xlRow,xlCol+4,'12:')
    #xlFlagSheet.write(xlRow,xlCol+5,ds.globalattributes['Flag12'])
    #xlFlagSheet.write(xlRow,xlCol+6,'13:')
    #xlFlagSheet.write(xlRow,xlCol+7,ds.globalattributes['Flag13'])
    #xlFlagSheet.write(xlRow,xlCol+8,'14:')
    #xlFlagSheet.write(xlRow,xlCol+9,ds.globalattributes['Flag14'])
    #xlFlagSheet.write(xlRow,xlCol+10,'15:')
    #xlFlagSheet.write(xlRow,xlCol+11,ds.globalattributes['Flag15'])
    #xlFlagSheet.write(xlRow,xlCol+12,'16:')
    #xlFlagSheet.write(xlRow,xlCol+13,ds.globalattributes['Flag16'])
    #xlFlagSheet.write(xlRow,xlCol+14,'17:')
    #xlFlagSheet.write(xlRow,xlCol+15,ds.globalattributes['Flag17'])
    #xlFlagSheet.write(xlRow,xlCol+16,'18:')
    #xlFlagSheet.write(xlRow,xlCol+17,ds.globalattributes['Flag18'])
    #xlFlagSheet.write(xlRow,xlCol+18,'19:')
    #xlFlagSheet.write(xlRow,xlCol+19,ds.globalattributes['Flag19'])
    #xlRow = xlRow + 1
    #xlFlagSheet.write(xlRow,xlCol,'30:')
    #xlFlagSheet.write(xlRow,xlCol+1,ds.globalattributes['Flag30'])
    #xlFlagSheet.write(xlRow,xlCol+2,'31:')
    #xlFlagSheet.write(xlRow,xlCol+3,ds.globalattributes['Flag31'])
    #xlFlagSheet.write(xlRow,xlCol+4,'32:')
    #xlFlagSheet.write(xlRow,xlCol+5,ds.globalattributes['Flag32'])
    #xlFlagSheet.write(xlRow,xlCol+6,'33:')
    #xlFlagSheet.write(xlRow,xlCol+7,ds.globalattributes['Flag33'])
    #xlFlagSheet.write(xlRow,xlCol+8,'34:')
    #xlFlagSheet.write(xlRow,xlCol+9,ds.globalattributes['Flag34'])
    #xlFlagSheet.write(xlRow,xlCol+10,'35:')
    #xlFlagSheet.write(xlRow,xlCol+11,ds.globalattributes['Flag35'])
    #xlFlagSheet.write(xlRow,xlCol+12,'36:')
    #xlFlagSheet.write(xlRow,xlCol+13,ds.globalattributes['Flag36'])
    #xlFlagSheet.write(xlRow,xlCol+14,'37:')
    #xlFlagSheet.write(xlRow,xlCol+15,ds.globalattributes['Flag37'])
    #xlFlagSheet.write(xlRow,xlCol+16,'38:')
    #xlFlagSheet.write(xlRow,xlCol+17,ds.globalattributes['Flag38'])
    #xlFlagSheet.write(xlRow,xlCol+18,'39:')
    #xlFlagSheet.write(xlRow,xlCol+19,ds.globalattributes['Flag39'])
    bins = numpy.arange(-0.5,23.5)
    xlRow = 5
    xlCol = 1
    for Value in bins[:len(bins)-1]:
        xlFlagSheet.write(xlRow,xlCol,int(Value+0.5))
        xlCol = xlCol + 1
    xlRow = xlRow + 1
    xlCol = 0
    dsVarNames = ds.series.keys()
    dsVarNames.sort(key=unicode.lower)
    for ThisOne in dsVarNames:
        data,flag,attr = pfp_utils.GetSeries(ds, ThisOne)
        hist, bin_edges = numpy.histogram(flag, bins=bins)
        xlFlagSheet.write(xlRow,xlCol,ThisOne)
        xlCol = xlCol + 1
        for Value in hist:
            xlFlagSheet.write(xlRow,xlCol,float(Value))
            xlCol = xlCol + 1
        xlCol = 0
        xlRow = xlRow + 1
    xlFile.save(xl_filename)

def load_controlfile(path='.', title='Choose a control file'):
    """
    Purpose:
     Returns a control file object.
    Usage:
     cf = pfp_io.load_controlfile([path=<some_path_to_a_controlfile>],[title=<some title>])
          where path [optional] is the path to a subdirectory
                title [optional] is a title for the file open dialog
                cf is a control file object
    Author: PRI
    Date: Back in the day
    """
    name = get_filename_dialog(file_path=path, title=title, ext="*.*")
    cf = get_controlfilecontents(name)
    return cf

def nc_concatenate(cf):
    # initialise logicals
    TimeGap = False
    # get an instance of the data structure
    ds = DataStructure()
    # get the input file list
    InFile_list = cf['Files']['In'].keys()
    # read in the first file
    baseFileName = cf['Files']['In'][InFile_list[0]]
    logger.info(' Reading data from '+os.path.split(baseFileName)[1])
    fixtimestepmethod = pfp_utils.get_keyvaluefromcf(cf,["Options"],"FixTimeStepMethod",default="round")
    ds_n = nc_read_series(baseFileName,fixtimestepmethod=fixtimestepmethod)
    if len(ds_n.series.keys())==0:
        logger.error(' An error occurred reading netCDF file: '+baseFileName)
        return
    # fill the global attributes
    for ThisOne in ds_n.globalattributes.keys():
        ds.globalattributes[ThisOne] = ds_n.globalattributes[ThisOne]
    # find the first datetime in the file where more than 50% of the variables are present.
    dt = ds_n.series["DateTime"]["Data"]
    cond_idx = numpy.zeros(len(dt))
    series_list = ds_n.series.keys()
    # remove non-data series
    for item in ["DateTime","DateTime_UTC","xlDateTime",
                 "Year","Month","Day","Hour","Minute","Second",
                 "Hdh","Ddd","time"]:
        if item in series_list: series_list.remove(item)

    # loop over the data series and calculate fraction of data present
    opt = pfp_utils.get_keyvaluefromcf(cf,["Options"],"Truncate",default="Yes")
    if opt.lower() == "yes":
        default_string = "Ah,CO2,Fa,Fg,Fld,Flu,Fn,Fsd,Fsu,ps,Sws,Ta,Ts,Ws,Wd,Precip"
        series_string = pfp_utils.get_keyvaluefromcf(cf,["Options"],"SeriesToCheck",default=default_string)
        series_list = pfp_cfg.cfg_string_to_list(series_string)
        for item in series_list:
            data,flag,attr = pfp_utils.GetSeriesasMA(ds_n,item)
            idx = numpy.ma.where(data.mask==False)
            cond_idx[idx] = cond_idx[idx] + 1
        cond_idx = cond_idx/len(series_list)
        # find the first element where more than 50% data is present
        opt = pfp_utils.get_keyvaluefromcf(cf,["Options"],"TruncateThreshold",default="50")
        threshold = float(opt)/float(100)
        idx = numpy.where(cond_idx>=threshold)[0]
        # skip if enough data is present from the start of the file
        if len(idx)!=0 and idx[0]!=0:
            si = idx[0]
            msg = " Start date truncated from "+str(dt[0])
            msg = msg+" to "+str(dt[si])
            logger.warning(msg)
            # update the relevent global attributes
            ds_n.globalattributes["start_date"] = dt[si]
            ds_n.globalattributes["nc_nrecs"] = len(dt[si:])
            # now loop over the data series and truncate
            series_list = ds_n.series.keys()
            for item in series_list:
                ds_n.series[item]["Data"] = ds_n.series[item]["Data"][si:]
                ds_n.series[item]["Flag"] = ds_n.series[item]["Flag"][si:]

    # check that we have 'Ws' and 'Wd' series
    if "Ws" not in ds_n.series.keys():
        if "Ws_CSAT" in ds_n.series.keys():
            msg = " Ws not found, copying series Ws_CSAT to Ws"
            logger.info(msg)
            ds_n.series["Ws"] = ds_n.series["Ws_CSAT"].copy()
        else:
            msg = "Both Ws and Ws_CSAT missing from file"
            logger.warning(msg)
    if "Wd" not in ds_n.series.keys():
        if "Wd_CSAT" in ds_n.series.keys():
            msg = " Wd not found, copying series Wd_CSAT to Wd"
            logger.info(msg)
            ds_n.series["Wd"] = ds_n.series["Wd_CSAT"].copy()
        else:
            msg = "Both Wd and Wd_CSAT missing from file"
            logger.warning(msg)
    # fill the variables
    for ThisOne in ds_n.series.keys():
        ds.series[ThisOne] = {}
        ds.series[ThisOne]['Data'] = ds_n.series[ThisOne]['Data']
        ds.series[ThisOne]['Flag'] = ds_n.series[ThisOne]['Flag']
        ds.series[ThisOne]['Attr'] = {}
        for attr in ds_n.series[ThisOne]['Attr'].keys():
            ds.series[ThisOne]['Attr'][attr] = ds_n.series[ThisOne]['Attr'][attr]
    ts = int(ds.globalattributes['time_step'])
    # loop over the remaining files given in the control file
    for n in InFile_list[1:]:
        ncFileName = cf['Files']['In'][InFile_list[int(n)]]
        nc_file_name = os.path.split(ncFileName)
        logger.info(' Reading data from '+nc_file_name[1])
        ds_n = nc_read_series(ncFileName,fixtimestepmethod=fixtimestepmethod)
        if len(ds.series.keys())==0:
            logger.error(' An error occurred reading the netCDF file: '+nc_file_name[1])
            return
        dt_n = ds_n.series['DateTime']['Data']
        dt = ds.series['DateTime']['Data']
        nRecs_n = len(ds_n.series["DateTime"]["Data"])
        nRecs = len(ds.series["DateTime"]["Data"])
        # check that we have 'Ws' and 'Wd' series
        if "Ws" not in ds_n.series.keys():
            if "Ws_CSAT" in ds_n.series.keys():
                msg = " Ws not found, copying series Ws_CSAT to Ws"
                logger.info(msg)
                ds_n.series["Ws"] = ds_n.series["Ws_CSAT"].copy()
            else:
                msg = " Both Ws and Ws_CSAT missing from file"
                logger.warning(msg)
        if "Wd" not in ds_n.series.keys():
            if "Wd_CSAT" in ds_n.series.keys():
                msg = " Wd not found, copying series Wd_CSAT to Wd"
                logger.info(msg)
                ds_n.series["Wd"] = ds_n.series["Wd_CSAT"].copy()
            else:
                msg = " Both Wd and Wd_CSAT missing from file"
                logger.warning(msg)
        if dt_n[0]<dt[-1]+datetime.timedelta(minutes=ts):
            logger.info(' Overlapping times detected in consecutive files')
            si = pfp_utils.GetDateIndex(dt_n,str(dt[-1]),ts=ts)+1
            ei = -1
        if dt_n[0]==dt[-1]+datetime.timedelta(minutes=ts):
            logger.info(' Start and end times OK in consecutive files')
            si = 0; ei = -1
        if dt_n[0]>dt[-1]+datetime.timedelta(minutes=ts):
            logger.info(' Gap between start and end times in consecutive files')
            si = 0; ei = -1
            #TimeGap = True
        # loop over the data series in the concatenated file
        for ThisOne in ds.series.keys():
            # does this series exist in the file being added to the concatenated file
            if ThisOne in ds_n.series.keys():
                # if so, then append this series to the concatenated series
                if type(ds.series[ThisOne]["Data"]) is list:
                    ds.series[ThisOne]['Data'] = ds.series[ThisOne]['Data']+ds_n.series[ThisOne]['Data'][si:]
                else:
                    ds.series[ThisOne]['Data'] = numpy.append(ds.series[ThisOne]['Data'],ds_n.series[ThisOne]['Data'][si:])
                ds.series[ThisOne]['Flag'] = numpy.append(ds.series[ThisOne]['Flag'],ds_n.series[ThisOne]['Flag'][si:])
            else:
                # if not, then create a dummy series and concatenate that
                ds_n.series[ThisOne] = {}
                ds_n.series[ThisOne]['Data'] = numpy.array([c.missing_value]*nRecs_n,dtype=numpy.float64)
                ds_n.series[ThisOne]['Flag'] = numpy.array([1]*nRecs_n,dtype=numpy.int32)
                ds.series[ThisOne]['Data'] = numpy.append(ds.series[ThisOne]['Data'],ds_n.series[ThisOne]['Data'][si:])
                ds.series[ThisOne]['Flag'] = numpy.append(ds.series[ThisOne]['Flag'],ds_n.series[ThisOne]['Flag'][si:])
        # and now loop over the series in the file being concatenated
        for ThisOne in ds_n.series.keys():
            # does this series exist in the concatenated data
            if ThisOne not in ds.series.keys():
                # if not then add it
                ds.series[ThisOne] = {}
                ds.series[ThisOne]['Data'] = numpy.array([c.missing_value]*nRecs,dtype=numpy.float64)
                ds.series[ThisOne]['Flag'] = numpy.array([1]*nRecs,dtype=numpy.int32)
                ds.series[ThisOne]['Data'] = numpy.append(ds.series[ThisOne]['Data'],ds_n.series[ThisOne]['Data'][si:])
                ds.series[ThisOne]['Flag'] = numpy.append(ds.series[ThisOne]['Flag'],ds_n.series[ThisOne]['Flag'][si:])
                ds.series[ThisOne]['Attr'] = {}
                for attr in ds_n.series[ThisOne]['Attr'].keys():
                    ds.series[ThisOne]['Attr'][attr] = ds_n.series[ThisOne]['Attr'][attr]
    # find the last datetime in the file where more than 50% of the variables are present.
    ds.globalattributes["nc_nrecs"] = len(ds.series["DateTime"]["Data"])
    dt = ds.series["DateTime"]["Data"]
    cond_idx = numpy.zeros(len(dt))
    #series_list = ds.series.keys()
    ## remove non-data series
    #for item in ["DateTime","DateTime_UTC","xlDateTime",
                 #"Year","Month","Day","Hour","Minute","Second",
                 #"Hdh","Ddd","time"]:
        #if item in series_list: series_list.remove(item)

    # loop over the data series and calculate fraction of data present
    opt = pfp_utils.get_keyvaluefromcf(cf,["Options"],"Truncate",default="Yes")
    if opt.lower() == "yes":
        default_string = "Ah,CO2,Fa,Fg,Fld,Flu,Fn,Fsd,Fsu,ps,Sws,Ta,Ts,Ws,Wd,Precip"
        series_string = pfp_utils.get_keyvaluefromcf(cf,["Options"],"SeriesToCheck",default=default_string)
        series_list = pfp_cfg.cfg_string_to_list(series_string)
        if isinstance(series_list, basestring):
            series_list = ast.literal_eval(series_list)
        for item in series_list:
            data,flag,attr = pfp_utils.GetSeriesasMA(ds,item)
            idx = numpy.where(numpy.ma.getmaskarray(data)==False)
            cond_idx[idx] = cond_idx[idx] + 1
        cond_idx = cond_idx/len(series_list)
        # find the last element where more than 50% data is present
        opt = pfp_utils.get_keyvaluefromcf(cf,["Options"],"TruncateThreshold",default="50")
        threshold = float(opt)/float(100)
        idx = numpy.where(cond_idx>=threshold)[0]
        # skip if data is present to the end of the file
        if len(idx)!=0 and idx[-1]!=len(dt)-1:
            ei = idx[-1]
            msg = " End date truncated from "+str(dt[-1])
            msg = msg+" to "+str(dt[ei])
            logger.warning(msg)
            # update the relevent global attributes
            ds.globalattributes["end_date"] = dt[ei]
            # now loop over the data series and truncate
            series_list = ds.series.keys()
            for item in series_list:
                ds.series[item]["Data"] = ds.series[item]["Data"][:ei+1]
                ds.series[item]["Flag"] = ds.series[item]["Flag"][:ei+1]
        # update the number of records
        ds.globalattributes["nc_nrecs"] = len(ds.series["DateTime"]["Data"])

    # now sort out any time gaps
    if pfp_utils.CheckTimeStep(ds):
        fixtimestepmethod = pfp_utils.get_keyvaluefromcf(cf,["Options"],"FixTimeStepMethod",default="round")
        pfp_utils.FixTimeStep(ds,fixtimestepmethod=fixtimestepmethod)
        # update the Excel datetime from the Python datetime
        pfp_utils.get_xldatefromdatetime(ds)
        # update the Year, Month, Day etc from the Python datetime
        pfp_utils.get_ymdhmsfromdatetime(ds)
    # if requested, fill any small gaps by interpolation
    # get a list of series in ds excluding the QC flags
    series_list = [item for item in ds.series.keys() if "_QCFlag" not in item]
    # remove the datetime variables, these will have no gaps
    datetime_list = ["xlDateTime","DateTime","Year","Month","Day","Hour","Minute","Second","Hdh","Ddd"]
    for item in datetime_list:
        if item in series_list: series_list.remove(item)
    # loop over the non-datetime data series in ds and interpolate
    # get the maximum gap length (in hours) from the control file
    maxlen = int(pfp_utils.get_keyvaluefromcf(cf,["Options"],"MaxGapInterpolate",default=2))
    if maxlen!=0:
        # now loop over the series and do the interpolation
        logger.info(" Interpolating over fixed time gaps ("+str(maxlen)+" hour max)")
        for item in series_list:
            pfp_ts.InterpolateOverMissing(ds,series=item,maxlen=maxlen)
    # make sure we have all of the humidities
    pfp_ts.CalculateHumidities(ds)
    # and make sure we have all of the meteorological variables
    pfp_ts.CalculateMeteorologicalVariables(ds)
    # check units of Fc and convert if necessary
    Fc_list = [label for label in ds.series.keys() if label[0:2] == "Fc" and "Flag" not in label]
    pfp_utils.CheckUnits(ds, Fc_list, "umol/m2/s", convert_units=True)
    # re-calculate the synthetic Fsd
    pfp_ts.get_synthetic_fsd(ds)
    # re-apply the quality control checks (range, diurnal and rules)
    pfp_ck.do_qcchecks(cf,ds)
    # update the global attributes for this level
    if "nc_level" in ds.globalattributes.keys():
        level = ds.globalattributes["nc_level"]
    else:
        level = "unknown"
    pfp_utils.UpdateGlobalAttributes(cf,ds,level)
    # check missing data and QC flags are consistent
    pfp_utils.CheckQCFlags(ds)
    # update the coverage statistics
    pfp_utils.get_coverage_individual(ds)
    pfp_utils.get_coverage_groups(ds)
    # write the netCDF file
    outFileName = pfp_utils.get_keyvaluefromcf(cf,["Files","Out"],"ncFileName",default="out.nc")
    logger.info(' Writing data to '+os.path.split(outFileName)[1])
    # check to see if the base and concatenated file names are the same
    # IE the user wants to overwrite the base file
    if outFileName==baseFileName:
        # ... but we will save them from themselves!
        t = time.localtime()
        rundatetime = datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]).strftime("%Y%m%d%H%M")
        new_ext = "_"+rundatetime+".nc"
        # add the current local datetime the base file name
        newFileName = baseFileName.replace(".nc",new_ext)
        msg = " Renaming "+baseFileName+" to "+newFileName
        logger.info(msg)
        # ... and rename the base file to preserve it
        os.rename(baseFileName,newFileName)
        # now the base file will not be overwritten
    ncFile = nc_open_write(outFileName)
    ndims = int(pfp_utils.get_keyvaluefromcf(cf,["Options"],"NumberOfDimensions", default=3))
    nc_write_series(ncFile,ds,ndims=ndims)

def nc_split():
    split_info = {}
    split_gui = Tkinter.Toplevel()
    split_gui.wm_title("Split netCDF file")
    split_gui.grid()
    # first row contains the input file name selection
    nrow = 0
    split_gui.infilenameLabel = Tkinter.Label(split_gui,text="Input file")
    split_gui.infilenameLabel.grid(row=nrow,column=0,columnspan=1)
    split_gui.infilename = Tkinter.StringVar()
    split_gui.infilename.set("")
    split_gui.infilenameEntry = Tkinter.Entry(split_gui,textvariable=split_gui.infilename,width=30)
    split_gui.infilenameEntry.grid(row=nrow,column=1)
    split_gui.infilenameBrowse = Tkinter.Button(split_gui,text="Browse",command=lambda:ncsplit_infilename_browse(split_gui))
    split_gui.infilenameBrowse.grid(row=nrow,column=2)
    # second row has the start date entry
    nrow = nrow + 1
    split_gui.startLabel = Tkinter.Label(split_gui, text="Start date (YYYY-MM-DD)")
    split_gui.startLabel.grid(row=nrow,column=0,columnspan=1)
    split_gui.startEntry = Tkinter.Entry(split_gui)
    split_gui.startEntry.grid(row=nrow,column=1,columnspan=1)
    # third row has the end date entry
    nrow = nrow + 1
    split_gui.endLabel = Tkinter.Label(split_gui, text="End date   (YYYY-MM-DD)")
    split_gui.endLabel.grid(row=nrow,column=0,columnspan=1)
    split_gui.endEntry = Tkinter.Entry(split_gui)
    split_gui.endEntry.grid(row=nrow,column=1,columnspan=1)
    # fourth row contains the output file name selection
    nrow = nrow + 1
    split_gui.outfilenameLabel = Tkinter.Label(split_gui,text="Output file")
    split_gui.outfilenameLabel.grid(row=nrow,column=0,columnspan=1)
    split_gui.outfilename = Tkinter.StringVar()
    split_gui.outfilename.set("")
    split_gui.outfilenameEntry = Tkinter.Entry(split_gui,textvariable=split_gui.outfilename,width=30)
    split_gui.outfilenameEntry.grid(row=nrow,column=1)
    split_gui.outfilenameBrowse = Tkinter.Button(split_gui,text="Browse",command=lambda:ncsplit_outfilename_browse(split_gui))
    split_gui.outfilenameBrowse.grid(row=nrow,column=2)
    # action buttons on the bottom row
    nrow = nrow + 1
    split_gui.doneButton = Tkinter.Button(split_gui,text="Done",command=lambda:ncsplit_done(split_gui))
    split_gui.doneButton.grid(row=nrow,column=0,columnspan=1)
    split_gui.runButton = Tkinter.Button(split_gui,text="Run",command=lambda:ncsplit_run(split_gui))
    split_gui.runButton.grid(row=nrow,column=1,columnspan=1)
    # progress message area
    nrow = nrow + 1
    split_gui.progress_row = nrow
    split_gui.progress = Tkinter.Label(split_gui, text='Waiting for input ...')
    split_gui.progress.grid(row=nrow,column=0,columnspan=6,sticky="W")
    # event loop for GUI
    split_gui.wait_window(split_gui)

def ncsplit_infilename_browse(split_gui):
    root = Tkinter.Tk(); root.withdraw()
    filename = tkFileDialog.askopenfilename(parent=root,title="Choose an input netCDF file",
                                            initialdir="../Sites")
    root.destroy()
    split_gui.inpathname = ntpath.split(filename)[0]+"/"
    split_gui.infilename.set(ntpath.split(filename)[1])

def ncsplit_outfilename_browse(split_gui):
    root = Tkinter.Tk(); root.withdraw()
    filename = tkFileDialog.asksaveasfilename(parent=root,initialdir=split_gui.inpathname,
                                          title="Choose an output netCDF file")
    root.destroy()
    split_gui.outpathname = ntpath.split(filename)[0]+"/"
    split_gui.outfilename.set(ntpath.split(filename)[1])

def ncsplit_done(split_gui):
    split_gui.destroy()

def ncsplit_run(split_gui):
    msg = " Splitting "+split_gui.infilename.get()
    ncsplit_progress(split_gui,msg)
    infilename = split_gui.inpathname+split_gui.infilename.get()
    outfilename = split_gui.inpathname+split_gui.outfilename.get()
    msg = " Splitting "+infilename
    logger.info(msg)
    msg = " Output to "+outfilename
    logger.info(msg)
    startdate = str(split_gui.startEntry.get())
    enddate = str(split_gui.endEntry.get())
    # read the input file into the input data structure
    ds_in = nc_read_series(infilename)
    ts = int(ds_in.globalattributes["time_step"])
    ldt_in = ds_in.series["DateTime"]["Data"]
    ldt_in_flag = ds_in.series["DateTime"]["Flag"]
    # create the output data structure
    ds_out = DataStructure()
    # copy the global attributes
    for item in ds_in.globalattributes.keys():
        ds_out.globalattributes[item] = ds_in.globalattributes[item]
    # get the indices of the start and end datetimes
    si = pfp_utils.GetDateIndex(ldt_in,startdate,ts=ts,default=0,match="exact")
    ei = pfp_utils.GetDateIndex(ldt_in,enddate,ts=ts,default=len(ldt_in),match="exact")
    # get a list of the series in ds_in
    series_list = [item for item in ds_in.series.keys() if "_QCFlag" not in item]
    # remove the Python datetime series
    for item in ["DateTime","DateTime_UTC"]:
        if item in series_list: series_list.remove(item)
    # loop over the series
    for item in series_list:
        data,flag,attr = pfp_utils.GetSeriesasMA(ds_in,item,si=si,ei=ei)
        pfp_utils.CreateSeries(ds_out,item,data,flag,attr)
    # deal with the Python datetime series
    ldt_out = ldt_in[si:ei+1]
    ldt_out_flag = ldt_in_flag[si:ei+1]
    ds_out.series["DateTime"] = {}
    ds_out.series["DateTime"]["Data"] = ldt_out
    ds_out.series["DateTime"]["Flag"] = ldt_out_flag
    ds_out.series["DateTime"]["Attr"]= ds_in.series["DateTime"]["Attr"]
    # update the number of records global attribute
    ds_out.globalattributes["nc_nrecs"] = len(ldt_out)
    # update the start and end datetime global attribute
    ds_out.globalattributes["start_date"] = str(ldt_out[0])
    ds_out.globalattributes["end_date"] = str(ldt_out[-1])
    # write the output data structure to a netCDF file
    ncFile = nc_open_write(outfilename)
    nc_write_series(ncFile, ds_out)
    msg = " Finished splitting "+split_gui.infilename.get()
    ncsplit_progress(split_gui,msg)
    logger.info(msg)

def ncsplit_progress(split_gui,text):
    """ Update progress message in nc split GUI."""
    split_gui.progress.destroy()
    split_gui.progress = Tkinter.Label(split_gui, text=text)
    split_gui.progress.grid(row=9,column=0,columnspan=6,sticky="W")
    split_gui.update()

def nc_read_series(ncFullName,checktimestep=True,fixtimestepmethod="round"):
    """
    Purpose:
     Reads a netCDF file and returns the meta-data and data in a DataStructure.
     The returned data structure is an instance of pfp_io.DataStructure().
     The data structure consists of:
      1) ds.globalattributes
         A dictionary containing the global attributes of the netCDF file.
      2) ds.series
         A dictionary containing the variable data, meta-data and QC flag
         Each variable dictionary in ds.series contains;
         a) ds.series[variable]["Data"]
            A 1D numpy float64 array containing the variable data, missing
            data value is -9999.
         b) ds.series[variable]["Flag"]
            A 1D numpy int32 array containing the QC flag data for this variable.
         c) ds.series[variable]["Attr"]
            A dictionary containing the variable attributes.
    Usage:
     nc_name = pfp_io.get_filename_dialog(path="../Sites/Whroo/Data/Processed/")
     ds = pfp_io.nc_read_series(nc_name)
     where nc_name is the full name of the netCDF file to be read
           ds is the returned data structure
    Side effects:
     This routine checks the time step of the data read from the netCDF file
     against the value of the global attribute "time_step", see pfp_utils.CheckTimeStep.
     If a problem is found with the time step (duplicate records, non-integral
     time steps or gaps) then pfp_utils.FixTimeStep is called to repair the time step.
     Fixing non-integral timne steps requires some user input.  The options are to
     quit ([Q]), interpolate ([I], not implemented yet) or round ([R]).  Quitting
     causes the script to exit and return to the command prompt.  Interpolation
     is not implemented yet but will interpolate the data from the original time
     step to a regular time step.  Rounding will round any non-itegral time steps
     to the nearest time step.
    Author: PRI
    Date: Back in the day
    """
    logger.info(" Reading netCDF file "+ntpath.split(ncFullName)[1])
    netCDF4.default_encoding = 'latin-1'
    ds = DataStructure()
    # check to see if the requested file exists, return empty ds if it doesn't
    if ncFullName[0:4]!="http":
        if not pfp_utils.file_exists(ncFullName,mode="quiet"):
            logger.error(' netCDF file '+ncFullName+' not found')
            raise Exception("nc_read_series: file not found")
    # file probably exists, so let's read it
    ncFile = netCDF4.Dataset(ncFullName,'r')
    # disable automatic masking of data when valid_range specified
    ncFile.set_auto_mask(False)
    # now deal with the global attributes
    gattrlist = ncFile.ncattrs()
    if len(gattrlist)!=0:
        for gattr in gattrlist:
            ds.globalattributes[gattr] = getattr(ncFile,gattr)
    # get a list of the variables in the netCDF file (not their QC flags)
    varlist = [x for x in ncFile.variables.keys() if "_QCFlag" not in x]
    for ThisOne in varlist:
        # skip variables that do not have time as a dimension
        dimlist = [x.lower() for x in ncFile.variables[ThisOne].dimensions]
        if "time" not in dimlist: continue
        # create the series in the data structure
        ds.series[unicode(ThisOne)] = {}
        # get the data and the QC flag
        data,flag,attr = nc_read_var(ncFile,ThisOne)
        ds.series[ThisOne]["Data"] = data
        ds.series[ThisOne]["Flag"] = flag
        ds.series[ThisOne]["Attr"] = attr
    ncFile.close()
    # make sure all values of -9999 have non-zero QC flag
    # NOTE: the following was a quick and dirty fix for something a long time ago
    #       and needs to be retired
    #pfp_utils.CheckQCFlags(ds)
    # get a series of Python datetime objects
    if "time" in ds.series.keys():
        time,f,a = pfp_utils.GetSeries(ds,"time")
        pfp_utils.get_datetimefromnctime(ds,time,a["units"])
    else:
        pfp_utils.get_datetimefromymdhms(ds)
    # round the Python datetime to the nearest second
    pfp_utils.round_datetime(ds,mode="nearest_second")
    # check the time step and fix it required
    if checktimestep:
        if pfp_utils.CheckTimeStep(ds):
            pfp_utils.FixTimeStep(ds,fixtimestepmethod=fixtimestepmethod)
            # update the Excel datetime from the Python datetime
            pfp_utils.get_xldatefromdatetime(ds)
            # update the Year, Month, Day etc from the Python datetime
            pfp_utils.get_ymdhmsfromdatetime(ds)
    # tell the user when the data starts and ends
    ldt = ds.series["DateTime"]["Data"]
    msg = " Got data from "+ldt[0].strftime("%Y-%m-%d %H:%M:%S")+" to "+ldt[-1].strftime("%Y-%m-%d %H:%M:%S")
    logger.info(msg)
    return ds

def nc_read_todf(ncFullName, var_list=[], include_qcflags=False):
    """
    Purpose:
     Read an OzFlux netCDF file and return the data in an Pandas data frame.
    Usage:
     df = pfp_io.nc_read_todf(ncFullName)
      where ncFullName is the full name of the netCDF file.
    Side effects:
     Returns a Pandas data frame
    Author: PRI using code originally written by Ian McHugh
    Date: August 2014
    """
    logger.info(" Reading netCDF file "+ncFullName+" to Pandas data frame")
    netCDF4.default_encoding = 'latin-1'
    # check to see if the requested file exists, return empty ds if it doesn't
    if not pfp_utils.file_exists(ncFullName, mode="quiet"):
        logger.error(' netCDF file '+ncFullName+' not found')
        raise Exception("nc_read_todf: file not found")
    # file probably exists, so let's read it
    ncFile = netCDF4.Dataset(ncFullName, "r")
    # disable automatic masking of data when valid_range specified
    ncFile.set_auto_mask(False)
    # now deal with the global attributes
    gattrlist = ncFile.ncattrs()
    if len(gattrlist)!=0:
        gattr = {}
        for attr in gattrlist:
            gattr[attr] = getattr(ncFile,attr)
    # get a list of variables to read from the netCDF file
    if len(var_list) == 0:
        # get the variable list from the netCDF file contents
        var_list = [l for l in ncFile.variables.keys() if "_QCFlag" not in l]
    if include_qcflags:
        # add the QC flags to the list entered as an argument
        var_flag = []
        for var in var_list:
            var_flag.append(var+"_QCFlag")
        var_list = var_list+var_flag
    # read the variables and attributes from the netCDF file
    # create dictionaries to hold the data and the variable attributes
    data = {}
    vattr = {}
    for item in var_list:
        # skip variables that do not have time as a dimension
        dimlist = [x.lower() for x in ncFile.variables[item].dimensions]
        if "time" not in dimlist:
            continue
        data[item], flag, vattr[item] = nc_read_var(ncFile, item)
        data[item] = numpy.ma.filled(data[item], fill_value=c.missing_value)
    ncFile.close()
    # get a list of Python datetimes from the xlDatetime
    # this may be better replaced with one of the standard OzFluxQC routines
    dates = netCDF4.num2date(data["time"], vattr["time"]["units"])
    # convert the dictionary to a Pandas data frame
    df = pandas.DataFrame(data, index=dates)
    # replace missing values with NaN
    df.replace(to_replace=c.missing_value, value=numpy.NaN, inplace=True)
    return df, gattr, vattr

def df_droprecords(df,qc_list=[0,10]):
    # replace configured error values with NaNs
    df.replace(c.missing_value,np.nan)
    # replace unacceptable QC flags with NaNs
    var_list = df.columns.values.tolist()
    data_list = [item for item in var_list if "QCFlag" not in item]
    flag_list = [item for item in var_list if "QCFlag" in item]
    if len(data_list)!=len(flag_list): raise Exception("df_droprecords: number of data and flag series differ")
    eval_string='|'.join(['(df[flag_list[i]]=='+str(i)+')' for i in qc_list])
    #for i in xrange(len(data_list)):
    for i in range(len(data_list)):
        df[data_list[i]]=np.where(eval(eval_string),df[data_list[i]],np.nan)
    # drop the all records with NaNs
    df=df[data_list]
    # return the data frame
    return df

def nc_read_var(ncFile,ThisOne):
    """ Reads a variable from a netCDF file and returns the data, the QC flag and the variable
        attribute dictionary.
    """
    # check the number of dimensions
    nDims = len(ncFile.variables[ThisOne].shape)
    if nDims not in [1,3]:
        msg = "nc_read_var: unrecognised number of dimensions ("+str(nDims)
        msg = msg+") for netCDF variable "+ ThisOne
        raise Exception(msg)
    if nDims==1:
        # single dimension
        data = ncFile.variables[ThisOne][:]
        # netCDF4 returns a masked array if the "missing_variable" attribute has been set
        # for the variable, here we trap this and force the array in ds.series to be ndarray
        if numpy.ma.isMA(data): data,dummy = pfp_utils.MAtoSeries(data)
        # check for a QC flag
        if ThisOne+'_QCFlag' in ncFile.variables.keys():
            # load it from the netCDF file
            flag = ncFile.variables[ThisOne+'_QCFlag'][:]
        else:
            # create an empty flag series if it does not exist
            nRecs = numpy.size(data)
            flag = numpy.zeros(nRecs,dtype=numpy.int32)
        # trap non-finite values and set them to c.missing_value
        if not numpy.isfinite(data).all():
            idx = numpy.where(numpy.isfinite(data) == False)[0]
            data[idx] = numpy.float64(c.missing_value)
            idx = numpy.where((numpy.isfinite(data) == False) & (flag == 0))[0]
            flag[idx] = numpy.int32(8)
    elif nDims==3:
        # 3 dimensions
        data = ncFile.variables[ThisOne][:,0,0]
        # netCDF4 returns a masked array if the "missing_variable" attribute has been set
        # for the variable, here we trap this and force the array in ds.series to be ndarray
        # may not be needed after adding ncFile.set_auto_mask(False) in nc_read_series().
        if numpy.ma.isMA(data): data,dummy = pfp_utils.MAtoSeries(data)
        # check for a QC flag
        if ThisOne+'_QCFlag' in ncFile.variables.keys():
            # load it from the netCDF file
            flag = ncFile.variables[ThisOne+'_QCFlag'][:,0,0]
        else:
            # create an empty flag series if it does not exist
            nRecs = numpy.size(data)
            flag = numpy.zeros(nRecs,dtype=numpy.int32)
        # trap non-finite values and set them to c.missing_value
        if not numpy.isfinite(data).all():
            idx = numpy.where(numpy.isfinite(data) == False)[0]
            data[idx] = numpy.float64(c.missing_value)
            idx = numpy.where((numpy.isfinite(data) == False) & (flag == 0))[0]
            flag[idx] = numpy.int32(8)
    # force float32 to float64
    if data.dtype=="float32": data = data.astype(numpy.float64)
    # check for Year, Month etc as int64, force to int32 if required
    if ThisOne in ["Year","Month","Day","Hour","Minute","Second"]:
        if data.dtype=="int64": data = data.astype(numpy.int32)
    # get the variable attributes
    vattrlist = ncFile.variables[ThisOne].ncattrs()
    attr = {}
    if len(vattrlist)!=0:
        for vattr in vattrlist:
            attr[vattr] = getattr(ncFile.variables[ThisOne],vattr)
    return data,flag,attr

def nc_open_write(ncFullName,nctype='NETCDF4'):
    """
    Purpose:
     Opens a netCDF file object for writing.  The opened netCDF file
     object is then passed as an argument to pfp_io.nc_write_series, where
     the actual writing of data occurs.
    Usage:
     nc_name = '../Sites/Whroo/Data/Processed/all/Whroo_L4.nc'
     nc_file = pfp_io.nc_open_write(nc_name)
     where nc_name is the ful file name of the netCDF to be written
           nc_file is the returned netCDF file object
    Author: PRI
    Date: Back in the day
    """
    file_name = os.path.split(ncFullName)
    logger.info("Opening netCDF file "+file_name[1])
    try:
        ncFile = netCDF4.Dataset(ncFullName,'w',format=nctype)
    except:
        logger.error(' Unable to open netCDF file '+ncFullName+' for writing')
        ncFile = ''
    return ncFile

def nc_write_data(nc_obj, data_dict):
    """
    Purpose:
     Write a dictionary to a netCDF file or group within a netCDF file.
    Usage:
    Author: PRI
    Date: January 2018
    """
    nrecs = len(data_dict["variables"]["DateTime"]["data"])
    # and give it dimensions of time, latitude and longitude
    nc_obj.createDimension("time", nrecs)
    nc_obj.createDimension("latitude", 1)
    nc_obj.createDimension("longitude", 1)
    dims = ("time", "latitude", "longitude")
    # write the time variable to the netCDF object
    nc_time_units = "seconds since 1970-01-01 00:00:00.0"
    nc_time = netCDF4.date2num(data_dict["variables"]["DateTime"]["data"], nc_time_units, calendar="gregorian")
    nc_var = nc_obj.createVariable("time", "d", ("time",))
    nc_var[:] = nc_time
    setattr(nc_var, "long_name", "time")
    setattr(nc_var, "standard_name", "time")
    setattr(nc_var, "units", nc_time_units)
    setattr(nc_var, "calendar", "gregorian")
    if "time_step" in data_dict["variables"]["DateTime"]["attr"]:
        time_step = data_dict["variables"]["DateTime"]["attr"]["time_step"]
        setattr(nc_var, "time_step", time_step)
    # write the latitude and longitude variables to the group
    nc_var = nc_obj.createVariable("latitude", "d", ("latitude",))
    nc_var[:] = float(data_dict["globalattributes"]["latitude"])
    setattr(nc_var, 'long_name', 'latitude')
    setattr(nc_var, 'standard_name', 'latitude')
    setattr(nc_var, 'units', 'degrees north')
    nc_var = nc_obj.createVariable("longitude", "d", ("longitude",))
    nc_var[:] = float(data_dict["globalattributes"]["longitude"])
    setattr(nc_var, 'long_name', 'longitude')
    setattr(nc_var, 'standard_name', 'longitude')
    setattr(nc_var, 'units', 'degrees east')
    # get a list of variables to write to the netCDF file
    labels = sorted([label for label in data_dict["variables"].keys() if label != "DateTime"])
    # write the variables to the netCDF file object
    for label in labels:
        nc_var = nc_obj.createVariable(label, "d", dims)
        nc_var[:, 0, 0] = data_dict["variables"][label]["data"].tolist()
        for attr_key in data_dict["variables"][label]["attr"]:
            attr_value = data_dict["variables"][label]["attr"][attr_key]
            nc_var.setncattr(attr_key, attr_value)

    return

def nc_write_globalattributes(nc_file, ds, flag_defs=True):
    """
    Purpose:
    Usage:
    Author: PRI
    Date: Back in the day
    """
    ldt = ds.series["DateTime"]["Data"]
    ds.globalattributes['QC_version'] = str(cfg.version_name)+' '+str(cfg.version_number)
    ds.globalattributes["start_date"] = str(ldt[0])
    ds.globalattributes["end_date"] = str(ldt[-1])
    t = time.localtime()
    ds.globalattributes["nc_rundatetime"] = str(datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]))
    gattr_list = ds.globalattributes.keys()
    gattr_list.sort()
    flag_list = []
    attr_list = []
    for item in gattr_list:
        if "Flag" in item:
            flag_list.append(item)
        else:
            attr_list.append(item)
    for item in attr_list:
        if isinstance(ds.globalattributes[item],str):
            attr = ds.globalattributes[item]
        elif isinstance(ds.globalattributes[item],unicode):
            attr = ds.globalattributes[item].encode('ascii','ignore')
        else:
            attr = str(ds.globalattributes[item])
        setattr(nc_file,item,attr)
    if flag_defs:
        for item in flag_list:
            if isinstance(ds.globalattributes[item],str):
                attr = ds.globalattributes[item]
            elif isinstance(ds.globalattributes[item],unicode):
                attr = ds.globalattributes[item].encode('ascii','ignore')
            else:
                attr = str(ds.globalattributes[item])
            setattr(nc_file,item,attr)
    return

def nc_write_series(ncFile, ds, outputlist=None, ndims=3):
    """
    Purpose:
     Write the contents of a data structure to a netCDF file.
    Usage:
     nc_file = pfp_io.nc_open_write(nc_name)
     pfp_io.nc_write_series(nc_file,ds)
     where nc_file is a netCDF file object returned by pfp_io.nc_open_write
           ds is a data structure
    Author: PRI
    Date: Back in the day
    """
    # write the global attributes to the netCDF file
    nc_write_globalattributes(ncFile, ds)
    # we specify the size of the Time dimension because netCDF4 is slow to write files
    # when the Time dimension is unlimited
    if "nc_nrecs" in ds.globalattributes.keys():
        nRecs = int(ds.globalattributes['nc_nrecs'])
    else:
        nRecs = len(ldt)
    ncFile.createDimension("time",nRecs)
    if ndims==3:
        ncFile.createDimension("latitude",1)
        ncFile.createDimension("longitude",1)
        dims = ("time","latitude","longitude")
    else:
        dims = ("time",)
    if outputlist is None:
        outputlist = ds.series.keys()
    else:
        for ThisOne in outputlist:
            if ThisOne not in ds.series.keys():
                logger.warning(" Requested series "+ThisOne+" not found in data structure")
                outputlist.remove(ThisOne)
        if len(outputlist)==0: outputlist = ds.series.keys()
    # can't write an array of Python datetime objects to a netCDF file
    # actually, this could be written as characters
    for ThisOne in ["DateTime","DateTime_UTC"]:
        if ThisOne in outputlist: outputlist.remove(ThisOne)
    # write the time variable
    ldt = ds.series["DateTime"]["Data"]
    nc_time = netCDF4.date2num(ldt,"days since 1800-01-01 00:00:00.0",calendar="gregorian")
    ncVar = ncFile.createVariable("time","d",("time",))
    ncVar[:] = nc_time
    setattr(ncVar,"long_name","time")
    setattr(ncVar,"standard_name","time")
    setattr(ncVar,"units","days since 1800-01-01 00:00:00.0")
    setattr(ncVar,"calendar","gregorian")
    if "time" in outputlist: outputlist.remove("time")
    # now write the latitude and longitude variables
    if "latitude" not in ds.globalattributes: ndims = 1
    if "longitude" not in ds.globalattributes: ndims = 1
    if ndims==3:
        if "latitude" not in outputlist:
            ncVar = ncFile.createVariable("latitude","d",("latitude",))
            ncVar[:] = pfp_utils.convert_anglestring(str(ds.globalattributes["latitude"]))
            setattr(ncVar,'long_name','latitude')
            setattr(ncVar,'standard_name','latitude')
            setattr(ncVar,'units','degrees north')
        if "longitude" not in outputlist:
            ncVar = ncFile.createVariable("longitude","d",("longitude",))
            ncVar[:] = pfp_utils.convert_anglestring(str(ds.globalattributes["longitude"]))
            setattr(ncVar,'long_name','longitude')
            setattr(ncVar,'standard_name','longitude')
            setattr(ncVar,'units','degrees east')
    # now make sure the date and time series are in outputlist
    datetimelist = ['xlDateTime','Year','Month','Day','Hour','Minute','Second','Hdh','Ddd']
    # and write them to the netCDF file
    for ThisOne in sorted(datetimelist):
        if ThisOne in ds.series.keys(): nc_write_var(ncFile,ds,ThisOne,dims)
        if ThisOne in outputlist: outputlist.remove(ThisOne)
    # write everything else to the netCDF file
    for ThisOne in sorted(outputlist):
        nc_write_var(ncFile,ds,ThisOne,dims)
    # write the coordinate reference system (crs) variable
    if "crs" not in outputlist:
        ncVar = ncFile.createVariable("crs","i",())
        setattr(ncVar,"grid_mapping_name","latitude_longitude")
        setattr(ncVar,"long_name","WGS 1984 datum")
        setattr(ncVar,"longitude_of_prime_meridian","0.0")
        setattr(ncVar,"semi_major_axis","6378137.0")
        setattr(ncVar,"inverse_flattening","298.257223563")
    ncFile.close()

def nc_write_var(ncFile, ds, ThisOne, dim):
    """
    Purpose:
     Function to write data from a series in the data structure to a netCDF variable.
    Usage:
     nc_write_var(ncFile,ds,ThisOne,("time","latitude","longitude"))
      where ncFile is a netCDF file object
            ds is the data structure
            ThisOne is the label of a series in ds
            ("time","latitude","longitude") is the dimension tuple
    Author: PRI
    Date: August 2014
    """
    # get the data type of the series in ds
    dt = get_ncdtype(ds.series[ThisOne]["Data"])
    # force data type to float64 or int32
    if dt not in ["d", "i"]:
        dt = "d"
        if ThisOne in ["Year", "Month", "Day", "Hour", "Minute", "Second"]:
            dt = "i"
    # create the netCDF variable
    try:
        ncVar = ncFile.createVariable(ThisOne, dt, dim)
    except RuntimeError:
        msg = "Error writing variable to netCDF file: "+ThisOne
        raise Exception(msg)
    # different writes to the variable depending on whether it is 1D or 3D
    if len(dim)==1:
        ncVar[:] = ds.series[ThisOne]["Data"].tolist()
    elif len(dim)==3:
        ncVar[:, 0, 0] = ds.series[ThisOne]["Data"].tolist()
    else:
        msg = "Unrecognised dimension request for netCDF variable: "+ThisOne
        raise RuntimeError(msg)
    # write the attributes
    for item in ds.series[ThisOne]["Attr"]:
        if item != "_FillValue":
            attr = str(ds.series[ThisOne]["Attr"][item])
            ncVar.setncattr(item, attr)
    # make sure the missing_value attribute is written
    if "missing_value" not in ds.series[ThisOne]["Attr"]:
        ncVar.setncattr("missing_value", c.missing_value)
    # get the data type of the QC flag
    dt = get_ncdtype(ds.series[ThisOne]["Flag"])
    # create the variable
    ncVar = ncFile.createVariable(ThisOne+"_QCFlag", dt, dim)
    # write 1D or 3D
    if len(dim)==1:
        ncVar[:] = ds.series[ThisOne]["Flag"].tolist()
    elif len(dim)==3:
        ncVar[:, 0, 0] = ds.series[ThisOne]["Flag"].tolist()
    else:
        msg = "Unrecognised dimension request for netCDF variable: "+ThisOne
        raise RuntimeError(msg)
    # set the attributes
    ncVar.setncattr("long_name", ThisOne+"QC flag")
    ncVar.setncattr("units", "none")

def xl_open_write(xl_name):
    xl_filename = os.path.basename(xl_name)
    logger.info(' Opening '+xl_filename+' for writing')
    try:
        xl_file = xlwt.Workbook()
    except:
        logger.error(' Unable to open Excel file '+xl_name+' for writing')
        xl_file = ''
    return xl_file

def xl_read_flags(cf,ds,level,VariablesInFile):
    # First data row in Excel worksheets.
    FirstDataRow = int(pfp_utils.get_keyvaluefromcf(cf,["Files",level],"first_data_row")) - 1
    HeaderRow = int(pfp_utils.get_keyvaluefromcf(cf,['Files','in'],'header_row')) - 1
    # Get the full name of the Excel file from the control file.
    xlFullName = get_filename_from_cf(cf,level)
    # Get the Excel workbook object.
    if os.path.isfile(xlFullName):
        xlBook = xlrd.open_workbook(xlFullName)
    else:
        logger.error(' Excel file '+xlFullName+' not found, choose another')
        xlFullName = get_filename_dialog(path='.',title='Choose an Excel file')
        if len(xlFullName)==0:
            return
        xlBook = xlrd.open_workbook(xlFullName)
    ds.globalattributes['xlFullName'] = xlFullName

    for ThisOne in VariablesInFile:
        if 'xl' in cf['Variables'][ThisOne].keys():
            logger.info(' Getting flags for '+ThisOne+' from spreadsheet')
            ActiveSheet = xlBook.sheet_by_name('Flag')
            LastDataRow = int(ActiveSheet.nrows)
            HeaderList = [x.lower() for x in ActiveSheet.row_values(HeaderRow)]
            if cf['Variables'][ThisOne]['xl']['name'] in HeaderList:
                xlCol = HeaderRow.index(cf['Variables'][ThisOne]['xl']['name'])
                Values = ActiveSheet.col_values(xlCol)[FirstDataRow:LastDataRow]
                Types = ActiveSheet.col_types(xlCol)[FirstDataRow:LastDataRow]
                ds.series[ThisOne]['Flag'] = numpy.array([c.missing_value]*len(Values),numpy.int32)
                for i in range(len(Values)):
                    if Types[i]==2: #xlType=3 means a date/time value, xlType=2 means a number
                        ds.series[ThisOne]['Flag'][i] = numpy.int32(Values[i])
                    else:
                        logger.error('  xl_read_flags: flags for '+ThisOne+' not found in xl file')
    return ds

#def xl_read_series(cf):
    ## Instance the data structure object.
    #ds = DataStructure()
    ## get the filename
    #FileName = get_infilenamefromcf(cf)
    #if len(FileName)==0:
        #msg = " in_filename not found in control file"
        #logger.error(msg)
        #ds.returncodes = {"value":1,"message":msg}
        #return ds
    #if not os.path.exists(FileName):
        #msg = ' Input file '+FileName+' specified in control file not found'
        #logger.error(msg)
        #ds.returncodes = {"value":1,"message":msg}
        #return ds
    #label_list = cf['Variables'].keys()
    #if "xlDateTime" not in label_list and "DateTime" not in label_list:
        #msg = " No xlDateTime or DateTime section found in control file"
        #logger.error(msg)
        #ds.returncodes = {"value":1,"message":msg}
        #return ds
    ## convert from Excel row number to xlrd row number
    #first_data_row = int(pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_firstdatarow")) - 1
    #header_row = int(pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_headerrow")) - 1
    ## get the Excel workbook object.
    #file_name = os.path.split(FileName)
    #logger.info(" Reading Excel file "+file_name[1])
    #xl_book = xlrd.open_workbook(FileName)
    ##log.info(" Opened and read Excel file "+FileName)
    #ds.globalattributes['featureType'] = 'timeseries'
    #ds.globalattributes['xl_filename'] = FileName
    #ds.globalattributes['xl_datemode'] = str(xl_book.datemode)
    #xlsheet_names = [x.lower() for x in xl_book.sheet_names()]
    ## Get the Excel file modification date and time, these will be
    ## written to the netCDF file to uniquely identify the version
    ## of the Excel file used to create this netCDF file.
    #s = os.stat(FileName)
    #t = time.localtime(s.st_mtime)
    #ds.globalattributes['xl_moddatetime'] = str(datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]))
    ## Loop over the variables defined in the 'Variables' section of the
    ## configuration file.
    ## We do the xlDateTime variable first so as to set the default number of records
    #if "xlDateTime" in cf["Variables"]:
        #xlsheet_name = cf["Variables"]["xlDateTime"]["xl"]["sheet"]
        #if xlsheet_name.lower() in xlsheet_names:
            #xlsheet_index = xlsheet_names.index(xlsheet_name.lower())
            #active_sheet = xl_book.sheet_by_index(xlsheet_index)
            #header_list = [x.lower() for x in active_sheet.row_values(header_row)]
            #if cf["Variables"]["xlDateTime"]["xl"]["name"].lower() in header_list:
                #logger.info(" Getting xlDateTime from sheet "+xlsheet_name)
                #last_data_row = int(active_sheet.nrows)
                #ds.series[unicode("xlDateTime")] = {}
                #xl_col = header_list.index(cf["Variables"]["xlDateTime"]["xl"]["name"].lower())
                #values = active_sheet.col_values(xl_col)[first_data_row:last_data_row]
                #types = active_sheet.col_types(xl_col)[first_data_row:last_data_row]
                #nrecs = len(values)
                #ds.series["xlDateTime"]["Data"] = numpy.ones(nrecs,dtype=numpy.float64)*float(c.missing_value)
                #ds.series["xlDateTime"]["Flag"] = numpy.ones(nrecs,dtype=numpy.int32)
                #for i in range(nrecs):
                    #if (types[i]==3) or (types[i]==2):
                        #ds.series["xlDateTime"]["Data"][i] = numpy.float64(values[i])
                        #ds.series["xlDateTime"]["Flag"][i] = numpy.int32(0)
                #ds.globalattributes['nc_nrecs'] = str(nrecs)
            #else:
                #logger.error("  xlDateTime not found on sheet "+xlsheet_name)
        #else:
            #logger.error("  Sheet "+xlsheet_name+" (xlDateTime) not found in Excel workbook")
    ## remove xlDateTime from the list of series to be read
    #if "xlDateTime" in label_list:
        #label_list.remove("xlDateTime")
    ## and now loop over the series to be read from the Excel file
    #for label in label_list:
        #if xl_check_cf_section(cf, label):
            #xlsheet_name = cf["Variables"][label]["xl"]["sheet"]
            #if xlsheet_name.lower() in xlsheet_names:
                #xlsheet_index = xlsheet_names.index(xlsheet_name.lower())
                #active_sheet = xl_book.sheet_by_index(xlsheet_index)
                #header_list = [x.lower() for x in active_sheet.row_values(header_row)]
                #if cf["Variables"][label]["xl"]["name"].lower() in header_list:
                    #logger.info(" Getting "+label+" from sheet "+xlsheet_name)
                    #last_data_row = int(active_sheet.nrows)
                    #if last_data_row-first_data_row == nrecs:
                        #ds.series[unicode(label)] = {}
                        #xl_col = header_list.index(cf["Variables"][label]["xl"]["name"].lower())
                        #values = active_sheet.col_values(xl_col)[first_data_row:last_data_row]
                        #types = active_sheet.col_types(xl_col)[first_data_row:last_data_row]
                        #nrecs = len(values)
                        #ds.series[label]["Data"] = numpy.ones(nrecs,dtype=numpy.float64)*float(c.missing_value)
                        #ds.series[label]["Flag"] = numpy.ones(nrecs,dtype=numpy.int32)
                        #for i in range(nrecs):
                            #if (types[i]==3) or (types[i]==2) and (values[i]!=c.missing_value):
                                #ds.series[label]["Data"][i] = numpy.float64(values[i])
                                #ds.series[label]["Flag"][i] = numpy.int32(0)
                    #else:
                        #logger.error("  "+label+" on sheet "+xlsheet_name+" is the wrong length")
                        #continue
                #else:
                    #logger.error("  "+label+" not found on sheet "+xlsheet_name)
            #else:
                #logger.error("  Sheet "+xlsheet_name+" ("+label+") not found in Excel workbook")
    #ds.returncodes = {"value":0,"message":"OK"}
    #return ds

def xl_read_series(cf):
    # Instance the data structure object.
    ds = DataStructure()
    # add the global atributes
    for gattr in cf['Global'].keys():
        ds.globalattributes[gattr] = cf['Global'][gattr]
    # get the filename
    FileName = get_infilenamefromcf(cf)
    if len(FileName)==0:
        msg = " in_filename not found in control file"
        logger.error(msg)
        ds.returncodes = {"value":1,"message":msg}
        return ds
    if not os.path.exists(FileName):
        msg = ' Input file '+FileName+' specified in control file not found'
        logger.error(msg)
        ds.returncodes = {"value":1,"message":msg}
        return ds
    label_list = cf['Variables'].keys()
    if "xlDateTime" not in label_list and "DateTime" not in label_list:
        msg = " No xlDateTime or DateTime section found in control file"
        logger.error(msg)
        ds.returncodes = {"value":1,"message":msg}
        return ds
    # convert from Excel row number to xlrd row number
    first_data_row = int(pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_firstdatarow")) - 1
    header_row = int(pfp_utils.get_keyvaluefromcf(cf,["Files"],"in_headerrow")) - 1
    # get the Excel workbook object.
    file_name = os.path.split(FileName)
    logger.info(" Reading Excel file "+file_name[1])
    xl_book = xlrd.open_workbook(FileName)
    #log.info(" Opened and read Excel file "+FileName)
    ds.globalattributes['featureType'] = 'timeseries'
    ds.globalattributes['xl_filename'] = FileName
    ds.globalattributes['xl_datemode'] = str(xl_book.datemode)
    xlsheet_names = [x.lower() for x in xl_book.sheet_names()]
    # Get the Excel file modification date and time, these will be
    # written to the netCDF file to uniquely identify the version
    # of the Excel file used to create this netCDF file.
    s = os.stat(FileName)
    t = time.localtime(s.st_mtime)
    ds.globalattributes['xl_moddatetime'] = str(datetime.datetime(t[0],t[1],t[2],t[3],t[4],t[5]))
    # Loop over the variables defined in the 'Variables' section of the configuration file.
    info = {}
    for n, label in enumerate(label_list):
        if xl_check_cf_section(cf, label):
            xlsheet_name = cf["Variables"][label]["xl"]["sheet"]
            if xlsheet_name.lower() in xlsheet_names:
                xlsheet_index = xlsheet_names.index(xlsheet_name.lower())
                active_sheet = xl_book.sheet_by_index(xlsheet_index)
                header_list = [x.lower() for x in active_sheet.row_values(header_row)]
                if cf["Variables"][label]["xl"]["name"].lower() in header_list:
                    logger.info(" Getting "+label+" from sheet "+xlsheet_name)
                    last_data_row = int(active_sheet.nrows)
                    ds.series[unicode(label)] = {}
                    xl_col = header_list.index(cf["Variables"][label]["xl"]["name"].lower())
                    values = active_sheet.col_values(xl_col)[first_data_row:last_data_row]
                    types = active_sheet.col_types(xl_col)[first_data_row:last_data_row]
                    nrecs = len(values)
                    ds.series[label]["Data"] = numpy.ones(nrecs,dtype=numpy.float64)*float(c.missing_value)
                    ds.series[label]["Flag"] = numpy.ones(nrecs,dtype=numpy.int32)
                    for i in range(nrecs):
                        if (types[i]==3) or (types[i]==2) and (values[i]!=c.missing_value):
                            ds.series[label]["Data"][i] = numpy.float64(values[i])
                            ds.series[label]["Flag"][i] = numpy.int32(0)
                    ds.series[label]["Attr"] = {"nrecs":nrecs}
                    for attr in cf["Variables"][label]["Attr"].keys():
                        ds.series[label]["Attr"][attr] = cf["Variables"][label]["Attr"][attr]
                    if "missing_value" not in ds.series[label]["Attr"].keys():
                        ds.series[label]["Attr"]["missing_value"] = numpy.int32(c.missing_value)
                    info[label] = {"sheet":active_sheet, "nrecs":nrecs}
                else:
                    if "Function" not in cf["Variables"][label]:
                        logger.error("  "+label+" not found on sheet "+xlsheet_name)
            else:
                if "Function" not in cf["Variables"][label]:
                    logger.error("  Sheet "+xlsheet_name+" ("+label+") not found in Excel workbook")
    # check that all variables have the same length
    all_good = True
    label_list = info.keys()
    nrecs0 = info[label_list[0]]["nrecs"]
    for label in label_list[1:]:
        if info[label]["nrecs"] != nrecs0:
            msg = "  Series " + label + " has " + str(info[label]["nrecs"])
            msg = msg + ", expected "+str(nrecs0)
            logger.error(msg)
            all_good = False
    if all_good:
        ds.returncodes = {"value":0, "message":"OK"}
        ds.globalattributes["nc_nrecs"] = nrecs0
    else:
        msg = "Series with unequal lengths found"
        ds.returncodes = {"value":1, "message":msg}
    return ds

def xl_check_cf_section(cf, label):
    """
    Purpose:
     Helper logical for checking L1 control file entries.
    Usage:
    Author: PRI
    Date: March 2017
    """
    result = False
    cf_label = cf["Variables"][label]
    if "xl" in cf_label.keys():
        if "xl" in cf_label.keys():
            if "sheet" in cf_label["xl"].keys():
                result = True
            else:
                logger.error("  Key 'sheet' not found in control file entry for "+label)
                result = False
    return result

def xl_write_AlternateStats(ds):
    if "alternate" not in dir(ds): return
    # get the output file name
    out_filename = get_outfilenamefromcf(ds.cf)
    # get the Excel file name
    xl_filename = out_filename.replace('.nc','_AlternateStats.xls')
    file_name = os.path.split(xl_filename)
    logger.info(' Writing alternate fit statistics to '+file_name[1])
    # open the Excel file
    xlfile = xlwt.Workbook()
    # list of outputs to write to the Excel file
    date_list = ["startdate","enddate"]
    # loop over the series that have been gap filled using alternate data
    d_xf = xlwt.easyxf(num_format_str='dd/mm/yyyy hh:mm')
    label_list = ds.alternate.keys()
    label_list.sort()
    for label in label_list:
        # get the list of values to output with the start and end dates removed
        output_list = ds.alternate[label]["results"].keys()
        for item in date_list:
            if item in output_list: output_list.remove(item)
        # add a sheet with the series label
        xlResultsSheet = xlfile.add_sheet(label)
        xlRow = 9
        xlCol = 0
        for dt in date_list:
            xlResultsSheet.write(xlRow,xlCol,dt)
            for item in ds.alternate[label]["results"][dt]:
                xlRow = xlRow + 1
                xlResultsSheet.write(xlRow,xlCol,item,d_xf)
            xlRow = 9
            xlCol = xlCol + 1
        for output in output_list:
            xlResultsSheet.write(xlRow, xlCol, output)
            # convert masked array to ndarray
            output_array = numpy.ma.filled(ds.alternate[label]["results"][output], float(c.missing_value))
            for item in output_array:
                xlRow = xlRow + 1
                # xlwt under Anaconda seems to only allow float64!
                xlResultsSheet.write(xlRow, xlCol, numpy.float64(item))
            xlRow = 9
            xlCol = xlCol + 1
    xlfile.save(xl_filename)

def xl_write_SOLOStats(ds, l5_info):
    if "solo" not in l5_info.keys():
        return
    # get the output file name
    out_filename = get_outfilenamefromcf(l5_info["cf"])
    # get the Excel file name
    xl_filename = out_filename.replace('.nc', '_SOLOStats.xls')
    xl_name = os.path.split(xl_filename)
    logger.info(' Writing SOLO statistics to ' + xl_name[1])
    # open the Excel file
    xlfile = xlwt.Workbook()
    # list of outputs to write to the Excel file
    date_list = ["startdate", "enddate"]
    # loop over the series that have been gap filled using ACCESS data
    d_xf = xlwt.easyxf(num_format_str='dd/mm/yyyy hh:mm')
    outputs = l5_info["solo"]["outputs"].keys()
    outputs.sort()
    for output in outputs:
        # get the list of values to output with the start and end dates removed
        stats = l5_info["solo"]["outputs"][output]["results"].keys()
        for item in date_list:
            if item in outputs:
                outputs.remove(item)
        # add a sheet with the series output
        xlResultsSheet = xlfile.add_sheet(output)
        xlRow = 10
        xlCol = 0
        for dt in date_list:
            xlResultsSheet.write(xlRow, xlCol, dt)
            for item in l5_info["solo"]["outputs"][output]["results"][dt]:
                xlRow = xlRow + 1
                xlResultsSheet.write(xlRow, xlCol, item, d_xf)
            xlRow = 10
            xlCol = xlCol + 1
            # remove startdate and enddate from the list of outputs
            stats.remove(dt)
        for stat in stats:
            xlResultsSheet.write(xlRow, xlCol, stat)
            # convert masked array to ndarray
            output_array = numpy.ma.filled(l5_info["solo"]["outputs"][output]["results"][stat],
                                           float(c.missing_value))
            for item in output_array:
                xlRow = xlRow + 1
                # xlwt under Anaconda seems to only allow float64!
                xlResultsSheet.write(xlRow, xlCol, numpy.float64(item))
            xlRow = 10
            xlCol = xlCol + 1
    xlfile.save(xl_filename)

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
     pfp_io.xl_write_ISD_timesteps(xl_file_path, data)
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
                xl_sheet.write(row+1,col+1,data[site][year][stat])
    # save the workbook
    xl_book.save(xl_file_path)

    return

def xl_write_data(xl_sheet, data, xlCol=0):
    """
    Purpose:
     Writes a dictionary to a worksheet in an Excel workbook.
     This routine has 2 arguments,an Excel worksheet instance and
     a dictionary of data to be written out.  The dictionary
     format needs to be:
      1) data["DateTime"]["data"]   - a list of Python datetimes, these will
                                      be written tp the first column of the
                                      worksheet
         data["DateTime"]["units"]  - units of the date time eg "Days", "Years"
         data["DateTime"]["format"] - a format string for xlwt.easyxf eg "dd/mm/yyy"
      2) data[variable]["data"]     - a numpy array of data values
         data[variable]["units"]    - units of the data
         data[variable]["format"]   - an xlwt.easyxf format string eg "0.00" for 2 decimal places
         There can be multiple variables but each must follow the above template.
    Usage:
     pfp_io.xl_write_data(xl_sheet, data)
      where xl_sheet is an Excel worksheet instance
            data     is a dictionary as defined above
    Side effects:
     Writes to an Excel worksheet instance
    Called by:
    Calls:
    Author: PRI
    Date: June 2015
    """
    #xlCol = 0
    # write the data to the xl file
    series_list = data.keys()
    xl_sheet.write(1,xlCol,data["DateTime"]["attr"]["units"])
    nrows = len(data["DateTime"]["data"])
    ncols = len(series_list)
    d_xf = xlwt.easyxf(num_format_str=data["DateTime"]["attr"]["format"])
    for j in range(nrows):
        xl_sheet.write(j+2,xlCol,data["DateTime"]["data"][j],d_xf)
    series_list.remove("DateTime")
    series_list.sort()
    for item in series_list:
        xlCol = xlCol + 1
        xl_sheet.write(0,xlCol,data[item]["attr"]["units"])
        xl_sheet.write(1,xlCol,item)
        d_xf = xlwt.easyxf(num_format_str=data[item]["attr"]["format"])
        if numpy.ma.isMA(data[item]["data"]):
            tmp = numpy.ma.filled(data[item]["data"],fill_value=numpy.NaN)
        else:
            tmp = data[item]["data"]
        for j in range(nrows):
            xl_sheet.write(j+2,xlCol,tmp[j],d_xf)

def xl_write_series(ds, xlfullname, outputlist=None):
    if "nc_nrecs" in ds.globalattributes.keys():
        nRecs = int(ds.globalattributes["nc_nrecs"])
    else:
        variablelist = ds.series.keys()
        nRecs = len(ds.series[variablelist[0]]["Data"])
    # open the Excel file
    msg = " Opening and writing Excel file " + os.path.basename(xlfullname)
    logger.info(msg)
    xlfile = xlwt.Workbook(encoding="latin-1")
    # set the datemode
    if "xl_datemode" not in ds.globalattributes:
        if platform.system() == "darwin":
            ds.globalattributes["xl_datemode"] = 0
        else:
            ds.globalattributes["xl_datemode"] = 1
    xlfile.dates_1904 = int(ds.globalattributes["xl_datemode"])
    # add sheets to the Excel file
    xlAttrSheet = xlfile.add_sheet("Attr")
    xlDataSheet = xlfile.add_sheet("Data")
    xlFlagSheet = xlfile.add_sheet("Flag")
    # write the global attributes
    msg = " Writing the global attributes to the Excel file"
    logger.info(msg)
    xlcol = 0
    xlrow = 0
    xlAttrSheet.write(xlrow, xlcol, "Global attributes")
    xlrow = xlrow + 1
    globalattrlist = ds.globalattributes.keys()
    globalattrlist.sort()
    for ThisOne in sorted([x for x in globalattrlist if "Flag" not in x]):
        xlAttrSheet.write(xlrow, xlcol, ThisOne)
        xlAttrSheet.write(xlrow, xlcol+1, str(ds.globalattributes[ThisOne].encode("ascii", "ignore")))
        xlrow = xlrow + 1
    for ThisOne in sorted([x for x in globalattrlist if "Flag" in x]):
        xlAttrSheet.write(xlrow, xlcol, ThisOne)
        xlAttrSheet.write(xlrow, xlcol+1, str(ds.globalattributes[ThisOne].encode("ascii", "ignore")))
        xlrow = xlrow + 1
    # write the variable attributes
    logger.info(" Writing the variable attributes to the Excel file")
    xlrow = xlrow + 1
    xlAttrSheet.write(xlrow, xlcol, "Variable attributes")
    xlrow = xlrow + 1
    xlcol_varname = 0
    xlcol_attrname = 1
    xlcol_attrvalue = 2
    variablelist = ds.series.keys()
    if outputlist is None:
        outputlist = variablelist
    else:
        for ThisOne in outputlist:
            if ThisOne not in variablelist:
                logger.warning(" Requested series " + ThisOne + " not found in data structure")
                outputlist.remove(ThisOne)
        if len(outputlist) == 0:
            outputlist = variablelist
    outputlist.sort()
    for ThisOne in ["DateTime", "DateTime_UTC"]:
        if ThisOne in outputlist: outputlist.remove(ThisOne)
    for ThisOne in outputlist:
        xlAttrSheet.write(xlrow, xlcol_varname, ThisOne)
        attributelist = ds.series[ThisOne]["Attr"].keys()
        attributelist.sort()
        for Attr in attributelist:
            xlAttrSheet.write(xlrow, xlcol_attrname, Attr)
            xlAttrSheet.write(xlrow, xlcol_attrvalue, str(ds.series[ThisOne]["Attr"][Attr]))
            xlrow = xlrow + 1
    # write the Excel date/time to the data and the QC flags as the first column
    if "xlDateTime" not in ds.series:
        pfp_utils.get_xldatefromdatetime(ds)
    xlDateTime, f, a = pfp_utils.GetSeries(ds, "xlDateTime")
    logger.info(" Writing the datetime to the Excel file")
    d_xf = xlwt.easyxf(num_format_str='dd/mm/yyyy hh:mm')
    xlDataSheet.write(2,xlcol,'xlDateTime')
    for j in range(nRecs):
        xlDataSheet.write(j+3,xlcol,xlDateTime[j],d_xf)
        xlFlagSheet.write(j+3,xlcol,xlDateTime[j],d_xf)
    # remove xlDateTime from the list of variables to be written to the Excel file
    if "xlDateTime" in outputlist: outputlist.remove("xlDateTime")
    # now start looping over the other variables in the xl file
    xlcol = xlcol + 1
    # loop over variables to be output to xl file
    for ThisOne in outputlist:
        # put up a progress message
        msg = " Writing " + ThisOne + " into column " + str(xlcol) + " of the Excel file"
        logger.info(msg)
        # write the units and the variable name to the header rows in the xl file
        attrlist = ds.series[ThisOne]["Attr"].keys()
        if "long_name" in attrlist:
            longname = ds.series[ThisOne]["Attr"]["long_name"]
        elif "Description" in attrlist:
            longname = ds.series[ThisOne]["Attr"]["Description"]
        else:
            longname = None
        if "units" in attrlist:
            units = ds.series[ThisOne]["Attr"]["units"]
        elif "Units" in attrlist:
            units = ds.series[ThisOne]["Attr"]["Units"]
        else:
            units = None
        xlDataSheet.write(0, xlcol, longname)
        xlDataSheet.write(1, xlcol, units)
        xlDataSheet.write(2, xlcol, ThisOne)
        # loop over the values in the variable series (array writes don't seem to work)
        for j in range(nRecs):
            xlDataSheet.write(j+3, xlcol, float(ds.series[ThisOne]["Data"][j]))
        # check to see if this variable has a quality control flag
        if "Flag" in ds.series[ThisOne].keys():
            # write the QC flag name to the xls file
            xlFlagSheet.write(2, xlcol, ThisOne)
            # specify the format of the QC flag (integer)
            d_xf = xlwt.easyxf(num_format_str="0")
            # loop over QC flag values and write to xls file
            for j in range(nRecs):
                xlFlagSheet.write(j+3, xlcol, int(ds.series[ThisOne]['Flag'][j]), d_xf)
        # increment the column pointer
        xlcol = xlcol + 1
    xlfile.save(xlfullname)

def xlsx_write_series(ds, xlsxfullname, outputlist=None):
    if "nc_nrecs" in ds.globalattributes.keys():
        nRecs = int(ds.globalattributes["nc_nrecs"])
    else:
        variablelist = ds.series.keys()
        nRecs = len(ds.series[variablelist[0]]["Data"])
    # open the Excel file
    msg = " Opening and writing Excel file " + os.path.basename(xlsxfullname)
    logger.info(msg)
    if "xl_datemode" not in ds.globalattributes:
        if platform.system() == "darwin":
            ds.globalattributes["xl_datemode"] = 0
        else:
            ds.globalattributes["xl_datemode"] = 1
    if int(ds.globalattributes["xl_datemode"]) == 1:
        xlfile = xlsxwriter.Workbook(xlsxfullname, {"date_1904": True, "nan_inf_to_errors": True})
    else:
        xlfile = xlsxwriter.Workbook(xlsxfullname, {"date_1904": False, "nan_inf_to_errors": True})
    # add sheets to the Excel file
    xlAttrSheet = xlfile.add_worksheet("Attr")
    xlDataSheet = xlfile.add_worksheet("Data")
    xlFlagSheet = xlfile.add_worksheet("Flag")
    # write the global attributes
    logger.info(" Writing the global attributes to the Excel file")
    xlcol = 0
    xlrow = 0
    xlAttrSheet.write(xlrow, xlcol, "Global attributes")
    xlrow = xlrow + 1
    globalattrlist = ds.globalattributes.keys()
    globalattrlist.sort()
    for ThisOne in sorted([x for x in globalattrlist if "Flag" not in x]):
        xlAttrSheet.write(xlrow, xlcol, ThisOne)
        xlAttrSheet.write(xlrow, xlcol+1, str(ds.globalattributes[ThisOne]))
        xlrow = xlrow + 1
    for ThisOne in sorted([x for x in globalattrlist if "Flag" in x]):
        xlAttrSheet.write(xlrow, xlcol, ThisOne)
        xlAttrSheet.write(xlrow, xlcol+1, str(ds.globalattributes[ThisOne]))
        xlrow = xlrow + 1
    # write the variable attributes
    logger.info(" Writing the variable attributes to the Excel file")
    xlrow = xlrow + 1
    xlAttrSheet.write(xlrow, xlcol, "Variable attributes")
    xlrow = xlrow + 1
    xlcol_varname = 0
    xlcol_attrname = 1
    xlcol_attrvalue = 2
    variablelist = ds.series.keys()
    if outputlist is None:
        outputlist = variablelist
    else:
        for ThisOne in outputlist:
            if ThisOne not in variablelist:
                logger.warning(" Requested series " + ThisOne + " not found in data structure")
                outputlist.remove(ThisOne)
        if len(outputlist) == 0:
            outputlist = variablelist
    outputlist.sort()
    for ThisOne in ["DateTime", "DateTime_UTC"]:
        if ThisOne in outputlist: outputlist.remove(ThisOne)
    for ThisOne in outputlist:
        xlAttrSheet.write(xlrow, xlcol_varname, ThisOne)
        attributelist = ds.series[ThisOne]["Attr"].keys()
        attributelist.sort()
        for Attr in attributelist:
            xlAttrSheet.write(xlrow, xlcol_attrname, Attr)
            xlAttrSheet.write(xlrow, xlcol_attrvalue, str(ds.series[ThisOne]["Attr"][Attr]))
            xlrow = xlrow + 1
    # write the Excel date/time to the data and the QC flags as the first column
    ldt = ds.series["DateTime"]["Data"]
    logger.info(" Writing the datetime to the Excel file")
    dt_format = xlfile.add_format({"num_format": "dd/mm/yyyy hh:mm"})
    xlDataSheet.write(2, xlcol, "xlDateTime")
    xlFlagSheet.write(2, xlcol, "xlDateTime")
    for j in range(nRecs):
        xlDataSheet.write_datetime(j+3, xlcol, ldt[j], dt_format)
        xlFlagSheet.write_datetime(j+3, xlcol, ldt[j], dt_format)
    # remove xlDateTime from the list of variables to be written to the Excel file
    if "xlDateTime" in outputlist: outputlist.remove("xlDateTime")
    # now start looping over the other variables in the xl file
    xlcol = xlcol + 1
    # loop over variables to be output to xl file
    for ThisOne in outputlist:
        # put up a progress message
        logger.info(" Writing " + ThisOne + " into column " + str(xlcol) + " of the Excel file")
        # write the units and the variable name to the header rows in the xl file
        attrlist = ds.series[ThisOne]["Attr"].keys()
        if "long_name" in attrlist:
            longname = ds.series[ThisOne]["Attr"]["long_name"]
        elif "Description" in attrlist:
            longname = ds.series[ThisOne]["Attr"]["Description"]
        else:
            longname = None
        if "units" in attrlist:
            units = ds.series[ThisOne]["Attr"]["units"]
        elif "Units" in attrlist:
            units = ds.series[ThisOne]["Attr"]["Units"]
        else:
            units = None
        xlDataSheet.write(0, xlcol, longname)
        xlDataSheet.write(1, xlcol, units)
        xlDataSheet.write(2, xlcol, ThisOne)
        # loop over the values in the variable series (array writes don't seem to work)
        for j in range(nRecs):
            xlDataSheet.write(j+3, xlcol, float(ds.series[ThisOne]["Data"][j]))
        # check to see if this variable has a quality control flag
        if "Flag" in ds.series[ThisOne].keys():
            # write the QC flag name to the Excel file
            xlFlagSheet.write(2, xlcol, ThisOne)
            # specify the format of the QC flag (integer)
            flag_format = xlfile.add_format({"num_format": "0"})
            # loop over QC flag values and write to xl file
            for j in range(nRecs):
                xlFlagSheet.write(j+3, xlcol, int(ds.series[ThisOne]["Flag"][j]), flag_format)
        # increment the column pointer
        xlcol = xlcol + 1

    xlfile.close()
