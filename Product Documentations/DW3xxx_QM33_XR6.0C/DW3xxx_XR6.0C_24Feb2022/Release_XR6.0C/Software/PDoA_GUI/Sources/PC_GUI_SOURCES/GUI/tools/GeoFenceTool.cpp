// -------------------------------------------------------------------------------------------------------------------
//
//  File: GeoFenceTool.cpp
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#include "GeoFenceTool.h"

#include "ViewSettings.h"
#include "RTLSDisplayApplication.h"

#include <QCursor>

GeoFenceTool::GeoFenceTool(QObject *parent) :
    AbstractTool(parent)
{
}

QCursor GeoFenceTool::cursor()
{
    return Qt::CrossCursor;
}

void GeoFenceTool::clicked(const QPointF &scenePos)
{
    ViewSettings *vs = RTLSDisplayApplication::viewSettings();
    //vs->setGFCentreX(scenePos.x());
    //vs->setGFCentreY(scenePos.y());

    vs->setGFCentreXY(scenePos.x(), scenePos.y());

    //emit done();
}

void GeoFenceTool::signalDone(void)
{
    emit done();
}
