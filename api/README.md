# Deployment & Configuration

## 1️⃣ Directory structure

```text
newsletter-aggregator/
├── api/                   # Python API
│   ├── server.py
│   ├── security.py
│   ├── requirements.txt
│   └── venv/              # Python virtual environment
├── client/                # Frontend (React)
├── .env                   # Environment variables for API
├── deploy.sh              # Deployment script
└── systemd/
    └── digest.service     # systemd service for API
```

## 2️⃣ Python API Deployment

### a) Setup virtual environment

```bash
cd /home/digest/newsletter-aggregator/api
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### b) systemd service (`digest.service`)

```ini
[Unit]
Description=Newsletter Aggregator API
After=network.target

[Service]
User=digest
Group=digest
WorkingDirectory=/home/digest/newsletter-aggregator/api
ExecStart=/home/digest/newsletter-aggregator/api/venv/bin/gunicorn server:app -b 0.0.0.0:8000 --access-logfile - --error-logfile -
EnvironmentFile=/home/digest/newsletter-aggregator/.env
Restart=always

[Install]
WantedBy=multi-user.target
```

### c) Start / enable the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable digest
sudo systemctl start digest
sudo systemctl status digest
```

## 3️⃣ Frontend Client Deployment

```bash
cd client
npm install
npm run build
```

- Serve the build directory with Nginx or another web server.

## 4️⃣ Environment Variables

Create `.env` in the project root:

```text
API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:pass@localhost/db
OTHER_SETTING=value
```

## 5️⃣ Nginx Configuration

```nginx
server {
    server_name api.serifdigest.com;

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/api.serifdigest.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.serifdigest.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    access_log /var/log/nginx/api.serifdigest.access.log;
    error_log  /var/log/nginx/api.serifdigest.error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}

server {
    listen 80;
    server_name api.serifdigest.com;
    return 301 https://$host$request_uri;
}
```

## 6️⃣ Logging

```bash
journalctl -u digest -f
```

```bash
tail -f /var/log/nginx/api.serifdigest.access.log
tail -f /var/log/nginx/api.serifdigest.error.log
```

Optional Flask request logging:

```python
@app.before_request
def log_request_info():
    app.logger.info(f"{request.method} {request.path} from {request.remote_addr}")
```

## 7️⃣ Deployment Script (`deploy.sh`)

```bash
#!/usr/bin/env bash
set -e

APP_DIR="/home/digest/newsletter-aggregator/api"
SERVICE_NAME="digest"
VENV_DIR="$APP_DIR/venv"

cd "$APP_DIR"

git pull origin main

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install -r requirements.txt

sudo systemctl restart "$SERVICE_NAME"
```

## 8️⃣ Network / API Notes

- API listens on **127.0.0.1:8000**
- Nginx proxies **api.serifdigest.com** → Gunicorn
- Frontend calls `https://api.serifdigest.com/`
- Firewall must allow port 443
- Check Nginx + Gunicorn logs for errors or failed requests
