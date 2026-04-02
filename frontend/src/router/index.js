import { createRouter, createWebHistory } from 'vue-router'
import AdminView from '../views/AdminView.vue'
import LoginView from '../views/LoginView.vue'

const routes = [
  // 1. Страница входа (без защиты)
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
  },

  {
    path: '/',
    redirect: '/main' 
  },
  
  // 2. Главная страница (требуется авторизация)
  {
    path: '/main',
    name: 'Main',
    component: () => import('../views/MainView.vue'),
    meta: { requiresAuth: true }
  },

  // 3. Админка (требуется авторизация + роль admin)
  {
    path: '/admin',
    name: 'Admin',
    component: AdminView,
    meta: { requiresAuth: true, role: 'admin' },
    // Сохраняем вложенные маршруты из вашего оригинального файла
    children: [
      {
        path: 'users',
        component: () => import('../components/admin/UserManagement.vue')
      },
      {
        path: 'parkings',
        component: () => import('../components/admin/CameraManagement.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 4. Защита маршрутов (Navigation Guard)
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const role = localStorage.getItem('user_role')

  if (!token && to.path !== '/login') {
    return next('/login')
  }

  if (token && to.path === '/login') {
    return role === 'admin' ? next('/admin') : next('/main')
  }

  if (to.meta.role && to.meta.role !== role) {
    return next('/main')
  }

  next()
})

export default router