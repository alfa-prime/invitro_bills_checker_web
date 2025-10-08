from typing import Annotated
import httpx
from fastapi import Request, Depends
from app.service.gateway import GatewayService


async def get_base_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.gateway_client


async def get_gateway_service(client: Annotated[httpx.AsyncClient, Depends(get_base_http_client)]) -> GatewayService:
    return GatewayService(client=client)
