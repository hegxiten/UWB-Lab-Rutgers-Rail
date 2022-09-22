// -------------------------------------------------------------------------------------------------------------------
//
//  File: RTLSClient.cpp
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
// ==============================================================================
// =                                                                            =
// =                                                                            =
// =                D E C A W A V E    C O N F I D E N T I A L                  =
// =                                                                            =
// =                                                                            =
// ==============================================================================
//
// This software contains Decawave confidential information and techniques,
// subject to licence and non-disclosure agreements.  No part of this software
// package may be revealed to any third-party without the express permission of
// Decawave Ltd.
//
// ==============================================================================
//  Author:
//      Decawave
//
// -------------------------------------------------------------------------------------------------------------------

#include "RTLSClient.h"

#include "RTLSDisplayApplication.h"
#include "SerialConnection.h"
#include "mainwindow.h"

#include <QTextStream>
#include <QDateTime>
#include <QThread>
#include <QFile>
#include <QDebug>
#include <math.h>
#include <QMessageBox>

#include <QDomDocument>
#include <QFile>
#include "json_utils.h"
#include "windows.h"

//e.g. RAtagID(16bit) seq (8bit) range(32bit signed mm) PDOA (32bit signed mrad) mode (8bit)
//"RA%04x %02x %04x %04x %02x"
//RA0000 cd 0000057b 0000838b 00
#define PHASE_RANGE_REPORT_ARGS (9)
#define PHASE_RANGE_REPORT_LEN  (58)

#define ANT_FACTOR (1.8)  // ANT_FACTOR depends on antenna characteristics

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/**
* @brief RTLSDisplayApplication
*        Constructor; The application consumes the data received over the COM port connection and sends the
*        processed data to the graphical display
* */
RTLSClient::RTLSClient(QObject *parent) :
    QObject(parent),
    _first(true),
    _file(nullptr)
{
    _fileLogOn = false;
    _motionFilterOn = false;
    _gotKlist = false;
    _serial = nullptr;

    _nodeConfig[0].phaseCorection = 0;
    _nodeConfig[0].rangeCorection = 0;
    _phaseCalibration = false;
    _calibrationDone = false;
    _calibrationDistance = 0 ;
    calibInx = 0;
    calibInx = 0;

    for (int i = 0; i<CALIB_HIS_LEN; i++)
    {
        phaseHisCalib[i] = 0;
        rangeHisCalib[i] = 0;
    }

    RTLSDisplayApplication::connectReady(this, "onReady()");

}

/**
* @brief onReady()
*        When onReady signal is received by the RTLS Client the client sets up a connection to serialConnection
*        serialOpened signal.
* */
void RTLSClient::onReady()
{
    QObject::connect(RTLSDisplayApplication::serialConnection(), SIGNAL(serialOpened(QString)),
                         this, SLOT(onConnected(QString)));

}

/**
* @brief onConnected()
*        When onConnected signal is received by the RTLS Client the client gets ready to consume the data from the
*        opened COM port (connectes to readyRead() signal). It also opens a new log file and updates the status bar message
*        on the main window.
* */
void RTLSClient::onConnected(QString conf)
{
    //update the status bar message with Node's version
    emit statusBarMessage(QString("Deca-PDOA-RTLS node connected (%1)").arg(conf));

    //save Node's version
    _verNode = conf ;
    //get application version to write into the log file
    _verGUI = RTLSDisplayApplication::mainWindow()->version();

    //open a new log file
    openNewLog();

    //signal that the logging is enabled
    if(_fileLogOn)
        emit loggingOn(true);

    //get pointer to Serial Connection object and set up a connection to serial ports readyRead() signal
    _serial = RTLSDisplayApplication::serialConnection();

    //20190729
    //connect(_serial->serialPort(), SIGNAL(readyRead()), this, SLOT(newData()));
    //we will implement polling of the Com port input buffer because readyRead() signal is not good for real-time processing
    //PDoA Node: it is not signaling on high traffic -> bufferyng 12-16K of data
    _timer_com_port_read = new QTimer(this);
    _timer_com_port_read->setInterval(10);
    connect(_timer_com_port_read, SIGNAL(timeout()), this, SLOT(newData()));
    _timer_com_port_read->start();

#if 0
    // send STOP command and then get a list of known tag's from the node
    _serial->clear();
    _serial->writeData("stop\n");
    Sleep(100);
#else
    // Stop command has been issued on searching of the com-port
#endif

    // send STAT request to get Node's PDOA and range offsets to update the displayed information on the GUI
    _serial->writeData(("stat\n"));
//    Sleep(100);

    //start the Node application (as it was stopped above)
    _serial->writeData("node\n"); //set application as PDOA node

    Sleep(100);
    _serial->writeData(("getKList\n"));

    //periodic timer, to periodically request a new tag's list
    //this timer is started from the RTLS client
    _timerDlist = new QTimer(this);
    connect(_timerDlist, SIGNAL(timeout()), this, SLOT(timerDlistExpire()));
    timerDlistStart(2000);

    //when conneted to the node the 1st time - emit signal to GraphicsWidget to add Node object.
    //notify the user which node the GUI is connected to (Node version)
    if(_first)
    {
        //set the position of the node on the screen
        emit nodePos(0, 0, 0); //it is always placed on 0,0 (origin)

        _first = false;
    }
}

