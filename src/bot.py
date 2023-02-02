import asyncio
import datetime
import logging
import json
import os
import sys
from typing import List, Optional, Tuple, Type

from discord import Activity, ActivityType, ApplicationCommand, ApplicationContext, Embed, Guild, Intents, Message, SlashCommand, SlashCommandGroup, TextChannel
from discord import ApplicationCommandInvokeError, CheckFailure
from discord import __version__ as discord_version
from discord.ext.commands import Context, when_mentioned_or
import discord.errors as errors
import discord.ext.commands.errors as command_errors
import discord.ext.tasks as tasks

from . import database as db
from .gdrive import TourneyDataClient
from . import pss_crew as crew
from . import pss_daily as daily
from . import pss_dropship as dropship
from .pss_exception import Error, MaintenanceError, NotFound, SelectTimeoutError
from . import pss_item as item
from . import pss_login as login
from . import pss_marker as marker
from . import pss_room as room
from . import pss_sprites as sprites
from . import pss_user as user
from . import server_settings
from .server_settings import GUILD_SETTINGS
from . import settings
from . import utils
from . yadc_bot import YadcBot





# ############################################################################ #
# ----------                       Bot Setup                        ---------- #
# ############################################################################ #

async def get_prefix(bot: YadcBot, message: Message) -> str:
    result = await server_settings.get_prefix(bot, message)
    return when_mentioned_or(result)(bot, message)

INTENTS: Intents = Intents.default()
if settings.INTENT_MESSAGE_CONTENT:
    INTENTS.message_content = True

BOT = YadcBot(
    command_prefix=get_prefix,
    description='This is a Discord Bot for Pixel Starships',
    activity=Activity(type=ActivityType.playing, name='Slash Commands only. Visit support.dolores2.xyz for help.'),
    debug_guilds=settings.DEBUG_GUILDS or None,
    intents=INTENTS,
)


__COMMANDS = []

INITIALIZED: bool = False

