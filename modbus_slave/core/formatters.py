"""Módulo de conversión y formateo de datos para registros Modbus.

Proporciona soporte completo para:
- 16-bit: Unsigned Int (UInt16), Signed Int (Int16), Hexadecimal, Binario.
- 32-bit: Int32, UInt32, Float32 (IEEE-754).
- Los 4 esquemas de ordenamiento de bytes industriales (Endianness):
  - ABCD: Big-Endian (Motorola, estándar IEEE-754).
  - CDAB: Little-Endian Word Swap (Estándar industrial Modicon / Schneider).
  - BADC: Big-Endian Byte Swap.
  - DCBA: Little-Endian puro (Intel x86).
"""

from __future__ import annotations

import struct
from enum import Enum
from typing import Any, List, Sequence, Union


class DataFormat(str, Enum):
    """Formatos de interpretación de registros."""
    UINT16 = "uint16"
    INT16 = "int16"
    HEX = "hex"
    BIN = "bin"
    INT32 = "int32"
    UINT32 = "uint32"
    FLOAT32 = "float32"


class Endianness(str, Enum):
    """Ordenamiento de bytes para tipos de 32 bits."""
    ABCD = "ABCD"  # Big-Endian
    CDAB = "CDAB"  # Little-Endian Byte-Swap (Modicon)
    BADC = "BADC"  # Big-Endian Byte-Swap
    DCBA = "DCBA"  # Little-Endian


def get_register_span(format_type: Union[DataFormat, str]) -> int:
    """Retorna la cantidad de registros de 16 bits requeridos por el tipo de dato."""
    fmt = DataFormat(format_type)
    if fmt in (DataFormat.INT32, DataFormat.UINT32, DataFormat.FLOAT32):
        return 2
    return 1


def _reorder_32bit_bytes_from_abcd(raw_4bytes: bytes, target_endianness: Endianness) -> bytes:
    """Convierte 4 bytes en formato canónico ABCD al formato destino."""
    b0, b1, b2, b3 = raw_4bytes
    if target_endianness == Endianness.ABCD:
        return bytes([b0, b1, b2, b3])
    elif target_endianness == Endianness.CDAB:
        return bytes([b2, b3, b0, b1])
    elif target_endianness == Endianness.BADC:
        return bytes([b1, b0, b3, b2])
    elif target_endianness == Endianness.DCBA:
        return bytes([b3, b2, b1, b0])
    raise ValueError(f"Endianness desconocido: {target_endianness}")


def _reorder_32bit_bytes_to_abcd(source_4bytes: bytes, source_endianness: Endianness) -> bytes:
    """Convierte 4 bytes desde el formato fuente al canónico ABCD."""
    if source_endianness == Endianness.ABCD:
        return source_4bytes
    elif source_endianness == Endianness.CDAB:
        b0, b1, b2, b3 = source_4bytes
        return bytes([b2, b3, b0, b1])
    elif source_endianness == Endianness.BADC:
        b0, b1, b2, b3 = source_4bytes
        return bytes([b1, b0, b3, b2])
    elif source_endianness == Endianness.DCBA:
        b0, b1, b2, b3 = source_4bytes
        return bytes([b3, b2, b1, b0])
    raise ValueError(f"Endianness desconocido: {source_endianness}")


