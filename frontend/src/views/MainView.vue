# Что этот файл делает?
# При открытии страницы запрашивает: GET /api/parking-map/parking_a/state
# Получает: layout + occupancy
# Передает данные в ParkingMap.vue
# Каждые 2 секунды запрашивает только: GET /api/parking-map/parking_a/occupancy
# Если run_parking_stream.py обновил occupancy.json, карта перекрасится автоматически.

<template>
  <main class="main-view">
    <section class="hero">
      <div>
        <p class="eyebrow">ParkFlow AI</p>
        <h1>Цифровая карта парковки</h1>
        <p class="subtitle">
          Актуальная занятость парковочных мест по данным детекции.
        </p>
      </div>

      <div class="parking-selector">
        <label for="parking-id">Parking ID</label>
        <input
          id="parking-id"
          v-model="parkingId"
          type="text"
          @keyup.enter="reloadState"
        />
        <button type="button" @click="reloadState">
          Обновить
        </button>
      </div>
    </section>

    <section class="status-row">
      <div class="status-card">
        <span>Всего</span>
        <strong>{{ summary.total }}</strong>
      </div>

      <div class="status-card free">
        <span>Свободно</span>
        <strong>{{ summary.free }}</strong>
      </div>

      <div class="status-card occupied">
        <span>Занято</span>
        <strong>{{ summary.occupied }}</strong>
      </div>

      <div class="status-card unknown">
        <span>Неизвестно</span>
        <strong>{{ summary.unknown }}</strong>
      </div>
    </section>

    <section v-if="loading" class="message-card">
      Загрузка цифровой карты...
    </section>

    <section v-else-if="error" class="message-card error">
      {{ error }}
    </section>

    <section v-else class="content-grid">
      <div class="map-card">
        <div class="card-header">
          <div>
            <h2>{{ parkingName }}</h2>
            <p>
              {{ layout?.parking?.id || parkingId }}
              <span v-if="occupancy?.timestamp_sec !== undefined">
                · кадр {{ occupancy?.frame_index ?? 0 }}
              </span>
            </p>
          </div>

          <div class="legend">
            <span><i class="dot free"></i> свободно</span>
            <span><i class="dot occupied"></i> занято</span>
            <span><i class="dot unknown"></i> неизвестно</span>
          </div>
        </div>

        <ParkingMap
          :layout="layout"
          :occupancy="occupancy"
        />
      </div>

      <aside class="side-panel">
        <div class="panel-card">
          <h3>Свободные места</h3>

          <div v-if="freeSpots.length === 0" class="empty-list">
            Свободных мест нет или данные ещё не обновились.
          </div>

          <ul v-else class="spots-list">
            <li v-for="spot in freeSpots" :key="spot.id">
              <span class="spot-id">{{ spot.id }}</span>
              <span class="spot-meta">
                зона {{ spot.zone ?? '—' }},
                ряд {{ spot.row ?? '—' }},
                место {{ spot.col ?? '—' }}
              </span>
            </li>
          </ul>
        </div>

        <div class="panel-card">
          <h3>Техническое состояние</h3>

          <dl class="tech-list">
            <div>
              <dt>Последнее обновление</dt>
              <dd>{{ lastUpdatedLabel }}</dd>
            </div>

            <div>
              <dt>Источник</dt>
              <dd>{{ occupancy?.source_type || layout?.camera?.source_type || '—' }}</dd>
            </div>

            <div>
              <dt>Камера</dt>
              <dd>{{ layout?.camera?.id || occupancy?.camera_id || '—' }}</dd>
            </div>

            <div>
              <dt>Polling</dt>
              <dd>{{ pollMs }} мс</dd>
            </div>
          </dl>
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import apiClient from '../services/api-client'
import ParkingMap from '../components/map/ParkingMap.vue'

const parkingId = ref('parking_a')

const layout = ref(null)
const occupancy = ref(null)
const loading = ref(false)
const error = ref(null)
const lastUpdatedAt = ref(null)

const pollMs = Number(import.meta.env.VITE_PARKING_POLL_MS || 2000)

let pollTimer = null

const parkingName = computed(() => {
  return layout.value?.parking?.name || layout.value?.parking?.id || parkingId.value
})

const summary = computed(() => {
  return occupancy.value?.summary || {
    total: layout.value?.spots?.length || 0,
    occupied: 0,
    free: 0,
    unknown: layout.value?.spots?.length || 0,
  }
})

const occupancyBySpotId = computed(() => {
  const map = new Map()

  if (!occupancy.value || !Array.isArray(occupancy.value.spots)) {
    return map
  }

  occupancy.value.spots.forEach((item) => {
    map.set(item.spot_id, item)
  })

  return map
})

