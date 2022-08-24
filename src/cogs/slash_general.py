from discord import ApplicationContext as _ApplicationContext
from discord import slash_command as _slash_command
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import CogBase as _CogBase
from .base import GeneralCogBase as _GeneralCogBase
from .. import server_settings as _server_settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class GeneralSlashCog(_GeneralCogBase, name='General Slash'):
    @_slash_command(name='about', brief='Display info on this bot')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def about_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Displays information about this bot and its authors.
        """
        self._log_command_use(ctx)
        embed = self._get_about_output(ctx)
        await _utils.discord.respond_with_output(ctx, [embed])


    @_slash_command(name='invite', brief='Get an invite link')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def invite_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Produces an invite link for this bot and displays it.
        """
        self._log_command_use(ctx)

        as_embed = await _server_settings.get_use_embeds(ctx)
        output = self._get_invite_output(ctx, as_embed)
        await _utils.discord.respond_with_output(ctx, [output], ephemeral=True)


    @_slash_command(name='links', brief='Show useful links')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def links_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Shows the links for useful sites regarding Pixel Starships.
        """
        self._log_command_use(ctx)
        output = await self._get_links_output(ctx)
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='ping', brief='Ping the server')
    async def ping_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Ping the bot to verify that it\'s listening for _commands.
        """
        self._log_command_use(ctx)
        latency = self.bot.latency * 1000
        output = f'Pong! ({int(latency)} ms)'
        await _utils.discord.respond_with_output(ctx, [output], ephemeral=True)


    @_slash_command(name='support', brief='Invite to bot\'s support server')
    async def support_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Produces an invite link to the support server for this bot and sends it via DM.
        """
        self._log_command_use(ctx)

        as_embed = await _server_settings.get_use_embeds(ctx)
        output = self._get_support_output(ctx, as_embed)
        await _utils.discord.respond_with_output(ctx, [output], ephemeral=True)



def setup(bot: _YadcBot):
    bot.add_cog(GeneralSlashCog(bot))