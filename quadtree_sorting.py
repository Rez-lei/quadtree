# ！/usr/bin/env python3
# --- coding:utf-8 ---
# File: quadtree_sorting.py
# Author: Zhanglei  Time: 2023/5/3 16:19

from osgeo import ogr, os, osr
from math import ceil
import geopandas as gpd


# 判断面内点的数量
def intersects(polygon_geom, point_shp):
    """

    :param polygon_geom: 输入面要素
    :param point_shp: 输入点图层
    :return: 返回面内点的数量
    """
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(point_shp, 1)
    points = dataSource.GetLayer(0)

    # 统计在面要素内部的点的数量
    count = 0
    for point in points:
        point_geom = point.GetGeometryRef()
        if polygon_geom.Intersect(point_geom):
            count += 1

    return count


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Rectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains(self, point):
        return (self.x <= point.x <= self.x + self.width and
                self.y <= point.y <= self.y + self.height)

    def intersects(self, other):
        return not (self.x + self.width < other.x or
                    self.y + self.height < other.y or
                    self.x > other.x + other.width or
                    self.y > other.y + other.height)


class QuadTree:
    def __init__(self, x, y, width, height, capacity):
        self.x = x  # 网格左上角 x 坐标
        self.y = y  # 网格左上角 y 坐标
        self.width = width  # 网格宽度
        self.height = height  # 网格高度
        self.capacity = capacity  # 网格容量，即最多可容纳的点数
        self.points = []  # 当前网格中包含的点
        self.sub_quads = None  # 分裂出的四个子网格

    def subdivide(self):
        """
        将当前网格分裂为四个子网格
        """
        half_width = self.width // 2
        half_height = self.height // 2
        self.sub_quads = [
            QuadTree(self.x, self.y, half_width, half_height, self.capacity),
            QuadTree(self.x + half_width, self.y, half_width, half_height, self.capacity),
            QuadTree(self.x, self.y + half_height, half_width, half_height, self.capacity),
            QuadTree(self.x + half_width, self.y + half_height, half_width, half_height, self.capacity)
        ]

    def insert(self, point):
        """
        插入一个点实体
        """
        if not (self.x <= point.x < self.x + self.width and self.y <= point.y < self.y + self.height):
            return False  # 点实体不在当前网格范围内，插入失败

        if len(self.points) < self.capacity and not self.sub_quads:
            # 当前网格还未达到容量上限，插入成功
            self.points.append(point)
            return True

        if not self.sub_quads:
            self.subdivide()

        # 将当前网格中的点实体插入到子网格中
        for quad in self.sub_quads:
            if quad.insert(point):
                return True

        return False  # 插入失败

    def query(self, x, y, width, height):
        """
        查询一个矩形区域内的所有点实体
        """
        result = []
        if self.x >= x + width or self.x + self.width <= x or self.y >= y + height or self.y + self.height <= y:
            return result  # 当前网格与查询区域没有重叠，返回空列表

        for point in self.points:
            if x <= point.x < x + width and y <= point.y < y + height:
                result.append(point)  # 点实体在查询区域内，加入结果列表

        if self.sub_quads:
            for quad in self.sub_quads:
                result.extend(quad.query(x, y, width, height))  # 递归查询子网格

        return result


# 读取矢量文件四角范围作为四叉树范围
def quadtree_Grid(infile, outfile):
    """

    :param infile:
    :param outfile:
    :return:
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

    # 创建输出文件
    outdriver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(outfile):
        outdriver.DeleteDataSource(outfile)
    outds = outdriver.CreateDataSource(outfile)
    outlayer = outds.CreateLayer(outfile, geom_type=ogr.wkbPolygon)

    # 设置空间参考
    SpatialReference = osr.SpatialReference()
    SpatialReference.ImportFromEPSG(4529)

    # 不添加属性信息，获取图层属性
    outfielddefn = outlayer.GetLayerDefn()

    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(x_min, y_max)
    ring.AddPoint(x_max, y_max)
    ring.AddPoint(x_max, y_min)
    ring.AddPoint(x_min, y_min)
    ring.CloseRings()
    # 写入几何多边形
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    # 创建要素，写入多边形
    outfeat = ogr.Feature(outfielddefn)
    outfeat.SetGeometry(poly)
    # 写入图层
    outlayer.CreateFeature(outfeat)
    outfeat = None

    # 写入投影文件
    SpatialReference.MorphFromESRI()
    prjfile = open(outfile.replace('.shp', '.prj'), 'w')
    prjfile.write(SpatialReference.ExportToWkt())
    prjfile.close()

    # 写入字符编码文件
    char_code = "UTF-8"
    cpgfile = open(outfile.replace('.shp', '.cpg'), 'w')
    cpgfile.write(char_code)
    cpgfile.close()

    # 写入后清除缓存
    outds = None


# 代码测试
if __name__ == '__main__':
    # os.chdir('I:/基于多约束的空间聚类/Delaunay三角网/地块TIN/图结构测试数据')
    # point = '顶点.shp'
    # polygon = '分组地块.shp'
    # out = '分组地块范围.shp'
    # quadtree_Grid(polygon, out)
    p1 = Point(4, 2)
    p2 = Point(1, 1)
    Q = QuadTree(0, 0, 6, 6, 1)
    Q.insert(p1)
    Q.insert(p2)

    results = Q.query(0, 0, 6, 6)
    for result in results:
        print(result.x, result.y)