/**
* @brief openNewLog()
*        Open a new log file in which to save tag's location data received from the PDOA node
* */
void RTLSClient::openNewLog(void)
{
    QDateTime now = QDateTime::currentDateTime();

    QString filename("./Logs/"+now.toString("yyyyMMdd_hhmmss")+"PDOARTLS_log.txt");
    _file = new QFile(filename);

    if (!_file->open(QFile::ReadWrite | QFile::Text))
    {
        qDebug(qPrintable(QString("Error: Cannot read file %1 %2").arg(filename).arg(_file->errorString())));
        QMessageBox::critical(nullptr, tr("Logfile Error"), QString("Cannot create file %1 %2\nPlease make sure ./Logs/ folder exists.").arg(filename).arg(_file->errorString()));
    }
    else
    {
        QString nowstr = now.toString("T:hhmmsszzz:");
        QString s = nowstr + QString("PDOARTLSGUI:LogFile:%1:%2\n").arg(_verNode).arg(_verGUI);
        QTextStream ts( _file );
        ts << s;

        _fileLogOn = true;
    }
}

/**
* @brief closeLog()
*        Flush and close the opened log file.
* */
void RTLSClient::closeLog(void)
{
    if(_file)
    {
        _file->flush();
        _file->close();
        delete _file;
        _file = nullptr;
    }

    _fileLogOn = false;
}

/**
* @brief getLoggingState()
*        Returns the current logging state
* */
bool RTLSClient::getLoggingState(void)
{
    return _fileLogOn;
}

/**
* @brief updateTagAddr16()
*        update the tag's 16-bit address when the tag added confirmation received from the node
*        Note: although the client sets the tag's address as part of adding of the tag to the node's known list,
*        the node may change the initial address if it sees any conflicts with the already added tags (i.e. the
*        given address matches one of the node's existing tags)
* */
void RTLSClient::updateTagAddr16(quint64 id64, int id16)
{
    int idx = -1;

    //find the tag in the _tagList
    for(idx=0; idx<_tagList.size(); idx++)
    {
        //if this is the tag update the 16-bit address
        if(_tagList.at(idx).id64 == id64)
        {
            tag_reports_t rp = _tagList.at(idx);

            rp.id16 = id16 ;

            //update the list entry
            _tagList.replace(idx, rp);

            continue; //break;
        }

        if(_tagList.at(idx).id16 == id16) //another tag with same 16 bit address
        {
            tag_reports_t rp = _tagList.at(idx);

            rp.id16 = -1 ;

            //update the list entry
            _tagList.replace(idx, rp);
        }

    }
}

/**
* @brief removeTagFromList()
*        remove existing tag from client's tag list
* */
void RTLSClient::removeTagFromList(quint64 id64)
{
    //first check if we have this tag already
    int idx;
    //find the tag in the list
    for(idx=0; idx<_tagList.size(); idx++)
    {
        //find this tag in the list
        if(_tagList.at(idx).id64 == id64)
        {
            break;
        }
    }

    //remove the tag from the list
    if(idx < _tagList.size())
    {
        _tagList.removeAt(idx);
    }

}

