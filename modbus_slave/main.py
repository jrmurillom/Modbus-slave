"""Punto de entrada principal de la aplicación Modbus Slave Pro."""

from __future__ import annotations

import argparse
import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from modbus_slave.core.datastore import ThreadSafeDataStore
from modbus_slave.ui.main_window import MainWindow
from modbus_slave.ui.theme import DARK_THEME_QSS


def get_asset_path(filename: str) -> str:
    """Obtiene la ruta absoluta a un recurso estático (soporta modo compilado y desarrollo)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = getattr(sys, "_MEIPASS")
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "modbus_slave", "assets", filename)


def main() -> None:
    """Función de arranque principal."""
    # Configuración de AppUserModelID para que Windows muestre el icono en la barra de tareas
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "antigravity.modbusslavepro.app.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Modbus Slave Pro - Industrial Simulator")
    parser.add_argument("--host", default="0.0.0.0", help="Dirección IP de escucha (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=502, help="Puerto TCP Modbus (default: 502)")
    parser.add_argument("--slave-id", type=int, default=1, help="Slave/Unit ID inicial (default: 1)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Modbus Slave Pro")
    app.setOrganizationName("Antigravity")
    app.setStyleSheet(DARK_THEME_QSS)

    # Cargar y asignar icono oficial de la aplicación
    icon_ico = get_asset_path("icon.ico")
    icon_png = get_asset_path("icon.png")
    icon_target = icon_ico if os.path.exists(icon_ico) else icon_png
    if os.path.exists(icon_target):
        app_icon = QIcon(icon_target)
        app.setWindowIcon(app_icon)

    datastore = ThreadSafeDataStore(slave_id=args.slave_id, size=2000)
    window = MainWindow(datastore=datastore)
    window.server._host = args.host
    window.server._port = args.port

    if os.path.exists(icon_target):
        window.setWindowIcon(QIcon(icon_target))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
