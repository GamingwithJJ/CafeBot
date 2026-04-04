import DataStorage
from Classes.QuoteClass import Quote
from Classes.Verse import Verse


async def add_gif(ctx, type: str, link: str):
    """Adds a new gif for the specified type"""
    type = type.lower()

    try:
        DataStorage.gifs[type].append(link)
        DataStorage.save_gifs()
        await ctx.send(f"Added the link to the list")
    except Exception as e:
        await ctx.send(f"There was an error, {e}")


async def remove_gif(ctx, type: str, link: str):
    """Removes a gif of the specified link"""
    type = type.lower()
    gif_list = None

    try:
        gif_list = DataStorage.gifs[type]
    except Exception as e:
        await ctx.send(f"There was an error, {e}")
        return

    for index, gif in enumerate(gif_list):
        if gif == link:
            DataStorage.gifs[type].pop(index)
            DataStorage.save_gifs()
            await ctx.send("Removed gif from the list.")
            return

    await ctx.send("Gif with the specified link was not found.")


async def add_quote(ctx, authors, quote):
    """Adds a new quote with the author"""
    quotes_dictionary = DataStorage.quotes

    if isinstance(authors, str):
        authors = [authors.lower().capitalize()]
    else:
        author_overwrite_list = []
        for author in authors:
            author_overwrite_list.append(author.lower().capitalize())

    # Filter for already exists
    for author in authors:
        if author in quotes_dictionary:
            for quote_object in quotes_dictionary[author]:
                if quote_object.get_text() == quote:
                    await ctx.send(f"That quote already exists for {author}")
                    return

    for author in authors:
        quote_object = Quote(quote, author)
        if author not in quotes_dictionary:
            DataStorage.quotes[author] = []
            if author not in DataStorage.quote_users:
                DataStorage.quote_users.append(author)
                DataStorage.save_quote_users()
        DataStorage.quotes[author].append(quote_object)

    DataStorage.save_quotes()
    await ctx.send(f"✅ Added quote")


async def remove_quote(ctx, quote_to_remove: str):
    """Removes a quote by its text content."""
    for author, quote_list in DataStorage.quotes.items():
        for index, quote_obj in enumerate(quote_list):
            if quote_obj.get_text() == quote_to_remove:
                DataStorage.quotes[author].pop(index)
                DataStorage.save_quotes()
                await ctx.send(f"✅ Removed quote from {author}!")
                return

    await ctx.send("❌ Could not find that quote.")


async def add_eight_ball(ctx, response: str):
    if response in DataStorage.magic_eight_ball:
        await ctx.send("This response already exists!")
        return
    DataStorage.magic_eight_ball.append(response)
    DataStorage.save_eight_ball()
    await ctx.send(f"✅ Added response!")


async def remove_eight_ball(ctx, response_to_remove: str):
    for index, response in enumerate(DataStorage.magic_eight_ball):
        if response == response_to_remove:
            DataStorage.magic_eight_ball.pop(index)
            DataStorage.save_eight_ball()
            await ctx.send(f"✅Removed Response!")
    await ctx.send("Could not find specified response")


async def add_verse(ctx, reference: str, verse_text: str):
    """Adds a new Bible verse to the database"""
    # Check if we already have it
    for v in DataStorage.verses:
        if v.get_reference().lower() == reference.lower():
            await ctx.send(f"❌ You already have {reference} saved!")
            return

    new_verse = Verse(verse_text, reference)
    DataStorage.verses.append(new_verse)
    DataStorage.save_verses()

    await ctx.send(f"✅ Successfully added **{reference}**!")


async def remove_verse(ctx, reference: str):
    """Removes a verse by its reference"""
    for index, v in enumerate(DataStorage.verses):
        if v.get_reference().lower() == reference.lower():
            DataStorage.verses.pop(index)
            DataStorage.save_verses()
            await ctx.send(f"✅ Removed **{reference}**!")
            return

    await ctx.send("❌ Could not find a verse with that reference.")

