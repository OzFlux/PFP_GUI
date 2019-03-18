# standard modules
import datetime
import logging
import os
import zipfile
# 3rd party modules
import matplotlib.pyplot as plt
from matplotlib.path import Path
import numpy
import pandas
#from scipy.misc.pilutil import imread
# PFP modules
import constants as c
import pfp_io
import pfp_gf
import pfp_utils

# Kljun, N., Calanca, P., Rotach, M. W., and Schmid, H. P., 2015:
# A simple two-dimensional parameterisation for Flux Footprint Prediction (FFP),
# Geosci. Model Dev., 8, 3695-3713.
import footprint_FFP_climatology as calcfootNK
# The following script cacl_footprint_FKM_climatology is based on the Neftel et al. (2008) ART_footprint tool:
# https://zenodo.org/record/816236#.W2eqUXBx3VM (http://doi.org/10.5281/zenodo.816236), which 
# Kormann, R. and Meixner, F.X., 2001: An analytical footprint model for non-neutral stratification.
# Boundary-Layer Meteorology 99: 207. https://doi.org/10.1023/A:1018991015119 and Neftel, A., Spirig, C.,
# Ammann, C., 2008: Application and test of a simple tool for operational footprint evaluations. Environmental
# Pollution 152, 644-652.
import footprint_FKM_climatology as calcfootKM

logger = logging.getLogger("pfp_log")

# constant for converting degrees to radiant
c_d2r = numpy.pi/180.0
# constant to convert the footprint area from x,y in lon,lat coordinates at the tower site
onedegree = 6378100.0 * c_d2r # distance in m for 1 deg of latitude

