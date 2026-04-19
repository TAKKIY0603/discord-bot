import os
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

JST = timezone(timedelta(hours=9))


def get_welcome_message(member: discord.Member) -> str:
    hour = datetime.now(JST).hour

    if 5 <= hour < 11:
        return f"おはよう！ {member.mention} さん、ようこそ！"
    if 11 <= hour < 18:
        return f"こんにちは！ {member.mention} さん、参加ありがとう！"
    if 18 <= hour < 23:
        return f"こんばんは！ {member.mention} さん、ゆっくりしていってね！"
    return f"夜遅くにようこそ！ {member.mention} さん、来てくれてありがとう！"


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    channel = None

    if WELCOME_CHANNEL_ID and WELCOME_CHANNEL_ID.isdigit():
        channel = bot.get_channel(int(WELCOME_CHANNEL_ID))

    if channel is None:
        channel = member.guild.system_channel

    if channel is None:
        return

    await channel.send(get_welcome_message(member))


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


bot.run(TOKEN)
