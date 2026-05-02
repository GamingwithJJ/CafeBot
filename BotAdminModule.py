import asyncio
import random
import datetime
import difflib
import DataStorage
import discord
from Classes.QuoteClass import Quote
from Classes.Verse import Verse
import EconomyModule


def _fuzzy_find(query: str, candidates: list) -> str | None:
    if not candidates:
        return None
    query_lower = query.lower()
    best = max(candidates, key=lambda c: difflib.SequenceMatcher(None, query_lower, c.lower(), autojunk=False).ratio())
    return best


async def _confirm_removal(ctx, embed: discord.Embed) -> bool:
    embed.set_footer(text="React ✅ to confirm, ❌ to cancel (30s)")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, user):
        return user == ctx.author and reaction.message.id == msg.id and str(reaction.emoji) in ("✅", "❌")

    try:
        reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=30.0, check=check)
        return str(reaction.emoji) == "✅"
    except asyncio.TimeoutError:
        await ctx.send("Cancelled (timed out).")
        return False


def _format_duration(seconds):
    if seconds >= 86400:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h" if hours else f"{days}d"
    if seconds >= 3600:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    return f"{seconds // 60}m"


async def add_gif(ctx, type: str, link: str):
    """Adds a new gif for the specified type"""
    type = type.lower()

    try:
        new_category = type not in DataStorage.gifs
        if new_category:
            DataStorage.gifs[type] = []
        DataStorage.gifs[type].append(link)
        DataStorage.save_gifs()
        if new_category:
            await ctx.send(f"Created new category `{type}` and added the link.")
        else:
            await ctx.send(f"Added the link to the list")
    except Exception as e:
        await ctx.send(f"There was an error, {e}")


async def remove_gif(ctx, type: str, link: str):
    """Removes a gif of the specified link"""
    type = type.lower()
    gif_list = None

    try:
        gif_list = DataStorage.gifs[type]
    except Exception as e:
        await ctx.send(f"There was an error, {e}")
        return

    for index, gif in enumerate(gif_list):
        if gif == link:
            DataStorage.gifs[type].pop(index)
            DataStorage.save_gifs()
            await ctx.send("Removed gif from the list.")
            return

    await ctx.send("Gif with the specified link was not found.")


async def add_gif_message(ctx, type: str, message: str):
    """Adds a new message template to a gif emote category."""
    type = type.lower()

    if type not in DataStorage.gif_messages:
        await ctx.send(f"❌ No gif category named `{type}` found.")
        return

    if message in DataStorage.gif_messages[type]:
        await ctx.send("That message already exists for this category.")
        return

    DataStorage.gif_messages[type].append(message)
    DataStorage.save_gif_messages()
    await ctx.send(f"✅ Added message to `{type}`.")


async def remove_gif_message(ctx, type: str, message: str):
    type = type.lower()

    if type not in DataStorage.gif_messages:
        await ctx.send(f"❌ No gif category named `{type}` found.")
        return

    candidates = DataStorage.gif_messages[type]
    matched = _fuzzy_find(message, candidates)
    if matched is None:
        await ctx.send(f"❌ No messages found in `{type}`.")
        return

    embed = discord.Embed(title="🔍 Closest Match Found", color=discord.Color.orange())
    embed.add_field(name="Category", value=f"`{type}`", inline=True)
    embed.add_field(name="Message", value=matched, inline=False)

    if await _confirm_removal(ctx, embed):
        DataStorage.gif_messages[type].remove(matched)
        DataStorage.save_gif_messages()
        await ctx.send(f"✅ Removed message from `{type}`.")
    else:
        await ctx.send("❌ Removal cancelled.")


async def add_quote(ctx, authors, quote):
    """Adds a new quote with the author"""
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_id = str(ctx.guild.id)

    if isinstance(authors, str):
        authors = [authors.lower().capitalize()]
    else:
        authors = [author.lower().capitalize() for author in authors]

    guild_quotes = DataStorage.quotes.setdefault(guild_id, {})

    # Filter for already exists
    for author in authors:
        if author in guild_quotes:
            for quote_object in guild_quotes[author]:
                if quote_object.get_text() == quote:
                    await ctx.send(f"That quote already exists for {author}")
                    return

    for author in authors:
        quote_object = Quote(quote, author)
        if author not in guild_quotes:
            guild_quotes[author] = []
        guild_quotes[author].append(quote_object)

    DataStorage.save_quotes()
    await ctx.send(f"✅ Added quote")


