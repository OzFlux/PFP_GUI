# standard modules
import ast
import calendar
import datetime
import logging
import os
import sys
import time
# 3rd party modules
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import numpy
import xlwt
# PFP modules
import constants as c
import pfp_ck
import pfp_io
import pfp_plot
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

def do_2dinterpolation(array_2d):
    """
    Takes a 2d array as input and;
     1) tiles this into a 3 x 3 space (9 repeats of the original 2d array in 3 columns and 3 rows)
     2) removes the missing data (c.missing_value) from the tiled array
     3) does a bi-linear interpolation to replace the the missing data
     4) returns the central tile
     The effect is to replace missing data in the original 2d array with data from a bi-linear
     interpolation, the tiling repeats the original array along its boundaries to avoid problems
     at the array edges.
     Ian McHugh's cleaned up version (avoids error messages from matplotlib version of griddata).
     Checked by comparing the Fci(day) values from the original code and from this version.  The
     values were the same so this version pushed to GitHub on 11/5/2015.
    """

    WasMA = False
    if numpy.ma.isMA(array_2d):
        WasMA = True
        array_2d = numpy.ma.filled(array_2d, float(c.missing_value))

    # Tile the 2d array into a 3 by 3 array
    data_2d_tiled = numpy.tile(array_2d,(3,3))

    # Get the dimensions of the tiled array and create coordinates and grid
    num_x = numpy.shape(data_2d_tiled)[1]
    array_x = numpy.arange(0, num_x)
    num_y = numpy.shape(data_2d_tiled)[0]
    array_y = numpy.arange(0, num_y)
    coords_x, coords_y = numpy.meshgrid(array_x, array_y)

    # Make a flat array of the tiled data
    data_1d = data_2d_tiled.flatten()

    # Make a 2d array of the coordinates
    data_coords = numpy.column_stack([coords_x.flatten(),
                                   coords_y.flatten()])

    # Define an index that will return all valid data for the array
    index = numpy.where(data_1d!= c.missing_value)

    # Do the interpolation
    grid_z = griddata(data_coords[index], data_1d[index],
                      (coords_x, coords_y), method = 'linear')

    # Retrieve the central tile
    array_2d_filled = grid_z[num_y / 3: num_y / 3 * 2, num_x / 3: num_x / 3 * 2]

    # Check something...
    if WasMA:
        array_2d_filled = numpy.ma.masked_where(abs(array_2d_filled - numpy.float64(c.missing_value)) < c.eps, array_2d_filled)
        array_2d = numpy.ma.masked_where(abs(array_2d - numpy.float64(c.missing_value)) < c.eps, array_2d)

    # Return the filled array
    return array_2d_filled

def write_data_1columnpermonth(xlSheet, data, ts, format_string=''):
    xlCol = 0
    # write the data to the xl file
    nrows = numpy.shape(data)[0]
    ncols = numpy.shape(data)[1]
    xlSheet.write(1,xlCol,'Hour')
    for j in range(nrows+1):
        xlSheet.write(j+2,xlCol,float(j)*ts/60)
    xlCol = xlCol + 1
    if len(format_string)!=0:
        d_xf = xlwt.easyxf(num_format_str=format_string)
    else:
        d_xf = xlwt.easyxf()
    for m in range(1,ncols+1):
        xlSheet.write(0,xlCol,calendar.month_abbr[m])
        xlSheet.write(1,xlCol,'Av')
        for j in range(nrows):
            xlSheet.write(j+2,xlCol,data[j,m-1],d_xf)
        xlCol = xlCol + 1

