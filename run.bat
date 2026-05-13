@echo off
REM TESTING FRAMEWORK SETUP SCRIPT

echo.
echo ========================================
echo   TESTING FRAMEWORK SETUP
echo ========================================
echo.

REM Crear carpetas
echo [1/3] Creando carpetas...
mkdir templates 2>nul
mkdir static\css 2>nul
mkdir static\js 2>nul
echo ✓ Carpetas creadas

REM Instalar Python
echo.
echo [2/3] Instalando dependencias...
pip install -q Flask Flask-CORS selenium requests beautifulsoup4 webdriver-manager
echo ✓ Dependencias instaladas

REM Ejecutar app
echo.
echo [3/3] Iniciando servidor...
echo.
echo ✓ Abre: http://localhost:5000
echo.
python app.py

pause
