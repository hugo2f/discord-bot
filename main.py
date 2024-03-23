import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import event_handlers
import command_handlers

# initialize bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.remove_command("help")  # to define custom help command

# set events and commands
event_handlers.set_events(bot)
command_handlers.set_commands(bot)

# run the bot
bot.run(TOKEN)
