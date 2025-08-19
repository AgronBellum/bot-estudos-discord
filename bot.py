import os
import discord
from discord.ext import commands

# Token do bot vem da variável de ambiente DISCORD_TOKEN
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # necessário para ler mensagens

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! Estou online e funcionando!")

bot.run(TOKEN)
