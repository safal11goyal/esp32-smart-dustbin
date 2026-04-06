from __future__ import annotations

import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from queue import Empty, Queue
from threading import Lock
from uuid import uuid4

import numpy as np
import tensorflow as tf
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "settings.json"
REPO_ROOT = BASE_DIR.parent
FRONTEND_DIR = REPO_ROOT / "frontend"


def load_settings() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


SETTINGS = load_settings()
MODEL_PATH = BASE_DIR / str(SETTINGS["model_path"])
LABELS_PATH = BASE_DIR / str(SETTINGS["labels_path"])
IMAGES_DIR = BASE_DIR / str(SETTINGS["images_dir"])
RECEIVED_DIR = BASE_DIR / str(SETTINGS.get("received_dir", "received"))
DETECTIONS_PATH = RECEIVED_DIR / "detections.json"
DEVICE_STATE_PATH = RECEIVED_DIR / "device_state.json"
IMAGE_SIZE = tuple(SETTINGS["image_size"])
HOST = str(SETTINGS["host"])
PORT = int(SETTINGS["port"])
HEARTBEAT_TIMEOUT_SECONDS = int(SETTINGS.get("heartbeat_timeout_seconds", 150))
BIN_EMPTY_DISTANCE_CM = float(SETTINGS.get("bin_empty_distance_cm", 10.5))
BIN_FULL_DISTANCE_CM = float(SETTINGS.get("bin_full_distance_cm", 2.0))

app = Flask(__name__)
event_subscribers: set[Queue[tuple[str, dict[str, object]]]] = set()
event_subscribers_lock = Lock()


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
    if not DETECTIONS_PATH.exists():
        DETECTIONS_PATH.write_text('{"detections": []}\n', encoding="utf-8")
    if not DEVICE_STATE_PATH.exists():
        DEVICE_STATE_PATH.write_text(
            (
                "{\n"
                '  "last_heartbeat_at": null,\n'
                '  "device_status": "unknown",\n'
                '  "wifi_connected": false,\n'
                '  "bin_distance_cm": null,\n'
                '  "bin_fill_percent": null\n'
                "}\n"
            ),
            encoding="utf-8",
        )


def load_labels() -> list[str]:
    raw_labels = LABELS_PATH.read_text(encoding="utf-8").splitlines()
    return [label.strip() for label in raw_labels if label.strip()]


def subscribe_events() -> Queue[tuple[str, dict[str, object]]]:
    subscriber: Queue[tuple[str, dict[str, object]]] = Queue()
    with event_subscribers_lock:
        event_subscribers.add(subscriber)
    return subscriber


def unsubscribe_events(subscriber: Queue[tuple[str, dict[str, object]]]) -> None:
    with event_subscribers_lock:
        event_subscribers.discard(subscriber)


def publish_event(event_type: str, payload: dict[str, object]) -> None:
    with event_subscribers_lock:
        subscribers = list(event_subscribers)

    for subscriber in subscribers:
        subscriber.put((event_type, payload))