async def remove_quote(ctx, quote_to_remove: str):
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_id = str(ctx.guild.id)
    guild_quotes = DataStorage.quotes.get(guild_id, {})

    all_entries = [(quote_obj.get_text(), author, quote_obj)
                   for author, quote_list in guild_quotes.items()
                   for quote_obj in quote_list]

    if not all_entries:
        await ctx.send("❌ No quotes found.")
        return

    q_lower = quote_to_remove.lower()
    matched_text, matched_author, matched_obj = max(
        all_entries,
        key=lambda e: difflib.SequenceMatcher(None, q_lower, e[0].lower(), autojunk=False).ratio()
    )

    embed = discord.Embed(title="🔍 Closest Match Found", color=discord.Color.orange())
    embed.add_field(name="Quote", value=matched_text, inline=False)
    embed.add_field(name="Author", value=matched_author, inline=True)

    if await _confirm_removal(ctx, embed):
        guild_quotes[matched_author].remove(matched_obj)
        DataStorage.save_quotes()
        await ctx.send(f"✅ Removed quote from {matched_author}!")
    else:
        await ctx.send("❌ Removal cancelled.")


async def add_eight_ball(ctx, response: str):
    if response in DataStorage.magic_eight_ball:
        await ctx.send("This response already exists!")
        return
    DataStorage.magic_eight_ball.append(response)
    DataStorage.save_eight_ball()
    await ctx.send(f"✅ Added response!")


async def remove_eight_ball(ctx, response_to_remove: str):
    matched = _fuzzy_find(response_to_remove, DataStorage.magic_eight_ball)
    if matched is None:
        await ctx.send("❌ No 8-ball responses found.")
        return

    embed = discord.Embed(title="🔍 Closest Match Found", color=discord.Color.orange())
    embed.add_field(name="Response", value=matched, inline=False)

    if await _confirm_removal(ctx, embed):
        DataStorage.magic_eight_ball.remove(matched)
        DataStorage.save_eight_ball()
        await ctx.send("✅ Removed response!")
    else:
        await ctx.send("❌ Removal cancelled.")


async def add_trivia(ctx, category: str, sub_category: str, question: str, answers: str):
    """
    Adds a new trivia question to the bank dynamically.
    Answers should be separated by commas (e.g., "coffee, beans, java").
    """
    category = category.lower()
    sub_category = sub_category.lower()

    # Split the comma-separated string into a clean list of lowercase answers
    acceptable_answers = [ans.strip().lower() for ans in answers.split(",")]

    # If the category doesn't exist yet, create it!
    if category not in DataStorage.trivia_questions:
        DataStorage.trivia_questions[category] = {}

    # If the sub-category doesn't exist yet, create it!
    if sub_category not in DataStorage.trivia_questions[category]:
        DataStorage.trivia_questions[category][sub_category] = []

    # Format the data into our tuple format and append it
    new_question_data = [question, acceptable_answers]
    DataStorage.trivia_questions[category][sub_category].append(new_question_data)

    # Save the file
    DataStorage.save_trivia_bank()

    await ctx.send(f"✅ Added new question to **{category.capitalize()} -> {sub_category.capitalize()}**!")


