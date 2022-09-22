// -------------------------------------------------------------------------------------------------------------------
//
//  File: SerialConnection.cpp
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#include "SerialConnection.h"

#include <QDebug>
#include <QSerialPortInfo>
#include <QMessageBox>
#include "json_utils.h"
#include "windows.h"

#define INST_VERSION_LEN  (64)


SerialConnection::SerialConnection(QObject *parent) :
    QObject(parent)
{
    _serial = new QSerialPort(this);

    connect(_serial, SIGNAL(error(QSerialPort::SerialPortError)), this,
            SLOT(handleError(QSerialPort::SerialPortError)));
    _serialDisconnected = true;
}

SerialConnection::~SerialConnection()
{
    if(_serial->isOpen())
        _serial->close();

    delete _serial;
}

QStringList SerialConnection::portsList()
{
    return _ports;
}

void SerialConnection::findSerialDevices()
{
    _portInfo.clear();
    _ports.clear();

    foreach (const QSerialPortInfo &port, QSerialPortInfo::availablePorts())
    //for (QSerialPortInfo port : QSerialPortInfo::availablePorts())
    {
        if(!port.hasProductIdentifier())
        {
            continue;
        }
#ifdef QT_DEBUG
        //Their is some sorting to do for just list the port I want, with vendor Id & product Id
        qDebug() << "Probing:" << port.portName() << port.vendorIdentifier() << port.productIdentifier()
                 << port.hasProductIdentifier() << port.hasVendorIdentifier() << port.isBusy()
                 << port.manufacturer() << port.description();
#else
        qDebug() << "Probing: " << port.portName() << port.description();
#endif

        _serial->setPort(port);
        if(!_serial->isOpen())
        {
            if (_serial->open(QIODevice::ReadWrite))
            {
                _serial->setBaudRate(QSerialPort::Baud115200/*p.baudRate*/);
                _serial->setDataBits(QSerialPort::Data8/*p.dataBits*/);
                _serial->setParity(QSerialPort::NoParity/*p.parity*/);
                _serial->setStopBits(QSerialPort::OneStop/*p.stopBits*/);
                _serial->setFlowControl(QSerialPort::NoFlowControl /*p.flowControl*/);
                _serial->setDataTerminalReady(true);

                QByteArray  data ;
                QString     device ;

                writeData("stop\n");
                while(_serial->waitForReadyRead(500))
                {
                    data = _serial->readAll();
                    qDebug() << QString(data).toLocal8Bit();
                }
                _serial->clear();

                Sleep(100);

                writeData("deca$\n");
                Sleep(100);
                while(_serial->waitForReadyRead(1000))
                {
                    data = _serial->readAll();
                    device += QString(data);
#ifdef QT_DEBUG
                    qDebug() << device.toLocal8Bit();
#endif
                }
                _serial->clear();

                if(device.contains("Node") || device.contains("Juniper"))
                {
                    _portInfo += port;
                    _ports += port.portName();
                }

                _serial->close();
            }
            else
            {
                _serial->close();
            }
        }
    }

    //connect(_serial, SIGNAL(readyRead()), this, SLOT(readData()));
}

int SerialConnection::openSerialPort(QSerialPortInfo x)
{
    int error = 0;
    _serial->setPort(x);

    if(!_serial->isOpen())
    {
        if (_serial->open(QIODevice::ReadWrite))
        {
            _serial->setBaudRate(QSerialPort::Baud115200/*p.baudRate*/);
            _serial->setDataBits(QSerialPort::Data8/*p.dataBits*/);
            _serial->setParity(QSerialPort::NoParity/*p.parity*/);
            _serial->setStopBits(QSerialPort::OneStop/*p.stopBits*/);
            _serial->setFlowControl(QSerialPort::NoFlowControl /*p.flowControl*/);
            _serial->setReadBufferSize(0);  //set the unlimited buffer size
            _serial->setDataTerminalReady(true);

            emit statusBarMessage(tr("Connected to %1").arg(x.portName()));

#if 0
//          on creating of a list of all com-ports, the "stop\n" has already been issued
            writeData("stop\n");
            while(_serial->waitForReadyRead(1000))
            {
                QByteArray  data ;
                data = _serial->readAll();
            }
            _serial->clear();
#endif

#if 1
            connect(_serial, SIGNAL(readyRead()), this, SLOT(readData()));

            writeData("deca$\n");
            _serial->waitForReadyRead(2000);
#else
            //do not really need to use a slot in this one-time readData() action
            writeData("deca$\n");
            _serial->waitForReadyRead(1000);
            readData();
#endif
        }
        else
        {
            emit statusBarMessage(tr("Open error"));

            qDebug() << "Serial error: " << _serial->error();

            _serial->close();

            emit serialError();

            error = 1;
        }
    }
    else
    {
        qDebug() << "port already open!";

        error = 0;
    }


    if(_serial->isOpen())
    {
        emit connectionStateChanged(Connected);
    }

    return error;
}

