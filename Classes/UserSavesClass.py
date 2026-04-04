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
            "marriage": []
        }
        self.marriage_partner = None
        self.partner_gained_date = None
        self.beans = 0.0
        self.last_shift = None
        self.last_daily = None
        self.daily_reward_streak = 0

        #Trivia
        self.enabled_trivia_categories = []

    def set_marriage_partner(self, new_partner: int):
        self.marriage_partner = new_partner
        self.partner_gained_date = datetime.datetime.now()

    def get_marriage_partner(self):
        return self.marriage_partner

    def get_partner_gained_date(self):
        return self.partner_gained_date

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

    def get_beans(self):
        return self.beans

    def set_beans(self, beans: float):
        self.beans = beans

    def ajust_beans(self, amount: float):
        self.beans += amount

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
            "beans": self.beans,
            "last_shift": self.last_shift.isoformat() if self.last_shift else None,
            "partner_gained_date": self.partner_gained_date.isoformat() if self.partner_gained_date else None,
            "last_daily": self.last_daily.isoformat() if self.last_daily else None,
            "daily_reward_streak": self.daily_reward_streak,
            "enabled_trivia_categories" : self.enabled_trivia_categories
        }

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)
