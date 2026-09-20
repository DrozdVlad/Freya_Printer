# Telegram-бот → принтер Citizen CT-E351

Бот принимает заявку в Telegram и печатает записку на термопринтере
Citizen CT-E351 (ESC/POS). Текст рендерится шрифтом **Lora Regular**,
каждая строка — строго по центру ленты.

## Как выглядит диалог

```
/start
  → Тип процедуры:  [Недільна планова літургія] [Замовна літургія] [Замовна панахида]
  → Дата и время:   21.09.2026 09:30   (или кнопка «Зараз»)
  → Имя и фамилия:  Іван Петренко
  → [➕ Ще ім'я] / [✅ Все]
  → Сколько копий:  [1] [2] [3] [5] [10] или числом
  → Превью картинки + [🖨 Друкувати] / [✖️ Скасувати]
  → Печать
```

Команды: `/start`, `/cancel`, `/status` (проверка связи с принтером),
`/whoami` (узнать свой Telegram id), `/help`.

## Что печатается

```
        ЗА УПОКІЙ
  замовна панахида
  ───────────────
     21.09.2026
       09:30
  ───────────────
   Іван Петренко
   Марія Коваль
  ───────────────
```

Ширина 576 точек (80 мм бумаги, 72 мм области печати, 203 dpi).
Для 58 мм поставьте `PRINT_WIDTH=420`.

## Установка на Ubuntu

```bash
git clone <repo> printer-bot && cd printer-bot
sudo bash install.sh
sudo nano /opt/printer-bot/.env      # BOT_TOKEN + данные принтера
sudo systemctl restart telegram-printer-bot
```

`install.sh` делает всё: ставит пакеты, создаёт пользователя `printerbot`,
кладёт код в `/opt/printer-bot`, собирает venv, ставит udev-правило для USB
и регистрирует systemd-сервис в автозапуск.

**Автостарт при включении компьютера** обеспечивает systemd:
сервис включён через `systemctl enable`, поднимается после сети,
`Restart=always` перезапускает его при любом падении.

```bash
systemctl status telegram-printer-bot     # состояние
journalctl -u telegram-printer-bot -f     # логи в реальном времени
```

## Настройка (`/opt/printer-bot/.env`)

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | токен от [@BotFather](https://t.me/BotFather) |
| `ALLOWED_USER_IDS` | белый список Telegram id через запятую (пусто = все) |
| `PRINTER_BACKEND` | `network` / `usb` / `serial` / `file` |
| `PRINTER_HOST`, `PRINTER_PORT` | для сетевого принтера, порт RAW — 9100 |
| `PRINTER_USB_VENDOR/PRODUCT` | для USB (смотреть в `lsusb`) |
| `PRINT_WIDTH` | 576 (80 мм) или 420 (58 мм) |
| `FONT_SIZE_TITLE/BODY` | размеры шрифта в точках |
| `CUT_PAPER` | отрезать бумагу после каждой копии |
| `MAX_COPIES` | защита от случайных 500 копий |
| `TIMEZONE` | для кнопки «Зараз», по умолчанию `Europe/Kyiv` |

### Как подключить принтер

**Ethernet (используется сейчас).** Данные принтера уже прописаны в `.env.example`:

```
PRINTER_BACKEND=network
PRINTER_HOST=192.168.100.210     # DHCP OFF, адрес статический — не уплывёт
PRINTER_PORT=9100
```

Сетевой лист принтера: MAC `00:0D:AC:34:24:4B`, маска `255.255.0.0`,
шлюз `192.168.100.1`, таймаут 60 с, PrintPort 9100.

⚠️ Ubuntu-сервер должен видеть принтер по сети. Проверка с сервера:

```bash
nc -vz 192.168.100.210 9100      # должно быть "succeeded"
```

Если не отвечает — сервер в другой подсети (например `192.168.50.x`),
нужен маршрут через роутер либо сервер в той же сети `192.168.100.x`.
Найти принтер сканированием: `python3 scripts/discover.py 192.168.100`

**USB:** посмотрите `lsusb` → строка вида `ID 1cb0:0003 Citizen`.
Впишите VID/PID в `.env`, поставьте `PRINTER_BACKEND=usb`.
Если udev-правило не подхватилось — `sudo udevadm control --reload-rules && sudo udevadm trigger`.

Альтернатива для USB без pyusb: `PRINTER_BACKEND=file` и `PRINTER_FILE_PATH=/dev/usb/lp0`.

## Проверка

```bash
python3 scripts/selftest.py                 # весь тракт на фейковом принтере, железо не нужно
python3 scripts/preview.py out/preview.png  # PNG-превью записки
python3 scripts/testprint.py 1              # реальная печать одной копии
```

## Изменить список процедур

Правится один список в [bot/texts.py](bot/texts.py):

```python
PROCEDURES = (
    Procedure(key="...", button="Короткая надпись на кнопке",
              title="ЧТО ПЕЧАТАЕТСЯ\nвторой строкой"),
)
```

## Структура

```
bot/config.py    — настройки из .env
bot/texts.py     — тексты и список процедур
bot/dt.py        — разбор даты/времени
bot/render.py    — рендер записки в картинку (Lora, центрирование)
bot/printing.py  — ESC/POS: сеть/USB/serial, профиль CT-E351, резка
bot/main.py      — диалог Telegram
fonts/           — Lora Regular (OFL), собран из вариативного шрифта
systemd/         — unit и udev-правило
scripts/         — selftest, preview, testprint, discover
```

## Стек

Python 3.10+, `python-telegram-bot` (polling, без вебхуков и белого IP),
`python-escpos`, `Pillow`.
