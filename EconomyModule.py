import random

import DataStorage
import datetime
import discord


#Configuration Variables
BREW_COOLDOWN_TIME = 30 # Minutes
BEANS_PER_BREW = (10, 50) # Range between the two numbers
DAILY_REWARD_BASE = 100

LOTTERY_TICKET_COST = 50
LOTTERY_MAX_TICKETS = 10

BANK_UPGRADE_TIERS = [1000, 2000, 5000, 10000, 20000]
BANK_UPGRADE_COSTS = [0, 300, 800, 2000, 5000]

ROB_SUCCESS_RATE = 0.45
ROB_STEAL_RANGE = (0.10, 0.25)
ROB_STEAL_CAP = 500
ROB_FAILURE_FINE = 150
ROB_COOLDOWN_MINUTES = 60
ROB_IMMUNITY_MINUTES = 45
ROB_MIN_TARGET_WALLET = 100

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
    """Lists the top ten richest users by total beans (wallet + bank)"""
    user_saves = DataStorage.user_data

    def total_beans(u):
        return u.beans + u.bank_balance

    top_users = sorted(
        [u for u in user_saves.values() if total_beans(u) > 0],
        key=total_beans,
        reverse=True
    )[:10]

    if not top_users:
        await ctx.send("There were no users who qualify")
        return

    description = ""
    for i, user in enumerate(top_users):
        description += f"{i + 1}. <@{user.discord_id}>: {int(total_beans(user)):,}\n"

    embed = discord.Embed(
        title="🏆 Top 10 Richest Users",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="Beantop List — wallet + bank combined")

    await ctx.send(embed=embed)


async def cafe_status(ctx):
    """Show a server-wide snapshot of cafe activity."""
    user_saves = DataStorage.user_data

    total_beans = sum(u.beans + u.bank_balance for u in user_saves.values())
    total_marriages = sum(len(u.marriage_partner) for u in user_saves.values()) // 2
    total_quotes = sum(
        len(quote_list)
        for author_dict in DataStorage.quotes.values()
        for quote_list in author_dict.values()
    )
    total_authors = len({
        author
        for author_dict in DataStorage.quotes.values()
        for author in author_dict
    })

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

    if bet < 50:
        await ctx.send("Minimum bet is 50 beans.")
        return
    if bet > user.get_beans():
        await ctx.send(f"You don't have enough beans! Balance: {int(user.get_beans())}")
        return

    def spin_result():
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
        return display, winnings, result_text

    def make_embed(display, winnings, result_text):
        color = discord.Color.gold() if winnings > 0 else discord.Color.red()
        embed = discord.Embed(title="🎰 Slot Machine", color=color)
        embed.add_field(name="Reels", value=display, inline=False)
        embed.add_field(name="Result", value=result_text, inline=False)
        embed.add_field(name="Bet", value=f"{bet} beans", inline=True)
        change = f"+{winnings}" if winnings >= 0 else str(winnings)
        embed.add_field(name="Change", value=f"{change} beans", inline=True)
        embed.add_field(name="New Balance", value=f"{int(user.get_beans())} beans", inline=True)
        embed.set_footer(text="CafeBot Casino | ☕🎰")
        return embed

    class SlotsView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.message = None

        @discord.ui.button(label="Play Again", style=discord.ButtonStyle.green)
        async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            if user.get_beans() < bet:
                button.disabled = True
                await interaction.response.edit_message(content="❌ Not enough beans to play again!", view=self)
                return
            display, winnings, result_text = spin_result()
            user.ajust_beans(winnings)
            DataStorage.save_user_data()
            await interaction.response.edit_message(embed=make_embed(display, winnings, result_text), view=self)

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.edit(view=self)

    display, winnings, result_text = spin_result()
    user.ajust_beans(winnings)
    DataStorage.save_user_data()

    view = SlotsView()
    msg = await ctx.send(embed=make_embed(display, winnings, result_text), view=view)
    view.message = msg


_BJ_RANK_VALUES = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':10,'Q':10,'K':10,'A':11}
_BJ_SUITS = ['♠', '♥', '♦', '♣']
_BJ_RANKS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']


