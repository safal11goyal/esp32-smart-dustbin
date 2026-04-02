from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import tensorflow as tf
from flask import Flask, jsonify, request
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "settings.json"


def load_settings() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


SETTINGS = load_settings()
MODEL_PATH = BASE_DIR / str(SETTINGS["model_path"])
LABELS_PATH = BASE_DIR / str(SETTINGS["labels_path"])
IMAGES_DIR = BASE_DIR / str(SETTINGS["images_dir"])
RECEIVED_DIR = BASE_DIR / str(SETTINGS.get("received_dir", "received"))
IMAGE_SIZE = tuple(SETTINGS["image_size"])
HOST = str(SETTINGS["host"])
PORT = int(SETTINGS["port"])

app = Flask(__name__)


def ensure_required_files() -> None:
    missing_files = [str(path) for path in (MODEL_PATH, LABELS_PATH) if not path.exists()]
    if missing_files:
        missing = ", ".join(missing_files)
        raise FileNotFoundError(
            f"Missing required model file(s): {missing}. Export them from Teachable Machine "
            "and place them in the models directory."
        )


def ensure_directories() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)


def load_labels() -> list[str]:
    raw_labels = LABELS_PATH.read_text(encoding="utf-8").splitlines()
    return [label.strip() for label in raw_labels if label.strip()]


def prepare_image(image_bytes: bytes) -> np.ndarray:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize(IMAGE_SIZE)
    image_array = np.array(image, dtype=np.float32) / 255.0
    return np.expand_dims(image_array, axis=0)


ensure_directories()
ensure_required_files()
model = tf.keras.models.load_model(MODEL_PATH)
labels = load_labels()


def predict_image(image_bytes: bytes) -> tuple[str, float]:
    image_batch = prepare_image(image_bytes)
    prediction = model.predict(image_batch, verbose=0)[0]
    index = int(np.argmax(prediction))
    confidence = float(prediction[index])
    return labels[index], confidence


def clean_label(label: str) -> str:
    if "B" in label:
        return "bio"
    if "N" in label:
        return "nonbio"
    return "unknown"


def save_received_image(image_bytes: bytes) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{uuid4().hex[:8]}.jpg"
    output_path = RECEIVED_DIR / filename
    output_path.write_bytes(image_bytes)
    return output_path


def resolve_image_path(filename: str) -> Path:
    candidate = (IMAGES_DIR / filename).resolve()
    images_root = IMAGES_DIR.resolve()
    if images_root not in candidate.parents and candidate != images_root:
        raise ValueError("Image path must stay inside the images directory.")
    if not candidate.is_file():
        raise FileNotFoundError(f"Image not found: {candidate}")
    return candidate


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.post("/predict")
def predict() -> tuple[object, int]:
    image_bytes = request.get_data(cache=False, as_text=False, parse_form_data=False)

    if not image_bytes:
        return jsonify({"error": "Request body must contain raw image bytes."}), 400

    try:
        saved_path = save_received_image(image_bytes)
        raw_label, _confidence = predict_image(image_bytes)
    except Exception as exc:  # pragma: no cover - defensive API error handling
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "raw": raw_label,
            "result": clean_label(raw_label),
            "saved_as": saved_path.name,
            "saved_path": str(saved_path),
        },
    ), 200


@app.post("/predict-file")
def predict_file() -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    filename = payload.get("filename")

    if not filename or not isinstance(filename, str):
        return jsonify({"error": "JSON body must include a string field 'filename'."}), 400

    try:
        image_path = resolve_image_path(filename)
        raw_label, _confidence = predict_image(image_path.read_bytes())
    except Exception as exc:  # pragma: no cover - defensive API error handling
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {"filename": filename, "raw": raw_label, "result": clean_label(raw_label)},
    ), 200


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
