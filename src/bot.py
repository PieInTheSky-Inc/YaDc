import calendar
import datetime
import logging
import json
import os
import pytz
import re
import sys
from typing import Dict, List, Optional, Tuple, Union

import asyncio
from discord import Activity, ActivityType, Embed, File, Guild, Message, TextChannel
from discord import __version__ as discord_version
from discord.ext.commands import Bot, BucketType, Context, cooldown, is_owner, when_mentioned_or
import discord.errors as errors
import discord.ext.commands.errors as command_errors
import discord.ext.tasks as tasks
import holidays

from . import database as db
from . import emojis
from .gdrive import TourneyDataClient as _TourneyDataClient
from . import pagination
from . import pss_achievement as achievement
from . import pss_ai as ai
from . import pss_assert
from . import pss_core as core
from . import pss_craft as craft
from . import pss_crew as crew
from . import pss_daily as daily
from . import pss_dropship as dropship
from .pss_entity import EntitiesData, EntityInfo
from .pss_exception import Error, InvalidParameterValueError, MaintenanceError, MissingParameterError, NotFound, ParameterTypeError
from . import pss_fleet as fleet
from . import pss_gm as gm
from . import pss_item as item
from . import pss_login as login
from . import pss_lookups as lookups
from . import pss_mission as mission
from . import pss_promo as promo
from . import pss_raw as raw
from . import pss_research as research
from . import pss_room as room
from . import pss_ship as ship
from . import pss_situation as situation
from . import pss_sprites as sprites
from . import pss_tournament as tourney
from . import pss_top
from . import pss_training as training
from . import pss_user as user
from . import pss_wiki as wiki
from . import server_settings
from .server_settings import GUILD_SETTINGS
from . import settings
from . import utils

from .cogs import CurrentDataCog, GeneralCog, RawDataCog, SettingsCog, TournamentCog, WikiCog





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

INITIALIZED: bool = False

PWD: str = os.getcwd()

RATE: int = 5
RAW_COOLDOWN: float = 10.0
RAW_RATE: int = 5

