import asyncio
import json
import os
import random
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")
VOICE_LOG_CHANNEL_ID = os.getenv("VOICE_LOG_CHANNEL_ID")
MEDIA_RELAY_CHANNEL_ID = os.getenv("MEDIA_RELAY_CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guild_messages = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

JST = timezone(timedelta(hours=9))
PREF_CITY_MAP = {
    "北海道": "Sapporo",
    "青森県": "Aomori",
    "岩手県": "Morioka",
    "宮城県": "Sendai",
    "秋田県": "Akita",
    "山形県": "Yamagata",
    "福島県": "Fukushima",
    "茨城県": "Mito",
    "栃木県": "Utsunomiya",
    "群馬県": "Maebashi",
    "埼玉県": "Saitama",
    "千葉県": "Chiba",
    "東京都": "Tokyo",
    "神奈川県": "Yokohama",
    "新潟県": "Niigata",
    "富山県": "Toyama",
    "石川県": "Kanazawa",
    "福井県": "Fukui",
    "山梨県": "Kofu",
    "長野県": "Nagano",
    "岐阜県": "Gifu",
    "静岡県": "Shizuoka",
    "愛知県": "Nagoya",
    "三重県": "Tsu",
    "滋賀県": "Otsu",
    "京都府": "Kyoto",
    "大阪府": "Osaka",
    "兵庫県": "Kobe",
    "奈良県": "Nara",
    "和歌山県": "Wakayama",
    "鳥取県": "Tottori",
    "島根県": "Matsue",
    "岡山県": "Okayama",
    "広島県": "Hiroshima",
    "山口県": "Yamaguchi",
    "徳島県": "Tokushima",
    "香川県": "Takamatsu",
    "愛媛県": "Matsuyama",
    "高知県": "Kochi",
    "福岡県": "Fukuoka",
    "佐賀県": "Saga",
    "長崎県": "Nagasaki",
    "熊本県": "Kumamoto",
    "大分県": "Oita",
    "宮崎県": "Miyazaki",
    "鹿児島県": "Kagoshima",
    "沖縄県": "Naha",
}
URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v")


def get_welcome_message(member: discord.Member) -> str:
    hour = datetime.now(JST).hour

    if 5 <= hour < 11:
        return f"おはよう！ {member.mention} さん、ようこそ！"
    if 11 <= hour < 18:
        return f"こんにちは！ {member.mention} さん、参加ありがとう！"
    if 18 <= hour < 23:
        return f"こんばんは！ {member.mention} さん、ゆっくりしていってね！"
    return f"夜遅くにようこそ！ {member.mention} さん、来てくれてありがとう！"


def extract_prefecture(text: str) -> str | None:
    for pref in PREF_CITY_MAP:
        if pref in text:
            return pref
    return None


def fetch_today_weather(city: str) -> tuple[str, str, str]:
    q = urllib.parse.quote(city)
    url = f"https://wttr.in/{q}?format=j1"
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    today = data["weather"][0]
    weather_text = today["hourly"][4]["weatherDesc"][0]["value"]
    max_temp = today["maxtempC"]
    min_temp = today["mintempC"]
    return weather_text, max_temp, min_temp


def normalize_url(url: str) -> str:
    return url.split("?")[0].split("#")[0].lower()


def classify_url(url: str) -> str | None:
    normalized = normalize_url(url)
    if normalized.endswith(IMAGE_EXTENSIONS):
        return "image"
    if normalized.endswith(VIDEO_EXTENSIONS):
        return "video"
    return None


async def relay_media_if_needed(message: discord.Message) -> bool:
    if not MEDIA_RELAY_CHANNEL_ID or not MEDIA_RELAY_CHANNEL_ID.isdigit():
        return False

    relay_channel = bot.get_channel(int(MEDIA_RELAY_CHANNEL_ID))
    if relay_channel is None or relay_channel.id == message.channel.id:
        return False

    relayed = False

    for url in URL_PATTERN.findall(message.content):
        kind = classify_url(url)
        if kind == "image":
            await relay_channel.send(f"[画像リンク転載] 送信者: {message.author.mention}\n{url}")
            relayed = True
        elif kind == "video":
            await relay_channel.send(f"[動画リンク転載] 送信者: {message.author.mention}\n{url}")
            relayed = True

    for attachment in message.attachments:
        name = attachment.filename.lower()
        if name.endswith(IMAGE_EXTENSIONS):
            await relay_channel.send(
                f"[画像添付転載] 送信者: {message.author.mention}",
                file=await attachment.to_file(),
            )
            relayed = True
            continue

        if name.endswith(VIDEO_EXTENSIONS):
            duration = getattr(attachment, "duration", None)
            if duration is None or duration <= 180:
                await relay_channel.send(
                    f"[動画添付転載] 送信者: {message.author.mention}",
                    file=await attachment.to_file(),
                )
                relayed = True
            else:
                await relay_channel.send(
                    f"[動画スキップ] 3分超のため転載しませんでした: {attachment.url}"
                )
                relayed = True

    return relayed


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
    if bot.user and message.author.id == bot.user.id:
        return

    content = message.content.strip()
    lowered = content.lower()
    print(f"[on_message] author={message.author} dm={message.guild is None} content={content}")

    try:
        await relay_media_if_needed(message)
    except Exception as exc:
        print(f"[relay_media_if_needed] error: {exc}")

    if "こんにちは" in content:
        await message.channel.send("こんにちは！")
    elif "おはよう" in content:
        await message.channel.send("おはよう！")
    elif "おやすみ" in content:
        await message.channel.send("おやすみ！")
    elif "死ね" in content:
        await message.channel.send("その言葉はやめよう。落ち着いて話そう。")
    elif "ばか" in content or "バカ" in content or "馬鹿" in content:
        await message.channel.send("悪口はなしでいこう。")
    elif "やりますねぇ" in content:
        await message.channel.send("やりますやります！")
    elif "hey" in lowered and "今日" in content and "天気" in content:
        pref = extract_prefecture(content)
        if not pref:
            await message.channel.send("都道府県名を入れて聞いてね。（例: Hey 今日の大阪府の天気は？）")
        else:
            city = PREF_CITY_MAP[pref]
            try:
                weather_text, max_temp, min_temp = await asyncio.to_thread(fetch_today_weather, city)
                await message.channel.send(
                    f"{pref}（{city}）の今日の天気: {weather_text}\n"
                    f"最高気温: {max_temp}℃ / 最低気温: {min_temp}℃"
                )
            except Exception:
                await message.channel.send("天気情報の取得に失敗しました。少し待ってもう一度試してね。")
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
