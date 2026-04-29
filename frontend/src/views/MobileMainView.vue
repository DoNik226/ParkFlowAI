<template>
  <div class="mobile-container">

    <!-- MAP -->
    <div class="map-area">
      <div class="map-placeholder">Карта</div>

      <div class="load-bar">
        Загруженность: {{ occupancy }}%
      </div>

      <div class="zoom-controls">
        <button>+</button>
        <button>-</button>
      </div>
    </div>

    <!-- BOTTOM PANEL -->
    <div class="bottom-panel">
      <button class="logout" @click="openLogoutModal">
        <img src="../assets/img/sign-out-black.png"/>
      </button>

      <button class="route-btn-mobile">Маршрут</button>

      <button :style="{fontSize: '30px'}" class="icon-btn-mobile" @click="openMenu">☰</button>
    </div>

    <!-- MENU -->
    <div class="menu" :class="{ open: menuOpen }">

      <!-- HEADER -->
      <div class="menu-header" @click="closeMenu">
            <img class="back-icon" src="../assets/img/back.png">
        <span :style="{fontSize: '20px'}">Сохранить и выйти</span>
      </div>

      <!-- DROPDOWNS -->
      <div class="dropdowns">

        <div class="dropdown">
          <div class="dropdown-header" @click="toggleParking">
            <span>Парковка</span>
            <img 
                src="../assets/img/down-arrow.png" 
                class="arrow"
                :class="{ rotate: showParking }"
              >
          </div>

          <div v-if="showParking" class="dropdown-body">
            <div v-for="p in parkings" :key="p" class="dropdown-item">
              <span>{{ p }}</span>
              <input type="radio"
                     :checked="selectedParking === p"
                     @change="selectedParking = p" />
            </div>
          </div>
        </div>

        <div class="dropdown">
          <div class="dropdown-header" @click="toggleEntrance">
            <span>№ въезда</span>
            <img 
                src="../assets/img/down-arrow.png" 
                class="arrow"
                :class="{ rotate: showEntrance }"
              >
          </div>

          <div v-if="showEntrance" class="dropdown-body">
            <div v-for="e in entrances" :key="e" class="dropdown-item">
              <span>{{ e }}</span>
              <input type="radio"
                     :checked="selectedEntrance === e"
                     @change="selectedEntrance = e" />
            </div>
          </div>
        </div>

      </div>

      <!-- SPOTS -->
      <div class="spots">
        <h3>Свободные места</h3>

        <div class="spots-list">
          <button
            v-for="spot in spots"
            :key="spot.id"
            :class="['spot-btn', { active: selectedSpot === spot.id }]"
            @click="selectSpot(spot.id)"
          >
            <div class="spot-number">{{ spot.entrance }}</div>
            <div class="spot-distance">{{ spot.distance }} метров</div>
          </button>
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
    await authService.logout()  // Вызов API (раздел "Авторизация")
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

// ===== МЕНЮ =====
const menuOpen = ref(false)
const openMenu = () => menuOpen.value = true
const closeMenu = () => menuOpen.value = false

// ===== DROPDOWNS =====
const showParking = ref(false)
const showEntrance = ref(false)

const toggleParking = () => showParking.value = !showParking.value
const toggleEntrance = () => showEntrance.value = !showEntrance.value

// ===== ДАННЫЕ ПАРКОВОК (реактивные, данные с API) =====
const parkings = ref([])           // Было: ['Парковка 1', 'Парковка 2', ...]
const entrances = ref([])          // Было: ['1', '2', '3', '4']
const spots = ref([])              // Было: хардкод 5 объектов
const occupancy = ref(0)           // ← Новая переменная для загруженности
const selectedParking = ref(null)
const selectedEntrance = ref(null)
const selectedSpot = ref(null)

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

// ===== ВЫБОР МЕСТА =====
const selectSpot = (id) => selectedSpot.value = id

// ===== ПОСТРОЕНИЕ МАРШРУТА (через API) =====
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

<style scoped>
.mobile-container {
  height: 100dvh;
  overflow: hidden;
  position: relative;
}

