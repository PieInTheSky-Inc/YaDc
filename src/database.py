from datetime import datetime
import json as _json
from threading import Lock as _Lock
from typing import Any, Callable, Dict, List, Tuple, Union

import asyncpg

from . import pss_daily as daily
from . import settings
from .typehints import SalesCache
from . import utils


# ---------- Typehint definitions ----------

ColumnDefinition = Tuple[str, str, bool, bool]





# ---------- Constants ----------

CONNECTION_POOL: asyncpg.pool.Pool = None
__CONNECTION_POOL_LOCK: _Lock = _Lock()





# ---------- DataBase ----------

USING_LOOKUP = {
    'BIGINT': 'bigint',
    'INT': 'integer'
}





# ---------- Import/Export ----------

async def export_to_json() -> str:
    devices = await _export_table('devices')
    sales = await _export_table('sales')
    serversettings = await _export_table('serversettings')

    result = {
        'devices': devices,
        'sales': sales,
        'serversettings': serversettings,
    }
    return _json.dumps(result, indent=4, cls=utils.json.YadcEncoder)


async def import_from_json(json: str) -> None:
    tables = _json.loads(json, cls=utils.json.YadcDecoder)
    for table_name, table_contents in tables.items():
        await _import_table(table_name, table_contents['column_names'], table_contents['values'])


async def _export_table(table_name: str) -> dict:
    column_names = await get_column_names(table_name)
    rows = await fetchall(f'SELECT * FROM {table_name}')
    values = [dict(row) for row in rows]
    return {
        'column_names': column_names,
        'values': values
    }


async def _import_table(table_name: str, column_names: List[str], rows: List[List[Any]]) -> None:
    """
    This function will clear the specified table and insert the values provided.
    """
    column_names_string = ','.join(column_names)
    values_string = ', '.join([f'${i}' for i in range(1, len(column_names) + 1)])
    query = f'INSERT INTO {table_name} ({column_names_string}) VALUES ({values_string})'

    print(f'[_import_table] Clearing table: {table_name}')
    await execute(f'DELETE FROM {table_name}')

    print(f'[_import_table] Importing data to table: {table_name}')
    for values in rows:
        await execute(query, values)





# ---------- DB Schema ----------

async def init_schema() -> None:
    success_create_schema = await create_schema()
    if not success_create_schema:
        print('[init_schema] DB initialization failed upon creating the DB schema.')
        return

    if not (await update_schema('1.2.2.0', update_schema_v_1_2_2_0)):
        return

    if not (await update_schema('1.2.4.0', update_schema_v_1_2_4_0)):
        return

    if not (await update_schema('1.2.5.0', update_schema_v_1_2_5_0)):
        return

    if not (await update_schema('1.2.6.0', update_schema_v_1_2_6_0)):
        return

    if not (await update_schema('1.2.7.0', db_update_schema_v_1_2_7_0)):
        return

    if not (await update_schema('1.2.8.0', update_schema_v_1_2_8_0)):
        return

    if not (await update_schema('1.2.9.0', update_schema_v_1_2_9_0)):
        return

    if not (await update_schema('1.3.0.0', update_schema_v_1_3_0_0)):
        return

    if not (await update_schema('1.3.1.0', update_schema_v_1_3_1_0)):
        return

    success_serversettings = await try_create_table('serversettings', [
        ('guildid', 'TEXT', True, True),
        ('dailychannelid', 'TEXT', False, False),
        ('dailycanpost', 'BOOLEAN', False, False),
        ('dailylatestmessageid', 'TEXT', False, False),
        ('usepagination', 'BOOLEAN', False, False),
        ('prefix', 'TEXT', False, False),
        ('dailydeleteonchange', 'BOOLEAN', False, False)
    ])
    if not success_serversettings:
        print('[init_schema] DB initialization failed upon creating the table \'serversettings\'.')
        return

    print('[init_schema] DB initialization succeeded')