/**
* @brief addTagToList()
*        Add a newly discovered tag into the client's tag list and initialise the node tag aoa/range reports structure
*        Send a signal to the graphics display to add the tag to its database
* */
void RTLSClient::addTagToList(quint64 id64)
{
    tag_reports_t r;

    //first check if we have this tag already
    int idx;
    //find the tag in the list
    for(idx=0; idx<_tagList.size(); idx++)
    {
        //find this tag in the list
        if(_tagList.at(idx).id64 == id64)
        {
            return;
        }
    }

    //add new tag to our list
    memset(&r, 0, sizeof(tag_reports_t));
    r.id16 = static_cast<ushort>(-1) ; //don't assign the 16 bit address here ... node will do it when tag joins
    r.id64 = id64;
    r.Mode = 0;
    r.multFast = static_cast<ushort>(1);
    r.multSlow = 1;
    r.ready = false;
    r.filterReady = 0;

    r.filterHisIdx = 0;
    r.motionFilterReady = false;
    for (int i = 0; i<FILTER_SIZE; i++)
    {
       r.estXHis[i] = 0;
       r.estYHis[i] = 0;
    }

    _tagList.append(r);

    //Add newly discovered tag to the list (64-bit ID, 16-bit ID, false as it is new)
    emit addDiscoveredTag(r.id64, r.id16, false, r.multFast, (r.Mode & 0x1));
}

/**
* @brief addTagFromKList()
*        Add a tag (from received Node's Known List into the client's tag list and initialise the node tag aoa/range reports structure
*        Send a signal to the graphics display to add the tag to its database
* */
void RTLSClient::addTagFromKList(void *arg)
{
    tag_data_t    *tag = static_cast<tag_data_t*>(arg);
    tag_reports_t r;
    memset(&r, 0, sizeof(tag_reports_t));
    r.id16 = static_cast<short>(tag->addr16);
    r.id64 = tag->addr64;
    r.Mode = static_cast<short>(tag->mode);
    r.multFast = static_cast<short>(tag->multFast);
    r.multSlow = static_cast<short>(tag->multSlow);
    r.ready = true;
    r.filterReady = 0;

    r.filterHisIdx = 0;
    r.motionFilterReady = false;
    for (int i = 0; i<FILTER_SIZE; i++)
    {
       r.estXHis[i] = 0;
       r.estYHis[i] = 0;
    }

    _tagList.append(r);

    //Add a known tag to the list (64-bit ID, 16-bit ID, true as it is already known)
    emit addDiscoveredTag(r.id64, r.id16, true, r.multFast, (r.Mode & 0x1));
}

/**
* @brief updatePDOAandRangeOffset()
*        Function to update the range and PDOA offsets in the client and on the GUI
* */
void RTLSClient::updatePDOAandRangeOffset(int pdoa_offset_degrees, int range_offset_mm)
{
    _nodeConfig[0].phaseCorection = static_cast<double>(pdoa_offset_degrees) * M_PI / 180.0;
    _nodeConfig[0].rangeCorection = static_cast<double>(range_offset_mm)/1000.0 ;

    emit phaseOffsetUpdated(_nodeConfig[0].phaseCorection);
    emit rangeOffsetUpdated(_nodeConfig[0].rangeCorection);
}

/**
* @brief stddev()
*        Function to calculate STDDEV of the elements of the array
* */
double stddev(double *array, int length)
{
    int i;
    double mean = 0;
    double sum = 0;

    //find a mean
    for(i=0; i<length; i++)
    {
        mean += array[i];
    }

    mean /= length;

    for(i=0; i<length; i++)
    {
        sum += ((array[i] - mean)*(array[i] - mean));
    }

    sum /= (length - 1) ;

    return sqrt (sum) ;
}

/**
* @brief updateTagStatistics()
*        Update tag's statistics: the location history array and the average
* */
void RTLSClient::updateTagStatistics(int i, double x, double y)
{
    int idx = _tagList.at(i).arr_idx;

    tag_reports_t rp = _tagList.at(i);

    //update the value in the array
    rp.x_arr[idx] = x;
    rp.y_arr[idx] = y;

    rp.arr_idx++;
    //wrap the index
    if(rp.arr_idx >= HIS_LENGTH)
    {
        rp.arr_idx = 0;
        rp.ready = true;
        rp.filterReady = 1;
    }

    rp.count++;

    if(rp.filterReady > 0)
    {

        if(rp.filterReady == 1)
        {
            rp.filterReady++;
        }

    }

    //update the list entry
    _tagList.replace(i, rp);
}

/**
* @brief enableMotionFilter()
*        Set _motionFilterOn flag to the given value
* */
void RTLSClient::enableMotionFilter(bool enabled)
{
    _motionFilterOn = enabled;
}

