# Скажи мне, кто твой шлиф

По одному панорамному снимку полированного шлифа система определяет:
1. Долю талька — тёмной рассеянной фазы в нерудной (силикатной) матрице, в процентах от матрицы и от всего кадра.
2. Степень замещения сульфидных срастаний — «обычные» (крупные, слабо замещённые нерудной фазой) или «тонкие» (значительно замещённые серой/тёмной фазой).
3. Итоговый технологический сорт руды — один из трёх классов: рядовая — минимальное замещение, преобладают обычные срастания, тальк ≤10%; труднообогатимая — значительное замещение, преобладают тонкие срастания; оталькованная — доля талька превышает 10% (маркер, требующийотдельного технологического режима обогащения).
Результат выдаётся как количественные метрики (% талька, % по типам срастаний), цветовая маска поверх снимка (зелёный/красный/синий) и человекочитаемое заключение — то есть замена ручной экспертной оценки на объективный, быстрый и воспроизводимый автоматический анализ.

Презентация: https://disk.yandex.ru/d/mjRyM9cXGkGV9w
Видео: https://disk.yandex.ru/d/6GR8pjDrl8qJxg


"Know you specimen" — приложение анализа и классификации образцов руды.

## Требования

- **Python** 3.14 или выше
- **uv** — менеджер пакетов ([установка](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js + npm** — для сборки веб-интерфейса ([установка](https://nodejs.org/))
- **Docker** (опционально, для контейнеризации)

## Установка

```bash
# Установка зависимостей
uv sync
```

## Запуск

### CLI — пакетная обработка

Обрабатывает все изображения из `IMAGE_INPUT_DIR` и сохраняет результаты в `OUTPUT_DIR`.

Перед запуском создайте папки `./input_images` и `./output` (или укажите свои пути в `.env`):

```bash
mkdir -p input_images output
```

```bash
uv run know-your-specimen
```

### Веб-интерфейс

Веб-приложение, доступное по корневому адресу `/` (`http://localhost:8000`).
Собирается из исходников Vue в статику и раздаётся Python-сервером.

```bash
cd frontend
npm install
npm run build
```

После сборки запустите REST API сервер — он автоматически подхватит `frontend/dist/` и начнёт отдавать SPA по корневому пути.

```bash
uv run uvicorn know_your_specimen.server:app --host 0.0.0.0 --port 8000
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

## Тестовые данные

Примеры снимков шлифов и минералов для тестирования доступны на Яндекс.Диске:

[Образцы руды и минералов](https://disk.yandex.ru/d/Fo5eIM984glHaA)

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
frontend/                 Веб-интерфейс (Vite + Vue)
pyproject.toml            Зависимости и конфигурация проекта
pytest.ini                Настройки pytest
uv.lock                   Зафиксированные версии зависимостей
.env                      Переменные окружения
Dockerfile                Сборка Docker-образа
.dockerignore             Исключения для Docker-контекста
```
