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

# Один друк за раз — щоб паралельні запити не змішали байти в одному сокеті.
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
    # Profile.__init__ обнуляє features, тому передаємо їх явно —
    # інакше escpos вважає, що принтер не вміє різати папір.
    return klass(features=data["features"])


def _build_printer(cfg: Config):
    from escpos import printer as esc

    width_mm = 72 if cfg.print_width >= 576 else 48
    profile = _profile(cfg.print_width, width_mm)

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


def _print_sync(cfg: Config, image: Image.Image, copies: int) -> None:
    device = _build_printer(cfg)
    try:
        device.open()
        device.hw("INIT")
        for index in range(copies):
            device.image(image, impl="bitImageRaster", center=False)
            device.text("\n" * cfg.feed_lines)
            if cfg.cut_paper:
                device.cut()
            log.info("Надруковано копію %s/%s", index + 1, copies)
    except Exception as exc:  # noqa: BLE001 — показуємо користувачу причину
        raise PrinterError(str(exc)) from exc
    finally:
        try:
            device.close()
        except Exception:  # noqa: BLE001
            log.debug("Помилка при закритті з'єднання з принтером", exc_info=True)


async def print_image(cfg: Config, image: Image.Image, copies: int) -> None:
    """Друкує зображення `copies` разів. Блокуючий ввід/вивід — у потоці."""
    async with _print_lock:
        await asyncio.to_thread(_print_sync, cfg, image, copies)


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
