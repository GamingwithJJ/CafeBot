# ☕ CafeBot

CafeBot is a multi-purpose, modular Discord bot built with Python and `discord.py`. It features a custom data-storage solution and provides a wide array of utilities ranging from server moderation and tabletop RPG (D&D) mechanics to a fully functioning server economy and social engagement tools.

---

## Features

- **Modular Architecture** — Bot logic is cleanly separated into dedicated modules (`EconomyModule`, `FunModule`, `DndModule`, etc.) for maintainability and scalability.
- **Custom Data Persistence** — JSON-based local storage (`DataStorage.py`) that serializes object-oriented Python classes (D&D characters, user profiles, etc.) into persistent data files.
- **Custom Permissions Wrapper** — A `@is_authorized` decorator strictly manages access levels (Server Admin, Moderator, Bot Admin) across all commands.
- **Tabletop RPG Mechanics** — Complex dice rolling with modifiers and an object-oriented D&D character creator tracking stats, proficiencies, and HP.
- **Server Economy** — Users can work shifts, claim daily rewards, maintain streaks, and tip others, with a leaderboard system.
- **Engagement & Social Systems** — Quote saving, an interactive duel mini-game, a marriage registry, and categorized GIF reactions.
- **Robust Moderation** — Channel purging, lockdowns, slowmode toggling, and user timeout/kick/ban capabilities.

---

## Tech Stack

| Component     | Technology               |
|---------------|--------------------------|
| Language      | Python 3.x               |
| Bot Library   | `discord.py 2.x`         |
| Configuration | `python-dotenv`          |
| Data Storage  | JSON (local filesystem)  |

---

## Prerequisites

- Python 3.10+
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- The bot must be invited to your server with the **Message Content Intent** enabled

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
├── botMain.py            # Entry point and command router
├── DataStorage.py        # JSON load/save/cache handler
├── EconomyModule.py      # Economy commands (work, daily, tip, leaderboard)
├── DndModule.py          # D&D commands (character creation, dice rolling)
├── FunModule.py          # Fun/social commands (duels, GIFs, marriage, quotes)
├── ModerationModule.py   # Moderation commands (purge, lockdown, ban, kick)
├── BotAdminModule.py     # Bot-admin only commands
├── Classes/
│   ├── UserSavesClass.py # User profile data model
│   ├── DndCharacter.py   # D&D character data model
│   ├── QuoteClass.py     # Quote data model
│   └── RequestClass.py   # Request data model
├── Saves/
│   ├── MagicEightBall.json
│   ├── gif_messages.json
│   └── gifs.json
└── requirements.txt
```

---

## Configuration Notes

- The `Saves/` directory is created and managed automatically by `DataStorage.py`.
- The `.env` file should **never** be committed to version control. It is listed in `.gitignore`.
- Bot admin IDs defined in `administrators` have elevated permissions beyond standard Discord server roles.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push and open a pull request

---

## License

This project is currently unlicensed. See [choosealicense.com](https://choosealicense.com) if you'd like to add one.
