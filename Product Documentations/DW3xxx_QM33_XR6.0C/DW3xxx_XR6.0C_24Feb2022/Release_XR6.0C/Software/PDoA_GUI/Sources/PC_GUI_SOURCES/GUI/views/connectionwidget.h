// -------------------------------------------------------------------------------------------------------------------
//
//  File: ConnectionWidget.h
//
//  Copyright 2014-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#ifndef CONNECTIONWIDGET_H
#define CONNECTIONWIDGET_H

#include <QWidget>
#include "SerialConnection.h"

namespace Ui {
class ConnectionWidget;
}

class ConnectionWidget : public QWidget
{
    Q_OBJECT

public:
    explicit ConnectionWidget(QWidget *parent = 0);
    ~ConnectionWidget();
    int updateDeviceList();

public slots:
    void connectionStateChanged(SerialConnection::ConnectionState state);
    void serialError();

protected slots:
    void onReady();
    void connectButtonClicked();

private:
    SerialConnection::ConnectionState _state;
    Ui::ConnectionWidget *ui;

    int _selected;
};

#endif // CONNECTIONWIDGET_H
