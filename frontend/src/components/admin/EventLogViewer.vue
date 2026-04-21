<template>
  <div class="log-page" ref="rootRef">

    <div class="table-container">
      <table class="log-table">
        <thead>
          <tr>

            <!-- ОБЪЕКТ -->
            <th>
              Объект

              <button
                class="icon"
                :class="{ active: showObjectDropdown }"
                @click.stop="toggle('object')"
              >
                ▼
              </button>

              <div v-if="showObjectDropdown" class="dropdown">
                <div
                  v-for="item in objectOptions"
                  :key="item.value"
                  :class="{ active: selectedObject === item.value }"
                  @click="setObjectFilter(item.value)"
                >
                  {{ item.label }}
                </div>
              </div>
            </th>

            <!-- ПАРКОВКА -->
            <th v-if="selectedObject === 'camera'">
              Парковка

              <button
                class="icon"
                :class="{ active: showParkingDropdown }"
                @click.stop="toggle('parking')"
              >
                ▼
              </button>

              <div v-if="showParkingDropdown" class="dropdown">
                <div
                  @click="setParkingFilter('')"
                  :class="{ active: !selectedParking }"
                >
                  Все
                </div>

                <div
                  v-for="p in uniqueParkings"
                  :key="p"
                  :class="{ active: selectedParking === p }"
                  @click="setParkingFilter(p)"
                >
                  {{ p }}
                </div>
              </div>
            </th>

            <!-- ДАТА -->
            <th>
              Дата и время

              <button class="icon" @click.stop="toggle('date')">
                <svg width="16" height="16" viewBox="0 0 24 24">
                  <path fill="currentColor"
                    d="M7 2h2v2h6V2h2v2h3v18H4V4h3V2zm13 8H4v10h16V10z"/>
                </svg>
              </button>

              <div v-if="showDateFilter" class="dropdown date-popup">
                <div class="field">
                  <label>От</label>
                  <input type="datetime-local" v-model="dateFrom" />
                </div>

                <div class="field">
                  <label>До</label>
                  <input type="datetime-local" v-model="dateTo" />
                </div>

                <div class="actions">
                  <button @click="dateFrom = ''; dateTo = ''">Сбросить</button>
                </div>
              </div>
            </th>

            <!-- ОПИСАНИЕ -->
            <th>
              Описание

              <button class="icon" @click.stop="toggle('search')">
                <svg width="16" height="16" viewBox="0 0 24 24">
                  <path fill="currentColor"
                    d="M10 2a8 8 0 105.29 14.29l4.7 4.7l1.41-1.41l-4.7-4.7A8 8 0 0010 2z"/>
                </svg>
              </button>

              <div v-if="showSearch" class="dropdown">
                <div class="search-box">
                  <svg width="16" height="16" viewBox="0 0 24 24">
                    <path fill="currentColor"
                      d="M10 2a8 8 0 105.29 14.29l4.7 4.7l1.41-1.41l-4.7-4.7A8 8 0 0010 2z"/>
                  </svg>

                  <input v-model="searchText" placeholder="Поиск события..." />
                </div>
              </div>
            </th>

          </tr>
        </thead>

        <tbody>
          <tr v-for="(item, i) in filteredData" :key="i">
            <td>{{ item.objectName }}</td>

            <td v-if="selectedObject === 'camera'">
              {{ item.parkingName || '-' }}
            </td>

            <td>{{ item.date }}</td>
            <td>{{ item.description }}</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const logs = ref([
  { type: 'user', objectName: 'ivan', date: '2026-04-14 10:00', description: 'Вход' },
  { type: 'admin', objectName: 'admin1', date: '2026-04-14 11:00', description: 'Удаление' },
  {
    type: 'camera',
    objectName: 'CAM-01',
    parkingName: 'P1',
    date: '2026-04-14 12:00',
    description: 'Обнаружен авто'
  }
])

const rootRef = ref(null)


