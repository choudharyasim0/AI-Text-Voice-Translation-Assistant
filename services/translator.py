import json
import os
from datetime import datetime
from deep_translator import GoogleTranslator

class TranslatorService:
    def __init__(self, history_file):
        self.history_file = history_file
        self.ensure_history_file()

    def ensure_history_file(self):
        if not os.path.exists(self.history_file):
            try:
                os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except Exception:
                pass

    def translate(self, text, source='auto', target='en', save_history=True):
        try:
            # deep-translator کا استعمال (یہ 100% مستحکم ہے اور رےٹ لمٹ نہیں دیتا)
            translator = GoogleTranslator(source=source, target=target)
            translated_text = translator.translate(text)

            if save_history:
                self.save_to_history(text, translated_text, source, target)

            return translated_text
        except Exception as e:
            raise Exception(f"Translation Error: {str(e)}")

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
            history.insert(0, entry)  # نئی ہسٹری سب سے اوپر آئے گی

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history[:50], f, ensure_ascii=False, indent=2)  # صرف آخری 50 اینٹریز سیو رکھے گا
        except Exception:
            pass

    def clear_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except Exception as e:
            raise Exception(f"Failed to clear history: {str(e)}")
