from fastapi import Request, status
from fastapi.responses import JSONResponse
from .logger_setup import logger


async def global_exception_handler(request: Request, exc: Exception):
    """
    Глобальный обработчик для всех необработанных исключений.
    Логирует полное исключение и возвращает стандартизированный JSON-ответ.
    """
    logger.exception(f"Unhandled exception for request {request.method} {request.url}: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected internal error occurred."
            }
        },
    )


class GatewayConnectivityError(Exception):
    """
    Специальное исключение, которое будет вызываться,
    когда GatewayService не может подключиться к шлюзу.
    """
    pass