@echo off
echo ========================================================
echo   Ejecutando Suite Completa de Pruebas Automatizadas
echo   Proyecto: Modbus Slave Pro (28 Tests)
echo ========================================================
echo.
.\.venv\Scripts\pytest.exe -v
echo.
pause
