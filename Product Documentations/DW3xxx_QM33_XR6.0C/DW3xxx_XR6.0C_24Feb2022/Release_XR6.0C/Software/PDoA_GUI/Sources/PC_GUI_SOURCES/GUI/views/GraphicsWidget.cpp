// -------------------------------------------------------------------------------------------------------------------
//
//  File: GraphicsWidget.cpp
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#include "GraphicsWidget.h"
#include "ui_GraphicsWidget.h"

#include "RTLSDisplayApplication.h"
#include "ViewSettings.h"

#include <QDomDocument>
#include <QGraphicsScene>
#include <QGraphicsItem>
#include <QGraphicsItemGroup>
#include <QGraphicsRectItem>
#include <QDebug>
#include <QInputDialog>
#include <QFile>
#include <QPen>
#include <QDesktopWidget>
#include <QComboBox>

#define PEN_WIDTH (0.05)
#define NODE_SIZE (100) // area to cover has a diameter of 100m ....
#define FONT_SIZE (10)

GraphicsWidget::GraphicsWidget(QWidget *parent) :
    QWidget(parent),
    ui(new Ui::GraphicsWidget)
{
    QDesktopWidget desktop;
    int desktopHeight=desktop.geometry().height();
    int desktopWidth=desktop.geometry().width();
    Q_UNUSED(desktopHeight);

    ui->setupUi(this);

    this->_scene = new QGraphicsScene(this);

    ui->graphicsView->setScene(this->_scene);
    ui->graphicsView->scale(1, -1);
    ui->graphicsView->setBaseSize(this->height()*3/4, this->width());

    //tagTable
    //Tag ID, x, y, range, ...
    QStringList tableHeader;
    tableHeader << "Tag ID/Label" << "Joined" << "X\n(m)" << "Y\n(m)" << "Range (m)"
                << "Use IMU" << "Fast \nrate (Hz)" << "Slow \nrate (Hz)";

    ui->tagTable->setHorizontalHeaderLabels(tableHeader);

    ui->tagTable->setColumnWidth(ColumnID,130);    //ID
    ui->tagTable->setColumnWidth(ColumnJoin,55); //join
    ui->tagTable->setColumnWidth(ColumnX,55); //x
    ui->tagTable->setColumnWidth(ColumnY,55); //y
    ui->tagTable->setColumnWidth(ColumnRA0,70);
    ui->tagTable->setColumnWidth(ColumnIMU,55);
    ui->tagTable->setColumnWidth(ColumnFR,70);
    //ui->tagTable->setColumnWidth(ColumnSR,70);

    ui->tagTable->setColumnHidden(ColumnIDr, true); //ID raw hex
    //ui->tagTable->setColumnWidth(ColumnIDr,70); //ID raw hex
    //ui->tagTable->setColumnHidden(ColumnIMU,true);



    if(desktopWidth <= 800)
    {
        ui->tagTable->setMaximumWidth(200);
    }
    ui->tagTable->setMaximumHeight(150);

    _selectedTagIdx = -1;

    //set defaults
    _tagSize = 0.15;
    _nodeSize = NODE_SIZE;
    _historyLength = 20;
    _showHistoryP = _showHistory = false;
    _showRange = false;

    _busy = true ;
    _ignore = true;

    //periodic timer, to periodically check if tags are present
    //this timer is started on reception of onReady() signal
    _timer = new QTimer(this);
    connect(_timer, SIGNAL(timeout()), this, SLOT(timerUpdateTagTableExpire()));

    _signalMapper = new QSignalMapper(this);

    RTLSDisplayApplication::connectReady(this, "onReady()");
}

void GraphicsWidget::onReady()
{
    QObject::connect(this, SIGNAL(centerAt(double,double)), graphicsView(), SLOT(centerAt(double, double)));
    QObject::connect(this, SIGNAL(centerRect(QRectF)), graphicsView(), SLOT(centerRect(QRectF)));

    QObject::connect(ui->tagTable, SIGNAL(cellChanged(int, int)), this, SLOT(tagTableChanged(int, int)));
    QObject::connect(ui->tagTable, SIGNAL(cellClicked(int, int)), this, SLOT(tagTableClicked(int, int)));
    QObject::connect(ui->tagTable, SIGNAL(itemSelectionChanged()), this, SLOT(itemSelectionChanged()));

    //QObject::connect(ui->tagTable, SIGNAL(cellDoubleClicked(int, int)), this, SLOT(tagTableDoubleClicked(int, int)));

    _timer->setInterval(10000);
    _timer->start();

    QObject::connect(_signalMapper, SIGNAL(mapped(const QString &)), this, SLOT(tableComboChanged(const QString &)));

    _busy = false ;
}

GraphicsWidget::~GraphicsWidget()
{
    // wiping out objects in these two lists
    qDeleteAll( _nodes );
    _nodes.clear();
    qDeleteAll( _tags );
    _tags.clear();

    delete _scene;
    delete ui;
}

GraphicsView *GraphicsWidget::graphicsView()
{
    return ui->graphicsView;
}


void GraphicsWidget::loadConfigFile(QString filename)
{
    QFile file(filename);

    if (!file.open(QIODevice::ReadOnly))
    {
        qDebug(qPrintable(QString("Error: Cannot read file %1 %2").arg(filename).arg(file.errorString())));
        return;
    }

    QDomDocument doc;
    QString error;
    int errorLine;
    int errorColumn;

    if(doc.setContent(&file, false, &error, &errorLine, &errorColumn))
    {
        qDebug() << "file error !!!" << error << errorLine << errorColumn;

        emit setTagHistory(_historyLength);
    }

    QDomElement config = doc.documentElement();

    if( config.tagName() == "config" )
    {
        QDomNode n = config.firstChild();
        while( !n.isNull() )
        {
            QDomElement e = n.toElement();
            if( !e.isNull() )
            {
                if( e.tagName() == "tag_cfg" )
                {
                    _nodeSize = (e.attribute( "size", "" )).toDouble();
                    _historyLength = (e.attribute( "history", "" )).toInt();
                }
                else
                if( e.tagName() == "tag" )
                {
                    bool ok;
                    quint64 id = (e.attribute( "ID", "" )).toULongLong(&ok, 16);
                    Q_UNUSED(id);
                    QString label = (e.attribute( "label", "" ));

                    //_nodeLabels.insert(id, label);
                }
            }

            n = n.nextSibling();
        }

    }

    file.close();

    emit setTagHistory(_historyLength);
}


