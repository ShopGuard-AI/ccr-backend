@echo off
echo ========================================
echo   Iniciando Frontend - Monitoramento
echo ========================================
echo.
echo Mudando para diretorio frontend...
cd frontend
echo.
echo Iniciando servidor de desenvolvimento...
echo Frontend disponivel em: http://localhost:5173
echo.
call npm run dev
pause
