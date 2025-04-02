# 🎶 Discord Music Bot

[![GitHub release](https://img.shields.io/github/v/release/gtz666/Discord-Music-Bot?include_prereleases)](https://github.com/gtz666/Discord-Music-Bot/releases)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)

![Discord](https://img.shields.io/badge/discord.py-2.x-purple)

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.txt)

A full-featured, slash-command-based music bot for Discord, built with Python. Supports queue management, YouTube streaming, loop modes, auto-playlist generation, and channel restriction.

---

## 🚀 Features

- `!play <keywords/link>` — Search YouTube and play immediately (force join + force play)
- `!add <keywords>` — Add song to queue without playback
- `!stop / !resume` — Pause and resume playback
- `!volume <0–100>` — Adjust volume
- `!next / !last` — Skip to next or replay previous
- `!loop <none|queue|single>` — Choose playback loop mode
- `!gen <keyword>` — Auto-add 5 related YouTube tracks
- `!show` — Show current playing song, recent history, and queue
- `!clear` — Clear the queue
- `!leave` — Disconnect bot from voice channel
- `!commands` — Show help list

---

## 📦 Setup

### 1. Clone the project

```bash
git clone https://github.com/gtz666/Discord-Music-Bot.git
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
├── Procfile          
├── runtime.txt
```

## License

``MIT License``. You are free to use, modify, and distribute this bot.


## 💡 Todo / Ideas

Embed-based visual display

Multi-language support

Save/load playlists

Web dashboard interface
