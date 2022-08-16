from discord.ext.commands import Bot as _Bot
from discord.ext.commands import group as _command_group
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import RawCogBase as _RawCogBase
from .. import pss_achievement as _achievement
from .. import pss_ai as _ai
from .. import pss_crew as _crew
from .. import pss_gm as _gm
from .. import pss_item as _item
from .. import pss_mission as _mission
from .. import pss_promo as _promo
from .. import pss_raw as _raw
from .. import pss_research as _research
from .. import pss_room as _room
from .. import pss_ship as _ship
from .. import pss_situation as _situation
from .. import pss_training as _training


class RawDataCog(_RawCogBase, name='Raw Data'):
    """
    This module offers commands to obtain raw game data.
    """

    @_command_group(name='raw', brief='Get raw data from the PSS API', invoke_without_command=True, hidden=True)
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw(self, ctx: _Context):
        """
        Get raw data from the Pixel Starships API.
        Use one of the sub-commands to retrieve data for a certain entity type. The sub-commands may have sub-commands on their own, so make sure to check the related help commands.

        Usage:
        /raw [subcommand] <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await ctx.send_help('raw')


    @raw.command(name='achievement', aliases=['achievements'], brief='Get raw achievement data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_achievement(self, ctx: _Context, *, achievement_id: str = None):
        """
        Get raw achievement design data from the PSS API.

        Usage:
        /raw achievement <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the achievement with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _achievement.achievements_designs_retriever, 'achievement', achievement_id)


    @raw.group(name='ai', brief='Get raw ai data', invoke_without_command=True)
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_ai(self, ctx: _Context):
        """
        Get raw ai design data from the PSS API.

        Usage:
        /raw ai [subcommand] <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await ctx.send_help('raw ai')


    @raw_ai.command(name='action', aliases=['actions'], brief='Get raw ai action data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_ai_action(self, ctx: _Context, ai_action_id: int = None):
        """
        Get raw ai action design data from the PSS API.

        Usage:
        /raw ai action <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the ai action with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _ai.action_types_designs_retriever, 'ai_action', ai_action_id)


    @raw_ai.command(name='condition', aliases=['conditions'], brief='Get raw ai condition data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_ai_condition(self, ctx: _Context, ai_condition_id: int = None):
        """
        Get raw ai condition design data from the PSS API.

        Usage:
        /raw ai condition <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the ai condition with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _ai.condition_types_designs_retriever, 'ai_condition', ai_condition_id)


    @raw.command(name='char', aliases=['crew', 'chars', 'crews'], brief='Get raw crew data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_char(self, ctx: _Context, *, char_id: str = None):
        """
        Get raw character design data from the PSS API.

        Usage:
        /raw char <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the character with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _crew.characters_designs_retriever, 'character', char_id)


    @raw.command(name='collection', aliases=['coll', 'collections'], brief='Get raw collection data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_collection(self, ctx: _Context, *, collection_id: str = None):
        """
        Get raw collection design data from the PSS API.

        Usage:
        /raw collection <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the collection with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _crew.collections_designs_retriever, 'collection', collection_id)


    @raw.command(name='event', aliases=['events'], brief='Get raw event data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_event(self, ctx: _Context, *, situation_id: str = None):
        """
        Get raw event design data (actually situation design data) from the PSS API.

        Usage:
        /raw event <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the event with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _situation.situations_designs_retriever, 'situation', situation_id)


    @raw.group(name='gm', aliases=['galaxymap', 'galaxy'], brief='Get raw gm data', invoke_without_command=True)
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_gm(self, ctx: _Context):
        """
        Get raw gm design data from the PSS API.

        Usage:
        /raw gm [subcommand] <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the entity of the specified type with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await ctx.send_help('raw gm')


    @raw_gm.command(name='system', aliases=['systems', 'star', 'stars'], brief='Get raw gm system data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_gm_system(self, ctx: _Context, *, star_system_id: str = None):
        """
        Get raw star system design data from the PSS API.

        Usage:
        /raw gm system <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the GM system with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _gm.star_systems_designs_retriever, 'star system', star_system_id)


    @raw_gm.command(name='path', aliases=['paths', 'link', 'links'], brief='Get raw gm path data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_gm_link(self, ctx: _Context, *, star_system_link_id: str = None):
        """
        Get raw star system link design data from the PSS API.

        Usage:
        /raw gm path <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the GM path with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _gm.star_system_links_designs_retriever, 'star system link', star_system_link_id)


    @raw.command(name='item', aliases=['items'], brief='Get raw item data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_item(self, ctx: _Context, *, item_id: str = None):
        """
        Get raw item design data from the PSS API.

        Usage:
        /raw item <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the item with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _item.items_designs_retriever, 'item', item_id)


    @raw.command(name='mission', aliases=['missions'], brief='Get raw mission data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_mission(self, ctx: _Context, *, mission_id: str = None):
        """
        Get raw mission design data from the PSS API.

        Usage:
        /raw mission <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the mission with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _mission.missions_designs_retriever, 'mission', mission_id)


    @raw.command(name='promotion', aliases=['promo', 'promotions', 'promos'], brief='Get raw promotion data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_promotion(self, ctx: _Context, *, promo_id: str = None):
        """
        Get raw promotion design data from the PSS API.

        Usage:
        /raw promotion <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the promotion with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _promo.promotion_designs_retriever, 'promotion', promo_id)


    @raw.command(name='research', aliases=['researches'], brief='Get raw research data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_research(self, ctx: _Context, *, research_id: str = None):
        """
        Get raw research design data from the PSS API.

        Usage:
        /raw research <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the research with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _research.researches_designs_retriever, 'research', research_id)


    @raw.group(name='room', aliases=['rooms'], brief='Get raw room data', invoke_without_command=True)
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_room(self, ctx: _Context, *, room_id: str = None):
        """
        Get raw room design data from the PSS API.

        Usage:
        /raw room <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the room with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command and its sub-commands are only available to certain users. If you think, you should be eligible to use these commands, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _room.rooms_designs_retriever, 'room', room_id)


    @raw_room.command(name='purchase', aliases=['purchases'], brief='Get raw room purchase data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_room_purchase(self, ctx: _Context, *, room_purchase_id: str = None):
        """
        Get raw room purchase design data from the PSS API.

        Usage:
        /raw room purchase <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the room purchase with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _room.rooms_designs_purchases_retriever, 'room purchase', room_purchase_id)


    @raw.command(name='ship', aliases=['ships', 'hull', 'hulls'], brief='Get raw ship data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_ship(self, ctx: _Context, *, ship_id: str = None):
        """
        Get raw ship design data from the PSS API.

        Usage:
        /raw ship <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the ship hull with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _ship.ships_designs_retriever, 'ship', ship_id)


    @raw.command(name='training', aliases=['trainings'], brief='Get raw training data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def raw_training(self, ctx: _Context, *, training_id: str = None):
        """
        Get raw training design data from the PSS API.

        Usage:
        /raw training <id> <format>

        Parameters:
        id:     A natural number. If specified, the command will only return the raw data for the training with the specified id.
        format: A string determining the format of the output to be returned. These are valid values:
                    • --json (JSON)
                    • --xml (raw XML as returned by the API)
                If this parameter is omitted, an Excel spreadsheet will be created or, when having specified an id, a list of properties will be printed.
        All parameters are optional.

        It may take a while for the bot to create the file, so be patient ;)
        NOTE: This command is only available to certain users. If you think, you should be eligible to use this command, please contact the author of this bot.
        """
        self._log_command_use(ctx)
        await _raw.post_raw_data(ctx, _training.trainings_designs_retriever, 'training', training_id)





def setup(bot: _Bot):
    bot.add_cog(RawDataCog(bot))