import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from googletrans import Translator
import json
import atexit
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from collections import defaultdict
import sys
from drive_integration import msg_counts
from utils import play_audio

"""
global variables
"""
DEFAULT_VOLUME = 0.4
TRANSLATE = True
JUAN = False
stop_playing = False

country_flags = {
    '🇺🇸': 'en',
    '🇫🇷': 'fr',
    '🇪🇸': 'es',
    '🇯🇵': 'ja',
    '🇨🇳': 'zh-cn',
}

translator = Translator()

def set_events(bot):
    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')

    @bot.event
    async def on_raw_reaction_add(payload):
        user = await bot.fetch_user(payload.user_id)
        if user.bot:
            return
        channel = await bot.fetch_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        if payload.emoji.name in country_flags and TRANSLATE:
            lang = country_flags[payload.emoji.name]
            print(f'Translating {payload.emoji.name} to {lang}')
            translation = translator.translate(msg.content, dest=lang)
            await msg.reply(translation.text)

    @bot.event
    async def on_voice_state_update(member, before, after):
        """
        When someone joins a channel, join them and play nihao.mp3
        """
        if member.bot or after.channel is None or before.channel == after.channel:
            return

        bot_voice_client = None
        for voice_client in bot.voice_clients:
            if voice_client.guild == member.guild:
                bot_voice_client = voice_client
                break

        if bot_voice_client and bot_voice_client.is_playing():  # wait until prev audio finishes
            await asyncio.sleep(1)

        prev_voice_channel = bot_voice_client.channel if bot_voice_client else None
        if bot_voice_client is None:
            bot_voice_client = await after.channel.connect()
        elif bot_voice_client.channel != after.channel:
            await bot_voice_client.move_to(after.channel)

        await asyncio.sleep(1.5)  # wait for them to connect to the channel
        await play_audio(bot_voice_client, 'nihao')

        if prev_voice_channel is not None:
            await bot_voice_client.move_to(prev_voice_channel)
        else:
            await bot_voice_client.disconnect(force=True)

    @bot.event
    async def on_message(msg):
        if msg.author.bot:  # only react to humans
            return

        # record message counts in GMZ
        if msg.guild and msg.guild.id == 885632562691719230:
            msg_counts[msg.author.name] += 1

        if msg.content.startswith(bot.command_prefix):
            command = msg.content.split()[0][len(bot.command_prefix):]
            if command in bot.all_commands:
                if any(c in command for c in ['play', 'join', 'leave', 'stop']) \
                        or command == 'vol' and len(msg.content.split()) > 2:  # only when a volume is given
                    await msg.delete()
                await bot.process_commands(msg)
        elif JUAN:
            response = None
            if '别卷' in msg.content:
                response = '对啊就是'
            elif '卷' in msg.content:
                response = 'ayayay别卷了'
            else:
                if msg.author.name == 'dcm9':
                    response = 'zhm别卷了来打吧'
            if response:
                await msg.reply(response)

    @bot.event
    async def on_message_delete(msg):
        # process human messages only
        if msg.author.bot:
            return

        # don't echo commands deleted by the bot
        if msg.content.startswith(bot.command_prefix):
            return
        deleted_message = f"{msg.author.display_name} just recalled:\n{msg.content}"
        await msg.channel.send(deleted_message)
