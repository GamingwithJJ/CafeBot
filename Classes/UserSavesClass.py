from Classes.RequestClass import Request
import json
from Classes.DndCharacter import DndCharacter
import datetime


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    return datetime.datetime.fromisoformat(value)


class GuildState:
    """All user data scoped to a single guild."""

    def __init__(self):
        # Economy
        self.beans = 0.0
        self.bank_balance = 0.0
        self.bank_level = 0
        # Cooldowns
        self.last_shift = None
        self.last_daily = None
        self.daily_reward_streak = 0
        self.last_rob = None
        self.rob_immunity_until = None
        # Stats
        self.trivia_correct = 0
        self.total_marriages = 0
        self.total_divorces = 0
        # Relationships
        self.marriage_partner = []          # list[int Discord IDs]
        self.partner_gained_date = {}       # {partner_id (int) → datetime}
        self.adopted_children = []          # list[int]
        self.adopted_by = []                # list[int]
        # Pending proposals — scoped to this guild
        self.requests = {"marriage": [], "adoption": [], "bet": []}
        # Active bets (post-acceptance) — mirrored to both players' state
        self.active_bets = {}    # {"<lo_id>:<hi_id>": {"amount": int, "votes": {str(player_id): int(winner_id)}}}

    def to_dict(self):
        return {
            "beans": self.beans,
            "bank_balance": self.bank_balance,
            "bank_level": self.bank_level,
            "last_shift": self.last_shift.isoformat() if self.last_shift else None,
            "last_daily": self.last_daily.isoformat() if self.last_daily else None,
            "daily_reward_streak": self.daily_reward_streak,
            "last_rob": self.last_rob.isoformat() if self.last_rob else None,
            "rob_immunity_until": self.rob_immunity_until.isoformat() if self.rob_immunity_until else None,
            "trivia_correct": self.trivia_correct,
            "total_marriages": self.total_marriages,
            "total_divorces": self.total_divorces,
            "marriage_partner": list(self.marriage_partner),
            "partner_gained_date": {
                str(pid): dt.isoformat() for pid, dt in self.partner_gained_date.items()
            },
            "adopted_children": list(self.adopted_children),
            "adopted_by": list(self.adopted_by),
            "requests": {
                req_type: [r.to_dict() for r in req_list]
                for req_type, req_list in self.requests.items()
            },
            "active_bets": {
                k: {
                    "amount": int(v["amount"]),
                    "votes": {str(pid): int(wid) for pid, wid in v["votes"].items()},
                    **({"reason": v["reason"]} if v.get("reason") else {}),
                }
                for k, v in self.active_bets.items()
            },
        }

    @classmethod
    def from_dict(cls, data):
        gs = cls()
        gs.beans = float(data.get("beans", 0.0))
        gs.bank_balance = float(data.get("bank_balance", 0.0))
        gs.bank_level = int(data.get("bank_level", 0))
        gs.last_shift = _parse_dt(data.get("last_shift"))
        gs.last_daily = _parse_dt(data.get("last_daily"))
        gs.daily_reward_streak = int(data.get("daily_reward_streak", 0))
        gs.last_rob = _parse_dt(data.get("last_rob"))
        gs.rob_immunity_until = _parse_dt(data.get("rob_immunity_until"))
        gs.trivia_correct = int(data.get("trivia_correct", 0))
        gs.total_marriages = int(data.get("total_marriages", 0))
        gs.total_divorces = int(data.get("total_divorces", 0))

        # marriage_partner: handle scalar→list legacy shim
        mp = data.get("marriage_partner", [])
        if isinstance(mp, list):
            gs.marriage_partner = list(mp)
        elif mp is not None:
            gs.marriage_partner = [mp]
        else:
            gs.marriage_partner = []

        # partner_gained_date: handle scalar→dict legacy shim
        pgd = data.get("partner_gained_date", {})
        if isinstance(pgd, dict):
            gs.partner_gained_date = {
                int(pid): _parse_dt(dt) for pid, dt in pgd.items() if dt
            }
        elif pgd is not None and gs.marriage_partner:
            # legacy single-date scalar — attribute to first partner
            gs.partner_gained_date = {gs.marriage_partner[0]: _parse_dt(pgd)}
        else:
            gs.partner_gained_date = {}

        gs.adopted_children = list(data.get("adopted_children", []))

        # adopted_by: scalar→list legacy shim
        ab = data.get("adopted_by", [])
        if isinstance(ab, list):
            gs.adopted_by = list(ab)
        elif ab is not None:
            gs.adopted_by = [ab]
        else:
            gs.adopted_by = []

        # requests
        req_data = data.get("requests", {"marriage": [], "adoption": [], "bet": []})
        gs.requests = {"marriage": [], "adoption": [], "bet": []}
        for req_type, req_list in req_data.items():
            gs.requests.setdefault(req_type, [])
            for r in req_list:
                gs.requests[req_type].append(Request(
                    r.get("request_type", req_type),
                    r.get("user_id"),
                    amount=r.get("amount"),
                    reason=r.get("reason"),
                ))

        # active bets
        gs.active_bets = {}
        for k, v in data.get("active_bets", {}).items():
            gs.active_bets[k] = {
                "amount": int(v.get("amount", 0)),
                "votes": {str(pid): int(wid) for pid, wid in v.get("votes", {}).items()},
                "reason": v.get("reason"),
            }
        return gs


