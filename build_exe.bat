@echo off
setlocal
cd /d "%~dp0"

echo =====================================================
echo  Modbus Slave Pro - Compilador de Ejecutable (.exe)
echo =====================================================
echo.

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [INFO] Instalando PyInstaller en el entorno virtual...
    call .\.venv\Scripts\pip.exe install pyinstaller
)

echo [1/2] Limpiando compilaciones anteriores...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"

echo [2/2] Compilando ModbusSlavePro.exe portable...
.\.venv\Scripts\pyinstaller.exe --clean ModbusSlavePro.spec

if %ERRORLEVEL% equ 0 (
    echo.
    echo =====================================================
    echo  COMPILACION EXITOSA!
    echo  Ejecutable generado en:
    echo  %~dp0dist\ModbusSlavePro.exe
    echo =====================================================
) else (
    echo.
    echo [ERROR] Ocurrio un error durante la compilacion.
)
