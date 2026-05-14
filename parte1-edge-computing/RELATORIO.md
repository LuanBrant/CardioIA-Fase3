# Relatório – Parte 1 (Edge Computing) – CardioIA Fase 3

**Aluno:** Luan Brant
**Projeto:** CardioIA – Monitoramento Contínuo / IoT na Saúde
**Plataforma:** Wokwi (ESP32 DevKit v1) + Arduino/C++
**Repositório:** ver README principal do projeto

---

## 1. Visão geral

Esta etapa do projeto CardioIA implementa o **nó de borda (Edge)** de um
wearable cardiológico. O dispositivo é responsável por:

1. **Capturar sinais vitais** de um paciente (temperatura, umidade da pele
   e frequência cardíaca);
2. **Processar localmente** as leituras, classificando-as como normais ou
   em condição de alerta;
3. **Garantir resiliência offline**: continuar coletando e armazenando
   mesmo quando o link de rede está indisponível;
4. **Sincronizar com a nuvem** assim que a conectividade for restabelecida,
   sem perda de amostras (até o limite do buffer projetado).

O conjunto compõe a primeira camada do pipeline IoT médico
**captura → processamento → transmissão → visualização → alerta**.

## 2. Hardware simulado (Wokwi)

| Componente              | Pino ESP32 | Função                                                      |
|-------------------------|------------|-------------------------------------------------------------|
| **DHT22**               | GPIO 4     | Sensor obrigatório (temperatura + umidade)                  |
| Botão "PULSO" (vermelho)| GPIO 5     | Segundo sensor – cada toque equivale a 1 batimento cardíaco |
| Botão "WIFI" (azul)     | GPIO 18    | Alterna o estado simulado de conectividade                  |
| LED verde "WIFI"        | GPIO 2     | Indicador visual: aceso = online / apagado = offline        |
| LED vermelho "ALERTA"   | GPIO 15    | Aceso quando há condição clínica de risco                   |

O DHT22 atende ao requisito obrigatório do enunciado; o **botão de pulso**
foi escolhido como segundo sensor por simular fielmente um pulse sensor:
o usuário pressiona em ritmo cardíaco simulado e a contagem de bordas de
descida em uma janela móvel de 10 s, multiplicada por 6, gera o BPM em
tempo real – mesma técnica usada em pulsímetros ópticos de mercado.

## 3. Fluxo de funcionamento

```
        +-------------------+
        | DHT22 + Botão BPM |
        +---------+---------+
                  |
                  v
        +-------------------+         WiFi OFF       +------------------+
        |   Leitura a cada  | ---------------------> |   Buffer RAM     |
        |        2 s        |                        |   (100 amostras) |
        +---------+---------+                        +---------+--------+
                  |  WiFi ON                                  |
                  v                                           |
        +-------------------+        flushBuffer()            |
        |  Envio direto     | <-------------------------------+
        |   "para nuvem"    |
        |  (Serial.println) |
        +-------------------+
```

1. A cada **2 s** o loop principal lê DHT22 e BPM acumulado.
2. Avalia limites: `T > 38 °C`, `BPM > 120`, `BPM < 40`, `UMID > 85 %`.
3. Se a flag `wifiConnected` estiver `true`, a leitura segue direto para o
   "canal de nuvem" (no protótipo, `Serial.println` formatado em JSON –
   na Parte 2 essa mesma estrutura será publicada via MQTT).
4. Caso contrário, a amostra é gravada no **buffer circular em RAM**,
   preservando o histórico local.
5. Assim que o usuário pressiona o botão "WIFI" e o estado volta a `true`,
   `flushBuffer()` drena todas as amostras represadas em ordem cronológica
   e zera o cache local – emulando a operação `POST + ACK + DELETE` que
   ocorreria contra a nuvem em produção.

## 4. Lógica de resiliência offline

### 4.1 Escolha do buffer

O simulador Wokwi (web e VSCode/PlatformIO) **não persiste SPIFFS** entre
execuções – o sistema de arquivos é volátil e é destruído ao encerrar a
simulação. O enunciado autoriza, portanto, a usar o **Monitor Serial como
alternativa de resiliência offline** e adotamos um **buffer circular em
RAM (`Reading buffer[BUFFER_SIZE]`)** como cache equivalente.

Justificativa do tamanho `BUFFER_SIZE = 100`:

| Variável                    | Valor                         |
|-----------------------------|-------------------------------|
| Intervalo entre amostras    | 2 s                           |
| Tamanho do buffer           | 100 amostras                  |
| Autonomia offline           | **~3,3 minutos**              |
| Custo de memória            | 100 × 24 B ≈ 2,4 KB de RAM    |

