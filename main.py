# -*- coding: utf-8 -*-


import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from PyQt5.QtWidgets import QApplication, QTableWidgetItem
from PyQt5 import uic

import glob
import numpy as np
import SimpleITK as sitk
import os

from utils.utils import readNii
from widgets.canvas import Canvas
import json


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi("UIFile.ui")
        self.ui.setGeometry(QApplication.desktop().availableGeometry())
        self.ui.canvas = Canvas(self.ui.graphicsView)
        self.ui.canvas.wheeled.connect(self.myWheel)

        self.initUI()

        #是否翻转
        self.isflipud = False
        self.sitkImage = object()
        self.npImage = object()
        self.currIndex = 0  # 记录当前第几层
        self.maxCurrIndex = 0  # 记录数据的最大层
        self.minCurrIndex = 0  # 记录数据的最小层，其实就是0
        self.baseFileName = ''

        #菜单栏
        self.ui.openfold.triggered.connect(self.openFold)
        self.ui.setWindowTitle('腰椎间盘退变等级标注工具')

        self.ui.isflipud.triggered.connect(self.setIsflipud)



        # 宽宽窗位滑动条
        self.ui.slider_ww.valueChanged.connect(self.resetWWWcAndShow)

        self.ui.slider_wc.valueChanged.connect(self.resetWWWcAndShow)


        # 设置窗宽窗位文本框只能输入一定范围的整数
        intValidator = QIntValidator(self)
        intValidator.setRange(0, 2000)
        self.ui.line_ww.setValidator(intValidator)
        self.ui.line_ww.editingFinished.connect(self.resetWWWcAndShow)
        self.ui.line_wc.setValidator(intValidator)
        self.ui.line_wc.editingFinished.connect(self.resetWWWcAndShow)

        #表格
        self.ui.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tableWidget.doubleClicked.connect(self.tabelDoubleClicked)
        self.ui.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)

        #保存按钮
        self.ui.savebn.clicked.connect(self.saveLabel)
        self.ui.savebn.setEnabled(False)


    def initUI(self):
        try:
            self.max = 0
            self.min = 0
            self.ui.line_ww.setText(str(self.max))
            self.ui.line_wc.setText(str(self.min))
            self.ui.slider_ww.setValue(self.max)
            self.ui.slider_wc.setValue(self.min)
            self.currWw = 0
            self.currWc = 0

            self.ui.picture.setPixmap(QPixmap("./image/label.png")) # 只有图片
        except Exception as e:
            QMessageBox.warning(self,"warn",str(e),QMessageBox.Yes,QMessageBox.Yes)


    def openFold(self):
        """
        打开文件夹，读取文件的nii文件
        """
        self.ui.tableWidget.clearContents()
        self.dirPath = QFileDialog.getExistingDirectory(self,
                                                      "选取文件",
                                                      "./")
        
        self.nameFileNames = glob.glob(self.dirPath+"/*.nii.gz") 
        self.nameFileNames = sorted(self.nameFileNames)

        self.initTabelWidgetUI()
        self.ui.savebn.setEnabled(True)


    def setIsflipud(self):
        if self.isflipud:
            self.isflipud = False
        else:
            self.isflipud = True


    def initTabelWidgetUI(self):
        """
        读取文件夹之后，设置表格的属性
        """
        self.ui.tableWidget.setRowCount(len(self.nameFileNames))
        self.ui.tableWidget.setColumnCount(2)

        for index ,name in enumerate(self.nameFileNames) :
            baseName = os.path.basename(name)
            jsonNamePath = name.replace('.nii.gz','.json')
            nameItem = QTableWidgetItem(baseName)

            self.ui.tableWidget.setItem(index,1,nameItem)

            self.ui.tableWidget.setColumnWidth(0,16)
            self.ui.tableWidget.setColumnWidth(1,200)
            self.ui.tableWidget.setRowHeight(index,16)

            label = self.labelPng(os.path.exists(jsonNamePath))
            self.ui.tableWidget.setCellWidget(index, 0, label) 

    def labelPng(self,isLabel=True):
        """
        设置label为图片
        """
        label = QLabel("")
        label.setAlignment(Qt.AlignCenter) # 水平居中
        if isLabel:
            label.setPixmap(QPixmap("./image/green.png").scaled(16, 16)) # 只有图片
        else:
            label.setPixmap(QPixmap("./image/red.png").scaled(16, 16)) # 只有图片

        return label

    def tabelDoubleClicked(self,index):
        """
        表格双击事件，双击之后读取对应的文件
        """
        self.currentRow = index.row()
        self.currentFileName = self.ui.tableWidget.item(self.currentRow , 1).text()
        self.readFile()
        self.showLabel()

        
    def showLabel(self):
        jsonSavePath = os.path.join(self.dirPath,self.currentFileName).replace('.nii.gz','.json')
        if os.path.exists(jsonSavePath):
            with open(jsonSavePath) as file_obj:
                data = json.load(file_obj)

            if data is not None:
                self.ui.L5_S1CB.setCurrentIndex(data['L5_S1'] if data['L5_S1']!= -1 else 0)
                self.ui.L4_L5CB.setCurrentIndex(data['L4_L5'] if data['L4_L5']!= -1 else 0)
                self.ui.L3_L4CB.setCurrentIndex(data['L3_L4'] if data['L3_L4']!= -1 else 0)
                self.ui.L2_L3CB.setCurrentIndex(data['L2_L3'] if data['L2_L3']!= -1 else 0)
                self.ui.L1_L2CB.setCurrentIndex(data['L1_L2'] if data['L1_L2']!= -1 else 0)
        else:

                self.ui.L5_S1CB.setCurrentIndex(0)
                self.ui.L4_L5CB.setCurrentIndex(0)
                self.ui.L3_L4CB.setCurrentIndex(0)
                self.ui.L2_L3CB.setCurrentIndex(0)
                self.ui.L1_L2CB.setCurrentIndex(0)


    def readFile(self):
        """
        读取医疗文件
        """

        if self.currentFileName:
            filePath = os.path.join(self.dirPath,self.currentFileName)

            self.sitkImage = sitk.ReadImage(filePath)
            self.maxValue = np.max(sitk.GetArrayFromImage(self.sitkImage))
            self.minValue = np.min(sitk.GetArrayFromImage(self.sitkImage))
            self.max = int(self.maxValue/2)
            self.min = int(self.minValue)

            self.npImage = readNii(self.sitkImage, self.max, self.min,self.isflipud)

            self.maxCurrIndex = self.npImage.shape[0]
            self.currIndex = int(self.maxCurrIndex / 2)
            self.resetWWWC()

            self.showImg(self.npImage[self.currIndex])


    def saveLabel(self):
        """保存标注"""
        data = dict()
        data['L5_S1'] = int(self.ui.L5_S1CB.currentText())
        data['L4_L5'] = int(self.ui.L4_L5CB.currentText())
        data['L3_L4'] = int(self.ui.L3_L4CB.currentText())
        data['L2_L3'] = int(self.ui.L2_L3CB.currentText())
        data['L1_L2'] = int(self.ui.L1_L2CB.currentText())
        if -1 in list(data.values()):
            QMessageBox.warning(self,"警告","还有椎间盘没有标注,不能保存!",QMessageBox.Yes,QMessageBox.Yes)
        else:
            jsonSavePath = os.path.join(self.dirPath,self.currentFileName).replace('.nii.gz','.json')
            with open(jsonSavePath, 'w') as json_file:
                json_file.write(json.dumps(data, ensure_ascii=False, indent=4))

            label = self.labelPng(isLabel=True)
            self.ui.tableWidget.setCellWidget(self.currentRow, 0, label) 


    def showImg(self, img):
        """
        显示图片
        """
        if self.isflipud:#是否图像翻转
            img = np.flipud(img)
        try:
            if img.ndim == 2:
                img = np.expand_dims(img, axis=2)
                img = np.concatenate((img, img, img), axis=-1).astype(np.uint8)
            elif img.ndim == 3:
                img = img.astype(np.uint8)
            qimage = QImage(img, img.shape[0], img.shape[1], img.shape[1] * 3, QImage.Format_RGB888)
            pixmap_imgSrc = QPixmap.fromImage(qimage)

            self.ui.canvas.addScenes(pixmap_imgSrc,self.currIndex)
        except Exception as e:
            QMessageBox.warning(self,"warn",str(e),QMessageBox.Yes,QMessageBox.Yes)



    def resetWWWC(self):
            self.ui.line_ww.setText(str(self.max))
            self.ui.line_wc.setText(str(self.min))
            self.ui.slider_ww.setValue(self.max)
            self.ui.slider_wc.setValue(self.min)

            self.ui.slider_ww.setMinimum(self.minValue)
            self.ui.slider_ww.setMaximum(self.maxValue)
            intValidator = QIntValidator(self)
            intValidator.setRange(self.minValue, self.maxValue)
            self.ui.line_ww.setValidator(intValidator)
            self.ui.line_wc.setValidator(intValidator)


            self.currWw = self.max
            self.currWc = self.min

    def resetWWWcAndShow(self):
        """
        修改医学图像的窗宽窗位，
        每次修改后都会在界面呈现出来
        """
        if hasattr(self.sender(), "objectName"):
            objectName = self.sender().objectName()
        else:
            objectName = None
        try:

            if objectName == 'slider_ww' or objectName == 'slider_wc':
                self.currWw = self.ui.slider_ww.value()
                self.currWc = self.ui.slider_wc.value()
                self.ui.line_ww.setText(str(self.ui.slider_ww.value()))
                self.ui.line_wc.setText(str(self.ui.slider_wc.value()))


            elif objectName == 'line_ww' or objectName == 'line_wc':
                self.currWw = int(self.ui.line_ww.text())
                self.currWc = int(self.ui.line_wc.text())
                self.ui.slider_ww.setValue(self.currWw)
                self.ui.slider_wc.setValue(self.currWc)

            if self.maxCurrIndex != self.minCurrIndex:
                self.npImage = readNii(self.sitkImage, self.currWw, self.currWc,self.isflipud)

                self.showImg(self.npImage[self.currIndex])
        except Exception as e:
            QMessageBox.warning(self,"warn",str(e),QMessageBox.Yes,QMessageBox.Yes)


    """画布事件"""
    def myWheel(self,currIndex):
        """
        滚轮切换上下层
        """
        try:
            if self.maxCurrIndex != self.minCurrIndex:
                if currIndex > self.maxCurrIndex-1 :
                    self.currIndex = self.maxCurrIndex-1
                elif currIndex < 0:
                    self.currIndex = 0
                else:
                    self.currIndex = currIndex

                self.showImg(self.npImage[self.currIndex])
        except Exception as e:
            QMessageBox.warning(self,"warn",str(e),QMessageBox.Yes,QMessageBox.Yes)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainWindow()
    
    main.ui.show()
    
    sys.exit(app.exec_())
