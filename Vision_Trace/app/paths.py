from pathlib import Path
import os
from dotenv import load_dotenv

# =========================================================
# BASE
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"

# Load environment variables
load_dotenv(CONFIG_DIR / ".env")

# =========================================================
# ENV VARIABLES (SECRETS)
# =========================================================

# ---------- GOOGLE ----------
VISION_API_KEY = os.getenv("VISION_API_KEY")
GOOGLE_NLP_API_KEY = os.getenv("GOOGLE_NLP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------- AWS ----------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
AWS_BUCKET = os.getenv("VISION_TRACE_BUCKET")

# ---------- TWITTER ----------
TWITTER_AUTH_TOKEN = os.getenv("TWITTER_AUTH_TOKEN")
TWITTER_CSRF_TOKEN = os.getenv("TWITTER_CSRF_TOKEN")

# ---------- INSTAGRAM ----------
INSTAGRAM_COOKIE_FILE = CONFIG_DIR / "instagram_cookies.json"

# =========================================================
# VALIDATION (FAIL FAST)
# =========================================================

REQUIRED_VARS = {
    "VISION_API_KEY": VISION_API_KEY,
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "AWS_REGION": AWS_REGION,
    "AWS_BUCKET": AWS_BUCKET,
}

missing = [k for k, v in REQUIRED_VARS.items() if not v]
if missing:
    raise RuntimeError(f"❌ Missing required env vars: {', '.join(missing)}")

# =========================================================
# DATA ROOTS
# =========================================================

IMAGES_DIR = DATA_DIR / "images"
RESPONSES_DIR = DATA_DIR / "responses"
RESULTS_DIR = DATA_DIR / "results"
TWEETS_DIR = DATA_DIR / "tweets"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TWEETS_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# INSTAGRAM PATHS (USER SCOPED)
# =========================================================

def insta_user_dir(username: str) -> Path:
    path = IMAGES_DIR / "instagram" / username
    path.mkdir(parents=True, exist_ok=True)
    return path


def insta_profile_dir(username: str) -> Path:
    path = insta_user_dir(username) / "profile"
    path.mkdir(parents=True, exist_ok=True)
    return path


def insta_posts_dir(username: str) -> Path:
    path = insta_user_dir(username) / "posts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def insta_tagged_dir(username: str) -> Path:
    path = insta_user_dir(username) / "tagged"
    path.mkdir(parents=True, exist_ok=True)
    return path

# =========================================================
# RESPONSES (USER SCOPED)
# =========================================================

def responses_user_dir(username: str) -> Path:
    path = RESPONSES_DIR / username
    path.mkdir(parents=True, exist_ok=True)
    return path


def vision_response_dir(username: str) -> Path:
    path = responses_user_dir(username) / "vision"
    path.mkdir(parents=True, exist_ok=True)
    return path


def aws_response_dir(username: str) -> Path:
    path = responses_user_dir(username) / "aws"
    path.mkdir(parents=True, exist_ok=True)
    return path

# =========================================================
# RESULTS (USER SCOPED)
# =========================================================

def results_user_dir(username: str) -> Path:
    path = RESULTS_DIR / username
    path.mkdir(parents=True, exist_ok=True)
    return path


def owner_face_dir(username: str) -> Path:
    path = results_user_dir(username) / "owner_face"
    path.mkdir(parents=True, exist_ok=True)
    return path


def prediction_dir(username: str) -> Path:
    path = results_user_dir(username) / "predictions"
    path.mkdir(parents=True, exist_ok=True)
    return path

# =========================================================
# TWITTER PATHS
# =========================================================

def twitter_user_dir(insta_username: str) -> Path:
    """
    Twitter used together with Instagram
    """
    path = TWEETS_DIR / insta_username
    path.mkdir(parents=True, exist_ok=True)
    return path


def twitter_only_dir(twitter_username: str) -> Path:
    """
    Twitter-only analysis
    """
    path = TWEETS_DIR / f"twitter_only_{twitter_username}"
    path.mkdir(parents=True, exist_ok=True)
    return path
