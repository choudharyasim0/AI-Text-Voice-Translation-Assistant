import json
import os
from datetime import datetime

from deep_translator import GoogleTranslator, MyMemoryTranslator
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
                # History is best-effort; translation can still work if storage is unavailable.
                pass

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
            translated_text = GoogleTranslator(
                source=source,
                target=target
            ).translate(text)
            if not isinstance(translated_text, str) or not translated_text.strip():
                raise ValueError('GoogleTranslator returned an empty translation.')
        except Exception as google_error:
            fallback_source = source
            if source.lower() in {'auto', 'autodetect', 'detect'}:
                try:
                    fallback_source = detect(text)
                except LangDetectException as detection_error:
                    raise TranslationError(
                        'Google translation failed, and the source language could not '
                        'be detected for the MyMemory fallback. Select the source '
                        'language and try again.'
                    ) from detection_error
                except Exception as detection_error:
                    raise TranslationError(
                        'Google translation failed, and the source language could not '
                        'be detected for the MyMemory fallback. Select the source '
                        'language and try again.'
                    ) from detection_error

            try:
                translated_text = MyMemoryTranslator(
                    source=fallback_source,
                    target=target
                ).translate(text)
                if not isinstance(translated_text, str) or not translated_text.strip():
                    raise ValueError('MyMemoryTranslator returned an empty translation.')
            except Exception as fallback_error:
                raise TranslationError(
                    'Translation failed with both Google Translate and MyMemory. '
                    'Check the language selection and try again later.'
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
            entry = {
                'source_text': source_text,
                'translated_text': translated_text,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            history.insert(0, entry)

            directory = os.path.dirname(self.history_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history[:50], f, ensure_ascii=False, indent=2)
        except (OSError, TypeError, ValueError):
            # Do not fail a successful translation because history storage failed.
            pass

    def clear_history(self):
        try:
            directory = os.path.dirname(self.history_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except OSError as e:
            raise RuntimeError(f'Failed to clear history: {e}') from e
