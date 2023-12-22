import json as _json
import re as _re
from typing import Any as _Any
from typing import Dict as _Dict
from typing import List as _List
from typing import Optional as _Optional
from typing import Tuple as _Tuple
from typing import Union as _Union

from discord import ApplicationContext as _ApplicationContext
from discord import ClientUser as _ClientUser
from discord import Embed as _Embed
from discord import Member as _Member
from discord import TextChannel as _TextChannel
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import Cog as _Cog
from discord.ext.commands import Context as _Context
import discord.ext.commands.errors as _command_errors

from .. import pss_dropship as _dropship
from ..pss_exception import BotPermissionError as _BotPermissionError
from .. import server_settings as _server_settings
from .. import settings as _settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class CogBase(_Cog):
    COOLDOWN: float = 15.0
    RATE: int = 5

    def __init__(self, bot: _YadcBot) -> None:
        if not bot:
            raise ValueError('Parameter \'bot\' must not be None.')
        self.__bot = bot


    @property
    def bot(self) -> _YadcBot:
        return self.__bot


    def _extract_dash_parameters(self, full_arg: str, args: _Optional[_List[str]], *dash_parameters) -> _Tuple[_Union[bool, str], ...]:
        new_arg = full_arg or ''
        if args:
            new_arg += f' {" ".join(args)}'
        result = []

        for dash_parameter in dash_parameters:
            if dash_parameter:
                rx_dash_parameter = ''.join((r'\B', dash_parameter, r'\b'))
                dash_parameter_match = _re.search(rx_dash_parameter, new_arg)
                if dash_parameter_match:
                    remove = ''
                    parameter_pos = dash_parameter_match.span()[0]

                    if '=' in dash_parameter:
                        value_start = parameter_pos + len(dash_parameter)
                        value_end = new_arg.find('--', value_start)
                        if value_end < 0:
                            value_len = len(new_arg) - value_start
                        else:
                            value_len = value_end - value_start - 1
                        value = new_arg[value_start:value_start + value_len]
                        remove = f'{dash_parameter}{value}'
                        result.append(value)
                    else:
                        remove = dash_parameter
                        result.append(True)
                    if parameter_pos > 0:
                        remove = f' {remove}'
                    rx_remove = ''.join((' ', _re.escape(remove), r'\b'))
                    new_arg = _re.sub(rx_remove, '', new_arg).strip()
                else:
                    if '=' in dash_parameter:
                        result.append(None)
                    else:
                        result.append(False)
        return new_arg, *result


    def _log_command_use(self, ctx: _Context):
        if _settings.PRINT_DEBUG_COMMAND:
            print(f'Invoked command: {ctx.message.content}')


    def _log_command_use_error(self, ctx: _Context, err: Exception, force_printing: bool = False):
        if _settings.PRINT_DEBUG_COMMAND or force_printing:
            print(f'Invoked command had an error: {ctx.message.content}')
            if err:
                print(str(err))





class CurrentCogBase(CogBase):
    async def _get_daily_output(self, ctx: _Union[_ApplicationContext, _Context]) -> _Union[_List[str], _List[_Embed]]:
        self._log_command_use(ctx)
        as_embed = await _server_settings.get_use_embeds(ctx)
        output, output_embed, _ = await _dropship.get_dropship_text(ctx.bot, ctx.guild)
        if as_embed:
            return output_embed
        else:
            return output