async def update_schema(version: str, update_function: Callable) -> bool:
    success = await update_function()
    if not success:
        print(f'[update_schema] DB initialization failed upon upgrading the DB schema to version {version}.')
    return success


async def update_schema_v_1_3_1_0() -> bool:
    schema_version = await get_schema_version()
    if schema_version:
        compare_1300 = utils.compare_versions(schema_version, '1.3.1.0')
        compare_1290 = utils.compare_versions(schema_version, '1.3.0.0')
        if compare_1300 <= 0:
            return True
        elif compare_1290 > 0:
            return False

    print(f'[update_schema_v_1_3_1_0] Updating database schema from v1.3.0.0 to v1.3.1.0')

    query_add_column = f'ALTER TABLE serversettings ADD COLUMN useembeds BOOL;'
    success_add_column = await try_execute(query_add_column)

    if not success_add_column:
        print(f'[update_schema_v_1_3_1_0] ERROR: Failed to add column \'useembeds\' to table \'serversettings\'!')
        return False

    success = await try_set_schema_version('1.3.1.0')
    return success


async def update_schema_v_1_3_0_0() -> bool:
    schema_version = await get_schema_version()
    if schema_version:
        compare_1300 = utils.compare_versions(schema_version, '1.3.0.0')
        compare_1290 = utils.compare_versions(schema_version, '1.2.9.0')
        if compare_1300 <= 0:
            return True
        elif compare_1290 > 0:
            return False

    print(f'[update_schema_v_1_3_0_0] Updating database schema from v1.2.9.0 to v1.3.0.0')

    query_add_column = f'ALTER TABLE serversettings ADD COLUMN botnewschannelid BIGINT;'
    success_add_column = await try_execute(query_add_column)
    if not success_add_column:
        print(f'[update_schema_v_1_3_0_0] ERROR: Failed to add column \'botnewschannelid\' to table \'serversettings\'!')
        return False

    column_definitions_sales = [
        ('id', 'SERIAL', True, True),
        ('limitedcatalogargument', 'INT', False, False),
        ('limitedcatalogtype', 'TEXT', False, False),
        ('limitedcatalogcurrencytype', 'TEXT', False, False),
        ('limitedcatalogcurrencyamount', 'INT', False, False),
        ('limitedcatalogmaxtotal', 'INT', False, False),
        ('limitedcatalogexpirydate', 'TIMESTAMPTZ', False, False)
    ]
    success_create_table = await try_create_table('sales', column_definitions_sales)
    if not success_create_table:
        print(f'[update_schema_v_1_3_0_0] ERROR: Failed to add table \'sales\'!')
        return False

    success = await try_set_schema_version('1.3.0.0')
    return success


async def update_schema_v_1_2_9_0() -> bool:
    schema_version = await get_schema_version()
    if schema_version:
        compare_1290 = utils.compare_versions(schema_version, '1.2.9.0')
        compare_1280 = utils.compare_versions(schema_version, '1.2.8.0')
        if compare_1290 <= 0:
            return True
        elif compare_1280 > 0:
            return False

    print(f'[update_schema_v_1_2_9_0] Updating database schema from v1.2.8.0 to v1.2.9.0')

    query_add_column = f'ALTER TABLE serversettings ADD COLUMN dailychangemode INT;'
    success_add_column = await try_execute(query_add_column)
    if not success_add_column:
        print(f'[update_schema_v_1_2_9_0] ERROR: Failed to add column \'dailychangemode\' to table \'serversettings\'!')
        return False

    query_lines_move_data = [f'UPDATE serversettings SET dailychangemode = 1 WHERE dailydeleteonchange IS NULL;']
    query_lines_move_data.append(f'UPDATE serversettings SET dailychangemode = 2 WHERE dailydeleteonchange = {utils.database.convert_boolean(True)};')
    query_lines_move_data.append(f'UPDATE serversettings SET dailychangemode = 3 WHERE dailydeleteonchange = {utils.database.convert_boolean(False)};')
    query_move_data = '\n'.join(query_lines_move_data)
    success_move_data = await try_execute(query_move_data)
    if not success_move_data:
        print(f'[update_schema_v_1_2_9_0] ERROR: Failed to convert and copy data from column \'dailydeleteonchange\' into column \'dailychangemode\'!')
        return False

    query_drop_column = f'ALTER TABLE serversettings DROP COLUMN IF EXISTS dailydeleteonchange;'
    success_drop_column = await try_execute(query_drop_column)
    if not success_drop_column:
        print(f'[update_schema_v_1_2_9_0] ERROR: Failed to drop column \'dailydeleteonchange\'!')
        return False

    success = await try_set_schema_version('1.2.9.0')
    return success


