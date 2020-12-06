from datetime import datetime
import json
import os
import time
from typing import Any, List

from discord.ext.commands import Context

import excel
import pss_entity as entity
import settings
from typehints import EntitiesData, EntityInfo
import utils


# ---------- Raw info ----------

async def post_raw_data(ctx: Context, retriever: entity.EntityRetriever, entity_name: str, entity_id: str) -> None:
    if ctx.author.id in settings.RAW_COMMAND_USERS:
        retrieved_at = utils.get_utc_now()
        mode = None
        if entity_id:
            if '--json' in entity_id:
                entity_id = entity_id.replace('--json', '').strip()
                mode = 'json'
            elif '--xml' in entity_id:
                entity_id = entity_id.replace('--xml', '').strip()
                mode = 'xml'
        if entity_id:
            try:
                entity_id = int(entity_id)
            except:
                raise ValueError(f'Invalid parameter specified: `{entity_id}` is not a valid entity id!')
        if entity_id:
            await __post_raw_entity(ctx, retriever, entity_name, str(entity_id), mode, retrieved_at)
        else:
            await __post_raw_file(ctx, retriever, entity_name, mode, retrieved_at)
    else:
        await ctx.send('You are not allowed to use this command. If you think this is an error, join the support server and contact the bot\'s author.')





# ---------- Helper functions ----------

def __create_raw_file(content: str, file_type: str, file_name_prefix: str, retrieved_at: datetime) -> str:
    if not file_type:
        file_type = 'txt'
    timestamp = retrieved_at.strftime('%Y%m%d-%H%M%S')
    file_name = f'{file_name_prefix}_{timestamp}.{file_type}'
    with open(file_name, 'w') as fp:
        fp.write(content)
    return file_name


def __flatten_raw_data(data: EntitiesData) -> List[EntityInfo]:
    flat_data = []
    for row in data.values():
        result_row = __flatten_raw_entity(row)
        flat_data.append(result_row)
    return flat_data


def __flatten_raw_dict_for_excel(raw_dict: EntitiesData) -> List[EntityInfo]:
    entity = {}
    result = []
    children = []
    for key, value in raw_dict.items():
        if isinstance(value, dict):
            children.extend(__flatten_raw_dict_for_excel(value))
        elif isinstance(value, list):
            for child in value:
                children.extend(__flatten_raw_dict_for_excel(child))
        else:
            entity[key] = excel.fix_field(value)
    if children:
        for child in children:
            result_entity = dict(entity)
            result_entity.update(child)
            result.append(result_entity)
    else:
        result = [entity]
    return result


def __flatten_raw_entity(entity_info: EntityInfo) -> EntityInfo:
    result = {}
    for field_name, field in entity_info.items():
        if __should_include_raw_field(field):
            if isinstance(field, dict):
                for sub_field_name, sub_field in field.items():
                    result[f'{field_name}.{sub_field_name}'] = sub_field
            else:
                result[field_name] = field
    return result


async def __post_raw_entity(ctx: Context, retriever: entity.EntityRetriever, entity_name: str, entity_id: str, mode: str, retrieved_at: datetime) -> None:
    async with ctx.typing():
        output = []
        data = await retriever.get_data_dict3()
        entity_info = data.get(entity_id, None)
        if entity_info is None:
            title = [f'Could not find raw **{entity_name}** data for id **{entity_id}**.']
        else:
            title = [f'Raw **{entity_name}** data for id **{entity_id}**:']
            if not mode:
                flat_entity = __flatten_raw_entity(entity_info)
                for key, value in flat_entity.items():
                    output.append(f'{key} = {value}')
            else:
                result = ''
                if mode == 'xml':
                    result = await retriever.get_raw_entity_info_by_id_as_xml(entity_id)
                elif mode == 'json':
                    result = await retriever.get_raw_entity_info_by_id_as_json(entity_id, fix_xml_attributes=True)
                output = result.split('\n')
        output_len = len(output) + sum([len(row) for row in output])
    if output_len > utils.discord.MAXIMUM_CHARACTERS:
        file_path = __create_raw_file('\n'.join(output), mode, f'{entity_name}_design_{entity_id}', retrieved_at)
        await utils.discord.post_output_with_files(ctx, title, [file_path])
        os.remove(file_path)
    else:
        output[0] = f'```{output[0]}'
        output[-1] += '```'
        await utils.discord.post_output(ctx, title)
        await utils.discord.post_output(ctx, output)


async def __post_raw_file(ctx: Context, retriever: entity.EntityRetriever, entity_name: str, mode: str, retrieved_at: datetime) -> None:
    async with ctx.typing():
        retrieved_at = retrieved_at or utils.get_utc_now()
        entity_name = entity_name.replace(' ', '_')
        file_name_prefix = f'{entity_name}_designs'
        raw_data = await retriever.get_raw_data()
        raw_data_dict = utils.convert.raw_xml_to_dict(raw_data, fix_attributes=True, preserve_lists=True)
        if mode == 'xml':
            file_path = __create_raw_file(raw_data, mode, file_name_prefix, retrieved_at)
        elif mode == 'json':
            data = json.dumps(raw_data_dict)
            file_path = __create_raw_file(data, mode, file_name_prefix, retrieved_at)
        else:
            #flattened_data = __flatten_raw_data(raw_data)
            start = time.perf_counter()
            flattened_data = __flatten_raw_dict_for_excel(raw_data_dict)
            time1 = time.perf_counter() - start
            file_path = excel.create_xl_from_raw_data_dict(flattened_data, file_name_prefix, retrieved_at)
            time2 = time.perf_counter() - start
            print(f'Flattening the data took {time1:.2f} seconds.')
            print(f'Creating the excel sheet took {time2:.2f} seconds.')
    await utils.discord.post_output_with_files(ctx, [], [file_path])
    os.remove(file_path)


def __should_include_raw_field(field: Any) -> bool:
    # include properties which are:
    #  - strings
    #  - non-nested dicts
    # don't include properties which are:
    #  - nested dicts
    if isinstance(field, str):
        return True
    if isinstance(field, dict):
        if field and len(field) > 0:
            field_sub_keys = [not isinstance(field[sub_key], dict) for sub_key in field.keys()]
            return all(field_sub_keys)
    return False