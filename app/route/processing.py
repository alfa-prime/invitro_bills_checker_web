import uuid
import shutil
from pathlib import Path
from fastapi import (
    APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect,
    BackgroundTasks, HTTPException, Depends
)
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.websocket_manager import manager
from app.core.config import get_settings

from app.service.processing.getter import (
    get_raw_data,
    get_ids,
    get_test_data_from_evmias,
    get_person_tests_history,
    get_pay_type, get_medical_history
)
from app.service.processing.sanitizer import sanitize_raw_data, sanitize_persons_tests_history, sanitize_for_report
from app.service.processing.tool import separate_records, doubles_and_not_found, save_json, make_report

from app.core import get_gateway_service
from app.service.gateway import GatewayService

router = APIRouter(prefix="/api/processing", tags=["Data Processing"])
settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "materials" / "uploads"
RESULTS_DIR = BASE_DIR / "materials" / "results"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def run_processing_pipeline(task_id: str, input_path: Path, output_path: Path, service: GatewayService):
    """
    pipeline обработки файла.
    """
    task_results_path = RESULTS_DIR / task_id
    task_results_path.mkdir(exist_ok=True)

    try:
        await manager.send_progress(task_id, {"progress": 2, "message": "Чтение данных из файла..."})
        raw_data = await run_in_threadpool(get_raw_data, input_path, settings.START_ROW, settings.MAX_COL)
        await run_in_threadpool(save_json, raw_data,
                                task_results_path / "01.raw_data.json")

        await manager.send_progress(task_id, {"progress": 5, "message": "Подготовка данных..."})
        sanitized_data = await run_in_threadpool(sanitize_raw_data, raw_data)
        await run_in_threadpool(save_json, sanitized_data,
                                task_results_path / "02.sanitized_raw_data.json")

        await manager.send_progress(task_id, {"progress": 10, "message": "Поиск ID пациентов в ЕВМИАС..."})
        persons_ids = await get_ids(
            service, sanitized_data,
            task_id=task_id, manager=manager,
            start_progress=10, end_progress=20
        )
        await run_in_threadpool(save_json, persons_ids,
                                task_results_path / "03.persons_ids.json")

        await manager.send_progress(task_id, {"progress": 20, "message": "Анализ полученных ID..."})
        valid_records = await run_in_threadpool(separate_records, persons_ids, task_results_path)
        await run_in_threadpool(save_json, valid_records,
                                task_results_path / "04.valid_records.json")

        await manager.send_progress(task_id, {"progress": 25, "message": "Сохранение 'не найденных' и 'двойников'..."})
        await run_in_threadpool(shutil.copy, input_path, output_path)
        await run_in_threadpool(doubles_and_not_found, output_path, task_results_path)

        await manager.send_progress(task_id, {"progress": 30, "message": "Получение данных об услугах из ЕВМИАС ..."})
        test_data_from_evmias = await get_test_data_from_evmias(
            service, valid_records,
            task_id=task_id, manager=manager,
            start_progress=30, end_progress=40
        )
        await run_in_threadpool(save_json, test_data_from_evmias,
                                task_results_path / "05.test_data_from_evmias.json")

        await manager.send_progress(task_id, {"progress": 40, "message": "Запрос истории анализов пациентов..."})
        persons_tests_history = await get_person_tests_history(
            service, test_data_from_evmias,
            task_id=task_id, manager=manager,
            start_progress=40, end_progress=50
        )
        await run_in_threadpool(save_json, persons_tests_history, task_results_path / "06.persons_tests_history.json")

        await manager.send_progress(task_id, {"progress": 60, "message": "Очистка данных истории анализов..."})
        sanitized_persons_tests_history = await run_in_threadpool(sanitize_persons_tests_history, persons_tests_history)
        await run_in_threadpool(save_json, sanitized_persons_tests_history,
                                task_results_path / "07.sanitized_persons_tests_history.json")

        await manager.send_progress(task_id, {"progress": 70, "message": "Определение типа оплаты #1..."})
        records_with_pay_type = await get_pay_type(
            service, sanitized_persons_tests_history,
            task_id=task_id, manager=manager,
            start_progress=70, end_progress=80
        )
        await run_in_threadpool(save_json, records_with_pay_type,
                                task_results_path / "08.pay_type_by_tests_history.json")

        await manager.send_progress(task_id, {"progress": 80, "message": "Определение типа оплаты #2..."})
        medical_history = await get_medical_history(
            service, records_with_pay_type,
            task_id=task_id, manager=manager,
            start_progress=80, end_progress=90
        )
        await run_in_threadpool(save_json, medical_history,
                                task_results_path / "09.pay_type_by_medical_history.json")

        await manager.send_progress(task_id, {"progress": 90, "message": "Подготовка отчета..."})
        data_for_report = await run_in_threadpool(sanitize_for_report, medical_history)
        await run_in_threadpool(save_json, data_for_report,
                                task_results_path / "10.data_for_report.json")

        await run_in_threadpool(make_report, data_for_report, output_path)

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
        service: GatewayService = Depends(get_gateway_service)
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Неверный формат файла. Требуется .xlsx")

    task_id = str(uuid.uuid4())
    input_path = UPLOADS_DIR / f"{task_id}_{file.filename}"
    output_path = RESULTS_DIR / f"{task_id}_report.xlsx"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(run_processing_pipeline, task_id, input_path, output_path, service)

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
