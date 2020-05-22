import datetime
import openpyxl

import pss_entity as entity
import pss_tournament as tourney
import settings
import utility as util




# ---------- Constants ----------

__BASE_TABLE_STYLE = openpyxl.worksheet.table.TableStyleInfo(name="TableStyleLight1", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
__EARLIEST_EXCEL_DATETIME = datetime.datetime(1900, 1, 1, tzinfo=datetime.timezone.utc)


def create_xl_from_data(data: list, file_prefix: str, data_retrieved_at: datetime.datetime, column_formats: list, file_name: str = None) -> str:
    if data_retrieved_at is None:
        data_retrieved_at = util.get_utcnow()
    if file_name:
        save_to = file_name
    else:
        save_to = get_file_name(file_prefix, data_retrieved_at)

    wb = openpyxl.Workbook()
    ws = wb.active

    for item in data:
        ws.append(item)

    col_count = len(list(ws.columns)) + 1
    row_count = len(list(ws.rows)) + 1
    for i, col_no in enumerate(range(1, col_count)):
        column_format = column_formats[i]
        if column_format:
            for row_no in range(2, row_count):
                ws.cell(row_no, col_no).number_format = column_format

    wb.save(save_to)
    return save_to


def create_xl_from_raw_data_dict(flattened_data: list, entity_key_name: str, file_prefix: str, data_retrieved_at: datetime.datetime = None) -> str:
    if data_retrieved_at is None:
        data_retrieved_at = util.get_utcnow()
    save_to = get_file_name(file_prefix, data_retrieved_at)

    header_names = []
    for row in flattened_data:
        for key in row:
            if key not in header_names:
                header_names.append(key)

    wb = openpyxl.Workbook()
    ws = wb.active

    ws.append(header_names)
    for row in flattened_data:
        for field_name, field in row.items():
            row[field_name] = _fix_field(field)
        ws.append(list(row.values()))

    col_count = len(list(ws.columns)) - 1
    row_count = len(list(ws.rows)) - 1

    ref = _convert_to_ref(col_count, row_count)
    table = openpyxl.worksheet.table.Table(displayName='tbl', ref=ref)
    table.tableStyleInfo = __BASE_TABLE_STYLE
    ws.add_table(table)

    wb.save(save_to)
    return save_to


def get_file_name(file_prefix: str, data_retrieved_at: datetime) -> str:
    file_prefix = file_prefix.replace(' ', '_')
    if tourney.is_tourney_running(utc_now=data_retrieved_at):
        file_timestamp = f'tournament-{data_retrieved_at.year}-{util.get_month_short_name(data_retrieved_at).lower()}'
    else:
        file_timestamp = data_retrieved_at.strftime('%Y%m%d-%H%M%S')
    result = f'{file_prefix}_{file_timestamp}.xlsx'
    return result


def _convert_to_ref(column_count: int, row_count: int, column_start: int = 0, row_start: int = 0, zero_based: bool = True) -> str:
    if zero_based:
        column_start += 1
        row_start += 1
    start_column_letter = openpyxl.utils.get_column_letter(column_start)
    end_column_letter = openpyxl.utils.get_column_letter(column_start + column_count)
    result = f'{start_column_letter}{row_start}:{end_column_letter}{row_start + row_count}'
    return result


def _fix_field(field: str):
    if field:
        try:
            dt = util.parse_pss_datetime(field)
            if dt < __EARLIEST_EXCEL_DATETIME:
                return __EARLIEST_EXCEL_DATETIME
            else:
                return dt
        except (TypeError, ValueError):
            try:
                return int(field)
            except (TypeError, ValueError):
                try:
                    return float(field)
                except (TypeError, ValueError):
                    pass
        field_lower = field.lower().strip()
        if field_lower == 'false':
            return False
        elif field_lower == 'true':
            return True

    return field