QDomElement TagToNode( QDomDocument &d, quint64 id, QString label )
{
    QDomElement cn = d.createElement( "tag" );
    cn.setAttribute("ID", QString::number(id, 16));
    cn.setAttribute("label", label);
    return cn;
}

void GraphicsWidget::saveConfigFile(QString filename)
{
    QFile file( filename );

    if (!file.open(QFile::WriteOnly | QFile::Text))
    {
        qDebug(qPrintable(QString("Error: Cannot read file %1 %2").arg("./PDOARTLStag_config.xml").arg(file.errorString())));
        return;
    }

    QDomDocument doc;

    // Adding tag config root
    QDomElement config = doc.createElement("config");
    doc.appendChild(config);

    QDomElement cn = doc.createElement( "tag_cfg" );
    cn.setAttribute("size", QString::number(_nodeSize));
    cn.setAttribute("history", QString::number(_historyLength));
    config.appendChild(cn);

    //update the map
    QMap<quint64, QString>::iterator i = _tagLabels.begin();

    while (i != _tagLabels.end())
    {
        config.appendChild( TagToNode(doc, i.key(), i.value()) );

        i++;
    }

    QTextStream ts( &file );
    ts << doc.toString();

    file.close();

    qDebug() << doc.toString();
}

void GraphicsWidget::tableComboChanged(QString position)
{
    QStringList coordinates = position.split("-");
    int row = coordinates[0].toInt();
    int col = coordinates[1].toInt();

    tagTableClicked(row, col);
    //QComboBox* combo=(QComboBox*)table->cellWidget(row, col);
    //tag->fastrate = indexToRates[cbox->currentIndex()];
}


void GraphicsWidget::itemSelectionChanged(void)
{
    QList <QTableWidgetItem *>  l = ui->tagTable->selectedItems();
}

void GraphicsWidget::tagTableChanged(int r, int c)
{
    if(!_ignore)
    {
        Tag *tag = nullptr;
        bool ok;
        quint64 tagId = (ui->tagTable->item(r,ColumnIDr)->text()).toULongLong(&ok, 16);
        tag = _tags.value(tagId, nullptr);

        if(!tag) return;

        if(c == ColumnID) //label has changed
        {
            QString newLabel = ui->tagTable->item(r,ColumnID)->text();

            tag->tagLabelStr = newLabel;
            tag->tagLabel->setText(newLabel);

            //update the map
            QMap<quint64, QString>::iterator i = _tagLabels.find(tagId);

            if(i == _tagLabels.end()) //did not find the label
            {
                //insert the new value
                _tagLabels.insert(tagId, newLabel);
            }
            else //if (i != taglabels.end()) // && i.key() == tagId)
            {
                _tagLabels.erase(i); //erase the key
                _tagLabels.insert(tagId, newLabel);
            }
        }

        /*if(c == ColumnFR) //label has changed
        {
            tag->joined = tag->joined;
        }*/
    }
}

void GraphicsWidget::tagTableClicked(int r, int c)
{
    Tag *tag = nullptr;
    bool ok;
    quint64 tagId = (ui->tagTable->item(r,ColumnIDr)->text()).toULongLong(&ok, 16);
    tag = _tags.value(tagId, nullptr);

    _selectedTagIdx = r;

    if(!tag) return;

    if(c == ColumnJoin) //add/remove tag from the list of known tags
    {
        QTableWidgetItem *pItemC0 = ui->tagTable->item(r, ColumnID);
        QTableWidgetItem *pItem = ui->tagTable->item(r, c);
        tag->joined = (pItem->checkState() == Qt::Checked) ? true : false;

        if(tag->joined)
        {
            pItemC0->setTextColor(Qt::black);

            pItem->setBackground(QBrush(QColor::fromHsvF(tag->colourH, tag->colourS, tag->colourV)));
        }
        else
        {
            pItemC0->setTextColor(Qt::red);
            pItem->setBackgroundColor(Qt::white);
            tag->showLabel = false;
            QTableWidgetItem *item = ui->tagTable->item(r, ColumnID);
            item->setCheckState(Qt::Unchecked);
        }
    }

    if(c == ColumnIMU) //toggle stationary display
    {
        QTableWidgetItem *pItem = ui->tagTable->item(r, c);
        tag->useIMU = (pItem->checkState() == Qt::Checked) ? true : false;
    }

    if(c == ColumnID) //toggle label
    {
        QTableWidgetItem *pItem = ui->tagTable->item(r, c);
        tag->showLabel = (pItem->checkState() == Qt::Checked) ? true : false;

        tag->tagLabel->setOpacity(tag->showLabel ? 1.0 : 0.0);
        tag->tagLabel2->setOpacity(tag->showLabel ? 1.0 : 0.0);
    }

    //if(c == ColumnFR) //toggle label
    {
        int indexToRates[6] = {1, 2, 5, 10, 50, 100};

        QComboBox* cbox = static_cast<QComboBox*>(ui->tagTable->cellWidget(r, ColumnFR));

        tag->fastrate = indexToRates[cbox->currentIndex()];

    }

    //if tag belongs to the network
    if((c == ColumnJoin)||(c == ColumnFR)||(c == ColumnIMU))
    {
        if(tag->joined == true)
        {
            //fast_rate/slow_rate are in units of superframe periods
            //add 64bitID 16bitID fast_rate slow_rate IMU
            //"Add2list 11AABB4455FF7788 10AA 1 2 1"
            //add this tag to the node's known list so ranging can start
            //
            //
            //slow_rate is set to 100*100ms (0.1 Hz) and should be read from config file
            //
            //
            QString ids = QString("%1").arg(tagId, 16, 16, QChar('0'));
            //QString id16s = QString("%1").arg(tag->id16, 4, 16, QChar('0'));
            QString frs = QString("%1").arg(tag->fastrate, 4, 16, QChar('0'));
            QString mods = QString("%1").arg(tag->useIMU, 2, 16, QChar('0'));

            //slow rate is set to 100 (0x0064)
            //QString add2list = QString("addtag %1 %2 %3 64 %4\r\n").arg(ids).arg(id16s).arg(frs).arg(mods);
            QString add2list = QString("addtag %1 %2 %3 64 %4\r\n").arg(ids).arg(0x1000).arg(frs).arg(mods);

            RTLSDisplayApplication::serialConnection()->writeData(add2list.toLocal8Bit());

            RTLSDisplayApplication::serialConnection()->writeData("save\n");
        }
    }

    if ((c == ColumnJoin) && (tag->joined == false))
    {
        QString ids = QString("%1").arg(tagId, 16, 16, QChar('0'));
        QString deltag = QString("deltag %1\r\n").arg(ids);
        RTLSDisplayApplication::serialConnection()->writeData(deltag.toLocal8Bit());

        RTLSDisplayApplication::serialConnection()->writeData("save\n");

        //clearTag(r); //clear Tag from table and also remove from Tag List (_tags)
        //RTLSDisplayApplication::client()->removeTagFromList(tagId);
    }
}


