import json
import os
from datetime import datetime

from deep_translator import GoogleTranslator, MyMemoryTranslator


class TranslatorService:
    def __init__(self, history_file):
        self.history_file = history_file
        self.ensure_history_file()

    def ensure_history_file(self):
        if not os.path.exists(self.history_file):
            try:
                directory = os.path.dirname(self.history_file)
                if directory:
                    os.makedirs(directory, exist_ok=True)

                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except Exception:
                pass

    def translate(self, text, source='auto', target='en', save_history=True):
        try:
            translated_text = GoogleTranslator(
                source=source,
                target=target
            ).translate(text)

            if not translated_text:
                raise ValueError("GoogleTranslator returned an empty translation")

        except Exception as google_error:
            try:
                translated_text = MyMemoryTranslator(
                    source=source,
                    target=target
                ).translate(text)

                if not translated_text:
                    raise ValueError("MyMemoryTranslator returned an empty translation")
            except Exception as fallback_error:
                raise Exception(
                    f"Translation Error: GoogleTranslator failed ({google_error}); "
                    f"MyMemoryTranslator fallback failed ({fallback_error})"
                ) from fallback_error

        if save_history:
            try:
                self.save_to_history(text, translated_text, source, target)
            except Exception:
                pass

        return translated_text

    def get_history(self):
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def save_to_history(self, source_text, translated_text, source_lang, target_lang):
        try:
            history = self.get_history()
            entry = {
                'source_text': source_text,
                'translated_text': translated_text,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            history.insert(0, entry)

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history[:50], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clear_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except Exception as e:
            raise Exception(f"Failed to clear history: {str(e)}") from e