/* MAP */
.map-area {
  position: absolute;
  inset: 0;
  background: #ddd;
}

.map-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.load-bar {
  position: absolute;
  display: flex;
  bottom: 80px;
  left: 30%;
  transform: translateX(-50%);
  background: white;
  padding: 6px 12px;
  border-radius: 10px;
  border: 1px solid #555252;
  opacity: 0.6;
}

.zoom-controls {
  position: absolute;
  right: 10px;
  top: 50%;
  display: flex;
  flex-direction: column;
}

.zoom-controls button {
  width: 45px;
  height: 45px;
  margin: 4px 0;
  border-radius: 24px;
  background: white;
  opacity: 0.7;
}

/* BOTTOM */
.bottom-panel {
  position: absolute;
  display: flex;
  flex-direction: row;
  bottom: 0;
  width: 100%;
  height: 70px;
  background: white;
  align-items: center; 
  justify-content: center;     
  gap: 16px;              
  padding: 0;
}

.route-btn-mobile {
  width: 190px;
  height: 50px; 
  border-radius: 10px;
  background: #D9D9D9;
  color: black;
  border: 1px solid #555252;
  font-size: 24px;
  line-height: normal;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.icon-btn-mobile {
  width: 50px;        
  height: 50px;               
  border: 1px solid #555252;
  border-radius: 10px;
  background: #D9D9D9;
  display: flex;
  align-items: center;
  justify-content: center;

}

.icon-btn-mobile img {
  width: 30px;        
  height: 30px;
  object-fit: contain;
  display: block;
}

.logout {
  width: 50px;        
  height: 50px;               
  border: 1px solid #555252;
  border-radius: 10px;
  background: #D9D9D9;
  display: flex;
  align-items: center;
  justify-content: center;

}

.logout img {
  width: 30px;        
  height: 30px;
  object-fit: contain;
  display: block;
}

/* .modal-content {
  border: 3px solid #376CFB;
} */

.modal-content p{
  color: #2689E6;
}

.confirm-btn{ 
  background: #439AEB;
}

.cancel-btn {
  background: #EB5743;
  color: white;
}

/* MENU */
.menu {
  position: fixed;
  top: 0;
  right: -100%;
  width: 100%;
  height: 100%;
  background: white;
  transition: 0.3s;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.menu.open {
  right: 0;
}

/* HEADER */
.menu-header {
  background: #2689E6;
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 15px;
  border-bottom: 1px solid #1575CF;
  color: white;
}

.back-icon {
    background: none;
    border: none;
    margin-right: 20px;
    height: 40px;
}


/* DROPDOWNS */
.dropdowns {
  height: 50px;
  display: flex;
}

.dropdown {
  flex: 1;
  border-right: 1px solid #1575CF;
  position: relative;
}

.dropdown:last-child {
  border-right: none;
}

.dropdown-header {
  padding: 15px;
  display: flex;
  justify-content: space-between;
  background: #2673E6;
}

/* FIXED DROPDOWN SIZE */
.dropdown-body {
  position: absolute;
  top: 100%;
  width: 100%;
  height: 100px;
  overflow-y: auto;
  background: #f5f7f7;
  border: 1px solid #1575CF;
  z-index: 10;
}

.dropdown-item {
  padding: 12px 15px;
  display: flex;
  justify-content: space-between;
  border: 1px solid #1575CF;
}

/* SPOTS */
.spots {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 80px 20px 0 10px;
}

.spots h3 {
    justify-content: center;
    display: flex;
    color: #2689E6;
    align-items: center;
    font-size: 28px;
    margin-left: 10px;
}

.spots-list {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
  padding-left:40px;
  padding-right: 40px;
}

.spot-btn {
  width: 100%;
  padding: 10px;
  height: 70px;
  margin-bottom: 6px;
}

.spot-btn.active {
  border: 2px solid blue;
}



/* ADAPT HEIGHT */
@media (max-height: 700px) {
  .dropdown-body {
    height: 90px;
  }
}

@media (max-height: 600px) {
  .dropdown-body {
    height: 70px;
  }
}
</style>