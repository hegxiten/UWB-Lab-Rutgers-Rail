# Use the photo-synced clock values from the two PCs used in the field tests
# and output a synchronized timestamp for each data entry

from datetime import datetime


T430_TIME_SNAPSHOTS_SERIES_1 = [
    "2021-05-25 11:33:21.021201",
    "2021-05-25 11:33:22.252233",
    "2021-05-25 11:33:22.923815",
    "2021-05-25 11:33:23.929193",
    "2021-05-25 11:33:24.149055",
    "2021-05-25 11:33:25.267973",
    "2021-05-25 11:33:27.616056",
    "2021-05-25 11:33:28.952845",
]

P52_TIME_SNAPSHOTS_SERIES_1 = [
    "2021-05-25 11:33:18.702721",
    "2021-05-25 11:33:20.011339",
    "2021-05-25 11:33:20.560019",
    "2021-05-25 11:33:21.545972",
    "2021-05-25 11:33:21.873932",
    "2021-05-25 11:33:22.967382",
    "2021-05-25 11:33:25.374067",
    "2021-05-25 11:33:26.575533",
]

T430_TIME_SNAPSHOTS_SERIES_2 = [
    "2021-05-25 21:03:52.174534",
    "2021-05-25 21:03:56.616392",
    "2021-05-25 21:03:55.641101",
    "2021-05-25 21:03:53.478314",
    "2021-05-25 21:03:49.256633",
    "2021-05-25 21:02:10.873004",

]

P52_TIME_SNAPSHOTS_SERIES_2 = [
    "2021-05-25 21:03:49.696099",
    "2021-05-25 21:03:54.180805",
    "2021-05-25 21:03:53.087130",
    "2021-05-25 21:03:51.008897",
    "2021-05-25 21:03:46.843464",
    "2021-05-25 21:02:08.332688",
]

def offset_calculate():
    T430_stmps_1 = [datetime.strptime(i, '%Y-%m-%d %H:%M:%S.%f') for i in T430_TIME_SNAPSHOTS_SERIES_1]
    P52_stmps_1 = [datetime.strptime(i, '%Y-%m-%d %H:%M:%S.%f') for i in P52_TIME_SNAPSHOTS_SERIES_1]

    T430_stmps_2 = [datetime.strptime(i, '%Y-%m-%d %H:%M:%S.%f') for i in T430_TIME_SNAPSHOTS_SERIES_2]
    P52_stmps_2 = [datetime.strptime(i, '%Y-%m-%d %H:%M:%S.%f') for i in P52_TIME_SNAPSHOTS_SERIES_2]

    assert len(P52_stmps_1) == len(T430_stmps_1)
    assert len(P52_stmps_2) == len(T430_stmps_2)

    sum_1 = P52_stmps_1[0] - P52_stmps_1[0]
    for i in range(len(P52_stmps_1)):
        diff_t = P52_stmps_1[i] - T430_stmps_1[i]
        sum_1 += diff_t

    avg_1 = sum_1 / len(P52_stmps_1)

    sum_2 = P52_stmps_2[0] - P52_stmps_2[0]
    for i in range(len(P52_stmps_2)):
        diff_t = P52_stmps_2[i] - T430_stmps_2[i]
        sum_2 += diff_t
    avg_2 = sum_1 / len(P52_stmps_1)
    
    avg_diff = (avg_1 + avg_2) / 2

    T430_offset = avg_diff / 2
    P52_offset = - avg_diff / 2
    
    # Returned in signed datetime objects. 
    # If needed, use object.total_seconds() to convert into float seconds.
    return T430_offset, P52_offset


if __name__ == "__main__":
    print(offset_calculate()[0].total_seconds(), offset_calculate()[1].total_seconds())