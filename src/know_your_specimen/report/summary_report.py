from typing import Dict


def print_segmentation_stats(stats: dict) -> None:
    """Print statistics for a single processed image."""
    print(f"  зон талька найдено:               {stats['zones_count']}")
    print(f"  % талька от нерудной (силикатной) зоны: {stats['pct_talc_of_matrix']}%")
    print(f"  % талька от всего кадра:          {stats['pct_talc_of_full_image']}%")
    print(f"  % рудной фазы от всего кадра:     {stats['pct_ore_of_full_image']}%")
    print(f"  ПРЕДСКАЗАННЫЙ КЛАСС:              {stats['predicted_class']}")
    print(f"  предварительный вывод:            {stats['classification_hint']}")


def print_summary_report(class_counts: Dict[str, int], total_files: int, errors: int = 0) -> None:
    """
    Prints a summary report of processed files, including class distribution.

    Args:
        class_counts: Dictionary mapping predicted class names to their counts.
        total_files: Total number of files that were processed.
        errors: Number of files that failed to process.
    """
    processed = total_files - errors

    print("=" * 60)
    print("ИТОГОВАЯ СВОДКА")
    print("=" * 60)
    print(f"Всего обработано файлов: {processed} из {total_files}")
    if errors:
        print(f"Не удалось прочитать: {errors}")
    print()
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        pct = count / processed * 100 if processed > 0 else 0
        print(f"  {cls:20s}: {count:4d}  ({pct:.1f}%)")
    print("=" * 60)
