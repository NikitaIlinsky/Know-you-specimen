"""
Определяет цветовой режим фото шлифа (обычный цвет/сепия/градации серого/
жёсткий ЧБ) и подсказывает, какие параметры talc_percentage.py стоит
проверить для этого конкретного файла.

Зачем это нужно: ML-классификатор сорта руды (ore_classifier_model.pkl)
теперь обучен БЕЗ цветовых признаков (мы проверили - точность без них даже
выше, 84.6% против 82.5%), поэтому классификатор сорта руды одинаково
работает и на цветных, и на чёрно-белых снимках - отдельная подстройка ему
не нужна.

А вот сама детекция талька (detect_talc) и разделение руда/матрица
опираются на АБСОЛЮТНУЮ яркость пикселя (--bright-exclude, по умолчанию
100 из 255). Если у части датасета принципиально другая экспозиция/контраст
(например, пересвеченный скан, где почти всё выше 100), этот порог перестаёт
разделять руду и породу правильно - вот это уже нужно подстраивать вручную
под конкретную серию снимков.

Использование:
    python3 image_mode_detector.py снимок.jpg
    python3 image_mode_detector.py папка_со_снимками/

ВАЖНО: пороги ниже (что считать "сепией", что "ЧБ") подобраны по общим
соображениям, а не откалиброваны на реальных примерах сепии/ЧБ из твоего
датасета - я их пока не видел. Пришли несколько таких файлов - подстрою
пороги точнее.
"""

import os
import sys

import cv2
import numpy as np


def imread_unicode(path):
    try:
        data = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def detect_image_mode(img, safe_max_dim=1500):
    """
    Возвращает (режим, детали).
    Режимы: 'color', 'sepia', 'grayscale', 'bw_scan'
    """
    h0, w0 = img.shape[:2]
    scale = safe_max_dim / max(h0, w0)
    if scale < 1:
        # Это чистая статистика по цвету/яркости - даунскейл не портит
        # результат, а без него на панорамах в сотни мегапикселей
        # анализ падал по памяти (несколько полноразмерных float-каналов).
        img = cv2.resize(img, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h_ch, s_ch, v_ch = cv2.split(hsv)
    b, g, r = cv2.split(img.astype(np.float32))

    sat_mean = float(s_ch.mean())
    # разброс между каналами R/G/B - у настоящего чёрно-белого R=G=B везде
    channel_spread = float(np.mean(np.abs(r - g)) + np.mean(np.abs(g - b)) + np.mean(np.abs(r - b)))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    unique_vals = len(np.unique(gray))
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist_norm = hist / hist.sum()
    # доля пикселей в крайних 10 уровнях (около 0 и около 255) - признак жёсткого ЧБ/бинаризованного скана
    extreme_frac = float(hist_norm[:10].sum() + hist_norm[-10:].sum())

    hue_vals = h_ch[s_ch > 20]  # оттенок там, где вообще есть насыщенность
    dominant_hue = float(np.median(hue_vals)) if len(hue_vals) > 100 else None

    details = {
        "sat_mean": round(sat_mean, 1),
        "channel_spread": round(channel_spread, 1),
        "unique_gray_levels": unique_vals,
        "extreme_pixel_frac": round(extreme_frac * 100, 1),
        "dominant_hue": round(dominant_hue, 1) if dominant_hue is not None else None,
    }

    if channel_spread < 2.0 and sat_mean < 8:
        if extreme_frac > 0.5 and unique_vals < 40:
            mode = "bw_scan"
        else:
            mode = "grayscale"
    elif sat_mean < 90 and dominant_hue is not None and 8 <= dominant_hue <= 30:
        mode = "sepia"
    else:
        mode = "color"

    return mode, details


def suggest_params(mode, details):
    notes = []
    if mode == "color":
        notes.append(
            "обычный цветной снимок (как основной датасет) - параметры по умолчанию должны подойти."
        )
    elif mode == "sepia":
        notes.append(
            "сепия - цветовых признаков классификатор не использует, но проверь --bright-exclude "
            "и --sensitivity на паре тестовых файлов: сепия-тонирование может сдвигать общую яркость."
        )
    elif mode == "grayscale":
        notes.append(
            "градации серого без цветового сдвига - должно работать так же, как цвет, "
            "т.к. вся детекция и так идёт по яркости. Цветовые признаки классификатора здесь "
            "автоматически неинформативны, но модель их и не использует."
        )
    elif mode == "bw_scan":
        notes.append(
            "похоже на жёсткий чёрно-белый/бинаризованный скан (мало уникальных уровней "
            f"яркости: {details['unique_gray_levels']}, {details['extreme_pixel_frac']}% пикселей "
            "в крайних значениях). ЭТО РИСКОВАННЫЙ СЛУЧАЙ: детекция талька по адаптивному "
            "процентилю яркости может вести себя непредсказуемо, если в кадре всего 2-3 "
            "уровня серого. Рекомендую явно проверить --debug на 2-3 таких файлах и, "
            "возможно, --bright-exclude вручную."
        )
    return notes


def main():
    if len(sys.argv) < 2:
        print("Использование: python3 image_mode_detector.py файл.jpg  ИЛИ  папка/")
        return
    target = sys.argv[1]

    if os.path.isdir(target):
        files = []
        for root, _, filenames in os.walk(target):
            for fn in filenames:
                if fn.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff")):
                    files.append(os.path.join(root, fn))
    else:
        files = [target]

    print(f"Проверяю {len(files)} файл(ов)...\n")
    mode_counts = {}
    for f in sorted(files):
        img = imread_unicode(f)
        if img is None:
            print(f"[!] Не удалось прочитать: {f}")
            continue
        mode, details = detect_image_mode(img)
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        print(f"--- {f} ---")
        print(f"  режим: {mode}")
        print(
            f"  детали: sat_mean={details['sat_mean']}  channel_spread={details['channel_spread']}  "
            f"уникальных_уровней_серого={details['unique_gray_levels']}  "
            f"доля_в_крайних_значениях={details['extreme_pixel_frac']}%  "
            f"доминирующий_оттенок={details['dominant_hue']}"
        )
        for note in suggest_params(mode, details):
            print(f"  -> {note}")
        print()

    if len(files) > 1:
        print("=" * 50)
        print("СВОДКА ПО РЕЖИМАМ:")
        for mode, count in sorted(mode_counts.items(), key=lambda x: -x[1]):
            print(f"  {mode:12s}: {count}")
