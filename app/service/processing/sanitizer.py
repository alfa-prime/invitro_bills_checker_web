from typing import Any
import datetime as dt
from datetime import datetime, timedelta
from dateutil.parser import parse

from . import constants
from app.service.processing.tool import is_person_id_valid
from .pay_type_mapper import PAY_TYPE_IDS


def sanitize_for_report(data: list) -> list[dict]:
    """
    Преобразует сложные вложенные данные в ПЛОСКУЮ структуру,
    которую ожидает функция `make_report`.
    """
    result = []
    for row in data:
        person = row.get("person", {})
        test_src = row.get("test_src", {})
        test_evmias = row.get("test_evmias")
        test_report = row.get("test_report")
        person_id = person.get("id")

        # Переменные для финального отчета
        final_pay_type = ""
        final_comment = ""

        # Логика определения комментария и типа оплаты
        if person_id == constants.PERSON_ID_STATUS_NOT_FOUND:
            final_comment = "Пациент не найден в ЕВМИАС (сверить установочные данные)"
        elif person_id == constants.PERSON_ID_STATUS_MULTIPLE_FOUND:
            final_comment = "Найдено несколько пациентов (двойники)"
        elif person_id == constants.PERSON_ID_STATUS_API_ERROR:
            final_comment = "Ошибка API при поиске пациента"
        elif not test_evmias:
            final_comment = constants.COMMENT_SERVICE_NOT_FOUND.format(test_src.get('code', ''))
        elif not test_report:
            final_comment = constants.COMMENT_RESULTS_NOT_FOUND
        else:
            final_pay_type = test_report.get("pay_type", "")

        # ИСПРАВЛЕНИЕ: Создаем ПЛОСКИЙ словарь
        result.append({
            # Данные пациента на верхнем уровне
            'last_name': person.get('last_name', ''),
            'first_name': person.get('first_name', ''),
            'middle_name': person.get('middle_name', ''),
            'birth_day': person.get('birth_day', ''),

            # Остальные данные
            "visit_date": row.get("visit_date", ""),
            "inz": row.get("inz", ""),
            "test_code": test_src.get("code", ""),
            "test_name": test_src.get("name", ""),
            "test_quantity": test_src.get("quantity", 0),
            "test_price": test_src.get("price", 0.0),

            # Результаты анализа
            'test_pay_type': final_pay_type,  # Используем ключ, который ожидает make_report
            'comment': final_comment,  # Передаем рассчитанный комментарий

            # Сохраняем оригинальные объекты для make_report, если они нужны
            'test_evmias': test_evmias,
            'test_report': test_report
        })
    return result



def sanitize_medical_history(raw_data: dict, visit_date: str):
    data = raw_data.get("data", {})
    visit_date = datetime.strptime(visit_date, '%d.%m.%Y')
    border_date = visit_date - timedelta(days=14)
    result = []
    if data:
        for each in data:
            if each["EvnType"] not in ["direction", "par", "disp"]:
                set_date = datetime.strptime(each["objectSetDate"], '%d.%m.%Y')
                if border_date < set_date <= visit_date:
                    evn_id = each["children"][0].get("Evn_id")

                    sanitized_each = {
                        "date_set": each["objectSetDate"],
                        "date_dis": each["objectDisDate"],
                        "med_personal_id": each["MedPersonal_id"],
                        "evn_class_name": each["EvnClass_Name"],
                        "diag_code": each["Diag_Code"],
                        "diag_name": each["Diag_Name"],
                        "evn_type": each["EvnType"],
                        "children_evn_id": evn_id,
                        "med_staff_fact_id": each["children"][0]["MedStaffFact_id"]
                    }
                    result.append(sanitized_each)
    return result


def sanitize_test_info(data: dict) -> dict[str, Any] | None:
    return {
        "direction_id": data.get("EvnDirection_id"),
        "pay_type_id": data.get("PayType_id"),
        "pay_type": PAY_TYPE_IDS[data.get("PayType_id")],
    }


def _sanitize_history_item(data: list) -> list:
    result = []
    for row in data:
        result.append({
            "event_id": row["Evn_id"],
            "med_personal_id": row["ED_MedPersonal_id"],
            "date": row["EvnUslugaPar_setDate"],
            "test_name": row["UslugaComplex_Name"],
            "tests_group_name": row["MedService_Name"],
            "test_id": row["UslugaComplex_id"],
            "sort": row["sort"],
        })
    return result


