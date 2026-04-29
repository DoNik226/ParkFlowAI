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
        <div class="map-box">
          <!-- <div class="zoom-controls">
            <button @click="zoomIn">+</button>
            <button @click="zoomOut">-</button>
          </div> -->

          <div v-if="isLoading" class="map-state-message">
            Загрузка цифровой карты...
          </div>

          <div v-else-if="error" class="map-state-message error">
            {{ error }}
          </div>

          <ParkingMap
            v-else
            :layout="layout"
            :occupancy="occupancyState"
            @select-spot="selectSpot"
          />
        </div>

        <!-- <button class="route-btn" @click="buildRouteForSelected">
          Построить маршрут
        </button> -->
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
              <span>{{ selectedEntrance || '№ въезда' }}</span>

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
                :key="entrance"
                class="dropdown-item"
              >
                <span>{{ entrance }}</span>

                <input
                  type="radio"
                  :checked="selectedEntrance === entrance"
                  @change="selectEntrance(entrance)"
                >
              </div>

              <button class="refresh" @click.stop="reloadState">
                <img src="../assets/img/refresh.png" alt="Обновить" width="20" height="20">
              </button>
            </div>
          </div>
        </div>

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
import ParkingMap from '@/components/map/ParkingMap.vue'

const route = useRoute()
const router = useRouter()

function goAdminHome() {
  router.push('/admin')
}

const pollMs = Number(import.meta.env.VITE_PARKING_POLL_MS || 2000)

const parkings = ref([
  {
    id: 'parking_a',
    name: 'Парковка A',
  },
])

const entrances = ref(['1'])

const selectedParkingId = ref(String(route.query.parking_id || 'parking_a'))
const selectedEntrance = ref('1')
const selectedSpot = ref(null)

const layout = ref(null)
const occupancyState = ref(null)
const isLoading = ref(false)
const error = ref(null)

const showParking = ref(false)
const showEntrance = ref(false)
const showLogoutModal = ref(false)

const isAdmin = computed(() => {
  return localStorage.getItem('user_role') === 'admin'
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

let pollTimer = null

const selectedParkingName = computed(() => {
  return parkings.value.find((parking) => parking.id === selectedParkingId.value)?.name || selectedParkingId.value
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

async function loadParkingsList() {
  try {
    const response = await parkingService.getAllParkings()

    if (Array.isArray(response) && response.length) {
      parkings.value = response.map((parking) => ({
        id: String(parking.id),
        name: parking.name || String(parking.id),
      }))
    }
  } catch (err) {
    console.warn('Не удалось загрузить список парковок, используется parking_a:', err)
  }
}

async function loadState() {
  const state = await parkingMapService.getState(selectedParkingId.value)

  layout.value = state.layout
  occupancyState.value = state.occupancy

  const parking = state.layout?.parking

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

  await loadEntrances()
}

async function loadEntrances() {
  try {
    const response = await parkingService.getEntrances(selectedParkingId.value)

    if (Array.isArray(response) && response.length) {
      entrances.value = response.map((entrance) => {
        if (typeof entrance === 'string' || typeof entrance === 'number') {
          return String(entrance)
        }

        return String(entrance.id ?? entrance.name ?? '1')
      })

      selectedEntrance.value = entrances.value[0]
    }
  } catch (err) {
    console.warn('Не удалось загрузить въезды, используется заглушка:', err)
    entrances.value = ['1']
    selectedEntrance.value = '1'
  }
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
  error.value = null

  try {
    await loadState()
    startPolling()
  } catch (err) {
    console.error('Ошибка загрузки цифровой карты:', err)
    error.value = 'Не удалось загрузить цифровую карту парковки'
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
  showParking.value = false

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
}

function selectSpot(spot) {
  selectedSpot.value = spot
}

function getSpotTitle(spot) {
  if (spot.label) return spot.label
  if (spot.number) return spot.number
  if (spot.id) return `Место ${spot.id.split('_').at(-1)}`
  return 'Место'
}

// function buildRouteForSelected() {
//   if (!selectedSpot.value) {
//     console.log('Сначала выберите свободное место')
//     return
//   }

//   console.log('Построить маршрут:', {
//     parking_id: selectedParkingId.value,
//     entrance: selectedEntrance.value,
//     spot: selectedSpot.value,
//   })
// }

// function zoomIn() {
//   console.log('zoom in')
// }

// function zoomOut() {
//   console.log('zoom out')
// }

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