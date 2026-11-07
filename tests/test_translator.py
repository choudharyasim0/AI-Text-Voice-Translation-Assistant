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
            assert (source, target) == ('en', 'fr')

        def translate(self, text):
            assert text == 'hello'
            return 'bonjour'

    monkeypatch.setattr(translator_module, 'GoogleTranslator', FakeGoogleTranslator)
    assert service.translate('hello', 'en', 'fr') == 'bonjour'
    assert service.get_history()[0]['translated_text'] == 'bonjour'


def test_google_failure_uses_regional_mymemory_codes_and_detected_source(service, monkeypatch):
    class FailedGoogleTranslator:
        def __init__(self, **kwargs):
            raise RuntimeError('rate limited')

    class FakeMyMemoryTranslator:
        def __init__(self, source, target):
            assert (source, target) == ('fr-FR', 'en-GB')

        def translate(self, text):
            return 'hello'

    monkeypatch.setattr(translator_module, 'GoogleTranslator', FailedGoogleTranslator)
    monkeypatch.setattr(translator_module, 'MyMemoryTranslator', FakeMyMemoryTranslator)
    monkeypatch.setattr(translator_module, 'detect', lambda text: 'fr')

    assert service.translate('bonjour', 'auto', 'en', save_history=False) == 'hello'
    assert service.get_history() == []


def test_google_code_is_mapped_to_mymemory_language_code(service):
    assert service._mymemory_language_code('fr') == 'fr-FR'
    assert service._mymemory_language_code('en') == 'en-GB'
    assert service._mymemory_language_code('zh-CN') == 'zh-CN'


def test_unsupported_mymemory_language_has_actionable_error(service, monkeypatch):
    monkeypatch.setattr(
        translator_module,
        'GoogleTranslator',
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError('rate limited')),
    )
    with pytest.raises(TranslationError, match='MyMemory does not support language code'):
        service.translate('hello', 'en', 'xx', save_history=False)


def test_google_and_mymemory_failure_is_reported(service, monkeypatch):
    class FailedTranslator:
        def __init__(self, **kwargs):
            raise RuntimeError('provider unavailable')

    monkeypatch.setattr(translator_module, 'GoogleTranslator', FailedTranslator)
    monkeypatch.setattr(translator_module, 'MyMemoryTranslator', FailedTranslator)
    with pytest.raises(TranslationError, match='Translation providers failed'):
        service.translate('hello', 'en', 'fr', save_history=False)


def test_invalid_empty_text_is_rejected(service):
    with pytest.raises(ValueError, match='Text is required'):
        service.translate('  ', save_history=False)


def test_history_is_limited_and_clearable(service):
    service.save_to_history('hello', 'bonjour', 'en', 'fr')
    with open(service.history_file, encoding='utf-8') as history_file:
        assert json.load(history_file)[0]['source_text'] == 'hello'
    service.clear_history()
    assert service.get_history() == []
