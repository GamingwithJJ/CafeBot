import discord
import asyncio
import random
import DataStorage

TESTIMONY_CHANNEL_ID = 0


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


async def random_verse(ctx):
    """Pulls a random verse from the database"""
    if not DataStorage.verses:
        await ctx.send("No verses have been added yet!")
        return

    # Pick a random verse object
    verse = random.choice(DataStorage.verses)

    embed = discord.Embed(
        title="📖 Random verse",
        description=f'"{verse.get_text()}"',
        color=discord.Color.gold()
    )
    embed.set_footer(text=verse.get_reference() + f"({verse.get_version()})")

    await ctx.send(embed=embed)