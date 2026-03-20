class DndCharacter:
    SKILL_STAT_MAP = {
        "acrobatics": "dexterity",
        "animal_handling": "wisdom",
        "arcana": "intelligence",
        "athletics": "strength",
        "deception": "charisma",
        "history": "intelligence",
        "insight": "wisdom",
        "intimidation": "charisma",
        "investigation": "intelligence",
        "medicine": "wisdom",
        "nature": "intelligence",
        "perception": "wisdom",
        "performance": "charisma",
        "persuasion": "charisma",
        "religion": "intelligence",
        "sleight_of_hand": "dexterity",
        "stealth": "dexterity",
        "survival": "wisdom"
    }

    def __init__(self, character_class: str, name: str = "New Character", level: int = 1):
        # Core Identity
        self.character_class = character_class
        self.name = name
        self.level = level

        # Ability Scores
        self.strength = 10
        self.dexterity = 10
        self.constitution = 10
        self.intelligence = 10
        self.wisdom = 10
        self.charisma = 10

        # Save Proficiencies (True/False)
        self.strength_save_proficiency = False
        self.dexterity_save_proficiency = False
        self.constitution_save_proficiency = False
        self.intelligence_save_proficiency = False
        self.wisdom_save_proficiency = False
        self.charisma_save_proficiency = False

        # Skills: 0 = none, 0.5 = half, 1 = proficiency, 2 = expertise
        self.acrobatics = 0
        self.animal_handling = 0
        self.arcana = 0
        self.athletics = 0
        self.deception = 0
        self.history = 0
        self.insight = 0
        self.intimidation = 0
        self.investigation = 0
        self.medicine = 0
        self.nature = 0
        self.perception = 0
        self.performance = 0
        self.persuasion = 0
        self.religion = 0
        self.sleight_of_hand = 0
        self.stealth = 0
        self.survival = 0

        # Combat Stats
        self.max_hp = 10
        self.current_hp = 10
        self.armor_class = 10
        self.speed = 30
        self.initiative_bonus = 0

        # Inventory & Resources
        self.gold = 0
        self.inventory = []

    def get_name(self):
        return self.name

    def get_class(self):
        return self.character_class

    def get_level(self):
        return self.level

    # --- Modifier Calculations ---
    def get_proficiency_bonus(self):
        """Proficiency bonus scales with level."""
        return (self.level - 1) // 4 + 2

    def get_stat_modifier(self, stat_name: str):
        """Calculates modifier from a stat score."""
        stat_value = getattr(self, stat_name.lower(), 10)
        return (stat_value - 10) // 2

    def get_skill_bonus(self, skill_name: str, stat_name: str):
        """Calculates total skill bonus including proficiency."""
        modifier = self.get_stat_modifier(stat_name)
        proficiency_level = getattr(self, skill_name.lower(), 0)
        proficiency_bonus = int(self.get_proficiency_bonus() * proficiency_level)
        return modifier + proficiency_bonus

    def get_save_bonus(self, stat_name: str):
        """Calculates saving throw bonus."""
        modifier = self.get_stat_modifier(stat_name)
        save_prof_attr = f"{stat_name.lower()}_save_proficiency"
        is_proficient = getattr(self, save_prof_attr, False)
        if is_proficient:
            return modifier + self.get_proficiency_bonus()
        return modifier

    # --- Combat Methods ---
    def take_damage(self, amount: int):
        self.current_hp = max(0, self.current_hp - amount)
        return self.current_hp

    def heal(self, amount: int):
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp

    def is_alive(self):
        return self.current_hp > 0

    # --- Inventory Methods ---
    def add_item(self, item: str):
        self.inventory.append(item)

    def remove_item(self, item: str):
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False

    def add_gold(self, amount: int):
        self.gold += amount

    def spend_gold(self, amount: int):
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False

    # --- Serialization ---
    def to_dict(self):
        return {
            "name": self.name,
            "character_class": self.character_class,
            "level": self.level,
            "stats": {
                "strength": self.strength,
                "dexterity": self.dexterity,
                "constitution": self.constitution,
                "intelligence": self.intelligence,
                "wisdom": self.wisdom,
                "charisma": self.charisma
            },
            "saves": {
                "strength": self.strength_save_proficiency,
                "dexterity": self.dexterity_save_proficiency,
                "constitution": self.constitution_save_proficiency,
                "intelligence": self.intelligence_save_proficiency,
                "wisdom": self.wisdom_save_proficiency,
                "charisma": self.charisma_save_proficiency
            },
            "skills": {
                "acrobatics": self.acrobatics,
                "animal_handling": self.animal_handling,
                "arcana": self.arcana,
                "athletics": self.athletics,
                "deception": self.deception,
                "history": self.history,
                "insight": self.insight,
                "intimidation": self.intimidation,
                "investigation": self.investigation,
                "medicine": self.medicine,
                "nature": self.nature,
                "perception": self.perception,
                "performance": self.performance,
                "persuasion": self.persuasion,
                "religion": self.religion,
                "sleight_of_hand": self.sleight_of_hand,
                "stealth": self.stealth,
                "survival": self.survival
            },
            "combat": {
                "max_hp": self.max_hp,
                "current_hp": self.current_hp,
                "armor_class": self.armor_class,
                "speed": self.speed,
                "initiative_bonus": self.initiative_bonus
            },
            "gold": self.gold,
            "inventory": self.inventory
        }

    @classmethod
    def from_dict(cls, data: dict):
        char = cls(
            character_class=data.get("character_class", "Fighter"),
            name=data.get("name", "New Character"),
            level=data.get("level", 1)
        )

        # Load stats
        stats = data.get("stats", {})
        char.strength = stats.get("strength", 10)
        char.dexterity = stats.get("dexterity", 10)
        char.constitution = stats.get("constitution", 10)
        char.intelligence = stats.get("intelligence", 10)
        char.wisdom = stats.get("wisdom", 10)
        char.charisma = stats.get("charisma", 10)

        # Load saves
        saves = data.get("saves", {})
        char.strength_save_proficiency = saves.get("strength", False)
        char.dexterity_save_proficiency = saves.get("dexterity", False)
        char.constitution_save_proficiency = saves.get("constitution", False)
        char.intelligence_save_proficiency = saves.get("intelligence", False)
        char.wisdom_save_proficiency = saves.get("wisdom", False)
        char.charisma_save_proficiency = saves.get("charisma", False)

        # Load skills
        skills = data.get("skills", {})
        char.acrobatics = skills.get("acrobatics", 0)
        char.animal_handling = skills.get("animal_handling", 0)
        char.arcana = skills.get("arcana", 0)
        char.athletics = skills.get("athletics", 0)
        char.deception = skills.get("deception", 0)
        char.history = skills.get("history", 0)
        char.insight = skills.get("insight", 0)
        char.intimidation = skills.get("intimidation", 0)
        char.investigation = skills.get("investigation", 0)
        char.medicine = skills.get("medicine", 0)
        char.nature = skills.get("nature", 0)
        char.perception = skills.get("perception", 0)
        char.performance = skills.get("performance", 0)
        char.persuasion = skills.get("persuasion", 0)
        char.religion = skills.get("religion", 0)
        char.sleight_of_hand = skills.get("sleight_of_hand", 0)
        char.stealth = skills.get("stealth", 0)
        char.survival = skills.get("survival", 0)

        # Load combat
        combat = data.get("combat", {})
        char.max_hp = combat.get("max_hp", 10)
        char.current_hp = combat.get("current_hp", 10)
        char.armor_class = combat.get("armor_class", 10)
        char.speed = combat.get("speed", 30)
        char.initiative_bonus = combat.get("initiative_bonus", 0)

        char.gold = data.get("gold", 0)
        char.inventory = data.get("inventory", [])

        return char