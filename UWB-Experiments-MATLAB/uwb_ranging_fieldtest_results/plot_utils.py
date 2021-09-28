import os, re
import json
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter
import seaborn as sns

from datetime import datetime
import math
import pandas as pd
from itertools import chain

from utils import post_process_get_moving_test_data_and_timestamp
from utils import remove_outlier_by_quantile

from pandas.core.common import SettingWithCopyWarning
import warnings
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
CALIBRATED_CAM_TO_V2B = -6400.8
pd.set_option('display.float_format', lambda x: '%.5f' % x)

RESAMPLE_RULE = "1S"
MAX_UPD_RATE = 40
NUL_UPD_RATE = 0

static_main_master = '0C1A'
static_focusing_slaves = ['1912', '8D38']
static_master_slave_mapping = { '0C1A': [static_focusing_slaves[0], static_focusing_slaves[1]],
                        '9B0F': [static_focusing_slaves[1], static_focusing_slaves[0]]}
moving_main_master = '88BA'
moving_focusing_slaves = ['45BA', '0B8A']
moving_master_slave_mapping = { '88BA': [moving_focusing_slaves[0], moving_focusing_slaves[1]],
                        '111C': [moving_focusing_slaves[1], moving_focusing_slaves[0]]}

def update_rate_aggregate_reporting_pairs(df, masters, slaves):
    slices_designated_slave = []
    for master_id in df['Initiating Master'].unique():
        if master_id in masters:
            for slave_id in df['Reporting Slave'].unique():
                if slave_id in slaves:
                    sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)]
                    sliced_by_designated_slave["Instant Update Rate (Hz)"] = (1 / sliced_by_designated_slave['Timestamp Norm (s)'].diff())
                    slices_designated_slave.append(sliced_by_designated_slave)
    
    if slices_designated_slave:
        concat_df = pd.concat(slices_designated_slave)
        concat_df.sort_values(['Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True], inplace=True)
        concat_df["Aggregated Update Rate (Hz)"] = (1 / concat_df['Timestamp Norm (s)'].diff())
        ret = concat_df
    else:
        ret = df
    return ret


def plot_time_series_ranging(fdir, moving_ground_truth_df, static_veh, is_static_plot=False, moving_veh=2, resample_rule=RESAMPLE_RULE):
    base_folder = os.path.dirname(fdir)
    df = pd.read_csv(fdir, parse_dates=["Datetime Normalized"], index_col=["Datetime Normalized"])
    df["Aggregated Update Rate (Hz)"] = np.nan
    if df.empty:
        return

    if moving_ground_truth_df is None:
        time_range = df.index.max() - df.index.min()
        time_stamp_lim = [
            df.index.min() - time_range * 0.1,
            df.index.max() + time_range * 0.1
            ]
    else:
        min_time = min(df.index.min(), pd.to_datetime(moving_ground_truth_df["Time UNIX Norm (s)"],unit='s').min())
        max_time = max(df.index.max(), pd.to_datetime(moving_ground_truth_df["Time UNIX Norm (s)"],unit='s').max())
        time_range = max_time - min_time
        time_stamp_lim = [
            min_time - time_range * 0.1,
            max_time + time_range * 0.1
            ]

    df_static_veh_all_pairs = remove_outlier_by_quantile(df[df['Initiating Vehicle'] == static_veh], "Correction Distance (mm)") 
    df_moving_veh_all_pairs = remove_outlier_by_quantile(df[df['Initiating Vehicle'] == moving_veh], "Correction Distance (mm)")
    
    df_static_veh_hz_cleaned_all_pairs = update_rate_aggregate_reporting_pairs( df_static_veh_all_pairs, 
                                                                                static_master_slave_mapping.keys(), 
                                                                                static_focusing_slaves)
    df_moving_veh_hz_cleaned_all_pairs = update_rate_aggregate_reporting_pairs( df_moving_veh_all_pairs, 
                                                                                moving_master_slave_mapping.keys(), 
                                                                                moving_focusing_slaves)
    df_static_veh_hz_cleaned_all_pairs_outlier_removed = remove_outlier_by_quantile(df_static_veh_hz_cleaned_all_pairs, "Aggregated Update Rate (Hz)")
    df_moving_veh_hz_cleaned_all_pairs_outlier_removed = remove_outlier_by_quantile(df_moving_veh_hz_cleaned_all_pairs, "Aggregated Update Rate (Hz)")
    
    df_static_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_static_veh_hz_cleaned_all_pairs_outlier_removed.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_hz_cleaned_all_pairs_outlier_removed.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)

    df_static_veh_all_pairs_resampled = df_static_veh_all_pairs.resample(rule=resample_rule, origin=time_stamp_lim[0]).mean()
    df_moving_veh_all_pairs_resampled = df_moving_veh_all_pairs.resample(rule=resample_rule, origin=time_stamp_lim[0]).mean()    
    df_static_veh_hz_cleaned_all_pairs_outlier_removed_resampled = df_static_veh_hz_cleaned_all_pairs_outlier_removed.resample(rule=resample_rule, origin=time_stamp_lim[0]).mean()
    df_moving_veh_hz_cleaned_all_pairs_outlier_removed_resampled = df_moving_veh_hz_cleaned_all_pairs_outlier_removed.resample(rule=resample_rule, origin=time_stamp_lim[0]).mean()

    # Plotting
    figure = plt.figure(figsize=(16, 9), dpi=150)
    raw_name = os.path.basename(os.path.dirname(fdir))
    print("plotting: " + raw_name)
    if is_static_plot: # Static Experiment
        
        static_surveyed_dist = df_static_veh_all_pairs_resampled["Surveyed Distance (mm)"].get(0, float('nan'))
        if not np.isnan(static_surveyed_dist):
            titlename = "Static Test - " + raw_name.split("-static-v2-")[-1] + " - " + str(int(static_surveyed_dist)) + "mm"
        else:
            titlename = "Static Test - " + raw_name.split("-static-v2-")[-1] + " - " "Not Measured"
        figure.suptitle(titlename, fontsize='x-large', fontweight='bold')

        plot_time_series_dist(  figure=figure,
                                arrange_spec=221,
                                static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed_resampled,
                                moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed_resampled,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                surveyed_static_ground_truth_value=static_surveyed_dist,
                                moving_ground_truth_df=None,
                                time_stamp_lim=time_stamp_lim)


        plot_upd_rate(  figure=figure,
                        arrange_spec=223,
                        static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed_resampled, 
                        moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed_resampled, 
                        static_veh=static_veh, 
                        moving_veh=moving_veh, 
                        time_stamp_lim=time_stamp_lim)
        
        _raw_data_static_whole = df[df['Initiating Vehicle'] == static_veh]
        _raw_data_moving_whole = df[df['Initiating Vehicle'] == moving_veh]
        _raw_data_static = _raw_data_static_whole["Correction Distance (mm)"]
        _raw_data_moving = _raw_data_moving_whole["Correction Distance (mm)"]
        static_hist_disp_range = (_raw_data_static.quantile(0.05), _raw_data_static.quantile(0.95))
        static_hist_disp_range = None if np.nan in static_hist_disp_range else static_hist_disp_range
        binwidth = 20
        static_bins = np.arange(min(_raw_data_static), max(_raw_data_static) + binwidth, binwidth) if not _raw_data_static.empty else None
        moving_hist_disp_range = (_raw_data_moving.quantile(0.05), _raw_data_moving.quantile(0.95))
        moving_hist_disp_range = None if np.nan in moving_hist_disp_range else moving_hist_disp_range
        moving_bins = np.arange(min(_raw_data_moving), max(_raw_data_moving) + binwidth, binwidth) if not _raw_data_moving.empty else None

        plot_hist(  figure=figure,  
                    arrange_spec=222, 
                    veh_df=_raw_data_static_whole,
                    bin_size=static_bins, 
                    ground_truth_value=static_surveyed_dist,
                    master_slave_mapping=static_master_slave_mapping,
                    disp_range=static_hist_disp_range,
                    hist_title="Hist - Vehicle {} (Static) against Vehicle {} (Mover)".format(static_veh, moving_veh))
        
        plot_hist(  figure=figure,  
                    arrange_spec=224, 
                    veh_df=_raw_data_moving_whole,
                    bin_size=moving_bins, 
                    ground_truth_value=static_surveyed_dist,
                    master_slave_mapping=moving_master_slave_mapping,
                    disp_range=moving_hist_disp_range, 
                    hist_title="Hist - Vehicle {} (Mover) against Vehicle {} (Static)".format(moving_veh, static_veh))
        
        # Saving to directory
        _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + ".png")
        # plt.savefig(_fig_dir)
        plt.show()
    
    else: # Moving Experiment
        if moving_ground_truth_df is not None:
            moving_ground_truth_df.rename(columns={"DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)":"Surveyed Distance (mm)"}, inplace=True)
            moving_ground_truth_df.set_index("Datetime Normalized", inplace=True)
            moving_ground_truth_df = moving_ground_truth_df[~moving_ground_truth_df.index.isnull()] # Remove NaT indices for ground truths
            
            _temp_df_survey_interpolate = pd.DataFrame(index=pd.concat([df, moving_ground_truth_df]).index.drop_duplicates()).sort_index()
            _temp_df_survey_interpolate["Surveyed Distance (mm)"] = moving_ground_truth_df["Surveyed Distance (mm)"]
            _temp_df_survey_interpolate = _temp_df_survey_interpolate.interpolate()
            df["Surveyed Distance (mm)"] = _temp_df_survey_interpolate["Surveyed Distance (mm)"]
        if "moving" in raw_name.split("-v2-")[0]:
            titlename = "Moving Test - " + raw_name.split("-v2-")[-1]
            figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
        elif "moving" in raw_name.split("-v2-")[0]:
            titlename = "Virtual Moving Test - " + raw_name.split("-v2-")[-1]
            figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
        
        plot_time_series_dist(  figure=figure,
                                arrange_spec=311,
                                static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed,
                                moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                surveyed_static_ground_truth_value=None,
                                moving_ground_truth_df=moving_ground_truth_df,
                                time_stamp_lim=time_stamp_lim)

        plot_upd_rate(  figure=figure,
                        arrange_spec=312,
                        static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed,
                        moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed,
                        static_veh=static_veh,
                        moving_veh=moving_veh,
                        time_stamp_lim=time_stamp_lim)

        # Instant Speed UWB Strict
        # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
        plot_time_series_speed( figure=figure, 
                                arrange_spec=313, 
                                static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed, 
                                moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed,
                                static_veh=static_veh,
                                moving_veh=moving_veh, 
                                moving_ground_truth_df=moving_ground_truth_df,
                                time_stamp_lim=time_stamp_lim)

        # Saving to directory
        _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + ".png")
        # plt.savefig(_fig_dir)
        plt.show()

        figure_resample = plt.figure(figsize=(16, 9), dpi=150)
        titlename = os.path.basename(os.path.dirname(fdir)) + "-Resampled"
        figure_resample.suptitle(titlename, fontsize='x-large', fontweight='bold')
        
        plot_time_series_dist(  figure=figure_resample,
                                arrange_spec=311,
                                static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed_resampled,
                                moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed_resampled,
                                static_veh=static_veh,
                                moving_veh=moving_veh,
                                surveyed_static_ground_truth_value=None,
                                moving_ground_truth_df=moving_ground_truth_df,
                                time_stamp_lim=time_stamp_lim)

        plot_upd_rate(  figure=figure_resample,
                        arrange_spec=312,
                        static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed_resampled,
                        moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed_resampled,
                        static_veh=static_veh,
                        moving_veh=moving_veh,
                        time_stamp_lim=time_stamp_lim)
        
        # Instant Speed UWB Strict
        # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
        plot_time_series_speed( figure=figure_resample, 
                                arrange_spec=313, 
                                static_veh_df=df_static_veh_hz_cleaned_all_pairs_outlier_removed, 
                                moving_veh_df=df_moving_veh_hz_cleaned_all_pairs_outlier_removed,
                                static_veh=static_veh,
                                moving_veh=moving_veh, 
                                moving_ground_truth_df=moving_ground_truth_df,
                                time_stamp_lim=time_stamp_lim, 
                                resample=True)

        # Saving to directory
        _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + "_resampled.png")
        # plt.savefig(_fig_dir)
        plt.show()

