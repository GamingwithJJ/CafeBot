
import discord
import random
import DataStorage
import asyncio
from DataStorage import get_or_create_user
from Classes.RequestClass import Request
from Classes.UserSavesClass import User


async def marry(ctx, member):
    target_user_id = member.id
    author = ctx.author
    author_user_id = author.id

    target_user_data = get_or_create_user(target_user_id)
    author_user_data = get_or_create_user(author_user_id)

    if author_user_id == target_user_id:
        await ctx.send("You can't marry yourself silly!")
        return

    if member.bot:
        await ctx.send("You can't marry a bot!")
        return

    if target_user_id in author_user_data.get_marriage_partners():
        await ctx.send("You are already married to this person!")
        return

    if target_user_data.get_request("marriage", author_user_id) is not None:
        await ctx.send("You have already sent a request to this user")
        return

    request_to_send = Request("marriage", author_user_id)
    target_user_data.add_request("marriage", request_to_send)
    await ctx.send(f"Sent request to {member}")

    # Check if that user already sent the user a request, if so Marry them.
    if author_user_data.get_request("marriage", target_user_id) is not None:
        # Remove the requests
        author_user_data.remove_request_by_data("marriage", target_user_id)
        target_user_data.remove_request(request_to_send)
        # Add the partners
        author_user_data.add_marriage_partner(target_user_id)
        target_user_data.add_marriage_partner(author_user_id)
        await ctx.send("You are both now married! Congratulations!")

    DataStorage.save_user_data() # Temorary. Saves the file every time.


async def divorce(ctx, member):
    author_id = ctx.author.id
    target_id = member.id
    author_data = get_or_create_user(author_id)

    if target_id not in author_data.get_marriage_partners():
        await ctx.send("💔 You aren't married to that person!")
        return

    partner_data = get_or_create_user(target_id)
    author_data.remove_marriage_partner(target_id)
    partner_data.remove_marriage_partner(author_id)
    DataStorage.save_user_data()

    await ctx.send(f"📜 {ctx.author.mention} has divorced <@{target_id}>. The papers have been signed.")


async def adopt(ctx, member):
    author_id = ctx.author.id
    target_id = member.id

    if author_id == target_id:
        await ctx.send("You can't adopt yourself!")
        return

    if member.bot:
        await ctx.send("You can't adopt a bot!")
        return

    author_data = get_or_create_user(author_id)
    target_data = get_or_create_user(target_id)

    if target_id in author_data.get_adopted_children():
        await ctx.send("You have already adopted this person!")
        return

    if target_id in author_data.get_adopted_by():
        await ctx.send("You can't adopt someone who has already adopted you!")
        return

    if target_data.get_request("adoption", author_id) is not None:
        await ctx.send("You have already sent an adoption request to this user!")
        return

    request_to_send = Request("adoption", author_id)
    target_data.add_request("adoption", request_to_send)

    if author_data.get_request("adoption", target_id) is not None:
        author_data.remove_request_by_data("adoption", target_id)
        target_data.remove_request(request_to_send)
        author_data.add_adopted_child(target_id)
        target_data.add_adopted_parent(author_id)
        DataStorage.save_user_data()
        await ctx.send(f"Adoption complete! {member.mention} is now your child! 👨‍👧")
    else:
        DataStorage.save_user_data()
        await ctx.send(f"Sent adoption request to {member.mention}.")


