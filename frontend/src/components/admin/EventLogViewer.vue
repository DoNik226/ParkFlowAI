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
    <div class="table-container" v-if="activeTab === 'user'">

      <div class="table-with-button">

        <table class="log-table">
          <thead>
            <!-- HEADER -->
            <tr>
              <th>Пользователь</th>
              <th>Дата и время</th>
              <th>Описание</th>
            </tr>

            <!-- FILTER ROW -->
            <tr class="filter-row">
              <th>
                <input 
                  v-model="filters.user"
                  class="input"
                  placeholder="Фильтр"
                />
              </th>

              <th>
                <div class="date-filter">
                  <div class="date-group">
                    <span>От</span>
                    <input type="datetime-local" v-model="filters.dateFrom" />
                  </div>

                  <div class="date-group">
                    <span>До</span>
                    <input type="datetime-local" v-model="filters.dateTo" />
                  </div>
                </div>
              </th>

              <th>
                <input 
                  v-model="filters.description"
                  class="input"
                  placeholder="Фильтр"
                />
              </th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="(item, index) in filteredLogs" :key="index">
              <td>{{ item.user }}</td>
              <td>{{ item.date }}</td>
              <td>{{ item.description }}</td>
            </tr>
          </tbody>
        </table>

        <!-- SEARCH BUTTON (рядом с таблицей) -->
        <button class="search-btn" @click="applyFilter">
          🔍
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

const activeTab = ref('user')

const logs = ref([
  { user: 'ivanivanovich', date: '2026-04-14 10:15', description: 'Вход в систему' },
  { user: 'petrpetrovich', date: '2026-04-14 11:20', description: 'Обновление въезда' },
  { user: 'sidorsidorovich', date: '2026-04-13 09:05', description: 'Выход из системы' }
])

const filters = ref({
  user: '',
  dateFrom: '',
  dateTo: '',
  description: ''
})

const appliedFilters = ref({ ...filters.value })

const applyFilter = () => {
  appliedFilters.value = { ...filters.value }
}

const filteredLogs = computed(() => {
  return logs.value.filter(log => {

    const matchUser = appliedFilters.value.user
      ? log.user.toLowerCase().includes(appliedFilters.value.user.toLowerCase())
      : true

    const matchDesc = appliedFilters.value.description
      ? log.description.toLowerCase().includes(appliedFilters.value.description.toLowerCase())
      : true

    const logDate = new Date(log.date)

    const matchFrom = appliedFilters.value.dateFrom
      ? logDate >= new Date(appliedFilters.value.dateFrom)
      : true

    const matchTo = appliedFilters.value.dateTo
      ? logDate <= new Date(appliedFilters.value.dateTo)
      : true

    return matchUser && matchDesc && matchFrom && matchTo
  })
})
</script>

<style scoped>
.log-page {
  padding: 20px;
}

/* TOP BAR */
.top-bar {
  background: #e5e5e5;
  padding: 10px;
  display: flex;
  gap: 10px;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: #cfcfcf;
  cursor: pointer;
  border-radius: 6px;
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

/* TABLE */
.log-table {
  width: 100%;
  border-collapse: collapse;
}

.log-table th,
.log-table td {
  border: 1px solid #ddd;
  padding: 8px;
}

.log-table th {
  background: #f3f3f3;
}

/* FILTER ROW */
.filter-row input {
  width: 100%;
}

/* DATE FILTER */
.date-filter {
  display: flex;
  gap: 6px;
}

.date-group {
  display: flex;
  flex-direction: column;
  font-size: 10px;
}

/* INPUT */
.input {
  padding: 4px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

/* BUTTON */
.search-btn {
  height: 36px;
  width: 40px;
  border: none;
  background: #3B66F4;
  color: white;
  border-radius: 6px;
  cursor: pointer;
}
</style>