TOURNEY_DATA_CLIENT: _TourneyDataClient = None


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
    print('+ on_ready()')
    print(f'sys.argv: {sys.argv}')
    print(f'Current time: {utils.format.datetime(utils.get_utc_now())}')
    print(f'Current Working Directory: {PWD}')
    print(f'Bot logged in as {BOT.user.name} (id={BOT.user.id}) on {len(BOT.guilds)} servers')
    print(f'Bot version is: {settings.VERSION}')
    schema_version = await db.get_schema_version()
    print(f'DB schema version is: {schema_version}')
    print(f'Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
    print(f'discord.py version: {discord_version}')

    print(f'Loading cog "{GeneralCog.__name__}" from extension "src.cogs.general"')
    BOT.load_extension('src.cogs.general')
    print(f'Loading cog "{CurrentDataCog.__name__}" from extension "src.cogs.current"')
    BOT.load_extension('src.cogs.current')
    print(f'Loading cog "{RawDataCog.__name__}" from extension "src.cogs.raw"')
    BOT.load_extension('src.cogs.raw')
    print(f'Loading cog "{SettingsCog.__name__}" from extension "src.cogs.settings"')
    BOT.load_extension('src.cogs.settings')
    print(f'Loading cog "{WikiCog.__name__}" from extension "src.cogs.wiki"')
    BOT.load_extension('src.cogs.wiki')
    if settings.FEATURE_TOURNEYDATA_ENABLED:
        print(f'Loading cog "{TournamentCog.__name__}" from extension "src.cogs.tournament"')
        BOT.load_extension('src.cogs.tournament')

    if settings.FEATURE_AUTODAILY_ENABLED:
        print('Starting auto-daily loop.')
        post_dailies_loop.start()


@BOT.event
async def on_connect() -> None:
    print('+ on_connect()')
    await __initialize()


@BOT.event
async def on_resumed() -> None:
    print('+ on_resumed()')
    await __initialize()


@BOT.event
async def on_disconnect() -> None:
    print('+ on_disconnect()')


@BOT.event
async def on_shard_ready() -> None:
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
            # Check err.original here for custom exceptions
            if err.original:
                error_type = type(err.original).__name__
                if isinstance(err.original, Error):
                    if isinstance(err.original, MaintenanceError):
                        error_type = 'Pixel Starships is under maintenance'
                    error_message = f'{err.original.msg}'
                else:
                    error_message = f'{err.original}'
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

        title = ' '.join(utils.parse.camel_case(error_type))
        as_embed = await server_settings.get_use_embeds(ctx)
        try:

            if as_embed:
                colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
                if retry_after:
                    error_message = f'{ctx.author.mention}\n{error_message}'
                embed = utils.discord.create_embed(title, description=error_message, colour=colour)
                await ctx.reply(embed=embed, delete_after=retry_after, mention_author=False)
            else:
                error_message = '\n'.join([f'> {x}' for x in error_message.splitlines()])
                if retry_after:
                    error_message = f'> {ctx.author.mention}\n{error_message}'
                await ctx.reply(f'**{title}**\n{error_message}', delete_after=retry_after, mention_author=False)
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

@tasks.loop(minutes=5)
async def post_dailies_loop() -> None:
    utc_now = utils.get_utc_now()
    if utc_now < settings.POST_AUTODAILY_FROM:
        return

    utc_now = utils.get_utc_now()

    daily_info = await daily.get_daily_info()
    db_daily_info, db_daily_modify_date = await daily.db_get_daily_info()
    has_daily_changed = daily.has_daily_changed(daily_info, utc_now, db_daily_info, db_daily_modify_date)

    if has_daily_changed:
        print(f'[post_dailies_loop] daily info changed:\n{json.dumps(daily_info, indent=2)}')
        autodaily_settings = await server_settings.get_autodaily_settings(utc_now=utc_now)
        print(f'[post_dailies_loop] retrieved {len(autodaily_settings)} guilds to post to')
    else:
        autodaily_settings = await server_settings.get_autodaily_settings(no_post_yet=True)
        if autodaily_settings:
            print(f'[post_dailies_loop] retrieved new {len(autodaily_settings)} channels without a post, yet.')

    created_output = False
    posted_count = 0
    if autodaily_settings:
        output, output_embeds, created_output = await dropship.get_dropship_text(daily_info=daily_info)
        if created_output:
            current_daily_message = '\n'.join(output)
            current_daily_embed = output_embeds[0]
            posted_count = await post_dailies(current_daily_message, current_daily_embed, autodaily_settings, utc_now)
        print(f'[post_dailies_loop] posted to {posted_count} of {len(autodaily_settings)} guilds')

    if has_daily_changed and (created_output or not autodaily_settings):
        await daily.db_set_daily_info(daily_info, utc_now)


@post_dailies_loop.before_loop
async def before_post_dailies_loop() -> None:
    await BOT.wait_until_ready()


async def post_dailies(current_daily_message: str, current_daily_embed: Embed, autodaily_settings: List[server_settings.AutoDailySettings], utc_now: datetime.datetime) -> int:
    posted_count = 0
    for guild_autodaily_settings in autodaily_settings:
        if guild_autodaily_settings.guild_id is not None and guild_autodaily_settings.channel_id is not None:
            posted, can_post, latest_message = await post_autodaily(guild_autodaily_settings.channel, guild_autodaily_settings.latest_message_id, guild_autodaily_settings.change_mode, current_daily_message, current_daily_embed, utc_now)
            if posted:
                posted_count += 1
            else:
                guild_name = guild_autodaily_settings.guild.name
                guild_id = guild_autodaily_settings.guild_id
                channel_name = f'#{guild_autodaily_settings.channel.name}' if guild_autodaily_settings.channel else '<not accessible>'
                channel_id = guild_autodaily_settings.channel_id
                print(f'[post_dailies] Failed to post to guild \'{guild_name}\' ({guild_id}), channel \'{channel_name}\' ({channel_id})')
            await guild_autodaily_settings.update(can_post=can_post, latest_message=latest_message, store_now_as_created_at=(not can_post and not latest_message))
    return posted_count


async def post_autodaily(text_channel: TextChannel, latest_message_id: int, change_mode: bool, current_daily_message: str, current_daily_embed: Embed, utc_now: datetime.datetime) -> Tuple[bool, bool, Message]:
    """
    Returns (posted, can_post, latest_message)
    """
    posted = False
    if text_channel and current_daily_message:
        error_msg_delete = f'could not delete message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_edit = f'could not edit message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_post = f'could not post a message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]'

        post_new = change_mode != server_settings.AutoDailyChangeMode.EDIT
        can_post = True
        latest_message: Message = None
        use_embeds = await server_settings.get_use_embeds(None, bot=BOT, guild=text_channel.guild)
        if use_embeds:
            colour = utils.discord.get_bot_member_colour(BOT, text_channel.guild)
            embed = current_daily_embed.copy()
            embed.colour = colour
        else:
            embed = None

        if can_post:
            can_post, latest_message = await daily_fetch_latest_message(text_channel, latest_message_id)

        if can_post:
            if latest_message and latest_message.created_at.day == utc_now.day:
                latest_message_id = latest_message.id
                if change_mode == server_settings.AutoDailyChangeMode.DELETE_AND_POST_NEW:
                    try:
                        deleted = await utils.discord.try_delete_message(latest_message)
                        if deleted:
                            latest_message = None
                            utils.dbg_prnt(f'[post_autodaily] deleted message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                        else:
                            print(f'[post_autodaily] could not delete message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
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
                        if use_embeds:
                            await latest_message.edit(embed=embed)
                        else:
                            await latest_message.edit(content=current_daily_message)
                        posted = True
                        utils.dbg_prnt(f'[post_autodaily] edited message [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
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

            if not posted and can_post and post_new:
                try:
                    if use_embeds:
                        latest_message = await text_channel.send(embed=embed)
                    else:
                        latest_message = await text_channel.send(current_daily_message)
                    posted = True
                    utils.dbg_prnt(f'[post_autodaily] posted message [{latest_message.id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
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


async def daily_fetch_latest_message(text_channel: TextChannel, latest_message_id: int) -> Tuple[bool, Message]:
    """
    Attempts to fetch the message by id, then by content from the specified channel.
    Returns (can_post, latest_message)
    """
    can_post: bool = True
    result: Message = None

    if text_channel and latest_message_id is not None:
        try:
            result = await text_channel.fetch_message(latest_message_id)
            utils.dbg_prnt(f'[daily_fetch_latest_message] found latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
        except errors.NotFound:
            print(f'[daily_fetch_latest_message] could not find latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
        except Exception as err:
            print(f'[daily_fetch_latest_message] could not fetch message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {err}')
            can_post = False

    return can_post, result










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
    """
    Lists auto-daily channels currently configured.
    """
    __log_command_use(ctx)
    pass


@cmd_autodaily_list.command(name='all', brief='List all configured auto-daily channels', hidden=True)
@is_owner()
async def cmd_autodaily_list_all(ctx: Context):
    """
    Lists all auto-daily channels currently configured across all guilds.
    """
    __log_command_use(ctx)
    output = await daily.get_daily_channels(ctx, None, None)
    await utils.discord.reply_with_output(ctx, output)


@cmd_autodaily.command(name='post', brief='Post a daily message on this server\'s auto-daily channel', hidden=True)
@is_owner()
async def cmd_autodaily_post(ctx: Context):
    """
    Posts the daily message to all auto-daily channels currently configured across all guilds.
    """
    __log_command_use(ctx)
    guild = ctx.guild
    channel_id = await server_settings.db_get_daily_channel_id(guild.id)
    if channel_id is not None:
        text_channel = BOT.get_channel(channel_id)
        as_embed = await server_settings.get_use_embeds(ctx)
        output, output_embed, _ = await dropship.get_dropship_text()
        if as_embed:
            await utils.discord.reply_with_output_to_channel(text_channel, output_embed)
        else:
            await utils.discord.reply_with_output_to_channel(text_channel, output)


@BOT.group(name='db', brief='DB commands', hidden=True, invoke_without_command=True)
@is_owner()
async def cmd_db(ctx: Context):
    """
    Database commands
    """
    __log_command_use(ctx)
    await ctx.send_help('db')


@cmd_db.command(name='query', brief='Try to execute a DB query', hidden=True)
@is_owner()
async def cmd_db_query(ctx: Context, *, query: str):
    """
    Starts a database query and returns a success message.
    """
    __log_command_use(ctx)
    success = await db.try_execute(query)
    if not success:
        await ctx.send(f'The query \'{query}\' failed.')
    else:
        await ctx.send(f'The query \'{query}\' has been executed successfully.')


@cmd_db.command(name='select', brief='Try to select from DB', hidden=True)
@is_owner()
async def cmd_db_select(ctx: Context, *, query: str):
    """
    Selects from a database and returns the results.
    """
    __log_command_use(ctx)
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
        await utils.discord.reply_with_output(ctx, result)
    else:
        raise Error(f'The query \'{query}\' didn\'t return any results.')


@BOT.group(name='debug', brief='Get debug info', hidden=True, invoke_without_command=True)
@is_owner()
async def cmd_debug(ctx: Context, *, args: str = None):
    __log_command_use(ctx)


@cmd_debug.group(name='autodaily', aliases=['daily'], brief='Get debug info', invoke_without_command=True)
@is_owner()
async def cmd_debug_autodaily(ctx: Context):
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        utc_now = utils.get_utc_now()
        result = await server_settings.get_autodaily_settings()
        json_base = []
        for autodaily_settings in result:
            json_base.append({
                'guild_id': autodaily_settings.guild_id or '-',
                'channel_id': autodaily_settings.channel_id or '-',
                'change_mode': autodaily_settings.change_mode or '-',
                'message_id': autodaily_settings.latest_message_id or '-',
                'created_at': utils.format.datetime(autodaily_settings.latest_message_created_at) if autodaily_settings.latest_message_created_at else '-',
                'modified_at': utils.format.datetime(autodaily_settings.latest_message_modified_at) if autodaily_settings.latest_message_modified_at else '-'
            })
        file_name = f'autodaily_settings_all_{utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
        with open(file_name, 'w') as fp:
            json.dump(json_base, fp, indent=4)
        await ctx.send(f'Retrieved {len(result)} auto-daily settings.', file=File(file_name))
        os.remove(file_name)


@cmd_debug_autodaily.group(name='nopost', aliases=['new'], brief='Get debug info')
@is_owner()
async def cmd_debug_autodaily_nopost(ctx: Context, *, args: str = None):
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        _, legacy = __extract_dash_parameters(args, None, '--legacy')
        utc_now = utils.get_utc_now()
        if legacy:
            result = await server_settings.get_autodaily_settings_legacy(ctx.bot, utc_now, no_post_yet=True)
        else:
            result = await server_settings.get_autodaily_settings(no_post_yet=True)
        json_base = []
        for autodaily_settings in result:
            json_base.append({
                'guild_id': autodaily_settings.guild_id or '-',
                'channel_id': autodaily_settings.channel_id or '-',
                'change_mode': autodaily_settings.change_mode or '-',
                'message_id': autodaily_settings.latest_message_id or '-',
                'created_at': utils.format.datetime(autodaily_settings.latest_message_created_at) if autodaily_settings.latest_message_created_at else '-',
                'modified_at': utils.format.datetime(autodaily_settings.latest_message_modified_at) if autodaily_settings.latest_message_modified_at else '-'
            })
        file_name = f'autodaily_settings_nopost_{utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
        with open(file_name, 'w') as fp:
            json.dump(json_base, fp, indent=4)
        await ctx.send(f'Retrieved {len(result)} auto-daily settings.', file=File(file_name))
        os.remove(file_name)


@cmd_debug_autodaily.group(name='changed', brief='Get debug info')
@is_owner()
async def cmd_debug_autodaily_changed(ctx: Context, *, args: str = None):
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        _, legacy = __extract_dash_parameters(args, None, '--legacy')
        utc_now = utils.get_utc_now()
        if legacy:
            result = await server_settings.get_autodaily_settings_legacy(ctx.bot, utc_now)
        else:
            result = await server_settings.get_autodaily_settings(utc_now=utc_now)
        json_base = []
        for autodaily_settings in result:
            json_base.append({
                'guild_id': autodaily_settings.guild_id or '-',
                'channel_id': autodaily_settings.channel_id or '-',
                'change_mode': autodaily_settings.change_mode or '-',
                'message_id': autodaily_settings.latest_message_id or '-',
                'created_at': utils.format.datetime(autodaily_settings.latest_message_created_at) if autodaily_settings.latest_message_created_at else '-',
                'modified_at': utils.format.datetime(autodaily_settings.latest_message_modified_at) if autodaily_settings.latest_message_modified_at else '-'
            })
        file_name = f'autodaily_settings_changed_{utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
        with open(file_name, 'w') as fp:
            json.dump(json_base, fp, indent=4)
        await ctx.send(f'Retrieved {len(result)} auto-daily settings.', file=File(file_name))
        os.remove(file_name)


@BOT.group(name='device', brief='list available devices', hidden=True)
@is_owner()
async def cmd_device(ctx: Context):
    """
    Returns all known devices stored in the DB.
    """
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
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
    try:
        device = login.DEVICES.current
        access_token = await device.get_access_token()
        await ctx.send(f'Logged in with device \'{device.key}\'.\nObtained access token: {access_token}')
    except Exception as err:
        device = login.DEVICES.current
        raise Error(f'Could not log in with device \'{device.key}\':```{err}```')


@cmd_device.command(name='remove', aliases=['delete', 'yeet'], brief='remove device', hidden=True)
@is_owner()
async def cmd_device_remove(ctx: Context, device_key: str):
    """
    Attempts to remove a device with the given device_key from the DB.
    """
    __log_command_use(ctx)
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
    device = login.DEVICES.select_device_by_key(device_key)
    await ctx.send(f'Selected device \'{device.key}\'.')


@BOT.command(name='embed', brief='Embeds your message.', hidden=True)
@is_owner()
async def cmd_embed(ctx: Context, *, message: str = None):
    __log_command_use(ctx)
    colour = utils.discord.get_bot_member_colour(BOT, ctx.guild)
    embed = utils.discord.create_embed('Your message in an embed', description=message, colour=colour)
    await ctx.send(embed=embed)


@BOT.command(name='sales-add', brief='Add a past sale.', hidden=True)
@is_owner()
async def cmd_sales_add(ctx: Context, sold_on: str, price: int, currency: str, max_amount: int, *, entity_name: str):
    """
    Add a past sale to the database.
    """
    __log_command_use(ctx)
    if price <= 0:
        error_msg = '\n'.join([
            f'Parameter `price` received an invalid value: {price}'
            f'The value must be greater than 0.'
        ])
        raise ValueError(error_msg)

    if max_amount <= 0:
        error_msg = '\n'.join([
            f'Parameter `max_amount` received an invalid value: {max_amount}'
            f'The value must be greater than 0.'
        ])
        raise ValueError(error_msg)

    currency_lower = currency.lower()
    if currency_lower.startswith('min'):
        currency_type = 'Mineral'
    elif currency_lower.startswith('gas'):
        currency_type = 'Gas'
    elif 'bux' in currency_lower:
        currency_type = 'Starbux'
    else:
        error_msg = '\n'.join([
            f'Parameter `currency` received wrong value: {currency}'
            'Valid values are: Bux, Gas, Min, Mineral, Mins, Minerals, Starbux'
        ])
        raise ValueError(error_msg)

    try:
        expires_at = utils.parse.formatted_datetime(sold_on, include_time=False, include_tz=False, include_tz_brackets=False) + utils.datetime.ONE_DAY
    except Exception as ex:
        error_msg = '\n'.join((
            f'Parameter `sold_on` received an invalid value: {sold_on}',
            f'Values must be dates in format: yyyy-MM-dd'
        ))
        raise ValueError(error_msg) from ex


    entities_infos = []
    characters_designs_infos = await crew.characters_designs_retriever.get_entities_infos_by_name(entity_name)
    for entity_info in characters_designs_infos:
        entity_info['entity_type'] = 'Character'
        entity_info['entity_id'] = entity_info[crew.CHARACTER_DESIGN_KEY_NAME]
        entity_info['entity_name'] = entity_info[crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        entities_infos.append(entity_info)
    items_designs_infos = await item.items_designs_retriever.get_entities_infos_by_name(entity_name)
    for entity_info in items_designs_infos:
        entity_info['entity_type'] = 'Item'
        entity_info['entity_id'] = entity_info[item.ITEM_DESIGN_KEY_NAME]
        entity_info['entity_name'] = entity_info[item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        entities_infos.append(entity_info)
    rooms_designs_infos = await room.rooms_designs_retriever.get_entities_infos_by_name(entity_name)
    for entity_info in rooms_designs_infos:
        entity_info['entity_type'] = 'Room'
        entity_info['entity_id'] = entity_info[room.ROOM_DESIGN_KEY_NAME]
        entity_info['entity_name'] = entity_info[room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        entities_infos.append(entity_info)

    entity_info = None
    entity_id = None
    entity_type = None
    if entities_infos:
        if len(entities_infos) == 1:
            entity_info = entities_infos[0]
        else:
            paginator = pagination.Paginator(ctx, entity_name, entities_infos, daily.get_sales_search_details_with_id, True)
            _, entity_info = await paginator.wait_for_option_selection()
    if entity_info:
        entity_id = int(entity_info['entity_id'])
        entity_type = entity_info['entity_type']

    if entity_id:
        entity_id = int(entity_id)
        success = await daily.add_sale(entity_id, price, currency_type, entity_type, expires_at, max_amount)
        if success:
            await ctx.send(f'Successfully added {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database.')
        else:
            await ctx.send(f'Failed adding {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database. Check the log for more information.')


@BOT.command(name='sales-export', brief='Export sales history.', hidden=True)
@is_owner()
async def cmd_sales_export(ctx: Context):
    """
    Export sales history to json.
    """
    __log_command_use(ctx)
    sales_infos = await daily.get_sales_infos()
    utc_now = utils.get_utc_now()
    file_name = f'sales_history_{utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
    with open(file_name, 'w') as fp:
        json.dump(sales_infos, fp, indent=4, cls=daily.SaleInfoEncoder)
    await ctx.send(file=File(file_name))
    os.remove(file_name)


@BOT.command(name='sales-import', brief='Import sales history.', hidden=True)
@is_owner()
async def cmd_sales_import(ctx: Context, *, args: str = None):
    """
    Import sales history from json.
    """
    __log_command_use(ctx)
    if not ctx.message.attachments:
        raise Error('You need to upload a file to be imported.')
    if len(ctx.message.attachments) > 1:
        raise Error('Too many files provided.')

    _, overwrite, overwrite_all = __extract_dash_parameters(args, None, '--overwrite', '--overwriteall')
    if overwrite and overwrite_all:
        raise ValueError('You may only specify one of the parameters: `--overwrite`, `--overwriteall`')

    attachment = ctx.message.attachments[0]
    file_contents = (await attachment.read()).decode('utf-8')
    if not file_contents:
        raise Error('The file provided must not be empty.')

    sales_infos = json.JSONDecoder(object_hook=daily.sale_info_decoder_object_hook).decode(file_contents)
    #sales_infos = json.loads(file_contents, cls=json.JSONDecoder(object_hook=daily.sale_info_decoder_object_hook))
    if not sales_infos:
        raise Error('The data provided must not be empty.')
    sales_infos = sorted(sales_infos, key=lambda x: x['limitedcatalogexpirydate'])

    if overwrite_all:
        await daily.clear_sales()

    failed_sales_infos = []
    for sale_info in sales_infos:
        success = await daily.__db_add_sale(
            sale_info.get('limitedcatalogargument'),
            sale_info.get('limitedcatalogcurrencyamount'),
            sale_info.get('limitedcatalogcurrencytype'),
            sale_info.get('limitedcatalogtype'),
            sale_info.get('limitedcatalogexpirydate'),
            sale_info.get('limitedcatalogmaxtotal'),
            overwrite=overwrite
        )
        if not success:
            failed_sales_infos.append(sale_info)

    if len(failed_sales_infos) == len(sales_infos):
        raise Error('Could not import any sales info from the specified file.')
    output = [
        f'Successfully imported file {attachment.filename}.'
    ]
    if failed_sales_infos:
        output.append(
            f'Failed to import the following sales infos:'
        )
        output.extend([json.dumps(sale_info) for sale_info in failed_sales_infos])
    await daily.update_db_sales_info_cache()
    await utils.discord.reply_with_output(ctx, output)


@BOT.command(name='sales-parse', brief='Parse and add a past sale.', hidden=True)
@is_owner()
async def cmd_sales_parse(ctx: Context, sold_on: str, *, sale_text: str):
    """
    Parse a sale from the daily news and add it to the database.
    """
    __log_command_use(ctx)
    try:
        expires_at = utils.parse.formatted_datetime(sold_on, include_time=False, include_tz=False, include_tz_brackets=False) + utils.datetime.ONE_DAY
    except Exception as ex:
        error_msg = '\n'.join((
            f'Parameter `sold_on` received an invalid value: {sold_on}',
            f'Values must be dates in format: yyyy-MM-dd'
        ))
        raise ValueError(error_msg) from ex

    rx_entity_name = r'(.*?)(?= [\(\[])'
    rx_number = r'(\d+)'
    rx_currency = r'<:.+?:\d+>'

    sale_text_lines = sale_text.split('\n')
    entity_name_match = re.search(rx_entity_name, sale_text_lines[0])
    if entity_name_match:
        entity_name = entity_name_match.group(0)
    else:
        raise Error(f'Could not extract the entity name from: {sale_text_lines[0]}')

    price_match = re.search(rx_number, sale_text_lines[1])
    if price_match:
        price = int(price_match.group(0))
    else:
        raise Error(f'Could not extract the price from: {sale_text_lines[1]}')

    currency_match = re.search(rx_currency, sale_text_lines[1])
    if currency_match:
        currency = currency_match.group(0).lower()
    else:
        raise Error(f'Could not extract the currency from: {sale_text_lines[1]}')

    currency_type = lookups.CURRENCY_EMOJI_LOOKUP_REVERSE.get(currency)
    if currency_type:
        currency_type = currency_type.capitalize()
    else:
        raise Error(f'Could not convert currency emoji to currency type: {currency}')

    max_amount_match = re.search(rx_number, sale_text_lines[2])
    if max_amount_match:
        max_amount = int(max_amount_match.group(0))
    else:
        raise Error(f'Could not extract the currency from: {sale_text_lines[2]}')

    entities_infos = []
    characters_designs_infos = await crew.characters_designs_retriever.get_entities_infos_by_name(entity_name)
    for entity_info in characters_designs_infos:
        entity_info['entity_type'] = 'Character'
        entity_info['entity_id'] = entity_info[crew.CHARACTER_DESIGN_KEY_NAME]
        entity_info['entity_name'] = entity_info[crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        entities_infos.append(entity_info)
    items_designs_infos = await item.items_designs_retriever.get_entities_infos_by_name(entity_name)
    for entity_info in items_designs_infos:
        entity_info['entity_type'] = 'Item'
        entity_info['entity_id'] = entity_info[item.ITEM_DESIGN_KEY_NAME]
        entity_info['entity_name'] = entity_info[item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        entities_infos.append(entity_info)
    rooms_designs_infos = await room.rooms_designs_retriever.get_entities_infos_by_name(entity_name)
    for entity_info in rooms_designs_infos:
        entity_info['entity_type'] = 'Room'
        entity_info['entity_id'] = entity_info[room.ROOM_DESIGN_KEY_NAME]
        entity_info['entity_name'] = entity_info[room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        entities_infos.append(entity_info)

    entity_info = None
    entity_id = None
    entity_type = None
    if entities_infos:
        if len(entities_infos) == 1:
            entity_info = entities_infos[0]
        else:
            paginator = pagination.Paginator(ctx, entity_name, entities_infos, daily.get_sales_search_details_with_id, True)
            _, entity_info = await paginator.wait_for_option_selection()
    if entity_info:
        entity_id = int(entity_info['entity_id'])
        entity_type = entity_info['entity_type']

    if entity_id:
        entity_id = int(entity_id)
        success = await daily.add_sale(entity_id, price, currency_type, entity_type, expires_at, max_amount)
        if success:
            await ctx.send(f'Successfully added {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database.')
        else:
            await ctx.send(f'Failed adding {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database. Check the log for more information.')


@BOT.command(name='sendnews', aliases=['botnews'], brief='Send bot news to all servers.', hidden=True)
@is_owner()
async def cmd_send_bot_news(ctx: Context, *, news: str = None):
    """
    Sends an embed to all guilds which have a bot news channel configured.

    Usage:
      /sendnews [--test] [--<property_key>=<property_value> ...]

    Available property keys:
      --test:    Optional. Use to only send the news to the current channel.
      --title:   Mandatory. The title of the news.
      --content: Optional. The contents of the news.

    Example:
      /sendnews --title=This is a title. --content=This is the content.
      /sendnews --test --title=This is a title. --content=This is the content.
    """
    __log_command_use(ctx)
    if not news:
        return

    _, for_testing, title, content = __extract_dash_parameters(news, None, '--test', '--title=', '--content=')
    if not title:
        raise ValueError('You need to specify a title!')
    avatar_url = BOT.user.avatar_url
    if not for_testing:
        for bot_news_channel in server_settings.GUILD_SETTINGS.bot_news_channels:
            embed_colour = utils.discord.get_bot_member_colour(BOT, bot_news_channel.guild)
            embed: Embed = utils.discord.create_embed(title, description=content, colour=embed_colour)
            embed.set_thumbnail(url=avatar_url)
            try:
                await bot_news_channel.send(embed=embed)
            except errors.Forbidden:
                pass
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
        txt = utils.datetime.get_discord_datestamp(utc_now, include_time=True, include_seconds=True)
        await ctx.send(txt)
    elif action == 'init':
        await db.init_schema()
        await ctx.send('Initialized the database from scratch')
        await utils.discord.try_delete_original_message(ctx)
    elif action == 'commands':
        output = [', '.join(sorted(BOT.all_commands.keys()))]
        await utils.discord.reply_with_output(ctx, output)
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
        await utils.discord.reply_with_output(ctx, output)


@BOT.command(name='updatecache', brief='Updates all caches manually', hidden=True)
@is_owner()
async def cmd_updatecache(ctx: Context):
    """
    This command is to be used to update all caches manually.
    """
    __log_command_use(ctx)
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
    await daily.update_db_sales_info_cache()
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
        raise Exception('This command cannot be used in DMs or group chats, but only in Discord servers/guilds.')


def __log_command_use(ctx: Context):
    if settings.PRINT_DEBUG_COMMAND:
        print(f'Invoked command: {ctx.message.content}')


def __log_command_use_error(ctx: Context, err: Exception, force_printing: bool = False):
    if settings.PRINT_DEBUG_COMMAND or force_printing:
        print(f'Invoked command had an error: {ctx.message.content}')
        if err:
            print(str(err))


def __extract_dash_parameters(full_arg: str, args: Optional[List[str]], *dash_parameters) -> Tuple[Union[bool, str], ...]:
    new_arg = full_arg or ''
    if args:
        new_arg += f' {" ".join(args)}'
    result = []

    for dash_parameter in dash_parameters:
        if dash_parameter:
            rx_dash_parameter = ''.join((r'\B', dash_parameter, r'\b'))
            dash_parameter_match = re.search(rx_dash_parameter, new_arg)
            if dash_parameter_match:
                remove = ''
                parameter_pos = dash_parameter_match.span()[0]

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
                rx_remove = ''.join((' ', re.escape(remove), r'\b'))
                new_arg = re.sub(rx_remove, '', new_arg).strip()
            else:
                if '=' in dash_parameter:
                    result.append(None)
                else:
                    result.append(False)
    return new_arg, *result











# ############################################################################ #
# ----------                      Run the Bot                       ---------- #
# ############################################################################ #

async def __initialize() -> None:
    print('Initializing.')
    await db.init()
    await server_settings.init(BOT)
    await server_settings.clean_up_invalid_server_settings(BOT)
    await sprites.init()
    await login.init()
    await daily.init()

    await crew.init()
    await item.init()
    await room.init()
    await user.init()
    global __COMMANDS
    __COMMANDS = sorted([key for key, value in BOT.all_commands.items() if value.hidden == False])
    INITIALIZED = True
    print(f'Initialized!')


def run_bot() -> None:
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    BOT.run(token)