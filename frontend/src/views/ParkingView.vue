<template>
  <section class="parking-list-container">
    <transition name="toast">
      <div v-if="notification.show" :class="['toast-notification', notification.type]">
        <span class="toast-icon">
          {{ notification.type === 'success' ? '✓' : '⚠' }}
        </span>
        <span class="toast-message">{{ notification.message }}</span>
      </div>
    </transition>

    <div class="content">
      <div class="page-top">
        <div class="page-title">
          <h1>Парковки</h1>
          <p>Список парковок, доступных текущему администратору</p>
        </div>

        <button class="secondary-btn" @click="loadParkings">
          Обновить
        </button>
      </div>

      <div v-if="isLoading" class="loading-indicator">
        Загрузка данных...
      </div>

      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <div v-if="!isLoading && !errorMessage && !parkings.length" class="empty-state">
        Парковки пока не созданы.
      </div>

      <div v-else class="parking-list">
        <div
          v-for="parking in parkings"
          :key="parking.id"
          class="parking-item"
        >
          <div class="parking-header">
            <div class="parking-title">
              <span class="parking-name">{{ parking.name }}</span>
              <span class="parking-id">ID: {{ parking.id }}</span>
            </div>

            <div class="parking-summary">
              <span class="summary-item free">
                Свободно: {{ parking.summary?.free ?? 0 }}
              </span>

              <span class="summary-item occupied">
                Занято: {{ parking.summary?.occupied ?? 0 }}
              </span>

              <span class="summary-item unknown">
                Неизвестно: {{ parking.summary?.unknown ?? 0 }}
              </span>
            </div>

            <div class="header-buttons">
              <button class="map-btn" @click="openMap(parking.id)">
                Карта
              </button>

              <button class="settings-btn" @click="openSetup(parking.id)">
                Настройка
              </button>

              <button
                class="collapse-btn"
                @click="toggleParking(parking.id)"
              >
                <span :class="['arrow', { rotated: expandedParking === parking.id }]">
                  ▲
                </span>
              </button>
            </div>
          </div>

          <div v-if="expandedParking === parking.id" class="parking-details">
            <div class="info-row">
              <div class="info-box">
                <span>Описание</span>
                <b>{{ getParkingDescription(parking) }}</b>
              </div>

              <div class="info-box">
                <span>Компания</span>
                <b>{{ parking.company_id ?? '—' }}</b>
              </div>

              <div class="info-box">
                <span>Мест</span>
                <b>{{ parking.spots_count ?? 0 }}</b>
              </div>

              <div class="info-box">
                <span>Зон</span>
                <b>{{ parking.zones_count ?? 0 }}</b>
              </div>
            </div>

            <div class="table-wrap">
              <table class="cameras-table">
                <thead>
                  <tr>
                    <th>Камера</th>
                    <th>Тип источника</th>
                    <th>Статус</th>
                    <th>URL / Видео</th>
                  </tr>
                </thead>

                <tbody>
                  <tr
                    v-for="camera in getParkingCameras(parking)"
                    :key="camera.id || `${parking.id}-source`"
                  >
                    <td>
                      <div class="camera-name">
                        {{ camera.name || 'Источник парковки' }}
                      </div>

                      <div class="camera-id">
                        ID: {{ camera.id || '—' }}
                      </div>
                    </td>

                    <td>
                      <span :class="['source-type', getSourceType(camera)]">
                        {{ getSourceTypeLabel(camera) }}
                      </span>
                    </td>

                    <td>
                      <span :class="['status-badge', getCameraStatusClass(camera)]">
                        {{ getCameraStatusText(camera) }}
                      </span>
                    </td>

                    <td class="source-cell">
                      <div class="source-main">
                        {{ getSourceDisplay(camera).main }}
                      </div>

                      <div v-if="getSourceDisplay(camera).sub" class="source-sub">
                        {{ getSourceDisplay(camera).sub }}
                      </div>
                    </td>
                  </tr>

                  <tr v-if="!getParkingCameras(parking).length">
                    <td colspan="4" class="empty-camera">
                      Источник камеры пока не настроен
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="detail-actions">
              <button class="map-btn" @click="openMap(parking.id)">
                Открыть карту
              </button>

              <button class="settings-btn" @click="openSetup(parking.id)">
                Настройки
              </button>

              <button class="danger-btn" @click="deleteParking(parking)">
                Удалить парковку
              </button>
            </div>
          </div>
        </div>

        <div class="center-button">
          <button class="add-parking-btn" @click="createParking">
            Добавить парковку
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { parkingService } from '@/services/parking'

