# standard modules
import copy
import logging
import os
# PFP modules
import pfp_ck
import pfp_gf
import pfp_gfALT
import pfp_gfMDS
import pfp_gfSOLO
import pfp_io
import pfp_rp
import pfp_ts
import pfp_utils

logger = logging.getLogger("pfp_log")

def l1qc(cf):
    # get the data series from the Excel file
    in_filename = pfp_io.get_infilenamefromcf(cf)
    if not pfp_utils.file_exists(in_filename,mode="quiet"):
        msg = " Input file "+in_filename+" not found ..."
        logger.error(msg)
        ds1 = pfp_io.DataStructure()
        ds1.returncodes = {"value":1,"message":msg}
        return ds1
    file_name,file_extension = os.path.splitext(in_filename)
    if "csv" in file_extension.lower():
        ds1 = pfp_io.csv_read_series(cf)
        if ds1.returncodes["value"] != 0:
            return ds1
        # get a series of Excel datetime from the Python datetime objects
        #pfp_utils.get_xldatefromdatetime(ds1)
    else:
        ds1 = pfp_io.xl_read_series(cf)
        if ds1.returncodes["value"] != 0:
            return ds1
        # get a series of Python datetime objects from the Excel datetime
        #pfp_utils.get_datetimefromxldate(ds1)
    # get the netCDF attributes from the control file
    #pfp_ts.do_attributes(cf,ds1)
    pfp_utils.get_datetime(cf, ds1)
    # round the Python datetime to the nearest second
    pfp_utils.round_datetime(ds1, mode="nearest_second")
    #check for gaps in the Python datetime series and fix if present
    fixtimestepmethod = pfp_utils.get_keyvaluefromcf(cf, ["options"], "FixTimeStepMethod", default="round")
    if pfp_utils.CheckTimeStep(ds1):
        pfp_utils.FixTimeStep(ds1, fixtimestepmethod=fixtimestepmethod)
    # recalculate the Excel datetime
    pfp_utils.get_xldatefromdatetime(ds1)
    # get the Year, Month, Day etc from the Python datetime
    pfp_utils.get_ymdhmsfromdatetime(ds1)
    # write the processing level to a global attribute
    ds1.globalattributes['nc_level'] = str("L1")
    # get the start and end date from the datetime series unless they were
    # given in the control file
    if 'start_date' not in ds1.globalattributes.keys():
        ds1.globalattributes['start_date'] = str(ds1.series['DateTime']['Data'][0])
    if 'end_date' not in ds1.globalattributes.keys():
        ds1.globalattributes['end_date'] = str(ds1.series['DateTime']['Data'][-1])
    # calculate variances from standard deviations and vice versa
    pfp_ts.CalculateStandardDeviations(cf,ds1)
    # create new variables using user defined functions
    pfp_ts.DoFunctions(cf,ds1)
    # create a series of synthetic downwelling shortwave radiation
    pfp_ts.get_synthetic_fsd(ds1)
    # check missing data and QC flags are consistent
    pfp_utils.CheckQCFlags(ds1)

    return ds1

def l2qc(cf,ds1):
    """
        Perform initial QA/QC on flux data
        Generates L2 from L1 data
        * check parameters specified in control file

        Functions performed:
            pfp_ck.do_rangecheck*
            pfp_ck.do_CSATcheck
            pfp_ck.do_7500check
            pfp_ck.do_diurnalcheck*
            pfp_ck.do_excludedates*
            pfp_ck.do_excludehours*
            pfp_ts.albedo
        """
    # make a copy of the L1 data
    ds2 = copy.deepcopy(ds1)
    # set some attributes for this level
    pfp_utils.UpdateGlobalAttributes(cf,ds2,"L2")
    ds2.globalattributes['Functions'] = ''
    # put the control file name into the global attributes
    #ds2.globalattributes['controlfile_name'] = cf['controlfile_name']
    # apply the quality control checks (range, diurnal, exclude dates and exclude hours
    pfp_ck.do_qcchecks(cf,ds2)
    # do the CSAT diagnostic check
    pfp_ck.do_SONICcheck(cf,ds2)
    # do the IRGA diagnostic check
    pfp_ck.do_IRGAcheck(cf,ds2)
    # constrain albedo estimates to full sun angles
    #pfp_ts.albedo(cf,ds2)
    #log.info(' Finished the albedo constraints')    # apply linear corrections to the data
    #log.info(' Applying linear corrections ...')
    pfp_ck.do_linear(cf,ds2)
    # check missing data and QC flags are consistent
    pfp_utils.CheckQCFlags(ds2)
    # write series statistics to file
    pfp_io.get_seriesstats(cf,ds2)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds2)

    return ds2

