import os as _os

from discord import File as _File
from discord.ext.commands import Context as _Context

from .pss_exception import Error as _Error
from .pss_entity import EntityRetriever as _EntityRetriever
from . import settings as _settings
from . import utils as _utils


async def get_data_lua(entity_retriever: _EntityRetriever) -> str:
    entities_data = await entity_retriever.get_data_dict3()
    entities = []
    for entity_id, entity_info in entities_data.items():
        properties = []
        for property_name, property_value in entity_info.items():
            property_value = str(property_value).replace('"', '\\"') if property_value else ''
            properties.append(f'{property_name}="{property_value}"')
        entity_properties = ','.join(properties)
        entity_str = f'["{entity_id}"]={{{entity_properties}}}'
        entities.append(entity_str)
    lines = [
        'p={',
        ',\n'.join(s for s in entities),
        '}',
        'return p',
        ]
    return '\n'.join(lines)


async def create_data_lua_file(entity_retriever: _EntityRetriever, entity_name: str) -> str:
    """
    Returns the file_path to the created file.
    """
    timestamp = _utils.get_utc_now().strftime('%Y%m%d-%H%M%S')
    data = await get_data_lua(entity_retriever)
    file_path = f'wiki_{entity_name}_data_{timestamp}.lua'
    with open(file_path, 'w') as fp:
        fp.write(data)
    return file_path


async def send_data_lua_file(ctx: _Context, entity_retriever: _EntityRetriever, entity_name: str) -> None:
    file_path = await create_data_lua_file(entity_retriever, entity_name)
    await ctx.send(file=_File(file_path))
    _os.remove(file_path)


async def assert_allowed(ctx: _Context) -> None:
    if not (await ctx.bot.is_owner(ctx.author)):
        if ctx.guild.id not in _settings.WIKI_COMMAND_GUILDS:
            if ctx.author.id not in _settings.WIKI_COMMAND_USERS:
                raise _Error('You are not allowed to use this command.')