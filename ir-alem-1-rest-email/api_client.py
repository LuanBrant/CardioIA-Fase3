"""
Cliente REST que simula um ESP32 enviando sinais vitais para o
servidor `api_server.py`.

Uso:
  python api_client.py              # cenário misto (normal + alertas)
  python api_client.py --crisis     # simula crise cardíaca

Os dados são gerados sinteticamente para demonstrar:
  - leitura normal (paciente em repouso)
  - taquicardia
  - febre alta
  - queda / imobilidade prolongada
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from typing import Iterator

import requests


API_URL = "http://127.0.0.1:8000"
DEVICE  = "cardioia-001"


def normal_reading() -> dict:
    return {
        "device_id": DEVICE,
        "bpm": random.randint(60, 95),
        "temperature": round(random.uniform(36.2, 37.2), 2),
        "humidity": round(random.uniform(45, 70), 1),
        "movement": round(random.uniform(0.2, 0.7), 2),
    }


def crisis_reading() -> dict:
    return {
        "device_id": DEVICE,
        "bpm": random.randint(130, 175),
        "temperature": round(random.uniform(38.5, 40.0), 2),
        "humidity": round(random.uniform(80, 95), 1),
        "movement": round(random.uniform(0.0, 0.05), 2),
    }


def mixed_stream(n: int = 12) -> Iterator[dict]:
    """6 leituras normais → 3 leituras de crise → 3 leituras de recuperação."""
    for _ in range(6):
        yield normal_reading()
    for _ in range(3):
        yield crisis_reading()
    for _ in range(3):
        r = normal_reading()
        r["bpm"] = random.randint(95, 110)        # ainda elevado
        r["temperature"] = round(random.uniform(37.5, 37.9), 2)
        yield r


def send_one(reading: dict) -> dict:
    r = requests.post(f"{API_URL}/readings", json=reading, timeout=5)
    r.raise_for_status()
    return r.json()


def show(result: dict) -> None:
    risk = result.get("risk") or {}
    level = risk.get("level", "ok")
    reasons = risk.get("reasons", [])
    icon = "!" if level == "critical" else ("~" if level == "warning" else "v")
    print(f"{icon} [{level:<8}] bpm={result['bpm']:>3} | "
          f"T={result['temperature']:>4.1f}C | "
          f"H={result['humidity']:>4.1f}% | "
          f"mov={result.get('movement', 0):.2f} | "
          f"-> {', '.join(reasons)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cliente REST CardioIA")
    parser.add_argument("--crisis", action="store_true",
                        help="Envia apenas leituras de crise cardíaca")
    parser.add_argument("--n", type=int, default=12,
                        help="Quantidade de leituras (modo misto)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Intervalo entre leituras em segundos")
    parser.add_argument("--api", default=API_URL,
                        help="URL base da API REST")
    args = parser.parse_args()

    global API_URL
    API_URL = args.api

    print(f"==> Enviando leituras para {API_URL}")
    try:
        h = requests.get(f"{API_URL}/health", timeout=3).json()
        print(f"    health: {h}")
    except Exception as exc:
        print(f"!! API indisponível em {API_URL}: {exc}", file=sys.stderr)
        return 1

    stream = (crisis_reading() for _ in range(args.n)) \
             if args.crisis else mixed_stream(args.n)

    for reading in stream:
        try:
            show(send_one(reading))
        except Exception as exc:
            print(f"!! falha ao enviar: {exc}", file=sys.stderr)
        time.sleep(args.interval)

    print("==> Concluído. Inspecione /readings e /alerts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
