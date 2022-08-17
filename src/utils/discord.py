from datetime import datetime as _datetime
from re import compile as _compile
from re import escape as _escape
from re import Pattern as _Pattern
from re import search as _search
from typing import Any as _Any
from typing import AnyStr as _AnyStr
from typing import List as _List
from typing import Optional as _Optional
from typing import Union as _Union
from typing import Tuple as _Tuple

from discord import ApplicationContext as _ApplicationContext
from discord import Colour as _Colour
from discord import Embed as _Embed
from discord import File as _File
from discord import Forbidden as _Forbidden
from discord import Guild as _Guild
from discord import Interaction as _Interaction
from discord import Member as _Member
from discord import Message as _Message
from discord import MISSING as _MISSING
from discord import NotFound as _NotFound
from discord import Reaction as _Reaction
from discord import TextChannel as _TextChannel
from discord import User as _User
from discord import WebhookMessage as _WebhookMessage
from discord.abc import Messageable as _Messageable
from discord.ext.commands import Bot as _Bot
from discord.ext.commands import Context as _Context
from discord.ui import View as _View

from . import miscellaneous as _utils


# ---------- Constants ----------

DEFAULT_EMBED_INLINE: bool = True

MAXIMUM_CHARACTERS: int = 1900
MAXIMUM_CHARACTERS_EMBED_DESCRIPTION: int = 2048

