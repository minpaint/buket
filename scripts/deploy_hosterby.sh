#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/apps/buket}"
BACKEND_DIR="${BACKEND_DIR:-$APP_DIR/backend}"
BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-$BACKEND_DIR/.env}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "Backend directory not found: $BACKEND_DIR" >&2
  exit 1
fi

if [[ -f "$BACKEND_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$BACKEND_ENV_FILE"
  set +a
fi

BACKEND_VENV_DIR="${BACKEND_VENV_DIR:-$BACKEND_DIR/.venv}"
DJANGO_MANAGE="${DJANGO_MANAGE:-$BACKEND_DIR/manage.py}"

cd "$BACKEND_DIR"

if [[ ! -d "$BACKEND_VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$BACKEND_VENV_DIR"
fi

# shellcheck disable=SC1091
source "$BACKEND_VENV_DIR/bin/activate"

python -m pip install --upgrade pip
pip install -r requirements.txt
python "$DJANGO_MANAGE" check
python "$DJANGO_MANAGE" migrate --noinput
python "$DJANGO_MANAGE" collectstatic --noinput
deactivate

BOT_DIR="${BOT_DIR:-$APP_DIR/telegram-bot}"
BOT_VENV_DIR="${BOT_VENV_DIR:-$BOT_DIR/.venv}"

if [[ -d "$BOT_DIR" && -f "$BOT_DIR/requirements.txt" ]]; then
  cd "$BOT_DIR"

  if [[ ! -d "$BOT_VENV_DIR" ]]; then
    "$PYTHON_BIN" -m venv "$BOT_VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$BOT_VENV_DIR/bin/activate"
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  deactivate
fi

if [[ -n "${POST_DEPLOY_COMMAND:-}" ]]; then
  bash -lc "$POST_DEPLOY_COMMAND"
fi

if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
  curl --fail --silent --show-error "$HEALTHCHECK_URL" >/dev/null
fi

echo "Deploy completed successfully."
