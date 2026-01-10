@echo off
title R7_V3 Trading Bot
cd /d "c:\Users\mlisb\PROJETOS_Local\R7_V3"

echo ========================================
echo    R7_V3 - Sistema de Trading Bot
echo ========================================
echo.
echo Iniciando sistema...
echo.

REM Mata processos anteriores se existirem
taskkill /f /im python.exe 2>nul

REM Aguarda um momento
timeout /t 2 /nobreak >nul

REM Inicia o bot principal
echo Iniciando R7_V3 Bot...
python main.py

REM Se o script terminar, aguarda antes de fechar
echo.
echo Bot finalizado. Pressione qualquer tecla para fechar...
pause >nul