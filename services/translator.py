import json
import os
import tempfile
import threading
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
    # File storage is ephemeral but writable on Vercel. Keep a process-local fallback
    # for deployments where even /tmp is not writable.
    _memory_history = {}
    _history_lock = threading.RLock()

    def __init__(self, history_file):
        self.history_file = self._get_history_path(history_file)
        self.ensure_history_file()

    @staticmethod
    def _get_history_path(configured_path):
        if os.environ.get('VERCEL') or os.environ.get('ENVIRONMENT', '').lower() == 'production':
            return '/tmp/history.json'
        return configured_path or '/tmp/history.json'

    def ensure_history_file(self):
        with self._history_lock:
            try:
                os.makedirs(os.path.dirname(self.history_file) or '.', exist_ok=True)
                if not os.path.exists(self.history_file):
                    self._write_history([])
            except (OSError, TypeError, ValueError):
                self._memory_history.setdefault(self.history_file, [])

    @staticmethod
    def _mymemory_language_code(language):
        """Map Google/ISO language codes to a code accepted by MyMemory."""
        mymemory_codes = MY_MEMORY_LANGUAGES_TO_CODES
        value = str(language).strip()
        lowered = value.lower()

        for name, code in mymemory_codes.items():
            if lowered in {name.lower(), code.lower()}:
                return code

        google_name = next(
            (name for name, code in GOOGLE_LANGUAGES_TO_CODES.items()
             if code.lower() == lowered),
            None,
        )
        if google_name and google_name.lower() in mymemory_codes:
            return mymemory_codes[google_name.lower()]

        base_code = lowered.split('-', 1)[0]
        for name, code in mymemory_codes.items():
            if code.split('-', 1)[0].lower() == base_code:
                return code

        raise ValueError(f"MyMemory does not support language code '{language}'.")

    @staticmethod
    def _split_for_mymemory(text, limit=450):
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
        translations = [
            MyMemoryTranslator(
                source=mymemory_source,
                target=mymemory_target
            ).translate(chunk)
            for chunk in self._split_for_mymemory(text)
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

        text, source, target = text.strip(), source.strip(), target.strip()
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
                translated_text = self._translate_with_mymemory(text, fallback_source, target)
            except Exception as fallback_error:
                raise TranslationError(
                    'Translation providers failed. Google error: '
                    f'{google_error}. MyMemory error: {fallback_error}'
                ) from fallback_error

        translated_text = translated_text.strip()
        if save_history:
            self.save_to_history(text, translated_text, source, target)
        return translated_text

    def _read_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as history_file:
                data = json.load(history_file)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return list(self._memory_history.get(self.history_file, []))

    def _write_history(self, history):
        """Write atomically where possible; callers provide the history lock."""
        directory = os.path.dirname(self.history_file) or '.'
        os.makedirs(directory, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(prefix='.history-', suffix='.json', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as history_file:
                json.dump(history[:50], history_file, ensure_ascii=False, indent=2)
            os.replace(temporary_path, self.history_file)
        except Exception:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
            raise

    def get_history(self):
        with self._history_lock:
            try:
                history = self._read_history()
                self._memory_history[self.history_file] = list(history[:50])
                return history[:50]
            except Exception:
                return list(self._memory_history.get(self.history_file, []))

    def save_to_history(self, source_text, translated_text, source_lang, target_lang):
        with self._history_lock:
            entry = {
                'source_text': source_text,
                'translated_text': translated_text,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            history = self._read_history()
            history.insert(0, entry)
            history = history[:50]
            self._memory_history[self.history_file] = list(history)
            try:
                self._write_history(history)
            except Exception:
                # In-memory history keeps the current serverless instance usable.
                pass

    def clear_history(self):
        with self._history_lock:
            self._memory_history[self.history_file] = []
            try:
                self._write_history([])
            except Exception:
                # Clearing in-memory state is sufficient when storage is unavailable.
                pass
