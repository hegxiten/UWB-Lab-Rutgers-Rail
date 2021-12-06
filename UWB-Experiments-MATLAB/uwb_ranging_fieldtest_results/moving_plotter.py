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
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
CALIBRATED_CAM_TO_V2B = -6400.8
pd.set_option('display.float_format', lambda x: '%.5f' % x)
pd.set_option('display.max_rows', None)

RESAMPLE_RULE = "1S"

static_main_master = '0C1A'
static_focusing_slaves = ['1912', '8D38']
static_master_slave_mapping = { '0C1A': [static_focusing_slaves[0], static_focusing_slaves[1]],
                        '9B0F': [static_focusing_slaves[1], static_focusing_slaves[0]]}
moving_main_master = '88BA'
moving_focusing_slaves = ['45BA', '0B8A']
moving_master_slave_mapping = { '88BA': [moving_focusing_slaves[0], moving_focusing_slaves[1]],
                        '111C': [moving_focusing_slaves[1], moving_focusing_slaves[0]]}
static_veh, moving_veh = 1, 2

static_stats_list_pairwise = []
static_stats_list_aggregated = []
moving_stats_list_pairwise = []
moving_stats_list_aggregated = []

static_stats_dist_idx = []
moving_stats_dist_idx = []

test_file_list, ground_truth_list = post_process_get_moving_test_data_and_timestamp(ROOT_DIR, "Moving Test 1 (V2V)", "V2", CALIBRATED_CAM_TO_V2B)
assert(len(test_file_list) == len(ground_truth_list))
for i in range(len(test_file_list)):
    test_file, ground_truth = test_file_list[i], ground_truth_list[i]
    if "data-A-user-processed_log" in test_file and os.path.basename(test_file).startswith("2021"):
        continue
    _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
    _integ_csv_base = "Integrated_ABAB_COMBO-" + _test_csv_base.split("PostProcessed_")[1].split("-data-")[0] + ".csv"
    _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)
    
    # Processing Statistics
    base_folder = os.path.dirname(_integ_csv_dir)
    raw_name = os.path.basename(os.path.dirname(_integ_csv_dir))
    print("processing: " + raw_name)
    df = pd.read_csv(_integ_csv_dir, parse_dates=["Datetime Normalized"], index_col=["Datetime Normalized"])

    df["Test Name"] = raw_name
    df["Test Category"] = "Moving Test"
    df["Aggregated Update Rate (Hz)"] = np.nan
    df['UWB Measured Instant Speed - Strict Pair (mph)'] = np.nan
    df['Aggregated Measured Speed (mph)'] = np.nan
    df['Test Start Time'] = pd.to_datetime(re.match('^[0-9]+[\-][0-9]+[\-][0-9]+[\-][0-9]+[\-][0-9]+[\-][0-9]+', 
                                                    raw_name)[0],
                                           format="%Y-%m-%d-%H-%M-%S")
    # Filter out distance measurement outliers 
    df, df_outlier = uwb_dist_outlier_identify(df, segments = 5)
    # Remove duplicated index
    _newindex = df.reset_index().groupby("Datetime Normalized")["Datetime Normalized"].apply(lambda x: x + np.arange(x.size).astype('timedelta64[ms]'))
    df.index = _newindex
    if df.empty:
        print(raw_name + " No Data")
        continue

    moving_ground_truth_df = ground_truth
    df_static_veh_all_pairs = df[df['Initiating Vehicle'] == static_veh]
    df_moving_veh_all_pairs = df[df['Initiating Vehicle'] == moving_veh]
    df_static_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)

    df_static_veh_hz_aggregated_all_pairs = update_rate_by_strict_pairs(        df_static_veh_all_pairs, 
                                                                                static_master_slave_mapping.keys(), 
                                                                                static_focusing_slaves)
    df_moving_veh_hz_aggregated_all_pairs = update_rate_by_strict_pairs(        df_moving_veh_all_pairs, 
                                                                                moving_master_slave_mapping.keys(), 
                                                                                moving_focusing_slaves)
    df_static_veh_hz_aggregated_all_pairs = instant_spd_by_strict_pairs(        df_static_veh_hz_aggregated_all_pairs, 
                                                                                static_master_slave_mapping.keys(), 
                                                                                static_focusing_slaves)
    df_moving_veh_hz_aggregated_all_pairs = instant_spd_by_strict_pairs(        df_moving_veh_hz_aggregated_all_pairs, 
                                                                                moving_master_slave_mapping.keys(), 
                                                                                moving_focusing_slaves)

    df_static_veh_hz_aggregated_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_hz_aggregated_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)

    if moving_ground_truth_df is not None:
        # Calculate Ground Truth Instant Speed
        dist_diff = moving_ground_truth_df["Camera Dist to Static Veh (CPLR, mm)"].diff()
        time_diff = moving_ground_truth_df["Time UNIX Norm (s)"].diff()
        instant_spd = (dist_diff / time_diff) * 0.00223694
        moving_ground_truth_df["Instant Speed by Marker (mph)"] = instant_spd

        df_static_veh_hz_aggregated_all_pairs = interpolate_ground_truth(df_static_veh_hz_aggregated_all_pairs, moving_ground_truth_df)
        df_moving_veh_hz_aggregated_all_pairs = interpolate_ground_truth(df_moving_veh_hz_aggregated_all_pairs, moving_ground_truth_df)
        static_stats_dist_idx.append(df_static_veh_hz_aggregated_all_pairs.set_index("Surveyed Distance (mm)"))
        moving_stats_dist_idx.append(df_moving_veh_hz_aggregated_all_pairs.set_index("Surveyed Distance (mm)"))

    # Stats generate
    df_stats_pairwise_static = generate_stats_pairwise(df_static_veh_hz_aggregated_all_pairs, 
                                                       static_veh, 
                                                       None, 
                                                       static_master_slave_mapping, 
                                                       static_main_master,
                                                       raw_name)
    df_stats_aggregated_static = generate_stats_aggregated(df_static_veh_hz_aggregated_all_pairs, 
                                                           static_veh, 
                                                           None,
                                                           raw_name)
    static_stats_list_pairwise.append(df_stats_pairwise_static)
    static_stats_list_aggregated.append(df_stats_aggregated_static)
    df_stats_pairwise_moving = generate_stats_pairwise(df_moving_veh_hz_aggregated_all_pairs, 
                                                       moving_veh, 
                                                       None, 
                                                       moving_master_slave_mapping, 
                                                       moving_main_master,
                                                       raw_name)
    df_stats_aggregated_moving = generate_stats_aggregated(df_moving_veh_hz_aggregated_all_pairs, 
                                                           moving_veh, 
                                                           None,
                                                           raw_name)
    moving_stats_list_pairwise.append(df_stats_pairwise_moving)
    moving_stats_list_aggregated.append(df_stats_aggregated_moving)
    
    ######################################################
    # Plotting individual tests
    ######################################################
    # print("plotting: " + raw_name)
    # figure = plt.figure(figsize=(16, 9), dpi=150)
    # figure_resample = plt.figure(figsize=(16, 9), dpi=150)
    # if "moving" in raw_name.split("-v2-")[0]:
    #     titlename = "Moving Test - " + raw_name.split("-v2-")[-1]
    #     figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
    # else:
    #     titlename = "Virtual Moving Test - " + raw_name.split("-v2-")[-1]
    #     figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
    # plot_time_series_dist(  figure=figure,
    #                         arrange_spec=311,
    #                         static_veh_df=df_static_veh_hz_aggregated_all_pairs,
    #                         moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
    #                         static_veh=static_veh,
    #                         moving_veh=moving_veh,
    #                         df_outlier=df_outlier,
    #                         surveyed_static_ground_truth_value=None,
    #                         moving_ground_truth_df=moving_ground_truth_df)

    # plot_upd_rate(  figure=figure,
    #                 arrange_spec=312,
    #                 static_veh_df=df_static_veh_hz_aggregated_all_pairs,
    #                 moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
    #                 static_veh=static_veh,
    #                 moving_veh=moving_veh,
    #                 moving_ground_truth_df=moving_ground_truth_df
    #                 )

    # # Instant Speed UWB Strict
    # # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
    # plot_time_series_speed( figure=figure, 
    #                         arrange_spec=313, 
    #                         static_veh_df=df_static_veh_hz_aggregated_all_pairs, 
    #                         moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
    #                         static_veh=static_veh,
    #                         moving_veh=moving_veh,
    #                         moving_ground_truth_df=moving_ground_truth_df)
    # titlename = titlename + "-Resampled"
    # figure_resample.suptitle(titlename, fontsize='x-large', fontweight='bold')
    # plot_time_series_dist(  figure=figure_resample,
    #                         arrange_spec=311,
    #                         static_veh_df=df_static_veh_hz_aggregated_all_pairs,
    #                         moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
    #                         static_veh=static_veh,
    #                         moving_veh=moving_veh,
    #                         df_outlier=df_outlier,
    #                         surveyed_static_ground_truth_value=None,
    #                         moving_ground_truth_df=moving_ground_truth_df,
    #                         resample=True)

    # plot_upd_rate(  figure=figure_resample,
    #                 arrange_spec=312,
    #                 static_veh_df=df_static_veh_hz_aggregated_all_pairs,
    #                 moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
    #                 static_veh=static_veh,
    #                 moving_veh=moving_veh,
    #                 moving_ground_truth_df=moving_ground_truth_df,
    #                 resample=True)

    # # Instant Speed UWB Strict
    # # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
    # plot_time_series_speed( figure=figure_resample, 
    #                         arrange_spec=313, 
    #                         static_veh_df=df_static_veh_hz_aggregated_all_pairs, 
    #                         moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
    #                         static_veh=static_veh,
    #                         moving_veh=moving_veh,
    #                         moving_ground_truth_df=moving_ground_truth_df,
    #                         resample=True)
    # figure.tight_layout(pad=1.0)
    # figure_resample.tight_layout(pad=1.0)
    # figure_error = plt.figure(figsize=(16, 9), dpi=150)
    # plot_time_series_error( figure=figure_error,
    #                         arrange_spec=111,
    #                         static_veh_df=df_static_veh_hz_aggregated_all_pairs,
    #                         moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
    #                         static_veh=static_veh,
    #                         moving_veh=moving_veh,
    #                         df_outlier=df_outlier,
    #                         surveyed_static_ground_truth_value=None,
    #                         moving_ground_truth_df=moving_ground_truth_df,
    #                         ax=None)

    # plt.show()

