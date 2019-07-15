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

def get_seasonal_results(contents):
    # get the seasonal values
    season_values = numpy.array([float(s) for s in contents[2].split()])
    season_counts = numpy.array([int(s) for s in contents[3].split()])
    return {"value": season_values, "count": season_counts}

def get_annual_results(contents):
    # get the annual values
    season_values = numpy.array([float(s) for s in contents[2].split()])
    season_counts = numpy.array([int(s) for s in contents[3].split()])
    annual_values = numpy.max(season_values)
    annual_counts = numpy.sum(season_counts)
    return {"value": annual_values, "count": annual_counts}

def get_temperature_class_results(contents):
    # get the seasonal results by temperature class
    temperature_classes = {}
    for i, n in enumerate(range(7, 14)):
        temperature_classes[i] = {}
        temperature_classes[i]["values"] = numpy.array([float(s) for s in contents[n].split()])
        temperature_classes[i]["counts"] = numpy.zeros(len(temperature_classes[i]["values"]))
    return temperature_classes

def get_bootstrap_results(contents):
    # get the individual bootstrap results
    bootstrap_results = {}
    bootstrap_values = {}
    bootstrap_counts = {}
    n = 17
    season_values = numpy.array([float(s) for s in contents[n][:contents[n].index("forward")].split()])
    number_seasons = len(season_values)
    for i in range(0, number_seasons):
        bootstrap_values[i] = numpy.array([])
        bootstrap_counts[i] = numpy.array([])
    # on Windows machines, len(contents[n]) == 1 for the first empty line after thhe bootstrap section
    while len(contents[n]) > 1:
        season_values = numpy.array([float(s) for s in contents[n][0:contents[n].index("forward")].split()])
        season_counts = numpy.array([int(s) for s in contents[n+1][0:].split()])
        for i in range(0, number_seasons):
            bootstrap_values[i] = numpy.append(bootstrap_values[i], season_values[i])
            bootstrap_counts[i] = numpy.append(bootstrap_counts[i], season_counts[i])
        n = n + 2
    for i in range(0, number_seasons):
        bootstrap_results[i] = {}
        bootstrap_results[i]["values"] = bootstrap_values[i]
        bootstrap_results[i]["counts"] = bootstrap_counts[i]
    return bootstrap_results

def make_data_array(ds, current_year):
    ldt = pfp_utils.GetVariable(ds, "DateTime")
    nrecs = ds.globalattributes["nc_nrecs"]
    ts = int(ds.globalattributes["time_step"])
    start = datetime.datetime(current_year,1,1,0,30,0)
    end = datetime.datetime(current_year+1,1,1,0,0,0)
    cdt = numpy.array([dt for dt in pfp_utils.perdelta(start, end, datetime.timedelta(minutes=ts))])
    mt = numpy.ones(len(cdt))*float(-9999)
    data = numpy.stack([cdt, mt, mt, mt, mt, mt, mt, mt], axis=-1)
    si = pfp_utils.GetDateIndex(ldt["Data"], start, default=0)
    ei = pfp_utils.GetDateIndex(ldt["Data"], end, default=nrecs)
    dt = pfp_utils.GetVariable(ds, "DateTime", start=si, end=ei)
    idx1, idx2 = pfp_utils.FindMatchingIndices(cdt, dt["Data"])
    for n, label in enumerate(["Fc", "VPD", "ustar", "Ta", "Fsd", "Fh", "Fe"]):
        var = pfp_utils.GetVariable(ds, label, start=si, end=ei)
        data[idx1,n+1] = var["Data"]
    # convert datetime to ISO dates
    data[:,0] = numpy.array([int(xdt.strftime("%Y%m%d%H%M")) for xdt in cdt])
    return data

def mpt_main(cf):
    base_file_path = cf["Files"]["file_path"]
    nc_file_name = cf["Files"]["in_filename"]
    nc_file_path = os.path.join(base_file_path, nc_file_name)
    ds = pfp_io.nc_read_series(nc_file_path)
    out_file_paths = run_mpt_code(ds, nc_file_name)
    ustar_results = read_mpt_output(out_file_paths)
    mpt_file_path = nc_file_path.replace(".nc", "_MPT.xls")
    xl_write_mpt(mpt_file_path, ustar_results)
    return

def run_mpt_code(ds, nc_file_name):
    ldt = pfp_utils.GetVariable(ds, "DateTime")
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
        msg = " MPT: processing year " + str(current_year)
        logger.info(msg)
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

#def read_mpt_output(out_file_paths):
    #ustar_results = {"Annual":{}, "Years":{}}
    #seasons = ["Summer", "Autumn", "Winter", "Spring"]
    #ura = ustar_results["Annual"]
    #ury = ustar_results["Years"]
    #year_list = sorted(out_file_paths.keys())
    #for year in year_list:
        #ury[year] = {}
        #out_file_path = out_file_paths[year]
        #with open(out_file_path) as file:
            #lines = file.readlines()
        ## pick out the annual data
        #season_values = lines[2].strip().split()
        #season_count = lines[3].strip().split()
        ## entry 0 for the year is the observation run, 1 onwards are bootstraps
        #ury[year][0] = {}
        #for i in range(len(season_values)):
            #ury[year][0][seasons[i]] = {"value":float(season_values[i]),"count":int(season_count[i])}
        #annual_value = max([ury[year][0][season]["value"] for season in ury[year][0].keys()])
        #annual_count = sum([ury[year][0][season]["count"] for season in ury[year][0].keys()])
        #ura[year] = {"value":annual_value,"count":annual_count}
        #n = 17
        #i = 1
        #while len(lines[n].strip()) > 0:
            #ury[year][i] = {}
            #if "forward" in lines[n]:
                #lines[n] = lines[n][:lines[n].index("forward")]
            #season_values = lines[n].strip().split()
            #season_count = lines[n+1].strip().split()
            #for j in range(len(season_values)):
                #ury[year][i][seasons[j]] = {"value":float(season_values[j]),"count":int(season_count[j])}
            #n += 2
            #i += 1
    #return ustar_results

