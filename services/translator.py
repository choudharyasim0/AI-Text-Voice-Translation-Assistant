
import json
import os
import html
import urllib.request
import urllib.error

from datetime import datetime
from threading import Thread, Lock


class TranslatorService:

    def __init__(self, history_file):

        self.history_file = history_file
        self.history_lock = Lock()

        if not os.path.exists(history_file):
            with open(history_file, "w") as f:
                json.dump([], f)

    def translate(self, text, source, target, save_history=True):

        api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")

        if not api_key:
            raise RuntimeError(
                "Google Translation API key is missing. "
                "Configure GOOGLE_TRANSLATE_API_KEY in Vercel."
            )

        payload = {
            "q": text,
            "target": target,
            "format": "text"
        }

        # Auto-detection: source language is omitted
        if source and source.lower() != "auto":
            payload["source"] = source

        request_data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            "https://translation.googleapis.com/language/translate/v2",
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            translated = html.unescape(
                result["data"]["translations"][0]["translatedText"]
            )

        except urllib.error.HTTPError as error:

            try:
                error_data = json.loads(
                    error.read().decode("utf-8")
                )

                message = error_data.get(
                    "error", {}
                ).get(
                    "message",
                    "Google Translation API request failed."
                )

            except Exception:
                message = "Google Translation API request failed."

            raise RuntimeError(message) from None

        except urllib.error.URLError:
            raise RuntimeError(
                "Unable to connect to Google Translation API."
            ) from None

        except (KeyError, IndexError, ValueError):
            raise RuntimeError(
                "Invalid response received from Google Translation API."
            ) from None

        if save_history:
            Thread(
                target=self.save_history,
                args=(text, translated, source, target),
                daemon=True
            ).start()

        return translated

    def save_history(
        self,
        original,
        translated,
        source,
        target
    ):

        with self.history_lock:

            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)

            except (json.JSONDecodeError, FileNotFoundError):
                data = []

            data.append({
                "original": original,
                "translated": translated,
                "source": source,
                "target": target,
                "time": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            })

            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=4)

    def get_history(self):

        with open(self.history_file) as f:
            return json.load(f)

    def clear_history(self):

        with open(self.history_file, "w") as f:
            json.dump([], f)
