#!/usr/bin/env bash
# Встановлення бота на Ubuntu/Debian як systemd-сервіс.
# Запуск:  sudo bash install.sh
set -euo pipefail

APP_DIR=/opt/printer-bot
APP_USER=printerbot
SERVICE=telegram-printer-bot
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Потрібні права root: sudo bash install.sh" >&2
  exit 1
fi

echo "==> Пакети"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip libusb-1.0-0 rsync

echo "==> Користувач $APP_USER"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/printerbot --shell /usr/sbin/nologin "$APP_USER"
fi
for grp in lp dialout plugdev; do
  getent group "$grp" >/dev/null && usermod -aG "$grp" "$APP_USER" || true
done

echo "==> Копіювання в $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.venv/' --exclude '__pycache__/' --exclude '.git/' \
  --exclude 'out/' --exclude '.env' \
  "$SRC_DIR"/ "$APP_DIR"/

echo "==> Віртуальне оточення"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Конфіг"
if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "    створено $APP_DIR/.env — впишіть BOT_TOKEN і дані принтера!"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> udev (USB-принтер)"
install -m 644 "$APP_DIR/systemd/99-citizen-printer.rules" /etc/udev/rules.d/99-citizen-printer.rules
udevadm control --reload-rules || true
udevadm trigger || true

echo "==> systemd"
install -m 644 "$APP_DIR/systemd/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE" || true

cat <<MSG

Готово.

  1. Впишіть налаштування:   sudo nano $APP_DIR/.env
  2. Перезапустіть:          sudo systemctl restart $SERVICE
  3. Статус:                 systemctl status $SERVICE
  4. Логи:                   journalctl -u $SERVICE -f

Сервіс увімкнено в автозапуск — після перезавантаження комп'ютера
бот підніметься сам і буде готовий приймати повідомлення.
MSG