df_all_static_stats_pairwise_moving_test = pd.concat(static_stats_list_pairwise, ignore_index=True)
df_all_static_stats_aggregated_moving_test = pd.concat(static_stats_list_aggregated, ignore_index=True)
df_all_static_stats_aggregated_moving_test["Main Pair Counts"] = np.array(df_all_static_stats_pairwise_moving_test[(df_all_static_stats_pairwise_moving_test["Is Main Master"]==True) & (df_all_static_stats_pairwise_moving_test["Is Main Slave"]==True)]["Reporting Counts"])
df_all_moving_stats_pairwise_moving_test = pd.concat(moving_stats_list_pairwise, ignore_index=True)
df_all_moving_stats_aggregated_moving_test = pd.concat(moving_stats_list_aggregated, ignore_index=True)
df_all_moving_stats_aggregated_moving_test["Main Pair Counts"] = np.array(df_all_moving_stats_pairwise_moving_test[(df_all_moving_stats_pairwise_moving_test["Is Main Master"]==True) & (df_all_moving_stats_pairwise_moving_test["Is Main Slave"]==True)]["Reporting Counts"])

df_all_static_stats_dist_idx_moving_test = pd.concat(static_stats_dist_idx)
df_all_moving_stats_dist_idx_moving_test = pd.concat(moving_stats_dist_idx)

