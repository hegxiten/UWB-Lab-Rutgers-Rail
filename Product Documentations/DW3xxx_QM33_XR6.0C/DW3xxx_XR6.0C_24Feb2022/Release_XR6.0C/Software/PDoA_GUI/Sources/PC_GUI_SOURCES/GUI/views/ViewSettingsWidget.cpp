// -------------------------------------------------------------------------------------------------------------------
//
//  File: ViewSettingsWidget.cpp
//
//  Copyright 2015-2019 (c) Decawave Ltd, Dublin, Ireland.
//
//  All rights reserved.
//
//  Author:
//
// -------------------------------------------------------------------------------------------------------------------

#include "ViewSettingsWidget.h"
#include "ui_ViewSettingsWidget.h"

#include "RTLSDisplayApplication.h"
#include "QPropertyModel.h"
#include "ViewSettings.h"
#include "OriginTool.h"
#include "GeoFenceTool.h"
#include "ScaleTool.h"
#include "GraphicsView.h"
#include "GraphicsWidget.h"

#include <QFileDialog>
#include <QInputDialog>
#include <QMessageBox>


ViewSettingsWidget::ViewSettingsWidget(QWidget *parent) :
    QWidget(parent),
    ui(new Ui::ViewSettingsWidget),
    _floorplanOpen(false)
{
    ui->setupUi(this);

    //ui->tabWidget->setCurrentIndex(0);
    //ui->tabWidget->removeTab(2);

    QObject::connect(ui->floorplanOpen_pb, SIGNAL(clicked()), this, SLOT(floorplanOpenClicked()));

    QObject::connect(ui->scaleX_pb, SIGNAL(clicked()), this, SLOT(scaleClicked()));
    QObject::connect(ui->scaleY_pb, SIGNAL(clicked()), this, SLOT(scaleClicked()));
    QObject::connect(ui->origin_pb, SIGNAL(clicked()), this, SLOT(originClicked()));

    QObject::connect(ui->gridShow, SIGNAL(clicked()), this, SLOT(gridShowClicked()));
    QObject::connect(ui->showOrigin, SIGNAL(clicked()), this, SLOT(originShowClicked()));
    QObject::connect(ui->showTagHistory, SIGNAL(clicked()), this, SLOT(tagHistoryShowClicked()));

    QObject::connect(ui->tagHistoryN, SIGNAL(valueChanged(int)), this, SLOT(tagHistoryNumberValueChanged(int)));

    QObject::connect(RTLSDisplayApplication::viewSettings(), SIGNAL(showSave(bool)), this, SLOT(showSave(bool)));
    QObject::connect(RTLSDisplayApplication::viewSettings(), SIGNAL(showGO(bool, bool)), this, SLOT(showOriginGrid(bool, bool)));
    QObject::connect(RTLSDisplayApplication::viewSettings(), SIGNAL(setFloorPlanPic()), this, SLOT(getFloorPlanPic()));

    QObject::connect(ui->saveFP, SIGNAL(clicked()), this, SLOT(saveFPClicked()));

    QObject::connect(ui->motionFilter, SIGNAL(clicked()), this, SLOT(motionFilterClicked()));

    QObject::connect(ui->doCalibration, SIGNAL(clicked()), this, SLOT(doCalibrationClicked()));

    QObject::connect(ui->startGeoFencing, SIGNAL(clicked()), this, SLOT(startGeoFencingClicked()));

    QObject::connect(ui->centre_pb_2, SIGNAL(clicked()), this, SLOT(applyClicked()));
    //QObject::connect(ui->gftab, SIGNAL(clicked()), this, SLOT(gfCentreClicked()));
    QObject::connect(ui->tabWidget, SIGNAL(currentChanged(int)), this, SLOT(tabSelected()));

    QObject::connect(RTLSDisplayApplication::client(), SIGNAL(calibrationBar(int)), this, SLOT(calibrationBar(int)));

    QObject::connect(RTLSDisplayApplication::client(), SIGNAL(phaseOffsetUpdated(double)), this, SLOT(writePhaseOffset(double)));
    QObject::connect(RTLSDisplayApplication::client(), SIGNAL(rangeOffsetUpdated(double)), this, SLOT(writeRangeOffset(double)));

    QObject::connect(RTLSDisplayApplication::viewSettings(), SIGNAL(setGFCentreValueXY(double, double)), this, SLOT(setGFCentreXY(double, double)));
    QObject::connect(RTLSDisplayApplication::viewSettings(), SIGNAL(setGFCentreValueX(double)), this, SLOT(setGFCentreX(double)));
    QObject::connect(RTLSDisplayApplication::viewSettings(), SIGNAL(setGFCentreValueY(double)), this, SLOT(setGFCentreY(double)));


    RTLSDisplayApplication::connectReady(this, "onReady()");
}

