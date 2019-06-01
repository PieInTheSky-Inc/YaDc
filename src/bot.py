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

import pss_core as core
import pss_daily as d
import pss_dropship as dropship
import pss_fleets as flt
import pss_market as mkt
import pss_prestige as p
import pss_research as rs
import pss_tournament as tourney
import utility as util


# ----- Setup ---------------------------------------------------------
RATE = 3
COOLDOWN = 30.0
USER_PSS_TOOLKIT = None

if "COMMAND_PREFIX" in os.environ:
    COMMAND_PREFIX=os.getenv('COMMAND_PREFIX')
else:
    COMMAND_PREFIX='/'

PWD = os.getcwd()
sys.path.insert(0, PWD + '/src/')

for folder in ['raw', 'data']:
    if not os.path.exists(folder):
        os.makedir(folder)

ACTIVITY = discord.Activity(type=discord.ActivityType.playing, name='/help')


# ----- Bot Setup -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    style = '{',
    datefmt = "%Y%m%d %H:%M:%S",
    format = "{asctime} [{levelname:<8}] {name}: {message}")

bot = commands.Bot(command_prefix=COMMAND_PREFIX,
                   description='This is a Discord Bot for Pixel Starships',
                   activity=ACTIVITY)

setattr(bot, "logger", logging.getLogger("bot.py"))


# ----- Bot Events ------------------------------------------------------------
@bot.event
async def on_ready():
    print(f'Current Working Directory: {PWD}')
    print(f'Bot prefix is: {COMMAND_PREFIX}')
    print('Bot logged in as {} (id={}) on {} servers'.format(
        bot.user.name, bot.user.id, len(bot.guilds)))
    game = discord.Game(name='for /help')
    core.init_db()
    bot.loop.create_task(post_dailies_loop())
    print('[on_ready] added task: post_dailies_loop()')


@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, commands.CommandOnCooldown):
        await ctx.send('Error: {}'.format(err))


# ----- Tasks ----------------------------------------------------------
async def post_dailies_loop():
    while True:
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        if utc_now.second != 0:
            await asyncio.sleep(60 - utc_now.second)
        else:
            await post_all_dailies(verbose=False, post_anyway=False)


async def post_all_dailies(verbose=False, post_anyway=False):
    utc_now = util.get_utcnow()
    utc_today = datetime.datetime(utc_now.year, utc_now.month, utc_now.day)
    configured_channel_count = len(d.get_all_daily_channels())
    if configured_channel_count > 0:
        old_dropship_txt = dropship.get_dropship_text(dropship.db_get_dropship_text_parts())
        dropship_txt, updated_parts_ids = dropship.get_and_update_auto_daily_text()
        if post_anyway or (dropship_txt and updated_parts_ids):
            print('[post_all_dailies] updated dropship text parts: {}'.format(updated_parts_ids))
            fix_daily_channels(verbose)
            valid_channels = d.get_valid_daily_channels()
            valid_channel_ids = [int(c[1]) for c in valid_channels]
            print('[post_all_dailies] post daily announcement to {} channels.'.format(len(valid_channel_ids)))
            txt = '__**{}h {}m**__ {}\n'.format(utc_now.hour, utc_now.minute, ', '.join(updated_parts_ids))
            for daily_channel in valid_channels: # daily_channel fields: 0 - guild_id; 1 - channel_id; 2 - can_post; 3 - latest_message_id
                text_channel = bot.get_channel(int(daily_channel[1]))
                if text_channel is not None:
                    guild = text_channel.guild
                    guild_member_bot = guild.get_member(bot.user.id)
                    old_msg = None
                    if daily_channel[3]:
                        try:
                            old_msg = await text_channel.fetch_message(daily_channel[3])
                        except Exception as error:
                            print('[post_all_dailies] {} occurred while trying to retrieve the latest message in channel \'{}\' on server \'{}\': {}'.format(error.__class__.__name__, text_channel.name, guild.name))
                    try:
                        if old_msg:
                            await old_msg.delete()
                        await text_channel.send(txt)
                        new_msg = await text_channel.send(dropship_txt)
                        updated_daily_channel = d.update_daily_channel(guild.id, latest_message_id=new_msg.id)
                        if not updated_daily_channel:
                            print('[post_all_dailies] could not update latest message id for channel \'{}\' on guild \'{}\': {}'.format(text_channel.name, guild.name, new_msg.id))
                    except Exception as error:
                        print('[post_all_dailies] {} occurred while trying to post to channel \'{}\' on server \'{}\''.format(error.__class__.__name__, text_channel.name, guild.name))
        elif verbose:
            print('dropship text hasn\'t changed.')
            
            