/**
 * @fn    tagIDtoString
 * @brief  convert hex Tag ID to string (preappend 0x)
 *
 * */
void GraphicsWidget::tagIDToString(quint64 tagId, QString *t)
{
    //NOTE: this needs to be hex string as it is written into ColumnIDr
    //and is used later to remove the correct Tag
    *t = "0x"+QString::number(tagId, 16);
}

int GraphicsWidget::findTagRowIndex(QString &t)
{
    for (int ridx = 0 ; ridx < ui->tagTable->rowCount() ; ridx++ )
    {
        QTableWidgetItem* item = ui->tagTable->item(ridx, ColumnIDr);

        if(item)
        {
            if(item->text() == t)
            {
                return ridx;
            }
        }
    }

    return -1;
}

//get tag ID 64 from label
quint64 GraphicsWidget::getID64FromLabel(QString &label)
{
    bool ok;
    quint64 tagId = 0;

    for (int ridx = 0 ; ridx < ui->tagTable->rowCount() ; ridx++ )
    {
        //QTableWidgetItem* item = ui->tagTable->item(ridx, ColumnIDr);
        QTableWidgetItem* itemLabel = ui->tagTable->item(ridx, ColumnID);
        QTableWidgetItem* itemID64 = ui->tagTable->item(ridx, ColumnIDr);

        if(label == itemLabel->text())
        {
            tagId = itemID64->text().toULongLong(&ok, 16);
            break;
        }

    }

    return tagId;
}


//can only use ranging tags for calibration
QStringList GraphicsWidget::getListOfTags(void)
{
    QStringList list;

    for (int ridx = 0 ; ridx < ui->tagTable->rowCount() ; ridx++ )
    {
        //QTableWidgetItem* item = ui->tagTable->item(ridx, ColumnIDr);
        QTableWidgetItem* item = ui->tagTable->item(ridx, ColumnID);
        QTableWidgetItem* item2 = ui->tagTable->item(ridx, ColumnJoin);
        if(item2->checkState() == Qt::Checked)
        {
            list << item->text();
        }

    }

    return list;
}

/**
 * @fn    getRateIndex
 * @brief  getRateIndex converts tags fast rate (integer: 1, 2, 5, 10, 50 or 100)
 *         which corresponds to 10, 5, 2, 1, 0.2 and 0.1 Hz.
 *
 * */
int getRateIndex(int fastrate)
{
    int comboIdx = 0;

    switch(fastrate)
    {
        case 100: //0.1 Hz
            comboIdx = 5;
        break;
        case 50: //0.2 Hz
            comboIdx = 4;
        break;
        case 10: //1 Hz
            comboIdx = 3;
        break;
        case 5: //2 Hz
            comboIdx = 2;
        break;
        case 2: //5 Hz
            comboIdx = 1;
        break;
        case 1: //10 Hz
        default:
            comboIdx = 0;
        break;
    }

    return comboIdx;
}

/**
 * @fn    insertTag
 * @brief  insert Tag into the tagTable at row ridx
 *
 * */
void GraphicsWidget::insertTag(Tag *tag, int ridx, QString &t, bool showLabel)
{
    _ignore = true;

    ui->tagTable->insertRow(ridx);

    qDebug() << "Insert Tag" << ridx << t << tag->tagLabelStr;

    for( int col = ColumnID ; col < ui->tagTable->columnCount(); col++)
    {
        if(col == ColumnID )
        {
            QTableWidgetItem *pItem = new QTableWidgetItem();
            if(showLabel)
            {
                pItem->setCheckState(Qt::Checked);
                pItem->setText(tag->tagLabelStr);
            }
            else
            {
                pItem->setCheckState(Qt::Unchecked);
                pItem->setText(tag->tagLabelStr);
            }
            ui->tagTable->setItem(ridx, col, pItem);
        }
        else
        {
            QTableWidgetItem *pItem = new QTableWidgetItem();
            if(col == ColumnIDr)
            {
                pItem->setText(t);
            }

            pItem->setFlags((pItem->flags() ^ Qt::ItemIsEditable) | Qt::ItemIsSelectable);
            ui->tagTable->setItem(ridx, col, pItem);
        }

        if(col == ColumnIMU)
        {
            QTableWidgetItem *pItem = new QTableWidgetItem();
            if(tag->useIMU)
            {
                pItem->setCheckState(Qt::Checked);
            }
            else
            {
                pItem->setCheckState(Qt::Unchecked);
            }
            pItem->setText(" ");
            pItem->setFlags(Qt::ItemIsEnabled | Qt::ItemIsUserCheckable);
            pItem->setTextAlignment(Qt::AlignHCenter);
            ui->tagTable->setItem(ridx,col,pItem);
        }


        if(col == ColumnJoin)
        {
            QTableWidgetItem *pItem = new QTableWidgetItem();
            if(tag->joined)
            {
                pItem->setCheckState(Qt::Checked);
                pItem->setBackground(QBrush(QColor::fromHsvF(tag->colourH, tag->colourS, tag->colourV)));
            }
            else
            {
                pItem->setCheckState(Qt::Unchecked);
                pItem->setBackgroundColor(Qt::white);
            }
            pItem->setText(" ");
            pItem->setTextAlignment(Qt::AlignHCenter);
            pItem->setFlags(Qt::ItemIsEnabled | Qt::ItemIsUserCheckable);
            ui->tagTable->setItem(ridx,col,pItem);
        }

        if(col == ColumnFR) //add drop down list for selection of fast rate
        {
            QComboBox* combo = new QComboBox();
            QStringList items;
            items << "10" << "5" << "2" << "1" << "0.2" << "0.1" ;
            //table->setCellWidget(row,col,combo);
            combo->addItems(items);
            combo->setCurrentIndex(getRateIndex(tag->fastrate));
            combo->setFont(tag->tagLabel->font());
            combo->setPalette( QPalette( Qt::white ) );
            //ui->tagTable->setItem(ridx,col,combo);
            ui->tagTable->setCellWidget(ridx,col,combo);

            //connect(combo, SIGNAL(currentIndexChanged(int)),this, SLOT(combochanged(int)));
            connect(combo, SIGNAL(currentIndexChanged(int)), _signalMapper, SLOT(map()));
                 _signalMapper->setMapping(combo, QString("%1-%2").arg(ridx).arg(col));
        }
   }

   _ignore = false; //we've added a row
}

