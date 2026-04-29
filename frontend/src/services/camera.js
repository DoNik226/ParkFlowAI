import apiClient from './api-client'

/**
 * Сервис работы с камерами
 */
export const cameraService = {
  /**
   * Получить список камер
   * GET /cameras?parking_id=1
   */
  async getAllCameras(parkingId = null) {
    const params = parkingId ? { parking_id: parkingId } : {}
    const response = await apiClient.get('/cameras', { params })
    return response.data
  },

  /**
   * Получить данные конкретной камеры
   * GET /cameras/{id}
   */
  async getCameraById(id) {
    const response = await apiClient.get(`/cameras/${id}`)
    return response.data
  },

  /**
   * Добавить камеру (только админ)
   * POST /cameras
   */
  async createCamera(cameraData) {
    const response = await apiClient.post('/cameras', cameraData)
    return response.data
  },

  /**
   * Обновить камеру (только админ)
   * PUT /cameras/{id}
   */
  async updateCamera(id, cameraData) {
    const response = await apiClient.put(`/cameras/${id}`, cameraData)
    return response.data
  },

  /**
   * Удалить камеру (только админ)
   * DELETE /cameras/{id}
   */
  async deleteCamera(id) {
    const response = await apiClient.delete(`/cameras/${id}`)
    return response.data
  },

  /**
   * Переподключить камеру (только админ)
   * POST /cameras/{id}/reconnect
   */
  async reconnectCamera(id) {
    const response = await apiClient.post(`/cameras/${id}/reconnect`)
    return response.data
  },

  /**
   * Получить URL видеопотока (MJPEG/HLS)
   * GET /cameras/{id}/stream
   */
  getCameraStreamUrl(id) {
    return `${apiClient.defaults.baseURL}/cameras/${id}/stream`
  },

  /**
   * Получить текущий кадр 
   * GET /cameras/{id}/snapshot
   */
  async getCameraSnapshot(id) {
    const response = await apiClient.get(`/cameras/${id}/snapshot`, {
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * Получить URL для snapshot 
   */
  getCameraSnapshotUrl(id) {
    return `${apiClient.defaults.baseURL}/cameras/${id}/snapshot`
  }
}