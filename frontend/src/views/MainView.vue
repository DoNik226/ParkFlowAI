<template>
  <div class="main-container">
    
    <!-- HEADER -->
    <header class="header">
      <div class="logo">ParkFlow AI</div>

      <div class="load-box">
        Загруженность: 64%
      </div>

      <div class="user-info">
        <span>ID пользователя: 12345</span>
        <button class="logout">
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
              Парковки ⌵
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
              № въезда ⌵
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
</template>

<script setup>
import { ref } from 'vue'

const showParking = ref(false)
const showEntrance = ref(false)

const parkings = ['P1', 'P2']
const entrances = ['1', '2']

const selectedParking = ref(null)
const selectedEntrance = ref(null)

const spots = ref([
  { id: 1, entrance: 30, distance: 20 },
  { id: 2, entrance: 18, distance: 24 },
  { id: 3, entrance: 32, distance: 26 },
  { id: 4, entrance: 40, distance: 35 },
  { id: 5, entrance: 42, distance: 38 }
])

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

const buildRoute = (spot) => {
  console.log('Маршрут до:', spot)
}
</script>

