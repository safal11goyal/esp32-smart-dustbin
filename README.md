# ESP32 Smart Waste Segregator

ESP32-CAM smart dustbin project that captures waste images, sends them to a local ML backend, and routes waste into `bio` or `nonbio`.

## Repository Layout

- `hw_code/`: ESP32-CAM Arduino sketch
- `ml_backend/`: Flask + TensorFlow inference backend
- `frontend/`: Dashboard assets served by the backend

## Backend Requirements

- Windows with Python `3.12` or `3.13`
- Teachable Machine model files:
  - `ml_backend/models/keras_model.h5`
  - `ml_backend/models/labels.txt`

Python `3.14` is not supported for this backend flow because TensorFlow wheels are not available for it on Windows.

## Quick Start (Windows PowerShell)

```powershell
git clone https://github.com/safal11goyal/esp32-smart-dustbin.git
cd esp32-smart-dustbin\ml_backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
python server\main.py
```

Backend runs on `http://127.0.0.1:5000`.

## Useful Backend Routes

- `GET /health`
- `GET /status`
- `GET /detections`
- `GET /received/<filename>`
- `POST /predict` (raw image bytes)
- `POST /predict-file` (JSON body with filename)
- `POST /device/heartbeat`

## ESP32 Setup Notes

In `hw_code/hw_code.ino`, set:

- `ssid`
- `password`
- `serverUrl` (example: `http://192.168.1.10:5000/predict`)

Keep the ESP32 and backend machine on the same network.

## Arduino CLI (Optional)

```powershell
arduino-cli config init
arduino-cli core update-index
arduino-cli core install esp32:esp32
arduino-cli lib install "ESP32Servo"
```

Compile and upload (replace COM port as needed):

```powershell
arduino-cli compile --fqbn esp32:esp32:esp32cam hw_code
arduino-cli upload -p COM5 --fqbn esp32:esp32:esp32cam hw_code
arduino-cli monitor -p COM5 -c baudrate=115200
```
