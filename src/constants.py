import os

current_dir = os.path.dirname(__file__)
audio_path = os.path.join(current_dir, '..', 'audios')
AUDIO_NAMES = sorted(list(file.split('.')[0] for file in os.listdir(audio_path)))
AUDIO_LIST = '\n'.join(f"{idx + 1}. {file}" for idx, file in enumerate(AUDIO_NAMES))