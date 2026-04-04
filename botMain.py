import discord
from discord.ext import commands
import DataStorage

import DndModule
import EconomyModule
import FunModule
import ModerationModule
import BotAdminModule
import FaithModule

from dotenv import dotenv_values

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

bot.remove_command('help')

config = dotenv_values(".env")
DataStorage.administrators = config.get("administrators").split(",")


def is_authorized(required_type: str = "any"):
    async def predicate(ctx):

        if str(ctx.author.id) in DataStorage.administrators:
            return True

        if required_type == "server_admin":
            return ctx.author.guild_permissions.administrator

        elif required_type == "moderator":
            return ctx.author.guild_permissions.manage_messages

        elif required_type == "kick":
            return ctx.author.guild_permissions.kick_members

        elif required_type == "ban":
            return ctx.author.guild_permissions.ban_members

        elif required_type == "mute":
            return ctx.author.guild_permissions.moderate_members

        elif required_type == "bot_admin":
            # Commands for only bot administrators
            return False

        elif required_type == "any":
            # Anyone can use this command
            return True

        # Default: deny access
        return False

    return commands.check(predicate)


# Events:
@bot.event
async def on_ready():
    DataStorage.load_user_data()
    DataStorage.load_all()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


# Commands:


# --- HELP MENU CONFIGURATION ---

# 1. Helper function to check if a user can see a command
def check_cmd_permission(ctx, required_type):
    # Bot admins can see everything
    if str(ctx.author.id) in DataStorage.administrators:
        return True

    if required_type == "any":
        return True
    elif required_type == "server_admin":
        return ctx.author.guild_permissions.administrator
    elif required_type == "moderator":
        return ctx.author.guild_permissions.manage_messages
    elif required_type == "kick":
        return ctx.author.guild_permissions.kick_members
    elif required_type == "ban":
        return ctx.author.guild_permissions.ban_members
    elif required_type == "mute":
        return ctx.author.guild_permissions.moderate_members
    elif required_type == "bot_admin":
        return False

    return False


# 2. Format: ("Command Usage", "Description", "Required Permission")
COMMAND_MODULES = {
    "Misc": {
        "description": "General bot utilities.",
        "emoji": "🔧",
        "commands": [
            ("`.ping`", "Check if the bot is awake", "any"),
            ("`.help [module]`", "Display this menu", "any")
        ]
    },
    "Moderation": {
        "description": "Server management and moderation tools.",
        "emoji": "🛡️",
        "commands": [
            ("`.purge <amount>`", "Delete messages", "server_admin"),
            ("`.lockdown [state] [all]`", "Lock channels", "server_admin"),
            ("`.slowmode <on/off> [seconds]`", "Set chat delay", "server_admin"),
            ("`.kick <user> [reason]`", "Kick a member", "kick"),
            ("`.ban <user> [reason]`", "Ban a member", "ban"),
            ("`.softban <user> [days] [reason]`", "Ban & delete msgs, then unban", "server_admin"),
            ("`.unban <id>`", "Unban a user by ID", "ban"),
            ("`.mute <user> [mins] [reason]`", "Timeout a user", "server_admin"),
            ("`.unmute <user>`", "Remove timeout", "server_admin"),
            ("`.whois <user>`", "View user account info", "server_admin")
        ]
    },
    "DnD": {
        "description": "Tabletop RPG dice and character management.",
        "emoji": "🎲",
        "commands": [
            ("`.roll <dice> [modifier]`", "Roll dice (e.g. .roll d20)", "any"),
            ("`.roll_multiple <input>`", "Roll multiple sets of dice", "any"),
            ("`.create_character <name> <class>`", "Create and save a character", "any"),
            ("`.view_characters`", "Lists all your currently saved characters", "any")
        ]
    },
    "Fun": {
        "description": "Social commands, marriage, quotes, and games.",
        "emoji": "💕",
        "commands": [
            ("`.marry <user>`", "Propose to another user", "any"),
            ("`.divorce`", "End your current marriage", "any"),
            ("`.partner`", "View your marriage certificate", "any"),
            ("`.marriage_top`", "Top ten marriages in the server", "any"),
            ("`.duel <user>`", "Have a duel with the specified user!", "any"),
            ("`.quote`", "Generate a random quote!", "any"),
            ("`.quote_list <user> <amount>`", "Quotes from a specific user", "any"),
            ("`.quote_count <user>`", "Check how many quotes someone has", "any"),
            ("`.quote_top`", "Top quoters leaderboard", "any"),
            ("`.eight_ball <question>`", "Ask the eight ball a question", "any"),
            ("`.coinflip`", "Flip a coin!", "any"),
            ("`Emotes:`", "`.punch`, `.kill`, `.kiss`, etc.", "any")
        ]
    },
    "Economy": {
        "description": "Work shifts, earn beans, and tip friends.",
        "emoji": "☕",
        "commands": [
            ("`.shift`", "Work a shift to earn Coffee Beans", "any"),
            ("`.beans`", "Check your bean balance", "any"),
            ("`.tip <@user> <amount>`", "Send beans to another user", "any"),
            ("`.bean_top`", "Lists the richest users", "any"),
            ("`.daily`", "Get your daily reward!", "any")
        ]
    },
    "Faith": {
        "description": "send testimonies, get Bible verses, and more! (WIP)",
        "emoji": "✝️",
        "commands": [
            ("`.send_anonymous_testimony`", "Sends your testimony anonymously into the testimonies chat", "any")
        ]
    },
    "Admin": {
        "description": "Bot configuration and database management.",
        "emoji": "⚙️",
        "commands": [
            ("`.add_gif <type> <link>`", "Adds a new GIF", "bot_admin"),
            ("`.remove_gif <type> <link>`", "Removes a GIF", "bot_admin"),
            ("`.add_quote <author> <quote>`", "Adds a new quote", "bot_admin"),
            ("`.remove_quote <quote>`", "Removes a quote", "bot_admin"),
            ("`.add_eight_ball <response>`", "Add an 8-ball response", "bot_admin"),
            ("`.remove_eight_ball <response>`", "Remove an 8-ball response", "bot_admin")
        ]
    }
}


