
import discord
import random
import DataStorage
import asyncio
import os
import uuid
from DataStorage import get_or_create_user
from Classes.RequestClass import Request
from Classes.UserSavesClass import User
from collections import deque
from PIL import Image, ImageDraw, ImageFont


async def marry(ctx, member):
    target_user_id = member.id
    author = ctx.author
    author_user_id = author.id

    target_user_data = get_or_create_user(target_user_id)
    author_user_data = get_or_create_user(author_user_id)

    if author_user_id == target_user_id:
        await ctx.send("You can't marry yourself silly!")
        return

    if member.bot:
        await ctx.send("You can't marry a bot!")
        return

    if target_user_id in author_user_data.get_marriage_partners():
        await ctx.send("You are already married to this person!")
        return

    if target_user_data.get_request("marriage", author_user_id) is not None:
        await ctx.send("You have already sent a request to this user")
        return

    request_to_send = Request("marriage", author_user_id)
    target_user_data.add_request("marriage", request_to_send)
    await ctx.send(f"Sent request to {member}")

    # Check if that user already sent the user a request, if so Marry them.
    if author_user_data.get_request("marriage", target_user_id) is not None:
        # Remove the requests
        author_user_data.remove_request_by_data("marriage", target_user_id)
        target_user_data.remove_request(request_to_send)
        # Add the partners
        author_user_data.add_marriage_partner(target_user_id)
        target_user_data.add_marriage_partner(author_user_id)
        await ctx.send("You are both now married! Congratulations!")

    DataStorage.save_user_data() # Temorary. Saves the file every time.


async def divorce(ctx, member):
    author_id = ctx.author.id
    target_id = member.id
    author_data = get_or_create_user(author_id)

    if target_id not in author_data.get_marriage_partners():
        await ctx.send("💔 You aren't married to that person!")
        return

    partner_data = get_or_create_user(target_id)
    author_data.remove_marriage_partner(target_id)
    partner_data.remove_marriage_partner(author_id)
    DataStorage.save_user_data()

    await ctx.send(f"📜 {ctx.author.mention} has divorced <@{target_id}>. The papers have been signed.")


async def adopt(ctx, member):
    author_id = ctx.author.id
    target_id = member.id

    if author_id == target_id:
        await ctx.send("You can't adopt yourself!")
        return

    if member.bot:
        await ctx.send("You can't adopt a bot!")
        return

    author_data = get_or_create_user(author_id)
    target_data = get_or_create_user(target_id)

    if target_id in author_data.get_adopted_children():
        await ctx.send("You have already adopted this person!")
        return

    if target_id in author_data.get_adopted_by():
        await ctx.send("You can't adopt someone who has already adopted you!")
        return

    if target_data.get_request("adoption", author_id) is not None:
        await ctx.send("You have already sent an adoption request to this user!")
        return

    request_to_send = Request("adoption", author_id)
    target_data.add_request("adoption", request_to_send)

    if author_data.get_request("adoption", target_id) is not None:
        author_data.remove_request_by_data("adoption", target_id)
        target_data.remove_request(request_to_send)
        target_data.add_adopted_child(author_id)
        author_data.add_adopted_parent(target_id)
        DataStorage.save_user_data()
        await ctx.send(f"Adoption complete! You have been adopted by {member.mention}! 👨‍👧")
    else:
        DataStorage.save_user_data()
        await ctx.send(f"Sent adoption request to {member.mention}.")


