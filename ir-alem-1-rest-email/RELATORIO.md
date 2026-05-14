# Relatório – Ir Além 1 – REST + E-mail (CardioIA Fase 3)

**Aluno:** Luan Brant
**Módulo:** Comunicação automatizada com REST e e-mail (RPA na saúde)
**Stack:** Python 3.11 + FastAPI + Uvicorn + Pydantic + smtplib

---

## 1. Objetivo

Construir um serviço Python que:

1. **Receba sinais vitais** de pacientes via API REST (HTTP/JSON);
2. **Avalie risco clínico** com regras alinhadas com o firmware Edge
   (Partes 1 e 2);
3. **Dispare e-mail automatizado** para a equipe médica em caso de
   alerta;
4. **Exponha consultas** sobre histórico de leituras e alertas.

A integração demonstra como **conectar IoT a RPA na saúde**, expandindo
o pipeline `ESP32 → MQTT → Dashboard` para `ESP32 → REST → Triagem → E-mail`.

## 2. Arquitetura

```
   +---------+   POST /readings   +-------------+
   | ESP32   |  ----------------> | api_server  |
   | Wokwi   |   (HTTP/JSON)      |  (FastAPI)  |
   +---------+                    +------+------+
                                         |
                              +----------+----------+
                              |                     |
                       risk_engine.classify   email_alert.send_alert
                       (regras clinicas)       (SMTP TLS / dry-run)
                              |                     |
                              v                     v
                        deque em memoria        Caixa do medico
                        (readings + alerts)
```

## 3. Componentes

### 3.1 `api_server.py`

FastAPI expondo:

| Método | Rota          | Comportamento                                  |
|--------|---------------|------------------------------------------------|
| `GET`  | `/health`     | Retorna `{status, readings, alerts}`           |
| `POST` | `/readings`   | Persiste leitura, classifica, dispara e-mail   |
| `GET`  | `/readings`   | Últimas N leituras (`?limit=`)                 |
| `GET`  | `/alerts`     | Últimos alertas detectados                     |
| `DEL`  | `/readings`   | Limpa armazenamento (utilitário de teste)      |

Armazenamento em `collections.deque(maxlen=500)` — suficiente para o
protótipo. Em produção esse mesmo módulo plugaria em InfluxDB/Postgres.

Documentação Swagger gerada automaticamente em
**http://127.0.0.1:8000/docs**.

### 3.2 `risk_engine.py`

Motor de classificação clínica com **duas APIs públicas**:

- **`classify(temperature, humidity, bpm, movement) -> RiskAssessment`** —
  retorna `level ∈ {ok, warning, critical}`, lista de motivos e score 0-10.
- **`assess(Reading) -> List[dict]`** — versão lista, mantida para
  compatibilidade com clientes anteriores.

Regras implementadas (limiares alinhados com o firmware ESP32):

| Critério                              | Severidade |
|---------------------------------------|------------|
| BPM > 120                             | critical   |
| BPM < 40                              | critical   |
| BPM > 100                             | warning    |
| Temperatura > 38 °C                   | critical   |
| Temperatura > 37,5 °C                 | warning    |
| Temperatura < 35 °C                   | critical   |
| Umidade > 85 %                        | warning    |
| Movimento < 0,05 e BPM < 50           | critical (suspeita de síncope) |
| Movimento < 0,05 (outros casos)       | warning    |
| Movimento > 0,9 e BPM > 120           | warning    |

O score é a **soma das contribuições de cada regra** (capada em 10) — útil
para ordenar alertas em uma fila de triagem ou alimentar um modelo de IA
secundário (ex.: Ir Além 2).

### 3.3 `email_alert.py`

Encapsula o envio SMTP via `smtplib` + `EmailMessage`:

- Lê credenciais de variáveis de ambiente
  `CARDIOIA_SMTP_HOST/PORT/USER/PASS` e `CARDIOIA_ALERT_TO`.
- **Fallback dry-run**: se qualquer variável estiver ausente, o módulo
  apenas imprime o e-mail formatado no console. Isso é fundamental
  para apresentar o projeto sem expor credenciais reais nem ficar
  refém de redes que bloqueiam a porta 587.
