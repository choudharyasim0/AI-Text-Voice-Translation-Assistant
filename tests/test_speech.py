from io import BytesIO

from services import speech as speech_module
from services.speech import SpeechService


def test_generate_audio_returns_rewound_bytesio(monkeypatch):
    class FakeTTS:
        def __init__(self, text, lang, slow):
            assert text == 'hello'
            assert lang == 'en'
            assert slow is False

        def write_to_fp(self, output):
            output.write(b'fake-mp3-data')

    monkeypatch.setattr(speech_module, 'gTTS', FakeTTS)
    output = SpeechService().generate_audio('hello', 'en')

    assert isinstance(output, BytesIO)
    assert output.tell() == 0
    assert output.read() == b'fake-mp3-data'


def test_generate_audio_uses_english_fallback(monkeypatch):
    languages = []

    class FakeTTS:
        def __init__(self, text, lang, slow):
            languages.append(lang)
            if lang == 'fr':
                raise ValueError('unsupported language')

        def write_to_fp(self, output):
            output.write(b'fallback-mp3')

    monkeypatch.setattr(speech_module, 'gTTS', FakeTTS)
    output = SpeechService().generate_audio('bonjour', 'fr')

    assert languages == ['fr', 'en']
    assert output.read() == b'fallback-mp3'
