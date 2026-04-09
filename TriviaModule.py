import discord
import asyncio
import random
import DataStorage


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
                    available_questions.append((sub_category, q[0], q[1]))

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

    try:
        # 2. The Game Loop
        for round_num in range(1, rounds + 1):

            chosen_item = random.choice(available_questions)
            sub_category, question_text, acceptable_answers = chosen_item
            available_questions.remove(chosen_item)

            embed = discord.Embed(
                title=f"Round {round_num} of {rounds}",
                description=f"**{question_text}**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Category: {sub_category.capitalize()} • You have 15 seconds to answer!")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel == ctx.channel and not m.author.bot

            try:
                deadline = asyncio.get_event_loop().time() + 15.0
                while True:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        raise asyncio.TimeoutError
                    msg = await ctx.bot.wait_for('message', timeout=remaining, check=check)

                    if any(answer in msg.content.lower() for answer in acceptable_answers):
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


async def quick_trivia(ctx, user_data, category: str = None):
    """Single-question trivia — no session needed."""
    available_questions = []

    if category:
        cat_lower = category.lower()
        if cat_lower in DataStorage.trivia_questions:
            for sub_category, questions in DataStorage.trivia_questions[cat_lower].items():
                for q in questions:
                    available_questions.append((sub_category, q[0], q[1]))
        else:
            cats = ", ".join(DataStorage.trivia_questions.keys())
            await ctx.send(f"❌ Category **{category}** not found. Available: `{cats}`")
            return
    else:
        for category in user_data.enabled_trivia_categories:
            if category in DataStorage.trivia_questions:
                for sub_category, questions in DataStorage.trivia_questions[category].items():
                    for q in questions:
                        available_questions.append((sub_category, q[0], q[1]))

    if not available_questions:
        await ctx.send("⚠️ No questions available. Enable some categories with `.trivia_config` or specify a category.")
        return

    sub_category, question_text, acceptable_answers = random.choice(available_questions)

    embed = discord.Embed(
        title=f"🧠 Quick Trivia! (Category: {category})",
        description=f"**{question_text}**",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Category: {sub_category.capitalize()} • You have 15 seconds to answer! First correct answer wins 10 beans.")
    await ctx.send(embed=embed)

    def check(m):
        return m.channel == ctx.channel and not m.author.bot

    try:
        deadline = asyncio.get_event_loop().time() + 15.0
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            msg = await ctx.bot.wait_for('message', timeout=remaining, check=check)
            if any(answer in msg.content.lower() for answer in acceptable_answers):
                official_answer = acceptable_answers[0].capitalize()
                winner_data = DataStorage.get_or_create_user(msg.author.id)
                winner_data.trivia_correct += 1
                winner_data.ajust_beans(10)
                DataStorage.save_user_data()
                await ctx.send(f"✅ **{msg.author.display_name}** got it! The answer was: **{official_answer}**. +10 beans!")
                return
    except asyncio.TimeoutError:
        official_answer = acceptable_answers[0].capitalize()
        await ctx.send(f"⏳ Time's up! The answer was: **{official_answer}**")


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