void ViewSettingsWidget::onReady()
{
    QPropertyDataWidgetMapper *mapper = QPropertyModel::newMapper(RTLSDisplayApplication::viewSettings(), this);
    mapper->addMapping(ui->gridWidth_sb, "gridWidth");
    mapper->addMapping(ui->gridHeight_sb, "gridHeight");

    mapper->addMapping(ui->floorplanFlipX_cb, "floorplanFlipX", "checked");
    mapper->addMapping(ui->floorplanFlipY_cb, "floorplanFlipY", "checked");
    mapper->addMapping(ui->gridShow, "showGrid", "checked");
    mapper->addMapping(ui->showOrigin, "showOrigin", "checked");

    mapper->addMapping(ui->floorplanXOff_sb, "floorplanXOffset");
    mapper->addMapping(ui->floorplanYOff_sb, "floorplanYOffset");

    mapper->addMapping(ui->floorplanXScale_sb, "floorplanXScale");
    mapper->addMapping(ui->floorplanYScale_sb, "floorplanYScale");
    mapper->toFirst();

    QObject::connect(ui->floorplanFlipX_cb, SIGNAL(clicked()), mapper, SLOT(submit())); // Bug with QDataWidgetMapper (QTBUG-1818)
    QObject::connect(ui->floorplanFlipY_cb, SIGNAL(clicked()), mapper, SLOT(submit()));
    QObject::connect(ui->gridShow, SIGNAL(clicked()), mapper, SLOT(submit())); // Bug with QDataWidgetMapper (QTBUG-1818)
    QObject::connect(ui->showOrigin, SIGNAL(clicked()), mapper, SLOT(submit()));

    ui->showTagHistory->setChecked(false);

    ui->tabWidget->setCurrentIndex(0);

    QObject::connect(ui->centerScreen, SIGNAL(clicked()), RTLSDisplayApplication::graphicsWidget(), SLOT(centerOnNodes()));

    _loggingOn = RTLSDisplayApplication::client()->getLoggingState();
    if(_loggingOn)
    {
        setLogging(false);
    }
    else
    {
        setLogging(true);
    }

    QObject::connect(ui->startLog, SIGNAL(clicked()), this, SLOT(startLog()));

    ui->calibrationProceBar->setValue(0);

    // Show phase offset on GUI
    ui->phaseOffsetBox->setValue(RTLSDisplayApplication::client()->getPhaseOffset());

    // Show range offset on GUI
    ui->rangeOffsetBox->setValue(RTLSDisplayApplication::client()->getRangeOffset());

    QObject::connect(RTLSDisplayApplication::serialConnection(), SIGNAL(serialOpened(QString)),
                         this, SLOT(onConnected(QString)));

    QObject::connect(ui->centre_x, SIGNAL(valueChanged(double)), this, SLOT(cxValueChanged(double)));
    QObject::connect(ui->centre_y, SIGNAL(valueChanged(double)), this, SLOT(cyValueChanged(double)));
    QObject::connect(ui->rangeOffsetStop, SIGNAL(valueChanged(double)), this, SLOT(hValueChanged(double)));
    QObject::connect(ui->rangeOffsetStop_2, SIGNAL(valueChanged(double)), this, SLOT(wValueChanged(double)));

    QObject::connect(this, SIGNAL(updateScene()), RTLSDisplayApplication::graphicsView(), SLOT(floorplanChanged()));

    //copy defaults to local
    _new_x = ui->centre_x->value();
    _new_y = ui->centre_y->value();
    _geofencing = false;
}

