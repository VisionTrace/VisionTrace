import json
from pathlib import Path
from datetime import datetime

import boto3

from app.paths import (
    IMAGES_DIR,
    aws_response_dir,
    AWS_REGION,
    AWS_BUCKET,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY
)

# =========================================================
# CONFIG
# =========================================================

MIN_CONFIDENCE = 70

# =========================================================
# AWS CLIENTS
# =========================================================

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

rekognition = boto3.client(
    "rekognition",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# =========================================================
# HELPERS
# =========================================================

def upload_image(local_path: Path) -> str:
    """
    Upload image to S3 and return object key
    """
    key = f"vision_trace/{local_path.name}"
    s3.upload_file(str(local_path), AWS_BUCKET, key)
    return key


def analyze_image(s3_key: str) -> dict:
    """
    Run full Rekognition analysis on an image in S3
    """

    result = {}

    # 1️⃣ LABELS / ENVIRONMENT
    labels = rekognition.detect_labels(
        Image={"S3Object": {"Bucket": AWS_BUCKET, "Name": s3_key}},
        MaxLabels=50,
        MinConfidence=MIN_CONFIDENCE
    )

    result["environment"] = [
        {
            "name": l["Name"],
            "confidence": l["Confidence"],
            "parents": [p["Name"] for p in l.get("Parents", [])],
            "instances": l.get("Instances", [])
        }
        for l in labels["Labels"]
    ]

    # 2️⃣ FACE ANALYSIS
    faces = rekognition.detect_faces(
        Image={"S3Object": {"Bucket": AWS_BUCKET, "Name": s3_key}},
        Attributes=["ALL"]
    )

    result["faces"] = [
        {
            "bounding_box": f["BoundingBox"],
            "age_range": f["AgeRange"],
            "gender": f["Gender"],
            "emotions": f["Emotions"],
            "smile": f["Smile"],
            "eyeglasses": f["Eyeglasses"],
            "sunglasses": f["Sunglasses"],
            "beard": f["Beard"],
            "mustache": f["Mustache"],
            "eyes_open": f["EyesOpen"],
            "mouth_open": f["MouthOpen"],
            "pose": f["Pose"],
            "quality": f["Quality"],
            "confidence": f["Confidence"]
        }
        for f in faces["FaceDetails"]
    ]

    # 3️⃣ TEXT DETECTION
    text = rekognition.detect_text(
        Image={"S3Object": {"Bucket": AWS_BUCKET, "Name": s3_key}}
    )

    result["text_clues"] = [
        {
            "text": t["DetectedText"],
            "type": t["Type"],
            "confidence": t["Confidence"],
            "bounding_box": t["Geometry"]["BoundingBox"]
        }
        for t in text["TextDetections"]
    ]

    # 4️⃣ MODERATION
    moderation = rekognition.detect_moderation_labels(
        Image={"S3Object": {"Bucket": AWS_BUCKET, "Name": s3_key}},
        MinConfidence=MIN_CONFIDENCE
    )

    result["moderation"] = [
        {
            "name": m["Name"],
            "parent": m.get("ParentName"),
            "confidence": m["Confidence"]
        }
        for m in moderation["ModerationLabels"]
    ]

    # 5️⃣ METADATA
    result["metadata"] = {
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
        "aws_region": AWS_REGION,
        "s3_object": s3_key
    }

    return result

# =========================================================
# USER PIPELINE
# =========================================================

def run_aws_for_user(username: str):
    """
    Run AWS Rekognition on all Instagram images for a user
    """

    images_root = IMAGES_DIR / "instagram" / username
    output_dir = aws_response_dir(username)

    if not images_root.exists():
        raise FileNotFoundError(f"No images found for user: {username}")

    print(f"🧠 Running AWS Rekognition for: {username}")

    for category in ["posts", "tagged"]:
        category_dir = images_root / category
        if not category_dir.exists():
            continue

        for img_path in category_dir.glob("*"):
            if img_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue

            try:
                print(f"   → {category}/{img_path.name}")

                s3_key = upload_image(img_path)
                analysis = analyze_image(s3_key)

                out_file = output_dir / f"{category}_{img_path.stem}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(analysis, f, indent=2, ensure_ascii=False)

            except Exception as e:
                print(f"❌ Rekognition failed for {img_path.name}: {e}")

    print("✅ AWS Rekognition analysis complete")

# =========================================================
# CLI ENTRY
# =========================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m modules.vision.aws_rekognition <instagram_username>")
        sys.exit(1)

    run_aws_for_user(sys.argv[1])
