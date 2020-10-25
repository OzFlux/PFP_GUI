# standard modules
import copy
import logging
import os
# PFP modules
import pfp_ck
import pfp_compliance
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
    """
    Purpose:
     Reads input files, either an Excel workbook or a collection of CSV files,
     and returns the data as a data structure.
    Usage:
    Side effects:
     Returns a data structure containing the data specified in the L1
     control file.
    Author: PRI
    Date: February 2020
    """
    # get a new data structure
    ds = pfp_io.DataStructure()
    # parse the L1 control file
    l1_info = pfp_compliance.ParseL1ControlFile(cf)
    # return if parsing throws an error
    if not pfp_compliance.check_status_ok(ds, l1_info): return ds
    # check the Excel workbook
    xl_data = pfp_compliance.CheckExcelWorkbook(l1_info)
    # copy data from the worksheets to individual data structures
    ds_dict = pfp_io.ExcelToDataStructures(xl_data, l1_info)
    # merge the individual data structures to a single data structure
    ds = pfp_ts.MergeDataStructures(ds_dict, l1_info)
    # write the processing level to a global attribute
    ds.globalattributes["nc_level"] = "L1"
    # create new variables using user defined functions
    pfp_ts.DoFunctions(ds, l1_info["read_excel"])
    # calculate variances from standard deviations and vice versa
    pfp_ts.CalculateStandardDeviations(ds)
    # check missing data and QC flags are consistent
    pfp_utils.CheckQCFlags(ds)
    return ds

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
    pfp_utils.UpdateGlobalAttributes(cf, ds2, "L2")
    # apply linear corrections to the data
    pfp_ck.do_linear(cf, ds2)
    # apply the quality control checks (range, diurnal, exclude dates and exclude hours
    pfp_ck.do_qcchecks(cf, ds2)
    # do the CSAT diagnostic check
    pfp_ck.do_SONICcheck(cf, ds2)
    # do the IRGA diagnostic check
    pfp_ck.do_IRGAcheck(cf, ds2)
    # check missing data and QC flags are consistent
    pfp_utils.CheckQCFlags(ds2)
    # write series statistics to file
    pfp_io.get_seriesstats(cf, ds2)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds2)

    return ds2

def l3qc(cf, ds2):
    """
    """
    # make a copy of the L2 data
    ds3 = copy.deepcopy(ds2)
    # set some attributes for this level
    pfp_utils.UpdateGlobalAttributes(cf, ds3, "L3")
    # check to see if we have any imports
    pfp_gf.ImportSeries(cf,ds3)
    # apply linear corrections to the data
    pfp_ck.do_linear(cf,ds3)
    # parse the control file for information on how the user wants to do the gap filling
    l3_info = pfp_compliance.ParseL3ControlFile(cf, ds3)
    if l3_info["status"]["value"] != 0:
        logger.error(l3_info["status"]["message"])
        return ds3
    # ************************
    # *** Merge humidities ***
    # ************************
    # merge whatever humidities are available
    pfp_ts.MergeHumidities(cf, ds3, convert_units=True)
    # **************************
    # *** Merge temperatures ***
    # **************************
    # get the air temperature from the CSAT virtual temperature
    pfp_ts.TaFromTv(cf, ds3)
    # merge the HMP and corrected CSAT data
    pfp_ts.CombineSeries(cf, ds3, "Ta", convert_units=True)
    pfp_utils.CheckUnits(ds3, "Ta", "C", convert_units=True)
    # ***************************
    # *** Calcuate humidities ***
    # ***************************
    # calculate humidities (absolute, specific and relative) from whatever is available
    pfp_ts.CalculateHumidities(ds3)
    # ********************************
    # *** Merge CO2 concentrations ***
    # ********************************
    # merge the CO2 concentration
    pfp_ts.CombineSeries(cf, ds3, l3_info["CO2"]["label"], convert_units=True)
    # ******************************************
    # *** Calculate meteorological variables ***
    # ******************************************
    # Update meteorological variables
    pfp_ts.CalculateMeteorologicalVariables(ds3, l3_info)
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
    pfp_utils.ConvertCO2Units(cf, ds3)
    # calculate Fc storage term - single height only at present
    pfp_ts.CalculateFcStorageSinglePoint(cf, ds3, l3_info["CO2"]["label"])
    # convert Fc units if required
    pfp_utils.ConvertFcUnits(cf, ds3)
    # merge Fc and Fc_storage series if required
    pfp_ts.CombineSeries(cf, ds3, l3_info["Fc"]["combine_list"], save_originals=True)
    # correct Fc for storage term - only recommended if storage calculated from profile available
    pfp_ts.CorrectFcForStorage(cf, ds3)
    # *************************
    # *** Radiation section ***
    # *************************
    # merge the incoming shortwave radiation
    pfp_ts.CombineSeries(cf, ds3, 'Fsd')
    # calculate the net radiation from the Kipp and Zonen CNR1
    pfp_ts.CalculateNetRadiation(cf, ds3)
    pfp_ts.CombineSeries(cf, ds3, 'Fn')
    # ****************************************
    # *** Wind speed and direction section ***
    # ****************************************
    # combine wind speed from the Wind Sentry and the SONIC
    pfp_ts.CombineSeries(cf,ds3, 'Ws')
    # combine wind direction from the Wind Sentry and the SONIC
    pfp_ts.CombineSeries(cf,ds3, 'Wd')
    # ********************
    # *** Soil section ***
    # ********************
    # correct soil heat flux for storage
    #    ... either average the raw ground heat flux, soil temperature and moisture
    #        and then do the correction (OzFlux "standard")
    pfp_ts.CombineSeries(cf, ds3, 'Ts')
    pfp_ts.CombineSeries(cf, ds3, 'Sws')
    if pfp_utils.get_optionskeyaslogical(cf, "CorrectIndividualFg"):
        #    ... or correct the individual ground heat flux measurements (James' method)
        pfp_ts.CorrectIndividualFgForStorage(cf, ds3)
        pfp_ts.CombineSeries(cf, ds3, 'Fg')
    else:
        pfp_ts.CombineSeries(cf, ds3, 'Fg')
        pfp_ts.CorrectFgForStorage(cf, ds3)
    # calculate the available energy
    pfp_ts.CalculateAvailableEnergy(ds3)
    # create new series using MergeSeries or AverageSeries
    pfp_ck.CreateNewSeries(cf, ds3)
    # Calculate Monin-Obukhov length
    pfp_ts.CalculateMoninObukhovLength(ds3)
    # re-apply the quality control checks (range, diurnal and rules)
    pfp_ck.do_qcchecks(cf, ds3)
    # check missing data and QC flags are consistent
    pfp_utils.CheckQCFlags(ds3)
    # get the statistics for the QC flags and write these to an Excel spreadsheet
    pfp_io.get_seriesstats(cf, ds3)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds3)
    # write the percentage of good data for groups
    pfp_utils.get_coverage_groups(ds3)
    # remove intermediate series from the data structure
    pfp_ts.RemoveIntermediateSeries(ds3, l3_info)
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
    pfp_ts.CalculateMeteorologicalVariables(ds4, l4_info)
    # check for any missing data
    pfp_utils.get_missingingapfilledseries(ds4, l4_info)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds4)
    # write the percentage of good data for groups
    pfp_utils.get_coverage_groups(ds4)
    # remove intermediate series from the data structure
    pfp_ts.RemoveIntermediateSeries(ds4, l4_info)

    return ds4

