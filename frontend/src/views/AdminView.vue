<template>
  <div class="admin-container">
    <header class="header">
      <div class="logo">ParkFlow AI</div>

      <div class="right">
        <span>{{ username }}</span>

        <button
          v-if="isAdminHome"
          class="logout"
          title="Выйти"
          @click="logout"
        >
          <img src="../assets/img/sign-out.png" width="30" alt="Выйти">
        </button>

        <button
          v-else
          class="logout"
          title="Назад"
          @click="goAdminHome"
        >
          <img src="../assets/img/back.png" width="30" alt="Назад">
        </button>
      </div>
    </header>

    <main class="admin-content">
      <!-- Главное меню админа показывается только на /admin -->
      <div v-if="isAdminHome" class="admin-buttons">
        <button class="admin-item" @click="goUsers">
          <div class="admin-card">
            <img src="../assets/img/user.png" alt="Пользователи">
          </div>
          <span class="admin-label">Пользователи</span>
        </button>

        <button class="admin-item" @click="goParkings">
          <div class="admin-card">
            <img src="../assets/img/parking.png" alt="Парковки">
          </div>
          <span class="admin-label">Парковки</span>
        </button>

        <button class="admin-item" @click="goEvents">
          <div class="admin-card">
            <img src="../assets/img/save.png" alt="Журнал событий">
          </div>
          <span class="admin-label">Журнал событий</span>
        </button>

        <button class="admin-item" @click="goApplication">
          <div class="admin-card">
            <img src="../assets/img/mobile-app.png" alt="Приложение">
          </div>
          <span class="admin-label">Приложение</span>
        </button>
      </div>

      <!-- На /admin/users, /admin/parkings, /admin/events показывается только страница -->
      <router-view v-else />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authService } from '@/services/auth'

const route = useRoute()
const router = useRouter()

const username = computed(() => {
  return localStorage.getItem('username') || localStorage.getItem('user_role') || 'admin'
})

const isAdminHome = computed(() => route.path === '/admin')

function goAdminHome() {
  router.push('/admin')
}

function goUsers() {
  router.push('/admin/users')
}

function goParkings() {
  router.push('/admin/parkings')
}

function goEvents() {
  router.push('/admin/events')
}

function goApplication() {
  router.push('/main')
}

async function logout() {
  try {
    await authService.logout()
  } catch (error) {
    console.error('Ошибка выхода:', error)
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_id')
    localStorage.removeItem('username')

    router.replace('/login')
  }
}
</script>

<style scoped>
.admin-container {
  min-height: 100vh;
  background: #f7f7f7;
}

.header {
  height: 70px;
  background: #2d8fe3;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
}

.logo {
  font-size: 24px;
  font-weight: 700;
}

.right {
  display: flex;
  align-items: center;
  gap: 28px;
  font-size: 18px;
}

.logout {
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.admin-content {
  padding: 48px 24px;
}

.admin-buttons {
  display: flex;
  justify-content: center;
  gap: 90px;
  flex-wrap: wrap;
  margin-top: 120px;
}

.admin-item {
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: center;
}

.admin-card {
  width: 185px;
  height: 185px;
  background: #4a9ee8;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease, background 0.15s ease;
}

.admin-card img {
  max-width: 92px;
  max-height: 92px;
}

.admin-item:hover .admin-card {
  transform: translateY(-3px);
  background: #2d8fe3;
}

.admin-label {
  display: block;
  margin-top: 14px;
  color: #2d8fe3;
  font-size: 18px;
}

@media (max-width: 900px) {
  .admin-buttons {
    gap: 32px;
    margin-top: 40px;
  }

  .admin-card {
    width: 150px;
    height: 150px;
  }
}
</style>