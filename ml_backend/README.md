# ESP32 Smart Waste Segregator ML Backend

This backend serves image classification predictions for ESP32 camera captures.

Project layout:

- `server/` contains Flask API and inference code
- `configs/` contains runtime settings
- `models/` contains `keras_model.h5` and `labels.txt`
- `images/` contains local test images
- `received/` stores images received by `/predict`

## Python Version

This project is configured for **Python 3.12 or 3.13** on Windows.
Python 3.14 is not currently supported by TensorFlow wheels on Windows.

## Setup (Windows PowerShell)

```powershell
cd C:\Users\goyal\OneDrive\Desktop\esp32-smart-waste-segregator\ml_backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

If you only have Python 3.12 installed, use:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

## Run Server

```powershell
.\.venv\Scripts\Activate.ps1
python server\main.py
```

The API starts at `http://127.0.0.1:5000`.

## Health Check

```powershell
curl http://127.0.0.1:5000/health
```

## Predict With Raw Image Bytes

```powershell
curl -X POST http://127.0.0.1:5000/predict --data-binary "@images\your-image.jpg"
```

## Predict By Existing Filename

```powershell
curl -X POST http://127.0.0.1:5000/predict-file `
  -H "Content-Type: application/json" `
  -d "{\"filename\":\"your-image.jpg\"}"
```
