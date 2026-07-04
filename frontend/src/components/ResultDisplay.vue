<template>
  <div class="result mb-4">
    <div v-if="processedImage" class="result-image mb-4">
      <img :src="processedImage" alt="Обработанное изображение" class="img-fluid" />
    </div>
    <div v-if="textResult" class="text-result p-3 bg-light rounded-3 border-start border-4 border-success">
      <p class="mb-0 fw-semibold">{{ textResult }}</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    processedImage: String,
    textResult: String,
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
  max-height: 400px;
  max-width: 100%;
  object-fit: contain;
  border-radius: 12px;
}

.text-result {
  background: #f8f9fa !important;
  border-color: #5882ff !important;
  border-radius: 8px;
}
</style>