def _bj_hand_value(hand):
    total = sum(_BJ_RANK_VALUES[rank] for rank, _ in hand)
    aces = sum(1 for rank, _ in hand if rank == 'A')
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def _bj_hand_display(hand, hide_second=False):
    cards = [f"{rank}{suit}" for rank, suit in hand]
    if hide_second:
        return f"{cards[0]}  🂠"
    return "  ".join(cards)


def _bj_make_embed(player, dealer, hide_dealer=True, result_text=None):
    embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
    embed.add_field(name=f"Your Hand ({_bj_hand_value(player)})", value=_bj_hand_display(player), inline=False)
    d_label = "Dealer's Hand" if hide_dealer else f"Dealer's Hand ({_bj_hand_value(dealer)})"
    embed.add_field(name=d_label, value=_bj_hand_display(dealer, hide_second=hide_dealer), inline=False)
    if result_text:
        embed.add_field(name="Result", value=result_text, inline=False)
    return embed


def _bj_resolve(player, dealer, bet):
    p, d = _bj_hand_value(player), _bj_hand_value(dealer)
    if p > 21:
        return -bet, "💥 Bust! You went over 21."
    elif d > 21 or p > d:
        return bet, "🎉 You win!"
    elif p == d:
        return 0, "🤝 Push — your bet is returned."
    else:
        return -bet, "💸 Dealer wins."


def _bj_new_game():
    deck = [(rank, suit) for suit in _BJ_SUITS for rank in _BJ_RANKS]
    random.shuffle(deck)
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    return deck, player_hand, dealer_hand


class BlackjackView(discord.ui.View):
    def __init__(self, ctx, user, bet, deck, player_hand, dealer_hand):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user = user
        self.bet = bet
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.message = None

    async def end_game(self, interaction, final_player, final_dealer):
        winnings, result_text = _bj_resolve(final_player, final_dealer, self.bet)
        self.user.ajust_beans(winnings)
        DataStorage.save_user_data()
        change = f"+{winnings}" if winnings >= 0 else str(winnings)
        result_text += f"\n**{change} beans** → Balance: {int(self.user.get_beans())}"
        embed = _bj_make_embed(final_player, final_dealer, hide_dealer=False, result_text=result_text)
        self.stop()
        play_again_view = BlackjackPlayAgainView(self.ctx, self.bet)
        await interaction.response.edit_message(embed=embed, view=play_again_view)
        play_again_view.message = interaction.message

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        self.player_hand.append(self.deck.pop())
        pv = _bj_hand_value(self.player_hand)
        if pv > 21:
            await self.end_game(interaction, self.player_hand, self.dealer_hand)
        elif pv == 21:
            while _bj_hand_value(self.dealer_hand) < 17:
                self.dealer_hand.append(self.deck.pop())
            await self.end_game(interaction, self.player_hand, self.dealer_hand)
        else:
            await interaction.response.edit_message(
                embed=_bj_make_embed(self.player_hand, self.dealer_hand, hide_dealer=True), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        while _bj_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
        await self.end_game(interaction, self.player_hand, self.dealer_hand)

    async def on_timeout(self):
        while _bj_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
        winnings, result_text = _bj_resolve(self.player_hand, self.dealer_hand, self.bet)
        self.user.ajust_beans(winnings)
        DataStorage.save_user_data()
        embed = _bj_make_embed(self.player_hand, self.dealer_hand, hide_dealer=False,
                               result_text=result_text + " (timed out)")
        play_again_view = BlackjackPlayAgainView(self.ctx, self.bet)
        play_again_view.message = self.message
        if self.message:
            await self.message.edit(embed=embed, view=play_again_view)


class BlackjackPlayAgainView(discord.ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.message = None

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.green)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        user = DataStorage.get_or_create_user(self.ctx.author.id)
        if user.get_beans() < self.bet:
            button.disabled = True
            await interaction.response.edit_message(content="❌ Not enough beans to play again!", view=self)
            return

        deck, player_hand, dealer_hand = _bj_new_game()

        if _bj_hand_value(player_hand) == 21:
            winnings = int(self.bet * 1.5)
            user.ajust_beans(winnings)
            DataStorage.save_user_data()
            embed = _bj_make_embed(player_hand, dealer_hand, hide_dealer=False,
                                   result_text=f"🎰 BLACKJACK! +{winnings} beans")
            new_view = BlackjackPlayAgainView(self.ctx, self.bet)
            await interaction.response.edit_message(embed=embed, view=new_view)
            new_view.message = interaction.message
            return

        new_view = BlackjackView(self.ctx, user, self.bet, deck, player_hand, dealer_hand)
        await interaction.response.edit_message(
            embed=_bj_make_embed(player_hand, dealer_hand, hide_dealer=True), view=new_view)
        new_view.message = interaction.message

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)


