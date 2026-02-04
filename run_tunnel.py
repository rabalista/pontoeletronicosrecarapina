import subprocess
import sys
import time

def log(msg):
    try:
        with open("tunnel_output.txt", "a") as f:
            f.write(msg + "\n")
    except:
        pass

log("STARTING TUNNEL...")

cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5005", "nokey@localhost.run"]
log(f"CMD: {cmd}")

try:
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    while True:
        line = process.stdout.readline()
        if not line:
            break
        log(f"OUT: {line.strip()}")
        if "lhr.life" in line:
            log(f"FOUND: {line.strip()}")
except Exception as e:
    log(f"ERROR: {e}")
