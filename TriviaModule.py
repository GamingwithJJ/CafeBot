import discord
import asyncio
import random
import DataStorage
import TriviaMatching


def grade(guess: str, answers: list, ctx, question: str) -> bool:
    """
    Thin grading helper: delegates to TriviaMatching.verdict, fires the
    gray-zone logger for borderline guesses, and returns the boolean result.
    """
    result = TriviaMatching.verdict(guess, answers)
    guild_id = str(ctx.guild.id) if ctx.guild else ""
    TriviaMatching.log_gray(guild_id, question, answers, guess, result)
    return result["correct"]


def get_question_timeout(question_text: str, acceptable_answers: list) -> int:
    # Answer length determines question time in tiers
    q_words = len(question_text.split())
    if q_words <= 10:
        base = 15
    elif q_words <= 20:
        base = 20
    else:
        base = 30

    # Answer length can add to the question time
    min_answer_words = min(len(a.split()) for a in acceptable_answers)
    if min_answer_words >= 7:
        bonus = 10
    elif min_answer_words >= 4:
        bonus = 5
    else:
        bonus = 0

    return base + bonus

active_trivia_channels = []  # List of channel id's currently with ongoing trivia


class TriviaConfigView(discord.ui.View):
    def __init__(self, user_data):
        super().__init__(timeout=120)  # Menu expires after 2 minutes
        self.user_data = user_data

        # Build the dropdown options dynamically from the TRIVIA_BANK
        options = []
        for category in DataStorage.trivia_questions.keys():
            # Check the box if they already have it enabled in their save file
            is_enabled = category in self.user_data.enabled_trivia_categories
            options.append(
                discord.SelectOption(label=category.capitalize(), value=category, default=is_enabled)
            )

        # Create the dropdown menu
        self.select_menu = discord.ui.Select(
            placeholder="Select which categories to enable...",
            min_values=1,  # Must have at least 1 category enabled
            max_values=len(options),
            options=options
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    # What happens when they make a selection
    async def select_callback(self, interaction: discord.Interaction):
        # Only the person who ran the command can click the menu
        if interaction.user.id != int(self.user_data.discord_id):
            await interaction.response.send_message("❌ This is not your menu!", ephemeral=True)
            return

        # Save their new selections to their user profile
        self.user_data.enabled_trivia_categories = self.select_menu.values
        DataStorage.save_user_data()

        await interaction.response.send_message(f"✅ Your trivia categories have been updated!", ephemeral=True)


async def open_config(ctx, user_data):
    """Opens the interactive config menu for the user."""
    embed = discord.Embed(
        title="⚙️ Trivia Configuration",
        description= f"\nUse the menu below to toggle which categories appear in your games!",
        color=discord.Color.gold()
    )
    view = TriviaConfigView(user_data)
    await ctx.send(embed=embed, view=view)


async def start_session(ctx, rounds: int, user_data):
    if ctx.channel.id in active_trivia_channels:
        await ctx.send("🚫 A trivia session is already happening in this channel!")
        return

    # 1. Gather Questions based on USER CONFIG
    available_questions = []

    for category in user_data.enabled_trivia_categories:
        if category in DataStorage.trivia_questions:
            for sub_category, questions in DataStorage.trivia_questions[category].items():
                for q in questions:
                    available_questions.append((category, sub_category, q[0], q[1]))

    if len(available_questions) < rounds:
        await ctx.send(
            f"⚠️ You requested {rounds} rounds, but your enabled categories only have {len(available_questions)} questions available! Please enable more categories or lower the round count.")
        return

    # Lock the channel
    active_trivia_channels.append(ctx.channel.id)
    scores = {}

    enabled_cats_string = ", ".join([c.capitalize() for c in user_data.enabled_trivia_categories])
    await ctx.send(
        f"🎉 **Trivia Session Starting!**\n**Enabled Topics:** {enabled_cats_string}\n**Rounds:** {rounds}\nThe first person to type the correct answer wins the round. Get ready...")
    await asyncio.sleep(3)

    selected_questions = random.sample(available_questions, rounds)

    try:
        # 2. The Game Loop
        for round_num, chosen_item in enumerate(selected_questions, start=1):

            chosen_category, sub_category, question_text, acceptable_answers = chosen_item

            timeout = get_question_timeout(question_text, acceptable_answers)

            embed = discord.Embed(
                title=f"Round {round_num} of {rounds}",
                description=f"**{question_text}**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"📂 {chosen_category.capitalize()} → {sub_category.capitalize()} • You have {timeout}s to answer!")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel == ctx.channel and not m.author.bot

            try:
                deadline = asyncio.get_event_loop().time() + timeout
                while True:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        raise asyncio.TimeoutError
                    msg = await ctx.bot.wait_for('message', timeout=remaining, check=check)

                    if grade(msg.content, acceptable_answers, ctx, question_text):
                        official_answer = acceptable_answers[0].capitalize()
                        await ctx.send(
                            f"✅ **{msg.author.display_name}** got it right! The answer was: {official_answer}")

                        scores[msg.author] = scores.get(msg.author, 0) + 1
                        DataStorage.get_or_create_user(msg.author.id).state(str(ctx.guild.id)).trivia_correct += 1
                        break

            except asyncio.TimeoutError:
                official_answer = acceptable_answers[0].capitalize()
                await ctx.send(f"⏳ Time's up! Nobody got it. The answer was: **{official_answer}**")

            await asyncio.sleep(2)

    finally:
        # 3. The Finale
        active_trivia_channels.remove(ctx.channel.id)

        if not scores:
            await ctx.send("🛑 **Trivia Over!** Nobody scored any points. Better luck next time!")
            return

        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        winner = sorted_scores[0][0]
        winning_score = sorted_scores[0][1]

        embed = discord.Embed(
            title="🏆 Trivia Results!",
            description=f"**{winner.mention} wins with {winning_score} points!**",
            color=discord.Color.gold()
        )

        reward_amount = winning_score * 25
        guild_id = str(ctx.guild.id)
        user_winner_data = DataStorage.get_or_create_user(winner.id)
        user_winner_data.ajust_beans(guild_id, reward_amount)
        DataStorage.save_user_data()

        embed.set_footer(text=f"Awarded {reward_amount} Coffee Beans to the winner!")
        await ctx.send(embed=embed)


class QuickTriviaView(discord.ui.View):
    def __init__(self, ctx, user_data, category_arg):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user_data = user_data
        self.category_arg = category_arg
        self.message = None

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.green)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await interaction.response.defer()
        updated_user_data = DataStorage.get_or_create_user(self.ctx.author.id)
        await quick_trivia(self.ctx, updated_user_data, self.category_arg)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)


