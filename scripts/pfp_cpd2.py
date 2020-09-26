# standard modules
import datetime
import logging
import os
import time
# 3rd party modules
import numpy
import scipy
import scipy.stats
import statsmodels.api as sm
import xlwt
# PFP modules
import pfp_io
import pfp_ts
import pfp_utils

# get the logger
logger = logging.getLogger("pfp_log")

def cpd2_main(cf):
    """
    Purpose:
    Usage:
    Side effects:
    Author: PRI
    Date: November 2019
    """
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "Num_bootstraps", default=100)
    nBoot = int(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "Fsd_threshold", default=5)
    Fsd_threshold = float(opt)
    opt = pfp_utils.get_keyvaluefromcf(cf, ["Options"], "ApplyFcStorage", default="No")
    apply_storage = True
    if opt.lower() != "yes":
        apply_storage = False
    fPlot = 0
    # Set input file and output path and create directories for plots and results
    path_out = cf["Files"]["file_path"]
    file_in = os.path.join(cf["Files"]["file_path"], cf["Files"]["in_filename"])
    if "out_filename" in cf["Files"]:
        file_out = os.path.join(cf["Files"]["file_path"], cf["Files"]["out_filename"])
    else:
        file_name = cf["Files"]["in_filename"].replace(".nc", "_CPD_Barr.xls")
        file_out = os.path.join(cf["Files"]["file_path"], file_name)
    plot_path = "plots/"
    if "plot_path" in cf["Files"]:
        plot_path = os.path.join(cf["Files"]["plot_path"], "CPD/")
    if not os.path.isdir(plot_path):
        os.makedirs(plot_path)
    results_path = path_out
    if not os.path.isdir(results_path):
        os.makedirs(results_path)
    # get a dictionary of the variable names
    var_list = cf["Variables"].keys()
    names = {}
    for item in var_list:
        if "name" in cf["Variables"][item].keys():
            names[item] = cf["Variables"][item]["name"]
        else:
            names[item] = item
        msg = " CPD (Barr): Using variable " + names[item] + " for " + item
        logger.info(msg)
    # read the netcdf file
    logger.info(" Reading netCDF file " + file_in)
    ds = pfp_io.nc_read_series(file_in)
    if ds.returncodes["value"] != 0: return
    # get the single-point storage, Fc_single, if available
    if apply_storage and "Fc_storage" not in ds.series.keys():
        pfp_ts.CalculateFcStorageSinglePoint(cf, ds, Fc_out="Fc_single")
        Fc_single = pfp_utils.GetVariable(ds, "Fc_single")
        Fc_single["Label"] = "Fc_storage"
        pfp_utils.CreateVariable(ds, Fc_single)
    cSiteYr = ds.globalattributes["site_name"]
    ts = int(ds.globalattributes["time_step"])
    dt = pfp_utils.GetVariable(ds, "DateTime")
    ustar_results = {}
    years = sorted(list(set([ldt.year for ldt in dt["Data"]])))
    msg = " Starting CPD analysis for " + str(years)
    logger.info(msg)
    pb = {"nYears": len(years), "n": 0}
    for n, year in enumerate(years):
        pb["n"] = n + 1
        ustar_results[year] = {}
        start = datetime.datetime(year, 1, 1, 0, 0) + datetime.timedelta(minutes=ts)
        end = datetime.datetime(year+1, 1, 1, 0, 0)
        Fsd = pfp_utils.GetVariable(ds, names["Fsd"], start=start, end=end, out_type="nan")
        Fc = pfp_utils.GetVariable(ds, names["Fc"], start=start, end=end, out_type="nan")
        ustar = pfp_utils.GetVariable(ds, names["ustar"], start=start, end=end, out_type="nan")
        Ta = pfp_utils.GetVariable(ds, names["Ta"], start=start, end=end, out_type="nan")
        if start < Fsd["DateTime"][0] or end > Fsd["DateTime"][-1]:
            Fsd = pfp_utils.PadVariable(Fsd, start, end, out_type="nan")
            Fc = pfp_utils.PadVariable(Fc, start, end, out_type="nan")
            ustar = pfp_utils.PadVariable(ustar, start, end, out_type="nan")
            Ta = pfp_utils.PadVariable(Ta, start, end, out_type="nan")
        # if requested, apply storage
        if apply_storage:
            label = cf["Variables"]["Fc"]["name"]
            msg = " CPD2: Applying Fc_stoage to " + label
            logger.info(msg)
            pfp_ts.CorrectFcForStorage(cf, ds, Fc_out=label, Fc_in=label, Fc_storage_in="Fc_storage")
        # get the day/night indicator, fNight is 1 for night time, 0 for day time
        fNight = numpy.where(Fsd["Data"] < Fsd_threshold, 1, 0)
        # get a time series
        nrPerDay = numpy.mod(len(ustar["Data"]), 365)
        if nrPerDay == 0:
            nrPerDay = numpy.mod(len(ustar["Data"]), 364)
        first = 1 + float(1)/float(nrPerDay)
        last = float(len(ustar["Data"]))/float(nrPerDay) + 1
        t = numpy.linspace(first, last, len(ustar["Data"]))
        # call the bootstrap routine
        Cp2, Stats2, Cp3, Stats3 = cpdBootstrapUStarTh4Season20100901(t, Fc["Data"], ustar["Data"],
                                                                      Ta["Data"], fNight, fPlot,
                                                                      cSiteYr, nBoot, pb)
        # call the QC routine
        Cp, n, tW, CpW, cMode, cFailure, fSelect, sSine, FracSig, FracModeD, FracSelect = \
            cpdAssignUStarTh20100901(Stats2,fPlot,cSiteYr)
        ustar_results[year]["ustar_mean"] = numpy.nanmean(Cp)
        ustar_results[year]["ustar_sig"] = numpy.nanstd(Cp)
        ustar_results[year]["bootstraps"] = Cp
        msg = "  Finished CPD analysis for year " + str(year)
        logger.info(msg)
    xl_write_cpd(file_out, ustar_results)
    return

def xl_write_cpd(cpd_full_path, ustar_results):
    """
    Purpose:
    Usage:
    Side effects:
    Author: PRI
    Date: November 2019
    """
    years = sorted(ustar_results.keys())
    xl_file = xlwt.Workbook()
    xl_sheet = xl_file.add_sheet("Annual")
    xl_sheet.write(0, 0,"Year")
    xl_sheet.write(0, 1,"ustar_mean")
    xl_sheet.write(0, 2,"ustar_sig")
    for n, year in enumerate(years):
        xl_sheet.write(n+1, 0, year)
        xl_sheet.write(n+1, 1, ustar_results[year]["ustar_mean"])
        xl_sheet.write(n+1, 2, ustar_results[year]["ustar_sig"])
    for year in years:
        xl_sheet = xl_file.add_sheet(str(year))
        xl_sheet.write(0, 0, "Bootstraps")
        xl_sheet.write(0, 1, "Values")
        bootstraps = len(ustar_results[year]["bootstraps"])
        for n in range(bootstraps):
            xl_sheet.write(n+1, 0, n)
            xl_sheet.write(n+1, 1, ustar_results[year]["bootstraps"][n])
    xl_file.save(cpd_full_path)
    return

