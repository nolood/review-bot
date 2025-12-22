# Детальный план интеграции GLM Code Review Bot для GitLab

## Обзор
Данный документ описывает пошаговый план реализации бота для автоматического код-ревью на основе GLM-4.6 модели, интегрированного в GitLab CI/CD.

## Фаза 1: Подготовка окружения и базовая структура

### 1.1 Создание структуры проекта
```
/
├── .gitlab-ci.yml          # CI/CD конфигурация
├── Dockerfile              # Опционально, для Docker-образа
├── requirements.txt        # Python зависимости
├── review_bot.py          # Основной скрипт бота
├── src/
│   ├── __init__.py
│   ├── gitlab_client.py   # Работа с GitLab API
│   ├── glm_client.py      # Работа с GLM API
│   ├── diff_parser.py     # Парсинг diff изменений
│   └── comment_publisher.py # Публикация комментариев
├── tests/
│   ├── test_gitlab_client.py
│   ├── test_glm_client.py
│   ├── test_diff_parser.py
│   └── test_comment_publisher.py
└── config/
    └── prompts.py         # Шаблоны промптов для GLM
```

### 1.2 Базовые зависимости (requirements.txt)
```
requests>=2.31.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

## Фаза 2: Настройка CI/CD

### 2.1 .gitlab-ci.yml конфигурация
```yaml
stages:
  - review

variables:
  PYTHON_VERSION: "3.11"

code_review:
  stage: review
  image: python:${PYTHON_VERSION}
  before_script:
    - pip install -r requirements.txt
  script:
    - python review_bot.py
  only:
    - merge_requests
  artifacts:
    paths:
      - review_logs/
    expire_in: 1 week
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

### 2.2 Переменные окружения в GitLab
Необходимо создать в GitLab Project Settings > CI/CD > Variables:

- `GLM_API_KEY` (Protected, Masked) - API ключ для GLM-4.6
- `GITLAB_TOKEN` (Protected, Masked) - Personal Access Token с scopes: api, read_repository
- `GITLAB_API_URL` - URL GitLab API (например: https://gitlab.com/api/v4)

## Фаза 3: Реализация основных компонентов

### 3.1 GitLab API клиент (src/gitlab_client.py)
```python
import requests
import os
from typing import Dict, List, Any

class GitLabClient:
    def __init__(self):
        self.token = os.getenv('GITLAB_TOKEN')
        self.api_url = os.getenv('GITLAB_API_URL', 'https://gitlab.com/api/v4')
        self.project_id = os.getenv('CI_PROJECT_ID')
        self.mr_iid = os.getenv('CI_MERGE_REQUEST_IID')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def get_merge_request_diff(self) -> str:
        """Получение diff для merge request"""
        url = f"{self.api_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}/diffs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return self._format_diff(response.json())
    
    def post_comment(self, body: str, position: Dict[str, Any] = None) -> Dict:
        """Публикация комментария в MR"""
        url = f"{self.api_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}/notes"
        data = {'body': body}
        if position:
            data['position'] = position
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def _format_diff(self, diffs: List[Dict]) -> str:
        """Форматирование diff в текстовый формат"""
        formatted_diff = []
        for diff in diffs:
            formatted_diff.append(f"--- {diff['old_path']}")
            formatted_diff.append(f"+++ {diff['new_path']}")
            formatted_diff.append(diff['diff'])
        return '\n'.join(formatted_diff)
```

### 3.2 GLM API клиент (src/glm_client.py)
```python
import requests
import json
import os
from typing import Dict, List

class GLMClient:
    def __init__(self):
        self.api_key = os.getenv('GLM_API_KEY')
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    def analyze_code(self, diff: str, prompt_template: str = None) -> Dict:
        """Отправка diff в GLM для анализа"""
        if not prompt_template:
            prompt_template = self._get_default_prompt()
        
        prompt = f"{prompt_template}\n\nDiff:\n{diff}"
        
        payload = {
            "model": "glm-4",
            "messages": [
                {"role": "system", "content": "Ты - опытный код-ревьюер. Анализируй код и давай конструктивные рекомендации."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(self.api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        return self._parse_response(response.json())
    
    def _get_default_prompt(self) -> str:
        """Стандартный промпт для анализа кода"""
        return """Проанализируй этот код и предложи:
1. Улучшение читаемости
2. Исправление потенциальных багов
3. Оптимизацию функций

Формат ответа: JSON со структурой:
{
  "comments": [
    {
      "file": "путь/к/файлу",
      "line": номер_строки,
      "comment": "текст_комментария",
      "severity": "low|medium|high"
    }
  ]
}"""
    
    def _parse_response(self, response: Dict) -> Dict:
        """Парсинг ответа от GLM"""
        try:
            content = response['choices'][0]['message']['content']
            # Попытка распарсить JSON
            return json.loads(content)
        except (KeyError, json.JSONDecodeError):
            # Если не JSON, возвращаем как текст
            return {"comments": [{"comment": content, "severity": "medium"}]}
```

### 3.3 Парсер diff (src/diff_parser.py)
```python
from typing import Dict, List, Tuple
import re

class DiffParser:
    @staticmethod
    def parse_diff(diff_text: str) -> List[Dict]:
        """Парсинг diff текста и извлечение изменений по файлам"""
        files = []
        current_file = None
        
        lines = diff_text.split('\n')
        for line in lines:
            # Определение нового файла
            if line.startswith('+++ b/'):
                if current_file:
                    files.append(current_file)
                current_file = {
                    'path': line[6:],
                    'changes': []
                }
            # Добавление строк изменений
            elif line.startswith('+') and not line.startswith('+++'):
                if current_file:
                    current_file['changes'].append({
                        'type': 'addition',
                        'content': line[1:],
                        'line': None  # Будет определено позже
                    })
            elif line.startswith('-') and not line.startswith('---'):
                if current_file:
                    current_file['changes'].append({
                        'type': 'deletion',
                        'content': line[1:],
                        'line': None  # Будет определено позже
                    })
        
        if current_file:
            files.append(current_file)
        
        return files
    
    @staticmethod
    def chunk_diff(diff_text: str, max_tokens: int = 3000) -> List[str]:
        """Разбиение большого diff на чанки"""
        if len(diff_text) <= max_tokens:
            return [diff_text]
        
        chunks = []
        current_chunk = ""
        files = DiffParser.parse_diff(diff_text)
        
        for file_diff in files:
            file_text = f"+++ b/{file_diff['path']}\n"
            for change in file_diff['changes']:
                prefix = '+' if change['type'] == 'addition' else '-'
                file_text += f"{prefix}{change['content']}\n"
            
            if len(current_chunk) + len(file_text) > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = file_text
            else:
                current_chunk += file_text
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
```

### 3.4 Публикатор комментариев (src/comment_publisher.py)
```python
from typing import Dict, List
from .gitlab_client import GitLabClient
import markdown

class CommentPublisher:
    def __init__(self, gitlab_client: GitLabClient):
        self.gitlab_client = gitlab_client
    
    def publish_review(self, analysis_result: Dict) -> None:
        """Публикация результатов анализа в MR"""
        if 'comments' not in analysis_result:
            self._publish_general_comment("Не удалось проанализировать код")
            return
        
        comments = analysis_result['comments']
        
        # Группировка комментариев по файлам
        file_comments = {}
        general_comments = []
        
        for comment in comments:
            if 'file' in comment and 'line' in comment:
                file_key = comment['file']
                if file_key not in file_comments:
                    file_comments[file_key] = []
                file_comments[file_key].append(comment)
            else:
                general_comments.append(comment)
        
        # Публикация общих комментариев
        if general_comments:
            self._publish_general_comments(general_comments)
        
        # Публикация файловых комментариев
        for file_path, comments in file_comments.items():
            self._publish_file_comments(file_path, comments)
    
    def _publish_general_comments(self, comments: List[Dict]) -> None:
        """Публикация общих комментариев"""
        body = "## 🤖 GLM Code Review\n\n"
        for comment in comments:
            severity_emoji = self._get_severity_emoji(comment.get('severity', 'medium'))
            body += f"{severity_emoji} {comment['comment']}\n\n"
        
        self.gitlab_client.post_comment(body)
    
    def _publish_file_comments(self, file_path: str, comments: List[Dict]) -> None:
        """Публикация комментариев для конкретного файла"""
        body = f"## 📁 {file_path}\n\n"
        
        for comment in comments:
            severity_emoji = self._get_severity_emoji(comment.get('severity', 'medium'))
            line_info = f" (строка {comment['line']})" if 'line' in comment else ""
            body += f"{severity_emoji}{line_info}: {comment['comment']}\n\n"
        
        # Публикация с позицией в файле (если есть line)
        position = None
        if comments and 'line' in comments[0]:
            position = {
                "base_sha": self.gitlab_client.get_base_sha(),
                "start_sha": self.gitlab_client.get_start_sha(),
                "head_sha": self.gitlab_client.get_head_sha(),
                "position_type": "text",
                "new_path": file_path,
                "new_line": comments[0]['line']
            }
        
        self.gitlab_client.post_comment(body, position)
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Получение эмодзи для уровня серьезности"""
        severity_map = {
            'low': '💡',
            'medium': '⚠️',
            'high': '🚨'
        }
        return severity_map.get(severity, 'ℹ️')
```

## Фаза 4: Основной скрипт бота

### 4.1 review_bot.py
```python
#!/usr/bin/env python3
import os
import logging
import json
from datetime import datetime

from src.gitlab_client import GitLabClient
from src.glm_client import GLMClient
from src.diff_parser import DiffParser
from src.comment_publisher import CommentPublisher

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('review_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Starting GLM Code Review Bot")
    
    try:
        # Инициализация клиентов
        gitlab_client = GitLabClient()
        glm_client = GLMClient()
        diff_parser = DiffParser()
        comment_publisher = CommentPublisher(gitlab_client)
        
        # Получение diff
        logger.info("Fetching merge request diff")
        diff = gitlab_client.get_merge_request_diff()
        
        if not diff.strip():
            logger.info("No changes found in merge request")
            return
        
        # Проверка размера diff и разбиение на чанки при необходимости
        chunks = diff_parser.chunk_diff(diff)
        logger.info(f"Processing {len(chunks)} chunks")
        
        all_comments = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            # Отправка в GLM
            analysis = glm_client.analyze_code(chunk)
            
            if 'comments' in analysis:
                all_comments.extend(analysis['comments'])
            
            # Сохранение промежуточных результатов
            with open(f'review_logs/chunk_{i+1}_analysis.json', 'w') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # Публикация результатов
        if all_comments:
            logger.info(f"Publishing {len(all_comments)} comments")
            result = {'comments': all_comments}
            comment_publisher.publish_review(result)
        else:
            logger.info("No comments generated")
        
        # Сохранение финального результата
        timestamp = datetime.now().isoformat()
        with open(f'review_logs/final_result_{timestamp}.json', 'w') as f:
            json.dump({'comments': all_comments}, f, indent=2, ensure_ascii=False)
        
        logger.info("Review completed successfully")
        
    except Exception as e:
        logger.error(f"Error during review process: {str(e)}")
        # Попытка публикации ошибки в MR
        try:
            gitlab_client = GitLabClient()
            error_message = f"## 🚨 GLM Code Review Error\n\n```\n{str(e)}\n```"
            gitlab_client.post_comment(error_message)
        except:
            pass
        raise

if __name__ == "__main__":
    main()
```

## Фаза 5: Тестирование и отладка

### 5.1 Создание тестовых скриптов
```python
# tests/test_integration.py
import unittest
from unittest.mock import Mock, patch
from src.gitlab_client import GitLabClient
from src.glm_client import GLMClient

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.gitlab_client = GitLabClient()
        self.glm_client = GLMClient()
    
    @patch('src.gitlab_client.requests.get')
    def test_get_merge_request_diff(self, mock_get):
        # Мок ответа GitLab API
        mock_response = Mock()
        mock_response.json.return_value = [{'old_path': 'test.py', 'new_path': 'test.py', 'diff': '+print("hello")'}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        diff = self.gitlab_client.get_merge_request_diff()
        self.assertIn('print("hello")', diff)
    
    @patch('src.glm_client.requests.post')
    def test_analyze_code(self, mock_post):
        # Мок ответа GLM API
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '{"comments": [{"comment": "test", "severity": "low"}]}'}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.glm_client.analyze_code('test diff')
        self.assertIn('comments', result)
```

### 5.2 CI/CD для тестов
```yaml
# .gitlab-ci.yml (дополнение)
test:
  stage: test
  image: python:3.11
  before_script:
    - pip install -r requirements.txt
    - pip install pytest
  script:
    - pytest tests/ -v
  only:
    - merge_requests
```

## Фаза 6: Оптимизация и мониторинг

### 6.1 Оптимизация запросов к GLM
- Кэширование результатов для похожих изменений
- Использование более компактных промптов
- Опциональная асинхронная обработка

### 6.2 Мониторинг и аналитика
```python
# src/monitoring.py
import json
import os
from datetime import datetime

class ReviewMonitor:
    def log_review(self, mr_id: int, comments_count: int, processing_time: float):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'mr_id': mr_id,
            'comments_count': comments_count,
            'processing_time': processing_time
        }
        
        log_file = 'review_logs/analytics.json'
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
```

## Фаза 7: Расширенные возможности

### 7.1 Поддержка разных языков программирования
- Специфичные промпты для разных языков
- Определение языка по расширению файла

### 7.2 Игнорирование файлов и директорий
```python
# config/ignore_patterns.py
IGNORE_PATTERNS = [
    '*.min.js',
    '*.css.map',
    'node_modules/**',
    'vendor/**',
    '*.log'
]
```

### 7.3 Кастомизация правил ревью
- Возможность добавления собственных правил через конфигурационные файлы
- Поддержка project-specific настроек

## План внедрения

1. **Неделя 1**: Создание структуры проекта и базовых компонентов
2. **Неделя 2**: Реализация GitLab и GLM клиентов
3. **Неделя 3**: Создание основного скрипта и CI/CD интеграции
4. **Неделя 4**: Тестирование и отладка
5. **Неделя 5**: Оптимизация и добавление продвинутых функций

## Потенциальные проблемы и решения

### Проблема: Размер diff превышает лимиты GLM API
**Решение**: Реализовать интеллектуальное разбиение на чанки с сохранением контекста

### Проблема: Слишком много "шумных" комментариев
**Решение**: Добавить фильтрацию комментариев по релевантности и серьезности

### Проблема: Задержки в CI/CD пайплайне
**Решение**: 
- Опциональный асинхронный режим
- Ограничение времени анализа
- Кэширование результатов

### Проблема: Ошибки API
**Решение**: 
- Retry механизм с экспоненциальным backoff
- Graceful degradation при недоступности GLM
- Детальное логирование для отладки