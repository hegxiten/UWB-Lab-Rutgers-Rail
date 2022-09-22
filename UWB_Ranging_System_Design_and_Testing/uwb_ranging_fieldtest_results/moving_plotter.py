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
all_test_files, ground_truth_list = post_process_get_moving_test_data_and_timestamp(ROOT_DIR, 
                                                                                    "Moving Test 1 (V2V)", 
                                                                                    "V2", 
                                                                                    CALIBRATED_CAM_TO_V2B)
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


TICK_FONT_SIZE = 12
LABEL_FONT_SIZE = 14
AXES_TITLE_SIZE = 16

import matplotlib 
matplotlib.rc('xtick', labelsize=TICK_FONT_SIZE) 
matplotlib.rc('ytick', labelsize=TICK_FONT_SIZE)
matplotlib.rc('axes', labelsize=LABEL_FONT_SIZE) 
matplotlib.rc('axes', titlesize=AXES_TITLE_SIZE)

def parse_single_test_data(test_file, ground_truth):
    # moving test and virtual test parser - identical
    _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
    _integ_csv_base = "Integrated_ABAB_COMBO-" + _test_csv_base.split("PostProcessed_")[1].split("-data-")[0] + ".csv"
    _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)

    # Processing Statistics
    base_folder = os.path.dirname(_integ_csv_dir)
    raw_name = os.path.basename(os.path.dirname(_integ_csv_dir))
    print("processing: " + raw_name)
    df = pd.read_csv(_integ_csv_dir, parse_dates=["Datetime Normalized"], index_col=["Datetime Normalized"])

    # Adding additional columns
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
    _newindex = df.reset_index().groupby("Datetime Normalized")["Datetime Normalized"]\
                    .apply(lambda x: x + np.arange(x.size).astype('timedelta64[ms]'))
    df.index = _newindex
    if df.empty:
        print(raw_name + " No Data")
        return None

    # Separting data frames by data-receiving vehicles 
    moving_ground_truth_df = ground_truth
    df_static_veh_all_pairs = df[df['Initiating Vehicle'] == static_veh]
    df_moving_veh_all_pairs = df[df['Initiating Vehicle'] == moving_veh]
    df_static_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)
    df_moving_veh_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], ascending=[True, True], inplace=True)

    # Adding update rate metrics: strict pairs and instant speed 
    df_static_veh_hz_aggregated_all_pairs = update_rate_by_strict_pairs(df_static_veh_all_pairs, 
                                                                        static_master_slave_mapping.keys(), 
                                                                        static_focusing_slaves)
    df_moving_veh_hz_aggregated_all_pairs = update_rate_by_strict_pairs(df_moving_veh_all_pairs, 
                                                                        moving_master_slave_mapping.keys(), 
                                                                        moving_focusing_slaves)
    df_static_veh_hz_aggregated_all_pairs = instant_spd_by_strict_pairs(df_static_veh_hz_aggregated_all_pairs, 
                                                                        static_master_slave_mapping.keys(), 
                                                                        static_focusing_slaves)
    df_moving_veh_hz_aggregated_all_pairs = instant_spd_by_strict_pairs(df_moving_veh_hz_aggregated_all_pairs, 
                                                                        moving_master_slave_mapping.keys(), 
                                                                        moving_focusing_slaves)
    df_static_veh_hz_aggregated_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], 
                                                      ascending=[True, True], inplace=True)
    df_moving_veh_hz_aggregated_all_pairs.sort_values(['Timestamp Norm (s)', 'Reporting Slave'], 
                                                      ascending=[True, True], inplace=True)
    # Calculate Ground Truth Instant Speed
    if moving_ground_truth_df is not None:
        dist_diff = moving_ground_truth_df["Camera Dist to Static Veh (CPLR, mm)"].diff()
        time_diff = moving_ground_truth_df["Time UNIX Norm (s)"].diff()
        instant_spd = (dist_diff / time_diff) * 0.00223694
        moving_ground_truth_df["Instant Speed by Marker (mph)"] = instant_spd
    
    return {"df_static_veh_hz_aggregated_all_pairs":df_static_veh_hz_aggregated_all_pairs, 
            "df_moving_veh_hz_aggregated_all_pairs":df_moving_veh_hz_aggregated_all_pairs, 
            "df_outlier":df_outlier,
            "df_static_veh_all_pairs":df_static_veh_all_pairs,
            "df_moving_veh_all_pairs":df_moving_veh_all_pairs,
            "static_veh":static_veh,
            "moving_veh":moving_veh,
            "moving_ground_truth_df":moving_ground_truth_df
            }