# Fields that lived at the top of a user record before the per-guild refactor.
# Used by the migration shim in DataStorage to detect and relocate legacy data.
LEGACY_GUILD_FIELDS = (
    "beans", "bank_balance", "bank_level", "last_shift", "last_daily",
    "daily_reward_streak", "last_rob", "rob_immunity_until",
    "trivia_correct", "total_marriages", "total_divorces",
    "marriage_partner", "partner_gained_date",
    "adopted_children", "adopted_by", "requests",
)


class User:
    def __init__(self, discord_id: str):
        self.discord_id = discord_id

        # GLOBAL personal data
        self.characters = []
        self.enabled_trivia_categories = []
        self.bookmarked_verses = []
        self.warnings = {}  # {guild_id_str: [{"reason", "issued_by", "timestamp"}]}
        self.default_dm_guild_id = None  # Optional[str] — set by .dm_server picker

        # PER-GUILD data
        self.guild_data = {}  # {guild_id_str: GuildState}

    # -------- per-guild accessor --------

    def state(self, guild_id) -> GuildState:
        """Get or create the GuildState for a guild."""
        gid = str(guild_id)
        if gid not in self.guild_data:
            self.guild_data[gid] = GuildState()
        return self.guild_data[gid]

    def effective_guild_id(self, ctx):
        """The guild id this command should act against — current guild if any, else the user's DM default."""
        if getattr(ctx, "guild", None) is not None:
            return str(ctx.guild.id)
        return self.default_dm_guild_id

    # -------- economy --------

    def get_beans(self, guild_id):
        return self.state(guild_id).beans

    def set_beans(self, guild_id, beans: float):
        self.state(guild_id).beans = beans

    def ajust_beans(self, guild_id, amount: float):
        gs = self.state(guild_id)
        gs.beans = round(gs.beans + amount, 2)

    def set_last_shift(self, guild_id, time: datetime.datetime):
        self.state(guild_id).last_shift = time

    # -------- relationships: marriage --------

    def add_marriage_partner(self, guild_id, partner_id: int):
        gs = self.state(guild_id)
        if partner_id not in gs.marriage_partner:
            gs.marriage_partner.append(partner_id)
            gs.partner_gained_date[partner_id] = datetime.datetime.now()
            gs.total_marriages += 1

    def remove_marriage_partner(self, guild_id, partner_id: int):
        gs = self.state(guild_id)
        if partner_id in gs.marriage_partner:
            gs.marriage_partner.remove(partner_id)
            gs.partner_gained_date.pop(partner_id, None)
            gs.total_divorces += 1

    def get_marriage_partners(self, guild_id):
        return self.state(guild_id).marriage_partner

    def get_partner_gained_date(self, guild_id, partner_id: int):
        return self.state(guild_id).partner_gained_date.get(partner_id)

    # -------- relationships: adoption --------

    def add_adopted_child(self, guild_id, child_id: int):
        gs = self.state(guild_id)
        if child_id not in gs.adopted_children:
            gs.adopted_children.append(child_id)

    def remove_adopted_child(self, guild_id, child_id: int):
        gs = self.state(guild_id)
        if child_id in gs.adopted_children:
            gs.adopted_children.remove(child_id)

    def get_adopted_children(self, guild_id):
        return self.state(guild_id).adopted_children

    def add_adopted_parent(self, guild_id, parent_id: int):
        gs = self.state(guild_id)
        if parent_id not in gs.adopted_by:
            gs.adopted_by.append(parent_id)

    def remove_adopted_parent(self, guild_id, parent_id: int):
        gs = self.state(guild_id)
        if parent_id in gs.adopted_by:
            gs.adopted_by.remove(parent_id)

    def get_adopted_by(self, guild_id):
        return self.state(guild_id).adopted_by

    # -------- requests (per-guild) --------

    def add_request(self, guild_id, type, request: Request):
        gs = self.state(guild_id)
        gs.requests.setdefault(type, []).append(request)

    def get_request(self, guild_id, request_type: str, user_sent: int):
        gs = self.state(guild_id)
        if request_type not in gs.requests:
            return None
        user_sent_str = str(user_sent)
        for request in gs.requests[request_type]:
            if str(request.get_user()) == user_sent_str:
                return request
        return None

    def remove_request(self, guild_id, request_input: Request):
        gs = self.state(guild_id)
        request_type = request_input.get_type()
        if request_type not in gs.requests:
            return False
        for request in gs.requests[request_type]:
            if request.equal_request(request_input.get_type(), request_input.get_user()):
                gs.requests[request_type].remove(request)
                return True
        return False

    def remove_request_by_data(self, guild_id, request_type: str, user_sent: int):
        return self.remove_request(guild_id, Request(request_type, user_sent))

    # -------- global: characters --------

    def get_character(self, character_name: str):
        for character in self.characters:
            if character.get_name() == character_name:
                return character
        return None

    def add_character(self, character: DndCharacter):
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

    # -------- global: bookmarks --------

    def add_verse_bookmark(self, version: str, book: str, chapter: str, verse_num: str):
        self.bookmarked_verses.append([version, book, chapter, verse_num])

    def get_verse_bookmarks(self):
        return self.bookmarked_verses

    # -------- global: warnings (already per-guild keyed) --------

    def add_warning(self, guild_id: str, reason: str, issued_by: str, timestamp: str):
        self.warnings.setdefault(str(guild_id), []).append({
            "reason": reason, "issued_by": issued_by, "timestamp": timestamp
        })

    def get_warnings(self, guild_id: str):
        return self.warnings.get(str(guild_id), [])

    # -------- serialization --------

    def to_dict(self):
        return {
            "discord_id": self.discord_id,
            "characters": [
                char.to_dict() if hasattr(char, "to_dict") else char
                for char in self.characters
            ],
            "enabled_trivia_categories": self.enabled_trivia_categories,
            "bookmarked_verses": self.bookmarked_verses,
            "warnings": self.warnings,
            "default_dm_guild_id": self.default_dm_guild_id,
            "guild_data": {
                gid: gs.to_dict() for gid, gs in self.guild_data.items()
            },
        }

    @classmethod
    def from_dict(cls, data):
        user = cls(data["discord_id"])

        # Characters
        for char_data in data.get("characters", []):
            if isinstance(char_data, dict):
                user.characters.append(DndCharacter.from_dict(char_data))
            else:
                user.characters.append(char_data)

        user.enabled_trivia_categories = list(data.get("enabled_trivia_categories", []))
        user.bookmarked_verses = list(data.get("bookmarked_verses", []))
        user.warnings = dict(data.get("warnings", {}))
        ddg = data.get("default_dm_guild_id")
        user.default_dm_guild_id = str(ddg) if ddg else None

        # Per-guild data
        for gid, gs_data in data.get("guild_data", {}).items():
            user.guild_data[str(gid)] = GuildState.from_dict(gs_data)

        return user

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)