const router = useRouter()

const parkings = ref([])
const expandedParking = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')

const notification = ref({
  show: false,
  message: '',
  type: 'success',
})

function showNotification(message, type = 'success') {
  notification.value = {
    show: true,
    message,
    type,
  }

  setTimeout(() => {
    notification.value.show = false
  }, 3000)
}

async function loadParkings() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const data = await parkingService.getAllParkings()

    parkings.value = Array.isArray(data)
      ? data.map(normalizeParking)
      : []
  } catch (error) {
    console.error('Ошибка загрузки парковок:', error)
    errorMessage.value = 'Не удалось загрузить список парковок'
    parkings.value = []
  } finally {
    isLoading.value = false
  }
}

function normalizeParking(parking) {
  const cameras = []

  if (Array.isArray(parking.cameras)) {
    cameras.push(...parking.cameras)
  } else if (parking.camera) {
    cameras.push(parking.camera)
  }

  const parkingSource = buildParkingSourceCamera(parking)

  if (!cameras.length && parkingSource) {
    cameras.push(parkingSource)
  }

  return {
    ...parking,
    id: String(parking.id),
    cameras,
  }
}

function buildParkingSourceCamera(parking) {
  const sourceType = parking.source_type || parking.camera_source_type
  const sourceUrl = parking.source_url || parking.rtsp_url
  const testVideoPath = parking.test_video_path || parking.video_path || parking.source_video_path

  if (!sourceType && !sourceUrl && !testVideoPath) {
    return null
  }

  return {
    id: parking.camera_id || null,
    name: parking.camera_name || parking.source_name || 'Источник парковки',
    source_type: sourceType || (sourceUrl ? 'rtsp' : 'video'),
    source_url: sourceUrl || null,
    rtsp_url: sourceUrl || null,
    test_video_path: testVideoPath || null,
    video_path: testVideoPath || null,
  }
}

function toggleParking(id) {
  expandedParking.value = expandedParking.value === id ? null : id
}

function createParking() {
  router.push('/admin/parkings/new')
}

function openSetup(parkingId) {
  router.push(`/admin/parkings/${parkingId}/setup`)
}

function openMap(parkingId) {
  router.push({
    path: '/main',
    query: {
      parking_id: parkingId,
    },
  })
}

async function deleteParking(parking) {
  const ok = window.confirm(`Удалить парковку "${parking.name}"?`)

  if (!ok) return

  isLoading.value = true
  errorMessage.value = ''

  try {
    await parkingService.deleteParking(parking.id)
    await loadParkings()
    showNotification('Парковка удалена', 'success')
  } catch (error) {
    console.error('Ошибка удаления парковки:', error)
    errorMessage.value = 'Не удалось удалить парковку'
    showNotification('Не удалось удалить парковку', 'error')
  } finally {
    isLoading.value = false
  }
}

function getParkingDescription(parking) {
  return parking.description || parking.address || '—'
}

function getParkingCameras(parking) {
  return Array.isArray(parking.cameras) ? parking.cameras : []
}

function getSourceType(camera) {
  return String(camera.source_type || camera.type || '').toLowerCase()
}

function getSourceTypeLabel(camera) {
  const type = getSourceType(camera)

  if (type === 'video') return 'Видео'
  if (type === 'rtsp') return 'RTSP'
  if (type === 'stream') return 'Поток'

  return 'Не задан'
}

