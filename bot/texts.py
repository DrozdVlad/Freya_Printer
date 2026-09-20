"""Тексти інтерфейсу та перелік процедур.

`button` — підпис на кнопці в Telegram, `title` — що друкується.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Procedure:
    key: str
    button: str
    title: str


PROCEDURES: tuple[Procedure, ...] = (
    Procedure(
        key="sunday_liturgy",
        button="Недільна планова літургія",
        title="ЗА УПОКІЙ\nнедільна планова літургія",
    ),
    Procedure(
        key="ordered_liturgy",
        button="Замовна літургія",
        title="ЗА УПОКІЙ\nзамовна літургія",
    ),
    Procedure(
        key="ordered_panakhyda",
        button="Замовна панахида",
        title="ЗА УПОКІЙ\nзамовна панахида",
    ),
)

PROCEDURE_BY_BUTTON = {p.button: p for p in PROCEDURES}
PROCEDURE_BY_KEY = {p.key: p for p in PROCEDURES}

# Кнопки
BTN_NOW = "🕒 Зараз"
BTN_MORE = "➕ Ще ім'я"
BTN_DONE = "✅ Все"
BTN_PRINT = "🖨 Друкувати"
BTN_CANCEL = "✖️ Скасувати"
COPY_PRESETS = ("1", "2", "3", "5", "10")

# Повідомлення
GREETING = (
    "Вітаю! Я друкую записки на принтері Citizen CT-E351.\n\n"
    "Оберіть тип процедури 👇"
)
ASK_TYPE = "Оберіть тип процедури:"
ASK_DATETIME = (
    "Вкажіть *дату і час* друку.\n\n"
    "Формат: `21.09.2026 09:30`\n"
    "Можна також: `21.09 09:30`, `сьогодні 10:00`, `завтра 8:00`\n"
    "або натисніть кнопку «Зараз»."
)
BAD_DATETIME = (
    "Не зрозумів дату/час 🤔\n"
    "Спробуйте так: `21.09.2026 09:30` або натисніть «Зараз»."
)
ASK_FIRST_NAME = ("Введіть *ім'я та прізвище*.\n"
                  "Можна одразу списком — кожне імʼя з нового рядка.")
ASK_NEXT_NAME = "Введіть наступне *ім'я та прізвище*:"
BAD_NAME = "Ім'я закоротке. Введіть, будь ласка, ім'я та прізвище."
ASK_MORE = "Додати ще одне ім'я чи це все?"
ASK_COPIES = "Скільки копій друкувати?"
BAD_COPIES = "Вкажіть кількість копій числом (від 1 до {max_copies})."
NOT_ALLOWED = "Вибачте, у вас немає доступу до цього бота."
CANCELLED = "Скасовано. Натисніть /start, щоб почати заново."
PRINTING = "Відправляю на принтер… ⏳"
UNKNOWN = "Не зрозумів. Натисніть /start, щоб почати заново."

HELP = (
    "*Команди*\n"
    "/start — нова записка\n"
    "/cancel — скасувати поточну\n"
    "/status — перевірити зв'язок з принтером\n"
    "/help — ця довідка"
)
