/*
  ESP32 MQTT IoT — Temperature, Light Switch, Brightness Control
  ─────────────────────────────────────────────────────────────────
  Libraries ที่ต้องติดตั้งใน Arduino IDE:
    • PubSubClient  (by Nick O'Leary)
    • DHT sensor library  (by Adafruit)
    • Adafruit Unified Sensor (dependency)

  วิธีติดตั้ง: Arduino IDE → Sketch → Include Library → Manage Libraries
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// ── WiFi / MQTT Config ───────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASS     = "YOUR_WIFI_PASSWORD";
const char* MQTT_BROKER   = "broker.hivemq.com";   // เปลี่ยนตาม Broker
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENT   = "esp32_node_001";
const char* MQTT_USER     = "";   // ถ้าต้องการ username
const char* MQTT_PASS_STR = "";   // ถ้าต้องการ password

// ── Topics ───────────────────────────────────────────────────────
const char* TOPIC_SENSOR   = "esp32/sensor/dht";       // Publish อุณหภูมิ
const char* TOPIC_SWITCH   = "esp32/light/switch";     // Subscribe สวิตซ์
const char* TOPIC_BRIGHT   = "esp32/light/brightness"; // Subscribe ความสว่าง

// ── Hardware Pins ────────────────────────────────────────────────
#define DHT_PIN     4       // DHT11/DHT22 data pin
#define DHT_TYPE    DHT11   // เปลี่ยนเป็น DHT22 ถ้าใช้ DHT22
#define LED_PIN     2       // GPIO2 = onboard LED (หรือต่อหลอดไฟ)
#define PWM_PIN     5       // PWM pin สำหรับ MOSFET/LED driver

// PWM Config
#define PWM_CHANNEL   0
#define PWM_FREQ      5000   // Hz
#define PWM_BITS      8      // 0–255

// ── Globals ──────────────────────────────────────────────────────
WiFiClient   espClient;
PubSubClient mqtt(espClient);
DHT          dht(DHT_PIN, DHT_TYPE);

bool  lightState = false;
int   brightness = 0;
unsigned long lastSensorMs = 0;
const unsigned long SENSOR_INTERVAL = 5000; // ส่งข้อมูลทุก 5 วินาที

// ── Setup ────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  // GPIO
  pinMode(LED_PIN, OUTPUT);
  ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_BITS);
  ledcAttachPin(PWM_PIN, PWM_CHANNEL);
  ledcWrite(PWM_CHANNEL, 0);

  dht.begin();
  connectWiFi();

  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
}

// ── Loop ─────────────────────────────────────────────────────────
void loop() {
  if (!mqtt.connected()) reconnectMQTT();
  mqtt.loop();

  // ส่งข้อมูล sensor ทุก SENSOR_INTERVAL ms
  if (millis() - lastSensorMs >= SENSOR_INTERVAL) {
    lastSensorMs = millis();
    publishSensor();
  }
}

// ── WiFi ─────────────────────────────────────────────────────────
void connectWiFi() {
  Serial.print("[WiFi] กำลังเชื่อมต่อ: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("[WiFi] เชื่อมต่อแล้ว IP: ");
  Serial.println(WiFi.localIP());
}

// ── MQTT Reconnect ───────────────────────────────────────────────
void reconnectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("[MQTT] กำลังเชื่อมต่อ...");
    bool ok = (strlen(MQTT_USER) > 0)
      ? mqtt.connect(MQTT_CLIENT, MQTT_USER, MQTT_PASS_STR)
      : mqtt.connect(MQTT_CLIENT);

    if (ok) {
      Serial.println("เชื่อมต่อสำเร็จ");
      mqtt.subscribe(TOPIC_SWITCH, 1);
      mqtt.subscribe(TOPIC_BRIGHT, 1);
      Serial.printf("[MQTT] Subscribe: %s, %s\n", TOPIC_SWITCH, TOPIC_BRIGHT);
    } else {
      Serial.printf("ล้มเหลว rc=%d ลองใหม่ใน 5 วินาที\n", mqtt.state());
      delay(5000);
    }
  }
}

// ── MQTT Callback (รับข้อมูลจาก Dashboard) ──────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int len) {
  char msg[64] = {0};
  memcpy(msg, payload, min(len, (unsigned int)63));
  Serial.printf("[MQTT] RX [%s]: %s\n", topic, msg);

  // สวิตซ์ไฟ
  if (strcmp(topic, TOPIC_SWITCH) == 0) {
    lightState = (msg[0] == '1');
    applyLight();
    Serial.printf("[Light] %s\n", lightState ? "เปิด" : "ปิด");
  }

  // ความสว่าง (0–100 จาก Dashboard → แปลงเป็น 0–255 สำหรับ PWM)
  if (strcmp(topic, TOPIC_BRIGHT) == 0) {
    int pct = atoi(msg);
    pct = constrain(pct, 0, 100);
    brightness = pct;
    if (pct > 0) lightState = true;
    applyLight();
    Serial.printf("[Brightness] %d%%\n", pct);
  }
}

// ── Apply Light State ────────────────────────────────────────────
void applyLight() {
  if (!lightState) {
    digitalWrite(LED_PIN, LOW);
    ledcWrite(PWM_CHANNEL, 0);
    return;
  }
  int pwmVal = map(brightness, 0, 100, 0, 255);
  ledcWrite(PWM_CHANNEL, pwmVal);
  digitalWrite(LED_PIN, brightness > 0 ? HIGH : LOW);
}

// ── Publish Sensor Data ──────────────────────────────────────────
void publishSensor() {
  float temp  = dht.readTemperature();
  float humid = dht.readHumidity();

  if (isnan(temp) || isnan(humid)) {
    Serial.println("[DHT] อ่านค่าไม่ได้");
    // ส่งข้อมูลจำลองในกรณีทดสอบโดยไม่มีเซนเซอร์
    temp  = 25.0 + (millis() % 100) / 20.0;
    humid = 60.0 + (millis() % 50) / 5.0;
  }

  // ส่งเป็น JSON format
  char payload[80];
  snprintf(payload, sizeof(payload),
    "{\"temp\":%.1f,\"humid\":%.1f}", temp, humid);

  bool ok = mqtt.publish(TOPIC_SENSOR, payload, true); // retained = true
  Serial.printf("[MQTT] TX [%s]: %s %s\n", TOPIC_SENSOR, payload, ok ? "✓" : "✗");
}
