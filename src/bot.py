from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from discord.ext import commands
from dateutil.relativedelta import relativedelta

import asyncio
import datetime
import discord
import holidays
import logging
import math
import os
import pytz
import re
import sys
import time

import emojis
import gdrive
import pagination
import pss_assert
import pss_core as core
import pss_crew as crew
import pss_daily as daily
import pss_dropship as dropship
import pss_exception
import pss_fleet as fleet
import pss_item as item
import pss_lookups as lookups
import pss_research as research
import pss_room as room
import pss_tournament as tourney
import pss_top
import pss_training as training
import pss_user as user
import server_settings
import settings
import utility as util



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


# ----- Bot Setup -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    style = '{',
    datefmt = '%Y%m%d %H:%M:%S',
    format = '{asctime} [{levelname:<8}] {name}: {message}')

bot = commands.Bot(command_prefix=COMMAND_PREFIX,
                   description='This is a Discord Bot for Pixel Starships',
                   activity=ACTIVITY)

setattr(bot, 'logger', logging.getLogger('bot.py'))


# ----- Bot Events ------------------------------------------------------------
@bot.event
async def on_ready() -> None:
    print(f'sys.argv: {sys.argv}')
    print(f'Current Working Directory: {PWD}')
    print(f'Bot prefix is: {COMMAND_PREFIX}')
    print(f'Bot version is: {settings.VERSION}')
    print(f'Bot logged in as {bot.user.name} (id={bot.user.id}) on {len(bot.guilds)} servers')
    core.init_db()
    bot.loop.create_task(post_dailies_loop())


@bot.event
async def on_command_error(ctx: discord.ext.commands.Context, err) -> None:
    if isinstance(err, commands.CommandOnCooldown):
        await ctx.send('Error: {}'.format(err))
    else:
        logging.getLogger().error(err, exc_info=True)
        if isinstance(err, pss_exception.Error):
            await ctx.send(f'`{ctx.message.clean_content}`: {err.msg}')
        elif isinstance(err, commands.CheckFailure):
            await ctx.send(f'Error: You don\'t have the required permissions in order to be able to use this command!')
        else:
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
    while True:
        utc_now = util.get_utcnow()
        daily_info = daily.mock_get_daily_info()
        has_daily_changed = daily.has_daily_changed(daily_info, utc_now)
        autodaily_settings = server_settings.db_get_autodaily_settings(without_latest_message_id=True)
        if has_daily_changed:
            await fix_daily_channels()
            autodaily_settings.extend(server_settings.db_get_autodaily_settings(can_post=True))

        created_output = False
        if autodaily_settings:
            autodaily_settings = daily.remove_duplicate_autodaily_settings(autodaily_settings)
            output, created_output = dropship.get_dropship_text(daily_info=daily_info)
            if created_output:
                await post_dailies(output, autodaily_settings, utc_now)

        if has_daily_changed:
            seconds_to_wait = 300
            if created_output:
                daily.db_set_daily_info(daily_info, utc_now)
        else:
            seconds_to_wait = util.get_seconds_to_wait(1)
        await asyncio.sleep(seconds_to_wait)


async def post_all_dailies(output: list, utc_now: datetime) -> None:
    await fix_daily_channels()
    print(f'[post_all_dailies] Fixed daily channels.')
    autodaily_settings = server_settings.db_get_autodaily_settings(can_post=True)
    print(f'[post_all_dailies] Retrieved autodaily settings.')
    await post_dailies(output, autodaily_settings, utc_now)


async def post_dailies(output: list, autodaily_settings: list, utc_now: datetime) -> None:
    for (guild_id, channel_id, can_post, latest_message_id, delete_on_change) in autodaily_settings:
        if guild_id is not None:
            can_post, latest_message_id = await post_autodaily(channel_id, latest_message_id, delete_on_change, output, utc_now)
            server_settings.db_update_autodaily_settings(guild_id, can_post=can_post, latest_message_id=latest_message_id)


