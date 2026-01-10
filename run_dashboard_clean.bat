@echo off
echo ============================================
echo 🎯 R7_V3 Dashboard - Inicialização Otimizada
echo ============================================
echo.
echo Iniciando dashboard sem erros de console...
echo.
cd /d %~dp0
streamlit run dashboard_r7_v2.py --server.port 8504 --server.headless true --logger.level error
echo.
echo Dashboard finalizado.
pause</content>
<parameter name="filePath">c:\Users\mlisb\PROJETOS_Local\R7_V3\run_dashboard_clean.bat