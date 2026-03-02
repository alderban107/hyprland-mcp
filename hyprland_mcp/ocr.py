"""OCR via Tesseract — extract text and bounding boxes from screenshots."""

import io

import pytesseract
from PIL import Image as PILImage, ImageOps, ImageFilter

from .errors import require_tool


def _check_tesseract():
    require_tool("tesseract")


def _preprocess_for_ocr(img: PILImage.Image) -> PILImage.Image:
    """Preprocess image for better OCR accuracy, especially on dark themes.

    Detects dark-background images and inverts them. Tesseract works best
    with black text on white backgrounds.
    """
    # Convert to grayscale for analysis
    gray = img.convert("L")

    # Sample the image to determine if it's dark-themed
    # Check average brightness of a sample of pixels
    pixels = list(gray.getdata())
    avg_brightness = sum(pixels) / len(pixels)

    if avg_brightness < 128:
        # Dark theme — invert so text becomes dark-on-light
        gray = ImageOps.invert(gray)

    # Light sharpen to improve edge clarity
    gray = gray.filter(ImageFilter.SHARPEN)

    return gray


def extract_text(image_bytes: bytes) -> str:
    """Run OCR on image bytes, return plain text."""
    _check_tesseract()
    img = PILImage.open(io.BytesIO(image_bytes))
    processed = _preprocess_for_ocr(img)
    return pytesseract.image_to_string(processed).strip()


def extract_boxes(image_bytes: bytes, scale: float = 1.0) -> list[dict]:
    """Run OCR and return word-level bounding boxes.

    Returns list of {"text", "x", "y", "w", "h", "conf"} dicts.
    Coordinates are scaled back to original image coordinates if scale != 1.0.
    Filters out low-confidence noise (conf < 30).
    """
    _check_tesseract()
    img = PILImage.open(io.BytesIO(image_bytes))
    processed = _preprocess_for_ocr(img)
    data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)

    boxes = []
    n = len(data["text"])
    inv_scale = 1.0 / scale if scale != 1.0 else 1.0

    for i in range(n):
        text = data["text"][i].strip()
        conf = int(data["conf"][i])
        if not text or conf < 30:
            continue
        boxes.append({
            "text": text,
            "x": int(data["left"][i] * inv_scale),
            "y": int(data["top"][i] * inv_scale),
            "w": int(data["width"][i] * inv_scale),
            "h": int(data["height"][i] * inv_scale),
            "conf": conf,
        })

    return boxes


def find_text(
    boxes: list[dict],
    target: str,
    *,
    case_sensitive: bool = False,
) -> list[dict]:
    """Find bounding boxes matching target text.

    Supports multi-word matching by looking at consecutive boxes on the same line.
    Returns matches sorted by confidence (highest first).
    """
    target_words = target.split()
    if not case_sensitive:
        target_words = [w.lower() for w in target_words]

    if len(target_words) == 1:
        # Single word — simple substring match
        matches = []
        for box in boxes:
            text = box["text"] if case_sensitive else box["text"].lower()
            if target_words[0] in text:
                matches.append(box)
        matches.sort(key=lambda b: b["conf"], reverse=True)
        return matches

    # Multi-word — find consecutive boxes that form the phrase
    matches = []
    for i in range(len(boxes) - len(target_words) + 1):
        span = boxes[i:i + len(target_words)]
        texts = [b["text"] if case_sensitive else b["text"].lower() for b in span]

        # Check if all words match and boxes are roughly on the same line
        if texts == target_words:
            y_values = [b["y"] for b in span]
            if max(y_values) - min(y_values) < span[0]["h"] * 1.5:
                # Merge into a single bounding box
                x = span[0]["x"]
                y = min(b["y"] for b in span)
                right = max(b["x"] + b["w"] for b in span)
                bottom = max(b["y"] + b["h"] for b in span)
                avg_conf = sum(b["conf"] for b in span) // len(span)
                matches.append({
                    "text": " ".join(b["text"] for b in span),
                    "x": x, "y": y,
                    "w": right - x, "h": bottom - y,
                    "conf": avg_conf,
                })

    matches.sort(key=lambda b: b["conf"], reverse=True)
    return matches
