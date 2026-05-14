# Relatório – Parte 2 (Fog & Cloud com MQTT) – CardioIA Fase 3

**Aluno:** Luan Brant
**Projeto:** CardioIA – Monitoramento Contínuo / IoT na Saúde
**Componentes:** ESP32 + DHT22 + botão + 2 LEDs / HiveMQ / Node-RED

---

## 1. Objetivo

Estender o nó Edge construído na Parte 1 acoplando a ele a camada
**Fog/Cloud**, de modo que os sinais vitais sejam:

1. **Transmitidos** para um broker MQTT (HiveMQ);
2. **Consumidos** por um *gateway* de aplicação (Node-RED);
3. **Visualizados** em um dashboard com gráficos, *gauges* e alertas
   automáticos.

Esta arquitetura representa o ciclo IoT médico completo:
`captura → processamento → transmissão → visualização → alerta`.

## 2. Arquitetura

```
 +------------+        MQTT pub          +-----------+      MQTT sub      +-----------+
 |  ESP32     | -----------------------> |   HiveMQ  | -----------------> |  Node-RED |
 |  CardioIA  |   cardioia/<id>/telem    | (broker)  |  cardioia/<id>/*   |  Dashboard|
 |            | <----------------------- |           | <----------------- |  + alerts |
 +------------+        MQTT sub          +-----------+   cardioia/<id>/cmd+-----------+
   sensores             cardioia/<id>/cmd
   - DHT22                                                                ^
   - botao BPM                                                            |
                                                                          v
                                                              Grafana (opcional)
```

### 2.1 Broker

O firmware aponta por padrão para o broker público **broker.hivemq.com:1883**,
o que permite avaliar o protótipo sem credenciais. Trocando 5 linhas de
configuração no `sketch.ino` ele opera contra **HiveMQ Cloud** em TLS 8883
com usuário/senha – pronto para produção.

### 2.2 Tópicos

| Tópico                                | Direção         | Conteúdo                                                       |
|----------------------------------------|------------------|----------------------------------------------------------------|
| `cardioia/<deviceId>/telemetry`        | ESP32 → Broker   | JSON com `temperature`, `humidity`, `bpm`, `alert`, `ts`       |
| `cardioia/<deviceId>/alert`            | ESP32 → Broker   | JSON `retained` somente em condição de alerta + motivo         |
| `cardioia/<deviceId>/cmd`              | Broker → ESP32   | comandos remotos (ex.: `{"action":"blink"}`)                   |

O uso de **retained=true** no tópico `alert` garante que um cliente que se
conecta após o evento ainda receba o último estado clínico do paciente
imediatamente – característica fundamental para o oncall médico.

### 2.3 Formato do payload

```json
{
  "device": "cardioia-001",
  "ts": 14523,
  "temperature": 37.5,
  "humidity": 58.0,
  "bpm": 132,
  "alert": true
}
```

JSON serializado com **ArduinoJson 7** – idêntico ao formato usado pela
Parte 1, o que mantém a compatibilidade ponta-a-ponta.

## 3. Fluxo de comunicação MQTT

1. No `setup()`, o ESP32 conecta ao Wi-Fi (no Wokwi usa o SSID aberto
   `Wokwi-GUEST`).
2. Inicia o `PubSubClient` e tenta `connect()` no broker; em caso de
   falha, faz *retry* a cada 2 s. Quando bem-sucedido, faz
   `subscribe(cardioia/<id>/cmd)`.
3. A cada **2 s** o `loop()` lê DHT22 e BPM calculado por janela móvel.
4. Constrói o JSON e chama `mqtt.publish(topicTelemetry, payload)`.
5. Se houver condição de alerta clínico (febre, taquicardia, bradicardia
   ou sudorese), publica também em `cardioia/<id>/alert` com `retained=true`
   e o campo `reason` listando os critérios violados.
6. `mqtt.loop()` é chamado a cada iteração para manter o keepalive e
   processar callbacks de mensagens recebidas (ex.: comando "blink" que
   pisca o LED de alerta como ACK visual).

### 3.1 Resiliência de rede

A função `connectWiFi()` é chamada novamente sempre que
`WiFi.status() != WL_CONNECTED`. O mesmo vale para `connectMQTT()`. Em
um produto real, esse trecho seria combinado com o **buffer offline da
Parte 1** – os arquivos do buffer seriam re-publicados em ordem assim
que `mqtt.connected()` retornasse `true`.

## 4. Dashboard Node-RED

O arquivo `node-red-flow.json` contém o flow completo, pronto para
importar (menu → Import → Clipboard). Atende todos os elementos
exigidos pelo enunciado:

| Elemento                            | Implementação no flow                                              |
|--------------------------------------|--------------------------------------------------------------------|
| **Gráfico de sinal vital escolhido** | `ui_chart` "Grafico BPM" (linha) – janela móvel de 10 min          |
| **Gráfico complementar**             | `ui_chart` "Grafico Temperatura"                                   |
| **Medidor (gauge)**                  | `ui_gauge` "Temperatura" + `ui_gauge` "Umidade" + `ui_gauge` BPM   |
| **Indicador de alerta**              | `ui_text` "LED Alerta" (cor verde/vermelho) + `ui_toast` (popup)   |
| **Limites configuráveis**            | Funções `Limites BPM` e `Limites Temp`                             |
| **Sub no MQTT alert**                | `mqtt in` + `Formata alerta MQTT` + debug + toast                  |

### 4.1 Layout do dashboard (http://127.0.0.1:1880/ui)

