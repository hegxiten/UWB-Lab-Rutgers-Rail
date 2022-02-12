from datetime import datetime
import math
import pandas as pd
import numpy as np
from scipy import optimize
import os
import re

MAX_REPORTING_RATE_PER_VEHICLE = 40 # Hz
MIN_REPORTING_INTERVAL = 0.1        # Sec
ROLLING_WINDOW = 10
RESAMPLE_RULE = '1S'

def segments_fit(X, Y, count):
    xmin = X.min()
    xmax = X.max()

    seg = np.full(count - 1, (xmax - xmin) / count)

    px_init = np.r_[np.r_[xmin, seg].cumsum(), xmax]
    py_init = np.array([Y[np.abs(X - x) < (xmax - xmin) * 0.01].mean() for x in px_init])
    
    def helper_separate_1d_to_2d(p):
        seg = p[:count - 1]
        py = p[count - 1:]
        px = np.r_[np.r_[xmin, seg].cumsum(), xmax]
        return px, py

    def err(p):
        px, py = helper_separate_1d_to_2d(p)
        Y2 = np.interp(X, px, py)
        return np.mean((Y - Y2)**2)
    r = optimize.minimize(err, x0=np.r_[seg, py_init], method='Nelder-Mead')
    return helper_separate_1d_to_2d(r.x)

def uwb_dist_outlier_identify(df, threshold=5000, segments=5):
    px, py = segments_fit(df['Timestamp Norm (s)'], df['Correction Distance (mm)'], segments)
    px, py = px[~np.isnan(py)], py[~np.isnan(py)]
    X, Y = df['Timestamp Norm (s)'], df['Correction Distance (mm)']
    assert px.size == py.size
    if px.size != 0:
        Y2 = np.interp(X, px, py)
        df_outlier = df[np.abs(Y2 - Y) >  threshold]
        df_cleaned = df[np.abs(Y2 - Y) <=  threshold]
        return df_cleaned, df_outlier
    else:
        return df, df.drop(df.index)

def update_rate_by_strict_pairs(df):
    slices_designated_slave = []
    for test in df["Test Name"].unique():
        for veh in df["Initiating Vehicle"].unique():
            for master_id in df['Initiating Master'].unique():
                for slave_id in df['Reporting Slave'].unique():
                        sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) 
                                                        & (df['Initiating Master'] == master_id)
                                                        & (df['Initiating Vehicle'] == veh) 
                                                        & (df['Test Name'] == test) ]
                        sliced_by_designated_slave["Instant Update Rate (Hz)"] = (1 / sliced_by_designated_slave['Timestamp Norm (s)'].diff().clip(MIN_REPORTING_INTERVAL))
                        slices_designated_slave.append(sliced_by_designated_slave)
    if slices_designated_slave:
        df = pd.concat(slices_designated_slave)
        df.sort_values( ['Timestamp Norm (s)'], ascending=[True], inplace=True)
        df["Aggregated Update Rate (Hz)"] = ((ROLLING_WINDOW - 1) / df["Timestamp Norm (s)"].rolling(ROLLING_WINDOW).apply(lambda x: x[-1] - x[0])).clip(upper=MAX_REPORTING_RATE_PER_VEHICLE)
        df.sort_values(['Timestamp Norm (s)', 'Initiating Vehicle', 'Reporting Slave'], 
                    ascending=[True, True, True], 
                    inplace=True)
    return df