ViewSettingsWidget::~ViewSettingsWidget()
{
    delete ui;
}

void ViewSettingsWidget::onConnected(QString conf)
{
    Q_UNUSED(conf);
}

void ViewSettingsWidget::tabSelected(){

    if(ui->tabWidget->currentIndex()==3){

        // Do something here when user clicked on Geofencing tab
        gfCentreClicked();
    }
    else
    {
        // cancel the GF tool
        emit toolDone();
    }
}

void ViewSettingsWidget::startLog(void)
{
    if(_loggingOn)
    {
        //stop current log
        RTLSDisplayApplication::client()->closeLog();
        setLogging(false);
    }
    else
    {
        //start new Log
        RTLSDisplayApplication::client()->openNewLog();
        setLogging(true);
    }
}

void ViewSettingsWidget::setLogging(bool on)
{
    _loggingOn = on;

    if(_loggingOn == false)
    {
        ui->startLog->setText("Start Logging");
    }
    else
    {
        ui->startLog->setText("Stop Logging");
    }
}

int ViewSettingsWidget::applyFloorPlanPic(const QString &path)
{
    QPixmap pm(path);

    if (pm.isNull())
    {
        //QMessageBox::critical(this, "Could not load floor plan", QString("Failed to load image : %1").arg(path));
        return -1;
    }

    ui->floorplanPath_lb->setText(QFileInfo(path).fileName());
    RTLSDisplayApplication::viewSettings()->setFloorplanPixmap(pm);

    return 0;
}

void ViewSettingsWidget::getFloorPlanPic()
{
    applyFloorPlanPic(RTLSDisplayApplication::viewSettings()->getFloorplanPath());
}

void ViewSettingsWidget::floorplanOpenClicked()
{
    if(_floorplanOpen == false)
    {
        QString path = QFileDialog::getOpenFileName(this, "Open Bitmap", QString(), "Image (*.png *.jpg *.jpeg *.bmp)");
        if (path.isNull()) return;

        if(applyFloorPlanPic(path) == 0) //if OK set/save the path string
        {
            RTLSDisplayApplication::viewSettings()->floorplanShow(true);
            RTLSDisplayApplication::viewSettings()->setFloorplanPath(path);
        }
        _floorplanOpen = true;
        ui->floorplanOpen_pb->setText("Clear");

    }
    else //clear the floorplan settings
    {
       applyFloorPlanPic("");
       RTLSDisplayApplication::viewSettings()->clearSettings();
       RTLSDisplayApplication::viewSettings()->floorplanShow(false);
       _floorplanOpen = false;
       ui->floorplanOpen_pb->setText("Open");
       ui->floorplanFlipX_cb->setChecked(false);
       ui->floorplanFlipY_cb->setChecked(false);
       ui->floorplanXScale_sb->setValue(100.0);
       ui->floorplanYScale_sb->setValue(100.0);
       ui->floorplanXOff_sb->setValue(0.0);
       ui->floorplanYOff_sb->setValue(0.0);
       ui->floorplanPath_lb->setText("No Floor Plan");
    }
}

void ViewSettingsWidget::showOriginGrid(bool orig, bool grid)
{
    Q_UNUSED(orig)

    ui->gridShow->setChecked(grid);
    ui->showOrigin->setChecked(orig);
}

void ViewSettingsWidget::gridShowClicked()
{
    RTLSDisplayApplication::viewSettings()->setShowGrid(ui->gridShow->isChecked());
}

void ViewSettingsWidget::originShowClicked()
{
    RTLSDisplayApplication::viewSettings()->setShowOrigin(ui->showOrigin->isChecked());
}

void ViewSettingsWidget::tagHistoryNumberValueChanged(int value)
{
    RTLSDisplayApplication::graphicsWidget()->tagHistoryNumber(value);
}

void ViewSettingsWidget::setTagHistory(int h)
{
    ui->tagHistoryN->setValue(h);
}

