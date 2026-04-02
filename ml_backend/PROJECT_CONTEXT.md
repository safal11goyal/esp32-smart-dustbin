# ESP32 + Teachable Machine Flask Server Setup

## Overview

This project turns a laptop into an image-classification server for an ESP32 camera using a Teachable Machine model exported as Keras `.h5`.

The ESP32 sends image bytes over HTTP, and the Python server returns the predicted label.

Current project root:

`/home/maestro/genai-course`

## Final Project Structure

```text
genai-course/
├── .python/                 # Local Python 3.11 runtime
├── .venv/                   # Virtual environment and installed packages
├── configs/
│   └── settings.json        # Server configuration
├── images/                  # Images used for testing predictions
├── models/
│   ├── keras_model.h5       # Teachable Machine exported model
│   └── labels.txt           # Model labels
├── server/
│   ├── app.py               # Flask app and prediction logic
│   ├── main.py              # Server entrypoint
│   ├── bulk_test.py         # Bulk image test runner
│   └── test_embedding.py    # Unrelated embedding test file
├── PROJECT_CONTEXT.md
├── README.md
├── pyproject.toml
└── uv.lock
```

## What We Did

### 1. Checked Existing Environment

We first checked whether dependencies were installed in the directory.

Findings:
- The repo had a `pyproject.toml`
- It did not have a local `.venv` initially
- It was pinned to Python `3.14`
- TensorFlow is not compatible with Python `3.14` in this setup

### 2. Added a Flask Prediction Server

We created server code to:
- load `keras_model.h5`
- load `labels.txt`
- accept image bytes over HTTP
- return JSON predictions

Initial API route:
- `POST /predict`

Later we added:
- `POST /predict-file`

`/predict-file` allows testing by filename from the `images/` directory.

Example:

```json
{"filename":"00000001.jpg"}
```

### 3. Created a Separate Python 3.11 Runtime

Because the repo was on Python `3.14`, we created a separate Python `3.11` environment for TensorFlow compatibility.

What was done:
- provisioned Python `3.11`
- created `.venv`
- installed required packages:
  - `tensorflow`
  - `flask`
  - `pillow`
  - `numpy`

Later we made the runtime self-contained by moving the interpreter into:

`.python/`

So now both:
- interpreter
- virtualenv
- installed modules

live inside the same project directory.

### 4. Reorganized the Codebase

The repo was reorganized to this structure:
- `server/` for code
- `configs/` for configuration
- `models/` for model files
- `images/` for input images

We removed the earlier root-level:
- `server.py`
- `main.py`
- `test.py`

and replaced them with:
- `server/app.py`
- `server/main.py`

### 5. Added Configuration File

Created:

`configs/settings.json`

Current contents:

```json
{
  "host": "0.0.0.0",
  "port": 5000,
  "image_size": [224, 224],
  "model_path": "models/keras_model.h5",
  "labels_path": "models/labels.txt",
  "images_dir": "images"
}
```

This lets the server read model paths, image size, and host/port from config.

### 6. Verified Model and Image Files

We checked that the required model files exist in:

- `models/keras_model.h5`
- `models/labels.txt`

We also confirmed that the `images/` directory contains test images.

### 7. Fixed TensorFlow / Keras Model Compatibility

When we first tried loading the model, it failed with a Keras deserialization error involving `DepthwiseConv2D`.

Cause:
- The model was exported with:
  - Keras `2.4.0`
- The environment had:
  - TensorFlow `2.21.0`
  - Keras `3.x`

Fix:
- Downgraded to a more compatible stack:
  - TensorFlow `2.15.1`
  - Keras `2.15.0`

After that, the model loaded correctly and inference worked.

### 8. Verified Real Prediction

We successfully ran prediction against:

`images/00000001.jpg`

Result returned:

```python
('1 N', 1.0)
```

This confirmed:
- model loads
- labels load
- image preprocessing works
- prediction path works

### 9. Added Bulk Test Script

Created:

`server/bulk_test.py`

Purpose:
- scans all images in `images/`
- randomizes order
- runs prediction on every image
- prints per-image results
- prints a summary of counts by label

Command:

```bash
source .venv/bin/activate
python server/bulk_test.py
```

Optional fixed random order:

```bash
python server/bulk_test.py --seed 42
```

### 10. Fixed Bulk Test Crashes on Corrupted Images

During bulk testing, one image caused this error:

```text
OSError: image file is truncated (19 bytes not processed)
```

