from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path

from app import IMAGES_DIR, predict_image


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run predictions on every image in the images directory in random order.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible shuffle order.",
    )
    return parser.parse_args()


def collect_images(images_dir: Path) -> list[Path]:
    files = [
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"No image files found in {images_dir}")
    return files


def main() -> None:
    args = parse_args()
    images = collect_images(IMAGES_DIR)

    rng = random.Random(args.seed)
    rng.shuffle(images)

    label_counts: Counter[str] = Counter()
    failures: list[tuple[Path, str]] = []

    print(f"Testing {len(images)} image(s) from {IMAGES_DIR}")
    if args.seed is not None:
        print(f"Shuffle seed: {args.seed}")

    for index, image_path in enumerate(images, start=1):
        try:
            label, confidence = predict_image(image_path.read_bytes())
        except Exception as exc:
            failures.append((image_path, str(exc)))
            print(f"{index:03d}. {image_path.name} -> ERROR ({exc})")
            continue

        label_counts[label] += 1
        print(f"{index:03d}. {image_path.name} -> {label} ({confidence:.4f})")

    print("\nSummary")
    for label, count in sorted(label_counts.items()):
        print(f"{label}: {count}")

    if failures:
        print(f"\nFailures: {len(failures)}")
        for image_path, error in failures:
            print(f"{image_path.name}: {error}")


if __name__ == "__main__":
    main()
