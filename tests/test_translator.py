import json

import pytest

from services import translator as translator_module
from services.translator import TranslationError, TranslatorService


@pytest.fixture
def service(tmp_path):
    return TranslatorService(str(tmp_path / 'history' / 'translations.json'))


def test_google_translation_saves_history(service, monkeypatch):
    class FakeGoogleTranslator:
        def __init__(self, source, target):
            assert source == 'en'
            assert target == 'fr'

        def translate(self, text):
            assert text == 'hello'
            return 'bonjour'

    monkeypatch.setattr(translator_module, 'GoogleTranslator', FakeGoogleTranslator)
    result = service.translate('hello', 'en', 'fr')

    assert result == 'bonjour'
    assert service.get_history()[0]['translated_text'] == 'bonjour'


def test_google_failure_uses_mymemory_with_detected_auto_source(service, monkeypatch):
    class FailedGoogleTranslator:
        def __init__(self, **kwargs):
            raise RuntimeError('rate limited')

    class FakeMyMemoryTranslator:
        def __init__(self, source, target):
            assert source == 'fr'
            assert target == 'en'

        def translate(self, text):
            return 'hello'

    monkeypatch.setattr(translator_module, 'GoogleTranslator', FailedGoogleTranslator)
    monkeypatch.setattr(translator_module, 'MyMemoryTranslator', FakeMyMemoryTranslator)
    monkeypatch.setattr(translator_module, 'detect', lambda text: 'fr')

    assert service.translate('bonjour', 'auto', 'en', save_history=False) == 'hello'
    assert service.get_history() == []


def test_both_providers_failing_returns_safe_translation_error(service, monkeypatch):
    class FailedTranslator:
        def __init__(self, **kwargs):
            raise RuntimeError('provider unavailable')

    monkeypatch.setattr(translator_module, 'GoogleTranslator', FailedTranslator)
    monkeypatch.setattr(translator_module, 'MyMemoryTranslator', FailedTranslator)

    with pytest.raises(TranslationError, match='both Google Translate and MyMemory'):
        service.translate('hello', 'en', 'fr', save_history=False)


def test_invalid_empty_text_is_rejected(service):
    with pytest.raises(ValueError, match='Text is required'):
        service.translate('  ', save_history=False)


def test_history_is_limited_and_clearable(service):
    service.save_to_history('hello', 'bonjour', 'en', 'fr')
    assert json.loads(open(service.history_file, encoding='utf-8').read())[0]['source_text'] == 'hello'
    service.clear_history()
    assert service.get_history() == []
