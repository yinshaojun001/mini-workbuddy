#!/usr/bin/env bash

set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "usage: $0 <git-sha>" >&2
  exit 2
fi

readonly GIT_SHA="$1"
readonly DEPLOY_ROOT="/opt/mini-workbuddy"
readonly RELEASE_DIR="$DEPLOY_ROOT/releases/$GIT_SHA"
readonly IMAGE="mini-workbuddy-backend:$GIT_SHA"

if [[ ! "$GIT_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid git SHA: $GIT_SHA" >&2
  exit 2
fi

if [[ ! -f "$RELEASE_DIR/backend-image.tar.gz" ]]; then
  echo "missing backend image archive" >&2
  exit 1
fi

gzip -dc "$RELEASE_DIR/backend-image.tar.gz" | docker load

set -a
source "$DEPLOY_ROOT/.env"
set +a

docker rm --force mini-workbuddy-backend >/dev/null 2>&1 || true
docker run \
  --detach \
  --name mini-workbuddy-backend \
  --restart unless-stopped \
  --memory 768m \
  --cpus 1.0 \
  --env "WORKSPACE_DIR=/data/workspace" \
  --env "FRONTEND_ORIGIN=$FRONTEND_ORIGIN" \
  --env "COMMAND_TIMEOUT_SECONDS=${COMMAND_TIMEOUT_SECONDS:-30}" \
  --volume "$DEPLOY_ROOT/workspace:/data/workspace" \
  --publish 127.0.0.1:8001:8001 \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  "$IMAGE" >/dev/null

for attempt in {1..30}; do
  if curl --silent --fail http://127.0.0.1:8001/api/health >/dev/null; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    docker logs --tail 100 mini-workbuddy-backend >&2 || true
    echo "backend health check failed" >&2
    exit 1
  fi
  sleep 2
done

ln -sfn "$RELEASE_DIR" "$DEPLOY_ROOT/current.next"
mv -Tf "$DEPLOY_ROOT/current.next" "$DEPLOY_ROOT/current"
rm -f "$RELEASE_DIR/backend-image.tar.gz"

echo "deployed $GIT_SHA"
