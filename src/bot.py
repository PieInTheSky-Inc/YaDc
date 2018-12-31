from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from discord.ext import commands
import discord
import logging
import os
import pss_prestige as p
import sys


RATE = 3
COOLDOWN = 30.0


PWD = os.getcwd()
print('Current Working Directory: {}'.format(PWD))
sys.path.insert(0, PWD + '/src/')
import utility

logging.basicConfig(
    level=logging.INFO,
    style = '{',
    datefmt = "%Y%m%d %H:%M:%S",
    format = "{asctime} [{levelname:<8}] {name}: {message}")

bot = commands.Bot(command_prefix=';',
                   description='Heroku Discord Bot Example')

setattr(bot, "logger", logging.getLogger("bot.py"))


# ----- Bot Events ------------------------------------------------------------
@bot.event
async def on_ready():
    print('Bot logged in as {} (id={})'.format(
        bot.user.name, bot.user.id))


@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, commands.CommandOnCooldown):
        await ctx.send('Error: {}'.format(err))


# ----- General Bot Commands ----------------------------------------------------------
@bot.command(brief='Ping the server')
async def ping(ctx):
    """Ping the server to verify that it\'s listening for commands"""
    await ctx.send('Pong!')

    
@bot.command(brief='Run shell command')
@commands.is_owner()
async def shell(ctx, *, cmd):
    """Run a shell command"""
    txt = utility.shell_cmd(cmd)
    await ctx.send(txt)


# ----- PSS Bot Commands --------------------------------------------------------------
@bot.command(brief='Get prestige combos of crew')
@commands.cooldown(rate=RATE, per=COOLDOWN, type=commands.BucketType.channel)
async def prestige(ctx, *, name: str=None):
    """Get the prestige combinations of the character specified"""
    if name is None:
        help_txt = 'Enter: {}prestige [character name]'.format(command_prefix)
        await ctx.send(help_txt)
        return

    write_log(ctx.prefix, ctx.command, '{}'.format(name),
              ctx.author, ctx.guild)
    prestige_txt, success = p.get_prestige(name, 'from', tbl_i2n, tbl_n2i)
    for txt in prestige_txt:
        await ctx.send(txt)
        

# ----- Run the Bot -----------------------------------------------------------
if __name__ == '__main__':
    token = str(os.environ.get('DISCORD_BOT_TOKEN'))
    bot.run(token)
