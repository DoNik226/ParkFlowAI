<template>
  <div class="main-container">
    <header class="header">
      <div class="logo">ParkFlow AI</div>

      <div class="load-box">
        Загруженность: {{ occupancyPercent }}%
      </div>

      <div class="user-info">
        <span>{{ userLabel }}</span>

        <button
          v-if="isAdmin"
          class="logout"
          title="Назад в админ-меню"
          @click="goAdminHome"
        >
          <img src="../assets/img/back.png" alt="Назад" width="30" height="30">
        </button>

        <button
          v-else
          class="logout"
          title="Выйти"
          @click="openLogoutModal"
        >
          <img src="../assets/img/sign-out.png" alt="Выход" width="30" height="30">
        </button>
      </div>
    </header>

    <div class="content">
      <div class="map-section">
        <div v-if="showVideoDetectorControls" class="detector-panel">
          <div>
            <b>Тестовое видео</b>
            <span>
              {{ detectorActive ? 'детекция запущена' : 'детекция остановлена' }}
            </span>
          </div>

          <button
            v-if="!detectorActive"
            :disabled="detectorLoading"
            @click="startVideoDetector"
          >
            {{ detectorLoading ? 'Запуск...' : 'Старт видео' }}
          </button>

          <button
            v-else
            class="danger"
            :disabled="detectorLoading"
            @click="stopVideoDetector"
          >
            {{ detectorLoading ? 'Остановка...' : 'Стоп видео' }}
          </button>
        </div>

        <div v-if="actionError" class="action-error">
          {{ actionError }}
        </div>

        <div class="map-box">
          <div v-if="isLoading" class="map-state-message">
            Загрузка цифровой карты...
          </div>

          <div v-else-if="mapError" class="map-state-message error">
            {{ mapError }}
          </div>

          <ParkingMap
            v-else
            :layout="layout"
            :occupancy="occupancyState"
            :map-data="mapData"
            :route-path="routePath"
            :selected-spot-id="selectedSpot?.id || null"
            :selected-entrance-id="selectedEntranceVertexId"
            @select-spot="selectSpot"
          />
        </div>
      </div>

      <div class="control-panel">
        <div class="dropdowns">
          <div class="dropdown">
            <div
              class="dropdown-header left"
              :class="{ open: showParking }"
              @click="toggleParking"
            >
              <span>{{ selectedParkingName || 'Парковки' }}</span>

              <img
                src="../assets/img/down-arrow.png"
                class="arrow"
                :class="{ rotate: showParking }"
                alt=""
              >
            </div>

            <div
              v-if="showParking"
              class="dropdown-body left-body"
              :class="{ 'both-open-left': showParking && showEntrance }"
            >
              <div
                v-for="parking in parkings"
                :key="parking.id"
                class="dropdown-item"
              >
                <span>{{ parking.name }}</span>

                <input
                  type="radio"
                  :checked="selectedParkingId === parking.id"
                  @change="selectParking(parking.id)"
                >
              </div>

              <button class="refresh" @click.stop="reloadState">
                <img src="../assets/img/refresh.png" alt="Обновить" width="20" height="20">
              </button>
            </div>
          </div>

          <div class="dropdown">
            <div
              class="dropdown-header right"
              :class="{ open: showEntrance }"
              @click="toggleEntrance"
            >
              <span>{{ selectedEntranceLabel || '№ въезда' }}</span>

              <img
                src="../assets/img/down-arrow.png"
                class="arrow"
                :class="{ rotate: showEntrance }"
                alt=""
              >
            </div>

            <div
              v-if="showEntrance"
              class="dropdown-body right-body"
              :class="{ 'both-open-right': showParking && showEntrance }"
            >
              <div
                v-for="entrance in entrances"
                :key="typeof entrance === 'string' ? entrance : entrance.id"
                class="dropdown-item"
              >
                <span>{{ typeof entrance === 'string' ? entrance : entrance.name }}</span>

                <input
                  type="radio"
                  :checked="selectedEntrance === (typeof entrance === 'string' ? entrance : entrance.id)"
                  @change="selectEntrance(typeof entrance === 'string' ? entrance : entrance.id)"
                >
              </div>

              <button class="refresh" @click.stop="reloadState">
                <img src="../assets/img/refresh.png" alt="Обновить" width="20" height="20">
              </button>
            </div>
          </div>
        </div>

        <button class="build-route-btn" @click="buildRouteForSelected">
          Построить маршрут
        </button>

        <div class="free-spots">
          <h3>Свободные места</h3>

          <div class="spots-list">
            <button
              v-for="spot in freeSpots"
              :key="spot.id"
              class="spot-btn"
              :class="{ selected: selectedSpot?.id === spot.id }"
              @click="selectSpot(spot)"
            >
              <div class="spot-number">
                {{ getSpotTitle(spot) }}
              </div>

              <div class="spot-distance">
                зона {{ spot.zone ?? '—' }},
                ряд {{ spot.row ?? '—' }},
                место {{ spot.col ?? '—' }}
              </div>
            </button>

            <div v-if="!freeSpots.length" class="empty-spots">
              Свободных мест нет или данные ещё не обновились
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="showLogoutModal" class="modal">
    <div class="modal-content">
      <p>Вы уверены, что хотите выйти?</p>

      <div class="modal-actions">
        <button class="cancel-btn" @click="cancelLogout">Нет</button>
        <button class="confirm-btn" @click="confirmLogout">Да</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authService } from '@/services/auth'