async def quick_trivia(ctx, user_data, category: str = None):
    """Single-question trivia — no session needed."""
    category_arg = category  # preserve the original arg for Play Again
    available_questions = []

    if category:
        cat_lower = category.lower()
        if cat_lower in DataStorage.trivia_questions:
            for sub_category, questions in DataStorage.trivia_questions[cat_lower].items():
                for q in questions:
                    available_questions.append((cat_lower, sub_category, q[0], q[1]))
        else:
            cats = ", ".join(DataStorage.trivia_questions.keys())
            await ctx.send(f"❌ Category **{category}** not found. Available: `{cats}`")
            return
    else:
        for category in user_data.enabled_trivia_categories:
            if category in DataStorage.trivia_questions:
                for sub_category, questions in DataStorage.trivia_questions[category].items():
                    for q in questions:
                        available_questions.append((category, sub_category, q[0], q[1]))

    if not available_questions:
        await ctx.send("⚠️ No questions available. Enable some categories with `.trivia_config` or specify a category.")
        return

    chosen_category, sub_category, question_text, acceptable_answers = random.choice(available_questions)

    timeout = get_question_timeout(question_text, acceptable_answers)

    embed = discord.Embed(
        title="🧠 Quick Trivia!",
        description=f"**{question_text}**",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"📂 {chosen_category.capitalize()} → {sub_category.capitalize()} • {timeout}s to answer! First correct answer wins 10 beans.")
    await ctx.send(embed=embed)

    def check(m):
        return m.channel == ctx.channel and not m.author.bot

    view = QuickTriviaView(ctx, user_data, category_arg)

    try:
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            msg = await ctx.bot.wait_for('message', timeout=remaining, check=check)
            if grade(msg.content, acceptable_answers, ctx, question_text):
                official_answer = acceptable_answers[0].capitalize()
                winner_data = DataStorage.get_or_create_user(msg.author.id)
                guild_id = winner_data.effective_guild_id(ctx)
                winner_data.state(guild_id).trivia_correct += 1
                winner_data.ajust_beans(guild_id, 10)
                DataStorage.save_user_data()
                result = await ctx.send(f"✅ **{msg.author.display_name}** got it! The answer was: **{official_answer}**. +10 beans!", view=view)
                view.message = result
                return
    except asyncio.TimeoutError:
        official_answer = acceptable_answers[0].capitalize()
        try:
            result = await ctx.send(f"⏳ Time's up! The answer was: **{official_answer}**", view=view)
            view.message = result
        except discord.DiscordException:
            pass


