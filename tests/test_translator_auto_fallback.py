import pytest

from services import translator as translator_module
from services.translator import TranslationError, TranslatorService


@pytest.fixture
def translator(tmp_path):
    return TranslatorService(str(tmp_path / 'history.json'))


def test_auto_source_is_detected_before_mymemory_fallback(translator, monkeypatch):
    calls = []

    class GoogleFails:
        def __init__(self, **kwargs):
            raise RuntimeError('Google rate limited')

    class FakeMyMemory:
        def __init__(self, source, target):
            calls.append((source, target))

        def translate(self, text):
            return 'Hello world'

    monkeypatch.setattr(translator_module, 'GoogleTranslator', GoogleFails)
    monkeypatch.setattr(translator_module, 'MyMemoryTranslator', FakeMyMemory)
    monkeypatch.setattr(translator_module, 'detect', lambda text: 'fr')

    assert translator.translate('Bonjour le monde', 'auto', 'en', save_history=False) == 'Hello world'
    assert calls == [('fr-FR', 'en-GB')]


def test_mymemory_code_rejects_auto():
    with pytest.raises(ValueError, match='not auto'):
        TranslatorService._mymemory_code('auto')


def test_explicit_source_uses_mymemory_fallback(translator, monkeypatch):
    calls = []

    class GoogleFails:
        def __init__(self, **kwargs):
            raise RuntimeError('Google unavailable')

    class FakeMyMemory:
        def __init__(self, source, target):
            calls.append((source, target))

        def translate(self, text):
            return 'bonjour'

    monkeypatch.setattr(translator_module, 'GoogleTranslator', GoogleFails)
    monkeypatch.setattr(translator_module, 'MyMemoryTranslator', FakeMyMemory)

    assert translator.translate('hello', 'en', 'fr', save_history=False) == 'bonjour'
    assert calls == [('en-GB', 'fr-FR')]


def test_auto_detection_failure_returns_translation_error(translator, monkeypatch):
    class GoogleFails:
        def __init__(self, **kwargs):
            raise RuntimeError('Google unavailable')

    monkeypatch.setattr(translator_module, 'GoogleTranslator', GoogleFails)
    monkeypatch.setattr(
        translator_module,
        'detect',
        lambda text: (_ for _ in ()).throw(translator_module.LangDetectException('no lang', '')),
    )

    with pytest.raises(TranslationError, match='Could not detect the source language'):
        translator.translate('abc', 'auto', 'en', save_history=False)
