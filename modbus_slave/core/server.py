"""Motor del Servidor Modbus TCP.

Encapsula el ciclo de vida del servidor (arranque, parada, hilos asíncronos)
desacoplado de la interfaz gráfica, permitiendo ejecución en segundo plano
con control de concurrencia y tolerancia a fallos.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Callable, List, Optional, Tuple

from pymodbus.server import ModbusTcpServer, ServerAsyncStop, StartAsyncTcpServer
from pymodbus.server.base import ModbusBaseServer
from pymodbus.simulator import DataType, SimData, SimDevice

from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.logger import TrafficLogger


class ModbusServerError(Exception):
    """Excepción base para errores de inicialización o ejecución del servidor."""
    pass


class TrackedModbusTcpServer(ModbusTcpServer):
    """Servidor TCP Modbus con inspección de direcciones IP y puertos de clientes conectados."""

    def __init__(
        self,
        *args,
        on_client_connect: Optional[Callable[[Tuple[str, int]], None]] = None,
        on_client_disconnect: Optional[Callable[[Tuple[str, int]], None]] = None,
        **kwargs,
    ) -> None:
        self.on_client_connect = on_client_connect
        self.on_client_disconnect = on_client_disconnect
        super().__init__(*args, **kwargs)

    def callback_new_connection(self):
        handler = super().callback_new_connection()
        orig_connection_made = handler.connection_made
        orig_connection_lost = handler.connection_lost

        def custom_connection_made(transport):
            peer = transport.get_extra_info("peername")
            if self.on_client_connect and peer:
                self.on_client_connect(peer)
            orig_connection_made(transport)

        def custom_connection_lost(exc):
            peer = handler.transport.get_extra_info("peername") if handler.transport else None
            if self.on_client_disconnect and peer:
                self.on_client_disconnect(peer)
            orig_connection_lost(exc)

        handler.connection_made = custom_connection_made
        handler.connection_lost = custom_connection_lost
        return handler


class ModbusTcpServerEngine:
    """Administrador del servidor Modbus TCP con soporte de hilos y sniffer integrado."""

    def __init__(self, datastore: ThreadSafeDataStore, logger: Optional[TrafficLogger] = None) -> None:
        self.datastore = datastore
        self.logger = logger or TrafficLogger()

        self._host: str = "0.0.0.0"
        self._port: int = 502
        self._is_running: bool = False
        self._lock = threading.RLock()

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._server_ready_event = threading.Event()
        self._startup_error: Optional[Exception] = None

        # Listeners para eventos del servidor
        self._status_listeners: List[Callable[[bool, str, int], None]] = []

    @property
    def is_running(self) -> bool:
        """Indica si el servidor está escuchando conexiones activamente."""
        with self._lock:
            return self._is_running

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def add_status_listener(self, callback: Callable[[bool, str, int], None]) -> None:
        """Registra un observador para cambios en el estado del servidor (running, host, port)."""
        with self._lock:
            if callback not in self._status_listeners:
                self._status_listeners.append(callback)

    def remove_status_listener(self, callback: Callable[[bool, str, int], None]) -> None:
        with self._lock:
            if callback in self._status_listeners:
                self._status_listeners.remove(callback)

    def _notify_status(self) -> None:
        running = self._is_running
        host = self._host
        port = self._port
        for listener in list(self._status_listeners):
            try:
                listener(running, host, port)
            except Exception:
                pass

    def _trace_packet_hook(self, is_tx: bool, raw_data: bytes) -> bytes:
        """Intercepta cada paquete de red de entrada y salida."""
        self.logger.log_packet(is_tx=is_tx, raw_data=raw_data)
        return raw_data

    def _trace_connect_hook(self, connected: bool) -> None:
        """Fallback para registrar conexiones cuando no se captura peer directo."""
        if connected:
            if not self.logger.connected_clients:
                self.logger.register_client_connect(None)
        else:
            if self.logger.connected_clients:
                self.logger.register_client_disconnect(None)

    async def _action_hook(
        self,
        func_code: int,
        start_address: int,
        address: int,
        count: int,
        registers: List[int],
        values: Optional[List[int]]
    ) -> None:
        """Hook invocado por pymodbus cuando un maestro interactúa con los datos."""
        self.datastore.handle_master_action(
            func_code=func_code,
            start_address=start_address,
            address=address,
            count=count,
            registers=registers,
            values=values,
        )
        return None

    def start(self, host: str = "0.0.0.0", port: int = 502) -> None:
        """Inicia el servidor en un hilo de fondo dedicado."""
        with self._lock:
            if self._is_running:
                return

            self._host = host
            self._port = port
            self._server_ready_event.clear()
            self._startup_error = None

            self._thread = threading.Thread(target=self._run_server_thread, daemon=True, name="ModbusServerThread")
            self._thread.start()

        # Esperar confirmación de arranque o fallo
        if not self._server_ready_event.wait(timeout=5.0):
            self.stop()
            raise ModbusServerError("Tiempo de espera agotado al iniciar el servidor Modbus TCP.")

        if self._startup_error:
            self.stop()
            raise ModbusServerError(f"Fallo al abrir el puerto {port}: {self._startup_error}")

        with self._lock:
            self._is_running = True
        self._notify_status()

    def _run_server_thread(self) -> None:
        """Función objetivo del hilo asíncrono del servidor."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Construir bloques según la capacidad del DataStore (count=1 porque values ya contiene la lista de elementos)
        size = self.datastore.size
        sd_co = SimData(0, count=1, values=self.datastore.get_coils(0, size), datatype=DataType.BITS)
        sd_di = SimData(0, count=1, values=self.datastore.get_discrete_inputs(0, size), datatype=DataType.BITS)
        sd_hr = SimData(0, count=1, values=self.datastore.get_holding_registers(0, size), datatype=DataType.REGISTERS)
        sd_ir = SimData(0, count=1, values=self.datastore.get_input_registers(0, size), datatype=DataType.REGISTERS)

        dev = SimDevice(
            id=self.datastore.slave_id,
            simdata=([sd_co], [sd_di], [sd_hr], [sd_ir]),
            action=self._action_hook
        )

        async def run_srv():
            try:
                server_instance = TrackedModbusTcpServer(
                    dev,
                    address=(self._host, self._port),
                    trace_packet=self._trace_packet_hook,
                    trace_connect=self._trace_connect_hook,
                    on_client_connect=self.logger.register_client_connect,
                    on_client_disconnect=self.logger.register_client_disconnect,
                )
                srv_task = asyncio.create_task(server_instance.serve_forever())
                await asyncio.sleep(0.05)

                # Vincular el runtime vivo al datastore
                if ModbusBaseServer.active_server and hasattr(ModbusBaseServer.active_server, "context"):
                    ctx = ModbusBaseServer.active_server.context
                    if hasattr(ctx, "devices") and self.datastore.slave_id in ctx.devices:
                        self.datastore.bind_pymodbus_runtime(ctx.devices[self.datastore.slave_id])

                self._server_ready_event.set()
                await srv_task
            except Exception as e:
                self._startup_error = e
                self._server_ready_event.set()

        try:
            self._loop.run_until_complete(run_srv())
        except Exception as e:
            if not self._server_ready_event.is_set():
                self._startup_error = e
                self._server_ready_event.set()
        finally:
            try:
                # Cancelar tareas pendientes en el loop
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
            except Exception:
                pass

    def stop(self) -> None:
        """Detiene el servidor de manera segura liberando el socket y el puerto."""
        with self._lock:
            if not self._is_running and not (self._thread and self._thread.is_alive()):
                return

            self._is_running = False

        if self._loop and self._loop.is_running():
            async def do_stop():
                try:
                    await ServerAsyncStop()
                except Exception:
                    pass

            try:
                future = asyncio.run_coroutine_threadsafe(do_stop(), self._loop)
                future.result(timeout=2.0)
            except Exception:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            self._thread = None

        self.datastore.bind_pymodbus_runtime(None)
        self.logger.clear_connected_clients()
        self._notify_status()
