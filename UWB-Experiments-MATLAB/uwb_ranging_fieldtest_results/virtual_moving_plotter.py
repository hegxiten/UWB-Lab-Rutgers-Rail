import os, re
import json
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter

from datetime import datetime
import math
import pandas as pd

from virtual_moving_data_processing import get_moving_test_data_and_timestamp

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")


def plot_time_series_ranging(fdir, ground_truth_df):
    df = pd.read_csv(fdir, index_col=[0])
    df_v1, df_v2 = df[df["Vehicle"] == 3], df[df["Vehicle"] == 2]
    
    # Plotting
    figure = plt.figure(figsize=(16, 9), dpi=150)
    ax1 = figure.add_subplot(2,2,1)
    ax1.plot(pd.to_datetime(df_v1["Timestamp Norm (s)"],unit='s'), df_v1["UWB Distance (mm)"], label="V1")
    ax1.plot(pd.to_datetime(df_v2["Timestamp Norm (s)"],unit='s'), df_v2["UWB Distance (mm)"], label="V2")
    ax1.plot(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'), ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"], label="Ground Truth",  marker='*',markerfacecolor = 'r')
    print(pd.to_datetime(ground_truth_df["Time UNIX Norm (s)"],unit='s'))
    ax1.set_title("Time Series Distance (mm)")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Distance (mm)")
    ax1.legend()
    
    ax2 = figure.add_subplot(2,2,2)
    ax2.hist(df_v1["UWB Distance (mm)"], bins=20)
    ax2.set_title("Hist - Vehicle 1 (Static)")
    ax2.set_xlabel("Distance (mm)")
    ax2.set_ylabel("Counts")
    ax2.legend()
    
    ax3 = figure.add_subplot(2,2,3)
    ax3.hist(df_v2["UWB Distance (mm)"], bins=20)
    ax3.set_title("Hist - Vehicle 2 (Mover)")
    ax3.set_xlabel("Distance (mm)")
    ax3.set_ylabel("Counts")
    ax3.legend()
    
    ax4 = figure.add_subplot(2,2,4)
    ax4.plot(pd.to_datetime(df_v1["Timestamp Norm (s)"],unit='s'), df_v1["Update Rate (Hz)"], label="V1")
    ax4.plot(pd.to_datetime(df_v2["Timestamp Norm (s)"],unit='s'), df_v2["Update Rate (Hz)"], label="V2")
    ax4.set_title("Time Series Update Rate (Hz)")
    ax4.set_xlabel("Time")
    ax4.set_ylabel("UWB Reporting Frequency (Hz)")
    ax4.legend()

    # Saving to directory
    _fig_dir = os.path.join(os.path.dirname(fdir), os.path.splitext(os.path.basename(fdir))[0] + ".png")
    # plt.savefig(_fig_dir)
    plt.show()


if __name__ == "__main__":
    test_file_list, ground_truth_list = get_moving_test_data_and_timestamp("Moving Test 1 (V2V)", "V2")
    assert(len(test_file_list) == len(ground_truth_list))
    for i in range(len(test_file_list)):
        test_file, ground_truth = test_file_list[i], ground_truth_list[i]
        _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
        _integ_csv_base = "Integrated_" + _test_csv_base.split("PostProcessed_")[1]
        _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)
        df = pd.read_csv(_integ_csv_dir)
        
        plot_time_series_ranging(_integ_csv_dir, ground_truth)

