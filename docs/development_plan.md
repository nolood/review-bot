# Детальный план разработки GLM Code Review Bot

### Этап 1: Инфраструктура проекта
1. **Структура директорий:**
   - `src/` - основной код
   - `src/config/` - конфигурация
   - `tests/` - тесты
   - `logs/` - логи
   - `scripts/` - вспомогательные скрипты

2. **Файлы конфигурации:**
   - `.gitlab-ci.yml` - CI/CD pipeline
   - `requirements.txt` - Python зависимости  
   - `requirements-dev.txt` - dev зависимости
   - `.gitignore` - исключения для git
   - `.env.example` - шаблон переменных окружения
   - `Dockerfile` - опциональный Docker образ

### Этап 2: Ядро системы (файлы и функции)

3. **`review_bot.py` - основной скрипт:**
   - `main()` - точка входа
   - `validate_environment()` - проверка переменных
   - `process_merge_request()` - основная логика

4. **`src/gitlab_client.py` - GitLab API:**
   - `GitLabClient` класс
   - `get_merge_request_diff()` - получение diff
   - `get_merge_request_info()` - информация о MR
   - `post_comment()` - публикация комментария
   - `post_inline_comment()` - коммент по строке

5. **`src/glm_client.py` - GLM API:**
   - `GLMClient` класс
   - `analyze_code_diff()` - анализ diff
   - `format_review_prompt()` - форматирование промпта
   - `parse_response()` - парсинг ответа GLM

6. **`src/diff_parser.py` - обработка diff:**
   - `DiffParser` класс
   - `parse_gitlab_diff()` - парсинг diff
   - `chunk_large_diff()` - разбиение на чанки
   - `extract_file_context()` - контекст файлов
   - `filter_relevant_files()` - фильтрация файлов

7. **`src/comment_publisher.py` - публикация:**
   - `CommentPublisher` класс
   - `format_comments()` - форматирование комментариев
   - `publish_review_summary()` - общее резюме
   - `publish_file_comments()` - комментарии по файлам

### Этап 3: Конфигурация и утилиты

8. **`src/config/prompts.py` - промпты для GLM:**
   - `CODE_REVIEW_PROMPT` - базовый промпт
   - `SECURITY_REVIEW_PROMPT` - проверка безопасности
   - `PERFORMANCE_REVIEW_PROMPT` - оптимизация

9. **`src/config/settings.py` - настройки:**
   - `Settings` класс с Pydantic
   - Валидация переменных окружения
   - Значения по умолчанию

10. **`src/utils/logger.py` - логирование:**
    - Настройка структурированного логирования
    - Форматирование логов GLM запросов/ответов
    - Уровни логирования

### Этап 4: Обработка ошибок и reliability

11. **`src/utils/retry.py` - retry логика:**
    - `@retry_with_backoff` декоратор
    - Экспоненциальный backoff
    - Максимальное количество попыток

12. **`src/utils/exceptions.py` - исключения:**
    - `GLMAPIError` - ошибки GLM API
    - `GitLabAPIError` - ошибки GitLab API
    - `DiffParsingError` - ошибки парсинга

13. **Обработка edge cases:**
    - Пустые diff
    - Слишком большие diff (>200K токенов)
    - Недоступность GLM API
    - Отсутствие прав доступа

### Этап 5: CI/CD и тестирование

14. **`.gitlab-ci.yml` pipeline:**
    ```yaml
    stages:
      - test
      - review
    
    test:
      stage: test
      script:
        - pytest tests/
        - black --check src/
        - flake8 src/
      only:
        - merge_requests
    
    code_review:
      stage: review
      script:
        - python review_bot.py
      only:
        - merge_requests
      artifacts:
        paths:
          - logs/
    ```

15. **Тесты в `tests/`:**
    - `test_gitlab_client.py` - моки GitLab API
    - `test_glm_client.py` - моки GLM API
    - `test_diff_parser.py` - тесты парсинга
    - `test_integration.py` - интеграционные тесты

### Этап 6: Документация и финализация

16. **`README.md` документация:**
    - Установка и настройка
    - Пример использования
    - Требования к переменным окружения

17. **Опциональные улучшения:**
    - Поддержка разных языков программирования
    - Кастомные правила ревью
    - Метрики и аналитика
    - Игнорирование определенных файлов/паттернов

### Детальный workflow для каждой MR:
1. GitLab CI запускает pipeline на MR
2. `review_bot.py` проверяет переменные окружения
3. `GitLabClient` получает diff и информацию о MR
4. `DiffParser` обрабатывает diff и разбивает на чанки при необходимости
5. `GLMClient` отправляет каждый чанк в GLM-4.6 API
6. `CommentPublisher` форматирует и публикует комментарии
7. Логи сохраняются для аналитики и отладки

### Ключевые технические решения:
- **GLM API**: POST `https://api.z.ai/api/paas/v4/chat/completions`
- **Аутентификация**: `Authorization: Bearer ${GLM_API_KEY}`
- **Лимиты**: 200K токенов контекст, разбиение на чанки по ~50K токенов
- **Формат комментариев**: JSON `{file, line, comment, severity}`