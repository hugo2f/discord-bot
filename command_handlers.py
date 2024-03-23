import asyncio
import os
import discord
from collections import defaultdict
from drive_integration import msg_counts, volumes
from utils import play_audio, get_audio_source, AUDIO_NAMES, AUDIO_LIST, set_stop_playing

command_lock = asyncio.Lock()

USER_IDS = {
    'cato': 332017992068104204,
    'zhm': 687778165573287972,
    'sdl': 597662493074259972,
    'glnt': 676967387370618880,
    'gaj': 675332441388351489,
    'ltz': 880604419903881216,
    'wms': 689384461313507342,
    'xh': 674838013045506067,
    'me': 827541553476010005,
    'carl': 754547462147932210,
    'ap': 891395220124626944,
}
CHANNEL_IDS = {
    # Gimme Zhu
    'general': 885632562691719233,
    'juaneral': 983893953701101609,
}
channel_name = 'general'  # default channel


def set_commands(bot):
    @bot.command()
    async def play(ctx, audio_name=None, channel=None):
        async with command_lock:
            if ctx.author.bot or not audio_name or not get_audio_source(audio_name):
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
            volume = volumes[audio]
            await ctx.reply(f'Current volume: {volume}')
        elif 0 <= volume <= 1:
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
        user = user.strip()
        if user not in USER_IDS:
            print(f'User {user} not found')
            return

        user_obj = bot.get_user(USER_IDS[user.strip()])
        await user_obj.send(msg)

    @bot.command()
    async def setChannel(ctx, new_channel):
        global channel_name
        channel_name = new_channel
        print(f'Current channel: {channel_name} - {CHANNEL_IDS[channel_name]}')

    @bot.command()
    async def message_count(ctx, *args):
        if len(args) == 0:
            for user in msg_counts:
                await ctx.send(f"{user} has sent {msg_counts[user]} message(s).")
        else:
            for arg in args:
                if arg not in msg_counts:
                    await ctx.send(f"{arg} has not sent any messages.")
                else:
                    await ctx.send(f"{arg} has sent {msg_counts[arg]} message(s).")

    @bot.command()
    async def clear_msg(ctx):
        global msg_counts
        msg_counts = defaultdict(int)
        print('Message counts cleared')