def cpdBootstrapUStarTh4Season20100901(t, NEE, uStar, T, fNight, fPlot, cSiteYr, nBoot, pb):
    """
    cpdBootstrapUStarTh4Season20100901

    is a simplified operational version of

    20100901 changes 3A 4I to 2A 3I as sggested by Xiaolan Wang.

    20100408 replaces 20100318, updating ChPt function from:
     FindChangePointMod3LundReeves2002_20100318 to
     FindChangePointMod2A4ILundReeves2002_20100408.
     which: adds back A model, makes a correction to the significance test,
     and adds a comparison of the 4- versus 3-parameter models.
     and adds a comparison of the 4- versus 3-parameter models.

     20100318 new version with small tweaks to FindChangePoint
     also adds mT and ciT to Stats structures.

     is a new working implementation of Alan's u*Th evaluation algorithm
     based on Lund and Reeves' (2002) modified by Wang's (2003) change-point
     detection algorithm.

     Relationship to other programs:

     Called by batchNewNacpEstimateUStarTh_Moving_Mod3LundChPt_20100115
      - script which identifies which sites to process
     Calls newNacpEvaluateUStarTh_MovingStrat_20100114
      - function that processes an individual year of data, using
        FindChangePointMod3LundReeves2002_20091204

     This implementation may supplant all previous versions.

     It uses moving windows of fixed size to evaluate seasonal variation.

     Three combinations of stratification and pooling are implemented.
      - All begin with 2D (time x temperature) stratification
        (moving-window time x n temperature classes within each window).
      - Two (W and A) add normalization and pooling.

     1. Method S (full stratification)
        estimates the change-points for each of the strata
        (nWindows x nTClasses) with no need for normalization.
     2. Method W (pooling within time windows)
        begins with a variant of S but pools the temperature classes
        within each time window before estimating one change-point per window.
        Before pooling, the binned mean NEE data within each temperature class
        are normalized against the 80th NEE percentile for that class.
     3. Method A (pooling to annual)
        further pools the pooled normalized data from W over all time windows
        before estimating a single change-point per year.

     The detailed analysis parameters are output in a Stats structured
     record.

     ========================================================================
     ========================================================================

     Functions called:
      cpdEvaluateUStarTh20100901
      fcx2roevec
      stats toolbox:  nanmedian

     Written by Alan Barr 15 Jan 2010.
     Translated to Python by PRI September 2019.
     ========================================================================
     ========================================================================
    """
    nt = len(t)
    nPerDay = int(round(1 / numpy.median(numpy.diff(t))))
    iNight = numpy.where(fNight == 1)[0]
    iOut = numpy.where((uStar < 0) | (uStar > 4))[0]
    uStar[iOut] = numpy.nan
    nSeasons = 4
    nStrataN = 4
    nStrataX = 8
    nBins = 50
    nPerBin = 5
    if nPerDay == 24:
        nPerBin = 3
    nPerSeason = nStrataN*nBins*nPerBin
    ntN = nSeasons*nPerSeason

    itNee = numpy.where(~numpy.isnan(NEE + uStar + T))[0]
    itNee = numpy.intersect1d(itNee, iNight)
    ntNee = len(itNee)
    Cp2 = numpy.full((nSeasons, nStrataX, nBoot), numpy.nan)
    Cp3 = numpy.full((nSeasons, nStrataX, nBoot), numpy.nan)
    # Stats2 and Stats3 as dictionaries
    stat_labels = ['ciT', 'mt', 'Fmax', 'puStarVsT', 'ruStarVsT', 'mT', 'n', 'p',
                   'cib0', 'cib1', 'b0', 'b1', 'b2', 'ti', 'tf', 'c2', 'Cp', 'cic2']
    Stats2 = {}
    Stats3 = {}
    for iBoot in range(nBoot):
        Stats2[iBoot] = {}
        Stats3[iBoot] = {}
        for iSeason in range(nSeasons):
            Stats2[iBoot][iSeason] = {}
            Stats3[iBoot][iSeason] = {}
            for iStrata in range(nStrataX):
                Stats2[iBoot][iSeason][iStrata] = {}
                Stats3[iBoot][iSeason][iStrata] = {}
                for stat in stat_labels:
                    Stats2[iBoot][iSeason][iStrata][stat] = numpy.nan
                    Stats3[iBoot][iSeason][iStrata][stat] = numpy.nan
    if ntNee >= ntN:
        for iBoot in range(nBoot):
            if iBoot == 0:
                it = numpy.linspace(0, nt-1, nt).astype(int)
            else:
                it = numpy.sort(numpy.random.randint(0, nt, nt))
            if iBoot > 0:
                fPlot = 0

            #print "Calling cpdEvaluateUStarTh4Season20100901"
            t0 = time.time()
            xCp2, xStats2, xCp3, xStats3 = cpdEvaluateUStarTh4Season20100901(t[it], NEE[it], uStar[it],
                                                                             T[it], fNight[it],
                                                                             fPlot, cSiteYr)
            #print "cpdEvaluateUStarTh4Season20100901 took " + str(time.time() - t0)

            Cp2[:, :, iBoot] = xCp2
            Stats2[iBoot] = xStats2
            Cp3[:, :, iBoot] = xCp3
            Stats3[iBoot] = xStats3

            progress = float((pb["n"]-1)*nBoot+iBoot+1)/float(pb["nYears"]*nBoot)
            pfp_utils.update_progress(progress)

    else:
        #print "cpdBootstrapUStarTh4Season: insufficient points"
        logger.info("cpdBootstrapUStarTh4Season: insufficient points")
    return Cp2, Stats2, Cp3, Stats3