async def update_schema_v_1_2_8_0() -> bool:
    column_definitions_serversettings = [
        ('guildid', 'BIGINT', True, True),
        ('dailychannelid', 'BIGINT', False, False),
        ('dailylatestmessageid', 'BIGINT', False, False),
        ('dailynotifyid', 'BIGINT', False, False),
        ('dailynotifytype', 'INT', False, False)
    ]

    schema_version = await get_schema_version()
    if schema_version:
        compare_1280 = utils.compare_versions(schema_version, '1.2.8.0')
        compare_1270 = utils.compare_versions(schema_version, '1.2.7.0')
        if compare_1280 <= 0:
            return True
        elif compare_1270 > 0:
            return False

    print(f'[update_schema_v_1_2_8_0] Updating database schema from v1.2.7.0 to v1.2.8.0')

    query_lines = ['ALTER TABLE serversettings']
    for column_name, new_column_type, _, _ in column_definitions_serversettings:
        if new_column_type in USING_LOOKUP:
            using = f' USING {column_name}::{USING_LOOKUP[new_column_type]}'
        else:
            using = ''
        query_lines.append(f'ALTER COLUMN {column_name} SET DATA TYPE {new_column_type}{using},')
    query_lines[-1] = query_lines[-1].replace(',', ';')

    query = '\n'.join(query_lines)
    success = await try_execute(query)
    if success:
        success = await try_set_schema_version('1.2.8.0')
    return success


async def db_update_schema_v_1_2_7_0() -> bool:
    column_definitions_devices = [
        ('key', 'TEXT', True, True),
        ('checksum', 'TEXT', False, False),
        ('loginuntil', 'TIMESTAMPTZ', False, False)
    ]

    schema_version = await get_schema_version()
    if schema_version:
        compare_1270 = utils.compare_versions(schema_version, '1.2.7.0')
        compare_1260 = utils.compare_versions(schema_version, '1.2.6.0')
        if compare_1270 <= 0:
            return True
        elif compare_1260 > 0:
            return False

    print(f'[update_schema_v_1_2_8_0] Updating database schema from v1.2.6.0 to v1.2.7.0')

    success = await try_create_table('devices', column_definitions_devices)
    if success:
        success = await try_set_schema_version('1.2.7.0')
    return success


async def update_schema_v_1_2_6_0() -> bool:
    column_definitions_serversettings = [
        ('dailylatestmessagecreatedate', 'TIMESTAMPTZ', False, False),
        ('dailylatestmessagemodifydate', 'TIMESTAMPTZ', False, False)
    ]

    schema_version = await get_schema_version()
    if schema_version:
        compare_1260 = utils.compare_versions(schema_version, '1.2.6.0')
        compare_1250 = utils.compare_versions(schema_version, '1.2.5.0')
        if compare_1260 <= 0:
            return True
        elif compare_1250 > 0:
            return False

    print(f'[update_schema_v_1_2_6_0] Updating database schema from v1.2.5.0 to v1.2.6.0')

    query_lines = []
    for (column_name, column_type, column_is_primary, column_not_null) in column_definitions_serversettings:
        column_definition = utils.database.get_column_definition(column_name, column_type, is_primary=column_is_primary, not_null=column_not_null)
        query_lines.append(f'ALTER TABLE serversettings ADD COLUMN IF NOT EXISTS {column_definition};')

    query = '\n'.join(query_lines)
    success = await try_execute(query)
    if success:
        success = await try_set_schema_version('1.2.6.0')
    return success


