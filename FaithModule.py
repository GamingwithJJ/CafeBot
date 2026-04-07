import discord
import asyncio
import random
import DataStorage

TESTIMONY_CHANNEL_ID = 1490167539110510856

last_random_verse = [] # contains a single verse format: version, book, chapter, verse


async def send_testimony(ctx, user_message: str):
    """Sends a message which has to be dmed to the bot in a testimony channel."""
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("🚫 This command only works in DMS, please read the help usage of this command carefully")
        return

    await ctx.send(
        f"Are you sure you want to send this testimony to the server anonymously?\n"
        f"Make sure you dont have any identifying information in the testimony as this bot does not check for that. \n"
        f"**Your message:** {user_message}\n"
        f"*(Type **yes** to confirm, or **no** to cancel)*"
    )

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        # The bot will wait up to 30.0 seconds for a message that passes the 'check'
        reply = await ctx.bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        # If 30 seconds pass without a reply, timeout
        await ctx.send("⏳ You took too long to reply! Message sending cancelled.")
        return

    if reply.content.lower() not in ['yes', 'y']:
        await ctx.send("❌ Message cancelled.")
        return

    channel = ctx.bot.get_channel(TESTIMONY_CHANNEL_ID)

    if channel is None:
        await ctx.send("❌ Error: I could not find the target channel.")
        return

    await channel.send(f"**Anonymous testimony:** {user_message}")
    await ctx.send("✅ Your message was sent successfully to the server!")


async def random_verse(ctx, version):
    """
    Pulls a random verse, version is an optional input defaulting to none
    """

    if DataStorage.bible_index:
        version_name = version
        if version is None:
            version_name = random.choice(list(DataStorage.bible_index.keys()))
        elif version not in DataStorage.bible_index:
            available = ", ".join(DataStorage.bible_index.keys())
            await ctx.send(f"❌ Version **{version}** not found. Available versions: `{available}`")
            return
        version_data = DataStorage.bible_index[version_name]

        book_name = random.choice(list(version_data.keys()))
        chapter_data = version_data[book_name]

        chapter_num = random.choice(list(chapter_data.keys()))
        verse_data = chapter_data[chapter_num]

        verse_num = random.choice(list(verse_data.keys()))
        verse_text = verse_data[verse_num]

        global last_random_verse
        last_random_verse = [version_name, book_name, chapter_num, verse_num]

        embed = discord.Embed(
            title="📖 Random Verse",
            description=f'"{verse_text}"',
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"{book_name} {chapter_num}:{verse_num} ({version_name})")
        await ctx.send(embed=embed)
    else:
        await ctx.send("Error, Bible index not found")


async def verse_context(ctx):
    """Shows up to 2 verses before and after the last randomly generated verse."""
    if not last_random_verse:
        await ctx.send("❌ No random verse has been generated yet. Use `.random_verse` first.")
        return

    version_name, book_name, chapter_num, verse_num = last_random_verse

    version_data = DataStorage.bible_index.get(version_name)
    if not version_data:
        await ctx.send("❌ The version from the last verse is no longer available.")
        return

    chapter_data = version_data.get(book_name, {}).get(chapter_num, {})
    if not chapter_data:
        await ctx.send("❌ Could not find the chapter for the last verse.")
        return

    sorted_verse_keys = sorted(chapter_data.keys(), key=lambda x: int(x))
    current_idx = sorted_verse_keys.index(verse_num)

    start = max(0, current_idx - 2)
    end = min(len(sorted_verse_keys) - 1, current_idx + 2)
    context_keys = sorted_verse_keys[start:end + 1]

    embed = discord.Embed(
        title=f"📖 {book_name} {chapter_num} — Context",
        color=discord.Color.gold()
    )
    for v in context_keys:
        marker = "▶ " if v == verse_num else ""
        embed.add_field(
            name=f"{marker}{book_name} {chapter_num}:{v}",
            value=f'"{chapter_data[v]}"',
            inline=False
        )
    embed.set_footer(text=version_name)
    await ctx.send(embed=embed)


