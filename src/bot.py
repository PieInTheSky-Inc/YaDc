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
import pagination
import pss_fleet as fleet
import pss_core as core
import pss_crew as crew
import pss_daily as daily
import pss_dropship as dropship
import pss_exception
import pss_item as item
import pss_lookups as lookups
import pss_research as research
import pss_room as room
import pss_tournament as tourney
import pss_top
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
    COMMAND_PREFIX='/'

PWD = os.getcwd()
sys.path.insert(0, PWD + '/src/')

ACTIVITY = discord.Activity(type=discord.ActivityType.playing, name='/help')


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
async def on_ready():
    print(f'sys.argv: {sys.argv}')
    print(f'Current Working Directory: {PWD}')
    print(f'Bot prefix is: {COMMAND_PREFIX}')
    print('Bot logged in as {} (id={}) on {} servers'.format(
        bot.user.name, bot.user.id, len(bot.guilds)))
    core.init_db()
    bot.loop.create_task(post_dailies_loop())


@bot.event
async def on_command_error(ctx: discord.ext.commands.Context, err):
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
async def on_guild_join(guild: discord.Guild):
    success = server_settings.db_create_server_settings(guild.id)
    if not success:
        print(f'[on_guild_join] Could not create server settings for guild {guild.name} (ID: {guild.id})')


@bot.event
async def on_guild_remove(guild: discord.Guild):
    success = server_settings.db_delete_server_settings(guild.id)
    if not success:
        print(f'[on_guild_join] Could not delete server settings for guild {guild.name} (ID: {guild.id})')


# ----- Tasks ----------------------------------------------------------
async def post_dailies_loop():
    while True:
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        if utc_now.hour == 0:
            await asyncio.sleep(59)
        elif utc_now.hour == 1 and utc_now.minute == 0:
            await post_all_dailies()
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(3600)


async def post_all_dailies():
    fix_daily_channels()
    channel_ids = daily.get_valid_daily_channel_ids()
    output, _ = dropship.get_dropship_text()
    for channel_id in channel_ids:
        text_channel = bot.get_channel(channel_id)
        if text_channel != None:
            guild = text_channel.guild
            try:
                if output:
                    posts = util.create_posts_from_lines(output, settings.MAXIMUM_CHARACTERS)
                    for post in posts:
                        await text_channel.send(post)
            except Exception as error:
                print('[post_all_dailies] {} occurred while trying to post to channel \'{}\' on server \'{}\': {}'.format(error.__class__.__name__, text_channel.name, guild.name, error))


def fix_daily_channels():
    rows = server_settings.db_get_autodaily_settings(None, None)
    for row in rows:
        can_post = False
        guild_id = int(row[0])
        channel_id = int(row[1])
        text_channel = bot.get_channel(channel_id)
        if text_channel != None:
            guild = bot.get_guild(guild_id)
            if guild != None:
                guild_member = guild.get_member(bot.user.id)
                if guild_member != None:
                    permissions = text_channel.permissions_for(guild_member)
                    if permissions != None and permissions.send_messages == True:
                        print('[fix_daily_channels] bot can post in configured channel \'{}\' (id: {}) on server \'{}\' (id: {})'.format(text_channel.name, channel_id, guild.name, guild_id))
                        can_post = True
                    else:
                        print('[fix_daily_channels] bot is not allowed to post in configured channel \'{}\' (id: {}) on server \'{}\' (id: {})'.format(text_channel.name, channel_id, guild.name, guild_id))
                else:
                    print('[fix_daily_channels] couldn\'t fetch member for bot for guild: {} (id: {})'.format(guild.name, guild_id))
            else:
                print('[fix_daily_channels] couldn\'t fetch guild for channel \'{}\' (id: {}) with id: {}'.format(text_channel.name, channel_id, guild_id))
        else:
            print('[fix_daily_channels] couldn\'t fetch channel with id: {}'.format(channel_id))
        daily.fix_daily_channel(guild_id, can_post)


# ----- General Bot Commands ----------------------------------------------------------
@bot.command(brief='Ping the server')
async def ping(ctx: discord.ext.commands.Context):
    """Ping the server to verify that it\'s listening for commands"""
    async with ctx.typing():
        await ctx.send('Pong!')


@bot.command(hidden=True, brief='Run shell command')
@commands.is_owner()
async def shell(ctx: discord.ext.commands.Context, *, cmd):
    """Run a shell command"""
    async with ctx.typing():
        txt = util.shell_cmd(cmd)
        await ctx.send(txt)


