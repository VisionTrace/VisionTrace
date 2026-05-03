import json
import shutil
from pathlib import Path
from collections import defaultdict

import boto3

from app.paths import (
    insta_profile_dir,
    insta_posts_dir,
    insta_tagged_dir,
    results_user_dir,
    owner_face_dir,
    responses_user_dir,
    AWS_REGION,
    AWS_BUCKET,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY
)

# =========================================================
# CONFIG
# =========================================================

SIMILARITY_THRESHOLD = 85

# =========================================================
# AWS CLIENTS
# =========================================================

rekognition = boto3.client(
    "rekognition",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# =========================================================
# HELPERS
# =========================================================

def upload(username: str, image: Path) -> str:
    key = f"owner_detection/{username}/{image.name}"
    s3.upload_file(str(image), AWS_BUCKET, key)
    return key


def detect_faces(key: str):
    return rekognition.detect_faces(
        Image={"S3Object": {"Bucket": AWS_BUCKET, "Name": key}},
        Attributes=["DEFAULT"]
    ).get("FaceDetails", [])


def compare(src_key: str, tgt_key: str) -> bool:
    try:
        res = rekognition.compare_faces(
            SourceImage={"S3Object": {"Bucket": AWS_BUCKET, "Name": src_key}},
            TargetImage={"S3Object": {"Bucket": AWS_BUCKET, "Name": tgt_key}},
            SimilarityThreshold=SIMILARITY_THRESHOLD
        )
        return bool(res["FaceMatches"])
    except Exception:
        return False

# =========================================================
# MAIN OWNER DETECTION LOGIC
# =========================================================

def detect_owner(username: str):

    profile_pic = insta_profile_dir(username) / "profile_pic.jpg"
    posts_dir = insta_posts_dir(username)
    tagged_dir = insta_tagged_dir(username)

    result_dir = results_user_dir(username)
    owner_dir = owner_face_dir(username)
    response_dir = responses_user_dir(username)

    owner_key = None
    face_sources = {}
    clusters = defaultdict(list)

    # =====================================================
    # STEP 1: CHECK PROFILE PIC
    # =====================================================

    if profile_pic.exists():
        key = upload(username, profile_pic)
        faces = detect_faces(key)

        if faces:
            owner_key = key
            face_sources[key] = {
                "source": "profile_pic",
                "path": str(profile_pic),
                "box": faces[0]["BoundingBox"]
            }

    # =====================================================
    # STEP 2: ANALYZE PRIMARY POSTS
    # =====================================================

    for img in posts_dir.glob("*.png"):
        key = upload(username, img)
        faces = detect_faces(key)

        if not faces:
            continue

        face_sources[key] = {
            "source": "post",
            "path": str(img),
            "box": faces[0]["BoundingBox"]
        }

        if owner_key:
            if compare(owner_key, key):
                clusters["owner"].append(key)
        else:
            placed = False
            for cluster in clusters.values():
                if compare(cluster[0], key):
                    cluster.append(key)
                    placed = True
                    break
            if not placed:
                clusters[len(clusters)].append(key)

    # =====================================================
    # STEP 3: RESOLVE OWNER IF PROFILE PIC FAILED
    # =====================================================

    if not owner_key:
        if not clusters:
            # No faces anywhere
            result = {
                "username": username,
                "owner_source": None,
                "owner_reference": None,
                "total_appearances": 0,
                "appearances": []
            }

            with open(response_dir / "owner_detection.json", "w") as f:
                json.dump(result, f, indent=2)

            print("⚠️ No faces detected anywhere.")
            return result

        # Select most frequent face cluster
        largest_cluster = max(clusters.values(), key=len)
        owner_key = largest_cluster[0]

        face_sources[owner_key]["source"] = "primary_post"

    # =====================================================
    # SAVE OWNER REFERENCE IMAGE
    # =====================================================

    owner_info = face_sources.get(owner_key)

    if owner_info:
        owner_path = Path(owner_info["path"])
        shutil.copy(owner_path, owner_dir / "owner_reference.jpg")
    else:
        result = {
            "username": username,
            "owner_source": None,
            "owner_reference": None,
            "total_appearances": 0,
            "appearances": []
        }

        with open(response_dir / "owner_detection.json", "w") as f:
            json.dump(result, f, indent=2)

        return result

    # =====================================================
    # STEP 4: FULL SCAN (POSTS + TAGGED)
    # =====================================================

    appearances = []

    def scan(folder: Path, category: str):
        for img in folder.glob("*.png"):
            key = upload(username, img)
            faces = detect_faces(key)

            if faces and compare(owner_key, key):
                appearances.append({
                    "image": str(img),
                    "category": category,
                    "bounding_box": faces[0]["BoundingBox"],
                    "confidence": faces[0]["Confidence"]
                })

    scan(posts_dir, "post")
    scan(tagged_dir, "tagged")

    # =====================================================
    # FINAL OUTPUT
    # =====================================================

    result = {
        "username": username,
        "owner_source": owner_info["source"],
        "owner_reference": str(owner_dir / "owner_reference.jpg"),
        "total_appearances": len(appearances),
        "appearances": appearances
    }

    with open(response_dir / "owner_detection.json", "w") as f:
        json.dump(result, f, indent=2)

    print("✅ Owner detection complete")

    return result


# =========================================================
# CLI ENTRY
# =========================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m modules.vision.owner_detector <instagram_username>")
        exit(1)

    detect_owner(sys.argv[1])
