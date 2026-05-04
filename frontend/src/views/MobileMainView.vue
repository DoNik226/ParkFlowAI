<template>
  <div class="mobile-container">
    <div class="map-area">
      <div v-if="isLoading" class="map-state-message">
        Загрузка карты...
      </div>

      <div v-else-if="mapError" class="map-state-message error">
        {{ mapError }}
      </div>

      <div
        v-else
        ref="mapViewportRef"
        class="mobile-map-viewport"
        @pointerdown="startMobileMapGesture"
        @pointermove="moveMobileMapGesture"
        @pointerup="endMobileMapGesture"
        @pointercancel="endMobileMapGesture"
        @pointerleave="endMobileMapGesture"
      >
        <div
          class="mobile-map-pan-layer"
          :class="{ panning: isMapPanning }"
          :style="mobileMapTransformStyle"
        >
          <ParkingMap
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

      <div class="load-bar">
        Загруженность: {{ occupancyPercent }}%
      </div>

      <div v-if="actionError" class="action-error">
        {{ actionError }}
      </div>
    </div>

    <div class="mobile-bottom-panel">
      <button class="mobile-bottom-btn logout" title="Выйти" @click="openLogoutModal">
        <img src="../assets/img/sign-out-black.png" alt="Выйти">
      </button>

      <button class="mobile-route-btn" @click="buildRouteForSelected">
        Маршрут
      </button>

      <button class="mobile-bottom-btn mobile-menu-btn" title="Меню" @click="openMenu">
        ☰
      </button>
    </div>

    <div class="menu" :class="{ open: menuOpen }">
      <div class="menu-header" @click="closeMenu">
        <img class="back-icon" src="../assets/img/back.png" alt="Назад">
        <span>Сохранить и выйти</span>
      </div>

      <div class="dropdowns">
        <div class="dropdown">
          <div class="dropdown-header" @click="toggleParking">
            <span>{{ selectedParkingName || 'Парковка' }}</span>

            <img
              src="../assets/img/down-arrow.png"
              class="arrow"
              :class="{ rotate: showParking }"
              alt=""
            >
          </div>

          <div v-if="showParking" class="dropdown-body">
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
          </div>
        </div>

        <div class="dropdown">
          <div class="dropdown-header" @click="toggleEntrance">
            <span>{{ selectedEntranceLabel || '№ въезда' }}</span>

            <img
              src="../assets/img/down-arrow.png"
              class="arrow"
              :class="{ rotate: showEntrance }"
              alt=""
            >
          </div>

          <div v-if="showEntrance" class="dropdown-body">
            <div
              v-for="entrance in entrances"
              :key="entrance.id"
              class="dropdown-item"
            >
              <span>{{ entrance.name }}</span>

              <input
                type="radio"
                :checked="selectedEntrance === entrance.id"
                @change="selectEntrance(entrance.id)"
              >
            </div>
          </div>
        </div>
      </div>

      <div class="spots">
        <h3>Свободные места</h3>

        <div class="spots-list">
          <button
            v-for="spot in freeSpots"
            :key="spot.id"
            class="spot-btn"
            :class="{ active: selectedSpot?.id === spot.id }"
            @click="selectSpotFromMenu(spot)"
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

  <div v-if="showLogoutModal" class="modal" @click="cancelLogout">
    <div class="modal-content" @click.stop>
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
import { parkingService } from '@/services/parking'
import { parkingMapService } from '@/services/parking-map'
import ParkingMap from '@/components/map/ParkingMap.vue'

const route = useRoute()
const router = useRouter()

const pollMs = Number(import.meta.env.VITE_PARKING_POLL_MS || 2000)

const parkings = ref([])
const entrances = ref([])

const selectedParkingId = ref(route.query.parking_id ? String(route.query.parking_id) : '')
const selectedEntrance = ref(null)
const selectedSpot = ref(null)