function getCameraSource(camera) {
  return (
    camera.source_url ||
    camera.url ||
    camera.source ||
    camera.rtsp_url ||
    camera.test_video_path ||
    camera.video_path ||
    camera.source_path ||
    ''
  )
}

function getVideoPath(camera) {
  return (
    camera.test_video_path ||
    camera.video_path ||
    camera.source_path ||
    camera.source ||
    ''
  )
}

function getFileName(path) {
  if (!path) return ''

  const normalized = String(path).replaceAll('\\', '/')
  return normalized.split('/').filter(Boolean).at(-1) || normalized
}

function getSourceDisplay(camera) {
  const type = getSourceType(camera)

  if (type === 'video') {
    const videoPath = getVideoPath(camera)
    const fileName = getFileName(videoPath)

    return {
      main: fileName || 'Видео не загружено',
      sub: videoPath && fileName !== videoPath ? videoPath : '',
    }
  }

  if (type === 'rtsp' || type === 'stream') {
    const url = camera.source_url || camera.url || camera.rtsp_url || camera.source

    return {
      main: url || 'URL потока не указан',
      sub: '',
    }
  }

  const source = getCameraSource(camera)

  return {
    main: source || 'Источник не указан',
    sub: '',
  }
}

function isRtspSource(camera) {
  const type = getSourceType(camera)
  return type === 'rtsp' || type === 'stream'
}

function isVideoSource(camera) {
  const type = getSourceType(camera)
  return type === 'video'
}

function hasRtspStream(camera) {
  return Boolean(
    camera.source_url ||
    camera.url ||
    camera.rtsp_url
  )
}

function hasVideoFile(camera) {
  return Boolean(
    camera.test_video_path ||
    camera.video_path ||
    camera.source_path ||
    camera.source
  )
}

function getCameraStatusClass(camera) {
  if (isRtspSource(camera) && hasRtspStream(camera)) {
    return 'online'
  }

  if (isVideoSource(camera) && hasVideoFile(camera)) {
    return 'video'
  }

  return 'offline'
}

function getCameraStatusText(camera) {
  if (isRtspSource(camera) && hasRtspStream(camera)) {
    return 'видеопоток активен'
  }

  if (isVideoSource(camera) && hasVideoFile(camera)) {
    return 'используется видео'
  }

  return 'не активно'
}

onMounted(() => {
  loadParkings()
})
</script>

<style scoped>
.parking-list-container {
  min-height: calc(100vh - 70px);
  background-color: #f5f7fb;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  box-sizing: border-box;
}

.content {
  padding: 34px 40px;
  width: 100%;
  box-sizing: border-box;
}

.page-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  margin-bottom: 28px;
  padding: 18px 22px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

.page-title h1 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 30px;
  line-height: 1.1;
}

.page-title p {
  margin: 0;
  color: #6b7280;
  font-size: 15px;
}

.secondary-btn {
  border: none;
  border-radius: 10px;
  padding: 12px 18px;
  background: #eef2f7;
  color: #1f2937;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.add-parking-btn {
  background-color: #2689e6;
  color: white;
  border: none;
  padding: 14px 38px;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  font-weight: 700;
}

.toast-notification {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 15px 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.14);
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 2000;
  font-size: 15px;
  font-weight: 500;
  min-width: 300px;
  justify-content: center;
}

.toast-notification.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.toast-notification.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.toast-icon {
  font-size: 18px;
  font-weight: bold;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

.loading-indicator {
  background-color: #d1ecf1;
  color: #0c5460;
  padding: 12px 20px;
  text-align: center;
  font-size: 14px;
  margin-bottom: 20px;
  border-radius: 8px;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 12px 20px;
  text-align: center;
  font-size: 14px;
  margin-bottom: 20px;
  border-radius: 8px;
  border: 1px solid #f5c6cb;
}

.empty-state {
  padding: 26px;
  background: #fff;
  color: #6b7280;
  border-radius: 14px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
}

.parking-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
}