async def update_schema_v_1_2_5_0() -> bool:
    column_definitions = [
        ('dailynotifyid', 'TEXT', False, False),
        ('dailynotifytype', 'TEXT', False, False)
    ]

    schema_version = await get_schema_version()
    if schema_version:
        compare_1250 = utils.compare_versions(schema_version, '1.2.5.0')
        compare_1240 = utils.compare_versions(schema_version, '1.2.4.0')
        if compare_1250 <= 0:
            return True
        elif compare_1240 > 0:
            return False

    print(f'[update_schema_v_1_2_5_0] Updating database schema from v1.2.4.0 to v1.2.5.0')

    query_lines = []
    for (column_name, column_type, column_is_primary, column_not_null) in column_definitions:
        column_definition = utils.database.get_column_definition(column_name, column_type, is_primary=column_is_primary, not_null=column_not_null)
        query_lines.append(f'ALTER TABLE serversettings ADD COLUMN IF NOT EXISTS {column_definition};')

    query = '\n'.join(query_lines)
    success = await try_execute(query)
    if success:
        success = await try_set_schema_version('1.2.5.0')
    return success


async def update_schema_v_1_2_4_0() -> bool:
    column_definitions = [
        ('dailydeleteonchange', 'BOOLEAN', False, False, None)
    ]

    schema_version = await get_schema_version()
    if schema_version:
        compare_1240 = utils.compare_versions(schema_version, '1.2.4.0')
        compare_1220 = utils.compare_versions(schema_version, '1.2.2.0')
        if compare_1240 <= 0:
            return True
        elif compare_1220 > 0:
            return False

    print(f'[update_schema_v_1_2_4_0] Updating database schema from v1.2.2.0 to v1.2.4.0')

    query_lines = []
    for (column_name, column_type, column_is_primary, column_not_null, column_default) in column_definitions:
        column_definition = utils.database.get_column_definition(column_name, column_type, is_primary=column_is_primary, not_null=column_not_null, default=column_default)
        query_lines.append(f'ALTER TABLE serversettings ADD COLUMN IF NOT EXISTS {column_definition}')

    query = '\n'.join(query_lines)
    success = await try_execute(query)
    if success:
        utc_now = utils.get_utc_now()
        daily_info = await daily.get_daily_info()
        success = await daily.db_set_daily_info(daily_info, utc_now)
        if success:
            success = await try_set_schema_version('1.2.4.0')
    return success


