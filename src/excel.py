from datetime import datetime
import openpyxl

import pss_tournament as tourney
import settings
import utility as util


def create_xl_from_data(data: list, file_prefix: str, data_retrieval_date: datetime, column_formats: list, file_name: str = None) -> str:
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


def get_file_name(file_prefix: str, data_retrieved_at: datetime) -> str:
    file_prefix = file_prefix.replace(' ', '_')
    if tourney.is_tourney_running(utc_now=data_retrieved_at):
        file_timestamp = f'tournament-{data_retrieved_at.year}-{util.get_month_short_name(data_retrieved_at).lower()}'
    else:
        file_timestamp = data_retrieved_at.strftime('%Y%m%d-%H%M%S')
    result = f'{file_prefix}_{file_timestamp}.xlsx'
    return result
