"""Конфігурація застосунку. Читається з .env або зі змінних оточення."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _int(name: str, default: int) -> int:
    raw = _str(name)
    return int(raw) if raw else default


def _bool(name: str, default: bool) -> bool:
    raw = _str(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on", "так"}


def _hex_int(name: str, default: int) -> int:
    raw = _str(name)
    return int(raw, 0) if raw else default


def _opt_hex_int(name: str) -> int | None:
    raw = _str(name)
    return int(raw, 0) if raw else None


def _ids(name: str) -> frozenset[int]:
    raw = _str(name)
    if not raw:
        return frozenset()
    return frozenset(int(p) for p in raw.replace(";", ",").split(",") if p.strip())


@dataclass(frozen=True)
class Config:
    # Telegram
    bot_token: str
    allowed_user_ids: frozenset[int]

    # Принтер
    backend: str
    host: str
    port: int
    timeout: int
    usb_vendor: int
    usb_product: int
    usb_in_ep: int | None
    usb_out_ep: int | None
    serial_port: str
    serial_baudrate: int
    file_path: str

    # Друк
    print_width: int
    font_path: Path
    font_size_title: int
    font_size_body: int
    font_size_small: int
    feed_lines: int
    cut_paper: bool
    max_copies: int
    timezone: str

    @property
    def restricted(self) -> bool:
        return bool(self.allowed_user_ids)

    def is_allowed(self, user_id: int) -> bool:
        return (not self.restricted) or user_id in self.allowed_user_ids

    def describe_printer(self) -> str:
        if self.backend == "network":
            return f"network {self.host}:{self.port}"
        if self.backend == "usb":
            return f"usb {self.usb_vendor:#06x}:{self.usb_product:#06x}"
        if self.backend == "serial":
            return f"serial {self.serial_port} @ {self.serial_baudrate}"
        if self.backend == "file":
            return f"file {self.file_path}"
        return f"dummy ({self.backend})"


def load_config() -> Config:
    font_path = Path(_str("FONT_PATH", "fonts/Lora-Regular.ttf"))
    if not font_path.is_absolute():
        font_path = BASE_DIR / font_path

    cfg = Config(
        bot_token=_str("BOT_TOKEN"),
        allowed_user_ids=_ids("ALLOWED_USER_IDS"),
        backend=_str("PRINTER_BACKEND", "network").lower(),
        host=_str("PRINTER_HOST", "192.168.100.210"),
        port=_int("PRINTER_PORT", 9100),
        timeout=_int("PRINTER_TIMEOUT", 15),
        usb_vendor=_hex_int("PRINTER_USB_VENDOR", 0x1CB0),
        usb_product=_hex_int("PRINTER_USB_PRODUCT", 0x0003),
        usb_in_ep=_opt_hex_int("PRINTER_USB_IN_EP"),
        usb_out_ep=_opt_hex_int("PRINTER_USB_OUT_EP"),
        serial_port=_str("PRINTER_SERIAL_PORT", "/dev/ttyUSB0"),
        serial_baudrate=_int("PRINTER_SERIAL_BAUDRATE", 115200),
        file_path=_str("PRINTER_FILE_PATH", "/dev/usb/lp0"),
        print_width=_int("PRINT_WIDTH", 576),
        font_path=font_path,
        font_size_title=_int("FONT_SIZE_TITLE", 36),
        font_size_body=_int("FONT_SIZE_BODY", 32),
        font_size_small=_int("FONT_SIZE_SMALL", 26),
        feed_lines=_int("FEED_LINES", 4),
        cut_paper=_bool("CUT_PAPER", True),
        max_copies=_int("MAX_COPIES", 50),
        timezone=_str("TIMEZONE", "Europe/Kyiv"),
    )

    if cfg.backend not in {"network", "usb", "serial", "file", "dummy"}:
        raise ValueError(f"Невідомий PRINTER_BACKEND: {cfg.backend!r}")
    if not cfg.font_path.exists():
        raise FileNotFoundError(f"Не знайдено шрифт: {cfg.font_path}")
    return cfg
