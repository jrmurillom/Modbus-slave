# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/)
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2026-10-08

### Añadido
- **Servidor Modbus TCP:** Soporte multiconexión en segundo plano para los 4 bloques de datos estándar:
  - Coils (`0x`)
  - Discrete Inputs (`1x`)
  - Input Registers (`3x`)
  - Holding Registers (`4x`)
- **Interfaz Gráfica Industrial (PySide6 / Qt6):**
  - Tema visual oscuro de alto contraste optimizado para entornos de control.
  - Telemetría en vivo con contador de peticiones del maestro (`Rx = X : ID = Y : F = ZZ`).
  - Detección y listado de clientes Modbus conectados (IP y puerto).
- **Edición In-Line:**
  - Modificación directa en celdas estilo hoja de cálculo.
  - Validadores numéricos (`Int16`, `UInt16`, `Float32`, `Hex`) con feedback visual de borde de advertencia.
  - Alternancia rápida con barra espaciadora para bits y coils.
- **Direccionamiento:**
  - Base 0 Protocol Address (`0, 1, 2...`) por defecto.
  - Alternancia a Base 1 PLC Modicon (`40001, 40002...`).
  - Diálogo y atajo de salto rápido a registro (`Ctrl + G`).
- **Conversión de Formatos y Endianness:**
  - Decodificación y codificación para `UInt16`, `Int16`, `Hex`, `Bin`, `Float32` (IEEE-754) e `Int32`.
  - Soporte de los 4 esquemas de ordenamiento de bytes: `CDAB`, `ABCD`, `BADC` y `DCBA`.
- **Sniffer de Tráfico:**
  - Dock acoplable de inspección de tramas hexadecimales RX/TX en tiempo real.
  - Límite de memoria acotado a 1,000 filas con auto-poda para ejecución continua.
  - Exportación de tráfico capturado a `.csv` o `.txt` y copiado al portapapeles (`Ctrl + C`).
- **Simulación de Señales:**
  - Generadores de onda en segundo plano: Rampa, Seno, Ruido Aleatorio y Pulsos periódicos.
- **Ventana de Atajos de Teclado (`F1`):**
  - Diálogo interactivo accesible desde el menú `Ayuda`, barra de herramientas o tecla `F1`.
- **Portabilidad y Distribución:**
  - Script automatizado `build_exe.bat` para empaquetado PyInstaller.
  - Binario autónomo compilado `dist/ModbusSlavePro.exe` (~47 MB) con icono incrustado en el recurso PE.
  - Icono oficial de la aplicación (Matriz de Registros Modbus).
- **Pruebas Automatizadas:**
  - Suite de 35 pruebas unitarias e integrales (`pytest`) cubriendo todas las capas al 100%.