async def update_schema_v_1_2_2_0() -> bool:
    query_lines = []
    rename_columns = {
        'channelid': 'dailychannelid',
        'canpost': 'dailycanpost'
    }
    column_definitions = [
        ('guildid', 'TEXT', True, True),
        ('dailychannelid', 'TEXT', False, False),
        ('dailycanpost', 'BOOLEAN', False, False),
        ('dailylatestmessageid', 'TEXT', False, False),
        ('usepagination', 'BOOLEAN', False, False),
        ('prefix', 'TEXT', False, False)
    ]

    schema_version = await get_schema_version()
    if schema_version:
        compare_1220 = utils.compare_versions(schema_version, '1.2.2.0')
        compare_1000 = utils.compare_versions(schema_version, '1.0.0.0')
        if compare_1220 <= 0:
            return True
        elif compare_1000 > 0:
            return False

    print(f'[update_schema_v_1_2_2_0] Updating database schema from v1.0.0.0 to v1.2.2.0')

    query = 'ALTER TABLE IF EXISTS daily RENAME TO serversettings'
    try:
        success = await try_execute(query, raise_db_error=True)
    except Exception as error:
        success = False
        print_db_query_error('update_schema_v_1_2_2_0', query, None, error)
    if success:
        column_names = await get_column_names('serversettings')
        column_names = [column_name.lower() for column_name in column_names]
        for name_from, name_to in rename_columns.items():
            if name_from in column_names:
                query_lines.append(f'ALTER TABLE IF EXISTS serversettings RENAME COLUMN {name_from} TO {name_to};')

        for (column_name, column_type, column_is_primary, column_not_null) in column_definitions:
            if column_name in rename_columns.values() or column_name in column_names:
                query_lines.append(f'ALTER TABLE IF EXISTS serversettings ALTER COLUMN {column_name} TYPE {column_type};')
                if column_not_null:
                    not_null_toggle = 'SET'
                else:
                    not_null_toggle = 'DROP'
                query_lines.append(f'ALTER TABLE IF EXISTS serversettings ALTER COLUMN {column_name} {not_null_toggle} NOT NULL;')

        query = '\n'.join(query_lines)
        if query:
            success = await try_execute(query)
        else:
            success = True
        if success:
            query_lines = []
            column_names = await get_column_names('serversettings')
            column_names = [column_name.lower() for column_name in column_names]
            for (column_name, column_type, column_is_primary, column_not_null) in column_definitions:
                if column_name not in column_names:
                    query_lines.append(f'ALTER TABLE IF EXISTS serversettings ADD COLUMN IF NOT EXISTS {utils.database.get_column_definition(column_name, column_type, column_is_primary, column_not_null)};')
            query = '\n'.join(query_lines)
            if query:
                success = await try_execute(query)
            else:
                success = True
            if success:
                success = await try_set_schema_version('1.2.2.0')
    return success


async def create_schema() -> bool:
    column_definitions_settings = [
        ('settingname', 'TEXT', True, True),
        ('modifydate', 'TIMESTAMPTZ', False, True),
        ('settingboolean', 'BOOLEAN', False, False),
        ('settingfloat', 'FLOAT', False, False),
        ('settingint', 'INT', False, False),
        ('settingtext', 'TEXT', False, False),
        ('settingtimestamp', 'TIMESTAMPTZ', False, False)
    ]
    column_definitions_daily = [
        ('guildid', 'TEXT', True, True),
        ('channelid', 'TEXT', False, True),
        ('canpost', 'BOOLEAN')
    ]
    query_server_settings = 'SELECT * FROM serversettings'

    schema_version = await get_schema_version()
    if schema_version:
        compare_1000 = utils.compare_versions(schema_version, '1.0.0.0')
        if compare_1000 <= 0:
            return True

    print(f'[create_schema] Creating database schema v1.0.0.0')

    success_settings = await try_create_table('settings', column_definitions_settings)
    if not success_settings:
        print('[create_schema] DB initialization failed upon creating the table \'settings\'.')

    create_daily = False
    try:
        _ = await fetchall(query_server_settings)
    except asyncpg.exceptions.UndefinedTableError:
        create_daily = True

    if create_daily:
        success_daily = await try_create_table('daily', column_definitions_daily)
    else:
        success_daily = True

    if success_daily is False:
        print('[create_schema] DB initialization failed upon creating the table \'daily\'.')

    success = success_settings and success_daily
    if success:
        success = await try_set_schema_version('1.0.0.0')
    return success





# ---------- Helper ----------

async def connect() -> bool:
    __log_db_function_enter('connect')

    global CONNECTION_POOL
    if is_connected(CONNECTION_POOL) is False:
        __log_db('[connect] Connection pool is not connected')
        try:
            __log_db('[connect] Creating connection pool')
            CONNECTION_POOL = await asyncpg.create_pool(dsn=settings.DATABASE_URL, min_size=1, max_size=5)
            return True
        except Exception as error:
            error_name = error.__class__.__name__
            print(f'[connect] {error_name} occurred while establishing connection: {error}')
            return False
    else:
        __log_db('[connect] Is Connected')
        return True


