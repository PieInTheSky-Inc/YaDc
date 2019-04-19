from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from discord.ext import commands
from dateutil.relativedelta import relativedelta

import datetime
import discord
import holidays
import logging
import os
import pss_core as core
import pss_dropship as dropship
import pss_fleets as flt
import pss_market as mkt
import pss_prestige as p
import pss_research as rs
import pss_toolkit as toolkit
import pytz
import re
import sys
import time
import utility


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


# ----- Bot Setup -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    style = '{',
    datefmt = "%Y%m%d %H:%M:%S",
    format = "{asctime} [{levelname:<8}] {name}: {message}")

bot = commands.Bot(command_prefix=COMMAND_PREFIX,
                   description='This is a Discord Bot for Pixel Starships')

setattr(bot, "logger", logging.getLogger("bot.py"))


# ----- Bot Events ------------------------------------------------------------
@bot.event
async def on_ready():
    print(f'Current Working Directory: {PWD}')
    print(f'Bot prefix is: {COMMAND_PREFIX}')
    print('Bot logged in as {} (id={}) on {} servers'.format(
        bot.user.name, bot.user.id, len(bot.guilds)))
    global USER_PSS_TOOLKIT
    USER_PSS_TOOLKIT = await bot.fetch_user(487398795756437514)


@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, commands.CommandOnCooldown):
        await ctx.send('Error: {}'.format(err))


# ----- General Bot Commands ----------------------------------------------------------
@bot.command(brief='Ping the server')
async def ping(ctx):
    """Ping the server to verify that it\'s listening for commands"""
    await ctx.send('Pong!')

    
@bot.command(hidden=True, brief='Run shell command')
@commands.is_owner()
async def shell(ctx, *, cmd):
    """Run a shell command"""
    txt = utility.shell_cmd(cmd)
    await ctx.send(txt)


# ----- PSS Bot Commands --------------------------------------------------------------
@bot.command(brief='Get prestige combos of crew')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def prestige(ctx, *, name):
    """Get the prestige combinations of the character specified"""
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


@bot.command(brief='Get item prices from the PSS API')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def price(ctx, *, item_name=None):
    """Get the average price in bux of the item(s) specified, as returned by the PSS API. Note that prices returned by the API may not reflect the real market value, due to transfers between alts/friends"""
    raw_text = mkt.load_item_design_raw()
    item_lookup = mkt.parse_item_designs(raw_text)
    real_name = mkt.get_real_name(item_name, item_lookup)
    if len(item_name) < 2 and real_name != 'U':
        await ctx.send("Please enter at least two characters for item name")
    elif real_name is not None:
        market_txt = mkt.filter_item_designs(item_name, item_lookup, filter='price')
        market_txt = "**Prices matching '{}'**\n".format(item_name) + market_txt
        market_txt += '\n\nNote: bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons'
        await ctx.send(market_txt)
    else:
        await ctx.send("Could not find item name '{}'".format(item_name))


@bot.command(brief='Get item fair prices from the PSS API')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def fairprice(ctx, *, item_name=None):
    """Get Savy's fair price in bux of the item(s) specified, as returned by the PSS API."""
    raw_text = mkt.load_item_design_raw()
    item_lookup = mkt.parse_item_designs(raw_text)
    real_name = mkt.get_real_name(item_name, item_lookup)
    if len(item_name) < 2 and real_name != 'U':
        await ctx.send("Please enter at least two characters for item name")
    elif real_name is not None:
        market_txt = mkt.filter_item_designs(item_name, item_lookup, filter='fairprice')
        market_txt = "**Fair prices matching '{}'**\n".format(item_name) + market_txt
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


@bot.command(name='stats', aliases=['char', 'item'],
    brief='Get item/character stats')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stats(ctx, *, name=''):
    """Get the stats of a character/crew or item"""
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
    txt = p.show_collection(collection)
    if txt is None:
        await ctx.send("No entries found for '{}'".format(collection))
    else:
        await ctx.send(txt)


@bot.command(brief='Division stars (works only during tournament finals)')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def stars(ctx, *, division=None):
    """Get stars earned by each fleet during final tournament week. Replace [division] with a division name (a, b, c or d)"""
    txt = flt.get_division_stars(division)
    await ctx.send(txt)


@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@bot.command(hidden=True, brief='Show the dailies')
async def daily(ctx):
    """Show the dailies"""
    txt = dropship.get_dropship_text()
    await ctx.message.delete()
    await ctx.send(txt)


@bot.command(brief='Get crew levelling costs')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def level(ctx, level):
    """Shows the cost for a crew to reach a certain level. Replace <level> with a value between 2 and 40"""
    txt = p.get_level_cost(level)
    await ctx.send(txt)


@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@bot.command(hidden=True, brief='(beta) Get room infos')
async def roomsbeta(ctx, *, room_name=None):
    """(beta) Shows the information for specific room types. This command is currently under testing"""
    txt = rs.get_room_description(room_name)
    await ctx.send(txt)


@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
@bot.command(hidden=True, brief='(beta) Get missile info')
async def missilebeta(ctx, *, missile_name=None):
    """(beta) Shows the information for specific missile types. This command is currently under testing"""
    txt = rs.get_missile_description(missile_name)
    await ctx.send(txt)


@bot.command(brief='Get PSS stardate & Melbourne time')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def time(ctx):
    """Get PSS stardate, as well as the day and time in Melbourne, Australia. Gives the name of the Australian holiday, if it is a holiday in Australia."""
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
    txt = core.read_links_file()
    await ctx.send(txt)


@bot.command(hidden=True, aliases=['unquote'],
    brief='Quote/unquote text')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def quote(ctx, *, txt=''):
    """Quote or unquote text"""
    txt = core.parse_unicode(txt, str(ctx.invoked_with))
    await ctx.send(txt)


@bot.command(hidden=True, brief='Parse URL')
@commands.is_owner()
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def parse(ctx, *, url):
    """Parses the data from a URL"""
    txt_list = core.parse_links3(url)
    for txt in txt_list:
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


@bot.command(hidden=True, brief='Get fleet details', aliases=['fleet'])
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def alliance(ctx, *, fleet_name=None):
    """Gets a spreadsheet containing current data on the specified fleet"""
    txt = toolkit.get_fleet_spreadsheet(ctx, fleet_name)
    await ctx.send(txt)
    

@bot.command(hidden=True)
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def test(ctx,):
    user = await bot.fetch_user(281491870788354049)
    #txt = str(user)
    #await ctx.send(txt)
    #await bot.send_message(user, 'user')
    #await bot.send_message(ctx.author, 'ctx.author')
    #member = await commands.MemberConverter.Convert(ctx, user)
    #await bot.send_message(member, 'member')
        


# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