def write_data_1columnpertimestep(xlSheet, data, ts, startdate=None, format_string=''):
    tmp = data.copy()
    if numpy.ma.isMA(tmp): tmp = numpy.ma.filled(tmp,float(c.missing_value))
    xlCol = 0
    # write the data to the xl file
    xlSheet.write(1,xlCol,'Day')
    nrows = numpy.shape(tmp)[0]
    ncols = numpy.shape(tmp)[1]
    if startdate is None:
        for j in range(nrows+1):
            xlSheet.write(j+2,xlCol,j)
    else:
        d_xf = xlwt.easyxf(num_format_str='dd/mm/yyyy')
        for j in range(nrows):
            d = startdate + datetime.timedelta(days=j)
            xlSheet.write(j+2,xlCol,d,d_xf)
    xlCol = xlCol + 1
    if len(format_string)!=0:
        d_xf = xlwt.easyxf(num_format_str=format_string)
    else:
        d_xf = xlwt.easyxf()
    for m in range(1,ncols+1):
        xlSheet.write(1,xlCol,float(m)*ts/60)
        for j in range(nrows):
            xlSheet.write(j+2,xlCol,float(tmp[j,m-1]),d_xf)
        xlCol = xlCol + 1

def do_diurnalstats(Month, Hdh, data, xlSheet, format_string='',ts=30):
    xlCol = 0
    nInts = 24*int((60/ts)+0.5)
    Av_all = numpy.ma.zeros([nInts,12]) + float(c.missing_value)
    if len(format_string)!=0:
        d_xf = xlwt.easyxf(num_format_str=format_string)
    else:
        d_xf = xlwt.easyxf()
    for m in range(1,13):
        mi = numpy.where(Month==m)[0]
        Num,Hr,Av,Sd,Mx,Mn = get_diurnalstats(Hdh[mi],data[mi],ts)
        Av_all[:,m-1] = Av[:]
        Num = numpy.ma.filled(Num,float(c.missing_value))
        Hr = numpy.ma.filled(Hr,float(c.missing_value))
        Av = numpy.ma.filled(Av,float(c.missing_value))
        Sd = numpy.ma.filled(Sd,float(c.missing_value))
        Mx = numpy.ma.filled(Mx,float(c.missing_value))
        Mn = numpy.ma.filled(Mn,float(c.missing_value))
        if m==1:
            xlSheet.write(1,xlCol,'Hour')
            for j in range(len(Hr)):
                xlSheet.write(j+2,xlCol,Hr[j])
            xlCol = xlCol + 1
        xlSheet.write(0,xlCol,calendar.month_abbr[m])
        xlSheet.write(1,xlCol,'Num')
        xlSheet.write(1,xlCol+1,'Av')
        xlSheet.write(1,xlCol+2,'Sd')
        xlSheet.write(1,xlCol+3,'Mx')
        xlSheet.write(1,xlCol+4,'Mn')
        for j in range(len(Hr)):
            xlSheet.write(j+2,xlCol,Num[j])
            xlSheet.write(j+2,xlCol+1,Av[j],d_xf)
            xlSheet.write(j+2,xlCol+2,Sd[j],d_xf)
            xlSheet.write(j+2,xlCol+3,Mx[j],d_xf)
            xlSheet.write(j+2,xlCol+4,Mn[j],d_xf)
        xlCol = xlCol + 5
    return Av_all

def get_diurnalstats(DecHour,Data,ts):
    nInts = 24*int((60/ts)+0.5)
    Num = numpy.ma.zeros(nInts,dtype=int)
    Hr = numpy.ma.zeros(nInts,dtype=float)
    for i in range(nInts):
        Hr[i] = float(i)*ts/60.
    Av = numpy.ma.masked_all(nInts)
    Sd = numpy.ma.masked_all(nInts)
    Mx = numpy.ma.masked_all(nInts)
    Mn = numpy.ma.masked_all(nInts)
    if numpy.size(Data)!=0:
        for i in range(nInts):
            li = numpy.ma.where((abs(DecHour-Hr[i])<c.eps)&(abs(Data-float(c.missing_value))>c.eps))
            Num[i] = numpy.size(li)
            if Num[i]!=0:
                Av[i] = numpy.ma.mean(Data[li])
                Sd[i] = numpy.ma.std(Data[li])
                Mx[i] = numpy.ma.maximum(Data[li])
                Mn[i] = numpy.ma.minimum(Data[li])
    return Num, Hr, Av, Sd, Mx, Mn

def get_rangecheck_limit(cf,label,upr_def=1E10,lwr_def=-1E10):
    upper = float(upr_def)
    lower = float(lwr_def)
    for section in ['Variables']:
        if label in cf[section].keys():
            if 'RangeCheck' in cf[section][label].keys():
                upper = float(cf[section][label]['RangeCheck']['Upper'])
                lower = float(cf[section][label]['RangeCheck']['Lower'])
    return upper,lower

