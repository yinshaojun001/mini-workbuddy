#!/usr/bin/env bash

set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "usage: $0 <public-base-url>" >&2
  exit 2
fi

readonly PUBLIC_BASE_URL="${1%/}"
readonly RESULT_DIR="$(mktemp -d)"
trap 'rm -rf "$RESULT_DIR"' EXIT

request() {
  local slug="$1"
  curl \
    --silent \
    --show-error \
    --retry 5 \
    --retry-delay 2 \
    --retry-all-errors \
    --max-time 30 \
    --output "$RESULT_DIR/$slug.json" \
    --write-out '%{http_code}' \
    "$PUBLIC_BASE_URL/api/public/apps/$slug"
}

fortune_status="$(request fortune)"
if [[ "$fortune_status" != "200" ]] || ! jq -e '.slug == "fortune"' "$RESULT_DIR/fortune.json" >/dev/null; then
  echo "fortune public route failed: HTTP $fortune_status" >&2
  sed -n '1,20p' "$RESULT_DIR/fortune.json" >&2
  exit 1
fi

dream_status="$(request dream)"
case "$dream_status" in
  200)
    jq -e '.slug == "dream"' "$RESULT_DIR/dream.json" >/dev/null || {
      echo "dream public route returned invalid metadata" >&2
      exit 1
    }
    ;;
  404)
    jq -e '.error.code == "APP_NOT_FOUND"' "$RESULT_DIR/dream.json" >/dev/null || {
      echo "dream route did not reach the application runtime" >&2
      sed -n '1,20p' "$RESULT_DIR/dream.json" >&2
      exit 1
    }
    ;;
  *)
    echo "dream public route failed: HTTP $dream_status" >&2
    sed -n '1,20p' "$RESULT_DIR/dream.json" >&2
    exit 1
    ;;
esac

echo "public routes verified: fortune=200 dream=$dream_status"
