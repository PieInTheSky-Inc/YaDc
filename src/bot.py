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
import pss_exception
import pss_core as core
import pss_crew as crew
import pss_daily as d
import pss_dropship as dropship
import pss_exception
import pss_fleets as flt
import pss_item as item
import pss_lookups as lookups
import pss_research as research
import pss_room as room
import pss_tournament as tourney
import pss_top
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
    elif isinstance(err, pss_exception.Error):
        logging.getLogger().error(err, exc_info=True)
        await ctx.send(f'`{ctx.message.clean_content}`: {err.msg}')
    else:
        logging.getLogger().error(err, exc_info=True)
        await ctx.send('Error: {}'.format(err))


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
    channel_ids = d.get_valid_daily_channel_ids()
    output, _ = dropship.get_dropship_text()
    for channel_id in channel_ids:
        text_channel = bot.get_channel(channel_id)
        if text_channel != None:
            guild = text_channel.guild
            try:
                if output:
                    posts = util.create_posts_from_lines(output, core.MAXIMUM_CHARACTERS)
                    for post in posts:
                        await text_channel.send(post)
            except Exception as error:
                print('[post_all_dailies] {} occurred while trying to post to channel \'{}\' on server \'{}\': {}'.format(error.__class__.__name__, text_channel.name, guild.name, error))


def fix_daily_channels():
    rows = d.select_daily_channel(None, None)
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
        d.fix_daily_channel(guild_id, can_post)