void GraphicsWidget::addDiscoveredTag(quint64 tagId, int id, bool known, int fastrate, int imu)
{
    Tag *tag;
    QString t ;

    tag = _tags.value(tagId, nullptr);

    if(!tag) //add tag that has not already been added
    {
        qDebug() << "addDiscoveredTag " << QString::number(tagId, 16) ;

        addNewTag(tagId, true);

        tag = this->_tags.value(tagId, nullptr);

        tagIDToString(tagId, &t); //convert uint64 to string

        int ridx = findTagRowIndex(t);
        tag->id16 = id;
        tag->joined = known;
        tag->useIMU = imu;

        if(fastrate != -1)
        {
            tag->fastrate = fastrate;
        }

        if(ridx == -1)
        {
            ridx = ui->tagTable->rowCount();

            insertTag(tag, ridx, t, false /*tag->showLabel*/);
        }
    }
}

/**
 * @fn    addNewNode
 * @brief  add new Node with nodeId into the nodes QMap
 *
 * */
void GraphicsWidget::addNewNode(uint nodeId, bool show)
{
    static double c_h = 0.1;
    Node *node;
    Q_UNUSED(show);

    QString _nodeLabel = QString("      Node");

    qDebug() << "Add new Node: 0x" + QString::number(nodeId, 16) << nodeId;

    //insert into QMap list, and create an array to hold history of its positions
    _nodes.insert(nodeId,new(Node));

    node = this->_nodes.value(nodeId, nullptr);
    //node->p.resize(_historyLength);

    c_h += 0.618034;
    if (c_h >= 1)
        c_h -= 1;
    node->colourH = c_h;
    node->colourS = 0.5;
    node->colourV = 0.98;

    node->showLabel = (_nodeLabel != nullptr) ? true : false;
    node->nodeLabelStr = _nodeLabel;

    //node->pixmap = this->_scene->addPixmap(QPixmap(":/node.png"));
#if 0
    {
        QPixmap pm(":/node.png");
        node->pixmap = this->_scene->addPixmap(pm) ;
        node->pixmap->setZValue(1);
        node->pixmap->setOpacity(1);
        node->pixmap->setFlag(QGraphicsItem::ItemIgnoresTransformations);
    }
#endif
    //add text label and hide until we see if user has enabled showLabel
    {
        QPen pen = QPen(Qt::blue);
        node->nodeLabel = new QGraphicsSimpleTextItem(nullptr);
        node->nodeLabel->setFlag(QGraphicsItem::ItemIgnoresTransformations);
        node->nodeLabel->setZValue(1);
        node->nodeLabel->setText(_nodeLabel);
        node->nodeLabel->setOpacity(1);
        QFont font = node->nodeLabel->font();
        font.setPointSize(FONT_SIZE);
        font.setWeight(QFont::Normal);
        node->nodeLabel->setFont(font);
        pen.setStyle(Qt::SolidLine);
        pen.setWidthF(PEN_WIDTH);
        node->nodeLabel->setPen(pen);
        this->_scene->addItem(node->nodeLabel);
    }

    node->gf_enabled = false;
}

/**
 * @fn    addNewTag
 * @brief  add new Tag with tagId into the tags QMap
 *
 * */
