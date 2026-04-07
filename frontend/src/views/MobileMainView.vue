<template>
  <div class="mobile-container">

    <!-- MAP -->
    <div class="map-area">
      <div class="map-placeholder">Карта</div>

      <div class="load-bar">
        Загруженность: 64%
      </div>

      <div class="zoom-controls">
        <button>+</button>
        <button>-</button>
      </div>
    </div>

    <!-- BOTTOM PANEL -->
    <div class="bottom-panel">
      <button class="icon-btn-mobile">
        <img src="../assets/img/sign-out.png"/>
      </button>

      <button class="route-btn-mobile">Маршрут</button>

      <button class="icon-btn-mobile" @click="openMenu">☰</button>
    </div>

    <!-- MENU -->
    <div class="menu" :class="{ open: menuOpen }">

      <!-- HEADER -->
      <div class="menu-header">
        <button class="back-mobile" @click="closeMenu">
            <img src="../assets/img/back.png">
        </button>
        <span>Сохранить и выйти</span>
      </div>

      <!-- DROPDOWNS -->
      <div class="dropdowns">

        <div class="dropdown">
          <div class="dropdown-header" @click="toggleParking">
            <span>Парковка</span>
            <span>{{ showParking ? '▲' : '▼' }}</span>
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
            <span>{{ showEntrance ? '▲' : '▼' }}</span>
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
            {{ spot.name }}
          </button>
        </div>
      </div>

    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'

const menuOpen = ref(false)

const openMenu = () => menuOpen.value = true
const closeMenu = () => menuOpen.value = false

const showParking = ref(false)
const showEntrance = ref(false)

const toggleParking = () => showParking.value = !showParking.value
const toggleEntrance = () => showEntrance.value = !showEntrance.value

const parkings = ['Парковка 1', 'Парковка 2', 'Парковка 3', 'Парковка 4']
const entrances = ['1', '2', '3', '4']

const selectedParking = ref(null)
const selectedEntrance = ref(null)

const spots = ref([
  { id: 1, name: 'A1' },
  { id: 2, name: 'A2' },
  { id: 3, name: 'A3' },
  { id: 4, name: 'B1' },
  { id: 5, name: 'B2' }
])

const selectedSpot = ref(null)
const selectSpot = (id) => selectedSpot.value = id
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
  border-radius: 8px;
  border: 1px solid black;
}

.zoom-controls {
  position: absolute;
  right: 10px;
  top: 50%;
  display: flex;
  flex-direction: column;
}

.zoom-controls button {
  width: 40px;
  height: 40px;
  margin: 4px 0;
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
  background: #439AEB;
  color: white;
  border: none;
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
  border: 1px solid black;
  border-radius: 10px;
  background: grey;
  display: flex;
  align-items: center;
  justify-content: center;

}

.icon-btn-mobile img {
  width: 34px;        
  height: 34px;
  object-fit: contain;
  display: block;
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
  border-bottom: 1px solid #ccc;
  color: white;
}

.back-mobile {
    background: none;
    border: none;
    margin-right: 20px;
}

.back-mobile img {
    height: 40px;
    width: 40px;
}

/* DROPDOWNS */
.dropdowns {
  height: 50px;
  display: flex;
}

.dropdown {
  flex: 1;
  border-right: 1px solid #eee;
  position: relative;
}

.dropdown:last-child {
  border-right: none;
}

.dropdown-header {
  padding: 15px;
  display: flex;
  justify-content: space-between;
}

/* FIXED DROPDOWN SIZE */
.dropdown-body {
  position: absolute;
  top: 100%;
  width: 100%;
  height: 100px;
  overflow-y: auto;
  background: white;
  border: 1px solid #ccc;
  z-index: 10;
}

.dropdown-item {
  padding: 12px 15px;
  display: flex;
  justify-content: space-between;
}

/* SPOTS */
.spots {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 80px 10px 0 10px;
}

.spots h3 {
    justify-content: center;
    display: flex;
    color: #439AEB;
    align-items: center;
    font-size: 28px;
}

.spots-list {
  flex: 1;
  overflow-y: auto;
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