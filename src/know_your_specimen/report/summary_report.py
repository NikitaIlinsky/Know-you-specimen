from typing import Dict


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
