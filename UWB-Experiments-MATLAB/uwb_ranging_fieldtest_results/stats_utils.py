from datetime import datetime
import math
import pandas as pd
import numpy as np
from scipy import optimize


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

def update_rate_by_strict_pairs(df, masters, slaves):
    slices_designated_slave = []
    for master_id in df['Initiating Master'].unique():
        if master_id in masters:
            for slave_id in df['Reporting Slave'].unique():
                if slave_id in slaves:
                    sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)]
                    sliced_by_designated_slave["Instant Update Rate (Hz)"] = (1 / sliced_by_designated_slave['Timestamp Norm (s)'].diff().clip(MIN_REPORTING_INTERVAL))
                    slices_designated_slave.append(sliced_by_designated_slave)
    if slices_designated_slave:
        df = pd.concat(slices_designated_slave)
        df.sort_values( ['Timestamp Norm (s)'], ascending=[True], inplace=True)
        df["Aggregated Update Rate (Hz)"] = ((ROLLING_WINDOW - 1) / df["Timestamp Norm (s)"].rolling(ROLLING_WINDOW).apply(lambda x: x[-1] - x[0])).clip(upper=MAX_REPORTING_RATE_PER_VEHICLE)
    return df

def instant_spd_by_strict_pairs(df, masters, slaves):
    slices_uwb_spd_strict_pair = []
    for master_id in df['Initiating Master'].unique():
        if master_id in masters:
            for slave_id in df['Reporting Slave'].unique():
                if slave_id in slaves:
                    sliced_by_designated_slave = df[(df['Reporting Slave'] == slave_id) & (df['Initiating Master'] == master_id)]
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
            pairwise_stats_map['Measuring Vehicle'] = veh
            pairwise_stats_map['Measuring Master'] = master_id
            pairwise_stats_map['Is Main Master'] = True if master_id == main_master else False
            pairwise_stats_map['Measuring Slave'] = slave_id
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
    agg_stats_map['Measuring Vehicle'] = veh
    agg_stats_map['Is Aggregated'] = True
    if len(veh_df["Surveyed Distance (mm)"].unique()) == 1:
        agg_stats_map['Static Ground Truth (mm)'] = veh_df["Surveyed Distance (mm)"].get(0, float('nan'))
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


def interpolate_ground_truth(veh_df, moving_ground_truth_df):
    moving_ground_truth_df = moving_ground_truth_df.set_index("Datetime Normalized")
    moving_ground_truth_df = moving_ground_truth_df[~moving_ground_truth_df.index.isnull()]
    _temp_df_survey_interpolate = pd.DataFrame(index=pd.concat([veh_df, moving_ground_truth_df]).index.drop_duplicates()).sort_index()
    _temp_df_survey_interpolate["Surveyed Distance (mm)"] = moving_ground_truth_df["DIST_GROUND_TRUTH_CPLR_TO_CPLR (mm)"]
    _temp_df_survey_interpolate = _temp_df_survey_interpolate.interpolate(limit_direction='both', limit_area='inside')    
    veh_df["Surveyed Distance (mm)"] = _temp_df_survey_interpolate["Surveyed Distance (mm)"]
    dist_diff = veh_df["Surveyed Distance (mm)"].diff()
    time_diff = veh_df["Timestamp Norm (s)"].diff()
    instant_spd = (dist_diff / time_diff) * 0.00223694
    veh_df["Instant Speed by Marker (mph)"] = instant_spd
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
