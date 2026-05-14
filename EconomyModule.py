import random
import asyncio
from typing import Optional

import DataStorage
import datetime
import discord
from Classes.RequestClass import Request


#Configuration Variables
BREW_COOLDOWN_TIME = 30 # Minutes
BEANS_PER_BREW = (10, 50) # Range between the two numbers
DAILY_REWARD_BASE = 100

LOTTERY_TICKET_COST = 50

bot = None  # Set by botMain after bot is created; used for auto-draw channel lookup

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
JACKPOT_CONTRIBUTION_RATE = 0.25
SLOTS_BASE_JACKPOT_MULTIPLIER = 226
BLACKJACK_LOSS_JACKPOT_RATE = 0.10

HILO_MIN_BET = 50
HILO_MULTIPLIER = 1.4
HILO_TIMEOUT = 30

ROULETTE_MIN_BET = 25
ROULETTE_RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
ROULETTE_BLACK = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}


async def beans(ctx):
    """Shows the current amount of beans the user has"""
    user = ctx.author
    user_data = DataStorage.get_or_create_user(user.id)
    guild_id = user_data.effective_guild_id(ctx)

    embed = discord.Embed(
        title="☕ Coffee Bean Balance",
        description=f"**{user.display_name}** has **{int(user_data.get_beans(guild_id))}** beans.",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    await ctx.send(embed=embed)


async def shift(ctx):
    """Works a shift providing the user with currency"""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    state = user.state(guild_id)
    current_time = datetime.datetime.now()


    # Check for cooldown
    if state.last_shift: # If the last_shift is none, we know its a new user and can proceed as there is no cooldown
        time_passed = current_time - state.last_shift
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
    user.ajust_beans(guild_id, beans_earned)
    user.set_last_shift(guild_id, current_time)
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="☕ Shift Complete!",
        description=f"You worked a shift at the cafe and earned **{beans_earned}** Beans!",
        color=discord.Color.from_rgb(111, 78, 55)  # Coffee brown
    )
    embed.add_field(name="💰 New Balance", value=f"**{int(user.get_beans(guild_id))}** beans", inline=False)
    embed.set_footer(text=f"Next shift available in {BREW_COOLDOWN_TIME} minutes")
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


async def tip(ctx, target: discord.Member, amount: float):
    """Sends a specified user some of your beans"""
    author = ctx.author
    author_id = author.id
    target_id = target.id
    guild_id = str(ctx.guild.id)

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

    if author_data.get_beans(guild_id) < amount:
        embed = discord.Embed(
            title="❌ Insufficient Beans",
            description=f"You only have **{int(author_data.get_beans(guild_id))}** beans, but tried to tip **{int(amount)}**.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    author_data.ajust_beans(guild_id, -1 * amount)
    target_data.ajust_beans(guild_id, amount)
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="💸 Tip Sent!",
        description=f"{ctx.author.mention} tipped **{int(amount)}** beans to {target.mention}!",
        color=discord.Color.green()
    )

    embed.add_field(name=f"{ctx.author.display_name}'s Balance", value=f"{int(author_data.get_beans(guild_id))} beans", inline=True)
    embed.add_field(name=f"{target.display_name}'s Balance", value=f"{int(target_data.get_beans(guild_id))} beans", inline=True)

    await ctx.send(embed=embed)


# ============================================================================
# Peer-to-peer betting (.bet / .betwinner / .cancelbet)
# ============================================================================
# Pending offers are stored as Request("bet", proposer_id, amount=N) on the
# TARGET'S state (parity with .marry/.adopt). Once accepted, the bet moves to
# active_bets, mirrored on both players' state and keyed by a canonical pair.

def _pair_key(a_id, b_id):
    lo, hi = sorted((int(a_id), int(b_id)))
    return f"{lo}:{hi}"


def _find_active_bets_for(user_obj, guild_id, user_id):
    """Return [(pair_key, record, other_id), ...] for active bets involving user_id."""
    out = []
    for k, v in user_obj.state(guild_id).active_bets.items():
        a, b = (int(x) for x in k.split(":"))
        if a == int(user_id) or b == int(user_id):
            other = b if a == int(user_id) else a
            out.append((k, v, other))
    return out


async def bet(ctx, target: discord.Member, amount: int, reason: Optional[str] = None):
    """Propose a peer-to-peer bet, or accept an incoming offer by matching the exact amount.
    Optional `reason` is stored with the offer and surfaces in resolution/cancellation embeds."""
    author = ctx.author
    guild_id = str(ctx.guild.id)

    if target.id == author.id:
        await ctx.send("You can't bet against yourself.")
        return

    if target.bot:
        await ctx.send("You can't bet against a bot.")
        return

    if amount <= 0:
        await ctx.send("Bet amount must be a positive number.")
        return

    author_data = DataStorage.get_or_create_user(author.id)
    target_data = DataStorage.get_or_create_user(target.id)

    if author_data.get_beans(guild_id) < amount:
        embed = discord.Embed(
            title="❌ Insufficient Beans",
            description=f"You only have **{int(author_data.get_beans(guild_id))}** beans, but tried to bet **{int(amount)}**.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    pair = _pair_key(author.id, target.id)

    # 1) Acceptance branch — is there a pending bet request from target in MY state?
    incoming = author_data.get_request(guild_id, "bet", target.id)
    if incoming is not None:
        offer_amount = int(incoming.get_amount() or 0)
        if offer_amount != amount:
            await ctx.send(
                f"{target.mention} offered you a bet of **{offer_amount}** beans, not **{amount}**. "
                f"Match their amount or use `.cancelbet {target.mention}` to decline."
            )
            return
        # Accept: escrow author's beans, drop the request, create active bet on both sides.
        # The offerer's reason carries over; an acceptor-supplied reason is ignored.
        offer_reason = incoming.get_reason()
        author_data.ajust_beans(guild_id, -1 * amount)
        author_data.remove_request_by_data(guild_id, "bet", target.id)
        record = {"amount": amount, "votes": {}, "reason": offer_reason}
        author_data.state(guild_id).active_bets[pair] = record
        target_data.state(guild_id).active_bets[pair] = record
        DataStorage.save_user_data()

        embed = discord.Embed(
            title="🤝 Bet Active!",
            description=(
                f"{author.mention} vs {target.mention} — **{amount}** beans each, "
                f"**{2 * amount}**-bean pot.\n\n"
                f"Both players must run `.betwinner <user>` naming the same winner to resolve. "
                f"Disagreement nulls the bet and refunds both."
            ),
            color=discord.Color.green()
        )
        if offer_reason:
            embed.add_field(name="Reason", value=offer_reason, inline=False)
        await ctx.send(embed=embed)
        return

    # 2) Already an active bet between us?
    if pair in author_data.state(guild_id).active_bets:
        existing = author_data.state(guild_id).active_bets[pair]
        await ctx.send(
            f"You already have an active bet with {target.mention} for **{int(existing['amount'])}** beans. "
            f"Resolve it with `.betwinner` or `.cancelbet {target.mention}` first."
        )
        return

    # 3) Already a pending offer from me to them? (My request lives in their state.)
    outgoing = target_data.get_request(guild_id, "bet", author.id)
    if outgoing is not None:
        existing_amount = int(outgoing.get_amount() or 0)
        await ctx.send(
            f"You've already offered {target.mention} a bet of **{existing_amount}** beans. "
            f"Use `.cancelbet {target.mention}` to drop it before offering a new one."
        )
        return

    # 4) New offer — escrow proposer's beans, store request on target's state
    author_data.ajust_beans(guild_id, -1 * amount)
    target_data.add_request(guild_id, "bet", Request("bet", author.id, amount=amount, reason=reason))
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="🎲 Bet Offered",
        description=(
            f"{author.mention} offers {target.mention} a **{amount}**-bean bet. "
            f"Beans escrowed.\n\n"
            f"{target.mention}: run `.bet {author.mention} {amount}` to accept, "
            f"or `.cancelbet {author.mention}` to decline.\n"
            f"{author.mention}: use `.cancelbet {target.mention}` to cancel and refund."
        ),
        color=discord.Color.gold()
    )
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=embed)


