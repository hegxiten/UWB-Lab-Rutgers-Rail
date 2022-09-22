// -------------------------------------------------------------------------------------------------------------------
//
//  File: GraphicsWidget.h
//
//  Copyright 2014-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#ifndef GRAPHICSWIDGET_H
#define GRAPHICSWIDGET_H

#include <QGraphicsRectItem>
#include <QWidget>
#include <QAbstractItemView>
#include <QGraphicsView>
#include "RTLSClient.h"
#include <QDateTime>
#include <QTimer>
#include <QSignalMapper>

namespace Ui {
class GraphicsWidget;
}

class GraphicsDataModel;
class QGraphicsScene;
class QModelIndex;
class GraphicsView;
class QAbstractGraphicsShapeItem;
class QGraphicsItem;

struct Tag
{
    Tag(void)
    {
        idx = 0;
    }

    quint64 id;
    int id16;
    int idx;
    QVector<QAbstractGraphicsShapeItem *> p;
    bool useIMU;   //use IMU on tag for low update rate indication
    bool joined ;  //does this tag belong to the known network
    int fastrate ; //this is one of the values: 1, 2, 5, 10, 50 or 100 units of 100 ms = SF period.
    //double tsPrev; //previous timestamp in sec
    double colourH;
    double colourS;
    double colourV;

    bool showLabel;
    QGraphicsSimpleTextItem *tagLabel;  //to store tag label/ID
    QGraphicsSimpleTextItem *tagLabel2; //to store range value
    QString tagLabelStr;

    QPointF point;

    QDateTime _last_time;

    bool _cleared;

    QAbstractGraphicsShapeItem *alarm;
};

struct Node
{
    Node(void)
    {
        idx = 0;
        ridx = 0;
    }

    quint64 id;
    int idx;
    int ridx;
    QAbstractGraphicsShapeItem *zone1;
    QAbstractGraphicsShapeItem *zone2;
    QAbstractGraphicsShapeItem *zone3;
    QGraphicsPixmapItem *pixmap;

    double colourH;
    double colourS;
    double colourV;

    bool show;
    bool showLabel;
    QGraphicsSimpleTextItem *nodeLabel;
    QString nodeLabelStr;

    QPointF point;
    //QGraphicsLineItem * line;

    double gf_x;
    double gf_y;
    double gf_height;
    double gf_width;
    bool gf_enabled;
};

class GraphicsWidget : public QWidget
{
    Q_OBJECT

public:

    enum Column {
        ColumnID = 0,   ///< 64 bit address of the tag (uint64)
        ColumnJoin,     ///< join checkbox
        ColumnX,        ///< X coordinate (double)
        ColumnY,        ///< Y coordinate (double)
        ColumnRA0,      ///< range (double)
        ColumnIMU,      ///< IMU on/off (double)
        ColumnFR ,      ///< Fast ranging rate (double)
        //ColumnSR ,      ///< Slow ranging rate (double)
        ColumnIDr,      ///< ID raw (hex) hidden
        ColumnCount
    };

    explicit GraphicsWidget(QWidget *parent = 0);
    ~GraphicsWidget();

    GraphicsView *graphicsView();

    int findTagRowIndex(QString &t);
    void insertTag(Tag *tag, int ridx, QString &t, bool showLabel);
    void tagIDToString(quint64 tagId, QString *t);
    void addNewNode(uint nodeId, bool show); //add Node into the nodes list (QMap)
    void addNewTag(quint64 tagId, bool show); //add Tag into the tags list (QMap)
    void loadConfigFile(QString filename);
    void saveConfigFile(QString filename);

signals:
    void centerAt(double x, double y);
    void centerRect(const QRectF &visibleRect);

    void setTagHistory(int h);

public slots:

    void clearTags(void);
    void clearTag(int r);
    QStringList getListOfTags(void);
    quint64 getID64FromLabel(QString &label);
    //void scaleNode(qreal dx, qreal dy);

    void addDiscoveredTag(quint64 tagId, int id, bool known, int fastrate, int imu);
    void nodePos(int nodeId, double x, double y);
    void tagPos(quint64 tagId, double x, double y, int mode);
    void tagRange(quint64 tagID, double range, double x, double y);

    void centerOnNodes(void);

    void tagHistoryNumber(int value);
    void setShowTagHistory(bool);

    void tagTableChanged(int r, int c);
    void tagTableClicked(int r, int c);
    void itemSelectionChanged(void);
    void tableComboChanged(QString position);

    void startGeoFencing(double x, double y, double rangeStart, double rangeStop);
    void drawGeoFencingCentre(double x, double y);
    void stopGeoFencing(void);

protected slots:
    void onReady();
    void timerUpdateTagTableExpire(void);

protected:
    void tagHistory(quint64 tagId);

private:
    Ui::GraphicsWidget *ui;
    QGraphicsScene *_scene;

    QMap<quint64, Tag*> _tags;
    QMap<quint64, Node *> _nodes;
    QMap<quint64, QString> _tagLabels;

    double  _nodeSize;
    double  _tagSize;
    int   _historyLength;
    bool _showHistory;
    bool _showHistoryP;
    bool _busy;
    bool _ignore;

    int _selectedTagIdx;

    bool _showRange;

    QTimer *_timer;
    QSignalMapper *_signalMapper;
};

#endif // GRAPHICSWIDGET_H