async def unadopt(ctx, member):
    author_id = ctx.author.id
    target_id = member.id

    author_data = get_or_create_user(author_id)
    target_data = get_or_create_user(target_id)

    if target_id in author_data.get_adopted_children():
        # Author is the parent
        author_data.remove_adopted_child(target_id)
        target_data.remove_adopted_parent(author_id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 The adoption of {member.mention} has been dissolved.")
    elif target_id in author_data.get_adopted_by():
        # Author is the child
        target_data.remove_adopted_child(author_id)
        author_data.remove_adopted_parent(target_id)
        DataStorage.save_user_data()
        await ctx.send(f"📜 Your adoption by {member.mention} has been dissolved.")
    else:
        await ctx.send("You don't have an adoption relationship with that person.")


async def family(ctx):
    author_id = ctx.author.id
    user_data = DataStorage.get_or_create_user(author_id)

    parents = user_data.get_adopted_by()
    children = user_data.get_adopted_children()

    if not parents and not children:
        embed = discord.Embed(
            title="👨‍👩‍👧 No Family Found",
            description="You haven't adopted anyone yet, and no one has adopted you!\nUse `.adopt @user` to start a family.",
            color=discord.Color.light_gray()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="👨‍👩‍👧 Your Family",
        color=discord.Color.green()
    )

    if parents:
        mentions = " ".join(f"<@{pid}>" for pid in parents)
        embed.add_field(name=f"👴 Adopted By ({len(parents)})", value=mentions, inline=False)

    if children:
        mentions = " ".join(f"<@{cid}>" for cid in children)
        embed.add_field(name=f"🧒 Children ({len(children)})", value=mentions, inline=False)

    embed.set_footer(text="CafeBot Family Registry | ☕")
    await ctx.send(embed=embed)


def get_family_neighbors(user_id: int) -> dict:
    user = DataStorage.get_or_create_user(user_id)
    return {
        "parents": list(user.get_adopted_by()),
        "children": list(user.get_adopted_children()),
        "partners": list(user.get_marriage_partners()),
    }


def build_family_subgraph(
    root_id: int,
    max_up: int = 2,
    max_down: int = 2,
    include_partners: bool = True,
    max_nodes: int = 25
) -> tuple[dict, bool]:
    graph = {}
    visited = set()
    queue = deque([(root_id, 0, 0)])
    truncated = False

    while queue:
        if len(graph) >= max_nodes:
            truncated = True
            break

        user_id, up_depth, down_depth = queue.popleft()

        if user_id in visited:
            continue

        visited.add(user_id)
        neighbors = get_family_neighbors(user_id)
        graph[user_id] = neighbors

        if include_partners:
            for partner_id in neighbors["partners"]:
                if partner_id not in visited:
                    queue.append((partner_id, up_depth, down_depth))

        if up_depth < max_up:
            for parent_id in neighbors["parents"]:
                if parent_id not in visited:
                    queue.append((parent_id, up_depth + 1, down_depth))

        if down_depth < max_down:
            for child_id in neighbors["children"]:
                if child_id not in visited:
                    queue.append((child_id, up_depth, down_depth + 1))

    if queue:
        truncated = True

    return graph, truncated


async def resolve_family_name(ctx, user_id: int) -> str:
    member = None
    if getattr(ctx, "guild", None):
        member = ctx.guild.get_member(user_id)
    if member is None:
        member = ctx.bot.get_user(user_id)
    if member is None:
        try:
            member = await ctx.bot.fetch_user(user_id)
        except Exception:
            return f"Unknown({user_id})"
    return member.display_name


async def build_family_name_map(ctx, graph: dict) -> dict[int, str]:
    name_map = {}
    for user_id in graph:
        name_map[user_id] = await resolve_family_name(ctx, user_id)
    return name_map


def choose_generation_level(existing_level: int | None, new_level: int) -> bool:
    if existing_level is None:
        return True
    if abs(new_level) < abs(existing_level):
        return True
    if abs(new_level) == abs(existing_level) and new_level < existing_level:
        return True
    return False


def compute_family_levels(root_id: int, graph: dict) -> dict[int, int]:
    levels = {root_id: 0}
    queue = deque([root_id])

    while queue:
        user_id = queue.popleft()
        level = levels[user_id]
        rels = graph.get(user_id, {"parents": [], "children": [], "partners": []})

        for partner_id in rels["partners"]:
            if partner_id in graph and choose_generation_level(levels.get(partner_id), level):
                levels[partner_id] = level
                queue.append(partner_id)

        for parent_id in rels["parents"]:
            if parent_id in graph and choose_generation_level(levels.get(parent_id), level - 1):
                levels[parent_id] = level - 1
                queue.append(parent_id)

        for child_id in rels["children"]:
            if child_id in graph and choose_generation_level(levels.get(child_id), level + 1):
                levels[child_id] = level + 1
                queue.append(child_id)

    return levels


def get_level_label(level: int, root_id: int, user_id: int) -> str:
    if user_id == root_id:
        return "You"
    if level == 0:
        return "Partner Tier"
    if level < 0:
        return f"Gen {level}"
    return f"Gen +{level}"


def load_family_fonts() -> tuple:
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
        meta_font = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        meta_font = ImageFont.load_default()
    return title_font, name_font, meta_font


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [text]

    lines = []
    current = words[0]

    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=name_font if False else font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines[:2]


def build_family_rows(root_id: int, graph: dict, levels: dict[int, int], name_map: dict[int, str]) -> list[tuple[int, list[int]]]:
    row_map = {}
    for user_id in graph:
        level = levels.get(user_id, 0)
        row_map.setdefault(level, []).append(user_id)

    rows = []
    for level in sorted(row_map):
        ids = row_map[level]
        if level == 0:
            partners = sorted([user_id for user_id in ids if user_id != root_id], key=lambda uid: name_map[uid].lower())
            ordered = [root_id] + partners if root_id in ids else partners
        else:
            ordered = sorted(ids, key=lambda uid: name_map[uid].lower())
        rows.append((level, ordered))
    return rows


def layout_family_cards(rows: list[tuple[int, list[int]]], canvas_width: int, top_y: int,
                        card_width: int, card_height: int, card_gap: int, row_gap: int) -> tuple[dict[int, tuple[int, int, int, int]], int]:
    positions = {}
    current_y = top_y

    for _level, row_ids in rows:
        row_width = len(row_ids) * card_width + max(0, len(row_ids) - 1) * card_gap
        start_x = max(40, (canvas_width - row_width) // 2)

        for index, user_id in enumerate(row_ids):
            x1 = start_x + index * (card_width + card_gap)
            y1 = current_y
            positions[user_id] = (x1, y1, x1 + card_width, y1 + card_height)

        current_y += card_height + row_gap

    return positions, current_y


def get_card_colors(level: int, root_id: int, user_id: int) -> tuple[str, str, str]:
    if user_id == root_id:
        return "#D8F3DC", "#2D6A4F", "#1B4332"
    if level < 0:
        return "#E8F0FE", "#5B7DB1", "#294172"
    if level > 0:
        return "#FFF4CC", "#C49A32", "#7A5A00"
    return "#FDE7D9", "#C97A40", "#7A4420"


def draw_connector(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str, width: int = 4):
    sx, sy = start
    ex, ey = end
    mid_y = (sy + ey) // 2
    draw.line((sx, sy, sx, mid_y), fill=fill, width=width)
    draw.line((sx, mid_y, ex, mid_y), fill=fill, width=width)
    draw.line((ex, mid_y, ex, ey), fill=fill, width=width)


def draw_family_edges(draw: ImageDraw.ImageDraw, graph: dict, positions: dict[int, tuple[int, int, int, int]]):
    edge_color = "#9E8F7A"
    partner_pairs = set()

    for user_id, rels in graph.items():
        if user_id not in positions:
            continue

        x1, y1, x2, y2 = positions[user_id]
        user_center_x = (x1 + x2) // 2

        for child_id in rels["children"]:
            if child_id not in positions:
                continue

            child_box = positions[child_id]
            child_center_x = (child_box[0] + child_box[2]) // 2
            draw_connector(draw, (user_center_x, y2), (child_center_x, child_box[1]), edge_color, width=4)

        for partner_id in rels["partners"]:
            if partner_id not in positions:
                continue
            pair = tuple(sorted((user_id, partner_id)))
            if pair in partner_pairs:
                continue
            partner_pairs.add(pair)

            px1, py1, px2, py2 = positions[partner_id]
            left_box = positions[pair[0]]
            right_box = positions[pair[1]]
            if left_box[0] > right_box[0]:
                left_box, right_box = right_box, left_box

            line_y = (left_box[1] + left_box[3]) // 2
            draw.line((left_box[2], line_y, right_box[0], line_y), fill="#C67B5C", width=5)
            midpoint_x = (left_box[2] + right_box[0]) // 2
            draw.ellipse((midpoint_x - 4, line_y - 4, midpoint_x + 4, line_y + 4), fill="#C67B5C")


def draw_family_cards(draw: ImageDraw.ImageDraw, graph: dict, positions: dict[int, tuple[int, int, int, int]],
                      levels: dict[int, int], root_id: int, name_map: dict[int, str], name_font, meta_font):
    for user_id, box in positions.items():
        x1, y1, x2, y2 = box
        fill_color, border_color, accent_color = get_card_colors(levels.get(user_id, 0), root_id, user_id)
        draw.rounded_rectangle(box, radius=18, fill=fill_color, outline=border_color, width=3)
        draw.rounded_rectangle((x1 + 10, y1 + 10, x1 + 26, y2 - 10), radius=8, fill=accent_color)

        name_lines = wrap_text(draw, name_map[user_id], name_font, max_width=(x2 - x1) - 56)
        header = get_level_label(levels.get(user_id, 0), root_id, user_id)
        rels = graph[user_id]
        meta_parts = []
        if rels["partners"]:
            meta_parts.append(f"{len(rels['partners'])} partner{'s' if len(rels['partners']) != 1 else ''}")
        if rels["children"]:
            meta_parts.append(f"{len(rels['children'])} child{'ren' if len(rels['children']) != 1 else ''}")
        if rels["parents"]:
            meta_parts.append(f"{len(rels['parents'])} parent{'s' if len(rels['parents']) != 1 else ''}")
        meta_text = " • ".join(meta_parts) if meta_parts else "No linked family"

        text_x = x1 + 38
        current_y = y1 + 14
        for line in name_lines:
            draw.text((text_x, current_y), line, font=name_font, fill="#2C241D")
            line_box = draw.textbbox((text_x, current_y), line, font=name_font)
            current_y = line_box[3] + 2

        draw.text((text_x, current_y + 2), header, font=meta_font, fill=accent_color)
        draw.text((text_x, current_y + 20), meta_text, font=meta_font, fill="#5E5348")


async def render_family_tree_image(ctx, root_id: int, graph: dict) -> str:
    title_font, name_font, meta_font = load_family_fonts()
    name_map = await build_family_name_map(ctx, graph)
    levels = compute_family_levels(root_id, graph)
    rows = build_family_rows(root_id, graph, levels, name_map)

    card_width = 220
    card_height = 92
    card_gap = 44
    row_gap = 96
    side_margin = 80
    title_height = 110
    footer_height = 60

    widest_row = max((len(row_ids) for _level, row_ids in rows), default=1)
    canvas_width = max(900, widest_row * card_width + max(0, widest_row - 1) * card_gap + side_margin * 2)
    positions, bottom_y = layout_family_cards(
        rows,
        canvas_width,
        title_height,
        card_width,
        card_height,
        card_gap,
        row_gap
    )
    canvas_height = bottom_y + footer_height

    image = Image.new("RGB", (canvas_width, canvas_height), "#FBF7F2")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((24, 24, canvas_width - 24, canvas_height - 24), radius=28, outline="#D8C8B8", width=3)
    title = f"Family Tree: {name_map.get(root_id, 'Unknown')}"
    subtitle = "Parents above, children below, partners linked on the same generation."
    draw.text((48, 38), title, font=title_font, fill="#3F2D21")
    draw.text((50, 74), subtitle, font=meta_font, fill="#7A6859")

    draw_family_edges(draw, graph, positions)
    draw_family_cards(draw, graph, positions, levels, root_id, name_map, name_font, meta_font)

    output_path = os.path.join("Saves", f"family_tree_{root_id}_{uuid.uuid4().hex}.png")
    image.save(output_path)
    return output_path


async def family_tree(ctx, member: discord.Member = None):
    target = member or ctx.author
    max_up = 2
    max_down = 2
    max_nodes = 25

    graph, truncated = build_family_subgraph(
        target.id,
        max_up=max_up,
        max_down=max_down,
        include_partners=True,
        max_nodes=max_nodes
    )
    if len(graph) == 1 and not graph[target.id]["parents"] and not graph[target.id]["children"] and not graph[target.id]["partners"]:
        embed = discord.Embed(
            title="👨‍👩‍👧 No Family Found",
            description="This user doesn't have any saved family relationships yet.",
            color=discord.Color.light_gray()
        )
        await ctx.send(embed=embed)
        return

    try:
        image_path = await render_family_tree_image(ctx, target.id, graph)
    except Exception as exc:
        await ctx.send(f"❌ I couldn't render the family tree image. Renderer error: `{exc}`")
        return

    footer = f"Showing up to {max_up} generations up, {max_down} down, and {max_nodes} total people."
    if truncated:
        footer += " Results were trimmed to keep the tree readable."

    embed = discord.Embed(
        title=f"🌳 Family Tree for {target.display_name}",
        description="Rendered with Pillow.",
        color=discord.Color.green()
    )
    embed.set_footer(text=footer)
    await ctx.send(embed=embed, file=discord.File(image_path, filename="family_tree.png"))


async def duel(ctx, target: discord.Member):
    author = ctx.author
    bot_id = ctx.bot.user.id

    if target.id == author.id:
        await ctx.send("You cant duel yourself silly!")
        return

    if target.id == bot_id:
        await ctx.send("You want to duel me? Well Alright!")
        await ctx.send(f"{ctx.bot.user} did 999999 damage to {author}! ({999999-100}/100)")
        await ctx.send(f"Sorry! You lost!")
        return

    author_hp = 100
    target_hp = 100

    embed = discord.Embed(
        title="⚔️ A Duel has Begun!",
        description=f"{author.mention} vs {target.mention}",
        color=discord.Color.red()
    )
    embed.add_field(name=f"{author.display_name}'s HP", value=f"❤️ {author_hp}/100", inline=True)
    embed.add_field(name=f"{target.display_name}'s HP", value=f"❤️ {target_hp}/100", inline=True)
    embed.set_footer(text="Let the battle begin!")

    duel_msg = await ctx.send(embed=embed)
    while author_hp > 0 and target_hp > 0:
        author_roll = random.randint(1, 20)
        target_roll = random.randint(1, 20)

        # Author Turn
        target_hp -= author_roll
        embed.description = f"💥 **{author.display_name}** deals **{author_roll}** damage!"
        embed.set_field_at(0, name=f"{author.display_name}'s HP", value=f"❤️ {author_hp}/100", inline=True)
        embed.set_field_at(1, name=f"{target.display_name}'s HP", value=f"❤️ {target_hp}/100", inline=True)
        await duel_msg.edit(embed=embed)

        # Target Turn
        author_hp -= target_roll
        embed.description = f"💥 **{target.display_name}** deals **{target_roll}** damage!"
        embed.set_field_at(0, name=f"{author.display_name}'s HP", value=f"❤️ {author_hp}/100", inline=True)
        embed.set_field_at(1, name=f"{target.display_name}'s HP", value=f"❤️ {target_hp}/100", inline=True)
        await duel_msg.edit(embed=embed)
        await asyncio.sleep(1.5)


    embed.title = "🏆 Duel Finished!"
    # If author is alive and target is dead
    if author_hp > 0 and target_hp <= 0:
        embed.description = f"Congratulations {author.mention}, you have defeated {target.mention}!"
        embed.color = discord.Color.gold()

    # If target is alive and author is dead
    elif target_hp > 0 and author_hp <= 0:
        embed.description = f"Congratulations {target.mention}, you have defeated {author.mention}!"
        embed.color = discord.Color.gold()

    # Both died at the same time
    else:
        embed.title = "🤝 It's a Tie!"
        embed.description = f"Both {author.mention} and {target.mention} have fallen at the same time!"
        embed.color = discord.Color.light_grey()
    embed.set_footer(text="Good Fight!")
    await duel_msg.edit(embed=embed)


async def quote(ctx):
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {})
    list_of_users = list(guild_quotes.keys())
    if not list_of_users:
        await ctx.send("No quotes have been added yet!")
        return

    random_user = random.choice(list_of_users)
    random_quote = random.choice(guild_quotes[random_user])

    embed = discord.Embed(
        description=f'"{random_quote.get_text()}"',
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"— {random_quote.get_author()}")
    await ctx.send(embed=embed)


async def quotes(ctx, amount: int):
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {})
    quotes_users = list(guild_quotes.keys())
    if not quotes_users:
        await ctx.send("No quotes have been added yet!")
        return

    embed = discord.Embed(title="📖 Random Quotes", color=discord.Color.gold())
    for _ in range(amount):
        random_user = random.choice(quotes_users)
        random_quote = random.choice(guild_quotes[random_user])
        embed.add_field(name=f"— {random_quote.get_author()}", value=f'"{random_quote.get_text()}"', inline=False)
    await ctx.send(embed=embed)


