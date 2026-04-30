<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Добавить парковку</h1>
        <p>Создание парковки и первичного источника камеры</p>
      </div>

      <button class="secondary-btn" @click="goBack">
        Назад
      </button>
    </div>

    <div class="card">
      <div class="form-grid">
        <label>
          <span>Название парковки</span>
          <input
            v-model="form.name"
            type="text"
            placeholder="Например: Парковка у офиса"
          >
        </label>

        <label>
          <span>Slug / ID парковки</span>
          <input
            v-model="form.slug"
            type="text"
            placeholder="parking_office"
          >
        </label>

        <label>
          <span>Описание</span>
          <input
            v-model="form.description"
            type="text"
            placeholder="Необязательно"
          >
        </label>

        <label>
          <span>Название камеры</span>
          <input
            v-model="form.camera_name"
            type="text"
            placeholder="Камера 1"
          >
        </label>

        <label>
          <span>Тип источника</span>
          <select v-model="form.source_type">
            <option value="rtsp">RTSP камера</option>
            <option value="video">Тестовое видео</option>
          </select>
        </label>

        <label v-if="form.source_type === 'rtsp'">
          <span>RTSP URL</span>
          <input
            v-model="form.source_url"
            type="text"
            placeholder="rtsp://login:password@host:554/stream"
          >
        </label>
      </div>

      <div v-if="error" class="alert error">
        {{ error }}
      </div>

      <div v-if="success" class="alert success">
        {{ success }}
      </div>

      <div class="actions">
        <button class="primary-btn" :disabled="loading" @click="createParking">
          {{ loading ? 'Создание...' : 'Создать парковку' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { parkingService } from '@/services/parking'

const router = useRouter()

const loading = ref(false)
const error = ref('')
const success = ref('')

const form = reactive({
  name: '',
  slug: '',
  description: '',
  source_type: 'video',
  source_url: '',
  camera_name: '',
})

function makeSlug(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-zа-я0-9]+/gi, '_')
    .replace(/^_+|_+$/g, '')
}

function validate() {
  if (!form.name.trim()) {
    return 'Введите название парковки'
  }

  if (form.source_type === 'rtsp' && !form.source_url.trim()) {
    return 'Для RTSP-камеры нужно указать RTSP URL'
  }

  return null
}

async function createParking() {
  error.value = ''
  success.value = ''

  const validationError = validate()
  if (validationError) {
    error.value = validationError
    return
  }

  loading.value = true

  try {
    const payload = {
      name: form.name.trim(),
      slug: form.slug.trim() || makeSlug(form.name),
      description: form.description.trim() || null,
      source_type: form.source_type,
      source_url: form.source_type === 'rtsp' ? form.source_url.trim() : null,
      camera_name: form.camera_name.trim() || null,
    }

    const created = await parkingService.createParking(payload)

    success.value = 'Парковка создана'

    router.push({
      path: `/admin/parkings/${created.id}/setup`,
    })
  } catch (err) {
    console.error('Ошибка создания парковки:', err)

    if (err.response?.status === 409) {
      error.value = 'Парковка с таким slug уже существует'
    } else if (err.response?.status === 403) {
      error.value = 'Нет прав на создание парковки'
    } else {
      error.value = 'Не удалось создать парковку'
    }
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/admin/parkings')
}
</script>

<style scoped>
.page {
  min-height: calc(100vh - 70px);
  padding: 28px;
  background: #f5f7fb;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.page-header h1 {
  margin: 0 0 6px;
  color: #1f2937;
}

.page-header p {
  margin: 0;
  color: #6b7280;
}

.card {
  background: #fff;
  border-radius: 18px;
  padding: 24px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(240px, 1fr));
  gap: 18px;
}

label span {
  display: block;
  margin-bottom: 8px;
  color: #374151;
  font-weight: 700;
}

input,
select {
  width: 100%;
  height: 42px;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 0 12px;
  background: #fff;
}

.alert {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 10px;
}

.alert.error {
  background: #fee2e2;
  color: #991b1b;
}

.alert.success {
  background: #dcfce7;
  color: #166534;
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

.primary-btn,
.secondary-btn {
  border: none;
  border-radius: 10px;
  padding: 12px 18px;
  cursor: pointer;
  font-weight: 700;
}

.primary-btn {
  background: #2d8fe3;
  color: white;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  background: #eef2f7;
  color: #1f2937;
}

@media (max-width: 800px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>