void GraphicsWidget::addNewTag(quint64 tagId, bool show)
{
    Q_UNUSED(show);
    static double c_h = 0.1;
    Tag *tag;
    QString taglabel = QString::number(tagId, 16); //taglabels.value(tagId, NULL);

    qDebug() << "Add new Tag: 0x" + taglabel << tagId;

    //insert into QMap list, and create an array to hold history of its positions
    _tags.insert(tagId,new(Tag));

    tag = this->_tags.value(tagId, nullptr);

    tag->id = tagId ;

    tag->p.resize(_historyLength);

    c_h += 0.568034;
    if (c_h >= 1)
        c_h -= 1;
    tag->colourH = c_h;
    tag->colourS = 0.55;
    tag->colourV = 0.98;

    //tag->tsPrev = 0;
    tag->fastrate = 1 ; //default rate is 10 Hz
    tag->joined = false ;
    tag->useIMU = false;
    tag->showLabel = (taglabel != nullptr) ? true : false;
    tag->tagLabelStr = taglabel;
    //add text label and hide until we see if user has enabled showLabel
    {
        QPen pen = QPen(Qt::blue);
        tag->tagLabel = new QGraphicsSimpleTextItem(nullptr);
        tag->tagLabel->setFlag(QGraphicsItem::ItemIgnoresTransformations);
        tag->tagLabel->setZValue(5);
        tag->tagLabel->setText(taglabel);
        tag->tagLabel->setOpacity(0);
        QFont font = tag->tagLabel->font();
        font.setPointSize(FONT_SIZE);
        font.setWeight(QFont::Normal);
        tag->tagLabel->setFont(font);
        pen.setStyle(Qt::SolidLine);
        pen.setWidthF(PEN_WIDTH);
        tag->tagLabel->setPen(pen);
        this->_scene->addItem(tag->tagLabel);
    }
    {
        QPen pen = QPen(Qt::blue);
        tag->tagLabel2 = new QGraphicsSimpleTextItem(nullptr);
        tag->tagLabel2->setFlag(QGraphicsItem::ItemIgnoresTransformations);
        tag->tagLabel2->setZValue(5);
        tag->tagLabel2->setText("");
        tag->tagLabel2->setOpacity(0);
        QFont font = tag->tagLabel2->font();
        font.setPointSize(FONT_SIZE);
        font.setWeight(QFont::Normal);
        tag->tagLabel2->setFont(font);
        pen.setStyle(Qt::SolidLine);
        pen.setWidthF(PEN_WIDTH);
        tag->tagLabel2->setPen(pen);
        this->_scene->addItem(tag->tagLabel2);
    }

    QAbstractGraphicsShapeItem *tag_alarm = this->_scene->addEllipse(-1*0.2/2, -1*0.2/2, 0.2, 0.2);
    QBrush b2 = QBrush(QColor(185, 0, 0, 196));//QColor::fromHsvF(node->colourH, node->colourS, node->colourV));

    tag->alarm = tag_alarm;
    tag->alarm->setBrush(b2);
    tag->alarm->setBrush(b2.color().darker());
    tag->alarm->setOpacity(0); //hide it
    tag->alarm->setPen(Qt::NoPen);
    tag->alarm->setZValue(10);
}

/**
 * @fn    nodePos
 * @brief  update node position on the screen (add to scene if it does not exist)
 *
 * */
void GraphicsWidget::nodePos(int nodeId, double x, double y)
{
    //qDebug() << "nodePos Node: " + QString::number(tagId) << " " << x << " " << y ;

    if(_busy) //don't display
    {
        qDebug() << "(Widget - busy IGNORE) Node: " + QString::number(nodeId) << " " << x << " " << y;
    }
    else
    {
        Node *node = nullptr;
        //bool newNode = false;

        _busy = true ;

        node = _nodes.value(nodeId, nullptr);

        if(!node) //add new node to the nodes array
        {
            //node does not exist, so create a new one
            //newNode = true;
            addNewNode(nodeId, true);
            node = this->_nodes.value(nodeId, nullptr);
        }


        //if(!node->p[node->idx]) //we have not added this object yet to the history array
        {
            //QGraphicsPixmapItem *item = this->_scene->addPixmap(QPixmap("node.png"));
            QGraphicsEllipseItem *ellipse1 = this->_scene->addEllipse(-1*_nodeSize/2, -1*_nodeSize/2, _nodeSize, _nodeSize);
            QGraphicsEllipseItem *ellipse3 = this->_scene->addEllipse(-1*_nodeSize/2, -1*_nodeSize/2, _nodeSize, _nodeSize);
            QGraphicsEllipseItem *ellipse2 = this->_scene->addEllipse(-1*_nodeSize/2, -1*_nodeSize/2, _nodeSize, _nodeSize);

            //this will be used for geo-fencing centre
            ellipse1->setOpacity(0);

            //this will be used for geo-fencing
            ellipse2->setOpacity(0);

            //this is to define the working region area
            ellipse3->setStartAngle(0*16); //start at 60, it is in 16ths of a degree (whole range is 360 * 16)
            ellipse3->setSpanAngle(180*16); //go to 120 deg

            node->zone1 = ellipse1;
            node->zone2 = ellipse2;
            node->zone3 = ellipse3;

            //node->p[node->idx] = item;
            node->zone1->setPen(Qt::NoPen);
            node->zone2->setPen(Qt::NoPen);
            node->zone3->setPen(Qt::NoPen);

            //set semi transparent colour
            QBrush b = QBrush(QColor(0, 255, 0 ,127));//QColor::fromHsvF(node->colourH, node->colourS, node->colourV));
            node->zone1->setBrush(b);
            node->zone1->setBrush(b.color().lighter());
            //node->zone1->setOpacity(0);

            QBrush b3 = QBrush(QColor(0, 235, 0 ,127));//QColor::fromHsvF(node->colourH, node->colourS, node->colourV));
            node->zone3->setBrush(b3);
            node->zone3->setBrush(b3.color().lighter());
            //node->zone3->setOpacity(0);
        }

        _ignore = true;

        node->point.setX(x);
        node->point.setY(y);

        node->zone1->setZValue(3);
        node->zone2->setZValue(5); //zone 2 is for geo-fencing
        node->zone3->setZValue(6);


        node->nodeLabel->setPos(x + 0.15, y + 0.15);

        _ignore = false;
        _busy = false ;

        //qDebug() << "Tag: 0x" + QString::number(tagId, 16) << " " << x << " " << y << " " << z;
    }
}

/*
void GraphicsWidget::scaleNode(qreal dx, qreal dy)
{
    Node *node = NULL;
    node = _nodes.value(0, NULL);

    qDebug() << dx << dy ;

    if(node != NULL)
    {
        //QRectF pixRect = node->pixmap->boundingRect();
        //node->pixmap->setPos(0 - (dx)*0.01, 0 + dy*0.01);

        qDebug() << pixRect << node->point;

        //node->pixmap->setPos(0 - (pixRect.width()/2)*0.01, 0 + pixRect.height()*0.01);

        //node->pixmap->setPos(0 - (dx)*0.01, 0 + pixRect.height()*0.01);
    }

}*/



/**
 * @fn     tagPos
 * @brief  update tag position on the screen (add to scene if it does not exist)
 *
 * */