async def quote_list(ctx, user: str, number):
    """Sorts quotes by a individual and only shows quotes which are sent by a certain individual."""
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {})
    user = user.lower().capitalize()
    if user not in guild_quotes:
        await ctx.send(f"{user} user is not a recognized quote user")
        return

    available = guild_quotes[user]
    number = min(number, len(available))
    selected_quotes = random.sample(available, number)
    embed = discord.Embed(title=f"📖 Quotes from {user}", color=discord.Color.gold())
    for i, q in enumerate(selected_quotes):
        embed.add_field(name=f"Quote #{i + 1}", value=f'"{q.get_text()}"', inline=False)
    await ctx.send(embed=embed)


async def quote_count(ctx, user: str):
    """Displays the quotes count of a certain user"""
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {})
    user = user.lower().capitalize()
    if user not in guild_quotes:
        await ctx.send(f"{user} is not a valid quoter")
        return

    embed = discord.Embed(
        description=f"**{user}** has **{len(guild_quotes[user])}** quotes in the database.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


async def quote_top(ctx):
    """Displays the top ten quoters"""
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {})
    quote_amounts = [(author, len(qs)) for author, qs in guild_quotes.items()]
    top_users = sorted(quote_amounts, key=lambda x: x[1], reverse=True)[:10]

    if not top_users:
        await ctx.send("There were no users who qualify")
        return

    description = ""
    for i, (author, count) in enumerate(top_users):
        description += f"{i + 1}. `{author}`: {count}\n"

    embed = discord.Embed(
        title="🏆 Top 10 users with the most quotes!",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="Top Quoters List!")

    await ctx.send(embed=embed)



