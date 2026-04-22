import datetime
import discord
import DataStorage

async def purge(ctx, amount: int):
    if amount < 1:
        await ctx.send("Please specify an amount to purge greater than 0")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)

    await ctx.send(f"Deleted {len(deleted) - 1} messages.", delete_after=5)


async def lockdown_channel(ctx, channel, state: bool): # Locks or unlocks a single channel

    if state:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)

        await ctx.send(f"🔒 {channel.mention} has been locked down.")
    else:
        await channel.set_permissions(ctx.guild.default_role, send_messages=None)

        await ctx.send(f"🔒 {channel.mention} has been unlocked.")


async def lockdown(ctx, state: bool,all_channels: bool): # Locks or unlocks a single channel or the whole server using lockdown_channel
    current_channel = ctx.channel

    boolean_state = bool(state)

    if all_channels:

        if state:
            await ctx.send("🔒 Initiating server lockdown... please wait.")
        else:
            await ctx.send("🔒 Unlocking server.. please wait.")

        for channel in ctx.guild.text_channels:
            await lockdown_channel(ctx, channel, state)
    else:
        await lockdown_channel(ctx, ctx.channel, state)


async def kick_user(ctx, member, reason):
    if member.id == ctx.author.id:
        await ctx.send("You cannot kick yourself.")
        return

    await member.kick(reason=reason)
    await ctx.send(f"👢 **{member.name}** has been kicked. Reason: {reason}")


async def ban_user(ctx, member, reason):
    if member.id == ctx.author.id:
        await ctx.send("You cannot ban yourself.")
        return

    await member.ban(reason=reason)
    await ctx.send(f"🔨 **{member.name}** has been BANNED. Reason: {reason}")


async def unban_user(ctx, user_id: int):
    user = await ctx.bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"✅ **{user.name}** has been unbanned.")


async def slowmode(ctx,boolean: bool,seconds: int):
    if seconds > 21600:
        await ctx.send("Slowmode cannot exceed six hours")
        return

    if not boolean: # If it is false
        await ctx.channel.edit(slowmode_delay=0)
        await ctx.send("Slowmode disabled")
        return

    await ctx.channel.edit(slowmode_delay=seconds)

    await ctx.send(f"🐢 Slowmode set to {seconds} seconds.")


async def timeout_user(ctx, member, minutes: int, reason):
    duration = datetime.timedelta(minutes=minutes)

    await member.timeout(duration, reason=reason)

    await ctx.send(f"**{member.name}** has been timed out for {minutes} minutes. Reason: {reason}")


async def remove_timeout(ctx, member):
    await member.timeout(None)
    await ctx.send(f"**{member.name}** has been released from timeout.")


async def softban_user(ctx, member, amount_of_days: int, reason):

    await member.ban(delete_message_days=amount_of_days, reason=reason)

    await ctx.guild.unban(member)

    await ctx.send(f"🌪️ **{member.name}** was softbanned (Messages wiped, but they can rejoin).")


async def warn_user(ctx, member: discord.Member, reason: str):
    """Log a warning against a server member."""
    if member.id == ctx.author.id:
        await ctx.send("You cannot warn yourself.")
        return

    user_data = DataStorage.get_or_create_user(member.id)
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    user_data.add_warning(str(ctx.guild.id), reason, str(ctx.author.id), timestamp)
    DataStorage.save_user_data()

    total = len(user_data.get_warnings(str(ctx.guild.id)))
    embed = discord.Embed(
        title="⚠️ Warning Issued",
        color=discord.Color.orange()
    )
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"{member.display_name} now has {total} warning(s).")
    await ctx.send(embed=embed)


async def view_warnings(ctx, member: discord.Member):
    """Display all logged warnings for a member."""
    user_data = DataStorage.get_or_create_user(member.id)
    warnings = user_data.get_warnings(str(ctx.guild.id))

    if not warnings:
        await ctx.send(f"✅ **{member.display_name}** has no warnings on record.")
        return

    embed = discord.Embed(
        title=f"⚠️ Warnings for {member.display_name}",
        color=discord.Color.orange()
    )
    for i, w in enumerate(warnings, 1):
        embed.add_field(
            name=f"Warning #{i} — {w['timestamp']}",
            value=f"**Reason:** {w['reason']}\n**Issued by:** <@{w['issued_by']}>",
            inline=False
        )
    await ctx.send(embed=embed)


async def whois(ctx, member):
    # Create the Embed
    embed = discord.Embed(title=f"User Info - {member.name}", color=member.color)

    # Set the thumbnail to their profile picture
    embed.set_thumbnail(url=member.display_avatar.url)

    # Add data fields
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Nickname", value=member.nick, inline=True)

    # Format dates nicely
    created = member.created_at.strftime("%b %d, %Y")
    joined = member.joined_at.strftime("%b %d, %Y")

    embed.add_field(name="Account Created", value=created, inline=False)
    embed.add_field(name="Joined Server", value=joined, inline=False)

    # List their roles (skipping @everyone)
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    # Join them with spaces, or say "None" if empty
    role_str = " ".join(roles) if roles else "None"

    embed.add_field(name="Roles", value=role_str, inline=False)

    await ctx.send(embed=embed)