async def disconnect() -> None:
    __log_db_function_enter('disconnect')

    global CONNECTION_POOL
    if is_connected(CONNECTION_POOL):
        await CONNECTION_POOL.close()


async def execute(query: str, args: list = None) -> bool:
    __log_db_function_enter('execute', query=f'\'{query}\'', args=args)

    async with CONNECTION_POOL.acquire() as connection:
        async with connection.transaction():
            if args:
                await connection.execute(query, *args)
            else:
                await connection.execute(query)


async def fetchall(query: str, args: list = None) -> List[asyncpg.Record]:
    __log_db_function_enter('fetchall', query=f'\'{query}\'', args=args)

    if query and query[-1] != ';':
        query += ';'
    result: List[asyncpg.Record] = None
    if await connect():
        try:
            async with CONNECTION_POOL.acquire() as connection:
                async with connection.transaction():
                    if args:
                        result = await connection.fetch(query, *args)
                    else:
                        result = await connection.fetch(query)
        except (asyncpg.exceptions.PostgresError, asyncpg.PostgresError) as pg_error:
            raise pg_error
        except Exception as error:
            print_db_query_error('fetchall', query, args, error)
    else:
        print('[fetchall] could not connect to db')
    return result


def get_column_list(column_definitions: List[ColumnDefinition]) -> str:
    __log_db_function_enter('get_column_list', column_definitions=column_definitions)

    result = []
    for column_definition in column_definitions:
        result.append(utils.database.get_column_definition(*column_definition))
    return ', '.join(result)


async def get_column_names(table_name: str) -> List[str]:
    __log_db_function_enter('get_column_names', table_name=f'\'{table_name}\'')

    result = None
    query = f'SELECT column_name FROM information_schema.columns WHERE table_name = $1'
    result = await fetchall(query, [table_name])
    if result:
        result = [record[0] for record in result]
    return result


async def get_schema_version() -> str:
    __log_db_function_enter('get_schema_version')

    try:
        result, _ = await get_setting('schema_version')
    except:
        result = None
    return result or ''


def is_connected(pool: asyncpg.pool.Pool) -> bool:
    __log_db_function_enter('is_connected', pool=pool)

    if pool:
        return not (pool._closed or pool._closing)
    return False


async def try_set_schema_version(version: str) -> bool:
    __log_db_function_enter('try_set_schema_version', version=f'\'{version}\'')

    prior_version = await get_schema_version()
    utc_now = utils.get_utc_now()
    if not prior_version:
        query = f'INSERT INTO settings (modifydate, settingtext, settingname) VALUES ($1, $2, $3)'
    else:
        query = f'UPDATE settings SET modifydate = $1, settingtext = $2 WHERE settingname = $3'
    success = await try_execute(query, [utc_now, version, 'schema_version'])
    if success:
        __settings_cache['schema_version'] = (version, utc_now)
    return success


async def try_create_table(table_name: str, column_definitions: List[ColumnDefinition]) -> bool:
    __log_db_function_enter('try_create_table', table_name=f'\'{table_name}\'', column_definitions=column_definitions)

    column_list = get_column_list(column_definitions)
    query_create = f'CREATE TABLE {table_name} ({column_list});'
    success = False
    if await connect():
        try:
            success = await try_execute(query_create, raise_db_error=True)
        except asyncpg.exceptions.DuplicateTableError:
            success = True
    else:
        print('[try_create_table] could not connect to db')
    return success


