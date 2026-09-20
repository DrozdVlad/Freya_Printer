#!/usr/bin/env python3
"""Згенерувати PNG-прев'ю записки без принтера.

    python3 scripts/preview.py            # демо-дані
    python3 scripts/preview.py out.png "Іван Петренко" "Марія Коваль"
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config
from bot.render import Receipt, render_receipt
from bot.texts import PROCEDURES

cfg = load_config()
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/preview.png")
names = sys.argv[2:] or ["Іван Петренко", "Марія Коваль-Оксентіївська", "Олег Сидоренко"]

receipt = Receipt(
    procedure_title=PROCEDURES[0].title,
    when=datetime(2026, 9, 21, 9, 30),
    names=list(names),
)
img = render_receipt(cfg, receipt)
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out)
print(f"{out}  —  {img.width}×{img.height} px")
