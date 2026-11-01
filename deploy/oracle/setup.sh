#!/usr/bin/env bash
# Run once on a fresh Ubuntu VM (Oracle Always Free): installs Docker, builds the Mieux API from GitHub and serves it over HTTPS.
# Usage: bash setup.sh            (the public IP is detected; the address will be https://<ip-with-dashes>.sslip.io)
set -euo pipefail
sudo apt-get update -y && sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sudo sh   # official Docker install (includes the compose plugin)
sudo systemctl enable --now docker
sudo mkdir -p /srv/mieux/data && sudo chown -R "$USER" /srv/mieux
cd /srv/mieux
[ -d repo ] || git clone https://github.com/Helmus101/mieux.git repo
git -C repo pull -q
IP=$(curl -s https://api.ipify.org)
HOST="$(echo "$IP" | tr . -).sslip.io"   # free hostname that points at the IP, so Caddy can get a real HTTPS certificate
cat > docker-compose.yml <<EOF
services:
  api:
    build: ./repo/backend
    restart: always
    volumes: ["/srv/mieux/data:/data"]
    environment: { ALLOWED_ORIGINS: "*" }
  caddy:
    image: caddy:2
    restart: always
    ports: ["80:80", "443:443"]
    volumes: ["/srv/mieux/Caddyfile:/etc/caddy/Caddyfile", "caddy_data:/data"]
volumes: { caddy_data: {} }
EOF
printf '%s {\n  reverse_proxy api:8010\n}\n' "$HOST" > Caddyfile
# Ubuntu images on Oracle block ports with iptables: open web ports
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT; sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo docker compose up -d --build
echo "API address: https://$HOST   (the data files must be in /srv/mieux/data, then: sudo docker compose restart api)"
