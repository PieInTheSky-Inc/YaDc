from discord.ext.commands import command as _command
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import CogBase as _CogBase
from .base import GeneralCogBase as _GeneralCogBase
from .. import server_settings as _server_settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class GeneralCog(_GeneralCogBase, name='General'):
    """
    This module offers commands to obtain information about the bot itself.
    """

    @_command(name='about', aliases=['info'], brief='Display info on this bot')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def about(self, ctx: _Context):
        """
        Displays information about this bot and its authors.

        Usage:
        /about
        /info

        Examples:
        /about - Displays information on this bot and its authors.
        """
        self._log_command_use(ctx)
        embed = self._get_about_output(ctx)
        await _utils.discord.reply_with_output(ctx, [embed])


    @_command(name='flip', aliases=['flap', 'flipflap'], brief='There\'s no flip without the flap.', hidden=True)
    async def flap(self, ctx: _Context):
        """
        There's no flip without the flap.

        Thanks to bloodyredbaron for the idea <3
        """
        self._log_command_use(ctx)
        await _utils.discord.try_delete_original_message(ctx)
        output = [
            'There\'s no flip without the flap. ~ bloodyredbaron',
            'https://www.youtube.com/watch?v=V4vCQ-5mC_I'
        ]
        await _utils.discord.post_output(ctx, output)


    @_command(name='invite', brief='Get an invite link')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def invite(self, ctx: _Context):
        """
        Produces an invite link for this bot and sends it via DM.

        Usage:
        /invite

        Examples:
        /invite - Produces an invite link for this bot and sends it via DM.
        """
        self._log_command_use(ctx)

        as_embed = await _server_settings.get_use_embeds(ctx)
        output = self._get_invite_output(ctx, as_embed)
        await _utils.discord.dm_author(ctx, [output], output_is_embeds=as_embed)
        if _utils.discord.is_guild_channel(ctx.channel):
            notice = f'{ctx.author.mention} Sent invite link via DM.'
            if as_embed:
                notice = _utils.discord.create_embed(None, description=notice, colour=_utils.discord.get_bot_member_colour(self.bot, ctx.guild))
            await _utils.discord.reply_with_output(ctx, [notice])


    @_command(name='links', brief='Show useful links')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def links(self, ctx: _Context):
        """
        Shows the links for useful sites regarding Pixel Starships.

        Usage:
        /links

        Examples:
        /links - Shows the links for useful sites regarding Pixel Starships.
        """
        self._log_command_use(ctx)
        output = await self._get_links_output(ctx)
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='ping', brief='Ping the server')
    async def ping(self, ctx: _Context):
        """
        Ping the bot to verify that it\'s listening for _commands.

        Usage:
        /ping

        Examples:
        /ping - The bot will answer with 'Pong!'.
        """
        self._log_command_use(ctx)
        latency = self.bot.latency * 1000
        output = f'Pong! ({int(latency)} ms)'
        await _utils.discord.reply_with_output(ctx, [output])


    @_command(name='support', brief='Invite to bot\'s support server')
    async def support(self, ctx: _Context):
        """
        Produces an invite link to the support server for this bot and sends it via DM.

        Usage:
        /support

        Examples:
        /support - Produces an invite link to the support server and sends it via DM.
        """
        self._log_command_use(ctx)

        as_embed = await _server_settings.get_use_embeds(ctx)
        output = self._get_support_output(ctx, as_embed)
        await _utils.discord.dm_author(ctx, [output], output_is_embeds=as_embed)
        if _utils.discord.is_guild_channel(ctx.channel):
            notice = f'{ctx.author.mention} Sent invite link to bot support server via DM.'
            if as_embed:
                notice = _utils.discord.create_embed(None, description=notice, colour=_utils.discord.get_bot_member_colour(self.bot, ctx.guild))
            await _utils.discord.reply_with_output(ctx, [notice])



def setup(bot: _YadcBot):
    bot.add_cog(GeneralCog(bot))