# Coordinate steps in footprint process
def footprint_main(cf, mode):
    """
    This script reads data from a PyFluxPro .nc file and processes the data for:
    (1) Kormann&Meixner uses input (single time)        zm,z0,ustar,umean,L,sigmav,wind_dir
    (2) Kljun et al. uses input (vectors for all times) zm,z0,ustar,umean,L,sigmav,wind_dir,Habl
        so Natascha's FFP also needs the height of the boundary layer ===> currently ERAI data got Habl,
        and ACCESS got Habl00 ... Habl22
    === > input for Kormann & Meixner and Natascha Kljun's footprint climatology
    (a) PyFluxPro L3 netcdf file
    (b) ERAI/ACCESS netcdf file
    === > output for the climatology
    (a) daily footprint climatology
    (b) monthly footprint climatology
    (c) annual footprint climatology
    (d) special time set in controlfile for footprint climatology
    (e) every timestep
    GOAL: Footprint climatology can be done on a set time in controlfile
          calculating Kljun et al., 2015 and Kormann and Meixner, 2001 footprint
    DONE: set time in controlfile, special, daily, monthly and annual, every timestep
          Kljun et al. (2015) footprint
          Kormann and Meixner (2001) footprint
          save footprint fields in netcdf file
    Still to do: calculate Habl if not exist, better is set Habl (latter is done)
    C.M.Ewenz, 10 Jun 2018
               21 Jun 2018 (corrections to monthly indexing)
               29 Jun 2018 (kml file, single time stamp)
    P.R.Isaac,    Jul 2018 (re-wrote fp_data_in to get_footprint_data_in; configuration in get_footprint_cfg; time slicing; etc)
    C.M.Ewenz, 30 Jul 2018 (cleaned up printing of info, warning and error messages - include messages in logger)
    C.M.Ewenz, 22 Jan 2019 (included "Hourly" for plotting every timestep)
    C.M.Ewenz, 08 Feb 2019 (estimate cumulative footprint field)
    C.M.EWenz, 21 Feb 2019 (calculate proportion of footprint field in area of interest)
    """
    logger.info(' Read input data files ...')
    # get the L3 data
    ds = get_footprint_data_in(cf, mode)
    ldt = ds.series["DateTime"]["Data"]
    # get the configuration data for the footprint
    d = get_footprint_cfg(cf, ds)
    logger.info(' Starting footprint calculation ...')
    list_StDate, list_EnDate = create_index_list(cf, d, ldt)
    logger.info(' Starting footprint climatology calculation ...')
    # !!! Prepare Output netcdf file !!!
    # Set initial x,y Variables for output
    xout = numpy.linspace(d["xmin"], d["xmax"], d["nx"] + 1)
    yout = numpy.linspace(d["ymin"], d["ymax"], d["nx"] + 1)
    lat0 = float(d["latitude"])
    lon0 = float(d["longitude"])
    lat = lat0 + (yout / onedegree)
    lon = lon0 + (xout / (numpy.cos(lat0*c_d2r) * onedegree))
    lon_2d, lat_2d = numpy.meshgrid(lon, lat)
    # - Initialise output netcdf file and write x,y grid into file as xDistance and yDistance from the tower
    nc_name = d["file_out"]
    #print 'nc_name = ',nc_name
    nc_file = pfp_io.nc_open_write(nc_name)
    # create the x and y dimensions.
    nc_file.createDimension('longitude', len(lon))
    nc_file.createDimension('latitude', len(lat))
    # create time dimension (record, or unlimited dimension)
    nc_file.createDimension('time', None)
    # create number of footprints in climatology dimension (record, or unlimited dimension)
    nc_file.createDimension('dtime', None)
    nc_file.createDimension('num', None)
    # Define coordinate variables, which will hold the coordinate information, x and y distance from the tower location.
    X = nc_file.createVariable('longitude', "d", ('longitude',))
    Y = nc_file.createVariable('latitude', "d", ('latitude',))
    # Define time variable and number of footprints variable at each time
    tx = nc_file.createVariable('dtime', "d", ('dtime',))
    num = nc_file.createVariable('num', "d", ('num',))
    # Assign units attributes to coordinate var data, attaches text attribute to coordinate variables, containing units.
    X.units = 'degree'
    Y.units = 'degree'
    # write data to coordinate vars.
    X[:] = lon
    Y[:] = lat
    # create the sumphi variable
    phi = nc_file.createVariable('sumphi', "d", ('time', 'longitude', 'latitude'))
    # set the units attribute.
    phi.units = ' '
    # === General inputs for FFP
    zmt = d["zm_d"]
    domaint = [d["xmin"], d["xmax"], d["ymin"], d["ymax"]]
    nxt = d["nx"]
    rst = None #[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9] #[90.] #None #[20.,40.,60.,80.]
    # if plotting to screen      is requested then iplot = 1
    # if plotting to googleEarth is requested then iplot = 2
    iplot = int(cf['General']['iplot'])
    # IF export images in kml format?
    if iplot == 2:  # write kml - format header
        kmlname = d["site_name"] + '_' + mode + '_fp' + '.kml'
        kml_name_path = d["plot_path"] +kmlname
        fi = open(kml_name_path, 'w')
        kml_initialise(d,fi,mode)
    i_aoi = pfp_utils.get_keyvaluefromcf(cf,["Options"],'AreaOfInterest')
    if i_aoi:
        paoi = open(d["plot_path"] +'aoi_result.txt', 'w') # open output file
        paoi.write("Start time, Field number, Percent of total\n")

        # ------------------------
    # After deciding which climatology is done, let's do it!
    irun = -1
    for i in range(0, len(list_StDate)):
        irun = irun+1
        # get the start and end indices
        si = list_StDate[i]
        ei = list_EnDate[i]
        # get the series as masked arrays
        umeant, _, _ = pfp_utils.GetSeriesasMA(ds, "Ws", si=si, ei=ei)
        olt, _, _ = pfp_utils.GetSeriesasMA(ds, "L", si=si, ei=ei)
        sigmavt, _, _ = pfp_utils.GetSeriesasMA(ds, "V_Sd", si=si, ei=ei)
        ustart, _, _ = pfp_utils.GetSeriesasMA(ds, "ustar", si=si, ei=ei)
        wind_dirt, _, _ = pfp_utils.GetSeriesasMA(ds, "Wd", si=si, ei=ei)
        z0t, _, _ = pfp_utils.GetSeriesasMA(ds, "z0", si=si, ei=ei)
        ht, _, _ = pfp_utils.GetSeriesasMA(ds, "Habl", si=si, ei=ei)
        # get a composite mask over all variables
        mask_all = numpy.ma.getmaskarray(ustart)
        for item in [umeant, olt, sigmavt, wind_dirt, z0t, ht]:
            mask_item = numpy.ma.getmaskarray(item)
            mask_all = numpy.ma.mask_or(mask_all, mask_item)
        # and then apply the composite mask to all variables and remove masked elements
        umeant = list(numpy.ma.compressed(numpy.ma.masked_where(mask_all == True, umeant)))
        olt = list(numpy.ma.compressed(numpy.ma.masked_where(mask_all == True, olt)))
        sigmavt = list(numpy.ma.compressed(numpy.ma.masked_where(mask_all == True, sigmavt)))
        ustart = list(numpy.ma.compressed(numpy.ma.masked_where(mask_all == True, ustart)))
        wind_dirt = list(numpy.ma.compressed(numpy.ma.masked_where(mask_all == True, wind_dirt)))
        z0t = list(numpy.ma.compressed(numpy.ma.masked_where(mask_all == True, z0t)))
        ht = list(numpy.ma.compressed(numpy.ma.masked_where(mask_all == True, ht)))
        if len(umeant) == 0:
            msg = "No footprint input data for "+str(ldt[si])+" to "+str(ldt[ei])
            logger.warning(msg)
            num[irun]=0
        else:
            if mode == "kljun":
                FFP = calcfootNK.FFP_climatology (zm=zmt,z0=z0t,umean=umeant,h=ht,ol=olt,sigmav=sigmavt,ustar=ustart,\
                                                  wind_dir=wind_dirt,domain=domaint,dx=None,dy=None,nx=nxt,ny=None,\
                                                rs=rst,rslayer=1,smooth_data=1,crop=False,pulse=None,verbosity=2)
                x              = FFP['x_2d']
                y              = FFP['y_2d']
                f              = FFP['fclim_2d']
                num[irun]      = FFP['n']
                #tx[irun] = str(ldt[ei])
                phi[irun,:,:] = f
                fmax=numpy.amax(f)
                fm=f/fmax
            elif mode == "kormei":
                FKM = calcfootKM.FKM_climatology(zm=zmt, z0=z0t, umean=umeant, ol=olt, sigmav=sigmavt, ustar=ustart,\
                                                 wind_dir=wind_dirt, domain=domaint, dx=None, dy=None, nx=nxt, ny=None, \
                         rs=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], rslayer=0,\
                         smooth_data=1, crop=False, pulse=None, verbosity=2)
                x              = FKM['x_2d']
                y              = FKM['y_2d']
                f              = FKM['fclim_2d']
                num[irun]      = FKM['n']
                #tx[irun] = str(ldt[ei])
                phi[irun,:,:] = f
                fmax=numpy.amax(f)
                fm=f/fmax
            else:
                msg = " Unrecognised footprint type " + str(mode)
                logger.error(msg)
                return
            i_cum = pfp_utils.get_keyvaluefromcf(cf,["Options"],'Cumulative')
            if i_cum:
                # ===
                msg = "Caclulated cumulative footprint field"
                logger.info(msg)
                f_min = 0.05
                f_step = 0.05
                f = calc_cumulative(fm,f_min,f_step)
            else:
                f = fm
            if i_aoi:
                # === 
                msg = "Contribution from area of interest"
                logger.info(msg)
                area = PolygonContribution(cf,x,y,fm,ldt[si], ldt[ei],paoi)

        # ====================================================================================================
        # get the default plot width and height
        #clevs = [0.01,0.05,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1]
        clevs = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1]
        imagename = pfp_utils.get_keyvaluefromcf(cf,["General"],'OzFlux_area_image')
        if not num[irun] == 0:
            if iplot == 1:
                # plot on screen and in jpg
                plotphifield(x, y, ldt[si], ldt[ei], f, d["site_name"], mode, clevs, imagename,i_cum)
            elif iplot == 2:
                # plot on screen, in jpg and write kml (google earth) file
                #plotphifield(x, y, ldt[si], ldt[ei], f, d["site_name"], mode, clevs, imagename)
                kml_write(lon, lat, ldt[si], ldt[ei], f, d["site_name"], mode, clevs, fi, d["plot_path"],i_cum)
            plot_num = plt.gcf().number
            if  plot_num > 20:
                plt.close("all")
        # ====================================================================================================
        # Some stats:
        #  a) Possible total number of footprints per climatology = ei - si
        tot_fp = ei - si
        #  b) Remove each time step with "no value", number of times footprint is run = len(umeant)
        tot_fp_nv = len(umeant)
        #  c) Fianl number of valid footprints, removed all time steps where conditions not valid
        tot_valid = num[irun]
        msg = 'Total = ' + str(tot_fp) + ' Used = ' + str(tot_fp_nv) + ' Valid = ' + str(tot_valid) + ' footprints!'
        logger.info(msg)
        
        #progress = float(i+1)/float(len(list_StDate))
        #pfp_utils.update_progress(progress) 
    if iplot == 2:
        # Finish kml file and process a compressed kmz file including all images
        kml_finalise(d,fi,mode,kmlname)
    if i_aoi:
        paoi.close()                  

    # ================================================================
    msg = " Finished " + str(mode) + " footprint writing"
    logger.info(msg)
    msg = " Closing netcdf file " + str(nc_name)
    logger.info(msg)
    nc_file.close()
    # ================================================================

