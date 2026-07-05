#!/usr/bin/env bash
# Generate a self-signed TLS cert for local HTTPS (profile data in transit).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CERT_DIR="${ROOT}/certs"
mkdir -p "${CERT_DIR}"

openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout "${CERT_DIR}/key.pem" \
  -out "${CERT_DIR}/cert.pem" \
  -days 365 \
  -subj "/CN=localhost"

echo "Wrote ${CERT_DIR}/key.pem and ${CERT_DIR}/cert.pem"
echo "Start the API with TLS:"
echo "  uvicorn app.main:app --reload --ssl-keyfile=certs/key.pem --ssl-certfile=certs/cert.pem"