/**
* @brief getPhaseOffset()
*        Get phase corection / offset value
* */
double RTLSClient::getPhaseOffset(void)
{
    return _nodeConfig[0].phaseCorection ;
}

/**
* @brief getRangeOffset()
*        Get range corection / offset value
* */
double RTLSClient::getRangeOffset(void)
{
    return _nodeConfig[0].rangeCorection ;
}

/**
* @brief enablePhaseAndDistCalibration()
*        Clear calibration data and enable calibration; clear the calibration data displayed on the GUI
* */
void RTLSClient::enablePhaseAndDistCalibration(quint64 id64, double distance)
{
    _calibrationTagID = id64;
    _phaseCalibration = true;
    _calibrationDone = false;
    _calibrationDistance = distance;
    _nodeConfig[0].rangeCorection = 0;
    _nodeConfig[0].phaseCorection = 0;

    for (int i = 0; i<CALIB_HIS_LEN; i++)
    {
        phaseHisCalib[i] = 0;
        rangeHisCalib[i] = 0;
    }

    calibInx = 0;
    calibInx = 0;

    //clear the values in the GUI - maybe not needed...
    emit phaseOffsetUpdated(_nodeConfig[0].phaseCorection);
    emit rangeOffsetUpdated(_nodeConfig[0].rangeCorection);

    //clear the values in the node, so that reported range is raw
    sendPhaseAndRangeCorrectionToNode(0, 0);
}

/**
* @brief sendPhaseCorrectionToNode()
*        Send the calculated phase correction offset to the Node also issue the SAVE command to save it
* */
void RTLSClient::sendPhaseAndRangeCorrectionToNode(double phase, double range)
{
    int16_t    tmp = static_cast<int16_t>(180*phase/M_PI);
    QString s_pdof = QString("pdoaoff %1\r\n").arg(tmp, 6, 10, QChar('0'));
    _serial->writeData(s_pdof.toLocal8Bit());

    tmp = static_cast<int16_t>(range*1000);
    s_pdof = QString("rngoff %1\r\n").arg(tmp, 6, 10, QChar('0'));
    _serial->writeData(s_pdof.toLocal8Bit());
}