async def lookup_verse(ctx, version: str, book: str, chapter: str, verse_num: str):
    """
    Looks up a specific verse by version, book, chapter, and verse number.
    Usage: .verse <version> <book> <chapter> <verse>
    Example: .verse KJV John 3 16
    """
    if not DataStorage.bible_index:
        await ctx.send("📖 The Bible index hasn't been loaded yet. Please contact a bot admin.")
        return

    version = version.upper()
    book = book.lower().capitalize()

    try:
        version_data = DataStorage.bible_index[version]
    except KeyError:
        available = ", ".join(DataStorage.bible_index.keys())
        await ctx.send(f"❌ Version **{version}** not found. Available versions: `{available}`")
        return

    try:
        book_data = version_data[book]
    except KeyError:
        await ctx.send(f"❌ Book **{book}** not found in **{version}**. Check your spelling (e.g. `John`, `Genesis`).")
        return

    try:
        chapter_data = book_data[chapter]
    except KeyError:
        max_ch = max(book_data.keys(), key=lambda x: int(x))
        await ctx.send(f"❌ **{book}** only has chapters 1–{max_ch} in **{version}**.")
        return

    max_v = max(chapter_data.keys(), key=lambda x: int(x))

    # --- Range (e.g. "3-8") ---
    if "-" in verse_num:
        start_str, end_str = verse_num.split("-", 1)
        start, end = int(start_str), int(end_str)

        if str(start) not in chapter_data or str(end) not in chapter_data:
            await ctx.send(f"❌ **{book} {chapter}** only has verses 1–{max_v} in **{version}**.")
            return

        embed = discord.Embed(
            title=f"📖 {book} {chapter}:{start}–{end}",
            color=discord.Color.gold()
        )
        for v in range(start, end + 1):
            verse_text = chapter_data.get(str(v))
            if verse_text:
                embed.add_field(name=f"Verse {v}", value=f'"{verse_text}"', inline=False)
        embed.set_footer(text=version)
        await ctx.send(embed=embed)

    # --- Single verse ---
    else:
        if verse_num not in chapter_data:
            await ctx.send(f"❌ **{book} {chapter}** only has verses 1–{max_v} in **{version}**.")
            return

        embed = discord.Embed(
            title=f"📖 {book} {chapter}:{verse_num}",
            description=f'"{chapter_data[verse_num]}"',
            color=discord.Color.gold()
        )
        embed.set_footer(text=version)
        await ctx.send(embed=embed)


async def list_versions(ctx):
    """Lists all Bible versions currently loaded in the index."""
    if not DataStorage.bible_index:
        await ctx.send("📖 The Bible index hasn't been loaded yet. Please contact a bot admin.")
        return

    versions = list(DataStorage.bible_index.keys())
    embed = discord.Embed(
        title="📖 Available Bible Versions",
        description="\n".join(f"• **{v}**" for v in versions),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


async def search_verses(ctx, max_results: int, query: str):
    """
    Searches the Bible index for verses containing the query string.
    Optionally filter by version by prefixing with `version:<VERSION> `.

    Usage:
        .verse_search love one another
        .verse_search version:KJV love one another
    """
    if not DataStorage.bible_index:
        await ctx.send("📖 The Bible index hasn't been loaded yet. Please contact a bot admin.")
        return

    # --- Optional version filter ---
    version_filter = None
    if query.lower().startswith("version:"):
        parts = query.split(" ", 1)
        version_filter = parts[0].split(":", 1)[1].upper()
        query = parts[1] if len(parts) > 1 else ""

    if not query.strip():
        await ctx.send("❌ Please provide a search term.")
        return

    query_lower = query.lower()
    results = []  # list of (version, book, chapter, verse_num, text)
    MAX_RESULTS = max_results

    for version_name, version_data in DataStorage.bible_index.items():
        if version_filter and version_name.upper() != version_filter:
            continue
        for book_name, chapter_data in version_data.items():
            for chapter_num, verse_data in chapter_data.items():
                for verse_num, verse_text in verse_data.items():
                    if query_lower in verse_text.lower():
                        results.append((version_name, book_name, chapter_num, verse_num, verse_text))
                    if len(results) >= MAX_RESULTS:
                        break
                if len(results) >= MAX_RESULTS:
                    break
            if len(results) >= MAX_RESULTS:
                break
        if len(results) >= MAX_RESULTS:
            break

    if not results:
        filter_note = f" in **{version_filter}**" if version_filter else ""
        await ctx.send(f"🔍 No verses found containing **\"{query}\"**{filter_note}.")
        return

    # --- Build embed ---
    version_label = version_filter if version_filter else "All Versions"
    embed = discord.Embed(
        title=f"🔍 Search results for \"{query}\"",
        description=f"Showing up to {MAX_RESULTS} results · {version_label}",
        color=discord.Color.blue()
    )

    for version_name, book_name, chapter_num, verse_num, verse_text in results:
        reference = f"{book_name} {chapter_num}:{verse_num} ({version_name})"
        # Truncate long verses in the embed field to keep things clean
        display_text = verse_text if len(verse_text) <= 200 else verse_text[:197] + "..."
        embed.add_field(name=reference, value=f'"{display_text}"', inline=False)

    await ctx.send(embed=embed)