def l3qc(cf,ds2):
    """
    """
    # make a copy of the L2 data
    ds3 = copy.deepcopy(ds2)
    # set some attributes for this level
    pfp_utils.UpdateGlobalAttributes(cf,ds3,"L3")
    # put the control file name into the global attributes
    #ds3.globalattributes['controlfile_name'] = cf['controlfile_name']
    # check to see if we have any imports
    pfp_gf.ImportSeries(cf,ds3)
    # apply linear corrections to the data
    pfp_ck.do_linear(cf,ds3)
    # ************************
    # *** Merge humidities ***
    # ************************
    # merge whatever humidities are available
    pfp_ts.MergeHumidities(cf,ds3,convert_units=True)
    # **************************
    # *** Merge temperatures ***
    # **************************
    # get the air temperature from the CSAT virtual temperature
    pfp_ts.TaFromTv(cf,ds3)
    # merge the HMP and corrected CSAT data
    pfp_ts.MergeSeries(cf,ds3,"Ta",convert_units=True)
    pfp_utils.CheckUnits(ds3,"Ta","C",convert_units=True)
    # ***************************
    # *** Calcuate humidities ***
    # ***************************
    # calculate humidities (absolute, specific and relative) from whatever is available
    pfp_ts.CalculateHumidities(ds3)
    # ********************************
    # *** Merge CO2 concentrations ***
    # ********************************
    # merge the 7500 CO2 concentration
    # PRI 09/08/2017 possibly the ugliest thing I have done yet
    # This needs to be abstracted to a general alias checking routine at the
    # start of the L3 processing so that possible aliases are mapped to a single
    # set of variable names.
    if "CO2" in cf["Variables"]:
        CO2 = "CO2"
    elif "Cc" in cf["Variables"]:
        CO2 = "Cc"
    else:
        msg = "Label for CO2 ('CO2','Cc') not found in control file"
        logger.warning(msg)
        CO2 = None
    pfp_ts.MergeSeries(cf, ds3, CO2, convert_units=True)
    # ******************************************
    # *** Calculate meteorological variables ***
    # ******************************************
    # Update meteorological variables
    pfp_ts.CalculateMeteorologicalVariables(ds3)
    # *************************************************
    # *** Calculate fluxes from covariances section ***
    # *************************************************
    # check to see if the user wants to use the fluxes in the L2 file
    if not pfp_utils.get_optionskeyaslogical(cf, "UseL2Fluxes", default=False):
        # check the covariance units and change if necessary
        pfp_ts.CheckCovarianceUnits(ds3)
        # do the 2D coordinate rotation
        pfp_ts.CoordRotation2D(cf, ds3)
        # do the Massman frequency attenuation correction
        pfp_ts.MassmanStandard(cf, ds3)
        # calculate the fluxes
        pfp_ts.CalculateFluxes(cf, ds3)
        # approximate wT from virtual wT using wA (ref: Campbell OPECSystem manual)
        pfp_ts.FhvtoFh(cf, ds3)
        # correct the H2O & CO2 flux due to effects of flux on density measurements
        if pfp_ts.Fe_WPL(cf, ds3):
            return ds3
        if pfp_ts.Fc_WPL(cf, ds3):
            return ds3
    # **************************
    # *** CO2 and Fc section ***
    # **************************
    # convert CO2 units if required
    pfp_utils.ConvertCO2Units(cf, ds3, CO2=CO2)
    # calculate Fc storage term - single height only at present
    pfp_ts.CalculateFcStorageSinglePoint(cf, ds3, Fc_out='Fc_single', CO2_in=CO2)
    # convert Fc and Fc_storage units if required
    pfp_utils.ConvertFcUnits(cf, ds3)
    # merge Fc and Fc_storage series if required
    merge_list = [label for label in cf["Variables"].keys() if label[0:2]=="Fc" and "MergeSeries" in cf["Variables"][label].keys()]
    for label in merge_list:
        pfp_ts.MergeSeries(cf, ds3, label, save_originals=True)
    # correct Fc for storage term - only recommended if storage calculated from profile available
    pfp_ts.CorrectFcForStorage(cf, ds3)
    # *************************
    # *** Radiation section ***
    # *************************
    # merge the incoming shortwave radiation
    pfp_ts.MergeSeries(cf, ds3, 'Fsd')
    # calculate the net radiation from the Kipp and Zonen CNR1
    pfp_ts.CalculateNetRadiation(cf,ds3,Fn_out='Fn_4cmpt',Fsd_in='Fsd',Fsu_in='Fsu',Fld_in='Fld',Flu_in='Flu')
    pfp_ts.MergeSeries(cf,ds3,'Fn')
    # ****************************************
    # *** Wind speed and direction section ***
    # ****************************************
    # combine wind speed from the Wind Sentry and the SONIC
    pfp_ts.MergeSeries(cf,ds3,'Ws')
    # combine wind direction from the Wind Sentry and the SONIC
    pfp_ts.MergeSeries(cf,ds3,'Wd')
    # ********************
    # *** Soil section ***
    # ********************
    # correct soil heat flux for storage
    #    ... either average the raw ground heat flux, soil temperature and moisture
    #        and then do the correction (OzFlux "standard")
    pfp_ts.AverageSeriesByElements(cf,ds3,'Ts')
    pfp_ts.AverageSeriesByElements(cf,ds3,'Sws')
    if pfp_utils.get_optionskeyaslogical(cf, "CorrectIndividualFg"):
        #    ... or correct the individual ground heat flux measurements (James' method)
        pfp_ts.CorrectIndividualFgForStorage(cf,ds3)
        pfp_ts.AverageSeriesByElements(cf,ds3,'Fg')
    else:
        pfp_ts.AverageSeriesByElements(cf,ds3,'Fg')
        pfp_ts.CorrectFgForStorage(cf,ds3,Fg_out='Fg',Fg_in='Fg',Ts_in='Ts',Sws_in='Sws')
    # calculate the available energy
    pfp_ts.CalculateAvailableEnergy(ds3,Fa_out='Fa',Fn_in='Fn',Fg_in='Fg')
    # create new series using MergeSeries or AverageSeries
    pfp_ck.CreateNewSeries(cf,ds3)
    # Calculate Monin-Obukhov length
    pfp_ts.CalculateMoninObukhovLength(ds3)
    # re-apply the quality control checks (range, diurnal and rules)
    pfp_ck.do_qcchecks(cf,ds3)
    # coordinate gaps in the three main fluxes
    pfp_ck.CoordinateFluxGaps(cf,ds3)
    # coordinate gaps in Ah_7500_Av with Fc
    pfp_ck.CoordinateAh7500AndFcGaps(cf,ds3)
    # check missing data and QC flags are consistent
    pfp_utils.CheckQCFlags(ds3)
    # get the statistics for the QC flags and write these to an Excel spreadsheet
    pfp_io.get_seriesstats(cf,ds3)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds3)
    # write the percentage of good data for groups
    pfp_utils.get_coverage_groups(ds3)

    return ds3

