"""
intergrowth_segmentation.py

Дополнение к talk_percentage.py: сегментация сульфидных срастаний на
"обычные" (зелёный) и "тонкие" (красный), плюс объединение с маской
талька (синий) в единую цветовую маску - как требует ТЗ хакатона
("Скажи мне кто твой шлиф").

КЛЮЧЕВАЯ ИДЕЯ (взята прямо из формулировки оргов):
"Труднообогатимый: рудные (светлые) фазы значительно ЗАМЕЩАЮТСЯ серой
или тёмной фазой" / "Рядовой: могут НЕЗНАЧИТЕЛЬНО замещаться".

То есть отличие "обычных" от "тонких" срастаний - это доля площади
ВНУТРИ исходного зерна руды, которая на самом деле замещена (потемнела),
а не абсолютный размер зерна самого по себе.

В detect_talc() уже считаются два варианта маски руды:
  - ore_mask_raw    - реальная светлая руда (простой порог яркости)
  - ore_mask_closed - "конверт" зерна (raw + морфологическое закрытие,
                       которое заращивает внутренние тёмные вкрапления)

Замещённая площадь внутри зерна = closed AND NOT raw. Доля замещения
на зерно = (closed_area - raw_area) / closed_area. Это и есть степень
"тонкости" срастания - ничего гадать не приходится, оба ингредиента уже
были в пайплайне.
"""
import cv2
import numpy as np


def segment_intergrowths(ore_mask_raw, ore_mask_closed,
                          substitution_thresh=0.25, small_grain_area_ratio=0.00015):
    """
    Классифицирует каждое зерно руды (по "конверту" - closed-маске) как
    "обычное" (ordinary) или "тонкое" (fine) срастание.

    Параметры:
      substitution_thresh - доля замещённой площади внутри конверта зерна,
                             начиная с которой зерно считается "тонким"
                             срастанием (default 0.25 = 25%).
      small_grain_area_ratio - зёрна мельче этой доли площади кадра
                             автоматически считаются "тонким" срастанием
                             (мелкая рассыпанная вкрапленность сама по себе
                             признак труднообогатимой руды, даже если
                             внутри однородная).

    Возвращает:
      grain_label_mask - uint8 массив того же размера, что и маски:
                          0 = не руда, 1 = обычное срастание (зелёное),
                          2 = тонкое срастание (красное)
      grain_stats - список словарей с метриками по каждому зерну (для
                    отладки/отчёта): area, substitution_ratio, class
    """
    h, w = ore_mask_raw.shape[:2]
    total_area = h * w
    small_area_threshold = total_area * small_grain_area_ratio

    closed_u8 = (ore_mask_closed > 0).astype(np.uint8)
    n_labels, labels = cv2.connectedComponents(closed_u8, connectivity=8)

    grain_label_mask = np.zeros((h, w), dtype=np.uint8)
    grain_stats = []

    raw_bool = ore_mask_raw > 0

    for lbl in range(1, n_labels):
        envelope = (labels == lbl)
        envelope_area = int(envelope.sum())
        if envelope_area < 5:
            continue

        raw_in_envelope = envelope & raw_bool
        raw_area = int(raw_in_envelope.sum())
        substitution_ratio = 1.0 - (raw_area / envelope_area if envelope_area > 0 else 0)

        is_fine = (substitution_ratio >= substitution_thresh) or (envelope_area < small_area_threshold)
        grain_class = 'тонкое' if is_fine else 'обычное'

        # красим только РЕАЛЬНУЮ руду (raw) внутри зерна, а не весь "конверт"
        # (конверт мог включать в себя тёмные замещённые участки - их красить
        # как срастание не нужно, они уже не рудная фаза)
        grain_label_mask[raw_in_envelope] = 2 if is_fine else 1

        grain_stats.append({
            'area_px': envelope_area,
            'raw_area_px': raw_area,
            'substitution_ratio': round(substitution_ratio, 3),
            'class': grain_class,
        })

    return grain_label_mask, grain_stats


def summarize_intergrowths(grain_stats, total_area):
    """
    Агрегирует по-зёренную статистику в проценты для отчёта и для
    определения "преобладающего" типа срастания (нужно для итоговой
    классификации рядовая/труднообогатимая, когда тальк <=10%).
    """
    ordinary_px = sum(g['raw_area_px'] for g in grain_stats if g['class'] == 'обычное')
    fine_px = sum(g['raw_area_px'] for g in grain_stats if g['class'] == 'тонкое')
    n_ordinary = sum(1 for g in grain_stats if g['class'] == 'обычное')
    n_fine = sum(1 for g in grain_stats if g['class'] == 'тонкое')

    return {
        'ordinary_intergrowth_pct_of_frame': round(ordinary_px / total_area * 100, 2),
        'fine_intergrowth_pct_of_frame': round(fine_px / total_area * 100, 2),
        'n_ordinary_grains': n_ordinary,
        'n_fine_grains': n_fine,
        'dominant_intergrowth_type': 'тонкие срастания' if fine_px > ordinary_px else 'обычные срастания',
    }


def make_combined_color_mask(shape, grain_label_mask, talc_mask):
    """
    Собирает итоговую цветовую маску по ТЗ:
      зелёный = обычные срастания
      красный = тонкие срастания
      синий   = тальк
    Возвращает BGR-изображение (для cv2.imwrite/оверлея).
    """
    h, w = shape[:2]
    color = np.zeros((h, w, 3), dtype=np.uint8)
    color[grain_label_mask == 1] = (0, 200, 0)     # зелёный (BGR)
    color[grain_label_mask == 2] = (0, 0, 220)     # красный (BGR)
    talc_bool = talc_mask > 0
    color[talc_bool] = (220, 100, 0)               # синий (BGR)
    return color


def render_combined_overlay(img, grain_label_mask, talc_mask, alpha=0.45):
    """Накладывает цветовую маску на исходное изображение с прозрачностью."""
    color = make_combined_color_mask(img.shape, grain_label_mask, talc_mask)
    mask_any = (grain_label_mask > 0) | (talc_mask > 0)
    output = img.copy()
    blended = cv2.addWeighted(img, 1 - alpha, color, alpha, 0)
    output[mask_any] = blended[mask_any]
    return output


def build_text_conclusion(predicted_class, pct_talc_of_matrix, intergrowth_summary):
    """
    Формирует текстовое заключение ровно в формате из ТЗ:
    "Руда классифицирована как оталькованная: содержание талька 14%,
     преобладание тонких срастаний"
    """
    dominant = intergrowth_summary['dominant_intergrowth_type']
    return (f"Руда классифицирована как {predicted_class}: "
            f"содержание талька {pct_talc_of_matrix:.0f}%, "
            f"преобладание {dominant}")
