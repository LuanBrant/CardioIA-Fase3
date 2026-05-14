"""
CardioIA - logica de classificacao de risco clinico em sinais vitais.

Regras (alinhadas com o firmware Edge da Parte 1):
    febre        : T > 38 C
    febricula    : T > 37.5 C
    hipotermia   : T < 35 C
    taquicardia  : BPM > 120
    bradicardia  : BPM < 40
    sudorese     : umidade > 85 %
    inatividade  : ausencia prolongada de movimento (proxy de queda/sincope)

Cada regra atribui um "level"; a regra mais grave prevalece.

A API publica `classify(...)` que retorna um `RiskAssessment`
(Pydantic) consumido pela camada REST. Tambem mantemos `assess(Reading)`
para compatibilidade com clientes que ja usavam a versao baseada em
dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal

from pydantic import BaseModel

Level = Literal["ok", "warning", "critical"]

# ----------------------------------------------------------------------
# Limiares clinicos (alinhados com o firmware ESP32)
# ----------------------------------------------------------------------
BPM_TACHY_LIMIT      = 120
BPM_BRADY_LIMIT      = 40
BPM_ELEVATED         = 100
TEMP_FEVER_LIMIT     = 38.0
TEMP_FEVERICULE      = 37.5
TEMP_HYPOTHERMIA     = 35.0
HUMIDITY_SWEAT       = 85.0
MOVEMENT_FALL_LIMIT  = 0.05
MOVEMENT_HIGH_LIMIT  = 0.9


# ----------------------------------------------------------------------
# API moderna (Pydantic) usada pelo api_server.py
# ----------------------------------------------------------------------
class RiskAssessment(BaseModel):
    level: Level
    reasons: list[str]
    score: int  # 0..10, quanto maior mais critico


def _max_level(a: Level, b: Level) -> Level:
    order = {"ok": 0, "warning": 1, "critical": 2}
    return a if order[a] >= order[b] else b


def classify(
    *,
    temperature: float,
    humidity: float,
    bpm: int,
    movement: float = 0.0,
) -> RiskAssessment:
    """Classifica uma leitura conforme regras clinicas configuradas."""
    reasons: list[str] = []
    score = 0
    level: Level = "ok"

    if bpm > BPM_TACHY_LIMIT:
        reasons.append(f"taquicardia (BPM={bpm})")
        score += 5
        level = "critical"
    elif 0 < bpm < BPM_BRADY_LIMIT:
        reasons.append(f"bradicardia (BPM={bpm})")
        score += 5
        level = "critical"
    elif bpm > BPM_ELEVATED:
        reasons.append(f"BPM elevado ({bpm})")
        score += 2
        level = _max_level(level, "warning")

    if temperature > TEMP_FEVER_LIMIT:
        reasons.append(f"febre (T={temperature:.1f}C)")
        score += 4
        level = "critical"
    elif temperature > TEMP_FEVERICULE:
        reasons.append(f"febricula (T={temperature:.1f}C)")
        score += 1
        level = _max_level(level, "warning")
    elif temperature < TEMP_HYPOTHERMIA:
        reasons.append(f"hipotermia (T={temperature:.1f}C)")
        score += 4
        level = "critical"

    if humidity > HUMIDITY_SWEAT:
        reasons.append(f"sudorese intensa (H={humidity:.0f}%)")
        score += 2
        level = _max_level(level, "warning")

    if movement < MOVEMENT_FALL_LIMIT:
        # imobilidade prolongada com BPM baixo eh muito sugestivo de sincope
        if bpm < 50:
            reasons.append("imobilidade + BPM baixo (possivel sincope)")
            score += 4
            level = "critical"
        else:
            reasons.append("ausencia prolongada de movimento")
            score += 2
            level = _max_level(level, "warning")
    elif movement > MOVEMENT_HIGH_LIMIT and bpm > BPM_TACHY_LIMIT:
        reasons.append("atividade intensa + taquicardia")
        score += 2
        level = _max_level(level, "warning")

    if not reasons:
        reasons.append("sinais vitais dentro dos parametros")

    return RiskAssessment(level=level, reasons=reasons, score=min(score, 10))


# ----------------------------------------------------------------------
# API legada (dataclass) - mantida para compatibilidade
# ----------------------------------------------------------------------
@dataclass
class Reading:
    device_id: str
    bpm: int
    temperature: float
    humidity: float
    movement: float   # 0..1 (0 = imovel, 1 = atividade intensa)
    ts: float         # epoch seconds


def assess(reading: Reading) -> List[dict]:
    """Retorna alertas detectados em formato lista (versao legada)."""
    r = classify(
        temperature=reading.temperature,
        humidity=reading.humidity,
        bpm=reading.bpm,
        movement=reading.movement,
    )
    if r.level == "ok":
        return []
    return [
        {
            "type": "clinical_alert",
            "severity": "high" if r.level == "critical" else "medium",
            "message": "; ".join(r.reasons),
        }
    ]
