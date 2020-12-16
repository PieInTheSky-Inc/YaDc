from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import calendar
import datetime
import logging
import json
import os
import pytz
import sys
from typing import List, Tuple, Union

import asyncio
from discord import Activity, ActivityType, Message, Embed, Guild, TextChannel
from discord import __version__ as discord_version
from discord.ext.commands import Bot, BucketType, Context, cooldown, is_owner, when_mentioned_or
import discord.errors as errors
import discord.ext.commands.errors as command_errors
import holidays

import database as db
from gdrive import TourneyDataClient
import pagination
import pss_achievement as achievement
import pss_ai as ai
import pss_core as core
import pss_crew as crew
import pss_daily as daily
import pss_dropship as dropship
from pss_exception import Error, InvalidParameterValueError, MissingParameterError, NotFound, ParameterTypeError
import pss_fleet as fleet
import pss_gm as gm
import pss_item as item
import pss_login as login
import pss_lookups as lookups
import pss_mission as mission
import pss_promo as promo
import pss_raw as raw
import pss_research as research
import pss_room as room
import pss_ship as ship
import pss_tournament as tourney
import pss_top
import pss_training as training
import pss_user as user
import server_settings
from server_settings import GUILD_SETTINGS
import settings
import utils





# ############################################################################ #
# ----------                       Bot Setup                        ---------- #
# ############################################################################ #

async def get_prefix(bot: Bot, message: Message) -> str:
    result = await server_settings.get_prefix(bot, message)
    return when_mentioned_or(result)(bot, message)


BOT = Bot(command_prefix=get_prefix,
                    description='This is a Discord Bot for Pixel Starships',
                    activity=Activity(type=ActivityType.playing, name='/help'))

__COMMANDS = []
COOLDOWN: float = 15.0

PWD: str = os.getcwd()

RATE: int = 5
RAW_COOLDOWN: float = 10.0
RAW_RATE: int = 5

TOURNEY_DATA_CLIENT: TourneyDataClient = TourneyDataClient(
    settings.GDRIVE_PROJECT_ID,
    settings.GDRIVE_PRIVATE_KEY_ID,
    settings.GDRIVE_PRIVATE_KEY,
    settings.GDRIVE_CLIENT_EMAIL,
    settings.GDRIVE_CLIENT_ID,
    settings.GDRIVE_SCOPES,
    settings.GDRIVE_FOLDER_ID,
    settings.GDRIVE_SERVICE_ACCOUNT_FILE,
    settings.GDRIVE_SETTINGS_FILE,
    settings.TOURNAMENT_DATA_START_DATE
)

logging.basicConfig(
    level=logging.INFO,
    style = '{',
    datefmt = '%Y%m%d %H:%M:%S',
    format = '{asctime} [{levelname:<8}] {name}: {message}')

setattr(BOT, 'logger', logging.getLogger('bot.py'))










# ############################################################################ #
# ----------                       Bot Events                       ---------- #
# ############################################################################ #

@BOT.event
async def on_ready() -> None:
    print(f'sys.argv: {sys.argv}')
    print(f'Current Working Directory: {PWD}')
    print(f'Bot logged in as {BOT.user.name} (id={BOT.user.id}) on {len(BOT.guilds)} servers')
    await db.init()
    schema_version = await db.get_schema_version()
    await server_settings.init(BOT)
    await server_settings.clean_up_invalid_server_settings(BOT)
    await login.init()
    await daily.init()

    await crew.init()
    await item.init()
    await room.init()
    await user.init()
    global __COMMANDS
    __COMMANDS = sorted([key for key, value in BOT.all_commands.items() if value.hidden == False])
    print(f'Initialized!')
    print(f'Bot version is: {settings.VERSION}')
    schema_version = await db.get_schema_version()
    print(f'DB schema version is: {schema_version}')
    print(f'discord.py version: {discord_version}')
    BOT.loop.create_task(post_dailies_loop())


@BOT.event
async def on_connect():
    print('+ on_connect()')


@BOT.event
async def on_resumed():
    print('+ on_resumed()')


@BOT.event
async def on_disconnect():
    print('+ on_disconnect()')


@BOT.event
async def on_shard_ready():
    print('+ on_shard_ready()')


@BOT.event
async def on_command_error(ctx: Context, err: Exception) -> None:
    __log_command_use_error(ctx, err)

    if settings.THROW_COMMAND_ERRORS:
        raise err
    else:
        error_type = type(err).__name__
        error_message = str(err)
        retry_after = None
        if isinstance(err, command_errors.CommandOnCooldown):
            error_message += f'\nThis message will delete itself, when you may use the command again.'
            retry_after = err.retry_after
        elif isinstance(err, command_errors.CommandNotFound):
            prefix = await server_settings.get_prefix(BOT, ctx.message)
            invoked_with = ctx.invoked_with.split(' ')[0]
            commands_map = utils.get_similarity_map(__COMMANDS, invoked_with)
            bot_commands = [f'`{prefix}{command}`' for command in sorted(commands_map[max(commands_map.keys())])]
            error_message = f'Command `{prefix}{invoked_with}` not found. Do you mean {utils.format.get_or_list(bot_commands)}?'
        elif isinstance(err, command_errors.CheckFailure):
            error_message = error_message or 'You don\'t have the required permissions in order to be able to use this command!'
        elif isinstance(err, command_errors.CommandInvokeError):
            if err.original:
                error_type = type(err.original).__name__
                if isinstance(err.original, Error):
                    error_message = f'`{ctx.message.clean_content}`\n{err.original.msg}'
                else:
                    error_message = f'`{ctx.message.clean_content}`\n{err.original}'
        else:
            if not isinstance(err, command_errors.MissingRequiredArgument):
                logging.getLogger().error(err, exc_info=True)
            command_args = utils.discord.get_exact_args(ctx)
            help_args = ctx.message.clean_content.replace(command_args, '').strip()[1:]
            command = BOT.get_command(help_args)
            try:
                await ctx.send_help(command)
            except errors.Forbidden:
                __log_command_use_error(ctx, err, force_printing=True)

        as_embed = await server_settings.get_use_embeds(ctx)
        try:

            if as_embed:
                colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
                if retry_after:
                    error_message = f'{ctx.author.mention}\n{error_message}'
                embed = utils.discord.create_embed(error_type, description=error_message, colour=colour)
                await ctx.send(embed=embed, delete_after=retry_after)
            else:
                error_message = '\n'.join([f'> {x}' for x in error_message.splitlines()])
                if retry_after:
                    error_message = f'> {ctx.author.mention}\n{error_message}'
                await ctx.send(f'**{error_type}**\n{error_message}', delete_after=retry_after)
        except errors.Forbidden:
            __log_command_use_error(ctx, err, force_printing=True)


@BOT.event
async def on_guild_join(guild: Guild) -> None:
    print(f'Joined guild with id {guild.id} ({guild.name})')
    success = await GUILD_SETTINGS.create_guild_settings(BOT, guild.id)
    if not success:
        print(f'[on_guild_join] Could not create server settings for guild \'{guild.name}\' (ID: \'{guild.id}\')')


@BOT.event
async def on_guild_remove(guild: Guild) -> None:
    print(f'Left guild with id {guild.id} ({guild.name})')
    success = await GUILD_SETTINGS.delete_guild_settings(guild.id)
    if not success:
        print(f'[on_guild_join] Could not delete server settings for guild \'{guild.name}\' (ID: \'{guild.id}\')')










# ############################################################################ #
# ----------                         Tasks                          ---------- #
# ############################################################################ #

async def post_dailies_loop() -> None:
    print(f'Started post dailies loop')
    utc_now = utils.get_utc_now()
    while utc_now < settings.POST_AUTODAILY_FROM:
        wait_for = utils.datetime.get_seconds_to_wait(60, utc_now=utc_now)
        await asyncio.sleep(wait_for)
        utc_now = utils.get_utc_now()

    while True:
        utc_now = utils.get_utc_now()
        yesterday = datetime.datetime(utc_now.year, utc_now.month, utc_now.day) - utils.datetime.ONE_SECOND

        daily_info = await daily.get_daily_info()
        db_daily_info, db_daily_modify_date = await daily.db_get_daily_info()
        has_daily_changed = daily.has_daily_changed(daily_info, utc_now, db_daily_info, db_daily_modify_date)

        autodaily_settings = await server_settings.get_autodaily_settings(BOT, no_post_yet=True)
        if autodaily_settings:
            print(f'[post_dailies_loop] retrieved {len(autodaily_settings)} channels')
        if has_daily_changed:
            print(f'[post_dailies_loop] daily info changed:\n{json.dumps(daily_info)}')
            post_here = await server_settings.get_autodaily_settings(BOT)
            print(f'[post_dailies_loop] retrieved {len(post_here)} guilds to post')
            autodaily_settings.extend(post_here)

        created_output = False
        posted_count = 0
        if autodaily_settings:
            autodaily_settings = daily.remove_duplicate_autodaily_settings(autodaily_settings)
            print(f'[post_dailies_loop] going to post to {len(autodaily_settings)} guilds')

            latest_message_output_text, latest_message_output_embeds, _ = await dropship.get_dropship_text(daily_info=db_daily_info)
            latest_daily_message = '\n'.join(latest_message_output_text)
            lastest_daily_embed = latest_message_output_embeds[0]
            output, output_embeds, created_output = await dropship.get_dropship_text(daily_info=daily_info)
            if created_output:
                current_daily_message = '\n'.join(output)
                current_daily_embed = output_embeds[0]
                posted_count = await post_dailies(current_daily_message, current_daily_embed, autodaily_settings, utc_now, yesterday, latest_daily_message, lastest_daily_embed)
            print(f'[post_dailies_loop] posted to {posted_count} of {len(autodaily_settings)} guilds')

        if has_daily_changed:
            if created_output or not autodaily_settings:
                await daily.db_set_daily_info(daily_info, utc_now)

        seconds_to_wait = utils.datetime.get_seconds_to_wait(5)
        await asyncio.sleep(seconds_to_wait)


async def post_dailies(current_daily_message: str, current_daily_embed: Embed, autodaily_settings: List[server_settings.AutoDailySettings], utc_now: datetime.datetime, yesterday: datetime.datetime, latest_daily_message_contents: str, latest_daily_message_embed: Embed) -> int:
    posted_count = 0
    for settings in autodaily_settings:
        if settings.guild.id is not None and settings.channel_id is not None:
            posted, can_post, latest_message = await post_autodaily(settings.channel, settings.latest_message_id, settings.change_mode, current_daily_message, current_daily_embed, utc_now, yesterday, latest_daily_message_contents, latest_daily_message_embed)
            if posted:
                posted_count += 1
            await settings.update(can_post=can_post, latest_message=latest_message, store_now_as_created_at=(not can_post and not latest_message))
    return posted_count


