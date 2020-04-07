from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import asyncio
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
from threading import Lock
from typing import Dict, List, Tuple, Union

import emojis
import gdrive
import pagination
import server_settings
import settings
import utility as util

import pss_assert
import pss_core as core
import pss_crew as crew
import pss_daily as daily
import pss_dropship as dropship
import pss_exception
import pss_fleet as fleet
import pss_item as item
import pss_login as login
import pss_lookups as lookups
import pss_research as research
import pss_room as room
import pss_tournament as tourney
import pss_top
import pss_training as training
import pss_user as user



# ----- Setup ---------------------------------------------------------
RATE = 5
COOLDOWN = 15.0

if 'COMMAND_PREFIX' in os.environ:
    COMMAND_PREFIX=os.getenv('COMMAND_PREFIX')
else:
    COMMAND_PREFIX=server_settings.get_prefix

PWD = os.getcwd()
sys.path.insert(0, PWD + '/src/')

ACTIVITY = discord.Activity(type=discord.ActivityType.playing, name='/help')

tournament_data = gdrive.TourneyData(
    settings.GDRIVE_PROJECT_ID,
    settings.GDRIVE_PRIVATE_KEY_ID,
    settings.GDRIVE_PRIVATE_KEY,
    settings.GDRIVE_CLIENT_EMAIL,
    settings.GDRIVE_CLIENT_ID,
    settings.GDRIVE_SCOPES,
    settings.GDRIVE_FOLDER_ID,
    settings.GDRIVE_SERVICE_ACCOUNT_FILE,
    settings.GDRIVE_SETTINGS_FILE
)

__COMMANDS = []









# ----- Bot Setup -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    style = '{',
    datefmt = '%Y%m%d %H:%M:%S',
    format = '{asctime} [{levelname:<8}] {name}: {message}')

bot = discord.ext.commands.Bot(command_prefix=COMMAND_PREFIX,
                               description='This is a Discord Bot for Pixel Starships',
                               activity=ACTIVITY)

setattr(bot, 'logger', logging.getLogger('bot.py'))









# ----- Bot Events ------------------------------------------------------------
@bot.event
async def on_ready() -> None:
    print(f'sys.argv: {sys.argv}')
    print(f'Current Working Directory: {PWD}')
    print(f'Bot version is: {settings.VERSION}')
    print(f'DB schema version is: {core.db_get_schema_version()}')
    print(f'Bot logged in as {bot.user.name} (id={bot.user.id}) on {len(bot.guilds)} servers')
    global __COMMANDS
    __COMMANDS = sorted([key for key, value in bot.all_commands.items() if value.hidden == False])
    #bot.loop.create_task(post_dailies_loop())


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
async def on_command_error(ctx: discord.ext.commands.Context, err) -> None:
    if isinstance(err, discord.ext.commands.CommandOnCooldown):
        await ctx.send('Error: {}'.format(err))
    elif isinstance(err, discord.ext.commands.CommandNotFound):
        prefix = COMMAND_PREFIX(bot, ctx.message)
        invoked_with = ctx.invoked_with.split(' ')[0]
        commands_map = util.get_similarity_map(__COMMANDS, invoked_with)
        commands = [f'`{prefix}{command}`' for command in sorted(commands_map[max(commands_map.keys())])]
        await ctx.send(f'Error: Command `{prefix}{invoked_with}` not found. Do you mean {util.get_or_list(commands)}?')
    elif isinstance(err, discord.ext.commands.CheckFailure):
        await ctx.send(f'Error: You don\'t have the required permissions in order to be able to use this command!')
    elif isinstance(err, pss_exception.Error):
        await ctx.send(f'`{ctx.message.clean_content}`: {err.msg}')
    else:
        logging.getLogger().error(err, exc_info=True)
        command_args = util.get_exact_args(ctx)
        help_args = ctx.message.clean_content.replace(command_args, '').strip()[1:]
        command = bot.get_command(help_args)
        await ctx.send_help(command)
        await ctx.send(f'Error: {err}')


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    success = server_settings.db_create_server_settings(guild.id)
    if not success:
        print(f'[on_guild_join] Could not create server settings for guild \'{guild.name}\' (ID: \'{guild.id}\')')


@bot.event
async def on_guild_remove(guild: discord.Guild) -> None:
    success = server_settings.db_delete_server_settings(guild.id)
    if not success:
        print(f'[on_guild_join] Could not delete server settings for guild \'{guild.name}\' (ID: \'{guild.id}\')')