async def remove_trivia(ctx, category: str, sub_category: str | None, question: str):
    category = category.lower()

    if category not in DataStorage.trivia_questions:
        await ctx.send(f"❌ Category **{category.capitalize()}** not found.")
        return

    if sub_category is not None:
        sub_category = sub_category.lower()
        if sub_category not in DataStorage.trivia_questions[category]:
            await ctx.send(f"❌ Sub-category **{sub_category.capitalize()}** not found in **{category.capitalize()}**.")
            return
        search_entries = [(e, sub_category) for e in DataStorage.trivia_questions[category][sub_category]]
    else:
        search_entries = [
            (e, sc)
            for sc, entries in DataStorage.trivia_questions[category].items()
            for e in entries
        ]

    if not search_entries:
        await ctx.send("❌ No trivia questions found in that category.")
        return

    q_lower = question.lower()
    ranked = sorted(
        search_entries,
        key=lambda pair: difflib.SequenceMatcher(None, q_lower, pair[0][0].lower(), autojunk=False).ratio(),
        reverse=True
    )

    def make_embed(i):
        entry, sub = ranked[i]
        embed = discord.Embed(title=f"🔍 Match {i + 1} of {len(ranked)}", color=discord.Color.orange())
        embed.add_field(name="Category", value=f"{category.capitalize()} → {sub.capitalize()}", inline=False)
        embed.add_field(name="Question", value=entry[0], inline=False)
        embed.add_field(name="Answers", value=", ".join(entry[1]), inline=False)
        embed.set_footer(text="⬅️ prev  ➡️ next  ✅ remove  ❌ cancel (60s)")
        return embed

    index = 0
    msg = await ctx.send(embed=make_embed(0))
    for emoji in ("⬅️", "➡️", "✅", "❌"):
        await msg.add_reaction(emoji)

    def check(reaction, user):
        return (
            user == ctx.author
            and reaction.message.id == msg.id
            and str(reaction.emoji) in ("⬅️", "➡️", "✅", "❌")
        )

    while True:
        try:
            reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=60.0, check=check)
            emoji = str(reaction.emoji)

            if emoji == "➡️":
                index = (index + 1) % len(ranked)
                await msg.edit(embed=make_embed(index))
                try:
                    await msg.remove_reaction(emoji, ctx.author)
                except discord.Forbidden:
                    pass
            elif emoji == "⬅️":
                index = (index - 1) % len(ranked)
                await msg.edit(embed=make_embed(index))
                try:
                    await msg.remove_reaction(emoji, ctx.author)
                except discord.Forbidden:
                    pass
            elif emoji == "✅":
                matched_entry, matched_sub = ranked[index]
                DataStorage.trivia_questions[category][matched_sub].remove(matched_entry)
                DataStorage.save_trivia_bank()
                await ctx.send(f"✅ Removed question from **{category.capitalize()} → {matched_sub.capitalize()}**!")
                return
            elif emoji == "❌":
                await ctx.send("❌ Removal cancelled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("Cancelled (timed out).")
            return


async def force_marry(ctx, user1: discord.Member, user2: discord.Member):
    """Force two users into a marriage without mutual consent."""
    if user1.id == user2.id:
        await ctx.send("❌ You can't marry a user to themselves.")
        return
    if user1.bot or user2.bot:
        await ctx.send("❌ Can't force-marry a bot.")
        return

    guild_id = str(ctx.guild.id)
    user1_data = DataStorage.get_or_create_user(user1.id)
    user2_data = DataStorage.get_or_create_user(user2.id)

    if user2.id in user1_data.get_marriage_partners(guild_id):
        await ctx.send("❌ These users are already married to each other.")
        return

    user1_data.add_marriage_partner(guild_id, user2.id)
    user2_data.add_marriage_partner(guild_id, user1.id)
    DataStorage.save_user_data()
    await ctx.send(f"💍 {user1.mention} and {user2.mention} have been force-married.")


async def force_divorce(ctx, user1: discord.Member, user2: discord.Member):
    """Force dissolve a marriage between two users."""
    guild_id = str(ctx.guild.id)
    user1_data = DataStorage.get_or_create_user(user1.id)
    user2_data = DataStorage.get_or_create_user(user2.id)

    if user2.id not in user1_data.get_marriage_partners(guild_id):
        await ctx.send("❌ These users are not married to each other.")
        return

    user1_data.remove_marriage_partner(guild_id, user2.id)
    user2_data.remove_marriage_partner(guild_id, user1.id)
    DataStorage.save_user_data()
    await ctx.send(f"📜 {user1.mention} and {user2.mention} have been force-divorced.")


async def force_adopt(ctx, parent_user: discord.Member, child_user: discord.Member):
    """Force an adoption relationship between two users."""
    if parent_user.id == child_user.id:
        await ctx.send("❌ A user can't adopt themselves.")
        return
    if parent_user.bot or child_user.bot:
        await ctx.send("❌ Can't force-adopt a bot.")
        return

    guild_id = str(ctx.guild.id)
    parent_data = DataStorage.get_or_create_user(parent_user.id)
    child_data = DataStorage.get_or_create_user(child_user.id)

    if child_user.id in parent_data.get_adopted_children(guild_id):
        await ctx.send("❌ This adoption relationship already exists.")
        return
    if child_user.id in parent_data.get_adopted_by(guild_id):
        await ctx.send("❌ Can't adopt someone who has already adopted you.")
        return

    parent_data.add_adopted_child(guild_id, child_user.id)
    child_data.add_adopted_parent(guild_id, parent_user.id)
    DataStorage.save_user_data()
    await ctx.send(f"👨‍👧 {parent_user.mention} has been made the parent of {child_user.mention}.")


async def force_unadopt(ctx, user1: discord.Member, user2: discord.Member):
    """Force dissolve an adoption relationship between two users."""
    guild_id = str(ctx.guild.id)
    user1_data = DataStorage.get_or_create_user(user1.id)
    user2_data = DataStorage.get_or_create_user(user2.id)

    if user2.id in user1_data.get_adopted_children(guild_id):
        user1_data.remove_adopted_child(guild_id, user2.id)
        user2_data.remove_adopted_parent(guild_id, user1.id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 Adoption dissolved: {user1.mention} is no longer the parent of {user2.mention}.")
    elif user2.id in user1_data.get_adopted_by(guild_id):
        user2_data.remove_adopted_child(guild_id, user1.id)
        user1_data.remove_adopted_parent(guild_id, user2.id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 Adoption dissolved: {user2.mention} is no longer the parent of {user1.mention}.")
    else:
        await ctx.send("❌ These users don't have an adoption relationship.")


async def admin_lottery_start(ctx, ticket_cap, duration_seconds, max_per_user):
    """Start a new lottery with the given trigger conditions."""
    guild_id = str(ctx.guild.id)

    if DataStorage.get_lottery_active(guild_id):
        await ctx.send("A lottery is already running! Use `.admin_lottery_cancel` to cancel it first.")
        return

    end_time = None
    if duration_seconds is not None:
        end_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=duration_seconds)
        end_time = end_dt.isoformat()

    DataStorage.lottery_active[guild_id] = {
        "ticket_cap": ticket_cap,
        "end_time": end_time,
        "max_per_user": max_per_user,
        "channel_id": str(ctx.channel.id),
    }
    DataStorage.lottery_pot[guild_id] = 0.0
    DataStorage.lottery_entries[guild_id] = {}
    DataStorage.save_lottery()

    cap_display = f"{ticket_cap:,} tickets" if ticket_cap else "No cap"
    time_display = _format_duration(duration_seconds) if duration_seconds else "No time limit"

    embed = discord.Embed(
        title="🎟️ Lottery Started!",
        description="A new lottery round has begun. Buy tickets with `.lottery_buy <amount>`!",
        color=discord.Color.green()
    )
    embed.add_field(name="🎫 Ticket Cap", value=cap_display, inline=True)
    embed.add_field(name="⏱️ Time Limit", value=time_display, inline=True)
    embed.add_field(name="👤 Max Per User", value=str(max_per_user), inline=True)
    embed.add_field(name="💰 Ticket Cost", value=f"{EconomyModule.LOTTERY_TICKET_COST} beans", inline=True)
    await ctx.send(embed=embed)


async def admin_lottery_cancel(ctx):
    """Cancel the active lottery and refund all ticket buyers."""
    guild_id = str(ctx.guild.id)

    if not DataStorage.get_lottery_active(guild_id):
        await ctx.send("No lottery is currently running.")
        return

    entries = DataStorage.get_lottery_entries(guild_id)
    refund_count = 0
    for user_id, ticket_count in entries.items():
        refund = ticket_count * EconomyModule.LOTTERY_TICKET_COST
        user = DataStorage.get_or_create_user(int(user_id))
        user.ajust_beans(guild_id, refund)
        refund_count += 1

    DataStorage.lottery_active.pop(guild_id, None)
    DataStorage.lottery_pot[guild_id] = 0.0
    DataStorage.lottery_entries[guild_id] = {}
    DataStorage.save_user_data()
    DataStorage.save_lottery()

    embed = discord.Embed(
        title="❌ Lottery Cancelled",
        description=f"The lottery has been cancelled. **{refund_count}** participant(s) have been refunded.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


async def force_lottery_draw(ctx):
    """Draws a lottery winner immediately and resets the pool."""
    guild_id = str(ctx.guild.id)
    entries = DataStorage.get_lottery_entries(guild_id)

    if not entries:
        await ctx.send("No tickets have been sold this round!")
        return

    await EconomyModule._execute_lottery_draw(guild_id, ctx.channel)


async def admin_lottery_add(ctx, amount: int):
    """Adds beans directly to the lottery pot without requiring ticket purchases."""
    if amount <= 0:
        await ctx.send("Amount must be positive.")
        return
    guild_id = str(ctx.guild.id)
    DataStorage.lottery_pot[guild_id] = DataStorage.get_lottery_pot(guild_id) + amount
    DataStorage.save_lottery()
    embed = discord.Embed(
        title="🎟️ Lottery Pot Updated",
        description=f"Added **{amount:,}** beans to the lottery pot.",
        color=discord.Color.gold()
    )
    embed.add_field(name="New Pot", value=f"{int(DataStorage.get_lottery_pot(guild_id)):,} beans")
    await ctx.send(embed=embed)


async def admin_jackpot_set(ctx, amount: int):
    """Set the per-server slots jackpot pool to an exact amount."""
    if amount < 0:
        await ctx.send("Amount must be zero or positive.")
        return
    guild_id = str(ctx.guild.id)
    DataStorage.set_jackpot(guild_id, amount)
    DataStorage.save_jackpot()
    embed = discord.Embed(
        title="🎰 Jackpot Updated",
        description=f"Set the slots jackpot to **{amount:,}** beans.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


async def admin_lottery_give(ctx, target: discord.Member, amount: int):
    """Grant lottery tickets to a user without requiring bean payment."""
    if amount <= 0:
        await ctx.send("Amount must be positive.")
        return

    guild_id = str(ctx.guild.id)
    user_id = str(target.id)
    DataStorage.lottery_entries.setdefault(guild_id, {})[user_id] = \
        DataStorage.get_lottery_entries(guild_id).get(user_id, 0) + amount
    DataStorage.save_lottery()

    embed = discord.Embed(
        title="🎟️ Tickets Granted",
        description=f"Granted **{amount}** ticket(s) to {target.mention}.",
        color=discord.Color.gold()
    )
    embed.add_field(name="Their Total", value=f"{DataStorage.lottery_entries[guild_id][user_id]} ticket(s)", inline=True)
    embed.add_field(name="Current Pot", value=f"{int(DataStorage.get_lottery_pot(guild_id)):,} beans", inline=True)
    await ctx.send(embed=embed)


async def admin_user_info(ctx, target: discord.Member):
    """Display a full summary of a user's saved data for the current server."""
    guild_id = str(ctx.guild.id)
    user = DataStorage.get_or_create_user(target.id)
    state = user.state(guild_id)
    cap = EconomyModule.BANK_UPGRADE_TIERS[state.bank_level]

    embed = discord.Embed(
        title=f"🔍 User Info — {target.display_name}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=target.display_avatar.url)

    # Economy
    embed.add_field(
        name="💰 Economy",
        value=(
            f"**Wallet:** {int(user.get_beans(guild_id)):,} beans\n"
            f"**Bank:** {int(state.bank_balance):,} / {cap:,} beans (Level {state.bank_level})"
        ),
        inline=False
    )

    # Social
    spouses = ", ".join(f"<@{pid}>" for pid in state.marriage_partner) or "None"
    children = ", ".join(f"<@{cid}>" for cid in state.adopted_children) or "None"
    parents = ", ".join(f"<@{pid}>" for pid in state.adopted_by) or "None"
    embed.add_field(
        name="💍 Social",
        value=(
            f"**Spouses:** {spouses}\n"
            f"**Children:** {children}\n"
            f"**Parents:** {parents}\n"
            f"**Total Marriages:** {state.total_marriages} | **Divorces:** {state.total_divorces}"
        ),
        inline=False
    )

    # Stats
    last_shift = state.last_shift.strftime("%Y-%m-%d %H:%M") if state.last_shift else "Never"
    last_daily = state.last_daily.strftime("%Y-%m-%d %H:%M") if state.last_daily else "Never"
    embed.add_field(
        name="📊 Stats",
        value=(
            f"**Daily Streak:** {state.daily_reward_streak}\n"
            f"**Trivia Correct:** {state.trivia_correct}\n"
            f"**Last Shift:** {last_shift}\n"
            f"**Last Daily:** {last_daily}"
        ),
        inline=False
    )

    # Moderation
    embed.add_field(
        name="🔨 Moderation",
        value=f"**Warnings (this server):** {len(user.get_warnings(guild_id))}",
        inline=False
    )

    embed.set_footer(text="All economy/social data shown is for this server only.")
    await ctx.send(embed=embed)


async def admin_tip(ctx, target: discord.Member, amount: float):
    """Grants a user beans without requiring the admin to have funds."""
    if amount == 0:
        await ctx.send("Amount must be greater or less than 0.")
        return

    guild_id = str(ctx.guild.id)
    target_data = DataStorage.get_or_create_user(target.id)
    target_data.ajust_beans(guild_id, amount)
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="💸 Admin Tip Sent!",
        description=f"{ctx.author.mention} granted **{amount}** beans to {target.mention}!",
        color=discord.Color.green()
    )
    embed.add_field(name=f"{target.display_name}'s New Balance", value=f"{int(target_data.get_beans(guild_id))} beans")

    await ctx.send(embed=embed)
