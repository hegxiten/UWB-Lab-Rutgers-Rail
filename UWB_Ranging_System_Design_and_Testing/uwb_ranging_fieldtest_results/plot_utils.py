import os, re
import json
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter
from scipy.linalg.special_matrices import dft
import seaborn as sns

from datetime import datetime
import math
import pandas as pd
from itertools import chain

from utils import post_process_get_moving_test_data_and_timestamp, remove_outlier_by_quantile
from stats_utils import *

from collections import defaultdict

from pandas.core.common import SettingWithCopyWarning
import warnings
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
CALIBRATED_CAM_TO_V2B = -6400.8
pd.set_option('display.float_format', lambda x: '%.5f' % x)


MAX_UPD_RATE = 40
NUL_UPD_RATE = 0
MARKER_SIZE = 20


TICK_FONT_SIZE = 10
LABEL_FONT_SIZE = 12
AXES_TITLE_SIZE = 14

import matplotlib 
matplotlib.rc('font', size=TICK_FONT_SIZE)
matplotlib.rc('xtick', labelsize=TICK_FONT_SIZE) 
matplotlib.rc('ytick', labelsize=TICK_FONT_SIZE)
matplotlib.rc('axes', labelsize=LABEL_FONT_SIZE) 
matplotlib.rc('axes', titlesize=AXES_TITLE_SIZE)
matplotlib.rc('legend', fontsize=LABEL_FONT_SIZE)

