import configparser
import os
import asyncio
import discord
from github_integration import volumes, set_volumes_changed
from audio_handler import play_audio, set_stop_playing
from constants import CURRENT_DIR, AUDIO_NAMES, AUDIO_LIST

config = configparser.ConfigParser()
CONFIG_PATH = os.path.join(CURRENT_DIR, '..', 'variables.ini')
config.read(CONFIG_PATH)
USER_IDS = {key: int(value) for key, value in config['USER_IDS'].items()}
CHANNEL_IDS = {key: int(value) for key, value in config['CHANNEL_IDS'].items()}
channel_name = config['SETTINGS']['channel_name']

command_lock = asyncio.Lock()


def set_commands(bot):
    @bot.command()
    async def play(ctx, audio_name=None, channel=None):
        async with command_lock:
            try:
                idx = int(audio_name) - 1
                audio_name = AUDIO_NAMES[idx]
            except ValueError:
                pass

            if ctx.author.bot or not audio_name or audio_name not in AUDIO_NAMES:
                return
            # execute command after current audio finishes
            if ctx.voice_client and ctx.voice_client.is_playing():
                await asyncio.sleep(1)

            author_voice_channel = ctx.author.voice.channel if ctx.author.voice else None
            if channel:
                voice_channel = discord.utils.get(ctx.guild.voice_channels, name=channel)
            else:
                voice_channel = ctx.voice_client.channel if ctx.voice_client else author_voice_channel

            if voice_channel is None:
                return

            # go back (or leave) to previous channel after playing audio
            bot_voice_client = ctx.voice_client
            prev_voice_channel = bot_voice_client.channel if bot_voice_client else None
            if bot_voice_client and bot_voice_client.channel != voice_channel:
                await bot_voice_client.move_to(voice_channel)
            elif not bot_voice_client:
                bot_voice_client = await voice_channel.connect()

            await play_audio(bot_voice_client, audio_name)

            if prev_voice_channel is not None:
                await bot_voice_client.move_to(prev_voice_channel)
            else:
                await bot_voice_client.disconnect()

    @bot.command()
    async def replay(ctx, audio_name=None, count=0):
        if count == 0:
            return

        async with command_lock:
            if ctx.author.bot or not audio_name or audio_name not in AUDIO_NAMES:
                return
            # execute command after current audio finishes
            if ctx.voice_client and ctx.voice_client.is_playing():
                await asyncio.sleep(1)

            author_voice_channel = ctx.author.voice.channel if ctx.author.voice else None
            voice_channel = ctx.voice_client.channel if ctx.voice_client else author_voice_channel

            if voice_channel is None:
                return

            # go back (or leave) to previous channel after playing audio
            bot_voice_client = ctx.voice_client
            prev_voice_channel = bot_voice_client.channel if bot_voice_client else None
            if bot_voice_client and bot_voice_client.channel != voice_channel:
                await bot_voice_client.move_to(voice_channel)
            elif not bot_voice_client:
                bot_voice_client = await voice_channel.connect()

            try:
                for _ in range(count):
                    keep_playing = await play_audio(bot_voice_client, audio_name)
                    if not keep_playing:
                        print('Replay stopped')
                        break
            finally:
                # Move back to previous channel or disconnect
                if prev_voice_channel is not None:
                    await bot_voice_client.move_to(prev_voice_channel)
                else:
                    await bot_voice_client.disconnect()

    @bot.command()
    async def join(ctx, channel=None):
        if channel:
            voice_channel = discord.utils.get(ctx.guild.voice_channels, name=channel)

            if voice_channel is None:  # not a valid channel
                return
        else:
            voice_channel = ctx.author.voice.channel if ctx.author.voice else None
            if voice_channel is None:
                return  # no channel and author not in a channel
        # check if the bot is already in a voice channel
        voice_client = ctx.voice_client
        if voice_client:
            # if the bot is already in the specified voice channel, do nothing
            if voice_client.channel == voice_channel:
                return
            # if the bot is in a different voice channel, move it to the specified channel
            else:
                await voice_client.move_to(voice_channel)
        # if the bot is not in a voice channel, join the specified channel
        else:
            await voice_channel.connect()

    @bot.command()
    async def vol(ctx, audio, volume: float = None):
        try:
            idx = int(audio) - 1
            audio = AUDIO_NAMES[idx]
        except ValueError:
            pass

        if volume is None:
            if audio not in AUDIO_NAMES:
                await ctx.reply('Audio not found')
            else:
                volume = volumes[audio]
                await ctx.reply(f'Current volume: {volume}')
        elif 0 <= volume <= 1:
            set_volumes_changed()
            volumes[audio] = volume
            print(f'"{audio}" now has volume {volume}')

    @bot.command()
    async def audios(ctx):
        await ctx.reply(AUDIO_LIST)

    @bot.command()
    async def help(ctx):
        await ctx.reply("Commands: play <name/id> (channel), stop_playing, join, leave, audios, vol <name> <volume>")

    @bot.command()
    async def leave(ctx):
        # check if the bot is in a voice channel
        if ctx.author.bot or not ctx.voice_client:
            print('Bot is not currently in a voice channel.')
            return

        # disconnect the bot from the current voice channel
        await ctx.voice_client.disconnect()

    @bot.command()
    async def stop(ctx):
        set_stop_playing()

    @bot.command()
    async def send(ctx, *, msg: str):
        """
        command format: !send msg (, people to mention separated by spaces)
        sends msg and mentions user if not None
        prints people that can be mentioned if msg is None
        """
        if not msg:
            await ctx.reply(set(USER_IDS.keys()))
            return

        channel = bot.get_channel(CHANNEL_IDS[channel_name])
        users = None
        if ',' in msg:
            msg, users = msg.rsplit(',', 1)

        if not users:
            await channel.send(f"{msg}")
            return

        users_to_mention = []
        for username in users.split():
            user_obj = await bot.fetch_user(USER_IDS[username])
            users_to_mention.append(user_obj.mention)
        await channel.send(f"{' '.join(users_to_mention)} {msg}")

    @bot.command()
    async def send_dm(ctx, *, msg: str):
        """
        !send_dm msg, user
        """
        if ',' not in msg:
            print('No user selected')
            return
        msg, user = msg.rsplit(',', 1)
        user = user.strip().lower()
        if user not in USER_IDS:
            print(f'User {user} not found')
            return

        try:
            user_obj = bot.get_user(USER_IDS[user])
            await user_obj.send(msg)
        except AttributeError as e:
            print('Likely error: the bot can only send to users that have shared a server with the bot')
            print(e)
        except Exception as e:
            print(e)

    @bot.command()
    async def setChannel(ctx, new_channel):
        global channel_name
        channel_name = new_channel
        print(f'Current channel: {channel_name} - {CHANNEL_IDS[channel_name]}')
