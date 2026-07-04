<template>
  <div class="app-wrapper">
    <!-- Header -->
    <header class="header">
      <div class="container">
        <div class="header-content">
          <div class="logo-section">
            <span class="logo-text">НОРНИКЕЛЬ • СКАЖИ МНЕ КТО ТВОЙ ШЛИФ</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Analysis Section -->
    <section class="analysis-section">
      <div class="container">
        <h2 class="section-title">АНАЛИЗ РУД</h2>
        
        <div class="row g-4">
          <!-- Left Panel - Upload -->
          <div class="col-lg-6">
            <div class="analysis-card">
              <ImageUploader @image-selected="handleImageSelected" />
            </div>
          </div>

          <!-- Right Panel - Results -->
          <div class="col-lg-6">
            <!-- Loading state -->
            <div v-if="isLoading" class="analysis-card loading-card">
              <div class="loading-content">
                <div class="spinner"></div>
                <p>Анализируем изображение...</p>
                <small>Это может занять несколько секунд</small>
              </div>
            </div>

            <!-- Error state -->
            <div v-else-if="error" class="analysis-card error-card">
              <div class="error-content">
                <p class="error-message">{{ error }}</p>
                <button class="btn btn-outline-secondary" @click="clearError">
                  Попробовать снова
                </button>
              </div>
            </div>

            <!-- Results -->
            <div v-else-if="showResults" class="analysis-card">
              <div ref="reportContent">
                <!-- Обработанное изображение и результат -->
                <ResultDisplay
                  :processed-image="processedImage"
                  :text-result="textResult"
                />
                
                <!-- Таблица метрик -->
                <MetricsTable :metrics="metrics" />
              </div>
              
              <!-- Кнопка скачивания -->
              <div class="download-section mt-4">
                <button class="btn btn-download w-100" @click="downloadReport" :disabled="isDownloading">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  {{ isDownloading ? 'Формируем отчёт...' : 'Скачать отчёт' }}
                </button>
              </div>
            </div>
            
            <!-- Placeholder when no results -->
            <div v-else class="analysis-card placeholder-card">
              <div class="placeholder-content">
                <p>Загрузите изображение для анализа</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="container text-center">
        <small>Zero DownTime | Санкт-Петербург 2026</small>
      </div>
    </footer>
  </div>
</template>

<script>
import html2pdf from 'html2pdf.js'
import axios from 'axios'
import ImageUploader from './components/ImageUploader.vue'
import ResultDisplay from './components/ResultDisplay.vue'
import MetricsTable from './components/MetricsTable.vue'

// Базовый URL API
const API_BASE_URL = 'http://localhost:8000'

