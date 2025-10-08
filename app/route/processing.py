import uuid
import shutil
from pathlib import Path
import httpx
from fastapi import (
    APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect,
    BackgroundTasks, HTTPException, Depends
)
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.websocket_manager import manager
from app.core.config import get_settings
from app.core import get_http_client

from app.service.processing.getter import get_raw_data, get_ids
from app.service.processing.sanitizer import sanitize_raw_data
from app.service.processing.tool import separate_records, doubles_and_not_found, save_json

router = APIRouter(prefix="/api/processing", tags=["Data Processing"])
settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "materials" / "uploads"
RESULTS_DIR = BASE_DIR / "materials" / "results"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def run_processing_pipeline(task_id: str, input_path: Path, output_path: Path, client: httpx.AsyncClient):
    """
    pipeline обработки файла.
    """
    task_results_path = RESULTS_DIR / task_id
    task_results_path.mkdir(exist_ok=True)

    try:
        # Шаг 1: Получение сырых данных
        await manager.send_progress(task_id, {"progress": 10, "message": "Чтение данных из файла..."})
        raw_data = await run_in_threadpool(get_raw_data, input_path, settings.START_ROW, settings.MAX_COL)

        # Шаг 2: Санитизация данных
        await manager.send_progress(task_id, {"progress": 25, "message": "Подготовка данных..."})
        sanitized_data = await run_in_threadpool(sanitize_raw_data, raw_data)

        # Шаг 3: Получение ID пациентов (сетевая операция)
        await manager.send_progress(task_id, {"progress": 50, "message": "Запрос ID пациентов из ЕВМИАС..."})
        persons_ids = await get_ids(client, sanitized_data, task_id=task_id, manager=manager)

        # Шаг 4: Отделение валидных записей
        await manager.send_progress(task_id, {"progress": 75, "message": "Анализ полученных ID..."})
        valid_records = await run_in_threadpool(separate_records, persons_ids, task_results_path)

        # Шаг 5: Создание отчета с "не найденными" и "двойниками"
        await manager.send_progress(task_id, {"progress": 90, "message": "Формирование отчета..."})
        await run_in_threadpool(shutil.copy, input_path, output_path)
        await run_in_threadpool(doubles_and_not_found, output_path, task_results_path)

        download_url = f"/api/processing/download/{task_id}"
        await manager.send_progress(task_id, {
            "progress": 100, "message": "Отчет готов к скачиванию!", "download_url": download_url
        })

    except Exception as e:
        print(f"ОШИБКА в задаче {task_id}: {e}")
        await manager.send_progress(task_id, {"progress": -1, "message": f"Произошла критическая ошибка: {e}"})


@router.post("/upload", summary="Загрузка файла и запуск обработки")
async def upload_and_process(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        client: httpx.AsyncClient = Depends(get_http_client)
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Неверный формат файла. Требуется .xlsx")

    task_id = str(uuid.uuid4())
    input_path = UPLOADS_DIR / f"{task_id}_{file.filename}"
    output_path = RESULTS_DIR / f"{task_id}_report.xlsx"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(run_processing_pipeline, task_id, input_path, output_path, client)

    return {"task_id": task_id}


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id)


@router.get("/download/{task_id}", summary="Скачивание обработанного файла")
async def download_result(task_id: str):
    file_path = RESULTS_DIR / f"{task_id}_report.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден или еще не готов.")
    return FileResponse(path=file_path, filename="report.xlsx")
