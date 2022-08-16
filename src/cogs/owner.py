import os as _os
import json as _json
import re as _re
from typing import List as _List

from discord import Embed as _Embed
from discord import File as _File
import discord.errors as _errors
from discord.ext.commands import Bot as _Bot
from discord.ext.commands import Context as _Context
from discord.ext.commands import command as _command
from discord.ext.commands import group as _command_group
from discord.ext.commands import is_owner as _is_owner

from .base import CogBase as _CogBase
from .. import database as _db
from .. import pagination as _pagination
from .. import pss_crew as _crew
from .. import pss_daily as _daily
from .. import pss_dropship as _dropship
from ..pss_exception import Error as _Error
from .. import pss_item as _item
from .. import pss_login as _login
from .. import pss_lookups as _lookups
from .. import pss_research as _research
from .. import pss_room as _room
from .. import pss_training as _training
from .. import server_settings as _server_settings
from .. import settings as _settings
from .. import utils as _utils


class OwnerCog(_CogBase, name='Owner commands'):
    """
    This module offers commands for the owner of the bot.
    """

    @_command_group(name='autodaily', brief='Configure auto-daily for the server', hidden=True)
    @_is_owner()
    async def autodaily(self, ctx: _Context):
        """
        This command can be used to get an overview of the autodaily settings for this bot.

        In order to use this command or any sub commands, you need to be the owner of this bot.
        """
        self._log_command_use(ctx)
        pass


    @autodaily.group(name='list', brief='List configured auto-daily channels', invoke_without_command=False, hidden=True)
    @_is_owner()
    async def autodaily_list(self, ctx: _Context):
        """
        Lists auto-daily channels currently configured.
        """
        self._log_command_use(ctx)
        pass


    @autodaily_list.command(name='all', brief='List all configured auto-daily channels', hidden=True)
    @_is_owner()
    async def autodaily_list_all(self, ctx: _Context):
        """
        Lists all auto-daily channels currently configured across all guilds.
        """
        self._log_command_use(ctx)
        output = await _daily.get_daily_channels(ctx, None, None)
        await _utils.discord.reply_with_output(ctx, output)


    @autodaily.command(name='post', brief='Post a daily message on this server\'s auto-daily channel', hidden=True)
    @_is_owner()
    async def autodaily_post(self, ctx: _Context):
        """
        Posts the daily message to all auto-daily channels currently configured across all guilds.
        """
        self._log_command_use(ctx)
        guild = ctx.guild
        channel_id = await _server_settings.db_get_daily_channel_id(guild.id)
        if channel_id is not None:
            text_channel = self.bot.get_channel(channel_id)
            as_embed = await _server_settings.get_use_embeds(ctx)
            output, output_embed, _ = await _dropship.get_dropship_text()
            if as_embed:
                await _utils.discord.reply_with_output_to_channel(text_channel, output_embed)
            else:
                await _utils.discord.reply_with_output_to_channel(text_channel, output)


    @_command_group(name='db', brief='DB commands', hidden=True, invoke_without_command=True)
    @_is_owner()
    async def db(self, ctx: _Context):
        """
        Database commands
        """
        self._log_command_use(ctx)
        await ctx.send_help('db')


    @db.command(name='query', brief='Try to execute a DB query', hidden=True)
    @_is_owner()
    async def db_query(self, ctx: _Context, *, query: str):
        """
        Starts a database query and returns a success message.
        """
        self._log_command_use(ctx)
        success = await _db.try_execute(query)
        if not success:
            await ctx.send(f'The query \'{query}\' failed.')
        else:
            await ctx.send(f'The query \'{query}\' has been executed successfully.')


    @db.command(name='select', brief='Try to select from DB', hidden=True)
    @_is_owner()
    async def db_select(self, ctx: _Context, *, query: str):
        """
        Selects from a database and returns the results.
        """
        self._log_command_use(ctx)
        if not query.lower().startswith('select '):
            query = f'SELECT {query}'
        try:
            result = await _db.fetchall(query)
            error = None
        except Exception as error:
            result = []
            raise _Error(f'The query \'{query}\' failed.')
        if result:
            await ctx.send(f'The query \'{query}\' has been executed successfully.')
            result = [str(record) for record in result]
            await _utils.discord.reply_with_output(ctx, result)
        else:
            raise _Error(f'The query \'{query}\' didn\'t return any results.')


    @_command_group(name='debug', brief='Get debug info', hidden=True, invoke_without_command=True)
    @_is_owner()
    async def debug(self, ctx: _Context, *, args: str = None):
        self._log_command_use(ctx)


    @debug.group(name='autodaily', aliases=['daily'], brief='Get debug info', invoke_without_command=True)
    @_is_owner()
    async def debug_autodaily(self, ctx: _Context):
        self._log_command_use(ctx)
        if ctx.invoked_subcommand is None:
            utc_now = _utils.get_utc_now()
            result = await _server_settings.get_autodaily_settings()
            json_base = []
            for autodaily_settings in result:
                json_base.append({
                    'guild_id': autodaily_settings.guild_id or '-',
                    'channel_id': autodaily_settings.channel_id or '-',
                    'change_mode': autodaily_settings.change_mode or '-',
                    'message_id': autodaily_settings.latest_message_id or '-',
                    'created_at': _utils.format.datetime(autodaily_settings.latest_message_created_at) if autodaily_settings.latest_message_created_at else '-',
                    'modified_at': _utils.format.datetime(autodaily_settings.latest_message_modified_at) if autodaily_settings.latest_message_modified_at else '-'
                })
            file_name = f'autodaily_settings_all_{_utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
            with open(file_name, 'w') as fp:
                _json.dump(json_base, fp, indent=4)
            await ctx.send(f'Retrieved {len(result)} auto-daily settings.', file=_File(file_name))
            _os.remove(file_name)


    @debug_autodaily.group(name='nopost', aliases=['new'], brief='Get debug info')
    @_is_owner()
    async def debug_autodaily_nopost(self, ctx: _Context, *, args: str = None):
        self._log_command_use(ctx)
        if ctx.invoked_subcommand is None:
            _, legacy = self._extract_dash_parameters(args, None, '--legacy')
            utc_now = _utils.get_utc_now()
            if legacy:
                result = await _server_settings.get_autodaily_settings_legacy(ctx.bot, utc_now, no_post_yet=True)
            else:
                result = await _server_settings.get_autodaily_settings(no_post_yet=True)
            json_base = []
            for autodaily_settings in result:
                json_base.append({
                    'guild_id': autodaily_settings.guild_id or '-',
                    'channel_id': autodaily_settings.channel_id or '-',
                    'change_mode': autodaily_settings.change_mode or '-',
                    'message_id': autodaily_settings.latest_message_id or '-',
                    'created_at': _utils.format.datetime(autodaily_settings.latest_message_created_at) if autodaily_settings.latest_message_created_at else '-',
                    'modified_at': _utils.format.datetime(autodaily_settings.latest_message_modified_at) if autodaily_settings.latest_message_modified_at else '-'
                })
            file_name = f'autodaily_settings_nopost_{_utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
            with open(file_name, 'w') as fp:
                _json.dump(json_base, fp, indent=4)
            await ctx.send(f'Retrieved {len(result)} auto-daily settings.', file=_File(file_name))
            _os.remove(file_name)


    @debug_autodaily.group(name='changed', brief='Get debug info')
    @_is_owner()
    async def debug_autodaily_changed(self, ctx: _Context, *, args: str = None):
        self._log_command_use(ctx)
        if ctx.invoked_subcommand is None:
            _, legacy = self._extract_dash_parameters(args, None, '--legacy')
            utc_now = _utils.get_utc_now()
            if legacy:
                result = await _server_settings.get_autodaily_settings_legacy(ctx.bot, utc_now)
            else:
                result = await _server_settings.get_autodaily_settings(utc_now=utc_now)
            json_base = []
            for autodaily_settings in result:
                json_base.append({
                    'guild_id': autodaily_settings.guild_id or '-',
                    'channel_id': autodaily_settings.channel_id or '-',
                    'change_mode': autodaily_settings.change_mode or '-',
                    'message_id': autodaily_settings.latest_message_id or '-',
                    'created_at': _utils.format.datetime(autodaily_settings.latest_message_created_at) if autodaily_settings.latest_message_created_at else '-',
                    'modified_at': _utils.format.datetime(autodaily_settings.latest_message_modified_at) if autodaily_settings.latest_message_modified_at else '-'
                })
            file_name = f'autodaily_settings_changed_{_utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
            with open(file_name, 'w') as fp:
                _json.dump(json_base, fp, indent=4)
            await ctx.send(f'Retrieved {len(result)} auto-daily settings.', file=_File(file_name))
            _os.remove(file_name)


    @_command_group(name='device', brief='list available devices', hidden=True)
    @_is_owner()
    async def device(self, ctx: _Context):
        """
        Returns all known devices stored in the DB.
        """
        self._log_command_use(ctx)
        if ctx.invoked_subcommand is None:
            output = []
            for device in _login.DEVICES.devices:
                output.append(_utils.discord.ZERO_WIDTH_SPACE)
                if device.can_login_until:
                    login_until = _utils.format.datetime(device.can_login_until)
                else:
                    login_until = '-'
                output.append(f'Key: {device.key}\nChecksum: {device.checksum}\nCan login until: {login_until}')
            output = output[1:]
            posts = _utils.discord.create_posts_from_lines(output, _utils.discord.MAXIMUM_CHARACTERS)
            for post in posts:
                await ctx.send(post)


    @device.command(name='add', brief='store device', hidden=True)
    @_is_owner()
    async def device_add(self, ctx: _Context, device_key: str):
        """
        Attempts to store a device with the given device_key in the DB.
        """
        self._log_command_use(ctx)
        try:
            device = await _login.DEVICES.add_device_by_key(device_key)
            await ctx.send(f'Added device with device key \'{device.key}\'.')
        except Exception as err:
            raise _Error(f'Could not add device with device key\'{device_key}\':```{err}```')


    @device.command(name='create', brief='create & store random device', hidden=True)
    @_is_owner()
    async def device_create(self, ctx: _Context):
        """
        Creates a new random device_key and attempts to store the new device in the DB.
        """
        self._log_command_use(ctx)
        device = await _login.DEVICES.create_device()
        try:
            await device.get_access_token()
            await ctx.send(f'Created and stored device with key \'{device.key}\'.')
        except Exception as err:
            await _login.DEVICES.remove_device(device)
            raise _Error(f'Failed to create and store device:```{err}```')


    @device.command(name='login', brief='login to a device', hidden=True)
    @_is_owner()
    async def device_login(self, ctx: _Context):
        """
        Attempts to remove a device with the given device_key from the DB.
        """
        self._log_command_use(ctx)
        try:
            device = _login.DEVICES.current
            access_token = await device.get_access_token()
            await ctx.send(f'Logged in with device \'{device.key}\'.\nObtained access token: {access_token}')
        except Exception as err:
            device = _login.DEVICES.current
            raise _Error(f'Could not log in with device \'{device.key}\':```{err}```')


    @device.command(name='remove', aliases=['delete', 'yeet'], brief='remove device', hidden=True)
    @_is_owner()
    async def device_remove(self, ctx: _Context, device_key: str):
        """
        Attempts to remove a device with the given device_key from the DB.
        """
        self._log_command_use(ctx)
        try:
            await _login.DEVICES.remove_device_by_key(device_key)
            await ctx.send(f'Removed device with device key: \'{device_key}\'.')
        except Exception as err:
            raise _Error(f'Could not remove device with device key \'{device_key}\':```{err}```')


    @device.command(name='select', brief='select a device', hidden=True)
    @_is_owner()
    async def device_select(self, ctx: _Context, device_key: str):
        """
        Attempts to select a device with the given device_key from the DB.
        """
        self._log_command_use(ctx)
        device = _login.DEVICES.select_device_by_key(device_key)
        await ctx.send(f'Selected device \'{device.key}\'.')


    @_command(name='embed', brief='Embeds your message.', hidden=True)
    @_is_owner()
    async def embed(self, ctx: _Context, *, message: str = None):
        self._log_command_use(ctx)
        colour = _utils.discord.get_bot_member_colour(self.bot, ctx.guild)
        embed = _utils.discord.create_embed('Your message in an embed', description=message, colour=colour)
        await ctx.send(embed=embed)


    @_command_group(name='list', brief='List stuff', invoke_without_command=False, hidden=True)
    @_is_owner()
    async def list_(self, ctx: _Context):
        """
        Lists stuff.
        """
        self._log_command_use(ctx)
        if not ctx.invoked_subcommand:
            ctx.send_help('list')


    @list_.command(name='commands', brief='List all top-level commands', invoke_without_command=False, hidden=True)
    @_is_owner()
    async def list_commands(self, ctx: _Context):
        """
        Lists all top-level commands.
        """
        self._log_command_use(ctx)
        commands = sorted(list(set([command.full_parent_name or command.name for command in self.bot.all_commands.values()])))
        output = [
            '```',
            *commands,
            '```',
        ]
        await _utils.discord.reply_with_output(ctx, output)


    @list_.command(name='commandtree', brief='List the full command tree', invoke_without_command=False, hidden=True)
    @_is_owner()
    async def list_commandtree(self, ctx: _Context):
        """
        Lists all commands.
        """
        self._log_command_use(ctx)
        command_tree = sorted(list(set(_get_command_tree(self.bot.all_commands.values()))))
        output = [
            '```',
            *command_tree,
            '```',
        ]
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='sales-add', brief='Add a past sale.', hidden=True)
    @_is_owner()
    async def sales_add(self, ctx: _Context, sold_on: str, price: int, currency: str, max_amount: int, *, entity_name: str):
        """
        Add a past sale to the database.
        """
        self._log_command_use(ctx)
        if price <= 0:
            error_msg = '\n'.join([
                f'Parameter `price` received an invalid value: {price}'
                f'The value must be greater than 0.'
            ])
            raise ValueError(error_msg)

        if max_amount <= 0:
            error_msg = '\n'.join([
                f'Parameter `max_amount` received an invalid value: {max_amount}'
                f'The value must be greater than 0.'
            ])
            raise ValueError(error_msg)

        currency_lower = currency.lower()
        if currency_lower.startswith('min'):
            currency_type = 'Mineral'
        elif currency_lower.startswith('gas'):
            currency_type = 'Gas'
        elif 'bux' in currency_lower:
            currency_type = 'Starbux'
        else:
            error_msg = '\n'.join([
                f'Parameter `currency` received wrong value: {currency}'
                'Valid values are: Bux, Gas, Min, Mineral, Mins, Minerals, Starbux'
            ])
            raise ValueError(error_msg)

        try:
            expires_at = _utils.parse.formatted_datetime(sold_on, include_time=False, include_tz=False, include_tz_brackets=False) + _utils.datetime.ONE_DAY
        except Exception as ex:
            error_msg = '\n'.join((
                f'Parameter `sold_on` received an invalid value: {sold_on}',
                f'Values must be dates in format: yyyy-MM-dd'
            ))
            raise ValueError(error_msg) from ex


        entities_infos = []
        characters_designs_infos = await _crew.characters_designs_retriever.get_entities_infos_by_name(entity_name)
        for entity_info in characters_designs_infos:
            entity_info['entity_type'] = 'Character'
            entity_info['entity_id'] = entity_info[_crew.CHARACTER_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)
        items_designs_infos = await _item.items_designs_retriever.get_entities_infos_by_name(entity_name)
        for entity_info in items_designs_infos:
            entity_info['entity_type'] = 'Item'
            entity_info['entity_id'] = entity_info[_item.ITEM_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)
        rooms_designs_infos = await _room.rooms_designs_retriever.get_entities_infos_by_name(entity_name)
        for entity_info in rooms_designs_infos:
            entity_info['entity_type'] = 'Room'
            entity_info['entity_id'] = entity_info[_room.ROOM_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)

        entity_info = None
        entity_id = None
        entity_type = None
        if entities_infos:
            if len(entities_infos) == 1:
                entity_info = entities_infos[0]
            else:
                paginator = _pagination.Paginator(ctx, entity_name, entities_infos, _daily.get_sales_search_details_with_id, True)
                _, entity_info = await paginator.wait_for_option_selection()
        if entity_info:
            entity_id = int(entity_info['entity_id'])
            entity_type = entity_info['entity_type']

        if entity_id:
            entity_id = int(entity_id)
            success = await _daily.add_sale(entity_id, price, currency_type, entity_type, expires_at, max_amount)
            if success:
                await ctx.send(f'Successfully added {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database.')
            else:
                await ctx.send(f'Failed adding {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database. Check the log for more information.')


    @_command(name='sales-export', brief='Export sales history.', hidden=True)
    @_is_owner()
    async def sales_export(self, ctx: _Context):
        """
        Export sales history to json.
        """
        self._log_command_use(ctx)
        sales_infos = await _daily.get_sales_infos()
        utc_now = _utils.get_utc_now()
        file_name = f'sales_history_{_utils.format.datetime(utc_now, include_tz=False, include_tz_brackets=False)}.json'
        with open(file_name, 'w') as fp:
            _json.dump(sales_infos, fp, indent=4, cls=_daily.SaleInfoEncoder)
        await ctx.send(file=_File(file_name))
        _os.remove(file_name)


    @_command(name='sales-import', brief='Import sales history.', hidden=True)
    @_is_owner()
    async def sales_import(self, ctx: _Context, *, args: str = None):
        """
        Import sales history from json.
        """
        self._log_command_use(ctx)
        if not ctx.message.attachments:
            raise _Error('You need to upload a file to be imported.')
        if len(ctx.message.attachments) > 1:
            raise _Error('Too many files provided.')

        _, overwrite, overwrite_all = self._extract_dash_parameters(args, None, '--overwrite', '--overwriteall')
        if overwrite and overwrite_all:
            raise ValueError('You may only specify one of the parameters: `--overwrite`, `--overwriteall`')

        attachment = ctx.message.attachments[0]
        file_contents = (await attachment.read()).decode('utf-8')
        if not file_contents:
            raise _Error('The file provided must not be empty.')

        sales_infos = _json.JSONDecoder(object_hook=_daily.sale_info_decoder_object_hook).decode(file_contents)
        #sales_infos = json.loads(file_contents, cls=json.JSONDecoder(object_hook=daily.sale_info_decoder_object_hook))
        if not sales_infos:
            raise _Error('The data provided must not be empty.')
        sales_infos = sorted(sales_infos, key=lambda x: x['limitedcatalogexpirydate'])

        if overwrite_all:
            await _daily.clear_sales()

        failed_sales_infos = []
        for sale_info in sales_infos:
            success = await _daily.__db_add_sale(
                sale_info.get('limitedcatalogargument'),
                sale_info.get('limitedcatalogcurrencyamount'),
                sale_info.get('limitedcatalogcurrencytype'),
                sale_info.get('limitedcatalogtype'),
                sale_info.get('limitedcatalogexpirydate'),
                sale_info.get('limitedcatalogmaxtotal'),
                overwrite=overwrite
            )
            if not success:
                failed_sales_infos.append(sale_info)

        if len(failed_sales_infos) == len(sales_infos):
            raise _Error('Could not import any sales info from the specified file.')
        output = [
            f'Successfully imported file {attachment.filename}.'
        ]
        if failed_sales_infos:
            output.append(
                f'Failed to import the following sales infos:'
            )
            output.extend([_json.dumps(sale_info) for sale_info in failed_sales_infos])
        await _daily.update_db_sales_info_cache()
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='sales-parse', brief='Parse and add a past sale.', hidden=True)
    @_is_owner()
    async def sales_parse(self, ctx: _Context, sold_on: str, *, sale_text: str):
        """
        Parse a sale from the daily news and add it to the database.
        """
        self._log_command_use(ctx)
        try:
            expires_at = _utils.parse.formatted_datetime(sold_on, include_time=False, include_tz=False, include_tz_brackets=False) + _utils.datetime.ONE_DAY
        except Exception as ex:
            error_msg = '\n'.join((
                f'Parameter `sold_on` received an invalid value: {sold_on}',
                f'Values must be dates in format: yyyy-MM-dd'
            ))
            raise ValueError(error_msg) from ex

        rx_entity_name = r'(.*?)(?= [\(\[])'
        rx_number = r'(\d+)'
        rx_currency = r'<:.+?:\d+>'

        sale_text_lines = sale_text.split('\n')
        entity_name_match = _re.search(rx_entity_name, sale_text_lines[0])
        if entity_name_match:
            entity_name = entity_name_match.group(0)
        else:
            raise _Error(f'Could not extract the entity name from: {sale_text_lines[0]}')

        price_match = _re.search(rx_number, sale_text_lines[1])
        if price_match:
            price = int(price_match.group(0))
        else:
            raise _Error(f'Could not extract the price from: {sale_text_lines[1]}')

        currency_match = _re.search(rx_currency, sale_text_lines[1])
        if currency_match:
            currency = currency_match.group(0).lower()
        else:
            raise _Error(f'Could not extract the currency from: {sale_text_lines[1]}')

        currency_type = _lookups.CURRENCY_EMOJI_LOOKUP_REVERSE.get(currency)
        if currency_type:
            currency_type = currency_type.capitalize()
        else:
            raise _Error(f'Could not convert currency emoji to currency type: {currency}')

        max_amount_match = _re.search(rx_number, sale_text_lines[2])
        if max_amount_match:
            max_amount = int(max_amount_match.group(0))
        else:
            raise _Error(f'Could not extract the currency from: {sale_text_lines[2]}')

        entities_infos = []
        characters_designs_infos = await _crew.characters_designs_retriever.get_entities_infos_by_name(entity_name)
        for entity_info in characters_designs_infos:
            entity_info['entity_type'] = 'Character'
            entity_info['entity_id'] = entity_info[_crew.CHARACTER_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)
        items_designs_infos = await _item.items_designs_retriever.get_entities_infos_by_name(entity_name)
        for entity_info in items_designs_infos:
            entity_info['entity_type'] = 'Item'
            entity_info['entity_id'] = entity_info[_item.ITEM_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)
        rooms_designs_infos = await _room.rooms_designs_retriever.get_entities_infos_by_name(entity_name)
        for entity_info in rooms_designs_infos:
            entity_info['entity_type'] = 'Room'
            entity_info['entity_id'] = entity_info[_room.ROOM_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)

        entity_info = None
        entity_id = None
        entity_type = None
        if entities_infos:
            if len(entities_infos) == 1:
                entity_info = entities_infos[0]
            else:
                paginator = _pagination.Paginator(ctx, entity_name, entities_infos, _daily.get_sales_search_details_with_id, True)
                _, entity_info = await paginator.wait_for_option_selection()
        if entity_info:
            entity_id = int(entity_info['entity_id'])
            entity_type = entity_info['entity_type']

        if entity_id:
            entity_id = int(entity_id)
            success = await _daily.add_sale(entity_id, price, currency_type, entity_type, expires_at, max_amount)
            if success:
                await ctx.send(f'Successfully added {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database.')
            else:
                await ctx.send(f'Failed adding {entity_type} \'{entity_name}\' sold on {sold_on} for {price} {currency_type} to database. Check the log for more information.')


    @_command(name='sendnews', aliases=['botnews'], brief='Send bot news to all servers.', hidden=True)
    @_is_owner()
    async def send_bot_news(self, ctx: _Context, *, news: str = None):
        """
        Sends an embed to all guilds which have a bot news channel configured.

        Usage:
        /sendnews [--test] [--<property_key>=<property_value> ...]

        Available property keys:
        --test:    Optional. Use to only send the news to the current channel.
        --title:   Mandatory. The title of the news.
        --content: Optional. The contents of the news.

        Example:
        /sendnews --title=This is a title. --content=This is the content.
        /sendnews --test --title=This is a title. --content=This is the content.
        """
        self._log_command_use(ctx)
        if not news:
            return

        _, for_testing, title, content = self._extract_dash_parameters(news, None, '--test', '--title=', '--content=')
        if not title:
            raise ValueError('You need to specify a title!')
        avatar_url = self.bot.user.avatar_url
        if not for_testing:
            for bot_news_channel in _server_settings.GUILD_SETTINGS.bot_news_channels:
                embed_colour = _utils.discord.get_bot_member_colour(self.bot, bot_news_channel.guild)
                embed: _Embed = _utils.discord.create_embed(title, description=content, colour=embed_colour)
                embed.set_thumbnail(url=avatar_url)
                try:
                    await bot_news_channel.send(embed=embed)
                except _errors.Forbidden:
                    pass
        embed_colour = _utils.discord.get_bot_member_colour(self.bot, ctx.guild)
        embed = _utils.discord.create_embed(title, description=content, colour=embed_colour)
        embed.set_thumbnail(url=avatar_url)
        await ctx.send(embed=embed)


    @_command(name='test', brief='These are testing commands, usually for debugging purposes', hidden=True)
    @_is_owner()
    async def test(self, ctx: _Context, action, *, params = None):
        self._log_command_use(ctx)
        print(f'+ called command test(self, ctx: _Context, {action}, {params}) by {ctx.author}')
        if action == 'utcnow':
            utc_now = _utils.get_utc_now()
            txt = _utils.datetime.get_discord_datestamp(utc_now, include_time=True, include_seconds=True)
            await ctx.send(txt)
        elif action == 'init':
            await _db.init_schema()
            await ctx.send('Initialized the database from scratch')
            await _utils.discord.try_delete_original_message(ctx)
        elif action == 'commands':
            output = [', '.join(sorted(self.bot.all_commands.keys()))]
            await _utils.discord.reply_with_output(ctx, output)
        elif action == 'setting':
            setting_name = params.replace(' ', '_').upper()
            result = _settings.__dict__.get(setting_name)
            if result is None:
                output = [f'Could not find a setting named `{params}`']
            else:
                if isinstance(result, str):
                    result = f'"{result}"'
                elif isinstance(result, list):
                    for i, element in enumerate(result):
                        if isinstance(element, str):
                            result[i] = f'"{element}"'
                elif isinstance(result, dict):
                    for key, value in result.items():
                        result.pop(key)
                        if isinstance(key, str):
                            key = f'"{key}"'
                        if isinstance(value, str):
                            value = f'"{value}"'
                        result[key] = value
                output = [str(result)]
            await _utils.discord.reply_with_output(ctx, output)


    @_command(name='updatecache', brief='Updates all caches manually', hidden=True)
    @_is_owner()
    async def updatecache(self, ctx: _Context):
        """
        This command is to be used to update all caches manually.
        """
        self._log_command_use(ctx)
        await _crew.characters_designs_retriever.update_cache()
        await _crew.collections_designs_retriever.update_cache()
        prestige_to_caches = list(_crew.__prestige_to_cache_dict.values())
        for prestige_to_cache in prestige_to_caches:
            await prestige_to_cache.update_data()
        prestige_from_caches = list(_crew.__prestige_from_cache_dict.values())
        for prestige_from_cache in prestige_from_caches:
            await prestige_from_cache.update_data()
        await _item.items_designs_retriever.update_cache()
        await _research.researches_designs_retriever.update_cache()
        await _room.rooms_designs_retriever.update_cache()
        await _training.trainings_designs_retriever.update_cache()
        await _daily.update_db_sales_info_cache()
        await ctx.send('Updated all caches successfully!')





def _get_command_tree(commands) -> _List[str]:
    """Returns a nested dictionary"""
    result = []
    from discord.ext.commands import Command as _Command
    from discord.ext.commands import Group as _Group
    command: _Command = None
    for command in commands:
        result.append(f'{command.full_parent_name or ""} {command.name}'.strip())
        if isinstance(command, _Group):
            result.extend(_get_command_tree(command.walk_commands()))
    return result




def setup(bot: _Bot):
    bot.add_cog(OwnerCog(bot))