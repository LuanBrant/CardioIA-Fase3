/*
 * =====================================================================================
 *  CardioIA - Fase 3 - PARTE 1: Edge Computing
 *  Sistema de monitoramento cardiologico vestivel com resiliencia offline
 *
 *  Sensores:
 *    - DHT22 (temperatura + umidade)            -> simula sensor cutaneo
 *    - Botao "pulso" (interrupcao)              -> simula batimento cardiaco
 *
 *  Botoes auxiliares:
 *    - Botao "wifi" (interrupcao)               -> alterna conectividade simulada
 *
 *  Indicadores:
 *    - LED verde                                -> estado de conectividade WiFi
 *    - LED vermelho                             -> alerta cardiologico ativo
 *
 *  Estrategia de resiliencia (Edge Computing):
 *    - Buffer circular em RAM com BUFFER_SIZE amostras (~3 horas a cada 2s).
 *    - Em simulador o SPIFFS e volatil, entao o buffer cumpre o papel de
 *      "armazenamento offline" e e dumpado via Serial.println (que e o
 *      "envio para a nuvem" simulado) assim que o WiFi volta.
 *    - Em chip real basta trocar storeReading() / flushBuffer() por
 *      gravacao SPIFFS/SD; a interface logica e identica.
 * =====================================================================================
 */
#include <Arduino.h>
#include <DHT.h>

// ----- Pinagem -----
#define DHT_PIN        4
#define DHT_TYPE       DHT22
#define PULSE_BUTTON   5
#define WIFI_BUTTON    18
#define LED_WIFI       2
#define LED_ALERT      15

// ----- Parametros clinicos (limites de alerta) -----
#define TEMP_MAX_C     38.0f     // febre
#define BPM_MAX        120       // taquicardia
#define BPM_MIN        40        // bradicardia
#define HUM_MAX        85.0f     // sudorese intensa
#define SAMPLE_PERIOD  2000UL    // 2 s entre leituras
#define BPM_WINDOW     10000UL   // janela de calculo de BPM (10 s)

// ----- Buffer circular para resiliencia offline -----
// 100 amostras a cada 2s = ~3 min antes de sobrescrever as mais antigas.
// Em producao com SPIFFS/SD esse valor sobe para milhares.
#define BUFFER_SIZE    100

struct Reading {
  unsigned long ts;
  float temperature;
  float humidity;
  int   bpm;
  bool  alert;
};

Reading buffer[BUFFER_SIZE];
volatile int bufferHead  = 0;          // posicao da proxima escrita
volatile int bufferCount = 0;          // quantidade de amostras valida
unsigned long droppedSamples = 0;      // metricas de overflow (LRU)

// ----- Estado de rede simulado -----
volatile bool wifiConnected = false;
volatile unsigned long lastWifiToggle = 0;

// ----- Medicao de batimentos -----
volatile unsigned long pulseCount = 0;
volatile unsigned long lastPulseMs = 0;
unsigned long lastBpmCalc = 0;
int currentBpm = 70;                   // valor inicial em repouso

DHT dht(DHT_PIN, DHT_TYPE);

// ----- ISR: cada borda de descida = 1 batimento -----
void IRAM_ATTR pulseISR() {
  unsigned long now = millis();
  // debounce de 80 ms -> evita registrar batimentos > 750 BPM (impossivel)
  if (now - lastPulseMs > 80) {
    pulseCount++;
    lastPulseMs = now;
  }
}

// ----- ISR: alterna conectividade WiFi simulada -----
void IRAM_ATTR wifiISR() {
  unsigned long now = millis();
  if (now - lastWifiToggle > 300) {     // debounce 300 ms
    wifiConnected  = !wifiConnected;
    lastWifiToggle = now;
  }
}

// ----- Armazena uma amostra no buffer circular -----
// Estrategia LRU: quando o buffer enche, sobrescreve a amostra mais antiga.
// Para um wearable cardiologico isso e aceitavel: amostras antigas perdem
// relevancia diagnostica frente as recentes.
void storeReading(float temp, float hum, int bpm, bool alert) {
  buffer[bufferHead].ts          = millis();
  buffer[bufferHead].temperature = temp;
  buffer[bufferHead].humidity    = hum;
  buffer[bufferHead].bpm         = bpm;
  buffer[bufferHead].alert       = alert;
  bufferHead = (bufferHead + 1) % BUFFER_SIZE;
  if (bufferCount < BUFFER_SIZE) {
    bufferCount++;
  } else {
    droppedSamples++;                  // overflow: amostra antiga descartada
  }
}

