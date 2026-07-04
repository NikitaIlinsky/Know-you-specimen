from know_your_specimen.config import config
from know_your_specimen.initialization.initialization import get_image_paths
from know_your_specimen.segmentation.talk_percentage import process_file


def main():
    images = get_image_paths(config.image_input_dir, config.allowed_extensions)

    if not images:
        print(f"[!] В папке {config.image_input_dir} не найдено изображений")
        return

    print(f"Найдено {len(images)} изображений. Обрабатываю...\n")

    class_counts = {}
    errors = 0
    for image_path in images:
        stats = process_file(image_path, config.output_dir, config)
        if stats is None:
            errors += 1
        else:
            cls = stats["predicted_class"]
            class_counts[cls] = class_counts.get(cls, 0) + 1

    print("=" * 60)
    print("ИТОГОВАЯ СВОДКА")
    print("=" * 60)
    print(f"Всего обработано файлов: {len(images) - errors} из {len(images)}")
    if errors:
        print(f"Не удалось прочитать: {errors}")
    print()
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        pct = count / (len(images) - errors) * 100 if (len(images) - errors) > 0 else 0
        print(f"  {cls:20s}: {count:4d}  ({pct:.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
