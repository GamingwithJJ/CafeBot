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
QUOTE_USERS_FILE = "Saves/QuoteUsers.json"
VERSES_FILE = "Saves/verses.json"
TRIVIA_QUESTIONS_FILE = "Saves/trivia_questions.json"

# Format: { "category_name": { "sub_category_name": [ ("Question", ["answer1", "answer2"]) ] } }
trivia_questions = {}

verses = []

administrators = []


magic_eight_ball = []

quote_users = []
# Users who are valid quote users

#quotes = []
quotes = {} #Keys are names of quoters


gifs = {}


gif_messages = {}

"""
Checks if a user with a specified discord id exists and creats one if it does not.
"""


def get_or_create_user(user_id):
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        user_data[user_id_str] = User(user_id_str)
    return user_data[user_id_str]


def save_eight_ball():
    """Saves magic eight ball responses to JSON file."""
    try:
        with open(MAGIC_EIGHT_BALL_FILE, "w", encoding="utf-8") as f:
            json.dump(magic_eight_ball, f, indent=4, ensure_ascii=False)
        print("✅Eight ball responses saved!")
    except Exception as e:
        print(f"❌ Error saving eight ball responses: {e}")


def save_quote_users():
    """Saves quote_users to JSON file"""
    try:
        with open(QUOTE_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(quote_users, f, indent=4)
        print("✅ Quote users saved!")
    except Exception as e:
        print(f"Error saving quote users!")


def save_quotes():
    """Saves quotes to JSON file."""
    data_to_save = {}

    for quoter, quote_list in quotes.items():
        data_to_save[quoter] = [q.to_dict() for q in quote_list]

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


def save_trivia_bank():
    """Saves the trivia dictionary to the JSON file."""
    try:
        with open(TRIVIA_QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(trivia_questions, f, indent=4)
        print("✅ Trivia Bank saved!")
    except Exception as e:
        print(f"❌ Error saving trivia bank: {e}")


def save_all():
    """Saves all bot configuration data."""
    save_quotes()
    save_gifs()
    save_gif_messages()
    save_eight_ball()
    save_quote_users()
    save_verses()
    save_trivia_bank()


def load_all():
    """Loads all data from files. Returns defaults if files don't exist."""
    global quotes, gifs, gif_messages, magic_eight_ball, quote_users, verses, trivia_questions

    # Load quotes
    quotes_data = {}
    if os.path.exists(QUOTES_FILE):
        with open(QUOTES_FILE, "r") as f:
            quotes_data = json.load(f)

    for quoter, quote_list in quotes_data.items():

        if quoter not in quotes:
            quotes[quoter] = []

        for quote_dict in quote_list:
            quote_object = Quote(quote_dict['text'], quote_dict['author'])
            quote_object.set_tags(quote_dict.get('tags', []))
            quotes[quoter].append(quote_object)

    # Load quote users
    if os.path.exists(QUOTE_USERS_FILE):
        with open(QUOTE_USERS_FILE, "r") as f:
            quote_users = json.load(f)
    else:
        quote_users = []

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

    # Load verses
    if os.path.exists(VERSES_FILE):
        with open(VERSES_FILE, "r", encoding="utf-8") as f:
            verses_data = json.load(f)
            for verse_dict in verses_data:
                verses.append(Verse(verse_dict["text"], verse_dict["reference"]))
    else:
        verses = []

    if os.path.exists(TRIVIA_QUESTIONS_FILE):
        with open(TRIVIA_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            trivia_questions = json.load(f)
    else:
        trivia_questions = {}

    print(
        f"✅ Loaded {len(quotes)} quote authors, "
        f"{len(quote_users)} quote users, "
        f"{len(gifs)} gif categories, "
        f"{len(gif_messages)} message categories, "
        f"{len(magic_eight_ball)} eight ball responses, "
        f"{len(verses)} verses, and "
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
            user.marriage_partner = user_dict.get("marriage_partner", None)
            user.beans = user_dict.get("beans", 0)
            last_shift_string = user_dict.get("last_shift")
            user.last_shift = datetime.datetime.fromisoformat(last_shift_string) if last_shift_string else None
            partner_gained_date_string = user_dict.get("partner_gained_date")
            user.partner_gained_date = datetime.datetime.fromisoformat(partner_gained_date_string) if partner_gained_date_string else None
            last_daily_string = user_dict.get("last_daily")
            user.last_daily = datetime.datetime.fromisoformat(last_daily_string) if last_daily_string else None
            user.daily_reward_streak = user_dict.get("daily_reward_streak", 0)
            user.enabled_trivia_categories = user_dict.get("enabled_trivia_categories")

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

