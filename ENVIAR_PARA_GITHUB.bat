@echo off
TITLE ENVIAR ATUALIZACOES PARA GITHUB
color 0E
cd /d "%~dp0"

:: Garantir que o Git saiba quem é o usuário para não falhar no commit
git config user.name >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Configurando identidade local do Git para evitar erros de commit...
    git config --local user.name "Ridan Alves Balista"
    git config --local user.email "rabalista@sedu.es.gov.br"
)


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
