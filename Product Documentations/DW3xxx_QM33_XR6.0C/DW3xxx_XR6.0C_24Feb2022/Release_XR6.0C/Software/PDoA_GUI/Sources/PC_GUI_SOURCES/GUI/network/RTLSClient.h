// -------------------------------------------------------------------------------------------------------------------
//
//  File: RTLSClient.h
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#ifndef RTLSCLIENT_H
#define RTLSCLIENT_H

#include <QObject>
#include <QThread>

#include "SerialConnection.h"
#include <stdint.h>

class QFile;

#define HIS_LENGTH 100
#define FILTER_SIZE 10  //NOTE: filter size needs to be > 2

#define CALIB_IGNORE_LEN 200 //NOTE: If a node is started from "cold", it will take a number of ranges to come up to
                             // the operational temperature. This temperature drift will cause offset to drift during
                             // the initial number of ranges. Thus while doing calibration the 1st 200 ranges will be ignored.
#define CALIB_HIS_LEN 200

typedef struct
{
    double x_arr[HIS_LENGTH]; //array containing history of x coordinates
    double y_arr[HIS_LENGTH]; //array containing history of y coordinates

    quint64 id64;
    int  id16;
    int  multFast;
    int  multSlow;
    int  Mode;

    int arr_idx;
    int count;
    int filterReady;
    bool ready;

    //motion filter
    bool motionFilterReady; //set to true when enough data accumulated in the filter array
    int filterHisIdx;
    double estXHis[FILTER_SIZE];
    double estYHis[FILTER_SIZE];

} tag_reports_t;

typedef struct
{
    double x, y, z;
    int id;
    QString label;
    double phaseCorection;
    double rangeCorection;
} node_struct_t;


class RTLSClient : public QObject
{
    Q_OBJECT

public:
    explicit RTLSClient(QObject *parent = nullptr);

    void updateTagStatistics(int i, double x, double y);
    void addTagToList(quint64 id64);
    void updateTagAddr16(quint64 id64, int id16);
    void addTagFromKList(void *arg);

    void enableMotionFilter(bool enabled);
    void enablePhaseAndDistCalibration(quint64 id64, double distance);

    void openNewLog(void);
    void closeLog(void);
    bool getLoggingState(void);

    void phaseAndRangeCalibration(double phase, double range);
    void motionFilter(double *x, double *y, int tid);

    double getPhaseOffset(void);
    double getRangeOffset(void);

    void processRangeAndPDOAReport(void *arg);

    void sendPhaseAndRangeCorrectionToNode(double phase, double range);

    void updatePDOAandRangeOffset(int pdoa_offset_degrees, int range_offset_cm);

    void removeTagFromList(quint64 id64);
    void gotKlist(bool gotit);

signals:
    void clearTags();
    void tagPos(quint64 tagId, double x, double y, int mode);
    void nodePos(int nodeId, double x, double y);
    void tagRange(quint64 tagID, double range, double x, double y);
    void statusBarMessage(QString status);

    void centerOnNodes();
    void loggingOn(bool);

    //void hideAll();

    void addDiscoveredTag(quint64 tagID, int ID16, bool known, int fastrate, int imu);

    void calibrationBar(int currentVal);
    void phaseOffsetUpdated(double phaseOffset);
    void rangeOffsetUpdated(double rangeOffset);

protected slots:
    void onReady();
    void onConnected(QString conf);
    void newData();

private slots:
    void connectionStateChanged(SerialConnection::ConnectionState);
    void timerDlistExpire(void);
    void timerDlistStart(int);

private:
    bool _first;

    QList <tag_reports_t> _tagList;

    QFile *_file;

    SerialConnection *_serial;

    node_struct_t _nodeConfig[1]; //current demo has only 1 PDOA node
    int _nodeAdd;

    QString _verNode;
    QString _verGUI;

    bool _fileLogOn;
    bool _motionFilterOn;   //set to true when motion filter is running
    bool _gotKlist;         //set to true after the Klist has received

    int calibInx;

    double phaseHisCalib[CALIB_HIS_LEN];
    double rangeHisCalib[CALIB_HIS_LEN];
    double _calibrationDistance;
    bool _phaseCalibration;
    bool _calibrationDone;
    quint64 _calibrationTagID;

    QByteArray _data;

    QTimer *_timer_com_port_read, *_timerDlist;

};

void r95Sort(double s[], int l, int r);

#endif // RTLSCLIENT_H
