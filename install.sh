#!/usr/bin/env bash
# Встановлення бота на Ubuntu/Debian одною командою.
#
#   sudo bash install.sh                 # спитає токен
#   sudo bash install.sh 123456:AA...    # токен аргументом
#
# Після цього бот працює і піднімається сам після перезавантаження.
set -euo pipefail

APP_DIR=/opt/printer-bot
APP_USER=printerbot
SERVICE=telegram-printer-bot
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN="${1:-${BOT_TOKEN:-}}"

say() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
warn() { printf '\033[33m    %s\033[0m\n' "$1"; }

if [[ $EUID -ne 0 ]]; then
  echo "Потрібні права root:  sudo bash install.sh" >&2
  exit 1
fi

# ── Токен ───────────────────────────────────────────────────────────────────
if [[ -z "$TOKEN" && -f "$APP_DIR/.env" ]]; then
  TOKEN="$(grep -E '^BOT_TOKEN=' "$APP_DIR/.env" | cut -d= -f2- || true)"
fi
if [[ -z "$TOKEN" && -t 0 ]]; then
  echo
  echo "Токен бота від @BotFather (виглядає як 7123456789:AAH...)"
  read -r -p "BOT_TOKEN: " TOKEN
fi
if [[ ! "$TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
  echo "Токен не схожий на справжній: '$TOKEN'" >&2
  echo "Запустіть ще раз:  sudo bash install.sh <токен>" >&2
  exit 1
fi

# ── Пакети ──────────────────────────────────────────────────────────────────
say "Пакети"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip libusb-1.0-0 rsync curl netcat-openbsd

# ── Перевірка токена ────────────────────────────────────────────────────────
say "Перевірка токена"
BOT_NAME="$(curl -fsS --max-time 15 "https://api.telegram.org/bot$TOKEN/getMe" \
            | sed -n 's/.*"username":"\([^"]*\)".*/\1/p' || true)"
if [[ -n "$BOT_NAME" ]]; then
  echo "    бот @$BOT_NAME — токен робочий"
else
  warn "Telegram не підтвердив токен. Встановлюю далі, але бот може не піднятися."
fi

# ── Користувач ──────────────────────────────────────────────────────────────
say "Користувач $APP_USER"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/printerbot \
          --shell /usr/sbin/nologin "$APP_USER"
fi
for grp in lp dialout plugdev; do
  getent group "$grp" >/dev/null && usermod -aG "$grp" "$APP_USER" || true
done

# ── Код ─────────────────────────────────────────────────────────────────────
say "Код у $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.venv/' --exclude '__pycache__/' --exclude '.git/' \
  --exclude 'out/' --exclude '.env' --exclude 'state.json' \
  "$SRC_DIR"/ "$APP_DIR"/

say "Віртуальне оточення"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# ── Конфіг ──────────────────────────────────────────────────────────────────
say "Конфіг"
[[ -f "$APP_DIR/.env" ]] || cp "$APP_DIR/.env.example" "$APP_DIR/.env"
set_env() {
  local key="$1" value="$2"
  if grep -qE "^$key=" "$APP_DIR/.env"; then
    python3 - "$APP_DIR/.env" "$key" "$value" <<'PY'
import sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path, encoding="utf-8").read().splitlines()
out = [f"{key}={value}" if line.startswith(f"{key}=") else line for line in lines]
open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
  else
    printf '%s=%s\n' "$key" "$value" >> "$APP_DIR/.env"
  fi
}
set_env BOT_TOKEN "$TOKEN"
[[ -n "${ALLOWED_USERNAMES:-}" ]] && set_env ALLOWED_USERNAMES "$ALLOWED_USERNAMES"

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

# ── USB ─────────────────────────────────────────────────────────────────────
say "Правило udev для USB-принтера"
install -m 644 "$APP_DIR/systemd/99-citizen-printer.rules" \
        /etc/udev/rules.d/99-citizen-printer.rules
udevadm control --reload-rules >/dev/null 2>&1 || true
udevadm trigger >/dev/null 2>&1 || true

# ── Сервіс ──────────────────────────────────────────────────────────────────
say "Сервіс systemd"
install -m 644 "$APP_DIR/systemd/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable --quiet "$SERVICE"
systemctl restart "$SERVICE"

sleep 3
if systemctl is-active --quiet "$SERVICE"; then
  say "Бот працює"
else
  say "Бот не піднявся — останні рядки журналу:"
  journalctl -u "$SERVICE" -n 20 --no-pager || true
  exit 1
fi

# ── Принтер ─────────────────────────────────────────────────────────────────
PRINTER_HOST="$(grep -E '^PRINTER_HOST=' "$APP_DIR/.env" | cut -d= -f2- || true)"
PRINTER_PORT="$(grep -E '^PRINTER_PORT=' "$APP_DIR/.env" | cut -d= -f2- || true)"
if [[ -n "$PRINTER_HOST" ]]; then
  say "Звʼязок з принтером $PRINTER_HOST:${PRINTER_PORT:-9100}"
  if nc -z -w 4 "$PRINTER_HOST" "${PRINTER_PORT:-9100}" 2>/dev/null; then
    echo "    принтер відповідає"
  else
    warn "Принтер не відповідає. Бот працює, але друк не пройде."
    warn "Перевірте мережу або виправте PRINTER_HOST у $APP_DIR/.env"
  fi
fi

cat <<MSG

────────────────────────────────────────────────────────────
Готово. ${BOT_NAME:+Напишіть боту https://t.me/$BOT_NAME та натисніть /start}

Сервіс у автозапуску: після перезавантаження підніметься сам.

  systemctl status $SERVICE        стан
  journalctl -u $SERVICE -f        журнал
  sudo systemctl restart $SERVICE  перезапуск

Налаштування: $APP_DIR/.env
────────────────────────────────────────────────────────────
MSG