async def betwinner(ctx, winner: discord.Member, opponent: discord.Member = None):
    """Vote on the winner of an active bet. Agreement pays the winner; disagreement nulls and refunds."""
    invoker = ctx.author
    guild_id = str(ctx.guild.id)
    invoker_data = DataStorage.get_or_create_user(invoker.id)

    # Resolve which active bet
    if winner.id != invoker.id:
        pair_key = _pair_key(invoker.id, winner.id)
        record = invoker_data.state(guild_id).active_bets.get(pair_key)
        if record is None:
            await ctx.send(f"No active bet found between you and {winner.mention}.")
            return
        other_id = winner.id
        winner_id = winner.id
    else:
        # Self-claim
        if opponent is None:
            active = _find_active_bets_for(invoker_data, guild_id, invoker.id)
            if len(active) == 0:
                await ctx.send("You have no active bets.")
                return
            if len(active) > 1:
                mentions = ", ".join(f"<@{oid}>" for _, _, oid in active)
                await ctx.send(
                    f"You have multiple active bets (with {mentions}). "
                    f"Use `.betwinner {invoker.mention} <opponent>` to specify which bet you won."
                )
                return
            pair_key, record, other_id = active[0]
            winner_id = invoker.id
        else:
            if opponent.id == invoker.id:
                await ctx.send("Opponent can't be yourself.")
                return
            pair_key = _pair_key(invoker.id, opponent.id)
            record = invoker_data.state(guild_id).active_bets.get(pair_key)
            if record is None:
                await ctx.send(f"No active bet found with {opponent.mention}.")
                return
            other_id = opponent.id
            winner_id = invoker.id

    # Already voted?
    if str(invoker.id) in record["votes"]:
        prior = record["votes"][str(invoker.id)]
        await ctx.send(
            f"You already voted in this bet (for <@{prior}>). Waiting for <@{other_id}> to vote."
        )
        return

    # Record vote and mirror to opponent's state
    record["votes"][str(invoker.id)] = int(winner_id)
    other_data = DataStorage.get_or_create_user(other_id)
    other_data.state(guild_id).active_bets[pair_key] = record

    other_vote = record["votes"].get(str(other_id))
    amount = int(record["amount"])
    pot = 2 * amount

    if other_vote is None:
        DataStorage.save_user_data()
        await ctx.send(
            f"Vote recorded: <@{winner_id}> wins. Waiting for <@{other_id}> to vote with `.betwinner`."
        )
        return

    # Both voted — resolve
    bet_reason = record.get("reason")
    invoker_data.state(guild_id).active_bets.pop(pair_key, None)
    other_data.state(guild_id).active_bets.pop(pair_key, None)

    if other_vote == int(winner_id):
        winner_data = DataStorage.get_or_create_user(winner_id)
        winner_data.ajust_beans(guild_id, pot)
        DataStorage.save_user_data()
        embed = discord.Embed(
            title="🏆 Bet Resolved!",
            description=f"<@{winner_id}> wins **{pot}** beans!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Winner's Balance",
            value=f"{int(winner_data.get_beans(guild_id))} beans",
            inline=True
        )
        if bet_reason:
            embed.add_field(name="Reason", value=bet_reason, inline=False)
        await ctx.send(embed=embed)
    else:
        # Disagreement → refund both
        a, b = (int(x) for x in pair_key.split(":"))
        DataStorage.get_or_create_user(a).ajust_beans(guild_id, amount)
        DataStorage.get_or_create_user(b).ajust_beans(guild_id, amount)
        DataStorage.save_user_data()
        embed = discord.Embed(
            title="❌ Disagreement — Bet Nulled",
            description=(
                f"<@{a}> and <@{b}> couldn't agree on the winner. "
                f"Each player refunded **{amount}** beans."
            ),
            color=discord.Color.red()
        )
        if bet_reason:
            embed.add_field(name="Reason", value=bet_reason, inline=False)
        await ctx.send(embed=embed)


def _find_bet_counterparties(invoker_id, guild_id):
    """Return a set of other-user ids that the invoker has any pending offer or active bet with."""
    invoker_data = DataStorage.get_or_create_user(invoker_id)
    others = set()

    # Active bets — mirrored on invoker's state
    for _, _, other_id in _find_active_bets_for(invoker_data, guild_id, invoker_id):
        others.add(int(other_id))

    # Incoming offers — live on invoker's state
    for req in invoker_data.state(guild_id).requests.get("bet", []):
        others.add(int(req.get_user()))

    # Outgoing offers — invoker's request lives on each target's state; scan all users.
    for uid, u in DataStorage.user_data.items():
        if int(uid) == int(invoker_id):
            continue
        if u.get_request(guild_id, "bet", invoker_id) is not None:
            others.add(int(uid))

    return others


