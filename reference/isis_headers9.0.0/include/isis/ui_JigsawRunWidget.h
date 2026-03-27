/********************************************************************************
** Form generated from reading UI file 'JigsawRunWidget.ui'
**
** Created by: Qt User Interface Compiler version 5.15.8
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_JIGSAWRUNWIDGET_H
#define UI_JIGSAWRUNWIDGET_H

#include <QtCore/QVariant>
#include <QtGui/QIcon>
#include <QtWidgets/QApplication>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QDockWidget>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QGroupBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLCDNumber>
#include <QtWidgets/QLabel>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QScrollArea>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_JigsawRunWidget
{
public:
    QWidget *dockWidgetContents;
    QVBoxLayout *verticalLayout_3;
    QScrollArea *scrollArea;
    QWidget *scrollAreaWidgetContents;
    QHBoxLayout *horizontalLayout_4;
    QVBoxLayout *verticalLayout_2;
    QHBoxLayout *horizontalLayout;
    QLabel *statusLabel;
    QLabel *statusOutputLabel;
    QSpacerItem *verticalSpacer_3;
    QHBoxLayout *horizontalLayout_2;
    QLabel *iterationLabel;
    QLCDNumber *iterationLcdNumber;
    QLabel *pointLabel;
    QLCDNumber *pointLcdNumber;
    QSpacerItem *verticalSpacer;
    QHBoxLayout *horizontalLayout_3;
    QGroupBox *groupBox;
    QGridLayout *gridLayout;
    QLCDNumber *measuresLcdNumber;
    QLCDNumber *pointsLcdNumber;
    QLCDNumber *imagesLcdNumber;
    QLabel *label_3;
    QLabel *label_6;
    QLabel *label_5;
    QGroupBox *rmsAdjustedPointSigmasGroupBox;
    QGridLayout *gridLayout_2;
    QLabel *radiusLcdLabel;
    QLabel *label_4;
    QLabel *label_7;
    QLCDNumber *latitudeLcdNumber;
    QLCDNumber *longitudeLcdNumber;
    QLCDNumber *radiusLcdNumber;
    QSpacerItem *verticalSpacer_2;
    QVBoxLayout *verticalLayout;
    QCheckBox *detachedLabelsCheckBox;
    QCheckBox *useLastSettings;
    QHBoxLayout *horizontalLayout_8;
    QPushButton *JigsawSetupButton;
    QSpacerItem *horizontalSpacer_2;
    QPushButton *JigsawRunButton;
    QSpacerItem *horizontalSpacer;
    QPushButton *JigsawAcceptButton;
    QSpacerItem *verticalSpacer_4;
    QScrollArea *statusUpdateScrollArea;
    QLabel *statusUpdatesLabel;

    void setupUi(QDockWidget *JigsawRunWidget)
    {
        if (JigsawRunWidget->objectName().isEmpty())
            JigsawRunWidget->setObjectName(QString::fromUtf8("JigsawRunWidget"));
        JigsawRunWidget->resize(638, 586);
        JigsawRunWidget->setMinimumSize(QSize(88, 107));
        dockWidgetContents = new QWidget();
        dockWidgetContents->setObjectName(QString::fromUtf8("dockWidgetContents"));
        dockWidgetContents->setEnabled(true);
        QSizePolicy sizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(dockWidgetContents->sizePolicy().hasHeightForWidth());
        dockWidgetContents->setSizePolicy(sizePolicy);
        dockWidgetContents->setMinimumSize(QSize(0, 0));
        QIcon icon;
        icon.addFile(QString::fromUtf8("icons/jigsaw.png"), QSize(), QIcon::Normal, QIcon::Off);
        dockWidgetContents->setWindowIcon(icon);
        verticalLayout_3 = new QVBoxLayout(dockWidgetContents);
        verticalLayout_3->setObjectName(QString::fromUtf8("verticalLayout_3"));
        scrollArea = new QScrollArea(dockWidgetContents);
        scrollArea->setObjectName(QString::fromUtf8("scrollArea"));
        scrollArea->setWidgetResizable(true);
        scrollAreaWidgetContents = new QWidget();
        scrollAreaWidgetContents->setObjectName(QString::fromUtf8("scrollAreaWidgetContents"));
        scrollAreaWidgetContents->setGeometry(QRect(0, 0, 618, 547));
        horizontalLayout_4 = new QHBoxLayout(scrollAreaWidgetContents);
        horizontalLayout_4->setObjectName(QString::fromUtf8("horizontalLayout_4"));
        verticalLayout_2 = new QVBoxLayout();
        verticalLayout_2->setObjectName(QString::fromUtf8("verticalLayout_2"));
        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        statusLabel = new QLabel(scrollAreaWidgetContents);
        statusLabel->setObjectName(QString::fromUtf8("statusLabel"));

        horizontalLayout->addWidget(statusLabel);

        statusOutputLabel = new QLabel(scrollAreaWidgetContents);
        statusOutputLabel->setObjectName(QString::fromUtf8("statusOutputLabel"));

        horizontalLayout->addWidget(statusOutputLabel);


        verticalLayout_2->addLayout(horizontalLayout);

        verticalSpacer_3 = new QSpacerItem(20, 18, QSizePolicy::Minimum, QSizePolicy::Preferred);

        verticalLayout_2->addItem(verticalSpacer_3);

        horizontalLayout_2 = new QHBoxLayout();
        horizontalLayout_2->setObjectName(QString::fromUtf8("horizontalLayout_2"));
        iterationLabel = new QLabel(scrollAreaWidgetContents);
        iterationLabel->setObjectName(QString::fromUtf8("iterationLabel"));
        iterationLabel->setTextFormat(Qt::PlainText);
        iterationLabel->setAlignment(Qt::AlignCenter);

        horizontalLayout_2->addWidget(iterationLabel);

        iterationLcdNumber = new QLCDNumber(scrollAreaWidgetContents);
        iterationLcdNumber->setObjectName(QString::fromUtf8("iterationLcdNumber"));
        QSizePolicy sizePolicy1(QSizePolicy::Preferred, QSizePolicy::Preferred);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(iterationLcdNumber->sizePolicy().hasHeightForWidth());
        iterationLcdNumber->setSizePolicy(sizePolicy1);
        iterationLcdNumber->setAutoFillBackground(true);
        iterationLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        horizontalLayout_2->addWidget(iterationLcdNumber);

        pointLabel = new QLabel(scrollAreaWidgetContents);
        pointLabel->setObjectName(QString::fromUtf8("pointLabel"));

        horizontalLayout_2->addWidget(pointLabel);

        pointLcdNumber = new QLCDNumber(scrollAreaWidgetContents);
        pointLcdNumber->setObjectName(QString::fromUtf8("pointLcdNumber"));
        sizePolicy1.setHeightForWidth(pointLcdNumber->sizePolicy().hasHeightForWidth());
        pointLcdNumber->setSizePolicy(sizePolicy1);
        pointLcdNumber->setAutoFillBackground(true);
        pointLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        horizontalLayout_2->addWidget(pointLcdNumber);


        verticalLayout_2->addLayout(horizontalLayout_2);

        verticalSpacer = new QSpacerItem(20, 20, QSizePolicy::Minimum, QSizePolicy::Preferred);

        verticalLayout_2->addItem(verticalSpacer);

        horizontalLayout_3 = new QHBoxLayout();
        horizontalLayout_3->setObjectName(QString::fromUtf8("horizontalLayout_3"));
        groupBox = new QGroupBox(scrollAreaWidgetContents);
        groupBox->setObjectName(QString::fromUtf8("groupBox"));
        sizePolicy1.setHeightForWidth(groupBox->sizePolicy().hasHeightForWidth());
        groupBox->setSizePolicy(sizePolicy1);
        groupBox->setAutoFillBackground(true);
        groupBox->setAlignment(Qt::AlignCenter);
        gridLayout = new QGridLayout(groupBox);
        gridLayout->setObjectName(QString::fromUtf8("gridLayout"));
        measuresLcdNumber = new QLCDNumber(groupBox);
        measuresLcdNumber->setObjectName(QString::fromUtf8("measuresLcdNumber"));
        sizePolicy1.setHeightForWidth(measuresLcdNumber->sizePolicy().hasHeightForWidth());
        measuresLcdNumber->setSizePolicy(sizePolicy1);
        measuresLcdNumber->setAutoFillBackground(false);
        measuresLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        gridLayout->addWidget(measuresLcdNumber, 2, 1, 1, 1);

        pointsLcdNumber = new QLCDNumber(groupBox);
        pointsLcdNumber->setObjectName(QString::fromUtf8("pointsLcdNumber"));
        sizePolicy1.setHeightForWidth(pointsLcdNumber->sizePolicy().hasHeightForWidth());
        pointsLcdNumber->setSizePolicy(sizePolicy1);
        pointsLcdNumber->setAutoFillBackground(false);
        pointsLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        gridLayout->addWidget(pointsLcdNumber, 1, 1, 1, 1);

        imagesLcdNumber = new QLCDNumber(groupBox);
        imagesLcdNumber->setObjectName(QString::fromUtf8("imagesLcdNumber"));
        imagesLcdNumber->setAutoFillBackground(false);
        imagesLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        gridLayout->addWidget(imagesLcdNumber, 0, 1, 1, 1);

        label_3 = new QLabel(groupBox);
        label_3->setObjectName(QString::fromUtf8("label_3"));

        gridLayout->addWidget(label_3, 0, 0, 1, 1, Qt::AlignRight);

        label_6 = new QLabel(groupBox);
        label_6->setObjectName(QString::fromUtf8("label_6"));

        gridLayout->addWidget(label_6, 2, 0, 1, 1, Qt::AlignRight);

        label_5 = new QLabel(groupBox);
        label_5->setObjectName(QString::fromUtf8("label_5"));

        gridLayout->addWidget(label_5, 1, 0, 1, 1, Qt::AlignRight);


        horizontalLayout_3->addWidget(groupBox);

        rmsAdjustedPointSigmasGroupBox = new QGroupBox(scrollAreaWidgetContents);
        rmsAdjustedPointSigmasGroupBox->setObjectName(QString::fromUtf8("rmsAdjustedPointSigmasGroupBox"));
        rmsAdjustedPointSigmasGroupBox->setEnabled(true);
        sizePolicy1.setHeightForWidth(rmsAdjustedPointSigmasGroupBox->sizePolicy().hasHeightForWidth());
        rmsAdjustedPointSigmasGroupBox->setSizePolicy(sizePolicy1);
        rmsAdjustedPointSigmasGroupBox->setAutoFillBackground(true);
        rmsAdjustedPointSigmasGroupBox->setAlignment(Qt::AlignCenter);
        gridLayout_2 = new QGridLayout(rmsAdjustedPointSigmasGroupBox);
        gridLayout_2->setObjectName(QString::fromUtf8("gridLayout_2"));
        radiusLcdLabel = new QLabel(rmsAdjustedPointSigmasGroupBox);
        radiusLcdLabel->setObjectName(QString::fromUtf8("radiusLcdLabel"));
        radiusLcdLabel->setEnabled(true);

        gridLayout_2->addWidget(radiusLcdLabel, 2, 0, 1, 1, Qt::AlignRight);

        label_4 = new QLabel(rmsAdjustedPointSigmasGroupBox);
        label_4->setObjectName(QString::fromUtf8("label_4"));

        gridLayout_2->addWidget(label_4, 0, 0, 1, 1, Qt::AlignRight);

        label_7 = new QLabel(rmsAdjustedPointSigmasGroupBox);
        label_7->setObjectName(QString::fromUtf8("label_7"));

        gridLayout_2->addWidget(label_7, 1, 0, 1, 1, Qt::AlignRight);

        latitudeLcdNumber = new QLCDNumber(rmsAdjustedPointSigmasGroupBox);
        latitudeLcdNumber->setObjectName(QString::fromUtf8("latitudeLcdNumber"));
        sizePolicy1.setHeightForWidth(latitudeLcdNumber->sizePolicy().hasHeightForWidth());
        latitudeLcdNumber->setSizePolicy(sizePolicy1);
        latitudeLcdNumber->setSmallDecimalPoint(false);
        latitudeLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        gridLayout_2->addWidget(latitudeLcdNumber, 0, 1, 1, 1);

        longitudeLcdNumber = new QLCDNumber(rmsAdjustedPointSigmasGroupBox);
        longitudeLcdNumber->setObjectName(QString::fromUtf8("longitudeLcdNumber"));
        sizePolicy1.setHeightForWidth(longitudeLcdNumber->sizePolicy().hasHeightForWidth());
        longitudeLcdNumber->setSizePolicy(sizePolicy1);
        longitudeLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        gridLayout_2->addWidget(longitudeLcdNumber, 1, 1, 1, 1);

        radiusLcdNumber = new QLCDNumber(rmsAdjustedPointSigmasGroupBox);
        radiusLcdNumber->setObjectName(QString::fromUtf8("radiusLcdNumber"));
        radiusLcdNumber->setEnabled(true);
        sizePolicy1.setHeightForWidth(radiusLcdNumber->sizePolicy().hasHeightForWidth());
        radiusLcdNumber->setSizePolicy(sizePolicy1);
        radiusLcdNumber->setSegmentStyle(QLCDNumber::Flat);

        gridLayout_2->addWidget(radiusLcdNumber, 2, 1, 1, 1);

        label_4->raise();
        label_7->raise();
        radiusLcdLabel->raise();
        latitudeLcdNumber->raise();
        longitudeLcdNumber->raise();
        radiusLcdNumber->raise();

        horizontalLayout_3->addWidget(rmsAdjustedPointSigmasGroupBox);


        verticalLayout_2->addLayout(horizontalLayout_3);

        verticalSpacer_2 = new QSpacerItem(20, 20, QSizePolicy::Minimum, QSizePolicy::Preferred);

        verticalLayout_2->addItem(verticalSpacer_2);

        verticalLayout = new QVBoxLayout();
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        detachedLabelsCheckBox = new QCheckBox(scrollAreaWidgetContents);
        detachedLabelsCheckBox->setObjectName(QString::fromUtf8("detachedLabelsCheckBox"));
        detachedLabelsCheckBox->setEnabled(true);
        detachedLabelsCheckBox->setChecked(true);
        detachedLabelsCheckBox->setTristate(false);

        verticalLayout->addWidget(detachedLabelsCheckBox);

        useLastSettings = new QCheckBox(scrollAreaWidgetContents);
        useLastSettings->setObjectName(QString::fromUtf8("useLastSettings"));
        sizePolicy1.setHeightForWidth(useLastSettings->sizePolicy().hasHeightForWidth());
        useLastSettings->setSizePolicy(sizePolicy1);

        verticalLayout->addWidget(useLastSettings);

        horizontalLayout_8 = new QHBoxLayout();
        horizontalLayout_8->setObjectName(QString::fromUtf8("horizontalLayout_8"));
        JigsawSetupButton = new QPushButton(scrollAreaWidgetContents);
        JigsawSetupButton->setObjectName(QString::fromUtf8("JigsawSetupButton"));

        horizontalLayout_8->addWidget(JigsawSetupButton);

        horizontalSpacer_2 = new QSpacerItem(40, 20, QSizePolicy::Preferred, QSizePolicy::Minimum);

        horizontalLayout_8->addItem(horizontalSpacer_2);

        JigsawRunButton = new QPushButton(scrollAreaWidgetContents);
        JigsawRunButton->setObjectName(QString::fromUtf8("JigsawRunButton"));
        JigsawRunButton->setEnabled(false);

        horizontalLayout_8->addWidget(JigsawRunButton);

        horizontalSpacer = new QSpacerItem(40, 20, QSizePolicy::Preferred, QSizePolicy::Minimum);

        horizontalLayout_8->addItem(horizontalSpacer);

        JigsawAcceptButton = new QPushButton(scrollAreaWidgetContents);
        JigsawAcceptButton->setObjectName(QString::fromUtf8("JigsawAcceptButton"));
        JigsawAcceptButton->setEnabled(false);

        horizontalLayout_8->addWidget(JigsawAcceptButton);


        verticalLayout->addLayout(horizontalLayout_8);


        verticalLayout_2->addLayout(verticalLayout);

        verticalSpacer_4 = new QSpacerItem(20, 18, QSizePolicy::Minimum, QSizePolicy::Expanding);

        verticalLayout_2->addItem(verticalSpacer_4);

        statusUpdateScrollArea = new QScrollArea(scrollAreaWidgetContents);
        statusUpdateScrollArea->setObjectName(QString::fromUtf8("statusUpdateScrollArea"));
        QSizePolicy sizePolicy2(QSizePolicy::Expanding, QSizePolicy::Expanding);
        sizePolicy2.setHorizontalStretch(0);
        sizePolicy2.setVerticalStretch(2);
        sizePolicy2.setHeightForWidth(statusUpdateScrollArea->sizePolicy().hasHeightForWidth());
        statusUpdateScrollArea->setSizePolicy(sizePolicy2);
        statusUpdateScrollArea->setFocusPolicy(Qt::NoFocus);
        statusUpdateScrollArea->setFrameShape(QFrame::Box);
        statusUpdateScrollArea->setSizeAdjustPolicy(QAbstractScrollArea::AdjustIgnored);
        statusUpdateScrollArea->setWidgetResizable(true);
        statusUpdatesLabel = new QLabel();
        statusUpdatesLabel->setObjectName(QString::fromUtf8("statusUpdatesLabel"));
        statusUpdatesLabel->setGeometry(QRect(0, 0, 594, 151));
        QSizePolicy sizePolicy3(QSizePolicy::Expanding, QSizePolicy::Expanding);
        sizePolicy3.setHorizontalStretch(1);
        sizePolicy3.setVerticalStretch(2);
        sizePolicy3.setHeightForWidth(statusUpdatesLabel->sizePolicy().hasHeightForWidth());
        statusUpdatesLabel->setSizePolicy(sizePolicy3);
        statusUpdatesLabel->setWordWrap(true);
        statusUpdateScrollArea->setWidget(statusUpdatesLabel);

        verticalLayout_2->addWidget(statusUpdateScrollArea);


        horizontalLayout_4->addLayout(verticalLayout_2);

        scrollArea->setWidget(scrollAreaWidgetContents);

        verticalLayout_3->addWidget(scrollArea);

        JigsawRunWidget->setWidget(dockWidgetContents);

        retranslateUi(JigsawRunWidget);

        QMetaObject::connectSlotsByName(JigsawRunWidget);
    } // setupUi

    void retranslateUi(QDockWidget *JigsawRunWidget)
    {
        JigsawRunWidget->setWindowTitle(QCoreApplication::translate("JigsawRunWidget", "&Jigsaw", nullptr));
        dockWidgetContents->setWindowTitle(QCoreApplication::translate("JigsawRunWidget", "Jigsaw", nullptr));
        statusLabel->setText(QCoreApplication::translate("JigsawRunWidget", "Status:", nullptr));
        statusOutputLabel->setText(QString());
        iterationLabel->setText(QCoreApplication::translate("JigsawRunWidget", "Iteration", nullptr));
        pointLabel->setText(QCoreApplication::translate("JigsawRunWidget", "Point", nullptr));
        groupBox->setTitle(QCoreApplication::translate("JigsawRunWidget", "   Control Network   ", nullptr));
        label_3->setText(QCoreApplication::translate("JigsawRunWidget", "Images", nullptr));
        label_6->setText(QCoreApplication::translate("JigsawRunWidget", "Measures", nullptr));
        label_5->setText(QCoreApplication::translate("JigsawRunWidget", "Points", nullptr));
        rmsAdjustedPointSigmasGroupBox->setTitle(QCoreApplication::translate("JigsawRunWidget", "RMS Adj Point Sigmas", nullptr));
        radiusLcdLabel->setText(QCoreApplication::translate("JigsawRunWidget", "Radius", nullptr));
        label_4->setText(QCoreApplication::translate("JigsawRunWidget", "Latitude", nullptr));
        label_7->setText(QCoreApplication::translate("JigsawRunWidget", "Longitude", nullptr));
        detachedLabelsCheckBox->setText(QCoreApplication::translate("JigsawRunWidget", "Write Detached Image Labels on Accept", nullptr));
        useLastSettings->setText(QCoreApplication::translate("JigsawRunWidget", "Use Last Accepted Settings", nullptr));
        JigsawSetupButton->setText(QCoreApplication::translate("JigsawRunWidget", "&Setup", nullptr));
        JigsawRunButton->setText(QCoreApplication::translate("JigsawRunWidget", "&Run", nullptr));
        JigsawAcceptButton->setText(QCoreApplication::translate("JigsawRunWidget", "Accept", nullptr));
        statusUpdatesLabel->setText(QCoreApplication::translate("JigsawRunWidget", "Welcome to Jigsaw", nullptr));
    } // retranslateUi

};

namespace Ui {
    class JigsawRunWidget: public Ui_JigsawRunWidget {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_JIGSAWRUNWIDGET_H
