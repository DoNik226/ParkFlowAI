<template>
  <section class="parking-view">
    <div class="page-header">
      <div>
        <h1>Парковки</h1>
        <p>Парковки, доступные текущему администратору</p>
      </div>

      <div class="header-actions">
        <button class="secondary-btn" @click="loadParkings">
          Обновить
        </button>

        <button class="primary-btn" @click="createParking">
          + Добавить парковку
        </button>
      </div>
    </div>

    <div v-if="loading" class="state-card">
      Загрузка парковок...
    </div>

    <div v-else-if="error" class="state-card error">
      {{ error }}
    </div>

    <div v-else-if="!parkings.length" class="state-card">
      Парковки пока не созданы.
    </div>

    <div v-else class="parking-grid">
      <article
        v-for="parking in parkings"
        :key="parking.id"
        class="parking-card"
      >
        <div class="card-top">
          <div>
            <h2>{{ parking.name }}</h2>
            <p>ID: {{ parking.id }}</p>
          </div>

          <span class="badge">
            {{ parking.spots_count ?? 0 }} мест
          </span>
        </div>

        <div class="summary">
          <div>
            <span>Свободно</span>
            <strong class="free">{{ parking.summary?.free ?? 0 }}</strong>
          </div>

          <div>
            <span>Занято</span>
            <strong class="occupied">{{ parking.summary?.occupied ?? 0 }}</strong>
          </div>

          <div>
            <span>Неизвестно</span>
            <strong class="unknown">{{ parking.summary?.unknown ?? 0 }}</strong>
          </div>
        </div>

        <div class="meta">
          <div>
            <span>Компания</span>
            <b>{{ parking.company_id }}</b>
          </div>

          <div>
            <span>Зоны</span>
            <b>{{ parking.zones_count ?? 0 }}</b>
          </div>
        </div>

        <div class="actions">
          <button @click="openMap(parking.id)">
            Карта
          </button>

          <button class="secondary" @click="openSetup(parking.id)">
            Настройка
          </button>

          <button class="danger" @click="deleteParking(parking)">
            Удалить
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { parkingService } from '@/services/parking'

const router = useRouter()

const parkings = ref([])
const loading = ref(false)
const error = ref('')

async function loadParkings() {
  loading.value = true
  error.value = ''

  try {
    parkings.value = await parkingService.getAllParkings()
  } catch (err) {
    console.error('Ошибка загрузки парковок:', err)
    error.value = 'Не удалось загрузить список парковок'
  } finally {
    loading.value = false
  }
}

function createParking() {
  router.push('/admin/parkings/new')
}

function openSetup(parkingId) {
  router.push(`/admin/parkings/${parkingId}/setup`)
}

function openMap(parkingId) {
  router.push({
    path: '/main',
    query: {
      parking_id: parkingId,
    },
  })
}

async function deleteParking(parking) {
  const ok = window.confirm(`Удалить парковку "${parking.name}"?`)
  if (!ok) return

  try {
    await parkingService.deleteParking(parking.id)
    await loadParkings()
  } catch (err) {
    console.error('Ошибка удаления парковки:', err)
    error.value = 'Не удалось удалить парковку'
  }
}

onMounted(() => {
  loadParkings()
})
</script>

<style scoped>
.parking-view {
  min-height: calc(100vh - 70px);
  padding: 28px;
  background: #f5f7fb;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 6px;
  color: #1f2937;
}

.page-header p {
  margin: 0;
  color: #6b7280;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.primary-btn,
.secondary-btn {
  border: none;
  border-radius: 10px;
  padding: 11px 16px;
  cursor: pointer;
  font-weight: 700;
}

.primary-btn {
  background: #2d8fe3;
  color: #fff;
}

.secondary-btn {
  background: #eef2f7;
  color: #1f2937;
}

.state-card {
  padding: 22px;
  background: #fff;
  border-radius: 16px;
  color: #6b7280;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.state-card.error {
  color: #dc2626;
}

.parking-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 18px;
}

.parking-card {
  background: #fff;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  border: 1px solid #e5e7eb;
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.card-top h2 {
  margin: 0 0 4px;
  color: #111827;
}

.card-top p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

.badge {
  height: max-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eef6ff;
  color: #2d8fe3;
  font-weight: 700;
  font-size: 13px;
}

.summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 9px;
  margin-bottom: 16px;
}

.summary div,
.meta div {
  padding: 12px;
  border-radius: 12px;
  background: #f9fafb;
}

.summary span,
.meta span {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}

.summary strong {
  font-size: 24px;
}

.free {
  color: #16a34a;
}

.occupied {
  color: #dc2626;
}

.unknown {
  color: #6b7280;
}

.meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 9px;
  margin-bottom: 16px;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}

.actions button {
  border: none;
  border-radius: 10px;
  background: #2d8fe3;
  color: #fff;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 700;
}

.actions .secondary {
  background: #eef2f7;
  color: #1f2937;
}

.actions .danger {
  background: #ef4444;
  color: #fff;
}

@media (max-width: 720px) {
  .parking-view {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .summary,
  .meta,
  .actions {
    grid-template-columns: 1fr;
  }
}
</style>