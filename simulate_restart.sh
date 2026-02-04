#!/bin/bash

echo "🔄 Simulando reinicialização do computador..."

# 1. Parar o serviço automático (como se o PC estivesse desligando)
echo "🛑 Parando serviço automático (LaunchAgent)..."
launchctl unload ~/Library/LaunchAgents/com.ri.ponto.plist

# 2. Forçar a morte dos processos (garantir que tudo parou)
echo "🧹 Limpando processos remanescentes..."
pkill -9 -f "keep_alive.sh"
pkill -9 -f "run_cloudflare.py"
pkill -9 -f "app.py"
pkill -9 -f "cloudflared"
pkill -9 -f "ssh.*serveo.net"
pkill -9 -f "expose_docker.py"
rm -f run_cloudflare.lock

# Esperar um pouco para simular o tempo desligado
echo "⏳ Aguardando 3 segundos..."
sleep 3

# 3. Iniciar o serviço novamente (como se o PC estivesse ligando)
echo "🚀 Iniciando serviço novamente (LaunchAgent)..."
launchctl load ~/Library/LaunchAgents/com.ri.ponto.plist

echo "✅ Simulação concluída!"
echo "📄 Verifique o log com: tail -f ~/PontoEletronico/system.log"