async def try_execute(query: str, args: list = None, raise_db_error: bool = False) -> bool:
    __log_db_function_enter('try_execute', query=f'\'{query}\'', args=args, raise_db_error=raise_db_error)

    if query and query[-1] != ';':
        query += ';'
    success = False
    if await connect():
        try:
            await execute(query, args)
            success = True
        except (asyncpg.exceptions.PostgresError, asyncpg.PostgresError) as pg_error:
            if raise_db_error:
                raise pg_error
            else:
                print_db_query_error('try_execute', query, args, pg_error)
                success = False
        except Exception as error:
            print_db_query_error('try_execute', query, args, error)
            success = False
    else:
        print('[try_execute] could not connect to db')
    return success


async def get_setting(setting_name: str) -> Tuple[object, datetime]:
    __log_db_function_enter('get_setting', setting_name=f'\'{setting_name}\'')

    if __settings_cache is None or setting_name not in __settings_cache.keys():
        modify_date: datetime = None
        query = f'SELECT * FROM settings WHERE settingname = $1'
        args = [setting_name]
        try:
            records = await fetchall(query, args)
        except Exception as error:
            print_db_query_error('get_setting', query, args, error)
            records = []
        if records:
            result = records[0]
            modify_date = result[1]
            value = None
            for field in result[2:]:
                if field:
                    value = field
                    break
            setting = (value, modify_date)
            __settings_cache[setting_name] = setting
            return setting
        else:
            return (None, None)
    else:
        return __settings_cache[setting_name]


async def get_settings(setting_names: List[str] = None) -> Dict[str, Tuple[object, datetime]]:
    __log_db_function_enter('get_settings', setting_names=setting_names)
    setting_names = setting_names or []
    result = {setting_name: (None, None) for setting_name in setting_names}

    if __settings_cache is None:
        db_setting_names = setting_names
    else:
        db_setting_names = [setting_name for setting_name in setting_names if setting_name not in __settings_cache.keys()]
        result.update({setting_name: setting_value for setting_name, setting_value in __settings_cache.items() if setting_name in setting_names})

    if not result:
        query = f'SELECT * FROM settings'
        if db_setting_names:
            where_strings = [f'settingname = ${i}' for i in range(1, len(db_setting_names) + 1, 1)]
            where_string = ' OR '.join(where_strings)
            query += f' WHERE {where_string}'
            records = await fetchall(query, args=db_setting_names)
        else:
            records = await fetchall(query)

        for record in records:
            setting_name = record[0]
            modify_date = record[1]
            value = None
            for field in record[2:]:
                if field:
                    value = field
                    break
            result[setting_name] = (value, modify_date)
    return result


async def get_sales_infos(expiry_date: datetime = None) -> SalesCache:
    __log_db_function_enter('get_sales_infos')

    args = []
    query = 'SELECT * FROM sales'
    if expiry_date is not None:
        query += f' WHERE limitedcatalogexpirydate = $1'
        args.append(expiry_date)
    query += ' ORDER BY limitedcatalogexpirydate DESC'
    try:
        records = await fetchall(query, args)
    except asyncpg.UndefinedTableError:
        records = None
    if records:
        result = [dict(record) for record in records]
    else:
        result = []
    return result


async def set_setting(setting_name: str, value: Any, utc_now: datetime = None) -> bool:
    __log_db_function_enter('set_setting', setting_name=f'\'{setting_name}\'', value=value, utc_now=utc_now)

    column_name = None
    if isinstance(value, bool):
        column_name = 'settingboolean'
    elif isinstance(value, int):
        column_name = 'settingint'
    elif isinstance(value, float):
        column_name = 'settingfloat'
    elif isinstance(value, datetime):
        column_name = 'settingtimestamptz'
    else:
        column_name = 'settingtext'

    success = True
    setting, modify_date = await get_setting(setting_name)
    if utc_now is None:
        utc_now = utils.get_utc_now()
    query = ''
    if setting is None and modify_date is None:
        query = f'INSERT INTO settings ({column_name}, modifydate, settingname) VALUES ($1, $2, $3)'
    elif setting != value:
        query = f'UPDATE settings SET {column_name} = $1, modifydate = $2 WHERE settingname = $3'
    success = not query or await try_execute(query, [value, utc_now, setting_name])
    if success:
        __settings_cache[setting_name] = (value, utc_now)
    return success


