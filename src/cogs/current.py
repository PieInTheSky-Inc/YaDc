import datetime as _datetime
import holidays as _holidays
import os as _os
import pytz as _pytz
from typing import List as _List
from typing import Union as _Union

from discord import ApplicationContext as _ApplicationContext
from discord import Bot as _Bot
from discord import Embed as _Embed
from discord import Option as _Option
from discord import OptionChoice as _OptionChoice
from discord import slash_command as _slash_command
from discord import SlashCommandOptionType as _SlashCommandOptionType
from discord.ext.commands import command as _command
from discord.ext.commands import group as _command_group
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import CogBase as _CogBase

from .. import pagination as _pagination
from .. import pss_crew as _crew
from .. import pss_daily as _daily
from .. import pss_dropship as _dropship
from ..pss_exception import Error as _Error
from ..pss_exception import InvalidParameterValueError as _InvalidParameterValueError
from ..pss_exception import MissingParameterError as _MissingParameterError
from ..pss_exception import NotFound as _NotFound
from ..pss_exception import ParameterTypeError as _ParameterTypeError
from .. import pss_fleet as _fleet
from .. import pss_item as _item
from .. import pss_lookups as _lookups
from .. import pss_research as _research
from .. import pss_room as _room
from .. import pss_ship as _ship
from .. import pss_situation as _situation
from .. import pss_tournament as _tourney
from .. import pss_top as _top
from .. import pss_training as _training
from .. import pss_user as _user
from .. import server_settings as _server_settings
from .. import settings as _settings
from .. import utils as _utils



