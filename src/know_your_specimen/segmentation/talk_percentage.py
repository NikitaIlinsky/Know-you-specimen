"""
Собственный алгоритм детекции талька и расчёта его процентного содержания.

Логика (по описанию из ТЗ: тальк = "тёмные рассеянные области в
нерудных зонах"):

1. Исключаем рудную (светлую) фазу — тальк ищем только внутри
   силикатной матрицы.
2. Внутри матрицы считаем локальную ПЛОТНОСТЬ очень тёмных пикселей
   (это и есть "рассеянность" — не абсолютная яркость, а частота
   мелких тёмных вкраплений на единицу площади).
3. Небольшое морфологическое закрытие объединяет соседние вкрапления
   в компактные пятна, но НЕ склеивает всё в один сплошной блоб —
   тальк должен остаться "россыпью", а не монолитной зоной.
4. Считаем итоговый % площади талька — от всей матрицы (нерудной зоны)
   и от всего кадра.

Это не попытка повторить точную разметку организатора pixel-in-pixel —
это самостоятельная разметка для дальнейшего обучения модели.
"""

import json
import os

import cv2
import numpy as np


def detect_talc(
    img,
    very_dark_thresh=15,
    bright_exclude=100,
    density_window=17,
    density_thresh=0.15,
    close_kernel_size=5,
    min_area_ratio=0.0003,
):
    height, width = img.shape[:2]
    total_area = height * width
    min_area = total_area * min_area_ratio

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # рудная (светлая) фаза исключается из поиска талька
    ore_mask = gray >= bright_exclude
    matrix_mask = (~ore_mask).astype(np.uint8)
    matrix_area = matrix_mask.sum()

    # плотность очень тёмных пикселей — признак "рассеянности"
    very_dark = (gray < very_dark_thresh).astype(np.float32)
    density = cv2.boxFilter(very_dark, -1, (density_window, density_window))

    talc_candidate = (density > density_thresh).astype(np.uint8) * 255
    talc_candidate = cv2.bitwise_and(talc_candidate, talc_candidate, mask=matrix_mask)

    # умеренное закрытие — объединяет соседние вкрапления в пятна,
    # но не превращает всё в один сплошной массив
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (close_kernel_size, close_kernel_size)
    )
    closed = cv2.morphologyEx(talc_candidate, cv2.MORPH_CLOSE, close_kernel)
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, open_kernel)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    zones = [c for c in contours if cv2.contourArea(c) > min_area]

    final_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(final_mask, zones, -1, 255, thickness=cv2.FILLED)

    talc_area = (final_mask > 0).sum()
    pct_of_matrix = talc_area / matrix_area * 100 if matrix_area > 0 else 0
    pct_of_full_image = talc_area / total_area * 100

    stats = {
        "zones_count": len(zones),
        "talc_area_px": int(talc_area),
        "matrix_area_px": int(matrix_area),
        "ore_area_px": int(ore_mask.sum()),
        "pct_talc_of_matrix": round(pct_of_matrix, 2),
        "pct_talc_of_full_image": round(pct_of_full_image, 2),
        "pct_ore_of_full_image": round(ore_mask.sum() / total_area * 100, 2),
    }

    return zones, final_mask, stats


def make_hatch_pattern(shape, spacing=12, thickness=2):
    h, w = shape
    hatch = np.zeros((h, w), dtype=np.uint8)
    for offset in range(-h, w, spacing):
        cv2.line(hatch, (offset, 0), (offset + h, h), 255, thickness)
    return hatch


def render_output(img, mask, zones, stats, fill_alpha=0.4):
    output = img.copy()
    red = np.zeros_like(img)
    red[:, :] = (0, 0, 255)
    mask_bool = mask > 0
    output[mask_bool] = cv2.addWeighted(img, 1 - fill_alpha, red, fill_alpha, 0)[mask_bool]

    hatch_lines = make_hatch_pattern(mask.shape)
    hatch_in_zone = cv2.bitwise_and(hatch_lines, mask)
    output[hatch_in_zone > 0] = (0, 0, 220)

    cv2.drawContours(output, zones, -1, (0, 0, 255), 2)

    # подпись с итоговым процентом прямо на изображении
    label = f"Talc: {stats['pct_talc_of_matrix']}% of matrix | {stats['pct_talc_of_full_image']}% of frame"
    cv2.rectangle(output, (0, 0), (min(len(label) * 15 + 20, output.shape[1]), 45), (0, 0, 0), -1)
    cv2.putText(output, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return output


def process_file(input_path, output_dir):
    img = cv2.imread(input_path)
    if img is None:
        print(f"Не удалось прочитать: {input_path}")
        return None

    zones, mask, stats = detect_talc(img)
    output = render_output(img, mask, zones, stats)

    base = os.path.splitext(os.path.basename(input_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    result_path = os.path.join(output_dir, f"{base}_talc_red.jpg")
    mask_path = os.path.join(output_dir, f"{base}_talc_mask.png")
    stats_path = os.path.join(output_dir, f"{base}_stats.json")

    cv2.imwrite(result_path, output)
    cv2.imwrite(mask_path, mask)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"{base}:")
    print(f"  зон талька найдено: {stats['zones_count']}")
    print(f"  % талька от нерудной (силикатной) зоны: {stats['pct_talc_of_matrix']}%")
    print(f"  % талька от всего кадра: {stats['pct_talc_of_full_image']}%")
    print(f"  % рудной фазы от всего кадра: {stats['pct_ore_of_full_image']}%")
    print(f"  сохранено: {result_path}")

    return stats
