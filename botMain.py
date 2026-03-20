import discord
from discord.ext import commands
import DataStorage

import DndModule
import EconomyModule
import FunModule
import ModerationModule
import BotAdminModule

from dotenv import dotenv_values

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

bot.remove_command('help')


def is_authorized(required_type: str = "any"):
    async def predicate(ctx):
        user_id = ctx.author.id

        if user_id in DataStorage.administrators:
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


@bot.command()
@is_authorized("any")
async def help(ctx):
    embed = discord.Embed(
        title="☕ CafeBot Command Menu",
        description="Here is a list of commands you can use.",
        color=discord.Color.gold()
    )

    # --- Misc Module ---
    misc_text = """
    `.ping` - Check if the bot is awake
    `.help` - Display this command menu
    """
    embed.add_field(name="🔧 Misc", value=misc_text, inline=False)

    # --- Moderation Module ---
    mod_text = """
    `.purge <amount>` - Delete messages (Admin)
    `.lockdown [state] [all]` - Lock channels (Admin)
    `.slowmode <on/off> [seconds]` - Set chat delay (Admin)
    `.kick <user> [reason]` - Kick a member
    `.ban <user> [reason]` - Ban a member
    `.softban <user> [days] [reason]` - Ban & delete msgs, then unban
    `.unban <id>` - Unban a user by ID
    `.mute <user> [mins] [reason]` - Timeout a user
    `.unmute <user>` - Remove timeout
    `.whois <user>` - View user account info (Admin)
    """
    embed.add_field(name="🛡️ Moderation", value=mod_text, inline=False)

    # --- DnD Module ---
    dnd_text = """
    `.roll <dice> [modifier]` - Roll dice (e.g. `.roll d20`, `.roll 2d6 +3`)
    `.roll_multiple <input>` - Roll multiple sets of dice
    `.create_character <name> <class>` - Create and save a specified character
    `.view_characters` - Lists all your currently saved characters
    """
    embed.add_field(name="🎲 DnD", value=dnd_text, inline=False)

    # --- Fun Module ---
    fun_text = """
    `.marry <user>` - Propose to another user (or accept if they proposed to you)
    `.divorce` - End your current marriage
    `.partner` - Lists your current marriage and how long you have been married
    `.marriage_top` - Lists the top ten marriages in the server by length.
    `.duel <user>` - Have a duel with the specified user!
    `.quote` - Generate a random quote!
    `.quote_list <user> <amount>` - Generates a random quote which is sent by or mentions a specified user
    `.quote_count <user>` - Lists how many quotes a quoter has.
    `.quote_top` - Lists the top quoters.
    `Emotes:` `.punch`, `.kill`, `.kiss`, `.slap`, `.tickle`, `.wave`, `.cry`, `.happy`
    `.eight_ball <question>` - Ask the eight ball a question and have it generate a response!
    `.coinflip` - Flip a coin!
    """
    embed.add_field(name="💕 Fun", value=fun_text, inline=False)

    # --- Economy Module ---
    economy_text = """
    `.shift` - Work a shift to earn Coffee Beans
    `.beans` - Check your bean balance
    `.tip <@user> <amount>` - Send beans to another user
    `.bean_top` - Lists the richest users.
    `.daily` - Get your daily reward!
    """
    embed.add_field(name="☕ Economy", value=economy_text, inline=False)

    # Footer
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    await ctx.send(embed=embed)


@bot.command()
@is_authorized("bot_admin")
async def admin_help(ctx):
    embed = discord.Embed(
        title="☕ CafeBot Admin Commands",
        description="Use these commands to manage the bot's GIF database and settings.",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="`.add_gif <type> <link>`",
        value="Adds a new GIF link to the database.\n*Example: `.add_gif punch https://tenor.com/example.gif`*",
        inline=False
    )

    embed.add_field(
        name="`.remove_gif <type> <link>`",
        value="Removes a specific GIF link from the database.\n*Example: `.remove_gif punch https://tenor.com/example.gif`*",
        inline=False
    )

    embed.add_field(
        name="`.add_quote <quoter> <quote>`",
        value="Adds a new quote into the database.",
        inline=False
    )

    embed.add_field(
        name="`.remove_quote <quote>`",
        value="Removes the specified quote from the datebase.",
        inline=False
    )

    embed.add_field(
        name="`.add_eight_ball <response>`",
        value="Adds the specified eight ball response to the database.",
        inline=False
    )

    embed.add_field(
        name="`.remove_eight_ball <response>`",
        value="Removes the specified eight ball response from the database.",
        inline=False
    )

    embed.set_footer(text="CafeBot Administration | Use responsibly! ☕")
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

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
async def tip(ctx, target: discord.Member, amount: int):
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