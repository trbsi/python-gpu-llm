import argparse
import re
import time

import requests
from dotenv import load_dotenv
from llm_reply import LlmReplyService

GET_URL = "https://peachka.net/movies/api/get-title"
UPDATE_URL = "https://peachka.net/movies/api/update-title"

SLEEP_SECONDS = 2  # delay between requests

load_dotenv()


# Usage: python3 rewrite_title.py --type=title_and_description --lang=en
class TitleProcessor:
    DEFAULT_TOKENS = 150
    LAST_ID = 0

    def __init__(self, limit: int, type: str, lang: str):
        self.limit = limit
        self.type = type
        self.lang = lang

        self.llm = LlmReplyService()
        self.llm.init()

    def is_only_title(self):
        return self.type == 'only_title'

    def is_only_description(self):
        return self.type == 'only_description'

    def is_title_and_description(self):
        return self.type == 'title_and_description'

    def fetch_items(self):
        try:
            params = {"limit": self.limit, "last_id": self.LAST_ID, "lang": self.lang}
            response = requests.get(GET_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.LAST_ID = int(data.get("last_id"))
            return data.get("items", [])
        except Exception as e:
            print(f"Fetch error: {e}")
            return []

    def generate_reply(self, content: str) -> str | None:
        chat_history = [{"role": "user", "content": content}]

        try:
            reply = self.llm.get_local_reply(chat_history, self.DEFAULT_TOKENS)
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
        try:
            url = f"{UPDATE_URL}?lang={self.lang}"
            response = requests.post(url, json=items, timeout=10)
            response.raise_for_status()
            print(f"Updated batch size={len(items)}")
        except Exception as e:
            print(f"Update error: {e}")

    def process_item(self, item):
        video_id = item.get("video_id")
        title = item.get("title")
        tags = item.get("tags")

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
            if self.lang == 'en':
                content_lang = 'Use English language.'
            elif self.lang == 'hr' or self.lang == 'sr':
                content_lang = 'Use Serbian language.'
            elif self.lang == 'es':
                content_lang = 'Use Spanish language.'
            elif self.lang == 'pt':
                content_lang = 'Use Portuguese language.'
            elif self.lang == 'de':
                content_lang = 'Use German language.'
            elif self.lang == 'ru':
                content_lang = 'Use Russian language.'

            content = (
                'Rewrite the title and generate a description for this adult video clip. Use the provided tags to inform both the title and description.'
                'Title guidelines:'
                'Rewrite to be SEO-optimized while sounding natural and human. Use title and tags to construct title. '
                'Use explicit, direct language that matches how adult content is actually searched for. Avoid robotic or overly formal phrasing.'
                'Description guidelines:'
                'Write 3–5 sentences in a casual, first-person or observational tone — like a real user or uploader wrote it'
                'Lead with the most searchable/compelling detail'
                'Weave in relevant tags naturally (don\'t just list them)'
                'Be vivid and specific to the actual scene'
                'Format — respond only in valid JSON: { "title": "", "description": "" }'
                f'Original title: "{title}"'
                f'Tags: "{tags}"'
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

        try:
            return json.loads(text)
        except:
            pass

        for pattern in [r'\[.*\]', r'\{.*\}']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    continue

        return None

    def run(self):
        while True:
            try:
                items = self.fetch_items()

                if not items:
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
                time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--type", type=str, default='only_title')
    parser.add_argument("--lang", type=str, default='en')

    args = parser.parse_args()

    processor = TitleProcessor(
        limit=args.limit,
        type=args.type,
        lang=args.lang,
    )
    processor.run()
