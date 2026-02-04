import os
import sys
import subprocess
import re
import time
import hashlib

def update_config_js(public_url):
    config_path = os.path.join("site_para_cloudflare", "config.js")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if public_url.endswith('/'):
            public_url = public_url[:-1]

        # Port 5005 is the default
        port = 5005

        import socket
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith("127."):
                try: local_ip = subprocess.check_output("ipconfig getifaddr en0", shell=True).decode().strip()
                except: 
                    try: local_ip = subprocess.check_output("ipconfig getifaddr en1", shell=True).decode().strip()
                    except: pass
            local_api = f"http://{local_ip}:{port}"
        except:
            local_api = None

        # Discovery announcement (same as run_cloudflare.py)
        announce_url(public_url)

        # Update candidates
        top_candidates = [public_url, local_api]
        unique_top = [c for c in top_candidates if c]

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
        
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ config.js atualizado com: {public_url}")
        sys.stdout.flush()
            
    except Exception as e:
        print(f"❌ Erro ao atualizar config.js: {e}")

def announce_url(public_url):
    try:
        secret = "dev_secret"
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("SECRET_KEY="):
                        secret = line.split("=")[1].strip()
        user_id = hashlib.sha256(f"ponto_carapina_{secret}".encode()).hexdigest()[:16]
        topic = f"ponto_carapina_{user_id}"
        registry_url = f"https://ntfy.sh/{topic}"
        cmd = ["curl", "-s", "-d", public_url, registry_url]
        subprocess.run(cmd, capture_output=True, text=True)
    except: pass

def start_tunnel():
    port = 5005
    print(f"🌍 Iniciando Túnel Público (via Serveo) para porta {port}...")
    sys.stdout.flush()
    
    # ssh -R 80:localhost:5005 serveo.net
    command = [
        "ssh", "-R", f"80:127.0.0.1:{port}", "serveo.net",
        "-o", "ServerAliveInterval=60",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null"
    ]
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print("⏳ Aguardando URL pública...")
    sys.stdout.flush()
    url = None
    
    # Serveo outputs the URL to stdout
    start_time = time.time()
    while time.time() - start_time < 30:
        line = process.stdout.readline()
        if not line:
            break
        if "Forwarding HTTP traffic from" in line:
            match = re.search(r'https://[a-zA-Z0-9.-]+', line)
            if match:
                url = match.group(0)
                break
    
    if url:
        print(f"\n✨ TÚNEL ONLINE: {url} ✨\n")
        update_config_js(url)
        print("Mantenha este processo rodando...")
        sys.stdout.flush()
        for line in process.stdout:
            pass
    else:
        print("❌ Falha ao obter URL ou timeout.")
        process.kill()

if __name__ == "__main__":
    start_tunnel()