Para um **wearable cardiológico** de monitoramento contínuo o ideal de
mercado é manter pelo menos algumas horas de autonomia. Em chip real,
trocando o buffer RAM por SPIFFS ou cartão microSD (≈ 4 MB → 8 GB) o
mesmo código permite **dezenas de milhares de amostras**, suficientes para
**dias** de operação sem conectividade – cenário típico de pacientes
domiciliares pós-cirurgia.

### 4.2 Estratégia LRU em overflow

Quando o buffer enche antes do retorno da conectividade, a estratégia
adotada é **sobrescrever a amostra mais antiga (LRU)** e incrementar o
contador `droppedSamples`. A escolha clínica é deliberada: o evento
diagnóstico relevante para uma equipe médica que recebe o histórico
"atrasado" é, na maioria dos casos, o que aconteceu **mais próximo do
momento atual** – e não eventos de horas atrás. O contador é enviado junto
com o flush para que o backend saiba que houve perda de telemetria.

### 4.3 Garantias

- **Não há perda de leitura por falta de rede** dentro da janela de
  capacidade do buffer.
- **Não há leitura duplicada**: o `flushBuffer()` zera `bufferHead` e
  `bufferCount` somente após emitir todas as amostras.
- **A leitura em curso** quando a rede volta também é enviada – o
  `flushBuffer()` é executado antes da publicação da amostra atual,
  garantindo ordenação temporal correta na nuvem.

## 5. Detecção local de alerta (Edge AI mínimo)

A regra de alerta é executada no próprio ESP32 (não depende de nuvem):

```
alert = (T > 38 °C) || (BPM > 120) || (BPM < 40) || (UMID > 85 %)
```

Esses limites refletem padrões clínicos básicos:

- **38 °C** – limiar de febre;
- **> 120 BPM** – taquicardia em repouso;
- **< 40 BPM** – bradicardia significativa;
- **> 85 % de umidade** na pele – proxy de sudorese intensa, que pode
  preceder eventos isquêmicos.

O LED vermelho acende imediatamente, **sem latência de rede** – princípio
fundamental do Edge Computing aplicado à saúde: a decisão crítica não
pode depender da nuvem.

## 6. Saídas no Serial Monitor (exemplo)

```
======================================================
 CardioIA - Fase 3 / Parte 1 - Edge Computing
======================================================
 Buffer circular: 100 amostras (3.3 min de autonomia)
 Limites de alerta: T>38.0C | BPM>120 ou <40 | UMID>85.0%
======================================================
[LEITURA] t=2003ms | temp=32.10C | hum=55.00% | bpm=70 | wifi=OFF
[EDGE-CACHE] offline -> amostra 1/100 em RAM (descartadas: 0)
[LEITURA] t=4005ms | temp=32.50C | hum=55.10% | bpm=132 | wifi=OFF  *** ALERTA ***
[EDGE-CACHE] offline -> amostra 2/100 em RAM (descartadas: 0)
...
>>> [SYNC] WiFi online - drenando buffer offline para a nuvem...
>>> [SYNC] Amostras a enviar: 12   |   Amostras descartadas por overflow: 0
[CLOUD-SYNC] {"ts":2003,"temp":32.10,"hum":55.00,"bpm":70,"alert":false}
[CLOUD-SYNC] {"ts":4005,"temp":32.50,"hum":55.10,"bpm":132,"alert":true}
...
[CLOUD-LIVE] {"ts":26113,"temp":32.80,"hum":54.90,"bpm":85,"alert":false}
```

## 7. Como executar

### Wokwi Web
1. Acesse <https://wokwi.com/projects/new/esp32>.
2. Cole `sketch.ino` no editor de código.
3. Cole `diagram.json` na aba **diagram.json**.
4. Adicione **DHT sensor library** e **Adafruit Unified Sensor** na aba
   **libraries.txt**.
5. Pressione ▶ e use os botões: o vermelho "PULSO" para gerar batimentos
   e o azul "WIFI" para alternar online/offline.

### VSCode + PlatformIO + extensão Wokwi
1. Abra a pasta `parte1-edge-computing/`.
2. `PlatformIO: Build`.
3. `Wokwi: Start Simulator`.

## 8. Conclusão

A Parte 1 entrega o **núcleo Edge** do CardioIA com leitura sincronizada
de dois sensores, classificação local de alerta sem dependência de nuvem
e estratégia explícita de resiliência offline (buffer circular com LRU e
flush idempotente). A arquitetura está pronta para a próxima fase
(transmissão MQTT) – basta substituir os `Serial.println` por
`mqttClient.publish()` no mesmo ponto de código.