void GraphicsWidget::tagPos(quint64 tagId, double x, double y, int mode)
{
    QDateTime now = QDateTime::currentDateTime();

    if(_busy) //don't display
    {
        qDebug() << "(Widget - busy IGNORE) Node: " + QString::number(tagId) << " " << x << " " << y;
    }
    else
    {
        int ridx = -1;
        Tag *tag = nullptr;
        bool newTag = false;
        QString t ;

        _busy = true ;

        tagIDToString(tagId, &t); //convert uint64 to string

        tag = _tags.value(tagId, nullptr);

        if(!tag) //add new tag to the tags array
        {
            //tag does not exist, so create a new one
            newTag = true;
            addNewTag(tagId, true);
            tag = this->_tags.value(tagId, nullptr);
        }

        ridx = findTagRowIndex(t);

        if(!tag->p[tag->idx]) //we have not added this object yet to the history array
        {
            QAbstractGraphicsShapeItem *tag_pt = this->_scene->addEllipse(-1*_tagSize/2, -1*_tagSize/2, _tagSize, _tagSize);
            tag->p[tag->idx] = tag_pt;

            tag_pt->setPen(Qt::NoPen);
            tag_pt->setZValue(6);

            if(tag->idx > 0) //use same brush settings for existing tag ID
            {
                tag_pt->setBrush(tag->p[0]->brush());
            }
            else //new brush... new tag ID as idx = 0
            {
                QBrush b = QBrush(QColor::fromHsvF(tag->colourH, tag->colourS, tag->colourV));
                QPen pen = QPen(b.color().darker());
                pen.setStyle(Qt::SolidLine);
                pen.setWidthF(PEN_WIDTH);
                //set the brush colour of the labels
                tag_pt->setBrush(b.color().dark());
                tag->tagLabel->setBrush(b.color().dark());
                tag->tagLabel->setPen(pen);
                tag->tagLabel2->setBrush(b.color().dark());
                tag->tagLabel2->setPen(pen);
            }

            tag_pt->setToolTip(t);

            if(newTag) //if this tag has not been added to the table add it now
            {

                if(ridx == -1)
                {
                    ridx = ui->tagTable->rowCount();

                    insertTag(tag, ridx, t, tag->showLabel);
                }
            }

            //change colour of label to black if it was e.g. in red
            {

                QTableWidgetItem *pItemC0 = ui->tagTable->item(ridx, ColumnID);

                pItemC0->setTextColor(Qt::black); //black

            }
        }

        //if stationary
        {
            QBrush b1 = tag->p[0]->brush();
            QPen p1 = tag->tagLabel->pen();

            if(mode&0x1)
            {//if stationary
                //b1.setStyle(Qt::Dense7Pattern);
                b1.setStyle(Qt::NoBrush);
                p1.setStyle(Qt::SolidLine);
                p1.setWidthF(PEN_WIDTH/2);
            }
            else
            {
                b1.setStyle(Qt::SolidPattern);
                p1.setStyle(Qt::NoPen);
            }

            tag->p[tag->idx]->setBrush(b1);
            tag->p[tag->idx]->setPen(p1);
        }

        tag->_last_time = now;
        tag->_cleared = false;

        //qDebug() << tag->idx << tag->p[0]->brush() << tag->tagLabel->pen();
        //qDebug() << QString::number(tagId, 16) << tag->_last_time ;

        _ignore = true;
//        update table entries
//        ui->tagTable->item(ridx,ColumnX)->setText(QString::number(x, 'f', 3));
//        ui->tagTable->item(ridx,ColumnY)->setText(QString::number(y, 'f', 3));

        //set tag position on the screen
        tag->p[tag->idx]->setPos(x, y);

        tag->alarm->setPos(x, y); //move it to the avg x and y values

        tag->point.setX(x);
        tag->point.setY(y);

        if(_showHistory)
        {
            tagHistory(tagId);
            tag->idx = (tag->idx+1)%_historyLength;
        }
        else
        {
            //index will stay at 0
            tag->p[tag->idx]->setOpacity(1);
        }

        tag->tagLabel->setPos(x + 0.15, y + 0.15);
        tag->tagLabel2->setPos(x + 0.15, y + 0.35);

        _ignore = false;
        _busy = false ;

        //qDebug() << "Tag: 0x" + QString::number(tagId, 16) << " " << x << " " << y << " " << z;
    }
}

/**
 * @fn    tagRange
 * @brief  update range to a particular tag
 *
 * */
void GraphicsWidget::tagRange(quint64 tagID, double range, double x, double y)
{
    //qDebug() << "tagRange: " << tag << " " << range ;

    if(_busy) //don't display
    {
        qDebug() << "(Widget - busy IGNORE) Tag: " << tagID << " range " << range;
    }
    else
    {
        Tag *tag = nullptr;
        QString t ;
        int ridx = 0;
        _busy = true ;

        tag = _tags.value(tagID, nullptr);

        if(!tag) return;

        //NOTE: the ranges are shown on the tags only
        if (tag)
        {
            QString _nodeLabel = QString("R = %3 m").arg(range, 0, 'f', 2);
            tag->tagLabel2->setText(_nodeLabel);
        }

        //update Tag range value in the table
        tagIDToString(tagID, &t);

        ridx = findTagRowIndex(t);

        if(ridx != -1)
        {
            ui->tagTable->item(ridx,ColumnRA0)->setText(QString::number(range, 'f', 3));
            //update table entries
            ui->tagTable->item(ridx,ColumnX)->setText(QString::number(x, 'f', 3));
            ui->tagTable->item(ridx,ColumnY)->setText(QString::number(y, 'f', 3));

        }
        else //add tag into tag table
        {
            ridx = ui->tagTable->rowCount();

            insertTag(tag, ridx, t, false);
        }


        //check geo-fencing area if enabled
        {
            Node *node = _nodes.value(0, nullptr);

            if(node)
            {
                if(node->gf_enabled)
                {
                    //QPointF p(x - node->gf_x, y - node->gf_y);
                    //QPointF p(x, y);
                    //qDebug() << "node->gf_enabled Tag: " << tagID << " range " << range;

                    if(((node->gf_x < x) && ((node->gf_x + node->gf_width) > x))
                            && ((node->gf_y > y) && ((node->gf_y + node->gf_height) < y)))
                    //if(node->zone2->contains(p))
                    {
                        //ALARM !!!
                        tag->alarm->setOpacity(1);
                        ui->tagTable->item(ridx,ColumnID)->setBackground(QBrush(QColor(185, 0, 0, 127)));
                    }
                    else
                    {
                        tag->alarm->setOpacity(0); //transparent
                        ui->tagTable->item(ridx,ColumnID)->setBackground(QBrush(QColor(Qt::white)));
                    }
                }
                else
                {
                    tag->alarm->setOpacity(0); //transparent
                    ui->tagTable->item(ridx,ColumnID)->setBackground(QBrush(QColor(Qt::white)));
                }

            }
        }

        _ignore = false;
        _busy = false ;
    }
}

