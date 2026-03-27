/********************************************************************************
** Form generated from reading UI file 'ProfileDialog.ui'
**
** Created by: Qt User Interface Compiler version 5.15.8
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_PROFILEDIALOG_H
#define UI_PROFILEDIALOG_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QDialog>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_ProfileDialog
{
public:
    QWidget *widget;
    QVBoxLayout *verticalLayout;
    QPushButton *createStartButton;
    QPushButton *createEndButton;
    QHBoxLayout *horizontalLayout;
    QPushButton *helpButton;
    QPushButton *profileButton;
    QPushButton *cancelButton;

    void setupUi(QDialog *ProfileDialog)
    {
        if (ProfileDialog->objectName().isEmpty())
            ProfileDialog->setObjectName(QString::fromUtf8("ProfileDialog"));
        ProfileDialog->resize(271, 168);
        widget = new QWidget(ProfileDialog);
        widget->setObjectName(QString::fromUtf8("widget"));
        widget->setGeometry(QRect(10, 32, 249, 103));
        verticalLayout = new QVBoxLayout(widget);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        verticalLayout->setContentsMargins(0, 0, 0, 0);
        createStartButton = new QPushButton(widget);
        createStartButton->setObjectName(QString::fromUtf8("createStartButton"));

        verticalLayout->addWidget(createStartButton);

        createEndButton = new QPushButton(widget);
        createEndButton->setObjectName(QString::fromUtf8("createEndButton"));

        verticalLayout->addWidget(createEndButton);

        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        helpButton = new QPushButton(widget);
        helpButton->setObjectName(QString::fromUtf8("helpButton"));

        horizontalLayout->addWidget(helpButton);

        profileButton = new QPushButton(widget);
        profileButton->setObjectName(QString::fromUtf8("profileButton"));
        profileButton->setEnabled(false);

        horizontalLayout->addWidget(profileButton);

        cancelButton = new QPushButton(widget);
        cancelButton->setObjectName(QString::fromUtf8("cancelButton"));

        horizontalLayout->addWidget(cancelButton);


        verticalLayout->addLayout(horizontalLayout);


        retranslateUi(ProfileDialog);
        QObject::connect(profileButton, SIGNAL(clicked()), ProfileDialog, SLOT(accept()));
        QObject::connect(cancelButton, SIGNAL(clicked()), ProfileDialog, SLOT(reject()));

        QMetaObject::connectSlotsByName(ProfileDialog);
    } // setupUi

    void retranslateUi(QDialog *ProfileDialog)
    {
        ProfileDialog->setWindowTitle(QCoreApplication::translate("ProfileDialog", "Select Profile Endpoints", nullptr));
        createStartButton->setText(QCoreApplication::translate("ProfileDialog", "Create Start Point", nullptr));
        createEndButton->setText(QCoreApplication::translate("ProfileDialog", "Create End Point", nullptr));
        helpButton->setText(QCoreApplication::translate("ProfileDialog", "Help", nullptr));
        profileButton->setText(QCoreApplication::translate("ProfileDialog", "Profile", nullptr));
        cancelButton->setText(QCoreApplication::translate("ProfileDialog", "Cancel", nullptr));
    } // retranslateUi

};

namespace Ui {
    class ProfileDialog: public Ui_ProfileDialog {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_PROFILEDIALOG_H
