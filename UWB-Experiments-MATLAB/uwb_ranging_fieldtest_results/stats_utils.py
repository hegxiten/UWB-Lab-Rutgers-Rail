from datetime import datetime
import math
import pandas as pd
from plot_utils import get_time_stamp_lim, get_nan_slices_indices, RESAMPLE_RULE


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
            pairwise_stats_map['Ground Truth (mm)'] = df_pairwise_sliced["Surveyed Distance (mm)"].get(0, float('nan'))
            pairwise_stats_map['Average Measurement (mm)'] = df_pairwise_sliced["Correction Distance (mm)"].mean()
            pairwise_stats_map['STD (mm)'] = df_pairwise_sliced["Correction Distance (mm)"].std()
            pairwise_stats_map['Operation Duration'] = (time_stamp_lim[1] - time_stamp_lim[0]).total_seconds()
            pairwise_stats_map['Reporting Counts'] = len(df_pairwise_sliced.index)
            pairwise_stats_map['Downtime Periods'] = get_nan_slices_indices(df_pairwise_sliced, veh, time_stamp_lim)
            pairwise_stats_map['Downtime Duration'] = sum([(_stopt - _startt).total_seconds()
                                                              for [_startt, _stopt] in 
                                                              get_nan_slices_indices(df_pairwise_sliced.resample(rule=RESAMPLE_RULE).mean(), 
                                                                                     veh, 
                                                                                     time_stamp_lim)])
            
            stats_list.append(pairwise_stats_map)
    return pd.DataFrame(stats_list)

def generate_stats_aggregated(veh_df, veh, df_with_overall_time, raw_name):
    stats_list = []
    # aggregated stats
    time_stamp_lim = get_time_stamp_lim(veh_df, df_with_overall_time_duration=df_with_overall_time)
    agg_stats_map = {}
    agg_stats_map['Test Name'] = raw_name
    agg_stats_map['Measuring Vehicle'] = veh
    agg_stats_map['Is Aggregated'] = True
    agg_stats_map['Ground Truth (mm)'] = veh_df["Surveyed Distance (mm)"].get(0, float('nan'))
    agg_stats_map['Average Measurement (mm)'] = veh_df["Correction Distance (mm)"].mean()
    agg_stats_map['STD (mm)'] = veh_df["Correction Distance (mm)"].std()
    agg_stats_map['Operation Duration'] = (time_stamp_lim[1] - time_stamp_lim[0]).total_seconds()
    agg_stats_map['Downtime Periods'] = get_nan_slices_indices(veh_df, veh, time_stamp_lim)
    agg_stats_map['Downtime Duration'] = sum([(_stopt - _startt).total_seconds()
                                              for [_startt, _stopt] in 
                                              get_nan_slices_indices(veh_df.resample(rule=RESAMPLE_RULE).mean(), 
                                                                     veh, 
                                                                     time_stamp_lim)])
    agg_stats_map['Reporting Counts'] = len(veh_df.index)
    return pd.DataFrame([agg_stats_map])