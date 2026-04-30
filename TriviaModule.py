import discord
import asyncio
import random
import re
import difflib
import DataStorage


_STRIP_WORDS = {"the", "a", "an", "of", "and", "in", "on", "at", "to", "for"}

def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    words = [w for w in s.split() if w not in _STRIP_WORDS]
    return " ".join(words)


def is_correct_answer(msg_content: str, acceptable_answers: list) -> bool:
    normalized_msg = _normalize(msg_content)
    msg_words = normalized_msg.split()
    msg_word_set = set(msg_words)

    for answer in acceptable_answers:
        norm_answer = _normalize(answer)
        if not norm_answer:
            continue
        answer_words = norm_answer.split()
        window_size = len(answer_words)

        # Single-word answer: whole-word token match (prevents "6" matching "16")
        # Multi-word answer: phrase substring match
        if window_size == 1:
            if norm_answer in msg_words:
                return True
        else:
            if norm_answer in normalized_msg:
                return True

        # Order-independent match for safe-length multi-word answers
        if 2 <= window_size <= 5 and all(len(w) >= 4 for w in answer_words):
            if set(answer_words).issubset(msg_word_set):
                return True

        # Fuzzy match — skip for purely numeric answers (years, counts, etc.)
        is_numeric = norm_answer.replace(" ", "").isdigit()
        answer_len = len(norm_answer)
        if answer_len >= 4 and not is_numeric:
            if answer_len <= 6:
                threshold = 0.90
            elif answer_len <= 12:
                threshold = 0.85
            else:
                threshold = 0.82
            for i in range(max(1, len(msg_words) - window_size + 1)):
                window = " ".join(msg_words[i : i + window_size])
                ratio = difflib.SequenceMatcher(None, norm_answer, window).ratio()
                if ratio >= threshold:
                    return True

    return False


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

                    if is_correct_answer(msg.content, acceptable_answers):
                        official_answer = acceptable_answers[0].capitalize()
                        await ctx.send(
                            f"✅ **{msg.author.display_name}** got it right! The answer was: {official_answer}")

                        scores[msg.author] = scores.get(msg.author, 0) + 1
                        DataStorage.get_or_create_user(msg.author.id).trivia_correct += 1
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
        user_winner_data = DataStorage.get_or_create_user(winner.id)
        user_winner_data.ajust_beans(reward_amount)
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
            if is_correct_answer(msg.content, acceptable_answers):
                official_answer = acceptable_answers[0].capitalize()
                winner_data = DataStorage.get_or_create_user(msg.author.id)
                winner_data.trivia_correct += 1
                winner_data.ajust_beans(10)
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
    """Show a user's personal trivia statistics."""
    embed = discord.Embed(
        title=f"🧠 {ctx.author.display_name}'s Trivia Stats",
        color=discord.Color.blue()
    )
    embed.add_field(name="✅ Correct Answers", value=str(user_data.trivia_correct), inline=True)
    enabled = user_data.enabled_trivia_categories
    cats_str = ", ".join(c.capitalize() for c in enabled) if enabled else "None configured"
    embed.add_field(name="📂 Enabled Categories", value=cats_str, inline=False)
    embed.set_footer(text="Use .trivia_config to change your categories")
    await ctx.send(embed=embed)