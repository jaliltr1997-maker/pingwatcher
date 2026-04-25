import sys

from PyQt5.QtWidgets import QApplication

from .main_window import MainWindow
from .settings import SettingsStore


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(settings_store=SettingsStore())
    window.show()
    return app.exec_()