def cpdEvaluateUStarTh4Season20100901(t, NEE, uStar, T, fNight, fPlot, cSiteYr):
    """
    nacpEvaluateUStarTh4Season20100901
    estimates uStarTh for a site-year of data using change-point
    detection (cpd) methods implemented within the general framework
    of the Papale et al. (2006) uStarTh evaluation method.

    Syntax:
     [Cp2,Stats2,Cp3,Stats3] = ...
      cpdEvaluateUStarTh20100901(t,NEE,uStar,T,fNight,fPlot,cSiteYr)
     where:
      - Cp2 and Cp3 are nW x nT matrices containing change-point
        uStarTh estimates from the 2-parameter operational
        and 3-parameter diagnostic models
      - Stats2 and Stats3 are structured records containing the corresponding
        nW x nT matrices of cpd statistics.
      - t is the time vector
      - NEE, uStar and T (temperature)
      - fNight is a vector specifying day (0) or night (1)
      - fPlot is a scalar flag that is set high (1) to plot
      - cSiteYr is a text string used in the plot title

    The analysis is based on one year of data.  The year is stratified
    by time of year and temperature into nW by nT strata, each with a
    fixed number of data.
    The uStarTh is estimated independently for each stratum, using two
    change-point models: the 2-parameter operational and 3-parameter
    diagnostic models.

    The primary modification Papale et al. (2006) is the use of
    change-point detection (cpd) rather than a moving point test
    to evaluate the uStarTh.  The cpd method is adopted from
    Lund and Reeves (2002) and Wang (2003).

    Relationship to other programs:
        1. cpdBootstrapUStarTh20100901
            - function which processes specified sites including bootstrapping
              and data output.
    calls
        2. CPDEvaluateUStarTh20100901
            - function that processes an individual year of data
    calls
        3. cpdFindChangePoint20100901 (change-point detection function).
    Functions called:
     cpdFindChangePoint20100901
     fcBin, fcDatevec, fcDoy
     stats toolbox:  nanmedian, prctile, regress

    Written by Alan Barr 15 Jan 2010.
    Translated to Python by PRI September 2019.
    """
    # Initializations
    nt = len(t)
    Y, M, D, h, m, s = mydatevec(t)
    # mydatevec returns float because it uses numpy.nan
    iYr = int(numpy.median(Y))
    dn = mydatenum(iYr, 12, 31, 12, 0, 0)
    EndDOY = mydoy(dn)
    nPerDay = int(round(1 / numpy.median(numpy.diff(t))))
    nSeasons = 4
    nStrataN = 4
    nStrataX = 8
    nBins = 50
    nPerBin = 5
    if nPerDay == 24:
        nPerBin = 3
    nPerSeasonN = nStrataN*nBins*nPerBin
    nN = nSeasons*nPerSeasonN
    itOut = numpy.where((uStar[~numpy.isnan(uStar)] < 0) | (uStar[~numpy.isnan(uStar)] > 3))[0]
    uStar[itOut] = numpy.nan
    itAnnual = numpy.where((fNight == 1) & (~numpy.isnan(NEE+uStar+T)))[0]
    ntAnnual = len(itAnnual)
    # Initialize outputs, Cp2 and Cp3 as numpy arrays.
    Cp2 = numpy.full((nSeasons, nStrataX), numpy.nan)
    Cp3 = numpy.full((nSeasons, nStrataX), numpy.nan)
    # Stats2 and Stats3 as dictionaries
    stat_labels = ['ciT', 'mt', 'Fmax', 'puStarVsT', 'ruStarVsT', 'mT', 'n', 'p',
                   'cib0', 'cib1', 'b0', 'b1', 'b2', 'ti', 'tf', 'c2', 'Cp', 'cic2']
    Stats2 = {}
    Stats3 = {}
    for iSeason in range(nSeasons):
        Stats2[iSeason] = {}
        Stats3[iSeason] = {}
        for iStrata in range(nStrataX):
            Stats2[iSeason][iStrata] = {}
            Stats3[iSeason][iStrata] = {}
            for stat in stat_labels:
                Stats2[iSeason][iStrata][stat] = numpy.nan
                Stats3[iSeason][iStrata][stat] = numpy.nan
    if ntAnnual < nN:
        #print "cpdEvaluateUStarTh4Season: ntAnnual less than nN ", ntAnnual, nN
        msg = "  cpdEvaluateUStarTh4Season: ntAnnual (" + str(ntAnnual)
        msg += ") less than nN (" + str(nN) + ")"
        logger.info(msg)
        return Cp2, Stats2, Cp3, Stats3
    # Octave has ntAnnual, nSeasons and nPerSeason as floats
    # then round(1040.5) ==> 1041.0
    nPerSeason = round(float(ntAnnual) / float(nSeasons))
    # Move December to beginning of year and date as previous year.
    itD = numpy.where(M == 12)[0]
    itReOrder = numpy.concatenate([range(min(itD), nt), range(0, (min(itD)))])
    # PRI Spetember 2019 - I don't think this works as intended using t as generated
    t[itD] = t[itD] - EndDOY
    t = t[itReOrder]
    T = T[itReOrder]
    uStar = uStar[itReOrder]
    NEE = NEE[itReOrder]
    fNight = fNight[itReOrder]
    itAnnual = numpy.where((fNight == 1) & (~numpy.isnan(NEE + uStar + T)))[0]
    ntAnnual = len(itAnnual)
    # Reset nPerSeason and nInc based on actual number of good data.
    # nSeasons is a temporary variable.
    nSeasons = round(float(ntAnnual) / float(nPerSeason))
    nPerSeason = float(ntAnnual) / nSeasons
    nPerSeason = round(nPerSeason)
    # Stratify in two dimensions:
    # 1. by time using moving windows
    # 2. by temperature class
    # Then estimate change points Cp2 and Cp3 for each stratum.
    xls_out = {"cSiteYr": cSiteYr, "cpdBin_input": {}, "cpdBin_output": {},
               "cpdFindChangePoint_output": {}}
    for iSeason in range(0, int(nSeasons)):
        xls_out["cpdBin_input"][iSeason] = {}
        xls_out["cpdBin_output"][iSeason] = {}
        if iSeason == 0:
            jtSeason = range(0, int(nPerSeason))
        else:
            if iSeason == nSeasons-1:
                jtSeason = range(int((nSeasons - 1)*nPerSeason), int(ntAnnual))
            else:
                jtSeason = range(int(iSeason*nPerSeason), int((iSeason + 1)*nPerSeason))
        itSeason = itAnnual[jtSeason]
        ntSeason = len(itSeason)
        nStrata = numpy.floor(ntSeason / (nBins*nPerBin))
        if nStrata < nStrataN:
            nStrata = nStrataN
        if nStrata > nStrataX:
            nStrata = nStrataX
        bin_range = numpy.arange(0, 101, 100/nStrata)

        xls_out["nSeasons"] = nSeasons
        xls_out["nStrata"] = nStrata

        TTh = myprctile(T[itSeason], bin_range)
        for iStrata in range(0, int(nStrata)):
            xls_out["cpdBin_input"][iSeason][iStrata] = {}
            xls_out["cpdBin_output"][iSeason][iStrata] = {}
            #itStrata = numpy.where((T >= TTh[iStrata]) & (T <= TTh[iStrata + 1]))[0]
            # using numpy.greater_equal() with "where" to suppress NaN warnings
            c1 = numpy.greater_equal(T, TTh[iStrata], where=~numpy.isnan(T))
            c2 = numpy.less_equal(T, TTh[iStrata+1], where=~numpy.isnan(T))
            itStrata = numpy.where(c1 & c2)[0]
            itStrata = numpy.intersect1d(itStrata, itSeason)

            xls_out["cpdBin_input"][iSeason][iStrata]["itStrata"] = itStrata
            xls_out["cpdBin_input"][iSeason][iStrata]["uStar"] = uStar[itStrata]
            xls_out["cpdBin_input"][iSeason][iStrata]["NEE"] = NEE[itStrata]

            n, muStar, mNEE = cpdBin(uStar[itStrata], NEE[itStrata], [], nPerBin)

            xls_out["cpdBin_output"][iSeason][iStrata]["muStar"] = muStar
            xls_out["cpdBin_output"][iSeason][iStrata]["mNEE"] = mNEE

            xCp2, xs2, xCp3, xs3 = cpdFindChangePoint20100901(muStar, mNEE, iSeason, iStrata)

            n, muStar, mT = cpdBin(uStar[itStrata], T[itStrata], [], nPerBin)
            r, p = scipy.stats.pearsonr(muStar, mT)
            xs2["mt"] = numpy.mean(t[itStrata])
            xs2["ti"] = t[itStrata[0]]
            xs2["tf"] = t[itStrata[-1]]
            xs2["ruStarVsT"] = r
            xs2["puStarVsT"] = p
            xs2["mT"] = numpy.mean(T[itStrata])
            xs2["ciT"] = 0.5*numpy.diff(myprctile(T[itStrata], numpy.array([2.5, 97.5])))[0]
            xs2["nSeasons"] = nSeasons
            xs2["nStrata"] = nStrata
            xs3["mt"] = xs2["mt"]
            xs3["ti"] = xs2["ti"]
            xs3["tf"] = xs2["tf"]
            xs3["ruStarVsT"] = xs2["ruStarVsT"]
            xs3["puStarVsT"] = xs2["puStarVsT"]
            xs3["mT"] = xs2["mT"]
            xs3["ciT"] = xs2["ciT"]
            xs3["nSeasons"] = nSeasons
            xs3["nStrata"] = nStrata
            Cp2[iSeason, iStrata] = xCp2
            Stats2[iSeason][iStrata] = xs2
            Cp3[iSeason, iStrata] = xCp3
            Stats3[iSeason][iStrata] = xs3

    xls_out["cpdFindChangePoint_output"]["Cp2"] = Cp2
    xls_out["cpdFindChangePoint_output"]["Cp3"] = Cp3
    xls_out["cpdFindChangePoint_output"]["Stats2"] = Stats2
    xls_out["cpdFindChangePoint_output"]["Stats3"] = Stats3
    #cpdEvaluateUStarTh4Season_xls_output(xls_out)

    return Cp2, Stats2, Cp3, Stats3

