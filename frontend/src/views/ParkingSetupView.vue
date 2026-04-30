<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Настройка парковки</h1>
        <p v-if="parking">
          {{ parking.name }} / {{ parking.id }}
        </p>
      </div>

      <button class="secondary-btn" @click="goBack">
        Назад
      </button>
    </div>

    <div v-if="loading" class="card">
      Загрузка...
    </div>

    <div v-else-if="error" class="alert error">
      {{ error }}
    </div>

    <div v-else class="grid">
      <div class="card">
        <h2>Источник камеры</h2>

        <p class="muted">
          Для тестирования можно загрузить видео. Для реального подключения используется RTSP.
        </p>

        <div class="upload-row">
          <input
            ref="videoInputRef"
            type="file"
            accept="video/*"
            @change="onVideoSelected"
          >

          <button
            class="primary-btn"
            :disabled="!videoFile || uploadingVideo"
            @click="uploadVideo"
          >
            {{ uploadingVideo ? 'Загрузка...' : 'Загрузить тестовое видео' }}
          </button>
        </div>

        <div v-if="videoMessage" class="alert success">
          {{ videoMessage }}
        </div>
      </div>

      <div class="card">
        <h2>Скриншот для разметки</h2>

        <p class="muted">
          Скриншот будет использоваться в редакторе разметки парковочных мест.
        </p>

        <div class="upload-row">
          <input
            ref="snapshotInputRef"
            type="file"
            accept="image/*"
            @change="onSnapshotSelected"
          >

          <button
            class="primary-btn"
            :disabled="!snapshotFile || uploadingSnapshot"
            @click="uploadSnapshot"
          >
            {{ uploadingSnapshot ? 'Загрузка...' : 'Загрузить скриншот' }}
          </button>
        </div>

        <button
          class="secondary-btn full"
          :disabled="capturing"
          @click="captureSnapshot"
        >
          {{ capturing ? 'Получение кадра...' : 'Получить кадр из видео/RTSP' }}
        </button>

        <div v-if="snapshotMessage" class="alert success">
          {{ snapshotMessage }}
        </div>

        <div v-if="snapshotUrl" class="snapshot-box">
          <img :src="snapshotUrl" alt="Скриншот парковки">
        </div>

        <button class="secondary-btn full" @click="loadSnapshot">
          Обновить предпросмотр скриншота
        </button>
      </div>

      <div class="card">
        <h2>Редакторы</h2>

        <div class="editor-actions">
          <button class="primary-btn" @click="openLayoutEditor">
            Редактор разметки мест
          </button>

          <button class="primary-btn" @click="openMapEditor">
            Конструктор цифровой карты
          </button>

          <button class="secondary-btn" @click="openUserMap">
            Открыть пользовательскую карту
          </button>
        </div>
      </div>

      <div class="card">
        <h2>Состояние</h2>

        <div class="info-list">
          <div>
            <span>Layout</span>
            <b>{{ parking?.layout_file_path ? 'создан' : 'нет' }}</b>
          </div>

          <div>
            <span>Map</span>
            <b>{{ parking?.map_file_path ? 'создан' : 'нет' }}</b>
          </div>

          <div>
            <span>Occupancy</span>
            <b>{{ parking?.occupancy_file_path ? 'создан' : 'нет' }}</b>
          </div>

          <div>
            <span>Мест</span>
            <b>{{ parking?.spots_count ?? 0 }}</b>
          </div>

          <div>
            <span>Зон</span>
            <b>{{ parking?.zones_count ?? 0 }}</b>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { parkingService } from '@/services/parking'

const route = useRoute()
const router = useRouter()

const parkingId = String(route.params.parkingId)

const loading = ref(false)
const error = ref('')

const parking = ref(null)

const videoFile = ref(null)
const snapshotFile = ref(null)

const uploadingVideo = ref(false)
const uploadingSnapshot = ref(false)
const capturing = ref(false)

const videoMessage = ref('')
const snapshotMessage = ref('')

const snapshotUrl = ref('')

async function loadParking() {
  loading.value = true
  error.value = ''

  try {
    parking.value = await parkingService.getParking(parkingId)
    await loadSnapshot()
  } catch (err) {
    console.error('Ошибка загрузки парковки:', err)
    error.value = 'Не удалось загрузить парковку'
  } finally {
    loading.value = false
  }
}