def get_footprint_cfg(cf, ds):
    # Build dictionary of additional configs
    d={}
    # === Which climatology, either definded time, daily, monthly or annual
    d["Climatology"] = pfp_utils.get_keyvaluefromcf(cf,["Options"],"Climatology",default="Special")
    climfreq = d["Climatology"]
    #
    if "out_filename" in cf['Files']:
        file_out = os.path.join(cf['Files']['file_path'],cf['Files']['out_filename'])
    else:
        if climfreq == 'Annual':
            file_out = os.path.join(cf['Files']['file_path'],cf['Files']['in_filename'].replace(".nc","_y_fp.nc"))
        elif climfreq == 'Monthly':
            file_out = os.path.join(cf['Files']['file_path'],cf['Files']['in_filename'].replace(".nc","_m_fp.nc"))
        elif climfreq == 'Daily':
            file_out = os.path.join(cf['Files']['file_path'],cf['Files']['in_filename'].replace(".nc","_d_fp.nc"))
        elif climfreq == 'Hourly':
            file_out = os.path.join(cf['Files']['file_path'],cf['Files']['in_filename'].replace(".nc","_h_fp.nc"))
        elif climfreq == 'Single':
            file_out = os.path.join(cf['Files']['file_path'],cf['Files']['in_filename'].replace(".nc","_si_fp.nc"))
        elif climfreq == 'Special':
            file_out = os.path.join(cf['Files']['file_path'],cf['Files']['in_filename'].replace(".nc","_sp_fp.nc"))

    plot_path = "plots/"
    if "plot_path" in cf["Files"]: plot_path = os.path.join(cf["Files"]["plot_path"],"FP/")
    if not os.path.isdir(plot_path): os.makedirs(plot_path)

    results_path = cf['Files']['file_path']
    if not os.path.isdir(results_path): os.makedirs(results_path)

    d["tower_height"]   = float(cf["Options"]["tower_height"])
    d["canopy_height"]  = float(cf["Options"]["canopy_height"])
    d["footprint_size"] = int(cf["Options"]["footprint_size"])
    d["zm_d"]           = d["tower_height"]-(2.0/3.0*d["canopy_height"])
    d["xTower"]         = 0 #int(cf['Tower']['xTower'])
    d["yTower"]         = 0 #int(cf['Tower']['yTower'])
    d["xmin"]           = -0.5*d["footprint_size"]
    d["xmax"]           =  0.5*d["footprint_size"]
    d["ymin"]           = -0.5*d["footprint_size"]
    d["ymax"]           =  0.5*d["footprint_size"]
    d["nx"]             = int(cf["Options"]["num_cells"])

    d["flux_period"] = int(ds.globalattributes["time_step"])
    #d["timezone"] = int(ds.globalattributes["timezone"])
    d["site_name"] = ds.globalattributes["site_name"]
    if "Latitude" in cf["Options"]:
        d["latitude"] = cf["Options"]["Latitude"]
    else:
        d["latitude"] = ds.globalattributes["latitude"]
    if "Longitude" in cf["Options"]:
        d["longitude"] = cf["Options"]["Longitude"]
    else:
        d["longitude"] = ds.globalattributes["longitude"]

    d["call_mode"] = pfp_utils.get_keyvaluefromcf(cf,["Options"],"call_mode",default="interactive",mode="quiet")
    d["show_plots"] = pfp_utils.get_keyvaluefromcf(cf,["Options"],"show_plots",default=True,mode="quiet")
    d["file_out"] = file_out
    d["plot_path"] = plot_path

    return d

def get_footprint_data_in(cf, mode):
    import pfp_utils
    # read input data and prepare for input into Kormann and Meixner, 2001 or Kljun et al., 2015
    # python routines
    # ---------------------- Get input / output file name ------------------------------------
    # Set input file and output path and create directories for plots and results
    file_in = os.path.join(cf['Files']['file_path'], cf['Files']['in_filename'])
    # read the netcdf file
    msg = ' Reading netCDF file ' + str(file_in)
    logger.info(msg)
    ds = pfp_io.nc_read_series(file_in)
    nrecs = int(ds.globalattributes["nc_nrecs"])
    # array of 0s for QC flag
    f0 = numpy.zeros(nrecs, dtype=numpy.int32)
    # array of 1s for QC flag
    f1 = numpy.ones(nrecs, dtype=numpy.int32)
    # read the external file for Habl if mode = kljun
    # === check to see if we have Habl timeseries in imports ??? What if not? Botheration!
    if mode == "kljun":
        pfp_gf.ImportSeries(cf, ds)
    else: # kormei does not need Habl
        Habl = pfp_utils.CreateEmptyVariable("Habl", nrecs)
        Habl["Label"] = "Habl"
        Habl["Data"] = numpy.ma.array(numpy.full(nrecs, 1000))
        Habl["Flag"] = f0
        Habl["Attr"] = {"long_name":" Boundary-layer height", "units":"m",
                        "standard_name":"not defined"}
        pfp_utils.CreateVariable(ds, Habl)
    # check to see if Monin-Obukhov length is in the data structure
    if "L" not in ds.series.keys():
        # if not, calculate it
        pfp_utils.CalculateMoninObukhovLength(ds)
    # if the cross wind standard deviation is not in the data set (quite common) then use something else
    if "V_Sd" not in ds.series.keys():
        # could do better with:
        # 1) reprocess L3 and output variance of U, V and W
        # 2) estimated from standard deviation of wind direction (if available)
        # 3) estimate using MO relations (needs Habl)
        V_Sd = pfp_utils.CreateEmptyVariable("V_Sd", nrecs)
        if "Uy_Sd" in ds.series.keys():
            #logger.warning("Stdev of cross wind component not in data structure, estimated as 0.5*Ws")
            Uy_Sd = pfp_utils.GetVariable(ds, "Uy_Sd")
            V_Sd["Data"] = Uy_Sd["Data"]
            V_Sd["Attr"]["height"] = Uy_Sd["Attr"]["height"]
        else:
            logger.warning("Stdev of cross wind component not in data structure, estimated as 0.5*Ws")
            Ws = pfp_utils.GetVariable(ds, "Ws")
            V_Sd["Data"] = 0.5*Ws["Data"]
            V_Sd["Attr"]["height"] = Ws["Attr"]["height"]
        V_Sd["Flag"] = numpy.where(numpy.ma.getmaskarray(V_Sd["Data"])==True, f1, f0)
        V_Sd["Attr"]["long_name"] = "Variance of cross-wind velocity component, estimated from Ws"
        V_Sd["Attr"]["units"] = "(m/s)2"
        pfp_utils.CreateVariable(ds, V_Sd)
    # === roughness length
    if "z0" not in ds.series.keys():
        z0 = pfp_utils.CreateEmptyVariable("z0", nrecs)
        # check the global attriibutes first
        if "roughness_length" in ds.globalattributes.keys():
            roughness_length = float(ds.globalattributes["roughness_length"])
            z0["Data"] = numpy.ma.array(numpy.full(nrecs, roughness_length))
            z0["Attr"]["long_name"] = "Roughness length from global attributes"
        elif "roughness_length" in cf["Options"]:
            roughness_length = float(cf["Options"]["roughness_length"])
            z0["Data"] = numpy.ma.array(numpy.full(nrecs, roughness_length))
            z0["Attr"]["long_name"] = "Roughness length from footprint control file"
        else:
            zT = float(cf["Options"]["tower_height"])
            zC = float(cf["Options"]["canopy_height"])
            zm = zT-(2.0/3.0)*zC
            L = pfp_utils.GetVariable(ds, "L")
            ustar = pfp_utils.GetVariable(ds, "ustar")
            Ws = pfp_utils.GetVariable(ds, "Ws")
            z0["Data"] = z0calc(zm, L["Data"], Ws["Data"], ustar["Data"])
            z0["Attr"]["long_name"] = "Roughness length calculated from u*, L, Ws and (z-d)"
        z0["Flag"] = numpy.where(numpy.ma.getmaskarray(z0["Data"])==True, f1, f0)
        z0["Attr"]["units"] = "m"
        pfp_utils.CreateVariable(ds, z0)
    return ds