# ----- Tasks ----------------------------------------------------------
async def post_dailies_loop() -> None:
    utc_now = util.get_utcnow()
    while utc_now < settings.POST_AUTODAILY_FROM:
        wait_for = util.get_seconds_to_wait(60, utc_now=utc_now)
        await asyncio.sleep(wait_for)
        utc_now = util.get_utcnow()

    while True:
        utc_now = util.get_utcnow()
        yesterday = datetime.datetime(utc_now.year, utc_now.month, utc_now.day) - settings.ONE_SECOND

        daily_info = daily.get_daily_info()
        db_daily_info, db_daily_modify_date = daily.db_get_daily_info()
        has_daily_changed = daily.has_daily_changed(daily_info, utc_now, db_daily_info, db_daily_modify_date)

        autodaily_settings = server_settings.get_autodaily_settings(bot, no_post_yet=True)
        if autodaily_settings:
            print(f'[post_dailies_loop] retrieved {len(autodaily_settings)} channels')
        if has_daily_changed:
            print(f'[post_dailies_loop] daily info changed:\n{json.dumps(daily_info)}')
            post_here = server_settings.get_autodaily_settings(bot)
            print(f'[post_dailies_loop] retrieved {len(post_here)} guilds to post')
            autodaily_settings.extend(post_here)

        created_output = False
        posted_count = 0
        if autodaily_settings:
            autodaily_settings = daily.remove_duplicate_autodaily_settings(autodaily_settings)
            print(f'[post_dailies_loop] going to post to {len(autodaily_settings)} guilds')

            latest_message_output, _ = dropship.get_dropship_text(daily_info=db_daily_info)
            latest_daily_message = '\n'.join(latest_message_output)
            output, created_output = dropship.get_dropship_text(daily_info=daily_info)
            if created_output:
                current_daily_message = '\n'.join(output)
                posted_count = await post_dailies(current_daily_message, autodaily_settings, utc_now, yesterday, latest_daily_message)
            print(f'[post_dailies_loop] posted to {posted_count} of {len(autodaily_settings)} guilds')

        if has_daily_changed:
            seconds_to_wait = 300.0
            if created_output:
                daily.db_set_daily_info(daily_info, utc_now)
        else:
            seconds_to_wait = util.get_seconds_to_wait(1)
        await asyncio.sleep(seconds_to_wait)


async def post_dailies(current_daily_message: str, autodaily_settings: List[server_settings.AutoDailySettings], utc_now: datetime.datetime, yesterday: datetime.datetime, latest_daily_message_contents: str) -> int:
    posted_count = 0
    for settings in autodaily_settings:
        if settings.guild.id is not None and settings.channel_id is not None:
            posted, can_post, latest_message_id = await post_autodaily(settings.channel, settings.latest_message_id, settings.delete_on_change, current_daily_message, utc_now, yesterday, latest_daily_message_contents)
            if posted:
                posted_count += 1
                await notify_on_autodaily(settings.guild, settings.notify, settings.notify_type)
            server_settings.db_update_autodaily_settings(settings.guild.id, can_post=can_post, latest_message_id=latest_message_id, latest_message_modify_date=utc_now)
    return posted_count


async def post_autodaily(text_channel: discord.TextChannel, latest_message_id: int, delete_on_change: bool, current_daily_message: str, utc_now: datetime.datetime, yesterday: datetime.datetime, latest_daily_message_contents: str) -> (bool, bool, str):
    """
    Returns (posted, can_post, latest_message_id)
    """
    posted = False
    if text_channel and current_daily_message:
        error_msg_delete = f'could not delete message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_edit = f'could not edit message [{latest_message_id}] from channel [{text_channel.id}] on guild [{text_channel.guild.id}]'
        error_msg_post = f'could not post a message in channel [{text_channel.id}] on guild [{text_channel.guild.id}]'

        if delete_on_change is None or delete_on_change is True:
            post_new = True
        else:
            post_new = False

        can_post = True
        latest_message: discord.Message = None

        if can_post:
            can_post, latest_message = await daily_fetch_latest_message(text_channel, latest_message_id, yesterday, latest_daily_message_contents, current_daily_message)

        if can_post:
            if latest_message and latest_message.created_at.day == utc_now.day:
                latest_message_id = latest_message.id
                if latest_message.content == current_daily_message:
                    post_new = False
                elif delete_on_change is True:
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
                elif delete_on_change is False:
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
            return posted, can_post, latest_message.id
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











# ----- General Bot Commands ----------------------------------------------------------
@bot.command(brief='Ping the server', name='ping')
async def cmd_ping(ctx: discord.ext.commands.Context):
    """
    Ping the bot to verify that it\'s listening for commands.

    Usage:
      /ping

    Examples:
      /ping - The bot will answer with 'Pong!'.
    """
    await ctx.send('Pong!')










# ---------- PSS Bot Commands ----------

