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

    uploadButton.addEventListener('click', handleUpload);

    async function handleUpload() {
        if (fileInput.files.length === 0) {
            alert('Пожалуйста, выберите файл.');
            return;
        }
        const file = fileInput.files[0];

        showArea('progress');
        statusText.textContent = 'Загрузка файла на сервер...';
        statusDetail.textContent = ''; // Очищаем детали
        progressBar.value = 0;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/processing/upload', {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) throw new Error('Ошибка при загрузке файла.');
            const result = await response.json();
            connectWebSocket(result.task_id);
        } catch (error) {
            showError(error.message);
        }
    }

    function connectWebSocket(taskId) {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/api/processing/ws/${taskId}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            statusText.textContent = 'Соединение установлено, ожидание обработки...';
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            // ИСПРАВЛЕННАЯ ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ

            // Сначала обработаем особые случаи (ошибка или завершение)
            if (data.progress === -1) {
                showError(data.message);
                ws.close();
                return; // Выходим из функции
            }

            if (data.progress === 100) {
                console.log("Получено сообщение о завершении:", data);
                downloadLink.href = data.download_url;
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

    function showArea(areaName) {
        uploadArea.classList.add('hidden');
        progressArea.classList.add('hidden');
        resultArea.classList.add('hidden');
        errorArea.classList.add('hidden');

        if (areaName === 'progress') progressArea.classList.remove('hidden');
        if (areaName === 'result') resultArea.classList.remove('hidden');
        if (areaName === 'error') errorArea.classList.remove('hidden');
    }

    function showError(message) {
        errorText.textContent = message;
        showArea('error');
    }
});