@echo off
REM Directorio DG4 - Arranque del mini-servicio de WhatsApp
cd /d "%~dp0"

if not exist ".env" (
    echo.
    echo ============================================
    echo   FALTA CONFIGURAR whatsapp\.env
    echo   1. Copia el archivo .env.example y renombralo a .env
    echo   2. Llena PHONE_NUMBER_ID y WHATSAPP_ACCESS_TOKEN
    echo      con los datos de tu panel de Meta for Developers
    echo ============================================
    echo.
    pause
    exit /b
)

echo Verificando dependencias...
python -m pip install -r requirements.txt --quiet

echo.
echo ============================================
echo   Mini-servicio de WhatsApp - iniciando (modo local de prueba)
echo   No cierres esta ventana mientras lo uses.
echo   Para exponerlo de verdad a WhatsApp, ver whatsapp\LEEME_WHATSAPP.md
echo   (despliegue en Render, no requiere esta ventana abierta)
echo ============================================
echo.

python bot.py

pause
