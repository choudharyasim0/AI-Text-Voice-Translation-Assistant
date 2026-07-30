import pytest
from app import app, translator


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def test_home_page_renders(client):
    response = client.get('/')
    assert response.status_code == 200


def test_languages_endpoint_returns_data(client):
    response = client.get('/languages')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'auto' in data


def test_translate_endpoint_requires_text(client):
    response = client.post('/translate', json={'text': ''})
    assert response.status_code == 400


def test_home_page_contains_voice_controls(client):
    response = client.get('/')
    html = response.get_data(as_text=True)
    assert 'id="voiceSourceLang"' in html
    assert 'id="voiceInputText"' in html
    assert 'id="clearHistoryBtn"' in html


def test_clear_history_clears_backend_storage(client):
    translator.save_history('hello', 'bonjour', 'auto', 'fr')
    response = client.delete('/clear-history')
    assert response.status_code == 200
    assert translator.get_history() == []
