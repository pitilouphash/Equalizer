#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ce script doit être exécuté en tant que root (sudo)." >&2
  exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
APP_DIR="${APP_DIR:-/opt/equalizer}"

echo "Installation d'Equalizer dans ${APP_DIR}" 

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  rsync \
  libasound2 \
  libasound2-dev \
  portaudio19-dev \
  ffmpeg \
  libfftw3-3 \
  libfftw3-dev

mkdir -p "${APP_DIR}"

if [[ "${REPO_ROOT}" != "${APP_DIR}" ]]; then
  echo "Copie des fichiers de l'application..."
  rsync -a --delete --exclude '.git' "${REPO_ROOT}/" "${APP_DIR}/"
fi

cd "${APP_DIR}"

python3 -m venv venv
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r requirements.txt

mkdir -p /etc/equalizer

if [[ ! -f /etc/equalizer/equalizer.env ]]; then
  cat <<'ENVFILE' >/etc/equalizer/equalizer.env
# Renseignez la clé API utilisée par l'application
EQUALIZER_API_KEY=REMPLACER_CETTE_VALEUR
ENVFILE
  echo "Fichier /etc/equalizer/equalizer.env créé. Pensez à renseigner la clé API."
fi

install -D -m 0644 "${APP_DIR}/systemd/equalizer.service" /etc/systemd/system/equalizer.service
install -D -m 0644 "${APP_DIR}/config/logrotate/equalizer" /etc/logrotate.d/equalizer

systemctl daemon-reload
systemctl enable equalizer.service

mkdir -p /var/log/equalizer
touch /var/log/equalizer/equalizer.log
chown root:root /var/log/equalizer/equalizer.log
chmod 640 /var/log/equalizer/equalizer.log

echo "Installation terminée. Démarrez le service avec : systemctl start equalizer.service"
