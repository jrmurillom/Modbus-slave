"""Pruebas unitarias para ThreadSafeDataStore."""

import threading
import pytest
from modbus_slave.core.datastore import ModbusBlockType, ThreadSafeDataStore


def test_datastore_initialization():
    ds = ThreadSafeDataStore(slave_id=1, size=50)
    assert ds.slave_id == 1
    assert ds.size == 50
    assert len(ds.get_holding_registers(0, 50)) == 50
    assert all(val == 0 for val in ds.get_holding_registers(0, 50))
    assert all(val is False for val in ds.get_coils(0, 50))


def test_holding_registers_read_write():
    ds = ThreadSafeDataStore(size=100)
    # Escritura individual
    ds.set_holding_register(10, 1234)
    assert ds.get_holding_register(10) == 1234

    # Enmascaramiento a 16 bits (0xFFFF)
    ds.set_holding_register(11, 0x1FFFF)
    assert ds.get_holding_register(11) == 0xFFFF

    # Escritura en bloque
    ds.set_holding_registers(20, [100, 200, 300])
    assert ds.get_holding_registers(20, 3) == [100, 200, 300]


def test_coils_read_write():
    ds = ThreadSafeDataStore(size=50)
    ds.set_coil(5, True)
    assert ds.get_coil(5) is True
    assert ds.get_coil(6) is False

    ds.set_coils(10, [True, False, True])
    assert ds.get_coils(10, 3) == [True, False, True]


def test_discrete_inputs_and_input_registers():
    ds = ThreadSafeDataStore(size=50)
    ds.set_discrete_input(2, True)
    assert ds.get_discrete_input(2) is True

    ds.set_input_register(7, 5555)
    assert ds.get_input_register(7) == 5555


def test_change_subscriber():
    ds = ThreadSafeDataStore(size=50)
    notifications = []

    def on_change(block, address, count, old_vals, new_vals, source):
        notifications.append({
            "block": block,
            "address": address,
            "count": count,
            "old": old_vals,
            "new": new_vals,
            "source": source
        })

    ds.subscribe(on_change)
    ds.set_holding_register(5, 42, source="local")

    assert len(notifications) == 1
    assert notifications[0]["block"] == ModbusBlockType.HOLDING_REGISTERS.value
    assert notifications[0]["address"] == 5
    assert notifications[0]["old"] == [0]
    assert notifications[0]["new"] == [42]
    assert notifications[0]["source"] == "local"

    # Master write hook
    ds.handle_master_action(func_code=16, start_address=0, address=5, count=1, registers=[], values=[999])
    assert len(notifications) == 2
    assert notifications[1]["new"] == [999]
    assert notifications[1]["source"] == "master"


def test_metadata_and_alias():
    ds = ThreadSafeDataStore(size=50)
    ds.set_alias(ModbusBlockType.HOLDING_REGISTERS.value, 1, "Motor_Speed_RPM")
    assert ds.get_alias(ModbusBlockType.HOLDING_REGISTERS.value, 1) == "Motor_Speed_RPM"
    assert ds.get_alias(ModbusBlockType.HOLDING_REGISTERS.value, 2) == ""


def test_thread_safety_concurrent_writes():
    ds = ThreadSafeDataStore(size=100)
    threads = []
    num_threads = 10
    iterations_per_thread = 100

    def writer(t_id):
        for i in range(iterations_per_thread):
            ds.set_holding_register(t_id, i)

    for t_id in range(num_threads):
        t = threading.Thread(target=writer, args=(t_id,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Todos los registros deben tener el último valor escrito
    for t_id in range(num_threads):
        assert ds.get_holding_register(t_id) == iterations_per_thread - 1