```
┌──────────────────────────────────────────────────────────────────┐
│ CardioIA Dashboard – Paciente cardioia-001                       │
├──────────────────────────────────────────────────────────────────┤
│ Sinais Vitais                                                    │
│   ┌────────────────────────────────────┐   ┌────────────────┐    │
│   │ Linha:   BPM (atual)               │   │  Gauge BPM     │    │
│   │     ▁▂▂▃▅▇█▇▅▃▂▂▁                  │   │   ╭───────╮    │    │
│   │                                    │   │   │  120  │    │    │
│   └────────────────────────────────────┘   ╰───────────╯    │    │
│   ┌────────────────────────────────────┐   ┌────────────────┐    │
│   │ Linha:   Temperatura (C)           │   │  Gauge Temp    │    │
│   │     ──────────────                  │   │   ╭───────╮    │    │
│   │                                    │   │   │ 36.9C │    │    │
│   └────────────────────────────────────┘   ╰───────────╯    │    │
│                                            ┌────────────────┐    │
│                                            │ Gauge Umidade  │    │
│                                            ╰───────────────╯    │
├──────────────────────────────────────────────────────────────────┤
│ Status Clinico                                                   │
│   [ ⚠ ALERTA CLINICO ] / [ ✓ PACIENTE ESTAVEL ]                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Limites de alerta no dashboard

- **BPM > 120** → toast “Taquicardia detectada: X bpm”, gauge muda para
  vermelho (faixa 120–180).
- **BPM < 40** → toast “Bradicardia detectada: X bpm”.
- **Temperatura > 38 °C** → toast “Febre detectada: X °C”, gauge vermelho.
- **Mensagem em `…/alert`** → toast “Alerta do dispositivo cardioia-001:
  taquicardia;febre;”.
- **Indicador grande**: muda de verde “PACIENTE ESTÁVEL” para vermelho
  “ALERTA CLÍNICO” sempre que o campo `alert` da telemetria for `true`.

### 4.3 Inject de teste

O flow inclui um nó `inject` chamado **"Teste sem ESP32"** que envia uma
mensagem JSON simulada a cada 5 s, permitindo validar o dashboard sem
precisar conectar o hardware. Basta clicar no botão azul à esquerda do nó.

## 5. Integração opcional com Grafana

Para a opção de **Grafana Cloud** basta encadear um broker MQTT externo a
uma fonte de dados Prometheus/InfluxDB e o mesmo flow Node-RED ganha um
nó `influxdb out` adicional. O dashboard fica:

```
[mqtt in] → [function:divide] → [influxdb out: cardioia_metrics]
                                                |
                                                v
                                      Grafana Cloud (telemetry board)
```

A descrição passo-a-passo está em `README.md` da Parte 2 e fica como
extensão futura, já que o dashboard Node-RED cumpre integralmente os
requisitos do enunciado.

## 6. Como reproduzir

### 6.1 Subir o broker MQTT

Nenhuma ação necessária para o broker público `broker.hivemq.com`.
Para HiveMQ Cloud: criar uma cluster gratuita em <https://www.hivemq.com/cloud/>,
copiar host/usuário/senha e ajustar no `sketch.ino`.

### 6.2 Rodar o ESP32 (Wokwi)

1. Acesse <https://wokwi.com/projects/new/esp32>.
2. Cole `sketch.ino`, `diagram.json`, `libraries.txt`.
3. ▶ Start.
4. Verifique no monitor serial:
   ```
   [WIFI] OK -> IP 10.13.37.2
   [MQTT] Conectando a broker.hivemq.com:1883 ... OK
   [MQTT-TX] cardioia/cardioia-001/telemetry :: {"device":"cardioia-001",...}
   ```

### 6.3 Rodar o Node-RED localmente

```bash
# Instalar Node-RED
npm install -g --unsafe-perm node-red
# Iniciar
node-red
# Instalar a paleta de dashboard
npm install node-red-dashboard
# Abrir editor
xdg-open http://127.0.0.1:1880
```

Importe `node-red-flow.json` → Deploy → abra
<http://127.0.0.1:1880/ui>.

### 6.4 Testar o pipeline ponta-a-ponta

- Ative a simulação do Wokwi.
- Pressione o botão **BPM** rapidamente (>2 pressões/segundo) durante uns
  10 s → BPM > 120 → o LED de alerta do ESP32 acende, o gauge BPM no
  Node-RED fica vermelho e aparece um toast.
- Aumente a temperatura do DHT22 no Wokwi para 39 °C → toast de febre
  + indicador grande passa a “ALERTA CLINICO”.

## 7. Boas práticas e segurança

- **Identificação por dispositivo**: cada paciente publica em um *namespace*
  próprio (`cardioia/<deviceId>/...`), evitando vazamento cruzado.
- **Mensagens retained somente em alertas**: telemetria comum não é
  retida para não inflar o broker.
- **JSON minimalista** (256 B) reduz custo de banda – relevante em
  redes 4G/LoRa de dispositivos vestíveis.
- **TLS recomendado em produção**: HiveMQ Cloud expõe TLS 8883 nativamente;
  basta trocar `WiFiClient` por `WiFiClientSecure` e configurar a CA root.
- **LGPD**: o `deviceId` deve ser pseudonimizado; nunca publicar PII no
  payload.

## 8. Resultado obtido

O sistema entrega, ponta-a-ponta:

- Telemetria contínua chegando ao broker a cada 2 s;
- Dashboard atualizado em tempo real em `http://127.0.0.1:1880/ui`;
- Alertas automáticos (3 mecanismos paralelos: indicador grande, toast
  popup e LED físico no ESP32);
- Caminho de retorno (cmd) funcional para acionar atuadores remotamente.

A arquitetura está pronta para receber as extensões Ir Além 1
(notificação por e-mail via REST) e Ir Além 2 (análise de séries
temporais com IA) já entregues nesta mesma fase.
