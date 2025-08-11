from qgis.gui import QgsMapTool
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.core import QgsPointXY


class PickPointTool(QgsMapTool):
    """A tool to pick a point on the map canvas and emit the coordinates."""

    pointPicked = pyqtSignal(QgsPointXY)  # Signal emitted when a point is picked.

    def __init__(self, canvas):
        """Initialize the tool with the given canvas.
        Args:
            canvas (QgsMapCanvas): The map canvas where the tool will operate.
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        """Handle the mouse release event to pick a point.
        Args:
            event (QgsMapMouseEvent): The mouse event containing the position.
        """
        if event.button() == Qt.LeftButton:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(event.pos())
            self.pointPicked.emit(point)
            self.deactivate()

    def deactivate(self):
        """Deactivate the tool and reset the cursor."""
        super().deactivate()
        self.canvas.unsetMapTool(self)
