import os, re
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import math

from utils import offset_calculate

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
EPOCH_DT = datetime(1970,1,1)

pd.set_option('display.float_format', lambda x: '%.5f' % x)

CALIBRATED_CAM_TO_V2B = -6400.8
MASTER_PAIRS = {'0C1A': '1912', '88BA': '45BA'}

def tabularize_individual_tests(filename):
    # Declare the path of the filename you want to use
    print("processing {}...".format(filename))
    _dirname = os.path.dirname(filename)

    T430_offset, P52_offset = offset_calculate() 

    # Identify the PC for time offset
    if "T430" in filename:
        t_offset = T430_offset
    elif "P52" in filename:
        t_offset = P52_offset

    # Identify the vehicle
    if "v1" in filename or "V1" in filename:
        Vehicle = 1
    elif "v2" in filename or "V2" in filename:
        Vehicle = 2
    elif "v3" in filename or "V3" in filename:
        Vehicle = 3
    # Identify the end
    if "data-A" in filename:
        Endside = "A"
    elif "data-B" in filename:
        Endside = "B"

    # File is processed depending on whether it is a raw file or a processed file.
    if "processed_log" in filename:
        df = read_df_from_processed_input(filename, t_offset, Vehicle, Endside)
        # Dataframe is converted into csv file
        converted_filename = "PostProcessed_" + Path(filename).stem + ".csv"
        df.to_csv(os.path.join(_dirname, converted_filename), index=False)
    else:
        print("Invalid filename. Please make sure to input a valid log file.")

    # Final processed dataframe is printed. Additonal data analysis can be done using it.
    print(df)

