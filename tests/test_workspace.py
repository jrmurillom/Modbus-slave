"""Pruebas unitarias para persistencia de proyectos JSON."""

import json
import pytest
from modbus_slave.config.workspace import load_workspace_file, save_workspace_file


def test_workspace_save_and_load(tmp_path):
    project_file = tmp_path / "test_session.json"
    dummy_data = {
        "version": "1.0",
        "slave_id": 2,
        "host": "127.0.0.1",
        "port": 5020,
        "block": "holding_registers",
        "start_address": 0,
        "length": 50,
        "format_type": "float32",
        "endianness": "CDAB",
        "registers": {
            "0": {"alias": "Temp_Sensor_1", "val": 1234},
            "2": {"alias": "Motor_Speed", "val": 5678},
        }
    }

    save_workspace_file(str(project_file), dummy_data)
    assert project_file.exists()

    loaded = load_workspace_file(str(project_file))
    assert loaded["slave_id"] == 2
    assert loaded["port"] == 5020
    assert loaded["format_type"] == "float32"
    assert loaded["registers"]["0"]["alias"] == "Temp_Sensor_1"
    assert loaded["registers"]["0"]["val"] == 1234


def test_workspace_file_not_found(tmp_path):
    fake_path = tmp_path / "non_existent.json"
    with pytest.raises(FileNotFoundError):
        load_workspace_file(str(fake_path))