async def cancelbet(ctx, target: Optional[discord.Member] = None):
    """Cancel a pending offer, decline an incoming offer, or forfeit an active bet.
    With no target, auto-resolves when the invoker has exactly one bet relationship."""
    invoker = ctx.author
    guild_id = str(ctx.guild.id)

    # Auto-detect if no target given
    if target is None:
        others = _find_bet_counterparties(invoker.id, guild_id)
        if len(others) == 0:
            await ctx.send("You have no pending bet offers or active bets.")
            return
        if len(others) > 1:
            mentions = ", ".join(f"<@{oid}>" for oid in others)
            await ctx.send(
                f"You have bets with multiple users ({mentions}). "
                f"Specify which one: `.cancelbet <user>`."
            )
            return
        only_id = next(iter(others))
        if ctx.guild is not None:
            resolved = ctx.guild.get_member(only_id)
        else:
            resolved = None
        if resolved is None:
            try:
                resolved = await ctx.bot.fetch_user(only_id)
            except discord.HTTPException:
                resolved = None
        if resolved is None:
            await ctx.send("Couldn't resolve the other player. Use `.cancelbet <user>` to specify.")
            return
        target = resolved

    invoker_data = DataStorage.get_or_create_user(invoker.id)
    target_data = DataStorage.get_or_create_user(target.id)

    # 1) Cancel my outgoing offer — my Request lives in target's state.
    outgoing = target_data.get_request(guild_id, "bet", invoker.id)
    if outgoing is not None:
        amount = int(outgoing.get_amount() or 0)
        invoker_data.ajust_beans(guild_id, amount)
        target_data.remove_request_by_data(guild_id, "bet", invoker.id)
        DataStorage.save_user_data()
        await ctx.send(
            f"Cancelled your bet offer to {target.mention}. **{amount}** beans refunded."
        )
        return

    # 2) Decline an incoming offer — their Request lives in my state.
    incoming = invoker_data.get_request(guild_id, "bet", target.id)
    if incoming is not None:
        amount = int(incoming.get_amount() or 0)
        target_data.ajust_beans(guild_id, amount)
        invoker_data.remove_request_by_data(guild_id, "bet", target.id)
        DataStorage.save_user_data()
        await ctx.send(
            f"Declined {target.mention}'s bet offer. They've been refunded **{amount}** beans."
        )
        return

    # 3) Forfeit an active bet — opponent takes the pot.
    pair_key = _pair_key(invoker.id, target.id)
    record = invoker_data.state(guild_id).active_bets.get(pair_key)
    if record is not None:
        amount = int(record["amount"])
        pot = 2 * amount
        bet_reason = record.get("reason")
        target_data.ajust_beans(guild_id, pot)
        invoker_data.state(guild_id).active_bets.pop(pair_key, None)
        target_data.state(guild_id).active_bets.pop(pair_key, None)
        DataStorage.save_user_data()
        embed = discord.Embed(
            title="🏳️ Bet Forfeited",
            description=f"{invoker.mention} forfeited. {target.mention} wins the **{pot}**-bean pot.",
            color=discord.Color.orange()
        )
        if bet_reason:
            embed.add_field(name="Reason", value=bet_reason, inline=False)
        await ctx.send(embed=embed)
        return

    await ctx.send(f"You have no pending offer or active bet with {target.mention}.")


