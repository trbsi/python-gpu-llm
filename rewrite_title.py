import argparse
import re
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
    DEFAULT_TOKENS = 150
    BATCH_TITLES = False
    LAST_ID = 0

    def __init__(self, limit: int, workers: int, type: str, lang: str):
        self.limit = limit
        self.workers = workers
        self.type = type
        self.lang = lang

        self.llm = LlmReplyService()
        self.llm.init()

    def is_batch_titles(self):
        return self.type == 'batch_titles'

    def is_only_title(self):
        return self.type == 'only_title'

    def is_only_description(self):
        return self.type == 'only_description'

    def is_title_and_description(self):
        return self.type == 'title_and_description'

    def fetch_items(self):
        try:
            response = requests.get(GET_URL, params={"limit": self.limit, "last_id": self.LAST_ID}, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.LAST_ID = int(data.get("last_id"))
            return data.get("items", [])
        except Exception as e:
            print(f"Fetch error: {e}")
            return []

    def generate_reply(self, content: str) -> str | None:
        chat_history = [
            {
                "role": "user",
                "content": content
            }
        ]

        try:
            max_tokens = self.DEFAULT_TOKENS * 10 if self.is_batch_titles() else self.DEFAULT_TOKENS
            reply = self.llm.get_local_reply(chat_history, max_tokens)
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
            url = f"{UPDATE_URL}?lang={self.lang}"
            response = requests.post(url, json=payload, timeout=10)
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

        if self.is_only_title():
            title_content = (
                "Rewrite title column to be SEO friendly and different but keep same meaning. Make description human like. Like how human would write the title for the porn clip. Title can be max 50 characters."
                f'Make it dirty. Use porn words. Do it all in English language. Respond only with new title: "{title}"'
            )
            new_title = self.generate_reply(title_content)
            if not new_title:
                return None
        elif self.is_only_description():
            description_content = (
                'Use porn words, be extra dirty, nasty, raw and creative. Make description human like. Like how human would describe the porn clip.'
                f'Give me a description of a porn clip for the title, reply only with description, up to 150 words, make sure to end sentence with a dot. Do it all in English language. Title is: "{title}"'
            )
            new_description = self.generate_reply(description_content)
        elif self.is_title_and_description():
            content = ''
            if self.lang == 'en':
                content += 'Use English language.'
            elif self.lang == 'hr' or self.lang == 'sr':
                content += 'Use Serbian language.'
            elif self.lang == 'es':
                content += 'Use Spanish language.'
            elif self.lang == 'pt':
                content += 'Use Portuguese language.'
            elif self.lang == 'de':
                content += 'Use German language.'
            elif self.lang == 'ru':
                content += 'Use Russian language.'

            content += (
                'Rewrite title column to be SEO friendly and different but keep same meaning, make it dirty, nasty and raw, use porn words. Title can be max 50 characters.'
                'Then generate description, use porn words, be extra dirty, nasty, raw and creative.'
                'Make description and title human like. Like how human would write the description and title for the porn clip.'
                'Respond in valid JSON format: { "title": "", "description": "" }'
                f'Original title: "{title}"'
            )
            response = self.generate_reply(content)
            response = self.extract_json(response)
            new_title = response.get("title")
            new_description = response.get("description")

        print(f"{video_id} Generated title: {new_title}")
        print(f"{video_id} Generated description: {new_description}")
        print("")

        return {
            "lang": self.lang,
            "video_id": video_id,
            "title": new_title,
            "description": new_description,
        }

    def extract_json(self, text: str):
        import json

        text = text.strip().replace("```json", "").replace("```", "").strip()

        # Try direct parse first (fast path)
        try:
            return json.loads(text)
        except:
            pass

        # Fallback: extract first JSON-like structure
        for pattern in [r'\[.*\]', r'\{.*\}']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    continue

        return None

    def build_titles_text(self, items):
        return "\n".join(
            f"{item['video_id']}. {item['title']}"
            for i, item in enumerate(items)
        )

    def run(self):
        while True:
            try:
                items = self.fetch_items()

                if not items:
                    time.sleep(SLEEP_SECONDS)
                    continue

                # =========================
                # 🔥 BATCH MODE (NEW)
                # =========================
                if self.BATCH_TITLES:
                    titles_text = self.build_titles_text(items)

                    prompt = (
                        "Rewrite title column to be SEO friendly and different but keep same meaning, make it dirty, nasty and raw, use porn words.\n"
                        "Then generate description, use porn words, be extra dirty, nasty, raw and creative.\n"
                        'Return ONLY valid JSON array:[{"video_id": ..., "title": "...", "description": "..."}]'
                        "\n"
                        f"Titles:\n{titles_text}"
                    )

                    response = self.generate_reply(prompt)
                    response = self.extract_json(response)
                    print(response)

                    if not response:
                        print("Batch JSON parse failed")
                        continue

                    # If model does NOT return video_id, map manually
                    processed_batch = []

                    for i, item in enumerate(items):
                        if i < len(response):
                            r = response[i]
                            processed_batch.append({
                                "video_id": item["video_id"],
                                "title": r.get("title"),
                                "description": r.get("description"),
                            })

                    if processed_batch:
                        self.update_items(processed_batch)

                    time.sleep(SLEEP_SECONDS)
                    continue

                # =========================
                # 🔥 PARALLEL MODE (OLD)
                # =========================
                processed_batch = []

                with ThreadPoolExecutor(max_workers=self.workers) as executor:
                    futures = [executor.submit(self.process_item, item) for item in items]

                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            if result:
                                processed_batch.append(result)
                        except Exception as e:
                            print(f"Worker error: {e}")

                if processed_batch:
                    self.update_items(processed_batch)

            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(SLEEP_SECONDS)


# Usage: python3 rewrite_title --type=title_and_description --lang=en
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--type", type=str, default='only_title')
    parser.add_argument("--lang", type=str, default='en')

    args = parser.parse_args()

    processor = TitleProcessor(
        limit=args.limit,
        workers=args.workers,
        type=args.type,
        lang=args.lang,
    )
    processor.run()
