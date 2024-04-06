import discord
import asyncio
from drive_integration import volumes
import os
from constants import AUDIO_NAMES, AUDIO_PATH


stop_playing = False

async def play_audio(voice_client, audio_name):
    """
    :return: only for replay command: True if continue replaying,
             False if audio not found or stop was called during replay
    """
    global stop_playing
    try:
        idx = int(audio_name) - 1
        audio_name = AUDIO_NAMES[idx]
    except ValueError:
        pass
    audio_source = get_audio_source(audio_name)
    if not audio_source:
        print(f'Audio not found: {audio_name}')
        return False

    print(f'Playing {audio_name}')
    volume = volumes[audio_name]
    audio_player = discord.PCMVolumeTransformer(audio_source, volume=volume)
    voice_client.play(audio_player)
    while voice_client.is_playing():
        await asyncio.sleep(0.5)
        if stop_playing:
            stop_playing = False
            voice_client.stop()
            print("Audio stopped")
            return False
    return True


def get_audio_source(audio_name):
    try:
        idx = int(audio_name) - 1
        audio_name = AUDIO_NAMES[idx]
    except ValueError:
        pass

    if audio_name not in AUDIO_NAMES: # audio needs to exist
        return None

    mp3_path = os.path.join(AUDIO_PATH, f'{audio_name}.mp3')
    m4a_path = os.path.join(AUDIO_PATH, f'{audio_name}.m4a')
    if os.path.exists(mp3_path):
        return discord.FFmpegPCMAudio(mp3_path)
    elif os.path.exists(m4a_path):
        return discord.FFmpegPCMAudio(m4a_path)
    else:
        print(f'Issue with {audio_name}: not mp3 or m4a')
        return None


def get_stop_playing():
    return stop_playing


def set_stop_playing():
    global stop_playing
    stop_playing = True