async def bean_top(ctx):
    """Lists the top ten richest users in this server by total beans (wallet + bank)"""
    user_saves = DataStorage.user_data
    guild_id = str(ctx.guild.id)

    def total_beans(u):
        gs = u.guild_data.get(guild_id)
        return (gs.beans + gs.bank_balance) if gs else 0

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
    guild_id = str(ctx.guild.id)

    total_beans = 0
    total_marriages = 0
    registered_users = 0
    for u in user_saves.values():
        gs = u.guild_data.get(guild_id)
        if not gs:
            continue
        total_beans += gs.beans + gs.bank_balance
        total_marriages += len(gs.marriage_partner)
        if gs.beans > 0 or gs.bank_balance > 0 or gs.marriage_partner or gs.adopted_children or gs.adopted_by:
            registered_users += 1
    total_marriages //= 2

    # Quotes are nested {guild_id: {author: [Quote]}}
    guild_quotes = DataStorage.quotes.get(guild_id, {})
    total_quotes = sum(len(q_list) for q_list in guild_quotes.values())
    total_authors = len(guild_quotes)

    embed = discord.Embed(
        title="☕ Cafe Status",
        description="A snapshot of this server's cafe activity!",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.add_field(name="💰 Beans in Circulation", value=f"{total_beans:,.0f}", inline=True)
    embed.add_field(name="👥 Active Users", value=str(registered_users), inline=True)
    embed.add_field(name="💍 Active Marriages", value=str(total_marriages), inline=True)
    embed.add_field(name="📖 Total Quotes", value=f"{total_quotes} from {total_authors} authors", inline=False)
    embed.set_footer(text="CafeBot | ☕")
    await ctx.send(embed=embed)


async def daily(ctx):
    """Claim a daily reward of Coffee Beans."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    state = user.state(guild_id)
    now = datetime.datetime.now()

    if state.last_daily:
        time_passed = now - state.last_daily
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
            state.daily_reward_streak = 0
            await ctx.send("You have lost your streak!")

    amount_to_reward = int(DAILY_REWARD_BASE * (1 + (state.daily_reward_streak * 0.02)))
    state.daily_reward_streak += 1
    user.ajust_beans(guild_id, amount_to_reward)
    state.last_daily = now
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="Daily Reward!",
        description=f"You claimed your daily allowance of **{amount_to_reward}** Coffee Beans! \n Your current streak is {state.daily_reward_streak} days!",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 New Balance", value=f"**{int(user.get_beans(guild_id))}** beans")
    embed.set_footer(text="See you tomorrow! ☕")
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


def _resolve_slots_outcome(guild_id, bet, reels):
    """Compute the slot outcome: net change to user beans, and result text.

    Mutates jackpot_pot as a side effect: every spin contributes
    `JACKPOT_CONTRIBUTION_RATE × bet` to the pool; triple 7s resets the pool
    when it pays the pool (i.e. when pool > floor).
    Returns (winnings, result_text) where winnings is the net change to beans.
    """
    DataStorage.add_to_jackpot(guild_id, bet * JACKPOT_CONTRIBUTION_RATE)
    DataStorage.save_jackpot()
    if reels[0] == reels[1] == reels[2]:
        if reels[0] == "7️⃣":
            pool = int(DataStorage.get_jackpot(guild_id))
            floor = SLOTS_BASE_JACKPOT_MULTIPLIER * bet
            if pool > floor:
                payout = pool
                DataStorage.reset_jackpot(guild_id)
                DataStorage.save_jackpot()
            else:
                payout = floor
            return payout - bet, f"🎰 JACKPOT! Triple 7s — won {payout:,} beans!"
        return int(bet * 26) - bet, "🎉 Three of a kind!"
    if reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        return bet, "✨ Two of a kind!"
    return -bet, "💸 No match. Better luck next time!"


async def slots(ctx, bet: int):
    """Spin the slot machine and bet Coffee Beans."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)

    if bet < 50:
        await ctx.send("Minimum bet is 50 beans.")
        return
    if bet > user.get_beans(guild_id):
        await ctx.send(f"You don't have enough beans! Balance: {int(user.get_beans(guild_id))}")
        return

    def spin_result():
        reels = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        display = " | ".join(reels)
        winnings, result_text = _resolve_slots_outcome(guild_id, bet, reels)
        return display, winnings, result_text

    def make_embed(display, winnings, result_text):
        color = discord.Color.gold() if winnings > 0 else discord.Color.red()
        embed = discord.Embed(title="🎰 Slot Machine", color=color)
        embed.add_field(name="Reels", value=display, inline=False)
        embed.add_field(name="Result", value=result_text, inline=False)
        embed.add_field(name="Bet", value=f"{bet} beans", inline=True)
        change = f"+{winnings}" if winnings >= 0 else str(winnings)
        embed.add_field(name="Change", value=f"{change} beans", inline=True)
        embed.add_field(name="New Balance", value=f"{int(user.get_beans(guild_id))} beans", inline=True)
        embed.add_field(name="🎰 Jackpot", value=f"{int(DataStorage.get_jackpot(guild_id)):,} beans", inline=False)
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
            if user.get_beans(guild_id) < bet:
                button.disabled = True
                await interaction.response.edit_message(content="❌ Not enough beans to play again!", view=self)
                return
            display, winnings, result_text = spin_result()
            user.ajust_beans(guild_id, winnings)
            DataStorage.save_user_data()
            await interaction.response.edit_message(embed=make_embed(display, winnings, result_text), view=self)

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.edit(view=self)

    display, winnings, result_text = spin_result()
    user.ajust_beans(guild_id, winnings)
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
        self.guild_id = user.effective_guild_id(ctx)
        self.user = user
        self.bet = bet
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.message = None

    async def end_game(self, interaction, final_player, final_dealer):
        winnings, result_text = _bj_resolve(final_player, final_dealer, self.bet)
        self.user.ajust_beans(self.guild_id, winnings)
        if winnings < 0:
            DataStorage.add_to_jackpot(self.guild_id, self.bet * BLACKJACK_LOSS_JACKPOT_RATE)
            DataStorage.save_jackpot()
        DataStorage.save_user_data()
        change = f"+{winnings}" if winnings >= 0 else str(winnings)
        result_text += f"\n**{change} beans** → Balance: {int(self.user.get_beans(self.guild_id))}"
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
        self.user.ajust_beans(self.guild_id, winnings)
        if winnings < 0:
            DataStorage.add_to_jackpot(self.guild_id, self.bet * BLACKJACK_LOSS_JACKPOT_RATE)
            DataStorage.save_jackpot()
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
        self.guild_id = DataStorage.get_or_create_user(ctx.author.id).effective_guild_id(ctx)
        self.bet = bet
        self.message = None

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.green)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        user = DataStorage.get_or_create_user(self.ctx.author.id)
        if user.get_beans(self.guild_id) < self.bet:
            button.disabled = True
            await interaction.response.edit_message(content="❌ Not enough beans to play again!", view=self)
            return

        deck, player_hand, dealer_hand = _bj_new_game()

        if _bj_hand_value(player_hand) == 21:
            winnings = int(self.bet * 1.5)
            user.ajust_beans(self.guild_id, winnings)
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
    guild_id = user.effective_guild_id(ctx)

    if bet < 20:
        await ctx.send("Minimum bet is 20 beans.")
        return
    if bet > user.get_beans(guild_id):
        await ctx.send(f"You don't have enough beans! Balance: {int(user.get_beans(guild_id))}")
        return

    deck, player_hand, dealer_hand = _bj_new_game()

    if _bj_hand_value(player_hand) == 21:
        winnings = int(bet * 1.5)
        user.ajust_beans(guild_id, winnings)
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


async def _execute_lottery_draw(guild_id, channel):
    """Draw a winner, award the pot, and reset lottery state. Posts result to channel."""
    guild_id = str(guild_id)
    entries = DataStorage.get_lottery_entries(guild_id)
    pot = DataStorage.get_lottery_pot(guild_id)

    population = list(entries.keys())
    weights = [entries[uid] for uid in population]
    winner_id = random.choices(population, weights=weights, k=1)[0]

    winner_data = DataStorage.get_or_create_user(int(winner_id))
    winner_data.ajust_beans(guild_id, pot)

    DataStorage.lottery_pot[guild_id] = 0.0
    DataStorage.lottery_entries[guild_id] = {}
    DataStorage.lottery_active.pop(guild_id, None)
    DataStorage.save_user_data()
    DataStorage.save_lottery()

    embed = discord.Embed(
        title="🎉 Lottery Draw!",
        description=f"<@{winner_id}> won the lottery and took home **{int(pot):,} beans**!",
        color=discord.Color.gold()
    )
    embed.set_footer(text="The pot has been reset. Start a new lottery with .admin_lottery_start!")
    await channel.send(embed=embed)