def read_df_from_processed_input(filename, t_offset, Vehicle, Endside):
    # Initial values are declared
    df = pd.DataFrame(
        columns=[
            'Datetime Normalized',
            'Vehicle', 
            'Endside', 
            'Initiating Master', 
            'Reporting Slave',
            'Correction Distance (mm)',
            'UWB Distance (mm)', 
            'Timestamp Norm (s)', 
            'Timestamp Local (s)', 
            ])
    i = 0
    with open(filename, "r") as input_f:
        i = 0
        while True:
            # Data is read line by line
            data_uwb_raw = input_f.readline()
            if not data_uwb_raw:
                break
            # Ignores the first line
            if "UTC TIME REFERENCE" in data_uwb_raw:
                continue
            # Parses the data into variables and cleans it
            elif "uwb data:" in data_uwb_raw:
                # Only extract the master ID for the dataline for now. 
                data_no_processing_str = data_uwb_raw.split("end reporting uwb data: ")[-1].replace("\'", "\"")
                data_no_processing_dict = json.loads(data_no_processing_str)
                master_info = data_no_processing_dict.get('masterInfoPos')

                # Analyze the processed data for now. Read the next line.
                data_processed_raw = input_f.readline()
                datetime_re_match = re.search(   
                    "(?<=[[])"
                    "(?P<raw_tstmp>[0-9]{4}[\-]"
                    "[0-9]{2}[\-][0-9]{2}\s[0-9]{2}[\:][0-9]{2}[\:][0-9]{2}"
                    "[\.][0-9]{6})(?<!\s[local])", data_processed_raw)

                datetime_str = datetime_re_match.group("raw_tstmp")
                datetime_raw = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')
                datetime_norm = datetime_raw + t_offset

                # NOTE: UTC not considered. 
                Timestamp_norm = (datetime_norm - EPOCH_DT).total_seconds()
                Timestamp_local = (datetime_raw - EPOCH_DT).total_seconds()
                Vehicle = Vehicle
                Endside = Endside
                Initiating_master = master_info.get('master_id')
                Reporting_slave = MASTER_PAIRS.get(Initiating_master)

                data_processed_str = data_processed_raw.split("end reporting decoded foreign slaves: ")[-1].replace("\'", "\"")
                data_processed_list = json.loads(data_processed_str)
                
                Adjusted_dist = float('inf')
                for slave in data_processed_list:
                    Reporting_slave = slave.get('slave_id')
                    # TODO: here we temporarily ignored the usability of the opposite side slave of the foreign vehicle. (09/15/2021)
                    if MASTER_PAIRS.get(Initiating_master) == Reporting_slave:
                        UWB_dist = slave.get('dist_to')
                        if master_info.get("side_master") == 1: # Reporting Master is at B End, a.k.a. 88BA 
                            if slave["side_slave"] == 2: # self.B v.s. others.A_slave
                                x_diff =   master_info["x_master"] + slave['x_slave']
                                y_diff =   master_info["y_master"] + slave['y_slave']
                                z_diff =   master_info["z_master"] - slave['z_slave']
                                try:
                                    side_to_side_dist = int(math.sqrt(slave["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                                except ValueError:
                                    side_to_side_dist = float("nan")
                                Adjusted_dist = min(side_to_side_dist, Adjusted_dist)
                            elif slave["side_slave"] == 1: # self.B v.s. others.B_slave
                                x_diff =   master_info["x_master"] - slave['x_slave']
                                y_diff =   master_info["y_master"] - slave['y_slave']
                                z_diff =   master_info["z_master"] - slave['z_slave']
                                try:
                                    side_to_side_dist = int(math.sqrt(slave["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                                except ValueError:
                                    side_to_side_dist = float("nan")
                                Adjusted_dist = min(side_to_side_dist, Adjusted_dist)
                        elif master_info.get("side_master") == 2: # Reporting Master is at A End, a.k.a. 0C1A 
                            if slave["side_slave"] == 2: # self.A v.s. others.A_slave
                                x_diff =   master_info["x_master"] - slave['x_slave']
                                y_diff =   master_info["y_master"] - slave['y_slave']
                                z_diff =   master_info["z_master"] - slave['z_slave']
                                try:
                                    side_to_side_dist = int(math.sqrt(slave["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                                except ValueError:
                                    side_to_side_dist = float("nan")
                                Adjusted_dist = min(side_to_side_dist, Adjusted_dist)
                            elif slave["side_slave"] == 1: # self.A v.s. others.B_slave
                                x_diff =   master_info["x_master"] + slave['x_slave']
                                y_diff =   master_info["y_master"] + slave['y_slave']
                                z_diff =   master_info["z_master"] - slave['z_slave']
                                try:
                                    side_to_side_dist = int(math.sqrt(slave["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                                except ValueError:
                                    side_to_side_dist = float("nan")
                                Adjusted_dist = min(side_to_side_dist, Adjusted_dist)
                        df.loc[i] = [pd.to_datetime(Timestamp_norm, unit='s')] \
                            + [Vehicle] + [Endside] \
                            + [Initiating_master] + [Reporting_slave] \
                            + [Adjusted_dist] \
                            + [UWB_dist] \
                            + [Timestamp_norm] + [Timestamp_local]
                        i = i + 1
    return df

    
def get_moving_test_data_and_timestamp(test_major_name, vehicle):
    test_list, instant_location_list_local = [], []
    if test_major_name == "Moving Test 1 (V2V)":
        if "V2" in vehicle: 
            # Moving vehicle, ballast regulator, separated files, 
            # Side to be processed: B
            _dir_name = 'V2-THINKPADP52-BallastRegulator-Moving-1'
            endside = "B"
        elif "V1" in vehicle:
            # Moving vehicle, tamper, single file
            # Side to be processed: A
            _dir_name = 'V1-THINKPADT430-Tamper-Moving-1'
            endside = "A"
    elif test_major_name == "Moving Test 2 (Virtual Vehicle)":
        if "V2" in vehicle: 
            # Moving vehicle, ballast regulator, separated files, 
            # Side to be processed: B
            _dir_name = 'V2-THINKPADT430-BallastRegulator-Moving-2'
            endside = "B"
        elif "V3" in vehicle:
            # Moving vehicle, tamper, single file
            # Side to be processed: A
            _dir_name = 'V3-THINKPADP52-Virtual-Moving-2'
            endside = "B"
    file_dir = os.path.join(ROOT_DIR, test_major_name, _dir_name)
    
    for test in os.listdir(file_dir):
        cur_dir = os.path.join(file_dir, test)
        for f in os.listdir(cur_dir):
            if "data-{}-user-processed_log.log".format(endside) in f:
                _test_file_name = os.path.join(cur_dir, f)
                _dirname = os.path.dirname(_test_file_name)
                test_list.append(_test_file_name)
            if "-vid-data.csv" in f:
                surveyed_time_locations_by_vid = get_instant_locations_local_time(os.path.join(cur_dir, f))
                instant_location_list_local.append(surveyed_time_locations_by_vid)
    return test_list, instant_location_list_local


def get_instant_locations_local_time(_vid_data_file):
    # Get the timestamps with the markers (and referred marker locations) in key value pairs (hashmaps)
    # This shall be the local timestamps without/pre clock sync

    df_test = pd.read_csv(_vid_data_file, header=None, skiprows=2, names=["Time UNIX Norm (s)", "Marker Name", "Camera Dist to Static Veh (CPLR, mm)"])
    T430_offset, P52_offset = offset_calculate()
    # Identify the PC for time offset
    if "T430" in _vid_data_file:
        t_offset = T430_offset
    elif "P52" in _vid_data_file:
        t_offset = P52_offset
    
    # Process the time difference (offset)
    df_test["Time UNIX Norm (s)"] = df_test["Time UNIX Norm (s)"] + t_offset.total_seconds()
    # Process the real bumper-to-bumper distance
    df_test["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"] = df_test["Camera Dist to Static Veh (CPLR, mm)"] + CALIBRATED_CAM_TO_V2B
    return df_test


def convert_distance_unit_to_mm(string_distance):
    if "mm" in string_distance:
        return float(string_distance.split('mm')[0])
    
    # If not in mm
    if "FT" in string_distance:
        _ft = float(string_distance.split('FT')[0])
        _dist = _ft * 304.8
        if "IN" in string_distance:
            _in = float(string_distance.split('FT')[1].split("IN")[0])
            _dist += _in * 25.4
        return round(_dist, 1)
    elif "IN" in string_distance:
        # Less than one ft
        _in = float(string_distance.split('IN')[0])
        _dist = _in * 25.4
        return round(_dist, 1)
    return float('nan')

if __name__ == "__main__":
    # test_list, ground_truth = get_moving_test_data_and_timestamp("Moving Test 1 (V2V)", "V1")
    # for i in range(len(test_list)):
    #     tabularize_individual_tests(test_list[i])

    test_list, ground_truth = get_moving_test_data_and_timestamp("Moving Test 1 (V2V)", "V2")
    for i in range(len(test_list)):
        tabularize_individual_tests(test_list[i])