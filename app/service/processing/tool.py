import json
from pathlib import Path
from openpyxl import load_workbook, worksheet
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, PatternFill

from . import constants

CENTER_ALIGNED = Alignment(horizontal='center', vertical='center')


def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def separate_records(data, results_path: Path):
    not_found_file = results_path / "not_found_records.json"
    doubles_file = results_path / "doubles_records.json"

    not_found = [r for r in data if r['person']['id'] == constants.PERSON_ID_STATUS_NOT_FOUND]
    if not_found: save_json(not_found, not_found_file)

    doubles = [r for r in data if r['person']['id'] == constants.PERSON_ID_STATUS_MULTIPLE_FOUND]
    if doubles: save_json(doubles, doubles_file)

    invalid = {
        constants.PERSON_ID_STATUS_NOT_FOUND,
        constants.PERSON_ID_STATUS_MULTIPLE_FOUND,
        constants.PERSON_ID_STATUS_API_ERROR
    }
    return [r for r in data if r['person']['id'] not in invalid]


def _align_column_center(sheet: worksheet, columns: list):
    for column_to_align in columns:
        for cell in sheet[column_to_align]:
            cell.alignment = CENTER_ALIGNED


def _align_row_center(sheet: worksheet, rows: list):
    for row_to_align in rows:
        for cell in sheet[row_to_align]:
            cell.alignment = CENTER_ALIGNED


def _auto_cells_width(sheet):
    for col in sheet.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        sheet.column_dimensions[col_letter].width = max_length + 4


def doubles_and_not_found(book_path: Path, results_path: Path):
    process_map = {
        "Не найдено в ЕВМИАС": results_path / "not_found_records.json",
        "Двойники": results_path / "doubles_records.json"
    }

    book = load_workbook(book_path)

    for sheet_name, file_name in process_map.items():
        if file_name.is_file():
            sheet = book.create_sheet(sheet_name)
            sheet.append(["Дата взятия", "ИНЗ", "ФИО", "Дата рождения"])
            with open(file_name, "r", encoding="utf-8") as f:
                data = json.load(f)

            unique_records = set()
            for each in data:
                person = each["person"]
                row_tuple = (
                    each["visit_date"],
                    each["inz"],
                    f"{person['last_name']} {person['first_name']} {person['middle_name']}".strip(),
                    person['birth_day']
                )
                unique_records.add(row_tuple)

            for record in sorted(list(unique_records)):
                sheet.append(record)

            _auto_cells_width(sheet)

            rows_to_align = [1]
            _align_row_center(sheet, rows_to_align)

            columns_to_align = ["A", "B", "D"]
            _align_column_center(sheet, columns_to_align)

    book.save(book_path)
    book.close()


def make_report(data, filename):
    book = load_workbook(filename)
    # задаем цвет для заливки не валидных строк
    invalid_fill = PatternFill(start_color="FFFFC7CE", end_color="FFFFC7CE", fill_type="solid")

    sheet = book.create_sheet("Для работы")
    sheet.append([
        "Дата взятия", "ИНЗ", "ФИО", "Дата рождения", "Код теста",
        "Название теста", "Кол-во", "Цена", "Оплата", "Комментарий"
    ])

    for each in data:
        visit_date = each["visit_date"]
        inz = each["inz"]
        name = f"{each['last_name']} {each['first_name']} {each['middle_name']}"
        birthday = each['birth_day']
        test_code = each['test_code']
        test_name = each['test_name']
        test_quantity = each['test_quantity']
        test_price = each['test_price']

        test_evmias = each['test_evmias']
        test_report = each['test_report']

        if not test_evmias:
            test_pay_type = ''
            comment = constants.COMMENT_SERVICE_NOT_FOUND.format(test_code)
        elif not test_report:
            test_pay_type = ''
            comment = constants.COMMENT_RESULTS_NOT_FOUND
        else:
            test_pay_type = each['test_pay_type']
            comment = ''

        row = [visit_date, inz, name, birthday, test_code, test_name, test_quantity, test_price, test_pay_type, comment]
        sheet.append(row)

        # Проверяем условие и подкрашиваем строку с невалидными данными по оплате
        if comment:
            # Получаем номер только что добавленной строки
            current_row = sheet.max_row
            # Применяем заливку ко всем ячейкам в этой строке
            for cell in sheet[current_row]:
                cell.fill = invalid_fill

    # автоширина всех колонок
    _auto_cells_width(sheet)

    # выравнивание строк по центру
    rows_to_align = [1]
    _align_row_center(sheet, rows_to_align)

    # выравнивание колонок по центру
    columns_to_align = ["A", "B", "D"]
    _align_column_center(sheet, columns_to_align)

    # задаем формат ячейки 0,00
    price_column = 'H'
    for cell in sheet[price_column][1:]:
        cell.number_format = constants.PRICE_FORMAT

    book.save(filename)
    book.close()
