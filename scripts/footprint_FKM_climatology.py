import logging

logger = logging.getLogger("pfp_log")

def FKM_climatology(zm=None, z0=None, umean=None, ol=None, sigmav=None, ustar=None,
                    wind_dir=None, domain=None, dx=None, dy=None, nx=None, ny=None, 
                    rs=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], rslayer=0,
                    smooth_data=1, crop=False, pulse=None, verbosity=2):
    """
    Derive a flux footprint estimate based on the paper from Kormann and Meixner (2001). The equations solved
    follow the work from Neftel et al. (2008) and the ART footprint tool. Currently no sections are 
    defined to estimate the proportion of footprint source from this defined areas as in Neftel et al. (2008).
    See Kormann, R. and Meixner, F.X., 2001: An analytical footprint model for non-neutral stratification.
    Boundary-Layer Meteorology 99: 207. https://doi.org/10.1023/A:1018991015119 and 
    Neftel, A., Spirig, C., Ammann, C., 2008: Application and test of a simple tool for operational footprint 
    evaluations. Environmental Pollution 152, 644-652. for details.
    The layout of this python script follows the footprint climatology layout by Kljun et al., 2015.
    contact: cacilia.ewenz@internode.on.net

    This function calculates footprints within a fixed physical domain for a series of
    time steps, rotates footprints into the corresponding wind direction and aggregates
    all footprints to a footprint climatology. The percentage of source area is
    calculated for the footprint climatology.


    FKM Input
        All vectors need to be of equal length (one value for each time step)
        zm       = Measurement height above displacement height (i.e. z-d) [m]
                   usually a scalar, but can also be a vector 
        z0       = Roughness length [m]
                   usually a scalar, but can also be a vector 
        umean    = Vector of mean wind speed at zm [ms-1] - enter [None] if not known 
                   Either z0 or umean is required. If both are given,
                   z0 is selected to calculate the footprint
        ol       = Vector of Obukhov length [m]
        sigmav   = Vector of standard deviation of lateral velocity fluctuations [ms-1]
                   if not available it is calculated as 0.5*Ws (wind speed)
        ustar    = Vector of friction velocity [ms-1]
        wind_dir = Vector of wind direction in degrees (of 360) for rotation of the footprint

        Optional input:
        domain       = Domain size as an array of [xmin xmax ymin ymax] [m].
                       Footprint will be calculated for a measurement at [0 0 zm] m
                       Default is smallest area including the r% footprint or [-1000 1000 -1000 1000]m,
                       whichever smallest (80% footprint if r not given).
        dx, dy       = Cell size of domain [m]
                       Small dx, dy results in higher spatial resolution and higher computing time
                       Default is dx = dy = 2 m. If only dx is given, dx=dy.
        nx, ny       = Two integer scalars defining the number of grid elements in x and y
                       Large nx/ny result in higher spatial resolution and higher computing time
                       Default is nx = ny = 1000. If only nx is given, nx=ny.
                       If both dx/dy and nx/ny are given, dx/dy is given priority if the domain is also specified.
        pulse        = Display progress of footprint calculations every pulse-the footprint (e.g., "100")
        verbosity    = Level of verbosity at run time: 0 = completely silent, 1 = notify only of fatal errors,
                       2 = all notifications
    FKM output
        FKM      = Structure array with footprint climatology data for measurement at [0 0 zm] m
        x_2d     = x-grid of 2-dimensional footprint [m]
        y_2d     = y-grid of 2-dimensional footprint [m]
        fclim_2d = Normalised footprint function values of footprint climatology [m-2]
        n        = Number of footprints calculated and included in footprint climatology
        flag_err = 0 if no error, 1 in case of error, 2 if not all contour plots (rs%) within specified domain
    
    Footprint calculation following the Kormann-Meixner Approach
    1st Version by Marx Stampfli, stampfli mathematics, Bern, Switzerland
    Revision December 2006, C. Spirig and A. Neftel, Agroscope, Zurich, Switzerland
                ported into python CM Ewenz, Adelaide Nov 2015 to May 2016
    Array of lower and upper ranges for following parameters
                 (empty,Xcoord,Ycoord,U_star,     LM,Std_v,Wdir,   zm,U_meas,empty)
    lrange = Array(0,    -5000, -5000,  0.01,-999999,    0,   0,    0,     0,    0)
    urange = Array(0,     5000,  5000,     5, 999999,   20, 360, 1000,    30,    0)

    Created: May 2018 Cacilia Ewenz
    version: 0.1
    last change: 08/06/2018 Cacilia Ewenz
    Copyright (C) 2018, Cacilia Ewenz
    """

    import meteorologicalfunctions as mf
    import pfp_utils
    import matplotlib.pyplot as plt
    import numpy
    import pandas
    import csv
    import xlrd
    import datetime
    import dateutil
    from scipy import signal as sg
    import ast
    from netCDF4 import Dataset as NetCDFFile
    import os
    import sys
    import numbers
  
    import constants as c
    c_d2r=c.Pi/180.0

    #===========================================================================
    # initialise counter for exception messages
    counter = [None]*22 # There are 21/20 different exceptions raised in kormei/kljun
    msgstring = [None]*22
    # Input check
    flag_err = 0
        
    # Check existence of required input pars
    if None in [zm, ol, sigmav, ustar] or (z0 is None and umean is None):
        raise_fkm_exception(1, verbosity, counter, msgstring)

    # Convert all input items to lists
    if not isinstance(zm, list): zm = [zm]
    if not isinstance(ol, list): ol = [ol]
    if not isinstance(sigmav, list): sigmav = [sigmav]
    if not isinstance(ustar, list): ustar = [ustar]
    if not isinstance(wind_dir, list): wind_dir = [wind_dir]
    if not isinstance(z0, list): z0 = [z0]
    if not isinstance(umean, list): umean = [umean]

    # Check that all lists have same length, if not raise an error and exit
    ts_len = len(ustar)
    #print " zm = ",len(zm),len(ol),len(z0)

    if any(len(lst) != ts_len for lst in [sigmav, wind_dir, ol]):
        # at least one list has a different length, exit with error message
        raise_fkm_exception(11, verbosity, counter, msgstring)

    # Special treatment for zm, which is allowed to have length 1 for any
    # length >= 1 of all other parameters
    if all(val is None for val in zm): raise_fkm_exception(12, verbosity, counter, msgstring)
    if len(zm) == 1:
        #raise_fkm_exception(17, verbosity, counter, msgstring)
        zm = [zm[0] for i in range(ts_len)]

    # Rename lists as now the function expects time series of inputs
    ustars, sigmavs, ols, wind_dirs, zms, z0s, umeans = \
            ustar, sigmav, ol, wind_dir, zm, z0, umean

    #===========================================================================
    # Define computational domain
    # Check passed values and make some smart assumptions
    if isinstance(dx, numbers.Number) and dy is None: dy = dx
    if isinstance(dy, numbers.Number) and dx is None: dx = dy
    if not all(isinstance(item, numbers.Number) for item in [dx, dy]): dx = dy = None
    if isinstance(nx, int) and ny is None: ny = nx
    if isinstance(ny, int) and nx is None: nx = ny
    if not all(isinstance(item, int) for item in [nx, ny]): nx = ny = None
    if not isinstance(domain, list) or len(domain) != 4: domain = None

    if all(item is None for item in [dx, nx, domain]):
        # If nothing is passed, default domain is a square of 2 Km size centered
        # at the tower with pixel size of 2 meters (hence a 1000x1000 grid)
        domain = [-1000., 1000., -1000., 1000.]
        dx = dy = 2.
        nx = ny = 1000
    elif domain is not None:
        # If domain is passed, it takes the precendence over anything else
        if dx is not None:
            # If dx/dy is passed, takes precendence over nx/ny
            nx = int((domain[1]-domain[0]) / dx)
            ny = int((domain[3]-domain[2]) / dy)
        else:
            # If dx/dy is not passed, use nx/ny (set to 1000 if not passed)
            if nx is None: nx = ny = 1000
            # If dx/dy is not passed, use nx/ny
            dx = (domain[1]-domain[0]) / float(nx)
            dy = (domain[3]-domain[2]) / float(ny)
    elif dx is not None and nx is not None:
        # If domain is not passed but dx/dy and nx/ny are, define domain
        domain = [-nx*dx/2, nx*dx/2, -ny*dy/2, ny*dy/2]
    elif dx is not None:
        # If domain is not passed but dx/dy is, define domain and nx/ny
        domain = [-1000, 1000, -1000, 1000]
        nx = int((domain[1]-domain[0]) / dx)
        ny = int((domain[3]-domain[2]) / dy)
    elif nx is not None:
        # If domain and dx/dy are not passed but nx/ny is, define domain and dx/dy
        domain = [-1000, 1000, -1000, 1000]
        dx = (domain[1]-domain[0]) / float(nx)
        dy = (domain[3]-domain[2]) / float(nx)

    # Put domain into more convenient vars
    xmin, xmax, ymin, ymax = domain
    #print " domain = ",xmin,xmax,ymin,ymax

    # Define pulse if not passed
    if pulse == None:
        if ts_len <= 20:
            pulse = 1
        else:
            pulse = int(ts_len / 20)

    #===========================================================================
    # Define physical domain in cartesian and polar coordinates
    # Cartesian coordinates
    x = numpy.linspace(xmin, xmax, nx + 1)
    y = numpy.linspace(ymin, ymax, ny + 1)
    x_2d, y_2d = numpy.meshgrid(x, y)

    # initialize raster for footprint climatology
    fclim_2d = numpy.zeros(x_2d.shape)
    #===========================================================================
    # Loop on time series

    # Initialize logic array valids to those 'timestamps' for which all inputs are
    # at least present (but not necessarily physically plausible)
    valids = [True if not any([val is None for val in vals]) else False \
              for vals in zip(ustars, sigmavs, ols, wind_dirs, zms)]
    
    for ix, (ustar, sigmav, ol, wind_dir, zm, z0, umean) \
            in enumerate(zip(ustars, sigmavs, ols, wind_dirs, zms, z0s, umeans)):

        # Counter
        if verbosity > 1 and ix % pulse == 0:
            progress = float(ix+1)/float(ts_len)
            pfp_utils.update_progress(progress)
            #msg = "Calculating footprint ", ix+1, " of ", str(ts_len)
            #logger.info(msg)

        valids[ix] = check_fkm_inputs(ustar, sigmav, ol, wind_dir, zm, z0, umean, rslayer, verbosity, counter, msgstring)
        # If inputs are not valid, skip current footprint
        # if not valids[ix]:
        #     raise_fkm_exception(16, verbosity, counter, msgstring)
        # else:
        if valids[ix]:
            # --- calculate Korman-Meixner footprint
            # phi, u, m, n
            zmol = zm / ol
            #print zm, ol, zmol
            if ol > 0.0:
                phi = 1.0+5.0*zmol
                u = (ustar / c.k) * (numpy.log(zm / z0) + 5.0 * zmol)
                m = (1.0 + 5.0 * (zmol)) / (numpy.log(zm / z0) + 5.0 * zmol)
                n = 1.0 / (1.0 + 5.0 * zmol)
            elif ol == 0.0:
                phi = 1.0
                u = ustar / c.k * (numpy.log(zm / z0))
                m = ustar / c.k / u
                n = 1.0
            else:
                zeta = (1.0-16.0*zmol)**0.25
                psi = -2.0*numpy.log(0.5*(1.0+zeta))-numpy.log(0.5*(1.0+zeta*zeta))+2.0*numpy.arctan(zeta)-0.5*c.Pi
                phi = 1.0/(zeta**2)
                u = ustar/c.k*(numpy.log(zm/z0)+psi)
                m = ustar/c.k/zeta/u
                n = (1.0-24.0*zmol)/(1.0-16.0*zmol)
            # r, mu
            r = 2 + m - n
            
            mu = (1 + m) / (2 + m - n)
            
            # U=Umaj, Kmaj, xi
            Umaj = u / (zm**m)
            Kmaj = c.k * ustar * zm / phi / zm**n
            # Kmaj corresponds to kappa in KM 2001
            xi = Umaj * (zm **r) / (r * r * Kmaj)
            # xPhiMax is the (x-)position of the maximum of phi
            xPhiMax = r * xi / (2 * r + 1)
            
            if mu == 0.0:
                GammaProxmu = 0.0
            else:
                GammaProxmu = (1.0 / mu) + 0.1002588 * numpy.exp(mu) - 0.493536 + 0.3066 * mu - 0.09 * (mu**2)
              
            if 1/r == 0.0:
                GammaProx1r = 0.0
            else:
                GammaProx1r = r + 0.1002588 * numpy.exp(1/r) - 0.493536 + 0.3066 * (1/r) - 0.09 * ((1/r)**2)
        
            # Kormann-Meixner parameters A-E
            A = 1 + mu
            B = Umaj * (zm**r) / r / r / Kmaj
            C = (B**mu) /GammaProxmu
            D = sigmav * GammaProx1r / GammaProxmu / ((r * r * Kmaj / Umaj)**(m / r)) / Umaj
            E = (r - m) / r
            #
            # Result: f_2d = normalised f_2d field over the x and y gridcells
            #
            f_2d = numpy.zeros(x_2d.shape)
            # Wind direction and mathematical definitions of angles
            theta = numpy.fmod(450.0-wind_dir,360.0)*c_d2r
            x_ =  x_2d * numpy.cos(theta) + y_2d * numpy.sin(theta)
            y_ = -x_2d * numpy.sin(theta) + y_2d * numpy.cos(theta)
            # mask negative x values
            f_2d = numpy.ma.masked_where(x_ <= 0.0, f_2d)
            x_ma = numpy.ma.masked_where(x_ <= 0.0, x_)

            # This is the original version from the ART-footprint model of Neftel et al., 2008
            # --------------------------------------------------------------------------------
            # sigma = D * x**E
            # CWIF = C * numpy.exp(-B / x) * x**(-A)

            sigma = D * x_ma**E
            F = C * numpy.exp(-B / x_ma) * x_ma**(-A)
            Dy = 1 / numpy.sqrt(2 * c.Pi) / sigma * numpy.exp(-y_**2 / 2 / sigma**2)
            Phimaj = Dy * F
            KorMeix = Phimaj
            f_2d = KorMeix
            
            #help0 = x_ma**E
            #help1 = (numpy.sqrt(2.0*c.Pi)*D*(help0))
            #help2 = numpy.exp(-(y_**2)/(2.0*(D*(help0))**2))
            #help3 = C*numpy.exp(-B/x_ma)*(x_ma**(-A))
            #f_2d = help2*help3/help1
            
            f_2d = numpy.ma.filled(f_2d,float(0))

            #===========================================================================
            # Add to footprint climatology raster
            #print "max of f_2d=",np.max(f_2d)
            fclim_2d = fclim_2d + f_2d;
                        
    #===========================================================================
    # Continue if at least one valid footprint was calculated
    n = sum(valids)
    vs = None
    clevs = None
    if n==0:
        logger.warning("No footprint calculated")
        flag_err = 1
    else:

        #===========================================================================
        # Normalize and smooth footprint climatology
        fclim_2d = fclim_2d / n;

        #logger.info("Number of valid footprints = "+str(n))

        if smooth_data is not None:
            skernel  = numpy.matrix('0.05 0.1 0.05; 0.1 0.4 0.1; 0.05 0.1 0.05')
            fclim_2d = sg.convolve2d(fclim_2d,skernel,mode='same');
            fclim_2d = sg.convolve2d(fclim_2d,skernel,mode='same');

    # Finally print the stats for exception messages, fatal exceptions already resulted in aborting program
    raise_fkm_exception(0, verbosity, counter, msgstring)

    return {'x_2d': x_2d, 'y_2d': y_2d, 'fclim_2d': fclim_2d,'n':n, 'flag_err':flag_err}

