# 📒 Changelog

All notable changes to this project will be documented in this file.

---

## v0.3.0 – April 1, 2025

### Major Improvements
- Use ! commands instead of slash commands to avoid conflict with Discord Default commands
- Refactored `!play` to **immediately insert and play** a song (without clearing the queue)
- Ensured bot **moves voice channel automatically** if user is in a different one
- `!play` now triggers `vc.stop()` properly to skip current track

### Bug Fixes
- Fixed issue where `!play` would add song but not play
- Fixed double entries in playback history (`!show`)
- Prevented crash when `!leave` is called mid-play
- Improved queue logic: current song is now **not** part of queue (`now_playing` is separate)
- Loop logic updated (`loop single` reinserts current track correctly)

### New Commands
- `!add` – Add a song to the end of the queue without playing
- `!leave` – Disconnect bot from voice channel
- `!show` – Displays current track, recent history (5 max), and upcoming queue

## [v0.2.0] - 2024-04-01

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

## [v0.1.0] - 2024-03-31

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