function onVideoSelected(event) {
  videoFile.value = event.target.files?.[0] || null
  videoMessage.value = ''
}

function onSnapshotSelected(event) {
  snapshotFile.value = event.target.files?.[0] || null
  snapshotMessage.value = ''
}

async function uploadVideo() {
  if (!videoFile.value) return

  uploadingVideo.value = true
  videoMessage.value = ''

  try {
    await parkingService.uploadSourceVideo(parkingId, videoFile.value)
    videoMessage.value = 'Тестовое видео загружено'
    parking.value = await parkingService.getParking(parkingId)
  } catch (err) {
    console.error('Ошибка загрузки видео:', err)
    error.value = 'Не удалось загрузить видео'
  } finally {
    uploadingVideo.value = false
  }
}

async function uploadSnapshot() {
  if (!snapshotFile.value) return

  uploadingSnapshot.value = true
  snapshotMessage.value = ''

  try {
    await parkingService.uploadSnapshot(parkingId, snapshotFile.value)
    snapshotMessage.value = 'Скриншот загружен'
    parking.value = await parkingService.getParking(parkingId)
    await loadSnapshot()
  } catch (err) {
    console.error('Ошибка загрузки скриншота:', err)
    error.value = 'Не удалось загрузить скриншот'
  } finally {
    uploadingSnapshot.value = false
  }
}

async function captureSnapshot() {
  capturing.value = true
  snapshotMessage.value = ''
  error.value = ''

  try {
    await parkingService.captureSnapshot(parkingId)
    snapshotMessage.value = 'Скриншот получен из источника'
    parking.value = await parkingService.getParking(parkingId)
    await loadSnapshot()
  } catch (err) {
    console.error('Ошибка получения скриншота:', err)

    if (err.response?.status === 400) {
      error.value = 'Не удалось открыть источник камеры/видео. Проверь RTSP или загруженное видео.'
    } else {
      error.value = 'Не удалось получить скриншот'
    }
  } finally {
    capturing.value = false
  }
}

async function loadSnapshot() {
  if (snapshotUrl.value) {
    URL.revokeObjectURL(snapshotUrl.value)
    snapshotUrl.value = ''
  }

  try {
    const blob = await parkingService.getSnapshotBlob(parkingId)
    snapshotUrl.value = URL.createObjectURL(blob)
  } catch {
    snapshotUrl.value = ''
  }
}

function openLayoutEditor() {
  router.push(`/admin/parkings/${parkingId}/layout-editor`)
}

function openMapEditor() {
  router.push(`/admin/parkings/${parkingId}/map-editor`)
}

function openUserMap() {
  router.push({
    path: '/main',
    query: {
      parking_id: parkingId,
    },
  })
}

function goBack() {
  router.push('/admin/parkings')
}

onMounted(() => {
  loadParking()
})

onBeforeUnmount(() => {
  if (snapshotUrl.value) {
    URL.revokeObjectURL(snapshotUrl.value)
  }
})
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

.page-header p,
.muted {
  margin: 0;
  color: #6b7280;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: 18px;
}

.card {
  background: #fff;
  border-radius: 18px;
  padding: 22px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.card h2 {
  margin: 0 0 10px;
  color: #1f2937;
}

.upload-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 18px;
  flex-wrap: wrap;
}

.primary-btn,
.secondary-btn {
  border: none;
  border-radius: 10px;
  padding: 11px 16px;
  cursor: pointer;
  font-weight: 700;
}

.primary-btn {
  background: #2d8fe3;
  color: white;
}

.secondary-btn {
  background: #eef2f7;
  color: #1f2937;
}

.primary-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.full {
  width: 100%;
  margin-top: 14px;
}

.alert {
  margin-top: 14px;
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

.snapshot-box {
  margin-top: 16px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  background: #111827;
}

.snapshot-box img {
  width: 100%;
  display: block;
  max-height: 360px;
  object-fit: contain;
}

.editor-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-list {
  display: grid;
  gap: 12px;
}

.info-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #e5e7eb;
}

.info-list span {
  color: #6b7280;
}

.info-list b {
  color: #111827;
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>