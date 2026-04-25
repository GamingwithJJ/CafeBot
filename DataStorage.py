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


def load_user_data():
    global user_data
    local_user_data = {}

    try:
        with open(DATA_FILE, "r") as file:
            loaded_data = json.load(file)

        for user_id, user_dict in loaded_data.items():
            user = User(user_dict["discord_id"])
            raw_mp = user_dict.get("marriage_partner", [])
            if raw_mp is None:
                user.marriage_partner = []
            elif isinstance(raw_mp, int):
                user.marriage_partner = [raw_mp]
            else:
                user.marriage_partner = raw_mp

            raw_pgd = user_dict.get("partner_gained_date", {})
            if raw_pgd is None:
                user.partner_gained_date = {}
            elif isinstance(raw_pgd, str):
                dt = datetime.datetime.fromisoformat(raw_pgd)
                user.partner_gained_date = {user.marriage_partner[0]: dt} if user.marriage_partner else {}
            elif isinstance(raw_pgd, dict):
                user.partner_gained_date = {
                    int(k): datetime.datetime.fromisoformat(v)
                    for k, v in raw_pgd.items()
                }
            else:
                user.partner_gained_date = {}

            user.beans = user_dict.get("beans", 0)
            last_shift_string = user_dict.get("last_shift")
            user.last_shift = datetime.datetime.fromisoformat(last_shift_string) if last_shift_string else None
            last_daily_string = user_dict.get("last_daily")
            user.last_daily = datetime.datetime.fromisoformat(last_daily_string) if last_daily_string else None
            user.daily_reward_streak = user_dict.get("daily_reward_streak", 0)
            user.total_marriages = user_dict.get("total_marriages", 0)
            user.total_divorces = user_dict.get("total_divorces", 0)
            user.enabled_trivia_categories = user_dict.get("enabled_trivia_categories", [])
            user.trivia_correct = user_dict.get("trivia_correct", 0)
            user.bookmarked_verses = user_dict.get("bookmarked_verses", [])
            raw_warnings = user_dict.get("warnings", {})
            if isinstance(raw_warnings, list):
                user.warnings = {LEGACY_GUILD_ID: raw_warnings} if raw_warnings else {}
            else:
                user.warnings = raw_warnings
            user.bank_balance = user_dict.get("bank_balance", 0.0)
            user.bank_level = user_dict.get("bank_level", 0)
            last_rob_str = user_dict.get("last_rob")
            user.last_rob = datetime.datetime.fromisoformat(last_rob_str) if last_rob_str else None
            rob_immunity_str = user_dict.get("rob_immunity_until")
            user.rob_immunity_until = datetime.datetime.fromisoformat(rob_immunity_str) if rob_immunity_str else None
            user.adopted_children = user_dict.get("adopted_children", [])
            raw_adopted_by = user_dict.get("adopted_by", [])
            if raw_adopted_by is None:
                user.adopted_by = []
            elif isinstance(raw_adopted_by, int):
                user.adopted_by = [raw_adopted_by]  # migrate old single-value saves
            else:
                user.adopted_by = raw_adopted_by

            # Rebuild DndCharacter objects
            for char_data in user_dict.get("characters", []):
                character = DndCharacter.from_dict(char_data)
                user.characters.append(character)

            # Rebuild Request objects
            for request_type, request_list in user_dict.get("requests", {}).items():
                user.requests[request_type] = []
                for request_data in request_list:
                    request = Request(
                        request_data["request_type"],
                        request_data["user_id"]
                    )
                    user.requests[request_type].append(request)

            local_user_data[user_id] = user

        print(f"Successfully loaded {len(local_user_data)} users from {DATA_FILE}")
        user_data = local_user_data

    except Exception as e:
        print(f"Error loading user data: {e}")
        user_data = local_user_data