def plot_time_series_dist(figure, arrange_spec, static_veh_df, moving_veh_df, static_veh, moving_veh, surveyed_static_ground_truth_value, moving_ground_truth_df, time_stamp_lim):
    ax = figure.add_subplot(arrange_spec)
    ax.plot( static_veh_df.index, 
             static_veh_df["Correction Distance (mm)"], 
             label="Static V{} against Mover V{}".format(static_veh, moving_veh),
             alpha=0.9,
             color="C0", 
             linestyle="-")
    ax.plot( moving_veh_df.index, 
             moving_veh_df["Correction Distance (mm)"], 
             label="Mover V{} against Static V{}".format(moving_veh, static_veh),
             alpha=0.9,
             color="C1",
             linestyle="-")
    if surveyed_static_ground_truth_value:
        ax.axhline(y=surveyed_static_ground_truth_value, color="g", label="Manually Measured", alpha=0.9)
    else:
        if moving_ground_truth_df is not None:
            ax.plot(pd.to_datetime(moving_ground_truth_df["Time UNIX Norm (s)"],unit='s'), 
                    moving_ground_truth_df["Surveyed Distance (mm)"], 
                    label="Timestamped Location (Video)", 
                    marker='*',
                    markerfacecolor = 'r',
                    alpha=0.2,
                    linewidth=5, 
                    color="g")
    ax.set_title("Time Series Distance (mm)")
    ax.set_xlim(time_stamp_lim)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_ylabel("Distance (mm)")
    
    ax.legend()