/**
* @brief processRangeAndPDOAReport()
*        Function to parse the JSON format range and PDOA reports from the node
* */
void RTLSClient::processRangeAndPDOAReport(void *arg)
{
    int idx;
    int tag_index = -1;

    tag_data_t *tag = static_cast<tag_data_t *>(arg);

    double pdoa_rad = (tag->twr.pdoa_deg / 180.0) * M_PI ;


    //1st need to check if we know about this tag, if we do it will be in the list,
    //find the tag in the list
    for(idx=0; idx<_tagList.size(); idx++)
    {
        //find this tag in the list
        if(_tagList.at(idx).id16 == tag->addr16)
        {
            tag_index = idx;
            break;
        }
    }

    if(tag_index == -1)
    {
        //error - this tag is not in the list ...
        //do we need to send a command to node to obtain known tag list?
        return;
    }

    QDateTime now = QDateTime::currentDateTime();
    QString nowstr = now.toString("T:hhmmsszzz:");

    //if invalid ("DEAD") value report to log
    if(static_cast<unsigned int>(tag->twr.xdist_m) == 0xDEADBEEF ||\
       static_cast<unsigned int>(tag->twr.ydist_m) == 0xDEADBEEF)
    {
        //log data to file
        if(_fileLogOn)
        {
            QString s =  nowstr + QString("0xDEAD:%1:%2\n").
                                            arg(QString::number(_tagList.at(tag_index).id64, 16)).
                                            arg(tag->twr.rangeNum);
            QTextStream ts( _file );
            ts << s;
            return;
        }
    }
    // have rang/PDOA report  - update position on the GUI
    {
        tag_reports_t rp1;
        double x, y; //coordinates for plotting on the GUI
        //double estCoordPhaseDeg; //this is the filtered phase (if motion filtering is on)

        x = tag->twr.xdist_m;
        y = -tag->twr.ydist_m; //for GUI the y-axis increases downwards


        //log data to file
        if(_fileLogOn)
        {
            QString s =  nowstr + QString("RR2:%1:%2:%3\n").
                                            arg(QString::number(_tagList.at(tag_index).id64, 16)).
                                            arg(tag->twr.rangeNum).
                                            arg(tag->twr.dist_m);
            QTextStream ts( _file );
            ts << s;
        }

        // Motion Filter of estimation coordinates and phase correction part of stationary node filter
        motionFilter(&x, &y, tag_index);

        // update position on screen
        emit tagPos(_tagList.at(tag_index).id64, x, y, (tag->mode & 0x1));

        //log data to file - !!! NOTE: this data is filtered if filter is enabled, else it will be RAW !!!
        if(_fileLogOn)
        {
            QString s =  nowstr +
                    QString("LOC:%1:%2:%3:%4\n").
                                arg(QString::number(_tagList.at(tag_index).id64, 16)).
                                arg(tag->twr.rangeNum).
                                arg(x).
                                arg(y);
            QTextStream ts( _file );
            ts << s;
        }

        //PDOA calibration
        if (_phaseCalibration && (_tagList.at(tag_index).id64 == _calibrationTagID)) //check if correct tag
        {
            //when calculating pdoa offset, the raw pdoa should be used (i.e. before any offset is applied),
            //need to make sure the ranges/pdoa reported from node are using offsets of 0
            if((tag->mode & 0xC000) == 0xC000) //offsets are clear
            {
                phaseAndRangeCalibration(pdoa_rad, (tag->twr.dist_m - _calibrationDistance));

                emit calibrationBar (calibInx);

                if (_calibrationDone)
                {
                    _phaseCalibration = false;
                    emit phaseOffsetUpdated(_nodeConfig[0].phaseCorection);
                    emit rangeOffsetUpdated(_nodeConfig[0].rangeCorection);
                    emit centerOnNodes();

                    sendPhaseAndRangeCorrectionToNode(_nodeConfig[0].phaseCorection, _nodeConfig[0].rangeCorection);

                    _serial->writeData("save");
                }
            }
        }
        //else //update statistics when not it the calibration mode
        {
            //double stdev;
            //update tag position statistics
            updateTagStatistics(tag_index, x, y); //phase changed to degrees before STDEV calc.

            rp1 = _tagList.at(tag_index);

            emit tagRange(rp1.id64, tag->twr.dist_m, x, y);
        }
        //log data to file
        if(_fileLogOn)
        {
            QString s =  nowstr +
                    QString("AA2:%1:%2:%3:%4\n").
                                arg(QString::number(rp1.id64, 16)).
                                arg(tag->twr.rangeNum).
                                arg(pdoa_rad).
                                arg(_nodeConfig[0].phaseCorection);
            QTextStream ts( _file );
            ts << s;
        }
    } //end of PDOA processing

}

/**
* @brief newData()
*        Function to consume and parse the data received on the serial connection from the Node
* */
void RTLSClient::newData()
{
    static auto reent = 0;
    if(reent)
    {
        qDebug() << "newData: not allowed: reent";
        return;
    }

    if(!_serial)
    {
        return;
    }

    reent = 1;

    QByteArray data;
    int offset;

    data = _serial->serialPort()->readAll();

    if (data.length() > 0)
    {
        _data.append(data);

        offset = 0;
        int length = _data.length();

        while(length >= MIN_JSON_TLV_HEADER) // we have received a range report from the node
        {
            QByteArray header;

            header = _data.mid(offset, 2);

            //loop here until we reach header ("JS")
            if(header.contains("JS"))
            {
                bool ok = false;
                int jlength =  _data.mid(offset+2, 4).toInt(&ok,16);

                if(ok && (length >= jlength+MIN_JSON_TLV_HEADER + 2 /* '/r/n' */))
                {
                    QByteArray dataChunk;

                    dataChunk = _data.mid(offset+MIN_JSON_TLV_HEADER, jlength);

                    check_json_stream(dataChunk);

                    offset += (jlength+MIN_JSON_TLV_HEADER +2/* '/r/n' */);
                    length -= (jlength+MIN_JSON_TLV_HEADER +2/* '/r/n' */);
                }
                else
                {
                    break;
                }
            }
            else if(header.contains("/r/n"))
            {
                offset += 2;
                length -= 2;
            }
            else
            {
                offset += 1;
                length -= 1;
            }
        } //end of while

        _data = _data.right(length);

        //qDebug() <<"_data.size out: " <<_data.size();
    }

    reent = 0;
}

