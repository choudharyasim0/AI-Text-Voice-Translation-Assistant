from deep_translator import GoogleTranslator


class LanguageService:
    @staticmethod
    def get_languages():
        """
        Returns all languages supported by Google Translator.
        """
        languages = GoogleTranslator().get_supported_languages(as_dict=True)

        # Add Auto Detect manually
        language_dict = {
            "auto": "Auto Detect"
        }

        # GoogleTranslator returns language name -> code, so invert to code -> label.
        inverted_languages = {
            code: name.title()
            for name, code in languages.items()
        }

        sorted_languages = dict(sorted(inverted_languages.items(), key=lambda item: item[1].lower()))
        language_dict.update(sorted_languages)

        return language_dict