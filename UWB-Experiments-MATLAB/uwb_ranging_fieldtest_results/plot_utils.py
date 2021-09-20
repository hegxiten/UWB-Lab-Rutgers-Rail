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
from utils import remove_distance_outlier, remove_freq_outlier

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
CALIBRATED_CAM_TO_V2B = -6400.8
pd.set_option('display.float_format', lambda x: '%.5f' % x)


def plot_time_series_ranging(fdir, ground_truth_df, static_veh, moving_veh=2):
    base_folder = os.path.dirname(fdir)
    df = pd.read_csv(fdir, parse_dates=["Datetime Normalized"], index_col=["Datetime Normalized"])
    df_static_veh = remove_distance_outlier(df[df['Initiating Vehicle'] == static_veh], "Correction Distance (mm)") 
    df_moving_veh = remove_distance_outlier(df[df['Initiating Vehicle'] == moving_veh], "Correction Distance (mm)")
    df_static_veh.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    surveyed_dist = df_static_veh["Surveyed Distance (mm)"].get(0, float('nan'))
    df_static_veh_hz_cleaned = remove_freq_outlier(df_static_veh[df_static_veh['Initiating Vehicle'] == static_veh])
    df_moving_veh_hz_cleaned = remove_freq_outlier(df_moving_veh[df_moving_veh['Initiating Vehicle'] == moving_veh])
    
    if df.empty:
        return
    
    if ground_truth_df is not None:
        time_stamp_lim = [
            min(df.index.min() - pd.Timedelta(seconds=10), pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s').min() - pd.Timedelta(seconds=10)),
            max(df.index.max() + pd.Timedelta(seconds=10), pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s').max() + pd.Timedelta(seconds=10))
            ]
    else:
        time_stamp_lim = [
            df.index.min() - pd.Timedelta(seconds=10),
            df.index.max() + pd.Timedelta(seconds=10)
            ]

    # Plotting
    figure = plt.figure(figsize=(16, 9), dpi=150)
    titlename = os.path.basename(os.path.dirname(fdir))
    figure.suptitle(titlename)

    if not np.isnan(surveyed_dist): # Static Experiment
        ax1 = figure.add_subplot(2,2,1)
        ax1.plot(df_static_veh.index, df_static_veh["Correction Distance (mm)"], label="V{}".format(str(static_veh)))
        ax1.plot(df_moving_veh.index, df_moving_veh["Correction Distance (mm)"], label="V{}".format(str(moving_veh)))
        if not np.isnan(surveyed_dist):
            ax1.plot(df_moving_veh.index, [surveyed_dist] * df_moving_veh["Timestamp Norm (s)"].shape[0], label="Manually Measured")
        if ground_truth_df is not None:
            ax1.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"], label="Timestamped Location (Video)",  marker='*',markerfacecolor = 'r')
        ax1.set_title("Time Series Distance (mm)")
        ax1.set_xlabel("Time")
        ax1.set_xlim(time_stamp_lim)
        ax1.set_ylabel("Distance (mm)")
        ax1.legend()

        ax2 = figure.add_subplot(2,2,3)
        ax2.plot(df_static_veh_hz_cleaned.index, df_static_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{}".format(static_veh))
        ax2.plot(df_moving_veh_hz_cleaned.index, df_moving_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{}".format(moving_veh))
        ax2.set_title("Time Series Update Rate (Hz)")
        ax2.set_xlabel("Time")
        ax2.set_xlim(time_stamp_lim)
        ax2.set_ylabel("UWB Reporting Frequency (Hz)")
        ax2.legend()

        ax3 = figure.add_subplot(2,2,2)
        ax3.hist(df_static_veh["Correction Distance (mm)"], bins=20)
        ax3.axvline(x=surveyed_dist, color='r', linestyle='dashed', linewidth=2, label="Manually Measured")
        ax3.set_title("Hist - Vehicle {} (Static)".format(str(static_veh)))
        ax3.set_xlabel("Distance (mm)")
        ax3.set_ylabel("Counts")
        ax3.legend()
        
        ax4 = figure.add_subplot(2,2,4)
        ax4.hist(df_moving_veh["Correction Distance (mm)"], bins=20)
        ax4.axvline(x=surveyed_dist, color='r', linestyle='dashed', linewidth=2, label="Manually Measured")
        ax4.set_title("Hist - Vehicle {} (Mover)".format(str(moving_veh)))
        ax4.set_xlabel("Distance (mm)")
        ax4.set_ylabel("Counts")
        ax4.legend()
        
        # Saving to directory
        _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + ".png")
        # plt.savefig(_fig_dir)
        plt.show()
    
    else: # Moving Experiment
        ax1 = figure.add_subplot(3,1,1)
        ax1.plot(df_static_veh.index, df_static_veh["Correction Distance (mm)"], label="V{}".format(str(static_veh)))
        ax1.plot(df_moving_veh.index, df_moving_veh["Correction Distance (mm)"], label="V{}".format(str(moving_veh)))
        if not np.isnan(surveyed_dist):
            ax1.plot(pd.to_datetime(df_moving_veh["Datetime Normalized"]), [surveyed_dist] * df_moving_veh["Timestamp Norm (s)"].shape[0], label="Manually Measured")
        if ground_truth_df is not None:
            ax1.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"], label="Timestamped Location (Video)",  marker='*',markerfacecolor = 'r')
        ax1.set_title("Time Series Distance (mm)")
        ax1.set_xlim(time_stamp_lim)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax1.set_ylabel("Distance (mm)")
        ax1.legend()

        ax2 = figure.add_subplot(3,1,2)
        ax2.plot(df_static_veh_hz_cleaned.index, df_static_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{}".format(static_veh))
        ax2.plot(df_moving_veh_hz_cleaned.index, df_moving_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{}".format(moving_veh))
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
        if not added_spd_uwb_strict_pair.empty:
            _ = added_spd_uwb_strict_pair.resample(rule="100L").mean()
            ax3.plot(added_spd_uwb_strict_pair.index, added_spd_uwb_strict_pair["UWB Measured Speed - Strict Pair (mph)"], label="UWB Measured Speed".format(str(moving_veh)))
        if ground_truth_df is not None:
            # Calculate Ground Truth Instant Speed
            dist_diff = ground_truth_df["Camera Dist to Static Veh (CPLR, mm)"].diff().fillna(0.)
            time_diff = ground_truth_df["Time UNIX Norm (s)"].diff().fillna(0.)
            ground_truth_df["Instant Speed by Marker (mph)"] = (dist_diff / time_diff) * 0.00223694
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
        ax1.plot(df_static_veh.index, df_static_veh["Correction Distance (mm)"], label="V{}".format(str(static_veh)))
        ax1.plot(df_moving_veh.index, df_moving_veh["Correction Distance (mm)"], label="V{}".format(str(moving_veh)))
        if not np.isnan(surveyed_dist):
            ax1.plot(pd.to_datetime(df_moving_veh["Datetime Normalized"]), [surveyed_dist] * df_moving_veh["Timestamp Norm (s)"].shape[0], label="Manually Measured")
        if ground_truth_df is not None:
            ax1.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"], label="Timestamped Location (Video)",  marker='*',markerfacecolor = 'r')
        ax1.set_title("Time Series Distance (mm)")
        ax1.set_xlim(time_stamp_lim)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax1.set_ylabel("Distance (mm)")
        ax1.legend()

        ax2 = figure_resample.add_subplot(3,1,2)
        ax2.plot(df_static_veh_hz_cleaned.index, df_static_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{}".format(static_veh))
        ax2.plot(df_moving_veh_hz_cleaned.index, df_moving_veh_hz_cleaned["Instant Update Rate (Hz)"], label="V{}".format(moving_veh))
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
        for _df in slices_uwb_spd_strict_pair:
            added_spd_uwb_strict_pair = pd.concat([added_spd_uwb_strict_pair, _df])
            added_spd_uwb_strict_pair.sort_values(['Initiating Vehicle', 'Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True, True])
        if not added_spd_uwb_strict_pair.empty:
            _ = added_spd_uwb_strict_pair.resample(rule="1S").mean()
            ax3.plot(_.index, _["UWB Measured Speed - Strict Pair (mph)"], label="UWB Measured Speed".format(str(moving_veh)))
        if ground_truth_df is not None:
            # Calculate Ground Truth Instant Speed
            dist_diff = ground_truth_df["Camera Dist to Static Veh (CPLR, mm)"].diff().fillna(0.)
            time_diff = ground_truth_df["Time UNIX Norm (s)"].diff().fillna(0.)
            ground_truth_df["Instant Speed by Marker (mph)"] = (dist_diff / time_diff) * 0.00223694
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