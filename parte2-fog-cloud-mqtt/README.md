# Parte 2 — Fog / Cloud Computing (MQTT + Node-RED)

ESP32 publica sinais vitais via MQTT em um broker público (HiveMQ) e o
Node-RED consome esses tópicos para exibir um **dashboard em tempo real**
com gráficos, gauges, indicador de alerta e notificações toast.

## Arquivos

| Arquivo                 | Propósito                                                |
|-------------------------|----------------------------------------------------------|
| `sketch.ino`            | Firmware ESP32 para Wokwi Web                            |
| `src/main.cpp`          | Mesma fonte para PlatformIO                              |
| `diagram.json`          | Circuito Wokwi (ESP32 + DHT22 + botão + 2 LEDs)          |
| `libraries.txt`         | Dependências do Wokwi Web                                |
| `platformio.ini`        | Build PlatformIO local                                   |
| `wokwi.toml`            | Apontamento Wokwi → binário PIO                          |
| `node-red-flow.json`    | Flow completo do dashboard (import direto no Node-RED)   |
| `RELATORIO.md`          | Relatório técnico (≥ 2 páginas)                          |

## Tópicos MQTT publicados

| Tópico                                       | Conteúdo                                          |
|----------------------------------------------|---------------------------------------------------|
| `cardioia/cardioia-001/telemetry`            | JSON `{ts, temperature, humidity, bpm, alert}`    |
| `cardioia/cardioia-001/alert` (retained)     | JSON `{device, ts, bpm, temp, humidity, reason}`  |
| `cardioia/cardioia-001/cmd` (subscribe)      | Comandos remotos (ex.: `blink` pisca LED de ACK)  |

## Executar no Wokwi Web

1. Crie o projeto em <https://wokwi.com/projects/new/esp32>.
2. Cole `sketch.ino`, `diagram.json` e `libraries.txt` nas abas
   correspondentes.
3. ▶ Iniciar simulação. A serial vai mostrar `[WIFI] OK` e `[MQTT] OK`.
4. Pressione o botão **vermelho** para gerar batimentos. Ajuste a
   temperatura do DHT22 clicando no componente.

## Importar o dashboard no Node-RED

```bash
# Instalar Node-RED localmente (uma vez)
npm install -g --unsafe-perm node-red

# Dashboard
cd ~/.node-red && npm install node-red-dashboard

# Iniciar
node-red
# Abre http://127.0.0.1:1880
```

No editor, **Menu → Import → cole o conteúdo de `node-red-flow.json`** e
**Deploy**. O dashboard fica em **http://127.0.0.1:1880/ui**.

Há um nó **`inject`** chamado *"Teste sem ESP32"* que injeta payloads de
exemplo a cada 5 s — útil para validar o dashboard mesmo sem o Wokwi
rodando.

## Usar HiveMQ Cloud (TLS) em vez do broker público

No `sketch.ino` substitua:

```cpp
const char* MQTT_HOST = "<sua-instancia>.s2.eu.hivemq.cloud";
const int   MQTT_PORT = 8883;
const char* MQTT_USER = "<usuario>";
const char* MQTT_PASS = "<senha>";
```

E troque `WiFiClient` por `WiFiClientSecure` (carregando o cert. root da
LetsEncrypt), conforme exemplo do RELATORIO.md.

## Prints / Evidências

Salve seus prints em `../docs/images/` com os nomes sugeridos abaixo
(referenciados pelo relatório):

- `wokwi-running.png` — simulador em execução com Serial Monitor
- `node-red-flow.png` — flow do Node-RED no editor
- `node-red-dashboard.png` — dashboard `/ui` recebendo dados
- `mqtt-explorer.png` — opcional: tópicos vistos no MQTT Explorer
