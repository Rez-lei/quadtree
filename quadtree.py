# ！/usr/bin/env python3
# --- coding:utf-8 ---
# File: quadtree.py
# Author: Zhanglei  Time: 2023/5/4 15:12


import numpy as np
import os
from osgeo import ogr, osr


class Point:
    def __init__(self, x, y, point_id):
        self.x = x
        self.y = y
        self.point_id = point_id


class QuadTree:
    def __init__(self, x, y, width, height, depth=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.depth = depth
        self.points = []
        self.children = None

    def insert(self, point):
        if not self.contains(point):  # 点实体不在当前网格范围内，插入失败
            return False

        if len(self.points) < 1:
            self.points.append(point)
            return True

        if self.children is None:
            self.split()

        for child in self.children:
            if child.insert(point):
                return True

        return False

    def split(self):
        x1 = self.x
        y1 = self.y
        w2 = self.width / 2
        h2 = self.height / 2

        self.children = [
            QuadTree(x1, y1, w2, h2, self.depth + 1),
            QuadTree(x1 + w2, y1, w2, h2, self.depth + 1),
            QuadTree(x1, y1 - h2, w2, h2, self.depth + 1),
            QuadTree(x1 + w2, y1 - h2, w2, h2, self.depth + 1)
        ]

        for point in self.points:
            for child in self.children:
                child.insert(point)
        # 这里将points设为空存在问题，后面的点会插入到根节点中
        # self.points = []
        self.points = [0]

    def contains(self, point):
        return (
                self.x <= point.x <= self.x + self.width and
                self.y - self.height <= point.y <= self.y
            # self.y <= point.y <= self.y - self.height

        )

    def get_ordered_points(self):
        if self.children is None:
            return self.points

        ordered_points = []

        for child in self.children:
            ordered_points += child.get_ordered_points()

        return ordered_points


# 读取矢量文件四角范围作为四叉树范围
def quadtree_Grid(infile):
    """

    :param infile:
    :return: 返回网格左上角 x 坐标，网格左上角 y 坐标，网格宽度，网格高度
    """

    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(infile, 1)
    layer = dataSource.GetLayer(0)
    x_min = layer.GetExtent()[0]
    x_max = layer.GetExtent()[1]
    y_min = layer.GetExtent()[2]
    y_max = layer.GetExtent()[3]

    # 参数转换到浮点型
    x_min = float(x_min)
    x_max = float(x_max)
    y_min = float(y_min)
    y_max = float(y_max)

    width = abs(x_max - x_min)
    height = abs(y_max - y_min)

    return x_min, y_max, width, height


def point_List(infile):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(infile, 1)
    layer = dataSource.GetLayer(0)

    point_list = []
    for point in layer:
        point_id = point.GetField('Point_id')
        geom = point.GetGeometryRef()
        point_x = geom.GetX()
        point_y = geom.GetY()
        p = Point(point_x, point_y, point_id)
        point_list.append(p)

    return point_list


# 编码排序
def code_Sort(infile, point_list):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(infile, 1)
    layer = dataSource.GetLayer(0)

    fieldDefn = ogr.FieldDefn('unit_code', ogr.OFTString)
    fieldDefn.SetWidth(4)
    layer.CreateField(fieldDefn)

    for point in point_list:
        # point_id要和要素的FID对应
        feat = layer.GetFeature(point.point_id)
        feat.SetField('unit_code', 'YZ' + '-' + str(point_list.index(point)))
        layer.SetFeature(feat)
    feat = None


if __name__ == '__main__':
    os.chdir('I:/基于多约束的空间聚类/Delaunay三角网/地块TIN/图结构测试数据')
    point_shp = '顶点.shp'
    polygon = '分组地块.shp'

    x_min, y_max, width, height = quadtree_Grid(polygon)
    points = point_List(point_shp)

    quadtree = QuadTree(x_min, y_max, width, height)

    for point in points:
        quadtree.insert(point)

    ordered_points = quadtree.get_ordered_points()
    # for point in ordered_points:
    #     print(point.x, point.y, point.point_id)
    code_Sort(point_shp, ordered_points)
