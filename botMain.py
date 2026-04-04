import discord
from discord.ext import commands
import DataStorage

import DndModule
import EconomyModule
import FunModule
import ModerationModule
import BotAdminModule
import FaithModule
import TriviaModule
import MusicModule

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
            ("`.help [module]`", "Show all modules, or use `.help <module>` to list the commands inside it", "any")
        ]
    },
    "Moderation": {
        "description": "Server management and moderation tools.",
        "emoji": "🛡️",
        "commands": [
            ("`.purge <amount>`", "Delete the last `<amount>` messages in the current channel", "server_admin"),
            ("`.lockdown [True/False] [all]`", "Lock or unlock the current channel (`True` = lock, `False` = unlock). Pass `True` as the second argument to apply to every text channel in the server at once", "server_admin"),
            ("`.slowmode [True/False] [seconds]`", "Set a per-message cooldown in the current channel. Defaults to 500s if no time is given. Pass `False` to disable. Maximum is 6 hours (21600s)", "server_admin"),
            ("`.kick <user> [reason]`", "Kick a member from the server. They can rejoin using a new invite", "kick"),
            ("`.ban <user> [reason]`", "Permanently ban a member from the server", "ban"),
            ("`.softban <user> [days] [reason]`", "Ban a member to wipe their recent messages, then immediately unban them so they can rejoin. `[days]` sets how many days of messages to delete (default: 1)", "server_admin"),
            ("`.unban <user_id>`", "Unban a user by their Discord user ID (right-click → Copy ID with Developer Mode on)", "ban"),
            ("`.mute <user> [mins] [reason]`", "Put a user in Discord timeout for `[mins]` minutes (default: 10). They cannot send messages or speak in voice while timed out", "server_admin"),
            ("`.unmute <user>`", "Remove an active timeout from a user early", "server_admin"),
            ("`.whois <user>`", "View a detailed profile of a server member: their ID, nickname, account creation date, server join date, and all their roles", "server_admin")
        ]
    },
    "DnD": {
        "description": "Tabletop RPG dice rolling and character management.",
        "emoji": "🎲",
        "commands": [
            ("`.roll <NdX> [modifier]`", "Roll dice using standard notation (e.g. `.roll 2d20`, `.roll 1d6 3`). Supported dice: d4, d6, d8, d10, d12, d20, d100. An optional modifier is added to the final total. Max 100 dice per roll", "any"),
            ("`.roll_multiple <input>`", "Roll multiple sets of dice in one command, separated by commas (e.g. `.roll_multiple 2d20 3, 1d8`). Each group is rolled and reported separately", "any"),
            ("`.create_character <class> <name>`", "Create and save a new D&D character. Valid classes: Artificer, Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard. Each name must be unique per user", "any"),
            ("`.view_characters`", "List all D&D characters you currently have saved", "any")
        ]
    },
    "Fun": {
        "description": "Social commands, marriage, quotes, duels, trivia, and games.",
        "emoji": "💕",
        "commands": [
            ("`.marry <user>`", "Send a marriage proposal to another user. If they also use `.marry` on you, you are automatically wed. Both users must currently be single", "any"),
            ("`.divorce`", "End your current marriage. This immediately severs the bond for both partners", "any"),
            ("`.partner`", "View your marriage certificate, showing your partner and how long you've been together", "any"),
            ("`.marriage_top`", "See the top 10 longest-running marriages in the server, sorted by how long ago they were formed", "any"),
            ("`.duel <user>`", "Start a turn-based duel against another user. Both combatants begin with 100 HP. Each round, both roll a d20 and deal that much damage — last one standing wins. You can also challenge the bot (good luck)", "any"),
            ("`.quote`", "Display a single random quote from the quote database", "any"),
            ("`.quotes <amount>`", "Display multiple random quotes at once (maximum 5)", "any"),
            ("`.quote_list <user> <amount>`", "Display random quotes from a specific person by their author name in the database (maximum 5 at a time)", "any"),
            ("`.quote_count <user>`", "Check how many quotes a specific person has saved in the database", "any"),
            ("`.quote_top`", "See the top 10 people with the most quotes in the database", "any"),
            ("`.eight_ball <question>`", "Consult the Magic 8-Ball with a yes/no question for a cryptic answer", "any"),
            ("`.coinflip`", "Flip a coin and get Heads or Tails", "any"),
            ("`.trivia <rounds>`", "Start a multiplayer trivia session in the current channel. Questions are drawn from your enabled categories (set with `.trivia_config`). The first person to type the correct answer wins the round. Regular users are limited to 10 rounds max. The winner earns 25 Coffee Beans per correct answer", "any"),
            ("`.trivia_config`", "Open an interactive dropdown menu to choose which trivia categories appear in your games", "any"),
            ("`Emotes (optional @target):`", "**Aggressive:** `.punch` `.slap` `.bonk` `.bite` `.kill` `.obliterate`\n**Affectionate:** `.kiss` `.smooch` `.hug` `.cuddle` `.pat`\n**Social:** `.wave` `.cheer` `.tickle` `.spill`\n**Reactions:** `.stare` `.shocked`\n**Self:** `.happy` `.cry` `.sleep` `.sip` `.explode`", "any")
        ]
    },
    "Economy": {
        "description": "Work shifts, earn Coffee Beans, and tip friends.",
        "emoji": "☕",
        "commands": [
            ("`.shift`", "Work a shift at the cafe to earn between 10–50 Coffee Beans. Has a 30-minute cooldown between uses", "any"),
            ("`.beans`", "Check your current Coffee Bean balance", "any"),
            ("`.tip <@user> <amount>`", "Send some of your Coffee Beans to another user. You cannot tip yourself or bots, and you must have enough beans to cover the amount", "any"),
            ("`.bean_top`", "See the top 10 richest users in the server by Coffee Bean balance", "any"),
            ("`.daily`", "Claim your daily Coffee Bean reward (base: 100 beans). Your streak grows by 1 each consecutive day you claim, adding +2% to your reward per streak day. Missing more than 48 hours resets your streak. 24-hour cooldown", "any")
        ]
    },
    "Faith": {
        "description": "Send testimonies, get Bible verses, and more! (WIP)",
        "emoji": "✝️",
        "commands": [
            ("`.send_anonymous_testimony <message>`", "Send a testimony to the server's testimony channel with no name attached. **Must be used in DMs with the bot.** The bot will show you a preview and ask you to confirm before sending", "any"),
            ("`.verse`", "Display a random Bible verse from the database", "any")
        ]
    },
    "Music": {
        "description": "Play music in voice channels from YouTube.",
        "emoji": "🎵",
        "commands": [
            ("`.play <song name>`", "Search YouTube and add a song to the queue. Joins your voice channel if not already connected", "any"),
            ("`.skip`", "Skip the currently playing song and move to the next in the queue", "any"),
            ("`.leave`", "Clear the queue and disconnect the bot from the voice channel", "any")
        ]
    },
    "Admin": {
        "description": "Bot configuration and database management.",
        "emoji": "⚙️",
        "commands": [
            ("`.add_gif <type> <link>`", "Add a new GIF URL to a specific emote category (e.g. `punch`, `hug`)", "bot_admin"),
            ("`.remove_gif <type> <link>`", "Remove a GIF URL from an emote category by its exact link", "bot_admin"),
            ("`.add_quote <author> <quote>`", "Add a new quote to the database under the given author name", "bot_admin"),
            ("`.remove_quote <quote>`", "Remove a quote from the database by its exact text content", "bot_admin"),
            ("`.add_eight_ball <response>`", "Add a new response to the Magic 8-Ball's answer pool", "bot_admin"),
            ("`.remove_eight_ball <response>`", "Remove a response from the Magic 8-Ball's answer pool by its exact text", "bot_admin"),
            ("`.add_verse <version> <reference> <verse_text>`", "Add a Bible verse to the database. Wrap multi-word fields in quotes (e.g. `.add_verse NIV \"John 3:16\" For God so loved...`)", "bot_admin"),
            ("`.remove_verse <version> <reference>`", "Remove a Bible verse by its translation version and reference (e.g. `.remove_verse NIV John 3:16`)", "bot_admin"),
            ("`.add_trivia <category> <sub_category> <question> <answers>`", "Add a new question to the trivia bank. Wrap fields containing spaces in quotes. Answers should be a comma-separated list of all acceptable answers (e.g. `\"coffee, java, beans\"`)", "bot_admin")
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
async def add_verse(ctx, version: str, reference: str, *, verse_text: str):
    # Usage: .add_verse NIV "John 3:16" For God so loved...
    await BotAdminModule.add_verse(ctx, reference, verse_text, version)


@bot.command()
@is_authorized("bot_admin")
async def remove_verse(ctx, version: str, *, reference: str):
    await BotAdminModule.remove_verse(ctx, reference, version)


@bot.command()
@is_authorized("any")
async def trivia(ctx, rounds: int):
    """Starts a trivia session using the user's config."""
    user_data = DataStorage.get_or_create_user(ctx.author.id)

    # Check if the user is an Admin
    is_admin = str(ctx.author.id) in DataStorage.administrators or ctx.author.guild_permissions.administrator

    # Apply limits to non-admins
    if not is_admin and rounds > 10:
        await ctx.send("🚫 Regular users can only start games with up to 10 rounds!")
        return

    if rounds < 1:
        await ctx.send("You need to play at least 1 round!")
        return

    await TriviaModule.start_session(ctx, rounds, user_data)


@bot.command()
@is_authorized("bot_admin")
async def add_trivia(ctx, category: str, sub_category: str, question: str, *, answers: str):
    """
    Usage: .add_trivia "category" "sub-category" "Question?" "answer 1, answer 2"
    Use quotes around each section if they contain spaces!
    """
    await BotAdminModule.add_trivia(ctx, category, sub_category, question, answers)


@bot.command()
@is_authorized("any")
async def trivia_config(ctx):
    """Opens the trivia configuration menu."""
    user_data = DataStorage.get_or_create_user(ctx.author.id)
    await TriviaModule.open_config(ctx, user_data)


# --- MUSIC COMMANDS ---

@bot.command()
@is_authorized("any")
async def play(ctx, *, search: str):
    """Searches YouTube and plays a song! Usage: .play <song name>"""
    await MusicModule.play_song(ctx, search)


@bot.command()
@is_authorized("any")
async def skip(ctx):
    """Skips the currently playing song."""
    await MusicModule.skip_song(ctx)


@bot.command()
@is_authorized("any")
async def leave(ctx):
    """Clears the queue and makes the bot leave the voice channel."""
    await MusicModule.leave_channel(ctx)


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