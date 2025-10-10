from typing import Annotated, Optional
import httpx
from fastapi import Request, Depends, Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings

from app.service.gateway import GatewayService

settings = get_settings()


async def get_base_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.gateway_client


async def get_gateway_service(client: Annotated[httpx.AsyncClient, Depends(get_base_http_client)]) -> GatewayService:
    return GatewayService(client=client)


api_key_header_scheme = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(api_key_header_scheme)):
    """
    Проверяет X-API-KEY из заголовка запроса.
    """
    if api_key and api_key == settings.APP_API_KEY:
        return api_key

    # Если ключ отсутствует или неверный, возвращаем ошибку 403 Forbidden
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Отсутствует или неверный API ключ в заголовке 'X-API-KEY'.",
    )
