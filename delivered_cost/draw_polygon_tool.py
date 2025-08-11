# yourplugin/draw_polygon_tool.py
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsPointXY, QgsGeometry, QgsWkbTypes
from qgis.PyQt.QtCore import pyqtSignal, Qt


class DrawPolygonTool(QgsMapTool):
    """A tool to draw a polygon on the map canvas and emit the polygon geometry when completed."""

    polygonCompleted = pyqtSignal(QgsGeometry)

    def __init__(self, canvas):
        """Initialize the tool with the given canvas.
        Args:
            canvas (QgsMapCanvas): The map canvas where the tool will operate.
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setWidth(2)
        self.points = []
        self.setCursor(Qt.CrossCursor)

    def canvasPressEvent(self, event):
        """Handle the mouse press event to start drawing a polygon.
        Args:
            event (QgsMapMouseEvent): The mouse event containing the position.
        """
        point = self.canvas.getCoordinateTransform().toMapCoordinates(event.pos())
        self.points.append(point)
        self.rubberBand.addPoint(point, True)

    def canvasMoveEvent(self, event):
        """Handle the mouse move event to update the polygon being drawn.
        Args:
            event (QgsMapMouseEvent): The mouse event containing the position.
        """
        if not self.points:
            return
        point = self.canvas.getCoordinateTransform().toMapCoordinates(event.pos())
        if self.rubberBand.numberOfVertices() > len(self.points):
            self.rubberBand.removePoint(-1)
        self.rubberBand.addPoint(point, True)

    def canvasReleaseEvent(self, event):
        """Handle the mouse release event to finalize the polygon.
        Args:
            event (QgsMapMouseEvent): The mouse event containing the position.
        """
        if event.button() == Qt.RightButton and len(self.points) >= 3:
            self.rubberBand.closePoints()
            geom = QgsGeometry.fromPolygonXY([self.points])
            self.polygonCompleted.emit(geom)
            self.reset()

    def reset(self):
        """Reset the tool to its initial state."""
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.points = []

    def deactivate(self):
        """Deactivate the tool and reset the cursor."""
        self.reset()
        super().deactivate()
