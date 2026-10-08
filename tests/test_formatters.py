"""Pruebas unitarias para DataFormat y conversiones de Endianness."""

import pytest
from modbus_slave.core.formatters import (
    DataFormat,
    Endianness,
    decode_registers,
    encode_value,
    format_to_display_string,
    get_register_span,
)


def test_16bit_formats_roundtrip():
    # UInt16
    regs = encode_value(12345, DataFormat.UINT16)
    assert regs == [12345]
    assert decode_registers(regs, DataFormat.UINT16) == 12345

    # Int16 Positivo y Negativo
    regs_pos = encode_value(1500, DataFormat.INT16)
    assert decode_registers(regs_pos, DataFormat.INT16) == 1500

    regs_neg = encode_value(-1500, DataFormat.INT16)
    assert regs_neg == [65536 - 1500]
    assert decode_registers(regs_neg, DataFormat.INT16) == -1500

    # Hex
    regs_hex = encode_value("0xABCD", DataFormat.HEX)
    assert regs_hex == [0xABCD]
    assert decode_registers(regs_hex, DataFormat.HEX) == "0xABCD"

    # Binary
    regs_bin = encode_value("00000000 11111111", DataFormat.BIN)
    assert regs_bin == [255]
    assert decode_registers(regs_bin, DataFormat.BIN) == "00000000 11111111"


@pytest.mark.parametrize("endianness", [
    Endianness.ABCD,
    Endianness.CDAB,
    Endianness.BADC,
    Endianness.DCBA,
])
def test_float32_all_endianness_roundtrip(endianness):
    test_values = [0.0, 1.0, -1.0, 1234.56, -9876.54, 3.14159]
    for val in test_values:
        encoded = encode_value(val, DataFormat.FLOAT32, endianness=endianness)
        assert len(encoded) == 2
        decoded = decode_registers(encoded, DataFormat.FLOAT32, endianness=endianness)
        assert pytest.approx(decoded, abs=1e-3) == val


@pytest.mark.parametrize("endianness", [
    Endianness.ABCD,
    Endianness.CDAB,
    Endianness.BADC,
    Endianness.DCBA,
])
def test_int32_all_endianness_roundtrip(endianness):
    test_values = [0, 1, -1, 100000, -500000, 2147483647, -2147483648]
    for val in test_values:
        encoded = encode_value(val, DataFormat.INT32, endianness=endianness)
        assert len(encoded) == 2
        decoded = decode_registers(encoded, DataFormat.INT32, endianness=endianness)
        assert decoded == val


def test_register_span():
    assert get_register_span(DataFormat.UINT16) == 1
    assert get_register_span(DataFormat.INT16) == 1
    assert get_register_span(DataFormat.HEX) == 1
    assert get_register_span(DataFormat.BIN) == 1
    assert get_register_span(DataFormat.FLOAT32) == 2
    assert get_register_span(DataFormat.INT32) == 2
    assert get_register_span(DataFormat.UINT32) == 2


def test_display_string():
    assert format_to_display_string(1450.5678, DataFormat.FLOAT32, decimals=2) == "1450.57"
    assert format_to_display_string("0x00FF", DataFormat.HEX) == "0x00FF"
    assert format_to_display_string(100, DataFormat.UINT16) == "100"
