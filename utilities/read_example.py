import matplotlib.pyplot as plt
import netCDF4
import os
import pandas

def read_netcdf(nc_full_name,variable_list=[]):
    """
    Purpose:
     Read an OzFlux netCDF file and return the data in an Pandas data frame.
    Usage:
     df = qcio.nc_read_todf(nc_full_name,variable_list=variable_list)
      where nc_full_name is the full name of the netCDF file.
            variable_list (optional) is an list of variables to be read
     If variable_list is not passed, all variables in the netCDF are returned.
    Side effects:
     Returns a Pandas data frame containing the data indexed by datetime and
     a dictionary containing the global and variable attributes.
    Author: PRI using code originally written by Ian McHugh
    Date: June 2015
    """
    # check to see if the file exists
    if "http" not in nc_full_name.lower():
        if not os.path.exists(nc_full_name):
            raise Exception("read_netcdf: input file "+nc_full_name+" not found")
    # read the netCDF file
    nc_file = netCDF4.Dataset(nc_full_name,"r")
    # create a dictionary to hold the global and variable attributes
    attr = {}
    attr["global"] = {}
    attr["variable"] = {}
    # now deal with the global attributes
    gattrlist = nc_file.ncattrs()
    if len(gattrlist)!=0:
        for item in gattrlist:
            attr["global"][item] = getattr(nc_file,item)
    # get a list of Python datetimes from the xlDatetime
    time = time = nc_file.variables["time"][:]
    time_units = getattr(nc_file.variables["time"],"units")
    dates_list = list(netCDF4.num2date(time,time_units))
    # get a list of variables to read from the netCDF file
    # was a variable list passed in as variable_list?
    if len(variable_list)==0:
        # if not, get the variable list from the netCDF file contents
        variable_list = nc_file.variables.keys()
    else:
        # if so, add the QC flags to the list entered as an argument
        flag_list = []
        for item in variable_list: flag_list.append(item+"_QCFlag")
        variable_list = variable_list+flag_list
    # read the variables and attributes from the netCDF file
    # create a dictionary to hold the data
    data = {}
    # loop over the variables to be read
    for item in variable_list:
        # get the number of dimensions
        # variables in OzFlux netCDF files can have 1 (time) or 3 dimensions (time,latitude,longitude)
        ndims = len(nc_file.variables[item].shape)
        if ndims==1:
            data[item] = ncFile.variables[item][:]
        elif ndims==3:
            # drop the degenerate dimensions (latitude and longitude)
            data[item] = nc_file.variables[item][:,0,0]
        else:
            raise Exception("unrecognised number of dimensions for variable"+str(item))
        # get the variable attributes
        vattrlist = nc_file.variables[item].ncattrs()
        if len(vattrlist)!=0:
            attr["variable"][item] = {}
            for vattr in vattrlist:
                attr["variable"][item][vattr] = getattr(nc_file.variables[item],vattr)
    nc_file.close()
    # convert the dictionary to a Pandas data frame
    df = pandas.DataFrame(data,index=dates_list)
    return df,attr

# read the variables from the local netCDF file
nc_full_name = "../../Sites/Whroo/Data/Processed/all/Whroo_2011_to_2014_L6.nc"
variable_list = ['Fsd','Ta','VPD','NEE_SOLO']
print "reading local netCDF file"
df,attr = read_netcdf(nc_full_name,variable_list=variable_list)

# plot the variables
print "plotting local netCDF file"
fig = plt.figure(1)
plt.figtext(0.5,0.95,"Local file",horizontalalignment='center')
ax1 = plt.subplot(411)
ax1.plot(df.index.values,df['Fsd'])
ax2 = plt.subplot(412,sharex=ax1)
ax2.plot(df.index.values,df['Ta'])
ax3 = plt.subplot(413,sharex=ax1)
ax3.plot(df.index.values,df['VPD'])
ax4 = plt.subplot(414,sharex=ax1)
ax4.plot(df.index.values,df['NEE_SOLO'])
plt.show()

# read the variables from the remote netCDF file
nc_dap_name = "http://dap.ozflux.org.au/thredds/dodsC/ozflux/sites/Whroo/L6/Whroo_2011_to_2014_L6.nc"
variable_list = ['Fsd','Ta','VPD','NEE_SOLO']
print "reading remote netCDF file"
df,attr = read_netcdf(nc_dap_name,variable_list=variable_list)

# plot the variables
print "plotting remote netCDF file"
fig = plt.figure(2)
plt.figtext(0.5,0.95,"OPeNDAP file",horizontalalignment='center')
ax1 = plt.subplot(411)
ax1.plot(df.index.values,df['Fsd'])
ax2 = plt.subplot(412,sharex=ax1)
ax2.plot(df.index.values,df['Ta'])
ax3 = plt.subplot(413,sharex=ax1)
ax3.plot(df.index.values,df['VPD'])
ax4 = plt.subplot(414,sharex=ax1)
ax4.plot(df.index.values,df['NEE_SOLO'])
plt.show()
