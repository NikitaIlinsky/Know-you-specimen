# Nornikel

"Know you specimen" — приложение анализа и классификации образцов руды.

## Установка

```bash
# Установка зависимостей
uv sync
```

## Запуск

### CLI — пакетная обработка

Обрабатывает все изображения из `IMAGE_INPUT_DIR` и сохраняет результаты в `OUTPUT_DIR`.

```bash
uv run know-your-specimen
```

### REST API сервер

Запускает HTTP-сервер для обработки одного изображения по REST-запросу.

```bash
uv run uvicorn know_your_specimen.server:app --host 0.0.0.0 --port 8000
```

Сервер поднимается на `http://localhost:8000`. Интерактивная документация (Swagger UI) доступна по адресу `http://localhost:8000/docs`.

### Docker

```bash
# Сборка образа
docker build -t know-your-specimen .

# Запуск контейнера
docker run -p 8000:8000 know-your-specimen
```

Сервер будет доступен на `http://localhost:8000`. Папку `output/` можно примонтировать в хост-систему:

```bash
docker run -p 8000:8000 -v $(pwd)/output:/app/output know-your-specimen
```

## Конфигурация (.env)

Скопируйте `.env.example` в `.env` и при необходимости измените значения:

```bash
cp .env.example .env
```

Настройки задаются через переменные окружения в файле `.env`:

| Переменная           | По умолчанию                  | Описание                          |
|----------------------|-------------------------------|-----------------------------------|
| `IMAGE_INPUT_DIR`    | `./input_images`              | Папка с входными изображениями    |
| `OUTPUT_DIR`         | `./output`                    | Папка для результатов             |
| `DEBUG_MODE`         | `False`                       | Включить отладочный вывод         |
| `ALLOWED_EXTENSIONS` | `.jpg,.jpeg,.png,.bmp,.tiff`  | Разрешённые расширения файлов     |
| `SENSITIVITY`        | `50`                          | Чувствительность детекции (0–100) |
| `BRIGHT_EXCLUDE`     | `100`                         | Порог яркости для рудной фазы     |
| `DENSITY_WINDOW`     | `17`                          | Размер окна плотности             |
| `MIN_AREA_RATIO`     | `0.0003`                      | Минимальная доля площади зоны     |

## REST API

| Endpoint | Method | Описание |
|---|---|---|
| `/health` | `GET` | Проверка работоспособности сервера |
| `/api/v1/analyze` | `POST` | Загрузка изображения, анализ, возврат результатов |
| `/api/v1/output/{filename}` | `GET` | Скачивание сгенерированного артефакта |

### POST /api/v1/analyze

Принимает изображение в формате `multipart/form-data` (поле `file`).
Возвращает JSON со статистикой анализа и URL-ами артефактов.

**Пример запроса:**

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@specimen.jpg"
```

**Пример ответа (200):**

```json
{
  "stats": {
    "zones_count": 5,
    "pct_talc_of_matrix": 12.4,
    "pct_talc_of_full_image": 3.1,
    "pct_ore_of_full_image": 25.0,
    "predicted_class": "rich",
    "classification_hint": "высокое содержание",
    "sensitivity": 50.0
  },
  "artifacts": {
    "annotated_image": "/api/v1/output/a1b2c3d4e5f6_talk.jpg",
    "mask_image": "/api/v1/output/a1b2c3d4e5f6_talk_mask.png",
    "stats_json": "/api/v1/output/a1b2c3d4e5f6_talk_stats.json"
  }
}
```

**Коды ответов:**

| Код | Описание |
|---|---|
| `200` | Изображение успешно обработано |
| `422` | Неверный запрос (отсутствует файл, неподдерживаемый формат, битое изображение) |
| `500` | Внутренняя ошибка обработки |

### GET /api/v1/output/{filename}

Скачивает артефакт, сгенерированный в результате анализа.
URL для скачивания берётся из поля `artifacts` ответа `POST /api/v1/analyze`.

```bash
curl -O http://localhost:8000/api/v1/output/a1b2c3d4e5f6_talk.jpg
```

## Testing

This project uses pytest for testing. To run the tests:

```bash
# Install test dependencies
uv sync --group test

# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v
```

## Project Structure

```
src/know_your_specimen/
├── main.py               CLI — пакетная обработка изображений
├── server.py             FastAPI — REST API сервер
├── config.py             Конфигурация (переменные окружения)
├── classification/       Классификация образцов руды
├── initialization/       Загрузка и подготовка изображений
├── report/               Отчёты и сводки
└── segmentation/         Сегментация и детекция талька
test/
├── test_main.py          Тесты CLI
└── test_server.py        Тесты REST API
pyproject.toml            Зависимости и конфигурация проекта
```
