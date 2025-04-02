# main.py

import asyncio
import yt_dlp as youtube_dl
import os
import json
import shutil
from dotenv import load_dotenv
from pathlib import Path
import traceback
import subprocess

os.environ['OPUS_LIBRARY'] = '/nix/store/cb7xz81832zj9pciyi585f3rp60wjcyx-libopus-1.5.2/lib/libopus.so.0'

from discord import opus
if not opus.is_loaded():
    opus.load_opus(os.environ['OPUS_LIBRARY'])

import discord
from discord.ext import commands

print("[DEBUG] Searching for opus:")
print(subprocess.getoutput("find / -name 'libopus.so*' 2>/dev/null"))

print(f"[DEBUG] Opus loaded: {opus.is_loaded()}")

load_dotenv()

# 写入 cookie 文件（用于 yt-dlp）
cookie_content = os.getenv("YTDLP_COOKIE")
if cookie_content:
    Path("cookies.txt").write_text(cookie_content.replace("\\n", "\n").strip(), encoding="utf-8")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

voice_clients = {}
volume_levels = {}
playlist_queues = {}
now_playing = {}
current_sources = {}
play_history = {}
loop_mode = {}

LOOP_NONE = "none"
LOOP_QUEUE = "queue"
LOOP_SINGLE = "single"


def get_ffmpeg_options():
    return {
        'before_options': '',
        'options': '-vn'
    }

def get_ffmpeg_path():
    return shutil.which("ffmpeg") or "ffmpeg"


def get_ydl_opts():
    return {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'default_search': 'ytsearch',
        
    }

print(f"[DEBUG] FFmpeg path used: {get_ffmpeg_path()}")

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    queue = playlist_queues.get(guild_id, [])

    if not queue or not vc or not vc.is_connected():
        now_playing[guild_id] = None
        return False

    item = queue.pop(0)
    path, title = item['path'], item['title']
    volume = volume_levels.get(guild_id, 0.5)

    try:
        if not os.path.isfile(path):
            print(f"[ERROR] File not found: {path}")
            await ctx.send("❌ Audio file missing. Something went wrong with download.")
            return
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(path, executable=get_ffmpeg_path(), **get_ffmpeg_options()),
            volume=volume
        )
        current_sources[guild_id] = source
        now_playing[guild_id] = title

        def after_playing(err):
            try:
                if loop_mode.get(guild_id) == LOOP_SINGLE:
                    queue.insert(0, item)
                elif loop_mode.get(guild_id) == LOOP_QUEUE:
                    queue.append(item)

                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            except Exception as e:
                now_playing[guild_id] = None

        try:
            print(f"[DEBUG] Trying to play local file: {path}, exists: {os.path.exists(path)}")
            vc.play(source, after=after_playing)
        except Exception as e:
            print(f"[ERROR] vc.play(): {e}")
            traceback.print_exc()
            await ctx.send("❌ Failed to play the song.")

        play_history.setdefault(guild_id, []).append({'title': title})
        if len(play_history[guild_id]) > 5:
            play_history[guild_id] = play_history[guild_id][-5:]
    except Exception as e:
        print(f"[ERROR] vc.play(): {e}")
        await ctx.send("❌ Failed to play the song.")

