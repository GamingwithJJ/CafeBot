import os
import json
from Classes.UserSavesClass import User
from Classes.RequestClass import Request
from Classes.DndCharacter import DndCharacter
from Classes.QuoteClass import Quote
from Classes.Verse import Verse
import datetime
from dotenv import dotenv_values



user_data = {} # Store users by userID = UserSavesClass
DATA_FILE = "Saves/UserSaves.json"
QUOTES_FILE = "Saves/quotes.json"
GIFS_FILE = "Saves/gifs.json"
MESSAGES_FILE = "Saves/gif_messages.json"
MAGIC_EIGHT_BALL_FILE = "Saves/MagicEightBall.json"
VERSES_FILE = "Saves/verses.json"
TRIVIA_QUESTIONS_DIR = "Saves/trivia"
BIBLE_INDEX_FILE = "Saves/bible_index.json"

# Format: { "category_name": { "sub_category_name": [ ("Question", ["answer1", "answer2"]) ] } }
trivia_questions = {}

# Format:  {"version" : {"book" : {"chapter" : "verse" : ("VerseContent")}}}
bible_index = {}

verses = []

administrators = []


magic_eight_ball = []

LEGACY_GUILD_ID = "1399918182529105920"

quotes = {}  # {guild_id_str: {author_name: [Quote]}}


gifs = {}


gif_messages = {}

lottery_pot = {}     # guild_id_str → float
lottery_entries = {}  # guild_id_str → {discord_id_str: ticket count}
lottery_active = {}  # guild_id_str → {ticket_cap, end_time, max_per_user, channel_id}
LOTTERY_FILE = "Saves/lottery.json"

jackpot_pot = {}  # guild_id_str → float
JACKPOT_FILE = "Saves/jackpot.json"

"""
Checks if a user with a specified discord id exists and creats one if it does not.
"""


def get_or_create_user(user_id):
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        user_data[user_id_str] = User(user_id_str)
    return user_data[user_id_str]


def get_lottery_pot(guild_id):
    return lottery_pot.get(str(guild_id), 0.0)


def get_lottery_entries(guild_id):
    return lottery_entries.get(str(guild_id), {})


def save_eight_ball():
    """Saves magic eight ball responses to JSON file."""
    try:
        with open(MAGIC_EIGHT_BALL_FILE, "w", encoding="utf-8") as f:
            json.dump(magic_eight_ball, f, indent=4, ensure_ascii=False)
        print("✅Eight ball responses saved!")
    except Exception as e:
        print(f"❌ Error saving eight ball responses: {e}")


