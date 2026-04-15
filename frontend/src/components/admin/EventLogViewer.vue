<template>
  <div class="log-page">

    <!-- TOP BAR -->
    <div class="top-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- TABLE -->
    <div class="table-container">

      <div class="table-with-button">

        <table class="log-table">
          <thead>
            <!-- HEADER -->
            <tr>
              <th v-for="col in activeTable.columns" :key="col.key" :style="{ width: col.width }">
                {{ col.label }}
              </th>
            </tr>

            <!-- FILTER ROW -->
            <tr class="filter-row">

              <!-- USER FILTERS -->
              <template v-if="activeTab === 'user'">
                <th>
                  <input v-model="filters.user.user" class="input" placeholder="Пользователь" />
                </th>

                <th>
                  <div class="date-filter"> 
                    <div class="date-group"> 
                      <span>От</span> 
                      <input type="datetime-local" v-model="filters.dateFrom" /> 
                    </div> <div class="date-group"> 
                      <span>До</span> 
                      <input type="datetime-local" v-model="filters.dateTo" /> 
                    </div>
                  </div>
                </th>

                <th>
                  <input v-model="filters.user.description" class="input" placeholder="Описание" />
                </th>
              </template>

              <!-- ADMIN FILTERS -->
              <template v-if="activeTab === 'admin'">
                <th>
                  <input v-model="filters.admin.admin" class="input" placeholder="Администратор" />
                </th>

                <th>
                  <div class="date-filter"> 
                    <div class="date-group"> 
                      <span>От</span> 
                      <input type="datetime-local" v-model="filters.dateFrom" /> 
                    </div> <div class="date-group"> 
                      <span>До</span> 
                      <input type="datetime-local" v-model="filters.dateTo" /> 
                    </div>
                  </div>
                </th>

                <th>
                  <input v-model="filters.admin.description" class="input" placeholder="Описание" />
                </th>
              </template>

              <!-- CAMERA FILTERS -->
              <template v-if="activeTab === 'camera'">

                <th>
                  <input v-model="filters.camera.cameraName" class="input" placeholder="Камера" />
                </th>

                <th>
                  <input v-model="filters.camera.parkingName" class="input" placeholder="Парковка" />
                </th>

                <th>
                  <div class="date-filter"> 
                    <div class="date-group"> 
                      <span>От</span> 
                      <input type="datetime-local" v-model="filters.dateFrom" /> 
                    </div> <div class="date-group"> 
                      <span>До</span> 
                      <input type="datetime-local" v-model="filters.dateTo" /> 
                    </div>
                  </div>
                </th>

                <th>
                  <input v-model="filters.camera.description" class="input" placeholder="Описание" />
                </th>

              </template>

            </tr>
          </thead>

          <tbody>
            <tr v-for="(item, index) in filteredData" :key="index">
              <td v-for="col in activeTable.columns" :key="col.key" :style="{ width: col.width }">
                {{ item[col.key] }}
              </td>
            </tr>
          </tbody>
        </table>

        <button class="search-btn" @click="applyFilter">
          <img src="../../assets/img/loupe.png" width="23px">
        </button>

      </div>

    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const tabs = [
  { key: 'user', label: 'Действия пользователя' },
  { key: 'admin', label: 'Действия администратора' },
  { key: 'camera', label: 'События с камер' }
]

const tableConfig = {
  user: {
    columns: [
      { key: 'user', label: 'Пользователь', width: '25%' },
      { key: 'date', label: 'Дата и время', width: '35%' },
      { key: 'description', label: 'Описание', width: '40%' }
    ],
    dataKey: 'userLogs'
  },

  admin: {
    columns: [
      { key: 'admin', label: 'Администратор', width: '25%' },
      { key: 'date', label: 'Дата и время', width: '35%' },
      { key: 'description', label: 'Описание', width: '40%' }
    ],
    dataKey: 'adminLogs'
  },

  camera: {
    columns: [
      { key: 'cameraName', label: 'Камера', width: '15%' },
      { key: 'parkingName', label: 'Парковка', width: '15%' },
      { key: 'date', label: 'Дата и время', width: '36%' },
      { key: 'description', label: 'Описание', width: '34%' }
    ],
    dataKey: 'cameraLogs'
  }
}