@bot.command(name="play")
async def play(ctx, *, search: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❗ You must be in a voice channel.")
        return

    try:
        vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        target_channel = ctx.author.voice.channel
        if vc is None:
            vc = await target_channel.connect()
            voice_clients[ctx.guild.id] = vc
        elif vc.channel != target_channel:
            await vc.move_to(target_channel)

        with youtube_dl.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(f"ytsearch1:{search}", download=True)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            else:
                await ctx.send("❌ No results found.")
                return
            file_path = f"/tmp/{info['id']}.m4a"
            title = info.get('title', 'Unknown Title')

        queue = playlist_queues.setdefault(ctx.guild.id, [])
        queue.insert(0, {'path': file_path, 'title': title})
        await ctx.send(f"🎶 Now playing: {title}")

        if not vc.is_playing() and not vc.is_paused():
            await play_next(ctx)
        else:
            vc.stop()

    except Exception as e:
        await ctx.send(f"❌ Failed to retrieve or play the audio: {e}")
        print(f"[ERROR] play(): {e}")


@bot.command(name="stop")
async def stop(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Music paused.")
    else:
        await ctx.send("Nothing is playing.")

@bot.command(name="resume")
async def resume(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Resumed the music.")
    else:
        await ctx.send("Nothing to resume.")

@bot.command(name="volume")
async def volume(ctx, level: int):
    if not (0 <= level <= 100):
        await ctx.send("Volume must be between 0 and 100.")
        return
    volume_levels[ctx.guild.id] = level / 100
    src = current_sources.get(ctx.guild.id)
    if src:
        src.volume = level / 100
    await ctx.send(f"🔊 Volume set to {level}%")

@bot.command(name="clear")
async def clear(ctx):
    playlist_queues[ctx.guild.id] = []
    await ctx.send("🧹 Queue cleared.")

@bot.command(name="next")
async def next(ctx):
    queue = playlist_queues.get(ctx.guild.id, [])
    if queue:
        vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if vc:
            vc.stop()
        await ctx.send(f"⏭️ Playing next: {queue[0]['title']}")
    else:
        await ctx.send("No more songs in the queue.")

@bot.command(name="last")
async def last(ctx):
    history = play_history.get(ctx.guild.id, [])
    if len(history) < 2:
        await ctx.send("No previous song.")
        return
    prev = history[-2]
    playlist_queues.setdefault(ctx.guild.id, []).insert(0, prev)
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc:
        vc.stop()
    await ctx.send(f"🔁 Replaying: {prev['title']}")

@bot.command(name="loop")
async def loop(ctx, mode: str):
    if mode not in [LOOP_NONE, LOOP_QUEUE, LOOP_SINGLE]:
        await ctx.send("❌ Invalid loop mode. Use: none, queue, or single")
        return
    loop_mode[ctx.guild.id] = mode
    await ctx.send(f"🔁 Loop mode set to: {mode}")

@bot.command(name="gen")
async def gen(ctx, *, keyword: str):
    await ctx.send(f"🔎 Generating songs for: {keyword}")
    ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'cookiefile': 'cookies.txt'
        }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        results = ydl.extract_info(f"ytsearch5:{keyword}", download=False)['entries']
    playlist = [{'path': r['path'], 'title': r['title']} for r in results]
    playlist_queues.setdefault(ctx.guild.id, []).extend(playlist)
    if not discord.utils.get(bot.voice_clients, guild=ctx.guild):
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
    if not discord.utils.get(bot.voice_clients, guild=ctx.guild).is_playing():
        play_next(ctx)

@bot.command(name="add")
async def add(ctx, *, search: str):
    ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'cookiefile': 'cookies.txt'
        }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        
        info = ydl.extract_info(f"ytsearch1:{search}", download=False)['entries'][0]
        path, title = info['path'], info['title']
    playlist_queues.setdefault(ctx.guild.id, []).append({'path': path, 'title': title})
    await ctx.send(f"➕ Added to queue: {title}")

@bot.command(name="show")
async def show(ctx):
    queue = playlist_queues.get(ctx.guild.id, [])
    now = now_playing.get(ctx.guild.id)
    history = play_history.get(ctx.guild.id, [])
    msg = f"🎶 Now playing: {now}\n\n" if now else "No song playing.\n"
    if history:
        msg += "🕓 Recent:\n" + "\n".join(f"• {h['title']}" for h in history[-5:]) + "\n\n"
    if queue:
        msg += "📜 Queue:\n" + "\n".join(f"{i+1}. {q['title']}" for i, q in enumerate(queue))
    else:
        msg += "Queue is empty."
    await ctx.send(msg[:2000])

@bot.command(name="leave")
async def leave(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc:
        await vc.disconnect()
        voice_clients.pop(ctx.guild.id, None)
        await ctx.send("👋 Disconnected from voice channel.")
    else:
        await ctx.send("I'm not in a voice channel.")

@bot.command(name="commands")
async def commands_list(ctx):
    await ctx.send("""
**🎵 Music Bot Commands**
!play <keywords> — Play immediately (force join + interrupt)
!add <keywords> — Add song to queue
!stop — Pause current song
!resume — Resume paused song
!volume <0-100> — Set volume
!clear — Clear queue
!next — Play next song
!last — Replay previous
!loop <none|queue|single> — Set loop mode
!gen <genre> — Auto add 5 songs
!show — Show queue and recent history
!leave — Disconnect from voice
!commands — Show this help menu
    """)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(os.getenv("BOT_TOKEN"))
