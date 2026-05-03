import json
from datetime import datetime
from pathlib import Path
import requests
import pandas as pd

from app.paths import (
    TWEETS_DIR,
    RESPONSES_DIR,
    GOOGLE_NLP_API_KEY
)

# =========================================================
# CONFIG
# =========================================================

if not GOOGLE_NLP_API_KEY:
    raise RuntimeError("❌ GOOGLE_NLP_API_KEY not set in .env")

API_URL = (
    "https://language.googleapis.com/v1/documents:annotateText"
    f"?key={GOOGLE_NLP_API_KEY}"
)

# =========================================================
# GOOGLE NLP CORE
# =========================================================

def analyze_text_blob(text: str) -> dict:

    payload = {
        "document": {
            "type": "PLAIN_TEXT",
            "content": text
        },
        "features": {
            "extractSyntax": True,
            "extractEntities": True,
            "extractDocumentSentiment": True,
            "extractEntitySentiment": True,
            "classifyText": True,
            "moderateText": True
        },
        "encodingType": "UTF8"
    }

    response = requests.post(API_URL, json=payload, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(
            f"NL API error {response.status_code}: {response.text}"
        )

    return response.json()

# =========================================================
# PIPELINE
# =========================================================

def run_tweet_analysis(
    twitter_username: str,
    instagram_username: str | None = None
):

    # ---------- DETERMINE TWEET DIR ----------
    if instagram_username:
        tweets_dir = TWEETS_DIR / instagram_username
        response_dir = RESPONSES_DIR / instagram_username
        output_file = response_dir / "twitter_analysis.json"
    else:
        tweets_dir = TWEETS_DIR / f"twitter_only_{twitter_username}"
        response_dir = RESPONSES_DIR / f"twitter_only_{twitter_username}"
        output_file = response_dir / "tweet_analysis.json"

    response_dir.mkdir(parents=True, exist_ok=True)

    # ---------- FIND CSV ----------
    csv_files = list(tweets_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No tweet CSV found in {tweets_dir}"
        )

    df = pd.read_csv(csv_files[0])

    if "text" not in df.columns:
        raise RuntimeError("CSV missing 'text' column")

    tweets = (
        df["text"]
        .dropna()
        .astype(str)
        .tolist()
    )

    if not tweets:
        raise RuntimeError("No tweet content found")

    combined_text = " ".join(tweets)

    print(
        f"🧠 Analyzing {len(tweets)} tweets "
        f"(@{twitter_username})"
    )

    analysis = analyze_text_blob(combined_text)

    # ---------- METADATA ----------
    analysis["_metadata"] = {
        "twitter_username": twitter_username,
        "linked_instagram": instagram_username,
        "tweet_count": len(tweets),
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
        "engine": "google_natural_language"
    }

    # ---------- SAVE ----------
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            analysis,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"✅ Tweet analysis saved → {output_file}")

    return str(output_file)

# =========================================================
# CLI
# =========================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m modules.twitter.analyze <twitter_username> [instagram_username]")
        exit(1)

    twitter_user = sys.argv[1]
    insta_user = sys.argv[2] if len(sys.argv) > 2 else None

    run_tweet_analysis(
        twitter_username=twitter_user,
        instagram_username=insta_user
    )