def decode_registers(
    registers: Sequence[int],
    format_type: Union[DataFormat, str],
    endianness: Union[Endianness, str] = Endianness.CDAB,
) -> Any:
    """Decodifica registros crudos de 16 bits al tipo de dato especificado.
    
    Args:
        registers: Secuencia de enteros de 16 bits (1 o 2 elementos).
        format_type: Formato deseado.
        endianness: Ordenamiento para tipos de 32 bits.
        
    Returns:
        Valor decodificado (int, float o str).
    """
    fmt = DataFormat(format_type)
    end = Endianness(endianness)
    reg0 = (registers[0] if len(registers) > 0 else 0) & 0xFFFF

    # Formatos de 16 bits
    if fmt == DataFormat.UINT16:
        return reg0

    if fmt == DataFormat.INT16:
        # Convertir a con signo (complemento a 2)
        return reg0 if reg0 < 32768 else reg0 - 65536

    if fmt == DataFormat.HEX:
        return f"0x{reg0:04X}"

    if fmt == DataFormat.BIN:
        b_str = f"{reg0:016b}"
        return f"{b_str[:8]} {b_str[8:]}"

    # Formatos de 32 bits (requiere 2 registros)
    reg1 = (registers[1] if len(registers) > 1 else 0) & 0xFFFF
    # Empaquetar los 2 registros en 4 bytes de red
    r0_bytes = struct.pack(">H", reg0)
    r1_bytes = struct.pack(">H", reg1)
    combined = r0_bytes + r1_bytes

    # Convertir a ABCD canónico
    canonical_bytes = _reorder_32bit_bytes_to_abcd(combined, end)

    if fmt == DataFormat.FLOAT32:
        return struct.unpack(">f", canonical_bytes)[0]

    if fmt == DataFormat.INT32:
        return struct.unpack(">i", canonical_bytes)[0]

    if fmt == DataFormat.UINT32:
        return struct.unpack(">I", canonical_bytes)[0]

    return reg0


def encode_value(
    value: Any,
    format_type: Union[DataFormat, str],
    endianness: Union[Endianness, str] = Endianness.CDAB,
) -> List[int]:
    """Codifica un valor de alto nivel en una lista de registros de 16 bits (0-65535).
    
    Args:
        value: Valor numérico o cadena (para hex/bin).
        format_type: Formato del valor ingresado.
        endianness: Ordenamiento para tipos de 32 bits.
        
    Returns:
        Lista de 1 o 2 enteros de 16 bits.
    """
    fmt = DataFormat(format_type)
    end = Endianness(endianness)

    # 16-bit UInt
    if fmt == DataFormat.UINT16:
        val = int(value)
        return [max(0, min(val, 0xFFFF))]

    # 16-bit Int (Signed)
    if fmt == DataFormat.INT16:
        val = int(value)
        if val < 0:
            val = (val + 65536) & 0xFFFF
        return [val & 0xFFFF]

    # Hexadecimal
    if fmt == DataFormat.HEX:
        s_val = str(value).strip().lower()
        if s_val.startswith("0x"):
            s_val = s_val[2:]
        val = int(s_val or "0", 16)
        return [val & 0xFFFF]

    # Binario
    if fmt == DataFormat.BIN:
        s_val = str(value).replace(" ", "").strip()
        val = int(s_val or "0", 2)
        return [val & 0xFFFF]

    # 32-bit Float
    if fmt == DataFormat.FLOAT32:
        f_val = float(value)
        abcd_bytes = struct.pack(">f", f_val)
        target_bytes = _reorder_32bit_bytes_from_abcd(abcd_bytes, end)
        r0 = struct.unpack(">H", target_bytes[:2])[0]
        r1 = struct.unpack(">H", target_bytes[2:])[0]
        return [r0, r1]

    # 32-bit Int
    if fmt == DataFormat.INT32:
        i_val = int(value)
        abcd_bytes = struct.pack(">i", i_val)
        target_bytes = _reorder_32bit_bytes_from_abcd(abcd_bytes, end)
        r0 = struct.unpack(">H", target_bytes[:2])[0]
        r1 = struct.unpack(">H", target_bytes[2:])[0]
        return [r0, r1]

    # 32-bit UInt
    if fmt == DataFormat.UINT32:
        u_val = int(value)
        abcd_bytes = struct.pack(">I", u_val)
        target_bytes = _reorder_32bit_bytes_from_abcd(abcd_bytes, end)
        r0 = struct.unpack(">H", target_bytes[:2])[0]
        r1 = struct.unpack(">H", target_bytes[2:])[0]
        return [r0, r1]

    return [int(value) & 0xFFFF]


def format_to_display_string(
    value: Any,
    format_type: Union[DataFormat, str],
    decimals: int = 2
) -> str:
    """Convierte el valor decodificado a una cadena limpia para la tabla."""
    fmt = DataFormat(format_type)
    if fmt == DataFormat.FLOAT32 and isinstance(value, (int, float)):
        return f"{value:.{decimals}f}"
    if fmt == DataFormat.HEX:
        return str(value)
    if fmt == DataFormat.BIN:
        return str(value)
    return str(value)
