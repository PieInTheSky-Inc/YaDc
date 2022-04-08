from pss_entity import EntityRetriever as _EntityRetriever
import utils as _utils


async def get_data_lua(entity_retriever: _EntityRetriever) -> str:
    entities_data = await entity_retriever.get_data_dict3()
    entities = []
    for entity_id, entity_info in entities_data.items():
        entity_properties = ','.join(f'{property_name}="{property_value}"' for property_name, property_value in entity_info.items())
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