# ----- General Bot Commands ----------------------------------------------------------
@bot.command(brief='Ping the server')
async def ping(ctx):
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
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Get character recipes')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def recipe(ctx: discord.ext.commands.Context, *, char_name=None):
    """Get the prestige recipes of a character"""
    async with ctx.typing():
        output, _ = crew.get_prestige_to_info(char_name)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Get item ingredients', aliases=['ing'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def ingredients(ctx: discord.ext.commands.Context, *, name=None):
    """Get the ingredients for an item"""
    async with ctx.typing():
        output, _ = item.get_ingredients_for_item(name)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Get crafting recipes', aliases=['upg'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def upgrade(ctx: discord.ext.commands.Context, *, item_name=None):
    """Returns any crafting recipe involving the requested item."""
    async with ctx.typing():
        output, _ = item.get_item_upgrades_from_name(item_name)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Get item\'s market prices and fair prices from the PSS API', aliases=['fairprice', 'cost'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def price(ctx: discord.ext.commands.Context, *, item_name=None):
    """Get the average price (market price) and the Savy price (fair price) in bux of the item(s) specified, as returned by the PSS API. Note that prices returned by the API may not reflect the real market value, due to transfers between alts/friends"""
    async with ctx.typing():
        output, _ = item.get_item_price(item_name)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


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

    if char_success and char_output:
        await util.post_output(ctx, char_output, core.MAXIMUM_CHARACTERS)

    if item_success and item_output:
        if char_success:
            await ctx.send(core.EMPTY_LINE)
        await util.post_output(ctx, item_output, core.MAXIMUM_CHARACTERS)

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
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(name='item', brief='Get item stats')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_item(ctx: discord.ext.commands.Context, *, item_name):
    """Get the stats of an item."""
    async with ctx.typing():
        output, _ = item.get_item_details(item_name)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


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
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(name='research', brief='Get research data')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_research(ctx: discord.ext.commands.Context, *, name: str = None):
    """Get the research details on a specific research. If multiple matches are found, only a brief summary will be provided"""
    async with ctx.typing():
        output, _ = research.get_research_details_from_name(name)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Get collections')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def collection(ctx: discord.ext.commands.Context, *, collection_name=None):
    """Get the details on a specific collection."""
    async with ctx.typing():
        output, _ = crew.get_collection_info(collection_name)
    if output:
        posts = util.create_posts_from_lines(output, core.MAXIMUM_CHARACTERS)
        for post in posts:
            await ctx.send(post)


@bot.command(brief='Division stars (works only during tournament finals)')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stars(ctx: discord.ext.commands.Context, *, division=None):
    """Get stars earned by each fleet during final tournament week. Replace [division] with a division name (a, b, c or d)"""
    async with ctx.typing():
        txt = flt.get_division_stars(division)
    txt_split = txt.split('\n\n')
    for division_list in txt_split:
        await ctx.send(division_list)


@bot.command(hidden=True, brief='Show the dailies')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def daily(ctx):
    """Show the dailies"""
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = dropship.get_dropship_text()
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Show the news')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def news(ctx):
    """Show the news"""
    await util.try_delete_original_message(ctx)
    async with ctx.typing():
        output, _ = dropship.get_news()
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.group(hidden=True, brief='Configure auto-posting the daily announcement for the current server.')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily(ctx):
    """
    This command can be used to configure the bot to automatically post the daily announcement at 1 am UTC to a certain text channel.
    The daily announcement is the message that this bot will post, when you use the /daily command.

    In order to use this command, you need Administrator permissions for this server.
    """
    pass


@autodaily.command(name='fix', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_fix(ctx):
    fix_daily_channels()
    await ctx.send('Fixed daily channels')


@autodaily.command(name='set', brief='Set an autodaily channel.')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_set(ctx: discord.ext.commands.Context, text_channel: discord.TextChannel):
    """Configure a channel on this server to have the daily announcement posted at."""
    if text_channel:
        guild = ctx.guild
        success = d.try_store_daily_channel(guild.id, text_channel.id)
        if success:
            txt = 'Set auto-posting of the daily announcement to channel {}.'.format(text_channel.mention)
        else:
            txt = 'Could not set auto-posting of the daily announcement for this server :('
        await ctx.send(txt)


@autodaily.command(name='get', brief='Get the autodaily channel.')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_get(ctx):
    """See which channel has been configured on this server to receive the daily announcement."""
    guild = ctx.guild
    channel_id = d.get_daily_channel_id(guild.id)
    txt = ''
    if channel_id >= 0:
        text_channel = bot.get_channel(channel_id)
        if text_channel:
            channel_name = text_channel.mention
        else:
            channel_name = '_deleted channel_'
        txt += 'The daily announcement will be auto-posted at 1 am UTC in channel {}.'.format(channel_name)
    else:
        txt += 'Auto-posting of the daily announcement is not configured for this server!'
    await ctx.send(txt)


@autodaily.group(name='list', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list(ctx):
    pass


@autodaily_list.command(name='all', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list_all(ctx):
    channels = d.select_daily_channel(None, None)
    txt = ''
    i = 0
    for channel in channels:
        text_channel = bot.get_channel(int(channel[1]))
        if text_channel:
            guild = text_channel.guild
            txt += '{}: #{} ({})\n'.format(guild.name, text_channel.name, channel[2])
            if i == 20:
                txt += '\n'
                i = 0
        else:
            txt += f'Invalid channel id: {channel[1]}'
    txt_split = txt.split('\n\n')
    if txt_split:
        for msg in txt_split:
                await ctx.send(msg)
    else:
        ctx.send('Auto-posting of the daily announcement is not configured for any server!')


@autodaily_list.command(name='invalid', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list_invalid(ctx):
    channels = d.select_daily_channel(None, False)
    txt = ''
    i = 0
    for channel in channels:
        text_channel = bot.get_channel(int(channel[1]))
        if text_channel:
            guild = text_channel.guild
            txt += '{}: #{} ({})\n'.format(guild.name, text_channel.name, channel[2])
            if i == 20:
                txt += '\n'
                i = 0
        else:
            txt += f'Invalid channel id: {channel[1]}'
    txt_split = txt.split('\n\n')
    if txt_split:
        for msg in txt_split:
                await ctx.send(msg)
    else:
        ctx.send('Auto-posting of the daily announcement is not configured for any server!')


@autodaily_list.command(name='valid', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_list_valid(ctx):
    channels = d.select_daily_channel(None, True)
    txt = ''
    i = 0
    for channel in channels:
        text_channel = bot.get_channel(int(channel[1]))
        if text_channel:
            guild = text_channel.guild
            txt += '{}: #{} ({})\n'.format(guild.name, text_channel.name, channel[2])
            if i == 20:
                txt += '\n'
                i = 0
        else:
            txt += f'Invalid channel id: {channel[1]}'
    txt_split = txt.split('\n\n')
    if txt_split:
        for msg in txt_split:
                await ctx.send(msg)
    else:
        ctx.send('Auto-posting of the daily announcement is not configured for any server!')


@autodaily.command(name='remove', brief='Turn off autodaily feature for this server.')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_remove(ctx):
    """Stop auto-posting the daily announcement to this Discord server"""
    guild = ctx.guild
    txt = ''
    channel_id = d.get_daily_channel_id(guild.id)
    if channel_id >= 0:
        if d.try_remove_daily_channel(guild.id):
            txt += 'Removed auto-posting the daily announcement from this server.'
        else:
            txt += 'Could not remove auto-posting the daily announcement from this server.'
    else:
        txt += 'Auto-posting of the daily announcement is not configured for this server!'
    await ctx.send(txt)


@autodaily.command(name='post', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_post(ctx):
    guild = ctx.guild
    channel_id = d.get_daily_channel_id(guild.id)
    if channel_id >= 0:
        text_channel = bot.get_channel(channel_id)
        output, _ = dropship.get_dropship_text()
        if output:
            posts = util.create_posts_from_lines(output, core.MAXIMUM_CHARACTERS)
            for post in posts:
                if post:
                    await text_channel.send(post)


@autodaily.command(name='postall', hidden=True)
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily_postall(ctx):
    await util.try_delete_original_message(ctx)
    await post_all_dailies()


@autodaily.error
async def autodaily_error(ctx: discord.ext.commands.Context, error):
    if isinstance(error, commands.ConversionError) or isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('You need to pass an action channel to the `{}autodaily` command!'.format(COMMAND_PREFIX))
    elif isinstance(error, commands.CheckFailure):
        await ctx.send('You need the permission `Administrator` in order to be able to use this command!')


@bot.command(brief='Get crew levelling costs', aliases=['lvl'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def level(ctx: discord.ext.commands.Context, from_level: int = None, to_level: int = None):
    """Shows the cost for a crew to reach a certain level.
       Parameter from_level is required to be lower than to_level
       If only from_level is being provided, it will print out costs from level 1 to from_level"""
    async with ctx.typing():
        output, _ = crew.get_level_costs(from_level, to_level)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


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
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)
    else:
        await ctx.send(f'Could not get top {count} fleets.')


@top.command(name='captains', brief='Prints top captains', aliases=['players', 'users'])
async def top_captains(ctx: discord.ext.commands.Context, count: int = 100):
    """Prints top fleets."""
    async with ctx.typing():
        output, _ = pss_top.get_top_captains(count)
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)
    else:
        await ctx.send(f'Could not get top {count} captains.')


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
    if output:
        await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Get PSS stardate & Melbourne time', name='time')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def cmd_time(ctx):
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
async def links(ctx):
    """Shows the links for useful sites in Pixel Starships"""
    async with ctx.typing():
        output = core.read_links_file()
    await util.post_output(ctx, output, core.MAXIMUM_CHARACTERS)


@bot.command(brief='Display info on this bot')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def about(ctx):
    """Displays information on this bot and its authors."""
    async with ctx.typing():
        result = core.read_about_file()
    await ctx.send(result)


@bot.group(brief='Information on tournament time', aliases=['tourney'])
@commands.cooldown(rate=RATE*10, per=COOLDOWN, type=commands.BucketType.channel)
async def tournament(ctx):
    """Get information about the time of the tournament.
       If this command is called without a sub command, it will display
       information about the time of the current month's tournament."""
    if ctx.invoked_subcommand is None:
        cmd = bot.get_command('tournament current')
        await ctx.invoke(cmd)


@tournament.command(brief='Information on this month\'s tournament time', name='current')
async def tournament_current(ctx):
    """Get information about the time of the current month's tournament."""
    async with ctx.typing():
        utc_now = util.get_utcnow()
        start_of_tourney = tourney.get_current_tourney_start()
        embed_colour = util.get_bot_member_colour(bot, ctx.guild)
        embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@tournament.command(brief='Information on next month\'s tournament time', name='next')
async def tournament_next(ctx):
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
async def updatecache(ctx):
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
    elif action == 'options':
        async with ctx.typing():
            count = 10
            if params:
                count = int(params)
            if count > 10:
                count = 10
            available_options = dict({emoji: i + 1 for i, emoji in enumerate(emojis.options[:count])})
            options = [f'{emoji}: {i}' for emoji, i in available_options.items()]
            content = "\n".join(options)
            content = f'```{content}```'

        message = await ctx.send(content)
        await wait_for_option_selection(ctx, message, available_options)





# ---------- Check functions ----------

async def wait_for_option_selection(ctx: discord.ext.commands.Context, option_message: discord.Message, available_options: dict) -> str:
    def option_selection_check(reaction: discord.Reaction, user: discord.User):
        if user == ctx.author:
            emoji = str(reaction.emoji)
            if emoji in available_options.keys() or emoji == emojis.page_stop:
                return True
        else:
            reaction.remove(user)
            return False

    await option_message.add_reaction(emojis.page_stop)
    for option in available_options.keys():
        await option_message.add_reaction(option)

    try:
        reaction, _ = await bot.wait_for('reaction_add', timeout=60.0, check=option_selection_check)
    except asyncio.TimeoutError:
        await option_message.delete()
        await ctx.send('You\'ve waited for too long to answer :(')
    else:
        await option_message.delete()
        emoji = str(reaction.emoji)
        if emoji != emojis.page_stop:
            await ctx.send(f'You selected option {emoji}: {available_options[emoji]}')





# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
