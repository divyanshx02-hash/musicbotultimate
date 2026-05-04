#!/bin/bash
# MusicBot — One-command Ubuntu 22.04 VPS Setup
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  MusicBot — Full VPS Setup Script         ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root or with sudo${NC}"
  exit 1
fi

echo -e "${GREEN}[1/8] Updating system packages...${NC}"
apt-get update -qq && apt-get upgrade -y -qq

echo -e "${GREEN}[2/8] Installing system dependencies...${NC}"
apt-get install -y -qq \
  python3.11 \
  python3.11-pip \
  python3.11-venv \
  python3.11-dev \
  ffmpeg \
  git \
  curl \
  wget \
  redis-server \
  build-essential \
  libffi-dev \
  libssl-dev \
  pkg-config

echo -e "${GREEN}[3/8] Enabling and starting Redis...${NC}"
systemctl enable redis-server
systemctl start redis-server

echo -e "${GREEN}[4/8] Installing yt-dlp...${NC}"
wget -q -O /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
chmod +x /usr/local/bin/yt-dlp

echo -e "${GREEN}[5/8] Creating virtual environment...${NC}"
BOT_DIR="/opt/musicbot"
mkdir -p "$BOT_DIR"
cp -r . "$BOT_DIR/"
cd "$BOT_DIR"

python3.11 -m venv venv
source venv/bin/activate

echo -e "${GREEN}[6/8] Installing Python dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "${GREEN}[7/8] Setting up directories...${NC}"
mkdir -p downloads logs assets/fonts

# Download font
wget -q -O assets/fonts/NotoSans-Bold.ttf \
  "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Bold.ttf" || true

echo -e "${GREEN}[8/8] Creating systemd service...${NC}"
cat > /etc/systemd/system/musicbot.service << EOF
[Unit]
Description=MusicBot Telegram Music Bot
After=network.target redis.service

[Service]
Type=simple
User=root
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable musicbot

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Setup Complete!                          ${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Copy your .env file: cp .env.example $BOT_DIR/.env"
echo "  2. Edit the .env file: nano $BOT_DIR/.env"
echo "  3. Generate session strings: python string_session_generator.py"
echo "  4. Start the bot: systemctl start musicbot"
echo "  5. Check logs: journalctl -u musicbot -f"
echo ""
echo -e "${GREEN}Bot installed to: $BOT_DIR${NC}"