#===============================================================================
#===============================================================================
def check_fkm_inputs(ustar, sigmav, ol, wind_dir, zm, z0, umean, rslayer, verbosity, counter, msgstring):
    # Check passed values for physical plausibility and consistency
    if zm <= 0.:
        raise_fkm_exception(2, verbosity, counter, msgstring)
        return False
    if z0 <= 0.:
        raise_fkm_exception(3, verbosity, counter, msgstring)
        return False
    if float(zm)/ol < -3:
        raise_fkm_exception(7, verbosity, counter, msgstring)
        return False
    if float(zm)/ol > 3:
        raise_fkm_exception(7, verbosity, counter, msgstring)
        return False
    if sigmav <= 0:
        raise_fkm_exception(8, verbosity, counter, msgstring)
        return False
    if ustar <= 0.1:
        raise_fkm_exception(9, verbosity, counter, msgstring)
        return False
    if umean <= 0.0:
        raise_fkm_exception(21, verbosity, counter, msgstring)
        return False
    if wind_dir > 360:
        raise_fkm_exception(10, verbosity, counter, msgstring)
        return False
    if wind_dir < 0:
        raise_fkm_exception(10, verbosity, counter, msgstring)
        return False
    return True
#===============================================================================
exTypes = {'message': 'Message',
           'alert': 'Alert',
           'error': 'Error',
           'fatal': 'Fatal error'}

