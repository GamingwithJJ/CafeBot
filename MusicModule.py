import discord
import asyncio
import shutil
import yt_dlp
import aiohttp
import logging
import os

log = logging.getLogger("MusicModule")

# ---------------------------------------------------------------------------
# 0. PATH SETUP — add the bot's directory so yt-dlp can find a locally
#    uploaded `node` binary for YouTube signature/challenge solving.
# ---------------------------------------------------------------------------
_bot_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['PATH'] = _bot_dir + os.pathsep + os.environ.get('PATH', '')
log.info(f"Bot directory added to PATH: {_bot_dir}")

# Quick check: can we find node?
_node_path = shutil.which("node")
if _node_path:
    log.info(f"Found node at: {_node_path}")
else:
    log.warning("Node.js NOT found — YouTube signature solving will fail!")

# ---------------------------------------------------------------------------
# 1. FFMPEG BINARY — use the SYSTEM binary, not imageio_ffmpeg's stripped copy.
#    imageio_ffmpeg ships a minimal build meant for image processing that often
#    lacks network protocol/codec support and segfaults on stream URLs.
#    Fallback order: system PATH → common Linux locations → imageio as last resort.
# ---------------------------------------------------------------------------
def _find_ffmpeg():
    # Prefer the real system binary
    path = shutil.which("ffmpeg")
    if path:
        return path

    # Common locations on Debian/Ubuntu containers (e.g. Sparked Host)
    for candidate in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        import os
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # Last resort: fall back to imageio_ffmpeg's bundled copy
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"  # hope it's on PATH

FFMPEG_EXECUTABLE = _find_ffmpeg()
log.info(f"Using ffmpeg: {FFMPEG_EXECUTABLE}")


# ---------------------------------------------------------------------------
# 2. YT-DLP OPTIONS — hardened for data-center IPs
# ---------------------------------------------------------------------------
_COMMON_YTDL_OPTS = {
    # Prefer direct HTTP(S) streams — ffmpeg 5.1.8 on Debian 12 can't handle
    # opus segments inside HLS playlists (SoundCloud's hls_opus format).
    'format': 'bestaudio[protocol=https]/bestaudio[protocol=http]/bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',

    # --- JavaScript runtime ---
    # Node.js is NOT enabled by default (only Deno is).
    # Explicitly enable it; node is already on PATH.
    'js_runtimes': {'node': {}},

    # --- YouTube-specific defenses ---
    # Use a single client to minimize JS challenge solving (the CPU-heavy part).
    # 'web' alone is sufficient when cookies are provided.
    'extractor_args': {
        'youtube': {
            'player_client': ['web'],
        }
    },
    # Mimic a real browser
    'http_headers': {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
    },
    # Cookies exported from a browser where you're logged into YouTube.
    # Place cookies.txt in the same directory as botMain.py.
    'cookiefile': 'cookies.txt',
}

ytdl = yt_dlp.YoutubeDL(_COMMON_YTDL_OPTS)


# ---------------------------------------------------------------------------
# 3. FFMPEG OPTIONS — reconnection settings for cloud hosts
# ---------------------------------------------------------------------------
ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}


# ---------------------------------------------------------------------------
# 4. QUEUE MANAGEMENT + URL CACHE
#    YouTube stream URLs last ~6 hours. Caching them avoids re-running the
#    expensive Node.js challenge solver for repeat plays.
# ---------------------------------------------------------------------------
import time

music_queues = {}
now_playing = {}          # guild_id → {'url', 'title'} of the active song
loop_enabled = {}         # guild_id → bool
_url_cache = {}           # key = search term, value = {'url', 'title', 'expires'}
_CACHE_TTL = 4 * 3600     # 4 hours (conservative — URLs last ~6h)

# Limit to 1 concurrent extraction so multiple .play commands don't
# spawn parallel Node.js processes that spike the CPU to 100%.
_extract_semaphore = asyncio.Semaphore(1)


