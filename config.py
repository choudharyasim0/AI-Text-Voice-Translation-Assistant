import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'data', 'history.json')
    AUDIO_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'audio')
