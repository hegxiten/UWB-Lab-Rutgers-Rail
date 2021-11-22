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

from scipy import optimize

from utils import post_process_get_moving_test_data_and_timestamp, remove_outlier_by_quantile
from stats_utils import *

from pandas.core.common import SettingWithCopyWarning
import warnings
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
CALIBRATED_CAM_TO_V2B = -6400.8
pd.set_option('display.float_format', lambda x: '%.5f' % x)

MAX_REPORTING_RATE_PER_VEHICLE = 40 # Hz
MIN_REPORTING_INTERVAL = 0.1        # Sec

MAX_UPD_RATE = 40
NUL_UPD_RATE = 0
MARKER_SIZE = 20

ROLLING_WINDOW = 10


def segments_fit(X, Y, count):
    xmin = X.min()
    xmax = X.max()

    seg = np.full(count - 1, (xmax - xmin) / count)

    px_init = np.r_[np.r_[xmin, seg].cumsum(), xmax]
    py_init = np.array([Y[np.abs(X - x) < (xmax - xmin) * 0.01].mean() for x in px_init])
    
    def helper_separate_1d_to_2d(p):
        seg = p[:count - 1]
        py = p[count - 1:]
        px = np.r_[np.r_[xmin, seg].cumsum(), xmax]
        return px, py

    def err(p):
        px, py = helper_separate_1d_to_2d(p)
        Y2 = np.interp(X, px, py)
        return np.mean((Y - Y2)**2)
    r = optimize.minimize(err, x0=np.r_[seg, py_init], method='Nelder-Mead')
    return helper_separate_1d_to_2d(r.x)


def uwb_dist_outlier_identify(df, threshold=5000, segments=5):
    px, py = segments_fit(df['Timestamp Norm (s)'], df['Correction Distance (mm)'], segments)
    px, py = px[~np.isnan(py)], py[~np.isnan(py)]
    X, Y = df['Timestamp Norm (s)'], df['Correction Distance (mm)']
    assert px.size == py.size
    if px.size != 0:
        Y2 = np.interp(X, px, py)
        df_outlier = df[np.abs(Y2 - Y) >  threshold]
        df_cleaned = df[np.abs(Y2 - Y) <=  threshold]
        return df_cleaned, df_outlier
    else:
        return df, df.drop(df.index)


def update_rate_by_strict_pairs(df, masters, slaves):
    slices_designated_slave = []
    for master_id in df['Initiating Master'].unique():
        if master_id in masters:
            for slave_id in df['Reporting Slave'].unique():
                if slave_id in slaves:
                    sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)]
                    sliced_by_designated_slave["Instant Update Rate (Hz)"] = (1 / sliced_by_designated_slave['Timestamp Norm (s)'].diff().clip(MIN_REPORTING_INTERVAL))
                    slices_designated_slave.append(sliced_by_designated_slave)
    if slices_designated_slave:
        df = pd.concat(slices_designated_slave)
        df.sort_values( ['Timestamp Norm (s)'], ascending=[True], inplace=True)
        df["Aggregated Update Rate (Hz)"] = ((ROLLING_WINDOW - 1) / df["Timestamp Norm (s)"].rolling(ROLLING_WINDOW).apply(lambda x: x[-1] - x[0])).clip(upper=MAX_REPORTING_RATE_PER_VEHICLE)
    return df