def plot_upd_rate(figure, arrange_spec, static_veh_df, moving_veh_df, static_veh, moving_veh, time_stamp_lim):
    ax = figure.add_subplot(arrange_spec)
    ax.plot( static_veh_df.index, 
             static_veh_df["Aggregated Update Rate (Hz)"], 
             label="Static V{} against Mover V{}".format(static_veh, moving_veh),
             alpha=0.7,
             color='C0')
    ax.plot( moving_veh_df.index, 
             moving_veh_df["Aggregated Update Rate (Hz)"], 
             label="Mover V{} against Static V{}".format(moving_veh, static_veh),
             alpha=0.7,
             color='C1')
    # ax.axhline(y=MAX_UPD_RATE, color='r', linestyle='dashed', label="Max Update Rate (All Devices Connected)", alpha=0.9)
    # ax.axhline(y=NUL_UPD_RATE, color='r', linestyle='dashed', label="Min Update Rate (No Devices Connected)", alpha=0.9)
    ax.set_title("Aggregated Update Rate (Hz)")
    ax.set_xlabel("Time")
    ax.set_xlim(time_stamp_lim)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_ylabel("Aggregated UWB Reporting Frequency (Hz)")

    # Span for missing values
    reindexed_static = static_veh_df.reset_index()
    reindexed_moving = moving_veh_df.reset_index()
    static_nan_slices = get_nan_slices_indices(reindexed_static, time_stamp_lim=time_stamp_lim, veh=static_veh)
    moving_nan_slices = get_nan_slices_indices(reindexed_moving, time_stamp_lim=time_stamp_lim, veh=moving_veh)
    for i in range(len(static_nan_slices)):
        slice = static_nan_slices[i]
        if len(slice) < 2:
            continue
        [slice_lo, slice_hi] = slice
        ax.axvspan( slice_lo, slice_hi,
                    facecolor='C0',
                    alpha=0.3,
                    label="_" * i + "V{} Signal Lost Period".format(static_veh))

    for i in range(len(moving_nan_slices)):
        slice = moving_nan_slices[i]
        if len(slice) < 2:
            continue
        [slice_lo, slice_hi] = slice
        ax.axvspan( slice_lo, slice_hi,
                    facecolor='C1',
                    alpha=0.3,
                    label="_" * i + "V{} Signal Lost Period".format(moving_veh))
    ax.legend()