async def gif(ctx, type: str, target: discord.Member = None):
    gifs = DataStorage.gifs[type]
    if not gifs:
        await ctx.send(f"⚠️ No GIFs have been added for `{type}` yet. A bot admin can add some with `.add_gif {type} <url>`.")
        return

    gif = random.choice(gifs)

    embed = discord.Embed(color=discord.Color.random())

    template = random.choice(DataStorage.gif_messages[type])
    target_name = target.mention if target else "the void"
    embed.description = template.format(
        author = ctx.author.mention,
        target = target_name
    )

    embed.set_image(url=gif)
    await ctx.send(embed=embed)


async def magic_eight_ball(ctx, question: str):
    response = random.choice(DataStorage.magic_eight_ball)

    embed = discord.Embed(
        title="🔮 Magic 8-Ball",
        description=f"{ctx.author.mention} consults the oracle...",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="❓ Question",
        value=question,
        inline=False
    )

    embed.add_field(
        name="☕ Answer",
        value=f"**{response}**",
        inline=False
    )

    embed.set_footer(text="CafeBot | The coffee grounds have spoken.")
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

    await ctx.send(embed=embed)


async def partner(ctx):
    """Lists your current partners and the time you've been together."""
    author_id = ctx.author.id
    user_data = DataStorage.get_or_create_user(author_id)

    partners = user_data.get_marriage_partners()

    if not partners:
        embed = discord.Embed(
            title="💔 No Partner Found",
            description="You dont have a partner yet, Use .marry to propose!",
            color=discord.Color.light_gray()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="💕 Marriage Certificate",
        description="This is a certificate of your marriage!",
        color=discord.Color.fuchsia()
    )

    embed.add_field(name="👤 User", value=ctx.author.mention, inline=False)

    for pid in partners:
        date = user_data.get_partner_gained_date(pid)
        if date:
            ts = int(date.timestamp())
            date_str = f"<t:{ts}:D> (<t:{ts}:R>)"
        else:
            date_str = "A long, long time ago..."
        embed.add_field(name="💍 Partner", value=f"<@{pid}>\n📅 {date_str}", inline=True)

    # Shared children: adopted by author AND at least one partner
    all_partner_children = set()
    for pid in partners:
        pd = DataStorage.get_or_create_user(pid)
        all_partner_children |= set(pd.get_adopted_children())
    shared = set(user_data.get_adopted_children()) & all_partner_children
    if shared:
        embed.add_field(name="👨‍👩‍👧 Shared Children", value=" ".join(f"<@{cid}>" for cid in shared), inline=False)

    if len(partners) == 1:
        partner_user = ctx.bot.get_user(partners[0]) or await ctx.bot.fetch_user(partners[0])
        if partner_user:
            embed.set_thumbnail(url=partner_user.display_avatar.url)

    embed.set_footer(
        text="CafeBot Love Registry | ☕💕",
        icon_url=ctx.bot.user.display_avatar.url
    )

    await ctx.send(embed=embed)


