from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
import io

router = APIRouter(prefix="/api/upload", tags=["File Upload"])


@router.post(
    "/",
    summary="Загрузка файла и его возврат",
    description="Принимает файл и немедленно отправляет его обратно для скачивания."
)
async def upload_and_echo_file(file: UploadFile = File(...)):
    """
    Этот эндпоинт читает байты из загруженного файла в память
    и возвращает их в виде StreamingResponse, чтобы браузер мог их скачать.
    """
    # Читаем содержимое файла в буфер в памяти
    file_content = await file.read()
    file_buffer = io.BytesIO(file_content)

    # Устанавливаем указатель в начало буфера
    file_buffer.seek(0)

    # Создаем заголовки, чтобы браузер понял, что это файл для скачивания
    headers = {'Content-Disposition': f'attachment; filename="{file.filename}"'}

    return StreamingResponse(file_buffer, media_type=file.content_type, headers=headers)