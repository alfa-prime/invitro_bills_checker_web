from fastapi import APIRouter, Depends


router = APIRouter(prefix="/health", tags=["Health Check"])


@router.get(
    "/",
    summary="Стандартная проверка работоспособности",
    description="Возвращает 'pong', если сервис запущен и отвечает на запросы."
)
async def check():
    """Простая проверка работоспособности сервиса."""
    return {"ping": "pong"}

