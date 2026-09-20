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
    [рисунок храма]
 Аннозачатіївський Храм
  ─────────────────
       ЗА УПОКІЙ
   замовна панахида
  ─────────────────
      21.09.2026
        09:30
  ─────────────────
    Іван Петренко
     Марія Коваль
  ─────────────────
```

Шапка — картинка `assets/header.png` (фото храма) и подпись под ней.
Заменить: положить свой PNG на это место, он отмасштабируется под
`HEADER_IMAGE_WIDTH_MM` и переведётся в 1 бит.

Файл подготовлен под печать: небо убрано, контраст и резкость подняты,
размер ровно 480 точек (60 мм) — столько же, сколько стоит в
`HEADER_IMAGE_WIDTH_MM`, поэтому принтеру не приходится его пересчитывать.
Режим `dither` (Флойд–Стейнберг) — для фотографии; для штрихового
рисунка лучше `threshold`.

```
HEADER_IMAGE=assets/header.png   # пусто = печатать без картинки
HEADER_IMAGE_WIDTH_MM=60
HEADER_DITHER=dither             # threshold — если картинка штриховая
HEADER_THRESHOLD=140             # для threshold: ниже = тоньше линии
HEADER_TEXT=Аннозачатіївський Храм
CONTENT_ALIGN=top                # храм вверху листка; center — по центру
CONTENT_TOP_MM=6
```

## Размер листка

**72 × 148 мм** — 576 × 1184 точек (203 dpi = ровно 8 точек на мм).

Длина фиксированная: содержимое центрируется на холсте 1184 точки,
после печати сразу идёт подача к ножу и отрез (`GS V 66 0`),
поэтому каждая копия выходит одного размера.

```
PAPER_WIDTH_MM=72       # ширина ленты, область печати
PAPER_LENGTH_MM=148     # длина до отреза; 0 = рвать по содержимому
CONTENT_OFFSET_MM=0     # сдвиг текста вниз, если печать идёт не по центру
```

**Калибровка после первой печати:** замерьте листок линейкой.
Вышел длиннее/короче — поправьте `PAPER_LENGTH_MM` на разницу.
Текст сидит не по центру (нож режет с отступом от печатающей головки) —
подвиньте `CONTENT_OFFSET_MM` (можно с минусом).

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
| `PAPER_WIDTH_MM` / `PAPER_LENGTH_MM` | размер листка в мм (72 × 148) |
| `CONTENT_OFFSET_MM` | сдвиг содержимого вниз при калибровке |
| `HEADER_IMAGE` / `HEADER_TEXT` | картинка храма и подпись под ней |
| `CONTENT_ALIGN` | `top` (по умолчанию) или `center` |
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
                   (растр кодируется один раз на всю партию копий)
bot/main.py      — диалог Telegram
fonts/           — Lora Regular (OFL), собран из вариативного шрифта
assets/header.png — изображение храма для шапки
systemd/         — unit и udev-правило
scripts/         — selftest, preview, testprint, discover
```

## Стек

Python 3.10+, `python-telegram-bot` (polling, без вебхуков и белого IP),
`python-escpos`, `Pillow`.