void ViewSettingsWidget::tagHistoryShowClicked()
{
    RTLSDisplayApplication::graphicsWidget()->setShowTagHistory(ui->showTagHistory->isChecked());
}

void ViewSettingsWidget::saveFPClicked()
{
    RTLSDisplayApplication::viewSettings()->setSaveFP(ui->saveFP->isChecked());

    if(ui->saveFP->isChecked())
    {
        //save the current settings when clicked
       emit saveViewSettings();
    }
}

void ViewSettingsWidget::showSave(bool save)
{
    ui->saveFP->setChecked(save);
}

void ViewSettingsWidget::motionFilterClicked()
{
    RTLSDisplayApplication::client()->enableMotionFilter(ui->motionFilter->isChecked());
}

void ViewSettingsWidget::originClicked()
{
    OriginTool *tool = new OriginTool(this);
    QObject::connect(tool, SIGNAL(done()), tool, SLOT(deleteLater()));
    RTLSDisplayApplication::graphicsView()->setTool(tool);
}

void ViewSettingsWidget::scaleClicked()
{
    ScaleTool *tool = nullptr;

    if (QObject::sender() == ui->scaleX_pb)
        tool = new ScaleTool(ScaleTool::XAxis, this);
    else if (QObject::sender() == ui->scaleY_pb)
        tool = new ScaleTool(ScaleTool::YAxis, this);

    QObject::connect(tool, SIGNAL(done()), tool, SLOT(deleteLater()));
    RTLSDisplayApplication::graphicsView()->setTool(tool);
}

void ViewSettingsWidget::gfCentreClicked()
{
    GeoFenceTool *tool = new GeoFenceTool(this);

    QObject::connect(this, SIGNAL(toolDone()), tool, SLOT(signalDone()));
    QObject::connect(tool, SIGNAL(done()), tool, SLOT(deleteLater()));
    RTLSDisplayApplication::graphicsView()->setTool(tool);
    emit updateScene();
}

void ViewSettingsWidget::applyClicked()
{
    _applied = true;
    ui->centre_x->setValue(_new_x);
    ui->centre_y->setValue(_new_y);
    emit updateScene();
}

void ViewSettingsWidget::setGFCentreX(double x)
{
    _applied = false;
    _new_x = x;
    //ui->centre_x->setValue(x);
}

void ViewSettingsWidget::setGFCentreY(double y)
{
    _applied = false;
    _new_y = y;
    //ui->centre_y->setValue(y);

    RTLSDisplayApplication::graphicsWidget()->drawGeoFencingCentre(_new_x, _new_y);
    //gfCentreClicked(); //re-enable the centre selection
}

void ViewSettingsWidget::setGFCentreXY(double x, double y)
{
    _applied = false;
    _new_x = x;
    _new_y = y;

    RTLSDisplayApplication::graphicsWidget()->drawGeoFencingCentre(_new_x, _new_y);
}

void ViewSettingsWidget::startGeoFencingClicked()
{
    if(_geofencing)
    {
       _geofencing = false;
       ui->startGeoFencing->setText("Enable");

       RTLSDisplayApplication::graphicsWidget()->stopGeoFencing();

       //ui->centre_pb_2->setDisabled(false);
       //ui->centre_x->setDisabled(false);
       //ui->centre_y->setDisabled(false);
       //ui->rangeOffsetStop->setDisabled(false);
    }
    else
    {
        _geofencing = true;
        ui->startGeoFencing->setText("Disable");

        RTLSDisplayApplication::graphicsWidget()->startGeoFencing(ui->centre_x->value(), ui->centre_y->value(),
                                                                  ui->rangeOffsetStop->value(), ui->rangeOffsetStop_2->value());

        //ui->centre_pb_2->setDisabled(true);
        //ui->centre_x->setDisabled(true);
        //ui->centre_y->setDisabled(true);
        //ui->rangeOffsetStop->setDisabled(true);
    }
    emit updateScene();
}

void ViewSettingsWidget::cxValueChanged(double x)
{
    Q_UNUSED(x);
    if(_applied)
        RTLSDisplayApplication::graphicsWidget()->startGeoFencing(ui->centre_x->value(), ui->centre_y->value(),
                                                                 ui->rangeOffsetStop->value(), ui->rangeOffsetStop_2->value());
}

