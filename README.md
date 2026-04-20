# ☕ CafeBot

CafeBot is a multi-purpose, modular Discord bot built with Python and `discord.py`. It features a custom data-storage solution and provides a wide array of utilities ranging from server moderation and tabletop RPG (D&D) mechanics to a full-fledged server economy, trivia, music playback, faith/devotional tools, and social engagement systems.

---

## Features

### Core Architecture
- **Modular Design** — Bot logic is cleanly separated into dedicated modules (`EconomyModule`, `FunModule`, `DndModule`, `TriviaModule`, `MusicModule`, `FaithModule`, `ModerationModule`, `BotAdminModule`) for maintainability and scalability.
- **Custom Data Persistence** — JSON-based local storage (`DataStorage.py`) that serializes object-oriented Python classes (user profiles, D&D characters, quotes, requests, verses) into persistent data files.
- **Custom Permissions Wrapper** — An `@is_authorized` decorator manages access levels (Server Admin, Moderator, Bot Admin, per-permission checks like kick/ban/mute) across all commands.
- **Unified Prefix + Slash Commands** — Commands are exposed both as traditional `.` prefix commands and as Discord slash commands via a shared interaction-context adapter.

### Server Economy
- **Work shifts** with cooldown and randomized payouts (`.shift`).
- **Daily rewards** with persistent streak tracking and escalating bonuses (`.daily`).
- **Tipping** between users and a bean leaderboard (`.tip`, `.bean_top`, `.beans`).
- **Banking** with deposit, withdraw, and a 5-tier upgradeable vault cap (`.bank`, `.deposit`, `.withdraw`, `.bank_upgrade`).
- **Robbery** mechanic with success rates, cooldowns, and victim immunity windows (`.rob`).
- **Lottery** with tiered ticket purchases, pot tracking, and periodic draws (`.lottery`, `.lottery_buy`).
- **Gambling mini-games** — slot machine (`.slots`) and blackjack (`.blackjack`).

### Trivia
- **Session-based trivia** with configurable round counts (`.start_trivia`) and quick single-question mode (`.quick_trivia`).
- **Per-user category preferences** via dropdown config UI (`.trivia_config`).
- **Dynamic question timeouts** scaled to question/answer length (15–40 seconds).
- **Normalized, fuzzy answer matching** (punctuation/case-insensitive, ~0.82 similarity tolerance).
- **Stats tracking** (`.trivia_stats`) and admin question management (`.add_trivia`, `.remove_trivia`).

### Music Playback
- **YouTube / SoundCloud search and playback** (`.play`).
- **Queue management** — skip (`.skip_song`), pause/resume (`.pause_song`), loop toggle (`.toggle_loop`), queue view (`.show_queue`).
- **Voice channel control** (`.leave_channel`).
- **Hardened yt-dlp integration** with browser-header fallback and SoundCloud alternative to mitigate rate limiting.

### Faith / Devotional Tools
- **Random Bible verse lookup** across multiple translations (`.random_verse <version>`).
- **Verse context view** showing surrounding passages (`.verse_context`).
- **Anonymous testimony submission** via DM with confirmation, relayed to a designated channel (`.send_testimony`).

### Tabletop RPG (D&D)
- **Dice rolling** for standard D&D types (d4 – d100) with modifiers (`.roll_dice`, `.roll_multiple`).
- **Character creation** supporting 13 D&D classes (`.create_character`).
- **Full character sheets** with ability scores, skills, saves, AC, HP, gold, and inventory (`.view_character`, `.view_characters`, `.character_delete`).

### Engagement & Social
- **Marriage registry** with mutual-accept requests, divorce, partner lookup, and a longest-marriage leaderboard (`.marry`, `.divorce`, `.partner`, `.marriage_top`).
- **Adoption system** with family hierarchy and family tree view (`.adopt`, `.unadopt`, `.family`).
- **Quote database** (guild-scoped) with add/remove, search, stats, and leaderboard (`.add_quote`, `.remove_quote`, `.quote`, `.quotes`, `.quote_list`, `.quote_count`, `.quote_top`, `.quote_search`, `.quote_stats`).
- **GIF reaction system** with customizable categories and author/target templating (`.gif`).
- **Duel mini-game** — turn-based PvP with 100 HP and randomized damage (`.duel`).
- **Magic 8-Ball** with admin-editable response pool (`.magic_eight_ball`).
- **Coin flip** (`.coinflip`) and unified **profile dashboard** showing beans, streak, characters, and marriage status (`.profile`).

