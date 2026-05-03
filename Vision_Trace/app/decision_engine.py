# app/decision_engine.py

class DecisionEngine:

    def __init__(self, instagram: str | None = None, twitter: str | None = None):
        self.instagram = instagram
        self.twitter = twitter

    def detect_mode(self) -> str:
        if self.instagram and self.twitter:
            return "hybrid"
        elif self.instagram:
            return "insta"
        elif self.twitter:
            return "twitter_only"
        else:
            raise ValueError("At least one identifier must be provided.")

    def build_plan(self):
        mode = self.detect_mode()

        steps = []

        if mode in ["insta", "hybrid"]:
            steps.extend([
                "instagram_scrape",
                "vision_analysis",
                "aws_analysis",
                "owner_detection"
            ])

        if mode in ["twitter_only", "hybrid"]:
            steps.extend([
                "twitter_scrape",
                "twitter_analyze"
            ])

        steps.extend([
            "structured_extraction",
            "profile_generation"
        ])

        return {
            "mode": mode,
            "steps": steps
        }
