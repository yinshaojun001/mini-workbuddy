#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT="${MINI_WORKBUDDY_BACKEND_PORT:-8001}"
FRONTEND_PORT="${MINI_WORKBUDDY_FRONTEND_PORT:-5173}"
BACKEND_PID=""
FRONTEND_PID=""

info() {
  printf '\033[1;32m[mini-workbuddy]\033[0m %s\n' "$1"
}

fail() {
  printf '\033[1;31m[mini-workbuddy]\033[0m %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "缺少命令：$1"
}

ensure_port_free() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "端口 $port 已被占用，请先停止对应服务。"
  fi
}

cleanup() {
  trap - INT TERM EXIT
  info "正在停止前后端服务..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill -TERM "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
  fi
  [[ -n "$FRONTEND_PID" ]] && wait "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "$BACKEND_PID" ]] && wait "$BACKEND_PID" 2>/dev/null || true
  info "服务已停止。"
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local pid="$3"
  local attempts=0

  until curl --noproxy '*' --silent --fail "$url" >/dev/null 2>&1; do
    if ! kill -0 "$pid" 2>/dev/null; then
      fail "$name 启动失败，请查看上方日志。"
    fi
    attempts=$((attempts + 1))
    if [[ "$attempts" -ge 60 ]]; then
      fail "$name 启动超时。"
    fi
    sleep 0.5
  done
}

require_command uv
require_command npm
require_command curl
ensure_port_free "$BACKEND_PORT"
ensure_port_free "$FRONTEND_PORT"

if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  info "正在安装后端依赖..."
  (cd "$BACKEND_DIR" && uv sync)
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  info "正在安装前端依赖..."
  (cd "$FRONTEND_DIR" && npm install)
fi

trap cleanup INT TERM EXIT

info "正在启动 FastAPI（http://127.0.0.1:${BACKEND_PORT}）..."
(
  cd "$BACKEND_DIR"
  exec uv run uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

info "正在启动 Vue（http://127.0.0.1:${FRONTEND_PORT}）..."
(
  cd "$FRONTEND_DIR"
  MINI_WORKBUDDY_API_TARGET="http://127.0.0.1:${BACKEND_PORT}" \
    exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

wait_for_url "后端" "http://127.0.0.1:${BACKEND_PORT}/api/health" "$BACKEND_PID"
wait_for_url "前端" "http://127.0.0.1:${FRONTEND_PORT}/" "$FRONTEND_PID"

printf '\n'
info "Mini-workbuddy 已启动"
printf '  前端：    http://127.0.0.1:%s\n' "$FRONTEND_PORT"
printf '  API 文档：http://127.0.0.1:%s/docs\n' "$BACKEND_PORT"
printf '  停止服务：Ctrl+C\n\n'

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done

fail "检测到服务意外退出，请查看上方日志。"
