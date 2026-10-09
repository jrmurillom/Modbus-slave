# Modbus Slave Pro

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-green)
![Protocol](https://img.shields.io/badge/Protocol-Modbus%20TCP-orange)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![CI](https://github.com/jrmurillom/Modbus-slave/actions/workflows/ci.yml/badge.svg)](https://github.com/jrmurillom/Modbus-slave/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/Tests-42%20Passing-brightgreen)

Simulador y servidor Modbus TCP con interfaz gráfica de escritorio desarrollada en Python 3.11 y PySide6 (Qt6).

---

## 📌 ¿Qué ofrece?

- **Servidor Modbus TCP:** Soporte para múltiples conexiones concurrentes y los 4 bloques de memoria estándar:
  - Coils (`0x`)
  - Discrete Inputs (`1x`)
  - Input Registers (`3x`)
  - Holding Registers (`4x`)
- **Telemetría en Vivo:** Contador de peticiones (`Rx = X : ID = Y : F = ZZ`), estado de enlace y visualización de clientes conectados (IP y puerto).
- **Edición In-Line:** Modificación directa de valores y alias en celdas con validación numérica (`Int16`, `UInt16`, `Float32`, `Hex`).
- **Direccionamiento Flexible:** Alternancia entre Base 0 (`0, 1, 2...`) y Base 1 PLC (`40001, 40002...`).
- **Conversión de Formatos y Endianness:** Interpretación en `UInt16`, `Int16`, `Hex`, `Bin`, `Float32` e `Int32` en esquemas `CDAB`, `ABCD`, `BADC` y `DCBA`.
- **Resaltado Reactivo:** Detección visual instantánea en celdas ante escrituras de maestros remotos.
- **Sniffer de Tráfico:** Inspección de tramas hexadecimales RX/TX en tiempo real, búfer acotado a 1,000 filas, copiado al portapapeles y exportación a `.csv` o `.txt`.
- **Simulación de Señales:** Generador de formas de onda (Rampa, Seno, Ruido y Pulsos binarios) para pruebas dinámicas.
- **Persistencia:** Guardado y carga de sesiones de trabajo en formato `.json`.
- **Atajos en la App:** Consulta interactiva de comandos rápidos desde la aplicación (`F1`).

---

## 📦 Portabilidad y Descargas

La aplicación puede ejecutarse de forma independiente en Windows sin requerir instalación previa de Python ni configuración de dependencias:

- **Descarga directa:** Puedes descargar el ejecutable listo para usar `ModbusSlavePro.exe` desde la sección de [Releases de GitHub](https://github.com/jrmurillom/Modbus-slave/releases).
- **Transporte directo:** Un único archivo listo para ejecutarse desde el disco o memoria USB en Windows 10 u 11.
- **Compilador local:** Incluye el script `build_exe.bat` para compilar el ejecutable localmente utilizando PyInstaller.

---

## 💻 Ejecución

### Opción 1: Ejecutable compilado (.exe)
Hacer doble clic en `dist\ModbusSlavePro.exe`.

### Opción 2: Script de inicio rápido
```cmd
.\run_app.bat
```

### Opción 3: Vía Python
```powershell
.\.venv\Scripts\python.exe -m modbus_slave.main
```

**Parámetros opcionales:**
```powershell
# Iniciar en puerto alternativo y con ID específico:
.\.venv\Scripts\python.exe -m modbus_slave.main --port 5020 --slave-id 1

# Especificar IP de enlace:
.\.venv\Scripts\python.exe -m modbus_slave.main --host 127.0.0.1 --port 5020
```

---

## 🛠 Compilación del Ejecutable

Para compilar o regenerar el binario autónomo:

```cmd
.\build_exe.bat
```

O mediante comando manual:
```powershell
.\.venv\Scripts\pyinstaller.exe --clean ModbusSlavePro.spec
```

El resultado se genera en `dist\ModbusSlavePro.exe`.

---

## 🧪 Pruebas Automatizadas

Para ejecutar la suite de pruebas unitarias y de integración:

```cmd
.\run_tests.bat
```
O con pytest directamente:
```powershell
.\.venv\Scripts\pytest.exe -v
```

---

## 📐 Estructura del Proyecto

```text
modbus-slave/
├── build_exe.bat               # Compilador a ejecutable de un solo clic
├── run_app.bat                 # Lanzador de la aplicación
├── run_tests.bat               # Ejecutor de la suite de pruebas
├── ModbusSlavePro.spec         # Configuración de compilación PyInstaller
├── requirements.txt            # Dependencias del proyecto
├── pyproject.toml              # Metadatos del paquete y configuración de pytest
├── LICENSE                     # Licencia de código abierto MIT
├── CONTRIBUTING.md             # Guía de contribución para desarrolladores
├── README.md                   # Documentación del proyecto
├── .github/
│   ├── workflows/              # Automatización CI/CD (Tests y Release .exe)
│   └── ISSUE_TEMPLATE/         # Plantillas de soporte y bugs
├── modbus_slave/
│   ├── main.py                 # Punto de entrada
│   ├── core/
│   │   ├── datastore.py        # Almacén de memoria thread-safe (0x, 1x, 3x, 4x)
│   │   ├── formatters.py       # Conversión de formatos y esquemas de Endianness
│   │   ├── server.py           # Servidor Modbus TCP y seguimiento de clientes
│   │   ├── logger.py           # Sniffer de tramas y telemetría Rx/Tx
│   │   └── simulation.py       # Motor de simulación de variables
│   ├── ui/
│   │   ├── main_window.py      # Ventana principal, telemetría y menús
│   │   ├── bridge.py           # Puente seguro de señales Qt
│   │   ├── theme.py            # Estilos de interfaz gráfica
│   │   ├── models/
│   │   │   └── register_model.py # Modelo virtualizado de registros
│   │   ├── views/
│   │   │   ├── register_view.py  # Vista de tabla con edición in-line
│   │   │   └── traffic_dock.py   # Dock del sniffer de tráfico
│   │   └── dialogs/
│   │       ├── connection_dialog.py     # Configuración de red y puerto
│   │       ├── register_setup_dialog.py # Configuración de esclavo (F8)
│   │       ├── shortcuts_dialog.py      # Referencia de atajos (F1)
│   │       └── simulation_dialog.py     # Configuración de simulación
│   └── config/
│       └── workspace.py        # Guardado y carga de sesiones en JSON
└── tests/                      # Suite de pruebas automatizadas (42 tests)
```
