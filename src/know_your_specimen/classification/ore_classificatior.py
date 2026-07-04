import numpy as np

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


def classify_ore(material_stats: dict) -> tuple[str, dict[str, float], str]:
    """Nearest-centroid классификация по четырём признакам.

    Args:
        material_stats: Словарь статистик материала (тот же, что возвращается
            в stats из detect_talc). Ожидаемые ключи:
            - ore_pct: процент рудной фазы (сырая маска, без замыкания)
            - std_contrast: межклассовый контраст (std от Отсу)
            - grain_density_in_ore: плотность границ Canny внутри руды
            - median_ore_grain_area: медианная площадь рудного зерна
            - ore_pct_of_full: процент рудной фазы (заращённая маска)

    Returns:
        Кортеж (best_label, dists, classification_hint) — предсказанный
        класс, расстояния до центроидов и текстовая подсказка.
    """
    x = np.array(
        [
            material_stats["ore_pct"],
            material_stats["std_contrast"],
            material_stats["grain_density_in_ore"],
            material_stats["median_ore_grain_area"],
        ]
    )
    x_norm = (x - CLASSIFIER_FEATURE_MEAN) / CLASSIFIER_FEATURE_STD
    dists = {label: float(np.linalg.norm(x_norm - c)) for label, c in CLASSIFIER_CENTROIDS.items()}
    best_label = min(dists, key=lambda k: dists[k])

    if material_stats.get("ore_pct_of_full", 100) < 15:
        hint = (
            f"вероятно труднообогатимый (мало рудной фазы, <15% кадра). "
            f"Классификатор (LOO 73%, n=30): {best_label}"
        )
    else:
        hint = (
            f"классификатор (LOO n=30: 73%, "
            f"внешняя проверка на 178 фото предыдущей версии: 60%): "
            f"{best_label}"
        )
    return best_label, dists, hint
