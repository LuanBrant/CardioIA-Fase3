"""
Servidor REST do CardioIA (Ir Além 1).

Expõe:
  POST /readings      Recebe uma leitura do ESP32/cliente e:
                        - persiste em memória (deque de 500)
                        - executa o motor de risco
                        - dispara e-mail automatizado em caso de alerta
  GET  /readings      Devolve as últimas N leituras (?limit=)
  GET  /alerts        Devolve o histórico de alertas detectados
  GET  /health        Healthcheck

Executar:
  pip install -r requirements.txt
  uvicorn api_server:app --reload --port 8000
"""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from risk_engine import Reading, assess, classify, RiskAssessment
from email_alert import send_alert


class ReadingIn(BaseModel):
    device_id: str = Field(..., examples=["cardioia-001"])
    bpm: int = Field(..., ge=0, le=300)
    temperature: float = Field(..., ge=15.0, le=45.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    movement: float = Field(0.5, ge=0.0, le=1.0)
    ts: Optional[float] = None


class ReadingOut(ReadingIn):
    alerts: List[dict]
    risk: RiskAssessment


app = FastAPI(
    title="CardioIA – API REST de Monitoramento Cardiológico",
    description="Serviço Python que consome dados do ESP32, executa o motor "
                "de risco e dispara e-mails automatizados.",
    version="1.0.0",
)

readings_store: Deque[dict] = deque(maxlen=500)
alerts_store: Deque[dict] = deque(maxlen=200)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "readings": len(readings_store),
            "alerts": len(alerts_store)}


@app.post("/readings", response_model=ReadingOut)
def post_reading(payload: ReadingIn) -> ReadingOut:
    ts = payload.ts if payload.ts is not None else time.time()
    r = Reading(
        device_id=payload.device_id,
        bpm=payload.bpm,
        temperature=payload.temperature,
        humidity=payload.humidity,
        movement=payload.movement,
        ts=ts,
    )
    risk = classify(
        temperature=r.temperature,
        humidity=r.humidity,
        bpm=r.bpm,
        movement=r.movement,
    )
    alerts = assess(r)
    record = {
        "device_id": r.device_id,
        "bpm": r.bpm,
        "temperature": r.temperature,
        "humidity": r.humidity,
        "movement": r.movement,
        "ts": r.ts,
        "alerts": alerts,
        "risk": risk.model_dump(),
    }
    readings_store.append(record)

    if alerts:
        email_result = send_alert(r.device_id, alerts, record)
        alerts_store.append({
            "device_id": r.device_id,
            "ts": r.ts,
            "alerts": alerts,
            "email": email_result,
        })

    return ReadingOut(**record)


@app.get("/readings")
def list_readings(limit: int = Query(50, ge=1, le=500)) -> List[dict]:
    data = list(readings_store)
    return data[-limit:]


@app.get("/alerts")
def list_alerts(limit: int = Query(50, ge=1, le=200)) -> List[dict]:
    data = list(alerts_store)
    return data[-limit:]


@app.delete("/readings")
def clear() -> dict:
    """Util para testes: limpa o histórico em memória."""
    readings_store.clear()
    alerts_store.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