def plot_single_test_data(raw_name):
    parsing_results = moving_tests.get(raw_name)
    if not parsing_results:
        print(raw_name + " No Data, Not Plotting")
        return
    # Unpack dataframes
    df_static_veh_hz_aggregated_all_pairs = parsing_results["df_static_veh_hz_aggregated_all_pairs"]
    df_moving_veh_hz_aggregated_all_pairs = parsing_results["df_moving_veh_hz_aggregated_all_pairs"]
    df_outlier = parsing_results["df_outlier"]
    static_veh = parsing_results["static_veh"]
    moving_veh = parsing_results["moving_veh"]
    df_static_veh_all_pairs = parsing_results["df_static_veh_all_pairs"]
    df_moving_veh_all_pairs = parsing_results["df_moving_veh_all_pairs"]
    moving_ground_truth_df = parsing_results["moving_ground_truth_df"]
    
    ######################################################
    # Plotting individual tests
    ######################################################
    print("plotting: " + raw_name)
    figure = plt.figure(figsize=(16, 9), dpi=150)
    figure_resample = plt.figure(figsize=(16, 9), dpi=150)
    if "moving" in raw_name.split("-v2-")[0]:
        titlename = "Moving Test - " + raw_name.split("-v2-")[-1]
        figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
    else:
        titlename = "Virtual Moving Test - " + raw_name.split("-v2-")[-1]
        figure.suptitle(titlename, fontsize='x-large', fontweight='bold')
    
    ######################################################
    ########## Original Results ##########
    ######################################################
    
    plot_time_series_dist(  figure=figure,
                            arrange_spec=411,
                            static_veh_df=df_static_veh_hz_aggregated_all_pairs,
                            moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                            static_veh=static_veh,
                            moving_veh=moving_veh,
                            df_outlier=df_outlier,
                            surveyed_static_ground_truth_value=None,
                            moving_ground_truth_df=moving_ground_truth_df)

    plot_upd_rate(  figure=figure,
                    arrange_spec=412,
                    static_veh_df=df_static_veh_hz_aggregated_all_pairs,
                    moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                    static_veh=static_veh,
                    moving_veh=moving_veh,
                    moving_ground_truth_df=moving_ground_truth_df
                    )

    # Instant Speed UWB Strict
    # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
    plot_time_series_speed( figure=figure, 
                            arrange_spec=413, 
                            static_veh_df=df_static_veh_hz_aggregated_all_pairs, 
                            moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                            static_veh=static_veh,
                            moving_veh=moving_veh,
                            moving_ground_truth_df=moving_ground_truth_df)
    
    plot_real_time_moving_errors(figure=figure, 
                                 arrange_spec=414, 
                                 static_veh_df=df_static_veh_hz_aggregated_all_pairs, 
                                 moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                                 static_veh=static_veh,
                                 moving_veh=moving_veh,
                                 moving_ground_truth_df=moving_ground_truth_df)
    
    ######################################################
    ########## RESAMPLED RESULTS ##########
    ######################################################
    
    titlename = titlename + "-Resampled"
    figure_resample.suptitle(titlename, fontsize='x-large', fontweight='bold')
    plot_time_series_dist(  figure=figure_resample,
                            arrange_spec=411,
                            static_veh_df=df_static_veh_hz_aggregated_all_pairs,
                            moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                            static_veh=static_veh,
                            moving_veh=moving_veh,
                            df_outlier=df_outlier,
                            surveyed_static_ground_truth_value=None,
                            moving_ground_truth_df=moving_ground_truth_df,
                            resample=True)

    plot_upd_rate(  figure=figure_resample,
                    arrange_spec=412,
                    static_veh_df=df_static_veh_hz_aggregated_all_pairs,
                    moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                    static_veh=static_veh,
                    moving_veh=moving_veh,
                    moving_ground_truth_df=moving_ground_truth_df,
                    resample=True)

    # Instant Speed UWB Strict
    # Calculate UWB Measured Instant Speed by Vehicle's Master with Each Slave to Range
    plot_time_series_speed( figure=figure_resample, 
                            arrange_spec=413, 
                            static_veh_df=df_static_veh_hz_aggregated_all_pairs, 
                            moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                            static_veh=static_veh,
                            moving_veh=moving_veh,
                            moving_ground_truth_df=moving_ground_truth_df,
                            resample=True)
    
    plot_real_time_moving_errors(figure=figure_resample, 
                                 arrange_spec=414, 
                                 static_veh_df=df_static_veh_hz_aggregated_all_pairs, 
                                 moving_veh_df=df_moving_veh_hz_aggregated_all_pairs,
                                 static_veh=static_veh,
                                 moving_veh=moving_veh,
                                 moving_ground_truth_df=moving_ground_truth_df, 
                                 resample=True)
    
    figure.tight_layout(pad=1.0)
    figure_resample.tight_layout(pad=1.0)
    plt.show()


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
    test_6_east = all_test_names[11]
    moving_tests[test_6_east] = parse_single_test_data(test_raw_name_file_map[test_6_east]["B"], "Moving Test", test_preset_map, 
                                                    test_raw_name_file_map[test_6_east]["ground_truth"])
    plot_single_test_data(test_6_east, moving_tests, 'Moving Test', test_preset_map)