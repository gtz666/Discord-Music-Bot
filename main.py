import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
import asyncio
import yt_dlp as youtube_dl
import os
import json
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global state
voice_clients = {}
volume_levels = {}
playlist_queues = {}
now_playing = {}
current_sources = {}
play_history = {}
loop_mode = {}  # none, queue, single

# allowed_channels = {}

# Load allowed_channels from JSON (persistent channel binding)
try:
    with open("allowed_channels.json", "r") as f:
        allowed_channels = json.load(f)
        allowed_channels = {int(k): int(v) for k, v in allowed_channels.items()}
except (FileNotFoundError, json.JSONDecodeError):
    allowed_channels = {}

# ---------------- MUSIC LOOP CONTROL ----------------
LOOP_NONE = "none"
LOOP_QUEUE = "queue"
LOOP_SINGLE = "single"

# ---------------- PLAYBACK ----------------
def get_ffmpeg_options():
    return {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    }

def play_next(ctx):
    guild_id = ctx.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    queue = playlist_queues.get(guild_id, [])
    if not queue or not vc:
        now_playing[guild_id] = None
        return False

    item = queue[0]
    url, title = item['url'], item['title']
    volume = volume_levels.get(guild_id, 0.5)
    ffmpeg_options = get_ffmpeg_options()
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **ffmpeg_options), volume=volume)
    current_sources[guild_id] = source
    now_playing[guild_id] = title

    def after_playing(err):
        mode = loop_mode.get(guild_id, LOOP_NONE)
        if mode == LOOP_SINGLE:
            pass
        elif mode == LOOP_QUEUE:
            queue.append(queue.pop(0))
        else:
            queue.pop(0)

        async def idle_disconnect():
            await asyncio.sleep(180)
            if not vc.is_playing() and not vc.is_paused():
                await vc.disconnect()
                voice_clients.pop(guild_id, None)

        play_next(ctx)
        asyncio.run_coroutine_threadsafe(idle_disconnect(), bot.loop)

    vc.play(source, after=after_playing)
    play_history.setdefault(guild_id, []).append({'url': url, 'title': title})
    if len(play_history[guild_id]) > 5:
        play_history[guild_id] = play_history[guild_id][-5:]
    return True

# ---------------- HYBRID COMMANDS ----------------

@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"🔄 Synced {len(synced)} slash commands.")

