import random
import DataStorage
import discord
from Classes.QuoteClass import Quote
from Classes.Verse import Verse
import EconomyModule


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
    """Removes a message template from a gif emote category by exact text."""
    type = type.lower()

    if type not in DataStorage.gif_messages:
        await ctx.send(f"❌ No gif category named `{type}` found.")
        return

    for index, msg in enumerate(DataStorage.gif_messages[type]):
        if msg == message:
            DataStorage.gif_messages[type].pop(index)
            DataStorage.save_gif_messages()
            await ctx.send(f"✅ Removed message from `{type}`.")
            return

    await ctx.send("❌ Could not find that exact message in this category.")


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
    """Removes a quote by its text content."""
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_id = str(ctx.guild.id)
    guild_quotes = DataStorage.quotes.get(guild_id, {})

    for author, quote_list in guild_quotes.items():
        for index, quote_obj in enumerate(quote_list):
            if quote_obj.get_text() == quote_to_remove:
                quote_list.pop(index)
                DataStorage.save_quotes()
                await ctx.send(f"✅ Removed quote from {author}!")
                return

    await ctx.send("❌ Could not find that quote.")


async def add_eight_ball(ctx, response: str):
    if response in DataStorage.magic_eight_ball:
        await ctx.send("This response already exists!")
        return
    DataStorage.magic_eight_ball.append(response)
    DataStorage.save_eight_ball()
    await ctx.send(f"✅ Added response!")


async def remove_eight_ball(ctx, response_to_remove: str):
    for index, response in enumerate(DataStorage.magic_eight_ball):
        if response == response_to_remove:
            DataStorage.magic_eight_ball.pop(index)
            DataStorage.save_eight_ball()
            await ctx.send(f"✅Removed Response!")
            return
    await ctx.send("Could not find specified response")


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


async def remove_trivia(ctx, category: str, sub_category: str, question: str):
    """
    Removes a trivia question from the bank by matching the question text.
    """
    category = category.lower()
    sub_category = sub_category.lower()

    if category not in DataStorage.trivia_questions:
        await ctx.send(f"Category **{category.capitalize()}** not found.")
        return

    if sub_category not in DataStorage.trivia_questions[category]:
        await ctx.send(f"Sub-category **{sub_category.capitalize()}** not found in **{category.capitalize()}**.")
        return

    questions = DataStorage.trivia_questions[category][sub_category]
    for index, entry in enumerate(questions):
        if entry[0].lower() == question.lower():
            questions.pop(index)
            DataStorage.save_trivia_bank()
            await ctx.send(f"✅ Removed question from **{category.capitalize()} -> {sub_category.capitalize()}**!")
            return

    await ctx.send("Could not find a question matching that text.")


async def force_marry(ctx, user1: discord.Member, user2: discord.Member):
    """Force two users into a marriage without mutual consent."""
    if user1.id == user2.id:
        await ctx.send("❌ You can't marry a user to themselves.")
        return
    if user1.bot or user2.bot:
        await ctx.send("❌ Can't force-marry a bot.")
        return

    user1_data = DataStorage.get_or_create_user(user1.id)
    user2_data = DataStorage.get_or_create_user(user2.id)

    if user2.id in user1_data.get_marriage_partners():
        await ctx.send("❌ These users are already married to each other.")
        return

    user1_data.add_marriage_partner(user2.id)
    user2_data.add_marriage_partner(user1.id)
    DataStorage.save_user_data()
    await ctx.send(f"💍 {user1.mention} and {user2.mention} have been force-married.")


async def force_divorce(ctx, user1: discord.Member, user2: discord.Member):
    """Force dissolve a marriage between two users."""
    user1_data = DataStorage.get_or_create_user(user1.id)
    user2_data = DataStorage.get_or_create_user(user2.id)

    if user2.id not in user1_data.get_marriage_partners():
        await ctx.send("❌ These users are not married to each other.")
        return

    user1_data.remove_marriage_partner(user2.id)
    user2_data.remove_marriage_partner(user1.id)
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

    parent_data = DataStorage.get_or_create_user(parent_user.id)
    child_data = DataStorage.get_or_create_user(child_user.id)

    if child_user.id in parent_data.get_adopted_children():
        await ctx.send("❌ This adoption relationship already exists.")
        return
    if child_user.id in parent_data.get_adopted_by():
        await ctx.send("❌ Can't adopt someone who has already adopted you.")
        return

    parent_data.add_adopted_child(child_user.id)
    child_data.add_adopted_parent(parent_user.id)
    DataStorage.save_user_data()
    await ctx.send(f"👨‍👧 {parent_user.mention} has been made the parent of {child_user.mention}.")