def cpdFindChangePoint20100901(xx, yy, iSeason, iStrata):
    """
    cpdFindChangePoint20100901

    is an operational version of the Lund and Reeves (2002)
    change-point detection algorithm as modified and
    implemented by Alan Barr for uStarTh evaluation.

    Syntax:
     [Cp2,s2,Cp3,s3] = cpdFindChangePoint20100901(uStar,NEE,fPlot,Txt)
      - Cp2 changepoint (uStarTh) from operational 2-parameter model,
      - Cp3 changepoint (uStarTh) from diagnostic 3-parameter model,
      - s2 structured record containing statistics from Cp2 evaluation,
      - s3 structured record containing statistics from Cp3 evaluation
      - xx,yy variables for change-point detection
      - fPlot flag set to 1 to plot
      - cPlot text string for plot title
    Note: The individual variables Cp2 and Cp3 are set to NaN if not significant
          but the values s2.Cp and s3.Cp are retained even if not significant.
    Functions called:
     - cpdFmax2pCp2,cpdFmax2pCp3
    from stats toolbox - regress
    Written by Alan Barr, last updated 7 Oct 2010
    Translated to Python by PRI, September 2019
    """
    # Initialize outputs.
    Cp2 = numpy.nan
    Cp3 = numpy.nan
    # s2 and s3 as dictionaries
    s2 = {}
    s3 = {}
    for item in ["n", "Cp", "Fmax", "p", "b0", "b1", "b2", "c2", "cib0", "cib1", "cic2"]:
        s2[item] = numpy.nan
        s3[item] = numpy.nan
    # Copy inputs
    x = numpy.array(xx)
    y = numpy.array(yy)
    # Exclude missing data (nan)
    x = x[~numpy.isnan(xx) & ~numpy.isnan(yy)]
    y = y[~numpy.isnan(xx) & ~numpy.isnan(yy)]
    # number of points left
    n = len(x)
    # return if less than 10 points
    if n < 10:
        return Cp2, s2, Cp3, s3
    # Exclude extreme outliers.
    # scipy.stats.linregress is 6 times faster than numpy.polyval!
    a = scipy.stats.linregress(x, y)
    yHat = a[1] + a[0]*x
    dy = y - yHat
    mdy = numpy.mean(dy)
    sdy = numpy.std(dy, ddof=1)
    ns = 4
    x = x[numpy.abs(dy - mdy) <= ns*sdy]
    y = y[numpy.abs(dy - mdy) <= ns*sdy]
    n = len(x)
    if n < 10:
        return Cp2, s2, Cp3, s3
    # Compute statistics of reduced (null hypothesis) models
    # for later testing of Cp2 and Cp3 significance.
    yHat2 = numpy.mean(y)
    SSERed2 = numpy.sum((y - yHat2) ** 2)
    a = scipy.stats.linregress(x, y)
    yHat3 = a[1] + a[0]*x
    SSERed3 = numpy.sum((y - yHat3) ** 2)
    nFull2 = 2
    nFull3 = 3
    # Compute F score (Fc2 and Fc3) for each data point in order to identify Fmax.
    Fc2 = numpy.full(n, numpy.nan)
    Fc3 = numpy.full(n, numpy.nan)
    nEndPtsN = 3
    nEndPts = numpy.floor(0.05*n)
    if nEndPts < nEndPtsN:
        nEndPts = nEndPtsN
    for i in numpy.arange(0, n-1):
        # fit operational 2 parameter model, with zero slope above Cp2:
        # 2 connected line segments, segment 2 has zero slope
        # parameters b0, b1 and xCp
        iAbv = numpy.arange(i, n)
        x1 = numpy.array(x)
        x1[iAbv] = x[i]
        x1a = numpy.column_stack((numpy.ones(len(x1)), x1))
        # we use numpy.linalg.lstsq to duplicate the matrix left divide
        # used in the original MATLAB code.
        a2 = numpy.linalg.lstsq(x1a, y, rcond=None)[0]
        yHat2 = a2[0] + a2[1]*x1
        SSEFull2 = numpy.sum((y - yHat2) ** 2)
        Fc2[i] = (SSERed2 - SSEFull2) / (SSEFull2 / (n - nFull2))
        # 2 connected line segments with noslope constraints
        # parameters b0, b1, b2 and xCp
        zAbv = numpy.zeros(n)
        zAbv[iAbv] = 1
        x1 = numpy.array(x)
        x2 = numpy.multiply((x - x[i]), zAbv)
        X = numpy.column_stack((numpy.ones(len(x1)), x1, x2))
        # we use numpy.linalg.lstsq to duplicate the matrix left divide
        # used in the original MATLAB code.
        a3 = numpy.linalg.lstsq(X, y, rcond=None)[0]
        yHat3 = a3[0] + a3[1]*x1 + a3[2]*x2
        SSEFull3 = numpy.sum((y - yHat3) ** 2)
        Fc3[i] = (SSERed3 - SSEFull3) / (SSEFull3 / (n - nFull3))
    # Assign changepoints from Fc2 and Fc3 maxima.
    # Calc stats and test for significance of Fmax scores.
    pSig = 0.05
    # 2 parameter model
    iCp2 = numpy.argmax(Fc2[~numpy.isnan(Fc2)])
    Fmax2 = Fc2[iCp2]
    xCp2 = x[iCp2]
    iAbv = numpy.arange((iCp2 + 1), n)
    x1 = numpy.array(x)
    x1[iAbv] = xCp2
    # if OLS can't find a solution, a2.params only has 1 element not 2
    # this is trapped below
    a2 = sm.OLS(y, sm.add_constant(x1)).fit()
    p2 = cpdFmax2pCp2(Fmax2, n)
    Cp2 = xCp2
    if p2 > pSig:
        Cp2 = numpy.nan
    # 3 parameter model
    iCp3 = numpy.argmax(Fc3[~numpy.isnan(Fc3)])
    Fmax3 = Fc3[iCp3]
    xCp3 = x[iCp3]
    iAbv = numpy.arange((iCp3 + 1), n)
    zAbv = numpy.zeros(n)
    zAbv[iAbv] = 1
    x1 = numpy.array(x)
    x2 = numpy.multiply((x - xCp3), zAbv)
    X = numpy.column_stack((numpy.ones(len(x1)), x1, x2))
    # if OLS can't find a solution, a3.params only has 1 element not 3
    # this is trapped below
    a3 = sm.OLS(y, X).fit()
    p3 = cpdFmax2pCp3(Fmax3, n)
    Cp3 = xCp3
    if p3 > pSig:
        Cp3 = numpy.nan
    # Assign values to s2, but only if not too close to end points.
    s2["n"] = n
    s3["n"] = n
    if (iCp2 > nEndPts - 1) and (iCp2 < (n - nEndPts - 1)):
        if len(a2.params) == 2:
            s2["Cp"] = Cp2
            s2["Fmax"] = Fmax2
            s2["p"] = p2
            s2["b0"] = a2.params[0]
            s2["b1"] = a2.params[1]
            s2["cib0"] = 0.5*(a2.conf_int(pSig)[0, 1] - a2.conf_int(pSig)[0, 0])
            s2["cib1"] = 0.5*(a2.conf_int(pSig)[1, 1] - a2.conf_int(pSig)[1, 0])
    if (iCp3 > nEndPts - 1) and (iCp3 < (n - nEndPts - 1)):
        if len(a3.params) == 3:
            s3["Cp"] = xCp3
            s3["Fmax"] = Fmax3
            s3["p"] = p3
            s3["b0"] = a3.params[0]
            s3["b1"] = a3.params[1]
            s3["b2"] = a3.params[2]
            s3["c2"] = a3.params[1] + a3.params[2]
            s3["cib0"] = 0.5*(a3.conf_int(pSig)[0, 1] - a3.conf_int(pSig)[0, 0])
            s3["cib1"] = 0.5*(a3.conf_int(pSig)[1, 1] - a3.conf_int(pSig)[1, 0])
            s3["cic2"] = 0.5*(a3.conf_int(pSig)[2, 1] - a3.conf_int(pSig)[2, 0])

    return Cp2, s2, Cp3, s3

def cpdFmax2pCp2(Fmax, n):
    """
    p = cpdFmax2pCp2(Fmax,n)
    assigns the probability p that the 2-parameter,
    operational change-point model fit is significant.
    It interpolates within a Table pTable, generated
    for the 2-parameter model by Alan Barr following Wang (2003).
    If Fmax is outside the range in the table,
    then the normal F stat is used to help extrapolate.
    Functions called: stats toolbox - fcdf, finv
    Written by Alan Barr April 2010
    """
    p = numpy.nan
    if numpy.isnan(Fmax) or numpy.isnan(n) or n < 10:
        return p
    pTable = numpy.array([0.8, 0.9, 0.95, 0.99])
    np = len(pTable)
    nTable = numpy.array([10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, 700, 1000])
    FmaxTable = numpy.array([[3.9293, 6.2992, 9.1471, 18.2659],
                             [3.7734, 5.6988, 7.877, 13.81],
                             [3.7516, 5.5172, 7.4426, 12.6481],
                             [3.7538, 5.3224, 7.0306, 11.4461],
                             [3.7941, 5.303, 6.8758, 10.6635],
                             [3.8548, 5.348, 6.8883, 10.5026],
                             [3.9798, 5.4465, 6.9184, 10.4527],
                             [4.0732, 5.5235, 6.9811, 10.3859],
                             [4.1467, 5.6136, 7.0624, 10.5596],
                             [4.277, 5.7391, 7.2005, 10.6871],
                             [4.4169, 5.8733, 7.3421, 10.6751],
                             [4.5556, 6.0591, 7.5627, 11.0072],
                             [4.7356, 6.2738, 7.7834, 11.2319]])
    FmaxCritical = numpy.full(np, numpy.nan)
    for ip in numpy.arange(np):
        interp_func = scipy.interpolate.PchipInterpolator(nTable, FmaxTable[:, ip])
        FmaxCritical[ip] = interp_func(n)
    if Fmax < FmaxCritical[0]:
        fAdj = (scipy.stats.f.ppf(0.9, 3, n)*Fmax) / FmaxCritical[0]
        p = 2*(1 - scipy.stats.f.cdf(fAdj, 3, n))
        if p > 1:
            p = 1
        return p
    if Fmax > FmaxCritical[-1]:
        fAdj = (scipy.stats.f.ppf(0.995, 3, n)*Fmax) / FmaxCritical[2]
        p = 2*(1 - scipy.stats.f.cdf(fAdj, 3, n))
        if p < 0:
            p = 0
        return p
    interp_func = scipy.interpolate.PchipInterpolator(FmaxCritical, 1 - pTable)
    p = interp_func(Fmax)
    return numpy.asscalar(p)

