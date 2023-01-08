import datetime as _datetime
import holidays as _holidays
import os as _os
import pytz as _pytz
import re as _re
from typing import Dict as _Dict

from discord import ApplicationContext as _ApplicationContext
from discord import Option as _Option
from discord import OptionChoice as _OptionChoice
from discord import slash_command as _slash_command
from discord import SlashCommandGroup as _SlashCommandGroup
from discord import TextChannel as _TextChannel
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import SettingCogBase as _SettingCogBase

from .. import pagination as _pagination
from ..pss_exception import Error as _Error
from ..pss_exception import BotPermissionError as _BotPermissionError
from ..pss_exception import InvalidParameterValueError as _InvalidParameterValueError
from ..pss_exception import NotFound as _NotFound
from .. import server_settings as _server_settings
from .. import settings as _settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class SettingsSlashCog(_SettingCogBase, name='Settings Slash'):
    _ON_OFF_CHOICES = [
        _OptionChoice(name='on', value='on'),
        _OptionChoice(name='off', value='off'),
    ]


    @_slash_command(name='prefix', brief='Retrieve prefix settings')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_BucketType.user)
    async def prefix_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Retrieve the prefix setting for this server.
        """
        self._log_command_use(ctx)

        if _utils.discord.is_guild_channel(ctx.channel):
            guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
            prefix_settings = guild_settings.get_prefix_setting()
        else:
            prefix_settings = {'prefix': _settings.DEFAULT_PREFIX}
        await self._respond_with_server_settings(ctx, prefix_settings, note='Prefixed commands may not work on Discord servers/guilds. Use Slash Commands instead.')


    _settings_slash_group = _SlashCommandGroup('settings', 'Get or set bot settings for this server.')

    @_settings_slash_group.command(name='show', brief='Get bot settings for this server')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_show_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Show bot settings for this Discord server/guild.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)
        await self._respond_with_server_settings(ctx)


    _settings_reset_slash_group = _settings_slash_group.create_subgroup('reset', 'Reset bot settings for this server.')

    @_settings_reset_slash_group.command(name='all', brief='Reset all settings to defaults.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_all_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset all settings for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        guild_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id))
        success = await guild_settings.reset()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset all settings for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the auto-daily settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')

    @_settings_reset_slash_group.command(name='autodaily', brief='Reset all auto-daily settings to defaults.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_autodaily_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the auto-daily settings for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autodaily_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autodaily
        success = await autodaily_settings.reset()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the auto-daily settings for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the auto-daily settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    @_settings_reset_slash_group.command(name='autodailychannel', brief='Reset auto-daily channel.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_autodailychannel_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the auto-daily channel for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autodaily_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autodaily
        success = await autodaily_settings.reset_channel()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the auto-daily channel for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the auto-daily channel for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    @_settings_reset_slash_group.command(name='autodailymode', brief='Reset auto-daily change mode.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_autodailymode_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the auto-daily change mode for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autodaily_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autodaily
        success = await autodaily_settings.reset_change_mode()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the auto-daily change mode for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the auto-daily change mode for this server.\n'
                        + 'Please try again or contact the bot\'s author.')

    @_settings_reset_slash_group.command(name='autotrader', brief='Reset all auto-trader settings to defaults.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_autotrader_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the auto-trader settings for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autotrader_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autotrader
        success = await autotrader_settings.reset()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the auto-trader settings for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the auto-trader settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    @_settings_reset_slash_group.command(name='autotraderchannel', brief='Reset auto-trader channel.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_autotraderchannel_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the auto-trader channel for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autotrader_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autotrader
        success = await autotrader_settings.reset_channel()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the auto-trader channel for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the auto-trader channel for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    @_settings_reset_slash_group.command(name='autotradermode', brief='Reset auto-trader change mode.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_autotradermode_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the auto-trader change mode for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autotrader_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autotrader
        success = await autotrader_settings.reset_change_mode()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the auto-trader change mode for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the auto-trader change mode for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    @_settings_reset_slash_group.command(name='embed', aliases=['embeds'], brief='Reset embed settings')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_embeds_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the embed settings for this server to 'ON'.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
        success = await guild_settings.reset_use_embeds()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the embed settings for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the embed settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    @_settings_reset_slash_group.command(name='pagination', aliases=['pages'], brief='Reset pagination settings')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_pagination_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the pagination settings for this server to 'ON'.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
        success = await guild_settings.reset_use_pagination()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the pagination settings for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the pagination settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    @_settings_reset_slash_group.command(name='prefix', brief='Reset bot prefix.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_reset_prefix_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Reset the bot's prefix for this server to '/'.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
        success = await guild_settings.reset_prefix()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully reset the prefix for this server.')
        else:
            raise _Error('An error ocurred while trying to reset the prefix settings for this server.\n'
                        + 'Please try again or contact the bot\'s author.')


    _settings_set_slash_group = _settings_slash_group.create_subgroup('set', 'Set bot settings for this server.')

    @_settings_set_slash_group.command(name='autodailychannel', brief='Set auto-daily channel.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_set_autodaily_channel_slash(
        self,
        ctx: _ApplicationContext,
        channel: _Option(_TextChannel, 'Select a channel. Leave empty to use the current channel', required=False, default=None) = None,
    ):
        """
        Set the auto-daily channel for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)
        channel: _TextChannel

        autodaily_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autodaily
        if not channel:
            channel = ctx.channel

        self._assert_automessage_channel_permissions(channel, ctx.me)

        success = await autodaily_settings.set_channel(channel)
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully set the auto-daily channel for this server.')
        else:
            raise _Error(f'Could not set auto-daily channel for this server. Please try again or contact the bot\'s author.')


    @_settings_set_slash_group.command(name='autodailychangemode', brief='Toggle auto-daily change mode.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_set_autodaily_mode_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Toggle the auto-daily change mode for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autodaily_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autodaily
        success = await autodaily_settings.toggle_change_mode()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully toggled the auto-daily change mode for this server.')
        else:
            raise _Error(f'Could not set auto-daily change mode for this server. Please try again or contact the bot\'s author.')



    @_settings_set_slash_group.command(name='autotraderchannel', brief='Set auto-trader channel.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_set_autotrader_channel_slash(
        self,
        ctx: _ApplicationContext,
        channel: _Option(_TextChannel, 'Select a channel. Leave empty to use the current channel', required=False, default=None) = None
    ):
        """
        Set the auto-daily channel for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autotrader_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autotrader
        if not channel:
            channel = ctx.channel

        self._assert_automessage_channel_permissions(channel, ctx.me)

        success = await autotrader_settings.set_channel(channel)
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully set the auto-trader channel for this server.')
            await ctx.invoke(self.bot.get_command('trader'))
        else:
            raise _Error(f'Could not set auto-trader channel for this server. Please try again or contact the bot\'s author.')


    @_settings_set_slash_group.command(name='autotraderchangemode', brief='Toggle auto-trader change mode')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_set_autotrader_mode_slash(
        self,
        ctx: _ApplicationContext
    ):
        """
        Toggle the auto-trader change mode for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        autotrader_settings = (await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)).autotrader
        success = await autotrader_settings.toggle_change_mode()
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully toggled the auto-trader change mode for this server.')
        else:
            raise _Error(f'Could not toggle auto-trader change mode for this server. Please try again or contact the bot\'s author.')


    @_settings_set_slash_group.command(name='embed', brief='Set/toggle embed settings.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_set_embeds_slash(
        self,
        ctx: _ApplicationContext,
        switch: _Option(str, '', choices=_ON_OFF_CHOICES, required=False, default=None) = None
    ):
        """
        Set or toggle the pagination for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
        success = await guild_settings.set_use_embeds(switch)
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully changed the embed settings for this server.')
        else:
            raise _Error(f'Could not set embed settings for this server. Please try again or contact the bot\'s author.')


    @_settings_set_slash_group.command(name='pagination', brief='Set pagination')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_set_pagination_slash(
        self,
        ctx: _ApplicationContext,
        switch: _Option(str, '', choices=_ON_OFF_CHOICES, required=False, default=None) = None
    ):
        """
        Set or toggle the pagination for this server.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
        success = await guild_settings.set_use_pagination(switch)
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully changed the pagination settings for this server.')
        else:
            raise _Error(f'Could not set pagination settings for this server. Please try again or contact the bot\'s author.')


    @_settings_set_slash_group.command(name='prefix', brief='Set prefix.')
    @_cooldown(rate=_SettingCogBase.RATE, per=_SettingCogBase.COOLDOWN, type=_SettingCogBase.COOLDOWN_TYPE)
    async def settings_set_prefix(
        self,
        ctx: _ApplicationContext,
        prefix: _Option(str, 'The new prefix to be used for prefixed commands.')):
        """
        Set the prefix for this server. The default is '/'.
        """
        self._log_command_use(ctx)
        await self._assert_settings_command_valid(ctx)

        prefix = prefix.lstrip()
        guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
        success = await guild_settings.set_prefix(prefix)
        if success:
            await self._respond_with_server_settings(ctx, note='Successfully changed the prefix for this server.')
        else:
            raise _Error(f'Could not set prefix for this server. Please try again or contact the bot\'s author.')


    async def _respond_with_server_settings(self, ctx: _ApplicationContext, settings: _Dict[str, str] = None, note: str = None) -> None:
        if ctx.guild is None:
            if not settings:
                raise _Error('If `SettingsCog._respond_with_server_settings` function is called in DMs, a set of `settings` must be provided!')
            title = 'Bot settings'
        else:
            title = f'Server settings for {ctx.guild.name}'
            guild_settings = await _server_settings.GUILD_SETTINGS.get(self.bot, ctx.guild.id)
            settings = settings or guild_settings.get_full_settings()
        output = await _server_settings.get_pretty_guild_settings(ctx, settings, title=title, note=note)
        await _utils.discord.respond_with_output(ctx, output)





def setup(bot: _YadcBot):
    bot.add_cog(SettingsSlashCog(bot))