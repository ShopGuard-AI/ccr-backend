@echo off
echo ========================================
echo   Iniciando Backend - Monitoramento
echo ========================================
echo.
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat
echo.
echo Iniciando API Server na porta 5000...
echo Backend disponivel em: http://localhost:5000
echo.
python api_server.py
pause
