from know_your_specimen.config import config
from know_your_specimen.initialization.initialization import get_image_paths
from know_your_specimen.report.summary_report import print_summary_report
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

    print_summary_report(class_counts, len(images), errors)


if __name__ == "__main__":
    main()
