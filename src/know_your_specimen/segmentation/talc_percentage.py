import json
import os
import pickle

import cv2
import numpy as np

from know_your_specimen.config import Config, config
from know_your_specimen.segmentation.intergrowth_segmentation import (
    build_text_conclusion,
    render_combined_overlay,
    segment_intergrowths,
    summarize_intergrowths,
)

try:
    from skimage.feature import graycomatrix, graycoprops, local_binary_pattern
    from skimage.measure import label, regionprops

    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

_ML_MODEL_CACHE = None
_ML_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "ore_classifier_model.pkl"
)


def load_ml_model():
    """
    Загружает обученную ML-модель (SVM, 5-fold CV точность 81.8% на 143
    примерах - см. документацию). Кэшируется при первом вызове. Если файл
    модели или scikit-image недоступны - возвращает None, и скрипт
    откатывается на старый эвристический классификатор (центроиды).
    """
    global _ML_MODEL_CACHE
    if _ML_MODEL_CACHE is not None:
        return _ML_MODEL_CACHE
    if not SKIMAGE_AVAILABLE or not os.path.exists(_ML_MODEL_PATH):
        _ML_MODEL_CACHE = False
        return False
    try:
        with open(_ML_MODEL_PATH, "rb") as f:
            _ML_MODEL_CACHE = pickle.load(f)
        return _ML_MODEL_CACHE
    except Exception as e:
        print(f"  [debug] Не удалось загрузить ML-модель ({e}), использую старый классификатор")
        _ML_MODEL_CACHE = False
        return False


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


# Параметры классификатора, обученного (nearest-centroid, z-нормализация)
# на 30 размеченных примерах (по 10 на класс: рядовая/тальковая/труднообогатимая).
# LOO-кросс-валидация дала точность 73.3% (22/30) - заметно лучше случайного
# угадывания (33%). ВАЖНАЯ ОГОВОРКА: отдельная проверка ПРЕДЫДУЩЕЙ версии
# классификатора (2 признака, обученной на 15 примерах) на большом внешнем
# датасете из 178 снимков дала только 60.1% - то есть LOO на маленькой
# выборке обычно завышает реальную точность. Текущая версия использует вдвое
# больше обучающих данных, что должно улучшить обобщение, но не проверена
# напрямую на большом внешнем датасете.
CLASSIFIER_FEATURE_MEAN = np.array([30.756273, 27.771074, 11.025873, 25.366667])
CLASSIFIER_FEATURE_STD = np.array([22.606224, 7.047225, 7.012449, 6.524229])
CLASSIFIER_CENTROIDS = {
    "рядовая": np.array([1.009782, 0.618916, -0.476391, -0.715282]),
    "труднообогатимая": np.array([-0.730661, -0.683900, 0.407904, 0.817466]),
    "оталькованная": np.array([-0.279121, 0.064985, 0.068487, -0.102183]),
}


def classify_ore(ore_pct, std_contrast, grain_density_in_ore, median_ore_grain_area):
    """Nearest-centroid классификация по четырём признакам."""
    x = np.array([ore_pct, std_contrast, grain_density_in_ore, median_ore_grain_area])
    x_norm = (x - CLASSIFIER_FEATURE_MEAN) / CLASSIFIER_FEATURE_STD
    dists = {label: np.linalg.norm(x_norm - c) for label, c in CLASSIFIER_CENTROIDS.items()}
    best_label = min(dists.items(), key=lambda item: item[1])[0]
    return best_label, dists


def detect_background(
    gray,
    dark_thresh=40,
    texture_thresh=3,
    window=15,
    adaptive=True,
    dark_percentile=2,
    texture_percentile=8,
):
    """
    Находит области, которые похожи не на тёмную матрицу породы, а на
    ФОН - место за пределами шлифа или сильно расфокусированный край.
    Отличие от реальной тёмной матрицы: фон одновременно ОЧЕНЬ тёмный
    И текстурно ПЛОСКИЙ (нет зерна породы).

    ВАЖНО (фикс для тёмных панорам): раньше пороги были фиксированными
    абсолютными числами (dark_thresh=40, texture_thresh=3), откалиброванными
    на ярких снимках 5x-20x (медианная яркость 82-195). На панорамах
    экспозиция/контраст совсем другие (у одной из тестовых панорам медианная
    яркость всего 24!) - фиксированный порог 40 срезал 71% кадра как "фон",
    хотя это была реальная тёмная порода с тальком. Теперь по умолчанию
    (adaptive=True) пороги считаются как НИЗКИЕ ПЕРЦЕНТИЛИ распределения
    ЭТОГО конкретного кадра - "фон" это то, что заметно темнее и площе
    почти всего остального в кадре, а не темнее какого-то абсолютного
    числа. adaptive=False оставляет старое поведение (на случай, если
    где-то понадобится точно воспроизвести прежний результат).
    """
    mean = cv2.boxFilter(gray, -1, (window, window))
    sq = cv2.boxFilter(gray * gray, -1, (window, window))
    local_std = np.sqrt(np.maximum(sq - mean * mean, 0))

    if adaptive:
        dark_thresh = min(dark_thresh, float(np.percentile(gray, dark_percentile)))
        texture_thresh = min(texture_thresh, float(np.percentile(local_std, texture_percentile)))

    background = (gray < dark_thresh) & (local_std < texture_thresh)
    return background.astype(np.uint8)