const layout = ref(null)
const mapData = ref(null)
const occupancyState = ref(null)
const routePath = ref([])

const isLoading = ref(false)
const mapError = ref('')
const actionError = ref('')

const menuOpen = ref(false)
const showParking = ref(false)
const showEntrance = ref(false)
const showLogoutModal = ref(false)

const mapViewportRef = ref(null)

const mapScale = ref(0.65)
const minMapScale = 0.4
const maxMapScale = 4

const mapPan = ref({
  x: 0,
  y: 80,
})

const mapPanStart = ref({
  x: 0,
  y: 0,
})

const mapPanBeforeDrag = ref({
  x: 0,
  y: 0,
})

const activePointers = ref(new Map())
const pinchStartDistance = ref(0)
const pinchStartScale = ref(1)

const pinchStartCenter = ref({
  x: 0,
  y: 0,
})

const pinchStartPan = ref({
  x: 0,
  y: 0,
})

const isMapPanning = ref(false)
const suppressMapSelection = ref(false)

let pollTimer = null

const mobileMapTransformStyle = computed(() => {
  return {
    transform: `translate3d(${mapPan.value.x}px, ${mapPan.value.y}px, 0) scale(${mapScale.value})`,
    transformOrigin: '0 0',
  }
})

const selectedParkingName = computed(() => {
  return parkings.value.find((parking) => parking.id === selectedParkingId.value)?.name || selectedParkingId.value
})

const selectedEntranceLabel = computed(() => {
  const entrance = entrances.value.find((item) => item.id === selectedEntrance.value)
  return entrance?.name || selectedEntrance.value
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
  const entrance = entrances.value.find((item) => item.id === selectedEntrance.value)

  if (!entrance) {
    return null
  }

  return entrance.vertex_id || entrance.id || null
})

function isInteractiveMapTarget(target) {
  return Boolean(
    target?.closest?.(
      'button, input, select, textarea, a, .load-bar, .action-error'
    )
  )
}

function getPointerDistance(pointerA, pointerB) {
  const dx = pointerA.x - pointerB.x
  const dy = pointerA.y - pointerB.y

  return Math.sqrt(dx * dx + dy * dy)
}