exceptions = [
    {'code': 1,
     'type': exTypes['fatal'],
     'msg': 'At least one required parameter is missing. Please enter all '
            'required inputs. Check documentation for details.'},
    {'code': 2,
     'type': exTypes['error'],
     'msg': 'zm (measurement height) must be larger than zero.'},
    {'code': 3,
     'type': exTypes['error'],
     'msg': 'z0 (roughness length) must be larger than zero.'},
    {'code': 4,
     'type': exTypes['error'],
     'msg': 'h (ABL height) must be larger than 10 m.'},
    {'code': 5,
     'type': exTypes['error'],
     'msg': 'zm (measurement height) must be smaller than h (PBL height).'},
    {'code': 6,
     'type': exTypes['alert'],
     'msg': 'zm (measurement height) should be above roughness sub-layer (12.5*z0).'},
    {'code': 7,
     'type': exTypes['error'],
     'msg': 'zm/ol (measurement height to Obukhov length ratio) must be equal or larger than -15.5.'},
    {'code': 8,
     'type': exTypes['error'],
     'msg': 'sigmav (standard deviation of crosswind) must be larger than zero.'},
    {'code': 9,
     'type': exTypes['error'],
     'msg': 'ustar (friction velocity) must be >=0.1.'},
    {'code': 10,
     'type': exTypes['error'],
     'msg': 'wind_dir (wind direction) must be >=0 and <=360.'},
    {'code': 11,
     'type': exTypes['fatal'],
     'msg': 'Passed data arrays (ustar, zm, h, ol) don\'t all have the same length.'},
    {'code': 12,
     'type': exTypes['fatal'],
     'msg': 'No valid zm (measurement height above displacement height) passed.'},
    {'code': 13,
     'type': exTypes['alert'],
     'msg': 'Using z0, ignoring umean if passed.'},
    {'code': 14,
     'type': exTypes['alert'],
     'msg': 'No valid z0 passed, using umean.'},
    {'code': 15,
     'type': exTypes['fatal'],
     'msg': 'No valid z0 or umean array passed.'},
    {'code': 16,
     'type': exTypes['error'],
     'msg': 'At least one required input is invalid. Skipping current footprint.'},
    {'code': 17,
     'type': exTypes['alert'],
     'msg': 'Only one value of zm passed. Using it for all footprints.'},
    {'code': 18,
     'type': exTypes['fatal'],
     'msg': 'if provided, rs must be in the form of a number or a list of numbers.'},
    {'code': 19,
     'type': exTypes['alert'],
     'msg': 'rs value(s) larger than 90% were found and eliminated.'},
    {'code': 20,
     'type': exTypes['error'],
     'msg': 'zm (measurement height) must be above roughness sub-layer (12.5*z0).'},
    {'code': 21,
     'type': exTypes['error'],
     'msg': 'umean (mean wind speed) must be >=0.0.'},
    ]