def cpdFmax2pCp3(Fmax, n):
    """
    p = cpdFmax2pCp3(Fmax,n)
    assigns the probability p that the 3-parameter,
    diagnostic change-point model fit is significant.
    It interpolates within a Table pTable, generated
    for the 3-parameter model by Wang (2003).
    If Fmax is outside the range in the table,
    then the normal F stat is used to help extrapolate.
    Functions called: stats toolbox - fcdf, finv
    Written by Alan Barr April 2010
    """
    p = numpy.nan
    if numpy.isnan(Fmax) or numpy.isnan(n) or n < 10:
        return p
    pTable = numpy.array([0.9, 0.95, 0.99])
    np = len(pTable)
    nTable = numpy.concatenate([numpy.arange(10, 110, 10),
                                numpy.arange(150, 600, 50),
                                numpy.arange(600, 1200, 200),
                                numpy.arange(2500, 3500, 1000)])
    FmaxTable = numpy.array([[11.646, 15.559, 28.412],
                             [9.651, 11.948, 18.043],
                             [9.379, 11.396, 16.249],
                             [9.261, 11.148, 15.75],
                             [9.269, 11.068, 15.237],
                             [9.296, 11.072, 15.252],
                             [9.296, 11.059, 14.985],
                             [9.341, 11.072, 15.013],
                             [9.397, 11.08, 14.891],
                             [9.398, 11.085, 14.874],
                             [9.506, 11.127, 14.828],
                             [9.694, 11.208, 14.898],
                             [9.691, 11.31, 14.975],
                             [9.79, 11.406, 14.998],
                             [9.794, 11.392, 15.044],
                             [9.84, 11.416, 14.98],
                             [9.872, 11.474, 15.072],
                             [9.929, 11.537, 15.115],
                             [9.955, 11.552, 15.086],
                             [9.995, 11.549, 15.164],
                             [10.102, 11.673, 15.292],
                             [10.169, 11.749, 15.154],
                             [10.478, 12.064, 15.519]])
    FmaxCritical = numpy.full(np, numpy.nan)
    for ip in numpy.arange(np):
        interp_func = scipy.interpolate.PchipInterpolator(nTable, FmaxTable[:, ip])
        FmaxCritical[ip] = interp_func(n)
    if Fmax < FmaxCritical[0]:
        fAdj = (scipy.stats.f.ppf(0.95, 3, n)*Fmax) / FmaxCritical[0]
        p = 2*(1 - scipy.stats.f.cdf(fAdj, 3, n))
        if p > 1:
            p = 1
        return p
    if Fmax > FmaxCritical[-1]:
        fAdj = (scipy.stats.f.ppf(0.995, 3, n)*Fmax) / FmaxCritical[2]
        p = 2*(1 - scipy.stats.f.cdf(fAdj, 3, n))
        if p < 0:
            p = 0
        return p
    interp_func = scipy.interpolate.PchipInterpolator(FmaxCritical, 1 - pTable)
    p = interp_func(Fmax)
    return numpy.asscalar(p)

def cpdBin(x, y, dx, nPerBin):
    """
    cpdBin
    calculates binned mean values of vectors x and y
    for use in change-point (uStarTh) detection
    Syntax: [nBins,mx,my] = cpdBin(x,y,dx,nPerBin);

    dx and nPerBin control how the data are binned.
    if dx is a positive scalar, it specifies the binning increment.
    if dx is a vector, it specifies the bin borders.
    if dx is empty, then nPerBin is used to bin the data,
    into bins with nPerBin points in each bin.
    """
    nBins = 0
    mx = []
    my = []
    if numpy.any(numpy.array(dx) <= 0):
        #print 'Function cpdBin aborted. dx cannot be <=0. '
        msg = "  Function cpdBin aborted. dx cannot be <=0. "
        logger.info(msg)
        return nBins, mx, my

    if len(dx) == 0:
        # into bins with nPerBin points in each bin.
        iYaN = numpy.where(~numpy.isnan(x + y) == True)[0]
        nYaN = len(iYaN)
        nBins = numpy.floor(nYaN / nPerBin).astype(numpy.int)
        mx = numpy.full(nBins, numpy.nan)
        my = numpy.full(nBins, numpy.nan)
        iprctile = numpy.arange(0, 101, (100. / float(nBins)))
        # PRI - October 2019
        # replace numpy.percentile() with Python translation of MATLAB/Octave
        # prctile() and quantile() functions.
        dx = myprctile(x[iYaN], iprctile)
        xL = dx[:-1]
        xU = dx[1:]
        jx = 0
        for i in numpy.arange(0, len(xL)):
            ix = numpy.where(((~numpy.isnan(x+y)) & (x >= xL[i]) & (x <= xU[i])) == True)[0]
            if len(ix) >= nPerBin:
                mx[jx] = numpy.mean(x[ix])
                my[jx] = numpy.mean(y[ix])
                jx = jx + 1
    elif len(dx) == 1:
        nx = numpy.min(x)
        xx = numpy.max(x)
        nx = dx*numpy.floor(nx / dx).astype(numpy.int)
        xx = dx*numpy.ceil(xx / dx).astype(numpy.int)
        mx = numpy.full(len(numpy.arange(nx, xx, dx)), numpy.nan)
        my = numpy.full(len(numpy.arange(nx, xx, dx)), numpy.nan)
        for jx in numpy.arange(nx, xx, dx):
            ix = numpy.where(((~numpy.isnan(x+y)) & (abs(x - jx) < 0.5*dx)) == True)[0]
            if len(ix) >= nPerBin:
                mx[nBins] = numpy.mean(x[ix])
                my[nBins] = numpy.mean(y[ix])
                nBins = nBins + 1
    else:
        xL = dx[:-1]
        xU = dx[1:]
        mx = numpy.full(len(xL), numpy.nan)
        my = numpy.full(len(xL), numpy.nan)
        for i in numpy.arange(0, len(xL)):
            ix = numpy.where(((~numpy.isnan(x+y)) & (x >= xL[i]) & (x <= xU[i])) == True)[0]
            if len(ix) >= nPerBin:
                mx[nBins] = numpy.mean(x[ix])
                my[nBins] = numpy.mean(y[ix])
                nBins = nBins + 1
    return nBins, mx, my

def mydatenum(Y, M, D, h, m, s):
    trap_Y0 = False
    if Y == 0:
        trap_Y0 = True
        Y = 1
    d = datetime.datetime(Y, M, D, h, m, s)
    if trap_Y0:
        dn = 1 + d.toordinal() + (d - datetime.datetime.fromordinal
                                  (d.toordinal())).total_seconds()/(24*60*60)
    else:
        dn = 366 + d.toordinal() + (d - datetime.datetime.fromordinal
                                    (d.toordinal())).total_seconds()/(24*60*60)
    return dn