@bot.hybrid_command(name="play")
async def play(ctx, *, search: str):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    if not ctx.author.voice:
        await ctx.send("You must be in a voice channel.")
        return
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not vc:
        vc = await ctx.author.voice.channel.connect()
        voice_clients[ctx.guild.id] = vc

    ydl_opts = {'format': 'bestaudio', 'noplaylist': True, 'quiet': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
        url, title = info['url'], info['title']

    playlist_queues.setdefault(ctx.guild.id, []).append({'url': url, 'title': title})
    await ctx.send(f"Added to queue: {title}")
    if not vc.is_playing() and not vc.is_paused():
        play_next(ctx)

@bot.hybrid_command(name="volume")
async def volume(ctx, level: int):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    if not (0 <= level <= 100):
        await ctx.send("Volume must be 0-100")
        return
    volume_levels[ctx.guild.id] = level / 100
    src = current_sources.get(ctx.guild.id)
    if src:
        src.volume = level / 100
    await ctx.send(f"Volume set to {level}%")

@bot.hybrid_command(name="stop")
async def stop(ctx):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("Music paused.")
    elif vc and vc.is_paused():
        await ctx.send("Already paused.")
    else:
        await ctx.send("Nothing is playing.")

@bot.hybrid_command(name="resume")
async def resume(ctx):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("Resumed.")
    else:
        await ctx.send("Nothing to resume.")

@bot.hybrid_command(name="clear")
async def clear(ctx):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    playlist_queues[ctx.guild.id] = []
    await ctx.send("Queue cleared.")

@bot.hybrid_command(name="next")
async def next(ctx):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    queue = playlist_queues.get(ctx.guild.id, [])
    if vc and queue:
        vc.stop()
        await ctx.send(f"Playing the next song: {queue[0]['title']}")
    else:
        await ctx.send("No more songs in the playlist.")

@bot.hybrid_command(name="last")
async def last(ctx):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    history = play_history.get(ctx.guild.id, [])
    if len(history) < 2:
        await ctx.send("No previous song.")
        return
    prev = history[-2]
    playlist_queues.setdefault(ctx.guild.id, []).insert(0, prev)
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc:
        vc.stop()
    await ctx.send(f"Replaying: {prev['title']}")

@bot.hybrid_command(name="show")
async def show(ctx):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
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

@bot.hybrid_command(name="loop")
async def loop(ctx, mode: str):
    if mode not in [LOOP_NONE, LOOP_QUEUE, LOOP_SINGLE]:
        await ctx.send("Loop mode must be: none / queue / single")
        return
    loop_mode[ctx.guild.id] = mode
    await ctx.send(f"Loop mode set to {mode}.")

@bot.hybrid_command(name="gen")
async def gen(ctx, *, keyword: str):
    if allowed_channels.get(ctx.guild.id) and ctx.channel.id != allowed_channels[ctx.guild.id]:
        return
    await ctx.send(f"🔎 Generating songs for: {keyword}")
    ydl_opts = {'format': 'bestaudio', 'noplaylist': True, 'quiet': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        results = ydl.extract_info(f"ytsearch5:{keyword}", download=False)['entries']
    playlist = [{'url': r['url'], 'title': r['title']} for r in results]
    playlist_queues.setdefault(ctx.guild.id, []).extend(playlist)
    await ctx.send(f"Added {len(playlist)} songs to the playlist.")
    if not discord.utils.get(bot.voice_clients, guild=ctx.guild):
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
    if not discord.utils.get(bot.voice_clients, guild=ctx.guild).is_playing():
        play_next(ctx)

@bot.hybrid_command(name="setchannel", description="Restrict bot to one command channel")
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    class ChannelSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=c.name, value=str(c.id))
                for c in ctx.guild.text_channels[:25]
            ]
            super().__init__(placeholder="📂 Select command channel", options=options)

        async def callback(self, interaction: discord.Interaction):
            # 保存频道 ID
            allowed_channels[ctx.guild.id] = int(self.values[0])
            # 写入 JSON 持久化
            with open("allowed_channels.json", "w") as f:
                json.dump({str(k): v for k, v in allowed_channels.items()}, f)
            # 回应用户
            await interaction.response.send_message(
                f"✅ Commands are now restricted to <#{self.values[0]}>", ephemeral=True
            )

    view = View()
    view.add_item(ChannelSelect())
    await ctx.send("Choose a text channel for bot commands:", view=view)
@bot.hybrid_command(name="?", description="Show all commands")
async def help_command(ctx):
    await ctx.send("""
    **🎵 Music Commands**
    `/play <keywords>` - Search and play music
    `/playlink <url>` - Play from a direct YouTube URL
    `/add <keywords>` - Add song to queue
    `/show` - Show current + queued songs
    `/stop` - Pause current song
    `/resume` - Resume paused song
    `/next` - Skip to next
    `/last` - Play previous song
    `/clear` - Clear the queue
    `/volume <0-100>` - Set volume
    `/loop <none|queue|single>` - Loop setting
    `/gen <keyword>` - Auto-generate 5 songs of that style
    `/setchannel` - Restrict bot to one text channel

    💡 Use `/sync` in dev mode to update slash commands.
        """)

@bot.event
async def on_guild_join(guild):
    default_channel = guild.system_channel or discord.utils.get(guild.text_channels, permissions__send_messages=True)
    if default_channel:
        await default_channel.send("👋 Hello! I'm your music bot.\n Use `/setchannel` to make me listening to one channel.\n Use `!sync` and /? to see all the commands")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Command sync failed: {e}")

bot.run(os.getenv("BOT_TOKEN"))
