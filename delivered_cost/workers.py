from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from PyQt5.QtWidgets import QMessageBox


class WorkerSignals(QObject):
    """Signals for the worker thread to communicate with the main thread."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)


class DeliveredCostWorker(QRunnable):
    """Worker thread for running the delivered cost calculations."""

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """Run the delivered cost calculations."""
        try:
            from .delvCost import run
        except ImportError as e:
            self.signals.error.emit(f"Import Error: {str(e)}")
            return

        try:

            def log_fn(msg):
                """
                Log messages to the main thread.
                Args:
                    msg (str): The message to log.
                """
                self.signals.log.emit(msg)

            class PBarWrapper:
                """Wrapper for a progress bar to emit progress signals."""

                def __init__(self, emit_func):
                    self._val = 0
                    self._max = 12
                    self._emit = emit_func

                def setValue(self, val):
                    """Set the current value of the progress bar and emit the signal."""
                    self._val = val
                    self._emit.emit(val)

                def value(self):
                    """Get the current value of the progress bar."""
                    return self._val

                def setmaximum(self, val):
                    """Set the maximum value of the progress bar."""
                    self._max = val

                def maximum(self):
                    """Get the maximum value of the progress bar."""
                    return self._max

            self.args["pbar"] = PBarWrapper(
                self.signals.progress
            )  # Wrap the progress bar to emit signals
            self.args["log"] = log_fn  # Use the log function to emit log messages

            result = run(**self.args)  # Run the delivered cost calculations
            self.signals.finished.emit(result)  # Emit the result when finished

        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            self.signals.error.emit(f"Error: {str(e)}\n{tb}")
