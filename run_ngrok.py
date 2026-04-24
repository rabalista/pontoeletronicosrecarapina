import os
import subprocess
import time
import sys
import webbrowser
import socket
import json
import urllib.request
import re
import threading

def get_local_ip():
    """Detects the local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Check against a public DNS (doesn't actually connect) to get the correct interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def install_auth_token():
    print("\n🔐 CONFIGURAÇÃO DO NGROK (Acesso Externo)")
    print("Para funcionar fora da escola (4G), precisamos de um código gratuito.")
    print("1. Acesse: https://dashboard.ngrok.com/get-started/your-authtoken")
    print("2. Faça login com Google/Email (é grátis).")
    print("3. Copie o código que começa com '2...'")
    
    token = input("\n👉 Cole o seu Authtoken aqui e aperte ENTER: ").strip()
    if token:
        try:
            subprocess.run(["ngrok", "config", "add-authtoken", token], check=True)
            print("✅ Token salvo com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao salvar token: {e}")
            input("Aperte ENTER para sair...")
            sys.exit(1)

def update_config_js(ngrok_url, local_ip_url):
    print(f"🔄 Atualizando config.js...")
    try:
        path = "static/config.js"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Remove old ngrok links
            content = re.sub(r'"https://[a-z0-9-]+\.ngrok-free\.app",\s*', '', content)
            content = re.sub(r'"https://[a-z0-9-]+\.ngrok-free\.dev",\s*', '', content)
            
            # Remove old local IP links (simple regex for standard 192/10/172 subnets)
            content = re.sub(r'"http://192\.168\.\d+\.\d+:5005",\s*', '', content)
            content = re.sub(r'"http://10\.\d+\.\d+\.\d+:5005",\s*', '', content)
            content = re.sub(r'"http://172\.\d+\.\d+\.\d+:5005",\s*', '', content)
            
            # Add new links to API_CANDIDATES
            new_lines = f'  "{ngrok_url}",\n  "{local_ip_url}",\n'
            content = content.replace("const API_CANDIDATES = [", "const API_CANDIDATES = [\n" + new_lines)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print("✅ Arquivo config.js atualizado com Sucesso!")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar config.js: {e}")

def run_ngrok():
    print("\n🚀 Iniciando Ngrok (Acesso Externo)...")
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:5005"

    try:
        # mata ngrok anterior
        os.system("taskkill /F /IM ngrok.exe >nul 2>&1")
        
        # Inicia
        cmd = ["ngrok", "http", "5005"]
        process = subprocess.Popen(cmd)
        
        print("⏳ Aguardando link do Ngrok...")
        time.sleep(5)
        
        # Pega a URL da API local do Ngrok
        public_url = ""
        try:
            req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read())
                public_url = data['tunnels'][0]['public_url']
                print(f"\n✨ TÚNEL PRONTO: {public_url}")
        except Exception as e:
            print(f"⚠️ Não consegui pegar o link do Ngrok automaticamente: {e}")
            print("👉 Olhe no painel: https://dashboard.ngrok.com/cloud-edge/endpoints")

        # Atualiza config.js com AMBOS os links
        if public_url:
            update_config_js(public_url, local_url)
        
        print("\n" + "="*50)
        print("WEB / CELULAR (INTERNET 4G/5G):")
        print(f"👉 {public_url}")
        print("-" * 50)
        print("REDE LOCAL (WIFI / MESMA REDE):")
        print(f"👉 {local_url}")
        print("="*50 + "\n")
        
        print("⚠️  NÃO FECHE ESSA JANELA PRETA! (O sistema vai parar se fechar)")
        process.wait()
    except Exception as e:
        print(f"❌ Erro: {e}")
        input("Aperte ENTER...")

def run_backend():
    print("🚀 Iniciando Backend na porta 5005...")
    try:
        # Reusa o python atual para rodar app.py
        subprocess.run([sys.executable, "app.py"], check=True)
    except Exception as e:
        print(f"❌ Erro no Backend: {e}")

if __name__ == "__main__":
    # Verifica se já tem config
    config_path = os.path.expanduser("~/.ngrok2/ngrok.yml")
    print("Verificando configuração...")
    
    install_auth_token()
    
    # Inicia Backend em paralelo
    threading.Thread(target=run_backend, daemon=True).start()
    
    # Aguarda um pouco o backend subir
    time.sleep(3)
    
    run_ngrok()
