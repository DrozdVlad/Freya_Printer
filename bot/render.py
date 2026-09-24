"""Рендер записки в монохромне зображення для термопринтера.

Друкуємо картинкою, а не вбудованим шрифтом принтера, бо потрібен Lora.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .config import Config

log = logging.getLogger(__name__)

MARGIN_TOP = 16
MARGIN_BOTTOM = 24
SIDE_PADDING = 16
LINE_SPACING = 1.30
RULE_THICKNESS = 2
RULE_WIDTH_RATIO = 0.55
GAP_BEFORE_RULE = 14
GAP_AFTER_RULE = 14
GAP_AFTER_IMAGE = 10
BOTTOM_PAD = 16
PAGE_GAP = 24

DATE_LABEL = "Дата звершення"


@dataclass
class Receipt:
    """Дані, які друкуємо."""

    procedure_title: str
    when: date
    names: list[str] = field(default_factory=list)
    printed_at: datetime | None = None
    # номер аркуша в копії, якщо імена не влізли на один
    page: int = 1
    pages: int = 1

    @property
    def date_str(self) -> str:
        return self.when.strftime("%d.%m.%Y")

    @property
    def printed_str(self) -> str:
        return self.printed_at.strftime("друк %d.%m.%Y %H:%M") if self.printed_at else ""

    @property
    def page_str(self) -> str:
        return f"аркуш {self.page} з {self.pages}" if self.pages > 1 else ""

    def split(self, per_page: int) -> list["Receipt"]:
        """Ділить імена на аркуші по `per_page`; разом вони — одна копія."""
        if per_page <= 0 or len(self.names) <= per_page:
            return [self]
        chunks = [self.names[i:i + per_page]
                  for i in range(0, len(self.names), per_page)]
        return [replace(self, names=chunk, page=index, pages=len(chunks))
                for index, chunk in enumerate(chunks, start=1)]


@lru_cache(maxsize=4)
def _header(path: str, mtime: float, width: int, dither: str,
            threshold: int) -> Image.Image:
    """Готує картинку шапки: масштаб під ширину стрічки і 1 біт."""
    with Image.open(path) as source:
        image = source.convert("RGBA")
    flat = Image.new("RGBA", image.size, (255, 255, 255, 255))
    flat.alpha_composite(image)
    grey = flat.convert("L")
    if grey.width != width:
        height = max(1, round(grey.height * width / grey.width))
        grey = grey.resize((width, height), Image.LANCZOS)
    if dither == "dither":
        return grey.convert("1")
    return grey.point(lambda value: 255 if value > threshold else 0, mode="1")


def header_image(cfg: Config) -> Image.Image | None:
    if cfg.header_image is None:
        return None
    width = min(cfg.print_width,
                round(cfg.header_image_width_mm * cfg.dots_per_mm))
    return _header(str(cfg.header_image), cfg.header_image.stat().st_mtime,
                   width, cfg.header_dither, cfg.header_threshold)


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
    picture = header_image(cfg)
    if picture is not None:
        items.append(("image", picture))
    if cfg.header_text:
        items.append(("text_block", (cfg.header_text, _font(path, cfg.font_size_small))))
    if picture is not None or cfg.header_text:
        items.append(("rule", None))
    items.append(("text_block", (receipt.procedure_title, title)))
    items.append(("rule", None))
    items.append(("text_block", (DATE_LABEL, _font(path, cfg.font_size_small))))
    items.append(("text_block", (receipt.date_str, body)))
    items.append(("rule", None))
    for name in receipt.names:
        items.append(("text_block", (name, body)))
    items.append(("rule", None))
    if receipt.page_str:
        items.append(("text_block", (receipt.page_str, _font(path, cfg.font_size_tiny))))
    if receipt.printed_str:
        items.append(("text_block", (receipt.printed_str, _font(path, cfg.font_size_tiny))))
    return items


def _render_content(cfg: Config, receipt: Receipt) -> Image.Image:
    """Малює вміст записки; висота — рівно стільки, скільки треба тексту."""
    width = cfg.print_width
    max_text_width = width - 2 * SIDE_PADDING

    probe = ImageDraw.Draw(Image.new("L", (width, 10), 255))
    items = _blocks(cfg, receipt)

    # рахуємо висоту
    laid_out: list[tuple[str, object]] = []
    height = MARGIN_TOP
    for kind, payload in items:
        if kind == "rule":
            height += GAP_BEFORE_RULE + RULE_THICKNESS + GAP_AFTER_RULE
            laid_out.append(("rule", None))
            continue
        if kind == "image":
            picture: Image.Image = payload  # type: ignore[assignment]
            height += picture.height + GAP_AFTER_IMAGE
            laid_out.append(("image", picture))
            continue
        text, font = payload  # type: ignore[misc]
        for line in _wrap(probe, text, font, max_text_width):
            height += _line_height(font)
            laid_out.append(("line", (line, font)))
    height += MARGIN_BOTTOM

    # малюємо
    canvas = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(canvas)
    centre = width // 2
    y = MARGIN_TOP
    for kind, payload in laid_out:
        if kind == "image":
            picture = payload
            canvas.paste(picture.convert("L"), (centre - picture.width // 2, y))
            y += picture.height + GAP_AFTER_IMAGE
            continue
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

    return canvas


def _sheet_height(cfg: Config, content: Image.Image) -> int:
    step = cfg.dots_per_mm
    margin = round(cfg.content_top_mm * step)
    needed = margin + content.height + BOTTOM_PAD
    height = max(cfg.print_length, -(-needed // step) * step)
    limit = cfg.max_print_length
    if limit and height > limit:
        log.warning("Листок %s точок обрізано до стелі %s", height, limit)
        height = limit
    return height


def _place(cfg: Config, content: Image.Image, height: int) -> Image.Image:
    """Кладе вміст на листок заданої довжини і переводить у 1 біт."""
    if cfg.print_length <= 0:
        sheet = content
    else:
        step = cfg.dots_per_mm
        margin = round(cfg.content_top_mm * step)
        sheet = Image.new("L", (cfg.print_width, height), 255)
        offset = round(cfg.content_offset_mm * step)
        if cfg.content_align == "top":
            top = margin + offset
        else:
            top = (height - content.height) // 2 + offset
        top = max(0, min(top, max(0, height - content.height)))
        sheet.paste(content, (0, top))

    # поріг без дизерингу: текст на чеку має бути чітким
    return sheet.point(lambda value: 255 if value > 150 else 0, mode="1")


def render_pages(cfg: Config, receipt: Receipt) -> list[Image.Image]:
    """Аркуші однієї копії: по NAMES_PER_SHEET імен на кожному.

    PAPER_LENGTH_MM — мінімальна довжина листка. Якщо вміст не влазить,
    листок подовжується (кратно міліметру), щоб нічого не стискати.
    Усі аркуші копії мають однакову довжину. PAPER_MAX_LENGTH_MM ставить
    стелю, 0 — без обмеження.
    """
    contents = [_render_content(cfg, part)
                for part in receipt.split(cfg.names_per_sheet)]
    height = max(_sheet_height(cfg, content) for content in contents)
    return [_place(cfg, content, height) for content in contents]


def render_receipt(cfg: Config, receipt: Receipt) -> Image.Image:
    """Один листок з усіма іменами (без поділу на аркуші)."""
    content = _render_content(cfg, receipt)
    return _place(cfg, content, _sheet_height(cfg, content))


def preview_frame(sheets: Image.Image | list[Image.Image]) -> Image.Image:
    """Кладе аркуші поруч на сіре тло — для перегляду в Telegram."""
    pages = [sheets] if isinstance(sheets, Image.Image) else list(sheets)
    pad = 20
    width = sum(page.width for page in pages) + PAGE_GAP * (len(pages) - 1)
    height = max(page.height for page in pages)
    canvas = Image.new("L", (width + 2 * pad, height + 2 * pad), 210)
    draw = ImageDraw.Draw(canvas)
    x = pad
    for page in pages:
        canvas.paste(page.convert("L"), (x, pad))
        draw.rectangle([x - 1, pad - 1, x + page.width, pad + page.height],
                       outline=120, width=1)
        x += page.width + PAGE_GAP
    return canvas
