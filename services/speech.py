import io

from gtts import gTTS


class SpeechService:
    def __init__(self, audio_folder=None):
        # Retain this argument for compatibility with existing app configuration.
        # Serverless-safe audio is returned as memory data, never written to disk.
        self.audio_folder = audio_folder

    def _normalize_language(self, lang):
        if not lang:
            return 'en'

        normalized = str(lang).strip().lower()
        if normalized in {'auto', 'detect', ''}:
            return 'en'

        language_map = {
            'en': 'en', 'en-us': 'en', 'en-gb': 'en',
            'ur': 'ur', 'ur-pk': 'ur',
            'hi': 'hi', 'hi-in': 'hi',
            'ar': 'ar', 'ar-sa': 'ar',
            'fr': 'fr', 'fr-fr': 'fr',
            'de': 'de', 'de-de': 'de',
            'es': 'es', 'es-es': 'es',
            'it': 'it', 'it-it': 'it',
            'ja': 'ja', 'ja-jp': 'ja',
            'ko': 'ko', 'ko-kr': 'ko',
            'zh': 'zh-cn', 'zh-cn': 'zh-cn', 'zh-tw': 'zh-tw',
        }
        if normalized in language_map:
            return language_map[normalized]
        if normalized.startswith('zh'):
            return 'zh-cn'
        base_code = normalized.split('-', 1)[0]
        return language_map.get(base_code, base_code if len(base_code) in (2, 3) else 'en')

    def generate_audio(self, text, lang='en'):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Text is required for speech synthesis.')

        text = text.strip()
        language_code = self._normalize_language(lang)
        audio_buffer = io.BytesIO()
        try:
            gTTS(text=text, lang=language_code, slow=False).write_to_fp(audio_buffer)
        except Exception as primary_error:
            # Keep the prior English fallback for unsupported TTS language codes.
            if language_code == 'en':
                raise RuntimeError(f'Text-to-speech failed: {primary_error}') from primary_error
            audio_buffer = io.BytesIO()
            try:
                gTTS(text=text, lang='en', slow=False).write_to_fp(audio_buffer)
            except Exception as fallback_error:
                raise RuntimeError(f'Text-to-speech failed: {fallback_error}') from fallback_error

        if audio_buffer.tell() == 0:
            raise RuntimeError('Text-to-speech returned an empty audio stream.')
        audio_buffer.seek(0)
        return audio_buffer
