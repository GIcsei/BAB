#!/usr/bin/env bash

set -e

# -------------------------
# Configuration
# -------------------------
PROJECT_NAME="bank_analysis_backend"
BASE_COMPOSE="docker-compose.yml"
DEV_COMPOSE="docker-compose.dev.yml"
PROD_COMPOSE="docker-compose.prod.yml"
LOG_DIR="./logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/run_$TIMESTAMP.log"
DATE_TAG=$(date +"%Y%m%d")

# -------------------------
# Colors
# -------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -------------------------
# Prepare logging
# -------------------------
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "${BLUE}========== Docker Environment Launcher ==========${NC}"
echo -e "${BLUE}Log file:${NC} $LOG_FILE"
echo ""

# -------------------------
# Get version from pyproject.toml
# -------------------------
if [[ ! -f pyproject.toml ]]; then
  echo -e "${RED}pyproject.toml not found!${NC}"
  exit 1
fi

VERSION=$(grep '^version' pyproject.toml | head -n1 | cut -d '"' -f2)

if [[ -z "$VERSION" ]]; then
  echo -e "${RED}Could not extract version from pyproject.toml${NC}"
  exit 1
fi

IMAGE_TAG="${VERSION}-${DATE_TAG}"

echo -e "${GREEN}Detected version:${NC} $VERSION"
echo -e "${GREEN}Image tag:${NC} $IMAGE_TAG"
echo ""

# -------------------------
# User input
# -------------------------
read -p "Enter environment (dev/prod): " ENV

if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
  echo -e "${RED}Invalid environment. Use 'dev' or 'prod'.${NC}"
  exit 1
fi

# -------------------------
# Stop previous containers
# -------------------------
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker compose -f "$BASE_COMPOSE" down || true

# -------------------------
# Build image with tag
# -------------------------
echo -e "${YELLOW}Building image...${NC}"
docker build \
  -t ${PROJECT_NAME}:${IMAGE_TAG} \
  -t ${PROJECT_NAME}:latest \
  .

echo -e "${GREEN}Build completed.${NC}"
echo ""

# -------------------------
# Run environment
# -------------------------
if [[ "$ENV" == "dev" ]]; then
  echo -e "${BLUE}Starting DEVELOPMENT environment...${NC}"
  docker compose \
    -f "$BASE_COMPOSE" \
    -f "$DEV_COMPOSE" \
    up

else
  echo -e "${BLUE}Starting PRODUCTION environment...${NC}"
  docker compose \
    -f "$BASE_COMPOSE" \
    -f "$PROD_COMPOSE" \
    up -d
fi

echo -e "${GREEN}Done.${NC}"