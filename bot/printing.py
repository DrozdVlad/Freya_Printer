"""Робота з принтером Citizen CT-E351 (ESC/POS)."""
from __future__ import annotations

import asyncio
import copy
import logging
import socket
from functools import lru_cache

from PIL import Image

from .config import Config

log = logging.getLogger(__name__)

# один друк за раз: паралельні запити змішали б байти в сокеті
_print_lock = asyncio.Lock()


class PrinterError(RuntimeError):
    """Не вдалося надрукувати."""


@lru_cache(maxsize=4)
def _profile(width_pixels: int, width_mm: int):
    """Профіль CT-E351: 80 мм паперу, 72 мм (576 точок) області друку."""
    from escpos.capabilities import Profile

    data = copy.deepcopy(Profile.profile_data)
    data["media"] = {
        "dpi": 203,
        "width": {"pixels": width_pixels, "mm": width_mm},
    }
    klass = type("CitizenCTE351Profile", (Profile,), {"profile_data": data})
    # Profile.__init__ обнуляє features, без них escpos не ріже папір
    return klass(features=data["features"])


def _width_mm(cfg: Config) -> int:
    return round(cfg.print_width / cfg.dots_per_mm)


def _build_printer(cfg: Config):
    from escpos import printer as esc

    profile = _profile(cfg.print_width, _width_mm(cfg))

    if cfg.backend == "network":
        return esc.Network(host=cfg.host, port=cfg.port, timeout=cfg.timeout, profile=profile)
    if cfg.backend == "usb":
        kwargs = {}
        if cfg.usb_in_ep is not None:
            kwargs["in_ep"] = cfg.usb_in_ep
        if cfg.usb_out_ep is not None:
            kwargs["out_ep"] = cfg.usb_out_ep
        return esc.Usb(
            idVendor=cfg.usb_vendor,
            idProduct=cfg.usb_product,
            timeout=cfg.timeout * 1000,
            profile=profile,
            **kwargs,
        )
    if cfg.backend == "serial":
        return esc.Serial(
            devfile=cfg.serial_port,
            baudrate=cfg.serial_baudrate,
            timeout=cfg.timeout,
            profile=profile,
        )
    if cfg.backend == "file":
        return esc.File(devfile=cfg.file_path, profile=profile)
    return esc.Dummy(profile=profile)


def _encode_copy(cfg: Config, image: Image.Image) -> bytes:
    """Кодує одну копію в ESC/POS.

    Растр важить ~80 КБ, тож для партії копій кодуємо його один раз
    і повторюємо готовий блок байтів.
    """
    from escpos.printer import Dummy

    job = Dummy(profile=_profile(cfg.print_width, _width_mm(cfg)))
    job.hw("INIT")
    job.image(image, impl="bitImageRaster", center=False)
    if cfg.print_length > 0:
        # полотно вже потрібної довжини: GS V 66 0 подає до ножа і ріже
        if cfg.cut_paper:
            job.cut(feed=False)
    else:
        job.text("\n" * cfg.feed_lines)
        if cfg.cut_paper:
            job.cut()
    return bytes(job.output)


def _print_sync(cfg: Config, pages: list[Image.Image], copies: int) -> None:
    # копія — усі аркуші підряд, кожен відрізаний окремо
    payload = b"".join(_encode_copy(cfg, page) for page in pages)
    device = _build_printer(cfg)
    try:
        device.open()
        for index in range(copies):
            device._raw(payload)
            log.info("Надруковано копію %s/%s (аркушів: %s)",
                     index + 1, copies, len(pages))
    except Exception as exc:  # noqa: BLE001 — показуємо користувачу причину
        raise PrinterError(str(exc)) from exc
    finally:
        try:
            device.close()
        except Exception:  # noqa: BLE001
            log.debug("Помилка при закритті з'єднання з принтером", exc_info=True)


async def print_image(cfg: Config, image: Image.Image | list[Image.Image],
                      copies: int) -> None:
    """Друкує копію (один аркуш або кілька) `copies` разів.

    Блокуючий ввід/вивід — у потоці.
    """
    pages = [image] if isinstance(image, Image.Image) else list(image)
    async with _print_lock:
        await asyncio.to_thread(_print_sync, cfg, pages, copies)


def _check_sync(cfg: Config) -> str:
    if cfg.backend == "network":
        with socket.create_connection((cfg.host, cfg.port), timeout=cfg.timeout):
            return f"TCP {cfg.host}:{cfg.port} — з'єднання відкрито"
    device = _build_printer(cfg)
    try:
        device.open()
        return f"{cfg.describe_printer()} — пристрій відкрито"
    finally:
        try:
            device.close()
        except Exception:  # noqa: BLE001
            pass


async def check_printer(cfg: Config) -> str:
    """Перевіряє, чи принтер доступний. Кидає виняток, якщо ні."""
    return await asyncio.to_thread(_check_sync, cfg)