async def marriage_top(ctx):
    """Lists the top 10 marriages ordered by length married"""
    user_saves = DataStorage.user_data

    pairs = []
    for user_id, user in user_saves.items():
        for pid in user.get_marriage_partners():
            # Only emit each pair once by requiring user_id < str(pid)
            if user_id < str(pid):
                date = user.get_partner_gained_date(pid)
                if date:
                    pairs.append((user_id, pid, date))

    top_pairs = sorted(pairs, key=lambda x: x[2])[:10]

    if not top_pairs:
        await ctx.send("No marriages found in the registry! 💔")
        return

    description = ""
    for i, (uid, pid, date) in enumerate(top_pairs):
        timestamp = int(date.timestamp())
        description += f"{i + 1}. <@{uid}> & <@{pid}> — <t:{timestamp}:R>\n"

    embed = discord.Embed(
        title="🏆 Top 10 Longest Marriages",
        description=description,
        color=discord.Color.gold()
    )
    embed.set_footer(text="CafeBot Love Registry | ☕💕")

    await ctx.send(embed=embed)


async def quote_search(ctx, keyword: str):
    """Search quotes by text content."""
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {})
    keyword_lower = keyword.lower()
    results = []
    for author, quote_list in guild_quotes.items():
        for q in quote_list:
            if keyword_lower in q.get_text().lower():
                results.append(q)

    if not results:
        await ctx.send(f"🔍 No quotes found containing **\"{keyword}\"**.")
        return

    embed = discord.Embed(title=f"🔍 Quotes matching \"{keyword}\"", color=discord.Color.gold())
    for q in results[:10]:
        embed.add_field(name=f"— {q.get_author()}", value=f'"{q.get_text()}"', inline=False)
    if len(results) > 10:
        embed.set_footer(text=f"Showing 10 of {len(results)} matches.")
    await ctx.send(embed=embed)


