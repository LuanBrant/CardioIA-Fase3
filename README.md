# CardioIA – Fase 3: Monitoramento Contínuo (IoT na Saúde)

Projeto da disciplina **IoT na Saúde – FIAP**, fase 3 do CardioIA.
Integra **Edge Computing**, **Fog/Cloud Computing**, **dashboards** e
duas trilhas "Ir Além" (REST + Email automatizado e IA em séries
temporais), demonstrando o pipeline completo
**captura → processamento → transmissão → visualização → alerta** de um
wearable cardiológico.

> **Autor:** Luan Brant
> **Disciplina:** IoT na Saúde – Fase 3 (CardioIA)
> **Instituição:** FIAP

---

## Estrutura do repositório

```
CardioIA-Fase3/
├── parte1-edge-computing/          # ESP32 + DHT22 + cache offline (Wokwi)
├── parte2-fog-cloud-mqtt/          # MQTT (HiveMQ) + Dashboard Node-RED
├── ir-alem-1-rest-email/           # API REST + automação de email
├── ir-alem-2-ia-series-temporais/  # LogReg vs LIF neuromórfico
├── docs/images/                    # prints / evidências
└── README.md                       # este arquivo
```

Cada subpasta tem seu próprio **`README.md`** (como rodar) e
**`RELATORIO.md`** (entregável de relatório técnico).

---

## Mapeamento dos entregáveis pedidos pelo enunciado

### Parte 1 – Edge Computing
- ✅ Link do projeto no Wokwi → **adicionar manualmente** em
  `parte1-edge-computing/README.md` após salvar no Wokwi Web.
- ✅ Código C++ comentado: [`parte1-edge-computing/src/main.cpp`](parte1-edge-computing/src/main.cpp)
  e [`parte1-edge-computing/sketch.ino`](parte1-edge-computing/sketch.ino).
- ✅ Relatório (≥ 1 página): [`parte1-edge-computing/RELATORIO.md`](parte1-edge-computing/RELATORIO.md).

### Parte 2 – Fog/Cloud + Dashboard
- ✅ Código ESP32 (MQTT): [`parte2-fog-cloud-mqtt/sketch.ino`](parte2-fog-cloud-mqtt/sketch.ino).
- ✅ Export do dashboard Node-RED: [`parte2-fog-cloud-mqtt/node-red-flow.json`](parte2-fog-cloud-mqtt/node-red-flow.json).
- ✅ Relatório (≥ 2 páginas): [`parte2-fog-cloud-mqtt/RELATORIO.md`](parte2-fog-cloud-mqtt/RELATORIO.md).
- 🖼  Prints → você precisa **gerar manualmente** rodando o Node-RED
  e salvando em `docs/images/`.

### Ir Além 1 – REST + Email
- ✅ Cliente + servidor REST: [`ir-alem-1-rest-email/`](ir-alem-1-rest-email/).
- ✅ Motor de risco clínico: [`ir-alem-1-rest-email/risk_engine.py`](ir-alem-1-rest-email/risk_engine.py).
- ✅ Disparo de e-mail (com modo dry-run): [`ir-alem-1-rest-email/email_alert.py`](ir-alem-1-rest-email/email_alert.py).
- ✅ Relatório: [`ir-alem-1-rest-email/RELATORIO.md`](ir-alem-1-rest-email/RELATORIO.md).

### Ir Além 2 – IA em séries temporais
- ✅ Notebook comentado: [`ir-alem-2-ia-series-temporais/cardioia_timeseries.ipynb`](ir-alem-2-ia-series-temporais/cardioia_timeseries.ipynb).
- ✅ Implementação LogReg vs LIF neuromórfico.
- ✅ Relatório comparativo: [`ir-alem-2-ia-series-temporais/RELATORIO.md`](ir-alem-2-ia-series-temporais/RELATORIO.md).
- 🎥 Vídeo YouTube (até 4 min, "não listado") → **gravar manualmente**.

---

## Pipeline completo (visão de arquitetura)

```
   +-----------+           +--------------+           +--------------+
   |  ESP32    |  MQTT     |  HiveMQ      |  MQTT     |  Node-RED    |
   |  Wearable | --------> |  Broker      | --------> |  Dashboard   |
   |  (P1+P2)  |           |  (Fog)       |           |  (Cloud UI)  |
   +-----+-----+           +------+-------+           +--------------+
         |                        |
         | Edge buffer            | MQTT bridge
         | offline (P1)           v
         |                 +--------------+           +--------------+
         |                 |  FastAPI     |  HTTP     |  SMTP relay  |
         |                 |  (Ir Alem 1) | --------> |  (alerta)    |
         |                 +------+-------+           +--------------+
         |                        |
         |                        |  serializa em CSV / dataset
         |                        v
         |                 +--------------+
         +---------------> |  Notebook IA |
                           |  LogReg vs   |
                           |  LIF (P-IA2) |
                           +--------------+
```

---

## Como rodar **tudo** localmente

```bash
# 1) Parte 1 (Wokwi Web)
#    Acesse https://wokwi.com/projects/new/esp32
#    Cole o conteudo de parte1-edge-computing/sketch.ino
#    Cole o diagram.json e libraries.txt nas abas correspondentes
#    Run

# 2) Parte 2 (Wokwi + Node-RED)
#    a) Mesma coisa para parte2-fog-cloud-mqtt/
#    b) npm install -g --unsafe-perm node-red node-red-dashboard
#       node-red
#       -> http://127.0.0.1:1880  -> Menu Import -> cole node-red-flow.json
#       -> http://127.0.0.1:1880/ui (dashboard)

# 3) Ir Alem 1 (FastAPI + email)
cd ir-alem-1-rest-email
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # (opcional) preencha SMTP, ou rode em dry-run
uvicorn api_server:app --reload
# em outro terminal:
python api_client.py             # cenario misto
python api_client.py --crisis    # crise cardiaca

# 4) Ir Alem 2 (Notebook)
cd ../ir-alem-2-ia-series-temporais
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook cardioia_timeseries.ipynb
```

---

## Critérios de avaliação atendidos

| Critério                                                  | Onde está coberto                                    |
|-----------------------------------------------------------|------------------------------------------------------|
| Leitura de sensores (DHT22 + 2º sensor)                   | Partes 1 e 2: DHT22 + botão simulando pulso          |
| Resiliência offline (Edge Computing)                      | Parte 1: buffer circular + flush-on-reconnect        |
| Envio via MQTT e integração com broker                    | Parte 2: HiveMQ + tópicos versionados                |
| Dashboard funcional e alertas automáticos                 | Parte 2: Node-RED com gauges, charts, LEDs, toasts   |
| Documentação clara (código + relatórios)                  | README + RELATORIO em cada subpasta                  |
| **Ir Além 1** – API REST + email + lógica de risco         | `ir-alem-1-rest-email/`                              |
| **Ir Além 2** – Comparativo IA (clássica vs neuromórfica)  | `ir-alem-2-ia-series-temporais/`                     |

---

## O que ainda depende de ação manual sua

Veja a seção dedicada na conversa com o Claude (também resumida no
arquivo [`INSTRUCOES_MANUAIS.md`](INSTRUCOES_MANUAIS.md)).