def kml_initialise(d,fi,mode):
    # 
    #!#kmlname = d["site_name"] + '_' + mode + '_fp' + '.kml'
    #!#kml_name_path = d["plot_path"] +kmlname
    #!#fi = open(kml_name_path, 'w')
    fi.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fi.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
    fi.write("<Folder>\n")
    fi.write("  <name>" + d["site_name"] + "</name>")
    # GE zooms in to the site location
    fi.write('  <LookAt>\n')
    fi.write('    <longitude>'+str(d["longitude"])+'</longitude>\n')
    fi.write('    <latitude>'+str(d["latitude"])+'</latitude>\n')
    fi.write('    <footprintitude>'+str(d["footprint_size"])+'</footprintitude>\n')
    fi.write('    <range>'+str(d["footprint_size"])+'</range>\n')
    fi.write('    <tilt>0</tilt>\n')
    fi.write('    <heading>0</heading>\n')
    fi.write('    <footprintitudeMode>relativeToGround</footprintitudeMode>\n')
    fi.write('  </LookAt>\n')
    # Define the legend in a screen overlay
    fi.write('  <ScreenOverlay>\n')
    fi.write('    <name>Legend: Footprint</name>\n')
    fi.write('    <Icon> <href>cbar.png</href></Icon>\n')
    fi.write('    <overlayXY x="0" y="0" xunits="fraction" yunits="fraction"/>\n')
    fi.write('    <screenXY x="25" y="95" xunits="pixels" yunits="pixels"/>\n')
    fi.write('    <rotationXY x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>\n')
    fi.write('    <size x="0" y="0" xunits="pixels" yunits="pixels"/>\n')
    fi.write('  </ScreenOverlay>\n')
    # Adding our own icon for the placemark
    #fi.write('  <Style id="Options">\n')
    #fi.write('    <IconStyle>\n')
    #fi.write('      <scale>1.5</scale>\n')
    #fi.write('      <Icon>\n')
    #fi.write('        <href>ec_tower.png</href>\n') # !!! this file needs to be copied into the plot directory
    #fi.write('      </Icon>\n')
    #fi.write('    </IconStyle>\n')
    #fi.write('  </Style>\n')
    # Adding a placemark for the site
    fi.write('  <Placemark>\n')
    fi.write('      <name>'+ d["site_name"] +'</name>\n')
    #fi.write('      <styleUrl>#tower</styleUrl>')
    fi.write('      <Point>\n')
    fi.write('          <coordinates>'+str(d["longitude"])+','+str(d["latitude"])+',0</coordinates>\n')
    fi.write('      </Point>\n')
    fi.write('  </Placemark>\n')

def kml_write(lon, lat, zt1, zt2, data, station, mode, clevs, fi, plot_path,i_cum):
    plot_in='Footprint_'+ mode + zt1.strftime("%Y%m%d%H%M") +'.png'
    plotname=plot_path + plot_in
    width = 5
    height = width * data.shape[0]/data.shape[1]
    plt.ioff()
    plt.figure(figsize=(width,height))
    cs = plt.contourf(data,clevs,cmap=plt.get_cmap('hsv'),alpha=0.5)
    plt.axis('off')
    plt.savefig(plotname,transparent=True)
    #plt.clf()
    fn = plt.gcf().number
    plt.close(fn)
    # draw a new figure and replot the colorbar there
    fig,ax = plt.subplots(figsize=(width,height))
    cbar = plt.colorbar(cs,ax=ax)
    # =========================================================================
    #rlevs = [1 - clev for clev in clevs if clev is not None]
    #cbar.set_ticks(rlevs)
    cbar.set_ticks(clevs)
    if i_cum:
        cbar.set_label('Cumulative footprint contribution in percent')
    else:
        cbar.set_label('Percentage of footprint contribution')
    #cbar.set_label('Footprint in fraction')
    #cbar.set_label('Flux footprint contribution in fraction')
    ax.remove()
    plt.savefig(plot_path+'cbar.png',bbox_inches='tight') #, transparent=True)
    fn = plt.gcf().number
    #plt.clf()
    plt.close(fn)
    plt.ion()
    # get the lat/lon bounds of the area
    lon1 = lon[0]
    lon2 = lon[-1]
    lat1 = lat[0]
    lat2 = lat[-1]
    # Hopefully the file was opened properly and the header written
    fi.write('<GroundOverlay>\n')
    fi.write('  <name>'+station+zt2.strftime("%Y%m%d%H%M")+'</name>\n')
    fi.write('  <bgColor>8fffffff</bgColor>\n')
    fi.write('  <Icon>\n')
    fi.write('    <href>'+plot_in+'</href>\n')
    fi.write('  </Icon>\n')
    fi.write('  <TimeSpan>\n')
    fi.write('    <begin>'+zt1.strftime("%Y-%m-%dT%H:%M")+'</begin>\n')
    fi.write('    <end>'+zt2.strftime("%Y-%m-%dT%H:%M")+'</end>\n')
    fi.write('  </TimeSpan>\n')
    fi.write('  <footprintitude>0.0</footprintitude>\n')
    fi.write('  <footprintitudeMode>clampToGround</footprintitudeMode>\n')
    fi.write('  <LatLonBox>\n')
    fi.write('    <north>'+str(lat2)+'</north>\n')
    fi.write('    <south>'+str(lat1)+'</south>\n')
    fi.write('    <east>'+str(lon2)+'</east>\n')
    fi.write('    <west>'+str(lon1)+'</west>\n')
    fi.write('    <rotation>0.0</rotation>\n')
    fi.write('  </LatLonBox>\n')
    fi.write('</GroundOverlay>\n')

