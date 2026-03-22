#!/usr/bin/env bash
set -euo pipefail

# -------------------------
# Configuration
# -------------------------
PROJECT_NAME="icseig/bank_analysis_backend"
BASE_COMPOSE="docker/docker-compose.yml"
DEV_COMPOSE="docker/docker-compose.dev.yml"
PROD_COMPOSE="docker/docker-compose.prod.yml"
DOCKERFILE_PATH="docker/Dockerfile"

LOG_DIR="./logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/run_$TIMESTAMP.log"
DATE_TAG=$(date +"%Y%m%d")

BACKUP_DIR="./backups"
ENV_FILE="./.env"
# -------------------------
# Colors
# -------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# -------------------------
# Prepare logging
# -------------------------
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "${BLUE}========== Docker Environment Launcher ==========${NC}"
echo -e "${BLUE}Log file:${NC} $LOG_FILE"
echo ""

# -------------------------
# Extract version safely
# -------------------------
if [[ ! -f pyproject.toml ]]; then
  echo -e "${RED}pyproject.toml not found!${NC}"
  exit 1
fi

VERSION=$(python3 -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")

if [[ -z "$VERSION" ]]; then
  echo -e "${RED}Could not extract version${NC}"
  exit 1
fi

IMAGE_TAG="${VERSION}-${DATE_TAG}"

echo -e "${GREEN}Detected version:${NC} $VERSION"
echo -e "${GREEN}Image tag:${NC} $IMAGE_TAG"
echo -e "${BLUE}Exporting tag to ENV variable...${NC}"
export IMAGE_TAG="${IMAGE_TAG}"
echo -e "${GREEN}IMAGE_TAG set to ${IMAGE_TAG}${NC}"
echo ""

# -------------------------
# Environment selection
# -------------------------
read -p "Enter environment (dev/prod) [dev]: " ENV
ENV=${ENV:-dev}

if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
  echo -e "${RED}Invalid environment.${NC}"
  exit 1
fi

# -------------------------
# Backup option
# -------------------------
read -p "Create offline backup before deploy? (y/N): " DO_BACKUP
DO_BACKUP=${DO_BACKUP:-N}

if [[ "${DO_BACKUP,,}" == "y" ]]; then
  BACKUP_STAMP="${BACKUP_DIR}/backup_${VERSION}_${TIMESTAMP}"
  mkdir -p "$BACKUP_STAMP"

  echo -e "${YELLOW}Creating offline backup in ${BACKUP_STAMP}...${NC}"

  # Back up compose files
  cp "$BASE_COMPOSE" "$BACKUP_STAMP/"
  if [[ "$ENV" == "dev" ]]; then
    cp "$DEV_COMPOSE" "$BACKUP_STAMP/"
  else
    cp "$PROD_COMPOSE" "$BACKUP_STAMP/"
  fi

  # Back up .env (exclude secrets from logs – only copy, never print)
  if [[ -f "$ENV_FILE" ]]; then
    cp "$ENV_FILE" "$BACKUP_STAMP/.env"
    echo -e "${GREEN}Backed up .env${NC}"
  fi

  # Back up pyproject.toml for version record
  cp pyproject.toml "$BACKUP_STAMP/"

  # Export named Docker volumes for the current stack
  echo -e "${YELLOW}Exporting Docker volumes (if any)...${NC}"
  if [[ "$ENV" == "dev" ]]; then
    COMPOSE_FILES_BACKUP="-f $BASE_COMPOSE -f $DEV_COMPOSE"
  else
    COMPOSE_FILES_BACKUP="-f $BASE_COMPOSE -f $PROD_COMPOSE"
  fi

  VOLUMES=$(docker compose --env-file "${ENV_FILE}" ${COMPOSE_FILES_BACKUP} \
    config --volumes 2>/dev/null || true)

  if [[ -n "$VOLUMES" ]]; then
    while IFS= read -r VOL; do
      VOL_FULL="${PROJECT_NAME/\//_}_${VOL}"
      TAR_OUT="${BACKUP_STAMP}/${VOL}.tar.gz"
      if docker volume inspect "$VOL_FULL" &>/dev/null; then
        echo -e "${BLUE}Backing up volume: ${VOL_FULL}${NC}"
        docker run --rm \
          -v "${VOL_FULL}:/data:ro" \
          -v "$(realpath "$BACKUP_STAMP"):/backup" \
          busybox sh -c "tar czf /backup/${VOL}.tar.gz -C /data ." \
          && echo -e "${GREEN}Volume ${VOL} backed up to ${TAR_OUT}${NC}" \
          || echo -e "${YELLOW}Could not back up volume ${VOL} (may be empty or unavailable)${NC}"
      fi
    done <<< "$VOLUMES"
  else
    echo -e "${YELLOW}No named volumes found for this stack.${NC}"
  fi

  echo -e "${GREEN}Backup complete: ${BACKUP_STAMP}${NC}"
fi

# -------------------------
# Compose stack selection
# -------------------------
if [[ "$ENV" == "dev" ]]; then
  COMPOSE_FILES="-f $BASE_COMPOSE -f $DEV_COMPOSE"
else
  COMPOSE_FILES="-f $BASE_COMPOSE -f $PROD_COMPOSE"
fi

# -------------------------
# Stop stack cleanly
# -------------------------
echo -e "${YELLOW}Stopping stack...${NC}"
docker compose --env-file ${ENV_FILE} $COMPOSE_FILES down -v

# -------------------------
# Build
# -------------------------
echo -e "${YELLOW}Building image...${NC}"
docker build \
  -f "$DOCKERFILE_PATH" \
  --pull \
  -t "${PROJECT_NAME}:${IMAGE_TAG}_${ENV}" \
  -t "${PROJECT_NAME}:latest" \
  .

echo -e "${GREEN}Build completed.${NC}"

# -------------------------
# Start stack
# -------------------------
if [[ "$ENV" == "dev" ]]; then
  echo -e "${BLUE}Starting DEVELOPMENT environment...${NC}"
else
  echo -e "${BLUE}Starting PRODUCTION environment...${NC}"
fi

docker compose --env-file ${ENV_FILE} $COMPOSE_FILES -p $PROJECT_NAME up -d -V --wait
echo -e "${GREEN}Containers running in background.${NC}"
echo -e "${BLUE}Use 'docker compose logs -f' to stream logs.${NC}"
echo -e "${GREEN}Done.${NC}"
