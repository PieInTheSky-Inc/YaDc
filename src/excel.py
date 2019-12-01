from datetime import datetime
import openpyxl

import settings
import utility as util


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


def get_file_name(file_prefix: str, data_retrieval_date: datetime) -> str:
    file_prefix = file_prefix.replace(' ', '_')
    file_timestamp = data_retrieval_date.strftime('%Y%m%d-%H%M%S')
    result = f'{file_prefix}_{file_timestamp}.xlsx'
    return result
