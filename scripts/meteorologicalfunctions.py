import constants as c
import numpy
import pfp_utils

def absolutehumidityfromRH(Ta,RH):
    # convert to masked arrays
    RH, WasND = pfp_utils.SeriestoMA(RH)
    Ta, dummy = pfp_utils.SeriestoMA(Ta)
    # do the job
    VPsat = es(Ta)
    vp = RH * VPsat / float(100)
    ah = float(1000000) * vp / ((Ta + 273.15) * c.Rv)
    # convert back to ndarray if input is not a masked array
    if WasND: ah, _ = pfp_utils.MAtoSeries(ah)
    return ah

def co2_ppmfrommgCO2pm3(c_mgpm3,T,p):
    """
     Convert CO2 mass density (mgCO2/m3) to mole fraction (umol/mol)
        Usage:
         CO2_ppm = co2_ppmfrommgCO2pm3(CO2_mgpm3, T, p)
         where
         CO2_mgpm3 (input) - CO2 concentration, mgCO2/m3
         T (input) - air temperature, C
         p (input) - air pressure, kPa
        Returns the CO2 mole fraction in umol/mol.
    """
    # convert to masked array if required
    c_mgpm3, WasND = pfp_utils.SeriestoMA(c_mgpm3)
    T, dummy = pfp_utils.SeriestoMA(T)
    T = T + 273.15             # temperature in K
    p, dummy = pfp_utils.SeriestoMA(p)
    p = p * float(1000)        # pressure in Pa
    # do the job
    c_ppm = (c_mgpm3/c.Mco2)*c.R*T/p
    # convert back to ndarray if input is not a masked array
    if WasND: c_ppm, _ = pfp_utils.MAtoSeries(c_ppm)
    return c_ppm

def co2_mgCO2pm3fromppm(c_ppm,T,p):
    """
     Convert CO2 concentration units of umol/mol (ppm) to mgCO2/m3
        Usage:
         CO2_mgpm3 = co2_mgCO2pm3fromppm(CO2_ppm, T, p)
         where
         CO2_ppm (input) - CO2 concentration, umol/mol
         T (input) - air temperature, C
         p (input) - air pressure, kPa
        Returns the CO2 concentration in mg/m3.
    """
    # convert to masked array if required
    c_ppm, WasND = pfp_utils.SeriestoMA(c_ppm)
    T, dummy = pfp_utils.SeriestoMA(T)
    T = T + 273.15             # temperature in K
    p, dummy = pfp_utils.SeriestoMA(p)
    p = p * float(1000)        # pressure in Pa
    # do the job
    c_mgpm3 = c_ppm*c.Mco2*p/(c.R*T)
    # convert back to ndarray if input is not a masked array
    if WasND: c_mgpm3, _ = pfp_utils.MAtoSeries(c_mgpm3)
    return c_mgpm3

def co2_umolpm3fromppm(c_ppm, T, p):
    """
     Convert CO2 concentration units of umol/mol (ppm) to umol/m3
        Usage:
         CO2_umolpm3 = co2_umolpm3fromppm(CO2_ppm, T, p)
         where
         CO2_ppm (input) - CO2 concentration, umol/mol
         T (input) - air temperature, C
         p (input) - air pressure, kPa
        Returns the CO2 concentration in umol/m3.
    """
    # convert to masked array if required
    c_ppm, WasND = pfp_utils.SeriestoMA(c_ppm)
    T, dummy = pfp_utils.SeriestoMA(T)
    T = T + 273.15             # temperature in K
    p, dummy = pfp_utils.SeriestoMA(p)
    p = p * float(1000)        # pressure in Pa
    # do the job
    c_umolpm3 = c_ppm*p/(c.R*T)
    # convert back to ndarray if input is not a masked array
    if WasND: c_umolpm3, _ = pfp_utils.MAtoSeries(c_umolpm3)
    return c_umolpm3

def densitydryair(Ta,ps,vp):
    # Calculate density of dry air from temperature, pressure and vapour pressure
    #  Ta - air temperature, C
    #  ps - pressure, kPa
    #  vp - vapour pressure, kPa
    # Returns
    #  rhod - dry air density, kg/m3
    rhod = 1000*(ps-vp)/((Ta+273.15)*c.Rd)
    return rhod

def densitymoistair(Ta,ps,vp):
    # Calculate density of moist air from temperature, pressure and vapour pressure
    #  Ta - air temperature, C
    #  ps - pressure, kPa
    #  vp - vapour pressure, kPa
    # Returns
    #  rhom - moist air density, kg/m3
    rhow = vp*1000/((Ta+273.15)*c.Rv)
    rhod = (ps-vp)*1000/((Ta+273.15)*c.Rd)
    rhom = rhow + rhod
    return rhom

