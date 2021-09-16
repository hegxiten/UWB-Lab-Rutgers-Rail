import os, re
import json
import numpy as np

from datetime import datetime
from static_data_processing import get_test_files_and_survey
import pandas as pd

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
EPOCH_DT = datetime(1970,1,1)

lump_sum_file_list, _ = get_test_files_and_survey("Static Test", "V1")
lump_sum_file = lump_sum_file_list[0]
lump_sum_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(lump_sum_file))[0] + ".csv"
lump_sum_csv = os.path.join(os.path.dirname(lump_sum_file), lump_sum_csv_base)

df_main = pd.read_csv(lump_sum_csv)

for test_file in get_test_files_and_survey("Static Test", "V2")[0]:
    _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
    df_test_post_processed = pd.read_csv(os.path.join(os.path.dirname(test_file), _test_csv_base), parse_dates=["Datetime Normalized"])
    # df_test_post_processed.set_index("Datetime Normalized", inplace=True)
    
    surveyed_dist = df_test_post_processed["Surveyed Distance (mm)"].unique()[0]
    # Slice the main (lump sum data) by the time values in the individual tests
    df_main_sliced = df_main[np.logical_and(
        df_main['Timestamp Norm (s)'] > df_test_post_processed["Timestamp Norm (s)"].min(),
        df_main['Timestamp Norm (s)'] < df_test_post_processed["Timestamp Norm (s)"].max()
        )].copy()
    df_main_sliced["Surveyed Distance (mm)"] = surveyed_dist
    _sliced_csv_base = "SlicedMain_" + _test_csv_base.split("PostProcessed_")[1]
    _sliced_csv_dir = os.path.join(os.path.dirname(test_file), _sliced_csv_base)
    df_main_sliced.to_csv(_sliced_csv_dir, date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)

    # Combine all and sort
    _integ = pd.concat([df_main_sliced, df_test_post_processed])
    _integ.sort_values(['Initiating Vehicle', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True], inplace=True, ignore_index=True)

    _integ_csv_base = "Integrated_" + _test_csv_base.split("PostProcessed_")[1]
    _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)
    _integ.to_csv(_integ_csv_dir, date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)