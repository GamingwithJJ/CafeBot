import discord
import asyncio
import yt_dlp
import platform

if platform.system() == "Windows": # So the Module works on Linux and Windows
    FFMPEG_EXECUTABLE = "ffmpeg.exe"
else:
    FFMPEG_EXECUTABLE = "./ffmpeg"

# These settings tell yt-dlp to find the lightest, fastest audio stream
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

# These settings are crucial for cloud hosts so the stream doesn't drop
ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# This dictionary stores the music queue for each server
music_queues = {}


def get_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    return music_queues[guild_id]


async def play_next(ctx):
    """A background function that checks the queue and plays the next song."""
    queue = get_queue(ctx.guild.id)

    if len(queue) > 0:
        song = queue.pop(0)
        vc = ctx.voice_client

        # We just drop the global FFMPEG_EXECUTABLE right here!
        audio_source = discord.FFmpegPCMAudio(
            song['url'],
            executable=FFMPEG_EXECUTABLE,
            **ffmpeg_options
        )

        vc.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop))

        await ctx.send(f"🎶 Now playing: **{song['title']}**")
    else:
        await ctx.send("The queue is empty! Add more songs or I will take a break.")


async def play_song(ctx, search: str):
    """The main command to search and play a song."""
    # 1. Check if the user is actually in a voice channel
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel to request music!")
        return

    # 2. Connect the bot to the voice channel
    vc = ctx.voice_client
    if not vc:
        vc = await ctx.author.voice.channel.connect()
    elif vc.channel != ctx.author.voice.channel:
        await vc.move_to(ctx.author.voice.channel)

    await ctx.send(f"🔍 Searching for: `{search}`...")

    # 3. Search YouTube without freezing the bot
    loop = asyncio.get_event_loop()
    try:
        # We run this in an executor so the rest of your bot's commands don't freeze during the search
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
    except Exception as e:
        await ctx.send(f"❌ Could not find that song. Error: {e}")
        return

    # If it returns a list of search results, just grab the first one
    if 'entries' in data:
        data = data['entries'][0]

    song_info = {
        'url': data['url'],
        'title': data['title']
    }

    # 4. Add the song to the server's queue
    queue = get_queue(ctx.guild.id)
    queue.append(song_info)

    # 5. If nothing is currently playing, start the music!
    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)
    else:
        await ctx.send(f"📝 Added to queue: **{data['title']}**")


async def skip_song(ctx):
    """Skips the current song."""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()  # Stopping the audio automatically triggers the `after` callback to play the next song!
        await ctx.send("⏭️ Skipped!")
    else:
        await ctx.send("Nothing is playing right now.")


async def leave_channel(ctx):
    """Clears the queue and leaves the voice channel."""
    vc = ctx.voice_client
    if vc:
        # Clear the queue for this server
        if ctx.guild.id in music_queues:
            music_queues[ctx.guild.id] = []
        await vc.disconnect()
        await ctx.send("👋 Disconnected from voice. See ya!")
    else:
        await ctx.send("I'm not in a voice channel.")