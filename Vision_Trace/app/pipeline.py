# app/pipeline.py

import asyncio

from modules.instagram.scrape import run_scrape
from modules.vision.visionapi import run_vision_for_user
from modules.vision.aws_rekognition import run_aws_for_user
from modules.vision.owner_detector import detect_owner
from modules.twitter.scrape import scrape_twitter
from modules.twitter.analyze import run_tweet_analysis
from modules.prediction.structured_extractor import StructuredExtractor
from modules.prediction.profile_engine import ProfileEngine


class Pipeline:

    def __init__(self, instagram=None, twitter=None):
        self.instagram = instagram
        self.twitter = twitter

    async def execute(self, plan):

        mode = plan["mode"]

        for step in plan["steps"]:
            print(f"🚀 Executing: {step}")

            if step == "instagram_scrape":
                run_scrape(self.instagram)

            elif step == "vision_analysis":
                run_vision_for_user(self.instagram)

            elif step == "aws_analysis":
                run_aws_for_user(self.instagram)

            elif step == "owner_detection":
                detect_owner(self.instagram)

            elif step == "twitter_scrape":
                await scrape_twitter(
                    twitter_username=self.twitter,
                    instagram_username=self.instagram
                )

            elif step == "twitter_analyze":
                run_tweet_analysis(
                    twitter_username=self.twitter,
                    instagram_username=self.instagram
                )

            elif step == "structured_extraction":
                target = self.instagram if self.instagram else self.twitter
                extractor = StructuredExtractor(target, mode)
                extractor.run_full_extraction()

            elif step == "profile_generation":
                target = self.instagram if self.instagram else self.twitter
                engine = ProfileEngine(target, mode)
                engine.generate_report()

        print("✅ PIPELINE COMPLETE")