def _cache_get(search: str) -> dict | None:
    """Return cached song info if still valid, else None."""
    key = search.lower().strip()
    entry = _url_cache.get(key)
    if entry and entry['expires'] > time.time():
        return {'url': entry['url'], 'title': entry['title']}
    _url_cache.pop(key, None)
    return None


def _cache_set(search: str, url: str, title: str):
    key = search.lower().strip()
    _url_cache[key] = {'url': url, 'title': title, 'expires': time.time() + _CACHE_TTL}


def get_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    return music_queues[guild_id]


# ---------------------------------------------------------------------------
# 5. STREAM URL VALIDATOR
#    Prevents the segfault by verifying yt-dlp actually gave us audio, not
#    a 403 page or CAPTCHA HTML.
# ---------------------------------------------------------------------------
async def _validate_stream_url(url: str) -> bool:
    """HEAD-request the stream URL; return True only if it looks like media."""
    # Reject HLS manifests outright — ffmpeg 5.1.8 can't handle opus HLS segments
    if '.m3u8' in url.split('?')[0]:
        log.warning("Rejecting HLS manifest URL (.m3u8) — not supported by this ffmpeg")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    log.warning(f"Stream URL returned HTTP {resp.status}")
                    return False
                ct = resp.headers.get("Content-Type", "")
                # Reject HLS/DASH playlist content types
                if "mpegurl" in ct or "dash" in ct:
                    log.warning(f"Rejecting playlist Content-Type: {ct}")
                    return False
                if any(t in ct for t in ("audio", "video", "octet-stream", "webm")):
                    return True
                log.warning(f"Unexpected Content-Type for stream: {ct}")
                return False
    except Exception as e:
        log.warning(f"Stream validation failed: {e}")
        return False


# ---------------------------------------------------------------------------
# 6. EXTRACTION HELPER — tries YouTube, then falls back to SoundCloud
# ---------------------------------------------------------------------------
async def _extract_song(search: str, loop) -> dict | None:
    """
    Try to extract a playable stream URL.
    Returns {'url': ..., 'title': ...} or None on failure.
    """

    # --- Check cache first (instant, no CPU, no semaphore needed) ---
    cached = _cache_get(search)
    if cached:
        log.info(f"Cache hit for: {search}")
        return cached

    # --- Acquire semaphore so only 1 extraction runs at a time ---
    async with _extract_semaphore:

        # Double-check cache — another request may have cached this while we waited
        cached = _cache_get(search)
        if cached:
            return cached

        # --- Attempt 1: normal search (usually hits YouTube) ---
        try:
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(search, download=False)
            )
            if 'entries' in data:
                data = data['entries'][0]

            url = data.get('url')
            if url and await _validate_stream_url(url):
                result = {'url': url, 'title': data.get('title', 'Unknown')}
                _cache_set(search, result['url'], result['title'])
                return result
            else:
                log.warning("YouTube stream URL failed validation — trying SoundCloud fallback")
        except Exception as e:
            log.warning(f"YouTube extraction failed: {e}")

        # --- Attempt 2: SoundCloud fallback ---
        try:
            sc_search = f"scsearch:{search}"
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(sc_search, download=False)
            )
            if 'entries' in data:
                data = data['entries'][0]

            url = data.get('url')
            if url and await _validate_stream_url(url):
                result = {'url': url, 'title': data.get('title', 'Unknown') + ' (SoundCloud)'}
                _cache_set(search, result['url'], result['title'])
                return result
        except Exception as e:
            log.warning(f"SoundCloud extraction also failed: {e}")

        return None


