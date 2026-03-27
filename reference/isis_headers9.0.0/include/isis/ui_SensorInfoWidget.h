/********************************************************************************
** Form generated from reading UI file 'SensorInfoWidget.ui'
**
** Created by: Qt User Interface Compiler version 5.15.8
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_SENSORINFOWIDGET_H
#define UI_SENSORINFOWIDGET_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QFrame>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QScrollArea>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QTabWidget>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_SensorInfoWidget
{
public:
    QVBoxLayout *verticalLayout;
    QScrollArea *scrollArea;
    QWidget *scrollAreaWidgetContents;
    QVBoxLayout *verticalLayout_2;
    QLabel *targetImage;
    QLabel *spacecraftlabel;
    QSpacerItem *verticalSpacer;
    QTabWidget *tabWidget;
    QWidget *tab;
    QWidget *layoutWidget;
    QGridLayout *gridLayout;
    QLabel *label;
    QSpacerItem *horizontalSpacer;
    QLabel *poleDeclinationLabel;
    QLabel *label_2;
    QLabel *poleRightAscensionLabel;
    QSpacerItem *horizontalSpacer_4;
    QWidget *tab_3;
    QWidget *layoutWidget_3;
    QGridLayout *gridLayout_3;
    QSpacerItem *horizontalSpacer_11;
    QLabel *bRadiiLabel;
    QLabel *meanRadiiLabel;
    QLabel *cRadiiLabel;
    QLabel *meanLabel;
    QLabel *aRadiiLabel;
    QLabel *bRadiiUnitsLabel;
    QLabel *meanRadiiUnitsLabel;
    QLabel *cRadiiUnitsLabel;
    QLabel *aLabel;
    QLabel *cLabel;
    QLabel *aRadiiUnitsLabel;
    QLabel *bLabel;
    QLabel *label_9;
    QWidget *tab_2;
    QWidget *widget;
    QGridLayout *gridLayout_2;
    QLabel *label_6;
    QSpacerItem *horizontalSpacer_6;
    QLabel *polePMOffsetLabel;
    QLabel *label_10;
    QSpacerItem *verticalSpacer_2;
    QLabel *label_7;
    QLabel *label_11;
    QLabel *label_12;

    void setupUi(QFrame *SensorInfoWidget)
    {
        if (SensorInfoWidget->objectName().isEmpty())
            SensorInfoWidget->setObjectName(QString::fromUtf8("SensorInfoWidget"));
        SensorInfoWidget->resize(444, 625);
        verticalLayout = new QVBoxLayout(SensorInfoWidget);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        scrollArea = new QScrollArea(SensorInfoWidget);
        scrollArea->setObjectName(QString::fromUtf8("scrollArea"));
        scrollArea->setWidgetResizable(true);
        scrollAreaWidgetContents = new QWidget();
        scrollAreaWidgetContents->setObjectName(QString::fromUtf8("scrollAreaWidgetContents"));
        scrollAreaWidgetContents->setGeometry(QRect(0, 0, 424, 605));
        verticalLayout_2 = new QVBoxLayout(scrollAreaWidgetContents);
        verticalLayout_2->setObjectName(QString::fromUtf8("verticalLayout_2"));
        targetImage = new QLabel(scrollAreaWidgetContents);
        targetImage->setObjectName(QString::fromUtf8("targetImage"));
        targetImage->setMinimumSize(QSize(391, 181));
        targetImage->setMaximumSize(QSize(391, 181));
        targetImage->setFrameShape(QFrame::Panel);
        targetImage->setFrameShadow(QFrame::Sunken);
        targetImage->setLineWidth(2);
        targetImage->setScaledContents(true);

        verticalLayout_2->addWidget(targetImage);

        spacecraftlabel = new QLabel(scrollAreaWidgetContents);
        spacecraftlabel->setObjectName(QString::fromUtf8("spacecraftlabel"));

        verticalLayout_2->addWidget(spacecraftlabel);

        verticalSpacer = new QSpacerItem(20, 13, QSizePolicy::Minimum, QSizePolicy::Preferred);

        verticalLayout_2->addItem(verticalSpacer);

        tabWidget = new QTabWidget(scrollAreaWidgetContents);
        tabWidget->setObjectName(QString::fromUtf8("tabWidget"));
        tabWidget->setMinimumSize(QSize(391, 181));
        tabWidget->setTabPosition(QTabWidget::South);
        tab = new QWidget();
        tab->setObjectName(QString::fromUtf8("tab"));
        layoutWidget = new QWidget(tab);
        layoutWidget->setObjectName(QString::fromUtf8("layoutWidget"));
        layoutWidget->setGeometry(QRect(10, 10, 301, 211));
        gridLayout = new QGridLayout(layoutWidget);
        gridLayout->setObjectName(QString::fromUtf8("gridLayout"));
        gridLayout->setContentsMargins(0, 0, 0, 0);
        label = new QLabel(layoutWidget);
        label->setObjectName(QString::fromUtf8("label"));
        QFont font;
        font.setPointSize(14);
        font.setBold(true);
        font.setWeight(75);
        label->setFont(font);

        gridLayout->addWidget(label, 0, 0, 1, 2);

        horizontalSpacer = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout->addItem(horizontalSpacer, 0, 2, 1, 1);

        poleDeclinationLabel = new QLabel(layoutWidget);
        poleDeclinationLabel->setObjectName(QString::fromUtf8("poleDeclinationLabel"));
        QFont font1;
        font1.setPointSize(10);
        poleDeclinationLabel->setFont(font1);
        poleDeclinationLabel->setWordWrap(true);

        gridLayout->addWidget(poleDeclinationLabel, 3, 0, 1, 3);

        label_2 = new QLabel(layoutWidget);
        label_2->setObjectName(QString::fromUtf8("label_2"));
        label_2->setFont(font);

        gridLayout->addWidget(label_2, 2, 0, 1, 2);

        poleRightAscensionLabel = new QLabel(layoutWidget);
        poleRightAscensionLabel->setObjectName(QString::fromUtf8("poleRightAscensionLabel"));
        poleRightAscensionLabel->setFont(font1);
        poleRightAscensionLabel->setWordWrap(true);

        gridLayout->addWidget(poleRightAscensionLabel, 1, 0, 1, 3);

        horizontalSpacer_4 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout->addItem(horizontalSpacer_4, 2, 2, 1, 1);

        tabWidget->addTab(tab, QString());
        tab_3 = new QWidget();
        tab_3->setObjectName(QString::fromUtf8("tab_3"));
        layoutWidget_3 = new QWidget(tab_3);
        layoutWidget_3->setObjectName(QString::fromUtf8("layoutWidget_3"));
        layoutWidget_3->setGeometry(QRect(20, 20, 311, 191));
        gridLayout_3 = new QGridLayout(layoutWidget_3);
        gridLayout_3->setObjectName(QString::fromUtf8("gridLayout_3"));
        gridLayout_3->setContentsMargins(0, 0, 0, 0);
        horizontalSpacer_11 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_3->addItem(horizontalSpacer_11, 0, 2, 1, 1);

        bRadiiLabel = new QLabel(layoutWidget_3);
        bRadiiLabel->setObjectName(QString::fromUtf8("bRadiiLabel"));
        QFont font2;
        font2.setPointSize(14);
        bRadiiLabel->setFont(font2);
        bRadiiLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(bRadiiLabel, 2, 2, 1, 1);

        meanRadiiLabel = new QLabel(layoutWidget_3);
        meanRadiiLabel->setObjectName(QString::fromUtf8("meanRadiiLabel"));
        meanRadiiLabel->setFont(font2);
        meanRadiiLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(meanRadiiLabel, 4, 2, 1, 1);

        cRadiiLabel = new QLabel(layoutWidget_3);
        cRadiiLabel->setObjectName(QString::fromUtf8("cRadiiLabel"));
        cRadiiLabel->setFont(font2);
        cRadiiLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(cRadiiLabel, 3, 2, 1, 1);

        meanLabel = new QLabel(layoutWidget_3);
        meanLabel->setObjectName(QString::fromUtf8("meanLabel"));
        QFont font3;
        font3.setPointSize(14);
        font3.setBold(false);
        font3.setWeight(50);
        meanLabel->setFont(font3);
        meanLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(meanLabel, 4, 0, 1, 1);

        aRadiiLabel = new QLabel(layoutWidget_3);
        aRadiiLabel->setObjectName(QString::fromUtf8("aRadiiLabel"));
        aRadiiLabel->setFont(font2);
        aRadiiLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(aRadiiLabel, 1, 2, 1, 1);

        bRadiiUnitsLabel = new QLabel(layoutWidget_3);
        bRadiiUnitsLabel->setObjectName(QString::fromUtf8("bRadiiUnitsLabel"));
        bRadiiUnitsLabel->setFont(font2);
        bRadiiUnitsLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(bRadiiUnitsLabel, 2, 3, 1, 1);

        meanRadiiUnitsLabel = new QLabel(layoutWidget_3);
        meanRadiiUnitsLabel->setObjectName(QString::fromUtf8("meanRadiiUnitsLabel"));
        meanRadiiUnitsLabel->setFont(font2);
        meanRadiiUnitsLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(meanRadiiUnitsLabel, 4, 3, 1, 1);

        cRadiiUnitsLabel = new QLabel(layoutWidget_3);
        cRadiiUnitsLabel->setObjectName(QString::fromUtf8("cRadiiUnitsLabel"));
        cRadiiUnitsLabel->setFont(font2);
        cRadiiUnitsLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(cRadiiUnitsLabel, 3, 3, 1, 1);

        aLabel = new QLabel(layoutWidget_3);
        aLabel->setObjectName(QString::fromUtf8("aLabel"));
        aLabel->setFont(font3);
        aLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(aLabel, 1, 0, 1, 1);

        cLabel = new QLabel(layoutWidget_3);
        cLabel->setObjectName(QString::fromUtf8("cLabel"));
        cLabel->setFont(font3);
        cLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(cLabel, 3, 0, 1, 1);

        aRadiiUnitsLabel = new QLabel(layoutWidget_3);
        aRadiiUnitsLabel->setObjectName(QString::fromUtf8("aRadiiUnitsLabel"));
        aRadiiUnitsLabel->setFont(font2);
        aRadiiUnitsLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(aRadiiUnitsLabel, 1, 3, 1, 1);

        bLabel = new QLabel(layoutWidget_3);
        bLabel->setObjectName(QString::fromUtf8("bLabel"));
        bLabel->setFont(font3);
        bLabel->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(bLabel, 2, 0, 1, 1);

        label_9 = new QLabel(layoutWidget_3);
        label_9->setObjectName(QString::fromUtf8("label_9"));
        label_9->setFont(font3);

        gridLayout_3->addWidget(label_9, 0, 0, 1, 2);

        tabWidget->addTab(tab_3, QString());
        tab_2 = new QWidget();
        tab_2->setObjectName(QString::fromUtf8("tab_2"));
        widget = new QWidget(tab_2);
        widget->setObjectName(QString::fromUtf8("widget"));
        widget->setGeometry(QRect(10, 10, 291, 151));
        gridLayout_2 = new QGridLayout(widget);
        gridLayout_2->setObjectName(QString::fromUtf8("gridLayout_2"));
        gridLayout_2->setContentsMargins(0, 0, 0, 0);
        label_6 = new QLabel(widget);
        label_6->setObjectName(QString::fromUtf8("label_6"));
        label_6->setFont(font);

        gridLayout_2->addWidget(label_6, 0, 0, 1, 1);

        horizontalSpacer_6 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_2->addItem(horizontalSpacer_6, 0, 1, 1, 1);

        polePMOffsetLabel = new QLabel(widget);
        polePMOffsetLabel->setObjectName(QString::fromUtf8("polePMOffsetLabel"));
        polePMOffsetLabel->setFont(font1);
        polePMOffsetLabel->setWordWrap(true);

        gridLayout_2->addWidget(polePMOffsetLabel, 1, 0, 1, 2);

        tabWidget->addTab(tab_2, QString());

        verticalLayout_2->addWidget(tabWidget);

        label_10 = new QLabel(scrollAreaWidgetContents);
        label_10->setObjectName(QString::fromUtf8("label_10"));

        verticalLayout_2->addWidget(label_10);

        verticalSpacer_2 = new QSpacerItem(20, 37, QSizePolicy::Minimum, QSizePolicy::Preferred);

        verticalLayout_2->addItem(verticalSpacer_2);

        label_7 = new QLabel(scrollAreaWidgetContents);
        label_7->setObjectName(QString::fromUtf8("label_7"));
        label_7->setWordWrap(true);

        verticalLayout_2->addWidget(label_7);

        label_11 = new QLabel(scrollAreaWidgetContents);
        label_11->setObjectName(QString::fromUtf8("label_11"));

        verticalLayout_2->addWidget(label_11);

        label_12 = new QLabel(scrollAreaWidgetContents);
        label_12->setObjectName(QString::fromUtf8("label_12"));
        label_12->setWordWrap(true);

        verticalLayout_2->addWidget(label_12);

        scrollArea->setWidget(scrollAreaWidgetContents);

        verticalLayout->addWidget(scrollArea);


        retranslateUi(SensorInfoWidget);

        tabWidget->setCurrentIndex(0);


        QMetaObject::connectSlotsByName(SensorInfoWidget);
    } // setupUi

    void retranslateUi(QFrame *SensorInfoWidget)
    {
        SensorInfoWidget->setWindowTitle(QCoreApplication::translate("SensorInfoWidget", "Sensor Information", nullptr));
        targetImage->setText(QString());
        spacecraftlabel->setText(QCoreApplication::translate("SensorInfoWidget", "Spacecraft", nullptr));
        label->setText(QCoreApplication::translate("SensorInfoWidget", "Right Ascension", nullptr));
        poleDeclinationLabel->setText(QCoreApplication::translate("SensorInfoWidget", "Now is the time for all good men to come to the aid of their countrymen", nullptr));
        label_2->setText(QCoreApplication::translate("SensorInfoWidget", "Declination", nullptr));
        poleRightAscensionLabel->setText(QCoreApplication::translate("SensorInfoWidget", "Now is the time for all good men to come to the aid of their countrymen", nullptr));
        tabWidget->setTabText(tabWidget->indexOf(tab), QCoreApplication::translate("SensorInfoWidget", "Specifications", nullptr));
        bRadiiLabel->setText(QCoreApplication::translate("SensorInfoWidget", "TextLabel", nullptr));
        meanRadiiLabel->setText(QCoreApplication::translate("SensorInfoWidget", "TextLabel", nullptr));
        cRadiiLabel->setText(QCoreApplication::translate("SensorInfoWidget", "TextLabel", nullptr));
        meanLabel->setText(QCoreApplication::translate("SensorInfoWidget", "mean", nullptr));
        aRadiiLabel->setText(QCoreApplication::translate("SensorInfoWidget", "TextLabel", nullptr));
        bRadiiUnitsLabel->setText(QCoreApplication::translate("SensorInfoWidget", "km", nullptr));
        meanRadiiUnitsLabel->setText(QCoreApplication::translate("SensorInfoWidget", "km", nullptr));
        cRadiiUnitsLabel->setText(QCoreApplication::translate("SensorInfoWidget", "km", nullptr));
        aLabel->setText(QCoreApplication::translate("SensorInfoWidget", "a", nullptr));
        cLabel->setText(QCoreApplication::translate("SensorInfoWidget", "c", nullptr));
        aRadiiUnitsLabel->setText(QCoreApplication::translate("SensorInfoWidget", "km", nullptr));
        bLabel->setText(QCoreApplication::translate("SensorInfoWidget", "b", nullptr));
        label_9->setText(QCoreApplication::translate("SensorInfoWidget", "Radii", nullptr));
        tabWidget->setTabText(tabWidget->indexOf(tab_3), QCoreApplication::translate("SensorInfoWidget", "What else?", nullptr));
        label_6->setText(QCoreApplication::translate("SensorInfoWidget", "Prime Meridian (W)", nullptr));
        polePMOffsetLabel->setText(QCoreApplication::translate("SensorInfoWidget", "Now is the time for all good men to come to the aid of their countrymen", nullptr));
        tabWidget->setTabText(tabWidget->indexOf(tab_2), QCoreApplication::translate("SensorInfoWidget", "Calibration", nullptr));
        label_10->setText(QCoreApplication::translate("SensorInfoWidget", "where", nullptr));
        label_7->setText(QCoreApplication::translate("SensorInfoWidget", "T = interval in Julien centuries (of 36525 days) from the standard epoch.", nullptr));
        label_11->setText(QCoreApplication::translate("SensorInfoWidget", "d = interval in days from the standard epoch.", nullptr));
        label_12->setText(QCoreApplication::translate("SensorInfoWidget", "The standard epoch is JD 2451545.0, i.e. 2000 January 1 12 hours TDB.", nullptr));
    } // retranslateUi

};

namespace Ui {
    class SensorInfoWidget: public Ui_SensorInfoWidget {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_SENSORINFOWIDGET_H