def kml_finalise(d,fi,mode,kmlname):
    # write the footer of the kml file and close the file
    fi.write("</Folder>\n")
    fi.write('</kml>\n')
    fi.close()
    # copy tower icon into the plot path directory to be added to the kmz file
    # create a kmz file out of the kml file
    cwd = os.getcwd()
    os.chdir(d["plot_path"])
    kmzname = kmlname.replace(".kml", ".kmz")
    msg = " Creating KMZ file " + kmzname
    logger.info(msg)
    plotlist = [p for p in os.listdir('.') if p.endswith(".png")]
    compression = zipfile.ZIP_DEFLATED
    zf = zipfile.ZipFile(kmzname, mode='w')
    zf.write(kmlname, compress_type=compression)
    os.remove(kmlname)
    for f in plotlist:
        zf.write(f, compress_type=compression)
        os.remove(f)
    zf.close()
    os.chdir(cwd)

def plotphifield(x, y, zt1, zt2, data, station, mode, clevs, imagename,i_cum):
    # plot footprint in 2-dim field; use x,y - coordinates
    text = 'Footprint ' + station + ' ' + zt1.strftime("%Y%m%d%H%M") + '  to  ' + zt2.strftime("%Y%m%d%H%M")
    plotname='plots/Footprint_'+ mode + zt1.strftime("%Y%m%d%H%M") + '.jpg'
    x_ll = x[0,0]   #xllcorner #-250
    x_ur = x[-1,-1] #xurcorner # 250
    y_ll = y[0,0]   #yllcorner #-250
    y_ur = y[-1,-1] #yurcorner # 250
    # create figure and axes instances
    plt.ion()
    fig = plt.figure(figsize=(10,10))
    ax = fig.add_axes([0.1,0.1,0.8,0.8])
    cs = plt.contourf(x,y,data,clevs,cmap=plt.get_cmap('hsv'))
    cbar = plt.colorbar(cs,location='right',pad=0.04,fraction=0.046)
    if i_cum:
        cbar.set_label('Cumulative footprint contribution in percent')
    else:
        cbar.set_label('Percentage of footprint contribution')
    # contour levels
    plt.title(text)
    plt.xlabel('x [m]')
    plt.ylabel('y [m]')
    if imagename != 'None':
        #img = imread(imagename)
        img = plt.imread(imagename)
        plt.imshow(img, zorder=0, extent=[x_ll, x_ur, y_ll, y_ur])
    plt.savefig(plotname)
    plt.draw()
    plt.pause(1e-9)
    plt.ioff()

def calc_cumulative(f, f_min,f_step):
    # ------------------------------------------------------------------------------------
    # calculate the cumulative footprint values by correlating the percentage of max field 
    # to the contribution of the area between two isolines to the total
    # cmewenz - Feb 2019
    fcum05 = numpy.ma.masked_where(f <= f_min, f)
    fcum05 = numpy.ma.filled(fcum05,float(0))
    fcum  = numpy.sum(fcum05)
    num = int(round((1.0 - (f_min)) / f_step))
    ser1 = numpy.linspace(1.0-f_step,f_min,num)
    ser2 = numpy.linspace(1.0,f_min+f_step,num)
    ser3 = 0.5*(ser1+ser2)
    #print ser1,ser2
    cclevs = []
    stest = 0.0
    fmax=numpy.amax(f)
    for i in range(0,len(ser1)):
        test = numpy.ma.masked_where((f <= ser1[i]) | (f > ser2[i]), f)
        if test.count() > 0:
            test = numpy.sum(test)/fcum
        else:
            test = 0.0
        stest = stest + test
        cclevs.append(stest)
        #print ser3[i],stest #fmax,numpy.sum(fcum05),ser1[i],ser2[i],test,stest
    # estimating polygon to match the correlation between cumulative and percent from max
    fcum_eq = numpy.polyfit(ser3,cclevs,3)
    #print fcum_eq
    fcum=fcum_eq[0]*f*f*f+fcum_eq[1]*f*f+fcum_eq[2]*f+fcum_eq[3]
    f=fcum
    
    return f