# 3. The New Dynamic Help Command
@bot.command()
@is_authorized("any")
async def help(ctx, module_name: str = None):
    # If they just type .help (no module specified)
    if module_name is None:
        embed = discord.Embed(
            title="☕ CafeBot Modules",
            description="Use `.help <module>` to see the commands inside it!",
            color=discord.Color.gold()
        )

        for mod_name, mod_data in COMMAND_MODULES.items():
            # Check if user has access to at least ONE command in this module
            can_see_module = any(check_cmd_permission(ctx, req) for _, _, req in mod_data["commands"])

            if can_see_module:
                embed.add_field(
                    name=f"{mod_data['emoji']} {mod_name}",
                    value=mod_data["description"],
                    inline=False
                )

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # If they typed .help <module>
    else:
        # Find the module, ignoring capitalization
        target_module = None
        for mod_name in COMMAND_MODULES:
            if mod_name.lower() == module_name.lower():
                target_module = mod_name
                break

        if not target_module:
            await ctx.send(f"❌ Could not find a module named `{module_name}`.")
            return

        mod_data = COMMAND_MODULES[target_module]

        embed = discord.Embed(
            title=f"{mod_data['emoji']} {target_module} Commands",
            description=mod_data["description"],
            color=discord.Color.gold()
        )

        # Loop through commands and only add the ones they have permission for
        visible_commands = 0
        for cmd_usage, cmd_desc, req_permission in mod_data["commands"]:
            if check_cmd_permission(ctx, req_permission):
                embed.add_field(name=cmd_usage, value=cmd_desc, inline=False)
                visible_commands += 1

        # If they found the module but don't have access to any commands inside it
        if visible_commands == 0:
            await ctx.send("🚫 You do not have permission to view commands in this module.")
            return

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)


@bot.command()
@is_authorized("any")
async def ping(ctx):
    await ctx.send('Pong!')


@bot.command()
@is_authorized("server_admin")
async def purge(ctx, amount: int):
    await ModerationModule.purge(ctx, amount)


