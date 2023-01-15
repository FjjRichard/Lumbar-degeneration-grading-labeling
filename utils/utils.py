# -*- coding: utf-8 -*-
import SimpleITK as sitk


def wwwc(sitkImage, max=1500, min=-550):
    # 设置窗宽窗位
    intensityWindow = sitk.IntensityWindowingImageFilter()
    intensityWindow.SetWindowMaximum(max)
    intensityWindow.SetWindowMinimum(min)
    sitkImage = intensityWindow.Execute(sitkImage)
    return sitkImage


def readNii(path, ww, wc, isflipud):
    """读取和加载数据"""
    if type(path) == str:
        img = wwwc(sitk.ReadImage(path), ww, wc)
    else:
        img = wwwc(path, ww, wc)
    data = sitk.GetArrayFromImage(img)
    # 图像是上下翻转的，所有把他们翻转过来
    # print(isflipud)
    # if isflipud:
    #     data = np.flip(data,1)
    return data



