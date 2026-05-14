/*
 * =====================================================================================
 *  CardioIA - Fase 3 - PARTE 2: Fog/Cloud com MQTT
 *
 *  - WiFi REAL no simulador (Wokwi-GUEST) ou rede do aluno
 *  - Publica via MQTT em broker.hivemq.com (broker publico, sem TLS)
 *  - Compativel com broker HiveMQ Cloud (basta trocar host/porta/credenciais)
 *  - Publica:
 *       cardioia/<deviceId>/telemetry  (JSON com todos os sinais)
 *       cardioia/<deviceId>/alert      (somente em condicao de alerta)
 *  - Recebe (subscribe):
 *       cardioia/<deviceId>/cmd        (comandos remotos: piscar LED, etc.)
 * =====================================================================================
 */
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ----------------------- CONFIGURAVEIS ----------------------------------------------
#define DEVICE_ID       "cardioia-001"

// Wokwi possui um SSID aberto chamado "Wokwi-GUEST"
const char* WIFI_SSID   = "Wokwi-GUEST";
const char* WIFI_PASS   = "";

// Broker MQTT publico (HiveMQ). Pode trocar por seu HiveMQ Cloud:
//   const char* MQTT_HOST = "<sua-instancia>.s2.eu.hivemq.cloud";
//   const int   MQTT_PORT = 8883;   // TLS
//   const char* MQTT_USER = "...";
//   const char* MQTT_PASS = "...";
const char* MQTT_HOST   = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;
const char* MQTT_USER   = "";
const char* MQTT_PASS   = "";

// ----- Pinagem -----
#define DHT_PIN         4
#define DHT_TYPE        DHT22
#define PULSE_BUTTON    5
#define LED_STATUS      2
#define LED_ALERT       15

// ----- Limites clinicos -----
#define TEMP_MAX_C      38.0f
#define BPM_MAX         120
#define BPM_MIN         40
#define HUM_MAX         85.0f
#define SAMPLE_PERIOD   2000UL
#define BPM_WINDOW      10000UL

// ----- Topicos -----
String topicTelemetry = String("cardioia/") + DEVICE_ID + "/telemetry";
String topicAlert     = String("cardioia/") + DEVICE_ID + "/alert";
String topicCmd       = String("cardioia/") + DEVICE_ID + "/cmd";

// ----- Recursos -----
DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient   net;
PubSubClient mqtt(net);

// ----- Medicao BPM -----
volatile unsigned long pulseCount  = 0;
volatile unsigned long lastPulseMs = 0;
unsigned long lastBpmCalc = 0;
int currentBpm = 70;

void IRAM_ATTR pulseISR() {
  unsigned long now = millis();
  if (now - lastPulseMs > 80) {
    pulseCount++;
    lastPulseMs = now;
  }
}

void connectWiFi() {
  Serial.printf("[WIFI] Conectando a %s ", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.printf("\n[WIFI] OK -> IP %s\n", WiFi.localIP().toString().c_str());
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String msg;
  msg.reserve(length);
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.printf("[MQTT-RX] %s :: %s\n", topic, msg.c_str());
  // Comando remoto: aceitar "blink" para piscar o LED de alerta como ACK
  if (msg.indexOf("blink") >= 0) {
    for (int i = 0; i < 6; i++) {
      digitalWrite(LED_ALERT, !digitalRead(LED_ALERT));
      delay(120);
    }
    digitalWrite(LED_ALERT, LOW);
  }
}

void connectMQTT() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  while (!mqtt.connected()) {
    Serial.printf("[MQTT] Conectando a %s:%d ... ", MQTT_HOST, MQTT_PORT);
    String clientId = String(DEVICE_ID) + "-" + String((uint32_t)esp_random(), HEX);
    bool ok;
    if (strlen(MQTT_USER) > 0) {
      ok = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS);
    } else {
      ok = mqtt.connect(clientId.c_str());
    }
    if (ok) {
      Serial.println("OK");
      mqtt.subscribe(topicCmd.c_str());
      Serial.printf("[MQTT] Subscrito em %s\n", topicCmd.c_str());
    } else {
      Serial.printf("FALHA (rc=%d). Tentando novamente em 2s...\n", mqtt.state());
      delay(2000);
    }
  }
}

void publishTelemetry(float temp, float hum, int bpm, bool alert) {
  StaticJsonDocument<256> doc;
  doc["device"]      = DEVICE_ID;
  doc["ts"]          = millis();
  doc["temperature"] = temp;
  doc["humidity"]    = hum;
  doc["bpm"]         = bpm;
  doc["alert"]       = alert;
  char payload[256];
  size_t n = serializeJson(doc, payload, sizeof(payload));
  mqtt.publish(topicTelemetry.c_str(), (uint8_t*)payload, n, false);
  Serial.printf("[MQTT-TX] %s :: %s\n", topicTelemetry.c_str(), payload);

  if (alert) {
    StaticJsonDocument<256> a;
    a["device"]   = DEVICE_ID;
    a["ts"]       = millis();
    a["bpm"]      = bpm;
    a["temp"]     = temp;
    a["humidity"] = hum;
    String reason = "";
    if (temp > TEMP_MAX_C) reason += "febre;";
    if (bpm  > BPM_MAX)    reason += "taquicardia;";
    if (bpm  < BPM_MIN)    reason += "bradicardia;";
    if (hum  > HUM_MAX)    reason += "sudorese;";
    a["reason"] = reason;
    char abuf[256];
    size_t an = serializeJson(a, abuf, sizeof(abuf));
    mqtt.publish(topicAlert.c_str(), (uint8_t*)abuf, an, true);  // retained
    Serial.printf("[MQTT-TX] %s :: %s\n", topicAlert.c_str(), abuf);
  }
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F(" CardioIA - Fase 3 / Parte 2 - Fog & Cloud (MQTT)"));
  Serial.println(F("======================================================"));

  pinMode(PULSE_BUTTON, INPUT_PULLUP);
  pinMode(LED_STATUS,   OUTPUT);
  pinMode(LED_ALERT,    OUTPUT);
  attachInterrupt(digitalPinToInterrupt(PULSE_BUTTON), pulseISR, FALLING);

  dht.begin();
  connectWiFi();
  digitalWrite(LED_STATUS, HIGH);
  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_STATUS, LOW);
    connectWiFi();
    digitalWrite(LED_STATUS, HIGH);
  }
  if (!mqtt.connected()) {
    connectMQTT();
  }
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastBpmCalc >= BPM_WINDOW) {
    noInterrupts();
    unsigned long n = pulseCount;
    pulseCount = 0;
    interrupts();
    currentBpm  = (int)(n * (60000UL / BPM_WINDOW));
    lastBpmCalc = now;
  }

  static unsigned long lastSample = 0;
  if (now - lastSample < SAMPLE_PERIOD) return;
  lastSample = now;

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println(F("[ERRO] Falha de leitura do DHT22"));
    return;
  }

  bool alert = (t > TEMP_MAX_C) || (currentBpm > BPM_MAX) ||
               (currentBpm < BPM_MIN) || (h > HUM_MAX);
  digitalWrite(LED_ALERT, alert ? HIGH : LOW);

  publishTelemetry(t, h, currentBpm, alert);
}
