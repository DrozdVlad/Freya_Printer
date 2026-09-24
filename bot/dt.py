"""Розбір дати, яку користувач вводить вручну."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

_DATE_FORMATS = ("%d.%m.%y", "%d.%m.%Y", "%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y")


def now_in(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone)).replace(second=0, microsecond=0)


def parse_date(raw: str) -> date | None:
    """Дата звершення: `20.12.26` або `20.12.2026`; None, якщо не розпізнали."""
    text = "".join(raw.split())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
