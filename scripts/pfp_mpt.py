# standard Python modules
import datetime
import logging
import os
import subprocess
# 3rd party
import numpy
import xlwt
# PFP modules
import pfp_io
import pfp_utils

logger = logging.getLogger("pfp_log")

def make_data_array(ds, current_year):
    ldt = qcutils.GetVariable(ds, "DateTime")
    nrecs = ds.globalattributes["nc_nrecs"]
    ts = int(ds.globalattributes["time_step"])
    start = datetime.datetime(current_year,1,1,0,30,0)
    end = datetime.datetime(current_year+1,1,1,0,0,0)
    cdt = numpy.array([dt for dt in qcutils.perdelta(start, end, datetime.timedelta(minutes=ts))])
    mt = numpy.ones(len(cdt))*float(-9999)
    data = numpy.stack([cdt, mt, mt, mt, mt, mt, mt, mt], axis=-1)
    si = qcutils.GetDateIndex(ldt["Data"], start, default=0)
    ei = qcutils.GetDateIndex(ldt["Data"], end, default=nrecs)
    dt = qcutils.GetVariable(ds, "DateTime", start=si, end=ei)
    idx1, idx2 = qcutils.FindMatchingIndices(cdt, dt["Data"])
    for n, label in enumerate(["Fc", "VPD", "ustar", "Ta", "Fsd", "Fh", "Fe"]):
        var = qcutils.GetVariable(ds, label, start=si, end=ei)
        data[idx1,n+1] = var["Data"]
    # convert datetime to ISO dates
    data[:,0] = numpy.array([int(xdt.strftime("%Y%m%d%H%M")) for xdt in cdt])
    return data

def mpt_main(cf):
    base_file_path = cf["Files"]["file_path"]
    nc_file_name = cf["Files"]["in_filename"]
    nc_file_path = os.path.join(base_file_path, nc_file_name)
    ds = qcio.nc_read_series(nc_file_path)
    out_file_paths = run_mpt_code(ds, nc_file_name)
    ustar_results = read_mpt_output(out_file_paths)
    mpt_file_path = nc_file_path.replace(".nc", "_MPT.xls")
    xl_write_mpt(mpt_file_path, ustar_results)
    return

def run_mpt_code(ds, nc_file_name):
    ldt = qcutils.GetVariable(ds, "DateTime")
    out_file_paths = {}
    header = "TIMESTAMP,NEE,VPD,USTAR,TA,SW_IN,H,LE"
    fmt = "%12i,%f,%f,%f,%f,%f,%f,%f"
    first_year = ldt["Data"][0].year
    last_year = ldt["Data"][-1].year
    log_file_path = os.path.join("mpt", "log", "mpt.log")
    mptlogfile = open(log_file_path, "wb")
    in_base_path = os.path.join("mpt", "input", "")
    out_base_path = os.path.join("mpt", "output", "")
    for current_year in range(first_year, last_year+1):
        in_name = nc_file_name.replace(".nc","_"+str(current_year)+"_MPT.csv")
        in_full_path = os.path.join(in_base_path, in_name)
        out_full_path = in_full_path.replace("input", "output").replace(".csv", "_ut.txt")
        data = make_data_array(ds, current_year)
        numpy.savetxt(in_full_path, data, header=header, delimiter=",", comments="", fmt=fmt)
        ustar_mp_exe = os.path.join(".", "mpt", "bin", "ustar_mp")
        cmd = [ustar_mp_exe, "-input_path="+in_full_path, "-output_path="+out_base_path]
        subprocess.call(cmd, stdout=mptlogfile)
        if os.path.isfile(out_full_path):
            out_file_paths[current_year] = out_full_path
    mptlogfile.close()
    return out_file_paths

def read_mpt_output(out_file_paths):
    ustar_results = {"Annual":{}, "Years":{}}
    seasons = ["Summer", "Autumn", "Winter", "Spring"]
    ura = ustar_results["Annual"]
    ury = ustar_results["Years"]
    year_list = sorted(out_file_paths.keys())
    for year in year_list:
        ury[year] = {}
        out_file_path = out_file_paths[year]
        with open(out_file_path) as file:
            lines = file.readlines()
        # pick out the annual data
        season_values = lines[2].strip().split()
        season_count = lines[3].strip().split()
        # entry 0 for the year is the observation run, 1 onwards are bootstraps
        ury[year][0] = {}
        for i in range(len(season_values)):
            ury[year][0][seasons[i]] = {"value":float(season_values[i]),"count":int(season_count[i])}
        annual_value = max([ury[year][0][season]["value"] for season in ury[year][0].keys()])
        annual_count = sum([ury[year][0][season]["count"] for season in ury[year][0].keys()])
        ura[year] = {"value":annual_value,"count":annual_count}
        n = 17
        i = 1
        while len(lines[n].strip()) > 0:
            ury[year][i] = {}
            if "forward" in lines[n]:
                lines[n] = lines[n][:lines[n].index("forward")]
            season_values = lines[n].strip().split()
            season_count = lines[n+1].strip().split()
            for j in range(len(season_values)):
                ury[year][i][seasons[j]] = {"value":float(season_values[j]),"count":int(season_count[j])}
            n += 2
            i += 1
    return ustar_results

def xl_write_mpt(mpt_full_path, ustar_results):
    year_list = sorted(ustar_results["Annual"].keys())
    xl_file = xlwt.Workbook()
    xl_sheet = xl_file.add_sheet("Annual")
    xl_sheet.write(0, 0,"Year")
    xl_sheet.write(0, 1,"ustar_mean")
    for n, year in enumerate(year_list):
        xl_sheet.write(n+1, 0, year)
        if ustar_results["Annual"][year]["value"] != -9999:
            xl_sheet.write(n+1, 1, ustar_results["Annual"][year]["value"])
    xl_file.save(mpt_full_path)
    return
