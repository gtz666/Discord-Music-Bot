# 📒 Changelog

All notable changes to this project will be documented in this file.

---

## [v0.2.0] - 2024-04-02

### Added
- ✅ All commands converted to slash (HybridCommand) format
- ✅ `/sync` command for manual slash command registration
- ✅ `/gen` auto-playlist generator by keyword (e.g. `/gen lofi`)
- ✅ `/setchannel` with UI dropdown to restrict bot commands to a selected text channel
- ✅ Persistent `allowed_channels.json` to save channel bindings across restarts
- ✅ `/loop` to set repeat mode: `none`, `queue`, or `single`
- ✅ `/last` command to replay previous song (up to 5-history)
- ✅ `/volume` with real-time update
- ✅ `/show` now displays current + queue + history
- ✅ `/` command (`/?`) to show full command list

### Improved
- ✅ Commands now check and respect allowed channel restriction
- ✅ Welcome message sent when bot joins a server

### Removed
- ❌ Removed reminder-related commands and background task

### Security
- ✅ Token now stored in `.env` and loaded via `dotenv`
- ✅ `.gitignore` updated to exclude `.env`, JSON state files, and cache

---

## [v0.1.0] - 2024-04-01

### Added
- Basic command-based music bot with:
  - `!play` to search and play a song
  - `!playlink` to play by URL
  - `!add` to add to queue
  - `!stop`, `!resume`, `!next`, `!clear`, `!volume`
  - `!show` to display playlist
  - `!last` to replay previous song
  - `!leave` to disconnect
- Auto disconnect after 3 minutes of idle
- Simple reminder system via `!remindme`
- Emoji reactions for each command

---