# ----- PSS Bot Commands --------------------------------------------------------------
@bot.command(brief='Get prestige combos of crew')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def prestige(ctx: discord.ext.commands.Context, *, char_name=None):
    """Get the prestige combinations of the character specified"""
    async with ctx.typing():
        output, _ = crew.get_prestige_from_info(char_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get character recipes')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def recipe(ctx: discord.ext.commands.Context, *, char_name=None):
    """Get the prestige recipes of a character"""
    async with ctx.typing():
        output, _ = crew.get_prestige_to_info(char_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item ingredients', aliases=['ing'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def ingredients(ctx: discord.ext.commands.Context, *, name=None):
    """Get the ingredients for an item"""
    async with ctx.typing():
        output, _ = item.get_ingredients_for_item(name)
    await util.post_output(ctx, output)


@bot.command(brief='Get crafting recipes', aliases=['upg'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def upgrade(ctx: discord.ext.commands.Context, *, item_name=None):
    """Returns any crafting recipe involving the requested item."""
    async with ctx.typing():
        output, _ = item.get_item_upgrades_from_name(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get item\'s market prices and fair prices from the PSS API', aliases=['fairprice', 'cost'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def price(ctx: discord.ext.commands.Context, *, item_name=None):
    """Get the average price (market price) and the Savy price (fair price) in bux of the item(s) specified, as returned by the PSS API. Note that prices returned by the API may not reflect the real market value, due to transfers between alts/friends"""
    async with ctx.typing():
        output, _ = item.get_item_price(item_name)
    await util.post_output(ctx, output)


@bot.command(name='stats', brief='Get item/crew stats')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stats(ctx: discord.ext.commands.Context, level=None, *, name=None):
    """Get the stats of a character/crew or item.

       Parameters:
         level (optional): will only apply to crew stats.
         name (mandatory): name of a crew or item
    """
    async with ctx.typing():
        level, name = util.get_level_and_name(level, name)
        try:
            char_output, char_success = crew.get_char_details_from_name(name, level)
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
        await ctx.send(f'Could not find a character or an item named **{name}**')



@bot.command(name='char', brief='Get character stats', aliases=['crew'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def char(ctx: discord.ext.commands.Context, level=None, *, char_name=None):
    """Get the stats of a character/crew.

       Parameters:
         level (optional): if specified, stats for this level will be printed
         char_name (mandatory): name of a crew
    """
    async with ctx.typing():
        level, char_name = util.get_level_and_name(level, char_name)
        output, _ = crew.get_char_details_from_name(char_name, level=level)
    await util.post_output(ctx, output)


@bot.command(name='item', brief='Get item stats')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_item(ctx: discord.ext.commands.Context, *, item_name):
    """Get the stats of an item."""
    async with ctx.typing():
        output, _ = item.get_item_details(item_name)
    await util.post_output(ctx, output)


@bot.command(brief='Get best items for a slot')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def best(ctx: discord.ext.commands.Context, slot=None, stat=None):
    """Get the best enhancement item for a given slot. If multiple matches are found, matches will be shown in descending order according to their bonus.

       Parameters:
         slot (mandatory): the equipment slot. Use 'all' or 'any' to get infor for all slots.
         stat (mandatory): the crew stat you're looking for.
    """
    async with ctx.typing():
        output, _ = item.get_best_items(slot, stat)
    await util.post_output(ctx, output)


@bot.command(name='research', brief='Get research data')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_research(ctx: discord.ext.commands.Context, *, name: str = None):
    """Get the research details on a specific research. If multiple matches are found, only a brief summary will be provided"""
    async with ctx.typing():
        output, _ = research.get_research_details_from_name(name)
    await util.post_output(ctx, output)


@bot.command(brief='Get collections')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def collection(ctx: discord.ext.commands.Context, *, collection_name=None):
    """Get the details on a specific collection."""
    async with ctx.typing():
        output, _ = crew.get_collection_info(collection_name)
    await util.post_output(ctx, output)


@bot.command(brief='Division stars (works only during tournament finals)')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stars(ctx: discord.ext.commands.Context, *, division=None):
    """Get stars earned by each fleet during final tournament week. Replace [division] with a division name (a, b, c or d)"""
    async with ctx.typing():
        output, _ = pss_top.get_division_stars(division=division)
    await util.post_output(ctx, output)


@bot.command(hidden=True, brief='Show the dailies', name='daily')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_daily(ctx: discord.ext.commands.Context):
    """Show the dailies"""
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = dropship.get_dropship_text()
    await util.post_output(ctx, output)


@bot.command(brief='Show the news')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def news(ctx: discord.ext.commands.Context):
    """Show the news"""
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = dropship.get_news()
    await util.post_output(ctx, output)


@bot.group(hidden=True, brief='Configure auto-posting the daily announcement for the current server.')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily(ctx: discord.ext.commands.Context):
    """
    This command can be used to configure the bot to automatically post the daily announcement at 1 am UTC to a certain text channel.
    The daily announcement is the message that this bot will post, when you use the /daily command.

    In order to use this command, you need Administrator permissions for this server.
    """
    pass


@autodaily.command(brief='Fix the auto-daily channels.', name='fix')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_fix(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        fix_daily_channels()
    await ctx.send('Fixed daily channels')


@autodaily.group(name='list')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list(ctx: discord.ext.commands.Context):
    pass


@autodaily_list.command(name='all')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list_all(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, None)
    await util.post_output(ctx, output)


@autodaily_list.command(name='invalid')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list_invalid(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, False)
    await util.post_output(ctx, output)


@autodaily_list.command(name='valid')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list_valid(ctx: discord.ext.commands.Context):
    async with ctx.typing():
        output = daily.get_daily_channels(ctx, None, True)
    await util.post_output(ctx, output)


@autodaily.command(name='post')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_post(ctx: discord.ext.commands.Context):
    guild = ctx.guild
    channel_id = server_settings.db_get_daily_channel_id(guild.id)
    if channel_id is not None:
        text_channel = bot.get_channel(channel_id)
        output, _ = dropship.get_dropship_text()
        await util.post_output_to_channel(text_channel, output)


@autodaily.command(name='postall')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_postall(ctx: discord.ext.commands.Context):
    await util.try_delete_original_message(ctx)
    await post_all_dailies()


@bot.command(brief='Get crew levelling costs', aliases=['lvl'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def level(ctx: discord.ext.commands.Context, from_level: int = None, to_level: int = None):
    """Shows the cost for a crew to reach a certain level.
       Parameter from_level is required to be lower than to_level
       If only from_level is being provided, it will print out costs from level 1 to from_level"""
    async with ctx.typing():
        output, _ = crew.get_level_costs(from_level, to_level)
    await util.post_output(ctx, output)


@bot.group(name='top', brief='Prints top fleets or captains', invoke_without_command=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def top(ctx: discord.ext.commands.Context, count: int = 100):
    """Prints either top fleets or captains (fleets by default)."""
    if ctx.invoked_subcommand is None:
        cmd = bot.get_command(f'top fleets')
        await ctx.invoke(cmd, count=count)


@top.command(name='fleets', brief='Prints top fleets', aliases=['alliances'])
async def top_fleets(ctx: discord.ext.commands.Context, count: int = 100):
    """Prints top fleets."""
    async with ctx.typing():
        output, _ = pss_top.get_top_fleets(count)
    await util.post_output(ctx, output)


@top.command(name='captains', brief='Prints top captains', aliases=['players', 'users'])
async def top_captains(ctx: discord.ext.commands.Context, count: int = 100):
    """Prints top fleets."""
    async with ctx.typing():
        output, _ = pss_top.get_top_captains(count)
    await util.post_output(ctx, output)


@bot.command(name='room', brief='Get room infos')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_room(ctx: discord.ext.commands.Context, *, name: str = None):
    """
    Usage: /room [name]
           /room [short name] [lvl]

    Get detailed information on a room. If more than 2 results are found, details will be omitted.

    Examples:
    - /room mineral
    - /room cloak generator lv2
    - /room mst 3
    """
    async with ctx.typing():
        output, _ = room.get_room_details_from_name(name)
    await util.post_output(ctx, output)


@bot.command(brief='Get PSS stardate & Melbourne time', name='time')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_time(ctx: discord.ext.commands.Context):
    """Get PSS stardate, as well as the day and time in Melbourne, Australia. Gives the name of the Australian holiday, if it is a holiday in Australia."""
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


@bot.command(brief='Show links')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def links(ctx: discord.ext.commands.Context):
    """Shows the links for useful sites in Pixel Starships"""
    async with ctx.typing():
        output = core.read_links_file()
    await util.post_output(ctx, output)


@bot.command(brief='Display info on this bot')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def about(ctx: discord.ext.commands.Context):
    """Displays information on this bot and its authors."""
    async with ctx.typing():
        txt = core.read_about_file()
    await ctx.send(txt)


@bot.group(brief='Information on tournament time', aliases=['tourney'])
@commands.cooldown(rate=RATE*10, per=COOLDOWN, type=commands.BucketType.channel)
async def tournament(ctx: discord.ext.commands.Context):
    """Get information about the time of the tournament.
       If this command is called without a sub command, it will display
       information about the time of the current month's tournament."""
    if ctx.invoked_subcommand is None:
        cmd = bot.get_command('tournament current')
        await ctx.invoke(cmd)


@tournament.command(brief='Information on this month\'s tournament time', name='current')
async def tournament_current(ctx: discord.ext.commands.Context):
    """Get information about the time of the current month's tournament."""
    async with ctx.typing():
        utc_now = util.get_utcnow()
        start_of_tourney = tourney.get_current_tourney_start()
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@tournament.command(brief='Information on next month\'s tournament time', name='next')
async def tournament_next(ctx: discord.ext.commands.Context):
    """Get information about the time of next month's tournament."""
    async with ctx.typing():
        utc_now = util.get_utcnow()
        start_of_tourney = tourney.get_next_tourney_start()
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@bot.command(brief='Updates all caches manually', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=1, per=1, type=commands.BucketType.channel)
async def updatecache(ctx: discord.ext.commands.Context):
    """This command is to be used to update all caches manually."""
    async with ctx.typing():
        crew.__character_designs_cache.update_data()
        crew.__collection_designs_cache.update_data()
        prestige_to_caches = list(crew.__prestige_to_cache_dict.values())
        for prestige_to_cache in prestige_to_caches:
            prestige_to_cache.update_data()
        prestige_from_caches = list(crew.__prestige_from_cache_dict.values())
        for prestige_from_cache in prestige_from_caches:
            prestige_from_cache.update_data()
        item.__item_designs_cache.update_data()
        research.__research_designs_cache.update_data()
        room.__room_designs_cache.update_data()
    await ctx.send('Updated all caches successfully!')



@bot.command(brief='Get infos on a fleet', name='fleet')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_fleet(ctx: discord.ext.commands.Context, *, fleet_name=None):
    """Get details on a fleet.

       This command will also create a spreadsheet containing information on a fleet's members."""
    async with ctx.typing():
        fleet_infos = fleet.get_fleet_details_by_name(fleet_name)

    if fleet_infos:
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            paginator = pagination.Paginator(ctx, fleet_name, fleet_infos, fleet.get_fleet_search_details)
            _, fleet_info = await paginator.wait_for_option_selection()

        if fleet_info:
            output, file_path = fleet.get_full_fleet_info_as_text(fleet_info)
            await util.post_output_with_file(ctx, output, file_path)
            os.remove(file_path)
    else:
        await ctx.send(f'Could not find a fleet named {fleet_name}')



@bot.command(brief='Get infos on a player')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def player(ctx: discord.ext.commands.Context, *, player_name=None):
    """Get details on a player.

       You can only search for the beginning of a name.
       Savy servers only return up to 10 results.
       So if you can't find the player you're looking for, you need to search again."""
    async with ctx.typing():
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
        await ctx.send(f'Could not find a player named {player_name}')










@bot.group(brief='Server settings', name='settings')
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_settings(ctx: discord.ext.commands.Context):
    """Retrieve settings for this server.
       Set settings for this server using the subcommands 'set' and 'reset'.

       You need the Administrator permission to use any of these commands."""
    if ctx.channel.type != discord.ChannelType.text:
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')


@cmd_settings.command(brief='Retrieve auto-daily settings', name='autodaily', aliases=['daily'])
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_get_autodaily(ctx: discord.ext.commands.Context):
    """Retrieve the pagination setting for this server. You need administrator privileges to do so."""
    if ctx.channel.type == discord.ChannelType.text:
        async with ctx.typing():
            channel_name = server_settings.get_daily_channel_name(ctx)
            if channel_name:
                output = [f'The daily announcement will be auto-posted at 1 am UTC in channel {channel_name}.']
            else:
                output = ['Auto-posting of the daily announcement is not configured for this server!']
        await util.post_output(ctx, output)


@cmd_settings.command(brief='Retrieve pagination settings', name='pagination', aliases=['pages'])
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_get_pagination(ctx: discord.ext.commands.Context):
    """Retrieve the pagination setting for this server. You need administrator privileges to do so."""
    if ctx.channel.type == discord.ChannelType.text:
        async with ctx.typing():
            use_pagination_mode = server_settings.convert_to_on_off(server_settings.db_get_use_pagination(ctx.guild.id))
            output = [f'Pagination on this server has been set to: {use_pagination_mode}']
        await util.post_output(ctx, output)










@cmd_settings.group(brief='Reset server settings', name='reset')
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_reset(ctx: discord.ext.commands.Context):
    """Reset settings to defaults for this server.

       You need the Administrator permission to use any of these commands."""
    if ctx.channel.type != discord.ChannelType.text:
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')


@cmd_reset.command(brief='Reset auto-daily settings to defaults', name='autodaily', aliases=['daily'])
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_reset_autodaily(ctx: discord.ext.commands.Context):
    """Reset auto-posting the daily for this server.

       You need the Administrator permission to use this command."""
    if ctx.channel.type == discord.ChannelType.text:
        async with ctx.typing():
            success = server_settings.db_reset_autodaily_settings(ctx.guild.id)
            if success:
                output = ['Successfully removed auto-daily settings for this server.']
            else:
                output = [
                    'An error ocurred while trying to remove the auto-daily settings for this server.',
                    'Please try again or contact the bot\'s author.'
                ]
        await util.post_output(ctx, output)


@cmd_reset.command(brief='Reset pagination settings', name='pagination', aliases=['pages'])
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_reset_pagination(ctx: discord.ext.commands.Context):
    """Reset pagination for this server.

       You need the Administrator permission to use this command."""
    if ctx.channel.type == discord.ChannelType.text:
        async with ctx.typing():
            _ = server_settings.db_reset_use_pagination(ctx.guild.id)
            use_pagination_mode = server_settings.convert_to_on_off(server_settings.db_get_use_pagination(ctx.guild.id))
            output = [f'Pagination on this server is: {use_pagination_mode}']
        await util.post_output(ctx, output)










@cmd_settings.group(brief='Change server settings', name='set')
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_set(ctx: discord.ext.commands.Context):
    """Configure settings for this server.

       You need the Administrator permission to use any of these commands."""
    if ctx.channel.type != discord.ChannelType.text:
        await ctx.send('This command cannot be used in DMs or group chats, but only on Discord servers!')


@cmd_set.command(brief='Set auto-daily', name='autodaily', aliases=['daily'])
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_set_autodaily(ctx: discord.ext.commands.Context, text_channel: discord.TextChannel):
    """Set a channel to automatically post the daily announcement in at 1 am UTC.

       You need the Administrator permission to use this command."""
    if ctx.channel.type == discord.ChannelType.text:
        async with ctx.typing():
            if text_channel:
                success = daily.try_store_daily_channel(ctx.guild.id, text_channel.id)
                if success:
                    output = [f'Set auto-posting of the daily announcement to channel {text_channel.mention}.']
                else:
                    output = [
                        'Could not set auto-posting of the daily announcement for this server :(',
                        'Please try again or contact the bot\'s author.'
                    ]
            else:
                output = ['You need to provide a text channel!']
        await util.post_output(ctx, output)


@cmd_set.command(brief='Set pagination', name='pagination', aliases=['pages'])
@commands.has_permissions(administrator=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_set_pagination(ctx: discord.ext.commands.Context, switch: str = None):
    """Set pagination for this server.

       If the <switch> parameter is not set, this command will toggle the setting.
       Valid values for <switch> are:
       - Turning it on: on, true, yes, 1
       - Turning it off: off, false, no, 0
       Default is 'OFF'

       You need the Administrator permission to use this command."""
    if ctx.channel.type == discord.ChannelType.text:
        async with ctx.typing():
            if switch is not None:
                switch = util.convert_input_to_boolean(switch)
                result = server_settings.db_update_use_pagination(ctx.guild.id, switch)
            else:
                result = server_settings.toggle_use_pagination(ctx.guild.id)
            use_pagination_mode = server_settings.convert_to_on_off(result)
            output = [f'Pagination on this server is: {use_pagination_mode}']
        await util.post_output(ctx, output)










@bot.command(hidden=True, brief='These are testing commands, usually for debugging purposes')
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def test(ctx: discord.ext.commands.Context, action, *, params):
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


@bot.command(hidden=True)
@commands.is_owner()
async def updateschema(ctx: discord.ext.commands.Context):
    success = core.db_update_schema_v_1_2_2_0()
    if success:
        await ctx.send('Successfully updated db schema.')
    else:
        await ctx.send('An error ocurred while updating the db schema.')











# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    print(f'discord.py version: {discord.__version__}')
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