async def trivia_stats(ctx, user_data):
    """Show a user's per-server trivia statistics."""
    guild_id = user_data.effective_guild_id(ctx)
    state = user_data.state(guild_id)
    embed = discord.Embed(
        title=f"🧠 {ctx.author.display_name}'s Trivia Stats",
        color=discord.Color.blue()
    )
    embed.add_field(name="✅ Correct Answers (this server)", value=str(state.trivia_correct), inline=True)
    enabled = user_data.enabled_trivia_categories
    cats_str = ", ".join(c.capitalize() for c in enabled) if enabled else "None configured"
    embed.add_field(name="📂 Enabled Categories", value=cats_str, inline=False)
    embed.set_footer(text="Use .trivia_config to change your categories")
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# .trivia_review — bot_admin labeling command
# ---------------------------------------------------------------------------

_REVIEW_QUEUE_CAP = 25  # max entries served per session


def _build_review_queue() -> list:
    """
    Read the graylog, filter out already-labeled entries, then return a randomly
    interleaved queue of at most _REVIEW_QUEUE_CAP items with a roughly equal mix
    of accepted-gray (verdict==True) and rejected-gray (verdict==False).

    Identity key for "already labeled": (question, guess, tuple(sorted(answers))).
    """
    all_entries = TriviaMatching.load_graylog()
    labeled_rows = TriviaMatching.load_labels()

    labeled_keys = set()
    for row in labeled_rows:
        try:
            key = (row["question"], row["guess"], tuple(sorted(row["answers"])))
            labeled_keys.add(key)
        except (KeyError, TypeError):
            pass

    unlabeled = []
    for entry in all_entries:
        try:
            key = (entry["question"], entry["guess"], tuple(sorted(entry["answers"])))
        except (KeyError, TypeError):
            continue
        if key not in labeled_keys:
            unlabeled.append(entry)

    accepted = [e for e in unlabeled if e.get("verdict") is True]
    rejected = [e for e in unlabeled if e.get("verdict") is False]

    random.shuffle(accepted)
    random.shuffle(rejected)

    # Interleave accepted and rejected to keep the queue balanced.
    interleaved = []
    a_idx = r_idx = 0
    while len(interleaved) < _REVIEW_QUEUE_CAP and (a_idx < len(accepted) or r_idx < len(rejected)):
        if a_idx < len(accepted):
            interleaved.append(accepted[a_idx])
            a_idx += 1
        if len(interleaved) < _REVIEW_QUEUE_CAP and r_idx < len(rejected):
            interleaved.append(rejected[r_idx])
            r_idx += 1

    return interleaved


