from typing import Annotated

from fastapi import APIRouter, Depends

from app.core import get_gateway_service
from app.model import GatewayRequest
from app.service.gateway import GatewayService

router = APIRouter(prefix="/health", tags=["Health Check"])


@router.get(
    "/",
    summary="Стандартная проверка работоспособности",
    description="Возвращает 'pong', если сервис запущен и отвечает на запросы."
)
async def check():
    """Простая проверка работоспособности сервиса."""
    return {"ping": "pong"}


@router.post(
    "/gateway",
    summary="Проверка связи со шлюзом API",
    description="Отправляет тестовый запрос на API-шлюз для проверки связи и аутентификации."
)
async def check_gateway_connection(
        gateway_service: Annotated[GatewayService, Depends(get_gateway_service)]
):
    payload_dict = {
        "params": {"c": "Common", "m": "getCurrentDateTime"},
        "data": {"is_activerulles": "true"}
    }

    validated_payload = GatewayRequest.model_validate(payload_dict)

    response = await gateway_service.make_request(
        'post',
        json=validated_payload.model_dump()
    )

    return response