async def set_settings(settings: Dict[str, Tuple[object, datetime]]) -> bool:
    __log_db_function_enter('set_settings', settings=settings)

    utc_now = utils.get_utc_now()
    if settings:
        query_lines = []
        args = []
        success = True
        current_settings = await get_settings(settings.keys())
        for setting_name, (value, modified_at) in settings.items():
            query = ''
            column_name = None
            if isinstance(value, bool):
                column_name = 'settingboolean'
                value = utils.database.convert_boolean(value)
            elif isinstance(value, int):
                column_name = 'settingint'
            elif isinstance(value, float):
                column_name = 'settingfloat'
            elif isinstance(value, datetime):
                column_name = 'settingtimestamptz'
                value = utils.database.convert_timestamp(value)
            else:
                column_name = 'settingtext'
                value = utils.database.convert_text(value)
            current_value, db_modify_date = current_settings[setting_name]
            modify_date = db_modify_date or utc_now

            setting_name = utils.database.convert_text(setting_name)
            if current_value is None and db_modify_date is None:
                query = f'INSERT INTO settings ({column_name}, modifydate, settingname) VALUES ({value}, \'{modified_at}\', {setting_name});'
            elif current_value != value:
                query = f'UPDATE settings SET {column_name} = {value}, modifydate = \'{modified_at}\' WHERE settingname = {setting_name};'

            if query:
                query_lines.append(query)
                args.extend([value, modified_at, setting_name])
        success = not query_lines or await try_execute('\n'.join(query_lines))
        if success:
            __settings_cache.update(settings)
        return success
    else:
        return True


async def update_sales_info(sales_info: Dict[str, Any]) -> bool:
    __log_db_function_enter('update_sales_info', sales_info=sales_info)

    db_sales_infos = await get_sales_infos(expiry_date=sales_info['LimitedCatalogExpiryDate'])
    column_names = []
    placeholders = []
    set_fields = []
    args = []
    for i, column_name in enumerate(sales_info, start=1):
        args.append(sales_info[column_name])
        column_name = column_name.lower()
        column_names.append(column_name)
        placeholders.append(f'${i}')
        set_fields.append(f'{column_name} = ${i}')

    if db_sales_infos:
        current_sales_info = db_sales_infos[0]
        current_sales_info_id = current_sales_info['id']
        query = f'UPDATE sales SET {", ".join(set_fields)} WHERE id = {current_sales_info_id}'
    else:
        query = f'INSERT INTO sales ({", ".join(column_names)}) VALUES ({", ".join(placeholders)})'
    success = await try_execute(query, args)
    return success


def print_db_query_error(function_name: str, query: str, args: List[Any], error: asyncpg.exceptions.PostgresError) -> None:
    if args:
        args = f'\n{args}'
    else:
        args = ''
    print(f'[{function_name}] {error.__class__.__name__} while performing the query: {query}{args}\nMSG: {error}')


def __log_db_function_enter(function_name: str, **kwargs) -> None:
    if settings.PRINT_DEBUG_DB:
        params = ', '.join([f'{k}={v}' for k, v in kwargs.items()])
        print(f'+ {function_name}({params})')


def __log_db(message: str) -> None:
    if settings.PRINT_DEBUG_DB:
        print(message)





# ---------- Initialization ----------

__settings_cache: Dict[str, Tuple[object, datetime]] = None


async def init_caches() -> None:
    try:
        settings = await get_settings()
    except (asyncpg.exceptions.UndefinedTableError): # settings table doesn't exist
        settings = {}
    global __settings_cache
    __settings_cache = settings


async def init() -> None:
    await connect()
    await init_caches()
    await init_schema()