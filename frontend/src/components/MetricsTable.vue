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
          <tr>
            <td><i class="bi bi-circle-fill text-primary me-2 small"></i>Количество зон</td>
            <td class="text-end fw-bold">{{ metrics.zonesCount }}</td>
          </tr>
          <tr>
            <td><i class="bi bi-circle-fill text-info me-2 small"></i>Доля талька в матрице</td>
            <td class="text-end fw-bold">{{ metrics.pctTalcOfMatrix }}%</td>
          </tr>
          <tr>
            <td><i class="bi bi-circle-fill text-info me-2 small"></i>Доля талька от всего изображения</td>
            <td class="text-end fw-bold">{{ metrics.pctTalcOfFullImage }}%</td>
          </tr>
          <tr>
            <td><i class="bi bi-circle-fill text-success me-2 small"></i>Доля руды от всего изображения</td>
            <td class="text-end fw-bold">{{ metrics.pctOreOfFullImage }}%</td>
          </tr>
          <tr>
            <td><i class="bi bi-circle-fill text-warning me-2 small"></i>Предсказанный класс</td>
            <td class="text-end fw-bold">{{ metrics.predictedClass }}</td>
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
      default: () => ({
        zonesCount: 0,
        pctTalcOfMatrix: 0,
        pctTalcOfFullImage: 0,
        pctOreOfFullImage: 0,
        predictedClass: '',
        classificationHint: '',
        sensitivity: 0,
      }),
    },
  },
}
</script>