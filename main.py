# main.py
import subprocess
import discord
from discord.ext import commands
import asyncio
import yt_dlp as youtube_dl
import os
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Write cookies from environment variable to file
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

def get_ffmpeg_options(local=False):
    return {} if local else {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    }

def get_ffmpeg_path():
    import shutil
    return shutil.which("ffmpeg") or "ffmpeg"

print(f"[DEBUG] FFmpeg path used: {get_ffmpeg_path()}")

def play_next(ctx):
    guild_id = ctx.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    queue = playlist_queues.get(guild_id, [])

    if not queue or not vc or not vc.is_connected():
        now_playing[guild_id] = None
        return False

    item = queue.pop(0)
    url, title = item['url'], item['title']
    volume = volume_levels.get(guild_id, 0.5)
    ffmpeg_options = get_ffmpeg_options()
    filepath = item.get("filepath") or url  # in case you're using local file later

    try:
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(filepath, executable=get_ffmpeg_path(), **ffmpeg_options),
            volume=volume
        )
    except Exception as e:
        print(f"[ERROR] FFmpegPCMAudio failed: {e}")
        async def send_error():
            await ctx.send(f"❌ Audio source error: {e}")
        bot.loop.create_task(send_error())
        return False

    current_sources[guild_id] = source
    now_playing[guild_id] = title

    def after_playing(err):
        try:
            if loop_mode.get(guild_id) == LOOP_SINGLE:
                playlist_queues.setdefault(guild_id, []).insert(0, item)
            elif loop_mode.get(guild_id) == LOOP_QUEUE:
                playlist_queues.setdefault(guild_id, []).append(item)

            async def idle_disconnect():
                await asyncio.sleep(180)
                if not vc.is_playing() and not vc.is_paused():
                    await vc.disconnect()
                    voice_clients.pop(guild_id, None)

            play_next(ctx)
            asyncio.run_coroutine_threadsafe(idle_disconnect(), bot.loop)
        except Exception as e:
            now_playing[guild_id] = None
            print(f"[ERROR] after_playing(): {e}")

    try:
        vc.play(source, after=after_playing)
        print("[DEBUG] vc.play() called successfully.")
    except Exception as e:
        print(f"[ERROR] vc.play(): {e}")

    # update history
    if not play_history.get(guild_id) or play_history[guild_id][-1]['url'] != url:
        play_history.setdefault(guild_id, []).append({'url': url, 'title': title})
        if len(play_history[guild_id]) > 5:
            play_history[guild_id] = play_history[guild_id][-5:]

    return True


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

        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'cookiefile': 'cookies.txt'
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            url, title = info['webpage_url'], info['title']

        queue = playlist_queues.setdefault(ctx.guild.id, [])
        queue.insert(0, {'url': url, 'title': title})
        await ctx.send(f"🎶 Now playing: {title}")

        if not vc.is_playing() and not vc.is_paused():
            play_next(ctx)
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
    playlist = [{'url': r['url'], 'title': r['title']} for r in results]
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
        info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
        url, title = info['url'], info['title']
    playlist_queues.setdefault(ctx.guild.id, []).append({'url': url, 'title': title})
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
