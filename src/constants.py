import os

CURRENT_DIR = os.path.dirname(__file__)
AUDIO_PATH = os.path.join(CURRENT_DIR, '..', 'audios')
AUDIO_NAMES = sorted(list(file.split('.')[0] for file in os.listdir(AUDIO_PATH)))
AUDIO_LIST = '\n'.join(f"{idx + 1}. {file}" for idx, file in enumerate(AUDIO_NAMES))
