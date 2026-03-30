import { createRouter, createWebHistory } from 'vue-router'
import AdminView from '../views/AdminView.vue'

const routes = [
  {
    path: '/',
    component: () => import('../views/MainView.vue')
  },

  {
    path: '/admin',
    component: AdminView,
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

export default router