def fix_daily_channels(verbose=False):
    if verbose:
        print('+ called fix_daily_channels({})'.format(verbose))
    rows = d.get_all_daily_channels()
    if verbose:
        print('[fix_daily_channels] retrieved {} configured daily channels: {}'.format(len(rows), ', '.join(rows)))
    for row in rows:
        can_post = False
        guild_id = int(row[0])
        channel_id = int(row[1])
        text_channel = bot.get_channel(channel_id)
        if verbose:
            print('[fix_daily_channels] processing guild_id \'{}\', channel_id \'{}\', text_channel \'{}\''.format(guild_id, channel_id, text_channel))
        if text_channel is not None:
            guild = text_channel.guild
            if verbose:
                print('[fix_daily_channels] retrieved guild: {}'.format(guild))
            if guild is not None:
                guild_member = guild.get_member(bot.user.id)
                if verbose:
                    print('[fix_daily_channels] retrieved guild_member: {}'.format(guild_member))
                if guild_member is not None:
                    permissions = text_channel.permissions_for(guild_member)
                    if verbose:
                        print('[fix_daily_channels] retrieved permissions: \'{}\''.format(permissions))
                    if permissions is not None and permissions.send_messages:
                        if verbose:
                            print('[fix_daily_channels] bot can post in configured channel \'{}\' (id: {}) on server \'{}\' (id: {})'.format(text_channel.name, channel_id, guild.name, guild_id))
                        can_post = True
                    elif verbose:
                        print('[fix_daily_channels] bot is not allowed to post in configured channel \'{}\' (id: {}) on server \'{}\' (id: {})'.format(text_channel.name, channel_id, guild.name, guild_id))
                elif verbose:
                    print('[fix_daily_channels] couldn\'t fetch member for bot for guild: {} (id: {})'.format(guild.name, guild_id))
            elif verbose:
                print('[fix_daily_channels] couldn\'t fetch guild for channel \'{}\' (id: {}) with id: {}'.format(text_channel.name, channel_id, guild_id))
        elif verbose:
            print('[fix_daily_channels] couldn\t fetch channel with id: {}'.format(channel_id))
        d.fix_daily_channel(guild_id, can_post)


# ----- General Bot Commands ----------------------------------------------------------
@bot.command(brief='Ping the server')
async def ping(ctx):
    """Ping the server to verify that it\'s listening for commands"""
    async with ctx.typing():
        await ctx.send('Pong!')

    
@bot.command(hidden=True, brief='Run shell command')
@commands.is_owner()
async def shell(ctx, *, cmd):
    """Run a shell command"""
    async with ctx.typing():
        txt = util.shell_cmd(cmd)
        await ctx.send(txt)


# ----- PSS Bot Commands --------------------------------------------------------------
@bot.command(brief='Get prestige combos of crew')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def prestige(ctx, *, name):
    """Get the prestige combinations of the character specified"""
    async with ctx.typing():
        prestige_txt, success = p.get_prestige(name, 'from')
        for txt in prestige_txt:
            await ctx.send(txt)
        

@bot.command(brief='Get character recipes')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def recipe(ctx, *, name=''):
    """Get the prestige recipes of a character"""
    async with ctx.typing():
        if name.startswith('--raw '):
            name = re.sub('^--raw[ ]+', '', name)
            prestige_txt, success = p.get_prestige(name, 'to', raw=True)
        else:
            prestige_txt, success = p.get_prestige(name, 'to', raw=False)
        if success is True:
            for txt in prestige_txt:
                await ctx.send(txt)
        else:
            await ctx.send(f'Failed to find a recipe for crew "{name}" (note that item recipes now use the `/ingredients` command)')


@bot.command(brief='Get item ingredients')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def ingredients(ctx, *, name=None):
    """Get the ingredients for an item"""
    async with ctx.typing():
        content, real_name = mkt.get_item_recipe(name, levels=5)
        if real_name is not None:
            content = '**Ingredients for {}**\n'.format(real_name) + content
            content = content + '\n\nNote: bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons'
            await ctx.send(content)
            recipe_found = True


