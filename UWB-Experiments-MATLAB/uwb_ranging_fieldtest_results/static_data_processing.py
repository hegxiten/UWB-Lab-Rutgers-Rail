import os, re
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import math

from utils import offset_calculate, post_process_new_data_entry, post_process_convert_distance_unit_to_mm

from utils import same_track_side_longitudinal_dist, oppo_track_side_longitudinal_dist,post_process_device_side_code_to_str

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NSUWB/")
EPOCH_DT = datetime(1970,1,1)

pd.set_option('display.float_format', lambda x: '%.5f' % x)
STATIC_RAW_SURVEY_RESULTS = {
    "static-v2-1": "",
    "static-v2-2": "6002mm",
    "static-v2-3": "7800mm",
    "static-v2-4": "9541mm",
    "static-v2-5": "37FT",
    "static-v2-6": "42FT11.5IN",
    "static-v2-7": "49FT1.5IN", 
    "static-v2-8": "56FT7IN",
    "static-v2-9": "62FT3.5IN", 
    "static-v2-10": "71FT3.75IN",
    "static-v2-11": "80FT10.5IN",
    "static-v2-12": "89FT10IN",
    "static-v2-13": "98FT0.25IN",
    "static-v2-14": "106FT7.5IN",
    "static-v2-15": "114FT7.5IN",
    "static-v2-16": "146FT1IN",
}
CALIBRATED_CAM_TO_V2B = -6400.8
MASTER_PAIRS = {
    '0C1A': '1912', 
    '88BA': '45BA',
    '9B0F': '8D38',
    '111C': '0B8A'
    }

def tabularize_individual_tests(filename, Surveyed_dist=None):
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

    # Only read file from processed log.
    if "processed_log" in filename:
        df = read_df_from_processed_input(filename, t_offset, Surveyed_dist)
        # Dataframe to save into csv file
        converted_filename = "PostProcessed_" + Path(filename).stem + ".csv"
        df.to_csv(os.path.join(_dirname, converted_filename), date_format="%Y-%m-%d %H:%M:%S.%5f", index=False)
    else:
        print("Invalid filename. Please make sure to input a valid log file.")

    # Final processed dataframe is printed. Additonal data analysis can be done using it.
    print(df)
    print("====================================")



