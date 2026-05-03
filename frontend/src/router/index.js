import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '@/views/LoginView.vue'
import MainView from '@/views/MainView.vue'
import MobileMainView from '@/views/MobileMainView.vue'
import AdminView from '@/views/AdminView.vue'
import ParkingView from '@/views/ParkingView.vue'
import DigitalMapEditorView from '@/views/DigitalMapEditorView.vue'

import ParkingLayoutEditorView from '@/views/ParkingLayoutEditorView.vue'
import ParkingCreateView from '@/views/ParkingCreateView.vue'
import ParkingSetupView from '@/views/ParkingSetupView.vue'

import UserManagement from '@/components/admin/UserManagement.vue'
import EventLogViewer from '@/components/admin/EventLogViewer.vue'

function isMobile() {
  return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
}

function getUserHomePath() {
  return isMobile() ? '/m' : '/main'
}

const routes = [
  {
    path: '/',
    redirect: () => getUserHomePath(),
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
  },
  {
    path: '/main',
    name: 'Main',
    component: MainView,
    meta: { requiresAuth: true },
  },
  {
    path: '/m',
    name: 'MobileMain',
    component: MobileMainView,
    meta: { requiresAuth: true },
  },
  {
    path: '/parkings',
    name: 'Parkings',
    component: ParkingView,
    meta: { requiresAuth: true },
  },

  {
    path: '/admin',
    name: 'AdminHome',
    component: AdminView,
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      {
        path: 'users',
        name: 'AdminUsers',
        component: UserManagement,
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'parkings/new',
        name: 'AdminParkingCreate',
        component: ParkingCreateView,
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'parkings/:parkingId/setup',
        name: 'AdminParkingSetup',
        component: ParkingSetupView,
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'parkings/:parkingId/layout-editor',
        name: 'AdminParkingLayoutEditor',
        component: ParkingLayoutEditorView,
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'parkings/:parkingId/map-editor',
        name: 'AdminParkingMapEditor',
        component: DigitalMapEditorView,
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'parkings',
        name: 'AdminParkings',
        component: ParkingView,
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'cameras',
        redirect: '/admin',
      },
      {
        path: 'events',
        name: 'AdminEvents',
        component: EventLogViewer,
        meta: { requiresAuth: true, role: 'admin' },
      },
    ],
  },

  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  const role = localStorage.getItem('user_role')

  if (!token && to.path !== '/login') {
    return '/login'
  }

  if (token && to.path === '/login') {
    return role === 'admin' ? '/admin' : getUserHomePath()
  }

  // Обычный пользователь не должен попадать в админку
  if (to.meta.role && to.meta.role !== role) {
    return {
      path: getUserHomePath(),
      query: to.query,
    }
  }

  // Если обычный пользователь с телефона попал на desktop-страницу,
  // переводим его на мобильную карту.
  if (token && role !== 'admin' && isMobile() && to.path === '/main') {
    return {
      path: '/m',
      query: to.query,
    }
  }

  // Если обычный пользователь с компьютера попал на мобильную страницу,
  // переводим его на desktop-карту.
  if (token && role !== 'admin' && !isMobile() && to.path === '/m') {
    return {
      path: '/main',
      query: to.query,
    }
  }

  return true
})

export default router