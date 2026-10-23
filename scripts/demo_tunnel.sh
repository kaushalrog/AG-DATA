#!/usr/bin/env bash
# Public real-data demo from this laptop: the app + read-only API over the current gold release,
# in Docker, exposed through a free Cloudflare quick tunnel (no account needed).
#
#   scripts/demo_tunnel.sh          # prints a https://<random>.trycloudflare.com link; Ctrl-C stops it
#
# The link works only while this script runs, and it changes on every start. No API key or raw data
# leaves the machine: the container holds only the published results (scripts/build_space.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${AGRI_DEMO_PORT:-7860}"
command -v cloudflared >/dev/null || { echo "install cloudflared first: brew install cloudflared" >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "start Docker Desktop first" >&2; exit 1; }

scripts/build_space.sh build/space
docker build -q -t agdata-space build/space >/dev/null
docker rm -f agdata-demo >/dev/null 2>&1 || true
# the tunnel's https origin serves the app itself, so cross-origin access is not needed
docker run -d --name agdata-demo --restart unless-stopped -p "127.0.0.1:$PORT:7860" agdata-space >/dev/null
for _ in $(seq 1 60); do curl -sf "http://127.0.0.1:$PORT/api/v1/ready" >/dev/null && break; sleep 1; done
curl -sf "http://127.0.0.1:$PORT/api/v1/ready" || { echo "server did not become ready" >&2; docker logs agdata-demo | tail -20; exit 1; }
echo
trap 'docker rm -f agdata-demo >/dev/null 2>&1; echo "stopped"' EXIT
echo "Starting the Cloudflare tunnel; the public link appears below (look for trycloudflare.com)."
cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT"