def _make_review_embed(entry: dict, index: int, total: int) -> discord.Embed:
    """Build the embed for a single review entry."""
    verdict_label = "Accepted (bot said CORRECT)" if entry.get("verdict") else "Rejected (bot said INCORRECT)"
    verdict_color = discord.Color.green() if entry.get("verdict") else discord.Color.red()

    answers_str = ", ".join(entry.get("answers", []))
    score = entry.get("features", {}).get("char_ratio", "?")
    if isinstance(score, float):
        score = f"{score:.3f}"

    embed = discord.Embed(
        title=f"Gray-Zone Review ({index}/{total})",
        color=verdict_color
    )
    embed.add_field(name="Question", value=entry.get("question", "?"), inline=False)
    embed.add_field(name="Correct Answers", value=answers_str or "?", inline=False)
    embed.add_field(name="Player Guess", value=f'`{entry.get("guess", "?")}`', inline=True)
    embed.add_field(name="Bot Decision", value=verdict_label, inline=True)
    embed.add_field(name="Score", value=score, inline=True)
    embed.set_footer(text="React: ✅ correct  ❌ incorrect  ⏭ skip")
    return embed


class TriviaReviewView(discord.ui.View):
    """
    Interactive review view for gray-zone trivia entries.
    Only the invoking bot admin may click.
    Mirrors the on_timeout pattern from QuickTriviaView.
    """

    def __init__(self, ctx, queue: list):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.queue = queue
        self.index = 0          # current position in queue
        self.labeled_count = 0
        self.skipped_count = 0
        self.message = None

    # ------------------------------------------------------------------
    # Guard: only the invoking admin may interact
    # ------------------------------------------------------------------

    async def _auth_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Only the admin who invoked this command can label entries.", ephemeral=True
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _current_entry(self):
        return self.queue[self.index]

    async def _advance(self, interaction: discord.Interaction):
        """Move to the next entry or finish the session."""
        self.index += 1
        if self.index >= len(self.queue):
            await self._finish(interaction)
        else:
            embed = _make_review_embed(self._current_entry(), self.index + 1, len(self.queue))
            await interaction.response.edit_message(embed=embed, view=self)

    async def _finish(self, interaction: discord.Interaction):
        """Disable buttons and show a summary."""
        for item in self.children:
            item.disabled = True
        summary = discord.Embed(
            title="Review Complete",
            description=(
                f"Session finished!\n"
                f"Labeled: **{self.labeled_count}**\n"
                f"Skipped: **{self.skipped_count}**\n"
                f"Queue exhausted."
            ),
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(embed=summary, view=self)

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    @discord.ui.button(label="✅ Correct", style=discord.ButtonStyle.green)
    async def mark_correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._auth_check(interaction):
            return
        TriviaMatching.append_label(self._current_entry(), "correct")
        self.labeled_count += 1
        await self._advance(interaction)

    @discord.ui.button(label="❌ Incorrect", style=discord.ButtonStyle.red)
    async def mark_incorrect(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._auth_check(interaction):
            return
        TriviaMatching.append_label(self._current_entry(), "incorrect")
        self.labeled_count += 1
        await self._advance(interaction)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.secondary)
    async def skip_entry(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._auth_check(interaction):
            return
        self.skipped_count += 1
        await self._advance(interaction)

    # ------------------------------------------------------------------
    # Timeout — mirror QuickTriviaView
    # ------------------------------------------------------------------

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.DiscordException:
                pass


async def review(ctx):
    """
    bot_admin command: replay unlabeled gray-zone entries one at a time.
    DM-friendly (no guild_only restriction) — the graylog is global.
    """
    queue = _build_review_queue()
    if not queue:
        await ctx.send("No unlabeled gray-zone entries found. Play some trivia first to populate the log!")
        return

    embed = _make_review_embed(queue[0], 1, len(queue))
    view = TriviaReviewView(ctx, queue)
    result = await ctx.send(embed=embed, view=view)
    view.message = result