def instant_spd_by_strict_pairs(df):
    slices_uwb_spd_strict_pair = []
    for test in df["Test Name"].unique():
        for veh in df["Initiating Vehicle"].unique():
            for master_id in df['Initiating Master'].unique():
                for slave_id in df['Reporting Slave'].unique():
                    sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) 
                                                    & (df['Initiating Master'] == master_id)
                                                    & (df['Initiating Vehicle'] == veh) 
                                                    & (df['Test Name'] == test) ]
                    _dist_diff = sliced_by_designated_slave["Correction Distance (mm)"].diff().fillna(0.)
                    _time_diff = sliced_by_designated_slave["Timestamp Norm (s)"].diff().fillna(0.)
                    spd_mph = (_dist_diff / _time_diff) * 0.00223694
                    spd_mph = spd_mph.to_frame('UWB Measured Instant Speed - Strict Pair (mph)')
                    sliced_by_designated_slave['UWB Measured Instant Speed - Strict Pair (mph)'] = spd_mph['UWB Measured Instant Speed - Strict Pair (mph)']
                    slices_uwb_spd_strict_pair.append(sliced_by_designated_slave)
    if slices_uwb_spd_strict_pair:
        df = pd.concat(slices_uwb_spd_strict_pair)
        df.sort_values(['Initiating Master', 'Reporting Slave', 'Timestamp Norm (s)'], ascending=[True, True, True], inplace=True)
        df["Aggregated Measured Speed (mph)"] = df["Correction Distance (mm)"].rolling(ROLLING_WINDOW).apply(lambda x: x[-1] - x[0]) \
            / (df["Timestamp Norm (s)"].rolling(ROLLING_WINDOW).max() - df["Timestamp Norm (s)"].rolling(ROLLING_WINDOW).min()) * 0.00223694
        df.sort_values(['Timestamp Norm (s)', 'Initiating Vehicle', 'Reporting Slave'], 
                        ascending=[True, True, True], 
                        inplace=True)
        return df
    else:
        return df


def generate_stats_pairwise(veh_df, veh, df_with_overall_time, master_slave_mapping, main_master, raw_name):
    stats_list = []
    # pairwise stats
    if df_with_overall_time == None:
        df_with_overall_time = veh_df
    time_stamp_lim = get_time_stamp_lim(veh_df, df_with_overall_time_duration=df_with_overall_time)
    for master_id in master_slave_mapping.keys():
        for slave_id in master_slave_mapping[master_id]:
            df_pairwise_sliced = veh_df[(veh_df["Initiating Master"] == master_id) & (veh_df["Reporting Slave"] == slave_id)]
            pairwise_stats_map = {}
            pairwise_stats_map['Test Name'] = raw_name
            pairwise_stats_map['Operation Duration'] = (time_stamp_lim[1] - time_stamp_lim[0]).total_seconds()
            pairwise_stats_map['Initiating Vehicle'] = veh
            pairwise_stats_map['Initiating Master'] = master_id
            pairwise_stats_map['Is Main Master'] = True if master_id == main_master else False
            pairwise_stats_map['Reporting Slave'] = slave_id
            pairwise_stats_map['Is Main Slave'] = True if master_slave_mapping[master_id][0] == slave_id else False
            pairwise_stats_map['Is Aggregated'] = False
            if df_pairwise_sliced.empty or df_pairwise_sliced["Correction Distance (mm)"].isnull().all():
                pairwise_stats_map['Downtime Periods'] = [time_stamp_lim]
                pairwise_stats_map['Downtime Duration'] = (time_stamp_lim[1] - time_stamp_lim[0]).total_seconds()
                pairwise_stats_map['Reporting Counts'] = len(df_pairwise_sliced.index)
                stats_list.append(pairwise_stats_map)
                continue
            if len(df_pairwise_sliced["Surveyed Distance (mm)"].unique()) == 1:
                pairwise_stats_map['Static Ground Truth (mm)'] = df_pairwise_sliced["Surveyed Distance (mm)"].get(0, float('nan'))
            else:
                pairwise_stats_map['Static Ground Truth (mm)'] = float('nan')
            pairwise_stats_map['Average Measurement (mm)'] = df_pairwise_sliced["Correction Distance (mm)"].mean()
            pairwise_stats_map['Average Measurement Error (mm)'] = (df_pairwise_sliced['Correction Distance (mm)'] - df_pairwise_sliced['Surveyed Distance (mm)']).mean()
            pairwise_stats_map['STD (mm)'] = (df_pairwise_sliced['Correction Distance (mm)'] - df_pairwise_sliced['Surveyed Distance (mm)']).std()
            pairwise_stats_map['Operation Duration'] = (time_stamp_lim[1] - time_stamp_lim[0]).total_seconds()
            pairwise_stats_map['Reporting Counts'] = len(df_pairwise_sliced.index)
            pairwise_stats_map['Downtime Periods'] = get_nan_slices_indices(df_pairwise_sliced, veh, time_stamp_lim)
            pairwise_stats_map['Downtime Duration'] = sum([(_stopt - _startt).total_seconds()
                                                              for [_startt, _stopt] in 
                                                              get_nan_slices_indices(df_pairwise_sliced.resample(rule=RESAMPLE_RULE).mean(), 
                                                                                     veh, 
                                                                                     time_stamp_lim)])
            pairwise_stats_map['Test Start Time'] = veh_df['Test Start Time'].unique()[0]
            pairwise_stats_map['First Report Time'] = veh_df.index.tolist()[0]
            stats_list.append(pairwise_stats_map)
    return pd.DataFrame(stats_list)

