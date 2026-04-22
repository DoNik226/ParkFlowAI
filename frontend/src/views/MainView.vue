<template>
  <div class="main-container">
    
    <!-- HEADER -->
    <header class="header">
      <div class="logo">ParkFlow AI</div>

      <div class="load-box">
        Загруженность: {{ occupancy }}%
      </div>

      <div class="user-info">
        <span>ID пользователя: {{ userId }}</span>
        <button class="logout" @click="openLogoutModal">
            <img src="../assets/img/sign-out.png" alt="Выход" width="30" height="30">
        </button>

      </div>
    </header>

    <!-- MAIN -->
    <div class="content">

      <!-- MAP AREA -->
      <div class="map-section">
        <div class="map-box">
          <div class="zoom-controls">
            <button>+</button>
            <button>-</button>
          </div>
        </div>

        <button class="route-btn">Построить маршрут</button>
      </div>

      <!-- RIGHT PANEL -->
      <div class="control-panel">

        <!-- DROPDOWNS -->
        <div class="dropdowns">

          <!-- Parking -->
          <div class="dropdown">
            <div 
              class="dropdown-header"
              :class="['left', { open: showParking }]"
              @click="toggleParking"
            >
              <span>Парковки</span>
              <img 
                src="../assets/img/down-arrow.png" 
                class="arrow"
                :class="{ rotate: showParking }"
              >
            </div>

            <div 
              v-if="showParking" 
              class="dropdown-body"
              :class="{
                'left-body': true,
                'both-open-left': showParking && showEntrance
            }"
            >
              <div 
                v-for="p in parkings" 
                :key="p" 
                class="dropdown-item"
              >
                <span>{{ p }}</span>
                <input 
                  type="radio" 
                  :checked="selectedParking === p" 
                  @change="selectParking(p)"
                >
              </div>

              <button class="refresh">
                <img src="../assets/img/refresh.png" alt="Обновить" width="20" height="20">
              </button>
            </div>
          </div>

          <!-- Entrance -->
          <div class="dropdown">
            <div 
              class="dropdown-header"
              :class="['right', { open: showEntrance }]"
              @click="toggleEntrance"
            >
              <span>№ въезда</span>
              <img 
                src="../assets/img/down-arrow.png" 
                class="arrow"
                :class="{ rotate: showEntrance }"
              >
            </div>

            <div 
              v-if="showEntrance" 
              class="dropdown-body"
              :class="{
                'right-body': true,
                'both-open-right': showParking && showEntrance
            }"
            >
              <div 
                v-for="e in entrances" 
                :key="e" 
                class="dropdown-item"
              >
                <span>{{ e }}</span>
                <input 
                  type="radio" 
                  :checked="selectedEntrance === e" 
                  @change="selectEntrance(e)"
                >
              </div>

              <button class="refresh">
                <img src="../assets/img/refresh.png" alt="Обновить" width="20" height="20">
              </button>
            </div>
          </div>

        </div>

        <div class="free-spots">
          <h3>Свободные места</h3>

          <div class="spots-list">
            <button 
              v-for="spot in spots" 
              :key="spot.id"
              class="spot-btn"
              @click="buildRoute(spot)"
            >
              <div class="spot-number">{{ spot.entrance }}</div>
              <div class="spot-distance">{{ spot.distance }} метров</div>
            </button>
          </div>
        </div>

      </div>

    </div>
  </div>
  <!-- LOGOUT MODAL -->
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
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { parkingService } from '@/services/parking'
import { mapService } from '@/services/map'
import { sseClient } from '@/services/sse-client'
import { authService } from '@/services/auth'

const router = useRouter()

// ===== МОДАЛЬНОЕ ОКНО ВЫХОДА =====
const showLogoutModal = ref(false)

const openLogoutModal = () => {
  showLogoutModal.value = true
}

const cancelLogout = () => {
  showLogoutModal.value = false
}

const confirmLogout = async () => {
  try {
    await authService.logout()  // Вызов API
  } catch (error) {
    console.error('Ошибка выхода:', error)
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_id')
    showLogoutModal.value = false
    router.push('/login')
  }
}

// ===== ДАННЫЕ ПАРКОВОК  =====
const showParking = ref(false)
const showEntrance = ref(false)

const parkings = ref([])           
const entrances = ref([])          
const spots = ref([])              
const occupancy = ref(0)          
const userId = ref(localStorage.getItem('user_id') || 'N/A')  // ← Из localStorage

const selectedParking = ref(null)
const selectedEntrance = ref(null)

// ===== SSE И ЗАГРУЗКА =====
const sseDisconnect = ref(null)
const isLoading = ref(false)

// ===== ЗАГРУЗКА ДАННЫХ ПАРКОВОК =====
const loadParkingData = async () => {
  isLoading.value = true
  try {
    const data = await parkingService.getAllParkings()
    parkings.value = data.map(p => p.name)
    
    if (data.length > 0) {
      const entrancesData = await parkingService.getEntrances(data[0].id)
      entrances.value = entrancesData.map(e => e.name)
      
      const freeSpots = await parkingService.getFreeSpots(data[0].id, entrancesData[0]?.id)
      spots.value = freeSpots
      
      const occupancyData = await parkingService.getParkingOccupancy(data[0].id)
      occupancy.value = occupancyData.occupancy_percentage
    }
  } catch (error) {
    console.error('Ошибка загрузки данных:', error)
  } finally {
    isLoading.value = false
  }
}

// ===== ПОДКЛЮЧЕНИЕ SSE-ОБНОВЛЕНИЙ =====
const connectSSE = () => {
  sseDisconnect.value = sseClient.connect((event) => {
    if (event.type === 'spot_status_changed') {
      loadParkingData()  // Перезагрузить при изменении статуса места
    }
  })
}

// ===== ВЫЗОВ ПРИ МОНТИРОВАНИИ =====
onMounted(() => {
  loadParkingData()
  connectSSE()
})

// ===== ОЧИСТКА ПРИ УХОДЕ СО СТРАНИЦЫ =====
onBeforeUnmount(() => {
  if (sseDisconnect.value) {
    sseDisconnect.value()  // Отключить SSE
  }
})

// ===== УПРАВЛЕНИЕ DROPDOWN =====
const toggleParking = () => {
  showParking.value = !showParking.value
}

const toggleEntrance = () => {
  showEntrance.value = !showEntrance.value
}

const selectParking = (p) => selectedParking.value = p
const selectEntrance = (e) => selectedEntrance.value = e

const applyParking = () => showParking.value = false
const applyEntrance = () => showEntrance.value = false

// ===== ПОСТРОЕНИЕ МАРШРУТА =====
const buildRoute = async (spot) => {
  try {
    const route = await mapService.buildRoute(selectedEntrance.value, spot.id)
    console.log('Маршрут построен:', route)
    // Здесь будет логика отображения маршрута на карте
  } catch (error) {
    console.error('Ошибка построения маршрута:', error)
  }
}
</script>