# ---------------------------------------------------------------------------
# 7. PLAYBACK
# ---------------------------------------------------------------------------
async def play_next(ctx):
    """Pops the next song from the queue and plays it."""
    queue = get_queue(ctx.guild.id)

    # If loop is on, re-insert the just-finished song at the front of the queue
    if loop_enabled.get(ctx.guild.id) and ctx.guild.id in now_playing:
        queue.insert(0, now_playing[ctx.guild.id])

    if not queue:
        now_playing.pop(ctx.guild.id, None)
        await ctx.send("The queue is empty! Add more songs or I will take a break.")
        return

    song = queue.pop(0)
    vc = ctx.voice_client

    if not vc or not vc.is_connected():
        now_playing.pop(ctx.guild.id, None)
        return

    # Track what's currently playing so it can be displayed
    now_playing[ctx.guild.id] = song

    audio_source = discord.FFmpegPCMAudio(
        song['url'],
        executable=FFMPEG_EXECUTABLE,
        **ffmpeg_options
    )

    def _after(error):
        if error:
            log.error(f"Playback error: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)

    vc.play(audio_source, after=_after)
    await ctx.send(f"🎶 Now playing: **{song['title']}**")


async def play_song(ctx, search: str):
    """The main command to search and play a song."""
    # 1. Make sure the user is in a voice channel
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel to request music!")
        return

    # 2. Connect / move the bot
    vc = ctx.voice_client
    if not vc:
        vc = await ctx.author.voice.channel.connect()
    elif vc.channel != ctx.author.voice.channel:
        await vc.move_to(ctx.author.voice.channel)

    await ctx.send(f"🔍 Searching for: `{search}`...")

    # 3. Extract a validated stream URL (with SoundCloud fallback)
    loop = asyncio.get_event_loop()
    song = await _extract_song(search, loop)

    if not song:
        await ctx.send(
            "❌ Couldn't get a playable stream. YouTube may be blocking this "
            "server's IP and SoundCloud didn't have a match either.\n"
            "**Tip:** Try `.play <direct mp3/ogg URL>` with a direct link, "
            "or ask an admin to set up a `cookies.txt` file."
        )
        return

    # 4. Queue it up
    queue = get_queue(ctx.guild.id)
    queue.append(song)

    # 5. Start playing if nothing else is
    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)
    else:
        await ctx.send(f"📝 Added to queue: **{song['title']}**")


# ---------------------------------------------------------------------------
# 8. SKIP / LEAVE (unchanged logic, minor cleanup)
# ---------------------------------------------------------------------------
async def skip_song(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()  # triggers the `after` callback → plays next
        await ctx.send("⏭️ Skipped!")
    else:
        await ctx.send("Nothing is playing right now.")


async def pause_song(ctx):
    vc = ctx.voice_client
    if not vc:
        await ctx.send("I'm not in a voice channel.")
        return
    if vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Paused.")
    elif vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Resumed.")
    else:
        await ctx.send("Nothing is playing right now.")


async def toggle_loop(ctx):
    guild_id = ctx.guild.id
    loop_enabled[guild_id] = not loop_enabled.get(guild_id, False)
    if loop_enabled[guild_id]:
        await ctx.send("🔁 Loop **enabled** — current song will repeat.")
    else:
        await ctx.send("➡️ Loop **disabled**.")


async def leave_channel(ctx):
    vc = ctx.voice_client
    if vc:
        music_queues.pop(ctx.guild.id, None)
        now_playing.pop(ctx.guild.id, None)
        loop_enabled.pop(ctx.guild.id, None)
        await vc.disconnect()
        await ctx.send("👋 Disconnected from voice. See ya!")
    else:
        await ctx.send("I'm not in a voice channel.")


async def show_queue(ctx):
    """Display the currently playing song and upcoming queue."""
    current = now_playing.get(ctx.guild.id)
    queue = get_queue(ctx.guild.id)

    if not current and not queue:
        await ctx.send("🎵 Nothing is playing and the queue is empty.")
        return

    lines = []
    if current:
        lines.append(f"🎶 **Now Playing:** {current['title']}")

    if queue:
        lines.append("\n📝 **Up Next:**")
        for i, song in enumerate(queue[:10], 1):
            lines.append(f"`{i}.` {song['title']}")
        if len(queue) > 10:
            lines.append(f"*...and {len(queue) - 10} more*")
    elif current:
        lines.append("\n📝 **Up Next:** Nothing queued.")

    await ctx.send("\n".join(lines))