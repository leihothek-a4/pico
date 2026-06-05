#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example and fill in API_KEY, SECRET_KEY, GitHub OAuth values."
  exit 1
fi

git pull --ff-only

docker compose build --no-cache
docker compose up -d

echo "Deployed. Health check:"
curl -fsS -H "Authorization: Bearer $(grep '^API_KEY=' .env | cut -d= -f2-)" http://127.0.0.1:5000/api/health
echo
