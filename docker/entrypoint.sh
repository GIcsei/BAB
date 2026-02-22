#!/usr/bin/env bash
set -euo pipefail

APP_USER="appuser"
PUID="${PUID:-1200}"
PGID="${PGID:-1201}"

if ! [[ "${PUID}" =~ ^[0-9]+$ && "${PGID}" =~ ^[0-9]+$ ]]; then
  echo "PUID and PGID must be numeric values" >&2
  exit 1
fi

umask 027

if [[ "$(id -u)" -eq 0 ]]; then
  if getent group "${APP_USER}" >/dev/null 2>&1; then
    CURRENT_GID="$(getent group "${APP_USER}" | cut -d: -f3)"
    if [[ "${CURRENT_GID}" != "${PGID}" ]]; then
      groupmod -o -g "${PGID}" "${APP_USER}"
    fi
  fi

  CURRENT_UID="$(id -u "${APP_USER}")"
  if [[ "${CURRENT_UID}" != "${PUID}" ]]; then
    usermod -o -u "${PUID}" -g "${PGID}" "${APP_USER}"
  fi

  mkdir -p /var/app/user_data /var/app/downloads
  chown -R "${PUID}:${PGID}" /var/app

  exec gosu "${PUID}:${PGID}" "$@"
fi

exec "$@"
