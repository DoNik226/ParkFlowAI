import apiClient from './api-client'

/**
 * Сервис административных функций
 */
export const adminService = {
  // GET /users — Получить список пользователей
  async getUsers() {
    const response = await apiClient.get('/users')
    return response.data
  },

  // GET /users/{id} — Получить данные пользователя
  async getUserById(id) {
    const response = await apiClient.get(`/users/${id}`)
    return response.data
  },

  // POST /users — Создать пользователя
  async createUser(userData) {
    const response = await apiClient.post('/users', userData)
    return response.data
  },

  // PUT /users/{id} — Обновить данные пользователя
  async updateUser(id, userData) {
    const response = await apiClient.put(`/users/${id}`, userData)
    return response.data
  },

  // PUT /users/{id}/password — Сменить пароль
  async changeUserPassword(id, newPassword) {
    const response = await apiClient.put(`/users/${id}/password`, {
      new_password: newPassword
    })
    return response.data
  },

  // PUT /users/{id}/block — Заблокировать/разблокировать
  async blockUser(id, block, durationMinutes = 30) {
    const response = await apiClient.put(`/users/${id}/block`, {
      block,
      duration_minutes: durationMinutes
    })
    return response.data
  },

  // DELETE /users/{id} — Удалить пользователя
  async deleteUser(id) {
    const response = await apiClient.delete(`/users/${id}`)
    return response.data
  },

  // GET /parkings — Получить список парковок
  async getParkings() {
    const response = await apiClient.get('/parkings')
    return response.data
  }
}