def mydatevec(t):
    """
    function [y,m,d,h,mn,s]=mydatevec(t)
    was written by Alan Barr to return 2400 UTC rather than 0000 UTC.
    NOTE:
     This function has been rewritten to preserve the intent of
     the original code (as received from Carlo Trotti).  Under Octave,
     the original code did not work as expected.  For a 30 minute time
     step, the Octave "datevec" routine returned minutes as 29 or 59
     with seconds as 60!  This meant that 00:00 was never converted t0
     24:00 the previous day as intended.
     This function converts times of 00:00 to 24:00 the previous day.
    """
    # use year 2000 as an offset, this is needed because MATLAB will accept
    # year = 0 but Python will not (year >= 1)
    # also, MATLAB treats year = 0 as a leap year, so we choose a year offset
    # that is also a leap year
    yr0 = 2000
    # mimic MATLAB's ability to handle scalar or vector inputs
    t = numpy.asarray(t)
    scalar_input = False
    if t.ndim == 0:
        t = t[None]  # Makes x 1D
        scalar_input = True
    # do the business
    iYaN = numpy.where(~numpy.isnan(t))[0]
    y = numpy.full(len(t), numpy.nan)
    m = y.copy()
    d = y.copy()
    h = y.copy()
    mn = y.copy()
    s = y.copy()
    dt0 = datetime.datetime(yr0, 1, 1)
    dt00 = numpy.array([dt0 + datetime.timedelta(tt - 1) for tt in t[iYaN]])
    y[iYaN] = numpy.array([dt.year for dt in dt00]) - yr0
    m[iYaN] = numpy.array([dt.month for dt in dt00])
    d[iYaN] = numpy.array([dt.day for dt in dt00])
    h[iYaN] = numpy.array([dt.hour for dt in dt00])
    mn[iYaN] = numpy.array([dt.minute for dt in dt00])
    s[iYaN] = numpy.array([dt.second for dt in dt00])
    # index of midnights
    idx = numpy.where((h == 0) & (mn == 0) & (s == 0))[0]
    dt24 = numpy.array([dt00[i] - datetime.timedelta(1) for i in idx])
    y[idx] = numpy.array([dt.year for dt in dt24]) - yr0
    m[idx] = numpy.array([dt.month for dt in dt24])
    d[idx] = numpy.array([dt.day for dt in dt24])
    h[idx] = 24
    if scalar_input:
        # convert back to scalar
        return numpy.ndarray.item(y), numpy.ndarray.item(m), numpy.ndarray.item(d), \
               numpy.ndarray.item(h), numpy.ndarray.item(mn), numpy.ndarray.item(s)
    else:
        return y, m, d, h, mn, s

def mydoy(t):
    """
    doy is a day-of-year function
    that converts the serial date number t to the day of year.
    See datenum for a definition of t.
    doy differs from other formulations in that the last
    period of each day (denoted as 2400 by mydatevec)
    is attributed to the day ending 2400
    rather than the day beginning 0000.
    Original MATLAB code "Written by Alan Barr 2002."
    Rewritten for Python by PRI
    """
    # use year 2000 as an offset, this is needed because MATLAB will accept
    # year = 0 but Python will not (year >= 1)
    # also, MATLAB treats year = 0 as a leap year, so we choose a year offset
    # that is also a leap year
    yr0 = 2000
    Y, M, D, h, m, s = mydatevec(t)
    Y = Y + yr0
    tt = mydatenum(int(Y), int(M), int(D), 0, 0, 0)
    d = numpy.floor(tt - mydatenum(int(Y) - 1, 12, 31, 0, 0, 0))
    return d

def fcnaniqr(X):
    """
    fcnaniqr computes the interquartile range, ignoring NaNs.

    IQR = fcnaniqr(X)
     returns the interquartile range of the values in X,
     treating NaNs as missing.

     fcnaniqr is a limited adaptation of IQR:
     X cannot exceed 3 dimensions,
     and IQR is always computed across the
     first non-singleton dimension of X.

     For vector input, IQR is a scalar.
     For 2D matrix input, IQR is a row vector containing
      the interquartile range of each column of X.
     For a 3D arrays, IQR is a 2d array, computed
      along the first non-singleton dimension of X.

     The IQR is a robust estimate of the spread of the data,
     since changes in the upper and lower 25% of the data
     do not affect it.

     Written by Alan Barr
     Translated to Python by PRI in October 2019
    """
    # find non-singleton dimensions of length d
    d = X.shape
    d = numpy.setdiff1d(d, 1)
    nd = len(d)
    if nd == 1:
        iYaN = numpy.where(~numpy.isnan(X))[0]
        nYaN = len(iYaN)
        IQR = numpy.nan
        if nYaN <= 3:
            y = X[iYaN]
            # PRI - October 2019
            # replace numpy.percentile() with Python translation of MATLAB/Octave
            # prctile() and quantile() functions.
            yN, yX = myprctile(y, numpy.array([25, 75]))
            IQR = yX - yN
    else:
        if nd == 2:
            nr, nc = X.shape
            IQR = numpy.full((nc), numpy.nan)
            for ic in range(nc):
                iYaN = numpy.where(~numpy.isnan(X[:,ic]))[0]
                nYaN = len(iYaN)
                if nYaN > 3:
                    y = X[iYaN, ic]
                    # PRI - October 2019
                    # replace numpy.percentile() with Python translation of MATLAB/Octave
                    # prctile() and quantile() functions.
                    yN, yX = myprctile(y, numpy.array([25, 75]))
                    IQR[ic] = yX - yN
        else:
            if nd == 3:
                nr, nc, nq = X.shape
                IQR = numpy.full((nc, nq), numpy.nan)
                for iq in range(nq):
                    for ic in range(nc):
                        iYaN = numpy.where(~numpy.isnan(X[:, ic, iq]))[0]
                        nYaN = len(iYaN)
                        if nYaN > 3:
                            y = X[iYaN, ic, iq]
                            # PRI - October 2019
                            # replace numpy.percentile() with Python translation of MATLAB/Octave
                            # prctile() and quantile() functions.
                            yN, yX = myprctile(y, numpy.array([25, 75]))
                            IQR[ic, iq] = yX - yN
    return IQR

def myprctile(Y, q):
    """
    Stripped down version of Octave prctile.m
    """
    Q = myquantile(Y, q/float(100))
    return Q

def myquantile(x, p, method=5):
    """
    Stripped down version of Octave quantile.m;
     - assumes x is 1D
     - assumes 0 <= p[i] <= 1
     - only implements the switch case (method) 5
    """
    x = numpy.sort(x)
    m = numpy.sum(~numpy.isnan(x))
    mm = numpy.full(len(p), m)
    # we are only dealing with 1D vectors so xc=0 and xr*(0:xc-1)=0
    pcd = numpy.full(len(p), 0)
    p = numpy.kron(p, m) + 0.5
    pi = numpy.maximum(numpy.minimum(numpy.floor(p), mm-1), 1)
    pr = numpy.maximum(numpy.minimum(p - pi, 1), 0)
    pi = pi + pcd
    inv = numpy.multiply((1-pr), x[pi.astype(int)-1]) + numpy.multiply(pr, x[pi.astype(int)])
    return inv

