"""
SGK E-Kesinti Otomasyon - API Client
Worker entegrasyonu icin HTTP istemcisi
"""

import hashlib
import json
import platform
import socket
import uuid
import urllib.request
import urllib.error
import ssl
import time
from typing import Optional, Dict, Any


# Worker URL - deploy edildikten sonra guncellenmeli
WORKER_URL = "https://sgk-api-v2.ardaekiz72.workers.dev"
ADMIN_PASSWORD = "***KALDIRILDI***"  # Admin paneli icin (sadece admin tarafindan kullanilir)

# Timeout
REQUEST_TIMEOUT = 10

# SSL context
SSL_CTX = ssl.create_default_context()


def get_hardware_id() -> str:
    """Hardware ID uret - sgk_app.py ile ayni format"""
    try:
        cpu_id = platform.processor() or "unknown"
        node = uuid.getnode()
        mac = ':'.join(('%012x' % node)[i:i+2] for i in range(0, 12, 2))
        raw = f"{cpu_id}-{mac}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
        parts = [digest[i:i+4] for i in range(0, 16, 4)]
        return f"SGK-{parts[0]}-{parts[1]}-{parts[2]}-{parts[3]}"
    except Exception:
        return "SGK-0000-0000-0000-0000"


def get_public_ip() -> str:
    """Public IP adresini al"""
    services = [
        "https://api.ipify.org?format=json",
        "https://httpbin.org/ip",
        "https://ifconfig.me/ip",
    ]
    for url in services:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SGK-App/1.0"})
            with urllib.request.urlopen(req, timeout=5, context=SSL_CTX) as resp:
                data = resp.read().decode()
                if "ipify" in url:
                    return json.loads(data).get("ip", "unknown")
                elif "httpbin" in url:
                    return json.loads(data).get("origin", "unknown")
                else:
                    return data.strip()
        except Exception:
            continue
    return "unknown"


def _make_request(endpoint: str, method: str = "GET",
                  data: Optional[Dict] = None,
                  params: Optional[Dict] = None) -> Dict[str, Any]:
    """Worker API'ye istek at"""
    url = f"{WORKER_URL}{endpoint}"

    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    headers = {"Content-Type": "application/json", "User-Agent": "SGK-App/1.0"}
    body = json.dumps(data).encode() if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": f"HTTP {e.code}", "authorized": False}
    except urllib.error.URLError:
        return {"error": "Connection failed", "authorized": False}
    except socket.timeout:
        return {"error": "Timeout", "authorized": False}
    except Exception as e:
        return {"error": str(e), "authorized": False}


def register_and_check(hwid: Optional[str] = None) -> Dict[str, Any]:
    """
    HWID ve IP kaydet, yetki durumunu kontrol et.
    Uygulama her acildiginda cagirilmali.

    Returns:
        {
            "authorized": bool,
            "message": str,
            "hwid": str,
            "first_seen": str,
            "last_seen": str
        }
    """
    if hwid is None:
        hwid = get_hardware_id()

    ip = get_public_ip()

    result = _make_request(
        endpoint="/api/register",
        method="POST",
        data={"hwid": hwid, "ip": ip}
    )

    return result


def check_authorization(hwid: Optional[str] = None) -> bool:
    """
    Yetki durumunu kontrol et (basit Boolean sonuc).
    """
    result = register_and_check(hwid)
    return result.get("authorized", False)


def admin_get_users(password: str) -> Dict[str, Any]:
    """Admin: tum kullanici listesini al"""
    return _make_request(
        endpoint="/api/admin/users",
        params={"password": password}
    )


def admin_authorize(password: str, hwid: str) -> Dict[str, Any]:
    """Admin: HWID yetkilendir"""
    return _make_request(
        endpoint="/api/admin/authorize",
        method="POST",
        data={"password": password, "hwid": hwid}
    )


def admin_deauthorize(password: str, hwid: str) -> Dict[str, Any]:
    """Admin: HWID yetkisini kaldir"""
    return _make_request(
        endpoint="/api/admin/deauthorize",
        method="POST",
        data={"password": password, "hwid": hwid}
    )


def admin_stats(password: str) -> Dict[str, Any]:
    """Admin: istatistikleri al"""
    return _make_request(
        endpoint="/api/admin/stats",
        params={"password": password}
    )


# --- Entegrasyon Ornegi ---
if __name__ == "__main__":
    print("=== SGK License Client Test ===\n")

    hwid = get_hardware_id()
    print(f"HWID: {hwid}")

    print("\n[1] Register & Check...")
    result = register_and_check(hwid)
    print(f"    Result: {json.dumps(result, indent=2)}")

    print(f"\n[2] Authorization: {'AKTIF' if result.get('authorized') else 'PASIF'}")

    print("\n[3] Admin Stats...")
    stats = admin_stats(ADMIN_PASSWORD)
    print(f"    Stats: {json.dumps(stats, indent=2)}")