async def quote_stats(ctx):
    """Show overall quote database statistics."""
    if ctx.guild is None:
        await ctx.send("❌ Quote commands can't be used in DMs.")
        return

    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {})
    if not guild_quotes:
        await ctx.send("No quotes in the database yet.")
        return

    total = sum(len(qs) for qs in guild_quotes.values())
    top_author = max(guild_quotes, key=lambda a: len(guild_quotes[a]))
    avg = total / len(guild_quotes)

    embed = discord.Embed(title="📊 Quote Database Stats", color=discord.Color.gold())
    embed.add_field(name="Total Quotes", value=str(total), inline=True)
    embed.add_field(name="Total Authors", value=str(len(guild_quotes)), inline=True)
    embed.add_field(name="Average per Author", value=f"{avg:.1f}", inline=True)
    embed.add_field(name="Most Quoted", value=f"{top_author} ({len(guild_quotes[top_author])})", inline=False)
    await ctx.send(embed=embed)


async def profile(ctx):
    """Show a personal profile dashboard."""
    author_id = ctx.author.id
    user_data = DataStorage.get_or_create_user(author_id)

    partners = user_data.get_marriage_partners()
    if partners:
        partner_display = " ".join(f"<@{pid}>" for pid in partners)
    else:
        partner_display = "Single 💔"

    author_name = ctx.author.display_name.lower().capitalize()
    guild_quotes = DataStorage.quotes.get(str(ctx.guild.id), {}) if ctx.guild else {}
    quote_count = len(guild_quotes.get(author_name, []))

    embed = discord.Embed(
        title=f"☕ {ctx.author.display_name}'s Profile",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.add_field(name="💰 Beans", value=f"{user_data.get_beans():.0f}", inline=True)
    embed.add_field(name="💍 Partner", value=partner_display, inline=True)
    embed.add_field(name="🎙️ Quotes in DB", value=str(quote_count), inline=True)
    embed.add_field(name="⚔️ D&D Characters", value=str(len(user_data.characters)), inline=True)
    embed.add_field(name="📅 Daily Streak", value=f"{user_data.daily_reward_streak} days", inline=True)
    embed.add_field(name="💍 Total Marriages", value=str(user_data.total_marriages), inline=True)
    embed.add_field(name="💔 Total Divorces", value=str(user_data.total_divorces), inline=True)
    embed.add_field(name="🧠 Trivia Wins", value=str(user_data.trivia_correct), inline=True)
    embed.add_field(name="📖 Bookmarked Verses", value=str(len(user_data.bookmarked_verses)), inline=True)
    embed.set_footer(text="CafeBot Profile | ☕")
    await ctx.send(embed=embed)


async def coinflip(ctx):
    random_number = random.randint(0, 1)
    outcome = None

    if random_number == 0:
        outcome = "Heads"
    else:
        outcome = "Tails"

    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"{ctx.author.mention} tossed a coin into the air...",
        color=discord.Color.gold()
    )

    await asyncio.sleep(1)

    embed.add_field(
        name="The result is...",
        value=f"✨ **{outcome}** ✨",
        inline=False
    )

    await ctx.send(embed=embed)