def cpdAssignUStarTh20100901(Stats, fPlot, cSiteYr):
    """
    cpdAssignUStarTh20100901
     aggregates and assigns uStarTh from the Stats* structured records
     as output by cpdBootstrapUStarTh20100901.

    Syntax:

    	[CpA,nA,tW,CpW,cMode,cFailure,fSelect,sSine,FracSig,FracModeD,FracSelect] ...
    = cpdExtractuStarTh20100901 (Stats,fPlot,cSiteYr)
    	where:
    	- Stats is a structured record output by
          cpdBootstrapuStarTh20100901, can be:
          - Stats2 (2-parameter operational change-point model) or
          - Stats3 (3-parameter diagnostic change-point model)
        - fPlot is a flag that is set to 1 for plotting the aggregation analysis
        - cSiteYr is text containing site and year for the fPlot plot

    - CpA is a scalar or vector of annual uStarTh (ChangePoint) means
    - nA is the number of selected change-points in the annual mean
    - CpW and tW are vectors showing seasonal variation in uStarTh
    - cMode is the dominant change-point mode:
      D Deficit (b1>0) or E Excess (b1<0)
    - cFailure is a string containing failure messages
    - fSelect is an array the same size as Stats* that flags the
      selected Cp values for computing CpA and CpW
    - sSine contains the coefficients of an annual sine curve
      fit to tW and CpW
    - FracSig,FracModeD,FracSelect are the fraction of attempted
      change-point detections that are significant, in mode D and
      select.

    The Stats2 or Stats3 records may be 2D (nWindows x nStrata)
    or 3D (nWindows x nStrata x nBoot). If 2D, then CpA
    is a scalar and CpW is averaged across the nStrata temperature strata.
    If 3D, then CpA is a vector of length nBoot and CpW is averaged
    across nBoot bootstraps and nStrata temperature strata.
    Stats input is accepted from both 4Season (nWindows=4)
    and flexible window (nWindows>=7) processing.

    The aggregation process is selective, selecting only:
    - significant change points (p <= 0.05)
    - in the dominant mode (Deficit (b1>0) or Excess (b1<0))
    - after excluding outliers (based on regression stats).
    No assignment is made if the detection failure rate
    is too high.
    Functions called:
     fcBin, fcDatetick, fcEqnAnnualSine, fcNaniqr, fcReadFields
     fcr2Calc, fcx2colvec, fcx2rowvec
    stats toolbox:
     nanmedian, nanmean, nlinfit, prctile

    Written 16 April 2010 by Alan Barr
    Translated to Python by PRI September 2019
    """
    CpA = []
    nA = []
    tW = []
    CpW = []
    fSelect = []
    cMode = ''
    cFailure = ''
    sSine = []
    FracSig = []
    FracModeD = []
    FracSelect = []
    # Compute window sizes etc.
    nBoot = len(Stats.keys())
    nWindows = len(Stats[0].keys())
    nStrata = len(Stats[0][0].keys())
    if nBoot == 1:
        nStrataN = 0.5
    else:
        if nBoot > 1:
            nStrataN = 1.0
        else:
            cFailure = "Stats must be 2D or 3D."
            return CpA, nA, tW, CpW, cMode, cFailure, fSelect, sSine, FracSig, FracModeD, FracSelect
    nWindowsN = 4
    nSelectN = nWindowsN*nStrataN*nBoot
    CpA = numpy.full((nBoot), numpy.nan)
    nA = numpy.full((nBoot), numpy.nan)
    tW = numpy.full((nWindows), numpy.nan)
    CpW = numpy.full((nWindows), numpy.nan)
    # Extract variable arrays from Stats structure.
    # Reassign mt and Cp as x* to retain array shape,
    # then convert the extracted arrays to column vectors.
    mt = numpy.full((nStrata*nWindows*nBoot), numpy.nan)
    xmt = numpy.full((nWindows, nStrata, nBoot), numpy.nan)
    Cp = numpy.full((nStrata*nWindows*nBoot), numpy.nan)
    xCp = numpy.full((nWindows, nStrata, nBoot), numpy.nan)
    b1 = numpy.full((nStrata*nWindows*nBoot), numpy.nan)
    c2 = numpy.full((nStrata*nWindows*nBoot), numpy.nan)
    cib1 = numpy.full((nStrata*nWindows*nBoot), numpy.nan)
    cic2 = numpy.full((nStrata*nWindows*nBoot), numpy.nan)
    p = numpy.full((nStrata*nWindows*nBoot), numpy.nan)
    for boot in range(nBoot):
        for season in range(nWindows):
            for tclass in range(nStrata):
                xmt[season, tclass, boot] = Stats[boot][season][tclass]["mt"]
                xCp[season, tclass, boot] = Stats[boot][season][tclass]["Cp"]
                i = season + tclass*nWindows + boot*nWindows*nStrata
                mt[i] = Stats[boot][season][tclass]["mt"]
                Cp[i] = Stats[boot][season][tclass]["Cp"]
                b1[i] = Stats[boot][season][tclass]["b1"]
                c2[i] = Stats[boot][season][tclass]["c2"]
                cib1[i] = Stats[boot][season][tclass]["cib1"]
                cic2[i] = Stats[boot][season][tclass]["cic2"]
                p[i] = Stats[boot][season][tclass]["p"]
    pSig = 0.05
    fP = numpy.where((p <= pSig), 1, 0)
    # Determine if Stats input is from the operational 2-parameter
    # or diagnostic 3-parameter change-point model
    # and set c2 and cic2 to zero if 2-parameter
    nPar = 3
    if numpy.all(numpy.isnan(c2)):
        nPar = 2
        c2 = float(0)*b1
        cic2 = c2
    # Classify Cp regressions by slopes of b1 and c2 regression coeff:
    #  - NS: not sig, mfP=NaN, p>0.05
    #  - ModeE: atypical significant Cp (b1<c2)
    #  - ModeD: typical significant Cp (b1>=c2)
    iTry = numpy.where(~numpy.isnan(mt))[0]
    nTry = len(iTry)
    # trap nTry == 0
    if nTry == 0:
        #cFailure = "cpdAssignUStarTh: nTry is 0"
        return CpA, nA, tW, CpW, cMode, cFailure, fSelect, sSine, FracSig, FracModeD, FracSelect
    iCp = numpy.where(~numpy.isnan(b1 + c2 + Cp))[0]
    nCp = len(iCp)
    iNS = numpy.where((fP == 0) & (~numpy.isnan(b1 + c2 + Cp)))[0]
    nNS = len(iNS)
    iSig = numpy.where((fP == 1) & (~numpy.isnan(b1 + c2 + Cp)))[0]
    nSig = len(iSig)
    # trap nSig == 0
    if nSig == 0:
        #cFailure = "cpdAssignUStarTh: nSig is 0"
        return CpA, nA, tW, CpW, cMode, cFailure, fSelect, sSine, FracSig, FracModeD, FracSelect
    iModeE = numpy.where((fP == 1) & (b1 < c2))[0]
    nModeE = len(iModeE)
    iModeD = numpy.where((fP == 1) & (b1 >= c2))[0]
    nModeD = len(iModeD)
    # Evaluate and accept primary mode of significant Cps
    if nModeD >= nModeE:
        iSelect = iModeD
        cMode = "D"
    else:
        iSelect = iModeE
        cMode = "E"
    nSelect = len(iSelect)
    fSelect = numpy.zeros(len(fP))
    fSelect[iSelect] = 1
    # convert from number to boolean
    fSelect = fSelect.astype(bool)
    fModeD = numpy.full((len(fP)), numpy.nan)
    fModeD[iModeD] = 1
    fModeE = numpy.full((len(fP)), numpy.nan)
    fModeE[iModeE] = 1
    FracSig = float(nSig) / float(nTry)
    FracModeD = float(nModeD) / float(nSig)
    FracSelect = float(nSelect) / float(nTry)
    # Abort analysis if too few of the regressions produce significant Cps.
    if FracSelect < 0.1:
        cFailure = "Less than 10% successful detections. "
        return CpA, nA, tW, CpW, cMode, cFailure, fSelect, sSine, FracSig, FracModeD, FracSelect
    # Exclude outliers from Select mode based on Cp and regression stats
    if nPar == 2:
        x = numpy.column_stack((Cp, b1, cib1))
        nx = 3
    else:
        if nPar == 3:
            x = numpy.column_stack((Cp, b1, c2, cib1, cic2))
            nx = 5
    mx = numpy.nanmedian(x, axis=0)
    sx = fcnaniqr(x)
    xNorm = x*numpy.nan
    # PRI - I believe the use of x[:, 0] is wrong and it should be x[:, i]
    for i in range(nx):
        xNorm[:, i] = (x[:, 0] - mx[i]) / sx[i]
    xNormX = numpy.nanmax(abs(xNorm), axis=1)
    ns = 5
    fOut = (xNormX > ns)
    iOut = numpy.where(fOut)[0]
    iSelect = numpy.setdiff1d(iSelect, iOut)
    nSelect = len(iSelect)
    fSelect = ~fOut & fSelect
    fModeD[iOut] = numpy.nan
    iModeD = numpy.where(fModeD == 1)[0]
    nModeD = len(iModeD)
    fModeE[iOut] = numpy.nan
    iModeE = numpy.where(fModeE == 1)[0]
    nModeE = len(iModeE)
    iSig = numpy.union1d(iModeD, iModeE)
    nSig = len(iSig)
    FracSig = float(nSig) / float(nTry)
    FracModeD = float(nModeD) / float(nSig)
    FracSelect = float(nSelect) / float(nTry)
    # PRI - the following check seems doomed to failure.  Given the way nSelect
    #       and nSelectN are calculated, we would always expect nSelect<nSelectN.
    #if nSelect<nSelectN; cFailure=sprintf('Too few selected change points: %g/%g',nSelect,nSelectN); return;  end;
    # PRI - however, if we change the definition of nStrata and nBoot at the start
    #       of this script to what I think is correct then the original check
    #       makes sense.  It will return if less than half of the windows give a
    #       change point value that passes all QC checks.
    #       So, having changed the definition of nStrata and nBoot, we will
    #       re-instate the check.
    # PRI - comment out this check for testing purposes only, to match current MATLAB
    #       code.
    #if nSelect < nSelectN:
        #cFailure = "Too few selected change points: " + str(int(nSelect)) + ", " + str(int(nSelectN))
        #print cFailure
        #return CpA, nA, tW, CpW, cMode, cFailure, fSelect, sSine, FracSig, FracModeD, FracSelect
    # Aggregate the values to season and year.
    CpSelect = numpy.full((Cp.shape), numpy.nan)
    CpSelect[iSelect] = Cp[iSelect]
    xCpGF = numpy.reshape(CpSelect,(nWindows, nStrata, nBoot), order='F')
    if nBoot == 1:
        # PRI - needed to reverse order of nanmean/sum and fcx2colvec to get expected
        #       behaviour in Octave when nBoot=1
        # CpA=fcx2colvec(nanmean(xCpGF));
        # nA=fcx2colvec(sum(~isnan(xCpSelect)));
        CpA = numpy.nanmean(xCpGF)
        nA = numpy.sum(~numpy.isnan(xCpGF))
    else:
        # PRI - redundant, left in solely to be consistent with MATLAB code
        # PRI - no, not redundant, PRI is wiser now ...
        # CpA=fcx2colvec(nanmean(reshape(xCpGF,dot(nWindows,nStrata),nBoot)))
        # nA=fcx2colvec(sum(logical_not(isnan(reshape(xCpSelect,dot(nWindows,nStrata),nBoot)))))
        a = numpy.reshape(xCpGF, (nWindows*nStrata, nBoot), order='F')
        CpA = numpy.nanmean(a, axis=0)
        nA = numpy.sum(~numpy.isnan(a), axis=0)
    # Calculate mean tW and CpW for each window based on Select data only.
    # Because the bootstrap varies the number of windows among bootstraps,
    # base on the median number of windows and reshape sorted data.
    a = numpy.reshape(xmt, (nWindows, nStrata*nBoot), order='F')
    nW = numpy.nanmedian(numpy.sum(~numpy.isnan(a), axis=0))
    mtSelect = numpy.sort(mt[iSelect])
    i = numpy.argsort(mt[iSelect])
    CpSelect = Cp[iSelect[i]]
    iprctile = numpy.arange(0, 101, 100/nW)
    xBins = myprctile(mtSelect, iprctile)
    n, tW, CpW = cpdBin(mtSelect, CpSelect, xBins, 0)
    # This is the end of the translated code.
    # The following code to detect seasonal trends is not implemented.
    # Fit annual sine curve
    bSine = numpy.array([1, 1, 1])
    # PRI - unable to get the following code to run in Octave
    #[bSine] = nlinfit(mt(iSelect),Cp(iSelect),'fcEqnAnnualSine',bSine)
    #yHat = fcEqnAnnualSine(bSine, mt(iSelect))
    #r2 = fcr2Calc(Cp(iSelect),yHat)
    #mtHat=sort(mt(iSelect)); CpHat=fcEqnAnnualSine(bSine,mtHat);
    r2 = 1.0
    if bSine[1] < 0:
        bSine[1] = -1.0 * bSine[1]
        bSine[2] = bSine[2] + 365.25 / 2
    bSine[2] = numpy.mod(bSine[2], 365.25)
    sSine = numpy.append(bSine, r2)

