#!/bin/bash

# Configurações - Altere se mudar a senha
CONTAINER_NAME="sql1"
DB_ORIGINAL="PontoEletronicoDB"
DB_TESTE="PontoTeste"
SA_PASSWORD="MyStrongPass123"
BACKUP_PATH="/var/opt/mssql/data"

echo "🚀 Iniciando processo de Backup e Restore..."

# 1. Gerar backup do banco original dentro do container
echo "📦 Gerando backup do banco original..."
docker exec $CONTAINER_NAME /opt/mssql-tools18/bin/sqlcmd \
   -S localhost -U sa -P "$SA_PASSWORD" -C \
   -Q "BACKUP DATABASE [$DB_ORIGINAL] TO DISK = N'$BACKUP_PATH/PontoEletronicoDB.bak' WITH FORMAT"

# 2. Copiar para o Mac (Backup de segurança)
echo "💾 Copiando arquivo para o Mac..."
docker cp $CONTAINER_NAME:$BACKUP_PATH/PontoEletronicoDB.bak ./PontoEletronicoDB.bak

# 3. Preparar arquivo para o banco de teste
echo "🔧 Ajustando permissões no container..."
docker cp ./PontoEletronicoDB.bak $CONTAINER_NAME:$BACKUP_PATH/PontoTeste.bak
docker exec -u 0 $CONTAINER_NAME chown mssql:root $BACKUP_PATH/PontoTeste.bak

# 4. Restaurar no banco de Teste
echo "🔄 Restaurando no banco [$DB_TESTE]..."
docker exec $CONTAINER_NAME /opt/mssql-tools18/bin/sqlcmd \
   -S localhost -U sa -P "$SA_PASSWORD" -C \
   -Q "RESTORE DATABASE [$DB_TESTE] FROM DISK = N'$BACKUP_PATH/PontoTeste.bak' WITH MOVE '$DB_ORIGINAL' TO '$BACKUP_PATH/PontoTeste.mdf', MOVE '${DB_ORIGINAL}_log' TO '$BACKUP_PATH/PontoTeste_log.ldf', REPLACE, RECOVERY"

echo "✅ Processo concluído com sucesso!"