import random
import DataStorage
from DataStorage import get_or_create_user
from Classes.DndCharacter import DndCharacter


async def roll_dice(ctx, dice_type_and_amount: str, modifier):
    rolls_to_return = []

    dice_type_and_amount_list = dice_type_and_amount.lower().split('d')

    amount = int(dice_type_and_amount_list[0])
    dice_type = dice_type_and_amount_list[1]

    if amount > 100:
        await ctx.send("You cant roll more than 100 dice at a time. (Blame Caleb.) (Why would you need to do that?)")
        return

    if dice_type == "100":
        for i in range(amount):
            number = random.randint(1, 100)
            rolls_to_return.append(number)

    elif dice_type == "20":
        for i in range(amount):
            number = random.randint(1, 20)
            rolls_to_return.append(number)

    elif dice_type == "12":
        for i in range(amount):
            number = random.randint(1, 12)
            rolls_to_return.append(number)

    elif dice_type == "10":
        for i in range(amount):
            number = random.randint(1, 10)
            rolls_to_return.append(number)

    elif dice_type == "8":
        for i in range(amount):
            number = random.randint(1, 8)
            rolls_to_return.append(number)

    elif dice_type == "6":
        for i in range(amount):
            number = random.randint(1, 6)
            rolls_to_return.append(number)

    elif dice_type == "4":
        for i in range(amount):
            number = random.randint(1, 4)
            rolls_to_return.append(number)

    else:
        #Error, dice type not recognized
        #print("Error")
        await ctx.send(f" `d{dice_type}` is not recognized as a dice type")
        return

    total = sum(rolls_to_return) + modifier

    output_string = f"Rolls for {amount}D{dice_type} were: {str(rolls_to_return)} total of all rolls is {total}"
    if modifier > 0:
        output_string += f" plus your modifier is {total}"
    await ctx.send(output_string)


async def roll_multiple(ctx, roll_string: str):
    roll_string = roll_string.lower()
    # Should come in a format 20d20 3,30d10 3,10d8
    dice_rolls = roll_string.split(",")
    for dice_roll in dice_rolls:
        parts = dice_roll.split('d')

        amount = parts[0]
        type_and_modifier = parts[1]
        type = parts[1]
        modifier = 0
        if ' ' in type_and_modifier: # If there is a space, there is a modifier
            type_and_modifier_list = type_and_modifier.split(' ')
            type = type_and_modifier_list[0]
            modifier = int(type_and_modifier_list[1])

        dice_type_and_amount_input = f"{amount}d{type}" # so that the function above this works properly
        await roll_dice(ctx, dice_type_and_amount_input, modifier)


async def create_character(ctx, name: str, dnd_class: str):
    dnd_classes = [
        "ARTIFICER",
        "BARBARIAN",
        "BARD",
        "CLERIC",
        "DRUID",
        "FIGHTER",
        "MONK",
        "PALADIN",
        "RANGER",
        "ROGUE",
        "SORCERER",
        "WARLOCK",
        "WIZARD"
    ]

    if dnd_class.upper() not in dnd_classes:
        await ctx.send(f"{dnd_class} is not a valid class in DND.")
        return

    user_id = ctx.author.id
    user = get_or_create_user(user_id)

    new_character = DndCharacter(dnd_class, name)
    result = user.add_character(new_character)
    if not result:
        await ctx.send("A Character with that specified name already exists.")
        return

    DataStorage.save_user_data()

    await ctx.send(f"✅ Created character **{name}**!")


async def view_characters(ctx):
    user_id = ctx.author.id
    user = get_or_create_user(user_id)

    await ctx.send(user.view_characters())