def generate_stats_aggregated(veh_df, veh, df_with_overall_time, raw_name):
    # aggregated stats
    time_stamp_lim = get_time_stamp_lim(veh_df, df_with_overall_time_duration=df_with_overall_time)
    agg_stats_map = {}
    agg_stats_map['Test Name'] = raw_name
    agg_stats_map['Initiating Vehicle'] = veh
    agg_stats_map['Is Aggregated'] = True
    if len(veh_df["Surveyed Distance (mm)"].unique()) == 1:
        agg_stats_map['Static Ground Truth (mm)'] = veh_df["Surveyed Distance (mm)"].get(0, float('nan'))
    else:
        agg_stats_map['Static Ground Truth (mm)'] = float('nan')
    agg_stats_map['Average Measurement (mm)'] = veh_df["Correction Distance (mm)"].mean()
    agg_stats_map['Average Measurement Error (mm)'] = (veh_df['Correction Distance (mm)'] - veh_df['Surveyed Distance (mm)']).mean()
    agg_stats_map['STD (mm)'] = (veh_df['Correction Distance (mm)'] - veh_df['Surveyed Distance (mm)']).std()
    agg_stats_map['Reporting Counts'] = len(veh_df.index)
    agg_stats_map['Operation Duration'] = (time_stamp_lim[1] - time_stamp_lim[0]).total_seconds()
    agg_stats_map['Downtime Periods'] = get_nan_slices_indices(veh_df, veh, time_stamp_lim)
    agg_stats_map['Downtime Duration'] = sum([(x[1] - x[0]).total_seconds()
                                            for x in 
                                            get_nan_slices_indices(veh_df.resample(rule=RESAMPLE_RULE).mean(), 
                                                                    veh, 
                                                                    time_stamp_lim)
                                            if len(x) == 2])
    agg_stats_map['Test Start Time'] = veh_df['Test Start Time'].unique()[0]
    agg_stats_map['First Report Time'] = veh_df.index.tolist()[0]
    return pd.DataFrame([agg_stats_map])


def interpolate_ground_truth(veh_df, moving_ground_truth_df=None):
    if moving_ground_truth_df is None:
        moving_ground_truth_df = veh_df[veh_df["Surveyed Distance (mm)"].notnull()]
        moving_ground_truth_df = moving_ground_truth_df[~moving_ground_truth_df.index.duplicated()]
        _temp_df_survey_interpolate = pd.DataFrame(index=pd.concat([veh_df, moving_ground_truth_df]).index).sort_index()
        _temp_df_survey_interpolate = _temp_df_survey_interpolate[~_temp_df_survey_interpolate.index.duplicated()]
        _temp_df_survey_interpolate["Surveyed Distance (mm)"] = moving_ground_truth_df["Surveyed Distance (mm)"]
    else:
        moving_ground_truth_df = moving_ground_truth_df.set_index("Datetime Normalized")
        moving_ground_truth_df = moving_ground_truth_df[moving_ground_truth_df.index.notnull()]
        _temp_df_survey_interpolate = pd.DataFrame(index=pd.concat([veh_df, moving_ground_truth_df]).index.drop_duplicates()).sort_index()
        _temp_df_survey_interpolate["Surveyed Distance (mm)"] = moving_ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"]
    _temp_df_survey_interpolate = _temp_df_survey_interpolate.interpolate(limit_direction='both', limit_area='inside')
    veh_df["Surveyed Distance (mm)"] = _temp_df_survey_interpolate["Surveyed Distance (mm)"]
    dist_diff = veh_df["Surveyed Distance (mm)"].diff()
    time_diff = veh_df["Timestamp Norm (s)"].diff()
    instant_spd = (dist_diff / time_diff) * 0.00223694
    veh_df["Instant Speed by Marker (mph)"] = instant_spd
    veh_df["Error (mm)"] = veh_df["Correction Distance (mm)"] - veh_df["Surveyed Distance (mm)"]
    return veh_df

