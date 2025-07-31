from qgis.gui import QgsMapTool
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.core import QgsPointXY


class PickPointTool(QgsMapTool):
    pointPicked = pyqtSignal(QgsPointXY)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(event.pos())
            self.pointPicked.emit(point)
            self.deactivate()

    def deactivate(self):
        super().deactivate()
        self.canvas.unsetMapTool(self)