function getPointerCenter(pointerA, pointerB) {
  return {
    x: (pointerA.x + pointerB.x) / 2,
    y: (pointerA.y + pointerB.y) / 2,
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function startMobileMapGesture(event) {
  if (isInteractiveMapTarget(event.target)) {
    return
  }

  if (event.pointerType === 'mouse' && event.button !== 0) {
    return
  }

  activePointers.value.set(event.pointerId, {
    x: event.clientX,
    y: event.clientY,
  })

  event.currentTarget?.setPointerCapture?.(event.pointerId)

  if (activePointers.value.size === 1) {
    isMapPanning.value = true
    suppressMapSelection.value = false

    mapPanStart.value = {
      x: event.clientX,
      y: event.clientY,
    }

    mapPanBeforeDrag.value = {
      x: mapPan.value.x,
      y: mapPan.value.y,
    }
  }

  if (activePointers.value.size === 2) {
    const pointers = Array.from(activePointers.value.values())
    const center = getPointerCenter(pointers[0], pointers[1])

    pinchStartDistance.value = getPointerDistance(pointers[0], pointers[1])
    pinchStartScale.value = mapScale.value

    pinchStartCenter.value = {
      x: center.x,
      y: center.y,
    }

    pinchStartPan.value = {
      x: mapPan.value.x,
      y: mapPan.value.y,
    }

    suppressMapSelection.value = true
  }
}

function moveMobileMapGesture(event) {
  if (!activePointers.value.has(event.pointerId)) {
    return
  }

  activePointers.value.set(event.pointerId, {
    x: event.clientX,
    y: event.clientY,
  })

  event.preventDefault()

  if (activePointers.value.size === 2) {
    const pointers = Array.from(activePointers.value.values())
    const currentDistance = getPointerDistance(pointers[0], pointers[1])
    const currentCenter = getPointerCenter(pointers[0], pointers[1])

    if (!pinchStartDistance.value) {
      return
    }

    const nextScale = clamp(
      pinchStartScale.value * (currentDistance / pinchStartDistance.value),
      minMapScale,
      maxMapScale,
    )

    const scaleRatio = nextScale / pinchStartScale.value

    mapScale.value = nextScale

    mapPan.value = {
      x:
        currentCenter.x -
        (pinchStartCenter.value.x - pinchStartPan.value.x) * scaleRatio,
      y:
        currentCenter.y -
        (pinchStartCenter.value.y - pinchStartPan.value.y) * scaleRatio,
    }

    suppressMapSelection.value = true
    return
  }

  if (activePointers.value.size === 1 && isMapPanning.value) {
    const dx = event.clientX - mapPanStart.value.x
    const dy = event.clientY - mapPanStart.value.y

    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
      suppressMapSelection.value = true
    }

    mapPan.value = {
      x: mapPanBeforeDrag.value.x + dx,
      y: mapPanBeforeDrag.value.y + dy,
    }
  }
}

function endMobileMapGesture(event) {
  activePointers.value.delete(event.pointerId)

  event.currentTarget?.releasePointerCapture?.(event.pointerId)

  if (activePointers.value.size === 0) {
    isMapPanning.value = false

    window.setTimeout(() => {
      suppressMapSelection.value = false
    }, 200)
  }

  if (activePointers.value.size === 1) {
    const pointer = Array.from(activePointers.value.values())[0]

    mapPanStart.value = {
      x: pointer.x,
      y: pointer.y,
    }

    mapPanBeforeDrag.value = {
      x: mapPan.value.x,
      y: mapPan.value.y,
    }

    pinchStartDistance.value = 0
    pinchStartScale.value = mapScale.value
  }
}

function resetMobileMapTransform() {
  mapScale.value = 0.65

  mapPan.value = {
    x: 0,
    y: 80,
  }

  activePointers.value.clear()
  pinchStartDistance.value = 0
  pinchStartScale.value = mapScale.value

  pinchStartCenter.value = {
    x: 0,
    y: 0,
  }

  pinchStartPan.value = {
    x: 0,
    y: 0,
  }

  isMapPanning.value = false
  suppressMapSelection.value = false
}

function openMenu() {
  menuOpen.value = true
}

function closeMenu() {
  menuOpen.value = false
}

function toggleParking() {
  showParking.value = !showParking.value
}

function toggleEntrance() {
  showEntrance.value = !showEntrance.value
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
  } catch (error) {
    console.error('Ошибка выхода:', error)
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_id')
    localStorage.removeItem('username')
    showLogoutModal.value = false
    router.push('/login')
  }
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
        path: route.path,
        query: {
          ...route.query,
          parking_id: selectedParkingId.value,
        },
      })
    }
  } catch (error) {
    console.error('Ошибка загрузки списка парковок:', error)
    parkings.value = []
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
}

