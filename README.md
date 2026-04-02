# ESP32 Smart Waste Segregator

[![ESP32-CAM](https://img.shields.io/badge/board-ESP32--CAM-222222?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com/)
[![Arduino CLI](https://img.shields.io/badge/tool-Arduino%20CLI-00979D?style=for-the-badge&logo=arduino&logoColor=white)](https://arduino.github.io/arduino-cli/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask API](https://img.shields.io/badge/backend-Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![TensorFlow 2.15](https://img.shields.io/badge/model-TensorFlow%202.15-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://www.tensorflow.org/)

An ESP32-CAM smart dustbin that captures waste images, sends them to a local Flask classification server, and routes waste into `bio` or `nonbio`.

## Overview

This repository contains:

- `hw_code/`: ESP32-CAM Arduino sketch for the smart dustbin hardware
- `ml_backend/`: Python Flask server that receives images and classifies them as `bio` or `nonbio`

## Repository Layout

```text
esp32-smart-waste-segregator/
├── hw_code/
│   └── hw_code.ino
├── ml_backend/
│   ├── configs/
│   ├── models/
│   ├── server/
│   ├── README.md
│   ├── pyproject.toml
│   └── uv.lock
└── README.md
```

## System Flow

1. The ESP32-CAM detects an object near the bin.
2. It captures an image and sends raw bytes to the Flask backend.
3. The backend runs the Teachable Machine model.
4. The backend returns `bio` or `nonbio`.
5. The servo rotates to the matching side of the bin.

## What You Need

On a fresh machine, install:

- Git
- Python 3.11
- `venv` support for Python 3.11
- Arduino CLI
- ESP32 board support for Arduino CLI
- A USB serial connection to the ESP32-CAM

You also need the Teachable Machine model files for the backend:

- `ml_backend/models/keras_model.h5`
- `ml_backend/models/labels.txt`

`labels.txt` is tracked in Git if present. The `.h5` model file is intentionally ignored by Git and must be copied in manually.

## 1. Clone The Repository

```bash
git clone https://github.com/TH3-MA3STRO/esp32-smart-waste-segregator.git
cd esp32-smart-waste-segregator
```

## 2. Set Up The ML Backend

Move into the backend directory:

```bash
cd ml_backend
```

Create a Python 3.11 virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies:

```bash
pip install flask pillow numpy tensorflow==2.15.1
```

Place your Teachable Machine export files in `ml_backend/models/`:

- `keras_model.h5`
- `labels.txt`

The default backend config is in [ml_backend/configs/settings.json](/home/maestro/projects/esd_smart_dustbin/ml_backend/configs/settings.json). By default, it starts on port `5000`.

Run the backend:

```bash
python server/main.py
```

You should now have the API available at:

```text
http://<your-machine-ip>:5000/predict
```

Quick health check:

```bash
curl http://127.0.0.1:5000/health
```

## 3. Update The Arduino Sketch

Open [hw_code/hw_code.ino](/home/maestro/projects/esd_smart_dustbin/hw_code/hw_code.ino) and update these values before compiling:

- `ssid`
- `password`
- `serverUrl`

`serverUrl` must point to the machine running the backend, for example:

```cpp
const char *serverUrl = "http://192.168.1.10:5000/predict";
```

The laptop and ESP32-CAM must be on the same network.

## 4. Set Up Arduino CLI

If Arduino CLI is not initialized yet:

```bash
arduino-cli config init
arduino-cli core update-index
arduino-cli core install esp32:esp32
```

If needed, install the libraries used by the sketch:

```bash
arduino-cli lib install "ESP32Servo"
```

## 5. Compile, Upload, And Monitor

From the repository root:

Compile:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32cam hw_code
```

Upload:

```bash
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32cam hw_code
```

Monitor serial output:

```bash
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200
```

Notes:

- If your serial device is not `/dev/ttyUSB0`, replace it with the correct port.
- The sketch uses `Serial.begin(115200)`, so the monitor baud rate must be `115200`.

## 6. Typical Run Flow

1. Start the backend:

```bash
cd ml_backend
source .venv/bin/activate
python server/main.py
```

2. In another terminal, compile and upload the sketch:

```bash
cd /path/to/esd_smart_dustbin
arduino-cli compile --fqbn esp32:esp32:esp32cam hw_code
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32cam hw_code
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200
```

3. Trigger the bin and watch:

- serial output from the ESP32-CAM
- received images saved under `ml_backend/received/`
- backend responses from `/predict`

## Troubleshooting

- If the backend fails on startup, check that `ml_backend/models/keras_model.h5` and `ml_backend/models/labels.txt` exist.
- If the ESP32-CAM cannot classify images, verify that `serverUrl` points to the correct machine IP and port.
- If upload fails, confirm the serial port with `arduino-cli board list`.
- If serial output is unreadable, make sure the monitor baud is `115200`.
- If TensorFlow install fails on a newer Python version, use Python `3.11`.