/* OPTIONS */
const objectOptions = [
  { value: 'all', label: 'Все' },
  { value: 'user', label: 'Пользователь' },
  { value: 'admin', label: 'Администратор' },
  { value: 'camera', label: 'Камера' }
]

/* STATE */
const selectedObject = ref('all')
const selectedParking = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const searchText = ref('')

/* DROPDOWNS */
const showObjectDropdown = ref(false)
const showParkingDropdown = ref(false)
const showDateFilter = ref(false)
const showSearch = ref(false)

/* TOGGLE */
const toggle = (type) => {

  const map = {
    object: showObjectDropdown,
    parking: showParkingDropdown,
    date: showDateFilter,
    search: showSearch
  }

  const target = map[type]

  const isOpen = target.value

  closeAll()

  // если было закрыто — открыть
  target.value = !isOpen
}

const closeAll = () => {
  showObjectDropdown.value = false
  showParkingDropdown.value = false
  showDateFilter.value = false
  showSearch.value = false
}


const handleClickOutside = (e) => {
  const el = rootRef.value
  if (!el) return

  if (!el.contains(e.target)) {
    closeAll()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

/* SETTERS */
const setObjectFilter = (val) => {
  selectedObject.value = val
  closeAll()
}

const setParkingFilter = (val) => {
  selectedParking.value = val
  closeAll()
}

/* DATA */
const uniqueParkings = computed(() => {
  return [...new Set(
    logs.value
      .filter(l => l.type === 'camera')
      .map(l => l.parkingName)
  )]
})

/* FILTER */
const filteredData = computed(() => {
  return logs.value.filter(item => {

    if (selectedObject.value !== 'all' && item.type !== selectedObject.value)
      return false

    if (selectedObject.value === 'camera' && selectedParking.value) {
      if (item.parkingName !== selectedParking.value) return false
    }

    if (searchText.value &&
      !item.description.toLowerCase().includes(searchText.value.toLowerCase()))
      return false

    const d = new Date(item.date)

    if (dateFrom.value && d < new Date(dateFrom.value)) return false
    if (dateTo.value && d > new Date(dateTo.value)) return false

    return true
  })
})
</script>

<style scoped>
.log-table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  border: 1px solid #e0e0e0;
  padding: 12px;
  text-align: center;
  position: relative;
}

th {
  background: #f9fafb;
  font-weight: 600;
}

/* ICON */
.icon {
  margin-left: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  border: none;
  background: none;
  transition: 0.2s;
}

.icon.active {
  transform: rotate(180deg);
}

/* КНОПКИ ФИЛЬТРОВ */
.filter-btn {
  margin-left: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: 0.2s;
}

.filter-btn:hover {
  background: #eef2ff;
}

/* DROPDOWN */
.dropdown {
  position: absolute;
  top: 44px;
  left: 50%;
  transform: translateX(-50%);

  min-width: 240px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(0,0,0,0.12);

  padding: 12px;
  z-index: 100;

  animation: fade 0.15s ease;
}

/* ПУНКТЫ */
.dropdown div {
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
}

.dropdown div:hover {
  background: #f4f7ff;
}

.dropdown .active {
  background: #3B66F4;
  color: white;
}

/* ПОЛЯ */
.field {
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}

.field label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.field input {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #dcdcdc;
  transition: 0.2s;
}

.field input:focus {
  border-color: #3B66F4;
  box-shadow: 0 0 0 2px rgba(59,102,244,0.15);
  outline: none;
}

/* ПОИСК */
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;

  border: 1px solid #dcdcdc;
  border-radius: 8px;
  padding: 8px 10px;
}

.search-box input {
  border: none;
  outline: none;
  width: 100%;
}

/* ACTIONS */
.actions {
  display: flex;
  justify-content: flex-end;
}

.actions button {
  border: none;
  background: #f3f4f6;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.actions button:hover {
  background: #e5e7eb;
}

/* ROWS */
tbody tr:nth-child(even) {
  background: #fafafa;
}

/* ANIMATION */
@keyframes fade {
  from {
    opacity: 0;
    transform: translate(-50%, -5px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}
</style>