def get_time_stamp_lim(df, df_with_overall_time_duration=None):
    if df_with_overall_time_duration is None:
        time_stamp_lim = [df.index.min(),df.index.max()]
    else:
        try:
            min_time = min(df.index.min(), pd.to_datetime(df_with_overall_time_duration["Time UNIX Norm (s)"],unit='s').min())
            max_time = max(df.index.max(), pd.to_datetime(df_with_overall_time_duration["Time UNIX Norm (s)"],unit='s').max())
        except KeyError:
            min_time = min(df.index.min(), pd.to_datetime(df_with_overall_time_duration["Timestamp Norm (s)"],unit='s').min())
            max_time = max(df.index.max(), pd.to_datetime(df_with_overall_time_duration["Timestamp Norm (s)"],unit='s').max())
        time_stamp_lim = [min_time, max_time]
    return time_stamp_lim

def get_nan_slices_indices(df, veh, time_stamp_lim):
    slices = []
    _flag = False
    df = df.reset_index()
    for i in range(len(df['Aggregated Update Rate (Hz)'])):
        if not np.isnan(df.iloc[i]['Aggregated Update Rate (Hz)']):
            if _flag == True:
                if slices:
                    slices[-1].append(df.iloc[i]["Datetime Normalized"])
                    _flag = not _flag
        else:
            if _flag == False:
                if 0 < i-1 < len(df['Aggregated Update Rate (Hz)']) - 1:
                    slices.append([df.iloc[i-1]["Datetime Normalized"]])
                    _flag = not _flag
                if 0 == i:
                    slices.append([df.iloc[i]["Datetime Normalized"]])
                    _flag = not _flag
                if len(df['Aggregated Update Rate (Hz)']) - 1 == i:
                    if slices:
                        slices[-1].append(df.iloc[i]["Datetime Normalized"])
    if slices:
        _nan_start, _nan_stop = slices[0][0], df.iloc[-1]["Datetime Normalized"]
        if df[(df["Datetime Normalized"] < _nan_start) & (df["Datetime Normalized"] > df[df['Initiating Vehicle']==veh]["Datetime Normalized"].min())]['Aggregated Update Rate (Hz)'].size <= 1:
            slices.insert(0, [time_stamp_lim[0], _nan_start])
        if df[(df["Datetime Normalized"] > _nan_stop) & (df["Datetime Normalized"] < df[df['Initiating Vehicle']==veh]["Datetime Normalized"].max())]['Aggregated Update Rate (Hz)'].size <= 1:
            slices.append([_nan_stop, time_stamp_lim[1]])
    else:
        _nan_start, _nan_stop = df["Datetime Normalized"].min(), df["Datetime Normalized"].max()
        slices.insert(0, [min(time_stamp_lim[0], _nan_start), max(time_stamp_lim[0], _nan_start)])
        slices.append([min(time_stamp_lim[1], _nan_stop), max(time_stamp_lim[1], _nan_stop)])
    import itertools
    slices.sort()
    return list(k for k,_ in itertools.groupby(slices))