async def blackjack(ctx, bet: int):
    """Play blackjack against the dealer."""
    user = DataStorage.get_or_create_user(ctx.author.id)

    if bet < 20:
        await ctx.send("Minimum bet is 20 beans.")
        return
    if bet > user.get_beans():
        await ctx.send(f"You don't have enough beans! Balance: {int(user.get_beans())}")
        return

    deck, player_hand, dealer_hand = _bj_new_game()

    if _bj_hand_value(player_hand) == 21:
        winnings = int(bet * 1.5)
        user.ajust_beans(winnings)
        DataStorage.save_user_data()
        embed = _bj_make_embed(player_hand, dealer_hand, hide_dealer=False,
                               result_text=f"🎰 BLACKJACK! +{winnings} beans")
        play_again_view = BlackjackPlayAgainView(ctx, bet)
        msg = await ctx.send(embed=embed, view=play_again_view)
        play_again_view.message = msg
        return

    view = BlackjackView(ctx, user, bet, deck, player_hand, dealer_hand)
    msg = await ctx.send(embed=_bj_make_embed(player_hand, dealer_hand, hide_dealer=True), view=view)
    view.message = msg


async def lottery(ctx):
    """Show the current lottery pot and your ticket count."""
    guild_id = str(ctx.guild.id)
    user = DataStorage.get_or_create_user(ctx.author.id)
    entries = DataStorage.get_lottery_entries(guild_id)
    pot = DataStorage.get_lottery_pot(guild_id)
    tickets_held = entries.get(str(ctx.author.id), 0)
    tickets_remaining = LOTTERY_MAX_TICKETS - tickets_held
    total_tickets = sum(entries.values())

    embed = discord.Embed(
        title="🎟️ Bean Lottery",
        description=(
            f"**Pot:** {int(pot):,} beans\n"
            f"**Total tickets sold:** {total_tickets}\n"
            f"**Your tickets:** {tickets_held} / {LOTTERY_MAX_TICKETS}\n"
            f"**Ticket cost:** {LOTTERY_TICKET_COST} beans each"
        ),
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Your Balance", value=f"{int(user.get_beans())} beans", inline=True)
    embed.add_field(name="🎫 Tickets Left to Buy", value=str(tickets_remaining), inline=True)

    if entries:
        top_entries = sorted(entries.items(), key=lambda x: x[1], reverse=True)[:10]
        lines = [f"<@{uid}> — {count} ticket(s)" for uid, count in top_entries]
        total_entrants = len(entries)
        field_name = "🎫 Top Entrants" if total_entrants > 10 else "🎫 Current Entrants"
        footer_note = f"Showing top 10 of {total_entrants} entrants. " if total_entrants > 10 else ""
        embed.add_field(name=field_name, value="\n".join(lines), inline=False)
    else:
        footer_note = ""
        embed.add_field(name="🎫 Current Entrants", value="No tickets sold yet.", inline=False)

    embed.set_footer(text=f"{footer_note}Use .lottery_buy <amount> to buy tickets!")
    await ctx.send(embed=embed)


async def lottery_buy(ctx, amount: int):
    """Buy lottery tickets."""
    guild_id = str(ctx.guild.id)
    user = DataStorage.get_or_create_user(ctx.author.id)
    user_id = str(ctx.author.id)

    if amount <= 0:
        await ctx.send("Please specify a positive number of tickets.")
        return

    entries = DataStorage.get_lottery_entries(guild_id)
    tickets_held = entries.get(user_id, 0)
    tickets_available = LOTTERY_MAX_TICKETS - tickets_held

    if tickets_available <= 0:
        await ctx.send(f"You already have the maximum of {LOTTERY_MAX_TICKETS} tickets this round!")
        return

    if amount > tickets_available:
        await ctx.send(f"You can only buy up to {tickets_available} more ticket(s) this round.")
        return

    total_cost = amount * LOTTERY_TICKET_COST
    if user.get_beans() < total_cost:
        embed = discord.Embed(
            title="❌ Insufficient Beans",
            description=f"{amount} ticket(s) costs **{total_cost}** beans, but you only have **{int(user.get_beans())}**.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    user.ajust_beans(-total_cost)
    DataStorage.lottery_entries.setdefault(guild_id, {})[user_id] = tickets_held + amount
    DataStorage.lottery_pot[guild_id] = DataStorage.get_lottery_pot(guild_id) + total_cost
    DataStorage.save_user_data()
    DataStorage.save_lottery()

    new_tickets = DataStorage.lottery_entries[guild_id][user_id]
    embed = discord.Embed(
        title="🎟️ Tickets Purchased!",
        description=f"You bought **{amount}** ticket(s) for **{total_cost}** beans.",
        color=discord.Color.green()
    )
    embed.add_field(name="Your Tickets", value=f"{new_tickets} / {LOTTERY_MAX_TICKETS}", inline=True)
    embed.add_field(name="Current Pot", value=f"{int(DataStorage.get_lottery_pot(guild_id)):,} beans", inline=True)
    embed.add_field(name="New Balance", value=f"{int(user.get_beans())} beans", inline=True)
    await ctx.send(embed=embed)


async def bank(ctx):
    """Show your bank balance, cap, and upgrade info."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    cap = BANK_UPGRADE_TIERS[user.bank_level]
    max_level = len(BANK_UPGRADE_TIERS) - 1

    embed = discord.Embed(
        title="🏦 Your Bank",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans()):,} beans", inline=True)
    embed.add_field(name="🏦 Bank Balance", value=f"{int(user.bank_balance):,} / {cap:,} beans", inline=True)

    if user.bank_level < max_level:
        next_cap = BANK_UPGRADE_TIERS[user.bank_level + 1]
        upgrade_cost = BANK_UPGRADE_COSTS[user.bank_level + 1]
        embed.add_field(
            name="⬆️ Next Upgrade",
            value=f"Cap {cap:,} → {next_cap:,} for **{upgrade_cost:,} beans**\nUse `.bank_upgrade` to purchase",
            inline=False
        )
    else:
        embed.add_field(name="⬆️ Upgrades", value="Max level reached!", inline=False)

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)


async def deposit(ctx, amount: int):
    """Move beans from wallet to bank."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    cap = BANK_UPGRADE_TIERS[user.bank_level]
    space = cap - user.bank_balance

    if amount <= 0:
        await ctx.send("Please specify a positive amount to deposit.")
        return
    if amount > user.get_beans():
        await ctx.send(f"You only have **{int(user.get_beans()):,}** beans in your wallet.")
        return
    if space <= 0:
        await ctx.send(f"Your bank is full! ({cap:,} / {cap:,}). Upgrade your bank to store more.")
        return
    if amount > space:
        await ctx.send(f"Your bank only has room for **{int(space):,}** more beans. Deposit that amount or upgrade your bank.")
        return

    user.ajust_beans(-amount)
    user.bank_balance = round(user.bank_balance + amount, 2)
    DataStorage.save_user_data()
    embed = discord.Embed(
        title="🏦 Deposit Successful",
        description=f"Deposited **{amount:,}** beans into your bank.",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans()):,} beans", inline=True)
    embed.add_field(name="🏦 Bank", value=f"{int(user.bank_balance):,} / {cap:,} beans", inline=True)
    await ctx.send(embed=embed)


async def withdraw(ctx, amount: int):
    """Move beans from bank to wallet."""
    user = DataStorage.get_or_create_user(ctx.author.id)

    if amount <= 0:
        await ctx.send("Please specify a positive amount to withdraw.")
        return
    if amount > user.bank_balance:
        await ctx.send(f"You only have **{int(user.bank_balance):,}** beans in your bank.")
        return

    user.bank_balance = round(user.bank_balance - amount, 2)
    user.ajust_beans(amount)
    DataStorage.save_user_data()

    cap = BANK_UPGRADE_TIERS[user.bank_level]
    embed = discord.Embed(
        title="🏦 Withdrawal Successful",
        description=f"Withdrew **{amount:,}** beans from your bank.",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans()):,} beans", inline=True)
    embed.add_field(name="🏦 Bank", value=f"{int(user.bank_balance):,} / {cap:,} beans", inline=True)
    await ctx.send(embed=embed)