def l5qc(main_gui, cf, ds4):
    ds5 = pfp_io.copy_datastructure(cf, ds4)
    # ds5 will be empty (logical false) if an error occurs in copy_datastructure
    # return from this routine if this is the case
    if not ds5:
        return ds5
    # set some attributes for this level
    pfp_utils.UpdateGlobalAttributes(cf, ds5, "L5")
    # parse the control file for information on how the user wants to do the gap filling
    l5_info = pfp_gf.ParseL5ControlFile(cf, ds5)
    if ds5.returncodes["value"] != 0:
        return ds5
    # check to see if we have any imports
    pfp_gf.ImportSeries(cf, ds5)
    # re-apply the quality control checks (range, diurnal and rules)
    pfp_ck.do_qcchecks(cf, ds5)
    pfp_gf.CheckL5Drivers(ds5, l5_info)
    if ds5.returncodes["value"] != 0:
        return ds5
    # now do the flux gap filling methods
    # *** start of the section that does the gap filling of the fluxes ***
    pfp_gf.CheckGapLengths(cf, ds5, l5_info)
    if ds5.returncodes["value"] != 0:
        return ds5
    # apply the turbulence filter (if requested)
    pfp_ck.ApplyTurbulenceFilter(cf, ds5, l5_info)
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
    # check that all targets were gap filled
    pfp_gf.CheckL5Targets(ds5, l5_info)
    if ds5.returncodes["value"] != 0:
        return ds5
    # calculate Monin-Obukhov length
    pfp_ts.CalculateMoninObukhovLength(ds5)
    # write the percentage of good data as a variable attribute
    pfp_utils.get_coverage_individual(ds5)
    # write the percentage of good data for groups
    pfp_utils.get_coverage_groups(ds5)
    # remove intermediate series from the data structure
    pfp_ts.RemoveIntermediateSeries(ds5, l5_info)

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
    pfp_utils.CheckFcUnits(ds6, "umol/m2/s", convert_units=True)
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
    pfp_rp.ERUsingLloydTaylor(cf, ds6, l6_info)
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
    # remove intermediate series from the data structure
    pfp_ts.RemoveIntermediateSeries(ds6, l6_info)
    # do the L6 summary
    pfp_rp.L6_summary(cf, ds6)

    return ds6