def instant_spd_by_strict_pairs(df, masters, slaves):
    slices_uwb_spd_strict_pair = []
    for master_id in df['Initiating Master'].unique():
        if master_id in masters:
            for slave_id in df['Reporting Slave'].unique():
                if slave_id in slaves:
                    sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)]
                    _dist_diff = sliced_by_designated_slave["Correction Distance (mm)"].diff().fillna(0.)
                    _time_diff = sliced_by_designated_slave["Timestamp Norm (s)"].diff().fillna(0.)
                    spd_mph = (_dist_diff / _time_diff) * 0.00223694
                    spd_mph = spd_mph.to_frame('UWB Measured Instant Speed - Strict Pair (mph)')
                    sliced_by_designated_slave['UWB Measured Instant Speed - Strict Pair (mph)'] = spd_mph['UWB Measured Instant Speed - Strict Pair (mph)']
                    slices_uwb_spd_strict_pair.append(sliced_by_designated_slave)
    if slices_uwb_spd_strict_pair:
        df = pd.concat(slices_uwb_spd_strict_pair)
        df.sort_values(['Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True], inplace=True)
        df["Aggregated Measured Speed (mph)"] = df["Correction Distance (mm)"].rolling(ROLLING_WINDOW).apply(lambda x: x[-1] - x[0]) \
            / (df["Timestamp Norm (s)"].rolling(ROLLING_WINDOW).max() - df["Timestamp Norm (s)"].rolling(ROLLING_WINDOW).min()) * 0.00223694
        return df
    else:
        return df

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
                            resample=False):
    ax = figure.add_subplot(arrange_spec)
    if resample:
        static_veh_df = static_veh_df.resample(rule=RESAMPLE_RULE).mean()
        moving_veh_df = moving_veh_df.resample(rule=RESAMPLE_RULE).mean()
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
    ax.set_xlim(_xlim)
    ax.set_xlabel("Time")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_ylabel("Distance (mm)")   
    ax.legend()


def plot_upd_rate(  figure, 
                    arrange_spec, 
                    static_veh_df, 
                    moving_veh_df, 
                    static_veh, 
                    moving_veh,
                    moving_ground_truth_df, 
                    resample=False):
    ax = figure.add_subplot(arrange_spec)
    if resample:
        static_veh_df = static_veh_df.resample(rule=RESAMPLE_RULE).mean()
        moving_veh_df = moving_veh_df.resample(rule=RESAMPLE_RULE).mean()
        ax.plot(static_veh_df.index, 
                static_veh_df["Aggregated Update Rate (Hz)"], 
                label="Static V{} against Mover V{}".format(static_veh, moving_veh),
                alpha=0.9,
                color='C0',
                linestyle="-")
        ax.plot(moving_veh_df.index, 
                moving_veh_df["Aggregated Update Rate (Hz)"], 
                label="Mover V{} against Static V{}".format(moving_veh, static_veh),
                alpha=0.9,
                color='C1',
                linestyle="-")
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
    ax.set_ylabel("Aggregated UWB Reporting Frequency (Hz)")

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
                        label="V{}: {} against {}".format(veh, master, slave),
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
    ax2.set_ylabel("Kernel Density Estimation (KDE)")
    ax.legend()


def plot_time_series_speed( figure, 
                            arrange_spec, 
                            static_veh_df, 
                            moving_veh_df, 
                            static_veh, 
                            moving_veh, 
                            moving_ground_truth_df, 
                            resample=False):
    ax = figure.add_subplot(arrange_spec)
    if resample:
        # Static
        static_veh_df = static_veh_df.resample(rule=RESAMPLE_RULE).mean()
        ax.plot(static_veh_df.index, 
                static_veh_df["Aggregated Measured Speed (mph)"], 
                label="UWB Measured Relative Speed by V{}".format(static_veh),
                alpha=0.8,
                linestyle="--")
        # Moving
        moving_veh_df = moving_veh_df.resample(rule=RESAMPLE_RULE).mean()
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



def plot_static_differentiate_pairs(fdir, 
                                    ground_truth_df, 
                                    static_veh, 
                                    moving_veh,
                                    static_main_master,
                                    static_master_slave_mapping,
                                    static_focusing_slaves,
                                    moving_main_master,
                                    moving_master_slave_mapping, 
                                    moving_focusing_slaves,):
    # Deprecate Me
    base_folder = os.path.dirname(fdir)
    df = pd.read_csv(fdir, parse_dates=["Datetime Normalized"], index_col=["Datetime Normalized"])
    if df.empty:
        return
    df.sort_values(['Initiating Vehicle', 'Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], 
                   ascending=[True, True, True, True], 
                   inplace=True)
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

    # -------------------------------
    df_static_veh_strict_pair = remove_outlier_by_quantile(
        df[
            (df['Initiating Vehicle'] == static_veh) & (df["Initiating Master"] == static_main_master) & (df["Reporting Slave"] == static_master_slave_mapping[static_main_master][0])
            ], "Correction Distance (mm)") 
    df_moving_veh_strict_pair = remove_outlier_by_quantile(
        df[
            (df['Initiating Vehicle'] == moving_veh) & (df["Initiating Master"] == moving_main_master) & (df["Reporting Slave"] == moving_master_slave_mapping[moving_main_master][0])
            ], "Correction Distance (mm)")
    df_static_veh_strict_pair_hz_cleaned = remove_outlier_by_quantile(df_static_veh_strict_pair, "Instant Update Rate (Hz)")
    df_moving_veh_strict_pair_hz_cleaned = remove_outlier_by_quantile(df_moving_veh_strict_pair, "Instant Update Rate (Hz)")

    df_static_veh_all_pairs = remove_outlier_by_quantile(df[df['Initiating Vehicle'] == static_veh], "Correction Distance (mm)") 
    df_moving_veh_all_pairs = remove_outlier_by_quantile(df[df['Initiating Vehicle'] == moving_veh], "Correction Distance (mm)")
    
    df_static_veh_all_pairs_hz_cleaned = update_rate_by_strict_pairs(df_static_veh_all_pairs, 
                                                                     static_master_slave_mapping.keys(), 
                                                                     static_focusing_slaves)
    df_moving_veh_all_pairs_hz_cleaned = update_rate_by_strict_pairs(df_moving_veh_all_pairs, 
                                                                     moving_master_slave_mapping.keys(), 
                                                                     moving_focusing_slaves)
    df_static_veh_all_pairs_hz_cleaned = remove_outlier_by_quantile(df_static_veh_all_pairs_hz_cleaned[df_static_veh_all_pairs_hz_cleaned['Initiating Vehicle'] == static_veh], "Aggregated Update Rate (Hz)")
    df_moving_veh_all_pairs_hz_cleaned = remove_outlier_by_quantile(df_moving_veh_all_pairs_hz_cleaned[df_moving_veh_all_pairs_hz_cleaned['Initiating Vehicle'] == moving_veh], "Aggregated Update Rate (Hz)")
    
    df_static_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_static_veh_all_pairs_hz_cleaned.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_all_pairs_hz_cleaned.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)

    df_static_veh_all_pairs = df_static_veh_all_pairs.resample(rule="1S").mean()
    df_moving_veh_all_pairs = df_moving_veh_all_pairs.resample(rule="1S").mean()    
        
    df_static_veh_all_pairs_hz_cleaned = df_static_veh_all_pairs_hz_cleaned.resample(rule="1S").mean()
    df_moving_veh_all_pairs_hz_cleaned = df_moving_veh_all_pairs_hz_cleaned.resample(rule="1S").mean()

    df_static_veh_strict_pair = df_static_veh_strict_pair.resample(rule="1S").mean()
    df_moving_veh_strict_pair = df_moving_veh_strict_pair.resample(rule="1S").mean()
        
    df_static_veh_strict_pair_hz_cleaned = df_static_veh_strict_pair_hz_cleaned.resample(rule="1S").mean()
    df_moving_veh_strict_pair_hz_cleaned = df_moving_veh_strict_pair_hz_cleaned.resample(rule="1S").mean()

    # Plotting Differentiated Strict Pair
    figure = plt.figure(figsize=(16, 9), dpi=150)
    raw_name = os.path.basename(os.path.dirname(fdir))
    print("plotting: " + raw_name)
        
    surveyed_dist = df_static_veh_all_pairs["Surveyed Distance (mm)"].get(0, float('nan'))
    if not np.isnan(surveyed_dist):
        titlename = "Static Test - " + raw_name.split("-static-v2-")[-1] + " - " + str(int(surveyed_dist)) + "mm"
    else:
        titlename = "Static Test - " + raw_name.split("-static-v2-")[-1] + " - " "Not Measured"
    figure.suptitle(titlename)
    
    ax1 = figure.add_subplot(2,2,1)
    ax1.plot(df_static_veh_strict_pair.index, 
             df_static_veh_strict_pair["Correction Distance (mm)"], 
             label="V{} against V{}, Master {} Slave {}".format(static_veh, moving_veh, static_main_master, static_master_slave_mapping[static_main_master][0]),
             alpha=0.6,
             linestyle="--")
    ax1.plot(df_static_veh_all_pairs.index, 
             df_static_veh_all_pairs["Correction Distance (mm)"], 
             label="V{} against V{}, Aggregated All Pairs".format(static_veh, moving_veh),
             alpha=0.6,
             linestyle=":")
    ax1.plot(df_moving_veh_strict_pair.index, [surveyed_dist] * df_moving_veh_strict_pair["Timestamp Norm (s)"].shape[0], label="Manually Measured")
    ax1.set_title("Static Vehicle Time Series Distance (mm)")
    ax1.set_xlabel("Time")
    ax1.set_xlim(time_stamp_lim)
    ax1.set_ylabel("Distance (mm)")
    ax1.legend()

    ax2 = figure.add_subplot(2,2,2)
    ax2.plot(df_moving_veh_strict_pair.index, 
             df_moving_veh_strict_pair["Correction Distance (mm)"], 
             label="V{} against V{}, Master {} Slave {}".format(moving_veh, static_veh, moving_main_master, moving_master_slave_mapping[moving_main_master][0]),
             alpha=0.6,
             linestyle="--")
    ax2.plot(df_moving_veh_all_pairs.index, 
             df_moving_veh_all_pairs["Correction Distance (mm)"], 
             label="V{} against V{}, Aggregated All Pairs".format(moving_veh, static_veh),
             alpha=0.6,
             linestyle=":")
    ax2.plot(df_moving_veh_strict_pair.index, [surveyed_dist] * df_moving_veh_strict_pair["Timestamp Norm (s)"].shape[0], label="Manually Measured")
    ax2.set_title("Moving Vehicle Time Series Distance (mm)")
    ax2.set_xlabel("Time")
    ax2.set_xlim(time_stamp_lim)
    ax2.set_ylabel("Distance (mm)")
    ax2.legend()

    # Saving to directory
    _fig_dir = os.path.join(os.path.dirname(os.path.dirname(fdir)), os.path.splitext(os.path.basename(base_folder))[0] + ".png")
    # plt.savefig(_fig_dir)
    plt.show()



if __name__ == "__main__":
    static_main_master_static_test = '0C1A'
    static_focusing_slaves_static_test = ['1912', '8D38']
    static_master_slave_mapping_static_test = { '0C1A': [static_focusing_slaves_static_test[0], static_focusing_slaves_static_test[1]],
                            '9B0F': [static_focusing_slaves_static_test[1], static_focusing_slaves_static_test[0]]}
    moving_main_master_static_test = '88BA'
    moving_focusing_slaves_static_test = ['45BA', '0B8A']
    moving_master_slave_mapping_static_test = { '88BA': [moving_focusing_slaves_static_test[0], moving_focusing_slaves_static_test[1]],
                            '111C': [moving_focusing_slaves_static_test[1], moving_focusing_slaves_static_test[0]]}

    test_file_list, ground_truth_list = post_process_get_moving_test_data_and_timestamp(ROOT_DIR, "Moving Test 1 (V2V)", "V2", CALIBRATED_CAM_TO_V2B)
    TEST_FILE_NAME = "2021-05-25-10-55-51-moving-v2-1-east-reset"
    assert(len(test_file_list) == len(ground_truth_list))
    for i in range(len(test_file_list)):
        test_file, ground_truth = test_file_list[i], ground_truth_list[i]
        if "data-A-user-processed_log" in test_file and os.path.basename(test_file).startswith("2021"):
            continue
        if TEST_FILE_NAME in test_file:
            _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
            _integ_csv_base = "Integrated_ABAB_COMBO-" + _test_csv_base.split("PostProcessed_")[1].split("-data-")[0] + ".csv"
            _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)
            df = pd.read_csv(_integ_csv_dir, parse_dates=["Datetime Normalized"], index_col=["Datetime Normalized"])
        
            df["Aggregated Update Rate (Hz)"] = np.nan
            df['UWB Measured Speed - Strict Pair (mph)'] = np.nan

            # Remove duplicated index
            _newindex = df.reset_index().groupby("Datetime Normalized")["Datetime Normalized"].apply(lambda x: x + np.arange(x.size).astype(np.timedelta64))
            df.index = _newindex
            plot_time_series_ranging(_integ_csv_dir, 
                                    ground_truth, 
                                    static_veh=1, 
                                    moving_veh=2,
                                    static_master_slave_mapping=static_master_slave_mapping_static_test,
                                    static_focusing_slaves=static_focusing_slaves_static_test,
                                    moving_master_slave_mapping=moving_master_slave_mapping_static_test, 
                                    moving_focusing_slaves=moving_focusing_slaves_static_test, 
                                    is_static_plot=False, 
                                    resample_rule=RESAMPLE_RULE)
            break