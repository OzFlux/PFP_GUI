"""Routines for the Lasslop and Lloyd and Taylor partitioning"""

# standard modules
import datetime
import logging
import os
import warnings
# 3rd party modules
import matplotlib
import matplotlib.pyplot as plt
import numpy
from scipy.optimize import curve_fit, OptimizeWarning
# PFP modules
import constants as c
import pfp_cfg
import pfp_gui
import pfp_utils

import pdb

def rp_initplot(**kwargs):
    # set the margins, heights, widths etc
    pd = {"margin_bottom":0.075,"margin_top":0.075,"margin_left":0.05,"margin_right":0.05,
          "xy_height":0.20,"xy_width":0.20,"xyts_space":0.05,"xyts_space":0.05,
          "ts_width":0.9}
    # set the keyword arguments
    for key, value in kwargs.iteritems():
        pd[key] = value
    # calculate bottom of the first time series and the height of the time series plots
    pd["ts_bottom"] = pd["margin_bottom"]+pd["xy_height"]+pd["xyts_space"]
    pd["ts_height"] = (1.0 - pd["margin_top"] - pd["ts_bottom"])/float(pd["nDrivers"]+1)
    return pd

def rp_plot(pd, ds, output, drivers, target, iel, called_by, si=0, ei=-1):
    """ Plot the results of the respiration run """
    mode_dict = {'ERUsingLasslop': 'LL', 'ERUsingLloydTaylor': 'LT'}
    mode = mode_dict[called_by]
    
    if called_by == 'ERUsingLasslop': mode = 'LL'
    if called_by == 'ERUsingLloydTaylor': mode = 'LT'
    
    ieli = iel["info"]
    ielo = iel["outputs"]
    # get a local copy of the datetime series
    if ei == -1:
        dt = ds.series['DateTime']['Data'][si:]
    else:
        dt = ds.series['DateTime']['Data'][si:ei+1]
    xdt = numpy.array(dt)
    Hdh, f, a = pfp_utils.GetSeriesasMA(ds, 'Hdh', si=si, ei=ei)
    # get the observed and modelled values
    obs, f, a = pfp_utils.GetSeriesasMA(ds, target, si=si, ei=ei)
    mod, f, a = pfp_utils.GetSeriesasMA(ds, output, si=si, ei=ei)
    # make the figure
    if iel["gui"]["show_plots"]:
        plt.ion()
    else:
        plt.ioff()
    fig = plt.figure(pd["fig_num"], figsize=(13, 8))
    fig.clf()
    fig.canvas.set_window_title(target + " (" + mode + "): " + pd["startdate"] 
                                + " to " + pd["enddate"])
    plt.figtext(0.5, 0.95, pd["title"], ha='center', size=16)
    # XY plot of the diurnal variation
    rect1 = [0.10, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax1 = plt.axes(rect1)
    # get the diurnal stats of the observations
    mask = numpy.ma.mask_or(obs.mask, mod.mask)
    obs_mor = numpy.ma.array(obs, mask=mask)
    dstats = pfp_utils.get_diurnalstats(dt, obs_mor, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'b-', label="Obs")
    # get the diurnal stats of all predictions
    dstats = pfp_utils.get_diurnalstats(dt, mod, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'r-', label=mode + "(all)")
    mod_mor = numpy.ma.masked_where(numpy.ma.getmaskarray(obs) == True, mod, copy=True)
    dstats = pfp_utils.get_diurnalstats(dt, mod_mor, ieli)
    ax1.plot(dstats["Hr"], dstats["Av"], 'g-', label=mode + "(obs)")
    plt.xlim(0, 24)
    plt.xticks([0, 6, 12, 18, 24])
    ax1.set_ylabel(target)
    ax1.set_xlabel('Hour')
    ax1.legend(loc='upper right', frameon=False, prop={'size':8})
    # XY plot of the 30 minute data
    rect2 = [0.40, pd["margin_bottom"], pd["xy_width"], pd["xy_height"]]
    ax2 = plt.axes(rect2)
    ax2.plot(mod, obs, 'b.')
    ax2.set_ylabel(target + '_obs')
    ax2.set_xlabel(target + '_' + mode)
    # plot the best fit line
    coefs = numpy.ma.polyfit(numpy.ma.copy(mod), numpy.ma.copy(obs), 1)
    xfit = numpy.ma.array([numpy.ma.minimum.reduce(mod), numpy.ma.maximum.reduce(mod)])
    yfit = numpy.polyval(coefs, xfit)
    r = numpy.ma.corrcoef(mod, obs)
    ax2.plot(xfit, yfit, 'r--', linewidth=3)
    eqnstr = 'y = %.3fx + %.3f, r = %.3f'%(coefs[0], coefs[1], r[0][1])
    ax2.text(0.5, 0.875, eqnstr, fontsize=8, horizontalalignment='center', transform=ax2.transAxes)
    # write the fit statistics to the plot
    numpoints = numpy.ma.count(obs)
    numfilled = numpy.ma.count(mod)-numpy.ma.count(obs)
    diff = mod - obs
    bias = numpy.ma.average(diff)
    ielo[output]["results"]["Bias"].append(bias)
    rmse = numpy.ma.sqrt(numpy.ma.mean((obs-mod)*(obs-mod)))
    plt.figtext(0.725, 0.225, 'No. points')
    plt.figtext(0.825, 0.225, str(numpoints))
    ielo[output]["results"]["No. points"].append(numpoints)
    plt.figtext(0.725, 0.200, 'No. filled')
    plt.figtext(0.825, 0.200, str(numfilled))
    plt.figtext(0.725, 0.175, 'Slope')
    plt.figtext(0.825, 0.175, str(pfp_utils.round2sig(coefs[0], sig=4)))
    ielo[output]["results"]["m_ols"].append(coefs[0])
    plt.figtext(0.725, 0.150, 'Offset')
    plt.figtext(0.825, 0.150, str(pfp_utils.round2sig(coefs[1], sig=4)))
    ielo[output]["results"]["b_ols"].append(coefs[1])
    plt.figtext(0.725, 0.125, 'r')
    plt.figtext(0.825, 0.125, str(pfp_utils.round2sig(r[0][1], sig=4)))
    ielo[output]["results"]["r"].append(r[0][1])
    plt.figtext(0.725, 0.100, 'RMSE')
    plt.figtext(0.825, 0.100, str(pfp_utils.round2sig(rmse, sig=4)))
    ielo[output]["results"]["RMSE"].append(rmse)
    var_obs = numpy.ma.var(obs)
    ielo[output]["results"]["Var (obs)"].append(var_obs)
    var_mod = numpy.ma.var(mod)
    ielo[output]["results"]["Var (" + mode + ")"].append(var_mod)
    ielo[output]["results"]["Var ratio"].append(var_obs/var_mod)
    ielo[output]["results"]["Avg (obs)"].append(numpy.ma.average(obs))
    ielo[output]["results"]["Avg (" + mode + ")"].append(numpy.ma.average(mod))
    # time series of drivers and target
    ts_axes = []
    rect = [pd["margin_left"], pd["ts_bottom"], pd["ts_width"], pd["ts_height"]]
    ts_axes.append(plt.axes(rect))
    #ts_axes[0].plot(xdt,obs,'b.',xdt,mod,'r-')
    ts_axes[0].scatter(xdt, obs, c=Hdh)
    ts_axes[0].plot(xdt, mod, 'r-')
    plt.axhline(0)
    ts_axes[0].set_xlim(xdt[0], xdt[-1])
    TextStr = target + '_obs (' + ds.series[target]['Attr']['units'] + ')'
    ts_axes[0].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[0].transAxes)
    TextStr = output + '(' + ds.series[output]['Attr']['units'] + ')'
    ts_axes[0].text(0.85, 0.85, TextStr, color='r', horizontalalignment='right', transform=ts_axes[0].transAxes)
    for ThisOne, i in zip(drivers, range(1, pd["nDrivers"] + 1)):
        this_bottom = pd["ts_bottom"] + i*pd["ts_height"]
        rect = [pd["margin_left"], this_bottom, pd["ts_width"], pd["ts_height"]]
        ts_axes.append(plt.axes(rect, sharex=ts_axes[0]))
        data, flag, attr = pfp_utils.GetSeriesasMA(ds, ThisOne, si=si, ei=ei)
        data_notgf = numpy.ma.masked_where(flag != 0, data)
        data_gf = numpy.ma.masked_where(flag == 0, data)
        ts_axes[i].plot(xdt, data_notgf, 'b-')
        ts_axes[i].plot(xdt, data_gf, 'r-')
        plt.setp(ts_axes[i].get_xticklabels(), visible=False)
        TextStr = ThisOne + '(' + ds.series[ThisOne]['Attr']['units'] + ')'
        ts_axes[i].text(0.05, 0.85, TextStr, color='b', horizontalalignment='left', transform=ts_axes[i].transAxes)
    # save a hard copy of the plot
    sdt = xdt[0].strftime("%Y%m%d")
    edt = xdt[-1].strftime("%Y%m%d")
    if not os.path.exists(ieli["plot_path"]):
        os.makedirs(ieli["plot_path"])
    figname = (ieli["plot_path"] + pd["site_name"].replace(" ","") + 
               "_" + mode + "_" + pd["label"])
    figname = figname + "_" + sdt + "_" + edt + '.png'
    fig.savefig(figname, format='png')
    # draw the plot on the screen
    if iel["gui"]["show_plots"]:
        plt.draw()
        #plt.pause(1)
        mypause(1)
        plt.ioff()
    else:
        plt.close(fig)
        plt.ion()
        
def mypause(interval):
    backend = plt.rcParams['backend']
    if backend in matplotlib.rcsetup.interactive_bk:
        figManager = matplotlib._pylab_helpers.Gcf.get_active()
        if figManager is not None:
            canvas = figManager.canvas
            if canvas.figure.stale:
                canvas.draw()
            canvas.start_event_loop(interval)
            return