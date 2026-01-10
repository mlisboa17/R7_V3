@echo off
echo ========================================
echo    BOT R7_V3 - INICIANDO
echo ========================================
echo.

REM Mata processos Python existentes
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

REM Limpa cache Python
echo Limpando cache Python...
del /S /Q __pycache__ 2>nul
del /S /Q *.pyc 2>nul

echo.
echo Iniciando bot em background...
start /B python main.py > bot_output.log 2>&1

timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo    BOT INICIADO!
echo ========================================
echo.
echo Monitorando logs...
timeout /t 15 /nobreak >nul
powershell -Command "Get-Content .\logs\r7_v3.log -Tail 30 | Where-Object { $_ -match 'Conectado|ERROR|Erro|IA:|Snapshot' }"

echo.
echo Pressione qualquer tecla para ver log completo...
pause >nul
type logs\r7_v3.log | more
