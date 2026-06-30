@echo off
TITLE PONTO ELETRONICO - SISTEMA (NAO FECHE)
color 0A

cd /d "%~dp0"

echo ===================================================
echo   INICIANDO SISTEMA DE PONTO + ACESSO EXTERNO
echo ===================================================
echo.
echo 1. Iniciando o Python...
echo 2. Ligando o Motor (Backend)...
echo 3. Abrindo o Tunel (Ngrok)...
echo.
echo AGUARDE O LINK APARECER ABAIXO...
echo.
echo Sistema atualizado: Brasao adicionado ao relatorio SIAHRES.

.\.venv\Scripts\python.exe run_ngrok.py

echo.
echo O SISTEMA PAROU. PODE FECHAR ESTA JANELA.
pause
