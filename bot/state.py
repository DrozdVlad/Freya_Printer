"""Маленьке сховище для того, що бот дізнається під час роботи."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class State:
    """JSON-файл з налаштуваннями, які бот запамʼятовує сам."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            self._data = json.loads(self.path.read_text("utf-8"))
        except FileNotFoundError:
            self._data = {}
        except (OSError, ValueError) as exc:
            log.warning("Не вдалося прочитати %s: %s", self.path, exc)
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def save(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2),
                           encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("Не вдалося зберегти %s: %s", self.path, exc)
