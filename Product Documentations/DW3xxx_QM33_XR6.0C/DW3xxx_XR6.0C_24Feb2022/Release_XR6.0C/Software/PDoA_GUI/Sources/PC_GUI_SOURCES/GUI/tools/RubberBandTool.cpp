// -------------------------------------------------------------------------------------------------------------------
//
//  File: RubberBandTool.cpp
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#include "RubberBandTool.h"

#include "RTLSDisplayApplication.h"
#include "GraphicsView.h"
#include "mainwindow.h"

#include <QItemSelectionModel>
#include <QCursor>
#include <QPainter>
#include <QMouseEvent>
#include <QCommonStyle>

RubberBandTool::RubberBandTool(QObject *parent) :
    AbstractTool(parent)
{

}

void RubberBandTool::draw(QPainter *painter, const QRectF &rect, const QPointF &cursor)
{
    /*
     * Rather than just drawing a blue rectangle, we use QStyle which gives a native look to the rubberband object.
     * However, because it use integer coordinates, we need to scale down the painter, to get smaller increments.
     */
    double f = 100.;

    painter->save();
    painter->setClipRect(rect);

    painter->scale(1./f, 1./f);

    QRectF area = QRectF(_start * f, cursor * f).normalized();

    QStyleOptionRubberBand opt;
    opt.rect = area.toAlignedRect();
    QApplication::style()->drawControl(QStyle::CE_RubberBand, &opt, painter);

    painter->restore();
}

bool RubberBandTool::mousePressEvent(const QPointF &scenePos)
{
    _previousItems.clear();

    _start = scenePos;

    return true;
}

void RubberBandTool::mouseMoveEvent(const QPointF &scenePos)
{
    /*
     * Compare the new and old set of item under the designated rectangle.
     * Select the added ones, and unselect the removed ones.
     */

    QRectF area = QRectF(_start, scenePos).normalized();
    QGraphicsScene *scene = RTLSDisplayApplication::graphicsView()->scene();

    QSet<QGraphicsItem *> newItems = scene->items(area).toSet();
    QSet<QGraphicsItem *> oldItems = _previousItems;

    oldItems -= newItems;
    newItems -= _previousItems;

    _previousItems = scene->items(area).toSet();
}

void RubberBandTool::mouseReleaseEvent(const QPointF &scenePos)
{
    Q_UNUSED(scenePos)
    emit done();
}

void RubberBandTool::cancel()
{
    AbstractTool::cancel();
    _previousItems.clear();
}
