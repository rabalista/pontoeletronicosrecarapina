@echo off
TITLE RESTAURAR BANCO DE DADOS - PONTO ELETRONICO
color 0C
cd /d "C:\usr\PontoEletronico"

echo ===================================================
echo   AVISO: ISSO VAI SUBSTITUIR O BANCO DE DADOS ATUAL!
echo ===================================================
echo.
echo Procurando backup em: C:\usr\PontoEletronico\PontoEletronicoDB.bak
echo.

if not exist "PontoEletronicoDB.bak" (
    echo [ERRO] Arquivo de backup nao encontrado!
    echo Primeiro rode o "SINCRONIZAR_DO_GITHUB.bat".
    pause
    exit
)

set /p confirm="Tem certeza que deseja RESTAURAR o banco agora? (S/N): "
if /i "%confirm%" NEQ "S" exit

echo.
echo Restaurando... (Isso pode demorar alguns segundos)

:: Tenta pegar as configurações do .env ou usa padrão
sqlcmd -S .\SQLEXPRESS -U admin_site -P Sedu@2026 -Q "ALTER DATABASE [PontoEletronicoDB] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; RESTORE DATABASE [PontoEletronicoDB] FROM DISK = 'C:\usr\PontoEletronico\PontoEletronicoDB.bak' WITH REPLACE; ALTER DATABASE [PontoEletronicoDB] SET MULTI_USER;"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo   BANCO DE DADOS RESTAURADO COM SUCESSO!
    echo ===================================================
) else (
    echo.
    echo ###################################################
    echo   ERRO AO RESTAURAR! Verifique se o SQL Server
    echo   esta instalado e se o usuario admin_site existe.
    echo ###################################################
)

echo.
pause