async def unadopt(ctx, member):
    author_id = ctx.author.id
    target_id = member.id

    author_data = get_or_create_user(author_id)
    target_data = get_or_create_user(target_id)

    if target_id in author_data.get_adopted_children():
        # Author is the parent
        author_data.remove_adopted_child(target_id)
        target_data.remove_adopted_parent(author_id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 The adoption of {member.mention} has been dissolved.")
    elif target_id in author_data.get_adopted_by():
        # Author is the child
        target_data.remove_adopted_child(author_id)
        author_data.remove_adopted_parent(target_id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 Your adoption by {member.mention} has been dissolved.")
    else:
        await ctx.send("You don't have an adoption relationship with that person.")


async def family(ctx):
    author_id = ctx.author.id
    user_data = DataStorage.get_or_create_user(author_id)

    parents = user_data.get_adopted_by()
    children = user_data.get_adopted_children()

    if not parents and not children:
        embed = discord.Embed(
            title="👨‍👩‍👧 No Family Found",
            description="You haven't adopted anyone yet, and no one has adopted you!\nUse `.adopt @user` to start a family.",
            color=discord.Color.light_gray()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="👨‍👩‍👧 Your Family",
        color=discord.Color.green()
    )

    if parents:
        mentions = " ".join(f"<@{pid}>" for pid in parents)
        embed.add_field(name=f"👴 Adopted By ({len(parents)})", value=mentions, inline=False)

    if children:
        mentions = " ".join(f"<@{cid}>" for cid in children)
        embed.add_field(name=f"🧒 Children ({len(children)})", value=mentions, inline=False)

    embed.set_footer(text="CafeBot Family Registry | ☕")
    await ctx.send(embed=embed)


async def duel(ctx, target: discord.Member):
    author = ctx.author
    bot_id = ctx.bot.user.id

    if target.id == author.id:
        await ctx.send("You cant duel yourself silly!")
        return

    if target.id == bot_id:
        await ctx.send("You want to duel me? Well Alright!")
        await ctx.send(f"{ctx.bot.user} did 999999 damage to {author}! ({999999-100}/100)")
        await ctx.send(f"Sorry! You lost!")
        return

    author_hp = 100
    target_hp = 100

    embed = discord.Embed(
        title="⚔️ A Duel has Begun!",
        description=f"{author.mention} vs {target.mention}",
        color=discord.Color.red()
    )
    embed.add_field(name=f"{author.display_name}'s HP", value=f"❤️ {author_hp}/100", inline=True)
    embed.add_field(name=f"{target.display_name}'s HP", value=f"❤️ {target_hp}/100", inline=True)
    embed.set_footer(text="Let the battle begin!")

    duel_msg = await ctx.send(embed=embed)
    while author_hp > 0 and target_hp > 0:
        author_roll = random.randint(1, 20)
        target_roll = random.randint(1, 20)

        # Author Turn
        target_hp -= author_roll
        embed.description = f"💥 **{author.display_name}** deals **{author_roll}** damage!"
        embed.set_field_at(0, name=f"{author.display_name}'s HP", value=f"❤️ {author_hp}/100", inline=True)
        embed.set_field_at(1, name=f"{target.display_name}'s HP", value=f"❤️ {target_hp}/100", inline=True)
        await duel_msg.edit(embed=embed)

        # Target Turn
        author_hp -= target_roll
        embed.description = f"💥 **{target.display_name}** deals **{target_roll}** damage!"
        embed.set_field_at(0, name=f"{author.display_name}'s HP", value=f"❤️ {author_hp}/100", inline=True)
        embed.set_field_at(1, name=f"{target.display_name}'s HP", value=f"❤️ {target_hp}/100", inline=True)
        await duel_msg.edit(embed=embed)
        await asyncio.sleep(1.5)


    embed.title = "🏆 Duel Finished!"
    # If author is alive and target is dead
    if author_hp > 0 and target_hp <= 0:
        embed.description = f"Congratulations {author.mention}, you have defeated {target.mention}!"
        embed.color = discord.Color.gold()

    # If target is alive and author is dead
    elif target_hp > 0 and author_hp <= 0:
        embed.description = f"Congratulations {target.mention}, you have defeated {author.mention}!"
        embed.color = discord.Color.gold()

    # Both died at the same time
    else:
        embed.title = "🤝 It's a Tie!"
        embed.description = f"Both {author.mention} and {target.mention} have fallen at the same time!"
        embed.color = discord.Color.light_grey()
    embed.set_footer(text="Good Fight!")
    await duel_msg.edit(embed=embed)


async def quote(ctx):

    list_of_users = list(DataStorage.quotes.keys())
    if not list_of_users:
        await ctx.send("No quotes have been added yet!")
        return

    quotes_dictionary = DataStorage.quotes
    random_user_number = random.randint(0, len(list_of_users) - 1)
    random_user = list_of_users[random_user_number]

    random_quote_number = random.randint(0, len(quotes_dictionary[random_user]) - 1)
    random_quote = quotes_dictionary[random_user][random_quote_number]

    embed = discord.Embed(
        description=f'"{random_quote.get_text()}"',
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"— {random_quote.get_author()}")
    await ctx.send(embed=embed)


async def quotes(ctx, amount: int):
    quotes_users = list(DataStorage.quotes.keys())
    if not quotes_users:
        await ctx.send("No quotes have been added yet!")
        return

    embed = discord.Embed(title="📖 Random Quotes", color=discord.Color.gold())
    for number in range(0, amount):
        quotes_dictionary = DataStorage.quotes
        random_user_number = random.randint(0, len(quotes_users) - 1)
        random_user = quotes_users[random_user_number]

        random_quote_number = random.randint(0, len(quotes_dictionary[random_user]) - 1)
        random_quote = quotes_dictionary[random_user][random_quote_number]
        embed.add_field(name=f"— {random_quote.get_author()}", value=f'"{random_quote.get_text()}"', inline=False)
    await ctx.send(embed=embed)


async def quote_list(ctx, user: str, number):
    """Sorts quotes by a individual and only shows quotes which are sent by a certain individual."""
    user = user.lower().capitalize()
    if user not in DataStorage.quotes.keys():
        await ctx.send(f"{user} user is not a recognized quote user")
        return

    available = DataStorage.quotes[user]
    number = min(number, len(available))
    selected_quotes = random.sample(available, number)
    embed = discord.Embed(title=f"📖 Quotes from {user}", color=discord.Color.gold())
    for i, quote in enumerate(selected_quotes):
        embed.add_field(name=f"Quote #{i + 1}", value=f'"{quote.get_text()}"', inline=False)
    await ctx.send(embed=embed)


async def quote_count(ctx, user: str):
    """Displays the quotes count of a certain user"""
    user = user.lower().capitalize()
    if user not in DataStorage.quotes.keys():
        await ctx.send(f"{user} is not a valid quoter")
        return

    embed = discord.Embed(
        description=f"**{user}** has **{len(DataStorage.quotes[user])}** quotes in the database.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


async def quote_top(ctx):
    """Displays the top ten quoters"""
    quoters = DataStorage.quotes.keys()
    quotes = DataStorage.quotes

    quote_amounts = [] # List which stores the amount of quotes for each quoter and the name of the quoter in a tuple
    for quoter_temp in quoters:
        amount_of_quotes = len(quotes[quoter_temp])
        quote_amounts.append((quoter_temp, amount_of_quotes))

    top_users = sorted(
        quote_amounts,
        key=lambda x: x[1], # Sort by second number
        reverse=True  # Sort descending (biggest numbers first)
    )[:10]

    if not top_users:
        await ctx.send("There were no users who qualify")
        return

    description = ""
    for i, quoter in enumerate(top_users):
        quote_amount = quoter[1]
        description += f"{i + 1}. `{quoter[0]}`: {quote_amount}\n"

    embed = discord.Embed(
        title="🏆 Top 10 users with the most quotes!",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="Top Quoters List!")

    await ctx.send(embed=embed)



async def gif(ctx, type: str, target: discord.Member = None):
    gifs = DataStorage.gifs[type]
    if not gifs:
        await ctx.send(f"⚠️ No GIFs have been added for `{type}` yet. A bot admin can add some with `.add_gif {type} <url>`.")
        return

    gif = random.choice(gifs)

    embed = discord.Embed(color=discord.Color.random())

    template = random.choice(DataStorage.gif_messages[type])
    target_name = target.mention if target else "the void"
    embed.description = template.format(
        author = ctx.author.mention,
        target = target_name
    )

    embed.set_image(url=gif)
    await ctx.send(embed=embed)


async def magic_eight_ball(ctx, question: str):
    response = random.choice(DataStorage.magic_eight_ball)

    embed = discord.Embed(
        title="🔮 Magic 8-Ball",
        description=f"{ctx.author.mention} consults the oracle...",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="❓ Question",
        value=question,
        inline=False
    )

    embed.add_field(
        name="☕ Answer",
        value=f"**{response}**",
        inline=False
    )

    embed.set_footer(text="CafeBot | The coffee grounds have spoken.")
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

    await ctx.send(embed=embed)


async def partner(ctx):
    """Lists your current partners and the time you've been together."""
    author_id = ctx.author.id
    user_data = DataStorage.get_or_create_user(author_id)

    partners = user_data.get_marriage_partners()

    if not partners:
        embed = discord.Embed(
            title="💔 No Partner Found",
            description="You dont have a partner yet, Use .marry to propose!",
            color=discord.Color.light_gray()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="💕 Marriage Certificate",
        description="This is a certificate of your marriage!",
        color=discord.Color.fuchsia()
    )

    embed.add_field(name="👤 User", value=ctx.author.mention, inline=False)

    for pid in partners:
        date = user_data.get_partner_gained_date(pid)
        if date:
            ts = int(date.timestamp())
            date_str = f"<t:{ts}:D> (<t:{ts}:R>)"
        else:
            date_str = "A long, long time ago..."
        embed.add_field(name="💍 Partner", value=f"<@{pid}>\n📅 {date_str}", inline=True)

    # Shared children: adopted by author AND at least one partner
    all_partner_children = set()
    for pid in partners:
        pd = DataStorage.get_or_create_user(pid)
        all_partner_children |= set(pd.get_adopted_children())
    shared = set(user_data.get_adopted_children()) & all_partner_children
    if shared:
        embed.add_field(name="👨‍👩‍👧 Shared Children", value=" ".join(f"<@{cid}>" for cid in shared), inline=False)

    if len(partners) == 1:
        partner_user = ctx.bot.get_user(partners[0]) or await ctx.bot.fetch_user(partners[0])
        if partner_user:
            embed.set_thumbnail(url=partner_user.display_avatar.url)

    embed.set_footer(
        text="CafeBot Love Registry | ☕💕",
        icon_url=ctx.bot.user.display_avatar.url
    )

    await ctx.send(embed=embed)


async def marriage_top(ctx):
    """Lists the top 10 marriages ordered by length married"""
    user_saves = DataStorage.user_data

    pairs = []
    for user_id, user in user_saves.items():
        for pid in user.get_marriage_partners():
            # Only emit each pair once by requiring user_id < str(pid)
            if user_id < str(pid):
                date = user.get_partner_gained_date(pid)
                if date:
                    pairs.append((user_id, pid, date))

    top_pairs = sorted(pairs, key=lambda x: x[2])[:10]

    if not top_pairs:
        await ctx.send("No marriages found in the registry! 💔")
        return

    description = ""
    for i, (uid, pid, date) in enumerate(top_pairs):
        timestamp = int(date.timestamp())
        description += f"{i + 1}. <@{uid}> & <@{pid}> — <t:{timestamp}:R>\n"

    embed = discord.Embed(
        title="🏆 Top 10 Longest Marriages",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="CafeBot Love Registry | ☕💕")

    await ctx.send(embed=embed)


async def quote_search(ctx, keyword: str):
    """Search quotes by text content."""
    keyword_lower = keyword.lower()
    results = []
    for author, quote_list in DataStorage.quotes.items():
        for q in quote_list:
            if keyword_lower in q.get_text().lower():
                results.append(q)

    if not results:
        await ctx.send(f"🔍 No quotes found containing **\"{keyword}\"**.")
        return

    embed = discord.Embed(title=f"🔍 Quotes matching \"{keyword}\"", color=discord.Color.gold())
    for q in results[:10]:
        embed.add_field(name=f"— {q.get_author()}", value=f'"{q.get_text()}"', inline=False)
    if len(results) > 10:
        embed.set_footer(text=f"Showing 10 of {len(results)} matches.")
    await ctx.send(embed=embed)


async def quote_stats(ctx):
    """Show overall quote database statistics."""
    if not DataStorage.quotes:
        await ctx.send("No quotes in the database yet.")
        return

    total = sum(len(qs) for qs in DataStorage.quotes.values())
    top_author = max(DataStorage.quotes, key=lambda a: len(DataStorage.quotes[a]))
    avg = total / len(DataStorage.quotes)

    embed = discord.Embed(title="📊 Quote Database Stats", color=discord.Color.gold())
    embed.add_field(name="Total Quotes", value=str(total), inline=True)
    embed.add_field(name="Total Authors", value=str(len(DataStorage.quotes)), inline=True)
    embed.add_field(name="Average per Author", value=f"{avg:.1f}", inline=True)
    embed.add_field(name="Most Quoted", value=f"{top_author} ({len(DataStorage.quotes[top_author])})", inline=False)
    await ctx.send(embed=embed)


async def profile(ctx):
    """Show a personal profile dashboard."""
    author_id = ctx.author.id
    user_data = DataStorage.get_or_create_user(author_id)

    partners = user_data.get_marriage_partners()
    if partners:
        partner_display = " ".join(f"<@{pid}>" for pid in partners)
    else:
        partner_display = "Single 💔"

    author_name = ctx.author.display_name.lower().capitalize()
    quote_count = len(DataStorage.quotes.get(author_name, []))

    embed = discord.Embed(
        title=f"☕ {ctx.author.display_name}'s Profile",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.add_field(name="💰 Beans", value=f"{user_data.get_beans():.0f}", inline=True)
    embed.add_field(name="💍 Partner", value=partner_display, inline=True)
    embed.add_field(name="🎙️ Quotes in DB", value=str(quote_count), inline=True)
    embed.add_field(name="⚔️ D&D Characters", value=str(len(user_data.characters)), inline=True)
    embed.add_field(name="📅 Daily Streak", value=f"{user_data.daily_reward_streak} days", inline=True)
    embed.add_field(name="🧠 Trivia Wins", value=str(user_data.trivia_correct), inline=True)
    embed.add_field(name="📖 Bookmarked Verses", value=str(len(user_data.bookmarked_verses)), inline=True)
    embed.set_footer(text="CafeBot Profile | ☕")
    await ctx.send(embed=embed)


async def coinflip(ctx):
    random_number = random.randint(0, 1)
    outcome = None

    if random_number == 0:
        outcome = "Heads"
    else:
        outcome = "Tails"

    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"{ctx.author.mention} tossed a coin into the air...",
        color=discord.Color.gold()
    )

    await asyncio.sleep(1)

    embed.add_field(
        name="The result is...",
        value=f"✨ **{outcome}** ✨",
        inline=False
    )

    await ctx.send(embed=embed)