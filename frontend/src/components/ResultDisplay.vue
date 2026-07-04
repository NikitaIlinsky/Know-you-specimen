<template>
  <div class="result mb-4">
    <div v-if="processedImage" class="result-image mb-4">
      <img :src="processedImage" alt="Обработанное изображение" class="img-fluid" />
    </div>
    <div v-if="textResult" class="text-result p-3 bg-light rounded-3 border-start border-4 border-success mb-3">
      <p class="mb-0 fw-semibold">{{ textResult }}</p>
    </div>
    <div v-if="textConclusion" class="text-conclusion p-3 bg-light rounded-3 border-start border-4 border-info">
      <h6 class="fw-bold mb-2">Заключение</h6>
      <p class="mb-0">{{ textConclusion }}</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    processedImage: String,
    textResult: String,
    textConclusion: String,
  },
}
</script>

<style scoped>
.result {
  height: 100%;
}

.result-image {
  overflow: hidden;
  border-radius: 12px;
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}

.result-image img {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
  border-radius: 12px;
}

.text-result {
  background: #f8f9fa !important;
  border-color: #5882ff !important;
  border-radius: 8px;
}

.text-conclusion {
  background: #f8f9fa !important;
  border-color: #0dcaf0 !important;
  border-radius: 8px;
}

.text-conclusion h6 {
  color: #1a1a2e;
}
</style>