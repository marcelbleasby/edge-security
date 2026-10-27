#!/bin/sh
# Gera tráfego benigno e marcadores determinísticos dentro da rede de laboratório.
# Usa apenas o busybox do Alpine; a rede lab não tem saída para a internet.
set -u
DNS_SERVER="${DNS_SERVER:-172.30.0.53}"
WEB_HOST="${WEB_HOST:-172.30.0.80}"
INTERVAL="${INTERVAL:-20}"

echo "lab-client $(hostname): dns=$DNS_SERVER web=$WEB_HOST interval=${INTERVAL}s"
while true; do
  nslookup example.org "$DNS_SERVER" >/dev/null 2>&1
  nslookup lab-alerta.test "$DNS_SERVER" >/dev/null 2>&1
  wget -q -T 3 -O /dev/null "http://$WEB_HOST/" 2>/dev/null
  wget -q -T 3 -O /dev/null "http://$WEB_HOST/lab-marker" 2>/dev/null
  if [ "${SCAN:-0}" = "1" ]; then
    for port in 21 23 3389; do
      wget -q -T 1 -O /dev/null "http://$WEB_HOST:$port/" 2>/dev/null
    done
  fi
  sleep "$INTERVAL"
done
