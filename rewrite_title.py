import requests
import time

from llm_reply import LlmReplyService

GET_URL = "https://peachka.net/movies/api/get-title"
UPDATE_URL = "https://peachka.net/movies/api/update-title"

SLEEP_SECONDS = 2  # delay between requests


# Run as: python rewrite_title.py
class TitleProcessor:
    def __init__(self):
        self.llm = LlmReplyService()
        self.llm.init()

    def fetch_items(self, limit: int = 10):
        try:
            response = requests.get(GET_URL, params={"limit": limit}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            print(f"Fetch error: {e}")
            return []

    def generate_title(self, original_title: str) -> str | None:
        chat_history = [
            {
                "role": "user",
                "content": (
                    "Rewrite title column to be SEO friendly and different but keep same meaning. "
                    f"Keep it engaging. Respond only with new title: {original_title}"
                )
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
            {"video_id": 1, "title": "new title"},
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

    def run(self):
        while True:
            try:
                items = self.fetch_items(limit=10)

                if not items:
                    time.sleep(SLEEP_SECONDS)
                    continue

                processed_batch = []

                for item in items:
                    video_id = item.get("video_id")
                    title = item.get("title")

                    if not video_id or not title:
                        print("Invalid item:", item)
                        continue

                    print(f"Processing: {video_id} -> {title}")
 
                    new_title = self.generate_title(title)
                    if not new_title:
                        print("No new title generated")
                        continue

                    print(f"Generated: {new_title}\n")

                    processed_batch.append({
                        "video_id": video_id,
                        "title": new_title
                    })

                if processed_batch:
                    self.update_items(processed_batch)

            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    processor = TitleProcessor()
    processor.run()
