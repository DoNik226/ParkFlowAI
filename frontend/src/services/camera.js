import apiClient from './api-client'

export const cameraService = {
  async getAllCameras(params = {}) {
    const response = await apiClient.get('/cameras', { params })
    return response.data
  },

  async getCamera(cameraId) {
    const response = await apiClient.get(`/cameras/${cameraId}`)
    return response.data
  },

  async createCamera(data) {
    const response = await apiClient.post('/cameras', data)
    return response.data
  },

  async updateCamera(cameraId, data) {
    const response = await apiClient.put(`/cameras/${cameraId}`, data)
    return response.data
  },

  async deleteCamera(cameraId) {
    const response = await apiClient.delete(`/cameras/${cameraId}`)
    return response.data
  },

  async reconnectCamera(cameraId) {
    const response = await apiClient.post(`/cameras/${cameraId}/reconnect`)
    return response.data
  },
}