@bot.command(brief='Get item\'s market prices and fair prices from the PSS API', aliases=['fairprice'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def price(ctx, *, item_name=None):
    """Get the average price (market price) and the Savy price (fair price) in bux of the item(s) specified, as returned by the PSS API. Note that prices returned by the API may not reflect the real market value, due to transfers between alts/friends"""
    async with ctx.typing():
        raw_text = mkt.load_item_design_raw()
        item_lookup = mkt.parse_item_designs(raw_text)
        real_name = mkt.get_real_name(item_name, item_lookup)
        if len(item_name) < 2 and real_name != 'U':
            await ctx.send("Please enter at least two characters for item name")
        elif real_name is not None:
            item_list = mkt.filter_item_designs(item_name, item_lookup, filter='price')
            item_name_column_width = item_list.index('|') - 1
            market_txt = "__Prices matching '{}'__```\n".format(item_name)
            market_txt += '{} | Market price | Savy fair price\n'.format('Item name'.ljust(item_name_column_width))
            market_txt += '{}-+--------------+----------------\n'.format(''.ljust(item_name_column_width, '-'))
            market_txt += item_list
            market_txt += '\n```**Note:** Market prices listed here may not always be accurate due to transfers between alts/friends or other reasons.'
            await ctx.send(market_txt)
        else:
            await ctx.send("Could not find item name '{}'".format(item_name))


@bot.command(name='list', brief='List items/characters')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def list(ctx, *, action=''):
    """action=crew:  shows all characters
    action=newcrew:  shows the newest 10 characters that have been added to the game
    action=items:    shows all items
    action=research: shows all research
    action=rooms:    shows all rooms
    action=missiles: shows all missiles"""

    async with ctx.typing():
        txt_list = []
        if action in ['chars', 'characters', 'crew', 'newchars', 'newcrew']:
            txt_list = p.get_char_list(action)
        elif action == 'items':
            txt_list = mkt.get_item_list()
        elif action == 'research':
            txt_list = rs.get_research_names()
        elif action == 'rooms':
            txt_list = rs.get_room_names()
        elif action == 'missiles':
            txt_list = rs.get_missile_names()

        for txt in txt_list:
            await ctx.send(txt)


@bot.command(name='stats', aliases=['char', 'item'], brief='Get item/character stats')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stats(ctx, *, name=''):
    """Get the stats of a character/crew or item"""
    async with ctx.typing():
        if len(name) == 0:
            return
        # First try to find a character match
        # (skip this section if command was invoked with 'item'
        if ctx.invoked_with != 'item':
            if name.startswith('--raw '):
                name = re.sub('^--raw[ ]+', '', name)
                result = p.get_stats(name, embed=False, raw=True)
            else:
                result = p.get_stats(name, embed=False, raw=False)
            if result is not None:
                await ctx.send(result)
                found_match = True

        # Next try to find an item match
        if ctx.invoked_with != 'char':
            market_txt = mkt.get_item_stats(name)
            if market_txt is not None:
                await ctx.send(market_txt)
                found_match = True

        if found_match is False:
            await ctx.send('Could not find entry for "{}"'.format(name))


@bot.command(brief='Get best items for a slot')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def best(ctx, slot=None, enhancement=None):
    """Get the best enhancement item for a given slot. If multiple matches are found, matches will be shown in descending order."""
    async with ctx.typing():
        raw_text = mkt.load_item_design_raw()
        item_lookup = mkt.parse_item_designs(raw_text)
        df_items = mkt.rtbl2items(item_lookup)
        df_filter = mkt.filter_item(
            df_items, slot, enhancement,
            cols=['ItemDesignName', 'EnhancementValue', 'MarketPrice'])

        txt = mkt.itemfilter2txt(df_filter)
        if txt is None:
            await ctx.send('No entries found for {} slot, {} enhancement'.format(
                slot, enhancement))

            str_slots = ', '.join(df_items['ItemSubType'].value_counts().index)
            str_enhancements = ', '.join(df_items['EnhancementType'].value_counts().index)
            txt  = 'Slots: {}\n'.format(str_slots)
            txt += 'Enhancements: {}'.format(str_enhancements)
            await ctx.send(txt)
        else:
            await ctx.send(txt)


@bot.command(brief='Get research data')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def research(ctx, *, research=''):
    """Get the research details on a specific research. If multiple matches are found, only a brief summary will be provided"""
    async with ctx.typing():
        df_research_designs = rs.get_research_designs()
        df_selected = rs.filter_researchdf(df_research_designs, research)
        txt = rs.research_to_txt(df_selected)
        if txt is None:
            await ctx.send("No entries found for '{}'".format(research))
        else:
            await ctx.send(txt)


@bot.command(brief='Get collections')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def collection(ctx, *, collection=None):
    """Get the details on a specific collection."""
    async with ctx.typing():
        txt = p.show_collection(collection)
        if txt is None:
            await ctx.send("No entries found for '{}'".format(collection))
        else:
            await ctx.send(txt)


@bot.command(brief='Division stars (works only during tournament finals)')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stars(ctx, *, division=None):
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
    async with ctx.typing():
        txt = dropship.get_dropship_text()
        await ctx.message.delete()
        await ctx.send(txt)


@bot.command(hidden=True, brief='Configure auto-posting the daily announcement for the current server.')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@commands.has_permissions(administrator=True)
async def autodaily(ctx, action: str, text_channel: discord.TextChannel = None):
    """
    This command can be used to configure the bot to automatically post the daily announcement at 1 am UTC to a certain text channel.
    The daily announcement is the message that this bot will post, when you use the /daily command.
    
    action = set:    Configure a channel on this server to have the daily announcement posted at.
    action = remove: Stop auto-posting the daily announcement to this Discord server.
    action = get:    See which channel has been configured on this server to receive the daily announcement.
    
    In order to use this command, you need Administrator permissions for this server.
    """
    guild = ctx.guild
    author_is_owner = await bot.is_owner(ctx.author)
    txt = ''
    if action == 'set':
        if text_channel is None:
            await ctx.send('You need to specify a text channel!')
        else:
            await setdaily(ctx, text_channel)
    elif action == 'remove':
        await removedaily(ctx)
    elif action == 'get':
        await getdaily(ctx)
    elif action == 'fix':
        if author_is_owner:
            fix_daily_channels()
            await ctx.send('Fixed daily channels')
    elif action == 'listall':
        if author_is_owner:
            await listalldailies(ctx, None)
    elif action == 'listvalid':
        if author_is_owner:
            await listalldailies(ctx, True)
    elif action == 'listinvalid':
        if author_is_owner:
            await listalldailies(ctx, False)
    elif action == 'post':
        if author_is_owner:
            guild = ctx.guild
            channel_id = d.get_daily_channel_id(guild.id)
            if channel_id >= 0:
                text_channel = bot.get_channel(channel_id)
                await text_channel.send(dropship.get_dropship_text())
    elif action == 'postall':
        if author_is_owner:
            await post_all_dailies(verbose=True, post_anyway=True)
                

async def setdaily(ctx, text_channel: discord.TextChannel):
    guild = ctx.guild
    success = d.try_store_daily_channel(guild.id, text_channel.id)
    if success:
        txt = 'Set auto-posting of the daily announcement to channel {}.'.format(text_channel.mention)
    else:
        txt = 'Could not set auto-posting of the daily announcement for this server :('
    await ctx.send(txt)

async def getdaily(ctx):
    guild = ctx.guild
    channel_id = d.get_daily_channel_id(guild.id)
    txt = ''
    if channel_id >= 0:
        text_channel = bot.get_channel(channel_id)
        txt += 'The daily announcement will be auto-posted at 1 am UTC in channel {}.'.format(text_channel.mention)
    else:
        txt += 'Auto-posting of the daily announcement is not configured for this server!'
    await ctx.send(txt)

async def listalldailies(ctx, valid = None):
    channels = d.select_daily_channel(None, valid)
    txt = ''
    i = 0
    for channel in channels:
        text_channel = bot.get_channel(int(channel[1]))
        guild = text_channel.guild
        txt += '{}: #{} ({})\n'.format(guild.name, text_channel.name, channel[2])
        if i == 20:
            txt += '\n'
            i = 0
    if txt == '':
        await ctx.send('No servers have been configurated to use the autodaily feature.')
    else:
        txt_split = txt.split('\n\n')
        for msg in txt_split:
            await ctx.send(msg)
        
async def removedaily(ctx):
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
    

@autodaily.error
async def autodaily_error(ctx, error):
    if isinstance(error, commands.ConversionError) or isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('You need to pass an action channel to the `{}autodaily` command!'.format(COMMAND_PREFIX))
    elif isinstance(error, commands.CheckFailure):
        await ctx.send('You need the permission `Administrator` in order to be able to use this command!')


@bot.command(brief='Get crew levelling costs')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def level(ctx, level):
    """Shows the cost for a crew to reach a certain level. Replace <level> with a value between 2 and 40"""
    async with ctx.typing():
        txt = p.get_level_cost(level)
        await ctx.send(txt)


@bot.command(hidden=True, brief='(beta) Get room infos')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def roomsbeta(ctx, *, room_name=None):
    """(beta) Shows the information for specific room types. This command is currently under testing"""
    async with ctx.typing():
        txt = rs.get_room_description(room_name)
        await ctx.send(txt)


@bot.command(hidden=True, brief='(beta) Get missile info')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def missilebeta(ctx, *, missile_name=None):
    """(beta) Shows the information for specific missile types. This command is currently under testing"""
    async with ctx.typing():
        txt = rs.get_missile_description(missile_name)
        await ctx.send(txt)


@bot.command(brief='Get PSS stardate & Melbourne time')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def time(ctx):
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
        txt = core.read_links_file()
        await ctx.send(txt)


@bot.command(hidden=True, aliases=['unquote'], brief='Quote/unquote text')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def quote(ctx, *, txt=''):
    """Quote or unquote text"""
    async with ctx.typing():
        txt = core.parse_unicode(txt, str(ctx.invoked_with))
        await ctx.send(txt)


@bot.command(hidden=True, brief='Parse URL')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def parse(ctx, *, url):
    """Parses the data from a URL"""
    async with ctx.typing():
        txt_list = core.parse_links3(url)
        for txt in txt_list:
            await ctx.send(txt)
            
            
@bot.group(brief='Get tournament information', aliases=['tourney'])
@commands.cooldown(rate=RATE*10, per=COOLDOWN, type=commands.BucketType.channel)
async def tournament(ctx):
    """Get information about the monthly tournament"""
    print('+ called command tournament(ctx)')
    print(f'ctx.invoked_subcommand: {ctx.invoked_subcommand}')
    print(f'ctx.invoked_subcommand is None: {ctx.invoked_subcommand is None}')
    print(f'ctx.subcommand_passed: {ctx.subcommand_passed}')
    print(f'ctx.subcommand_passed is None: {ctx.subcommand_passed is None}')
    if ctx.invoked_subcommand is None:
        try:
            await ctx.invoke(command='tournament current')
        except Exception as error:
            print(f'[tournament] {error.__class__.__name__} occurred with string: {error}')
        try:
            await ctx.invoke(command='tournament current')
        except Exception as error:
            print(f'[tournament] {error.__class__.__name__} occurred with delegate: {error}')
        try:
            for cmd in bot.commands:
                print(f'[tournament] current command: {cmd.name}')
                if cmd.name == 'tournament current':
                    print(f'[tournament] invoking command \'tournament current \'')
                    await ctx.invoke(command=cmd)
        except Exception as error:
            print(f'[tournament] {error.__class__.__name__} occurred with commands set: {error}')


@tournament.command(name='current')
async def tournament_current(ctx):
    """Get information about the current month's tournament"""
    print('+ called command tournament_current(ctx)')
    utc_now = util.get_utcnow()
    start_of_tourney = tourney.get_current_tourney_start()
    print(f'[tournament current] Retrieved current tourney start: {start_of_tourney}')
    txt = tourney.format_tourney_start(start_of_tourney, utc_now)
    print(f'[tournament current] Retrieved output: {txt}')
    await ctx.send(txt)
    
    
@tournament.command(name='next')
async def tournament_next(ctx):
    """Get information about the next month's tournament"""
    print('+ called command tournament_next(ctx)')
    utc_now = util.get_utcnow()
    start_of_tourney = tourney.get_next_tourney_start()
    print(f'[tournament next] Retrieved next tourney start: {start_of_tourney}')
    txt = tourney.format_tourney_start(start_of_tourney, utc_now)
    print(f'[tournament next] Retrieved output: {txt}')
    await ctx.send(txt)


@bot.command(hidden=True,
    brief='These are testing commands, usually for debugging purposes')
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def testing(ctx, *, action=None):
    """These are testing commands, usually for debugging purposes"""
    if action == 'restart':
        await ctx.send('Bot will attempt a restart')
    elif action == 'info':
        guild = ctx.guild  # server = ctx.server
        author = ctx.author
        channel = ctx.channel
        txt = 'Server (Guild): {} (id={})\n'.format(guild, guild.id)
        txt += 'Author: {} (id={})\n'.format(author, author.id)
        txt += 'Channel: {} (id={})\n'.format(channel, channel.id)
        txt += 'Discord.py version: {}'.format(discord.__version__)
        await ctx.send(txt)
    elif action[:3] == 'say':
        txt = action[3:]
        await ctx.send(txt)
    elif action == 'guilds':
        guilds = bot.guilds
        txt_list = []
        txt = ''
        for i, guild in enumerate(guilds):
            owner = str(guild.owner)
            txt1 = '{}. {}: {} ({}, owner - {})\n'.format(
                i+1, guild.id, guild.name, guild.region, owner)
            if len(txt + txt1) > 1900:
                await ctx.send(txt + txt1)
                txt = ''
            else:
                txt = txt + txt1
        await ctx.send(txt)
    elif action == 'invite':
        txt = '{}'.format(bot.get_invite())
        await ctx.send(txt)
    elif action == 'invoked':
        txt  = 'ctx.prefix = `{}`\n'.format(ctx.prefix)
        txt += 'ctx.invoke = `{}`\n'.format(ctx.invoke)
        txt += 'ctx.invoked_subcommand = `{}`\n'.format(ctx.invoked_subcommand)
        txt += 'ctx.invoked_with = `{}`\n'.format(ctx.invoked_with)
        txt += 'ctx.invoked_with methods: `{}`'.format(dir(ctx.invoked_with))
        await ctx.send(txt)
    elif action == 'actions':
        txt = 'bot methods: `{}`'.format(dir(bot))
        await ctx.send(txt)
    elif action[:4] == 'doc ':
        # /testing doc ctx.invoke
        txt = '{}'.format(dir(action[4:]))
        exec(txt)
        await ctx.send(f'`{txt}`')
    elif action[:5] == 'exec ':
        # /testing exec print(dir(ctx.invoke))
        # /testing exec print(ctx.invoke)
        # /testing exec help(ctx.invoke)
        # /testing exec print('{}{}'.format(ctx.prefix,ctx.command))
        exec(action[5:])
    # elif action in ['ctx', 'ctx.author', 'ctx.bot', 'ctx.channel',
    #                 'ctx.guild', 'ctx.message']:
    #     txt = 'format(dir({})))'.format(action)
    #     txt = 'print("{}".' + txt
    #     exec(txt)
    elif action[:4] == 'sql ':
        cmd = action[4:]
        p.custom_sqlite_command(cmd)
        await ctx.send('Executing SQL Command: "{}"'.format(cmd))
    elif action == 'ctx':
        txt = 'ctx methods: `{}`'.format(dir(ctx))
        await ctx.send(txt)
    elif action == 'ctx.author':
        txt = 'ctx.author methods: `{}`'.format(dir(ctx.author))
        await ctx.send(txt)
    elif action == 'ctx.bot':
        txt = 'ctx.bot methods: `{}`'.format(dir(ctx.bot))
        await ctx.send(txt)
    elif action == 'ctx.channel':
        txt = 'ctx.channel methods: `{}`'.format(dir(ctx.channel))
        await ctx.send(txt)
    elif action == 'ctx.guild':
        txt = 'ctx.guild methods: `{}`'.format(dir(ctx.guild))
        await ctx.send(txt)
    elif action == 'ctx.message':
        txt = 'ctx.message methods: `{}`'.format(dir(ctx.guild))
        await ctx.send(txt)

    await ctx.message.delete()  # await bot.delete_message(ctx.message)
    if action == 'restart':
        txt = 'Bot is now attempting to restart'
        print(txt)
        bot.close()
        quit()
    

@bot.command(hidden=True, brief='These are testing commands, usually for debugging purposes')
@commands.is_owner()
@commands.cooldown(rate=2*RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def test(ctx, action, *, params=None):
    print(f'+ called command test(ctx, {action}, {params}) by {ctx.author}')
    if action == 'utcnow':
        utcnow = util.get_utcnow()
        txt = util.get_formatted_datetime(utcnow)
        await ctx.send(txt)
    elif action == 'init':
        core.init_db(True)
        await ctx.send('Initialized the database from scratch')
        await ctx.message.delete()
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
    elif action == 'embed':
        bot_member = ctx.guild.get_member(bot.user.id)
        print(f'[test] retrieved bot guild member: {bot_member}')
        bot_colour = bot_member.colour
        print(f'[test] retrieved bot guild colour: {bot_colour}')
        txt = params
        if txt is None:
            txt = 'Text'
        print(f'[test] retrieved text: {txt}')
        titl = 'Title'
        desc = 'Description'
        embe = discord.Embed(title=titl, description=desc, colour=bot_colour)
        print(f'[test] created embed: {embe}')
        embe.add_field(name='Field title', value=txt)
        print(f'[test] added field to embed.')
        await ctx.send(embed=embe)


# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
