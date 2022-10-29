from typing import Dict as _Dict
from typing import List as _List
from typing import Union as _Union

from discord import ApplicationContext as _ApplicationContext
from discord import Option as _Option
from discord import slash_command as _slash_command
from discord import SlashCommand as _SlashCommand
from discord import SlashCommandGroup as _SlashCommandGroup
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import CogBase as _CogBase
from .base import GeneralCogBase as _GeneralCogBase
from .. import server_settings as _server_settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class GeneralSlashCog(_GeneralCogBase, name='General Slash'):
    def __init__(self, bot: _YadcBot):
        super().__init__(bot)
        self.__all_base_slash_commands: _Dict[int, _Union[_SlashCommand, _SlashCommandGroup]] = {}
        self.__base_slash_commands_by_cogs: _Dict[str, _Union[_SlashCommand, _SlashCommandGroup]] = {}
        self.__help_command_output: _List[str] = []


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


    @_slash_command(name='help', brief='Get help')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def help_slash(self,
        ctx: _ApplicationContext,
        command_or_category: _Option(str, 'Specify the command or category you need help for', required=False, default=None) = None
    ):
        # Iterate all commands. self.bot.all_commands returns all base level commands and groups, no subcommands.
        # help will list all slash commands by their mention (cmd.mention) along with their description (cmd.mention).
        # if it got subcommands, there's a link/button for each
        self._log_command_use(ctx)

        self._update_command_lists()

        if command_or_category:
            pass
        else:
            title = f'{ctx.guild.me.display_name} Slash Commands'
            lines = list(self.__help_command_output)
            if (await _server_settings.get_use_embeds(ctx)):
                icon_url = (self.bot.user.avatar or self.bot.user.default_avatar).url
                colour = _utils.discord.get_bot_member_colour(self.bot, ctx.guild)
                output = _utils.discord.create_basic_embeds_from_description(title, description=lines, colour=colour, icon_url=icon_url)
            else:
                output = lines.insert(0, title)
            await _utils.discord.respond_with_output(ctx, output, ephemeral=True)


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


    def _update_command_lists(self) -> None:
        if not self.__all_base_slash_commands:
            for cmd in self.bot.all_commands.values():
                if isinstance(cmd, (_SlashCommand, _SlashCommandGroup)) and cmd.id not in self.__all_base_slash_commands.keys():
                    self.__all_base_slash_commands[cmd.id] = cmd

        if not self.__base_slash_commands_by_cogs:
            for cmd in self.__all_base_slash_commands.values():
                self.__base_slash_commands_by_cogs.setdefault(cmd.cog.qualified_name, []).append(cmd)

        if not self.__help_command_output:
            for cog_name in sorted(self.__base_slash_commands_by_cogs.keys()):
                cog_commands = sorted(self.__base_slash_commands_by_cogs[cog_name], key=lambda cmd: cmd.name)
                block = ['', f'__**Category {cog_name.replace("Slash", "").replace("Cog", "").strip()}**__']
                for cmd in cog_commands:
                    if isinstance(cmd, _SlashCommand):
                        block.append(GeneralSlashCog._get_command_help_string(cmd))
                    elif isinstance(cmd, _SlashCommandGroup):
                        block.extend(GeneralSlashCog._get_subcommands_help(cmd))
                if len(block) >= 3:
                    self.__help_command_output.append('\n'.join(block[:3]))
                    block = block[3:]
                self.__help_command_output.extend(block)
            while self.__help_command_output and self.__help_command_output[0] == '':
                self.__help_command_output.pop(0)


    @staticmethod
    def _get_subcommands_help(cmd: _SlashCommandGroup) -> _List[str]:
        sub_commands: _List[_SlashCommand] = []
        sub_command_groups = []

        for sub in sorted(cmd.subcommands, key=lambda sub: sub.name):
            if isinstance(sub, _SlashCommand):
                sub_commands.append(sub)
            elif isinstance(sub, _SlashCommandGroup):
                sub_command_groups.append(sub)

        sub_commands.sort(key=lambda cmd: cmd.name)
        sub_command_groups.sort(key=lambda cmd: cmd.name)

        result = []
        for sub_group in sub_command_groups:
            result.extend(GeneralSlashCog._get_subcommands_help(sub_group))
        for sub_cmd in sub_commands:
            result.append(GeneralSlashCog._get_command_help_string(sub_cmd))
        return result


    @staticmethod
    def _get_command_help_string(cmd: _SlashCommand) -> str:
        return f'> {cmd.mention}  {cmd.description}'


def setup(bot: _YadcBot):
    bot.add_cog(GeneralSlashCog(bot))