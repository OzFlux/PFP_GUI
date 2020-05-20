# standard modules
from collections import OrderedDict
import datetime
import glob
import os
import pickle
import sys
# 3rd party modules
import dateutil
import matplotlib.pyplot as plt
import numpy
import pylab
# PFP modules
if not os.path.exists("../scripts/"):
    print "portal_audit: the scripts directory is missing"
    sys.exit()
# since the scripts directory is there, try importing the modules
sys.path.append('../scripts')
import pfp_io

def do_audit_analysis(base_path):
    sites = sorted(os.listdir(base_path))
    for item in sites:
        if not os.path.isdir(os.path.join(base_path, item)):
            sites.remove(item)

    site_info = OrderedDict()
    all_sites = {"start_date":datetime.datetime(3000,1,1,0,0),
                 "end_date": datetime.datetime(2000,1,1,0,0)}
    n = 0
    for site in sites:
        portal_dir = os.path.join(base_path, site, "Data", "Portal")
        file_mask = os.path.join(portal_dir, "*.nc")
        files = glob.glob(file_mask)
        l3_name = os.path.join(portal_dir, site + "_L3")
        if os.path.isfile(l3_name):
            print "Processing ", site
            site_info[site] = {"file_name":l3_name}
            ds = qcio.nc_read_series(l3_name)
            site_info[site]["site_name"] = ds.globalattributes["site_name"]
            start_date = dateutil.parser.parse(ds.globalattributes["start_date"])
            site_info[site]["start_date"] = start_date
            end_date = dateutil.parser.parse(ds.globalattributes["end_date"])
            site_info[site]["end_date"] = end_date
            site_info[site]["X"] = numpy.array([start_date, end_date])
            site_info[site]["Y"] = numpy.array([n+1, n+1])
            n = n + 1
            all_sites["start_date"] = min([all_sites["start_date"], site_info[site]["start_date"]])
            all_sites["end_date"] = max([all_sites["end_date"], site_info[site]["end_date"]])

    with open('audit_analysis.pickle', 'wb') as handle:
        pickle.dump([all_sites, site_info], handle, protocol=pickle.HIGHEST_PROTOCOL)

    return all_sites, site_info

base_path = "/mnt/OzFlux/Sites/"
do_it = True

if do_it:
    all_sites, site_info = do_audit_analysis(base_path)
else:
    with open('audit_analysis.pickle', 'rb') as handle:
        l = pickle.load(handle)
        all_sites = l[0]
        site_info = l[1]
end_year = all_sites["end_date"].year
all_sites["end_date"] = datetime.datetime(end_year+1, 1, 1, 0, 0)
site_list = site_info.keys()
ylabel_list = [""]+site_list+[""]
color_list = ["blue", "red", "green", "yellow", "magenta", "black", "orange", "brown"]
xsize = 15.0
ysize = max([len(site_list)*0.2, 1])
# plot all sites
fig = plt.figure(figsize=(xsize, ysize))
plt.ylim([0, len(site_list)+1])
plt.xlim([all_sites["start_date"], all_sites["end_date"]])
for n, site in enumerate(site_list):
    plt.plot(site_info[site]["X"], site_info[site]["Y"], color=color_list[numpy.mod(n,8)], linewidth=4)
ylabel_posn = range(0, len(site_list)+2)
pylab.yticks(ylabel_posn, ylabel_list)
fig.tight_layout()
#plt.show()
# plot active sites
active_sites = ["AliceSpringsMulga", "Calperum", "CumberlandPlain", "DalyUncleared", "DryRiver",
                "Gingin", "GreatWesternWoodlands", "HowardSprings", "Litchfield", "Ridgefield",
                "RobsonCreek", "Samford", "SturtPlains", "TiTreeEast", "Tumbarumba", "Warra",
                "Whroo", "WombatStateForest", "Yanco"]
ylabel_list = [""]+active_sites+[""]
fig = plt.figure(figsize=(xsize, ysize))
plt.ylim([0, len(active_sites)+1])
plt.xlim([all_sites["start_date"], all_sites["end_date"]])
for n, site in enumerate(active_sites):
    plt.plot(site_info[site]["X"], [n+1, n+1], color=color_list[numpy.mod(n,8)], linewidth=4)
ylabel_posn = range(0, len(active_sites)+2)
pylab.yticks(ylabel_posn, ylabel_list)
fig.tight_layout()

plt.show()

print "All done"