## cpdAssignUStarTh20100901.m:200
    ##	=======================================================================
##	=======================================================================

    #if fPlot:
        #FracSelectByWindow=sum(reshape(logical_not(isnan(xCpGF)),nWindows,dot(nStrata,nBoot)),2) / sum(reshape(logical_not(isnan(xmt)),nWindows,dot(nStrata,nBoot)),2)
## cpdAssignUStarTh20100901.m:207
        #mtByWindow=nanmean(reshape(xmt,nWindows,dot(nStrata,nBoot)),2)
## cpdAssignUStarTh20100901.m:208
        #fcFigLoc(1,0.5,0.45,'NE')
        #subplot('position',concat([0.08,0.56,0.6,0.38]))
        #hold('on')
        #box('on')
        #plot(mt,Cp,'r.',mt(iModeE),Cp(iModeE),'b.',mt(iModeD),Cp(iModeD),'g.')
        #nBins=copy(nWindows)
## cpdAssignUStarTh20100901.m:214
        #if nModeD >= dot(nBins,30):
            #n,mx,my=fcBin(mt(iModeD),Cp(iModeD),[],round(nModeD / nBins),nargout=3)
## cpdAssignUStarTh20100901.m:216
            #hold('on')
            #plot(mx,my,'ko-','MarkerFaceColor','y','MarkerSize',8,'LineWidth',2)
        #if nModeE >= dot(nBins,30):
            #n,mx,my=fcBin(mt(iModeE),Cp(iModeE),[],round(nModeE / nBins),nargout=3)
## cpdAssignUStarTh20100901.m:220
            #hold('on')
            #plot(mx,my,'bo-','MarkerFaceColor','c','MarkerSize',8,'LineWidth',2)
        #fcDatetick(mt,'Mo',4,1)
        #ylabel('Cp')
        #ylabel('Raw Cp Modes D (green) E (red)')
        #ylim(concat([0,prctile(Cp,99.9)]))
        #hold('off')
        #title(sprintf('%s  Stats%g  Mode%s  nSelect/nTry: %g/%g  uStarTh: %5.3f (%5.3f) ',cSiteYr,nPar,cMode,nSelect,nTry,nanmedian(Cp(iSelect)),dot(0.5,diff(prctile(Cp(iSelect),concat([2.5,97.5]))))))
        #subplot('position',concat([0.08,0.06,0.6,0.38]))
        #hold('on')
        #box('on')
        #if 'G' == cMode:
            #c='g'
## cpdAssignUStarTh20100901.m:231
        #else:
            #if 'L' == cMode:
                #c='b'
## cpdAssignUStarTh20100901.m:231
            #else:
                #c='k'
## cpdAssignUStarTh20100901.m:231
        #plot(mt(iSelect),Cp(iSelect),concat([c,'.']),mtHat,CpHat,'r-','LineWidth',3)
        #plot(tW,CpW,'ro','MarkerFaceColor','y','MarkerSize',9.T,'LineWidth',2)
        #fcDatetick(mt(iSelect),'Mo',4,1)
        #ylabel('Select Cp')
        #ylim(concat([0,prctile(Cp(iSelect),99)]))
        #title(sprintf('Cp = %5.3f + %5.3f sin(wt - %3.0f) (r^2 = %5.3f) ',bSine,r2))
        #subplot('position',concat([0.76,0.56,0.22,0.38]))
        #hist(CpA,30)
        #grid('on')
        #box('on')
        #xlim(concat([min(CpA),max(CpA)]))
        #xlabel('Annual \\itu_*^{Th}')
        #ylabel('Frequency')
        #title(sprintf('Median (CI): %5.3f (%5.3f) ',nanmedian(CpA),dot(0.5,diff(prctile(CpA,concat([2.5,97.5]))))))
        #subplot('position',concat([0.76,0.06,0.22,0.38]))
        #plot(mtByWindow,FracSelectByWindow,'o-')
        #fcDatetick(mtByWindow,'Mo',4,1)
        #ylabel('FracSelectByWindow')
        #ylim(concat([0,1]))

    ##	=======================================================================
##	=======================================================================

    return CpA, nA, tW, CpW, cMode, cFailure, fSelect, sSine, FracSig, FracModeD, FracSelect
