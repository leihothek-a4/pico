# Pico inventory app

Flask service on `128.140.115.158:5000` — RFID inventory + Pico online/offline status for n8n.

## How online/offline works

The Pico **checks in automatically** when it calls `GET /api/inventory` (every ~60s from firmware). No ICMP ping required.

| Status | Meaning |
|--------|---------|
| **online** | Inventory fetched within `PRESENCE_TIMEOUT_SECONDS` (default 150s) |
| **offline** | No check-in within the timeout |
| **unknown** | Never checked in |

Legacy ping-based updates via `POST /api/lockers/presence/batch` still work if you use them.

## Where to see status

| Where | URL | Auth |
|-------|-----|------|
| **Status dashboard** | http://128.140.115.158:5000/status | GitHub login |
| **Lockers overview** | http://128.140.115.158:5000/ | GitHub login |
| **API for n8n** | `GET /api/presence` or `GET /api/lockers/status` | `Authorization: Bearer {API_KEY}` |

Directus admin (`/admin/devices`) shows a **different** kind of status (TCP/WebSocket lock server).

## n8n workflow (pull status)

Run every 1–5 minutes on Hetzner (same host as n8n, or any host that can reach pico/app).

```
Schedule (cron)
    │
    ▼
HTTP GET /api/presence
    Authorization: Bearer {API_KEY}
    │
    ▼
Use JSON in later nodes
    summary.online / summary.offline
    lockers[].online
    lockers[].device_uid
    lockers[].locker_id
```

### HTTP Request node

- Method: `GET`
- URL: `http://127.0.0.1:5000/api/presence` (on Hetzner use localhost; from elsewhere use `http://128.140.115.158:5000/api/presence`)
- Header: `Authorization` = `Bearer VP5mwn1b` (your `API_KEY`)

### Example response

```json
{
  "presence_timeout_seconds": 150,
  "checked_at": "2026-06-17T20:00:00Z",
  "summary": {
    "online": 1,
    "offline": 0,
    "unknown": 0,
    "total": 1
  },
  "lockers": [
    {
      "id": 1,
      "device_uid": "92177dcd-daee-9f43-1e4d-6af70e077ac0",
      "locker_id": "5ff8f55157189d9107d39d3a285a84f8",
      "name": "leihothek-pico2w",
      "ip": "192.168.137.204",
      "status": "online",
      "online": true,
      "last_seen_at": "2026-06-17T19:58:12Z",
      "last_ping_at": null,
      "seconds_since_seen": 42
    }
  ]
}
```

### Example n8n Code node (filter online lockers)

```javascript
const lockers = $input.first().json.lockers ?? [];
return lockers
  .filter((locker) => locker.online)
  .map((locker) => ({ json: locker }));
```

### Optional: adjust timeout

Set `PRESENCE_TIMEOUT_SECONDS` on the server (default `150`). Should be ~2–3× the Pico inventory interval (firmware default 60s).

## Deploy

**Always use docker compose** — never `docker run -v leihothek-pico-data:/app/src`.

```bash
cd /root/pico/app
./deploy.sh
```

Only `/app/data` is persisted (database). Code comes from the image build.

Verify:

```bash
curl -H "Authorization: Bearer $API_KEY" http://127.0.0.1:5000/api/health
curl -H "Authorization: Bearer $API_KEY" http://127.0.0.1:5000/api/presence
```

## RFID UIDs

On the Lockers page, each part has inline name + RFID UID + Save.

## Debugging Pico HTTP 401

```bash
docker logs -f app-pico-app-1
```

Set `LEIHOTHEK_PICO_APP_API_KEY` in firmware to match server `API_KEY` (`VP5mwn1b`).