def PolygonContribution(cf,x,y,fm,start,finish,paoi):
    # =======================================================================================================
    # Create a field which defines in what area of interest each grid point is located in 
    # a maximum of 10 AoIs can be defined, must be rectangles but do not need to line up 
    # with the grid, so can be to an angle of the x,y grid
    # ID = number for field identification
    # area = rectangle specification; x1_coord y1_coord x2_coord y2_coord x3_coord y3_coord x4_coord y4_coord
    # cmewenz 22/02/2019
    # =======================================================================================================
    ix, iy = numpy.shape(fm)
    x, y  = x.flatten(),y.flatten()
    points = numpy.vstack((x,y)).T
    sum_fm = fm.sum()
    #paoi = open('aoi_result.txt', 'w') # open output file
    #paoi.write("Start time, Field number, Percent of total\n")
    for ID in cf["AOI"].keys():
        area = pfp_utils.get_keyvaluefromcf(cf,["AOI",ID],"area",default="")
        area = [float(i) for i in area]
        vertices = numpy.reshape(area,(-1,2))
        polygon = Path(vertices)
        # Find if grid point is inside a polygon using matplotlib
        # (https://stackoverflow.com/questions/21339448/how-to-get-list-of-points-inside-a-polygon-in-python)
        grid = polygon.contains_points(points)
        mask = grid.reshape(ix,iy)
        #num_true = (mask == True).sum()
        #num_fals = (mask == False).sum()
        #num_all  = num_true + num_fals
        # mask fm to only contain the area of interest data
        fm_masked = numpy.ma.compressed(numpy.ma.masked_where(mask == False, fm))
        # sum the area
        sum_fm_masked = fm_masked.sum()
        print "%s, %s, % 8.2f" % (start.strftime("%Y%m%d%H%M"),ID, 100.0*(sum_fm_masked/sum_fm))
        #,num_true, num_fals, num_all, sum_fm, sum_fm_masked
        #msg = "Field number = " + ID + ' ' + str(100.0*(sum_fm_masked/sum_fm)) + '%'
        #logger.info(msg)
        paoi.write("%s, %s, % 8.2f\n" % (start.strftime("%Y%m%d %H%M"),ID, 100.0*(sum_fm_masked/sum_fm)))  
    return

def z0calc(zm,LM,U_meas,UStar):
    # aerodynamic roughness length
    # Psi functions according to Dyer (1974)
    # a) create positive and negative LM masks
    LMp = numpy.ma.masked_where(LM <  float(0),LM)
    LMn = numpy.ma.masked_where(LM >= float(0),LM)
    # Calculate z0 assuming logarithmic wind profile
    #          === functions are from Kormann and Meixner (2001) (Eqs. 31 to 35)
    #b) for stable conditions, linear
    FIp = 5.0 * zm/LMp
    # c) for unstable conditions
    zeta = (1.0-16.0*zm/LMn)**(0.25)
    FIn = -2.0*numpy.log(0.5*(1.0+zeta))-numpy.log(0.5*(1.0+zeta*zeta))+2.0*numpy.arctan(zeta)-0.5*c.Pi
    # d) put both parts together again
    #FI = numpy.ma.mask_or(FIp,FIn)
    # d1) fill positive and negative Fn masks
    FIp = numpy.ma.filled(FIp,float(0))
    FIn = numpy.ma.filled(FIn,float(0))
    FI  = FIp+FIn
    # e) determine
    alpha = U_meas * 0.4 / UStar - FI
    # f) finally calculate the roughness length
    ZNull = zm / numpy.exp(alpha)
    #!#            === functions derived from Leclerc and Foken 2015 book, page 61 after Hogstroem, 1988
    #!# b) for stable conditions, linear
    #!FIp = -6.0 * zm/LMp
    #!# c) for unstable conditions
    #!zeta = (1.0+19.3*zm/LMn)**0.25
    #!temp = 0.125*(1.0+zeta*zeta)*(1.0+zeta)*(1.0+zeta)
    #!FIn = numpy.log(temp)-2.0*numpy.arctan(zeta)+0.5*c.Pi
    #!# d) put both parts together again
    #!#FI = numpy.ma.mask_or(FIp,FIn,copy=True)
    #!# d1) fill positive and negative Fn masks
    #!FIp = numpy.ma.filled(FIp,float(0))
    #!FIn = numpy.ma.filled(FIn,float(0))
    #!FI  = FIp+FIn
    #!# e) determine
    #!alpha = U_meas * 0.4 / UStar + FI
    #!# f) finally calculate the roughness length
    #!ZNull = zm / numpy.exp(alpha)
    #!#            ===
    #set a lower limit for z0 to avoid numeric problems
    ZNull = numpy.ma.masked_where(ZNull<0.0001,ZNull)
    ZNull = numpy.ma.filled(ZNull,0.0001)
    return ZNull

