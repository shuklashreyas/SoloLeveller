# SoloLeveller — A Gamified Habit Tracker

## Overview
SoloLeveller turns personal growth into an RPG-style progression loop inspired by Solo Leveling. You build seven core attributes through positive actions (“Atone”) and see them dip when you log negative behaviors (“Sin”). Daily play rewards consistency, variety, and honesty.

## Tech Stack
- Python — core logic  
- Tkinter — desktop UI  
- SQLite — local persistence  
- Pygame — SFX/BGM audio backend  
- Pillow (optional) — used for certain visual effects if enabled

## Current Feature Set (WIP)

### Attributes, Sins, and Logging
- Seven positive attributes: Spiritual, Physical, Mindful, Social, Integrity, Intellect, Character.
- Seven deadly sins mapped to the attribute they harm.
- Atoning/Sinning dialogs with curated menus plus an “Other…” option for custom entries.
- Today-only logging: you can only add or edit logs for the current day.
- Daily Double: each day highlights one Atone category and one Sin; matching entries are doubled in magnitude.

### Progression & Rank
- Attribute scale: FIFA-style 35–99 bounds with a sensible progression curve.
- XP strip and levels: total XP, level calculation, and progress to next level are shown; level-ups trigger a toast and SFX.

### Dates and History
- Start-day clamp: your viewable range is locked from the day you complete the baseline quiz up to today.  
  Example: if you started on Aug 13, you can view Aug 13…today and nothing outside that window.
- Daily journal with a writing prompt per day.
- Action log shows all entries for the selected date.

### Contracts (Pacts)
- My Contracts: your active, time-boxed commitments.
  - You can create one active personal contract at a time, lasting 1–7 days.
  - Global cap: maximum 3 active contracts total (personal + claimed).
  - Breaking a contract marks it broken and applies the XP penalty once (tracked).
- Available Today: rotating, time-limited contract offers you can claim before they expire (some expire in hours).
  - New offers are auto-generated daily.
  - A badge on the Contracts button shows how many offers are currently available.

### Themes, Audio, and UX
- Theme picker with multiple palettes; the whole UI restyles instantly.
- SFX and background music with a mute toggle (state persists).
- Baseline quiz on first run to establish starting stats.

## Screenshots (Work in Progress)
![Dashboard](sc1.png)
![Contracts](sc2.png)
![Theme & Stats](sc3.png)

## Getting Started

### Install
```bash
git clone <repository-url>
cd habit-tracker
pip install -r requirements.txt
python main.py
```

### Resetting Data
If you want to reset all progress: rm habit_tracker.db


# License

Legends Never Fall by Aylex | https://freetouse.com/music/aylex
Free To Use | https://freetouse.com/music
Music promoted by https://www.free-stock-music.com

Winery by Aylex | https://freetouse.com/music/aylex
Free To Use | https://freetouse.com/music
Music promoted by https://www.free-stock-music.com