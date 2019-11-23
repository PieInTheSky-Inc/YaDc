from datetime import date, datetime, time, timedelta, timezone
import discord
import requests
import jellyfish
import json
import math
import pytz
import subprocess
import urllib.parse


import pss_lookups as lookups
import settings


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


def get_first_of_next_month():
    utcnow = get_utcnow()
    return get_first_of_following_month(utcnow)


def get_formatted_datetime(date_time, include_tz=True, include_tz_brackets=True):
    result = date_time.strftime('%Y-%m-%d %H:%M:%S')
    if include_tz:
        tz = date_time.strftime('%Z')
        if include_tz_brackets:
            result += ' ({})'.format(tz)
        else:
            result += ' {}'.format(tz)
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


def get_formatted_duration(total_seconds: int, include_relative_indicator: bool = True) -> str:
    is_past = total_seconds < 0
    if is_past:
        total_seconds = abs(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    seconds = round(seconds)
    minutes = math.floor(minutes)
    hours = math.floor(hours)
    days = math.floor(days)
    weeks = math.floor(weeks)
    result = ''
    print_weeks = weeks > 0
    print_days = print_weeks or days > 0
    print_hours = print_days or hours > 0
    print_minutes = print_hours or minutes > 0
    if print_weeks:
        result += f'{weeks:d}w '
    if print_days:
        result += f'{days:d}d '
    if print_hours:
        result += f'{hours:d}h '
    if print_minutes:
        result += f'{minutes:d}m '
    result += f'{seconds:d}s'

    if include_relative_indicator:
        if is_past:
            result = f'{result} ago'
        else:
            result = f'in {result}'
    return result



def get_formatted_timedelta(delta, include_relative_indicator=True):
    total_seconds = delta.total_seconds()
    return get_formatted_duration(total_seconds, include_relative_indicator=include_relative_indicator)


def get_utcnow():
    return datetime.now(timezone.utc)


def parse_pss_datetime(pss_datetime: str) -> datetime:
    pss_format = '%Y-%m-%dT%H:%M:%S'
    detailed_pss_format = '%Y-%m-%dT%H:%M:%S.%f'
    result = None
    try:
        result = datetime.strptime(pss_datetime, pss_format)
    except ValueError:
        result = datetime.strptime(pss_datetime, detailed_pss_format)
    result = pytz.utc.localize(result)
    return result


async def post_output(ctx, output: list, maximum_characters: int = settings.MAXIMUM_CHARACTERS) -> list:
    if output and ctx.channel:
        await post_output_to_channel(ctx.channel, output, maximum_characters=maximum_characters)


async def post_output_to_channel(text_channel: discord.TextChannel, output: list, maximum_characters: int = settings.MAXIMUM_CHARACTERS) -> list:
    if output and text_channel:
        if output[-1] == settings.EMPTY_LINE:
            output = output[:-1]
        if output[0] == settings.EMPTY_LINE:
            output = output[1:]

        posts = create_posts_from_lines(output, maximum_characters)
        for post in posts:
            if post:
                await text_channel.send(post)


async def post_output_with_file(ctx, output: list, file_path: str, maximum_characters: int = settings.MAXIMUM_CHARACTERS) -> list:
    if output:
        if output[-1] == settings.EMPTY_LINE:
            output = output[:-1]
        if output[0] == settings.EMPTY_LINE:
            output = output[1:]

        posts = create_posts_from_lines(output, maximum_characters)
        last_post_index = len(posts) - 1
        if last_post_index >= 0:
            for i, post in enumerate(posts):
                if post:
                    if i == last_post_index:
                        await ctx.send(content=post, file=discord.File(file_path))
                    else:
                        await ctx.send(content=post)


async def get_latest_message(from_channel, by_member_id=None, with_content=None, after=None, before=None):
    if from_channel is not None:
        messages = from_channel.history(limit=100, after=after, before=before, older_first=True).flatten()
        for msg in reversed(messages):
            process = not by_member_id or msg.author.id == by_member_id
            if process and msg.content == with_content:
                return msg
    return None


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
        return None


def get_embed_field_def(title=None, text=None, inline=True):
    return (title, text, inline)


def dbg_prnt(text):
    print(f'[{get_utcnow()}]: {text}')


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


def get_wikia_link(page_name: str) -> str:
    page_name = '_'.join([part for part in page_name.split(' ')])
    page_name = '_'.join([part.lower().capitalize() for part in page_name.split('_')])
    result = f'{settings.WIKIA_BASE_ADDRESS}{page_name}'

    if not check_hyperlink(result):
        page_name_split = page_name.split('_')
        if len(page_name_split) > 1:
            page_name = f'{page_name_split[0].upper()}_{"_".join(page_name_split[1:])}'
        else:
            page_name = page_name.upper()
    result = f'{settings.WIKIA_BASE_ADDRESS}{page_name}'

    if not check_hyperlink(result):
        result = ''

    return result


def check_hyperlink(hyperlink: str) -> bool:
    if hyperlink:
        request = requests.get(hyperlink)
        return request.status_code == 200
    else:
        return False


async def try_delete_original_message(ctx):
    try:
        await ctx.message.delete()
    except:
        pass


def get_similarity(value_to_check: str, against: str) -> float:
    result = jellyfish.jaro_winkler(value_to_check, against)
    if value_to_check.startswith(against):
        result += 1.0
    return result


def get_similarity_map(values_to_check: dict, against: str) -> dict:
    result = {}
    for key, value in values_to_check.items():
        similarity = get_similarity(value, against)
        result[key] = similarity
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


def sort_tuples_by(data: tuple, order_info: list) -> list:
    """order_info is a list of tuples (element index,reverse)"""
    result = data
    if order_info:
        for i in range(len(order_info), 0, -1):
            element_index = order_info[i - 1][0]
            reverse = convert_to_boolean(order_info[i - 1][1])
            result = sorted(result, key=lambda data_point: data_point[element_index], reverse=reverse)
        return result
    else:
        return sorted(result)


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


def format_excel_datetime(dt: datetime) -> str:
    result = dt.strftime('%Y-%m-%d %H:%M:%S')
    return result


def convert_pss_timestamp_to_excel(pss_timestamp: str) -> str:
    dt = parse_pss_datetime(pss_timestamp)
    result = format_excel_datetime(dt)
    return result


def compare_versions(version_1: str, version_2: str) -> int:
    """Compares to version strings with format x.x.x.x

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





#---------- DB utilities ----------
DB_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

def db_get_column_definition(column_name: str, column_type: str, is_primary: bool = False, not_null: bool = False, alter_column: bool = False) -> str:
    column_name_txt = column_name.lower()
    column_type_txt = column_type.upper()
    is_primary_txt = ''
    not_null_txt = ''
    if is_primary:
        is_primary_txt = 'PRIMARY KEY'
    if not_null:
        not_null_txt = 'NOT NULL'
    result = f'{column_name_txt} {column_type_txt} {is_primary_txt} {not_null_txt}'
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
    if is_text_type:
        column_value = db_convert_text(column_value)
    return f'{column_name} = {column_value}'


def db_convert_boolean(value: bool) -> str:
    if value:
        return 'TRUE'
    else:
        return 'FALSE'

def db_convert_text(value: object) -> str:
    if value:
        result = str(value)
        result = result.replace('\'', '\'\'')
        result = f'\'{result}\''
        return result
    else:
        return ''

def db_convert_timestamp(datetime: datetime) -> str:
    if datetime:
        result = f'TIMESTAMPTZ \'{datetime.strftime(DB_TIMESTAMP_FORMAT)}\''
        return result
    else:
        return None

def db_convert_to_boolean(db_boolean: str, default_if_none: bool = None) -> bool:
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
    if db_timestamp is None:
        return default_if_none
    result = db_timestamp.strptime(DB_TIMESTAMP_FORMAT)
    return result

def db_convert_to_int(db_int: str, default_if_none: bool = None) -> int:
    if db_int is None:
        return default_if_none
    result = int(db_int)
    return result

def db_convert_to_float(db_float: str, default_if_none: bool = None) -> float:
    if db_float is None:
        return default_if_none
    result = float(db_float)
    return result
