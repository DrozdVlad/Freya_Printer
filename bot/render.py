"""Рендер записки в монохромне зображення для термопринтера.

Друкуємо саме картинкою, а не вбудованим шрифтом принтера, бо ТЗ вимагає
шрифт Lora Regular. Кожен рядок вирівняно строго по центру.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .config import Config

MARGIN_TOP = 16
MARGIN_BOTTOM = 24
SIDE_PADDING = 16
LINE_SPACING = 1.30
RULE_THICKNESS = 2
RULE_WIDTH_RATIO = 0.55
GAP_BEFORE_RULE = 14
GAP_AFTER_RULE = 14


@dataclass
class Receipt:
    """Дані, які друкуємо."""

    procedure_title: str
    when: datetime
    names: list[str] = field(default_factory=list)

    @property
    def date_str(self) -> str:
        return self.when.strftime("%d.%m.%Y")

    @property
    def time_str(self) -> str:
        return self.when.strftime("%H:%M")


@lru_cache(maxsize=16)
def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _line_height(font: ImageFont.FreeTypeFont) -> int:
    ascent, descent = font.getmetrics()
    return int((ascent + descent) * LINE_SPACING)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
          max_width: int) -> list[str]:
    """Переносить рядок по словах, щоб влізти в ширину стрічки."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            probe = f"{current} {word}"
            if draw.textlength(probe, font=font) <= max_width:
                current = probe
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _blocks(cfg: Config, receipt: Receipt) -> list[tuple[str, object]]:
    """Список елементів записки: ("text", (рядок, шрифт)) або ("rule", None)."""
    path = str(cfg.font_path)
    title = _font(path, cfg.font_size_title)
    body = _font(path, cfg.font_size_body)

    items: list[tuple[str, object]] = []
    items.append(("text_block", (receipt.procedure_title, title)))
    items.append(("rule", None))
    items.append(("text_block", (receipt.date_str, body)))
    items.append(("text_block", (receipt.time_str, body)))
    items.append(("rule", None))
    for name in receipt.names:
        items.append(("text_block", (name, body)))
    items.append(("rule", None))
    return items


def render_receipt(cfg: Config, receipt: Receipt) -> Image.Image:
    """Повертає готове ч/б зображення записки на всю ширину друку."""
    width = cfg.print_width
    max_text_width = width - 2 * SIDE_PADDING

    probe = ImageDraw.Draw(Image.new("L", (width, 10), 255))
    items = _blocks(cfg, receipt)

    # 1-й прохід: рахуємо висоту
    laid_out: list[tuple[str, object]] = []
    height = MARGIN_TOP
    for kind, payload in items:
        if kind == "rule":
            height += GAP_BEFORE_RULE + RULE_THICKNESS + GAP_AFTER_RULE
            laid_out.append(("rule", None))
            continue
        text, font = payload  # type: ignore[misc]
        for line in _wrap(probe, text, font, max_text_width):
            height += _line_height(font)
            laid_out.append(("line", (line, font)))
    height += MARGIN_BOTTOM

    # 2-й прохід: малюємо
    canvas = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(canvas)
    centre = width // 2
    y = MARGIN_TOP
    for kind, payload in laid_out:
        if kind == "rule":
            y += GAP_BEFORE_RULE
            half = int(width * RULE_WIDTH_RATIO / 2)
            draw.rectangle(
                [centre - half, y, centre + half, y + RULE_THICKNESS - 1], fill=0
            )
            y += RULE_THICKNESS + GAP_AFTER_RULE
            continue
        line, font = payload  # type: ignore[misc]
        if line:
            draw.text((centre, y), line, font=font, fill=0, anchor="ma")
        y += _line_height(font)

    # Поріг без дизерингу — текст на чеку виходить чітким
    return canvas.point(lambda p: 255 if p > 150 else 0).convert("1")


def render_preview(cfg: Config, receipt: Receipt) -> Image.Image:
    """Те саме зображення, але на сірому тлі — для перегляду в Telegram."""
    receipt_img = render_receipt(cfg, receipt).convert("L")
    pad = 24
    canvas = Image.new(
        "L", (receipt_img.width + 2 * pad, receipt_img.height + 2 * pad), 225
    )
    canvas.paste(receipt_img, (pad, pad))
    return canvas
