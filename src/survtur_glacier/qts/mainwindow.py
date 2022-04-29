# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/hdd/files/Dropbox/Personal/Python/survtur_glacier/src/survtur_glacier/qts/mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(713, 634)
        MainWindow.setStyleSheet("")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.newTasksTable = TasksTable(self.centralwidget)
        self.newTasksTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.newTasksTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.newTasksTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.newTasksTable.setObjectName("newTasksTable")
        self.newTasksTable.setColumnCount(2)
        self.newTasksTable.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.newTasksTable.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.newTasksTable.setHorizontalHeaderItem(1, item)
        self.newTasksTable.horizontalHeader().setHighlightSections(False)
        self.newTasksTable.verticalHeader().setVisible(False)
        self.verticalLayout_2.addWidget(self.newTasksTable)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.horizontalLayout_3.addWidget(self.label)
        self.btnActiveTasks = QtWidgets.QPushButton(self.centralwidget)
        self.btnActiveTasks.setCheckable(True)
        self.btnActiveTasks.setObjectName("btnActiveTasks")
        self.horizontalLayout_3.addWidget(self.btnActiveTasks)
        self.btnFaultyTasks = QtWidgets.QPushButton(self.centralwidget)
        self.btnFaultyTasks.setCheckable(True)
        self.btnFaultyTasks.setObjectName("btnFaultyTasks")
        self.horizontalLayout_3.addWidget(self.btnFaultyTasks)
        self.btnSucceedTasks = QtWidgets.QPushButton(self.centralwidget)
        self.btnSucceedTasks.setCheckable(True)
        self.btnSucceedTasks.setObjectName("btnSucceedTasks")
        self.horizontalLayout_3.addWidget(self.btnSucceedTasks)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2.addLayout(self.verticalLayout_2)
        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)
        self.vaultContent = QtWidgets.QVBoxLayout()
        self.vaultContent.setObjectName("vaultContent")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.requestInventoryBtn = QtWidgets.QToolButton(self.centralwidget)
        self.requestInventoryBtn.setAutoRaise(True)
        self.requestInventoryBtn.setObjectName("requestInventoryBtn")
        self.horizontalLayout.addWidget(self.requestInventoryBtn)
        self.vaultSelector = QtWidgets.QComboBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.vaultSelector.sizePolicy().hasHeightForWidth())
        self.vaultSelector.setSizePolicy(sizePolicy)
        self.vaultSelector.setCurrentText("")
        self.vaultSelector.setObjectName("vaultSelector")
        self.horizontalLayout.addWidget(self.vaultSelector)
        self.currentPathTxt = QtWidgets.QLineEdit(self.centralwidget)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.currentPathTxt.setPalette(palette)
        self.currentPathTxt.setAutoFillBackground(False)
        self.currentPathTxt.setFrame(False)
        self.currentPathTxt.setReadOnly(True)
        self.currentPathTxt.setObjectName("currentPathTxt")
        self.horizontalLayout.addWidget(self.currentPathTxt)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.btnMkdir = QtWidgets.QToolButton(self.centralwidget)
        self.btnMkdir.setAutoRaise(True)
        self.btnMkdir.setObjectName("btnMkdir")
        self.horizontalLayout.addWidget(self.btnMkdir)
        self.btnUpload = QtWidgets.QPushButton(self.centralwidget)
        self.btnUpload.setObjectName("btnUpload")
        self.horizontalLayout.addWidget(self.btnUpload)
        self.searchLine = QtWidgets.QLineEdit(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.searchLine.sizePolicy().hasHeightForWidth())
        self.searchLine.setSizePolicy(sizePolicy)
        self.searchLine.setObjectName("searchLine")
        self.horizontalLayout.addWidget(self.searchLine)
        self.vaultContent.addLayout(self.horizontalLayout)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.inventoryView = InventoryTableView(self.centralwidget)
        self.inventoryView.setMouseTracking(True)
        self.inventoryView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.inventoryView.setAcceptDrops(True)
        self.inventoryView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.inventoryView.setTabKeyNavigation(True)
        self.inventoryView.setDragEnabled(True)
        self.inventoryView.setAlternatingRowColors(True)
        self.inventoryView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.inventoryView.setShowGrid(False)
        self.inventoryView.setSortingEnabled(True)
        self.inventoryView.setObjectName("inventoryView")
        self.inventoryView.horizontalHeader().setHighlightSections(False)
        self.inventoryView.verticalHeader().setVisible(False)
        self.verticalLayout_3.addWidget(self.inventoryView)
        self.inventoryStatus = QtWidgets.QLabel(self.centralwidget)
        self.inventoryStatus.setEnabled(True)
        self.inventoryStatus.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.inventoryStatus.setObjectName("inventoryStatus")
        self.verticalLayout_3.addWidget(self.inventoryStatus)
        self.vaultContent.addLayout(self.verticalLayout_3)
        self.gridLayout.addLayout(self.vaultContent, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 713, 23))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionFastGlacier_style = QtWidgets.QAction(MainWindow)
        self.actionFastGlacier_style.setObjectName("actionFastGlacier_style")
        self.actionSurvturGlacier_style = QtWidgets.QAction(MainWindow)
        self.actionSurvturGlacier_style.setObjectName("actionSurvturGlacier_style")

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "SurvturGlacierGui"))
        item = self.newTasksTable.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "New Column"))
        item = self.newTasksTable.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Progress"))
        self.label.setText(_translate("MainWindow", "Show tasks:"))
        self.btnActiveTasks.setStatusTip(_translate("MainWindow", "Show tasks that are executing now or just planned."))
        self.btnActiveTasks.setText(_translate("MainWindow", "Active"))
        self.btnFaultyTasks.setStatusTip(_translate("MainWindow", "Show tasks that have problems. These task can be restarted or deleted."))
        self.btnFaultyTasks.setText(_translate("MainWindow", "Faulty"))
        self.btnSucceedTasks.setStatusTip(_translate("MainWindow", "List of tasts that did what they have to."))
        self.btnSucceedTasks.setText(_translate("MainWindow", "Succeed"))
        self.requestInventoryBtn.setToolTip(_translate("MainWindow", "Request new vault inventory"))
        self.requestInventoryBtn.setStatusTip(_translate("MainWindow", "Request new inventory for vault."))
        self.requestInventoryBtn.setText(_translate("MainWindow", "R"))
        self.vaultSelector.setStatusTip(_translate("MainWindow", "Current vault and its size."))
        self.currentPathTxt.setStatusTip(_translate("MainWindow", "Current location in a vault."))
        self.currentPathTxt.setPlaceholderText(_translate("MainWindow", "root"))
        self.btnMkdir.setToolTip(_translate("MainWindow", "Create new folder…"))
        self.btnMkdir.setStatusTip(_translate("MainWindow", "Create directory"))
        self.btnMkdir.setText(_translate("MainWindow", "D"))
        self.btnUpload.setToolTip(_translate("MainWindow", "Upload files…"))
        self.btnUpload.setStatusTip(_translate("MainWindow", "Upload one or more files to current folder."))
        self.btnUpload.setText(_translate("MainWindow", "Upload…"))
        self.searchLine.setStatusTip(_translate("MainWindow", "Search for this text at whole vault."))
        self.searchLine.setPlaceholderText(_translate("MainWindow", "Search…"))
        self.inventoryStatus.setText(_translate("MainWindow", "TextLabel"))
        self.actionFastGlacier_style.setText(_translate("MainWindow", "FastGlacier style"))
        self.actionSurvturGlacier_style.setText(_translate("MainWindow", "SurvturGlacier style"))
from .widgets.inventory_table_view import InventoryTableView
from .widgets.tasks_table import TasksTable