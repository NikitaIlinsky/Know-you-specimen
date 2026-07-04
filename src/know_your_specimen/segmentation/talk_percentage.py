import json
import os

import cv2
import numpy as np

from ..classification.ore_classificatior import classify_ore


def imread_unicode(path):
    try:
        data = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"  [debug] Ошибка чтения через imdecode: {e}")
        return None


def imwrite_unicode(path, img, ext=".jpg"):
    try:
        ok, buf = cv2.imencode(ext, img)
        if not ok:
            return False
        buf.tofile(path)
        return True
    except Exception as e:
        print(f"  [debug] Ошибка записи через tofile: {e}")
        return False


def sensitivity_to_params(sensitivity):
    """
    Переводит одну ручку 'чувствительность' (0-100) в три внутренних
    параметра алгоритма. sensitivity=50 - нейтральное значение,
    подобранное перебором по трём эталонным снимкам с разметкой эксперта.

    Чем ВЫШЕ sensitivity, тем БОЛЬШЕ area будет размечено как тальк:
      - dark_percentile растёт -> порог "тёмного" пикселя выше
        -> больше пикселей считаются тёмными
      - density_thresh падает -> легче набрать нужную плотность
        тёмных точек в окне
      - close_kernel растёт -> отдельные вкрапления сильнее
        "слипаются" в широкие пятна (примерно то, что эксперт
        подразумевает под "обширное пятно с чёрными зёрнами",
        а не точечные вкрапления)

    Чем НИЖЕ sensitivity, тем строже алгоритм и тем меньше/мельче зоны.
    """
    s = max(0, min(100, sensitivity))
    t = (s - 50) / 50.0  # от -1.0 до +1.0

    dark_percentile = 12 + t * 8  # диапазон 4..20
    density_thresh = 0.10 - t * 0.05  # диапазон 0.05..0.15
    close_kernel_size = int(round(9 + t * 8))  # диапазон 1..17
    close_kernel_size = max(3, close_kernel_size)
    if close_kernel_size % 2 == 0:
        close_kernel_size += 1

    return dark_percentile, density_thresh, close_kernel_size