def plot_hist(figure, arrange_spec, veh_df, bin_size, ground_truth_value, master_slave_mapping, disp_range, hist_title):
    veh_df = veh_df.reset_index()
    ax = figure.add_subplot(arrange_spec)
    ax2 = ax.twinx()
    my_palette = sns.color_palette("muted")
    i = 0
    for veh in veh_df["Initiating Vehicle"].unique():
        for master, slaves in master_slave_mapping.items():
            for slave in slaves:
                _data = veh_df.loc[(veh_df["Initiating Master"]==master) & (veh_df["Reporting Slave"]==slave) & (veh_df["Initiating Vehicle"]==veh), "Correction Distance (mm)"]
                if not _data.empty and _data.var() > 0:
                    sns.histplot(
                        _data,
                        bins=bin_size,
                        alpha =0.6,
                        label="veh{}: {} against {}".format(veh, master, slave),
                        ax=ax,
                        color="C"+str(i))
                    sns.kdeplot(_data, ax=ax2, linewidth=1.5, color="C"+str(i))
                    i += 1
    
    ax.axvline(x=ground_truth_value, color="g", label="Manually Measured", linewidth=3, alpha=0.7)
    ax.set_title(hist_title)
    ax.set_xlabel("Distance (mm)")
    if not (np.nan in disp_range) and not np.isnan(ground_truth_value):
        ax.set_xlim(min(disp_range[0], ground_truth_value) * 0.98, max(disp_range[1], ground_truth_value) * 1.02)
    ax.set_ylabel("Count")
    ax2.set_ylabel("Gaussian Density")
    ax.legend()


