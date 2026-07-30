import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "voice_translation_secret_key")

    HISTORY_FILE = "history/translations.json"

    AUDIO_FOLDER = "static/audio"