async def post_autodaily(channel_id: int, latest_message_id: int, delete_on_change: bool, output: list, utc_now: datetime) -> (bool, str):
    """
    Returns (can_post, latest_message_id)
    """
    if delete_on_change is None or delete_on_change is True:
        post_new = True
    else:
        post_new = False

    if channel_id and output:
        can_post = True
        post = util.create_posts_from_lines(output, settings.MAXIMUM_CHARACTERS)[0]
        text_channel: discord.TextChannel = bot.get_channel(channel_id)
        latest_message: discord.Message = None
        if text_channel is not None:
            guild = text_channel.guild
            if can_post and latest_message_id:
                try:
                    latest_message = await text_channel.fetch_message(latest_message_id)
                except discord.NotFound:
                    print(f'[post_autodaily] could not find latest message [{latest_message_id}]')
                except Exception as err:
                    print(f'[post_autodaily] could not fetch message [{latest_message_id}]: {err}')
                    can_post = False

            if can_post:
                if latest_message and latest_message.created_at.day == utc_now.day:
                    if delete_on_change is True:
                        try:
                            await latest_message.delete()
                            latest_message = None
                            print(f'[post_autodaily] deleted message [{latest_message_id}] from channel [{channel_id}] on guild [{guild.id}]')
                        except discord.NotFound:
                            print(f'[post_autodaily] could not delete message [{latest_message_id}] from channel [{channel_id}] on guild [{guild.id}]: the message could not be found')
                            can_post = False
                        except discord.Forbidden:
                            print(f'[post_autodaily] could not delete message [{latest_message_id}] from channel [{channel_id}] on guild [{guild.id}]: the bot doesn\'t have the required permissions.')
                            can_post = False
                        except Exception as err:
                            print(f'[post_autodaily] could not delete message [{latest_message_id}] from channel [{channel_id}] on guild [{guild.id}]: {err}')
                            can_post = False

                    elif delete_on_change is False:
                        try:
                            await latest_message.edit(content=post)
                            print(f'[post_autodaily] edited message [{latest_message_id}] in channel [{channel_id}] on guild [{guild.id}]')
                        except discord.NotFound:
                            print(f'[post_autodaily] could not edit message [{latest_message_id}] from channel [{channel_id}] on guild [{guild.id}]: the message could not be found')
                            can_post = False
                        except discord.Forbidden:
                            print(f'[post_autodaily] could not edit message [{latest_message_id}] from channel [{channel_id}] on guild [{guild.id}]: the bot doesn\'t have the required permissions.')
                            can_post = False
                        except Exception as err:
                            print(f'[post_autodaily] could not edit message [{latest_message_id}] from channel [{channel_id}] on guild [{guild.id}]: {err}')
                            can_post = False
                else:
                    post_new = True

                if post_new and can_post:
                    try:
                        latest_message = await text_channel.send(post)
                        print(f'[post_autodaily] posted message [{latest_message.id}] in channel [{channel_id}] on guild [{guild.id}]')
                    except discord.Forbidden:
                        print(f'[post_autodaily] could not post a message in channel [{channel_id}] on guild [{guild.id}]: the bot doesn\'t have the required permissions.')
                        can_post = False
                    except Exception as err:
                        print(f'[post_autodaily] could not post a message in channel [{channel_id}] on guild [{guild.id}]: {err}')
                        can_post = False
        else:
            can_post = False

        if latest_message:
            return (can_post, latest_message.id)
        else:
            return (can_post, None)
    else:
        return (None, None)


async def fix_daily_channels():
    rows = [row for row in server_settings.db_get_autodaily_settings(None, None) if row and row[0]]
    for row in rows:
        can_post = False
        guild_id = row[0]
        channel_id = row[1]
        try:
            text_channel = await bot.fetch_channel(channel_id)
        except:
            text_channel = None
        if text_channel is not None:
            try:
                guild = await bot.fetch_guild(guild_id)
            except:
                guild = None
            if guild is not None:
                try:
                    me = await guild.fetch_member(bot.user.id)
                except:
                    me = None
                if me is not None:
                    permissions = text_channel.permissions_for(me)
                    if permissions is not None and permissions.send_messages is True:
                        print(f'[fix_daily_channels] bot can post in configured channel \'{text_channel.name}\' (id: {channel_id}) on server \'{guild.name}\' (id: {guild_id})')
                        can_post = True
                    else:
                        print(f'[fix_daily_channels] bot is not allowed to post in configured channel \'{text_channel.name}\' (id: {channel_id}) on server \'{guild.name}\' (id: {guild_id})')
                else:
                    print(f'[fix_daily_channels] couldn\'t fetch member for bot for guild: {guild.name} (id: {guild_id})')
            else:
                print(f'[fix_daily_channels] couldn\'t fetch guild for channel \'{text_channel.name}\' (id: {channel_id}) with id: {guild_id}')
        else:
            print(f'[fix_daily_channels] couldn\'t fetch channel with id: {channel_id}')
        daily.fix_daily_channel(guild_id, can_post)


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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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


