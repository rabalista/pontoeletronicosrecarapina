@echo off
TITLE SINCRONIZAR SISTEMA - PONTO ELETRONICO
color 0B
cd /d "C:\usr\PontoEletronico"

echo ===================================================
echo   BUSCANDO ATUALIZACOES DA MAQUINA PRINCIPAL
echo ===================================================
echo.

git pull origin main --allow-unrelated-histories

echo.
echo ===================================================
echo   SISTEMA ATUALIZADO COM SUCESSO!
echo ===================================================
echo.
pause
