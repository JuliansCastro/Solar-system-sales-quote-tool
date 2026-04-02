# Script para lanzar la aplicación Django localmente (PowerShell)
# Este script cambia al directorio solar_app y ejecuta el servidor de desarrollo

# Define las rutas
$PROJECT_DIR = "c:\Users\JuliansCastro\Documents\Developer\Python\Django\Solar-system-sales-quote-tool"
$SOLAR_APP_DIR = "$PROJECT_DIR\solar_app"
$PYTHON_EXE = "C:\ProgramData\radioconda\python.exe"

# Cambiar al directorio de la aplicación
Write-Host "Navegando a: $SOLAR_APP_DIR" -ForegroundColor Cyan
Set-Location $SOLAR_APP_DIR

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "manage.py")) {
    Write-Host "Error: manage.py no encontrado en $SOLAR_APP_DIR" -ForegroundColor Red
    Write-Host "Verifica que la ruta del proyecto sea correcta." -ForegroundColor Red
    exit 1
}

# Ejecutar el servidor de desarrollo
Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Write-Host "Iniciando servidor Django..." -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

& $PYTHON_EXE manage.py runserver
