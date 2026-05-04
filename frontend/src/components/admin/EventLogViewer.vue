<template>
  <div class="log-page" ref="rootRef">

    <div class="table-container">
      <div class="table-wrapper">
        <table class="log-table">
          <thead>
            <tr>

              <!-- ОБЪЕКТ -->
              <th class="col-object">
                Объект

                <button
                  class="icon"
                  :class="{ active: showObjectDropdown }"
                  @click.stop="toggle('object')"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24">
                    <path
                      d="M8 10l4 4 4-4"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
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
              <th v-if="selectedObject === 'camera'" class="col-parking">
                Парковка

                <button
                  class="icon"
                  :class="{ active: showParkingDropdown }"
                  @click.stop="toggle('parking')"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24">
                    <path
                      d="M8 10l4 4 4-4"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
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
              <th class="col-date">
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
                    <input
                      type="text"
                      v-model="dateFrom"
                      placeholder="2026-04-22 14:30"
                      @input="formatDateInput($event, 'from')"
                    />
                  </div>

                  <div class="field">
                    <label>До</label>
                    <input
                      type="text"
                      v-model="dateTo"
                      placeholder="2026-04-22 14:30"
                      @input="formatDateInput($event, 'to')"
                    />
                  </div>

                  <div class="actions">
                    <button @click="dateFrom = ''; dateTo = ''">Сбросить</button>
                  </div>
                </div>
              </th>

              <!-- ОПИСАНИЕ -->
              <th class="col-search">
                Описание

                <button class="icon search" @click.stop="toggle('search')">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <circle
                      cx="11"
                      cy="11"
                      r="7"
                      stroke="currentColor"
                      stroke-width="2"
                    />
                    <line
                      x1="16.65"
                      y1="16.65"
                      x2="21"
                      y2="21"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                    />
                  </svg>
                </button>

                <div v-if="showSearch" class="dropdown">
                  <div class="search-box">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <circle
                        cx="11"
                        cy="11"
                        r="7"
                        stroke="currentColor"
                        stroke-width="2"
                      />
                      <line
                        x1="16.65"
                        y1="16.65"
                        x2="21"
                        y2="21"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                      />
                    </svg>

                    <input v-model="searchText" placeholder="Поиск события..." />
                  </div>
                </div>
              </th>

            </tr>
          </thead>

          <tbody>
            <tr v-if="isLoading">
              <td :colspan="selectedObject === 'camera' ? 4 : 3">
                Загрузка журнала событий...
              </td>
            </tr>

            <tr v-else-if="loadError">
              <td :colspan="selectedObject === 'camera' ? 4 : 3">
                {{ loadError }}
              </td>
            </tr>

            <tr v-else-if="!filteredData.length">
              <td :colspan="selectedObject === 'camera' ? 4 : 3">
                События не найдены
              </td>
            </tr>

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

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

import adminService from '@/services/admin'

const logs = ref([])
const isLoading = ref(false)
const loadError = ref('')

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

function formatTimestamp(value) {
  if (!value) return '-'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)

  const pad = (num) => String(num).padStart(2, '0')

  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join('-') + ' ' + [
    pad(date.getHours()),
    pad(date.getMinutes()),
  ].join(':')
}

function mapLogEntry(item) {
  const objectName =
    item.entity_name ||
    item.actor_username ||
    (item.entity_type === 'system' ? 'Система' : `#${item.entity_id ?? '-'}`)

  return {
    id: item.id,
    type: item.entity_type,
    objectName,
    parkingName: item.parking_name || '',
    date: formatTimestamp(item.timestamp),
    description: item.description,
    raw: item,
  }
}

