#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 15 13:53:16 2018

@author: ian
"""

import datetime as dt
from lmfit import Model
import matplotlib.pyplot as plt
import numpy as np
import operator
import pandas as pd
import pdb

#------------------------------------------------------------------------------
# Init
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
class partition(object):
    """
    Class for fitting of respiration parameters and estimation of respiration
    WARNING - NO FILTERING OR DATA INTEGRITY CHECKS APPLIED HERE!!!
    To do - add separate method for integrity checks on user-supplied args
    
    Args:
        * dataframe (pd.dataframe): containing a minimum of temperature, solar 
          radiation, VPD and CO2 flux.
    Kwargs:
        * names_dict (dict): maps the variable names used in the dataset to 
          common names (keys must be 'air_temperature', 'soil_temperature', 
          'insolation', 'Cflux'); if None, defaults to the internal 
          specification, which works for PyFluxPro.
        * weights (str, or list of ints / floats): if str, must be either 
          'air' or 'soil', which determines which temperature series is used 
          for the fit; if list is supplied, it must have two numbers (ints or 
          floats), which are used for the weighting in the ratio air:soil 
          e.g. choice of [3, 1] would cause weighting of 3:1 in favour of air 
          temperature, or e.g. [1, 3] would result in the reverse.
    """
    def __init__(self, dataframe, names_dict = None, fit_daytime_rb = False, 
                 weights_air_soil = 'air', noct_threshold = 10, 
                 convert_to_photons = True):

        interval = int(filter(lambda x: x.isdigit(), 
                              pd.infer_freq(dataframe.index)))
        assert interval % 30 == 0
        self.interval = interval 
        if not names_dict: 
            self.external_names = self._define_default_external_names()
        else:
            self.external_names = names_dict
        self.internal_names = self._define_default_internal_names()
        self.convert_to_photons = convert_to_photons
        self.weighting = _check_weights_format(weights_air_soil)
        self.df = self._make_formatted_df(dataframe)
        if convert_to_photons:
            self.noct_threshold = noct_threshold * 0.46 * 4.6
        else:
            self.noct_threshold = noct_threshold
        self._fit_daytime_rb = fit_daytime_rb
#------------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    # Methods
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def day_params(self, date, Eo, window_size, priors_dict):
        
        def model_fit(these_params):
            return model.fit(df.NEE,
                             par_series = df.PPFD, vpd_series = df.VPD, 
                             t_series = df.TC, params = these_params)
            
        if self._fit_daytime_rb:
            rb_prior = priors_dict['rb']
        else:
            rb_prior = self.nocturnal_params(date, Eo, window_size, 
                                             priors_dict)['rb']
        beta_prior = priors_dict['beta']
        df = self.get_subset(date, size = window_size, mode = 'day')
        try:
            if not len(df) > 4: 
                raise RuntimeError('insufficient data for fit')
            f = _NEE_model
            model = Model(f, independent_vars = ['par_series', 'vpd_series',
                                                 't_series'])
            params = model.make_params(rb = rb_prior, Eo = Eo,
                                       alpha = priors_dict['alpha'],
                                       beta = beta_prior, 
                                       k = priors_dict['k'])
            rmse_list, params_list = [], []
            for this_beta in [beta_prior, beta_prior / 2, beta_prior * 2]:
                params['beta'].value = this_beta
                params['Eo'].vary = False
                params['rb'].vary = self._fit_daytime_rb
                result = model_fit(these_params = params)
                if result.params['rb'] < 0: 
                    raise RuntimeError('rb parameter out of range')
                if not 0 <= result.params['k'].value <= 10:
                    params['k'].value = priors_dict['k']
                    params['k'].vary = False
                    result = model_fit(these_params = params)
                if not -0.22 <= result.params['alpha'].value <= 0:
                    params['alpha'].value = priors_dict['alpha']
                    params['alpha'].vary = False
                    result = model_fit(these_params = params)
                if not -100 <= result.params['beta'].value <= 0: 
                    raise RuntimeError('beta parameter out of range')
                rmse_list.append(np.sqrt(((df.NEE - result.best_fit)**2).sum()))
                params_list.append(result.best_values)
            idx = rmse_list.index(min(rmse_list))
            priors_dict['alpha'] = result.best_values['alpha']
            return params_list[idx]
        except RuntimeError, e:
            priors_dict['alpha'] = 0
            raise RuntimeError(e)
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    """Defines the internal names used by the algorithm"""
    
    def _define_default_internal_names(self):

        return {'Cflux': 'NEE',
                'air_temperature': 'Ta',
                'soil_temperature': 'Ts',
                'insolation': 'PPFD',
                'vapour_pressure_deficit': 'VPD'}
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    """Maps the variable names in the external dataset to generic variable
       references"""
    
    def _define_default_external_names(self):

        return {'Cflux': 'Fc',
                'air_temperature': 'Ta',
                'soil_temperature': 'Ts',
                'insolation': 'Fsd',
                'vapour_pressure_deficit': 'VPD'}
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def estimate_Eo(self, window_size = 15, window_step = 5, get_stats = False):
        
        """Estimate the activation energy type parameter for the L&T Arrhenius
           style equation using nocturnal data"""
        
        Eo_list = []
        for date in self.make_date_iterator(window_size, window_step):
            df = self.get_subset(date, size = window_size, mode = 'night')
            if not len(df) > 6: continue
            if not df.TC.max() - df.TC.min() >= 5: continue
            f = _Lloyd_and_Taylor
            model = Model(f, independent_vars = ['t_series'])
            params = model.make_params(rb = 1, 
                                       Eo = self.prior_parameter_estimates()['Eo'])
            result = model.fit(df.NEE,
                               t_series = df.TC,
                               params = params)
            if not 50 < result.params['Eo'].value < 400: continue
            se = (result.conf_interval()['Eo'][4][1] - 
                  result.conf_interval()['Eo'][2][1]) / 2
            if se > result.params['Eo'].value / 2.0: continue
            Eo_list.append([result.params['Eo'].value, se])
        if len(Eo_list) == 0: raise RuntimeError('Could not find any valid '
                                                 'estimates of Eo! Exiting...')
        print ('Found {} valid estimates of Eo'.format(str(len(Eo_list))))
        Eo_array = np.array(Eo_list)
        Eo = ((Eo_array[:, 0] / (Eo_array[:, 1])).sum() / 
              (1 / Eo_array[:, 1]).sum())
        if not 50 < Eo < 400: raise RuntimeError('Eo value {} outside '
                                                 'acceptable parameter range '
                                                 '(50-400)! Exiting...'
                                                 .format(str(round(Eo, 2))))
        return Eo
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def estimate_er_time_series(self, params_df = False):
        
        if not isinstance(params_df, pd.core.frame.DataFrame):
            params_df = self.estimate_parameters(mode = 'night')
        resp_series = pd.Series()
        for date in params_df.index:
            params = params_df.loc[date]
            str_date = dt.datetime.strftime(date, '%Y-%m-%d')
            data = self.df.loc[str_date, 'TC']
            resp_series = resp_series.append(_Lloyd_and_Taylor
                                             (t_series = data, 
                                              Eo = params.Eo, rb = params.rb))
        return resp_series
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def estimate_gpp_time_series(self, params_df = False):
        
        if not isinstance(params_df, pd.core.frame.DataFrame):
            params_df = self.estimate_parameters(mode = 'day')
        gpp_series = pd.Series()
        for date in params_df.index:
            params = params_df.loc[date]
            str_date = dt.datetime.strftime(date, '%Y-%m-%d')
            data = self.df.loc[str_date, ['PPFD', 'VPD']]
            gpp_series = gpp_series.append(_rectangular_hyperbola
                                           (par_series = data.PPFD,
                                            vpd_series = data.VPD,
                                            alpha = params.alpha,
                                            beta = params.beta,
                                            k = params.k))
        
        return gpp_series
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def estimate_nee_time_series(self, params_df = False, 
                                 splice_with_obs = False):
        return (self.estimate_gpp_time_series(params_df) + 
                self.estimate_er_time_series(params_df))
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def estimate_parameters(self, mode, Eo = None, window_size = 4, 
                            window_step = 4):
        
        priors_dict = self.prior_parameter_estimates()
        func = self._get_func()[mode]
        if not Eo: Eo = self.estimate_Eo()
        result_list, date_list = [], []
        print 'Processing the following dates ({} mode): '.format(mode)
        for date in self.make_date_iterator(window_size, window_step):
            print date.date(),
            try:
                result_list.append(func(date, Eo, window_size, priors_dict))
                date_list.append(date)
                print
            except RuntimeError, e:
                print '- {}'.format(e)
                continue
        full_date_list = np.unique(self.df.index.date)
        flag = pd.Series(0, index = date_list, name = 'Fill_flag')
        flag = flag.reindex(pd.date_range(full_date_list[0], full_date_list[-1], 
                                          freq='D'))
        flag.fillna(1, inplace = True)
        out_df = pd.DataFrame(result_list, index = date_list)
        out_df = out_df.resample('D').interpolate()
        out_df = out_df.reindex(np.unique(self.df.index.date))
        out_df.fillna(method = 'bfill', inplace = True)
        out_df.fillna(method = 'ffill', inplace = True)
        return out_df.join(flag)
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def _get_func(self):
        
        return {'night': self.nocturnal_params, 'day': self.day_params}
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def get_subset(self, date, size, mode):
        
        ops = {"day": operator.gt, "night": operator.lt}
        ref_date = date + dt.timedelta(0.5)
        date_tuple = (ref_date - dt.timedelta(size / 2.0 - 
                                              self.interval / 1440.0),
                      ref_date + dt.timedelta(size / 2.0))
        sub_df = self.df.loc[date_tuple[0]: date_tuple[1], 
                             ['NEE', 'PPFD', 'TC', 'VPD']].dropna()
        return sub_df[ops[mode](sub_df.PPFD, self.noct_threshold)]
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def make_date_iterator(self, size, step):
        
        start_date = (self.df.index[0].to_pydatetime().date() + 
                      dt.timedelta(size / 2))
        end_date = self.df.index[-1].to_pydatetime().date()
        return pd.date_range(start_date, end_date, 
                             freq = '{}D'.format(str(step)))
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def _make_formatted_df(self, df):
        
        """Update this to check for soil temperature - if not there, default
           to Ta"""
        
        sub_df = _rename_df(df, self.external_names, self.internal_names)
        if self.convert_to_photons: sub_df['PPFD'] = sub_df['PPFD'] * 0.46 * 4.6
        if self.weighting == 'air': s = sub_df['Ta'].copy()
        if self.weighting == 'soil': s = sub_df['Ts'].copy()
        if isinstance(self.weighting, list):
            s = (sub_df['Ta'] * self.weighting[0] + 
                 sub_df['Ts'] * self.weighting[1]) / sum(self.weighting)
        s.name = 'TC'
        return sub_df.join(s)
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def nocturnal_params(self, date, Eo, window_size, priors_dict):
        
        df = self.get_subset(date, size = window_size, mode = 'night')
        if not len(df) > 2: raise RuntimeError('insufficient data for fit')
        f = _Lloyd_and_Taylor
        model = Model(f, independent_vars = ['t_series'])
        params = model.make_params(rb = priors_dict['rb'], 
                                   Eo = Eo)
        params['Eo'].vary = False
        result = model.fit(df.NEE,
                           t_series = df.TC, 
                           params = params)
        if result.params['rb'].value < 0: raise RuntimeError('rb parameter '
                                                             'out of range')
        return result.best_values
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def plot_er(self, date, window_size = 15, Eo = None):

        state = self._fit_daytime_rb
        df = self.get_subset(date, size = window_size, mode = 'night')        
        assert len(df) > 0
        if not Eo: Eo = self.estimate_Eo()
        results_dict = {}
        try:
            results_dict['night'] = (
                    self.nocturnal_params(date, Eo, window_size,
                                          self.prior_parameter_estimates()))['rb']
        except RuntimeError, e:
            print ('Fit of nocturnal rb failed with the following message {}'
                   .format(e))
        try:
            self._fit_daytime_rb = True            
            results_dict['day'] = (
                    self.day_params(date, Eo, window_size, 
                                    self.prior_parameter_estimates()))['rb']
        except RuntimeError, e:
            print ('Fit of daytime rb failed with the following message {}'
                   .format(e))
        self._fit_daytime_rb = state
        fig, ax = plt.subplots(1, 1, figsize = (14, 8))
        fig.patch.set_facecolor('white')
        ax.axhline(0, color = 'black')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.tick_params(axis = 'y', labelsize = 14)
        ax.tick_params(axis = 'x', labelsize = 14)
        ax.set_title(dt.datetime.strftime(date, '%Y-%m-%d'), fontsize = 18)
        ax.set_xlabel('$Temperature\/(^oC)$', fontsize = 18)
        ax.set_ylabel('$NEE\/(\mu molC\/m^{-2}\/s^{-1})$', fontsize = 18)
        labels_dict = {'night': 'Night Eo and rb', 'day': 'Night Eo, day rb'}
        styles_dict = {'night': '--', 'day': ':'}
        ax.plot(df.TC, df.NEE, color = 'None', marker = 'o', 
                mfc = 'grey', mec = 'black', ms = 8, alpha = 0.5,
                label = 'Observations')
        df['TC_alt'] = np.linspace(df.TC.min(), df.TC.max(), len(df))
        for key in results_dict.keys():
            s = _Lloyd_and_Taylor(t_series = df.TC_alt, rb = results_dict[key],
                                  Eo = Eo)
            ax.plot(df.TC_alt, s, color = 'black', ls = styles_dict[key], 
                    label = labels_dict[key])
        ax.legend(loc = [0.05, 0.8], fontsize = 12)
        return fig
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def plot_nee(self, date, window_size = 15, Eo = None):
        
        state = self._fit_daytime_rb
        df = self.get_subset(date, size = window_size, mode = 'day')
        assert len(df) > 0
        if not Eo: Eo = self.estimate_Eo()
        results_dict = {}
        try:
            self._fit_daytime_rb = False
            results_dict['night'] = (self.day_params(date, Eo, window_size,
                                     self.prior_parameter_estimates()))
        except RuntimeError, e:
            print ('Fit of daytime parameters and nocturnal rb failed with '
                   'the following message {}'.format(e))
        try:
            self._fit_daytime_rb = True            
            results_dict['day'] = (self.day_params(date, Eo, window_size, 
                                   self.prior_parameter_estimates()))
        except RuntimeError, e:
            print ('Fit of daytime parameters and rb failed with the '
                   'following message {}'.format(e))
        self._fit_daytime_rb = state            
        fig, ax = plt.subplots(1, 1, figsize = (14, 8))
        fig.patch.set_facecolor('white')
        ax.axhline(0, color = 'black')
        ax.set_xlim([0, df.PPFD.max() * 1.05])
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.tick_params(axis = 'y', labelsize = 14)
        ax.tick_params(axis = 'x', labelsize = 14)
        ax.set_title(dt.datetime.strftime(date.to_pydatetime(), '%Y-%m-%d'),
                     fontsize = 18)
        ax.set_xlabel('$PPFD\/(\mu mol\/photons\/m^{-2}\/s^{-1})$', 
                      fontsize = 18)
        ax.set_ylabel('$NEE\/(\mu molC\/m^{-2}\/s^{-1})$', fontsize = 18)
        labels_dict = {'night': 'Night Eo and rb', 'day': 'Night Eo, day rb'}
        markers_dict = {'night': '+', 'day': 'x'}
        colors_dict = {'night': 'blue', 'day': 'magenta'}
        ax.plot(df.PPFD, df.NEE, color = 'None', marker = 'o', 
                mfc = 'grey', mec = 'black', ms = 8, alpha = 0.5,
                label = 'Observations')
        for key in results_dict.keys():
            params = results_dict[key]
            s = _NEE_model(par_series=df.PPFD, vpd_series=df.VPD, 
                           t_series=df.TC, rb = params['rb'], 
                           Eo = params['Eo'], alpha = params['alpha'],
                           beta = params['beta'], k = params['k'])
            ax.plot(df.PPFD, s, color = colors_dict[key], 
                    marker = markers_dict[key], label = labels_dict[key],
                    ls = 'None')
        ax.legend(loc = [0.05, 0.1], fontsize = 12)
        return fig
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def prior_parameter_estimates(self):
        
        return {'rb': self.df.loc[self.df.PPFD < self.noct_threshold, 
                                  'NEE'].mean(),
                'Eo': 100,
                'alpha': -0.01,
                'beta': (self.df.loc[self.df.PPFD > self.noct_threshold, 
                                     'NEE'].quantile(0.03)-
                          self.df.loc[self.df.PPFD > 10, 
                                      'NEE'].quantile(0.97)),
                'k': 0}
    #--------------------------------------------------------------------------    
    
#------------------------------------------------------------------------------
def _check_weights_format(weighting):
    
    try:
        assert isinstance(weighting, (str, list))
    except AssertionError:
        raise TypeError('"weighting" kwarg must be either string or list')
    try:    
        if isinstance(weighting, str):
            assert weighting in ['air', 'soil']
            return weighting
    except AssertionError:
        raise TypeError('if str passed for "weighting" kwarg, it must '
                           'be either "air" or "soil"')
    try:
        if isinstance(weighting, list):
            assert len(weighting) == 2
            for x in weighting:
                assert isinstance(x, (int, float))
            return weighting
    except AssertionError:
        raise TypeError('if list passed for weighting kwarg, it must '
                        'conists of only 2 elements, each of which must '
                        'be of type int or float')
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
"""Arrhenius style equation as used in Lloyd and Taylor 1994"""

def _Lloyd_and_Taylor(t_series, rb, Eo):

    return rb  * np.exp(Eo * (1 / (10 + 46.02) - 1 / (t_series + 46.02)))
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
"""Rectangular hyperbola as used in Lasslop et al 2010"""

def _rectangular_hyperbola(par_series, vpd_series, alpha, beta, k):
    
    beta_VPD = beta * np.exp(-k * (vpd_series - 1))
    index = vpd_series <= 1
    beta_VPD[index] = beta
    GPP = (alpha * par_series) / (1 - (par_series / 2000) + 
           (alpha * par_series / beta_VPD))    
    index = par_series < 5
    GPP[index] = 0
    return GPP
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------    
"""Complete model containing both temperature and ligh response functions"""

def _NEE_model(par_series, vpd_series, t_series, rb, Eo, alpha, beta, k):
    
    return (_rectangular_hyperbola(par_series, vpd_series, alpha, beta, k) + 
            _Lloyd_and_Taylor(t_series, rb, Eo))
#------------------------------------------------------------------------------
    
#------------------------------------------------------------------------------
"""Convert external names to internal names"""

def _rename_df(df, external_names, internal_names):
    
    assert sorted(external_names.keys()) == sorted(internal_names.keys())
    swap_dict = {external_names[key]: internal_names[key] 
                 for key in internal_names.keys()}
    sub_df = df[swap_dict.keys()].copy()
    sub_df.columns = swap_dict.values()
    return sub_df    
#------------------------------------------------------------------------------