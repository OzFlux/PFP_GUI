beta = 5       # "beta" value in adiabatic correction to wind profile
Cd = 840.0     # heat capacity of mineral component of soil, J/kg/K
Co = 1920.0    # heat capacity of organic component of soil, J/kg/K
Cp = 1004.67   # specific heat of dry air at constant pressure, J/kg-K
Cpd = 1004.67  # specific heat of dry air at constant pressure, J/kg-K
Cw = 4180.0    # heat capacity of water, J/kg/K
D0 = 10.       # specific humidity deficit threshold for Lasslop et al (2010) NEE expression
E0_long = 100  # long term activation energy, default value
eps = 0.0000001 # a small number for comparing floats
g = 9.81       # gravitation constant
gamma = 28     # "gamma" value in adiabatic correction to wind profile
g2kg = 1E-3    # convert grams to kilograms
k = 0.4        # von Karmans constant
Lv = 2453600   # latent heat of vapourisation, J/kg
Mc = 0.04401   # molecular weight of carbon dioxide, kg/mol
Md = 0.02897   # molecular weight of dry air, kg/mol
missing_value = -9999         # missing data value
large_value = 1E35            # large value
small_value = -1E35           # small value
Mv = 0.01802   # molecular weight of water vapour, kg/mol
mu = Md/Mv     # ratio of dry air molecular weight to water vapour molecular weight
PT100_alpha = 3.9080E-3
PT100_beta = -5.8019E-7
rho_water = 1000.0 # density of water, kg/m3
R = 8.314      # universal gas constant, Pam3/molK
Rd = 287.04    # gas constant for dry air, J/kg/K
Rv = 461.5     # gas constant for water vapour, J/kg/K
Pi = 3.14159   # Pi
sb = 5.6704E-8 # Stefan-Boltzman constant, W/m2/K4
Tref = 15.0    # reference temperature in the Lloyd-Taylor respiration equation, C
T0   = -46.02  # zero temp[erature in the Lloyd-Taylor respiration equation, C
lwVert = 0.115       # vertical path length of CSAT3, m
lwHor = 0.058      # horizontal path length of CSAT3, m
lTv = 0.115      # path length of sonic virtual temperature, m
dIRGA = 0.0095 # path diameter of LI7500 IRGA
lIRGA = 0.127  # path length of LI7500 IRGA
Tb = 1800      # 30-min period, in seconds
C2K = 273.15   # convert degrees celsius to kelvin
# dictionary of site names and time zones
tz_dict = {"adelaideriver":"Australia/Darwin",
           "alicespringsmulga":"Australia/Darwin",
           "arcturus":"Australia/Brisbane",
           "calperum":"Australia/Adelaide",
           "capetribulation":"Australia/Brisbane",
           "cowbay":"Australia/Brisbane",
           "cumberlandplains":"Australia/Sydney",
           "cup_ec":"Australia/Sydney",
           "daintree":"Australia/Brisbane",
           "dalypasture":"Australia/Darwin",
           "dalyregrowth":"Australia/Darwin",
           "dalyuncleared":"Australia/Darwin",
           "dargo":"Australia/Melbourne",
           "dryriver":"Australia/Darwin",
           "foggdam":"Australia/Darwin",
           "gingin":"Australia/Perth",
           "greatwestern":"Australia/Perth",
           "gww":"Australia/Perth",
           "howardsprings":"Australia/Darwin",
           "litchfield":"Australia/Darwin",
           "nimmo":"Australia/Sydney",
           "reddirt":"Australia/Darwin",
           "riggs":"Australia/Melbourne",
           "robson":"Australia/Brisbane",
           "samford":"Australia/Brisbane",
           "sturtplains":"Australia/Darwin",
           "titreeeast":"Australia/Darwin",
           "tumbarumba":"Australia/Canberra",
           "wallaby":"Australia/Melbourne",
           "warra":"Australia/Hobart",
           "whroo":"Australia/Melbourne",
           "wombat":"Australia/Melbourne",
           "yanco_jaxa":"Australia/Sydney"}
units_synonyms = {"Fsd":["W/m2","W+1m-2"],
                  "Fsu":["W/m2","W+1m-2"],
                  "Fld":["W/m2","W+1m-2"],
                  "Flu":["W/m2","W+1m-2"],
                  "Fn":["W/m2","W+1m-2"],
                  "Fg":["W/m2","W+1m-2"],
                  "Precip":["mm"],
                  "ps":["kPa"],
                  "RH":["%","percent"],
                  "Sws":["frac","m3/m3","m+3m-3"],
                  "Ta":["C","degC"],
                  "Ts":["C","degC"],
                  "Wd":["degT","deg","degrees"],
                  "Ws":["m/s","m+1s-1"]}