import asyncio
import json
from pathlib import Path
import os

from twikit import Client
import pandas as pd

from app.paths import (
    twitter_user_dir,
    twitter_only_dir,
    TWITTER_AUTH_TOKEN,
    TWITTER_CSRF_TOKEN
)

# =========================================================
# VALIDATION
# =========================================================

if not TWITTER_AUTH_TOKEN or not TWITTER_CSRF_TOKEN:
    raise RuntimeError("❌ TWITTER_AUTH_TOKEN or TWITTER_CSRF_TOKEN not set in .env")

# =========================================================
# CORE SCRAPER
# =========================================================

async def scrape_twitter(
    twitter_username: str,
    tweet_count: int = 50,
    instagram_username: str | None = None
):
    """
    Scrapes tweets for a given Twitter username.
    If instagram_username is provided, tweets are stored under that user context.
    """

    # ---------- OUTPUT DIRECTORY ----------
    if instagram_username:
        user_dir = twitter_user_dir(instagram_username)
        csv_path = user_dir / f"{twitter_username}_tweets.csv"
        json_path = user_dir / f"{twitter_username}_tweets.json"
    else:
        user_dir = twitter_only_dir(twitter_username)
        csv_path = user_dir / "tweets.csv"
        json_path = user_dir / "tweets.json"

    # ---------- CLIENT ----------
    client = Client("en-US")
    client.set_cookies({
        "auth_token": TWITTER_AUTH_TOKEN,
        "ct0": TWITTER_CSRF_TOKEN
    })

    print(f"🐦 Fetching @{twitter_username} tweets…")

    # ---------- FETCH ----------
    user = await client.get_user_by_screen_name(twitter_username)
    tweets = await user.get_tweets("Tweets", count=tweet_count)

    records = []
    for tweet in tweets:
        records.append({
            "id": tweet.id,
            "date": tweet.created_at,
            "text": tweet.text,
            "retweets": tweet.retweet_count,
            "likes": tweet.favorite_count
        })

    # ---------- SAVE ----------
    df = pd.DataFrame(records)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(df)} tweets to {user_dir}")

    return {
        "twitter_username": twitter_username,
        "instagram_context": instagram_username,
        "tweet_count": len(df),
        "csv": str(csv_path),
        "json": str(json_path)
    }

# =========================================================
# CLI ENTRY
# =========================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m modules.twitter.scrape <twitter_username> [instagram_username]")
        exit(1)

    twitter_user = sys.argv[1]
    insta_user = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(
        scrape_twitter(
            twitter_username=twitter_user,
            tweet_count=100,
            instagram_username=insta_user
        )
    )