RX_DISCORD_INVITE: _Pattern = _compile(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?')

ZERO_WIDTH_SPACE: str = '\u200b'


# ---------- Functions ----------

def convert_color_string_to_embed_color(color_string: str) -> _Colour:
    if color_string:
        split_color_string = color_string.split(',')
        r, g, b = [int(c) for c in split_color_string]
        result = _Colour.from_rgb(r, g, b)
    else:
        result = _Embed.Empty
    return result


def create_basic_embeds_from_description(title: str, repeat_title: bool = True, description: _List[str] = None, colour: _Colour = None, thumbnail_url: str = None, repeat_thumbnail: bool = True, image_url: str = None, repeat_image: bool = True, icon_url: str = None, author_url: str = None, footer: str = None, footer_icon_url: str = None, repeat_footer: bool = True, timestamp: _datetime = None, repeat_timestamp: bool = True) -> _List[_Embed]:
    result = []
    if description:
        embed_bodies = create_posts_from_lines(description, MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
        body_count = len(embed_bodies)
        for i, embed_body in enumerate(embed_bodies, start=1):
            embed = create_embed(_Embed.Empty, description=embed_body, colour=colour)
            if title and title != _Embed.Empty and (i == 1 or repeat_title):
                embed.set_author(name=title, url=author_url or _Embed.Empty, icon_url=icon_url or _Embed.Empty)
            if thumbnail_url and (i == 1 or repeat_thumbnail):
                embed.set_thumbnail(url=thumbnail_url)
            if image_url and (i == body_count or repeat_image):
                embed.set_image(url=image_url)
            if timestamp and (i == body_count or repeat_timestamp):
                embed.set_footer(text=ZERO_WIDTH_SPACE, icon_url=_Embed.Empty)
                embed.timestamp = timestamp
            if footer and (i == body_count or repeat_footer):
                embed.set_footer(text=footer, icon_url=footer_icon_url or _Embed.Empty)
            result.append(embed)
        return result
    else:
        return [create_embed(title, colour=colour, thumbnail_url=thumbnail_url, image_url=image_url, icon_url=icon_url, author_url=author_url, footer=footer, timestamp=timestamp)]


def create_basic_embeds_from_fields(title: str, repeat_title: bool = True, description: str = None, repeat_description: bool = True, colour: _Colour = None, fields: _List[_Tuple[str, str, bool]] = None, thumbnail_url: str = None, repeat_thumbnail: bool = True, image_url: str = None, repeat_image: bool = True, icon_url: str = None, author_url: str = None, footer: str = None, footer_icon_url: str = None, repeat_footer: bool = True, timestamp: _datetime = None, repeat_timestamp: bool = True) -> _List[_Embed]:
    result = []
    if fields:
        embed_fields = list(_utils.chunk_list(fields, 25))
        body_count = len(embed_fields)
        for i, embed_fields in enumerate(embed_fields, start=1):
            embed = create_embed(_Embed.Empty, fields=embed_fields, colour=colour)
            if title and title != _Embed.Empty and (i == 1 or repeat_title):
                embed.set_author(name=title, url=author_url or _Embed.Empty, icon_url=icon_url or _Embed.Empty)
            if description and (i == 1 or repeat_description):
                embed.description = description
            if thumbnail_url and (i == 1 or repeat_thumbnail):
                embed.set_thumbnail(url=thumbnail_url)
            if image_url and (i == body_count or repeat_image):
                embed.set_image(url=image_url)
            if timestamp and (i == body_count or repeat_timestamp):
                embed.set_footer(text=ZERO_WIDTH_SPACE, icon_url=_Embed.Empty)
                embed.timestamp = timestamp
            if footer and (i == body_count or repeat_footer):
                embed.set_footer(text=footer, icon_url=footer_icon_url or _Embed.Empty)
            result.append(embed)
        return result
    else:
        return [create_embed(title, colour=colour, thumbnail_url=thumbnail_url, image_url=image_url, icon_url=icon_url, author_url=author_url, footer=footer, timestamp=timestamp)]


def create_embed(title: str, description: str = None, colour: _Colour = None, fields: _List[_Tuple[str, str, bool]] = None, thumbnail_url: str = None, image_url: str = None, icon_url: str = None, author_url: str = None, footer: str = None, footer_icon_url: str = None, timestamp: _datetime = None) -> _Embed:
    result = _Embed(title=_Embed.Empty, description=description or _Embed.Empty, colour=colour or _Embed.Empty, timestamp=timestamp or _Embed.Empty)
    if title and title != _Embed.Empty:
        result.set_author(name=title, url=author_url or _Embed.Empty, icon_url=icon_url or _Embed.Empty)
    if fields is not None:
        for t in fields:
            result.add_field(name=t[0], value=t[1], inline=t[2])
    if thumbnail_url:
        result.set_thumbnail(url=thumbnail_url)
    if image_url:
        result.set_image(url=image_url)
    if footer:
        result.set_footer(text=footer, icon_url=footer_icon_url or _Embed.Empty)
    elif timestamp:
        result.set_footer(text=ZERO_WIDTH_SPACE, icon_url=_Embed.Empty)

    return result


def create_posts_from_lines(lines: _List[str], char_limit: int) -> _List[str]:
    result = []
    current_post = ''

    for line in lines:
        line_length = len(line)
        new_post_length = 1 + len(current_post) + line_length
        if new_post_length > char_limit:
            result.append(current_post)
            current_post = ''
        if len(current_post) > 0:
            current_post += '\n'

        current_post += line

    if current_post:
        result.append(current_post)

    if not result:
        result = ['']

    return result


async def dm_author(ctx: _Context, output: _Union[_List[_Embed], _List[str]], output_is_embeds: bool = False, maximum_characters: int = MAXIMUM_CHARACTERS) -> None:
    if output and ctx.author:
        await post_output_to_channel(ctx.author, output, output_is_embeds=output_is_embeds, maximum_characters=maximum_characters)


def get_bot_member_colour(bot: _Bot, guild: _Guild) -> _Colour:
    try:
        bot_member = guild.get_member(bot.user.id)
        bot_colour = bot_member.colour
        return bot_colour
    except:
        return _Embed.Empty


def get_embed_field_def(title: str = None, text: str = None, inline: bool = True) -> _Tuple[str, str, bool]:
    return (title, text, inline)


def get_exact_args(ctx: _Context, additional_parameters: int = 0) -> str:
    try:
        if ctx.command.full_parent_name:
            full_parent_command = f'{ctx.prefix}{ctx.command.full_parent_name} '
        else:
            full_parent_command = f'{ctx.prefix}'
        command_names = [ctx.command.name]
        if ctx.command.aliases:
            command_names.extend(ctx.command.aliases)
        command_names = [_escape(command_name) for command_name in command_names]
        rx_command_names = '|'.join(command_names)
        rx_command = f'{_escape(full_parent_command)}({rx_command_names}) (.*? ){{{additional_parameters}}}'
        rx_match = _search(rx_command, ctx.message.content)
        if rx_match is not None:
            return str(ctx.message.content[len(rx_match.group(0)):])
        else:
            return ''
    except:
        return ''


def is_guild_channel(channel: _Messageable) -> bool:
    if hasattr(channel, 'guild') and channel.guild:
        return True
    else:
        return False


async def post_output(ctx: _Context, output: _Union[_List[_Embed], _List[str]], maximum_characters: int = MAXIMUM_CHARACTERS) -> None:
    if output and ctx.channel:
        output_is_embeds = isinstance(output[0], _Embed)
        await post_output_to_channel(ctx.channel, output, output_is_embeds=output_is_embeds, maximum_characters=maximum_characters)


async def post_output_to_channel(channel: _Union[_TextChannel, _Member, _User], output: _Union[_List[_Embed], _List[str]], output_is_embeds: bool = False, maximum_characters: int = MAXIMUM_CHARACTERS) -> None:
    if output and channel:
        output = __prepare_output(output)

        if output_is_embeds:
            posts = _chunk_embeds(output)
        else:
            posts = create_posts_from_lines(output, maximum_characters)
        for post in posts:
            if post:
                if output_is_embeds:
                    await channel.send(embeds=post)
                else:
                    await channel.send(post)


async def post_output_with_files(ctx: _Context, output: _Union[_List[_Embed], _List[str]], file_paths: _List[str], output_is_embeds: bool = False, maximum_characters: int = MAXIMUM_CHARACTERS) -> None:
    if output or file_paths:
        if output:
            output = __prepare_output(output)

        if output_is_embeds:
            posts = _chunk_embeds(output)
        else:
            posts = create_posts_from_lines(output, maximum_characters)
        last_post_index = len(posts) - 1
        files = [_File(file_path) for file_path in file_paths]
        if last_post_index >= 0:
            for i, post in enumerate(posts):
                if output_is_embeds:
                    await ctx.send(embeds=post)
                else:
                    if i == last_post_index and post or files:
                        await ctx.send(content=post, files=files)
                    elif post:
                        await ctx.send(content=post)
            if output_is_embeds and files:
                await ctx.send(files=files)


def __prepare_output(output: _Union[_List[str], _List[_Embed]]) -> _Union[_List[str], _List[_Embed]]:
    if output[-1] == ZERO_WIDTH_SPACE:
        output = output[:-1]
    if output[0] == ZERO_WIDTH_SPACE:
        output = output[1:]
    return output


async def reply_with_output(ctx: _Context, output: _Union[_List[_Embed], _List[str]], maximum_characters: int = MAXIMUM_CHARACTERS, mention_author: bool = False) -> _Message:
    """
    Returns the last message created or None, of output has not been specified.
    """
    result = None
    if output:
        output_is_embeds = isinstance(output[0], _Embed)
        output = __prepare_output(output)

        if output_is_embeds:
            posts = _chunk_embeds(output)
        else:
            posts = create_posts_from_lines(output, maximum_characters)
        first_post, *posts = posts

        if output_is_embeds:
            if (await original_message_exists(ctx)):
                result = await ctx.reply(embeds=first_post, mention_author=mention_author)
            else:
                result = await ctx.send(embeds=first_post)

            for post in posts:
                result = await ctx.send(embeds=post)
        else:
            if (await original_message_exists(ctx)):
                result = await ctx.reply(content=first_post, mention_author=mention_author)
            else:
                result = await ctx.send(content=first_post)

            for post in posts:
                result = await ctx.send(content=post)
    return result


async def original_message_exists(ctx: _Context) -> bool:
    if not ctx.message:
        return False
    try:
        await ctx.fetch_message(ctx.message.id) #try to fetch the message
        return True
    except _NotFound: #if a NotFound error appears, the message is either not in this channel or deleted
        return False



async def respond_with_output(ctx: _ApplicationContext, output: _Union[_List[_Embed], _List[str]], maximum_characters: int = MAXIMUM_CHARACTERS, ephemeral: bool = False, view: _View = _MISSING) -> _Union[_Interaction, _WebhookMessage]:
    """
    Returns the last message created or None, if output has not been specified.
    """
    result = None
    if output:
        output_is_embeds = isinstance(output[0], _Embed)
        output = __prepare_output(output)

        if output_is_embeds:
            posts = output
            post_groups = _chunk_embeds(posts)
            for post_group in post_groups:
                result = await ctx.respond(embeds=post_group, ephemeral=ephemeral, view=view)
        else:
            posts = create_posts_from_lines(output, maximum_characters)
            for post in posts:
                result = await ctx.respond(content=post, ephemeral=ephemeral, view=view)
    return result


async def reply_with_output_and_files(ctx: _Context, output: _Union[_List[_Embed], _List[str]], file_paths: _List[str], output_is_embeds: bool = False, maximum_characters: int = MAXIMUM_CHARACTERS, mention_author: bool = False) -> None:
    """
    Returns the last message created or None, if neither output nor files have been specified.
    """
    result = None
    if output or file_paths:
        if output:
            output = __prepare_output(output)

        if output_is_embeds:
            posts = _chunk_embeds(output)
        else:
            posts = create_posts_from_lines(output, maximum_characters)
        first_post, *posts = posts
        if posts:
            *posts, last_post = posts
        else:
            last_post = None

        files = [_File(file_path) for file_path in file_paths] or None

        if last_post:
            if output_is_embeds:
                await ctx.reply(embeds=first_post, mention_author=mention_author)
                for post in posts:
                    await ctx.send(embeds=post)
                result = await ctx.send(embeds=last_post)
                if files:
                    result = await ctx.send(files=files)
            else:
                await ctx.reply(content=first_post, mention_author=mention_author)
                for post in posts:
                    await ctx.send(content=post)
                result = await ctx.send(content=last_post, files=files)
        else:
            if output_is_embeds:
                result = await ctx.reply(embeds=first_post, mention_author=mention_author)
                if files:
                    result = await ctx.send(files=files)
            else:
                result = await ctx.send(content=first_post, files=files)
    return result


async def respond_with_output_and_files(ctx: _ApplicationContext, output: _Union[_List[_Embed], _List[str]], file_paths: _List[str], maximum_characters: int = MAXIMUM_CHARACTERS, ephemeral: bool = False) -> _Union[_Interaction, _WebhookMessage]:
    """
    Returns the last message created or None, if output has not been specified.
    """
    result = None
    if output:
        output_is_embeds = isinstance(output[0], _Embed)
        output = __prepare_output(output)

        if output_is_embeds:
            posts = _chunk_embeds(output)
        else:
            posts = create_posts_from_lines(output, maximum_characters)

        first_post, posts, last_post = _split_posts(posts)
        files = [_File(file_path) for file_path in file_paths] or None
        kwarg_name = 'embeds' if output_is_embeds else 'content'

        if first_post:
            first_kwargs = {kwarg_name: first_post}
            await ctx.respond(**first_kwargs, ephemeral=ephemeral)
        for post in posts:
            post_kwargs = {kwarg_name: post}
            await ctx.respond(**post_kwargs, ephemeral=ephemeral)
        if last_post:
            last_kwargs = {kwarg_name: last_post}
            await ctx.respond(**last_kwargs, files=files, ephemeral=ephemeral)
    return result


async def edit_original_message(
    interaction: _Interaction,
    output: _Optional[_Union[_List[_Embed], _List[str]]] = None,
    content: _Optional[str] = _MISSING,
    embeds: _Optional[_List[_Embed]] = _MISSING,
    file_paths: _Optional[_List[str]] = _MISSING,
    view: _View = _MISSING
) -> _Interaction:
    if output is not None and (content and content != _MISSING or embeds and embeds != _MISSING):
        raise ValueError('You must either specify only output or content and/or embeds!')

    result = None
    files = [_File(file_path) for file_path in file_paths] if file_paths else _MISSING
    if output:
        output_is_embeds = isinstance(output[0], _Embed)
        output = __prepare_output(output)

        if output_is_embeds:
            posts = _chunk_embeds(output)
        else:
            posts = create_posts_from_lines(output, MAXIMUM_CHARACTERS)
        post = posts[0]

        if output_is_embeds:
            kwargs = {
                'content': None,
                'embeds': post,
            }
        else:
            kwargs = {
                'content': post,
                'embeds': None,
            }
    else:
        kwargs = {
            'content': content,
            'embeds': embeds,
        }
    result = await interaction.edit_original_message(files=files, view=view, **kwargs)
    return result


async def try_delete_message(message: _Message) -> bool:
    try:
        await message.delete()
        return True
    except _Forbidden:
        return False
    except _NotFound:
        return True


async def try_delete_original_message(ctx: _Context) -> bool:
    return await try_delete_message(ctx.message)


async def try_remove_reaction(reaction: _Reaction, user: _User) -> bool:
    try:
        await reaction.remove(user)
        return True
    except _Forbidden:
        return False


def _chunk_embeds(embeds: _List[_Embed]) -> _List[_List[_Embed]]:
    if not embeds:
        return []
    current_result = []
    current_length = 0
    result = []
    while embeds:
        embed = embeds.pop(0)
        if current_length + len(embed) >= 6000 or len(current_result) == 10:
            result.append(current_result)
            current_result = []
            current_length = 0
        current_result.append(embed)
        current_length += len(embed)
    if current_result:
        result.append(current_result)
    return result


def _split_posts(posts: _List[_Any]) -> _Tuple[_Optional[_Any], _List[_Any], _Optional[_Any]]:
    if posts:
        first_post, *posts = posts
        if posts:
            *posts, last_post = posts
        else:
            last_post = first_post
            first_post = None
        return first_post, posts, last_post
    return None, [], None