def get_formatstring(cf,label,fmt_def=''):
    fmt_str = fmt_def
    for section in ['Variables']:
        if label in cf[section].keys():
            if 'Format' in cf[section][label].keys():
                fmt_str = str(cf[section][label]['Format'])
    return fmt_str

def climatology(cf):
    nc_filename = pfp_io.get_infilenamefromcf(cf)
    if not pfp_utils.file_exists(nc_filename): return
    xl_filename = nc_filename.replace(".nc","_Climatology.xls")
    xlFile = xlwt.Workbook()
    ds = pfp_io.nc_read_series(nc_filename)
    # calculate Fa if it is not in the data structure
    got_Fa = True
    if "Fa" not in ds.series.keys():
        if "Fn" in ds.series.keys() and "Fg" in ds.series.keys():
            pfp_ts.CalculateAvailableEnergy(ds,Fa_out='Fa',Fn_in='Fn',Fg_in='Fg')
        else:
            got_Fa = False
            logger.warning(" Fn or Fg not in data struicture")
    # get the time step
    ts = int(ds.globalattributes['time_step'])
    # get the site name
    SiteName = ds.globalattributes['site_name']
    # get the datetime series
    dt = ds.series['DateTime']['Data']
    Hdh = ds.series['Hdh']['Data']
    Month = ds.series['Month']['Data']
    # get the initial start and end dates
    StartDate = str(dt[0])
    EndDate = str(dt[-1])
    # find the start index of the first whole day (time=00:30)
    si = pfp_utils.GetDateIndex(dt,StartDate,ts=ts,default=0,match='startnextday')
    # find the end index of the last whole day (time=00:00)
    ei = pfp_utils.GetDateIndex(dt,EndDate,ts=ts,default=-1,match='endpreviousday')
    # get local views of the datetime series
    ldt = dt[si:ei+1]
    Hdh = Hdh[si:ei+1]
    Month = Month[si:ei+1]
    # get the number of time steps in a day and the number of days in the data
    ntsInDay = int(24.0*60.0/float(ts))
    nDays = int(len(ldt))/ntsInDay

    for ThisOne in cf['Variables'].keys():
        if "AltVarName" in cf['Variables'][ThisOne].keys(): ThisOne = cf['Variables'][ThisOne]["AltVarName"]
        if ThisOne in ds.series.keys():
            logger.info(" Doing climatology for "+ThisOne)
            data,f,a = pfp_utils.GetSeriesasMA(ds,ThisOne,si=si,ei=ei)
            if numpy.ma.count(data)==0:
                logger.warning(" No data for "+ThisOne+", skipping ...")
                continue
            fmt_str = get_formatstring(cf,ThisOne,fmt_def='')
            xlSheet = xlFile.add_sheet(ThisOne)
            Av_all = do_diurnalstats(Month,Hdh,data,xlSheet,format_string=fmt_str,ts=ts)
            # now do it for each day
            # we want to preserve any data that has been truncated by the use of the "startnextday"
            # and "endpreviousday" match options used above.  Here we revisit the start and end indices
            # and adjust these backwards and forwards respectively if data has been truncated.
            nDays_daily = nDays
            ei_daily = ei
            si_daily = si
            sdate = ldt[0]
            edate = ldt[-1]
            # is there data after the current end date?
            if dt[-1]>ldt[-1]:
                # if so, push the end index back by 1 day so it is included
                ei_daily = ei + ntsInDay
                nDays_daily = nDays_daily + 1
                edate = ldt[-1]+datetime.timedelta(days=1)
            # is there data before the current start date?
            if dt[0]<ldt[0]:
                # if so, push the start index back by 1 day so it is included
                si_daily = si - ntsInDay
                nDays_daily = nDays_daily + 1
                sdate = ldt[0]-datetime.timedelta(days=1)
            # get the data and use the "pad" option to add missing data if required to
            # complete the extra days
            data,f,a = pfp_utils.GetSeriesasMA(ds,ThisOne,si=si_daily,ei=ei_daily,mode="pad")
            data_daily = data.reshape(nDays_daily,ntsInDay)
            xlSheet = xlFile.add_sheet(ThisOne+'(day)')
            write_data_1columnpertimestep(xlSheet, data_daily, ts, startdate=sdate, format_string=fmt_str)
            data_daily_i = do_2dinterpolation(data_daily)
            xlSheet = xlFile.add_sheet(ThisOne+'i(day)')
            write_data_1columnpertimestep(xlSheet, data_daily_i, ts, startdate=sdate, format_string=fmt_str)
        elif ThisOne=="EF" and got_Fa:
            logger.info(" Doing evaporative fraction")
            EF = numpy.ma.zeros([48,12]) + float(c.missing_value)
            Hdh,f,a = pfp_utils.GetSeriesasMA(ds,'Hdh',si=si,ei=ei)
            Fa,f,a = pfp_utils.GetSeriesasMA(ds,'Fa',si=si,ei=ei)
            Fe,f,a = pfp_utils.GetSeriesasMA(ds,'Fe',si=si,ei=ei)
            for m in range(1,13):
                mi = numpy.where(Month==m)[0]
                Fa_Num,Hr,Fa_Av,Sd,Mx,Mn = get_diurnalstats(Hdh[mi],Fa[mi],ts)
                Fe_Num,Hr,Fe_Av,Sd,Mx,Mn = get_diurnalstats(Hdh[mi],Fe[mi],ts)
                index = numpy.ma.where((Fa_Num>4)&(Fe_Num>4))
                EF[:,m-1][index] = Fe_Av[index]/Fa_Av[index]
            # reject EF values greater than upper limit or less than lower limit
            upr, lwr = get_rangecheck_limit(cf,'EF')
            EF = numpy.ma.filled(numpy.ma.masked_where((EF>upr)|(EF<lwr),EF),float(c.missing_value))
            # write the EF to the Excel file
            xlSheet = xlFile.add_sheet('EF')
            write_data_1columnpermonth(xlSheet, EF, ts, format_string='0.00')
            # do the 2D interpolation to fill missing EF values
            EFi = do_2dinterpolation(EF)
            xlSheet = xlFile.add_sheet('EFi')
            write_data_1columnpermonth(xlSheet, EFi, ts, format_string='0.00')
            # now do EF for each day
            Fa,f,a = pfp_utils.GetSeriesasMA(ds,'Fa',si=si,ei=ei)
            Fe,f,a = pfp_utils.GetSeriesasMA(ds,'Fe',si=si,ei=ei)
            EF = Fe/Fa
            EF = numpy.ma.filled(numpy.ma.masked_where((EF>upr)|(EF<lwr),EF),float(c.missing_value))
            EF_daily = EF.reshape(nDays,ntsInDay)
            xlSheet = xlFile.add_sheet('EF(day)')
            write_data_1columnpertimestep(xlSheet, EF_daily, ts, startdate=ldt[0], format_string='0.00')
            EFi = do_2dinterpolation(EF_daily)
            xlSheet = xlFile.add_sheet('EFi(day)')
            write_data_1columnpertimestep(xlSheet, EFi, ts, startdate=ldt[0], format_string='0.00')
        elif ThisOne=="BR":
            logger.info(" Doing Bowen ratio")
            BR = numpy.ma.zeros([48,12]) + float(c.missing_value)
            Fe,f,a = pfp_utils.GetSeriesasMA(ds,'Fe',si=si,ei=ei)
            Fh,f,a = pfp_utils.GetSeriesasMA(ds,'Fh',si=si,ei=ei)
            for m in range(1,13):
                mi = numpy.where(Month==m)[0]
                Fh_Num,Hr,Fh_Av,Sd,Mx,Mn = get_diurnalstats(Hdh[mi],Fh[mi],ts)
                Fe_Num,Hr,Fe_Av,Sd,Mx,Mn = get_diurnalstats(Hdh[mi],Fe[mi],ts)
                index = numpy.ma.where((Fh_Num>4)&(Fe_Num>4))
                BR[:,m-1][index] = Fh_Av[index]/Fe_Av[index]
            # reject BR values greater than upper limit or less than lower limit
            upr,lwr = get_rangecheck_limit(cf,'BR')
            BR = numpy.ma.filled(numpy.ma.masked_where((BR>upr)|(BR<lwr),BR),float(c.missing_value))
            # write the BR to the Excel file
            xlSheet = xlFile.add_sheet('BR')
            write_data_1columnpermonth(xlSheet, BR, ts, format_string='0.00')
            # do the 2D interpolation to fill missing EF values
            BRi = do_2dinterpolation(BR)
            xlSheet = xlFile.add_sheet('BRi')
            write_data_1columnpermonth(xlSheet, BRi, ts, format_string='0.00')
            # now do BR for each day ...
            Fe,f,a = pfp_utils.GetSeriesasMA(ds,'Fe',si=si,ei=ei)
            Fh,f,a = pfp_utils.GetSeriesasMA(ds,'Fh',si=si,ei=ei)
            BR = Fh/Fe
            BR = numpy.ma.filled(numpy.ma.masked_where((BR>upr)|(BR<lwr),BR),float(c.missing_value))
            BR_daily = BR.reshape(nDays,ntsInDay)
            xlSheet = xlFile.add_sheet('BR(day)')
            write_data_1columnpertimestep(xlSheet, BR_daily, ts, startdate=ldt[0], format_string='0.00')
            BRi = do_2dinterpolation(BR_daily)
            xlSheet = xlFile.add_sheet('BRi(day)')
            write_data_1columnpertimestep(xlSheet, BRi, ts, startdate=ldt[0], format_string='0.00')
        elif ThisOne=="WUE":
            logger.info(" Doing ecosystem WUE")
            WUE = numpy.ma.zeros([48,12]) + float(c.missing_value)
            Fe,f,a = pfp_utils.GetSeriesasMA(ds,'Fe',si=si,ei=ei)
            Fc,f,a = pfp_utils.GetSeriesasMA(ds,'Fc',si=si,ei=ei)
            for m in range(1,13):
                mi = numpy.where(Month==m)[0]
                Fc_Num,Hr,Fc_Av,Sd,Mx,Mn = get_diurnalstats(Hdh[mi],Fc[mi],ts)
                Fe_Num,Hr,Fe_Av,Sd,Mx,Mn = get_diurnalstats(Hdh[mi],Fe[mi],ts)
                index = numpy.ma.where((Fc_Num>4)&(Fe_Num>4))
                WUE[:,m-1][index] = Fc_Av[index]/Fe_Av[index]
            # reject WUE values greater than upper limit or less than lower limit
            upr,lwr = get_rangecheck_limit(cf,'WUE')
            WUE = numpy.ma.filled(numpy.ma.masked_where((WUE>upr)|(WUE<lwr),WUE),float(c.missing_value))
            # write the WUE to the Excel file
            xlSheet = xlFile.add_sheet('WUE')
            write_data_1columnpermonth(xlSheet, WUE, ts, format_string='0.00000')
            # do the 2D interpolation to fill missing EF values
            WUEi = do_2dinterpolation(WUE)
            xlSheet = xlFile.add_sheet('WUEi')
            write_data_1columnpermonth(xlSheet, WUEi, ts, format_string='0.00000')
            # now do WUE for each day ...
            Fe,f,a = pfp_utils.GetSeriesasMA(ds,'Fe',si=si,ei=ei)
            Fc,f,a = pfp_utils.GetSeriesasMA(ds,'Fc',si=si,ei=ei)
            WUE = Fc/Fe
            WUE = numpy.ma.filled(numpy.ma.masked_where((WUE>upr)|(WUE<lwr),WUE),float(c.missing_value))
            WUE_daily = WUE.reshape(nDays,ntsInDay)
            xlSheet = xlFile.add_sheet('WUE(day)')
            write_data_1columnpertimestep(xlSheet, WUE_daily, ts, startdate=ldt[0], format_string='0.00000')
            WUEi = do_2dinterpolation(WUE_daily)
            xlSheet = xlFile.add_sheet('WUEi(day)')
            write_data_1columnpertimestep(xlSheet, WUEi, ts, startdate=ldt[0], format_string='0.00000')
        else:
            logger.warning(" Requested variable "+ThisOne+" not in data structure")
            continue
    logger.info(" Saving Excel file "+os.path.split(xl_filename)[1])
    xlFile.save(xl_filename)

