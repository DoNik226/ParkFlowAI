import { createRouter, createWebHistory } from 'vue-router'
import AdminView from '../views/AdminView.vue'
import LoginView from '../views/LoginView.vue'
import ParkingView from '../views/ParkingView.vue'


const routes = [
  // 1. Страница входа (без защиты)
  {
    path: '/',
    name: 'Login',
    component: LoginView,
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
        component: () => import('../views/ParkingView.vue')
      }, 
    ]
  }, 
  
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 4. Защита маршрутов (Navigation Guard)
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const role = localStorage.getItem('user_role')

  if (to.meta.requiresAuth && !token) {
    // Если нужен вход, но токена нет -> на страницу логина
    next('/')
  } else if (to.meta.role && to.meta.role !== role) {
    // Если роль не совпадает -> на страницу логина
    next('/')
  } else {
    // Всё ок -> пропускаем
    next()
  }
})

export default router