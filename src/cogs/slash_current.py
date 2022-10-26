import datetime as _datetime
import holidays as _holidays
import os as _os
import pytz as _pytz

from discord import ApplicationContext as _ApplicationContext
from discord import Option as _Option
from discord import OptionChoice as _OptionChoice
from discord import slash_command as _slash_command
from discord import SlashCommandGroup as _SlashCommandGroup
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import CurrentCogBase as _CurrentCogBase

from .. import pagination as _pagination
from .. import pss_crew as _crew
from .. import pss_daily as _daily
from .. import pss_dropship as _dropship
from ..pss_exception import Error as _Error
from ..pss_exception import InvalidParameterValueError as _InvalidParameterValueError
from ..pss_exception import NotFound as _NotFound
from .. import pss_fleet as _fleet
from .. import pss_item as _item
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
from ..yadc_bot import YadcBot as _YadcBot



class CurrentDataSlashCog(_CurrentCogBase, name='Current PSS Data Slash'):
    _BEST_SLOT_CHOICES = [
        _OptionChoice(name='Any', value=''),
        _OptionChoice(name='Head', value='head'),
        _OptionChoice(name='Accessory', value='accessory'),
        _OptionChoice(name='Body', value='body'),
        _OptionChoice(name='Weapon/Hand', value='weapon'),
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


    @_slash_command(name='best', brief='Get best items for a slot')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def best_slash(self,
        ctx: _ApplicationContext,
        slot: _Option(str, 'Enter ', choices=_BEST_SLOT_CHOICES),
        stat: _Option(str, 'Enter ', choices=_BEST_STAT_CHOICES)
        ):
        """
        Get the best equipment for a given slot.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _item.get_best_items(ctx, slot, stat, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='builder', brief='Get ship builder links')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def builder_slash(self,
            ctx: _ApplicationContext,
            name: _Option(str, 'Enter player name.')
        ):
        """
        Get links to websites offering a ship builder tool with the specific player's ship layout loaded.
        """
        self._log_command_use(ctx)

        user_info, response = await _user.find_user(ctx, name)

        if user_info:
            await _utils.discord.edit_original_response(ctx, response, content='Player found. Building layout links, please wait...', embeds=[], view=None)
            as_embed = await _server_settings.get_use_embeds(ctx)
            output = await _ship.get_ship_builder_links(ctx, user_info, as_embed=as_embed)
            await _utils.discord.edit_original_response(ctx, response, output=output)


    @_slash_command(name='char', brief='Get character stats')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def char_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter crew name.'),
        level: _Option(int, 'Enter crew level.', min_value=1, max_value=40, required=False) = None
    ):
        """
        Get the stats of a character/crew at a specific level or ranging from level 1 to 40.
        """
        await self._perform_char_command(ctx, name, level)


    @_slash_command(name='collection', brief='Get collection stats')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def collection_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter collection name.', required=False) = None
    ):
        """
        Get the details on a collection. If no collection is specified, will display all collections.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _crew.get_collection_details_by_name(ctx, name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='craft', brief='Get crafting recipes')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def craft_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter item name.')
    ):
        """
        Get the items a specified item can be crafted into.
        """
        await self._perform_craft_command(ctx, name)


    @_slash_command(name='crew', brief='Get character stats')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def crew_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter crew name.'),
        level: _Option(int, 'Enter crew level.', min_value=1, max_value=40, required=False) = None
    ):
        """
        Get the stats of a character/crew at a specific level or ranging from level 1 to 40.
        """
        await self._perform_char_command(ctx, name, level)


    @_slash_command(name='daily', brief='Show the dailies')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN*2, type=_BucketType.guild)
    async def daily_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Prints the MOTD along today's contents of the dropship etc.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        as_embed = await _server_settings.get_use_embeds(ctx)
        output, output_embed, _ = await _dropship.get_dropship_text(ctx.bot, ctx.guild)
        if as_embed:
            await _utils.discord.respond_with_output(ctx, output_embed)
        else:
            await _utils.discord.respond_with_output(ctx, output)


    _event_slash_group = _SlashCommandGroup('event', 'Get in-game event info')

    @_event_slash_group.command(name='current', brief='Get current event info')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def event_current_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Prints information on currently running events in PSS.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _situation.get_event_details(ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_event_slash_group.command(name='last', brief='Get last event info')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def event_last_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Prints information on the last event that ran in PSS.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _situation.get_event_details(ctx, latest_only=True, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='fleet', brief='Get infos on a fleet')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def fleet_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter fleet name.')
    ):
        """
        Get info on a fleet and its members.
        """
        self._log_command_use(ctx)

        fleet_info, response = await _fleet.find_fleet(ctx, name)
        await _utils.discord.edit_original_response(ctx, response, content='Fleet found. Compiling fleet info...', embeds=[], view=None)
        is_tourney_running = _tourney.is_tourney_running()
        max_tourney_battle_attempts = (await _tourney.get_max_tourney_battle_attempts()) if is_tourney_running else None
        output, file_paths = await _fleet.get_full_fleet_info_as_text(ctx, fleet_info, max_tourney_battle_attempts=max_tourney_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))

        await _utils.discord.edit_original_response(ctx, response, output=output, file_paths=file_paths)
        for file_path in file_paths:
            _os.remove(file_path)


    @_slash_command(name='ingredients', brief='Get item ingredients')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def ingredients_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter item name.')
    ):
        """
        Get the ingredients for an item to be crafted with their estimated crafting costs.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _item.get_ingredients_for_item(ctx, name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='item', brief='Get item stats')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def item_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter item name.')
    ):
        """
        Get the stats of any item matching the given item name.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _item.get_item_details_by_name(ctx, name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='layout', brief='Get a player\'s ship layout')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def layout_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter player name.')
    ):
        """
        Searches for the given player and returns their current ship layout.
        """
        self._log_command_use(ctx)

        user_info, response = await _user.find_user(ctx, name)

        if user_info:
            await _utils.discord.edit_original_response(ctx, response, content='Player found.')
            _, user_ship_info = await _ship.get_inspect_ship_for_user(user_info[_user.USER_KEY_NAME])
            if user_ship_info:
                await _utils.discord.edit_original_response(ctx, response, content='Building layout, please wait...', embeds=[], view=None)
                output, file_path = await _user.get_user_ship_layout(ctx, user_info[_user.USER_KEY_NAME], as_embed=(await _server_settings.get_use_embeds(ctx)))

                await _utils.discord.edit_original_response(ctx, response, output=output, file_paths=[file_path])
                _os.remove(file_path)
            else:
                raise _Error('Could not get the player\'s ship data.')


    @_slash_command(name='level', brief='Get crew levelling costs')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def level_slash(self,
        ctx: _ApplicationContext,
        from_level: _Option(int, 'Enter the current level. Default is 1.', min_value=1, max_value=39, default=1),
        to: _Option(int, 'Enter the target level. Default is 40.', min_value=2, max_value=40, default=40)
    ):
        """
        Shows the cost for a crew to reach a certain level.
        """
        self._log_command_use(ctx)

        if from_level >= to:
            raise ValueError('Parameter `from_level` must be smaller than parameter `to_level`.')
        output = _crew.get_level_costs(ctx, from_level, to, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='news', brief='Show the news')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def news_slash(self,
        ctx: _ApplicationContext,
        count: _Option(int, 'Enter number of entries to be displayed.', min_value=1, default=1)
    ):
        """
        Prints news in ascending order.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _dropship.get_news(ctx, take=count, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='player', brief='Get infos on a player')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def player_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter player name.')
    ):
        """
        Get details on a player.
        """
        self._log_command_use(ctx)

        user_info, response = await _user.find_user(ctx, name)

        await _utils.discord.edit_original_response(ctx, response, content='Player found. Compiling player info...', embeds=[], view=None)
        if _tourney.is_tourney_running() and _settings.FEATURE_TOURNEYDATA_ENABLED:
            yesterday_tourney_data = self.bot.tournament_data_client.get_latest_daily_data()
            if yesterday_tourney_data:
                yesterday_user_info = yesterday_tourney_data.users.get(user_info[_user.USER_KEY_NAME], {})
                user_info['YesterdayAllianceScore'] = yesterday_user_info.get('AllianceScore', '0')
        max_tourney_battle_attempts = await _tourney.get_max_tourney_battle_attempts()
        output = await _user.get_user_details_by_info(ctx, user_info, max_tourney_battle_attempts=max_tourney_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_response(ctx, response, output=output)


    @_slash_command(name='prestige', brief='Get prestige combos of crew')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def prestige_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter crew name.')
    ):
        """
        Get the prestige combinations of the crew specified.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _crew.get_prestige_from_info(ctx, name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='price', brief='Get item\'s prices from the PSS API')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def price_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter item name.')
    ):
        """
        Get the average price (market price) and the Savy Fair Price in bux of the item(s) specified.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _item.get_item_price(ctx, name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='recipe', brief='Get crew/item recipes')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def recipe_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter crew or item name.')
    ):
        """
        Get the prestige recipes of the crew or the ingredients of the item specified.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
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

            await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='research', brief='Get research data')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def research_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter research name.')
    ):
        """
        Get the details on one or more specific research(es).
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _research.get_research_infos_by_name(name, ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='room', brief='Get room infos')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def room_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter room name or abbreviation/short name.'),
        level: _Option(int, 'Enter room level.', min_value=1, required=False) = None
    ):
        """
        Get detailed information on one or more rooms.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        room_name = name
        if level:
            room_name += str(level)
        output = await _room.get_room_details_by_name(room_name, ctx=ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    sales_slash: _SlashCommandGroup = _SlashCommandGroup('sales', 'Get information about past sales.')

    @sales_slash.command(name='recent', brief='List recently expired sales')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def sales_recent_slash(self,
        ctx: _ApplicationContext,
    ):
        """
        Get information on things that have been sold in shop over the last 30 days.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _daily.get_sales_details(ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @sales_slash.command(name='of', brief='List all sales of a specific crew, item or room.')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def sales_of_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter crew, item or room name.')
    ):
        """
        Get information on things that have been sold in shop in the past.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()

        entities_infos = []
        characters_designs_infos = await _crew.characters_designs_retriever.get_entities_infos_by_name(name)
        for entity_info in characters_designs_infos:
            entity_info['entity_type'] = 'Character'
            entity_info['entity_id'] = entity_info[_crew.CHARACTER_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)
        items_designs_infos = await _item.items_designs_retriever.get_entities_infos_by_name(name)
        for entity_info in items_designs_infos:
            entity_info['entity_type'] = 'Item'
            entity_info['entity_id'] = entity_info[_item.ITEM_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)
        rooms_designs_infos = await _room.rooms_designs_retriever.get_entities_infos_by_name(name)
        for entity_info in rooms_designs_infos:
            entity_info['entity_type'] = 'Room'
            entity_info['entity_id'] = entity_info[_room.ROOM_DESIGN_KEY_NAME]
            entity_info['entity_name'] = entity_info[_room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            entities_infos.append(entity_info)


        if entities_infos:
            if len(entities_infos) == 1:
                entity_info = entities_infos[0]
            else:
                entities_infos.sort(key=lambda entity: entity['entity_name'])
                entities_infos = entities_infos[:25]

                options = {entity_info['entity_name']: (entity_info['entity_name'], entity_info) for entity_info in entities_infos}
                view = _pagination.SelectView(ctx, 'Please select.', options)
                entity_info = await view.wait_for_selection(ctx.interaction)

            if entity_info:
                output = await _daily.get_sales_history(ctx, entity_info, as_embed=(await _server_settings.get_use_embeds(ctx)))
            else:
                output = []
        else:
            raise _NotFound(f'Could not find a crew, an item or a room with the name `{name}`.')
        if ctx.interaction.response.is_done():
            await _utils.discord.edit_original_response(ctx.interaction, output)
        else:
            await _utils.discord.respond_with_output(ctx, output)


    @sales_slash.command(name='beds', brief='List expired bed room sales.')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def sales_beds_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Get information on bed rooms that have been sold in shop in the past.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        room_type = 'Bedroom'
        room_type_pretty = 'bed room'
        output = await _daily.get_sales_history_for_rooms(ctx, room_type, room_type_pretty, as_embed=(await _server_settings.get_use_embeds(ctx)))

        if output:
            await _utils.discord.respond_with_output(ctx, output)
        else:
            raise _Error('An unknown error ocurred, please contact the bot\'s author.')


    @sales_slash.command(name='droidrooms', brief='List expired droid room sales.')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def sales_droidrooms_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Get information on android rooms that have been sold in shop in the past.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        room_type = 'Android'
        room_type_pretty = 'droid room'
        output = await _daily.get_sales_history_for_rooms(ctx, room_type, room_type_pretty, as_embed=(await _server_settings.get_use_embeds(ctx)))

        if output:
            await _utils.discord.respond_with_output(ctx, output)
        else:
            raise _Error('An unknown error ocurred, please contact the bot\'s author.')


    @_slash_command(name='stars', brief='Division stars')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def stars_slash(self,
        ctx: _ApplicationContext,
        division: _Option(str, 'Enter division letter.', choices=_top.DIVISION_CHOICES, default=None, required=False) = None
    ):
        """
        Get stars earned by each fleet during the current final tournament week.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        if _tourney.is_tourney_running():
            output = await _top.get_division_stars(ctx, division=division, as_embed=(await _server_settings.get_use_embeds(ctx)))
            await _utils.discord.respond_with_output(ctx, output)
        elif _settings.FEATURE_TOURNEYDATA_ENABLED:
            cmd = self.bot.get_application_command('past stars division')
            await ctx.invoke(cmd, division)
        else:
            raise _Error('There is no tournament running currently!')


    @_slash_command(name='starsfleet', brief='Fleet stars')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def starsfleet_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter fleet name.')
    ):
        """
        Get stars earned by the specified fleet during the current final tournament week.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        if _tourney.is_tourney_running():
            response = await _utils.discord.respond_with_output(ctx, ['Searching fleet...'])
            fleet_infos = await _fleet.get_current_tournament_fleet_infos_by_name(name)
            fleet_infos.sort(key=lambda fleet: fleet[_fleet.FLEET_DESCRIPTION_PROPERTY_NAME])
            fleet_infos = fleet_infos[:25]
            if fleet_infos:
                if len(fleet_infos) == 1:
                    fleet_info = fleet_infos[0]
                else:
                    options = {fleet_info[_fleet.FLEET_KEY_NAME]: (_fleet.get_fleet_search_details(fleet_info), fleet_info) for fleet_info in fleet_infos}
                    view = _pagination.SelectView(ctx, 'Please select a fleet.', options)
                    fleet_info = await view.wait_for_selection(response)

                if fleet_info:
                    max_tourney_battle_attempts = await _tourney.get_max_tourney_battle_attempts()
                    fleet_users_infos = await _fleet.get_fleet_users_data_by_fleet_info(fleet_info)
                    output = await _fleet.get_fleet_users_stars_from_info(ctx, fleet_info, fleet_users_infos, max_tourney_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
                    await _utils.discord.edit_original_response(ctx, response, output=output)
            else:
                raise _NotFound(f'Could not find a fleet named `{name}` participating in the current tournament.')
        elif _settings.FEATURE_TOURNEYDATA_ENABLED:
            cmd = self.bot.get_application_command('past stars fleet')
            await ctx.invoke(cmd, name)
        else:
            raise _Error('There is no tournament running currently!')


    @_slash_command(name='stats', aliases=['stat'], brief='Get crew/item stats')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def stats_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter crew or item name.'),
        level: _Option(int, 'Enter crew level', min_value=1, max_value=40, default=None, required=False),
    ):
        """
        Get the stats of a character/crew or item.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
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

            await _utils.discord.respond_with_output(ctx, output)
        else:
            raise _NotFound(f'Could not find a character or an item named `{name}`.')


    @_slash_command(name='time', brief='Get PSS stardate & Melbourne time')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def time_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Get PSS stardate, as well as the day and time in Melbourne, Australia.
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
        await _utils.discord.respond_with_output(ctx, output)


    top_slash: _SlashCommandGroup = _SlashCommandGroup('top', 'Get info on the best players and fleets.')

    @top_slash.command(name='players', brief='Prints top players')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def top_captains_slash(self,
        ctx: _ApplicationContext,
        count: _Option(int, 'Enter the number of entries to be displayed', min_value=1, max_value=100, default=100, required=False)
    ):
        """
        Prints top captains. Prints top 100 captains by default.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _top.get_top_captains(ctx, count, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @top_slash.command(name='fleets', brief='Prints top fleets')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def top_fleets_slash(self,
        ctx: _ApplicationContext,
        count: _Option(int, 'Enter the number of entries to be displayed', min_value=1, max_value=100, default=100, required=False)
    ):
        """
        Prints top fleets. Prints top 100 fleets by default.
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _top.get_top_fleets(ctx, take=count, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    tournament_slash: _SlashCommandGroup = _SlashCommandGroup('tournament', 'Get tournament start and end date.')

    @tournament_slash.command(name='current', brief='Information on this month\'s tournament time')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def tournament_current_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Get information about the starting time of the current month's tournament.
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

        await _utils.discord.respond_with_output(ctx, output)


    @tournament_slash.command(name='next', brief='Information on next month\'s tournament time')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def tournament_next_slash(self,
        ctx: _ApplicationContext
    ):
        """
        Get information about the starting time of the next month's tournament.
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

        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='training', brief='Get training infos')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def training_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter training name.')
    ):
        """
        Get detailed information on one or more training(s).
        """
        self._log_command_use(ctx)

        await ctx.interaction.response.defer()
        output = await _training.get_training_details_from_name(name, ctx, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @_slash_command(name='upgrade', brief='Get crafting recipes')
    @_cooldown(rate=_CurrentCogBase.RATE, per=_CurrentCogBase.COOLDOWN, type=_BucketType.user)
    async def upgrade_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter item name.')
    ):
        """
        Get the items a specified item can be crafted into.
        """
        await self._perform_craft_command(ctx, name)


    async def _perform_char_command(self, ctx: _ApplicationContext, crew_name: str, level: int = None) -> None:
        self._log_command_use(ctx)

        output = await _crew.get_char_details_by_name(ctx, crew_name, level=level, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    async def _perform_craft_command(self, ctx: _ApplicationContext, item_name: str) -> None:
        self._log_command_use(ctx)

        output = await _item.get_item_upgrades_from_name(ctx, item_name, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)





def setup(bot: _YadcBot):
    bot.add_cog(CurrentDataSlashCog(bot))