### Moderation
- Message purge (`.purge`), per-channel and server-wide lockdowns (`.lockdown_channel`, `.lockdown`), slowmode with a 6-hour cap (`.slowmode`), and user kick / ban / unban with reasons (`.kick_user`, `.ban_user`, `.unban_user`).

### Bot Admin
- Privileged overrides for moderating social state: `.force_marry`, `.force_divorce`, `.force_adopt`, `.force_unadopt`, `.force_lottery_draw`.

---

## Tech Stack

| Component     | Technology               |
|---------------|--------------------------|
| Language      | Python 3.10+             |
| Bot Library   | `discord.py 2.7+` (with voice) |
| Audio         | `yt-dlp`, `imageio-ffmpeg`, FFmpeg |
| Configuration | `python-dotenv`          |
| Data Storage  | JSON (local filesystem)  |

---

## Prerequisites

- Python 3.10+
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- The bot must be invited to your server with the **Message Content Intent** enabled
- **FFmpeg** available on your system `PATH` (required for the music module)

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/CafeBot.git
   cd CafeBot
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Create a `.env` file in the root directory:
   ```env
   token=YOUR_DISCORD_BOT_TOKEN
   administrators=YOUR_DISCORD_ID,ANOTHER_DISCORD_ID
   ```

   | Variable         | Description                                              |
   |------------------|----------------------------------------------------------|
   | `token`          | Your Discord bot token                                   |
   | `administrators` | Comma-separated Discord user IDs with bot-admin access   |

5. **Run the bot:**
   ```bash
   python botMain.py
   ```

---

## Project Structure

```
CafeBot/
├── botMain.py            # Entry point and command router (prefix + slash)
├── DataStorage.py        # JSON load/save/cache handler
├── EconomyModule.py      # Economy: shifts, daily, tips, bank, lottery, rob, slots, blackjack
├── TriviaModule.py       # Trivia sessions, category config, normalized answer matching
├── MusicModule.py        # YouTube/SoundCloud playback, queue, loop, pause
├── FaithModule.py        # Bible verse lookup, verse context, anonymous testimony
├── DndModule.py          # D&D dice and character commands
├── FunModule.py          # Duels, quotes, marriage, adoption, GIFs, 8-ball, profile
├── ModerationModule.py   # Purge, lockdown, slowmode, kick/ban/unban
├── BotAdminModule.py     # Bot-admin-only force commands
├── Classes/
│   ├── UserSavesClass.py # User profile data model (economy, streaks, family, stats)
│   ├── DndCharacter.py   # D&D character data model
│   ├── QuoteClass.py     # Quote data model
│   ├── RequestClass.py   # Pending marriage/adoption request model
│   └── Verse.py          # Bible verse data model
├── Saves/
│   ├── UserSaves.json
│   ├── QuoteUsers.json
│   ├── quotes.json
│   ├── trivia_questions.json
│   ├── bible_index.json
│   ├── MagicEightBall.json
│   ├── gif_messages.json
│   └── gifs.json
├── COPYING               # GPL-3.0 license text
└── requirements.txt
```

---

## Configuration Notes

- The `Saves/` directory is created and managed automatically by `DataStorage.py`.
- The `.env` file should **never** be committed to version control. It is listed in `.gitignore`.
- Bot admin IDs defined in `administrators` have elevated permissions beyond standard Discord server roles.
- The music module will warn on startup if `ffmpeg` is not found on `PATH`.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push and open a pull request

---

## License

CafeBot is licensed under the **GNU General Public License v3.0** (GPL-3.0). You are free to use, modify, and redistribute this software under the terms of that license; any distributed derivative work must also be released under GPL-3.0. See the [`COPYING`](./COPYING) file for the full license text, or visit <https://www.gnu.org/licenses/gpl-3.0.html>.
