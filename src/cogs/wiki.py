import os as _os
from typing import Dict as _Dict
from typing import List as _List
from typing import Tuple as _Tuple

from discord import Bot as _Bot
from discord.ext.commands import group as _command_group
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import RawCogBase as _RawCogBase
from .. import pss_achievement as _achievement
from .. import pss_ai as _ai
from .. import pss_craft as _craft
from .. import pss_crew as _crew
from ..pss_exception import Error as _Error
from .. import pss_item as _item
from .. import pss_raw as _raw
from .. import pss_research as _research
from .. import pss_room as _room
from .. import pss_ship as _ship
from .. import pss_training as _training
from .. import pss_wiki as _wiki
from .. import settings as _settings
from .. import utils as _utils


class WikiCog(_RawCogBase, name='Wiki data'):
    """
    This module offers commands to transform raw game data into data that can be used by fandom wiki Data Modules.
    """

    @_command_group(name='wiki', brief='Get transformed data for the wiki', invoke_without_command=True, hidden=True)
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki(self, ctx: _Context):
        """
        Transform data to be used in the wiki.
        """
        if ctx.invoked_subcommand is None:
            self._log_command_use(ctx)
            await _wiki.assert_allowed(ctx)
            await ctx.send_help('wiki')


    @wiki.command(name='itemdata', brief='Get transformed item data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_itemdata(self, ctx: _Context):
        """
        Transform ItemDesigns data to be used in: https://pixelstarships.fandom.com/wiki/Module:Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)

        item_data = await _item.items_designs_retriever.get_data_dict3()
        retrieved_at = _utils.get_utc_now()
        items_list: _Dict[int, _Dict] = {}
        result = []
        for item_id, item_info in item_data.items():
            if item_info.get('ItemType') != 'Equipment':
                continue

            bonus: _List[_Tuple[str, float]] = _item.get_all_enhancements(item_info)
            ingredients: _Dict[str, str] = _item.get_ingredients_dict(item_info.get('Ingredients'))
            category = _item.get_type(item_info, None)
            item_properties = {
                'name': item_info.get(_item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, ''),
                'description': item_info.get('ItemDesignDescription', ''),
                'rarity': item_info.get('Rarity', ''),
                'category': category,
                'useRecipes': f'',
                'item1ItemId': f'',
                'item1Quantity': f'',
                'item2ItemId': f'',
                'item2Quantity': f'',
                'item3ItemId': f'',
                'item3Quantity': f'',
                'item4ItemId': f'',
                'item4Quantity': f'',
            }

            for i, (bonus_value, bonus_type) in enumerate(bonus, 1):
                item_properties[f'bonus{i}Value'] = bonus_value
                item_properties[f'bonus{i}Type'] = bonus_type
            for i, (ingredient_item_id, ingredient_count) in enumerate(ingredients.items(), 1):
                item_properties[f'item{i}ItemId'] = ingredient_item_id
                item_properties[f'item{i}Quantity'] = ingredient_count
                items_list.setdefault(int(ingredient_item_id), {}).setdefault('inRecipes', []).append(item_id)

            items_list[int(item_id)] = item_properties

        items_list = {key: value for key, value in items_list.items() if 'name' in value.keys()}

        for item_id in sorted(items_list.keys()):
            item_properties = items_list[item_id]
            if 'inRecipes' in item_properties.keys():
                parents = sorted(item_properties['inRecipes'], key=lambda x: int(x))
                item_properties['useRecipes'] = f'{"|".join(parents)}'
                item_properties.pop('inRecipes')
            result.append(f'itemList["{item_id}"] = {{')
            for property_key, property_value in item_properties.items():
                result.append(f'\t{property_key} = "{property_value}"')
            result.append('}')

        if result:
            file_path = _raw.create_raw_file('\n'.join(result), 'lua', 'itemList', retrieved_at)
            await _utils.discord.post_output_with_files(ctx, [], [file_path])

            if file_path:
                _os.remove(file_path)
        else:
            raise _Error('An unexpected error occured. Please contact the bot\'s author.')


    @wiki.group(name='data', brief='Get transformed data', invoke_without_command=True)
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into the wiki's data Modules.
        """
        if ctx.invoked_subcommand is None:
            self._log_command_use(ctx)
            await _wiki.assert_allowed(ctx)


    @wiki_data.command(name='achievements', aliases=['achievement'], brief='Get transformed achievements data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_achievements(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Achievement_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _achievement.achievements_designs_retriever, 'achievement')


    @wiki_data.group(name='ai', brief='Get transformed ai data', invoke_without_command=True)
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_ai(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into an ai data Module.
        """
        if ctx.invoked_subcommand is None:
            self._log_command_use(ctx)
            await _wiki.assert_allowed(ctx)


    @wiki_data_ai.command(name='actions', aliases=['action'], brief='Get transformed ai actions data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_ai_actions(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Ai_Actions_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _ai.action_types_designs_retriever, 'aiaction')


    @wiki_data_ai.command(name='conditions', aliases=['condition'], brief='Get transformed ai conditions data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_ai_conditions(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Ai_Conditions_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _ai.condition_types_designs_retriever, 'aicondition')


    @wiki_data.command(name='collections', aliases=['collection'], brief='Get transformed collections data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_collections(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Collection_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _crew.collections_designs_retriever, 'collection')


    @wiki_data.command(name='crafts', aliases=['craft'], brief='Get transformed crafts data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_crafts(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Craft_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _craft.crafts_designs_retriever, 'craft')


    @wiki_data.command(name='crews', aliases=['crew'], brief='Get transformed crews data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_crews(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Crew_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _crew.characters_designs_retriever, 'crew')


    @wiki_data.command(name='items', aliases=['item'], brief='Get transformed items data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_items(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Item_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _item.items_designs_retriever, 'item')


    @wiki_data.command(name='missiles', aliases=['missile'], brief='Get transformed missiles data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_missiles(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Missile_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _room.missiles_designs_retriever, 'missile')


    @wiki_data.command(name='researches', aliases=['research'], brief='Get transformed researches data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_researches(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Research_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _research.researches_designs_retriever, 'research')


    @wiki_data.group(name='rooms', aliases=['room'], brief='Get transformed rooms data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_rooms(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Room_Data
        """
        if ctx.invoked_subcommand is None:
            self._log_command_use(ctx)
            await _wiki.assert_allowed(ctx)
            await _wiki.send_data_lua_file(ctx, _room.rooms_designs_retriever, 'room')


    @wiki_data_rooms.command(name='sprites', aliases=['sprite'], brief='Get transformed room sprites data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_rooms_sprites(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Room_Sprite_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _room.rooms_designs_sprites_retriever, 'roomsprite')


    @wiki_data_rooms.command(name='purchases', aliases=['purchase'], brief='Get transformed rooms purchase data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_rooms_purchases(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Room_Purchase_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _room.rooms_designs_purchases_retriever, 'roompurchase')


    @wiki_data.command(name='ships', aliases=['ship'], brief='Get transformed ships data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_ships(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Ship_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _ship.ships_designs_retriever, 'ship')


    @wiki_data.command(name='trainings', aliases=['training'], brief='Get transformed trainings data')
    @_cooldown(rate=_RawCogBase.RATE, per=_RawCogBase.COOLDOWN, type=_BucketType.user)
    async def wiki_data_trainings(self, ctx: _Context):
        """
        Polls the API and returns a string that can be inserted directly into Module:Training_Data
        """
        self._log_command_use(ctx)
        await _wiki.assert_allowed(ctx)
        await _wiki.send_data_lua_file(ctx, _training.trainings_designs_retriever, 'training')





def setup(bot: _Bot):
    if _settings.OFFER_PREFIXED_COMMANDS:
        bot.add_cog(WikiCog(bot))