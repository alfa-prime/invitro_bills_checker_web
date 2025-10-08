document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const status = document.getElementById('status');

    uploadButton.addEventListener('click', async () => {
        // Проверяем длину списка файлов
        if (fileInput.files.length === 0) {
            status.textContent = 'Пожалуйста, выберите файл.';
            return;
        }

        // Берем первый файл из списка (files[0])
        const file = fileInput.files[0];

        status.textContent = `Загрузка файла: ${file.name}...`;

        const formData = new FormData();
        // Добавляем сам файл, а не список
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload/', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                // Попытаемся получить текст ошибки от сервера для лучшей диагностики
                const errorText = await response.text();
                console.error("Server response:", errorText);
                throw new Error('Ошибка сервера при загрузке файла.');
            }

            status.textContent = 'Файл получен! Начинаю скачивание...';

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.download = file.name;
            document.body.appendChild(a);

            a.click();

            window.URL.revokeObjectURL(downloadUrl);
            a.remove();

            status.textContent = 'Файл успешно скачан!';

        } catch (error) {
            console.error('Ошибка:', error);
            status.textContent = 'Произошла ошибка при загрузке файла.';
        }
    });
});