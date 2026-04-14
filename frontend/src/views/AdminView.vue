<template>
  <div class="admin-container">

    <!-- HEADER -->
    <header class="header">
      <div class="logo">ParkFlow AI</div>

      <div class="right">
        <span>admin</span>
        <!-- если НЕ главная админка -->
        <button v-if="$route.path !== '/admin'" @click="$router.push('/admin')" class="logout">
          <img src="../assets/img/back.png" width="30">
        </button>

        <!-- если главная -->
        <button v-else class="logout">
          <img src="../assets/img/sign-out.png" width="30">
        </button>
      </div>
    </header>

    <!-- CONTENT -->
    <div class="admin-content">

      <div v-if="$route.path === '/admin'" class="admin-buttons">

        <div class="admin-item" @click="goUsers">
            <div class="admin-card">
            <img src="../assets/img/user.png" alt="app">
            </div>
            <span class="admin-label">Пользователи</span>
        </div>

        <div class="admin-item" @click="goParkings">
            <div class="admin-card">
            <img src="../assets/img/parking.png" alt="app">
            </div>
            <span class="admin-label">Парковки</span>
        </div>

        <div class="admin-item" @click="goApp">
            <div class="admin-card">
              <img src="../assets/img/mobile-app.png" alt="app">
            </div>
            <span class="admin-label">Приложение</span>
        </div>

        <div class="admin-item" @click="goEvents">
            <div class="admin-card">
              <img src="../assets/img/mobile-app.png" alt="app">
            </div>
            <span class="admin-label">Журнал событий</span>
        </div>

        </div>

      <!-- ВЛОЖЕННЫЕ СТРАНИЦЫ -->
      <router-view />

    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goUsers = () => router.push('/admin/users')
const goParkings = () => router.push('/admin/parkings')
const goApp = () => router.push('/main')
const goEvents = () => router.push('/admin/events')
</script>