def l4qc(main_gui, cf, ds3):
    ds4 = pfp_io.copy_datastructure(cf, ds3)
    # ds4 will be empty (logical false) if an error occurs in copy_datastructure
    # return from this routine if this is the case
    if not ds4:
        return ds4
    # set some attributes for this level
    pfp_utils.UpdateGlobalAttributes(cf, ds4, "L4")
    # check to see if we have any imports
    pfp_gf.ImportSeries(cf, ds4)
    # re-apply the quality control checks (range, diurnal and rules)
    pfp_ck.do_qcchecks(cf, ds4)
    # now do the meteorological driver gap filling
    # parse the control file for information on how the user wants to do the gap filling
    l4_info = pfp_gf.ParseL4ControlFile(cf, ds4)
    if ds4.returncodes["value"] != 0:
        return ds4
    # *** start of the section that does the gap filling of the drivers ***
    # read the alternate data files
    ds_alt = pfp_gf.ReadAlternateFiles(ds4, l4_info)
    # fill short gaps using interpolation
    pfp_gf.GapFillUsingInterpolation(cf, ds4)
    # gap fill using climatology
    if "GapFillFromClimatology" in l4_info:
        pfp_gf.GapFillFromClimatology(ds4, l4_info, "GapFillFromClimatology")
    # do the gap filling using the ACCESS output
    if "GapFillFromAlternate" in l4_info:
        pfp_gfALT.GapFillFromAlternate(main_gui, ds4, ds_alt, l4_info, "GapFillFromAlternate")
        if ds4.returncodes["value"] != 0:
            return ds4
    # merge the first group of gap filled drivers into a single series
    pfp_ts.MergeSeriesUsingDict(ds4, l4_info, merge_order="prerequisite")
    # re-calculate the ground heat flux but only if requested in control file
    opt = pfp_utils.get_keyvaluefromcf(cf,["Options"], "CorrectFgForStorage", default="No", mode="quiet")
    if opt.lower() != "no":
        pfp_ts.CorrectFgForStorage(cf, ds4, Fg_out='Fg', Fg_in='Fg_Av', Ts_in='Ts', Sws_in='Sws')
    # re-calculate the net radiation
    pfp_ts.CalculateNetRadiation(cf, ds4, Fn_out='Fn', Fsd_in='Fsd', Fsu_in='Fsu', Fld_in='Fld', Flu_in='Flu')
    # re-calculate the available energy
    pfp_ts.CalculateAvailableEnergy(ds4, Fa_out='Fa', Fn_in='Fn', Fg_in='Fg')
    # merge the second group of gap filled drivers into a single series
    pfp_ts.MergeSeriesUsingDict(ds4, l4_info, merge_order="standard")
    # re-calculate the water vapour concentrations
    pfp_ts.CalculateHumiditiesAfterGapFill(ds4, l4_info)
    # re-calculate the meteorological variables
    pfp_ts.CalculateMeteorologicalVariables(ds4)
    # the Tumba rhumba
    pfp_ts.CalculateComponentsFromWsWd(ds4)
    # check for any missing data
    pfp_utils.get_missingingapfilledseries(ds4, l4_info)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds4)
    # write the percentage of good data for groups
    pfp_utils.get_coverage_groups(ds4)

    return ds4

