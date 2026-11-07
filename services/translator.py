import json
import os
import re
from datetime import datetime

from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.constants import (
    GOOGLE_LANGUAGES_TO_CODES,
    MY_MEMORY_LANGUAGES_TO_CODES,
)
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException


class TranslationError(RuntimeError):
    """Raised when all configured translation providers fail."""


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
            except OSError:
                # Translation should remain available if history storage is unavailable.
                pass

    @staticmethod
    def _mymemory_language_code(language):
        """Map Google/ISO language codes to a code accepted by MyMemory."""
        mymemory_codes = MY_MEMORY_LANGUAGES_TO_CODES
        value = str(language).strip()
        lowered = value.lower()

        # MyMemory uses regional tags (for example fr-FR and en-GB), unlike
        # Google's short codes (fr, en). Accept MyMemory's exact codes/names first.
        for name, code in mymemory_codes.items():
            if lowered == name.lower() or lowered == code.lower():
                return code

        google_name = next(
            (name for name, code in GOOGLE_LANGUAGES_TO_CODES.items()
             if code.lower() == lowered),
            None,
        )
        if google_name:
            mapped = mymemory_codes.get(google_name.lower())
            if mapped:
                return mapped

        # For regional codes, try exact base code against MyMemory variants.
        base_code = lowered.split('-', 1)[0]
        candidates = [
            code for code in mymemory_codes.values()
            if code.split('-', 1)[0].lower() == base_code
        ]
        if candidates:
            return candidates[0]

        # Detection packages may return a code absent from Google's language table.
        # Match its base code against MyMemory's regional language codes as well.
        raise ValueError(f"MyMemory does not support language code '{language}'.")

    @staticmethod
    def _split_for_mymemory(text, limit=450):
        """Split long input into request-sized pieces without splitting words."""
        chunks = []
        remaining = text.strip()
        while remaining:
            if len(remaining) <= limit:
                chunks.append(remaining)
                break

            split_at = remaining.rfind(' ', 0, limit + 1)
            if split_at <= 0:
                split_at = limit
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        return chunks

    def _translate_with_mymemory(self, text, source, target):
        mymemory_source = self._mymemory_language_code(source)
        mymemory_target = self._mymemory_language_code(target)
        chunks = self._split_for_mymemory(text)
        translations = [
            MyMemoryTranslator(source=mymemory_source, target=mymemory_target).translate(chunk)
            for chunk in chunks
        ]
        if any(not isinstance(part, str) or not part.strip() for part in translations):
            raise ValueError('MyMemory returned an empty translation.')
        return ' '.join(part.strip() for part in translations)

    def translate(self, text, source='auto', target='en', save_history=True):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Text is required for translation.')
        if not isinstance(source, str) or not source.strip():
            raise ValueError('A source language is required.')
        if not isinstance(target, str) or not target.strip():
            raise ValueError('A target language is required.')

        text = text.strip()
        source = source.strip()
        target = target.strip()

        try:
            translated_text = GoogleTranslator(source=source, target=target).translate(text)
            if not isinstance(translated_text, str) or not translated_text.strip():
                raise ValueError('Google returned an empty translation.')
        except Exception as google_error:
            fallback_source = source
            if source.lower() in {'auto', 'autodetect', 'detect'}:
                try:
                    fallback_source = detect(text)
                except (LangDetectException, Exception) as detection_error:
                    raise TranslationError(
                        'Google translation failed and the source language could not be '
                        'detected. Select a source language and try again.'
                    ) from detection_error

            try:
                translated_text = self._translate_with_mymemory(
                    text, fallback_source, target
                )
            except Exception as fallback_error:
                raise TranslationError(
                    'Translation providers failed. Google error: '
                    f'{google_error}. MyMemory error: {fallback_error}'
                ) from fallback_error

        translated_text = translated_text.strip()
        if save_history:
            self.save_to_history(text, translated_text, source, target)
        return translated_text

    def get_history(self):
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return history if isinstance(history, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def save_to_history(self, source_text, translated_text, source_lang, target_lang):
        try:
            history = self.get_history()
            history.insert(0, {
                'source_text': source_text,
                'translated_text': translated_text,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })
            directory = os.path.dirname(self.history_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history[:50], f, ensure_ascii=False, indent=2)
        except (OSError, TypeError, ValueError):
            # A history write failure must not invalidate a successful translation.
            pass

    def clear_history(self):
        try:
            directory = os.path.dirname(self.history_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except OSError as exc:
            raise RuntimeError(f'Failed to clear history: {exc}') from exc