def raise_fkm_exception(code, verbosity, counter, msgstring):
    '''Raise exception or prints message according to specified code'''

    icode = int(code)
    if icode > 0:
        if counter[icode] == None:
            counter[icode] = 1
        else:
            counter[icode] = counter[icode] + 1
        ex = [it for it in exceptions if it['code'] == code][0]
        msgstring[icode] = ex['type'] + '(' + str(ex['code']).zfill(4) + '):\n '+ ex['msg']
        #if verbosity > 0: print('')
        if ex['type'] == exTypes['fatal']:
            if verbosity > 0:
                msgstring[icode] = msgstring[icode] + '\n FKM_fixed_domain execution aborted.'
            else:
                msgstring[icode] = ''
            raise Exception(msgstring[icode])
        elif ex['type'] == exTypes['alert']:
            msgstring[icode] = msgstring[icode] #+ '\n Execution continues.'
            if verbosity > 1: 
                pass
        elif ex['type'] == exTypes['error']:
            msgstring[icode] = msgstring[icode] #+ '\n Execution continues.'
            if verbosity > 1: 
                pass
        else:
            if verbosity > 1: 
                pass
    elif icode == 0:
        for iicode in range(1,len(counter)):
            # printout the final stats for exception messages
            if not counter[iicode] == None:
                # print message as logger info 
                logger.warning(str(counter[iicode]) +' times '+ msgstring[iicode])
   # ================================================================
