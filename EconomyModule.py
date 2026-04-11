import random

import DataStorage
import datetime
import discord


#Configuration Variables
BREW_COOLDOWN_TIME = 30 # Minutes
BEANS_PER_BREW = (10, 50) # Range between the two numbers
DAILY_REWARD_BASE = 100

SLOT_SYMBOLS = ["☕", "🫘", "🥐", "💰", "🍀", "7️⃣", "🌀", "⭐", "🎪", "☁️"]


async def beans(ctx):
    """Shows the current amount of beans the user has"""
    user = ctx.author
    user_data = DataStorage.get_or_create_user(user.id)

    embed = discord.Embed(
        title="☕ Coffee Bean Balance",
        description=f"**{user.display_name}** has **{int(user_data.get_beans())}** beans.",
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
    embed.add_field(name="💰 New Balance", value=f"**{int(user.get_beans())}** beans", inline=False)
    embed.set_footer(text=f"Next shift available in {BREW_COOLDOWN_TIME} minutes")
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


async def tip(ctx, target: discord.Member, amount: float):
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
            description=f"You only have **{int(author_data.get_beans())}** beans, but tried to tip **{int(amount)}**.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    author_data.ajust_beans(-1 * amount)
    target_data.ajust_beans(amount)
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="💸 Tip Sent!",
        description=f"{ctx.author.mention} tipped **{int(amount)}** beans to {target.mention}!",
        color=discord.Color.green()
    )

    embed.add_field(name=f"{ctx.author.display_name}'s Balance", value=f"{int(author_data.get_beans())} beans", inline=True)
    embed.add_field(name=f"{target.display_name}'s Balance", value=f"{int(target_data.get_beans())} beans", inline=True)

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
        bean_amount = int(user.get_beans())
        description += f"{i + 1}. <@{user.discord_id}>: {bean_amount}\n"

    embed = discord.Embed(
        title="🏆 Top 10 Richest Users",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="Beantop List")

    await ctx.send(embed=embed)


