import os
import sys
import time
import subprocess
import threading
import re
import hashlib
import urllib.request
import urllib.parse
import signal
import platform

# Configuração
CLOUDFLARE_PAGES_URL = "https://pontowebsrecarapina.rabalista.workers.dev"
PORT = 5005
LOCK_FILE = "run_cloudflare.lock"
IS_WINDOWS = platform.system() == 'Windows'

# Variáveis globais para controle robusto
CURRENT_PUBLIC_URL = None
CAFFEINATE_PROCESS = None

def update_config_js(url):
    """Atualiza o config.js com a nova URL e ID de descoberta."""
    try:
        import socket
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "127.0.0.1"
            
        # Try to find a real IP on Windows
        if local_ip.startswith("127."):
             try:
                 # This is a basic attempt, might need more robust logic for Windows if multiple NICs
                 local_ip = socket.gethostbyname(socket.gethostname())
             except: pass
        
        local_api = f"http://{local_ip}:{PORT}"
        print(f"   🏠 IP LOCAL DETECTADO: {local_api}")

        # Update in static and public folders
        paths_to_update = [
            os.path.join("static", "config.js"),
            os.path.join("public", "config.js"),
            os.path.join("site_para_cloudflare 10", "config.js")
        ]

        for config_path in paths_to_update:
            if not os.path.exists(config_path): continue
            
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
        
            top_candidates = [url, local_api]
            unique_top = []
            for c in top_candidates:
                if c and c not in unique_top: unique_top.append(c)

            existing_candidates = []
            match_list = re.search(r'const API_CANDIDATES = \[(.*?)\];', content, re.DOTALL)
            if match_list:
                existing_candidates = [c.strip().strip('"').strip("'") for c in match_list.group(1).split(',')]
                existing_candidates = [c for c in existing_candidates if c]

            unique_all = []
            for c in (unique_top + existing_candidates):
                if c and c not in unique_all and len(unique_all) < 8:
                    unique_all.append(c)
            
            candidates_str = "\n".join([f'  "{c}",' for c in unique_all])
            content = re.sub(r'const API_CANDIDATES = \[.*?\];', 
                            f'const API_CANDIDATES = [\n{candidates_str}\n];', 
                            content, flags=re.DOTALL)
            
            discovery_id = get_discovery_id()
            print(f"   🆔 ID de Descoberta: {discovery_id}")
            content = re.sub(r'const DISCOVERY_ID = ".*?";', f'const DISCOVERY_ID = "{discovery_id}";', content)
            
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"   ✅ Arquivo '{config_path}' atualizado!")
    except Exception as e:
        print(f"   ⚠️ Falha ao atualizar config.js: {e}")

