import httpx
from fastapi import Request
from app.core import get_settings

settings = get_settings()


async def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.gateway_client

