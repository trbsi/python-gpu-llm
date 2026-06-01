import argparse
import re
import time
import traceback
import requests
from dotenv import load_dotenv
from llm_reply import LlmReplyService

GET_URL = "https://peachka.net/movies/api/get-title"
UPDATE_URL = "https://peachka.net/movies/api/update-title"

SLEEP_SECONDS = 10

load_dotenv()


class TitleProcessor:
    DEFAULT_TOKENS = 250
    LAST_ID = 0

    # ✅ SYSTEM PROMPT (sent once per request)
    SYSTEM_PROMPT = """
You are a high-throughput metadata rewriting engine for adult video content.

TASK:
- Rewrite titles to be SEO-friendly, natural, and explicit
- Generate descriptions based on title and tags
- Return ONLY valid JSON:
  {"title": "...", "description": "..."}

STYLE:
- Human-like, not robotic
- Search-optimized adult wording
- 3–5 sentence description
- No extra text outside JSON
"""

    def __init__(self, limit: int, type: str, lang: str):
        self.limit = limit
        self.type = type
        self.lang = lang

        self.llm = LlmReplyService()
        self.llm.init()

    # -------------------------
    # TYPE HELPERS
    # -------------------------

    def is_only_title(self):
        return self.type == "only_title"

    def is_only_description(self):
        return self.type == "only_description"

    def is_title_and_description(self):
        return self.type == "title_and_description"

    # -------------------------
    # API FETCH
    # -------------------------

    def fetch_items(self):
        try:
            params = {
                "limit": self.limit,
                "last_id": self.LAST_ID,
                "lang": self.lang,
            }

            response = requests.get(GET_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            self.LAST_ID = int(data.get("last_id", self.LAST_ID))

            return data.get("items", [])

        except Exception as e:
            print(f"Fetch error: {e}")
            return []

    # -------------------------
    # LLM CALL (OPTIMIZED)
    # -------------------------

    def generate_reply(self, user_content: str) -> str | None:
        """
        Only sends:
        - 1 system prompt (short, reused)
        - 1 minimal user payload
        """
        try:
            chat_history = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]

            reply = self.llm.get_local_reply(chat_history, self.DEFAULT_TOKENS)

            return reply.strip() if reply else None

        except Exception as e:
            print(f"LLM error: {e}")
            return None

    # -------------------------
    # UPDATE API
    # -------------------------

    def update_items(self, items: list[dict]):
        try:
            url = f"{UPDATE_URL}?lang={self.lang}"
            response = requests.post(url, json=items, timeout=10)
            response.raise_for_status()

            print(f"Updated batch size={len(items)}")

        except Exception as e:
            print(f"Update error: {e}")

    # -------------------------
    # PROCESS SINGLE ITEM (OPTIMIZED)
    # -------------------------

    def process_item(self, item):
        video_id = item.get("video_id")
        title = item.get("title")
        tags = item.get("tags")

        if not video_id or not title:
            return None

        print(f"Processing: {video_id} -> {title}")

        # 🔥 minimal input only (no long prompt engineering per item)
        user_prompt = (
            f"title: {title}\n"
            f"tags: {tags}\n"
            f"language: {self.lang}\n"
        )

        try:
            response = self.generate_reply(user_prompt)

            if not response:
                return None

            data = self.extract_json(response)

            if not data:
                return None

            new_title = data.get("title")
            new_description = data.get("description")

        except Exception as e:
            print(f"Failed to process {video_id}: {e}")
            return None

        print(f"{video_id} Generated title: {new_title}")
        print(f"{video_id} Generated description: {new_description}\n")

        return {
            "lang": self.lang,
            "video_id": video_id,
            "title": new_title,
            "description": new_description,
        }

    # -------------------------
    # JSON PARSER (ROBUST)
    # -------------------------

    def extract_json(self, text: str):
        import json

        if not text:
            return None

        text = text.strip()
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        # fallback extraction
        for pattern in [r"\{.*\}", r"\[.*\]"]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    continue

        return None

    # -------------------------
    # MAIN LOOP
    # -------------------------

    def run(self):
        while True:
            try:
                items = self.fetch_items()

                if not items:
                    print("No items to process")
                    time.sleep(SLEEP_SECONDS)
                    continue

                processed_batch = []

                for item in items:
                    result = self.process_item(item)
                    if result:
                        processed_batch.append(result)

                if processed_batch:
                    self.update_items(processed_batch)

            except Exception as e:
                print(f"Loop error: {e}")
                print(traceback.format_exc())
                time.sleep(SLEEP_SECONDS)


# -------------------------
# ENTRYPOINT
# -------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--type", type=str, default="only_title")
    parser.add_argument("--lang", type=str, default="en")

    args = parser.parse_args()

    processor = TitleProcessor(
        limit=args.limit,
        type=args.type,
        lang=args.lang,
    )

    processor.run()