void ViewSettingsWidget::cyValueChanged(double y)
{
    Q_UNUSED(y);
    if(_applied)
        RTLSDisplayApplication::graphicsWidget()->startGeoFencing(ui->centre_x->value(), ui->centre_y->value(),
                                                                 ui->rangeOffsetStop->value(), ui->rangeOffsetStop_2->value());
}

void ViewSettingsWidget::wValueChanged(double h)
{
    Q_UNUSED(h);
    RTLSDisplayApplication::graphicsWidget()->startGeoFencing(ui->centre_x->value(), ui->centre_y->value(),
                                                              ui->rangeOffsetStop->value(), ui->rangeOffsetStop_2->value());
}

void ViewSettingsWidget::hValueChanged(double w)
{
    Q_UNUSED(w);
    RTLSDisplayApplication::graphicsWidget()->startGeoFencing(ui->centre_x->value(), ui->centre_y->value(),
                                                              ui->rangeOffsetStop->value(), ui->rangeOffsetStop_2->value());
}

void ViewSettingsWidget::doCalibrationClicked()
{
    QStringList items;
    items = RTLSDisplayApplication::graphicsWidget()->getListOfTags();

    if(items.length() == 0)
    {
        //no tags to range with - exit with a warning message
        QMessageBox::critical(NULL, tr("Calibration Error"), QString("No joined tags found cannot do calibration!\nPlease add tags to the system."));
    }
    else
    {
        QMessageBox msgBox;
        msgBox.setText("Place the node and a tag at the same height, and directly in front of the node and aligned with the centre line of its antenna array, and measure the distance between them." );
        msgBox.setStandardButtons(QMessageBox::Ok | QMessageBox::Cancel);
        msgBox.setDefaultButton(QMessageBox::Cancel);
        int ret = msgBox.exec();
        switch (ret)
        {
            case QMessageBox::Ok:
            {
                bool ok;
                //QMessageBox msgBox1;
                //msgBox1.setText("Select the tag to use for calibration." );
                //msgBox1.setStandardButtons(QMessageBox::Ok | QMessageBox::Cancel);
                //msgBox1.setDefaultButton(QMessageBox::Cancel);

                {
                    QString idStr = QInputDialog::getItem(nullptr, "Select the tag", "ID:",
                                                          items, 0, false, &ok);
                    //qDebug() << idStr ;
                    //int ret = msgBox1.exec();
                    switch (ret)
                    {
                        case QMessageBox::Ok:
                        {
                            //QString idStr = QInputDialog::getText(NULL, "Distance (m)", "Measured distance (m)", QLineEdit::Normal, "", &ok);
                            double distance = QInputDialog::getDouble(nullptr, "Distance (m)", "Measured distance (m)", 3., 0.5, 10., 3, &ok);

                            if (ok)
                            {
                                quint64 tagId = RTLSDisplayApplication::graphicsWidget()->getID64FromLabel(idStr);
                                RTLSDisplayApplication::client()->enablePhaseAndDistCalibration(tagId, distance);
                            }
                         }
                         break;
                         case QMessageBox::Cancel:
                         break;
                    }
                }

            }
            break;

            case QMessageBox::Cancel:
            break;

        }
    }
}

void ViewSettingsWidget::calibrationBar(int currentVal)
{
    if ((currentVal<=(CALIB_IGNORE_LEN+CALIB_HIS_LEN))&&(currentVal!=-1))
    {
        ui->calibrationProceBar->setValue(currentVal*100/(CALIB_IGNORE_LEN+CALIB_HIS_LEN));

        if (currentVal==CALIB_HIS_LEN)
        {
            currentVal = -1;
        }

    }
}


void ViewSettingsWidget::writePhaseOffset(double updatedPhaseOffset)
{
    ui->phaseOffsetBox->setValue(updatedPhaseOffset/M_PI*180);
}

void ViewSettingsWidget::writeRangeOffset(double updatedRangeOffset)
{
    ui->rangeOffsetBox->setValue(updatedRangeOffset);
}