from matplotlib.ticker import FuncFormatter
figure = plt.figure(figsize=(16, 9), dpi=150)
width=0.3
labels = df_all_static_stats_aggregated_moving_test["Test Name"].astype(str)
ax = figure.add_subplot(111)
ax.set_title("Measurement Precision (STD)")
errbar_1 = ax.errorbar(x=np.arange(len(labels.index)) - width/2, 
                       y=df_all_static_stats_aggregated_moving_test["Average Measurement Error (mm)"],
                       yerr=df_all_static_stats_aggregated_moving_test["STD (mm)"],
                       capsize=10,
                       linestyle='--',
                       marker='o',
                       label='Avg. Error with STD, V{}\n(Static Vehicle)'.format(static_veh))
errbar_2 = ax.errorbar(x=np.arange(len(labels.index)) + width/2, 
                       y=df_all_static_stats_aggregated_moving_test["Average Measurement Error (mm)"],
                       yerr=df_all_moving_stats_aggregated_moving_test["STD (mm)"],
                       capsize=10,
                       linestyle='--',
                       marker='o',
                       label='Avg. Error with STD, V{}\n(Moving Vehicle)'.format(moving_veh))
ax.set_xlabel("Manually Measured Distance (mm), Individual Tests")
ax.set_xticks(np.arange(len(labels.index)))
ax.set_xticklabels([x.split("-v2-")[1] for x in list(labels)])
ax.set_ylabel("Measurement Evaluation Metrics (mm)")
# ax2 = ax.twinx()
# rects1 = ax2.bar(np.arange(len(labels.index)) - width/2,
#                  df_all_static_stats_aggregated_moving_test["Downtime Duration"] / df_all_static_stats_aggregated_moving_test["Operation Duration"],
#                  width=width, label='V{} Connection Downtime %'.format(static_veh), alpha=0.5)
# rects2 = ax2.bar(np.arange(len(labels.index)) + width/2,
#                  df_all_moving_stats_aggregated_moving_test["Downtime Duration"] / df_all_moving_stats_aggregated_moving_test["Operation Duration"],
#                  width=width, label='V{} Connection Downtime %'.format(moving_veh), alpha=0.5)
# ax2.set_xticks(np.arange(len(labels.index)))
# ax2.set_xticklabels([x.split("-v2-")[1] for x in list(labels)])
# ax2.set_ylabel("Downtime Percentage % (Exponential)")
# ax2.set_ylim([0, 1])
# ax2.bar_label(rects1, padding=3, labels=['{:.2%}'.format(x).lstrip('0') for x in rects1.datavalues], fontsize=8)
# ax2.bar_label(rects2, padding=3, labels=['{:.2%}'.format(x).lstrip('0') for x in rects2.datavalues], fontsize=8)
# ax2.grid(axis='y', linestyle='--')
# ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:.0%}'.format(y)))