class GeneralCogBase(CogBase):
    def _get_about_output(self, ctx: _Union[_ApplicationContext, _Context]) -> _Embed:
        guild_count = len([guild for guild in self.bot.guilds if guild.id not in _settings.IGNORE_SERVER_IDS_FOR_COUNTING])
        user_name = self.bot.user.display_name
        if ctx.guild is None:
            nick = self.bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        has_nick = self.bot.user.display_name != nick
        pfp_url = (self.bot.user.avatar or self.bot.user.default_avatar).url
        about_info = self._read_about_file()

        title = f'About {nick}'
        if has_nick:
            title += f' ({user_name})'
        description = about_info['description']
        footer = f'Serving on {guild_count} guild{"" if guild_count == 1 else "s"}.'
        fields = [
            ('version', f'v{_settings.VERSION}', True),
            ('authors', ', '.join(about_info['authors']), True),
            ('profile pic by', about_info['pfp'], True),
            ('support', about_info['support'], False)
        ]
        colour = _utils.discord.get_bot_member_colour(self.bot, ctx.guild)

        embed = _utils.discord.create_embed(title, description=description, colour=colour, fields=fields, thumbnail_url=pfp_url, footer=footer)
        return embed


    def _get_invite_output(self, ctx: _Union[_ApplicationContext, _Context], as_embed: bool) -> _Union[str, _Embed]:
        if ctx.guild is None:
            nick = self.bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        title = f'Invite {nick} to your server'
        invite_url = f'{_settings.BASE_INVITE_URL}{self.bot.user.id}'
        colour = None

        if as_embed:
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            description = f'[{title}]({invite_url})'
            output = _utils.discord.create_embed(None, description=description, colour=colour)
        else:
            output = f'{title}: {invite_url}'
        return output


    async def _get_links_output(self, ctx: _Union[_ApplicationContext, _Context]) -> _Union[str, _Embed]:
        links = self._read_links_file()
        output = []
        if (await _server_settings.get_use_embeds(ctx)):
            title = 'Pixel Starships weblinks'
            colour = _utils.discord.get_bot_member_colour(self.bot, ctx.guild)
            fields = []
            for field_name, hyperlinks in links.items():
                field_value = []
                for (description, hyperlink) in hyperlinks:
                    field_value.append(f'[{description}]({hyperlink})')
                fields.append((field_name, '\n'.join(field_value), False))
            embed = _utils.discord.create_embed(title, fields=fields, colour=colour)
            output.append(embed)
        else:
            for category, hyperlinks in links.items():
                output.append(f'**{category}**')
                for (description, hyperlink) in hyperlinks:
                    output.append(f'{description}: <{hyperlink}>')
                output.append(_utils.discord.ZERO_WIDTH_SPACE)
            if output:
                output = output[:-1]
        return output


    def _get_support_output(self, ctx: _Union[_ApplicationContext, _Context], as_embed: bool) -> _Union[str, _Embed]:
        if ctx.guild is None:
            nick = self.bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        about = self._read_about_file()
        title = f'Join {nick} support server'
        colour = None
        guild_invite = about['support']

        if as_embed:
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            description = f'[{title}]({guild_invite})'
            output = _utils.discord.create_embed(None, description=description, colour=colour)
        else:
            output = f'{title}: {guild_invite}'
        return output


    def _read_about_file(self, language_key: str = 'en') -> _Dict[str, _Any]:
        result = {}
        for pss_about_file in _settings.PSS_ABOUT_FILES:
            try:
                with open(pss_about_file) as f:
                    result = _json.load(f)
                break
            except:
                pass
        return result.get(language_key)


    def _read_links_file(self, language_key: str = 'en') -> _Dict[str, _List[_List[str]]]:
        links = {}
        for pss_links_file in _settings.PSS_LINKS_FILES:
            try:
                with open(pss_links_file) as f:
                    links = _json.load(f)
                break
            except:
                pass
        return links.get(language_key)





class RawCogBase(CogBase):
    COOLDOWN: float = 10.0
    RATE: int = 5






class SettingCogBase(CogBase):
    COOLDOWN_TYPE = _BucketType.guild


    async def _assert_settings_command_valid(self, ctx: _Union[_ApplicationContext, _Context]) -> None:
        if _utils.discord.is_guild_channel(ctx.channel):
            permissions = ctx.channel.permissions_for(ctx.author)
            if permissions.manage_guild is not True:
                raise _command_errors.MissingPermissions(['manage_guild'])
        else:
            raise Exception('This command cannot be used in DMs or group chats, but only in Discord servers/guilds.')


    async def _assert_automessage_channel_permissions(self, channel: _TextChannel, me: _Union[_ClientUser, _Member]) -> None:
        permissions = channel.permissions_for(me)
        if permissions.read_messages is not True:
            raise _BotPermissionError('I don\'t have access to that channel.')
        if permissions.read_message_history is not True:
            raise _BotPermissionError('I don\'t have access to the messages history in that channel.')
        if permissions.send_messages is not True:
            raise _BotPermissionError('I don\'t have permission to post in that channel.')






class TournamentCogBase(CogBase):
    FLEETS_RATE: int = 1
    FLEETS_COOLDOWN: float = 60.0
    