#!/usr/bin/env python3
"""Згенерувати PNG-прев'ю записки без принтера.

    python3 scripts/preview.py            # демо-дані
    python3 scripts/preview.py out.png "Іван Петренко" "Марія Коваль"
    python3 scripts/preview.py out.png 19   # 19 демо-імен → 2 аркуші
"""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config
from bot.render import Receipt, preview_frame, render_pages
from bot.texts import PROCEDURES

cfg = load_config()
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/preview.png")
names = sys.argv[2:] or ["Іван Петренко", "Марія Коваль-Оксентіївська", "Олег Сидоренко"]
if len(names) == 1 and names[0].isdigit():
    names = [f"Ім'я Прізвище {i}" for i in range(1, int(names[0]) + 1)]

receipt = Receipt(
    procedure_title=PROCEDURES[0].title,
    when=date(2026, 12, 20),
    printed_at=datetime.now().replace(second=0, microsecond=0),
    names=list(names),
)
pages = render_pages(cfg, receipt)
img = preview_frame(pages)
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out)
print(f"{out}  —  аркушів: {len(pages)}, кожен {pages[0].width}×{pages[0].height} px")
