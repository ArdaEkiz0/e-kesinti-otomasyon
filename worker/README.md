# SGK License API - Cloudflare Worker Deployment

## Kurulum Adimlari

### 1. Wrangler Kurulumu
```bash
npm install -g wrangler
wrangler login
```

### 2. D1 Veritabani Olusturma
```bash
wrangler d1 create sgk-license-db
```
Cikan `database_id`'yi `wrangler.toml` icine yazin.

### 3. Tablo Olusturma
```bash
wrangler d1 execute sgk-license-db --file=schema.sql
```

### 4. Worker Deploy
```bash
cd worker
wrangler deploy
```

### 5. Admin Sifresini Degistirme
`index.js` dosyasindaki `ADMIN_PASSWORD_HASH` degiskenini guncelleyin:
```javascript
// Yeni sifrenin SHA-256 hash'ini alin
node -e "console.log(require('crypto').createHash('sha256').update('yeniSifre').digest('hex'))"
```

### 6. Python Client Entegrasyonu
`api_client.py` dosyasindaki `WORKER_URL` degiskenini guncelleyin:
```python
WORKER_URL = "https://sgk-license-api.CIZGI.workers.dev"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/register` | POST | HWID + IP kaydet |
| `/api/admin/users` | GET | Kullanici listesi |
| `/api/admin/authorize` | POST | HWID yetkilendir |
| `/api/admin/deauthorize` | POST | Yetkiyi kaldir |
| `/api/admin/stats` | GET | Istatistikler |
| `/admin` | GET | Admin paneli |

## Admin Paneli
`https://sgk-license-api.CIZGI.workers.dev/admin` adresinden erisilebilir.
Varsayilan sifre: `password`

## Dosya Yapisi
```
worker/
  index.js         - Worker API kodu
  wrangler.toml    - Worker konfigurasyonu
  schema.sql       - D1 tablo yapisi
  README.md        - Bu dosya
api_client.py      - Python istemci
```
