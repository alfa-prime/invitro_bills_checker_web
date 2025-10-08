"""
Этот модуль содержит глобальные константы, используемые в проекте,
чтобы избежать "магических" строк и чисел в коде.
"""

# Статусы поиска ID пациента
PERSON_ID_STATUS_NOT_FOUND = '404'
PERSON_ID_STATUS_MULTIPLE_FOUND = '500'
PERSON_ID_STATUS_API_ERROR = '503_API_ERROR'

PRICE_FORMAT = '0.00'

COMMENT_SERVICE_NOT_FOUND = "Услуга с кодом '{}' не найдена в ЕВМИАС"
COMMENT_RESULTS_NOT_FOUND = "Результаты не найдены в ЕВМИАС"

