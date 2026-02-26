set -e

APP_DIR="/home/digest/newsletter-aggregator"
API_DIR="$APP_DIR/api"
SERVICE_NAME="digest"
VENV_DIR="$API_DIR/venv"

echo "🚀 Starting deployment..."
cd "$API_DIR"

echo "📥 Pulling latest code..."
git pull origin main

if [ ! -d "$VENV_DIR" ]; then
  echo "🐍 Creating virtualenv..."
  python3 -m venv "$VENV_DIR"
fi

echo "🐍 Activating virtualenv..."
source "$VENV_DIR/bin/activate"

if [ -f "requirements.txt" ]; then
  echo "📦 Installing dependencies..."
  cd "$APP_DIR"
  pip install -r requirements.txt
fi

echo "🔄 Restarting systemd service..."
sudo systemctl restart "$SERVICE_NAME"

echo "✅ Deployment complete!"