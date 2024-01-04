import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from googletrans import Translator
import json
import atexit

load_dotenv()  # Load environment variables from .env file
TOKEN = os.getenv('DISCORD_TOKEN')  # Discord bot token
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
translator = Translator()
command_lock = asyncio.Lock()
bot.remove_command("help")  # to define custom help command

# Read the dictionary from the JSON file
with open('volumes.json', 'r') as fin:
    VOLUMES = json.load(fin)
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

AUDIO_NAMES = sorted(list(file.split('.')[0] for file in os.listdir('./audios')))
AUDIO_LIST = '\n'.join(f"{idx + 1}. {file}" for idx, file in enumerate(AUDIO_NAMES))

msg_count = {}

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

    if bot_voice_client and bot_voice_client.is_playing(): # wait until prev audio finishes
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
    
    # Record message that each user sent
    if msg.author.name not in msg_count:
        msg_count[msg.author.name] = 1
    else:
        msg_count[msg.author.name] += 1

    if msg.content.startswith(bot.command_prefix):
        command = msg.content.split()[0][len(bot.command_prefix):]
        if command in bot.all_commands:
            if any(c in command for c in ['play', 'join', 'leave', 'stop_playing']) \
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

    # Send the deleted message to the specified channel
    await msg.channel.send(deleted_message)


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


async def play_audio(voice_client, audio_name):
    global stop_playing
    try:
        idx = int(audio_name) - 1
        audio_name = AUDIO_NAMES[idx]
    except ValueError:
        pass
    audio_source = get_audio_source(audio_name)
    # if not audio_source:
    #     print(f'Audio not found: {audio_name}')
    #     return

    print(f'Playing {audio_name}')
    volume = VOLUMES.get(audio_name, DEFAULT_VOLUME)
    audio_player = discord.PCMVolumeTransformer(audio_source, volume=volume)
    voice_client.play(audio_player)
    while voice_client.is_playing():
        await asyncio.sleep(1)
        if stop_playing:
            stop_playing = False
            voice_client.stop_playing()
            return


def get_audio_source(audio_name):
    audio_source = None
    if os.path.exists(f'audios/{audio_name}.mp3'):  # audio needs to exist
        audio_source = discord.FFmpegPCMAudio(f'audios/{audio_name}.mp3')
    elif os.path.exists(f'audios/{audio_name}.m4a'):
        audio_source = discord.FFmpegPCMAudio(f'audios/{audio_name}.m4a')
    return audio_source


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
        volume = VOLUMES.get(audio, DEFAULT_VOLUME)
        await ctx.reply(f'Current volume: {volume}')
    elif 0 <= volume <= 1:
        VOLUMES[audio] = volume
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
    global stop_playing
    stop_playing = True


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
}
CHANNEL_IDS = {
    # Gimme Zhu
    'general': 885632562691719233,
    'juaneral': 983893953701101609,
}
channel_name = 'general'  # default channel


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
        for user in msg_count:
            await ctx.send(f"{user} has sent {msg_count[user]} message(s).")
    else:
        for arg in args:
            if arg not in msg_count:
                await ctx.send(f"{arg} has not sent any messages.")
            else:
                await ctx.send(f"{arg} has sent {msg_count[arg]} message(s).")


def update_volumes():
    # remove unnecessary entries in VOLUMES
    to_remove = []
    for audio, volume in VOLUMES.items():
        if not (os.path.exists(f'audios/{audio}.mp3')
                or os.path.exists(f'audios/{audio}.m4a')) \
                or volume == DEFAULT_VOLUME:
            to_remove.append(audio)
    for audio in to_remove:
        del VOLUMES[audio]

    with open('volumes.json', 'w') as fout:
        json.dump(VOLUMES, fout, indent=4)
    print('volume.json updated')


atexit.register(update_volumes)
bot.run(TOKEN)  # Start the Discord bot
