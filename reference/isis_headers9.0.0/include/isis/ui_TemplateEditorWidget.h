/********************************************************************************
** Form generated from reading UI file 'TemplateEditorWidget.ui'
**
** Created by: Qt User Interface Compiler version 5.15.8
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_TEMPLATEEDITORWIDGET_H
#define UI_TEMPLATEEDITORWIDGET_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QFrame>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QTextEdit>
#include <QtWidgets/QVBoxLayout>

QT_BEGIN_NAMESPACE

class Ui_TemplateEditorWidget
{
public:
    QVBoxLayout *verticalLayout;
    QTextEdit *templateTextEdit;
    QPushButton *templateTextSave;
    QPushButton *templateTextSaveAs;

    void setupUi(QFrame *TemplateEditorWidget)
    {
        if (TemplateEditorWidget->objectName().isEmpty())
            TemplateEditorWidget->setObjectName(QString::fromUtf8("TemplateEditorWidget"));
        TemplateEditorWidget->resize(0, 0);
        TemplateEditorWidget->setMinimumSize(QSize(0, 0));
        TemplateEditorWidget->setMaximumSize(QSize(420, 16777215));
        verticalLayout = new QVBoxLayout(TemplateEditorWidget);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        templateTextEdit = new QTextEdit(TemplateEditorWidget);
        templateTextEdit->setObjectName(QString::fromUtf8("templateTextEdit"));
        QFont font;
        font.setPointSize(10);
        templateTextEdit->setFont(font);

        verticalLayout->addWidget(templateTextEdit);

        templateTextSave = new QPushButton(TemplateEditorWidget);
        templateTextSave->setObjectName(QString::fromUtf8("templateTextSave"));

        verticalLayout->addWidget(templateTextSave);

        templateTextSaveAs = new QPushButton(TemplateEditorWidget);
        templateTextSaveAs->setObjectName(QString::fromUtf8("templateTextSaveAs"));

        verticalLayout->addWidget(templateTextSaveAs);


        retranslateUi(TemplateEditorWidget);

        QMetaObject::connectSlotsByName(TemplateEditorWidget);
    } // setupUi

    void retranslateUi(QFrame *TemplateEditorWidget)
    {
        TemplateEditorWidget->setWindowTitle(QCoreApplication::translate("TemplateEditorWidget", "DockWidget", nullptr));
        templateTextSave->setText(QCoreApplication::translate("TemplateEditorWidget", " Save Changes ", nullptr));
        templateTextSaveAs->setText(QCoreApplication::translate("TemplateEditorWidget", " Save Changes As... ", nullptr));
    } // retranslateUi

};

namespace Ui {
    class TemplateEditorWidget: public Ui_TemplateEditorWidget {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_TEMPLATEEDITORWIDGET_H