def check_link_ready(url, timeout=90):
    """Proba a URL até ela responder 200 ou o timeout passar."""
    if "localhost" in url or "127.0.0.1" in url: return True
    
    print(f"📡 Verificando se o link {url} já está ativo (Warm-up)...")
    max_attempts = max(1, timeout // 3)
    for i in range(max_attempts):
        try:
            req = urllib.request.Request(f"{url}/api/online", headers={
                'User-Agent': 'Mozilla/5.0',
                'Bypass-Tunnel-Reminder': 'true'
            })
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print(f"✨ Link {url} VERIFICADO!")
                    return True
        except Exception as e:
            pass
        if i % 5 == 0: print(f"   ⏳ Aguardando aquecimento ({i+1}/{max_attempts})...")
        time.sleep(3)
    return False

def run_backend():
    print(f"🚀 Iniciando Backend na porta {PORT}...")
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    
    while True:
        try:
            kill_port(PORT)
            with open("backend.log", "a") as log_file:
                proc = subprocess.Popen([sys.executable, "app.py"], env=env, stdout=log_file, stderr=log_file)
            proc.wait()
            log(f"Backend (PID {proc.pid}) encerrou. Reiniciando em 5s...")
        except Exception as e:
            log(f"Erro ao executar backend: {e}")
        time.sleep(5)

def log(msg):
    try:
        with open("debug_run.log", "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except: pass

def start_serveo_fallback():
    """Tenta abrir um túnel reserva via Serveo se o Cloudflare demorar."""
    # Serveo via ssh might rely on 'ssh' being in path (Windows has OpenSSH usually)
    print("🌍 [Reserva] Iniciando túnel Serveo...")
    while True:
        try:
            # cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", f"80:localhost:{PORT}", "serveo.net"]
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-R", f"80:localhost:{PORT}", "serveo.net"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            
            for line in process.stdout:
                if "Forwarding HTTP traffic from" in line:
                    match = re.search(r'https://[a-zA-Z0-9.-]+', line)
                    if match:
                        url = match.group(0)
                        print(f"✨ TÚNEL RESERVA (SERVEO): {url}")
                        global CURRENT_PUBLIC_URL
                        CURRENT_PUBLIC_URL = url
                        update_config_js(url)
                        break
            process.wait()
        except Exception as e:
            print(f"⚠️ Falha no túnel reserva Serveo: {e}")
        time.sleep(10)

def get_discovery_id():
    """Gera o ID único de descoberta baseado na SECRET_KEY."""
    secret = "dev_secret"
    try:
        if os.path.exists(".env"):
            with open(".env", "r", encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith("SECRET_KEY="):
                        val = line.split("=", 1)[1].strip()
                        if val: 
                            secret = val
                            print(f"   🔑 SECRET_KEY encontrada no .env: {val[:5]}... (len={len(val)})")
                            break
        else:
            print("   ⚠️ Arquivo .env não encontrado!")
    except Exception as e:
        # print(f"   ❌ Erro ao ler .env: {e}")
        pass
    
    final_id = hashlib.sha256(f"registroponto_{secret}".encode()).hexdigest()[:16]
    # print(f"   🆔 ID Calculado: {final_id} (usando '{secret[:3]}...')")
    return final_id


def start_robust_heartbeat():
    """Thread persistente única que sempre envia o link ATUAL."""
    def signal_heartbeat():
        user_id = get_discovery_id()
        topic = f"registroponto_{user_id}"
        registry_url = f"https://ntfy.sh/{topic}"
        dweet_url_base = f"https://dweet.io/dweet/for/ponto_carapina_{user_id}?api="
        
        print(f"📡 Heartbeat Persistente Ativo (ID: {user_id})")
        attempts = 0
        
        while True:
            url_to_send = CURRENT_PUBLIC_URL
            if url_to_send:
                attempts += 1
                try:
                    # Ntfy (Principal) - Use curl if available, or python requests if we had it (using curl for now as Windows usually has it)
                    subprocess.run(["curl", "-s", "-d", url_to_send, registry_url], capture_output=True, timeout=5)
                    # Dweet (Backup)
                    subprocess.run(["curl", "-s", dweet_url_base + url_to_send], capture_output=True, timeout=5)
                    
                    if attempts <= 3:
                        print(f"   💓 Sinal Enviado: {url_to_send}")
                except Exception as e:
                    pass
            
            # Intervalo dinâmico: Mais frequente no início ou após mudança de URL
            time.sleep(60 if attempts > 10 else 15)

    threading.Thread(target=signal_heartbeat, daemon=True).start()

def toggle_caffeinate(on=True):
    """Inibe o sistema de dormir."""
    global CAFFEINATE_PROCESS
    if not IS_WINDOWS:
        try:
            if on:
                if not CAFFEINATE_PROCESS or CAFFEINATE_PROCESS.poll() is not None:
                    print("☕ Ativando Cafeína (impedindo standby)...")
                    CAFFEINATE_PROCESS = subprocess.Popen(["caffeinate", "-ims"])
            else:
                if CAFFEINATE_PROCESS:
                    print("☕ Encerrando Cafeína...")
                    CAFFEINATE_PROCESS.terminate()
                    CAFFEINATE_PROCESS = None
        except Exception as e:
            print(f"⚠️ Erro ao controlar caffeinate: {e}")
    else:
        # On Windows, we can use a simpler method or just ignore it implies 'PowerToys Awake' or similar
        # For now we skip specific Windows implementation as python doesn't have built-in easy awake
        pass

def start_tunnel():
    log("🌍 Iniciando Cloudflare Tunnel...")
    
    # Check for cloudflared.exe on Windows
    binary = "cloudflared.exe" if IS_WINDOWS else "./cloudflared"
    
    if not os.path.exists(binary) and not os.path.exists("./" + binary):
        # Look in path? simplified check
        print(f"❌ ERRO: Binário '{binary}' não encontrado.")
        return

    # Limpa logs antigos para garantir que pegamos a URL nova
    if os.path.exists("cloudflared.log"):
        open("cloudflared.log", "w").close()

    tunnel_cmd = [binary if os.path.exists(binary) else "./"+binary, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--logfile", "cloudflared.log"]
    process = subprocess.Popen(tunnel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    
    print("⏳ Aguardando URL pública da Cloudflare...")
    cf_regex = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    
    start_t = time.time()
    url = None
    while time.time() - start_t < 60:
        line = process.stderr.readline()
        if not line:
            if process.poll() is not None: break
            time.sleep(0.1); continue
            
        match = cf_regex.search(line)
        if match:
            found_url = match.group(0)
            if "api.trycloudflare.com" not in found_url:
                url = found_url
                break
    
    if url:
        global CURRENT_PUBLIC_URL
        CURRENT_PUBLIC_URL = url
        print(f"\n✨ TÚNEL PRONTO (Cloudflare): {url} ✨")
        print("   ⚠️  Se der ERRO 1033 nesse link, aguarde abaixo o LINK FIXO ou PINGGY!\n")
        update_config_js(url)
        
        # Monitora a saúde do túnel
        while process.poll() is None:
            time.sleep(5)
    else:
        print("❌ Falha ao encontrar URL no Cloudflare (Firewall pode estar bloqueando).")
        process.kill()

def start_serveo_fallback():
    """Tenta abrir um túnel reserva via Serveo se o Cloudflare demorar."""
    print("🌍 [Reserva 1] Tentando Serveo (Link Fixo)...")
    try:
        # Tenta pegar o subdominio 'ponto-sre-carapina'
        # Adicionando 'user@' para evitar conflito com usuario do Windows
        cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-R", f"ponto-sre-carapina:80:localhost:{PORT}", "user@serveo.net"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        for line in process.stdout:
            if "Forwarding HTTP traffic from" in line:
                match = re.search(r'https://[a-zA-Z0-9.-]+', line)
                if match:
                    url = match.group(0)
                    if "ponto-sre-carapina" in url:
                        print(f"\n🔗 LINK FIXO (SERVEO): {url}  <-- USE ESSE!\n")
                    else:
                        print(f"✨ TÚNEL RESERVA (SERVEO): {url}")
                    
                    global CURRENT_PUBLIC_URL
                    CURRENT_PUBLIC_URL = url
                    update_config_js(url)
                    break
        process.wait()
    except Exception as e:
        print(f"⚠️ Falha no Serveo: {e}")

def start_pinggy_fallback():
    """Tenta abrir um túnel reserva via Pinggy (Porta 443 - Melhor para Firewall)."""
    print("🌍 [Reserva 2] Tentando Pinggy (Porta 443 - Ignorar pedido de senha)...")
    try:
        # Pinggy ssh command: ssh -p 443 -R0:localhost:5005 a.pinggy.io
        # Adicionando 'user@' para evitar que o Windows tente logar como dominio
        # Adicionando BatchMode=yes para falhar se pedir senha
        cmd = ["ssh", "-p", "443", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-R0:localhost:" + str(PORT), "user@a.pinggy.io"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        for line in process.stdout:
            # Pinggy outputs: http://...pinggy.link
            match = re.search(r'https://[a-zA-Z0-9.-]+\.pinggy\.link', line) or re.search(r'http://[a-zA-Z0-9.-]+\.pinggy\.link', line)
            if match:
                url = match.group(0).replace("http://", "https://") # Force https
                print(f"✨ TÚNEL RESERVA (PINGGY): {url}")
                global CURRENT_PUBLIC_URL
                CURRENT_PUBLIC_URL = url
                update_config_js(url)
                break
        process.wait()
    except Exception as e:
        print(f"⚠️ Falha no Pinggy: {e}")

def start_localhost_run_fallback():
    """Tenta abrir um túnel reserva via Localhost.run (Porta 22)."""
    print("🌍 [Reserva 3] Tentando Localhost.run...")
    try:
        cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", f"80:localhost:{PORT}", "nokey@localhost.run"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        for line in process.stdout:
            match = re.search(r'https://[a-zA-Z0-9.-]+\.lhr\.life', line) or re.search(r'https://[a-zA-Z0-9.-]+\.localhost\.run', line)
            if match:
                url = match.group(0)
                print(f"✨ TÚNEL RESERVA (LOCALHOST.RUN): {url}")
                global CURRENT_PUBLIC_URL
                CURRENT_PUBLIC_URL = url
                update_config_js(url)
                break
        process.wait()
    except Exception as e:
        print(f"⚠️ Falha no Localhost.run: {e}")

def kill_port(port):
    try:
        if IS_WINDOWS:
            # Windows way to kill port
            cmd = f"netstat -ano | findstr :{port}"
            try:
                output = subprocess.check_output(cmd, shell=True).decode()
                for line in output.splitlines():
                    parts = line.split()
                    if len(parts) > 4:
                        pid = parts[-1] 
                        if pid != "0": 
                            # print(f"🧹 Liberando porta {port} (PID {pid})...")
                            os.system(f"taskkill /F /PID {pid} >nul 2>&1")
            except: pass
        else:
            # Unix way
            cmd = f"lsof -ti:{port}"
            pids = subprocess.check_output(cmd, shell=True).decode().strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"🧹 Liberando porta {port} (PID {pid})...")
                    os.kill(int(pid), signal.SIGKILL)
    except: pass

if __name__ == "__main__":
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            print(f"⚠️ O sistema já está rodando (PID {old_pid}).")
            sys.exit(0)
        except SystemExit:
            raise
        except: 
            pass
    
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    toggle_caffeinate(True)
    kill_port(PORT)

    # Iniciar backend
    threading.Thread(target=run_backend, daemon=True).start()
    
    # [NOVO] Adiciona o IP local no script IMEDIATAMENTE antes dos túneis externos travarem no proxy
    update_config_js("")
    
    # Iniciar Heartbeat Persistente (uma única vez)
    start_robust_heartbeat()
    
    # Iniciar túneis de reserva em threads paralelas
    threading.Thread(target=start_serveo_fallback, daemon=True).start()
    threading.Thread(target=start_pinggy_fallback, daemon=True).start()
    
    # Iniciar monitoramento de saúde (Self-Healing)
    def monitor_health():
        print("🚑 Monitoramento de Saúde (Self-Healing) Ativo...")
        fail_count = 0
        while True:
            time.sleep(30)
            if CURRENT_PUBLIC_URL:
                try:
                    # Tenta acessar o endpoint de saúde
                    req = urllib.request.Request(
                        f"{CURRENT_PUBLIC_URL}/api/online", 
                        headers={'User-Agent': 'HealthCheck', 'Bypass-Tunnel-Reminder': 'true'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        if response.status == 200:
                            if fail_count > 0:
                                print(f"💚 Saúde recuperada após {fail_count} falhas.")
                            fail_count = 0
                        else:
                            print(f"⚠️ Health Check retornou status {response.status}")
                            fail_count += 1
                except Exception as e:
                    # print(f"⚠️ Falha no Health Check: {e}")
                    fail_count += 1
                
                # Se falhar 3 vezes seguidas (1m30s sem acesso), mata tudo
                if fail_count >= 3:
                     # On Windows we can just exit
                     print("💀 MÁXIMO DE FALHAS ATINGIDO. O SISTEMA SERÁ REINICIADO AGORA.")
                     os._exit(1)
            else:
                fail_count = 0
                
    threading.Thread(target=monitor_health, daemon=True).start()

    try:
        while True:
            start_tunnel()
            print("⚠️ Túnel principal caiu. Tentando reiniciar em 10s...")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Encerrando...")
        toggle_caffeinate(False)
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
        sys.exit(0)

