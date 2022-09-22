// -------------------------------------------------------------------------------------------------------------------
//
//  File: GeoFenceTool.h
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#ifndef GEOFENCETOOL_H
#define GEOFENCETOOL_H

#include "AbstractTool.h"

/**
 * The GeoFenceTool class is a tool used for setting the floorplan's geo-fence area centre point.
 *
 * It reacts to the clicked() event.
 * When clicked() is called, the centre is calculated based on the click position, and the tool finishes right away.
 * @see AbstractTool
 */
class GeoFenceTool : public AbstractTool
{
    Q_OBJECT
public:
    explicit GeoFenceTool(QObject *parent = 0);
    virtual ~GeoFenceTool() {}

    virtual QCursor cursor();

    /**
     * Handle mouse clicks.
     * This function calculate the new centre point based on \a scenePos, and updates it with the new value.
     * The tool then emits the done() signal.
     *
     * @param scenePos the position of the click in scene coordinates.
     */
    virtual void clicked(const QPointF &scenePos);

signals:

public slots:

    void signalDone(void);

};

#endif // GEOFENCETOOL_H
