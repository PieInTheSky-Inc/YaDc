from datetime import datetime
import openpyxl

import pss_entity as entity
import settings
import utility as util




# ---------- Constants ----------

__BASE_TABLE_STYLE = openpyxl.worksheet.table.TableStyleInfo(name="TableStyleLight1", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)


def create_xl_from_data(data: list, file_prefix: str, data_retrieval_date: datetime, column_formats: list, file_name: str = None) -> str:
    if data_retrieval_date is None:
        data_retrieval_date = util.get_utcnow()
    if file_name:
        save_to = file_name
    else:
        save_to = get_file_name(file_prefix, data_retrieval_date)

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


def create_xl_from_raw_data_dict(entities_data: entity.EntitiesDesignsData, entity_key_name: str, file_prefix: str, data_retrieval_date: datetime = None) -> str:
    if data_retrieval_date is None:
        data_retrieval_date = util.get_utcnow()
    save_to = get_file_name(file_prefix, data_retrieval_date)

    header_names = []
    entities_data = sorted(entities_data.values(), key=lambda row: int(row[entity_key_name]))
    xl_data = []
    for row in entities_data:
        result_row = {}
        for field_name, field in row.items():
            if should_include_raw_field(field):
                if isinstance(field, dict):
                    for sub_field_name, sub_field in field.items():
                        header_name = f'{field_name}.{sub_field_name}'
                        result_row[header_name] = sub_field
                        if header_name not in header_names:
                            header_names.append(header_name)
                else:
                    header_name = field_name
                    result_row[header_name] = field
                    if header_name not in header_names:
                        header_names.append(header_name)
        xl_data.append(result_row)

    wb = openpyxl.Workbook()
    ws = wb.active

    ws.append(header_names)
    for row in xl_data:
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


def get_file_name(file_prefix: str, data_retrieval_date: datetime) -> str:
    file_prefix = file_prefix.replace(' ', '_')
    file_timestamp = data_retrieval_date.strftime('%Y%m%d-%H%M%S')
    result = f'{file_prefix}_{file_timestamp}.xlsx'
    return result


def should_include_raw_field(field) -> bool:
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