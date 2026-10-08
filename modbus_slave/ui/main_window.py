"""Ventana principal de Modbus Slave Pro (PySide6).

Integra la barra de telemetría de peticiones Rx, tabla virtualizada de registros,
sniffer de tráfico hexadecimal en tiempo real, motor de simulación y gestión de proyectos.
"""

from __future__ import annotations

import os
from typing import Optional
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from modbus_slave.config.workspace import load_workspace_file, save_workspace_file
from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.formatters import DataFormat, Endianness, get_register_span
from modbus_slave.core.logger import PacketEntry, TrafficLogger
from modbus_slave.core.server import ModbusServerError, ModbusTcpServerEngine
from modbus_slave.core.simulation import SimulationEngine
from modbus_slave.ui.bridge import ServerQtBridge
from modbus_slave.ui.dialogs.connection_dialog import ConnectionDialog
from modbus_slave.ui.dialogs.register_setup_dialog import RegisterSetupDialog
from modbus_slave.ui.dialogs.shortcuts_dialog import KeyboardShortcutsDialog
from modbus_slave.ui.dialogs.simulation_dialog import SimulationDialog
from modbus_slave.ui.models.register_model import RegisterTableModel
from modbus_slave.ui.views.register_view import RegisterTableView
from modbus_slave.ui.views.traffic_dock import TrafficDockWidget


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(
        self,
        datastore: Optional[ThreadSafeDataStore] = None,
        logger: Optional[TrafficLogger] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modbus Slave Pro - Industrial Simulator")
        self.resize(1100, 750)

        # Capa de dominio (Core)
        self.datastore = datastore or ThreadSafeDataStore(slave_id=1, size=2000)
        self.logger = logger or TrafficLogger()
        self.server = ModbusTcpServerEngine(self.datastore, self.logger)
        self.simulation_engine = SimulationEngine(self.datastore)

        # Puente de sincronización segura con Qt
        self.bridge = ServerQtBridge(self)
        self.datastore.subscribe(self.bridge.on_register_change)
        self.logger.add_listener(self.bridge.on_packet_logged)
        self.server.add_status_listener(self.bridge.on_server_status_changed)

        # Parámetros activos de vista (Base 0 e Int16 por defecto como en Modbus Slave)
        self.current_block = ModbusBlockType.HOLDING_REGISTERS.value
        self.start_address = 0
        self.display_count = 100
        self.format_type = DataFormat.INT16
        self.endianness = Endianness.CDAB
        self.use_plc_addresses = False
        self.current_project_path: Optional[str] = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Construye todos los elementos gráficos de la interfaz."""
        # Widget central contenedor
        central_container = QWidget()
        central_layout = QVBoxLayout(central_container)
        central_layout.setContentsMargins(6, 6, 6, 6)
        central_layout.setSpacing(6)

        # 1. Cabecera de Telemetría Dinámica (Idéntica a Modbus Slave)
        self.telemetry_widget = QWidget()
        self.telemetry_widget.setStyleSheet("""
            QWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
            }
        """)
        telem_layout = QHBoxLayout(self.telemetry_widget)
        telem_layout.setContentsMargins(10, 6, 10, 6)

        # Indicador Rx = 0: ID = 1: F = 03
        self.lbl_telemetry_header = QLabel("Rx = 0 : ID = 1 : F = 03")
        font_telem = QFont("Consolas", 13)
        font_telem.setBold(True)
        self.lbl_telemetry_header.setFont(font_telem)
        self.lbl_telemetry_header.setStyleSheet("color: #89dceb; border: none;")
        telem_layout.addWidget(self.lbl_telemetry_header)

        # Botón para resetear contador Rx
        self.btn_reset_rx = QPushButton("Reset Rx")
        self.btn_reset_rx.setToolTip("Reiniciar contador de peticiones Rx a 0")
        self.btn_reset_rx.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_reset_rx.clicked.connect(self._reset_rx_counter)
        telem_layout.addWidget(self.btn_reset_rx)

        # Botón para resetear valores de registros a cero
        self.btn_reset_values = QPushButton("Reset Values")
        self.btn_reset_values.setToolTip("Restablecer a cero los registros de datos (Ctrl+Shift+R)")
        self.btn_reset_values.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_reset_values.clicked.connect(lambda: self._confirm_and_reset_values(all_blocks=False))
        telem_layout.addWidget(self.btn_reset_values)

        telem_layout.addStretch()

        # Indicador de enlace
        self.lbl_connection_state = QLabel("● No connection")
        font_conn = QFont("Segoe UI", 11)
        font_conn.setBold(True)
        self.lbl_connection_state.setFont(font_conn)
        self.lbl_connection_state.setStyleSheet("color: #f38ba8; border: none;")
        telem_layout.addWidget(self.lbl_connection_state)

        central_layout.addWidget(self.telemetry_widget)

        # 2. Tabla Central de Registros
        self.table_model = RegisterTableModel(
            datastore=self.datastore,
            parent=self,
            block=self.current_block,
            start_address=self.start_address,
            display_count=self.display_count,
            format_type=self.format_type,
            endianness=self.endianness,
            use_plc_addresses=self.use_plc_addresses,
        )
        self.table_view = RegisterTableView(self)
        self.table_view.setModel(self.table_model)
        central_layout.addWidget(self.table_view)

        self.setCentralWidget(central_container)

        # 3. Dock Inferior: Sniffer de Tráfico
        self.traffic_dock = TrafficDockWidget(self.logger, self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.traffic_dock)

        # 4. Barras de Menú y Herramientas
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()

    def _create_menus(self) -> None:
        menubar = self.menuBar()

        # Menú Archivo
        file_menu = menubar.addMenu("&Archivo")
        act_new = QAction("&Nuevo Proyecto", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._new_project)
        file_menu.addAction(act_new)

        act_open = QAction("&Abrir Proyecto...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._open_project)
        file_menu.addAction(act_open)

        act_save = QAction("&Guardar Proyecto", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._save_project)
        file_menu.addAction(act_save)

        act_save_as = QAction("Guardar &Como...", self)
        act_save_as.triggered.connect(self._save_project_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()
        act_exit = QAction("&Salir", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Menú Edición
        edit_menu = menubar.addMenu("&Edición")
        act_goto = QAction("&Ir a Dirección...", self)
        act_goto.setShortcut(QKeySequence("Ctrl+G"))
        act_goto.setToolTip("Saltar rápidamente a una dirección de registro (Ctrl+G)")
        act_goto.triggered.connect(self._go_to_address)
        edit_menu.addAction(act_goto)

        edit_menu.addSeparator()
        act_reset_current = QAction("Restablecer &Bloque Actual a Cero...", self)
        act_reset_current.setShortcut(QKeySequence("Ctrl+Shift+R"))
        act_reset_current.setToolTip("Restablece a cero los registros del bloque actual on-the-fly (Ctrl+Shift+R)")
        act_reset_current.triggered.connect(lambda: self._confirm_and_reset_values(all_blocks=False))
        edit_menu.addAction(act_reset_current)

        act_reset_all = QAction("Restablecer &Todos los Bloques a Cero...", self)
        act_reset_all.setToolTip("Restablece a cero todos los registros de los 4 bloques Modbus on-the-fly")
        act_reset_all.triggered.connect(lambda: self._confirm_and_reset_values(all_blocks=True))
        edit_menu.addAction(act_reset_all)

        # Menú Conexión
        conn_menu = menubar.addMenu("&Conexión")
        self.act_start_srv = QAction("▶ &Iniciar Servidor", self)
        self.act_start_srv.setShortcut("F5")
        self.act_start_srv.triggered.connect(self._start_server)
        conn_menu.addAction(self.act_start_srv)

        self.act_stop_srv = QAction("⏹ &Detener Servidor", self)
        self.act_stop_srv.setShortcut("F6")
        self.act_stop_srv.setEnabled(False)
        self.act_stop_srv.triggered.connect(self._stop_server)
        conn_menu.addAction(self.act_stop_srv)

        conn_menu.addSeparator()
        act_conn_setup = QAction("&Configurar Red / IP...", self)
        act_conn_setup.triggered.connect(self._configure_connection)
        conn_menu.addAction(act_conn_setup)

        # Menú Setup
        setup_menu = menubar.addMenu("&Setup")
        act_slave_def = QAction("&Definición de Esclavo (Slave Definition)...", self)
        act_slave_def.setShortcut("F8")
        act_slave_def.triggered.connect(self._configure_slave_definition)
        setup_menu.addAction(act_slave_def)

        # Menú Display
        disp_menu = menubar.addMenu("&Display (Formato)")
        formats = [
            ("Unsigned 16-bit (UInt16)", DataFormat.UINT16, Endianness.CDAB),
            ("Signed 16-bit (Int16)", DataFormat.INT16, Endianness.CDAB),
            ("Hexadecimal (0x0000)", DataFormat.HEX, Endianness.CDAB),
            ("Binario (16-bit)", DataFormat.BIN, Endianness.CDAB),
            ("Float 32 (CDAB - Modicon)", DataFormat.FLOAT32, Endianness.CDAB),
            ("Float 32 (ABCD - Big-Endian)", DataFormat.FLOAT32, Endianness.ABCD),
            ("Signed 32-bit (Int32)", DataFormat.INT32, Endianness.CDAB),
        ]
        for name, fmt, end in formats:
            act = QAction(name, self)
            act.triggered.connect(lambda checked=False, f=fmt, e=end: self._change_format(f, e))
            disp_menu.addAction(act)

        disp_menu.addSeparator()
        self.act_plc_addresses = QAction("Direcciones PLC (Base 1 / 40001)", self)
        self.act_plc_addresses.setCheckable(True)
        self.act_plc_addresses.setChecked(False)
        self.act_plc_addresses.toggled.connect(self._toggle_plc_addresses)
        disp_menu.addAction(self.act_plc_addresses)

        # Menú Simulación
        sim_menu = menubar.addMenu("&Simulación")
        act_sim_edit = QAction("&Configurar Simulación de Registro...", self)
        act_sim_edit.triggered.connect(self._configure_simulation_for_selected)
        sim_menu.addAction(act_sim_edit)

        self.act_toggle_sim = QAction("▶ Iniciar Motor de Simulación", self)
        self.act_toggle_sim.triggered.connect(self._toggle_simulation_engine)
        sim_menu.addAction(self.act_toggle_sim)

        # Menú Ayuda
        help_menu = menubar.addMenu("&Ayuda")
        act_shortcuts = QAction("&Atajos de Teclado...", self)
        act_shortcuts.setShortcut("F1")
        act_shortcuts.setToolTip("Ver lista de atajos de teclado y comandos rápidos (F1)")
        act_shortcuts.triggered.connect(self._show_shortcuts_dialog)
        help_menu.addAction(act_shortcuts)

        help_menu.addSeparator()
        act_about = QAction("&Acerca de Modbus Slave Pro...", self)
        act_about.triggered.connect(self._show_about_dialog)
        help_menu.addAction(act_about)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Barra Principal")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        self.btn_tb_server = QPushButton("▶ Iniciar Servidor (F5)")
        self.btn_tb_server.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        self.btn_tb_server.clicked.connect(self._toggle_server)
        toolbar.addWidget(self.btn_tb_server)

        toolbar.addSeparator()

        btn_conn = QPushButton("Configurar Red")
        btn_conn.clicked.connect(self._configure_connection)
        toolbar.addWidget(btn_conn)

        btn_f8 = QPushButton("Slave Definition (F8)")
        btn_f8.clicked.connect(self._configure_slave_definition)
        toolbar.addWidget(btn_f8)

        btn_goto = QPushButton("Ir a Dir (Ctrl+G)")
        btn_goto.setToolTip("Saltar rápidamente a una dirección de registro (Ctrl+G)")
        btn_goto.clicked.connect(self._go_to_address)
        toolbar.addWidget(btn_goto)

        btn_shortcuts = QPushButton("⌨ Atajos (F1)")
        btn_shortcuts.setToolTip("Consultar atajos de teclado y comandos rápidos (F1)")
        btn_shortcuts.clicked.connect(self._show_shortcuts_dialog)
        toolbar.addWidget(btn_shortcuts)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Formato: "))
        self.cmb_toolbar_format = QComboBox()
        self.cmb_toolbar_format.addItem("UInt16", (DataFormat.UINT16, Endianness.CDAB))
        self.cmb_toolbar_format.addItem("Int16 (Signed)", (DataFormat.INT16, Endianness.CDAB))
        self.cmb_toolbar_format.addItem("Hex", (DataFormat.HEX, Endianness.CDAB))
        self.cmb_toolbar_format.addItem("Bin", (DataFormat.BIN, Endianness.CDAB))
        self.cmb_toolbar_format.addItem("Float 32 (CDAB)", (DataFormat.FLOAT32, Endianness.CDAB))
        self.cmb_toolbar_format.addItem("Float 32 (ABCD)", (DataFormat.FLOAT32, Endianness.ABCD))
        self.cmb_toolbar_format.addItem("Int32 (CDAB)", (DataFormat.INT32, Endianness.CDAB))
        # Seleccionar Int16 por defecto (índice 1)
        self.cmb_toolbar_format.setCurrentIndex(1)
        self.cmb_toolbar_format.currentIndexChanged.connect(self._on_toolbar_format_changed)
        toolbar.addWidget(self.cmb_toolbar_format)

        toolbar.addSeparator()

        btn_sim = QPushButton("⚡ Simular Registro")
        btn_sim.clicked.connect(self._configure_simulation_for_selected)
        toolbar.addWidget(btn_sim)

    def _create_statusbar(self) -> None:
        sb = self.statusBar()
        self.lbl_sb_srv = QLabel("Servidor: DETENIDO")
        self.lbl_sb_srv.setStyleSheet("color: #f38ba8; font-weight: bold;")
        sb.addWidget(self.lbl_sb_srv)

        self.lbl_sb_endpoint = QLabel("Endpoint: 0.0.0.0:502")
        sb.addWidget(self.lbl_sb_endpoint)

        self.lbl_sb_clients = QLabel("Clientes Activos: 0")
        sb.addWidget(self.lbl_sb_clients)

        sb.addPermanentWidget(QLabel("Modbus TCP | Sin Límite de Tiempo (24/7)"))

    def _connect_signals(self) -> None:
        """Conecta las señales del bridge Qt."""
        self.bridge.register_changed.connect(self.table_model.handle_external_change)
        self.bridge.packet_logged.connect(self._on_packet_logged)
        self.bridge.server_status_changed.connect(self._on_server_status_changed)

    def _update_telemetry_header(self) -> None:
        fc_code = "03"
        if self.current_block == ModbusBlockType.COILS.value:
            fc_code = "01"
        elif self.current_block == ModbusBlockType.DISCRETE_INPUTS.value:
            fc_code = "02"
        elif self.current_block == ModbusBlockType.INPUT_REGISTERS.value:
            fc_code = "04"

        self.lbl_telemetry_header.setText(
            f"Rx = {self.logger.rx_count} : ID = {self.datastore.slave_id} : F = {fc_code}"
        )

        clients = self.logger.connected_clients
        clients_list = self.logger.get_connected_clients()
        if clients_list:
            client_tip = "Clientes Modbus TCP conectados:\n" + "\n".join(f"• {c}" for c in clients_list)
        else:
            client_tip = "Sin clientes conectados"

        if self.server.is_running:
            if clients > 0:
                self.lbl_connection_state.setText(f"● Connected ({clients} Master{'s' if clients > 1 else ''})")
                self.lbl_connection_state.setStyleSheet("color: #a6e3a1; border: none;")
            else:
                self.lbl_connection_state.setText("● Listening (Waiting master)")
                self.lbl_connection_state.setStyleSheet("color: #f9e2af; border: none;")
        else:
            self.lbl_connection_state.setText("● No connection")
            self.lbl_connection_state.setStyleSheet("color: #f38ba8; border: none;")

        self.lbl_connection_state.setToolTip(client_tip)
        self.lbl_sb_clients.setText(f"Clientes Activos: {clients}")
        self.lbl_sb_clients.setToolTip(client_tip)

    def _go_to_address(self) -> None:
        """Permite al operador saltar inmediatamente a cualquier dirección de registro (Ctrl+G)."""
        span = get_register_span(self.format_type)
        curr = self.table_view.currentIndex()
        default_val = self.table_model._get_row_address(curr.row()) if curr.isValid() else self.start_address
        max_addr = max(0, self.datastore.size - span)

        target_addr, ok = QInputDialog.getInt(
            self,
            "Ir a Dirección",
            f"Ingrese dirección de registro (0 - {max_addr}):",
            default_val,
            0,
            max_addr,
            1,
        )
        if not ok:
            return

        # Si la dirección cae fuera del rango visualizado actual, ajustar start_address para centrarla
        if target_addr < self.start_address or target_addr >= (self.start_address + self.display_count):
            self.start_address = max(0, min(target_addr - (self.display_count // 4), max_addr))
            self.table_model.set_view_parameters(start_address=self.start_address)
            self._update_telemetry_header()

        # Calcular fila correspondiente en el modelo
        row = (target_addr - self.start_address) // span
        if 0 <= row < self.table_model.rowCount():
            model_idx = self.table_model.index(row, 2)  # Columna de valor
            self.table_view.scrollTo(model_idx)
            self.table_view.setCurrentIndex(model_idx)
            self.table_view.setFocus()

    def _reset_rx_counter(self) -> None:
        self.logger.reset_counters()
        self._update_telemetry_header()
        self.traffic_dock.update_stats()

    def _confirm_and_reset_values(self, all_blocks: bool = False) -> None:
        """Restablece los registros a cero on-the-fly con salvaguarda condicional inteligente."""
        block_names = {
            ModbusBlockType.COILS.value: "Coils (0x)",
            ModbusBlockType.DISCRETE_INPUTS.value: "Discrete Inputs (1x)",
            ModbusBlockType.INPUT_REGISTERS.value: "Input Registers (3x)",
            ModbusBlockType.HOLDING_REGISTERS.value: "Holding Registers (4x)",
        }
        block_label = (
            "TODOS los bloques (0x, 1x, 3x, 4x)"
            if all_blocks
            else block_names.get(self.current_block, self.current_block)
        )
        target_block = None if all_blocks else self.current_block

        clients_count = self.logger.connected_clients
        if clients_count > 0:
            # Salvaguarda 1: Advertencia severa en caliente si hay maestros Modbus conectados
            msg = (
                f"⚠️ ATENCIÓN: Hay {clients_count} cliente(s) Modbus TCP conectado(s) en este momento.\n\n"
                f"Restablecer a cero {block_label} en caliente alterará las lecturas del maestro en tiempo real.\n\n"
                f"¿Desea forzar el restablecimiento a cero de inmediato?"
            )
            res = QMessageBox.warning(
                self,
                "Confirmar Restablecimiento en Caliente (On-The-Fly)",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
        else:
            # Salvaguarda 2: Confirmación estándar para prevenir clics accidentales
            msg = f"¿Está seguro de que desea restablecer a cero {block_label}?"
            res = QMessageBox.question(
                self,
                "Restablecer Valores a Cero",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

        if res != QMessageBox.StandardButton.Yes:
            return

        # Ejecutar reseteo atómico thread-safe
        self.datastore.reset_values(block=target_block, source="local")

        # Salvaguarda 3: Trazabilidad en el Sniffer de Tráfico
        audit_desc = f"Operador ejecutó Reset Values en caliente: {block_label}"
        self.logger.log_system_event(audit_desc)

        self.statusBar().showMessage(f"✓ Registros restablecidos a cero ({block_label})", 4000)

    def _on_packet_logged(self, entry: PacketEntry) -> None:
        self.traffic_dock.add_packet(entry)
        self._update_telemetry_header()

    def _on_server_status_changed(self, is_running: bool, host: str, port: int) -> None:
        if is_running:
            self.btn_tb_server.setText("⏹ Detener Servidor (F6)")
            self.btn_tb_server.setStyleSheet("background-color: #c62828; color: white; font-weight: bold;")
            self.act_start_srv.setEnabled(False)
            self.act_stop_srv.setEnabled(True)
            self.lbl_sb_srv.setText("Servidor: RUNNING")
            self.lbl_sb_srv.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self.lbl_sb_endpoint.setText(f"Endpoint: {host}:{port}")
        else:
            self.btn_tb_server.setText("▶ Iniciar Servidor (F5)")
            self.btn_tb_server.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
            self.act_start_srv.setEnabled(True)
            self.act_stop_srv.setEnabled(False)
            self.lbl_sb_srv.setText("Servidor: DETENIDO")
            self.lbl_sb_srv.setStyleSheet("color: #f38ba8; font-weight: bold;")

        self._update_telemetry_header()

    def _toggle_server(self) -> None:
        if self.server.is_running:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self) -> None:
        try:
            self.server.start(host=self.server.host, port=self.server.port)
        except ModbusServerError as e:
            err_str = str(e)
            is_collision_or_perm = any(
                keyword in err_str.lower()
                for keyword in ["10048", "already in use", "permission", "privilegios", "access denied", "tiempo de espera"]
            )
            if self.server.port == 502 and is_collision_or_perm:
                res = QMessageBox.question(
                    self,
                    "Conflicto en Puerto 502 (Modbus TCP)",
                    f"El puerto 502 no pudo abrirse (en uso o requiere privilegios de administrador en Windows):\n\n"
                    f"{err_str}\n\n"
                    f"¿Desea cambiar automáticamente al puerto alternativo estándar 5020 e iniciar el servidor?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if res == QMessageBox.StandardButton.Yes:
                    self.server._port = 5020
                    self.lbl_sb_endpoint.setText(f"Endpoint: {self.server.host}:5020")
                    try:
                        self.server.start(host=self.server.host, port=5020)
                        return
                    except ModbusServerError as e2:
                        QMessageBox.critical(
                            self,
                            "Error al Iniciar Servidor en 5020",
                            f"Fallo al abrir puerto 5020:\n{e2}"
                        )
                        return

            QMessageBox.critical(
                self,
                "Error al Iniciar Servidor",
                f"No se pudo enlazar el servidor:\n{e}\n\nNota: Si el puerto 502 requiere privilegios de administrador, configure el puerto 5020 desde Conexión."
            )

    def _stop_server(self) -> None:
        self.server.stop()

    def _configure_connection(self) -> None:
        dlg = ConnectionDialog(host=self.server.host, port=self.server.port, slave_id=self.datastore.slave_id, parent=self)
        if dlg.exec():
            host, port, sid = dlg.get_values()
            was_running = self.server.is_running
            if was_running:
                self.server.stop()

            self.datastore.slave_id = sid
            self._update_telemetry_header()

            if was_running:
                self.server.start(host=host, port=port)
            else:
                self.server._host = host
                self.server._port = port
                self.lbl_sb_endpoint.setText(f"Endpoint: {host}:{port}")

    def _configure_slave_definition(self) -> None:
        dlg = RegisterSetupDialog(
            slave_id=self.datastore.slave_id,
            current_block=self.current_block,
            start_address=self.start_address,
            length=self.display_count,
            parent=self,
        )
        if dlg.exec():
            sid, block, addr, length = dlg.get_values()
            self.datastore.slave_id = sid
            self.current_block = block
            self.start_address = addr
            self.display_count = length

            self.table_model.set_view_parameters(
                block=self.current_block,
                start_address=self.start_address,
                display_count=self.display_count,
            )
            self._update_telemetry_header()

    def _change_format(self, fmt: DataFormat, end: Endianness) -> None:
        self.format_type = fmt
        self.endianness = end
        self.table_model.set_view_parameters(format_type=fmt, endianness=end)

        # Sincronizar combo de toolbar
        for i in range(self.cmb_toolbar_format.count()):
            f, e = self.cmb_toolbar_format.itemData(i)
            if f == fmt and e == end:
                self.cmb_toolbar_format.blockSignals(True)
                self.cmb_toolbar_format.setCurrentIndex(i)
                self.cmb_toolbar_format.blockSignals(False)
                break

    def _on_toolbar_format_changed(self, idx: int) -> None:
        fmt, end = self.cmb_toolbar_format.itemData(idx)
        self._change_format(fmt, end)

    def _toggle_plc_addresses(self, checked: bool) -> None:
        self.use_plc_addresses = checked
        self.table_model.set_view_parameters(use_plc_addresses=checked)

    def _configure_simulation_for_selected(self) -> None:
        curr = self.table_view.currentIndex()
        row = curr.row() if curr.isValid() else 0
        addr = self.table_model._get_row_address(row)

        existing_rule = None
        for r in self.simulation_engine.get_rules():
            if r.block == self.current_block and r.address == addr:
                existing_rule = r
                break

        dlg = SimulationDialog(
            block=self.current_block,
            address=addr,
            format_type=self.format_type,
            endianness=self.endianness,
            existing_rule=existing_rule,
            parent=self,
        )
        if dlg.exec():
            rule = dlg.get_rule()
            if rule:
                self.simulation_engine.add_rule(rule)
                self.datastore.get_metadata(self.current_block, addr).simulation_config = {
                    "waveform": rule.waveform.value
                }
            else:
                self.simulation_engine.remove_rule(self.current_block, addr)
                self.datastore.get_metadata(self.current_block, addr).simulation_config = None

            if not self.simulation_engine.is_running and len(self.simulation_engine.get_rules()) > 0:
                self.simulation_engine.start()
                self.act_toggle_sim.setText("⏹ Detener Motor de Simulación")

            self.table_model.dataChanged.emit(
                self.table_model.index(row, 0),
                self.table_model.index(row, self.table_model.columnCount() - 1),
                [Qt.ItemDataRole.DisplayRole]
            )

    def _toggle_simulation_engine(self) -> None:
        if self.simulation_engine.is_running:
            self.simulation_engine.stop()
            self.act_toggle_sim.setText("▶ Iniciar Motor de Simulación")
        else:
            self.simulation_engine.start()
            self.act_toggle_sim.setText("⏹ Detener Motor de Simulación")

    def _new_project(self) -> None:
        res = QMessageBox.question(self, "Nuevo Proyecto", "¿Desea limpiar todos los registros y comenzar un proyecto nuevo?")
        if res == QMessageBox.StandardButton.Yes:
            self.simulation_engine.stop()
            self.simulation_engine.clear_rules()
            self.server.stop()
            self.datastore = ThreadSafeDataStore(slave_id=1, size=2000)
            self.table_model.datastore = self.datastore
            self.table_model.set_view_parameters(start_address=0, display_count=100)
            self.current_project_path = None
            self._update_telemetry_header()

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir Proyecto Modbus", "", "Modbus Project (*.json)")
        if not path:
            return

        try:
            data = load_workspace_file(path)
            self.datastore.slave_id = data.get("slave_id", 1)
            self.server._host = data.get("host", "0.0.0.0")
            self.server._port = data.get("port", 502)
            self.current_block = data.get("block", ModbusBlockType.HOLDING_REGISTERS.value)
            self.start_address = data.get("start_address", 0)
            self.display_count = data.get("length", 100)
            self.format_type = DataFormat(data.get("format_type", DataFormat.INT16.value))
            self.endianness = Endianness(data.get("endianness", Endianness.CDAB.value))
            self.use_plc_addresses = data.get("use_plc_addresses", False)
            self.act_plc_addresses.setChecked(self.use_plc_addresses)

            # Cargar registros guardados
            regs_data = data.get("registers", {})
            for str_addr, val_dict in regs_data.items():
                addr = int(str_addr)
                if "alias" in val_dict:
                    self.datastore.set_alias(self.current_block, addr, val_dict["alias"])
                if "val" in val_dict:
                    if self.current_block == ModbusBlockType.HOLDING_REGISTERS.value:
                        self.datastore.set_holding_register(addr, val_dict["val"])
                    elif self.current_block == ModbusBlockType.COILS.value:
                        self.datastore.set_coil(addr, bool(val_dict["val"]))

            self.table_model.set_view_parameters(
                block=self.current_block,
                start_address=self.start_address,
                display_count=self.display_count,
                format_type=self.format_type,
                endianness=self.endianness,
                use_plc_addresses=self.use_plc_addresses,
            )
            self.current_project_path = path
            self._update_telemetry_header()
            QMessageBox.information(self, "Proyecto Cargado", f"Proyecto cargado con éxito:\n{os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudo cargar el archivo:\n{e}")

    def _save_project(self) -> None:
        if self.current_project_path:
            self._do_save(self.current_project_path)
        else:
            self._save_project_as()

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Proyecto Modbus", "modbus_project.json", "Modbus Project (*.json)")
        if path:
            self.current_project_path = path
            self._do_save(path)

    def _do_save(self, path: str) -> None:
        registers_dict = {}
        for addr in range(self.start_address, self.start_address + self.display_count):
            alias = self.datastore.get_alias(self.current_block, addr)
            val = (
                self.datastore.get_holding_register(addr)
                if self.current_block == ModbusBlockType.HOLDING_REGISTERS.value
                else self.datastore.get_coil(addr)
            )
            if alias or val != 0:
                registers_dict[str(addr)] = {"alias": alias, "val": val}

        workspace_data = {
            "version": "1.0",
            "slave_id": self.datastore.slave_id,
            "host": self.server.host,
            "port": self.server.port,
            "block": self.current_block,
            "start_address": self.start_address,
            "length": self.display_count,
            "format_type": self.format_type.value,
            "endianness": self.endianness.value,
            "use_plc_addresses": self.use_plc_addresses,
            "registers": registers_dict,
        }
        try:
            save_workspace_file(path, workspace_data)
            QMessageBox.information(self, "Guardado", f"Proyecto guardado con éxito en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

    def _show_shortcuts_dialog(self) -> None:
        """Abre la ventana de referencia de atajos de teclado y comandos rápidos (F1)."""
        dlg = KeyboardShortcutsDialog(self)
        dlg.exec()

    def _show_about_dialog(self) -> None:
        """Muestra información básica de la aplicación y versión."""
        QMessageBox.about(
            self,
            "Acerca de Modbus Slave Pro",
            "<h3>Modbus Slave Pro v1.0.0</h3>"
            "<p>Simulador y servidor Modbus TCP con soporte multiformato, "
            "inspección de tráfico y simulación de señales.</p>"
            "<p><b>Stack:</b> Python 3.11 + PySide6 (Qt6)</p>",
        )

    def closeEvent(self, event: Any) -> None:
        """Cierre seguro de servidores y simulación al salir."""
        self.simulation_engine.stop()
        self.server.stop()
        event.accept()