@bot.command()
@is_authorized("server_admin")
async def lockdown(ctx, state: bool = True, all_channels: bool = False):
    await ModerationModule.lockdown(ctx, state, all_channels)


@bot.command()
@is_authorized("kick")
async def kick(ctx, member: discord.Member, reason="No reason provided"):
    await ModerationModule.kick_user(ctx, member, reason)


@bot.command()
@is_authorized("ban")
async def ban(ctx, member: discord.Member, reason="No reason provided"):
    await ModerationModule.ban_user(ctx, member, reason)


@bot.command()
@is_authorized("ban")
async def unban(ctx, user_id: int):
    await ModerationModule.unban_user(ctx, user_id)


@bot.command()
@is_authorized("server_admin")
async def slowmode(ctx, boolean: bool = True, seconds: int = 500):
    await ModerationModule.slowmode(ctx, boolean, seconds)


@bot.command()
@is_authorized("server_admin")
async def mute(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason given"):
    await ModerationModule.timeout_user(ctx, member, minutes, reason)


@bot.command()
@is_authorized("server_admin")
async def unmute(ctx, member: discord.Member):
    await ModerationModule.remove_timeout(ctx, member)


@bot.command()
@is_authorized("server_admin")
async def softban(ctx, member: discord.Member, amount_of_days: int = 1, reason="No reason given"):
    await ModerationModule.softban_user(ctx, member, amount_of_days, reason)


@bot.command()
@is_authorized("server_admin")
async def whois(ctx, member: discord.Member):
    await ModerationModule.whois(ctx, member)


@bot.command()
@is_authorized("any")
async def roll(ctx, dice_type_and_amount: str, modifier: int = 0):
    await DndModule.roll_dice(ctx, dice_type_and_amount, modifier)


@bot.command()
@is_authorized("any")
async def roll_multiple(ctx, *,  dice_input):
    await DndModule.roll_multiple(ctx, dice_input)


@bot.command()
@is_authorized("any")
async def create_character(ctx, dnd_class: str, name: str):
    await DndModule.create_character(ctx, dnd_class, name)


@bot.command()
@is_authorized("any")
async def view_characters(ctx):
    await DndModule.view_characters(ctx)


@bot.command()
@is_authorized("any")
async def marry(ctx, target_user: discord.Member):
    await FunModule.marry(ctx, target_user)


@bot.command()
@is_authorized("any")
async def divorce(ctx):
    await FunModule.divorce(ctx)


@bot.command()
@is_authorized("any")
async def duel(ctx, target: discord.Member):
    await FunModule.duel(ctx, target)


@bot.command()
@is_authorized("any")
async def quote(ctx):
    await FunModule.quote(ctx)


@bot.command()
@is_authorized("bot_admin")
async def add_quote(ctx, authors, *, quote_input: str):
    await BotAdminModule.add_quote(ctx, authors, quote_input)


@bot.command()
@is_authorized("bot_admin")
async def remove_quote(ctx, *, quote_input: str):
    await BotAdminModule.remove_quote(ctx, quote_input)


@bot.command()
@is_authorized("bot_admin")
async def add_gif(ctx, type: str, link: str):
    await BotAdminModule.add_gif(ctx, type, link)


@bot.command()
@is_authorized("bot_admin")
async def remove_gif(ctx, type: str, link: str):
    await BotAdminModule.remove_gif(ctx, type, link)


@bot.command()
@is_authorized("any")
async def punch(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "punch", target)


@bot.command()
@is_authorized("any")
async def kill(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "kill", target)


@bot.command()
@is_authorized("any")
async def slap(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "slap", target)


@bot.command()
@is_authorized("any")
async def tickle(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "tickle", target)


@bot.command()
@is_authorized("any")
async def wave(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "wave", target)


@bot.command()
@is_authorized("any")
async def happy(ctx):
    await FunModule.gif(ctx, "happy")


@bot.command()
@is_authorized("any")
async def cry(ctx):
    await FunModule.gif(ctx, "cry")


@bot.command()
@is_authorized("any")
async def kiss(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "kiss", target)


@bot.command()
@is_authorized("any")
async def smooch(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "kiss", target)


@bot.command()
@is_authorized("any")
async def hug(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "hug", target)


@bot.command()
@is_authorized("any")
async def sip(ctx):
    # No target needed!
    await FunModule.gif(ctx, "sip")


@bot.command()
@is_authorized("any")
async def spill(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "spill", target)


@bot.command()
@is_authorized("any")
async def shocked(ctx):
    await FunModule.gif(ctx, "shocked")


@bot.command()
@is_authorized("any")
async def pat(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "pat", target)


@bot.command()
@is_authorized("any")
async def cuddle(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "cuddle", target)


@bot.command()
@is_authorized("any")
async def cheer(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "cheer", target)


@bot.command()
@is_authorized("any")
async def bonk(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "bonk", target)


@bot.command()
@is_authorized("any")
async def bite(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "bite", target)


@bot.command()
@is_authorized("any")
async def stare(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "stare", target)


@bot.command()
@is_authorized("any")
async def explode(ctx):
    await FunModule.gif(ctx, "explode")


@bot.command()
@is_authorized("any")
async def sleep(ctx):
    await FunModule.gif(ctx, "sleep")


@bot.command()
@is_authorized("any")
async def obliterate(ctx, target: discord.Member = None):
    await FunModule.gif(ctx, "purge", target)


@bot.command()
@is_authorized("any")
async def eight_ball(ctx, *, question: str = "No question asked"):
    await FunModule.magic_eight_ball(ctx, question)


@bot.command()
@is_authorized("bot_admin")
async def add_eight_ball(ctx, *, response: str):
    await BotAdminModule.add_eight_ball(ctx, response)


@bot.command()
@is_authorized("bot_admin")
async def remove_eight_ball(ctx, *, response: str):
    await BotAdminModule.remove_eight_ball(ctx, response)


@bot.command()
@is_authorized("any")
async def shift(ctx):
    await EconomyModule.shift(ctx)


@bot.command()
@is_authorized("any")
async def beans(ctx):
    await EconomyModule.beans(ctx)


@bot.command()
@is_authorized("any")
async def tip(ctx, target: discord.Member, amount: float):
    await EconomyModule.tip(ctx, target, amount)


@bot.command()
@is_authorized("any")
async def partner(ctx):
    await FunModule.partner(ctx)


@bot.command()
@is_authorized("any")
async def marriage_top(ctx):
    await FunModule.marriage_top(ctx)


@bot.command()
@is_authorized("any")
async def bean_top(ctx):
    await EconomyModule.bean_top(ctx)


@bot.command()
@is_authorized("any")
async def quote_list(ctx, user: str, amount: int = 1):
    await FunModule.quote_list(ctx, user, amount)


@bot.command()
@is_authorized("any")
async def quote_count(ctx, user: str):
    await FunModule.quote_count(ctx, user)


@bot.command()
@is_authorized("any")
async def quote_top(ctx):
    await FunModule.quote_top(ctx)


@bot.command()
@is_authorized("any")
async def quotes(ctx, amount: int):
    await FunModule.quotes(ctx, amount)


@bot.command()
@is_authorized("any")
async def coinflip(ctx):
    await FunModule.coinflip(ctx)


@bot.command()
@is_authorized("any")
async def daily(ctx):
    await EconomyModule.daily(ctx)


@bot.command()
@is_authorized("any")
async def send_anonymous_testimony(ctx, *, message: str):
    await FaithModule.send_testimony(ctx, message)

@bot.command()
@is_authorized("any")
async def verse(ctx):
    await FaithModule.random_verse(ctx)

@bot.command()
@is_authorized("bot_admin")
async def add_verse(ctx, reference: str, *, verse_text: str):
    # We use '*' for verse_text so it captures the whole sentence
    # Usage: .add_verse "John 3:16" For God so loved...
    await BotAdminModule.add_verse(ctx, reference, verse_text)

@bot.command()
@is_authorized("bot_admin")
async def remove_verse(ctx, *, reference: str):
    await BotAdminModule.remove_verse(ctx, reference)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🚫 You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided.")
    else:
        # Log unexpected errors
        print(f"Unexpected error: {error}")


config = dotenv_values(".env")
token = config.get("token")

bot.run(token)