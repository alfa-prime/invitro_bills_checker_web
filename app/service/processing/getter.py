from pathlib import Path
from openpyxl import load_workbook
from app.core.logger_setup import logger
from .request import fetch_person_id
from app.service.gateway import GatewayService


async def get_ids(
        service: GatewayService, data: list,
        task_id: str, manager,
        start_progress: int = 50, end_progress: int = 75
) -> list:
    result = []
    total = len(data)

    if total == 0:
        return []

    progress_span = end_progress - start_progress

    for i, row in enumerate(data):
        record = await fetch_person_id(service, row)
        result.append(record)

        current_progress = start_progress + int(((i + 1) / total) * progress_span)
        progress_message = {
            "progress": current_progress,
            "detail": f"Обработано {i + 1} из {total}"
        }
        await manager.send_progress(task_id, progress_message)

    return result


def get_raw_data(book_path: Path, start_row: int, max_col: int, min_col: int = 2):
    logger.info(f"Обработка файла {book_path}")
    if not book_path.exists():
        logger.error(f"Ошибка: Файл не найден по пути {book_path}")
        return []

    book = load_workbook(book_path)
    sheet = book.active
    visit_date, patient_birthday = None, None
    processed_data, seen_rows = [], set()

    for row in sheet.iter_rows(min_row=start_row, min_col=min_col, max_col=max_col, values_only=True):
        row = [item for item in row if item is not None]
        if not row: break
        if len(row) == 1:
            visit_date = row[0].strftime('%d.%m.%Y') if hasattr(row[0], 'strftime') else str(row[0])
        elif len(row) == 2:
            patient_birthday = row[0].strftime('%d.%m.%Y') if hasattr(row[0], 'strftime') else str(row[0])
        elif len(row) > 2:
            if visit_date and patient_birthday:
                combined_row = [visit_date, patient_birthday] + row
                row_tuple = tuple(combined_row)
                if row_tuple not in seen_rows:
                    processed_data.append(combined_row)
                    seen_rows.add(row_tuple)
    book.close()
    return processed_data