def save_quotes():
    """Saves quotes to JSON file."""
    data_to_save = {}

    for guild_id, author_dict in quotes.items():
        data_to_save[guild_id] = {}
        for author, quote_list in author_dict.items():
            data_to_save[guild_id][author] = [q.to_dict() for q in quote_list]

    try:
        with open(QUOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        print("✅ Quotes saved!")
    except Exception as e:
        print(f"❌ Error saving quotes: {e}")


def save_gifs():
    """Saves gifs to JSON file."""
    try:
        with open(GIFS_FILE, "w", encoding="utf-8") as f:
            json.dump(gifs, f, indent=4)
        print("✅ Gifs saved!")
    except Exception as e:
        print(f"❌ Error saving gifs: {e}")


def save_gif_messages():
    """Saves gif messages to JSON file."""
    try:
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(gif_messages, f, indent=4)
        print("✅ Gif messages saved!")
    except Exception as e:
        print(f"❌ Error saving gif messages: {e}")


def save_verses():
    """Saves verses to JSON file."""
    try:
        with open(VERSES_FILE, "w", encoding="utf-8") as f:
            # Convert all Verse objects to dictionaries
            json.dump([v.to_dict() for v in verses], f, indent=4, ensure_ascii=False)
        print("✅ Verses saved!")
    except Exception as e:
        print(f"❌ Error saving verses: {e}")


def save_bible_index():
    """Saves the Bible index to JSON. Only needed if you mutate it at runtime."""
    try:
        with open(BIBLE_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(bible_index, f, indent=4, ensure_ascii=False)
        print("✅ Bible index saved!")
    except Exception as e:
        print(f"❌ Error saving Bible index: {e}")


def save_trivia_bank():
    """Saves each trivia category to its own file in TRIVIA_QUESTIONS_DIR."""
    try:
        os.makedirs(TRIVIA_QUESTIONS_DIR, exist_ok=True)
        for category, subcategories in trivia_questions.items():
            path = os.path.join(TRIVIA_QUESTIONS_DIR, f"{category}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(subcategories, f, indent=4, ensure_ascii=False)
        print("✅ Trivia Bank saved!")
    except Exception as e:
        print(f"❌ Error saving trivia bank: {e}")


def save_lottery():
    """Saves lottery state to JSON file."""
    global lottery_pot, lottery_entries, lottery_active
    try:
        with open(LOTTERY_FILE, "w", encoding="utf-8") as f:
            json.dump({"pot": lottery_pot, "entries": lottery_entries, "active": lottery_active}, f, indent=4)
        print("✅ Lottery state saved!")
    except Exception as e:
        print(f"❌ Error saving lottery state: {e}")


def load_lottery():
    """Loads lottery state from JSON file."""
    global lottery_pot, lottery_entries, lottery_active
    if os.path.exists(LOTTERY_FILE):
        try:
            with open(LOTTERY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            pot = data.get("pot", {})
            entries = data.get("entries", {})
            # Migrate old flat format: {"pot": float, "entries": {user_id: count}}
            if isinstance(pot, (int, float)):
                lottery_pot = {LEGACY_GUILD_ID: float(pot)}
                lottery_entries = {LEGACY_GUILD_ID: entries} if isinstance(entries, dict) else {}
                print(f"⚠️ Old lottery format detected — migrated to guild {LEGACY_GUILD_ID}.")
            else:
                lottery_pot = pot
                lottery_entries = entries
            lottery_active = data.get("active", {})
            print(f"✅ Lottery loaded — {len(lottery_pot)} server(s)")
        except Exception as e:
            print(f"❌ Error loading lottery state: {e}")
            lottery_pot = {}
            lottery_entries = {}
            lottery_active = {}
    else:
        lottery_pot = {}
        lottery_entries = {}
        lottery_active = {}


def get_lottery_active(guild_id):
    """Returns the active lottery config for a guild, or None if none is running."""
    return lottery_active.get(str(guild_id))


def get_jackpot(guild_id):
    return jackpot_pot.get(str(guild_id), 0.0)


def add_to_jackpot(guild_id, amount):
    gid = str(guild_id)
    jackpot_pot[gid] = jackpot_pot.get(gid, 0.0) + float(amount)


def reset_jackpot(guild_id):
    jackpot_pot[str(guild_id)] = 0.0


def set_jackpot(guild_id, amount):
    jackpot_pot[str(guild_id)] = float(amount)


def save_jackpot():
    """Saves jackpot state to JSON file."""
    try:
        with open(JACKPOT_FILE, "w", encoding="utf-8") as f:
            json.dump(jackpot_pot, f, indent=4)
        print("✅ Jackpot state saved!")
    except Exception as e:
        print(f"❌ Error saving jackpot state: {e}")


def load_jackpot():
    """Loads jackpot state from JSON file."""
    global jackpot_pot
    if os.path.exists(JACKPOT_FILE):
        try:
            with open(JACKPOT_FILE, "r", encoding="utf-8") as f:
                jackpot_pot = json.load(f)
            print(f"✅ Jackpot loaded — {len(jackpot_pot)} server(s)")
        except Exception as e:
            print(f"❌ Error loading jackpot state: {e}")
            jackpot_pot = {}
    else:
        jackpot_pot = {}


def save_all():
    """Saves all bot configuration data."""
    save_quotes()
    save_gifs()
    save_gif_messages()
    save_eight_ball()
    save_verses()
    save_trivia_bank()
    save_bible_index()
    save_lottery()
    save_jackpot()


def load_bible_index():
    """
    Loads the Bible index from Saves/bible_index.json into memory.

    Expected file format:
    {
        "KJV": {
            "Genesis": {
                "1": {
                    "1": "In the beginning God created the heaven and the earth."
                }
            }
        }
    }
    """
    global bible_index
    if os.path.exists(BIBLE_INDEX_FILE):
        try:
            with open(BIBLE_INDEX_FILE, "r", encoding="utf-8") as f:
                bible_index = json.load(f)
            total_verses = sum(
                len(verses_dict)
                for version_data in bible_index.values()
                for book_data in version_data.values()
                for verses_dict in book_data.values()
            )
            print(f"✅ Bible index loaded — {len(bible_index)} version(s), ~{total_verses:,} verses.")
        except Exception as e:
            print(f"❌ Error loading Bible index: {e}")
            bible_index = {}
    else:
        bible_index = {}
        print("⚠️  No Bible index file found at Saves/bible_index.json. Bible lookup commands will be unavailable.")


def load_all():
    """Loads all data from files. Returns defaults if files don't exist."""
    global quotes, gifs, gif_messages, magic_eight_ball, verses, trivia_questions
    load_lottery()
    load_jackpot()

    # Load quotes
    quotes_data = {}
    if os.path.exists(QUOTES_FILE):
        with open(QUOTES_FILE, "r") as f:
            quotes_data = json.load(f)

    # Migrate old format {author: [Quote]} → {guild_id: {author: [Quote]}}
    if quotes_data and any(isinstance(v, list) for v in quotes_data.values()):
        quotes_data = {LEGACY_GUILD_ID: quotes_data}

    for guild_id, author_dict in quotes_data.items():
        if guild_id not in quotes:
            quotes[guild_id] = {}
        for author, quote_list in author_dict.items():
            if author not in quotes[guild_id]:
                quotes[guild_id][author] = []
            for quote_dict in quote_list:
                quote_object = Quote(quote_dict['text'], quote_dict['author'])
                quote_object.set_tags(quote_dict.get('tags', []))
                quotes[guild_id][author].append(quote_object)


    # Load gifs
    if os.path.exists(GIFS_FILE):
        with open(GIFS_FILE, "r") as f:
            gifs = json.load(f)
    else:
        gifs = {}

    # Load gif messages
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r") as f:
            gif_messages = json.load(f)
    else:
        gif_messages = {}

    if os.path.exists(MAGIC_EIGHT_BALL_FILE):
        with open(MAGIC_EIGHT_BALL_FILE, "r", encoding="utf-8") as f:
            magic_eight_ball = json.load(f)
    else:
        magic_eight_ball = []

    trivia_questions = {}
    if os.path.isdir(TRIVIA_QUESTIONS_DIR):
        for fname in os.listdir(TRIVIA_QUESTIONS_DIR):
            if fname.endswith(".json"):
                category = fname[:-5]
                with open(os.path.join(TRIVIA_QUESTIONS_DIR, fname), "r", encoding="utf-8") as f:
                    trivia_questions[category] = json.load(f)

    load_bible_index()

    print(
        f"✅ Loaded {len(quotes)} quote authors, "
        f"{len(gifs)} gif categories, "
        f"{len(gif_messages)} message categories, "
        f"{len(magic_eight_ball)} eight ball responses, "
        f"{len(trivia_questions)} trivia categories."
    )


def save_user_data():
    try:
        data_to_save = {}

        for user_id, user in user_data.items():
            data_to_save[user_id] = user.to_dict()

        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data_to_save, file, indent=4, ensure_ascii=False)

        print(f"Successfully saved {len(user_data)} users to {DATA_FILE}")
        return True
    except Exception as e:
        print(f"Error saving user data: {e}")
        return False


def _migrate_legacy_user_record(user_dict):
    """If a user record is in the old flat format (no guild_data), relocate
    all per-guild fields under LEGACY_GUILD_ID. Mutates and returns user_dict.
    """
    # Legacy warnings: list → guild-keyed dict
    raw_warnings = user_dict.get("warnings", {})
    if isinstance(raw_warnings, list):
        user_dict["warnings"] = {LEGACY_GUILD_ID: raw_warnings} if raw_warnings else {}

    if "guild_data" in user_dict:
        return user_dict  # already new format

    from Classes.UserSavesClass import LEGACY_GUILD_FIELDS
    legacy_state = {}
    for field in LEGACY_GUILD_FIELDS:
        if field in user_dict:
            legacy_state[field] = user_dict.pop(field)

    user_dict["guild_data"] = {LEGACY_GUILD_ID: legacy_state} if legacy_state else {}
    return user_dict


def load_user_data():
    global user_data
    local_user_data = {}

    try:
        with open(DATA_FILE, "r") as file:
            loaded_data = json.load(file)

        migrated = 0
        for user_id, user_dict in loaded_data.items():
            had_guild_data = "guild_data" in user_dict
            user_dict = _migrate_legacy_user_record(user_dict)
            if not had_guild_data:
                migrated += 1
            local_user_data[user_id] = User.from_dict(user_dict)

        if migrated:
            print(f"⚠️ Migrated {migrated} user(s) from legacy flat format → guild_data[{LEGACY_GUILD_ID}].")
        print(f"Successfully loaded {len(local_user_data)} users from {DATA_FILE}")
        user_data = local_user_data

    except Exception as e:
        print(f"Error loading user data: {e}")
        user_data = local_user_data

