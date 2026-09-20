"""Конфігурація застосунку. Читається з .env або зі змінних оточення."""
from __future__ import annotations

import logging
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


def _float(name: str, default: float) -> float:
    raw = _str(name).replace(",", ".")
    return float(raw) if raw else default


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


def _resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


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

    # Шапка
    header_image: Path | None
    header_image_width_mm: float
    header_dither: str
    header_threshold: int
    header_text: str

    # Друк
    paper_width_mm: float
    paper_length_mm: float
    dots_per_mm: int
    content_align: str
    content_top_mm: float
    content_offset_mm: float
    print_width: int
    print_length: int
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

    @property
    def paper_size(self) -> str:
        return (f"{self.paper_width_mm:g}×{self.paper_length_mm:g} мм "
                f"({self.print_width}×{self.print_length} точок)")

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
    # 203 dpi = 8 точок на міліметр
    dots_per_mm = _int("DOTS_PER_MM", 8)
    paper_width_mm = _float("PAPER_WIDTH_MM", 72.0)
    paper_length_mm = _float("PAPER_LENGTH_MM", 148.0)

    print_width = _int("PRINT_WIDTH", 0) or round(paper_width_mm * dots_per_mm)
    # 0 => довжина листка по вмісту
    print_length = round(paper_length_mm * dots_per_mm) if paper_length_mm > 0 else 0

    font_path = _resolve(_str("FONT_PATH", "fonts/Lora-Regular.ttf"))

    header_image = None
    raw_header = _str("HEADER_IMAGE", "assets/header.png")
    if raw_header:
        candidate = _resolve(raw_header)
        if candidate.exists():
            header_image = candidate
        else:
            logging.getLogger(__name__).warning(
                "Файл шапки %s не знайдено — друкуємо без картинки", candidate
            )

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
        header_image=header_image,
        header_image_width_mm=_float("HEADER_IMAGE_WIDTH_MM", 60.0),
        header_dither=_str("HEADER_DITHER", "dither").lower(),
        header_threshold=_int("HEADER_THRESHOLD", 140),
        header_text=_str("HEADER_TEXT", "Аннозачатіївський Храм"),
        paper_width_mm=paper_width_mm,
        paper_length_mm=paper_length_mm,
        dots_per_mm=dots_per_mm,
        content_align=_str("CONTENT_ALIGN", "top").lower(),
        content_top_mm=_float("CONTENT_TOP_MM", 6.0),
        content_offset_mm=_float("CONTENT_OFFSET_MM", 0.0),
        print_width=print_width,
        print_length=print_length,
        font_path=font_path,
        font_size_title=_int("FONT_SIZE_TITLE", 46),
        font_size_body=_int("FONT_SIZE_BODY", 40),
        font_size_small=_int("FONT_SIZE_SMALL", 32),
        feed_lines=_int("FEED_LINES", 4),
        cut_paper=_bool("CUT_PAPER", True),
        max_copies=_int("MAX_COPIES", 50),
        timezone=_str("TIMEZONE", "Europe/Kyiv"),
    )

    if cfg.backend not in {"network", "usb", "serial", "file", "dummy"}:
        raise ValueError(f"Невідомий PRINTER_BACKEND: {cfg.backend!r}")
    if cfg.content_align not in {"top", "center"}:
        raise ValueError(f"Невідомий CONTENT_ALIGN: {cfg.content_align!r}")
    if cfg.header_dither not in {"threshold", "dither"}:
        raise ValueError(f"Невідомий HEADER_DITHER: {cfg.header_dither!r}")
    if cfg.print_width % 8 != 0:
        raise ValueError(
            f"Ширина друку має бути кратна 8 точкам, зараз {cfg.print_width}"
        )
    if not cfg.font_path.exists():
        raise FileNotFoundError(f"Не знайдено шрифт: {cfg.font_path}")
    return cfg