async def post_autodaily(text_channel: TextChannel, latest_message_id: int, change_mode: bool, current_daily_message: str, current_daily_embed: Embed, utc_now: datetime.datetime, yesterday: datetime.datetime, latest_daily_message_contents: str, latest_daily_message_embed: Embed) -> Tuple[bool, bool, Message]:
    """
    Returns (posted, can_post, latest_message)
    """
    posted = False
    if text_channel and current_daily_message:
        error_msg_delete = f'could not delete message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_edit = f'could not edit message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_post = f'could not post a message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]'

        if change_mode == server_settings.AutoDailyChangeMode.EDIT:
            post_new = False
        else:
            post_new = True

        can_post = True
        latest_message: Message = None

        if can_post:
            can_post, latest_message = await daily_fetch_latest_message(text_channel, latest_message_id, yesterday, latest_daily_message_contents, current_daily_message, latest_daily_message_embed, current_daily_embed)

        if can_post:
            if latest_message and latest_message.created_at.day == utc_now.day:
                latest_message_id = latest_message.id
                if dropship.compare_dropship_messages(latest_message, current_daily_message, current_daily_embed):
                    post_new = False
                elif change_mode == server_settings.AutoDailyChangeMode.DELETE_AND_POST_NEW:
                    try:
                        await latest_message.delete()
                        latest_message = None
                        print(f'[post_autodaily] deleted message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                    except errors.NotFound:
                        print(f'[post_autodaily] {error_msg_delete}: the message could not be found')
                    except errors.Forbidden:
                        print(f'[post_autodaily] {error_msg_delete}: the bot doesn\'t have the required permissions.')
                        can_post = False
                    except Exception as err:
                        print(f'[post_autodaily] {error_msg_delete}: {err}')
                        can_post = False
                elif change_mode == server_settings.AutoDailyChangeMode.EDIT:
                    try:
                        await latest_message.edit(content=current_daily_message)
                        posted = True
                        print(f'[post_autodaily] edited message [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                    except errors.NotFound:
                        print(f'[post_autodaily] {error_msg_edit}: the message could not be found')
                    except errors.Forbidden:
                        print(f'[post_autodaily] {error_msg_edit}: the bot doesn\'t have the required permissions.')
                        can_post = False
                    except Exception as err:
                        print(f'[post_autodaily] {error_msg_edit}: {err}')
                        can_post = False
            else:
                post_new = True

            if can_post and post_new:
                try:
                    use_embeds = await server_settings.get_use_embeds(None, bot=BOT, guild=text_channel.guild)
                    if use_embeds:
                        colour = utils.discord.get_bot_member_colour(BOT, text_channel.guild)
                        embed = current_daily_embed.copy()
                        embed.colour = colour
                        latest_message = await text_channel.send(embed=embed)
                    else:
                        latest_message = await text_channel.send(current_daily_message)
                    posted = True
                    print(f'[post_autodaily] posted message [{latest_message.id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                except errors.Forbidden:
                    print(f'[post_autodaily] {error_msg_post}: the bot doesn\'t have the required permissions.')
                    can_post = False
                except Exception as err:
                    print(f'[post_autodaily] {error_msg_post}: {err}')
                    can_post = False
        else:
            can_post = False

        if latest_message:
            return posted, can_post, latest_message
        else:
            return posted, can_post, None
    else:
        return posted, None, None


async def daily_fetch_latest_message(text_channel: TextChannel, latest_message_id: int, yesterday: datetime.datetime, latest_daily: str, current_daily: str, latest_daily_embed: Embed, current_daily_embed: Embed) -> Tuple[bool, Message]:
    """
    Attempts to fetch the message by id, then by content from the specified channel.
    Returns (can_post, latest_message)
    """
    can_post: bool = True
    result: Message = None

    if text_channel:
        if latest_message_id is not None:
            try:
                result = await text_channel.fetch_message(latest_message_id)
                print(f'[daily_fetch_latest_message] found latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
            except errors.NotFound:
                print(f'[daily_fetch_latest_message] could not find latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
            except Exception as err:
                print(f'[daily_fetch_latest_message] could not fetch message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {err}')
                can_post = False
        if result is None:
            try:
                async for message in text_channel.history(after=yesterday):
                    if message.author == BOT.user and (dropship.compare_dropship_messages(message, latest_daily, latest_daily_embed) or dropship.compare_dropship_messages(message, current_daily, current_daily_embed)) and (message.content == latest_daily or message.content == current_daily):
                        result = message
                        print(f'[daily_fetch_latest_message] found latest message by content in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {result.id}')
                        break
            except Exception as err:
                print(f'[daily_fetch_latest_message] could not find latest message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {err}')
                can_post = False
            if result is None:
                print(f'[daily_fetch_latest_message] could not find latest message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')

    return can_post, result










# ############################################################################ #
# ----------                  General Bot Commands                  ---------- #
# ############################################################################ #

@BOT.command(name='about', aliases=['info'], brief='Display info on this bot')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_about(ctx: Context):
    """
    Displays information about this bot and its authors.

    Usage:
      /about
      /info

    Examples:
      /about - Displays information on this bot and its authors.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        guild_count = len([guild for guild in BOT.guilds if guild.id not in settings.IGNORE_SERVER_IDS_FOR_COUNTING])
        user_name = BOT.user.display_name
        if ctx.guild is None:
            nick = BOT.user.display_name
        else:
            nick = ctx.guild.me.display_name
        has_nick = BOT.user.display_name != nick
        pfp_url = BOT.user.avatar_url
        about_info = core.read_about_file()

        title = f'About {nick}'
        if has_nick:
            title += f' ({user_name})'
        description = about_info['description']
        footer = f'Serving on {guild_count} guild{"" if guild_count == 1 else "s"}.'
        fields = [
            ('version', f'v{settings.VERSION}', True),
            ('authors', ', '.join(about_info['authors']), True),
            ('profile pic by', about_info['pfp'], True),
            ('support', about_info['support'], False)
        ]
        colour = utils.discord.get_bot_member_colour(BOT, ctx.guild)

        embed = utils.discord.create_embed(title, description=description, colour=colour, fields=fields, thumbnail_url=pfp_url, footer=footer)
    await utils.discord.post_output(ctx, [embed])


@BOT.command(name='invite', brief='Get an invite link')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_invite(ctx: Context):
    """
    Produces an invite link for this bot and sends it via DM.

    Usage:
      /invite

    Examples:
      /invite - Produces an invite link for this bot and sends it via DM.
    """
    __log_command_use(ctx)

    async with ctx.typing():
        as_embed = await server_settings.get_use_embeds(ctx)

        if ctx.guild is None:
            nick = BOT.user.display_name
        else:
            nick = ctx.guild.me.display_name
        title = f'Invite {nick} to your server'
        invite_url = f'{settings.BASE_INVITE_URL}{BOT.user.id}'
        colour = None

        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            description = f'[{title}]({invite_url})'
            output = utils.discord.create_embed(None, description=description, colour=colour)
        else:
            output = f'{title}: {invite_url}'
    await utils.discord.dm_author(ctx, [output], output_is_embeds=as_embed)
    if utils.discord.is_guild_channel(ctx.channel):
        notice = f'{ctx.author.mention} Sent invite link via DM.'
        if as_embed:
            notice = utils.discord.create_embed(None, description=notice, colour=colour)
        await utils.discord.post_output(ctx, [notice])


@BOT.command(name='links', brief='Show links')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_links(ctx: Context):
    """
    Shows the links for useful sites regarding Pixel Starships.

    Usage:
      /links

    Examples:
      /links - Shows the links for useful sites regarding Pixel Starships.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        links = core.read_links_file()
        output = []
        if (await server_settings.get_use_embeds(ctx)):
            title = 'Pixel Starships weblinks'
            colour = utils.discord.get_bot_member_colour(BOT, ctx.guild)
            fields = []
            for field_name, hyperlinks in links.items():
                field_value = []
                for (description, hyperlink) in hyperlinks:
                    field_value.append(f'[{description}]({hyperlink})')
                fields.append((field_name, '\n'.join(field_value), False))
            embed = utils.discord.create_embed(title, fields=fields, colour=colour)
            output.append(embed)
        else:
            for category, hyperlinks in links.items():
                output.append(f'**{category}**')
                for (description, hyperlink) in hyperlinks:
                    output.append(f'{description}: <{hyperlink}>')
                output.append(utils.discord.ZERO_WIDTH_SPACE)
            if output:
                output = output[:-1]
    await utils.discord.post_output(ctx, output)


@BOT.command(name='ping', brief='Ping the server')
async def cmd_ping(ctx: Context):
    """
    Ping the bot to verify that it\'s listening for commands.

    Usage:
      /ping

    Examples:
      /ping - The bot will answer with 'Pong!'.
    """
    __log_command_use(ctx)
    msg = await ctx.send('Pong!')
    miliseconds = (msg.created_at - ctx.message.created_at).microseconds / 1000.0
    await msg.edit(content=f'{msg.content} ({miliseconds} ms)')


@BOT.command(name='support', brief='Invite to bot\'s support server')
async def cmd_support(ctx: Context):
    """
    Produces an invite link to the support server for this bot and sends it via DM.

    Usage:
      /support

    Examples:
      /support - Produces an invite link to the support server and sends it via DM.
    """
    __log_command_use(ctx)

    async with ctx.typing():
        as_embed = await server_settings.get_use_embeds(ctx)

        if ctx.guild is None:
            nick = BOT.user.display_name
        else:
            nick = ctx.guild.me.display_name
        about = core.read_about_file()
        title = f'Join {nick} support server'
        colour = None
        guild_invite = about['support']

        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            description = f'[{title}]({guild_invite})'
            output = utils.discord.create_embed(None, description=description, colour=colour)
        else:
            output = f'{title}: {guild_invite}'
    await utils.discord.dm_author(ctx, [output], output_is_embeds=as_embed)
    if utils.discord.is_guild_channel(ctx.channel):
        notice = f'{ctx.author.mention} Sent invite link to bot support server via DM.'
        if as_embed:
            notice = utils.discord.create_embed(None, description=notice, colour=colour)
        await utils.discord.post_output(ctx, [notice])










# ############################################################################ #
# ----------                    PSS Bot Commands                    ---------- #
# ############################################################################ #

@BOT.command(name='best', brief='Get best items for a slot')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_best(ctx: Context, slot: str, *, stat: str = None):
    """
    Get the best enhancement item for a given slot. If multiple matches are found, matches will be shown in descending order according to their bonus.

    Usage:
      /best [slot] [stat]
      /best [item name]

    Parameters:
      slot: the equipment slot. Use 'all' or 'any' or omit this parameter to get info for all slots. Optional. Valid values are: [all/any (for all slots), head, hat, helm, helmet, body, shirt, armor, leg, pant, pants, weapon, hand, gun, accessory, shoulder, pet]
      stat: the crew stat you're looking for. Mandatory. Valid values are: [hp, health, attack, atk, att, damage, dmg, repair, rep, ability, abl, pilot, plt, science, sci, stamina, stam, stm, engine, eng, weapon, wpn, fire resistance, fire]
      item name: an item's name, whose slot and stat will be used to look up best data.

    Examples:
      /best hand atk - Prints all equipment items for the weapon slot providing an attack bonus.
      /best all hp - Prints all equipment items for all slots providing a HP bonus.
      /best hp - Prints all equipment items for all slots providing a HP bonus.
      /best storm lance - Prints all equipment items for the same slot and stat as a Storm Lance.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        item_name = slot
        if stat is not None:
            item_name += f' {stat}'
        item_name = item_name.strip().lower()

        if item_name not in lookups.EQUIPMENT_SLOTS_LOOKUP and item_name not in lookups.STAT_TYPES_LOOKUP:
            items_details = await item.get_items_details_by_name(item_name)
            found_matching_items = items_details and len(items_details) > 0
            items_details = item.filter_items_details_for_equipment(items_details)
        else:
            items_details = []
            found_matching_items = False
        if items_details:
            if len(items_details) == 1:
                item_details = items_details[0]
            else:
                use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
                paginator = pagination.Paginator(ctx, item_name, items_details, item.get_item_search_details, use_pagination)
                _, item_details = await paginator.wait_for_option_selection()
            slot, stat = item.get_slot_and_stat_type(item_details)
        else:
            if found_matching_items:
                raise ValueError(f'The item `{item_name}` is not a gear type item!')

        slot, stat = item.fix_slot_and_stat(slot, stat)
        output = await item.get_best_items(ctx, slot, stat, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='char', aliases=['crew'], brief='Get character stats')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_char(ctx: Context, level: str = None, *, crew_name: str = None):
    """
    Get the stats of a character/crew. If a level is specified, the stats will apply to the crew being on that level. Else the stats range form level 1 to 40 will be displayed.

    Usage:
      /stats <level> [name]

    Parameters:
      level: Level of a crew. Optional.
      name:  (Part of) the name of a crew. Mandatory.

    Examples:
      /stats hug - Will print the stats range for a crew having 'hug' in its name.
      /stats 25 hug - Will print the stats range for a level 25 crew having 'hug' in its name.

    Notes:
      This command will only print stats for the crew with the best matching crew_name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        level, crew_name = utils.get_level_and_name(level, crew_name)
        output = await crew.get_char_details_by_name(ctx, crew_name, level=level, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='craft', aliases=['upg', 'upgrade'], brief='Get crafting recipes')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_craft(ctx: Context, *, item_name: str):
    """
    Get the items a specified item can be crafted into.

    Usage:
      /craft [item_name]
      /upgrade [item_name]
      /upg [item_name]

    Parameters:
      item_name: (Part of) the name of an item to be upgraded. Mandatory.

    Examples:
      /craft large mineral crate - Prints all crafting options for a 'Large Mineral Crate'.

    Notes:
      This command will only print crafting costs for the item with the best matching item name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await item.get_item_upgrades_from_name(ctx, item_name, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='collection', aliases=['coll'], brief='Get collections')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_collection(ctx: Context, *, collection_name: str = None):
    """
    Get the details on a specific collection. If the collection name is omitted, it will display all collections.

    Usage:
      /collection <collection_name>

    Parameters:
      collection_name: The name of the collection to get details on.

    Examples:
      /collection savy - Will print information on a collection having 'savy' in its name.
      /collection - Will print less information on all collections.

    Notes:
      This command will only print stats for the collection with the best matching collection_name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await crew.get_collection_details_by_name(ctx, collection_name, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='daily', brief='Show the dailies')
@cooldown(rate=RATE, per=COOLDOWN*2, type=BucketType.user)
async def cmd_daily(ctx: Context):
    """
    Prints the MOTD along today's contents of the dropship, the merchant ship, the shop and the sale.

    Usage:
      /daily

    Examples:
      /daily - Prints the information described above.
    """
    __log_command_use(ctx)
    await utils.discord.try_delete_original_message(ctx)
    async with ctx.typing():
        as_embed = await server_settings.get_use_embeds(ctx)
        output, output_embed, _ = await dropship.get_dropship_text(ctx.bot, ctx.guild)
    if as_embed:
        await utils.discord.post_output(ctx, output_embed)
    else:
        await utils.discord.post_output(ctx, output)


@BOT.command(name='fleet', aliases=['alliance'], brief='Get infos on a fleet')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_fleet(ctx: Context, *, fleet_name: str):
    """
    Get details on a fleet. This command will also create a spreadsheet containing information on a fleet's members. If the provided fleet name does not match any fleet exactly, you will be prompted to select from a list of results. The selection prompt will time out after 60 seconds.

    Usage:
      /fleet [fleet_name]
      /alliance [fleet_name]

    Parameters:
      fleet_name: The (beginning of the) name of the fleet to search for. Mandatory.

    Examples:
      /fleet HYDRA - Offers a list of fleets having a name starting with 'HYDRA'. Upon selection prints fleet details and posts the spreadsheet.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        exact_name = utils.discord.get_exact_args(ctx)
        if exact_name:
            fleet_name = exact_name
        fleet_infos = await fleet.get_fleet_infos_by_name(fleet_name)

    if fleet_infos:
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
            paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details, use_pagination)
            _, fleet_info = await paginator.wait_for_option_selection()

        if fleet_info:
            async with ctx.typing():
                as_embed = await server_settings.get_use_embeds(ctx)
                max_tourney_battle_attempts = await tourney.get_max_tourney_battle_attempts()
                output, file_paths = await fleet.get_full_fleet_info_as_text(ctx, fleet_info, max_tourney_battle_attempts=max_tourney_battle_attempts, as_embed=as_embed)
            await utils.discord.post_output_with_files(ctx, output, file_paths, output_is_embeds=as_embed)
            for file_path in file_paths:
                os.remove(file_path)
    else:
        raise NotFound(f'Could not find a fleet named `{fleet_name}`.')


@BOT.command(name='ingredients', aliases=['ing'], brief='Get item ingredients')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_ingredients(ctx: Context, *, item_name: str):
    """
    Get the ingredients for an item to be crafted with their estimated crafting costs.

    Usage:
      /ingredients [item_name]
      /ing [item_name]

    Parameters:
      item_name: (Part of) the name of an item to be crafted. Mandatory.

    Examples:
      /ingredients large mineral crate - Prints the crafting costs and recipe for a 'Large Mineral Crate'.

    Notes:
      This command will only print crafting costs for the item with the best matching item name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await item.get_ingredients_for_item(ctx, item_name, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='item', brief='Get item stats')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_item(ctx: Context, *, item_name: str):
    """
    Get the stats of any item matching the given item_name.

    Usage:
      /item [item_name]

    Parameters:
      item_name:  (Part of) the name of an item. Mandatory.

    Examples:
      /item hug - Will print some stats for an item having 'hug' in its name.

    Notes:
      This command will print information for all items matching the specified name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await item.get_item_details_by_name(ctx, item_name, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='level', aliases=['lvl'], brief='Get crew levelling costs')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_level(ctx: Context, from_level: str, to_level: str = None):
    """
    Shows the cost for a crew to reach a certain level.

    Usage:
      /level <from_level> [to_level]
      /lvl <from_level> [to_level]

    Parameters:
      from_level: The level from which on the requirements shall be calculated. If specified, must be lower than [to_level]. Optional.
      to_level:   The level to which the requirements shall be calculated. Must be greater than 0 and lower than 41. Mandatory.

    Examples:
      /level 35 - Prints exp and gas requirements from level 1 to 35
      /level 25 35 - Prints exp and gas requirements from level 25 to 35"""
    __log_command_use(ctx)
    async with ctx.typing():
        if from_level and not to_level:
            to_level = from_level
            from_level = None

        if to_level:
            try:
                to_level = int(to_level)
            except:
                raise ParameterTypeError('Parameter `to_level` must be a natural number from 2 to 40.')
        if from_level:
            try:
                from_level = int(from_level)
            except:
                raise ParameterTypeError('Parameter `from_level` must be a natural number from 1 to 39.')

        if from_level and to_level and from_level >= to_level:
            raise ValueError('Parameter `from_level` must be smaller than parameter `to_level`.')
        output = crew.get_level_costs(ctx, from_level, to_level, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='news', brief='Show the news')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_news(ctx: Context, entry_count: str = '5'):
    """
    Prints all news in ascending order. You can

    Parameters:
      entry_count: Optional. The number of news to print. Defaults to 5.

    Usage:
      /news
      /news 3

    Examples:
      /news - Prints the latest 5 news in ascending order.
      /news 3 - Prints the latest 3 news in ascending order.
    """
    __log_command_use(ctx)
    try:
        take = int(entry_count)
    except (TypeError, ValueError) as ex:
        raise ParameterTypeError(f'The parameter `entry_count` must be an integer.') from ex
    await utils.discord.try_delete_original_message(ctx)
    async with ctx.typing():
        output = await dropship.get_news(ctx, take=take, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.group(name='past', aliases=['history'], brief='Get historic data', invoke_without_command=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_past(ctx: Context, month: str = None, year: str = None):
    """
    Get historic tournament data.

    Parameters:
      month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
      year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.

    You need to use one of the subcommands.
    """
    __log_command_use(ctx)
    await ctx.send_help('past')


@cmd_past.group(name='stars', brief='Get historic division stars', invoke_without_command=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_past_stars(ctx: Context, month: str = None, year: str = None, *, division: str = None):
    """
    Get historic tournament division stars data.

    Parameters:
      month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
      year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
      division: Optional. The division for which the data should be displayed. If not specified will print all divisions.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        utc_now = utils.get_utc_now()
        output = []

        (month, year, division) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')

        if not pss_top.is_valid_division_letter(division):
            subcommand = BOT.get_command('past stars fleet')
            await ctx.invoke(subcommand, month=month, year=year, fleet_name=division)
            return
        else:
            month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
            tourney_data = TOURNEY_DATA_CLIENT.get_data(year, month)
            if tourney_data:
                output = await pss_top.get_division_stars(ctx, division=division, fleet_data=tourney_data.fleets, retrieved_date=tourney_data.retrieved_at, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@cmd_past_stars.command(name='fleet', aliases=['alliance'], brief='Get historic fleet stars')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_past_stars_fleet(ctx: Context, month: str = None, year: str = None, *, fleet_name: str = None):
    """
    Get historic tournament fleet stars data.

    Parameters:
      month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
      year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
      fleet_name: Mandatory. The fleet for which the data should be displayed.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = []
        error = None
        utc_now = utils.get_utc_now()
        (month, year, fleet_name) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not fleet_name:
            raise MissingParameterError('The parameter `fleet_name` is mandatory.')

        month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
        tourney_data = TOURNEY_DATA_CLIENT.get_data(year, month)

        if tourney_data is None:
            fleet_infos = []
        else:
            fleet_infos = await fleet.get_fleet_infos_from_tourney_data_by_name(fleet_name, tourney_data.fleets)

    if fleet_infos:
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
            paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details, use_pagination)
            _, fleet_info = await paginator.wait_for_option_selection()

        if fleet_info:
            async with ctx.typing():
                output = await fleet.get_fleet_users_stars_from_tournament_data(ctx, fleet_info, tourney_data.fleets, tourney_data.users, tourney_data.retrieved_at, as_embed=(await server_settings.get_use_embeds(ctx)))
    elif error:
        raise Error(str(error))
    else:
        raise Error (f'Could not find a fleet named `{fleet_name}` that participated in the {year} {calendar.month_name[int(month)]} tournament.')
    await utils.discord.post_output(ctx, output)


@cmd_past.command(name='fleet', aliases=['alliance'], brief='Get historic fleet data')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_past_fleet(ctx: Context, month: str = None, year: str = None, *, fleet_name: str = None):
    """
    Get historic tournament fleet data.

    Parameters:
      month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
      year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
      fleet_name: Mandatory. The fleet for which the data should be displayed.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        error = None
        utc_now = utils.get_utc_now()
        (month, year, fleet_name) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not fleet_name:
            raise MissingParameterError('The parameter `fleet_name` is mandatory.')

        month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
        tourney_data = TOURNEY_DATA_CLIENT.get_data(year, month)

        if tourney_data is None:
            fleet_infos = []
        else:
            fleet_infos = await fleet.get_fleet_infos_from_tourney_data_by_name(fleet_name, tourney_data.fleets)

    if fleet_infos:
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
            paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details, use_pagination)
            _, fleet_info = await paginator.wait_for_option_selection()

        if fleet_info:
            async with ctx.typing():
                as_embed = await server_settings.get_use_embeds(ctx)
                output, file_paths = await fleet.get_full_fleet_info_as_text(ctx, fleet_info, past_fleets_data=tourney_data.fleets, past_users_data=tourney_data.users, past_retrieved_at=tourney_data.retrieved_at, as_embed=as_embed)
            await utils.discord.post_output_with_files(ctx, output, file_paths, output_is_embeds=as_embed)
            for file_path in file_paths:
                os.remove(file_path)
    elif error:
        raise Error(str(error))
    else:
        raise NotFound(f'Could not find a fleet named `{fleet_name}` that participated in the {year} {calendar.month_name[int(month)]} tournament.')


@cmd_past.command(name='fleets', aliases=['alliances'], brief='Get historic fleet data', hidden=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_past_fleets(ctx: Context, month: str = None, year: str = None):
    """
    Get historic tournament fleet data.

    Parameters:
      month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
      year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
      fleet_name: Mandatory. The fleet for which the data should be displayed.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        error = None
        utc_now = utils.get_utc_now()
        month, year = TourneyDataClient.retr
        (month, year, _) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')

        month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
        tourney_data = TOURNEY_DATA_CLIENT.get_data(year, month)

    if tourney_data and tourney_data.fleets and tourney_data.users:
        async with ctx.typing():
            file_name = f'tournament_results_{year}-{utils.datetime.get_month_short_name(tourney_data.retrieved_at).lower()}.csv'
            file_paths = [fleet.create_fleets_sheet_csv(tourney_data.users, tourney_data.retrieved_at, file_name)]
        await utils.discord.post_output_with_files(ctx, [], file_paths)
        for file_path in file_paths:
            os.remove(file_path)
    elif error:
        raise Error(str(error))
    else:
        raise Error(f'An error occured while retrieving tournament results for the {year} {calendar.month_name[int(month)]} tournament. Please contact the bot\'s author!')


@cmd_past.command(name='player', aliases=['user'], brief='Get historic player data')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_past_player(ctx: Context, month: str = None, year: str = None, *, player_name: str = None):
    """
    Get historic tournament player data.

    Parameters:
      month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
      year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
      player_name: Mandatory. The player for which the data should be displayed.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = []
        error = None
        utc_now = utils.get_utc_now()
        (month, year, player_name) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not player_name:
            raise MissingParameterError('The parameter `player_name` is mandatory.')

        month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
        try:
            tourney_data = TOURNEY_DATA_CLIENT.get_data(year, month)
        except ValueError as err:
            error = str(err)
            tourney_data = None

        if tourney_data is None:
            user_infos = []
        else:
            user_infos = await user.get_user_infos_from_tournament_data_by_name(player_name, tourney_data.users)

    if user_infos:
        if len(user_infos) == 1:
            user_info = user_infos[0]
        else:
            use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
            paginator = pagination.Paginator(ctx, player_name, user_infos, user.get_user_search_details, use_pagination)
            _, user_info = await paginator.wait_for_option_selection()

        if user_info:
            async with ctx.typing():
                output = await user.get_user_details_by_info(ctx, user_info, retrieved_at=tourney_data.retrieved_at, past_fleet_infos=tourney_data.fleets, as_embed=(await server_settings.get_use_embeds(ctx)))
    elif error:
        raise Error(str(error))
    else:
        raise NotFound(f'Could not find a player named `{player_name}` that participated in the {year} {calendar.month_name[int(month)]} tournament.')
    await utils.discord.post_output(ctx, output)


@BOT.command(name='player', aliases=['user'], brief='Get infos on a player')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_player(ctx: Context, *, player_name: str = None):
    """
    Get details on a player. If the provided player name does not match any player exactly, you will be prompted to select from a list of results. The selection prompt will time out after 60 seconds. Due to restrictions by SavySoda, it will print 10 options max at a time.

    Usage:
      /player [player_name]
      /user [player_name]

    Parameters:
      player_name: The (beginning of the) name of the player to search for. Mandatory.

    Examples:
      /player Namith - Offers a list of fleets having a name starting with 'Namith'. Upon selection prints player details.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        exact_name = utils.discord.get_exact_args(ctx)
        if exact_name:
            player_name = exact_name
        if not player_name:
            raise MissingParameterError('The parameter `player_name` is mandatory.')
        user_infos = await user.get_user_infos_by_name(player_name)

    if user_infos:
        if len(user_infos) == 1:
            user_info = user_infos[0]
        else:
            use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
            paginator = pagination.Paginator(ctx, player_name, user_infos, user.get_user_search_details, use_pagination)
            _, user_info = await paginator.wait_for_option_selection()

        if user_info:
            async with ctx.typing():
                max_tourney_battle_attempts = await tourney.get_max_tourney_battle_attempts()
                output = await user.get_user_details_by_info(ctx, user_info, max_tourney_battle_attempts=max_tourney_battle_attempts, as_embed=(await server_settings.get_use_embeds(ctx)))
            await utils.discord.post_output(ctx, output)
    else:
        raise NotFound(f'Could not find a player named `{player_name}`.')


@BOT.command(name='prestige', brief='Get prestige combos of crew')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_prestige(ctx: Context, *, crew_name: str):
    """
    Get the prestige combinations of the crew specified.

    Usage:
      /prestige [crew_name]

    Parameters:
      crew_name: (Part of) the name of the crew to be prestiged. Mandatory.

    Examples:
      /prestige xin - Will print all prestige combinations including the crew 'Xin'.

    Notes:
      This command will only print recipes for the crew with the best matching crew name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await crew.get_prestige_from_info(ctx, crew_name, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='price', aliases=['fairprice', 'cost'], brief='Get item\'s prices from the PSS API')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_price(ctx: Context, *, item_name: str):
    """
    Get the average price (market price) and the Savy price (fair price) in bux of the item(s) specified.

    Usage:
      /price [item_name]
      /fairprice [item_name]
      /cost [item_name]

    Parameters:
      item_name: (Part of) the name of an item to be crafted. Mandatory.

    Examples:
      /price mineral crate - Prints prices for all items having 'mineral crate' in their names.

    Notes:
      Market prices returned may not reflect the real market value, due to transfers between alts/friends.
      This command will print prices for all items matching the specified item_name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await item.get_item_price(ctx, item_name, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='recipe', brief='Get character recipes')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_recipe(ctx: Context, *, crew_name: str):
    """
    Get the prestige recipes of the crew specified.

    Usage:
      /recipe [crew_name]

    Parameters:
      crew_name: (Part of) the name of the crew to be prestiged into. Mandatory.

    Examples:
      /recipe xin - Will print all prestige combinations resulting in the crew 'Xin'.

    Notes:
      This command will only print recipes for the crew with the best matching crew name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await crew.get_prestige_to_info(ctx, crew_name, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='research', brief='Get research data')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_research(ctx: Context, *, research_name: str):
    """
    Get the details on a specific research. If multiple matches are found, only a brief summary will be provided.

    Usage:
      /research [research_name]

    Parameters:
      research_name: The name of the research to get details on.

    Examples:
      /research python - Will print information on all researches having 'python' in their names.

    Notes:
      This command will print information for all researches matching the specified name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await research.get_research_infos_by_name(research_name, ctx, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='room', brief='Get room infos')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_room(ctx: Context, *, room_name: str):
    """
    Get detailed information on a room. If more than 2 results are found, details will be omitted.

    Usage:
      /room [name]
      /room [short name] [room level]

    Parameters:
      name:       A room's name or part of it. Mandatory.
      short name: A room's short name (2 or 3 characters). Mandatory.
      room level: A room's level. Mandatory.

    Examples:
      /room mineral - Searches for rooms having 'mineral' in their names and prints their details.
      /room cloak generator lv2 - Searches for rooms having 'cloak generator lv2' in their names and prints their details.
      /room mst 3 - Searches for the lvl 3 room having the short room code 'mst'.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await room.get_room_details_by_name(room_name, ctx=ctx, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.command(name='sales', brief='List expired sales')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_sales(ctx: Context, *, object_name: str = None):
    """
    Get information on things that have been sold in shop in the past. This command will post the late sales price and for how many days it will be available (rounded down, so 0 days means only available today). If a parameter is given, the command will output the sales history for that object.

    Usage:
      /sales <object_name>
      /sales <object_name> --reverse

    Parameter:
      object_name: The name of the object you want to see the shop history for. Optional
      --reverse:   Will sort the output from old to new

    Examples:
      /sales - Prints information on the last 30 sales.
      /sales Virgo - Prints information on the sale history of the crew Virgo
      /sales Flower - Prints information on the sale history of the room Flower Gardens
    """
    __log_command_use(ctx)

    object_name, reverse_output = __extract_dash_parameters(object_name, '--reverse')

    if object_name:
        async with ctx.typing():
            entities_infos = []
            characters_designs_infos = await crew.characters_designs_retriever.get_entities_infos_by_name(object_name)
            for entity_info in characters_designs_infos:
                entity_info['entity_type'] = 'Crew'
                entity_info['entity_id'] = entity_info[crew.CHARACTER_DESIGN_KEY_NAME]
                entity_info['entity_name'] = entity_info[crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                entities_infos.append(entity_info)
            items_designs_infos = await item.items_designs_retriever.get_entities_infos_by_name(object_name)
            for entity_info in items_designs_infos:
                entity_info['entity_type'] = 'Item'
                entity_info['entity_id'] = entity_info[item.ITEM_DESIGN_KEY_NAME]
                entity_info['entity_name'] = entity_info[item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                entities_infos.append(entity_info)
            rooms_designs_infos = await room.rooms_designs_retriever.get_entities_infos_by_name(object_name)
            for entity_info in rooms_designs_infos:
                entity_info['entity_type'] = 'Room'
                entity_info['entity_id'] = entity_info[room.ROOM_DESIGN_KEY_NAME]
                entity_info['entity_name'] = entity_info[room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                entities_infos.append(entity_info)

        if entities_infos:
            if len(entities_infos) == 1:
                entity_info = entities_infos[0]
            else:
                entities_infos = sorted(entities_infos, key=lambda x: x['entity_name'])
                use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
                paginator = pagination.Paginator(ctx, object_name, entities_infos, daily.get_sales_search_details, use_pagination)
                _, entity_info = await paginator.wait_for_option_selection()

            if entity_info:
                async with ctx.typing():
                    output = await daily.get_sales_history(ctx, entity_info, reverse=reverse_output, as_embed=(await server_settings.get_use_embeds(ctx)))
            else:
                output = []
        else:
            raise NotFound(f'Could not find an object with the name `{object_name}`.')
    else:
        async with ctx.typing():
            output = await daily.get_sales_details(ctx, reverse=reverse_output, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.group(name='stars', brief='Division stars', invoke_without_command=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_stars(ctx: Context, *, division: str = None):
    """
    Get stars earned by each fleet during the current final tournament week.

    Usage:
      /stars
      /stars <division>

    Parameters:
      division: The letter of the division to show the star counts for. Optional. Valid values: [A, B, C, D]

    Examples:
      /stars - Prints the star count for every fleet competing in the current tournament finals.
      /stars A - Prints the star count for every fleet competing in division A in the current tournament finals.

    Notes:
      This command does not work outside of the tournament finals week.
    """
    __log_command_use(ctx)
    if tourney.is_tourney_running():
        async with ctx.typing():
            if not pss_top.is_valid_division_letter(division):
                subcommand = BOT.get_command('stars fleet')
                await ctx.invoke(subcommand, fleet_name=division)
                return
            else:
                output = await pss_top.get_division_stars(ctx, division=division, as_embed=(await server_settings.get_use_embeds(ctx)))
        await utils.discord.post_output(ctx, output)
    else:
        cmd = BOT.get_command('past stars')
        await ctx.invoke(cmd, month=None, year=None, division=division)


@cmd_stars.command(name='fleet', aliases=['alliance'], brief='Fleet stars')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_stars_fleet(ctx: Context, *, fleet_name: str = None):
    """
    Get stars earned by the specified fleet during the current final tournament week. If the provided fleet name does not match any fleet exactly, you will be prompted to select from a list of results. The selection prompt will time out after 60 seconds.

    Usage:
      /stars
      /stars fleet [fleet_name]

    Parameters:
      fleet_name: The (beginning of the) name of a fleet to show the star counts for. Mandatory.

    Examples:
      /stars fleet HYDRA - Offers a list of fleets having a name starting with 'hydra'. Upon selection, prints the star count for every member of the fleet, if it competes in the current tournament finals.

    Notes:
      If this command is being called outside of the tournament finals week, it will show historic data for the last tournament.
    """
    __log_command_use(ctx)
    if tourney.is_tourney_running():
        async with ctx.typing():
            exact_name = utils.discord.get_exact_args(ctx)
            if exact_name:
                fleet_name = exact_name
            if not fleet_name:
                raise MissingParameterError('The parameter `fleet_name` is mandatory.')

            fleet_infos = await fleet.get_fleet_infos_by_name(fleet_name)
            fleet_infos = [fleet_info for fleet_info in fleet_infos if fleet_info[pss_top.DIVISION_DESIGN_KEY_NAME] != '0']

        if fleet_infos:
            if len(fleet_infos) == 1:
                fleet_info = fleet_infos[0]
            else:
                use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
                paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details, use_pagination)
                _, fleet_info = await paginator.wait_for_option_selection()

            if fleet_info:
                async with ctx.typing():
                    fleet_users_infos = await fleet.get_fleet_users_data_by_fleet_info(fleet_info)
                    output = await fleet.get_fleet_users_stars_from_info(ctx, fleet_info, fleet_users_infos, as_embed=(await server_settings.get_use_embeds(ctx)))
                await utils.discord.post_output(ctx, output)
        else:
            raise NotFound(f'Could not find a fleet named `{fleet_name}` participating in the current tournament.')
    else:
        cmd = BOT.get_command('past stars fleet')
        await ctx.invoke(cmd, month=None, year=None, fleet_name=fleet_name)


@BOT.command(name='stats', aliases=['stat'], brief='Get item/crew stats')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_stats(ctx: Context, level: str = None, *, name: str = None):
    """
    Get the stats of a character/crew or item. This command is a combination of the commands /char and /item.

    Usage:
      /stats <level> [name]

    Parameters:
      level: Level of a crew. Will only apply to crew stats. Optional.
      name:  (Part of) the name of a crew or item. Mandatory.

    Examples:
      /stats hug - Will output results of the commands '/char hug' and '/item hug'
      /stats 25 hug - Will output results of the command '/char 25 hug' and '/item hug'

    Notes:
      This command will only print stats for the crew with the best matching name.
      This command will print information for all items matching the specified name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        full_name = ' '.join([x for x in [level, name] if x])
        level, name = utils.get_level_and_name(level, name)
        use_embeds = (await server_settings.get_use_embeds(ctx))
        try:
            char_output = await crew.get_char_details_by_name(ctx, name, level, as_embed=use_embeds)
            char_success = True
        except (InvalidParameterValueError, Error):
            char_output = None
            char_success = False
        try:
            item_output = await item.get_item_details_by_name(ctx, name, as_embed=use_embeds)
            item_success = True
        except (InvalidParameterValueError, Error):
            item_output = None
            item_success = False

    if char_success:
        await utils.discord.post_output(ctx, char_output)

    if item_success:
        if char_success and not use_embeds:
            await ctx.send(utils.discord.ZERO_WIDTH_SPACE)
        await utils.discord.post_output(ctx, item_output)

    if not char_success and not item_success:
        raise NotFound(f'Could not find a character or an item named `{full_name}`.')


@BOT.command(name='time', brief='Get PSS stardate & Melbourne time')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_time(ctx: Context):
    """
    Get PSS stardate, as well as the day and time in Melbourne, Australia. Gives the name of the Australian holiday, if it is a holiday in Australia.

    Usage:
      /time

    Examples:
      /time - Prints PSS stardate, day & time in Melbourne and public holidays.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        utc_now = utils.get_utc_now()
        star_date = f'Star date {utils.datetime.get_star_date(utc_now)}'

        mel_tz = pytz.timezone('Australia/Melbourne')
        mel_time = utc_now.replace(tzinfo=datetime.timezone.utc).astimezone(mel_tz)
        melbourne_time = mel_time.strftime('It is %A, %H:%M in Melbourne (at Savy HQ)')

        aus_holidays = holidays.Australia(years=utc_now.year, prov='ACT')
        mel_date = datetime.date(mel_time.year, mel_time.month, mel_time.day)
        holiday = ('It is also a holiday in Australia', aus_holidays.get(mel_date))

        first_day_of_next_month = utils.datetime.get_first_of_following_month(utc_now)
        time_till_next_month = ('Time until next monthly reset', utils.format.timedelta(first_day_of_next_month - utc_now, include_relative_indicator=False, include_seconds=False))

        while (first_day_of_next_month.month - 1) % 3:
            first_day_of_next_month = utils.datetime.get_first_of_following_month(first_day_of_next_month)
        time_till_next_prestige_change = ('Time until next prestige recipe changes', utils.format.timedelta(first_day_of_next_month - utc_now, include_relative_indicator=False, include_seconds=False))

        fields = [(field[0], field[1], False) for field in [holiday, time_till_next_month, time_till_next_prestige_change] if field[1]]
        as_embed = server_settings.get_use_embeds(ctx)
        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            output = [utils.discord.create_embed(star_date, description=melbourne_time, fields=fields, colour=colour)]
        else:
            output = [star_date, melbourne_time]
            [output.append(f'{field[0]}: {field[1]}') for field in fields if field[1]]
    await utils.discord.post_output(ctx, output)


@BOT.group(name='top', brief='Prints top fleets or captains', invoke_without_command=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_top(ctx: Context, *, count: str = '100'):
    """
    Prints either top fleets or captains. Prints top 100 fleets by default.

    Usage:
      /top <count>

    Parameters:
      count: The number of rows to be printed. Optional.

    Examples:
      /top - prints top 100 fleets.
      /top 30 - prints top 30 fleets."""
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        if ' ' in count:
            split_count = count.split(' ')
            try:
                count = int(split_count[0])
            except:
                try:
                    count = int(split_count[1])
                except:
                    raise ParameterTypeError('Invalid parameter provided! Parameter `count` must be a natural number from 1 to 100.')
                command = split_count[0]
            command = split_count[1]
        else:
            try:
                count = int(count)
            except:
                raise ParameterTypeError('Invalid parameter provided! Parameter `count` must be a natural number from 1 to 100.')
            command = 'fleets'
        cmd = BOT.get_command(f'top {command}')
        await ctx.invoke(cmd, count=count)


@cmd_top.command(name='players', aliases=['player', 'captains', 'captain', 'users', 'user'], brief='Prints top captains')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_top_captains(ctx: Context, count: str = '100'):
    """
    Prints top captains. Prints top 100 captains by default.

    Usage:
      /top captains <count>
      /top <count> captains

    Parameters:
      count: The number of rows to be printed. Optional.

    Examples:
      /top captains - prints top 100 captains.
      /top captains 30 - prints top 30 captains.
      /top 30 captains - prints top 30 captains."""
    __log_command_use(ctx)

    try:
        count = int(count)
    except:
        raise ParameterTypeError('Parameter `count` must be a natural number from 1 to 100.')

    async with ctx.typing():
        output = await pss_top.get_top_captains(ctx, count, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@cmd_top.command(name='fleets', aliases=['fleet', 'alliances', 'alliance'], brief='Prints top fleets')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_top_fleets(ctx: Context, count: str = '100'):
    """
    Prints top fleets. Prints top 100 fleets by default.

    Usage:
      /top fleets <count>
      /top <count> fleets

    Parameters:
      count: The number of rows to be printed. Optional.

    Examples:
      /top fleets - prints top 100 fleets.
      /top fleets 30 - prints top 30 fleets.
      /top 30 fleets - prints top 30 fleets."""
    __log_command_use(ctx)

    try:
        count = int(count)
    except:
        raise ParameterTypeError('Parameter `count` must be a natural number from 1 to 100.')

    async with ctx.typing():
        output = await pss_top.get_top_fleets(ctx, take=count, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)


@BOT.group(name='tournament', aliases=['tourney'], brief='Information on tournament time')
async def cmd_tournament(ctx: Context):
    """
    Get information about the starting time of the tournament.

    Usage:
      /tournament
      /tourney

    Examples:
      /tournament - Displays information about the starting time of this month's tournament.
    """
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        cmd = BOT.get_command('tournament current')
        await ctx.invoke(cmd)


@cmd_tournament.command(name='current', brief='Information on this month\'s tournament time')
async def cmd_tournament_current(ctx: Context):
    """
    Get information about the starting time of the current month's tournament.

    Usage:
      /tournament current
      /tourney current

    Examples:
      /tournament current - Displays information about the starting time of this month's tournament.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        utc_now = utils.get_utc_now()
        start_of_tourney = tourney.get_current_tourney_start()
        embed_colour = utils.discord.get_bot_member_colour(BOT, ctx.guild)
        embed = tourney.get_tourney_start_as_embed(start_of_tourney, utc_now, embed_colour)
        if (await server_settings.get_use_embeds(ctx)):
            output = [embed]
        else:
            output = tourney.convert_tourney_embed_to_plain_text(embed)

    await utils.discord.post_output(ctx, output)


@cmd_tournament.command(name='next', brief='Information on next month\'s tournament time')
async def cmd_tournament_next(ctx: Context):
    """
    Get information about the starting time of the next month's tournament.

    Usage:
      /tournament next
      /tourney next

    Examples:
      /tournament next - Displays information about the starting time of next month's tournament.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        utc_now = utils.get_utc_now()
        start_of_tourney = tourney.get_next_tourney_start()
        embed_colour = utils.discord.get_bot_member_colour(BOT, ctx.guild)
        embed = tourney.get_tourney_start_as_embed(start_of_tourney, utc_now, embed_colour)
        if (await server_settings.get_use_embeds(ctx)):
            output = [embed]
        else:
            output = tourney.convert_tourney_embed_to_plain_text(embed)

    await utils.discord.post_output(ctx, output)


@BOT.command(name='training', brief='Get training infos')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_training(ctx: Context, *, training_name: str):
    """
    Get detailed information on a training. If more than 2 results are found, some details will be omitted.

    Usage:
      /training [name]

    Parameters:
      name: A room's name or part of it. Mandatory.

    Examples:
      /training bench - Searches for trainings having 'bench' in their names and prints their details.

    Notes:
      The training yields displayed represent the upper bound of possible yields.
      The highest yield will always be displayed on the far left.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = await training.get_training_details_from_name(training_name, ctx, as_embed=(await server_settings.get_use_embeds(ctx)))
    await utils.discord.post_output(ctx, output)










# ############################################################################ #
# ----------                      Raw commands                      ---------- #
# ############################################################################ #

@BOT.group(name='raw', brief='Get raw data from the PSS API', invoke_without_command=True, hidden=True)
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw(ctx: Context):
    """
    Get raw data from the Pixel Starships API.
    Use one of the sub-commands to retrieve data for a certain entity type. The sub-commands may have sub-commands on their own, so make sure to check the related help commands.

    Usage:
      /raw [subcommand] <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await ctx.send_help('raw')


@cmd_raw.command(name='achievement', aliases=['achievements'], brief='Get raw achievement data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_achievement(ctx: Context, *, achievement_id: str = None):
    """
    Get raw achievement design data from the PSS API.

    Usage:
      /raw achievement <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the achievement with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, achievement.achievements_designs_retriever, 'achievement', achievement_id)


@cmd_raw.group(name='ai', brief='Get raw ai data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_ai(ctx: Context):
    """
    Get raw ai design data from the PSS API.

    Usage:
      /raw ai [subcommand] <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await ctx.send_help('raw ai')


@cmd_raw_ai.command(name='action', aliases=['actions'], brief='Get raw ai action data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_ai_action(ctx: Context, ai_action_id: int = None):
    """
    Get raw ai action design data from the PSS API.

    Usage:
      /raw ai action <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the ai action with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, ai.action_types_designs_retriever, 'ai_action', ai_action_id)


@cmd_raw_ai.command(name='condition', aliases=['conditions'], brief='Get raw ai condition data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_ai_condition(ctx: Context, ai_condition_id: int = None):
    """
    Get raw ai condition design data from the PSS API.

    Usage:
      /raw ai condition <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the ai condition with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, ai.condition_types_designs_retriever, 'ai_condition', ai_condition_id)


@cmd_raw.command(name='char', aliases=['crew', 'chars', 'crews'], brief='Get raw crew data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_char(ctx: Context, *, char_id: str = None):
    """
    Get raw character design data from the PSS API.

    Usage:
      /raw char <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the character with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, crew.characters_designs_retriever, 'character', char_id)


@cmd_raw.command(name='collection', aliases=['coll', 'collections'], brief='Get raw collection data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_collection(ctx: Context, *, collection_id: str = None):
    """
    Get raw collection design data from the PSS API.

    Usage:
      /raw collection <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the collection with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, crew.collections_designs_retriever, 'collection', collection_id)


@cmd_raw.group(name='gm', aliases=['galaxymap', 'galaxy'], brief='Get raw gm data', invoke_without_command=True)
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_gm(ctx: Context):
    """
    Get raw gm design data from the PSS API.

    Usage:
      /raw gm [subcommand] <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await ctx.send_help('raw gm')


@cmd_raw_gm.command(name='system', aliases=['systems', 'star', 'stars'], brief='Get raw gm system data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_gm_system(ctx: Context, *, star_system_id: str = None):
    """
    Get raw star system design data from the PSS API.

    Usage:
      /raw gm system <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the GM system with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, gm.star_systems_designs_retriever, 'star system', star_system_id)


@cmd_raw_gm.command(name='path', aliases=['paths', 'link', 'links'], brief='Get raw gm path data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_gm_link(ctx: Context, *, star_system_link_id: str = None):
    """
    Get raw star system link design data from the PSS API.

    Usage:
      /raw gm path <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the GM path with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, gm.star_system_links_designs_retriever, 'star system link', star_system_link_id)


@cmd_raw.command(name='item', aliases=['items'], brief='Get raw item data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_item(ctx: Context, *, item_id: str = None):
    """
    Get raw item design data from the PSS API.

    Usage:
      /raw item <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the item with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, item.items_designs_retriever, 'item', item_id)


@cmd_raw.command(name='mission', aliases=['missions'], brief='Get raw mission data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_mission(ctx: Context, *, mission_id: str = None):
    """
    Get raw mission design data from the PSS API.

    Usage:
      /raw mission <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the mission with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, mission.missions_designs_retriever, 'mission', mission_id)


@cmd_raw.command(name='promotion', aliases=['promo', 'promotions', 'promos'], brief='Get raw promotion data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_promotion(ctx: Context, *, promo_id: str = None):
    """
    Get raw promotion design data from the PSS API.

    Usage:
      /raw promotion <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the promotion with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, promo.promotion_designs_retriever, 'promotion', promo_id)


@cmd_raw.command(name='research', aliases=['researches'], brief='Get raw research data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_research(ctx: Context, *, research_id: str = None):
    """
    Get raw research design data from the PSS API.

    Usage:
      /raw research <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the research with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, research.researches_designs_retriever, 'research', research_id)


@cmd_raw.group(name='room', aliases=['rooms'], brief='Get raw room data', invoke_without_command=True)
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_room(ctx: Context, *, room_id: str = None):
    """
    Get raw room design data from the PSS API.

    Usage:
      /raw room <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the room with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, room.rooms_designs_retriever, 'room', room_id)


@cmd_raw_room.command(name='purchase', aliases=['purchases'], brief='Get raw room purchase data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_room_purchase(ctx: Context, *, room_purchase_id: str = None):
    """
    Get raw room purchase design data from the PSS API.

    Usage:
      /raw room purchase <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the room purchase with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, room.rooms_designs_purchases_retriever, 'room purchase', room_purchase_id)


@cmd_raw.command(name='ship', aliases=['ships', 'hull', 'hulls'], brief='Get raw ship data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_ship(ctx: Context, *, ship_id: str = None):
    """
    Get raw ship design data from the PSS API.

    Usage:
      /raw ship <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the ship hull with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, ship.ships_designs_retriever, 'ship', ship_id)


@cmd_raw.command(name='training', aliases=['trainings'], brief='Get raw training data')
@cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=BucketType.user)
async def cmd_raw_training(ctx: Context, *, training_id: str = None):
    """
    Get raw training design data from the PSS API.

    Usage:
      /raw training <id> <format>

    Parameters:
      id:     A natural number. If specified, the command will only return the raw data for the training with the specified id.
      format: A string determining the format of the output to be returned. These are valid values:
                • --json (JSON)
                • --xml (raw XML as returned by the API)
              If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
      All parameters are optional.

    It may take a while for the bot to create the file, so be patient ;)
    NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
    """
    __log_command_use(ctx)
    await raw.post_raw_data(ctx, training.trainings_designs_retriever, 'training', training_id)










# ############################################################################ #
# ----------                Server settings commands                ---------- #
# ############################################################################ #

@BOT.group(name='settings', brief='Server settings', invoke_without_command=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings(ctx: Context, *args):
    """
    Retrieve settings for this Discord server/guild.
    Set settings for this server using the subcommands 'set' and 'reset'.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings

    Examples:
      /settings - Prints all settings for the current Discord server/guild.
    """

    if ctx.invoked_subcommand is None:
        __log_command_use(ctx)
        await __assert_settings_command_valid(ctx)

        _, on_reset = __extract_dash_parameters(ctx.message.content, args, '--on_reset')
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
            full_settings = guild_settings.get_full_settings()
            title = f'Server settings for {ctx.guild.name}'
            note = None if not on_reset else 'Successfully reset all bot settings for this server!'
            output = await server_settings.get_pretty_guild_settings(ctx, full_settings, title=title, note=note)
        await utils.discord.post_output(ctx, output)


@cmd_settings.group(name='autodaily', aliases=['daily'], brief='Retrieve auto-daily settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_get_autodaily(ctx: Context, *args):
    """
    Retrieve the auto-daily setting for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings autodaily
      /settings daily

    Examples:
      /settings autodaily - Prints all auto-daily settings for the current Discord server/guild.
    """

    if ctx.invoked_subcommand is None:
        __log_command_use(ctx)
        await __assert_settings_command_valid(ctx)

        _, on_reset = __extract_dash_parameters(ctx.message.content, args, '--on_reset')
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
            full_autodaily_settings = guild_settings.autodaily.get_full_settings()
            title = f'Auto-daily settings for {ctx.guild.name}'
            note = None if not on_reset else 'Successfully reset auto-daily settings for this server!'
            output = await server_settings.get_pretty_guild_settings(ctx, full_autodaily_settings, title=title, note=note)
        await utils.discord.post_output(ctx, output)


@cmd_settings_get_autodaily.command(name='channel', aliases=['ch'], brief='Retrieve auto-daily channel')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_get_autodaily_channel(ctx: Context, *args):
    """
    Retrieve the auto-daily setting for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings autodaily channel
      /settings daily ch

    Examples:
      /settings autodaily ch - Prints the auto-daily channel settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        _, on_reset, on_set = __extract_dash_parameters(ctx.message.content, args, '--on_reset', '--on_set')
        guild_settings = await GUILD_SETTINGS.get(ctx.bot, ctx.guild.id)
        full_autodaily_settings = guild_settings.autodaily.get_channel_setting()
        title = f'Auto-daily settings for {ctx.guild.name}'
        note = None
        if on_reset:
            note = 'Successfully reset auto-daily channel for this server!'
        elif on_set:
            note = 'Successfully set auto-daily channel for this server!'
        output = await server_settings.get_pretty_guild_settings(ctx, full_autodaily_settings, title=title, note=note)
    await utils.discord.post_output(ctx, output)


@cmd_settings_get_autodaily.command(name='changemode', aliases=['mode'], brief='Retrieve auto-daily mode', hidden=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_get_autodaily_mode(ctx: Context, *args):
    """
    Retrieve the auto-daily setting for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings autodaily changemode
      /settings daily mode

    Examples:
      /settings autodaily mode - Prints the auto-daily change mode settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        _, on_reset, on_set = __extract_dash_parameters(ctx.message.content, args, '--on_reset', '--on_set')
        guild_settings = await GUILD_SETTINGS.get(ctx.bot, ctx.guild.id)
        full_autodaily_settings = guild_settings.autodaily.get_changemode_setting()
        title = f'Auto-daily settings for {ctx.guild.name}'
        note = None
        if on_reset:
            note = 'Successfully reset auto-daily mode for this server!'
        elif on_set:
            note = 'Successfully set auto-daily mode for this server!'
        output = await server_settings.get_pretty_guild_settings(ctx, full_autodaily_settings, title=title, note=note)
    await utils.discord.post_output(ctx, output)


@cmd_settings.command(name='botnews', aliases=['botchannel'], brief='Retrieve the bot news channel', hidden=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_get_botnews(ctx: Context, *args):
    """
    Retrieves the bot news channel for this server. When there're important news about this bot, it'll post a message in the configured channel.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings botnews
      /settings botchannel

    Examples:
      /settings botnews - Gets the channel configured for this server to receive bot news.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        _, on_reset, on_set = __extract_dash_parameters(ctx.message.content, args, '--on_reset', '--on_set')
        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        full_settings = guild_settings.get_bot_news_channel_setting()
        title = f'Server settings for {ctx.guild.name}'
        note = None
        if on_reset:
            note = 'Successfully reset bot news channel for this server!'
        elif on_set:
            note = 'Successfully set bot news channel for this server!'
        output = await server_settings.get_pretty_guild_settings(ctx, full_settings, title=title, note=note)
    await utils.discord.post_output(ctx, output)


@cmd_settings.command(name='embed', aliases=['embeds'], brief='Retrieve embed settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_get_embeds(ctx: Context, *args):
    """
    Retrieve the embed setting for this server. It determines, whether the bot output on this server will be served in embeds or in plain text.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings embed
      /settings embeds

    Examples:
      /settings embed - Prints the embed setting for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        _, on_reset, on_set = __extract_dash_parameters(ctx.message.content, args, '--on_reset', '--on_set')
        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        full_settings = guild_settings.get_use_embeds_setting()
        title = f'Server settings for {ctx.guild.name}'
        note = None
        if on_reset:
            note = 'Successfully reset embed usage for this server!'
        elif on_set:
            note = 'Successfully toggled embed usage for this server!'
        output = await server_settings.get_pretty_guild_settings(ctx, full_settings, title=title, note=note)
    await utils.discord.post_output(ctx, output)


@cmd_settings.command(name='pagination', aliases=['pages'], brief='Retrieve pagination settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_get_pagination(ctx: Context, *args):
    """
    Retrieve the pagination setting for this server. For information on what pagination is and what it does, use this command: /help pagination

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings pagination
      /settings pages

    Examples:
      /settings pagination - Prints the pagination setting for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        _, on_reset, on_set = __extract_dash_parameters(ctx.message.content, args, '--on_reset', '--on_set')
        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        full_settings = guild_settings.get_pagination_setting()
        title = f'Server settings for {ctx.guild.name}'
        note = None
        if on_reset:
            note = 'Successfully reset pagination for this server!'
        elif on_set:
            note = 'Successfully toggled pagination for this server!'
        output = await server_settings.get_pretty_guild_settings(ctx, full_settings, title=title, note=note)
    await utils.discord.post_output(ctx, output)


@cmd_settings.command(name='prefix', brief='Retrieve prefix settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_get_prefix(ctx: Context, *args):
    """
    Retrieve the prefix setting for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings prefix

    Examples:
      /settings prefix - Prints the prefix setting for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    await ctx.invoke(BOT.get_command('prefix'), *args)


@BOT.command(name='prefix', brief='Retrieve prefix settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_prefix(ctx: Context, *args):
    """
    Retrieve the prefix setting for this server.

    This command can only be used on Discord servers/guilds.

    Usage:
      /prefix

    Examples:
      /prefix - Prints the prefix setting for the current Discord server/guild.
    """
    __log_command_use(ctx)

    async with ctx.typing():
        _, on_reset, on_set = __extract_dash_parameters(ctx.message.content, args, '--on_reset', '--on_set')
        if utils.discord.is_guild_channel(ctx.channel):
            title = f'Server settings for {ctx.guild.name}'
            guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
            prefix_settings = guild_settings.get_prefix_setting()
        else:
            title = 'Bot settings'
            prefix_settings = {'prefix': settings.DEFAULT_PREFIX}
        note = None
        if on_reset:
            note = 'Successfully reset prefix for this server!'
        elif on_set:
            note = 'Successfully set prefix for this server!'
        output = await server_settings.get_pretty_guild_settings(ctx, prefix_settings, title=title, note=note)
    await utils.discord.post_output(ctx, output)










@cmd_settings.group(name='reset', brief='Reset server settings', invoke_without_command=True)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset(ctx: Context):
    """
    Reset settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset

    Examples:
      /settings reset - Resets all settings for the current Discord server/guild.
    """
    if ctx.invoked_subcommand is None:
        __log_command_use(ctx)
        await __assert_settings_command_valid(ctx)

        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        success = await guild_settings.reset()
        if all(success):
            await ctx.invoke(BOT.get_command('settings'), '--on_reset')
        else:
            raise Error('Could not reset all settings for this server. Please check the settings and try again or contact the bot\'s author.')


@cmd_settings_reset.group(name='autodaily', aliases=['daily'], brief='Reset auto-daily settings to defaults')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset_autodaily(ctx: Context):
    """
    Reset the auto-daily settings for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset autodaily
      /settings reset daily

    Examples:
      /settings reset autodaily - Resets the auto-daily settings for the current Discord server/guild.
    """
    if ctx.invoked_subcommand is None:
        __log_command_use(ctx)
        await __assert_settings_command_valid(ctx)

        async with ctx.typing():
            autodaily_settings = (await GUILD_SETTINGS.get(BOT, ctx.guild.id)).autodaily
            success = await autodaily_settings.reset()
        if success:
            await ctx.invoke(BOT.get_command(f'settings autodaily'), '--on_reset')
        else:
            raise Error('An error ocurred while trying to remove the auto-daily settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


@cmd_settings_reset_autodaily.command(name='channel', aliases=['ch'], brief='Reset auto-daily channel')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset_autodaily_channel(ctx: Context):
    """
    Reset the auto-daily channel settings for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset autodaily channel
      /settings reset daily ch

    Examples:
      /settings reset autodaily - Removes the auto-daily channel settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if utils.discord.is_guild_channel(ctx.channel):
        async with ctx.typing():
            autodaily_settings = (await GUILD_SETTINGS.get(BOT, ctx.guild.id)).autodaily
            success = await autodaily_settings.reset_channel()
            if success:
                await ctx.invoke(BOT.get_command(f'settings autodaily channel'), '--on_reset')
            else:
                raise Error('An error ocurred while trying to remove the auto-daily channel setting for this server.\n'
                            + 'Please try again or contact the bot\'s author.')


@cmd_settings_reset_autodaily.command(name='changemode', aliases=['mode'], brief='Reset auto-daily change mode')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset_autodaily_mode(ctx: Context):
    """
    Reset the auto-daily change mode settings for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset autodaily changemode
      /settings reset daily mode

    Examples:
      /settings reset autodaily mode - Resets the change mode for auto-daily changes for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if utils.discord.is_guild_channel(ctx.channel):
        async with ctx.typing():
            autodaily_settings = (await GUILD_SETTINGS.get(BOT, ctx.guild.id)).autodaily
            success = await autodaily_settings.reset_daily_delete_on_change()
            if success:
                await ctx.invoke(BOT.get_command(f'settings autodaily mode'), '--on_reset')
            else:
                raise Error('An error ocurred while trying to remove the auto-daily notification settings for this server.\n'
                            + 'Please try again or contact the bot\'s author.')


@cmd_settings_reset.command(name='botnews', aliases=['botchannel'], brief='Reset bot news channel')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset_bot_news_channel(ctx: Context):
    """
    Reset the bot news channel for this server. When there're important news about this bot, it'll post a message in the configured channel.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset botnews
      /settings reset botchannel

    Examples:
      /settings reset botnews - Removes the channel '#announcements' from the list of channels to receive bot news.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if utils.discord.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
            success = await guild_settings.reset_bot_news_channel()
            if success:
                await ctx.invoke(BOT.get_command(f'settings botnews'), '--on_reset')
            else:
                raise Error('An error ocurred while trying to remove the bot news channel setting for this server.\n'
                            + 'Please try again or contact the bot\'s author.')


@cmd_settings_reset.command(name='embed', aliases=['embeds'], brief='Reset embed settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset_embeds(ctx: Context):
    """
    Reset the embed settings for this server to 'ON'. It determines, whether the bot output on this server will be served in embeds or in plain text.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset embed
      /settings reset embeds

    Examples:
      /settings reset embed - Resets the embed settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if utils.discord.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
            success = await guild_settings.reset_use_embeds()
        if success:
            await ctx.invoke(BOT.get_command(f'settings embed'), '--on_reset')
        else:
            raise Error('An error ocurred while trying to reset the embed settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


@cmd_settings_reset.command(name='pagination', aliases=['pages'], brief='Reset pagination settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset_pagination(ctx: Context):
    """
    Reset the pagination settings for this server to 'ON'. For information on what pagination is and what it does, use this command: /help pagination

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset pagination
      /settings reset pages

    Examples:
      /settings reset pagination - Resets the pagination settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if utils.discord.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
            success = await guild_settings.reset_use_pagination()
        if success:
            await ctx.invoke(BOT.get_command(f'settings pagination'), '--on_reset')
        else:
            raise Error('An error ocurred while trying to reset the pagination settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


@cmd_settings_reset.command(name='prefix', brief='Reset prefix settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_reset_prefix(ctx: Context):
    """
    Reset the prefix settings for this server to '/'.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset prefix

    Examples:
      /settings reset prefix - Resets the prefix settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if utils.discord.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
            success = await guild_settings.reset_prefix()
        if success:
            await ctx.invoke(BOT.get_command(f'settings prefix'), '--on_reset')
        else:
            raise Error('An error ocurred while trying to reset the prefix settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')










@cmd_settings.group(name='set', brief='Change server settings', invoke_without_command=False)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set(ctx: Context):
    """
    Set settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      Refer to sub-command help.

    Examples:
      Refer to sub-command help.
    """
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        await ctx.send_help('settings set')


@cmd_settings_set.group(name='autodaily', aliases=['daily'], brief='Change auto-daily settings', invoke_without_command=False)
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set_autodaily(ctx: Context):
    """
    Set auto-daily settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.
    """
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        await ctx.send_help('settings set autodaily')


@cmd_settings_set_autodaily.command(name='channel', aliases=['ch'], brief='Set auto-daily channel')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set_autodaily_channel(ctx: Context, text_channel: TextChannel = None):
    """
    Set the auto-daily channel for this server. This channel will receive an automatic /daily message at 1 am UTC.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set autodaily channel <text_channel_mention>
      /settings set daily ch <text_channel_mention>

    Parameters:
      text_channel_mention: A mention of a text-channel on the current Discord server/guild. Optional. If omitted, will try to set the current channel.

    Examples:
      /settings set daily channel - Sets the current channel to receive the /daily message once a day.
      /settings set autodaily ch #announcements - Sets the channel #announcements to receive the /daily message once a day.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        autodaily_settings: server_settings.AutoDailySettings = (await GUILD_SETTINGS.get(BOT, ctx.guild.id)).autodaily
        if not text_channel:
            text_channel = ctx.channel

        permissions = text_channel.permissions_for(ctx.me)
        if permissions.read_messages is not True:
            raise Error('I don\'t have access to that channel.')
        if permissions.read_message_history is not True:
            raise Error('I don\'t have access to the messages history in that channel.')
        if permissions.send_messages is not True:
            raise Error('I don\'t have permission to post in that channel.')

        success = await autodaily_settings.set_channel(text_channel)
    if success:
        await ctx.invoke(BOT.get_command('settings autodaily channel'), '--on_set')
    else:
        raise Error(f'Could not set autodaily channel for this server. Please try again or contact the bot\'s author.')


@cmd_settings_set_autodaily.command(name='changemode', aliases=['mode'], brief='Set auto-daily repost mode')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set_autodaily_mode(ctx: Context):
    """
    Set the auto-daily mode for this server. If the contents of the daily post change, this setting decides, whether an existing daily post gets edited, or if it gets deleted and a new one gets posted instead.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set autodaily changemode
      /settings set daily change

    Examples:
      /settings set autodaily changemode - Toggles the change mode.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        autodaily_settings = (await GUILD_SETTINGS.get(BOT, ctx.guild.id)).autodaily
        success = await autodaily_settings.toggle_change_mode()
    if success:
        await ctx.invoke(BOT.get_command('settings autodaily changemode'), '--on_set')
    else:
        raise Error(f'Could not set repost on autodaily change mode for this server. Please try again or contact the bot\'s author.')


@cmd_settings_set.command(name='botnews', aliases=['botchannel'], brief='Set the bot news channel')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set_bot_news_channel(ctx: Context, text_channel: TextChannel = None):
    """
    Set the bot news channel for this server. When there're important news about this bot, it'll post a message in the configured channel. If the channel gets omitted, the current channel will be used.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set botnews <text channel mention>
      /settings set botchannel <text channel mention>

    Examples:
      /settings set botnews #announcements - Sets the channel '#announcements' to receive bot news.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        if text_channel is None:
            text_channel = ctx.channel

        permissions = text_channel.permissions_for(ctx.me)
        if permissions.read_messages is not True:
            raise Error('I don\'t have access to that channel.')
        if permissions.read_message_history is not True:
            raise Error('I don\'t have access to the messages history in that channel.')
        if permissions.send_messages is not True:
            raise Error('I don\'t have permission to post in that channel.')

        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        success = await guild_settings.set_bot_news_channel(text_channel)
    if success:
        await ctx.invoke(BOT.get_command('settings botnews'), '--on_set')
    else:
        raise Error(f'Could not set the bot news channel for this server. Please try again or contact the bot\'s author.')


@cmd_settings_set.command(name='embed', aliases=['embeds'], brief='Set embed settings')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set_embeds(ctx: Context, switch: str = None):
    """
    Set or toggle the pagination for this server. The default is 'ON'. It determines, whether the bot output on this server will be served in embeds or in plain text.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set embed <switch>
      /settings set embeds <switch>

    Parameters:
      format: A string determining the new pagination setting. Optional. Can be one of these values: [on, off, true, false, yes, no, 1, 0, 👍, 👎]

    Notes:
      If the parameter <switch> is being omitted, the command will toggle between 'ON' and 'OFF' depending on the current setting.

    Examples:
      /settings set embed - Toggles the embed setting for the current Discord server/guild depending on the current setting.
      /settings set embed off - Turns off embeds for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        success = await guild_settings.set_use_embeds(switch)
    if success:
        await ctx.invoke(BOT.get_command('settings embed'), '--on_set')
    else:
        raise Error(f'Could not set embed settings for this server. Please try again or contact the bot\'s author.')


@cmd_settings_set.command(name='pagination', aliases=['pages'], brief='Set pagination')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set_pagination(ctx: Context, switch: str = None):
    """
    Set or toggle the pagination for this server. The default is 'ON'. For information on what pagination is and what it does, use this command: /help pagination

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set pagination <switch>
      /settings set pages <switch>

    Parameters:
      format: A string determining the new pagination setting. Optional. Can be one of these values: [on, off, true, false, yes, no, 1, 0, 👍, 👎]

    Notes:
      If the parameter <switch> is being omitted, the command will toggle between 'ON' and 'OFF' depending on the current setting.

    Examples:
      /settings set pagination - Toggles the pagination setting for the current Discord server/guild depending on the current setting.
      /settings set pagination off - Turns off pagination for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        success = await guild_settings.set_use_pagination(switch)
    if success:
        await ctx.invoke(BOT.get_command('settings pagination'), '--on_set')
    else:
        raise Error(f'Could not set pagination settings for this server. Please try again or contact the bot\'s author.')


@cmd_settings_set.command(name='prefix', brief='Set prefix')
@cooldown(rate=RATE, per=COOLDOWN, type=BucketType.user)
async def cmd_settings_set_prefix(ctx: Context, prefix: str):
    """
    Set the prefix for this server. The default is '/'.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set prefix [prefix]

    Parameters:
      prefix: A string determining the new prefix. Mandatory. Leading whitespace will be omitted.

    Examples:
      /settings set prefix & - Sets the bot's prefix for the current Discord server/guild to '&'
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        prefix = prefix.lstrip()
        guild_settings = await GUILD_SETTINGS.get(BOT, ctx.guild.id)
        success = await guild_settings.set_prefix(prefix)
    if success:
        await ctx.invoke(BOT.get_command('settings prefix'), '--on_set')
    else:
        raise Error(f'Could not set prefix for this server. Please try again or contact the bot\'s author.')










# ############################################################################ #
# ----------                     Owner commands                     ---------- #
# ############################################################################ #

@BOT.group(name='autodaily', brief='Configure auto-daily for the server', hidden=True)
@is_owner()
async def cmd_autodaily(ctx: Context):
    """
    This command can be used to get an overview of the autodaily settings for this bot.

    In order to use this command or any sub commands, you need to be the owner of this bot.
    """
    __log_command_use(ctx)
    pass


@cmd_autodaily.group(name='list', brief='List configured auto-daily channels', invoke_without_command=False, hidden=True)
@is_owner()
async def cmd_autodaily_list(ctx: Context):
    __log_command_use(ctx)
    pass


@cmd_autodaily_list.command(name='all', brief='List all configured auto-daily channels', hidden=True)
@is_owner()
async def cmd_autodaily_list_all(ctx: Context):
    __log_command_use(ctx)
    async with ctx.typing():
        output = await daily.get_daily_channels(ctx, None, None)
    await utils.discord.post_output(ctx, output)


@cmd_autodaily_list.command(name='invalid', brief='List all invalid configured auto-daily channels', hidden=True)
@is_owner()
async def cmd_autodaily_list_invalid(ctx: Context):
    __log_command_use(ctx)
    async with ctx.typing():
        output = await daily.get_daily_channels(ctx, None, False)
    await utils.discord.post_output(ctx, output)


@cmd_autodaily_list.command(name='valid', brief='List all valid configured auto-daily channels', hidden=True)
@is_owner()
async def cmd_autodaily_list_valid(ctx: Context):
    __log_command_use(ctx)
    async with ctx.typing():
        output = await daily.get_daily_channels(ctx, None, True)
    await utils.discord.post_output(ctx, output)


@cmd_autodaily.command(name='post', brief='Post a daily message on this server\'s auto-daily channel', hidden=True)
@is_owner()
async def cmd_autodaily_post(ctx: Context):
    __log_command_use(ctx)
    guild = ctx.guild
    channel_id = await server_settings.db_get_daily_channel_id(guild.id)
    if channel_id is not None:
        text_channel = BOT.get_channel(channel_id)
        as_embed = await server_settings.get_use_embeds(ctx)
        output, output_embed, _ = await dropship.get_dropship_text()
        if as_embed:
            await utils.discord.post_output_to_channel(text_channel, output_embed)
        else:
            await utils.discord.post_output_to_channel(text_channel, output)


@BOT.group(name='db', brief='DB commands', hidden=True, invoke_without_command=True)
@is_owner()
async def cmd_db(ctx: Context):
    __log_command_use(ctx)
    await ctx.send_help('db')


@cmd_db.command(name='query', brief='Try to execute a DB query', hidden=True)
@is_owner()
async def cmd_db_query(ctx: Context, *, query: str):
    __log_command_use(ctx)
    async with ctx.typing():
        success = await db.try_execute(query)
    if not success:
        await ctx.send(f'The query \'{query}\' failed.')
    else:
        await ctx.send(f'The query \'{query}\' has been executed successfully.')


@cmd_db.command(name='select', brief='Try to select from DB', hidden=True)
@is_owner()
async def cmd_db_select(ctx: Context, *, query: str):
    __log_command_use(ctx)
    async with ctx.typing():
        if not query.lower().startswith('select '):
            query = f'SELECT {query}'
        try:
            result = await db.fetchall(query)
            error = None
        except Exception as error:
            result = []
            raise Error(f'The query \'{query}\' failed.')
    if result:
        await ctx.send(f'The query \'{query}\' has been executed successfully.')
        result = [str(record) for record in result]
        await utils.discord.post_output(ctx, result)
    else:
        raise Error(f'The query \'{query}\' didn\'t return any results.')


@BOT.group(name='device', brief='list available devices', hidden=True)
@is_owner()
async def cmd_device(ctx: Context):
    """
    Returns all known devices stored in the DB.
    """
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        async with ctx.typing():
            output = []
            for device in login.DEVICES.devices:
                output.append(utils.discord.ZERO_WIDTH_SPACE)
                if device.can_login_until:
                    login_until = utils.format.datetime(device.can_login_until)
                else:
                    login_until = '-'
                output.append(f'Key: {device.key}\nChecksum: {device.checksum}\nCan login until: {login_until}')
            output = output[1:]
            posts = utils.discord.create_posts_from_lines(output, utils.discord.MAXIMUM_CHARACTERS)
        for post in posts:
            await ctx.send(post)


@cmd_device.command(name='add', brief='store device', hidden=True)
@is_owner()
async def cmd_device_add(ctx: Context, device_key: str):
    """
    Attempts to store a device with the given device_key in the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        try:
            device = await login.DEVICES.add_device_by_key(device_key)
            await ctx.send(f'Added device with device key \'{device.key}\'.')
        except Exception as err:
            raise Error(f'Could not add device with device key\'{device_key}\':```{err}```')


@cmd_device.command(name='create', brief='create & store random device', hidden=True)
@is_owner()
async def cmd_device_create(ctx: Context):
    """
    Creates a new random device_key and attempts to store the new device in the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        device = await login.DEVICES.create_device()
        try:
            await device.get_access_token()
            await ctx.send(f'Created and stored device with key \'{device.key}\'.')
        except Exception as err:
            await login.DEVICES.remove_device(device)
            raise Error(f'Failed to create and store device:```{err}```')


@cmd_device.command(name='login', brief='login to a device', hidden=True)
@is_owner()
async def cmd_device_login(ctx: Context):
    """
    Attempts to remove a device with the given device_key from the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        try:
            access_token = await login.DEVICES.get_access_token()
            device = login.DEVICES.current
            await ctx.send(f'Logged in with device \'{device.key}\'.\nObtained access token: {access_token}')
        except Exception as err:
            device = login.DEVICES.current
            raise Error(f'Could not log in with device \'{device.key}\':```{err}``')


@cmd_device.command(name='remove', aliases=['delete', 'yeet'], brief='remove device', hidden=True)
@is_owner()
async def cmd_device_remove(ctx: Context, device_key: str):
    """
    Attempts to remove a device with the given device_key from the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        try:
            await login.DEVICES.remove_device_by_key(device_key)
            await ctx.send(f'Removed device with device key: \'{device_key}\'.')
        except Exception as err:
            raise Error(f'Could not remove device with device key \'{device_key}\':```{err}```')


@cmd_device.command(name='select', brief='select a device', hidden=True)
@is_owner()
async def cmd_device_select(ctx: Context, device_key: str):
    """
    Attempts to select a device with the given device_key from the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        device = login.DEVICES.select_device_by_key(device_key)
    await ctx.send(f'Selected device \'{device.key}\'.')


@BOT.command(name='embed', brief='Embeds your message.', hidden=True)
@is_owner()
async def cmd_embed(ctx: Context, *, message: str = None):
    __log_command_use(ctx)
    colour = utils.discord.get_bot_member_colour(BOT, ctx.guild)
    embed = utils.discord.create_embed('Your message in an embed', description=message, colour=colour)
    await ctx.send(embed=embed)


@BOT.command(name='repeat', brief='Repeat your message.', hidden=True)
@is_owner()
async def cmd_repeat(ctx: Context, *, message: str = None):
    __log_command_use(ctx)
    await ctx.send(message)


@BOT.command(name='sendnews', aliases=['botnews'], brief='Send bot news to all servers.', hidden=True)
@is_owner()
async def cmd_send_bot_news(ctx: Context, *, news: str = None):
    """
    Sends an embed to all guilds which have a bot news channel configured.

    Usage:
      /sendnews [--<property_key>=<property_value> ...]

    Available property keys:
      title:   The title of the news.
      content: The contents of the news.

    Example:
      /sendnews --title=This is a title. --content=This is the content.
    """
    __log_command_use(ctx)
    if not news:
        return

    async with ctx.typing():
        _, title, content = __extract_dash_parameters(news, '--title=', '--content=')
        if not title:
            raise ValueError('You need to specify a title!')
        avatar_url = BOT.user.avatar_url
        for bot_news_channel in server_settings.GUILD_SETTINGS.bot_news_channels:
            embed_colour = utils.discord.get_bot_member_colour(BOT, bot_news_channel.guild)
            embed: Embed = utils.discord.create_embed(title, description=content, colour=embed_colour)
            embed.set_thumbnail(url=avatar_url)
            await bot_news_channel.send(embed=embed)
        embed_colour = utils.discord.get_bot_member_colour(BOT, ctx.guild)
        embed = utils.discord.create_embed(title, description=content, colour=embed_colour)
        embed.set_thumbnail(url=avatar_url)
    await ctx.send(embed=embed)


@BOT.command(name='test', brief='These are testing commands, usually for debugging purposes', hidden=True)
@is_owner()
async def cmd_test(ctx: Context, action, *, params = None):
    __log_command_use(ctx)
    print(f'+ called command test(ctx: Context, {action}, {params}) by {ctx.author}')
    if action == 'utcnow':
        utc_now = utils.get_utc_now()
        txt = utils.format.datetime(utc_now)
        await ctx.send(txt)
    elif action == 'init':
        await db.init_schema()
        await ctx.send('Initialized the database from scratch')
        await utils.discord.try_delete_original_message(ctx)
    elif action == 'commands':
        output = [', '.join(sorted(BOT.all_commands.keys()))]
        await utils.discord.post_output(ctx, output)
    elif action == 'setting':
        setting_name = params.replace(' ', '_').upper()
        result = settings.__dict__.get(setting_name)
        if result is None:
            output = [f'Could not find a setting named `{params}`']
        else:
            if isinstance(result, str):
                result = f'"{result}"'
            elif isinstance(result, list):
                for i, element in enumerate(result):
                    if isinstance(element, str):
                        result[i] = f'"{element}"'
            elif isinstance(result, dict):
                for key, value in result.items():
                    result.pop(key)
                    if isinstance(key, str):
                        key = f'"{key}"'
                    if isinstance(value, str):
                        value = f'"{value}"'
                    result[key] = value
            output = [str(result)]
        await utils.discord.post_output(ctx, output)


@BOT.command(name='updatecache', brief='Updates all caches manually', hidden=True)
@is_owner()
async def cmd_updatecache(ctx: Context):
    """This command is to be used to update all caches manually."""
    __log_command_use(ctx)
    async with ctx.typing():
        await crew.characters_designs_retriever.update_cache()
        await crew.collections_designs_retriever.update_cache()
        prestige_to_caches = list(crew.__prestige_to_cache_dict.values())
        for prestige_to_cache in prestige_to_caches:
            await prestige_to_cache.update_data()
        prestige_from_caches = list(crew.__prestige_from_cache_dict.values())
        for prestige_from_cache in prestige_from_caches:
            await prestige_from_cache.update_data()
        await item.items_designs_retriever.update_cache()
        await research.researches_designs_retriever.update_cache()
        await room.rooms_designs_retriever.update_cache()
        await training.trainings_designs_retriever.update_cache()
        await daily.__update_db_sales_info_cache()
    await ctx.send('Updated all caches successfully!')










# ############################################################################ #
# ----------                Command Helper Functions                ---------- #
# ############################################################################ #

async def __assert_settings_command_valid(ctx: Context) -> None:
    if utils.discord.is_guild_channel(ctx.channel):
        permissions = ctx.channel.permissions_for(ctx.author)
        if permissions.manage_guild is not True:
            raise command_errors.MissingPermissions(['manage_guild'])
    else:
        raise Exception('This command cannot be used in DMs or group chats, but only in Discord servers/guilds!')


def __log_command_use(ctx: Context):
    if settings.PRINT_DEBUG_COMMAND:
        print(f'Invoked command: {ctx.message.content}')


def __log_command_use_error(ctx: Context, err: Exception, force_printing: bool = False):
    if settings.PRINT_DEBUG_COMMAND or force_printing:
        print(f'Invoked command had an error: {ctx.message.content}')
        if err:
            print(str(err))


def __extract_dash_parameters(full_arg: str, args: List[str], *dash_parameters) -> Tuple[Union[bool, str], ...]:
    new_arg = full_arg or ''
    if args:
        new_arg += f' {" ".join(args)}'
    result = []

    for dash_parameter in dash_parameters:
        if dash_parameter:
            if dash_parameter in new_arg:
                remove = ''
                parameter_pos = new_arg.find(dash_parameter)
                if '=' in dash_parameter:
                    value_start = parameter_pos + len(dash_parameter)
                    value_end = new_arg.find('--', value_start)
                    if value_end < 0:
                        value_len = len(new_arg) - value_start
                    else:
                        value_len = value_end - value_start - 1
                    value = new_arg[value_start:value_start + value_len]
                    remove = f'{dash_parameter}{value}'
                    result.append(value)
                else:
                    remove = dash_parameter
                    result.append(True)
                if parameter_pos > 0:
                    remove = f' {remove}'
                new_arg = new_arg.replace(remove, '').strip()
            else:
                if '=' in dash_parameter:
                    result.append(None)
                else:
                    result.append(False)
    return new_arg, *result











# ############################################################################ #
# ----------                      Run the Bot                       ---------- #
# ############################################################################ #

if __name__ == '__main__':
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    BOT.run(token)
