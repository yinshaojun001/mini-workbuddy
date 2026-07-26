#!/usr/bin/env bash

set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "usage: $0 <git-sha>" >&2
  exit 2
fi

readonly GIT_SHA="$1"
readonly DEPLOY_ROOT="/opt/mini-workbuddy"
readonly RELEASE_DIR="$DEPLOY_ROOT/releases/$GIT_SHA"
readonly BACKEND_IMAGE="mini-workbuddy-backend:$GIT_SHA"
readonly ENGINE_IMAGE="fortune-bazi-engine:$GIT_SHA"
readonly NETWORK="mini-workbuddy-internal"

if [[ ! "$GIT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid git SHA: $GIT_SHA" >&2
  exit 2
fi

for required in backend-image.tar.gz fortune-engine-image.tar.gz frontend/index.html fortune-frontend/index.html; do
  if [[ ! -e "$RELEASE_DIR/$required" ]]; then
    echo "missing release artifact: $required" >&2
    exit 1
  fi
done

set -a
source "$DEPLOY_ROOT/.env"
set +a
: "${FRONTEND_ORIGIN:?FRONTEND_ORIGIN must be set in $DEPLOY_ROOT/.env}"
: "${FORTUNE_ORIGIN:?FORTUNE_ORIGIN must be set in $DEPLOY_ROOT/.env}"
: "${PUBLIC_SESSION_SECRET:?PUBLIC_SESSION_SECRET must be set in $DEPLOY_ROOT/.env}"
: "${PUBLIC_IP_HASH_SECRET:?PUBLIC_IP_HASH_SECRET must be set in $DEPLOY_ROOT/.env}"

readonly PREVIOUS_RELEASE="$(readlink -f "$DEPLOY_ROOT/current" 2>/dev/null || true)"
readonly PREVIOUS_BACKEND_IMAGE="$(docker inspect --format '{{.Config.Image}}' mini-workbuddy-backend 2>/dev/null || true)"
readonly PREVIOUS_ENGINE_IMAGE="$(docker inspect --format '{{.Config.Image}}' fortune-bazi-engine 2>/dev/null || true)"

start_engine() {
  local image="$1"
  docker rm --force fortune-bazi-engine >/dev/null 2>&1 || true
  docker run \
    --detach \
    --name fortune-bazi-engine \
    --restart unless-stopped \
    --network "$NETWORK" \
    --memory 256m \
    --cpus 0.75 \
    --log-driver json-file \
    --log-opt max-size=10m \
    --log-opt max-file=3 \
    "$image" >/dev/null
}

start_backend() {
  local image="$1"
  docker rm --force mini-workbuddy-backend >/dev/null 2>&1 || true
  docker run \
    --detach \
    --name mini-workbuddy-backend \
    --restart unless-stopped \
    --network "$NETWORK" \
    --memory 768m \
    --cpus 1.0 \
    --env "WORKSPACE_DIR=/data/workspace" \
    --env "FRONTEND_ORIGIN=$FRONTEND_ORIGIN" \
    --env "FORTUNE_ORIGIN=$FORTUNE_ORIGIN" \
    --env "PUBLIC_SESSION_SECRET=$PUBLIC_SESSION_SECRET" \
    --env "PUBLIC_IP_HASH_SECRET=$PUBLIC_IP_HASH_SECRET" \
    --env "BAZI_ENGINE_URL=http://fortune-bazi-engine:8080" \
    --env "COMMAND_TIMEOUT_SECONDS=${COMMAND_TIMEOUT_SECONDS:-30}" \
    --volume "$DEPLOY_ROOT/workspace:/data/workspace" \
    --publish 127.0.0.1:8001:8001 \
    --log-driver json-file \
    --log-opt max-size=10m \
    --log-opt max-file=3 \
    "$image" >/dev/null
}

rollback() {
  local exit_code=$?
  trap - ERR
  set +e
  echo "deployment failed; restoring previous containers and release" >&2
  docker rm --force mini-workbuddy-backend fortune-bazi-engine >/dev/null 2>&1
  if [[ -n "$PREVIOUS_ENGINE_IMAGE" ]]; then start_engine "$PREVIOUS_ENGINE_IMAGE"; fi
  if [[ -n "$PREVIOUS_BACKEND_IMAGE" ]]; then start_backend "$PREVIOUS_BACKEND_IMAGE"; fi
  if [[ -n "$PREVIOUS_RELEASE" && -d "$PREVIOUS_RELEASE" ]]; then
    ln -sfn "$PREVIOUS_RELEASE" "$DEPLOY_ROOT/current.next"
    mv -Tf "$DEPLOY_ROOT/current.next" "$DEPLOY_ROOT/current"
  fi
  exit "$exit_code"
}
trap rollback ERR

gzip -dc "$RELEASE_DIR/backend-image.tar.gz" | docker load
gzip -dc "$RELEASE_DIR/fortune-engine-image.tar.gz" | docker load
docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK" >/dev/null

start_engine "$ENGINE_IMAGE"
for attempt in {1..30}; do
  if docker exec fortune-bazi-engine node -e "fetch('http://127.0.0.1:8080/health').then(r=>{if(!r.ok)process.exit(1)})"; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    docker logs --tail 100 fortune-bazi-engine >&2 || true
    echo "fortune engine health check failed" >&2
    false
  fi
  sleep 2
done

start_backend "$BACKEND_IMAGE"
for attempt in {1..30}; do
  if curl --silent --fail http://127.0.0.1:8001/api/health >/dev/null; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    docker logs --tail 100 mini-workbuddy-backend >&2 || true
    echo "backend health check failed" >&2
    false
  fi
  sleep 2
done

ln -sfn "$RELEASE_DIR" "$DEPLOY_ROOT/current.next"
mv -Tf "$DEPLOY_ROOT/current.next" "$DEPLOY_ROOT/current"
rm -f "$RELEASE_DIR/backend-image.tar.gz" "$RELEASE_DIR/fortune-engine-image.tar.gz"
trap - ERR

echo "deployed $GIT_SHA"