@bot.command(brief='Get item/crew stats', name='stats')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
        level, name = util.get_level_and_name(level, name)
        try:
            char_output, char_success = crew.get_char_design_details_by_name(name, level)
        except pss_exception.InvalidParameter:
            char_output = None
            char_success = False
        try:
            item_output, item_success = item.get_item_details(name)
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
        await ctx.send(f'Could not find a character or an item named `{name}`.')


@bot.command(brief='Get character stats', name='char', aliases=['crew'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
        output, _ = item.get_item_details(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get best items for a slot', name='best')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
        output, _ = research.get_research_details_from_name(research_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get collections', name='collection', aliases=['coll'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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


@bot.group(brief='Division stars (works only during tournament finals)', name='stars', invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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


@cmd_stars.group(brief='Fleet stars (works only during tournament finals)', name='fleet', aliases=['alliance'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
                    fleet_users_infos = fleet.get_fleet_users_by_info(fleet_info).values()
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
@commands.cooldown(rate=RATE, per=COOLDOWN*2, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily(ctx: discord.ext.commands.Context):
    """
    This command can be used to configure the bot to automatically post the daily announcement at 1 am UTC to a certain text channel.
    The daily announcement is the message that this bot will post, when you use the /daily command.

    In order to use this command, you need the Administrator permission for the current Discord server/guild.
    """
    pass


@cmd_autodaily.command(brief='Fix the auto-daily channels.', name='fix')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily_fix(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        fix_daily_channels()
    await ctx.send('Fixed daily channels')


@cmd_autodaily.group(brief='List configured auto-daily channels', name='list', invoke_without_command=False)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list(ctx: discord.ext.commands.Context):
    pass


@cmd_autodaily_list.command(brief='List all configured auto-daily channels', name='all')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list_all(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, None)
    await util.post_output(ctx, output)


@cmd_autodaily_list.command(brief='List all invalid configured auto-daily channels', name='invalid')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list_invalid(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, False)
    await util.post_output(ctx, output)


@cmd_autodaily_list.command(brief='List all valid configured auto-daily channels', name='valid')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily_list_valid(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, True)
    await util.post_output(ctx, output)


@cmd_autodaily.command(brief='Post a daily message on this server\'s auto-daily channel', name='post')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily_post(ctx: discord.ext.commands.Context):
    guild = ctx.guild
    channel_id = server_settings.db_get_daily_channel_id(guild.id)
    if channel_id is not None:
        text_channel = bot.get_channel(channel_id)
        output, _ = dropship.get_dropship_text()
        await util.post_output_to_channel(text_channel, output)


@cmd_autodaily.command(brief='Post a daily message on all servers\' auto-daily channels', name='postall')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
@commands.has_permissions(manage_guild=True)
async def cmd_autodaily_postall(ctx: discord.ext.commands.Context):
    await util.try_delete_original_message(ctx)
    daily_info = daily.get_daily_info()
    await post_all_dailies(daily_info, util.get_utcnow())


@bot.command(brief='Get crew levelling costs', name='level', aliases=['lvl'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
        pss_start = datetime.date(year=2016, month=1, day=6)
        pss_stardate = (today - pss_start).days
        str_time = 'Today is Stardate {}\n'.format(pss_stardate)

        mel_tz = pytz.timezone('Australia/Melbourne')
        mel_time = now.replace(tzinfo=pytz.utc).astimezone(mel_tz)
        str_time += mel_time.strftime('It is %A, %H:%M in Melbourne')

        aus_holidays = holidays.Australia(years=now.year, prov='ACT')
        mel_time = datetime.date(mel_time.year, mel_time.month, mel_time.day)
        if mel_time in aus_holidays:
            str_time += '\nIt is also a holiday ({}) in Australia'.format(aus_holidays[mel_time])

        first_day_of_next_month = datetime.datetime(now.year, now.month, 1) + relativedelta(months=1, days=0)
        td = first_day_of_next_month - now
        str_time += '\nTime until the beginning of next month: {}d {}h {}m'.format(td.days, td.seconds//3600, (td.seconds//60) % 60)
    await ctx.send(str_time)


@bot.command(brief='Show links', name='links')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
        output = [
            core.read_about_file(),
            f'v{settings.VERSION}'
        ]
    await util.post_output(ctx, output)


@bot.command(brief='Get an invite link', name='invite')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_invite(ctx: discord.ext.commands.Context):
    """
    Produces an invite link and sends it via DM.

    Usage:
      /invite

    Examples:
      /invite - Produces an invite link and sends it via DM.
    """
    nick = ctx.guild.me.nick
    await ctx.author.send(f'Invite {nick} to your server: http://bit.ly/invite-pss-statistics')
    await ctx.send('Sent invite link via DM.')


@bot.group(brief='Information on tournament time', name='tournament', aliases=['tourney'])
@commands.cooldown(rate=RATE*10, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.is_owner()
@commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
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
        item.__item_designs_cache.update_data()
        research.__research_designs_cache.update_data()
        room.__room_designs_cache.update_data()
        training.training_designs_retriever.update_cache()
    await ctx.send('Updated all caches successfully!')



@bot.command(brief='Get infos on a fleet', name='fleet', aliases=['alliance'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_fleet(ctx: discord.ext.commands.Context, *, fleet_name: str):
    """
    Get details on a fleet. This command will also create a spreadsheet containing information on a fleet's members. If the provided fleet name does not match any fleet exactly, you will be prompted to select from a list of results. The selection prompt will time out after 60 seconds.

    Usage:
      /fleet [fleet_name]
      /alliance [fleet_name]

    Parameters:
      fleet_name: The (beginning of the) name of the fleet to search for. Mandatory.

    Examples:
      /fleet HYDRA - Offers a list of fleets having a name starting with 'hydra'.Upon selection prints fleet details and posts the spreadsheet.
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
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
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings(ctx: discord.ext.commands.Context):
    """
    Retrieve settings for this Discord server/guild.
    Set settings for this server using the subcommands 'set' and 'reset'.

    You need the Administrator permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings

    Examples:
      /settings - Prints all settings for the current Discord server/guild.
    """
    if not util.is_guild_channel(ctx.channel):
        await ctx.send('This command cannot be used in DMs or group chats, but only in Discord servers/guilds!')
    elif ctx.invoked_subcommand is None:
        autodaily_channel_mention = server_settings.get_daily_channel_mention(ctx)
        if autodaily_channel_mention is None:
            autodaily_channel_mention = '<not set>'
        use_pagination = server_settings.get_pagination_mode(ctx.guild.id)
        prefix = server_settings.get_prefix_or_default(ctx.guild.id)
        output = [
            f'**```Server settings for {ctx.guild.name}```**' +
            f'Auto-daily channel = {autodaily_channel_mention}',
            f'Pagination = `{use_pagination}`',
            f'Prefix = `{prefix}`'
        ]
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve auto-daily settings', name='autodaily', aliases=['daily'])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_autodaily(ctx: discord.ext.commands.Context):
    """
    Retrieve the auto-daily setting for this server.

    You need the Administrator permission to use this command.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings autodaily
      /settings daily

    Examples:
      /settings autodaily - Prints the auto-daily setting for the current Discord server/guild.
    """
    if util.is_guild_channel(ctx.channel):
        output = []
        async with ctx.typing():
            autodaily_settings = server_settings.db_get_autodaily_settings(guild_id=ctx.guild.id)
            if autodaily_settings:
                (_, channel_id, _, _, delete_on_change) = autodaily_settings[0]
                channel = await bot.fetch_channel(channel_id)
                change_mode = server_settings.convert_to_edit_delete(delete_on_change)
                if channel:
                    channel_mention = channel.mention or 'None'
                else:
                    channel_mention = 'None'
                output.append(f'The daily announcement will be auto-posted in channel: {channel_mention}')
                output.append(f'Change mode on this server is set to: `{change_mode}`')
            else:
                output.append('Auto-posting of the daily announcement is not configured for this server!')
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve pagination settings', name='pagination', aliases=['pages'])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_pagination(ctx: discord.ext.commands.Context):
    """
    Retrieve the pagination setting for this server. For information on what pagination is and what it does, use this command: /help pagination

    You need the Administrator permission to use this command.
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
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_get_prefix(ctx: discord.ext.commands.Context):
    """
    Retrieve the prefix setting for this server.

    You need the Administrator permission to use this command.
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
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset(ctx: discord.ext.commands.Context):
    """
    Reset settings for this server.

    You need the Administrator permission to use any of these commands.
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


@cmd_settings_reset.command(brief='Reset auto-daily settings to defaults', name='autodaily', aliases=['daily'])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_autodaily(ctx: discord.ext.commands.Context):
    """
    Reset the auto-daily settings for this server.

    You need the Administrator permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset autodaily
      /settings reset daily

    Examples:
      /settings reset autodaily - Resets the auto-daily settings for the current Discord server/guild.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            success = server_settings.db_reset_autodaily_channel(ctx.guild.id)
            if success:
                output = ['Successfully removed auto-daily settings for this server.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_settings_reset.command(brief='Reset pagination settings', name='pagination', aliases=['pages'])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_pagination(ctx: discord.ext.commands.Context):
    """
    Reset the pagination settings for this server to 'ON'. For information on what pagination is and what it does, use this command: /help pagination

    You need the Administrator permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset pagination
      /settings reset pages

    Examples:
      /settings reset pagination - Resets the pagination settings for the current Discord server/guild.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            _ = server_settings.db_reset_use_pagination(ctx.guild.id)
            use_pagination_mode = server_settings.get_pagination_mode(ctx.guild.id)
            output = [f'Pagination on this server is: `{use_pagination_mode}`']
        await util.post_output(ctx, output)


@cmd_settings_reset.command(brief='Reset prefix settings', name='prefix')
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_reset_prefix(ctx: discord.ext.commands.Context):
    """
    Reset the prefix settings for this server to '/'.

    You need the Administrator permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings reset prefix

    Examples:
      /settings reset prefix - Resets the prefix settings for the current Discord server/guild.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            _ = server_settings.reset_prefix(ctx.guild.id)
            prefix = server_settings.get_prefix_or_default(ctx.guild.id)
            output = [f'Prefix for this server has been reset to: `{prefix}`']
        await util.post_output(ctx, output)










@cmd_settings.group(brief='Change server settings', name='set', invoke_without_command=False)
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set(ctx: discord.ext.commands.Context):
    """
    Sets settings for this server.

    You need the Administrator permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      Refer to sub-command help.

    Examples:
      Refer to sub-command help.
    """
    if not util.is_guild_channel(ctx.channel):
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')


@cmd_settings_set.group(brief='Change auto-daily settings', name='autodaily', aliases=['daily'], invoke_without_command=False)
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_autodaily(ctx: discord.ext.commands.Context):
    """
    Change auto-daily settings for this server.
    """
    if not util.is_guild_channel(ctx.channel):
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')


@cmd_settings_set_autodaily.command(brief='Set auto-daily channel', name='channel', aliases=['ch'])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_autodaily_channel(ctx: discord.ext.commands.Context, text_channel: discord.TextChannel = None):
    """
    Sets the auto-daily channel for this server. This channel will receive an automatic /daily message at 1 am UTC.

    You need the Administrator permission to use any of these commands.
    This command can only be used on Discord servers/guilds.

    Usage:
      /settings set autodaily channel <text_channel_mention>
      /settings set daily ch <text_channel_mention>

    Parameters:
      text_channel_mention: A mention of a text-channel on the current Discord server/guild. Optional. If omitted, will set the current channel.

    Examples:
      /settings set daily channel - Sets the current channel to receive the /daily message once a day.
      /settings set autodaily ch #announcements - Sets the channel #announcements to receive the /daily message once a day.
    """
    if util.is_guild_channel(ctx.channel):
        async with ctx.typing():
            current_channel_id = server_settings.db_get_daily_channel_id(ctx.guild.id)
            if not text_channel:
                text_channel = ctx.channel
            if text_channel and isinstance(text_channel, discord.TextChannel) and util.is_guild_channel(text_channel):
                success = True
                if current_channel_id != text_channel.id:
                    success = server_settings.db_update_daily_latest_message_id(ctx.guild.id, None)
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


@cmd_settings_set_autodaily.command(brief='Set auto-daily channel', name='changemode', aliases=['mode'])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_autodaily_change(ctx: discord.ext.commands.Context):
    """
    Sets the auto-daily mode for this server. If the contents of the daily post change, this setting decides, whether an existing daily post gets edited, or if it gets deleted and a new one gets posted instead.

    You need the Administrator permission to use any of these commands.
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


@cmd_settings_set.command(brief='Set pagination', name='pagination', aliases=['pages'])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_pagination(ctx: discord.ext.commands.Context, switch: str = None):
    """
    Sets or toggle the pagination for this server. The default is 'ON'. For information on what pagination is and what it does, use this command: /help pagination

    You need the Administrator permission to use any of these commands.
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
@commands.has_permissions(manage_guild=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_settings_set_prefix(ctx: discord.ext.commands.Context, prefix: str):
    """
    Set the prefix for this server. The default is '/'.

    You need the Administrator permission to use any of these commands.
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
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
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
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.user)
async def cmd_test(ctx: discord.ext.commands.Context, action, *, params):
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











# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    print(f'discord.py version: {discord.__version__}')
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
