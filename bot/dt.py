"""Розбір дати й часу, які користувач вводить вручну."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_DATE_TIME_FORMATS = (
    "%d.%m.%Y %H:%M",
    "%d.%m.%y %H:%M",
    "%d.%m.%Y %H.%M",
    "%d.%m.%Y %H %M",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M",
    "%Y-%m-%d %H:%M",
)
_DATE_ONLY_WITH_TIME = ("%d.%m %H:%M", "%d/%m %H:%M", "%d-%m %H:%M")
_TIME_ONLY = ("%H:%M", "%H.%M")

_TODAY_WORDS = ("сьогодні", "сегодня", "today")
_TOMORROW_WORDS = ("завтра", "tomorrow")


def now_in(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone)).replace(second=0, microsecond=0)


def parse_datetime(raw: str, timezone: str) -> datetime | None:
    """Повертає наївний datetime або None, якщо розпізнати не вдалося."""
    text = " ".join(raw.strip().lower().split())
    if not text:
        return None

    today = now_in(timezone).replace(tzinfo=None)

    base_day: datetime | None = None
    for word in _TODAY_WORDS:
        if text.startswith(word):
            base_day, text = today, text[len(word):].strip()
            break
    else:
        for word in _TOMORROW_WORDS:
            if text.startswith(word):
                base_day, text = today + timedelta(days=1), text[len(word):].strip()
                break

    if base_day is not None:
        parsed_time = _parse_time(text) if text else (today.hour, today.minute)
        if parsed_time is None:
            return None
        return base_day.replace(hour=parsed_time[0], minute=parsed_time[1],
                                second=0, microsecond=0)

    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text)

    for fmt in _DATE_TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    for fmt in _DATE_ONLY_WITH_TIME:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(year=today.year)
        except ValueError:
            continue

    parsed_time = _parse_time(text)
    if parsed_time is not None:
        return today.replace(hour=parsed_time[0], minute=parsed_time[1],
                             second=0, microsecond=0)
    return None


def _parse_time(text: str) -> tuple[int, int] | None:
    text = text.strip()
    for fmt in _TIME_ONLY:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.hour, parsed.minute
        except ValueError:
            continue
    if text.isdigit() and 0 <= int(text) <= 23:
        return int(text), 0
    return None
