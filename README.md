# 🎶 Discord Music Bot

A full-featured, slash-command-based music bot for Discord, built with Python. Supports queue management, YouTube streaming, loop modes, auto-playlist generation, and channel restriction.

---

## 🚀 Features

- 🎵 `/play` — Search and play songs from YouTube
- 🔗 `/playlink` — Play music from a direct link
- ➕ `/add` — Add songs to the playlist
- 📜 `/show` — View current, recent, and upcoming songs
- ⏸️ `/stop`, `/resume`, `/next`, `/last` — Playback controls
- 🔁 `/loop` — Set looping mode: `none`, `queue`, or `single`
- 🧹 `/clear` — Clear the playlist
- 🔉 `/volume` — Adjust volume in real time
- 🧠 `/gen` — Auto-generate 5 relevant songs by genre
- 📺 `/setchannel` — Bind bot to a specific command channel
- 🛡️ Slash commands only work in selected text channel

---

## 📦 Setup

### 1. Clone the project

```bash
git clone https://github.com/gtz666/discord-music-bot.git
cd discord-music-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a .env file

```BOT_TOKEN=your_discord_bot_token_here```

✅ Make sure ```.env``` is in your ```.gitignore```

## ▶️ Run the Bot
```bash
python main.py
```

Use ```!sync``` if commands don't appear immediately

## 📁 File Structure

```bash

discord-music-bot/
├── main.py                # Main bot code
├── requirements.txt       # Dependency list
├── .gitignore             # Git ignore config
├── .env                   # Bot token (not uploaded)
├── allowed_channels.json  # Channel restrictions (auto-generated)
├── README.md              # Project overview
├── CHANGELOG.md           # Update history
```

## License

``MIT License``. You are free to use, modify, and distribute this bot.


## 💡 Todo / Ideas

Embed-based visual display

Multi-language support

Save/load playlists

Web dashboard interface
