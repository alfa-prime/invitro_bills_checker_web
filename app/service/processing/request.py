from async_lru import alru_cache
from datetime import datetime

from app.service.gateway import GatewayService
from app.core.config import get_settings
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
        print(f"Ошибка при обработке ответа от шлюза для '{last_name}': {e}")
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
