from deep_translator import GoogleTranslator


class LanguageService:
    # Used only if the translator library cannot provide its supported-language list.
    FALLBACK_LANGUAGES = {
        'auto': 'Auto Detect',
        'ar': 'Arabic',
        'bn': 'Bengali',
        'de': 'German',
        'en': 'English',
        'es': 'Spanish',
        'fa': 'Persian',
        'fr': 'French',
        'hi': 'Hindi',
        'it': 'Italian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'tr': 'Turkish',
        'ur': 'Urdu',
        'zh-CN': 'Chinese (Simplified)',
    }

    @staticmethod
    def get_languages():
        try:
            languages = GoogleTranslator().get_supported_languages(as_dict=True)
            inverted_languages = {
                code: name.title()
                for name, code in languages.items()
            }
            return {'auto': 'Auto Detect', **dict(sorted(
                inverted_languages.items(), key=lambda item: item[1].lower()
            ))}
        except Exception:
            # Keep the UI usable when the provider is offline or rate-limited.
            return dict(LanguageService.FALLBACK_LANGUAGES)
