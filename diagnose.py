import psutil
import requests
import os

with open("diagnostic_result.txt", "w") as f:
    f.write("--- DIAGNOSTIC START ---\n")
    
    # Check processes
    f.write("\n1. Running Processes:\n")
    found_app = False
    found_tunnel = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info['cmdline']
            if cmd:
                cmd_str = " ".join(cmd)
                if "app.py" in cmd_str:
                    f.write(f"APP: {cmd_str}\n")
                    found_app = True
                if "serveo" in cmd_str or "ssh" in cmd_str:
                    f.write(f"SSH: {cmd_str}\n")
                    found_tunnel = True
        except:
            pass
            
    if not found_app: f.write("❌ app.py NOT found.\n")
    if not found_tunnel: f.write("❌ SSH Tunnel NOT found.\n")

    # Check local port 5005
    f.write("\n2. Port 5005 Check:\n")
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 5005))
    if result == 0:
        f.write("✅ Port 5005 is OPEN (Backend Alive)\n")
    else:
        f.write(f"❌ Port 5005 is CLOSED (Error: {result})\n")
    sock.close()

    # Check Tunnel
    f.write("\n3. Tunnel Connectivity:\n")
    try:
        r = requests.get("https://ponto-sre-carapina.serveo.net/api/health", timeout=5)
        f.write(f"Status: {r.status_code}\n")
        f.write(f"Content: {r.text[:100]}\n")
    except Exception as e:
        f.write(f"❌ Tunnel Connect Error: {e}\n")

    f.write("\n--- DIAGNOSTIC END ---\n")
