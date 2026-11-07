import io

from gtts import gTTS


class SpeechService:
    def __init__(self, audio_folder=None):
        # Keep the parameter for compatibility; generated audio is never written to disk.
        self.audio_folder = audio_folder

    @staticmethod
    def _normalize_language(lang):
        if not lang:
            return 'en'
        normalized = str(lang).strip().lower()
        if normalized in {'auto', 'detect', ''}:
            return 'en'
        aliases = {
            'en-us': 'en', 'en-gb': 'en', 'ur-pk': 'ur', 'hi-in': 'hi',
            'ar-sa': 'ar', 'fr-fr': 'fr', 'de-de': 'de', 'es-es': 'es',
            'it-it': 'it', 'ja-jp': 'ja', 'ko-kr': 'ko',
            'zh': 'zh-cn', 'zh-tw': 'zh-tw',
        }
        if normalized.startswith('zh'):
            return aliases.get(normalized, 'zh-cn')
        code = aliases.get(normalized, normalized.split('-', 1)[0])
        return code if len(code) in (2, 3) else 'en'

    def generate_audio(self, text, lang='en'):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Text is required for speech synthesis.')

        language = self._normalize_language(lang)
        buffer = io.BytesIO()
        try:
            gTTS(text=text.strip(), lang=language, slow=False).write_to_fp(buffer)
        except Exception as primary_error:
            if language == 'en':
                raise RuntimeError(f'Text-to-speech failed: {primary_error}') from primary_error
            buffer = io.BytesIO()
            try:
                gTTS(text=text.strip(), lang='en', slow=False).write_to_fp(buffer)
            except Exception as fallback_error:
                raise RuntimeError(f'Text-to-speech failed: {fallback_error}') from fallback_error

        if not buffer.getvalue():
            raise RuntimeError('Text-to-speech returned an empty audio stream.')
        buffer.seek(0)
        return buffer
