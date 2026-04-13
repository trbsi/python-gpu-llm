import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

from llm_reply import LlmReplyService

GET_URL = "https://peachka.net/movies/api/get-title"
UPDATE_URL = "https://peachka.net/movies/api/update-title"

SLEEP_SECONDS = 2  # delay between requests

load_dotenv()


# Run as: python rewrite_title.py --limit 20 --workers 8
class TitleProcessor:
    ONLY_TITLE = True
    ONLY_DESCRIPTION = False

    def __init__(self, limit=10, workers=5):
        self.limit = limit
        self.workers = workers

        self.llm = LlmReplyService()
        self.llm.init()

    def fetch_items(self):
        try:
            response = requests.get(GET_URL, params={"limit": self.limit}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            print(f"Fetch error: {e}")
            return []

    def generate_title(self, content: str) -> str | None:
        chat_history = [
            {
                "role": "user",
                "content": content
            }
        ]

        try:
            reply = self.llm.get_local_reply(chat_history)
            return reply.strip()
        except Exception as e:
            print(f"LLM error: {e}")
            return None

    def update_items(self, items: list[dict]):
        """
        items format:
        [
            {"video_id": 1, "title": "new title", "description": "new description"},
            ...
        ]
        """
        payload = items

        try:
            response = requests.post(UPDATE_URL, json=payload, timeout=10)
            response.raise_for_status()
            print(f"Updated batch size={len(items)}")
        except Exception as e:
            print(f"Update error: {e}")

    def process_item(self, item):
        video_id = item.get("video_id")
        title = item.get("title")

        if not video_id or not title:
            return None

        print(f"Processing: {video_id} -> {title}")
        new_title = None
        new_description = None

        if self.ONLY_TITLE:
            title_content = (
                "Rewrite title column to be SEO friendly and different but keep same meaning. "
                f'Make it dirty. Use porn words. Respond only with new title: "{title}"'
            )
            new_title = self.generate_title(title_content)
            if not new_title:
                return None
        elif self.ONLY_DESCRIPTION:
            description_content = (
                'Use porn words, be extra dirty, nasty, raw and creative.'
                f'Give me a description of a porn clip for following title, reply only with description: "{title}"'
            )
            new_description = self.generate_title(description_content)
        else:
            content = (
                'Rewrite title column to be SEO friendly and different but keep same meaning, make it dirty, nasty and raw, use porn words.'
                'Then generate description, use porn words, be extra dirty, nasty, raw and creative.'
                'Respond in JSON format: { "title": "", "description": "" }'
                f'Original title: "{title}"'
                )
            response = self.generate_title(content)
            response = json.loads(response)
            new_title = response.get("title")
            new_description = response.get("description")



        print(f"Generated title: {new_title}")
        print(f"Generated description: {new_description}")

        return {
            "video_id": video_id,
            "title": new_title,
            "description": new_description,
        }

    def run(self):
        while True:
            try:
                items = self.fetch_items()

                if not items:
                    time.sleep(SLEEP_SECONDS)
                    continue

                processed_batch = []

                with ThreadPoolExecutor(max_workers=self.workers) as executor:
                    futures = [executor.submit(self.process_item, item) for item in items]

                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            processed_batch.append(result)

                if processed_batch:
                    self.update_items(processed_batch)

            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--workers", type=int, default=5)

    args = parser.parse_args()

    processor = TitleProcessor(limit=args.limit, workers=args.workers)
    processor.run()
