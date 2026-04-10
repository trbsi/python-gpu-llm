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

    def fetch_item(self):
        try:
            response = requests.get(GET_URL, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Fetch error: {e}")
            return None

    def generate_title(self, original_title: str) -> str | None:
        chat_history = [
            {"role": "user",
             "content": f"Rewrite title column to be SEO friendly and to be different but have the same meaning. keep it dirty. respond only with new title: {original_title}"}
        ]

        try:
            reply = self.llm.get_local_reply(chat_history)
            return reply.strip()
        except Exception as e:
            print(f"LLM error: {e}")
            return None

    def update_item(self, video_id: int, new_title: str):
        payload = {
            "video_id": video_id,
            "title": new_title
        }

        try:
            response = requests.post(UPDATE_URL, json=payload, timeout=10)
            response.raise_for_status()
            print(f"Updated video_id={video_id}")
        except Exception as e:
            print(f"Update error: {e}")

    def run(self):
        while True:
            try:
                item = self.fetch_item()

                if not item:
                    time.sleep(SLEEP_SECONDS)
                    continue

                video_id = item.get("video_id")
                title = item.get("title")

                if not video_id or not title:
                    print("Invalid response:", item)
                    time.sleep(SLEEP_SECONDS)
                    continue

                print(f"Processing: {video_id} -> {title}")
                new_title = self.generate_title(title)
                if not new_title:
                    print("No new title")
                    continue

                print(f"Generated: {new_title}")
                print("")
                self.update_item(video_id, new_title)
            except Exception as e:
                print(e)


if __name__ == "__main__":
    processor = TitleProcessor()
    processor.run()
