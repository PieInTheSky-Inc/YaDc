from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import asyncio
import calendar
import datetime
import dateutil
import discord
from discord.ext import commands
import holidays
import logging
import json
import math
import os
import pytz
import re
import sys
import time
from typing import Dict, List, Tuple, Union

import database as db
import emojis
import excel
import gdrive
from gdrive import TourneyDataClient
import pagination
import server_settings
from server_settings import GUILD_SETTINGS
import settings
import utility as util

import pss_achievement as achievement
import pss_ai as ai
import pss_assert
import pss_core as core
import pss_crew as crew
import pss_daily as daily
import pss_dropship as dropship
import pss_entity as entity
import pss_exception
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



# ----- Setup ---------------------------------------------------------
RATE = 5
COOLDOWN = 15.0

RAW_RATE = 5
RAW_COOLDOWN = 10.0

PWD = os.getcwd()
sys.path.insert(0, PWD + '/src/')

ACTIVITY = discord.Activity(type=discord.ActivityType.playing, name='/help')

tourney_data_client = TourneyDataClient(
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

__COMMANDS = []









# ----- Bot Setup -------------------------------------------------------------

async def get_prefix(bot: commands.Bot, message: discord.Message) -> str:
    result = await server_settings.get_prefix(bot, message)
    return commands.when_mentioned_or(result)(bot, message)


logging.basicConfig(
    level=logging.INFO,
    style = '{',
    datefmt = '%Y%m%d %H:%M:%S',
    format = '{asctime} [{levelname:<8}] {name}: {message}')

bot = commands.Bot(command_prefix=get_prefix,
                               description='This is a Discord Bot for Pixel Starships',
                               activity=ACTIVITY)

setattr(bot, 'logger', logging.getLogger('bot.py'))











# ----- Bot Events ------------------------------------------------------------
@bot.event
async def on_ready() -> None:
    print(f'sys.argv: {sys.argv}')
    print(f'Current Working Directory: {PWD}')
    print(f'Bot logged in as {bot.user.name} (id={bot.user.id}) on {len(bot.guilds)} servers')
    await db.init()
    schema_version = await db.get_schema_version()
    await server_settings.init(bot)
    await server_settings.clean_up_invalid_server_settings(bot)
    await login.init()
    await daily.init()

    await crew.init()
    await item.init()
    await room.init()
    await user.init()
    global __COMMANDS
    __COMMANDS = sorted([key for key, value in bot.all_commands.items() if value.hidden == False])
    print(f'Initialized!')
    print(f'Bot version is: {settings.VERSION}')
    print(f'DB schema version is: {schema_version}')
    bot.loop.create_task(post_dailies_loop())


@bot.event
async def on_connect():
    print('+ on_connect()')


@bot.event
async def on_resumed():
    print('+ on_resumed()')


@bot.event
async def on_disconnect():
    print('+ on_disconnect()')


@bot.event
async def on_shard_ready():
    print('+ on_shard_ready()')


@bot.event
async def on_command_error(ctx: commands.Context, err: Exception) -> None:
    __log_command_use_error(ctx, err)

    if settings.THROW_COMMAND_ERRORS:
        raise err
    else:
        error_message = str(err)
        retry_after = None
        if isinstance(err, commands.CommandOnCooldown):
            retry_after = err.retry_after
        elif isinstance(err, commands.CommandNotFound):
            prefix = await server_settings.get_prefix(bot, ctx.message)
            invoked_with = ctx.invoked_with.split(' ')[0]
            commands_map = util.get_similarity_map(__COMMANDS, invoked_with)
            bot_commands = [f'`{prefix}{command}`' for command in sorted(commands_map[max(commands_map.keys())])]
            error_message = f'Command `{prefix}{invoked_with}` not found. Do you mean {util.get_or_list(bot_commands)}?'
        elif isinstance(err, commands.CheckFailure):
            error_message = error_message or 'You don\'t have the required permissions in order to be able to use this command!'
        elif isinstance(err, commands.CommandInvokeError):
            if err.original:
                if isinstance(err.original, pss_exception.Error):
                    error_message = f'`{ctx.message.clean_content}`\n{err.original.msg}'
        else:
            if not isinstance(err, commands.MissingRequiredArgument):
                logging.getLogger().error(err, exc_info=True)
            command_args = util.get_exact_args(ctx)
            help_args = ctx.message.clean_content.replace(command_args, '').strip()[1:]
            command = bot.get_command(help_args)
            await ctx.send_help(command)
        error_message = '\n'.join([f'> {x}' for x in error_message.splitlines()])
        if retry_after:
            await ctx.send(f'**Error**\n> {ctx.author.mention}\n{error_message}', delete_after=retry_after)
        else:
            await ctx.send(f'**Error**\n{error_message}')


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    print(f'Joined guild with id {guild.id} ({guild.name})')
    success = await GUILD_SETTINGS.create_guild_settings(bot, guild.id)
    if not success:
        print(f'[on_guild_join] Could not create server settings for guild \'{guild.name}\' (ID: \'{guild.id}\')')


@bot.event
async def on_guild_remove(guild: discord.Guild) -> None:
    print(f'Left guild with id {guild.id} ({guild.name})')
    success = await GUILD_SETTINGS.delete_guild_settings(guild.id)
    if not success:
        print(f'[on_guild_join] Could not delete server settings for guild \'{guild.name}\' (ID: \'{guild.id}\')')










# ----- Tasks ----------------------------------------------------------

async def post_dailies_loop() -> None:
    print(f'Started post dailies loop')
    utc_now = util.get_utcnow()
    while utc_now < settings.POST_AUTODAILY_FROM:
        wait_for = util.get_seconds_to_wait(60, utc_now=utc_now)
        await asyncio.sleep(wait_for)
        utc_now = util.get_utcnow()

    while True:
        utc_now = util.get_utcnow()
        yesterday = datetime.datetime(utc_now.year, utc_now.month, utc_now.day) - settings.ONE_SECOND

        daily_info = await daily.get_daily_info()
        db_daily_info, db_daily_modify_date = await daily.db_get_daily_info()
        has_daily_changed = daily.has_daily_changed(daily_info, utc_now, db_daily_info, db_daily_modify_date)

        autodaily_settings = await server_settings.get_autodaily_settings(bot, no_post_yet=True)
        if autodaily_settings:
            print(f'[post_dailies_loop] retrieved {len(autodaily_settings)} channels')
        if has_daily_changed:
            print(f'[post_dailies_loop] daily info changed:\n{json.dumps(daily_info)}')
            post_here = await server_settings.get_autodaily_settings(bot)
            print(f'[post_dailies_loop] retrieved {len(post_here)} guilds to post')
            autodaily_settings.extend(post_here)

        created_output = False
        posted_count = 0
        if autodaily_settings:
            autodaily_settings = daily.remove_duplicate_autodaily_settings(autodaily_settings)
            print(f'[post_dailies_loop] going to post to {len(autodaily_settings)} guilds')

            latest_message_output, _ = await dropship.get_dropship_text(daily_info=db_daily_info)
            latest_daily_message = '\n'.join(latest_message_output)
            output, created_output = await dropship.get_dropship_text(daily_info=daily_info)
            if created_output:
                current_daily_message = '\n'.join(output)
                posted_count = await post_dailies(current_daily_message, autodaily_settings, utc_now, yesterday, latest_daily_message)
            print(f'[post_dailies_loop] posted to {posted_count} of {len(autodaily_settings)} guilds')

        if has_daily_changed:
            if created_output or not autodaily_settings:
                await daily.db_set_daily_info(daily_info, utc_now)

        seconds_to_wait = util.get_seconds_to_wait(5)
        await asyncio.sleep(seconds_to_wait)


async def post_dailies(current_daily_message: str, autodaily_settings: List[server_settings.AutoDailySettings], utc_now: datetime.datetime, yesterday: datetime.datetime, latest_daily_message_contents: str) -> int:
    posted_count = 0
    for settings in autodaily_settings:
        if settings.guild.id is not None and settings.channel_id is not None:
            posted, can_post, latest_message = await post_autodaily(settings.channel, settings.latest_message_id, settings.change_mode, current_daily_message, utc_now, yesterday, latest_daily_message_contents)
            if posted:
                posted_count += 1
                await notify_on_autodaily(settings.guild, settings.notify, settings.notify_type)
            await settings.update(can_post=can_post, latest_message=latest_message, store_now_as_created_at=(not can_post and not latest_message))
    return posted_count


async def post_autodaily(text_channel: discord.TextChannel, latest_message_id: int, change_mode: bool, current_daily_message: str, utc_now: datetime.datetime, yesterday: datetime.datetime, latest_daily_message_contents: str) -> (bool, bool, discord.Message):
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
        latest_message: discord.Message = None

        if can_post:
            can_post, latest_message = await daily_fetch_latest_message(text_channel, latest_message_id, yesterday, latest_daily_message_contents, current_daily_message)

        if can_post:
            if latest_message and latest_message.created_at.day == utc_now.day:
                latest_message_id = latest_message.id
                if latest_message.content == current_daily_message:
                    post_new = False
                elif change_mode == server_settings.AutoDailyChangeMode.DELETE_AND_POST_NEW:
                    try:
                        await latest_message.delete()
                        latest_message = None
                        print(f'[post_autodaily] deleted message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                    except discord.NotFound:
                        print(f'[post_autodaily] {error_msg_delete}: the message could not be found')
                    except discord.Forbidden:
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
                    except discord.NotFound:
                        print(f'[post_autodaily] {error_msg_edit}: the message could not be found')
                    except discord.Forbidden:
                        print(f'[post_autodaily] {error_msg_edit}: the bot doesn\'t have the required permissions.')
                        can_post = False
                    except Exception as err:
                        print(f'[post_autodaily] {error_msg_edit}: {err}')
                        can_post = False
            else:
                post_new = True

            if can_post and post_new:
                try:
                    latest_message = await text_channel.send(current_daily_message)
                    posted = True
                    print(f'[post_autodaily] posted message [{latest_message.id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
                except discord.Forbidden:
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


async def daily_fetch_latest_message(text_channel: discord.TextChannel, latest_message_id: int, yesterday: datetime.datetime, latest_daily: str, current_daily: str) -> (bool, discord.Message):
    """
    Attempts to fetch the message by id, then by content from the specified channel.
    Returns (can_post, latest_message)
    """
    can_post: bool = True
    result: discord.Message = None

    if text_channel:
        if latest_message_id is not None:
            try:
                result = await text_channel.fetch_message(latest_message_id)
                print(f'[daily_fetch_latest_message] found latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
            except discord.NotFound:
                print(f'[daily_fetch_latest_message] could not find latest message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')
            except Exception as err:
                print(f'[daily_fetch_latest_message] could not fetch message by id [{latest_message_id}] in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {err}')
                can_post = False
        if result is None:
            try:
                async for message in text_channel.history(after=yesterday):
                    if message.author == bot.user and (message.content == latest_daily or message.content == current_daily):
                        result = message
                        print(f'[daily_fetch_latest_message] found latest message by content in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {result.id}')
                        break
            except Exception as err:
                print(f'[daily_fetch_latest_message] could not find latest message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]: {err}')
                can_post = False
            if result is None:
                print(f'[daily_fetch_latest_message] could not find latest message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]')

    return can_post, result


async def notify_on_autodaily(guild: discord.Guild, notify: Union[discord.Member, discord.Role], notify_type: server_settings.AutoDailyNotifyType) -> None:
    if guild is not None and notify is not None and notify_type is not None:
        message = f'The auto-daily has been reposted on Discord server \'{guild.name}\''
        members = []
        if notify_type == server_settings.AutoDailyNotifyType.USER:
            if guild.id == notify.guild.id:
                members.append(notify)
        elif notify_type == server_settings.AutoDailyNotifyType.ROLE:
            if guild.id == notify.guild.id:
                members = notify.members
        for member in members:
            await member.send(content=message)











# ---------- General Bot Commands ----------

@bot.command(brief='Display info on this bot', name='about', aliases=['info'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_about(ctx: commands.Context):
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
        guilds = [guild for guild in bot.guilds if guild.id not in settings.IGNORE_SERVER_IDS_FOR_COUNTING]
        all_users = set(bot.users)
        users = []
        bots = []
        for user in all_users:
            if user.bot:
                bots.append(user)
            else:
                users.append(user)
        user_name = bot.user.display_name
        if ctx.guild is None:
            nick = bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        has_nick = bot.user.display_name != nick
        pfp_url = bot.user.avatar_url
        about_info = core.read_about_file()
        title = f'About {nick}'
        if has_nick:
            title += f' ({user_name})'
        description = about_info['description']
        footer = f'Serving {len(users)} users & {len(bots)} bots on {len(guilds)} guilds.'
        version = f'v{settings.VERSION}'
        support_link = about_info['support']
        authors = ', '.join(about_info['authors'])
        pfp_author = about_info['pfp']
        color = util.get_bot_member_colour(bot, ctx.guild)

        embed = discord.Embed(title=title, type='rich', color=color, description=description)
        embed.add_field(name="version", value=version)
        embed.add_field(name="authors", value=authors)
        embed.add_field(name="profile pic by", value=pfp_author)
        embed.add_field(name="support", value=support_link)
        embed.set_footer(text=footer)
        embed.set_thumbnail(url=pfp_url)
    await ctx.send(embed=embed)


@bot.command(brief='Get an invite link', name='invite')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_invite(ctx: commands.Context):
    """
    Produces an invite link for this bot and sends it via DM.

    Usage:
      /invite

    Examples:
      /invite - Produces an invite link for this bot and sends it via DM.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        if ctx.guild is None:
            nick = bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        output = [f'Invite {nick} to your server: {settings.BASE_INVITE_URL}{bot.user.id}']
    await util.dm_author(ctx, output)
    if not isinstance(ctx.channel, (discord.DMChannel, discord.GroupChannel)):
        await ctx.send(f'{ctx.author.mention} Sent invite link via DM.')


@bot.command(brief='Show links', name='links')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_links(ctx: commands.Context):
    """
    Shows the links for useful sites regarding Pixel Starships.

    Usage:
      /links

    Examples:
      /links - Shows the links for useful sites regarding Pixel Starships.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = core.read_links_file()
    await util.post_output(ctx, output)


@bot.command(brief='Ping the server', name='ping')
async def cmd_ping(ctx: commands.Context):
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










# ---------- PSS Bot Commands ----------

@bot.command(brief='Get best items for a slot', name='best')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_best(ctx: commands.Context, slot: str, *, stat: str = None):
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
            items_designs_details = await item.get_items_designs_details_by_name(item_name)
            found_matching_items = items_designs_details and len(items_designs_details) > 0
            items_designs_details = item.filter_items_designs_details_for_equipment(items_designs_details)
        else:
            items_designs_details = []
            found_matching_items = False
        if items_designs_details:
            if len(items_designs_details) == 1:
                item_design_details = items_designs_details[0]
            else:
                use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
                paginator = pagination.Paginator(ctx, item_name, items_designs_details, item.get_item_search_details, use_pagination)
                _, item_design_details = await paginator.wait_for_option_selection()
            slot, stat = item.get_slot_and_stat_type(item_design_details)
        else:
            if found_matching_items:
                raise pss_exception.Error(f'The item `{item_name}` is not a gear type item!')

        slot, stat = item.fix_slot_and_stat(slot, stat)
        output, _ = await item.get_best_items(slot, stat)
    await util.post_output(ctx, output)


@bot.command(brief='Get character stats', name='char', aliases=['crew'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_char(ctx: commands.Context, level: str = None, *, crew_name: str = None):
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
        level, crew_name = util.get_level_and_name(level, crew_name)
        output, _ = await crew.get_char_design_details_by_name(crew_name, level=level)
    await util.post_output(ctx, output)


@bot.command(brief='Get crafting recipes', name='craft', aliases=['upg', 'upgrade'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_craft(ctx: commands.Context, *, item_name: str):
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
        output, _ = await item.get_item_upgrades_from_name(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get prestige combos of crew', name='prestige')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_prestige(ctx: commands.Context, *, crew_name: str):
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
        output, _ = await crew.get_prestige_from_info(crew_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get character recipes', name='recipe')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_recipe(ctx: commands.Context, *, crew_name: str):
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
        output, _ = await crew.get_prestige_to_info(crew_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item ingredients', name='ingredients', aliases=['ing'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_ingredients(ctx: commands.Context, *, item_name: str):
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
        output, _ = await item.get_ingredients_for_item(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item\'s market prices and fair prices from the PSS API', name='price', aliases=['fairprice', 'cost'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_price(ctx: commands.Context, *, item_name: str):
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
        output, _ = await item.get_item_price(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item/crew stats', name='stats', aliases=['stat'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_stats(ctx: commands.Context, level: str = None, *, name: str = None):
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
        level, name = util.get_level_and_name(level, name)
        try:
            char_output, char_success = await crew.get_char_design_details_by_name(name, level)
        except pss_exception.InvalidParameter:
            char_output = None
            char_success = False
        try:
            item_output, item_success = await item.get_item_details_by_name(name)
        except pss_exception.InvalidParameter:
            item_output = None
            item_success = False

    if char_success:
        await util.post_output(ctx, char_output)

    if item_success:
        if char_success:
            await ctx.send(settings.EMPTY_LINE)
        await util.post_output(ctx, item_output)

    if not char_success and not item_success:
        await ctx.send(f'Could not find a character or an item named `{full_name}`.')


@bot.command(brief='Get item stats', name='item')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_item(ctx: commands.Context, *, item_name: str):
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
        output, _ = await item.get_item_details_by_name(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get research data', name='research')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_research(ctx: commands.Context, *, research_name: str):
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
        output, _ = await research.get_research_infos_by_name(research_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get collections', name='collection', aliases=['coll'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_collection(ctx: commands.Context, *, collection_name: str = None):
    """
    Get the details on a specific collection. If the collection name is omitted, it will display all collections.

    Usage:
      /collection <collection_name>

    Parameters:
      collection_name: The name of the collection to get details on.

    Examples:
      /collection_name savy - Will print information on a collection having 'savy' in its name.
      /collection - Will print less information on all collections.

    Notes:
      This command will only print stats for the collection with the best matching collection_name.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output, _ = await crew.get_collection_design_details_by_name(collection_name)
    await util.post_output(ctx, output)


@bot.group(brief='Division stars', name='stars', invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_stars(ctx: commands.Context, *, division: str = None):
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
            async with ctx.typing():
                output = []
                if not pss_top.is_valid_division_letter(division):
                    subcommand = bot.get_command('stars fleet')
                    await ctx.invoke(subcommand, fleet_name=division)
                else:
                    async with ctx.typing():
                        output, _ = await pss_top.get_division_stars(division=division)
            await util.post_output(ctx, output)
    else:
        cmd = bot.get_command('past stars')
        await ctx.invoke(cmd, month=None, year=None, division=division)


@cmd_stars.command(brief='Fleet stars', name='fleet', aliases=['alliance'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_stars_fleet(ctx: commands.Context, *, fleet_name: str):
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
            exact_name = util.get_exact_args(ctx)
            if exact_name:
                fleet_name = exact_name
            fleet_infos = await fleet.get_fleet_infos_by_name(fleet_name)
            fleet_infos = [fleet_info for fleet_info in fleet_infos if fleet_info['DivisionDesignId'] != '0']

        if fleet_infos:
            if len(fleet_infos) == 1:
                fleet_info = fleet_infos[0]
            else:
                use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
                paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details, use_pagination)
                _, fleet_info = await paginator.wait_for_option_selection()

            if fleet_info:
                async with ctx.typing():
                    fleet_users_infos = await fleet.get_fleet_users_by_info(fleet_info)
                    output = fleet.get_fleet_users_stars_from_info(fleet_info, fleet_users_infos)
                await util.post_output(ctx, output)
        else:
            await ctx.send(f'Could not find a fleet named `{fleet_name}` participating in the current tournament.')
    else:
        cmd = bot.get_command('past stars fleet')
        await ctx.invoke(cmd, month=None, year=None, fleet_name=fleet_name)


@bot.command(brief='Show the dailies', name='daily')
@commands.cooldown(rate=RATE, per=COOLDOWN*2, type=commands.BucketType.user)
async def cmd_daily(ctx: commands.Context):
    """
    Prints the MOTD along today's contents of the dropship, the merchant ship, the shop and the sale.

    Usage:
      /daily

    Examples:
      /daily - Prints the information described above.
    """
    __log_command_use(ctx)
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = await dropship.get_dropship_text()
    await util.post_output(ctx, output)


@bot.command(brief='Show the news', name='news')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_news(ctx: commands.Context):
    """
    Prints all news in ascending order.

    Usage:
      /news

    Examples:
      /news - Prints the information described above.
    """
    __log_command_use(ctx)
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = await dropship.get_news()
    await util.post_output(ctx, output)


@bot.command(brief='Get crew levelling costs', name='level', aliases=['lvl'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_level(ctx: commands.Context, from_level: int, to_level: int = None):
    """
    Shows the cost for a crew to reach a certain level.

    Usage:
      /level <from_level> [to_level]
      /lvl <from_level> [to_level]

    Parameters:
      from_level: The level from which on the requirements shall be calculated. If specified, must be lower than [to_level]. Optional.
      to_level:   The level to which the requirements shall be calculated. Mandatory.

    Examples:
      /level 35 - Prints exp and gas requirements from level 1 to 35
      /level 25 35 - Prints exp and gas requirements from level 25 to 35"""
    __log_command_use(ctx)
    async with ctx.typing():
        output, _ = crew.get_level_costs(from_level, to_level)
    await util.post_output(ctx, output)


@bot.group(brief='Prints top fleets or captains', name='top', invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_top(ctx: commands.Context, *, count: str = '100'):
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
                command = split_count[1]
            except:
                try:
                    count = int(split_count[1])
                    command = split_count[0]
                except:
                    raise ValueError('Invalid parameter provided! Parameter must be an integer or a sub-command.')
        else:
            try:
                count = int(count)
            except:
                raise ValueError('Invalid parameter provided! Parameter must be an integer or a sub-command.')
            command = 'fleets'
        cmd = bot.get_command(f'top {command}')
        await ctx.invoke(cmd, count=count)


@cmd_top.command(brief='Prints top captains', name='players', aliases=['captains', 'users'])
async def cmd_top_captains(ctx: commands.Context, count: int = 100):
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
    async with ctx.typing():
        output, _ = await pss_top.get_top_captains(count)
    await util.post_output(ctx, output)


@cmd_top.command(brief='Prints top fleets', name='fleets', aliases=['alliances'])
async def cmd_top_fleets(ctx: commands.Context, count: int = 100):
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
    async with ctx.typing():
        output, _ = await pss_top.get_top_fleets(count)
    await util.post_output(ctx, output)


@bot.command(brief='Get room infos', name='room')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_room(ctx: commands.Context, *, room_name: str):
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
        output, _ = await room.get_room_details_by_name(room_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get training infos', name='training')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_training(ctx: commands.Context, *, training_name: str):
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
        output, _ = await training.get_training_details_from_name(training_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get PSS stardate & Melbourne time', name='time')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_time(ctx: commands.Context):
    """
    Get PSS stardate, as well as the day and time in Melbourne, Australia. Gives the name of the Australian holiday, if it is a holiday in Australia.

    Usage:
      /time

    Examples:
      /time - Prints PSS stardate, day & time in Melbourne and public holidays.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        now = datetime.datetime.now()
        today = datetime.date(now.year, now.month, now.day)
        pss_stardate = (today - settings.PSS_START_DATE).days
        str_time = 'Today is Stardate {}\n'.format(pss_stardate)

        mel_tz = pytz.timezone('Australia/Melbourne')
        mel_time = now.replace(tzinfo=datetime.timezone.utc).astimezone(mel_tz)
        str_time += mel_time.strftime('It is %A, %H:%M in Melbourne')

        aus_holidays = holidays.Australia(years=now.year, prov='ACT')
        mel_time = datetime.date(mel_time.year, mel_time.month, mel_time.day)
        if mel_time in aus_holidays:
            str_time += '\nIt is also a holiday ({}) in Australia'.format(aus_holidays[mel_time])

        first_day_of_next_month = datetime.datetime(now.year, (now.month + 1) % 12 or 12, 1)
        td = first_day_of_next_month - now
        str_time += '\nTime until the beginning of next month: {}d {}h {}m'.format(td.days, td.seconds//3600, (td.seconds//60) % 60)
    await ctx.send(str_time)


@bot.group(brief='Information on tournament time', name='tournament', aliases=['tourney'])
@commands.cooldown(rate=RATE*10, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_tournament(ctx: commands.Context):
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
        cmd = bot.get_command('tournament current')
        await ctx.invoke(cmd)


@cmd_tournament.command(brief='Information on this month\'s tournament time', name='current')
async def cmd_tournament_current(ctx: commands.Context):
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
        utc_now = util.get_utcnow()
        start_of_tourney = tourney.get_current_tourney_start()
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@cmd_tournament.command(brief='Information on next month\'s tournament time', name='next')
async def cmd_tournament_next(ctx: commands.Context):
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
        utc_now = util.get_utcnow()
        start_of_tourney = tourney.get_next_tourney_start()
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@bot.command(brief='Updates all caches manually', name='updatecache', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
async def cmd_updatecache(ctx: commands.Context):
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
    await ctx.send('Updated all caches successfully!')



@bot.command(brief='Get infos on a fleet', name='fleet', aliases=['alliance'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_fleet(ctx: commands.Context, *, fleet_name: str):
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
        exact_name = util.get_exact_args(ctx)
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
                output, file_paths = await fleet.get_full_fleet_info_as_text(fleet_info)
            await util.post_output_with_files(ctx, output, file_paths)
            for file_path in file_paths:
                os.remove(file_path)
    else:
        await ctx.send(f'Could not find a fleet named `{fleet_name}`.')


@bot.command(brief='Get infos on a player', name='player', aliases=['user'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_player(ctx: commands.Context, *, player_name: str):
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
        exact_name = util.get_exact_args(ctx)
        if exact_name:
            player_name = exact_name
        user_infos = await user.get_user_details_by_name(player_name)

    if user_infos:
        if len(user_infos) == 1:
            user_info = user_infos[0]
        else:
            use_pagination = await server_settings.db_get_use_pagination(ctx.guild)
            paginator = pagination.Paginator(ctx, player_name, user_infos, user.get_user_search_details, use_pagination)
            _, user_info = await paginator.wait_for_option_selection()

        if user_info:
            async with ctx.typing():
                output = await user.get_user_details_by_info(user_info)
            await util.post_output(ctx, output)
    else:
        await ctx.send(f'Could not find a player named `{player_name}`.')


@bot.command(brief='Invite to bot\'s support server', name='support')
async def cmd_support(ctx: commands.Context):
    """
    Produces an invite link to the support server for this bot and sends it via DM.

    Usage:
      /support

    Examples:
      /support - Produces an invite link to the support server and sends it via DM.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        about = core.read_about_file()
        output = [about['support']]
    await util.dm_author(ctx, output)
    if not isinstance(ctx.channel, (discord.DMChannel, discord.GroupChannel)):
        await ctx.send(f'{ctx.author.mention} Sent invite link via DM.')











@bot.group(brief='Server settings', name='settings', invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings(ctx: commands.Context):
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
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if ctx.invoked_subcommand is None:
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)

            output = [f'**```Server settings for {ctx.guild.name}```**']
            output.extend(guild_settings.autodaily.get_pretty_settings())
            output.extend(guild_settings.get_pretty_bot_news_channel())
            output.append(f'Pagination = {guild_settings.pretty_use_pagination}')
            output.append(f'Prefix = {guild_settings.prefix}')
        await util.post_output(ctx, output)


@cmd_settings.group(brief='Retrieve auto-daily settings', name='autodaily', aliases=['daily'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_autodaily(ctx: commands.Context):
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
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if util.is_guild_channel(ctx.channel) and ctx.invoked_subcommand is None:
        output = []
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            output = guild_settings.autodaily.get_pretty_settings()
        await util.post_output(ctx, output)


@cmd_settings_get_autodaily.command(brief='Retrieve auto-daily channel', name='channel', aliases=['ch'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_autodaily_channel(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            output = guild_settings.autodaily.get_pretty_setting_channel()
        await util.post_output(ctx, output)


@cmd_settings_get_autodaily.command(brief='Retrieve auto-daily mode', name='changemode', aliases=['mode'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_autodaily_mode(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            output = guild_settings.autodaily.get_pretty_setting_changemode()
        await util.post_output(ctx, output)


@cmd_settings_get_autodaily.command(brief='Retrieve auto-daily notify', name='notify')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_autodaily_notify(ctx: commands.Context):
    """
    Retrieve the auto-daily setting for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings autodaily notify
      /settings daily notify

    Examples:
      /settings autodaily notify - Prints the auto-daily notification settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            output = guild_settings.autodaily.get_pretty_setting_notify()
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve the bot news channel', name='botnews', aliases=['botchannel'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_botnews(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            output = guild_settings.get_pretty_bot_news_channel()
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve pagination settings', name='pagination', aliases=['pages'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_pagination(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            output = [f'Pagination on this server has been set to: `{guild_settings.pretty_use_pagination}`']
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve prefix settings', name='prefix')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_prefix(ctx: commands.Context):
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

    command = bot.get_command('prefix')
    await ctx.invoke(command)


@bot.command(brief='Retrieve prefix settings', name='prefix')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_prefix(ctx: commands.Context):
    """
    Retrieve the prefix setting for this server.

    This command can only be used on Discord servers/guilds.

    Usage:
      /prefix

    Examples:
      /prefix - Prints the prefix setting for the current Discord server/guild.
    """
    __log_command_use(ctx)

    channel_type = 'server' if util.is_guild_channel(ctx.channel) else 'channel'
    async with ctx.typing():
        guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
        output = [f'Prefix for this {channel_type} is: `{guild_settings.prefix}`']
    await util.post_output(ctx, output)










@cmd_settings.group(brief='Reset server settings', name='reset', invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset(ctx: commands.Context):
    """
    Reset settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset

    Examples:
      /settings reset - Resets all settings for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if not util.is_guild_channel(ctx.channel):
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')
    elif ctx.invoked_subcommand is None:
        reset_autodaily = bot.get_command(f'settings reset autodaily')
        reset_pagination = bot.get_command(f'settings reset pagination')
        reset_prefix = bot.get_command(f'settings reset prefix')
        await ctx.invoke(reset_autodaily)
        await ctx.invoke(reset_pagination)
        await ctx.invoke(reset_prefix)


@cmd_settings_reset.group(brief='Reset auto-daily settings to defaults', name='autodaily', aliases=['daily'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_autodaily(ctx: commands.Context):
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
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if util.is_guild_channel(ctx.channel) and ctx.invoked_subcommand is None:
        async with ctx.typing():
            autodaily_settings = (await GUILD_SETTINGS.get(bot, ctx.guild.id)).autodaily
            success = await autodaily_settings.reset()
            if success:
                output = ['Successfully removed all auto-daily settings for this server.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset_autodaily.command(brief='Reset auto-daily channel', name='channel', aliases=['ch'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_autodaily_channel(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            autodaily_settings = (await GUILD_SETTINGS.get(bot, ctx.guild.id)).autodaily
            success = await autodaily_settings.reset_channel()
            if success:
                output = ['Successfully removed the auto-daily channel.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily channel setting for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset_autodaily.command(brief='Reset auto-daily change mode', name='changemode', aliases=['mode'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_autodaily_mode(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            autodaily_settings = (await GUILD_SETTINGS.get(bot, ctx.guild.id)).autodaily
            success = await autodaily_settings.cmd_settings_reset_autodaily_mode()
            if success:
                output = ['Successfully reset the auto-daily change mode.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily notification settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset_autodaily.command(brief='Reset auto-daily notifications', name='notify')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_autodaily_notify(ctx: commands.Context):
    """
    Reset the auto-daily notification settings for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset autodaily notify
      /settings reset daily notify

    Examples:
      /settings reset autodaily notify - Turns off notifications on auto-daily changes for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            autodaily_settings: server_settings.AutoDailySettings = (await GUILD_SETTINGS.get(bot, ctx.guild.id)).autodaily
            success = await autodaily_settings.reset_notify()
            if success:
                output = ['Successfully reset the auto-daily notifications.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily notification settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset.command(brief='Reset bot news channel', name='botnews', aliases=['botchannel'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_bot_news_channel(ctx: commands.Context):
    """
    Resets the bot news channel for this server. When there're important news about this bot, it'll post a message in the configured channel.

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

    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            success = await guild_settings.reset_bot_news_channel()
            if success:
                output = ['Successfully removed the bot news channel.']
            else:
                output = [
                    'An error ocurred while trying to remove the bot news channel setting for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset.command(brief='Reset pagination settings', name='pagination', aliases=['pages'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_pagination(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            success = await guild_settings.reset_use_pagination()
        if success:
            await ctx.invoke(bot.get_command(f'settings pagination'))
        else:
            output = [
                'An error ocurred while trying to reset the pagination settings for this server.',
                'Please try again or contact the bot\'s author.'
            ]
            await util.post_output(ctx, output)


@cmd_settings_reset.command(brief='Reset prefix settings', name='prefix')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_prefix(ctx: commands.Context):
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

    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
            success = await guild_settings.reset_prefix()
        if success:
            output = [f'Successfully reset the prefix for this server to: {guild_settings.prefix}']
            await util.post_output(ctx, output)
        else:
            output = [
                'An error ocurred while trying to reset the prefix settings for this server.',
                'Please try again or contact the bot\'s author.'
            ]
            await util.post_output(ctx, output)










@cmd_settings.group(brief='Change server settings', name='set', invoke_without_command=False)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set(ctx: commands.Context):
    """
    Sets settings for this server.

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


@cmd_settings_set.group(brief='Change auto-daily settings', name='autodaily', aliases=['daily'], invoke_without_command=False)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_autodaily(ctx: commands.Context):
    """
    Change auto-daily settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.
    """
    __log_command_use(ctx)
    await ctx.send_help('settings set autodaily')


@cmd_settings_set_autodaily.command(brief='Set auto-daily channel', name='channel', aliases=['ch'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_autodaily_channel(ctx: commands.Context, text_channel: discord.TextChannel = None):
    """
    Sets the auto-daily channel for this server. This channel will receive an automatic /daily message at 1 am UTC.

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
        autodaily_settings: server_settings.AutoDailySettings = (await GUILD_SETTINGS.get(bot, ctx.guild.id)).autodaily
        success = await autodaily_settings.set_channel(text_channel)
    if success:
        await ctx.invoke(bot.get_command('settings autodaily channel'))
    else:
        output = [f'Could not set autodaily channel for this server. Please try again or contact the bot\'s author.']
        await util.post_output(ctx, output)


@cmd_settings_set_autodaily.command(brief='Set auto-daily repost mode', name='changemode', aliases=['mode'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_autodaily_change(ctx: commands.Context):
    """
    Sets the auto-daily mode for this server. If the contents of the daily post change, this setting decides, whether an existing daily post gets edited, or if it gets deleted and a new one gets posted instead.

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
        autodaily_settings = (await GUILD_SETTINGS.get(bot, ctx.guild.id)).autodaily
        success = await autodaily_settings.toggle_change_mode()
    if success:
        await ctx.invoke(bot.get_command('settings autodaily changemode'))
    else:
        output = [f'Could not set repost on autodaily change mode for this server. Please try again or contact the bot\'s author.']
        await util.post_output(ctx, output)


@cmd_settings_set_autodaily.command(brief='Set auto-daily notify settings', name='notify')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_autodaily_notify(ctx: commands.Context, *, mention: Union[discord.Role, discord.Member] = None):
    """
    Sets the auto-daily notifications for this server. If the contents of the daily post change, this setting decides, who will get notified about that change. You can specify a user or a role. If nothing is being specified, this setting will be reset.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set autodaily notify <member/role mention>
      /settings set daily notify <member/role mention>

    Examples:
      /settings set autodaily notify @notify - Sets the role 'notify' to be notified on changes.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    if mention is None:
        await ctx.invoke(bot.get_command('settings reset autodaily notify'))
    else:
        async with ctx.typing():
            autodaily_settings = (await GUILD_SETTINGS.get(bot, ctx.guild.id)).autodaily
            success = await autodaily_settings.set_notify(mention)
        if success:
            await ctx.invoke(bot.get_command('settings autodaily notify'))
        else:
            output = [f'Could not set notify on autodaily settings for this server. Please try again or contact the bot\'s author.']
            await util.post_output(ctx, output)


@cmd_settings_set.command(brief='Set the bot news channel', name='botnews', aliases=['botchannel'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_bot_news_channel(ctx: commands.Context, text_channel: discord.TextChannel=None):
    """
    Sets the bot news channel for this server. When there're important news about this bot, it'll post a message in the configured channel. If the channel gets omitted, the current channel will be used.

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
        guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
        success = await guild_settings.set_bot_news_channel(text_channel)
    if success:
        await ctx.invoke(bot.get_command('settings botnews'))
    else:
        output = [f'Could not set the bot news channel for this server. Please try again or contact the bot\'s author.']
        await util.post_output(ctx, output)


@cmd_settings_set.command(brief='Set pagination', name='pagination', aliases=['pages'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_pagination(ctx: commands.Context, switch: str = None):
    """
    Sets or toggle the pagination for this server. The default is 'ON'. For information on what pagination is and what it does, use this command: /help pagination

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set pagination <switch>
      /settings set pages <switch>

    Parameters:
      format: A string determining the new pagination setting. Optional. Can be one of these values: [on, true, yes, 1, off, false, no, 0]

    Notes:
      If the parameter <switch> is being omitted, the command will toggle between 'ON' and 'OFF' depending on the current setting.

    Examples:
      /settings set pagination - Toggles the pagination setting for the current Discord server/guild depending on the current setting.
      /settings set pagination off - Turns off pagination for the current Discord server/guild.
    """
    __log_command_use(ctx)
    await __assert_settings_command_valid(ctx)

    async with ctx.typing():
        guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
        success = await guild_settings.set_use_pagination(switch)
    if success:
        await ctx.invoke(bot.get_command('settings pagination'))
    else:
        output = [f'Could not set pagination settings for this server. Please try again or contact the bot\'s author.']
        await util.post_output(ctx, output)


@cmd_settings_set.command(brief='Set prefix', name='prefix')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_prefix(ctx: commands.Context, prefix: str):
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
        guild_settings = await GUILD_SETTINGS.get(bot, ctx.guild.id)
        success = await guild_settings.set_prefix(prefix)
    if success:
        await ctx.invoke(bot.get_command('settings prefix'))
    else:
        output = [f'Could not set prefix for this server. Please try again or contact the bot\'s author.']
        await util.post_output(ctx, output)










@bot.group(name='past', brief='Get historic data', aliases=['history'], invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_past(ctx: commands.Context, month: str = None, year: str = None):
    """
    Get historic tournament data.

    Parameters:
    - month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
    - year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.

    You need to use one of the subcommands.
    """
    __log_command_use(ctx)
    await ctx.send_help('past')


@cmd_past.group(name='stars', brief='Get historic division stars', invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_past_stars(ctx: commands.Context, month: str = None, year: str = None, *, division: str = None):
    """
    Get historic tournament division stars data.

    Parameters:
    - month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
    - year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
    - division: Optional. The division for which the data should be displayed. If not specified will print all divisions.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        error = None
        utc_now = util.get_utcnow()
        output = []

        (month, year, division) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise pss_exception.Error('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        else:
            if not pss_top.is_valid_division_letter(division):
                subcommand = bot.get_command('past stars fleet')
                await ctx.invoke(subcommand, month=month, year=year, fleet_name=division)
            else:
                month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
                try:
                    tourney_data = tourney_data_client.get_data(year, month)
                except ValueError as err:
                    error = str(err)
                    tourney_data = None
                if tourney_data:
                    output, _ = await pss_top.get_division_stars(division=division, fleet_data=tourney_data.fleets, retrieved_date=tourney_data.retrieved_at)
                elif error:
                    output = [error]
    await util.post_output(ctx, output)


@cmd_past_stars.command(name='fleet', brief='Get historic fleet stars', aliases=['alliance'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_past_stars_fleet(ctx: commands.Context, month: str, year: str = None, *, fleet_name: str = None):
    """
    Get historic tournament fleet stars data.

    Parameters:
    - month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
    - year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
    - fleet_name: Mandatory. The fleet for which the data should be displayed.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = []
        error = None
        utc_now = util.get_utcnow()
        (month, year, fleet_name) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise pss_exception.Error('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        else:
            month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
            try:
                tourney_data = tourney_data_client.get_data(year, month)
            except ValueError as err:
                error = str(err)
                tourney_data = None

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
                output = fleet.get_fleet_users_stars_from_tournament_data(fleet_info, tourney_data.fleets, tourney_data.users, tourney_data.retrieved_at)
    elif error:
        output = [str(error)]
    else:
        output = [f'Could not find a fleet named `{fleet_name}` that participated in the {year} {calendar.month_name[int(month)]} tournament.']
    await util.post_output(ctx, output)


@cmd_past.command(name='fleet', brief='Get historic fleet data', aliases=['alliance'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_past_fleet(ctx: commands.Context, month: str, year: str = None, *, fleet_name: str = None):
    """
    Get historic tournament fleet data.

    Parameters:
    - month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
    - year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
    - fleet_name: Mandatory. The fleet for which the data should be displayed.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = []
        error = None
        utc_now = util.get_utcnow()
        (month, year, fleet_name) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise pss_exception.Error('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        else:
            month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
            try:
                tourney_data = tourney_data_client.get_data(year, month)
            except ValueError as err:
                error = str(err)
                tourney_data = None

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
                output, file_paths = await fleet.get_full_fleet_info_as_text(fleet_info, past_fleets_data=tourney_data.fleets, past_users_data=tourney_data.users, past_retrieved_at=tourney_data.retrieved_at)
            await util.post_output_with_files(ctx, output, file_paths)
            for file_path in file_paths:
                os.remove(file_path)
            return
    elif error:
        output = [str(error)]
    else:
        output = [f'Could not find a fleet named `{fleet_name}` that participated in the {year} {calendar.month_name[int(month)]} tournament.']
    await util.post_output(ctx, output)


@cmd_past.command(name='player', brief='Get historic player data', aliases=['user'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_past_player(ctx: commands.Context, month: str, year: str = None, *, player_name: str = None):
    """
    Get historic tournament player data.

    Parameters:
    - month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
    - year: Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
    - player_name: Mandatory. The player for which the data should be displayed.

    If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        output = []
        error = None
        utc_now = util.get_utcnow()
        (month, year, player_name) = TourneyDataClient.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise pss_exception.Error('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        else:
            month, year = TourneyDataClient.retrieve_past_month_year(month, year, utc_now)
            try:
                tourney_data = tourney_data_client.get_data(year, month)
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
                output = await user.get_user_details_by_info(user_info, tourney_data.retrieved_at, tourney_data.fleets)
    elif error:
        output = [str(error)]
    else:
        output = [f'Could not find a player named `{player_name}` that participated in the {year} {calendar.month_name[int(month)]} tournament.']
    await util.post_output(ctx, output)










@bot.group(name='raw', brief='Get raw data from the PSS API', invoke_without_command=True, hidden=True)
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw(ctx: commands.Context):
    """
    Get raw data from the Pixel Starships API.
    Use one of the sub-commands to retrieve data for a certain entity type. The sub-commands may have sub-commands on their own, so make sure to check the related help commands.

    Usage:
      /raw [subcommand] <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
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


@cmd_raw.command(name='achievement', brief='Get raw achievement data', aliases=['achievements'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_achievement(ctx: commands.Context, *, achievement_id: str = None):
    """
    Get raw achievement design data from the PSS API.

    Usage:
      /raw achievement <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the achievement with the specified id.
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
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_ai(ctx: commands.Context):
    """
    Get raw ai design data from the PSS API.

    Usage:
      /raw ai [subcommand] <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
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


@cmd_raw_ai.command(name='action', brief='Get raw ai action data', aliases=['actions'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_ai_action(ctx: commands.Context, ai_action_id: int = None):
    """
    Get raw ai action design data from the PSS API.

    Usage:
      /raw ai action <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the ai action with the specified id.
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


@cmd_raw_ai.command(name='condition', brief='Get raw ai condition data', aliases=['conditions'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_ai_condition(ctx: commands.Context, ai_condition_id: int = None):
    """
    Get raw ai condition design data from the PSS API.

    Usage:
      /raw ai condition <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the ai condition with the specified id.
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


@cmd_raw.command(name='char', brief='Get raw crew data', aliases=['crew', 'chars', 'crews'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_char(ctx: commands.Context, *, char_id: str = None):
    """
    Get raw character design data from the PSS API.

    Usage:
      /raw char <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the character with the specified id.
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


@cmd_raw.command(name='collection', brief='Get raw collection data', aliases=['coll', 'collections'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_collection(ctx: commands.Context, *, collection_id: str = None):
    """
    Get raw collection design data from the PSS API.

    Usage:
      /raw collection <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the collection with the specified id.
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


@cmd_raw.group(name='gm', brief='Get raw gm data', aliases=['galaxymap', 'galaxy'], invoke_without_command=True)
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_gm(ctx: commands.Context):
    """
    Get raw gm design data from the PSS API.

    Usage:
      /raw gm [subcommand] <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
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


@cmd_raw_gm.command(name='system', brief='Get raw gm system data', aliases=['systems', 'star', 'stars'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_gm_system(ctx: commands.Context, *, star_system_id: str = None):
    """
    Get raw star system design data from the PSS API.

    Usage:
      /raw gm system <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the GM system with the specified id.
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


@cmd_raw_gm.command(name='path', brief='Get raw gm path data', aliases=['paths', 'link', 'links'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_gm_link(ctx: commands.Context, *, star_system_link_id: str = None):
    """
    Get raw star system link design data from the PSS API.

    Usage:
      /raw gm path <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the GM path with the specified id.
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


@cmd_raw.command(name='item', brief='Get raw item data', aliases=['items'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_item(ctx: commands.Context, *, item_id: str = None):
    """
    Get raw item design data from the PSS API.

    Usage:
      /raw item <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the item with the specified id.
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


@cmd_raw.command(name='mission', brief='Get raw mission data', aliases=['missions'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_mission(ctx: commands.Context, *, mission_id: str = None):
    """
    Get raw mission design data from the PSS API.

    Usage:
      /raw mission <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the mission with the specified id.
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


@cmd_raw.command(name='promotion', brief='Get raw promotion data', aliases=['promo', 'promotions', 'promos'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_promotion(ctx: commands.Context, *, promo_id: str = None):
    """
    Get raw promotion design data from the PSS API.

    Usage:
      /raw promotion <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the promotion with the specified id.
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


@cmd_raw.command(name='research', brief='Get raw research data', aliases=['researches'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_research(ctx: commands.Context, *, research_id: str = None):
    """
    Get raw research design data from the PSS API.

    Usage:
      /raw research <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the research with the specified id.
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


@cmd_raw.group(name='room', brief='Get raw room data', aliases=['rooms'], invoke_without_command=True)
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_room(ctx: commands.Context, *, room_id: str = None):
    """
    Get raw room design data from the PSS API.

    Usage:
      /raw room <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the room with the specified id.
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


@cmd_raw_room.command(name='purchase', brief='Get raw room purchase data', aliases=['purchases'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_room_purchase(ctx: commands.Context, *, room_purchase_id: str = None):
    """
    Get raw room purchase design data from the PSS API.

    Usage:
      /raw room purchase <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the room purchase with the specified id.
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


@cmd_raw.command(name='ship', brief='Get raw ship data', aliases=['ships', 'hull', 'hulls'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_ship(ctx: commands.Context, *, ship_id: str = None):
    """
    Get raw ship design data from the PSS API.

    Usage:
      /raw ship <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the ship hull with the specified id.
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


@cmd_raw.command(name='training', brief='Get raw training data', aliases=['trainings'])
@commands.cooldown(rate=RAW_RATE, per=RAW_COOLDOWN, type=commands.BucketType.user)
async def cmd_raw_training(ctx: commands.Context, *, training_id: str = None):
    """
    Get raw training design data from the PSS API.

    Usage:
      /raw training <id> <format>

    Parameters:
      id:     An integer. If specified, the command will only return the raw data for the training with the specified id.
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











# ---------- Owner commands ----------


@bot.group(brief='Configure auto-daily for the server', name='autodaily', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_autodaily(ctx: commands.Context):
    """
    This command can be used to get an overview of the autodaily settings for this bot.

    In order to use this command or any sub commands, you need to be the owner of this bot.
    """
    __log_command_use(ctx)
    pass


@cmd_autodaily.group(brief='List configured auto-daily channels', name='list', invoke_without_command=False)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_autodaily_list(ctx: commands.Context):
    __log_command_use(ctx)
    pass


@cmd_autodaily_list.command(brief='List all configured auto-daily channels', name='all')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_autodaily_list_all(ctx: commands.Context):
    __log_command_use(ctx)
    async with ctx.typing():
        output = await daily.get_daily_channels(ctx, None, None)
    await util.post_output(ctx, output)


@cmd_autodaily_list.command(brief='List all invalid configured auto-daily channels', name='invalid')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_autodaily_list_invalid(ctx: commands.Context):
    __log_command_use(ctx)
    async with ctx.typing():
        output = await daily.get_daily_channels(ctx, None, False)
    await util.post_output(ctx, output)


@cmd_autodaily_list.command(brief='List all valid configured auto-daily channels', name='valid')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_autodaily_list_valid(ctx: commands.Context):
    __log_command_use(ctx)
    async with ctx.typing():
        output = await daily.get_daily_channels(ctx, None, True)
    await util.post_output(ctx, output)


@cmd_autodaily.command(brief='Post a daily message on this server\'s auto-daily channel', name='post')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_autodaily_post(ctx: commands.Context):
    __log_command_use(ctx)
    guild = ctx.guild
    channel_id = await server_settings.db_get_daily_channel_id(guild.id)
    if channel_id is not None:
        text_channel = bot.get_channel(channel_id)
        output, _ = await dropship.get_dropship_text()
        await util.post_output_to_channel(text_channel, output)

@bot.command(brief='These are testing commands, usually for debugging purposes', name='test', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_test(ctx: commands.Context, action, *, params = None):
    print(f'+ called command test(ctx: commands.Context, {action}, {params}) by {ctx.author}')
    if action == 'utcnow':
        utcnow = util.get_utcnow()
        txt = util.get_formatted_datetime(utcnow)
        await ctx.send(txt)
    elif action == 'init':
        await db.init_schema()
        await ctx.send('Initialized the database from scratch')
        await util.try_delete_original_message(ctx)
    elif action == 'commands':
        output = [', '.join(sorted(bot.all_commands.keys()))]
        await util.post_output(ctx, output)
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
        await util.post_output(ctx, output)


@bot.group(brief='DB commands', name='db', hidden=True, invoke_without_command=True)
@commands.is_owner()
async def cmd_db(ctx: commands.Context):
    await ctx.send_help('db')


@cmd_db.command(brief='Try to execute a DB query', name='query', hidden=True)
@commands.is_owner()
async def cmd_db_query(ctx: commands.Context, *, query: str):
    async with ctx.typing():
        success = await db.try_execute(query)
    if not success:
        await ctx.send(f'The query \'{query}\' failed.')
    else:
        await ctx.send(f'The query \'{query}\' has been executed successfully.')


@cmd_db.command(brief='Try to select from DB', name='select', hidden=True)
@commands.is_owner()
async def cmd_db_select(ctx: commands.Context, *, query: str):
    async with ctx.typing():
        if not query.lower().startswith('select '):
            query = f'SELECT {query}'
        try:
            result = await db.fetchall(query)
            error = None
        except Exception as error:
            result = []
    if error:
        await ctx.send(f'The query \'{query}\' failed.')
    elif result:
        await ctx.send(f'The query \'{query}\' has been executed successfully.')
        result = [str(record) for record in result]
        await util.post_output(ctx, result)
    else:
        await ctx.send(f'The query \'{query}\' didn\'t return any results.')



@bot.command(brief='Send bot news to all servers.', name='sendnews', aliases=['botnews'], hidden=True)
@commands.is_owner()
async def cmd_send_bot_news(ctx: commands.Context, *, news: str = None):
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
        split_news = news.split('--')
        news_parts = {key: value.strip() for key, value in [part.split('=', maxsplit=1) for part in split_news if '=' in part]}
        if 'title' not in news_parts:
            raise ValueError('You need to specify a title!')
        avatar_url = bot.user.avatar_url
        for bot_news_channel in server_settings.GUILD_SETTINGS.bot_news_channels:
            embed_colour = util.get_bot_member_colour(bot, bot_news_channel.guild)
            embed: discord.Embed = util.create_embed(news_parts['title'], description=news_parts.get('content'), colour=embed_colour)
            embed.set_thumbnail(url=avatar_url)
            await bot_news_channel.send(embed=embed)
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = util.create_embed(news_parts['title'], description=news_parts.get('content'), colour=embed_colour)
        embed.set_thumbnail(url=avatar_url)
    await ctx.send(embed=embed)


@bot.group(brief='list available devices', name='device', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_device(ctx: commands.Context):
    """
    Returns all known devices stored in the DB.
    """
    __log_command_use(ctx)
    if ctx.invoked_subcommand is None:
        async with ctx.typing():
            output = []
            for device in login.DEVICES.devices:
                output.append(settings.EMPTY_LINE)
                if device.can_login_until:
                    login_until = util.get_formatted_datetime(device.can_login_until)
                else:
                    login_until = '-'
                output.append(f'Key: {device.key}\nChecksum: {device.checksum}\nCan login until: {login_until}')
            output = output[1:]
            posts = util.create_posts_from_lines(output, settings.MAXIMUM_CHARACTERS)
        for post in posts:
            await ctx.send(post)


@cmd_device.command(brief='create & store random device', name='create')
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_device_create(ctx: commands.Context):
    """
    Creates a new random device_key and attempts to store the new device in the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        device = await login.DEVICES.create_device()
        try:
            await device.get_access_token()
            created = True
        except Exception as err:
            await login.DEVICES.remove_device(device)
            created = False
    if created is True:
        await ctx.send(f'Created and stored device with key \'{device.key}\'.')
    else:
        await ctx.send(f'Failed to create and store device:```{err}```')


@cmd_device.command(brief='store device', name='add')
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_device_add(ctx: commands.Context, device_key: str):
    """
    Attempts to store a device with the given device_key in the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        try:
            device = await login.DEVICES.add_device_by_key(device_key)
            added = True
        except Exception as err:
            added = False
    if added:
        await ctx.send(f'Added device with device key \'{device.key}\'.')
    else:
        await ctx.send(f'Could not add device with device key\'{device_key}\':```{err}```')


@cmd_device.command(brief='remove device', name='remove', aliases=['delete', 'yeet'])
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_device_remove(ctx: commands.Context, device_key: str):
    """
    Attempts to remove a device with the given device_key from the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        try:
            await login.DEVICES.remove_device_by_key(device_key)
            yeeted = True
        except Exception as err:
            yeeted = False
    if yeeted:
        await ctx.send(f'Removed device with device key: \'{device_key}\'.')
    else:
        await ctx.send(f'Could not remove device with device key \'{device_key}\':```{err}```')


@cmd_device.command(brief='login to a device', name='login')
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_device_login(ctx: commands.Context):
    """
    Attempts to remove a device with the given device_key from the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        try:
            access_token = await login.DEVICES.get_access_token()
            device = login.DEVICES.current
        except Exception as err:
            access_token = None
    if access_token is not None:
        await ctx.send(f'Logged in with device \'{device.key}\'.\nObtained access token: {access_token}')
    else:
        await ctx.send(f'Could not log in with device \'{device.key}\':```{err}``')


@cmd_device.command(brief='select a device', name='select')
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_device_select(ctx: commands.Context, device_key: str):
    """
    Attempts to select a device with the given device_key from the DB.
    """
    __log_command_use(ctx)
    async with ctx.typing():
        device = login.DEVICES.select_device(device_key)
    await ctx.send(f'Selected device \'{device.key}\'.')










# ---------- Command Helper Functions ----------





def __log_command_use(ctx: commands.Context):
    if settings.PRINT_DEBUG_COMMAND:
        print(f'Invoked command: {ctx.message.content}')


def __log_command_use_error(ctx: commands.Context, err: Exception):
    if settings.PRINT_DEBUG_COMMAND:
        print(f'Invoked command had an error: {ctx.message.content}')
        if err:
            print(str(err))


async def __assert_settings_command_valid(ctx: commands.Context) -> None:
    if util.is_guild_channel(ctx.channel):
        permissions = ctx.channel.permissions_for(ctx.author)
        if getattr(permissions, 'manage_guild') is not True:
            raise commands.MissingPermissions(['manage_guild'])
    else:
        raise Exception('This command cannot be used in DMs or group chats, but only in Discord servers/guilds!')












# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    print(f'discord.py version: {discord.__version__}')
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