def densitywatervapour(Ta,vp):
    # Calculate partial density of water vapour from temperature and vapour pressure
    #  Ta - air temperature, C
    #  vp - vapour pressure, kPa
    # Returns
    #  rhow - partial density of water vapour, kg/m3
    rhow = vp*1000/((Ta+273.15)*c.Rv)
    return rhow

def es(T):
    # Saturation vapour pressure.
    #  T is the air temperature, C
    #  es is the saturation vapour pressure in kPa
    return 0.6106 * numpy.exp(17.27 * T / (T + 237.3))

def Fc_gCpm2psfromumolpm2ps(Fc_umolpm2ps):
    """
    Convert Fc in units of umol/m2/s to units of gC/m2/s
    Usage:
     Fc_mgpm2ps = Fc_gCpm2psfromumolpm2ps(Fc_umolpm2ps)
     where:
      Fc_umolpm2ps (input) - CO2 flux in units of umol/m2/s
    Returns the CO2 flux in units of gC/m2/s
    """
    # convert to masked array
    Fc_umolpm2ps, WasND = pfp_utils.SeriestoMA(Fc_umolpm2ps)
    # do the job
    Fc_gCpm2ps = Fc_umolpm2ps * c.Mc/1E3
    # convert back to ndarray if input is not a masked array
    if WasND: Fc_gCpm2ps, _ = pfp_utils.MAtoSeries(Fc_gCpm2ps)
    return Fc_gCpm2ps

def Fc_mgCO2pm2psfromumolpm2ps(Fc_umolpm2ps):
    """
    Convert Fc in units of umol/m2/s to units of mgCO2/m2/s
    Usage:
     Fc_mgCO2pm2ps = Fc_mgCO2pm2psfromumolpm2ps(Fc_umolpm2ps)
     where:
      Fc_umolpm2ps (input) - CO2 flux in units of umol/m2/s
    Returns the CO2 flux in units of mgCO2/m2/s
    """
    # convert to masked array
    Fc_umolpm2ps, WasND = pfp_utils.SeriestoMA(Fc_umolpm2ps)
    # do the job
    Fc_mgCO2pm2ps = Fc_umolpm2ps * c.Mco2
    # convert back to ndarray if input is not a masked array
    if WasND: Fc_mgCO2pm2ps, _ = pfp_utils.MAtoSeries(Fc_mgCO2pm2ps)
    return Fc_mgCO2pm2ps

def Fc_umolpm2psfrommgCO2pm2ps(Fc_mgpm2ps):
    """
    Convert Fc in units of mg/m2/s to units of umol/m2/s
    Usage:
     Fc_umolpm2ps = Fc_umolpm2psfrommgCO2pm2ps(Fc_mgpm2ps)
     where:
      Fc_mgpm2ps (input) - CO2 flux in units of mg/m2/s
    Returns the CO2 flux in units of umol/m2/s
    """
    # convert to masked array
    Fc_mgpm2ps, WasND = pfp_utils.SeriestoMA(Fc_mgpm2ps)
    # do the job
    Fc_umolpm2ps = Fc_mgpm2ps / c.Mco2
    # convert back to ndarray if input is not a masked array
    if WasND: Fc_umolpm2ps, _ = pfp_utils.MAtoSeries(Fc_umolpm2ps)
    return Fc_umolpm2ps

def h2o_gpm3frommmolpmol(h_mmpm,T,p):
    """
     Convert H2O concentration units of mmol/mol to g/m3.
        Usage:
         H2O_gpm3 = h2o_gpm3frommmolpmol(H2O_mmolpmol, T, p)
         where
         H2O_mmolpmol (input) - H2O concentration, mmol/mol
         T (input) - air temperature, C
         p (input) - air pressure, kPa
        Returns the H2O concentration in g/m3.
    """
    # convert to masked arrays
    h_mmpm, WasND = pfp_utils.SeriestoMA(h_mmpm)
    T, dummy = pfp_utils.SeriestoMA(T)
    p, dummy = pfp_utils.SeriestoMA(p)
    # do the job
    h_gpm3 = (c.Mv*h_mmpm*p*1000)/(c.R*(T+273.15))
    # convert to ndarray if input is not a masked array
    if WasND: h_gpm3, _ = pfp_utils.MAtoSeries(h_gpm3)
    return h_gpm3

