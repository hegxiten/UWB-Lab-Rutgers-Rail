import os, re
import json
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter

from datetime import datetime
import math
import pandas as pd

from static_data_processing import get_test_files_and_survey

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NS Field Testing Compiled Raw Data_LocalProcessing/")


def plot_time_series_ranging(fdir):
    df = pd.read_csv(fdir, index_col=[0])
    df_v1, df_v2 = df[df["Vehicle"] == 1], df[df["Vehicle"] == 2]
    surveyed_dist = df_v2.loc[0, "Surveyed Distance (mm)"]
    
    # Plotting
    figure = plt.figure(figsize=(16, 9), dpi=150)
    ax1 = figure.add_subplot(2,2,1)
    ax1.plot(pd.to_datetime(df_v1["Timestamp Norm (s)"],unit='s'), df_v1["UWB Distance (mm)"], label="V1")
    ax1.plot(pd.to_datetime(df_v2["Timestamp Norm (s)"],unit='s'), df_v2["UWB Distance (mm)"], label="V2")
    ax1.plot(pd.to_datetime(df_v2["Timestamp Norm (s)"],unit='s'), [surveyed_dist] * df_v2["Timestamp Norm (s)"].shape[0], label="Surveyed")
    ax1.set_title("Time Series Distance (mm)")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Distance (mm)")
    ax1.legend()
    
    ax2 = figure.add_subplot(2,2,2)
    ax2.hist(df_v1["UWB Distance (mm)"], bins=20)
    ax2.axvline(x=surveyed_dist, color='r', linestyle='dashed', linewidth=2, label="Surveyed")
    ax2.set_title("Hist - Vehicle 1 (Static)")
    ax2.set_xlabel("Distance (mm)")
    ax2.set_ylabel("Counts")
    ax2.legend()
    
    ax3 = figure.add_subplot(2,2,3)
    ax3.hist(df_v2["UWB Distance (mm)"], bins=20)
    ax3.axvline(x=surveyed_dist, color='r', linestyle='dashed', linewidth=2, label="Surveyed")
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
    plt.savefig(_fig_dir)


if __name__ == "__main__":

    for test_file in get_test_files_and_survey("Static Test", "V2")[0]:
        _test_csv_base = "PostProcessed_" + os.path.splitext(os.path.basename(test_file))[0] + ".csv"
        _integ_csv_base = "Integrated_" + _test_csv_base.split("PostProcessed_")[1]
        _integ_csv_dir = os.path.join(os.path.dirname(test_file), _integ_csv_base)
        df = pd.read_csv(_integ_csv_dir)
        
        plot_time_series_ranging(_integ_csv_dir)