def format_sse(event_type: str, payload: dict[str, object]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


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


def load_detection_log() -> dict[str, list[dict[str, object]]]:
    try:
        payload = json.loads(DETECTIONS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        payload = {"detections": []}

    detections = payload.get("detections")
    if not isinstance(detections, list):
        detections = []

    return {"detections": detections}


def append_detection_record(
    *,
    saved_path: Path,
    raw_label: str,
    result: str,
    confidence: float,
) -> dict[str, object]:
    detection_log = load_detection_log()
    record = {
        "saved_as": saved_path.name,
        "received_url": f"/received/{saved_path.name}",
        "raw": raw_label,
        "result": result,
        "confidence": confidence,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    updated = [record, *detection_log["detections"]][:50]
    DETECTIONS_PATH.write_text(
        json.dumps({"detections": updated}, indent=2) + "\n",
        encoding="utf-8",
    )
    publish_event("detection", record)
    return record


def count_received_images() -> int:
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    return sum(1 for path in RECEIVED_DIR.iterdir() if path.is_file() and path.suffix.lower() in image_suffixes)


def calculate_bin_fill_percent(distance_cm: float | int | None) -> int | None:
    if distance_cm is None:
        return None

    try:
        distance = float(distance_cm)
    except (TypeError, ValueError):
        return None

    if distance <= 0:
        return None

    ratio = (BIN_EMPTY_DISTANCE_CM - distance) / (BIN_EMPTY_DISTANCE_CM - BIN_FULL_DISTANCE_CM)
    clamped = max(0.0, min(1.0, ratio))
    return round(clamped * 100)


def build_bin_state(distance_cm: float | int | None, fill_percent: int | None) -> dict[str, object]:
    if fill_percent is None:
        fill_percent = calculate_bin_fill_percent(distance_cm)

    if fill_percent is None:
        return {
            "distance_cm": None,
            "fill_percent": None,
            "detail": "No recent bin sensor reading available.",
            "empty_distance_cm": BIN_EMPTY_DISTANCE_CM,
            "full_distance_cm": BIN_FULL_DISTANCE_CM,
        }

    if fill_percent >= 90:
        detail = "Bin is nearly full and should be emptied soon."
    elif fill_percent >= 60:
        detail = "Bin is over half full."
    else:
        detail = "Bin has remaining space."

    return {
        "distance_cm": float(distance_cm) if distance_cm is not None else None,
        "fill_percent": fill_percent,
        "detail": detail,
        "empty_distance_cm": BIN_EMPTY_DISTANCE_CM,
        "full_distance_cm": BIN_FULL_DISTANCE_CM,
    }


def load_device_state() -> dict[str, object]:
    try:
        payload = json.loads(DEVICE_STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        payload = {"last_heartbeat_at": None}

    if not isinstance(payload, dict):
        payload = {"last_heartbeat_at": None}

    return payload


def write_device_state(
    *,
    heartbeat_at: datetime | None,
    device_status: str = "unknown",
    wifi_connected: bool = False,
    bin_distance_cm: float | int | None = None,
    bin_fill_percent: int | None = None,
) -> None:
    DEVICE_STATE_PATH.write_text(
        json.dumps(
            {
                "last_heartbeat_at": heartbeat_at.isoformat(timespec="seconds") if heartbeat_at else None,
                "device_status": device_status,
                "wifi_connected": wifi_connected,
                "bin_distance_cm": bin_distance_cm,
                "bin_fill_percent": bin_fill_percent,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def get_device_status() -> dict[str, object]:
    device_state = load_device_state()
    last_heartbeat_raw = device_state.get("last_heartbeat_at")
    device_status = str(device_state.get("device_status") or "unknown")
    wifi_connected = bool(device_state.get("wifi_connected"))
    bin_distance_cm = device_state.get("bin_distance_cm")
    bin_fill_percent = device_state.get("bin_fill_percent")

    if not isinstance(last_heartbeat_raw, str) or not last_heartbeat_raw:
        return {
            "online": False,
            "last_heartbeat_at": None,
            "timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
            "device_status": device_status,
            "wifi_connected": wifi_connected,
            "bin": build_bin_state(bin_distance_cm, bin_fill_percent),
        }

    try:
        last_heartbeat_at = datetime.fromisoformat(last_heartbeat_raw)
    except ValueError:
        return {
            "online": False,
            "last_heartbeat_at": None,
            "timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
            "device_status": device_status,
            "wifi_connected": wifi_connected,
            "bin": build_bin_state(bin_distance_cm, bin_fill_percent),
        }

    now = datetime.now()
    online = now - last_heartbeat_at <= timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
    return {
        "online": online,
        "last_heartbeat_at": last_heartbeat_at.isoformat(timespec="seconds"),
        "timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
        "device_status": device_status,
        "wifi_connected": wifi_connected,
        "bin": build_bin_state(bin_distance_cm, bin_fill_percent),
    }


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


@app.get("/status")
def status() -> tuple[dict[str, object], int]:
    return {
        "backend": {
            "healthy": True,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        },
        "esp32": get_device_status(),
        "capture_buffer": {
            "count": count_received_images(),
        },
    }, 200


@app.post("/device/heartbeat")
def device_heartbeat() -> tuple[dict[str, object], int]:
    payload = request.get_json(silent=True) or {}
    heartbeat_at = datetime.now()
    device_status = str(payload.get("device_status") or "unknown")
    wifi_connected = bool(payload.get("wifi_connected", False))
    bin_distance_cm = payload.get("bin_distance_cm")
    bin_fill_percent = payload.get("bin_fill_percent")

    if bin_fill_percent is None:
        bin_fill_percent = calculate_bin_fill_percent(bin_distance_cm)

    write_device_state(
        heartbeat_at=heartbeat_at,
        device_status=device_status,
        wifi_connected=wifi_connected,
        bin_distance_cm=bin_distance_cm,
        bin_fill_percent=bin_fill_percent,
    )
    return {
        "status": "ok",
        "received_at": heartbeat_at.isoformat(timespec="seconds"),
        "timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
        "device_status": device_status,
        "bin": build_bin_state(bin_distance_cm, bin_fill_percent),
    }, 200


@app.get("/")
@app.get("/dashboard")
def dashboard() -> object:
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/dashboard/<path:filename>")
def dashboard_assets(filename: str) -> object:
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/received/<path:filename>")
def received_image(filename: str) -> object:
    return send_from_directory(RECEIVED_DIR, filename)


@app.get("/detections")
def detections() -> tuple[dict[str, list[dict[str, object]]], int]:
    return load_detection_log(), 200


@app.get("/events")
def events() -> Response:
    subscriber = subscribe_events()

    def event_stream() -> object:
        try:
            yield format_sse(
                "connected",
                {"connected_at": datetime.now().isoformat(timespec="seconds")},
            )
            while True:
                try:
                    event_type, payload = subscriber.get(timeout=20)
                    yield format_sse(event_type, payload)
                except Empty:
                    yield ": keep-alive\n\n"
        finally:
            unsubscribe_events(subscriber)

    response = Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.post("/predict")
def predict() -> tuple[object, int]:
    image_bytes = request.get_data(cache=False, as_text=False, parse_form_data=False)

    if not image_bytes:
        return jsonify({"error": "Request body must contain raw image bytes."}), 400

    try:
        saved_path = save_received_image(image_bytes)
        raw_label, confidence = predict_image(image_bytes)
        result = clean_label(raw_label)
        detection = append_detection_record(
            saved_path=saved_path,
            raw_label=raw_label,
            result=result,
            confidence=confidence,
        )
    except Exception as exc:  # pragma: no cover - defensive API error handling
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "raw": raw_label,
            "result": result,
            "confidence": confidence,
            "saved_as": saved_path.name,
            "saved_path": str(saved_path),
            "received_url": f"/received/{saved_path.name}",
            "created_at": detection["created_at"],
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
        raw_label, confidence = predict_image(image_path.read_bytes())
    except Exception as exc:  # pragma: no cover - defensive API error handling
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "filename": filename,
            "raw": raw_label,
            "result": clean_label(raw_label),
            "confidence": confidence,
        },
    ), 200


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