/**
 * @fn    tagHistory
 * @brief  plot tag's history (the latest position is opaque
 *         and the previous ones have less opacity so that the
 *         one that is _historyLength is transparent
 * */
void GraphicsWidget::tagHistory(quint64 tagId)
{
    int i = 0;
    int j = 0;

    Tag *tag = this->_tags.value(tagId, nullptr);
    for(i = 0; i < _historyLength; i++)
    {
        QAbstractGraphicsShapeItem *tag_p = tag->p[i];

        if(!tag_p)
        {
            break;
        }
        else
        {
            j = (tag->idx - i); //element at index is opaque
            if(j<0) j+= _historyLength;
            tag_p->setOpacity(1-static_cast<qreal>(j)/_historyLength);
        }
    }
}

/**
 * @fn    tagHistoryNumber
 * @brief  set tag history length
 *
 * */
void GraphicsWidget::tagHistoryNumber(int newValue)
{
    bool tag_showHistory = _showHistory;

    while(_busy);
//    if(_busy)
//    {
//        return;
//    }

    _busy = true;

    //remove old history
    setShowTagHistory(false);

    //need to resize all the tag point arrays
    QMap<quint64, Tag*>::iterator i = _tags.begin();

    while(i != _tags.end())
    {
        Tag *tag = i.value();

        if(tag)
        {
            tag->p.resize(newValue);
        }

        tag->idx = 0; //reset history
        i++;
    }

    //set new history length
    _historyLength = newValue;

    //set the history to show/hide
    _showHistory = tag_showHistory;

    _busy = false;
}


/**
 * @fn    drawGeoFencingCentre
 * @brief draw the geofenced area centre
 *
 * */
void GraphicsWidget::drawGeoFencingCentre(double x, double y)
{
    Node *node = nullptr;

    node = _nodes.value(0, nullptr);

    if(node != nullptr) //if node connected
    {
        QGraphicsEllipseItem *ellipse2 = this->_scene->addEllipse(-1*0.05, -1*0.05, 0.05*2, 0.05*2);

        //ellipse2->setPos(0, 0);

        this->_scene->removeItem(node->zone1);
        delete(node->zone1);

        node->zone1 = ellipse2;

        QBrush b2 = QBrush(QColor(255, 0, 0, 127));//QColor::fromHsvF(node->colourH, node->colourS, node->colourV));
        node->zone1->setBrush(b2);

        QPen pen = QPen(b2.color().darker());
        pen.setStyle(Qt::SolidLine);
        pen.setWidthF(PEN_WIDTH);

        node->zone1->setPen(pen);

        node->zone1->setZValue(2);
        node->zone1->setOpacity(1);

        node->zone1->setPos(x, y);
    }
}

/**
 * @fn    startGeoFencing
 * @brief draw the geofenced area based on the passed parameters (centre/range)
 *
 * */
void GraphicsWidget::startGeoFencing(double x, double y, double height, double width)
{
    Node *node = nullptr;

    node = _nodes.value(0, nullptr);

    if(node != nullptr) //if node connected
    {
        //QGraphicsEllipseItem *ellipse2 = this->_scene->addEllipse(-1*rangeStop, -1*rangeStop, rangeStop*2, rangeStop*2);

        //ellipse2->setPos(0, 0);

        QGraphicsRectItem *rectangle = this->_scene->addRect(x, y, width, -height);

        this->_scene->removeItem(node->zone2);
        delete(node->zone2);

        node->zone2 = rectangle;

        QBrush b2 = QBrush(QColor(185, 185, 0, 127));//QColor::fromHsvF(node->colourH, node->colourS, node->colourV));
        node->zone2->setBrush(b2);
        node->zone2->setBrush(b2.color().lighter());

        QPen pen = QPen(b2.color().darker());
        pen.setStyle(Qt::SolidLine);
        pen.setWidthF(PEN_WIDTH);

        node->zone2->setPen(pen);

        node->zone2->setZValue(1);
        node->zone2->setOpacity(1);

        //node->zone2->setPos(x, y);
        node->gf_x = x;
        node->gf_y = y;
        node->gf_height = -height;
        node->gf_width = width;

        node->gf_enabled = true;
    }

}


/**
 * @fn    stopGeoFencing
 * @brief clear the geofenced area
 *
 * */
void GraphicsWidget::stopGeoFencing(void)
{
    Node *node = nullptr;

    node = _nodes.value(0, nullptr);

    if(node != nullptr) //if node connected
    {
        node->zone2->setOpacity(0);
        node->zone1->setOpacity(0);
        node->gf_enabled = false;
    }
}

/**
 * @fn    setShowTagHistory
 * @brief  if show Tag history is checked then display last N Tag locations
 *         else only show the current/last one
 *
 * */
void GraphicsWidget::setShowTagHistory(bool set)
{
    _busy = true ;

    if(set != _showHistory) //the value has changed
    {
        //for each tag
        if(set == false) //we want to hide history - clear the array
        {
            QMap<quint64, Tag*>::iterator i = _tags.begin();

            while(i != _tags.end())
            {
                Tag *tag = i.value();
                //keep 1 at index 0 ...
                for(int idx=1; idx<_historyLength; idx++ )
                {
                    QAbstractGraphicsShapeItem *tag_p = tag->p[idx];
                    if(tag_p)
                    {
                        tag_p->setOpacity(0); //hide it

                        this->_scene->removeItem(tag_p);
                        delete(tag_p);
                        tag_p = nullptr;
                        tag->p[idx] = nullptr;
                    }
                }
                tag->idx = 0; //reset history
                i++;
            }
        }
        else //the history will be shown though the tagHistory function above
        {

        }

        _showHistoryP = _showHistory = set; //update the value
    }

    _busy = false;
}