def plot_single_test_data(raw_name, test_dataset, test_category, test_preset_map):
    parsing_results = test_dataset.get(raw_name)
    if not parsing_results:
        print(raw_name + " No Data, Not Plotting")
        return
    static_veh, moving_veh = test_preset_map['STATIC_VEH'], test_preset_map['MOVING_VEH']
    
    # Unpack dataframes
    df_outlier_overall = parsing_results["df_outlier_overall"]
    moving_ground_truth_df = parsing_results["moving_ground_truth_df"]
    for veh in parsing_results["vehicles"]:
        df_veh_time_idx = parsing_results[veh]["df_veh_time_idx"]
        df_veh_dist_idx = parsing_results[veh]["df_veh_dist_idx"]
        veh_err_bins = parsing_results[veh]["veh_err_bins"]
        df_stats_pairwise = parsing_results[veh]['df_stats_pairwise']
        df_stats_aggregated = parsing_results[veh]['df_stats_aggregated']
        veh_dist_bins = parsing_results[veh]["veh_dist_bins"]
        hist_disp_range = parsing_results[veh]["hist_disp_range"]
        if veh == static_veh:
            df_static_time_idx, static_dist_bins, static_error_bins = df_veh_time_idx, veh_dist_bins, veh_err_bins
            static_hist_disp_range = hist_disp_range
            df_static_dist_idx = df_veh_dist_idx
        elif veh == moving_veh:
            df_moving_time_idx, moving_dist_bins, moving_error_bins = df_veh_time_idx, veh_dist_bins, veh_err_bins
            moving_hist_disp_range = hist_disp_range
            df_moving_dist_idx = df_veh_dist_idx
    
    ######################################################
    # Plotting individual tests
    ######################################################
    if test_category == "Moving Test" or test_category == "Virtual Moving Test":
        print("plotting: " + raw_name)
        figure = plt.figure(figsize=(16, 9), dpi=test_preset_map['PLOTTING_DPI'])
        if "moving" in raw_name.split("-v2-")[0]:
            titlename = "Moving Test - " + raw_name.split("-v2-")[-1]
            figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
        elif "virtual" in raw_name.split("-v2-")[0]:
            titlename = "Virtual Moving Test - " + raw_name.split("-v2-")[-1]
            figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
        plot_time_series_dist(  figure=figure,
                                arrange_spec=411,
                                static_veh_df=df_static_time_idx,
                                moving_veh_df=df_moving_time_idx,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                df_outlier=df_outlier_overall,
                                surveyed_static_ground_truth_value=None,
                                moving_ground_truth_df=moving_ground_truth_df,
                                scatter=True)

        plot_upd_rate(  figure=figure,
                        arrange_spec=412,
                        static_veh_df=df_static_time_idx,
                        moving_veh_df=df_moving_time_idx,
                        static_veh=static_veh,
                        moving_veh=moving_veh,
                        moving_ground_truth_df=moving_ground_truth_df,
                        scatter=True)

        # Instant Speed UWB Strict
        # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
        plot_time_series_speed( figure=figure, 
                                arrange_spec=413, 
                                static_veh_df=df_static_time_idx, 
                                moving_veh_df=df_moving_time_idx,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                moving_ground_truth_df=moving_ground_truth_df,
                                scatter=True)
        
        plot_real_time_moving_errors(   figure=figure, 
                                        arrange_spec=414, 
                                        static_veh_df=df_static_time_idx, 
                                        moving_veh_df=df_moving_time_idx,
                                        static_veh=static_veh,
                                        moving_veh=moving_veh,
                                        moving_ground_truth_df=moving_ground_truth_df,
                                        scatter=True)
        
        ######################################################
        ########## Error Histogram ##########
        ######################################################
        
        titlename = "Histogram of Real-Time Measurement Errors (Interpolated)"
        figure_hist = plt.figure(figsize=(16, 9), dpi=test_preset_map['PLOTTING_DPI'])
        figure_hist.suptitle(titlename, fontsize='x-large', fontweight='bold')
        plot_hist_moving_err_hbar(  figure=figure_hist,
                                    static_veh=static_veh,
                                    moving_veh=moving_veh,
                                    real_time_err_static_veh=df_static_time_idx['Error (mm)'],
                                    real_time_err_moving_veh=df_moving_time_idx['Error (mm)'],
                                    bin_size_static=static_error_bins,
                                    bin_size_moving=moving_error_bins
                                    )
        
        ######################################################
        ########## RESAMPLED RESULTS ##########
        ######################################################
        figure_resample = plt.figure(figsize=(16, 9), dpi=test_preset_map['PLOTTING_DPI'])
        titlename = raw_name + " - Resampled"
        figure_resample.suptitle(titlename, fontsize='x-large', fontweight='bold')
        plot_time_series_dist(  figure=figure_resample,
                                arrange_spec=411,
                                static_veh_df=df_static_time_idx,
                                moving_veh_df=df_moving_time_idx,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                df_outlier=df_outlier_overall,
                                surveyed_static_ground_truth_value=None,
                                moving_ground_truth_df=moving_ground_truth_df,
                                resample=True,
                                scatter=False)

        plot_upd_rate(  figure=figure_resample,
                        arrange_spec=412,
                        static_veh_df=df_static_time_idx,
                        moving_veh_df=df_moving_time_idx,
                        static_veh=static_veh,
                        moving_veh=moving_veh,
                        moving_ground_truth_df=moving_ground_truth_df,
                        resample=True,
                        scatter=False)

        # Instant Speed UWB Strict
        # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
        plot_time_series_speed( figure=figure_resample, 
                                arrange_spec=413, 
                                static_veh_df=df_static_time_idx, 
                                moving_veh_df=df_moving_time_idx,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                moving_ground_truth_df=moving_ground_truth_df,
                                resample=True,
                                scatter=False)

        ######################################################
        ########## Distance-Update Rate Relationship #########
        ##########1. Excluding Loss of Connection ############
        figure_dist_idx_upd_rate = plt.figure(figsize=(16, 9), dpi=test_preset_map['PLOTTING_DPI'])
        titlename = raw_name + " - Normalized Update Rate (Aggregated Overall) v.s. Surveyed Distances, Excluding Connection Loss"
        figure_dist_idx_upd_rate.suptitle(titlename, fontsize='x-large', fontweight='bold')
        dist_binsize = 200 if not test_preset_map.get('dist_interval_size') else test_preset_map.get('dist_interval_size')
        interval_idx_stats_map = defaultdict(dict)
        for veh_dist_idx_df_list in [[df_static_dist_idx], [df_moving_dist_idx]]:
            veh = veh_dist_idx_df_list[0]['Initiating Vehicle'].unique()[0]
            interval_idx_stats_map[veh]['aggregated'] = dist_interval_idx_df_by_veh_all_tests(veh_dist_idx_df_list, dist_binsize, test_preset_map)
            interval_idx_stats_map[veh]['main'] = dist_interval_idx_df_by_veh_all_tests(  veh_dist_idx_df_list, 
                                                                                        dist_binsize,
                                                                                        test_preset_map,
                                                                                        main_pair=True)
        plot_dist_idx_udpate_rate(  figure=figure_dist_idx_upd_rate,
                                    interval_idx_stats_map=interval_idx_stats_map,
                                    static_veh=static_veh,
                                    moving_veh=moving_veh,
                                    test_preset_map=test_preset_map,
                                    dist_bin=dist_binsize)
        ######################################################
        ########## Distance-Update Rate Relationship #########
        ##########2. Including Loss of Connection ############
        figure_dist_idx_upd_rate_inc_loss = plt.figure(figsize=(16, 9), dpi=test_preset_map['PLOTTING_DPI'])
        titlename = raw_name + " - Normalized Update Rate (Aggregated Overall) v.s. Surveyed Distances, Including Connection Loss"
        figure_dist_idx_upd_rate_inc_loss.suptitle(titlename, fontsize='x-large', fontweight='bold')
        dist_binsize = 200 if not test_preset_map.get('dist_interval_size') else test_preset_map.get('dist_interval_size')
        interval_idx_stats_map_inc_loss = defaultdict(dict)
        for veh_dist_idx_df_list in [[df_static_dist_idx], [df_moving_dist_idx]]:
            veh = veh_dist_idx_df_list[0]['Initiating Vehicle'].unique()[0]
            interval_idx_stats_map_inc_loss[veh]['aggregated'] = dist_interval_idx_df_by_veh_all_tests_monotonic(veh_dist_idx_df_list, dist_binsize)
            interval_idx_stats_map_inc_loss[veh]['main'] = dist_interval_idx_df_by_veh_all_tests_monotonic( veh_dist_idx_df_list, 
                                                                                                            dist_binsize,
                                                                                                            test_preset_map[veh]['main_master'],
                                                                                                            test_preset_map[veh]['master_slave_mapping'][test_preset_map[veh]['main_master']][0])
        plot_dist_idx_udpate_rate(  figure=figure_dist_idx_upd_rate_inc_loss,
                                    interval_idx_stats_map=interval_idx_stats_map_inc_loss,
                                    static_veh=static_veh,
                                    moving_veh=moving_veh,
                                    test_preset_map=test_preset_map,
                                    dist_bin=dist_binsize)
        figure.tight_layout(pad=1.0)
        figure_hist.tight_layout(pad=1.0)
        figure_resample.tight_layout(pad=1.0)
        figure_dist_idx_upd_rate.tight_layout(pad=1.0)
        figure_dist_idx_upd_rate_inc_loss.tight_layout(pad=1.0)

    if test_category == "Static Test":
        static_surveyed_dist = df_static_time_idx["Surveyed Distance (mm)"].get(0, float('nan'))
        titlename = "Static Test - " + raw_name.split("-v2-")[-1]  + " - " + str(int(static_surveyed_dist)) + "mm"
        figure = plt.figure(figsize=(16, 9), dpi=test_preset_map['PLOTTING_DPI'])
        figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
        figure2 = plt.figure(figsize=(16, 9), dpi=test_preset_map['PLOTTING_DPI'])
        plot_time_series_dist(  figure=figure,
                                arrange_spec=221,
                                static_veh_df=df_static_time_idx,
                                moving_veh_df=df_moving_time_idx,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                df_outlier=df_outlier_overall,
                                surveyed_static_ground_truth_value=static_surveyed_dist,
                                moving_ground_truth_df=None,
                                fill=False,
                                resample=False, 
                                scatter=False)
        
        plot_upd_rate(  figure=figure,
                        arrange_spec=223,
                        static_veh_df=df_static_time_idx, 
                        moving_veh_df=df_moving_time_idx, 
                        static_veh=static_veh, 
                        moving_veh=moving_veh, 
                        moving_ground_truth_df=None,
                        resample=True, 
                        scatter=False)
        
        plot_hist(  figure=figure,  
                    arrange_spec=222, 
                    veh_df=df_static_time_idx,
                    bin_size=static_dist_bins,
                    ground_truth_value=static_surveyed_dist,
                    master_slave_mapping=test_preset_map[static_veh]['master_slave_mapping'],
                    disp_range=static_hist_disp_range,
                    hist_title="Hist - Vehicle {} (Static) against Vehicle {} (Mover)".format(static_veh, moving_veh))
        plot_hist(  figure=figure,  
                    arrange_spec=224, 
                    veh_df=df_moving_time_idx,
                    bin_size=moving_dist_bins, 
                    ground_truth_value=static_surveyed_dist,
                    master_slave_mapping=test_preset_map[moving_veh]['master_slave_mapping'],
                    disp_range=moving_hist_disp_range, 
                    hist_title="Hist - Vehicle {} (Mover) against Vehicle {} (Static)".format(moving_veh, static_veh))
        
        plot_hist_hbar( figure=figure2,  
                        veh1_df=df_static_time_idx,
                        veh2_df=df_moving_time_idx,
                        veh1_bin_size=static_dist_bins, 
                        veh2_bin_size=moving_dist_bins, 
                        ground_truth_value=static_surveyed_dist,
                        static_master_slave_mapping=test_preset_map[static_veh]['master_slave_mapping'],
                        moving_master_slave_mapping=test_preset_map[moving_veh]['master_slave_mapping'],                       
                        static_disp_range=static_hist_disp_range, 
                        moving_disp_range=moving_hist_disp_range, 
                        hist_title="Hist - Vehicle {} (Mover) against Vehicle {} (Static)".format(moving_veh, static_veh))
        figure.tight_layout(pad=1.0)
        figure2.tight_layout(pad=1.0)
    plt.show()
    


