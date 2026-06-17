# Pico inventory app

Flask service on `128.140.115.158:5000` — RFID inventory + Pi online/offline status (via n8n pings).

## Where to see Pi connectivity

| Where | URL | Auth |
|-------|-----|------|
| **Status dashboard** | http://128.140.115.158:5000/status | GitHub login |
| **Lockers overview** | http://128.140.115.158:5000/ | GitHub login (badges on each locker) |
| **API (n8n / scripts)** | `GET /api/lockers/status` | `Authorization: Bearer {API_KEY}` |

Status values: `online`, `offline`, `unknown` (not pinged yet).

Directus admin (`/admin/devices`) shows a **different** kind of status (TCP/WebSocket lock server). Ping status lives only in pico/app.

## n8n workflow

Run every 1–5 minutes on the same Hetzner host as n8n.

```
┌─────────────┐     GET /api/connected      ┌──────────────┐
│  Schedule   │ ──────────────────────────► │  pico/app    │
│  (cron)     │     Bearer API_KEY          │  :5000       │
└──────┬──────┘                             └──────┬───────┘
       │                                             │ {"ips":["192.168.x.x",...]}
       ▼                                             │
┌─────────────┐     ping each IP                    │
│  Loop IPs   │ ◄───────────────────────────────────┘
└──────┬──────┘
       │  (Execute Command: ping -c 1 -W 2 {ip})
       ▼
┌─────────────┐     POST /api/lockers/presence/batch
│  HTTP POST  │ ─────────────────────────────────────► pico/app
└─────────────┘     Bearer API_KEY
```

### Step 1 — Fetch IPs

**HTTP Request** node:
- Method: `GET`
- URL: `http://127.0.0.1:5000/api/connected` (same server as n8n — use localhost)
- Header: `Authorization` = `Bearer VP5mwn1b` (your `API_KEY`)

Response: `{"ips": ["192.168.137.204", ...]}`

### Step 2 — Ping each IP

**Code** or **Loop** over `{{ $json.ips }}`, then **Execute Command**:
```bash
ping -c 1 -W 2 {{ $json.ip }}
```
Exit code `0` = online.

### Step 3 — Report results (batch)

**HTTP Request** node:
- Method: `POST`
- URL: `http://127.0.0.1:5000/api/lockers/presence/batch`
- Header: `Authorization` = `Bearer VP5mwn1b`
- Body (JSON):
```json
{
  "results": [
    { "ip": "192.168.137.204", "online": true },
    { "ip": "10.0.0.99", "online": false }
  ]
}
```

Alternative single update: `POST /api/lockers/presence` with `{"ip": "...", "online": true}`.

### Step 4 — Read status (optional)

`GET http://127.0.0.1:5000/api/lockers/status` — same auth header.

## Deploy

**Always use docker compose** — never `docker run -v leihothek-pico-data:/app/src`.

Mounting a volume on `/app/src` replaces the code baked into the image with stale files from June 4. Rebuilds then have no effect (`/status` and other new routes disappear).

```bash
cd /root/pico/app
./deploy.sh
# or: docker compose build --no-cache && docker compose up -d
```

Only `/app/data` is persisted (database). Code comes from the image build.

Verify: `curl -H "Authorization: Bearer $API_KEY" http://127.0.0.1:5000/api/health`  
→ should include `"presence"` in features.

## RFID UIDs

On the Lockers page, each part has inline name + RFID UID + Save.

## Debugging Pico HTTP 401

**Server logs** (no firmware change needed):

```bash
docker logs -f app-pico-app-1
```

Failed auth lines look like: `API auth failed: GET /api/inventory from … — {'header_present': …}`

**401 JSON** (safe, no secrets) tells you what arrived:

```json
{
  "error": "Unauthorized",
  "hint": "Send header: Authorization: Bearer <API_KEY>",
  "auth": {
    "header_present": false,
    "header_length": 0,
    "starts_with_bearer": false,
    "bearer_value_length": 0,
    "expected_bearer_length": 8,
    "server_api_key_configured": true
  }
}
```

- `header_present: false` → Pico did not send `Authorization` (reflash firmware with auth support).
- `bearer_value_length` ≠ `expected_bearer_length` → wrong API key in `leihothek_config.h`.

**Pico serial** (after reflashing firmware with `LEIHOTHEK_HTTP_DEBUG 1`):

```
[leihothek] HTTP GET 128.140.115.158:5000/api/inventory?... (bearer_len=8, request_bytes=…)
[leihothek] server says: {"error":"Unauthorized","auth":{...}}
```

Set `LEIHOTHEK_HTTP_DEBUG` to `0` in `leihothek_config.h` once fixed.
