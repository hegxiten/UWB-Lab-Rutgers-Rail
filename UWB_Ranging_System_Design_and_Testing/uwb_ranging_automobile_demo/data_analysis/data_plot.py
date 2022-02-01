import os, sys, time, math
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt

import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter

TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


def parse_time_stamp(str_line):
    # test = "[2021-04-11 17:00:35.632219 local] A end reporting decoded foreign slaves: [{'slave_id': 'DB00', 'x_slave': 20, 'y_slave': 190, 'z_slave': 490, 'vehicle_length_slave': 3950, 'id_assoc': 1, 'side_slave': 1, 'dist_to': 4370}]"
    timestamp_str = str_line.split(']')[0][1:]
    timestamp_str = timestamp_str.split(' local')[0]
    timestp = datetime.strptime(timestamp_str, TIME_FORMAT)
    return timestp

def filtered_lines_by_time(filedir, start_time, stop_time):
    ret = []
    with open(filedir, "r") as f:
        for line in f.readlines():
            if start_time <= parse_time_stamp(line) <= stop_time:
                ret.append(line)
    return ret


if __name__ == "__main__":
    # watch video to determine the time slots to analyze
    first_slot_start = datetime.strptime("2021-04-11 17:30:57.000000", TIME_FORMAT)
    first_slot_stop  = datetime.strptime("2021-04-11 17:31:26.000000", TIME_FORMAT)

    second_slot_start = datetime.strptime("2021-04-11 17:33:03.000000", TIME_FORMAT)
    second_slot_stop  = datetime.strptime("2021-04-11 17:33:40.000000", TIME_FORMAT)



    script_dir = os.path.dirname(os.path.realpath('__file__')) #<-- absolute dir the script is in
    test_name = "20210411/"
    v1_test_id = "2021-04-11-17-00-20"
    v2_test_id = "2021-04-11-17-30-18"
    v1_dir = os.path.join(script_dir, '../' + test_name + '/v1')
    v2_dir = os.path.join(script_dir, '../' + test_name + '/v2')
    
    v1_uwb_files = [i for i in os.listdir(v1_dir) if v1_test_id in i and '.log' in i and 'uwb' in i]
    v2_uwb_files = [i for i in os.listdir(v2_dir) if v2_test_id in i and '.log' in i and 'uwb' in i]
    
    v1_raw_files = [i for i in os.listdir(v1_dir) if v1_test_id in i and '.log' in i and 'raw' in i]
    v2_raw_files = [i for i in os.listdir(v2_dir) if v2_test_id in i and '.log' in i and 'raw' in i]

    v1_uwb_files_full_dir = [os.path.join(v1_dir, i) for i in v1_uwb_files]
    v2_uwb_files_full_dir = [os.path.join(v2_dir, i) for i in v2_uwb_files]

    v1_raw_files_full_dir = [os.path.join(v1_dir, i) for i in v1_raw_files]
    v2_raw_files_full_dir = [os.path.join(v2_dir, i) for i in v2_raw_files]
    
    v1_B_end_master_id = 'D91E'
    v1_B_master_info_dict = {"x_master": 0, "y_master": -16, "z_master": 48}
    V2_B_master_info_dict = {"x_master": 89, "y_master": -41, "z_master": 125}
    v2_A_master_info_dict = {"x_master": 197, "y_master": -50, "z_master": 131}
    v1_B_end_master_uwb_file = [i for i in v1_uwb_files_full_dir if '-B-' in i and 'uwb' in i].pop(0)
    v2_B_end_master_uwb_file = [i for i in v2_uwb_files_full_dir if '-B-' in i and 'uwb' in i].pop(0)
    v2_A_end_master_uwb_file = [i for i in v2_uwb_files_full_dir if '-A-' in i and 'uwb' in i].pop(0)
    V1_B_end_slave_id = 'DB00'
    v2_A_end_slave_id = '8D2A'
    V2_B_end_slave_id = '1328'
    
    # --------------------------------------- FIRST SLOT V1B ---------------------------------------
    v1_B_end_filtered_results_first = filtered_lines_by_time(v1_B_end_master_uwb_file, first_slot_start, first_slot_stop)
    t_first_V1B, d_uwb_first_V1B, d_adjust_first_V1B = [], [], []
    for line in v1_B_end_filtered_results_first:
        if "decoded foreign slaves:" in line:
            t_first_V1B.append(parse_time_stamp(line).timestamp())
            slave_lists = eval(line.split("foreign slaves: ")[1])
            d_uwb_first_V1B.append(None)
            d_adjust_first_V1B.append(None)
            for slv in slave_lists:
                if slv.get('slave_id') == V2_B_end_slave_id:
                    d_uwb_first_V1B[-1] = slv['dist_to']
                    x_diff =   v1_B_master_info_dict["x_master"] + slv['x_slave']
                    y_diff = - v1_B_master_info_dict["y_master"] - slv['y_slave']
                    z_diff =   v1_B_master_info_dict["z_master"] - slv['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(slv["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        adjusted_dist = float("nan")
                    d_adjust_first_V1B[-1] = adjusted_dist
    
    # --------------------------------------- FIRST SLOT V2B ---------------------------------------
    v2_B_end_filtered_results_first = filtered_lines_by_time(v2_B_end_master_uwb_file, first_slot_start, first_slot_stop)
    t_first_V2B, d_uwb_first_V2B, d_adjust_first_V2B = [], [], []
    for line in v2_B_end_filtered_results_first:
        if "decoded foreign slaves:" in line:
            t_first_V2B.append(parse_time_stamp(line).timestamp())
            slave_lists = eval(line.split("foreign slaves: ")[1]) 
            d_uwb_first_V2B.append(None)
            d_adjust_first_V2B.append(None)
            for slv in slave_lists:
                if slv.get('slave_id') == V1_B_end_slave_id:
                    d_uwb_first_V2B[-1] = slv['dist_to']
                    x_diff =   V2_B_master_info_dict["x_master"] + slv['x_slave']
                    y_diff = - V2_B_master_info_dict["y_master"] - slv['y_slave']
                    z_diff =   V2_B_master_info_dict["z_master"] - slv['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(slv["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        adjusted_dist = float("nan")
                    d_adjust_first_V2B[-1] = adjusted_dist

    # --------------------------------------- SECOND SLOT V1B ---------------------------------------
    v1_B_end_filtered_results_second = filtered_lines_by_time(v1_B_end_master_uwb_file, second_slot_start, second_slot_stop)
    t_second_V1B, d_uwb_second_V1B, d_adjust_second_V1B = [], [], []
    for line in v1_B_end_filtered_results_second:
        if "decoded foreign slaves:" in line:
            t_second_V1B.append(parse_time_stamp(line).timestamp())
            slave_lists = eval(line.split("foreign slaves: ")[1])
            d_uwb_second_V1B.append(None)
            d_adjust_second_V1B.append(None)
            for slv in slave_lists:
                if slv.get('slave_id') == v2_A_end_slave_id:
                    d_uwb_second_V1B[-1] = slv['dist_to']
                    x_diff =   v1_B_master_info_dict["x_master"] + slv['x_slave']
                    y_diff = - v1_B_master_info_dict["y_master"] - slv['y_slave']
                    z_diff =   v1_B_master_info_dict["z_master"] - slv['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(slv["dist_to"]**2 - z_diff**2 - y_diff**2) + x_diff)
                    except:
                        adjusted_dist = float("nan")
                    d_adjust_second_V1B[-1] = adjusted_dist

    # --------------------------------------- SECOND SLOT V2A ---------------------------------------
    v2_A_end_filtered_results_second = filtered_lines_by_time(v2_A_end_master_uwb_file, second_slot_start, second_slot_stop)
    t_second_V2A, d_uwb_second_V2A, d_adjust_second_V2A = [], [], []
    for line in v2_A_end_filtered_results_second:
        if "decoded foreign slaves:" in line:
            t_second_V2A.append(parse_time_stamp(line).timestamp())
            slave_lists = eval(line.split("foreign slaves: ")[1])
            d_uwb_second_V2A.append(None)
            d_adjust_second_V2A.append(None)
            for slv in slave_lists:
                if slv.get('slave_id') == V1_B_end_slave_id:
                    d_uwb_second_V2A[-1] = slv['dist_to']
                    x_diff =   v2_A_master_info_dict["x_master"] - slv['x_slave']
                    y_diff = - v2_A_master_info_dict["y_master"] + slv['y_slave']
                    z_diff =   v2_A_master_info_dict["z_master"] - slv['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(slv["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        adjusted_dist = float("nan")
                    d_adjust_second_V2A[-1] = adjusted_dist

    print(t_second_V2A, d_uwb_second_V2A, d_adjust_second_V2A)

    fig, ax = plt.subplots(2, 2)
    tfmt = mdates.DateFormatter('%H:%M:%S')

    N_first_V1B = len(t_first_V1B) 
    print(N_first_V1B)
    assert N_first_V1B == len(d_uwb_first_V1B) and N_first_V1B == len(d_adjust_first_V1B)
    xt_first_V1B = np.array(t_first_V1B)
    series_uwb_first_V1B = np.array(d_uwb_first_V1B).astype(np.double)
    s1mask_first_V1B = np.isfinite(series_uwb_first_V1B)
    series_adj_first_V1B = np.array(d_adjust_first_V1B).astype(np.double)
    s2mask_first_V1B = np.isfinite(series_adj_first_V1B)

    ax[0,0].plot([datetime.fromtimestamp(ts) for ts in xt_first_V1B[s1mask_first_V1B]], series_uwb_first_V1B[s1mask_first_V1B]/1000, linestyle='-', marker='o', label='Direct UWB Device Measurement, V1B')
    ax[0,0].plot([datetime.fromtimestamp(ts) for ts in xt_first_V1B[s2mask_first_V1B]], series_adj_first_V1B[s2mask_first_V1B]/1000, linestyle='-', marker='o', label='Adjusted Measurement, V1B')
    ax[0,0].xaxis.set_major_formatter(tfmt)
    ax[0,0].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax[0,0].set_xlabel('Time')
    ax[0,0].set_ylabel('Distance Measured in Meters')
    ax[0,0].legend()
    for tick in ax[0,0].get_xticklabels():
        tick.set_rotation(45)

    N_second_V1B = len(t_second_V1B) 
    print(N_second_V1B)
    assert N_second_V1B == len(d_uwb_second_V1B) and N_second_V1B == len(d_adjust_second_V1B)
    xt_second_V1B = np.array(t_second_V1B)
    series_uwb_second_V1B = np.array(d_uwb_second_V1B).astype(np.double)
    s1mask_second_V1B = np.isfinite(series_uwb_second_V1B)
    series_adj_second_V1B = np.array(d_adjust_second_V1B).astype(np.double)
    s2mask_second_V1B = np.isfinite(series_adj_second_V1B)

    ax[0,1].plot([datetime.fromtimestamp(ts) for ts in xt_second_V1B[s1mask_second_V1B]], series_uwb_second_V1B[s1mask_second_V1B]/1000, linestyle='-', marker='o', label='Direct UWB Device Measurement, V1B')
    ax[0,1].plot([datetime.fromtimestamp(ts) for ts in xt_second_V1B[s2mask_second_V1B]], series_adj_second_V1B[s2mask_second_V1B]/1000, linestyle='-', marker='o', label='Adjusted Measurement, V1B')
    ax[0,1].xaxis.set_major_formatter(tfmt)
    ax[0,1].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax[0,1].set_xlabel('Time')
    ax[0,1].set_ylabel('Distance Measured in Meters')
    ax[0,1].legend()
    for tick in ax[0,1].get_xticklabels():
        tick.set_rotation(45)

    N_first_V2B = len(t_first_V2B) 
    print(N_first_V2B)
    assert N_first_V2B == len(d_uwb_first_V2B) and N_first_V2B == len(d_adjust_first_V2B)
    xt_first_V2B = np.array(t_first_V2B)
    series_uwb_first_V2B = np.array(d_uwb_first_V2B).astype(np.double)
    s1mask_first_V2B = np.isfinite(series_uwb_first_V2B)
    series_adj_first_V2B = np.array(d_adjust_first_V2B).astype(np.double)
    s2mask_first_V2B = np.isfinite(series_adj_first_V2B)

    ax[1,0].plot([datetime.fromtimestamp(ts) for ts in xt_first_V2B[s1mask_first_V2B]], series_uwb_first_V2B[s1mask_first_V2B]/1000, linestyle='-', marker='o', label='Direct UWB Device Measurement, V2B')
    ax[1,0].plot([datetime.fromtimestamp(ts) for ts in xt_first_V2B[s2mask_first_V2B]], series_adj_first_V2B[s2mask_first_V2B]/1000, linestyle='-', marker='o', label='Adjusted Measurement, V2B')
    ax[1,0].xaxis.set_major_formatter(tfmt)
    ax[1,0].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax[1,0].set_xlabel('Time')
    ax[1,0].set_ylabel('Distance Measured in Meters')
    ax[1,0].legend()
    for tick in ax[1,0].get_xticklabels():
        tick.set_rotation(45)

    N_second_V2A = len(t_second_V2A) 
    print(N_second_V2A)
    assert N_second_V2A == len(d_uwb_second_V2A) and N_second_V2A == len(d_adjust_second_V2A)
    xt_second_V2A = np.array(t_second_V2A)
    series_uwb_second_V2A = np.array(d_uwb_second_V2A).astype(np.double)
    s1mask_second_V2A = np.isfinite(series_uwb_second_V2A)
    series_adj_second_V2A = np.array(d_adjust_second_V2A).astype(np.double)
    s2mask_second_V2A = np.isfinite(series_adj_second_V2A)

    ax[1,1].plot([datetime.fromtimestamp(ts) for ts in xt_second_V2A[s1mask_second_V2A]], series_uwb_second_V2A[s1mask_second_V2A]/1000, linestyle='-', marker='o', label='Direct UWB Device Measurement, V2A')
    ax[1,1].plot([datetime.fromtimestamp(ts) for ts in xt_second_V2A[s2mask_second_V2A]], series_adj_second_V2A[s2mask_second_V2A]/1000, linestyle='-', marker='o', label='Adjusted Measurement, V2A')
    ax[1,1].xaxis.set_major_formatter(tfmt)
    ax[1,1].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax[1,1].set_xlabel('Time')
    ax[1,1].set_ylabel('Distance Measured in Meters')
    ax[1,1].legend()
    for tick in ax[1,1].get_xticklabels():
        tick.set_rotation(45)


    plt.show()