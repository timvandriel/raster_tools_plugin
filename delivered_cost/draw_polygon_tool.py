# yourplugin/draw_polygon_tool.py
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsPointXY, QgsGeometry, QgsWkbTypes
from qgis.PyQt.QtCore import pyqtSignal, Qt


class DrawPolygonTool(QgsMapTool):
    polygonCompleted = pyqtSignal(QgsGeometry)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setWidth(2)
        self.points = []
        self.setCursor(Qt.CrossCursor)

    def canvasPressEvent(self, event):
        point = self.canvas.getCoordinateTransform().toMapCoordinates(event.pos())
        self.points.append(point)
        self.rubberBand.addPoint(point, True)

    def canvasMoveEvent(self, event):
        if not self.points:
            return
        point = self.canvas.getCoordinateTransform().toMapCoordinates(event.pos())
        if self.rubberBand.numberOfVertices() > len(self.points):
            self.rubberBand.removePoint(-1)
        self.rubberBand.addPoint(point, True)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.RightButton and len(self.points) >= 3:
            self.rubberBand.closePoints()
            geom = QgsGeometry.fromPolygonXY([self.points])
            self.polygonCompleted.emit(geom)
            self.reset()

    def reset(self):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.points = []

    def deactivate(self):
        self.reset()
        super().deactivate()
