#!/usr/bin/env python3
"""Самоперевірка без залізяки: піднімає фейковий ESC/POS-принтер на TCP
і проганяє повний ланцюг «рендер → сокет → байти».

    python3 scripts/selftest.py
"""
from __future__ import annotations

import asyncio
import os
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

received = bytearray()


def fake_printer(server: socket.socket) -> None:
    while True:
        try:
            conn, _ = server.accept()
        except OSError:
            return
        with conn:
            while chunk := conn.recv(65536):
                received.extend(chunk)


def main() -> int:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()
    threading.Thread(target=fake_printer, args=(server,), daemon=True).start()

    os.environ.update(
        PRINTER_BACKEND="network",
        PRINTER_HOST=host,
        PRINTER_PORT=str(port),
        PRINTER_TIMEOUT="5",
        BOT_TOKEN="test",
    )

    from bot.config import load_config
    from bot.printing import print_image
    from bot.render import Receipt, render_receipt
    from bot.texts import PROCEDURES

    cfg = load_config()
    receipt = Receipt(
        procedure_title=PROCEDURES[2].title,
        when=datetime(2026, 9, 21, 9, 30),
        names=["Іван Петренко", "Марія Коваль"],
    )
    image = render_receipt(cfg, receipt)
    copies = 3
    asyncio.run(print_image(cfg, image, copies))
    server.close()

    data = bytes(received)
    checks = {
        f"ширина {cfg.print_width} px ({cfg.paper_width_mm:g} мм)":
            image.width == cfg.print_width,
        f"довжина {cfg.print_length} px ({cfg.paper_length_mm:g} мм)":
            image.height == cfg.print_length,
        "режим 1-біт": image.mode == "1",
        "ESC @ (ініціалізація)": data.count(b"\x1b\x40") >= 1,
        "растрова графіка GS v 0": data.count(b"\x1d\x76\x30") >= copies,
        f"відрізів = {copies}": data.count(b"\x1dV") == copies,
        "дані надійшли": len(data) > 5000,
    }
    for label, ok in checks.items():
        print(f"{'✅' if ok else '❌'}  {label}")
    print(f"\nВідправлено {len(data)} байт на {host}:{port}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