Fix:
- updated `server/bulk_test.py` so it:
  - catches per-image errors
  - logs bad files
  - continues testing the rest
  - prints a failure summary at the end

So now one bad image does not stop the whole batch.

### 11. Fixed Raw HTTP Body Handling for ESP32 / curl

This request initially failed:

```bash
curl -X POST http://10.216.180.215:5000/predict \
  --data-binary @images/00000001.jpg
```

Error:

```json
{"error":"Request body must contain raw image bytes."}
```

Cause:
- Flask `request.data` was empty under the incoming content type

Fix:
- changed the server to use:

```python
request.get_data(cache=False, as_text=False, parse_form_data=False)
```

This correctly reads raw uploaded bytes from `curl` and from ESP32 HTTP clients.

After this fix, the same request worked.

### 12. Restarted and Verified the Server

We restarted the Flask server and confirmed it was listening on:

- `http://127.0.0.1:5000`
- `http://10.216.180.215:5000`

Verified working request:

```bash
curl -X POST http://10.216.180.215:5000/predict \
  --data-binary @images/00000001.jpg
```

Verified response:

```json
{"confidence":1.0,"result":"1 N"}
```

## Final API Endpoints

### `POST /predict`

Accepts raw image bytes in the request body.

Example:

```bash
curl -X POST http://10.216.180.215:5000/predict \
  --data-binary @images/00000001.jpg
```

Response:

```json
{"confidence":1.0,"result":"1 N"}
```

### `POST /predict-file`

Reads an image by filename from the `images/` directory.

Example:

```bash
curl -X POST http://10.216.180.215:5000/predict-file \
  -H "Content-Type: application/json" \
  -d '{"filename":"00000001.jpg"}'
```

## Current Runtime Versions

Compatible working setup:
- Python `3.11`
- TensorFlow `2.15.1`
- Keras `2.15.0`

Important:
- The original project Python `3.14` is not suitable for this TensorFlow model setup

## Important Files

### Server Code
- `server/app.py`
- `server/main.py`

### Bulk Testing
- `server/bulk_test.py`

### Config
- `configs/settings.json`

### Model Files
- `models/keras_model.h5`
- `models/labels.txt`

### Images
- `images/`

## How To Run the Server

```bash
source /home/maestro/genai-course/.venv/bin/activate
python /home/maestro/genai-course/server/main.py
```

The ESP32 should send requests to:

`http://10.216.180.215:5000/predict`

Notes:
- laptop and ESP32 must be on the same network
- the server must remain running while the ESP32 is using it

## How To Run Bulk Testing

```bash
source /home/maestro/genai-course/.venv/bin/activate
python /home/maestro/genai-course/server/bulk_test.py
```

Optional reproducible order:

```bash
python /home/maestro/genai-course/server/bulk_test.py --seed 42
```

## Known Notes

- Some images in `images/` may be corrupted or truncated
- bulk testing now skips those instead of stopping
- Flask’s built-in server is fine for development and testing with ESP32, but not for production deployment
- TensorFlow logs CPU and GPU warnings during startup; those warnings do not prevent CPU inference

## Good Context Prompt for ChatGPT

```md
I have a project at /home/maestro/genai-course that runs a Flask image-classification server for an ESP32 camera using a Teachable Machine model exported as keras_model.h5.

Project structure:
- server/app.py: Flask app and prediction logic
- server/main.py: server entrypoint
- server/bulk_test.py: runs predictions on all images in images/
- configs/settings.json: config
- models/keras_model.h5: exported Teachable Machine model
- models/labels.txt: labels
- images/: local test images
- .venv/: virtualenv
- .python/: local Python 3.11 runtime

Important details:
- Python 3.14 was incompatible with TensorFlow for this setup, so a local Python 3.11 runtime was created.
- TensorFlow 2.21 / Keras 3 caused model loading errors.
- The model was exported with Keras 2.4.0.
- Working environment is TensorFlow 2.15.1 and Keras 2.15.0.
- The /predict endpoint accepts raw image bytes.
- The /predict-file endpoint accepts JSON like {"filename":"00000001.jpg"} and loads from images/.
- The bulk test script randomizes all images and now skips corrupted files instead of crashing.

Verified working request:
curl -X POST http://10.216.180.215:5000/predict --data-binary @images/00000001.jpg

Verified response:
{"confidence":1.0,"result":"1 N"}

Help me continue from this setup.
```
