# local.py v0.3.5 — Local Discord Music Bot (No cookie required)

import os
import shutil
import asyncio
import traceback
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
import yt_dlp as youtube_dl

load_dotenv()

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

def get_ffmpeg_path():
    return shutil.which("ffmpeg") or "ffmpeg"

def get_ydl_opts(download=True):
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0'
    }
    if download:
        opts.update({
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }]
        })
    return opts

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    queue = playlist_queues.get(guild_id, [])

    if not queue or not vc or not vc.is_connected():
        now_playing[guild_id] = None
        return

    item = queue.pop(0)
    path, title = item['path'], item['title']
    volume = volume_levels.get(guild_id, 0.5)

    try:
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(path, executable=get_ffmpeg_path()),
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
                print(f"[ERROR] after_playing(): {e}")

        vc.play(source, after=after_playing)

        play_history.setdefault(guild_id, []).append({'path': path, 'title': title})
        if len(play_history[guild_id]) > 5:
            play_history[guild_id] = play_history[guild_id][-5:]

    except Exception as e:
        print(f"[ERROR] vc.play(): {e}")
        await ctx.send("❌ Failed to play audio.")

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

        with youtube_dl.YoutubeDL(get_ydl_opts(True)) as ydl:
            info = ydl.extract_info(search, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            path = f"/tmp/{info['id']}.m4a"
            title = info.get('title', 'Unknown Title')

        playlist_queues.setdefault(ctx.guild.id, []).insert(0, {'path': path, 'title': title})
        await ctx.send(f"🎶 Now playing: {title}")

        if not vc.is_playing() and not vc.is_paused():
            await play_next(ctx)
        else:
            vc.stop()

    except Exception as e:
        print(f"[ERROR] play(): {traceback.format_exc()}")
        await ctx.send(f"❌ Failed to play song: {e}")

@bot.command(name="add")
async def add(ctx, *, search: str):
    try:
        with youtube_dl.YoutubeDL(get_ydl_opts(True)) as ydl:
            info = ydl.extract_info(search, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            path = f"/tmp/{info['id']}.m4a"
            title = info.get('title', 'Unknown Title')

        playlist_queues.setdefault(ctx.guild.id, []).append({'path': path, 'title': title})
        await ctx.send(f"➕ Added to queue: {title}")
    except Exception as e:
        print(f"[ERROR] add(): {traceback.format_exc()}")
        await ctx.send(f"❌ Failed to add song: {e}")

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
        await ctx.send("▶️ Resumed.")
    else:
        await ctx.send("Nothing to resume.")

@bot.command(name="next")
async def next_song(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_playing():
        vc.stop()
    await ctx.send("⏭️ Skipping...")

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

@bot.command(name="loop")
async def loop(ctx, mode: str):
    if mode not in [LOOP_NONE, LOOP_QUEUE, LOOP_SINGLE]:
        await ctx.send("❌ Use: none | queue | single")
        return
    loop_mode[ctx.guild.id] = mode
    await ctx.send(f"🔁 Loop mode set to: {mode}")

@bot.command(name="clear")
async def clear(ctx):
    playlist_queues[ctx.guild.id] = []
    await ctx.send("🧹 Cleared queue.")

@bot.command(name="last")
async def last(ctx):
    history = play_history.get(ctx.guild.id, [])
    if len(history) < 2:
        await ctx.send("No previous track.")
        return
    prev = history[-2]
    playlist_queues.setdefault(ctx.guild.id, []).insert(0, prev)
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc:
        vc.stop()
    await ctx.send(f"🔁 Replaying: {prev['title']}")

@bot.command(name="show")
async def show(ctx):
    queue = playlist_queues.get(ctx.guild.id, [])
    now = now_playing.get(ctx.guild.id)
    history = play_history.get(ctx.guild.id, [])
    msg = f"🎶 Now playing: {now}\n\n" if now else "No song playing.\n"
    if history:
        msg += "🕓 History:\n" + "\n".join(f"• {h['title']}" for h in history[-5:]) + "\n\n"
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
        await ctx.send("👋 Disconnected.")
    else:
        await ctx.send("I'm not in a voice channel.")

@bot.command(name="commands")
async def commands_list(ctx):
    await ctx.send("""
**🎵 Music Bot Commands**
!play <keywords> — Play immediately
!add <keywords> — Add to queue
!stop — Pause music
!resume — Resume
!volume <0-100> — Set volume
!clear — Clear queue
!next — Play next song
!last — Replay previous
!loop <none|queue|single> — Set loop mode
!show — Show queue and recent
!leave — Disconnect bot
!commands — Show help
    """)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(os.getenv("BOT_TOKEN"))
