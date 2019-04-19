import discord
import subprocess

user_pss_toolkit = None

def shell_cmd(cmd):
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')
    
def get_user_pss_toolkit():
    if user_pss_toolkit == None:
        user_pss_toolkit = discord.client.get_user('487398795756437514')
    return user_pss_toolkit
    