import { parkingMapService } from '@/services/parking-map'
import { parkingService } from '@/services/parking'
import { detectionService } from '@/services/detection'
import ParkingMap from '@/components/map/ParkingMap.vue'

const route = useRoute()
const router = useRouter()

const pollMs = Number(import.meta.env.VITE_PARKING_POLL_MS || 2000)

// const parkings = ref([
//   {
//     id: 'parking_a',
//     name: 'Парковка A',
//   },
// ])

// const entrances = ref([])
// const selectedParkingId = ref(String(route.query.parking_id || 'parking_a'))

const parkings = ref([])

const entrances = ref([])

const selectedParkingId = ref(route.query.parking_id ? String(route.query.parking_id) : '')

const selectedEntrance = ref(null)
const selectedSpot = ref(null)

const layout = ref(null)
const occupancyState = ref(null)
const mapData = ref(null)
const routePath = ref([])

const detectorStatus = ref(null)
const detectorLoading = ref(false)

const isLoading = ref(false)
const mapError = ref(null)
const actionError = ref('')

const showParking = ref(false)
const showEntrance = ref(false)
const showLogoutModal = ref(false)

let pollTimer = null

const isAdmin = computed(() => {
  return localStorage.getItem('user_role') === 'admin'
})

const showVideoDetectorControls = computed(() => {
  return detectorStatus.value?.controls_visible === true
})

const detectorActive = computed(() => {
  return detectorStatus.value?.active === true
})

const userLabel = computed(() => {
  const userId = localStorage.getItem('user_id')
  const username = localStorage.getItem('username')
  const role = localStorage.getItem('user_role')

  if (userId) {
    return `ID пользователя: ${userId}`
  }

  if (username) {
    return `Пользователь: ${username}`
  }

  if (role) {
    return `Роль: ${role}`
  }

  return 'Пользователь'
})

const selectedParkingName = computed(() => {
  return parkings.value.find((parking) => parking.id === selectedParkingId.value)?.name || selectedParkingId.value
})

const selectedEntranceLabel = computed(() => {
  const entrance = entrances.value.find((item) => {
    if (typeof item === 'string') {
      return item === selectedEntrance.value
    }

    return String(item.id) === String(selectedEntrance.value)
  })

  if (!entrance) {
    return selectedEntrance.value
  }

  if (typeof entrance === 'string') {
    return entrance
  }

  return entrance.name || entrance.id
})

const summary = computed(() => {
  return occupancyState.value?.summary || {
    total: layout.value?.spots?.length || 0,
    occupied: 0,
    free: 0,
    unknown: layout.value?.spots?.length || 0,
  }
})

const occupancyPercent = computed(() => {
  const total = Number(summary.value.total) || 0
  const occupied = Number(summary.value.occupied) || 0

  if (!total) return 0

  return Math.round((occupied / total) * 100)
})

