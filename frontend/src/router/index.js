import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '@/views/LoginView.vue'
import MainView from '@/views/MainView.vue'
import MobileMainView from '@/views/MobileMainView.vue'
import AdminView from '@/views/AdminView.vue'
import ParkingView from '@/views/ParkingView.vue'

import UserManagement from '@/components/admin/UserManagement.vue'
import CameraManagement from '@/components/admin/CameraManagement.vue'
import EventLogViewer from '@/components/admin/EventLogViewer.vue'

function isMobile() {
  return window.innerWidth <= 768 || /Android|iPhone/i.test(navigator.userAgent)
}

const routes = [
  {
    path: '/',
    redirect: () => (isMobile() ? '/m' : '/main'),
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

  // Админский контур
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
        path: 'parkings',
        name: 'AdminParkings',
        component: ParkingView,
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'cameras',
        name: 'AdminCameras',
        component: CameraManagement,
        meta: { requiresAuth: true, role: 'admin' },
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
    return role === 'admin' ? '/admin' : (isMobile() ? '/m' : '/main')
  }

  if (to.meta.role && to.meta.role !== role) {
    return isMobile() ? '/m' : '/main'
  }

  return true
})

export default router