def parse_single_test_data(test_file, test_category, test_preset_map, ground_truth=None):
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
    df["Test Category"] = test_category
    df["Aggregated Update Rate (Hz)"] = np.nan
    df['UWB Measured Instant Speed - Strict Pair (mph)'] = np.nan
    df['Aggregated Measured Speed (mph)'] = np.nan
    df['Instant Speed by Marker (mph)'] = np.nan # Ground truth speed
    df['Test Start Time'] = pd.to_datetime(re.match('^[0-9]+[\-][0-9]+[\-][0-9]+[\-][0-9]+[\-][0-9]+[\-][0-9]+', 
                                                    raw_name)[0],
                                           format="%Y-%m-%d-%H-%M-%S")
    # Filter out distance measurement outliers
    df, df_outlier_overall = uwb_dist_outlier_identify(df, segments = 5)
    if df.empty:
        print(raw_name + " No Data")
        return None
    df.sort_values(['Timestamp Norm (s)', 'Initiating Vehicle', 'Reporting Slave'], 
                   ascending=[True, True, True], 
                   inplace=True)
    moving_ground_truth_df = ground_truth

    # Separting data frames by data-receiving vehicles 
    df = update_rate_by_strict_pairs(df)
    df = instant_spd_by_strict_pairs(df)
    
    ret = {}
    ret["vehicles"] = []
    ret["df_outlier_overall"] = df_outlier_overall
    ret["moving_ground_truth_df"] = moving_ground_truth_df
    binwidth = 20
    for veh in df['Initiating Vehicle'].unique():
        main_master = test_preset_map[veh]["main_master"]
        main_slave = test_preset_map[veh]['master_slave_mapping'][test_preset_map[veh]["main_master"]][0]
        ret["vehicles"].append(veh)
        ret[veh] = {}
        df_veh_time_idx = df[df['Initiating Vehicle'] == veh]
        veh_err_bins = None
        
        # Calculate Ground Truth Instant Speed
        df_veh_time_idx = interpolate_ground_truth(df_veh_time_idx, moving_ground_truth_df)
        df_veh_time_idx['Is Main Master'] = (df_veh_time_idx['Initiating Master'] == main_master)
        df_veh_time_idx['Is Main Slave'] = (df_veh_time_idx['Reporting Slave'] == main_slave)
        df_veh_dist_idx = df_veh_time_idx.set_index('Surveyed Distance (mm)')
        df_veh_spd_idx = df_veh_time_idx.set_index("Instant Speed by Marker (mph)")
        # Bins calculation for histograms
        veh_dist_bins = np.arange(  min(df_veh_time_idx["Correction Distance (mm)"]), 
                                    max(df_veh_time_idx["Correction Distance (mm)"]) + binwidth, 
                                    binwidth) \
                            if not df_veh_time_idx["Correction Distance (mm)"].empty else None
        veh_err_bins = np.arange(   min(df_veh_time_idx["Error (mm)"].dropna()), 
                                    max(df_veh_time_idx["Error (mm)"].dropna()) + binwidth, 
                                    binwidth) \
                            if not df_veh_time_idx["Error (mm)"].dropna().empty else None
            
        ret[veh]["df_veh_time_idx"] = df_veh_time_idx
        ret[veh]["df_veh_dist_idx"] = df_veh_dist_idx
        ret[veh]['df_veh_spd_idx'] = df_veh_spd_idx
        ret[veh]["hist_disp_range"] = (df_veh_time_idx["Correction Distance (mm)"].quantile(0.05), 
                                       df_veh_time_idx["Correction Distance (mm)"].quantile(0.95))
        ret[veh]["hist_disp_range"] = None if np.nan in ret[veh]["hist_disp_range"] else ret[veh]["hist_disp_range"]
        ret[veh]["veh_err_bins"] = veh_err_bins
        ret[veh]["veh_dist_bins"] = veh_dist_bins

        ret[veh]['df_stats_pairwise'] = generate_stats_pairwise(df_veh_time_idx, 
                                                                veh, 
                                                                None, 
                                                                test_preset_map[veh]["master_slave_mapping"], 
                                                                test_preset_map[veh]["main_master"],
                                                                raw_name) if test_preset_map is not None else None
        ret[veh]['df_stats_aggregated'] = generate_stats_aggregated(df_veh_time_idx, 
                                                                    veh, 
                                                                    None,
                                                                    raw_name) if test_preset_map is not None else None
    return ret


