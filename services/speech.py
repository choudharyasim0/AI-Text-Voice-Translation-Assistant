import os
import uuid
from datetime import datetime, timedelta

from gtts import gTTS


class SpeechService:
    def __init__(self, audio_folder):
        self.audio_folder = audio_folder
        os.makedirs(audio_folder, exist_ok=True)
        self._cleanup_old_files()

    def _normalize_language(self, lang):
        if not lang:
            return "en"

        normalized = str(lang).strip().lower()
        if normalized in {"auto", "detect", ""}:
            return "en"

        language_map = {
            "en": "en",
            "en-us": "en",
            "en-gb": "en",
            "ur": "ur",
            "ur-pk": "ur",
            "hi": "hi",
            "hi-in": "hi",
            "ar": "ar",
            "ar-sa": "ar",
            "fr": "fr",
            "fr-fr": "fr",
            "de": "de",
            "de-de": "de",
            "es": "es",
            "es-es": "es",
            "it": "it",
            "it-it": "it",
            "ja": "ja",
            "ja-jp": "ja",
            "ko": "ko",
            "ko-kr": "ko",
            "zh": "zh-cn",
            "zh-cn": "zh-cn",
            "zh-tw": "zh-tw",
        }

        if normalized in language_map:
            return language_map[normalized]

        if normalized.startswith("zh"):
            return "zh-cn"

        if "-" in normalized:
            base_code = normalized.split("-", 1)[0]
            if base_code in language_map:
                return language_map[base_code]

        return "en"

    def _cleanup_old_files(self, max_age_minutes=60, max_files=100):
        try:
            files = []
            for filename in os.listdir(self.audio_folder):
                path = os.path.join(self.audio_folder, filename)
                if not os.path.isfile(path):
                    continue
                if not filename.lower().endswith(".mp3"):
                    continue
                created_at = datetime.fromtimestamp(os.path.getmtime(path))
                files.append((created_at, path))

            files.sort(key=lambda item: item[0])
            cutoff = datetime.now() - timedelta(minutes=max_age_minutes)

            for created_at, path in files:
                if len(files) > max_files or created_at < cutoff:
                    try:
                        os.remove(path)
                    except OSError:
                        continue

        except FileNotFoundError:
            os.makedirs(self.audio_folder, exist_ok=True)

    def generate_audio(self, text, lang):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text is required for speech synthesis.")

        language_code = self._normalize_language(lang)
        filename = f"{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(self.audio_folder, filename)

        try:
            tts = gTTS(text=text, lang=language_code, slow=False)
            tts.save(filepath)
            self._cleanup_old_files()
            return filepath
        except Exception as exc:
            if os.path.exists(filepath):
                os.remove(filepath)

            try:
                fallback_tts = gTTS(text=text, lang="en", slow=False)
                fallback_tts.save(filepath)
                self._cleanup_old_files()
                return filepath
            except Exception as fallback_exc:
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise RuntimeError(f"Text-to-speech failed: {fallback_exc}") from fallback_exc