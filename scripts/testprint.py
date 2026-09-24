#!/usr/bin/env python3
"""Тестовий друк на реальному принтері (бере налаштування з .env).

    python3 scripts/testprint.py           # 1 копія
    python3 scripts/testprint.py 2         # 2 копії
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config
from bot.printing import check_printer, print_image
from bot.render import Receipt, render_receipt
from bot.texts import PROCEDURES


async def main() -> int:
    cfg = load_config()
    copies = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"Принтер: {cfg.describe_printer()}")
    try:
        print("Зв'язок:", await check_printer(cfg))
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Принтер недоступний: {exc}")
        return 1

    receipt = Receipt(
        procedure_title=PROCEDURES[1].title,
        when=datetime.now().date(),
        printed_at=datetime.now().replace(second=0, microsecond=0),
        names=["Тестове Ім'я", "Друге Ім'я"],
    )
    await print_image(cfg, render_receipt(cfg, receipt), copies)
    print(f"✅ Надруковано копій: {copies}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