async function loadLogs() {
  isLoading.value = true
  loadError.value = ''

  try {
    const response = await adminService.getLogs({ limit: 200 })
    logs.value = (response.logs || []).map(mapLogEntry)
  } catch (error) {
    console.error('Не удалось загрузить журнал событий:', error)
    loadError.value = 'Не удалось загрузить журнал событий'
    logs.value = []
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  loadLogs()
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

const formatDateInput = (e, type) => {
  const input = e.target

  const refVal = type === 'from' ? dateFrom : dateTo

  const cursorPos = input.selectionStart

  let digits = refVal.value.replace(/[^\d]/g, '')

  digits = digits.slice(0, 12)

  let formatted = ''

  if (digits.length > 0) formatted += digits.slice(0, 4)
  if (digits.length >= 5) formatted += '-' + digits.slice(4, 6)
  if (digits.length >= 7) formatted += '-' + digits.slice(6, 8)
  if (digits.length >= 9) formatted += ' ' + digits.slice(8, 10)
  if (digits.length >= 11) formatted += ':' + digits.slice(10, 12)

  refVal.value = formatted

  requestAnimationFrame(() => {
    let newPos = cursorPos

    const addedSeparators =
      (formatted.slice(0, newPos).match(/[- :]/g) || []).length

    input.setSelectionRange(newPos + addedSeparators, newPos + addedSeparators)
  })
}

const parseDate = (str) => {
  if (!str) return null

  const match = str.match(
    /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/
  )

  if (!match) return null

  const [_, y, m, d, h, min] = match

  const date = new Date(y, m - 1, d, h, min)

  // защита от 2026-99-99
  if (
    date.getFullYear() != y ||
    date.getMonth() != m - 1 ||
    date.getDate() != d ||
    date.getHours() != h ||
    date.getMinutes() != min
  ) {
    return null
  }

  return date
}


const invalidDateInput = computed(() => {
  return (
    (dateFrom.value && !parseDate(dateFrom.value)) ||
    (dateTo.value && !parseDate(dateTo.value))
  )
})

/* FILTER */
const filteredData = computed(() => {
  if (invalidDateInput.value) return []
  return logs.value.filter(item => {

    if (selectedObject.value !== 'all' && item.type !== selectedObject.value)
      return false

    if (selectedObject.value === 'camera' && selectedParking.value) {
      if (item.parkingName !== selectedParking.value) return false
    }

    if (searchText.value &&
      !item.description.toLowerCase().includes(searchText.value.toLowerCase()))
      return false


    const d = new Date(item.date.replace(' ', 'T'))
    const from = parseDate(dateFrom.value)
    const to = parseDate(dateTo.value)

    if (from && d < from) return false
    if (to && d > to) return false

    return true
  })
})
</script>

<style scoped>

.table-container {
  padding: 40px;
}

.table-wrapper {
  border-radius: 10px;
  border: 1px solid #6C6A6A;
  
}

.log-table { 
  width: 100%; 
  border-collapse: separate; 
  border-spacing: 0; 

}

.log-table td { 
  padding: 10px; 
  text-align: center; 
  border-right: 1px solid #6C6A6A; 
  border-top: 1px solid #6C6A6A; 
}

.log-table th { 
  padding: 10px; 
  text-align: center; 
  border-right: 1px solid #6C6A6A; 
} 


.log-table thead tr + tr th { 
  border-top: 1px solid #6C6A6A; 
} 

.log-table thead tr:first-child th:first-child {
  border-top-left-radius: 10px;
}

.log-table thead tr:first-child th:last-child {
  border-top-right-radius: 10px;
}

.log-table tbody tr:last-child td:first-child {
  border-bottom-left-radius: 10px;
}

.log-table tbody tr:last-child td:last-child {
  border-bottom-right-radius: 10px;
}

.log-table tbody tr:last-child td {
  border-bottom: 1px solid #6C6A6A;
}

/* Убираем правую границу у последнего столбца */ 
.log-table td:last-child { 
  border-right: none; 
} 

.log-table th:last-child { 
  border-right: none; 
} 

/* Чередование строк */ 
.log-table tbody tr:nth-child(even) { 
  background: #F5F2F2; 
} 

.log-table tbody tr:nth-child(odd) { 
  background: #FFFFFF; 
} 

.log-table thead tr:first-child th { 
  background: #F5F2F2; 

} 

.col-object {
  width: 22%;
}

.col-date {
  width: 25%;
}

.col-parking {
  width: 18%;
}

.col-search {
  width: 45%;
}

th, td {
  border: 1px solid #e0e0e0;
  padding: 12px;
  text-align: center;
  position: relative;
  text-overflow: ellipsis;
  white-space: nowrap;
}

th {
  background: #f9fafb;
  font-weight: 600;
  overflow: visible;
}

td {
  overflow: hidden;
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
  vertical-align: middle;
}

.icon.search svg {
  transform: translateY(-1px);
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
  top: 100%;       
  left: 3%;         

  transform: none; 

  margin-top: 3px; 

  min-width: 180px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(0,0,0,0.12);
  border: 1px solid lightgray;

  padding: 12px;
  z-index: 100;

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
  align-items: center;
  margin-bottom: 10px;
}

.field label {
  font-size: 18px;
  width: 50px;
  color: #666;
  margin-bottom: 4px;
}

.field input {
  flex: 1; 
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 16px;
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
  min-width: 300px;
  align-items: center;
  gap: 8px;

  border: 1px solid #dcdcdc;
  border-radius: 8px;
  padding: 8px 10px;
}

.search-box input {
  font-size: 16px;
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
  background: #439AEB;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.actions button:hover {
  background: #1867b1;
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
