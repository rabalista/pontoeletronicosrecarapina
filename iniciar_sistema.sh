#!/bin/bash

# =================================================================================
# INICIAR SISTEMA - PONTO ELETRÔNICO (SRE CARAPINA)
# =================================================================================
# Este script é executado automaticamente pelo LaunchAgent ao iniciar o Mac.

# 1. Aguarda a rede (Wi-Fi) conectar
sleep 15

# 2. Configura ambiente
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONUNBUFFERED=1

# Caminhos Absolutos
BASE_DIR="/Users/ridan/Downloads/VS-SQL/trae ponto eletronico online e offline cloudflare final/Ponto Eletronico - SRE Carapina"
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
CLOUDFLARE_PAGES_URL="https://pontowebsrecarapina.rabalista.workers.dev"

# Garante que estamos na pasta do script
if [ -d "$BASE_DIR" ]; then
    cd "$BASE_DIR"
else
    echo "❌ Erro: Diretório $BASE_DIR não encontrado." >> /tmp/ponto_startup.log
    exit 1
fi

# Log de início
echo "--- INICIANDO SISTEMA: $(date) ---" >> "$BASE_DIR/system.log"

# Limpa processos antigos
echo "🧹 Limpando processos antigos..."
/usr/bin/pkill -f "run_cloudflare.py"
/usr/bin/pkill -f "run_system.py"
# Mata processos na porta 5005
/usr/sbin/lsof -ti:5005 | xargs kill -9 2>/dev/null

# Limpa o log antigo (mas mantém o cabeçalho de início)
echo "--- RESET LOG ---" > "$BASE_DIR/system.log"

echo "🔄 Iniciando processos (Backend + Túnel)..."
# Inicia em background com nohup
# A saída vai para system.log para que este script possa ler a URL
nohup "$PYTHON_BIN" -u "$BASE_DIR/run_cloudflare.py" >> "$BASE_DIR/system.log" 2>&1 &
PID=$!
echo "📡 PID do processo principal: $PID"

# Loop para buscar a URL no log
MAX_ATTEMPTS=60
COUNT=0
URL=""

while [ $COUNT -lt $MAX_ATTEMPTS ]; do
    # Busca a URL ignorando emojis
    URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.(lhr\.life|localhost\.run|serveo\.net|trycloudflare\.com)" system.log | tail -1)
    LOCAL_IP=$(grep "IP LOCAL DETECTADO:" system.log | awk '{print $NF}')
    
    if [ -z "$URL" ]; then
        URL=$(grep -o "https://[a-zA-Z0-9.-]*\.lhr\.life" system.log | tail -1)
    fi
    if [ -z "$URL" ]; then
         URL=$(grep -o "https://[a-zA-Z0-9.-]*\.serveo\.net" system.log | tail -1)
    fi

    if [ ! -z "$URL" ]; then
        echo ""
        echo "=================================================================="
        echo "✅ SISTEMA ATUALIZADO E ONLINE!"
        echo "=================================================================="
        echo "👉 URL: $URL"
        
        # Espera o processo terminar (se morrer, o launchd reinicia)
        wait $PID
        exit 0
    fi
    
    sleep 2
    COUNT=$((COUNT+1))
done

echo "❌ Tempo esgotado. Verifique system.log."
exit 1