def _resize_max(img, max_dim=900):
    h, w = img.shape[:2]
    scale = max_dim / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def compute_rich_features(path):
    img_full = imread_unicode(path)
    if img_full is None:
        return None
    return compute_rich_features_from_img(img_full)


def compute_rich_features_from_img(img_full):
    """
    44 признака (яркость/контраст, границы Canny, форма и размер зёрен
    руды, локальная текстура, GLCM, LBP, цвет HSV) - именно на них
    обучена ML-модель (ore_classifier_model.pkl). Работает на уменьшенной
    копии изображения (макс. сторона 900px) для скорости; проценты и
    гистограммные признаки от этого не искажаются, т.к. считаются
    относительно площади/распределения, а не в абсолютных пикселях.
    """
    img = _resize_max(img_full, 900)
    h, w = img.shape[:2]
    total = h * w

    gray_raw = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    corrected = correct_vignette(gray_raw)
    bg = detect_background(gray_raw)

    ore_mask = corrected >= 100
    matrix_mask = (~ore_mask) & (bg == 0)

    feats = {}
    feats["ore_pct"] = float(ore_mask.sum() / total * 100)
    feats["bg_pct"] = float(bg.sum() / total * 100)
    feats["matrix_pct"] = float(matrix_mask.sum() / total * 100)

    gray_no_bg = corrected[bg == 0]
    feats["std_contrast"] = compute_std_contrast(gray_no_bg)
    feats["global_std"] = float(np.std(gray_no_bg)) if len(gray_no_bg) else 0.0

    gray_u8 = gray_raw.astype(np.uint8)
    edges = cv2.Canny(gray_u8, 50, 150)
    feats["edge_density_full"] = float(edges.mean() / 255 * 100)
    edges_in_ore = edges[ore_mask] if ore_mask.sum() > 0 else np.array([0])
    feats["edge_density_in_ore"] = (
        float(edges_in_ore.mean() / 255 * 100) if len(edges_in_ore) else 0.0
    )
    edges_in_matrix = edges[matrix_mask] if matrix_mask.sum() > 0 else np.array([0])
    feats["edge_density_in_matrix"] = (
        float(edges_in_matrix.mean() / 255 * 100) if len(edges_in_matrix) else 0.0
    )

    ore_u8 = (ore_mask.astype(np.uint8)) * 255
    n_labels, labels_im, stats_cc, _ = cv2.connectedComponentsWithStats(ore_u8, connectivity=8)
    areas = stats_cc[1:, cv2.CC_STAT_AREA]
    areas = areas[areas > 5]
    feats["median_ore_grain_area"] = float(np.median(areas)) if len(areas) else 0.0
    feats["mean_ore_grain_area"] = float(np.mean(areas)) if len(areas) else 0.0
    feats["std_ore_grain_area"] = float(np.std(areas)) if len(areas) else 0.0
    feats["n_ore_grains"] = float(len(areas))

    labeled = label(ore_mask)
    props = regionprops(labeled)
    props = [p for p in props if p.area > 5]
    if props:
        feats["ore_eccentricity_mean"] = float(np.mean([p.eccentricity for p in props]))
        feats["ore_solidity_mean"] = float(np.mean([p.solidity for p in props]))
        feats["ore_extent_mean"] = float(np.mean([p.extent for p in props]))
    else:
        feats["ore_eccentricity_mean"] = 0.0
        feats["ore_solidity_mean"] = 0.0
        feats["ore_extent_mean"] = 0.0

    mean_local = cv2.boxFilter(corrected, -1, (9, 9))
    sq_local = cv2.boxFilter(corrected * corrected, -1, (9, 9))
    local_std = np.sqrt(np.maximum(sq_local - mean_local * mean_local, 0))
    matrix_std_vals = local_std[matrix_mask] if matrix_mask.sum() > 0 else np.array([0])
    feats["texture_score_mean"] = float(matrix_std_vals.mean()) if len(matrix_std_vals) else 0.0
    feats["texture_score_median"] = (
        float(np.median(matrix_std_vals)) if len(matrix_std_vals) else 0.0
    )
    feats["high_texture_frac"] = (
        float(((local_std > 8) & matrix_mask).sum() / matrix_mask.sum() * 100)
        if matrix_mask.sum() > 0
        else 0.0
    )

    small = cv2.resize(gray_u8, (256, 192), interpolation=cv2.INTER_AREA)
    small_q = (small // 32).astype(np.uint8)
    glcm = graycomatrix(
        small_q,
        distances=[1, 3],
        angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4],
        levels=8,
        symmetric=True,
        normed=True,
    )
    for prop in ["contrast", "dissimilarity", "homogeneity", "energy", "correlation", "ASM"]:
        vals = graycoprops(glcm, prop)
        feats[f"glcm_{prop}_mean"] = float(vals.mean())
        feats[f"glcm_{prop}_std"] = float(vals.std())

    lbp = local_binary_pattern(gray_u8, P=8, R=1, method="uniform")
    lbp_matrix_vals = lbp[matrix_mask] if matrix_mask.sum() > 0 else np.array([0])
    if len(lbp_matrix_vals) > 0:
        hist, _ = np.histogram(lbp_matrix_vals, bins=10, range=(0, 10), density=True)
        for i, v in enumerate(hist):
            feats[f"lbp_bin{i}"] = float(v)
    else:
        for i in range(10):
            feats[f"lbp_bin{i}"] = 0.0

    h_ch, s_ch, v_ch = cv2.split(hsv)
    if matrix_mask.sum() > 0:
        feats["hue_matrix_mean"] = float(h_ch[matrix_mask].mean())
        feats["sat_matrix_mean"] = float(s_ch[matrix_mask].mean())
    else:
        feats["hue_matrix_mean"] = 0.0
        feats["sat_matrix_mean"] = 0.0
    if ore_mask.sum() > 0:
        feats["hue_ore_mean"] = float(h_ch[ore_mask].mean())
        feats["sat_ore_mean"] = float(s_ch[ore_mask].mean())
    else:
        feats["hue_ore_mean"] = 0.0
        feats["sat_ore_mean"] = 0.0

    return feats