def read_df_from_processed_input(filename, t_offset, Surveyed_dist=None):
    # Initial column names are declared
    df = pd.DataFrame(
        columns=[
            'Datetime Normalized',
            
            'Initiating Master', 
            'Master Side', 
            'Reporting Master X (mm)',
            'Reporting Master Y (mm)',
            'Reporting Master Z (mm)',
            'Initiating Vehicle', 
            'Initiating Vehicle Length (mm)', 
            
            'Reporting Slave',
            'Slave Side',
            'Reporting Slave X (mm)',
            'Reporting Slave Y (mm)',
            'Reporting Slave Z (mm)',
            'Reporting Vehicle', 
            'Reporting Vehicle Length (mm)',            
            
            'Correction Distance (mm)',
            'UWB Distance (mm)', 
            'Surveyed Distance (mm)', 
            'Timestamp Norm (s)', 
            'Timestamp Local (s)', 
            ])
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
                Initiating_master = master_info.get('master_id')

                data_processed_str = data_processed_raw.split("end reporting decoded foreign slaves: ")[-1].replace("\'", "\"")
                data_processed_list = json.loads(data_processed_str)

                Adjusted_dist = float('inf')
                if master_info.get("id_assoc") == 2:
                    if master_info.get("side_master") == 1: # Reporting Master is at B End (a.k.a. 88BA)
                        assert master_info.get("master_id") == "88BA"
                        for slave in data_processed_list:
                            Reporting_slave = slave.get('slave_id')
                            UWB_dist = slave.get('dist_to')
                            if slave.get("id_assoc") == master_info.get("id_assoc"):
                                continue
                            if MASTER_PAIRS.get(Initiating_master) == Reporting_slave:
                                assert Reporting_slave == "45BA"
                                side_to_side_dist = same_track_side_longitudinal_dist(master_info, slave) \
                                    - master_info["x_master"] - slave['x_slave']
                                # No Vehicle Length Adjustment
                                Adjusted_dist = side_to_side_dist
                            elif MASTER_PAIRS.get(Initiating_master) != Reporting_slave:
                                assert Reporting_slave == "0B8A"
                                side_to_side_dist = oppo_track_side_longitudinal_dist(master_info, slave) \
                                    - master_info["x_master"] + slave['x_slave'] - slave['vehicle_length_slave']
                                # Subtract Foreign Vehicle Length
                                Adjusted_dist = side_to_side_dist
                            master_side, slave_side = post_process_device_side_code_to_str(master_info, slave)
                            df.loc[i] = post_process_new_data_entry(Surveyed_dist, master_info, Timestamp_norm, Timestamp_local, Adjusted_dist, slave, Reporting_slave, UWB_dist, master_side, slave_side)
                            i = i + 1
                    
                    elif master_info.get("side_master") == 2: # Reporting Master is at A End (a.k.a. 111C)
                        assert master_info.get("master_id") == "111C"
                        for slave in data_processed_list:
                            Reporting_slave = slave.get('slave_id')
                            UWB_dist = slave.get('dist_to')
                            if slave.get("id_assoc") == master_info.get("id_assoc"):
                                continue
                            if MASTER_PAIRS.get(Initiating_master) == Reporting_slave:
                                assert Reporting_slave == "0B8A"
                                side_to_side_dist = same_track_side_longitudinal_dist(master_info, slave) \
                                    + master_info['x_master'] + slave['x_slave'] \
                                    - master_info['vehicle_length_master'] - slave['vehicle_length_slave']
                                # Subtract Both Vehicle Length
                                Adjusted_dist = side_to_side_dist
                            elif MASTER_PAIRS.get(Initiating_master) != Reporting_slave:
                                assert Reporting_slave == "45BA"
                                side_to_side_dist = oppo_track_side_longitudinal_dist(master_info, slave) \
                                    + master_info['x_master'] - slave['x_slave'] \
                                    - master_info['vehicle_length_master']
                                # Subtract Self Vehicle Length
                                Adjusted_dist = side_to_side_dist
                            master_side, slave_side = post_process_device_side_code_to_str(master_info, slave)
                            df.loc[i] = post_process_new_data_entry(Surveyed_dist, master_info, Timestamp_norm, Timestamp_local, Adjusted_dist, slave, Reporting_slave, UWB_dist, master_side, slave_side)
                            i = i + 1

                elif master_info.get("id_assoc") == 1:
                    if master_info.get("side_master") == 1: # Reporting Master is at B End (a.k.a. 9B0F)
                        assert master_info.get("master_id") == "9B0F"
                        for slave in data_processed_list:
                            Reporting_slave = slave.get('slave_id')
                            UWB_dist = slave.get('dist_to')
                            if slave.get("id_assoc") == master_info.get("id_assoc"):
                                continue
                            if MASTER_PAIRS.get(Initiating_master) == Reporting_slave:
                                assert Reporting_slave == "8D38"
                                side_to_side_dist = same_track_side_longitudinal_dist(master_info, slave) \
                                    + master_info['x_master'] + slave['x_slave'] \
                                    - master_info['vehicle_length_master'] - slave['vehicle_length_slave']
                                # Subtract Both Vehicle Length
                                Adjusted_dist = side_to_side_dist
                            elif MASTER_PAIRS.get(Initiating_master) != Reporting_slave:
                                assert Reporting_slave == "1912"
                                side_to_side_dist = oppo_track_side_longitudinal_dist(master_info, slave) \
                                    + master_info['x_master'] - slave['x_slave'] \
                                    - master_info['vehicle_length_master']
                                # Subtract Self Vehicle Length
                                Adjusted_dist = side_to_side_dist
                            master_side, slave_side = post_process_device_side_code_to_str(master_info, slave)
                            df.loc[i] = post_process_new_data_entry(Surveyed_dist, master_info, Timestamp_norm, Timestamp_local, Adjusted_dist, slave, Reporting_slave, UWB_dist, master_side, slave_side)
                            i = i + 1
                    
                    elif master_info.get("side_master") == 2: # Reporting Master is at A End (a.k.a. 0C1A)
                        assert master_info.get("master_id") == "0C1A"
                        for slave in data_processed_list:
                            Reporting_slave = slave.get('slave_id')
                            UWB_dist = slave.get('dist_to')
                            if slave.get("id_assoc") == master_info.get("id_assoc"):
                                continue
                            if MASTER_PAIRS.get(Initiating_master) == Reporting_slave:
                                assert Reporting_slave == "1912"
                                side_to_side_dist = same_track_side_longitudinal_dist(master_info, slave) \
                                    - master_info["x_master"] - slave['x_slave']
                                # No Vehicle Length Adjustment
                                Adjusted_dist = side_to_side_dist
                            elif MASTER_PAIRS.get(Initiating_master) != Reporting_slave:
                                assert Reporting_slave == "8D38"
                                side_to_side_dist = oppo_track_side_longitudinal_dist(master_info, slave) \
                                    - master_info["x_master"] + slave['x_slave'] - slave['vehicle_length_slave']
                                # Subtract Foreign Vehicle Length
                                Adjusted_dist = side_to_side_dist
                            master_side, slave_side = post_process_device_side_code_to_str(master_info, slave)
                            df.loc[i] = post_process_new_data_entry(Surveyed_dist, master_info, Timestamp_norm, Timestamp_local, Adjusted_dist, slave, Reporting_slave, UWB_dist, master_side, slave_side)
                            i = i + 1
    
    # Calculate the instant reporting frequency in slices 
    # (make sure it calculates in pairs)
    slices_designated_slave = []
    for master_id in df['Initiating Master'].unique():
        for slave_id in df['Reporting Slave'].unique():
            sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)]
            sliced_by_designated_slave["Instant Update Rate (Hz)"] = (1 / sliced_by_designated_slave['Timestamp Norm (s)'].diff())
            slices_designated_slave.append(sliced_by_designated_slave)

    if slices_designated_slave:
        concat_df = pd.concat(slices_designated_slave, ignore_index=True)
        concat_df.sort_values(['Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True], inplace=True, ignore_index=True)
        return concat_df
    else:
        return df

def get_test_files_and_survey(test_major_name, vehicle):
    test_fname_list, test_ground_truth = [], []
    if test_major_name == "Static Test":
        if "V2" in vehicle: 
            # Moving vehicle, ballast regulator, separated files, 
            _dir_name = 'V2-THINKPADP52-BallastRegulator-Static'
        elif "V1" in vehicle:
            # Moving vehicle, tamper, single file
            _dir_name = 'V1-THINKPADT430-Tamper-Static'
        file_dir = os.path.join(ROOT_DIR, test_major_name, _dir_name)
        for test in os.listdir(file_dir):
            cur_dir = os.path.join(file_dir, test)
            for f in os.listdir(cur_dir):
                if "user-processed_log.log" in f:
                    _dirname = os.path.dirname(os.path.join(cur_dir, f))
                    test_fname_list.append(os.path.join(_dirname, f))
                    surveyed_dist = float('nan')
                    for key, value in STATIC_RAW_SURVEY_RESULTS.items():
                        if key in cur_dir:
                            surveyed_dist = float(post_process_convert_distance_unit_to_mm(value))
                    test_ground_truth.append(surveyed_dist)
    return test_fname_list, test_ground_truth


if __name__ == "__main__":
    test_list, static_test_ground_truth = get_test_files_and_survey("Static Test", "V2")
    for i in range(len(test_list)):
        tabularize_individual_tests(test_list[i], static_test_ground_truth[i])
    
    # test_list, static_test_ground_truth = get_test_files_and_survey("Static Test", "V1")
    # for i in range(len(test_list)):
    #     tabularize_individual_tests(test_list[i], static_test_ground_truth[i])