@bot.command(brief='Get prestige combos of crew', name='prestige')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_prestige(ctx: discord.ext.commands.Context, *, crew_name: str):
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
    async with ctx.typing():
        output, _ = crew.get_prestige_from_info(crew_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get character recipes', name='recipe')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_recipe(ctx: discord.ext.commands.Context, *, crew_name: str):
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
    async with ctx.typing():
        output, _ = crew.get_prestige_to_info(crew_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item ingredients', name='ingredients', aliases=['ing'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_ingredients(ctx: discord.ext.commands.Context, *, item_name: str):
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
    async with ctx.typing():
        output, _ = item.get_ingredients_for_item(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get crafting recipes', name='craft', aliases=['upg', 'upgrade'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_craft(ctx: discord.ext.commands.Context, *, item_name: str):
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
    async with ctx.typing():
        output, _ = item.get_item_upgrades_from_name(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item\'s market prices and fair prices from the PSS API', name='price', aliases=['fairprice', 'cost'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_price(ctx: discord.ext.commands.Context, *, item_name: str):
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
    async with ctx.typing():
        output, _ = item.get_item_price(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item/crew stats', name='stats', aliases=['stat'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_stats(ctx: discord.ext.commands.Context, level: str = None, *, name: str = None):
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
    async with ctx.typing():
        full_name = f'{level} {name}'
        level, name = util.get_level_and_name(level, name)
        try:
            char_output, char_success = crew.get_char_design_details_by_name(name, level)
        except pss_exception.InvalidParameter:
            char_output = None
            char_success = False
        try:
            item_output, item_success = item.get_item_details_by_name(name)
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


@bot.command(brief='Get character stats', name='char', aliases=['crew'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_char(ctx: discord.ext.commands.Context, level: str = None, *, crew_name: str = None):
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
    async with ctx.typing():
        level, crew_name = util.get_level_and_name(level, crew_name)
        output, _ = crew.get_char_design_details_by_name(crew_name, level=level)
    await util.post_output(ctx, output)


@bot.command(brief='Get item stats', name='item')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_item(ctx: discord.ext.commands.Context, *, item_name: str):
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
    async with ctx.typing():
        output, _ = item.get_item_details_by_name(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get best items for a slot', name='best')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_best(ctx: discord.ext.commands.Context, slot: str, stat: str):
    """
    Get the best enhancement item for a given slot. If multiple matches are found, matches will be shown in descending order according to their bonus.

    Usage:
      /best [slot] [stat]

    Parameters:
      slot: the equipment slot. Use 'all' or 'any' to get info for all slots. Mandatory. Valid values are: [all/any (for all slots), head, hat, helm, helmet, body, shirt, armor, leg, pant, pants, weapon, hand, gun, accessory, shoulder, pet]
      stat: the crew stat you're looking for. Mandatory. Valid values are: [hp, health, attack, atk, att, damage, dmg, repair, rep, ability, abl, pilot, plt, science, sci, stamina, stam, stm, engine, eng, weapon, wpn, fire resistance, fire]

    Examples:
      /best hand atk - Prints all equipment items for the weapon slot providing an attack bonus.
      /best all hp - Prints all equipment items for all slots providing a HP bonus.
    """
    async with ctx.typing():
        output, _ = item.get_best_items(slot, stat)
    await util.post_output(ctx, output)


@bot.command(brief='Get research data', name='research')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_research(ctx: discord.ext.commands.Context, *, research_name: str):
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
    async with ctx.typing():
        output, _ = research.get_research_infos_by_name(research_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get collections', name='collection', aliases=['coll'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_collection(ctx: discord.ext.commands.Context, *, collection_name: str):
    """
    Get the details on a specific collection.

    Usage:
      /collection [collection_name]

    Parameters:
      collection_name: The name of the collection to get details on.

    Examples:
      /collection_name savy - Will print information on a collection having 'savy' in its name.

    Notes:
      This command will only print stats for the collection with the best matching collection_name.
    """
    async with ctx.typing():
        output, _ = crew.get_collection_design_details_by_name(collection_name)
    await util.post_output(ctx, output)


@bot.group(brief='Division stars', name='stars', invoke_without_command=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_stars(ctx: discord.ext.commands.Context, *, division: str = None):
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
    if ctx.invoked_subcommand is None:
        called_subcommand = False
        subcommands = ['fleet']
        for subcommand in subcommands:
            subcommand_length = len(subcommand)
            if division == subcommand:
                called_subcommand = True
                cmd = bot.get_command(f'stars {subcommand}')
                await ctx.invoke(cmd)
            elif division and division.startswith(f'{subcommand} '):
                called_subcommand = True
                cmd = bot.get_command(f'stars {subcommand}')
                args = str(division[subcommand_length:]).strip()
                await ctx.invoke(cmd, fleet_name=args)

        if not called_subcommand:
            if tourney.is_tourney_running():
                async with ctx.typing():
                    output, _ = pss_top.get_division_stars(division=division)
            else:
                async with ctx.typing():
                    (fleet_data, _, data_date) = tournament_data.get_data()
                    output, _ = pss_top.get_division_stars(division=division, fleet_data=fleet_data, retrieved_date=data_date)
            await util.post_output(ctx, output)


@cmd_stars.command(brief='Fleet stars', name='fleet', aliases=['alliance'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_stars_fleet(ctx: discord.ext.commands.Context, *, fleet_name: str):
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
    async with ctx.typing():
        exact_name = util.get_exact_args(ctx)
        if exact_name:
            fleet_name = exact_name
        is_tourney_running = tourney.is_tourney_running()
        (fleet_data, user_data, data_date) = tournament_data.get_data()
        fleet_infos = fleet.get_fleet_details_by_name(fleet_name)
        if is_tourney_running:
            fleet_infos = [fleet_info for fleet_info in fleet_infos if fleet_info['DivisionDesignId'] != '0']
        else:
            fleet_infos = [fleet_info for fleet_info in fleet_infos if fleet_info[fleet.FLEET_KEY_NAME] in fleet_data.keys()]

    if fleet_infos:
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details)
            _, fleet_info = await paginator.wait_for_option_selection()

        if fleet_info:
            async with ctx.typing():
                if is_tourney_running:
                    fleet_users_infos = fleet.get_fleet_users_by_info(fleet_info)
                    output = fleet.get_fleet_users_stars_from_info(fleet_info, fleet_users_infos)
                else:
                    output = fleet.get_fleet_users_stars_from_tournament_data(fleet_info, fleet_data, user_data, data_date)
            await util.post_output(ctx, output)
    else:
        if is_tourney_running:
            await ctx.send(f'Could not find a fleet named `{fleet_name}` participating in the current tournament.')
        else:
            await ctx.send(f'Could not find a fleet named `{fleet_name}` that participated in the last tournament.')


@bot.command(brief='Show the dailies', name='daily')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN*2, type=discord.ext.commands.BucketType.user)
async def cmd_daily(ctx: discord.ext.commands.Context):
    """
    Prints the MOTD along today's contents of the dropship, the merchant ship, the shop and the sale.

    Usage:
      /daily

    Examples:
      /daily - Prints the information described above.
    """
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = dropship.get_dropship_text()
    await util.post_output(ctx, output)


@bot.command(brief='Show the news', name='news')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_news(ctx: discord.ext.commands.Context):
    """
    Prints all news in ascending order.

    Usage:
      /news

    Examples:
      /news - Prints the information described above.
    """
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = dropship.get_news()
    await util.post_output(ctx, output)


@bot.group(brief='Configure auto-daily for the server', name='autodaily', hidden=True)
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
@discord.ext.commands.has_permissions(manage_guild=True)
async def cmd_autodaily(ctx: discord.ext.commands.Context):
    """
    This command can be used to configure the bot to automatically post the daily announcement at 1 am UTC to a certain text channel.
    The daily announcement is the message that this bot will post, when you use the /daily command.

    In order to use this command, you need the Administrator permission for the current Discord server/guild.
    """
    pass


@cmd_autodaily.group(brief='List configured auto-daily channels', name='list', invoke_without_command=False)
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
@discord.ext.commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list(ctx: discord.ext.commands.Context):
    pass


@cmd_autodaily_list.command(brief='List all configured auto-daily channels', name='all')
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
@discord.ext.commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list_all(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, None)
    await util.post_output(ctx, output)


@cmd_autodaily_list.command(brief='List all invalid configured auto-daily channels', name='invalid')
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
@discord.ext.commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list_invalid(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, False)
    await util.post_output(ctx, output)


@cmd_autodaily_list.command(brief='List all valid configured auto-daily channels', name='valid')
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
@discord.ext.commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list_valid(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, True)
    await util.post_output(ctx, output)


@cmd_autodaily.command(brief='Post a daily message on this server\'s auto-daily channel', name='post')
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
@discord.ext.commands.has_permissions(manage_guild=True)
async def cmd_autodaily_post(ctx: discord.ext.commands.Context):
    guild = ctx.guild
    channel_id = server_settings.db_get_daily_channel_id(guild.id)
    if channel_id is not None:
        text_channel = bot.get_channel(channel_id)
        output, _ = dropship.get_dropship_text()
        await util.post_output_to_channel(text_channel, output)


@bot.command(brief='Get crew levelling costs', name='level', aliases=['lvl'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_level(ctx: discord.ext.commands.Context, from_level: int, to_level: int = None):
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
    async with ctx.typing():
        output, _ = crew.get_level_costs(from_level, to_level)
    await util.post_output(ctx, output)


@bot.group(brief='Prints top fleets or captains', name='top', invoke_without_command=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_top(ctx: discord.ext.commands.Context, count: int = 100):
    """
    Prints either top fleets or captains. Prints top 100 fleets by default.

    Usage:
      /top <count>

    Parameters:
      count: The number of rows to be printed. Optional.

    Examples:
      /top - prints top 100 fleets.
      /top 30 - prints top 30 fleets."""
    if ctx.invoked_subcommand is None:
        cmd = bot.get_command(f'top fleets')
        await ctx.invoke(cmd, count=count)


@cmd_top.command(brief='Prints top fleets', name='fleets', aliases=['alliances'])
async def cmd_top_fleets(ctx: discord.ext.commands.Context, count: int = 100):
    """
    Prints top fleets. Prints top 100 fleets by default.

    Usage:
      /top fleets <count>

    Parameters:
      count: The number of rows to be printed. Optional.

    Examples:
      /top fleets - prints top 100 fleets.
      /top fleets 30 - prints top 30 fleets."""
    async with ctx.typing():
        output, _ = pss_top.get_top_fleets(count)
    await util.post_output(ctx, output)


@cmd_top.command(brief='Prints top captains', name='players', aliases=['captains', 'users'])
async def cmd_top_captains(ctx: discord.ext.commands.Context, count: int = 100):
    """
    Prints top captains. Prints top 100 captains by default.

    Usage:
      /top captains <count>

    Parameters:
      count: The number of rows to be printed. Optional.

    Examples:
      /top captains - prints top 100 captains.
      /top captains 30 - prints top 30 captains."""
    async with ctx.typing():
        output, _ = pss_top.get_top_captains(count)
    await util.post_output(ctx, output)


@bot.command(brief='Get room infos', name='room')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_room(ctx: discord.ext.commands.Context, *, name: str = None):
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
    async with ctx.typing():
        output, _ = room.get_room_details_from_name(name)
    await util.post_output(ctx, output)


@bot.command(brief='Get training infos', name='training')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_training(ctx: discord.ext.commands.Context, *, name: str = None):
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
    async with ctx.typing():
        output, _ = training.get_training_details_from_name(name)
    await util.post_output(ctx, output)


@bot.command(brief='Get PSS stardate & Melbourne time', name='time')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_time(ctx: discord.ext.commands.Context):
    """
    Get PSS stardate, as well as the day and time in Melbourne, Australia. Gives the name of the Australian holiday, if it is a holiday in Australia.

    Usage:
      /time

    Examples:
      /time - Prints PSS stardate, day & time in Melbourne and public holidays.
    """
    async with ctx.typing():
        now = datetime.datetime.now()
        today = datetime.date(now.year, now.month, now.day)
        pss_stardate = (today - settings.PSS_START_DATE).days
        str_time = 'Today is Stardate {}\n'.format(pss_stardate)

        mel_tz = pytz.timezone('Australia/Melbourne')
        mel_time = now.replace(tzinfo=pytz.utc).astimezone(mel_tz)
        str_time += mel_time.strftime('It is %A, %H:%M in Melbourne')

        aus_holidays = holidays.Australia(years=now.year, prov='ACT')
        mel_time = datetime.date(mel_time.year, mel_time.month, mel_time.day)
        if mel_time in aus_holidays:
            str_time += '\nIt is also a holiday ({}) in Australia'.format(aus_holidays[mel_time])

        first_day_of_next_month = datetime.datetime(now.year, (now.month + 1) % 12 or 12, 1)
        td = first_day_of_next_month - now
        str_time += '\nTime until the beginning of next month: {}d {}h {}m'.format(td.days, td.seconds//3600, (td.seconds//60) % 60)
    await ctx.send(str_time)


@bot.command(brief='Show links', name='links')
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_links(ctx: discord.ext.commands.Context):
    """
    Shows the links for useful sites regarding Pixel Starships.

    Usage:
      /links

    Examples:
      /links - Shows the links for useful sites regarding Pixel Starships.
    """
    async with ctx.typing():
        output = core.read_links_file()
    await util.post_output(ctx, output)


@bot.command(brief='Display info on this bot', name='about', aliases=['info'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_about(ctx: discord.ext.commands.Context):
    """
    Displays information about this bot and its authors.

    Usage:
      /about
      /info

    Examples:
      /about - Displays information on this bot and its authors.
    """
    async with ctx.typing():
        if ctx.guild is None:
            nick = bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        pfp_url = bot.user.avatar_url
        about_info = core.read_about_file()
        title = f'About {nick}'
        description = about_info['description']
        footer = f'Serving {len(bot.users)} users on {len(bot.guilds)} guilds.'
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
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_invite(ctx: discord.ext.commands.Context):
    """
    Produces an invite link and sends it via DM.

    Usage:
      /invite

    Examples:
      /invite - Produces an invite link and sends it via DM.
    """
    if ctx.guild is None:
        nick = bot.user.display_name
    else:
        nick = ctx.guild.me.display_name
    await ctx.author.send(f'Invite {nick} to your server: http://bit.ly/invite-pss-statistics')
    if not isinstance(ctx.channel, (discord.DMChannel, discord.GroupChannel)):
        await ctx.send(f'{ctx.author.mention} Sent invite link via DM.')


@bot.group(brief='Information on tournament time', name='tournament', aliases=['tourney'])
@discord.ext.commands.cooldown(rate=RATE*10, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_tournament(ctx: discord.ext.commands.Context):
    """
    Get information about the starting time of the tournament.

    Usage:
      /tournament
      /tourney

    Examples:
      /tournament - Displays information about the starting time of this month's tournament.
    """
    if ctx.invoked_subcommand is None:
        cmd = bot.get_command('tournament current')
        await ctx.invoke(cmd)


@cmd_tournament.command(brief='Information on this month\'s tournament time', name='current')
async def cmd_tournament_current(ctx: discord.ext.commands.Context):
    """
    Get information about the starting time of the current month's tournament.

    Usage:
      /tournament current
      /tourney current

    Examples:
      /tournament current - Displays information about the starting time of this month's tournament.
    """
    async with ctx.typing():
        utc_now = util.get_utcnow()
        start_of_tourney = tourney.get_current_tourney_start()
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@cmd_tournament.command(brief='Information on next month\'s tournament time', name='next')
async def cmd_tournament_next(ctx: discord.ext.commands.Context):
    """
    Get information about the starting time of the next month's tournament.

    Usage:
      /tournament next
      /tourney next

    Examples:
      /tournament next - Displays information about the starting time of next month's tournament.
    """
    async with ctx.typing():
        utc_now = util.get_utcnow()
        start_of_tourney = tourney.get_next_tourney_start()
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@bot.command(brief='Updates all caches manually', name='updatecache', hidden=True)
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=1, per=1, type=discord.ext.commands.BucketType.user)
async def cmd_updatecache(ctx: discord.ext.commands.Context):
    """This command is to be used to update all caches manually."""
    async with ctx.typing():
        crew.character_designs_retriever.update_cache()
        crew.collection_designs_retriever.update_cache()
        prestige_to_caches = list(crew.__prestige_to_cache_dict.values())
        for prestige_to_cache in prestige_to_caches:
            prestige_to_cache.update_data()
        prestige_from_caches = list(crew.__prestige_from_cache_dict.values())
        for prestige_from_cache in prestige_from_caches:
            prestige_from_cache.update_data()
        item.items_designs_retriever.update_cache()
        research.__research_designs_cache.update_data()
        room.rooms_designs_retriever.update_cache()
        training.training_designs_retriever.update_cache()
    await ctx.send('Updated all caches successfully!')



@bot.command(brief='Get infos on a fleet', name='fleet', aliases=['alliance'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_fleet(ctx: discord.ext.commands.Context, *, fleet_name: str):
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
    async with ctx.typing():
        exact_name = util.get_exact_args(ctx)
        if exact_name:
            fleet_name = exact_name
        fleet_infos = fleet.get_fleet_details_by_name(fleet_name)

    if fleet_infos:
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details)
            _, fleet_info = await paginator.wait_for_option_selection()

        if fleet_info:
            async with ctx.typing():
                (fleet_data, user_data, data_date) = tournament_data.get_data()
                output, file_paths = fleet.get_full_fleet_info_as_text(fleet_info, fleet_data=fleet_data, user_data=user_data, data_date=data_date)
            await util.post_output_with_files(ctx, output, file_paths)
            for file_path in file_paths:
                os.remove(file_path)
    else:
        await ctx.send(f'Could not find a fleet named `{fleet_name}`.')



@bot.command(brief='Get infos on a player', name='player', aliases=['user'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_player(ctx: discord.ext.commands.Context, *, player_name: str):
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
    async with ctx.typing():
        exact_name = util.get_exact_args(ctx)
        if exact_name:
            player_name = exact_name
        user_infos = user.get_user_details_by_name(player_name)

    if user_infos:
        if len(user_infos) == 1:
            user_info = user_infos[0]
        else:
            paginator = pagination.Paginator(ctx, player_name, user_infos, user.get_user_search_details)
            _, user_info = await paginator.wait_for_option_selection()

        if user_info:
            async with ctx.typing():
                output = user.get_user_details_by_info(user_info)
            await util.post_output(ctx, output)
    else:
        await ctx.send(f'Could not find a player named `{player_name}`.')










@bot.group(brief='Server settings', name='settings', invoke_without_command=True)
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings(ctx: discord.ext.commands.Context):
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
    if not util.is_guild_channel(ctx.channel):
        await ctx.send('This command cannot be used in DMs or group chats, but only in Discord servers/guilds!')
    elif ctx.invoked_subcommand is None:
        output = [f'**```Server settings for {ctx.guild.name}```**']

        autodaily_settings = server_settings.get_autodaily_settings(bot, ctx.guild.id)
        if autodaily_settings:
            output.extend(autodaily_settings[0].get_pretty_settings())
        use_pagination = server_settings.get_pagination_mode(ctx.guild.id)
        prefix = server_settings.get_prefix_or_default(ctx.guild.id)
        output.extend([
            f'Pagination = `{use_pagination}`',
            f'Prefix = `{prefix}`'
        ])
        await util.post_output(ctx, output)


@cmd_settings.group(brief='Retrieve auto-daily settings', name='autodaily', aliases=['daily'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_get_autodaily(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel) and ctx.invoked_subcommand is None:
        output = []
        async with ctx.typing():
            autodaily_settings = server_settings.get_autodaily_settings(bot, guild_id=ctx.guild.id)
            output = autodaily_settings[0].get_pretty_settings()
        await util.post_output(ctx, output)


@cmd_settings_get_autodaily.command(brief='Retrieve auto-daily channel', name='channel', aliases=['ch'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_get_autodaily_channel(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            autodaily_settings = server_settings.get_autodaily_settings(bot, guild_id=ctx.guild.id)
            output = autodaily_settings[0].get_pretty_setting_channel()
        await util.post_output(ctx, output)


@cmd_settings_get_autodaily.command(brief='Retrieve auto-daily mode', name='changemode', aliases=['mode'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_get_autodaily_mode(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            autodaily_settings = server_settings.get_autodaily_settings(bot, guild_id=ctx.guild.id)
            output = autodaily_settings[0].get_pretty_setting_changemode()
        await util.post_output(ctx, output)


@cmd_settings_get_autodaily.command(brief='Retrieve auto-daily notify', name='notify')
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_get_autodaily_notify(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            autodaily_settings = server_settings.get_autodaily_settings(bot, guild_id=ctx.guild.id)
            output = autodaily_settings[0].get_pretty_setting_notify()
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve pagination settings', name='pagination', aliases=['pages'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_get_pagination(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            use_pagination_mode = server_settings.get_pagination_mode(ctx.guild.id)
            output = [f'Pagination on this server has been set to: `{use_pagination_mode}`']
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve prefix settings', name='prefix')
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_get_prefix(ctx: discord.ext.commands.Context):
    """
    Retrieve the prefix setting for this server.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings prefix

    Examples:
      /settings prefix - Prints the prefix setting for the current Discord server/guild.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            prefix = server_settings.get_prefix_or_default(ctx.guild.id)
            output = [f'Prefix for this server is: `{prefix}`']
        await util.post_output(ctx, output)










@cmd_settings.group(brief='Reset server settings', name='reset', invoke_without_command=True)
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_reset(ctx: discord.ext.commands.Context):
    """
    Reset settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset

    Examples:
      /settings reset - Resets all settings for the current Discord server/guild.
    """
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
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_reset_autodaily(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel) and ctx.invoked_subcommand is None:
        async with ctx.typing():
            success = server_settings.db_reset_autodaily_settings(ctx.guild.id)
            if success:
                output = ['Successfully removed all auto-daily settings for this server.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset_autodaily.command(brief='Reset auto-daily channel', name='channel', aliases=['ch'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_reset_autodaily_channel(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            success = server_settings.db_reset_autodaily_channel(ctx.guild.id)
            if success:
                output = ['Successfully removed the auto-daily channel.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily channel setting for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset_autodaily.command(brief='Reset auto-daily change mode', name='changemode', aliases=['mode'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_reset_autodaily_mode(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            success = server_settings.reset_daily_delete_on_change(ctx.guild.id)
            if success:
                output = ['Successfully reset the auto-daily change mode.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily notification settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset_autodaily.command(brief='Reset auto-daily notifications', name='notify')
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_reset_autodaily_notify(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            success = server_settings.db_reset_autodaily_notify(ctx.guild.id)
            if success:
                output = ['Successfully reset the auto-daily notifications.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily notification settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset.command(brief='Reset pagination settings', name='pagination', aliases=['pages'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_reset_pagination(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            success = server_settings.db_reset_use_pagination(ctx.guild.id)
        if success:
            await ctx.invoke(bot.get_command(f'settings pagination'))
        else:
            output = [
                'An error ocurred while trying to reset the pagination settings for this server.',
                'Please try again or contact the bot\'s author.'
            ]
            await util.post_output(ctx, output)


@cmd_settings_reset.command(brief='Reset prefix settings', name='prefix')
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_reset_prefix(ctx: discord.ext.commands.Context):
    """
    Reset the prefix settings for this server to '/'.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset prefix

    Examples:
      /settings reset prefix - Resets the prefix settings for the current Discord server/guild.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            success = server_settings.reset_prefix(ctx.guild.id)
        if success:
            output = ['Successfully reset the prefix for this server.']
            await util.post_output(ctx, output)
            await ctx.invoke(bot.get_command(f'settings prefix'))
        else:
            output = [
                'An error ocurred while trying to reset the prefix settings for this server.',
                'Please try again or contact the bot\'s author.'
            ]
            await util.post_output(ctx, output)










@cmd_settings.group(brief='Change server settings', name='set', invoke_without_command=False)
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_set(ctx: discord.ext.commands.Context):
    """
    Sets settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      Refer to sub-command help.

    Examples:
      Refer to sub-command help.
    """
    if not util.is_guild_channel(ctx.channel):
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')


@cmd_settings_set.group(brief='Change auto-daily settings', name='autodaily', aliases=['daily'], invoke_without_command=False)
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_set_autodaily(ctx: discord.ext.commands.Context):
    """
    Change auto-daily settings for this server.

    You need the 'Manage Server' permission to use any of these commands.
    This command can only be used on Discord servers/guilds.
    """
    if not util.is_guild_channel(ctx.channel):
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')


@cmd_settings_set_autodaily.command(brief='Set auto-daily channel', name='channel', aliases=['ch'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_set_autodaily_channel(ctx: discord.ext.commands.Context, text_channel: discord.TextChannel = None):
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
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            autodaily_settings = server_settings.get_autodaily_settings(bot, guild_id=ctx.guild.id)[0]
            if not text_channel:
                text_channel = ctx.channel
            if text_channel and isinstance(text_channel, discord.TextChannel) and util.is_guild_channel(text_channel):
                success = True
                if autodaily_settings.channel_id != text_channel.id:
                    utc_now = util.get_utcnow()
                    yesterday = datetime.datetime(utc_now.year, utc_now.month, utc_now.day) - settings.ONE_SECOND
                    db_daily_info, _ = daily.db_get_daily_info()
                    latest_message_output, _ = dropship.get_dropship_text(daily_info=db_daily_info)
                    latest_daily_message = '\n'.join(latest_message_output)
                    _, latest_message = await daily_fetch_latest_message(text_channel, None, yesterday, latest_daily_message, None)
                    success = server_settings.db_update_daily_latest_message(ctx.guild.id, latest_message)
                success = daily.try_store_daily_channel(ctx.guild.id, text_channel.id)
                if success:
                    output = [f'Set auto-posting of the daily announcement to channel {text_channel.mention}.']
                else:
                    output = [
                        'Could not set auto-posting of the daily announcement for this server :(',
                        'Please try again or contact the bot\'s author.'
                    ]
            else:
                output = ['You need to provide a text channel on a server!']
        await util.post_output(ctx, output)


@cmd_settings_set_autodaily.command(brief='Set auto-daily repost mode', name='changemode', aliases=['mode'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_set_autodaily_change(ctx: discord.ext.commands.Context):
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
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            result = server_settings.toggle_daily_delete_on_change(ctx.guild.id)
            change_mode = server_settings.convert_to_edit_delete(result)
            output = [f'Change mode on this server is set to: `{change_mode}`']
        await util.post_output(ctx, output)


@cmd_settings_set_autodaily.command(brief='Set auto-daily notify settings', name='notify')
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_set_autodaily_notify(ctx: discord.ext.commands.Context, *, mention: Union[discord.Role, discord.Member]):
    """
    Sets the auto-daily notifications for this server. If the contents of the daily post change, this setting decides, who will get notified about that change. You can specify a user or a role.

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set autodaily notify <member/role mention>
      /settings set daily notify <member/role mention>

    Examples:
      /settings set autodaily notify @notify - Sets the role 'notify' to be notified on changes.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            if isinstance(mention, discord.Role):
                role: discord.Role = mention
                notify_id = role.id
                notify_type = server_settings.AutoDailyNotifyType.ROLE
            elif isinstance(mention, discord.Member):
                member: discord.Member = mention
                notify_id = member.id
                notify_type = server_settings.AutoDailyNotifyType.USER
            else:
                raise Exception('You need to specify a user or a role!')
            server_settings.set_autodaily_notify(ctx.guild.id, notify_id, notify_type)
            result = server_settings.get_autodaily_settings(bot, guild_id=ctx.guild.id)[0]
            output = [f'Notify on auto-daily changes: `{result._get_pretty_notify_settings()}`']
        await util.post_output(ctx, output)


@cmd_settings_set.command(brief='Set pagination', name='pagination', aliases=['pages'])
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_set_pagination(ctx: discord.ext.commands.Context, switch: str = None):
    """
    Sets or toggle the pagination for this server. The default is 'ON'. For information on what pagination is and what it does, use this command: /help pagination

    You need the 'Manage Server' permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set pagination <switch>
      /settings set pages <switch>

    Parameters:
      switch: A string determining the new pagination setting. Optional. Can be one of these values: [on, true, yes, 1, off, false, no, 0]

    Notes:
      If the parameter <switch> is being omitted, the command will toggle between 'ON' and 'OFF' depending on the current setting.

    Examples:
      /settings set pagination - Toggles the pagination setting for the current Discord server/guild depending on the current setting.
      /settings set pagination off - Turns off pagination for the current Discord server/guild.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            result = server_settings.set_pagination(ctx.guild.id, switch)
            use_pagination_mode = server_settings.convert_to_on_off(result)
            output = [f'Pagination on this server is: `{use_pagination_mode}`']
        await util.post_output(ctx, output)


@cmd_settings_set.command(brief='Set prefix', name='prefix')
@discord.ext.commands.has_permissions(manage_guild=True)
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_settings_set_prefix(ctx: discord.ext.commands.Context, prefix: str):
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
    if util.is_guild_channel(ctx.channel) and prefix:
        prefix = prefix.lstrip()
        pss_assert.valid_parameter_value(prefix, 'prefix', min_length=1)
        async with ctx.typing():
            success = server_settings.set_prefix(ctx.guild.id, prefix)
            if success:
                output = [f'Prefix for this server has been set to: `{prefix}`']
            else:
                output = [f'An unknown error ocurred while setting the prefix. Please try again or contact the bot\'s author.']
        await util.post_output(ctx, output)










@bot.command(name='pagination', hidden=True, aliases=['pages'])
@discord.ext.commands.cooldown(rate=RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.channel)
async def cmd_pagination(ctx: discord.ext.commands.Context):
    """
    Some commands allow the user to search for a fleet, a player or other stuff. Such a search may yield more than one result. Then the bot may offer the user to select one of these results.

    Pagination is a way to format the result list in way that allows the user to select one result. The pagination mode can be set individually per Discord server. There are two modes:
    - ON
    - OFF

    If pagination is turned ON for a server, the bot will print the results on pages of 5 results. The bot will add reactions. The user can use the reactions to navigate the pages or select an item of the result list.
    If pagination is turned OFF for a server, the bot will print the whole results list. The user can select an item from the list by typing the number in front of the respective result.

    In both cases the result list will disappear after 60 seconds without user input.
    """
    pass











@bot.command(brief='These are testing commands, usually for debugging purposes', name='test', hidden=True)
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=2*RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_test(ctx: discord.ext.commands.Context, action, *, params = None):
    print(f'+ called command test(ctx: discord.ext.commands.Context, {action}, {params}) by {ctx.author}')
    if action == 'utcnow':
        utcnow = util.get_utcnow()
        txt = util.get_formatted_datetime(utcnow)
        await ctx.send(txt)
    elif action == 'init':
        core.init_db()
        await ctx.send('Initialized the database from scratch')
        await util.try_delete_original_message(ctx)
    elif (action == 'select' or action == 'selectall') and params:
        query = f'SELECT {params}'
        result, error = core.db_fetchall(query)
        if error:
            await ctx.send(error)
        elif result:
            await ctx.send(result)
        else:
            await ctx.send('The query didn\'t return any results.')
    elif action == 'query' and params:
        query = f'{params}'
        success, error = core.db_try_execute(query)
        if not success:
            await ctx.send(error)
        else:
            await ctx.send(f'The query \'{params}\' has been executed successfully.')
    elif action == 'commands':
        output = [', '.join(__COMMANDS)]
        await util.post_output(ctx, output)


@bot.group(brief='list available devices', name='device', hidden=True)
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=2*RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_device(ctx: discord.ext.commands.Context):
    """
    Returns all known devices stored in the DB.
    """
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
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=2*RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_device_create(ctx: discord.ext.commands.Context):
    """
    Creates a new random device_key and attempts to store the new device in the DB.
    """
    async with ctx.typing():
        device = login.DEVICES.create_device()
        try:
            device.get_access_token()
            created = True
        except Exception as err:
            login.DEVICES.remove_device(device)
            created = False
    if created is True:
        await ctx.send(f'Created and stored device with key \'{device.key}\'.')
    else:
        await ctx.send(f'Failed to create and store device:```{err}```')


@cmd_device.command(brief='store device', name='add')
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=2*RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_device_add(ctx: discord.ext.commands.Context, device_key: str):
    """
    Attempts to store a device with the given device_key in the DB.
    """
    async with ctx.typing():
        try:
            device = login.DEVICES.add_device_by_key(device_key)
            added = True
        except Exception as err:
            added = False
    if added:
        await ctx.send(f'Added device with device key \'{device.key}\'.')
    else:
        await ctx.send(f'Could not add device with device key\'{device_key}\':```{err}```')


@cmd_device.command(brief='remove device', name='remove', aliases=['delete', 'yeet'])
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=2*RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_device_remove(ctx: discord.ext.commands.Context, device_key: str):
    """
    Attempts to remove a device with the given device_key from the DB.
    """
    async with ctx.typing():
        try:
            login.DEVICES.remove_device_by_key(device_key)
            yeeted = True
        except Exception as err:
            yeeted = False
    if yeeted:
        await ctx.send(f'Removed device with device key: \'{device_key}\'.')
    else:
        await ctx.send(f'Could not remove device with device key \'{device_key}\':```{err}```')


@cmd_device.command(brief='login to a device', name='login')
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=2*RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_device_login(ctx: discord.ext.commands.Context):
    """
    Attempts to remove a device with the given device_key from the DB.
    """
    async with ctx.typing():
        try:
            access_token = login.DEVICES.get_access_token()
            device = login.DEVICES.current
        except Exception as err:
            access_token = None
    if access_token is not None:
        await ctx.send(f'Logged in with device \'{device.key}\'.\nObtained access token: {access_token}')
    else:
        await ctx.send(f'Could not log in with device \'{device.key}\':```{err}``')


@cmd_device.command(brief='select a device', name='select')
@discord.ext.commands.is_owner()
@discord.ext.commands.cooldown(rate=2*RATE, per=COOLDOWN, type=discord.ext.commands.BucketType.user)
async def cmd_device_select(ctx: discord.ext.commands.Context, device_key: str):
    """
    Attempts to select a device with the given device_key from the DB.
    """
    async with ctx.typing():
        device = login.DEVICES.select_device(device_key)
    await ctx.send(f'Selected device \'{device.key}\'.')










# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    print(f'discord.py version: {discord.__version__}')
    core.init_db()
    login.init()
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
