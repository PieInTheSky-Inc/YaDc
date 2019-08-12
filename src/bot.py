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
import os
import pytz
import re
import sys
import time

import pss_core as core
import pss_crew as crew
import pss_data as data
import pss_daily as d
import pss_dropship as dropship
import pss_fleets as flt
import pss_market as mkt
import pss_research as rs
#import pss_toolkit as toolkit
import pss_tournament as tourney
import utility as util


# ----- Setup ---------------------------------------------------------
RATE = 5
COOLDOWN = 20.0

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
    core.init_db()
    bot.loop.create_task(post_dailies_loop())


@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, commands.CommandOnCooldown):
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
    txt = dropship.get_dropship_text()
    for channel_id in channel_ids:
        text_channel = bot.get_channel(channel_id)
        if text_channel != None:
            guild = text_channel.guild
            try:
                await text_channel.send(txt)
            except Exception as error:
                print('[post_all_dailies] {} occurred while trying to post to channel \'{}\' on server \'{}\': {}'.format(error.__class__.__name__, text_channel.name, guild.name))


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
async def prestige(ctx, *, char_name):
    """Get the prestige combinations of the character specified"""
    async with ctx.typing():
        prestige_txt = crew.get_prestige_from_info(char_name, as_embed=False)
        await ctx.send(prestige_txt)


@bot.command(brief='Get character recipes')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def recipe(ctx, *, char_name=''):
    """Get the prestige recipes of a character"""
    async with ctx.typing():
        prestige_txt = crew.get_prestige_to_info(char_name, as_embed=False)
        await ctx.send(prestige_txt)


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
            market_txt = "__**Prices matching '{}'**__\n\n".format(item_name)
            market_txt += mkt.filter_item_designs(item_name, item_lookup, filter='price')
            market_txt += '\n\n**Note:** 1st price is the market price. 2nd price is Savy\'s fair price. Market prices listed here may not always be accurate due to transfers between alts/friends or other reasons.'
            await ctx.send(market_txt)
        else:
            await ctx.send("Could not find item name '{}'".format(item_name))


@bot.command(name='stats', aliases=['char', 'item'], brief='Get item/character stats')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stats(ctx, *, name=''):
    """Get the stats of a character/crew or item"""
    if len(name) == 0:
        return
    # First try to find a character match
    # (skip this section if command was invoked with 'item'
    async with ctx.typing():
        if ctx.invoked_with != 'item':
            result = crew.get_char_info(name)
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
async def collection(ctx, *, collection_name=None):
    """Get the details on a specific collection."""
    async with ctx.typing():
        txt = crew.get_collection_info(collection_name, as_embed=False)
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


@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@bot.command(hidden=True, brief='Show the dailies')
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
        if text_channel == None:
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
            await post_all_dailies()


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


@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@bot.command(hidden=True, brief='(beta) Get room infos')
async def roomsbeta(ctx, *, room_name=None):
    """(beta) Shows the information for specific room types. This command is currently under testing"""
    async with ctx.typing():
        txt = rs.get_room_description(room_name)
        await ctx.send(txt)


@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@bot.command(hidden=True, brief='(beta) Get missile info')
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
    utc_now = util.get_utcnow()
    start_of_tourney = tourney.get_current_tourney_start()
    embed_colour = util.get_bot_member_colour(bot, ctx.guild)
    embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


@tournament.command(brief='Information on next month\'s tournament time', name='next')
async def tournament_next(ctx):
    """Get information about the time of next month's tournament."""
    utc_now = util.get_utcnow()
    start_of_tourney = tourney.get_next_tourney_start()
    embed_colour = util.get_bot_member_colour(bot, ctx.guild)
    embed = tourney.embed_tourney_start(start_of_tourney, utc_now, embed_colour)
    await ctx.send(embed=embed)


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
async def test(ctx, action, *, params):
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


#@bot.command(hidden=True, brief='Get fleet details', aliases=['fleet'])
#@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
#async def alliance(ctx, *, fleet_name=None):
#    """Gets a spreadsheet containing current data on the specified fleet"""
#    await toolkit.get_fleet_spreadsheet(ctx, fleet_name)


# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
