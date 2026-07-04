# Nornikel

"Know you specimen" — приложение анализа и классификации образцов руды.

## Установка и запуск

```bash
# Установка зависимостей
uv sync

# Запуск обработки изображений
uv run python src/know_your_specimen/main.py
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

- `src/` - Source code files
- `test/` - Test files
- `pyproject.toml` - Project configuration and dependencies