def create_index_list(cf, d, date):
    """
    Create a list of indices of the datetime for the requested climatology
    Single  = only one element for Start and End, here range is index , index+1
            difficulty, the time for this single element is actually the timestep
            from previous to the named in the list (timestamp at end of interval
    Special = only one element for Start and End
    Hourly  = every timestep
    Daily   = get a climatology for each day, forget about the couple of hours
            before and after the first day, use
            pfp_utils.GetDateIndex(ldt,date_str,ts=30,default=0,match='startnextday')
            pfp_utils.GetDateIndex(ldt,date_str,ts=30,default=0,match='endpreviousday')
    Monthly =
    Annual  =
    """
    #import datetime
    climfreq = d["Climatology"]
    # firstly what climatology is requested
    if climfreq == 'Single':
        list_StDate = []
        list_EnDate = []
        if 'StartDate' in cf['Options'].keys():
            xlStDate = cf['Options']['StartDate']
            list_StDate.append(pfp_utils.GetDateIndex(date,xlStDate,ts=d["flux_period"],default=0,match='exact'))
        else:
            logger.error("No StartDate given. Define which time for footprint calculation in StartDate (DD/MM/YYYY hh:mm)")

        list_EnDate.append(list_StDate[0]+1)

    elif climfreq == 'Special':
        list_StDate = []
        list_EnDate = []
        if 'StartDate' in cf['Options'].keys():
            xlStDate = cf['Options']['StartDate']
            #print xlStDate
            list_StDate.append(pfp_utils.GetDateIndex(date,xlStDate,ts=d["flux_period"],default=0,match='exact'))
        else:
            list_StDate.append(0)         # start from begin of file
        if 'EndDate' in cf['Options'].keys():
            xlEnDate = cf['Options']['EndDate']
            list_EnDate.append(pfp_utils.GetDateIndex(date,xlEnDate,ts=d["flux_period"],default=0,match='exact'))
        else:
            list_EnDate.append(len(date)-1) # run to end of file

    elif climfreq == 'Hourly':
        # if file is half hourly every single data is used
        if 'StartDate' in cf['Options'].keys():
            xlStDate = cf['Options']['StartDate']
            firstIdx = pfp_utils.GetDateIndex(date,xlStDate,ts=d["flux_period"],default=0,match='exact')
        else:
            firstIdx = 0         # start from begin of file
        if 'EndDate' in cf['Options'].keys():
            xlEnDate = cf['Options']['EndDate']
            lastIdx = pfp_utils.GetDateIndex(date,xlEnDate,ts=d["flux_period"],default=0,match='exact')
        else:
            lastIdx = len(date)-2 # run to end of file
        list_StDate = range(firstIdx,lastIdx)
        list_EnDate = range(firstIdx+1,lastIdx+1)
        #print 'Start to End = ',list_StDate, list_EnDate

    elif climfreq == 'Daily':
        StDate = date[0]
        EnDate = date[-1]
        sd = pandas.date_range(start=StDate, end=EnDate, freq='D', normalize=True)    # frequency daily
        ndays     = len(sd)
        list_StDate = []
        list_EnDate = []
        list_StDate.append(pfp_utils.GetDateIndex(date,sd[0],ts=d["flux_period"],default=0,match='exact'))
        list_EnDate.append(pfp_utils.GetDateIndex(date,sd[1],ts=d["flux_period"],default=-1,match='exact'))
        for i in range(1,ndays-1):
            list_StDate.append(pfp_utils.GetDateIndex(date,sd[i],ts=d["flux_period"],default=0,match='exact') +1)
            list_EnDate.append(pfp_utils.GetDateIndex(date,sd[i+1],ts=d["flux_period"],default=-1,match='exact'))
        test_i = pfp_utils.GetDateIndex(date,sd[-1],ts=d["flux_period"],default=0,match='exact')
        if test_i < len(date)-2: # at least one value for the next day, so only midnight not allowed
            list_StDate.append(test_i+1)
            list_EnDate.append(len(date)-1)

    elif climfreq == 'Monthly':
        StDate = date[0]
        EnDate = date[-1]
        sm = pandas.date_range(start=StDate, end=EnDate, freq='MS', normalize=True)    # frequency monthly
        num_int = len(sm)
        list_StDate = []
        list_EnDate = []
        test_i = pfp_utils.GetDateIndex(date,sm[0],ts=d["flux_period"],default=0,match='exact')
        if test_i > 0:
            list_StDate.append(0)
            list_EnDate.append(test_i)
            list_StDate.append(pfp_utils.GetDateIndex(date,sm[0],ts=d["flux_period"],default=0,match='exact')+1)
            list_EnDate.append(pfp_utils.GetDateIndex(date,sm[1],ts=d["flux_period"],default=-1,match='exact'))
        else:
            list_StDate.append(pfp_utils.GetDateIndex(date,sm[0],ts=d["flux_period"],default=0,match='exact'))
            list_EnDate.append(pfp_utils.GetDateIndex(date,sm[1],ts=d["flux_period"],default=-1,match='exact'))
        for i in range(1,num_int-1):
            list_StDate.append(pfp_utils.GetDateIndex(date,sm[i],ts=d["flux_period"],default=0,match='exact')+1)
            list_EnDate.append(pfp_utils.GetDateIndex(date,sm[i+1],ts=d["flux_period"],default=-1,match='exact'))
        test_i = pfp_utils.GetDateIndex(date,sm[-1],ts=d["flux_period"],default=0,match='exact')
        if test_i < len(date)-2: # at least one value for the next day, so only midnight not allowed
            list_StDate.append(test_i+1)
            list_EnDate.append(len(date)-1)

    elif climfreq == 'Annual':
        # Find number of years in df
        StDate = date[0]
        EnDate = date[-1]
        years_index = []
        #date.apply(lambda x: x.year)
        #for i in range(min(year),max(year)+1):
        for i in range(StDate.year,EnDate.year+1):
            years_index.append(i)
        num = len(years_index)
        years_index.append(max(years_index)+1)
        #print num,years_index
        list_StDate = []
        list_EnDate = []
        st = datetime.datetime(years_index[0],1,1,0,0)
        en = datetime.datetime(years_index[1],1,1,0,0)
        list_StDate.append(pfp_utils.GetDateIndex(date,st,ts=d["flux_period"],default=0,match='exact'))
        list_EnDate.append(pfp_utils.GetDateIndex(date,en,ts=d["flux_period"],default=-1,match='exact'))
        if num > 1:
            if num > 2:
                for i in range(1,num-1):
                    st = datetime.datetime(years_index[i],1,1,0,0)
                    en = datetime.datetime(years_index[i+1],1,1,0,0)
                    list_StDate.append(pfp_utils.GetDateIndex(date,st,ts=d["flux_period"],default=0,match='exact')+1)
                    list_EnDate.append(pfp_utils.GetDateIndex(date,en,ts=d["flux_period"],default=-1,match='exact'))
            st = datetime.datetime(years_index[num-1],1,1,0,0)
            en = datetime.datetime(years_index[num],1,1,0,0)
            test_is = pfp_utils.GetDateIndex(date,st,ts=d["flux_period"],default=-1,match='exact')
            test_ie = pfp_utils.GetDateIndex(date,en,ts=d["flux_period"],default=-1,match='exact')
            if test_ie - test_is > 2:
                list_StDate.append(test_is+1)
                list_EnDate.append(test_ie)
    return list_StDate,list_EnDate
