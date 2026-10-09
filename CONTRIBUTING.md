# Guía de Contribución a Modbus Slave Pro

¡Gracias por tu interés en contribuir a **Modbus Slave Pro**! Este proyecto es de código abierto bajo licencia MIT y busca ofrecer una herramienta de simulación industrial robusta, modular y de alto rendimiento.

Para mantener los más altos estándares de calidad y estabilidad, por favor sigue estas directrices antes de proponer cambios o enviar un Pull Request.

---

## 🛠 Entorno de Desarrollo Local

### Requisitos Previos
- **Python 3.11** o superior.
- **Git** instalado.
- Sistema Operativo: Windows 10/11 recomendado (plataforma objetivo principal para el ejecutable y UI).

### Configuración del Entorno

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/jrmurillom/Modbus-slave.git
   cd Modbus-slave
   ```

2. **Crear y activar un entorno virtual:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Instalar dependencias de desarrollo:**
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install pytest pytest-qt
   ```

---

## 🧪 Pruebas y Validación de Calidad

Cualquier cambio propuesto debe pasar sin errores la suite completa de pruebas antes de ser considerado.

Para ejecutar todas las pruebas automatizadas:
```powershell
pytest tests/ -v
```

### Reglas de Calidad Obligatorias:
- **Cero regresiones:** Todos los tests existentes deben permanecer en verde (PASS).
- **Nuevas pruebas:** Toda funcionalidad añadida o corrección de bugs debe incluir pruebas unitarias o de integración en el directorio `tests/`.
- **Thread Safety:** Todo acceso a memoria compartida o estructuras de datos en `core/` debe garantizar protección de concurrencia mediante `threading.Lock` o `threading.RLock`.

---

## 🏗 Arquitectura y Estilo de Código

El proyecto está diseñado bajo un desacoplamiento estricto entre el motor de protocolo y la interfaz gráfica:

```text
modbus_slave/
├── core/       # Motor sin dependencias de GUI (Datastore, Servidor Modbus, Formateadores, Logger)
├── ui/         # Interfaz PySide6 (Modelos virtuales, Vistas, Docks, Diálogos y Tema)
└── config/     # Serialización y persistencia de workspaces (.json)
```

1. **Separación de Responsabilidades:** No acoplar lógica de widgets o interfaz dentro de `core/`. La comunicación entre hilos y UI se gestiona exclusivamente a través de señales (`QtSignalBridge`).
2. **Legibilidad y Modularidad:** Prefiere código explícito, modular y auto-documentado sobre soluciones crípticas.
3. **No alterar el Look & Feel:** La interfaz sigue un tema industrial oscuro coherente (`Industrial Theme`). No introduzcas estilos dispersos o incompatibles.

---

## 🌿 Flujo de Trabajo para Pull Requests

1. **Crear una rama temática:**
   ```bash
   git checkout -b feature/mi-nueva-funcionalidad
   # o
   git checkout -b fix/correccion-de-bug
   ```

2. **Realizar tus cambios y probar localmente:**
   Asegúrate de que `pytest tests/ -v` se ejecute al 100% exitoso.

3. **Escribir mensajes de commit claros:**
   Describe brevemente qué se modificó y por qué (ej. `fix: corregir validación de límites en registros float32`).

4. **Enviar el Pull Request:**
   - Abre el PR hacia la rama `main` de este repositorio.
   - Completa la plantilla del Pull Request describiendo el contexto y las pruebas realizadas.
   - El pipeline automatizado de **GitHub Actions** ejecutará las pruebas en un entorno limpio para validar el PR.

---

## 🐛 Reporte de Errores y Sugerencias

Si encuentras un error o tienes una propuesta de mejora:
- Revisa las [Issues existentes](https://github.com/jrmurillom/Modbus-slave/issues) para evitar duplicados.
- Utiliza las plantillas oficiales de **Bug Report** o **Feature Request** proporcionando pasos exactos para reproducir el comportamiento o el caso de uso industrial que se desea resolver.