def compute_std_contrast(gray_no_bg):
    """
    Признак для рядовой руды: бимодальность/контраст (межклассовая
    дисперсия Отсу). Крупные чистые "материки" руды на тёмном фоне
    дают высокое значение; смазанный, невнятный контраст - низкое.
    """
    valid = gray_no_bg.astype(np.uint8)
    if len(valid) < 10:
        return 0.0
    otsu_thresh, _ = cv2.threshold(valid, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark_side = valid[valid < otsu_thresh]
    bright_side = valid[valid >= otsu_thresh]
    if len(dark_side) == 0 or len(bright_side) == 0:
        return 0.0
    w0, w1 = len(dark_side) / len(valid), len(bright_side) / len(valid)
    return float(np.sqrt(w0 * w1 * (dark_side.mean() - bright_side.mean()) ** 2))


def compute_median_ore_grain_area(ore_mask):
    """
    Признак: медианный размер связной компоненты рудной фазы.
    """
    ore_u8 = ore_mask.astype(np.uint8) * 255
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(ore_u8, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    areas = areas[areas > 5]
    return float(np.median(areas)) if len(areas) > 0 else 0.0


def compute_grain_density_in_ore(gray_raw_u8, ore_mask):
    """
    Признак: плотность мелких границ (Canny) именно ВНУТРИ рудной фазы.
    Труднообогатимая руда - рудные зёрна изъедены, рассыпаны на мелкие
    осколки, поэтому границ внутри руды много. Рядовая - крупные цельные
    зёрна с редкими границами внутри.
    """
    edges = cv2.Canny(gray_raw_u8, 50, 150)
    edges_in_ore = edges[ore_mask] if ore_mask.sum() > 0 else np.array([0])
    return float(edges_in_ore.mean() / 255.0 * 100) if len(edges_in_ore) > 0 else 0.0


def detect_background(gray, dark_thresh=40, texture_thresh=3, window=15):
    """
    Находит области, которые похожи не на тёмную матрицу породы, а на
    ФОН - место за пределами шлифа или сильно расфокусированный край.
    Отличие от реальной тёмной матрицы: фон одновременно ОЧЕНЬ тёмный
    И текстурно ПЛОСКИЙ (нет зерна породы). На одном из тестовых
    снимков такой фон занимал ~8% кадра и алгоритм принимал его за
    тальк, потому что плоский чёрный участок тривиально проходит
    любой порог "очень тёмного" пикселя.
    """
    mean = cv2.boxFilter(gray, -1, (window, window))
    sq = cv2.boxFilter(gray * gray, -1, (window, window))
    local_std = np.sqrt(np.maximum(sq - mean * mean, 0))
    background = (gray < dark_thresh) & (local_std < texture_thresh)
    return background.astype(np.uint8)


def correct_vignette(gray, vignette_sigma_ratio=6):
    """
    Убирает естественное затемнение по краям кадра (виньетирование
    оптики микроскопа). Без этой коррекции алгоритм принимает тёмные
    углы кадра за скопления талька, хотя это чисто оптический эффект -
    яркость на краю кадра падает более чем вдвое относительно центра
    просто из-за объектива, что подтвердилось на всех тестовых снимках.

    Метод: оцениваем фоновую освещённость сильным гауссовым размытием
    (низкие частоты) и делим исходное изображение на неё.
    """
    h, w = gray.shape
    illum = cv2.GaussianBlur(gray, (0, 0), sigmaX=min(h, w) / vignette_sigma_ratio)
    corrected = gray / (illum + 1e-3) * np.mean(illum)
    return np.clip(corrected, 0, 255)


def detect_talc(
    img,
    sensitivity=50,
    bright_exclude=100,
    density_window=17,
    min_area_ratio=0.0003,
    debug=False,
    debug_prefix=None,
    debug_dir=None,
):
    height, width = img.shape[:2]
    total_area = height * width
    min_area = total_area * min_area_ratio

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    corrected = correct_vignette(gray)
    background_mask = detect_background(gray)

    dark_percentile, density_thresh, close_kernel_size = sensitivity_to_params(sensitivity)

    ore_mask_raw = (corrected >= bright_exclude).astype(np.uint8) * 255
    # Заращиваем внутренние тёмные вкрапления/трещины ВНУТРИ рудного зерна
    # (это структурная текстура самого минерала - сколы, микротрещины,
    # неоднородности), а не силикатная матрица. Без этого шага такие
    # внутренние тёмные точки ошибочно засчитывались в поиск талька,
    # хотя физически находятся внутри светлого зерна, а не в породе.
    ore_close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    ore_mask_closed = cv2.morphologyEx(ore_mask_raw, cv2.MORPH_CLOSE, ore_close_kernel)
    ore_mask = ore_mask_closed > 0
    matrix_mask = (~ore_mask) & (background_mask == 0)
    matrix_mask = matrix_mask.astype(np.uint8)
    matrix_area = matrix_mask.sum()
    background_area = int(background_mask.sum())

    matrix_pixels = corrected[matrix_mask > 0]
    if len(matrix_pixels) > 0:
        very_dark_thresh = float(np.percentile(matrix_pixels, dark_percentile))
    else:
        very_dark_thresh = 15.0

    very_dark = (corrected < very_dark_thresh).astype(np.float32)
    density = cv2.boxFilter(very_dark, -1, (density_window, density_window))

    talc_candidate = (density > density_thresh).astype(np.uint8) * 255
    talc_candidate = cv2.bitwise_and(talc_candidate, talc_candidate, mask=matrix_mask)

    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (close_kernel_size, close_kernel_size)
    )
    closed = cv2.morphologyEx(talc_candidate, cv2.MORPH_CLOSE, close_kernel)
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, open_kernel)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    all_contour_count = len(contours)
    zones = [c for c in contours if cv2.contourArea(c) > min_area]

    final_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(final_mask, zones, -1, 255, thickness=cv2.FILLED)

    talc_area = (final_mask > 0).sum()
    pct_of_matrix = talc_area / matrix_area * 100 if matrix_area > 0 else 0
    pct_of_full_image = talc_area / total_area * 100

    ore_pct_of_full = (
        ore_mask.sum() / total_area * 100
    )  # для порога "мало руды" и отчёта - заращённая маска
    ore_pct_of_full_raw = (
        (ore_mask_raw > 0).sum() / total_area * 100
    )  # для классификатора - как при обучении

    # --- Классификатор сорта руды (обучен на 30 примерах, см. классы выше) ---
    # ВАЖНО: классификатор обучен на ПРОСТОЙ (незаращённой) маске руды -
    # используем именно её здесь, чтобы не сдвигать признаки относительно
    # обученных центроидов. Заращённая маска (ore_mask) используется только
    # для расчёта % талька, но не для классификатора.
    ore_mask_for_classifier = ore_mask_raw > 0
    gray_no_bg = corrected[background_mask == 0]
    std_contrast = compute_std_contrast(gray_no_bg)
    median_ore_grain_area = compute_median_ore_grain_area(ore_mask_for_classifier)
    grain_density_in_ore = compute_grain_density_in_ore(
        gray.astype(np.uint8), ore_mask_for_classifier
    )
    material_stats = {
        "ore_pct": ore_pct_of_full_raw,
        "std_contrast": std_contrast,
        "grain_density_in_ore": grain_density_in_ore,
        "median_ore_grain_area": median_ore_grain_area,
        "ore_pct_of_full": ore_pct_of_full,
    }
    predicted_class, class_distances, classification_hint = classify_ore(material_stats)

    stats = {
        "zones_count": len(zones),
        "zones_before_area_filter": all_contour_count,
        "sensitivity": sensitivity,
        "adaptive_very_dark_thresh": round(very_dark_thresh, 1),
        "dark_percentile_used": round(dark_percentile, 1),
        "density_thresh_used": round(density_thresh, 3),
        "close_kernel_used": close_kernel_size,
        "talc_area_px": int(talc_area),
        "matrix_area_px": int(matrix_area),
        "ore_area_px": int(ore_mask.sum()),
        "background_area_px": background_area,
        "background_pct_of_full_image": round(background_area / total_area * 100, 2),
        "pct_talc_of_matrix": round(pct_of_matrix, 2),
        "pct_talc_of_full_image": round(pct_of_full_image, 2),
        "pct_ore_of_full_image": round(ore_pct_of_full, 2),
        "std_contrast": round(std_contrast, 2),
        "median_ore_grain_area": round(median_ore_grain_area, 1),
        "predicted_class": predicted_class,
        "class_distances": {k: round(v, 3) for k, v in class_distances.items()},
        "classification_hint": classification_hint,
    }

    if debug:
        print(f"  [debug] Размер кадра: {width}x{height} = {total_area} px")
        print(
            f"  [debug] Чувствительность={sensitivity} -> dark_percentile={dark_percentile:.1f}, "
            f"density_thresh={density_thresh:.3f}, close_kernel={close_kernel_size}"
        )
        print(
            f"  [debug] Рудная (светлая) фаза: {ore_mask.sum()} px ({ore_mask.sum() / total_area * 100:.1f}%)"
        )
        print(
            f"  [debug] Нерудная (матричная) зона: {matrix_area} px ({matrix_area / total_area * 100:.1f}%)"
        )
        print(
            f"  [debug] Адаптивный порог 'очень тёмного' (после коррекции виньетирования): {very_dark_thresh:.1f}"
        )
        print(
            f"  [debug] Пикселей темнее порога: {int(very_dark.sum())} ({very_dark.sum() / total_area * 100:.2f}%)"
        )
        print(
            f"  [debug] Пикселей выше порога плотности ДО морфологии: {int((talc_candidate > 0).sum())}"
        )
        print(f"  [debug] Контуров ДО фильтра по площади: {all_contour_count}, ПОСЛЕ: {len(zones)}")

        if debug_dir and debug_prefix:
            os.makedirs(debug_dir, exist_ok=True)
            imwrite_unicode(
                os.path.join(debug_dir, f"{debug_prefix}_debug_corrected.png"),
                corrected.astype(np.uint8),
                ".png",
            )
            density_vis = np.clip(density * 255, 0, 255).astype(np.uint8)
            imwrite_unicode(
                os.path.join(debug_dir, f"{debug_prefix}_debug_density.png"), density_vis, ".png"
            )
            imwrite_unicode(
                os.path.join(debug_dir, f"{debug_prefix}_debug_candidate.png"),
                talc_candidate,
                ".png",
            )
            print(f"  [debug] Сохранены отладочные изображения в {debug_dir}/")

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

    label = f"Talc: {stats['pct_talc_of_matrix']}% of matrix | {stats['pct_talc_of_full_image']}% of frame | sens={stats['sensitivity']}"
    cv2.rectangle(output, (0, 0), (min(len(label) * 12 + 20, output.shape[1]), 45), (0, 0, 0), -1)
    cv2.putText(output, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return output


def process_file(input_path, config):
    output_dir = config.output_dir
    img = imread_unicode(input_path)
    if img is None:
        print(f"[!] Не удалось прочитать: {input_path}")
        print(
            "    Проверь: 1) файл существует, 2) это не битый/пустой файл, "
            "3) путь верный (скопируй его из проводника заново)."
        )
        return None

    base = os.path.splitext(os.path.basename(input_path))[0]
    debug_dir = os.path.join(output_dir, "debug") if config.debug_mode else None

    zones, mask, stats = detect_talc(
        img,
        debug=config.debug_mode,
        debug_prefix=base,
        debug_dir=debug_dir,
        sensitivity=config.sensitivity,
        bright_exclude=config.bright_exclude,
        density_window=config.density_window,
        min_area_ratio=config.min_area_ratio,
    )
    output = render_output(img, mask, zones, stats)

    os.makedirs(output_dir, exist_ok=True)

    result_path = os.path.join(output_dir, f"{base}_talk.jpg")
    mask_path = os.path.join(output_dir, f"{base}_talk_mask.png")
    stats_path = os.path.join(output_dir, f"{base}_talk_stats.json")

    imwrite_unicode(result_path, output, ".jpg")
    imwrite_unicode(mask_path, mask, ".png")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"  сохранено: {result_path}")
    print()

    return stats