def read_mpt_output(out_file_paths):
    ustar_results = {"Annual":{}, "Years":{}}
    seasons = ["Summer", "Autumn", "Winter", "Spring"]
    ura = ustar_results["Annual"]
    ury = ustar_results["Years"]
    year_list = sorted(out_file_paths.keys())
    for year in year_list:
        ury[year] = {}
        out_file_path = out_file_paths[year]
        with open(out_file_path) as mpt_file:
            contents = [l.rstrip('\n') for l in mpt_file.readlines()]
        # check the first line to make sure it is what we expect
        if not "ustar threshold by season" in contents[0] or not "bootstrapping" in contents[15]:
            msg = "MPT: unexpected contents in MPT output file"
            logger.error(msg)
            return ustar_results
        ury[year]["seasonal"] = get_seasonal_results(contents)
        ury[year]["annual"] = get_annual_results(contents)
        ury[year]["temperature_classes"] = get_temperature_class_results(contents)
        ury[year]["bootstraps"] = get_bootstrap_results(contents)        
    return ustar_results

def write_mpt_year_results(xl_sheet, mpt_results):
    # write the seasonal results
    row = 0
    # write the headers
    for col, item in enumerate(["Seasonal", "Values", "Counts", "Stdev"]):
        xl_sheet.write(row, col, item)
    # write the data
    for n in range(len(mpt_results["seasonal"]["value"])):
        row = row + 1
        xl_sheet.write(row, 0, n)
        xl_sheet.write(row, 1, mpt_results["seasonal"]["value"][n])
        xl_sheet.write(row, 2, mpt_results["seasonal"]["count"][n])
        values = mpt_results["bootstraps"][n]["values"]
        values = numpy.ma.masked_values(values, -9999)
        if numpy.ma.count(values) > 0:
            xl_sheet.write(row, 3, numpy.ma.std(values))
    # write the temperature class results
    row = 10
    # write the headers
    number_seasons = len(mpt_results["bootstraps"].keys())
    header_list = ["Temperature classes"]
    for s in range(number_seasons):
        header_list.append(str(s))
    for col, item in enumerate(header_list):
        xl_sheet.write(row, col, item)
    # write the data
    for i in range(len(mpt_results["temperature_classes"].keys())):
        row = row + 1
        xl_sheet.write(row, 0, i)
        for j in range(len(mpt_results["temperature_classes"][0]["values"])):
            xl_sheet.write(row, j+1, mpt_results["temperature_classes"][i]["values"][j])
    # write the bootstrap results
    row = 20
    # write the headers
    header1_list = ["Seasons"]
    header2_list = ["Bootstraps"]
    for s in range(number_seasons):
        header1_list.append(str(s))
        header1_list.append(str(s))
        header2_list.append("Values")
        header2_list.append("Counts")
    for col, item in enumerate(header1_list):
        xl_sheet.write(row, col, item)
    row = row + 1
    for col, item in enumerate(header2_list):
        xl_sheet.write(row, col, item)
    # write the data
    number_bootstraps = len(mpt_results["bootstraps"][0]["values"])
    for n in range(number_bootstraps):
        row = row + 1
        col = 0
        xl_sheet.write(row, col, n)
        for s in range(number_seasons):
            col = col + 1
            xl_sheet.write(row, col, mpt_results["bootstraps"][s]["values"][n])
            col = col + 1
            xl_sheet.write(row, col, mpt_results["bootstraps"][s]["counts"][n])
    return

def xl_write_mpt(mpt_full_path, ustar_results):
    year_list = sorted(ustar_results["Years"].keys())
    xl_file = xlwt.Workbook()
    xl_sheet = xl_file.add_sheet("Annual")
    xl_sheet.write(0, 0,"Year")
    xl_sheet.write(0, 1,"ustar_mean")
    xl_sheet.write(0, 2,"ustar_sig")
    for n, year in enumerate(year_list):
        xl_sheet.write(n+1, 0, year)
        if ustar_results["Years"][year]["annual"]["value"] != -9999:
            xl_sheet.write(n+1, 1, ustar_results["Years"][year]["annual"]["value"])
            season_list = ustar_results["Years"][year]["bootstraps"].keys()
            values = ustar_results["Years"][year]["bootstraps"][0]["values"]
            season_list.remove(0)
            for s in season_list:
                values = numpy.concatenate((values, ustar_results["Years"][year]["bootstraps"][s]["values"]))
            values = numpy.ma.masked_values(values, -9999)
            xl_sheet.write(n+1, 2, numpy.ma.std(values))
    for year in year_list:
        xl_sheet = xl_file.add_sheet(str(year))
        write_mpt_year_results(xl_sheet, ustar_results["Years"][year])
    xl_file.save(mpt_full_path)
    return