async def bank_upgrade(ctx):
    """Purchase the next bank tier."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    max_level = len(BANK_UPGRADE_TIERS) - 1

    if user.bank_level >= max_level:
        await ctx.send("Your bank is already at the maximum level!")
        return

    next_level = user.bank_level + 1
    cost = BANK_UPGRADE_COSTS[next_level]
    new_cap = BANK_UPGRADE_TIERS[next_level]

    if user.get_beans() < cost:
        await ctx.send(f"You need **{cost:,}** beans in your wallet to upgrade, but only have **{int(user.get_beans()):,}**.")
        return

    user.ajust_beans(-cost)
    user.bank_level = next_level
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="⬆️ Bank Upgraded!",
        description=f"Your bank cap is now **{new_cap:,} beans** (Level {next_level}).",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans()):,} beans", inline=True)
    embed.add_field(name="🏦 New Cap", value=f"{new_cap:,} beans", inline=True)
    if next_level < max_level:
        embed.set_footer(text=f"Next upgrade: {BANK_UPGRADE_TIERS[next_level + 1]:,} cap for {BANK_UPGRADE_COSTS[next_level + 1]:,} beans")
    else:
        embed.set_footer(text="Max level reached!")
    await ctx.send(embed=embed)


async def rob(ctx, target: discord.Member):
    """Attempt to steal beans from another user's wallet."""
    author = ctx.author
    now = datetime.datetime.now()

    if target.id == author.id:
        await ctx.send("You can't rob yourself.")
        return
    if target.bot:
        await ctx.send("You can't rob a bot.")
        return

    robber = DataStorage.get_or_create_user(author.id)

    if robber.last_rob:
        cooldown = datetime.timedelta(minutes=ROB_COOLDOWN_MINUTES)
        elapsed = now - robber.last_rob
        if elapsed < cooldown:
            remaining = cooldown - elapsed
            minutes, seconds = divmod(int(remaining.total_seconds()), 60)
            embed = discord.Embed(
                title="🚔 Lay Low!",
                description=f"You recently attempted a robbery. Try again in **{minutes}m {seconds}s**.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

    victim = DataStorage.get_or_create_user(target.id)

    if victim.rob_immunity_until and now < victim.rob_immunity_until:
        remaining = victim.rob_immunity_until - now
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        embed = discord.Embed(
            title="🛡️ Target is Protected",
            description=f"{target.display_name} was recently robbed and is immune for **{minutes}m {seconds}s**.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    if victim.get_beans() < ROB_MIN_TARGET_WALLET:
        await ctx.send(f"{target.display_name} doesn't have enough beans in their wallet to rob (minimum {ROB_MIN_TARGET_WALLET}).")
        return

    robber.last_rob = now

    if random.random() < ROB_SUCCESS_RATE:
        steal_fraction = random.uniform(*ROB_STEAL_RANGE)
        stolen = min(int(victim.get_beans() * steal_fraction), ROB_STEAL_CAP)
        victim.ajust_beans(-stolen)
        robber.ajust_beans(stolen)
        victim.rob_immunity_until = now + datetime.timedelta(minutes=ROB_IMMUNITY_MINUTES)
        DataStorage.save_user_data()

        embed = discord.Embed(
            title="💰 Successful Heist!",
            description=f"You stole **{stolen:,}** beans from {target.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Your Wallet", value=f"{int(robber.get_beans()):,} beans", inline=True)
        embed.add_field(name=f"{target.display_name}'s Wallet", value=f"{int(victim.get_beans()):,} beans", inline=True)
        embed.set_footer(text=f"{target.display_name} is immune from robbery for {ROB_IMMUNITY_MINUTES} minutes.")
    else:
        robber.ajust_beans(-ROB_FAILURE_FINE)
        victim.ajust_beans(ROB_FAILURE_FINE)
        DataStorage.save_user_data()

        embed = discord.Embed(
            title="🚨 Caught Red-Handed!",
            description=f"Your robbery failed! You paid a **{ROB_FAILURE_FINE:,}** bean fine to {target.mention}.",
            color=discord.Color.red()
        )
        embed.add_field(name="Your Wallet", value=f"{int(robber.get_beans()):,} beans", inline=True)
        embed.add_field(name=f"{target.display_name}'s Wallet", value=f"{int(victim.get_beans()):,} beans", inline=True)

    await ctx.send(embed=embed)
