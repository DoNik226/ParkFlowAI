import apiClient from './api-client'

export const adminService = {
  async getLogs(params = {}) {
    const response = await apiClient.get('/logs', { params })
    return response.data
  },

  async getUsers() {
    const response = await apiClient.get('/users')
    return response.data
  },

  async getUserById(id) {
    const response = await apiClient.get(`/users/${id}`)
    return response.data
  },

  async createUser(userData) {
    const response = await apiClient.post('/users', userData)
    return response.data
  },

  async updateUser(id, userData) {
    const response = await apiClient.put(`/users/${id}`, userData)
    return response.data
  },

  async changeUserPassword(id, newPassword) {
    const response = await apiClient.put(`/users/${id}/password`, {
      new_password: newPassword,
    })
    return response.data
  },

  async blockUser(id, block, durationMinutes = 30) {
    const response = await apiClient.put(`/users/${id}/block`, {
      block,
      duration_minutes: durationMinutes,
    })
    return response.data
  },

  async deleteUser(id) {
    const response = await apiClient.delete(`/users/${id}`)
    return response.data
  },

  async getParkings() {
    const response = await apiClient.get('/parkings')
    return response.data
  },
}

export default adminService
