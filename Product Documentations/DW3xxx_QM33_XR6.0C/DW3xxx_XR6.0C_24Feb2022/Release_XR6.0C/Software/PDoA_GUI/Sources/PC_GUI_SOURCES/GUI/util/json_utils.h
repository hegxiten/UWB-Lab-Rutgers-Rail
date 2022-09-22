// -------------------------------------------------------------------------------------------------------------------
//
//  File: json_utils.h
//
//  Copyright 2016-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//
// -------------------------------------------------------------------------------------------------------------------
//

#ifndef JSON_UTILS_H
#define JSON_UTILS_H

#include "stdio.h"

#include <QDebug>
#include <QString>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

#define MIN_JSON_TLV_HEADER   (6)   //JS + 4 chars of length e.g. 'JSxxxx{.....}'

typedef struct
{
    int              slot;
    quint64          addr64;
    int              addr16;
    int              multFast;
    int              multSlow;
    int              mode;

    struct {
        int         rangeNum;           //number from Tag Poll and Final messages indicates the current range number
        int         resTime_us;         //reseption time of Final wrt to SuperFrame start
        double      pdoa_deg;           //phase differences in degrees
        double      dist_m;             //distance, m
        double      xdist_m;            //X distance, m
        double      ydist_m;            //Y distance, m
        double      clockOffset_ppm;    //clock offset in ppm
        int         vData;              //service message data from the tag: (stationary, etc)
        int         accX;               //accelerometer X data
        int         accY;               //accelerometer Y data
        int         accZ;               //accelerometer Z data
    }twr;
}tag_data_t;

typedef struct
{
    int     antennaTX_A;   //in DW time units
    int     antennaRX_A;   //in DW time units
    int     antennaTX_B;   //in DW time units
    int     antennaRX_B;   //in DW time units
    int     pdoaOffset;    //in degrees
    int     distOffset;    //in millimeters
    int     accThreshold;               // in milli g
    int     accStationaryDuration;      // in ms (time to decide that node is stationary when below threshold)
    int     accMovingDuration;      // in ms (time to decide that node is moving when above threshold)

}calib_data_t;

int  check_json_stream(const QByteArray pd);
void check_json_version(const QByteArray st, QString *device, QString *version);

#endif //JSON_UTILS_H
