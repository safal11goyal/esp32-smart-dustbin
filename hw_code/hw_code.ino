#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// ---------------- WIFI ----------------
const char *ssid = "SM";
const char *password = "vdus7030";
const char *serverUrl = "http://192.168.124.215:5000/predict";

// ---------------- PINS ----------------
#define TRIG 13
#define ECHO_FRONT 12
#define ECHO_BIN 14
#define SERVO_PIN 15

Servo myServo;
bool detected = false;

// ---------------- CAMERA PINS ----------------
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// ---------------- DISTANCE FUNCTION ----------------
long getDistance(int echoPin)
{
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);

  if (duration == 0)
    return -1;

  return duration * 0.034 / 2;
}

// ---------------- CAMERA INIT ----------------
void initCamera()
{
  camera_config_t config;

  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  if (esp_camera_init(&config) != ESP_OK)
  {
    Serial.println("Camera init failed");
    while (true)
      ;
  }
}

// ---------------- SEND IMAGE ----------------
String sendImage()
{
  // flush old frames
  for (int i = 0; i < 2; i++)
  {
    camera_fb_t *tmp = esp_camera_fb_get();
    if (tmp)
      esp_camera_fb_return(tmp);
  }

  delay(300);

  camera_fb_t *fb = esp_camera_fb_get();

  if (!fb)
  {
    Serial.println("Camera capture failed");
    return "unknown";
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/octet-stream");

  Serial.println("Sending image...");

  int response = http.POST(fb->buf, fb->len);

  String result = "unknown";

  if (response > 0)
  {
    String payload = http.getString();

    Serial.println(payload);

    if (payload.indexOf("bio") >= 0)
      result = "bio";
    if (payload.indexOf("nonbio") >= 0)
      result = "nonbio";
  }
  else
  {
    Serial.println("HTTP failed");
  }

  http.end();
  esp_camera_fb_return(fb);

  return result;
}

// ---------------- SETUP ----------------
void setup()
{
  Serial.begin(115200);
  delay(2000);

  pinMode(TRIG, OUTPUT);
  pinMode(ECHO_FRONT, INPUT);
  pinMode(ECHO_BIN, INPUT);

  myServo.attach(SERVO_PIN);
  myServo.write(90);

  WiFi.begin(ssid, password);

  Serial.print("Connecting...");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");

  initCamera();
}

// ---------------- LOOP ----------------
void loop()
{
  long front = getDistance(ECHO_FRONT);
  delay(100); // IMPORTANT: avoid sensor interference
  long bin = getDistance(ECHO_BIN);

  Serial.print("Front: ");
  Serial.print(front);
  Serial.print(" | Bin: ");
  Serial.println(bin);

  // -------- OBJECT DETECTION --------
  if (front > 0 && front < 15 && !detected)
  {
    detected = true;

    Serial.println("Object detected");

    delay(1000);

    String prediction = sendImage();

    Serial.println("Prediction: " + prediction);

    if (prediction == "bio")
    {
      Serial.println("BIO → LEFT");
      myServo.write(0);
    }
    else if (prediction == "nonbio")
    {
      Serial.println("NONBIO → RIGHT");
      myServo.write(180);
    }

    delay(2000);
    myServo.write(90);
  }

  if (front > 25)
  {
    detected = false;
  }

  // -------- BIN LEVEL CHECK --------
  if (bin > 0 && bin < 5)
  {
    Serial.println("⚠️ BIN FULL");
  }

  delay(2000);
}