def get_nan_slices_indices(df, time_stamp_lim, veh):
    slices = []
    _flag = False
    for i in range(len(df['Aggregated Update Rate (Hz)'])):
        if not np.isnan(df.iloc[i]['Aggregated Update Rate (Hz)']):
            if _flag == True:
                if slices:
                    slices[-1].append(df.iloc[i]["Datetime Normalized"])
                    _flag = not _flag
        else:
            if _flag == False:
                if 0 < i-1 < len(df['Aggregated Update Rate (Hz)']) - 1:
                    slices.append([df.iloc[i-1]["Datetime Normalized"]])
                    _flag = not _flag
                if 0 == i:
                    slices.append([df.iloc[i]["Datetime Normalized"]])
                    _flag = not _flag
                if len(df['Aggregated Update Rate (Hz)']) - 1 == i:
                    if slices:
                        slices[-1].append(df.iloc[i]["Datetime Normalized"])
    if slices:
        _nan_start, _nan_stop = slices[0][0], slices[-1][-1]
        if df[(df["Datetime Normalized"] < _nan_start) & (df["Datetime Normalized"] > df[df['Initiating Vehicle']==veh]["Datetime Normalized"].min())]['Aggregated Update Rate (Hz)'].size <= 1:
            slices.insert(0, [time_stamp_lim[0], _nan_start])
        if df[(df["Datetime Normalized"] > _nan_stop) & (df["Datetime Normalized"] < df[df['Initiating Vehicle']==veh]["Datetime Normalized"].max())]['Aggregated Update Rate (Hz)'].size <= 1:
            slices.append([_nan_stop, time_stamp_lim[1]])
    return slices


