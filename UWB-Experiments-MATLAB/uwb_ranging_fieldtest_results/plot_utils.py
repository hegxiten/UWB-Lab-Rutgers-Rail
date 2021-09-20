import os, re
import json
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter

from datetime import datetime
import math
import pandas as pd

from utils import post_process_get_moving_test_data_and_timestamp
from utils import remove_outlier_by_quantile

from pandas.core.common import SettingWithCopyWarning
import warnings
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
CALIBRATED_CAM_TO_V2B = -6400.8
pd.set_option('display.float_format', lambda x: '%.5f' % x)


def plot_time_series_ranging(fdir, ground_truth_df, static_veh, is_static_plot=False, moving_veh=2):
    base_folder = os.path.dirname(fdir)
    df = pd.read_csv(fdir, parse_dates=["Datetime Normalized"], index_col=["Datetime Normalized"])
    if df.empty:
        return

    if ground_truth_df is None:
        time_range = df.index.max() - df.index.min()
        time_stamp_lim = [
            df.index.min() - time_range * 0.1,
            df.index.max() + time_range * 0.1
            ]
    else:
        min_time = min(df.index.min(), pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s').min())
        max_time = max(df.index.max(), pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s').max())
        time_range = max_time - min_time
        time_stamp_lim = [
            min_time - time_range * 0.1,
            max_time + time_range * 0.1
            ]

    df_static_veh = remove_outlier_by_quantile(df[df['Initiating Vehicle'] == static_veh], "Correction Distance (mm)") 
    df_moving_veh = remove_outlier_by_quantile(df[df['Initiating Vehicle'] == moving_veh], "Correction Distance (mm)")
    df_static_veh_hz_cleaned = remove_outlier_by_quantile(df_static_veh[df_static_veh['Initiating Vehicle'] == static_veh], "Instant Update Rate (Hz)")
    df_moving_veh_hz_cleaned = remove_outlier_by_quantile(df_moving_veh[df_moving_veh['Initiating Vehicle'] == moving_veh], "Instant Update Rate (Hz)")
    df_static_veh.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_static_veh_hz_cleaned.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_hz_cleaned.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)

    df_static_veh = df_static_veh.resample(rule="1S").mean()
    df_moving_veh = df_moving_veh.resample(rule="1S").mean()    
        
    df_static_veh_hz_cleaned = df_static_veh_hz_cleaned.resample(rule="1S").mean()
    df_moving_veh_hz_cleaned = df_moving_veh_hz_cleaned.resample(rule="1S").mean()

    # Plotting
    figure = plt.figure(figsize=(16, 9), dpi=150)
    titlename = os.path.basename(os.path.dirname(fdir))
    figure.suptitle(titlename)
    print("plotting: " + titlename)
    if is_static_plot: # Static Experiment
        
        surveyed_dist = df_static_veh["Surveyed Distance (mm)"].get(0, float('nan'))
        ax1 = figure.add_subplot(2,2,1)
        ax1.plot(df_static_veh.index, df_static_veh["Correction Distance (mm)"], label="V{} against V{}".format(static_veh, moving_veh))
        ax1.plot(df_moving_veh.index, df_moving_veh["Correction Distance (mm)"], label="V{} against V{}".format(moving_veh, static_veh))
        ax1.plot(df_moving_veh.index, [surveyed_dist] * df_moving_veh["Timestamp Norm (s)"].shape[0], label="Manually Measured")
        ax1.set_title("Time Series Distance (mm)")
        ax1.set_xlabel("Time")
        ax1.set_xlim(time_stamp_lim)
        ax1.set_ylabel("Distance (mm)")
        ax1.legend()

        ax2 = figure.add_subplot(2,2,3)
        ax2.plot(df_static_veh_hz_cleaned.index, df_static_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{} against V{}".format(static_veh, moving_veh))
        ax2.plot(df_moving_veh_hz_cleaned.index, df_moving_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{} against V{}".format(moving_veh, static_veh))
        ax2.set_title("Time Series Update Rate (Hz)")
        ax2.set_xlabel("Time")
        ax2.set_xlim(time_stamp_lim)
        ax2.set_ylabel("UWB Reporting Frequency (Hz)")
        ax2.legend()

        _data_static = df[df['Initiating Vehicle'] == static_veh]["Correction Distance (mm)"]
        _data_moving = df[df['Initiating Vehicle'] == moving_veh]["Correction Distance (mm)"]
        static_hist_disp_range = (_data_static.quantile(0.05), _data_static.quantile(0.95))
        static_hist_disp_range = None if np.nan in static_hist_disp_range else static_hist_disp_range
        binwidth = 20
        static_bins = np.arange(min(_data_static), max(_data_static) + binwidth, binwidth) if not _data_static.empty else None
        moving_hist_disp_range = (_data_moving.quantile(0.05), _data_moving.quantile(0.95))
        moving_hist_disp_range = None if np.nan in moving_hist_disp_range else moving_hist_disp_range
        moving_bins = np.arange(min(_data_moving), max(_data_moving) + binwidth, binwidth) if not _data_moving.empty else None

        ax3 = figure.add_subplot(2,2,2)
        ax3.hist(_data_static, bins=static_bins)
        ax3.axvline(x=surveyed_dist, color='r', linestyle='dashed', linewidth=2, label="Manually Measured")
        ax3.set_title("Hist - Vehicle {} (Static) against Vehicle {}".format(static_veh, moving_veh))
        ax3.set_xlabel("Distance (mm)")
        if not (np.nan in static_hist_disp_range) and not np.isnan(surveyed_dist):
            ax3.set_xlim(min(static_hist_disp_range[0], surveyed_dist) * 0.98, max(static_hist_disp_range[1], surveyed_dist) * 1.02)
        ax3.set_ylabel("Counts")
        ax3.legend()
        
        ax4 = figure.add_subplot(2,2,4)
        ax4.hist(_data_moving, bins=moving_bins)
        ax4.axvline(x=surveyed_dist, color='r', linestyle='dashed', linewidth=2, label="Manually Measured")
        ax4.set_title("Hist - Vehicle {} (Mover) against Vehicle {}".format(moving_veh, static_veh))
        ax4.set_xlabel("Distance (mm)")
        if not (np.nan in moving_hist_disp_range) and not np.isnan(surveyed_dist):
            ax4.set_xlim(min(moving_hist_disp_range[0], surveyed_dist) * 0.98, max(moving_hist_disp_range[1], surveyed_dist) * 1.02)
        ax4.set_ylabel("Counts")
        ax4.legend()
        
        # Saving to directory
        _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + ".png")
        # plt.savefig(_fig_dir)
        plt.show()
    
    else: # Moving Experiment
        if ground_truth_df is not None:
            ground_truth_df.rename(columns={"DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)":"Surveyed Distance (mm)"}, inplace=True)
            ground_truth_df.set_index("Datetime Normalized", inplace=True)
            ground_truth_df = ground_truth_df[~ground_truth_df.index.isnull()] # Remove NaT indices for ground truths
            
            _temp_df_survey_interpolate = pd.DataFrame(index=pd.concat([df, ground_truth_df]).index.drop_duplicates()).sort_index()
            _temp_df_survey_interpolate["Surveyed Distance (mm)"] = ground_truth_df["Surveyed Distance (mm)"]
            _temp_df_survey_interpolate = _temp_df_survey_interpolate.interpolate()
            df["Surveyed Distance (mm)"] = _temp_df_survey_interpolate["Surveyed Distance (mm)"]

        ax1 = figure.add_subplot(3,1,1)
        ax1.plot(df_static_veh.index, df_static_veh["Correction Distance (mm)"], label="V{} against V{}".format(static_veh, moving_veh))
        ax1.plot(df_moving_veh.index, df_moving_veh["Correction Distance (mm)"], label="V{} against V{}".format(moving_veh, static_veh))
        if ground_truth_df is not None:
            ax1.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["Surveyed Distance (mm)"], label="Timestamped Location (Video)",  marker='*',markerfacecolor = 'r')
        ax1.set_title("Time Series Distance (mm)")
        ax1.set_xlim(time_stamp_lim)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax1.set_ylabel("Distance (mm)")
        ax1.legend()

        ax2 = figure.add_subplot(3,1,2)
        ax2.plot(df_static_veh.index, df_static_veh["Instant Update Rate (Hz)"], label="V{} against V{}".format(static_veh, moving_veh))
        ax2.plot(df_moving_veh.index, df_moving_veh["Instant Update Rate (Hz)"], label="V{} against V{}".format(moving_veh, static_veh))
        ax2.set_title("Time Series Update Rate (Hz)")
        ax2.set_xlim(time_stamp_lim)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax2.set_ylabel("UWB Reporting Frequency (Hz)")
        ax2.legend()
        
        # Instant Speed UWB Strict
        # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
        ax3 = figure.add_subplot(3,1,3)
        slices_uwb_spd_strict_pair = []
        for master_id in df['Initiating Master'].unique():
            for slave_id in df['Reporting Slave'].unique():
                sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)].copy()
                _dist_diff = df["Correction Distance (mm)"].diff().fillna(0.)
                _time_diff = df["Timestamp Norm (s)"].diff().fillna(0.)
                spd_mph = (_dist_diff / _time_diff) * 0.00223694
                spd_mph = spd_mph.to_frame('UWB Measured Speed - Strict Pair (mph)')
                sliced_by_designated_slave = pd.concat([sliced_by_designated_slave, spd_mph])
                slices_uwb_spd_strict_pair.append(sliced_by_designated_slave)
        added_spd_uwb_strict_pair = pd.DataFrame()
        for _df in slices_uwb_spd_strict_pair:
            added_spd_uwb_strict_pair = pd.concat([added_spd_uwb_strict_pair, _df])
            added_spd_uwb_strict_pair.sort_values(['Initiating Vehicle', 'Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True, True])
        added_spd_uwb_strict_pair.sort_index(inplace=True)
        if not added_spd_uwb_strict_pair.empty:
            _ = added_spd_uwb_strict_pair.resample(rule="1S").mean()
            ax3.plot(added_spd_uwb_strict_pair.index, added_spd_uwb_strict_pair["UWB Measured Speed - Strict Pair (mph)"], label="UWB Measured Speed".format(moving_veh))
        if ground_truth_df is not None:
            # Calculate Ground Truth Instant Speed
            dist_diff = ground_truth_df["Camera Dist to Static Veh (CPLR, mm)"].diff().fillna(0.).copy()
            time_diff = ground_truth_df["Time UNIX Norm (s)"].diff().fillna(0.).copy()
            instant_spd = (dist_diff / time_diff) * 0.00223694
            ground_truth_df["Instant Speed by Marker (mph)"] = instant_spd
            ax3.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["Instant Speed by Marker (mph)"], label="Ground Measured Speed (mph)",  marker='*',markerfacecolor = 'r')
        ax3.axhline(y=0, color='r', linestyle='dashed', label="Zero Speed")
        ax3.set_title("Measured Speed - Strict Pair (mph)")
        ax3.set_xlabel("Time")
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax3.set_xlim(time_stamp_lim)
        ax3.set_ylabel("Speed (mph)")
        ax3.legend()

        # Saving to directory
        _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + ".png")
        # plt.savefig(_fig_dir)
        plt.show()

        figure_resample = plt.figure(figsize=(16, 9), dpi=150)
        titlename = os.path.basename(os.path.dirname(fdir)) + "-Resampled"
        figure_resample.suptitle(titlename)
        ax1 = figure_resample.add_subplot(3,1,1)
        df_static_veh = df_static_veh.resample(rule="1S").mean()
        df_moving_veh = df_moving_veh.resample(rule="1S").mean()
        ax1.plot(df_static_veh.index, df_static_veh["Correction Distance (mm)"], label="V{} against V{}".format(static_veh, moving_veh))
        ax1.plot(df_moving_veh.index, df_moving_veh["Correction Distance (mm)"], label="V{} against V{}".format(moving_veh, static_veh))
        if ground_truth_df is not None:
            ax1.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["Surveyed Distance (mm)"], label="Timestamped Location (Video)",  marker='*',markerfacecolor = 'r')
        ax1.set_title("Time Series Distance (mm)")
        ax1.set_xlim(time_stamp_lim)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax1.set_ylabel("Distance (mm)")
        ax1.legend()

        ax2 = figure_resample.add_subplot(3,1,2)
        ax2.plot(df_static_veh_hz_cleaned.index, df_static_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{} against V{}".format(static_veh, moving_veh))
        ax2.plot(df_moving_veh_hz_cleaned.index, df_moving_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{} against V{}".format(moving_veh, static_veh))
        ax2.set_title("Time Series Update Rate (Hz)")
        ax2.set_xlim(time_stamp_lim)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax2.set_ylabel("UWB Reporting Frequency (Hz)")
        ax2.legend()
        
        # Instant Speed UWB Strict
        # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
        ax3 = figure_resample.add_subplot(3,1,3)
        slices_uwb_spd_strict_pair = []
        for master_id in df['Initiating Master'].unique():
            for slave_id in df['Reporting Slave'].unique():
                sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)].copy()
                _dist_diff = df["Correction Distance (mm)"].diff().fillna(0.)
                _time_diff = df["Timestamp Norm (s)"].diff().fillna(0.)
                spd_mph = (_dist_diff / _time_diff) * 0.00223694
                spd_mph = spd_mph.to_frame('UWB Measured Speed - Strict Pair (mph)')
                sliced_by_designated_slave = pd.concat([sliced_by_designated_slave, spd_mph])
                slices_uwb_spd_strict_pair.append(sliced_by_designated_slave)
        added_spd_uwb_strict_pair = pd.DataFrame()
        added_spd_uwb_strict_pair.sort_index(inplace=True)
        for _df in slices_uwb_spd_strict_pair:
            added_spd_uwb_strict_pair = pd.concat([added_spd_uwb_strict_pair, _df])
            added_spd_uwb_strict_pair.sort_values(['Initiating Vehicle', 'Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True, True])
        if not added_spd_uwb_strict_pair.empty:
            _ = added_spd_uwb_strict_pair.resample(rule="1S").mean()
            ax3.plot(_.index, _["UWB Measured Speed - Strict Pair (mph)"], label="UWB Measured Speed".format(moving_veh))
        if ground_truth_df is not None:
            # Calculate Ground Truth Instant Speed
            dist_diff = ground_truth_df["Camera Dist to Static Veh (CPLR, mm)"].diff().fillna(0.).copy()
            time_diff = ground_truth_df["Time UNIX Norm (s)"].diff().fillna(0.).copy()
            instant_spd = (dist_diff / time_diff) * 0.00223694
            ground_truth_df["Instant Speed by Marker (mph)"] = instant_spd
            ax3.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["Instant Speed by Marker (mph)"], label="Ground Measured Speed (mph)",  marker='*',markerfacecolor = 'r')
        ax3.axhline(y=0, color='r', linestyle='dashed', label="Zero Speed")
        ax3.set_title("Measured Speed - Strict Pair (mph)")
        ax3.set_xlabel("Time")
        ax3.set_xlim(time_stamp_lim)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax3.set_ylabel("Speed (mph)")
        ax3.legend()

        # Saving to directory
        _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + "_resampled.png")
        # plt.savefig(_fig_dir)
        plt.show()