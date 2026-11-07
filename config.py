import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    # Vercel only permits runtime writes under /tmp. Allow an explicit override
    # for deployments with a persistent writable filesystem.
    HISTORY_FILE = os.environ.get(
        'HISTORY_FILE',
        '/tmp/history.json' if os.environ.get('VERCEL') else '/tmp/history.json',
    )
    # Retained for compatibility; SpeechService keeps generated audio in memory.
    AUDIO_FOLDER = os.environ.get('AUDIO_FOLDER', '/tmp/audio')