def h2o_mmolpmolfromgpm3(h_gpm3,T,p):
    """
     Convert H2O concentration units of g/m3 to mmol/mol.
        Usage:
         H2O_mmolpmol = h2o_mmolpmolfromgpm3(H2O_gpm3, T, p)
         where
         H2O_gpm3 (input) - H2O concentration, g/m3
         T (input) - air temperature, C
         p (input) - air pressure, kPa
        Returns the H2O concentration in mmol/mol.
    """
    # convert to masked arrays
    h_gpm3, WasND = pfp_utils.SeriestoMA(h_gpm3)
    T, dummy = pfp_utils.SeriestoMA(T)
    p, dummy = pfp_utils.SeriestoMA(p)
    # do the job
    h_mmpm = (h_gpm3/c.Mv)*c.R*(T+273.15)/(p*1000)
    # convert to ndarray if input is not a masked array
    if WasND: h_mmpm, _ = pfp_utils.MAtoSeries(h_mmpm)
    return h_mmpm

def h2o_mmolpm3fromgpm3(h_gpm3):
    """
     Convert H2O concentration units of g/m3 to mmol/m3.
        Usage:
         H2O_mmolpm3 = h2o_mmolpm3fromgpm3(H2O_gpm3)
         where
         H2O_gpm3 (input) - H2O concentration, g/m3
        Returns the H2O concentration in mmol/m3.
    """
    # convert to masked arrays
    h_gpm3, WasND = pfp_utils.SeriestoMA(h_gpm3)
    # do the job
    h_mmolpm3 = h_gpm3/float(c.Mv)
    # convert to ndarray if input is not a masked array
    if WasND: h_mmolpm3, _ = pfp_utils.MAtoSeries(h_mmolpm3)
    return h_mmolpm3

def Lv(Ta):
    # Calculate Lv as a function of temperature, from Stull 1988
    #  Ta - air temperature, C
    # Returns
    #  Lv - latent heat of vapourisation, J/kg
    return 2500800 - (2366.8 * Ta)

def mixingratio(ps,vp):
    # Calculate mixing ratio from vapour pressure and pressure
    #  ps - presure, kPa
    #  vp - vapour pressure, kPa
    # Returns
    #  mr - mixing ratio, kg/kg
    return 0.622*vp/(ps- vp)

def molen(T,Ah,p,ustar,heatflux,fluxtype='sensible'):
    # Calculate the Monin-Obukhov length
    ustar = numpy.ma.sqrt(numpy.square(ustar))    # force the sign of ustar to be positive
    vp = vapourpressure(Ah,T)       # calculate the vapour pressure
    mr = mixingratio(p,vp)          # calculate the mixing ratio
    Tv = theta(T,p)                 # calculate potential temperature
    Tvp = virtualtheta(Tv,mr)
    if fluxtype=='sensible':
        L = -Tvp*densitydryair(T, p, vp)*c.Cp*(ustar**3)/(c.g*c.k*heatflux)
    elif fluxtype=='kinematic':
        L = -Tvp*(ustar**3)/(c.g*c.k*heatflux)
    else:
        raise Exception(" meteorologicalfunctions.molen: unkown value for fluxtype (="+str(fluxtype)+") encountered")
    return L

def qfromrh(RH, T, p):
    # Specific humidity (kg/kg) from relative humidity, temperature and pressure
    #  RH is the relative humidity, %
    #  T is the air temperature, C
    #  p is the atmospheric pressure, kPa
    qRH = (c.Mv / c.Md) * (0.01 * RH * es(T) / p)
    return qRH

def qsat(esat,ps):
    return 0.622 * (esat / ps)

def RHfromabsolutehumidity(Ah,Ta):
    # Relative humidity from absolute humidity
    #  Ta is the air temperature, C
    #  Ah is the absolute humidity, g/m3
    #  RH is the relative humidity, %
    # convert to masked arrays
    Ah, WasND = pfp_utils.SeriestoMA(Ah)
    Ta, dummy = pfp_utils.SeriestoMA(Ta)
    # do the job
    VPsat = es(Ta)
    #vp = Ah * ((Ta+273.15)*c.Rv)/float(1000000)
    vp = vapourpressure(Ah,Ta)
    RH = float(100)*vp/VPsat
    # convert back to ndarray if input is not a masked array
    if WasND: RH, _ = pfp_utils.MAtoSeries(RH)
    return RH

def RHfromdewpoint(Td,Ta):
    # Relative humidity from dew point temperature
    #  Ta is the air temperature, C
    #  Td is the dew point temperature, C
    #  RH is the relative humidity, %
    # convert to masked arrays
    Td, WasND = pfp_utils.SeriestoMA(Td)
    Ta, dummy = pfp_utils.SeriestoMA(Ta)
    # do the job
    RH = 100*10**(7.591386*(Td/(Td+240.7263)-Ta/(Ta+240.7263)))
    # convert back to ndarray if input is not a masked array
    if WasND: RH, _ = pfp_utils.MAtoSeries(RH)
    return RH