async def lottery(ctx):
    """Show the current lottery pot and your ticket count."""
    guild_id = str(ctx.guild.id)
    user = DataStorage.get_or_create_user(ctx.author.id)
    entries = DataStorage.get_lottery_entries(guild_id)
    pot = DataStorage.get_lottery_pot(guild_id)
    active = DataStorage.get_lottery_active(guild_id)
    tickets_held = entries.get(str(ctx.author.id), 0)
    total_tickets = sum(entries.values())

    if not active:
        embed = discord.Embed(
            title="🎟️ Bean Lottery",
            description="**No lottery is currently running.**\nAn admin can start one with `.admin_lottery_start`.",
            color=discord.Color.greyple()
        )
        if pot > 0 or entries:
            embed.add_field(name="Lingering Pot", value=f"{int(pot):,} beans", inline=True)
            embed.add_field(name="Tickets Sold", value=str(total_tickets), inline=True)
        await ctx.send(embed=embed)
        return

    max_per_user = active["max_per_user"]
    ticket_cap = active.get("ticket_cap")
    end_time = active.get("end_time")
    tickets_remaining = max_per_user - tickets_held

    cap_display = f"{total_tickets} / {ticket_cap}" if ticket_cap else f"{total_tickets} (no cap)"

    if end_time:
        end_dt = datetime.datetime.fromisoformat(end_time)
        now = datetime.datetime.now(datetime.timezone.utc)
        remaining_secs = max(0, int((end_dt - now).total_seconds()))
        if remaining_secs >= 3600:
            time_display = f"{remaining_secs // 3600}h {(remaining_secs % 3600) // 60}m remaining"
        elif remaining_secs >= 60:
            time_display = f"{remaining_secs // 60}m {remaining_secs % 60}s remaining"
        else:
            time_display = f"{remaining_secs}s remaining"
    else:
        time_display = "No time limit"

    embed = discord.Embed(
        title="🎟️ Bean Lottery",
        description=(
            f"**Pot:** {int(pot):,} beans\n"
            f"**Tickets sold:** {cap_display}\n"
            f"**Your tickets:** {tickets_held} / {max_per_user}\n"
            f"**Ticket cost:** {LOTTERY_TICKET_COST} beans each\n"
            f"**Time:** {time_display}"
        ),
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Your Balance", value=f"{int(user.get_beans(guild_id))} beans", inline=True)
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
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    user_id = str(ctx.author.id)

    active = DataStorage.get_lottery_active(guild_id)
    if not active:
        await ctx.send("No lottery is currently running. Wait for an admin to start one!")
        return

    if amount <= 0:
        await ctx.send("Please specify a positive number of tickets.")
        return

    max_per_user = active["max_per_user"]
    entries = DataStorage.get_lottery_entries(guild_id)
    tickets_held = entries.get(user_id, 0)
    tickets_available = max_per_user - tickets_held

    if tickets_available <= 0:
        await ctx.send(f"You already have the maximum of {max_per_user} tickets this round!")
        return

    if amount > tickets_available:
        await ctx.send(f"You can only buy up to {tickets_available} more ticket(s) this round.")
        return

    total_cost = amount * LOTTERY_TICKET_COST
    if user.get_beans(guild_id) < total_cost:
        embed = discord.Embed(
            title="❌ Insufficient Beans",
            description=f"{amount} ticket(s) costs **{total_cost}** beans, but you only have **{int(user.get_beans(guild_id))}**.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    user.ajust_beans(guild_id, -total_cost)
    DataStorage.lottery_entries.setdefault(guild_id, {})[user_id] = tickets_held + amount
    DataStorage.lottery_pot[guild_id] = DataStorage.get_lottery_pot(guild_id) + total_cost
    DataStorage.save_user_data()
    DataStorage.save_lottery()

    new_tickets = DataStorage.lottery_entries[guild_id][user_id]
    total_tickets = sum(DataStorage.lottery_entries[guild_id].values())
    embed = discord.Embed(
        title="🎟️ Tickets Purchased!",
        description=f"You bought **{amount}** ticket(s) for **{total_cost}** beans.",
        color=discord.Color.green()
    )
    embed.add_field(name="Your Tickets", value=f"{new_tickets} / {max_per_user}", inline=True)
    embed.add_field(name="Current Pot", value=f"{int(DataStorage.get_lottery_pot(guild_id)):,} beans", inline=True)
    embed.add_field(name="New Balance", value=f"{int(user.get_beans(guild_id))} beans", inline=True)
    await ctx.send(embed=embed)

    ticket_cap = active.get("ticket_cap")
    if ticket_cap and total_tickets >= ticket_cap:
        channel = bot.get_channel(int(active["channel_id"]))
        if channel:
            await channel.send("🎰 All tickets sold! Drawing the winner now...")
            await _execute_lottery_draw(guild_id, channel)


async def bank(ctx):
    """Show your bank balance, cap, and upgrade info."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    state = user.state(guild_id)
    cap = BANK_UPGRADE_TIERS[state.bank_level]
    max_level = len(BANK_UPGRADE_TIERS) - 1

    embed = discord.Embed(
        title="🏦 Your Bank",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans(guild_id)):,} beans", inline=True)
    embed.add_field(name="🏦 Bank Balance", value=f"{int(state.bank_balance):,} / {cap:,} beans", inline=True)

    if state.bank_level < max_level:
        next_cap = BANK_UPGRADE_TIERS[state.bank_level + 1]
        upgrade_cost = BANK_UPGRADE_COSTS[state.bank_level + 1]
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
    guild_id = user.effective_guild_id(ctx)
    state = user.state(guild_id)
    cap = BANK_UPGRADE_TIERS[state.bank_level]
    space = cap - state.bank_balance

    if amount <= 0:
        await ctx.send("Please specify a positive amount to deposit.")
        return
    if amount > user.get_beans(guild_id):
        await ctx.send(f"You only have **{int(user.get_beans(guild_id)):,}** beans in your wallet.")
        return
    if space <= 0:
        await ctx.send(f"Your bank is full! ({cap:,} / {cap:,}). Upgrade your bank to store more.")
        return
    if amount > space:
        await ctx.send(f"Your bank only has room for **{int(space):,}** more beans. Deposit that amount or upgrade your bank.")
        return

    user.ajust_beans(guild_id, -amount)
    state.bank_balance = round(state.bank_balance + amount, 2)
    DataStorage.save_user_data()
    embed = discord.Embed(
        title="🏦 Deposit Successful",
        description=f"Deposited **{amount:,}** beans into your bank.",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans(guild_id)):,} beans", inline=True)
    embed.add_field(name="🏦 Bank", value=f"{int(state.bank_balance):,} / {cap:,} beans", inline=True)
    await ctx.send(embed=embed)


async def withdraw(ctx, amount: int):
    """Move beans from bank to wallet."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    state = user.state(guild_id)

    if amount <= 0:
        await ctx.send("Please specify a positive amount to withdraw.")
        return
    if amount > state.bank_balance:
        await ctx.send(f"You only have **{int(state.bank_balance):,}** beans in your bank.")
        return

    state.bank_balance = round(state.bank_balance - amount, 2)
    user.ajust_beans(guild_id, amount)
    DataStorage.save_user_data()

    cap = BANK_UPGRADE_TIERS[state.bank_level]
    embed = discord.Embed(
        title="🏦 Withdrawal Successful",
        description=f"Withdrew **{amount:,}** beans from your bank.",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans(guild_id)):,} beans", inline=True)
    embed.add_field(name="🏦 Bank", value=f"{int(state.bank_balance):,} / {cap:,} beans", inline=True)
    await ctx.send(embed=embed)


async def bank_upgrade(ctx):
    """Purchase the next bank tier."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    state = user.state(guild_id)
    max_level = len(BANK_UPGRADE_TIERS) - 1

    if state.bank_level >= max_level:
        await ctx.send("Your bank is already at the maximum level!")
        return

    next_level = state.bank_level + 1
    cost = BANK_UPGRADE_COSTS[next_level]
    new_cap = BANK_UPGRADE_TIERS[next_level]

    if user.get_beans(guild_id) < cost:
        await ctx.send(f"You need **{cost:,}** beans in your wallet to upgrade, but only have **{int(user.get_beans(guild_id)):,}**.")
        return

    user.ajust_beans(guild_id, -cost)
    state.bank_level = next_level
    DataStorage.save_user_data()

    embed = discord.Embed(
        title="⬆️ Bank Upgraded!",
        description=f"Your bank cap is now **{new_cap:,} beans** (Level {next_level}).",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Wallet", value=f"{int(user.get_beans(guild_id)):,} beans", inline=True)
    embed.add_field(name="🏦 New Cap", value=f"{new_cap:,} beans", inline=True)
    if next_level < max_level:
        embed.set_footer(text=f"Next upgrade: {BANK_UPGRADE_TIERS[next_level + 1]:,} cap for {BANK_UPGRADE_COSTS[next_level + 1]:,} beans")
    else:
        embed.set_footer(text="Max level reached!")
    await ctx.send(embed=embed)


async def rob(ctx, target: discord.Member):
    """Attempt to steal beans from another user's wallet."""
    author = ctx.author
    guild_id = str(ctx.guild.id)
    now = datetime.datetime.now()

    if target.id == author.id:
        await ctx.send("You can't rob yourself.")
        return
    if target.bot:
        await ctx.send("You can't rob a bot.")
        return

    robber = DataStorage.get_or_create_user(author.id)
    robber_state = robber.state(guild_id)

    if robber_state.last_rob:
        cooldown = datetime.timedelta(minutes=ROB_COOLDOWN_MINUTES)
        elapsed = now - robber_state.last_rob
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
    victim_state = victim.state(guild_id)

    if victim_state.rob_immunity_until and now < victim_state.rob_immunity_until:
        remaining = victim_state.rob_immunity_until - now
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        embed = discord.Embed(
            title="🛡️ Target is Protected",
            description=f"{target.display_name} was recently robbed and is immune for **{minutes}m {seconds}s**.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    if victim.get_beans(guild_id) < ROB_MIN_TARGET_WALLET:
        await ctx.send(f"{target.display_name} doesn't have enough beans in their wallet to rob (minimum {ROB_MIN_TARGET_WALLET}).")
        return

    robber_state.last_rob = now

    if random.random() < ROB_SUCCESS_RATE:
        steal_fraction = random.uniform(*ROB_STEAL_RANGE)
        stolen = min(int(victim.get_beans(guild_id) * steal_fraction), ROB_STEAL_CAP)
        victim.ajust_beans(guild_id, -stolen)
        robber.ajust_beans(guild_id, stolen)
        victim_state.rob_immunity_until = now + datetime.timedelta(minutes=ROB_IMMUNITY_MINUTES)
        DataStorage.save_user_data()

        embed = discord.Embed(
            title="💰 Successful Heist!",
            description=f"You stole **{stolen:,}** beans from {target.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Your Wallet", value=f"{int(robber.get_beans(guild_id)):,} beans", inline=True)
        embed.add_field(name=f"{target.display_name}'s Wallet", value=f"{int(victim.get_beans(guild_id)):,} beans", inline=True)
        embed.set_footer(text=f"{target.display_name} is immune from robbery for {ROB_IMMUNITY_MINUTES} minutes.")
    else:
        robber.ajust_beans(guild_id, -ROB_FAILURE_FINE)
        victim.ajust_beans(guild_id, ROB_FAILURE_FINE)
        DataStorage.save_user_data()

        embed = discord.Embed(
            title="🚨 Caught Red-Handed!",
            description=f"Your robbery failed! You paid a **{ROB_FAILURE_FINE:,}** bean fine to {target.mention}.",
            color=discord.Color.red()
        )
        embed.add_field(name="Your Wallet", value=f"{int(robber.get_beans(guild_id)):,} beans", inline=True)
        embed.add_field(name=f"{target.display_name}'s Wallet", value=f"{int(victim.get_beans(guild_id)):,} beans", inline=True)

    await ctx.send(embed=embed)


# --- HI-LO ---

_HILO_RANK_LABELS = {11: "J", 12: "Q", 13: "K", 14: "A"}


def _hilo_rank_label(r: int) -> str:
    return _HILO_RANK_LABELS.get(r, str(r))


class HiLoView(discord.ui.View):
    def __init__(self, ctx, user, bet):
        super().__init__(timeout=HILO_TIMEOUT)
        self.ctx = ctx
        self.user = user
        self.guild_id = user.effective_guild_id(ctx)
        self.bet = bet
        self.current_card = random.randint(2, 14)
        self.multiplier = 1.0
        self.guesses_made = 0
        self.message = None
        self.cash_out.disabled = True

    def _embed(self, status: str) -> discord.Embed:
        e = discord.Embed(title="🃏 Hi-Lo", description=status, color=discord.Color.dark_gold())
        e.add_field(name="Card", value=f"**{_hilo_rank_label(self.current_card)}**", inline=True)
        e.add_field(name="Bet", value=f"{self.bet:,}", inline=True)
        e.add_field(name="Multiplier", value=f"×{self.multiplier:.2f}", inline=True)
        return e

    async def _resolve(self, interaction: discord.Interaction, direction: str):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        next_card = random.randint(2, 14)
        if next_card == self.current_card:
            self.current_card = next_card
            await interaction.response.edit_message(
                embed=self._embed(f"🤝 Push! Same rank ({_hilo_rank_label(next_card)}) — pick again."),
                view=self,
            )
            return
        won = (next_card > self.current_card and direction == "higher") or \
              (next_card < self.current_card and direction == "lower")
        previous = self.current_card
        self.current_card = next_card
        if won:
            self.guesses_made += 1
            self.multiplier *= HILO_MULTIPLIER
            self.cash_out.disabled = False
            await interaction.response.edit_message(
                embed=self._embed(
                    f"✅ Correct! ({_hilo_rank_label(previous)} → {_hilo_rank_label(next_card)}) "
                    f"Multiplier ×{self.multiplier:.2f}"
                ),
                view=self,
            )
        else:
            self.user.ajust_beans(self.guild_id, -self.bet)
            DataStorage.save_user_data()
            play_again_view = HiLoPlayAgainView(self.ctx, self.bet)
            await interaction.response.edit_message(
                embed=self._embed(
                    f"💥 Bust! ({_hilo_rank_label(previous)} → {_hilo_rank_label(next_card)}) "
                    f"Lost {self.bet:,} beans."
                ),
                view=play_again_view,
            )
            play_again_view.message = interaction.message
            self.stop()

    @discord.ui.button(label="Higher", emoji="⬆️", style=discord.ButtonStyle.primary)
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "higher")

    @discord.ui.button(label="Lower", emoji="⬇️", style=discord.ButtonStyle.primary)
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "lower")

    @discord.ui.button(label="Cash Out", emoji="💰", style=discord.ButtonStyle.success)
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        if self.guesses_made == 0:
            await interaction.response.send_message("You must guess at least once before cashing out.", ephemeral=True)
            return
        payout = int(self.bet * self.multiplier)
        winnings = payout - self.bet
        self.user.ajust_beans(self.guild_id, winnings)
        DataStorage.save_user_data()
        play_again_view = HiLoPlayAgainView(self.ctx, self.bet)
        await interaction.response.edit_message(
            embed=self._embed(f"💰 Cashed out! +{winnings:,} beans (×{self.multiplier:.2f})"),
            view=play_again_view,
        )
        play_again_view.message = interaction.message
        self.stop()

    async def on_timeout(self):
        if self.guesses_made == 0 or self.message is None:
            return
        payout = int(self.bet * self.multiplier)
        winnings = payout - self.bet
        self.user.ajust_beans(self.guild_id, winnings)
        DataStorage.save_user_data()
        play_again_view = HiLoPlayAgainView(self.ctx, self.bet)
        try:
            await self.message.edit(
                embed=self._embed(f"⏱️ Auto-cashed out: +{winnings:,} beans (×{self.multiplier:.2f})"),
                view=play_again_view,
            )
            play_again_view.message = self.message
        except discord.DiscordException:
            pass


