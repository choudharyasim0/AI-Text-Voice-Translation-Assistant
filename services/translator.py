import json
import os
import tempfile
import threading
from datetime import datetime

from deep_translator import GoogleTranslator


class TranslatorService:
    _memory_history = {}
    _history_lock = threading.RLock()

    def __init__(self, history_file):
        # Vercel's writable filesystem is /tmp; other deployments use configured path.
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
            except (OSError, TypeError, ValueError):
                self._memory_history.setdefault(self.history_file, [])

    def translate(self, text, source='auto', target='en', save_history=True):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Text is required for translation.')

        original_text = text
        text_to_translate = text.strip()
        try:
            translated_text = GoogleTranslator(
                source=source,
                target=target
            ).translate(text_to_translate)
            if not isinstance(translated_text, str) or not translated_text.strip():
                raise ValueError('Empty translation received.')
        except Exception as exc:
            raise RuntimeError(f'Translation Error: {exc}') from exc

        if save_history:
            self.save_to_history(original_text, translated_text, source, target)
        return translated_text

    def _read_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as file:
                history = json.load(file)
            if isinstance(history, list):
                return history
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
        return list(self._memory_history.get(self.history_file, []))

    def _write_history(self, history):
        directory = os.path.dirname(self.history_file) or '.'
        os.makedirs(directory, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(
            prefix='.history-', suffix='.json', dir=directory
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                json.dump(history[:50], file, ensure_ascii=False, indent=2)
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
                history = self._read_history()[:50]
                self._memory_history[self.history_file] = list(history)
                return history
            except Exception:
                return list(self._memory_history.get(self.history_file, []))

    def save_to_history(self, source_text, translated_text, source_lang, target_lang):
        """Store complete input and output strings; file persistence is best-effort."""
        entry = {
            'source_text': str(source_text),
            'translated_text': str(translated_text),
            'source_lang': str(source_lang),
            'target_lang': str(target_lang),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        with self._history_lock:
            history = self._read_history()
            history.insert(0, entry)
            history = history[:50]
            self._memory_history[self.history_file] = list(history)
            try:
                self._write_history(history)
            except (OSError, TypeError, ValueError):
                # Preserve the entry in memory; history storage must not break translation.
                pass

    def clear_history(self):
        with self._history_lock:
            self._memory_history[self.history_file] = []
            try:
                self._write_history([])
            except (OSError, TypeError, ValueError):
                # The in-memory history is cleared even if /tmp cannot be written.
                pass
