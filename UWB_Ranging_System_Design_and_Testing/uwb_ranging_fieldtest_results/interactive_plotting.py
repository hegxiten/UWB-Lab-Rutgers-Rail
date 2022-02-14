import os, re
import json
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter
from matplotlib.widgets import Slider, Button, RadioButtons, CheckButtons

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

from collections import defaultdict

import warnings
warnings.filterwarnings("ignore")

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
CALIBRATED_CAM_TO_V2B = -6400.8
pd.set_option('display.float_format', lambda x: '%.5f' % x)
pd.set_option('display.max_columns', None)

RESAMPLE_RULE = "1S"
PLOTTING_DPI = 75
static_main_master = 'D91E'
static_focusing_slaves = ['1912', '8D38']
static_master_slave_mapping = { 'D91E': [static_focusing_slaves[0], static_focusing_slaves[1]],
                                '0090': [static_focusing_slaves[1], static_focusing_slaves[0]]}
moving_main_master = '88BA'
moving_focusing_slaves = ['DB00', '069B']
moving_master_slave_mapping = { '88BA': [moving_focusing_slaves[0], moving_focusing_slaves[1]],
                                '111C': [moving_focusing_slaves[1], moving_focusing_slaves[0]]}
STATIC_VEH, MOVING_VEH = 3, 2
VEH_NAME_MAP = {3: "static", 2: "moving"}
test_preset_map = defaultdict(dict)
test_preset_map['PLOTTING_DPI'] = PLOTTING_DPI
test_preset_map['STATIC_VEH'] = STATIC_VEH
test_preset_map['MOVING_VEH'] = MOVING_VEH
test_preset_map[STATIC_VEH]['master_slave_mapping'] = static_master_slave_mapping
test_preset_map[MOVING_VEH]['master_slave_mapping'] = moving_master_slave_mapping
test_preset_map[STATIC_VEH]['main_master'] = static_main_master
test_preset_map[MOVING_VEH]['main_master'] = moving_main_master
test_preset_map['dist_interval_size'] = 1000
#############################################
# if skip plotting any tests, list them here
skiptests = []
#############################################
all_test_files, ground_truth_list = post_process_get_moving_test_data_and_timestamp(ROOT_DIR, 
                                                                                    "Moving Test 2 (Virtual Vehicle)", 
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

virtual_moving_tests = {}
for test in all_test_names:
    virtual_moving_tests[test] = parse_single_test_data(test_raw_name_file_map[test]["B"],
                                                        "Virtual Moving Test",
                                                        test_preset_map,
                                                        test_raw_name_file_map[test]["ground_truth"])

# Global Statistics
static_stats_list_pairwise = []
static_stats_list_aggregated = []
moving_stats_list_pairwise = []
moving_stats_list_aggregated = []

# Combination of All, Indexed by Time
list_df_time_idx_static = []
list_df_time_idx_moving = []

# Combination of All, Indexed by Ground Truth Distances
list_df_dist_idx_static = []
list_df_dist_idx_moving = []

# Combination of All, Indexed by Instance Speed by Markers
list_df_spd_idx_static = []
list_df_spd_idx_moving = []

for raw_name in all_test_names:
    parsing_results = virtual_moving_tests.get(raw_name)
    if not parsing_results:
        continue
    # Unpack dataframes
    df_outlier_overall = parsing_results["df_outlier_overall"]
    moving_ground_truth_df = parsing_results["moving_ground_truth_df"]
    for veh in parsing_results["vehicles"]:
        df_veh_time_idx = parsing_results[veh]["df_veh_time_idx"]
        df_veh_dist_idx = parsing_results[veh]["df_veh_dist_idx"]
        df_veh_spd_idx = parsing_results[veh]["df_veh_spd_idx"]
        veh_err_bins = parsing_results[veh]["veh_err_bins"]
        df_stats_pairwise = parsing_results[veh]['df_stats_pairwise']
        df_stats_aggregated = parsing_results[veh]['df_stats_aggregated']
        if veh == STATIC_VEH:
            df_static_time_idx, static_bins = df_veh_time_idx, veh_err_bins
            list_df_time_idx_static.append(df_veh_time_idx)
            list_df_dist_idx_static.append(df_veh_dist_idx)
            list_df_spd_idx_static.append(df_veh_spd_idx)
            static_stats_list_pairwise.append(df_stats_pairwise)
            static_stats_list_aggregated.append(df_stats_aggregated)
        elif veh == MOVING_VEH:
            df_moving_time_idx, moving_bins = df_veh_time_idx, veh_err_bins
            list_df_time_idx_moving.append(df_veh_time_idx)
            list_df_dist_idx_moving.append(df_veh_dist_idx)
            list_df_spd_idx_moving.append(df_veh_spd_idx)
            moving_stats_list_pairwise.append(df_stats_pairwise)
            moving_stats_list_aggregated.append(df_stats_aggregated)
    
df_all_static_stats_pairwise = pd.concat(static_stats_list_pairwise, ignore_index=True)
df_all_static_stats_aggregated = pd.concat(static_stats_list_aggregated, ignore_index=True)
df_all_static_stats_aggregated["Main Pair Counts"] = np.array(
    df_all_static_stats_pairwise[(df_all_static_stats_pairwise["Is Main Master"]==True) & 
                                             (df_all_static_stats_pairwise["Is Main Slave"]==True)
                                            ]["Reporting Counts"])
df_all_moving_stats_pairwise = pd.concat(moving_stats_list_pairwise, ignore_index=True)
df_all_moving_stats_aggregated = pd.concat(moving_stats_list_aggregated, ignore_index=True)
df_all_moving_stats_aggregated["Main Pair Counts"] = np.array(
    df_all_moving_stats_pairwise[(df_all_moving_stats_pairwise["Is Main Master"]==True) & 
                                             (df_all_moving_stats_pairwise["Is Main Slave"]==True)
                                            ]["Reporting Counts"])

df_all_static_stats_dist_idx = pd.concat(list_df_dist_idx_static)
df_all_static_stats_time_idx = pd.concat(list_df_time_idx_static)
df_all_static_stats_spd_idx = pd.concat(list_df_spd_idx_static)
df_all_moving_stats_dist_idx = pd.concat(list_df_dist_idx_moving)
df_all_moving_stats_time_idx = pd.concat(list_df_time_idx_moving)
df_all_moving_stats_spd_idx = pd.concat(list_df_spd_idx_moving)

figure1 = plt.figure(figsize=(16, 9), dpi=75)
ax1 = figure1.add_subplot(19,11,(1,205))
i = 0
scatters_map = defaultdict(dict)
raw_data_map = defaultdict(dict)
scatters = []
for veh_df in [df_all_static_stats_time_idx, df_all_moving_stats_time_idx]:
    v, = veh_df['Initiating Vehicle'].unique()
    for master in veh_df['Initiating Master'].unique():
        m_veh_df = veh_df[veh_df['Initiating Master'] == master]
        for slave in m_veh_df['Reporting Slave'].unique():
            ms_veh_df = m_veh_df[(m_veh_df['Reporting Slave'] == slave)].copy()
            _scatter_ = ax1.scatter(    ms_veh_df['Surveyed Distance (mm)'], 
                                        ms_veh_df['Correction Distance (mm)'] - ms_veh_df['Surveyed Distance (mm)'], 
                                        alpha=0.3, marker="o", color="C{}".format(i),
                                        label="Vehicle {}'s Master {} against Slave {}".format(v, master, slave))
            scatters_map[(master, slave)] = _scatter_
            raw_data_map[(master, slave)] = ms_veh_df
            scatters.append(_scatter_)
            i += 1


def create_offset_slider(figure, slider_pos, offset_item, min_offset, max_offset, scatters_map, raw_data_map, device):
    offset_slider_axes = figure.add_subplot(19,11, slider_pos)
    offset_slider = Slider(
        ax=offset_slider_axes,
        label="{} {} Offset".format(device, offset_item),
        valmin=min_offset,
        valmax=max_offset,
        valinit=0
    )
    def update_offset(val):
        for pair, _scatter_ in scatters_map.items():
            _df = raw_data_map[pair]
            _changed_df = offset_virtual_test_measurements(_df, **{ offset_item: offset_slider.val, 'device': device}).copy()
            _offsets = np.c_[_changed_df['Surveyed Distance (mm)'], _changed_df['Correction Distance (mm)'] - _changed_df['Surveyed Distance (mm)']]
            _scatter_.set_offsets(_offsets)
            figure.canvas.draw_idle()
    offset_slider.on_changed(update_offset)
    return offset_slider


v3_length_offset_slider = create_offset_slider( figure=figure1, 
                                                slider_pos=(140, 143), 
                                                offset_item='V3L', 
                                                min_offset=-5000, 
                                                max_offset=5000, 
                                                scatters_map=scatters_map, 
                                                raw_data_map=raw_data_map,
                                                device='')
                                                
v2_length_offset_slider = create_offset_slider( figure=figure1, 
                                                slider_pos=(151, 154), 
                                                offset_item='V2L', 
                                                min_offset=-5000, 
                                                max_offset=5000, 
                                                scatters_map=scatters_map, 
                                                raw_data_map=raw_data_map,
                                                device='')

x_offset_slider_D91E = create_offset_slider(figure=figure1, 
                                            slider_pos=(8,11), 
                                            offset_item='X', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='D91E')

y_offset_slider_D91E = create_offset_slider(figure=figure1, 
                                            slider_pos=(19,22), 
                                            offset_item='Y', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='D91E')

z_offset_slider_D91E = create_offset_slider(figure=figure1, 
                                            slider_pos=(30,33), 
                                            offset_item='Z', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='D91E')

x_offset_slider_DB00 = create_offset_slider(figure=figure1, 
                                            slider_pos=(41,44), 
                                            offset_item='X', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='DB00')

y_offset_slider_DB00 = create_offset_slider(figure=figure1, 
                                            slider_pos=(52,55), 
                                            offset_item='Y', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='DB00')

z_offset_slider_DB00 = create_offset_slider(figure=figure1, 
                                            slider_pos=(63,66), 
                                            offset_item='Z', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='DB00')

x_offset_slider_069B = create_offset_slider(figure=figure1, 
                                            slider_pos=(74,77), 
                                            offset_item='X', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='069B')

y_offset_slider_069B = create_offset_slider(figure=figure1, 
                                            slider_pos=(85,88), 
                                            offset_item='Y', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='069B')

z_offset_slider_069B = create_offset_slider(figure=figure1, 
                                            slider_pos=(96,99), 
                                            offset_item='Z', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='069B')

x_offset_slider_0090 = create_offset_slider(figure=figure1, 
                                            slider_pos=(107,110), 
                                            offset_item='X', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='0090')

y_offset_slider_0090 = create_offset_slider(figure=figure1, 
                                            slider_pos=(118,121), 
                                            offset_item='Y', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='0090')

z_offset_slider_0090 = create_offset_slider(figure=figure1, 
                                            slider_pos=(129,132), 
                                            offset_item='Z', 
                                            min_offset=-2000, 
                                            max_offset=2000, 
                                            scatters_map=scatters_map, 
                                            raw_data_map=raw_data_map,
                                            device='0090')



# Create a `matplotlib.widgets.Button` to reset the sliders to initial values.
def reset(event):
    v3_length_offset_slider.reset()
    v2_length_offset_slider.reset()    
    x_offset_slider_D91E.reset()
    y_offset_slider_D91E.reset()
    z_offset_slider_D91E.reset()
    x_offset_slider_DB00.reset()
    y_offset_slider_DB00.reset()
    z_offset_slider_DB00.reset()
    x_offset_slider_069B.reset()
    y_offset_slider_069B.reset()
    z_offset_slider_069B.reset()
    x_offset_slider_0090.reset()
    y_offset_slider_0090.reset()
    z_offset_slider_0090.reset()

resetax = plt.axes([0.8, 0.025, 0.1, 0.04])
button = Button(resetax, 'Reset', hovercolor='0.975')
button.on_clicked(reset)

def checkbox_visibility_action(label):
    index = labels.index(label)
    scatters[index].set_visible(not scatters[index].get_visible())
    plt.draw()

checkbox_ax = figure1.add_subplot(19,11,(162,209))
labels = [str(line.get_label()) for line in scatters]
visibility = [line.get_visible() for line in scatters]
check_btn = CheckButtons(checkbox_ax, labels, visibility)
check_btn.on_clicked(checkbox_visibility_action)
ax1.legend()
plt.show()