import discord
import asyncio
from drive_integration import volumes
import os

AUDIO_NAMES = sorted(list(file.split('.')[0] for file in os.listdir('./audios')))
AUDIO_LIST = '\n'.join(f"{idx + 1}. {file}" for idx, file in enumerate(AUDIO_NAMES))

stop_playing = False
async def play_audio(voice_client, audio_name):
    global stop_playing
    try:
        idx = int(audio_name) - 1
        audio_name = AUDIO_NAMES[idx]
    except ValueError:
        pass
    audio_source = get_audio_source(audio_name)
    if not audio_source:
        print(f'Audio not found: {audio_name}')
        return

    print(f'Playing {audio_name}')
    volume = volumes[audio_name]
    audio_player = discord.PCMVolumeTransformer(audio_source, volume=volume)
    voice_client.play(audio_player)
    while voice_client.is_playing():
        await asyncio.sleep(1)
        if stop_playing:
            stop_playing = False
            voice_client.stop()
            print("Audio stopped")
            return


def get_audio_source(audio_name):
    try:
        idx = int(audio_name) - 1
        audio_name = AUDIO_NAMES[idx]
    except ValueError:
        pass
    audio_source = None
    if os.path.exists(f'audios/{audio_name}.mp3'):  # audio needs to exist
        audio_source = discord.FFmpegPCMAudio(f'audios/{audio_name}.mp3')
    elif os.path.exists(f'audios/{audio_name}.m4a'):
        audio_source = discord.FFmpegPCMAudio(f'audios/{audio_name}.m4a')
    return audio_source


def set_stop_playing():
    global stop_playing
    stop_playing = True
