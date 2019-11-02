from datetime import date, datetime, time, timedelta, timezone
import discord
import json
import math
import pytz
import subprocess


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
    if (weeks > 0):
        result += '{:d}w '.format(weeks)
    result += '{:d}d {:d}h {:d}m {:d}s'.format(days, hours, minutes, seconds)
    if include_relative_indicator:
        if is_past:
            result += ' ago'
        else:
            result = 'in {}'.format(result)
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


async def post_output(ctx, output: list, maximum_characters: int):
    if output:
        posts = create_posts_from_lines(output, maximum_characters)
        for post in posts:
            if post:
                await ctx.send(post)


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
    bot_member = guild.get_member(bot.user.id)
    bot_colour = bot_member.colour
    return bot_colour


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







#---------- DB utilities ----------
DB_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

def db_get_column_definition(column_name, column_type, is_primary=False, not_null=False):
    column_name_txt = column_name.upper()
    column_type_txt = column_type.upper()
    is_primary_txt = ''
    not_null_txt = ''
    if is_primary:
        is_primary_txt = ' PRIMARY KEY'
    if not_null:
        not_null_txt = ' NOT NULL'
    result = '{} {}{}{}'.format(column_name_txt, column_type_txt, is_primary_txt, not_null_txt)
    return result


def db_get_where_and_string(where_strings):
    if where_strings:
        result = ''
        for i in range(0, len(where_strings)):
            if i > 0:
                result += ' AND '
            result += where_strings[i]
        return result


def db_get_where_or_string(where_strings):
    if where_strings:
        result = ''
        for i in range(0, len(where_strings)):
            if i > 0:
                result += ' OR '
            result += where_strings[i]
        return result


def db_get_where_string(column_name, column_value, is_text_type=False):
    column_name = column_name.lower()
    if is_text_type:
        column_value = db_convert_text(column_value)
    return '{} = {}'.format(column_name, column_value)


def db_convert_boolean(value):
    if value:
        return 'TRUE'
    else:
        return 'FALSE'

def db_convert_text(value):
    if value:
        result = str(value)
        result = result.replace('\'', '\'\'')
        result = '\'{}\''.format(result)
        return result
    else:
        return ''

def db_convert_timestamp(datetime):
    if datetime:
        result = 'TIMESTAMPTZ \'{}\''.format(datetime.strftime(DB_TIMESTAMP_FORMAT))
        return result
    else:
        return None

def db_convert_to_boolean(db_boolean):
    if db_boolean is None:
        return None
    db_upper = db_boolean.upper()
    if db_upper == 'TRUE' or db_upper == '1' or db_upper == 'T' or db_upper == 'Y' or db_upper == 'YES':
        return True
    else:
        return False

def db_convert_to_datetime(db_timestamp):
    if db_timestamp is None:
        return None
    result = db_timestamp.strptime(DB_TIMESTAMP_FORMAT)
    return result

def db_convert_to_int(db_int):
    if db_int is None:
        return None
    result = int(db_int)
    return result

def db_convert_to_float(db_float):
    if db_float is None:
        return None
    result = float(db_float)
    return result
