<template>
  <div class="metrics">
    <h6 class="mb-3 text-primary">
      <i class="bi bi-graph-up me-2"></i>
      Количественные метрики
    </h6>
    <div class="table-responsive">
      <table class="table table-hover align-middle">
        <thead class="table-primary">
          <tr>
            <th>Параметр</th>
            <th class="text-end">Значение</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(value, key) in metrics" :key="key">
            <td>
              <i class="bi bi-circle-fill text-primary me-2 small"></i>
              {{ formatKey(key) }}
            </td>
            <td class="text-end fw-bold">
              {{ formatValue(value) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    metrics: {
      type: Object,
      default: () => ({}),
    },
  },
  methods: {
    formatKey(key) {
      // Преобразуем snake_case в читаемый вид
      const labels = {
        zones_count: 'Количество зон',
        pct_talc_of_matrix: 'Доля талька в матрице',
        pct_talc_of_full_image: 'Доля талька от всего изображения',
        pct_ore_of_full_image: 'Доля руды от всего изображения',
        predicted_class: 'Предсказанный класс',
        classification_hint: 'Подсказка классификации',
        sensitivity: 'Чувствительность',
      }
      
      return labels[key] || key.replace(/_/g, ' ')
    },
    
    formatValue(value) {
      // Добавляем % для процентных значений
      if (typeof value === 'number') {
        const percentFields = ['pct_talc_of_matrix', 'pct_talc_of_full_image', 'pct_ore_of_full_image', 'sensitivity']
        // Проверяем, есть ли ключ в объекте metrics (через родителя)
        return value
      }
      return value
    },
  },
}
</script>