def l5qc(main_gui, cf, ds4):
    ds5 = pfp_io.copy_datastructure(cf, ds4)
    # ds4 will be empty (logical false) if an error occurs in copy_datastructure
    # return from this routine if this is the case
    if not ds5:
        return ds5
    # set some attributes for this level
    pfp_utils.UpdateGlobalAttributes(cf, ds5, "L5")
    # check to see if we have any imports
    pfp_gf.ImportSeries(cf, ds5)
    # re-apply the quality control checks (range, diurnal and rules)
    pfp_ck.do_qcchecks(cf, ds5)
    # now do the flux gap filling methods
    # parse the control file for information on how the user wants to do the gap filling
    l5_info = pfp_gf.ParseL5ControlFile(cf, ds5)
    if ds5.returncodes["value"] != 0:
        return ds5
    # *** start of the section that does the gap filling of the fluxes ***
    pfp_gf.CheckGapLengths(cf, ds5, l5_info)
    if ds5.returncodes["value"] != 0:
        return ds5
    # apply the turbulence filter (if requested)
    pfp_ck.ApplyTurbulenceFilter(cf, ds5)
    # fill short gaps using interpolation
    pfp_gf.GapFillUsingInterpolation(cf, ds5)
    # gap fill using marginal distribution sampling
    if "GapFillUsingMDS" in l5_info:
        pfp_gfMDS.GapFillUsingMDS(ds5, l5_info, "GapFillUsingMDS")
    # do the gap filling using SOLO
    if "GapFillUsingSOLO" in l5_info:
        pfp_gfSOLO.GapFillUsingSOLO(main_gui, ds5, l5_info, "GapFillUsingSOLO")
        if ds5.returncodes["value"] != 0:
            return ds5
    # fill long gaps using SOLO
    if "GapFillLongSOLO" in l5_info:
        pfp_gfSOLO.GapFillUsingSOLO(main_gui, ds5, l5_info, "GapFillLongSOLO")
        if ds5.returncodes["value"] != 0:
            return ds5
    # merge the gap filled drivers into a single series
    pfp_ts.MergeSeriesUsingDict(ds5, l5_info, merge_order="standard")
    # calculate Monin-Obukhov length
    pfp_ts.CalculateMoninObukhovLength(ds5)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds5)
    # write the percentage of good data for groups
    pfp_utils.get_coverage_groups(ds5)

    return ds5