#
# Footprint GUI section
#
def footprint_run_gui(footprint_gui):
    """ Run the GapFillFromfootprint GUI."""
    ds_tower = footprint_gui.ds4
    ds_footprint = footprint_gui.ds_footprint
    footprint_info = footprint_gui.footprint_info
    # populate the footprint_info dictionary with things that will be useful
    if str(footprint_gui.radioButtons.checkedButton().text()) == "Manual":
        footprint_info["peropt"] = 1
    elif str(footprint_gui.radioButtons.checkedButton().text()) == "Months":
        footprint_info["peropt"] = 2
    elif str(footprint_gui.radioButtons.checkedButton().text()) == "Days":
        footprint_info["peropt"] = 3

    footprint_info["overwrite"] = footprint_gui.checkBox_Overwrite.isChecked()
    footprint_info["show_plots"] = footprint_gui.checkBox_ShowPlots.isChecked()
    footprint_info["show_all"] = footprint_gui.checkBox_PlotAll.isChecked()
    footprint_info["auto_complete"] = footprint_gui.checkBox_AutoComplete.isChecked()
    footprint_info["autoforce"] = False
    footprint_info["min_percent"] = max(int(str(footprint_gui.lineEdit_MinPercent.text())),1)

    footprint_info["site_name"] = ds_tower.globalattributes["site_name"]
    footprint_info["time_step"] = int(ds_tower.globalattributes["time_step"])
    footprint_info["nperhr"] = int(float(60)/footprint_info["time_step"]+0.5)
    footprint_info["nperday"] = int(float(24)*footprint_info["nperhr"]+0.5)
    footprint_info["max_lags"] = int(float(12)*footprint_info["nperhr"]+0.5)
    footprint_info["Options"] = {}
    footprint_info["footprint"] = {}
    series_list = [ds_tower.footprint[item]["label_tower"] for item in ds_tower.footprint.keys()]
    footprint_info["series_list"] = series_list
    #footprint_info["series_list"] = ["Ah","Ta"]
    logger.info(" Gap filling %s using footprint data", str(list(set(series_list))))
    if footprint_info["peropt"]==1:
        logger.info("Starting manual run ...")
        #footprint_progress(footprint_gui,"Starting manual run ...")
        # get the start and end datetimes entered in the footprint GUI
        if len(str(footprint_gui.lineEdit_StartDate.text())) != 0:
            footprint_info["startdate"] = str(footprint_gui.lineEdit_StartDate.text())
        if len(str(footprint_gui.lineEdit_EndDate.text())) != 0:
            footprint_info["enddate"] = str(footprint_gui.lineEdit_EndDate.text())
        footprint_main(ds_tower, ds_footprint, footprint_info)
        footprint_plotcoveragelines(ds_tower)
        #footprint_progress(footprint_gui,"Finished manual run ...")
        logger.info("Finished manual run ...")
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the footprint_info dictionary, this will hold much useful information
        footprint_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    elif footprint_info["peropt"]==2:
        logger.info("Starting auto (months) run ...")
        #footprint_progress(footprint_gui,"Starting auto (monthly) run ...")
        # get the start datetime entered in the footprint GUI
        nMonths = int(footprint_gui.lineEdit_NumberMonths.text())
        if len(str(footprint_gui.lineEdit_StartDate.text()))!=0:
            footprint_info["startdate"] = str(footprint_gui.lineEdit_StartDate.text())
        if len(str(footprint_gui.lineEdit_EndDate.text())) != 0:
            footprint_info["enddate"] = str(footprint_gui.lineEdit_EndDate.text())
        footprint_info["gui_startdate"] = footprint_info["startdate"]
        footprint_info["gui_enddate"] = footprint_info["enddate"]
        startdate = dateutil.parser.parse(footprint_info["startdate"])
        overlap_enddate = dateutil.parser.parse(footprint_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
        enddate = min([overlap_enddate,enddate])
        footprint_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        while startdate<overlap_enddate:
            footprint_main(ds_tower, ds_footprint, footprint_info)
            footprint_plotcoveragelines(ds_tower)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(months=nMonths)
            footprint_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            enddate = min([enddate,overlap_enddate])
            footprint_info["enddate"] = enddate.strftime("%Y-%m-%d %H:%M")
        footprint_autocomplete(ds_tower,ds_footprint,footprint_info)
        #footprint_progress(footprint_gui,"Finished auto (monthly) run ...")
        logger.info("Finished auto (months) run ...")
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the footprint_info dictionary, this will hold much useful information
        footprint_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    elif footprint_info["peropt"]==3:
        logger.info("Starting auto (days) run ...")
        #footprint_progress(footprint_gui,"Starting auto (days) run ...")
        # get the start datetime entered in the footprint GUI
        nDays = int(footprint_gui.lineEdit_NumberDays.text())
        if len(str(footprint_gui.lineEdit_StartDate.text())) != 0:
            footprint_info["startdate"] = str(footprint_gui.lineEdit_StartDate.text())
        if len(str(footprint_gui.lineEdit_EndDate.text())) != 0:
            footprint_info["enddate"] = str(footprint_gui.lineEdit_EndDate.text())
        footprint_info["gui_startdate"] = footprint_info["startdate"]
        footprint_info["gui_enddate"] = footprint_info["enddate"]
        startdate = dateutil.parser.parse(footprint_info["startdate"])
        gui_enddate = dateutil.parser.parse(footprint_info["gui_enddate"])
        overlap_enddate = dateutil.parser.parse(footprint_info["overlap_enddate"])
        enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
        enddate = min([overlap_enddate,enddate,gui_enddate])
        footprint_info["enddate"] = datetime.datetime.strftime(enddate,"%Y-%m-%d %H:%M")
        footprint_info["startdate"] = datetime.datetime.strftime(startdate,"%Y-%m-%d %H:%M")
        stopdate = min([overlap_enddate,gui_enddate])
        while startdate<stopdate:
            footprint_main(ds_tower, ds_footprint, footprint_info)
            footprint_plotcoveragelines(ds_tower)
            startdate = enddate
            enddate = startdate+dateutil.relativedelta.relativedelta(days=nDays)
            run_enddate = min([stopdate,enddate])
            footprint_info["startdate"] = startdate.strftime("%Y-%m-%d %H:%M")
            footprint_info["enddate"] = run_enddate.strftime("%Y-%m-%d %H:%M")
        footprint_autocomplete(ds_tower,ds_footprint,footprint_info)
        #footprint_progress(footprint_gui,"Finished auto (days) run ...")
        logger.info("Finished auto (days) run ...")
        # get the start and end datetime of the tower data
        ldt_tower = ds_tower.series["DateTime"]["Data"]
        startdate = ldt_tower[0]
        enddate = ldt_tower[-1]
        # create the footprint_info dictionary, this will hold much useful information
        footprint_info = {"overlap_startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "overlap_enddate":enddate.strftime("%Y-%m-%d %H:%M"),
                          "startdate":startdate.strftime("%Y-%m-%d %H:%M"),
                          "enddate":enddate.strftime("%Y-%m-%d %H:%M")}
    else:
        logger.error("GapFillFromfootprint: unrecognised period option")
    # write Excel spreadsheet with fit statistics
    #pfp_io.xl_write_footprintStats(ds_tower)

def footprint_done(footprint_gui):
    """
    Purpose:
     Finishes up after footprint data:
      - destroy the Footprint GUI
      - plot the summary statistics
      - write the summary statistics to an Excel file
    Usage:
    Side effects:
    Author: PRI, modified by CME
    Date: August 2014; modified March 2019
    """
    ds = footprint_gui.ds4
    # plot the summary statistics
    #footprint_plotsummary(ds,footprinternate_info)
    # destroy the footprint GUI
    footprint_gui.close()
    if len(plt.get_fignums())!=0:
        for i in plt.get_fignums():
            plt.close(i)
    # write Excel spreadsheet with fit statistics
    pfp_io.xl_write_footprintStats(ds)
    # put the return code into ds.footprint
    ds.returncodes["footprint"] = "normal"

def footprint_quit(footprint_gui):
    """ Quit the Footprint GUI."""
    ds = footprint_gui.ds4
    # destroy the footprint GUI
    footprint_gui.close()
    # put the return code into ds.footprint
    ds.returncodes["footprint"] = "quit"