function loadEntrancesFromMap() {
  const mapEntrances = mapData.value?.entrances

  if (Array.isArray(mapEntrances) && mapEntrances.length) {
    entrances.value = mapEntrances.map((entrance) => ({
      id: String(entrance.id),
      name: entrance.name || String(entrance.id),
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
  if (!selectedParkingId.value || !layout.value) return

  try {
    occupancyState.value = await parkingMapService.getOccupancy(selectedParkingId.value)
  } catch (error) {
    console.error('Ошибка обновления занятости:', error)
  }
}

async function reloadState() {
  stopPolling()

  isLoading.value = true
  mapError.value = ''
  actionError.value = ''

  try {
    if (!selectedParkingId.value) {
      mapError.value = 'Нет доступных парковок'
      return
    }

    await loadState()
    resetMobileMapTransform()
    startPolling()
  } catch (error) {
    console.error('Ошибка загрузки мобильной карты:', error)
    mapError.value = 'Не удалось загрузить карту парковки'
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

async function selectParking(parkingId) {
  selectedParkingId.value = String(parkingId)
  selectedSpot.value = null
  selectedEntrance.value = null
  routePath.value = []
  actionError.value = ''
  showParking.value = false

  router.replace({
    path: route.path,
    query: {
      ...route.query,
      parking_id: selectedParkingId.value,
    },
  })

  await reloadState()
}

function selectEntrance(entranceId) {
  selectedEntrance.value = String(entranceId)
  showEntrance.value = false
  routePath.value = []
  actionError.value = ''
}

function selectSpot(spot) {
  if (suppressMapSelection.value && !menuOpen.value) {
    return
  }

  selectedSpot.value = spot
  routePath.value = []
  actionError.value = ''
}

function selectSpotFromMenu(spot) {
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
    actionError.value = 'Выберите свободное место в меню'
    menuOpen.value = true
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
    actionError.value = 'Для выбранного места нет точки доступа'
    return
  }

  const path = findShortestPath(
    mapData.value.vertices,
    mapData.value.edges || [],
    startVertexId,
    targetVertex.id,
  )

  if (!path.length) {
    actionError.value = 'Маршрут не найден'
    return
  }

  routePath.value = path
  menuOpen.value = false
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

    if (currentId === null) break
    if (currentId === targetId) break

    unvisited.delete(currentId)

    getNeighbors(currentId, edges).forEach((neighbor) => {
      if (!unvisited.has(neighbor.id)) return

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
  },
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
.mobile-container {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  overflow: hidden;
  background: #10131a;
  isolation: isolate;
}

.map-area {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 78px;
  background: #10131a;
  overflow: hidden;
  z-index: 1;
}

.mobile-map-viewport {
  position: absolute;
  inset: 0;
  overflow: hidden;
  touch-action: none;
  user-select: none;
  z-index: 1;
}

.mobile-map-pan-layer {
  position: absolute;
  inset: 0;
  touch-action: none;
  user-select: none;
  cursor: grab;
  will-change: transform;
  transform-origin: 0 0;
  z-index: 1;
}

.mobile-map-pan-layer.panning {
  cursor: grabbing;
}

.mobile-map-pan-layer :deep(.parking-map) {
  touch-action: none;
}

.mobile-map-pan-layer :deep(.parking-map),
.mobile-map-pan-layer :deep(.map-svg) {
  overflow: visible;
}

.map-area :deep(.parking-map) {
  width: 100%;
  height: 100%;
  min-height: 0;
  border: none;
  border-radius: 0;
}

.map-area :deep(.map-svg) {
  height: 100%;
  min-height: 0;
}

.map-area :deep(.map-tools) {
  display: none !important;
}

.map-state-message {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: #64748b;
  background: #10131a;
  font-size: 16px;
  text-align: center;
  padding: 24px;
}

.map-state-message.error {
  color: #ef4444;
}

.load-bar {
  position: fixed;
  left: 12px;
  top: 12px;
  z-index: 3000;
  background: rgba(255, 255, 255, 0.94);
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid #dbeafe;
  color: #1f2937;
  font-size: 14px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.15);
  pointer-events: none;
}

.action-error {
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: 88px;
  z-index: 3000;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
  font-size: 13px;
}

.mobile-bottom-panel {
  position: fixed !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;

  width: 100vw;
  min-height: 78px;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom));

  display: flex !important;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 14px;

  background: #ffffff;
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.18);
  border-top: 1px solid #e5e7eb;

  z-index: 99999 !important;
  transform: none !important;
}

.mobile-route-btn {
  flex: 1;
  max-width: 230px;
  height: 52px;
  border-radius: 14px;
  background: #2d8fe3;
  color: white;
  border: none;
  font-size: 22px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  box-shadow: 0 6px 16px rgba(45, 143, 227, 0.28);
}

.mobile-bottom-btn {
  flex: 0 0 52px;
  width: 52px;
  height: 52px;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mobile-bottom-btn img {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.mobile-menu-btn {
  font-size: 30px;
  line-height: 1;
  color: #111827;
}

.menu {
  position: fixed;
  top: 0;
  right: -100%;
  width: 100%;
  height: 100dvh;
  background: white;
  transition: 0.3s;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 100000;
}

.menu.open {
  right: 0;
}

.menu-header {
  background: #2d8fe3;
  min-height: 60px;
  display: flex;
  align-items: center;
  padding: 0 15px;
  border-bottom: 1px solid #1575cf;
  color: white;
  font-size: 20px;
}

.back-icon {
  background: none;
  border: none;
  margin-right: 20px;
  height: 38px;
}

.dropdowns {
  min-height: 54px;
  display: flex;
}

.dropdown {
  flex: 1;
  border-right: 1px solid #1575cf;
  position: relative;
  min-width: 0;
}

.dropdown:last-child {
  border-right: none;
}

.dropdown-header {
  height: 54px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #2673e6;
  color: #fff;
  gap: 8px;
}

.dropdown-header span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  width: 16px;
  height: 16px;
  transition: transform 0.2s;
}

.arrow.rotate {
  transform: rotate(180deg);
}

.dropdown-body {
  position: absolute;
  top: 100%;
  width: 100%;
  max-height: 160px;
  overflow-y: auto;
  background: #f8fafc;
  border: 1px solid #1575cf;
  z-index: 10;
}

.dropdown-item {
  padding: 12px 10px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid #dbeafe;
  color: #1f2937;
}

.dropdown-item span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.spots {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 28px 18px 20px;
}

.spots h3 {
  justify-content: center;
  display: flex;
  color: #2689e6;
  align-items: center;
  font-size: 26px;
  margin: 0 0 18px;
}

.spots-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px;
}

.spot-btn {
  width: 100%;
  min-height: 76px;
  padding: 10px;
  margin-bottom: 10px;
  border: none;
  border-radius: 14px;
  background: #2d8fe3;
  color: #fff;
  box-shadow: 0 6px 16px rgba(45, 143, 227, 0.22);
}

.spot-btn.active {
  outline: 3px solid #fbbf24;
}

.spot-number {
  font-size: 22px;
  font-weight: 800;
}

.spot-distance {
  margin-top: 4px;
  font-size: 14px;
}

.empty-spots {
  padding: 20px;
  color: #64748b;
  text-align: center;
  font-size: 14px;
}

.modal {
  position: fixed;
  inset: 0;
  z-index: 200000;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.45);
}

.modal-content {
  width: min(320px, calc(100vw - 32px));
  padding: 24px;
  border-radius: 18px;
  background: white;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.25);
  text-align: center;
}

.modal-content p {
  color: #2689e6;
  font-size: 18px;
  margin: 0 0 18px;
}

.modal-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.confirm-btn,
.cancel-btn {
  min-width: 90px;
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  color: white;
  font-weight: 700;
}

.confirm-btn {
  background: #439aeb;
}

.cancel-btn {
  background: #eb5743;
}

@media (max-height: 650px) {
  .map-area {
    bottom: 68px;
  }

  .mobile-bottom-panel {
    min-height: 68px;
    padding-top: 8px;
    padding-bottom: calc(8px + env(safe-area-inset-bottom));
  }

  .mobile-route-btn,
  .mobile-bottom-btn {
    height: 48px;
  }

  .mobile-bottom-btn {
    flex-basis: 48px;
    width: 48px;
  }

  .spots {
    padding-top: 18px;
  }

  .spots h3 {
    font-size: 22px;
    margin-bottom: 12px;
  }

  .spot-btn {
    min-height: 66px;
  }
}
</style>