def RHfromspecifichumidity(q,Ta,ps):
    # Relative humidity from specific humidity
    #  q is the specific humidity, kg/kg
    #  Ta is the air temperature, C
    #  ps is the pressure, kPa
    #  RH is the relative humidity, %
    # convert to masked arrays
    q, WasND = pfp_utils.SeriestoMA(q)
    Ta, dummy = pfp_utils.SeriestoMA(Ta)
    # do the job
    VPsat = es(Ta)
    RH = float(100)*q*(c.Md/c.Mv)*ps/VPsat
    # convert back to ndarray if input is not a masked array
    if WasND: RH, _ = pfp_utils.MAtoSeries(RH)
    return RH

def densitytimesspecificheat(rhow,Cpw,rhoa,Cpa):
    '''
    Product of air density and specific heat capacity for moist air.
    '''
    return rhow*Cpw+rhoa*Cpa

def specificheatcapacitydryair(Tv):
    '''
    Specific heat capacity of air at constant pressure.
    USEAGE:
     cpd = pfp_mf.specificheatcapacitydryair(Tv)
    INPUT:
     Tv - virtual temperature (from sonic anemometer), C
    OUTPUT:
     cpd - specific heat capacity of dry air at constant pressure, J/kg/K
    SOURCE:
     EddyPro source code
    '''
    cpd = float(1005)+((Tv+23.12)**2)/float(3364)
    return cpd

def specificheatcapacitywatervapour(Ta, Ah):
    '''
    Specific heat capacity of water vapour at constant pressure.
    USEAGE:
     cpv = pfp_mf.specificheatcapacitywatervapour(Ta,Ah)
    INPUT:
     Ta - air temperature, C
     Ah - absolute humidity, %
    OUTPUT:
     cpv - specific heat capacity of water vapour at constant pressure, J/kg/K
    SOURCE:
     EddyPro source code
    '''
    RH = RHfromabsolutehumidity(Ah,Ta)
    cpv = float(1859)+0.13*RH+(0.193+0.0056*RH)*Ta+(0.001+0.00005*RH)*Ta**2
    return cpv

def specificheatmoistair(q):
    # Calculate Cp of moist air, from Stull 1988
    #  Cp - specific heat of dry air at constant pressure, J/kg-K
    #  q - specific humidity
    # Returns
    #  Cpm - specific heat of moist air at constant pressure, J/kg-K
    Cpm = c.Cpd * (1 + 0.84 * q)
    return Cpm

def specifichumidity(mr):
    # Calculate specific humidity from mixing ratio
    #  mr - mixing ration, kg/kg
    # Returns
    #  q = specific humidity, kg/kg
    q = mr/(1+mr)
    return q

def specifichumidityfromRH(RH, T, p):
    # Specific humidity (kg/kg) from relative humidity, temperature and pressure
    #  RH is the relative humidity, %
    #  T is the air temperature, C
    #  p is the atmospheric pressure, kPa
    # Returns
    #  q = specific humidity, kg/kg
    q = (c.Mv / c.Md) * (0.01 * RH * es(T) / p)
    return q

def tafromtv(Tv,q):
    # Calculate air temperature from virtual temperature using formula
    # from Campbell Scientific CSAT manual.
    # NOTE: this differs from the usual definition by using 0.51 not 0.61
    #  Tv - virtual temperature, C
    #  q - specific humidity, kg/kg
    # Returns
    #  Ta - air temperature, C
    Ta = ((Tv+273.15)/(1+0.51*q))-273.15
    return Ta

def theta(T,p):
    # Calculate potential temperature from air temperature and pressure
    #  T - air temperature, C
    #  p - pressure, kPa
    # Returns
    #  theta - potential temperature, K
    return (T+273.15)*(100/p)**0.286

def vapourpressure(Ah,Ta):
    # Calculate vapour pressure from absolute humidity and temperature
    #  Ah - absolute humidity, g/m3
    #  Ta - air temperature, C
    # Returns
    #  vp - vapour pressure, kPa
    vp = 0.000001*Ah*(Ta+273.15)*c.R/c.Mv
    return vp

def virtualtheta(theta_in, mr):
    # Calculate virtual potential temperature
    #  theta - potential temperature, K
    #  mr - mixing ratio, kg/kg
    # Returns
    #  Tvp - virtual potential temperature, K
    Tvp = theta_in * (1 + (0.61 * mr))
    return Tvp
