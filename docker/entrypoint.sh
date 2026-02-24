#!/usr/bin/env bash
set -euo pipefail

echo "I'm alive and using this plane to say logs"
APP_USER="appuser"
PUID="${PUID:-568}"
PGID="${PGID:-568}"

if ! [[ "${PUID}" =~ ^[0-9]+$ && "${PGID}" =~ ^[0-9]+$ ]]; then
  echo "PUID and PGID must be numeric values" >&2
  exit 1
fi

umask 027

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Running as root, adjusting user and group IDs to PUID:${PUID} PGID:${PGID}"
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

  echo "Adjusted ${APP_USER} to UID:${PUID} GID:${PGID}"
  echo "Ensuring ownership of /var/app/user_data and /var/app/downloads"
  echo "Creating directories if they do not exist"
  mkdir -p /var/app/user_data /var/app/downloads
  echo "Setting ownership to ${PUID}:${PGID}"
  chown -R "${PUID}:${PGID}" /var/app/user_data
  chown -R "${PUID}:${PGID}" /var/app/downloads

  echo "Dropping privileges to ${APP_USER} and executing command: $*"
  exec gosu "${PUID}:${PGID}" "$@"
fi

exec "$@"
