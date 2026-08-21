import json
import urllib.request
import urllib.error
import sys

API_TOKEN = "***KALDIRILDI***"
ACCOUNT_ID = "375e7ccb3889662f86cb4bc4097cf67f"
DATABASE_ID = "37f99095-2543-489f-b1a1-62f6bf7514af"
SCRIPT_NAME = "sgk-license-api"

with open("worker.mjs", "r", encoding="utf-8") as f:
    worker_code = f.read()

boundary = "----FormBoundary" + str(id(worker_code))
metadata = json.dumps({
    "main_module": "worker.mjs",
    "compatibility_date": "2024-01-01",
    "bindings": [
        {
            "type": "d1",
            "name": "DB",
            "id": DATABASE_ID
        }
    ]
})

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="metadata"\r\n'
    f"Content-Type: application/json\r\n\r\n"
    f"{metadata}\r\n"
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="worker.mjs"; filename="worker.mjs"\r\n'
    f"Content-Type: application/javascript+module\r\n\r\n"
    f"{worker_code}\r\n"
    f"--{boundary}--"
)

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/workers/scripts/{SCRIPT_NAME}"
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": f"multipart/form-data; boundary={boundary}"
}

req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="PUT")

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
        if result.get("success"):
            print(f"SUCCESS! Worker deployed: https://{SCRIPT_NAME}.<your-subdomain>.workers.dev")
            print(f"Admin Panel: https://{SCRIPT_NAME}.<your-subdomain>.workers.dev/admin")
        else:
            print(f"ERROR: {result}")
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print(f"HTTP ERROR {e.code}: {error_body}")
except Exception as e:
    print(f"ERROR: {e}")