def plot_time_series_dist(  figure, 
                            arrange_spec, 
                            static_veh_df, 
                            moving_veh_df, 
                            static_veh, 
                            moving_veh, 
                            df_outlier,
                            surveyed_static_ground_truth_value, 
                            moving_ground_truth_df,
                            fill=True,
                            resample=False,
                            scatter=False,
                            ax=None):
    if not ax:
        ax = figure.add_subplot(arrange_spec)
    if resample:
        static_veh_df = static_veh_df.resample(rule=RESAMPLE_RULE).mean()
        moving_veh_df = moving_veh_df.resample(rule=RESAMPLE_RULE).mean()
    if not scatter:
        if fill:
            if moving_ground_truth_df is not None:
                min_fill = min( static_veh_df["Correction Distance (mm)"].min(), 
                                moving_veh_df["Correction Distance (mm)"].min(),
                                moving_ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"].min())
            else:
                min_fill = min( static_veh_df["Correction Distance (mm)"].min(), 
                                moving_veh_df["Correction Distance (mm)"].min())
            ax.fill_between(static_veh_df.index, 
                            static_veh_df["Correction Distance (mm)"], 
                            min_fill,
                            label="Static V{} against Mover V{} Distance & Flow".format(static_veh, moving_veh),
                            alpha=0.4,
                            color="C0", 
                            linestyle="--")
            ax.fill_between(moving_veh_df.index, 
                            moving_veh_df["Correction Distance (mm)"], 
                            min_fill,
                            label="Mover V{} against Static V{} Distance & Flow".format(moving_veh, static_veh),
                            alpha=0.4,
                            color="C1",
                            linestyle=":")
        else:
            ax.plot(static_veh_df.index, 
                    static_veh_df["Correction Distance (mm)"], 
                    label="Static V{} against Mover V{}".format(static_veh, moving_veh),
                    alpha=0.9,
                    color="C0", 
                    linestyle="-")
            ax.plot(moving_veh_df.index, 
                    moving_veh_df["Correction Distance (mm)"], 
                    label="Mover V{} against Static V{}".format(moving_veh, static_veh),
                    alpha=0.9,
                    color="C1",
                    linestyle="-")
    else:
        ax.scatter( static_veh_df.index, 
                    static_veh_df["Correction Distance (mm)"], 
                    label="Static V{} against Mover V{} Data Points".format(static_veh, moving_veh),
                    alpha=0.3,
                    color="C0",
                    s=MARKER_SIZE)
        ax.scatter( moving_veh_df.index, 
                    moving_veh_df["Correction Distance (mm)"], 
                    label="Mover V{} against Static V{} Data Points".format(moving_veh, static_veh),
                    alpha=0.3,
                    color="C1",
                    s=MARKER_SIZE)
        if not df_outlier.empty:
            ax.scatter(df_outlier.index, df_outlier["Correction Distance (mm)"], marker="x", color='r', label="Outliers")
    if surveyed_static_ground_truth_value:
        ax.axhline(y=surveyed_static_ground_truth_value, color="g", label="Manually Measured", alpha=0.9)
    else:
        if moving_ground_truth_df is not None:
            ax.plot(pd.to_datetime(moving_ground_truth_df["Time UNIX Norm (s)"],unit='s'), 
                    moving_ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"], 
                    label="Timestamped Location (Video)", 
                    marker='*',
                    markerfacecolor = 'r',
                    alpha=0.2,
                    linewidth=10, 
                    color="g")
            ax.axhline(y=0, color="r", label="Contact Point (Zero Distance)", alpha=0.9, linestyle="--")
            
    ax.set_title("Time Series Distance (mm)")
    time_stamp_lim = get_time_stamp_lim(pd.concat([static_veh_df, moving_veh_df]), moving_ground_truth_df)
    _time_span = time_stamp_lim[1] - time_stamp_lim[0]
    _xlim = [time_stamp_lim[0] - 0.1 * _time_span, time_stamp_lim[1] + 0.1 * _time_span]
    if not (pd.isnull(_xlim[0]) or pd.isnull(_xlim[1])):
        ax.set_xlim(_xlim)
    ax.set_xlabel("Time")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_ylabel("Distance (mm)")   
    ax.legend()
    figure.tight_layout(pad=1.0)


def plot_upd_rate(  figure, 
                    arrange_spec, 
                    static_veh_df, 
                    moving_veh_df, 
                    static_veh, 
                    moving_veh,
                    moving_ground_truth_df, 
                    resample=False,
                    scatter=True,
                    ax=None):
    if not ax:
        ax = figure.add_subplot(arrange_spec)
    if resample:
        static_veh_df = static_veh_df.resample(rule=RESAMPLE_RULE).mean()
        moving_veh_df = moving_veh_df.resample(rule=RESAMPLE_RULE).mean()
    if not scatter:
        ax.plot(static_veh_df.index, 
                static_veh_df["Aggregated Update Rate (Hz)"], 
                label="Static V{} against Mover V{}".format(static_veh, moving_veh),
                alpha=0.9,
                color='C0',
                linestyle="--")
        ax.plot(moving_veh_df.index, 
                moving_veh_df["Aggregated Update Rate (Hz)"], 
                label="Mover V{} against Static V{}".format(moving_veh, static_veh),
                alpha=0.9,
                color='C1',
                linestyle="--")
    else:
        ax.scatter(static_veh_df.index, 
                static_veh_df["Aggregated Update Rate (Hz)"], 
                label="Static V{} against Mover V{}".format(static_veh, moving_veh),
                alpha=0.3,
                color='C0',
                s=MARKER_SIZE)
        ax.scatter(moving_veh_df.index, 
                moving_veh_df["Aggregated Update Rate (Hz)"], 
                label="Mover V{} against Static V{}".format(moving_veh, static_veh),
                alpha=0.3,
                color='C1',
                s=MARKER_SIZE)
    
    ax.set_title("Aggregated Update Rate (Hz)")
    ax.set_xlabel("Time")
    time_stamp_lim = get_time_stamp_lim(pd.concat([static_veh_df, moving_veh_df]), moving_ground_truth_df)
    _time_span = time_stamp_lim[1] - time_stamp_lim[0]
    _xlim = [time_stamp_lim[0] - 0.1 * _time_span, time_stamp_lim[1] + 0.1 * _time_span]
    ax.set_xlim(_xlim)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_ylabel("Aggregated Update Rate (Hz)")

    # Span for missing values
    if resample:
        static_nan_slices = get_nan_slices_indices(static_veh_df, veh=static_veh, time_stamp_lim=time_stamp_lim)
        moving_nan_slices = get_nan_slices_indices(moving_veh_df, veh=moving_veh, time_stamp_lim=time_stamp_lim)
        for i in range(len(static_nan_slices)):
            slice = static_nan_slices[i]
            if len(slice) < 2:
                continue
            [slice_lo, slice_hi] = slice
            ax.axvspan( slice_lo, slice_hi,
                        facecolor='C0',
                        alpha=0.2,
                        label="_" * i + "V{} Signal Lost Period".format(static_veh),
                        hatch="/")

        for i in range(len(moving_nan_slices)):
            slice = moving_nan_slices[i]
            if len(slice) < 2:
                continue
            [slice_lo, slice_hi] = slice
            ax.axvspan( slice_lo, slice_hi,
                        facecolor='C1',
                        alpha=0.2,
                        label="_" * i + "V{} Signal Lost Period".format(moving_veh),
                        hatch="\\")
    ax.legend()

def plot_time_series_speed( figure, 
                            arrange_spec, 
                            static_veh_df, 
                            moving_veh_df, 
                            static_veh, 
                            moving_veh, 
                            moving_ground_truth_df, 
                            resample=False,
                            scatter=False):
    ax = figure.add_subplot(arrange_spec)
    if resample:
        static_veh_df = static_veh_df.resample(rule=RESAMPLE_RULE).mean()
        moving_veh_df = moving_veh_df.resample(rule=RESAMPLE_RULE).mean()
    if not scatter:
        ax.plot(static_veh_df.index, 
                static_veh_df["Aggregated Measured Speed (mph)"], 
                label="UWB Measured Relative Speed by V{}".format(static_veh),
                alpha=0.8,
                linestyle="--")
        ax.plot(moving_veh_df.index, 
                moving_veh_df["Aggregated Measured Speed (mph)"], 
                label="UWB Measured Relative Speed by V{}".format(moving_veh),
                alpha=0.8,
                linestyle=":")
    else:
        # Static
        ax.scatter(static_veh_df.index, 
                static_veh_df["Aggregated Measured Speed (mph)"], 
                label="UWB Measured Relative Speed by V{} Data Points".format(static_veh),
                alpha=0.3,
                s=MARKER_SIZE,
                color="C0")
        # Moving
        ax.scatter(moving_veh_df.index, 
                moving_veh_df["Aggregated Measured Speed (mph)"], 
                label="UWB Measured Relative Speed by V{} Data Points".format(moving_veh),
                alpha=0.3,
                s=MARKER_SIZE,
                color="C1")
    
    # Ground
    if moving_ground_truth_df is not None:
        ax.plot( pd.to_datetime(moving_ground_truth_df["Time UNIX Norm (s)"],unit='s'), 
                 moving_ground_truth_df["Instant Speed by Marker (mph)"], 
                 label="Ground Measured Speed (mph)", 
                 marker='*',
                 markerfacecolor = 'r',
                 alpha=0.2,
                 linewidth=10)
    ax.axhline(y=0, color='r', linestyle='dashed', label="Zero Speed")
    ax.set_title("Measured Speed By Vehicle (mph)")
    ax.set_xlabel("Time")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    time_stamp_lim = get_time_stamp_lim(pd.concat([static_veh_df, moving_veh_df]), moving_ground_truth_df)
    _time_span = time_stamp_lim[1] - time_stamp_lim[0]
    _xlim = [time_stamp_lim[0] - 0.1 * _time_span, time_stamp_lim[1] + 0.1 * _time_span]
    ax.set_xlim(_xlim)
    ax.set_ylabel("Speed (mph)")
    ax.legend()

def plot_real_time_moving_errors(   figure, 
                                    arrange_spec, 
                                    static_veh_df, 
                                    moving_veh_df, 
                                    static_veh, 
                                    moving_veh, 
                                    moving_ground_truth_df, 
                                    ax=None,
                                    scatter=False):
    if moving_ground_truth_df is None:
        return
    if not ax:
        ax = figure.add_subplot(arrange_spec)
    if moving_ground_truth_df is not None:
        moving_ground_truth_df["Datetime Normalized"] = pd.to_datetime(moving_ground_truth_df["Time UNIX Norm (s)"],unit='s')
        ground_truth_aligned = (moving_ground_truth_df.set_index("Datetime Normalized")
                        .dropna()
                        .rename(columns={"DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)": "Correction Distance (mm)"})[
                            ["Correction Distance (mm)"]])
    if not scatter:
        ax.plot((static_veh_df['Error (mm)']), label="Static Vehicle (V{})".format(static_veh))
    else:
        ax.scatter(
            static_veh_df.index,
            static_veh_df['Error (mm)'], 
            label="Static V{} against Mover V{}  Interpolated Error".format(static_veh, moving_veh),
            alpha=0.3,
            s=MARKER_SIZE,
            color="C0")
    
    if not scatter:
        ax.plot((moving_veh_df['Error (mm)']), label="Moving Vehicle (V{})".format(moving_veh))
    else:
        ax.scatter(
            moving_veh_df.index,
            moving_veh_df['Error (mm)'], 
            label="Mover V{} against Static V{}  Interpolated Error".format(moving_veh, static_veh),
            alpha=0.3,
            s=MARKER_SIZE,
            color="C1")
    
    ax.set_title("Time Series Real Time Measurement Error (mm)")
    time_stamp_lim = get_time_stamp_lim(pd.concat([static_veh_df, moving_veh_df]), moving_ground_truth_df)
    _time_span = time_stamp_lim[1] - time_stamp_lim[0]
    _xlim = [time_stamp_lim[0] - 0.1 * _time_span, time_stamp_lim[1] + 0.1 * _time_span]
    ax.set_xlim(_xlim)
    ax.set_xlabel("Time")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_ylabel("Error Interpolated (mm)") 
    ax.legend()
    figure.tight_layout(pad=1.0)


def plot_hist_moving_err(   figure,
                            static_veh,
                            moving_veh,
                            real_time_err_static_veh,
                            real_time_err_moving_veh,
                            bin_size_static,
                            bin_size_moving
                            ):
    my_palette = sns.color_palette("muted")
    ax_static = figure.add_subplot(121)
    ax2_static = ax_static.twinx()
    hist_static = sns.histplot(
        data=real_time_err_static_veh.reset_index(),
        bins=bin_size_static,
        alpha =0.6,
        label="Error Counts, V{} against V{}".format(static_veh, moving_veh),
        ax=ax_static,
        color="C0"
    )
    kde_static = sns.kdeplot(
        data=real_time_err_static_veh.reset_index(),
        ax=ax2_static,
        label="Kernel Density Distribution, V{} against V{}".format(static_veh, moving_veh), 
        linewidth=1.5, 
        color="C0")
    zero_static = ax_static.axvline(x=0, color="g", label="Zero Error", linewidth=3, alpha=0.7)
    ax_moving = figure.add_subplot(122)
    ax2_moving = ax_moving.twinx()
    zero_moving = ax_moving.axvline(x=0, color="g", label="Zero Error", linewidth=3, alpha=0.7)
    hist_moving = sns.histplot(
        data=real_time_err_moving_veh.reset_index(),
        bins=bin_size_moving,
        alpha =0.6,
        label="Error Counts, V{} against V{}".format(moving_veh, static_veh),
        ax=ax_moving,
        color="C1"
    )
    kde_moving = sns.kdeplot(
        data=real_time_err_moving_veh.reset_index(),
        ax=ax2_moving, 
        label="Kernel Density Distribution, V{} against V{}".format(moving_veh, static_veh), 
        linewidth=1.5, 
        color="C1")
    
    # Clear the unwanted legend automatically generated by Seaborn
    ax_static.legend().set_title('')
    ax2_static.legend().set_title('')
    ax_moving.legend().set_title('')
    ax2_moving.legend().set_title('')

    ax_static.set_xlabel("Interpolated Measurement Error (mm)")
    ax_static.set_ylabel("Count")
    ax2_static.set_ylabel("Kernel Density Estimation (KDE)")
    ax_static.legend()

    ax_moving.set_xlabel("Interpolated Measurement Error (mm)")
    ax_moving.set_ylabel("Count")
    ax2_moving.set_ylabel("Kernel Density Estimation (KDE)")
    ax_moving.legend() 

def plot_hist(  figure, 
                arrange_spec, 
                veh_df, 
                bin_size, 
                ground_truth_value, 
                master_slave_mapping, 
                disp_range, 
                hist_title):
    veh_df = veh_df.reset_index()
    ax = figure.add_subplot(arrange_spec)
    ax2 = ax.twinx()
    my_palette = sns.color_palette("muted")
    i = 0
    for veh in veh_df["Initiating Vehicle"].unique():
        for master, slaves in master_slave_mapping.items():
            for slave in slaves:
                _data = veh_df.loc[
                    (veh_df["Initiating Master"]==master) & (veh_df["Reporting Slave"]==slave) & 
                    (veh_df["Initiating Vehicle"]==veh), "Correction Distance (mm)"]
                if not _data.empty and _data.var() > 0:
                    sns.histplot(
                        data=_data,
                        bins=bin_size,
                        alpha =0.6,
                        label="V{}: {} against {}".format(veh, master, slave),
                        ax=ax,
                        color="C"+str(i))
                    sns.kdeplot(
                        _data, 
                        ax=ax2, 
                        linewidth=1.5, 
                        color="C"+str(i))
                    i += 1
    
    ax.axvline(x=ground_truth_value, color="g", label="Manually Measured", linewidth=3, alpha=0.7)
    ax.set_title(hist_title)
    ax.set_xlabel("Distance (mm)")
    if not (np.nan in disp_range) and not np.isnan(ground_truth_value):
        ax.set_xlim(min(disp_range[0], ground_truth_value) * 0.98, max(disp_range[1], ground_truth_value) * 1.02)
    ax.set_ylabel("Count")
    ax2.set_ylabel("Kernel Density Estimation (KDE)")
    ax.legend()

def plot_hist_moving_err_hbar(  figure,
                                static_veh,
                                moving_veh,
                                real_time_err_static_veh,
                                real_time_err_moving_veh,
                                bin_size_static,
                                bin_size_moving
                            ):

    axs = figure.subplots(1,2,sharey=True)
    figure.subplots_adjust(wspace=0)
    ax_static, ax_moving = axs[0], axs[1]
    ax2_static, ax2_moving = axs[0].twiny(), axs[1].twiny()

    my_palette = sns.color_palette("muted")
    
    if real_time_err_static_veh is not None:
        zero_static = ax_static.axhline(y=0, color="g", label="Zero Error", linewidth=3, alpha=0.7)
        hist_static = sns.histplot(
            data=real_time_err_static_veh.reset_index(),
            y="Error (mm)",
            bins=bin_size_static,
            alpha =0.6,
            label="Error Counts, V{} against V{}".format(static_veh, moving_veh),
            ax=ax_static,
            color="C0"
        )
        kde_static = sns.kdeplot(
            data=real_time_err_static_veh.reset_index(),
            x="Error (mm)",
            ax=ax2_static,
            label="Kernel Density Distribution, V{} against V{}".format(static_veh, moving_veh), 
            linewidth=1.5,
            vertical=True,
            color="C0")
    
    if real_time_err_moving_veh is not None:
        zero_moving = ax_moving.axhline(y=0, color="g", label="Zero Error", linewidth=3, alpha=0.7)
        hist_moving = sns.histplot(
            data=real_time_err_moving_veh.reset_index(),
            y="Error (mm)",
            bins=bin_size_moving,
            alpha =0.6,
            label="Error Counts, V{} against V{}".format(moving_veh, static_veh),
            ax=ax_moving,
            color="C1"
        )
        kde_moving = sns.kdeplot(
            data=real_time_err_moving_veh.reset_index(),
            x="Error (mm)",
            ax=ax2_moving, 
            label="Kernel Density Distribution, V{} against V{}".format(moving_veh, static_veh), 
            linewidth=1.5,
            vertical=True, 
            color="C1")
    
    ax_static.set_xlim(ax_static.get_xlim()[::-1])
    ax2_static.set_xlim(ax2_static.get_xlim()[::-1])
    ax2_static.set_xlabel("Kernel Density Estimation (KDE)")
    ax2_moving.set_xlabel("Kernel Density Estimation (KDE)")
    
    ax_static.set_xticks(ax_static.get_xticks()[1:])
    ax2_static.set_xticks(ax2_static.get_xticks()[1:])

    axs[0].legend()
    axs[1].legend()

def plot_hist_hbar( figure, 
                    veh1_df, 
                    veh2_df, 
                    veh1_bin_size, 
                    veh2_bin_size, 
                    ground_truth_value, 
                    static_master_slave_mapping, 
                    moving_master_slave_mapping, 
                    static_disp_range, 
                    moving_disp_range, 
                    hist_title):
    veh1_df = veh1_df.reset_index()
    veh2_df = veh2_df.reset_index()

    axs = figure.subplots(1,2,sharey=True)
    figure.subplots_adjust(wspace=0)
    ax_0_2, ax_1_2 = axs[0].twiny(), axs[1].twiny()

    my_palette = sns.color_palette("muted")
    
    i = 0
    for veh in veh1_df["Initiating Vehicle"].unique():
        for master, slaves in static_master_slave_mapping.items():
            for slave in slaves:
                _data = veh1_df.loc[(veh1_df["Initiating Master"]==master) \
                    & (veh1_df["Reporting Slave"]==slave) \
                        & (veh1_df["Initiating Vehicle"]==veh), "Correction Distance (mm)"]
                if not _data.empty and _data.var() > 0:
                    sns.histplot(
                        data=_data,
                        bins=veh1_bin_size,
                        y=_data,
                        alpha =0.6,
                        label="V{}: {} against {}".format(veh, master, slave),
                        ax=axs[0],
                        color="C"+str(i))
                    sns.kdeplot(
                        _data, 
                        ax=ax_0_2, 
                        linewidth=1.5, 
                        vertical=True,
                        color="C"+str(i))
                    i += 1
    j = 0
    for veh in veh2_df["Initiating Vehicle"].unique():
        for master, slaves in moving_master_slave_mapping.items():
            for slave in slaves:
                _data = veh2_df.loc[(veh2_df["Initiating Master"]==master) \
                    & (veh2_df["Reporting Slave"]==slave) \
                        & (veh2_df["Initiating Vehicle"]==veh), "Correction Distance (mm)"]
                if not _data.empty and _data.var() > 0:
                    sns.histplot(
                        data=_data,
                        y=_data,
                        bins=veh2_bin_size,
                        alpha =0.6,
                        label="V{}: {} against {}".format(veh, master, slave),
                        ax=axs[1],
                        color="C"+str(j))
                    sns.kdeplot(
                        _data, 
                        ax=ax_1_2, 
                        linewidth=1.5, 
                        vertical=True,
                        color="C"+str(j))
                    j += 1
    #invert the order of x-axis values
    axs[0].set_xlim(axs[0].get_xlim()[::-1])
    ax_0_2.set_xlim(ax_0_2.get_xlim()[::-1])
    ax_0_2.set_xlabel("Kernel Density Estimation (KDE)")
    ax_1_2.set_xlabel("Kernel Density Estimation (KDE)")
    
    axs[0].set_xticks(axs[0].get_xticks()[1:])
    ax_0_2.set_xticks(ax_0_2.get_xticks()[1:])
    
    axs[0].axhline(y=ground_truth_value, color="g", label="Manually Measured", linewidth=3, alpha=0.7)
    axs[1].axhline(y=ground_truth_value, color="g", label="Manually Measured", linewidth=3, alpha=0.7)
    disp_range = (min(static_disp_range[0], moving_disp_range[0]), max(static_disp_range[1], moving_disp_range[1]))
    if not (np.nan in disp_range) and not np.isnan(ground_truth_value):
        axs[0].set_ylim(min(disp_range[0], ground_truth_value) * 0.98, max(disp_range[1], ground_truth_value) * 1.02)
    axs[0].legend()
    axs[1].legend()


def plot_dist_idx_scatter_error(figure, 
                                static_dist_idx_df,
                                moving_dist_idx_df,
                                test_preset_map):
    static_veh, moving_veh = test_preset_map['STATIC_VEH'], test_preset_map['MOVING_VEH']
    ax = figure.add_subplot(111)
    ax.scatter( static_dist_idx_df.index, 
                static_dist_idx_df['Error (mm)'],
                label="Static V{} against Mover V{} Data Points".format(static_veh, moving_veh),
                alpha=0.3,
                color="C0",
                s=MARKER_SIZE)
    ax.scatter( moving_dist_idx_df.index, 
                moving_dist_idx_df['Error (mm)'],
                label="Moving V{} against Mover V{} Data Points".format(static_veh, moving_veh),
                alpha=0.3,
                color="C1",
                s=MARKER_SIZE)
    ax.set_title("Error v.s. Surveyed Distance")
    ax.set_xlabel("Distance (mm)")
    ax.set_ylabel("Error (mm)")
    ax.legend()
    ax.set_xlim(left=0)
    figure.tight_layout(pad=1.0)



def plot_dist_idx_udpate_rate(  figure,
                                interval_idx_stats_map,
                                static_veh,
                                moving_veh,
                                test_preset_map,
                                dist_bin=200):
    static_df_counts = interval_idx_stats_map[static_veh]['aggregated']
    moving_df_counts = interval_idx_stats_map[moving_veh]['aggregated']
    static_df_counts_main_pair = interval_idx_stats_map[static_veh]['main']
    moving_df_counts_main_pair = interval_idx_stats_map[moving_veh]['main']
    ax = figure.add_subplot(111)
    ax.plot([i.mid for i in 
            (static_df_counts['reporting cnt'] / static_df_counts['duration']).index.array], 
            static_df_counts['reporting cnt'] / static_df_counts['duration'],
            label="Static Vehicle Aggregated All Pairs",color="C0", alpha=0.3, linestyle='--')
    ax.plot([i.mid for i in 
            (moving_df_counts['reporting cnt'] / moving_df_counts['duration']).index.array], 
            moving_df_counts['reporting cnt'] / moving_df_counts['duration'],
            label="Moving Vehicle Aggregated All Pairs",color="C1", alpha=0.3, linestyle='--')
        
    ax.plot([i.mid for i in 
            (static_df_counts_main_pair['reporting cnt'] / static_df_counts_main_pair['duration']).index.array], 
            static_df_counts_main_pair['reporting cnt'] / static_df_counts_main_pair['duration'],
            label="Static Vehicle Main Pair", color="C0")
    ax.plot([i.mid for i in 
            (moving_df_counts_main_pair['reporting cnt'] / moving_df_counts_main_pair['duration']).index.array], 
            moving_df_counts_main_pair['reporting cnt'] / moving_df_counts_main_pair['duration'],
            label="Moving Vehicle Main Pair", color="C1")

    ax.legend()
    ax.set_ylabel("Normalized Update Rate (Hz)")
    ax.set_xlabel("Surveyed Distance (mm)")
    figure.tight_layout(pad=1.0)


def plot_spd_idx_udpate_rate(   figure,
                                spd_interval_idx_stats_map,
                                static_veh,
                                moving_veh):
                                                                                        
    static_veh_rel_spd_aggregated = spd_interval_idx_stats_map[static_veh]['aggregated']['non-abs']
    moving_veh_rel_spd_aggregated = spd_interval_idx_stats_map[moving_veh]['aggregated']['non-abs']
    static_veh_abs_spd_aggregated = spd_interval_idx_stats_map[static_veh]['aggregated']['abs']
    moving_veh_abs_spd_aggregated = spd_interval_idx_stats_map[moving_veh]['aggregated']['abs']
    static_veh_rel_spd_main = spd_interval_idx_stats_map[static_veh]['main']['non-abs']
    moving_veh_rel_spd_main = spd_interval_idx_stats_map[moving_veh]['main']['non-abs']
    static_veh_abs_spd_main = spd_interval_idx_stats_map[static_veh]['main']['abs']
    moving_veh_abs_spd_main = spd_interval_idx_stats_map[moving_veh]['main']['abs']

    ax1 = figure.add_subplot(211)
    ax1.plot([i.mid for i in (static_veh_abs_spd_aggregated['update rate (hz)']).index.array], 
            static_veh_abs_spd_aggregated['update rate (hz)'],
            label="Static Vehicle Aggregated Pairs", marker="o", color="C0")
    ax1.plot([i.mid for i in (moving_veh_abs_spd_aggregated['update rate (hz)']).index.array], 
            moving_veh_abs_spd_aggregated['update rate (hz)'],
            label="Moving Vehicle Aggregated Pairs", marker="o", color="C1")
    ax1.legend()
    ax1.set_ylabel("Update Rate (Hz)")
    ax1.set_xlabel("Instant Absolute Relative Speed (mph)")
    ax1.set_title("Normalized Update Rate v.s. Absolute Speed")
    ax1.set_ylim(bottom=0)

    ax2 = figure.add_subplot(212)
    ax2.plot([i.mid for i in 
            (static_veh_rel_spd_aggregated['update rate (hz)']).index.array], 
            static_veh_rel_spd_aggregated['update rate (hz)'],
            label="Static Vehicle Aggregated Pairs", marker="o", color="C0")
    ax2.plot([i.mid for i in 
            (moving_veh_rel_spd_aggregated['update rate (hz)']).index.array], 
            moving_veh_rel_spd_aggregated['update rate (hz)'],
            label="Moving Vehicle Aggregated Pairs", marker="o", color="C1")
    ax2.legend()
    ax2.set_ylabel("Update Rate (Hz)")
    ax2.set_xlabel("Instant Relative Speed (mph)")
    ax2.set_title("Normalized Update Rate v.s. Relative Speed")
    ax2.set_ylim(bottom=0)

    ax1.plot([i.mid for i in (static_veh_abs_spd_main['update rate (hz)']).index.array], 
        static_veh_abs_spd_main['update rate (hz)'],
        label="Static Vehicle Main Pair", marker="o", color="C0", linestyle='--')
    ax1.plot([i.mid for i in (moving_veh_abs_spd_main['update rate (hz)']).index.array], 
        moving_veh_abs_spd_main['update rate (hz)'],
        label="Moving Vehicle Main Pair", marker="o", color="C1", linestyle='--')
    ax1.legend()
    ax1.set_ylabel("Update Rate (Hz)")
    ax1.set_xlabel("Instant Absolute Relative Speed (mph)")
    ax1.set_ylim(bottom=0)

    ax2.plot([i.mid for i in 
            (static_veh_rel_spd_main['update rate (hz)']).index.array], 
            static_veh_rel_spd_main['update rate (hz)'],
            label="Static Vehicle Main Pair", marker="o", color="C0", linestyle='--')
    ax2.plot([i.mid for i in 
            (moving_veh_rel_spd_main['update rate (hz)']).index.array], 
            moving_veh_rel_spd_main['update rate (hz)'],
            label="Moving Vehicle Main Pair", marker="o", color="C1", linestyle='--')
    ax2.legend()
    ax2.set_ylabel("Update Rate (Hz)")
    ax2.set_xlabel("Instant Relative Speed (mph)")
    ax2.set_ylim(bottom=0)

    figure.tight_layout(pad=1.0)


if __name__ == "__main__":
    import os, re
    import json
    import numpy as np

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import FormatStrFormatter

    from datetime import datetime
    import math
    import pandas as pd
    from itertools import chain

    from utils import post_process_get_moving_test_data_and_timestamp
    from utils import remove_outlier_by_quantile
    from static_data_processing import get_test_files_and_survey
    from plot_utils import *
    from stats_utils import *

    from pandas.core.common import SettingWithCopyWarning
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning) 
    warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)

    from collections import defaultdict

    ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
    CALIBRATED_CAM_TO_V2B = -6400.8
    pd.set_option('display.float_format', lambda x: '%.5f' % x)
    pd.set_option('display.max_columns', None)

    RESAMPLE_RULE = "1S"
    PLOTTING_DPI = 75
    static_main_master = '0C1A'
    static_focusing_slaves = ['1912', '8D38']
    static_master_slave_mapping = { '0C1A': [static_focusing_slaves[0], static_focusing_slaves[1]],
                            '9B0F': [static_focusing_slaves[1], static_focusing_slaves[0]]}
    moving_main_master = '88BA'
    moving_focusing_slaves = ['45BA', '0B8A']
    moving_master_slave_mapping = { '88BA': [moving_focusing_slaves[0], moving_focusing_slaves[1]],
                            '111C': [moving_focusing_slaves[1], moving_focusing_slaves[0]]}
    STATIC_VEH, MOVING_VEH = 1, 2
    VEH_NAME_MAP = {1: "static", 2: "moving"}
    test_preset_map = defaultdict(dict)
    test_preset_map['PLOTTING_DPI'] = PLOTTING_DPI
    test_preset_map['STATIC_VEH'] = STATIC_VEH
    test_preset_map['MOVING_VEH'] = MOVING_VEH
    test_preset_map[STATIC_VEH]['master_slave_mapping'] = static_master_slave_mapping
    test_preset_map[MOVING_VEH]['master_slave_mapping'] = moving_master_slave_mapping
    test_preset_map[STATIC_VEH]['main_master'] = static_main_master
    test_preset_map[MOVING_VEH]['main_master'] = moving_main_master
    test_preset_map['dist_interval_size'] = 200
    #############################################
    # if skip plotting any tests, list them here
    skiptests = []
    #############################################
    all_test_files, ground_truth_list = post_process_get_moving_test_data_and_timestamp(ROOT_DIR, 
                                                                                        "Moving Test 1 (V2V)", 
                                                                                        "V2", 
                                                                                        CALIBRATED_CAM_TO_V2B,
                                                                                        skiptests=skiptests)
    assert(len(all_test_files) == len(ground_truth_list))
    all_test_names_dup = [os.path.basename(os.path.dirname(f)) for f in all_test_files]
    # Remove Duplicates of Test Names
    all_test_names = []
    _ = [all_test_names.append(x) for x in all_test_names_dup if x not in all_test_names]
    test_raw_name_file_map = {}
    for i in range(len(all_test_names)):
        test_raw_name_file_map[all_test_names[i]] = {}
        a_side_file, b_side_file = all_test_files[2*i], all_test_files[2*i+1]
        test_raw_name_file_map[all_test_names[i]]["A"] = a_side_file
        test_raw_name_file_map[all_test_names[i]]["B"] = b_side_file
        test_raw_name_file_map[all_test_names[i]]["ground_truth"] = ground_truth_list[2*i]
    moving_tests = {}

    test_1_west = all_test_names[0]
    moving_tests[test_1_west] = parse_single_test_data(test_raw_name_file_map[test_1_west]["B"], "Moving Test", test_preset_map, 
                                                    test_raw_name_file_map[test_1_west]["ground_truth"])
    plot_single_test_data(test_1_west, moving_tests, 'Moving Test', test_preset_map)