- Em modo real usa `STARTTLS` + autenticação com app-password (Gmail).
- Retorna `{status, detail, subject}` para a API REST registrar o
  resultado no `alerts_store`.

Conteúdo gerado (exemplo):

```
Subject: [CardioIA][HIGH] cardioia-001 - 2 alerta(s)

CardioIA - Alerta clínico
Dispositivo: cardioia-001
Timestamp:   2026-05-14T12:30:11Z
-----------------------------------------------------------
Leitura atual:
  BPM         : 138
  Temperatura : 38.9 °C
  Umidade     : 88.0 %
  Movimento   : 0.10
-----------------------------------------------------------
Alertas detectados:
  [HIGH]   tachycardia        → Taquicardia detectada (138 bpm).
  [HIGH]   fever              → Febre detectada (38.9 °C).

Recomendações automáticas:
  - Confirmar contato com o paciente em até 5 min.
  - Verificar histórico recente no dashboard do Node-RED.
  - Acionar SAMU se o critério for de severidade HIGH.
```

### 3.4 `api_client.py`

Simula um ESP32 enviando dados sintéticos:

- 6 leituras normais (BPM 60-95, T 36.2-37.2)
- 3 leituras de crise (BPM 130-175, T 38.5-40, mov ≈ 0 — paciente caído)
- 3 leituras de recuperação (BPM 95-110, T 37.5-37.9)

Cada `POST /readings` imprime no console:
```
✓ bpm= 78 | T=36.7°C | H=55.0% | mov=0.40 | alerts=[]
⚠ bpm=143 | T=39.1°C | H=88.0% | mov=0.02 | alerts=['clinical_alert']
```

## 4. Fluxo end-to-end

1. **Aluno (ou ESP32) chama** `POST /readings`.
2. **FastAPI valida** o payload com Pydantic 2 (intervalos físicos
   plausíveis).
3. **`risk_engine.classify`** roda em `O(1)` e devolve o `RiskAssessment`.
4. **`risk_engine.assess`** transforma em lista de alertas (formato
   legado consumido pelo `email_alert`).
5. Se houver alertas, **`email_alert.send_alert`** monta o corpo HTML
   simples e envia (ou imprime, em dry-run).
6. Resposta HTTP retorna leitura + lista de alertas, e o evento fica
   gravado em `/alerts` para consulta posterior.

## 5. Demonstração rápida (sem SMTP)

```bash
# Janela 1
uvicorn api_server:app --reload --port 8000

# Janela 2
python api_client.py
```

Saída esperada na janela 1 (quando o cliente envia uma leitura de crise):

```
================================================================
DRY-RUN  |  Subject: [CardioIA][HIGH] cardioia-001 - 1 alerta(s)
----------------------------------------------------------------
CardioIA - Alerta clínico
...
================================================================
INFO:     127.0.0.1:54920 - "POST /readings HTTP/1.1" 200 OK
```

E `curl http://127.0.0.1:8000/alerts | jq` lista o evento persistido.

## 6. Segurança e privacidade

- **Credenciais nunca no repositório**: somente em `.env` (gitignored).
- **App-passwords no Gmail**: substituem a senha principal.
- **Pseudonimização**: o `device_id` é o único identificador transmitido;
  o servidor REST não recebe nem armazena PII (nome, CPF, prontuário).
- **TLS obrigatório em produção**: o módulo já usa `starttls()` com
  `ssl.create_default_context()`.
- **Rate limiting** ficou de fora do MVP, mas é o próximo passo
  recomendado (ex.: `slowapi`) para evitar spam de alertas e proteger o
  servidor SMTP.

## 7. Conclusão

A entrega cobre integralmente os entregáveis do **Ir Além 1**:
1. Consumo correto de API REST (server + client funcionais).
2. Motor de risco clínico bem definido, com unidades e severidades
   explícitas e alinhamento com o firmware Edge da Parte 1.
3. Disparo de e-mail funcional, com fallback dry-run para
   apresentações.
4. Código limpo, separação de camadas (`server / engine / alert /
   client`) e instruções de execução em `README.md`.