PWD: str = os.getcwd()


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

    await __initialize()

    print(f'sys.argv: {sys.argv}')
    print(f'Current time: {utils.format.datetime(utils.get_utc_now())}')
    print(f'Current Working Directory: {PWD}')
    print(f'Bot logged in as {BOT.user.name} (id={BOT.user.id}) on {len(BOT.guilds)} servers')
    print(f'Bot version is: {settings.VERSION}')
    schema_version = await db.get_schema_version()
    print(f'DB schema version is: {schema_version}')
    print(f'Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
    print(f'py-cord version: {discord_version}')

    if settings.FEATURE_AUTODAILY_ENABLED:
        print('Starting auto-daily loop.')
        autodaily_loop.start()

    if settings.FEATURE_AUTOTRADER_ENABLED:
        print('Starting auto-trader loop.')
        autotrader_loop.start()


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
async def on_application_command_error(ctx: ApplicationContext, err: Exception):
    __log_slash_command_use_error(ctx, err)

    if settings.THROW_COMMAND_ERRORS:
        raise err
    else:
        error_type = type(err).__name__
        error_message = str(err)
        retry_after = None
        if isinstance(err, command_errors.CommandOnCooldown):
            error_message += f'\nThis message will delete itself, when you may use the command again.'
            retry_after = err.retry_after
        elif isinstance(err, (CheckFailure, command_errors.MissingPermissions)):
            error_message = error_message or 'You don\'t have the required permissions in order to be able to use this command!'
        elif isinstance(err, ApplicationCommandInvokeError):
            # Check err.original here for custom exceptions
            if err.original:
                error_type = type(err.original).__name__
                if isinstance(err.original, Error):
                    if isinstance(err.original, SelectTimeoutError):
                        return
                    else:
                        if isinstance(err.original, MaintenanceError):
                            error_type = 'Pixel Starships is under maintenance'
                        error_message = f'{err.original.msg}'
                else:
                    error_message = f'{err.original}'
        elif not isinstance(err, command_errors.MissingRequiredArgument):
                logging.getLogger().error(err, exc_info=True)

        title = ' '.join(utils.parse.camel_case(error_type))
        as_embed = await server_settings.get_use_embeds(ctx)
        try:
            if as_embed:
                colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
                if retry_after:
                    error_message = f'{ctx.author.mention}\n{error_message}'
                embed = utils.discord.create_embed(title, description=error_message, colour=colour)
                output = [embed]
            else:
                error_message = '\n'.join([f'> {x}' for x in error_message.splitlines()])
                if retry_after:
                    error_message = f'> {ctx.author.mention}\n{error_message}'
                output = [f'**{title}**', error_message]
            if ctx.interaction.response.is_done():
                await utils.discord.edit_original_response(ctx, ctx.interaction, output)
            else:
                await utils.discord.respond_with_output(ctx, output)
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
async def autodaily_loop() -> None:
    MAX_GET_INFO_ATTEMPTS = 3
    utc_now = utils.get_utc_now()
    if utc_now < settings.POST_AUTODAILY_FROM:
        return

    utc_now = utils.get_utc_now()

    attempts = MAX_GET_INFO_ATTEMPTS
    while attempts > 0:
        try:
            daily_info = await daily.get_daily_info()
            attempts = 0
        except Exception as ex:
            print(f'ERROR: There was an error while trying to retrieve daily info:\n{ex}')
            attempts -= 1
            if attempts == 0:
                print(f'ERROR: Could not retrieve the daily info after {MAX_GET_INFO_ATTEMPTS} attempts.')
                return

    db_daily_info, db_daily_modify_date = await daily.db_get_daily_info()
    has_daily_changed = daily.has_daily_changed(daily_info, utc_now, db_daily_info, db_daily_modify_date)

    if has_daily_changed:
        print(f'[autodaily_loop] daily info changed:\n{json.dumps(daily_info, indent=2)}')
        autodaily_settings = await server_settings.get_autodaily_settings(utc_now=utc_now)
        print(f'[autodaily_loop] retrieved {len(autodaily_settings)} guilds to post to')
    else:
        autodaily_settings = await server_settings.get_autodaily_settings(no_post_yet=True)
        if autodaily_settings:
            print(f'[autodaily_loop] retrieved new {len(autodaily_settings)} channels without a post, yet.')

    created_output = False
    posted_count = 0
    if autodaily_settings:
        output, output_embeds, created_output = await dropship.get_dropship_text(daily_info=daily_info)
        if created_output:
            current_daily_message = '\n'.join(output)
            current_daily_embed = output_embeds[0]
            posted_count = await post_dailies(current_daily_message, current_daily_embed, autodaily_settings, utc_now)
        print(f'[autodaily_loop] posted to {posted_count} of {len(autodaily_settings)} guilds')

    if has_daily_changed and (created_output or not autodaily_settings):
        await daily.db_set_daily_info(daily_info, utc_now)


@autodaily_loop.before_loop
async def before_autodaily_loop() -> None:
    await BOT.wait_until_ready()


async def post_dailies(current_daily_message: str, current_daily_embed: Embed, autodaily_settings: List[server_settings.AutoMessageSettings], utc_now: datetime.datetime) -> int:
    posted_count = 0
    for guild_autodaily_settings in autodaily_settings:
        if guild_autodaily_settings.guild_id is not None and guild_autodaily_settings.channel_id is not None:
            posted, can_post, latest_message = await __post_automessage(guild_autodaily_settings.channel, guild_autodaily_settings.latest_message_id, guild_autodaily_settings.change_mode, current_daily_message, current_daily_embed, utc_now, True)
            if posted:
                posted_count += 1
            else:
                guild_name = guild_autodaily_settings.guild.name if guild_autodaily_settings.guild else None
                guild_id = guild_autodaily_settings.guild_id
                channel_name = f'#{guild_autodaily_settings.channel.name}' if guild_autodaily_settings.channel else '<not accessible>'
                channel_id = guild_autodaily_settings.channel_id
                print(f'[post_dailies] Failed to post to guild \'{guild_name}\' ({guild_id}), channel \'{channel_name}\' ({channel_id})')
            await guild_autodaily_settings.update(can_post=can_post, latest_message=latest_message, store_now_as_created_at=(not can_post and not latest_message))
    return posted_count


__FIRST_AUTOTRADER_POST_TIME = datetime.time(0, 0, 30, 0, datetime.timezone.utc)
__SECOND_AUTOTRADER_POST_TIME = datetime.time(12, 0, 30, 0, datetime.timezone.utc)

@tasks.loop(time=(__FIRST_AUTOTRADER_POST_TIME, __SECOND_AUTOTRADER_POST_TIME))
async def autotrader_loop() -> None:
    utc_now = utils.get_utc_now()

    autotrader_message_embed, autotrader_message_text = None, None
    trader_details_attempts = 0

    while not autotrader_message_embed and not autotrader_message_text:
        try:
            autotrader_message_embed, autotrader_message_text = await marker.get_autotrader_details()
            print(f'[autotrader_loop] Retrieved trader info after {trader_details_attempts + 1} attempts.')
        except NotFound:
            print(f'[autotrader_loop] ERROR: Could not retrieve the trader info. Trying again in 15 seconds.')
            trader_details_attempts += 1
            await asyncio.sleep(15)

    all_autotrader_settings = server_settings.GUILD_SETTINGS.autotrader_settings

    if all_autotrader_settings:
        posted_count = 0
        for autotrader_settings in all_autotrader_settings:
            if autotrader_settings.guild_id is not None and autotrader_settings.channel_id is not None:
                # post message
                posted, can_post, latest_message = await __post_automessage(autotrader_settings.channel, autotrader_settings.latest_message_id, autotrader_settings.change_mode, autotrader_message_text, autotrader_message_embed, utc_now, False)
                if posted:
                    posted_count += 1
                else:
                    guild_name = autotrader_settings.guild.name if autotrader_settings.guild else None
                    guild_id = autotrader_settings.guild_id
                    channel_name = f'#{autotrader_settings.channel.name}' if autotrader_settings.channel else '<not accessible>'
                    channel_id = autotrader_settings.channel_id
                    print(f'[autotrader_loop] Failed to post to guild \'{guild_name}\' ({guild_id}), channel \'{channel_name}\' ({channel_id})')
                await autotrader_settings.update(can_post=can_post, latest_message=latest_message, store_now_as_created_at=(not can_post and not latest_message))

        print(f'[autotrader_loop] posted to {posted_count} of {len(all_autotrader_settings)} guilds')


@autotrader_loop.before_loop
async def before_autotrader_loop() -> None:
    await BOT.wait_until_ready()



async def __post_automessage(text_channel: TextChannel, latest_message_id: int, change_mode: bool, current_daily_message: str, current_daily_embed: Embed, utc_now: datetime.datetime, replace_current_day_message: bool) -> Tuple[bool, bool, Message]:
    """
    Returns (posted, can_post, latest_message)
    """
    posted = False
    if text_channel and current_daily_message:
        error_msg_delete = f'could not delete message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_edit = f'could not edit message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_post = f'could not post a message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]'

        post_new = change_mode != server_settings.AutoMessageChangeMode.EDIT
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
            can_post, latest_message = await __auto_fetch_latest_message(text_channel, latest_message_id)

        if can_post:
            # If replace_current_day_message is True, check if the message has been created today
            if latest_message and (not replace_current_day_message or (utc_now and utc_now.day == latest_message.created_at.day)):
                latest_message_id = latest_message.id
                if change_mode == server_settings.AutoMessageChangeMode.DELETE_AND_POST_NEW:
                    try:
                        deleted = await utils.discord.try_delete_message(latest_message)
                        if deleted:
                            latest_message = None
                            utils.dbg_prnt(f'[post_automessage] deleted message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                        else:
                            print(f'[post_automessage] could not delete message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                    except errors.NotFound:
                        print(f'[post_automessage] {error_msg_delete}: the message could not be found')
                    except errors.Forbidden:
                        print(f'[post_automessage] {error_msg_delete}: the bot doesn\'t have the required permissions.')
                        can_post = False
                    except Exception as err:
                        print(f'[post_automessage] {error_msg_delete}: {err}')
                        can_post = False
                elif change_mode == server_settings.AutoMessageChangeMode.EDIT:
                    try:
                        if use_embeds:
                            await latest_message.edit(embed=embed)
                        else:
                            await latest_message.edit(content=current_daily_message)
                        posted = True
                        utils.dbg_prnt(f'[post_automessage] edited message [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                    except errors.NotFound:
                        print(f'[post_automessage] {error_msg_edit}: the message could not be found')
                    except errors.Forbidden:
                        print(f'[post_automessage] {error_msg_edit}: the bot doesn\'t have the required permissions.')
                        can_post = False
                    except Exception as err:
                        print(f'[post_automessage] {error_msg_edit}: {err}')
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
                    utils.dbg_prnt(f'[post_automessage] posted message [{latest_message.id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                except errors.Forbidden:
                    print(f'[post_automessage] {error_msg_post}: the bot doesn\'t have the required permissions.')
                    can_post = False
                except Exception as err:
                    print(f'[post_automessage] {error_msg_post}: {err}')
                    can_post = False
        else:
            can_post = False

        if latest_message:
            return posted, can_post, latest_message
        else:
            return posted, can_post, None
    else:
        return posted, None, None


async def __auto_fetch_latest_message(text_channel: TextChannel, latest_message_id: int) -> Tuple[bool, Message]:
    """
    Attempts to fetch the message by id, then by content from the specified channel.
    Returns (can_post, latest_message)
    """
    can_post: bool = True
    result: Message = None

    if text_channel and latest_message_id is not None:
        try:
            result = await text_channel.fetch_message(latest_message_id)
            utils.dbg_prnt(f'[auto_fetch_latest_message] found latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
        except errors.NotFound:
            print(f'[auto_fetch_latest_message] could not find latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
        except Exception as err:
            print(f'[auto_fetch_latest_message] could not fetch message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {err}')
            can_post = False

    return can_post, result


# ############################################################################ #
# ----------                Command Helper Functions                ---------- #
# ############################################################################ #

def __log_command_use_error(ctx: Context, err: Exception, force_printing: bool = False):
    if settings.PRINT_DEBUG_COMMAND or force_printing:
        print(f'Invoked command had an error: {ctx.message.content}')
        if err:
            print(str(err))


def __log_slash_command_use_error(ctx: ApplicationContext, err: Exception, force_printing: bool = False):
    if settings.PRINT_DEBUG_COMMAND or force_printing:
        print(f'Invoked command had an error: {ctx.message.content}')
        if err:
            print(str(err))





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
    __COMMANDS = sorted([key for key, value in BOT.all_commands.items() if hasattr(value, 'hidden') and value.hidden == False])
    INITIALIZED = True
    print(f'Initialized!')


def load_cog(path: str) -> None:
    print(f'Loading extension \'{path}\'.')
    BOT.extensions.get(path)
    if not BOT.extensions.get(path):
        BOT.load_extension(path)


def run_bot() -> None:
    if settings.OFFER_PREFIXED_COMMANDS:
        load_cog('src.cogs.general')
        load_cog('src.cogs.current')
        load_cog('src.cogs.raw')
        load_cog('src.cogs.settings')
        load_cog('src.cogs.wiki')
        load_cog('src.cogs.owner')
        if settings.FEATURE_TOURNEYDATA_ENABLED:
            load_cog('src.cogs.tournament')

    if settings.OFFER_SLASH_COMMANDS:
        load_cog('src.cogs.slash_general')
        load_cog('src.cogs.slash_current')
        #load_cog('src.cogs.slash_raw')
        load_cog('src.cogs.slash_settings')
        #load_cog('src.cogs.slash_wiki')
        #load_cog('src.cogs.slash_owner')
        if settings.FEATURE_TOURNEYDATA_ENABLED:
            load_cog('src.cogs.slash_tournament')

    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    BOT.run(token)