const activeTab = ref('user')

const logs = ref([
  { user: 'ivanivanovich', date: '2026-04-14 10:15', description: 'Вход в систему' },
  { user: 'petrpetrovich', date: '2026-04-14 11:20', description: 'Обновление въезда' },
  { user: 'sidorsidorovich', date: '2026-04-13 09:05', description: 'Выход из системы' }
])

const adminLogs = ref([
  { admin: 'admin1', date: '2026-04-14 12:00', description: 'Удаление пользователя' }
])

const cameraLogs = ref([
  {
    cameraName: 'CAM-01',
    parkingName: 'P1',
    date: '2026-04-14 09:00',
    description: 'Обнаружен автомобиль'
  }
])

const activeTable = computed(() => tableConfig[activeTab.value])

const currentData = computed(() => {
  if (activeTab.value === 'user') return logs.value
  if (activeTab.value === 'admin') return adminLogs.value
  if (activeTab.value === 'camera') return cameraLogs.value
})

const filters = ref({
  user: {
    user: '',
    dateFrom: '',
    dateTo: '',
    description: ''
  },

  admin: {
    admin: '',
    dateFrom: '',
    dateTo: '',
    description: ''
  },

  camera: {
    cameraName: '',
    parkingName: '',
    dateFrom: '',
    dateTo: '',
    description: ''
  }
})

const appliedFilters = ref({ ...filters.value })

const applyFilter = () => {
  appliedFilters.value = { ...filters.value }
}

const filteredData = computed(() => {
  const data = currentData.value
  const f = filters.value[activeTab.value]

  return data.filter(item => {

    const matchText = Object.keys(item).every(key => {
      if (key === 'date') return true

      if (!f[key]) return true

      return String(item[key])
        .toLowerCase()
        .includes(f[key].toLowerCase())
    })

    const date = new Date(item.date)

    const matchFrom = f.dateFrom
      ? date >= new Date(f.dateFrom)
      : true

    const matchTo = f.dateTo
      ? date <= new Date(f.dateTo)
      : true

    return matchText && matchFrom && matchTo
  })
})
</script>

<style scoped>

.log-page {
  padding: 20px;
}

/* TOP BAR */
.top-bar {
  margin: -20px -20px 0 -20px;
  width: calc(100% + 40px);
  background: #e5e5e5;
  display: flex;
  gap: 0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.tab-btn {
  padding: 10px 20px;
  display: flex;
  height: 40px;
  border: none;
  background: #cfcfcf;
  cursor: pointer;
  border-right: 1px solid #6C6A6A;
}

.tab-btn.active {
  background: white;
  font-weight: bold;
}

/* TABLE + BUTTON */
.table-with-button {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 20px;
}

.log-table {
  table-layout: fixed;
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid #6C6A6A;      
  border-radius: 10px;
  overflow: hidden;
}

/* BODY */
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

/* Убираем правую границу у последнего столбца */
.log-table td:last-child {
  border-right: none;
}

.log-table th:last-child {
  border-right: none;
}

/* Чередование строк */
.log-table tbody tr:nth-child(even) {
  background: #FFFFFF;
}

.log-table tbody tr:nth-child(odd) {
  background: #F5F2F2;
}

.log-table thead tr:first-child th {
  background: #F5F2F2;
}

.log-table {
  table-layout: fixed;
}

.filter-row {
  background: #FFFFFF;
  border-bottom: 1px solid #6C6A6A;
}


.filter-row input {
  width: 100%;
  padding: 4px;
  box-sizing: border-box;
}


.date-filter {
  display: flex;
  gap: 10px;
  max-width: 100%;
  overflow: hidden;
}

.date-group {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.date-group input {
  width: 160px;
  flex: 0 0 160px;
  box-sizing: border-box;
  padding: 6px;
  border-radius: 8px;
  border: 1px solid #ccc;
  text-align: center;
  color: #6C6A6A;
}

.date-group span {
  min-width: 20px;
  flex-shrink: 0;
}

.input {
  padding: 4px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.search-btn {
  height: 40px;
  width: 40px;
  margin-top: 50px;
  border: none;
  background: #3B66F4;
  color: white;
  border-radius: 10px;
  cursor: pointer;
}
</style>