// -------------------------------------------------------------------------------------------------------------------
//
//  File: SerialConnection.h
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#ifndef SERIALCONNECTION_H
#define SERIALCONNECTION_H

#include <QObject>
#include <QtSerialPort/QSerialPort>
#include <QStringList>
#include <QTimer>

/**
* @brief SerialConnection
*        Constructor, it initialises the Serial Connection its parts
*        it is used for managing the COM port connection.
*/
class SerialConnection : public QObject
{
    Q_OBJECT
public:
    explicit SerialConnection(QObject *parent = nullptr);
    ~SerialConnection();

    enum ConnectionState
    {
        Disconnected = 0,
        Connecting,
        Connected,
        ConnectionFailed
    };

    void findSerialDevices(); //find any tags or PDOA nodes that are connected to the PC

    int openSerialPort(QSerialPortInfo x); //open selected serial port

    QStringList portsList(); //return list of available serial ports (list of ports with tag/PDOA node connected)

    QSerialPort* serialPort() { return _serial; }

signals:
    void serialError(void);
    void getCfg(void);
    void nextCmd(void);

    void statusBarMessage(QString status);
    void connectionStateChanged(SerialConnection::ConnectionState);
    void serialOpened(QString);

public slots:
    void closeConnection(bool);
    void cancelConnection();
    int  openConnection(int index);
    void readData(void);
    void writeData(const QByteArray &data);
    void clear(void);

protected slots:

    void handleError(QSerialPort::SerialPortError error);

public:
    QString *get_connectionNodeStr(void);

private:

    QSerialPort *_serial;

    QList<QSerialPortInfo>    _portInfo ;
    QStringList _ports;

    QList<QByteArray> _cmdList ;

    QString _connectionVersion;
    QString _connectionConfig;
    QString _connectionNodeStr;
    bool _serialDisconnected;
};

#endif // SERIALCONNECTION_H
