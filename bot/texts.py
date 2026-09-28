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
        key="sorokoust",
        button="Сорокоуст",
        title="ЗА УПОКІЙ\nсорокоуст",
    ),
    Procedure(
        key="cathedral_liturgy",
        button="Соборна літургія",
        title="ЗА УПОКІЙ\nсоборна літургія",
    ),
    Procedure(
        key="cathedral_panakhyda",
        button="Соборна панахида",
        title="ЗА УПОКІЙ\nсоборна панахида",
    ),
    Procedure(
        key="individual_liturgy",
        button="Індивідуальна літургія",
        title="ЗА УПОКІЙ\nіндивідуальна літургія",
    ),
    Procedure(
        key="individual_panakhyda",
        button="Індивідуальна панахида",
        title="ЗА УПОКІЙ\nіндивідуальна панахида",
    ),
)

PROCEDURE_BY_BUTTON = {p.button: p for p in PROCEDURES}
PROCEDURE_BY_KEY = {p.key: p for p in PROCEDURES}

# Кнопки
BTN_MORE = "➕ Ще ім'я"
BTN_DONE = "✅ Все"
BTN_PRINT = "🖨 Друкувати"
BTN_CANCEL = "✖️ Скасувати"
BTN_AGAIN_NEW = "📝 Так, нова записка"
BTN_AGAIN_SAME = "🔁 Так, цю ж ще раз"
BTN_AGAIN_NO = "❌ Ні"
COPY_PRESETS = ("1", "2", "3", "5", "10")

# Повідомлення
GREETING = (
    "Вітаю! Я друкую записки на принтері Citizen CT-E351.\n\n"
    "Оберіть тип процедури 👇"
)
ASK_TYPE = "Оберіть тип процедури:"
ASK_DATE = (
    "Дата звершення?\n\n"
    "Формат: `20.12.26`"
)
BAD_DATE = (
    "Не зрозумів дату 🤔\n"
    "Введіть так: `20.12.26`"
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
UNKNOWN = "Оберіть тип процедури 👇"
BTN_OPEN_PRIVATE = "🖨 Оформити записку"
GO_PRIVATE = "Записки оформлюються в особистих повідомленнях — натисніть кнопку 👇"
ASK_AGAIN = "Друкувати ще?"
FINISHED = "Дякую! Коли знадобиться — натисніть /start."

HELP = (
    "*Команди*\n"
    "/start — нова записка\n"
    "/cancel — скасувати поточну\n"
    "/status — перевірити зв'язок з принтером\n"
    "/help — ця довідка"
)
