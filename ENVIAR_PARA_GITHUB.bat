@echo off
TITLE ENVIAR ATUALIZACOES PARA GITHUB
color 0E
cd /d "C:\usr\PontoEletronico"

echo ===================================================
echo   ENVIANDO CODIGO E BACKUP PARA O GITHUB
echo ===================================================
echo.

:: Opcional: Chama o backup do banco antes de subir
set /p backup="Deseja gerar um novo backup do banco antes de subir? (S/N): "
if /i "%backup%"=="S" (
    call GERAR_BACKUP_BANCO.bat
)

echo.
echo Adicionando arquivos ao Git...
git add .

echo.
set /p msg="Digite o que voce mudou (ex: Ajuste no layout): "
if "%msg%"=="" set msg="Atualizacao de rotina"

echo.
echo Criando commit...
git commit -m "%msg%"

echo.
echo Enviando para a nuvem (GitHub)...
git push origin main

echo.
echo ===================================================
echo   CONCLUIDO! SEU SISTEMA ESTA SALVO NA NUVEM.
echo ===================================================
echo.
pause
