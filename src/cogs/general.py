import json as _json
from typing import Any as _Any
from typing import Dict as _Dict
from typing import List as _List

from discord.ext.commands import Bot as _Bot
from discord.ext.commands import command as _command
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from . import BaseCog as _BaseCog
from .. import settings as _settings
from .. import server_settings as _server_settings
from .. import utils as _utils





class GeneralCog(_BaseCog, name='General'):
    """
    This extension offers commands
    """

    @_command(name='about', aliases=['info'], brief='Display info on this bot')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
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
        guild_count = len([guild for guild in self.__bot.guilds if guild.id not in _settings.IGNORE_SERVER_IDS_FOR_COUNTING])
        user_name = self.__bot.user.display_name
        if ctx.guild is None:
            nick = self.__bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        has_nick = self.__bot.user.display_name != nick
        pfp_url = self.__bot.user.avatar_url
        about_info = _read_about_file()

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
        colour = _utils.discord.get_bot_member_colour(self.__bot, ctx.guild)

        embed = _utils.discord.create_embed(title, description=description, colour=colour, fields=fields, thumbnail_url=pfp_url, footer=footer)
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
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
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

        if ctx.guild is None:
            nick = self.__bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        title = f'Invite {nick} to your server'
        invite_url = f'{_settings.BASE_INVITE_URL}{self.__bot.user.id}'
        colour = None

        if as_embed:
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            description = f'[{title}]({invite_url})'
            output = _utils.discord.create_embed(None, description=description, colour=colour)
        else:
            output = f'{title}: {invite_url}'
        await _utils.discord.dm_author(ctx, [output], output_is_embeds=as_embed)
        if _utils.discord.is_guild_channel(ctx.channel):
            notice = f'{ctx.author.mention} Sent invite link via DM.'
            if as_embed:
                notice = _utils.discord.create_embed(None, description=notice, colour=colour)
            await _utils.discord.reply_with_output(ctx, [notice])


    @_command(name='links', brief='Show links')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def links(self, ctx: _Context):
        """
        Shows the links for useful sites regarding Pixel Starships.

        Usage:
        /links

        Examples:
        /links - Shows the links for useful sites regarding Pixel Starships.
        """
        self._log_command_use(ctx)
        links = _read_links_file()
        output = []
        if (await _server_settings.get_use_embeds(ctx)):
            title = 'Pixel Starships weblinks'
            colour = _utils.discord.get_bot_member_colour(self.__bot, ctx.guild)
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
        msg = await ctx.send('Pong!')
        miliseconds = (msg.created_at - ctx.message.created_at).microseconds / 1000.0
        await msg.edit(content=f'{msg.content} ({miliseconds} ms)')


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

        if ctx.guild is None:
            nick = self.__bot.user.display_name
        else:
            nick = ctx.guild.me.display_name
        about = _read_about_file()
        title = f'Join {nick} support server'
        colour = None
        guild_invite = about['support']

        if as_embed:
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            description = f'[{title}]({guild_invite})'
            output = _utils.discord.create_embed(None, description=description, colour=colour)
        else:
            output = f'{title}: {guild_invite}'
        await _utils.discord.dm_author(ctx, [output], output_is_embeds=as_embed)
        if _utils.discord.is_guild_channel(ctx.channel):
            notice = f'{ctx.author.mention} Sent invite link to bot support server via DM.'
            if as_embed:
                notice = _utils.discord.create_embed(None, description=notice, colour=colour)
            await _utils.discord.reply_with_output(ctx, [notice])





def _read_about_file(language_key: str = 'en') -> _Dict[str, _Any]:
    result = {}
    for pss_about_file in _settings.PSS_ABOUT_FILES:
        try:
            with open(pss_about_file) as f:
                result = _json.load(f)
            break
        except:
            pass
    return result.get(language_key)


def _read_links_file(language_key: str = 'en') -> _Dict[str, _List[_List[str]]]:
    links = {}
    for pss_links_file in _settings.PSS_LINKS_FILES:
        try:
            with open(pss_links_file) as f:
                links = _json.load(f)
            break
        except:
            pass
    return links.get(language_key)





def setup(bot: _Bot):
    bot.add_cog(GeneralCog(bot))