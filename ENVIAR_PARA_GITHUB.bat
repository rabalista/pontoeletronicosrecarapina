@echo off
TITLE ENVIAR ATUALIZACOES - PONTO ELETRONICO
color 0E
cd /d "C:\usr\PontoEletronico"

echo ===================================================
echo   ENVIANDO MELHORIAS PARA A NUVEM (GITHUB)
echo ===================================================
echo.

git add .
git commit -m "Sincronizacao automatica - %date% %time%"
git push origin main

echo.
echo ===================================================
echo   MELHORIAS ENVIADAS COM SUCESSO!
echo ===================================================
echo.
pause
