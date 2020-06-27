import aiohttp
from datetime import date, datetime, time, timedelta, timezone
import calendar
import discord
from discord.ext import commands
import jellyfish
import json
import math
import pytz
import re
import subprocess
from threading import get_ident
from typing import Dict, Iterable, List, Tuple, Union
import urllib.parse


import pss_lookups as lookups
import settings





# ---------- Constants ----------

ONE_DAY = timedelta(days=1)










# ---------- Utilities ----------

def load_json_from_file(file_path: str) -> str:
    result = None
    with open(file_path) as fp:
        result = json.load(fp)
    return result


def convert_ticks_to_seconds(ticks: int) -> float:
    if ticks:
        ticks = float(ticks)
        return ticks / 40.0
    else:
        return 0.0


def convert_python_to_camel_case(s: str) -> str:
    result = ''.join(word.title() for word in s.split('_'))
    return result


def shell_cmd(cmd):
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def get_first_of_following_month(utcnow):
    year = utcnow.year
    month = utcnow.month + 1
    if (month == 13):
        year += 1
        month = 1
    result = datetime(year, month, 1, 0, 0, 0, 0, timezone.utc)
    return result


def get_first_of_next_month(utc_now: datetime = None):
    if utc_now is None:
        utc_now = get_utcnow()
    return get_first_of_following_month(utc_now)


def get_formatted_datetime(date_time, include_tz=True, include_tz_brackets=True):
    result = date_time.strftime('%Y-%m-%d %H:%M:%S')
    if include_tz:
        tz = date_time.strftime('%Z')
        if include_tz_brackets:
            result += ' ({})'.format(tz)
        else:
            result += ' {}'.format(tz)
    return result


def parse_formatted_datetime(date_time, include_tz=True, include_tz_brackets=True):
    format_string = '%Y-%m-%d %H:%M:%S'
    if include_tz:
        if include_tz_brackets:
            format_string += ' (%Z)'
        else:
            format_string += ' %Z'
    result = datetime.strptime(date_time, format_string)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


def get_formatted_date(date_time, include_tz=True, include_tz_brackets=True):
    result = date_time.strftime('%Y-%m-%d')
    if include_tz:
        tz = date_time.strftime('%Z')
        if include_tz_brackets:
            result += ' ({})'.format(tz)
        else:
            result += ' {}'.format(tz)
    return result