/**
 * @fn    hideAll
 * @brief  hide all nodes
 *
 * */
/*void GraphicsWidget::hideAll(void)
{

}*/

/**
 * @fn    centerOnNodes
 * @brief  resize the screen so that all nodes and tags are visible
 *
 * */
void GraphicsWidget::centerOnNodes(void)
{
    QPolygonF p1 = QPolygonF();
    QPointF pa1;
    bool ok = false;
    Node *n1 = this->_nodes.value(0, nullptr);

    if(n1 == nullptr)
    {
        return; //no node so just exit
    }

    pa1.setX(n1->point.x()); pa1.setY(n1->point.y());
    p1 << pa1;

    if(_tags.count() == 0)
    {
        return; //no any tags so just exit
    }

    QMap<quint64, Tag*>::iterator i = _tags.begin();

    while(i != _tags.end())
    {
        Tag *t1 = i.value();
        pa1.setX(t1->point.x()); pa1.setY(t1->point.y());
        p1 << pa1;
        ok = true;
        i++;
    }

    if(ok)
    {
        emit centerRect(p1.boundingRect());
    }
}

//this slot should be periodically called by the _timer e.g. every 30000 s
//any tags that do not update their location will be removed from display
//
void GraphicsWidget::timerUpdateTagTableExpire(void)
{
    if(_busy == false)
    {
        _busy = true ;
        if(!_tags.empty())
        {
            QMap<quint64, Tag*>::iterator i = _tags.begin();
            QDateTime now1 = QDateTime::currentDateTime();

//            qDebug() << "update tags on screen " ;
            while(i != _tags.end())
            {
                Tag *tag = i.value();

                if(tag->_last_time.isValid() && !tag->_cleared)
                {
                    QDateTime checkt ;

                    //if there is no update from this tag within 30s then remove the tag from the display
                    if(tag->useIMU)
                    {
                        checkt = tag->_last_time.addSecs(30) ;
                    }
                    else
                    {
                        //fastrate is in units of 100 ms
                        //
                        checkt = tag->_last_time.addSecs(tag->fastrate * 30 / 10) ; //in seconds
                    }
                    //qDebug() << QString::number(tag->id, 16) << tag->_last_time  << checkt << now1 ;
                    //if(tag->joined) //tag is joined
                    if(checkt < now1) //last update was > 60s ago (remove tag)
                    {
                        //qDebug() << tag->_last_time << now1 ;

                        //change colour of label to dark red
                        //only if the tag is joined
                        if(tag->joined)
                        {
                            QString t;
                            int ridx;
                            tagIDToString(tag->id, &t);
                            ridx = findTagRowIndex(t);
                            QTableWidgetItem *pItemC0 = ui->tagTable->item(ridx, ColumnID);
                            pItemC0->setTextColor(Qt::darkRed); //darkRed
                        }

                        if(tag->showLabel) //hide the labels once tag is gone
                        {
                            tag->tagLabel->setOpacity(0.0);
                            tag->tagLabel2->setOpacity(0.0);
                        }

                        //keep 1 at index 0 ...
                        for(int idx=0; idx<_historyLength; idx++ )
                        {
                            QAbstractGraphicsShapeItem *tag_p = tag->p[idx];
                            if(tag_p)
                            {
                                tag_p->setOpacity(0); //hide it

                                this->_scene->removeItem(tag_p);
                                delete(tag_p);
                                tag_p = nullptr;
                                tag->p[idx] = nullptr;
                            }
                        }

                        tag->_cleared = true;
                        qDebug() << "Tag clear history " <<  QString::number(tag->id, 16) << tag->fastrate << "last:" << checkt << "now:" << now1;
                    }
                }
                //tag->idx = 0; //reset history
                i++;
            }
//            qDebug() << "DONE update tags on screen " ;
        }
        _busy = false ;
    }

    //_timer->setInterval(30000);
}

void GraphicsWidget::clearTag(int r)
{
    qDebug() << "clear single row " << r;

    QTableWidgetItem* item = ui->tagTable->item(r, ColumnIDr);

    if(item)
    {
        qDebug() << "Item text: " << item->text();

        bool ok;
        quint64 tagID = item->text().toULongLong(&ok, 16);
        //clear scene from any tags
        Tag *tag = this->_tags.value(tagID, nullptr);
        if(tag->tagLabel) //remove label
        {
            //re-size the elipse... with a new rad value...
            tag->tagLabel->setOpacity(0); //hide it

            this->_scene->removeItem(tag->tagLabel);
            delete(tag->tagLabel);
            tag->tagLabel = nullptr;
        }
        if(tag->tagLabel2) //remove label
        {
            //re-size the elipse... with a new rad value...
            tag->tagLabel2->setOpacity(0); //hide it

            this->_scene->removeItem(tag->tagLabel2);
            delete(tag->tagLabel2);
            tag->tagLabel2 = nullptr;
        }
        //remove history...
        for(int idx=0; idx<_historyLength; idx++ )
        {
            QAbstractGraphicsShapeItem *tag_p = tag->p[idx];
            if(tag_p)
            {
                tag_p->setOpacity(0); //hide it

                this->_scene->removeItem(tag_p);
                delete(tag_p);
                tag_p = nullptr;
                tag->p[idx] = nullptr;

                qDebug() << "hist remove tag " << idx;
            }
        }
        {
            QMap<quint64, Tag*>::iterator i = _tags.find(tagID);

            if(i != _tags.end()) _tags.erase(i);
        }
    }
    ui->tagTable->removeRow(r);


    qDebug() << "clear row ";

}

void GraphicsWidget::clearTags(void)
{
    qDebug() << "table rows " << ui->tagTable->rowCount() << " list " << this->_tags.size();

    while (ui->tagTable->rowCount())
    {
        clearTag(0); //clear table from row 0... after each removal the next row will move into 0th position
    }

    //clear tag table
    ui->tagTable->clearContents();

    qDebug() << "clear tags/tag table";

}

