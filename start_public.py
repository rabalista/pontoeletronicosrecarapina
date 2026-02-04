import os
import sys
import time
import subprocess
import threading
import re

def update_config_js(public_url):
    config_path = os.path.join("netlify", "config.js")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove barra final se houver
        if public_url.endswith('/'):
            public_url = public_url[:-1]

        # Adiciona na lista API_CANDIDATES
        if public_url not in content:
            new_content = content.replace(
                'const API_CANDIDATES = [',
                f'const API_CANDIDATES = [\n  "{public_url}",'
            )
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✅ netlify/config.js atualizado com: {public_url}")
        else:
            print(f"ℹ️ URL já presente em netlify/config.js")
            
    except Exception as e:
        print(f"❌ Erro ao atualizar config.js: {e}")

def run_backend():
    print("🚀 Iniciando Backend Flask na porta 5005...")
    env = os.environ.copy()
    env["PORT"] = "5005"
    # Rodar app.py
    subprocess.call([sys.executable, "app.py"], env=env)

def start_tunnel():
    print("🌍 Iniciando Túnel Público (via Serveo)...")
    
    # Comando SSH para tunelamento reverso
    # Tenta usar serveo.net. Se falhar, tenta localhost.run
    # -o StrictHostKeyChecking=no para evitar prompt interativo de confirmação
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5005", "serveo.net"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print("⏳ Aguardando URL pública...")
    url = None
    
    # Ler saída para encontrar a URL
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(f"   [Serveo] {line.strip()}")
        if "Forwarding HTTP traffic from" in line:
            # Extrair URL
            match = re.search(r'https://[a-zA-Z0-9.-]+', line)
            if match:
                url = match.group(0)
                break
    
    if url:
        print(f"\n✨ TÚNEL ONLINE: {url} ✨\n")
        update_config_js(url)
        print("\n⚠️  ATENÇÃO: Mantenha esta janela aberta para o site funcionar!")
        print(f"👉 O site na Netlify conectará nesta URL: {url}")
        print("   (Se ainda não fez deploy, faça agora subindo a pasta 'netlify')\n")
        
        # Manter lendo a saída para não bloquear o buffer
        for line in process.stdout:
            pass
    else:
        print("❌ Não foi possível obter a URL do túnel. Tentando alternativa...")

if __name__ == "__main__":
    # Iniciar backend em thread separada
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.daemon = True
    backend_thread.start()
    
    # Dar um tempo para o backend subir
    time.sleep(3)
    
    # Iniciar túnel
    try:
        start_tunnel()
    except KeyboardInterrupt:
        sys.exit(0)
