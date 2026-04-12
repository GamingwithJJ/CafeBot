from Classes.RequestClass import Request
import json
from Classes.DndCharacter import DndCharacter
import datetime


class User:
    discord_id = ""
    characters = []
    requests = {
        "marriage": []
    } # Key is string request type, list contains a list of RequestClasses
    marriage_partner = None  # ID of another discord user
    partner_gained_date = None # Date the partnership started
    beans = 0.0 # Money for the economy
    last_shift = None # Stores the last time the user worked a shift
    last_daily = None # Stores the last time the user did their daily
    daily_reward_streak = 0 # Streak of rewards

    def __init__(self, discord_id: str):
        self.discord_id = discord_id
        self.characters = []
        self.requests = {
            "marriage": [],
            "adoption": []
        }
        self.marriage_partner = []        # list of int Discord IDs
        self.partner_gained_date = {}     # dict: partner_id (int) → datetime
        self.beans = 0.0
        self.last_shift = None
        self.last_daily = None
        self.daily_reward_streak = 0
        self.total_marriages = 0
        self.total_divorces = 0

        # Adoption
        self.adopted_children = []  # List of int Discord IDs
        self.adopted_by = []  # List of int Discord IDs (parents)

        #Trivia
        self.enabled_trivia_categories = []
        self.trivia_correct = 0

        # Faith
        self.bookmarked_verses = []  # List of [version, book, chapter, verse_num]

        # Moderation
        self.warnings = []  # List of {"reason": str, "issued_by": str, "timestamp": str}

    def add_adopted_child(self, child_id: int):
        self.adopted_children.append(child_id)

    def remove_adopted_child(self, child_id: int):
        if child_id in self.adopted_children:
            self.adopted_children.remove(child_id)

    def get_adopted_children(self):
        return self.adopted_children

    def add_adopted_parent(self, parent_id: int):
        if parent_id not in self.adopted_by:
            self.adopted_by.append(parent_id)

    def remove_adopted_parent(self, parent_id: int):
        if parent_id in self.adopted_by:
            self.adopted_by.remove(parent_id)

    def get_adopted_by(self):
        return self.adopted_by

    def add_marriage_partner(self, partner_id: int):
        if partner_id not in self.marriage_partner:
            self.marriage_partner.append(partner_id)
            self.partner_gained_date[partner_id] = datetime.datetime.now()
            self.total_marriages += 1

    def remove_marriage_partner(self, partner_id: int):
        if partner_id in self.marriage_partner:
            self.marriage_partner.remove(partner_id)
            self.partner_gained_date.pop(partner_id, None)
            self.total_divorces += 1

    def get_marriage_partners(self):
        return self.marriage_partner

    def get_partner_gained_date(self, partner_id: int):
        return self.partner_gained_date.get(partner_id)

    def add_request(self, type, request: Request):
        self.requests[type].append(request)

    def get_request(self, request_type: str, user_sent: int):
        if request_type not in self.requests:
            print(f"Error: Request type '{request_type}' not found")
            return None

        user_sent_str = str(user_sent)

        for request in self.requests[request_type]:
            request_user = str(request.get_user())
            if request_user == user_sent_str:  # Compare the ID inside the object
                return request

        print(f"Error: User ID {user_sent} not found")
        return None

    def remove_request(self, request_input: Request): # Returns true if successful or false if not
        request_type = request_input.get_type()
        if request_type not in self.requests:
            return False

        request_type_list = self.requests[request_type] # Gets a list of the requests of the specified type
        for request in request_type_list:
            if request.equal_request(request_input.get_type() ,request_input.get_user()):
                self.requests[request_type].remove(request)
                return True
        return False

    def remove_request_by_data(self, request_type: str, user_sent: int): # Returns true if successful or false if not, uses remove_request
        request = Request(request_type, user_sent)
        result = self.remove_request(request)
        return result

    def get_character(self, character_name: str):
        """ Gets a character by its name, returning None if none is found."""
        for character in self.characters:
            if character.get_name() == character_name:
                return character
        return None

    def add_character(self, character: DndCharacter):
        """Adds a character to be saved, returning false if the character already exists"""
        if self.get_character(character.get_name()) is not None:
            return False
        self.characters.append(character)
        return True

    def view_characters(self):
        if not self.characters:
            return "You don't have any characters yet! Use `.create_character` to make one."

        return_string = ""
        for character in self.characters:
            return_string += f"Name: {character.get_name()}, Class: {character.get_class()}, Level: {character.get_level()} \n"
        return return_string

    def add_verse_bookmark(self, version: str, book: str, chapter: str, verse_num: str):
        self.bookmarked_verses.append([version, book, chapter, verse_num])

    def get_verse_bookmarks(self):
        return self.bookmarked_verses

    def add_warning(self, reason: str, issued_by: str, timestamp: str):
        self.warnings.append({"reason": reason, "issued_by": issued_by, "timestamp": timestamp})

    def get_warnings(self):
        return self.warnings

    def get_beans(self):
        return self.beans

    def set_beans(self, beans: float):
        self.beans = beans

    def ajust_beans(self, amount: float):
        self.beans = round(self.beans + amount, 2)

    def set_last_shift(self, time: datetime.datetime):
        self.last_shift = time

    def to_dict(self):
        return {
            "discord_id": self.discord_id,
            "characters": [
                char.to_dict() if hasattr(char, 'to_dict') else char
                for char in self.characters
            ],
            "requests": {
                req_type: [r.to_dict() for r in req_list]
                for req_type, req_list in self.requests.items()
            },
            "marriage_partner": self.marriage_partner,
            "partner_gained_date": {
                str(pid): dt.isoformat()
                for pid, dt in self.partner_gained_date.items()
            },
            "adopted_children": self.adopted_children,
            "adopted_by": self.adopted_by,
            "beans": self.beans,
            "last_shift": self.last_shift.isoformat() if self.last_shift else None,
            "last_daily": self.last_daily.isoformat() if self.last_daily else None,
            "daily_reward_streak": self.daily_reward_streak,
            "total_marriages": self.total_marriages,
            "total_divorces": self.total_divorces,
            "enabled_trivia_categories" : self.enabled_trivia_categories,
            "trivia_correct": self.trivia_correct,
            "bookmarked_verses": self.bookmarked_verses,
            "warnings": self.warnings
        }

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)
