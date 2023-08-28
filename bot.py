import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from googletrans import Translator

load_dotenv()  # Load environment variables from .env file

translator = Translator()
TOKEN = os.getenv('DISCORD_TOKEN')  # Discord bot token
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
JUAN = False
STOP = False
VOLUMES = {
    'maren': 0.5,
    'ganma': 0.5,
    'storm': 0.2,
    'fit': 0.7,
}

country_flags = {
    '🇺🇸': 'en',
    '🇫🇷': 'fr',
    '🇪🇸': 'es',
    '🇯🇵': 'ja',
    '🇨🇳': 'zh-cn',
}

audios = list(file.split('.')[0] for file in os.listdir('./audios'))
AUDIO_LIST = '\n'.join(f"{idx + 1}. {file}" for idx, file in enumerate(audios))


def get_audio_source(audio_name):
    audio_source = None
    if os.path.exists(f'audios/{audio_name}.mp3'):  # audio needs to exist
        audio_source = discord.FFmpegPCMAudio(f'audios/{audio_name}.mp3')
    elif os.path.exists(f'audios/{audio_name}.m4a'):
        audio_source = discord.FFmpegPCMAudio(f'audios/{audio_name}.m4a')
    return audio_source


async def play_audio(voice_client, audio_name):
    global STOP
    try:
        idx = int(audio_name) - 1
        audio_name = audios[idx]
    except ValueError:
        pass
    audio_source = get_audio_source(audio_name)
    print(f'Playing {audio_name}')
    volume = 0.1
    if audio_name in VOLUMES:
        volume = VOLUMES[audio_name]
    audio_player = discord.PCMVolumeTransformer(audio_source, volume=volume)
    voice_client.play(audio_player)
    while voice_client.is_playing():
        await asyncio.sleep(1)
        if STOP:
            STOP = False
            voice_client.stop()
            return


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
    print(payload.emoji)
    if payload.emoji in country_flags and False:
        lang = country_flags[payload.emoji]
        translation = translator.translate(payload.message.content, dest=lang)
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

    if bot_voice_client is None:
        bot_voice_client = await after.channel.connect()
    elif bot_voice_client.channel != after.channel:
        await bot_voice_client.move_to(after.channel)

    prev_voice_channel = bot_voice_client.channel if bot_voice_client else None

    await asyncio.sleep(1.5)  # wait for them to connect to the channel
    await play_audio(bot_voice_client, 'nihao')

    if prev_voice_channel is not None:
        await bot_voice_client.move_to(prev_voice_channel)
    else:
        await bot_voice_client.disconnect()


@bot.event
async def on_message(msg):
    if msg.author.bot:  # only react to humans
        return
    if msg.content.startswith(bot.command_prefix):
        command = msg.content.split()[0][len(bot.command_prefix):]
        if command in bot.all_commands:
            if any(c in command for c in ['play', 'join', 'leave']):
                await msg.delete()
            await bot.process_commands(msg)
    elif JUAN:
        if msg.content == '干爆':
            response = '羡慕爆'
        elif '别卷' in msg.content:
            response = '对啊就是'
        elif '卷' in msg.content:
            response = 'ayayay别卷了'
        else:
            if msg.author.name == 'dcm9':
                response = 'zhm别卷了来打吧'
            else:
                response = ''
        if response:
            await msg.reply(response)


@bot.command()
async def play(ctx, audio_name=None, channel_name=None):
    # Requirement checks
    if ctx.author.bot or not audio_name or not os.path.exists(f'{audio_name}.mp3'):
        return

    # execute command after current audio finishes
    if ctx.voice_client and ctx.voice_client.is_playing():
        await asyncio.sleep(1)

    author_voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if author_voice_channel and not channel_name:
        voice_channel = author_voice_channel
    elif channel_name:
        voice_channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
        if voice_channel is None:
            return
    else:
        return

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
async def join(ctx, channel_name=None):
    if channel_name:
        voice_channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
        if voice_channel is None:  # channel_name is not a valid channel
            return
    else:
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if voice_channel is None:
            return  # no channel_name and author not in a channel
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
async def audios(ctx):
    await ctx.reply(AUDIO_LIST)


bot.remove_command("help")


@bot.command()
async def help(ctx):
    await ctx.reply("Commands: play <name/id> (channel), stop, join, leave, audios")


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
    global STOP
    STOP = True
    await ctx.message.delete()


bot.run(TOKEN)  # Start the Discord bot