class HiLoPlayAgainView(discord.ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.guild_id = DataStorage.get_or_create_user(ctx.author.id).effective_guild_id(ctx)
        self.message = None

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.green)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        user = DataStorage.get_or_create_user(self.ctx.author.id)
        if user.get_beans(self.guild_id) < self.bet:
            button.disabled = True
            await interaction.response.edit_message(content="❌ Not enough beans to play again.", view=self)
            return
        new_view = HiLoView(self.ctx, user, self.bet)
        await interaction.response.edit_message(
            embed=new_view._embed("Higher or lower? You must guess at least once before cashing out."),
            view=new_view,
        )
        new_view.message = interaction.message

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.DiscordException:
                pass


async def hilo(ctx, bet: int):
    """Press-your-luck Hi-Lo card game."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    if bet < HILO_MIN_BET:
        await ctx.send(f"Minimum bet is {HILO_MIN_BET} beans.")
        return
    if user.get_beans(guild_id) < bet:
        await ctx.send("❌ You don't have enough beans for that bet.")
        return
    view = HiLoView(ctx, user, bet)
    msg = await ctx.send(
        embed=view._embed("Higher or lower? You must guess at least once before cashing out."),
        view=view,
    )
    view.message = msg


# --- ROULETTE ---


def parse_roulette_choice(s: str):
    """Parse a roulette choice string.
    Returns (label, payout_multiplier, predicate) or (None, 0, None) on invalid.
    payout_multiplier is the total multiplier applied to bet on a win
    (e.g. 36 for a single number = 35:1 plus the original bet returned)."""
    s = s.strip().lower()
    if s.isdigit() and 0 <= int(s) <= 36:
        n = int(s)
        return (f"#{n}", 36, lambda r, _n=n: r == _n)
    if s == "red":
        return ("Red", 2, lambda r: r in ROULETTE_RED)
    if s == "black":
        return ("Black", 2, lambda r: r in ROULETTE_BLACK)
    if s == "even":
        return ("Even", 2, lambda r: r != 0 and r % 2 == 0)
    if s == "odd":
        return ("Odd", 2, lambda r: r != 0 and r % 2 == 1)
    if s == "low":
        return ("Low (1-18)", 2, lambda r: 1 <= r <= 18)
    if s == "high":
        return ("High (19-36)", 2, lambda r: 19 <= r <= 36)
    if s in ("1st12", "first12"):
        return ("1st 12", 3, lambda r: 1 <= r <= 12)
    if s in ("2nd12", "second12"):
        return ("2nd 12", 3, lambda r: 13 <= r <= 24)
    if s in ("3rd12", "third12"):
        return ("3rd 12", 3, lambda r: 25 <= r <= 36)
    if s == "col1":
        return ("Column 1", 3, lambda r: r != 0 and r % 3 == 1)
    if s == "col2":
        return ("Column 2", 3, lambda r: r != 0 and r % 3 == 2)
    if s == "col3":
        return ("Column 3", 3, lambda r: r != 0 and r % 3 == 0)
    return (None, 0, None)


async def _resolve_roulette_spin(message, user, guild_id, bet, choice_str, ctx):
    """Run the full spin sequence on the given message: edit to spin embed, sleep, edit to outcome + Play Again."""
    label, payout, predicate = parse_roulette_choice(choice_str)
    spin_embed = discord.Embed(
        title="🎰 Roulette",
        description=f"Spinning the wheel... **{label}**, {bet:,} beans",
        color=discord.Color.dark_red(),
    )
    try:
        await message.edit(embed=spin_embed, view=None)
    except discord.DiscordException:
        pass
    await asyncio.sleep(2)

    result = random.randint(0, 36)
    color_emoji = "🟢" if result == 0 else ("🔴" if result in ROULETTE_RED else "⚫")
    won = predicate(result)
    if won:
        gross = bet * payout
        net = gross - bet
        user.ajust_beans(guild_id, gross)
        DataStorage.save_user_data()
        outcome_embed = discord.Embed(
            title="🎰 Roulette",
            description=f"{color_emoji} **{result}** — {label} hit! **+{net:,} beans**",
            color=discord.Color.green(),
        )
    else:
        outcome_embed = discord.Embed(
            title="🎰 Roulette",
            description=f"{color_emoji} **{result}** — {label} missed. **-{bet:,} beans**",
            color=discord.Color.red(),
        )
    outcome_embed.set_footer(text=f"Wallet: {int(user.get_beans(guild_id)):,} beans")
    play_view = RoulettePlayAgainView(ctx, bet, choice_str)
    try:
        await message.edit(embed=outcome_embed, view=play_view)
        play_view.message = message
    except discord.DiscordException:
        pass


class RouletteBetView(discord.ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.message = None

    async def _check_owner(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return False
        return True

    async def _start_spin(self, interaction, choice_str):
        user = DataStorage.get_or_create_user(self.ctx.author.id)
        guild_id = user.effective_guild_id(self.ctx)
        if user.get_beans(guild_id) < self.bet:
            await interaction.response.send_message("❌ Not enough beans for that bet.", ephemeral=True)
            return
        user.ajust_beans(guild_id, -self.bet)
        DataStorage.save_user_data()
        for item in self.children:
            item.disabled = True
        await interaction.response.defer()
        await _resolve_roulette_spin(interaction.message, user, guild_id, self.bet, choice_str, self.ctx)
        self.stop()

    @discord.ui.button(label="Red", style=discord.ButtonStyle.danger, row=0)
    async def red(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "red")

    @discord.ui.button(label="Black", style=discord.ButtonStyle.secondary, row=0)
    async def black(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "black")

    @discord.ui.button(label="Even", style=discord.ButtonStyle.primary, row=0)
    async def even(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "even")

    @discord.ui.button(label="Odd", style=discord.ButtonStyle.primary, row=0)
    async def odd(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "odd")

    @discord.ui.button(label="Low (1-18)", style=discord.ButtonStyle.primary, row=1)
    async def low(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "low")

    @discord.ui.button(label="High (19-36)", style=discord.ButtonStyle.primary, row=1)
    async def high(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "high")

    @discord.ui.button(label="1st 12", style=discord.ButtonStyle.secondary, row=1)
    async def first12(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "1st12")

    @discord.ui.button(label="2nd 12", style=discord.ButtonStyle.secondary, row=1)
    async def second12(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "2nd12")

    @discord.ui.button(label="3rd 12", style=discord.ButtonStyle.secondary, row=1)
    async def third12(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "3rd12")

    @discord.ui.button(label="Col 1", style=discord.ButtonStyle.secondary, row=2)
    async def col1(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "col1")

    @discord.ui.button(label="Col 2", style=discord.ButtonStyle.secondary, row=2)
    async def col2(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "col2")

    @discord.ui.button(label="Col 3", style=discord.ButtonStyle.secondary, row=2)
    async def col3(self, interaction, button):
        if await self._check_owner(interaction):
            await self._start_spin(interaction, "col3")

    @discord.ui.button(label="Pick Number", emoji="🔢", style=discord.ButtonStyle.success, row=2)
    async def pick_number(self, interaction, button):
        if await self._check_owner(interaction):
            await interaction.response.send_modal(RouletteNumberModal(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.DiscordException:
                pass


class RouletteNumberModal(discord.ui.Modal, title="🎰 Pick a Number"):
    number_input = discord.ui.TextInput(
        label="Number (0-36)",
        placeholder="e.g. 17",
        min_length=1,
        max_length=2,
        required=True,
    )

    def __init__(self, parent_view: RouletteBetView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            n = int(self.number_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Invalid number — must be 0-36.", ephemeral=True)
            return
        if not 0 <= n <= 36:
            await interaction.response.send_message("❌ Number must be 0-36.", ephemeral=True)
            return
        user = DataStorage.get_or_create_user(self.parent_view.ctx.author.id)
        guild_id = user.effective_guild_id(self.parent_view.ctx)
        if user.get_beans(guild_id) < self.parent_view.bet:
            await interaction.response.send_message("❌ Not enough beans for that bet.", ephemeral=True)
            return
        user.ajust_beans(guild_id, -self.parent_view.bet)
        DataStorage.save_user_data()
        for item in self.parent_view.children:
            item.disabled = True
        await interaction.response.defer()
        if self.parent_view.message:
            await _resolve_roulette_spin(self.parent_view.message, user, guild_id, self.parent_view.bet, str(n), self.parent_view.ctx)
        self.parent_view.stop()


class RoulettePlayAgainView(discord.ui.View):
    def __init__(self, ctx, bet, choice_str):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.choice_str = choice_str
        self.message = None

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.green)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        user = DataStorage.get_or_create_user(self.ctx.author.id)
        guild_id = user.effective_guild_id(self.ctx)
        if user.get_beans(guild_id) < self.bet:
            button.disabled = True
            await interaction.response.edit_message(content="❌ Not enough beans to play again.", view=self)
            return
        user.ajust_beans(guild_id, -self.bet)
        DataStorage.save_user_data()
        await interaction.response.defer()
        await _resolve_roulette_spin(interaction.message, user, guild_id, self.bet, self.choice_str, self.ctx)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.DiscordException:
                pass


async def roulette(ctx, bet: int):
    """Open the Roulette bet picker."""
    user = DataStorage.get_or_create_user(ctx.author.id)
    guild_id = user.effective_guild_id(ctx)
    if bet < ROULETTE_MIN_BET:
        await ctx.send(f"Minimum bet is {ROULETTE_MIN_BET} beans.")
        return
    if user.get_beans(guild_id) < bet:
        await ctx.send("❌ You don't have enough beans for that bet.")
        return
    embed = discord.Embed(
        title="🎰 Roulette",
        description=f"**Bet: {bet:,} beans**\n\nPick your bet type below.",
        color=discord.Color.dark_red(),
    )
    embed.add_field(name="Outside (1:1)", value="🔴 Red · ⚫ Black · Even · Odd · Low · High", inline=False)
    embed.add_field(name="Dozens & Columns (2:1)", value="1st / 2nd / 3rd 12 · Col 1 / 2 / 3", inline=False)
    embed.add_field(name="Single Number (35:1)", value="🔢 Pick Number → enter 0-36", inline=False)
    view = RouletteBetView(ctx, bet)
    msg = await ctx.send(embed=embed, view=view)
    view.message = msg
