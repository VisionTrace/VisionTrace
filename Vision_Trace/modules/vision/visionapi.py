import base64
import json
import requests
from pathlib import Path

from app.paths import (
    VISION_API_KEY,
    IMAGES_DIR,
    vision_response_dir
)

# =========================================================
# GOOGLE VISION CONFIG
# =========================================================

VISION_URL = f"https://vision.googleapis.com/v1/images:annotate?key={VISION_API_KEY}"

FEATURES_LIST = [
    {"type": "LABEL_DETECTION", "maxResults": 20},
    {"type": "TEXT_DETECTION"},
    {"type": "OBJECT_LOCALIZATION"},
    {"type": "FACE_DETECTION"},
    {"type": "LOGO_DETECTION"},
    {"type": "LANDMARK_DETECTION"},
    {"type": "SAFE_SEARCH_DETECTION"},
    {"type": "IMAGE_PROPERTIES"},
    {"type": "WEB_DETECTION"},
]

# =========================================================
# CORE ANALYSIS
# =========================================================

def analyze_image(image_path: Path) -> dict:
    """
    Sends a single image to Google Vision API
    and returns the raw JSON response.
    """

    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    request_body = {
        "requests": [
            {
                "image": {"content": img_base64},
                "features": FEATURES_LIST
            }
        ]
    }

    response = requests.post(VISION_URL, json=request_body, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(
            f"Vision API error {response.status_code}: {response.text}"
        )

    return response.json()

# =========================================================
# USER PIPELINE
# =========================================================

def run_vision_for_user(username: str):
    """
    Runs Vision API on all Instagram images
    for a given user and saves results
    """

    images_root = IMAGES_DIR / "instagram" / username
    output_dir = vision_response_dir(username)

    if not images_root.exists():
        raise FileNotFoundError(f"No images found for user: {username}")

    print(f"🔍 Running Google Vision for: {username}")

    for category in ["posts", "tagged"]:
        category_dir = images_root / category
        if not category_dir.exists():
            continue

        for img_path in category_dir.glob("*"):
            if img_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue

            try:
                print(f"   → {category}/{img_path.name}")

                result = analyze_image(img_path)

                out_file = output_dir / f"{category}_{img_path.stem}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

            except Exception as e:
                print(f"❌ Vision failed for {img_path.name}: {e}")

    print("✅ Google Vision analysis complete")

# =========================================================
# CLI ENTRY
# =========================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m modules.vision.visionapi <instagram_username>")
        sys.exit(1)

    run_vision_for_user(sys.argv[1])
