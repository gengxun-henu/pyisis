/********************************************************************************
** Form generated from reading UI file 'JigsawSetupDialog.ui'
**
** Created by: Qt User Interface Compiler version 5.15.8
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_JIGSAWSETUPDIALOG_H
#define UI_JIGSAWSETUPDIALOG_H

#include <QtCore/QVariant>
#include <QtGui/QIcon>
#include <QtWidgets/QApplication>
#include <QtWidgets/QButtonGroup>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QDialog>
#include <QtWidgets/QDialogButtonBox>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QGroupBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QRadioButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QSpinBox>
#include <QtWidgets/QTabWidget>
#include <QtWidgets/QTableWidget>
#include <QtWidgets/QTreeView>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_JigsawSetupDialog
{
public:
    QWidget *layoutWidget;
    QHBoxLayout *horizontalLayout_3;
    QVBoxLayout *verticalLayout_3;
    QVBoxLayout *verticalLayout;
    QHBoxLayout *horizontalLayout;
    QTabWidget *JigsawSetup;
    QWidget *generalSettingsTab;
    QGridLayout *gridLayout_2;
    QHBoxLayout *horizontalLayout_7;
    QVBoxLayout *verticalLayout_6;
    QVBoxLayout *verticalLayout_8;
    QLabel *label;
    QGroupBox *groupBox_6;
    QGridLayout *gridLayout_11;
    QLineEdit *outputControlNetLineEdit;
    QLabel *outputControlNetLabel;
    QLabel *inputControlNetLabel;
    QComboBox *inputControlNetCombo;
    QSpacerItem *verticalSpacer_5;
    QLabel *label_2;
    QGroupBox *groupBox_8;
    QGridLayout *gridLayout_4;
    QSpacerItem *horizontalSpacer_7;
    QSpacerItem *horizontalSpacer;
    QLineEdit *outlierRejectionMultiplierLineEdit;
    QCheckBox *outlierRejectionCheckBox;
    QGroupBox *groupBox_7;
    QGridLayout *gridLayout_14;
    QComboBox *maximumLikelihoodModel1ComboBox;
    QLineEdit *maximumLikelihoodModel3QuantileLineEdit;
    QLineEdit *maximumLikelihoodModel2QuantileLineEdit;
    QLineEdit *maximumLikelihoodModel1QuantileLineEdit;
    QComboBox *maximumLikelihoodModel2ComboBox;
    QLabel *maximumLikelihoodModel2Label;
    QComboBox *maximumLikelihoodModel3ComboBox;
    QLabel *maximumLikelihoodModel1Label;
    QLabel *maximumLikelihoodModel3Label;
    QLabel *maxLikelihoodEstimationLabel;
    QLabel *CQuantileLabel;
    QSpacerItem *horizontalSpacer_2;
    QVBoxLayout *verticalLayout_7;
    QLabel *label_3;
    QGroupBox *groupBox_3;
    QGridLayout *gridLayout_17;
    QLineEdit *sigma0ThresholdLineEdit;
    QLabel *sigma0ThresholdLabel;
    QLineEdit *maximumIterationsLineEdit;
    QSpacerItem *horizontalSpacer_6;
    QLabel *maximumIterationsLabel;
    QSpacerItem *horizontalSpacer_5;
    QSpacerItem *verticalSpacer_3;
    QLabel *label_4;
    QGroupBox *groupBox_4;
    QGridLayout *gridLayout_13;
    QSpacerItem *horizontalSpacer_3;
    QLineEdit *pointLongitudeSigmaLineEdit;
    QSpacerItem *horizontalSpacer_4;
    QLabel *pointLongitudeSigmaLabel;
    QLineEdit *pointLatitudeSigmaLineEdit;
    QLineEdit *pointRadiusSigmaLineEdit;
    QCheckBox *pointRadiusSigmaCheckBox;
    QLabel *pointLatitudeSigmaLabel;
    QSpacerItem *verticalSpacer_4;
    QLabel *label_5;
    QGroupBox *groupBox_5;
    QVBoxLayout *verticalLayout_4;
    QCheckBox *observationModeCheckBox;
    QCheckBox *errorPropagationCheckBox;
    QWidget *observationSolveSettingsTab;
    QGridLayout *gridLayout_8;
    QGroupBox *groupBox;
    QGridLayout *gridLayout_9;
    QCheckBox *hermiteSplineCheckBox;
    QTableWidget *positionAprioriSigmaTable;
    QLabel *spkSolveDegreeLabel;
    QSpinBox *spkDegreeSpinBox;
    QSpinBox *spkSolveDegreeSpinBox;
    QLabel *spkDegreeLabel;
    QComboBox *positionComboBox;
    QPushButton *applySettingsPushButton;
    QTreeView *treeView;
    QGroupBox *groupBox_2;
    QGridLayout *gridLayout_10;
    QCheckBox *twistCheckBox;
    QLabel *ckSolveDegreeLabel;
    QLabel *ckDegreeLabel;
    QSpinBox *ckDegreeSpinBox;
    QCheckBox *fitOverPointingCheckBox;
    QTableWidget *pointingAprioriSigmaTable;
    QSpinBox *ckSolveDegreeSpinBox;
    QComboBox *pointingComboBox;
    QWidget *targetBodyTab;
    QGridLayout *gridLayout;
    QHBoxLayout *horizontalLayout_4;
    QLabel *targetLabel;
    QComboBox *targetBodyComboBox;
    QSpacerItem *verticalSpacer_2;
    QVBoxLayout *verticalLayout_2;
    QGroupBox *targetParametersGroupBox;
    QGridLayout *gridLayout_12;
    QLineEdit *primeMeridianOffsetLineEdit;
    QLineEdit *spinRateSigmaLineEdit;
    QLineEdit *rightAscensionVelocityLineEdit;
    QLineEdit *declinationVelocityLineEdit;
    QLineEdit *declinationSigmaLineEdit;
    QLabel *sigmaLabel;
    QLineEdit *declinationLineEdit;
    QLabel *valueLabel;
    QLineEdit *rightAscensionSigmaLineEdit;
    QCheckBox *poleRaCheckBox;
    QCheckBox *poleDecCheckBox;
    QLineEdit *rightAscensionVelocitySigmaLineEdit;
    QLineEdit *declinationVelocitySigmaLineEdit;
    QCheckBox *poleRaVelocityCheckBox;
    QCheckBox *poleDecVelocityCheckBox;
    QCheckBox *primeMeridianOffsetCheckBox;
    QLineEdit *primeMeridianOffsetSigmaLineEdit;
    QCheckBox *spinRateCheckBox;
    QLineEdit *spinRateLineEdit;
    QLineEdit *rightAscensionLineEdit;
    QGroupBox *radiiGroupBox;
    QGridLayout *gridLayout_6;
    QGridLayout *gridLayout_5;
    QRadioButton *meanRadiusRadioButton;
    QLabel *bRadiusLabel;
    QLabel *cRadiusLabel;
    QLineEdit *aRadiusLineEdit;
    QLineEdit *aRadiusSigmaLineEdit;
    QRadioButton *triaxialRadiiRadioButton;
    QLineEdit *cRadiusLineEdit;
    QLineEdit *meanRadiusLineEdit;
    QLineEdit *bRadiusSigmaLineEdit;
    QLineEdit *cRadiusSigmaLineEdit;
    QLineEdit *meanRadiusSigmaLineEdit;
    QLineEdit *bRadiusLineEdit;
    QLabel *aRadiusLabel;
    QRadioButton *noneRadiiRadioButton;
    QSpacerItem *verticalSpacer;
    QLabel *targetParametersMessage;
    QDialogButtonBox *okCloseButtonBox;
    QButtonGroup *radiiButtonGroup;

    void setupUi(QDialog *JigsawSetupDialog)
    {
        if (JigsawSetupDialog->objectName().isEmpty())
            JigsawSetupDialog->setObjectName(QString::fromUtf8("JigsawSetupDialog"));
        JigsawSetupDialog->resize(1000, 700);
        QSizePolicy sizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(JigsawSetupDialog->sizePolicy().hasHeightForWidth());
        JigsawSetupDialog->setSizePolicy(sizePolicy);
        QIcon icon;
        icon.addFile(QString::fromUtf8("icons/settings.png"), QSize(), QIcon::Normal, QIcon::Off);
        JigsawSetupDialog->setWindowIcon(icon);
        JigsawSetupDialog->setInputMethodHints(Qt::ImhNone);
        layoutWidget = new QWidget(JigsawSetupDialog);
        layoutWidget->setObjectName(QString::fromUtf8("layoutWidget"));
        layoutWidget->setGeometry(QRect(0, 0, 2, 2));
        horizontalLayout_3 = new QHBoxLayout(layoutWidget);
        horizontalLayout_3->setObjectName(QString::fromUtf8("horizontalLayout_3"));
        horizontalLayout_3->setContentsMargins(0, 0, 0, 0);
        verticalLayout_3 = new QVBoxLayout(JigsawSetupDialog);
        verticalLayout_3->setObjectName(QString::fromUtf8("verticalLayout_3"));
        verticalLayout = new QVBoxLayout();
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        JigsawSetup = new QTabWidget(JigsawSetupDialog);
        JigsawSetup->setObjectName(QString::fromUtf8("JigsawSetup"));
        JigsawSetup->setEnabled(true);
        QSizePolicy sizePolicy1(QSizePolicy::Preferred, QSizePolicy::Preferred);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(JigsawSetup->sizePolicy().hasHeightForWidth());
        JigsawSetup->setSizePolicy(sizePolicy1);
        generalSettingsTab = new QWidget();
        generalSettingsTab->setObjectName(QString::fromUtf8("generalSettingsTab"));
        gridLayout_2 = new QGridLayout(generalSettingsTab);
        gridLayout_2->setObjectName(QString::fromUtf8("gridLayout_2"));
        horizontalLayout_7 = new QHBoxLayout();
        horizontalLayout_7->setObjectName(QString::fromUtf8("horizontalLayout_7"));
        verticalLayout_6 = new QVBoxLayout();
        verticalLayout_6->setObjectName(QString::fromUtf8("verticalLayout_6"));
        verticalLayout_8 = new QVBoxLayout();
        verticalLayout_8->setObjectName(QString::fromUtf8("verticalLayout_8"));
        label = new QLabel(generalSettingsTab);
        label->setObjectName(QString::fromUtf8("label"));
        label->setMinimumSize(QSize(0, 15));
        label->setScaledContents(true);

        verticalLayout_8->addWidget(label);

        groupBox_6 = new QGroupBox(generalSettingsTab);
        groupBox_6->setObjectName(QString::fromUtf8("groupBox_6"));
        QSizePolicy sizePolicy2(QSizePolicy::Expanding, QSizePolicy::Expanding);
        sizePolicy2.setHorizontalStretch(0);
        sizePolicy2.setVerticalStretch(0);
        sizePolicy2.setHeightForWidth(groupBox_6->sizePolicy().hasHeightForWidth());
        groupBox_6->setSizePolicy(sizePolicy2);
        groupBox_6->setMinimumSize(QSize(0, 0));
        groupBox_6->setAutoFillBackground(false);
        groupBox_6->setAlignment(Qt::AlignCenter);
        gridLayout_11 = new QGridLayout(groupBox_6);
        gridLayout_11->setObjectName(QString::fromUtf8("gridLayout_11"));
        outputControlNetLineEdit = new QLineEdit(groupBox_6);
        outputControlNetLineEdit->setObjectName(QString::fromUtf8("outputControlNetLineEdit"));
        QSizePolicy sizePolicy3(QSizePolicy::Expanding, QSizePolicy::Fixed);
        sizePolicy3.setHorizontalStretch(0);
        sizePolicy3.setVerticalStretch(0);
        sizePolicy3.setHeightForWidth(outputControlNetLineEdit->sizePolicy().hasHeightForWidth());
        outputControlNetLineEdit->setSizePolicy(sizePolicy3);

        gridLayout_11->addWidget(outputControlNetLineEdit, 1, 1, 1, 1);

        outputControlNetLabel = new QLabel(groupBox_6);
        outputControlNetLabel->setObjectName(QString::fromUtf8("outputControlNetLabel"));
        QSizePolicy sizePolicy4(QSizePolicy::Expanding, QSizePolicy::Minimum);
        sizePolicy4.setHorizontalStretch(0);
        sizePolicy4.setVerticalStretch(0);
        sizePolicy4.setHeightForWidth(outputControlNetLabel->sizePolicy().hasHeightForWidth());
        outputControlNetLabel->setSizePolicy(sizePolicy4);
        outputControlNetLabel->setMaximumSize(QSize(150, 16777215));
        outputControlNetLabel->setTextFormat(Qt::RichText);

        gridLayout_11->addWidget(outputControlNetLabel, 1, 0, 1, 1);

        inputControlNetLabel = new QLabel(groupBox_6);
        inputControlNetLabel->setObjectName(QString::fromUtf8("inputControlNetLabel"));
        sizePolicy4.setHeightForWidth(inputControlNetLabel->sizePolicy().hasHeightForWidth());
        inputControlNetLabel->setSizePolicy(sizePolicy4);
        inputControlNetLabel->setMaximumSize(QSize(150, 16777215));

        gridLayout_11->addWidget(inputControlNetLabel, 0, 0, 1, 1);

        inputControlNetCombo = new QComboBox(groupBox_6);
        inputControlNetCombo->setObjectName(QString::fromUtf8("inputControlNetCombo"));
        sizePolicy3.setHeightForWidth(inputControlNetCombo->sizePolicy().hasHeightForWidth());
        inputControlNetCombo->setSizePolicy(sizePolicy3);
        inputControlNetCombo->setSizeAdjustPolicy(QComboBox::AdjustToContents);

        gridLayout_11->addWidget(inputControlNetCombo, 0, 1, 1, 1);


        verticalLayout_8->addWidget(groupBox_6);

        verticalSpacer_5 = new QSpacerItem(20, 50, QSizePolicy::Minimum, QSizePolicy::Preferred);

        verticalLayout_8->addItem(verticalSpacer_5);

        label_2 = new QLabel(generalSettingsTab);
        label_2->setObjectName(QString::fromUtf8("label_2"));
        label_2->setMinimumSize(QSize(0, 15));

        verticalLayout_8->addWidget(label_2);


        verticalLayout_6->addLayout(verticalLayout_8);

        groupBox_8 = new QGroupBox(generalSettingsTab);
        groupBox_8->setObjectName(QString::fromUtf8("groupBox_8"));
        sizePolicy1.setHeightForWidth(groupBox_8->sizePolicy().hasHeightForWidth());
        groupBox_8->setSizePolicy(sizePolicy1);
        gridLayout_4 = new QGridLayout(groupBox_8);
        gridLayout_4->setObjectName(QString::fromUtf8("gridLayout_4"));
        horizontalSpacer_7 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_4->addItem(horizontalSpacer_7, 1, 3, 1, 1);

        horizontalSpacer = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_4->addItem(horizontalSpacer, 1, 0, 1, 1);

        outlierRejectionMultiplierLineEdit = new QLineEdit(groupBox_8);
        outlierRejectionMultiplierLineEdit->setObjectName(QString::fromUtf8("outlierRejectionMultiplierLineEdit"));
        outlierRejectionMultiplierLineEdit->setEnabled(false);
        QSizePolicy sizePolicy5(QSizePolicy::Preferred, QSizePolicy::Fixed);
        sizePolicy5.setHorizontalStretch(0);
        sizePolicy5.setVerticalStretch(0);
        sizePolicy5.setHeightForWidth(outlierRejectionMultiplierLineEdit->sizePolicy().hasHeightForWidth());
        outlierRejectionMultiplierLineEdit->setSizePolicy(sizePolicy5);
        outlierRejectionMultiplierLineEdit->setMaximumSize(QSize(100, 16777215));
        outlierRejectionMultiplierLineEdit->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_4->addWidget(outlierRejectionMultiplierLineEdit, 1, 2, 1, 1);

        outlierRejectionCheckBox = new QCheckBox(groupBox_8);
        outlierRejectionCheckBox->setObjectName(QString::fromUtf8("outlierRejectionCheckBox"));
        sizePolicy5.setHeightForWidth(outlierRejectionCheckBox->sizePolicy().hasHeightForWidth());
        outlierRejectionCheckBox->setSizePolicy(sizePolicy5);
        outlierRejectionCheckBox->setMinimumSize(QSize(0, 0));
        outlierRejectionCheckBox->setMaximumSize(QSize(1000, 16777215));
        outlierRejectionCheckBox->setLayoutDirection(Qt::LeftToRight);

        gridLayout_4->addWidget(outlierRejectionCheckBox, 1, 1, 1, 1);


        verticalLayout_6->addWidget(groupBox_8);

        groupBox_7 = new QGroupBox(generalSettingsTab);
        groupBox_7->setObjectName(QString::fromUtf8("groupBox_7"));
        sizePolicy2.setHeightForWidth(groupBox_7->sizePolicy().hasHeightForWidth());
        groupBox_7->setSizePolicy(sizePolicy2);
        groupBox_7->setMinimumSize(QSize(0, 0));
        groupBox_7->setAutoFillBackground(false);
        groupBox_7->setAlignment(Qt::AlignCenter);
        groupBox_7->setFlat(false);
        groupBox_7->setCheckable(false);
        gridLayout_14 = new QGridLayout(groupBox_7);
        gridLayout_14->setObjectName(QString::fromUtf8("gridLayout_14"));
        maximumLikelihoodModel1ComboBox = new QComboBox(groupBox_7);
        maximumLikelihoodModel1ComboBox->addItem(QString());
        maximumLikelihoodModel1ComboBox->addItem(QString());
        maximumLikelihoodModel1ComboBox->addItem(QString());
        maximumLikelihoodModel1ComboBox->setObjectName(QString::fromUtf8("maximumLikelihoodModel1ComboBox"));
        sizePolicy3.setHeightForWidth(maximumLikelihoodModel1ComboBox->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel1ComboBox->setSizePolicy(sizePolicy3);

        gridLayout_14->addWidget(maximumLikelihoodModel1ComboBox, 6, 1, 1, 2);

        maximumLikelihoodModel3QuantileLineEdit = new QLineEdit(groupBox_7);
        maximumLikelihoodModel3QuantileLineEdit->setObjectName(QString::fromUtf8("maximumLikelihoodModel3QuantileLineEdit"));
        maximumLikelihoodModel3QuantileLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(maximumLikelihoodModel3QuantileLineEdit->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel3QuantileLineEdit->setSizePolicy(sizePolicy3);
        maximumLikelihoodModel3QuantileLineEdit->setMaximumSize(QSize(100, 16777215));

        gridLayout_14->addWidget(maximumLikelihoodModel3QuantileLineEdit, 8, 3, 1, 1);

        maximumLikelihoodModel2QuantileLineEdit = new QLineEdit(groupBox_7);
        maximumLikelihoodModel2QuantileLineEdit->setObjectName(QString::fromUtf8("maximumLikelihoodModel2QuantileLineEdit"));
        maximumLikelihoodModel2QuantileLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(maximumLikelihoodModel2QuantileLineEdit->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel2QuantileLineEdit->setSizePolicy(sizePolicy3);
        maximumLikelihoodModel2QuantileLineEdit->setMaximumSize(QSize(100, 16777215));

        gridLayout_14->addWidget(maximumLikelihoodModel2QuantileLineEdit, 7, 3, 1, 1);

        maximumLikelihoodModel1QuantileLineEdit = new QLineEdit(groupBox_7);
        maximumLikelihoodModel1QuantileLineEdit->setObjectName(QString::fromUtf8("maximumLikelihoodModel1QuantileLineEdit"));
        maximumLikelihoodModel1QuantileLineEdit->setEnabled(false);
        sizePolicy5.setHeightForWidth(maximumLikelihoodModel1QuantileLineEdit->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel1QuantileLineEdit->setSizePolicy(sizePolicy5);
        maximumLikelihoodModel1QuantileLineEdit->setMaximumSize(QSize(100, 16777215));

        gridLayout_14->addWidget(maximumLikelihoodModel1QuantileLineEdit, 6, 3, 1, 1);

        maximumLikelihoodModel2ComboBox = new QComboBox(groupBox_7);
        maximumLikelihoodModel2ComboBox->addItem(QString());
        maximumLikelihoodModel2ComboBox->addItem(QString());
        maximumLikelihoodModel2ComboBox->addItem(QString());
        maximumLikelihoodModel2ComboBox->addItem(QString());
        maximumLikelihoodModel2ComboBox->addItem(QString());
        maximumLikelihoodModel2ComboBox->setObjectName(QString::fromUtf8("maximumLikelihoodModel2ComboBox"));
        maximumLikelihoodModel2ComboBox->setEnabled(false);
        sizePolicy3.setHeightForWidth(maximumLikelihoodModel2ComboBox->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel2ComboBox->setSizePolicy(sizePolicy3);

        gridLayout_14->addWidget(maximumLikelihoodModel2ComboBox, 7, 1, 1, 2);

        maximumLikelihoodModel2Label = new QLabel(groupBox_7);
        maximumLikelihoodModel2Label->setObjectName(QString::fromUtf8("maximumLikelihoodModel2Label"));
        maximumLikelihoodModel2Label->setEnabled(false);
        QSizePolicy sizePolicy6(QSizePolicy::Minimum, QSizePolicy::Fixed);
        sizePolicy6.setHorizontalStretch(0);
        sizePolicy6.setVerticalStretch(0);
        sizePolicy6.setHeightForWidth(maximumLikelihoodModel2Label->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel2Label->setSizePolicy(sizePolicy6);
        maximumLikelihoodModel2Label->setMinimumSize(QSize(0, 0));
        maximumLikelihoodModel2Label->setMaximumSize(QSize(100, 16777215));

        gridLayout_14->addWidget(maximumLikelihoodModel2Label, 7, 0, 1, 1, Qt::AlignRight);

        maximumLikelihoodModel3ComboBox = new QComboBox(groupBox_7);
        maximumLikelihoodModel3ComboBox->addItem(QString());
        maximumLikelihoodModel3ComboBox->addItem(QString());
        maximumLikelihoodModel3ComboBox->addItem(QString());
        maximumLikelihoodModel3ComboBox->addItem(QString());
        maximumLikelihoodModel3ComboBox->addItem(QString());
        maximumLikelihoodModel3ComboBox->setObjectName(QString::fromUtf8("maximumLikelihoodModel3ComboBox"));
        maximumLikelihoodModel3ComboBox->setEnabled(false);
        sizePolicy3.setHeightForWidth(maximumLikelihoodModel3ComboBox->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel3ComboBox->setSizePolicy(sizePolicy3);

        gridLayout_14->addWidget(maximumLikelihoodModel3ComboBox, 8, 1, 1, 2);

        maximumLikelihoodModel1Label = new QLabel(groupBox_7);
        maximumLikelihoodModel1Label->setObjectName(QString::fromUtf8("maximumLikelihoodModel1Label"));
        sizePolicy6.setHeightForWidth(maximumLikelihoodModel1Label->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel1Label->setSizePolicy(sizePolicy6);
        maximumLikelihoodModel1Label->setMinimumSize(QSize(0, 0));
        maximumLikelihoodModel1Label->setMaximumSize(QSize(100, 16777215));

        gridLayout_14->addWidget(maximumLikelihoodModel1Label, 6, 0, 1, 1, Qt::AlignRight);

        maximumLikelihoodModel3Label = new QLabel(groupBox_7);
        maximumLikelihoodModel3Label->setObjectName(QString::fromUtf8("maximumLikelihoodModel3Label"));
        maximumLikelihoodModel3Label->setEnabled(false);
        sizePolicy6.setHeightForWidth(maximumLikelihoodModel3Label->sizePolicy().hasHeightForWidth());
        maximumLikelihoodModel3Label->setSizePolicy(sizePolicy6);
        maximumLikelihoodModel3Label->setMinimumSize(QSize(0, 0));
        maximumLikelihoodModel3Label->setMaximumSize(QSize(100, 16777215));
        maximumLikelihoodModel3Label->setAcceptDrops(false);

        gridLayout_14->addWidget(maximumLikelihoodModel3Label, 8, 0, 1, 1, Qt::AlignRight);

        maxLikelihoodEstimationLabel = new QLabel(groupBox_7);
        maxLikelihoodEstimationLabel->setObjectName(QString::fromUtf8("maxLikelihoodEstimationLabel"));
        sizePolicy3.setHeightForWidth(maxLikelihoodEstimationLabel->sizePolicy().hasHeightForWidth());
        maxLikelihoodEstimationLabel->setSizePolicy(sizePolicy3);

        gridLayout_14->addWidget(maxLikelihoodEstimationLabel, 4, 0, 1, 4);

        CQuantileLabel = new QLabel(groupBox_7);
        CQuantileLabel->setObjectName(QString::fromUtf8("CQuantileLabel"));
        sizePolicy5.setHeightForWidth(CQuantileLabel->sizePolicy().hasHeightForWidth());
        CQuantileLabel->setSizePolicy(sizePolicy5);

        gridLayout_14->addWidget(CQuantileLabel, 5, 3, 1, 1, Qt::AlignHCenter);


        verticalLayout_6->addWidget(groupBox_7);


        horizontalLayout_7->addLayout(verticalLayout_6);

        horizontalSpacer_2 = new QSpacerItem(50, 20, QSizePolicy::Preferred, QSizePolicy::Minimum);

        horizontalLayout_7->addItem(horizontalSpacer_2);

        verticalLayout_7 = new QVBoxLayout();
        verticalLayout_7->setObjectName(QString::fromUtf8("verticalLayout_7"));
        label_3 = new QLabel(generalSettingsTab);
        label_3->setObjectName(QString::fromUtf8("label_3"));
        label_3->setMinimumSize(QSize(0, 20));

        verticalLayout_7->addWidget(label_3);

        groupBox_3 = new QGroupBox(generalSettingsTab);
        groupBox_3->setObjectName(QString::fromUtf8("groupBox_3"));
        QSizePolicy sizePolicy7(QSizePolicy::Minimum, QSizePolicy::Expanding);
        sizePolicy7.setHorizontalStretch(0);
        sizePolicy7.setVerticalStretch(0);
        sizePolicy7.setHeightForWidth(groupBox_3->sizePolicy().hasHeightForWidth());
        groupBox_3->setSizePolicy(sizePolicy7);
        groupBox_3->setMinimumSize(QSize(0, 150));
        groupBox_3->setAutoFillBackground(false);
        groupBox_3->setAlignment(Qt::AlignCenter);
        gridLayout_17 = new QGridLayout(groupBox_3);
        gridLayout_17->setObjectName(QString::fromUtf8("gridLayout_17"));
        sigma0ThresholdLineEdit = new QLineEdit(groupBox_3);
        sigma0ThresholdLineEdit->setObjectName(QString::fromUtf8("sigma0ThresholdLineEdit"));
        sizePolicy3.setHeightForWidth(sigma0ThresholdLineEdit->sizePolicy().hasHeightForWidth());
        sigma0ThresholdLineEdit->setSizePolicy(sizePolicy3);
        sigma0ThresholdLineEdit->setMinimumSize(QSize(78, 0));
        sigma0ThresholdLineEdit->setMaximumSize(QSize(100, 100));
        sigma0ThresholdLineEdit->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_17->addWidget(sigma0ThresholdLineEdit, 0, 2, 1, 1, Qt::AlignRight);

        sigma0ThresholdLabel = new QLabel(groupBox_3);
        sigma0ThresholdLabel->setObjectName(QString::fromUtf8("sigma0ThresholdLabel"));
        sizePolicy5.setHeightForWidth(sigma0ThresholdLabel->sizePolicy().hasHeightForWidth());
        sigma0ThresholdLabel->setSizePolicy(sizePolicy5);
        sigma0ThresholdLabel->setMinimumSize(QSize(150, 0));
        sigma0ThresholdLabel->setMaximumSize(QSize(100, 16777215));

        gridLayout_17->addWidget(sigma0ThresholdLabel, 0, 1, 1, 1, Qt::AlignRight);

        maximumIterationsLineEdit = new QLineEdit(groupBox_3);
        maximumIterationsLineEdit->setObjectName(QString::fromUtf8("maximumIterationsLineEdit"));
        sizePolicy3.setHeightForWidth(maximumIterationsLineEdit->sizePolicy().hasHeightForWidth());
        maximumIterationsLineEdit->setSizePolicy(sizePolicy3);
        maximumIterationsLineEdit->setMaximumSize(QSize(100, 100));
        maximumIterationsLineEdit->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_17->addWidget(maximumIterationsLineEdit, 1, 2, 1, 1);

        horizontalSpacer_6 = new QSpacerItem(10, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_17->addItem(horizontalSpacer_6, 0, 3, 2, 1);

        maximumIterationsLabel = new QLabel(groupBox_3);
        maximumIterationsLabel->setObjectName(QString::fromUtf8("maximumIterationsLabel"));
        sizePolicy5.setHeightForWidth(maximumIterationsLabel->sizePolicy().hasHeightForWidth());
        maximumIterationsLabel->setSizePolicy(sizePolicy5);
        maximumIterationsLabel->setMinimumSize(QSize(150, 0));
        maximumIterationsLabel->setMaximumSize(QSize(100, 16777215));

        gridLayout_17->addWidget(maximumIterationsLabel, 1, 1, 1, 1, Qt::AlignHCenter);

        horizontalSpacer_5 = new QSpacerItem(10, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_17->addItem(horizontalSpacer_5, 0, 0, 2, 1);


        verticalLayout_7->addWidget(groupBox_3);

        verticalSpacer_3 = new QSpacerItem(20, 50, QSizePolicy::Minimum, QSizePolicy::Expanding);

        verticalLayout_7->addItem(verticalSpacer_3);

        label_4 = new QLabel(generalSettingsTab);
        label_4->setObjectName(QString::fromUtf8("label_4"));
        label_4->setMinimumSize(QSize(0, 20));

        verticalLayout_7->addWidget(label_4);

        groupBox_4 = new QGroupBox(generalSettingsTab);
        groupBox_4->setObjectName(QString::fromUtf8("groupBox_4"));
        sizePolicy7.setHeightForWidth(groupBox_4->sizePolicy().hasHeightForWidth());
        groupBox_4->setSizePolicy(sizePolicy7);
        groupBox_4->setMinimumSize(QSize(0, 200));
        groupBox_4->setAutoFillBackground(false);
        groupBox_4->setAlignment(Qt::AlignCenter);
        gridLayout_13 = new QGridLayout(groupBox_4);
        gridLayout_13->setObjectName(QString::fromUtf8("gridLayout_13"));
        horizontalSpacer_3 = new QSpacerItem(10, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_13->addItem(horizontalSpacer_3, 1, 0, 1, 1);

        pointLongitudeSigmaLineEdit = new QLineEdit(groupBox_4);
        pointLongitudeSigmaLineEdit->setObjectName(QString::fromUtf8("pointLongitudeSigmaLineEdit"));
        sizePolicy3.setHeightForWidth(pointLongitudeSigmaLineEdit->sizePolicy().hasHeightForWidth());
        pointLongitudeSigmaLineEdit->setSizePolicy(sizePolicy3);
        pointLongitudeSigmaLineEdit->setMinimumSize(QSize(100, 0));
        pointLongitudeSigmaLineEdit->setMaximumSize(QSize(100, 100));
        pointLongitudeSigmaLineEdit->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_13->addWidget(pointLongitudeSigmaLineEdit, 1, 2, 1, 1);

        horizontalSpacer_4 = new QSpacerItem(10, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        gridLayout_13->addItem(horizontalSpacer_4, 1, 3, 1, 1);

        pointLongitudeSigmaLabel = new QLabel(groupBox_4);
        pointLongitudeSigmaLabel->setObjectName(QString::fromUtf8("pointLongitudeSigmaLabel"));
        sizePolicy5.setHeightForWidth(pointLongitudeSigmaLabel->sizePolicy().hasHeightForWidth());
        pointLongitudeSigmaLabel->setSizePolicy(sizePolicy5);
        pointLongitudeSigmaLabel->setMaximumSize(QSize(100, 16777215));
        pointLongitudeSigmaLabel->setLayoutDirection(Qt::LeftToRight);
        pointLongitudeSigmaLabel->setTextFormat(Qt::RichText);

        gridLayout_13->addWidget(pointLongitudeSigmaLabel, 1, 1, 1, 1, Qt::AlignRight);

        pointLatitudeSigmaLineEdit = new QLineEdit(groupBox_4);
        pointLatitudeSigmaLineEdit->setObjectName(QString::fromUtf8("pointLatitudeSigmaLineEdit"));
        sizePolicy3.setHeightForWidth(pointLatitudeSigmaLineEdit->sizePolicy().hasHeightForWidth());
        pointLatitudeSigmaLineEdit->setSizePolicy(sizePolicy3);
        pointLatitudeSigmaLineEdit->setMaximumSize(QSize(100, 100));
        pointLatitudeSigmaLineEdit->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_13->addWidget(pointLatitudeSigmaLineEdit, 0, 2, 1, 1);

        pointRadiusSigmaLineEdit = new QLineEdit(groupBox_4);
        pointRadiusSigmaLineEdit->setObjectName(QString::fromUtf8("pointRadiusSigmaLineEdit"));
        pointRadiusSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(pointRadiusSigmaLineEdit->sizePolicy().hasHeightForWidth());
        pointRadiusSigmaLineEdit->setSizePolicy(sizePolicy3);
        pointRadiusSigmaLineEdit->setMinimumSize(QSize(100, 0));
        pointRadiusSigmaLineEdit->setMaximumSize(QSize(100, 100));
        pointRadiusSigmaLineEdit->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_13->addWidget(pointRadiusSigmaLineEdit, 2, 2, 1, 1);

        pointRadiusSigmaCheckBox = new QCheckBox(groupBox_4);
        pointRadiusSigmaCheckBox->setObjectName(QString::fromUtf8("pointRadiusSigmaCheckBox"));
        pointRadiusSigmaCheckBox->setEnabled(true);
        sizePolicy5.setHeightForWidth(pointRadiusSigmaCheckBox->sizePolicy().hasHeightForWidth());
        pointRadiusSigmaCheckBox->setSizePolicy(sizePolicy5);
        pointRadiusSigmaCheckBox->setMaximumSize(QSize(100, 16777215));
        pointRadiusSigmaCheckBox->setLayoutDirection(Qt::LeftToRight);
        pointRadiusSigmaCheckBox->setTristate(false);

        gridLayout_13->addWidget(pointRadiusSigmaCheckBox, 2, 1, 1, 1, Qt::AlignRight);

        pointLatitudeSigmaLabel = new QLabel(groupBox_4);
        pointLatitudeSigmaLabel->setObjectName(QString::fromUtf8("pointLatitudeSigmaLabel"));
        sizePolicy5.setHeightForWidth(pointLatitudeSigmaLabel->sizePolicy().hasHeightForWidth());
        pointLatitudeSigmaLabel->setSizePolicy(sizePolicy5);
        pointLatitudeSigmaLabel->setMaximumSize(QSize(100, 16777215));
        pointLatitudeSigmaLabel->setTextFormat(Qt::RichText);

        gridLayout_13->addWidget(pointLatitudeSigmaLabel, 0, 1, 1, 1, Qt::AlignRight);


        verticalLayout_7->addWidget(groupBox_4);

        verticalSpacer_4 = new QSpacerItem(20, 50, QSizePolicy::Minimum, QSizePolicy::Expanding);

        verticalLayout_7->addItem(verticalSpacer_4);

        label_5 = new QLabel(generalSettingsTab);
        label_5->setObjectName(QString::fromUtf8("label_5"));
        label_5->setMinimumSize(QSize(0, 20));

        verticalLayout_7->addWidget(label_5);

        groupBox_5 = new QGroupBox(generalSettingsTab);
        groupBox_5->setObjectName(QString::fromUtf8("groupBox_5"));
        sizePolicy7.setHeightForWidth(groupBox_5->sizePolicy().hasHeightForWidth());
        groupBox_5->setSizePolicy(sizePolicy7);
        groupBox_5->setMinimumSize(QSize(0, 100));
        groupBox_5->setAutoFillBackground(false);
        groupBox_5->setAlignment(Qt::AlignCenter);
        verticalLayout_4 = new QVBoxLayout(groupBox_5);
        verticalLayout_4->setObjectName(QString::fromUtf8("verticalLayout_4"));
        observationModeCheckBox = new QCheckBox(groupBox_5);
        observationModeCheckBox->setObjectName(QString::fromUtf8("observationModeCheckBox"));
        sizePolicy5.setHeightForWidth(observationModeCheckBox->sizePolicy().hasHeightForWidth());
        observationModeCheckBox->setSizePolicy(sizePolicy5);
        observationModeCheckBox->setMaximumSize(QSize(16777215, 40));

        verticalLayout_4->addWidget(observationModeCheckBox, 0, Qt::AlignHCenter);

        errorPropagationCheckBox = new QCheckBox(groupBox_5);
        errorPropagationCheckBox->setObjectName(QString::fromUtf8("errorPropagationCheckBox"));
        sizePolicy5.setHeightForWidth(errorPropagationCheckBox->sizePolicy().hasHeightForWidth());
        errorPropagationCheckBox->setSizePolicy(sizePolicy5);
        errorPropagationCheckBox->setMinimumSize(QSize(74, 0));
        errorPropagationCheckBox->setMaximumSize(QSize(16777215, 40));

        verticalLayout_4->addWidget(errorPropagationCheckBox, 0, Qt::AlignHCenter);


        verticalLayout_7->addWidget(groupBox_5);


        horizontalLayout_7->addLayout(verticalLayout_7);


        gridLayout_2->addLayout(horizontalLayout_7, 0, 0, 1, 1);

        JigsawSetup->addTab(generalSettingsTab, QString());
        observationSolveSettingsTab = new QWidget();
        observationSolveSettingsTab->setObjectName(QString::fromUtf8("observationSolveSettingsTab"));
        gridLayout_8 = new QGridLayout(observationSolveSettingsTab);
        gridLayout_8->setObjectName(QString::fromUtf8("gridLayout_8"));
        groupBox = new QGroupBox(observationSolveSettingsTab);
        groupBox->setObjectName(QString::fromUtf8("groupBox"));
        groupBox->setFlat(false);
        groupBox->setCheckable(false);
        gridLayout_9 = new QGridLayout(groupBox);
        gridLayout_9->setObjectName(QString::fromUtf8("gridLayout_9"));
        hermiteSplineCheckBox = new QCheckBox(groupBox);
        hermiteSplineCheckBox->setObjectName(QString::fromUtf8("hermiteSplineCheckBox"));
        hermiteSplineCheckBox->setEnabled(true);
        sizePolicy1.setHeightForWidth(hermiteSplineCheckBox->sizePolicy().hasHeightForWidth());
        hermiteSplineCheckBox->setSizePolicy(sizePolicy1);

        gridLayout_9->addWidget(hermiteSplineCheckBox, 2, 2, 1, 1);

        positionAprioriSigmaTable = new QTableWidget(groupBox);
        if (positionAprioriSigmaTable->columnCount() < 4)
            positionAprioriSigmaTable->setColumnCount(4);
        positionAprioriSigmaTable->setObjectName(QString::fromUtf8("positionAprioriSigmaTable"));
        sizePolicy1.setHeightForWidth(positionAprioriSigmaTable->sizePolicy().hasHeightForWidth());
        positionAprioriSigmaTable->setSizePolicy(sizePolicy1);
        positionAprioriSigmaTable->setMaximumSize(QSize(16777215, 16777215));
        positionAprioriSigmaTable->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);
        positionAprioriSigmaTable->setHorizontalScrollBarPolicy(Qt::ScrollBarAsNeeded);
        positionAprioriSigmaTable->setAutoScroll(true);
        positionAprioriSigmaTable->setAlternatingRowColors(true);
        positionAprioriSigmaTable->setShowGrid(true);
        positionAprioriSigmaTable->setColumnCount(4);
        positionAprioriSigmaTable->horizontalHeader()->setCascadingSectionResizes(false);
        positionAprioriSigmaTable->horizontalHeader()->setMinimumSectionSize(130);
        positionAprioriSigmaTable->horizontalHeader()->setDefaultSectionSize(125);
        positionAprioriSigmaTable->horizontalHeader()->setProperty("showSortIndicator", QVariant(false));
        positionAprioriSigmaTable->horizontalHeader()->setStretchLastSection(true);
        positionAprioriSigmaTable->verticalHeader()->setVisible(false);

        gridLayout_9->addWidget(positionAprioriSigmaTable, 4, 0, 1, 3);

        spkSolveDegreeLabel = new QLabel(groupBox);
        spkSolveDegreeLabel->setObjectName(QString::fromUtf8("spkSolveDegreeLabel"));
        spkSolveDegreeLabel->setEnabled(true);
        spkSolveDegreeLabel->setWordWrap(true);

        gridLayout_9->addWidget(spkSolveDegreeLabel, 1, 0, 1, 1);

        spkDegreeSpinBox = new QSpinBox(groupBox);
        spkDegreeSpinBox->setObjectName(QString::fromUtf8("spkDegreeSpinBox"));
        spkDegreeSpinBox->setEnabled(true);
        sizePolicy.setHeightForWidth(spkDegreeSpinBox->sizePolicy().hasHeightForWidth());
        spkDegreeSpinBox->setSizePolicy(sizePolicy);
        spkDegreeSpinBox->setMinimum(0);
        spkDegreeSpinBox->setValue(2);

        gridLayout_9->addWidget(spkDegreeSpinBox, 2, 1, 1, 1);

        spkSolveDegreeSpinBox = new QSpinBox(groupBox);
        spkSolveDegreeSpinBox->setObjectName(QString::fromUtf8("spkSolveDegreeSpinBox"));
        spkSolveDegreeSpinBox->setEnabled(true);
        sizePolicy.setHeightForWidth(spkSolveDegreeSpinBox->sizePolicy().hasHeightForWidth());
        spkSolveDegreeSpinBox->setSizePolicy(sizePolicy);
        spkSolveDegreeSpinBox->setMinimum(-1);
        spkSolveDegreeSpinBox->setValue(1);

        gridLayout_9->addWidget(spkSolveDegreeSpinBox, 1, 1, 1, 1);

        spkDegreeLabel = new QLabel(groupBox);
        spkDegreeLabel->setObjectName(QString::fromUtf8("spkDegreeLabel"));
        spkDegreeLabel->setEnabled(true);
        spkDegreeLabel->setWordWrap(true);

        gridLayout_9->addWidget(spkDegreeLabel, 2, 0, 1, 1);

        positionComboBox = new QComboBox(groupBox);
        positionComboBox->setObjectName(QString::fromUtf8("positionComboBox"));

        gridLayout_9->addWidget(positionComboBox, 0, 0, 1, 2);


        gridLayout_8->addWidget(groupBox, 0, 1, 1, 1);

        applySettingsPushButton = new QPushButton(observationSolveSettingsTab);
        applySettingsPushButton->setObjectName(QString::fromUtf8("applySettingsPushButton"));
        applySettingsPushButton->setEnabled(false);

        gridLayout_8->addWidget(applySettingsPushButton, 3, 1, 1, 1);

        treeView = new QTreeView(observationSolveSettingsTab);
        treeView->setObjectName(QString::fromUtf8("treeView"));
        treeView->setEditTriggers(QAbstractItemView::NoEditTriggers);
        treeView->setSelectionMode(QAbstractItemView::ExtendedSelection);
        treeView->setHeaderHidden(true);

        gridLayout_8->addWidget(treeView, 0, 0, 4, 1);

        groupBox_2 = new QGroupBox(observationSolveSettingsTab);
        groupBox_2->setObjectName(QString::fromUtf8("groupBox_2"));
        gridLayout_10 = new QGridLayout(groupBox_2);
        gridLayout_10->setObjectName(QString::fromUtf8("gridLayout_10"));
        twistCheckBox = new QCheckBox(groupBox_2);
        twistCheckBox->setObjectName(QString::fromUtf8("twistCheckBox"));
        sizePolicy1.setHeightForWidth(twistCheckBox->sizePolicy().hasHeightForWidth());
        twistCheckBox->setSizePolicy(sizePolicy1);
        twistCheckBox->setChecked(true);

        gridLayout_10->addWidget(twistCheckBox, 1, 2, 1, 1);

        ckSolveDegreeLabel = new QLabel(groupBox_2);
        ckSolveDegreeLabel->setObjectName(QString::fromUtf8("ckSolveDegreeLabel"));
        ckSolveDegreeLabel->setEnabled(true);
        ckSolveDegreeLabel->setWordWrap(true);

        gridLayout_10->addWidget(ckSolveDegreeLabel, 1, 0, 1, 1);

        ckDegreeLabel = new QLabel(groupBox_2);
        ckDegreeLabel->setObjectName(QString::fromUtf8("ckDegreeLabel"));
        ckDegreeLabel->setEnabled(true);
        ckDegreeLabel->setWordWrap(true);

        gridLayout_10->addWidget(ckDegreeLabel, 2, 0, 1, 1);

        ckDegreeSpinBox = new QSpinBox(groupBox_2);
        ckDegreeSpinBox->setObjectName(QString::fromUtf8("ckDegreeSpinBox"));
        ckDegreeSpinBox->setEnabled(true);
        sizePolicy.setHeightForWidth(ckDegreeSpinBox->sizePolicy().hasHeightForWidth());
        ckDegreeSpinBox->setSizePolicy(sizePolicy);
        ckDegreeSpinBox->setMinimum(0);
        ckDegreeSpinBox->setValue(2);

        gridLayout_10->addWidget(ckDegreeSpinBox, 2, 1, 1, 1);

        fitOverPointingCheckBox = new QCheckBox(groupBox_2);
        fitOverPointingCheckBox->setObjectName(QString::fromUtf8("fitOverPointingCheckBox"));
        sizePolicy1.setHeightForWidth(fitOverPointingCheckBox->sizePolicy().hasHeightForWidth());
        fitOverPointingCheckBox->setSizePolicy(sizePolicy1);
        fitOverPointingCheckBox->setMinimumSize(QSize(0, 0));

        gridLayout_10->addWidget(fitOverPointingCheckBox, 2, 2, 1, 1);

        pointingAprioriSigmaTable = new QTableWidget(groupBox_2);
        if (pointingAprioriSigmaTable->columnCount() < 4)
            pointingAprioriSigmaTable->setColumnCount(4);
        pointingAprioriSigmaTable->setObjectName(QString::fromUtf8("pointingAprioriSigmaTable"));
        sizePolicy1.setHeightForWidth(pointingAprioriSigmaTable->sizePolicy().hasHeightForWidth());
        pointingAprioriSigmaTable->setSizePolicy(sizePolicy1);
        pointingAprioriSigmaTable->setMaximumSize(QSize(16777215, 16777215));
        pointingAprioriSigmaTable->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);
        pointingAprioriSigmaTable->setHorizontalScrollBarPolicy(Qt::ScrollBarAsNeeded);
        pointingAprioriSigmaTable->setAlternatingRowColors(true);
        pointingAprioriSigmaTable->setShowGrid(true);
        pointingAprioriSigmaTable->setColumnCount(4);
        pointingAprioriSigmaTable->horizontalHeader()->setMinimumSectionSize(130);
        pointingAprioriSigmaTable->horizontalHeader()->setDefaultSectionSize(125);
        pointingAprioriSigmaTable->horizontalHeader()->setStretchLastSection(true);
        pointingAprioriSigmaTable->verticalHeader()->setVisible(false);

        gridLayout_10->addWidget(pointingAprioriSigmaTable, 4, 0, 1, 3);

        ckSolveDegreeSpinBox = new QSpinBox(groupBox_2);
        ckSolveDegreeSpinBox->setObjectName(QString::fromUtf8("ckSolveDegreeSpinBox"));
        ckSolveDegreeSpinBox->setEnabled(true);
        sizePolicy.setHeightForWidth(ckSolveDegreeSpinBox->sizePolicy().hasHeightForWidth());
        ckSolveDegreeSpinBox->setSizePolicy(sizePolicy);
        ckSolveDegreeSpinBox->setMinimum(-1);
        ckSolveDegreeSpinBox->setValue(2);

        gridLayout_10->addWidget(ckSolveDegreeSpinBox, 1, 1, 1, 1);

        pointingComboBox = new QComboBox(groupBox_2);
        pointingComboBox->setObjectName(QString::fromUtf8("pointingComboBox"));

        gridLayout_10->addWidget(pointingComboBox, 0, 0, 1, 2);

        pointingAprioriSigmaTable->raise();
        ckDegreeLabel->raise();
        ckDegreeSpinBox->raise();
        fitOverPointingCheckBox->raise();
        ckSolveDegreeSpinBox->raise();
        ckSolveDegreeLabel->raise();
        twistCheckBox->raise();
        pointingComboBox->raise();

        gridLayout_8->addWidget(groupBox_2, 1, 1, 1, 1);

        JigsawSetup->addTab(observationSolveSettingsTab, QString());
        targetBodyTab = new QWidget();
        targetBodyTab->setObjectName(QString::fromUtf8("targetBodyTab"));
        gridLayout = new QGridLayout(targetBodyTab);
        gridLayout->setObjectName(QString::fromUtf8("gridLayout"));
        horizontalLayout_4 = new QHBoxLayout();
        horizontalLayout_4->setObjectName(QString::fromUtf8("horizontalLayout_4"));
        targetLabel = new QLabel(targetBodyTab);
        targetLabel->setObjectName(QString::fromUtf8("targetLabel"));
        sizePolicy3.setHeightForWidth(targetLabel->sizePolicy().hasHeightForWidth());
        targetLabel->setSizePolicy(sizePolicy3);
        QFont font;
        font.setBold(true);
        font.setWeight(75);
        targetLabel->setFont(font);

        horizontalLayout_4->addWidget(targetLabel);

        targetBodyComboBox = new QComboBox(targetBodyTab);
        targetBodyComboBox->setObjectName(QString::fromUtf8("targetBodyComboBox"));
        sizePolicy.setHeightForWidth(targetBodyComboBox->sizePolicy().hasHeightForWidth());
        targetBodyComboBox->setSizePolicy(sizePolicy);

        horizontalLayout_4->addWidget(targetBodyComboBox);


        gridLayout->addLayout(horizontalLayout_4, 0, 0, 1, 1);

        verticalSpacer_2 = new QSpacerItem(20, 40, QSizePolicy::Minimum, QSizePolicy::Expanding);

        gridLayout->addItem(verticalSpacer_2, 5, 0, 1, 1);

        verticalLayout_2 = new QVBoxLayout();
        verticalLayout_2->setObjectName(QString::fromUtf8("verticalLayout_2"));
        targetParametersGroupBox = new QGroupBox(targetBodyTab);
        targetParametersGroupBox->setObjectName(QString::fromUtf8("targetParametersGroupBox"));
        gridLayout_12 = new QGridLayout(targetParametersGroupBox);
        gridLayout_12->setObjectName(QString::fromUtf8("gridLayout_12"));
        primeMeridianOffsetLineEdit = new QLineEdit(targetParametersGroupBox);
        primeMeridianOffsetLineEdit->setObjectName(QString::fromUtf8("primeMeridianOffsetLineEdit"));
        primeMeridianOffsetLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(primeMeridianOffsetLineEdit->sizePolicy().hasHeightForWidth());
        primeMeridianOffsetLineEdit->setSizePolicy(sizePolicy3);
        primeMeridianOffsetLineEdit->setMinimumSize(QSize(0, 22));
        primeMeridianOffsetLineEdit->setMaximumSize(QSize(16777215, 22));

        gridLayout_12->addWidget(primeMeridianOffsetLineEdit, 5, 1, 1, 1);

        spinRateSigmaLineEdit = new QLineEdit(targetParametersGroupBox);
        spinRateSigmaLineEdit->setObjectName(QString::fromUtf8("spinRateSigmaLineEdit"));
        spinRateSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(spinRateSigmaLineEdit->sizePolicy().hasHeightForWidth());
        spinRateSigmaLineEdit->setSizePolicy(sizePolicy3);

        gridLayout_12->addWidget(spinRateSigmaLineEdit, 6, 2, 1, 1);

        rightAscensionVelocityLineEdit = new QLineEdit(targetParametersGroupBox);
        rightAscensionVelocityLineEdit->setObjectName(QString::fromUtf8("rightAscensionVelocityLineEdit"));
        rightAscensionVelocityLineEdit->setEnabled(false);

        gridLayout_12->addWidget(rightAscensionVelocityLineEdit, 2, 1, 1, 1);

        declinationVelocityLineEdit = new QLineEdit(targetParametersGroupBox);
        declinationVelocityLineEdit->setObjectName(QString::fromUtf8("declinationVelocityLineEdit"));
        declinationVelocityLineEdit->setEnabled(false);

        gridLayout_12->addWidget(declinationVelocityLineEdit, 4, 1, 1, 1);

        declinationSigmaLineEdit = new QLineEdit(targetParametersGroupBox);
        declinationSigmaLineEdit->setObjectName(QString::fromUtf8("declinationSigmaLineEdit"));
        declinationSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(declinationSigmaLineEdit->sizePolicy().hasHeightForWidth());
        declinationSigmaLineEdit->setSizePolicy(sizePolicy3);
        declinationSigmaLineEdit->setMinimumSize(QSize(0, 22));
        declinationSigmaLineEdit->setMaximumSize(QSize(16777215, 22));

        gridLayout_12->addWidget(declinationSigmaLineEdit, 3, 2, 1, 1);

        sigmaLabel = new QLabel(targetParametersGroupBox);
        sigmaLabel->setObjectName(QString::fromUtf8("sigmaLabel"));
        sizePolicy3.setHeightForWidth(sigmaLabel->sizePolicy().hasHeightForWidth());
        sigmaLabel->setSizePolicy(sizePolicy3);
        sigmaLabel->setFont(font);
        sigmaLabel->setAlignment(Qt::AlignCenter);

        gridLayout_12->addWidget(sigmaLabel, 0, 2, 1, 1);

        declinationLineEdit = new QLineEdit(targetParametersGroupBox);
        declinationLineEdit->setObjectName(QString::fromUtf8("declinationLineEdit"));
        declinationLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(declinationLineEdit->sizePolicy().hasHeightForWidth());
        declinationLineEdit->setSizePolicy(sizePolicy3);
        declinationLineEdit->setMinimumSize(QSize(0, 22));
        declinationLineEdit->setMaximumSize(QSize(16777215, 22));

        gridLayout_12->addWidget(declinationLineEdit, 3, 1, 1, 1);

        valueLabel = new QLabel(targetParametersGroupBox);
        valueLabel->setObjectName(QString::fromUtf8("valueLabel"));
        sizePolicy3.setHeightForWidth(valueLabel->sizePolicy().hasHeightForWidth());
        valueLabel->setSizePolicy(sizePolicy3);
        valueLabel->setFont(font);
        valueLabel->setAlignment(Qt::AlignCenter);

        gridLayout_12->addWidget(valueLabel, 0, 1, 1, 1);

        rightAscensionSigmaLineEdit = new QLineEdit(targetParametersGroupBox);
        rightAscensionSigmaLineEdit->setObjectName(QString::fromUtf8("rightAscensionSigmaLineEdit"));
        rightAscensionSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(rightAscensionSigmaLineEdit->sizePolicy().hasHeightForWidth());
        rightAscensionSigmaLineEdit->setSizePolicy(sizePolicy3);

        gridLayout_12->addWidget(rightAscensionSigmaLineEdit, 1, 2, 1, 1);

        poleRaCheckBox = new QCheckBox(targetParametersGroupBox);
        poleRaCheckBox->setObjectName(QString::fromUtf8("poleRaCheckBox"));
        sizePolicy3.setHeightForWidth(poleRaCheckBox->sizePolicy().hasHeightForWidth());
        poleRaCheckBox->setSizePolicy(sizePolicy3);
        poleRaCheckBox->setMinimumSize(QSize(200, 18));
        poleRaCheckBox->setMaximumSize(QSize(144, 18));
        poleRaCheckBox->setFont(font);

        gridLayout_12->addWidget(poleRaCheckBox, 1, 0, 1, 1);

        poleDecCheckBox = new QCheckBox(targetParametersGroupBox);
        poleDecCheckBox->setObjectName(QString::fromUtf8("poleDecCheckBox"));
        sizePolicy3.setHeightForWidth(poleDecCheckBox->sizePolicy().hasHeightForWidth());
        poleDecCheckBox->setSizePolicy(sizePolicy3);
        poleDecCheckBox->setMinimumSize(QSize(200, 18));
        poleDecCheckBox->setMaximumSize(QSize(144, 18));
        poleDecCheckBox->setFont(font);

        gridLayout_12->addWidget(poleDecCheckBox, 3, 0, 1, 1);

        rightAscensionVelocitySigmaLineEdit = new QLineEdit(targetParametersGroupBox);
        rightAscensionVelocitySigmaLineEdit->setObjectName(QString::fromUtf8("rightAscensionVelocitySigmaLineEdit"));
        rightAscensionVelocitySigmaLineEdit->setEnabled(false);

        gridLayout_12->addWidget(rightAscensionVelocitySigmaLineEdit, 2, 2, 1, 1);

        declinationVelocitySigmaLineEdit = new QLineEdit(targetParametersGroupBox);
        declinationVelocitySigmaLineEdit->setObjectName(QString::fromUtf8("declinationVelocitySigmaLineEdit"));
        declinationVelocitySigmaLineEdit->setEnabled(false);

        gridLayout_12->addWidget(declinationVelocitySigmaLineEdit, 4, 2, 1, 1);

        poleRaVelocityCheckBox = new QCheckBox(targetParametersGroupBox);
        poleRaVelocityCheckBox->setObjectName(QString::fromUtf8("poleRaVelocityCheckBox"));
        poleRaVelocityCheckBox->setFont(font);

        gridLayout_12->addWidget(poleRaVelocityCheckBox, 2, 0, 1, 1);

        poleDecVelocityCheckBox = new QCheckBox(targetParametersGroupBox);
        poleDecVelocityCheckBox->setObjectName(QString::fromUtf8("poleDecVelocityCheckBox"));
        poleDecVelocityCheckBox->setFont(font);

        gridLayout_12->addWidget(poleDecVelocityCheckBox, 4, 0, 1, 1);

        primeMeridianOffsetCheckBox = new QCheckBox(targetParametersGroupBox);
        primeMeridianOffsetCheckBox->setObjectName(QString::fromUtf8("primeMeridianOffsetCheckBox"));
        sizePolicy3.setHeightForWidth(primeMeridianOffsetCheckBox->sizePolicy().hasHeightForWidth());
        primeMeridianOffsetCheckBox->setSizePolicy(sizePolicy3);
        primeMeridianOffsetCheckBox->setMinimumSize(QSize(200, 0));
        primeMeridianOffsetCheckBox->setMaximumSize(QSize(16777215, 18));
        primeMeridianOffsetCheckBox->setFont(font);

        gridLayout_12->addWidget(primeMeridianOffsetCheckBox, 5, 0, 1, 1);

        primeMeridianOffsetSigmaLineEdit = new QLineEdit(targetParametersGroupBox);
        primeMeridianOffsetSigmaLineEdit->setObjectName(QString::fromUtf8("primeMeridianOffsetSigmaLineEdit"));
        primeMeridianOffsetSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(primeMeridianOffsetSigmaLineEdit->sizePolicy().hasHeightForWidth());
        primeMeridianOffsetSigmaLineEdit->setSizePolicy(sizePolicy3);

        gridLayout_12->addWidget(primeMeridianOffsetSigmaLineEdit, 5, 2, 1, 1);

        spinRateCheckBox = new QCheckBox(targetParametersGroupBox);
        spinRateCheckBox->setObjectName(QString::fromUtf8("spinRateCheckBox"));
        sizePolicy3.setHeightForWidth(spinRateCheckBox->sizePolicy().hasHeightForWidth());
        spinRateCheckBox->setSizePolicy(sizePolicy3);
        spinRateCheckBox->setMinimumSize(QSize(200, 18));
        spinRateCheckBox->setMaximumSize(QSize(144, 18));
        spinRateCheckBox->setFont(font);

        gridLayout_12->addWidget(spinRateCheckBox, 6, 0, 1, 1);

        spinRateLineEdit = new QLineEdit(targetParametersGroupBox);
        spinRateLineEdit->setObjectName(QString::fromUtf8("spinRateLineEdit"));
        spinRateLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(spinRateLineEdit->sizePolicy().hasHeightForWidth());
        spinRateLineEdit->setSizePolicy(sizePolicy3);
        spinRateLineEdit->setMinimumSize(QSize(0, 22));
        spinRateLineEdit->setMaximumSize(QSize(16777215, 22));

        gridLayout_12->addWidget(spinRateLineEdit, 6, 1, 1, 1);

        rightAscensionLineEdit = new QLineEdit(targetParametersGroupBox);
        rightAscensionLineEdit->setObjectName(QString::fromUtf8("rightAscensionLineEdit"));
        rightAscensionLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(rightAscensionLineEdit->sizePolicy().hasHeightForWidth());
        rightAscensionLineEdit->setSizePolicy(sizePolicy3);

        gridLayout_12->addWidget(rightAscensionLineEdit, 1, 1, 1, 1);


        verticalLayout_2->addWidget(targetParametersGroupBox);


        gridLayout->addLayout(verticalLayout_2, 4, 0, 1, 1);

        radiiGroupBox = new QGroupBox(targetBodyTab);
        radiiGroupBox->setObjectName(QString::fromUtf8("radiiGroupBox"));
        radiiGroupBox->setFont(font);
        gridLayout_6 = new QGridLayout(radiiGroupBox);
        gridLayout_6->setObjectName(QString::fromUtf8("gridLayout_6"));
        gridLayout_5 = new QGridLayout();
        gridLayout_5->setObjectName(QString::fromUtf8("gridLayout_5"));
        meanRadiusRadioButton = new QRadioButton(radiiGroupBox);
        radiiButtonGroup = new QButtonGroup(JigsawSetupDialog);
        radiiButtonGroup->setObjectName(QString::fromUtf8("radiiButtonGroup"));
        radiiButtonGroup->addButton(meanRadiusRadioButton);
        meanRadiusRadioButton->setObjectName(QString::fromUtf8("meanRadiusRadioButton"));
        sizePolicy3.setHeightForWidth(meanRadiusRadioButton->sizePolicy().hasHeightForWidth());
        meanRadiusRadioButton->setSizePolicy(sizePolicy3);
        meanRadiusRadioButton->setMinimumSize(QSize(0, 18));
        meanRadiusRadioButton->setMaximumSize(QSize(193, 18));
        QFont font1;
        font1.setBold(true);
        font1.setItalic(false);
        font1.setWeight(75);
        meanRadiusRadioButton->setFont(font1);

        gridLayout_5->addWidget(meanRadiusRadioButton, 4, 0, 1, 1);

        bRadiusLabel = new QLabel(radiiGroupBox);
        bRadiusLabel->setObjectName(QString::fromUtf8("bRadiusLabel"));
        bRadiusLabel->setEnabled(false);
        sizePolicy3.setHeightForWidth(bRadiusLabel->sizePolicy().hasHeightForWidth());
        bRadiusLabel->setSizePolicy(sizePolicy3);
        bRadiusLabel->setMaximumSize(QSize(16777215, 16777215));
        bRadiusLabel->setFont(font);
        bRadiusLabel->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_5->addWidget(bRadiusLabel, 2, 2, 1, 1);

        cRadiusLabel = new QLabel(radiiGroupBox);
        cRadiusLabel->setObjectName(QString::fromUtf8("cRadiusLabel"));
        cRadiusLabel->setEnabled(false);
        sizePolicy3.setHeightForWidth(cRadiusLabel->sizePolicy().hasHeightForWidth());
        cRadiusLabel->setSizePolicy(sizePolicy3);
        cRadiusLabel->setMaximumSize(QSize(16777215, 16777215));
        cRadiusLabel->setFont(font);
        cRadiusLabel->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_5->addWidget(cRadiusLabel, 3, 2, 1, 1);

        aRadiusLineEdit = new QLineEdit(radiiGroupBox);
        aRadiusLineEdit->setObjectName(QString::fromUtf8("aRadiusLineEdit"));
        aRadiusLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(aRadiusLineEdit->sizePolicy().hasHeightForWidth());
        aRadiusLineEdit->setSizePolicy(sizePolicy3);
        aRadiusLineEdit->setMinimumSize(QSize(0, 22));
        aRadiusLineEdit->setMaximumSize(QSize(16777215, 22));
        QFont font2;
        font2.setBold(false);
        font2.setWeight(50);
        aRadiusLineEdit->setFont(font2);

        gridLayout_5->addWidget(aRadiusLineEdit, 1, 3, 1, 1);

        aRadiusSigmaLineEdit = new QLineEdit(radiiGroupBox);
        aRadiusSigmaLineEdit->setObjectName(QString::fromUtf8("aRadiusSigmaLineEdit"));
        aRadiusSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(aRadiusSigmaLineEdit->sizePolicy().hasHeightForWidth());
        aRadiusSigmaLineEdit->setSizePolicy(sizePolicy3);
        aRadiusSigmaLineEdit->setFont(font2);

        gridLayout_5->addWidget(aRadiusSigmaLineEdit, 1, 4, 1, 1);

        triaxialRadiiRadioButton = new QRadioButton(radiiGroupBox);
        radiiButtonGroup->addButton(triaxialRadiiRadioButton);
        triaxialRadiiRadioButton->setObjectName(QString::fromUtf8("triaxialRadiiRadioButton"));
        sizePolicy3.setHeightForWidth(triaxialRadiiRadioButton->sizePolicy().hasHeightForWidth());
        triaxialRadiiRadioButton->setSizePolicy(sizePolicy3);
        triaxialRadiiRadioButton->setMinimumSize(QSize(193, 0));
        triaxialRadiiRadioButton->setMaximumSize(QSize(193, 18));
        triaxialRadiiRadioButton->setFont(font);

        gridLayout_5->addWidget(triaxialRadiiRadioButton, 1, 0, 1, 1);

        cRadiusLineEdit = new QLineEdit(radiiGroupBox);
        cRadiusLineEdit->setObjectName(QString::fromUtf8("cRadiusLineEdit"));
        cRadiusLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(cRadiusLineEdit->sizePolicy().hasHeightForWidth());
        cRadiusLineEdit->setSizePolicy(sizePolicy3);
        cRadiusLineEdit->setMinimumSize(QSize(0, 22));
        cRadiusLineEdit->setMaximumSize(QSize(16777215, 22));
        cRadiusLineEdit->setFont(font2);

        gridLayout_5->addWidget(cRadiusLineEdit, 3, 3, 1, 1);

        meanRadiusLineEdit = new QLineEdit(radiiGroupBox);
        meanRadiusLineEdit->setObjectName(QString::fromUtf8("meanRadiusLineEdit"));
        meanRadiusLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(meanRadiusLineEdit->sizePolicy().hasHeightForWidth());
        meanRadiusLineEdit->setSizePolicy(sizePolicy3);
        meanRadiusLineEdit->setMinimumSize(QSize(0, 22));
        meanRadiusLineEdit->setMaximumSize(QSize(16777215, 22));
        meanRadiusLineEdit->setFont(font2);

        gridLayout_5->addWidget(meanRadiusLineEdit, 4, 3, 1, 1);

        bRadiusSigmaLineEdit = new QLineEdit(radiiGroupBox);
        bRadiusSigmaLineEdit->setObjectName(QString::fromUtf8("bRadiusSigmaLineEdit"));
        bRadiusSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(bRadiusSigmaLineEdit->sizePolicy().hasHeightForWidth());
        bRadiusSigmaLineEdit->setSizePolicy(sizePolicy3);
        bRadiusSigmaLineEdit->setFont(font2);

        gridLayout_5->addWidget(bRadiusSigmaLineEdit, 2, 4, 1, 1);

        cRadiusSigmaLineEdit = new QLineEdit(radiiGroupBox);
        cRadiusSigmaLineEdit->setObjectName(QString::fromUtf8("cRadiusSigmaLineEdit"));
        cRadiusSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(cRadiusSigmaLineEdit->sizePolicy().hasHeightForWidth());
        cRadiusSigmaLineEdit->setSizePolicy(sizePolicy3);
        cRadiusSigmaLineEdit->setFont(font2);

        gridLayout_5->addWidget(cRadiusSigmaLineEdit, 3, 4, 1, 1);

        meanRadiusSigmaLineEdit = new QLineEdit(radiiGroupBox);
        meanRadiusSigmaLineEdit->setObjectName(QString::fromUtf8("meanRadiusSigmaLineEdit"));
        meanRadiusSigmaLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(meanRadiusSigmaLineEdit->sizePolicy().hasHeightForWidth());
        meanRadiusSigmaLineEdit->setSizePolicy(sizePolicy3);
        meanRadiusSigmaLineEdit->setMinimumSize(QSize(0, 22));
        meanRadiusSigmaLineEdit->setMaximumSize(QSize(16777215, 22));
        meanRadiusSigmaLineEdit->setFont(font2);

        gridLayout_5->addWidget(meanRadiusSigmaLineEdit, 4, 4, 1, 1);

        bRadiusLineEdit = new QLineEdit(radiiGroupBox);
        bRadiusLineEdit->setObjectName(QString::fromUtf8("bRadiusLineEdit"));
        bRadiusLineEdit->setEnabled(false);
        sizePolicy3.setHeightForWidth(bRadiusLineEdit->sizePolicy().hasHeightForWidth());
        bRadiusLineEdit->setSizePolicy(sizePolicy3);
        bRadiusLineEdit->setMinimumSize(QSize(0, 22));
        bRadiusLineEdit->setMaximumSize(QSize(16777215, 22));
        bRadiusLineEdit->setFont(font2);

        gridLayout_5->addWidget(bRadiusLineEdit, 2, 3, 1, 1);

        aRadiusLabel = new QLabel(radiiGroupBox);
        aRadiusLabel->setObjectName(QString::fromUtf8("aRadiusLabel"));
        aRadiusLabel->setEnabled(false);
        sizePolicy3.setHeightForWidth(aRadiusLabel->sizePolicy().hasHeightForWidth());
        aRadiusLabel->setSizePolicy(sizePolicy3);
        aRadiusLabel->setMinimumSize(QSize(7, 0));
        aRadiusLabel->setMaximumSize(QSize(16777215, 16777215));
        aRadiusLabel->setFont(font);
        aRadiusLabel->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout_5->addWidget(aRadiusLabel, 1, 2, 1, 1);

        noneRadiiRadioButton = new QRadioButton(radiiGroupBox);
        radiiButtonGroup->addButton(noneRadiiRadioButton);
        noneRadiiRadioButton->setObjectName(QString::fromUtf8("noneRadiiRadioButton"));

        gridLayout_5->addWidget(noneRadiiRadioButton, 0, 0, 1, 1);


        gridLayout_6->addLayout(gridLayout_5, 0, 0, 1, 1);


        gridLayout->addWidget(radiiGroupBox, 6, 0, 1, 1);

        verticalSpacer = new QSpacerItem(20, 40, QSizePolicy::Minimum, QSizePolicy::Expanding);

        gridLayout->addItem(verticalSpacer, 2, 0, 1, 1);

        targetParametersMessage = new QLabel(targetBodyTab);
        targetParametersMessage->setObjectName(QString::fromUtf8("targetParametersMessage"));
        targetParametersMessage->setEnabled(true);

        gridLayout->addWidget(targetParametersMessage, 3, 0, 1, 1);

        JigsawSetup->addTab(targetBodyTab, QString());

        horizontalLayout->addWidget(JigsawSetup);


        verticalLayout->addLayout(horizontalLayout);

        okCloseButtonBox = new QDialogButtonBox(JigsawSetupDialog);
        okCloseButtonBox->setObjectName(QString::fromUtf8("okCloseButtonBox"));
        sizePolicy3.setHeightForWidth(okCloseButtonBox->sizePolicy().hasHeightForWidth());
        okCloseButtonBox->setSizePolicy(sizePolicy3);
        okCloseButtonBox->setOrientation(Qt::Horizontal);
        okCloseButtonBox->setStandardButtons(QDialogButtonBox::Cancel|QDialogButtonBox::Ok);

        verticalLayout->addWidget(okCloseButtonBox);


        verticalLayout_3->addLayout(verticalLayout);

#if QT_CONFIG(shortcut)
        maximumLikelihoodModel2Label->setBuddy(maximumLikelihoodModel2ComboBox);
        maximumLikelihoodModel1Label->setBuddy(maximumLikelihoodModel1ComboBox);
        maximumLikelihoodModel3Label->setBuddy(maximumLikelihoodModel3ComboBox);
        sigma0ThresholdLabel->setBuddy(sigma0ThresholdLineEdit);
        maximumIterationsLabel->setBuddy(maximumIterationsLineEdit);
#endif // QT_CONFIG(shortcut)
        QWidget::setTabOrder(poleRaCheckBox, rightAscensionLineEdit);
        QWidget::setTabOrder(rightAscensionLineEdit, rightAscensionSigmaLineEdit);
        QWidget::setTabOrder(rightAscensionSigmaLineEdit, poleDecCheckBox);
        QWidget::setTabOrder(poleDecCheckBox, declinationLineEdit);
        QWidget::setTabOrder(declinationLineEdit, declinationSigmaLineEdit);
        QWidget::setTabOrder(declinationSigmaLineEdit, noneRadiiRadioButton);
        QWidget::setTabOrder(noneRadiiRadioButton, triaxialRadiiRadioButton);
        QWidget::setTabOrder(triaxialRadiiRadioButton, aRadiusLineEdit);
        QWidget::setTabOrder(aRadiusLineEdit, aRadiusSigmaLineEdit);
        QWidget::setTabOrder(aRadiusSigmaLineEdit, bRadiusLineEdit);
        QWidget::setTabOrder(bRadiusLineEdit, bRadiusSigmaLineEdit);
        QWidget::setTabOrder(bRadiusSigmaLineEdit, cRadiusLineEdit);
        QWidget::setTabOrder(cRadiusLineEdit, cRadiusSigmaLineEdit);
        QWidget::setTabOrder(cRadiusSigmaLineEdit, meanRadiusRadioButton);
        QWidget::setTabOrder(meanRadiusRadioButton, meanRadiusLineEdit);
        QWidget::setTabOrder(meanRadiusLineEdit, meanRadiusSigmaLineEdit);
        QWidget::setTabOrder(meanRadiusSigmaLineEdit, okCloseButtonBox);

        retranslateUi(JigsawSetupDialog);
        QObject::connect(okCloseButtonBox, SIGNAL(accepted()), JigsawSetupDialog, SLOT(accept()));
        QObject::connect(okCloseButtonBox, SIGNAL(rejected()), JigsawSetupDialog, SLOT(reject()));

        JigsawSetup->setCurrentIndex(1);


        QMetaObject::connectSlotsByName(JigsawSetupDialog);
    } // setupUi

    void retranslateUi(QDialog *JigsawSetupDialog)
    {
        JigsawSetupDialog->setWindowTitle(QCoreApplication::translate("JigsawSetupDialog", "Jigsaw Setup", nullptr));
        label->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Data</span></p></body></html>", nullptr));
        groupBox_6->setTitle(QString());
        outputControlNetLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"right\">Output Control Net</p></body></html>", nullptr));
        inputControlNetLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"right\">Input Control Net</p></body></html>", nullptr));
        label_2->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Outlier Rejection Options</span></p></body></html>", nullptr));
        groupBox_8->setTitle(QString());
#if QT_CONFIG(tooltip)
        outlierRejectionMultiplierLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>Outlier Rejection Multiplier</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        outlierRejectionMultiplierLineEdit->setText(QCoreApplication::translate("JigsawSetupDialog", "3.0", nullptr));
        outlierRejectionMultiplierLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        outlierRejectionCheckBox->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Image measures are flagged as rejected if their residuals are greater \n"
"than the multiplier times the current standard deviation (sigma).\n"
"\n"
"Must be positive.", nullptr));
#endif // QT_CONFIG(tooltip)
        outlierRejectionCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Sigma Multiplier", nullptr));
        groupBox_7->setTitle(QString());
        maximumLikelihoodModel1ComboBox->setItemText(0, QCoreApplication::translate("JigsawSetupDialog", "NONE", nullptr));
        maximumLikelihoodModel1ComboBox->setItemText(1, QCoreApplication::translate("JigsawSetupDialog", "HUBER", nullptr));
        maximumLikelihoodModel1ComboBox->setItemText(2, QCoreApplication::translate("JigsawSetupDialog", "HUBER MODIFIED", nullptr));

        maximumLikelihoodModel3QuantileLineEdit->setText(QCoreApplication::translate("JigsawSetupDialog", "0.5", nullptr));
        maximumLikelihoodModel2QuantileLineEdit->setText(QCoreApplication::translate("JigsawSetupDialog", "0.5", nullptr));
        maximumLikelihoodModel1QuantileLineEdit->setText(QCoreApplication::translate("JigsawSetupDialog", "0.5", nullptr));
        maximumLikelihoodModel2ComboBox->setItemText(0, QCoreApplication::translate("JigsawSetupDialog", "NONE", nullptr));
        maximumLikelihoodModel2ComboBox->setItemText(1, QCoreApplication::translate("JigsawSetupDialog", "HUBER", nullptr));
        maximumLikelihoodModel2ComboBox->setItemText(2, QCoreApplication::translate("JigsawSetupDialog", "HUBER MODIFIED", nullptr));
        maximumLikelihoodModel2ComboBox->setItemText(3, QCoreApplication::translate("JigsawSetupDialog", "WELSCH", nullptr));
        maximumLikelihoodModel2ComboBox->setItemText(4, QCoreApplication::translate("JigsawSetupDialog", "CHEN", nullptr));

#if QT_CONFIG(tooltip)
        maximumLikelihoodModel2Label->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Valid Range: 1.0e-10 to 1.0", nullptr));
#endif // QT_CONFIG(tooltip)
        maximumLikelihoodModel2Label->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\">Model 2</p></body></html>", nullptr));
        maximumLikelihoodModel3ComboBox->setItemText(0, QCoreApplication::translate("JigsawSetupDialog", "NONE", nullptr));
        maximumLikelihoodModel3ComboBox->setItemText(1, QCoreApplication::translate("JigsawSetupDialog", "HUBER", nullptr));
        maximumLikelihoodModel3ComboBox->setItemText(2, QCoreApplication::translate("JigsawSetupDialog", "HUBER MODIFIED", nullptr));
        maximumLikelihoodModel3ComboBox->setItemText(3, QCoreApplication::translate("JigsawSetupDialog", "WELSCH", nullptr));
        maximumLikelihoodModel3ComboBox->setItemText(4, QCoreApplication::translate("JigsawSetupDialog", "CHEN", nullptr));

#if QT_CONFIG(tooltip)
        maximumLikelihoodModel1Label->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Valid Range: 1.0e-10 to 1.0", nullptr));
#endif // QT_CONFIG(tooltip)
        maximumLikelihoodModel1Label->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\">Model 1</p></body></html>", nullptr));
#if QT_CONFIG(tooltip)
        maximumLikelihoodModel3Label->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Valid Range: 1.0e-10 to 1.0", nullptr));
#endif // QT_CONFIG(tooltip)
        maximumLikelihoodModel3Label->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\">Model 3</p></body></html>", nullptr));
#if QT_CONFIG(tooltip)
        maxLikelihoodEstimationLabel->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Maximum Likelihood Estimation and Sigma Multiplier are exclusive options. \n"
"Set Model 1 to \"NONE\" before checking Sigma Multiplier.", nullptr));
#endif // QT_CONFIG(tooltip)
        maxLikelihoodEstimationLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\">Maximum Likelihood Estimation</p></body></html>", nullptr));
        CQuantileLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "C Quantile", nullptr));
        label_3->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Convergence Criteria</span></p></body></html>", nullptr));
        groupBox_3->setTitle(QString());
        sigma0ThresholdLineEdit->setText(QCoreApplication::translate("JigsawSetupDialog", "1.0e-10", nullptr));
#if QT_CONFIG(tooltip)
        sigma0ThresholdLabel->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Valid Range: 1.0e-10 to 1.0e+10", nullptr));
#endif // QT_CONFIG(tooltip)
        sigma0ThresholdLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"right\">Sigma&amp;0 Threshold</p></body></html>", nullptr));
        maximumIterationsLineEdit->setText(QCoreApplication::translate("JigsawSetupDialog", "50", nullptr));
#if QT_CONFIG(tooltip)
        maximumIterationsLabel->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Valid Range: 1 to 10,000", nullptr));
#endif // QT_CONFIG(tooltip)
        maximumIterationsLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"right\">Ma&amp;ximum Iterations</p></body></html>", nullptr));
        label_4->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Global Apriori Point Sigmas (meters)</span></p></body></html>", nullptr));
        groupBox_4->setTitle(QString());
#if QT_CONFIG(tooltip)
        pointLongitudeSigmaLabel->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Valid Range: 1.0e-10 to 1.0e+10", nullptr));
#endif // QT_CONFIG(tooltip)
        pointLongitudeSigmaLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\">Longitude</p></body></html>", nullptr));
        pointLatitudeSigmaLineEdit->setInputMask(QString());
#if QT_CONFIG(tooltip)
        pointRadiusSigmaCheckBox->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Solve for local point radii. \n"
"\n"
"Valid Range: 1.0e-10 to 1.0e+10", nullptr));
#endif // QT_CONFIG(tooltip)
        pointRadiusSigmaCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Radius", nullptr));
#if QT_CONFIG(tooltip)
        pointLatitudeSigmaLabel->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Valid Range: 1.0e-10 to 1.0e+10", nullptr));
#endif // QT_CONFIG(tooltip)
        pointLatitudeSigmaLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\">Latitude</p></body></html>", nullptr));
        label_5->setText(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Other</span></p></body></html>", nullptr));
        groupBox_5->setTitle(QString());
#if QT_CONFIG(tooltip)
        observationModeCheckBox->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Constrain position and pointing for images within an observation to be identical", nullptr));
#endif // QT_CONFIG(tooltip)
        observationModeCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Observation Mode", nullptr));
#if QT_CONFIG(tooltip)
        errorPropagationCheckBox->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "Compute adjusted parameter uncertainties", nullptr));
#endif // QT_CONFIG(tooltip)
        errorPropagationCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Error Propagation", nullptr));
        JigsawSetup->setTabText(JigsawSetup->indexOf(generalSettingsTab), QCoreApplication::translate("JigsawSetupDialog", "General", nullptr));
        groupBox->setTitle(QCoreApplication::translate("JigsawSetupDialog", "Instrument Position Solve Options", nullptr));
        hermiteSplineCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "over Hermite Spline", nullptr));
        spkSolveDegreeLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "SPK Solve Degree", nullptr));
        spkDegreeLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "SPK Degree", nullptr));
        applySettingsPushButton->setText(QCoreApplication::translate("JigsawSetupDialog", "Apply Settings to Selected Images", nullptr));
        groupBox_2->setTitle(QCoreApplication::translate("JigsawSetupDialog", "Instrument Pointing Solve Options", nullptr));
        twistCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Twist", nullptr));
        ckSolveDegreeLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "CK Solve Degree", nullptr));
        ckDegreeLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "CK Degree", nullptr));
        fitOverPointingCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "over Existing Pointing", nullptr));
        JigsawSetup->setTabText(JigsawSetup->indexOf(observationSolveSettingsTab), QCoreApplication::translate("JigsawSetupDialog", "Observation Solve Settings", nullptr));
        targetLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "Target:", nullptr));
        targetParametersGroupBox->setTitle(QCoreApplication::translate("JigsawSetupDialog", "Target Parameters", nullptr));
#if QT_CONFIG(tooltip)
        primeMeridianOffsetLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori prime meridian offset</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        primeMeridianOffsetLineEdit->setText(QString());
        primeMeridianOffsetLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        spinRateSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>spin rate a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        spinRateSigmaLineEdit->setText(QString());
        spinRateSigmaLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        rightAscensionVelocityLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori pole right ascension velocity</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        rightAscensionVelocityLineEdit->setText(QString());
#if QT_CONFIG(tooltip)
        declinationVelocityLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori pole declination velocity</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        declinationVelocityLineEdit->setText(QString());
#if QT_CONFIG(tooltip)
        declinationSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>pole declination a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        declinationSigmaLineEdit->setText(QString());
        declinationSigmaLineEdit->setPlaceholderText(QString());
        sigmaLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "sigma", nullptr));
#if QT_CONFIG(tooltip)
        declinationLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori pole declination</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        declinationLineEdit->setText(QString());
        declinationLineEdit->setPlaceholderText(QString());
        valueLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "value", nullptr));
#if QT_CONFIG(tooltip)
        rightAscensionSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>pole right ascension a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        rightAscensionSigmaLineEdit->setText(QString());
        rightAscensionSigmaLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        poleRaCheckBox->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "valid range: 0 to 360 degrees", nullptr));
#endif // QT_CONFIG(tooltip)
        poleRaCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Pole Right Ascension", nullptr));
#if QT_CONFIG(tooltip)
        poleDecCheckBox->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "valid range: -90 to +90 degrees", nullptr));
#endif // QT_CONFIG(tooltip)
        poleDecCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Pole Declination", nullptr));
#if QT_CONFIG(tooltip)
        rightAscensionVelocitySigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>pole right ascension velocity a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        rightAscensionVelocitySigmaLineEdit->setText(QString());
#if QT_CONFIG(tooltip)
        declinationVelocitySigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>pole declination velocity a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        declinationVelocitySigmaLineEdit->setText(QString());
        poleRaVelocityCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Pole Right Ascension Velocity", nullptr));
        poleDecVelocityCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Pole Declination Velocity", nullptr));
#if QT_CONFIG(tooltip)
        primeMeridianOffsetCheckBox->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "valid range: 0 to 360 degrees", nullptr));
#endif // QT_CONFIG(tooltip)
        primeMeridianOffsetCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Prime Meridian Offset (W0)", nullptr));
#if QT_CONFIG(tooltip)
        primeMeridianOffsetSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>prime meridian offset a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        primeMeridianOffsetSigmaLineEdit->setText(QString());
        primeMeridianOffsetSigmaLineEdit->setPlaceholderText(QString());
        spinRateCheckBox->setText(QCoreApplication::translate("JigsawSetupDialog", "Spin Rate (WDot)", nullptr));
#if QT_CONFIG(tooltip)
        spinRateLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori spin rate</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        spinRateLineEdit->setText(QString());
        spinRateLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        rightAscensionLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori pole right ascension</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        rightAscensionLineEdit->setText(QString());
        rightAscensionLineEdit->setPlaceholderText(QString());
        radiiGroupBox->setTitle(QCoreApplication::translate("JigsawSetupDialog", "Radii", nullptr));
        meanRadiusRadioButton->setText(QCoreApplication::translate("JigsawSetupDialog", "&mean radius", nullptr));
        bRadiusLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "b", nullptr));
        cRadiusLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "c", nullptr));
#if QT_CONFIG(tooltip)
        aRadiusLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori a radius</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        aRadiusLineEdit->setText(QString());
        aRadiusLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        aRadiusSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a radius a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        aRadiusSigmaLineEdit->setText(QString());
        aRadiusSigmaLineEdit->setPlaceholderText(QString());
        triaxialRadiiRadioButton->setText(QCoreApplication::translate("JigsawSetupDialog", "tria&xial radii", nullptr));
#if QT_CONFIG(tooltip)
        cRadiusLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori c radius</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        cRadiusLineEdit->setText(QString());
        cRadiusLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        meanRadiusLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori mean radius</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        meanRadiusLineEdit->setText(QString());
        meanRadiusLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        bRadiusSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>b radius a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        bRadiusSigmaLineEdit->setText(QString());
        bRadiusSigmaLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        cRadiusSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>c radius a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        cRadiusSigmaLineEdit->setText(QString());
        cRadiusSigmaLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        meanRadiusSigmaLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>mean radius a priori sigma</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        meanRadiusSigmaLineEdit->setText(QString());
        meanRadiusSigmaLineEdit->setPlaceholderText(QString());
#if QT_CONFIG(tooltip)
        bRadiusLineEdit->setToolTip(QCoreApplication::translate("JigsawSetupDialog", "<html><head/><body><p>a priori b radius</p></body></html>", nullptr));
#endif // QT_CONFIG(tooltip)
        bRadiusLineEdit->setText(QString());
        bRadiusLineEdit->setPlaceholderText(QString());
        aRadiusLabel->setText(QCoreApplication::translate("JigsawSetupDialog", "a", nullptr));
        noneRadiiRadioButton->setText(QCoreApplication::translate("JigsawSetupDialog", "none", nullptr));
        targetParametersMessage->setText(QCoreApplication::translate("JigsawSetupDialog", "TextLabel", nullptr));
        JigsawSetup->setTabText(JigsawSetup->indexOf(targetBodyTab), QCoreApplication::translate("JigsawSetupDialog", "Target Body", nullptr));
    } // retranslateUi

};

namespace Ui {
    class JigsawSetupDialog: public Ui_JigsawSetupDialog {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_JIGSAWSETUPDIALOG_H
