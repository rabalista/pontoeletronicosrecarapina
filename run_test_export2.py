import urllib.request, json
try:
    # Need to simulate the login to get a token first
    req = urllib.request.Request('http://127.0.0.1:5005/api/login', data=b'{"matricula":"admin","password":"admin"}', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        token = data['token']
        mat = data['user']['matricula']
        
    req2 = urllib.request.Request(f'http://127.0.0.1:5005/api/admin/report?user_id={mat}', headers={'x-access-token': token})
    with urllib.request.urlopen(req2) as response2:
        print("Success! Status:", response2.status)
except urllib.error.HTTPError as e:
    ex = e.read().decode()
    print("HTTPError:", e.code)
    print("Details:", ex)
except Exception as e:
    print("Error:", e)
