import os
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")
VOICE_LOG_CHANNEL_ID = os.getenv("VOICE_LOG_CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guild_messages = True
intents.dm_messages = True

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


@bot.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    if not VOICE_LOG_CHANNEL_ID or not VOICE_LOG_CHANNEL_ID.isdigit():
        return

    log_channel = bot.get_channel(int(VOICE_LOG_CHANNEL_ID))
    if log_channel is None:
        return

    before_channel = before.channel
    after_channel = after.channel

    if before_channel is None and after_channel is not None:
        await log_channel.send(
            f"{member.mention} が通話に参加しました（{after_channel.name}）"
        )
    elif before_channel is not None and after_channel is None:
        await log_channel.send(
            f"{member.mention} が通話から退出しました（{before_channel.name}）"
        )
    elif (
        before_channel is not None
        and after_channel is not None
        and before_channel.id != after_channel.id
    ):
        await log_channel.send(
            f"{member.mention} が通話を移動しました（{before_channel.name} → {after_channel.name}）"
        )


@bot.event
async def on_message(message: discord.Message):
    # Ignore only this bot's own messages to avoid self-reply loops.
    if bot.user and message.author.id == bot.user.id:
        return

    content = message.content.strip()
    lowered = content.lower()
    print(f"[on_message] author={message.author} dm={message.guild is None} content={content}")

    if "こんにちは" in content:
        await message.channel.send("こんにちは！")
    elif "おはよう" in content:
        await message.channel.send("おはよう！")
    elif "おやすみ" in content:
        await message.channel.send("おやすみ！")
    elif "ping" in lowered:
        await message.channel.send("Pong!")

    await bot.process_commands(message)


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


@bot.command()
async def hello(ctx):
    await ctx.send(f"話かけてくんな！{ctx.author.mention} さん！")


@bot.command()
async def dice(ctx):
    value = random.randint(1, 6)
    await ctx.send(f"{ctx.author.mention} のサイコロ結果: {value}")


@bot.command()
async def omikuji(ctx):
    results = ["大吉", "中吉", "小吉", "吉", "末吉", "凶"]
    await ctx.send(f"{ctx.author.mention} のおみくじ結果: {random.choice(results)}")


@bot.command(name="helpme")
async def helpme(ctx):
    await ctx.send("使えるコマンド: !ping / !hello / !dice / !omikuji / !helpme")


bot.run(TOKEN)
