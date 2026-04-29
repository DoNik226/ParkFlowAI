<template>
  <header class="app-header">
    <div class="brand" @click="goMain">ParkFlow AI</div>

    <nav class="nav">
      <button @click="goMain">Карта</button>
      <button v-if="isAdmin" @click="goAdmin">Админка</button>
      <button @click="logout">Выйти</button>
    </nav>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '@/services/auth'

const router = useRouter()

const isAdmin = computed(() => localStorage.getItem('user_role') === 'admin')

function goMain() {
  router.push('/main')
}

function goAdmin() {
  router.push('/admin')
}

async function logout() {
  await authService.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #0b0f17;
  color: #fff;
  border-bottom: 1px solid #202838;
}

.brand {
  font-weight: 800;
  color: #00e5a0;
  cursor: pointer;
}

.nav {
  display: flex;
  gap: 10px;
}

.nav button {
  border: 1px solid #2c3444;
  background: #111827;
  color: #fff;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
}
</style>