def compare_eddypro():
    epname = pfp_io.get_filename_dialog(title='Choose an EddyPro full output file')
    ofname = pfp_io.get_filename_dialog(title='Choose an L3 output file')

    ds_ep = pfp_io.read_eddypro_full(epname)
    ds_of = pfp_io.nc_read_series(ofname)

    dt_ep = ds_ep.series['DateTime']['Data']
    dt_of = ds_of.series['DateTime']['Data']

    start_datetime = max([dt_ep[0],dt_of[0]])
    end_datetime = min([dt_ep[-1],dt_of[-1]])

    si_of = pfp_utils.GetDateIndex(dt_of, str(start_datetime), ts=30, default=0, match='exact')
    ei_of = pfp_utils.GetDateIndex(dt_of, str(end_datetime), ts=30, default=len(dt_of), match='exact')
    si_ep = pfp_utils.GetDateIndex(dt_ep, str(start_datetime), ts=30, default=0, match='exact')
    ei_ep = pfp_utils.GetDateIndex(dt_ep, str(end_datetime), ts=30, default=len(dt_ep), match='exact')

    us_of = pfp_utils.GetVariable(ds_of,'ustar',start=si_of,end=ei_of)
    us_ep = pfp_utils.GetVariable(ds_ep,'ustar',start=si_ep,end=ei_ep)
    Fh_of = pfp_utils.GetVariable(ds_of,'Fh',start=si_of,end=ei_of)
    Fh_ep = pfp_utils.GetVariable(ds_ep,'Fh',start=si_ep,end=ei_ep)
    Fe_of = pfp_utils.GetVariable(ds_of,'Fe',start=si_of,end=ei_of)
    Fe_ep = pfp_utils.GetVariable(ds_ep,'Fe',start=si_ep,end=ei_ep)
    Fc_of = pfp_utils.GetVariable(ds_of,'Fc',start=si_of,end=ei_of)
    Fc_ep = pfp_utils.GetVariable(ds_ep,'Fc',start=si_ep,end=ei_ep)
    # copy the range check values from the OFQC attributes to the EP attributes
    for of, ep in zip([us_of, Fh_of, Fe_of, Fc_of], [us_ep, Fh_ep, Fe_ep, Fc_ep]):
        for item in ["rangecheck_upper", "rangecheck_lower"]:
            if item in of["Attr"]:
                ep["Attr"][item] = of["Attr"][item]
    # apply QC to the EddyPro data
    pfp_ck.ApplyRangeCheckToVariable(us_ep)
    pfp_ck.ApplyRangeCheckToVariable(Fc_ep)
    pfp_ck.ApplyRangeCheckToVariable(Fe_ep)
    pfp_ck.ApplyRangeCheckToVariable(Fh_ep)
    # plot the comparison
    plt.ion()
    fig = plt.figure(1,figsize=(8,8))
    pfp_plot.xyplot(us_ep["Data"],us_of["Data"],sub=[2,2,1],regr=2,xlabel='u*_EP (m/s)',ylabel='u*_OF (m/s)')
    pfp_plot.xyplot(Fh_ep["Data"],Fh_of["Data"],sub=[2,2,2],regr=2,xlabel='Fh_EP (W/m2)',ylabel='Fh_OF (W/m2)')
    pfp_plot.xyplot(Fe_ep["Data"],Fe_of["Data"],sub=[2,2,3],regr=2,xlabel='Fe_EP (W/m2)',ylabel='Fe_OF (W/m2)')
    pfp_plot.xyplot(Fc_ep["Data"],Fc_of["Data"],sub=[2,2,4],regr=2,xlabel='Fc_EP (umol/m2/s)',ylabel='Fc_OF (umol/m2/s)')
    plt.tight_layout()
    plt.draw()
    plt.ioff()
