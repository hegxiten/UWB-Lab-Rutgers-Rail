import os, re
import json
import numpy as np

from datetime import datetime
from static_data_processing import get_test_files_and_survey
import pandas as pd

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
EPOCH_DT = datetime(1970,1,1)

lump_sum_file_list, _ = get_test_files_and_survey("Static Test", "V1")
for f in lump_sum_file_list:
    if "-data-A-user-processed_log.log" in f:
        lump_sum_file_A = f
    elif "-data-B-user-processed_log.log" in f:
        lump_sum_file_B = f

lump_sum_csv_A_base = "PostProcessed_" + os.path.splitext(os.path.basename(lump_sum_file_A))[0] + ".csv"
lump_sum_csv_B_base = "PostProcessed_" + os.path.splitext(os.path.basename(lump_sum_file_B))[0] + ".csv"
lump_sum_csv_A = os.path.join(os.path.dirname(lump_sum_file_A), lump_sum_csv_A_base)
lump_sum_csv_B = os.path.join(os.path.dirname(lump_sum_file_B), lump_sum_csv_B_base)

df_lump_sum_A = pd.read_csv(lump_sum_csv_A)
df_lump_sum_B = pd.read_csv(lump_sum_csv_B)

surveyed_dist = None

for test_file in get_test_files_and_survey("Static Test", "V2")[0]:
    
    # Clean original files if any
    for f in os.listdir(os.path.join(os.path.dirname(test_file))):
        if "Integrated_" in f or "SlicedMain_" in f:
            os.remove(os.path.join(os.path.dirname(test_file), f))
    _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
    df_test_post_processed = pd.read_csv(os.path.join(os.path.dirname(test_file), _test_csv_base), parse_dates=["Datetime Normalized"])
    # df_test_post_processed.set_index("Datetime Normalized", inplace=True)
    surveyed_dist = df_test_post_processed["Surveyed Distance (mm)"].unique()
    if surveyed_dist.size != 0:
        surveyed_dist = surveyed_dist[0]
    
    # Slice the B main (lump sum data B) by the time values in the individual tests
    df_lump_sum_B_sliced = df_lump_sum_B[np.logical_and(
        df_lump_sum_B['Timestamp Norm (s)'] > df_test_post_processed["Timestamp Norm (s)"].min(),
        df_lump_sum_B['Timestamp Norm (s)'] < df_test_post_processed["Timestamp Norm (s)"].max()
        )].copy()
    df_lump_sum_B_sliced["Surveyed Distance (mm)"] = surveyed_dist
    # Slice the A main (lump sum data A) by the time values in the individual tests
    df_lump_sum_A_sliced = df_lump_sum_A[np.logical_and(
        df_lump_sum_A['Timestamp Norm (s)'] > df_test_post_processed["Timestamp Norm (s)"].min(),
        df_lump_sum_A['Timestamp Norm (s)'] < df_test_post_processed["Timestamp Norm (s)"].max()
        )].copy()
    df_lump_sum_A_sliced["Surveyed Distance (mm)"] = surveyed_dist

    _sliced_csv_B_base = "SlicedMain_B-" + _test_csv_base.split("PostProcessed_")[1]
    _sliced_csv_B_dir = os.path.join(os.path.dirname(test_file), _sliced_csv_B_base)
    df_lump_sum_B_sliced.to_csv(_sliced_csv_B_dir, date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)

    _sliced_csv_A_base = "SlicedMain_A-" + _test_csv_base.split("PostProcessed_")[1]
    _sliced_csv_A_dir = os.path.join(os.path.dirname(test_file), _sliced_csv_A_base)
    df_lump_sum_A_sliced.to_csv(_sliced_csv_A_dir, date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)

    _sliced_csv_AB_base = "SlicedMain_AB-" + _test_csv_base.split("PostProcessed_")[1]
    _sliced_csv_AB_dir =  os.path.join(os.path.dirname(test_file), _sliced_csv_AB_base)
    _sliced_df_main_AB = pd.concat([df_lump_sum_A_sliced, df_lump_sum_B_sliced])
    _sliced_df_main_AB.to_csv(_sliced_csv_AB_dir, date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)

    # Combine all B and sort
    _integ = pd.concat([df_lump_sum_B_sliced, df_lump_sum_A_sliced, df_test_post_processed])
    _integ.sort_values(['Initiating Vehicle', 'Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True, True], inplace=True, ignore_index=True)

    _integ_csv_base = "Integrated_AB-" + _test_csv_base.split("PostProcessed_")[1]
    _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)
    _integ.to_csv(_integ_csv_dir, date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)

    # Make a final Have-it-all Combo
    df_combo = pd.DataFrame()
    for f in os.listdir(os.path.join(os.path.dirname(test_file))):
        if "Integrated_AB" in f and "data-A-user-processed_log" in f:
            _moving_a_end_integ = pd.read_csv(os.path.join(os.path.dirname(test_file), f), parse_dates=["Datetime Normalized"])
            df_combo = pd.concat([df_combo, _moving_a_end_integ])
        if "Integrated_AB" in f and "data-B-user-processed_log" in f:
            _moving_b_end_integ = pd.read_csv(os.path.join(os.path.dirname(test_file), f), parse_dates=["Datetime Normalized"])
            df_combo = pd.concat([df_combo, _moving_b_end_integ])
    df_combo.sort_values(['Initiating Vehicle', 'Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True, True], inplace=True, ignore_index=True)
    _combo_csv_base = "Integrated_ABAB_COMBO-" + _test_csv_base.split("PostProcessed_")[1].split("-data-")[0] + ".csv"
    _combo_csv_dir = os.path.join(os.path.dirname(test_file), _combo_csv_base)
    df_combo.to_csv(_combo_csv_dir, date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)
