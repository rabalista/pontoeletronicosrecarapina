#!/bin/bash

# =================================================================================
# START ROBUST - PONTO ELETRÔNICO (SRE CARAPINA)
# =================================================================================
# Script robusto para inicialização automática via LaunchAgent.
# Garante que Docker, Rede e Dependências estejam prontos antes de iniciar o app.

# 1. Configura ambiente
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONUNBUFFERED=1

# Caminhos Absolutos
BASE_DIR="/Users/ridan/PontoEletronico"
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
LOG_FILE="$BASE_DIR/system_startup.log"

# Função de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Inicializa log
echo "--- NEW SESSION ---" >> "$LOG_FILE"
log "🚀 Iniciando script de startup robusto..."

# 2. Aguarda acesso ao diretório
MAX_RETRIES=30
COUNT=0
while [ ! -d "$BASE_DIR" ]; do
    log "⏳ Aguardando diretório do projeto ficar acessível ($COUNT/$MAX_RETRIES)..."
    sleep 2
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        log "❌ ERRO: Diretório não encontrado após 60s. Abortando."
        exit 1
    fi
done
cd "$BASE_DIR"
log "✅ Diretório acessado: $(pwd)"

# 3. Verifica e Inicia Docker
log "🐳 Verificando Docker..."
if ! /usr/bin/pgrep -f "Docker" > /dev/null; then
    log "⚠️  Docker não está rodando. Tentando iniciar..."
    open -a Docker
    
    # Aguarda Docker iniciar
    log "⏳ Aguardando Docker Desktop inicializar..."
    DOCKER_READY=0
    for i in {1..60}; do
        if docker info > /dev/null 2>&1; then
            DOCKER_READY=1
            break
        fi
        sleep 5
        echo -n "." >> "$LOG_FILE"
    done
    
    if [ $DOCKER_READY -eq 0 ]; then
        log "❌ ERRO: Docker falhou ao iniciar ou demorou demais."
    else
        log "✅ Docker iniciado com sucesso!"
    fi
else
    log "✅ Docker já estava rodando."
fi

# 4. Aguarda SQL Server (Porta 1433)
log "🗄️  Aguardando Banco de Dados (SQL Server)..."
DB_READY=0
for i in {1..45}; do
    if lsof -i :1433 > /dev/null 2>&1; then
        DB_READY=1
        break
    fi
    sleep 2
done

if [ $DB_READY -eq 1 ]; then
    log "✅ Banco de Dados detectado."
else
    log "⚠️  Banco de Dados não detectado na porta 1433 ainda, tentando iniciar app assim mesmo..."
fi

# 5. Limpeza de Processos Antigos
log "🧹 Limpando processos antigos para evitar conflitos..."
pkill -9 -f "keep_alive.sh"
pkill -9 -f "run_cloudflare.py"
pkill -9 -f "expose_docker.py"
pkill -9 -f "app.py"
pkill -9 -f "cloudflared"
pkill -9 -f "caffeinate"
# ssh cleanup for serveo
pkill -9 -f "ssh.*serveo.net"

# Liberar porta 5005 explicitamente
lsof -ti:5005 | xargs kill -9 2>/dev/null

log "✅ Prosseguindo para iniciar aplicação..."

# 6. Inicia Aplicação
# A Cafeína agora é gerida internamente pelo run_cloudflare.py
log "🔥 Iniciando run_cloudflare.py..."

# Redireciona stdout/stderr para system.log
# Usamos -u para output sem buffer
nohup "$PYTHON_BIN" -u "$BASE_DIR/run_cloudflare.py" >> "$BASE_DIR/system.log" 2>&1 &
APP_PID=$!
log "✅ App iniciado com PID: $APP_PID"

# Monitoramento
# Se o run_cloudflare.py morrer, o script de startup encerra (e o LaunchAgent reinicia tudo)
wait $APP_PID
log "🛑 O processo do App (PID $APP_PID) encerrou."
