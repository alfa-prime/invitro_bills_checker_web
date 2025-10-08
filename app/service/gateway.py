import httpx
from fastapi import HTTPException

from app.core import get_settings, logger


class GatewayService:
    settings = get_settings()

    GATEWAY_ENDPOINT = settings.GATEWAY_REQUEST_ENDPOINT

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def make_request(self, method: str, **kwargs) -> dict:
        """
        Выполняет HTTP-запрос к единственному эндпоинту шлюза.

        :param method: HTTP метод ('get', 'post', 'put', etc.).
        :param kwargs: Аргументы, которые будут переданы в httpx клиент.
                       Например: json=payload, params=query_params, headers=headers.
        """
        base_headers = {
            "origin": self.settings.HEADER_ORIGIN,
            "referer": self.settings.HEADER_REFERER,
            "x-requested-with": "XMLHttpRequest",
            "X-API-KEY": self.settings.API_KEY
        }

        #  Если в kwargs были переданы другие заголовки, объединяем их.
        #  Переданные заголовки имеют приоритет.
        if 'headers' in kwargs:
            base_headers.update(kwargs['headers'])

        # Обновляем kwargs окончательным набором заголовков
        kwargs['headers'] = base_headers

        try:
            if not hasattr(self._client, method.lower()):
                raise ValueError(f"Неподдерживаемый HTTP метод: {method}")

            http_method_func = getattr(self._client, method.lower())

            # Мы передаем эндпоинт и все остальные аргументы напрямую в httpx
            response = await http_method_func(self.GATEWAY_ENDPOINT, **kwargs)

            response.raise_for_status()
            return response.json() if response.content else {}

        except ValueError as exc:
            logger.exception(f"Внутренняя ошибка сервиса: {exc}")
            raise HTTPException(status_code=500, detail=str(exc))
        except httpx.RequestError as exc:
            logger.exception(f"Не удалось подключиться к шлюзу: {exc}")
            raise HTTPException(status_code=503, detail=f"Не удалось подключиться к шлюзу: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.exception(f"Ошибка от шлюза: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка от шлюза: {exc.response.text}")