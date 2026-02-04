import requests

def test_discovery():
    discovery_url = "https://ntfy.sh/ponto_carapina_3c667a98512a875a/raw?poll=1&since=all"
    try:
        res = requests.get(discovery_url)
        if res.status_code == 200:
            text = res.text
            lines = [l.strip() for l in text.split('\n') if l.strip().startswith('http')]
            if lines:
                last_url = lines[-1]
                if last_url and 'api.trycloudflare.com' not in last_url:
                    print(f"✅ Success! Found URL: {last_url}")
                    return
        print("❌ Failed to find valid URL")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_discovery()
