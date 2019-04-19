import bot
import discord
import subprocess

def shell_cmd(cmd):
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')
    
def get_user_pss_toolkit():
    return bot.fetch_user(487398795756437514)