int SerialConnection::openConnection(int index)
{
    QSerialPortInfo x;

    //open port from list
    x = _portInfo.at(index);

    qDebug() << "port is busy? " << x.isBusy() << "index " << index;
    //if(!open) return -1;

    qDebug() << "open serial port " << index << x.portName();

    //open serial port
    return openSerialPort(x);
}

void SerialConnection::closeConnection(bool error)
{
    if(!error) //the serial port is closing gracefully (e.g. cable has not been unplugged)
    {
        writeData("stop\n");
        _serial->clear();
    }

    _serial->close();

    while(_serial->isOpen())
    {
        _serial->clear();
    }

    emit statusBarMessage(tr("COM port Disconnected"));
    emit connectionStateChanged(Disconnected);

    _serialDisconnected = true;
}

void SerialConnection::writeData(const QByteArray &data)
{
    if(_serial->isOpen())
    {
        _serial->write(data);
        qDebug() << "send:" << data.constData();
    }
    else
    {
        qDebug() << "Serial is not open - can't write";
    }
}

void SerialConnection::clear()
{
    _serial->clear();
}

void SerialConnection::cancelConnection()
{
    emit connectionStateChanged(ConnectionFailed);
}

void SerialConnection::readData(void)
{
    if(_serialDisconnected)
    {
        QByteArray data = _serial->readAll();
        QByteArray dataChunk;
        int length = data.length();
        int offset = 0;

        qDebug() << "SerialConnection::readData() " << length << ":" << data ;

        while(length >= (MIN_JSON_TLV_HEADER))
        {
            QByteArray header = data.mid(offset, 2);

            if(header.contains("JS")) //loop here until we reach header ("JS")
            {
                bool ok = false;
                //next 4 is JSON object length, including curly brackets
                int jlength =  data.mid(offset+2, 4).toInt(&ok,16);

                //length >= jlength + 6 or else the object will be malformed
                if(ok && (length >= (jlength + MIN_JSON_TLV_HEADER)))
                {
                    //get the JSON object including curly brackets from the stream
                    dataChunk = data.mid(offset+MIN_JSON_TLV_HEADER, jlength);

                    {//awaiting for version object, no more

                        QString device, version;

                        check_json_version(dataChunk, &device, &version );

                        offset += (jlength+MIN_JSON_TLV_HEADER);
                        length -= (jlength+MIN_JSON_TLV_HEADER);

                        if(device.contains("Node")||device.contains("Juniper"))
                        {
                            qDebug() << "Node version: " << version;

                            _connectionConfig = version.mid(0,10);
                            _serialDisconnected = false;
                            _connectionNodeStr = device;

                            _serial->clear();

                            emit serialOpened(_connectionConfig);

                            return;
                        }
                    }
                }
            } //wait for JSON header
            offset += 1;
            length -= 1;
        }
        writeData("deca$\n");
    }
}


void SerialConnection::handleError(QSerialPort::SerialPortError error)
{
    if (error == QSerialPort::ResourceError) {
        //QMessageBox::critical(this, tr("Critical Error"), serial->errorString());
        closeConnection(true);
    }
}


QString * SerialConnection::get_connectionNodeStr(void)
{
    return &_connectionNodeStr;
}