def get_formatted_duration(total_seconds: int, include_relative_indicator: bool = True, include_seconds: bool = True) -> str:
    is_past = total_seconds < 0
    if is_past:
        total_seconds = abs(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    seconds = round(seconds)
    minutes = math.floor(minutes)
    if not include_seconds:
        minutes += 1
    hours = math.floor(hours)
    days = math.floor(days)
    weeks = math.floor(weeks)
    result_parts = []
    result = ''
    print_weeks = weeks > 0
    print_days = print_weeks or days > 0
    print_hours = print_days or hours > 0
    print_minutes = print_hours or minutes > 0
    if print_weeks:
        result_parts.append(f'{weeks:d}w')
    if print_days:
        result_parts.append(f'{days:d}d')
    if print_hours:
        result_parts.append(f'{hours:d}h')
    if print_minutes:
        result_parts.append(f'{minutes:d}m')
    if not result_parts or include_seconds:
        result_parts.append(f'{seconds:d}s')

    result = ' '.join(result_parts)

    if include_relative_indicator:
        if is_past:
            result = f'{result} ago'
        else:
            result = f'in {result}'
    return result



def get_formatted_timedelta(delta: timedelta, include_relative_indicator: bool = True, include_seconds: bool = True):
    total_seconds = delta.total_seconds()
    return get_formatted_duration(total_seconds, include_relative_indicator=include_relative_indicator, include_seconds=include_seconds)


def get_utcnow():
    return datetime.now(timezone.utc)


def parse_pss_datetime(pss_datetime: str) -> datetime:
    result = None
    if pss_datetime is not None:
        try:
            result = datetime.strptime(pss_datetime, settings.API_DATETIME_FORMAT_ISO)
        except ValueError:
            result = datetime.strptime(pss_datetime, settings.API_DATETIME_FORMAT_ISO_DETAILED)
        result = pytz.utc.localize(result)
    return result


async def post_output(ctx, output: list, maximum_characters: int = settings.MAXIMUM_CHARACTERS) -> None:
    if output and ctx.channel:
        await post_output_to_channel(ctx.channel, output, maximum_characters=maximum_characters)


async def post_output_to_channel(channel: Union[discord.TextChannel, discord.Member, discord.User], output: list, maximum_characters: int = settings.MAXIMUM_CHARACTERS) -> None:
    if output and channel:
        if output[-1] == settings.EMPTY_LINE:
            output = output[:-1]
        if output[0] == settings.EMPTY_LINE:
            output = output[1:]

        posts = create_posts_from_lines(output, maximum_characters)
        for post in posts:
            if post:
                await channel.send(post)


async def post_output_with_files(ctx: discord.ext.commands.Context, output: list, file_paths: list, maximum_characters: int = settings.MAXIMUM_CHARACTERS) -> None:
    if output or file_paths:
        if output:
            if output[-1] == settings.EMPTY_LINE:
                output = output[:-1]
            if output[0] == settings.EMPTY_LINE:
                output = output[1:]

        posts = create_posts_from_lines(output, maximum_characters)
        last_post_index = len(posts) - 1
        files = [discord.File(file_path) for file_path in file_paths]
        if last_post_index >= 0:
            for i, post in enumerate(posts):
                if i == last_post_index and post or files:
                    await ctx.send(content=post, files=files)
                elif post:
                    await ctx.send(content=post)


async def dm_author(ctx: discord.ext.commands.Context, output: list, maximum_characters: int = settings.MAXIMUM_CHARACTERS) -> None:
    if output and ctx.author:
        await post_output_to_channel(ctx.author, output, maximum_characters=maximum_characters)


def create_embed(title, description=None, colour=None, fields=None):
    result = discord.Embed(title=title, description=description, colour=colour)
    if fields is not None:
        for t in fields:
            result.add_field(name=t[0], value=t[1], inline=t[2])
    return result


def get_bot_member_colour(bot, guild):
    try:
        bot_member = guild.get_member(bot.user.id)
        bot_colour = bot_member.colour
        return bot_colour
    except:
        return discord.Embed.Empty


def get_embed_field_def(title=None, text=None, inline=True):
    return (title, text, inline)


def dbg_prnt(text: str) -> None:
    if settings.PRINT_DEBUG:
        print(f'[{get_utcnow()}][{get_ident()}]: {text}')


def create_posts_from_lines(lines, char_limit) -> list:
    result = []
    current_post = ''

    for line in lines:
        line_length = len(line)
        new_post_length = 1 + len(current_post) + line_length
        if new_post_length > char_limit:
            result.append(current_post)
            current_post = ''
        if len(current_post) > 0:
            current_post += '\n'

        current_post += line

    if current_post:
        result.append(current_post)

    if not result:
        result = ['']

    return result


def escape_escape_sequences(txt: str) -> str:
    if txt:
        txt = txt.replace('\\n', '\n')
        txt = txt.replace('\\r', '\r')
        txt = txt.replace('\\t', '\t')

    return txt


def get_reduced_number(num) -> (float, str):
    num = float(num)
    is_negative = num < 0
    if is_negative:
        num = abs(num)

    counter = 0
    while num >= 1000:
        counter += 1
        num /= 1000

    if is_negative:
        num *= -1
    result = float(int(math.floor(num * 10))) / 10
    return result, lookups.REDUCE_TOKENS_LOOKUP[counter]


def get_reduced_number_compact(num, max_decimal_count: int = settings.DEFAULT_FLOAT_PRECISION) -> str:
    reduced_num, multiplier = get_reduced_number(num)
    result = f'{format_up_to_decimals(reduced_num, max_decimal_count)}{multiplier}'
    return result


def is_str_in_list(value: str, lst: list, case_sensitive: bool = False) -> bool:
    if value and lst:
        if not case_sensitive:
            string = value.lower()
            lst = [item.lower() for item in lst]
        return string in lst
    return False


def format_up_to_decimals(num: float, max_decimal_count: int = settings.DEFAULT_FLOAT_PRECISION) -> str:
    result = f'{num:0.{max_decimal_count}f}'
    result = result.rstrip('0').rstrip('.')
    return result


async def get_wikia_link(page_name: str) -> str:
    page_name = '_'.join([part for part in page_name.split(' ')])
    page_name = '_'.join([part.lower().capitalize() for part in page_name.split('_')])
    result = f'{settings.WIKIA_BASE_ADDRESS}{page_name}'

    if not (await check_hyperlink(result)):
        page_name_split = page_name.split('_')
        if len(page_name_split) > 1:
            page_name = f'{page_name_split[0].upper()}_{"_".join(page_name_split[1:])}'
        else:
            page_name = page_name.upper()
    result = f'{settings.WIKIA_BASE_ADDRESS}{page_name}'

    if not (await check_hyperlink(result)):
        result = ''

    return result


async def check_hyperlink(hyperlink: str) -> bool:
    if hyperlink:
        session: aiohttp.ClientSession
        async with aiohttp.ClientSession() as session:
            response: aiohttp.ClientResponse
            async with session.get(hyperlink) as response:
                return response.status == 200
    else:
        return False


async def try_delete_original_message(ctx: discord.ext.commands.Context) -> bool:
    return await try_delete_message(ctx.message)


def get_similarity(value_to_check: str, against: str) -> float:
    result = jellyfish.jaro_winkler(value_to_check, against)
    if value_to_check.startswith(against):
        result += 1.0
    return result


def get_similarity_map(values_to_check: Iterable[str], against: str) -> dict:
    result = {}
    for value in values_to_check:
        similarity = get_similarity(value, against)
        result.setdefault(similarity, []).append(value)
    return result


def get_or_list(values: Iterable[str]) -> str:
    if not values:
        return ''
    elif len(values) == 1:
        return values[0]
    else:
        result = ', '.join(values[:-1])
        result += f' or {values[-1]}'
        return result


def sort_entities_by(entity_infos: list, order_info: list) -> list:
    """order_info is a list of tuples (property_name,transform_function,reverse)"""
    result = entity_infos
    if order_info:
        for i in range(len(order_info), 0, -1):
            property_name = order_info[i - 1][0]
            transform_function = order_info[i - 1][1]
            reverse = convert_to_boolean(order_info[i - 1][2])
            if transform_function:
                result = sorted(result, key=lambda entity_info: transform_function(entity_info[property_name]), reverse=reverse)
            else:
                result = sorted(result, key=lambda entity_info: entity_info[property_name], reverse=reverse)
        return result
    else:
        return sorted(result)


def sort_tuples_by(data: list, order_info: list) -> list:
    """order_info is a list of tuples (element index,reverse)"""
    result = data or []
    if result:
        if order_info:
            for i in range(len(order_info), 0, -1):
                element_index = order_info[i - 1][0]
                reverse = convert_to_boolean(order_info[i - 1][1])
                result = sorted(result, key=lambda data_point: data_point[element_index], reverse=reverse)
            return result
        else:
            return sorted(result)
    else:
        return result


def convert_input_to_boolean(s: str) -> bool:
    result = None
    if s:
        s = s.lower()
        if s == 'on' or s == '1' or s[0] == 't' or s[0] == 'y':
            result = True
        elif s == 'off'or s == '0' or s[0] == 'f' or s[0] == 'n':
            result = False
    return result


def convert_to_boolean(value: object, default_if_none: bool = False) -> bool:
    if value is None:
        return default_if_none
    if isinstance(value, str):
        try:
            value = bool(value)
        except:
            try:
                value = float(value)
            except:
                try:
                    value = int(value)
                except:
                    return len(value) > 0
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    if isinstance(value, float):
        return value > 0.0
    if isinstance(value, (tuple, list, dict, set)):
        return len(value) > 0
    raise NotImplementedError


def get_level_and_name(level, name) -> (int, str):
    if level is None and name is None:
        return level, name

    if level is not None and name is None:
        return None, level

    try:
        level = int(level)
    except:
        if level is not None:
            if name is None:
                name = level
            else:
                name = f'{level} {name}'
        level = None
    return level, name


def url_escape(s: str) -> str:
    if s:
        s = urllib.parse.quote(s, safe=' ')
        s = s.replace(' ', '+')
    return s


def format_excel_datetime(dt: datetime, include_seconds: bool = True) -> str:
    format_str = '%Y-%m-%d %H:%M'
    if include_seconds:
        format_str += ':%S'
    result = dt.strftime(format_str)
    return result


def convert_pss_timestamp_to_excel(pss_timestamp: str) -> str:
    dt = parse_pss_datetime(pss_timestamp)
    result = format_excel_datetime(dt)
    return result


def compare_versions(version_1: str, version_2: str) -> int:
    """Compares two version strings with format x.x.x.x

    Returns:
    -1, if version_1 is higher than version_2
    0, if version_1 is equal to version_2
    1, if version_1 is lower than version_2 """
    version_1 = version_1.strip('v')
    version_2 = version_2.strip('v')
    version_1_split = version_1.split('.')
    version_2_split = version_2.split('.')
    for i in range(0, len(version_1_split)):
        if version_1_split[i] < version_2_split[i]:
            return 1
        elif version_1_split[i] > version_2_split[i]:
            return -1
    return 0


def is_guild_channel(channel: discord.abc.Messageable) -> bool:
    if hasattr(channel, 'guild') and channel.guild:
        return True
    else:
        return False


def get_ranking(ranking: str) -> str:
    result = str(ranking)
    if result:
        if result.endswith(('4', '5', '6', '7', '8', '9', '0', '11', '12', '13')):
            result += 'th'
        elif result.endswith('1'):
            result += 'st'
        elif result.endswith('2'):
            result += 'nd'
        elif result.endswith('3'):
            result += 'rd'
    return result


def get_month_name(dt: datetime) -> str:
    result = calendar.month_name[dt.month]
    return result


def get_month_short_name(dt: datetime) -> str:
    result = calendar.month_abbr[dt.month]
    return result


def get_month_from_name(month_name: str) -> int:
    if month_name in lookups.MONTH_NAME_TO_NUMBER.keys():
        return lookups.MONTH_NAME_TO_NUMBER[month_name]
    else:
        return None


def get_month_from_short_name(month_short_name: str) -> int:
    if month_short_name in lookups.MONTH_SHORT_NAME_TO_NUMBER.keys():
        return lookups.MONTH_SHORT_NAME_TO_NUMBER[month_short_name]
    else:
        return None


def get_historic_data_note(dt: datetime) -> str:
    timestamp = get_formatted_datetime(dt)
    result = f'```This is historic data from: {timestamp}```'
    return result


def should_escape_entity_name(entity_name: str) -> bool:
    if entity_name:
        if entity_name != entity_name.strip():
            return True
        for markdown in ['_', '*', '~~', '>', '`']:
            if markdown in entity_name:
                return True
    return False


def escape_markdown(s: str) -> str:
    result = s
    if result:
        for markdown in ['_', '*', '~~', '>', '`']:
            if markdown in s:
                result = result.replace(markdown, f'\\{markdown}')
    return result


def get_seconds_to_wait(interval_length: int, utc_now: datetime = None) -> float:
    """
    interval_length: length of interval to wait in minutes
    """
    interval_length = float(interval_length)
    if utc_now is None:
        utc_now = get_utcnow()
    result = (interval_length * 60.0) - ((float(utc_now.minute) % interval_length) * 60.0) - float(utc_now.second) - float(utc_now.microsecond) / 1000000.0
    return result


def dicts_equal(d1: dict, d2: dict) -> bool:
    """
    Checks, whether the contents of two dicts are equal
    """
    if d1 and d2:
        d2_keys = d2.keys()
        for key1, value1 in d1.items():
            if key1 not in d2_keys:
                return False
            if d2[key1] != value1:
                return False
    elif not d1 and not d2:
        return True
    else:
        return False
    return True


def get_changed_value_keys(d1: dict, d2: dict, keys_to_check: list = None) -> list:
    if not keys_to_check:
        keys_to_check = list(d1.keys())
    result = []
    for key in keys_to_check:
        if key in d1:
            if key in d2:
                if d1[key] != d2[key]:
                    result.append(key)
    return result


async def try_delete_message(message: discord.Message) -> bool:
    try:
        await message.delete()
        return True
    except discord.Forbidden:
        return False


async def try_remove_reaction(reaction: discord.Reaction, user: discord.User) -> bool:
    try:
        await reaction.remove(user)
        return True
    except discord.Forbidden:
        return False


def get_exact_args(ctx: discord.ext.commands.Context, additional_parameters: int = 0) -> str:
    try:
        if ctx.command.full_parent_name:
            full_parent_command = f'{ctx.prefix}{ctx.command.full_parent_name} '
        else:
            full_parent_command = f'{ctx.prefix}'
        command_names = [ctx.command.name]
        if ctx.command.aliases:
            command_names.extend(ctx.command.aliases)
        rx_command_names = '|'.join(command_names)
        rx_command = f'{full_parent_command}({rx_command_names}) (.*? ){{{additional_parameters}}}'
        rx_match = re.search(rx_command, ctx.message.content)
        if rx_match is not None:
            return str(ctx.message.content[len(rx_match.group(0)):])
        else:
            return ''
    except:
        return ''


def get_next_day(utc_now: datetime = None) -> datetime:
    utc_now = utc_now or get_utcnow()
    result = datetime(utc_now.year, utc_now.month, utc_now.day, tzinfo=timezone.utc)
    result = result + ONE_DAY
    return result


def is_valid_month(month: str) -> bool:
    result = month and (month in lookups.MONTH_NAME_TO_NUMBER or month in lookups.MONTH_SHORT_NAME_TO_NUMBER)
    if not result:
        try:
            month = int(month)
            result = month >= 1 and month <= 12
        except (TypeError, ValueError):
            pass
    return result










#---------- DB utilities ----------
DB_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

def db_get_column_definition(column_name: str, column_type: str, is_primary: bool = False, not_null: bool = False, default: object = None) -> str:
    modifiers = []
    column_name_txt = column_name.lower()
    column_type_txt = column_type.upper()
    if is_primary:
        modifiers.append('PRIMARY KEY')
    if not_null:
        modifiers.append('NOT NULL')
    if default is not None:
        modifiers.append(f'DEFAULT {default}')
    result = f'{column_name_txt} {column_type_txt}'
    if modifiers:
        result += ' ' + ' '.join(modifiers)
    return result.strip()


def db_get_where_and_string(where_strings: list) -> str:
    if where_strings:
        return ' AND '.join(where_strings)
    else:
        return ''


def db_get_where_or_string(where_strings: list) -> str:
    if where_strings:
        return ' OR '.join(where_strings)
    else:
        return ''


def db_get_where_string(column_name: str, column_value: object, is_text_type: bool = False) -> str:
    column_name = column_name.lower()
    if column_value is None:
        return f'{column_name} IS NULL'
    if is_text_type:
        column_value = db_convert_text(column_value)
    return f'{column_name} = {column_value}'


def db_convert_boolean(value: bool) -> str:
    """Convert from python bool to postgresql BOOLEAN"""
    if value is True:
        return 'TRUE'
    elif value is False:
        return 'FALSE'
    else:
        return 'NULL'


def db_convert_text(value: object) -> str:
    """Convert from python object to postgresql TEXT"""
    if value is None:
        result = 'NULL'
    elif value:
        result = str(value)
        result = result.replace('\'', '\'\'')
        result = f'\'{result}\''
    else:
        result = ''
    return result


def db_convert_timestamp(datetime: datetime) -> str:
    """Convert from python datetime to postgresql TIMESTAMPTZ"""
    if datetime:
        result = f'TIMESTAMPTZ \'{datetime.strftime(DB_TIMESTAMP_FORMAT)}\''
        return result
    else:
        return db_convert_text(None)


def db_convert_to_boolean(db_boolean: str, default_if_none: bool = None) -> bool:
    """Convert from postgresql BOOLEAN to python bool"""
    if db_boolean is None:
        return default_if_none
    if isinstance(db_boolean, bool):
        return db_boolean
    db_upper = db_boolean.upper()
    if db_upper == 'TRUE' or db_upper == '1' or db_upper == 'T' or db_upper == 'Y' or db_upper == 'YES':
        return True
    else:
        return False


def db_convert_to_datetime(db_timestamp: str, default_if_none: bool = None) -> datetime:
    """Convert from postgresql TIMESTAMPTZ to python datetime"""
    if db_timestamp is None:
        return default_if_none
    result = datetime.strptime(db_timestamp, DB_TIMESTAMP_FORMAT)
    return result


def db_convert_to_int(db_int: str, default_if_none: bool = None) -> int:
    """Convert from postgresql INTEGER to python int"""
    if db_int is None:
        return default_if_none
    result = int(db_int)
    return result


def db_convert_to_float(db_float: str, default_if_none: bool = None) -> float:
    """Convert from postgresql NUMERIC to python float"""
    if db_float is None:
        return default_if_none
    result = float(db_float)
    return result
