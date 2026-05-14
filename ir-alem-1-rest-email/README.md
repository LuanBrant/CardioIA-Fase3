# Ir Além 1 — REST + E-mail automatizado (CardioIA)

Pipeline Python que recebe sinais vitais via API REST, executa um motor
de risco clínico e dispara e-mail automatizado quando há alerta
(taquicardia, febre, imobilidade, sudorese, etc.).

## Arquivos

| Arquivo            | Função                                                          |
|--------------------|-----------------------------------------------------------------|
| `api_server.py`    | Servidor FastAPI (`POST /readings`, `GET /readings`, `/alerts`) |
| `api_client.py`    | Cliente que simula um ESP32 enviando dados                      |
| `risk_engine.py`   | Motor de classificação clínica (modern + legacy APIs)           |
| `email_alert.py`   | Disparo SMTP (Gmail / qualquer relay) com fallback dry-run       |
| `requirements.txt` | Dependências                                                    |
| `.env.example`     | Modelo de configuração SMTP                                     |
| `RELATORIO.md`     | Relatório técnico (1-2 páginas)                                 |

## Como rodar

```bash
cd ir-alem-1-rest-email
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) servidor REST
uvicorn api_server:app --reload --port 8000
# (em outro terminal)

# 2) cliente simulando ESP32
python api_client.py             # cenário misto (normal + crise + recuperação)
python api_client.py --crisis    # só crises cardíacas
```

Endpoints disponíveis:
- `POST /readings`       → recebe leitura, classifica e dispara e-mail
- `GET  /readings?limit=50` → últimas leituras
- `GET  /alerts`         → histórico de alertas detectados
- `GET  /health`         → healthcheck

Documentação interativa em **http://127.0.0.1:8000/docs** (Swagger UI).

## Configurar SMTP

Copie `.env.example` para `.env` e preencha. Sem essas variáveis, o
módulo `email_alert.py` entra em **dry-run** e apenas imprime o e-mail
no console — perfeito para apresentação sem expor credenciais.

Para Gmail é preciso gerar uma **App Password** em
<https://myaccount.google.com/apppasswords> (a senha normal não funciona
com 2FA).

## Integração com o ESP32 (Partes 1 e 2)

O firmware da Parte 2 pode publicar no MQTT *e* fazer `POST /readings`
via HTTP. Para isso, basta adicionar `HTTPClient.h` ao `sketch.ino` e
chamar a API a cada leitura:

```cpp
HTTPClient http;
http.begin("http://<seu-ip>:8000/readings");
http.addHeader("Content-Type", "application/json");
http.POST(payload);
```

Outra opção (mais elegante) é usar o **Node-RED da Parte 2** como ponte:
um nó `http request` consumindo o tópico MQTT e chamando esta API.