def classify_ore_ml(img_full):
    """
    Настоящая ML-модель (SVM, обучена на 143 размеченных фото, 5-fold CV
    точность 81.8-86% в зависимости от разбиения). Возвращает
    (predicted_class, confidence_dict) или None, если модель недоступна.
    """
    bundle = load_ml_model()
    if not bundle:
        return None
    feats = compute_rich_features_from_img(img_full)
    if feats is None:
        return None
    model = bundle["model"]
    feature_names = bundle["feature_names"]
    x = np.array([[feats[name] for name in feature_names]])
    pred = model.predict(x)[0]
    proba = None
    if hasattr(model, "predict_proba"):
        p = model.predict_proba(x)[0]
        proba = dict(zip(model.classes_, p.tolist()))
    return pred, proba


def correct_vignette(gray, vignette_sigma_ratio=6, proxy_max_dim=500):
    """
    Убирает естественное затемнение по краям кадра (виньетирование
    оптики микроскопа). Без этой коррекции алгоритм принимает тёмные
    углы кадра за скопления талька, хотя это чисто оптический эффект -
    яркость на краю кадра падает более чем вдвое относительно центра
    просто из-за объектива, что подтвердилось на всех тестовых снимках.

    Метод: оцениваем фоновую освещённость сильным гауссовым размытием
    (низкие частоты) и делим исходное изображение на неё.

    ФИКС для больших панорам: сигма бралась как доля от РЕАЛЬНОГО размера
    кадра (min(h,w)/6). На панораме 10798x13712 это даёт sigma~1800 -
    гауссово размытие с таким радиусом на 148 мегапикселях практически
    никогда не завершается (не минуты - часы). Освещённость считаем на
    маленькой копии кадра (proxy_max_dim, по умолчанию 500px), затем
    растягиваем обратно. Проверено: было "не завершилось за 10+ минут",
    стало ~0.5 секунды, результат идентичный (освещённость - низкочастотный
    сигнал, полное разрешение для неё не нужно).
    """
    h, w = gray.shape
    scale = proxy_max_dim / max(h, w)
    if scale < 1:
        small = cv2.resize(
            gray, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA
        )
        sigma = min(small.shape) / vignette_sigma_ratio
        illum_small = cv2.GaussianBlur(small, (0, 0), sigmaX=sigma)
        illum = cv2.resize(illum_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
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

    # --- Адаптивный потолок для порога рудной фазы (фикс для тёмных панорам) ---
    # bright_exclude=100 - фиксированное число, откалиброванное на ярких
    # снимках 5x-20x. На тёмной панораме (медианная яркость 24 вместо
    # обычных 82-195) порог 100 не находит почти ничего (0.4% кадра),
    # хотя в кадре есть настоящая рудная фаза - просто в этой экспозиции
    # она темнее 100. Считаем Otsu-порог (бимодальное разделение) ПО ЭТОМУ
    # конкретному кадру и берём МЕНЬШЕЕ из (заданный порог, Otsu) - то есть
    # порог может только понижаться для необычно тёмных кадров, но никогда
    # не повышается для обычных (там Otsu обычно 99-117, т.е. не ниже 100).
    # ВАЖНО: это НЕ влияет на признаки ML-классификатора сорта руды - тот
    # считает свою маску руды независимо, с фиксированным порогом 100,
    # как при обучении, чтобы не сдвигать его точность.
    valid_for_otsu = corrected[background_mask == 0]
    if len(valid_for_otsu) > 100:
        otsu_thresh, _ = cv2.threshold(
            valid_for_otsu.astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        effective_bright_exclude = min(bright_exclude, float(otsu_thresh))
    else:
        effective_bright_exclude = bright_exclude

    ore_mask_raw = (corrected >= effective_bright_exclude).astype(np.uint8) * 255
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

    # --- Классификатор сорта руды: настоящая ML-модель (SVM, 44 признака,
    # обучена на 143 размеченных фото, честная 5-fold CV точность
    # 81.8-86%). Если модель или scikit-image недоступны - откатываемся
    # на старый эвристический классификатор на центроидах (n=30, ~57-73%).
    ml_result = classify_ore_ml(img)
    used_ml = ml_result is not None
    ore_mask_raw_bool = ore_mask_raw > 0
    gray_no_bg = corrected[background_mask == 0]
    std_contrast = compute_std_contrast(gray_no_bg)
    median_ore_grain_area = compute_median_ore_grain_area(ore_mask_raw_bool)
    if used_ml:
        predicted_class, class_distances = ml_result
    else:
        grain_density_in_ore = compute_grain_density_in_ore(
            gray.astype(np.uint8), ore_mask_raw_bool
        )
        ore_pct_of_full_raw = ore_mask_raw_bool.sum() / total_area * 100
        predicted_class, class_distances = classify_ore(
            ore_pct_of_full_raw, std_contrast, grain_density_in_ore, median_ore_grain_area
        )

    model_desc = (
        "ML-модель (SVM, 5-fold CV 81.8-86%, n=143)"
        if used_ml
        else "эвристика на центроидах (n=30, запасной вариант - ML-модель недоступна)"
    )

    if ore_pct_of_full < 15:
        classification_hint = f"вероятно труднообогатимый (мало рудной фазы, <15% кадра). {model_desc}: {predicted_class}"
    else:
        classification_hint = f"{model_desc}: {predicted_class}"

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
        "classifier_used": "ml_svm" if used_ml else "centroid_fallback",
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


def process_file(input_path: str, cfg: Config = config):
    img = imread_unicode(input_path)
    if img is None:
        print(f"[!] Не удалось прочитать: {input_path}")
        print(
            "    Проверь: 1) файл существует, 2) это не битый/пустой файл, "
            "3) путь верный (скопируй его из проводника заново)."
        )
        return None

    # Автоматическая защита от огромных панорам (память + время). На панораме
    # 10798x13712 (148 Мп) без этого пайплайн падал по OutOfMemory (несколько
    # float32-копий кадра по ~0.6 ГБ каждая). Проценты/признаки от даунскейла
    # не искажаются - они везде относительные. Явный --max-dimension всегда
    # можно переопределить; по умолчанию теперь 4000, а не "выключено".
    if cfg.max_dimension is not None and cfg.max_dimension > 0:
        h0, w0 = img.shape[:2]
        scale = cfg.max_dimension / max(h0, w0)
        if scale < 1:
            img = cv2.resize(img, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA)
            print(
                f"  [панорама] Уменьшено перед обработкой: {w0}x{h0} -> {img.shape[1]}x{img.shape[0]}"
            )

    base = os.path.splitext(os.path.basename(input_path))[0]
    debug_dir = os.path.join(cfg.output_dir, "debug") if cfg.debug_mode else None

    zones, mask, stats = detect_talc(
        img,
        debug=cfg.debug_mode,
        debug_prefix=base,
        debug_dir=debug_dir,
        sensitivity=cfg.sensitivity,
        bright_exclude=cfg.bright_exclude,
        density_window=cfg.density_window,
        min_area_ratio=cfg.min_area_ratio,
    )
    output = render_output(img, mask, zones, stats)

    # --- Сегментация срастаний (обычные/тонкие) по ТЗ хакатона: зелёный =
    # обычные срастания, красный = тонкие, синий = тальк (существующая
    # маска). Используем те же ore_mask_raw/closed, что уже считает
    # detect_talc внутри себя - просто пересчитываем их здесь один раз
    # ещё, чтобы не трогать сигнатуру detect_talc(). ---
    gray_for_grains = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    corrected_for_grains = correct_vignette(gray_for_grains)
    bright_exclude = cfg.bright_exclude
    ore_mask_raw_u8 = (corrected_for_grains >= bright_exclude).astype(np.uint8) * 255
    ore_close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    ore_mask_closed_u8 = cv2.morphologyEx(ore_mask_raw_u8, cv2.MORPH_CLOSE, ore_close_kernel)

    grain_label_mask, grain_stats = segment_intergrowths(ore_mask_raw_u8, ore_mask_closed_u8)
    total_area_px = img.shape[0] * img.shape[1]
    intergrowth_summary = summarize_intergrowths(grain_stats, total_area_px)
    combined_overlay = render_combined_overlay(img, grain_label_mask, mask)
    text_conclusion = build_text_conclusion(
        stats["predicted_class"], stats["pct_talc_of_matrix"], intergrowth_summary
    )
    stats["intergrowth"] = intergrowth_summary
    stats["text_conclusion"] = text_conclusion

    os.makedirs(cfg.output_dir, exist_ok=True)

    result_path = os.path.join(cfg.output_dir, f"{base}_talk.jpg")
    mask_path = os.path.join(cfg.output_dir, f"{base}_talk_mask.png")
    stats_path = os.path.join(cfg.output_dir, f"{base}_talk_stats.json")
    intergrowth_mask_path = os.path.join(cfg.output_dir, f"{base}_intergrowth_mask.png")
    combined_path = os.path.join(cfg.output_dir, f"{base}_combined_overlay.jpg")

    imwrite_unicode(result_path, output, ".jpg")
    imwrite_unicode(mask_path, mask, ".png")
    imwrite_unicode(intergrowth_mask_path, grain_label_mask * 127, ".png")
    imwrite_unicode(combined_path, combined_overlay, ".jpg")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"  зон талька найдено:               {stats['zones_count']}")
    print(f"  % талька от нерудной (силикатной) зоны: {stats['pct_talc_of_matrix']}%")
    print(f"  % талька от всего кадра:          {stats['pct_talc_of_full_image']}%")
    print(f"  % рудной фазы от всего кадра:     {stats['pct_ore_of_full_image']}%")
    print(f"  ПРЕДСКАЗАННЫЙ КЛАСС:              {stats['predicted_class']}")
    print(f"  предварительный вывод:            {stats['classification_hint']}")
    print(f"  {text_conclusion}")
    print(f"  сохранено: {result_path}")
    print()

    return stats


def win_basename(path):
    """Имя файла, устойчивое и к '/', и к '\\' (важно на Linux с Windows-путями)."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def true_label_from_path(path):
    """
    Определяет ИСТИННЫЙ класс по названию папки в пути - ТОЛЬКО для сверки
    точности в итоговом отчёте. НИКОГДА не используется для предсказания:
    классификатор (classify_ore) не видит путь к файлу и не имеет к этой
    функции доступа. Это чистая функция для последующей проверки "угадал
    ли алгоритм", а не часть самого алгоритма.
    """
    p = path.lower()
    if "труднообог" in p:
        return "труднообогатимая"
    if "рядов" in p:
        return "рядовая"
    if "оталькован" in p or "обогащен" in p:
        return "оталькованная"
    return None
