#!/usr/bin/env python3
"""Пошук принтера в мережі: сканує порт 9100 у вашій підмережі.

    python3 scripts/discover.py                 # авто-визначення підмережі
    python3 scripts/discover.py 192.168.1       # вручну
"""
import socket
import sys
from concurrent.futures import ThreadPoolExecutor

PORT = 9100


def local_prefix() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return ".".join(probe.getsockname()[0].split(".")[:3])
    finally:
        probe.close()


def check(ip: str) -> str | None:
    try:
        with socket.create_connection((ip, PORT), timeout=0.6):
            return ip
    except OSError:
        return None


def main() -> int:
    prefix = sys.argv[1] if len(sys.argv) > 1 else local_prefix()
    print(f"Сканую {prefix}.1-254 на порт {PORT}…")
    hosts = [f"{prefix}.{i}" for i in range(1, 255)]
    with ThreadPoolExecutor(max_workers=128) as pool:
        found = [ip for ip in pool.map(check, hosts) if ip]
    if not found:
        print("Нічого не знайдено. Перевірте кабель/мережу принтера.")
        return 1
    print("\nЗнайдено пристрої з відкритим 9100:")
    for ip in found:
        print(f"  PRINTER_HOST={ip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