def sanitize_persons_tests_history(data: list) -> list:
    result = []
    for row in data:
        person_id = row.get("person", {}).get("id")
        if not is_person_id_valid(person_id):
            result.append(row)
            continue
        test_history = row.get("tests_history")
        sanitize_history = _sanitize_history_item(test_history)
        try:
            test = row.get("test_evmias", None)
            if test is not None:
                test_id = test.get("id")

                if test_id is not None and isinstance(sanitize_history, list):
                    filtered_history = [
                        history_item for history_item in sanitize_history
                        if history_item.get("test_id") == test_id
                    ]

                    if len(filtered_history) > 1:
                        visit_date = row.get("visit_date")
                        visit_date = datetime.strptime(visit_date, '%d.%m.%Y')
                        try:
                            filtered_history = min(
                                filtered_history,
                                key=lambda record: abs(datetime.strptime(record['sort'], '%Y-%m-%d %H:%M:%S') - visit_date)
                            )
                        except ValueError:
                            pass
                            # print(row['person'])
                            # print(json.dumps(filtered_history, indent=4, ensure_ascii=False))
                    row["tests_history"] = filtered_history
            else:
                row["tests_history"] = sanitize_history
            result.append(row)

        except (TypeError, AttributeError):
            row["tests_history"] = sanitize_history
            result.append(row)
            continue

    return result


def sanitize_test_data_from_evmias(data: dict) -> dict:
    return {
        "id": data.get("UslugaComplex_id", ""),
        "code": data.get("UslugaComplex_Code", ""),
        "name": data.get("UslugaComplex_Name", ""),
    }


def _sanitize_birthday(raw_date_birth: Any) -> str:
    """
    Универсально обрабатывает дату рождения, принимая на вход:
    - объект datetime.datetime или datetime.date
    - строку в формате 'ДДММГГ...' (например, '120378МЁ4ВЪ')
    - строку с датой в стандартном формате ('12.03.1978', '1978-03-12' и т.д.)

    Возвращает дату в виде строки "ДД.ММ.ГГГГ".
    """
    # 1. Лучший случай: на входе уже объект datetime или date
    if isinstance(raw_date_birth, (dt.datetime, dt.date)):
        return raw_date_birth.strftime("%d.%m.%Y")

    # 2. Если это не строка, мы не знаем, что с этим делать
    if not isinstance(raw_date_birth, str):
        raise TypeError(f"Неподдерживаемый тип для даты рождения: {type(raw_date_birth)}")

    # --- Далее работаем только со строкой ---

    # 3. Попытка №1: обработать как специфичный формат 'ДДММГГ...'
    try:
        date_part = raw_date_birth[:6]
        if not date_part.isdigit() or len(date_part) != 6:
            # Если первые 6 символов - не цифры, этот формат нам не подходит,
            # вызываем ошибку, чтобы перейти к следующему блоку except
            raise ValueError("Формат не является ДДММГГ")

        day = int(date_part[:2])
        month = int(date_part[2:4])
        year_yy = int(date_part[4:])

        current_year_yy = datetime.today().year % 100
        current_century = (datetime.today().year // 100) * 100

        if year_yy > current_year_yy:
            year = current_century - 100 + year_yy
        else:
            year = current_century + year_yy

        valid_date = dt.date(year, month, day)
        return valid_date.strftime("%d.%m.%Y")

    except (ValueError, TypeError):
        # Эта попытка не удалась, ничего страшного. Пробуем следующий способ.
        pass

    # 4. Попытка №2: обработать как стандартную строку с датой
    try:
        # dateutil.parser.parse - очень умный парсер
        # dayfirst=True помогает правильно распознать даты вида '01.02.2023'
        # как 1 февраля, а не 2 января.
        valid_date = parse(raw_date_birth, dayfirst=True)
        return valid_date.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        # Если и эта попытка провалилась, значит формат действительно неизвестен
        pass

    # 5. Если ничего не помогло - вызываем ошибку
    raise ValueError(f"Не удалось распознать формат даты рождения: '{raw_date_birth}'")


def _sanitize_name(raw_name: str) -> list[str]:
    """
    Разбивает строку с ФИО на список из фамилии, имени и отчества.
    Учитывает двойные отчества (например, "оглы", "кызы").
    """
    raw_name = raw_name.title()
    name_parts = raw_name.strip().split()

    if len(name_parts) > 3:
        name_parts[2] = f"{name_parts[2]} {name_parts[3]}"
        name_parts = name_parts[:3]

    while len(name_parts) < 3:
        name_parts.append("")

    return name_parts


def sanitize_raw_data(data):
    sanitized = []
    for row in data:
        visit_date, raw_birthday, inz, full_name, test_code, test_name, test_quantity, test_price = row
        last, first, middle = _sanitize_name(full_name)
        birthday = _sanitize_birthday(raw_birthday)

        sanitized.append({
            "inz": inz,
            "visit_date": visit_date,
            "person": {
                "last_name": last,
                "first_name": first,
                "middle_name": middle,
                "birth_day": birthday
            },
            "test_src": {
                "code": test_code,
                "name": test_name,
                "quantity": test_quantity,
                "price": float(test_price)
            }
        })
    return sanitized