const occupancyBySpotId = computed(() => {
  const map = new Map()

  if (!occupancyState.value || !Array.isArray(occupancyState.value.spots)) {
    return map
  }

  occupancyState.value.spots.forEach((item) => {
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

const selectedEntranceVertexId = computed(() => {
  const entrance = entrances.value.find((item) => {
    if (typeof item === 'string') {
      return item === selectedEntrance.value
    }

    return String(item.id) === String(selectedEntrance.value)
  })

  if (!entrance || typeof entrance === 'string') {
    return null
  }

  return entrance.vertex_id || entrance.id || null
})

function goAdminHome() {
  router.push('/admin')
}

async function loadParkingsList() {
  try {
    const response = await parkingService.getAllParkings()

    if (Array.isArray(response) && response.length) {
      parkings.value = response.map((parking) => ({
        id: String(parking.id),
        name: parking.name || String(parking.id),
      }))

      const parkingFromUrl = route.query.parking_id ? String(route.query.parking_id) : ''

      const existsFromUrl = parkings.value.some((parking) => parking.id === parkingFromUrl)

      if (parkingFromUrl && existsFromUrl) {
        selectedParkingId.value = parkingFromUrl
        return
      }

      selectedParkingId.value = parkings.value[0].id

      router.replace({
        path: '/main',
        query: {
          ...route.query,
          parking_id: selectedParkingId.value,
        },
      })
    }
  } catch (err) {
    console.warn('Не удалось загрузить список парковок:', err)
    parkings.value = []
  }
}

async function loadDetectorStatus() {
  try {
    detectorStatus.value = await detectionService.getStatus(selectedParkingId.value)
  } catch (err) {
    console.warn('Не удалось получить статус детектора:', err)
    detectorStatus.value = null
  }
}

async function startVideoDetector() {
  detectorLoading.value = true
  actionError.value = ''

  try {
    await detectionService.start(selectedParkingId.value)
    await loadDetectorStatus()
  } catch (err) {
    console.error('Ошибка запуска детектора:', err)

    if (err.response?.status === 400) {
      actionError.value = 'Не удалось запустить детекцию: проверьте, что загружено тестовое видео и сохранён layout.'
    } else {
      actionError.value = 'Не удалось запустить детекцию видео'
    }
  } finally {
    detectorLoading.value = false
  }
}

async function stopVideoDetector() {
  detectorLoading.value = true
  actionError.value = ''

  try {
    await detectionService.stop(selectedParkingId.value)
    await loadDetectorStatus()
  } catch (err) {
    console.error('Ошибка остановки детектора:', err)
    actionError.value = 'Не удалось остановить детекцию видео'
  } finally {
    detectorLoading.value = false
  }
}

async function loadState() {
  const state = await parkingMapService.getState(selectedParkingId.value)

  layout.value = state.layout
  mapData.value = state.map
  occupancyState.value = state.occupancy

  const parking = state.layout?.parking || state.map?.parking

  if (parking?.id) {
    selectedParkingId.value = String(parking.id)
  }

  if (parking?.id && parking?.name) {
    const exists = parkings.value.some((item) => item.id === String(parking.id))

    if (!exists) {
      parkings.value.push({
        id: String(parking.id),
        name: parking.name,
      })
    }
  }

  loadEntrancesFromMap()
  await loadDetectorStatus()
}

function loadEntrancesFromMap() {
  const mapEntrances = mapData.value?.entrances

  if (Array.isArray(mapEntrances) && mapEntrances.length) {
    entrances.value = mapEntrances.map((entrance) => ({
      id: entrance.id,
      name: entrance.name || entrance.id,
      vertex_id: entrance.vertex_id || entrance.id,
    }))

    if (!selectedEntrance.value || !entrances.value.some((item) => item.id === selectedEntrance.value)) {
      selectedEntrance.value = entrances.value[0].id
    }

    return
  }

  entrances.value = [
    {
      id: '1',
      name: 'Въезд 1',
      vertex_id: null,
    },
  ]

  selectedEntrance.value = '1'
}

async function loadOccupancy() {
  if (!layout.value) return

  try {
    occupancyState.value = await parkingMapService.getOccupancy(selectedParkingId.value)
  } catch (err) {
    console.error('Ошибка обновления occupancy:', err)
  }
}

async function reloadState() {
  stopPolling()

  isLoading.value = true
  mapError.value = null
  actionError.value = ''

  try {
    if (!selectedParkingId.value) {
      mapError.value = 'Нет доступных парковок'
      return
    }

    await loadState()
    startPolling()
  } catch (err) {
    console.error('Ошибка загрузки цифровой карты:', err)
    mapError.value = 'Не удалось загрузить цифровую карту парковки'
  } finally {
    isLoading.value = false
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

function toggleParking() {
  showParking.value = !showParking.value
}

function toggleEntrance() {
  showEntrance.value = !showEntrance.value
}

async function selectParking(parkingId) {
  selectedParkingId.value = String(parkingId)
  selectedSpot.value = null
  selectedEntrance.value = null
  showParking.value = false
  routePath.value = []
  actionError.value = ''

  router.replace({
    path: '/main',
    query: {
      ...route.query,
      parking_id: selectedParkingId.value,
    },
  })

  await reloadState()
}

function selectEntrance(entrance) {
  selectedEntrance.value = String(entrance)
  showEntrance.value = false
  routePath.value = []
}

function selectSpot(spot) {
  selectedSpot.value = spot
  routePath.value = []
  actionError.value = ''
}

function getSpotTitle(spot) {
  if (spot.label) return spot.label
  if (spot.number) return spot.number
  if (spot.id) return `Место ${spot.id.split('_').at(-1)}`
  return 'Место'
}

function buildRouteForSelected() {
  actionError.value = ''
  routePath.value = []

  if (!selectedSpot.value) {
    actionError.value = 'Сначала выберите свободное место'
    return
  }

  if (!mapData.value || !Array.isArray(mapData.value.vertices)) {
    actionError.value = 'Цифровая карта ещё не построена'
    return
  }

  const startVertexId = selectedEntranceVertexId.value

  if (!startVertexId) {
    actionError.value = 'Для выбранного въезда нет точки графа'
    return
  }

  const targetVertex = mapData.value.vertices.find((vertex) => {
    return vertex.type === 'spot_access' && vertex.spot_id === selectedSpot.value.id
  })

  if (!targetVertex) {
    actionError.value = 'Для выбранного места нет точки доступа. Создайте точки мест в конструкторе карты.'
    return
  }

  const path = findShortestPath(
    mapData.value.vertices,
    mapData.value.edges || [],
    startVertexId,
    targetVertex.id
  )

  if (!path.length) {
    actionError.value = 'Маршрут не найден. Проверьте соединения графа в конструкторе карты.'
    return
  }

  routePath.value = path
}

function findShortestPath(vertices, edges, startId, targetId) {
  const vertexIds = vertices.map((vertex) => vertex.id)
  const distances = new Map()
  const previous = new Map()
  const unvisited = new Set(vertexIds)

  vertexIds.forEach((id) => {
    distances.set(id, Number.POSITIVE_INFINITY)
    previous.set(id, null)
  })

  distances.set(startId, 0)

  while (unvisited.size) {
    let currentId = null
    let currentDistance = Number.POSITIVE_INFINITY

    for (const id of unvisited) {
      const distance = distances.get(id)

      if (distance < currentDistance) {
        currentDistance = distance
        currentId = id
      }
    }

    if (currentId === null) {
      break
    }

    if (currentId === targetId) {
      break
    }

    unvisited.delete(currentId)

    const neighbors = getNeighbors(currentId, edges)

    neighbors.forEach((neighbor) => {
      if (!unvisited.has(neighbor.id)) {
        return
      }

      const nextDistance = currentDistance + neighbor.weight

      if (nextDistance < distances.get(neighbor.id)) {
        distances.set(neighbor.id, nextDistance)
        previous.set(neighbor.id, currentId)
      }
    })
  }

  if (distances.get(targetId) === Number.POSITIVE_INFINITY) {
    return []
  }

  const path = []
  let current = targetId

  while (current) {
    path.unshift(current)
    current = previous.get(current)
  }

  return path
}

function getNeighbors(vertexId, edges) {
  const neighbors = []

  edges.forEach((edge) => {
    const weight = Number(edge.length_meters) || 1

    if (edge.source === vertexId) {
      neighbors.push({
        id: edge.destination,
        weight,
      })
    }

    if (edge.is_bidirectional !== false && edge.destination === vertexId) {
      neighbors.push({
        id: edge.source,
        weight,
      })
    }
  })

  return neighbors
}

function openLogoutModal() {
  showLogoutModal.value = true
}

function cancelLogout() {
  showLogoutModal.value = false
}

async function confirmLogout() {
  try {
    await authService.logout()
  } catch (err) {
    console.error('Ошибка выхода:', err)
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_id')
    localStorage.removeItem('username')
    showLogoutModal.value = false
    router.push('/login')
  }
}

watch(
  () => route.query.parking_id,
  async (parkingId) => {
    if (!parkingId || String(parkingId) === selectedParkingId.value) {
      return
    }

    selectedParkingId.value = String(parkingId)
    selectedSpot.value = null
    selectedEntrance.value = null
    routePath.value = []
    await reloadState()
  }
)

onMounted(async () => {
  await loadParkingsList()
  await reloadState()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.map-section {
  min-width: 0;
}

.map-box {
  position: relative;
  width: 100%;
  height: 620px;
  overflow: hidden;
  border-radius: 18px;
}

.detector-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #dbeafe;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
}

.detector-panel div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.detector-panel b {
  color: #1f2937;
}

.detector-panel span {
  color: #6b7280;
  font-size: 14px;
}

.detector-panel button {
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  background: #2d8fe3;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.detector-panel button.danger {
  background: #ef4444;
}

.detector-panel button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-error {
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
  font-size: 14px;
}

.map-state-message {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 620px;
  color: #777;
  font-size: 18px;
  background: #10131a;
  border-radius: 16px;
}

.map-state-message.error {
  color: #e74c3c;
}

.build-route-btn {
  width: 100%;
  margin: 14px 0 18px;
  border: none;
  border-radius: 12px;
  padding: 13px 16px;
  background: #2d8fe3;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.build-route-btn:hover {
  background: #2279c6;
}

.empty-spots {
  padding: 16px;
  color: #777;
  font-size: 14px;
  text-align: center;
}

.spot-btn.selected {
  outline: 2px solid #2d8fe3;
}
</style>