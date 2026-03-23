# ☕ CafeBot

CafeBot is a multi-purpose, modular Discord bot built with Python and `discord.py`. It features a custom data-storage solution and provides a wide array of utilities ranging from server moderation and tabletop RPG (D&D) mechanics to a fully functioning server economy and social engagement tools.

## 🚀 Features

* **Modular Architecture:** The bot's logic is cleanly separated into dedicated modules (`EconomyModule`, `FunModule`, `DndModule`, etc.) to ensure maintainability and scalability.
* **Custom Data Persistence:** Implements a JSON-based local storage system (`DataStorage.py`) that serializes object-oriented Python classes (like D&D characters and User profiles) into persistent data files. 
* **Custom Permissions Wrapper:** Utilizes a custom `@is_authorized` decorator to strictly manage access levels (Server Admin, Moderator, Bot Admin) across all commands.
* **Tabletop RPG Mechanics:** Includes complex dice rolling (supporting modifiers and multiple dice sets) and an object-oriented D&D character creator that tracks stats, proficiencies, and HP.
* **Server Economy:** A built-in economy system where users can work shifts, claim daily rewards, maintain streaks, and tip other users, complete with a leaderboard system.
* **Engagement & Social Systems:** Features a robust quote-saving system, an interactive duel mini-game, a marriage registry, and categorized GIF reactions.
* **Robust Moderation:** Essential server management tools including purging, channel lockdowns, slowmode toggling, and user timeout/kick/ban capabilities.

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Library:** `discord.py`
* **Configuration:** `python-dotenv` for secure environment variable management.

## 💻 Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/CafeBot.git](https://github.com/yourusername/CafeBot.git)
   cd CafeBot
   ```

2. **Create and activate a virtual environment:**
   This keeps the bot's dependencies isolated from your system's global Python environment.
   * **Windows:**
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   * **macOS/Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup:**
   Create a `.env` file in the root directory and add your bot token and administrator IDs (comma-separated):
   ```env
   token=YOUR_DISCORD_BOT_TOKEN
   administrators=YOUR_DISCORD_ID,YOUR_FRIENDS_DISCORD_ID
   ```

5. **Run the bot:**
   ```bash
   python botMain.py
   ```

## 📁 Project Structure

* `botMain.py`: The main entry point and command router.
* `DataStorage.py`: Handles loading, saving, and caching of all JSON data.
* `Classes/`: Contains the object-oriented data models (`UserSavesClass`, `DndCharacter`, `QuoteClass`,`RequestClass`).
* `*Module.py`: The separated logical controllers for different bot functions (Economy, DnD, Moderation, Fun).
* `Saves/`: Directory where the persistent JSON data files are stored.
