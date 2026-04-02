@echo off
REM Script para lanzar la aplicación Django localmente
REM Este script cambia al directorio solar_app y ejecuta el servidor de desarrollo

setlocal enabledelayedexpansion

REM Define la ruta base del proyecto
set PROJECT_DIR=c:\Users\JuliansCastro\Documents\Developer\Python\Django\Solar-system-sales-quote-tool
set SOLAR_APP_DIR=%PROJECT_DIR%\solar_app
set PYTHON_EXE=C:/ProgramData/radioconda/python.exe

REM Cambiar al directorio de la aplicación
echo Navegando a: %SOLAR_APP_DIR%
cd /d "%SOLAR_APP_DIR%"

REM Verificar que estamos en el directorio correcto
if not exist "manage.py" (
    echo Error: manage.py no encontrado en %SOLAR_APP_DIR%
    echo Verifica que la ruta del proyecto sea correcta.
    exit /b 1
)

REM Ejecutar el servidor de desarrollo
echo.
echo ====================================
echo Iniciando servidor Django...
echo ====================================
echo.
"%PYTHON_EXE%" manage.py runserver

endlocal