async def force_unadopt(ctx, user1: discord.Member, user2: discord.Member):
    """Force dissolve an adoption relationship between two users."""
    user1_data = DataStorage.get_or_create_user(user1.id)
    user2_data = DataStorage.get_or_create_user(user2.id)

    if user2.id in user1_data.get_adopted_children():
        user1_data.remove_adopted_child(user2.id)
        user2_data.remove_adopted_parent(user1.id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 Adoption dissolved: {user1.mention} is no longer the parent of {user2.mention}.")
    elif user2.id in user1_data.get_adopted_by():
        user2_data.remove_adopted_child(user1.id)
        user1_data.remove_adopted_parent(user2.id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 Adoption dissolved: {user2.mention} is no longer the parent of {user1.mention}.")
    else:
        await ctx.send("❌ These users don't have an adoption relationship.")


async def force_lottery_draw(ctx):
    """Draws a lottery winner and resets the pool."""
    if not DataStorage.lottery_entries:
        await ctx.send("No tickets have been sold this round!")
        return

    population = list(DataStorage.lottery_entries.keys())
    weights = [DataStorage.lottery_entries[uid] for uid in population]
    winner_id = random.choices(population, weights=weights, k=1)[0]

    winner_data = DataStorage.get_or_create_user(int(winner_id))
    pot = DataStorage.lottery_pot
    winner_data.ajust_beans(pot)

    DataStorage.lottery_pot = 0.0
    DataStorage.lottery_entries = {}
    DataStorage.save_user_data()
    DataStorage.save_lottery()

    embed = discord.Embed(
        title="🎉 Lottery Draw!",
        description=f"<@{winner_id}> won the lottery and took home **{int(pot):,} beans**!",
        color=discord.Color.gold()
    )
    embed.set_footer(text="The pot has been reset. Good luck next round! 🎟️")
    await ctx.send(embed=embed)


async def admin_lottery_add(ctx, amount: int):
    """Adds beans directly to the lottery pot without requiring ticket purchases."""
    if amount <= 0:
        await ctx.send("Amount must be positive.")
        return
    DataStorage.lottery_pot += amount
    DataStorage.save_lottery()
    embed = discord.Embed(
        title="🎟️ Lottery Pot Updated",
        description=f"Added **{amount:,}** beans to the lottery pot.",
        color=discord.Color.gold()
    )
    embed.add_field(name="New Pot", value=f"{int(DataStorage.lottery_pot):,} beans")
    await ctx.send(embed=embed)


async def admin_user_info(ctx, target: discord.Member):
    """Display a full summary of a user's saved data."""
    user = DataStorage.get_or_create_user(target.id)
    cap = EconomyModule.BANK_UPGRADE_TIERS[user.bank_level]

    embed = discord.Embed(
        title=f"🔍 User Info — {target.display_name}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=target.display_avatar.url)

    # Economy
    embed.add_field(
        name="💰 Economy",
        value=(
            f"**Wallet:** {int(user.get_beans()):,} beans\n"
            f"**Bank:** {int(user.bank_balance):,} / {cap:,} beans (Level {user.bank_level})"
        ),
        inline=False
    )

    # Social
    spouses = ", ".join(f"<@{pid}>" for pid in user.marriage_partner) or "None"
    children = ", ".join(f"<@{cid}>" for cid in user.adopted_children) or "None"
    parents = ", ".join(f"<@{pid}>" for pid in user.adopted_by) or "None"
    embed.add_field(
        name="💍 Social",
        value=(
            f"**Spouses:** {spouses}\n"
            f"**Children:** {children}\n"
            f"**Parents:** {parents}\n"
            f"**Total Marriages:** {user.total_marriages} | **Divorces:** {user.total_divorces}"
        ),
        inline=False
    )

    # Stats
    last_shift = user.last_shift.strftime("%Y-%m-%d %H:%M") if user.last_shift else "Never"
    last_daily = user.last_daily.strftime("%Y-%m-%d %H:%M") if user.last_daily else "Never"
    embed.add_field(
        name="📊 Stats",
        value=(
            f"**Daily Streak:** {user.daily_reward_streak}\n"
            f"**Trivia Correct:** {user.trivia_correct}\n"
            f"**Last Shift:** {last_shift}\n"
            f"**Last Daily:** {last_daily}"
        ),
        inline=False
    )

    # Moderation
    embed.add_field(
        name="🔨 Moderation",
        value=f"**Warnings:** {len(user.warnings)}",
        inline=False
    )

    await ctx.send(embed=embed)


async def admin_tip(ctx, target: discord.Member, amount: float):
    """Grants a user beans without requiring the admin to have funds."""
    if amount == 0:
        await ctx.send("Amount must be greater or less than 0.")
        return

    target_data = DataStorage.get_or_create_user(target.id)
    target_data.ajust_beans(amount)
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="💸 Admin Tip Sent!",
        description=f"{ctx.author.mention} granted **{amount}** beans to {target.mention}!",
        color=discord.Color.green()
    )
    embed.add_field(name=f"{target.display_name}'s New Balance", value=f"{int(target_data.get_beans())} beans")

    await ctx.send(embed=embed)
