"""
Disparo de e-mail automatizado para alertas clínicos do CardioIA.

Lê credenciais SMTP do .env:
  CARDIOIA_SMTP_HOST     ex.: smtp.gmail.com
  CARDIOIA_SMTP_PORT     ex.: 587
  CARDIOIA_SMTP_USER     remetente (e-mail completo)
  CARDIOIA_SMTP_PASS     senha de app (Gmail: app password)
  CARDIOIA_ALERT_TO      destinatário (médico responsável / oncall)

Quando essas variáveis não estão definidas, o módulo opera em modo
"dry-run" — apenas imprime no console como ficaria o e-mail. Isso
permite avaliar o pipeline sem depender de credenciais reais.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from typing import List


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def _build_body(device_id: str, alerts: List[dict], reading: dict) -> str:
    head = (
        f"CardioIA - Alerta clínico\n"
        f"Dispositivo: {device_id}\n"
        f"Timestamp:   {datetime.utcfromtimestamp(reading['ts']).isoformat()}Z\n"
        f"-----------------------------------------------------------\n"
        f"Leitura atual:\n"
        f"  BPM         : {reading['bpm']}\n"
        f"  Temperatura : {reading['temperature']:.1f} °C\n"
        f"  Umidade     : {reading['humidity']:.1f} %\n"
        f"  Movimento   : {reading['movement']:.2f}\n"
        f"-----------------------------------------------------------\n"
        f"Alertas detectados:\n"
    )
    lines = [
        f"  [{a['severity'].upper()}] {a['type']:18s} → {a['message']}"
        for a in alerts
    ]
    foot = (
        "\nRecomendações automáticas:\n"
        "  - Confirmar contato com o paciente em até 5 min.\n"
        "  - Verificar histórico recente no dashboard do Node-RED.\n"
        "  - Acionar SAMU se o critério for de severidade HIGH.\n\n"
        "Este e-mail foi gerado automaticamente pelo CardioIA – Fase 3."
    )
    return head + "\n".join(lines) + foot


def send_alert(device_id: str, alerts: List[dict], reading: dict) -> dict:
    """
    Envia (ou simula o envio de) um alerta por e-mail (versao legada).
    Retorna um dict com `status` e `detail` para o servidor REST repassar.
    """
    if not alerts:
        return {"status": "noop", "detail": "Sem alertas para notificar."}

    host = _env("CARDIOIA_SMTP_HOST") or _env("SMTP_HOST")
    port = int(_env("CARDIOIA_SMTP_PORT", _env("SMTP_PORT", "587")) or 587)
    user = _env("CARDIOIA_SMTP_USER") or _env("SMTP_USER")
    pw   = _env("CARDIOIA_SMTP_PASS") or _env("SMTP_PASS")
    to   = _env("CARDIOIA_ALERT_TO")  or _env("ALERT_TO")

    subject_severity = "HIGH" if any(a["severity"] == "high" for a in alerts) else "MEDIUM"
    subject = f"[CardioIA][{subject_severity}] {device_id} - {len(alerts)} alerta(s)"
    body = _build_body(device_id, alerts, reading)

    if not (host and user and pw and to):
        # Dry-run: nenhum SMTP configurado, so imprime o e-mail.
        print("=" * 64)
        print(f"DRY-RUN  |  Subject: {subject}")
        print("-" * 64)
        print(body)
        print("=" * 64)
        return {
            "status": "dry-run",
            "detail": "Variaveis SMTP nao configuradas; e-mail apenas impresso.",
            "subject": subject,
        }

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls(context=context)
        server.login(user, pw)
        server.send_message(msg)

    return {
        "status": "sent",
        "detail": f"E-mail enviado para {to}",
        "subject": subject,
    }


def send_alert_email(record: dict) -> dict:
    """
    Wrapper moderno usado pelo api_server.py.
    `record` eh o dict salvo pela API e contem:
        device_id, temperature, humidity, bpm, movement, ts, id, risk
    """
    risk = record.get("risk") or {}
    # converte para o formato esperado pela versao legada
    severity = "high" if risk.get("level") == "critical" else "medium"
    alerts = [
        {"type": "clinical", "severity": severity, "message": r}
        for r in risk.get("reasons", []) if r and "dentro dos parametros" not in r
    ]
    ts = record.get("ts")
    if hasattr(ts, "timestamp"):
        ts_epoch = ts.timestamp()
    elif isinstance(ts, (int, float)):
        ts_epoch = float(ts)
    else:
        ts_epoch = datetime.utcnow().timestamp()
    reading = {
        "bpm":         record.get("bpm", 0),
        "temperature": record.get("temperature", 0.0),
        "humidity":    record.get("humidity", 0.0),
        "movement":    record.get("movement", 0.0) or 0.0,
        "ts":          ts_epoch,
    }
    return send_alert(record.get("device_id", "?"), alerts, reading)