async def cafe_status(ctx):
    """Show a server-wide snapshot of cafe activity."""
    user_saves = DataStorage.user_data

    total_beans = sum(u.get_beans() for u in user_saves.values())
    total_marriages = sum(len(u.marriage_partner) for u in user_saves.values()) // 2
    total_quotes = sum(len(qs) for qs in DataStorage.quotes.values())
    total_authors = len(DataStorage.quotes)

    embed = discord.Embed(
        title="☕ Cafe Status",
        description="A snapshot of the server's cafe activity!",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.add_field(name="💰 Beans in Circulation", value=f"{total_beans:,.0f}", inline=True)
    embed.add_field(name="👥 Registered Users", value=str(len(user_saves)), inline=True)
    embed.add_field(name="💍 Active Marriages", value=str(total_marriages), inline=True)
    embed.add_field(name="📖 Total Quotes", value=f"{total_quotes} from {total_authors} authors", inline=False)
    embed.set_footer(text="CafeBot | ☕")
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

    amount_to_reward = int(DAILY_REWARD_BASE * (1 + (user.daily_reward_streak * 0.02)))
    user.daily_reward_streak += 1
    user.ajust_beans(amount_to_reward)
    user.last_daily = now
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="Daily Reward!",
        description=f"You claimed your daily allowance of **{amount_to_reward}** Coffee Beans! \n Your current streak is {user.daily_reward_streak} days!",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 New Balance", value=f"**{int(user.get_beans())}** beans")
    embed.set_footer(text="See you tomorrow! ☕")
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


async def slots(ctx, bet: int):
    """Spin the slot machine and bet Coffee Beans."""
    user = DataStorage.get_or_create_user(ctx.author.id)

    if bet < 1:
        await ctx.send("Minimum bet is 1 bean.")
        return
    if bet > user.get_beans():
        await ctx.send(f"You don't have enough beans! Balance: {int(user.get_beans())}")
        return

    reels = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
    display = " | ".join(reels)

    if reels[0] == reels[1] == reels[2]:
        if reels[0] == "7️⃣":
            multiplier, result_text = 231, "🎰 JACKPOT! Triple 7s!"
        else:
            multiplier, result_text = 26, "🎉 Three of a kind!"
        winnings = int(bet * multiplier) - bet
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        winnings = bet
        result_text = "✨ Two of a kind!"
    else:
        winnings = -bet
        result_text = "💸 No match. Better luck next time!"

    user.ajust_beans(winnings)
    DataStorage.save_user_data()

    color = discord.Color.gold() if winnings > 0 else discord.Color.red()
    embed = discord.Embed(title="🎰 Slot Machine", color=color)
    embed.add_field(name="Reels", value=display, inline=False)
    embed.add_field(name="Result", value=result_text, inline=False)
    embed.add_field(name="Bet", value=f"{bet} beans", inline=True)
    change = f"+{winnings}" if winnings >= 0 else str(winnings)
    embed.add_field(name="Change", value=f"{change} beans", inline=True)
    embed.add_field(name="New Balance", value=f"{int(user.get_beans())} beans", inline=True)
    embed.set_footer(text="CafeBot Casino | ☕🎰")
    await ctx.send(embed=embed)


async def blackjack(ctx, bet: int):
    """Play blackjack against the dealer."""
    user = DataStorage.get_or_create_user(ctx.author.id)

    if bet < 1:
        await ctx.send("Minimum bet is 1 bean.")
        return
    if bet > user.get_beans():
        await ctx.send(f"You don't have enough beans! Balance: {int(user.get_beans())}")
        return

    def hand_value(hand):
        total = sum(hand)
        aces = hand.count(11)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def hand_display(hand, hide_second=False):
        face = lambda v: "A" if v == 11 else str(v)
        if hide_second:
            return f"{face(hand[0])}  🂠"
        return "  ".join(face(v) for v in hand)

    def make_embed(player, dealer, hide_dealer=True, result_text=None):
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
        embed.add_field(name=f"Your Hand ({hand_value(player)})", value=hand_display(player), inline=False)
        d_label = "Dealer's Hand" if hide_dealer else f"Dealer's Hand ({hand_value(dealer)})"
        embed.add_field(name=d_label, value=hand_display(dealer, hide_second=hide_dealer), inline=False)
        if result_text:
            embed.add_field(name="Result", value=result_text, inline=False)
        return embed

    def resolve(player, dealer):
        p, d = hand_value(player), hand_value(dealer)
        if p > 21:
            return -bet, "💥 Bust! You went over 21."
        elif d > 21 or p > d:
            return bet, "🎉 You win!"
        elif p == d:
            return 0, "🤝 Push — your bet is returned."
        else:
            return -bet, "💸 Dealer wins."

    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    if hand_value(player_hand) == 21:
        winnings = int(bet * 1.5)
        user.ajust_beans(winnings)
        DataStorage.save_user_data()
        embed = make_embed(player_hand, dealer_hand, hide_dealer=False,
                           result_text=f"🎰 BLACKJACK! +{winnings} beans")
        await ctx.send(embed=embed)
        return

    class BlackjackView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.message = None

        async def end_game(self, interaction, final_player, final_dealer):
            winnings, result_text = resolve(final_player, final_dealer)
            user.ajust_beans(winnings)
            DataStorage.save_user_data()
            change = f"+{winnings}" if winnings >= 0 else str(winnings)
            result_text += f"\n**{change} beans** → Balance: {int(user.get_beans())}"
            embed = make_embed(final_player, final_dealer, hide_dealer=False, result_text=result_text)
            self.stop()
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
        async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            player_hand.append(deck.pop())
            pv = hand_value(player_hand)
            if pv > 21:
                await self.end_game(interaction, player_hand, dealer_hand)
            elif pv == 21:
                while hand_value(dealer_hand) < 17:
                    dealer_hand.append(deck.pop())
                await self.end_game(interaction, player_hand, dealer_hand)
            else:
                await interaction.response.edit_message(
                    embed=make_embed(player_hand, dealer_hand, hide_dealer=True), view=self)

        @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
        async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            while hand_value(dealer_hand) < 17:
                dealer_hand.append(deck.pop())
            await self.end_game(interaction, player_hand, dealer_hand)

        async def on_timeout(self):
            while hand_value(dealer_hand) < 17:
                dealer_hand.append(deck.pop())
            winnings, result_text = resolve(player_hand, dealer_hand)
            user.ajust_beans(winnings)
            DataStorage.save_user_data()
            embed = make_embed(player_hand, dealer_hand, hide_dealer=False,
                               result_text=result_text + " (timed out)")
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.edit(embed=embed, view=self)

    view = BlackjackView()
    msg = await ctx.send(embed=make_embed(player_hand, dealer_hand, hide_dealer=True), view=view)
    view.message = msg