/**
* @brief connectionStateChanged()
*        Consumes the state changed signal from the serial connection, if
*        serial port is closed/disconnected then close the log file and disconnect the readyRead signal
* */
void RTLSClient::connectionStateChanged(SerialConnection::ConnectionState state)
{
    qDebug() << "RTLSClient::connectionStateChanged " << state;

    if(state == SerialConnection::Disconnected) //disconnect from Serial Port
    {
        if(_serial)
        {
            _timer_com_port_read->stop();
            disconnect(_timer_com_port_read, SIGNAL(timeout()), this, SLOT(newData()));

            _timerDlist->stop();

            _serial = nullptr;
        }

        if(_file)
        {
            _file->flush();
            _file->close(); //close the Log file
            delete _file;
            _file = nullptr;
        }

        _gotKlist = false;
        _tagList.clear();

        //clear tags in the GraphicsWidget table
    }

}

/**
* @brief phaseAndRangeCalibration()
*        called during calibration to calculate the PDOA and range offsets.
* */
void RTLSClient::phaseAndRangeCalibration(double phase, double range)
{
    if ((calibInx >= CALIB_IGNORE_LEN) && (calibInx < (CALIB_HIS_LEN + CALIB_IGNORE_LEN)))
    {
        phaseHisCalib [calibInx - CALIB_IGNORE_LEN] = phase;
        rangeHisCalib [calibInx - CALIB_IGNORE_LEN] = range;
        calibInx = calibInx + 1;

    }
    else
    {
        if (calibInx == (CALIB_HIS_LEN + CALIB_IGNORE_LEN))
        {
            double phaseSum = 0, rangeSum = 0;

            for (int i = 0; i<CALIB_HIS_LEN; i++)
            {
                phaseSum = phaseHisCalib[i] + phaseSum;
                rangeSum = rangeHisCalib[i] + rangeSum;
            }

            _nodeConfig[0].rangeCorection = rangeSum/CALIB_HIS_LEN;
            _nodeConfig[0].phaseCorection = phaseSum/CALIB_HIS_LEN;

            _calibrationDone = true;
        }
        else
        {
            calibInx++;
        }

    }

}

/**
* @brief motionFilter()
*        perfrom the motion-filter on the x and y inputs
* */
void RTLSClient::motionFilter(double* x, double* y, int i)
{
     tag_reports_t rp = _tagList.at(i);

     if (rp.filterHisIdx >= FILTER_SIZE)
     {
         rp.filterHisIdx = static_cast<int>(fmod(rp.filterHisIdx,FILTER_SIZE));
         rp.motionFilterReady = true;
     }

     rp.estXHis[rp.filterHisIdx] = *x;
     rp.estYHis[rp.filterHisIdx] = *y;

     rp.filterHisIdx = rp.filterHisIdx + 1;

     if (_motionFilterOn)
     {
         if(rp.motionFilterReady)
         {
             double tempX[FILTER_SIZE];
             memcpy(tempX, &rp.estXHis[0], sizeof(tempX));

             double tempY[FILTER_SIZE];
             memcpy(tempY, &rp.estYHis[0], sizeof(tempY));

             r95Sort(tempX,0,FILTER_SIZE-1);

             *x = (tempX[FILTER_SIZE/2] + tempX[FILTER_SIZE/2-1])/2;

             r95Sort(tempY,0,FILTER_SIZE-1);

             *y = (tempY[FILTER_SIZE/2] + tempY[FILTER_SIZE/2-1])/2;
         }

     }

     //update the list entry
     _tagList.replace(i, rp);
 }

/**
* @brief r95Sort()
*        R95 sort used by the motion filter function above
* */
void r95Sort (double s[], int l, int r)
{
    int i,j;
    double x;
    if(l<r)
    {
        i = l;
        j = r;
        x = s[i];
        while(i<j)
        {
            while (i<j&&s[j]>x) j--;
            if (i<j) s[i++] = s[j];
            while (i<j&&s[i]<x) i++;
            if (i < j) s[j--] = s[i];
        }
        s[i] = x;
        r95Sort(s, l, i-1);
        r95Sort(s, i+1, r);
    }

}


void RTLSClient::timerDlistStart(int t)
{
    _timerDlist->start(t);
}

//this slot should be periodically called by the _timer e.g. every 30sec
void RTLSClient::timerDlistExpire(void)
{
    if(!_serial->serialPort()->isOpen())
    {
        _timerDlist->stop();
        return;
    }

    _serial->writeData("getDlist\n");   //get the list of discovered tags

    if(!_gotKlist)
    {
        _serial->writeData("getKList\n");
    }

    _timerDlist->setInterval(30000);
}


void RTLSClient::gotKlist(bool gotit)
{
    _gotKlist = gotit;
}
