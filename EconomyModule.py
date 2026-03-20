import random

import DataStorage
import datetime
import discord


#Configuration Variables
BREW_COOLDOWN_TIME = 30 # Minutes
BEANS_PER_BREW = (10, 50) # Range between the two numbers
DAILY_REWARD_BASE = 100


async def beans(ctx):
    """Shows the current amount of beans the user has"""
    user = ctx.author
    user_data = DataStorage.get_or_create_user(user.id)

    embed = discord.Embed(
        title="☕ Coffee Bean Balance",
        description=f"**{user.display_name}** has **{user_data.get_beans()}** beans.",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    await ctx.send(embed=embed)


async def shift(ctx):
    """Works a shift providing the user with currency"""
    user = DataStorage.get_or_create_user(ctx.author.id)
    current_time = datetime.datetime.now()


    # Check for cooldown
    if user.last_shift: # If the last_shift is none, we know its a new user and can proceed as there is no cooldown
        time_passed = current_time - user.last_shift
        cooldown = datetime.timedelta(minutes=BREW_COOLDOWN_TIME)

        if time_passed < cooldown:
            remaining_cooldown_time = cooldown - time_passed
            minutes, seconds = divmod(int(remaining_cooldown_time.total_seconds()), 60)

            embed = discord.Embed(
                title="☕ Woah, slow down there!",
                description=f"You already worked recently!\nTry again in **{minutes}m {seconds}s**.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

    beans_earned = random.randint(*BEANS_PER_BREW)
    user.ajust_beans(beans_earned)
    user.set_last_shift(current_time)
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="☕ Shift Complete!",
        description=f"You worked a shift at the cafe and earned **{beans_earned}** Beans!",
        color=discord.Color.from_rgb(111, 78, 55)  # Coffee brown
    )
    embed.add_field(name="💰 New Balance", value=f"**{user.get_beans()}** beans", inline=False)
    embed.set_footer(text=f"Next shift available in {BREW_COOLDOWN_TIME} minutes")
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


async def tip(ctx, target: discord.member, amount: int):
    """Sends a specified user some of your beans"""
    author = ctx.author
    author_id = author.id
    target_id = target.id

    if target_id == author_id:
        await ctx.send("You can't tip yourself!")
        return

    if target.bot:
        await ctx.send("You can't tip a bot!")
        return

    if amount <= 0:
        await ctx.send("There we go, you sent a box of air, good job.")
        return

    author_data = DataStorage.get_or_create_user(author_id)
    target_data = DataStorage.get_or_create_user(target_id)

    if author_data.get_beans() < amount:
        embed = discord.Embed(
            title="❌ Insufficient Beans",
            description=f"You only have **{author_data.get_beans()}** beans, but tried to tip **{amount}**.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    author_data.ajust_beans(-1 * amount)
    target_data.ajust_beans(amount)
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="💸 Tip Sent!",
        description=f"{ctx.author.mention} tipped **{amount}** beans to {target.mention}!",
        color=discord.Color.green()
    )

    embed.add_field(name=f"{ctx.author.display_name}'s Balance", value=f"{author_data.beans} beans", inline=True)
    embed.add_field(name=f"{target.display_name}'s Balance", value=f"{target_data.beans} beans", inline=True)

    await ctx.send(embed=embed)


async def bean_top(ctx):
    """Lists the top ten richest users by bean amounts"""
    user_saves = DataStorage.user_data

    bean_users = []

    for user_id, user in user_saves.items():
        if user.get_beans() == 0:
            continue

        bean_users.append(user)

    top_users = sorted(
        [b for b in bean_users if b.beans],
        key=lambda x: x.beans,
        reverse = True
    )[:10]

    if not top_users:
        await ctx.send("There were no users who qualify")
        return

    description = ""
    for i, user in enumerate(top_users):
        bean_amount = user.get_beans()
        description += f"{i + 1}. <@{user.discord_id}>: {bean_amount}\n"

    embed = discord.Embed(
        title="🏆 Top 10 Richest Users",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="Beantop List")

    await ctx.send(embed=embed)


async def daily(ctx):
    """Claim a daily reward of Coffee Beans."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    now = datetime.datetime.now()

    if user.last_daily:
        time_passed = now - user.last_daily
        cooldown = datetime.timedelta(hours=24)
        grace_period = datetime.timedelta(hours=48)

        if time_passed < cooldown:
            remaining_time = cooldown - time_passed
            hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)

            embed = discord.Embed(
                title="You're on cooldown!",
                description=f"You've already claimed your daily! Come back in **{hours}h and {minutes}m**!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if time_passed > grace_period:
            user.daily_reward_streak = 0
            await ctx.send("You have lost your streak!")

    amount_to_reward = DAILY_REWARD_BASE * (1 + (user.daily_reward_streak * 0.02))
    user.daily_reward_streak += 1
    user.ajust_beans(amount_to_reward)
    user.last_daily = now
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="Daily Reward!",
        description=f"You claimed your daily allowance of **{amount_to_reward}** Coffee Beans! \n Your current streak is {user.daily_reward_streak} days!",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 New Balance", value=f"**{user.get_beans()}** beans")
    embed.set_footer(text="See you tomorrow! ☕")
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)
