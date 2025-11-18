import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command(name='hello')
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author.mention}!')

if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set!")
        print("Please set your Discord bot token to run this bot.")
    else:
        bot.run(token)