// ----- Dumpa todo o buffer via Serial e limpa o cache local -----
// Em chip real seria um POST HTTPS / publish MQTT, e ao receber ACK o
// arquivo SPIFFS/SD seria apagado.
void flushBuffer() {
  if (bufferCount == 0) return;
  Serial.println();
  Serial.println(F(">>> [SYNC] WiFi online - drenando buffer offline para a nuvem..."));
  Serial.printf(">>> [SYNC] Amostras a enviar: %d   |   Amostras descartadas por overflow: %lu\n",
                bufferCount, droppedSamples);

  int tail = (bufferHead - bufferCount + BUFFER_SIZE) % BUFFER_SIZE;
  for (int i = 0; i < bufferCount; i++) {
    Reading r = buffer[tail];
    Serial.printf("[CLOUD-SYNC] {\"ts\":%lu,\"temp\":%.2f,\"hum\":%.2f,\"bpm\":%d,\"alert\":%s}\n",
                  r.ts, r.temperature, r.humidity, r.bpm,
                  r.alert ? "true" : "false");
    tail = (tail + 1) % BUFFER_SIZE;
  }

  bufferCount     = 0;
  bufferHead      = 0;
  droppedSamples  = 0;
  Serial.println(F(">>> [SYNC] Sincronizacao concluida. Buffer local zerado."));
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" CardioIA - Fase 3 / Parte 1 - Edge Computing"));
  Serial.println(F(" Wearable cardiologico com resiliencia offline"));
  Serial.println(F("======================================================"));
  Serial.printf(" Buffer circular: %d amostras (%.1f min de autonomia)\n",
                BUFFER_SIZE, (BUFFER_SIZE * SAMPLE_PERIOD) / 60000.0f);
  Serial.printf(" Limites de alerta: T>%.1fC | BPM>%d ou <%d | UMID>%.1f%%\n",
                TEMP_MAX_C, BPM_MAX, BPM_MIN, HUM_MAX);
  Serial.println(F("======================================================"));
  Serial.println();

  pinMode(PULSE_BUTTON, INPUT_PULLUP);
  pinMode(WIFI_BUTTON,  INPUT_PULLUP);
  pinMode(LED_WIFI,  OUTPUT);
  pinMode(LED_ALERT, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(PULSE_BUTTON), pulseISR, FALLING);
  attachInterrupt(digitalPinToInterrupt(WIFI_BUTTON),  wifiISR,  FALLING);

  dht.begin();
}

void loop() {
  digitalWrite(LED_WIFI, wifiConnected ? HIGH : LOW);
  unsigned long now = millis();

  // Recalcula BPM com janela movel de 10 s (multiplica por 6 = 60 s)
  if (now - lastBpmCalc >= BPM_WINDOW) {
    noInterrupts();
    unsigned long n = pulseCount;
    pulseCount = 0;
    interrupts();
    currentBpm   = (int)(n * (60000UL / BPM_WINDOW));
    lastBpmCalc  = now;
  }

  static unsigned long lastSample = 0;
  if (now - lastSample < SAMPLE_PERIOD) return;
  lastSample = now;

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println(F("[ERRO] Falha de leitura do DHT22 - amostra descartada"));
    return;
  }

  bool alert = (t > TEMP_MAX_C) ||
               (currentBpm > BPM_MAX) ||
               (currentBpm < BPM_MIN) ||
               (h > HUM_MAX);
  digitalWrite(LED_ALERT, alert ? HIGH : LOW);

  Serial.printf("[LEITURA] t=%lums | temp=%.2fC | hum=%.2f%% | bpm=%d | wifi=%s%s\n",
                now, t, h, currentBpm,
                wifiConnected ? "ON" : "OFF",
                alert ? "  *** ALERTA ***" : "");

  if (wifiConnected) {
    // Antes de enviar a leitura atual, drenamos o que ficou represado offline
    if (bufferCount > 0) flushBuffer();
    Serial.printf("[CLOUD-LIVE] {\"ts\":%lu,\"temp\":%.2f,\"hum\":%.2f,\"bpm\":%d,\"alert\":%s}\n",
                  now, t, h, currentBpm, alert ? "true" : "false");
  } else {
    storeReading(t, h, currentBpm, alert);
    Serial.printf("[EDGE-CACHE] offline -> amostra %d/%d em RAM (descartadas: %lu)\n",
                  bufferCount, BUFFER_SIZE, droppedSamples);
  }
}
