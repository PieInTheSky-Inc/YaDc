#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import datetime
import discord
from discord.ext import commands
import json
import os

import excel
import pss_core as core
import pss_entity as entity
import settings
import utility as util


def __flatten_raw_dict(raw_dict: dict) -> list:
    # create one row per entity_info
    # if entity_info got a prop with children (a list):
    #   multiply entity_info times children count
    #   add respective child info
    result = []
    entity = {}
    children = []
    for key, value in raw_dict.items():
        if isinstance(value, dict):
            sub_dict = __flatten_raw_dict(value)
            entity.update(sub_dict)
        elif isinstance(value, list):
            for child in value:
                child = {f'{key[:-1]}.{k}': v for k, v in child.items()}
                flat_child = __flatten_raw_dict(child)
                children.extend(__flatten_raw_dict(flat_child))
        else:
            entity[key] = value
    if children:
        result = [dict(entity).update(child) for child in children]
    else:
        result = [entity]
    return result


def __flatten_raw_data(data: entity.EntitiesDesignsData) -> list:
    flat_data = []
    for row in data.values():
        result_row = __flatten_raw_entity(row)
        flat_data.append(result_row)
    return flat_data


def __flatten_raw_entity(entity_info: entity.EntityDesignInfo) -> dict:
    result = {}
    for field_name, field in entity_info.items():
        if __should_include_raw_field(field):
            if isinstance(field, dict):
                for sub_field_name, sub_field in field.items():
                    result[f'{field_name}.{sub_field_name}'] = sub_field
            else:
                result[field_name] = field
    return result


async def __post_raw_file(ctx: commands.Context, retriever: entity.EntityDesignsRetriever, entity_name: str, mode: str, retrieved_at: datetime.datetime):
    async with ctx.typing():
        retrieved_at = retrieved_at or util.get_utcnow()
        entity_name = entity_name.replace(' ', '_')
        file_name_prefix = f'{entity_name}_designs'
        raw_data = await retriever.get_raw_data()
        raw_data_dict = core.xmltree_to_raw_dict(raw_data, fix_attributes=True)
        if mode == 'xml':
            file_path = __create_raw_file(raw_data, mode, file_name_prefix, retrieved_at)
        elif mode == 'json':
            data = json.dumps(raw_data_dict)
            file_path = __create_raw_file(data, mode, file_name_prefix, retrieved_at)
        else:
            #flattened_data = __flatten_raw_dict(raw_data_dict)
            flattened_data = __flatten_raw_data(raw_data)
            file_path = excel.create_xl_from_raw_data_dict(flattened_data, retriever.key_name, file_name_prefix, retrieved_at)
    await util.post_output_with_files(ctx, [], [file_path])
    os.remove(file_path)


async def __post_raw_entity(ctx: commands.Context, retriever: entity.EntityDesignsRetriever, entity_name: str, entity_id: str, mode: str, retrieved_at: datetime.datetime):
    async with ctx.typing():
        output = []
        data = await retriever.get_data_dict3()
        entity_design_info = data.get(entity_id, None)
        if entity_design_info is None:
            title = [f'Could not find raw **{entity_name}** data for id **{entity_id}**.']
        else:
            title = [f'Raw **{entity_name}** data for id **{entity_id}**:']
            if not mode:
                flat_entity = __flatten_raw_entity(entity_design_info)
                for key, value in flat_entity.items():
                    output.append(f'{key} = {value}')
            else:
                if mode == 'xml':
                    result = await retriever.get_raw_entity_design_info_by_id_as_xml(entity_id)
                elif mode == 'json':
                    result = await retriever.get_raw_entity_design_info_by_id_as_json(entity_id, fix_xml_attributes=True)
                output = result.split('\n')
        output_len = len(output) + sum([len(row) for row in output])
    if output_len > settings.MAXIMUM_CHARACTERS:
        file_path = __create_raw_file('\n'.join(output), mode, f'{entity_name}_design_{entity_id}', retrieved_at)
        await util.post_output_with_files(ctx, title, [file_path])
        os.remove(file_path)
    else:
        output[0] = f'```{output[0]}'
        output[-1] += '```'
        await util.post_output(ctx, title)
        await util.post_output(ctx, output)


def __create_raw_file(content: str, file_type: str, file_name_prefix: str, retrieved_at: datetime.datetime) -> str:
    if not file_type:
        file_type = 'txt'
    timestamp = retrieved_at.strftime('%Y%m%d-%H%M%S')
    file_name = f'{file_name_prefix}_{timestamp}.{file_type}'
    with open(file_name, 'w') as fp:
        fp.write(content)
    return file_name


async def post_raw_data(ctx: commands.Context, retriever: entity.EntityDesignsRetriever, entity_name: str, entity_id: str):
    if ctx.author.id in settings.RAW_COMMAND_USERS:
        retrieved_at = util.get_utcnow()
        mode = None
        if entity_id:
            if '--json' in entity_id:
                entity_id = entity_id.replace('--json', '').strip()
                mode = 'json'
            elif '--xml' in entity_id:
                entity_id = entity_id.replace('--xml', '').strip()
                mode = 'xml'
        if entity_id:
            entity_id = int(entity_id)
        if entity_id:
            await __post_raw_entity(ctx, retriever, entity_name, str(entity_id), mode, retrieved_at)
        else:
            await __post_raw_file(ctx, retriever, entity_name, mode, retrieved_at)
    else:
        await ctx.send('You are not allowed to use this command. If you think this is an error, join the support server and contact the bot\'s author.')


def __should_include_raw_field(field) -> bool:
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