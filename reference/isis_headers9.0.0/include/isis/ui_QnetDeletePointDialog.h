/********************************************************************************
** Form generated from reading UI file 'QnetDeletePointDialog.ui'
**
** Created by: Qt User Interface Compiler version 5.15.8
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_QNETDELETEPOINTDIALOG_H
#define UI_QNETDELETEPOINTDIALOG_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QDialog>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QListWidget>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_QnetDeletePointDialog
{
public:
    QWidget *deletePointLayoutWidget;
    QWidget *widget;
    QWidget *widget1;
    QWidget *widget2;
    QVBoxLayout *vboxLayout;
    QHBoxLayout *hboxLayout;
    QLabel *pointIdLabel;
    QLineEdit *pointIdValue;
    QCheckBox *deleteAllCheckBox;
    QHBoxLayout *hboxLayout1;
    QLabel *orLabel;
    QSpacerItem *spacerItem;
    QLabel *imageLabel;
    QListWidget *fileList;
    QHBoxLayout *hboxLayout2;
    QSpacerItem *spacerItem1;
    QPushButton *okButton;
    QPushButton *cancelButton;

    void setupUi(QDialog *QnetDeletePointDialog)
    {
        if (QnetDeletePointDialog->objectName().isEmpty())
            QnetDeletePointDialog->setObjectName(QString::fromUtf8("QnetDeletePointDialog"));
        QnetDeletePointDialog->resize(278, 374);
        QnetDeletePointDialog->setModal(true);
        deletePointLayoutWidget = new QWidget(QnetDeletePointDialog);
        deletePointLayoutWidget->setObjectName(QString::fromUtf8("deletePointLayoutWidget"));
        deletePointLayoutWidget->setGeometry(QRect(20, 250, 351, 33));
        widget = new QWidget(QnetDeletePointDialog);
        widget->setObjectName(QString::fromUtf8("widget"));
        widget->setGeometry(QRect(10, 10, 258, 284));
        widget1 = new QWidget(QnetDeletePointDialog);
        widget1->setObjectName(QString::fromUtf8("widget1"));
        widget1->setGeometry(QRect(10, 20, 258, 321));
        widget2 = new QWidget(QnetDeletePointDialog);
        widget2->setObjectName(QString::fromUtf8("widget2"));
        widget2->setGeometry(QRect(10, 10, 258, 348));
        vboxLayout = new QVBoxLayout(widget2);
#ifndef Q_OS_MAC
        vboxLayout->setSpacing(6);
#endif
        vboxLayout->setContentsMargins(0, 0, 0, 0);
        vboxLayout->setObjectName(QString::fromUtf8("vboxLayout"));
        vboxLayout->setContentsMargins(0, 0, 0, 0);
        hboxLayout = new QHBoxLayout();
#ifndef Q_OS_MAC
        hboxLayout->setSpacing(6);
#endif
#ifndef Q_OS_MAC
        hboxLayout->setContentsMargins(0, 0, 0, 0);
#endif
        hboxLayout->setObjectName(QString::fromUtf8("hboxLayout"));
        pointIdLabel = new QLabel(widget2);
        pointIdLabel->setObjectName(QString::fromUtf8("pointIdLabel"));

        hboxLayout->addWidget(pointIdLabel);

        pointIdValue = new QLineEdit(widget2);
        pointIdValue->setObjectName(QString::fromUtf8("pointIdValue"));
        pointIdValue->setReadOnly(true);

        hboxLayout->addWidget(pointIdValue);


        vboxLayout->addLayout(hboxLayout);

        deleteAllCheckBox = new QCheckBox(widget2);
        deleteAllCheckBox->setObjectName(QString::fromUtf8("deleteAllCheckBox"));

        vboxLayout->addWidget(deleteAllCheckBox);

        hboxLayout1 = new QHBoxLayout();
#ifndef Q_OS_MAC
        hboxLayout1->setSpacing(6);
#endif
        hboxLayout1->setContentsMargins(0, 0, 0, 0);
        hboxLayout1->setObjectName(QString::fromUtf8("hboxLayout1"));
        orLabel = new QLabel(widget2);
        orLabel->setObjectName(QString::fromUtf8("orLabel"));
        orLabel->setAlignment(Qt::AlignHCenter);

        hboxLayout1->addWidget(orLabel);

        spacerItem = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        hboxLayout1->addItem(spacerItem);


        vboxLayout->addLayout(hboxLayout1);

        imageLabel = new QLabel(widget2);
        imageLabel->setObjectName(QString::fromUtf8("imageLabel"));

        vboxLayout->addWidget(imageLabel);

        fileList = new QListWidget(widget2);
        fileList->setObjectName(QString::fromUtf8("fileList"));
        fileList->setSelectionMode(QAbstractItemView::ExtendedSelection);

        vboxLayout->addWidget(fileList);

        hboxLayout2 = new QHBoxLayout();
#ifndef Q_OS_MAC
        hboxLayout2->setSpacing(6);
#endif
        hboxLayout2->setContentsMargins(0, 0, 0, 0);
        hboxLayout2->setObjectName(QString::fromUtf8("hboxLayout2"));
        spacerItem1 = new QSpacerItem(41, 31, QSizePolicy::Expanding, QSizePolicy::Minimum);

        hboxLayout2->addItem(spacerItem1);

        okButton = new QPushButton(widget2);
        okButton->setObjectName(QString::fromUtf8("okButton"));

        hboxLayout2->addWidget(okButton);

        cancelButton = new QPushButton(widget2);
        cancelButton->setObjectName(QString::fromUtf8("cancelButton"));

        hboxLayout2->addWidget(cancelButton);


        vboxLayout->addLayout(hboxLayout2);

        QWidget::setTabOrder(pointIdValue, fileList);
        QWidget::setTabOrder(fileList, deleteAllCheckBox);
        QWidget::setTabOrder(deleteAllCheckBox, okButton);
        QWidget::setTabOrder(okButton, cancelButton);

        retranslateUi(QnetDeletePointDialog);
        QObject::connect(okButton, SIGNAL(clicked()), QnetDeletePointDialog, SLOT(accept()));
        QObject::connect(cancelButton, SIGNAL(clicked()), QnetDeletePointDialog, SLOT(reject()));

        QMetaObject::connectSlotsByName(QnetDeletePointDialog);
    } // setupUi

    void retranslateUi(QDialog *QnetDeletePointDialog)
    {
        QnetDeletePointDialog->setWindowTitle(QCoreApplication::translate("QnetDeletePointDialog", "Delete ControlPoint", nullptr));
        pointIdLabel->setText(QCoreApplication::translate("QnetDeletePointDialog", "ControlPoint ID:", nullptr));
        deleteAllCheckBox->setText(QCoreApplication::translate("QnetDeletePointDialog", "Delete ControlPoint", nullptr));
        orLabel->setText(QCoreApplication::translate("QnetDeletePointDialog", "Or", nullptr));
        imageLabel->setText(QCoreApplication::translate("QnetDeletePointDialog", "Select images to remove from ControlPoint", nullptr));
        okButton->setText(QCoreApplication::translate("QnetDeletePointDialog", "OK", nullptr));
        cancelButton->setText(QCoreApplication::translate("QnetDeletePointDialog", "Cancel", nullptr));
    } // retranslateUi

};

namespace Ui {
    class QnetDeletePointDialog: public Ui_QnetDeletePointDialog {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_QNETDELETEPOINTDIALOG_H