def dist_interval_idx_df_by_veh_all_tests(veh_dist_idx_df_list, dist_bin, master=None, slave=None):
    if master is None or slave is None:
        assert (master is None) and (slave is None)
    list_df_veh_interval_idx = []
    veh_interval_idx = None
    for df_dist_idx in veh_dist_idx_df_list:
        df_dist_idx = df_dist_idx[df_dist_idx['Instant Speed by Marker (mph)'].notnull()]
        if master and slave:
           df_dist_idx = df_dist_idx[(df_dist_idx["Initiating Master"] == master) & (df_dist_idx["Reporting Slave"] == slave)]
        if df_dist_idx.shape[0] == 0:
            continue
        else:
            if df_dist_idx.index.dropna().is_monotonic_increasing \
                or df_dist_idx.index.dropna().is_monotonic_decreasing:
                interval_ticks = np.arange(
                    dist_bin * (min(df_dist_idx.index) // dist_bin), 
                    dist_bin * ((max(df_dist_idx.index) + dist_bin) // dist_bin + 1), 
                    dist_bin)
                interval_ticks_df = pd.DataFrame(index=interval_ticks)
                ticks_inserted_df = pd.concat([df_dist_idx, interval_ticks_df]).sort_index()
                ticks_inserted_df["Timestamp Norm (s)"] = ticks_inserted_df["Timestamp Norm (s)"].interpolate(method="linear", limit_direction='both', limit_area='inside')
                interval_ticks_df["Timestamp Norms (s)"] = (
                    ticks_inserted_df[~ticks_inserted_df.index.duplicated()]["Timestamp Norm (s)"])
                df_interval_idx = pd.DataFrame()
                df_interval_idx["min timestamp"] = df_dist_idx["Timestamp Norm (s)"].groupby(pd.cut(df_dist_idx.index, interval_ticks)).min()
                df_interval_idx["max timestamp"] = df_dist_idx["Timestamp Norm (s)"].groupby(pd.cut(df_dist_idx.index, interval_ticks)).max()
                df_interval_idx["avg timestamp"] = df_dist_idx["Timestamp Norm (s)"].groupby(pd.cut(df_dist_idx.index, interval_ticks)).mean()
                df_interval_idx["reporting cnt"] = df_dist_idx["Timestamp Norm (s)"].groupby(pd.cut(df_dist_idx.index, interval_ticks)).count()
                # Interpolate values only for the inside NaN gaps. 
                df_interval_idx["avg timestamp"] = df_interval_idx["avg timestamp"].interpolate(  method='linear', 
                                                                                        limit_direction='both', 
                                                                                        limit_area="inside")
                df_interval_idx["left interpolated timestamp"] = interval_ticks_df.iloc[:-1]["Timestamp Norms (s)"].array
                df_interval_idx["right interpolated timestamp"] = interval_ticks_df.iloc[1:]["Timestamp Norms (s)"].array
                df_interval_idx["duration"] = abs(df_interval_idx["left interpolated timestamp"] - df_interval_idx['right interpolated timestamp'])
                list_df_veh_interval_idx.append(df_interval_idx)
                if veh_interval_idx is None:
                    veh_interval_idx = df_interval_idx.index
                else:
                    veh_interval_idx = veh_interval_idx.union(df_interval_idx.index)
    veh_df_interval_idx_all_tests = pd.DataFrame( 
        index=veh_interval_idx, columns=['reporting cnt', 'duration'])
    veh_df_interval_idx_all_tests['reporting cnt'] = 0
    veh_df_interval_idx_all_tests['duration'] = 0
    for df_interval_idx in list_df_veh_interval_idx:
        df_interval_idx = df_interval_idx.reindex_like(veh_df_interval_idx_all_tests).fillna(0)
        veh_df_interval_idx_all_tests['reporting cnt'] += df_interval_idx['reporting cnt']
        veh_df_interval_idx_all_tests['duration'] += df_interval_idx['duration']
    return veh_df_interval_idx_all_tests


def spd_interval_idx_df_by_veh_all_tests(veh_spd_idx_df_list, spd_bin, spd_range, test_preset_map, main_pair=False, absolute=False, min_reporting_cnts=10):
    list_df_spd_idx_pairwise = []
    list_df_veh_interval_idx = []
    veh_interval_idx = None
    for df_spd_idx in veh_spd_idx_df_list:
        veh = df_spd_idx['Initiating Vehicle'].unique()[0]
        df_spd_idx["Time Interval (s)"] = df_spd_idx["Timestamp Norm (s)"].diff()
        if main_pair:
            for master in df_spd_idx['Initiating Master'].unique():
                for slave in df_spd_idx['Reporting Slave'].unique():
                    if (master == test_preset_map[veh]['main_master']) & (slave == test_preset_map[veh]['master_slave_mapping'][test_preset_map[veh]['main_master']][0]):
                        df_spd_idx = df_spd_idx[(df_spd_idx["Initiating Master"] == master) & (df_spd_idx["Reporting Slave"] == slave)]
                        list_df_spd_idx_pairwise.append(df_spd_idx)
        else:
            list_df_spd_idx_pairwise.append(df_spd_idx)
                
    for df_spd_idx_pairwise in list_df_spd_idx_pairwise:
        df_spd_idx_pairwise = df_spd_idx_pairwise[(df_spd_idx_pairwise.index.notnull()) & (np.isfinite(df_spd_idx_pairwise.index))]
        if df_spd_idx_pairwise.index.empty:
            continue
        interval_ticks = np.arange(
            spd_bin * (min(df_spd_idx_pairwise.index) // spd_bin), 
            spd_bin * ((max(df_spd_idx_pairwise.index) + spd_bin) // spd_bin + 1), 
            spd_bin)
        interval_ticks_df = pd.DataFrame()
        interval_ticks_df["duration"] = df_spd_idx_pairwise["Time Interval (s)"].groupby(pd.cut(df_spd_idx_pairwise.index, interval_ticks)).sum()
        interval_ticks_df["reporting cnt"] = df_spd_idx_pairwise["Timestamp Norm (s)"].groupby(pd.cut(df_spd_idx_pairwise.index, interval_ticks)).count()
        list_df_veh_interval_idx.append(interval_ticks_df)
        if veh_interval_idx is None:
            veh_interval_idx = interval_ticks_df.index
        else:
            veh_interval_idx = veh_interval_idx.union(interval_ticks_df.index)

    veh_df_interval_idx_all_tests = pd.DataFrame( 
        index=veh_interval_idx, columns=['reporting cnt', 'duration'])
    veh_df_interval_idx_all_tests['reporting cnt'] = 0
    veh_df_interval_idx_all_tests['duration'] = 0
    for df_interval_idx in list_df_veh_interval_idx:
        df_interval_idx = df_interval_idx.reindex_like(veh_df_interval_idx_all_tests).fillna(0)
        veh_df_interval_idx_all_tests['reporting cnt'] += df_interval_idx['reporting cnt']
        veh_df_interval_idx_all_tests['duration'] += df_interval_idx['duration']
    
    if absolute:
        veh_df_interval_idx_all_tests['absmid'] = [abs(i.mid) for i in veh_df_interval_idx_all_tests.index.array]
        _temp_df_veh = veh_df_interval_idx_all_tests.reset_index(drop=True)
        absv_bins = np.arange(0, 
                        spd_bin * ((max(_temp_df_veh['absmid']) + spd_bin) // spd_bin + 1), 
                        spd_bin)
        veh_df_interval_idx_all_tests = pd.DataFrame()
        veh_df_interval_idx_all_tests['reporting cnt'] = _temp_df_veh.groupby(
            pd.cut(_temp_df_veh['absmid'], absv_bins)).apply(lambda i:sum(i['reporting cnt']))
        veh_df_interval_idx_all_tests["duration"] = _temp_df_veh.groupby(
            pd.cut(_temp_df_veh['absmid'], absv_bins)).apply(lambda i:sum(i["duration"]))
    veh_df_interval_idx_all_tests = veh_df_interval_idx_all_tests.loc[
        [spd_range[0] < i.mid < spd_range[1] for i in veh_df_interval_idx_all_tests.index.array]]
    veh_df_interval_idx_all_tests['update rate (hz)'] = veh_df_interval_idx_all_tests['reporting cnt'] / veh_df_interval_idx_all_tests['duration']
    veh_df_interval_idx_all_tests = veh_df_interval_idx_all_tests[veh_df_interval_idx_all_tests['reporting cnt']>=min_reporting_cnts]
    return veh_df_interval_idx_all_tests

