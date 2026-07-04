<template>
  <div class="uploader h-100">
    <div 
      class="upload-area rounded-3 d-flex align-items-center justify-content-center mb-3"
      @click="triggerUpload"
      :class="{ 'has-image': imagePreview }"
    >
      <input
        type="file"
        ref="fileInput"
        accept="image/*"
        @change="handleFile"
        style="display: none"
      />
      <img v-if="imagePreview" :src="imagePreview" alt="Загруженное изображение" class="img-fluid" />
      <div v-else class="upload-placeholder text-center p-5">
        <button class="btn btn-primary btn-lg px-5">
          Загрузить панараму...
        </button>
        <p class="text-muted mt-3 mb-0">Нажмите кнопку для выбора изображения</p>
      </div>
    </div>
    <button v-if="imagePreview" class="btn btn-outline-secondary w-100" @click="triggerUpload">
      Загрузить новую панараму
    </button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      imagePreview: null,
      selectedFile: null,
    }
  },
  methods: {
    triggerUpload() {
      this.$refs.fileInput.click()
    },
    handleFile(event) {
      const file = event.target.files[0]
      if (file) {
        this.selectedFile = file
        this.imagePreview = URL.createObjectURL(file)
        this.$emit('image-selected', file)
      }
    },
  },
}
</script>

<style scoped>
.upload-area {
  min-height: 400px;
  height: 400px;
  cursor: pointer;
  background: #f8f9fa;
  transition: all 0.2s ease;
  border: 2px dashed #dee2e6 !important;
  overflow: hidden;
}

.upload-area:hover {
  background: #e9ecef;
  border-color: #5882ff !important;
}

.upload-area.has-image {
  border: none !important;
  background: #fff;
}

.upload-area img {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
  border-radius: 12px;
}

.upload-placeholder {
  pointer-events: none;
}
</style>