def l6qc(main_gui, cf, ds5):
    ds6 = pfp_io.copy_datastructure(cf, ds5)
    # ds6 will be empty (logical false) if an error occurs in copy_datastructure
    # return from this routine if this is the case
    if not ds6:
        return ds6
    # set some attributes for this level
    pfp_utils.UpdateGlobalAttributes(cf, ds6, "L6")
    # parse the control file
    l6_info = pfp_rp.ParseL6ControlFile(cf, ds6)
    # check to see if we have any imports
    pfp_gf.ImportSeries(cf, ds6)
    # check units of Fc
    Fc_list = [label for label in ds6.series.keys() if label[0:2] == "Fc"]
    pfp_utils.CheckUnits(ds6, Fc_list, "umol/m2/s", convert_units=True)
    # get ER from the observed Fc
    pfp_rp.GetERFromFc(cf, ds6)
    # return code will be non-zero if turbulance filter not applied to CO2 flux
    if ds6.returncodes["value"] != 0:
        return ds6
    # estimate ER using SOLO
    if "ERUsingSOLO" in l6_info:
        pfp_rp.ERUsingSOLO(main_gui, ds6, l6_info, "ERUsingSOLO")
        if ds6.returncodes["value"] != 0:
            return ds6
    # estimate ER using FFNET
    #pfp_rp.ERUsingFFNET(cf, ds6, l6_info)
    # estimate ER using Lloyd-Taylor
    pfp_rp.ERUsingLloydTaylor(ds6, l6_info)
    # estimate ER using Lasslop et al
    pfp_rp.ERUsingLasslop(ds6, l6_info)
    # merge the estimates of ER with the observations
    pfp_ts.MergeSeriesUsingDict(ds6, l6_info, merge_order="standard")
    # calculate NEE from Fc and ER
    pfp_rp.CalculateNEE(cf, ds6, l6_info)
    # calculate NEP from NEE
    pfp_rp.CalculateNEP(cf, ds6)
    # calculate ET from Fe
    pfp_rp.CalculateET(ds6)
    # partition NEE into GPP and ER
    pfp_rp.PartitionNEE(ds6, l6_info)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds6)
    # write the percentage of good data for groups
    pfp_utils.get_coverage_groups(ds6)
    # do the L6 summary
    pfp_rp.L6_summary(cf, ds6)

    return ds6