const freeSpots = computed(() => {
  if (!layout.value || !Array.isArray(layout.value.spots)) {
    return []
  }

  return layout.value.spots.filter((spot) => {
    const state = occupancyBySpotId.value.get(spot.id)
    return state?.status === 'free'
  })
})

const lastUpdatedLabel = computed(() => {
  if (!lastUpdatedAt.value) {
    return 'нет данных'
  }

  return lastUpdatedAt.value.toLocaleTimeString('ru-RU')
})

async function loadState() {
  const response = await apiClient.get(`/api/parking-map/${parkingId.value}/state`)

  layout.value = response.data.layout
  occupancy.value = response.data.occupancy
  lastUpdatedAt.value = new Date()
}

async function loadOccupancy() {
  if (!layout.value) {
    return
  }

  try {
    const response = await apiClient.get(`/api/parking-map/${parkingId.value}/occupancy`)
    occupancy.value = response.data
    lastUpdatedAt.value = new Date()
  } catch (err) {
    console.error('Не удалось обновить occupancy:', err)
  }
}

async function reloadState() {
  stopPolling()

  loading.value = true
  error.value = null

  try {
    await loadState()
    startPolling()
  } catch (err) {
    console.error(err)
    error.value = 'Не удалось загрузить цифровую карту парковки. Проверь backend API и наличие layout.json / occupancy.json.'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()

  pollTimer = window.setInterval(() => {
    loadOccupancy()
  }, pollMs)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  reloadState()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.main-view {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(0, 229, 160, 0.12), transparent 32%),
    #0b0f17;
  color: #f2f5f8;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 22px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #00e5a0;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 700;
}

h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.15;
}

.subtitle {
  margin: 10px 0 0;
  color: #9aa4b2;
}

.parking-selector {
  min-width: 260px;
  padding: 14px;
  border: 1px solid #202838;
  border-radius: 16px;
  background: rgba(16, 20, 30, 0.82);
}

.parking-selector label {
  display: block;
  margin-bottom: 8px;
  color: #8c98aa;
  font-size: 12px;
}

.parking-selector input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #2b3445;
  border-radius: 10px;
  background: #0e131d;
  color: #fff;
  margin-bottom: 10px;
}

.parking-selector button {
  width: 100%;
  border: none;
  border-radius: 10px;
  padding: 10px 12px;
  background: #00e5a0;
  color: #06100c;
  font-weight: 700;
  cursor: pointer;
}

.status-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.status-card {
  padding: 16px;
  border: 1px solid #202838;
  border-radius: 16px;
  background: rgba(16, 20, 30, 0.82);
}

.status-card span {
  display: block;
  color: #8c98aa;
  font-size: 12px;
  margin-bottom: 8px;
}

.status-card strong {
  font-size: 28px;
}

.status-card.free strong {
  color: #46c864;
}

.status-card.occupied strong {
  color: #e64646;
}

.status-card.unknown strong {
  color: #aaa;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
  align-items: stretch;
}

.map-card,
.panel-card,
.message-card {
  border: 1px solid #202838;
  border-radius: 18px;
  background: rgba(16, 20, 30, 0.88);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22);
}

.map-card {
  padding: 18px;
  min-height: 680px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.card-header h2 {
  margin: 0 0 6px;
}

.card-header p {
  margin: 0;
  color: #8c98aa;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #aeb7c6;
  font-size: 12px;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}

.dot.free {
  background: #46c864;
}

.dot.occupied {
  background: #e64646;
}

.dot.unknown {
  background: #999;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.panel-card {
  padding: 18px;
}

.panel-card h3 {
  margin: 0 0 14px;
}

.empty-list {
  color: #8c98aa;
  font-size: 14px;
  line-height: 1.5;
}

.spots-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 430px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.spots-list li {
  padding: 10px 12px;
  border: 1px solid #202838;
  border-radius: 12px;
  background: #0e131d;
}

.spot-id {
  display: block;
  color: #46c864;
  font-weight: 700;
  margin-bottom: 4px;
}

.spot-meta {
  color: #8c98aa;
  font-size: 12px;
}

.tech-list {
  margin: 0;
}

.tech-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #202838;
}

.tech-list div:last-child {
  border-bottom: none;
}

.tech-list dt {
  color: #8c98aa;
}

.tech-list dd {
  margin: 0;
  color: #fff;
  text-align: right;
  word-break: break-word;
}

.message-card {
  padding: 22px;
  color: #aeb7c6;
}

.message-card.error {
  color: #ff7777;
}

@media (max-width: 980px) {
  .hero {
    flex-direction: column;
  }

  .parking-selector {
    width: 100%;
  }

  .status-row {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .map-card {
    min-height: 520px;
  }
}

@media (max-width: 560px) {
  .main-view {
    padding: 14px;
  }

  h1 {
    font-size: 24px;
  }

  .status-row {
    grid-template-columns: 1fr;
  }

  .card-header {
    flex-direction: column;
  }
}
</style>