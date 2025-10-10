document.addEventListener('DOMContentLoaded', () => {
    // Получаем все нужные элементы со страницы
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const uploadArea = document.getElementById('upload-area');
    const progressArea = document.getElementById('progress-area');
    const resultArea = document.getElementById('result-area');
    const errorArea = document.getElementById('error-area');
    const statusText = document.getElementById('status-text');
    const statusDetail = document.getElementById('status-detail');
    const progressBar = document.getElementById('progress-bar');
    const downloadLink = document.getElementById('download-link');
    const errorText = document.getElementById('error-text');

    downloadLink.addEventListener('click', handleDownload);
    uploadButton.addEventListener('click', handleUpload);

    async function handleUpload() {
        if (fileInput.files.length === 0) {
            alert('Пожалуйста, выберите файл.');
            return;
        }
        const file = fileInput.files[0];

        uploadButton.disabled = true;
        uploadButton.textContent = 'Обработка...';

        showArea('progress');
        statusText.textContent = 'Загрузка файла на сервер...';
        statusDetail.textContent = ''; // Очищаем детали
        progressBar.value = 0;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/processing/upload', {
                method: 'POST',
                headers: {
                    'X-API-KEY': 'lXrhZrd7SNdAdU6lkfUQ1wOJzngWHqsAnWu0DmV9QtM'
                },
                body: formData,
            });

            if (!response.ok) throw new Error('Ошибка при загрузке файла.');

            const result = await response.json();
            connectWebSocket(result.task_id);

        } catch (error) {
            showError(error.message);
            resetUploadButton();
        }
    }

    function connectWebSocket(taskId) {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const apiKey = 'lXrhZrd7SNdAdU6lkfUQ1wOJzngWHqsAnWu0DmV9QtM';
        const wsUrl = `${wsProtocol}//${window.location.host}/api/processing/ws/${taskId}?api_key=${apiKey}`;
        const ws = new WebSocket(wsUrl);


        ws.onopen = () => {
            statusText.textContent = 'Соединение установлено, ожидание обработки...';
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.progress === -1) {
                showError(data.message);
                ws.close();
                return; // Выходим из функции
            }

            if (data.progress === 100) {
                console.log("Получено сообщение о завершении:", data);
                downloadLink.dataset.url = data.download_url;
                showArea('result'); // Переключаем интерфейс на результат
                ws.close();
                return; // Выходим из функции
            }

            // Если это обычное сообщение о прогрессе, обновляем UI
            progressBar.value = data.progress;
            if (data.message) {
                statusText.textContent = data.message;
            }
            if (data.detail) {
                statusDetail.textContent = data.detail;
            } else {
                statusDetail.textContent = '';
            }
        };

        ws.onerror = () => {
            showError('Произошла ошибка WebSocket соединения.');
        };
    }

    function resetUI() {
        fileInput.value = '';
        resetUploadButton();
        showArea('upload');
    }

    function resetUploadButton() {
        uploadButton.disabled = false;
        uploadButton.textContent = 'Загрузить и обработать';
    }

    async function handleDownload(event) {
    // Предотвращаем стандартное поведение ссылки (переход по href)
    event.preventDefault();

    const url = downloadLink.dataset.url;
    if (!url) return;

    // Показываем пользователю, что скачивание началось
    const originalText = downloadLink.textContent;
    downloadLink.textContent = 'Подготовка файла...';

    try {
        const apiKey = 'lXrhZrd7SNdAdU6lkfUQ1wOJzngWHqsAnWu0DmV9QtM';

        // Делаем fetch-запрос с правильным заголовком
        const response = await fetch(url, {
            headers: { 'X-API-KEY': apiKey }
        });

        if (!response.ok) {
            throw new Error(`Ошибка при скачивании файла: ${response.statusText}`);
        }

        // Получаем имя файла из заголовка Content-Disposition, если оно есть,
        // или используем имя по умолчанию.
        const disposition = response.headers.get('content-disposition');
        let filename = 'report.xlsx';
        if (disposition && disposition.indexOf('attachment') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) {
              filename = matches[1].replace(/['"]/g, '');
            }
        }

        // Получаем тело ответа как Blob (бинарные данные)
        const blob = await response.blob();

        // Создаем временную ссылку в памяти для скачивания
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = downloadUrl;
        a.download = filename; // Устанавливаем имя файла
        document.body.appendChild(a);

        a.click(); // Имитируем клик для начала скачивания

        // Очищаем временные объекты
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
        resetUI();



    } catch (error) {
        alert(error.message); // Показываем ошибку
    } finally {
        // Возвращаем исходный текст кнопки
        downloadLink.textContent = originalText;
    }
}

    function showArea(areaName) {
        uploadArea.classList.add('hidden');
        progressArea.classList.add('hidden');
        resultArea.classList.add('hidden');
        errorArea.classList.add('hidden');

        if (areaName === 'upload') uploadArea.classList.remove('hidden');
        if (areaName === 'progress') progressArea.classList.remove('hidden');
        if (areaName === 'result') resultArea.classList.remove('hidden');
        if (areaName === 'error') errorArea.classList.remove('hidden');
    }

    function showError(message) {
        errorText.textContent = message;
        showArea('error');
    }
});