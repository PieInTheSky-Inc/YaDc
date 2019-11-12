from datetime import datetime
import openpyxl

import settings
import utility as util


def create_xl_from_data(data: list, file_prefix: str, data_retrieval_date: datetime) -> str:
    if data_retrieval_date is None:
        data_retrieval_date = util.get_utcnow()
    file_timestamp = data_retrieval_date.strftime('%Y%m%d-%H%M%S')
    save_to = f'{file_prefix}{file_timestamp}.xlsx'

    wb = openpyxl.Workbook()
    ws = wb.active

    for item in data:
        ws.append(item)

    wb.save(save_to)
    return save_to