# Headwind MDM Maps Lite

Free, community-built GPS tracking for **Headwind MDM Community Edition**.  
Shows current device locations and simple history trails, optimized for low admin overhead.

[![Status](https://img.shields.io/badge/Project-Active-brightgreen)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#)
[![License](https://img.shields.io/badge/License-Apache--2.0-lightgrey)](LICENSE)

## ✨ What it does
- Device location map + basic history trails
- Works alongside Headwind MDM CE (unofficial)
- Lightweight Flask server + static web UI
- Optional login to see your fleet
- Low footprint; easy to host on a tiny VPS

> This is **not** an official Headwind product. For advanced reporting/SLAs, consider Headwind MDM Enterprise.

## 📦 Requirements
- Linux host (Ubuntu 22.04+ recommended)
- Python **3.10+** and PostgreSQL **13+** (or compatible)
- Access to your Headwind MDM database/API (read access for device list, or push locations via agent)
- Public URL if you want remote access (Nginx reverse proxy suggested)

## 🚀 Quick start (dev)
```bash
git clone https://github.com/nextech-systems/headwind-mdm-maps-lite.git
cd headwind-mdm-maps-lite
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run the app
python server-real.py
# open: http://localhost:5003
⚙️ Configuration (.env)
env
Copy code
# Flask
FLASK_SECRET=change-me-32-bytes-random
BIND_HOST=0.0.0.0
BIND_PORT=5003
DEBUG=false

# Database (PostgreSQL)
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=headwind
DB_USER=headwind
DB_PASSWORD=supersecret

# Auth (optional)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me

# Map defaults
DEFAULT_LAT=18.0153
DEFAULT_LON=-76.8099
DEFAULT_ZOOM=12
🗺️ Using with Headwind MDM
Push model: Deploy/update your device agent to POST GPS updates to this server’s /api/locations endpoint (see API below).

Pull model: Alternatively, schedule a job to pull device data from Headwind’s DB (read-only connection string).

🔌 REST API (minimal)
POST /api/locations — upsert a device location
Body (JSON):

json
Copy code
{ "imei": "...", "lat": 18.02, "lon": -76.80, "accuracy": 12, "battery": 87, "ts": "2025-10-08T14:03:00Z" }
GET /api/locations?since=... — recent points

GET /api/devices — device list with last fix

Auth: if ADMIN_EMAIL/ADMIN_PASSWORD set, login is required; otherwise endpoints are open.

Endpoints above reflect the intended minimalist surface. Adjust to exactly match the current code as needed.

🧪 Smoke test
Start server → open / → see map

Post a fake location → point appears on map

Toggle auth envs → login required

🛡️ Production hardening
Run via systemd, behind Nginx with HTTPS

Use strong FLASK_SECRET, rotate regularly

Create a DB user with least-privilege

Optional: enable rate limits / fail2ban

📄 License
Apache-2.0

makefile
Copy code

---

### `.env.sample`
```env
FLASK_SECRET=change-me
BIND_HOST=0.0.0.0
BIND_PORT=5003
DEBUG=false

DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=headwind
DB_USER=headwind
DB_PASSWORD=supersecret

ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me

DEFAULT_LAT=18.0153
DEFAULT_LON=-76.8099
DEFAULT_ZOOM=12
INSTALL.md (admins + installers)
markdown
Copy code
# Install — Headwind MDM Maps Lite (Ubuntu 22.04)

## 1) OS deps
```bash
sudo apt update
sudo apt install -y python3.10-venv python3-pip postgresql nginx
2) App setup
bash
Copy code
sudo useradd -r -s /usr/sbin/nologin mapslite
sudo mkdir -p /opt/mapslite && sudo chown mapslite: /opt/mapslite
sudo -u mapslite git clone https://github.com/nextech-systems/headwind-mdm-maps-lite.git /opt/mapslite
cd /opt/mapslite
sudo -u mapslite python3 -m venv .venv
sudo -u mapslite bash -lc ". ./.venv/bin/activate && pip install -r requirements.txt"
sudo -u mapslite cp .env.sample .env && sudo -u mapslite nano .env
3) Database (PostgreSQL)
sql
Copy code
CREATE USER mapslite WITH ENCRYPTED PASSWORD 'change-me';
CREATE DATABASE mapslite OWNER mapslite;
-- optional: grant read-only access to Headwind DB if you pull device metadata
4) systemd service
Create /etc/systemd/system/mapslite.service:

ini
Copy code
[Unit]
Description=Headwind MDM Maps Lite
After=network.target

[Service]
User=mapslite
Group=mapslite
WorkingDirectory=/opt/mapslite
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/mapslite/.venv/bin/python server-real.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
Enable and start:

bash
Copy code
sudo systemctl daemon-reload
sudo systemctl enable --now mapslite
5) Nginx reverse proxy (+ HTTPS)
Create /etc/nginx/sites-available/mapslite:

nginx
Copy code
server {
  listen 80;
  server_name maps.example.com;

  location / {
    proxy_pass http://127.0.0.1:5003;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
Then:

bash
Copy code
sudo ln -s /etc/nginx/sites-available/mapslite /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# (optional) sudo certbot --nginx -d maps.example.com
6) Headwind integration
Push model: Configure the device app/agent to POST JSON to https://maps.example.com/api/locations.

Pull model: (Optional) cron job that reads Headwind DB and updates this app’s tables.

7) Verify
Open https://maps.example.com → map loads

Post a test location → dot appears

yaml
Copy code

---

### `docker-compose.yml` (optional)
```yaml
version: "3.9"
services:
  app:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
    env_file:
      - .env
    command: bash -lc "pip install -r requirements.txt && python server-real.py"
    ports:
      - "5003:5003"
    restart: unless-stopped
SECURITY.md
markdown
Copy code
# Security Policy

- Report vulnerabilities via GitHub Issues or email (TBD).
- Please avoid posting PoCs with live secrets or device identifiers.
- Rotate `FLASK_SECRET` and database passwords regularly.
.github/workflows/ci.yml
yaml
Copy code
name: CI
on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python -m compileall 
