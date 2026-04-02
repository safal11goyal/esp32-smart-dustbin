# Teachable Machine Flask Server

Project layout:

- `server/` holds the Python code
- `configs/` holds configuration
- `models/` holds `keras_model.h5` and `labels.txt`
- `images/` holds images you want to classify locally
- `.venv/` holds installed packages
- `.python/` holds the local Python 3.11 runtime used by `.venv`

Put these Teachable Machine export files in `models/`:

- `models/keras_model.h5`
- `models/labels.txt`

Put any sample images you want to test in `images/`.

## Run

```bash
source .venv/bin/activate
python server/main.py
```

The API starts on `http://127.0.0.1:5000`.

## Test

```bash
curl -X POST http://127.0.0.1:5000/predict \
  --data-binary @images/your-image.jpg
```

You can also predict by filename for an image already stored in `images/`:

```bash
curl -X POST http://127.0.0.1:5000/predict-file \
  -H "Content-Type: application/json" \
  -d '{"filename":"your-image.jpg"}'
```

## Bulk Test

Run predictions on every image in `images/` in random order:

```bash
source .venv/bin/activate
python server/bulk_test.py
```

Use a fixed shuffle order if needed:

```bash
python server/bulk_test.py --seed 42
```
