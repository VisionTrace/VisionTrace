import argparse
from dotenv import load_dotenv

# Load env ONCE
load_dotenv("config/.env")

from app.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Vision Trace – Full OSINT Pipeline Runner"
    )

    parser.add_argument(
        "--instagram",
        help="Instagram username",
        required=False
    )

    parser.add_argument(
        "--twitter",
        help="Twitter/X username",
        required=False
    )

    parser.add_argument(
        "--camera",
        action="store_true",
        help="Use camera image (data/images/camera/current.jpg)"
    )

    parser.add_argument(
        "--basic",
        action="store_true",
        help="Run basic prediction"
    )

    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Run advanced prediction"
    )

    args = parser.parse_args()

    if not any([args.instagram, args.twitter, args.camera]):
        raise RuntimeError(
            "At least one input required: --instagram / --twitter / --camera"
        )

    run_pipeline(
        instagram_username=args.instagram,
        twitter_username=args.twitter,
        use_camera=args.camera,
        basic=args.basic,
        advanced=args.advanced
    )


if __name__ == "__main__":
    main()
