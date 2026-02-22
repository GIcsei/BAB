#!/usr/bin/env bash
set -euo pipefail

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
export IMAGE_TAG=$IMAGE_TAG
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
docker compose $COMPOSE_FILES down -v

# -------------------------
# Build
# -------------------------
echo -e "${YELLOW}Building image...${NC}"
docker build \
  -t ${PROJECT_NAME}:${IMAGE_TAG}_${ENV} \
  -t ${PROJECT_NAME}:latest \
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

docker compose $COMPOSE_FILES up -d
echo -e "${GREEN}Containers running in background.${NC}"
echo -e "${BLUE}Use 'docker compose logs -f' to stream logs.${NC}"
echo -e "${GREEN}Done.${NC}"