.parking-item {
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 6px 22px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  border: 1px solid #e5e7eb;
  width: 100%;
  box-sizing: border-box;
}

.parking-header {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto auto;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
  background-color: #ffffff;
  border-bottom: 1px solid #eef2f7;
}

.parking-title {
  min-width: 0;
}

.parking-name {
  display: block;
  font-size: 20px;
  font-weight: 800;
  color: #111827;
  line-height: 1.15;
}

.parking-id {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.parking-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.summary-item {
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  background: #f3f4f6;
  white-space: nowrap;
}

.summary-item.free {
  color: #16a34a;
  background: #ecfdf3;
}

.summary-item.occupied {
  color: #dc2626;
  background: #fef2f2;
}

.summary-item.unknown {
  color: #6b7280;
  background: #f3f4f6;
}

.header-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
}

.map-btn,
.settings-btn,
.danger-btn {
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 700;
}

.map-btn {
  background-color: #2689e6;
  color: white;
}

.settings-btn {
  background-color: #eef2f7;
  color: #111827;
}

.danger-btn {
  background: #ef4444;
  color: #fff;
}

.collapse-btn {
  background: transparent;
  border: none;
  color: #2689e6;
  font-size: 18px;
  cursor: pointer;
  padding: 7px 10px;
}

.arrow {
  display: inline-block;
  transition: transform 0.25s ease;
}

.arrow.rotated {
  transform: rotate(180deg);
}

.parking-details {
  padding: 20px;
  background: #fafafa;
  width: 100%;
  box-sizing: border-box;
}

.info-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 12px;
  margin-bottom: 18px;
}

.info-box {
  padding: 13px 14px;
  border-radius: 10px;
  background: white;
  border: 1px solid #e5e7eb;
}

.info-box span {
  display: block;
  margin-bottom: 5px;
  color: #6b7280;
  font-size: 12px;
}

.info-box b {
  color: #111827;
  font-size: 15px;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: white;
}

.cameras-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 780px;
}

.cameras-table th,
.cameras-table td {
  padding: 13px 14px;
  text-align: left;
  border-bottom: 1px solid #eef2f7;
  vertical-align: middle;
}

.cameras-table th {
  background-color: #f3f4f6;
  font-weight: 800;
  color: #1f2937;
  font-size: 14px;
}

.cameras-table tr:last-child td {
  border-bottom: none;
}

.camera-name {
  color: #111827;
  font-weight: 700;
}

.camera-id {
  margin-top: 3px;
  color: #6b7280;
  font-size: 12px;
}

.source-type {
  display: inline-flex;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  background: #eef2f7;
  color: #475569;
}

.source-type.video {
  background: #eef6ff;
  color: #2689e6;
}

.source-type.rtsp,
.source-type.stream {
  background: #ecfdf3;
  color: #16a34a;
}

.status-badge {
  display: inline-flex;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.status-badge.online {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.video {
  background-color: #eef6ff;
  color: #2689e6;
}

.status-badge.offline {
  background-color: #f8d7da;
  color: #721c24;
}

.source-cell {
  max-width: 460px;
}

.source-main {
  color: #111827;
  font-weight: 600;
  word-break: break-word;
}

.source-sub {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
  word-break: break-all;
}

.empty-camera {
  text-align: center;
  color: #6b7280;
  padding: 20px;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.center-button {
  display: flex;
  justify-content: center;
  width: 100%;
  margin-top: 12px;
}

@media (max-width: 900px) {
  .content {
    padding: 22px 18px;
  }

  .page-top {
    flex-direction: column;
    align-items: stretch;
  }

  .secondary-btn {
    width: 100%;
  }

  .parking-header {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }

  .parking-summary {
    justify-content: flex-start;
  }

  .header-buttons {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .info-row {
    grid-template-columns: 1fr;
  }

  .detail-actions {
    flex-direction: column;
  }

  .detail-actions button {
    width: 100%;
  }
}
</style>