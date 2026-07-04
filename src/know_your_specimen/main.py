from src.know_your_specimen.config import config
from src.know_your_specimen.initialization.initialization import get_image_paths
from src.know_your_specimen.report.summary_report import (
    print_segmentation_stats,
    print_summary_report,
)
from src.know_your_specimen.segmentation.talk_percentage import process_file


def main():
    images = get_image_paths(config.image_input_dir, config.allowed_extensions)
    if not images:
        return

    print(f"Найдено {len(images)} изображений. Обрабатываю...\n")

    class_counts, errors = _process_images(images)
    print_summary_report(class_counts, len(images), errors)


def _process_images(images: list[str]) -> tuple[dict[str, int], int]:
    """Process all images and return class counts and error count."""
    class_counts: dict[str, int] = {}
    errors = 0
    for image_path in images:
        print(f"--- {image_path} ---")
        stats = process_file(image_path, config.output_dir, config)
        if stats is None:
            errors += 1
        else:
            print_segmentation_stats(stats)
            print(f"  сохранено: {config.output_dir}")
            print()
            cls = stats["predicted_class"]
            class_counts[cls] = class_counts.get(cls, 0) + 1
    return class_counts, errors


if __name__ == "__main__":
    main()
