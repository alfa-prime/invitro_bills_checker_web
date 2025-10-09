from async_lru import alru_cache
from datetime import datetime

from app.service.gateway import GatewayService
from app.core.config import get_settings
from app.core.logger_setup import logger
from . import constants

settings = get_settings()


@alru_cache(maxsize=1024)
async def _fetch_person_id_from_api(
        service: GatewayService, last_name: str, first_name: str, middle_name: str, birth_day: str
) -> str:
    payload = {
        "params": {"c": "Person", "m": "getPersonSearchGrid", "_dc": datetime.now().timestamp()},
        "data": {
            "PersonSurName_SurName": last_name, "PersonFirName_FirName": first_name,
            "PersonSecName_SecName": middle_name, "PersonBirthDay_BirthDay": birth_day,
            "showAll": 1, "searchMode": "all", "allowOverLimit": 1, "page": 1, "start": 0, "limit": 100
        }
    }

    try:
        response_json = await service.make_request(
            method='post',
            json=payload,
        )

        if response_json and "totalCount" in response_json:
            count = response_json["totalCount"]
            if count == 1: return response_json["data"][0]["Person_id"]
            if count == 0: return constants.PERSON_ID_STATUS_NOT_FOUND
            return constants.PERSON_ID_STATUS_MULTIPLE_FOUND

        return constants.PERSON_ID_STATUS_NOT_FOUND

    except Exception as e:
        logger.error(f"Ошибка при обработке ответа от шлюза для '{last_name}': {e}")
        return constants.PERSON_ID_STATUS_API_ERROR


async def fetch_person_id(service: GatewayService, data: dict) -> dict:
    person = data["person"]
    person_id = await _fetch_person_id_from_api(
        service=service,
        last_name=person["last_name"],
        first_name=person["first_name"],
        middle_name=person["middle_name"],
        birth_day=person["birth_day"]
    )
    person["id"] = person_id
    return data


@alru_cache(maxsize=1024)
async def fetch_test_data_from_evmias(service: GatewayService, test_code: str) -> list:
    """
    Получает данные об услуге по ее коду из ЕВМИАС.
    Результат кешируется.
    """
    payload = {
        "params": {
            "c": "UslugaComplex",
            "m": "loadUslugaContentsGrid",
        },
        "data": {
            "object": "UslugaComplex",
            "isClose": 1,
            "UslugaComplex_pid": 3010101000029801,
            "UslugaComplex_CodeName": test_code,
            "limit": 100,
            "start": 0,
            "contents": 2,
            "paging": 2,
        }
    }
    try:
        response_json = await service.make_request(method='post', json=payload)
        return response_json.get("data", [])
    except Exception as e:
        logger.error(f"Ошибка при запросе данных для теста '{test_code}': {e}")
        return []


@alru_cache(maxsize=1024)
async def fetch_person_tests_history(service: GatewayService, person_id: str) -> list:
    """
    Получает историю лабораторных исследований для пациента по его ID.
    """
    payload = {
        "params": {
            "c": "EvnUslugaPar",
            "m": "loadEvnUslugaParPanel",
            "_dc": datetime.now().timestamp()
        },
        "data": {
            "Person_id": person_id,
            "limit": 1000,  # Берем большой лимит, чтобы захватить всю историю
            "page": 1,
            "start": 0,
        }
    }
    try:
        response_json = await service.make_request(method='post', json=payload)
        return response_json.get("data", [])
    except Exception as e:
        logger.error(f"Ошибка при запросе истории анализов для person_id '{person_id}': {e}")
        return []


@alru_cache(maxsize=2048)
async def fetch_test_report(service: GatewayService, event_id: str) -> dict | None:
    payload = {
        "params": {
            "c": "Template",
            "m": "getEvnForm"
        },
        "data": {
            "user_MedStaffFact_id": "3010101000069712",  # Статичный ID пользователя-сервиса
            "object": "EvnUslugaPar",
            "object_id": "EvnUslugaPar_id",
            "object_value": event_id,
            "parent_object": "",
            "archiveRecord": "0",
            "from_MZ": "1",
            "from_MSE": "1",
            "view_section": "main",
            "param_name": "checkAccessRightsTest",
            "param_value": "2"
        }
    }
    try:
        response_json = await service.make_request(method='post', json=payload)
        return response_json
    except Exception as e:
        print(f"Ошибка при запросе отчета для event_id '{event_id}': {e}")
        return None


@alru_cache(maxsize=1024) # Кешируем по person_id
async def fetch_medical_history(service: GatewayService, person_id: str) -> dict | None:
    """
    Получает общую медицинскую историю пациента (EMK).
    """
    payload = {
        "params": {
            "c": "EMK",
            "m": "getPersonHistory"
        },
        "data": {
            "Person_id": person_id,
            "type": 1,
            "userMedStaffFact_id": "3010101000069712",
            "userLpuUnitType_SysNick": "polka",
            # Список запрашиваемых типов событий
            "evnClassList": '["EvnPLDispDop13","EvnUslugaPar","EvnDirection","_EvnLabSample","EvnPL",'\
                            '"_EvnLabRequest","EvnVaccination","CmpCard","DispRefuse","ReturnEvnPrescrMse","OuterRegistry"]'
        }
    }
    try:
        return await service.make_request(method='post', json=payload)
    except Exception as e:
        logger.error(f"Ошибка при запросе мед. истории для person_id '{person_id}': {e}")
        return None


@alru_cache(maxsize=2048) # Кешируем по event_id
async def fetch_pay_type_id(service: GatewayService, evn_id: str) -> str | None:
    """
    Получает PayType_id для конкретного события посещения.
    """
    payload = {
        "params": {
            "c": "EMK",
            "m": "loadEvnVizitPLForm"
        },
        "data": {
            "EvnVizitPL_id": evn_id
        }
    }
    try:
        response_json = await service.make_request(method='post', json=payload)
        # Ответ приходит в виде списка из одного словаря
        if response_json and isinstance(response_json, list):
            return response_json[0].get("PayType_id")
        return None
    except Exception as e:
        logger.error(f"Ошибка при запросе типа оплаты для evn_id '{evn_id}': {e}")
        return None
