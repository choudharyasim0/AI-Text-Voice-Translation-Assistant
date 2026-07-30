from deep_translator import GoogleTranslator
import json
import os
from datetime import datetime
from threading import Thread, Lock


class TranslatorService:

    def __init__(self, history_file):

        self.history_file = history_file
        self.translators = {}
        self.history_lock = Lock()

        if not os.path.exists(history_file):

            with open(history_file, "w") as f:
                json.dump([], f)

    def get_translator(self, source, target):
        key = f"{source}:{target}"
        if key not in self.translators:
            self.translators[key] = GoogleTranslator(source=source, target=target)
        return self.translators[key]

    def translate(self, text, source, target, save_history=True):

        translated = self.get_translator(source, target).translate(text)

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
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=4)

    def get_history(self):

        with open(self.history_file) as f:

            return json.load(f)

    def clear_history(self):

        with open(self.history_file, "w") as f:

            json.dump([], f)