export default {
  components: {
    ImageUploader,
    ResultDisplay,
    MetricsTable,
  },
  data() {
    return {
      showResults: false,
      isLoading: false,
      isDownloading: false,
      error: null,
      uploadedImage: null,
      processedImage: null,
      textResult: '',
      metrics: {
        zonesCount: 0,
        pctTalcOfMatrix: 0,
        pctTalcOfFullImage: 0,
        pctOreOfFullImage: 0,
        predictedClass: '',
        classificationHint: '',
        sensitivity: 0,
      },
    }
  },
  methods: {
    async handleImageSelected(file) {
      console.log('Выбран файл:', file)
      
      // Сбрасываем предыдущие результаты и ошибки
      this.showResults = false
      this.error = null
      this.isLoading = true
      
      try {
        // Создаём FormData для отправки файла
        const formData = new FormData()
        formData.append('file', file)
        
        // Делаем POST-запрос на API
        const response = await axios.post(`${API_BASE_URL}/api/v1/analyze`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
        
        // Обрабатываем ответ
        const data = response.data
        
        // Загружаем картинку и конвертируем в base64 для PDF
        this.processedImage = await this.imageToBase64(
          `${API_BASE_URL}${data.artifacts.annotated_image}`
        )
        
        // Формируем текстовый результат
        this.textResult = `Класс: ${data.stats.predicted_class} (${data.stats.classification_hint})`
        
        // Маппим метрики из API
        this.metrics = {
          zonesCount: data.stats.zones_count,
          pctTalcOfMatrix: data.stats.pct_talc_of_matrix,
          pctTalcOfFullImage: data.stats.pct_talc_of_full_image,
          pctOreOfFullImage: data.stats.pct_ore_of_full_image,
          predictedClass: data.stats.predicted_class,
          classificationHint: data.stats.classification_hint,
          sensitivity: data.stats.sensitivity,
        }
        
        this.showResults = true
        
      } catch (error) {
        console.error('Ошибка при загрузке:', error)
        
        if (error.response) {
          if (error.response.status === 422) {
            this.error = 'Неверный запрос: отсутствует файл, неподдерживаемый формат или битое изображение'
          } else if (error.response.status === 500) {
            this.error = 'Внутренняя ошибка сервера при обработке изображения'
          } else {
            this.error = `Ошибка сервера: ${error.response.status} - ${error.response.data.detail || 'Неизвестная ошибка'}`
          }
        } else if (error.request) {
          this.error = 'Нет соединения с сервером. Проверьте, запущен ли сервер на http://localhost:8000'
        } else {
          this.error = `Ошибка: ${error.message}`
        }
        
      } finally {
        this.isLoading = false
      }
    },
    
    // Конвертируем изображение в base64 для корректного отображения в PDF
    async imageToBase64(url) {
      try {
        const response = await fetch(url)
        const blob = await response.blob()
        return new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onloadend = () => resolve(reader.result)
          reader.onerror = reject
          reader.readAsDataURL(blob)
        })
      } catch (error) {
        console.error('Ошибка при конвертации изображения:', error)
        return url // Возвращаем оригинальный URL если не удалось конвертировать
      }
    },
    
    clearError() {
      this.error = null
      this.uploadedImage = null
      this.showResults = false
    },
    
    async downloadReport() {
      if (this.isDownloading) return
      
      this.isDownloading = true
      
      try {
        const element = this.$refs.reportContent
        
        // Ждём, чтобы картинки точно загрузились
        await this.$nextTick()
        
        const opt = {
          margin: 10,
          filename: `отчет_анализ_руд_${Date.now()}.pdf`,
          image: { type: 'jpeg', quality: 0.98 },
          html2canvas: { 
            scale: 2, 
            useCORS: true,
            allowTaint: true,
            logging: false,
          },
          jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        }
        
        await html2pdf().set(opt).from(element).save()
      } catch (error) {
        console.error('Ошибка при создании PDF:', error)
        this.error = 'Не удалось создать PDF. Попробуйте ещё раз.'
      } finally {
        this.isDownloading = false
      }
    },
  },
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
  color: #1a1a2e;
}

.app-wrapper {
  min-height: 100vh;
}

/* Header */
.header {
  background-color: #5882ff;
  padding: 20px 0;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 30px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
}

/* Analysis Section */
.analysis-section {
  background-color: #fff;
  padding: 80px 0;
  min-height: 80vh;
}

.section-title {
  font-size: 48px;
  font-weight: 900;
  color: #1a1a2e;
  margin-bottom: 40px;
  text-align: center;
}

.analysis-card {
  background: #fff;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 30px;
  min-height: 500px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.row.g-4 {
  align-items: flex-start;
}

.placeholder-card,
.loading-card,
.error-card {
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-content,
.loading-content,
.error-content {
  text-align: center;
}

.placeholder-content p {
  color: #999;
  font-size: 18px;
}

/* Loading Spinner */
.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e0e0e0;
  border-top: 4px solid #5882ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-content p {
  font-size: 18px;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.loading-content small {
  color: #999;
}

/* Error */
.error-message {
  color: #dc3545;
  font-size: 16px;
  margin-bottom: 20px;
}

/* Download Button */
.download-section {
  margin-top: auto;
  padding-top: 20px;
}

.btn-download {
  background-color: #5882ff;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-download:hover:not(:disabled) {
  background-color: #4a73e6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(88, 130, 255, 0.3);
}

.btn-download:active:not(:disabled) {
  transform: translateY(0);
}

.btn-download:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Footer */
.footer {
  background-color: #1a1a2e;
  color: #5882ff;
  padding: 30px 0;
  margin-top: 80px;
}

.footer small {
  font-size: 14px;
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 20px;
  }
  
  .section-title {
    font-size: 36px;
  }
}
</style>