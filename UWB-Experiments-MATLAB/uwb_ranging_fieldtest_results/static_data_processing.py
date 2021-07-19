import os, re
import json

from datetime import datetime
from synchronize_computers import offset_calculate
import pandas as pd

ROOT_DIR = os.path.join("C:/Users/wangz/OneDrive/University_RU/NS Field Testing Compiled Raw Data_LocalProcessing/")
EPOCH_DT = datetime(1970,1,1)

RAW_SURVEY_RESULTS = {
    "static-v2-1": "7002mm",
    "static-v2-2": "7800mm",
    "static-v2-3": "9541mm",
    "static-v2-4": "37FT",
    "static-v2-5": "42FT11.5IN",
    "static-v2-6": "49FT1.5IN", 
    "static-v2-7": "56FT7IN",
    "static-v2-8": "62FT3.5IN", 
    "static-v2-9": "71FT3.75IN",
    "static-v2-10": "80FT10.5IN",
    "static-v2-11": "89FT10IN",
    "static-v2-12": "98FT0.25IN",
    "static-v2-13": "106FT7.5IN",
    "static-v2-14": "114FT7.5IN",
    "static-v2-15": "146FT1IN",
    "static-v2-16": ""
}

def tabularize_individual_tests(filename, Surveyed_dist):
    #Declare the path of the filename you want to use
    assert "processed_log" in filename
    print("processing {}...".format(filename))

    T430_offset, P52_offset = offset_calculate() 

    #Identify the PC for time offset
    if "T430" in filename:
        t_offset = T430_offset
    elif "P52" in filename:
        t_offset = P52_offset

    #Identify the vehicle
    if "v1" in filename or "V1" in filename:
        Vehicle = 1
    elif "v2" in filename or "V2" in filename:
        Vehicle = 2
    elif "v3" in filename or "V3" in filename:
        Vehicle = 3
    #Identify the end
    if "data-A" in filename:
        Endside = "A"
    elif "data-B" in filename:
        Endside = "B"


    #Initial values are declared
    df = pd.DataFrame(
        columns=[
            'Timestamp Norm (s)', 
            'Vehicle', 'Endside', 
            'Initiating Master', 
            'Reporting Slave',
            'UWB Distance (mm)', 
            'Surveyed Distance (mm)', 
            'Timestamp Local (s)', 
            'Epoch'
            ])
    i = 0
    master_pairs = {'0C1A': '1912', '88BA': '45BA'}
    #File is processed depending on whether it is a raw file or a processed file.
    if "processed_log" in filename:
        with open(filename, "r") as file:
            while True:
                #Data is read line by line
                data_uwb_raw = file.readline()
                if not data_uwb_raw:
                    break
                #Ignores the first line
                if "UTC TIME REFERENCE" in data_uwb_raw:
                    continue
                #Parses the data into variables and cleans it
                elif "uwb data:" in data_uwb_raw:
                    # Placeholder for raw UWB data.
                    # Only extract the master ID for the dataline for now. 
                    data_no_processing_str = data_uwb_raw.split("end reporting uwb data: ")[-1].replace("\'", "\"")
                    data_no_processing_dict = json.loads(data_no_processing_str)
                    master_info = data_no_processing_dict.get('masterInfoPos')

                    # Analyze the processed data for now. 
                    data_processed_raw = file.readline()
                    datetime_re_match = re.search(   
                        "(?<=[[])"
                        "(?P<raw_tstmp>[0-9]{4}[\-]"
                        "[0-9]{2}[\-][0-9]{2}\s[0-9]{2}[\:][0-9]{2}[\:][0-9]{2}"
                        "[\.][0-9]{6})(?<!\s[local])", data_processed_raw)

                    datetime_str = datetime_re_match.group("raw_tstmp")
                    datetime_raw = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')
                    datetime_norm = datetime_raw + t_offset

                    # TODO: UTC not considered. 
                    Timestamp_norm = (datetime_norm - EPOCH_DT).total_seconds()
                    Timestamp_local = (datetime_raw - EPOCH_DT).total_seconds()
                    Vehicle = Vehicle
                    Endside = Endside
                    Initiating_master = master_info.get('master_id')
                    Reporting_slave = master_pairs.get(Initiating_master)

                    data_processed_str = data_processed_raw.split("end reporting decoded foreign slaves: ")[-1].replace("\'", "\"")
                    data_processed_list = json.loads(data_processed_str)
                    
                    Distance = -1
                    for slave in data_processed_list:
                        if slave.get('slave_id') == Reporting_slave:
                            Distance = slave.get('dist_to')
                        else:
                            break
                    if Distance == -1:
                        continue
                    df.loc[i] = [Timestamp_norm] + [Vehicle] + [Endside] + [Initiating_master] + [Reporting_slave] + [Distance] + [Surveyed_dist] + [Timestamp_local] + [repr(EPOCH_DT)]
                    i = i + 1

    elif "raw_log" in filename:
        print("Please select a processed log file")    
    else:
        print("Invalid filename. Please make sure to input a valid log file.")

    #Dataframe is converted into csv file
    _dirname = os.path.dirname(filename)
    if "processed_log" in filename:
        converted_filename = "PostProcessed_" + filename[len(filename)-49:len(filename)-4] + ".csv"
        df.to_csv(os.path.join(_dirname, converted_filename), index=False)
    elif "raw_log" in filename:
        converted_filename = "PostProcessed_" + filename[len(filename)-38:len(filename)-4] + ".csv"
        df.to_csv(os.path.join(_dirname, converted_filename), index=False)

    #Final processed dataframe is printed. Additonal data analysis can be done using it.
    print(df)


def get_test_files_and_survey(test_major_name, vehicle):
    test_list, test_ground_truth = [], []
    if test_major_name == "Static Test":
        if "V2" in vehicle: 
            # Moving vehicle, ballast regulator, separated files, 
            # Side to be processed: B
            _dir_name = 'V2-THINKPADP52-BallastRegulator-Static'
            endside = "B"
        elif "V1" in vehicle:
            # Moving vehicle, tamper, single file
            # Side to be processed: A
            _dir_name = 'V1-THINKPADT430-Tamper-Static'
            endside = "A"
        file_dir = os.path.join(ROOT_DIR, test_major_name, _dir_name)
       
        for test in os.listdir(file_dir):
            cur_dir = os.path.join(file_dir, test)
            for f in os.listdir(cur_dir):
                if "data-{}-user-processed_log.log".format(endside) in f:
                    _dirname = os.path.dirname(os.path.join(cur_dir, f))
                    test_list.append(os.path.join(_dirname, f))
                    surveyed_dist = float('nan')
                    for key, value in RAW_SURVEY_RESULTS.items():
                        if key in cur_dir:
                            surveyed_dist = float(convert_distance_unit_to_mm(value))
                    test_ground_truth.append(surveyed_dist)
    return test_list, test_ground_truth
    

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
    test_list, static_test_ground_truth = get_test_files_and_survey("Static Test", "V2")
    for i in range(len(test_list)):
        tabularize_individual_tests(test_list[i], static_test_ground_truth[i])