# ax.legend([errbar_1, errbar_2, rects1, rects2], 
#           [errbar_1.get_label(), errbar_2.get_label(), 
#           rects1.get_label(), 
#           rects2.get_label()],
#           loc="upper center")

plt.show()

df_all_static_stats_dist_idx_moving_test = df_all_static_stats_dist_idx_moving_test.dropna('index')
figure = plt.figure(figsize=(16, 9), dpi=150)
ax = figure.add_subplot(111)
ax.set_title("Measuring Distance Error v.s Ground Truth Distance By Tests")
labels = df_all_static_stats_dist_idx_moving_test["Test Name"].astype(str)
i = 0
for test in list(labels.unique()):
    if i > 0:
        _test_df = df_all_static_stats_dist_idx_moving_test[df_all_static_stats_dist_idx_moving_test["Test Name"] == test]
        ax.scatter(_test_df.index, _test_df["Correction Distance (mm)"] - _test_df.index, alpha=0.3,  marker="o", color="C0")
        _test_df = df_all_moving_stats_dist_idx_moving_test[df_all_moving_stats_dist_idx_moving_test["Test Name"] == test]
        ax.scatter(_test_df.index, _test_df["Correction Distance (mm)"] - _test_df.index, alpha=0.3,  marker="D", color="C1")
    else:
        _test_df = df_all_static_stats_dist_idx_moving_test[df_all_static_stats_dist_idx_moving_test["Test Name"] == test]
        ax.scatter(_test_df.index, _test_df["Correction Distance (mm)"] - _test_df.index, alpha=0.3,  marker="o", color="C0", label = "Static Vehicle (V1) Ranging, All Tests")
        _test_df = df_all_moving_stats_dist_idx_moving_test[df_all_moving_stats_dist_idx_moving_test["Test Name"] == test]
        ax.scatter(_test_df.index, _test_df["Correction Distance (mm)"] - _test_df.index, alpha=0.3,  marker="D", color="C1", label = "Moving Vehicle (V2) Ranging, All Tests")
    i += 1
ax.set_xlabel("Ground Truth Distance (mm)")
ax.set_xlim(left=0)
ax.set_ylabel("Absolute Error (mm)")
ax.legend()
plt.show()