def plot_time_series_speed(figure, arrange_spec, static_veh_df, moving_veh_df, static_veh, moving_veh, moving_ground_truth_df, time_stamp_lim, resample=False):
    ax = figure.add_subplot(arrange_spec)
    # Static
    plot_speed_by_observing_vehicle(ax=ax, veh_df=static_veh_df, veh=static_veh, resample=resample)
    # Moving
    plot_speed_by_observing_vehicle(ax=ax, veh_df=moving_veh_df, veh=moving_veh, resample=resample)
    # Ground
    if moving_ground_truth_df is not None:
        # Calculate Ground Truth Instant Speed
        dist_diff = moving_ground_truth_df["Camera Dist to Static Veh (CPLR, mm)"].diff().fillna(0.).copy()
        time_diff = moving_ground_truth_df["Time UNIX Norm (s)"].diff().fillna(0.).copy()
        instant_spd = (dist_diff / time_diff) * 0.00223694
        moving_ground_truth_df["Instant Speed by Marker (mph)"] = instant_spd
        ax.plot(pd.to_datetime(moving_ground_truth_df["Time UNIX Norm (s)"],unit='s'), 
                 moving_ground_truth_df["Instant Speed by Marker (mph)"], 
                 label="Ground Measured Speed (mph)", 
                 marker='*',
                 markerfacecolor = 'r',
                 alpha=0.2,
                 linewidth=3)
    ax.axhline(y=0, color='r', linestyle='dashed', label="Zero Speed")
    ax.set_title("Measured Speed - Strict Pair (mph)")
    ax.set_xlabel("Time")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_xlim(time_stamp_lim)
    ax.set_ylabel("Speed (mph)")
    ax.legend()


def plot_speed_by_observing_vehicle(ax, veh_df, veh, resample, resample_rule=RESAMPLE_RULE, linestyle="-"):
    slices_uwb_spd_strict_pair = []
    for master_id in veh_df['Initiating Master'].unique():
        for slave_id in veh_df['Reporting Slave'].unique():
            sliced_by_designated_slave = veh_df[(veh_df['Reporting Slave'] == slave_id) & (veh_df['Initiating Master'] == master_id)].copy()
            _dist_diff = veh_df["Correction Distance (mm)"].diff().fillna(0.)
            _time_diff = veh_df["Timestamp Norm (s)"].diff().fillna(0.)
            spd_mph = (_dist_diff / _time_diff) * 0.00223694
            spd_mph = spd_mph.to_frame('UWB Measured Speed - Strict Pair (mph)')
            sliced_by_designated_slave = pd.concat([sliced_by_designated_slave, spd_mph])
            slices_uwb_spd_strict_pair.append(sliced_by_designated_slave)
    added_spd_uwb_strict_pair = pd.DataFrame()
    for _df in slices_uwb_spd_strict_pair:
        added_spd_uwb_strict_pair = pd.concat([added_spd_uwb_strict_pair, _df])
        added_spd_uwb_strict_pair.sort_values(['Initiating Vehicle', 'Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True, True])
    added_spd_uwb_strict_pair.sort_index(inplace=True)
    if resample:
        added_spd_uwb_strict_pair = added_spd_uwb_strict_pair.resample(rule=resample_rule).mean()
    ax.plot( added_spd_uwb_strict_pair.index, 
             added_spd_uwb_strict_pair["UWB Measured Speed - Strict Pair (mph)"], 
             label="UWB Measured Relative Speed by {}".format(veh),
             alpha=0.6,
             linestyle=linestyle)



if __name__ == "__main__":
    from static_data_processing import get_test_files_and_survey
    test_file_list, ground_truth_list = post_process_get_moving_test_data_and_timestamp(ROOT_DIR, "Moving Test 1 (V2V)", "V2", CALIBRATED_CAM_TO_V2B)
    assert(len(test_file_list) == len(ground_truth_list))
    for i in range(len(test_file_list)):
        test_file, ground_truth = test_file_list[i], ground_truth_list[i]
        if "data-A-user-processed_log" in test_file and os.path.basename(test_file).startswith("2021"):
            continue
        _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
        _integ_csv_base = "Integrated_ABAB_COMBO-" + _test_csv_base.split("PostProcessed_")[1].split("-data-")[0] + ".csv"
        _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)
        df = pd.read_csv(_integ_csv_dir)
        plot_time_series_ranging(_integ_csv_dir, ground_truth, static_veh=1, is_static_plot=False, moving_veh=2, resample_rule=RESAMPLE_RULE)