class CurrentDataCog(_CogBase, name='Current PSS Data'):
    """
    This module offers commands to get current game data.
    """
    _BEST_SLOT_CHOICES = [
        _OptionChoice(name='Any', value=None),
        _OptionChoice(name='Head', value='head'),
        _OptionChoice(name='Accessory', value='accessory'),
        _OptionChoice(name='Body', value='body'),
        _OptionChoice(name='Hand', value='weapon'),
        _OptionChoice(name='Weapon', value='weapon'),
        _OptionChoice(name='Leg', value='leg'),
        _OptionChoice(name='Pet', value='pet'),
        _OptionChoice(name='Module', value='module'),
    ]
    _BEST_STAT_CHOICES = [
        _OptionChoice(name='HP', value='hp'),
        _OptionChoice(name='Attack', value='atk'),
        _OptionChoice(name='Repair', value='rep'),
        _OptionChoice(name='Ability', value='abl'),
        _OptionChoice(name='Pilot', value='plt'),
        _OptionChoice(name='Science', value='sci'),
        _OptionChoice(name='Stamina', value='stam'),
        _OptionChoice(name='Engine', value='eng'),
        _OptionChoice(name='Weapon', value='wpn'),
        _OptionChoice(name='FireResistance', value='fr'),
    ]


    @_command(name='best', brief='Get best items for a slot')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def best(self, ctx: _Context, slot: str, *, stat: str = None):
        """
        Get the best enhancement item for a given slot. If multiple matches are found, matches will be shown in descending order according to their bonus.

        Usage:
        /best [slot] [stat]
        /best [item name]

        Parameters:
        slot:      Optional. The equipment slot. Use 'all' or 'any' or omit this parameter to get info for all slots. Optional. Valid values are: [all/any (for all slots), head, hat, helm, helmet, body, shirt, armor, leg, pant, pants, weapon, hand, gun, accessory, shoulder, pet]
        stat:      Mandatory. The crew stat you're looking for. Mandatory. Valid values are: [hp, health, attack, atk, att, damage, dmg, repair, rep, ability, abl, pilot, plt, science, sci, stamina, stam, stm, engine, eng, weapon, wpn, fire resistance, fire]
        item name: Optional. an item's name, whose slot and stat will be used to look up best data.

        If the parameter item_name is specified, all other parameters become optional.

        Examples:
        /best hand atk - Prints all equipment items for the weapon slot providing an attack bonus.
        /best all hp - Prints all equipment items for all slots providing a HP bonus.
        /best hp - Prints all equipment items for all slots providing a HP bonus.
        /best storm lance - Prints all equipment items for the same slot and stat as a Storm Lance.
        """
        self._log_command_use(ctx)
        item_name = slot
        if stat is not None:
            if slot is None:
                item_name = stat
            else:
                item_name += f' {stat}'
        item_name = item_name.strip().lower()

        if item_name not in _lookups.EQUIPMENT_SLOTS_LOOKUP and item_name not in _lookups.STAT_TYPES_LOOKUP:
            items_details = await _item.get_items_details_by_name(item_name)
            found_matching_items = items_details and len(items_details) > 0
            items_details = _item.filter_items_details_for_equipment(items_details)
        else:
            items_details = []
            found_matching_items = False
        if items_details:
            if len(items_details) == 1:
                item_details = items_details[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, item_name, items_details, _item.get_item_search_details, use_pagination)
                _, item_details = await paginator.wait_for_option_selection()
            slot, stat = _item.get_slot_and_stat_type(item_details)
        else:
            if found_matching_items:
                raise ValueError(f'The item `{item_name}` is not a gear type item!')
        output = await self._get_best_output(ctx, slot, stat)
        await _utils.discord.reply_with_output(ctx, output)


    @_slash_command(name='best', brief='Get best items for a slot')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def best_slash(self,
        ctx: _Context,
        stat: _Option(str, choices=_BEST_STAT_CHOICES),
        slot: _Option(str, required=False, default=None, choices=_BEST_SLOT_CHOICES)
        ):
        """
        Get the best enhancement item for a given slot.
        """
        self._log_command_use(ctx)
        output = await self._get_best_output(ctx, slot, stat)
        await _utils.discord.respond_with_output(ctx, output)


    @_command(name='builder', brief='Get ship builder links')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def builder(self, ctx: _Context, *, player_name: str):
        """
        Get links to websites offering a ship builder tool with the specific player's ship layout loaded. Currently there'll be links produced for pixelprestige.com and pixyship.com.

        Usage:
        /builder [player_name]

        Parameters:
        player_name: Mandatory. The (beginning of the) name of the player to search for.

        Examples:
        /builder Namith - Returns links to ship builder pages with the layout of the player Namith loaded.
        """
        self._log_command_use(ctx)
        exact_name = _utils.discord.get_exact_args(ctx)
        if exact_name:
            player_name = exact_name
        if not player_name:
            raise _MissingParameterError('The parameter `player_name` is mandatory.')
        user_infos = await _user.get_users_infos_by_name(player_name)

        if user_infos:
            if len(user_infos) == 1:
                user_info = user_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, player_name, user_infos, _user.get_user_search_details, use_pagination)
                _, user_info = await paginator.wait_for_option_selection()

            if user_info:
                output = await _ship.get_ship_builder_links(ctx, user_info, as_embed=(await _server_settings.get_use_embeds(ctx)))
                await _utils.discord.reply_with_output(ctx, output)
        else:
            leading_space_note = ''
            if player_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the player name.'
            raise _NotFound(f'Could not find a player named `{player_name}`.{leading_space_note}')


    @_command(name='char', aliases=['crew'], brief='Get character stats')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def char(self, ctx: _Context, level: str = None, *, crew_name: str = None):
        """
        Get the stats of a character/crew. If a level is specified, the stats will apply to the crew being on that level. Else the stats range form level 1 to 40 will be displayed.

        Usage:
        /stats <level> [name]

        Parameters:
        level: Optional. Level of a crew.
        name:  Mandatory. (Part of) the name of a crew.

        Examples:
        /stats hug - Will print the stats range for a crew having 'hug' in its name.
        /stats 25 hug - Will print the stats range for a level 25 crew having 'hug' in its name.

        Notes:
        This command will only print stats for the crew with the best matching crew_name.
        """
        self._log_command_use(ctx)
        level, crew_name = _utils.get_level_and_name(level, crew_name)
        output = await _crew.get_char_details_by_name(ctx, crew_name, level=level, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='craft', aliases=['upg', 'upgrade'], brief='Get crafting recipes')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def craft(self, ctx: _Context, *, item_name: str):
        """
        Get the items a specified item can be crafted into.

        Usage:
        /craft [item_name]
        /upgrade [item_name]
        /upg [item_name]

        Parameters:
        item_name: Mandatory. (Part of) the name of an item to be upgraded.

        Examples:
        /craft large mineral crate - Prints all crafting options for a 'Large Mineral Crate'.

        Notes:
        This command will only print crafting costs for the item with the best matching item name.
        """
        self._log_command_use(ctx)
        output = await _item.get_item_upgrades_from_name(ctx, item_name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='collection', aliases=['coll'], brief='Get collections')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def collection(self, ctx: _Context, *, collection_name: str = None):
        """
        Get the details on a specific collection. If the collection name is omitted, it will display all collections.

        Usage:
        /collection <collection_name>

        Parameters:
        collection_name: Mandatory. The name of the collection to get details on.

        Examples:
        /collection savy - Will print information on a collection having 'savy' in its name.
        /collection - Will print less information on all collections.

        Notes:
        This command will only print stats for the collection with the best matching collection_name.
        """
        self._log_command_use(ctx)
        output = await _crew.get_collection_details_by_name(ctx, collection_name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='daily', brief='Show the dailies')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN*2, type=_BucketType.guild)
    async def daily(self, ctx: _Context):
        """
        Prints the MOTD along today's contents of the dropship, the merchant ship, the shop and the sale.

        Usage:
        /daily

        Examples:
        /daily - Prints the information described above.
        """
        self._log_command_use(ctx)
        await _utils.discord.try_delete_original_message(ctx)
        as_embed = await _server_settings.get_use_embeds(ctx)
        output, output_embed, _ = await _dropship.get_dropship_text(ctx.bot, ctx.guild)
        if as_embed:
            await _utils.discord.post_output(ctx, output_embed)
        else:
            await _utils.discord.post_output(ctx, output)


    @_command_group(name='event', brief='Get current event info', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def event(self, ctx: _Context, *, params: str = None):
        """
        Prints information on currently running events in PSS.

        Usage:
        /event

        Examples:
        /event - Prints the information described above.
        """
        self._log_command_use(ctx)
        if ctx.invoked_subcommand is None:
            _, print_all, situation_id = self._extract_dash_parameters(params, None, '--all', '--id=')
            output = await _situation.get_event_details(ctx, situation_id=situation_id, all_events=print_all, as_embed=(await _server_settings.get_use_embeds(ctx)))
            await _utils.discord.reply_with_output(ctx, output)


    @event.command(name='last', aliases=['latest'], brief='Get last event info')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def event_last(self, ctx: _Context):
        """
        Prints information on the last event that ran in PSS.

        Usage:
        /event last
        /event latest

        Examples:
        /event last - Prints the information described above.
        """
        self._log_command_use(ctx)
        output = await _situation.get_event_details(ctx, latest_only=True, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='fleet', aliases=['alliance'], brief='Get infos on a fleet')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def fleet(self, ctx: _Context, *, fleet_name: str):
        """
        Get details on a fleet. This command will also create a spreadsheet containing information on a fleet's members. If the provided fleet name does not match any fleet exactly, you will be prompted to select from a list of results. The selection prompt will time out after 60 seconds.

        Usage:
        /fleet [fleet_name]
        /alliance [fleet_name]

        Parameters:
        fleet_name: Mandatory. The (beginning of the) name of the fleet to search for.

        Examples:
        /fleet HYDRA - Offers a list of fleets having a name starting with 'HYDRA'. Upon selection prints fleet details and posts the spreadsheet.
        """
        self._log_command_use(ctx)
        is_tourney_running = _tourney.is_tourney_running()
        exact_name = _utils.discord.get_exact_args(ctx)
        if exact_name:
            fleet_name = exact_name
        fleet_infos = await _fleet.get_fleet_infos_by_name(fleet_name)

        if fleet_infos:
            if len(fleet_infos) == 1:
                fleet_info = fleet_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, fleet_name, fleet_infos, _fleet.get_fleet_search_details, use_pagination)
                _, fleet_info = await paginator.wait_for_option_selection()

            if fleet_info:
                as_embed = await _server_settings.get_use_embeds(ctx)
                if is_tourney_running:
                    max_tourney_battle_attempts = await _tourney.get_max_tourney_battle_attempts()
                else:
                    max_tourney_battle_attempts = None
                output, file_paths = await _fleet.get_full_fleet_info_as_text(ctx, fleet_info, max_tourney_battle_attempts=max_tourney_battle_attempts, as_embed=as_embed)
                await _utils.discord.reply_with_output_and_files(ctx, output, file_paths, output_is_embeds=as_embed)
                for file_path in file_paths:
                    _os.remove(file_path)
        else:
            leading_space_note = ''
            if fleet_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the fleet name.'
            raise _NotFound(f'Could not find a fleet named `{fleet_name}`.{leading_space_note}')


    @_command(name='ingredients', aliases=['ing'], brief='Get item ingredients')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def ingredients(self, ctx: _Context, *, item_name: str):
        """
        Get the ingredients for an item to be crafted with their estimated crafting costs.

        Usage:
        /ingredients [item_name]
        /ing [item_name]

        Parameters:
        item_name: Mandatory. (Part of) the name of an item to be crafted.

        Examples:
        /ingredients large mineral crate - Prints the crafting costs and recipe for a 'Large Mineral Crate'.

        Notes:
        This command will only print crafting costs for the item with the best matching item name.
        """
        self._log_command_use(ctx)
        output = await _item.get_ingredients_for_item(ctx, item_name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='item', brief='Get item stats')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def item(self, ctx: _Context, *, item_name: str):
        """
        Get the stats of any item matching the given item_name.

        Usage:
        /item [item_name]

        Parameters:
        item_name: Mandatory. (Part of) the name of an item.

        Examples:
        /item hug - Will print some stats for an item having 'hug' in its name.

        Notes:
        This command will print information for all items matching the specified name.
        """
        self._log_command_use(ctx)
        output = await _item.get_item_details_by_name(ctx, item_name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='layout', brief='Get a player\'s ship layout')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def layout(self, ctx: _Context, *, player_name: str):
        """
        Searches for the given player and returns their current ship layout. The result will be delivered after 30 seconds.

        Usage:
        /layout [player_name]

        Parameters:
        player_name: Mandatory. The (beginning of the) name of the player to search for.

        Examples:
        /layout Namith - Offers a list of players having a name starting with 'Namith'. Upon selection prints the current player's ship layout.
        """
        self._log_command_use(ctx)
        start = _utils.get_utc_now()
        exact_name = _utils.discord.get_exact_args(ctx)
        if exact_name:
            player_name = exact_name
        if not player_name:
            raise _MissingParameterError('The parameter `player_name` is mandatory.')
        user_infos = await _user.get_users_infos_by_name(player_name)

        if user_infos:
            if len(user_infos) == 1:
                user_info = user_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, player_name, user_infos, _user.get_user_search_details, use_pagination)
                _, user_info = await paginator.wait_for_option_selection()

            if user_info:
                _, user_ship_info = await _ship.get_inspect_ship_for_user(user_info[_user.USER_KEY_NAME])
                if user_ship_info:
                    as_embed = await _server_settings.get_use_embeds(ctx)
                    info_message = await _utils.discord.reply_with_output(ctx, ['```Building layout, please wait...```'])
                    output, file_path = await _user.get_user_ship_layout(ctx, user_info[_user.USER_KEY_NAME], as_embed=as_embed)
                    await _utils.discord.try_delete_message(info_message)
                    await _utils.discord.reply_with_output_and_files(ctx, output, [file_path], output_is_embeds=as_embed)
                    _os.remove(file_path)
                else:
                    raise _Error('Could not get the player\'s ship data.')
        else:
            leading_space_note = ''
            if player_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the player name.'
            raise _NotFound(f'Could not find a player named `{player_name}`.{leading_space_note}')


    @_command(name='level', aliases=['lvl'], brief='Get crew levelling costs')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def level(self, ctx: _Context, from_level: str, to_level: str = None):
        """
        Shows the cost for a crew to reach a certain level.

        Usage:
        /level <from_level> [to_level]
        /lvl <from_level> [to_level]

        Parameters:
        from_level: Optional. The level from which on the requirements shall be calculated. If specified, must be lower than [to_level].
        to_level:   Mandatory. The level to which the requirements shall be calculated. Must be greater than 0 and lower than 41.

        Examples:
        /level 35 - Prints exp and gas requirements from level 1 to 35
        /level 25 35 - Prints exp and gas requirements from level 25 to 35"""
        self._log_command_use(ctx)
        if from_level and not to_level:
            to_level = from_level
            from_level = None

        if to_level:
            try:
                to_level = int(to_level)
            except:
                raise _ParameterTypeError('Parameter `to_level` must be a natural number from 2 to 40.')
        if from_level:
            try:
                from_level = int(from_level)
            except:
                raise _ParameterTypeError('Parameter `from_level` must be a natural number from 1 to 39.')

        if from_level and to_level and from_level >= to_level:
            raise ValueError('Parameter `from_level` must be smaller than parameter `to_level`.')
        output = _crew.get_level_costs(ctx, from_level, to_level, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='news', brief='Show the news')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def news(self, ctx: _Context, entry_count: str = '5'):
        """
        Prints all news in ascending order. You can

        Parameters:
        entry_count: Optional. The number of news to print. Defaults to 5.

        Usage:
        /news
        /news 3

        Examples:
        /news - Prints the latest 5 news in ascending order.
        /news 3 - Prints the latest 3 news in ascending order.
        """
        self._log_command_use(ctx)
        try:
            take = int(entry_count)
        except (TypeError, ValueError) as ex:
            raise _ParameterTypeError(f'The parameter `entry_count` must be an integer.') from ex
        await _utils.discord.try_delete_original_message(ctx)
        output = await _dropship.get_news(ctx, take=take, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='player', aliases=['user'], brief='Get infos on a player')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def player(self, ctx: _Context, *, player_name: str = None):
        """
        Get details on a player. If the provided player name does not match any player exactly, you will be prompted to select from a list of results. The selection prompt will time out after 60 seconds. Due to restrictions by SavySoda, it will print 10 options max at a time.

        Usage:
        /player [player_name]
        /user [player_name]

        Parameters:
        player_name: Mandatory. The (beginning of the) name of the player to search for.

        Examples:
        /player Namith - Offers a list of players having a name starting with 'Namith'. Upon selection prints player details.
        """
        self._log_command_use(ctx)
        exact_name = _utils.discord.get_exact_args(ctx)
        if exact_name:
            player_name = exact_name
        if not player_name:
            raise _MissingParameterError('The parameter `player_name` is mandatory.')
        user_infos = await _user.get_users_infos_by_name(player_name)

        if user_infos:
            if len(user_infos) == 1:
                user_info = user_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, player_name, user_infos, _user.get_user_search_details, use_pagination)
                _, user_info = await paginator.wait_for_option_selection()

            if user_info:
                if _tourney.is_tourney_running() and _settings.FEATURE_TOURNEYDATA_ENABLED:
                    yesterday_tourney_data = self.bot.get_cog('Fleet History').tournament_data_client.get_latest_daily_data()
                    if yesterday_tourney_data:
                        yesterday_user_info = yesterday_tourney_data.users.get(user_info[_user.USER_KEY_NAME], {})
                        user_info['YesterdayAllianceScore'] = yesterday_user_info.get('AllianceScore', '0')
                max_tourney_battle_attempts = await _tourney.get_max_tourney_battle_attempts()
                output = await _user.get_user_details_by_info(ctx, user_info, max_tourney_battle_attempts=max_tourney_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
                await _utils.discord.reply_with_output(ctx, output)
        else:
            leading_space_note = ''
            if player_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the player name.'
            raise _NotFound(f'Could not find a player named `{player_name}`.{leading_space_note}')


    @_command(name='prestige', brief='Get prestige combos of crew')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def prestige(self, ctx: _Context, *, crew_name: str):
        """
        Get the prestige combinations of the crew specified.

        Usage:
        /prestige [crew_name]

        Parameters:
        crew_name: Mandatory. (Part of) the name of the crew to be prestiged.

        Examples:
        /prestige xin - Will print all prestige combinations including the crew 'Xin'.

        Notes:
        This command will only print recipes for the crew with the best matching crew name.
        """
        self._log_command_use(ctx)
        output = await _crew.get_prestige_from_info(ctx, crew_name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='price', aliases=['fairprice', 'cost'], brief='Get item\'s prices from the PSS API')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def price(self, ctx: _Context, *, item_name: str):
        """
        Get the average price (market price) and the Savy price (fair price) in bux of the item(s) specified.

        Usage:
        /price [item_name]
        /fairprice [item_name]
        /cost [item_name]

        Parameters:
        item_name: Mandatory. (Part of) the name of an item to be crafted.

        Examples:
        /price mineral crate - Prints prices for all items having 'mineral crate' in their names.

        Notes:
        Market prices returned may not reflect the real market value, due to transfers between alts/friends.
        This command will print prices for all items matching the specified item_name.
        """
        self._log_command_use(ctx)
        output = await _item.get_item_price(ctx, item_name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='recipe', brief='Get character recipes')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def recipe(self, ctx: _Context, *, name: str):
        """
        Get the prestige recipes of the crew or the ingredients of the item specified.

        Usage:
        /recipe [name]

        Parameters:
        name: Mandatory. (Part of) the name of the crew to be prestiged into or item to be crafted.

        Examples:
        /recipe xin - Will print all prestige combinations resulting in the crew 'Xin'.
        /recipe hug - Will print all prestige combinations resulting in the crew 'Huge Hellaloya'
        /recipe medium mineral crate - Will print ingredients for the item 'Medium Mineral Crate'

        Notes:
        This command will only print recipes for the crew or item with the best matching name.
        """
        self._log_command_use(ctx)

        use_embeds = (await _server_settings.get_use_embeds(ctx))
        char_error = None
        item_error = None
        try:
            char_output = await _crew.get_prestige_to_info(ctx, name, as_embed=use_embeds)
        except _crew.PrestigeNoResultsError as e:
            raise _Error(e.msg) from e
        except _Error as e:
            char_error = e
            char_output = []

        try:
            item_output = await _item.get_ingredients_for_item(ctx, name, as_embed=use_embeds)
        except _Error as e:
            item_error = e
            item_output = []

        if char_error and item_error:
            if isinstance(char_error, _NotFound) and isinstance(item_error, _NotFound):
                raise _NotFound(f'Could not find a character or an item named `{name}`.')
            raise char_error
        else:
            if use_embeds:
                output = char_output + item_output
            else:
                output = char_output + [_utils.discord.ZERO_WIDTH_SPACE] + item_output

            await _utils.discord.reply_with_output(ctx, output)


    @_command(name='research', brief='Get research data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def research(self, ctx: _Context, *, research_name: str):
        """
        Get the details on a specific research. If multiple matches are found, only a brief summary will be provided.

        Usage:
        /research [research_name]

        Parameters:
        research_name: Mandatory. The name of the research to get details on.

        Examples:
        /research python - Will print information on all researches having 'python' in their names.

        Notes:
        This command will print information for all researches matching the specified name.
        """
        self._log_command_use(ctx)
        output = await _research.get_research_infos_by_name(research_name, ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='room', brief='Get room infos')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def room(self, ctx: _Context, *, room_name: str):
        """
        Get detailed information on a room. If more than 2 results are found, details will be omitted.

        Usage:
        /room [name]
        /room [short name] [room level]

        Parameters:
        name:       Mandatory. A room's name or part of it.
        short name: Mandatory. A room's short name (2 or 3 characters).
        room level: Mandatory. A room's level.

        Examples:
        /room mineral - Searches for rooms having 'mineral' in their names and prints their details.
        /room cloak generator lv2 - Searches for rooms having 'cloak generator lv2' in their names and prints their details.
        /room mst 3 - Searches for the lvl 3 room having the short room code 'mst'.
        """
        self._log_command_use(ctx)
        output = await _room.get_room_details_by_name(room_name, ctx=ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command_group(name='sales', brief='List expired sales', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def sales(self, ctx: _Context, *, object_name: str = None):
        """
        Get information on things that have been sold in shop in the past. This command will post the late sales price and for how many days it will be available (rounded down, so 0 days means only available today). If a parameter is given, the command will output the sales history for that object along with the original shop prices.

        Usage:
        /sales <object_name>
        /sales <object_name> --reverse

        Parameter:
        object_name: Optional. The name of the object you want to see the shop history for.
        --reverse:   Optional. Will sort the output from old to new

        Examples:
        /sales - Prints information on the last 30 sales.
        /sales Virgo - Prints information on the sale history of the crew Virgo
        /sales Flower - Prints information on the sale history of the room Flower Gardens
        """
        if ctx.invoked_subcommand is None:
            self._log_command_use(ctx)

            object_name, reverse_output = self._extract_dash_parameters(object_name, None, '--reverse')

            if object_name:
                entities_infos = []
                characters_designs_infos = await _crew.characters_designs_retriever.get_entities_infos_by_name(object_name)
                for entity_info in characters_designs_infos:
                    entity_info['entity_type'] = 'Character'
                    entity_info['entity_id'] = entity_info[_crew.CHARACTER_DESIGN_KEY_NAME]
                    entity_info['entity_name'] = entity_info[_crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                    entities_infos.append(entity_info)
                items_designs_infos = await _item.items_designs_retriever.get_entities_infos_by_name(object_name)
                for entity_info in items_designs_infos:
                    entity_info['entity_type'] = 'Item'
                    entity_info['entity_id'] = entity_info[_item.ITEM_DESIGN_KEY_NAME]
                    entity_info['entity_name'] = entity_info[_item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                    entities_infos.append(entity_info)
                rooms_designs_infos = await _room.rooms_designs_retriever.get_entities_infos_by_name(object_name)
                for entity_info in rooms_designs_infos:
                    entity_info['entity_type'] = 'Room'
                    entity_info['entity_id'] = entity_info[_room.ROOM_DESIGN_KEY_NAME]
                    entity_info['entity_name'] = entity_info[_room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                    entities_infos.append(entity_info)

                if entities_infos:
                    if len(entities_infos) == 1:
                        entity_info = entities_infos[0]
                    else:
                        entities_infos = sorted(entities_infos, key=lambda x: x['entity_name'])
                        use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                        paginator = _pagination.Paginator(ctx, object_name, entities_infos, _daily.get_sales_search_details, use_pagination)
                        _, entity_info = await paginator.wait_for_option_selection()

                    if entity_info:
                        output = await _daily.get_sales_history(ctx, entity_info, reverse=reverse_output, as_embed=(await _server_settings.get_use_embeds(ctx)))
                    else:
                        output = []
                else:
                    raise _NotFound(f'Could not find an object with the name `{object_name}`.')
            else:
                output = await _daily.get_sales_details(ctx, reverse=reverse_output, as_embed=(await _server_settings.get_use_embeds(ctx)))
            await _utils.discord.reply_with_output(ctx, output)


    @sales.command(name='bedrooms', aliases=['bed', 'beds', 'bedroom'], brief='List expired bed room sales')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def sales_bed(self, ctx: _Context, *, params: str = None):
        """
        Get information on bed rooms that have been sold in shop in the past. This command will post the original shop price.

        Usage:
        /sales bedrooms
        /sales beds --reverse

        Parameter:
        --reverse:   Optional. Will sort the output from old to new

        Examples:
        /sales beds - Prints all available information on bedroom sales.
        /sales bedrooms --reverse - Prints all available information on bedroom sales from old to new.
        """
        self._log_command_use(ctx)
        _, reverse_output = self._extract_dash_parameters(params, None, '--reverse')

        room_type = 'Bedroom'
        room_type_pretty = 'bed room'
        output = await _daily.get_sales_history_for_rooms(ctx, room_type, room_type_pretty, reverse=reverse_output, as_embed=(await _server_settings.get_use_embeds(ctx)))

        if output:
            await _utils.discord.reply_with_output(ctx, output)
        else:
            raise _Error('An unknown error ocurred, please contact the bot\'s author.')


    @sales.command(name='droidrooms', aliases=['droid', 'droids', 'droidroom'], brief='List expired droid room sales')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def sales_droid(self, ctx: _Context, *, params: str = None):
        """
        Get information on android rooms that have been sold in shop in the past. This command will post the original shop price.

        Usage:
        /sales droidrooms
        /sales droids --reverse

        Parameter:
        --reverse:   Optional. Will sort the output from old to new

        Examples:
        /sales droids - Prints all available information on android room sales.
        /sales droidrooms --reverse - Prints all available information on android room sales from old to new.
        """
        self._log_command_use(ctx)
        _, reverse_output = self._extract_dash_parameters(params, None, '--reverse')

        room_type = 'Android'
        room_type_pretty = 'droid room'
        output = await _daily.get_sales_history_for_rooms(ctx, room_type, room_type_pretty, reverse=reverse_output, as_embed=(await _server_settings.get_use_embeds(ctx)))

        if output:
            await _utils.discord.reply_with_output(ctx, output)
        else:
            raise _Error('An unknown error ocurred, please contact the bot\'s author.')


    @_command_group(name='stars', brief='Division stars', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def stars(self, ctx: _Context, *, division: str = None):
        """
        Get stars earned by each fleet during the current final tournament week.

        Usage:
        /stars
        /stars <division>

        Parameters:
        division: Optional. The letter of the division to show the star counts for. Valid values: [A, B, C, D]

        Examples:
        /stars - Prints the star count for every fleet competing in the current tournament finals.
        /stars A - Prints the star count for every fleet competing in division A in the current tournament finals.

        Notes:
        This command does not work outside of the tournament finals week.
        """
        self._log_command_use(ctx)
        if _tourney.is_tourney_running():
            if not _top.is_valid_division_letter(division):
                subcommand = self.bot.get_command('stars fleet')
                await ctx.invoke(subcommand, fleet_name=division)
                return
            else:
                output = await _top.get_division_stars(ctx, division=division, as_embed=(await _server_settings.get_use_embeds(ctx)))
            await _utils.discord.reply_with_output(ctx, output)
        else:
            cmd = self.bot.get_command('past stars')
            await ctx.invoke(cmd, month=None, year=None, division=division)


    @stars.command(name='fleet', aliases=['alliance'], brief='Fleet stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def stars_fleet(self, ctx: _Context, *, fleet_name: str = None):
        """
        Get stars earned by the specified fleet during the current final tournament week. If the provided fleet name does not match any fleet exactly, you will be prompted to select from a list of results. The selection prompt will time out after 60 seconds.

        Usage:
        /stars
        /stars fleet [fleet_name]

        Parameters:
        fleet_name: Mandatory. The (beginning of the) name of a fleet to show the star counts for.

        Examples:
        /stars fleet HYDRA - Offers a list of fleets having a name starting with 'hydra'. Upon selection, prints the star count for every member of the fleet, if it competes in the current tournament finals.

        Notes:
        If this command is being called outside of the tournament finals week, it will show historic data for the last tournament.
        """
        self._log_command_use(ctx)
        if _tourney.is_tourney_running():
            exact_name = _utils.discord.get_exact_args(ctx)
            if exact_name:
                fleet_name = exact_name
            if not fleet_name:
                raise _MissingParameterError('The parameter `fleet_name` is mandatory.')

            fleet_infos = await _fleet.get_fleet_infos_by_name(fleet_name)
            fleet_infos = [fleet_info for fleet_info in fleet_infos if fleet_info[_top.DIVISION_DESIGN_KEY_NAME] != '0']

            if fleet_infos:
                if len(fleet_infos) == 1:
                    fleet_info = fleet_infos[0]
                else:
                    use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                    paginator = _pagination.Paginator(ctx, fleet_name, fleet_infos, _fleet.get_fleet_search_details, use_pagination)
                    _, fleet_info = await paginator.wait_for_option_selection()

                if fleet_info:
                    max_tourney_battle_attempts = await _tourney.get_max_tourney_battle_attempts()
                    fleet_users_infos = await _fleet.get_fleet_users_data_by_fleet_info(fleet_info)
                    output = await _fleet.get_fleet_users_stars_from_info(ctx, fleet_info, fleet_users_infos, max_tourney_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
                    await _utils.discord.reply_with_output(ctx, output)
            else:
                raise _NotFound(f'Could not find a fleet named `{fleet_name}` participating in the current tournament.')
        else:
            cmd = self.bot.get_command('past stars fleet')
            await ctx.invoke(cmd, month=None, year=None, fleet_name=fleet_name)


    @_command(name='stats', aliases=['stat'], brief='Get item/crew stats')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def stats(self, ctx: _Context, level: str = None, *, name: str = None):
        """
        Get the stats of a character/crew or item. This command is a combination of the commands /char and /item.

        Usage:
        /stats <level> [name]

        Parameters:
        level: Optional. Level of a crew. Will only apply to crew stats.
        name:  Mandatory. (Part of) the name of a crew or item.

        Examples:
        /stats hug - Will output results of the commands '/char hug' and '/item hug'
        /stats 25 hug - Will output results of the command '/char 25 hug' and '/item hug'

        Notes:
        This command will only print stats for the crew with the best matching name.
        This command will print information for all items matching the specified name.
        """
        self._log_command_use(ctx)
        full_name = ' '.join([x for x in [level, name] if x])
        level, name = _utils.get_level_and_name(level, name)
        use_embeds = (await _server_settings.get_use_embeds(ctx))
        try:
            char_output = await _crew.get_char_details_by_name(ctx, name, level, as_embed=use_embeds)
            char_success = True
        except (_InvalidParameterValueError, _Error):
            char_output = []
            char_success = False
        try:
            item_output = await _item.get_item_details_by_name(ctx, name, as_embed=use_embeds)
            item_success = True
        except (_InvalidParameterValueError, _Error):
            item_output = []
            item_success = False

        if char_success or item_success:
            if use_embeds:
                output = char_output + item_output
            else:
                output = char_output + [_utils.discord.ZERO_WIDTH_SPACE] + item_output

            await _utils.discord.reply_with_output(ctx, output)
        else:
            raise _NotFound(f'Could not find a character or an item named `{full_name}`.')


    @_command(name='time', brief='Get PSS stardate & Melbourne time')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def time(self, ctx: _Context):
        """
        Get PSS stardate, as well as the day and time in Melbourne, Australia. Gives the name of the Australian holiday, if it is a holiday in Australia.

        Usage:
        /time

        Examples:
        /time - Prints PSS stardate, day & time in Melbourne and public holidays.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        star_date = f'Star date {_utils.datetime.get_star_date(utc_now)}'

        mel_tz = _pytz.timezone('Australia/Melbourne')
        mel_time = utc_now.replace(tzinfo=_datetime.timezone.utc).astimezone(mel_tz)
        melbourne_time = mel_time.strftime('It is %A, %H:%M in Melbourne (at Savy HQ)')

        aus_holidays = _holidays.Australia(years=utc_now.year, prov='ACT')
        mel_date = _datetime.date(mel_time.year, mel_time.month, mel_time.day)
        holiday = ('It is also a holiday in Australia', aus_holidays.get(mel_date))

        first_day_of_next_month = _utils.datetime.get_first_of_following_month(utc_now)
        time_till_next_month = ('Time until next monthly reset', f'{_utils.format.timedelta(first_day_of_next_month - utc_now, include_relative_indicator=False, include_seconds=False)} ({_utils.datetime.get_discord_datestamp(first_day_of_next_month, include_time=True)})')

        while (first_day_of_next_month.month - 1) % 3:
            first_day_of_next_month = _utils.datetime.get_first_of_following_month(first_day_of_next_month)
        time_till_next_prestige_change = ('Time until next prestige recipe changes', f'{_utils.format.timedelta(first_day_of_next_month - utc_now, include_relative_indicator=False, include_seconds=False)} ({_utils.datetime.get_discord_datestamp(first_day_of_next_month, include_time=True)})')

        fields = [(field[0], field[1], False) for field in [holiday, time_till_next_month, time_till_next_prestige_change] if field[1]]
        as_embed = await _server_settings.get_use_embeds(ctx)
        if as_embed:
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            output = [_utils.discord.create_embed(star_date, description=melbourne_time, fields=fields, colour=colour)]
        else:
            output = [star_date, melbourne_time]
            [output.append(f'{field[0]}: {field[1]}') for field in fields if field[1]]
        await _utils.discord.reply_with_output(ctx, output)


    @_command_group(name='top', brief='Prints top fleets or captains', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def top(self, ctx: _Context, *, count: str = '100'):
        """
        Prints either top fleets or captains. Prints top 100 fleets by default.

        Usage:
        /top <count>

        Parameters:
        count: Optional. The number of rows to be printed.

        Examples:
        /top - prints top 100 fleets.
        /top 30 - prints top 30 fleets."""
        self._log_command_use(ctx)
        if ctx.invoked_subcommand is None:
            if ' ' in count:
                split_count = count.split(' ')
                try:
                    count = int(split_count[0])
                except:
                    try:
                        count = int(split_count[1])
                    except:
                        raise _ParameterTypeError('Invalid parameter provided! Parameter `count` must be a natural number from 1 to 100.')
                    command = split_count[0]
                command = split_count[1]
            else:
                try:
                    count = int(count)
                except:
                    raise _ParameterTypeError('Invalid parameter provided! Parameter `count` must be a natural number from 1 to 100.')
                command = 'fleets'
            cmd = self.bot.get_command(f'top {command}')
            await ctx.invoke(cmd, count=count)


    @top.command(name='players', aliases=['player', 'captains', 'captain', 'users', 'user'], brief='Prints top captains')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def top_captains(self, ctx: _Context, count: str = '100'):
        """
        Prints top captains. Prints top 100 captains by default.

        Usage:
        /top captains <count>
        /top <count> captains

        Parameters:
        count: Optional. The number of rows to be printed.

        Examples:
        /top captains - prints top 100 captains.
        /top captains 30 - prints top 30 captains.
        /top 30 captains - prints top 30 captains."""
        self._log_command_use(ctx)

        try:
            count = int(count)
        except:
            raise _ParameterTypeError('Parameter `count` must be a natural number from 1 to 100.')

        output = await _top.get_top_captains(ctx, count, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @top.command(name='fleets', aliases=['fleet', 'alliances', 'alliance'], brief='Prints top fleets')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def top_fleets(self, ctx: _Context, count: str = '100'):
        """
        Prints top fleets. Prints top 100 fleets by default.

        Usage:
        /top fleets <count>
        /top <count> fleets

        Parameters:
        count: Optional. The number of rows to be printed.

        Examples:
        /top fleets - prints top 100 fleets.
        /top fleets 30 - prints top 30 fleets.
        /top 30 fleets - prints top 30 fleets."""
        self._log_command_use(ctx)

        try:
            count = int(count)
        except:
            raise _ParameterTypeError('Parameter `count` must be a natural number from 1 to 100.')

        output = await _top.get_top_fleets(ctx, take=count, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @_command_group(name='tournament', aliases=['tourney'], brief='Information on tournament time')
    async def tournament(self, ctx: _Context):
        """
        Get information about the starting time of the tournament.

        Usage:
        /tournament
        /tourney

        Examples:
        /tournament - Displays information about the starting time of this month's tournament.
        """
        self._log_command_use(ctx)
        if ctx.invoked_subcommand is None:
            cmd = self.bot.get_command('tournament current')
            await ctx.invoke(cmd)


    @tournament.command(name='current', brief='Information on this month\'s tournament time')
    async def tournament_current(self, ctx: _Context):
        """
        Get information about the starting time of the current month's tournament.

        Usage:
        /tournament current
        /tourney current

        Examples:
        /tournament current - Displays information about the starting time of this month's tournament.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        start_of_tourney = _tourney.get_current_tourney_start()
        embed_colour = _utils.discord.get_bot_member_colour(self.bot, ctx.guild)
        embed = _tourney.get_tourney_start_as_embed(start_of_tourney, utc_now, embed_colour)
        if (await _server_settings.get_use_embeds(ctx)):
            output = [embed]
        else:
            output = _tourney.convert_tourney_embed_to_plain_text(embed)

        await _utils.discord.reply_with_output(ctx, output)


    @tournament.command(name='next', brief='Information on next month\'s tournament time')
    async def tournament_next(self, ctx: _Context):
        """
        Get information about the starting time of the next month's tournament.

        Usage:
        /tournament next
        /tourney next

        Examples:
        /tournament next - Displays information about the starting time of next month's tournament.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        start_of_tourney = _tourney.get_next_tourney_start()
        embed_colour = _utils.discord.get_bot_member_colour(self.bot, ctx.guild)
        embed = _tourney.get_tourney_start_as_embed(start_of_tourney, utc_now, embed_colour)
        if (await _server_settings.get_use_embeds(ctx)):
            output = [embed]
        else:
            output = _tourney.convert_tourney_embed_to_plain_text(embed)

        await _utils.discord.reply_with_output(ctx, output)


    @_command(name='training', brief='Get training infos')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def training(self, ctx: _Context, *, training_name: str):
        """
        Get detailed information on a training. If more than 2 results are found, some details will be omitted.

        Usage:
        /training [name]

        Parameters:
        name: Mandatory. A room's name or part of it.

        Examples:
        /training bench - Searches for trainings having 'bench' in their names and prints their details.

        Notes:
        The training yields displayed represent the upper bound of possible yields.
        The highest yield will always be displayed on the far left.
        """
        self._log_command_use(ctx)
        output = await _training.get_training_details_from_name(training_name, ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    async def _get_best_output(self, ctx: _Union[_ApplicationContext, _Context], slot: str, stat: str) -> _Union[_List[str], _List[_Embed]]:
        slot, stat = _item.fix_slot_and_stat(slot, stat)
        output = await _item.get_best_items(ctx, slot, stat, as_embed=(await _server_settings.get_use_embeds(ctx)))
        return output





def setup(bot: _Bot):
    bot.add_cog(CurrentDataCog(bot))