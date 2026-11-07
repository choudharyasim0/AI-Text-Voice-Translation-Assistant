import json
import os
import tempfile
import threading
from datetime import datetime

from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.constants import MY_MEMORY_LANGUAGES_TO_CODES


class TranslationError(RuntimeError):
    """Raised when all translation providers fail."""


class TranslatorService:
    _memory_history = {}
    _history_lock = threading.RLock()

    def __init__(self, history_file='/tmp/history.json'):
        # Vercel's writable filesystem is limited to /tmp.
        self.history_file = (
            '/tmp/history.json'
            if os.environ.get('VERCEL')
            else (history_file or '/tmp/history.json')
        )
        self.ensure_history_file()

    def ensure_history_file(self):
        with self._history_lock:
            try:
                directory = os.path.dirname(self.history_file) or '.'
                os.makedirs(directory, exist_ok=True)
                if not os.path.exists(self.history_file):
                    self._write_history([])
            except Exception:
                self._memory_history.setdefault(self.history_file, [])

    @staticmethod
    def _mymemory_code(language):
        value = str(language).strip()
        if value.lower() in {'auto', 'detect', 'autodetect'}:
            return 'auto'

        codes = MY_MEMORY_LANGUAGES_TO_CODES
        lowered = value.lower()
        for name, code in codes.items():
            if lowered in {name.lower(), code.lower()}:
                return code

        base = lowered.split('-', 1)[0]
        for code in codes.values():
            if code.split('-', 1)[0].lower() == base:
                return code
        raise ValueError(f"MyMemory does not support language '{language}'.")

    def translate(self, text, source='auto', target='en', save_history=True):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Text is required for translation.')
        if not isinstance(source, str) or not source.strip():
            raise ValueError('A source language is required.')
        if not isinstance(target, str) or not target.strip():
            raise ValueError('A target language is required.')

        original_text = text
        text_to_translate = text.strip()
        source = source.strip()
        target = target.strip()

        try:
            translated_text = GoogleTranslator(
                source=source, target=target
            ).translate(text_to_translate)
            if not isinstance(translated_text, str) or not translated_text.strip():
                raise ValueError('Google Translator returned an empty translation.')
        except Exception as google_error:
            try:
                memory_source = self._mymemory_code(source)
                memory_target = self._mymemory_code(target)
                # MyMemory limits an individual request; split long paragraphs while
                # retaining the full source and output in history.
                parts = []
                remaining = text_to_translate
                while remaining:
                    if len(remaining) <= 450:
                        part, remaining = remaining, ''
                    else:
                        cut = remaining.rfind(' ', 0, 451)
                        if cut <= 0:
                            cut = 450
                        part, remaining = remaining[:cut], remaining[cut:].lstrip()
                    result = MyMemoryTranslator(
                        source=memory_source, target=memory_target
                    ).translate(part)
                    if not isinstance(result, str) or not result.strip():
                        raise ValueError('MyMemory returned an empty translation.')
                    parts.append(result.strip())
                translated_text = ' '.join(parts)
            except Exception as fallback_error:
                raise TranslationError(
                    'Translation failed with both providers. '
                    f'Google error: {google_error}. MyMemory error: {fallback_error}'
                ) from fallback_error

        translated_text = translated_text.strip()
        if save_history:
            try:
                self.save_to_history(original_text, translated_text, source, target)
            except Exception:
                # A history-storage problem must never fail a successful translation.
                pass
        return translated_text

    def _read_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as file:
                history = json.load(file)
            return history if isinstance(history, list) else []
        except Exception:
            return list(self._memory_history.get(self.history_file, []))

    def _write_history(self, history):
        directory = os.path.dirname(self.history_file) or '.'
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix='.history-', suffix='.json', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                json.dump(history[:50], file, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.history_file)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def get_history(self):
        with self._history_lock:
            try:
                history = self._read_history()[:50]
                self._memory_history[self.history_file] = list(history)
                return history
            except Exception:
                return list(self._memory_history.get(self.history_file, []))

    def save_to_history(self, source_text, translated_text, source_lang, target_lang):
        entry = {
            'source_text': str(source_text),
            'translated_text': str(translated_text),
            'source_lang': str(source_lang),
            'target_lang': str(target_lang),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        with self._history_lock:
            try:
                history = self._read_history()
                history.insert(0, entry)
                history = history[:50]
                self._memory_history[self.history_file] = list(history)
                self._write_history(history)
            except Exception:
                # Preserve best-effort in-memory history and never propagate I/O errors.
                current = list(self._memory_history.get(self.history_file, []))
                if not current or current[0] != entry:
                    current.insert(0, entry)
                self._memory_history[self.history_file] = current[:50]

    def clear_history(self):
        with self._history_lock:
            self._memory_history[self.history_file] = []
            try:
                self._write_history([])
            except Exception:
                pass
