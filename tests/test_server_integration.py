"""Prueba de integración de extremo a extremo: Servidor Modbus TCP contra Cliente real."""

import asyncio
from pymodbus.client import AsyncModbusTcpClient

from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore
from modbus_slave.core.logger import TrafficLogger
from modbus_slave.core.server import ModbusTcpServerEngine


def test_server_client_integration_e2e():
    async def _run():
        port = 5029
        ds = ThreadSafeDataStore(slave_id=1, size=100)
        logger = TrafficLogger()
        server = ModbusTcpServerEngine(datastore=ds, logger=logger)

        # Establecer valores iniciales
        ds.set_holding_register(0, 1111)
        ds.set_holding_register(1, 2222)
        ds.set_coil(0, True)

        server.start(host="127.0.0.1", port=port)
        assert server.is_running is True

        try:
            # Cliente Modbus TCP real
            client = AsyncModbusTcpClient("127.0.0.1", port=port)
            connected = await client.connect()
            assert connected is True

            # 1. Leer Holding Registers (FC03)
            rr = await client.read_holding_registers(address=0, count=2, device_id=1)
            assert not rr.isError()
            assert rr.registers == [1111, 2222]

            # 2. Escribir un Registro (FC06)
            wr = await client.write_register(address=5, value=9876, device_id=1)
            assert not wr.isError()
            # Verificar que el DataStore en memoria se actualizó
            assert ds.get_holding_register(5) == 9876

            # 3. Leer Coils (FC01) y Escribir Coil (FC05)
            rc = await client.read_coils(address=0, count=2, device_id=1)
            assert not rc.isError()
            assert rc.bits[0] is True

            wc = await client.write_coil(address=3, value=True, device_id=1)
            assert not wc.isError()
            assert ds.get_coil(3) is True

            # 4. Verificar que el Sniffer capturó las tramas y el contador Rx subió
            assert logger.rx_count >= 4
            assert logger.tx_count >= 4
            assert logger.error_count == 0

            entries = logger.get_entries()
            assert len(entries) >= 8  # 4 peticiones + 4 respuestas
            assert any(e.direction == "RX" for e in entries)
            assert any(e.direction == "TX" for e in entries)

            client.close()

        finally:
            server.stop()
            assert server.is_running is False

    asyncio.run(_run())


def test_server_reset_values_on_the_fly_e2e():
    """Valida que reset_values() opera on-the-fly con cliente Modbus TCP en comunicación activa."""
    async def _run():
        port = 5031
        ds = ThreadSafeDataStore(slave_id=1, size=50)
        logger = TrafficLogger()
        server = ModbusTcpServerEngine(datastore=ds, logger=logger)

        ds.set_holding_registers(0, [100, 200, 300])
        server.start(host="127.0.0.1", port=port)

        try:
            client = AsyncModbusTcpClient("127.0.0.1", port=port)
            connected = await client.connect()
            assert connected is True

            # 1. Maestro lee valores iniciales
            rr1 = await client.read_holding_registers(address=0, count=3, device_id=1)
            assert not rr1.isError()
            assert rr1.registers == [100, 200, 300]

            # 2. Reseteo ON-THE-FLY en caliente por el operador
            ds.reset_values(ModbusBlockType.HOLDING_REGISTERS.value)

            # 3. Maestro lee de inmediato SIN desconexión: debe leer 0
            rr2 = await client.read_holding_registers(address=0, count=3, device_id=1)
            assert not rr2.isError()
            assert rr2.registers == [0, 0, 0]

            # 4. El socket permanece vivo: maestro puede seguir escribiendo
            wr = await client.write_register(address=0, value=999, device_id=1)
            assert not wr.isError()
            assert ds.get_holding_register(0) == 999

            client.close()
        finally:
            server.stop()

    asyncio.run(_run())

